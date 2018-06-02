from mjcs.parser import parse_case
import json

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
