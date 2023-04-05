from mjcs.parser import parse_case
import json

def lambda_handler(event, context):
    for record in event['Records']:
        if 's3' in record:
            case_number = record['s3']['object']['key']
            try:
                parse_case(case_number)
            except NotImplementedError:
                pass
            except Exception:
                print(f'Error parsing case {case_number} (https://mdcaseexplorer.com/case/{case_number})')
                raise
        elif 'Sns' in record:
            msg = json.loads(record['Sns']['Message'])
            case_number = msg['case_number']
            detail_loc = msg['detail_loc']
            try:
                parse_case(case_number, detail_loc)
            except NotImplementedError:
                pass
            except Exception:
                print(f'Error parsing case {case_number} (https://mdcaseexplorer.com/case/{case_number})')
                raise
        elif record.get('eventSource') == 'aws:sqs':
            subrecords = json.loads(record['body'])['Records']
            for subrecord in subrecords:
                case_number = subrecord['manual']['case_number']
                detail_loc = subrecord['manual']['detail_loc']
                try:
                    parse_case(case_number, detail_loc)
                except:  # Ignore all parsing errors so entire batch doesn't fail
                    pass
