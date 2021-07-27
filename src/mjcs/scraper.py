from .config import config
from .session import AsyncSessionPool
from .util import db_session, get_detail_loc, send_to_queue, cases_batch_filter, get_queue_count
from .models import ScrapeVersion, Scrape, Case
from hashlib import sha256
import logging
import botocore
import re
import json
import trio
from datetime import datetime, timedelta
from sqlalchemy import and_, or_, text

logger = logging.getLogger(__name__)

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
        self.successful_scrapes = 0

        # Set up concurrency
        self.concurrency = concurrency or config.SCRAPER_DEFAULT_CONCURRENCY
        self.session_pool = AsyncSessionPool(self.concurrency)

    def start_service(self):
        trio.run(self.__start_service, restrict_keyboard_interrupt_to_checkpoints=True)
    
    def scrape_specific_case(self, case_number):
        async def __scrape_specific_case(case_number):
            detail_loc = get_detail_loc(case_number)
            await self.__scrape_case(case_number, detail_loc)
        trio.run(__scrape_specific_case, case_number)
    
    def rescrape_stale(self, days=None):
        # Abort if the scraper queue is already full
        if get_queue_count(config.scraper_queue) > config.SCRAPE_QUEUE_THRESHOLD:
            logger.info('Scraper queue is already full, aborting...')
            return
        
        filter = and_(
            text("cases.scrape_exempt = False"),
            or_(
                text("cases.last_scrape is null"),
                and_(
                    text("cases.active = True"),
                    or_(
                        text("cases.filing_date > current_date"),  # Sometimes MJCS lists filing dates in the future
                        or_(
                            text(f"age_days(cases.last_scrape) > ceiling({config.RESCRAPE_COEFFICIENT}*age_days(cases.filing_date))"),
                            text(f"age_days(cases.last_scrape) > {config.MAX_SCRAPE_AGE}")  # age_days function is defined in db/sql/functions.sql
                        )
                    )
                ),
                and_(
                    text("cases.active = False"),
                    or_(
                        text("cases.filing_date > current_date"),
                        text(f"age_days(cases.last_scrape) > {config.MAX_SCRAPE_AGE_INACTIVE}")
                    )
                )
            )
        )
        if days is not None:
            filter = and_(filter, text(f"age(filing_date) < '{days} days'"))
        logger.info('Generating batch queries')
        with db_session() as db:
            batch_filters = cases_batch_filter(db, filter)
        total = 0
        for batch_filter in batch_filters:
            logger.debug('Fetching batch of cases from database')
            with db_session() as db:
                cases = db.query(Case.case_number, Case.detail_loc).filter(batch_filter).all()
            
            # add cases to scraper queue
            messages = [
                json.dumps({
                    'case_number': case[0],
                    'detail_loc': case[1]
                }) for case in cases
            ]
            send_to_queue(config.scraper_queue, messages)
            logger.info(f'Submitted {len(cases)} cases for rescraping')
            total += len(cases)
        logger.info(f"Submitted a total of {total} cases for rescraping")

    def rescrape(self, days_ago_end, days_ago_start=0):
        # calculate date range
        today = datetime.now().date()
        date_end = today - timedelta(days=days_ago_start)
        date_start = today - timedelta(days=days_ago_end)
        logger.info(f'Rescraping cases between {date_start} and {date_end}')

        # query DB for cases filed in range
        with db_session() as db:
            cases = db.query(Case.case_number, Case.detail_loc).\
                filter(Case.filing_date >= date_start).\
                filter(Case.filing_date < date_end).\
                filter(Case.scrape_exempt == False).\
                all()
        logger.info(f'Found {len(cases)} cases in time range')

        # add cases to scraper queue
        messages = [
            json.dumps({
                'case_number': case[0],
                'detail_loc': case[1]
            }) for case in cases
        ]
        send_to_queue(config.scraper_queue, messages)
        logger.info(f'Submitted {len(cases)} cases for rescraping')
    
    async def __start_service(self):
        logger.info('Initiating scraper service.')
        try:
            # Blocks until all child tasks finish or exception thrown
            async with trio.open_nursery() as nursery:
                nursery.start_soon(self.__queue_manager, nursery)
        except KeyboardInterrupt:
            print("\nCaught KeyboardInterrupt: stopping service.")
        logger.info(f'Successfully scraped {self.successful_scrapes} cases.')
        logger.info("Scraper service stopped.")

    async def __queue_manager(self, nursery):
        while True:
            if len(nursery.child_tasks) < 100:
                logger.debug('Requesting 10 items from scraper queue')
                queue_items = config.scraper_queue.receive_messages(
                    WaitTimeSeconds = config.QUEUE_WAIT,
                    MaxNumberOfMessages = 10
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
                    await trio.sleep(config.SCRAPER_WAIT_INTERVAL)
            else:
                logger.debug('Queue full, waiting...')
                await trio.sleep(5)

    async def __scrape_case(self, case_number, detail_loc):
        session = await self.session_pool.get()
        logger.debug(f"Requesting case details for {case_number}")
        begin = datetime.now()
        response = await session.request(
            'POST',
            f'{config.MJCS_BASE_URL}/inquiryByCaseNum.jis',
            data = {
                'caseId': case_number
            }
        )
        end = datetime.now()
        duration = (end - begin).total_seconds()
        self.session_pool.put_nowait(session)

        # Handle scrape result
        try:
            self.__check_scrape_response(case_number, response)
            self.successful_scrapes += 1
        except FailedScrape as e:
            logger.warning(f'Scrape error {type(e).__name__}: {e}')
            await trio.sleep(1) #anti hammer
            with db_session() as db:
                scrape = Scrape(
                    case_number=case_number,
                    timestamp=begin,
                    duration=duration,
                    error=type(e).__name__
                )
                db.add(scrape)
                # if 3 bad scrapes, scrape_exempt = True
                last_scrapes = db.query(Scrape).filter(Scrape.case_number == case_number).filter(Scrape.error != None).limit(3).all()
                if last_scrapes and len(last_scrapes) == 3:
                    db.execute(
                        Case.__table__.update()\
                            .where(Case.case_number == case_number)\
                            .values(scrape_exempt=True)
                    )
        else:
            await self.__store_case_details(case_number, detail_loc, response.text, begin, duration)

    def __check_scrape_response(self, case_number, response):
        if response.status_code == 500:
            raise FailedScrape500(f'{response.status_code}: {response.text}')
        elif response.status_code != 200:
            raise FailedScrapeUnknownError(f'{response.status_code}: {response.text}')
        elif re.search(r'<span class="error">\s*<br>CaseSearch will only display results',response.text):
            raise FailedScrapeNotFound
        elif 'Sorry, but your query has timed out after 2 minute' in response.text:
            raise FailedScrapeTimeout
        elif len(response.text) < 1000:
            raise FailedScrapeTooShort
        elif "An unexpected error occurred" in response.text:
            raise FailedScrapeUnexpectedError
        elif "Note: Initial Sort is by Last Name." in response.text:
            raise FailedScrapeSearchResults
        # case numbers will often be displayed with dashes and/or spaces between parts of it
        elif not re.search(r'[\- ]*'.join(case_number),response.text) \
                and not re.search(r'[\- ]*'.join(case_number.lower()),response.text):
            raise FailedScrapeNoCaseNumber

    async def __store_case_details(self, case_number, detail_loc, html, timestamp, scrape_duration=None):
        add = False
        try:
            with db_session() as db:
                latest_sha256, = db.query(ScrapeVersion.sha256).\
                    join(Scrape, ScrapeVersion.s3_version_id == Scrape.s3_version_id).\
                    filter(Scrape.case_number == case_number).\
                    order_by(Scrape.timestamp.desc())[0]
        except IndexError:
            logger.info(f"Case details for {case_number} not found, adding...")
            add = True
        else:
            new_sha256 = sha256(html.encode('utf-8')).hexdigest()
            if latest_sha256 != new_sha256:
                logger.info(f"Found new version of case {case_number}, updating...")
                add = True
        
        with db_session() as db:
            # last_scrape gets updated on a successful scrape, even if new version not added
            db.execute(
                Case.__table__.update()\
                    .where(Case.case_number == case_number)\
                    .values(last_scrape = timestamp)
            )

            if add:
                obj = config.case_details_bucket.put_object(
                    Body = html,
                    Key = case_number,
                    Metadata = {
                        'timestamp': timestamp.isoformat(),
                        'detail_loc': detail_loc
                    }
                )
                try:
                    version_id = obj.version_id
                except botocore.exceptions.ClientError:
                    # Sometimes the version_id property isn't available from S3 when we first try to access it, so wait and try again
                    await trio.sleep(60)
                    version_id = obj.version_id

                with db_session() as db:
                    scrape_version = ScrapeVersion(
                        s3_version_id = version_id,
                        case_number = case_number,
                        length = len(html),
                        sha256 = sha256(html.encode('utf-8')).hexdigest()
                    )
                    scrape = Scrape(
                        case_number = case_number,
                        s3_version_id = version_id,
                        timestamp = timestamp,
                        duration = scrape_duration
                    )
                    db.add(scrape_version)
                    db.flush() # to satisfy foreign key constraint of scrapes
                    db.add(scrape)
