from .config import config
from .session import MjcsSession, RequestTimeout, Forbidden
from .util import db_session, get_detail_loc, send_to_queue, get_queue_count, RepeatedTimer
from .models import ScrapeVersion, Scrape, Case
from hashlib import sha256
import logging
import botocore
import boto3
import re
import json
import time
import requests
from datetime import datetime, timedelta
from sqlalchemy import and_, or_, text, select, func
from bs4 import BeautifulSoup

logger = logging.getLogger('mjcs')

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
    def __init__(self):
        self.scrapes = 0
        self.last_scrape_count = 0
        self.last_request_count = 0
        self.metrics = []
    
    @property
    def instance_id(self):
        if not hasattr(self, '_instance_id'):
            from ec2_metadata import ec2_metadata
            self._instance_id = ec2_metadata.instance_id
        return self._instance_id

    @property
    def session(self):
        if not hasattr(self, '_session'):
            self._session = MjcsSession()
        return self._session

    def record_metrics(self):
        now = datetime.now()
        new_scrape_count = self.scrapes
        delta_scrapes = new_scrape_count - self.last_scrape_count
        self.last_scrape_count = new_scrape_count

        new_request_count = self.session.requests
        delta_requests = new_request_count - self.last_request_count
        self.last_request_count = new_request_count

        dimensions = [
            {
                'Name': 'InstanceId',
                'Value': self.instance_id
            },
            {
                'Name': 'Environment',
                'Value': config.environment
            }
        ]
        self.metrics += [
            {
                'MetricName': 'Scrapes',
                'Dimensions': dimensions,
                'Timestamp': now,
                'Value': delta_scrapes
            },
            {
                'MetricName': 'ScraperRequests',
                'Dimensions': dimensions,
                'Timestamp': now,
                'Value': delta_requests
            }
        ]
        
    def report(self):
        config.boto3_session.client('cloudwatch').put_metric_data(
            Namespace='CaseHarvester',
            MetricData=self.metrics
        )

    def stale_filter(self, range_start_date=None, range_end_date=None, include_unscraped=False, include_inactive=False):
        or_filters = [and_(
            Case.active == True,
            or_(
                text("cases.filing_date > current_date"),  # Sometimes MJCS lists filing dates in the future
                or_(
                    text(f"age_days(cases.last_scrape) > ceiling({config.RESCRAPE_COEFFICIENT}*age_days(cases.filing_date))"),
                    text(f"age_days(cases.last_scrape) > {config.MAX_SCRAPE_AGE}")  # age_days function is defined in db/sql/functions.sql
                )
            )
        )]

        if include_unscraped:
            or_filters.append(Case.last_scrape == None)
        
        if include_inactive:
            or_filters.append(and_(
                Case.active == False,
                or_(
                    text("cases.filing_date > current_date"),
                    text(f"age_days(cases.last_scrape) > {config.MAX_SCRAPE_AGE_INACTIVE}")
                )
            ))

        filters = [
            Case.scrape_exempt == False,
            or_(*or_filters)
        ]

        if range_start_date:
            filters.append(Case.filing_date >= range_start_date)
        
        if range_end_date:
            filters.append(Case.filing_date <= range_end_date)

        return and_(*filters)

    def count_stale(self, range_start_date=None, range_end_date=None, include_unscraped=False, include_inactive=False):
        with db_session() as db:
            return db.scalar(
                select(func.count(Case.case_number))
                .where(self.stale_filter(range_start_date, range_end_date, include_unscraped, include_inactive))
            )

    def rescrape_stale(self, range_start_date=None, range_end_date=None, include_unscraped=False, include_inactive=False):
        # Abort if the scraper queue is already full
        if get_queue_count(config.scraper_queue) > config.SCRAPE_QUEUE_THRESHOLD:
            logger.info('Scraper queue is already full, aborting...')
            return
        
        filter = self.stale_filter(range_start_date, range_end_date, include_unscraped, include_inactive)
        total = 0
        with db_session() as db:
            partitions = db.execute(
                select(Case.case_number, Case.detail_loc)
                .where(filter)
                .execution_options(yield_per=10)
            ).partitions()
            for partition in partitions:
                # add cases to scraper queue
                messages = [
                    json.dumps({
                        'case_number': case[0],
                        'detail_loc': case[1]
                    }) for case in partition
                ]
                send_to_queue(config.scraper_queue, messages)
                logger.info(f'Submitted {len(partition)} cases for rescraping')
                total += len(partition)
        
        logger.info(f"Submitted a total of {total} cases for rescraping")

    def scrape_from_queue(self, record_metrics=False):
        if record_metrics:
            timer = RepeatedTimer(60, self.record_metrics)
            timer.start()
        try:
            while True:
                queue_items = config.scraper_queue.receive_messages(
                    WaitTimeSeconds = config.QUEUE_WAIT,
                    MaxNumberOfMessages = 10
                )
                if queue_items:
                    for item in queue_items:
                        body = json.loads(item.body)
                        case_number = body['case_number']
                        detail_loc = body.get('detail_loc')
                        try:
                            self.scrape_case(case_number, detail_loc)
                        except FailedScrape:
                            pass
                        item.delete()
                else:
                    logger.info('No items in scraper queue.')
                    break
        finally:
            if record_metrics:
                timer.stop()
                self.record_metrics()
                self.report()
            logger.info(f'Number of requests: {self.session.requests}')
            logger.info(f'Number of scrapes: {self.scrapes}')

    def scrape_case(self, case_number, detail_loc=None):
        logger.debug(f"Requesting case details for {case_number}")
        begin = datetime.now()

        # First we have to get the `searchtype` hidden field from the search page
        try:
            response = self.session.request(
                method='GET',
                url = f'{config.MJCS_BASE_URL}/inquirySearchParam.jis'
            )
        except requests.Timeout:
            raise RequestTimeout
        
        if response.status_code == 403:
            raise Forbidden
        elif response.status_code != 200:
            logger.debug(f"Failed to retrieve search page: {response.status_code}")
            raise FailedScrapeUnknownError(response.text)
        
        soup = BeautifulSoup(response.text, 'html.parser')
        searchtype = soup.find('input',{'name':'searchtype'}).get('value')

        # Now request the actual case details
        try:
            response = self.session.request(
                'POST',
                f'{config.MJCS_BASE_URL}/inquiryByCaseNum.jis',
                data = {
                    'caseId': case_number,
                    'searchtype': searchtype
                }
            )
        except requests.Timeout:
            raise RequestTimeout
        
        end = datetime.now()
        duration = (end - begin).total_seconds()

        # Handle scrape result
        self.scrapes += 1
        try:
            self.__check_scrape_response(case_number, response)
        except (FailedScrapeTimeout, FailedScrape500, FailedScrapeUnexpectedError, FailedScrapeUnknownError) as e:
            logger.debug(f'Scrape error {type(e).__name__}: {e}')
            time.sleep(1) #anti hammer
        except FailedScrape as e:
            logger.debug(f'Scrape error {type(e).__name__}: {e}')
            with db_session() as db:
                scrape = Scrape(
                    case_number=case_number,
                    timestamp=begin,
                    duration=duration,
                    error=type(e).__name__
                )
                db.add(scrape)
                # if 3 bad scrapes, scrape_exempt = True
                scrape_error_count = db.scalar(
                    select(func.count())
                    .select_from(Scrape)
                    .where(Scrape.case_number == case_number)
                    .where(Scrape.error != None)
                )
                if scrape_error_count >= 3:
                    db.execute(
                        Case.__table__.update()
                            .where(Case.case_number == case_number)
                            .values(scrape_exempt=True)
                    )
        else:
            self.__store_case_details(case_number, detail_loc, response.text, begin, duration)

    def __check_scrape_response(self, case_number, response):
        if response.status_code == 500:
            raise FailedScrape500(f'{response.status_code}: {response.text}')
        elif response.status_code == 403:
            raise Forbidden
        elif response.status_code != 200:
            raise FailedScrapeUnknownError(f'{response.status_code}: {response.text}')
        elif (re.search(r'<span class="error">\s*<br>CaseSearch will only display results',response.text) or
                re.search(r'Case Search will only return results that exactly match',response.text)):
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
        elif (not re.search(r'[- ]*'.join(case_number),response.text) and
                not re.search(r'[- ]*'.join(case_number.lower()),response.text)):
            raise FailedScrapeNoCaseNumber

    def __store_case_details(self, case_number, detail_loc, html, timestamp, scrape_duration=None):
        add = False
        with db_session() as db:
            latest_sha256 = db.scalars(
                select(ScrapeVersion.sha256)
                .join(Scrape, ScrapeVersion.s3_version_id == Scrape.s3_version_id)
                .where(Scrape.case_number == case_number)
                .order_by(Scrape.timestamp.desc())
            ).first()
        if not latest_sha256:
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
                Case.__table__.update()
                    .where(Case.case_number == case_number)
                    .values(last_scrape = timestamp)
            )

            if add:
                obj = config.case_details_bucket.put_object(
                    Body = html,
                    Key = case_number,
                    Metadata = {
                        'timestamp': timestamp.isoformat(),
                        'detail_loc': detail_loc or 'Unknown'
                    }
                )
                try:
                    version_id = obj.version_id
                except botocore.exceptions.ClientError as e:
                    logger.debug(f'S3 error {type(e).__name__}: {e}')
                    # Sometimes the version_id property isn't available from S3 when we first try to access it, so wait and try again
                    time.sleep(5)
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
