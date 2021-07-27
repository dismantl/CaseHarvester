from .common import TableBase, CaseTable, date_from_str, RelatedPerson, Event, Trial
from sqlalchemy import Column, Date, Numeric, Integer, String, Boolean, ForeignKey, Time, Index
from sqlalchemy.orm import relationship, backref
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.ext.declarative import declared_attr
from datetime import datetime

class DSCIVIL(CaseTable, TableBase):
    __tablename__ = 'dscivil'

    id = Column(Integer, primary_key=True)
    court_system = Column(String)
    claim_type = Column(String,nullable=True)
    district_code = Column(Integer,nullable=True)
    location_code = Column(Integer,nullable=True)
    filing_date = Column(Date,nullable=True)
    _filing_date_str = Column('filing_date_str',String,nullable=True)
    case_status = Column(String,nullable=True)

    case = relationship('Case', backref=backref('dscivil', uselist=False))

    __table_args__ = (Index('ixh_dscivil_case_number', 'case_number', postgresql_using='hash'),)

    @hybrid_property
    def filing_date_str(self):
        return self._filing_date_str
    @filing_date_str.setter
    def filing_date_str(self,val):
        self.filing_date = date_from_str(val)
        self._filing_date_str = val

class DSCIVILCaseTable(CaseTable):
    @declared_attr
    def case_number(self):
        return Column(String, ForeignKey('dscivil.case_number', ondelete='CASCADE'))

class DSCIVILComplaint(DSCIVILCaseTable, TableBase):
    __tablename__ = 'dscivil_complaints'
    __table_args__ = (Index('ixh_dscivil_complaints_case_number', 'case_number', postgresql_using='hash'),)
    dscivil = relationship('DSCIVIL', backref='complaints')

    id = Column(Integer, primary_key=True)
    complaint_number = Column(Integer,nullable=True)
    plaintiff = Column(String,nullable=True)
    defendant = Column(String,nullable=True)
    complaint_type = Column(String,nullable=True)
    complaint_status = Column(String, nullable=True)
    status_date = Column(Date, nullable=True)
    _status_date_str = Column('status_date_str',String,nullable=True)
    filing_date = Column(Date,nullable=True)
    _filing_date_str = Column('filing_date_str',String,nullable=True)
    amount = Column(Numeric,nullable=True)
    last_activity_date = Column(Date,nullable=True)
    _last_activity_date_str = Column('last_activity_date_str',String,nullable=True)

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
    def last_activity_date_str(self):
        return self._last_activity_date_str
    @last_activity_date_str.setter
    def last_activity_date_str(self,val):
        self.last_activity_date = date_from_str(val)
        self._last_activity_date_str = val

class DSCIVILHearing(DSCIVILCaseTable, TableBase):
    __tablename__ = 'dscivil_hearings'
    __table_args__ = (Index('ixh_dscivil_hearings_case_number', 'case_number', postgresql_using='hash'),)
    dscivil_complaint = relationship('DSCIVILComplaint', backref='hearings')

    id = Column(Integer, primary_key=True)
    complaint_id = Column(Integer, ForeignKey('dscivil_complaints.id'))
    date = Column(Date,nullable=True)
    _date_str = Column('date_str',String)
    time = Column(Time, nullable=True)
    _time_str = Column('time_str', String, nullable=True)
    room = Column(String,nullable=True)
    location = Column(String)
    duration = Column(String,nullable=True) # TODO confirm type
    hearing_type = Column(String)

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

