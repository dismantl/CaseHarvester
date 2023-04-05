#!/usr/bin/env python3
from mjcs import models
from mjcs.config import config
from mjcs.models.common import TableBase
from mjcs.spider import generate_spider_slices, Spider
from mjcs.scraper import Scraper, RequestTimeout, Forbidden
from mjcs.parser import Parser
from mjcs.util import db_session, get_case_model_list
from mjcs.collector import MDECCollector, BaltCityCollector
import boto3
from datetime import datetime, timedelta
import os
import json
import argparse
import logging
import subprocess
import socket
import watchtower
from ec2_metadata import ec2_metadata
from sqlalchemy import create_engine
from sqlalchemy.sql import text
from multiprocessing import set_start_method

logger = logging.getLogger('mjcs')

def get_export_val(exports, env_short, export_name):
    for export in exports:
        if f'{env_short}-{export_name}' in export['Name']:
            return export['Value']
    raise Exception(f'Unable to find {export_name} in AWS Cloudformation exports')

def run_db_init(args):
    exports = boto3.client('cloudformation').list_exports()['Exports']
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
    scripts_path = os.path.join(os.path.dirname(__file__), '..', 'db', 'sql')
    with create_engine(db_url, future=True).begin() as conn:
        for file in os.listdir(scripts_path):
            if file.endswith('.sql'):
                print(f'Running SQL initialization script {file}')
                with open(os.path.join(scripts_path, file), 'r') as script:
                    commands = script.read()
                conn.execute(text(commands))

def create_database_and_users(db_hostname, db_name, secrets, environment):
    master_username = secrets[environment]['DatabaseMasterUsername']
    master_password = secrets[environment]['DatabaseMasterPassword']
    username = secrets[environment]['DatabaseUsername']
    password = secrets[environment]['DatabasePassword']
    ro_username = secrets[environment]['DatabaseReadOnlyUsername']
    ro_password = secrets[environment]['DatabaseReadOnlyPassword']

    print("Creating database, roles, and users")
    postgres_url = f'postgresql://{master_username}:{master_password}@{db_hostname}/postgres'
    with create_engine(postgres_url, future=True).begin() as conn:
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
        """), pw=password, ro_pw=ro_password)
        
    print('Setting basic permissions')
    db_url = f'postgresql://{username}:{password}@{db_hostname}/{db_name}'
    with create_engine(db_url, future=True).begin() as conn:
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
        """))

def write_env_file(env_long, env_short, exports, db_name, username, password):
    env_dir = os.path.join(os.path.dirname(__file__), 'env')
    env_file_path = os.path.join(env_dir, env_long + '.env')
    db_hostname = get_export_val(exports, env_short, 'DatabaseHostname')
    db_url = f'postgresql://{username}:{password}@{db_hostname}/{db_name}'
    print("Writing env file", env_file_path)
    with open(env_file_path, 'w') as f:
        f.write(f'MJCS_DATABASE_URL={db_url}\n')
        f.write(f"CASE_DETAILS_BUCKET={get_export_val(exports,env_short,'CaseDetailsBucketName')}\n")
        f.write(f"SPIDER_QUEUE_NAME={get_export_val(exports,env_short,'SpiderQueueName')}\n")
        f.write(f"SPIDER_LAUNCH_TEMPLATE_ID={get_export_val(exports,env_short,'SpiderLaunchTemplateId')}\n")
        f.write(f"SCRAPER_QUEUE_NAME={get_export_val(exports,env_short,'ScraperQueueName')}\n")
        f.write(f"SCRAPER_LAUNCH_TEMPLATE_ID={get_export_val(exports,env_short,'ScraperLaunchTemplateId')}\n")
        f.write(f"PARSER_FAILED_QUEUE_NAME={get_export_val(exports,env_short,'ParserFailedQueueName')}\n")
        f.write(f"PARSER_QUEUE_NAME={get_export_val(exports,env_short,'ParserQueueName')}\n")
        f.write(f"PARSER_TRIGGER_ARN={get_export_val(exports,env_short,'ParserTriggerArn')}\n")
        f.write(f"VPC_SUBNET_1_ID={get_export_val(exports,env_short,'VPCPublicSubnet1Id')}\n")
        f.write(f"VPC_SUBNET_2_ID={get_export_val(exports,env_short,'VPCPublicSubnet2Id')}\n")
        f.write(f"ECS_CLUSTER_ARN={get_export_val(exports,env_short,'ECSClusterArn')}\n")
        f.write(f"NOTIFIER_RULE_NAME={get_export_val(exports,env_short,'NotifierRuleName')}\n")
        f.write(f"SPIDER_COUNT_PARAMETER_NAME={get_export_val(exports,env_short,'SpiderCountParameterName')}\n")
        f.write(f"SCRAPER_COUNT_PARAMETER_NAME={get_export_val(exports,env_short,'ScraperCountParameterName')}\n")
        f.write(f"SPIDER_QUEUE_NOT_EMPTY_ALARM_NAME={get_export_val(exports,env_short,'SpiderQueueNotEmptyAlarmName')}\n")
        f.write(f"SCRAPER_QUEUE_NOT_EMPTY_ALARM_NAME={get_export_val(exports,env_short,'ScraperQueueNotEmptyAlarmName')}\n")
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

