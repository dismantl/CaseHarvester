from ..models import (ODYCOSA, ODYCOSAReferenceNumber, ODYCOSAAttorney,
                      ODYCOSADocument, ODYCOSAInvolvedParty,
                      ODYCOSACourtSchedule, ODYCOSAJudgment)
from .base import CaseDetailsParser, consumer, ParserError, reference_number_re
import re
from bs4 import BeautifulSoup, SoupStrainer

# Note that consumers may not be called in order
class ODYCOSAParser(CaseDetailsParser):
    inactive_statuses = [
        'Transferred',
        'Closed'
    ]

    def __init__(self, case_number, html):
        self.case_number = case_number
        strainer = SoupStrainer('div',class_='BodyWindow')
        self.soup = BeautifulSoup(html,'html.parser',parse_only=strainer)
        if len(self.soup.contents) != 1 or not self.soup.div:
            raise ParserError("Unexpected HTML format", self.soup)
        self.marked_for_deletion = []

    def header(self, soup):
        header = soup.find('div',class_='Header')
        header.decompose()
        subheader = soup.find('div',class_='Subheader')
        if not subheader:
            raise ParserError('Missing subheader')
        subheader.decompose()

    def footer(self, soup):
        footer = soup.find('div',class_='InfoStatement',string=re.compile('This is an electronic case record'))
        footer.decompose()

    #########################################################
    # CASE INFORMATION
    #########################################################
    def case(self, db, soup):
        case = ODYCOSA(case_number=self.case_number)
        section_header = self.first_level_header(soup,'Case Information')

        case_info_table = self.table_next_first_column_prompt(section_header,'Court System:')
        case.court_system = self.value_first_column(case_info_table,'Court System:',remove_newlines=True)
        case_number = self.value_first_column(case_info_table,'Case Number:')
        if self.case_number.lower() != case_number.replace('-','').lower():
            raise ParserError('Case number "%s" in case details page does not match given: %s' % (case_number, self.case_number))
        case.case_title = self.value_first_column(case_info_table,'Title:')
        case.case_type = self.value_first_column(case_info_table,'Case Type:')
        case.filing_date_str = self.value_first_column(case_info_table,'Filing Date:')
        case.case_status = self.value_first_column(case_info_table,'Case Status:')
        self.case_status = case.case_status
        case.authoring_judge = self.value_first_column(case_info_table, 'Authoring Judge:', ignore_missing=True)
        case.tracking_numbers = self.value_first_column(case_info_table,r'Tracking Number\(s\):')
        db.add(case)
    
    #########################################################
    # OTHER REFERENCE NUMBERS
    #########################################################
    @consumer
    def reference_numbers(self, db, soup):
        try:
            section_header = self.first_level_header(soup, 'Other Reference Numbers')
        except ParserError:
            return

        prev_obj = section_header
        while True:
            try:
                t = self.immediate_sibling(prev_obj,'table')
            except ParserError:
                break
            prev_obj = t
            prompt_re = re.compile(reference_number_re)
            prompt_span = t.find('span',class_='FirstColumnPrompt',string=prompt_re)
            if not prompt_span:
                break
            ref_num = ODYCOSAReferenceNumber(case_number=self.case_number)
            ref_num.ref_num = self.value_first_column(t, prompt_span.string)
            ref_num.ref_num_type = prompt_re.fullmatch(prompt_span.string).group(1)
            db.add(ref_num)
    
    #########################################################
    # INVOLVED PARTIES INFORMATION
    #########################################################
    @consumer
    def involved_parties(self, db, soup):
        try:
            section_header = self.first_level_header(soup, 'Involved Parties Information')
        except ParserError:
            return
        
        prev_obj = section_header
        while True:
            party = None

            try:
                prev_obj = self.immediate_sibling(prev_obj, 'hr')
            except ParserError:
                pass
            
            try:
                subsection_header = self.immediate_sibling(prev_obj,'h5')
            except ParserError:
                break
            self.mark_for_deletion(subsection_header)
            prev_obj = subsection_header
            party = ODYCOSAInvolvedParty(case_number=self.case_number)
            party.party_type = self.format_value(subsection_header.string)

            try:
                name_table = self.table_next_first_column_prompt(subsection_header,'Name:')
            except ParserError:
                pass
            else:
                party.name = self.value_first_column(name_table,'Name:')
                prev_obj = name_table

                while True:
                    try:
                        t = self.immediate_sibling(prev_obj,'table')
                    except ParserError:
                        break

                    if 'Address:' in t.stripped_strings:
                        rows = t.find_all('tr')
                        party.address_1 = self.value_first_column(t,'Address:')
                        if len(rows) == 3:
                            party.address_2 = self.format_value(rows[1].find('span',class_='Value').string)
                            self.mark_for_deletion(rows[1])
                        party.city = self.value_first_column(t,'City:')
                        party.state = self.value_column(t,'State:')
                        party.zip_code = self.value_column(t,'Zip Code:',ignore_missing=True)
                    elif 'Removal Date:' in t.stripped_strings:
                        party.removal_date_str = self.value_first_column(t,'Removal Date:')
                    elif 'Appearance Date:' in t.stripped_strings:
                        party.appearance_date_str = self.value_first_column(t,'Appearance Date:')
                    elif 'Race:' in t.stripped_strings or 'DOB:' in t.stripped_strings:
                        party.race = self.value_first_column(t,'Race:',ignore_missing=True)
                        party.sex = self.value_column(t,'Sex:',ignore_missing=True)
                        party.height = self.value_column(t,'Height:',ignore_missing=True)
                        party.weight = self.value_column(t,'Weight:',numeric=True,ignore_missing=True)
                        party.hair_color = self.value_first_column(t,'HairColor:',ignore_missing=True)
                        party.eye_color = self.value_column(t,'EyeColor:',ignore_missing=True)
                        party.DOB_str = self.value_first_column(t,'DOB:',ignore_missing=True)
                    elif len(list(t.stripped_strings)) > 0:
                        break
                    prev_obj = t

            db.add(party)
            db.flush()

            # Attorneys
            while True:
                try:
                    subsection_header = self.immediate_sibling(prev_obj,'table')
                    subsection_table = self.immediate_sibling(subsection_header,'table')
                except ParserError:
                    break
                prev_obj = subsection_table
                subsection_name = subsection_header.find('h5').string
                self.mark_for_deletion(subsection_header)
                if 'Attorney(s) for the' in subsection_name:
                    for span in subsection_table.find_all('span',class_='FirstColumnPrompt',string='Name:'):
                        attorney = ODYCOSAAttorney(case_number=self.case_number)
                        attorney.party_id = party.id
                        name_row = span.find_parent('tr')
                        attorney.name = self.value_first_column(name_row,'Name:')
                        prev_row = name_row

                        try:
                            appearance_date_row = self.row_next_first_column_prompt(prev_row,'Appearance Date:')
                        except ParserError:
                            pass
                        else:
                            prev_row = appearance_date_row
                            attorney.appearance_date_str = self.value_first_column(appearance_date_row,'Appearance Date:')
                        
                        try:
                            removal_date_row = self.row_next_first_column_prompt(prev_row,'Removal Date:')
                        except ParserError:
                            pass
                        else:
                            prev_row = removal_date_row
                            attorney.removal_date_str = self.value_first_column(removal_date_row,'Removal Date:')
                        
                        try:
                            address_row = self.row_next_first_column_prompt(prev_row,'Address Line 1:')
                        except ParserError:
                            pass
                        else:
                            attorney.address_1 = self.value_first_column(address_row,'Address Line 1:')
                            prev_row = address_row
                            try:
                                address_row_2 = self.row_next_first_column_prompt(address_row,'Address Line 2:')
                            except ParserError:
                                pass
                            else:
                                prev_row = address_row_2
                                attorney.address_2 = self.value_first_column(address_row_2,'Address Line 2:')
                                try:
                                    address_row_3 = self.row_next_first_column_prompt(address_row_2,'Address Line 3:')
                                except ParserError:
                                    pass
                                else:
                                    prev_row = address_row_3
                                    attorney.address_3 = self.value_first_column(address_row_3,'Address Line 3:')
                            city_row = self.row_next_first_column_prompt(prev_row,'City:')
                            attorney.city = self.value_first_column(city_row,'City:')
                            attorney.state = self.value_column(city_row,'State:')
                            attorney.zip_code = self.value_column(city_row,'Zip Code:')
                        db.add(attorney)
    
    #########################################################
    # JUDGMENT INFORMATION
    #########################################################
    @consumer
    def judgments(self, db, soup):
        try:
            section_header = self.first_level_header(soup, 'Judgment Information')
        except ParserError:
            return
        
        prev_obj = section_header
        while True:
            try:
                t = self.table_next_first_column_prompt(prev_obj, 'Judgment Event Type:')
                prev_obj = self.immediate_sibling(t, 'hr')
            except ParserError:
                break

            judgment = ODYCOSAJudgment(case_number=self.case_number)
            judgment.judgment_event_type = self.value_first_column(t, 'Judgment Event Type:')
            judgment.judge_name = self.value_first_column(t, 'Judge Name:', ignore_missing=True)
            judgment.issue_date_str = self.value_first_column(t, 'Issue Date:')
            judgment.comment = self.value_first_column(t, 'Comment:')
            db.add(judgment)

    #########################################################
    # COURT SCHEDULING INFORMATION
    #########################################################
    @consumer
    def court_schedule(self, db, soup):
        try:
            section_header = self.first_level_header(soup, 'Court Scheduling Information')
        except ParserError:
            return
        
        prev_obj = section_header
        while True:
            try:
                t = self.table_next_first_column_prompt(prev_obj, 'Event Type:')
                prev_obj = self.immediate_sibling(t, 'hr')
            except ParserError:
                break

            schedule = ODYCOSACourtSchedule(case_number=self.case_number)
            schedule.event_type = self.value_first_column(t, 'Event Type:')
            schedule.date_str = self.value_first_column(t, 'Event Date:')
            schedule.time_str = self.value_column(t, 'Start Time:', ignore_missing=True)
            schedule.result = self.value_first_column(t, 'Result:', ignore_missing=True)
            schedule.panel_judges = self.value_first_column(t, 'Panel Judges:', ignore_missing=True)
            db.add(schedule)

    #########################################################
    # DOCUMENT INFORMATION
    #########################################################
    @consumer
    def document(self, db, soup):
        try:
            section_header = self.first_level_header(soup,'Document Information')
        except ParserError:
            return

        prev_obj = section_header
        while True:
            try:
                t = self.immediate_sibling(prev_obj,'table')
                separator = self.immediate_sibling(t,'hr')
            except ParserError:
                break
            prev_obj = separator
            doc = ODYCOSADocument(case_number=self.case_number)
            doc.file_date_str = self.value_first_column(t,'File Date:')
            doc.document_name = self.value_first_column(t,'Document Name:')
            db.add(doc)