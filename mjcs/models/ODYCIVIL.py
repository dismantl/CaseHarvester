from .common import TableBase, MetaColumn as Column, CaseTable, date_from_str
from sqlalchemy import Date, Numeric, Integer, String, Boolean, ForeignKey, Time, BigInteger, Index
from sqlalchemy.orm import relationship, backref
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.ext.declarative import declared_attr
from datetime import datetime

class ODYCIVIL(CaseTable, TableBase):
    '''MDEC Civil Cases'''
    __tablename__ = 'odycivil'
    is_root = True

    id = Column(Integer, primary_key=True)
    court_system = Column(String)
    location = Column(String, enum=True)
    case_title = Column(String)
    case_type = Column(String)
    filing_date = Column(Date)
    _filing_date_str = Column('filing_date_str',String)
    case_status = Column(String, enum=True)
    magistrate = Column(String)
    judicial_officer = Column(String)

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
        return Column(String, ForeignKey('odycivil.case_number', ondelete='CASCADE'), nullable=False)

class ODYCIVILReferenceNumber(ODYCIVILCaseTable, TableBase):
    __tablename__ = 'odycivil_reference_numbers'
    __table_args__ = (Index('ixh_odycivil_reference_numbers_case_number', 'case_number', postgresql_using='hash'),)
    odycivil = relationship('ODYCIVIL', backref='reference_numbers')

    id = Column(Integer, primary_key=True)
    ref_num = Column(String, nullable=False)
    ref_num_type = Column(String, nullable=False, enum=True)

class ODYCIVILCause(ODYCIVILCaseTable, TableBase):
    __tablename__ = 'odycivil_causes'
    __table_args__ = (Index('ixh_odycivil_causes_case_number', 'case_number', postgresql_using='hash'),)
    odycivil = relationship('ODYCIVIL', backref='causes')

    id = Column(Integer, primary_key=True)
    file_date = Column(Date)
    _file_date_str = Column('file_date_str', String)
    cause_description = Column(String)
    filed_by = Column(String, enum=True)
    filed_against = Column(String, enum=True)

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
    odycivil_cause = relationship('ODYCIVILCause', backref='cause_remedies')
    odycivil = relationship('ODYCIVIL', backref='cause_remedies')

    id = Column(Integer, primary_key=True)
    remedy_type = Column(String, enum=True)
    amount = Column(Numeric)
    comment = Column(String)
    cause_id = Column(Integer, ForeignKey('odycivil_causes.id'))

class ODYCIVILDefendant(ODYCIVILCaseTable, TableBase):
    __tablename__ = 'odycivil_defendants'
    __table_args__ = (Index('ixh_odycivil_defendants_case_number', 'case_number', postgresql_using='hash'),)
    odycivil = relationship('ODYCIVIL', backref='defendants')

    id = Column(Integer, primary_key=True)
    name = Column(String)
    DOB = Column(Date)
    _DOB_str = Column('DOB_str',String)
    address_1 = Column(String)
    address_2 = Column(String)
    city = Column(String)
    state = Column(String)
    zip_code = Column(String)
    aliases = relationship('ODYCIVILAlias')
    attorneys = relationship('ODYCIVILAttorney')

    @hybrid_property
    def DOB_str(self):
        return self._DOB_str
    @DOB_str.setter
    def DOB_str(self,val):
        self.DOB = date_from_str(val)
        self._DOB_str = val

class ODYCIVILInvolvedParty(ODYCIVILCaseTable, TableBase):
    __tablename__ = 'odycivil_involved_parties'
    __table_args__ = (Index('ixh_odycivil_involved_parties_case_number', 'case_number', postgresql_using='hash'),)
    odycivil = relationship('ODYCIVIL', backref='involved_parties')

    id = Column(Integer, primary_key=True)
    party_type = Column(String, enum=True)
    name = Column(String)
    appearance_date = Column(Date)
    _appearance_date_str = Column('appearance_date_str', String)
    removal_date = Column(Date)
    _removal_date_str = Column('removal_date_str', String)
    DOB = Column(Date)
    _DOB_str = Column('DOB_str',String)
    address_1 = Column(String)
    address_2 = Column(String)
    city = Column(String)
    state = Column(String)
    zip_code = Column(String)
    aliases = relationship('ODYCIVILAlias')
    attorneys = relationship('ODYCIVILAttorney')

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
    
    @hybrid_property
    def DOB_str(self):
        return self._DOB_str
    @DOB_str.setter
    def DOB_str(self,val):
        self.DOB = date_from_str(val)
        self._DOB_str = val

