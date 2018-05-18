from .config import config
from .db import db_session, engine
from .case import Case, cases_batch, cases_batch_filter, get_detail_loc
import asks
import trio
import boto3
import re
import json
from datetime import *

MJCS_AUTH_TARGET = 'http://casesearch.courts.state.md.us/casesearch/inquiry-index.jsp'

s3 = boto3.client('s3')
sqs = boto3.resource('sqs')
scraper_queue = sqs.get_queue_by_name(QueueName=config.SCRAPER_QUEUE_NAME)
failed_queue = sqs.get_queue_by_name(QueueName=config.SCRAPER_FAILED_QUEUE_NAME)

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

class FailedScrape(Exception):
    pass

class FailedScrapeTimeout(FailedScrape):
    pass

class FailedScrapeNotFound(FailedScrape):
    pass

class FailedScrapeUnknownError(FailedScrape):
    pass

class CompletedScrape(Exception):
    pass

class ExpiredSession(Exception):
    pass

class NoItemsInQueue(Exception):
    pass

class ScraperItem:
    def __init__(self, case_number, detail_loc):
        self.case_number = case_number
        self.detail_loc = detail_loc
        self.timeouts = 0
        self.err500s = 0
        self.errother = 0

class Scraper:
    def __init__(self):
        import requests
        from mjcs.session import Session
        self.session = Session()
        self.check_before_store = True

    def handle_scrape_response(self, scraper_item, response):
        if response.status_code != 200:
            if response.status_code == 500:
                scraper_item.err500s += 1
                if scraper_item.err500s >= config.QUERY_500_LIMIT:
                    self.log_failed_case(scraper_item.case_number,
                        scraper_item.detail_loc, "Reached 500 error limit")
                    raise FailedScrapeTimeout
            # This is how requests deals with redirects
            elif response.status_code == 302 \
                    and response.headers['Location'] == MJCS_AUTH_TARGET:
                raise ExpiredSession
            else:
                scraper_item.errother += 1
                if scraper_item.errother >= config.QUERY_500_LIMIT:
                    self.log_failed_case(
                        scraper_item.case_number, scraper_item.detail_loc,
                        "Received unexpected response: code = %d, body = %s" % (response.status_code, response.text)
                    )
                    raise FailedScrapeUnknownError
        elif re.search(r'<span class="error">\s*<br>CaseSearch will only display results',response.text):
            scraper_item.errother += 1
            if scraper_item.errother >= config.QUERY_500_LIMIT:
                self.log_failed_case(scraper_item.case_number,
                    scraper_item.detail_loc, "Case details not found")
                raise FailedScrapeNotFound
        elif 'Sorry, but your query has timed out after 2 minute' in response.text:
            scraper_item.timeouts += 1
            if scraper_item.timeouts >= config.QUERY_TIMEOUTS_LIMIT:
                self.log_failed_case(scraper_item.case_number,
                    scraper_item.detail_loc, "Reached timeout limit")
                raise FailedScrapeTimeout
        else:
            # Some sanity checks
            if "Acceptance of the following agreement is required" in response.text:
                scraper_item.errother += 1
                if scraper_item.errother >= config.QUERY_500_LIMIT:
                    self.log_failed_case(scraper_item.case_number, scraper_item.detail_loc,
                        "TOS page received despite successful request")
                    raise FailedScrapeUnknownError
            elif len(response.text) < 1000:
                scraper_item.errother += 1
                if scraper_item.errother >= config.QUERY_500_LIMIT:
                    self.log_failed_case(scraper_item.case_number, scraper_item.detail_loc,
                        "Response too short: " + response.text)
                    raise FailedScrapeUnknownError
            elif "An unexpected error occurred" in response.text \
                    or "Note: Initial Sort is by Last Name." in response.text \
                    or scraper_item.case_number not in response.text: # TODO this doesn't work for some non-Baltimore courts where case numbers have hyphens (e.g. D-072-LT-17-002210)
                scraper_item.errother += 1
                if scraper_item.errother >= config.QUERY_500_LIMIT:
                    self.log_failed_case(scraper_item.case_number, scraper_item.detail_loc,
                        "Error scraping case: " + response.text)
                    raise FailedScrapeUnknownError
            else:
                self.store_case_details(scraper_item.case_number, scraper_item.detail_loc, response.text)
                raise CompletedScrape

    def case_details_exist(self, case_number):
        try:
            o = s3.get_object(
                Bucket = config.CASE_DETAILS_BUCKET,
                Key = case_number
            )
        except s3.exceptions.NoSuchKey:
            return False
        else:
            return True

    def scrape(self, case_number, detail_loc):
        session = self.session
        scraper_item = ScraperItem(case_number, detail_loc)
        while True:
            try:
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
                    self.log_failed_case(case_number, detail_loc, "Reached timeout limit")
                    break
            else:
                try:
                    self.handle_scrape_response(scraper_item, response)
                except ExpiredSession:
                    session.renew()
                except FailedScrape:
                    break
                except CompletedScrape:
                    break

    def log_failed_case(self, case_number, detail_loc, error):
        print("Failed to scrape case %s: %s" % (case_number, error))
        failed_queue.send_message(
            MessageBody = json.dumps({
                'case_number': case_number,
                'detail_loc': detail_loc
            })
        )

    def store_case_details(self, case_number, detail_loc, html):
        if self.check_before_store:
            add = False
            try:
                previous_fetch = s3.get_object(Bucket=config.CASE_DETAILS_BUCKET, Key=case_number)
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
            boto3.client('s3').put_object(
                Body = html,
                Bucket = config.CASE_DETAILS_BUCKET,
                Key = case_number,
                Metadata = {
                    'timestamp': datetime.now().isoformat(),
                    'detail_loc': detail_loc
                }
            )
            # TODO what if s3 put_object succeeds, but cannot connect to database?
            engine.execute(
                Case.__table__.update()\
                    .where(Case.case_number == case_number)\
                    .values(last_scrape = datetime.now())
            )

