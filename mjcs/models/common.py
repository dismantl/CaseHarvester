from sqlalchemy import Column, Date, Numeric, Integer, String, Boolean, ForeignKey, Time, UniqueConstraint
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.ext.declarative import declared_attr
import re
from datetime import datetime

TableBase = declarative_base()

def date_from_str(date_str):
    if date_str:
        try:
            return datetime.strptime(date_str,"%m/%d/%Y")
        except:
            return None
    return None

class MetaColumn(Column):
    inherit_cache = True
    def __init__(self, *args, **kwargs):
        self.enum = kwargs.pop('enum', False)
        self.redacted = kwargs.pop('redacted', False)
        super(MetaColumn, self).__init__(*args, **kwargs)
Column = MetaColumn

class ColumnMetadata(TableBase):
    __tablename__ = 'column_metadata'
    __table_args__ = (UniqueConstraint('table', 'column_name', name='column_metadata_table_column_name_key'),)

    id = Column(Integer, primary_key=True)
    table = Column(String, nullable=False)
    column_name = Column(String, nullable=False)
    label = Column(String)
    description = Column(String)
    allowed_values = Column(ARRAY(String, dimensions=1))
    redacted = Column(Boolean, nullable=False, server_default='false')
    order = Column(Integer)

class CaseTable:
    @declared_attr
    def case_number(cls):
        return Column(String, ForeignKey('cases.case_number', ondelete='CASCADE'), unique=True)
