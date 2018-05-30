from ..db import TableBase
from .base import CaseDetailsParser, consumer, ParserError
from .common import CaseTable, date_from_str, RelatedPerson, Event, Trial
from sqlalchemy import Column, Date, Numeric, Integer, String, Boolean, ForeignKey, Time, BigInteger
from sqlalchemy.orm import relationship
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.ext.declarative import declared_attr
from datetime import *
import re

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

    @hybrid_property
    def filing_date_str(self):
        return self._filing_date_str
    @filing_date_str.setter
    def filing_date_str(self,val):
        self.filing_date = date_from_str(val)
        self._filing_date_str = val

class DSCIVILCaseTable(CaseTable):
    @declared_attr
    def case_number(cls):
        return Column(String, ForeignKey('dscivil.case_number', ondelete='CASCADE'), index=True)

class Complaint(DSCIVILCaseTable, TableBase):
    __tablename__ = 'dscivil_complaints'

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

class Hearing(DSCIVILCaseTable, TableBase):
    __tablename__ = 'dscivil_hearings'

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

    def __init__(self,case_number,complaint_id):
        self.case_number = case_number
        self.complaint_id = complaint_id

class Judgment(DSCIVILCaseTable, TableBase):
    __tablename__ = 'dscivil_judgments'

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
    post_interest_legal_rate = Column(Boolean,default=False,nullable=True)
    post_interest_contractual_rate = Column(Boolean,default=False,nullable=True)
    jointly_and_severally = Column(Integer,nullable=True)
    in_favor_of_defendant = Column(Boolean,default=False)
    possession_value = Column(Numeric)
    # possession_awardee = Column()
    possession_damages_value = Column(Numeric)
    value_sued_for = Column(Numeric)
    damages = Column(Numeric)
    # awardee = Column()
    dismissed_with_prejudice = Column(Boolean,default=False)
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

    def __init__(self,case_number,complaint_id):
        self.case_number = case_number
        self.complaint_id = complaint_id

class DSCIVILRelatedPerson(DSCIVILCaseTable, RelatedPerson, TableBase):
    __tablename__ = 'dscivil_related_persons'

    complaint_id = Column(Integer, ForeignKey('dscivil_complaints.id'))

    def __init__(self,case_number,complaint_id):
        self.case_number = case_number
        self.complaint_id = complaint_id

class DSCIVILEvent(DSCIVILCaseTable, Event, TableBase):
    __tablename__ = 'dscivil_events'

    complaint_number = Column(Integer,nullable=True)

class DSCIVILTrial(DSCIVILCaseTable, Trial, TableBase):
    __tablename__ = 'dscivil_trials'

