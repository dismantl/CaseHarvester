from ..config import config
from ..util import (NoItemsInQueue, db_session, cases_batch_filter, 
    get_detail_loc, send_to_queue)
from ..models import Case
from sqlalchemy import and_, distinct
import json
import logging
from os import getpid, cpu_count
from contextlib import contextmanager
from time import sleep

logger = logging.getLogger(__name__)

class BaseParserError(Exception):
    pass

# begin parser module exports
from .DSCR import DSCRParser
from .DSCP import DSCPParser
from .DSK8 import DSK8Parser
from .DSCIVIL import DSCIVILParser
from .CC import CCParser
from .ODYTRAF import ODYTRAFParser
from .ODYCRIM import ODYCRIMParser
from .ODYCIVIL import ODYCIVILParser
from .ODYCVCIT import ODYCVCITParser
from .DSTRAF import DSTRAFParser
from .K import KParser
from .PG import PGParser
from .DV import DVParser
from .MCCI import MCCIParser

parsers = [
    ('DSCR',DSCRParser),
    ('DSCP',DSCPParser),
    ('DSK8',DSK8Parser),
    ('DSCIVIL',DSCIVILParser),
    ('CC',CCParser),
    ('ODYTRAF',ODYTRAFParser),
    ('ODYCRIM',ODYCRIMParser),
    ('ODYCIVIL',ODYCIVILParser),
    ('ODYCVCIT',ODYCVCITParser),
    ('DSTRAF',DSTRAFParser),
    ('K',KParser),
    ('PG',PGParser),
    ('DV',DVParser),
    ('MCCI',MCCIParser)
]

def parse_case(case_number, detail_loc=None):
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
        if not detail_loc:
            detail_loc = get_detail_loc(case_number)
        logger.debug(f'Worker {getpid()} parsing {case_number} of type {detail_loc}')
        parse_case(case_number, detail_loc)
        logger.info(f'Successfully parsed case {case_number}')

    def parse_unparsed(self, detail_loc=None):
        logger.info(f'Loading unparsed cases of type {detail_loc if detail_loc else "ANY"} into parser queue')
        if detail_loc:
            filter = and_(Case.last_parse == None, Case.last_scrape != None,
                Case.detail_loc == detail_loc)
        else:
            filter = and_(Case.last_parse == None, Case.last_scrape != None,
                Case.detail_loc.in_([c for c,p in parsers]))
        with db_session() as db:
            self.load_into_queue(db.query(Case.case_number, Case.detail_loc).distinct().filter(filter), config.parser_queue)

    def reparse(self, detail_loc=None):
        logger.info(f'Loading all cases of type {detail_loc if detail_loc else "ANY"} into parser queue')
        if detail_loc:
            filter = and_(Case.last_scrape != None,
                Case.detail_loc == detail_loc)
        else:
            filter = and_(Case.last_scrape != None,
                Case.detail_loc.in_([c for c,p in parsers]))
        with db_session() as db:
            self.load_into_queue(db.query(Case.case_number, Case.detail_loc).distinct().filter(filter), config.parser_queue)

    def parse_from_queue(self, queue):
        from multiprocessing import Pool, set_start_method
        logger.info('Parsing cases from queue')
        if self.parallel:
            cpus = cpu_count()
            set_start_method('fork')  # multiprocessing logging won't work with the spawn method
            # start worker processes according to available CPU resources
            with Pool() as worker_pool:
                jobs = []
                while True:
                    try:
                        cases = self.__fetch_cases_from_queue(queue)
                    except NoItemsInQueue:
                        logger.info('No items found in queue')
                        break
                    for case_number, detail_loc, receipt_handle in cases:    
                        if not detail_loc:
                            detail_loc = get_detail_loc(case_number)
                        logger.debug(f'Dispatching {case_number} {detail_loc} to worker')
                        def callback_wrapper(case_number, receipt_handle):
                            def callback(_):
                                logger.debug(f'Deleting {case_number} from queue')
                                queue.delete_messages(Entries=[{'Id': 'unused', 'ReceiptHandle': receipt_handle}])
                            return callback
                        callback = callback_wrapper(case_number, receipt_handle)
                        job = worker_pool.apply_async(self.parse_case, (case_number, detail_loc), callback=callback, error_callback=callback)
                        jobs.append((job, case_number, detail_loc))
                    # Prune completed jobs from active list
                    while len(jobs) > cpus:
                        for job, case_number, detail_loc in jobs:
                            try:
                                if job.ready():
                                    try:
                                        job.get()  # To re-raise exceptions from child process
                                    except NotImplementedError:
                                        pass
                                    except Exception as e:
                                        if not detail_loc:
                                            detail_loc = get_detail_loc(case_number)
                                        logger.error(f'Error parsing case {case_number} ({config.MJCS_BASE_URL}/inquiryDetail.jis?caseId={case_number}&detailLoc={detail_loc}): {e}', exc_info=not self.ignore_errors)
                                        if not self.ignore_errors:
                                            raise
                                    jobs.remove((job, case_number, detail_loc))
                            except ValueError:
                                # Job not finished, let it keep running
                                pass
                logger.info('Wait for remaining jobs to complete before exiting')
                for job,_,_ in jobs:
                    job.wait(timeout=60)
        else:
            while True:
                try:
                    cases = self.__fetch_cases_from_queue(queue)
                except NoItemsInQueue:
                    logger.info('No items found in queue')
                    break
                for case_number, detail_loc, receipt_handle in cases:
                    try:
                        self.parse_case(case_number, detail_loc)
                    except NotImplementedError:
                        pass
                    except Exception as e:
                        if not detail_loc:
                            detail_loc = get_detail_loc(case_number)
                        logger.error(f'Error parsing case {case_number} ({config.MJCS_BASE_URL}/inquiryDetail.jis?caseId={case_number}&detailLoc={detail_loc}): {e}', exc_info=not self.ignore_errors)
                        if not self.ignore_errors:
                            raise
                    finally:
                        queue.delete_messages(Entries=[{'Id': 'unused', 'ReceiptHandle': receipt_handle}])
    
    def load_into_queue(self, query, queue):
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
        send_to_queue(queue, messages)
        logger.debug(f'Sent {len(messages)} messages to queue')

    def __fetch_cases_from_queue(self, queue):
        logger.debug('Requesting 10 items from queue')
        queue_items = queue.receive_messages(
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