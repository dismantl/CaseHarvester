#!/usr/bin/env python3

from mjcs.config import config
from mjcs.db import db_session
from mjcs.case import Case, cases_batch_filter
from sqlalchemy import and_
import boto3
from botocore.exceptions import ClientError

s3 = boto3.client('s3')

deleted = 0
with db_session() as db:
    for detail_loc in ['DSCR','DSK8','DSCIVIL']:
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
                except ClientError as ex:
                    if ex.response['Error']['Code'] == 'NoSuchKey':
                        case.last_scrape = None
                    else:
                        raise ex
                else:
                    html = o['Body'].read().decode('utf-8')
                    if o['ContentLength'] < 1000 or 'An unexpected error occurred' in html or "Note: Initial Sort is by Last Name." in html:
                        deleted += 1
                        print('Deleting',case.case_number)
                        s3.delete_object(
                            Bucket = config.CASE_DETAILS_BUCKET,
                            Key = case.case_number
                        )
                        case.last_scrape = None
                        case.last_parse = None
print('Deleted %s items' % deleted)
