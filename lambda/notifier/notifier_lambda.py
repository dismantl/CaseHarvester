import os
import requests

orch_ip_addr = os.getenv('ORCHESTRATOR_IP_ADDRESS')

def state_change_notifier(event, context):
    print(event)
    instance_id = event['detail']['instance-id']
    state = event['detail']['state']
    response = requests.get(f'http://{orch_ip_addr}/{state}/{instance_id}')

def queue_not_empty_notifier(event, context):
    print(event)
    alarm_name = event['detail']['alarmName']
    state = event['detail']['state']['value']
    if state == 'ALARM':
        if 'spider' in alarm_name:
            response = requests.get(f'http://{orch_ip_addr}/spider/available')
        elif 'scraper' in alarm_name:
            response = requests.get(f'http://{orch_ip_addr}/scraper/available')
    elif state == 'OK':
        if 'spider' in alarm_name:
            response = requests.get(f'http://{orch_ip_addr}/spider/empty')
        elif 'scraper' in alarm_name:
            response = requests.get(f'http://{orch_ip_addr}/scraper/empty')