from .common import TableBase, CaseTable, Trial, Event, date_from_str, Defendant, DefendantAlias, RelatedPerson
from sqlalchemy import Column, Date, Numeric, Integer, String, Boolean, ForeignKey, Time, BigInteger
from sqlalchemy.orm import relationship, backref
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.ext.declarative import declared_attr

class DSCR(CaseTable, TableBase):
    __tablename__ = 'dscr'

    id = Column(Integer, primary_key=True)
    court_system = Column(String, index=True)
    tracking_number = Column(String, nullable=True, index=True)
    case_type = Column(String, nullable=True, index=True)
    district_code = Column(Integer, nullable=True, index=True)
    location_code = Column(Integer, nullable=True, index=True)
    document_type = Column(String, nullable=True, index=True)
    issued_date = Column(Date, nullable=True, index=True)
    _issued_date_str = Column('issued_date_str',String, nullable=True, index=True)
    case_status = Column(String, nullable=True, index=True)
    case_disposition = Column(String, nullable=True, index=True)

    case = relationship('Case', backref=backref('dscr', uselist=False))

    @hybrid_property
    def issued_date_str(self):
        return self._issued_date_str
    @issued_date_str.setter
    def issued_date_str(self,val):
        self.issued_date = date_from_str(val)
        self._issued_date_str = val

class DSCRCaseTable(CaseTable):
    @declared_attr
    def case_number(cls):
        return Column(String, ForeignKey('dscr.case_number', ondelete='CASCADE'), index=True)

class DSCRCharge(DSCRCaseTable, TableBase):
    __tablename__ = 'dscr_charges'
    dscr = relationship('DSCR', backref='charges')

    id = Column(Integer, primary_key=True)
    charge_number = Column(Integer)
    charge_description = Column(String, nullable=True)
    statute = Column(String, nullable=True)
    statute_description = Column(String, nullable=True)
    amended_date = Column(Date, nullable=True)
    _amended_date_str = Column('amended_date_str',String, nullable=True)
    cjis_code = Column(String, nullable=True)
    mo_pll = Column(String, nullable=True)
    probable_cause = Column(Boolean, default=False)
    incident_date_from = Column(Date, nullable=True)
    _incident_date_from_str = Column('incident_date_from_str',String, nullable=True)
    incident_date_to = Column(Date, nullable=True)
    _incident_date_to_str = Column('incident_date_to_str',String, nullable=True)
    victim_age = Column(Integer, nullable=True)
    plea = Column(String, nullable=True)
    disposition = Column(String, nullable=True)
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

class DSCRDefendant(DSCRCaseTable, Defendant, TableBase):
    __tablename__ = 'dscr_defendants'
    dscr = relationship('DSCR', backref='defendants')

class DSCRDefendantAlias(DSCRCaseTable, DefendantAlias, TableBase):
    __tablename__ = 'dscr_defendant_aliases'
    dscr = relationship('DSCR', backref='defendant_aliases')

class DSCRRelatedPerson(DSCRCaseTable, RelatedPerson, TableBase):
    __tablename__ = 'dscr_related_persons'
    dscr = relationship('DSCR', backref='related_persons')

class DSCREvent(DSCRCaseTable, Event, TableBase):
    __tablename__ = 'dscr_events'
    dscr = relationship('DSCR', backref='events')

class DSCRTrial(DSCRCaseTable, Trial, TableBase):
    __tablename__ = 'dscr_trials'
    dscr = relationship('DSCR', backref='trials')

class DSCRBailEvent(DSCRCaseTable, TableBase):
    __tablename__ = 'dscr_bail_events'
    dscr = relationship('DSCR', backref='bail_events')

    id = Column(Integer, primary_key=True)
    event_name = Column(String)
    date = Column(Date)
    _date_str = Column('date_str',String)
    bail_amount = Column(Numeric)
    code = Column(String)
    percentage_required = Column(Numeric)
    type_of_bond = Column(String)
    judge_id = Column(String)

    @hybrid_property
    def date_str(self):
        return self._date_str
    @date_str.setter
    def date_str(self,val):
        self.date = date_from_str(val)
        self._date_str = val
