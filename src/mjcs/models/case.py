from sqlalchemy import Column, Boolean, Date, Integer, String, DateTime
from .common import TableBase

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
    scrape_exempt = Column(Boolean, default=False)
    parse_exempt = Column(Boolean, default=False)