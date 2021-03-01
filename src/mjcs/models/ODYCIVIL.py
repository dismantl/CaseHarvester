from .common import TableBase, CaseTable, Trial, Event, date_from_str, Defendant, DefendantAlias, RelatedPerson
from sqlalchemy import Column, Date, Numeric, Integer, String, Boolean, ForeignKey, Time, BigInteger, Index
from sqlalchemy.orm import relationship, backref
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.ext.declarative import declared_attr
from datetime import datetime

class ODYCIVIL(CaseTable, TableBase):
    __tablename__ = 'odycivil'

    id = Column(Integer, primary_key=True)
    court_system = Column(String)
    location = Column(String)
    case_title = Column(String)
    case_type = Column(String, nullable=True)
    filing_date = Column(Date, nullable=True)
    _filing_date_str = Column('filing_date_str',String, nullable=True)
    case_status = Column(String, nullable=True)

    case = relationship('Case', backref=backref('odycivil', uselist=False))

    __table_args__ = (Index('ixh_odycivil_case_number', 'case_number', postgresql_using='hash'),)

    @hybrid_property
    def filing_date_str(self):
        return self._filing_date_str
    @filing_date_str.setter
    def filing_date_str(self,val):
        self.filing_date = date_from_str(val)
        self._filing_date_str = val

class ODYCIVILCaseTable(CaseTable):
    @declared_attr
    def case_number(self):
        return Column(String, ForeignKey('odycivil.case_number', ondelete='CASCADE'))

class ODYCIVILReferenceNumber(ODYCIVILCaseTable, TableBase):
    __tablename__ = 'odycivil_reference_numbers'
    __table_args__ = (Index('ixh_odycivil_reference_numbers_case_number', 'case_number', postgresql_using='hash'),)
    odycivil = relationship('ODYCIVIL', backref='reference_numbers')

    id = Column(Integer, primary_key=True)
    ref_num = Column(String, nullable=False)
    ref_num_type = Column(String, nullable=False)

class ODYCIVILCause(ODYCIVILCaseTable, TableBase):
    __tablename__ = 'odycivil_causes'
    __table_args__ = (Index('ixh_odycivil_causes_case_number', 'case_number', postgresql_using='hash'),)
    odycivil = relationship('ODYCIVIL', backref='causes')

    id = Column(Integer, primary_key=True)
    file_date = Column(Date)
    _file_date_str = Column('file_date_str', String)
    cause_description = Column(String)
    filed_by = Column(String)
    filed_against = Column(String)

    @hybrid_property
    def file_date_str(self):
        return self._file_date_str
    @file_date_str.setter
    def file_date_str(self,val):
        self.file_date = date_from_str(val)
        self._file_date_str = val

class ODYCIVILCauseRemedy(ODYCIVILCaseTable, TableBase):
    __tablename__ = 'odycivil_cause_remedies'
    __table_args__ = (Index('ixh_odycivil_cause_remedies_case_number', 'case_number', postgresql_using='hash'),)

    id = Column(Integer, primary_key=True)
    remedy_type = Column(String)
    amount = Column(Numeric)
    comment = Column(String)
    cause_id = Column(Integer, ForeignKey('odycivil_causes.id'))

class ODYCIVILDefendant(ODYCIVILCaseTable, Defendant, TableBase):
    __tablename__ = 'odycivil_defendants'
    __table_args__ = (Index('ixh_odycivil_defendants_case_number', 'case_number', postgresql_using='hash'),)
    odycivil = relationship('ODYCIVIL', backref='defendants')

    aliases = relationship('ODYCIVILAlias')
    attorneys = relationship('ODYCIVILAttorney')

class ODYCIVILInvolvedParty(ODYCIVILCaseTable, TableBase):
    __tablename__ = 'odycivil_involved_parties'
    __table_args__ = (Index('ixh_odycivil_involved_parties_case_number', 'case_number', postgresql_using='hash'),)
    odycivil = relationship('ODYCIVIL', backref='involved_parties')

    id = Column(Integer, primary_key=True)
    party_type = Column(String, nullable=False)
    name = Column(String, nullable=False)
    address_1 = Column(String, nullable=True)
    address_2 = Column(String, nullable=True)
    city = Column(String, nullable=True)
    state = Column(String, nullable=True)
    zip_code = Column(String, nullable=True)
    aliases = relationship('ODYCIVILAlias')
    attorneys = relationship('ODYCIVILAttorney')

class ODYCIVILAlias(ODYCIVILCaseTable, TableBase):
    __tablename__ = 'odycivil_aliases'
    __table_args__ = (Index('ixh_odycivil_aliases_case_number', 'case_number', postgresql_using='hash'),)

    id = Column(Integer, primary_key=True)
    alias = Column(String, nullable=False)
    alias_type = Column(String, nullable=False)
    defendant_id = Column(Integer, ForeignKey('odycivil_defendants.id'),nullable=True)
    party_id = Column(Integer, ForeignKey('odycivil_involved_parties.id'),nullable=True)

