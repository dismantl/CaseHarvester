from .common import TableBase, MetaColumn as Column, CaseTable, date_from_str
from sqlalchemy import Date, Numeric, Integer, String, Boolean, ForeignKey, Time, Index
from sqlalchemy.orm import relationship, backref
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.ext.declarative import declared_attr
from datetime import datetime

class ODYTRAF(CaseTable, TableBase):
    '''MDEC Traffic Cases'''
    __tablename__ = 'odytraf'
    is_root = True

    id = Column(Integer, primary_key=True)
    court_system = Column(String, enum=True)
    location = Column(String, enum=True)
    case_title = Column(String)
    case_type = Column(String, nullable=True, enum=True)
    filing_date = Column(Date, nullable=True)
    _filing_date_str = Column('filing_date_str',String, nullable=True)
    violation_date = Column(Date, nullable=True)
    _violation_date_str = Column('violation_date_str',String, nullable=True)
    violation_time = Column(Time, nullable=True)
    _violation_time_str = Column('violation_time_str', String, nullable=True)
    violation_county = Column(String, enum=True)
    case_status = Column(String, nullable=True, enum=True)

    case = relationship('Case', backref=backref('odytraf', uselist=False))

    __table_args__ = (Index('ixh_odytraf_case_number', 'case_number', postgresql_using='hash'),)

    @hybrid_property
    def filing_date_str(self):
        return self._filing_date_str
    @filing_date_str.setter
    def filing_date_str(self,val):
        self.filing_date = date_from_str(val)
        self._filing_date_str = val

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
            self.violation_time = datetime.strptime(val,'%I:%M:%S %p').time()
        except:
            pass
        self._violation_time_str = val

class ODYTRAFCaseTable(CaseTable):
    @declared_attr
    def case_number(self):
        return Column(String, ForeignKey('odytraf.case_number', ondelete='CASCADE'), nullable=False)

class ODYTRAFReferenceNumber(ODYTRAFCaseTable, TableBase):
    __tablename__ = 'odytraf_reference_numbers'
    __table_args__ = (Index('ixh_odytraf_reference_numbers_case_number', 'case_number', postgresql_using='hash'),)
    odytraf = relationship('ODYTRAF', backref='reference_numbers')

    id = Column(Integer, primary_key=True)
    ref_num = Column(String, nullable=False)
    ref_num_type = Column(String, nullable=False, enum=True)

class ODYTRAFDefendant(ODYTRAFCaseTable, TableBase):
    __tablename__ = 'odytraf_defendants'
    __table_args__ = (Index('ixh_odytraf_defendants_case_number', 'case_number', postgresql_using='hash'),)
    odytraf = relationship('ODYTRAF', backref='defendants')

    id = Column(Integer, primary_key=True)
    name = Column(String, redacted=True)
    race = Column(String, nullable=True, enum=True)
    sex = Column(String, nullable=True)
    height = Column(String, nullable=True)
    weight = Column(Integer, nullable=True)
    DOB = Column(Date, nullable=True, redacted=True)
    _DOB_str = Column('DOB_str',String, nullable=True, redacted=True)
    address_1 = Column(String, nullable=True, redacted=True)
    address_2 = Column(String, nullable=True, redacted=True)
    city = Column(String, nullable=True)
    state = Column(String, nullable=True)
    zip_code = Column(String, nullable=True)
    aliases = relationship('ODYTRAFAlias')
    attorneys = relationship('ODYTRAFAttorney')

    @hybrid_property
    def DOB_str(self):
        return self._DOB_str
    @DOB_str.setter
    def DOB_str(self,val):
        self.DOB = date_from_str(val)
        self._DOB_str = val

class ODYTRAFInvolvedParty(ODYTRAFCaseTable, TableBase):
    __tablename__ = 'odytraf_involved_parties'
    __table_args__ = (Index('ixh_odytraf_involved_parties_case_number', 'case_number', postgresql_using='hash'),)
    odytraf = relationship('ODYTRAF', backref='involved_parties')

    id = Column(Integer, primary_key=True)
    party_type = Column(String, nullable=False, enum=True)
    name = Column(String, nullable=False)
    agency_name = Column(String, nullable=True)
    address_1 = Column(String, nullable=True)
    address_2 = Column(String, nullable=True)
    city = Column(String, nullable=True)
    state = Column(String, nullable=True)
    zip_code = Column(String, nullable=True)
    aliases = relationship('ODYTRAFAlias')
    attorneys = relationship('ODYTRAFAttorney')

class ODYTRAFAlias(ODYTRAFCaseTable, TableBase):
    __tablename__ = 'odytraf_aliases'
    __table_args__ = (Index('ixh_odytraf_aliases_case_number', 'case_number', postgresql_using='hash'),)
    odytraf = relationship('ODYTRAF', backref='aliases')

    id = Column(Integer, primary_key=True)
    alias = Column(String, nullable=False)
    alias_type = Column(String, nullable=False, enum=True)
    defendant_id = Column(Integer, ForeignKey('odytraf_defendants.id'),nullable=True)
    party_id = Column(Integer, ForeignKey('odytraf_involved_parties.id'),nullable=True)

