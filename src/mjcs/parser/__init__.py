from ..config import config
from ..util import (fetch_from_queue, NoItemsInQueue, db_session, cases_batch_filter, 
    get_detail_loc, send_to_queue)
from ..models import Case
from sqlalchemy import and_
import json
import time
import concurrent.futures
import logging
import queue
from os import getpid
from contextlib import contextmanager

logger = logging.getLogger(__name__)

class BaseParserError(Exception):
    pass

# begin parser module exports
from .DSCR import DSCRParser
from .DSK8 import DSK8Parser
from .DSCIVIL import DSCIVILParser
from .CC import CCParser
from .ODYTRAF import ODYTRAFParser
from .ODYCRIM import ODYCRIMParser

parsers = [
    ('DSCR',DSCRParser),
    ('DSK8',DSK8Parser),
    ('DSCIVIL',DSCIVILParser),
    ('CC',CCParser),
    ('ODYTRAF',ODYTRAFParser),
    ('ODYCRIM',ODYCRIMParser)
]

def load_failed_queue(ncases, detail_loc=None):
    if detail_loc:
        filter = and_(Case.last_parse == None, Case.last_scrape != None,
            Case.parse_exempt != True, Case.detail_loc == detail_loc)
    else:
        filter = and_(Case.last_parse == None, Case.last_scrape != None,
            Case.parse_exempt != True, Case.detail_loc.in_([c for c,p in parsers]))
    with db_session() as db:
        logger.info('Generating batch queries')
        batch_filters = cases_batch_filter(db, filter, limit=ncases if ncases != 'all' else None)
    for batch_filter in batch_filters:
        with db_session() as db:
            logger.debug('Fetching batch of cases from database')
            query = db.query(Case.case_number, Case.detail_loc).filter(batch_filter)
            if ncases != 'all':
                query = query.limit(ncases)
            messages = [
                json.dumps({
                    'Records': [
                        {
                            'manual': {
                                'case_number': case_number,
                                'detail_loc': detail_loc
                            }
                        }
                    ]
                }) for case_number, detail_loc in query
            ]
            send_to_queue(config.parser_failed_queue, messages)

def parse_case(case_number, detail_loc=None):
    # check if parse_exempt before scraping
    with db_session() as db:
        if db.query(Case.parse_exempt).filter(Case.case_number == case_number).scalar() == True:
            return
    case_details = config.case_details_bucket.Object(case_number).get()
    case_html = case_details['Body'].read().decode('utf-8')
    if not detail_loc:
        try:
            detail_loc = case_details['Metadata']['detail_loc']
        except KeyError:
            detail_loc = get_detail_loc(case_number)
    logger.debug(f'Parsing case {case_number}')
    for category,parser in parsers:
        if detail_loc == category:
            return parser(case_number, case_html).parse()
    err = f'Unsupported case type {detail_loc} for case number {case_number}'
    logger.debug(err)
    raise NotImplementedError(err)

class Parser:
    def __init__(self, ignore_errors=False, parallel=False):
        self.ignore_errors = ignore_errors
        self.parallel = parallel
        from multiprocessing_logging import install_mp_handler
        install_mp_handler(logger)

    def parse_case(self, case_number, detail_loc=None):
        logger.debug(f'Worker {getpid()} parsing {case_number} of type {detail_loc}')
        try:
            parse_case(case_number, detail_loc)
        except BaseParserError as e:
            logger.error(f'Error parsing case {case_number} (http://casesearch.courts.state.md.us/casesearch/inquiryDetail.jis?caseId={case_number}&detailLoc={detail_loc}): {e}', exc_info=not self.ignore_errors)
            if not self.ignore_errors:
                raise

    def parse_failed_queue(self):
        from multiprocessing import Pool, set_start_method
        logger.info('Parsing cases from failed queue')
        if self.parallel:
            set_start_method('fork')  # multiprocessing logging won't work with the spawn method
            # start worker processes according to available CPU resources
            with Pool() as worker_pool:
                jobs = []
                while True:
                    try:
                        cases = self.__fetch_cases_from_failed_queue()
                    except NoItemsInQueue:
                        logger.info('No items found in parser failed queue')
                        break
                    for case_number, detail_loc, receipt_handle in cases:    
                        logger.debug(f'Dispatching {case_number} {detail_loc} to worker')
                        def callback_wrapper(case_number, receipt_handle):
                            def callback(unused):
                                logger.debug(f'Deleting {case_number} from parser failed queue')
                                config.parser_failed_queue.delete_messages(Entries=[{'Id': 'unused', 'ReceiptHandle': receipt_handle}])
                            return callback
                        callback = callback_wrapper(case_number, receipt_handle)
                        job = worker_pool.apply_async(self.parse_case, (case_number, detail_loc), callback=callback, error_callback=callback)
                        jobs.append(job)
                    # Prune completed jobs from active list
                    for job in jobs:
                        try:
                            if job.ready():
                                jobs.remove(job)
                        except ValueError:
                            # Job not finished, let it keep running
                            pass
                logger.info('Wait for remaining jobs to complete before exiting')
                for job in jobs:
                    job.wait(timeout=60)
        else:
            while True:
                try:
                    cases = self.__fetch_cases_from_failed_queue()
                except NoItemsInQueue:
                    logger.info('No items found in parser failed queue')
                    break
                for case_number, detail_loc, receipt_handle in cases:
                    self.parse_case(case_number, detail_loc)
                    config.parser_failed_queue.delete_messages(Entries=[{'Id': 'unused', 'ReceiptHandle': receipt_handle}])
    
    def __fetch_cases_from_failed_queue(self):
        logger.debug('Requesting 10 items from parser failed queue')
        queue_items = config.parser_failed_queue.receive_messages(
            WaitTimeSeconds = config.QUEUE_WAIT,
            MaxNumberOfMessages = 10
        )
        if not queue_items:
            raise NoItemsInQueue
        cases = []
        for item in queue_items:
            record = json.loads(item.body)['Records'][0]
            if 's3' in record:
                case_number = record['s3']['object']['key']
                detail_loc = None
            elif 'Sns' in record:
                msg = json.loads(record['Sns']['Message'])
                case_number = msg['case_number']
                detail_loc = msg['detail_loc']
            elif 'manual' in record:
                case_number = record['manual']['case_number']
                detail_loc = record['manual']['detail_loc']
            cases.append((case_number, detail_loc, item.receipt_handle))
        return cases