class ParallelScraper(Scraper):
    def __init__(self, connections = config.SCRAPER_DEFAULT_CONCURRENCY):
        from mjcs.session import AsyncSession
        asks.init('trio')
        self.session_pool = trio.Queue(connections)
        for i in range(connections):
            self.session_pool.put_nowait(AsyncSession())
        self.check_before_store = True
        self.check_before_scrape = False

    async def scrape(self, case_number, detail_loc, task_status=trio.TASK_STATUS_IGNORED):
        task_status.started()
        session = await self.session_pool.get()
        scraper_item = ScraperItem(case_number, detail_loc)
        while True:
            try:
                print("Requesting case details for",case_number)
                response = await session.post(
                    'http://casesearch.courts.state.md.us/casesearch/inquiryByCaseNum.jis',
                    data = {
                        'caseId': case_number
                    },
                    max_redirects = 1
                )
            except asks.errors.RequestTimeout:
                scraper_item.timeouts += 1
                if scraper_item.timeouts >= config.QUERY_TIMEOUTS_LIMIT:
                    self.log_failed_case(case_number, detail_loc, "Reached timeout limit")
                    break
            else:
                # Because asks deals with redirects differently than requests
                if response.history and response.history[0].status_code == 302:
                    response.status_code = 302
                    response.headers['Location'] = response.history[0].headers['Location']
                try:
                    self.handle_scrape_response(scraper_item, response)
                except ExpiredSession:
                    print("Renewing session")
                    await session.renew()
                except FailedScrape:
                    print("Failed to scrape",case_number)
                    break
                except CompletedScrape:
                    print("Completed scraping",case_number)
                    break
        self.session_pool.put_nowait(session)

    async def __scrape_cases_main_task(self, cases):
        async with trio.open_nursery() as nursery:
            for case in cases:
                await nursery.start(self.scrape, case['case_number'], case['detail_loc'])

    def scrape_cases_or_raise(self, cases):
        self.check_before_store = True
        try:
            trio.run(self.__scrape_cases_main_task, cases, restrict_keyboard_interrupt_to_checkpoints=True)
        except KeyboardInterrupt:
            print("\nCaught KeyboardInterrupt: exiting...")
            raise

    async def __scrape_missing_main_task(self):
        with db_session() as db:
            for batch_filter in cases_batch_filter(db, Case.last_scrape == None):
                print("new batch")
                async with trio.open_nursery() as nursery:
                    for case in cases_batch(db, batch_filter):
                        await nursery.start(self.scrape, case.case_number, case.detail_loc)

    def scrape_missing_cases(self):
        self.check_before_store = False
        try:
            trio.run(self.__scrape_missing_main_task, restrict_keyboard_interrupt_to_checkpoints=True)
        except KeyboardInterrupt:
            print("\nCaught KeyboardInterrupt: exiting...")

    def scrape_from_queue_or_raise(self, queue, nitems=10, wait_time=config.QUEUE_WAIT):
        # TODO allow more than 10 items to be scraped at once
        print("Scraping up to %d items from queue" % nitems)
        queue_items = queue.receive_messages(
            WaitTimeSeconds = wait_time,
            MaxNumberOfMessages = nitems
        )
        if not queue_items:
            print("No items found in queue")
            raise NoItemsInQueue
        cases = []
        for item in queue_items:
            body = json.loads(item.body)
            case_number = body['case_number']
            if 'detail_loc' in body:
                detail_loc = body['detail_loc']
            else:
                detail_loc = get_detail_loc(case_number)
            cases.append({'case_number':case_number,'detail_loc':detail_loc})
        print("Scraping the following cases:",' '.join(map(lambda x: json.loads(x.body)['case_number'], queue_items)))
        self.scrape_cases_or_raise(cases)
        for item in queue_items:
            item.delete() # remove from queue
        print("Scraping complete")

    def scrape_from_queue(self):
        while True:
            try:
                self.scrape_from_queue_or_raise(scraper_queue)
            except NoItemsInQueue:
                break

    def scrape_from_failed_queue(self):
        while True:
            try:
                self.scrape_from_queue_or_raise(failed_queue)
            except NoItemsInQueue:
                break
