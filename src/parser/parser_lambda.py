from mjcs.parser import parse_case
import json

def lambda_handler(event, context):
    for record in event['Records']:
        if 's3' in record:
            case_number = record['s3']['object']['key']
            try:
                parse_case(case_number)
                print(f'Successfully parsed {case_number}')
            except NotImplementedError:
                pass
        elif 'Sns' in record:
            msg = json.loads(record['Sns']['Message'])
            case_number = msg['case_number']
            detail_loc = msg['detail_loc']
            try:
                parse_case(case_number, detail_loc)
                print(f'Successfully parsed {detail_loc} {case_number}')
            except NotImplementedError:
                pass
