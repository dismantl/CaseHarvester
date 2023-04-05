from ..models import (ODYTRAF, ODYTRAFReferenceNumber, ODYTRAFDefendant,
                     ODYTRAFInvolvedParty, ODYTRAFAttorney, ODYTRAFCourtSchedule,
                     ODYTRAFCharge, ODYTRAFWarrant, ODYTRAFBailBond,
                     ODYTRAFBondSetting, ODYTRAFDocument, ODYTRAFAlias, ODYTRAFService)
from .base import CaseDetailsParser, consumer, ParserError, ChargeFinder, reference_number_re
import re
from bs4 import BeautifulSoup, SoupStrainer

# Note that consumers may not be called in order
class ODYTRAFParser(CaseDetailsParser, ChargeFinder):
    inactive_statuses = [
        'Citation Voided',
        'Inactive / Incompetency',
        'Closed / Inactive',
        'Closed',
        'Expunged',
        'Inactive'
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
        case = ODYTRAF(case_number=self.case_number)
        section_header = self.first_level_header(soup,'Case Information')

        case_info_table = self.table_next_first_column_prompt(section_header,'Court System:')
        case.court_system = self.value_first_column(case_info_table,'Court System:',remove_newlines=True)
        case.location = self.value_first_column(case_info_table,'Location:')
        citation_number = self.value_first_column(case_info_table,'Citation Number:')
        if self.case_number.lower() not in citation_number.lower():
            raise ParserError('Case number "%s" in case details page does not match given: %s' % (citation_number, self.case_number))
        case.case_title = self.value_first_column(case_info_table,'Case Title:')
        case.case_type = self.value_first_column(case_info_table,'Case Type:')
        case.filing_date_str = self.value_first_column(case_info_table,'Filing Date:')
        case.violation_date_str = self.value_first_column(case_info_table,'Violation Date:')
        case.violation_time_str = self.value_column(case_info_table,'Violation Time:')
        case.violation_county = self.value_first_column(case_info_table,'Violation County:')
        # The following three fields are always blank
        self.mark_for_deletion(case_info_table.find('span',class_='FirstColumnPrompt',string='Agency Name:'))
        self.mark_for_deletion(case_info_table.find('span',class_='FirstColumnPrompt',string='Officer ID:'))
        self.mark_for_deletion(case_info_table.find('span',class_='Prompt',string='Officer Name:'))
        case.case_status = self.value_first_column(case_info_table,'Case Status:')
        self.case_status = case.case_status
        case.judicial_officer = self.value_first_column(case_info_table,'Judicial Officer:',ignore_missing=True)
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
            ref_num = ODYTRAFReferenceNumber(case_number=self.case_number)
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
        try:
            separator = self.immediate_sibling(section_header,'hr')
            section_header = separator
        except ParserError:
            pass
        self.consume_parties(db, section_header)

    def consume_parties(self, db, prev_obj):
        plaintiff_id = None
        defendant_id = None
        while True:
            party = None

            # Name, Agency
            try:
                subsection_header = self.immediate_sibling(prev_obj,'h5')
            except ParserError:
                break
            self.mark_for_deletion(subsection_header)
            party_type = self.format_value(subsection_header.string)
            prev_obj = subsection_header
            
            try:
                name_table = self.table_next_first_column_prompt(subsection_header,'Name:')
            except ParserError:
                pass
            else:
                # Attorneys for defendants and plaintiffs are listed in two different ways
                if party_type == 'Attorney for Defendant' and defendant_id:
                    party = ODYTRAFAttorney(case_number=self.case_number)
                    party.party_id = defendant_id
                elif party_type == 'Attorney for Plaintiff' and plaintiff_id:
                    party = ODYTRAFAttorney(case_number=self.case_number)
                    party.party_id = plaintiff_id
                elif party_type == 'Defendant':
                    party = ODYTRAFDefendant(case_number=self.case_number)
                else:
                    party = ODYTRAFInvolvedParty(case_number=self.case_number)
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
                        party.race = self.value_combined_first_column(demographics_table,'Race:',ignore_missing=True)
                        party.sex = self.value_column(demographics_table,'Sex:',ignore_missing=True)
                        party.height = self.value_column(demographics_table,'Height:',ignore_missing=True)
                        party.weight = self.value_column(demographics_table,'Weight:',numeric=True,ignore_missing=True)
                        party.DOB_str = self.value_combined_first_column(demographics_table,'DOB:',ignore_missing=True)
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
                    elif 'Removal Date:' in t.stripped_strings:
                        party.removal_date_str = self.value_first_column(t,'Removal Date:')
                    elif 'Appearance Date:' in t.stripped_strings:
                        party.appearance_date_str = self.value_first_column(t,'Appearance Date:')
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
                            alias_ = ODYTRAFAlias(case_number=self.case_number)
                            if type(party) == ODYTRAFDefendant:
                                alias_.defendant_id = party.id
                            else:
                                alias_.party_id = party.id
                            prompt_re = re.compile(r'^([\w ]+)\s*:\s*$')
                            alias_.alias = self.value_first_column(row, span.string)
                            alias_.alias_type = prompt_re.fullmatch(span.string).group(1)
                            db.add(alias_)
                    elif 'Attorney(s) for the' in subsection_name:
                        for span in subsection_table.find_all('span',class_='FirstColumnPrompt',string='Name:'):
                            attorney = ODYTRAFAttorney(case_number=self.case_number)
                            if type(party) == ODYTRAFDefendant:
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

            if not party or type(party) != ODYTRAFDefendant:  # Defendant section doesn't separate parties with <hr>
                separator = self.immediate_sibling(prev_obj,'hr')
                while True:
                    try:
                        separator = self.immediate_sibling(separator,'hr')
                    except:
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
            schedule = ODYTRAFCourtSchedule(case_number=self.case_number)
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
        new_charges = []
        while True:
            try:
                container = self.immediate_sibling(prev_obj,'div',class_='AltBodyWindow1')
            except ParserError:
                break
            if list(container.stripped_strings) == ['Case transferred to Circuit Court. See Circuit Court case.']:
                db.add(ODYTRAFCharge(
                    case_number=self.case_number,
                    notes='Case transferred to Circuit Court. See Circuit Court case.'
                ))
                self.mark_for_deletion(container)
                return
            if not container.find('span',class_='Prompt',string='Charge No:'):
                break
            try:
                separator = self.immediate_sibling(container, 'hr')
            except ParserError:
                prev_obj = container
            else:
                prev_obj = separator
            new_charge = self.parse_charge(container)
            new_charges.append(new_charge)
        
        for new_charge in new_charges:
            db.add(new_charge)
        new_charge_numbers = [c.charge_number for c in new_charges]
        self.find_charges(db, new_charge_numbers)
    
    def parse_charge(self, container):
        t1 = container.find('table')
        charge = ODYTRAFCharge(case_number=self.case_number)
        charge.charge_number = int(self.value_multi_column(t1,'Charge No:'))
        charge.statute_code = self.value_column(t1,'Statute Code:')
        t2 = self.immediate_sibling(t1,'table')
        charge.charge_description = self.value_multi_column(t2,'Charge Description:')
        t3 = self.immediate_sibling(t2,'table')
        t4 = t3.find('table')  # weird nested table shit
        charge.speed_limit = self.value_multi_column(t4,'Speed Limit:',ignore_missing=True)
        charge.recorded_speed = self.value_multi_column(t4,'Recorded Speed:',ignore_missing=True)
        charge.location_stopped = self.value_multi_column(t4,'Location Stopped:',ignore_missing=True)
        t5 = self.immediate_sibling(t4,'table')
        charge.probable_cause_indicator = self.value_multi_column(t5,'Probable Cause Indicator:',boolean_value=True,ignore_missing=True)
        charge.charge_contributed_to_accident = self.value_multi_column(t5,'Contributed to Accident:',boolean_value=True,ignore_missing=True)
        charge.charge_personal_injury = self.value_multi_column(t5,'Personal Injury:',boolean_value=True,ignore_missing=True)
        t6 = self.immediate_sibling(t5,'table')
        charge.property_damage = self.value_multi_column(t6,'Property Damage:',boolean_value=True)
        charge.seat_belts = self.value_multi_column(t6,'Seat Belts:',ignore_missing=True,boolean_value=True)
        t7 = self.immediate_sibling(t6,'table')
        charge.mandatory_court_appearance = self.value_multi_column(t7,'Mandatory Court Appearance:',boolean_value=True)
        charge.fine_amount_owed = self.value_column(t7,'Fine Amount Owed:',money=True)
        t8 = self.immediate_sibling(t7,'table')
        charge.vehicle_tag = self.value_multi_column(t8,'Vehicle Tag:')
        charge.state = self.value_multi_column(t8,'State:')
        charge.vehicle_description = self.value_multi_column(t8,'Vehicle Description:')

        # Disposition
        try:
            subsection_header = container.find('i',string='Disposition').find_parent('left')
        except (ParserError, AttributeError):
            pass
        else:
            self.mark_for_deletion(subsection_header)
            t1 = self.immediate_sibling(subsection_header,'table')
            charge.convicted_speed = self.value_multi_column(t1,'Convicted Speed:')
            charge.disposition_contributed_to_accident = self.value_column(t1,'Contributed to Accident:',boolean_value=True)
            charge.disposition_personal_injury = self.value_column(t1,'Personal Injury:',boolean_value=True)
            t2 = self.immediate_sibling(t1,'table')
            charge.plea = self.value_multi_column(t2,'Plea:')
            charge.plea_date_str = self.value_column(t2,'Plea Date:')
            charge.plea_judge = self.value_column(t2,'Judge:', ignore_missing=True)
            t3 = self.immediate_sibling(t2,'table')
            charge.disposition = self.value_multi_column(t3,'Disposition:')
            charge.disposition_date_str = self.value_column(t3,'Disposition Date:')
            charge.disposition_judge = self.value_column(t3,'Judge:',ignore_missing=True)

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

        # Probation
        try:
            subsection_header = container.find('i',string='Probation:').find_parent('left')
        except (ParserError, AttributeError):
            pass
        else:
            self.mark_for_deletion(subsection_header)
            t = self.immediate_sibling(subsection_header,'table')
            charge.probation_start_date_str = self.value_multi_column(t,'Start Date:')
            supervised_row = self.row_label(t,'Supervised')
            charge.probation_supervised_years = self.value_column(supervised_row,'Yrs:')
            charge.probation_supervised_months = self.value_column(supervised_row,'Mos:')
            charge.probation_supervised_days = self.value_column(supervised_row,'Days:')
            charge.probation_supervised_hours = self.value_column(supervised_row,'Hours:')
            unsupervised_row = self.row_label(t,'UnSupervised')
            charge.probation_unsupervised_years = self.value_column(unsupervised_row,'Yrs:')
            charge.probation_unsupervised_months = self.value_column(unsupervised_row,'Mos:')
            charge.probation_unsupervised_days = self.value_column(unsupervised_row,'Days:')
            charge.probation_unsupervised_hours = self.value_column(unsupervised_row,'Hours:')

        # Jail
        try:
            subsection_header = container.find('i',string='Jail').find_parent('left')
        except (ParserError, AttributeError):
            pass
        else:
            self.mark_for_deletion(subsection_header)
            t = self.immediate_sibling(subsection_header,'table')
            self.mark_for_deletion(t.find('span',class_='Prompt',string='Life/Death:'))
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

        # Sentence
        try:
            subsection_header = container.find('i',string='Sentence').find_parent('left')
        except (ParserError, AttributeError):
            pass
        else:
            self.mark_for_deletion(subsection_header)
            t = self.immediate_sibling(subsection_header,'table')
            charge.sentence_judge = self.value_multi_column(t,'Judge:')

        return charge

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
            warrant = ODYTRAFWarrant(case_number=self.case_number)
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
            db.add(warrant)

    #########################################################
    # BAIL BOND INFORMATION
    #########################################################
    @consumer
    def bail_bond(self, db, soup):
        try:
            subsection_header = self.first_level_header(soup,'Bail Bond Information')
        except ParserError:
            return
        subsection_container = self.immediate_sibling(subsection_header,'div',class_='AltBodyWindow1')
        header_row = subsection_container.find('tr')
        self.mark_for_deletion(header_row)
        prev_obj = header_row
        while True:
            try:
                row = self.immediate_sibling(prev_obj,'tr')
            except ParserError:
                break
            prev_obj = row
            vals = row.find_all('span',class_='Value')
            bail_bond = ODYTRAFBailBond(case_number=self.case_number)
            bail_bond.bond_type = self.format_value(vals[0].string)
            self.mark_for_deletion(vals[0])
            bail_bond.bond_amount_set = self.format_value(vals[1].string,money=True)
            self.mark_for_deletion(vals[1])
            bail_bond.bond_status_date_str = self.format_value(vals[2].string)
            self.mark_for_deletion(vals[2])
            bail_bond.bond_status = self.format_value(vals[3].string)
            self.mark_for_deletion(vals[3])
            db.add(bail_bond)

    #########################################################
    # BOND SETTING INFORMATION
    #########################################################
    @consumer
    def bond_setting(self, db, soup):
        try:
            subsection_header = self.first_level_header(soup,'Bond Setting Information')
        except ParserError:
            return
        subsection_container = subsection_header.find_parent('div',class_='AltBodyWindow1')
        for span in subsection_container.find_all('span',class_='FirstColumnPrompt',string='Bail Date:'):
            t = span.find_parent('table')
            bond_setting = ODYTRAFBondSetting(case_number=self.case_number)
            bond_setting.bail_date_str = self.value_first_column(t,'Bail Date:')
            bond_setting.bail_setting_type = self.value_first_column(t,'Bail Setting Type:')
            bond_setting.bail_amount = self.value_first_column(t,'Bail Amount:',money=True)
            bond_setting.judge = self.value_first_column(t, 'Judge:', ignore_missing=True)
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
        container = self.immediate_sibling(section_header,'div',class_='AltBodyWindow1')
        for t in container.find_all('table'):
            doc = ODYTRAFDocument(case_number=self.case_number)
            doc.file_date_str = self.value_first_column(t,'File Date:')
            self.mark_for_deletion(t.find('span',class_='FirstColumnPrompt',string='Filed By:'))
            doc.document_name = self.value_first_column(t,'Document Name:')
            doc.comment = self.value_first_column(t,'Comment:')
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
            service = ODYTRAFService(case_number=self.case_number)
            service.service_type = self.format_value(vals[0].string)
            self.mark_for_deletion(vals[0])
            service.requested_by = self.format_value(vals[1].string)
            self.mark_for_deletion(vals[1])
            service.issued_date_str = self.format_value(vals[2].string,money=True)
            self.mark_for_deletion(vals[2])
            db.add(service)
