import concurrent.futures
import sqlalchemy
import logging
import math
import json
from decimal import Decimal
from datetime import timedelta, datetime
from sqlalchemy import and_, func, select
from sqlalchemy.sql import select
from sqlalchemy.orm import sessionmaker
from contextlib import contextmanager
from .config import config
from .models import Case, ScrapeVersion, Scrape

logger = logging.getLogger(__name__)

class NoItemsInQueue(Exception):
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
    chunks = [items[i:i + 10] for i in range(0, len(items), 10)]
    for chunk in chunks:
        Entries = [
            {
                'Id': str(idx),
                'MessageBody': item
            } for idx, item in enumerate(chunk)
        ]
        queue.send_messages(Entries=Entries)

def total_cases(db):
    return db.query(Case).count()

def cases_batch_filter(db, filter=None, batch_size=None, limit=None):
    if not batch_size:
        batch_size = config.CASE_BATCH_SIZE
    for whereclause in column_windows(db, Case.case_number, batch_size, filter, limit):
        yield whereclause

def cases_batch(db, batch_filter):
    return db.query(Case).filter(batch_filter)

def get_detail_loc(case_number):
    with db_session() as db:
        detail_loc = db.execute(
                select([Case.detail_loc])\
                .where(Case.case_number == case_number)
            ).scalar()
    return detail_loc

@contextmanager
def db_session():
    """Provide a transactional scope around a series of operations."""
    db_factory = sessionmaker(bind = config.db_engine)
    db = db_factory()
    try:
        yield db
        db.commit()
    except:
        db.rollback()
        raise
    finally:
        db.close()

# https://stackoverflow.com/questions/7389759/memory-efficient-built-in-sqlalchemy-iterator-generator
# Adapted from https://bitbucket.org/zzzeek/sqlalchemy/wiki/UsageRecipes/WindowedRangeQuery
def column_windows(session, column, windowsize, filter=None, limit=None):
    """Return a series of WHERE clauses against
    a given column that break it into windows.

    Requires a database that supports window functions,
    i.e. Postgresql, SQL Server, Oracle.
    """
    def int_for_range(start_id, end_id):
        if filter is not None:
            if end_id:
                return and_(
                    column>=start_id,
                    column<end_id,
                    filter
                )
            else:
                return and_(
                    column>=start_id,
                    filter
                )
        else:
            if end_id:
                return and_(
                    column>=start_id,
                    column<end_id
                )
            else:
                return column>=start_id

    # Use the row_number() window function to order and number all rows
    q = session.query(
                column,
                func.row_number().\
                        over(order_by=column).\
                        label('rownum')
                )
    
    # Add any additional filters that will be applied before the window function
    if filter is not None: # http://docs.sqlalchemy.org/en/latest/changelog/migration_06.html#an-important-expression-language-gotcha
        q = q.filter(filter)
    
    # Limit the inner subquery where rows are sorted and numbered
    if limit:
        q = q.limit(limit)

    # Create outer query selecting from inner subquery
    q = q.from_self(column)

    # Collect the column IDs for the rows at the boundary of each window
    if windowsize > 1:
        q = q.filter(sqlalchemy.text(f'rownum % {windowsize}=1'))
    intervals = [id for id, in q]

    # Yield WHERE clauses using column ID ranges 
    while intervals:
        start = intervals.pop(0)
        if intervals:
            end = intervals[0]
        else:
            end = None
        yield int_for_range(start, end)

def delete_latest_scrape(db, case_number):
    versions = [_ for _, in db.query(ScrapeVersion.s3_version_id)\
        .filter(ScrapeVersion.case_number == case_number)]
    last_version_id = versions[0]
    last_version_obj = config.s3.ObjectVersion(
        config.CASE_DETAILS_BUCKET,
        case_number,
        last_version_id
    )
    last_version_obj.delete()
    db.execute(
        ScrapeVersion.__table__.delete()\
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
            Case.__table__.update()\
                .where(Case.case_number == case_number)\
                .values(
                    last_scrape = select([Scrape.timestamp])\
                        .where(
                            and_(
                                Scrape.case_number == case_number,
                                Scrape.s3_version_id == versions[1]
                            )
                        ).as_scalar()
                )
        )
    elif len(versions) == 1:
        db.execute(
            Case.__table__.update()\
                .where(Case.case_number == case_number)\
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
        range1 = [start_date, None]
        range2 = [end_date, None]
    elif days_diff == 2:
        range1 = [start_date, start_date + timedelta(1)]
        range2 = [end_date, None]
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