class ODYCIVILAttorney(ODYCIVILCaseTable, TableBase):
    __tablename__ = 'odycivil_attorneys'
    __table_args__ = (Index('ixh_odycivil_attorneys_case_number', 'case_number', postgresql_using='hash'),)

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
    defendant_id = Column(Integer, ForeignKey('odycivil_defendants.id'),nullable=True)
    party_id = Column(Integer, ForeignKey('odycivil_involved_parties.id'),nullable=True)

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

class ODYCIVILJudgment(ODYCIVILCaseTable, TableBase):
    __tablename__ = 'odycivil_judgments'
    __table_args__ = (Index('ixh_odycivil_judgment_case_number', 'case_number', postgresql_using='hash'),)
    odycivil = relationship('ODYCIVIL', backref='judgments')

    id = Column(Integer, primary_key=True)
    judgment_type = Column(String)  # Monetary, ...
    judgment_description = Column(String)  # Original, Modified, ...
    judgment_event_type = Column(String)
    judgment_against = Column(String)
    judgment_in_favor_of = Column(String)
    judgment_ordered_date = Column(Date)
    _judgment_ordered_date_str = Column('judgment_ordered_date_str',String)
    judgment_entry_date = Column(Date)
    _judgment_entry_date_str = Column('judgment_entry_date_str',String)
    postjudgment_interest = Column(String)
    principal_amount = Column(Numeric)
    prejudgment_interest = Column(Numeric)
    other_fee = Column(Numeric)
    service_fee = Column(Numeric)
    appearance_fee = Column(Numeric)
    witness_fee = Column(Numeric)
    filing_fee = Column(Numeric)
    attorney_fee = Column(Numeric)
    amount_of_judgment = Column(Numeric)
    total_indexed_judgment = Column(Numeric)
    comment = Column(String)
    awarded_to = Column(String)
    property_value = Column(Numeric)
    damages = Column(Numeric)
    property_description = Column(String)
    replivin_or_detinue = Column(String)
    r_d_amount = Column(Numeric)

    @hybrid_property
    def judgment_ordered_date_str(self):
        return self._judgment_ordered_date_str
    @judgment_ordered_date_str.setter
    def judgment_ordered_date_str(self,val):
        self.judgment_ordered_date = date_from_str(val)
        self._judgment_ordered_date_str = val

    @hybrid_property
    def judgment_entry_date_str(self):
        return self._judgment_entry_date_str
    @judgment_entry_date_str.setter
    def judgment_entry_date_str(self,val):
        self.judgment_entry_date = date_from_str(val)
        self._judgment_entry_date_str = val

class ODYCIVILJudgmentStatus(ODYCIVILCaseTable, TableBase):
    __tablename__ = 'odycivil_judgment_statuses'
    __table_args__ = (Index('ixh_odycivil_judgment_status_case_number', 'case_number', postgresql_using='hash'),)

    id = Column(Integer, primary_key=True)
    judgment_status = Column(String, nullable=False)
    judgment_date = Column(Date,nullable=True)
    _judgment_date_str = Column('judgment_date_str',String)
    judgment_id = Column(Integer, ForeignKey('odycivil_judgments.id'))

    @hybrid_property
    def judgment_date_str(self):
        return self._judgment_date_str
    @judgment_date_str.setter
    def judgment_date_str(self,val):
        self.judgment_date = date_from_str(val)
        self._judgment_date_str = val

class ODYCIVILJudgmentComment(ODYCIVILCaseTable, TableBase):
    __tablename__ = 'odycivil_judgment_comments'
    __table_args__ = (Index('ixh_odycivil_judgment_comments_case_number', 'case_number', postgresql_using='hash'),)
    odycivil = relationship('ODYCIVIL', backref='judgment_comments')

    id = Column(Integer, primary_key=True)
    amount = Column(Numeric)
    interest = Column(Numeric)
    atty_fee = Column(Numeric)
    judg_cost = Column(Numeric)
    other_amount = Column(Numeric)
    poss_of_prop = Column(Numeric)
    damanges_pop = Column(Numeric)
    value_of_prop = Column(Numeric)
    damgs_val_of_prop = Column(Numeric)
    repl_detn_amnt = Column(Numeric)
    judg_type = Column(String)
    judg_district = Column(String)
    judg_location = Column(String)
    judg_date = Column(Date)
    _judg_date_str = Column('judg_date_str',String)
    date_entered = Column(Date)
    _date_entered_str = Column('date_entered_str',String)

    @hybrid_property
    def judg_date_str(self):
        return self._judg_date_str
    @judg_date_str.setter
    def judg_date_str(self,val):
        self.judg_date = date_from_str(val)
        self._judg_date_str = val

    @hybrid_property
    def date_entered_str(self):
        return self._date_entered_str
    @date_entered_str.setter
    def date_entered_str(self,val):
        self.date_entered = date_from_str(val)
        self._date_entered_str = val    

