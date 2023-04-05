from ..config import config
from ..util import (NoItemsInQueue, db_session, get_detail_loc, send_to_queue)
from ..models import Case
from sqlalchemy import and_, update, select, text
from sqlalchemy.exc import PendingRollbackError, IntegrityError
import json
import logging
from os import getpid, cpu_count

logger = logging.getLogger('mjcs')

class BaseParserError(Exception):
    pass

class ParserError(BaseParserError):
    def __init__(self, message, content=None):
        self.message = message
        self.content = content

class UnparsedDataError(BaseParserError):
    def __init__(self, message, content):
        self.message = message
        self.content = content

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
from .PGV import PGVParser
from .MCCR import MCCRParser
from .ODYCOSA import ODYCOSAParser
from .ODYCOA import ODYCOAParser

# ordered by most common case type
parsers = {
    'ODYCIVIL': ODYCIVILParser,
    'ODYTRAF': ODYTRAFParser,
    'DSTRAF': DSTRAFParser,
    'ODYCRIM': ODYCRIMParser,
    'DSCR': DSCRParser,
    'DSCIVIL': DSCIVILParser,
    'CC': CCParser,
    'MCCI': MCCIParser,
    'PGV': PGVParser,
    'DSK8': DSK8Parser,
    'DV': DVParser,
    'DSCP': DSCPParser,
    'PG': PGParser,
    'ODYCVCIT': ODYCVCITParser,
    'MCCR': MCCRParser,
    'K': KParser,
    'ODYCOSA': ODYCOSAParser,
    'ODYCOA': ODYCOAParser
}

def parse_case(case_number, detail_loc=None, parse_as=None):
    case_details = config.case_details_bucket.Object(case_number).get()
    case_html = case_details['Body'].read().decode('utf-8')
    if not detail_loc:
        try:
            detail_loc = case_details['Metadata']['detail_loc']
        except KeyError:
            detail_loc = get_detail_loc(case_number)

    if parse_as:
        logger.debug(f'Parsing case {case_number} as {parse_as}')
        parser = parsers[parse_as]
        parser(case_number, case_html).parse()
        logger.debug(f"Successfully parsed {case_number} as {parse_as}")
    else:
        logger.debug(f'Parsing case {case_number}')

        # If we know the detail_loc, first try that parser
        if detail_loc and detail_loc != 'Unknown':
            if detail_loc not in parsers.keys():
                err = f'Unsupported case type {detail_loc} for case number {case_number}'
                logger.debug(err)
                raise NotImplementedError(err)
            parser = parsers[detail_loc]
            try:
                parser(case_number, case_html).parse()
            except BaseParserError:
                logger.debug(f"Failed to parse {case_number} as current detail_loc {detail_loc}")
            else:
                logger.debug(f"Successfully parsed {case_number}")
                return
        
        # Try all parsers
        for category, parser in parsers.items():
            try:
                parser(case_number, case_html).parse()
            except BaseParserError:
                logger.debug(f"Failed to parse {case_number} as {category}")
            else:
                logger.debug(f"Successfully parsed {case_number} as {category}")
                with db_session() as db:
                    db.execute(
                        update(Case)
                        .filter_by(case_number=case_number)
                        .values(detail_loc=category)
                    )
                    if detail_loc and detail_loc != 'Unknown':
                        db.execute(
                            text(f"DELETE FROM {detail_loc} WHERE case_number=:case_number"),
                            {'case_number': case_number}
                        )
                return
        err = f'Failed to parse case number {case_number}'
        logger.debug(err)
        raise ParserError(err)

