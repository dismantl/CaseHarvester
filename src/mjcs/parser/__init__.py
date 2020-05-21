from ..config import config
from ..util import fetch_from_queue, NoItemsInQueue, db_session, cases_batch_filter, get_detail_loc, process_cases
from ..models import Case
from sqlalchemy import and_
import json
import time
import concurrent.futures
import logging

logger = logging.getLogger(__name__)

# TODO move these to config
CONCURRENCY_AVAILABLE = 87
CONCURRENCY_RATIO = 0.9
AVERAGE_PARSER_DURATION = 5 # seconds

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

def parse_case_from_html(case_number, detail_loc, html):
    for category,parser in parsers:
        if detail_loc == category:
            return parser(case_number, html).parse()
    err = f'Unsupported case type {detail_loc} for case number {case_number}'
    logger.debug(err)
    raise NotImplementedError(err)

def parse_case(case, detail_loc=None):
    case_number = case['case_number'] if isinstance(case, dict) else case
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
    return parse_case_from_html(case_number, detail_loc, case_html)

def invoke_parser_lambda(detail_loc=None):
    if detail_loc:
        filter = and_(Case.last_parse == None, Case.last_scrape != None,
            Case.parse_exempt != True, Case.detail_loc == detail_loc)
    else:
        filter = and_(Case.last_parse == None, Case.last_scrape != None,
            Case.parse_exempt != True, Case.detail_loc.in_([c for c,p in parsers]))
    with db_session() as db:
        num_cases = db.query(Case.case_number).filter(filter).count()
        case_count = 1
        for batch_filter in cases_batch_filter(db, filter):
            for case_number,detail_loc in db.query(Case.case_number,Case.detail_loc).filter(batch_filter):
                logger.debug(f'Invoking Parser lambda for case {case_number} ({case_count} of {num_cases})')
                case_count += 1
                config.parser_trigger.publish(
                    Message='{"case_number":"%s","detail_loc":"%s"}' % (case_number,detail_loc)
                )
                time.sleep( AVERAGE_PARSER_DURATION / ( CONCURRENCY_AVAILABLE * CONCURRENCY_RATIO ) ) # so lambda doesn't get throttled

class Parser:
    def __init__(self, on_error=None, threads=1):
        self.on_error = on_error
        self.threads = threads

    def parse_case(self, case_number):
        return parse_case(case_number)

    def parse_unparsed_cases(self, detail_loc=None):
        if detail_loc:
            filter = and_(Case.last_parse == None, Case.last_scrape != None,
                Case.parse_exempt != True, Case.detail_loc == detail_loc)
        else:
            filter = and_(Case.last_parse == None, Case.last_scrape != None,
                Case.parse_exempt != True, Case.detail_loc.in_([c for c,p in parsers]))
        with db_session() as db:
            logger.info('Generating batch queries')
            batch_filters = cases_batch_filter(db, filter)
        for batch_filter in batch_filters:
            with db_session() as db:
                logger.debug('Fetching batch of cases from database')
                case_numbers = [c for c, in db.query(Case.case_number).filter(batch_filter)]
                logger.debug('Done.')
            process_cases(parse_case, case_numbers, None, self.on_error, self.threads)

    def parse_failed_queue(self, detail_loc=None):
        counter = {
            'total': 0,
            'count': 0
        }

        while True:
            queue_items = fetch_from_queue(config.parser_failed_queue)
            if not queue_items:
                logger.info("No items found in queue")
                break
            counter['total'] += len(queue_items)

            missing_case_type = {}
            cases = []
            case_number_to_item = {}
            for item in queue_items:
                record = json.loads(item.body)['Records'][0]
                if 's3' in record:
                    case_number = record['s3']['object']['key']
                    if detail_loc:
                        missing_case_type[case_number] = item
                    else:
                        cases.append({
                            'case_number': case_number,
                            'item': item
                        })
                        case_number_to_item[case_number] = item
                elif 'Sns' in record:
                    msg = json.loads(record['Sns']['Message'])
                    case_number = msg['case_number']
                    case_type = msg['detail_loc']
                    if not detail_loc or detail_loc == case_type:
                        cases.append({
                            'case_number': case_number,
                            'item': item
                        })
                        case_number_to_item[case_number] = item

            if missing_case_type:
                with db_session() as db:
                    query = db.query(Case.case_number,Case.detail_loc).filter(Case.case_number.in_([x for x in missing_case_type.keys()]))
                    for case_number, case_type in query:
                        if detail_loc == case_type:
                            cases.append({
                                'case_number': case_number,
                                'item': missing_case_type[case_number]
                            })
                            case_number_to_item[case_number] = missing_case_type[case_number]

            def queue_on_success(case):
                case['item'].delete()
            def queue_on_error(exception, case):
                if self.on_error:
                    action = self.on_error(exception, case['case_number'])
                    if action == 'delete':
                        case['item'].delete()
                    return action
                raise exception

            process_cases(parse_case, cases, queue_on_success, queue_on_error, self.threads, counter)

        logger.info(f"Total number of parsed cases: {counter['count']}")
        if counter['count'] == 0:
            raise NoItemsInQueue
