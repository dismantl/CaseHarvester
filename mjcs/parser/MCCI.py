from sqlalchemy.sql.expression import true
from ..models import (MCCI, MCCIAttorney, MCCICourtSchedule, MCCIDefendant, MCCIDocket,
                   MCCIInterestedParty, MCCIIssue, MCCIJudgment, MCCIPlaintiff,
                   MCCIAlias, MCCIWard, MCCIAudioMedia, MCCIGarnishee, MCCIResidentAgent)
from .base import CaseDetailsParser, consumer, ParserError
import re
from bs4 import BeautifulSoup, SoupStrainer

city_state_zip = re.compile(r'(?P<city>[A-Z ]+) (?P<state>[A-Z]{2}) (?P<zip_code>\d{5}(-\d{4})?)')

class ContinueParsing(Exception):
    pass

class MCCIParser(CaseDetailsParser):
    inactive_statuses = [
        'CLOSED',
        'EXPUNGED'
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
        subheaders = soup.find_all('div',class_='Subheader')
        for subheader in subheaders:
            subheader.decompose()

    def footer(self, soup):
        footer = soup.find('div',class_='InfoStatement',string=re.compile('This is an electronic case record'))
        footer.decompose()

    #########################################################
    # CASE INFORMATION
    #########################################################
    def case(self, db, soup):
        section_header = self.first_level_header(soup,'Case Information')
        t1 = self.table_next_first_column_prompt(section_header,'Court System:')
        t2 = self.table_next_first_column_prompt(t1,'Date Filed:')

        case = MCCI(case_number=self.case_number)
        case.court_system = self.value_first_column(t1,'Court System:',remove_newlines=True)
        case_number = self.value_first_column(t1,'Case Number:')
        if self.case_number.lower() != case_number.replace('-','').lower():
            raise ParserError('Case number "%s" in case details page does not match given: %s' % (case_number, self.case_number))
        case.sub_type = self.value_column(t1,'Sub Type:')
        case.filing_date_str = self.value_first_column(t2,'Date Filed:')
        case.case_status = self.value_first_column(t2,'Case Status:')
        self.case_status = case.case_status
        db.add(case)
    
    #########################################################
    # PLAINTIFF INFORMATION
    #########################################################
    @consumer
    def plaintiff(self, db, soup):
        try:
            section_header = self.first_level_header(soup, 'Plaintiff Information')
        except ParserError:
            return
        info_charge_stmt = self.immediate_sibling(section_header,'span',class_='InfoChargeStatement')
        self.mark_for_deletion(info_charge_stmt)
        self.consume_parties(db, 'Plaintiff', info_charge_stmt)
    
    #########################################################
    # DEFENDANT INFORMATION
    #########################################################
    @consumer
    def defendant(self, db, soup):
        try:
            section_header = self.first_level_header(soup, 'Defendant Information')
        except ParserError:
            return
        info_charge_stmt = self.immediate_sibling(section_header,'span',class_='InfoChargeStatement')
        self.mark_for_deletion(info_charge_stmt)
        self.consume_parties(db, 'Defendant', info_charge_stmt)
    
    #########################################################
    # WARD INFORMATION
    #########################################################
    @consumer
    def ward(self, db, soup):
        try:
            section_header = self.first_level_header(soup, 'Ward Information')
        except ParserError:
            return
        info_charge_stmt = self.immediate_sibling(section_header,'span',class_='InfoChargeStatement')
        self.mark_for_deletion(info_charge_stmt)
        self.consume_parties(db, 'Ward', info_charge_stmt)
    
    #########################################################
    # INTERESTED PARTY INFORMATION
    #########################################################
    @consumer
    def interested_party(self, db, soup):
        try:
            section_header = self.first_level_header(soup, 'Interested Party Information')
        except ParserError:
            return
        info_charge_stmt = self.immediate_sibling(section_header,'span',class_='InfoChargeStatement')
        self.mark_for_deletion(info_charge_stmt)
        self.consume_parties(db, 'Interested Party', info_charge_stmt)
    
    #########################################################
    # OTHER PARTY INFORMATION
    #########################################################
    @consumer
    def other_party(self, db, soup):
        try:
            section_header = self.first_level_header(soup, 'Other Party Information')
        except ParserError:
            return
        info_charge_stmt = self.immediate_sibling(section_header,'span',class_='InfoChargeStatement')
        self.mark_for_deletion(info_charge_stmt)
        self.consume_parties(db, 'Other', info_charge_stmt)
    
    #########################################################
    # GARNISHEE INFORMATION
    #########################################################
    @consumer
    def garnishee(self, db, soup):
        try:
            section_header = self.first_level_header(soup, 'Garnishee Information')
        except ParserError:
            return
        info_charge_stmt = self.immediate_sibling(section_header,'span',class_='InfoChargeStatement')
        self.mark_for_deletion(info_charge_stmt)
        self.consume_parties(db, 'Garnishee', info_charge_stmt)

    def consume_parties(self, db, party_type, prev_obj):
        while True:
            try:
                t1 = self.table_next_first_column_prompt(prev_obj, 'Name:')
            except ParserError:
                break
            prev_obj = t1

            if party_type == 'Defendant':
                party = MCCIDefendant(case_number=self.case_number)
            elif party_type == 'Plaintiff':
                party = MCCIPlaintiff(case_number=self.case_number)
            elif party_type == 'Ward':
                party = MCCIWard(case_number=self.case_number)
            elif party_type == 'Garnishee':
                party = MCCIGarnishee(case_number=self.case_number)
            else:
                party = MCCIInterestedParty(case_number=self.case_number)
            party.name = self.value_first_column(t1,'Name:')
            
            addr_row_1 = None
            try:
                addr_row_1 = t1.find('span',class_='FirstColumnPrompt',string='Address:')\
                            .find_parent('tr')
            except AttributeError:
                try:
                    t2 = self.immediate_sibling(t1,'table')
                    if f'Attorney(s) for the {party_type}' in list(t2.stripped_strings) or f'{party_type} Aliases' in list(t2.stripped_strings):
                        raise ContinueParsing
                except (ParserError, ContinueParsing):
                    pass
                else:
                    prev_obj = t2
                    try:
                        errant_row = self.immediate_sibling(t2,'tr')
                        prev_obj = errant_row
                    except ParserError:
                        pass
                    addr_row_1 = t2.find('span',class_='FirstColumnPrompt',string='Address:')\
                                .find_parent('tr')
            
            if addr_row_1:
                addr_line_1 = self.value_first_column(addr_row_1,'Address:')
                address_lines = [addr_line_1] if addr_line_1 else []
                prev_row = addr_row_1
                while True:
                    try:
                        addr_row = self.immediate_sibling(prev_row,'tr')
                    except ParserError:
                        break
                    prev_row = addr_row
                    addr_line = self.value_first_column(addr_row,'')
                    if addr_line:
                        address_lines.append(addr_line)
                if len(address_lines) == 1:
                    party.address = address_lines[0]
                elif len(address_lines) > 1:
                    match = city_state_zip.fullmatch(address_lines[-1])
                    if match:
                        party.address = "\n".join(address_lines[:-1])
                        party.city = match.group('city')
                        party.state = match.group('state')
                        party.zip_code = match.group('zip_code')
                    else:
                        party.address = "\n".join(address_lines)
            db.add(party)
            db.flush()
        
            while True:
                try:
                    errant_row = self.immediate_sibling(prev_obj,'tr')
                    prev_obj = errant_row
                except ParserError:
                    pass

                combined_alias_table = False
                try:
                    subsection_table = self.immediate_sibling(prev_obj,'table')
                    subsection_header = subsection_table.find('h6')
                    if list(subsection_table.stripped_strings) != [f'{party_type} Aliases']:
                        combined_alias_table = True
                except ParserError:
                    break
                self.mark_for_deletion(subsection_header)
                prev_obj = subsection_table
                
                try:
                    errant_row = self.immediate_sibling(prev_obj,'tr')
                    prev_obj = errant_row
                except ParserError:
                    pass
                
                if subsection_header.string == f'{party_type} Aliases':
                    if combined_alias_table:
                        for row in subsection_table.find_all('tr')[1:]:
                            alias = MCCIAlias(case_number=self.case_number)
                            alias.party = party_type
                            alias.name = self.value_first_column(row,'Name:')
                            db.add(alias)
                    else:
                        while True:
                            try:
                                t1 = self.immediate_sibling(prev_obj,'table')
                                if len(list(t1.stripped_strings)) > 2:
                                    raise ContinueParsing
                            except (ParserError, ContinueParsing):
                                break
                            prev_obj = t1
                            alias = MCCIAlias(case_number=self.case_number)
                            alias.party = party_type
                            alias.name = self.value_first_column(t1,'Name:')
                            db.add(alias)
                elif subsection_header.string == f'Attorney(s) for the {party_type}':
                    for span in subsection_table.find_all('span',class_='FirstColumnPrompt',string='Name:'):
                        phone_row = None
                        t1 = span.find_parent('table')
                        attorney = MCCIAttorney(case_number=self.case_number)
                        attorney.name = self.value_first_column(t1,'Name:')
                        attorney.appearance_date_str = self.value_first_column(t1,'Appearance Date:',ignore_missing=True)
                        attorney.removal_date_str = self.value_first_column(t1,'Removal Date:',ignore_missing=True)
                        try:
                            addr_row_1 = t1.find('span',class_='FirstColumnPrompt',string='Address:')\
                                        .find_parent('tr')
                        except AttributeError:
                            address_row_table = self.immediate_sibling(t1)
                            addr_row_1 = address_row_table.find('span',class_='FirstColumnPrompt',string='Address:')\
                                        .find_parent('tr')
                            try:
                                phone_table = self.table_next_first_column_prompt(address_row_table,'Phone:')
                            except ParserError:
                                pass
                            else:
                                phone_row = phone_table.find('span',class_='FirstColumnPrompt',string='Phone:')\
                                            .find_parent('tr')

                        address_lines = [self.value_first_column(addr_row_1,'Address:')]
                        prev_row = addr_row_1
                        while True:
                            try:
                                addr_row = self.immediate_sibling(prev_row,'tr')
                                if addr_row.find('span',class_='FirstColumnPrompt',string='Phone:'):
                                    raise ContinueParsing
                            except (ParserError, ContinueParsing):
                                break
                            prev_row = addr_row
                            if list(addr_row.stripped_strings):
                                address_lines.append(self.value_first_column(addr_row,''))
                        if len(address_lines) == 1:
                            attorney.address = address_lines[0]
                        else:
                            match = city_state_zip.fullmatch(address_lines[-1])
                            if match:
                                attorney.address = "\n".join(address_lines[:-1])
                                attorney.city = match.group('city')
                                attorney.state = match.group('state')
                                attorney.zip_code = match.group('zip_code')
                            else:
                                attorney.address = "\n".join(address_lines)
                        if not phone_row:
                            try:
                                phone_row = self.immediate_sibling(prev_row,'tr')
                            except ParserError:
                                pass
                        if phone_row:
                            attorney.phone = self.value_first_column(phone_row,'Phone:')
                        if party_type == 'Defendant':
                            attorney.defendant_id = party.id
                        elif party_type == 'Plaintiff':
                            attorney.plaintiff_id = party.id
                        elif party_type == 'Ward':
                            attorney.ward_id = party.id
                        db.add(attorney)
                elif subsection_header.string == f'Resident Agent for {party_type}':
                    for span in subsection_table.find_all('span',class_='FirstColumnPrompt',string='Name:'):
                        t1 = span.find_parent('table')
                        agent = MCCIResidentAgent(case_number=self.case_number)
                        agent.name = self.value_first_column(t1,'Name:')
                        try:
                            addr_row_1 = t1.find('span',class_='FirstColumnPrompt',string='Address:')\
                                        .find_parent('tr')
                        except AttributeError:
                            address_row_table = self.immediate_sibling(t1)
                            addr_row_1 = address_row_table.find('span',class_='FirstColumnPrompt',string='Address:')\
                                        .find_parent('tr')

                        address_lines = [self.value_first_column(addr_row_1,'Address:')]
                        prev_row = addr_row_1
                        while True:
                            try:
                                addr_row = self.immediate_sibling(prev_row,'tr')
                                if addr_row.find('span',class_='FirstColumnPrompt',string='Phone:'):
                                    raise ContinueParsing
                            except (ParserError, ContinueParsing):
                                break
                            prev_row = addr_row
                            if list(addr_row.stripped_strings):
                                address_lines.append(self.value_first_column(addr_row,''))
                        if len(address_lines) == 1:
                            agent.address = address_lines[0]
                        else:
                            match = city_state_zip.fullmatch(address_lines[-1])
                            if match:
                                agent.address = "\n".join(address_lines[:-1])
                                agent.city = match.group('city')
                                agent.state = match.group('state')
                                agent.zip_code = match.group('zip_code')
                            else:
                                agent.address = "\n".join(address_lines)
                        if party_type == 'Plaintiff':
                            agent.plaintiff_id = party.id
                        else:
                            raise ParserError(f'Cannot handle resident agent for {party_type}')
                        db.add(agent)
            
            separator = self.immediate_sibling(prev_obj,'hr')
            prev_obj = separator
    
    #########################################################
    # ISSUES INFORMATION
    #########################################################
    @consumer
    def issues(self, db, soup):
        try:
            section_header = self.first_level_header(soup,'Issues Information')
        except ParserError:
            return
        
        t1 = self.table_next_first_column_prompt(section_header,'Issue:')
        for span in t1.find_all('span',class_='FirstColumnPrompt',string='Issue:'):
            row = span.find_parent('tr')
            issue = MCCIIssue(case_number=self.case_number)
            issue.issue = self.value_first_column(row,'Issue:')
            db.add(issue)
    
    #########################################################
    # DOCUMENT TRACKING
    #########################################################
    @consumer
    def documents(self, db, soup):
        try:
            section_header = self.first_level_header(soup,'Document Tracking')
        except ParserError:
            return
        
        prev_obj = section_header
        while True:
            try:
                t1 = self.table_next_first_column_prompt(prev_obj,'Docket Date:')
                separator = self.immediate_sibling(t1,'hr')
            except ParserError:
                break
            prev_obj = separator

            docket = MCCIDocket(case_number=self.case_number)
            docket.date_str = self.value_first_column(t1,'Docket Date:')
            docket.docket_number = self.value_column(t1,'Docket Number:')
            docket.docket_description = self.value_first_column(t1,'Docket Description:')
            docket.docket_type = self.value_first_column(t1,'Docket Type:')
            docket.filed_by = self.value_column(t1,'Filed By:',ignore_missing=True)
            docket.status = self.value_column(t1,'Status:',ignore_missing=True)
            docket.ruling_judge = self.value_first_column(t1,'Ruling Judge/Magistrate:',ignore_missing=True)
            if not docket.ruling_judge:
                docket.ruling_judge = self.value_first_column(t1,'Ruling Judge:',ignore_missing=True)
            reference_docket_span = t1.find('span',class_='FirstColumnPrompt',string='Reference Docket(s):')
            if reference_docket_span:
                self.mark_for_deletion(reference_docket_span)
                first_ref_docket_val_span = reference_docket_span.find_parent('td').find_next_sibling('td').find('span',class_='Value')
                prev_span = first_ref_docket_val_span
                ref_docket_strings = [self.format_value(first_ref_docket_val_span.string)]
                while True:
                    self.mark_for_deletion(prev_span)
                    prev_span = prev_span.find_next_sibling('span')
                    if not prev_span or prev_span.get('class') != ['Value']:
                        break
                    ref_docket_strings.append(self.format_value(prev_span.string))
                docket.reference_docket = "\n".join(ref_docket_strings)
            docket.docket_text = self.value_first_column(t1,'Docket Text:')
            db.add(docket)
            db.flush()
            for span in t1.find_all('span',class_='FirstColumnPrompt',string='Audio Media:'):
                row = span.find_parent('tr')
                audio = MCCIAudioMedia(case_number=self.case_number)
                audio.audio_media = self.value_first_column(row,'Audio Media:',ignore_missing=True)
                audio.audio_start = self.value_column(row,'Start:',ignore_missing=True)
                audio.audio_stop = self.value_column(row,'Stop:',ignore_missing=True)
                audio.docket_id = docket.id
                db.add(audio)
    
    #########################################################
    # COURT SCHEDULING INFORMATION
    #########################################################
    @consumer
    def court_schedule(self, db, soup):
        try:
            section_header = self.first_level_header(soup,'Court Scheduling Information')
        except ParserError:
            return
        
        info_charge_stmt = self.immediate_sibling(section_header,'span',class_='InfoChargeStatement')
        self.mark_for_deletion(info_charge_stmt)
        prev_obj = info_charge_stmt
        while True:
            try:
                t1 = self.table_next_first_column_prompt(prev_obj,'Event Date:')
                separator = self.immediate_sibling(t1,'hr')
            except ParserError:
                break
            prev_obj = separator

            sched = MCCICourtSchedule(case_number=self.case_number)
            sched.date_str = self.value_first_column(t1,'Event Date:')
            sched.time_str = self.value_column(t1,'Event Time:',ignore_missing=True)
            sched.judge = self.value_column(t1,'Judge:',ignore_missing=True)
            if not sched.judge:
                sched.judge = self.value_column(t1,'Judge/Magistrate:',ignore_missing=True)
            location_span = t1.find('span',class_='FirstColumnPrompt',string='Location:')
            if location_span:
                self.mark_for_deletion(location_span)
                first_location_val_span = location_span.find_parent('td').find_next_sibling('td').find('span',class_='Value')
                prev_span = first_location_val_span
                location_strings = [self.format_value(first_location_val_span.string)]
                while True:
                    self.mark_for_deletion(prev_span)
                    prev_span = prev_span.find_next_sibling('span')
                    if not prev_span or prev_span.get('class') != ['Value']:
                        break
                    location_strings.append(self.format_value(prev_span.string))
                sched.location = "\n".join(location_strings)
            sched.courtroom = self.value_column(t1,'Courtroom:',ignore_missing=True)
            sched.description = self.value_first_column(t1,'Description:')
            db.add(sched)
    
    #########################################################
    # JUDGMENT INFORMATION
    #########################################################
    @consumer
    def judgments(self, db, soup):
        try:
            section_header = self.first_level_header(soup,'Judgment Information')
        except ParserError:
            return
        
        window_div = self.immediate_sibling(section_header,'div',class_='AltBodyWindow1')
        info_charge_stmt = window_div.find('span',class_='InfoChargeStatement')
        self.mark_for_deletion(info_charge_stmt)
        prev_obj = info_charge_stmt
        while True:
            try:
                t1 = self.table_next_first_column_prompt(prev_obj,'Date:')
                separator = self.immediate_sibling(t1,'hr')
            except ParserError:
                break
            prev_obj = separator

            judgment = MCCIJudgment(case_number=self.case_number)
            judgment.date_str = self.value_first_column(t1,'Date:')
            judgment.amount = self.value_column(t1,'Amount:',money=True)
            judgment.entered_str = self.value_column_no_prompt(t1,'Entered',ignore_missing=True)
            judgment.satisfied_str = self.value_column_no_prompt(t1,'Satisfied',ignore_missing=True)
            judgment.vacated_str = self.value_column_no_prompt(t1,'Vacated',ignore_missing=True)
            judgment.amended_str = self.value_column_no_prompt(t1,'Amended',ignore_missing=True)
            judgment.renewed_str = self.value_column_no_prompt(t1,'Renewed',ignore_missing=True)
            judgment.debtor = self.value_first_column(t1,'Debtor:')
            judgment.party_role = self.value_column(t1,'Party Role:')
            db.add(judgment)

            debtor_aliases = t1.find('h6',string='Debtor Aliases')
            if debtor_aliases:
                self.mark_for_deletion(debtor_aliases)
                for row in debtor_aliases.find_parent('table').find_all('tr')[1:]:
                    alias = MCCIAlias(case_number=self.case_number)
                    alias.party = 'Debtor'
                    alias.name = self.value_first_column(row,'Name:')
                    db.add(alias)