class DSCIVILParser(CaseDetailsParser):
    def header(self, soup):
        header = soup.find('div',class_='Header')
        header.decompose()
        subheader = soup.find('a',string='Go Back Now').find_parent('div')
        subheader.decompose()

    def footer(self, soup):
        footer = soup.find('div',class_='InfoStatement',string=re.compile('This is an electronic case record'))
        footer.decompose()

    #########################################################
    # CASE INFORMATION
    #########################################################
    def case(self, db, soup):
        a = datetime.now()
        self.delete_previous(db, DSCIVIL)
        print("Took %s seconds to delete previous DSCIVIL" % (datetime.now() - a).total_seconds())

        section_header = self.first_level_header(soup,'Case Information')
        t1 = self.table_next_first_column_prompt(section_header,'Court System:')
        t2 = self.table_next_first_column_prompt(t1,'Case Number:')

        case = DSCIVIL(self.case_number)
        case.court_system = self.value_first_column(t1,'Court System:',remove_newlines=True)
        case_number = self.value_first_column(t2,'Case Number:')
        if case_number != self.case_number:
            raise ParserError('Case number "%s" in case details page does not match given: %s' % (case_number, self.case_number))
        case.claim_type = self.value_column(t2,'Claim Type:',ignore_missing=True)
        district_location_codes = self.value_first_column(t2,'District/Location Codes:',ignore_missing=True)
        if district_location_codes:
            case.district_code, case.location_code = district_location_codes.replace(' ','').split('/')
        case.filing_date_str = self.value_column(t2,'Filing Date:',ignore_missing=True)
        case.case_status = self.value_column(t2,'Case Status:',ignore_missing=True)
        db.add(case)

    #########################################################
    # Scheduled Events/Trial Information
    #########################################################
    @consumer
    def trial(self, db, soup):
        try:
            section_header = self.first_level_header(soup,'Scheduled Events/Trial Information')
        except ParserError:
            return
        t1 = self.table_next_first_column_prompt(section_header,'Date:')
        trial = DSCIVILTrial(self.case_number)
        trial.date_str = self.value_first_column(t1,'Date:')
        trial.time_str = self.value_column(t1,'Time:')
        trial.room = self.value_column(t1,'Room:',ignore_missing=True)
        trial.duration = self.value_first_column(t1,'Est. Duration:',ignore_missing=True)
        trial.location = self.value_first_column(t1,'Location:')
        db.add(trial)

    #########################################################
    # Complaint, Judgment, and Related Persons Information
    #########################################################
    @consumer
    def complaint(self, db, soup):
        section_header = self.first_level_header(soup,'Complaint, Judgment, and Related Persons Information')
        info_charge_statement = self.info_charge_statement(section_header)

        prev_obj = info_charge_statement
        while True:
            try:
                subsection = self.immediate_sibling(prev_obj,'span',class_='AltBodyWindowDcCivil')
                separator = self.immediate_sibling(subsection,'hr')
                prev_obj = separator
            except ParserError:
                break

            c = Complaint(self.case_number)
            try:
                subsection_header = self.third_level_header(subsection,'Complaint Information')
                t1 = self.immediate_sibling(subsection_header,'table')
            except ParserError:
                pass
            else:
                c.complaint_number = self.value_first_column(t1,'Complaint No:')
                vs = subsection.find('span',class_='Prompt',string='Vs:')
                self.mark_for_deletion(vs)
                plaintiff_span = self.immediate_previous_sibling(vs,'span',class_='Value')
                self.mark_for_deletion(plaintiff_span)
                c.plaintiff = self.format_value(plaintiff_span.string)
                defendant_span = self.immediate_sibling(vs,'span',class_='Value')
                self.mark_for_deletion(defendant_span)
                c.defendant = self.format_value(defendant_span.string)
                c.complaint_type = self.value_first_column(t1,'Type:')
                c.complaint_status = self.value_first_column(t1,'Complaint Status:',ignore_missing=True)
                c.status_date_str = self.value_first_column(t1,'Status Date:')
                c.filing_date_str = self.value_column(t1,'Filing Date:')
                c.amount = self.value_column(t1,'Amount',money=True) # no colon after label
                c.last_activity_date_str = self.value_column(t1,'Last Activity Date:')
            db.add(c)

            self.hearing(db, subsection, c.id)
            self.judgment(db, subsection, c.id)
            self.related_person(db, subsection, c.id)

    def hearing(self, db, subsection, complaint_id):
        try:
            subsection_header = self.third_level_header(subsection,'Scheduled Event/Hearing Information')
        except ParserError:
            return
        info_charge_statement = self.info_charge_statement(subsection_header)

        prev_obj = info_charge_statement
        while True:
            try:
                t1 = self.table_next_first_column_prompt(prev_obj,'Date:')
                separator = self.immediate_sibling(t1,'hr')
                prev_obj = separator
            except ParserError:
                break

            h = Hearing(self.case_number, complaint_id)
            h.date_str = self.value_first_column(t1,'Date:')
            h.time_str = self.value_column(t1,'Time:')
            h.room = self.value_column(t1,'Room:')
            h.location = self.value_first_column(t1,'Location:')
            h.duration = self.value_first_column(t1,'Est. Duration:')
            h.hearing_type = self.value_column(t1,'Type:')
            db.add(h)

    def judgment(self, db, subsection, complaint_id):
        try:
            subsection_header = self.third_level_header(subsection,'Judgment Information')
        except ParserError:
            return
        t1 = self.immediate_sibling(subsection_header,'table')

        j = Judgment(self.case_number, complaint_id)
        j.judgment_type = self.value_first_column(t1,'Judgment Type:')
        j.judgment_date_str = self.value_column(t1,'Judgment Date:')
        j.judgment_amount = self.value_first_column(t1,'Judgment Amount:',money=True)
        j.judgment_interest = self.value_column(t1,'Judgment Interest:',money=True)
        j.costs = self.value_column(t1,'Costs:',money=True)
        j.other_amounts = self.value_column(t1,'Other Amounts:',money=True)
        j.attorney_fees = self.value_first_column(t1,'Attorney Fees:',money=True)
        j.post_interest_legal_rate = self.value_column(t1,'Post Interest Legal Rate:',ignore_missing=True,boolean_value=True)
        j.post_interest_contractual_rate = self.value_column(t1,'Post Interest Contractual Rate:',ignore_missing=True,boolean_value=True)
        j.jointly_and_severally = self.value_column(t1,'Jointly and Severally:',ignore_missing=True)
        j.in_favor_of_defendant = self.value_column(t1,'In Favor of Defendant:',boolean_value=True)
        j.possession_value = self.value_first_column(t1,'Possession Of Property Claimed valued At:',money=True)
        awardee_fields = t1.find_all('span',class_='Prompt',string='Is Awarded To The:')
        possession_awardee = self.value_column(awardee_fields[0].find_parent('tr'),'Is Awarded To The:')
        # possession_awardee = self.value_column(t1,'Is Awarded To The:') # TODO add to table
        j.possession_damages_value = self.value_column(t1,'Together With Damages Of:',money=True)
        j.value_sued_for = self.value_first_column(t1,'Value Of Property Sued For:',money=True)
        j.damages = self.value_column(t1,'Plus Damages Of:',money=True)
        # awardee = self.value_column(t1,'Is Awarded To The:') # TODO add to table
        awardee = self.value_column(awardee_fields[1].find_parent('tr'),'Is Awarded To The:')
        j.dismissed_with_prejudice = self.value_column(t1,'Dismissed With Prejudice:',boolean_value=True)
        j.replevin_detinue = self.value_first_column(t1,'Replevin/Detinue Amount:',money=True)
        j.recorded_lien_date_str = self.value_first_column(t1,'Recorded Lien Date:')
        j.judgment_renewed_date_str = self.value_column(t1,'Judgment renewed Date:')
        j.renewed_lien_date_str = self.value_first_column(t1,'Renewed Lien Date:')
        j.satisfaction_date_str = self.value_column(t1,'Satisfaction Date:')
        db.add(j)

    def related_person(self, db, subsection, complaint_id):
        subsection_header = self.third_level_header(subsection,'Related Person Information')

        prev_obj = subsection_header
        while True:
            try:
                t1 = self.immediate_sibling(prev_obj,'table')
                separator = self.immediate_sibling(t1,'hr')
                try:
                    separator = self.immediate_sibling(separator,'hr') # sometimes there are two <hr>s in a row
                except ParserError:
                    pass
                prev_obj = separator
            except ParserError:
                break

            p = DSCIVILRelatedPerson(self.case_number, complaint_id)
            p.name = self.value_first_column(t1,'Name:')
            p.connection = self.value_first_column(t1,'Connection to Complaint:')
            if t1.find('table'): # Address is inside another table
                p.address_1 = self.value_first_column(t1,'Address:',ignore_missing=True)
                address_fields = t1.find_all('span',class_='FirstColumnPrompt',string='Address:')
                if len(address_fields) == 2:
                    p.address_2 = self.value_first_column(address_fields[1].find_parent('tr'),'Address:')
                p.city = self.value_first_column(t1,'City:')
                p.state = self.value_column(t1,'State:')
                p.zip_code = self.value_column(t1,'Zip Code:')
            try:
                attorney_row = self.row_label(t1,'If Person is Attorney:')
            except ParserError:
                pass
            else:
                p.attorney_code = self.value_multi_column(attorney_row,'Attorney Code:')
                p.attorney_firm = self.value_column(attorney_row,"Attorney's Firm:")
            db.add(p)

    #########################################################
    # Case History Information
    #########################################################
    @consumer
    def case_history(self, db, soup):
        try:
            section_header = soup\
                .find('i',string='Case History Information')\
                .find_parent('h5')
        except AttributeError:
            return
        self.mark_for_deletion(section_header)
        info_charge_statement = self.info_charge_statement(section_header)

        prev_obj = info_charge_statement
        while True:
            try:
                t1 = self.table_next_first_column_prompt(prev_obj,'Type:')
                separator = self.immediate_sibling(t1,'hr')
                prev_obj = separator
            except ParserError:
                break

            event = DSCIVILEvent(self.case_number)
            event.event_name = self.value_first_column(t1,'Type:')
            event.complaint_number = self.value_column(t1,'Complaint No.:')
            event.date_str = self.value_first_column(t1,'Date:')
            event.comment = self.value_column(t1,'Comment:')
            db.add(event)