def run_spider(args):
    if args.from_queue:
        logger.info(f'{socket.gethostname()} spidering from queue')
        spider = Spider()
        try:
            spider.spider_from_queue(record_metrics=args.record_metrics)
        except (RequestTimeout, Forbidden) as e:
            logger.warning(f'Caught {type(e).__name__} error: {e}')
        finally:
            if args.shutdown:
                logger.info('Shutting down the system.')
                if hasattr(args, 'log') and args.log:
                    os.remove(args.log)
                subprocess.run(["shutdown", "now"])
    elif args.start_date:    
        generate_spider_slices(args.start_date, args.end_date or datetime.now(), args.court, args.site)
    else:
        raise Exception("Must specify search criteria, --launch-instances, --terminate-instances, or --from-queue")

def run_collector(args):
    if args.list == 'MDEC':
        collector = MDECCollector()
    elif args.list == 'BaltimoreCity':
        collector = BaltCityCollector()
    collector.collect_case_numbers(args.date)

def run_scraper(args):
    scraper = Scraper()
    if args.case:
        scraper.scrape_case(args.case)
    elif args.stale:
        scraper.rescrape_stale(args.start_date, args.end_date, args.include_unscraped, args.include_inactive)
    elif args.stale_count:
        count = scraper.count_stale(args.start_date, args.end_date, args.include_unscraped, args.include_inactive)
        logger.info(f'Counted {count} cases.')
    elif args.from_queue:
        logger.info(f'{socket.gethostname()} scraping from queue')
        try:
            scraper.scrape_from_queue(record_metrics=args.record_metrics)
        except (RequestTimeout, Forbidden) as e:
            logger.warning(f'Caught {type(e).__name__} error: {e}')
        finally:
            if args.shutdown:
                logger.info('Shutting down the system.')
                if hasattr(args, 'log') and args.log:
                    os.remove(args.log)
                subprocess.run(["shutdown", "now"])
    else:
        raise Exception("Must specify --case, --from-queue, --stale, or --stale-count.")

def run_parser(args):
    parser = Parser(args.ignore_errors, args.parallel)

    if args.failed_queue:
        parser.parse_from_queue(config.parser_failed_queue)
    elif args.queue:
        parser.parse_from_queue(config.parser_queue, parse_as=args.type)
    elif args.case:
        parser.parse_case(args.case, parse_as=args.type)
    elif args.unparsed:
        parser.parse_unparsed(args.type)
    elif args.stale:
        parser.parse_stale(args.type)
    elif args.reparse:
        parser.reparse(args.type)

