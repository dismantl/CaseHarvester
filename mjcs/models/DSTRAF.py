from .common import TableBase, MetaColumn as Column, CaseTable, date_from_str
from sqlalchemy import Date, Numeric, Integer, String, Boolean, ForeignKey, Time, Index
from sqlalchemy.orm import relationship, backref
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.ext.declarative import declared_attr
from datetime import datetime

class DSTRAF(CaseTable, TableBase):
    '''District Court Traffic Cases'''
    __tablename__ = 'dstraf'
    is_root = True

    id = Column(Integer, primary_key=True)
    court_system = Column(String, enum=True)
    district_code = Column(Integer)
    location_code = Column(Integer)
    violation_date = Column(Date)
    _violation_date_str = Column('violation_date_str',String)
    violation_time = Column(Time)
    _violation_time_str = Column('violation_time_str', String)
    violation_county = Column(String, enum=True)
    agency_name = Column(String)
    officer_id = Column(String)
    officer_name = Column(String)
    case_status = Column(String, enum=True)

    case = relationship('Case', backref=backref('dstraf', uselist=False))

    __table_args__ = (Index('ixh_dstraf_case_number', 'case_number', postgresql_using='hash'),)

    @hybrid_property
    def violation_date_str(self):
        return self._violation_date_str
    @violation_date_str.setter
    def violation_date_str(self,val):
        self.violation_date = date_from_str(val)
        self._violation_date_str = val

    @hybrid_property
    def violation_time_str(self):
        return self._violation_time_str
    @violation_time_str.setter
    def violation_time_str(self,val):
        try:
            self.violation_time = datetime.strptime(val,'%I:%M %p').time()
        except:
            try:
                self.violation_time = datetime.strptime(val,'%I:%M').time()
            except:
                pass
        self._violation_time_str = val

class DSTRAFCaseTable(CaseTable):
    @declared_attr
    def case_number(self):
        return Column(String, ForeignKey('dstraf.case_number', ondelete='CASCADE'), nullable=False)

class DSTRAFCharge(DSTRAFCaseTable, TableBase):
    __tablename__ = 'dstraf_charges'
    __table_args__ = (Index('ixh_dstraf_charges_case_number', 'case_number', postgresql_using='hash'),)
    dstraf = relationship('DSTRAF', backref='charges')

    id = Column(Integer, primary_key=True)
    article = Column(String, enum=True)
    sec = Column(Integer)
    sub_sec = Column(String)
    para = Column(String)
    code = Column(String)
    description = Column(String)
    speed_limit = Column(Integer)
    recorded_speed = Column(Integer)
    location_stopped = Column(String)
    contributed_to_accident = Column(String)
    personal_injury = Column(String)
    property_damage = Column(String)
    seat_belts = Column(String)
    fine = Column(Numeric)
    related_citation_number = Column(String)
    vehicle_tag = Column(String)
    state = Column(String)
    vehicle_description = Column(String)

