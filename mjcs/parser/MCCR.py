from ..models import (MCCR, MCCRAttorney, MCCRCharge, MCCRCourtSchedule,
                      MCCRDefendant, MCCRDocket, MCCRBailBond, MCCRAudioMedia,
                      MCCRJudgment, MCCRProbationOfficer, MCCRAlias, MCCRBondRemitter,
                      MCCRDistrictCourtNumber, MCCRTrackingNumber, MCCRDWIMonitor)
from .base import CaseDetailsParser, consumer, ParserError, ChargeFinder
import re

city_state_zip = re.compile(r'(?P<city>[A-Z ]+) (?P<state>[A-Z]{2}) (?P<zip_code>\d{5}(-\d{4})?)')

class ContinueParsing(Exception):
    pass

class MCCRParser(CaseDetailsParser, ChargeFinder):
    inactive_statuses = [
        'CLOSED'
    ]

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
        t2 = self.immediate_sibling(t1,'table')
        t3 = self.immediate_sibling(t2,'table')

        case = MCCR(case_number=self.case_number)
        case.court_system = self.value_first_column(t1,'Court System:',remove_newlines=True)
        case_number = self.value_first_column(t1,'Case Number:')
        if case_number != self.case_number:
            raise ParserError(f'Case number "{case_number}" in case details page does not match given: {self.case_number}')
        case.sub_type = self.value_column(t1,'Sub Type:')
        tracking_number_span = t2.find('span',class_='Prompt',string='Tracking Number:')
        if tracking_number_span:
            self.mark_for_deletion(tracking_number_span)
            tracking_number_table = tracking_number_span.find_parent('table').find('table')
            for span in tracking_number_table.find_all('span',class_='Value'):
                self.mark_for_deletion(span)
                tracking_number = MCCRTrackingNumber(case_number=self.case_number)
                tracking_number.tracking_number = self.format_value(span.string)
                db.add(tracking_number)
        district_court_number_span = t2.find('span',class_='Prompt',string='District Court Number:')
        if district_court_number_span:
            self.mark_for_deletion(district_court_number_span)
            district_court_number_table = district_court_number_span.find_parent('table').find('table')
            for span in district_court_number_table.find_all('span',class_='Value'):
                self.mark_for_deletion(span)
                district_court_number = MCCRDistrictCourtNumber(case_number=self.case_number)
                district_court_number.district_court_number = self.format_value(span.string)
                db.add(district_court_number)
        case.filing_date_str = self.value_first_column(t3,'Date Filed:')
        case.case_status = self.value_first_column(t3,'Case Status:')
        db.add(case)
        db.flush()

    ###########################################################
    # DEFENDANT INFORMATION
    ###########################################################
    @consumer
    def defendant(self, db, soup):
        section_header = self.first_level_header(soup,'Defendant Information')
        info_charge_statement = self.info_charge_statement(section_header)
        t1 = self.table_next_first_column_prompt(info_charge_statement,'Name:')
        prev_obj = t1

        defendant = MCCRDefendant(case_number=self.case_number)
        defendant.name = self.value_first_column(t1,'Name:')
        defendant.gender = self.value_column(t1,'Gender:')
        defendant.DOB_str = self.value_column(t1,'DOB:')

        addr_row_1 = None
        try:
            addr_row_1 = t1.find('span',class_='FirstColumnPrompt',string='Address:')\
                        .find_parent('tr')
        except AttributeError:
            try:
                t2 = self.immediate_sibling(t1,'table')
                if 'Attorney(s) for the Defendant' in list(t2.stripped_strings) or 'Defendant Aliases' in list(t2.stripped_strings):
                    raise ContinueParsing
            except (ParserError, ContinueParsing):
                pass
            else:
                prev_obj = t2
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
                defendant.address = address_lines[0]
            elif len(address_lines) > 1:
                match = city_state_zip.fullmatch(address_lines[-1])
                if match:
                    defendant.address = "\n".join(address_lines[:-1])
                    defendant.city = match.group('city')
                    defendant.state = match.group('state')
                    defendant.zip_code = match.group('zip_code')
                else:
                    defendant.address = "\n".join(address_lines)
        db.add(defendant)

        try:
            t3 = self.immediate_sibling(prev_obj,'table')
        except ParserError:
            return
        subsection_header = t3.find('h6',string='Defendant Aliases')
        if subsection_header:
            self.mark_for_deletion(subsection_header)
            if list(subsection_header.find_parent('table').stripped_strings) == ['Defendant Aliases']:
                prev_obj = t3
                while True:
                    try:
                        alias_table = self.immediate_sibling(prev_obj,'table')
                    except ParserError:
                        break
                    prev_obj = alias_table
                    alias = MCCRAlias(case_number=self.case_number)
                    alias.alias_name = self.value_first_column(alias_table,'Name:')
                    alias.party = 'Defendant'
                    db.add(alias)
            else:
                for row in t3.find_all('tr')[1:]:
                    alias = MCCRAlias(case_number=self.case_number)
                    alias.alias_name = self.value_first_column(row,'Name:')
                    alias.party = 'Defendant'
                    db.add(alias)

    ###########################################################
    # ATTORNEY INFORMATION
    ###########################################################
    @consumer
    def attorney(self, db, soup):
        try:
            attorneys_table = soup.find('h6',string='Attorney(s) for the Defendant')\
                                  .find_parent('table')
            subsection_header = self.sixth_level_header(attorneys_table,'Attorney\(s\) for the Defendant')
        except (ParserError, AttributeError):
            return
        
        for span in attorneys_table.find_all('span',class_='FirstColumnPrompt',string='Name:'):
            phone_row = None
            t = span.find_parent('table')
            attorney = MCCRAttorney(case_number=self.case_number)
            attorney.name = self.value_first_column(t,'Name:')
            attorney.appearance_date_str = self.value_first_column(t,'Appearance Date:',ignore_missing=True)
            attorney.removal_date_str = self.value_first_column(t,'Removal Date:',ignore_missing=True)
            addr_row_1 = None
            try:
                addr_row_1 = t.find('span',class_='FirstColumnPrompt',string='Address:')\
                              .find_parent('tr')
            except AttributeError:
                address_row_table = self.immediate_sibling(t)
                try:
                    addr_row_1 = address_row_table.find('span',class_='FirstColumnPrompt',string='Address:')\
                            .find_parent('tr')
                except AttributeError:
                    pass
                else:
                    try:
                        phone_table = self.table_next_first_column_prompt(address_row_table,'Phone:')
                    except ParserError:
                        pass
                    else:
                        phone_row = phone_table.find('span',class_='FirstColumnPrompt',string='Phone:')\
                                    .find_parent('tr')

            if addr_row_1:
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
                        addr_line = self.value_first_column(addr_row,'')
                        if addr_line:
                            address_lines.append(addr_line)
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
            db.add(attorney)
    
    ###########################################################
    # COURT SCHEDULING INFORMATION
    ###########################################################
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

            sched = MCCRCourtSchedule(case_number=self.case_number)
            sched.event_date_str = self.value_first_column(t1,'Event Date:')
            sched.event_time_str = self.value_column(t1,'Event Time:',ignore_missing=True)
            sched.judge = self.value_column(t1,'Judge:',ignore_missing=True)
            if not sched.judge:
                sched.judge = self.value_column(t1,'Judge/Magistrate:',ignore_missing=True)

            loc_span = t1.find('span',class_='FirstColumnPrompt',string='Location:')
            if loc_span:
                self.mark_for_deletion(loc_span)
                loc_val_col = loc_span.find_parent('td').find_next_sibling('td')
                loc_first_span = loc_val_col.find('span',class_='Value')
                self.mark_for_deletion(loc_first_span)
                loc_strings = [self.format_value(loc_first_span.string)]
                prev_span = loc_first_span
                while True:
                    try:
                        loc_val_span = self.immediate_sibling(prev_span,'span',class_='Value')
                    except ParserError:
                        break
                    self.mark_for_deletion(loc_val_span)
                    prev_span = loc_val_span
                    loc_line = self.format_value(loc_val_span.string)
                    if loc_line:
                        loc_strings.append(loc_line)
                sched.location = "\n".join(loc_strings)

            sched.courtroom = self.value_column(t1,'Courtroom:',ignore_missing=True)
            sched.description = self.value_first_column(t1,'Description:')
            db.add(sched)
    
    ###########################################################
    # CHARGE AND DISPOSITION INFORMATION
    ###########################################################
    @consumer
    def charges(self, db, soup):
        try:
            section_header = self.first_level_header(soup,'Charge and Disposition Information')
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
            if not container.find('span',class_='FirstColumnPrompt',string='Count No:'):
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
        t2 = self.table_next_first_column_prompt(t1,'Charge Description:')
        t3 = self.table_next_first_column_prompt(t2,'Citation Number:')

        charge = MCCRCharge(case_number=self.case_number)
        charge.charge_number = self.value_first_column(t1,'Count No:')
        charge.article_section_subsection = self.value_column(t1,'ArticleSectionSubsection:')
        charge.charge_description = self.value_first_column(t2,'Charge Description:')
        charge.citation_number = self.value_first_column(t3,'Citation Number:')
        charge.plea = self.value_column(t3,'Plea:')
        
        try:
            t4 = self.table_first_columm_prompt(container,'Disposition Text:')
        except ParserError:
            pass
        else:
            charge.disposition_text = self.value_first_column(t4,'Disposition Text:')
            charge.disposition_date_str = self.value_column(t4,'Disposition Date:')
            charge.judge = self.value_first_column(t4,'Judge:',ignore_missing=True)
        
        try:
            t5 = self.table_first_columm_prompt(container,'Time Imposed:')
        except ParserError:
            pass
        else:
            subsection_header = t5.find('span',class_='FirstColumnPrompt',string='Time Imposed:')
            self.mark_for_deletion(subsection_header)
            charge.imposed_life_times = self.value_column(t5,'Life Times:')
            charge.imposed_years = self.value_column(t5,'Yrs:')
            charge.imposed_months = self.value_column(t5,'Mos:')
            charge.imposed_days = self.value_column(t5,'Days:')
            consecutive = t5.find('span',class_='Value',string='(Consecutive)')
            if consecutive:
                self.mark_for_deletion(consecutive)
                charge.imposed_consecutive = True
            concurrent = t5.find('span',class_='Value',string='(Concurrent)')
            if concurrent:
                self.mark_for_deletion(concurrent)
                charge.imposed_concurrent = True
        
        try:
            t6 = self.table_first_columm_prompt(container,'Time Suspended:')
        except ParserError:
            pass
        else:
            subsection_header = t6.find('span',class_='FirstColumnPrompt',string='Time Suspended:')
            self.mark_for_deletion(subsection_header)
            charge.time_suspended_years = self.value_column(t6,'Yrs:')
            charge.time_suspended_months = self.value_column(t6,'Mos:')
            charge.time_suspended_days = self.value_column(t6,'Days:')
            all_but = t6.find('span',class_='Prompt',string='All But')
            if all_but:
                self.mark_for_deletion(all_but)
                charge.time_suspended_all_but = True
        
        try:
            t7 = self.table_first_columm_prompt(container,'Time Served Credit:')
        except ParserError:
            pass
        else:
            subsection_header = t7.find('span',class_='FirstColumnPrompt',string='Time Served Credit:')
            self.mark_for_deletion(subsection_header)
            charge.time_served_years = self.value_column(t7,'Yrs:')
            charge.time_served_months = self.value_column(t7,'Mos:')
            charge.time_served_days = self.value_column(t7,'Days:')
        
        try:
            t8 = self.table_first_columm_prompt(container,'Probation:')
        except ParserError:
            pass
        else:
            subsection_header = t8.find('span',class_='FirstColumnPrompt',string='Probation:')
            self.mark_for_deletion(subsection_header)
            charge.probation_years = self.value_column(t8,'Yrs:')
            charge.probation_months = self.value_column(t8,'Mos:')
            charge.probation_days = self.value_column(t8,'Days:')
            supervised = t8.find('span',class_='Value',string='(Supervised)')
            if supervised:
                self.mark_for_deletion(supervised)
                charge.probation_supervised = True
            unsupervised = t8.find('span',class_='Value',string='(Unsupervised)')
            if unsupervised:
                self.mark_for_deletion(unsupervised)
                charge.probation_unsupervised = True
            charge.disposition = self.value_first_column(t8,'Case Disposition:')
        
        return charge

    #########################################################
    # JUDGMENT INFORMATION
    #########################################################
    @consumer
    def judgments(self, db, soup):
        try:
            section_header = self.first_level_header(soup,'Judgment Information')
        except ParserError:
            return
        container = self.immediate_sibling(section_header,'div',class_='AltBodyWindow1')
        stmt = container.find('span',class_='InfoChargeStatement')
        self.mark_for_deletion(stmt)
        for span in container.find_all('span',class_='FirstColumnPrompt',string='Date:'):
            t1 = span.find_parent('table')
            judgment = MCCRJudgment(case_number=self.case_number)
            judgment.date_str = self.value_first_column(t1,'Date:')
            judgment.amount = self.value_column(t1,'Amount:',money=True)
            judgment.entered_date_str = self.value_column_no_prompt(t1,'Entered',ignore_missing=True)
            judgment.satisfied_str = self.value_column_no_prompt(t1,'Satisfied',ignore_missing=True)
            judgment.vacated_date_str = self.value_column_no_prompt(t1,'Vacated',ignore_missing=True)
            judgment.amended_str = self.value_column_no_prompt(t1,'Amended',ignore_missing=True)
            judgment.renewed_str = self.value_column_no_prompt(t1,'Renewed',ignore_missing=True)
            judgment.debtor = self.value_first_column(t1,'Debtor:')
            judgment.party_role = self.value_column(t1,'Party Role:')
            db.add(judgment)

            debtor_aliases = t1.find('h6',string='Debtor Aliases')
            if debtor_aliases:
                self.mark_for_deletion(debtor_aliases)
                for row in debtor_aliases.find_parent('table').find_all('tr')[1:]:
                    alias = MCCRAlias(case_number=self.case_number)
                    alias.party = 'Debtor'
                    alias.name = self.value_first_column(row,'Name:')
                    db.add(alias)

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

            docket = MCCRDocket(case_number=self.case_number)
            docket.docket_date_str = self.value_first_column(t1,'Docket Date:')
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
                    docket_line = self.format_value(prev_span.string)
                    if docket_line:
                        ref_docket_strings.append(docket_line)
                docket.reference_docket = "\n".join(ref_docket_strings)
            docket.docket_text = self.value_first_column(t1,'Docket Text:',ignore_missing=True)
            db.add(docket)
            db.flush()
            for span in t1.find_all('span',class_='FirstColumnPrompt',string='Audio Media:'):
                row = span.find_parent('tr')
                audio = MCCRAudioMedia(case_number=self.case_number)
                audio.audio_media = self.value_first_column(row,'Audio Media:',ignore_missing=True)
                audio.audio_start = self.value_column(row,'Start:',ignore_missing=True)
                audio.audio_stop = self.value_column(row,'Stop:',ignore_missing=True)
                audio.docket_id = docket.id
                db.add(audio)

    #########################################################
    # BAIL BOND TRACKING
    #########################################################
    @consumer
    def bail_bonds(self, db, soup):
        try:
            section_header = self.first_level_header(soup,'Bail Bond Information')
        except ParserError:
            return
        prev_obj = section_header

        while True:
            try:
                t1 = self.table_next_first_column_prompt(prev_obj,'Number:')
            except ParserError:
                break
            prev_obj = t1
            
            bb = MCCRBailBond(case_number=self.case_number)
            bb.number = self.value_first_column(t1,'Number:')
            bb.bond_type = self.value_column(t1,'Type:')
            bb.amount = self.value_first_column(t1,'Amount:',money=True)
            bb.minimum_percent = self.value_column(t1,'Minimum:',percent=True)
            for span in t1.find_all('span',class_='FirstColumnPrompt',string='Remitter:'):
                remitter = MCCRBondRemitter(case_number=self.case_number)
                remitter.remitter = self.value_first_column(span.find_parent('tr'),'Remitter:')
                db.add(remitter)

            bond_history_prompt = t1.find('span',class_='FirstColumnPrompt',string='Bond History:')
            if bond_history_prompt:
                self.mark_for_deletion(bond_history_prompt)
                bond_history_val = bond_history_prompt.find_parent('td').find_next_sibling('td').find('table')
                bond_history = []
                for span in bond_history_val.find_all('span',class_='Value'):
                    self.mark_for_deletion(span)
                    addr_line = self.format_value(span.string)
                    if addr_line:
                        bond_history.append(addr_line)
                bb.bond_history = "\n".join(bond_history)
            bb.bonding_company = self.value_first_column(t1,'Bonding Company:',ignore_missing=True)
            
            address_span = t1.find('span',class_='FirstColumnPrompt',string='Address:')
            if address_span:
                address_table = address_span.find_parent('table')
                addr_row_1 = address_table.find('span',class_='FirstColumnPrompt',string='Address:')\
                                        .find_parent('tr')
                addr_line_1 = self.value_first_column(addr_row_1,'Address:')
                address_lines = [addr_line_1] if addr_line_1 else []
                prev_row = addr_row_1
                while True:
                    try:
                        addr_row = self.immediate_sibling(prev_row,'tr')
                    except ParserError:
                        break
                    prev_row = addr_row
                    if list(addr_row.stripped_strings):
                        addr_line = self.value_first_column(addr_row,'')
                        if addr_line:
                            address_lines.append(addr_line)
                bb.bonding_company_address = "\n".join(address_lines)

            if 'Agent:' in list(t1.stripped_strings):
                bb.agent = self.value_first_column(t1,'Agent:')
                agent_addr_row_1 = t1.find('span',class_='FirstColumnPrompt',string='Address:')\
                                        .find_parent('tr')
                agent_addr_line_1 = self.value_first_column(agent_addr_row_1,'Address:')
                agent_address_lines = [agent_addr_line_1] if agent_addr_line_1 else []
                prev_row = agent_addr_row_1
                while True:
                    try:
                        addr_row = self.immediate_sibling(prev_row,'tr')
                    except ParserError:
                        break
                    prev_row = addr_row
                    if list(addr_row.stripped_strings):
                        addr_line = self.value_first_column(addr_row,'')
                        if addr_line:
                            agent_address_lines.append(addr_line)
                bb.agent_address = "\n".join(agent_address_lines)
            else:
                while True:
                    try:
                        t2 = self.immediate_sibling(prev_obj, 'table')
                        if 'Number:' in list(t2.stripped_strings):
                            raise ContinueParsing
                    except (ParserError, ContinueParsing):
                        break
                    prev_obj = t2
                    
                    if 'Agent:' in list(t2.stripped_strings):
                        bb.agent = self.value_first_column(t2,'Agent:')

                        try:
                            t3 = self.table_next_first_column_prompt(t2,'Address:')
                        except ParserError:
                            pass
                        else:
                            prev_obj = t3
                            agent_address_table = t3.find('span',class_='FirstColumnPrompt',string='Address:').find_parent('table')
                            agent_addr_row_1 = agent_address_table.find('span',class_='FirstColumnPrompt',string='Address:')\
                                                    .find_parent('tr')
                            agent_addr_line_1 = self.value_first_column(agent_addr_row_1,'Address:')
                            agent_address_lines = [agent_addr_line_1] if agent_addr_line_1 else []
                            prev_row = agent_addr_row_1
                            while True:
                                try:
                                    addr_row = self.immediate_sibling(prev_row,'tr')
                                except ParserError:
                                    break
                                prev_row = addr_row
                                if list(addr_row.stripped_strings):
                                    addr_line = self.value_first_column(addr_row,'')
                                    if addr_line:
                                        agent_address_lines.append(addr_line)
                            bb.agent_address = "\n".join(agent_address_lines)
                    elif 'Remitter:' in list(t2.stripped_strings):
                        bb.remitter = self.value_first_column(t2,'Remitter:')
            db.add(bb)

    #########################################################
    # PROBATION OFFICER TRACKING
    #########################################################
    @consumer
    def probation_officers(self, db, soup):
        try:
            section_header = self.first_level_header(soup,'Probation Officer Information')
        except ParserError:
            return
        t1 = self.table_next_first_column_prompt(section_header,'Name:')
        officer = MCCRProbationOfficer(case_number=self.case_number)
        officer.name = self.value_first_column(t1,'Name:')
        addr_span = t1.find('span',class_='FirstColumnPrompt',string='Address:')
        addr_table = t1
        if not addr_span:
            t2 = self.immediate_sibling(t1,'table')
            addr_span = t2.find('span',class_='FirstColumnPrompt',string='Address:')
            addr_table = t2
        if addr_span:
            addr_row = addr_span.find_parent('tr')
            address_lines = [self.value_first_column(addr_table,'Address:')]
            prev_row = addr_row
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
                officer.address = address_lines[0]
            else:
                match = city_state_zip.fullmatch(address_lines[-1])
                if match:
                    officer.address = "\n".join(address_lines[:-1])
                    officer.city = match.group('city')
                    officer.state = match.group('state')
                    officer.zip_code = match.group('zip_code')
                else:
                    officer.address = "\n".join(address_lines)
        db.add(officer)
    
    #########################################################
    # DWI MONITOR TRACKING
    #########################################################
    @consumer
    def dwi_monitors(self, db, soup):
        try:
            section_header = self.first_level_header(soup,'DWI Monitor Information')
        except ParserError:
            return
        t1 = self.table_next_first_column_prompt(section_header,'Name:')
        monitor = MCCRDWIMonitor(case_number=self.case_number)
        monitor.name = self.value_first_column(t1,'Name:')
        addr_span = t1.find('span',class_='FirstColumnPrompt',string='Address:')
        addr_table = t1
        if not addr_span:
            t2 = self.immediate_sibling(t1,'table')
            addr_span = t2.find('span',class_='FirstColumnPrompt',string='Address:')
            addr_table = t2
        if addr_span:
            addr_row = addr_span.find_parent('tr')
            address_lines = [self.value_first_column(addr_table,'Address:')]
            prev_row = addr_row
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
                monitor.address = address_lines[0]
            else:
                match = city_state_zip.fullmatch(address_lines[-1])
                if match:
                    monitor.address = "\n".join(address_lines[:-1])
                    monitor.city = match.group('city')
                    monitor.state = match.group('state')
                    monitor.zip_code = match.group('zip_code')
                else:
                    monitor.address = "\n".join(address_lines)
        db.add(monitor)