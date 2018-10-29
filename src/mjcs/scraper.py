from .config import config
from .db import db_session, TableBase
from .case import Case, cases_batch, cases_batch_filter, process_cases
from .session import Session
from sqlalchemy import and_, select, Column, DateTime, Integer, Numeric, String, ForeignKey, Index
from hashlib import sha256
import requests
import boto3
import re
import json
from datetime import *
from queue import Queue
import concurrent.futures

MJCS_AUTH_TARGET = 'http://casesearch.courts.state.md.us/casesearch/inquiry-index.jsp'

class ScrapeVersion(TableBase):
    __tablename__ = 'scrape_versions'

    s3_version_id = Column(String, primary_key=True)
    case_number = Column(String, ForeignKey('cases.case_number', ondelete='CASCADE'), index=True)
    length = Column(Integer)
    sha256 = Column(String)

class Scrape(TableBase):
    __tablename__ = 'scrapes'

    id = Column(Integer, primary_key=True)
    case_number = Column(String, ForeignKey('cases.case_number', ondelete='CASCADE'), index=True)
    s3_version_id = Column(String, ForeignKey('scrape_versions.s3_version_id', ondelete='CASCADE'))
    timestamp = Column(DateTime)
    duration = Column(Numeric, nullable=True) # seconds

Index('ix_scrape_timestamp', Scrape.case_number, Scrape.timestamp.desc())

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

def delete_latest_scrape(db, case_number):
    versions = [_ for _, in db.query(ScrapeVersion.s3_version_id)\
        .filter(ScrapeVersion.case_number == case_number)]
    last_version_id = versions[0]
    last_version_obj = config.s3.ObjectVersion(
        config.CASE_DETAILS_BUCKET,
        case_number,
        last_version_id
    )
    last_version_obj.delete()
    db.execute(
        ScrapeVersion.__table__.delete()\
            .where(
                and_(
                    ScrapeVersion.case_number == case_number,
                    ScrapeVersion.s3_version_id == last_version_id
                )
            )
    )
    if len(versions) > 1:
        # set last_scrape to timestamp of previous version
        db.execute(
            Case.__table__.update()\
                .where(Case.case_number == case_number)\
                .values(
                    last_scrape = select([Scrape.timestamp])\
                        .where(
                            and_(
                                Scrape.case_number == case_number,
                                Scrape.s3_version_id == versions[1]
                            )
                        ).as_scalar()
                )
        )
    elif len(versions) == 1:
        db.execute(
            Case.__table__.update()\
                .where(Case.case_number == case_number)\
                .values(last_scrape=None)
        )

def has_scrape(case_number):
    try:
        config.case_details_bucket.Object(case_number).get()
    except config.s3.meta.client.exceptions.NoSuchKey:
        return False
    else:
        return True

def store_case_details(case_number, detail_loc, html, scrape_duration=None, check_before_store=True):
    boto_session = boto3.session.Session(profile_name=config.aws_profile) # https://boto3.readthedocs.io/en/latest/guide/resources.html#multithreading-multiprocessing
    s3 = boto_session.resource('s3')
    case_details_bucket = s3.Bucket(config.CASE_DETAILS_BUCKET)
    if check_before_store:
        add = False
        try:
            previous_fetch = case_details_bucket.Object(case_number).get()
        except s3.meta.client.exceptions.NoSuchKey:
            print("Case details for %s not found, adding..." % case_number)
            add = True
        else:
            if previous_fetch['Body'].read().decode('utf-8') != html:
                print("Found new version of case %s, replacing..." % case_number)
                add = True
    else:
        add = True

    if add:
        timestamp = datetime.now()
        obj = case_details_bucket.put_object(
            Body = html,
            Key = case_number,
            Metadata = {
                'timestamp': timestamp.isoformat(),
                'detail_loc': detail_loc
            }
        )
        while True: # during multithreading sometimes obj.version_id throws an exception
            try:
                obj_version_id = obj.version_id
            except:
                pass
            else:
                break
        with db_session() as db:
            scrape_version = ScrapeVersion(
                s3_version_id = obj_version_id,
                case_number = case_number,
                length = len(html),
                sha256 = sha256(html.encode('utf-8')).hexdigest()
            )
            scrape = Scrape(
                case_number = case_number,
                s3_version_id = obj_version_id,
                timestamp = timestamp,
                duration = scrape_duration
            )
            db.add(scrape_version)
            db.flush() # to satisfy foreign key constraint of scrapes
            db.add(scrape)
            db.execute(
                Case.__table__.update()\
                    .where(Case.case_number == case_number)\
                    .values(last_scrape = timestamp)
            )

def fetch_from_queue(queue, nitems=None):
    def queue_receive(n):
        return queue.receive_messages(
            WaitTimeSeconds = config.QUEUE_WAIT,
            MaxNumberOfMessages = n
        )
    # Concurrently fetch up to nitems (or 100) messages from queue, 10 per thread
    queue_items = []
    if nitems:
        q,r = divmod(nitems,10)
        nitems_per_thread = [10 for _ in range(0,q)]
        if r:
            nitems_per_thread.append(r)
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(nitems_per_thread)) as executor:
            results = executor.map(queue_receive,nitems_per_thread)
            for result in results:
                if result:
                    queue_items += result
    else:
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            results = executor.map(queue_receive,[10 for _ in range(0,10)])
            for result in results:
                if result:
                    queue_items += result
    return queue_items

