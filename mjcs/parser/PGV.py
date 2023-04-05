from ..models import (PGV, PGVDefendant, PGVPlaintiff, PGVOtherParty, PGVAttorney, 
                      PGVJudgment, PGVDocket, PGVCourtSchedule, PGVDefendantAlias)
from .base import CaseDetailsParser, consumer, ParserError, UnparsedDataError
import re

class PGVParser(CaseDetailsParser):
    inactive_statuses = [
        'Closed',
        'Inactive',
        'Case Closed Statistically'
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
    
    def finalize(self, db):
        for obj in self.marked_for_deletion:
            obj.decompose()
        if list(self.soup.stripped_strings):
            # Sometimes there are attorneys not attached to defendants or plaintiffs
            self.attorney(db, self.soup)
            for obj in self.marked_for_deletion:
                obj.decompose()
            if list(self.soup.stripped_strings):
                raise UnparsedDataError("Data remaining in DOM after parsing:",list(self.soup.stripped_strings))
        self.update_last_parse(db)

    #########################################################
    # CASE INFORMATION
    #########################################################
    def case(self, db, soup):
        section_header = self.second_level_header(soup,'Case Information')
        t1 = self.table_next_first_column_prompt(section_header,'Court System:')

        case = PGV(case_number=self.case_number)
        case.court_system = self.value_combined_first_column(t1,'Court System:',remove_newlines=True)
        case_number = self.value_combined_first_column(t1,'Case Number:')
        if not case_number or case_number.replace('-','').replace(' ','') != self.case_number:
            raise ParserError(f'Case number "{case_number}" in case details page does not match given: {self.case_number}')
        case.case_description = self.value_combined_first_column(t1,'Case Description:')
        case.case_type = self.value_combined_first_column(t1,'Case Type:',ignore_missing=True)
        case.filing_date_str = self.value_combined_first_column(t1,'Filing Date:',ignore_missing=True)
        case.case_status = self.value_combined_first_column(t1,'Case Status:',ignore_missing=True)
        self.case_status = case.case_status
        db.add(case)
        db.flush()
    
    ###########################################################
    # Plaintiff/Petitioner Information
    ###########################################################
    @consumer
    def plaintiff(self, db, soup):
        try:
            section_header = self.second_level_header(soup,'Plaintiff/Petitioner Information')
        except ParserError:
            return

        prev_obj = section_header
        while True:
            try:
                t1 = self.table_next_first_column_prompt(prev_obj,'Party Type:')
                name_table = self.table_next_first_column_prompt(t1,'Name:')
                address_table = self.immediate_sibling(name_table,'table')
            except ParserError:
                break
            prev_obj = address_table
        
            plaintiff = PGVPlaintiff(case_number=self.case_number)
            plaintiff.party_type = self.value_first_column(t1,'Party Type:')
            assert(plaintiff.party_type == 'Plaintiff' or plaintiff.party_type == 'Petitioner')
            plaintiff.party_number = self.value_column(t1,'Party No.:')
            plaintiff.name = self.value_first_column(name_table,'Name:')

            if list(address_table.stripped_strings):
                plaintiff.address_1 = self.value_first_column(address_table,'Address:')
                plaintiff.city = self.value_first_column(address_table,'City:')
                plaintiff.state = self.value_column(address_table,'State:')
                plaintiff.zip_code = self.value_column(address_table,'Zip Code:')
            db.add(plaintiff)
            db.flush()
        
            while True:
                try:
                    subsection_header = self.immediate_sibling(prev_obj,'table')
                    t1 = self.immediate_sibling(subsection_header,'table')
                except ParserError:
                    break
                if list(subsection_header.stripped_strings) == ['Attorney Information']:
                    self.mark_for_deletion(subsection_header)
                    prev_obj = t1
                    for span in t1.find_all('span',class_='FirstColumnPrompt',string='Name:'):
                        r1 = span.find_parent('tr')
                        r2 = self.immediate_sibling(r1,'tr')
                        r3 = self.immediate_sibling(r2,'tr')
                        r4 = self.immediate_sibling(r3,'tr')
                        attorney = PGVAttorney(case_number=self.case_number)
                        attorney.name = self.value_first_column(r1,'Name:')
                        attorney.attorney_type = self.value_first_column(r2,'Attorney Type:')
                        attorney.address = self.value_first_column(r3,'Address:')
                        attorney.city = self.value_first_column(r4,'City:')
                        attorney.state = self.value_column(r4,'State:')
                        attorney.zip_code = self.value_column(r4,'Zip Code:')
                        attorney.plaintiff_id = plaintiff.id
                        db.add(attorney)
                else:
                    break
    
    ###########################################################
    # Defendant/Respondent Information
    ###########################################################
    @consumer
    def defendant(self, db, soup):
        try:
            section_header = self.second_level_header(soup,'Defendant/Respondent Information')
        except ParserError:
            return

        prev_obj = section_header
        while True:
            try:
                t1 = self.table_next_first_column_prompt(prev_obj,'Party Type:')
                name_table = self.table_next_first_column_prompt(t1,'Name:')
                address_table = self.immediate_sibling(name_table,'table')
            except ParserError:
                break
            prev_obj = address_table
        
            defendant = PGVDefendant(case_number=self.case_number)
            defendant.party_type = self.value_first_column(t1,'Party Type:')
            assert(defendant.party_type == 'Defendant' or defendant.party_type == 'Respondent')
            defendant.party_number = self.value_column(t1,'Party No.:')
            defendant.name = self.value_first_column(name_table,'Name:')

            if list(address_table.stripped_strings):
                defendant.address_1 = self.value_first_column(address_table,'Address:')
                defendant.city = self.value_first_column(address_table,'City:')
                defendant.state = self.value_column(address_table,'State:')
                defendant.zip_code = self.value_column(address_table,'Zip Code:')
            db.add(defendant)
            db.flush()

            while True:
                try:
                    subsection_header = self.immediate_sibling(prev_obj,'table')
                    t1 = self.immediate_sibling(subsection_header,'table')
                except ParserError:
                    break
                if list(subsection_header.stripped_strings) == ['Aliases Defendant/Respondent']:
                    self.mark_for_deletion(subsection_header)
                    prev_obj = t1
                    for span in t1.find_all('span',class_='FirstColumnPrompt',string='Name:'):
                        row = span.find_parent('tr')
                        alias = PGVDefendantAlias(case_number=self.case_number)
                        alias.alias_name = self.value_first_column(row,'Name:')
                        db.add(alias)
                elif list(subsection_header.stripped_strings) == ['Attorney Information']:
                    self.mark_for_deletion(subsection_header)
                    prev_obj = t1
                    for span in t1.find_all('span',class_='FirstColumnPrompt',string='Name:'):
                        r1 = span.find_parent('tr')
                        r2 = self.immediate_sibling(r1,'tr')
                        r3 = self.immediate_sibling(r2,'tr')
                        r4 = self.immediate_sibling(r3,'tr')
                        attorney = PGVAttorney(case_number=self.case_number)
                        attorney.name = self.value_first_column(r1,'Name:')
                        attorney.attorney_type = self.value_first_column(r2,'Attorney Type:')
                        attorney.address = self.value_first_column(r3,'Address:')
                        attorney.city = self.value_first_column(r4,'City:')
                        attorney.state = self.value_column(r4,'State:')
                        attorney.zip_code = self.value_column(r4,'Zip Code:')
                        attorney.defendant_id = defendant.id
                        db.add(attorney)
                else:
                    break
    
    ###########################################################
    # Attorney Information
    ###########################################################
    def attorney(self, db, soup):
        try:
            section_header = self.first_level_header(soup,'Attorney Information')
        except ParserError:
            return
        t1 = self.table_next_first_column_prompt(section_header,'Name:')
        
        for span in t1.find_all('span',class_='FirstColumnPrompt',string='Name:'):
            r1 = span.find_parent('tr')
            r2 = self.immediate_sibling(r1,'tr')
            r3 = self.immediate_sibling(r2,'tr')
            r4 = self.immediate_sibling(r3,'tr')
            attorney = PGVAttorney(case_number=self.case_number)
            attorney.name = self.value_first_column(r1,'Name:')
            attorney.attorney_type = self.value_first_column(r2,'Attorney Type:')
            attorney.address = self.value_first_column(r3,'Address:')
            attorney.city = self.value_first_column(r4,'City:')
            attorney.state = self.value_column(r4,'State:')
            attorney.zip_code = self.value_column(r4,'Zip Code:')
            db.add(attorney)

    ###########################################################
    # Other Party Information
    ###########################################################
    @consumer
    def other_parties(self, db, soup):
        try:
            section_header = self.second_level_header(soup,'Other Party Information')
        except ParserError:
            return
        prev_obj = section_header
        while True:
            try:
                t1 = self.table_next_first_column_prompt(prev_obj,'Party Type:')
                t2 = self.table_next_first_column_prompt(t1,'Name:')
            except ParserError:
                break
            prev_obj = t2

            party = PGVOtherParty(case_number=self.case_number)
            party.party_type = self.value_first_column(t1,'Party Type:')
            party.party_number = self.value_column(t1,'Party No.:')
            party.name = self.value_first_column(t2,'Name:')
            db.add(party)
    
    ###########################################################
    # Judgment Information
    ###########################################################
    @consumer
    def judgments(self, db, soup):
        try:
            section_header = self.second_level_header(soup,'Judgment Information')
        except ParserError:
            return
        
        container = self.immediate_sibling(section_header,'span',class_='AltBodyWindow1')
        info_charge_stmt = container.find('span',class_='InfoChargeStatement')
        self.mark_for_deletion(info_charge_stmt)
        prev_obj = info_charge_stmt
        while True:
            try:
                t1 = self.table_next_first_column_prompt(prev_obj,'Judgment Date:')
                separator = self.immediate_sibling(t1,'hr')
            except ParserError:
                break
            prev_obj = separator
            judgment = PGVJudgment(case_number=self.case_number)
            judgment.judgment_date_str = self.value_first_column(t1,'Judgment Date:')
            judgment.status_date_str = self.value_column(t1,'Status Date:')
            judgment.status = self.value_first_column(t1,'Status')
            judgment.amount = self.value_column(t1,'Amount:',money=True)
            judgment.against = self.value_first_column(t1,'Against:')
            db.add(judgment)
    
    ###########################################################
    # Court Scheduling Information
    ###########################################################
    @consumer
    def court_schedule(self, db, soup):
        try:
            section_header = self.second_level_header(soup,'Court Scheduling Information')
        except ParserError:
            return
        prev_obj = section_header
        while True:
            try:
                t1 = self.table_next_first_column_prompt(prev_obj,'Event Type:')
                separator = self.immediate_sibling(t1,'hr')
            except ParserError:
                break
            prev_obj = separator

            sched = PGVCourtSchedule(case_number=self.case_number)
            sched.event_type = self.value_first_column(t1,'Event Type:')
            sched.event_date_str = self.value_first_column(t1,'Event Date:')
            sched.time_str = self.value_column(t1,'Start Time:')
            sched.result = self.value_first_column(t1,'Result:')
            sched.result_date_str = self.value_column(t1,'Result Date:')
            db.add(sched)

    ###########################################################
    # Dockets
    ###########################################################
    @consumer
    def dockets(self, db, soup):
        section_header = self.second_level_header(soup,'Dockets')
        stmt = self.immediate_sibling(section_header,'span',class_='InfoChargeStatement')
        self.mark_for_deletion(stmt)

        prev_obj = stmt
        while True:
            try:
                t1 = self.immediate_sibling(prev_obj,'table')
                separator = self.immediate_sibling(t1,'hr')
            except ParserError:
                break
            prev_obj = separator
            docket = PGVDocket(case_number=self.case_number)
            docket.date_str = self.value_first_column(t1,'Date:')
            docket.document_name = self.value_first_column(t1,'Document Name:')
            docket.docket_text = self.value_first_column(t1,'Docket Text:',ignore_missing=True)
            db.add(docket)