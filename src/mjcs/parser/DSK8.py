from ..db import TableBase
from .base import CaseDetailsParser, consumer, ParserError
from .common import CaseTable, date_from_str, Defendant, DefendantAlias, RelatedPerson, Trial, Event
from sqlalchemy import Column, Date, Numeric, Integer, String, Boolean, ForeignKey, Time, BigInteger
from sqlalchemy.orm import relationship
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.ext.declarative import declared_attr
from datetime import *
import re

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
    def case_number(cls):
        return Column(String, ForeignKey('dsk8.case_number', ondelete='CASCADE'), index=True)

class DSK8Charge(DSK8CaseTable, TableBase):
    __tablename__ = 'dsk8_charges'

    id = Column(Integer, primary_key=True)
    charge_number = Column(Integer)
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

    id = Column(Integer, primary_key=True)
    bail_and_bond_id = Column(Integer, ForeignKey('dsk8_bail_and_bond.id'))
    name = Column(String, nullable=True)
    address_1 = Column(String, nullable=True)
    city = Column(String, nullable=True)
    state = Column(String, nullable=True)
    zip_code = Column(String, nullable=True)

    def __init__(self,case_number,bail_and_bond_id):
        self.case_number = case_number
        self.bail_and_bond_id = bail_and_bond_id

class DSK8Defendant(DSK8CaseTable, Defendant, TableBase):
    __tablename__ = 'dsk8_defendants'

class DSK8DefendantAlias(DSK8CaseTable, DefendantAlias, TableBase):
    __tablename__ = 'dsk8_defendant_aliases'

class DSK8RelatedPerson(DSK8CaseTable, RelatedPerson, TableBase):
    __tablename__ = 'dsk8_related_persons'

class DSK8Event(DSK8CaseTable, Event, TableBase):
    __tablename__ = 'dsk8_events'

class DSK8Trial(DSK8CaseTable, Trial, TableBase):
    __tablename__ = 'dsk8_trials'

