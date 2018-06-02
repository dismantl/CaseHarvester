from .config import config
from .db import db_session
from .case import Case, cases_batch, cases_batch_filter, process_cases
from .session import Session
from sqlalchemy import and_
import requests
import boto3
import re
import json
from datetime import *
from queue import Queue
import concurrent.futures

MJCS_AUTH_TARGET = 'http://casesearch.courts.state.md.us/casesearch/inquiry-index.jsp'

s3 = boto3.client('s3')

class ScraperItem:
    def __init__(self, case_number, detail_loc):
        self.case_number = case_number
        self.detail_loc = detail_loc
        self.timeouts = 0
        self.errors = 0

class FailedScrape(Exception):
    pass

class FailedScrapeTimeout(FailedScrape):
    pass

class FailedScrape500(FailedScrape):
    pass

class FailedScrapeNotFound(FailedScrape):
    pass

class FailedScrapeTooShort(FailedScrape):
    pass

class FailedScrapeUnexpectedError(FailedScrape):
    pass

class FailedScrapeSearchResults(FailedScrape):
    pass

class FailedScrapeNoCaseNumber(FailedScrape):
    pass

class FailedScrapeUnknownError(FailedScrape):
    pass

class CompletedScrape(Exception):
    pass

class ExpiredSession(Exception):
    pass

class NoItemsInQueue(Exception):
    pass

def check_scrape_sanity(case_number, html):
    if "Acceptance of the following agreement is required" in html:
        raise ExpiredSession
    elif len(html) < 1000:
        raise FailedScrapeTooShort
    elif "An unexpected error occurred" in html:
        raise FailedScrapeUnexpectedError
    elif "Note: Initial Sort is by Last Name." in html:
        raise FailedScrapeSearchResults
    else:
        # case numbers will often be displayed with dashes and/or spaces between parts of it
        if re.search(r'[\- ]*'.join(case_number),html):
            return
        if re.search(r'[\- ]*'.join(case_number.lower()),html):
            return
        raise FailedScrapeNoCaseNumber

def delete_scrape(db, case_number):
    case_details_bucket = boto3.resource('s3').Bucket(config.CASE_DETAILS_BUCKET)
    object_versions = case_details_bucket.object_versions.filter(Prefix=case_number)
    object_versions = [x for x in object_versions if x.object_key == case_number]
    if len(object_versions) > 1:
        # delete most recent version
        object_versions = sorted(object_versions,key=lambda x: x.last_modified)
        object_versions[-1].delete()
        # set last_scrape to timestamp of previous version
        db.execute(
            Case.__table__.update()\
                .where(Case.case_number == case_number)\
                .values(last_scrape=object_versions[-2].last_modified)
        )
    elif len(object_versions) == 1:
        case_details_bucket.Object(case_number).delete()
        # Set last_scrape = null in DB
        db.execute(
            Case.__table__.update()\
                .where(Case.case_number == case_number)\
                .values(last_scrape=None)
        )

def has_scrape(case_number):
    try:
        o = config.case_details_bucket.Object(case_number).get()
    except s3.exceptions.NoSuchKey:
        return False
    else:
        return True

def log_failed_case(case_number, detail_loc, error):
    print("Failed to scrape case %s: %s" % (case_number, error))
    config.scraper_failed_queue.send_message(
        MessageBody = json.dumps({
            'case_number': case_number,
            'detail_loc': detail_loc
        })
    )

def store_case_details(case_number, detail_loc, html, check_before_store=True):
    if check_before_store:
        add = False
        try:
            previous_fetch = config.case_details_bucket.Object(case_number).get()
        except s3.exceptions.NoSuchKey:
            print("Case details for %s not found, adding..." % case_number)
            add = True
        else:
            if previous_fetch['Body'].read().decode('utf-8') != html:
                print("Found new version of case %s, replacing..." % case_number)
                add = True
    else:
        add = True

    if add:
        config.case_details_bucket.put_object(
            Body = html,
            Key = case_number,
            Metadata = {
                'timestamp': datetime.now().isoformat(),
                'detail_loc': detail_loc
            }
        )
        # TODO what if s3 put_object succeeds, but cannot connect to database?
        with db_session() as db:
            db.execute(
                Case.__table__.update()\
                    .where(Case.case_number == case_number)\
                    .values(last_scrape = datetime.now())
            )

