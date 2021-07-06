from sqlalchemy import create_engine
import os
import boto3
import logging

class Config:
    def __getattr__(self, name):
        if self.__getattribute__('initialized') == False:
            raise Exception('Tried to access configuration value before initialization')
        return self.__getattribute__(name)

    def __init__(self):
        self.initialized = False
        self.aws_profile = None
        if os.getenv('AWS_LAMBDA_FUNCTION_NAME'):
            self.initialize_from_environment()

    # Does not need to be called by lambda functions, only CLI
    def initialize_from_environment(self, environment=None, aws_profile=None):
        if aws_profile and not self.__getattribute__('aws_profile'):
            self.aws_profile = aws_profile
        
        # Set up logging
        logger = logging.getLogger('mjcs')
        formatter = logging.Formatter('[%(asctime)s] %(levelname)s:%(name)s: %(message)s')
        handler = logging.StreamHandler()
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        if not logger.level:
            logger.setLevel(logging.INFO)
        if os.getenv('VERBOSE'):
            logger.setLevel(logging.DEBUG)

        if os.getenv('AWS_LAMBDA_FUNCTION_NAME'):
            logger.debug('Detected Lambda function, initializing environment.')
        elif environment:
            logger.debug(f'Initializing config from environment {environment}')
        
        if environment:
            from dotenv import load_dotenv # imported here so we don't have to package dotenv with lambda functions
            env_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'env')
            load_dotenv(dotenv_path=os.path.join(env_dir,'base.env'))
            if environment == 'dev' or environment == 'development':
                load_dotenv(dotenv_path=os.path.join(env_dir,'development.env'))
            elif environment == 'prod' or environment == 'production':
                load_dotenv(dotenv_path=os.path.join(env_dir,'production.env'))
            else:
                raise Exception('Invalid environment %s' % environment)

        # General options
        self.MJCS_BASE_URL = os.getenv('MJCS_BASE_URL', 'https://casesearch.courts.state.md.us/casesearch')
        self.CASE_BATCH_SIZE = int(os.getenv('CASE_BATCH_SIZE',1000))
        self.QUERY_TIMEOUT = int(os.getenv('QUERY_TIMEOUT',135)) # seconds
        self.QUEUE_WAIT = int(os.getenv('QUEUE_WAIT',5)) # seconds
        self.USER_AGENT = os.getenv('USER_AGENT')

        # Spider options
        self.SPIDER_DEFAULT_CONCURRENCY = int(os.getenv('SPIDER_DEFAULT_CONCURRENCY',10))
        self.SPIDER_DAYS_PER_QUERY = int(os.getenv('SPIDER_DAYS_PER_QUERY',16))
        self.SPIDER_UPDATE_FREQUENCY = int(os.getenv('SPIDER_UPDATE_FREQUENCY',900)) # seconds

        # Scraper options
        self.SCRAPER_DEFAULT_CONCURRENCY = int(os.getenv('SCRAPER_DEFAULT_CONCURRENCY',10)) # must be multiple of 2
        self.SCRAPER_WAIT_INTERVAL = int(os.getenv('SCRAPER_WAIT_INTERVAL',600)) # 10 mins
        self.MAX_SCRAPE_AGE = int(os.getenv('MAX_SCRAPE_AGE', 14)) # days
        self.MAX_SCRAPE_AGE_INACTIVE = int(os.getenv('MAX_SCRAPE_AGE_INACTIVE', 60)) # days
        self.RESCRAPE_COEFFICIENT = float(os.getenv('RESCRAPE_COEFFICIENT', self.MAX_SCRAPE_AGE / (365 * 4 + 1) ))
        self.SCRAPE_QUEUE_THRESHOLD = int(os.getenv('SCRAPE_QUEUE_THRESHOLD', 5000000))
        
        # Infrastructure identifiers
        self.MJCS_DATABASE_URL = os.getenv('MJCS_DATABASE_URL')
        self.CASE_DETAILS_BUCKET = os.getenv('CASE_DETAILS_BUCKET')
        self.SPIDER_DYNAMODB_TABLE_NAME = os.getenv('SPIDER_DYNAMODB_TABLE_NAME')
        self.SPIDER_RUNS_BUCKET_NAME = os.getenv('SPIDER_RUNS_BUCKET_NAME')
        self.SPIDER_TASK_DEFINITION_ARN = os.getenv('SPIDER_TASK_DEFINITION_ARN')
        self.SCRAPER_QUEUE_NAME = os.getenv('SCRAPER_QUEUE_NAME')
        self.PARSER_FAILED_QUEUE_NAME = os.getenv('PARSER_FAILED_QUEUE_NAME')
        self.PARSER_TRIGGER_ARN = os.getenv('PARSER_TRIGGER_ARN')
        self.VPC_SUBNET_1_ID = os.getenv('VPC_SUBNET_1_ID')
        self.VPC_SUBNET_2_ID = os.getenv('VPC_SUBNET_2_ID')
        self.ECS_CLUSTER_ARN = os.getenv('ECS_CLUSTER_ARN')

        # SQLAlchemy database engine
        if self.__getattribute__('MJCS_DATABASE_URL'):
            self.db_engine = create_engine(self.MJCS_DATABASE_URL)

        # Create custom boto3 session to use aws_profile
        self.boto3_session = boto3.session.Session(profile_name=self.aws_profile)

        # Generic boto3 resources/clients
        self.sqs = self.boto3_session.resource('sqs')
        self.dynamodb = self.boto3_session.resource('dynamodb')
        self.s3 = self.boto3_session.resource('s3')
        self.sns = self.boto3_session.resource('sns')
        self.lambda_ = self.boto3_session.client('lambda')

        # Specific AWS objects
        if self.__getattribute__('CASE_DETAILS_BUCKET'):
            self.case_details_bucket = self.s3.Bucket(self.CASE_DETAILS_BUCKET)
        if self.__getattribute__('SPIDER_DYNAMODB_TABLE_NAME'):
            self.spider_table = self.dynamodb.Table(self.SPIDER_DYNAMODB_TABLE_NAME)
        if self.__getattribute__('SPIDER_RUNS_BUCKET_NAME'):
            self.spider_runs_bucket = self.s3.Bucket(self.SPIDER_RUNS_BUCKET_NAME)
        if self.__getattribute__('SCRAPER_QUEUE_NAME'):
            self.scraper_queue = self.sqs.get_queue_by_name(QueueName=self.SCRAPER_QUEUE_NAME)
        if self.__getattribute__('PARSER_TRIGGER_ARN'):
            self.parser_trigger = self.sns.Topic(self.PARSER_TRIGGER_ARN)
        if self.__getattribute__('PARSER_FAILED_QUEUE_NAME'):
            self.parser_failed_queue = self.sqs.get_queue_by_name(QueueName=self.PARSER_FAILED_QUEUE_NAME)

        self.initialized = True

config = Config()
