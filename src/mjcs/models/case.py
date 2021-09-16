from .common import TableBase, MetaColumn as Column
from sqlalchemy import Boolean, Date, Integer, String, DateTime, Index

class Case(TableBase):
    __tablename__ = 'cases'
    __table_args__ = (
        Index('ixh_cases_case_number', 'case_number', postgresql_using='hash'),
        Index('ixh_cases_detail_loc', 'detail_loc', postgresql_using='hash'),
    )

    case_number = Column(String, primary_key=True)
    court = Column(String, enum=True)
    query_court = Column(String, nullable=True)
    case_type = Column(String, nullable=True)
    filing_date = Column(Date, nullable=True, index=True)
    filing_date_original = Column(String, nullable=True)
    status = Column(String, nullable=True, enum=True)
    caption = Column(String, nullable=True)
    loc = Column(Integer)
    detail_loc = Column(String, index=True, enum=True)
    last_scrape = Column(DateTime, nullable=True, index=True)
    last_parse = Column(DateTime, nullable=True, index=True)
    active = Column(Boolean, nullable=False, server_default='true')