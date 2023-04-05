from decimal import Clamped
from sqlalchemy.sql.schema import Table
from .common import TableBase, CaseTable, date_from_str, MetaColumn as Column
from sqlalchemy import Date, Numeric, Integer, String, Boolean, ForeignKey, Time, Text, Index
from sqlalchemy.orm import relationship, backref
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.ext.declarative import declared_attr
from datetime import datetime

class K(CaseTable, TableBase):
    '''Circuit Court Criminal Cases'''
    __tablename__ = 'k'
    is_root = True

    id = Column(Integer, primary_key=True)
    court_system = Column(String, enum=True)
    title = Column(String)
    case_type = Column(String, enum=True)
    filing_date = Column(Date)
    _filing_date_str = Column('filing_date_str',String)
    case_status = Column(String, enum=True)
    case_disposition = Column(String, enum=True)
    disposition_date = Column(Date)
    _disposition_date_str = Column('disposition_date_str',String)

    case = relationship('Case', backref=backref('k', uselist=False))

    __table_args__ = (Index('ixh_k_case_number', 'case_number', postgresql_using='hash'),)

    @hybrid_property
    def filing_date_str(self):
        return self._filing_date_str
    @filing_date_str.setter
    def filing_date_str(self,val):
        self.filing_date = date_from_str(val)
        self._filing_date_str = val

    @hybrid_property
    def disposition_date_str(self):
        return self._disposition_date_str
    @disposition_date_str.setter
    def disposition_date_str(self,val):
        self.disposition_date = date_from_str(val)
        self._disposition_date_str = val

class KCaseTable(CaseTable):
    @declared_attr
    def case_number(self):
        return Column(String, ForeignKey('k.case_number', ondelete='CASCADE'), nullable=False)

class Party:
    id = Column(Integer, primary_key=True)
    party_type = Column(String, enum=True)
    name = Column(String)

    @declared_attr
    def aliases(self):
        return relationship('KPartyAlias')

    @declared_attr
    def addresses(self):
        return relationship('KPartyAddress')

    @declared_attr
    def attorneys(self):
        return relationship('KAttorney')

class KDefendant(KCaseTable, TableBase):
    __tablename__ = 'k_defendants'
    __table_args__ = (Index('ixh_k_defendants_case_number', 'case_number', postgresql_using='hash'),)
    k = relationship('K', backref='defendants')

    id = Column(Integer, primary_key=True)
    party_type = Column(String, enum=True)
    name = Column(String, redacted=True)
    race = Column(String, enum=True)
    sex = Column(String)
    height = Column(Integer)
    weight = Column(Integer)
    DOB = Column(Date, redacted=True)
    _DOB_str = Column('DOB_str',String, redacted=True)

    @hybrid_property
    def DOB_str(self):
        return self._DOB_str
    @DOB_str.setter
    def DOB_str(self,val):
        self.DOB = date_from_str(val)
        self._DOB_str = val

    @declared_attr
    def aliases(self):
        return relationship('KPartyAlias')

    @declared_attr
    def addresses(self):
        return relationship('KPartyAddress')

    @declared_attr
    def attorneys(self):
        return relationship('KAttorney')

class KRelatedPerson(Party, KCaseTable, TableBase):
    __tablename__ = 'k_related_persons'
    __table_args__ = (Index('ixh_k_related_persons_case_number', 'case_number', postgresql_using='hash'),)
    k = relationship('K', backref='related_persons')

class KPartyAlias(KCaseTable, TableBase):
    __tablename__ = 'k_party_alias'
    __table_args__ = (Index('ixh_k_party_alias_case_number', 'case_number', postgresql_using='hash'),)
    k = relationship('K', backref='party_aliases')

    id = Column(Integer, primary_key=True)
    defendant_id = Column(Integer, ForeignKey('k_defendants.id'))
    related_person_id = Column(Integer, ForeignKey('k_related_persons.id'))
    name = Column(String)

class KPartyAddress(KCaseTable, TableBase):
    __tablename__ = 'k_party_addresses'
    __table_args__ = (Index('ixh_k_party_addresses_case_number', 'case_number', postgresql_using='hash'),)
    k = relationship('K', backref='party_addresses')

    id = Column(Integer, primary_key=True)
    defendant_id = Column(Integer, ForeignKey('k_defendants.id'))
    related_person_id = Column(Integer, ForeignKey('k_related_persons.id'))
    address_1 = Column(String)
    address_2 = Column(String)
    address_3 = Column(String)
    city = Column(String)
    state = Column(String)
    zip_code = Column(String)

