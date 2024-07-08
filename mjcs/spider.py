import json
import logging
import re
import string
import xml.etree.ElementTree as ElementTree
from datetime import datetime, timedelta

import trio
from bs4 import BeautifulSoup
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from .config import config
from .models import Case
from .session import AsyncSessionPool, Forbidden
from .util import db_session, send_to_queue, split_date_range

logger = logging.getLogger('mjcs')

# searching for underscore character leads to timeout for some reason
# % is a wildcard character
search_chars = string.ascii_uppercase \
    + string.digits \
    + string.punctuation.replace('_','').replace('%','') \
    + ' '

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


def generate_spider_slices(range_start_date, range_end_date=datetime.now(), court=None, site=None):
    def gen_timeranges(start_date, end_date):
        for n in range(0,int((end_date - start_date).days),config.SPIDER_DAYS_PER_QUERY):
            start = start_date + timedelta(n)
            end = start_date + timedelta(n) + timedelta(config.SPIDER_DAYS_PER_QUERY - 1)
            if end > end_date:
                end = end_date
            if start == end:
                end = start
            yield (start,end)
    
    slices = []
    for (start,end) in gen_timeranges(range_start_date, range_end_date):
        for char1 in search_chars.replace(' ',''): # don't start queries with a space
            for char2 in search_chars: # don't start queries with a space
                slices.append(
                    json.dumps({
                        'range_start_date': start.isoformat(),
                        'range_end_date': end.isoformat(),
                        'court': court,
                        'site': site,
                        'search_string': f'{char1}{char2}',
                    })
                )
    
    logger.info(f'Submitting {len(slices)} slices for spidering')
    send_to_queue(config.spider_queue, slices)


class Spider:
    def __init__(self, concurrency=1):
        self.concurrency = concurrency
        self.session_pool = AsyncSessionPool(concurrency)
    
    def spider_from_queue(self, forever=False):
        trio.run(self.__start_service, forever)

    async def __start_service(self, forever):
        logger.info('Initiating spider service.')
        try:
            # Blocks until all child tasks finish or exception thrown
            async with trio.open_nursery() as nursery:
                nursery.start_soon(self.__queue_manager, nursery, forever)
        except KeyboardInterrupt:
            print("\nCaught KeyboardInterrupt: stopping service.")
        logger.info("Spider service stopped.")

    async def __queue_manager(self, nursery, forever):
        while True:
            if len(nursery.child_tasks) < 100:
                queue_items = config.spider_queue.receive_messages(
                    WaitTimeSeconds = config.QUEUE_WAIT,
                    MaxNumberOfMessages = 10
                )
                if queue_items:
                    for item in queue_items:
                        body = json.loads(item.body)
                        range_start_date = datetime.fromisoformat(body['range_start_date'])
                        range_end_date = datetime.fromisoformat(body['range_end_date'])
                        search_string = body['search_string']
                        court = body.get('court')
                        site = body.get('site')
                        node = SearchNode(
                            self.session_pool,
                            range_start_date,
                            range_end_date,
                            search_string,
                            court,
                            site,
                            ignore_on_conflict=self.concurrency > 1
                        )
                        nursery.start_soon(node.search)
                        item.delete()
                else:
                    logger.info('No items in spider queue.')
                    if not forever:
                        break
                    await trio.sleep(5 * 60)
            else:
                await trio.sleep(5)


