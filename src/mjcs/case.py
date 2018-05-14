from .config import config
from .db import TableBase, column_windows, engine
from sqlalchemy import Column, Date, Integer, String, DateTime, LargeBinary, ForeignKey, UniqueConstraint
from sqlalchemy.sql import select
import zlib

def total_cases(db):
    return db.query(Case).count()

def cases_batch_filter(db, filter=None, batch_size=config.DB_BATCH_SIZE):
    for whereclause in column_windows(db, Case.case_number, batch_size, filter=filter):
        yield whereclause

def cases_batch(db, batch_filter):
    return db.query(Case).filter(batch_filter)

class Case(TableBase):
    __tablename__ = 'cases'

    case_number = Column(String, primary_key=True)
    court = Column(String)
    query_court = Column(String, nullable=True)
    case_type = Column(String, nullable=True)
    filing_date = Column(Date, nullable=True)
    filing_date_original = Column(String, nullable=True)
    status = Column(String, nullable=True)
    caption = Column(String, nullable=True)
    loc = Column(Integer)
    detail_loc = Column(String)
    url = Column(String)
    last_scrape = Column(DateTime, nullable=True)
    last_parse = Column(DateTime, nullable=True)

    def dict(self):
        return {
            'case_number': self.case_number,
            'court': self.court,
            'query_court': self.query_court,
            'case_type': self.case_type,
            'filing_date': self.filing_date,
            'filing_date_original': self.filing_date_original,
            'status': self.status,
            'caption': self.caption,
            'loc': self.loc,
            'detail_loc': self.detail_loc,
            'url': self.url
        }

def get_detail_loc(case_number):
    return engine.execute(
            select([Case.detail_loc])\
            .where(Case.case_number == case_number)
        ).scalar()
