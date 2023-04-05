from .common import TableBase, MetaColumn as Column, CaseTable, date_from_str
from sqlalchemy import Date, Numeric, Integer, String, Boolean, ForeignKey, Time, Index
from sqlalchemy.orm import relationship, backref
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.ext.declarative import declared_attr
from datetime import datetime

class ODYCVCIT(CaseTable, TableBase):
    '''MDEC Civil Citations'''
    __tablename__ = 'odycvcit'
    is_root = True

    id = Column(Integer, primary_key=True)
    court_system = Column(String, enum=True)
    location = Column(String, enum=True)
    case_title = Column(String)
    case_type = Column(String, enum=True)
    filing_date = Column(Date)
    _filing_date_str = Column('filing_date_str',String)
    case_status = Column(String, enum=True)
    tracking_numbers = Column(String)

    case = relationship('Case', backref=backref('odycvcit', uselist=False))

    __table_args__ = (Index('ixh_odycvcit_case_number', 'case_number', postgresql_using='hash'),)

    @hybrid_property
    def filing_date_str(self):
        return self._filing_date_str
    @filing_date_str.setter
    def filing_date_str(self,val):
        self.filing_date = date_from_str(val)
        self._filing_date_str = val

class ODYCVCITCaseTable(CaseTable):
    @declared_attr
    def case_number(self):
        return Column(String, ForeignKey('odycvcit.case_number', ondelete='CASCADE'), nullable=False)

class ODYCVCITReferenceNumber(ODYCVCITCaseTable, TableBase):
    __tablename__ = 'odycvcit_reference_numbers'
    __table_args__ = (Index('ixh_odycvcit_reference_numbers_case_number', 'case_number', postgresql_using='hash'),)
    odycvcit = relationship('ODYCVCIT', backref='reference_numbers')

    id = Column(Integer, primary_key=True)
    ref_num = Column(String, nullable=False)
    ref_num_type = Column(String, nullable=False, enum=True)

class ODYCVCITDefendant(ODYCVCITCaseTable, TableBase):
    __tablename__ = 'odycvcit_defendants'
    __table_args__ = (Index('ixh_odycvcit_defendants_case_number', 'case_number', postgresql_using='hash'),)
    odycvcit = relationship('ODYCVCIT', backref='defendants')

    id = Column(Integer, primary_key=True)
    name = Column(String, redacted=True)
    race = Column(String, enum=True)
    sex = Column(String)
    height = Column(String)
    weight = Column(Integer)
    hair_color = Column(String)
    eye_color = Column(String)
    DOB = Column(Date, redacted=True)
    _DOB_str = Column('DOB_str',String, redacted=True)
    address_1 = Column(String, redacted=True)
    address_2 = Column(String, redacted=True)
    city = Column(String)
    state = Column(String)
    zip_code = Column(String)
    aliases = relationship('ODYCVCITAlias')
    attorneys = relationship('ODYCVCITAttorney')

    @hybrid_property
    def DOB_str(self):
        return self._DOB_str
    @DOB_str.setter
    def DOB_str(self,val):
        self.DOB = date_from_str(val)
        self._DOB_str = val

class ODYCVCITInvolvedParty(ODYCVCITCaseTable, TableBase):
    __tablename__ = 'odycvcit_involved_parties'
    __table_args__ = (Index('ixh_odycvcit_involved_parties_case_number', 'case_number', postgresql_using='hash'),)
    odycvcit = relationship('ODYCVCIT', backref='involved_parties')

    id = Column(Integer, primary_key=True)
    party_type = Column(String, nullable=False, enum=True)
    name = Column(String, nullable=False)
    agency_name = Column(String)
    address_1 = Column(String)
    address_2 = Column(String)
    city = Column(String)
    state = Column(String)
    zip_code = Column(String)
    aliases = relationship('ODYCVCITAlias')
    attorneys = relationship('ODYCVCITAttorney')

class ODYCVCITAlias(ODYCVCITCaseTable, TableBase):
    __tablename__ = 'odycvcit_aliases'
    __table_args__ = (Index('ixh_odycvcit_aliases_case_number', 'case_number', postgresql_using='hash'),)
    odycvcit = relationship('ODYCVCIT', backref='aliases')

    id = Column(Integer, primary_key=True)
    alias = Column(String, nullable=False)
    alias_type = Column(String, nullable=False, enum=True)
    defendant_id = Column(Integer, ForeignKey('odycvcit_defendants.id'))
    party_id = Column(Integer, ForeignKey('odycvcit_involved_parties.id'))

