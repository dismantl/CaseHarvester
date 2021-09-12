from .common import TableBase, CaseTable, date_from_str, MetaColumn as Column
from sqlalchemy import Date, Numeric, Integer, String, Boolean, ForeignKey, Time, Text, Index
from sqlalchemy.orm import relationship, backref
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.ext.declarative import declared_attr
from datetime import datetime

class DV(CaseTable, TableBase):
    '''Domestic Violence Cases'''
    __tablename__ = 'dv'
    __table_args__ = (Index('ixh_dv_case_number', 'case_number', postgresql_using='hash'),)
    is_root = True

    id = Column(Integer, primary_key=True)
    court_system = Column(String, enum=True)
    case_type = Column(String, enum=True)
    filing_date = Column(Date)
    _filing_date_str = Column('filing_date_str',String)
    case_status = Column(String, enum=True)
    order_valid_thru = Column(Date)
    _order_valid_thru_str = Column('order_valid_thru_str',String)

    case = relationship('Case', backref=backref('dv', uselist=False))

    @hybrid_property
    def filing_date_str(self):
        return self._filing_date_str
    @filing_date_str.setter
    def filing_date_str(self,val):
        self.filing_date = date_from_str(val)
        self._filing_date_str = val

    @hybrid_property
    def order_valid_thru_str(self):
        return self._order_valid_thru_str
    @order_valid_thru_str.setter
    def order_valid_thru_str(self,val):
        self.order_valid_thru = date_from_str(val)
        self._order_valid_thru_str = val

class DVCaseTable(CaseTable):
    @declared_attr
    def case_number(self):
        return Column(String, ForeignKey('dv.case_number', ondelete='CASCADE'), nullable=False)

class DVDefendant(DVCaseTable, TableBase):
    __tablename__ = 'dv_defendants'
    __table_args__ = (Index('ixh_dv_defendants_case_number', 'case_number', postgresql_using='hash'),)
    dv = relationship('DV', backref='defendants')

    id = Column(Integer, primary_key=True)
    name = Column(String, redacted=True)
    city = Column(String)
    state = Column(String)
    DOB = Column(Date, redacted=True)
    _DOB_str = Column('DOB_str', String, redacted=True)

    @hybrid_property
    def DOB_str(self):
        return self._DOB_str
    @DOB_str.setter
    def DOB_str(self,val):
        self.DOB = date_from_str(val)
        self._DOB_str = val

class DVDefendantAttorney(DVCaseTable, TableBase):
    __tablename__ = 'dv_defendant_attorneys'
    __table_args__ = (Index('ixh_dv_defendant_attorneys_case_number', 'case_number', postgresql_using='hash'),)
    dv = relationship('DV', backref='defendant_attorneys')

    id = Column(Integer, primary_key=True)
    name = Column(String)

class DVHearing(DVCaseTable, TableBase):
    __tablename__ = 'dv_hearings'
    __table_args__ = (Index('ixh_dv_hearings_case_number', 'case_number', postgresql_using='hash'),)
    dv = relationship('DV', backref='hearings')

    id = Column(Integer, primary_key=True)
    hearing_date = Column(Date)
    _hearing_date_str = Column('hearing_date_str',String)
    hearing_time = Column(Time, nullable=True)
    _hearing_time_str = Column('hearing_time_str', String)
    room = Column(String)
    location = Column(String, enum=True)
    served_date = Column(Date)
    _served_date_str = Column('served_date_str',String)
    hearing_type = Column(String, enum=True)
    result = Column(String)

    @hybrid_property
    def hearing_date_str(self):
        return self._hearing_date_str
    @hearing_date_str.setter
    def hearing_date_str(self,val):
        self.hearing_date = date_from_str(val)
        self._hearing_date_str = val

    @hybrid_property
    def hearing_time_str(self):
        return self._hearing_time_str
    @hearing_time_str.setter
    def hearing_time_str(self,val):
        try:
            self.time = datetime.strptime(val,'%I:%M %p').time()
        except:
            try:
                self.time = datetime.strptime(val,'%I:%M').time()
            except:
                pass
        self._hearing_time_str = val

    @hybrid_property
    def served_date_str(self):
        return self._served_date_str
    @served_date_str.setter
    def served_date_str(self,val):
        self.served_date = date_from_str(val)
        self._served_date_str = val
    
class DVEvent(DVCaseTable, TableBase):
    __tablename__ = 'dv_events'
    __table_args__ = (Index('ixh_dv_events_case_number', 'case_number', postgresql_using='hash'),)
    dv = relationship('DV', backref='events')

    id = Column(Integer, primary_key=True)
    event_date = Column(Date)
    _event_date_str = Column('event_date_str',String)
    description = Column(String)

    @hybrid_property
    def event_date_str(self):
        return self._event_date_str
    @event_date_str.setter
    def event_date_str(self,val):
        self.event_date = date_from_str(val)
        self._event_date_str = val