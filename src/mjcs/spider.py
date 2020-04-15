from .config import config
from .util import db_session, split_date_range, chunks, float_to_decimal, decimal_to_float, JSONDatetimeEncoder
from .models import Case
from .session import AsyncSession
import trio
import asks
from sqlalchemy.dialects.postgresql import insert
from bs4 import BeautifulSoup, SoupStrainer
from datetime import datetime, timedelta
from boto3.dynamodb.conditions import Key
import re
import string
import xml.etree.ElementTree as ET
import h11
import json
import os
import logging
from functools import reduce
from botocore.exceptions import ClientError

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

class CompletedSearchNoResults(Exception):
    pass

class SpiderStatus:
    NEW = 1
    IN_PROGRESS = 2
    COMPLETE = 3
    CANCELED = 4
    FAILED = 5

class NodeStatus:
    NEW = 1
    IN_PROGRESS = 2
    COMPLETE = 3
    TIME_RANGE_SPLIT = 4
    FAILED = 5


class Spider:
    '''Main spider class'''

    def __init__(self, query_start_date, query_end_date, court=None, site=None, concurrency=None):
        # Spider paraemeters
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

        # Set up concurrency
        self.concurrency = concurrency or config.SPIDER_DEFAULT_CONCURRENCY
        asks.init('trio')
        self.session_pool = trio.Queue(self.concurrency)
        for _ in range(self.concurrency):
            self.session_pool.put_nowait(AsyncSession())

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
        spider.status = state_dict['status']
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
        # assert self.timestamp
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
            'slices': [ slice.__dict__ for slice in self.slices ],
            'results': self.results,
            'status': self.status,
        }

    @property
    def id(self):
        ''' ID is deterministic based on concatenation of search parameters '''
        if not hasattr(self,'_id'):
            self._id = f'spider/{self.query_start_date.strftime("%m-%d-%Y")}'
            if self.query_end_date:
                self._id += '/' + self.query_end_date.strftime("%m-%d-%Y")
            if self.court:
                self._id += '/' + self.court
            if self.site:
                self._id += '/' + self.site
        return self._id
    
    def start(self):
        if self.status == SpiderStatus.COMPLETE:
            logger.warning('Spider is in complete state, cannot start.')
            return
        elif self.status == SpiderStatus.NEW:
            self.__generate_slices()
            logger.info(f"Starting spider run: {self.query_start_date.date().isoformat()}/{self.query_end_date.date().isoformat()}/{self.court}/{self.site}")
            self.status = SpiderStatus.IN_PROGRESS
        elif self.status == SpiderStatus.IN_PROGRESS or self.status == SpiderStatus.CANCELED or self.status == SpiderStatus.FAILED:
            logger.info(f"Resuming previous spider run: {self.timestamp.isoformat()}/{self.query_start_date.date().isoformat()}/{self.query_end_date.date().isoformat()}/{self.court}/{self.site}")
            self.status == SpiderStatus.IN_PROGRESS

        self.timestamp = datetime.now()
        logger.info(f"Run timestamp: {self.timestamp.isoformat()}")
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
        try:
            # Block until all search nodes are complete or exception occurs
            async with trio.open_nursery() as nursery:
                for node in self.slices:
                    nursery.start_soon(node.start, self.session_pool, nursery)
                nursery.start_soon(self.__state_manager, nursery)
        except KeyboardInterrupt:
            print("\nCaught KeyboardInterrupt: saving spider run...")
            self.status = SpiderStatus.CANCELED
        except:
            self.status = SpiderStatus.FAILED
            raise
        else:
            self.status = SpiderStatus.COMPLETE
        finally:
            self.__save_run()
            self.__log_results()
        logger.info("Spider run complete")

    async def __state_manager(self, nursery):
        logger.debug('State manager initiating')
        last_update = datetime.now()
        while True:
            await trio.sleep(5)
            now = datetime.now()
            if len(nursery.child_tasks) == 1:
                logger.debug('State manager terminating')
                return
            if (now - last_update).total_seconds() > config.SPIDER_UPDATE_FREQUENCY:
                last_update = now
                logger.debug('Updating state')
                self.__save_run()

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

    def __append_slices(self, slices):
        self.slices += [
            SearchNode(
                range_start_date=slice['range_start_date'],
                range_end_date=slice['range_end_date'],
                search_string=slice['search_string'],
                parent=None,
                spider=self
            ) for slice in slices 
        ]
        
    def __save_run(self):
        logger.debug('Saving run.')
        self.results['run_seconds'] = delta_seconds(self.timestamp)
        self.__calculate_results()
        run = {
            'id': self.id,
            'timestamp': self.timestamp.isoformat(),
            'state': self.__dict__
        }

        try:
            config.spider_table.put_item(Item=float_to_decimal(run))
        except ClientError:
            logger.debug('State too large for DynamoDB, saving in S3')
            # Upload state to S3
            key = f'{self.id}/{self.timestamp.isoformat()}'
            run_obj = config.spider_runs_bucket.put_object(
                Body = json.dumps(self.__dict__, cls=JSONDatetimeEncoder).encode('utf-8'),
                Key = key,
                Metadata = {
                    'run_timestamp': self.timestamp.isoformat()
                }
            )
            logger.debug(f'Size of saved state object: {run_obj.content_length}')
            run['state'] = f's3://{config.SPIDER_RUNS_BUCKET_NAME}/{key}'
            config.spider_table.put_item(Item=float_to_decimal(run))

    def __load_run(self, run_datetime=None):
        if run_datetime:
            item = config.spider_table.get_item(Key={
                'id': self.id,
                'timestamp': run_datetime.isoformat()
            })
            run = decimal_to_float(item['Item'])
        else:
            item = config.spider_table.query(
                KeyConditionExpression=Key('id').eq(self.id),
                ScanIndexForward=False,
                Limit=1
            )
            run = decimal_to_float(item['Items'][0])

        if isinstance(run['state'], str) and run['state'][:5] == 's3://':
            logger.info('Loading state from {}'.format(run['state']))
            key = '{}/{}'.format(self.id, run['timestamp'])
            s3_obj = config.spider_runs_bucket.Object(key).get()
            state_dict = json.load(s3_obj['Body'])
        else:
            state_dict = run['state']
        return state_dict

    def __calculate_results(self):
        self.results['total_cases_added'] = self.results['total_cases_processed'] = self.results['total_requests'] = 0
        for slice in self.slices:
            self.results['total_cases_added'] += slice.results['total_cases_added']
            self.results['total_cases_processed'] += slice.results['total_cases_processed']
            self.results['total_requests'] += slice.results['total_requests']
    
    def __log_results(self):
        logger.info(f'SPIDER RESULTS FOR RUN {self.timestamp.isoformat()}')
        logger.info(f'Search criteria: {self.query_start_date.isoformat()} - {self.query_end_date.isoformat()} / Court: {self.court} / Site: {self.site}')
        logger.info('Run finished at ' + (self.timestamp + timedelta(seconds=float(self.results['run_seconds']))).isoformat())
        logger.info('Run duration: %f seconds' % self.results['run_seconds'])
        logger.info('Total requests sent: %d' % self.results['total_requests'])
        logger.info('Total new cases added: %d' % self.results['total_cases_added'])
        logger.info('Total cases processed: %d' % self.results['total_cases_processed'])
        if self.status == SpiderStatus.COMPLETE:
            logger.info('Spider run state: COMPLETE')
        elif self.status == SpiderStatus.FAILED:
            logger.info('Spider run state: FAILED')
        elif self.status == SpiderStatus.CANCELED:
            logger.info('Spider run state: CANCELED')
        else:
            logger.info(f'Spider run state: {self.status}')


