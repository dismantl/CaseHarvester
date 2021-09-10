#!/usr/bin/env python3
from sqlalchemy.sql.expression import table
from mjcs import models
from mjcs.config import config
from mjcs.models.common import TableBase
from mjcs.spider import Spider
from mjcs.scraper import Scraper
from mjcs.parser import Parser
from mjcs.util import db_session, get_case_model_list
import boto3
from datetime import datetime, timedelta
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
        if f'{env_short}-{export_name}' in export['Name']:
            return export['Value']
    raise Exception(f'Unable to find {export_name} in AWS Cloudformation exports')

def run_db_init(args):
    exports = get_stack_exports()
    db_hostname = get_export_val(exports, args.environment_short, 'DatabaseHostname')
    if not db_hostname:
        raise Exception('Unable to find database hostname in AWS cloudformation exports')
    secrets = json.loads(args.secrets_file.read())
    db_username = secrets[args.environment]['DatabaseUsername']
    db_password = secrets[args.environment]['DatabasePassword']
    db_url = f'postgresql://{db_username}:{db_password}@{db_hostname}/{args.db_name}'

    if args.create_tables_only:
        create_tables()
        run_db_init_scripts(db_url)
    elif args.write_env_only:
        write_env_file(args.environment, args.environment_short, exports, args.db_name, db_username, db_password)
    else:
        create_database_and_users(db_hostname, args.db_name, secrets, args.environment)
        write_env_file(args.environment, args.environment_short, exports, args.db_name, db_username, db_password)
        create_tables()
        run_db_init_scripts(db_url)

def run_db_init_scripts(db_url):
    conn = create_engine(db_url).connect()
    scripts_path = os.path.join(os.path.dirname(__file__), '..', 'db', 'sql')
    for file in os.listdir(scripts_path):
        if file.endswith('.sql'):
            print(f'Running SQL initialization script {file}')
            with open(os.path.join(scripts_path, file), 'r') as script:
                commands = script.read()
            conn.execute(text(commands))
    conn.close()

def create_database_and_users(db_hostname, db_name, secrets, environment):
    master_username = secrets[environment]['DatabaseMasterUsername']
    master_password = secrets[environment]['DatabaseMasterPassword']
    username = secrets[environment]['DatabaseUsername']
    password = secrets[environment]['DatabasePassword']
    ro_username = secrets[environment]['DatabaseReadOnlyUsername']
    ro_password = secrets[environment]['DatabaseReadOnlyPassword']

    print("Creating database, roles, and users")
    postgres_url = f'postgresql://{master_username}:{master_password}@{db_hostname}/postgres'
    conn = create_engine(postgres_url).connect()
    conn.execute(text("COMMIT"))
    conn.execute(text(f"CREATE DATABASE {db_name}"))
    conn.execute(text(f"""
        -- Create roles
        CREATE ROLE mjcs_admin NOLOGIN CREATEROLE;
        GRANT ALL PRIVILEGES ON DATABASE {db_name} TO mjcs_admin;
        GRANT rds_superuser TO mjcs_admin;
        CREATE ROLE mjcs_ro NOLOGIN;
        CREATE ROLE mjcs_ro_redacted NOLOGIN;

        -- Create users
        CREATE USER {username} LOGIN PASSWORD :pw;
        GRANT mjcs_admin TO {username};
        CREATE USER {ro_username} LOGIN PASSWORD :ro_pw;
        GRANT mjcs_ro_redacted TO {ro_username};
        COMMIT;
    """), pw=password, ro_pw=ro_password)
    conn.close()
        
    print('Setting basic permissions')
    db_url = f'postgresql://{username}:{password}@{db_hostname}/{db_name}'
    conn = create_engine(db_url).connect()
    conn.execute(text(f"""
        -- Database level permissions
        REVOKE ALL ON DATABASE mjcs FROM mjcs_ro, mjcs_ro_redacted;
        GRANT TEMPORARY, CONNECT ON DATABASE mjcs TO PUBLIC;

        -- Schema level permissions
        CREATE SCHEMA redacted AUTHORIZATION mjcs_admin;
        REVOKE ALL ON SCHEMA public, redacted FROM mjcs_ro, mjcs_ro_redacted;
        GRANT USAGE ON SCHEMA public, redacted TO PUBLIC;

        -- Table level permissions
        GRANT SELECT ON ALL TABLES IN SCHEMA public, redacted TO mjcs_admin, mjcs_ro;
        ALTER DEFAULT PRIVILEGES IN SCHEMA public
            GRANT SELECT ON TABLES TO mjcs_admin, mjcs_ro;
        ALTER DEFAULT PRIVILEGES IN SCHEMA redacted
            GRANT SELECT ON TABLES TO PUBLIC;
        COMMIT;
    """))
    conn.close()