class ODYCVCITAttorney(ODYCVCITCaseTable, TableBase):
    __tablename__ = 'odycvcit_attorneys'
    __table_args__ = (Index('ixh_odycvcit_attorneys_case_number', 'case_number', postgresql_using='hash'),)
    odycvcit = relationship('ODYCVCIT', backref='attorneys')

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
    defendant_id = Column(Integer, ForeignKey('odycvcit_defendants.id'))
    party_id = Column(Integer, ForeignKey('odycvcit_involved_parties.id'))

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

class ODYCVCITCourtSchedule(ODYCVCITCaseTable, TableBase):
    __tablename__ = 'odycvcit_court_schedule'
    __table_args__ = (Index('ixh_odycvcit_court_schedule_case_number', 'case_number', postgresql_using='hash'),)
    odycvcit = relationship('ODYCVCIT', backref='court_schedule')

    id = Column(Integer, primary_key=True)
    event_type = Column(String, nullable=False, enum=True)
    date = Column(Date)
    _date_str = Column('date_str', String)
    time = Column(Time)
    _time_str = Column('time_str', String)
    location = Column(String, enum=True)
    room = Column(String)
    result = Column(String, enum=True)

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

class ODYCVCITCharge(ODYCVCITCaseTable, TableBase):
    __tablename__ = 'odycvcit_charges'
    __table_args__ = (Index('ixh_odycvcit_charges_case_number', 'case_number', postgresql_using='hash'),)
    odycvcit = relationship('ODYCVCIT', backref='charges')

    id = Column(Integer, primary_key=True)
    charge_number = Column(Integer)
    expunged = Column(Boolean, nullable=False, server_default='false')
    cjis_code = Column(String)
    statute_code = Column(String)
    charge_description = Column(String)
    charge_class = Column(String, enum=True)
    probable_cause = Column(Boolean)
    offense_date_from = Column(Date)
    _offense_date_from_str = Column('offense_date_from_str', String)
    offense_date_to = Column(Date)
    _offense_date_to_str = Column('offense_date_to_str', String)
    agency_name = Column(String)
    officer_id = Column(String)
    plea = Column(String, enum=True)
    plea_date = Column(Date)
    _plea_date_str = Column('plea_date_str', String)
    disposition = Column(String, enum=True)
    disposition_date = Column(Date)
    _disposition_date_str = Column('disposition_date_str', String)
    converted_disposition = Column(String)
    jail_start_date = Column(Date)
    _jail_start_date_str = Column('jail_start_date_str', String)
    jail_years = Column(Integer)
    jail_months = Column(Integer)
    jail_days = Column(Integer)
    jail_hours = Column(Integer)
    jail_suspended_years = Column(Integer)
    jail_suspended_months = Column(Integer)
    jail_suspended_days = Column(Integer)
    jail_suspended_hours = Column(Integer)

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
    def offense_date_from_str(self):
        return self._offense_date_from_str
    @offense_date_from_str.setter
    def offense_date_from_str(self,val):
        self.offense_date_from = date_from_str(val)
        self._offense_date_from_str = val

    @hybrid_property
    def offense_date_to_str(self):
        return self._offense_date_to_str
    @offense_date_to_str.setter
    def offense_date_to_str(self,val):
        self.offense_date_to = date_from_str(val)
        self._offense_date_to_str = val

    @hybrid_property
    def jail_start_date_str(self):
        return self._jail_start_date_str
    @jail_start_date_str.setter
    def jail_start_date_str(self,val):
        self.jail_start_date = date_from_str(val)
        self._jail_start_date_str = val

class ODYCVCITProbation(ODYCVCITCaseTable, TableBase):
    __tablename__ = 'odycvcit_probation'
    __table_args__ = (Index('ixh_odycvcit_probation_case_number', 'case_number', postgresql_using='hash'),)
    odycvcit = relationship('ODYCVCIT', backref='probation')

    id = Column(Integer, primary_key=True)
    probation_start_date = Column(Date)
    _probation_start_date_str = Column('probation_start_date_str', String)
    probation_supervised = Column(Boolean)
    probation_supervised_years = Column(Integer)
    probation_supervised_months = Column(Integer)
    probation_supervised_days = Column(Integer)
    probation_supervised_hours = Column(Integer)
    probation_unsupervised = Column(Boolean)
    probation_unsupervised_years = Column(Integer)
    probation_unsupervised_months = Column(Integer)
    probation_unsupervised_days = Column(Integer)
    probation_unsupervised_hours = Column(Integer)

    @hybrid_property
    def probation_start_date_str(self):
        return self._probation_start_date_str
    @probation_start_date_str.setter
    def probation_start_date_str(self,val):
        self.probation_start_date = date_from_str(val)
        self._probation_start_date_str = val

