from .common import TableBase, CaseTable, date_from_str, Defendant, DefendantAlias, RelatedPerson, Trial, Event
from sqlalchemy import Column, Date, Numeric, Integer, String, Boolean, ForeignKey, Index
from sqlalchemy.orm import relationship, backref
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.ext.declarative import declared_attr

class DSK8(CaseTable, TableBase):
    __tablename__ = 'dsk8'

    id = Column(Integer, primary_key=True)
    court_system = Column(String)
    case_status = Column(String)
    status_date = Column(Date, nullable=True)
    _status_date_str = Column('status_date_str',String)
    tracking_number = Column(String, nullable=True)
    complaint_number = Column(String, nullable=True)
    district_case_number = Column(String, nullable=True) # TODO eventually make a ForeignKey relation
    filing_date = Column(Date, nullable=True)
    _filing_date_str = Column('filing_date_str',String)
    incident_date = Column(Date, nullable=True)
    _incident_date_str = Column('incident_date_str',String)

    case = relationship('Case', backref=backref('dsk8', uselist=False))

    __table_args__ = (Index('ixh_dsk8_case_number', 'case_number', postgresql_using='hash'),)

    @hybrid_property
    def status_date_str(self):
        return self._status_date_str
    @status_date_str.setter
    def status_date_str(self,val):
        self.status_date = date_from_str(val)
        self._status_date_str = val

    @hybrid_property
    def filing_date_str(self):
        return self._filing_date_str
    @filing_date_str.setter
    def filing_date_str(self,val):
        self.filing_date = date_from_str(val)
        self._filing_date_str = val

    @hybrid_property
    def incident_date_str(self):
        return self._incident_date_str
    @incident_date_str.setter
    def incident_date_str(self,val):
        self.incident_date = date_from_str(val)
        self._incident_date_str = val

class DSK8CaseTable(CaseTable):
    @declared_attr
    def case_number(self):
        return Column(String, ForeignKey('dsk8.case_number', ondelete='CASCADE'))

class DSK8Charge(DSK8CaseTable, TableBase):
    __tablename__ = 'dsk8_charges'
    __table_args__ = (Index('ixh_dsk8_charges_case_number', 'case_number', postgresql_using='hash'),)

    id = Column(Integer, primary_key=True)
    case_number = Column(String, nullable=False)
    charge_number = Column(Integer)
    expunged = Column(Boolean, nullable=False, server_default='false')
    cjis_traffic_code = Column(String, nullable=True)
    arrest_citation_number = Column(String, nullable=True)
    description = Column(String)
    plea = Column(String, nullable=True)
    plea_date = Column(Date, nullable=True)
    _plea_date_str = Column('plea_date_str', String, nullable=True)
    disposition = Column(String)
    disposition_date = Column(Date, nullable=True)
    _disposition_date_str = Column('disposition_date_str', String)
    verdict = Column(String, nullable=True)
    verdict_date = Column(Date, nullable=True)
    _verdict_date_str = Column('verdict_date_str', String, nullable=True)
    court_costs = Column(Numeric, nullable=True)
    fine = Column(Numeric, nullable=True)
    sentence_starts = Column(Date, nullable=True)
    _sentence_starts_str = Column('sentence_starts_str', String, nullable=True)
    sentence_date = Column(Date, nullable=True)
    _sentence_date_str = Column('sentence_date_str', String, nullable=True)
    sentence_term = Column(String, nullable=True)
    sentence_years = Column(Integer, nullable=True)
    sentence_months = Column(Integer, nullable=True)
    sentence_days = Column(Integer, nullable=True)
    confinement = Column(String, nullable=True)
    suspended_years = Column(Integer, nullable=True)
    suspended_months = Column(Integer, nullable=True)
    suspended_days = Column(Integer, nullable=True)
    probation_years = Column(Integer, nullable=True)
    probation_months = Column(Integer, nullable=True)
    probation_days = Column(Integer, nullable=True)
    probation_type= Column(String, nullable=True)

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
    def verdict_date_str(self):
        return self._verdict_date_str
    @verdict_date_str.setter
    def verdict_date_str(self,val):
        self.verdict_date = date_from_str(val)
        self._verdict_date_str = val

    @hybrid_property
    def sentence_starts_str(self):
        return self._sentence_starts_str
    @sentence_starts_str.setter
    def sentence_starts_str(self,val):
        self.sentence_starts = date_from_str(val)
        self._sentence_starts_str = val

    @hybrid_property
    def sentence_date_str(self):
        return self._sentence_date_str
    @sentence_date_str.setter
    def sentence_date_str(self,val):
        self.sentence_date = date_from_str(val)
        self._sentence_date_str = val

