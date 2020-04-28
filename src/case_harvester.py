#!/usr/bin/env python3
from mjcs.config import config
from mjcs.models import Case
from mjcs.models.common import TableBase
from mjcs.util import db_session, delete_latest_scrape
from mjcs.spider import Spider
from mjcs.scraper import Scraper
from mjcs.parser import Parser, invoke_parser_lambda
import boto3
from datetime import datetime, timedelta
import sys
import os
import json
import argparse
import logging
from sqlalchemy import create_engine
from sqlalchemy.sql import text

logger = logging.getLogger('mjcs')

def get_stack_exports():
    return boto3.client('cloudformation').list_exports()['Exports']

def get_export_val(exports, env_short, export_name):
    for export in exports:
        if '%s-%s' % (env_short,export_name) in export['Name']:
            return export['Value']
    raise Exception('Unable to find %s in AWS Cloudformation exports' % export_name)

def run_db_init(args):
    exports = get_stack_exports()
    db_hostname = get_export_val(exports, args.environment_short, 'DatabaseHostname')
    if not db_hostname:
        raise Exception('Unable to find database hostname in AWS cloudformation exports')
    secrets = json.loads(args.secrets_file.read())
    db_username = secrets[args.environment]['DatabaseUsername']
    db_password = secrets[args.environment]['DatabasePassword']
    db_master_username = secrets[args.environment]['DatabaseMasterUsername']
    db_master_password = secrets[args.environment]['DatabaseMasterPassword']
    db_ro_username = secrets[args.environment]['DatabaseReadOnlyUsername']
    db_ro_password = secrets[args.environment]['DatabaseReadOnlyPassword']

    if args.create_tables_only:
        create_tables()
    elif args.write_env_only:
        write_env_file(args.environment, args.environment_short, exports, args.db_name, db_username, db_password)
    else:
        create_database_and_user(db_hostname, args.db_name,
            db_master_username, db_master_password, db_username, db_password,
            db_ro_username, db_ro_password)
        write_env_file(args.environment, args.environment_short, exports, args.db_name, db_username, db_password)
        create_tables()

def create_database_and_user(db_hostname, db_name, master_username,
        master_password, username, password, ro_username, ro_password):
    postgres_url = 'postgresql://%s:%s@%s/postgres' % \
        (master_username, master_password, db_hostname)
    db_url = 'postgresql://%s:%s@%s/%s' % \
        (username, password, db_hostname, db_name)

    conn = create_engine(postgres_url).connect()
    conn.execute("commit")
    print("Creating database",db_name)
    conn.execute("create database " + db_name)
    print("Creating user",username)
    conn.execute(text("create user %s with password :pw" % username), pw=password)
    conn.execute("grant all privileges on database %s to %s" % (db_name,username))
    conn.execute("grant rds_superuser to %s" % (username))
    conn.execute(text("create user %s with password :pw" % ro_username), pw=ro_password)
    conn.close()

    conn = create_engine(db_url).connect()
    conn.execute("alter default privileges in schema public grant select on tables to %s"
        % ro_username)
    conn.close()

def write_env_file(env_long, env_short, exports, db_name, username, password):
    env_dir = os.path.join(os.path.dirname(__file__), '..', 'env')
    env_file_path = os.path.join(env_dir, env_long + '.env')
    db_hostname = get_export_val(exports, env_short, 'DatabaseHostname')
    db_url = f'postgresql://{username}:{password}@{db_hostname}/{db_name}'
    print("Writing env file", env_file_path)
    with open(env_file_path, 'w') as f:
        f.write('%s=%s\n' % ('MJCS_DATABASE_URL',db_url))
        f.write('%s=%s\n' % ('CASE_DETAILS_BUCKET',
            get_export_val(exports,env_short,'CaseDetailsBucketName')))
        f.write('%s=%s\n' % ('SPIDER_DYNAMODB_TABLE_NAME',
            get_export_val(exports,env_short,'SpiderDynamoDBTableName')))
        f.write('%s=%s\n' % ('SPIDER_RUNS_BUCKET_NAME',
            get_export_val(exports,env_short,'SpiderRunsBucketName')))
        f.write('%s=%s\n' % ('SPIDER_TASK_DEFINITION_ARN',
            get_export_val(exports,env_short,'SpiderTaskDefinitionArn')))
        f.write('%s=%s\n' % ('SCRAPER_QUEUE_NAME',
            get_export_val(exports,env_short,'ScraperQueueName')))
        f.write('%s=%s\n' % ('SCRAPER_FAILED_QUEUE_NAME',
            get_export_val(exports,env_short,'ScraperFailedQueueName')))
        f.write('%s=%s\n' % ('PARSER_FAILED_QUEUE_NAME',
            get_export_val(exports,env_short,'ParserFailedQueueName')))
        f.write('%s=%s\n' % ('PARSER_TRIGGER_ARN',
            get_export_val(exports,env_short,'ParserTriggerArn')))
        f.write('%s=%s\n' % ('VPC_SUBNET_1_ID',
            get_export_val(exports,env_short,'VPCPublicSubnet1Id')))
        f.write('%s=%s\n' % ('VPC_SUBNET_2_ID',
            get_export_val(exports,env_short,'VPCPublicSubnet2Id')))
        f.write('%s=%s\n' % ('ECS_CLUSTER_ARN',
            get_export_val(exports,env_short,'ECSClusterArn')))
    # re-load config
    config.initialize_from_environment(env_long)