class DSK8Parser(CaseDetailsParser):
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
        self.delete_previous(db, DSK8)
        print("Took %s seconds to delete previous DSK8" % (datetime.now() - a).total_seconds())

        case = DSK8(self.case_number)
        section_header = self.second_level_header(soup,'Case Information')

        t1 = self.table_next_first_column_prompt(section_header,'Court System:')
        t2 = t1.find('table') # tables 2 and 3 are actually inside table 1
        t3 = self.immediate_sibling(t2,'table')

        case.court_system = self.value_first_column(t1,'Court System:',remove_newlines=True)
        case_number = self.value_first_column(t1,'Case Number:')
        if case_number != self.case_number:
            raise ParserError('Case number "%s" in case details page does not match given: %s' % (case_number, self.case_number))
        case.case_status = self.value_column(t1,'Case Status:')
        case.status_date_str = self.value_first_column(t1, 'Status Date:')

        case.tracking_number = self.value_first_column(t2,'Tracking Number:',ignore_missing=True)
        case.complaint_number = self.value_first_column(t2,'Complaint No:',ignore_missing=True)
        case.district_case_number = self.value_first_column(t2,'District Case No:',ignore_missing=True)

        case.filing_date_str = self.value_first_column(t3,'Filing Date:',ignore_missing=True)
        case.incident_date_str = self.value_multi_column(t3,'Incident Date:',ignore_missing=True)
        db.add(case)

    #########################################################
    # DEFENDENT INFORMATION
    #########################################################
    @consumer
    def defendant_and_aliases(self, db, soup):
        section_header = self.second_level_header(soup,'Defendant Information')
        defendant = DSK8Defendant(self.case_number)

        t1 = self.table_next_first_column_prompt(section_header,'Defendant Name:')
        t2 = self.immediate_sibling(t1,'table')
        t3 = self.immediate_sibling(t2,'table')
        t4 = self.immediate_sibling(t3,'table')

        defendant.name = self.value_first_column(t1,'Defendant Name:')

        defendant.race = self.value_combined_first_column(t2,'Race:',ignore_missing=True)
        defendant.sex = self.value_column(t2,'Sex:',ignore_missing=True)
        defendant.DOB_str = self.value_combined_first_column(t2,'DOB:',ignore_missing=True)

        defendant.address_1 = self.value_combined_first_column(t3,'Address:',ignore_missing=True)

        defendant.city = self.value_first_column(t4,'City:',ignore_missing=True)
        defendant.state = self.value_column(t4,'State:',ignore_missing=True)
        defendant.zip_code = self.value_column(t4,'Zip Code:',ignore_missing=True)
        db.add(defendant)

        # check for ALIAS tables
        separator = self.immediate_sibling(t4,'hr')
        prev_obj = separator
        while True:
            try:
                t1 = self.table_next_first_column_prompt(prev_obj,'ALIAS:')
                t2 = self.immediate_sibling(t1,'table')
                t3 = self.immediate_sibling(t2,'table')
                separator = self.immediate_sibling(t3,'hr')
                prev_obj = separator
            except ParserError:
                break

            if list(t1.stripped_strings) or list(t2.stripped_strings) or list(t3.stripped_strings):
                alias = DSK8DefendantAlias(self.case_number)
                alias.alias_name = self.value_first_column(t1,'ALIAS:',ignore_missing=True)
                alias.address_1 = self.value_combined_first_column(t2,'Address:',ignore_missing=True)
                alias.city = self.value_first_column(t3,'City:',ignore_missing=True)
                alias.state = self.value_column(t3,'State:',ignore_missing=True)
                alias.zip_code = self.value_column(t3,'Zip Code:',ignore_missing=True)
                db.add(alias)

                # stupid edge case (e.g. 115027015)
                addresses = t2.find_all('span',class_='FirstColumnPrompt',string='Address:')
                if len(addresses) > 1:
                    for address in addresses[1:]:
                        new_alias = DSK8DefendantAlias(self.case_number)
                        new_alias.address_1 = self.value_combined_first_column(address.find_parent('td'),'Address:')
                        new_alias.city = alias.city
                        new_alias.state = alias.state
                        new_alias.zip_code = alias.zip_code
                        db.add(new_alias)

    #########################################################
    # CHARGE AND DISPOSITION INFORMATION
    #########################################################
    @consumer
    def charge_and_disposition(self, db, soup):
        try:
            section_header = self.second_level_header(soup,'Charge and Disposition Information')
        except ParserError:
            return
        info_charge_statement = self.info_charge_statement(section_header)

        prev_obj = info_charge_statement
        while True:
            try:
                section = self.immediate_sibling(prev_obj,'div',class_='AltBodyWindow1')
                separator = self.immediate_sibling(section,'hr')
                prev_obj = separator
            except ParserError:
                break

            charge = DSK8Charge(self.case_number)
            charge.charge_number = self.value_first_column(section,'Charge No:')
            charge.cjis_traffic_code = self.value_first_column(section,'CJIS/Traffic Code:',ignore_missing=True)
            charge.arrest_citation_number = self.value_multi_column(section,'Arrest/Citation No:',ignore_missing=True)
            charge.description = self.value_first_column(section,'Description:')
            charge.plea = self.value_first_column(section,'Plea:',ignore_missing=True)
            charge.plea_date_str = self.value_combined_first_column(section,'Plea Date:',ignore_missing=True)
            charge.disposition = self.value_first_column(section,'Disposition:',ignore_missing=True)
            charge.disposition_date_str = self.value_first_column(section,'Disposition Date:',ignore_missing=True)
            charge.verdict = self.value_first_column(section,'Verdict:',ignore_missing=True)
            charge.verdict_date_str = self.value_column(section,'Verdict Date:',ignore_missing=True)
            charge.sentence_starts_str = self.value_first_column(section,'Sentence Starts:',ignore_missing=True)
            charge.sentence_date_str = self.value_first_column(section,'Sentence Date:',ignore_missing=True)
            charge.sentence_term = self.value_first_column(section,'Sentence Term:',ignore_missing=True)
            charge.court_costs = self.value_combined_first_column(section,'Court Costs:',ignore_missing=True,money=True)
            charge.fine = self.value_column(section,'Fine:',ignore_missing=True,money=True)

            try:
                sentence_table = self.row_label(section,'Sentence Time:')
            except ParserError:
                pass
            else:
                charge.sentence_years = self.value_column(sentence_table,'Yrs:')
                charge.sentence_months = self.value_column(sentence_table,'Mos:')
                charge.sentence_days = self.value_column(sentence_table,'Days:')
                charge.confinement = self.value_column(sentence_table,'Confinement') # has space between label and :

            try:
                suspended_table = self.row_label(section,'Suspended Time:')
            except ParserError:
                pass
            else:
                charge.suspended_years = self.value_column(suspended_table,'Yrs:')
                charge.suspended_months = self.value_column(suspended_table,'Mos:')
                charge.suspended_days = self.value_column(suspended_table,'Days:')

            try:
                probation_table = self.row_label(section,'Probation Time:')
            except ParserError:
                pass
            else:
                charge.probation_years = self.value_column(probation_table,'Yrs:')
                charge.probation_months = self.value_column(probation_table,'Mos:')
                charge.probation_days = self.value_column(probation_table,'Days:')
                charge.probation_type = self.value_column(probation_table,'Type:')

            db.add(charge)

    #########################################################
    # SCHEDULE INFORMATION
    #########################################################
    @consumer
    def trial(self, db, soup):
        try:
            section_header = self.second_level_header(soup,'Schedule Information')
        except ParserError:
            return

        prev_obj = section_header
        while True:
            try:
                t1 = self.table_next_first_column_prompt(prev_obj,'Court Date:')
                t2 = self.table_next_first_column_prompt(t1,'Court Location:')
                separator = self.immediate_sibling(t2,'hr')
                prev_obj = separator
            except ParserError:
                break
            trial = DSK8Trial(self.case_number)
            trial.date_str = self.value_first_column(t1,'Court Date:')
            trial.time_str = self.value_column(t1,'Court Time:')
            trial.room = self.value_column(t1,'Room:')
            trial.location = self.value_first_column(t2,'Court Location:')
            trial.reason = self.value_first_column(t2,'Reason:')
            db.add(trial)

    #########################################################
    # RELATED PERSON INFORMATION
    #########################################################
    @consumer
    def related_person(self, db, soup):
        try:
            section_header = self.second_level_header(soup,'Related Person Information')
        except ParserError:
            return

        # Each related person section is three <table>s followed by an <hr>
        # Some tables may be empty, so check for .stripped_strings
        prev_obj = section_header
        while True:
            try:
                t1 = self.immediate_sibling(prev_obj,'table')
                t2 = self.immediate_sibling(t1,'table')
                t3 = self.immediate_sibling(t2,'table')
                separator = self.immediate_sibling(t3,'hr')
                prev_obj = separator
            except ParserError:
                break
            person = DSK8RelatedPerson(self.case_number)
            person.name = self.value_combined_first_column(t1,'Name:') # Can be null
            person.connection = self.value_combined_first_column(t1,'Connection:')
            person.address_1 = self.value_combined_first_column(t2,'Address:',ignore_missing=True)
            person.city = self.value_first_column(t3,'City:',ignore_missing=True)
            person.state = self.value_column(t3,'State:',ignore_missing=True)
            person.zip_code = self.value_column(t3,'Zip Code:',ignore_missing=True)
            db.add(person)

            # stupid edge case (115175016)
            addresses = t2.find_all('span',class_='FirstColumnPrompt',string='Address:')
            if len(addresses) > 1:
                for address in addresses[1:]:
                    new_person = DSK8RelatedPerson(self.case_number)
                    new_person.address_1 = self.value_combined_first_column(address.find_parent('td'),'Address:')
                    new_person.city = person.city
                    new_person.state = person.state
                    new_person.zip_code = person.zip_code
                    db.add(new_person)

    #########################################################
    # BAIL AND BOND INFORMATION
    #########################################################
    @consumer
    def bail_and_bond(self, db, soup):
        try:
            section_header = self.second_level_header(soup,'Bail and Bond Information')
        except ParserError:
            return

        prev_obj = section_header
        while True:
            try:
                section = self.immediate_sibling(prev_obj,'div',class_='AltBodyWindow1')
                separator = self.immediate_sibling(section,'hr')
                prev_obj = separator
            except ParserError:
                break

            t1 = self.table_first_columm_prompt(section,'Bail Amount:')
            t2 = self.table_next_first_column_prompt(t1,'Bond Type:')
            t3 = self.immediate_sibling(t2,'table')

            b = DSK8BailAndBond(self.case_number)

            b.bail_amount = self.value_first_column(section,'Bail Amount:',money=True)
            b.bail_number = self.value_multi_column(section,'Bail Number:',ignore_missing=True)
            b.set_date_str = self.value_first_column(section,'Set Date:')
            b.release_date_str = self.value_multi_column(section,'Release Date:',ignore_missing=True)
            b.bail_set_location = self.value_multi_column(section,'Bail Set Location:',ignore_missing=True)
            b.release_reason = self.value_first_column(section,'Release Reason:',ignore_missing=True)

            b.bond_type = self.value_first_column(section,'Bond Type:')
            b.ground_rent = self.value_multi_column(section,'Ground Rent:',ignore_missing=True,money=True)
            b.mortgage = self.value_first_column(section,'Mortgage:',ignore_missing=True,money=True)
            b.property_value = self.value_multi_column(section,'Property Value:',ignore_missing=True,money=True)
            b.property_address = self.value_first_column(section,'PropertyAddress:',ignore_missing=True)

            b.forfeit_date_str = self.value_first_column(section,'Forfeit Date:',ignore_missing=True)
            b.forfeit_extended_date_str = self.value_multi_column(section,'Forfeit Extended Date:',ignore_missing=True)
            b.days_extended = self.value_first_column(section,'Days Extended:',ignore_missing=True)
            b.bondsman_company_name = self.value_first_column(section,'CompanyName:',ignore_missing=True)
            b.judgment_date_str = self.value_multi_column(section,'JudgementDate:',ignore_missing=True)
            db.add(b)

            prev_obj_2 = None
            while True:
                try:
                    if not prev_obj_2:
                        # Bondsman tables are inside of table 3
                        t4 = self.table_first_columm_prompt(t3,'Bail Bondsman:')
                        t5 = self.table_next_first_column_prompt(t4,'City:')
                    else:
                        t4 = self.table_next_first_column_prompt(prev_obj_2,'Bail Bondsman:')
                        t5 = self.table_next_first_column_prompt(t4,'City:')
                    prev_obj_2 = t5
                except ParserError:
                    break
                bondsman = DSK8Bondsman(self.case_number, b.id)
                bondsman.name = self.value_first_column(t4,'Bail Bondsman:')
                bondsman.address_1 = self.value_first_column(t4,'Street:')
                bondsman.city = self.value_first_column(t5,'City:')
                bondsman.state = self.value_multi_column(t5,'State:')
                bondsman.zip_code = self.value_multi_column(t5,'Zip:')
                db.add(bondsman)

    #########################################################
    # EVENT HISTORY INFORMATION
    #########################################################
    @consumer
    def event_history(self, db, soup):
        try:
            section_header = self.second_level_header(soup,'Event History Information')
        except ParserError:
            return
        history_table = self.immediate_sibling(section_header,'table')
        # Mark column headers for deletion
        column_headers_row = history_table.find('tr')
        for column_header in column_headers_row.find_all('td'):
            self.mark_for_deletion(column_header)
        prev_obj = column_headers_row
        while True:
            try:
                event_row = self.immediate_sibling(prev_obj,'tr')
                prev_obj = event_row
            except ParserError:
                break
            event = DSK8Event(self.case_number)
            event_fields = list(event_row.find_all('span',class_='Value'))
            event.event_name = self.format_value(event_fields[0].string)
            self.mark_for_deletion(event_fields[0])
            event.date_str = self.format_value(event_fields[1].string)
            self.mark_for_deletion(event_fields[1])
            event.comment = self.format_value(event_fields[2].string)
            self.mark_for_deletion(event_fields[2])
            db.add(event)