class DSK8BailAndBond(DSK8CaseTable, TableBase):
    __tablename__ = 'dsk8_bail_and_bond'
    __table_args__ = (Index('ixh_dsk8_bail_and_bond_case_number', 'case_number', postgresql_using='hash'),)
    dsk8 = relationship('DSK8', backref='bail_and_bonds')

    id = Column(Integer, primary_key=True)
    bail_amount = Column(Integer)
    bail_number = Column(String)
    set_date = Column(Date, nullable=True)
    _set_date_str = Column('set_date_str', String)
    release_date = Column(Date, nullable=True)
    _release_date_str = Column('release_date_str', String, nullable=True)
    release_reason = Column(String, nullable=True)
    bail_set_location = Column(String)
    bond_type = Column(String)
    ground_rent = Column(Numeric, nullable=True)
    mortgage = Column(Numeric, nullable=True)
    property_value = Column(Numeric, nullable=True)
    property_address = Column(String, nullable=True)
    forfeit_date = Column(Date, nullable=True)
    _forfeit_date_str = Column('forfeit_date_str', String, nullable=True)
    forfeit_extended_date = Column(Date, nullable=True)
    _forfeit_extended_date_str = Column('forfeit_extended_date_str', String, nullable=True)
    days_extended = Column(Integer, nullable=True)
    bondsman_company_name = Column(String)
    judgment_date = Column(Date, nullable=True)
    _judgment_date_str = Column('judgment_date_str', String, nullable=True)

    @hybrid_property
    def set_date_str(self):
        return self._set_date_str
    @set_date_str.setter
    def set_date_str(self,val):
        self.set_date = date_from_str(val)
        self._set_date_str = val

    @hybrid_property
    def release_date_str(self):
        return self._release_date_str
    @release_date_str.setter
    def release_date_str(self,val):
        self.release_date = date_from_str(val)
        self._release_date_str = val

    @hybrid_property
    def forfeit_date_str(self):
        return self._forfeit_date_str
    @forfeit_date_str.setter
    def forfeit_date_str(self,val):
        self.forfeit_date = date_from_str(val)
        self._forfeit_date_str = val

    @hybrid_property
    def forfeit_extended_date_str(self):
        return self._forfeit_extended_date_str
    @forfeit_extended_date_str.setter
    def forfeit_extended_date_str(self,val):
        self.forfeit_extended_date = date_from_str(val)
        self._forfeit_extended_date_str = val

    @hybrid_property
    def judgment_date_str(self):
        return self._judgment_date_str
    @judgment_date_str.setter
    def judgment_date_str(self,val):
        self.judgment_date = date_from_str(val)
        self._judgment_date_str = val

class DSK8Bondsman(DSK8CaseTable, TableBase):
    __tablename__ = 'dsk8_bondsman'
    __table_args__ = (Index('ixh_dsk8_bondsman_case_number', 'case_number', postgresql_using='hash'),)
    bail_and_bond = relationship('DSK8BailAndBond', backref='bondsman')

    id = Column(Integer, primary_key=True)
    bail_and_bond_id = Column(Integer, ForeignKey('dsk8_bail_and_bond.id'))
    name = Column(String, nullable=True)
    address_1 = Column(String, nullable=True)
    city = Column(String, nullable=True)
    state = Column(String, nullable=True)
    zip_code = Column(String, nullable=True)

class DSK8Defendant(DSK8CaseTable, Defendant, TableBase):
    __tablename__ = 'dsk8_defendants'
    __table_args__ = (Index('ixh_dsk8_defendants_case_number', 'case_number', postgresql_using='hash'),)
    dsk8 = relationship('DSK8', backref='defendants')

class DSK8DefendantAlias(DSK8CaseTable, DefendantAlias, TableBase):
    __tablename__ = 'dsk8_defendant_aliases'
    __table_args__ = (Index('ixh_dsk8_defendant_aliases_case_number', 'case_number', postgresql_using='hash'),)
    dsk8 = relationship('DSK8', backref='defendant_aliases')

class DSK8RelatedPerson(DSK8CaseTable, RelatedPerson, TableBase):
    __tablename__ = 'dsk8_related_persons'
    __table_args__ = (Index('ixh_dsk8_related_persons_case_number', 'case_number', postgresql_using='hash'),)
    dsk8 = relationship('DSK8', backref='related_persons')

class DSK8Event(DSK8CaseTable, Event, TableBase):
    __tablename__ = 'dsk8_events'
    __table_args__ = (Index('ixh_dsk8_events_case_number', 'case_number', postgresql_using='hash'),)
    dsk8 = relationship('DSK8', backref='events')

class DSK8Trial(DSK8CaseTable, Trial, TableBase):
    __tablename__ = 'dsk8_trials'
    __table_args__ = (Index('ixh_dsk8_trials_case_number', 'case_number', postgresql_using='hash'),)
    dsk8 = relationship('DSK8', backref='trials')
