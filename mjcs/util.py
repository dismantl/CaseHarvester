import concurrent.futures
import logging
import math
import json
import threading 
import time
from decimal import Decimal
from datetime import timedelta, datetime
from sqlalchemy import and_, func, select
from sqlalchemy.orm import sessionmaker
from contextlib import contextmanager
from .config import config
from .models import Case, ScrapeVersion, Scrape

logger = logging.getLogger('mjcs')

class RepeatedTimer:
  def __init__(self, interval, function, *args, **kwargs):
    self._timer = None
    self.interval = interval
    self.function = function
    self.args = args
    self.kwargs = kwargs
    self.is_running = False
    self.next_call = time.time()

  def _run(self):
    self.is_running = False
    self.start()
    self.function(*self.args, **self.kwargs)

  def start(self):
    if not self.is_running:
      self.next_call += self.interval
      self._timer = threading.Timer(self.next_call - time.time(), self._run)
      self._timer.start()
      self.is_running = True

  def stop(self):
    self._timer.cancel()
    self.is_running = False

class NoItemsInQueue(Exception):
    pass

class TableNotFound(Exception):
    pass

class JSONDatetimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()

# Concurrently fetch up to nitems (or 100) messages from queue, 10 per thread
def fetch_from_queue(queue, nitems=100):
    if not nitems:
        nitems = 100
    def queue_receive(n):
        return queue.receive_messages(
            WaitTimeSeconds = config.QUEUE_WAIT,
            MaxNumberOfMessages = n
        )

    queue_items = []
    q,r = divmod(nitems,10)
    nitems_per_thread = [10 for _ in range(0,q)]
    if r:
        nitems_per_thread.append(r)
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(nitems_per_thread)) as executor:
        results = executor.map(queue_receive,nitems_per_thread)
        for result in results:
            if result:
                queue_items += result
    return queue_items

def send_to_queue(queue, items):
    # Can only send <= 10 items at a time
    for i in range(0, len(items), 10):
        Entries = [
            {
                'Id': str(idx),
                'MessageBody': item
            } for idx, item in enumerate(items[i:i + 10])
        ]
        queue.send_messages(Entries=Entries)

def total_cases(db):
    return db.scalar(select(func.count()).select_from(Case))

def get_detail_loc(case_number):
    with db_session() as db:
        detail_loc, = db.scalar(
            select(Case.detail_loc)
            .where(Case.case_number == case_number)
        )
    return detail_loc

@contextmanager
def db_session():
    """Provide a transactional scope around a series of operations."""
    Session = sessionmaker(bind=config.db_engine, future=True)
    with Session.begin() as session:
        yield session

def delete_latest_scrape(db, case_number):
    versions = db.scalars(
        select(ScrapeVersion.s3_version_id)
        .where(ScrapeVersion.case_number == case_number)
    ).all()
    last_version_id = versions[0]
    last_version_obj = config.s3.ObjectVersion(
        config.CASE_DETAILS_BUCKET,
        case_number,
        last_version_id
    )
    last_version_obj.delete()
    db.execute(
        ScrapeVersion.__table__.delete()
            .where(
                and_(
                    ScrapeVersion.case_number == case_number,
                    ScrapeVersion.s3_version_id == last_version_id
                )
            )
    )
    if len(versions) > 1:
        # set last_scrape to timestamp of previous version
        db.execute(
            Case.__table__.update()
                .where(Case.case_number == case_number)
                .values(
                    last_scrape = select(Scrape.timestamp)
                        .where(
                            and_(
                                Scrape.case_number == case_number,
                                Scrape.s3_version_id == versions[1]
                            )
                        )
                )
        )
    elif len(versions) == 1:
        db.execute(
            Case.__table__.update()
                .where(Case.case_number == case_number)
                .values(last_scrape=None)
        )

def has_scrape(case_number):
    try:
        config.case_details_bucket.Object(case_number).get()
    except config.s3.meta.client.exceptions.NoSuchKey:
        return False
    else:
        return True

def split_date_range(start_date, end_date):
    assert(end_date)
    assert(end_date > start_date)
    days_diff = (end_date - start_date).days
    if days_diff == 1:
        range1 = [start_date, start_date]
        range2 = [end_date, end_date]
    elif days_diff == 2:
        range1 = [start_date, start_date + timedelta(1)]
        range2 = [end_date, end_date]
    else:
        range1 = [start_date, start_date + timedelta(int(days_diff / 2))]
        range2 = [start_date + timedelta(math.ceil((days_diff + 1) / 2)), end_date]
    return range1, range2

def float_to_decimal(obj):
    if isinstance(obj, float):
        return Decimal(str(obj))
    elif isinstance(obj, list):
        return [ float_to_decimal(x) for x in obj ]
    elif isinstance(obj, dict):
        return { k: float_to_decimal(v) for k, v in obj.items() }
    return obj

def decimal_to_float(obj):
    if isinstance(obj, Decimal):
        return float(obj)
    elif isinstance(obj, list):
        return [ decimal_to_float(x) for x in obj ]
    elif isinstance(obj, dict):
        return { k: decimal_to_float(v) for k, v in obj.items() }
    return obj

def get_queue_count(queue):
    queue.load()
    return int(queue.attributes['ApproximateNumberOfMessages'])

def get_model_list(module):
    class_list = [cls for name, cls in module.__dict__.items() if isinstance(cls, type) and hasattr(cls, '__table__')]
    class_list = [x for x in set(class_list)]  # Remove duplicates
    return class_list

def get_root_model_list(module):
    model_list = get_model_list(module)
    return list(filter(lambda model: hasattr(model, 'is_root') and model.is_root, model_list))

def get_orm_class_by_name(table_name):
    from . import models
    model_map = {cls.__table__.name: cls for name, cls in models.__dict__.items() if isinstance(cls, type) and hasattr(cls, '__table__')}
    try:
        return model_map[table_name]
    except KeyError:
        raise TableNotFound(f'Unknown database table {table_name}')

def get_case_model_list(module):
    model_list = [module.Case]
    for root_model in get_root_model_list(module):
        model_list.append(root_model)
        for rel_name, relationship in root_model.__mapper__.relationships.items():
            model = get_orm_class_by_name(relationship.target.name)
            if model not in model_list:
                model_list.append(model)
    return model_list