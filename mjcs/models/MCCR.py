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

class MCCRTrackingNumber(MCCRCaseTable, TableBase):
    __tablename__ = 'mccr_tracking_numbers'
    __table_args__ = (Index('ixh_mccr_tracking_numbers_case_number', 'case_number', postgresql_using='hash'),)
    mccr = relationship('MCCR', backref='tracking_numbers')

    id = Column(Integer, primary_key=True)
    tracking_number = Column(String)

class MCCRDistrictCourtNumber(MCCRCaseTable, TableBase):
    __tablename__ = 'mccr_district_court_numbers'
    __table_args__ = (Index('ixh_mccr_district_court_numbers_case_number', 'case_number', postgresql_using='hash'),)
    mccr = relationship('MCCR', backref='district_court_numbers')

    id = Column(Integer, primary_key=True)
    district_court_number = Column(String)

class MCCRCharge(MCCRCaseTable, TableBase):
    __tablename__ = 'mccr_charges'
    __table_args__ = (Index('ixh_mccr_charges_case_number', 'case_number', postgresql_using='hash'),)
    mccr = relationship('MCCR', backref='charges')

    id = Column(Integer, primary_key=True)
    charge_number = Column(String)
    expunged = Column(Boolean, nullable=False, server_default='false')
    article_section_subsection = Column(String)
    charge_description = Column(String)
    citation_number = Column(String)
    plea = Column(String, enum=True)
    disposition_text = Column(String)
    disposition_date = Column(Date)
    _disposition_date_str = Column('disposition_date_str',String)
    disposition = Column(String)
    judge = Column(String)
    imposed_life_times = Column(String)
    imposed_years = Column(Integer)
    imposed_months = Column(Integer)
    imposed_days = Column(Integer)
    imposed_consecutive = Column(Boolean)
    imposed_concurrent = Column(Boolean)
    time_served_years = Column(Integer)
    time_served_months = Column(Integer)
    time_served_days = Column(Integer)
    time_suspended_all_but = Column(Boolean, nullable=False, server_default='false')
    time_suspended_years = Column(Integer)
    time_suspended_months = Column(Integer)
    time_suspended_days = Column(Integer)
    probation_supervised = Column(Boolean)
    probation_unsupervised = Column(Boolean)
    probation_years = Column(Integer)
    probation_months = Column(Integer)
    probation_days = Column(Integer)

    @hybrid_property
    def disposition_date_str(self):
        return self._disposition_date_str
    @disposition_date_str.setter
    def disposition_date_str(self,val):
        self.disposition_date = date_from_str(val)
        self._disposition_date_str = val

class MCCRJudgment(MCCRCaseTable, TableBase):
    __tablename__ = 'mccr_judgments'
    __table_args__ = (Index('ixh_mccr_judgments_case_number', 'case_number', postgresql_using='hash'),)
    mccr = relationship('MCCR', backref='judgments')

    id = Column(Integer, primary_key=True)
    date = Column(Date)
    _date_str = Column('date_str',String)
    amount = Column(Numeric)
    entered_date = Column(Date)
    _entered_date_str = Column('entered_date_str',String)
    satisfied = Column(Date)
    _satisfied_str = Column('satisfied_str', String)
    vacated_date = Column(Date)
    _vacated_date_str = Column('vacated_date_str',String)
    amended = Column(Date)
    _amended_str = Column('amended_str', String)
    renewed = Column(Date)
    _renewed_str = Column('renewed_str', String)
    debtor = Column(String)
    party_role = Column(String, enum=True)

    @hybrid_property
    def date_str(self):
        return self._date_str
    @date_str.setter
    def date_str(self,val):
        self.date = date_from_str(val)
        self._date_str = val
    
    @hybrid_property
    def entered_date_str(self):
        return self._entered_date_str
    @entered_date_str.setter
    def entered_date_str(self,val):
        self.entered_date = date_from_str(val)
        self._entered_date_str = val
    
    @hybrid_property
    def satisfied_str(self):
        return self._satisfied_str
    @satisfied_str.setter
    def satisfied_str(self,val):
        self.satisfied = date_from_str(val)
        self._satisfied_str = val
    
    @hybrid_property
    def vacated_date_str(self):
        return self._vacated_date_str
    @vacated_date_str.setter
    def vacated_date_str(self,val):
        self.vacated_date = date_from_str(val)
        self._vacated_date_str = val
    
    @hybrid_property
    def amended_str(self):
        return self._amended_str
    @amended_str.setter
    def amended_str(self,val):
        self.amended = date_from_str(val)
        self._amended_str = val
    
    @hybrid_property
    def renewed_str(self):
        return self._renewed_str
    @renewed_str.setter
    def renewed_str(self,val):
        self.renewed = date_from_str(val)
        self._renewed_str = val

