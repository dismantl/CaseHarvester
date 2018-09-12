from .db import TableBase
from .search import active_count
from .case import total_cases
from sqlalchemy import Column, Date, Integer, String, Boolean, DateTime
from datetime import *

class Run(TableBase):
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

    def __init__(self,
            db,
            start_date=None,
            end_date=None,
            court=None,
            queue_still_active=0,
            queue_finished=0,
            cases_added=0,
            results_processed=0,
            overwrite=False,
            force_scrape=False,
            retry_failed=False
        ):
        super().__init__(
            query_start_date = start_date,
            query_end_date = end_date,
            court = court,
            run_start = datetime.utcnow(),
            queue_still_active = queue_still_active,
            queue_finished = queue_finished,
            cases_added = cases_added,
            results_processed = results_processed,
            retry_failed = retry_failed
        )
        self.start_ncases = total_cases(db)
        self.overwrite = overwrite
        self.force_scrape = force_scrape

    def update(self, db):
        current_time = datetime.utcnow()
        self.run_seconds = (current_time - self.run_start).total_seconds()
        self.queue_still_active = active_count(db) # TODO support stats for failed retry runs
        self.cases_added = total_cases(db) - self.start_ncases
        print("Run updated!")
        print("Finished in %s seconds" % str(self.run_seconds))
        print("Number of query items still active in queue: %d" % self.queue_still_active)
        print("Number of query items finished: %d" % self.queue_finished)
        print("Number of cases added: %d" % self.cases_added)
        print("Number of results processed: %d" % self.results_processed)
        # TODO average query time
        # TODO # failed searches
