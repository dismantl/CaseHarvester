from .config import config
from .session import AsyncSession
from .util import (db_session, fetch_from_queue, NoItemsInQueue, cases_batch,
                   cases_batch_filter, process_cases, get_detail_loc, chunks)
from .models import ScrapeVersion, Scrape, Case
from sqlalchemy import and_
from hashlib import sha256
import logging
import requests
import boto3
import re
import json
import os
import trio
import asks
import h11
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

SQS_REQUEST_MAX = 10

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

class Scraper:
    def __init__(self, concurrency=None):
        self.cases_scraped = 0

        # Set up concurrency
        self.concurrency = concurrency or config.SCRAPER_DEFAULT_CONCURRENCY
        asks.init('trio')
        self.session_pool = trio.Queue(self.concurrency)
        for _ in range(self.concurrency):
            self.session_pool.put_nowait(AsyncSession())

    def start_service(self):
        trio.run(self.__start_service, restrict_keyboard_interrupt_to_checkpoints=True)
    
    def scrape_specific_case(self, case_number):
        async def __scrape_specific_case(case_number):
            detail_loc = get_detail_loc(case_number)
            await self.__scrape_case(case_number, detail_loc)
        trio.run(__scrape_specific_case)
    
    def rescrape(self, days_ago_end, days_ago_start=0):
        # calculate date range
        today = datetime.now().date()
        date_end = today - timedelta(days=days_ago_start)
        date_start = today - timedelta(days=days_ago_end)
        logger.info(f'Rescraping cases between {date_start} and {date_end}')

        # query DB for cases filed in range
        with db_session() as db:
            cases = db.query(Case.case_number, Case.loc, Case.detail_loc).\
                filter(Case.filing_date >= date_start).\
                filter(Case.filing_date < date_end).\
                all()
        logger.info(f'Found {len(cases)} cases in time range')

        # add cases to scraper queue
        count = 0
        for chunk in chunks(cases, 10):  # can only do 10 messages per batch request
            count += len(chunk)
            Entries=[
                {
                    'Id': str(idx),
                    'MessageBody': json.dumps({
                        'case_number': case[0],
                        'loc': case[1],
                        'detail_loc': case[2]
                    })
                } for idx, case in enumerate(chunk)
            ]
            config.scraper_queue.send_messages(
                Entries=Entries
            )
        logger.info(f'Submitted {count} cases for rescraping')
    
    async def __start_service(self):
        logger.info('Initiating scraper service.')
        try:
            # Blocks until all child tasks finish or exception thrown
            async with trio.open_nursery() as nursery:
                nursery.start_soon(self.__queue_manager, nursery)
        except KeyboardInterrupt:
            print("\nCaught KeyboardInterrupt: stopping service.")
        logger.info(f'Successfully scraped {self.cases_scraped} cases.')
        logger.info("Scraper service stopped.")

    async def __queue_manager(self, nursery):
        while True:
            if len(nursery.child_tasks) < 100:
                logger.debug(f'Requesting {SQS_REQUEST_MAX} items from scraper queue')
                queue_items = config.scraper_queue.receive_messages(
                    WaitTimeSeconds = config.QUEUE_WAIT,
                    MaxNumberOfMessages = SQS_REQUEST_MAX
                )
                if queue_items:
                    for item in queue_items:
                        body = json.loads(item.body)
                        case_number = body['case_number']
                        detail_loc = body['detail_loc']
                        nursery.start_soon(self.__scrape_case, case_number, detail_loc)
                        item.delete()
                else:
                    logger.debug('No items in scraper queue, waiting...')
                    await trio.sleep(60 * 10)  # 10 mins
            else:
                logger.debug('Queue full, waiting...')
                await trio.sleep(5)

    async def __scrape_case(self, case_number, detail_loc):
        session = await self.session_pool.get()
        
        retry = True
        try:
            while True:
                try:
                    logger.debug(f"Requesting case details for {case_number}")
                    begin = datetime.now()
                    response = await session.post(
                        'http://casesearch.courts.state.md.us/casesearch/inquiryByCaseNum.jis',
                        data = {
                            'caseId': case_number
                        },
                        allow_redirects = False
                    )
                    end = datetime.now()
                    duration = (begin - end).total_seconds()
                except (asks.errors.BadHttpResponse, h11.RemoteProtocolError, 
                        trio.BrokenStreamError, OSError, asks.errors.RequestTimeout) as e:
                    await trio.sleep(0.1) # courtesy
                    if retry:
                        retry = False
                        continue
                    logger.warning(f"Scrape error {str(type(e).__name__)}: {str(e)}")
                    # raise FailedScrape
                    raise
                
                try:
                    self.__handle_scrape_response(case_number, detail_loc, response, duration)
                except ExpiredSession:
                    logger.debug("Renewing session")
                    await session.renew()
                    continue
                except FailedScrapeTimeout:
                    await trio.sleep(0.1) # courtesy
                    if retry:
                        retry = False
                        continue
                    logger.warning(f"Scrape timeout for {case_number}")
                    raise
                except FailedScrape as e:
                    await trio.sleep(1) #anti hammer
                    logger.warning(f"Scrape error {str(type(e).__name__)}: {str(e)}")
                    raise
                self.cases_scraped += 1
                break
        except FailedScrape:
            config.scraper_failed_queue.send_message(
                MessageBody = json.dumps({
                    'case_number': case_number,
                    'detail_loc': detail_loc
                })
            )
        finally:
            await self.session_pool.put(session)

    def __handle_scrape_response(self, case_number, detail_loc, response, scrape_duration):
        if response.status_code != 200:
            if response.status_code == 500:
                raise FailedScrape500
            elif response.history and response.history[0].status_code == 302:
                raise ExpiredSession
            else:
                raise FailedScrapeUnknownError
        elif re.search(r'<span class="error">\s*<br>CaseSearch will only display results',response.text):
            raise FailedScrapeNotFound
        elif 'Sorry, but your query has timed out after 2 minute' in response.text:
            raise FailedScrapeTimeout
        else:
            # Some sanity checks
            if "Acceptance of the following agreement is" in response.text:
                raise ExpiredSession
            elif len(response.text) < 1000:
                raise FailedScrapeTooShort
            elif "An unexpected error occurred" in response.text:
                raise FailedScrapeUnexpectedError
            elif "Note: Initial Sort is by Last Name." in response.text:
                raise FailedScrapeSearchResults
            else:
                # case numbers will often be displayed with dashes and/or spaces between parts of it
                if not re.search(r'[\- ]*'.join(case_number),response.text) \
                        and not re.search(r'[\- ]*'.join(case_number.lower()),response.text):
                    raise FailedScrapeNoCaseNumber
            self.__store_case_details(case_number, detail_loc, response.text, scrape_duration)

    def __store_case_details(self, case_number, detail_loc, html, scrape_duration=None):
        add = False
        try:
            previous_fetch = config.case_details_bucket.Object(case_number).get()
        except config.s3.meta.client.exceptions.NoSuchKey:
            logger.info("Case details for %s not found, adding..." % case_number)
            add = True
        else:
            if previous_fetch['Body'].read().decode('utf-8') != html:
                logger.info("Found new version of case %s, updating..." % case_number)
                add = True

        if add:
            timestamp = datetime.now()
            obj = config.case_details_bucket.put_object(
                Body = html,
                Key = case_number,
                Metadata = {
                    'timestamp': timestamp.isoformat(),
                    'detail_loc': detail_loc
                }
            )
            with db_session() as db:
                scrape_version = ScrapeVersion(
                    s3_version_id = obj.version_id,
                    case_number = case_number,
                    length = len(html),
                    sha256 = sha256(html.encode('utf-8')).hexdigest()
                )
                scrape = Scrape(
                    case_number = case_number,
                    s3_version_id = obj.version_id,
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
