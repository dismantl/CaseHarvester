from .common import TableBase, MetaColumn as Column, CaseTable, date_from_str
from sqlalchemy import Date, Numeric, Integer, String, Boolean, ForeignKey, Index, Time
from sqlalchemy.orm import relationship, backref
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.ext.declarative import declared_attr
from datetime import datetime

class DSCP(CaseTable, TableBase):
    '''District Court Civil Citations'''
    __tablename__ = 'dscp'
    is_root = True

    id = Column(Integer, primary_key=True)
    court_system = Column(String, enum=True)
    tracking_number = Column(String, nullable=True)
    case_type = Column(String, nullable=True, enum=True)
    district_code = Column(Integer, nullable=True)
    location_code = Column(Integer, nullable=True)
    document_type = Column(String, nullable=True, enum=True)
    issued_date = Column(Date, nullable=True)
    _issued_date_str = Column('issued_date_str',String, nullable=True)
    case_status = Column(String, nullable=True, enum=True)
    case_disposition = Column(String, nullable=True, enum=True)

    case = relationship('Case', backref=backref('dscp', uselist=False))

    __table_args__ = (Index('ixh_dscp_case_number', 'case_number', postgresql_using='hash'),)

    @hybrid_property
    def issued_date_str(self):
        return self._issued_date_str
    @issued_date_str.setter
    def issued_date_str(self,val):
        self.issued_date = date_from_str(val)
        self._issued_date_str = val

class DSCPCaseTable(CaseTable):
    @declared_attr
    def case_number(self):
        return Column(String, ForeignKey('dscp.case_number', ondelete='CASCADE'), nullable=False)

class DSCPCharge(DSCPCaseTable, TableBase):
    __tablename__ = 'dscp_charges'
    __table_args__ = (Index('ixh_dscp_charges_case_number', 'case_number', postgresql_using='hash'),)
    dscp = relationship('DSCP', backref='charges')

    id = Column(Integer, primary_key=True)
    charge_number = Column(Integer)
    expunged = Column(Boolean, nullable=False, server_default='false')
    charge_description = Column(String, nullable=True)
    statute = Column(String, nullable=True)
    statute_description = Column(String, nullable=True)
    amended_date = Column(Date, nullable=True)
    _amended_date_str = Column('amended_date_str',String, nullable=True)
    cjis_code = Column(String, nullable=True)
    mo_pll = Column(String, nullable=True)
    probable_cause = Column(Boolean)
    incident_date_from = Column(Date, nullable=True)
    _incident_date_from_str = Column('incident_date_from_str',String, nullable=True)
    incident_date_to = Column(Date, nullable=True)
    _incident_date_to_str = Column('incident_date_to_str',String, nullable=True)
    victim_age = Column(String, nullable=True)
    plea = Column(String, nullable=True, enum=True)
    disposition = Column(String, nullable=True, enum=True)
    disposition_date = Column(Date, nullable=True)
    _disposition_date_str = Column('disposition_date_str',String, nullable=True)
    fine = Column(Numeric, nullable=True)
    court_costs = Column(Numeric, nullable=True)
    cicf = Column(Numeric, nullable=True)
    suspended_fine = Column(Numeric, nullable=True)
    suspended_court_costs = Column(Numeric, nullable=True)
    suspended_cicf = Column(Numeric, nullable=True)
    pbj_end_date = Column(Date, nullable=True)
    _pbj_end_date_str = Column('pbj_end_date_str',String, nullable=True)
    probation_end_date = Column(Date, nullable=True)
    _probation_end_date_str = Column('probation_end_date_str',String, nullable=True)
    restitution_amount = Column(Numeric, nullable=True)
    jail_term_years = Column(Integer, nullable=True)
    jail_term_months = Column(Integer, nullable=True)
    jail_term_days = Column(Integer, nullable=True)
    suspended_term_years = Column(Integer, nullable=True)
    suspended_term_months = Column(Integer, nullable=True)
    suspended_term_days = Column(Integer, nullable=True)
    credit_time_served = Column(String, nullable=True)

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

