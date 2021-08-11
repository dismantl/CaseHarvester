from mjcs.parser import parse_case, Parser
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
            except Exception as e:
                from mjcs.util import get_detail_loc
                detail_loc = get_detail_loc(case_number)
                print(f'Error parsing case {case_number} (https://casesearch.courts.state.md.us/casesearch/inquiryDetail.jis?caseId={case_number}&detailLoc={detail_loc})')
                raise e
        elif 'Sns' in record:
            msg = json.loads(record['Sns']['Message'])
            case_number = msg['case_number']
            detail_loc = msg['detail_loc']
            try:
                parse_case(case_number, detail_loc)
                print(f'Successfully parsed {detail_loc} {case_number}')
            except NotImplementedError:
                pass
        elif record.get('eventSource') == 'aws:sqs':
            subrecords = json.loads(record['body'])['Records']
            for subrecord in subrecords:
                case_number = subrecord['manual']['case_number']
                detail_loc = subrecord['manual']['detail_loc']
                try:
                    parse_case(case_number, detail_loc)
                    print(f'Successfully parsed {detail_loc} {case_number}')
                except:  # Ignore all parsing errors so entire batch doesn't fail
                    pass