class KAttorney(KCaseTable, TableBase):
    __tablename__ = 'k_attorneys'
    __table_args__ = (Index('ixh_k_attorneys_case_number', 'case_number', postgresql_using='hash'),)
    k = relationship('K', backref='attorneys')

    id = Column(Integer, primary_key=True)
    defendant_id = Column(Integer, ForeignKey('k_defendants.id'))
    related_person_id = Column(Integer, ForeignKey('k_related_persons.id'))
    name = Column(String)
    appearance_date = Column(Date)
    _appearance_date_str = Column('appearance_date_str',String)
    removal_date = Column(Date)
    _removal_date_str = Column('removal_date_str',String)
    practice_name = Column(String)
    address_1 = Column(String)
    address_2 = Column(String)
    city = Column(String)
    state = Column(String)
    zip_code = Column(String)

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

class KCharge(KCaseTable, TableBase):
    __tablename__ = 'k_charges'
    __table_args__ = (Index('ixh_k_charges_case_number', 'case_number', postgresql_using='hash'),)
    k = relationship('K', backref='charges')

    id = Column(Integer, primary_key=True)
    charge_number = Column(Integer)
    expunged = Column(Boolean, nullable=False, server_default='false')
    cjis_code = Column(String)
    statute_code = Column(String)
    charge_description = Column(String)
    charge_class = Column(String, enum=True)
    offense_date_from = Column(Date)
    _offense_date_from_str = Column('offense_date_from_str', String)
    offense_date_to = Column(Date)
    _offense_date_to_str = Column('offense_date_to_str', String)
    arrest_tracking_number = Column(String)
    citation = Column(String)
    charge_amend_number = Column(Integer)
    sentence_version = Column(Integer)
    plea = Column(String, enum=True)
    plea_date = Column(Date)
    _plea_date_str = Column('plea_date_str', String)
    disposition = Column(String, enum=True)
    disposition_date = Column(Date)
    _disposition_date_str = Column('disposition_date_str', String)
    disposition_merged_text = Column(String)
    jail_life = Column(Boolean)
    jail_years = Column(Integer)
    jail_months = Column(Integer)
    jail_days = Column(Integer)
    jail_hours = Column(Integer)
    jail_suspended_years = Column(Integer)
    jail_suspended_months = Column(Integer)
    jail_suspended_days = Column(Integer)
    jail_suspended_hours = Column(Integer)
    jail_unsuspended_years = Column(Integer)
    jail_unsuspended_months = Column(Integer)
    jail_unsuspended_days = Column(Integer)
    jail_unsuspended_hours = Column(Integer)
    jail_text = Column(String)
    probation_years = Column(Integer)
    probation_months = Column(Integer)
    probation_days = Column(Integer)
    probation_hours = Column(Integer)
    probation_supervised_years = Column(Integer)
    probation_supervised_months = Column(Integer)
    probation_supervised_days = Column(Integer)
    probation_supervised_hours = Column(Integer)
    probation_unsupervised_years = Column(Integer)
    probation_unsupervised_months = Column(Integer)
    probation_unsupervised_days = Column(Integer)
    probation_unsupervised_hours = Column(Integer)
    probation_text = Column(String)
    fine_amount = Column(Numeric)
    fine_suspended_amount = Column(Numeric)
    fine_due = Column(String)
    fine_first_payment_due = Column(String)
    community_work_service_hours = Column(Numeric)
    community_work_service_complete_by = Column(String)
    community_work_service_report_to = Column(String)
    community_work_service_report_date = Column(String)

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