class SearchNode:
    def __init__(self, range_start_date, range_end_date, search_string=None, parent=None, spider=None):
        self.range_start_date = range_start_date
        self.range_end_date = range_end_date
        self.search_string = search_string
        self.status = NodeStatus.NEW
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
        node = cls(
            range_start_date=datetime.strptime(state_dict['range_start_date'], '%m/%d/%Y'),
            range_end_date=datetime.strptime(state_dict['range_end_date'], '%m/%d/%Y'),
            search_string=state_dict['search_string'],
            parent=parent,
            spider=spider
        )
        node.status = state_dict['status']
        node.results = state_dict['results']
        node.timestamp = datetime.fromisoformat(state_dict['timestamp']) if state_dict['timestamp'] else None
        node.children = [ SearchNode.load(node, spider, child) for child in state_dict['children'] ]
        return node

    @property
    def __dict__(self):
        return {
            '_type': type(self).__name__,
            'range_start_date': self.range_start_date.strftime('%m/%d/%Y'),
            'range_end_date': self.range_end_date.strftime('%m/%d/%Y'),
            'search_string': self.search_string,
            'status': self.status,
            'results': self.results,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'children': [ child.__dict__ for child in self.children ]
        }
    
    async def start(self, session_pool, nursery):
        if self.status == NodeStatus.FAILED:
            logger.debug(f'Node failed: {self.range_start_date.date().isoformat()}/{self.range_end_date.date().isoformat()}')
            return
        elif self.status == NodeStatus.TIME_RANGE_SPLIT:
            logger.debug(f'Node time range split: {self.range_start_date.date().isoformat()}/{self.range_end_date.date().isoformat()}')
            return
        elif self.status == NodeStatus.NEW:
            # logger.debug(f'Node start search: {self.range_start_date.date().isoformat()}/{self.range_end_date.date().isoformat()}')
            if self.parent:
                await self.__search(session_pool)
            else:  # Root node
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
            logger.debug(f'Node resume search: {self.range_start_date.date().isoformat()}/{self.range_end_date.date().isoformat()}')
            if self.results['cases_returned'] == 500 and not self.children:
                self.__spawn_children()

        # Start children
        for node in self.children:
            nursery.start_soon(node.start, session_pool, nursery)
        self.status = NodeStatus.COMPLETE
        self.__propagate_results()
        # logger.debug(f'Node completed: {self.range_start_date.date().isoformat()}/{self.range_end_date.date().isoformat()}')
    
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
        session = await session_pool.get()

        self.timestamp = datetime.now()
        logger.debug("Searching for %s on start date %s" % (self.search_string, self.range_start_date.strftime("%-m/%-d/%Y")))
        query_params = {
            'lastName':self.search_string,
            'countyName':self.spider.court,
            'site':self.spider.site,
            'company':'N',
            'filingStart':self.range_start_date.strftime("%-m/%-d/%Y"),
            'filingEnd':self.range_end_date.strftime("%-m/%-d/%Y")
        }

        try:
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
                raise
            except CompletedSearchNoResults:
                self.status = NodeStatus.COMPLETE
                raise
            except FailedSearch:
                self.status = NodeStatus.FAILED
                raise

            # Parse HTML
            html = BeautifulSoup(response_html.text,'html.parser')
            results_table = html.find('table',class_='results',id='row')
            if not results_table:  # Sanity check
                logger.error('Error finding results table in returned HTML')
                self.status = NodeStatus.FAILED
                raise FailedSearchUnknownError
            rows = list(results_table.tbody.find_all('tr'))
            
            # Paginate through results if needed
            while html.find('span',class_='pagelinks').find('a',string='Next'):
                try:
                    response_html = await self.__query_mjcs(
                        session,
                        url = 'http://casesearch.courts.state.md.us' + html.find('span',class_='pagelinks').find('a',string='Next')['href'],
                        method = 'GET'
                    )
                except FailedSearch:
                    self.status = NodeStatus.FAILED
                    raise
                html = BeautifulSoup(response_html.text,'html.parser')
                try:
                    for row in html.find('table',class_='results',id='row').tbody.find_all('tr'):
                        rows.append(row)
                except:
                    self.status = NodeStatus.FAILED
                    raise FailedSearchUnknownError
        except (FailedSearch, CompletedSearchNoResults):
            await session_pool.put(session)
            return
        finally:
            self.results['query_seconds'] = delta_seconds(self.timestamp)

        await session_pool.put(session)
        logger.debug("Search string %s returned %d items, took %d seconds" % (self.search_string, len(rows), self.results['query_seconds']))

        # Process results
        processed_cases = {}
        for row in rows:
            elements = row.find_all('td')
            try:
                case_number = elements[0].a.string
            except:
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
            logger.info(f"{self.search_string}/{self.range_start_date.date().isoformat()}/{self.range_end_date.date().isoformat()} added {len(new_cases)} new cases")
        self.results['cases_returned'] = len(rows)
        self.results['distinct_cases'] = len(processed_cases)
        self.results['cases_added'] = len(new_cases)
        self.status = NodeStatus.IN_PROGRESS

        if 'The result set exceeds the limit of 500 records' in response_html.text or len(rows) == 500:
            # Procreate!
            self.__spawn_children()

    async def __query_mjcs(self, session, url, method='POST', post_params={}, xml=False):
        if xml:
            post_params['d-16544-e'] = 3
        retry = True
        while True:
            try:
                self.results['requests'] += 1
                response = await session.request(
                    method,
                    url,
                    data = post_params,
                    max_redirects = 1
                )
            except asks.errors.RequestTimeout:
                raise FailedSearchTimeout
            except (asks.errors.BadHttpResponse, h11.RemoteProtocolError, trio.BrokenStreamError, OSError) as e:
                if retry:
                    retry = False
                    continue
                logger.warning(f"{str(e)}: {self.search_string}/{self.range_start_date.date().isoformat()}/{self.range_end_date.date().isoformat()}")
                raise FailedSearchUnknownError

            if response.history and response.history[0].status_code == 302:
                logger.debug("Received 302 redirect, renewing session...")
                await session.renew()
                continue  # try again
            elif response.status_code == 500:
                logger.debug(f"Received 500 error: {self.search_string}/{self.range_start_date.date().isoformat()}/{self.range_end_date.date().isoformat()}")
                raise FailedSearch500Error
            elif response.status_code != 200:
                logger.warning("Unknown error. response code: %s, response body: %s" % (response.status_code, response.text))
                raise FailedSearchUnknownError
            else:
                if 'text/html' in response.headers['Content-Type'] \
                        and re.search(r'<span class="error">\s*<br>CaseSearch will only display results',response.text):
                    logger.debug("No cases for search string %s starting on %s" % (self.search_string,self.range_start_date.strftime("%-m/%-d/%Y")))
                    raise CompletedSearchNoResults
                elif 'text/html' in response.headers['Content-Type'] \
                        and re.search(r'<span class="error">\s*<br>Sorry, but your query has timed out after 2 minute',response.text):
                    logger.warning(f"MJCS Query Timeout: {self.search_string}/{self.range_start_date.date().isoformat()}/{self.range_end_date.date().isoformat()}")
                    raise FailedSearchTimeout

            return response

    def __split(self):
        logger.debug(f'Splitting date range {self.search_string}/{self.range_start_date.date().isoformat()}/{self.range_end_date.date().isoformat()}')
        range1, range2 = split_date_range(self.range_start_date, self.range_end_date)
        self.spider.__append_slices([
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
        if self.parent:
            self.parent.results['total_cases_added'] += self.results['cases_added']
            self.parent.results['total_cases_processed'] += self.results['distinct_cases']
            self.parent.results['total_requests'] += self.results['requests']