def handle_scrape_response(scraper_item, response, check_before_store=True):
    if response.status_code != 200:
        if response.status_code == 500:
            scraper_item.errors += 1
            if scraper_item.errors >= config.QUERY_ERROR_LIMIT:
                log_failed_case(scraper_item.case_number,
                    scraper_item.detail_loc, "Reached 500 error limit")
                raise FailedScrape500
        # This is how requests deals with redirects
        elif response.status_code == 302 \
                and response.headers['Location'] == MJCS_AUTH_TARGET:
            raise ExpiredSession
        else:
            scraper_item.errors += 1
            if scraper_item.errors >= config.QUERY_ERROR_LIMIT:
                log_failed_case(
                    scraper_item.case_number, scraper_item.detail_loc,
                    "Received unexpected response: code = %d, body = %s" % (response.status_code, response.text)
                )
                raise FailedScrapeUnknownError
    elif re.search(r'<span class="error">\s*<br>CaseSearch will only display results',response.text):
        scraper_item.errors += 1
        if scraper_item.errors >= config.QUERY_ERROR_LIMIT:
            log_failed_case(scraper_item.case_number,
                scraper_item.detail_loc, "Case details not found")
            raise FailedScrapeNotFound
    elif 'Sorry, but your query has timed out after 2 minute' in response.text:
        scraper_item.timeouts += 1
        if scraper_item.timeouts >= config.QUERY_TIMEOUTS_LIMIT:
            log_failed_case(scraper_item.case_number,
                scraper_item.detail_loc, "Reached timeout limit")
            raise FailedScrapeTimeout
    else:
        # Some sanity checks
        try:
            check_scrape_sanity(scraper_item.case_number, response.text)
        except FailedScrape as e:
            scraper_item.errors += 1
            if scraper_item.errors >= config.QUERY_ERROR_LIMIT:
                log_failed_case(scraper_item.case_number, scraper_item.detail_loc,
                    str(type(e)))
                raise e
        else:
            store_case_details(scraper_item.case_number, scraper_item.detail_loc, response.text, check_before_store)
            raise CompletedScrape

def scrape_case(case_number, detail_loc, session=None, check_before_store=True):
    if not session:
        session = Session()
    scraper_item = ScraperItem(case_number, detail_loc)
    while True:
        try:
            print("Requesting case details for",case_number)
            response = session.post(
                'http://casesearch.courts.state.md.us/casesearch/inquiryByCaseNum.jis',
                data = {
                    'caseId': case_number
                },
                allow_redirects = False
            )
        except requests.exceptions.Timeout:
            scraper_item.timeouts += 1
            if scraper_item.timeouts >= config.QUERY_TIMEOUTS_LIMIT:
                log_failed_scrape(case_number, detail_loc, "Reached timeout limit")
                raise FailedScrapeTimeout
        else:
            try:
                handle_scrape_response(scraper_item, response, check_before_store)
            except ExpiredSession:
                print("Renewing session")
                session.renew()
            except CompletedScrape:
                print("Completed scraping",case_number)
                break
            except Exception as e:
                e.html = response.text
                raise e

def scrape_case_thread(case):
    case_number = case['case_number']
    detail_loc = case['detail_loc']
    session_pool = case['session_pool']
    check_before_store = case['check_before_store']

    session = session_pool.get()
    ret = None
    try:
        ret = scrape_case(case_number, detail_loc, session, check_before_store)
    except:
        raise
    finally:
        session_pool.put_nowait(session)
    return ret