class ODYCVCITRestitution(ODYCVCITCaseTable, TableBase):
    __tablename__ = 'odycvcit_restitutions'
    __table_args__ = (Index('ixh_odycvcit_restitutions_case_number', 'case_number', postgresql_using='hash'),)
    odycvcit = relationship('ODYCVCIT', backref='restitutions')

    id = Column(Integer, primary_key=True)
    restitution_amount = Column(Numeric)
    restitution_entered_date = Column(Date)
    _restitution_entered_date_str = Column('restitution_entered_date_str', String)
    other_cost_amount = Column(Numeric)

    @hybrid_property
    def restitution_entered_date_str(self):
        return self._restitution_entered_date_str
    @restitution_entered_date_str.setter
    def restitution_entered_date_str(self,val):
        self.restitution_entered_date = date_from_str(val)
        self._restitution_entered_date_str = val

class ODYCVCITWarrant(ODYCVCITCaseTable, TableBase):
    __tablename__ = 'odycvcit_warrants'
    __table_args__ = (Index('ixh_odycvcit_warrants_case_number', 'case_number', postgresql_using='hash'),)
    odycvcit = relationship('ODYCVCIT', backref='warrants')

    id = Column(Integer, primary_key=True)
    warrant_type = Column(String, enum=True)
    issue_date = Column(Date)
    _issue_date_str = Column('issue_date_str', String)
    last_status = Column(String, enum=True)
    status_date = Column(Date)
    _status_date_str = Column('status_date_str', String)

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

class ODYCVCITBailBond(ODYCVCITCaseTable, TableBase):
    __tablename__ = 'odycvcit_bail_bonds'
    __table_args__ = (Index('ixh_odycvcit_bail_bonds_case_number', 'case_number', postgresql_using='hash'),)
    odycvcit = relationship('ODYCVCIT', backref='bail_bonds')

    id = Column(Integer, primary_key=True)
    bond_type = Column(String, enum=True)
    bond_amount_posted = Column(String)
    bond_status_date = Column(Date)
    _bond_status_date_str = Column('bond_status_date_str', String)
    bond_status = Column(String, enum=True)

    @hybrid_property
    def bond_status_date_str(self):
        return self._bond_status_date_str
    @bond_status_date_str.setter
    def bond_status_date_str(self,val):
        self.bond_status_date = date_from_str(val)
        self._bond_status_date_str = val

class ODYCVCITBondSetting(ODYCVCITCaseTable, TableBase):
    __tablename__ = 'odycvcit_bond_settings'
    __table_args__ = (Index('ixh_odycvcit_bond_settings_case_number', 'case_number', postgresql_using='hash'),)
    odycvcit = relationship('ODYCVCIT', backref='bond_settings')

    id = Column(Integer, primary_key=True)
    bail_date = Column(Date)
    _bail_date_str = Column('bail_date_str', String)
    bail_setting_type = Column(String, enum=True)
    bail_amount = Column(Numeric)

    @hybrid_property
    def bail_date_str(self):
        return self._bail_date_str
    @bail_date_str.setter
    def bail_date_str(self,val):
        self.bail_date = date_from_str(val)
        self._bail_date_str = val

class ODYCVCITDocument(ODYCVCITCaseTable, TableBase):
    __tablename__ = 'odycvcit_documents'
    __table_args__ = (Index('ixh_odycvcit_documents_case_number', 'case_number', postgresql_using='hash'),)
    odycvcit = relationship('ODYCVCIT', backref='documents')

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

class ODYCVCITService(ODYCVCITCaseTable, TableBase):
    __tablename__ = 'odycvcit_services'
    __table_args__ = (Index('ixh_odycvcit_services_case_number', 'case_number', postgresql_using='hash'),)
    odycvcit = relationship('ODYCVCIT', backref='services')

    id = Column(Integer, primary_key=True)
    service_type = Column(String, nullable=False, enum=True)
    issued_date = Column(Date)
    _issued_date_str = Column('issued_date_str',String)

    @hybrid_property
    def issued_date_str(self):
        return self._issued_date_str
    @issued_date_str.setter
    def issued_date_str(self,val):
        self.issued_date = date_from_str(val)
        self._issued_date_str = val