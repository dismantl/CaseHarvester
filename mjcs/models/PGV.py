from sqlalchemy.sql.schema import Table
from .common import TableBase, MetaColumn as Column, CaseTable, date_from_str
from sqlalchemy import Date, Numeric, Integer, String, Boolean, ForeignKey, Index, Time
from sqlalchemy.orm import relationship, backref
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.ext.declarative import declared_attr
from datetime import datetime

class PGV(CaseTable, TableBase):
    '''Prince George's County Circuit Court Civil Cases'''
    __tablename__ = 'pgv'
    is_root = True

    id = Column(Integer, primary_key=True)
    court_system = Column(String, enum=True)
    case_description = Column(String)
    case_type = Column(String, enum=True)
    filing_date = Column(Date)
    _filing_date_str = Column('filing_date_str',String)
    case_status = Column(String, enum=True)

    case = relationship('Case', backref=backref('pgv', uselist=False))

    __table_args__ = (Index('ixh_pgv_case_number', 'case_number', postgresql_using='hash'),)

    @hybrid_property
    def filing_date_str(self):
        return self._filing_date_str
    @filing_date_str.setter
    def filing_date_str(self,val):
        self.filing_date = date_from_str(val)
        self._filing_date_str = val

class PGVCaseTable(CaseTable):
    @declared_attr
    def case_number(self):
        return Column(String, ForeignKey('pgv.case_number', ondelete='CASCADE'), nullable=False)

class PGVPlaintiff(PGVCaseTable, TableBase):
    __tablename__ = 'pgv_plaintiffs'
    __table_args__ = (Index('ixh_pgv_plaintiffs_case_number', 'case_number', postgresql_using='hash'),)
    pgv = relationship('PGV', backref='plaintiffs')

    id = Column(Integer, primary_key=True)
    party_number = Column(Integer)
    party_type = Column(String)
    name = Column(String)
    address_1 = Column(String)
    city = Column(String)
    state = Column(String)
    zip_code = Column(String)
    attorneys = relationship('PGVAttorney')

class PGVDefendant(PGVCaseTable, TableBase):
    __tablename__ = 'pgv_defendants'
    __table_args__ = (Index('ixh_pgv_defendants_case_number', 'case_number', postgresql_using='hash'),)
    pgv = relationship('PGV', backref='defendants')

    id = Column(Integer, primary_key=True)
    party_number = Column(Integer)
    party_type = Column(String)
    name = Column(String)
    address_1 = Column(String)
    city = Column(String)
    state = Column(String)
    zip_code = Column(String)
    attorneys = relationship('PGVAttorney')

class PGVDefendantAlias(PGVCaseTable, TableBase):
    __tablename__ = 'pgv_defendant_aliases'
    __table_args__ = (Index('ixh_pgv_defendant_aliases_case_number', 'case_number', postgresql_using='hash'),)
    pgv = relationship('PGV', backref='defendant_aliases')

    id = Column(Integer, primary_key=True)
    alias_name = Column(String)

class PGVAttorney(PGVCaseTable, TableBase):
    __tablename__ = 'pgv_attorneys'
    __table_args__ = (Index('ixh_pgv_attorneys_case_number', 'case_number', postgresql_using='hash'),)
    pgv = relationship('PGV', backref='attorneys')

    id = Column(Integer, primary_key=True)
    name = Column(String)
    attorney_type = Column(String, enum=True)
    address = Column(String)
    city = Column(String)
    state = Column(String)
    zip_code = Column(String)
    defendant_id = Column(Integer, ForeignKey('pgv_defendants.id'))
    plaintiff_id = Column(Integer, ForeignKey('pgv_plaintiffs.id'))

class PGVOtherParty(PGVCaseTable, TableBase):
    __tablename__ = 'pgv_other_parties'
    __table_args__ = (Index('ixh_pgv_other_parties_case_number', 'case_number', postgresql_using='hash'),)
    pgv = relationship('PGV', backref='other_parties')

    id = Column(Integer, primary_key=True)
    party_type = Column(String, enum=True)
    party_number = Column(Integer)
    name = Column(String)

class PGVJudgment(PGVCaseTable, TableBase):
    __tablename__ = 'pgv_judgments'
    __table_args__ = (Index('ixh_pgv_judgments_case_number', 'case_number', postgresql_using='hash'),)
    pgv = relationship('PGV', backref='judgments')

    id = Column(Integer, primary_key=True)
    judgment_date = Column(Date)
    _judgment_date_str = Column('judgment_date_str',String)
    status_date = Column(Date)
    _status_date_str = Column('status_date_str',String)
    status = Column(String, enum=True)
    amount = Column(Numeric)
    against = Column(String)

    @hybrid_property
    def judgment_date_str(self):
        return self._judgment_date_str
    @judgment_date_str.setter
    def judgment_date_str(self,val):
        self.judgment_date = date_from_str(val)
        self._judgment_date_str = val

    @hybrid_property
    def status_date_str(self):
        return self._status_date_str
    @status_date_str.setter
    def status_date_str(self,val):
        self.status_date = date_from_str(val)
        self._status_date_str = val

class PGVCourtSchedule(PGVCaseTable, TableBase):
    __tablename__ = 'pgv_court_schedule'
    __table_args__ = (Index('ixh_pgv_court_schedule_case_number', 'case_number', postgresql_using='hash'),)
    pgv = relationship('PGV', backref='court_schedule')

    id = Column(Integer, primary_key=True)
    event_type = Column(String, enum=True)
    event_date = Column(Date)
    _event_date_str = Column('event_date_str', String)
    time = Column(Time)
    _time_str = Column('time_str', String)
    result = Column(String)
    result_date = Column(Date)
    _result_date_str = Column('result_date_str', String)

    @hybrid_property
    def event_date_str(self):
        return self._event_date_str
    @event_date_str.setter
    def event_date_str(self,val):
        self.event_date = date_from_str(val)
        self._event_date_str = val

    @hybrid_property
    def time_str(self):
        return self._time_str
    @time_str.setter
    def time_str(self,val):
        try:
            self.time = datetime.strptime(val,'%H:%M:%S').time()
        except:
            pass
        self._time_str = val
    
    @hybrid_property
    def result_date_str(self):
        return self._result_date_str
    @result_date_str.setter
    def result_date_str(self,val):
        self.result_date = date_from_str(val)
        self._result_date_str = val

class PGVDocket(PGVCaseTable, TableBase):
    __tablename__ = 'pgv_dockets'
    __table_args__ = (Index('ixh_pgv_dockets_case_number', 'case_number', postgresql_using='hash'),)
    pgv = relationship('PGV', backref='dockets')

    id = Column(Integer, primary_key=True)
    date = Column(Date)
    _date_str = Column('date_str', String)
    document_name = Column(String)
    docket_text = Column(String)

    @hybrid_property
    def date_str(self):
        return self._date_str
    @date_str.setter
    def date_str(self,val):
        self.date = date_from_str(val)
        self._date_str = val