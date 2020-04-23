from .config import config
from .util import db_session, split_date_range, chunks, JSONDatetimeEncoder, float_to_decimal, decimal_to_float
from .models import Case
from .session import AsyncSessionPool
import trio
import asks
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from boto3.dynamodb.conditions import Key
import re
import string
import json
import logging
from enum import Enum

logger = logging.getLogger(__name__)

def delta_seconds(timestamp):
        return (datetime.now() - timestamp).total_seconds()

class FailedSearch(Exception):
    pass

class FailedSearchTimeout(FailedSearch):
    pass

class FailedSearch500Error(FailedSearch):
    pass

class FailedSearchUnknownError(FailedSearch):
    pass

class FailedSearchUnavailable(FailedSearch):
    pass

class CompletedSearchNoResults(Exception):
    pass

class SpiderStatus(Enum):
    NEW = 1
    IN_PROGRESS = 2
    COMPLETE = 3
    CANCELED = 4
    FAILED = 5

class NodeStatus(Enum):
    NEW = 1
    IN_PROGRESS = 2
    COMPLETE = 3
    TIME_RANGE_SPLIT = 4
    FAILED = 5


class Spider:
    '''Main spider class'''

    def __init__(self, query_start_date, query_end_date, court=None, site=None, concurrency=None):
        # Spider parameters
        self.query_start_date = query_start_date
        self.query_end_date = query_end_date
        self.court = court
        self.site = site

        # Stateful attributes
        self.timestamp = None
        self.status = SpiderStatus.NEW
        self.results = {
            'run_seconds': 0.0,
            'total_cases_added': 0,
            'total_cases_processed': 0,
            'total_requests': 0
        }
        self.slices = []
        self.slice_idx = -1

        # Set up concurrency
        self.concurrency = concurrency or config.SPIDER_DEFAULT_CONCURRENCY
        self.session_pool = AsyncSessionPool(self.concurrency)

    @classmethod
    def load(cls, state_dict):
        if state_dict['_type'] != cls.__name__:
            raise Exception('Invalid state JSON object')
        spider = cls(
            query_start_date=datetime.strptime(state_dict['query_start_date'], '%m/%d/%Y'),
            query_end_date=datetime.strptime(state_dict['query_end_date'], '%m/%d/%Y'),
            court=state_dict['court'],
            site=state_dict['site'],
            concurrency=int(state_dict['concurrency']),
        )
        spider.results = state_dict['results']
        spider.status = SpiderStatus[state_dict['status']]
        spider.timestamp = datetime.fromisoformat(state_dict['timestamp']) if state_dict['timestamp'] else None
        spider.slices = [ SearchNode.load(None, spider, slice) for slice in state_dict['slices'] ]
        return spider

    # searching for underscore character leads to timeout for some reason
    # % is a wildcard character
    search_chars = string.ascii_uppercase \
        + string.digits \
        + string.punctuation.replace('_','').replace('%','') \
        + ' '    
    
    @property
    def __dict__(self):
        assert self.query_start_date
        assert self.query_end_date
        assert self.timestamp
        self.__calculate_results()
        return {
            'id': self.id,  # Hash/partition key
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,  # Range/sort key
            '_type': type(self).__name__,
            'query_start_date': self.query_start_date.strftime('%m/%d/%Y'),
            'query_end_date': self.query_end_date.strftime('%m/%d/%Y'),
            'court': self.court,
            'site': self.site,
            'concurrency': self.concurrency,
            'slices': [ slice.export() for slice in self.slices ],
            'results': self.results,
            'status': self.status.name,
        }

    @property
    def id(self):
        ''' ID is deterministic based on concatenation of search parameters '''
        if not hasattr(self,'_id'):
            self._id = self.query_start_date.strftime("%Y-%m-%d")
            if self.query_end_date:
                self._id += '/' + self.query_end_date.strftime("%Y-%m-%d")
            if self.court:
                self._id += '/' + self.court
            if self.site:
                self._id += '/' + self.site
        return self._id
    
    def start(self):
        trio.run(self.__start, restrict_keyboard_interrupt_to_checkpoints=True)

    def resume(self, run_datetime=None):
        ''' Resumes most recent (or specified) spider run '''
        state_dict = self.__load_run(run_datetime)
        loaded_spider = self.load(state_dict)
        self.results = loaded_spider.results
        self.status = loaded_spider.status
        self.timestamp = loaded_spider.timestamp
        self.slices = loaded_spider.slices
        self.start()

    async def __start(self):
        if self.status == SpiderStatus.COMPLETE:
            logger.warning('Spider is in complete state, cannot start.')
            return
        elif self.status == SpiderStatus.NEW:
            self.__generate_slices()
            logger.info(f"Starting spider run: {self.id}")
            self.status = SpiderStatus.IN_PROGRESS
        elif self.status == SpiderStatus.IN_PROGRESS or self.status == SpiderStatus.CANCELED or self.status == SpiderStatus.FAILED:
            logger.info(f"Resuming previous spider run: {self.timestamp.isoformat()}/{self.id}")
            self.status == SpiderStatus.IN_PROGRESS

        self.timestamp = datetime.now()
        logger.info(f"Run timestamp: {self.timestamp.isoformat()}")
        try:
            async with trio.open_nursery() as spider_nursery:
                def start_slice():
                    for node in self.slices[(self.slice_idx + 1):]:
                        if node.status == NodeStatus.NEW or node.status == NodeStatus.IN_PROGRESS or node.status == NodeStatus.FAILED:
                            self.slice_idx = self.slices.index(node)
                            logger.info(f'Starting slice {self.slice_idx + 1} of {len(self.slices)}')
                            spider_nursery.start_soon(node.start, self.session_pool, start_slice)
                            return
                for _ in range(self.concurrency):
                    start_slice()
                spider_nursery.start_soon(self.__state_manager, spider_nursery)
        except KeyboardInterrupt:
            print("\nCaught KeyboardInterrupt: saving spider run...")
            self.status = SpiderStatus.CANCELED
        except:
            self.status = SpiderStatus.FAILED
            raise
        else:
            self.status = SpiderStatus.COMPLETE
        finally:
            self.__save_run(save_children=True)
            self.__log_results()
        logger.info("Spider run complete")

    def __generate_slices(self):
        ''' Split up the query time range into smaller chunks to improve likelihood of getting (0 < n_results < 500) returned '''
        if self.slices:
            raise Exception('Cannot generate slices; spider already has slices')
        self.slices = []
        if not self.query_end_date:
            self.query_end_date = datetime.now().date()
        def gen_timeranges(start_date, end_date):
            for n in range(0,int((end_date - start_date).days),config.SPIDER_DAYS_PER_QUERY):
                start = start_date + timedelta(n)
                end = start_date + timedelta(n) + timedelta(config.SPIDER_DAYS_PER_QUERY - 1)
                if end > end_date:
                    end = end_date
                if start == end:
                    end = None
                yield (start,end)
        for (start,end) in gen_timeranges(self.query_start_date, self.query_end_date):
            self.slices.append(
                SearchNode(
                    range_start_date=start,
                    range_end_date=end,
                    search_string=None,
                    parent=None,
                    spider=self,
                )
            )
        logger.info(f'Generated {len(self.slices)} slices')

    def append_slices(self, slices):
        self.slices += [
            SearchNode(
                range_start_date=slice['range_start_date'],
                range_end_date=slice['range_end_date'],
                search_string=slice['search_string'],
                parent=None,
                spider=self
            ) for slice in slices 
        ]
        
    async def __state_manager(self, nursery):
        ''' Periodically save state '''
        logger.debug('Spider state manager initiating')
        last_update = datetime.now()
        while True:
            await trio.sleep(5)
            now = datetime.now()
            if len(nursery.child_tasks) == 1:
                logger.debug('Spider state manager terminating')
                return
            if (now - last_update).total_seconds() > config.SPIDER_UPDATE_FREQUENCY:
                last_update = now
                logger.debug('Updating spider state')
                self.__save_run(save_children=False)

    def __save_run(self, save_children=False):
        logger.debug('Saving run.')
        self.results['run_seconds'] = delta_seconds(self.timestamp)
        if save_children:
            # Save any in-progress slices to S3
            for slice in self.slices:
                if slice.status == NodeStatus.IN_PROGRESS:
                    logger.debug(f'Saving slice {slice.id}')
                    slice.save()
        self.__calculate_results()
        config.spider_table.put_item(Item=float_to_decimal(self.__dict__))

    def __load_run(self, run_datetime=None):
        if run_datetime:
            item = config.spider_table.get_item(Key={
                'id': self.id,
                'timestamp': run_datetime.isoformat()
            })
            return decimal_to_float(item['Item'])
        else:
            item = config.spider_table.query(
                KeyConditionExpression=Key('id').eq(self.id),
                ScanIndexForward=False,
                Limit=1
            )
            return decimal_to_float(item['Items'][0])

    def __calculate_results(self):
        self.results['total_cases_added'] = self.results['total_cases_processed'] = self.results['total_requests'] = 0
        for slice in self.slices:
            self.results['total_cases_added'] += slice.results['total_cases_added']
            self.results['total_cases_processed'] += slice.results['total_cases_processed']
            self.results['total_requests'] += slice.results['total_requests']
    
    def __log_results(self):
        logger.info(f'SPIDER RESULTS FOR RUN {self.timestamp.isoformat()}')
        logger.info(f'Search criteria: {self.query_start_date.strftime("%m/%d/%Y")} - {self.query_end_date.strftime("%m/%d/%Y")} / Court: {self.court} / Site: {self.site}')
        logger.info(f'Run finished at {(self.timestamp + timedelta(seconds=self.results["run_seconds"])).isoformat()}')
        logger.info(f'Run duration: {self.results["run_seconds"]} seconds')
        logger.info(f'Total requests sent: {self.results["total_requests"]}')
        logger.info(f'Total new cases added: {self.results["total_cases_added"]}')
        logger.info(f'Total cases processed: {self.results["total_cases_processed"]}')
        logger.info(f'Spider run state: {self.status.name}')
        logger.info(f'Number of slices complete: {sum(x.status == NodeStatus.COMPLETE for x in self.slices)}/{len(self.slices)}')


