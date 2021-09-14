from .common import TableBase, MetaColumn as Column, CaseTable, date_from_str
from sqlalchemy import Date, Numeric, Integer, String, Boolean, ForeignKey, Time, BigInteger, Index
from sqlalchemy.orm import relationship, backref
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.ext.declarative import declared_attr
from datetime import datetime

class MCCI(CaseTable, TableBase):
    '''Montgomery County Civil Cases'''
    __tablename__ = 'mcci'
    is_root = True

    id = Column(Integer, primary_key=True)
    court_system = Column(String)
    sub_type = Column(String, enum=True)
    filing_date = Column(Date)
    _filing_date_str = Column('filing_date_str',String)
    case_status = Column(String, enum=True)

    case = relationship('Case', backref=backref('mcci', uselist=False))

    __table_args__ = (Index('ixh_mcci_case_number', 'case_number', postgresql_using='hash'),)

    @hybrid_property
    def filing_date_str(self):
        return self._filing_date_str
    @filing_date_str.setter
    def filing_date_str(self,val):
        self.filing_date = date_from_str(val)
        self._filing_date_str = val

class MCCICaseTable(CaseTable):
    @declared_attr
    def case_number(self):
        return Column(String, ForeignKey('mcci.case_number', ondelete='CASCADE'), nullable=False)

class MCCIDefendant(MCCICaseTable, TableBase):
    __tablename__ = 'mcci_defendants'
    __table_args__ = (Index('ixh_mcci_defendants_case_number', 'case_number', postgresql_using='hash'),)
    mcci = relationship('MCCI', backref='defendants')

    id = Column(Integer, primary_key=True)
    name = Column(String)
    address = Column(String)
    city = Column(String)
    state = Column(String)
    zip_code = Column(String)
    attorneys = relationship('MCCIAttorney')

class MCCIAlias(MCCICaseTable, TableBase):
    __tablename__ = 'mcci_aliases'
    __table_args__ = (Index('ixh_mcci_aliases_case_number', 'case_number', postgresql_using='hash'),)
    mcci = relationship('MCCI', backref='aliases')

    id = Column(Integer, primary_key=True)
    name = Column(String)
    party = Column(String)

class MCCIPlaintiff(MCCICaseTable, TableBase):
    __tablename__ = 'mcci_plaintiffs'
    __table_args__ = (Index('ixh_mcci_plaintiffs_case_number', 'case_number', postgresql_using='hash'),)
    mcci = relationship('MCCI', backref='plaintiffs')

    id = Column(Integer, primary_key=True)
    name = Column(String)
    address = Column(String)
    city = Column(String)
    state = Column(String)
    zip_code = Column(String)
    attorneys = relationship('MCCIAttorney')
    resident_agent = relationship('MCCIResidentAgent')

class MCCIInterestedParty(MCCICaseTable, TableBase):
    __tablename__ = 'mcci_interested_parties'
    __table_args__ = (Index('ixh_mcci_interested_parties_case_number', 'case_number', postgresql_using='hash'),)
    mcci = relationship('MCCI', backref='interested_parties')

    id = Column(Integer, primary_key=True)
    name = Column(String)
    address = Column(String)
    city = Column(String)
    state = Column(String)
    zip_code = Column(String)

class MCCIWard(MCCICaseTable, TableBase):
    __tablename__ = 'mcci_wards'
    __table_args__ = (Index('ixh_mcci_wards_case_number', 'case_number', postgresql_using='hash'),)
    mcci = relationship('MCCI', backref='wards')

    id = Column(Integer, primary_key=True)
    name = Column(String)
    address = Column(String)
    city = Column(String)
    state = Column(String)
    zip_code = Column(String)
    attorneys = relationship('MCCIAttorney')

class MCCIGarnishee(MCCICaseTable, TableBase):
    __tablename__ = 'mcci_garnishees'
    __table_args__ = (Index('ixh_mcci_garnishees_case_number', 'case_number', postgresql_using='hash'),)
    mcci = relationship('MCCI', backref='garnishees')

    id = Column(Integer, primary_key=True)
    name = Column(String)
    address = Column(String)
    city = Column(String)
    state = Column(String)
    zip_code = Column(String)

class MCCIAttorney(MCCICaseTable, TableBase):
    __tablename__ = 'mcci_attorneys'
    __table_args__ = (Index('ixh_mcci_attorneys_case_number', 'case_number', postgresql_using='hash'),)
    mcci = relationship('MCCI', backref='attorneys')

    id = Column(Integer, primary_key=True)
    name = Column(String)
    appearance_date = Column(Date)
    _appearance_date_str = Column('appearance_date_str', String)
    removal_date = Column(Date)
    _removal_date_str = Column('removal_date_str', String)
    address = Column(String)
    city = Column(String)
    state = Column(String)
    zip_code = Column(String)
    phone = Column(String)
    defendant_id = Column(Integer, ForeignKey('mcci_defendants.id'))
    plaintiff_id = Column(Integer, ForeignKey('mcci_plaintiffs.id'))
    ward_id = Column(Integer, ForeignKey('mcci_wards.id'))

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

