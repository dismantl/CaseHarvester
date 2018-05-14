from mjcs.config import config
from mjcs.parser import parse_case_from_html, parse_case
import boto3
import json

s3 = boto3.client('s3')
bucket = config.CASE_DETAILS_BUCKET

def lambda_handler(event, context):
    for record in event['Records']:
        if 's3' in record:
            case_number = record['s3']['object']['key']
            case_details = s3.get_object(
                Bucket = bucket,
                Key = case_number
            )
            case_html = case_details['Body'].read().decode('utf-8')
            detail_loc = case_details['Metadata']['detail_loc']
            try:
                parse_case_from_html(case_number, detail_loc, case_html)
                print('Successfully parsed',case_number)
            except NotImplementedError:
                pass
        elif 'Sns' in record:
            msg = json.loads(record['Sns']['Message'])
            case_number = msg['case_number']
            detail_loc = msg['detail_loc']
            try:
                parse_case(case_number, detail_loc)
                print('Successfully parsed',case_number)
            except NotImplementedError:
                pass