class Scraper:
    def __init__(self, on_error=None, threads=1):
        self.on_error = on_error
        self.threads = threads

    def scrape_from_queue(self, queue, nitems=None):
        session_pool = Queue(self.threads)
        for i in range(self.threads):
            session_pool.put_nowait(Session())
        items_scraped = 0
        while True:
            def fetch_from_queue(n):
                return queue.receive_messages(
                    WaitTimeSeconds = config.QUEUE_WAIT,
                    MaxNumberOfMessages = n
                )

            # Concurrently fetch up to 1000 (or nitems) messages from queue
            queue_items = []
            if nitems:
                q,r = divmod(nitems,10)
                nitems_per_thread = [10 for _ in range(0,q)]
                if r:
                    nitems_per_thread.append(r)
                with concurrent.futures.ThreadPoolExecutor(max_workers=len(nitems_per_thread)) as executor:
                    results = executor.map(fetch_from_queue,nitems_per_thread)
                    for result in results:
                        if result:
                            queue_items += result
            else:
                with concurrent.futures.ThreadPoolExecutor(max_workers=100) as executor:
                    results = executor.map(fetch_from_queue,[10 for _ in range(0,100)])
                    for result in results:
                        if result:
                            queue_items += result
            if not queue_items:
                print("No items found in queue")
                if items_scraped == 0:
                    raise NoItemsInQueue
                break

            cases = []
            for item in queue_items:
                body = json.loads(item.body)
                case_number = body['case_number']
                detail_loc = body['detail_loc']
                cases.append({
                    'case_number': case_number,
                    'detail_loc': detail_loc,
                    'session_pool': session_pool,
                    'check_before_store': True,
                    'item': item
                })

            def queue_on_success(case):
                case['item'].delete()
            def queue_on_error(exception, case):
                if self.on_error:
                    action = self.on_error(exception, case['case_number'])
                    if action == 'delete' or action == 'store':
                        if action == 'store':
                            store_case_details(
                                case['case_number'],
                                case['detail_loc'],
                                exception.html
                            )
                        case['item'].delete()
                        return 'continue'
                    return action
                raise exception

            counter = {
                'total': len(cases),
                'count': 0
            }
            print("Scraping %d cases" % counter['total'])
            process_cases(scrape_case_thread, cases, queue_on_success, queue_on_error, self.threads, counter)
            print("Finished scraping %d cases" % counter['total'])
            if nitems:
                break # don't need to keep looping

    def scrape_from_scraper_queue(self, nitems=None):
        return self.scrape_from_queue(config.scraper_queue, nitems)

    def scrape_from_failed_queue(self, nitems=None):
        return self.scrape_from_queue(config.scraper_failed_queue, nitems)

    def scrape_missing_cases(self):
        filter = and_(Case.last_scrape == None, Case.parse_exempt != True)
        with db_session() as db:
            print('Getting count of unscraped cases...',end='',flush=True)
            counter = {
                'total': db.query(Case.case_number).filter(filter).count(),
                'count': 0
            }
            print('Done.')
            print('Generating batch queries...',end='',flush=True)
            batch_filters = cases_batch_filter(db, filter)
            print('Done.')

        for batch_filter in batch_filters:
            with db_session() as db:
                cases = cases_batch(db, batch_filter)
            cases = [{
                'case_number': case.case_number,
                'detail_loc': case.detail_loc,

            }]
            def _on_error(exception, case):
                if self.on_error:
                    action = self.on_error(exception, case['case_number'])
                    if action == 'delete' or action == 'store':
                        if action == 'store':
                            store_case_details(
                                case['case_number'],
                                case['detail_loc'],
                                exception.html,
                                check_before_store=True
                            )
                        return 'continue'
                    return action
                raise exception
            process_cases(scrape_case_thread, cases, None, _on_error, self.threads, counter)
