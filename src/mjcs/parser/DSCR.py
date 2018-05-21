from ..db import TableBase
from .base import CaseDetailsParser, consumer, ParserError
from .common import CaseTable, Trial, Event, date_from_str, Defendant, DefendantAlias, RelatedPerson
from sqlalchemy import Column, Date, Numeric, Integer, String, Boolean, ForeignKey, Time, BigInteger
from sqlalchemy.orm import relationship
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.ext.declarative import declared_attr
from datetime import *
import re

class DSCR(CaseTable, TableBase):
    __tablename__ = 'dscr'

    id = Column(Integer, primary_key=True)
    court_system = Column(String)
    tracking_number = Column(BigInteger, nullable=True)
    case_type = Column(String, nullable=True)
    district_code = Column(Integer, nullable=True)
    location_code = Column(Integer, nullable=True)
    document_type = Column(String, nullable=True)
    issued_date = Column(Date, nullable=True)
    _issued_date_str = Column('issued_date_str',String, nullable=True)
    case_status = Column(String, nullable=True)
    case_disposition = Column(String, nullable=True)

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
        return Column(String, ForeignKey('dscr.case_number', ondelete='CASCADE'))

class DSCRCharge(DSCRCaseTable, TableBase):
    __tablename__ = 'dscr_charges'

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
    credit_time_served = Column(Integer, nullable=True)

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

class DSCRDefendantAlias(DSCRCaseTable, DefendantAlias, TableBase):
    __tablename__ = 'dscr_defendant_aliases'

class DSCRRelatedPerson(DSCRCaseTable, RelatedPerson, TableBase):
    __tablename__ = 'dscr_related_persons'

class DSCREvent(DSCRCaseTable, Event, TableBase):
    __tablename__ = 'dscr_events'

class DSCRTrial(DSCRCaseTable, Trial, TableBase):
    __tablename__ = 'dscr_trials'

