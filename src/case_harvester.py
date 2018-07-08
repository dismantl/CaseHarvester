#!/usr/bin/env python3
from mjcs.config import config
from mjcs.db import TableBase, db_session
from mjcs.spider import Spider
from mjcs.case import Case
from mjcs.scraper import Scraper, delete_latest_scrape
from mjcs.parser import Parser, invoke_parser_lambda
import mjcs.models
import boto3
from datetime import *
import sys
import os
import json
import argparse
from sqlalchemy import create_engine
from sqlalchemy.sql import text

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
    engine_ = create_engine('postgresql://%s:%s@%s/postgres' % \
        (master_username, master_password, db_hostname))
    conn = engine_.connect()
    conn.execute("commit")
    print("Creating database",db_name)
    conn.execute("create database " + db_name)
    print("Creating user",username)
    conn.execute(text("create user %s with password :pw" % username), pw=password)
    conn.execute("grant all privileges on database %s to %s" % (db_name,username))
    conn.execute(text("create user %s with password :pw" % ro_username), pw=ro_password)
    conn.execute("alter default privileges in schema public grant select on tables to %s" % ro_username)
    conn.close()

def write_env_file(env_long, env_short, exports, db_name, username, password):
    env_dir = os.path.join(os.path.dirname(__file__), '..', 'env')
    env_file_path = os.path.join(env_dir, env_long + '.env')
    db_hostname = get_export_val(exports, env_short, 'DatabaseHostname')
    db_url = 'postgresql://%s:%s@%s/%s' % (username,password,db_hostname,db_name)
    print("Writing env file",env_file_path)
    with open(env_file_path, 'w') as f:
        f.write('%s=%s\n' % ('MJCS_DATABASE_URL',db_url))
        f.write('%s=%s\n' % ('CASE_DETAILS_BUCKET',
            get_export_val(exports,env_short,'CaseDetailsBucketName')))
        f.write('%s=%s\n' % ('SCRAPER_QUEUE_NAME',
            get_export_val(exports,env_short,'ScraperQueueName')))
        f.write('%s=%s\n' % ('SCRAPER_FAILED_QUEUE_NAME',
            get_export_val(exports,env_short,'ScraperFailedQueueName')))
        f.write('%s=%s\n' % ('SCRAPER_DYNAMODB_TABLE_NAME',
            get_export_val(exports,env_short,'ScraperDynamoDBTableName')))
        f.write('%s=%s\n' % ('SCRAPER_QUEUE_ALARM_NAME',
            get_export_val(exports,env_short,'ScraperQueueAlarmName')))
        f.write('%s=%s\n' % ('PARSER_FAILED_QUEUE_NAME',
            get_export_val(exports,env_short,'ParserFailedQueueName')))
        f.write('%s=%s\n' % ('PARSER_TRIGGER_ARN',
            get_export_val(exports,env_short,'ParserTriggerArn')))

def create_tables():
    print("Creating all tables")
    TableBase.metadata.create_all(config.db_engine)

def valid_date(s):
    try:
        return datetime.strptime(s, "%m/%d/%Y")
    except ValueError:
        raise argparse.ArgumentTypeError("Not a valid date: %s" % s)

def run_spider(args):
    spider = Spider(args.connections)

    if args.test:
        spider.test(args.overwrite, args.force_scrape)
    elif args.resume:
        spider.resume(args.overwrite, args.force_scrape)
    elif args.start_date:
        spider.search(args.start_date, args.end_date, args.court,
            args.overwrite, args.force_scrape)
    else:
        raise Exception("Must specify --resume, --test, or search criteria")

def scraper_prompt(exception, case_number):
    print(exception)
    while True:
        print('Continue scraping?')
        print('\t\t(y)es    - ignore error and continue scraping (default)')
        print('\t\t(n)o     - stop scraping and raise exception')
        print('\t\t(d)elete - ignore error and delete item from queue')
        print('\t\t(m)ark   - mark case as unscrapable and continue')
        print('\t\t(e)xempt - save scrape but exempt from parsing')
        print('\t\t(s)ave   - save scrape and continue')
        answer = input('Answer: (Y/n/d/m/e/s) ')
        if answer == 'y' or answer == 'Y' or not answer:
            return 'continue'
        elif answer == 'n':
            raise exception
        elif answer == 'd':
            return 'delete'
        elif answer == 'm':
            with db_session() as db:
                db.execute(
                    Case.__table__.update()\
                        .where(Case.case_number == case_number)\
                        .values(scrape_exempt = True)
                )
            return 'delete'
        elif answer == 'e':
            with db_session() as db:
                db.execute(
                    Case.__table__.update()\
                        .where(Case.case_number == case_number)\
                        .values(parse_exempt = True)
                )
            return 'store'
        elif answer == 's':
            return 'store'
        else:
            print('Invalid answer')

