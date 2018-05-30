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
            try:
                parse_case(case_number)
                print('Successfully parsed',case_number)
            except NotImplementedError:
                pass
        elif 'Sns' in record:
            msg = json.loads(record['Sns']['Message'])
            case_number = msg['case_number']
            try:
                parse_case(case_number)
                print('Successfully parsed',case_number)
            except NotImplementedError:
                pass