class Parser:
    def __init__(self, ignore_errors=False, parallel=False):
        self.ignore_errors = ignore_errors
        self.parallel = parallel
        from multiprocessing_logging import install_mp_handler
        install_mp_handler(logger)

    def parse_case(self, case_number, detail_loc=None, parse_as=None):
        logger.debug(f'Worker {getpid()} parsing {case_number} of type {parse_as or detail_loc}')
        parse_case(case_number, detail_loc, parse_as)

    def parse_unparsed(self, detail_loc=None):
        logger.info(f'Loading unparsed cases of type {detail_loc if detail_loc else "ANY"} into parser queue')
        if detail_loc:
            filter = and_(Case.last_parse == None, Case.last_scrape != None,
                Case.detail_loc == detail_loc)
        else:
            filter = and_(Case.last_parse == None, Case.last_scrape != None,
                Case.detail_loc.in_(parsers.keys()))
        with db_session() as db:
            self.load_into_queue(db.execute(select(Case.case_number, Case.detail_loc).distinct().where(filter)).all(), config.parser_queue)
    
    def parse_stale(self, detail_loc=None):
        logger.info(f'Loading stale cases of type {detail_loc if detail_loc else "ANY"} into parser queue')
        if detail_loc:
            filter = and_(Case.last_parse != None, Case.last_scrape != None,
                Case.last_parse < Case.last_scrape ,Case.detail_loc == detail_loc)
        else:
            filter = and_(Case.last_parse == None, Case.last_scrape != None,
                Case.last_parse < Case.last_scrape, Case.detail_loc.in_(parsers.keys()))
        with db_session() as db:
            self.load_into_queue(db.execute(select(Case.case_number, Case.detail_loc).distinct().where(filter)).all(), config.parser_queue)

    def reparse(self, detail_loc=None):
        logger.info(f'Loading all cases of type {detail_loc if detail_loc else "ANY"} into parser queue')
        if detail_loc:
            filter = and_(Case.last_scrape != None,
                Case.detail_loc == detail_loc)
        else:
            filter = and_(Case.last_scrape != None,
                Case.detail_loc.in_(parsers.keys()))
        with db_session() as db:
            self.load_into_queue(db.execute(select(Case.case_number, Case.detail_loc).distinct().where(filter)).all(), config.parser_queue)

    def parse_from_queue(self, queue, parse_as=None):
        if parse_as:
            logger.info(f'Parsing cases from queue as {parse_as}')
        else:
            logger.info('Parsing cases from queue')
        
        if self.parallel:
            from multiprocessing import Pool
            cpus = cpu_count()
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
                        logger.debug(f'Dispatching {case_number} {parse_as or detail_loc} to worker')
                        def callback_wrapper(case_number, receipt_handle):
                            def callback(_):
                                logger.debug(f'Deleting {case_number} from queue')
                                queue.delete_messages(Entries=[{'Id': 'unused', 'ReceiptHandle': receipt_handle}])
                            return callback
                        callback = callback_wrapper(case_number, receipt_handle)
                        job = worker_pool.apply_async(self.parse_case, (case_number, detail_loc, parse_as), callback=callback, error_callback=callback)
                        jobs.append((job, case_number, parse_as or detail_loc))
                    # Prune completed jobs from active list
                    while len(jobs) > cpus:
                        for job, case_number, detail_loc in jobs:
                            try:
                                if job.ready():
                                    try:
                                        job.get()  # To re-raise exceptions from child process
                                    except NotImplementedError:
                                        pass
                                    except (BaseParserError, PendingRollbackError, IntegrityError) as e:
                                        if self.ignore_errors:
                                            logger.error(f'Error parsing case {case_number} (https://mdcaseexplorer.com/case/{case_number}): {e}', exc_info=not self.ignore_errors)
                                        else:
                                            logger.error(f'Error parsing case {case_number} (https://mdcaseexplorer.com/case/{case_number})')
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
                        parse_case(case_number, detail_loc, parse_as)
                    except NotImplementedError:
                        pass
                    except BaseParserError as e:
                        if self.ignore_errors:
                            logger.error(f'Error parsing case {case_number} (https://mdcaseexplorer.com/case/{case_number}): {e}', exc_info=not self.ignore_errors)
                        else:
                            logger.error(f'Error parsing case {case_number} (https://mdcaseexplorer.com/case/{case_number})')
                            raise
                    finally:
                        queue.delete_messages(Entries=[{'Id': 'unused', 'ReceiptHandle': receipt_handle}])
    
    def load_into_queue(self, results, queue):
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
            }) for case_number, detail_loc in results
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
            detail_loc = None
            if 's3' in record:
                case_number = record['s3']['object']['key']
            elif 'Sns' in record:
                msg = json.loads(record['Sns']['Message'])
                case_number = msg['case_number']
                detail_loc = msg['detail_loc']
            elif 'manual' in record:
                case_number = record['manual']['case_number']
                detail_loc = record['manual']['detail_loc']
            cases.append((case_number, detail_loc, item.receipt_handle))
        return cases