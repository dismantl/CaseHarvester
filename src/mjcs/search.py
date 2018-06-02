from .config import config
from .db import TableBase, column_windows
from sqlalchemy import Column, Date, Integer, String, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from datetime import *
import zlib

class SearchItemResult(TableBase):
    __tablename__ = 'query_results'

    id = Column(Integer, primary_key=True)
    search_id = Column(String, ForeignKey('queue.id'))
    nresults = Column(Integer)
    timestamp = Column(DateTime)
    query_seconds = Column(Integer)

    search_item = relationship('SearchItem', back_populates='results')

    __table_args__ = (UniqueConstraint('search_id', 'timestamp', name='_search_id_timestamp_uc'),
                     )

    def __init__(self, search_id, nresults, timestamp, query_seconds):
        super().__init__(
            search_id = search_id,
            nresults = nresults,
            timestamp = timestamp,
            query_seconds = query_seconds
        )

def clear_queue(db):
    db.execute(
        SearchItem.__table__.update().where(SearchItem.status.in_(['new','retry'])).values(status='canceled')
    )

def active_items_batch_filter(db):
    for whereclause in column_windows(db, SearchItem.id, config.CASE_BATCH_SIZE, SearchItem.status.in_(['new','retry'])):
        yield whereclause

def active_items_batch(db, batch_filter):
    return db.query(SearchItem).filter(batch_filter)

def active_items(db, filter=None):
    q = db.query(SearchItem).filter(SearchItem.status.in_(['new','retry']))
    if filter:
        q = q.filter(filter)
    return q

def active_count(db, filter=None):
    q = active_items(db)
    if filter:
        q = q.filter(filter)
    return q.count()

class SearchItem(TableBase):
    __tablename__ = 'queue'

    id = Column(String, primary_key=True)
    search_string = Column(String)
    start_date = Column(Date)
    end_date = Column(Date, nullable=True)
    court = Column(String, nullable=True)
    status = Column(String, default='new')
    timeouts = Column(Integer, default=0)
    err500s = Column(Integer, default=0)
    errunknown = Column(String, nullable=True)

    results = relationship('SearchItemResult', back_populates='search_item')

    def __init__(self, search_string, start_date, end_date=None, court=None, status='new'):
        id = search_string + start_date.strftime("%-m/%-d/%Y")
        if end_date:
            id += end_date.strftime("%-m/%-d/%Y")
        if court:
            id += court
        super().__init__(
            id=id,
            search_string=search_string,
            start_date=start_date,
            end_date=end_date,
            court=court,
            status=status,
            timeouts = 0,
            err500s = 0
        )

    def dict(self):
        return {
            'id': self.id,
            'search_string': self.search_string,
            'start_date': self.start_date,
            'end_date': self.end_date,
            'court': self.court,
            'status': self.status,
            'timeouts': self.timeouts,
            'err500s': self.err500s,
            'errunknown': self.errunknown
        }

    def handle_unknown_err(self, error):
        self.errunknown = error
        self.status = 'failed'

    def handle_500(self):
        if self.err500s >= config.QUERY_ERROR_LIMIT:
            self.status = 'failed'
        else:
            self.err500s += 1
            self.status = 'retry'

    def handle_timeout(self, db):
        # For timeouts, split the date range in half and add both to queue
        if self.end_date:
            time_diff = self.end_date - self.start_date
            if time_diff.days == 1:
                item1 = [self.start_date, self.start_date + timedelta(days=(time_diff / 2).days)]
                item2 = [self.start_date + timedelta(time_diff.days + 1 / 2), self.end_date]
            else:
                item1 = [self.start_date, None]
                item2 = [self.end_date, None]
            print("Appending %s from %s to %s" % (self.search_string, item1[0], item1[1]))
            db.merge(SearchItem(
                search_string = self.search_string,
                start_date = item1[0],
                end_date = item1[1],
                court = self.court,
                status = 'new'
            ))
            print("Appending %s from %s to %s" % (self.search_string, item2[0], item2[1]))
            db.merge(SearchItem(
                search_string = self.search_string,
                start_date = item2[0],
                end_date = item2[1],
                court = self.court,
                status = 'new'
            ))
            self.status = 'timeout-split'
        else:
            if self.timeouts >= config.QUERY_TIMEOUTS_LIMIT:
                self.status = 'failed'
            else:
                self.timeouts += 1
                self.status = 'retry'

    def handle_complete(self, db, nresults, query_start, query_time):
        db.add(SearchItemResult(
            search_id = self.id,
            nresults = nresults,
            timestamp = query_start,
            query_seconds = query_time
        ))
        self.status = 'completed'
