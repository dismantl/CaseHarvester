#!/usr/bin/env python3
from mjcs.parser import ODYCRIMParser, ODYCVCITParser, ODYTRAFParser, DSCRParser, DSK8Parser
from mjcs.util import db_session, get_detail_loc, send_to_queue, NoItemsInQueue
from mjcs.models import ODYCRIMCharge, ODYTRAFCharge, ODYCVCITCharge, Scrape, DSCRCharge, DSK8Charge
from mjcs.config import config
from sqlalchemy.sql import text
from sqlalchemy.exc import IntegrityError
from bs4 import BeautifulSoup, SoupStrainer
import re
import logging
import argparse
import os
from multiprocessing import Pool, set_start_method
import json
import csv
from copy import deepcopy

logger = logging.getLogger('mjcs')
parsers = {
    'ODYCRIM': (ODYCRIMCharge, ODYCRIMParser),
    'ODYTRAF': (ODYTRAFCharge, ODYTRAFParser),
    'ODYCVCIT': (ODYCVCITCharge, ODYCVCITParser),
    'DSCR': (DSCRCharge, DSCRParser),
    'DSK8': (DSK8Charge, DSK8Parser)
}

def load_queue(detail_loc=None):
    if detail_loc:
        query_text = f"""
            SELECT
                distinct case_number,
                detail_loc
            FROM
                scrape_versions 
                JOIN
                    cases USING (case_number) 
            WHERE
                detail_loc = '{detail_loc}'
                AND parse_exempt = FALSE
                AND last_parse IS NOT NULL
            GROUP BY
                case_number,
                detail_loc
            HAVING
                COUNT(*) >= 2
        """
    else:
        locs = "', '".join([k for k,_ in parsers.items()])
        query_text = f"""
            SELECT
                distinct case_number,
                detail_loc
            FROM
                scrape_versions 
                JOIN
                    cases USING (case_number) 
            WHERE
                detail_loc IN ('{locs}')
                AND parse_exempt = FALSE
                AND last_parse IS NOT NULL
            GROUP BY
                case_number,
                detail_loc
            HAVING
                COUNT(*) >= 2
        """
    logger.debug(f'Querying for cases')
    with db_session() as db:
        results = db.execute(text(query_text))
    logger.debug('Query complete')
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
    send_to_queue(config.parser_queue, messages)

def fetch_cases_from_queue():
    logger.debug('Requesting 10 items from parser queue')
    queue_items = config.parser_queue.receive_messages(
        WaitTimeSeconds = config.QUEUE_WAIT,
        MaxNumberOfMessages = 10
    )
    if not queue_items:
        raise NoItemsInQueue
    cases = []
    for item in queue_items:
        record = json.loads(item.body)['Records'][0]
        if 'manual' in record:
            case_number = record['manual']['case_number']
            detail_loc = record['manual']['detail_loc']
        cases.append((case_number, detail_loc, item.receipt_handle))
    return cases

def check_case(case_number, charge_cls, parser_cls, receipt_handle):
    logger.info(f'Processing {case_number}')
    
    # Fetch HTML from S3 and set up parser
    case_details = config.case_details_bucket.Object(case_number).get()
    case_html = case_details['Body'].read().decode('utf-8')
    parser = parser_cls(case_number, case_html)

    # Delete and reparse charges
    try:
        with db_session() as db:
            db.execute(charge_cls.__table__.delete()\
                .where(charge_cls.case_number == case_number))
            parser.charge_and_disposition(db, parser.soup)
            parser.update_last_parse(db)
    except IntegrityError:
        logger.warning(f'Reparsing {case_number} due to integrity error')
        try:
            parser.parse()
        except:
            logger.warning(f'Failed to parse {case_number}')
            pass
    logger.debug(f'Deleting {case_number} from parser queue')
    config.parser_queue.delete_messages(Entries=[{'Id': 'unused', 'ReceiptHandle': receipt_handle}])

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="Check DSCR, DSK8, ODYCRIM, ODYTRAF, and ODYCVCIT cases for expunged charges",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument('--environment', '--env', default='development',
        choices=['production','prod','development','dev'],
        help="Environment to run in (e.g. production, development)")
    parser.add_argument('--load-queue', nargs='?', const='all', default=None,
        help="Load cases into the parser queue for later processing.")
    parser.add_argument('--case', '-c', help="Check specific case number")
    parser.add_argument('--parallel', '-p', action='store_true', default=False,
        help=f"Search for expunged charges in parallel with {os.cpu_count()} worker processes")
    parser.add_argument('--verbose', '-v', action='store_true',
        help="Print debug information")
    args = parser.parse_args()
    if (hasattr(args, 'verbose') and args.verbose) or os.getenv('VERBOSE'):
        logger.setLevel(logging.DEBUG)
    config.initialize_from_environment(args.environment)

    if args.case:
        detail_loc = get_detail_loc(args.case)
        check_case(args.case, parsers[detail_loc][0], parsers[detail_loc][1])
    elif args.load_queue:
        if args.load_queue == 'all':
            load_queue()
        else:
            load_queue(args.load_queue)
    elif args.parallel:
        cpus = os.cpu_count()
        set_start_method('fork')  # multiprocessing logging won't work with the spawn method
        # start worker processes according to available CPU resources
        with Pool() as worker_pool:
            jobs = []
            # for detail_loc, (charge_cls, parser_cls) in parsers.items():
            while True:
                try:
                    cases = fetch_cases_from_queue()
                except NoItemsInQueue:
                    logger.info('No items found in parser queue')
                    break
                for case_number, detail_loc, receipt_handle in cases:  
                    if not detail_loc:
                        detail_loc = get_detail_loc(case_number)  
                    logger.debug(f'Dispatching {case_number} {detail_loc} to worker')
                    job = worker_pool.apply_async(check_case, (case_number, parsers[detail_loc][0], parsers[detail_loc][1], receipt_handle))
                    jobs.append((job, case_number, detail_loc))
                # Prune completed jobs from active list
                while len(jobs) > cpus:
                    for job, case_number, detail_loc in jobs:
                        try:
                            if job.ready():
                                job.get()  # To re-raise exceptions from child process
                                jobs.remove((job, case_number, detail_loc))
                                logger.debug(f'Finished checking charges for {case_number} {detail_loc}')
                        except ValueError:
                            # Job not finished, let it keep running
                            pass
            logger.info('Wait for remaining jobs to complete before exiting')
            for job,_,_ in jobs:
                job.wait(timeout=60)
    else:
        while True:
            try:
                cases = fetch_cases_from_queue()
            except NoItemsInQueue:
                logger.info('No items found in parser queue')
                break
            for case_number, detail_loc, receipt_handle in cases:
                check_case(case_number, parsers[detail_loc][0], parsers[detail_loc][1], receipt_handle)