def export_tables(args):
    case_models = get_case_model_list(models)
    with db_session() as db:
        for model in case_models:
            redacted = False
            for col in model.__table__.columns:
                if col.redacted == True:
                    redacted = True
            if redacted:
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
    set_start_method('fork')

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
        choices=['production','development', 'prod', 'dev'],
        help="Environment to run the case harvester in (e.g. production, development)")
    parser.add_argument('--profile', '-p',
        help="AWS named profile to use for credentials (see \
        https://docs.aws.amazon.com/cli/latest/userguide/cli-multiple-profiles.html)")
    parser.add_argument('--log-file', help="Log to file")
    parser.add_argument('--cloudwatch', help="Log to the given AWS CloudWatch log group")
    subparsers = parser.add_subparsers(title='Commands')

    parser_spider = subparsers.add_parser('spider',
        help='Spider the Maryland Judiciary Case Search database for case numbers')
    parser_spider.add_argument('--start-date','-s', type=valid_date,
        help="Start date for search range. --end-date defaults to today if not specified")
    parser_spider.add_argument('--end-date','-e', type=valid_date,
        help="End date for search range (optional)")
    parser_spider.add_argument('--court', #choices=['BALTIMORE CITY'],
        help="What court to search, e.g. BALTIMORE CITY")
    parser_spider.add_argument('--site', choices=['CRIMINAL', 'CIVIL', 'TRAFFIC', 'CP'],
        help="What venues to search, criminal/civil/traffic/civil citation")
    parser_spider.add_argument('--verbose', '-v', action='store_true',
        help="Print debug information")
    parser_spider.add_argument('--from-queue', action='store_true',
        help="Spider MJCS with queries from the spider queue")
    parser_spider.add_argument('--shutdown', action='store_true',
        help="Shutdown machine after rate limit (must be run as root)")
    parser_spider.add_argument('--record-metrics', action='store_true',
        help="Send metrics to Cloudwatch every minute")
    parser_spider.set_defaults(func=run_spider)

    parser_collector = subparsers.add_parser('collector',
        help="Collect case numbers from PDFs posted daily by the Judiciary")
    parser_collector.add_argument('--list', '-l', required=True, choices=['MDEC', 'BaltimoreCity'],
        help="Which PDF list to parse")
    parser_collector.add_argument('--date', '-d', type=valid_date,
        help="Collect case numbers from this date (defaults to today)")
    parser_collector.set_defaults(func=run_collector)

    parser_scraper = subparsers.add_parser('scraper',
        help="Scrape case details from the Maryland Judiciary Case Search database")
    parser_scraper.add_argument('--case', '-c', help="Scrape specific case number")
    parser_scraper.add_argument('--verbose', '-v', action='store_true',
        help="Print debug information")
    parser_scraper.add_argument('--stale', action='store_true',
        help='Send stale cases to scraper queue based on scrape age')
    parser_scraper.add_argument('--stale-count', action='store_true',
        help='Count number of stale cases based on scrape age')
    parser_scraper.add_argument('--start-date','-s', type=valid_date,
        help="Start date for filing date range. --end-date defaults to today if not specified")
    parser_scraper.add_argument('--end-date','-e', type=valid_date,
        help="End date for filing date (optional)")
    parser_scraper.add_argument('--include-unscraped', action='store_true',
        help="Include unscraped case numbers when rescraping")
    parser_scraper.add_argument('--include-inactive', action='store_true',
        help="Include inactive cases when rescraping")
    parser_scraper.add_argument('--from-queue', action='store_true',
        help="Scrape cases from the scraper queue")
    parser_scraper.add_argument('--shutdown', action='store_true',
        help="Shutdown machine after rate limit (must be run as root)")
    parser_scraper.add_argument('--record-metrics', action='store_true',
        help="Send metrics to Cloudwatch every minute")
    parser_scraper.set_defaults(func=run_scraper)

    parser_parser = subparsers.add_parser('parser',
        help="Parse unparsed details from cases downloaded from the Maryland Judiciary Case Search")
    parser_parser.add_argument('--type', '-t', choices=['ODYTRAF','ODYCRIM','ODYCIVIL','ODYCVCIT','DSCR','DSK8','DSCIVIL','CC','DSTRAF','DSCP','K','PG','DV','MCCI','PGV','MCCR','ODYCOSA','ODYCOA'],
        help="Force parsing as this case type")
    parser_parser.add_argument('--ignore-errors', action='store_true', default=False,
        help="Ignore parsing errors")
    parser_parser.add_argument('--queue', action='store_true',
        help="Parse cases in the general parser queue (optionally \
            specifying --type)")
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
    parser_parser.add_argument('--stale', action='store_true',
        help="Parse cases from the database that have last_parse < last_scrape (optionally \
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
    if args.log_file:
        logger.addHandler(logging.FileHandler(filename=args.log_file, encoding='utf-8'))

    if args.environment[:3] == 'dev':
        args.environment = 'development'
        args.environment_short = 'dev'
    elif args.environment[:4] == 'prod':
        args.environment = 'production'
        args.environment_short = 'prod'
    config.initialize_from_environment(args.environment, args.profile)

    if args.cloudwatch:
        logger.addHandler(watchtower.CloudWatchLogHandler(
            log_group_name=args.cloudwatch,
            log_stream_name=ec2_metadata.instance_id,
            log_group_retention_days=config.CLOUDWATCH_RETENTION_DAYS,
            boto3_client=config.boto3_session.client('logs')
        ))

    if hasattr(args, 'func'):
        args.func(args)
    
    logging.shutdown()
    print("Goodbye!")
