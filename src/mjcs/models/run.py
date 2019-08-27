from sqlalchemy import Column, Date, Integer, String, Boolean, DateTime
from .common import TableBase

class BaseRun(TableBase):
    __tablename__ = 'runs'

    id = Column(Integer, primary_key=True)
    query_start_date = Column(Date, nullable=True)
    query_end_date = Column(Date, nullable=True)
    court = Column(String, nullable=True)
    run_start = Column(DateTime)
    run_seconds = Column(Integer)
    queue_still_active = Column(Integer)
    queue_finished = Column(Integer)
    cases_added = Column(Integer)
    results_processed = Column(Integer)
    retry_failed = Column(Boolean)
