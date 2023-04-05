from ..models import (PG, PGCharge, PGDefendant, PGDefendantAlias, PGOtherParty, 
                      PGAttorney, PGCourtSchedule, PGDocket, PGPlaintiff)
from .base import CaseDetailsParser, consumer, ParserError, ChargeFinder
import re

class PGParser(CaseDetailsParser, ChargeFinder):
    inactive_statuses = [
        'Inactive',
        'Closed',
        'Historical'
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
        section_header = self.second_level_header(soup,'Case Information')
        t1 = self.table_next_first_column_prompt(section_header,'Court System:')

        case = PG(case_number=self.case_number)
        case.court_system = self.value_combined_first_column(t1,'Court System:',remove_newlines=True)
        case_number = self.value_combined_first_column(t1,'Case Number:')
        if case_number.replace('-','').replace(' ','') != self.case_number:
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
            except ParserError:
                break
            prev_obj = name_table
        
            plaintiff = PGPlaintiff(case_number=self.case_number)
            party_type = self.value_first_column(t1,'Party Type:')
            assert(party_type == 'Plaintiff')
            plaintiff.party_number = self.value_column(t1,'Party No.:')
            plaintiff.name = self.value_first_column(name_table,'Name:')

            try:
                address_table = self.table_next_first_column_prompt(name_table,'Address:')
            except ParserError:
                pass
            else:
                prev_obj = address_table
                plaintiff.address_1 = self.value_first_column(address_table,'Address:')
                plaintiff.city = self.value_first_column(address_table,'City:')
                plaintiff.state = self.value_column(address_table,'State:')
                plaintiff.zip_code = self.value_column(address_table,'Zip Code:')
            db.add(plaintiff)

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
            except ParserError:
                break
            prev_obj = name_table
        
            defendant = PGDefendant(case_number=self.case_number)
            party_type = self.value_first_column(t1,'Party Type:')
            assert(party_type == 'Defendant')
            defendant.party_number = self.value_column(t1,'Party No.:')
            defendant.name = self.value_first_column(name_table,'Name:')

            try:
                address_table = self.table_next_first_column_prompt(name_table,'Address:')
            except ParserError:
                pass
            else:
                prev_obj = address_table
                defendant.address_1 = self.value_first_column(address_table,'Address:')
                defendant.city = self.value_first_column(address_table,'City:')
                defendant.state = self.value_column(address_table,'State:')
                defendant.zip_code = self.value_column(address_table,'Zip Code:')
            db.add(defendant)

    ###########################################################
    # Attorney Information
    ###########################################################
    @consumer
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
            attorney = PGAttorney(case_number=self.case_number)
            attorney.name = self.value_first_column(r1,'Name:')
            attorney.attorney_type = self.value_first_column(r2,'Attorney Type:')
            attorney.address_1 = self.value_first_column(r3,'Address:')
            attorney.city = self.value_first_column(r4,'City:')
            attorney.state = self.value_column(r4,'State:')
            attorney.zip_code = self.value_column(r4,'Zip Code:')
            db.add(attorney)
    
    ###########################################################
    # Aliases Defendant/Respondent
    ###########################################################
    @consumer
    def aliases(self, db, soup):
        try:
            section_header = self.sixth_level_header(soup,'Aliases Defendant/Respondent')
        except ParserError:
            return
        t1 = self.table_next_first_column_prompt(section_header,'Name:')
        
        for span in t1.find_all('span',class_='FirstColumnPrompt',string='Name:'):
            row = span.find_parent('tr')
            alias = PGDefendantAlias(case_number=self.case_number)
            alias.alias_name = self.value_first_column(row,'Name:')
            db.add(alias)
    
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

            party = PGOtherParty(case_number=self.case_number)
            party.party_type = self.value_first_column(t1,'Party Type:')
            party.party_number = self.value_column(t1,'Party No.:')
            party.name = self.value_first_column(t2,'Name:')
            db.add(party)

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

            sched = PGCourtSchedule(case_number=self.case_number)
            sched.event_type = self.value_first_column(t1,'Event Type:')
            sched.event_date_str = self.value_first_column(t1,'Event Date:')
            sched.time_str = self.value_column(t1,'Start Time:')
            sched.result = self.value_first_column(t1,'Result:')
            sched.result_date_str = self.value_column(t1,'Result Date:')
            db.add(sched)
    
    ###########################################################
    # Charge and Disposition Information
    ###########################################################
    @consumer
    def charge(self, db, soup):
        try:
            section_header = self.second_level_header(soup,'Charge and Disposition Information')
        except ParserError:
            return
        stmt = self.immediate_sibling(section_header,'span',class_='InfoChargeStatement')
        self.mark_for_deletion(stmt)

        prev_obj = stmt
        new_charges = []
        while True:
            try:
                container = self.immediate_sibling(prev_obj,'div',class_='AltBodyWindow1')
                separator = self.immediate_sibling(container,'hr')
            except ParserError:
                break
            if not container.find('span',class_='FirstColumnPrompt',string='Charge No:'):
                break
            prev_obj = separator
            new_charge = self.parse_charge(container)
            new_charges.append(new_charge)

        for new_charge in new_charges:
            db.add(new_charge)
        new_charge_numbers = [c.charge_number for c in new_charges]
        self.find_charges(db, new_charge_numbers)

    def parse_charge(self, container):
        t1 = container.find('table')
        t2 = self.table_next_first_column_prompt(t1,'Charge:')
        t3 = self.table_next_first_column_prompt(t2,'Charge Code:')
        subsection_header = self.fifth_level_header(container,'Disposition')
        t4 = self.immediate_sibling(subsection_header,'table')
        
        charge = PGCharge(case_number=self.case_number)
        charge.charge_number = int(self.value_first_column(t1,'Charge No:'))
        charge.charge = self.value_first_column(t2,'Charge:')
        charge.charge_code = self.value_first_column(t3,'Charge Code:')
        charge.offense_date_str = self.value_first_column(t3,'Offense Date:')
        charge.arrest_tracking_number = self.value_first_column(t3,'Arrest Tracking No:')
        charge.disposition = self.value_first_column(t4,'Disposition:')
        charge.disposition_date_str = self.value_combined_first_column(t4,'Disposition Date:')
        return charge
    
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
            docket = PGDocket(case_number=self.case_number)
            docket.date_str = self.value_first_column(t1,'Date:')
            docket.document_name = self.value_first_column(t1,'Document Name:')
            docket.docket_text = self.value_first_column(t1,'Docket Text:',ignore_missing=True)
            db.add(docket)