class MCCIResidentAgent(MCCICaseTable, TableBase):
    __tablename__ = 'mcci_resident_agents'
    __table_args__ = (Index('ixh_mcci_resident_agents_case_number', 'case_number', postgresql_using='hash'),)
    mcci = relationship('MCCI', backref='resident_agents')

    id = Column(Integer, primary_key=True)
    name = Column(String)
    address = Column(String)
    city = Column(String)
    state = Column(String)
    zip_code = Column(String)
    plaintiff_id = Column(Integer, ForeignKey('mcci_plaintiffs.id'))

class MCCIIssue(MCCICaseTable, TableBase):
    __tablename__ = 'mcci_issues'
    __table_args__ = (Index('ixh_mcci_issues_case_number', 'case_number', postgresql_using='hash'),)
    mcci = relationship('MCCI', backref='issues')

    id = Column(Integer, primary_key=True)
    issue = Column(String)

class MCCICourtSchedule(MCCICaseTable, TableBase):
    __tablename__ = 'mcci_court_schedule'
    __table_args__ = (Index('ixh_mcci_court_schedule_case_number', 'case_number', postgresql_using='hash'),)
    mcci = relationship('MCCI', backref='court_schedule')

    id = Column(Integer, primary_key=True)
    date = Column(Date)
    _date_str = Column('date_str', String)
    time = Column(Time)
    _time_str = Column('time_str', String)
    judge = Column(String)
    location = Column(String)
    courtroom = Column(String)
    description = Column(String)

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
            pass
        self._time_str = val

class MCCIJudgment(MCCICaseTable, TableBase):
    __tablename__ = 'mcci_judgments'
    __table_args__ = (Index('ixh_mcci_judgment_case_number', 'case_number', postgresql_using='hash'),)
    mcci = relationship('MCCI', backref='judgments')

    id = Column(Integer, primary_key=True)
    date = Column(Date)
    _date_str = Column('date_str', String)
    amount = Column(Numeric)
    debtor = Column(String)
    party_role = Column(String, enum=True)
    entered = Column(Date)
    _entered_str = Column('entered_str', String)
    satisfied = Column(Date)
    _satisfied_str = Column('satisfied_str', String)
    vacated = Column(Date)
    _vacated_str = Column('vacated_str', String)
    amended = Column(Date)
    _amended_str = Column('amended_str', String)
    renewed = Column(Date)
    _renewed_str = Column('renewed_str', String)

    @hybrid_property
    def date_str(self):
        return self._date_str
    @date_str.setter
    def date_str(self,val):
        self.date = date_from_str(val)
        self._date_str = val
    
    @hybrid_property
    def entered_str(self):
        return self._entered_str
    @entered_str.setter
    def entered_str(self,val):
        self.entered = date_from_str(val)
        self._entered_str = val

    @hybrid_property
    def satisfied_str(self):
        return self._satisfied_str
    @satisfied_str.setter
    def satisfied_str(self,val):
        self.satisfied = date_from_str(val)
        self._satisfied_str = val
    
    @hybrid_property
    def vacated_str(self):
        return self._vacated_str
    @vacated_str.setter
    def vacated_str(self,val):
        self.vacated = date_from_str(val)
        self._vacated_str = val
    
    @hybrid_property
    def amended_str(self):
        return self._amended_str
    @amended_str.setter
    def amended_str(self,val):
        self.amended = date_from_str(val)
        self._amended_str = val
    
    @hybrid_property
    def renewed_str(self):
        return self._renewed_str
    @renewed_str.setter
    def renewed_str(self,val):
        self.renewed = date_from_str(val)
        self._renewed_str = val

class MCCIDocket(MCCICaseTable, TableBase):
    __tablename__ = 'mcci_dockets'
    __table_args__ = (Index('ixh_mcci_dockets_case_number', 'case_number', postgresql_using='hash'),)
    mcci = relationship('MCCI', backref='dockets')

    id = Column(Integer, primary_key=True)
    date = Column(Date)
    _date_str = Column('date_str', String)
    docket_number = Column(Integer)
    docket_description = Column(String)
    docket_type = Column(String, enum=True)
    filed_by = Column(String, enum=True)
    docket_text = Column(String)
    status = Column(String)
    ruling_judge = Column(String)
    reference_docket = Column(String)

    @hybrid_property
    def date_str(self):
        return self._date_str
    @date_str.setter
    def date_str(self,val):
        self.date = date_from_str(val)
        self._date_str = val

class MCCIAudioMedia(MCCICaseTable, TableBase):
    __tablename__ = 'mcci_audio_media'
    __table_args__ = (Index('ixh_mcci_audio_media_case_number', 'case_number', postgresql_using='hash'),)
    mcci = relationship('MCCI', backref='audio_media')

    id = Column(Integer, primary_key=True)
    audio_media = Column(String)
    audio_start = Column(String)
    audio_stop = Column(String)
    docket_id = Column(Integer, ForeignKey('mcci_dockets.id'))