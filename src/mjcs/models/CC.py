from .common import TableBase, CaseTable, date_from_str, RelatedPerson, Event, Trial
from sqlalchemy import Column, Date, Numeric, Integer, String, Boolean, ForeignKey, Time, BigInteger, Text
from sqlalchemy.orm import relationship, backref
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.ext.declarative import declared_attr

class CC(CaseTable, TableBase):
    __tablename__ = 'cc'

    id = Column(Integer, primary_key=True)
    court_system = Column(String, index=True)
    title = Column(String, index=True)
    case_type = Column(String,nullable=True, index=True)
    filing_date = Column(Date,nullable=True, index=True)
    _filing_date_str = Column('filing_date_str',String,nullable=True, index=True)
    case_status = Column(String,nullable=True, index=True)
    case_disposition = Column(String,nullable=True, index=True)
    disposition_date = Column(Date,nullable=True, index=True)
    _disposition_date_str = Column('disposition_date_str',String,nullable=True, index=True)

    case = relationship('Case', backref=backref('cc', uselist=False))

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
    def case_number(cls):
        return Column(String, ForeignKey('cc.case_number', ondelete='CASCADE'), index=True)

class CCDistrictCaseNumber(CCCaseTable, TableBase):
    __tablename__ = 'cc_district_case_numbers'
    cc = relationship('CC', backref='district_case_numbers')

    id = Column(Integer, primary_key=True)
    district_case_number = Column(String) # TODO eventually make a ForeignKey relation

class Party:
    id = Column(Integer, primary_key=True)
    party_type = Column(String)
    party_number = Column(Integer,nullable=True)
    name = Column(String,nullable=True)
    business_org_name = Column(String,nullable=True)

    @declared_attr
    def aliases(cls):
        return relationship('CCPartyAlias')

    @declared_attr
    def addresses(cls):
        return relationship('CCPartyAddress')

    @declared_attr
    def attorneys(cls):
        return relationship('CCAttorney')

class CCPlaintiff(Party, CCCaseTable, TableBase):
    __tablename__ = 'cc_plaintiffs'
    cc = relationship('CC', backref='plaintiffs')

class CCDefendant(Party, CCCaseTable, TableBase):
    __tablename__ = 'cc_defendants'
    cc = relationship('CC', backref='defendants')

class CCRelatedPerson(Party, CCCaseTable, TableBase):
    __tablename__ = 'cc_related_persons'
    cc = relationship('CC', backref='related_persons')

class CCPartyAlias(CCCaseTable, TableBase):
    __tablename__ = 'cc_party_alias'

    id = Column(Integer, primary_key=True)
    plaintiff_id = Column(Integer, ForeignKey('cc_plaintiffs.id'),nullable=True)
    defendant_id = Column(Integer, ForeignKey('cc_defendants.id'),nullable=True)
    related_person_id = Column(Integer, ForeignKey('cc_related_persons.id'),nullable=True)
    name = Column(String)

class CCPartyAddress(CCCaseTable, TableBase):
    __tablename__ = 'cc_party_addresses'

    id = Column(Integer, primary_key=True)
    plaintiff_id = Column(Integer, ForeignKey('cc_plaintiffs.id'),nullable=True)
    defendant_id = Column(Integer, ForeignKey('cc_defendants.id'),nullable=True)
    related_person_id = Column(Integer, ForeignKey('cc_related_persons.id'),nullable=True)
    address = Column(String)
    city = Column(String)
    state = Column(String)
    zip_code = Column(String)

