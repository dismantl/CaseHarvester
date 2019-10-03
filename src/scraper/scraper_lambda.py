from mjcs.config import config
from mjcs.scraper import Scraper
from mjcs.util import NoItemsInQueue, db_session
from mjcs.models import Case
import json
from datetime import *

DYNAMODB_KEY='worker'

# on_error returns 'delete' so the case is removed from scraper queue regardless
# of if the scrape succeeded or failed
scraper = Scraper(threads=config.SCRAPER_DEFAULT_CONCURRENCY, on_error=lambda e,c: 'delete')

def mark_complete():
    print("Marking lambda invocation chain complete")
    config.scraper_table.delete_item(
        Key = {
            'id': DYNAMODB_KEY
        }
    )

def start_worker(context):
    print("Starting worker lambda invocation")
    invoked_time = datetime.now().isoformat()
    config.scraper_table.put_item( # will overwrite
        Item = {
            'id': DYNAMODB_KEY,
            'invoked': invoked_time
        }
    )
    config.lambda_.invoke(
        FunctionName = context.function_name,
        InvocationType = 'Event',
        Payload = '{"invocation":"worker","last_invocation":"%s"}' % invoked_time
    )

def check_invocation_time(last_invocation):
    worker_task = config.scraper_table.get_item(
        Key = {
            'id': DYNAMODB_KEY
        }
    )
    if not 'Item' in worker_task:
        raise Exception('Worker entry not found in Dynamodb table')
    if worker_task['Item']['invoked'] != last_invocation:
        raise Exception('Mismatched last invocation time')

def is_worker_running():
    worker_task = config.scraper_table.get_item(
        Key = {
            'id': DYNAMODB_KEY
        }
    )
    if not 'Item' in worker_task:
        print("No existing worker running")
        return False
    last_worker_invoked = datetime.strptime(worker_task['Item']['invoked'], "%Y-%m-%dT%H:%M:%S.%f")
    now = datetime.now()
    if now - last_worker_invoked > timedelta(minutes=config.SCRAPER_LAMBDA_EXPIRY_MIN):
        print("Last worker expired, removing from table")
        config.scraper_table.delete_item(
            Key = {
                'id': DYNAMODB_KEY
            }
        )
        return False
    print("Last worker invocation within %d minutes" % config.SCRAPER_LAMBDA_EXPIRY_MIN)
    return True

def items_count():
    config.scraper_queue.load() # refresh attributes
    return config.scraper_queue.attributes['ApproximateNumberOfMessages']

def rescrape_date_range(days_ago_start, days_ago_end):
    # calculate date range
    today = datetime.now().date()
    date_end = today - timedelta(days=days_ago_start)
    date_start = today - timedelta(days=days_ago_end)
    print(f'Rescraping cases between {date_start} and {date_end}')

    # query DB for cases filed in range
    with db_session() as db:
        cases = db.query(Case.case_number, Case.loc, Case.detail_loc).\
            filter(Case.filing_date >= date_start).\
            filter(Case.filing_date < date_end).\
            all()

    def chunks(l, n):
        for i in range(0, len(l), n):
            yield l[i:i + n]

    # add cases to scraper queue
    count = 0
    for chunk in chunks(cases, 10):  # can only do 10 messages per batch request
        count += len(chunk)
        config.scraper_queue.send_messages(
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
        )
    print(f'Submitted {count} cases for rescraping')

def lambda_handler(event, context):
    if 'Records' not in event and 'invocation' not in event:
        print(event)
        raise Exception('Received unknown event')

    if event.get('invocation') == 'worker':
        print("Worker invocation")
        check_invocation_time(event['last_invocation'])
        try:
            scraper.scrape_from_scraper_queue(nitems=config.SCRAPER_DEFAULT_CONCURRENCY)
        except NoItemsInQueue:
            mark_complete()
        else:
            start_worker(context)
    else: # Alarm/scheduled rule triggered
        print("Trigger invocation")
        if event.get('Records'):
            print('Received alarm trigger')
            alarm = json.loads(event['Records'][0]['Sns']['Message'])
            if alarm['AlarmName'] != config.SCRAPER_QUEUE_ALARM_NAME:
                raise Exception("Unknown alarm message received")
        elif event.get('invocation') == 'manual':
            print('Received manual trigger')
            print(event)
            print(context)
        elif event.get('invocation') == 'scheduled':
            print('Received scheduled trigger')
            if event.get('rescrape'):
                rescrape_date_range(
                    event['rescrape']['days_ago_start'],
                    event['rescrape']['days_ago_end']
                )

        if not items_count():
            print("No items in queue. Exiting...")
            return
        if is_worker_running():
            print("Worker invocation is already running. Exiting...")
            return
        start_worker(context)