class MCCRDefendant(MCCRCaseTable, TableBase):
    __tablename__ = 'mccr_defendants'
    __table_args__ = (Index('ixh_mccr_defendants_case_number', 'case_number', postgresql_using='hash'),)
    mccr = relationship('MCCR', backref='defendants')

    id = Column(Integer, primary_key=True)
    name = Column(String, redacted=True)
    gender = Column(String)
    DOB = Column(Date, redacted=True)
    _DOB_str = Column('DOB_str',String, redacted=True)
    address = Column(String, redacted=True)
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

class MCCRAlias(MCCRCaseTable, TableBase):
    __tablename__ = 'mccr_aliases'
    __table_args__ = (Index('ixh_mccr_aliases_case_number', 'case_number', postgresql_using='hash'),)
    mccr = relationship('MCCR', backref='aliases')

    id = Column(Integer, primary_key=True)
    alias_name = Column(String)
    party = Column(String)

class MCCRAttorney(MCCRCaseTable, TableBase):
    __tablename__ = 'mccr_attorneys'
    __table_args__ = (Index('ixh_mccr_attorneys_case_number', 'case_number', postgresql_using='hash'),)
    mccr = relationship('MCCR', backref='attorneys')

    id = Column(Integer, primary_key=True)
    name = Column(String)
    appearance_date = Column(Date)
    _appearance_date_str = Column('appearance_date_str',String)
    removal_date = Column(Date)
    _removal_date_str = Column('removal_date_str',String)
    address = Column(String)
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

class MCCRProbationOfficer(MCCRCaseTable, TableBase):
    __tablename__ = 'mccr_probation_officers'
    __table_args__ = (Index('ixh_mccr_probation_officers_case_number', 'case_number', postgresql_using='hash'),)
    mccr = relationship('MCCR', backref='probation_officers')

    id = Column(Integer, primary_key=True)
    name = Column(String)
    address = Column(String)
    city = Column(String)
    state = Column(String)
    zip_code = Column(String)

class MCCRDWIMonitor(MCCRCaseTable, TableBase):
    __tablename__ = 'mccr_dwi_monitors'
    __table_args__ = (Index('ixh_mccr_dwi_monitors_case_number', 'case_number', postgresql_using='hash'),)
    mccr = relationship('MCCR', backref='dwi_monitors')

    id = Column(Integer, primary_key=True)
    name = Column(String)
    address = Column(String)
    city = Column(String)
    state = Column(String)
    zip_code = Column(String)

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
            self.event_time = datetime.strptime(val,'%I:%M %p').time()
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
    status = Column(String)
    ruling_judge = Column(String)

    @hybrid_property
    def docket_date_str(self):
        return self._docket_date_str
    @docket_date_str.setter
    def docket_date_str(self,val):
        self.docket_date = date_from_str(val)
        self._docket_date_str = val

class MCCRAudioMedia(MCCRCaseTable, TableBase):
    __tablename__ = 'mccr_audio_media'
    __table_args__ = (Index('ixh_mccr_audio_media_case_number', 'case_number', postgresql_using='hash'),)
    mccr = relationship('MCCR', backref='audio_media')

    id = Column(Integer, primary_key=True)
    audio_media = Column(String)
    audio_start = Column(String)
    audio_stop = Column(String)
    docket_id = Column(Integer, ForeignKey('mccr_dockets.id'))

class MCCRBailBond(MCCRCaseTable, TableBase):
    __tablename__ = 'mccr_bail_bonds'
    __table_args__ = (Index('ixh_mccr_bail_bonds_case_number', 'case_number', postgresql_using='hash'),)
    mccr = relationship('MCCR', backref='bail_bonds')

    id = Column(Integer, primary_key=True)
    number = Column(Integer)
    bond_type = Column(String, enum=True)
    amount = Column(Numeric)
    minimum_percent = Column(Numeric)
    bond_history = Column(String)
    bonding_company = Column(String)
    bonding_company_address = Column(String)
    agent = Column(String)
    agent_address = Column(String)

class MCCRBondRemitter(MCCRCaseTable, TableBase):
    __tablename__ = 'mccr_bond_remitters'
    __table_args__ = (Index('ixh_mccr_bond_remitters_case_number', 'case_number', postgresql_using='hash'),)
    mccr = relationship('MCCR', backref='bond_remitters')

    id = Column(Integer, primary_key=True)
    remitter = Column(String)