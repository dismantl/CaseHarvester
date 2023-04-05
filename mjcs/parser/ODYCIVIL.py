from ..models import (ODYCIVIL, ODYCIVILReferenceNumber, ODYCIVILCause, 
                       ODYCIVILCauseRemedy, ODYCIVILDefendant, ODYCIVILInvolvedParty,
                       ODYCIVILAlias, ODYCIVILAttorney, ODYCIVILJudgment, 
                       ODYCIVILJudgmentStatus, ODYCIVILJudgmentComment, ODYCIVILCourtSchedule, ODYCIVILWarrant,
                       ODYCIVILDocument, ODYCIVILService, ODYCIVILBondSetting, ODYCIVILBailBond, ODYCIVILDisposition)
from .base import CaseDetailsParser, consumer, ParserError, reference_number_re
import re
from bs4 import BeautifulSoup, SoupStrainer
import logging

logger = logging.getLogger('mjcs')

# Note that consumers may not be called in order
class ODYCIVILParser(CaseDetailsParser):
    inactive_statuses = [
        'Closed / Inactive',
        'Closed',
        'Completed'
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
        case = ODYCIVIL(case_number=self.case_number)
        section_header = self.first_level_header(soup,'Case Information')

        case_info_table = self.table_next_first_column_prompt(section_header,'Court System:')
        case.court_system = self.value_first_column(case_info_table,'Court System:',remove_newlines=True)
        case.location = self.value_first_column(case_info_table,'Location:')
        case_number = self.value_first_column(case_info_table,'Case Number:')
        if self.case_number.lower() != case_number.replace('-','').replace('.','').replace('`','').lower():
            raise ParserError('Case number "%s" in case details page does not match given: %s' % (case_number, self.case_number))
        case.case_title = self.value_first_column(case_info_table,'Title:')
        case.case_type = self.value_first_column(case_info_table,'Case Type:')
        case.filing_date_str = self.value_first_column(case_info_table,'Filing Date:')
        case.case_status = self.value_first_column(case_info_table,'Case Status:')
        self.case_status = case.case_status
        case.magistrate = self.value_first_column(case_info_table, 'Magistrate:', ignore_missing=True)
        case.judicial_officer = self.value_first_column(case_info_table, 'Judicial Officer:', ignore_missing=True)
        db.add(case)

    #########################################################
    # CAUSES INFORMATION
    #########################################################
    @consumer
    def causes(self, db, soup):
        try:
            section_header = self.first_level_header(soup, 'Causes Information')
        except ParserError:
            return
        container = self.immediate_sibling(section_header,'div',class_='AltBodyWindow1')
        for claim_first_span in container.find_all('span', class_='Prompt', string='File Date:'):
            claim_table = claim_first_span.find_parent('table')
            cause = ODYCIVILCause(case_number=self.case_number)
            cause.file_date_str = self.value_multi_column(claim_table,'File Date:')
            cause.cause_description = self.value_multi_column(claim_table,'Cause Description')
            cause.filed_by = self.value_multi_column(claim_table,'Filed By:')
            cause.filed_against = self.value_multi_column(claim_table,'Filed Against:')
            db.add(cause)
            header_row = claim_table.find('th',class_='tableHeader',string='Remedy Type').find_parent('tr')
            self.mark_for_deletion(header_row)
            prev_obj = header_row
            while True:
                try:
                    row = self.immediate_sibling(prev_obj,'tr')
                except ParserError:
                    break
                prev_obj = row
                vals = row.find_all('span',class_='Value')
                db.flush()
                remedy = ODYCIVILCauseRemedy(case_number=self.case_number)
                remedy.cause_id = cause.id
                remedy.remedy_type = self.format_value(vals[0].string)
                self.mark_for_deletion(vals[0])
                remedy.amount = self.format_value(vals[1].string,money=True)
                self.mark_for_deletion(vals[1])
                remedy.comment = self.format_value(vals[2].string)
                self.mark_for_deletion(vals[2])
                db.add(remedy)

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
        prompt_re = re.compile(reference_number_re)
        empty_re = re.compile(r'^\s*:\s*$')
        while True:
            try:
                t = self.immediate_sibling(prev_obj,'table')
            except ParserError:
                break
            prev_obj = t
            prompt_span = t.find('span',class_='FirstColumnPrompt',string=prompt_re)
            if not prompt_span:
                if t.find('span',class_='FirstColumnPrompt',string=empty_re):
                    self.mark_for_deletion(t)
                    continue
                break
            ref_num = ODYCIVILReferenceNumber(case_number=self.case_number)
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
        plaintiff_id = None
        defendant_id = None
        while True:
            party = None
            
            try:
                subsection_header = self.immediate_sibling(prev_obj,'h5')
            except ParserError:
                try:  # sometimes there are parties that are minors and so their info is not included, but they can still have attorneys and aliases
                    t = self.immediate_sibling(prev_obj,'table')
                except ParserError:
                    break
                if not list(t.stripped_strings):
                    party_type = None
                    prev_obj = t
                else:
                    break
            else:
                self.mark_for_deletion(subsection_header)
                prev_obj = subsection_header
                party_type = self.format_value(subsection_header.string)

            if party_type == 'Attorney for Defendant' and defendant_id:
                party = ODYCIVILAttorney(case_number=self.case_number)
                party.party_id = defendant_id
            elif party_type == 'Attorney for Plaintiff' and plaintiff_id:
                party = ODYCIVILAttorney(case_number=self.case_number)
                party.party_id = plaintiff_id
            elif party_type == 'Defendant':
                party = ODYCIVILDefendant(case_number=self.case_number)
            else:
                party = ODYCIVILInvolvedParty(case_number=self.case_number)
                if party_type:
                    party.party_type = party_type

            try:
                name_table = self.table_next_first_column_prompt(prev_obj,'Name:')
            except ParserError:
                pass
            else:
                # Attorneys for defendants and plaintiffs are listed in two different ways
                
                party.name = self.value_first_column(name_table,'Name:')
                prev_obj = name_table

                while True:
                    try:
                        t = self.immediate_sibling(prev_obj,'table')
                    except ParserError:
                        break

                    if 'Address:' in t.stripped_strings:
                        address_table = t
                        rows = address_table.find_all('tr')
                        party.address_1 = self.value_first_column(address_table,'Address:')
                        if len(rows) == 3:
                            party.address_2 = self.format_value(rows[1].find('span',class_='Value').string)
                            self.mark_for_deletion(rows[1])
                        party.city = self.value_first_column(address_table,'City:')
                        party.state = self.value_column(address_table,'State:')
                        party.zip_code = self.value_column(address_table,'Zip Code:',ignore_missing=True)
                    elif 'Removal Date:' in t.stripped_strings:
                        party.removal_date_str = self.value_first_column(t,'Removal Date:')
                    elif 'Appearance Date:' in t.stripped_strings:
                        party.appearance_date_str = self.value_first_column(t,'Appearance Date:')
                    elif 'DOB:' in t.stripped_strings:
                        party.DOB_str = self.value_combined_first_column(t,'DOB:')
                    elif len(list(t.stripped_strings)) > 0:
                        break
                    prev_obj = t

            db.add(party)
            db.flush()
            if party_type == 'Plaintiff':
                plaintiff_id = party.id
            elif party_type == 'Defendant':
                defendant_id = party.id

            # Aliases and Attorneys
            while True:
                try:
                    subsection_header = self.immediate_sibling(prev_obj,'table')
                    subsection_table = self.immediate_sibling(subsection_header,'table')
                except ParserError:
                    break
                prev_obj = subsection_table
                subsection_name = subsection_header.find('h5').string
                self.mark_for_deletion(subsection_header)
                if subsection_name == 'Aliases':
                    for span in subsection_table.find_all('span',class_='FirstColumnPrompt'):
                        row = span.find_parent('tr')
                        alias_ = ODYCIVILAlias(case_number=self.case_number)
                        if type(party) == ODYCIVILDefendant:
                            alias_.defendant_id = party.id
                        else:
                            alias_.party_id = party.id
                        prompt_re = re.compile(r'^([\w ]+)\s*:\s*$')
                        alias_.alias = self.value_first_column(row, span.string)
                        alias_.alias_type = prompt_re.fullmatch(span.string).group(1)
                        db.add(alias_)
                elif 'Attorney(s) for the' in subsection_name:
                    for span in subsection_table.find_all('span',class_='FirstColumnPrompt',string='Name:'):
                        attorney = ODYCIVILAttorney(case_number=self.case_number)
                        if type(party) == ODYCIVILDefendant:
                            attorney.defendant_id = party.id
                        else:
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
                                # Workaround for addresses that list lines 1 and 3 but not 2
                                try:
                                    address_row_3 = self.row_next_first_column_prompt(prev_row,'Address Line 3:')
                                except ParserError:
                                    pass
                                else:
                                    prev_row = address_row_3
                                    attorney.address_2 = self.value_first_column(address_row_3,'Address Line 3:')
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

            try:
                separator = self.immediate_sibling(prev_obj,'hr')
            except ParserError:
                break
            prev_obj = separator

    #########################################################
    # COURT SCHEDULING INFORMATION
    #########################################################
    @consumer
    def court_schedule(self, db, soup):
        try:
            section_header = self.first_level_header(soup, 'Court Scheduling Information')
        except ParserError:
            return
        container = self.immediate_sibling(section_header,'div',class_='AltBodyWindow1')
        header_row = container.find('tr')
        self.mark_for_deletion(header_row)
        prev_obj = header_row
        while True:
            try:
                row = self.immediate_sibling(prev_obj,'tr')
            except ParserError:
                break
            prev_obj = row
            vals = row.find_all('span',class_='Value')
            schedule = ODYCIVILCourtSchedule(case_number=self.case_number)
            try:
                schedule.event_type = self.format_value(vals[0].string)
                self.mark_for_deletion(vals[0])
                schedule.date_str = self.format_value(vals[1].string)
                self.mark_for_deletion(vals[1])
                schedule.time_str = self.format_value(vals[2].string)
                self.mark_for_deletion(vals[2])
                schedule.judge = self.format_value(vals[3].string)
                self.mark_for_deletion(vals[3])
                schedule.location = self.format_value(vals[4].string)
                self.mark_for_deletion(vals[4])
                schedule.room = self.format_value(vals[5].string)
                self.mark_for_deletion(vals[5])
                schedule.result = self.format_value(vals[6].string)
                self.mark_for_deletion(vals[6])
            except IndexError:
                schedule.event_type = self.format_value(vals[0].string)
                self.mark_for_deletion(vals[0])
                schedule.date_str = self.format_value(vals[1].string)
                self.mark_for_deletion(vals[1])
                schedule.time_str = self.format_value(vals[2].string)
                self.mark_for_deletion(vals[2])
                schedule.location = self.format_value(vals[3].string)
                self.mark_for_deletion(vals[3])
                schedule.room = self.format_value(vals[4].string)
                self.mark_for_deletion(vals[4])
                schedule.result = self.format_value(vals[5].string)
                self.mark_for_deletion(vals[5])
            db.add(schedule)
    
    #########################################################
    # JUDGMENT INFORMATION
    #########################################################
    @consumer
    def judgments(self, db, soup):
        for section_header in soup.find_all('h5', string="Judgment Information"):
            self.mark_for_deletion(section_header)
            section_header_t = section_header.find_parent('table')
            if section_header_t:
                section_header = section_header_t
            section = self.immediate_sibling(section_header,'div',class_='AltBodyWindow1')
            self.judgment(db, section)
            
            if section.find('h5', string='Case Judgment Comment History'):
                section_header = section.find('h5', string='Case Judgment Comment History')
                self.mark_for_deletion(section_header)
                table = self.immediate_sibling(section_header, 'table')
                for row in table.find_all('tr'):
                    self.mark_for_deletion(row)
                    jc = ODYCIVILJudgmentComment(case_number=self.case_number)
                    text = row.find('td').string
                    for line in text.split('\n'):
                        label = line.split(':')[0].lower()
                        val = line.split(':')[1].strip()
                        if val[-1] == ';':
                            val = val.rstrip(';')
                        try:
                            assert(hasattr(jc,label))
                        except AssertionError:
                            logger.error(f'{label} not found')
                            raise
                        if re.fullmatch(r'\$?[\d\.,]+', val):
                            setattr(jc, label, self.format_value(val,money=True))
                        else:
                            setattr(jc, label, self.format_value(val))
                    db.add(jc)
            
            if section.find('h5', string='Case Disposition History'):
                section_header = section.find('h5', string='Case Disposition History')
                self.mark_for_deletion(section_header)
                table = self.immediate_sibling(section_header, 'table')
                for row in table.find_all('tr'):
                    self.mark_for_deletion(row)
                    d = ODYCIVILDisposition(case_number=self.case_number)
                    text = row.find('td').string
                    for line in text.split('\n'):
                        label = line.split(':')[0].lower().replace(' ','_')
                        val = line.split(':')[1].strip()
                        if val[-1] == ';':
                            val = val.rstrip(';')
                        try:
                            assert(hasattr(d,label))
                        except AssertionError:
                            logger.error(f'{label} not found')
                            raise
                        if re.fullmatch(r'\$?[\d\.,]+', val):
                            setattr(d, label, self.format_value(val,money=True))
                        else:
                            setattr(d, label, self.format_value(val))
                    db.add(d)

    def judgment(self, db, section):
        for t in section.find_all('table', recursive=False):
            j = ODYCIVILJudgment(case_number=self.case_number)
            if t.find('span',class_='Value',string='LandLord Tenants'):
                judgment = t.find('span',class_='Value',string='LandLord Tenants')
                if judgment:
                    self.mark_for_deletion(judgment)
                    r1 = judgment.find_parent('tr')
                    judgment_description = self.immediate_sibling(r1, 'tr').find('h6')
                    self.mark_for_deletion(judgment_description)
                    j.judgment_description = self.format_value(judgment_description.string)
                j.judgment_type = 'LandLord Tenants'
                try:
                    j.judgment_event_type = self.value_multi_column(t,'Judgment Event Type:')
                except ParserError:
                    j.judgment_event_type = self.value_first_column(t,'Judgment Event Type:')
                j.judge = self.value_multi_column(t, 'Judge:',ignore_missing=True)
                j.judgment_for = self.value_multi_column(t,'Judgment For:',ignore_missing=True)
                j.possession = self.value_multi_column(t,'Possession:',ignore_missing=True,boolean_value=True)
                j.premise_description = self.value_multi_column(t,'Premise Description:',ignore_missing=True)
                j.costs = self.value_multi_column(t,'Costs ?',boolean_value=True,ignore_missing=True)
                j.costs_ = self.value_multi_column(t,'^Costs:',money=True,ignore_missing=True)
                j.stay_upon_filing_of_bond = self.value_multi_column(t,'Stay Upon filing of Bond ?',boolean_value=True,ignore_missing=True)
                j.stay_of_execution_until_str = self.value_multi_column(t,'Stay of execution until:',ignore_missing=True)
                j.stay_details = self.value_first_column(t,'Stay Details:',ignore_missing=True)
                j.monetary_judgment = self.value_multi_column(t,'Monetary Judgment ?',boolean_value=True,ignore_missing=True)
                j.judgment_against = self.value_multi_column(t,'Judgment Against:',ignore_missing=True)
                j.judgment = self.value_multi_column(t,'Judgment:',ignore_missing=True)
                j.appeal_bond_amount = self.value_multi_column(t,'Appeal Bond Amount:',ignore_missing=True,money=True)
                j.court_costs = self.value_multi_column(t,'Court Costs:',money=True,ignore_missing=True)
                j.attorney_fee = self.value_multi_column(t,'Attorney Fees:',money=True,ignore_missing=True)
                j.party = self.value_first_column(t,'Party:',ignore_missing=True)
                j.comment = self.value_first_column_table(t,'Comment:',ignore_missing=True)
                if not j.comment:
                    j.comment = self.value_multi_column(t,'Comment:',ignore_missing=True)
            elif t.find('span',class_='Value',string='Land Lord Tenants'):
                judgment = t.find('span',class_='Value',string='Land Lord Tenants')
                if judgment:
                    self.mark_for_deletion(judgment)
                    r1 = judgment.find_parent('tr')
                    judgment_description = self.immediate_sibling(r1, 'tr').find('h6')
                    self.mark_for_deletion(judgment_description)
                    j.judgment_description = self.format_value(judgment_description.string)
                j.judgment_type = 'Land Lord Tenants'
                j.judgment_event_type = self.value_first_column_table(t,'Judgment Event Type:')
                j.judgment_for = self.value_first_column_table(t,'Judgment For:',ignore_missing=True)
                j.possession = self.value_first_column_table(t,'Possession ?',ignore_missing=True,boolean_value=True)
                j.premise_description = self.value_first_column_table(t,'Premise Description:',ignore_missing=True)
                j.costs = self.value_first_column(t,'Costs ?',boolean_value=True,ignore_missing=True)
                j.costs_ = self.value_first_column(t,'^Costs:',ignore_missing=True)
                j.stay_upon_filing_of_bond = self.value_first_column_table(t,'Stay Upon filing of Bond ?',boolean_value=True,ignore_missing=True)
                j.stay_of_execution_until_str = self.value_first_column_table(t,'Stay of execution until:',ignore_missing=True)
                j.stay_details = self.value_first_column_table(t,'Stay Details:',ignore_missing=True)
                j.monetary_judgment = self.value_first_column_table(t,'Monetary Judgment ?',boolean_value=True,ignore_missing=True)
                j.judgment_against = self.value_first_column_table(t,'Judgment Against:',ignore_missing=True)
                j.judgment = self.value_first_column(t,'Judgment:',ignore_missing=True)
                j.appeal_bond_amount = self.value_first_column(t,'Appeal Bond Amount:',ignore_missing=True,money=True)
                j.court_costs = self.value_first_column(t,'Court Costs:',money=True,ignore_missing=True)
                j.attorney_fee = self.value_first_column(t,'Attorney Fees:',ignore_missing=True)
                j.comment = self.value_first_column_table(t,'Comment:',ignore_missing=True)
                j.party = self.value_first_column(t,'Party:',ignore_missing=True)
            elif t.find('span',class_='Value',string='Monetary'):
                judgment = t.find('span',class_='Value',string='Monetary')
                if judgment:
                    self.mark_for_deletion(judgment)
                    r1 = judgment.find_parent('tr')
                    judgment_description = self.immediate_sibling(r1, 'tr').find('h6')
                    self.mark_for_deletion(judgment_description)
                    j.judgment_description = self.format_value(judgment_description.string)
                j.judgment_type = 'Monetary'
                j.judgment_event_type = self.value_first_column(t,'Judgment Event Type:')
                j.judge = self.value_multi_column(t, 'Judge:',ignore_missing=True)
                j.postjudgment_interest = self.value_multi_column(t,'PostJudgment Interest:',ignore_missing=True)
                if not j.postjudgment_interest:
                    j.postjudgment_interest = self.value_multi_column(t,'Post-Judgment Interest:',ignore_missing=True)
                j.principal_amount = self.value_multi_column(t,'Principal Amount:',money=True)
                j.prejudgment_interest = self.value_multi_column(t,'PreJudgment Interest:',money=True,ignore_missing=True)
                if not j.prejudgment_interest:
                    j.prejudgment_interest = self.value_multi_column(t,'Pre-Judgment Interest:',money=True,ignore_missing=True)
                j.other_fee = self.value_multi_column(t,'Other Fee:',money=True,ignore_missing=True)
                j.service_fee = self.value_multi_column(t,'Service Fee:',money=True,ignore_missing=True)
                j.appearance_fee = self.value_multi_column(t,'Appearance Fee:',money=True,ignore_missing=True)
                j.witness_fee = self.value_multi_column(t,'Witness Fee:',money=True,ignore_missing=True)
                j.filing_fee = self.value_multi_column(t,'Filing Fee:',money=True,ignore_missing=True)
                j.attorney_fee = self.value_multi_column(t,'Attorney Fee:',money=True,ignore_missing=True)
                j.amount_of_judgment = self.value_multi_column(t,'Amount of Judgment:',money=True)
                j.total_indexed_judgment = self.value_multi_column(t,'Total Indexed Judgment:',money=True,ignore_missing=True)
                if not j.total_indexed_judgment:
                    j.total_indexed_judgment = self.value_multi_column(t,'Total Judgment Index:',money=True,ignore_missing=True)
                j.comment = self.value_multi_column(t,'Comment:')
                j.judgment_against = self.value_multi_column(t,'Judgment Against:')
                j.judgment_in_favor_of = self.value_multi_column(t,'Judgment in Favor of:')
                j.judgment_ordered_date_str = self.value_multi_column(t,'Judgment Ordered Date:')
                j.judgment_entry_date_str = self.value_multi_column(t,'Judgment Entry Date:')
                j.judgment_expiration_date_str = self.value_multi_column(t,'Judgment Expiration Date:',ignore_missing=True)
                j.judgment_details = self.value_multi_column(t,'Judgment Details:',ignore_missing=True)
                j.interest_rate_details = self.value_multi_column(t,'Interest Rate Details:',ignore_missing=True)
            elif t.find('span',class_='Value',string='Property'):
                judgment = t.find('span',class_='Value',string='Property')
                if judgment:
                    self.mark_for_deletion(judgment)
                    r1 = judgment.find_parent('tr')
                    judgment_description = self.immediate_sibling(r1, 'tr').find('h6')
                    self.mark_for_deletion(judgment_description)
                    j.judgment_description = self.format_value(judgment_description.string)
                j.judgment_type = 'Property'
                j.judgment_event_type = self.value_multi_column(t,'Judgment Event Type:')
                j.judge = self.value_multi_column(t,'Judge:',ignore_missing=True)
                j.judgment_expiration_date_str = self.value_multi_column(t,'Judgment Expiration Date:',ignore_missing=True)
                awarded_to_span = t.find('span', class_='Prompt', string='Awarded To:')
                if awarded_to_span:
                    self.mark_for_deletion(awarded_to_span)
                    awarded_to_val = self.immediate_sibling(awarded_to_span.find_parent('td'), 'td')
                    self.mark_for_deletion(awarded_to_val)
                    j.awarded_to = self.format_value(list(awarded_to_val.stripped_strings)[0])
                j.property_value = self.value_multi_column(t,'Property Value:',money=True,ignore_missing=True)
                j.damages = self.value_multi_column(t,'Damages:',money=True,ignore_missing=True)
                j.property_description = self.value_multi_column(t,'Property Description:',ignore_missing=True)
                if not j.property_description:
                    j.property_description = self.value_multi_column_table(t,'Property Description:',ignore_missing=True)
                j.replivin_or_detinue = self.value_multi_column(t,'Replivin or Detinue:',ignore_missing=True)
                j.r_d_amount = self.value_multi_column(t,'R/D Amount:',money=True,ignore_missing=True)
                j.judgment_against = self.value_multi_column(t,'Judgment Against:')
                j.judgment_in_favor_of = self.value_multi_column(t,'Judgment in Favor of:')
                j.judgment_ordered_date_str = self.value_multi_column(t,'Judgment Ordered Date:')
                j.judgment_entry_date_str = self.value_multi_column(t,'Judgment Entry Date:',ignore_missing=True)
                if not j.judgment_entry_date_str:
                    j.judgment_entry_date_str = self.value_multi_column(t,'Judgment Entered Date:',ignore_missing=True)
            elif t.find('span',class_='Value',string='Non Monetary'):
                judgment = t.find('span',class_='Value',string='Non Monetary')
                if judgment:
                    self.mark_for_deletion(judgment)
                    r1 = judgment.find_parent('tr')
                    judgment_description = self.immediate_sibling(r1, 'tr').find('h6')
                    self.mark_for_deletion(judgment_description)
                    j.judgment_description = self.format_value(judgment_description.string)
                j.judgment_type = 'Non Monetary'
                j.judgment_event_type = self.value_first_column(t,'Judgment Event Type:')
                j.judge = self.value_multi_column(t,'Judge:',ignore_missing=True)
                j.judgment_against = self.value_multi_column(t,'Judgment Against:')
                j.judgment_in_favor_of = self.value_multi_column(t,'Judgment in Favor of:')
                j.judgment_ordered_date_str = self.value_multi_column(t,'Judgment Ordered Date:')
                j.judgment_entry_date_str = self.value_multi_column(t,'Judgment Entered Date:')
                j.judgment_expiration_date_str = self.value_multi_column(t,'Judgment Expiration Date:')
                j.comment = self.value_multi_column(t,'Judgment Comments:',ignore_missing=True)
                j.judgment_details = self.value_multi_column(t,'Judgment Details:',ignore_missing=True)
                j.trial_judgment_against_plaintiff = self.value_multi_column(t,'Trial Judgment Against a Plaintiff:',ignore_missing=True)
            elif t.find('span', class_='FirstColumnPrompt', string='Judgment Event Type:'):
                j.judgment_event_type = self.value_first_column(t,'Judgment Event Type:')
                j.judge = self.value_first_column(t,'Judge:')
                j.party = self.value_first_column(t,'Party:',ignore_missing=True)

            db.add(j)
            db.flush()

            # Judgment Status
            status_header = t.find('th',class_='tableHeader',string='Judgment Status')
            if status_header:
                status_header_row = status_header.find_parent('tr')
                self.mark_for_deletion(status_header_row)
                prev_obj = status_header_row
                while True:
                    try:
                        row = self.immediate_sibling(prev_obj,'tr')
                    except ParserError:
                        break
                    prev_obj = row
                    vals = row.find_all('span',class_='Value')
                    js = ODYCIVILJudgmentStatus(case_number=self.case_number)
                    js.judgment_id = j.id
                    js.judgment_status = self.format_value(vals[0].string)
                    self.mark_for_deletion(vals[0])
                    js.judgment_date_str = self.format_value(vals[1].string)
                    self.mark_for_deletion(vals[1])
                    try:
                        js.comment = self.format_value(vals[2].string)
                        self.mark_for_deletion(vals[2])
                    except IndexError:
                        pass
                    db.add(js)

    #########################################################
    # WARRANTS INFORMATION
    #########################################################
    @consumer
    def warrant(self, db, soup):
        try:
            section_header = self.first_level_header(soup,'Warrants Information')
        except ParserError:
            return
        container = self.immediate_sibling(section_header,'div',class_='AltBodyWindow1')
        header_row = container.find('tr')
        self.mark_for_deletion(header_row)
        prev_obj = header_row
        while True:
            try:
                row = self.immediate_sibling(prev_obj,'tr')
            except ParserError:
                break
            prev_obj = row
            vals = row.find_all('span',class_='Value')
            warrant = ODYCIVILWarrant(case_number=self.case_number)
            try:
                warrant.warrant_type = self.format_value(vals[0].string)
                self.mark_for_deletion(vals[0])
                warrant.issue_date_str = self.format_value(vals[1].string)
                self.mark_for_deletion(vals[1])
                warrant.judge = self.format_value(vals[2].string)
                self.mark_for_deletion(vals[2])
                warrant.last_status = self.format_value(vals[3].string)
                self.mark_for_deletion(vals[3])
                warrant.status_date_str = self.format_value(vals[4].string)
                self.mark_for_deletion(vals[4])
            except IndexError:
                warrant.warrant_type = self.format_value(vals[0].string)
                self.mark_for_deletion(vals[0])
                warrant.issue_date_str = self.format_value(vals[1].string)
                self.mark_for_deletion(vals[1])
                warrant.last_status = self.format_value(vals[2].string)
                self.mark_for_deletion(vals[2])
                warrant.status_date_str = self.format_value(vals[3].string)
                self.mark_for_deletion(vals[3])
            db.add(warrant)

    #########################################################
    # BOND SETTING INFORMATION
    #########################################################
    @consumer
    def bond_setting(self, db, soup):
        try:
            section_header = self.first_level_header(soup,'Bond Setting Information')
        except ParserError:
            return

        container = self.immediate_sibling(section_header, 'div', class_='AltBodyWindow1')
        for t in container.find_all('table'):
            if len(list(t.stripped_strings)) > 0:
                b = ODYCIVILBondSetting(case_number=self.case_number)
                b.bail_date_str = self.value_first_column(t,'Bail Date:')
                b.bail_setting_type = self.value_first_column(t,'Bail Setting Type:')
                b.bail_amount = self.value_first_column(t,'Bail Amount:',money=True)
                b.judge = self.value_first_column(t,'Judge:',ignore_missing=True)
                db.add(b)

    #########################################################
    # BAIL BOND INFORMATION
    #########################################################
    @consumer
    def bail_bond(self, db, soup):
        try:
            section_header = self.first_level_header(soup,'Bail Bond Information')
        except ParserError:
            return
        container = self.immediate_sibling(section_header,'div',class_='AltBodyWindow1')
        header_row = container.find('tr')
        self.mark_for_deletion(header_row)
        prev_obj = header_row
        while True:
            try:
                row = self.immediate_sibling(prev_obj,'tr')
            except ParserError:
                break
            prev_obj = row
            vals = row.find_all('span',class_='Value')
            b = ODYCIVILBailBond(case_number=self.case_number)
            b.bond_type = self.format_value(vals[0].string)
            self.mark_for_deletion(vals[0])
            b.bond_amount_set = self.format_value(vals[1].string,money=True)
            self.mark_for_deletion(vals[1])
            b.bond_status_date_str = self.format_value(vals[2].string)
            self.mark_for_deletion(vals[2])
            b.bond_status = self.format_value(vals[3].string)
            self.mark_for_deletion(vals[3])
            db.add(b)

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
            doc = ODYCIVILDocument(case_number=self.case_number)
            doc.file_date_str = self.value_first_column(t,'File Date:')
            self.mark_for_deletion(t.find('span',class_='FirstColumnPrompt',string='Filed By:'))
            doc.document_name = self.value_first_column(t,'Document Name:')
            doc.comment = self.value_first_column(t,'Comment:', ignore_missing=True)
            db.add(doc)

    #########################################################
    # SERVICE INFORMATION
    #########################################################
    @consumer
    def service(self, db, soup):
        try:
            section_header = self.first_level_header(soup,'Service Information')
        except ParserError:
            return

        section_container = self.immediate_sibling(section_header,'div',class_='AltBodyWindow1')
        header_row = section_container.find('tr')
        self.mark_for_deletion(header_row)
        prev_obj = header_row
        while True:
            try:
                row = self.immediate_sibling(prev_obj,'tr')
            except ParserError:
                break
            prev_obj = row
            vals = row.find_all('span',class_='Value')
            service = ODYCIVILService(case_number=self.case_number)
            service.service_type = self.format_value(vals[0].string)
            self.mark_for_deletion(vals[0])
            service.issued_date_str = self.format_value(vals[1].string,money=True)
            self.mark_for_deletion(vals[1])
            db.add(service)
