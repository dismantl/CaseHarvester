#!/usr/bin/env python3
from mjcs.parser.ODYCRIM import ODYCRIMParser
from mjcs.parser.ODYCVCIT import ODYCVCITParser
from mjcs.parser.ODYTRAF import ODYTRAFParser
from mjcs.util import db_session, get_detail_loc, send_to_queue, NoItemsInQueue
from mjcs.models import ODYCRIMCharge, ODYTRAFCharge, ODYCVCITCharge, Scrape, Case
from mjcs.config import config
from sqlalchemy.sql import text
from bs4 import BeautifulSoup, SoupStrainer
import re
import logging
import argparse
import os
from multiprocessing import Pool, set_start_method
import json

logger = logging.getLogger('mjcs')
parsers = {
    'ODYCRIM': (ODYCRIMCharge, ODYCRIMParser),
    'ODYTRAF': (ODYTRAFCharge, ODYTRAFParser),
    'ODYCVCIT': (ODYCVCITCharge, ODYCVCITParser)
}

def check_case(case_number, charge_cls, parser_cls):
    logger.info(f'Processing {case_number}')
    with db_session() as db:
        versions = db.query(Scrape).filter_by(case_number=case_number).filter(Scrape.s3_version_id != None).order_by(Scrape.timestamp.desc()).offset(1)
        for version in versions:
            logger.debug(f'Fetching version {version.s3_version_id}')
            html = config.s3.ObjectVersion(
                config.CASE_DETAILS_BUCKET,
                case_number,
                version.s3_version_id
            ).get()['Body'].read()
            strainer = SoupStrainer('div',class_='BodyWindow')
            soup = BeautifulSoup(html,'html.parser',parse_only=strainer)
            
            charge_numbers = []
            charge_spans = soup.find_all('span',class_='Prompt',string='Charge No:')
            for span in charge_spans:
                charge_number = span.find_parent('td').find_next_sibling('td').find('span',class_='Value').string
                charge_numbers.append(
                    int(re.sub('[ \t]+','',charge_number))
                )
            logger.debug(f'Found charge numbers: {", ".join([str(_) for _ in charge_numbers])}')
            existing_charge_numbers = [_ for _, in db.query(charge_cls.charge_number).filter_by(case_number=case_number).all()]
            missing_charge_numbers = list(set(charge_numbers) - set(existing_charge_numbers))
            if missing_charge_numbers:
                logger.info(f'!!! Found expunged charge number(s) {", ".join([str(_) for _ in missing_charge_numbers])} for case {case_number} !!!')
                parser = parser_cls(case_number, html)
                found = 0
                for span in charge_spans:
                    charge_number = span.find_parent('td').find_next_sibling('td').find('span',class_='Value').string
                    if int(re.sub('[ \t]+','',charge_number)) in missing_charge_numbers:
                        found += 1
                        new_charge = parser.parse_charge(span.find_parent('div',class_='AltBodyWindow1'))
                        new_charge.possibly_expunged = True
                        db.add(new_charge)
                if found != len(missing_charge_numbers):
                    raise Exception(f'Failed to find missing charge numbers for case {case_number}')

def get_cases(detail_loc=None, limit=None):
    if detail_loc:
        query_text = f"""
            SELECT
                case_number,
                detail_loc
            FROM
                scrape_versions 
                JOIN
                    cases USING (case_number) 
            WHERE
                detail_loc = '{detail_loc}'
                AND checked_expunged_charges = FALSE
                AND parse_exempt = FALSE
                AND last_parse IS NOT NULL
            GROUP BY
                case_number,
                detail_loc
            HAVING
                COUNT(*) >= 2
        """
    else:
        locs = "', '".join([k for k,v in parsers.items()])
        query_text = f"""
            SELECT
                case_number,
                detail_loc
            FROM
                scrape_versions 
                JOIN
                    cases USING (case_number) 
            WHERE
                detail_loc IN ('{locs}')
                AND checked_expunged_charges = FALSE
                AND parse_exempt = FALSE
                AND last_parse IS NOT NULL
            GROUP BY
                case_number,
                detail_loc
            HAVING
                COUNT(*) >= 2
        """
    if limit:
        query_text += f' LIMIT {limit}'
    logger.debug(f'Querying for cases')
    with db_session() as db:
        query = db.execute(text(query_text))
    logger.debug('Query complete')
    return query

def load_queue(ncases, detail_loc=None):
    logger.debug('Loading cases into parser queue')
    if ncases == 'all':
        while True:
            logger.debug('Fetching batch of cases')
            query = get_cases(detail_loc, config.CASE_BATCH_SIZE)
            if query.rowcount == 0:
                logger.debug('Finished loading cases into parser queue')
                return
            messages = []
            case_list = []
            for case_number, loc in query:
                messages.append(
                    json.dumps({
                        'Records': [
                            {
                                'manual': {
                                    'case_number': case_number,
                                    'detail_loc': loc
                                }
                            }
                        ]
                    })
                )
                case_list.append(case_number)
            send_to_queue(config.parser_queue, messages)
            logger.info(f'Submitted {query.rowcount} to parser queue')
            case_list = "', '".join(case_list)
            with db_session() as db:
                db.execute(text(f"""
                    UPDATE cases SET checked_expunged_charges = TRUE WHERE case_number in ('{case_list}')
                """))
            logger.debug(f'Updated checked_expunged_charges for {query.rowcount} cases')
    else:
        query = get_cases(detail_loc, ncases)
        if query.rowcount == 0:
            logger.debug('Finished loading cases into parser queue')
            return
        messages = []
        case_list = []
        for case_number, loc in query:
            messages.append(
                json.dumps({
                    'Records': [
                        {
                            'manual': {
                                'case_number': case_number,
                                'detail_loc': loc
                            }
                        }
                    ]
                })
            )
            case_list.append(case_number)
        send_to_queue(config.parser_queue, messages)
        case_list = "', '".join(case_list)
        with db_session() as db:
            db.execute(text(f"""
                UPDATE cases SET checked_expunged_charges = TRUE WHERE case_number in ('{case_list}')
            """))

def parser_queue_validator(string):
    try:
        if string == 'all':
            return string
        elif int(string) > 0:
            return int(string)
    except ValueError:
        raise argparse.ArgumentTypeError('Value must be a positive integer')

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

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="Check ODYCRIM, ODYTRAF, and ODYCVCIT cases for expunged charges",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument('--environment', '--env', default='development',
        choices=['production','prod','development','dev'],
        help="Environment to run in (e.g. production, development)")
    parser.add_argument('--load-queue', nargs='?', const='all', type=parser_queue_validator, metavar='NCASES',
        help="Load cases to check into the parser queue for later processing. \
            Optional argument limits the number of cases sent to the queue.")
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
                    def callback_wrapper(case_number, receipt_handle):
                        def callback(unused):
                            logger.debug(f'Deleting {case_number} from parser queue')
                            config.parser_queue.delete_messages(Entries=[{'Id': 'unused', 'ReceiptHandle': receipt_handle}])
                        return callback
                    callback = callback_wrapper(case_number, receipt_handle)
                    job = worker_pool.apply_async(check_case, (case_number, parsers[detail_loc][0], parsers[detail_loc][1]), callback=callback, error_callback=callback)
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
                check_case(case_number, parsers[detail_loc][0], parsers[detail_loc][1])
                config.parser_queue.delete_messages(Entries=[{'Id': 'unused', 'ReceiptHandle': receipt_handle}])
