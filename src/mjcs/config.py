from sqlalchemy import create_engine
import os
import boto3

sqs = boto3.resource('sqs')
dynamodb = boto3.resource('dynamodb')
s3 = boto3.resource('s3')
sns = boto3.resource('sns')

class Config:
    def __getattr__(self, name):
        if self.__getattribute__('initialized') == False:
            raise Exception('Tried to access configuration value before initialization')
        return self.__getattribute__(name)

    def __init__(self):
        if os.getenv('AWS_LAMBDA_FUNCTION_NAME'):
            self.set_values()
            self.initialized = True
        else:
            self.initialized = False

    # Does not need to be called by lambda functions, only CLI
    def initialize_from_environment(self, environment):
        if self.initialized == True:
            return
        from dotenv import load_dotenv # imported here so we don't have to package dotenv with lambda functions
        env_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'env')
        load_dotenv(dotenv_path=os.path.join(env_dir,'base.env'))
        if environment == 'dev' or environment == 'development':
            load_dotenv(dotenv_path=os.path.join(env_dir,'development.env'))
        elif environment == 'prod' or environment == 'production':
            load_dotenv(dotenv_path=os.path.join(env_dir,'production.env'))
        else:
            raise Exception('Invalid environment %s' % environment)
        self.set_values()
        self.initialized = True

    def set_values(self):
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
        self.SCRAPER_QUEUE_NAME = os.getenv('SCRAPER_QUEUE_NAME')
        self.SCRAPER_FAILED_QUEUE_NAME = os.getenv('SCRAPER_FAILED_QUEUE_NAME')
        self.SCRAPER_DYNAMODB_TABLE_NAME = os.getenv('SCRAPER_DYNAMODB_TABLE_NAME')
        self.SCRAPER_QUEUE_ALARM_NAME = os.getenv('SCRAPER_QUEUE_ALARM_NAME')
        self.CASE_DETAILS_BUCKET = os.getenv('CASE_DETAILS_BUCKET')
        self.PARSER_FAILED_QUEUE_NAME = os.getenv('PARSER_FAILED_QUEUE_NAME')
        self.PARSER_TRIGGER_ARN = os.getenv('PARSER_TRIGGER_ARN')

        self.db_engine = create_engine(self.MJCS_DATABASE_URL)
        self.case_details_bucket = s3.Bucket(self.CASE_DETAILS_BUCKET)
        if self.SCRAPER_QUEUE_NAME:
            self.scraper_queue = sqs.get_queue_by_name(QueueName=self.SCRAPER_QUEUE_NAME)
            self.scraper_table = dynamodb.Table(self.SCRAPER_DYNAMODB_TABLE_NAME)
            self.scraper_failed_queue = sqs.get_queue_by_name(QueueName=self.SCRAPER_FAILED_QUEUE_NAME)
        if self.PARSER_TRIGGER_ARN:
            self.parser_trigger = sns.Topic(self.PARSER_TRIGGER_ARN)
            self.parser_failed_queue = sqs.get_queue_by_name(QueueName=self.PARSER_FAILED_QUEUE_NAME)


config = Config()
