from .config import config
from .db import db_session, column_windows
from .search import SearchItem, active_count, active_items, clear_queue
from .case import Case
from .run import Run
from .session import AsyncSession
import boto3
import trio
import asks
from sqlalchemy.dialects.postgresql import insert
from bs4 import BeautifulSoup, SoupStrainer
from datetime import *
import re
import sys
import string
import xml.etree.ElementTree as ET
import h11
import json

sqs = boto3.resource('sqs')
scraper_queue = sqs.get_queue_by_name(QueueName=config.SCRAPER_QUEUE_NAME)

# TODO non-interactive option for lambda runs, via command line -y?
def prompt_continue(prompt):
    answer = input(prompt+' (y/N) ')
    if answer == 'n' or answer == 'N' or answer == '':
        print("Goodbye!")
        sys.exit(0)
    if answer != 'y' and answer != 'Y':
        raise Exception("Invalid answer")

class FailedSearch(Exception):
    pass

class FailedSearchTimeout(FailedSearch):
    pass

class FailedSearchExpiredSession(FailedSearch):
    pass

class FailedSearch500Error(FailedSearch):
    pass

class FailedSearchUnknownError(FailedSearch):
    pass

class CompletedSearchNoResults(Exception):
    pass

class Spider:
    '''Main spider class'''

    # searching for underscore character leads to timeout for some reason
    # % is a wildcard character
    __search_chars = string.ascii_uppercase \
        + string.digits \
        + string.punctuation.replace('_','').replace('%','') \
        + ' '

    __test_queries = [
        { # 500 results
            'search_string':'J',
            'start_date':datetime(2017,12,1),
            'end_date':datetime(2017,12,16),
            'court': 'BALTIMORE CITY'
        },
        { # 81 results
            'search_string':'T',
            'end_date':None,
            'start_date':datetime(2017,12,1),
            'court': 'BALTIMORE CITY'
        },
        { # 276 results
            'search_string':'E',
            'start_date':datetime(2017,12,17),
            'end_date':datetime(2017,12,31),
            'court': 'BALTIMORE CITY'
        },
        { # 39 results
            'search_string':'S',
            'end_date':None,
            'start_date':datetime(2017,12,17),
            'court': 'BALTIMORE CITY'
        },
        { # turns up cases with NUL char in name
            'search_string':'Z',
            'end_date':datetime(2017,12,9),
            'start_date':datetime(2017,11,24),
            'court': 'BALTIMORE CITY'
        },
        { # 1 result
            'search_string':'PUGH',
            'start_date':datetime(2017,5,12),
            'court':'BALTIMORE CITY'
        }
    ]

    async def __query_mjcs(self, db, item, session, url, method='POST', post_params={}, xml=False):
        if xml:
            post_params['d-16544-e'] = 3
        try:
            response = await session.request(
                method,
                url,
                data = post_params,
                max_redirects = 1
            )
        except asks.errors.RequestTimeout:
            item.handle_timeout(db)
            raise FailedSearchTimeout
        except h11.RemoteProtocolError as e:
            item.handle_unknown_err(e)
            raise FailedSearchUnknownError

        if response.history and response.history[0].status_code == 302:
            print("Received 302 redirect, renewing session...")
            await session.renew()
            raise FailedSearchExpiredSession
        elif response.status_code == 500:
            print("############## Received 500 error #################")
            item.handle_500()
            raise FailedSearch500Error
        elif response.status_code != 200:
            print("Unknown error. response code: %s, response body: %s" % (response.status_code, response.text))
            item.handle_unknown_err("response code: %s, response body: %s" % (response.status_code, response.text))
            raise FailedSearchUnknownError
        else:
            if 'text/html' in response.headers['Content-Type'] \
                    and re.search(r'<span class="error">\s*<br>CaseSearch will only display results',response.text):
                print("No cases for search string %s starting on %s" % (item.search_string,item.start_date.strftime("%-m/%-d/%Y")))
                raise CompletedSearchNoResults
            elif 'text/html' in response.headers['Content-Type'] \
                    and re.search(r'<span class="error">\s*<br>Sorry, but your query has timed out after 2 minute',response.text):
                print("$$$$$$$$$$$$$$ MJCS Timeout $$$$$$$$$$$$")
                item.handle_timeout(db)
                raise FailedSearchTimeout

        return response

    async def __search_cases(self, run, item, task_status=trio.TASK_STATUS_IGNORED):
        task_status.started()
        session = await self.session_pool.get()
        start_query = datetime.now()

        print("Searching for %s on start date %s" % (item.search_string,item.start_date.strftime("%-m/%-d/%Y")))
        query_params = {
            'lastName':item.search_string,
            'countyName':item.court,
            'company':'N',
            'filingStart':item.start_date.strftime("%-m/%-d/%Y") if item.end_date else None,
            'filingEnd':item.end_date.strftime("%-m/%-d/%Y") if item.end_date else None,
            'filingDate':item.start_date.strftime("%-m/%-d/%Y") if not item.end_date else None
        }
        with db_session() as db:
            try:
                response_html = await self.__query_mjcs(
                    db,
                    item,
                    session,
                    url = 'http://casesearch.courts.state.md.us/casesearch/inquirySearch.jis',
                    method = 'POST',
                    post_params = query_params,
                    xml = False
                )
            except FailedSearch:
                self.session_pool.put_nowait(session)
                return
            except CompletedSearchNoResults:
                item.handle_complete(db,0,start_query,(datetime.now() - start_query).total_seconds())
                run.queue_finished += 1
                self.session_pool.put_nowait(session)
                return

            # Parse HTML
            hit_limit = 'The result set exceeds the limit of 500 records' in response_html.text
            html = BeautifulSoup(response_html.text,'html.parser')
            results = []
            for row in html.find('table',class_='results',id='row').tbody.find_all('tr'):
                results.append(row)
            # Paginate through results if needed
            while html.find('span',class_='pagelinks').find('a',string='Next'):
                try:
                    response_html = await self.__query_mjcs(
                        db,
                        item,
                        session,
                        url = 'http://casesearch.courts.state.md.us' + html.find('span',class_='pagelinks').find('a',string='Next')['href'],
                        method = 'GET'
                    )
                except FailedSearch:
                    self.session_pool.put_nowait(session)
                    return
                html = BeautifulSoup(response_html.text,'html.parser')
                for row in html.find('table',class_='results',id='row').tbody.find_all('tr'):
                    results.append(row)

        query_time = (datetime.now() - start_query).total_seconds()
        self.session_pool.put_nowait(session)
        print("Search string %s returned %d items, took %d seconds" % (item.search_string, len(results), query_time))

        with db_session() as db:
            processed_cases = []
            for result in results:
                elements = result.find_all('td')
                case_number = elements[0].a.string
                if case_number not in processed_cases: # case numbers can appear multiple times in results
                    processed_cases.append(case_number)
                    case_exists = db.query(Case.case_number).filter(Case.case_number == case_number).one_or_none()
                    case_url = elements[0].a['href']
                    url_components = re.search("loc=(\d+)&detailLoc=([A-Z\d]+)$", case_url)
                    loc = url_components.group(1)
                    detail_loc = url_components.group(2)
                    if not case_exists or run.overwrite:
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
                            query_court = item.court,
                            loc = loc,
                            detail_loc = detail_loc,
                            url = case_url
                        )
                        case_dict = case.dict()
                        db.execute(
                            insert(Case.__table__).values(**case_dict)\
                                .on_conflict_do_update(
                                    index_elements=[Case.case_number],
                                    set_=case_dict
                                )
                        )
                    if not case_exists or run.force_scrape:
                        # only trigger Lambda scraper to pull case details if case didn't exist in database before
                        self.__add_to_scraper_queue(
                            case_number = case_number,
                            loc = loc,
                            detail_loc = detail_loc
                        )
            print("Submitted %d cases out of %d returned" % (len(processed_cases), len(results)))

            if hit_limit:
                # trailing spaces are trimmed, so <searh_string + ' '> will return same results as <search_string>.
                for char in self.__search_chars.replace(' ',''):
                    self.__upsert_search_item(db, SearchItem(
                        search_string = item.search_string + char,
                        start_date = item.start_date,
                        end_date = item.end_date,
                        court = item.court,
                        status = 'new'
                    ))
                    self.__upsert_search_item(db, SearchItem(
                        search_string = item.search_string + ' ' + char,
                        start_date = item.start_date,
                        end_date = item.end_date,
                        court = item.court,
                        status = 'new'
                    ))

            item.handle_complete(db, len(results), start_query, query_time)
            run.results_processed += len(results)
            run.queue_finished += 1

    def __add_to_scraper_queue(self, case_number, loc, detail_loc):
        scraper_queue.send_message(
            MessageBody = json.dumps({
                'case_number': case_number,
                'loc': loc,
                'detail_loc': detail_loc
            })
        )

    def __clear_queue(self, db):
        if active_count(db):
            prompt_continue("There are existing unsearched items in the queue. Are you sure you want to cancel them?")
            print("Clearing queue...")
            clear_queue(db)

    def __upsert_search_item(self, db, search_item):
        item_dict = search_item.dict()
        db.execute(
            insert(SearchItem.__table__).values(**item_dict)\
                .on_conflict_do_update(
                    index_elements=[SearchItem.id],
                    set_=item_dict
                )
        )

    def __seed_queue_test(self, db):
        for item in self.__test_queries:
            self.__upsert_search_item(db, SearchItem(
                search_string = item['search_string'],
                start_date = item['start_date'],
                end_date = item['end_date'] if 'end_date' in item else None,
                court = item['court']
            ))

    def __seed_queue(self, db, start_date, end_date=None, court=None):
        print("Seeding queue")
        if end_date:
            def gen_timeranges(start_date, end_date):
                for n in range(0,int((end_date - start_date).days),config.SPIDER_DAYS_PER_QUERY):
                    start = start_date + timedelta(n)
                    end = start_date + timedelta(n) + timedelta(config.SPIDER_DAYS_PER_QUERY - 1)
                    if end > end_date:
                        end = end_date
                    if start == end:
                        end = None
                    yield (start,end)
            for (start,end) in gen_timeranges(start_date, end_date):
                for char in self.__search_chars.replace(' ',''): # don't start queries with a space
                    self.__upsert_search_item(db, SearchItem(
                        search_string = char,
                        start_date = start,
                        end_date = end,
                        court = court
                    ))
        else:
            for char in self.__search_chars.replace(' ',''): # don't start queries with a space
                self.__upsert_search_item(db, SearchItem(
                    search_string = char,
                    start_date = start_date,
                    end_date = None,
                    court = court
                ))
        print("Finished seeding queue")

    async def __main_task(self, run):
        with db_session() as db:
            nitems = active_count(db)
        while nitems:
            with db_session() as db:
                items = active_items(db).limit(config.DB_BATCH_SIZE)
                print("new batch")
                async with trio.open_nursery() as nursery:
                    for item in items:
                        await nursery.start(self.__search_cases, run, item)
            with db_session() as db:
                nitems = active_count(db)

    def __run(self, start_date=None, end_date=None, court=None, overwrite=False, force_scrape=False):
        print("Starting run")
        with db_session() as db:
            run = Run(db, start_date, end_date, court, overwrite=overwrite, force_scrape=force_scrape)
            try:
                trio.run(self.__main_task, run, restrict_keyboard_interrupt_to_checkpoints=True)
            except KeyboardInterrupt:
                print("\nCaught KeyboardInterrupt: saving run...")
            run.complete(db)
            db.add(run)
        print("Run complete")

    def search(self, start_date, end_date=None, court=None, overwrite=False, force_scrape=False):
        with db_session() as db:
            self.__clear_queue(db)
            self.__seed_queue(db, start_date, end_date, court)
        self.__run(start_date, end_date, court, overwrite=overwrite, force_scrape=force_scrape)

    def resume(self, overwrite=False, force_scrape=False):
        with db_session() as db:
            if not active_count(db):
                raise Exception("Cannot resume, no items in queue")
        self.__run(overwrite=overwrite, force_scrape=force_scrape)

    def test(self, overwrite=False, force_scrape=False):
        with db_session() as db:
            self.__clear_queue(db)
            self.__seed_queue_test(db)
        self.__run(overwrite=overwrite, force_scrape=force_scrape)

    def __init__(self, connections = config.SPIDER_DEFAULT_CONCURRENCY):
        asks.init('trio')
        self.session_pool = trio.Queue(connections)
        for i in range(connections):
            self.session_pool.put_nowait(AsyncSession())