class Scraper:
    def __init__(self, on_error=None, threads=1, log_failed_scrapes=True):
        self.on_error = on_error
        self.threads = threads
        self.log_failed_scrapes = log_failed_scrapes

    def log_failed_scrape(self, case_number, detail_loc, error):
        print("Failed to scrape case %s: %s" % (case_number, error))
        if self.log_failed_scrapes:
            config.scraper_failed_queue.send_message(
                MessageBody = json.dumps({
                    'case_number': case_number,
                    'detail_loc': detail_loc
                })
            )

    def handle_scrape_response(self, scraper_item, response, scrape_duration, check_before_store=True):
        if response.status_code != 200:
            if response.status_code == 500:
                scraper_item.errors += 1
                if scraper_item.errors >= config.QUERY_ERROR_LIMIT:
                    self.log_failed_scrape(scraper_item.case_number,
                        scraper_item.detail_loc, "Reached 500 error limit")
                    raise FailedScrape500
            # This is how requests deals with redirects
            elif response.status_code == 302 \
                    and response.headers['Location'] == MJCS_AUTH_TARGET:
                raise ExpiredSession
            else:
                scraper_item.errors += 1
                if scraper_item.errors >= config.QUERY_ERROR_LIMIT:
                    self.log_failed_scrape(
                        scraper_item.case_number, scraper_item.detail_loc,
                        "Received unexpected response: code = %d, body = %s" % (response.status_code, response.text)
                    )
                    raise FailedScrapeUnknownError
        elif re.search(r'<span class="error">\s*<br>CaseSearch will only display results',response.text):
            scraper_item.errors += 1
            if scraper_item.errors >= config.QUERY_ERROR_LIMIT:
                self.log_failed_scrape(scraper_item.case_number,
                    scraper_item.detail_loc, "Case details not found")
                raise FailedScrapeNotFound
        elif 'Sorry, but your query has timed out after 2 minute' in response.text:
            scraper_item.timeouts += 1
            if scraper_item.timeouts >= config.QUERY_TIMEOUTS_LIMIT:
                self.log_failed_scrape(scraper_item.case_number,
                    scraper_item.detail_loc, "Reached timeout limit")
                raise FailedScrapeTimeout
        else:
            # Some sanity checks
            try:
                check_scrape_sanity(scraper_item.case_number, response.text)
            except FailedScrape as e:
                scraper_item.errors += 1
                if scraper_item.errors >= config.QUERY_ERROR_LIMIT:
                    self.log_failed_scrape(scraper_item.case_number, scraper_item.detail_loc,
                        str(type(e)))
                    raise e
            else:
                store_case_details(scraper_item.case_number, scraper_item.detail_loc, response.text, scrape_duration, check_before_store)
                raise CompletedScrape

    def scrape_case(self, case_number, detail_loc, session=None, check_before_store=True):
        if not session:
            session = Session()
        scraper_item = ScraperItem(case_number, detail_loc)
        while True:
            try:
                print("Requesting case details for",case_number)
                begin = datetime.now()
                response = session.post(
                    'http://casesearch.courts.state.md.us/casesearch/inquiryByCaseNum.jis',
                    data = {
                        'caseId': case_number
                    },
                    allow_redirects = False
                )
                end = datetime.now()
                duration = (begin - end).total_seconds()
            except requests.exceptions.Timeout:
                scraper_item.timeouts += 1
                if scraper_item.timeouts >= config.QUERY_TIMEOUTS_LIMIT:
                    self.log_failed_scrape(case_number, detail_loc, "Reached timeout limit")
                    raise FailedScrapeTimeout
            else:
                try:
                    self.handle_scrape_response(scraper_item, response, duration, check_before_store)
                except ExpiredSession:
                    print("Renewing session")
                    session.renew()
                except CompletedScrape:
                    print("Completed scraping",case_number)
                    break
                except Exception as e:
                    e.html = response.text
                    raise e

    def scrape_case_thread(self, case):
        case_number = case['case_number']
        detail_loc = case['detail_loc']
        session_pool = case['session_pool']
        check_before_store = case['check_before_store']

        session = session_pool.get()
        ret = None
        try:
            ret = self.scrape_case(case_number, detail_loc, session, check_before_store)
        except:
            raise
        finally:
            session_pool.put_nowait(session)
        return ret

    def scrape_from_queue(self, queue, nitems=None):
        session_pool = Queue(self.threads)
        for i in range(self.threads):
            session = Session()
            session.renew() # Renew session immediately bc it was causing errors in Lambda
            session_pool.put_nowait(session)
        counter = {
            'total': 0,
            'count': 0
        }

        while True:
            queue_items = fetch_from_queue(queue, nitems)
            if not queue_items:
                print("No items found in queue")
                break
            counter['total'] += len(queue_items)

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
                        return 'delete'
                    return action
                raise exception

            print("Scraping %d cases" % len(cases))
            process_cases(self.scrape_case_thread, cases, queue_on_success, queue_on_error, self.threads, counter)
            print("Finished scraping %d cases" % counter['total'])
            if nitems:
                break # don't need to keep looping

        print("Total number of scraped cases: %d" % counter['count'])
        if counter['count'] == 0:
            raise NoItemsInQueue

    def scrape_from_scraper_queue(self, nitems=None):
        return self.scrape_from_queue(config.scraper_queue, nitems)

    def scrape_from_failed_queue(self, nitems=None):
        self.log_failed_scrapes = False
        return self.scrape_from_queue(config.scraper_failed_queue, nitems)

    def scrape_missing_cases(self):
        filter = and_(Case.last_scrape == None, Case.scrape_exempt != True)
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
            process_cases(self.scrape_case_thread, cases, None, _on_error, self.threads, counter)
