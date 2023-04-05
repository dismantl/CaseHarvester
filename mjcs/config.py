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
        self.environment = None
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
            self.environment = environment
            logger.debug(f'Initializing config from environment {environment}')
            from dotenv import load_dotenv # imported here so we don't have to package dotenv with lambda functions
            env_dir = os.path.join(os.path.dirname(__file__), '..', 'env')
            load_dotenv(dotenv_path=os.path.join(env_dir,'base.env'))
            if environment == 'dev' or environment == 'development':
                load_dotenv(dotenv_path=os.path.join(env_dir,'development.env'))
            elif environment == 'prod' or environment == 'production':
                load_dotenv(dotenv_path=os.path.join(env_dir,'production.env'))
            else:
                raise Exception('Invalid environment %s' % environment)

        # General options
        self.MJCS_DOMAIN = os.getenv('MJCS_DOMAIN', 'casesearch.courts.state.md.us')
        self.MJCS_SITE = os.getenv('MJCS_SITE', f'https://{self.MJCS_DOMAIN}')
        self.MJCS_BASE_URL = os.getenv('MJCS_BASE_URL', f'{self.MJCS_SITE}/casesearch')
        self.CASE_BATCH_SIZE = int(os.getenv('CASE_BATCH_SIZE',1000))
        self.QUERY_TIMEOUT = int(os.getenv('QUERY_TIMEOUT',135)) # seconds
        self.QUEUE_WAIT = int(os.getenv('QUEUE_WAIT',5)) # seconds
        self.AWS_DEFAULT_REGION = os.getenv('AWS_DEFAULT_REGION', 'us-east-1')
        self.CLOUDWATCH_RETENTION_DAYS = os.getenv('CLOUDWATCH_RETENTION_DAYS', 30)

        # Spider options
        self.SPIDER_DAYS_PER_QUERY = int(os.getenv('SPIDER_DAYS_PER_QUERY',16))

        # Scraper options
        self.MAX_SCRAPE_AGE = int(os.getenv('MAX_SCRAPE_AGE', 14)) # days
        self.MAX_SCRAPE_AGE_INACTIVE = int(os.getenv('MAX_SCRAPE_AGE_INACTIVE', 90)) # days
        self.RESCRAPE_COEFFICIENT = float(os.getenv('RESCRAPE_COEFFICIENT', self.MAX_SCRAPE_AGE / (365 * 4 + 1) ))
        self.SCRAPE_QUEUE_THRESHOLD = int(os.getenv('SCRAPE_QUEUE_THRESHOLD', 5000000))
        
        # Infrastructure identifiers
        self.MJCS_DATABASE_URL = os.getenv('MJCS_DATABASE_URL')
        self.CASE_DETAILS_BUCKET = os.getenv('CASE_DETAILS_BUCKET')
        self.SPIDER_QUEUE_NAME = os.getenv('SPIDER_QUEUE_NAME')
        self.SCRAPER_QUEUE_NAME = os.getenv('SCRAPER_QUEUE_NAME')
        self.PARSER_FAILED_QUEUE_NAME = os.getenv('PARSER_FAILED_QUEUE_NAME')
        self.PARSER_QUEUE_NAME = os.getenv('PARSER_QUEUE_NAME')
        self.PARSER_TRIGGER_ARN = os.getenv('PARSER_TRIGGER_ARN')
        self.VPC_SUBNET_1_ID = os.getenv('VPC_SUBNET_1_ID')
        self.VPC_SUBNET_2_ID = os.getenv('VPC_SUBNET_2_ID')
        self.ECS_CLUSTER_ARN = os.getenv('ECS_CLUSTER_ARN')

        # SQLAlchemy database engine
        if self.__getattribute__('MJCS_DATABASE_URL'):
            self.db_engine = create_engine(self.MJCS_DATABASE_URL, future=True)

        # Create custom boto3 session to use aws_profile
        self.boto3_session = boto3.session.Session(profile_name=self.aws_profile, region_name=self.AWS_DEFAULT_REGION)

        # Generic boto3 resources/clients
        self.sqs = self.boto3_session.resource('sqs')
        self.dynamodb = self.boto3_session.resource('dynamodb')
        self.s3 = self.boto3_session.resource('s3')
        self.sns = self.boto3_session.resource('sns')
        self.lambda_ = self.boto3_session.client('lambda')

        self.initialized = True

    @property
    def case_details_bucket(self):
        return self.s3.Bucket(self.CASE_DETAILS_BUCKET)
    
    @property
    def spider_queue(self):
        return self.sqs.get_queue_by_name(QueueName=self.SPIDER_QUEUE_NAME)

    @property
    def scraper_queue(self):
        return self.sqs.get_queue_by_name(QueueName=self.SCRAPER_QUEUE_NAME)
        
    @property
    def parser_trigger(self):
        return self.sns.Topic(self.PARSER_TRIGGER_ARN)
    
    @property
    def parser_failed_queue(self):
        return self.sqs.get_queue_by_name(QueueName=self.PARSER_FAILED_QUEUE_NAME)
    
    @property
    def parser_queue(self):
        return self.sqs.get_queue_by_name(QueueName=self.PARSER_QUEUE_NAME)


config = Config()
