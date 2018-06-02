from .config import config
import sqlalchemy
from sqlalchemy import and_, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from contextlib import contextmanager
import h11

TableBase = declarative_base()

@contextmanager
def db_session():
    """Provide a transactional scope around a series of operations."""
    db_factory = sessionmaker(bind = config.db_engine)
    db = db_factory()
    try:
        yield db
        try:
            db.commit()
        except h11.RemoteProtocolError: # happens sometimes, try again
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