class DSCIVILJudgment(DSCIVILCaseTable, TableBase):
    __tablename__ = 'dscivil_judgments'
    __table_args__ = (Index('ixh_dscivil_judgments_case_number', 'case_number', postgresql_using='hash'),)
    dscivil_complaint = relationship('DSCIVILComplaint', backref='judgments')

    id = Column(Integer, primary_key=True)
    complaint_id = Column(Integer, ForeignKey('dscivil_complaints.id'))
    judgment_type = Column(String)
    judgment_date = Column(Date,nullable=True)
    _judgment_date_str = Column('judgment_date_str',String)
    judgment_amount = Column(Numeric)
    judgment_interest = Column(Numeric)
    costs = Column(Numeric)
    other_amounts = Column(Numeric)
    attorney_fees = Column(Numeric)
    post_interest_legal_rate = Column(Boolean)
    post_interest_contractual_rate = Column(Boolean)
    jointly_and_severally = Column(Integer,nullable=True)
    in_favor_of_defendant = Column(Boolean)
    possession_value = Column(Numeric)
    # possession_awardee = Column()
    possession_damages_value = Column(Numeric)
    value_sued_for = Column(Numeric)
    damages = Column(Numeric)
    # awardee = Column()
    dismissed_with_prejudice = Column(Boolean)
    replevin_detinue = Column(Numeric)
    recorded_lien_date = Column(Date,nullable=True)
    _recorded_lien_date_str = Column('recorded_lien_date_str',String,nullable=True)
    recorded_lien_date = Column(Date,nullable=True)
    _judgment_renewed_date_str = Column('judgment_renewed_date_str',String,nullable=True)
    renewed_lien_date = Column(Date,nullable=True)
    _renewed_lien_date_str = Column('renewed_lien_date_str',String,nullable=True)
    satisfaction_date = Column(Date,nullable=True)
    _satisfaction_date_str = Column('satisfaction_date_str',String,nullable=True)

    @hybrid_property
    def judgment_date_str(self):
        return self._judgment_date_str
    @judgment_date_str.setter
    def judgment_date_str(self,val):
        self.judgment_date = date_from_str(val)
        self._judgment_date_str = val

    @hybrid_property
    def recorded_lien_date_str(self):
        return self._recorded_lien_date_str
    @recorded_lien_date_str.setter
    def recorded_lien_date_str(self,val):
        self.recorded_lien_date = date_from_str(val)
        self._recorded_lien_date_str = val

    @hybrid_property
    def judgment_renewed_date_str(self):
        return self._judgment_renewed_date_str
    @judgment_renewed_date_str.setter
    def judgment_renewed_date_str(self,val):
        self.judgment_renewed_date = date_from_str(val)
        self._judgment_renewed_date_str = val

    @hybrid_property
    def renewed_lien_date_str(self):
        return self._renewed_lien_date_str
    @renewed_lien_date_str.setter
    def renewed_lien_date_str(self,val):
        self.renewed_lien_date = date_from_str(val)
        self._renewed_lien_date_str = val

    @hybrid_property
    def satisfaction_date_str(self):
        return self._satisfaction_date_str
    @satisfaction_date_str.setter
    def satisfaction_date_str(self,val):
        self.satisfaction_date = date_from_str(val)
        self._satisfaction_date_str = val

class DSCIVILRelatedPerson(DSCIVILCaseTable, RelatedPerson, TableBase):
    __tablename__ = 'dscivil_related_persons'
    __table_args__ = (Index('ixh_dscivil_related_persons_case_number', 'case_number', postgresql_using='hash'),)
    dscivil_complaint = relationship('DSCIVILComplaint', backref='related_persons')

    complaint_id = Column(Integer, ForeignKey('dscivil_complaints.id'))

class DSCIVILEvent(DSCIVILCaseTable, Event, TableBase):
    __tablename__ = 'dscivil_events'
    __table_args__ = (Index('ixh_dscivil_events_case_number', 'case_number', postgresql_using='hash'),)
    dscivil = relationship('DSCIVIL', backref='events')

    complaint_number = Column(Integer,nullable=True)

class DSCIVILTrial(DSCIVILCaseTable, Trial, TableBase):
    __tablename__ = 'dscivil_trials'
    __table_args__ = (Index('ixh_dscivil_trials_case_number', 'case_number', postgresql_using='hash'),)
    dscivil = relationship('DSCIVIL', backref='trials')
