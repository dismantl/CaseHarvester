from sqlalchemy import Column, DateTime, Integer, Numeric, String, ForeignKey, Index
from .common import TableBase

class ScrapeVersion(TableBase):
    __tablename__ = 'scrape_versions'

    s3_version_id = Column(String, primary_key=True)
    case_number = Column(String, ForeignKey('cases.case_number', ondelete='CASCADE'))
    length = Column(Integer)
    sha256 = Column(String)

Index('ix_scrapes_versions_case_number_s3_version_id', ScrapeVersion.case_number, ScrapeVersion.s3_version_id, unique=True)

class Scrape(TableBase):
    __tablename__ = 'scrapes'

    id = Column(Integer, primary_key=True)
    case_number = Column(String, ForeignKey('cases.case_number', ondelete='CASCADE'))
    s3_version_id = Column(String, ForeignKey('scrape_versions.s3_version_id', ondelete='CASCADE'))
    timestamp = Column(DateTime)
    duration = Column(Numeric) # seconds
    error = Column(String)

Index('ix_scrapes_case_number_timestamp', Scrape.case_number, Scrape.timestamp.desc(), unique=True)
Index('ix_scrapes_case_number_s3_version_id', Scrape.case_number, Scrape.s3_version_id, unique=True)