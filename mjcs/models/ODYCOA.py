from .common import TableBase, MetaColumn as Column, CaseTable, date_from_str
from sqlalchemy import Date, Integer, String, ForeignKey, Time, Index
from sqlalchemy.orm import relationship, backref
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.ext.declarative import declared_attr
from datetime import datetime

class ODYCOA(CaseTable, TableBase):
    '''MDEC Supreme Court of Maryland Cases'''
    __tablename__ = 'odycoa'
    is_root = True

    id = Column(Integer, primary_key=True)
    court_system = Column(String, enum=True)
    case_title = Column(String)
    case_type = Column(String, enum=True)
    filing_date = Column(Date)
    _filing_date_str = Column('filing_date_str',String)
    case_status = Column(String, enum=True)
    tracking_numbers = Column(String)
    authoring_judge = Column(String)

    case = relationship('Case', backref=backref('odycoa', uselist=False))

    __table_args__ = (Index('ixh_odycoa_case_number', 'case_number', postgresql_using='hash'),)

    @hybrid_property
    def filing_date_str(self):
        return self._filing_date_str
    @filing_date_str.setter
    def filing_date_str(self,val):
        self.filing_date = date_from_str(val)
        self._filing_date_str = val

class ODYCOACaseTable(CaseTable):
    @declared_attr
    def case_number(self):
        return Column(String, ForeignKey('odycoa.case_number', ondelete='CASCADE'), nullable=False)

class ODYCOAReferenceNumber(ODYCOACaseTable, TableBase):
    __tablename__ = 'odycoa_reference_numbers'
    __table_args__ = (Index('ixh_odycoa_reference_numbers_case_number', 'case_number', postgresql_using='hash'),)
    odycoa = relationship('ODYCOA', backref='reference_numbers')

    id = Column(Integer, primary_key=True)
    ref_num = Column(String, nullable=False)
    ref_num_type = Column(String, nullable=False, enum=True)

class ODYCOAInvolvedParty(ODYCOACaseTable, TableBase):
    __tablename__ = 'odycoa_involved_parties'
    __table_args__ = (Index('ixh_odycoa_involved_parties_case_number', 'case_number', postgresql_using='hash'),)
    odycoa = relationship('ODYCOA', backref='involved_parties')

    id = Column(Integer, primary_key=True)
    party_type = Column(String, nullable=False, enum=True)
    name = Column(String, nullable=False)
    race = Column(String, enum=True)
    sex = Column(String)
    height = Column(String)
    weight = Column(Integer)
    hair_color = Column(String)
    eye_color = Column(String)
    DOB = Column(Date)
    _DOB_str = Column('DOB_str',String)
    address_1 = Column(String)
    address_2 = Column(String)
    city = Column(String)
    state = Column(String)
    zip_code = Column(String)
    attorneys = relationship('ODYCOAAttorney')

    @hybrid_property
    def DOB_str(self):
        return self._DOB_str
    @DOB_str.setter
    def DOB_str(self,val):
        self.DOB = date_from_str(val)
        self._DOB_str = val

class ODYCOAAttorney(ODYCOACaseTable, TableBase):
    __tablename__ = 'odycoa_attorneys'
    __table_args__ = (Index('ixh_odycoa_attorneys_case_number', 'case_number', postgresql_using='hash'),)
    odycoa = relationship('ODYCOA', backref='attorneys')

    id = Column(Integer, primary_key=True)
    name = Column(String)
    appearance_date = Column(Date)
    _appearance_date_str = Column('appearance_date_str', String)
    removal_date = Column(Date)
    _removal_date_str = Column('removal_date_str', String)
    address_1 = Column(String)
    address_2 = Column(String)
    address_3 = Column(String)
    city = Column(String)
    state = Column(String)
    zip_code = Column(String)
    party_id = Column(Integer, ForeignKey('odycoa_involved_parties.id'))

    @hybrid_property
    def appearance_date_str(self):
        return self._appearance_date_str
    @appearance_date_str.setter
    def appearance_date_str(self,val):
        self.appearance_date = date_from_str(val)
        self._appearance_date_str = val

    @hybrid_property
    def removal_date_str(self):
        return self._removal_date_str
    @removal_date_str.setter
    def removal_date_str(self,val):
        self.removal_date = date_from_str(val)
        self._removal_date_str = val

class ODYCOAJudgment(ODYCOACaseTable, TableBase):
    __tablename__ = 'odycoa_judgments'
    __table_args__ = (Index('ixh_odycoa_judgment_case_number', 'case_number', postgresql_using='hash'),)
    odycoa = relationship('ODYCOA', backref='judgments')

    id = Column(Integer, primary_key=True)
    judgment_event_type = Column(String, enum=True)
    judge_name = Column(String)
    issue_date = Column(Date)
    _issue_date_str = Column('issue_date_str', String)
    comment = Column(String)

    @hybrid_property
    def issue_date_str(self):
        return self._issue_date_str
    @issue_date_str.setter
    def issue_date_str(self,val):
        self.issue_date = date_from_str(val)
        self._issue_date_str = val

class ODYCOACourtSchedule(ODYCOACaseTable, TableBase):
    __tablename__ = 'odycoa_court_schedule'
    __table_args__ = (Index('ixh_odycoa_court_schedule_case_number', 'case_number', postgresql_using='hash'),)
    odycoa = relationship('ODYCOA', backref='court_schedule')

    id = Column(Integer, primary_key=True)
    event_type = Column(String, nullable=False, enum=True)
    date = Column(Date)
    _date_str = Column('date_str', String)
    time = Column(Time)
    _time_str = Column('time_str', String)
    result = Column(String)
    panel_judges = Column(String)

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
            self.time = datetime.strptime(val,'%H:%M:%S').time()
        except:
            pass
        self._time_str = val

class ODYCOADocument(ODYCOACaseTable, TableBase):
    __tablename__ = 'odycoa_documents'
    __table_args__ = (Index('ixh_odycoa_documents_case_number', 'case_number', postgresql_using='hash'),)
    odycoa = relationship('ODYCOA', backref='documents')

    id = Column(Integer, primary_key=True)
    file_date = Column(Date)
    _file_date_str = Column('file_date_str',String)
    document_name = Column(String,nullable=False)

    @hybrid_property
    def file_date_str(self):
        return self._file_date_str
    @file_date_str.setter
    def file_date_str(self,val):
        self.file_date = date_from_str(val)
        self._file_date_str = val