def create_tables():
    print("Creating all tables")
    TableBase.metadata.create_all(config.db_engine)

def valid_date(s):
    try:
        return datetime.strptime(s, "%m/%d/%Y")
    except ValueError:
        raise argparse.ArgumentTypeError("Not a valid date: %s" % s)

def valid_datetime(s):
    try:
        return datetime.fromisoformat(s)
    except ValueError:
        raise argparse.ArgumentTypeError(f"Not a valid ISO-formatted timestamp: {s}")

def launch_fargate(args, start_date, end_date):
    command = [
        'python',
        '-u',
        'case_harvester.py',
        '--environment',
        args.environment,
        'spider',
        '--start-date',
        start_date.strftime('%m/%d/%Y'),
        '--end-date',
        end_date.strftime('%m/%d/%Y'),
    ]
    if args.court:
        command += ['--court', args.court]
    if args.site:
        command += ['--site', args.site]
    if args.verbose:
        command.append('-v')
    if args.timestamp:
        command += ['--timestamp', args.timestamp.isoformat()]
    elif args.resume:
        command.append('-r')
    
    client = boto3.client('ecs')
    response = client.run_task(
        cluster=config.ECS_CLUSTER_ARN,
        taskDefinition=config.SPIDER_TASK_DEFINITION_ARN,
        count=1,
        launchType='FARGATE',
        networkConfiguration={
            'awsvpcConfiguration': {
                'subnets': [ config.VPC_SUBNET_1_ID, config.VPC_SUBNET_2_ID ],
                'assignPublicIp': 'ENABLED'
            }
        },
        overrides={
            'containerOverrides': [
                {
                    'name': 'spider',
                    'command': command
                }
            ]
        }
    )
    print(f"Fargate task launched, returned status: {response['tasks'][0]['lastStatus']}")

def run_spider(args):
    if args.start_date:
        start_date = args.start_date
        end_date = args.end_date
    elif args.end_days_ago:
        today = datetime.now().date()
        end_date = datetime.combine(today - timedelta(days=args.start_days_ago), datetime.min.time())
        start_date = datetime.combine(today - timedelta(days=args.end_days_ago), datetime.min.time())
    else:
        raise Exception("Must specify search criteria")
    
    if args.fargate:
        return launch_fargate(args, start_date, end_date)

    spider = Spider(
            concurrency = args.concurrency,
            query_start_date=start_date,
            query_end_date=end_date,
            court=args.court,
            site=args.site
        )
    if args.timestamp:
        spider.resume(args.timestamp)
    elif args.resume:
        spider.resume()
    else:
        spider.start()

def run_scraper(args):
    scraper = Scraper(args.concurrency)
    if args.case:
        scraper.scrape_specific_case(args.case)
    elif args.rescrape_end:
        scraper.rescrape(days_ago_start=args.rescrape_start, days_ago_end=args.rescrape_end)
    elif args.service:
        scraper.start_service()
    else:
        raise Exception("Must specify --service or --rescrape-start/--rescrape-end.")

def parser_prompt(exception, case_number):
    if type(exception) == NotImplementedError:
        return 'delete'
    print(exception)
    while True:
        print('Continue parsing?')
        print('\t\t(y)es    - ignore error and continue parsing (default)')
        print('\t\t(n)o     - stop parsing and raise exception')
        print('\t\t(d)elete - delete scrape and remove from queue')
        answer = input('Answer: (Y/n/d) ')
        if answer == 'y' or answer == 'Y' or not answer:
            return 'continue'
        elif answer == 'n':
            raise exception
        elif answer == 'd':
            with db_session() as db:
                delete_latest_scrape(db, case_number)
            return 'delete'
        else:
            print('Invalid answer')

