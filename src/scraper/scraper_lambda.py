from mjcs.config import config
from mjcs.util import db_session
from mjcs.models import Case
import json
from datetime import datetime, timedelta

def rescrape(options):
    # Required options
    days_ago_start = options['days_ago_start']
    days_ago_end = options['days_ago_end']

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
    print(f'Found {len(cases)} cases in time range')

    def chunks(l, n):
        for i in range(0, len(l), n):
            yield l[i:i + n]

    # add cases to scraper queue
    count = 0
    for chunk in chunks(cases, 10):  # can only do 10 messages per batch request
        count += len(chunk)
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
        config.scraper_queue.send_messages(
            Entries=Entries
        )
    print(f'Submitted {count} cases for rescraping')


def lambda_handler(event, context):
    # Required parameters
    command = event['command']
    options = event['options']
    
    if command == 'rescrape':
        return rescrape(options)

    raise Exception(f'Unknown command {command}')