class CCAttorney(CCCaseTable, TableBase):
    __tablename__ = 'cc_attorneys'

    id = Column(Integer, primary_key=True)
    plaintiff_id = Column(Integer, ForeignKey('cc_plaintiffs.id'),nullable=True)
    defendant_id = Column(Integer, ForeignKey('cc_defendants.id'),nullable=True)
    related_person_id = Column(Integer, ForeignKey('cc_related_persons.id'),nullable=True)
    name = Column(String)
    appearance_date = Column(Date,nullable=True)
    _appearance_date_str = Column('appearance_date_str',String,nullable=True)
    removal_date = Column(Date,nullable=True)
    _removal_date_str = Column('removal_date_str',String,nullable=True)
    practice_name = Column(String,nullable=True)
    address_1 = Column(String)
    address_2 = Column(String,nullable=True)
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
    cc = relationship('CC', backref='court_schedules')

    id = Column(Integer, primary_key=True)
    event_type = Column(String)
    notice_date = Column(Date,nullable=True)
    _notice_date_str = Column('notice_date_str',String)
    event_date = Column(Date,nullable=True)
    _event_date_str = Column('event_date_str',String)
    event_time = Column(Time, nullable=True)
    _event_time_str = Column('event_time_str', String)
    result = Column(String)
    result_date = Column(Date,nullable=True)
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
            self.time = datetime.strptime(val,'%I:%M %p').time()
        except:
            try:
                self.time = datetime.strptime(val,'%I:%M').time()
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
    cc = relationship('CC', backref='documents')

    id = Column(Integer, primary_key=True)
    document_number = Column(Integer)
    sequence_number = Column(Integer)
    file_date = Column(Date,nullable=True)
    _file_date_str = Column('file_date_str',String,nullable=True)
    entered_date = Column(Date,nullable=True)
    _entered_date_str = Column('entered_date_str',String,nullable=True)
    decision = Column(String,nullable=True)
    party_type = Column(String,nullable=True) # TODO could eventually map this and party_number to case parties
    party_number = Column(Integer,nullable=True)
    document_name = Column(String,nullable=True)
    text = Column(Text,nullable=True)

class CCJudgment(CCCaseTable, TableBase):
    __tablename__ = 'cc_judgments'
    cc = relationship('CC', backref='judgments')

    id = Column(Integer, primary_key=True)
    judgment_type = Column(String)
    entered_date = Column(Date,nullable=True)
    _entered_date_str = Column('entered_date_str',String)
    amount = Column(Numeric)
    amount_other = Column(String,nullable=True)
    prejudgment_interest = Column(Numeric)
    appearance_fee = Column(Numeric)
    filing_fee = Column(Numeric)
    other_fee = Column(Numeric)
    service_fee = Column(Numeric)
    witness_fee = Column(Numeric)
    attorney_fee = Column(Numeric)
    total_indexed_judgment = Column(Numeric)
    tij_other = Column(String,nullable=True)
    comments = Column(String,nullable=True)
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

    id = Column(Integer, primary_key=True)
    judgment_id = Column(Integer, ForeignKey('cc_judgments.id'))
    judgment_against = Column(String)
    judgment_for = Column(String)
    entered_date = Column(Date,nullable=True)
    _entered_date_str = Column('entered_date_str',String)
    amount = Column(Numeric)
    amount_other = Column(String,nullable=True)
    status_date = Column(Date,nullable=True)
    _status_date_str = Column('status_date_str',String)
    status = Column(String)
    comments = Column(String,nullable=True)

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

    id = Column(Integer, primary_key=True)
    judgment_id = Column(Integer, ForeignKey('cc_judgments.id'))
    name = Column(String)

class CCJudgmentInFavor(CCCaseTable, TableBase):
    __tablename__ = 'cc_judgments_in_favor'

    id = Column(Integer, primary_key=True)
    judgment_id = Column(Integer, ForeignKey('cc_judgments.id'))
    name = Column(String)

class CCSupportOrder(CCCaseTable, TableBase):
    __tablename__ = 'cc_support_orders'
    cc = relationship('CC', backref='support_orders')

    id = Column(Integer, primary_key=True)
    order_id = Column(Integer)
    version = Column(Integer)
    order_date = Column(Date,nullable=True)
    _order_date_str = Column('order_date_str',String)
    obligor = Column(String)
    effective_date = Column(Date,nullable=True)
    _effective_date_str = Column('effective_date_str',String)
    effective_date_text = Column(String,nullable=True) # TODO confirm data type
    status = Column(String)
    date = Column(Date,nullable=True)
    _date_str = Column('date_str',String)
    reason = Column(String,nullable=True)
    support_amount = Column(Numeric)
    support_frequency = Column(String,nullable=True)
    support_to = Column(String,nullable=True)
    arrears_amount = Column(Numeric)
    arrears_frequency = Column(String,nullable=True)
    arrears_to = Column(String,nullable=True)
    mapr_amount = Column(Numeric)
    mapr_frequency = Column(String,nullable=True)
    medical_insurance_report_date = Column(Date,nullable=True)
    _medical_insurance_report_date_str = Column('medical_insurance_report_date_str',String,nullable=True)
    btr_amount = Column(Numeric)
    btr_frequency = Column(String,nullable=True)
    lien = Column(String)
    provisions = Column(String,nullable=True) # TODO confirm data type

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
