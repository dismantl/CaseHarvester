from .common import TableBase, CaseTable, Trial, Event, date_from_str, Defendant, DefendantAlias, RelatedPerson
from sqlalchemy import Column, Date, Numeric, Integer, String, Boolean, ForeignKey, Time, BigInteger, Index
from sqlalchemy.orm import relationship, backref
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.ext.declarative import declared_attr

class DSCR(CaseTable, TableBase):
    __tablename__ = 'dscr'

    id = Column(Integer, primary_key=True)
    court_system = Column(String)
    tracking_number = Column(String, nullable=True)
    case_type = Column(String, nullable=True)
    district_code = Column(Integer, nullable=True)
    location_code = Column(Integer, nullable=True)
    document_type = Column(String, nullable=True)
    issued_date = Column(Date, nullable=True)
    _issued_date_str = Column('issued_date_str',String, nullable=True)
    case_status = Column(String, nullable=True)
    case_disposition = Column(String, nullable=True)

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
        return Column(String, ForeignKey('dscr.case_number', ondelete='CASCADE'))

class DSCRCharge(CaseTable, TableBase):
    __tablename__ = 'dscr_charges'
    __table_args__ = (Index('ixh_dscr_charges_case_number', 'case_number', postgresql_using='hash'),)

    id = Column(Integer, primary_key=True)
    case_number = Column(String, nullable=False)
    charge_number = Column(Integer)
    possibly_expunged = Column(Boolean, nullable=False, server_default='false')
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
    __table_args__ = (Index('ixh_dscr_defendants_case_number', 'case_number', postgresql_using='hash'),)
    dscr = relationship('DSCR', backref='defendants')

class DSCRDefendantAlias(DSCRCaseTable, DefendantAlias, TableBase):
    __tablename__ = 'dscr_defendant_aliases'
    __table_args__ = (Index('ixh_dscr_defendant_aliases_case_number', 'case_number', postgresql_using='hash'),)
    dscr = relationship('DSCR', backref='defendant_aliases')

class DSCRRelatedPerson(DSCRCaseTable, RelatedPerson, TableBase):
    __tablename__ = 'dscr_related_persons'
    __table_args__ = (Index('ixh_dscr_related_persons_case_number', 'case_number', postgresql_using='hash'),)
    dscr = relationship('DSCR', backref='related_persons')

class DSCREvent(DSCRCaseTable, Event, TableBase):
    __tablename__ = 'dscr_events'
    __table_args__ = (Index('ixh_dscr_events_case_number', 'case_number', postgresql_using='hash'),)
    dscr = relationship('DSCR', backref='events')

class DSCRTrial(DSCRCaseTable, Trial, TableBase):
    __tablename__ = 'dscr_trials'
    __table_args__ = (Index('ixh_dscr_trials_case_number', 'case_number', postgresql_using='hash'),)
    dscr = relationship('DSCR', backref='trials')

class DSCRBailEvent(DSCRCaseTable, TableBase):
    __tablename__ = 'dscr_bail_events'
    __table_args__ = (Index('ixh_dscr_bail_events_case_number', 'case_number', postgresql_using='hash'),)
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