class ODYCIVILCourtSchedule(ODYCIVILCaseTable, TableBase):
    __tablename__ = 'odycivil_court_schedule'
    __table_args__ = (Index('ixh_odycivil_court_schedule_case_number', 'case_number', postgresql_using='hash'),)
    odycivil = relationship('ODYCIVIL', backref='court_schedules')

    id = Column(Integer, primary_key=True)
    event_type = Column(String, nullable=False)
    date = Column(Date, nullable=True)
    _date_str = Column('date_str', String, nullable=True)
    time = Column(Time, nullable=True)
    _time_str = Column('time_str', String, nullable=True)
    location = Column(String, nullable=True)
    room = Column(String, nullable=True)
    result = Column(String,nullable=True)

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

class ODYCIVILWarrant(ODYCIVILCaseTable, TableBase):
    __tablename__ = 'odycivil_warrants'
    __table_args__ = (Index('ixh_odycivil_warrants_case_number', 'case_number', postgresql_using='hash'),)
    odycivil = relationship('ODYCIVIL', backref='warrants')

    id = Column(Integer, primary_key=True)
    warrant_type = Column(String)
    issue_date = Column(Date)
    _issue_date_str = Column('issue_date_str', String, nullable=True)
    last_status = Column(String)
    status_date = Column(Date)
    _status_date_str = Column('status_date_str', String, nullable=True)

    @hybrid_property
    def issue_date_str(self):
        return self._issue_date_str
    @issue_date_str.setter
    def issue_date_str(self,val):
        self.date = date_from_str(val)
        self._issue_date_str = val
    
    @hybrid_property
    def status_date_str(self):
        return self._status_date_str
    @status_date_str.setter
    def status_date_str(self,val):
        self.date = date_from_str(val)
        self._status_date_str = val

class ODYCIVILBondSetting(ODYCIVILCaseTable, TableBase):
    __tablename__ = 'odycivil_bond_settings'
    __table_args__ = (Index('ixh_odycivil_bond_settings_case_number', 'case_number', postgresql_using='hash'),)

    id = Column(Integer, primary_key=True)
    bail_date = Column(Date)
    _bail_date_str = Column('bail_date_str', String)
    bail_setting_type = Column(String)
    bail_amount = Column(Numeric)

class ODYCIVILBailBond(ODYCIVILCaseTable, TableBase):
    __tablename__ = 'odycivil_bail_bonds'
    __table_args__ = (Index('ixh_odycivil_bail_bonds_case_number', 'case_number', postgresql_using='hash'),)

    id = Column(Integer, primary_key=True)
    bond_type = Column(String)
    bond_amount_set = Column(Numeric)
    bond_status_date = Column(Date)
    _bond_status_date_str = Column('bond_status_date_str', String)
    bond_status = Column(String)

class ODYCIVILDocument(ODYCIVILCaseTable, TableBase):
    __tablename__ = 'odycivil_documents'
    __table_args__ = (Index('ixh_odycivil_documents_case_number', 'case_number', postgresql_using='hash'),)
    odycivil = relationship('ODYCIVIL', backref='documents')

    id = Column(Integer, primary_key=True)
    file_date = Column(Date,nullable=True)
    _file_date_str = Column('file_date_str',String,nullable=True)
    filed_by = Column(String,nullable=True)
    document_name = Column(String,nullable=False)
    comment = Column(String)

    @hybrid_property
    def file_date_str(self):
        return self._file_date_str
    @file_date_str.setter
    def file_date_str(self,val):
        self.file_date = date_from_str(val)
        self._file_date_str = val

class ODYCIVILService(ODYCIVILCaseTable, TableBase):
    __tablename__ = 'odycivil_services'
    __table_args__ = (Index('ixh_odycivil_services_case_number', 'case_number', postgresql_using='hash'),)
    odycivil = relationship('ODYCIVIL', backref='services')

    id = Column(Integer, primary_key=True)
    service_type = Column(String, nullable=False)
    issued_date = Column(Date,nullable=True)
    _issued_date_str = Column('issued_date_str',String,nullable=True)
    service_status = Column(String,nullable=True)

    @hybrid_property
    def issued_date_str(self):
        return self._issued_date_str
    @issued_date_str.setter
    def issued_date_str(self,val):
        self.issued_date = date_from_str(val)
        self._issued_date_str = val
