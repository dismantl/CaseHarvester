import concurrent.futures
import sqlalchemy
import logging
from sqlalchemy import and_, func, select
from sqlalchemy.sql import select
from sqlalchemy.orm import sessionmaker
from contextlib import contextmanager
from .config import config
from .models import Case, ScrapeVersion, Scrape

logger = logging.getLogger(__name__)

class NoItemsInQueue(Exception):
    pass

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

def total_cases(db):
    return db.query(Case).count()

def cases_batch_filter(db, filter=None, batch_size=None):
    if not batch_size:
        batch_size = config.CASE_BATCH_SIZE
    for whereclause in column_windows(db, Case.case_number, batch_size, filter=filter):
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

def process_cases(func, cases, on_success=None, on_error=None, threads=1, counter=None):
    to_process = [_ for _ in cases]
    continue_processing = True
    caught_exception = None
    while to_process and continue_processing:
        if threads == 1:
            for case in to_process:
                case_number = case['case_number'] if type(case) == dict else case
                if counter:
                    logger.debug('Processing case %s (%s of %s)' % (case_number,counter['count'],counter['total']))
                    counter['count'] += 1
                try:
                    func(case)
                # except NotImplementedError:
                #     pass
                except Exception as e:
                    continue_processing = False
                    logger.exception(e)
                    logger.warning("Failed to process case %s" % case_number)
                    if on_error:
                        action = on_error(e, case)
                        if action == 'delete':
                            to_process.remove(case)
                        if action == 'continue' or action == 'delete':
                            continue_processing = True
                    else:
                        caught_exception = e
                    break
                else:
                    if on_success:
                        on_success(case)
                    to_process.remove(case)
        else:
            with concurrent.futures.ThreadPoolExecutor(max_workers=threads) as executor:
                future_to_case = {}
                for case in to_process:
                    future_to_case[executor.submit(func, case)] = case
                for future in concurrent.futures.as_completed(future_to_case):
                    case = future_to_case[future]
                    case_number = case['case_number'] if type(case) == dict else case
                    try:
                        future.result()
                    except concurrent.futures.CancelledError:
                        pass
                    except Exception as e: # Won't catch KeyboardInterrupt, which is raised in as_completed
                        continue_processing = False
                        # cancel all remaining tasks
                        for future in future_to_case:
                            future.cancel()
                        logger.exception(e)
                        logger.warning("Failed to process case %s" % case_number)
                        if on_error:
                            action = on_error(e, case)
                            if action == 'delete':
                                to_process.remove(case)
                            if action == 'continue' or action == 'delete':
                                continue_processing = True
                            if counter:
                                counter['count'] += 1
                                logger.debug('Processed case %s (%s of %s)' % (case_number,counter['count'],counter['total']))
                        else:
                            caught_exception = e
                    else:
                        if on_success:
                            on_success(case)
                        to_process.remove(case)
                        if counter:
                            counter['count'] += 1
                            logger.debug('Processed case %s (%s of %s)' % (case_number,counter['count'],counter['total']))
        if caught_exception:
            raise caught_exception

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
def column_windows(session, column, windowsize, filter=None):
    """Return a series of WHERE clauses against
    a given column that break it into windows.

    Result is an iterable of tuples, consisting of
    ((start, end), whereclause), where (start, end) are the ids.

    Requires a database that supports window functions,
    i.e. Postgresql, SQL Server, Oracle.

    Enhance this yourself !  Add a "where" argument
    so that windows of just a subset of rows can
    be computed.

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

    q = session.query(
                column,
                func.row_number().\
                        over(order_by=column).\
                        label('rownum')
                )
    if filter is not None: # http://docs.sqlalchemy.org/en/latest/changelog/migration_06.html#an-important-expression-language-gotcha
        q = q.filter(filter)
    q = q.from_self(column)

    if windowsize > 1:
        q = q.filter(sqlalchemy.text("rownum %% %d=1" % windowsize))

    intervals = [id for id, in q]

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