class SearchNode:    
    def __init__(self, session_pool, range_start_date, range_end_date, search_string, court=None, site=None, ignore_on_conflict=False):
        self.session_pool = session_pool
        self.range_start_date = range_start_date
        self.range_end_date = range_end_date
        self.court = court
        self.site = site
        self.search_string = search_string
        self.ignore_on_conflict = ignore_on_conflict

    @property
    def id(self):
        id = f'{self.range_start_date.strftime("%Y-%m-%d")}/{self.range_end_date.strftime("%Y-%m-%d")}'
        if self.court:
            id += '/' + self.court
        if self.site:
            id += '/' + self.site
        id = f'{id}/{self.search_string}'
        return id

    async def search(self, i=1):
        if i > 2:
            logger.error('Too many retried searches after XML parsing error')
            if len(self.search_string) <= 15:
                self.__spawn_children()
            elif self.range_start_date != self.range_end_date:
                self.__split()
            return
        
        session = await self.session_pool.get()
        try:
            response = await self.__get_results(session)
        except FailedSearchTimeout:
            if len(self.search_string) <= 15:
                self.__spawn_children()
            elif self.range_start_date != self.range_end_date:
                self.__split()
            return
        except CompletedSearchNoResults:
            return
        finally:
            self.session_pool.put_nowait(session)
        
        # Parse XML
        try:
            root = ElementTree.fromstring(response.text)
        except ElementTree.ParseError as e:
            if 'DATA NOT FOUND' not in response.text:
                logger.warning(f'Failed to parse XML: {e}')
                return await self.search(i=i+1)
            return

        rows = [[element.text for element in row] for row in root]

        # Process results
        processed_cases = {}
        for row in rows:
            case_number = row[0]
            if not processed_cases.get(case_number): # case numbers can appear multiple times in results
                if row[7]:
                    try:
                        filing_date = datetime.strptime(row[7],"%m/%d/%Y")
                    except:
                        filing_date = None
                else:
                    filing_date = None
                case = {
                    'case_number': row[0],
                    'court': row[4],
                    'case_type': row[5],
                    'status': row[6],
                    'filing_date': filing_date,
                    'filing_date_original': row[7],
                    'caption': row[8],
                    'query_court': self.court,
                    'detail_loc': 'Unknown'
                }
                processed_cases[case_number] = case
        logger.debug(f"Search string {self.search_string} returned {len(rows)} items ({len(processed_cases)} unique)")

        new_cases = []
        with db_session() as db:
            # See which cases need to be added to DB
            existing_cases = db.scalars(
                select(Case.case_number)
                .where(Case.case_number.in_(processed_cases.keys()))
            ).all()
            new_case_numbers = set(processed_cases.keys()) - set(existing_cases)
            new_cases = [processed_cases[x] for x in new_case_numbers]

            if len(new_cases) > 0:
                # Save new cases to database
                stmt = insert(Case).values(new_cases)
                if self.ignore_on_conflict:
                    stmt = stmt.on_conflict_do_nothing()
                db.execute(stmt)

                # Then send them to the scraper queue
                messages = [
                    json.dumps({
                        'case_number': case['case_number'],
                        'detail_loc': case['detail_loc'],
                        'loc': case.get('loc')
                    }) for case in new_cases
                ]
                send_to_queue(config.scraper_queue, messages)
                
                logger.info(f"{self.id} added {len(new_cases)} new cases")
        
        if len(rows) == 500:
            # Procreate!
            if len(self.search_string) <= 15:
                self.__spawn_children()
            elif self.range_start_date != self.range_end_date:
                self.__split()
        
        return len(new_cases)

    async def __get_results(self, session):
        response = await session.request(
            method='GET',
            url = f'{config.MJCS_BASE_URL}/inquiry-search.jsp',
            headers = {'Referer': f'{config.MJCS_BASE_URL}/'}
        )

        if response.status_code == 403:
            raise Forbidden
        elif response.status_code != 200:
            logger.warning("Failed to retrieve search page")
            raise FailedSearchUnknownError(response.text)
        soup = BeautifulSoup(response.text, 'html.parser')

        try:
            search_type = soup.find('input',{'name':'searchtype'}).get('value')
        except AttributeError:
            logger.warning("Failed to find searchtype input in search page")
            raise FailedSearchUnknownError

        query_params = {
            'lastName':self.search_string + '%',
            # 'firstName': '%',
            'company':'N',
            'filingStart':self.range_start_date.strftime("%-m/%-d/%Y"),
            'filingEnd':self.range_end_date.strftime("%-m/%-d/%Y"),
            'd-16544-e': 3,  # XML
            'searchtype': search_type
        }
        if self.court:
            query_params['countyName'] = self.court
        if self.site:
            query_params['site'] = self.site
        
        logger.debug(f'Searching for {self.id}')
        response = await session.request(
            method='POST',
            url=f'{config.MJCS_BASE_URL}/inquirySearch.jis',
            data=query_params,
            headers = {'Referer': f'{config.MJCS_BASE_URL}/inquiry-search.jsp'}
        )

        if response.status_code == 403:
            raise Forbidden
        elif response.status_code == 500:
            logger.warning(f"Received 500 error: {self.id}")
            raise FailedSearch500Error(response.text)
        elif response.status_code != 200:
            logger.warning(f"Unknown error. response code: {response.status_code}, response body: {response.text}")
            raise FailedSearchUnknownError(f'Response status code {response.status_code}, body {response.text}')
        elif ('text/html' in response.headers['Content-Type'] and
                re.search(r'<span class="error">\s*<br>CaseSearch will only display results',response.text)):
            # logger.debug("No cases for search string %s starting on %s" % (self.search_string,self.range_start_date.strftime("%-m/%-d/%Y")))
            raise CompletedSearchNoResults
        elif ('text/html' in response.headers['Content-Type'] and
                re.search(r'<span class="error">\s*<br>Sorry, but your query has timed out after 2 minute',response.text)):
            logger.warning(f"MJCS Query Timeout: {self.id}")
            raise FailedSearchTimeout
        elif 'text/html' in response.headers['Content-Type'] and 'Case Search is temporarily unavailable' in response.text:
            logger.warning(f"MJCS Unavailable error: {self.id}")
            raise FailedSearchUnavailable
        elif ('text/html' in response.headers['Content-Type'] and
                re.search(r'<span class="error">\s*<br>Invalid Search Criteria!',response.text)):
            raise CompletedSearchNoResults

        return response

    def __spawn_children(self):
        slices = []

        # A few shortcuts to save time
        if self.search_string == 'PUBLIC DEF':
            slices.append(
                json.dumps({
                    'range_start_date': self.range_start_date.isoformat(),
                    'range_end_date': self.range_end_date.isoformat(),
                    'court': self.court,
                    'site': self.site,
                    'search_string': 'PUBLIC DEFENDER',
                })
            )
        elif self.search_string == 'STATE OF MAR':
            slices.append(
                json.dumps({
                    'range_start_date': self.range_start_date.isoformat(),
                    'range_end_date': self.range_end_date.isoformat(),
                    'court': self.court,
                    'site': self.site,
                    'search_string': 'STATE OF MARYLAND',
                })
            )
        elif self.search_string == "STATE'S ATT":
            slices.append(
                json.dumps({
                    'range_start_date': self.range_start_date.isoformat(),
                    'range_end_date': self.range_end_date.isoformat(),
                    'court': self.court,
                    'site': self.site,
                    'search_string': "STATE'S ATTORNEY",
                })
            )
        else:
            for char in search_chars.replace(' ',''): # don't start queries with a space
                slices.append(
                    json.dumps({
                        'range_start_date': self.range_start_date.isoformat(),
                        'range_end_date': self.range_end_date.isoformat(),
                        'court': self.court,
                        'site': self.site,
                        'search_string': self.search_string + char,
                    })
                )
                slices.append(
                    json.dumps({
                        'range_start_date': self.range_start_date.isoformat(),
                        'range_end_date': self.range_end_date.isoformat(),
                        'court': self.court,
                        'site': self.site,
                        'search_string': self.search_string + ' ' + char,
                    })
                )

        send_to_queue(config.spider_queue, slices)
        logger.info(f'Submitted {len(slices)} slices for spidering')

    def __split(self):
        if self.range_start_date == self.range_end_date:
            return
        logger.debug(f'Splitting date range {self.id}')
        range1, range2 = split_date_range(self.range_start_date, self.range_end_date)
        send_to_queue(config.spider_queue, [
            json.dumps({
                'range_start_date': range1[0].isoformat(),
                'range_end_date': range1[1].isoformat(),
                'court': self.court,
                'site': self.site,
                'search_string': self.search_string,
            }),
            json.dumps({
                'range_start_date': range2[0].isoformat(),
                'range_end_date': range2[1].isoformat(),
                'court': self.court,
                'site': self.site,
                'search_string': self.search_string,
            })
        ])
        