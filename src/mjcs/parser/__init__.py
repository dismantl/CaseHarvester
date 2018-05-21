from ..config import config
from ..db import db_session
from ..case import Case, cases_batch_filter, get_detail_loc
from sqlalchemy import and_
import boto3
import json
import concurrent.futures
import time

# TODO move these to config
CONCURRENCY_AVAILABLE = 87
CONCURRENCY_RATIO = 0.9
AVERAGE_PARSER_DURATION = 5 # seconds

case_details_bucket = boto3.resource('s3').Bucket(config.CASE_DETAILS_BUCKET)
failed_queue = boto3.resource('sqs').get_queue_by_name(QueueName=config.PARSER_FAILED_QUEUE_NAME)
parser_trigger = boto3.resource('sns').Topic(config.PARSER_TRIGGER_ARN)

# begin parser module exports
from .DSCR import DSCRParser
from .DSK8 import DSK8Parser
from .DSCIVIL import DSCIVILParser
from .CC import CCParser

parsers = [
    ('DSCR',DSCRParser),
    ('DSK8',DSK8Parser),
    ('DSCIVIL',DSCIVILParser),
    ('CC',CCParser)
]

def parse_case_from_html(case_number, detail_loc, html):
    for category,parser in parsers:
        if detail_loc == category:
            return parser(case_number, html).parse()
    raise NotImplementedError('Unsupported case type: %s' % detail_loc)

def parse_case(case_number):
    case_details = case_details_bucket.Object(case_number).get()
    case_html = case_details['Body'].read().decode('utf-8')
    try:
        detail_loc = case_details['Metadata']['detail_loc']
    except KeyError:
        detail_loc = get_detail_loc(case_number)
    parse_case_from_html(case_number, detail_loc, case_html)

def parse_unparsed_cases(detail_loc=None, on_error=None, threads=1):
    if detail_loc:
        filter = and_(Case.last_parse == None, Case.last_scrape != None,
            Case.detail_loc == detail_loc)
    else:
        filter = and_(Case.last_parse == None, Case.last_scrape != None, Case.detail_loc.in_([c for c,p in parsers]))
    with db_session() as db:
        num_cases = db.query(Case.case_number).filter(filter).count()
        case_count = 1
        for batch_filter in cases_batch_filter(db, filter):
            if threads > 1:
                future_to_case_number = {}
                cases = list(db.query(Case.case_number).filter(batch_filter))
                for i in range(0, len(cases), threads):
                    case_batch = cases[i:i+threads]
                    with concurrent.futures.ThreadPoolExecutor(max_workers=threads) as executor:
                        for case_number, in case_batch:
                            print('Parsing case %s (%s of %s)' % (case_number,case_count,num_cases))
                            case_count += 1
                            future_to_case_number[executor.submit(parse_case, case_number)] = case_number
                        for future in concurrent.futures.as_completed(future_to_case_number):
                            case_number = future_to_case_number[future]
                            try:
                                future.result()
                            except NotImplementedError:
                                pass
                            except Exception as e:
                                print("!!! Failed to parse %s !!!" % case_number)
                                if on_error:
                                    on_error(e, case_number)
                                else:
                                    raise e
            else:
                for case_number, in db.query(Case.case_number).filter(batch_filter):
                    try:
                        print('Parsing case %s (%s of %s)' % (case_number,case_count,num_cases))
                        case_count += 1
                        parse_case(case_number)
                    except Exception as e:
                        print("!!! Failed to parse %s !!!" % case_number)
                        if on_error:
                            on_error(e, case_number)
                        else:
                            raise e

def parse_failed_queue(detail_loc=None, on_error=None, nitems=10, wait_time=config.QUEUE_WAIT):
    while True:
        queue_items = failed_queue.receive_messages(
            WaitTimeSeconds = wait_time,
            MaxNumberOfMessages = nitems
        )
        if not queue_items:
            print("No items found in queue")
            break
        for item in queue_items:
            record = json.loads(item.body)['Records'][0]
            if 's3' in record:
                case_number = record['s3']['object']['key']
                if detail_loc:
                    case_type = get_detail_loc(case_number)
                else:
                    case_type = None
            elif 'Sns' in record:
                msg = json.loads(record['Sns']['Message'])
                case_number = msg['case_number']
                case_type = msg['detail_loc']
            if not detail_loc or detail_loc == case_type:
                try:
                    print('Parsing case',case_number)
                    parse_case(case_number)
                except NotImplementedError:
                    item.delete() # remove from queue
                except Exception as e:
                    print("!!! Failed to parse %s !!!" % case_number)
                    if on_error:
                        if on_error(e, case_number) == 'delete':
                            item.delete()
                    else:
                        raise e
                else:
                    item.delete() # remove from queue
            else:
                print("item %s doesn't match type" % case_number, case_type)

def invoke_parser_lambda(detail_loc=None):
    if detail_loc:
        filter = and_(Case.last_parse == None, Case.last_scrape != None,
            Case.detail_loc == detail_loc)
    else:
        filter = and_(Case.last_parse == None, Case.last_scrape != None,
            Case.detail_loc.in_([c for c,p in parsers]))
    with db_session() as db:
        num_cases = db.query(Case.case_number).filter(filter).count()
        case_count = 1
        for batch_filter in cases_batch_filter(db, filter):
            for case_number,case_type in db.query(Case.case_number,Case.detail_loc).filter(batch_filter):
                print('Invoking Parser lambda for case %s (%s of %s)' % (case_number,case_count,num_cases))
                case_count += 1
                parser_trigger.publish(
                    Message='{"case_number":"%s","detail_loc":"%s"}' % (case_number,case_type)
                )
                time.sleep( AVERAGE_PARSER_DURATION / ( CONCURRENCY_AVAILABLE * CONCURRENCY_RATIO ) ) # so lambda doesn't get throttled