class ODYCIVILAlias(ODYCIVILCaseTable, TableBase):
    __tablename__ = 'odycivil_aliases'
    __table_args__ = (Index('ixh_odycivil_aliases_case_number', 'case_number', postgresql_using='hash'),)
    odycivil = relationship('ODYCIVIL', backref='aliases')

    id = Column(Integer, primary_key=True)
    alias = Column(String, nullable=False)
    alias_type = Column(String, nullable=False, enum=True)
    defendant_id = Column(Integer, ForeignKey('odycivil_defendants.id'))
    party_id = Column(Integer, ForeignKey('odycivil_involved_parties.id'))

class ODYCIVILAttorney(ODYCIVILCaseTable, TableBase):
    __tablename__ = 'odycivil_attorneys'
    __table_args__ = (Index('ixh_odycivil_attorneys_case_number', 'case_number', postgresql_using='hash'),)
    odycivil = relationship('ODYCIVIL', backref='attorneys')

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
    defendant_id = Column(Integer, ForeignKey('odycivil_defendants.id'))
    party_id = Column(Integer, ForeignKey('odycivil_involved_parties.id'))

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
    judgment_type = Column(String, enum=True)  # Monetary, ...
    judgment_description = Column(String, enum=True)  # Original, Modified, ...
    judgment_event_type = Column(String, enum=True)
    judge = Column(String)
    judgment_against = Column(String)
    judgment_in_favor_of = Column(String)
    judgment_for = Column(String)
    judgment_ordered_date = Column(Date)
    _judgment_ordered_date_str = Column('judgment_ordered_date_str',String)
    judgment_entry_date = Column(Date)
    _judgment_entry_date_str = Column('judgment_entry_date_str',String)
    judgment_expiration_date = Column(Date)
    _judgment_expiration_date_str = Column('judgment_expiration_date_str',String)
    judgment_details = Column(String)
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
    party = Column(String)
    possession = Column(Boolean)
    premise_description = Column(String)
    costs = Column(Boolean)
    costs_ = Column(Numeric)
    stay_upon_filing_of_bond = Column(Boolean)
    stay_of_execution_until = Column(Date)
    _stay_of_execution_until_str = Column('stay_of_execution_until_str',String)
    stay_details = Column(String)
    monetary_judgment = Column(Boolean)
    judgment = Column(String)
    appeal_bond_amount = Column(Numeric)
    court_costs = Column(Numeric)
    interest_rate_details = Column(String)
    trial_judgment_against_plaintiff = Column(String)

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
    
    @hybrid_property
    def stay_of_execution_until_str(self):
        return self._stay_of_execution_until_str
    @stay_of_execution_until_str.setter
    def stay_of_execution_until_str(self,val):
        self.stay_of_execution_until = date_from_str(val)
        self._stay_of_execution_until_str = val
    
    @hybrid_property
    def judgment_expiration_date_str(self):
        return self._judgment_expiration_date_str
    @judgment_expiration_date_str.setter
    def judgment_expiration_date_str(self,val):
        self.judgment_expiration_date = date_from_str(val)
        self._judgment_expiration_date_str = val

