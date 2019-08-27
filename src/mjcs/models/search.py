from sqlalchemy import Column, Date, Integer, String, DateTime, ForeignKey, UniqueConstraint
from .common import TableBase

class SearchItemStatus:
    new = 'new'
    retry = 'retry'
    canceled = 'canceled'
    failed = 'failed'
    timeout_split = 'timeout-split'
    completed = 'completed'

class SearchItemResult(TableBase):
    __tablename__ = 'query_results'

    id = Column(Integer, primary_key=True)
    search_id = Column(String, ForeignKey('queue.id'))
    nresults = Column(Integer)
    timestamp = Column(DateTime)
    query_seconds = Column(Integer)

    # search_item = relationship('SearchItem', back_populates='results')

    __table_args__ = (UniqueConstraint('search_id', 'timestamp', name='_search_id_timestamp_uc'),
                     )

    def __init__(self, search_id, nresults, timestamp, query_seconds):
        super().__init__(
            search_id = search_id,
            nresults = nresults,
            timestamp = timestamp,
            query_seconds = query_seconds
        )

class BaseSearchItem(TableBase):
    __tablename__ = 'queue'

    id = Column(String, primary_key=True)
    search_string = Column(String)
    start_date = Column(Date)
    end_date = Column(Date, nullable=True)
    court = Column(String, nullable=True)
    status = Column(String, default=SearchItemStatus.new)
    timeouts = Column(Integer, default=0)
    err500s = Column(Integer, default=0)
    errunknown = Column(String, nullable=True)
