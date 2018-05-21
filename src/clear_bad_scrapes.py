#!/usr/bin/env python3

from mjcs.config import config
from mjcs.db import db_session
from mjcs.case import Case, cases_batch_filter
from mjcs.scraper import delete_scrape, check_scrape_sanity, FailedScrape, ExpiredSession
from sqlalchemy import and_
import boto3

s3 = boto3.client('s3')

deleted = 0
with db_session() as db:
    for detail_loc in ['CC']:
        filter = and_(Case.last_parse == None, Case.last_scrape != None, Case.detail_loc == detail_loc)
        num_cases = db.query(Case.case_number).filter(filter).count()
        i = 1
        for batch_filter in cases_batch_filter(db, filter):
            for case in db.query(Case).filter(batch_filter):
                print('Checking case %s (%s of %s)' % (case.case_number,i,num_cases))
                i += 1
                try:
                    o = s3.get_object(
                        Bucket = config.CASE_DETAILS_BUCKET,
                        Key = case.case_number
                    )
                except s3.exceptions.NoSuchKey:
                    case.last_scrape = None
                    db.commit()
                else:
                    html = o['Body'].read().decode('utf-8')
                    try:
                        check_scrape_sanity(case.case_number, html)
                    except (FailedScrape, ExpiredSession):
                        deleted += 1
                        print('Deleting',case.case_number)
                        delete_scrape(db, case.case_number)
                        case.last_parse = None
                        db.commit()
print('Deleted %s items' % deleted)
