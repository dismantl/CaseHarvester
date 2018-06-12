from mjcs.config import config
from mjcs.scraper import Scraper, NoItemsInQueue
import json
from datetime import *
import boto3

DYNAMODB_KEY='worker'

lambda_ = boto3.client('lambda')
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
    lambda_.invoke(
        FunctionName = context.function_name,
        InvocationType = 'Event',
        Payload = '{"worker":true,"last_invocation":"%s"}' % invoked_time
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
    else:
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
        else:
            print("Last worker invocation within %d minutes" % config.SCRAPER_LAMBDA_EXPIRY_MIN)
            return True

def items_count():
    config.scraper_queue.load() # refresh attributes
    return config.scraper_queue.attributes['ApproximateNumberOfMessages']

def lambda_handler(event, context):
    if 'worker' in event: # this is a worker invocation
        print("Worker invocation")
        check_invocation_time(event['last_invocation'])
        try:
            scraper.scrape_from_scraper_queue(nitems=config.SCRAPER_DEFAULT_CONCURRENCY)
        except NoItemsInQueue:
            mark_complete()
        else:
            start_worker(context)
    else: # Alarm/cron rule triggered
        print("Trigger invocation")
        if 'Records' in event:
            alarm = json.loads(event['Records'][0]['Sns']['Message'])
            if alarm['AlarmName'] != config.SCRAPER_QUEUE_ALARM_NAME:
                raise Exception("Unknown alarm message received")
        elif 'manual' in event:
            pass
        elif 'detail-type' in event and event['detail-type'] == 'Scheduled Event':
            pass
        else:
            raise Exception("Unknown message received")
        if not items_count():
            print("No items in queue. Exiting...")
            return
        if is_worker_running():
            print("Worker invocation is already running. Exiting...")
            return
        start_worker(context)