class ODYTRAFAttorney(ODYTRAFCaseTable, TableBase):
    __tablename__ = 'odytraf_attorneys'
    __table_args__ = (Index('ixh_odytraf_attorneys_case_number', 'case_number', postgresql_using='hash'),)
    odytraf = relationship('ODYTRAF', backref='attorneys')

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=True)
    appearance_date = Column(Date)
    _appearance_date_str = Column('appearance_date_str', String)
    removal_date = Column(Date)
    _removal_date_str = Column('removal_date_str', String)
    address_1 = Column(String, nullable=True)
    address_2 = Column(String, nullable=True)
    address_3 = Column(String, nullable=True)
    city = Column(String, nullable=True)
    state = Column(String, nullable=True)
    zip_code = Column(String, nullable=True)
    defendant_id = Column(Integer, ForeignKey('odytraf_defendants.id'),nullable=True)
    party_id = Column(Integer, ForeignKey('odytraf_involved_parties.id'),nullable=True)

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

class ODYTRAFCourtSchedule(ODYTRAFCaseTable, TableBase):
    __tablename__ = 'odytraf_court_schedule'
    __table_args__ = (Index('ixh_odytraf_court_schedule_case_number', 'case_number', postgresql_using='hash'),)
    odytraf = relationship('ODYTRAF', backref='court_schedule')

    id = Column(Integer, primary_key=True)
    event_type = Column(String, nullable=False, enum=True)
    date = Column(Date, nullable=True)
    _date_str = Column('date_str', String, nullable=True)
    time = Column(Time, nullable=True)
    _time_str = Column('time_str', String, nullable=True)
    location = Column(String, nullable=True, enum=True)
    room = Column(String, nullable=True)
    result = Column(String,nullable=True, enum=True)

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

class ODYTRAFCharge(ODYTRAFCaseTable, TableBase):
    __tablename__ = 'odytraf_charges'
    __table_args__ = (Index('ixh_odytraf_charges_case_number', 'case_number', postgresql_using='hash'),)
    odytraf = relationship('ODYTRAF', backref='charges')

    id = Column(Integer, primary_key=True)
    charge_number = Column(Integer)
    expunged = Column(Boolean, nullable=False, server_default='false')
    charge_description = Column(String, nullable=True)
    statute_code = Column(String, nullable=True)
    speed_limit = Column(Integer, nullable=True)
    recorded_speed = Column(Integer, nullable=True)
    location_stopped = Column(String)
    probable_cause_indicator = Column(Boolean)
    charge_contributed_to_accident = Column(Boolean)
    charge_personal_injury = Column(Boolean)
    property_damage = Column(Boolean)
    seat_belts = Column(Boolean, nullable=True)
    mandatory_court_appearance = Column(Boolean)
    fine_amount_owed = Column(Numeric)
    vehicle_tag = Column(String)
    state = Column(String)
    vehicle_description = Column(String)
    convicted_speed = Column(Integer)
    disposition_contributed_to_accident = Column(Boolean)
    disposition_personal_injury = Column(Boolean)
    plea = Column(String, enum=True)
    plea_date = Column(Date, nullable=True)
    _plea_date_str = Column('plea_date_str', String, nullable=True)
    disposition = Column(String, enum=True)
    disposition_date = Column(Date, nullable=True)
    _disposition_date_str = Column('disposition_date_str', String, nullable=True)
    converted_disposition = Column(String, nullable=True)
    probation_start_date = Column(Date, nullable=True)
    _probation_start_date_str = Column('probation_start_date_str', String, nullable=True)
    probation_supervised_years = Column(Integer, nullable=True)
    probation_supervised_months = Column(Integer, nullable=True)
    probation_supervised_days = Column(Integer, nullable=True)
    probation_supervised_hours = Column(Integer, nullable=True)
    probation_unsupervised_years = Column(Integer, nullable=True)
    probation_unsupervised_months = Column(Integer, nullable=True)
    probation_unsupervised_days = Column(Integer, nullable=True)
    probation_unsupervised_hours = Column(Integer, nullable=True)
    jail_start_date = Column(Date, nullable=True)
    _jail_start_date_str = Column('jail_start_date_str', String, nullable=True)
    jail_years = Column(Integer, nullable=True)
    jail_months = Column(Integer, nullable=True)
    jail_days = Column(Integer, nullable=True)
    jail_hours = Column(Integer, nullable=True)
    jail_suspended_term = Column(String, nullable=True)
    jail_suspended_years = Column(Integer, nullable=True)
    jail_suspended_months = Column(Integer, nullable=True)
    jail_suspended_days = Column(Integer, nullable=True)
    jail_suspended_hours = Column(Integer, nullable=True)
    jail_suspend_all_but_years = Column(Integer, nullable=True)
    jail_suspend_all_but_months = Column(Integer, nullable=True)
    jail_suspend_all_but_days = Column(Integer, nullable=True)
    jail_suspend_all_but_hours = Column(Integer, nullable=True)

    @hybrid_property
    def plea_date_str(self):
        return self._plea_date_str
    @plea_date_str.setter
    def plea_date_str(self,val):
        self.plea_date = date_from_str(val)
        self._plea_date_str = val

    @hybrid_property
    def disposition_date_str(self):
        return self._disposition_date_str
    @disposition_date_str.setter
    def disposition_date_str(self,val):
        self.disposition_date = date_from_str(val)
        self._disposition_date_str = val

    @hybrid_property
    def probation_start_date_str(self):
        return self._probation_start_date_str
    @probation_start_date_str.setter
    def probation_start_date_str(self,val):
        self.probation_start_date = date_from_str(val)
        self._probation_start_date_str = val

    @hybrid_property
    def jail_start_date_str(self):
        return self._jail_start_date_str
    @jail_start_date_str.setter
    def jail_start_date_str(self,val):
        self.jail_start_date = date_from_str(val)
        self._jail_start_date_str = val

