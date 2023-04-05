from .common import TableBase, CaseTable, date_from_str, MetaColumn as Column
from sqlalchemy import Date, Numeric, Integer, String, Boolean, ForeignKey, Time, Text, Index
from sqlalchemy.orm import relationship, backref
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.ext.declarative import declared_attr
from datetime import datetime

class CC(CaseTable, TableBase):
    '''Circuit Court Civil Cases'''
    __tablename__ = 'cc'
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

    case = relationship('Case', backref=backref('cc', uselist=False))

    __table_args__ = (Index('ixh_cc_case_number', 'case_number', postgresql_using='hash'),)

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

class CCCaseTable(CaseTable):
    @declared_attr
    def case_number(self):
        return Column(String, ForeignKey('cc.case_number', ondelete='CASCADE'), nullable=False)

class CCDistrictCaseNumber(CCCaseTable, TableBase):
    __tablename__ = 'cc_district_case_numbers'
    __table_args__ = (Index('ixh_cc_district_case_numbers_case_number', 'case_number', postgresql_using='hash'),)
    cc = relationship('CC', backref='district_case_numbers')

    id = Column(Integer, primary_key=True)
    district_case_number = Column(String) # TODO eventually make a ForeignKey relation

class Party:
    id = Column(Integer, primary_key=True)
    party_type = Column(String, enum=True)
    party_number = Column(Integer)
    name = Column(String)
    business_org_name = Column(String)

    @declared_attr
    def aliases(self):
        return relationship('CCPartyAlias')

    @declared_attr
    def addresses(self):
        return relationship('CCPartyAddress')

    @declared_attr
    def attorneys(self):
        return relationship('CCAttorney')

class CCPlaintiff(Party, CCCaseTable, TableBase):
    __tablename__ = 'cc_plaintiffs'
    __table_args__ = (Index('ixh_cc_plaintiffs_case_number', 'case_number', postgresql_using='hash'),)
    cc = relationship('CC', backref='plaintiffs')

class CCDefendant(Party, CCCaseTable, TableBase):
    __tablename__ = 'cc_defendants'
    __table_args__ = (Index('ixh_cc_defendants_case_number', 'case_number', postgresql_using='hash'),)
    cc = relationship('CC', backref='defendants')

class CCRelatedPerson(Party, CCCaseTable, TableBase):
    __tablename__ = 'cc_related_persons'
    __table_args__ = (Index('ixh_cc_related_persons_case_number', 'case_number', postgresql_using='hash'),)
    cc = relationship('CC', backref='related_persons')

class CCPartyAlias(CCCaseTable, TableBase):
    __tablename__ = 'cc_party_alias'
    __table_args__ = (Index('ixh_cc_party_alias_case_number', 'case_number', postgresql_using='hash'),)
    cc = relationship('CC', backref='party_aliases')

    id = Column(Integer, primary_key=True)
    plaintiff_id = Column(Integer, ForeignKey('cc_plaintiffs.id'))
    defendant_id = Column(Integer, ForeignKey('cc_defendants.id'))
    related_person_id = Column(Integer, ForeignKey('cc_related_persons.id'))
    name = Column(String)

class CCPartyAddress(CCCaseTable, TableBase):
    __tablename__ = 'cc_party_addresses'
    __table_args__ = (Index('ixh_cc_party_addresses_case_number', 'case_number', postgresql_using='hash'),)
    cc = relationship('CC', backref='party_addresses')

    id = Column(Integer, primary_key=True)
    plaintiff_id = Column(Integer, ForeignKey('cc_plaintiffs.id'))
    defendant_id = Column(Integer, ForeignKey('cc_defendants.id'))
    related_person_id = Column(Integer, ForeignKey('cc_related_persons.id'))
    address = Column(String)
    city = Column(String)
    state = Column(String)
    zip_code = Column(String)

class CCAttorney(CCCaseTable, TableBase):
    __tablename__ = 'cc_attorneys'
    __table_args__ = (Index('ixh_cc_attorneys_case_number', 'case_number', postgresql_using='hash'),)
    cc = relationship('CC', backref='attorneys')

    id = Column(Integer, primary_key=True)
    plaintiff_id = Column(Integer, ForeignKey('cc_plaintiffs.id'))
    defendant_id = Column(Integer, ForeignKey('cc_defendants.id'))
    related_person_id = Column(Integer, ForeignKey('cc_related_persons.id'))
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

class CCCourtSchedule(CCCaseTable, TableBase):
    __tablename__ = 'cc_court_schedule'
    __table_args__ = (Index('ixh_cc_court_schedule_case_number', 'case_number', postgresql_using='hash'),)
    cc = relationship('CC', backref='court_schedule')

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

class CCDocument(CCCaseTable, TableBase):
    __tablename__ = 'cc_documents'
    __table_args__ = (Index('ixh_cc_documents_case_number', 'case_number', postgresql_using='hash'),)
    cc = relationship('CC', backref='documents')

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

class CCJudgment(CCCaseTable, TableBase):
    __tablename__ = 'cc_judgments'
    __table_args__ = (Index('ixh_cc_judgments_case_number', 'case_number', postgresql_using='hash'),)
    cc = relationship('CC', backref='judgments')

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
    judgment_modifications = relationship('CCJudgmentModification')
    judgments_against = relationship('CCJudgmentAgainst')
    judgments_in_favor = relationship('CCJudgmentInFavor')

    @hybrid_property
    def entered_date_str(self):
        return self._entered_date_str
    @entered_date_str.setter
    def entered_date_str(self,val):
        self.entered_date = date_from_str(val)
        self._entered_date_str = val

class CCJudgmentModification(CCCaseTable, TableBase):
    __tablename__ = 'cc_judgment_modifications'
    __table_args__ = (Index('ixh_cc_judgment_modifications_case_number', 'case_number', postgresql_using='hash'),)
    cc = relationship('CC', backref='judgment_modifications')

    id = Column(Integer, primary_key=True)
    judgment_id = Column(Integer, ForeignKey('cc_judgments.id'))
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

class CCJudgmentAgainst(CCCaseTable, TableBase):
    __tablename__ = 'cc_judgments_against'
    __table_args__ = (Index('ixh_cc_judgments_against_case_number', 'case_number', postgresql_using='hash'),)
    cc = relationship('CC', backref='judgments_against')

    id = Column(Integer, primary_key=True)
    judgment_id = Column(Integer, ForeignKey('cc_judgments.id'))
    name = Column(String)

class CCJudgmentInFavor(CCCaseTable, TableBase):
    __tablename__ = 'cc_judgments_in_favor'
    __table_args__ = (Index('ixh_cc_judgments_in_favor_case_number', 'case_number', postgresql_using='hash'),)
    cc = relationship('CC', backref='judgments_in_favor')

    id = Column(Integer, primary_key=True)
    judgment_id = Column(Integer, ForeignKey('cc_judgments.id'))
    name = Column(String)

class CCSupportOrder(CCCaseTable, TableBase):
    __tablename__ = 'cc_support_orders'
    __table_args__ = (Index('ixh_cc_support_orders_case_number', 'case_number', postgresql_using='hash'),)
    cc = relationship('CC', backref='support_orders')

    id = Column(Integer, primary_key=True)
    order_id = Column(Integer)
    version = Column(Integer)
    order_date = Column(Date)
    _order_date_str = Column('order_date_str',String)
    obligor = Column(String)
    effective_date = Column(Date)
    _effective_date_str = Column('effective_date_str',String)
    effective_date_text = Column(String) # TODO confirm data type
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
