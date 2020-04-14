from sqlalchemy import Column, Boolean, Date, Integer, String, DateTime
from .common import TableBase

class Case(TableBase):
    __tablename__ = 'cases'

    case_number = Column(String, primary_key=True)
    court = Column(String, index=True)
    query_court = Column(String, nullable=True, index=True)
    case_type = Column(String, nullable=True, index=True)
    filing_date = Column(Date, nullable=True, index=True)
    filing_date_original = Column(String, nullable=True, index=True)
    status = Column(String, nullable=True, index=True)
    caption = Column(String, nullable=True)
    loc = Column(Integer)
    detail_loc = Column(String, index=True)
    url = Column(String)
    last_scrape = Column(DateTime, nullable=True, index=True)
    last_parse = Column(DateTime, nullable=True, index=True)
    scrape_exempt = Column(Boolean, default=False, index=True)
    parse_exempt = Column(Boolean, default=False, index=True)