class DSCPDefendant(DSCPCaseTable, TableBase):
    __tablename__ = 'dscp_defendants'
    __table_args__ = (Index('ixh_dscp_defendants_case_number', 'case_number', postgresql_using='hash'),)
    dscp = relationship('DSCP', backref='defendants')

    id = Column(Integer, primary_key=True)
    name = Column(String, redacted=True)
    race = Column(String, nullable=True)
    sex = Column(String, nullable=True)
    height = Column(Integer, nullable=True)
    weight = Column(Integer, nullable=True)
    DOB = Column(Date, nullable=True, redacted=True)
    _DOB_str = Column('DOB_str',String, nullable=True, redacted=True)
    address_1 = Column(String, nullable=True, redacted=True)
    address_2 = Column(String, nullable=True, redacted=True)
    city = Column(String, nullable=True)
    state = Column(String, nullable=True)
    zip_code = Column(String, nullable=True)

    @hybrid_property
    def DOB_str(self):
        return self._DOB_str
    @DOB_str.setter
    def DOB_str(self,val):
        self.DOB = date_from_str(val)
        self._DOB_str = val

class DSCPDefendantAlias(DSCPCaseTable, TableBase):
    __tablename__ = 'dscp_defendant_aliases'
    __table_args__ = (Index('ixh_dscp_defendant_aliases_case_number', 'case_number', postgresql_using='hash'),)
    dscp = relationship('DSCP', backref='defendant_aliases')

    id = Column(Integer, primary_key=True)
    alias_name = Column(String, nullable=True)

class DSCPRelatedPerson(DSCPCaseTable, TableBase):
    __tablename__ = 'dscp_related_persons'
    __table_args__ = (Index('ixh_dscp_related_persons_case_number', 'case_number', postgresql_using='hash'),)
    dscp = relationship('DSCP', backref='related_persons')

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=True)
    connection = Column(String, nullable=True, enum=True)
    agency_code = Column(String, nullable=True, enum=True)
    agency_sub_code = Column(String, nullable=True)
    officer_id = Column(String, nullable=True)

class DSCPEvent(DSCPCaseTable, TableBase):
    __tablename__ = 'dscp_events'
    __table_args__ = (Index('ixh_dscp_events_case_number', 'case_number', postgresql_using='hash'),)
    dscp = relationship('DSCP', backref='events')

    id = Column(Integer, primary_key=True)
    event_name = Column(String, nullable=True, enum=True)
    date = Column(Date, nullable=True)
    _date_str = Column('date_str',String, nullable=True)
    comment = Column(String, nullable=True)

    @hybrid_property
    def date_str(self):
        return self._date_str
    @date_str.setter
    def date_str(self,val):
        self.date = date_from_str(val)
        self._date_str = val

class DSCPTrial(DSCPCaseTable, TableBase):
    __tablename__ = 'dscp_trials'
    __table_args__ = (Index('ixh_dscp_trials_case_number', 'case_number', postgresql_using='hash'),)
    dscp = relationship('DSCP', backref='trials')

    id = Column(Integer, primary_key=True)
    date = Column(Date, nullable=True)
    _date_str = Column('date_str', String, nullable=True)
    time = Column(Time, nullable=True)
    _time_str = Column('time_str', String, nullable=True)
    room = Column(String, nullable=True)
    trial_type = Column(String, nullable=True, enum=True)
    location = Column(String, nullable=True)

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

class DSCPBailEvent(DSCPCaseTable, TableBase):
    __tablename__ = 'dscp_bail_events'
    __table_args__ = (Index('ixh_dscp_bail_events_case_number', 'case_number', postgresql_using='hash'),)
    dscp = relationship('DSCP', backref='bail_events')

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