class KCourtSchedule(KCaseTable, TableBase):
    __tablename__ = 'k_court_schedule'
    __table_args__ = (Index('ixh_k_court_schedule_case_number', 'case_number', postgresql_using='hash'),)
    k = relationship('K', backref='court_schedule')

    id = Column(Integer, primary_key=True)
    event_type = Column(String, enum=True)
    notice_date = Column(Date)
    _notice_date_str = Column('notice_date_str',String)
    event_date = Column(Date)
    _event_date_str = Column('event_date_str',String)
    event_time = Column(Time)
    _event_time_str = Column('event_time_str', String)
    result = Column(String, enum=True)
    result_date = Column(Date)
    _result_date_str = Column('result_date_str',String)

    @hybrid_property
    def notice_date_str(self):
        return self._notice_date_str
    @notice_date_str.setter
    def notice_date_str(self,val):
        self.notice_date = date_from_str(val)
        self._notice_date_str = val

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
            try:
                self.event_time = datetime.strptime(val,'%I:%M').time()
            except:
                pass
        self._event_time_str = val

    @hybrid_property
    def result_date_str(self):
        return self._result_date_str
    @result_date_str.setter
    def result_date_str(self,val):
        self.result_date = date_from_str(val)
        self._result_date_str = val

class KDocument(KCaseTable, TableBase):
    __tablename__ = 'k_documents'
    __table_args__ = (Index('ixh_k_documents_case_number', 'case_number', postgresql_using='hash'),)
    k = relationship('K', backref='documents')

    id = Column(Integer, primary_key=True)
    document_number = Column(Integer)
    file_date = Column(Date)
    _file_date_str = Column('file_date_str',String)
    entered_date = Column(Date)
    _entered_date_str = Column('entered_date_str',String)
    decision = Column(String)
    party_type = Column(String, enum=True) # TODO could eventually map this and party_number to case parties
    party_number = Column(Integer)
    document_name = Column(String)
    text = Column(Text)

    @hybrid_property
    def file_date_str(self):
        return self._file_date_str
    @file_date_str.setter
    def file_date_str(self,val):
        self.file_date = date_from_str(val)
        self._file_date_str = val
    
    @hybrid_property
    def entered_date_str(self):
        return self._entered_date_str
    @entered_date_str.setter
    def entered_date_str(self,val):
        self.entered_date = date_from_str(val)
        self._entered_date_str = val

class KJudgment(KCaseTable, TableBase):
    __tablename__ = 'k_judgments'
    __table_args__ = (Index('ixh_k_judgments_case_number', 'case_number', postgresql_using='hash'),)
    k = relationship('K', backref='judgments')

    id = Column(Integer, primary_key=True)
    judgment_type = Column(String, enum=True)
    entered_date = Column(Date)
    _entered_date_str = Column('entered_date_str',String)
    amount = Column(Numeric)
    amount_other = Column(String)
    prejudgment_interest = Column(Numeric)
    appearance_fee = Column(Numeric)
    filing_fee = Column(Numeric)
    other_fee = Column(Numeric)
    service_fee = Column(Numeric)
    witness_fee = Column(Numeric)
    attorney_fee = Column(Numeric)
    total_indexed_judgment = Column(Numeric)
    tij_other = Column(String)
    comments = Column(String)
    judgment_modifications = relationship('KJudgmentModification')
    judgments_against = relationship('KJudgmentAgainst')
    judgments_in_favor = relationship('KJudgmentInFavor')

    @hybrid_property
    def entered_date_str(self):
        return self._entered_date_str
    @entered_date_str.setter
    def entered_date_str(self,val):
        self.entered_date = date_from_str(val)
        self._entered_date_str = val

class KJudgmentModification(KCaseTable, TableBase):
    __tablename__ = 'k_judgment_modifications'
    __table_args__ = (Index('ixh_k_judgment_modifications_case_number', 'case_number', postgresql_using='hash'),)
    k = relationship('K', backref='judgment_modifications')

    id = Column(Integer, primary_key=True)
    judgment_id = Column(Integer, ForeignKey('k_judgments.id'))
    judgment_against = Column(String)
    judgment_for = Column(String)
    entered_date = Column(Date)
    _entered_date_str = Column('entered_date_str',String)
    amount = Column(Numeric)
    amount_other = Column(String)
    status_date = Column(Date)
    _status_date_str = Column('status_date_str',String)
    status = Column(String, enum=True)
    comments = Column(String)

    @hybrid_property
    def entered_date_str(self):
        return self._entered_date_str
    @entered_date_str.setter
    def entered_date_str(self,val):
        self.entered_date = date_from_str(val)
        self._entered_date_str = val

    @hybrid_property
    def status_date_str(self):
        return self._status_date_str
    @status_date_str.setter
    def status_date_str(self,val):
        self.status_date = date_from_str(val)
        self._status_date_str = val