class ODYCIVILJudgmentStatus(ODYCIVILCaseTable, TableBase):
    __tablename__ = 'odycivil_judgment_statuses'
    __table_args__ = (Index('ixh_odycivil_judgment_status_case_number', 'case_number', postgresql_using='hash'),)
    odycivil_judgment = relationship('ODYCIVILJudgment', backref='judgment_statuses')
    odycivil = relationship('ODYCIVIL', backref='judgment_statuses')

    id = Column(Integer, primary_key=True)
    judgment_status = Column(String, nullable=False, enum=True)
    judgment_date = Column(Date)
    _judgment_date_str = Column('judgment_date_str',String)
    comment = Column(String)
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
    post_interest_rate = Column(String)
    other_amount = Column(Numeric)
    poss_of_prop = Column(Numeric)
    pop_award_to = Column(String)
    damages_pop = Column(Numeric)
    value_of_prop = Column(Numeric)
    val_of_prop_to = Column(String)
    damgs_val_of_prop = Column(Numeric)
    repl_detn_amnt = Column(Numeric)
    judg_type = Column(String, enum=True)
    in_favor_of_def = Column(String)
    judg_district = Column(String)
    judg_location = Column(String)
    judg_date = Column(Date)
    _judg_date_str = Column('judg_date_str',String)
    cc_recorded_date = Column(Date)
    _cc_recorded_date_str = Column('cc_recorded_date_str',String)
    satisfaction_date = Column(Date)
    _satisfaction_date_str = Column('satisfaction_date_str',String)
    sat_date_entered = Column(Date)
    _sat_date_entered_str = Column('sat_date_entered_str',String)
    date_entered = Column(Date)
    _date_entered_str = Column('date_entered_str',String)
    dis_with_prej = Column(String)
    j_and_s_code = Column(String)
    renewed_date = Column(Date)
    _renewed_date_str = Column('renewed_date_str',String)
    renewed_lien_date = Column(Date)
    _renewed_lien_date_str = Column('renewed_lien_date_str',String)
    renewed_date_ent = Column(Date)
    _renewed_date_ent_str = Column('renewed_date_end_str',String)
    amendcorrect = Column(String)
    defreason = Column(String)
    filingfee = Column(Numeric)
    freetext = Column(String)
    postjinterest = Column(Numeric)
    otherfee = Column(Numeric)
    printdate = Column(Date)
    _printdate_str = Column('printdate_str',String)
    totalcosts = Column(Numeric)
    totalinterest = Column(Numeric)
    totaljudg = Column(Numeric)
    totalprincipal = Column(String)
    totdecimalprin = Column(Numeric)
    user = Column(String)
    usercdate = Column(Date)
    _usercdate_str = Column('usercdate_str',String)
    judg_ccjs_ind = Column(String)
    servicefee = Column(Numeric)

    @hybrid_property
    def usercdate_str(self):
        return self._usercdate_str
    @usercdate_str.setter
    def usercdate_str(self,val):
        self.usercdate = date_from_str(val)
        self._usercdate_str = val

    @hybrid_property
    def judg_date_str(self):
        return self._judg_date_str
    @judg_date_str.setter
    def judg_date_str(self,val):
        self.judg_date = date_from_str(val)
        self._judg_date_str = val

    @hybrid_property
    def cc_recorded_date_str(self):
        return self._cc_recorded_date_str
    @cc_recorded_date_str.setter
    def cc_recorded_date_str(self,val):
        self.cc_recorded_date = date_from_str(val)
        self._cc_recorded_date_str = val
    
    @hybrid_property
    def satisfaction_date_str(self):
        return self._satisfaction_date_str
    @satisfaction_date_str.setter
    def satisfaction_date_str(self,val):
        self.satisfaction_date = date_from_str(val)
        self._satisfaction_date_str = val
    
    @hybrid_property
    def sat_date_entered_str(self):
        return self._sat_date_entered_str
    @sat_date_entered_str.setter
    def sat_date_entered_str(self,val):
        self.sat_date_entered = date_from_str(val)
        self._sat_date_entered_str = val

    @hybrid_property
    def date_entered_str(self):
        return self._date_entered_str
    @date_entered_str.setter
    def date_entered_str(self,val):
        self.date_entered = date_from_str(val)
        self._date_entered_str = val
    
    @hybrid_property
    def printdate_str(self):
        return self._printdate_str
    @printdate_str.setter
    def printdate_str(self,val):
        self.printdate = date_from_str(val)
        self._printdate_str = val
    
    @hybrid_property
    def renewed_date_str(self):
        return self._renewed_date_str
    @renewed_date_str.setter
    def renewed_date_str(self,val):
        self.renewed_date = date_from_str(val)
        self._renewed_date_str = val
    
    @hybrid_property
    def renewed_lien_date_str(self):
        return self._renewed_lien_date_str
    @renewed_lien_date_str.setter
    def renewed_lien_date_str(self,val):
        self.renewed_lien_date = date_from_str(val)
        self._renewed_lien_date_str = val
    
    @hybrid_property
    def renewed_date_ent_str(self):
        return self._renewed_date_ent_str
    @renewed_date_ent_str.setter
    def renewed_date_ent_str(self,val):
        self.renewed_date_ent = date_from_str(val)
        self._renewed_date_ent_str = val

