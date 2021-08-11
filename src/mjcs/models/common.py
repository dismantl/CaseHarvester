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
    def __init__(self, *args, **kwargs):
        self.enum = kwargs.pop('enum', False)
        self.redacted = kwargs.pop('redacted', False)
        super(MetaColumn, self).__init__(*args, **kwargs)
Column = MetaColumn

class ColumnMetadata(TableBase):
    __tablename__ = 'column_metadata'
    __table_args__ = (UniqueConstraint('table', 'column_name', name='column_metadata_column_name_width_pixels_key'),)

    id = Column(Integer, primary_key=True)
    table = Column(String, nullable=False)
    column_name = Column(String, nullable=False)
    description = Column(String)
    width_pixels = Column(Integer)
    allowed_values = Column(ARRAY(String, dimensions=1))

class CaseTable:
    @declared_attr
    def case_number(cls):
        return Column(String, ForeignKey('cases.case_number', ondelete='CASCADE'), unique=True)

class Defendant:
    id = Column(Integer, primary_key=True)
    name = Column(String, redacted=True)
    race = Column(String, nullable=True)
    sex = Column(String, nullable=True)
    height = Column(Integer, nullable=True)
    weight = Column(Integer, nullable=True)
    DOB = Column(Date, nullable=True, redacted=True)
    _DOB_str = Column('DOB_str',String, nullable=True, redacted=True)
    address_1 = Column(String, nullable=True, redacted=True)
    address_2 = Column(String, nullable=True, redacted=True)
    city = Column(String, nullable=True)
    state = Column(String, nullable=True)
    zip_code = Column(String, nullable=True)

    @hybrid_property
    def DOB_str(self):
        return self._DOB_str
    @DOB_str.setter
    def DOB_str(self,val):
        self.DOB = date_from_str(val)
        self._DOB_str = val

class DefendantAlias:
    id = Column(Integer, primary_key=True)
    alias_name = Column(String, nullable=True)
    address_1 = Column(String, nullable=True)
    address_2 = Column(String, nullable=True)
    city = Column(String, nullable=True)
    state = Column(String, nullable=True)
    zip_code = Column(String, nullable=True)

class RelatedPerson:
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=True)
    connection = Column(String, nullable=True, enum=True)
    address_1 = Column(String, nullable=True)
    address_2 = Column(String, nullable=True)
    city = Column(String, nullable=True)
    state = Column(String, nullable=True)
    zip_code = Column(String, nullable=True)
    agency_code = Column(String, nullable=True, enum=True)
    agency_sub_code = Column(String, nullable=True)
    officer_id = Column(String, nullable=True)
    attorney_code = Column(Integer,nullable=True)
    attorney_firm = Column(String,nullable=True)

class Trial:
    id = Column(Integer, primary_key=True)
    date = Column(Date, nullable=True)
    _date_str = Column('date_str', String, nullable=True)
    time = Column(Time, nullable=True)
    _time_str = Column('time_str', String, nullable=True)
    room = Column(String, nullable=True)
    trial_type = Column(String, nullable=True, enum=True)
    location = Column(String, nullable=True)
    reason = Column(String,nullable=True)

    @hybrid_property
    def date_str(self):
        return self._date_str
    @date_str.setter
    def date_str(self,val):
        self.date = date_from_str(val)
        self._date_str = val

    @hybrid_property
    def time_str(self):
        return self._time_str
    @time_str.setter
    def time_str(self,val):
        try:
            self.time = datetime.strptime(val,'%I:%M %p').time()
        except:
            try:
                self.time = datetime.strptime(val,'%I:%M').time()
            except:
                pass
        self._time_str = val

class Event:
    id = Column(Integer, primary_key=True)
    event_name = Column(String, nullable=True, enum=True)
    date = Column(Date, nullable=True)
    _date_str = Column('date_str',String, nullable=True)
    comment = Column(String, nullable=True)

    @hybrid_property
    def date_str(self):
        return self._date_str
    @date_str.setter
    def date_str(self,val):
        self.date = date_from_str(val)
        self._date_str = val
