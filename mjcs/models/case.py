from .common import TableBase, MetaColumn as Column
from sqlalchemy import Boolean, Date, Integer, String, DateTime, Index

class Case(TableBase):
    __tablename__ = 'cases'
    __table_args__ = (
        Index('ixh_cases_case_number', 'case_number', postgresql_using='hash'),
    )

    case_number = Column(String, primary_key=True)
    court = Column(String, enum=True)
    query_court = Column(String)
    case_type = Column(String)
    filing_date = Column(Date, index=True)
    filing_date_original = Column(String)
    status = Column(String, enum=True)
    caption = Column(String)
    loc = Column(Integer)
    detail_loc = Column(String, enum=True)
    last_scrape = Column(DateTime)
    last_parse = Column(DateTime)
    active = Column(Boolean, nullable=False, server_default='true')
    scrape_exempt = Column(Boolean, nullable=False, server_default='false')