class ODYCIVILDisposition(ODYCIVILCaseTable, TableBase):
    __tablename__ = 'odycivil_dispositions'
    __table_args__ = (Index('ixh_odycivil_dispositions_case_number', 'case_number', postgresql_using='hash'),)
    odycivil = relationship('ODYCIVIL', backref='dispositions')

    id = Column(Integer, primary_key=True)
    disp_date = Column(Date)
    _disp_date_str = Column('disp_date_str',String)
    disp_code = Column(String, enum=True)
    disp_description = Column(String, enum=True)
    disp_stage = Column(String, enum=True)
    disp_stage_description = Column(String, enum=True)
    user = Column(String)
    usercdate = Column(Date)
    _usercdate_str = Column('usercdate_str',String)

    @hybrid_property
    def disp_date_str(self):
        return self._disp_date_str
    @disp_date_str.setter
    def disp_date_str(self,val):
        self.disp_date = date_from_str(val)
        self._disp_date_str = val

    @hybrid_property
    def usercdate_str(self):
        return self._usercdate_str
    @usercdate_str.setter
    def usercdate_str(self,val):
        self.usercdate = date_from_str(val)
        self._usercdate_str = val


class ODYCIVILCourtSchedule(ODYCIVILCaseTable, TableBase):
    __tablename__ = 'odycivil_court_schedule'
    __table_args__ = (Index('ixh_odycivil_court_schedule_case_number', 'case_number', postgresql_using='hash'),)
    odycivil = relationship('ODYCIVIL', backref='court_schedule')

    id = Column(Integer, primary_key=True)
    event_type = Column(String, nullable=False, enum=True)
    date = Column(Date)
    _date_str = Column('date_str', String)
    time = Column(Time)
    _time_str = Column('time_str', String)
    judge = Column(String)
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

class ODYCIVILWarrant(ODYCIVILCaseTable, TableBase):
    __tablename__ = 'odycivil_warrants'
    __table_args__ = (Index('ixh_odycivil_warrants_case_number', 'case_number', postgresql_using='hash'),)
    odycivil = relationship('ODYCIVIL', backref='warrants')

    id = Column(Integer, primary_key=True)
    warrant_type = Column(String, enum=True)
    issue_date = Column(Date)
    _issue_date_str = Column('issue_date_str', String)
    judge = Column(String)
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

class ODYCIVILBondSetting(ODYCIVILCaseTable, TableBase):
    __tablename__ = 'odycivil_bond_settings'
    __table_args__ = (Index('ixh_odycivil_bond_settings_case_number', 'case_number', postgresql_using='hash'),)
    odycivil = relationship('ODYCIVIL', backref='bond_settings')

    id = Column(Integer, primary_key=True)
    bail_date = Column(Date)
    _bail_date_str = Column('bail_date_str', String)
    bail_setting_type = Column(String, enum=True)
    bail_amount = Column(Numeric)
    judge = Column(String)

    @hybrid_property
    def bail_date_str(self):
        return self._bail_date_str
    @bail_date_str.setter
    def bail_date_str(self,val):
        self.bail_date = date_from_str(val)
        self._bail_date_str = val

class ODYCIVILBailBond(ODYCIVILCaseTable, TableBase):
    __tablename__ = 'odycivil_bail_bonds'
    __table_args__ = (Index('ixh_odycivil_bail_bonds_case_number', 'case_number', postgresql_using='hash'),)
    odycivil = relationship('ODYCIVIL', backref='bail_bonds')

    id = Column(Integer, primary_key=True)
    bond_type = Column(String, enum=True)
    bond_amount_set = Column(Numeric)
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

class ODYCIVILDocument(ODYCIVILCaseTable, TableBase):
    __tablename__ = 'odycivil_documents'
    __table_args__ = (Index('ixh_odycivil_documents_case_number', 'case_number', postgresql_using='hash'),)
    odycivil = relationship('ODYCIVIL', backref='documents')

    id = Column(Integer, primary_key=True)
    file_date = Column(Date)
    _file_date_str = Column('file_date_str',String)
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
