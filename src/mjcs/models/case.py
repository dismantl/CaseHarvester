from sqlalchemy import Column, Boolean, Date, Integer, String, DateTime, Index
from .common import TableBase

class Case(TableBase):
    __tablename__ = 'cases'
    __table_args__ = (
        Index('ixh_cases_case_number', 'case_number', postgresql_using='hash'),
    )

    case_number = Column(String, primary_key=True)
    court = Column(String)
    query_court = Column(String, nullable=True)
    case_type = Column(String, nullable=True)
    filing_date = Column(Date, nullable=True, index=True)
    filing_date_original = Column(String, nullable=True)
    status = Column(String, nullable=True)
    caption = Column(String, nullable=True)
    loc = Column(Integer)
    detail_loc = Column(String)
    url = Column(String)
    last_scrape = Column(DateTime, nullable=True)
    last_parse = Column(DateTime, nullable=True)
    scrape_exempt = Column(Boolean, nullable=False, server_default='false')
    parse_exempt = Column(Boolean, nullable=False, server_default='false')
    active = Column(Boolean, nullable=False, server_default='true')