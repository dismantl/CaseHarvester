from sqlalchemy.sql.schema import Table
from .common import TableBase, MetaColumn as Column, CaseTable, date_from_str
from sqlalchemy import Date, Numeric, Integer, String, Boolean, ForeignKey, Index, Time
from sqlalchemy.orm import relationship, backref
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.ext.declarative import declared_attr
from datetime import datetime

class PG(CaseTable, TableBase):
    '''Prince George's County Circuit Court Criminal Cases'''
    __tablename__ = 'pg'
    is_root = True

    id = Column(Integer, primary_key=True)
    court_system = Column(String, enum=True)
    case_type = Column(String, enum=True)
    case_description = Column(String)
    filing_date = Column(Date)
    _filing_date_str = Column('filing_date_str',String)
    case_status = Column(String, enum=True)

    case = relationship('Case', backref=backref('pg', uselist=False))

    __table_args__ = (Index('ixh_pg_case_number', 'case_number', postgresql_using='hash'),)

    @hybrid_property
    def filing_date_str(self):
        return self._filing_date_str
    @filing_date_str.setter
    def filing_date_str(self,val):
        self.filing_date = date_from_str(val)
        self._filing_date_str = val

class PGCaseTable(CaseTable):
    @declared_attr
    def case_number(self):
        return Column(String, ForeignKey('pg.case_number', ondelete='CASCADE'), nullable=False)

class PGCharge(PGCaseTable, TableBase):
    __tablename__ = 'pg_charges'
    __table_args__ = (Index('ixh_pg_charges_case_number', 'case_number', postgresql_using='hash'),)
    pg = relationship('PG', backref='charges')

    id = Column(Integer, primary_key=True)
    charge_number = Column(Integer)
    expunged = Column(Boolean, nullable=False, server_default='false')
    charge = Column(String)
    charge_code = Column(String)
    offense_date = Column(Date)
    _offense_date_str = Column('offense_date_str',String)
    arrest_tracking_number = Column(String)
    disposition = Column(String, enum=True)
    disposition_date = Column(Date)
    _disposition_date_str = Column('disposition_date_str',String)

    @hybrid_property
    def offense_date_str(self):
        return self._offense_date_str
    @offense_date_str.setter
    def offense_date_str(self,val):
        self.offense_date = date_from_str(val)
        self._offense_date_str = val

    @hybrid_property
    def disposition_date_str(self):
        return self._disposition_date_str
    @disposition_date_str.setter
    def disposition_date_str(self,val):
        self.disposition_date = date_from_str(val)
        self._disposition_date_str = val

class PGPlaintiff(PGCaseTable, TableBase):
    __tablename__ = 'pg_plaintiffs'
    __table_args__ = (Index('ixh_pg_plaintiffs_case_number', 'case_number', postgresql_using='hash'),)
    pg = relationship('PG', backref='plaintiffs')

    id = Column(Integer, primary_key=True)
    party_number = Column(Integer)
    name = Column(String)
    address_1 = Column(String)
    address_2 = Column(String)
    city = Column(String)
    state = Column(String)
    zip_code = Column(String)

class PGDefendant(PGCaseTable, TableBase):
    __tablename__ = 'pg_defendants'
    __table_args__ = (Index('ixh_pg_defendants_case_number', 'case_number', postgresql_using='hash'),)
    pg = relationship('PG', backref='defendants')

    id = Column(Integer, primary_key=True)
    party_number = Column(Integer)
    name = Column(String, redacted=True)
    address_1 = Column(String, redacted=True)
    address_2 = Column(String, redacted=True)
    city = Column(String)
    state = Column(String)
    zip_code = Column(String)

class PGDefendantAlias(PGCaseTable, TableBase):
    __tablename__ = 'pg_defendant_aliases'
    __table_args__ = (Index('ixh_pg_defendant_aliases_case_number', 'case_number', postgresql_using='hash'),)
    pg = relationship('PG', backref='defendant_aliases')

    id = Column(Integer, primary_key=True)
    alias_name = Column(String)

class PGAttorney(PGCaseTable, TableBase):
    __tablename__ = 'pg_attorneys'
    __table_args__ = (Index('ixh_pg_attorneys_case_number', 'case_number', postgresql_using='hash'),)
    pg = relationship('PG', backref='attorneys')

    id = Column(Integer, primary_key=True)
    name = Column(String)
    attorney_type = Column(String, enum=True)
    address_1 = Column(String)
    city = Column(String)
    state = Column(String)
    zip_code = Column(String)

class PGOtherParty(PGCaseTable, TableBase):
    __tablename__ = 'pg_other_parties'
    __table_args__ = (Index('ixh_pg_other_parties_case_number', 'case_number', postgresql_using='hash'),)
    pg = relationship('PG', backref='other_parties')

    id = Column(Integer, primary_key=True)
    party_type = Column(String, enum=True)
    party_number = Column(Integer)
    name = Column(String)

class PGCourtSchedule(PGCaseTable, TableBase):
    __tablename__ = 'pg_court_schedule'
    __table_args__ = (Index('ixh_pg_court_schedule_case_number', 'case_number', postgresql_using='hash'),)
    pg = relationship('PG', backref='court_schedule')

    id = Column(Integer, primary_key=True)
    event_type = Column(String, enum=True)
    event_date = Column(Date)
    _event_date_str = Column('event_date_str', String)
    time = Column(Time)
    _time_str = Column('time_str', String)
    result = Column(String)
    result_date = Column(Date)
    _result_date_str = Column('result_date_str', String)

    @hybrid_property
    def event_date_str(self):
        return self._event_date_str
    @event_date_str.setter
    def event_date_str(self,val):
        self.event_date = date_from_str(val)
        self._event_date_str = val

    @hybrid_property
    def time_str(self):
        return self._time_str
    @time_str.setter
    def time_str(self,val):
        try:
            self.time = datetime.strptime(val,'%H:%M:%S').time()
        except:
            pass
        self._time_str = val
    
    @hybrid_property
    def result_date_str(self):
        return self._result_date_str
    @result_date_str.setter
    def result_date_str(self,val):
        self.result_date = date_from_str(val)
        self._result_date_str = val

class PGDocket(PGCaseTable, TableBase):
    __tablename__ = 'pg_dockets'
    __table_args__ = (Index('ixh_pg_dockets_case_number', 'case_number', postgresql_using='hash'),)
    pg = relationship('PG', backref='dockets')

    id = Column(Integer, primary_key=True)
    date = Column(Date)
    _date_str = Column('date_str', String)
    document_name = Column(String)
    docket_text = Column(String)

    @hybrid_property
    def date_str(self):
        return self._date_str
    @date_str.setter
    def date_str(self,val):
        self.date = date_from_str(val)
        self._date_str = val