class DSTRAFDisposition(DSTRAFCaseTable, TableBase):
    __tablename__ = 'dstraf_dispositions'
    __table_args__ = (Index('ixh_dstraf_dispositions_case_number', 'case_number', postgresql_using='hash'),)
    dstraf = relationship('DSTRAF', backref='dispositions')

    id = Column(Integer, primary_key=True)
    plea = Column(String, enum=True)
    disposition = Column(String, enum=True)
    disposition_date = Column(Date)
    _disposition_date_str = Column('disposition_date_str',String)
    speed_limit = Column(Integer)
    convicted_speed = Column(Integer)
    contributed_to_accident = Column(String)
    alcohol_restriction = Column(String)
    personal_injury = Column(String)
    subsequent_offense = Column(String)
    alcohol_education = Column(String)
    driver_improvement = Column(String)
    sentence_date = Column(Date)
    _sentence_date_str = Column('sentence_date_str', String)
    sentence_years = Column(Integer)
    sentence_months = Column(Integer)
    sentence_days = Column(Integer)
    suspended_years = Column(Integer)
    suspended_months = Column(Integer)
    suspended_days = Column(Integer)
    sentence_starts = Column(Date)
    _sentence_starts_str = Column('sentence_starts_str',String)
    probation_type = Column(String, enum=True)
    fine = Column(Numeric)
    court_costs = Column(Numeric)
    cicf = Column(Numeric)
    suspended_fine = Column(Numeric)
    suspended_court_costs = Column(Numeric)
    suspended_cicf = Column(Numeric)
    addition_statement = Column(String)
    addition_article = Column(String)
    addition_sec = Column(Integer)
    addition_sub_sec = Column(String)
    addiiton_para = Column(String)
    addition_code = Column(String)
    addition_amended_charge = Column(String)
    notes = Column(String)

    @hybrid_property
    def sentence_date_str(self):
        return self._sentence_date_str
    @sentence_date_str.setter
    def sentence_date_str(self,val):
        self.sentence_date = date_from_str(val)
        self._sentence_date_str = val

    @hybrid_property
    def disposition_date_str(self):
        return self._disposition_date_str
    @disposition_date_str.setter
    def disposition_date_str(self,val):
        self.disposition_date = date_from_str(val)
        self._disposition_date_str = val
    
    @hybrid_property
    def sentence_starts_str(self):
        return self._sentence_starts_str
    @sentence_starts_str.setter
    def sentence_starts_str(self,val):
        self.sentence_starts = date_from_str(val)
        self._sentence_starts_str = val

class DSTRAFDefendant(DSTRAFCaseTable, TableBase):
    __tablename__ = 'dstraf_defendants'
    __table_args__ = (Index('ixh_dstraf_defendants_case_number', 'case_number', postgresql_using='hash'),)
    dstraf = relationship('DSTRAF', backref='defendants')
    
    id = Column(Integer, primary_key=True)
    name = Column(String, redacted=True)
    race = Column(String, enum=True)
    sex = Column(String)
    height = Column(Integer)
    weight = Column(Integer)
    DOB = Column(Date, redacted=True)
    _DOB_str = Column('DOB_str',String, redacted=True)
    address_1 = Column(String, redacted=True)
    address_2 = Column(String, redacted=True)
    city = Column(String)
    state = Column(String)
    zip_code = Column(String)

    @hybrid_property
    def DOB_str(self):
        return self._DOB_str
    @DOB_str.setter
    def DOB_str(self,val):
        self.DOB = date_from_str(val)
        self._DOB_str = val

class DSTRAFRelatedPerson(DSTRAFCaseTable, TableBase):
    __tablename__ = 'dstraf_related_persons'
    __table_args__ = (Index('ixh_dstraf_related_persons_case_number', 'case_number', postgresql_using='hash'),)
    dstraf = relationship('DSTRAF', backref='related_persons')

    id = Column(Integer, primary_key=True)
    name = Column(String)
    connection = Column(String, enum=True)
    address_1 = Column(String)
    address_2 = Column(String)
    city = Column(String)
    state = Column(String)
    zip_code = Column(String)

class DSTRAFEvent(DSTRAFCaseTable, TableBase):
    __tablename__ = 'dstraf_events'
    __table_args__ = (Index('ixh_dstraf_events_case_number', 'case_number', postgresql_using='hash'),)
    dstraf = relationship('DSTRAF', backref='events')

    id = Column(Integer, primary_key=True)
    event_name = Column(String, enum=True)
    date = Column(Date)
    _date_str = Column('date_str',String)
    comment = Column(String)

    @hybrid_property
    def date_str(self):
        return self._date_str
    @date_str.setter
    def date_str(self,val):
        self.date = datetime.strptime(val, '%Y-%m-%d').date()
        self._date_str = val

class DSTRAFTrial(DSTRAFCaseTable, TableBase):
    __tablename__ = 'dstraf_trials'
    __table_args__ = (Index('ixh_dstraf_trials_case_number', 'case_number', postgresql_using='hash'),)
    dstraf = relationship('DSTRAF', backref='trials')

    id = Column(Integer, primary_key=True)
    date = Column(Date)
    _date_str = Column('date_str', String)
    time = Column(Time)
    _time_str = Column('time_str', String)
    room = Column(String)
    location = Column(String)
    reason = Column(String)

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
