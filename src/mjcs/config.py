from sqlalchemy import create_engine
import os
import boto3

class Config:
    def __getattr__(self, name):
        if self.__getattribute__('initialized') == False:
            raise Exception('Tried to access configuration value before initialization')
        return self.__getattribute__(name)

    def __init__(self):
        self.initialized = False
        self.aws_profile = None
        if os.getenv('AWS_LAMBDA_FUNCTION_NAME') or os.getenv('DOCKER_TASK'):
            self.initialize_from_environment()

    # Does not need to be called by lambda functions, only CLI
    def initialize_from_environment(self, environment=None, aws_profile=None):
        if aws_profile and not self.__getattribute__('aws_profile'):
            self.aws_profile = aws_profile

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

        self.CASE_BATCH_SIZE = int(os.getenv('CASE_BATCH_SIZE',1000))

        self.QUERY_TIMEOUTS_LIMIT = int(os.getenv('QUERY_TIMEOUTS_LIMIT',5))
        self.QUERY_ERROR_LIMIT = int(os.getenv('QUERY_ERROR_LIMIT',5)) # TODO split into scraper and spider
        self.QUERY_TIMEOUT = int(os.getenv('QUERY_TIMEOUT',135)) # seconds # TODO split into scraper and spider

        self.SPIDER_DEFAULT_CONCURRENCY = int(os.getenv('SPIDER_DEFAULT_CONCURRENCY',10))
        self.SPIDER_DAYS_PER_QUERY = int(os.getenv('SPIDER_DAYS_PER_QUERY',16))

        self.SCRAPER_DEFAULT_CONCURRENCY = int(os.getenv('SCRAPER_DEFAULT_CONCURRENCY',10)) # must be multiple of 2
        self.SCRAPER_LAMBDA_EXPIRY_MIN = int(os.getenv('SCRAPER_LAMBDA_EXPIRY_MIN',5))
        self.QUEUE_WAIT = int(os.getenv('QUEUE_WAIT',5)) # seconds

        self.MJCS_DATABASE_URL = os.getenv('MJCS_DATABASE_URL')
        self.CASE_DETAILS_BUCKET = os.getenv('CASE_DETAILS_BUCKET')

        self.SPIDER_QUEUE_NAME = os.getenv('SPIDER_QUEUE_NAME')
        self.SCRAPER_QUEUE_NAME = os.getenv('SCRAPER_QUEUE_NAME')
        self.SCRAPER_FAILED_QUEUE_NAME = os.getenv('SCRAPER_FAILED_QUEUE_NAME')
        self.PARSER_FAILED_QUEUE_NAME = os.getenv('PARSER_FAILED_QUEUE_NAME')
        self.PARSER_TRIGGER_ARN = os.getenv('PARSER_TRIGGER_ARN')

        if self.__getattribute__('MJCS_DATABASE_URL'):
            self.db_engine = create_engine(self.MJCS_DATABASE_URL)

        # Create custom boto3 session to use aws_profile
        self.boto3_session = boto3.session.Session(profile_name=self.aws_profile)

        # Generic boto3 resources/clients
        self.sqs = self.boto3_session.resource('sqs')
        self.s3 = self.boto3_session.resource('s3')
        self.sns = self.boto3_session.resource('sns')
        self.lambda_ = self.boto3_session.client('lambda')

        # Specific AWS objects
        if self.__getattribute__('CASE_DETAILS_BUCKET'):
            self.case_details_bucket = self.s3.Bucket(self.CASE_DETAILS_BUCKET)
        if self.__getattribute__('SCRAPER_QUEUE_NAME'):
            self.scraper_queue = self.sqs.get_queue_by_name(QueueName=self.SCRAPER_QUEUE_NAME)
        if self.__getattribute__('SCRAPER_FAILED_QUEUE_NAME'):
            self.scraper_failed_queue = self.sqs.get_queue_by_name(QueueName=self.SCRAPER_FAILED_QUEUE_NAME)
        if self.__getattribute__('PARSER_TRIGGER_ARN'):
            self.parser_trigger = self.sns.Topic(self.PARSER_TRIGGER_ARN)
        if self.__getattribute__('PARSER_FAILED_QUEUE_NAME'):
            self.parser_failed_queue = self.sqs.get_queue_by_name(QueueName=self.PARSER_FAILED_QUEUE_NAME)
        if self.__getattribute__('SPIDER_QUEUE_NAME'):
            self.spider_queue = self.sqs.get_queue_by_name(QueueName=self.SPIDER_QUEUE_NAME)

        self.initialized = True

config = Config()