class ODYTRAFWarrant(ODYTRAFCaseTable, TableBase):
    __tablename__ = 'odytraf_warrants'
    __table_args__ = (Index('ixh_odytraf_warrants_case_number', 'case_number', postgresql_using='hash'),)
    odytraf = relationship('ODYTRAF', backref='warrants')

    id = Column(Integer, primary_key=True)
    warrant_type = Column(String, enum=True)
    issue_date = Column(Date, nullable=True)
    _issue_date_str = Column('issue_date_str', String, nullable=True)
    last_status = Column(String, enum=True)
    status_date = Column(Date, nullable=True)
    _status_date_str = Column('status_date_str', String, nullable=True)

    @hybrid_property
    def issue_date_str(self):
        return self._issue_date_str
    @issue_date_str.setter
    def issue_date_str(self,val):
        self.issue_date = date_from_str(val)
        self._issue_date_str = val

    @hybrid_property
    def status_date_str(self):
        return self._status_date_str
    @status_date_str.setter
    def status_date_str(self,val):
        self.status_date = date_from_str(val)
        self._status_date_str = val

class ODYTRAFBailBond(ODYTRAFCaseTable, TableBase):
    __tablename__ = 'odytraf_bail_bonds'
    __table_args__ = (Index('ixh_odytraf_bail_bonds_case_number', 'case_number', postgresql_using='hash'),)
    odytraf = relationship('ODYTRAF', backref='bail_bonds')

    id = Column(Integer, primary_key=True)
    bond_type = Column(String, enum=True)
    bond_amount_set = Column(String)
    bond_status_date = Column(Date, nullable=True)
    _bond_status_date_str = Column('bond_status_date_str', String, nullable=True)
    bond_status = Column(String, enum=True)

    @hybrid_property
    def bond_status_date_str(self):
        return self._bond_status_date_str
    @bond_status_date_str.setter
    def bond_status_date_str(self,val):
        self.bond_status_date = date_from_str(val)
        self._bond_status_date_str = val

class ODYTRAFBondSetting(ODYTRAFCaseTable, TableBase):
    __tablename__ = 'odytraf_bond_settings'
    __table_args__ = (Index('ixh_odytraf_bond_settings_case_number', 'case_number', postgresql_using='hash'),)
    odytraf = relationship('ODYTRAF', backref='bond_settings')

    id = Column(Integer, primary_key=True)
    bail_date = Column(Date, nullable=True)
    _bail_date_str = Column('bail_date_str', String, nullable=True)
    bail_setting_type = Column(String, enum=True)
    bail_amount = Column(Numeric)

    @hybrid_property
    def bail_date_str(self):
        return self._bail_date_str
    @bail_date_str.setter
    def bail_date_str(self,val):
        self.bail_date = date_from_str(val)
        self._bail_date_str = val


class ODYTRAFDocument(ODYTRAFCaseTable, TableBase):
    __tablename__ = 'odytraf_documents'
    __table_args__ = (Index('ixh_odytraf_documents_case_number', 'case_number', postgresql_using='hash'),)
    odytraf = relationship('ODYTRAF', backref='documents')

    id = Column(Integer, primary_key=True)
    file_date = Column(Date,nullable=True)
    _file_date_str = Column('file_date_str',String,nullable=True)
    document_name = Column(String,nullable=True)
    comment = Column(String,nullable=True)

    @hybrid_property
    def file_date_str(self):
        return self._file_date_str
    @file_date_str.setter
    def file_date_str(self,val):
        self.file_date = date_from_str(val)
        self._file_date_str = val

class ODYTRAFService(ODYTRAFCaseTable, TableBase):
    __tablename__ = 'odytraf_services'
    __table_args__ = (Index('ixh_odytraf_services_case_number', 'case_number', postgresql_using='hash'),)
    odytraf = relationship('ODYTRAF', backref='services')

    id = Column(Integer, primary_key=True)
    service_type = Column(String, nullable=False, enum=True)
    requested_by = Column(String, nullable=True)
    issued_date = Column(Date,nullable=True)
    _issued_date_str = Column('issued_date_str',String,nullable=True)

    @hybrid_property
    def issued_date_str(self):
        return self._issued_date_str
    @issued_date_str.setter
    def issued_date_str(self,val):
        self.issued_date = date_from_str(val)
        self._issued_date_str = val
