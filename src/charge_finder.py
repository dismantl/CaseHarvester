#!/usr/bin/env python3
from mjcs.models.ODYCRIM import ODYCRIM
from mjcs.parser.ODYCRIM import ODYCRIMParser
from mjcs.parser.ODYCVCIT import ODYCVCITParser
from mjcs.parser.ODYTRAF import ODYTRAFParser
from mjcs.util import db_session, get_detail_loc
from mjcs.models import ODYCRIMCharge, ODYTRAFCharge, ODYCVCITCharge, Scrape
from mjcs.config import config
from sqlalchemy.sql import text
from sqlalchemy.exc import MultipleResultsFound
from bs4 import BeautifulSoup, SoupStrainer
import re
import logging
import argparse
import os

logger = logging.getLogger('mjcs')
parsers = {
    'ODYCRIM': (ODYCRIMCharge, ODYCRIMParser),
    'ODYTRAF': (ODYTRAFCharge, ODYTRAFParser),
    'ODYCVCIT': (ODYCVCITCharge, ODYCVCITParser)
}

def check_case(case_number, charge_cls, parser_cls):
    logger.debug(f'Processing {case_number}')
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
            logger.info(f'Found charge numbers: {", ".join([str(_) for _ in charge_numbers])}')
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
        db.execute(text(f"UPDATE cases SET checked_expunged_charges = TRUE WHERE case_number = '{case_number}'"))

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="Check ODYCRIM, ODYTRAF, and ODYCVCIT cases for expunged charges",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument('--environment', '--env', default='development',
        choices=['production','prod','development','dev'],
        help="Environment to run in (e.g. production, development)")
    parser.add_argument('--case', '-c', help="Check specific case number")
    parser.add_argument('--verbose', '-v', action='store_true',
        help="Print debug information")
    args = parser.parse_args()
    if (hasattr(args, 'verbose') and args.verbose) or os.getenv('VERBOSE'):
        logger.setLevel(logging.DEBUG)
    config.initialize_from_environment(args.environment)

    if args.case:
        detail_loc = get_detail_loc(args.case)
        check_case(args.case, parsers[detail_loc][0], parsers[detail_loc][1])
    else:
        for detail_loc, (charge_cls, parser_cls) in parsers.items():
            while True:
                with db_session() as db:
                    logger.info(f'Querying for {detail_loc}')
                    query = db.execute(text(f"""
                        SELECT
                            case_number 
                        FROM
                            scrape_versions 
                            JOIN
                                cases USING (case_number) 
                        WHERE
                            detail_loc = '{detail_loc}'
                            AND checked_expunged_charges = FALSE
                        GROUP BY
                            case_number 
                        HAVING
                            COUNT(*) >= 2
                        LIMIT
                            {config.CASE_BATCH_SIZE}
                    """))
                logger.info('Query complete')
                if query.rowcount == 0:
                    logger.info(f'Finished {detail_loc}')
                    break
                for case_number, in query:
                    check_case(case_number, charge_cls, parser_cls)
                    