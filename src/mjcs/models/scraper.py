from sqlalchemy import Column, DateTime, Integer, Numeric, String, ForeignKey, Index
from .common import TableBase

class ScrapeVersion(TableBase):
    __tablename__ = 'scrape_versions'

    s3_version_id = Column(String, primary_key=True)
    case_number = Column(String, ForeignKey('cases.case_number', ondelete='CASCADE'), index=True)
    length = Column(Integer)
    sha256 = Column(String)

class Scrape(TableBase):
    __tablename__ = 'scrapes'

    id = Column(Integer, primary_key=True)
    case_number = Column(String, ForeignKey('cases.case_number', ondelete='CASCADE'), index=True)
    s3_version_id = Column(String, ForeignKey('scrape_versions.s3_version_id', ondelete='CASCADE'))
    timestamp = Column(DateTime)
    duration = Column(Numeric, nullable=True) # seconds

Index('ix_scrape_timestamp', Scrape.case_number, Scrape.timestamp.desc())
