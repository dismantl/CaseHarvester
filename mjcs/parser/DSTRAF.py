from ..models import DSTRAF, DSTRAFCharge, DSTRAFDisposition, DSTRAFDefendant, DSTRAFEvent, DSTRAFTrial, DSTRAFRelatedPerson
from .base import CaseDetailsParser, consumer, ParserError
import re

# Note that consumers may not be called in order
class DSTRAFParser(CaseDetailsParser):
    inactive_statuses = [
        'INACTIVE CASE',
        'INACTIVE DUE TO INCOMPETENCY',
        'CLOSED CASE'
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
        case = DSTRAF(case_number=self.case_number)
        case_table = self.table_first_columm_prompt(self.soup,'Court System:')
        case.court_system = self.value_first_column(case_table,'Court System:',remove_newlines=True)
        case_number = self.value_first_column(case_table,'Citation Number:')
        if case_number.lstrip('0') != self.case_number.lstrip('0'):
            raise ParserError('Case number "%s" in case details page does not match given: %s' % (case_number, self.case_number))
        case.case_status = self.value_column(case_table,'Case Status:',ignore_missing=True)
        self.case_status = case.case_status
        case.violation_date_str = self.value_first_column(case_table,'Violation Date:',ignore_missing=True)
        case.violation_time_str = self.value_multi_column(case_table,'Violation Time:',ignore_missing=True)
        case.violation_county = self.value_first_column(case_table,'Violation County:',ignore_missing=True)
        case.district_code = self.value_first_column(case_table,'District Code:',ignore_missing=True)
        case.location_code = self.value_multi_column(case_table,'Location Code:',ignore_missing=True)
        case.agency_name = self.value_combined_first_column(case_table,'AgencyName:',ignore_missing=True)
        case.officer_name = self.value_combined_first_column(case_table,'Officer Name:',ignore_missing=True)
        case.officer_id = self.value_combined_first_column(case_table,'Officer ID:',ignore_missing=True)
        db.add(case)

    #########################################################
    # CHARGE INFORMATION
    #########################################################
    @consumer
    def charge(self, db, soup):
        try:
            section_header = self.first_level_header(soup,'Charge Information')
        except ParserError:
            return

        section = self.immediate_sibling(section_header,'span',class_='AltBodyWindow1')

        charge = DSTRAFCharge(case_number=self.case_number)
        self.mark_for_deletion(section.find('span',class_='FirstColumnPrompt',string='Charge:'))
        charge.article = self.value_column(section,'Article:')
        charge.sec = self.value_column(section,'Sec:')
        charge.sub_sec = self.value_column(section,'Sub-Sec:')
        charge.para = self.value_column(section,'Para:')
        charge.code = self.value_column(section,'Code:')
        charge.description = self.value_first_column(section,'Description:')
        charge.speed_limit = self.value_first_column(section,'Speed Limit:',ignore_missing=True)
        charge.recorded_speed = self.value_multi_column(section,'Recorded Speed:',ignore_missing=True)
        charge.location_stopped = self.value_first_column(section,'Location Stopped:',ignore_missing=True)
        charge.contributed_to_accident = self.value_multi_column(section,r'Contributed to Accident\?:')
        charge.personal_injury = self.value_multi_column(section,r'Personal Injury\?:')
        charge.property_damage = self.value_multi_column(section,r'Property Damage\?:',ignore_missing=True)
        charge.seat_belts = self.value_multi_column(section,'Seat Belts:',ignore_missing=True)
        charge.fine = self.value_first_column(section,'Fine:')
        charge.related_citation_number = self.value_multi_column(section,'Related Citation Number:',ignore_missing=True)
        charge.vehicle_tag = self.value_first_column(section,'Vehicle Tag:')
        charge.state = self.value_multi_column(section,'State:')
        charge.vehicle_description = self.value_multi_column(section,'Vehicle Description:')
        db.add(charge)

    #########################################################
    # DISPOSITION INFORMATION
    #########################################################
    @consumer
    def disposition(self, db, soup):
        try:
            section_header = self.second_level_header(soup,r'^Disposition Information')
        except ParserError:
            return

        section = self.immediate_sibling(section_header,'span',class_='AltBodyWindow1')

        d = DSTRAFDisposition(case_number=self.case_number)
        d.plea = self.value_first_column(section,'Plea:')
        d.disposition = self.value_first_column(section,'Disposition:')
        d.disposition_date_str = self.value_first_column(section,'Disposition Date:')
        d.speed_limit = self.value_first_column(section,'Speed Limit:',ignore_missing=True)
        d.convicted_speed = self.value_multi_column(section,'Convicted Speed:',ignore_missing=True)
        d.contributed_to_accident = self.value_first_column(section,'Contributed To Accident:')
        d.alcohol_restriction = self.value_multi_column(section,'Alcohol Restriction:',ignore_missing=True)
        d.personal_injury = self.value_multi_column(section,r'Personal Injury\?:')
        d.subsequent_offense = self.value_multi_column(section,'Subsequent Offense:',ignore_missing=True)
        d.alcohol_education = self.value_first_column(section,'Alcohol Education:',ignore_missing=True)
        d.driver_improvement = self.value_multi_column(section,'Driver Improvement:',ignore_missing=True)
        d.sentence_date_str = self.value_first_column(section,'Sentence Date:')
        d.sentence_starts_str = self.value_first_column(section,'Sentence Starts:',ignore_missing=True)
        d.probation_type = self.value_multi_column(section,'Probation Type:',ignore_missing=True)
        
        sentence_span = section.find('span',class_='FirstColumnPrompt',string='Sentence Time:')
        self.mark_for_deletion(sentence_span)
        sentence_table = sentence_span.find_parent('table')
        d.sentence_years = self.value_column(sentence_table,'Yrs:')
        d.sentence_months = self.value_column(sentence_table,'Mos:')
        d.sentence_days = self.value_column(sentence_table,'Days:')

        suspended_span = section.find('span',class_='FirstColumnPrompt',string='Suspended Time:')
        self.mark_for_deletion(suspended_span)
        suspended_table = suspended_span.find_parent('table')
        d.suspended_years = self.value_column(suspended_table,'Yrs:')
        d.suspended_months = self.value_column(suspended_table,'Mos:')
        d.suspended_days = self.value_column(suspended_table,'Days:')

        costs_row = section.find('span',class_='FirstColumnPrompt',string='Costs: Fine:').find_parent('tr')
        d.fine = self.value_first_column(costs_row,'Costs: Fine:')
        d.court_costs = self.value_multi_column(costs_row,'CourtCost:')
        d.cicf = self.value_multi_column(costs_row,'CICF:')

        suspended_row = section.find('span',class_='FirstColumnPrompt',string='Suspended: Fine:').find_parent('tr')
        d.suspended_fine = self.value_first_column(suspended_row,'Suspended: Fine:')
        d.suspended_court_costs = self.value_multi_column(suspended_row,'CourtCost:')
        d.suspended_cicf = self.value_multi_column(suspended_row,'CICF Cost:')

        info_charge_statement = section.find('span',class_='InfoChargeStatement')
        if info_charge_statement:
            statement_table = info_charge_statement.find_parent('table')
            d.addition_statement = self.format_value(info_charge_statement.string)
            self.mark_for_deletion(info_charge_statement)
            details_table = self.table_next_first_column_prompt(statement_table,'Charge:')
            self.mark_for_deletion(details_table.find('span',class_='FirstColumnPrompt',string='Charge:'))
            d.addition_article = self.value_column(details_table,'Article:')
            d.addition_sec = self.value_column(details_table,'Sec:')
            d.addition_sub_sec = self.value_column(details_table,'Sub-Sec:')
            d.addiiton_para = self.value_column(details_table,'Para:')
            d.addition_code = self.value_column(details_table,'Code:')
            d.addition_amended_charge = self.value_first_column(details_table,'Amended Charge:')
        
        db.add(d)

    #########################################################
    # CHARGE AND DISPOSITION INFORMATION
    #########################################################
    @consumer
    def charge_and_disposition(self, db, soup):
        try:
            section_header = self.first_level_header(soup,'Charge and Disposition Information')
        except ParserError:
            return
        
        try:
            container = self.immediate_sibling(section_header, 'div', class_='AltBodyWindow1')
            if list(container.stripped_strings)[0] == 'Case transferred to Circuit Court. See Circuit Court case.':
                self.mark_for_deletion(container)
                disposition = DSTRAFDisposition(case_number=self.case_number)
                disposition.notes = 'Case transferred to Circuit Court. See Circuit Court case.'
                db.add(disposition)
        except ParserError:
            pass

    #########################################################
    # DEFENDENT INFORMATION
    #########################################################
    @consumer
    def defendant(self, db, soup):
        defendant = DSTRAFDefendant(case_number=self.case_number)
        section_header = self.second_level_header(soup,'Defendant Information')

        name_table = self.table_next_first_column_prompt(section_header,'Defendant Name:')
        defendant.name = self.value_combined_first_column(name_table,'Defendant Name:')

        address_table = self.immediate_sibling(name_table,'table')
        if list(address_table.stripped_strings):
            defendant.address_1 = self.value_combined_first_column(address_table,'Address:')

        city_table = self.immediate_sibling(address_table,'table')
        if list(city_table.stripped_strings):
            defendant.city = self.value_first_column(city_table,'City:')
            defendant.state = self.value_column(city_table,'State:')
            defendant.zip_code = self.value_column(city_table,'Zip Code:')

        demographics_table = self.immediate_sibling(city_table,'table')
        if list(demographics_table.stripped_strings):
            defendant.race = self.value_combined_first_column(demographics_table,'Race:',ignore_missing=True)
            defendant.sex = self.value_combined_first_column(demographics_table,'Sex:',ignore_missing=True)
            defendant.height = self.value_column(demographics_table,'Height:',ignore_missing=True)
            defendant.weight = self.value_column(demographics_table,'Weight:',ignore_missing=True)
            defendant.DOB_str = self.value_combined_first_column(demographics_table,'DOB:',ignore_missing=True)

        db.add(defendant)

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
                table_1 = self.immediate_sibling(prev_obj,'table')
                table_2 = self.immediate_sibling(table_1,'table')
                table_3 = self.immediate_sibling(table_2,'table')
                separator = self.immediate_sibling(table_3,'hr')
                prev_obj = separator
            except ParserError:
                break
            person = DSTRAFRelatedPerson(case_number=self.case_number)
            person.name = self.value_combined_first_column(table_1,'Name:') # Can be null
            person.connection = self.value_combined_first_column(table_1,'Connection:')
            if list(table_2.stripped_strings): # Address
                person.address_1 = self.value_combined_first_column(table_2,'Address:')
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
            event = DSTRAFEvent(case_number=self.case_number)
            event_fields = list(event_row.find_all('span',class_='Value'))
            event.event_name = self.format_value(event_fields[0].string)
            self.mark_for_deletion(event_fields[0])
            event.date_str = self.format_value(event_fields[1].string)
            self.mark_for_deletion(event_fields[1])
            event.comment = self.format_value(event_fields[2].string)
            self.mark_for_deletion(event_fields[2])
            db.add(event)

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
                t1 = self.table_next_first_column_prompt(prev_obj,'Trial Date:')
                separator = self.immediate_sibling(t1,'hr')
                prev_obj = separator
            except ParserError:
                break
            trial = DSTRAFTrial(case_number=self.case_number)
            trial.date_str = self.value_first_column(t1,'Trial Date:')
            trial.time_str = self.value_column(t1,'Trial Time:')
            trial.room = self.value_column(t1,'Room:')
            trial.location = self.value_first_column(t1,'Trial Location:')
            trial.reason = self.value_first_column(t1,'Reason:')
            db.add(trial)