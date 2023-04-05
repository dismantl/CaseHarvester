from ..models import DSCP, DSCPCharge, DSCPDefendant, DSCPDefendantAlias, DSCPRelatedPerson, DSCPEvent, DSCPTrial, DSCPBailEvent
from .base import CaseDetailsParser, consumer, ParserError, ChargeFinder
from datetime import datetime
import re

# Note that consumers may not be called in order
class DSCPParser(CaseDetailsParser, ChargeFinder):
    inactive_statuses = [
        'CLOSED'
    ]

    def header(self, soup):
        header = soup.find('div',class_='Header')
        header.decompose()
        goback = soup.find('a',string='Go Back Now')
        if not goback:
            raise ParserError('Missing expected "Go Back Now" link')
        goback = goback.find_parent('div')
        goback.decompose()

    def footer(self, soup):
        footer = soup.find('div',class_='InfoStatement',string=re.compile('This is an electronic case record'))
        footer.decompose()

    #########################################################
    # CASE INFORMATION
    #########################################################
    def case(self, db, soup):
        case = DSCP(case_number=self.case_number)
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
        self.case_status = case.case_status
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
        schedule = DSCPTrial(case_number=self.case_number)

        table1 = self.table_next_first_column_prompt(section_header, 'Trial Date:')
        schedule.date_str = self.value_first_column(table1, 'Trial Date:')
        schedule.time_str = self.value_column(table1, 'Trial Time:')
        schedule.room = self.value_column(table1, 'Room:',ignore_missing=True)

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
        new_charges = []
        while True:
            try:
                charge_section = self.immediate_sibling(prev_obj,'div',class_='AltBodyWindow1')
                separator = self.immediate_sibling(charge_section,'hr')
                prev_obj = separator
            except ParserError:
                break
            new_charge = self.parse_charge(charge_section)
            new_charges.append(new_charge)

        for new_charge in new_charges:
            db.add(new_charge)
        new_charge_numbers = [c.charge_number for c in new_charges]
        self.find_charges(db, new_charge_numbers)

    def parse_charge(self, container):
        charge = DSCPCharge(case_number=self.case_number)
        charge_table_1 = self.table_first_columm_prompt(container,'Charge No:')
        charge.charge_number = int(self.value_first_column(charge_table_1,'Charge No:'))
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
            disposition_header = self.third_level_header(container,'Disposition')
        except ParserError:
            pass
        else:
            disposition_table = disposition_header.find_parent('table')
            charge.plea = self.value_first_column(disposition_table,'Plea:')
            charge.disposition = self.value_first_column(disposition_table,'Disposition:')
            charge.disposition_date_str = self.value_combined_first_column(disposition_table,'Disposition Date:')

            # TODO see if fine row and suspendent amt fine row are always the same
            fine_row = disposition_table\
                .find('span',class_='FirstColumnPrompt',string='Disposition Date:')\
                .find_parent('tr')\
                .find_next_sibling('tr')
            charge.fine = self.value_column(fine_row,'Fine:',money=True)
            charge.court_costs = self.value_column(fine_row,'Court Costs:',money=True)
            charge.cicf = self.value_column(fine_row,'CICF:',money=True)

            suspended_fine_row = self.row_first_label(disposition_table,'Amt Suspended:')
            charge.suspended_fine = self.value_column(suspended_fine_row,'Fine:',money=True)
            charge.suspended_court_costs = self.value_column(suspended_fine_row,'Court Costs:',money=True)
            charge.suspended_cicf = self.value_column(suspended_fine_row,'CICF:',money=True)

            charge.pbj_end_date_str = self.value_first_column(disposition_table,'PBJ EndDate:')
            charge.probation_end_date_str = self.value_column(disposition_table,'Probation End Date:')
            charge.restitution_amount = self.value_column(disposition_table,'Restitution Amount:',money=True)

            jail_term_row = self.row_first_label(disposition_table,'Jail Term:')
            charge.jail_term_years = self.value_column(jail_term_row,'Yrs:')
            charge.jail_term_months = self.value_column(jail_term_row,'Mos:')
            charge.jail_term_days = self.value_column(jail_term_row,'Days:')

            suspended_term_row = self.row_first_label(disposition_table,'Suspended Term:')
            charge.suspended_term_years = self.value_column(suspended_term_row,'Yrs:')
            charge.suspended_term_months = self.value_column(suspended_term_row,'Mos:')
            charge.suspended_term_days = self.value_column(suspended_term_row,'Days:')

            charge.credit_time_served = self.value_first_column(disposition_table,'Credit Time Served:')
        
        return charge

    #########################################################
    # DEFENDENT INFORMATION
    #########################################################
    @consumer
    def defendant_and_aliases(self, db, soup):
        defendant = DSCPDefendant(case_number=self.case_number)
        section_header = self.first_level_header(soup,'Defendant Information')

        name_table = self.table_next_first_column_prompt(section_header,'Defendant Name:')
        defendant.name = self.value_first_column(name_table,'Defendant Name:')

        demographics_table = self.immediate_sibling(name_table,'table')
        if list(demographics_table.stripped_strings):
            defendant.race = self.value_first_column(demographics_table,'Race:',ignore_missing=True)
            defendant.sex = self.value_first_column(demographics_table,'Sex:',ignore_missing=True)
            defendant.height = self.value_column(demographics_table,'Height:',ignore_missing=True)
            defendant.weight = self.value_column(demographics_table,'Weight:',ignore_missing=True)
            defendant.DOB_str = self.value_column(demographics_table,'DOB:',ignore_missing=True)

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
            alias = DSCPDefendantAlias(case_number=self.case_number)
            alias.alias_name = self.value_first_column(alias_table,'ALIAS:')
            db.add(alias)
            # Address table always empty
            address_table = self.immediate_sibling(alias_table,'table')
            separator = self.immediate_sibling(address_table,'hr')
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
            person = DSCPRelatedPerson(case_number=self.case_number)
            person.name = self.value_combined_first_column(table_1,'Name:') # Can be null
            person.connection = self.value_combined_first_column(table_1,'Connection:')
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
            event = DSCPEvent(case_number=self.case_number)
            event_fields = list(event_row.find_all('span',class_='Value'))
            event.event_name = self.format_value(event_fields[0].string)
            self.mark_for_deletion(event_fields[0])
            event.date_str = self.format_value(event_fields[1].string)
            self.mark_for_deletion(event_fields[1])
            event.comment = self.format_value(event_fields[2].string)
            self.mark_for_deletion(event_fields[2])
            if event.event_name == 'BALR' or event.event_name == 'BSET' or event.event_name == 'INIT':
                match = re.fullmatch(r'\s*(?P<date>\d{6})\s*;\s*(?P<amount>\d+\.\d\d)\s*;\s*(?P<code>[A-Z]+)\s*;\s*(?P<percent>[\d\.]+)?\s*;\s*(?P<bond>[A-Z]*)?\s*;\s*(?P<judge>[A-Z0-9]+)?\s*', event.comment)
                bail_event = DSCPBailEvent(case_number=self.case_number)
                bail_event.event_name = event.event_name
                bail_event.date_str = self.format_value(match.group('date'))
                bail_event.date = datetime.strptime(match.group('date'), '%y%m%d').date()
                bail_event.bail_amount = self.format_value(match.group('amount'), money=True)
                bail_event.code = self.format_value(match.group('code'))
                bail_event.percentage_required = self.format_value(match.group('percent'), numeric=True)
                type_of_bond = self.format_value(match.group('bond'))
                bail_event.type_of_bond = None if not type_of_bond else type_of_bond
                bail_event.judge_id = self.format_value(match.group('judge'))
                db.add(bail_event)
            db.add(event)