class SearchNode:
    def __init__(self, range_start_date, range_end_date, search_string=None, parent=None, spider=None):
        # Slice search parameters
        self.range_start_date = range_start_date
        self.range_end_date = range_end_date
        self.search_string = search_string

        # Stateful attributes
        self.status = NodeStatus.NEW
        self.error = None
        self.parent = parent
        self.spider = spider
        self.timestamp = None
        self.results = {
            'query_seconds': 0.0,
            'cases_returned': 0,
            'distinct_cases': 0,
            'cases_added': 0,
            'requests': 0,
            'total_cases_added': 0,
            'total_cases_processed': 0,
            'total_requests': 0
        }
        self.children = []
    
    @classmethod
    def load(cls, parent, spider, state_dict):
        if state_dict['_type'] != cls.__name__:
            raise Exception('Invalid SearchNode state')
        # Only fetch full state from S3 for in-progress root nodes
        if not parent and NodeStatus[state_dict['status']] == NodeStatus.IN_PROGRESS:
            assert not parent
            logger.info(f'Loading state from {state_dict["s3"]}')
            s3_obj = config.spider_runs_bucket.Object(state_dict["s3"]).get()
            state_dict = json.load(s3_obj['Body'])
        node = cls(
            range_start_date=datetime.strptime(state_dict['range_start_date'], '%m/%d/%Y'),
            range_end_date=datetime.strptime(state_dict['range_end_date'], '%m/%d/%Y'),
            search_string=state_dict.get('search_string'),
            parent=parent,
            spider=spider
        )
        node.status = NodeStatus[state_dict['status']]
        node.error = state_dict['error']
        node.results = state_dict['results']
        node.timestamp = datetime.fromisoformat(state_dict['timestamp']) if state_dict['timestamp'] else None
        # Only load children for non-root nodes or in-progress root nodes
        if parent or node.status == NodeStatus.IN_PROGRESS:
            node.children = [ SearchNode.load(node, spider, child) for child in state_dict['children'] ]
        return node

    @property
    def __dict__(self):
        return {
            'id': self.id,
            '_type': type(self).__name__,
            'range_start_date': self.range_start_date.strftime('%m/%d/%Y'),
            'range_end_date': self.range_end_date.strftime('%m/%d/%Y'),
            'search_string': self.search_string,
            'status': self.status.name,
            'error': self.error,
            'results': self.results,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'children': [ child.__dict__ for child in self.children ]
        }

    @property
    def id(self):
        ''' ID is deterministic based on concatenation of search parameters '''
        if not hasattr(self,'_id'):
            self._id = f'{self.range_start_date.strftime("%Y-%m-%d")}/{self.range_end_date.strftime("%Y-%m-%d")}'
            if self.spider.court:
                self._id += '/' + self.spider.court
            if self.spider.site:
                self._id += '/' + self.spider.site
            if self.search_string:
                self._id = f'{self.search_string}/{self._id}'
        return self._id
    
    @property
    def s3_key(self):
        if self.timestamp:
            return f'{self.id}/{self.timestamp.isoformat()}'
        return 's3://'

    def is_root(self):
        return not self.parent and not self.search_string

    def export(self):
        assert self.is_root()
        return {
            'id': self.id,
            '_type': type(self).__name__,
            'range_start_date': self.range_start_date.strftime('%m/%d/%Y'),
            'range_end_date': self.range_end_date.strftime('%m/%d/%Y'),
            'status': self.status.name,
            'error': self.error,
            'results': self.results,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            's3': self.s3_key
        }
    
    def save(self):
        assert self.is_root()
        s3_obj = config.spider_runs_bucket.put_object(
            Body = json.dumps(self.__dict__, cls=JSONDatetimeEncoder).encode('utf-8'),
            Key = self.s3_key,
            Metadata = {
                'run_timestamp': self.spider.timestamp.isoformat()
            }
        )
        logger.debug(f'Size of saved state: {s3_obj.content_length}')

    async def start(self, session_pool, callback):
        assert self.is_root()
        if self.status == NodeStatus.COMPLETE:
            logger.debug(f'Root node complete: {self.id}')
            return
        elif self.status == NodeStatus.FAILED:
            logger.debug(f'Root node failed: {self.id}')
            return
        elif self.status == NodeStatus.TIME_RANGE_SPLIT:
            logger.debug(f'Root node time range split: {self.id}')
            return
        elif self.status == NodeStatus.NEW:
            logger.debug(f'Root node start search: {self.id}')
            self.timestamp = datetime.now()
            for char in self.spider.search_chars.replace(' ',''): # don't start queries with a space
                self.children.append(
                    SearchNode(
                        range_start_date=self.range_start_date,
                        range_end_date=self.range_end_date,
                        search_string=char,
                        parent=self,
                        spider=self.spider
                    )
                )
            self.status = NodeStatus.IN_PROGRESS
        elif self.status == NodeStatus.IN_PROGRESS:
            logger.debug(f'Root node resume search: {self.timestamp.isoformat()}/{self.id}')
            if not self.children:
                self.__spawn_children()

        # Start children and state manager
        try:
            async with trio.open_nursery() as nursery:
                for node in self.children:
                    nursery.start_soon(node.__start_child, session_pool, nursery)
                nursery.start_soon(self.__state_manager, nursery)
            self.status = NodeStatus.COMPLETE
        except:
            raise
        finally:    
            self.save()
            self.__log_results()
            
        logger.debug(f'Root node completed: {self.id}')
        callback()

    async def __start_child(self, session_pool, nursery):
        if self.status == NodeStatus.COMPLETE:
            logger.debug(f'Node complete: {self.id}')
            return
        elif self.status == NodeStatus.FAILED:
            logger.debug(f'Node failed: {self.id}')
            return
        elif self.status == NodeStatus.TIME_RANGE_SPLIT:
            logger.debug(f'Node time range split: {self.id}')
            return
        elif self.status == NodeStatus.NEW:
            await self.__search(session_pool)
            self.status = NodeStatus.IN_PROGRESS
        elif self.status == NodeStatus.IN_PROGRESS:
            logger.debug(f'Node resume search: {self.timestamp.isoformat()}/{self.id}')
            if self.results['cases_returned'] == 500 and not self.children:
                self.__spawn_children()

        # Start children
        for node in self.children:
            nursery.start_soon(node.__start_child, session_pool, nursery)
        self.status = NodeStatus.COMPLETE
        self.__propagate_results()

    async def __state_manager(self, nursery):
        ''' Periodically save state '''
        logger.debug('Root node state manager initiating')
        last_update = datetime.now()
        while True:
            await trio.sleep(5)
            now = datetime.now()
            if len(nursery.child_tasks) == 1:
                logger.debug('Root node state manager terminating')
                return
            if (now - last_update).total_seconds() > config.SPIDER_UPDATE_FREQUENCY:
                last_update = now
                logger.debug('Updating root node state')
                self.save()

    def __spawn_children(self):
        if self.children:
            return
        # trailing spaces are trimmed, so <searh_string + ' '> will return same results as <search_string>.
        for char in self.spider.search_chars.replace(' ',''):
            self.children.append(
                SearchNode(
                    range_start_date=self.range_start_date,
                    range_end_date=self.range_end_date,
                    search_string=self.search_string + char,
                    parent=self,
                    spider=self.spider
                )
            )
            self.children.append(
                SearchNode(
                    range_start_date=self.range_start_date,
                    range_end_date=self.range_end_date,
                    search_string=self.search_string + ' ' + char,
                    parent=self,
                    spider=self.spider
                )
            )

    async def __search(self, session_pool):
        query_params = {
            'lastName':self.search_string,
            'countyName':self.spider.court,
            'site':self.spider.site,
            'company':'N',
            'filingStart':self.range_start_date.strftime("%-m/%-d/%Y"),
            'filingEnd':self.range_end_date.strftime("%-m/%-d/%Y")
        }

        session = await session_pool.get()
        logger.debug(f"Searching for {self.id}")
        self.timestamp = datetime.now()
        rows = await self.__get_results(session, query_params)
        self.results['query_seconds'] = delta_seconds(self.timestamp)
        session_pool.put_nowait(session)
        if not rows:
            return

        logger.debug(f"Search string {self.search_string} returned {len(rows)} items, took {self.results['query_seconds']} seconds")

        # Process results
        processed_cases = {}
        for row in rows:
            elements = row.find_all('td')
            try:
                case_number = elements[0].a.string
            except:
                self.error = 'Error parsing result rows'
                self.status = NodeStatus.FAILED
                return
            if not processed_cases.get(case_number): # case numbers can appear multiple times in results
                case_url = elements[0].a['href']
                url_components = re.search("loc=(\d+)&detailLoc=([A-Z\d]+)$", case_url)
                loc = url_components.group(1)
                detail_loc = url_components.group(2)
                if elements[7].string:
                    try:
                        filing_date = datetime.strptime(elements[7].string,"%m/%d/%Y")
                    except:
                        filing_date = None
                else:
                    filing_date = None
                case = Case(
                    case_number = case_number,
                    court = elements[4].string,
                    case_type = elements[5].string,
                    status = elements[6].string,
                    filing_date = filing_date,
                    filing_date_original = elements[7].string,
                    caption = elements[8].string,
                    query_court = self.spider.court,
                    loc = loc,
                    detail_loc = detail_loc,
                    url = case_url
                )
                processed_cases[case_number] = case
        
        new_cases = []
        with db_session() as db:
            # See which cases need to be added to DB
            existing_cases = db.query(Case.case_number).filter(Case.case_number.in_(list(processed_cases.keys()))).all()
            existing_cases = [x[0] for x in existing_cases]
            new_case_numbers = set(processed_cases.keys()) - set(existing_cases)
            new_cases = [processed_cases[x] for x in new_case_numbers]

            # Save new cases to database
            db.bulk_save_objects(new_cases)

            # Then send them to the scraper queue
            entries = []
            for idx, case in enumerate(new_cases):
                entries.append({
                    'Id': str(idx),
                    'MessageBody': json.dumps({
                        'case_number': case.case_number,
                        'loc': case.loc,
                        'detail_loc': case.detail_loc
                    })
                })
            for chunk in chunks(entries, 10):  # SQS limit of 10/request
                config.scraper_queue.send_messages(Entries=chunk)
            
        if len(new_cases) > 0:
            logger.debug(f"{self.id} added {len(new_cases)} new cases")
        self.results['cases_returned'] = len(rows)
        self.results['distinct_cases'] = len(processed_cases)
        self.results['cases_added'] = len(new_cases)
        self.status = NodeStatus.IN_PROGRESS

        if len(rows) == 500:
            # Procreate!
            self.__spawn_children()

    async def __get_results(self, session, query_params):
        try:
            response_html = await self.__query_mjcs(
                session,
                url = 'http://casesearch.courts.state.md.us/casesearch/inquirySearch.jis',
                method = 'POST',
                post_params = query_params,
                xml = False
            )
        except FailedSearchTimeout:
            self.__split()
            self.status = NodeStatus.TIME_RANGE_SPLIT
            return
        except CompletedSearchNoResults:
            self.status = NodeStatus.COMPLETE
            return
        except FailedSearch as e:
            self.status = NodeStatus.FAILED
            self.error = f'{type(e).__name__}: {e}'
            return

        # Parse HTML
        html = BeautifulSoup(response_html.text,'html.parser')
        results_table = html.find('table',class_='results',id='row')
        if not results_table:  # Sanity check
            err_msg = 'Error finding results table in returned HTML'
            self.error = err_msg
            self.status = NodeStatus.FAILED
            return
        rows = list(results_table.tbody.find_all('tr'))
        
        # Paginate through results if needed
        while html.find('span',class_='pagelinks').find('a',string='Next'):
            try:
                response_html = await self.__query_mjcs(
                    session,
                    url = 'http://casesearch.courts.state.md.us' + html.find('span',class_='pagelinks').find('a',string='Next')['href'],
                    method = 'GET'
                )
            except FailedSearch as e:
                self.status = NodeStatus.FAILED
                self.error = f'{type(e).__name__}: {e}'
                return
            html = BeautifulSoup(response_html.text,'html.parser')
            try:
                for row in html.find('table',class_='results',id='row').tbody.find_all('tr'):
                    rows.append(row)
            except:
                err_msg = 'Error parsing results table'
                self.status = NodeStatus.FAILED
                self.error = err_msg
                return
        return rows

    async def __query_mjcs(self, session, url, method='POST', post_params={}, xml=False):
        if xml:
            post_params['d-16544-e'] = 3
        try:
            self.results['requests'] += 1
            response = await session.request(
                method=method,
                url=url,
                data=post_params,
                max_redirects=1
            )
        except asks.errors.RequestTimeout:
            raise FailedSearchTimeout

        if response.status_code == 500:
            logger.debug(f"Received 500 error: {self.id}")
            raise FailedSearch500Error(response.text)
        elif response.status_code != 200:
            logger.warning(f"Unknown error. response code: {response.status_code}, response body: {response.text}")
            raise FailedSearchUnknownError(f'Response status code {response.status_code}, body {response.text}')
        elif 'text/html' in response.headers['Content-Type'] \
                and re.search(r'<span class="error">\s*<br>CaseSearch will only display results',response.text):
            # logger.debug("No cases for search string %s starting on %s" % (self.search_string,self.range_start_date.strftime("%-m/%-d/%Y")))
            raise CompletedSearchNoResults
        elif 'text/html' in response.headers['Content-Type'] \
                and re.search(r'<span class="error">\s*<br>Sorry, but your query has timed out after 2 minute',response.text):
            logger.warning(f"MJCS Query Timeout: {self.id}")
            raise FailedSearchTimeout
        elif 'text/html' in response.headers['Content-Type'] and 'Case Search is temporarily unavailable' in response.text:
            logger.warning(f"MJCS Unavailable error: {self.id}")
            raise FailedSearchUnavailable

        return response  

    def __split(self):
        logger.debug(f'Splitting date range {self.id}')
        range1, range2 = split_date_range(self.range_start_date, self.range_end_date)
        self.spider.append_slices([
            {
                'search_string': self.search_string,
                'range_start_date': range1[0],
                'range_end_date': range1[1]
            },
            {
                'search_string': self.search_string,
                'range_start_date': range2[0],
                'range_end_date': range2[1]
            }
        ])
    
    def __propagate_results(self):
        self.results['total_cases_added'] = self.results['cases_added']
        self.results['total_cases_processed'] = self.results['distinct_cases']
        self.results['total_requests'] = self.results['requests']

        # Propagate up the tree
        node = self
        while node.parent:
            node.parent.results['total_cases_added'] += self.results['cases_added']
            node.parent.results['total_cases_processed'] += self.results['distinct_cases']
            node.parent.results['total_requests'] += self.results['requests']
            node = node.parent
    
    def __log_results(self):
        logger.info(f'ROOT SEARCH NODE RESULTS')
        logger.info(f'Search criteria: {self.range_start_date.strftime("%m/%d/%Y")} - {self.range_end_date.strftime("%m/%d/%Y")} / Court: {self.spider.court} / Site: {self.spider.site}')
        logger.info(f'Node started at {self.timestamp}')
        logger.info(f'Node finished at {datetime.now().isoformat()}')
        logger.info(f'Total requests sent: {self.results["total_requests"]}')
        logger.info(f'Total new cases added: {self.results["total_cases_added"]}')
        logger.info(f'Total cases processed: {self.results["total_cases_processed"]}')
        logger.info(f'Node state: {self.status.name}')