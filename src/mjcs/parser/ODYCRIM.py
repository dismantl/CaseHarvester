from ..models import (ODYCRIM, ODYCRIMReferenceNumber, ODYCRIMDefendant,
                     ODYCRIMInvolvedParty, ODYCRIMAlias, ODYCRIMAttorney,
                     ODYCRIMCourtSchedule, ODYCRIMCharge, ODYCRIMProbation,
                     ODYCRIMRestitution, ODYCRIMWarrant, ODYCRIMBailBond,
                     ODYCRIMBondSetting, ODYCRIMDocument, ODYCRIMService)
from .base import CaseDetailsParser, consumer, ParserError
import re
from bs4 import BeautifulSoup, SoupStrainer

# Note that consumers may not be called in order
class ODYCRIMParser(CaseDetailsParser):
    inactive_statuses = [
        'Citation Voided',
        'Inactive / Incompetency',
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
        subheader.decompose()

    def footer(self, soup):
        footer = soup.find('div',class_='InfoStatement',string=re.compile('This is an electronic case record'))
        footer.decompose()

    #########################################################
    # CASE INFORMATION
    #########################################################
    def case(self, db, soup):
        case = ODYCRIM(case_number=self.case_number)
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
            prompt_re = re.compile(r'^([\w \'\-/]+)\s*:\s*$')
            prompt_span = t.find('span',class_='FirstColumnPrompt',string=prompt_re)
            if not prompt_span:
                break
            ref_num = ODYCRIMReferenceNumber(case_number=self.case_number)
            ref_num.ref_num = self.value_first_column(t, prompt_span.string)
            ref_num.ref_num_type = prompt_re.fullmatch(prompt_span.string).group(1)
            db.add(ref_num)

    #########################################################
    # DEFENDENT INFORMATION
    #########################################################
    @consumer
    def defendant(self, db, soup):
        section_header = self.first_level_header(soup,'Defendant Information')
        self.consume_parties(db, section_header)

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
            
            if str(prev_obj) == '<h5>Defendant</h5>':
                continue
            
            # Name, Agency
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
                    party = ODYCRIMAttorney(case_number=self.case_number)
                    party.party_id = defendant_id
                elif party_type == 'Attorney for Plaintiff' and plaintiff_id:
                    party = ODYCRIMAttorney(case_number=self.case_number)
                    party.party_id = plaintiff_id
                elif party_type == 'Defendant':
                    party = ODYCRIMDefendant(case_number=self.case_number)
                else:
                    party = ODYCRIMInvolvedParty(case_number=self.case_number)
                    party.party_type = party_type
                party.name = self.value_first_column(name_table,'Name:')
                party.agency_name = self.value_first_column(name_table,'AgencyName:',ignore_missing=True)
                prev_obj = name_table

                while True:
                    try:
                        t = self.immediate_sibling(prev_obj,'table')
                    except ParserError:
                        break

                    if 'Race:' in t.stripped_strings or 'DOB:' in t.stripped_strings:
                        demographics_table = t
                        party.race = self.value_first_column(demographics_table,'Race:')
                        party.sex = self.value_column(demographics_table,'Sex:')
                        party.height = self.value_column(demographics_table,'Height:')
                        party.weight = self.value_column(demographics_table,'Weight:',numeric=True)
                        party.hair_color = self.value_first_column(demographics_table,'HairColor:')
                        party.eye_color = self.value_column(demographics_table,'EyeColor:')
                        party.DOB_str = self.value_first_column(demographics_table,'DOB:',ignore_missing=True)
                    elif 'Address:' in t.stripped_strings:
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
                            alias_ = ODYCRIMAlias(case_number=self.case_number)
                            if type(party) == ODYCRIMDefendant:
                                alias_.defendant_id = party.id
                            else:
                                alias_.party_id = party.id
                            prompt_re = re.compile(r'^([\w ]+)\s*:\s*$')
                            alias_.alias = self.value_first_column(row, span.string)
                            alias_.alias_type = prompt_re.fullmatch(span.string).group(1)
                            db.add(alias_)
                    elif 'Attorney(s) for the' in subsection_name:
                        for span in subsection_table.find_all('span',class_='FirstColumnPrompt',string='Name:'):
                            attorney = ODYCRIMAttorney(case_number=self.case_number)
                            if type(party) == ODYCRIMDefendant:
                                attorney.defendant_id = party.id
                            else:
                                attorney.party_id = party.id
                            name_row = span.find_parent('tr')
                            attorney.name = self.value_first_column(name_row,'Name:')
                            try:
                                address_row = self.row_next_first_column_prompt(name_row,'Address Line 1:')
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

            if type(party) != ODYCRIMDefendant:  # Defendant section doesn't separate parties with <hr>
                separator = self.immediate_sibling(prev_obj,'hr')
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
            schedule = ODYCRIMCourtSchedule(case_number=self.case_number)
            schedule.event_type = self.format_value(vals[0].string)
            schedule.date_str = self.format_value(vals[1].string)
            schedule.time_str = self.format_value(vals[2].string)
            schedule.location = self.format_value(vals[3].string)
            schedule.room = self.format_value(vals[4].string)
            schedule.result = self.format_value(vals[5].string)
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

        prev_obj = section_header
        while True:
            try:
                container = self.immediate_sibling(prev_obj,'div',class_='AltBodyWindow1')
            except ParserError:
                break
            if not container.find('span',class_='Prompt',string='Charge No:'):
                break
            prev_obj = container
            t1 = container.find('table')
            charge = ODYCRIMCharge(case_number=self.case_number)
            charge.charge_number = self.value_multi_column(t1,'Charge No:')
            charge.cjis_code = self.value_column(t1,'CJIS Code:')
            charge.statute_code = self.value_column(t1,'Statute Code:')
            t2 = self.immediate_sibling(t1,'table')
            charge.charge_description = self.value_multi_column(t2,'Charge Description:')
            charge.charge_class = self.value_column(t2,'Charge Class:')
            t3 = self.immediate_sibling(t2,'table')
            probable_cause = self.value_multi_column(t3,'Probable Cause:')
            self.probable_cause = True if probable_cause == 'YES' else False
            t4 = self.immediate_sibling(t3,'table')
            charge.offense_date_from_str = self.value_multi_column(t4,'Offense Date From:')
            charge.offense_date_to_str = self.value_column(t4,'To:')
            charge.agency_name = self.value_multi_column(t4,'Agency Name:')
            charge.officer_id = self.value_column(t4,'Officer ID:')

            # Disposition
            try:
                subsection_header = container.find('i',string='Disposition').find_parent('left')
            except (ParserError, AttributeError):
                pass
            else:
                self.mark_for_deletion(subsection_header)
                t1 = self.immediate_sibling(subsection_header,'table')
                charge.plea = self.value_multi_column(t1,'Plea:',ignore_missing=True)
                charge.plea_date_str = self.value_column(t1,'Plea Date:',ignore_missing=True)
                charge.disposition = self.value_multi_column(t1,'Disposition:')
                charge.disposition_date_str = self.value_column(t1,'Disposition Date:')

            # Converted Disposition
            try:
                subsection_header = container.find('i',string='Converted Disposition:').find_parent('left')
            except (ParserError, AttributeError):
                pass
            else:
                self.mark_for_deletion(subsection_header)
                t = self.immediate_sibling(subsection_header,'table')
                self.mark_for_deletion(t)
                charge.converted_disposition = '\n'.join(t.stripped_strings)

            # Jail
            try:
                subsection_header = container.find('i',string='Jail').find_parent('left')
            except (ParserError, AttributeError):
                pass
            else:
                self.mark_for_deletion(subsection_header)
                t = self.immediate_sibling(subsection_header,'table')
                charge.jail_life = self.value_multi_column(t,'Life:',boolean_value=True)
                charge.jail_death = self.value_multi_column(t,'Death:',boolean_value=True)
                charge.jail_start_date_str = self.value_multi_column(t,'Start Date:')
                jail_row = self.row_label(t,'Jail Term:')
                charge.jail_years = self.value_column(jail_row,'Yrs:')
                charge.jail_months = self.value_column(jail_row,'Mos:')
                charge.jail_days = self.value_column(jail_row,'Days:')
                charge.jail_hours = self.value_column(jail_row,'Hours:')
                try:
                    suspended_row = self.row_label(t,'Suspended Term:')
                except ParserError:
                    pass
                else:
                    try:
                        charge.jail_suspended_years = self.value_column(suspended_row,'Yrs:')
                        charge.jail_suspended_months = self.value_column(suspended_row,'Mos:')
                        charge.jail_suspended_days = self.value_column(suspended_row,'Days:')
                        charge.jail_suspended_hours = self.value_column(suspended_row,'Hours:')
                    except ParserError:
                        charge.jail_suspended_term = self.value_multi_column(suspended_row,'Suspended Term:')
                try:
                    suspend_all_but_row = self.row_label(t,'Suspend All But:')
                except ParserError:
                    pass
                else:
                    charge.jail_suspend_all_but_years = self.value_column(suspend_all_but_row,'Yrs:')
                    charge.jail_suspend_all_but_months = self.value_column(suspend_all_but_row,'Mos:')
                    charge.jail_suspend_all_but_days = self.value_column(suspend_all_but_row,'Days:')
                    charge.jail_suspend_all_but_hours = self.value_column(suspend_all_but_row,'Hours:')
            db.add(charge)

    #########################################################
    # PROBATION
    #########################################################
    @consumer
    def probation(self, db, soup):
        try:
            section_header = soup.find('i',string='Probation:').find_parent('left')
        except (ParserError, AttributeError):
            return
        self.mark_for_deletion(section_header)
        t = self.immediate_sibling(section_header,'table')
        for span in t.find_all('span',class_='Prompt',string='Start Date:'):
            r1 = span.find_parent('tr')
            supervised_row = self.immediate_sibling(r1,'tr')
            unsupervised_row = self.immediate_sibling(supervised_row,'tr')
            probation = ODYCRIMProbation(case_number=self.case_number)
            probation.probation_start_date_str = self.value_multi_column(r1,'Start Date:')
            probation_supervised = self.value_multi_column(supervised_row,r'^Supervised\s*:\s*')
            probation.probation_supervised = True if probation_supervised == 'true' else False
            probation.probation_supervised_years = self.value_column(supervised_row,'Yrs:')
            probation.probation_supervised_months = self.value_column(supervised_row,'Mos:')
            probation.probation_supervised_days = self.value_column(supervised_row,'Days:')
            probation.probation_supervised_hours = self.value_column(supervised_row,'Hours:')
            probation_unsupervised = self.value_multi_column(unsupervised_row,r'^UnSupervised\s*:\s*')
            probation.probation_unsupervised = True if probation_unsupervised == 'true' else False
            probation.probation_unsupervised_years = self.value_column(unsupervised_row,'Yrs:')
            probation.probation_unsupervised_months = self.value_column(unsupervised_row,'Mos:')
            probation.probation_unsupervised_days = self.value_column(unsupervised_row,'Days:')
            probation.probation_unsupervised_hours = self.value_column(unsupervised_row,'Hours:')
            db.add(probation)

    #########################################################
    # RESTITUTION AND OTHER COSTS
    #########################################################
    @consumer
    def restitution(self, db, soup):
        try:
            section_header = soup.find('i',string='Restitution and Other Costs:').find_parent('left')
        except (ParserError, AttributeError):
            return
        self.mark_for_deletion(section_header)
        t = self.immediate_sibling(section_header,'table')
        if len(list(t.stripped_strings)) > 0:
            for row in t.find_all('tr'):
                restitution = ODYCRIMRestitution(case_number=self.case_number)
                restitution.restitution_amount = self.value_multi_column(row,'Restitution Amount:',money=True,ignore_missing=True)
                restitution.restitution_entered_date_str = self.value_column(row,'Entered Date:',ignore_missing=True)
                restitution.other_cost_amount = self.value_multi_column(row,'OtherCost Amount:',money=True,ignore_missing=True)
                db.add(restitution)

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
            warrant = ODYCRIMWarrant(case_number=self.case_number)
            warrant.warrant_type = self.format_value(vals[0].string)
            warrant.issue_date_str = self.format_value(vals[1].string)
            warrant.last_status = self.format_value(vals[2].string)
            warrant.status_date_str = self.format_value(vals[3].string)
            db.add(warrant)

    #########################################################
    # BAIL BOND INFORMATION
    #########################################################
    @consumer
    def bail_bond(self, db, soup):
        try:
            section_header = self.first_level_header(soup,'Bail Bond Information')
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
            bail_bond = ODYCRIMBailBond(case_number=self.case_number)
            bail_bond.bond_type = self.format_value(vals[0].string)
            bail_bond.bond_amount_posted = self.format_value(vals[1].string,money=True)
            bail_bond.bond_status_date_str = self.format_value(vals[2].string)
            bail_bond.bond_status = self.format_value(vals[3].string)
            db.add(bail_bond)

    #########################################################
    # BOND SETTING INFORMATION
    #########################################################
    @consumer
    def bond_setting(self, db, soup):
        try:
            section_header = self.first_level_header(soup,'Bond Setting Information')
        except ParserError:
            return
        section_container = section_header.find_parent('div',class_='AltBodyWindow1')
        for span in section_container.find_all('span',class_='FirstColumnPrompt',string='Bail Date:'):
            t = span.find_parent('table')
            bond_setting = ODYCRIMBondSetting(case_number=self.case_number)
            bond_setting.bail_date_str = self.value_first_column(t,'Bail Date:')
            bond_setting.bail_setting_type = self.value_first_column(t,'Bail Setting Type:')
            bond_setting.bail_amount = self.value_first_column(t,'Bail Amount:',money=True)
            db.add(bond_setting)

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
            doc = ODYCRIMDocument(case_number=self.case_number)
            doc.file_date_str = self.value_first_column(t,'File Date:')
            doc.filed_by = self.value_first_column(t,'Filed By:')
            doc.document_name = self.value_first_column(t,'Document Name:')
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
            service = ODYCRIMService(case_number=self.case_number)
            service.service_type = self.format_value(vals[0].string)
            service.issued_date_str = self.format_value(vals[1].string,money=True)
            service.service_status = self.format_value(vals[2].string)
            db.add(service)
