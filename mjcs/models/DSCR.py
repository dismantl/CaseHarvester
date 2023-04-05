from .common import TableBase, MetaColumn as Column, CaseTable, date_from_str
from sqlalchemy import Date, Numeric, Integer, String, Boolean, ForeignKey, Index, Time
from sqlalchemy.orm import relationship, backref
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.ext.declarative import declared_attr
from datetime import datetime

class DSCR(CaseTable, TableBase):
    '''District Court Criminal Cases'''
    __tablename__ = 'dscr'
    is_root = True

    id = Column(Integer, primary_key=True)
    court_system = Column(String, enum=True)
    tracking_number = Column(String)
    case_type = Column(String, enum=True)
    district_code = Column(Integer)
    location_code = Column(Integer)
    document_type = Column(String, enum=True)
    issued_date = Column(Date)
    _issued_date_str = Column('issued_date_str',String)
    case_status = Column(String, enum=True)
    case_disposition = Column(String, enum=True)

    case = relationship('Case', backref=backref('dscr', uselist=False))

    __table_args__ = (Index('ixh_dscr_case_number', 'case_number', postgresql_using='hash'),)

    @hybrid_property
    def issued_date_str(self):
        return self._issued_date_str
    @issued_date_str.setter
    def issued_date_str(self,val):
        self.issued_date = date_from_str(val)
        self._issued_date_str = val

class DSCRCaseTable(CaseTable):
    @declared_attr
    def case_number(self):
        return Column(String, ForeignKey('dscr.case_number', ondelete='CASCADE'), nullable=False)

class DSCRCharge(DSCRCaseTable, TableBase):
    __tablename__ = 'dscr_charges'
    __table_args__ = (Index('ixh_dscr_charges_case_number', 'case_number', postgresql_using='hash'),)
    dscr = relationship('DSCR', backref='charges')

    id = Column(Integer, primary_key=True)
    charge_number = Column(Integer)
    expunged = Column(Boolean, nullable=False, server_default='false')
    charge_description = Column(String)
    statute = Column(String)
    statute_description = Column(String)
    amended_date = Column(Date)
    _amended_date_str = Column('amended_date_str',String)
    cjis_code = Column(String)
    mo_pll = Column(String)
    probable_cause = Column(Boolean)
    incident_date_from = Column(Date)
    _incident_date_from_str = Column('incident_date_from_str',String)
    incident_date_to = Column(Date)
    _incident_date_to_str = Column('incident_date_to_str',String)
    victim_age = Column(Integer)
    plea = Column(String, enum=True)
    disposition = Column(String, enum=True)
    disposition_date = Column(Date)
    _disposition_date_str = Column('disposition_date_str',String)
    fine = Column(Numeric)
    court_costs = Column(Numeric)
    cicf = Column(Numeric)
    suspended_fine = Column(Numeric)
    suspended_court_costs = Column(Numeric)
    suspended_cicf = Column(Numeric)
    pbj_end_date = Column(Date)
    _pbj_end_date_str = Column('pbj_end_date_str',String)
    probation_end_date = Column(Date)
    _probation_end_date_str = Column('probation_end_date_str',String)
    restitution_amount = Column(Numeric)
    jail_term_years = Column(Integer)
    jail_term_months = Column(Integer)
    jail_term_days = Column(Integer)
    suspended_term_years = Column(Integer)
    suspended_term_months = Column(Integer)
    suspended_term_days = Column(Integer)
    credit_time_served = Column(String)
    notes = Column(String)

    @hybrid_property
    def amended_date_str(self):
        return self._amended_date_str
    @amended_date_str.setter
    def amended_date_str(self,val):
        self.amended_date = date_from_str(val)
        self._amended_date_str = val

    @hybrid_property
    def incident_date_from_str(self):
        return self._incident_date_from_str
    @incident_date_from_str.setter
    def incident_date_from_str(self,val):
        self.incident_date_from = date_from_str(val)
        self._incident_date_from_str = val

    @hybrid_property
    def incident_date_to_str(self):
        return self._incident_date_to_str
    @incident_date_to_str.setter
    def incident_date_to_str(self,val):
        self.incident_date_to = date_from_str(val)
        self._incident_date_to_str = val

    @hybrid_property
    def disposition_date_str(self):
        return self._disposition_date_str
    @disposition_date_str.setter
    def disposition_date_str(self,val):
        self.disposition_date = date_from_str(val)
        self._disposition_date_str = val

    @hybrid_property
    def pbj_end_date_str(self):
        return self._pbj_end_date_str
    @pbj_end_date_str.setter
    def pbj_end_date_str(self,val):
        self.pbj_end_date = date_from_str(val)
        self._pbj_end_date_str = val

    @hybrid_property
    def probation_end_date_str(self):
        return self._probation_end_date_str
    @probation_end_date_str.setter
    def probation_end_date_str(self,val):
        self.probation_end_date = date_from_str(val)
        self._probation_end_date_str = val