def write_env_file(env_long, env_short, exports, db_name, username, password):
    env_dir = os.path.join(os.path.dirname(__file__), '..', 'env')
    env_file_path = os.path.join(env_dir, env_long + '.env')
    db_hostname = get_export_val(exports, env_short, 'DatabaseHostname')
    db_url = f'postgresql://{username}:{password}@{db_hostname}/{db_name}'
    print("Writing env file", env_file_path)
    with open(env_file_path, 'w') as f:
        f.write(f'MJCS_DATABASE_URL={db_url}\n')
        f.write(f"CASE_DETAILS_BUCKET={get_export_val(exports,env_short,'CaseDetailsBucketName')}\n")
        f.write(f"SPIDER_DYNAMODB_TABLE_NAME={get_export_val(exports,env_short,'SpiderDynamoDBTableName')}\n")
        f.write(f"SPIDER_RUNS_BUCKET_NAME={get_export_val(exports,env_short,'SpiderRunsBucketName')}\n")
        f.write(f"SPIDER_TASK_DEFINITION_ARN={get_export_val(exports,env_short,'SpiderTaskDefinitionArn')}\n")
        f.write(f"SCRAPER_QUEUE_NAME={get_export_val(exports,env_short,'ScraperQueueName')}\n")
        f.write(f"PARSER_FAILED_QUEUE_NAME={get_export_val(exports,env_short,'ParserFailedQueueName')}\n")
        f.write(f"PARSER_QUEUE_NAME={get_export_val(exports,env_short,'ParserQueueName')}\n")
        f.write(f"PARSER_TRIGGER_ARN={get_export_val(exports,env_short,'ParserTriggerArn')}\n")
        f.write(f"VPC_SUBNET_1_ID={get_export_val(exports,env_short,'VPCPublicSubnet1Id')}\n")
        f.write(f"VPC_SUBNET_2_ID={get_export_val(exports,env_short,'VPCPublicSubnet2Id')}\n")
        f.write(f"ECS_CLUSTER_ARN={get_export_val(exports,env_short,'ECSClusterArn')}\n")
    # re-load config
    config.initialize_from_environment(env_long)

def create_tables():
    print("Creating all tables")
    TableBase.metadata.create_all(config.db_engine)

def valid_date(s):
    try:
        return datetime.strptime(s, "%m/%d/%Y")
    except ValueError:
        raise argparse.ArgumentTypeError(f"Not a valid date: {s}")

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
    elif args.stale:
        scraper.rescrape_stale()
    elif args.rescrape_end:
        scraper.rescrape(days_ago_start=args.rescrape_start, days_ago_end=args.rescrape_end)
    elif args.service:
        scraper.start_service()
    else:
        raise Exception("Must specify --service, --stale, or --rescrape-start/--rescrape-end.")

def run_parser(args):
    parser = Parser(args.ignore_errors, args.parallel)

    if args.failed_queue:
        parser.parse_from_queue(config.parser_failed_queue)
    elif args.queue:
        parser.parse_from_queue(config.parser_queue)
    elif args.case:
        parser.parse_case(args.case)
    elif args.unparsed:
        parser.parse_unparsed(args.type)
    elif args.reparse:
        parser.reparse(args.type)

def export_tables(args):
    case_models = get_case_model_list(models)
    with db_session() as db:
        for model in case_models:
            if args.redacted and 'defendants' in model.__tablename__:
                table_name = f'redacted.{model.__tablename__}'
                export_name = f'{model.__tablename__}_redacted.csv'
            else:
                table_name = model.__tablename__
                export_name = f'{model.__tablename__}.csv'
            logger.info(f'Exporting {table_name} to S3')
            db.execute(f"""
                SELECT
                    *
                FROM
                    aws_s3.query_export_to_s3('
                        SELECT
                            *
                        FROM
                            {table_name}',
                        aws_commons.create_s3_uri(
                            'caseharvester-exports',
                            '{export_name}',
                            'us-east-1'
                        ),
                        OPTIONS :='FORMAT CSV, HEADER'
                    )
            """)

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
    parser_scraper.add_argument('--stale', action='store_true',
        help='Send stale cases to scraper queue based on scrape age')
    parser_scraper.add_argument('--rescrape-start', type=int, default=0,
        help="Send existing cases to scraper queue for rescraping, starting this many days ago (default 0)")
    parser_scraper.add_argument('--rescrape-end', type=int,
        help="Send existing cases to scraper queue for rescraping, ending this many days ago")
    parser_scraper.add_argument('--service', action='store_true',
        help="Run the scraper as a service, scraping cases whenever there are messages in the scraper queue")
    parser_scraper.set_defaults(func=run_scraper)

    parser_parser = subparsers.add_parser('parser', help=\
        "Parse unparsed details from cases downloaded from the Maryland Judiciary Case Search")
    parser_parser.add_argument('--type', '-t', choices=['ODYTRAF','ODYCRIM','ODYCIVIL','ODYCVCIT','DSCR','DSK8','DSCIVIL','CC','DSTRAF','DSCP','K','PG','DV','MCCR'],
        help="Only parse cases of this type (requires --load-failed-queue or --unparsed)")
    parser_parser.add_argument('--ignore-errors', action='store_true', default=False,
        help="Ignore parsing errors")
    parser_parser.add_argument('--queue', action='store_true',
        help="Parse cases in the general parser queue")
    parser_parser.add_argument('--failed-queue', action='store_true',
        help="Parse cases in the parser failed queue")
    parser_parser.add_argument('--parallel', '-p', action='store_true', default=False,
        help=f"Parse cases in parallel with {os.cpu_count()} worker processes")
    parser_parser.add_argument('--case', '-c', help="Parse a specific case number")
    parser_parser.add_argument('--verbose', '-v', action='store_true',
        help="Print debug information")
    parser_parser.add_argument('--unparsed', '-u', action='store_true',
        help="Parse cases from the database that have not been successfully parsed (optionally \
            specifying --type), loading them into the parser queue")
    parser_parser.add_argument('--reparse', '-r', action='store_true',
        help="Reparse all or a specific type (using --type) of case, loading them into the parser queue")
    parser_parser.set_defaults(func=run_parser)

    parser_export_tables = subparsers.add_parser('export-tables',
        help='Export all case-related tables to S3')
    parser_export_tables.add_argument('--redacted', '-r', action='store_true',
        help="Export only non-redacted columns and tables")
    parser_export_tables.set_defaults(func=export_tables)

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