class KJudgmentAgainst(KCaseTable, TableBase):
    __tablename__ = 'k_judgments_against'
    __table_args__ = (Index('ixh_k_judgments_against_case_number', 'case_number', postgresql_using='hash'),)
    k = relationship('K', backref='judgments_against')

    id = Column(Integer, primary_key=True)
    judgment_id = Column(Integer, ForeignKey('k_judgments.id'))
    name = Column(String)

class KJudgmentInFavor(KCaseTable, TableBase):
    __tablename__ = 'k_judgments_in_favor'
    __table_args__ = (Index('ixh_k_judgments_in_favor_case_number', 'case_number', postgresql_using='hash'),)
    k = relationship('K', backref='judgments_in_favor')

    id = Column(Integer, primary_key=True)
    judgment_id = Column(Integer, ForeignKey('k_judgments.id'))
    name = Column(String)

class KSupportOrder(KCaseTable, TableBase):
    __tablename__ = 'k_support_orders'
    __table_args__ = (Index('ixh_k_support_orders_case_number', 'case_number', postgresql_using='hash'),)
    k = relationship('K', backref='support_orders')

    id = Column(Integer, primary_key=True)
    order_id = Column(Integer)
    version = Column(Integer)
    order_date = Column(Date)
    _order_date_str = Column('order_date_str',String)
    obligor = Column(String)
    effective_date = Column(Date)
    _effective_date_str = Column('effective_date_str',String)
    effective_date_text = Column(String)
    status = Column(String, enum=True)
    date = Column(Date)
    _date_str = Column('date_str',String)
    reason = Column(String)
    support_amount = Column(Numeric)
    support_frequency = Column(String, enum=True)
    support_to = Column(String)
    arrears_amount = Column(Numeric)
    arrears_frequency = Column(String, enum=True)
    arrears_to = Column(String)
    mapr_amount = Column(Numeric)
    mapr_frequency = Column(String, enum=True)
    medical_insurance_report_date = Column(Date)
    _medical_insurance_report_date_str = Column('medical_insurance_report_date_str',String)
    btr_amount = Column(Numeric)
    btr_frequency = Column(String, enum=True)
    lien = Column(String)
    provisions = Column(String) # TODO confirm data type

    @hybrid_property
    def order_date_str(self):
        return self._order_date_str
    @order_date_str.setter
    def order_date_str(self,val):
        self.order_date = date_from_str(val)
        self._order_date_str = val

    @hybrid_property
    def effective_date_str(self):
        return self._effective_date_str
    @effective_date_str.setter
    def effective_date_str(self,val):
        self.effective_date = date_from_str(val)
        self._effective_date_str = val

    @hybrid_property
    def date_str(self):
        return self._date_str
    @date_str.setter
    def date_str(self,val):
        self.date = date_from_str(val)
        self._date_str = val

    @hybrid_property
    def medical_insurance_report_date_str(self):
        return self._medical_insurance_report_date_str
    @medical_insurance_report_date_str.setter
    def medical_insurance_report_date_str(self,val):
        self.medical_insurance_report_date = date_from_str(val)
        self._medical_insurance_report_date_str = val

class KSentencingNetTools(KCaseTable, TableBase):
    __tablename__ = 'k_sentencing_net_tools'
    k = relationship('K', backref='sentencing_net_tools')

    id = Column(Integer, primary_key=True)
    serve_time_years = Column(Integer)
    serve_time_months = Column(Integer)
    serve_time_days = Column(Integer)
    serve_time_hours = Column(Integer)
    probation_years = Column(Integer)
    probation_months = Column(Integer)
    probation_days = Column(Integer)
    probation_hours = Column(Integer)
    fine_amount = Column(Numeric)
    fine_due_date = Column(Date)
    _fine_due_date_str = Column('fine_due_date_str', String)
    cws_hours = Column(Integer)
    credit_time_served = Column(Integer)
    
    @hybrid_property
    def fine_due_date_str(self):
        return self._fine_due_date_str
    @fine_due_date_str.setter
    def fine_due_date_str(self,val):
        self.fine_due_date = date_from_str(val)
        self._fine_due_date_str = val
