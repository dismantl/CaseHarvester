from ..models import (ODYCIVIL, ODYCIVILReferenceNumber, ODYCIVILCause, 
                       ODYCIVILCauseRemedy, ODYCIVILDefendant, ODYCIVILInvolvedParty,
                       ODYCIVILAlias, ODYCIVILAttorney, ODYCIVILJudgment, 
                       ODYCIVILJudgmentStatus, ODYCIVILJudgmentComment, ODYCIVILCourtSchedule, ODYCIVILWarrant,
                       ODYCIVILDocument, ODYCIVILService, ODYCIVILBondSetting, ODYCIVILBailBond, ODYCIVILDisposition)
from .base import CaseDetailsParser, consumer, ParserError
import re
from bs4 import BeautifulSoup, SoupStrainer

# Note that consumers may not be called in order
class ODYCIVILParser(CaseDetailsParser):
    inactive_statuses = [
        # TODO
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
        if self.case_number.lower() != case_number.replace('-','').lower():
            raise ParserError('Case number "%s" in case details page does not match given: %s' % (case_number, self.case_number))
        case.case_title = self.value_first_column(case_info_table,'Title:')
        case.case_type = self.value_first_column(case_info_table,'Case Type:')
        case.filing_date_str = self.value_first_column(case_info_table,'Filing Date:')
        case.case_status = self.value_first_column(case_info_table,'Case Status:')
        self.case_status = case.case_status
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
                self.mark_for_deletion(row)
                vals = row.find_all('span',class_='Value')
                db.flush()
                remedy = ODYCIVILCauseRemedy(case_number=self.case_number)
                remedy.cause_id = cause.id
                remedy.remedy_type = self.format_value(vals[0].string)
                remedy.amount = self.format_value(vals[1].string,money=True)
                remedy.comment = self.format_value(vals[2].string)
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
        while True:
            try:
                t = self.immediate_sibling(prev_obj,'table')
            except ParserError:
                break
            prev_obj = t
            prompt_re = re.compile(r'^([\w \'\-/]+)\s*:\s*$')
            prompt_span = t.find('span',class_='FirstColumnPrompt',string=prompt_re)
            if not prompt_span:
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
        self.consume_parties(db, section_header)

    def consume_parties(self, db, prev_obj):
        plaintiff_id = None
        defendant_id = None
        while True:
            party = None
            
            try:
                subsection_header = self.immediate_sibling(prev_obj,'h5')
            except ParserError:
                break
            self.mark_for_deletion(subsection_header)
            prev_obj = subsection_header
            party_type = self.format_value(subsection_header.string)

            try:
                name_table = self.table_next_first_column_prompt(subsection_header,'Name:')
            except ParserError:
                pass
            else:
                # Attorneys for defendants and plaintiffs are listed in two different ways
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
                    party.party_type = party_type
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
            self.mark_for_deletion(row)
            vals = row.find_all('span',class_='Value')
            schedule = ODYCIVILCourtSchedule(case_number=self.case_number)
            schedule.event_type = self.format_value(vals[0].string)
            schedule.date_str = self.format_value(vals[1].string)
            schedule.time_str = self.format_value(vals[2].string)
            schedule.location = self.format_value(vals[3].string)
            schedule.room = self.format_value(vals[4].string)
            schedule.result = self.format_value(vals[5].string)
            db.add(schedule)
    
    #########################################################
    # JUDGMENT INFORMATION
    #########################################################
    @consumer
    def judgments(self, db, soup):
        for section_header in soup.find_all('h5', string="Judgment Information"):
            self.mark_for_deletion(section_header)
            section = self.immediate_sibling(section_header,'div',class_='AltBodyWindow1')
            if section.find('span',class_='Value',string='Monetary') \
                    or section.find('span',class_='Value',string='Property'):
                self.judgment(db, section, 'Monetary')
                self.judgment(db, section, 'Property')
            elif section.find('span', class_='FirstColumnPrompt', string='Judgment Event Type:'):
                for span in section.find_all('span', class_='FirstColumnPrompt', string='Judgment Event Type:'):
                    row = span.find_parent('tr')
                    j = ODYCIVILJudgment(case_number=self.case_number)
                    j.judgment_event_type = self.value_first_column(row,'Judgment Event Type:')
                    db.add(j)
            
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
                        assert(hasattr(jc,label))
                        if re.fullmatch(r'[\d\.,]+', val):
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
                        assert(hasattr(d,label))
                        if re.fullmatch(r'[\d\.,]+', val):
                            setattr(d, label, self.format_value(val,money=True))
                        else:
                            setattr(d, label, self.format_value(val))
                    db.add(d)

    def judgment(self, db, section, judgment_type):
        for judgment in section.find_all('span',class_='Value',string=judgment_type):
            self.mark_for_deletion(judgment)
            r1 = judgment.find_parent('tr')
            t1 = judgment.find_parent('table')
            judgment_description = self.immediate_sibling(r1, 'tr').find('h6')
            self.mark_for_deletion(judgment_description)
            j = ODYCIVILJudgment(case_number=self.case_number)
            j.judgment_description = self.format_value(judgment_description.string)
            j.judgment_type = judgment_type
            if judgment_type == 'Monetary':
                j.judgment_event_type = self.value_first_column(t1,'Judgment Event Type:')
                j.postjudgment_interest = self.value_multi_column(t1,'PostJudgment Interest:')
                j.principal_amount = self.value_multi_column(t1,'Principal Amount:',money=True)
                j.prejudgment_interest = self.value_multi_column(t1,'PreJudgment Interest:',money=True)
                j.other_fee = self.value_multi_column(t1,'Other Fee:',money=True)
                j.service_fee = self.value_multi_column(t1,'Service Fee:',money=True)
                j.appearance_fee = self.value_multi_column(t1,'Appearance Fee:',money=True)
                j.witness_fee = self.value_multi_column(t1,'Witness Fee:',money=True)
                j.filing_fee = self.value_multi_column(t1,'Filing Fee:',money=True)
                j.attorney_fee = self.value_multi_column(t1,'Attorney Fee:',money=True)
                j.amount_of_judgment = self.value_multi_column(t1,'Amount of Judgment:',money=True)
                j.total_indexed_judgment = self.value_multi_column(t1,'Total Indexed Judgment:',money=True)
                j.comment = self.value_multi_column(t1,'Comment:')
            elif judgment_type == 'Property':
                j.judgment_event_type = self.value_multi_column(t1,'Judgment Event Type:')
                awarded_to_span = t1.find('span', class_='Prompt', string='Awarded To:')
                self.mark_for_deletion(awarded_to_span)
                awarded_to_val = self.immediate_sibling(awarded_to_span.find_parent('td'), 'td')
                self.mark_for_deletion(awarded_to_val)
                j.awarded_to = self.format_value(list(awarded_to_val.stripped_strings)[0])
                j.property_value = self.value_multi_column(t1,'Property Value:',money=True)
                j.damages = self.value_multi_column(t1,'Damages:',money=True)
                j.property_description = self.value_multi_column(t1,'Property Description:')
                j.replivin_or_detinue = self.value_multi_column(t1,'Replivin or Detinue:')
                j.r_d_amount = self.value_multi_column(t1,'R/D Amount:',money=True)
            j.judgment_against = self.value_multi_column(t1,'Judgment Against:')
            j.judgment_in_favor_of = self.value_multi_column(t1,'Judgment in Favor of:')
            j.judgment_ordered_date_str = self.value_multi_column(t1,'Judgment Ordered Date:')
            j.judgment_entry_date_str = self.value_multi_column(t1,'Judgment Entry Date:')

            db.add(j)
            db.flush()

            # Judgment Status
            status_header_row = t1.find('th',class_='tableHeader',string='Judgment Status').find_parent('tr')
            self.mark_for_deletion(status_header_row)
            prev_obj = status_header_row
            while True:
                try:
                    row = self.immediate_sibling(prev_obj,'tr')
                except ParserError:
                    break
                prev_obj = row
                self.mark_for_deletion(row)
                vals = row.find_all('span',class_='Value')
                js = ODYCIVILJudgmentStatus(case_number=self.case_number)
                js.judgment_id = j.id
                js.judgment_status = self.format_value(vals[0].string)
                js.judgment_date_str = self.format_value(vals[1].string)
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
            self.mark_for_deletion(row)
            vals = row.find_all('span',class_='Value')
            warrant = ODYCIVILWarrant(case_number=self.case_number)
            warrant.warrant_type = self.format_value(vals[0].string)
            warrant.issue_date_str = self.format_value(vals[1].string)
            warrant.last_status = self.format_value(vals[2].string)
            warrant.status_date_str = self.format_value(vals[3].string)
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

        prev_obj = section_header
        while True:
            try:
                t = self.immediate_sibling(prev_obj,'table')
                separator = self.immediate_sibling(t,'hr')
            except ParserError:
                break
            prev_obj = separator
            b = ODYCIVILBondSetting(case_number=self.case_number)
            b.bail_date_str = self.value_first_column(t,'Bail Date:')
            b.bail_setting_type = self.value_first_column(t,'Bail Setting Type:')
            b.bail_amount = self.value_first_column(t,'Bail Amount:',money=True)
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
            self.mark_for_deletion(row)
            vals = row.find_all('span',class_='Value')
            b = ODYCIVILBailBond(case_number=self.case_number)
            b.bond_type = self.format_value(vals[0].string)
            b.bond_amount_set = self.format_value(vals[1].string)
            b.bond_status_date_str = self.format_value(vals[2].string)
            b.bond_status = self.format_value(vals[3].string)
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
            doc.filed_by = self.value_first_column(t,'Filed By:')
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
            self.mark_for_deletion(row)
            vals = row.find_all('span',class_='Value')
            service = ODYCIVILService(case_number=self.case_number)
            service.service_type = self.format_value(vals[0].string)
            service.issued_date_str = self.format_value(vals[1].string,money=True)
            service.service_status = self.format_value(vals[2].string)
            db.add(service)
