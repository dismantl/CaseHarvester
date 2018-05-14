from ..config import config
from ..db import db_session
from ..case import Case, cases_batch_filter, get_detail_loc
from sqlalchemy import and_
import boto3
import json
import concurrent.futures
import time

# TODO move these to config
THREADS = 8 # number of logical cores on my Macbook Pro
CONCURRENCY_AVAILABLE = 140
CONCURRENCY_RATIO = 1.0
AVERAGE_PARSER_DURATION = 5 # seconds

s3 = boto3.client('s3')
sqs = boto3.resource('sqs')
sns = boto3.client('sns')

# begin parser module exports
from .DSCR import DSCRParser
from .DSK8 import DSK8Parser
from .DSCIVIL import DSCIVILParser

parsers = [
    ('DSCR',DSCRParser),
    ('DSK8',DSK8Parser),
    ('DSCIVIL',DSCIVILParser)
]

def parse_case_from_html(case_number, detail_loc, html):
    for category,parser in parsers:
        if detail_loc == category:
            return parser(case_number, html).parse()
    raise NotImplementedError('Unsupported case type: %s' % detail_loc)

def parse_case(case_number, detail_loc=None):
    case_details = s3.get_object(
        Bucket = config.CASE_DETAILS_BUCKET,
        Key = case_number
    )
    case_html = case_details['Body'].read().decode('utf-8')
    if not detail_loc:
        if 'detail_loc' in case_details['Metadata']:
            detail_loc = case_details['Metadata']['detail_loc']
        else:
            detail_loc = get_detail_loc(case_number)
    parse_case_from_html(case_number, detail_loc, case_html)

def parse_unparsed_cases(detail_loc=None, on_error=None):
    if detail_loc:
        filter = and_(Case.last_parse == None, Case.last_scrape != None,
            Case.detail_loc == detail_loc)
    else:
        filter = and_(Case.last_parse == None, Case.last_scrape != None, Case.detail_loc.in_([c for c,p in parsers]))
    with db_session() as db:
        num_cases = db.query(Case.case_number).filter(filter).count()
        case_count = 1
        for batch_filter in cases_batch_filter(db, filter):
            future_to_case_number = {}
            case_numbers = [x for x, in db.query(Case.case_number).filter(batch_filter)]
            for i in range(0, len(case_numbers), THREADS):
                case_number_batch = case_numbers[i:i+THREADS]
                with concurrent.futures.ThreadPoolExecutor(max_workers=THREADS) as executor:
                    for case_number in case_number_batch:
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

            # for case_number, in db.query(Case.case_number).filter(batch_filter):
            #     try:
            #         print('Parsing case %s (%s of %s)' % (case_number,x,num_cases))
            #         x += 1
            #         parse_case(case_number, detail_loc)
            #     except Exception as e:
            #         print("!!! Failed to parse %s !!!" % case_number)
            #         if on_error:
            #             on_error(e, case_number)
            #         else:
            #             raise e

def parse_failed_queue(detail_loc=None, on_error=None, nitems=10, wait_time=config.QUEUE_WAIT):
    failed_queue = sqs.get_queue_by_name(QueueName=config.PARSER_FAILED_QUEUE_NAME)
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
                case_type = get_detail_loc(case_number)
            elif 'Sns' in record:
                msg = json.loads(record['Sns']['Message'])
                case_number = msg['case_number']
                case_type = msg['detail_loc']
            if not detail_loc or detail_loc == case_type:
                try:
                    print('Parsing case',case_number)
                    parse_case(case_number, case_type)
                except Exception as e:
                    print("!!! Failed to parse %s !!!" % case_number)
                    if on_error:
                        r = on_error(e, case_number)
                        if r == 'delete':
                            item.delete() # TODO delete from S3 and set last_scrape = null for case
                    else:
                        raise e
                else:
                    item.delete() # remove from queue
            else:
                if not detail_loc:
                    print("No detail_loc specified")
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
                sns.publish(
                    TopicArn=config.PARSER_TRIGGER_ARN,
                    Message='{"case_number":"%s","detail_loc":"%s"}' % (case_number,case_type)
                )
                time.sleep( AVERAGE_PARSER_DURATION / ( CONCURRENCY_AVAILABLE * CONCURRENCY_RATIO ) ) # so lambda doesn't get throttled