# Note that consumers may not be called in order
class DSCRParser(CaseDetailsParser):
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
        self.delete_previous(db, DSCR)
        print("Took %s seconds to delete previous DSCR" % (datetime.now() - a).total_seconds())

        case = DSCR(self.case_number)
        section_header = self.first_level_header(soup,'Case Information')

        court_system_table = self.table_next_first_column_prompt(section_header,'Court System:')
        case.court_system = self.value_first_column(court_system_table,'Court System:',remove_newlines=True)

        case_info_table = self.table_next_first_column_prompt(court_system_table,'Case Number:')
        case_number = self.value_first_column(case_info_table,'Case Number:')
        if case_number != self.case_number:
            raise ParserError('Case number "%s" in case details page does not match given: %s' % (case_number, self.case_number))
        case.tracking_number = self.value_column(case_info_table,'Tracking No:',ignore_missing=True)
        case.case_type = self.value_first_column(case_info_table,'Case Type:',ignore_missing=True)
        case.district_code = self.value_first_column(case_info_table,'District Code:',ignore_missing=True)
        case.location_code = self.value_column(case_info_table,'Location Code:',ignore_missing=True)
        case.document_type = self.value_first_column(case_info_table,'Document Type:',ignore_missing=True)
        case.issued_date_str = self.value_column(case_info_table,'Issued Date:',ignore_missing=True)
        case.case_status = self.value_first_column(case_info_table,'Case Status:',ignore_missing=True)
        case.case_disposition = self.value_column(case_info_table,'Case Disposition:',ignore_missing=True)
        db.add(case)

    #########################################################
    # COURT SCHEDULING INFORMATION
    #########################################################
    @consumer
    def trial(self, db, soup):
        try:
            section_header = self.first_level_header(soup, 'Court Scheduling Information')
        except ParserError:
            return
        schedule = DSCRTrial(self.case_number)

        table1 = self.table_next_first_column_prompt(section_header, 'Trial Date:')
        schedule.date_str = self.value_first_column(table1, 'Trial Date:')
        schedule.time_str = self.value_column(table1, 'Trial Time:')
        schedule.room = self.value_column(table1, 'Room:')

        table2 = self.table_next_first_column_prompt(table1, 'Trial Type:')
        schedule.trial_type = self.value_first_column(table2, 'Trial Type:')

        schedule.location = self.value_first_column(soup, 'Trial Location:')
        db.add(schedule)

    #########################################################
    # CHARGE AND DISPOSITION INFORMATION
    #########################################################
    @consumer
    def charge_and_disposition(self, db, soup):
        try:
            section_header = self.first_level_header(soup,'Charge and Disposition Information')
        except ParserError:
            return
        info_charge_statement = self.info_charge_statement(section_header)

        prev_obj = info_charge_statement
        while True:
            try:
                charge_section = self.immediate_sibling(prev_obj,'div',class_='AltBodyWindow1')
                separator = self.immediate_sibling(charge_section,'hr')
                prev_obj = separator
            except ParserError:
                break

            charge = DSCRCharge(self.case_number)
            charge_table_1 = self.table_first_columm_prompt(charge_section,'Charge No:')
            charge.charge_number = self.value_first_column(charge_table_1,'Charge No:')
            charge.charge_description = self.value_column(charge_table_1,'Description:')

            charge_table_2 = self.table_next_first_column_prompt(charge_table_1,'Statute:')
            charge.statute = self.value_first_column(charge_table_2,'Statute:')
            charge.statute_description = self.value_column(charge_table_2,'Description:') # TODO see if this is always same as charge_description
            charge.amended_date_str = self.value_first_column(charge_table_2,'Amended Date:')
            charge.cjis_code = self.value_column(charge_table_2,'CJIS Code:')
            charge.mo_pll = self.value_column(charge_table_2,'MO/PLL:')
            charge.probable_cause = self.value_column(charge_table_2,'Probable Cause:',boolean_value=True)

            charge_table_3 = self.table_next_first_column_prompt(charge_table_2,'Incident Date From:')
            charge.incident_date_from_str = self.value_first_column(charge_table_3,'Incident Date From:')
            charge.incident_date_to_str = self.value_multi_column(charge_table_3,'To:')
            charge.victim_age = self.value_multi_column(charge_table_3,'Victim Age:')

            try:
                disposition_header = self.third_level_header(charge_section,'Disposition')
            except ParserError:
                pass
            else:
                disposition_table = disposition_header.find_parent('table')
                charge.plea = self.value_first_column(disposition_table,'Plea:')
                charge.disposition = self.value_first_column(disposition_table,'Disposition:')
                charge.disposition_date = self.value_combined_first_column(disposition_table,'Disposition Date:')

                # TODO see if fine row and suspendent amt fine row are always the same
                fine_row = disposition_table\
                    .find('span',class_='FirstColumnPrompt',string='Disposition Date:')\
                    .find_parent('tr')\
                    .find_next_sibling('tr')
                charge.fine = self.value_column(fine_row,'Fine:',money=True)
                charge.court_costs = self.value_column(fine_row,'Court Costs:',money=True)
                charge.cicf = self.value_column(fine_row,'CICF:',money=True)

                suspended_fine_row = self.row_label(disposition_table,'Amt Suspended:')
                charge.suspended_fine = self.value_column(suspended_fine_row,'Fine:',money=True)
                charge.suspended_court_costs = self.value_column(suspended_fine_row,'Court Costs:',money=True)
                charge.suspended_cicf = self.value_column(suspended_fine_row,'CICF:',money=True)

                charge.pbj_end_date_str = self.value_first_column(disposition_table,'PBJ EndDate:')
                charge.probation_end_date_str = self.value_column(disposition_table,'Probation End Date:')
                charge.restitution_amount = self.value_column(disposition_table,'Restitution Amount:',money=True)

                jail_term_row = self.row_label(disposition_table,'Jail Term:')
                charge.jail_term_years = self.value_column(jail_term_row,'Yrs:')
                charge.jail_term_months = self.value_column(jail_term_row,'Mos:')
                charge.jail_term_days = self.value_column(jail_term_row,'Days:')

                suspended_term_row = self.row_label(disposition_table,'Suspended Term:')
                charge.suspended_term_years = self.value_column(suspended_term_row,'Yrs:')
                charge.suspended_term_months = self.value_column(suspended_term_row,'Mos:')
                charge.suspended_term_days = self.value_column(suspended_term_row,'Days:')

                charge.credit_time_served = self.value_first_column(disposition_table,'Credit Time Served:')
            db.add(charge)

    #########################################################
    # DEFENDENT INFORMATION
    #########################################################
    @consumer
    def defendant_and_aliases(self, db, soup):
        defendant = DSCRDefendant(self.case_number)
        section_header = self.first_level_header(soup,'Defendant Information')

        name_table = self.table_next_first_column_prompt(section_header,'Defendant Name:')
        defendant.name = self.value_first_column(name_table,'Defendant Name:')

        demographics_table = self.immediate_sibling(name_table,'table')
        if list(demographics_table.stripped_strings):
            defendant.race = self.value_first_column(demographics_table,'Race:',ignore_missing=True)
            defendant.sex = self.value_first_column(demographics_table,'Sex:')
            defendant.height = self.value_column(demographics_table,'Height:')
            defendant.weight = self.value_column(demographics_table,'Weight:')
            defendant.DOB_str = self.value_column(demographics_table,'DOB:')

        address_table = self.immediate_sibling(demographics_table,'table')
        if list(address_table.stripped_strings):
            defendant.address_1 = self.value_first_column(address_table,'Address:')
            address_row = address_table\
                .find('span',class_='FirstColumnPrompt',string='Address:')\
                .find_parent('tr')
            if not address_row.find('span',class_='Prompt') \
                    and len(list(address_row.find_all('span',class_='FirstColumnPrompt'))) == 2 \
                    and len(list(address_row.find_all('span',class_='Value'))) == 2 \
                    and not address_row.find_all('span',class_='FirstColumnPrompt')[1].string:
                address_2 = address_row.find_all('span',class_='Value')[1].string
                if address_2:
                    self.mark_for_deletion(address_2.parent)
                    defendant.address_2 = self.format_value(address_2)
            defendant.city = self.value_first_column(address_table,'City:')
            defendant.state = self.value_column(address_table,'State:')
            defendant.zip_code = self.value_column(address_table,'Zip Code:')
        db.add(defendant)

        separator = self.immediate_sibling(address_table,'hr')

        # check for ALIAS tables
        prev_obj = separator
        while True:
            try:
                alias_table = self.table_next_first_column_prompt(prev_obj,'ALIAS:')
            except ParserError:
                break
            alias = DSCRDefendantAlias(self.case_number)
            alias.alias_name = self.value_first_column(alias_table,'ALIAS:')

            try:
                address_table = self.table_next_first_column_prompt(alias_table,'Address:')
            except ParserError:
                address_table = self.immediate_sibling(alias_table,'table')
                separator = self.immediate_sibling(address_table,'hr')
            else:
                alias.address_1 = self.value_first_column(address_table,'Address:')
                address_row = address_table\
                    .find('span',class_='FirstColumnPrompt',string='Address:')\
                    .find_parent('tr')
                if not address_row.find('span',class_='Prompt') \
                        and len(list(address_row.find_all('span',class_='FirstColumnPrompt'))) == 2 \
                        and len(list(address_row.find_all('span',class_='Value'))) == 2 \
                        and not address_row.find_all('span',class_='FirstColumnPrompt')[1].string:
                    address_2 = address_row.find_all('span',class_='Value')[1].string
                    if address_2:
                        self.mark_for_deletion(address_2.parent)
                        alias.address_2 = self.format_value(address_2)
                alias.city = self.value_first_column(address_table,'City:')
                alias.state = self.value_column(address_table,'State:')
                alias.zip_code = self.value_column(address_table,'Zip Code:')
                separator = self.immediate_sibling(address_table,'hr')
            db.add(alias)
            prev_obj = separator

    #########################################################
    # RELATED PERSON INFORMATION
    #########################################################
    @consumer
    def related_person(self, db, soup):
        try:
            section_header = self.second_level_header(soup,'Related Person Information')
        except ParserError:
            return
        info_charge_statement = self.info_charge_statement(section_header)

        # Each related person section is three <table>s followed by an <hr>
        # Some tables may be empty, so check for .stripped_strings
        prev_obj = info_charge_statement
        while True:
            try:
                table_1 = self.immediate_sibling(prev_obj,'table')
                table_2 = self.immediate_sibling(table_1,'table')
                table_3 = self.immediate_sibling(table_2,'table')
                separator = self.immediate_sibling(table_3,'hr')
                prev_obj = separator
            except ParserError:
                break
            person = DSCRRelatedPerson(self.case_number)
            person.name = self.value_combined_first_column(table_1,'Name:') # Can be null
            person.connection = self.value_combined_first_column(table_1,'Connection:')
            if list(table_2.stripped_strings): # Address
                person.address_1 = self.value_first_column(table_2,'Address:')
                if len(table_2.find_all('span',class_='FirstColumnPrompt')) == 2:
                    address_2 = table_2\
                        .find_all('span',class_='FirstColumnPrompt')[1]\
                        .find_parent('tr')\
                        .find('span',class_='Value')\
                        .string
                    if address_2:
                        self.mark_for_deletion(address_2.parent)
                        person.address_2 = self.format_value(address_2)
                person.city = self.value_first_column(table_3,'City:',ignore_missing=True)
                person.state = self.value_column(table_3,'State:')
                person.zip_code = self.value_column(table_3,'Zip Code:',ignore_missing=True)
            else:
                if list(table_3.stripped_strings): # Agency info
                    person.agency_code = self.value_first_column(table_3,'Agency Code:')
                    person.agency_sub_code = self.value_column(table_3,'Agency Sub-Code:')
                    person.officer_id = self.value_column(table_3,'Officer ID:')
            db.add(person)

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
            event = DSCREvent(self.case_number)
            event_fields = list(event_row.find_all('span',class_='Value'))
            event.event_name = self.format_value(event_fields[0].string)
            self.mark_for_deletion(event_fields[0])
            event.date_str = self.format_value(event_fields[1].string)
            self.mark_for_deletion(event_fields[1])
            event.comment = self.format_value(event_fields[2].string)
            self.mark_for_deletion(event_fields[2])
            db.add(event)
