import os

if not os.getenv('AWS_LAMBDA_FUNCTION_NAME'):
    from dotenv import load_dotenv
    env_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'env')
    load_dotenv(dotenv_path=os.path.join(env_dir,'base.env'))
    if os.getenv('MJCS_DEVELOPMENT_ENV'):
        load_dotenv(dotenv_path=os.path.join(env_dir,'development.env'))
    elif os.getenv('MJCS_PRODUCTION_ENV'):
        load_dotenv(dotenv_path=os.path.join(env_dir,'production.env'))
    else:
        load_dotenv(dotenv_path=os.path.join(env_dir,'development.env'))

class Config:
    DB_BATCH_SIZE = int(os.getenv('DB_BATCH_SIZE',1000))

    QUERY_TIMEOUTS_LIMIT = int(os.getenv('QUERY_TIMEOUTS_LIMIT',5))
    QUERY_500_LIMIT = int(os.getenv('QUERY_500_LIMIT',5))
    QUERY_TIMEOUT = int(os.getenv('QUERY_TIMEOUT',135)) # seconds

    SPIDER_DEFAULT_CONCURRENCY = int(os.getenv('SPIDER_DEFAULT_CONCURRENCY',10))
    SPIDER_DAYS_PER_QUERY = int(os.getenv('SPIDER_DAYS_PER_QUERY',16))

    SCRAPER_DEFAULT_CONCURRENCY = int(os.getenv('SCRAPER_DEFAULT_CONCURRENCY',10)) # must be multiple of 2
    SCRAPER_LAMBDA_EXPIRY_MIN = int(os.getenv('SCRAPER_LAMBDA_EXPIRY_MIN',5))
    QUEUE_WAIT = int(os.getenv('QUEUE_WAIT',5)) # seconds

    MJCS_DATABASE_URL = os.getenv('MJCS_DATABASE_URL')
    SCRAPER_QUEUE_NAME = os.getenv('SCRAPER_QUEUE_NAME')
    SCRAPER_FAILED_QUEUE_NAME = os.getenv('SCRAPER_FAILED_QUEUE_NAME')
    SCRAPER_DYNAMODB_TABLE_NAME = os.getenv('SCRAPER_DYNAMODB_TABLE_NAME')
    SCRAPER_QUEUE_ALARM_NAME = os.getenv('SCRAPER_QUEUE_ALARM_NAME')
    CASE_DETAILS_BUCKET = os.getenv('CASE_DETAILS_BUCKET')
    PARSER_FAILED_QUEUE_NAME = os.getenv('PARSER_FAILED_QUEUE_NAME')
    PARSER_TRIGGER_ARN = os.getenv('PARSER_TRIGGER_ARN')

config = Config()
