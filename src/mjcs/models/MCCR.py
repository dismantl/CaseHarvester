from sqlalchemy.sql.schema import Table
from .common import TableBase, MetaColumn as Column, CaseTable, date_from_str
from sqlalchemy import Date, Numeric, Integer, String, Boolean, ForeignKey, Index, Time
from sqlalchemy.orm import relationship, backref
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.ext.declarative import declared_attr
from datetime import datetime

class MCCR(CaseTable, TableBase):
    '''Montgomery County Criminal Cases'''
    __tablename__ = 'mccr'
    is_root = True

    id = Column(Integer, primary_key=True)
    court_system = Column(String, enum=True)
    sub_type = Column(String, enum=True)
    tracking_number = Column(String)
    district_court_number = Column(String)
    filing_date = Column(Date)
    _filing_date_str = Column('filing_date_str',String)
    case_status = Column(String, enum=True)

    case = relationship('Case', backref=backref('mccr', uselist=False))

    __table_args__ = (Index('ixh_mccr_case_number', 'case_number', postgresql_using='hash'),)

    @hybrid_property
    def filing_date_str(self):
        return self._filing_date_str
    @filing_date_str.setter
    def filing_date_str(self,val):
        self.filing_date = date_from_str(val)
        self._filing_date_str = val

class MCCRCaseTable(CaseTable):
    @declared_attr
    def case_number(self):
        return Column(String, ForeignKey('mccr.case_number', ondelete='CASCADE'), nullable=False)

class MCCRCharge(MCCRCaseTable, TableBase):
    __tablename__ = 'mccr_charges'
    __table_args__ = (Index('ixh_mccr_charges_case_number', 'case_number', postgresql_using='hash'),)
    mccr = relationship('MCCR', backref='charges')

    id = Column(Integer, primary_key=True)
    charge_number = Column(Integer)
    expunged = Column(Boolean, nullable=False, server_default='false')
    article_section_subsection = Column(String)
    charge_description = Column(String)
    citation_number = Column(String)
    plea = Column(String, enum=True)
    disposition_text = Column(String)
    disposition_date = Column(Date)
    _disposition_date_str = Column('disposition_date_str',String)
    judge = Column(String)
    imposed_life_times = Column(String)
    imposed_years = Column(Integer)
    imposed_months = Column(Integer)
    imposed_days = Column(Integer)
    imposed_consecutive = Column(Boolean, nullable=False, server_default='false')
    time_served_years = Column(Integer)
    time_served_months = Column(Integer)
    time_served_days = Column(Integer)

    @hybrid_property
    def disposition_date_str(self):
        return self._disposition_date_str
    @disposition_date_str.setter
    def disposition_date_str(self,val):
        self.disposition_date = date_from_str(val)
        self._disposition_date_str = val

# class MCCRPlaintiff(MCCRCaseTable, TableBase):
#     __tablename__ = 'mccr_plaintiffs'
#     __table_args__ = (Index('ixh_mccr_plaintiffs_case_number', 'case_number', postgresql_using='hash'),)
#     mccr = relationship('MCCR', backref='plaintiffs')

#     id = Column(Integer, primary_key=True)
#     party_number = Column(Integer)
#     name = Column(String)
#     address_1 = Column(String)
#     address_2 = Column(String)
#     city = Column(String)
#     state = Column(String)
#     zip_code = Column(String)

class MCCRDefendant(MCCRCaseTable, TableBase):
    __tablename__ = 'mccr_defendants'
    __table_args__ = (Index('ixh_mccr_defendants_case_number', 'case_number', postgresql_using='hash'),)
    mccr = relationship('MCCR', backref='defendants')

    id = Column(Integer, primary_key=True)
    name = Column(String, redacted=True)
    gender = Column(String)
    DOB = Column(Date, nullable=True, redacted=True)
    _DOB_str = Column('DOB_str',String, nullable=True, redacted=True)
    address_1 = Column(String, redacted=True)
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

# class MCCRDefendantAlias(MCCRCaseTable, TableBase):
#     __tablename__ = 'mccr_defendant_aliases'
#     __table_args__ = (Index('ixh_mccr_defendant_aliases_case_number', 'case_number', postgresql_using='hash'),)
#     mccr = relationship('MCCR', backref='defendant_aliases')

#     id = Column(Integer, primary_key=True)
#     alias_name = Column(String)

class MCCRAttorney(MCCRCaseTable, TableBase):
    __tablename__ = 'mccr_attorneys'
    __table_args__ = (Index('ixh_mccr_attorneys_case_number', 'case_number', postgresql_using='hash'),)
    mccr = relationship('MCCR', backref='attorneys')

    id = Column(Integer, primary_key=True)
    name = Column(String)
    appearance_date = Column(Date,nullable=True)
    _appearance_date_str = Column('appearance_date_str',String,nullable=True)
    removal_date = Column(Date,nullable=True)
    _removal_date_str = Column('removal_date_str',String,nullable=True)
    address_1 = Column(String)
    address_2 = Column(String)
    address_3 = Column(String)
    city = Column(String)
    state = Column(String)
    zip_code = Column(String)
    phone = Column(String)

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

# class MCCROtherParty(MCCRCaseTable, TableBase):
#     __tablename__ = 'mccr_other_parties'
#     __table_args__ = (Index('ixh_mccr_other_parties_case_number', 'case_number', postgresql_using='hash'),)
#     mccr = relationship('MCCR', backref='other_parties')

#     id = Column(Integer, primary_key=True)
#     party_type = Column(String, enum=True)
#     party_number = Column(Integer)
#     name = Column(String)

class MCCRCourtSchedule(MCCRCaseTable, TableBase):
    __tablename__ = 'mccr_court_schedule'
    __table_args__ = (Index('ixh_mccr_court_schedule_case_number', 'case_number', postgresql_using='hash'),)
    mccr = relationship('MCCR', backref='court_schedule')

    id = Column(Integer, primary_key=True)
    event_date = Column(Date)
    _event_date_str = Column('event_date_str', String)
    event_time = Column(Time)
    _event_time_str = Column('event_time_str', String)
    judge = Column(String)
    location = Column(String)
    courtroom = Column(String)
    description = Column(String)

    @hybrid_property
    def event_date_str(self):
        return self._event_date_str
    @event_date_str.setter
    def event_date_str(self,val):
        self.event_date = date_from_str(val)
        self._event_date_str = val

    @hybrid_property
    def event_time_str(self):
        return self._event_time_str
    @event_time_str.setter
    def event_time_str(self,val):
        try:
            self.event_time = datetime.strptime(val,'%H:%M:%S').time()
        except:
            pass
        self._event_time_str = val

class MCCRDocket(MCCRCaseTable, TableBase):
    __tablename__ = 'mccr_dockets'
    __table_args__ = (Index('ixh_mccr_dockets_case_number', 'case_number', postgresql_using='hash'),)
    mccr = relationship('MCCR', backref='dockets')

    id = Column(Integer, primary_key=True)
    docket_date = Column(Date)
    _docket_date_str = Column('docket_date_str', String)
    docket_number = Column(Integer)
    docket_description = Column(String)
    docket_type = Column(String)
    filed_by = Column(String)
    docket_text = Column(String)

    @hybrid_property
    def docket_date_str(self):
        return self._docket_date_str
    @docket_date_str.setter
    def docket_date_str(self,val):
        self.docket_date = date_from_str(val)
        self._docket_date_str = val