def run_parser(args):
    on_error = None
    if args.ignore_errors:
        on_error = lambda e,c: 'delete'
    elif args.prompt_on_error:
        on_error = parser_prompt

    parser = Parser(on_error, args.threads)

    if args.failed_queue:
        parser.parse_failed_queue(args.type)
    elif args.invoke_lambda:
        invoke_parser_lambda(args.type)
    elif args.case:
        parser.parse_case(args.case)
    else:
        parser.parse_unparsed_cases(args.type)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="Run Case Harvester to spider, scrape, or parse cases from "
            "the Maryland Judiciary Case Search",
        epilog="To see help text for a command, you can run:\n"
                '  %(prog)s spider --help\n'
                '  %(prog)s scraper --help\n'
                '  %(prog)s parser --help',
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument('--environment', '--env', default='development',
        choices=['production','prod','development','dev'],
        help="Environment to run the case harvester in (e.g. production, development)")
    parser.add_argument('--profile', '-p', default='default',
        help="AWS named profile to use for credentials (see \
        https://docs.aws.amazon.com/cli/latest/userguide/cli-multiple-profiles.html)")
    subparsers = parser.add_subparsers(title='Commands')

    parser_spider = subparsers.add_parser('spider',
        help='Spider the Maryland Judiciary Case Search database for case numbers')
    parser_spider.add_argument('--concurrency', '-c', type=int, default=10)
    parser_spider.add_argument('--start-date','-s', type=valid_date,
        help="Start date for search range. If --end-date is not specified, "
        "search for cases on this exact date")
    parser_spider.add_argument('--end-date','-e', type=valid_date,
        help="End date for search range (optional)")
    parser_spider.add_argument('--start-days-ago', type=int, default=0,
        help="Spider for cases starting this many days ago (default 0)")
    parser_spider.add_argument('--end-days-ago', type=int,
        help="Spider for cases ending this many days ago")
    parser_spider.add_argument('--resume','-r', action='store_true',
        help="Resume most recent spider run with the search conditions provided on the command line")
    parser_spider.add_argument('--timestamp', '-t', type=valid_datetime,
        help="Resume spider run at the given timestamp with the search conditions provided on the command line")
    parser_spider.add_argument('--court', #choices=['BALTIMORE CITY'],
        help="What court to search, e.g. BALTIMORE CITY")
    parser_spider.add_argument('--site', choices=['CRIMINAL', 'CIVIL', 'TRAFFIC', 'CP'],
        help="What venues to search, criminal/civil/traffic/civil citation")
    parser_spider.add_argument('--verbose', '-v', action='store_true',
        help="Print debug information")
    parser_spider.add_argument('--fargate', '-f', action='store_true',
        help="Launch spider as ECS Fargate task using provided command line arguments")
    parser_spider.set_defaults(func=run_spider)

    parser_scraper = subparsers.add_parser('scraper',
        help="Scrape case details from the Maryland Judiciary Case Search database")
    parser_scraper.add_argument('--concurrency', type=int, default=10)
    parser_scraper.add_argument('--case', '-c', help="Scrape specific case number")
    parser_scraper.add_argument('--verbose', '-v', action='store_true',
        help="Print debug information")
    parser_scraper.add_argument('--rescrape-start', type=int, default=0,
        help="Send existing cases to scraper queue for rescraping, starting this many days ago (default 0)")
    parser_scraper.add_argument('--rescrape-end', type=int,
        help="Send existing cases to scraper queue for rescraping, ending this many days ago")
    parser_scraper.add_argument('--service', action='store_true',
        help="Run the scraper as a service, scraping cases whenever there are messages in the scraper queue")
    parser_scraper.set_defaults(func=run_scraper)

    parser_parser = subparsers.add_parser('parser', help=\
        "Parse unparsed details from cases downloaded from the Maryland Judiciary Case Search")
    parser_parser.add_argument('--type', '-t', choices=['DSCR','DSK8','DSCIVIL','CC','ODYTRAF','ODYCRIM'],
        help="Only parse cases of this type (detail_loc)")
    parser_parser.add_argument('--ignore-errors', action='store_true',
        help="Ignore parsing errors")
    parser_parser.add_argument('--prompt-on-error', action='store_true',
        help="Prompt for actions when an error occurs")
    parser_parser.add_argument('--failed-queue', action='store_true',
        help="Parse cases in the parser failed queue")
    parser_parser.add_argument('--invoke-lambda', action='store_true',
        help="Use Lambda function to parse all unparsed cases")
    parser_parser.add_argument('--threads', type=int, default=1,
        help="Number of threads for parsing unparsed cases (default: 1)")
    parser_parser.add_argument('--case', '-c', help="Parse a specific case number")
    parser_parser.add_argument('--verbose', '-v', action='store_true',
        help="Print debug information")
    parser_parser.set_defaults(func=run_parser)

    if os.getenv('DEV_MODE'):
        parser_db = subparsers.add_parser('db_init', help="Database initialization")
        parser_db.add_argument('--db-name', required=True, help="Database name")
        parser_db.add_argument('--secrets-file', required=True,
            type=argparse.FileType('r'), help="Secrets file (in JSON format)")
        parser_db.add_argument('--create-tables-only', action='store_true',
            help="Only create tables in the database")
        parser_db.add_argument('--write-env-only', action='store_true',
            help="Only write environment files from cloudformation stack exports")
        parser_db.set_defaults(func=run_db_init)

    args = parser.parse_args()

    if (hasattr(args, 'verbose') and args.verbose) or os.getenv('VERBOSE'):
        logger.setLevel(logging.DEBUG)

    config.initialize_from_environment(args.environment, args.profile)
    if args.environment[:3] == 'dev':
        args.environment = 'development'
        args.environment_short = 'dev'
    elif args.environment[:4] == 'prod':
        args.environment = 'production'
        args.environment_short = 'prod'

    if hasattr(args, 'func'):
        args.func(args)
    print("Goodbye!")