class DSCRDefendant(DSCRCaseTable, TableBase):
    __tablename__ = 'dscr_defendants'
    __table_args__ = (Index('ixh_dscr_defendants_case_number', 'case_number', postgresql_using='hash'),)
    dscr = relationship('DSCR', backref='defendants')

    id = Column(Integer, primary_key=True)
    name = Column(String, redacted=True)
    race = Column(String, enum=True)
    sex = Column(String)
    height = Column(Integer)
    weight = Column(Integer)
    DOB = Column(Date, redacted=True)
    _DOB_str = Column('DOB_str',String, redacted=True)
    address_1 = Column(String, redacted=True)
    address_2 = Column(String, redacted=True)
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

class DSCRDefendantAlias(DSCRCaseTable, TableBase):
    __tablename__ = 'dscr_defendant_aliases'
    __table_args__ = (Index('ixh_dscr_defendant_aliases_case_number', 'case_number', postgresql_using='hash'),)
    dscr = relationship('DSCR', backref='defendant_aliases')

    id = Column(Integer, primary_key=True)
    alias_name = Column(String)
    address_1 = Column(String, redacted=True)
    address_2 = Column(String, redacted=True)
    city = Column(String)
    state = Column(String)
    zip_code = Column(String)

class DSCRRelatedPerson(DSCRCaseTable, TableBase):
    __tablename__ = 'dscr_related_persons'
    __table_args__ = (Index('ixh_dscr_related_persons_case_number', 'case_number', postgresql_using='hash'),)
    dscr = relationship('DSCR', backref='related_persons')

    id = Column(Integer, primary_key=True)
    name = Column(String)
    connection = Column(String, enum=True)
    address_1 = Column(String)
    address_2 = Column(String)
    city = Column(String)
    state = Column(String)
    zip_code = Column(String)
    agency_code = Column(String, enum=True)
    agency_sub_code = Column(String)
    officer_id = Column(String)

class DSCREvent(DSCRCaseTable, TableBase):
    __tablename__ = 'dscr_events'
    __table_args__ = (Index('ixh_dscr_events_case_number', 'case_number', postgresql_using='hash'),)
    dscr = relationship('DSCR', backref='events')

    id = Column(Integer, primary_key=True)
    event_name = Column(String, enum=True)
    date = Column(Date)
    _date_str = Column('date_str',String)
    comment = Column(String)

    @hybrid_property
    def date_str(self):
        return self._date_str
    @date_str.setter
    def date_str(self,val):
        self.date = date_from_str(val)
        self._date_str = val

class DSCRTrial(DSCRCaseTable, TableBase):
    __tablename__ = 'dscr_trials'
    __table_args__ = (Index('ixh_dscr_trials_case_number', 'case_number', postgresql_using='hash'),)
    dscr = relationship('DSCR', backref='trials')

    id = Column(Integer, primary_key=True)
    date = Column(Date)
    _date_str = Column('date_str', String)
    time = Column(Time)
    _time_str = Column('time_str', String)
    room = Column(String)
    trial_type = Column(String, enum=True)
    location = Column(String)

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
            self.time = datetime.strptime(val,'%I:%M %p').time()
        except:
            try:
                self.time = datetime.strptime(val,'%I:%M').time()
            except:
                pass
        self._time_str = val

class DSCRBailEvent(DSCRCaseTable, TableBase):
    __tablename__ = 'dscr_bail_events'
    __table_args__ = (Index('ixh_dscr_bail_events_case_number', 'case_number', postgresql_using='hash'),)
    dscr = relationship('DSCR', backref='bail_events')

    id = Column(Integer, primary_key=True)
    event_name = Column(String, enum=True)
    date = Column(Date)
    _date_str = Column('date_str',String)
    bail_amount = Column(Numeric)
    code = Column(String, enum=True)
    percentage_required = Column(Numeric)
    type_of_bond = Column(String, enum=True)
    judge_id = Column(String)

    @hybrid_property
    def date_str(self):
        return self._date_str
    @date_str.setter
    def date_str(self,val):
        self.date = date_from_str(val)
        self._date_str = val