def run_scraper(args):
    on_error = None
    if args.ignore_errors:
        on_error = lambda e,c: 'delete' # delete because failed scrapes will be (re-)added to failed queue
    elif args.prompt_on_error:
        on_error = scraper_prompt

    scraper = Scraper(on_error, args.threads)

    if args.invoke_lambda:
        exports = get_stack_exports()
        lambda_arn = get_export_val(exports, args.environment_short, 'ScraperArn')
        boto3.client('lambda').invoke(
            FunctionName = lambda_arn,
            InvocationType = 'Event',
            Payload = '{"manual":true}'
        )
    elif args.missing:
        scraper.scrape_missing_cases()
    elif args.queue:
        scraper.scrape_from_scraper_queue()
    elif args.failed_queue:
        scraper.scrape_from_failed_queue()
    else:
        raise Exception("Must specify --invoke-lambda, --missing, --queue, or --failed-queue.")

def parser_prompt(exception, case_number):
    if type(exception) == NotImplementedError:
        return 'continue'
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
        on_error = lambda e,c: 'continue'
    elif args.prompt_on_error:
        on_error = parser_prompt

    parser = Parser(on_error, args.threads)

    if args.failed_queue:
        parser.parse_failed_queue(args.type)
    elif args.invoke_lambda:
        invoke_parser_lambda(args.type)
    else:
        parser.parse_unparsed_cases(args.type)

if __name__ == '__main__':
    if len(sys.argv) == 2 and sys.argv[1] == 'db_init':
        db_init()
        sys.exit(0)

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
        choices=['production','development'],
        help="Environment to run the case harvester in (e.g. production, development)")
    parser.add_argument('--profile', '-p', default='default',
        help="AWS named profile to use for credentials (see \
        https://docs.aws.amazon.com/cli/latest/userguide/cli-multiple-profiles.html)")
    subparsers = parser.add_subparsers(title='Commands')

    parser_spider = subparsers.add_parser('spider',
        help='Spider the Maryland Judiciary Case Search database for case numbers')
    parser_spider.add_argument('--connections', '-c', type=int, default=10)
    parser_spider.add_argument('--test','-t',action='store_true',
        help="Seed queue with test items")
    parser_spider.add_argument('--start-date','-s', type=valid_date,
        help="Start date for search range. If --end-date is not specified, "
        "search for cases on this exact date")
    parser_spider.add_argument('--end-date','-e', type=valid_date,
        help="Optional. End date for search range")
    parser_spider.add_argument('--resume','-r', action='store_true',
        help="Use existing queue items in database")
    parser_spider.add_argument('--court', #choices=['BALTIMORE CITY'],
        help="What court to search, e.g. BALTIMORE CITY")
    parser_spider.add_argument('--overwrite','-o', action='store_true',
        help="Overwrite existing cases in database")
    parser_spider.add_argument('--force-scrape','-f', action='store_true',
        help="Force scraping of case details for all found cases")
    parser_spider.set_defaults(func=run_spider)

    parser_scraper = subparsers.add_parser('scraper',
        help="Scrape case details from the Maryland Judiciary Case Search database")
    parser_scraper.add_argument('--ignore-errors', action='store_true',
        help="Ignore scraping errors")
    parser_scraper.add_argument('--prompt-on-error', action='store_true',
        help="Prompt for actions when an error occurs")
    parser_scraper.add_argument('--missing', action='store_true', help=\
        "Scrape any cases that are in the database but don't have any case details in S3")
    parser_scraper.add_argument('--queue', action='store_true', help=\
        "Scrape cases in the scraper queue")
    parser_scraper.add_argument('--failed-queue', action='store_true', help=\
        "Scrape cases in the queue of failed cases")
    parser_scraper.add_argument('--invoke-lambda', action='store_true',
        help="Invoke scraper lambda function")
    parser_scraper.add_argument('--threads', type=int, default=1,
        help="Number of threads (default: 1)")
    parser_scraper.set_defaults(func=run_scraper)

    parser_parser = subparsers.add_parser('parser', help=\
        "Parse unparsed details from cases downloaded from the Maryland Judiciary Case Search")
    parser_parser.add_argument('--type', '-t', choices=['DSCR','DSK8','DSCIVIL','CC'],
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

    config.initialize_from_environment(args.environment, args.profile)
    if args.environment == 'development':
        args.environment_short = 'dev'
    elif args.environment == 'production':
        args.environment_short = 'prod'

    args.func(args)
    print("Goodbye!")
