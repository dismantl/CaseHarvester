from ..db import TableBase
from .base import CaseDetailsParser, consumer, ParserError
from .common import CaseTable, Trial, Event, date_from_str, Defendant, DefendantAlias, RelatedPerson
from sqlalchemy import Column, Date, Numeric, Integer, String, Boolean, ForeignKey, Time, BigInteger
from sqlalchemy.orm import relationship
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.ext.declarative import declared_attr
from datetime import *
import re
from bs4 import BeautifulSoup, SoupStrainer

class ODYTRAF(CaseTable, TableBase):
    __tablename__ = 'odytraf'

    id = Column(Integer, primary_key=True)
    court_system = Column(String)
    location = Column(String)
    citation_number = Column(String)
    case_title = Column(String)
    case_type = Column(String, nullable=True)
    filing_date = Column(Date, nullable=True)
    _filing_date_str = Column('filing_date_str',String, nullable=True)
    violation_date = Column(Date, nullable=True)
    _violation_date_str = Column('violation_date_str',String, nullable=True)
    violation_time = Column(Time, nullable=True)
    _violation_time_str = Column('violation_time_str', String, nullable=True)
    violation_county = Column(String)
    agency_name = Column(String)
    officer_id = Column(String)
    officer_name = Column(String)
    case_status = Column(String, nullable=True)

    @hybrid_property
    def filing_date_str(self):
        return self._filing_date_str
    @filing_date_str.setter
    def filing_date_str(self,val):
        self.filing_date = date_from_str(val)
        self._filing_date_str = val

    @hybrid_property
    def violation_date_str(self):
        return self._violation_date_str
    @violation_date_str.setter
    def violation_date_str(self,val):
        self.violation_date = date_from_str(val)
        self._violation_date_str = val

    @hybrid_property
    def violation_time_str(self):
        return self._violation_time_str
    @violation_time_str.setter
    def violation_time_str(self,val):
        try:
            self.violation_time = datetime.strptime(val,'%I:%M:%S %p').time()
        except:
            pass
        self._violation_time_str = val

class ODYTRAFCaseTable(CaseTable):
    @declared_attr
    def case_number(cls):
        return Column(String, ForeignKey('odytraf.case_number', ondelete='CASCADE'), index=True)

class ODYTRAFReferenceNumber(ODYTRAFCaseTable, TableBase):
    __tablename__ = 'odytraf_reference_numbers'

    id = Column(Integer, primary_key=True)
    ref_num = Column(String, nullable=False)
    ref_num_type = Column(String, nullable=False)

class ODYTRAFDefendant(ODYTRAFCaseTable, Defendant, TableBase):
    __tablename__ = 'odytraf_defendants'

    height = Column(String, nullable=True)

class ODYTRAFInvolvedParty(ODYTRAFCaseTable, TableBase):
    __tablename__ = 'odytraf_involved_parties'

    id = Column(Integer, primary_key=True)
    party_type = Column(String, nullable=False)
    name = Column(String, nullable=False)
    agency_name = Column(String, nullable=True)
    address_1 = Column(String, nullable=True)
    address_2 = Column(String, nullable=True)
    city = Column(String, nullable=True)
    state = Column(String, nullable=True)
    zip_code = Column(String, nullable=True)

class ODYTRAFAlias(ODYTRAFCaseTable, TableBase):
    __tablename__ = 'odytraf_aliases'

    id = Column(Integer, primary_key=True)
    alias = Column(String, nullable=False)
    alias_type = Column(String, nullable=False)
    defendant_id = Column(Integer, ForeignKey('odytraf_defendants.id'),nullable=True)
    party_id = Column(Integer, ForeignKey('odytraf_involved_parties.id'),nullable=True)

class ODYTRAFAttorney(ODYTRAFCaseTable, TableBase):
    __tablename__ = 'odytraf_attorneys'

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=True)
    address_1 = Column(String, nullable=True)
    address_2 = Column(String, nullable=True)
    address_3 = Column(String, nullable=True)
    city = Column(String, nullable=True)
    state = Column(String, nullable=True)
    zip_code = Column(String, nullable=True)
    defendant_id = Column(Integer, ForeignKey('odytraf_defendants.id'),nullable=True)
    party_id = Column(Integer, ForeignKey('odytraf_involved_parties.id'),nullable=True)


class ODYTRAFCourtSchedule(ODYTRAFCaseTable, TableBase):
    __tablename__ = 'odytraf_court_schedule'

    id = Column(Integer, primary_key=True)
    event_type = Column(String, nullable=False)
    date = Column(Date, nullable=True)
    _date_str = Column('date_str', String, nullable=True)
    time = Column(Time, nullable=True)
    _time_str = Column('time_str', String, nullable=True)
    location = Column(String, nullable=True)
    room = Column(String, nullable=True)
    result = Column(String,nullable=True)

    @hybrid_property
    def date_str(self):
        return self._date_str
    @date_str.setter
    def date_str(self,val):
        self.date = date_from_str(val)
        self._date_str = val

    @hybrid_property
    def time_str(self):
        return self._time_str
    @time_str.setter
    def time_str(self,val):
        try:
            self.time = datetime.strptime(val,'%H:%M:%S').time()
        except:
            pass
        self._time_str = val

class ODYTRAFCharge(ODYTRAFCaseTable, TableBase):
    __tablename__ = 'odytraf_charges'

    id = Column(Integer, primary_key=True)
    charge_number = Column(Integer)
    charge_description = Column(String, nullable=True)
    statute_code = Column(String, nullable=True)
    speed_limit = Column(Integer, nullable=True)
    recorded_speed = Column(Integer, nullable=True)
    location_stopped = Column(String)
    probable_cause_indicator = Column(Boolean)
    charge_contributed_to_accident = Column(Boolean)
    charge_personal_injury = Column(Boolean)
    property_damage = Column(Boolean)
    seat_belts = Column(Boolean, nullable=True)
    mandatory_court_appearance = Column(Boolean)
    fine_amount_owed = Column(Numeric)
    vehicle_tag = Column(String)
    state = Column(String)
    vehicle_description = Column(String)
    convicted_speed = Column(Integer)
    disposition_contributed_to_accident = Column(Boolean)
    disposition_personal_injury = Column(Boolean)
    plea = Column(String)
    plea_date = Column(Date, nullable=True)
    _plea_date_str = Column('plea_date_str', String, nullable=True)
    disposition = Column(String)
    disposition_date = Column(Date, nullable=True)
    _disposition_date_str = Column('disposition_date_str', String, nullable=True)
    converted_disposition = Column(String, nullable=True)
    probation_start_date = Column(Date, nullable=True)
    _probation_start_date_str = Column('probation_start_date_str', String, nullable=True)
    probation_supervised_years = Column(Integer, nullable=True)
    probation_supervised_months = Column(Integer, nullable=True)
    probation_supervised_days = Column(Integer, nullable=True)
    probation_supervised_hours = Column(Integer, nullable=True)
    probation_unsupervised_years = Column(Integer, nullable=True)
    probation_unsupervised_months = Column(Integer, nullable=True)
    probation_unsupervised_days = Column(Integer, nullable=True)
    probation_unsupervised_hours = Column(Integer, nullable=True)
    jail_life_death = Column(String, nullable=True)
    jail_start_date = Column(Date, nullable=True)
    _jail_start_date_str = Column('jail_start_date_str', String, nullable=True)
    jail_years = Column(Integer, nullable=True)
    jail_months = Column(Integer, nullable=True)
    jail_days = Column(Integer, nullable=True)
    jail_hours = Column(Integer, nullable=True)
    jail_suspended_years = Column(Integer, nullable=True)
    jail_suspended_months = Column(Integer, nullable=True)
    jail_suspended_days = Column(Integer, nullable=True)
    jail_suspended_hours = Column(Integer, nullable=True)
    jail_suspend_all_but_years = Column(Integer, nullable=True)
    jail_suspend_all_but_months = Column(Integer, nullable=True)
    jail_suspend_all_but_days = Column(Integer, nullable=True)
    jail_suspend_all_but_hours = Column(Integer, nullable=True)

    @hybrid_property
    def plea_date_str(self):
        return self._plea_date_str
    @plea_date_str.setter
    def plea_date_str(self,val):
        self.plea_date = date_from_str(val)
        self._plea_date_str = val

    @hybrid_property
    def disposition_date_str(self):
        return self._disposition_date_str
    @disposition_date_str.setter
    def disposition_date_str(self,val):
        self.disposition_date = date_from_str(val)
        self._disposition_date_str = val

    @hybrid_property
    def probation_start_date_str(self):
        return self._probation_start_date_str
    @probation_start_date_str.setter
    def probation_start_date_str(self,val):
        self.probation_start_date = date_from_str(val)
        self._probation_start_date_str = val

    @hybrid_property
    def jail_start_date_str(self):
        return self._jail_start_date_str
    @jail_start_date_str.setter
    def jail_start_date_str(self,val):
        self.jail_start_date = date_from_str(val)
        self._jail_start_date_str = val

class ODYTRAFWarrant(ODYTRAFCaseTable, TableBase):
    __tablename__ = 'odytraf_warrants'

    id = Column(Integer, primary_key=True)
    warrant_type = Column(String)
    issue_date = Column(Date, nullable=True)
    _issue_date_str = Column('issue_date_str', String, nullable=True)
    last_status = Column(String)
    status_date = Column(Date, nullable=True)
    _status_date_str = Column('status_date_str', String, nullable=True)

    @hybrid_property
    def issue_date_str(self):
        return self._issue_date_str
    @issue_date_str.setter
    def issue_date_str(self,val):
        self.issue_date = date_from_str(val)
        self._issue_date_str = val

    @hybrid_property
    def status_date_str(self):
        return self._status_date_str
    @status_date_str.setter
    def status_date_str(self,val):
        self.status_date = date_from_str(val)
        self._status_date_str = val

class ODYTRAFBailBond(ODYTRAFCaseTable, TableBase):
    __tablename__ = 'odytraf_bail_bonds'

    id = Column(Integer, primary_key=True)
    bond_type = Column(String)
    bond_amount_set = Column(String)
    bond_status_date = Column(Date, nullable=True)
    _bond_status_date_str = Column('bond_status_date_str', String, nullable=True)
    bond_status = Column(String)

    @hybrid_property
    def bond_status_date_str(self):
        return self._bond_status_date_str
    @bond_status_date_str.setter
    def bond_status_date_str(self,val):
        self.bond_status_date = date_from_str(val)
        self._bond_status_date_str = val

class ODYTRAFBondSetting(ODYTRAFCaseTable, TableBase):
    __tablename__ = 'odytraf_bond_settings'

    id = Column(Integer, primary_key=True)
    bail_date = Column(Date, nullable=True)
    _bail_date_str = Column('bail_date_str', String, nullable=True)
    bail_setting_type = Column(String)
    bail_amount = Column(Numeric)

    @hybrid_property
    def bail_date_str(self):
        return self._bail_date_str
    @bail_date_str.setter
    def bail_date_str(self,val):
        self.bail_date = date_from_str(val)
        self._bail_date_str = val


class ODYTRAFDocument(ODYTRAFCaseTable, TableBase):
    __tablename__ = 'odytraf_documents'

    id = Column(Integer, primary_key=True)
    file_date = Column(Date,nullable=True)
    _file_date_str = Column('file_date_str',String,nullable=True)
    filed_by = Column(String,nullable=True)
    document_name = Column(String,nullable=True)
    comment = Column(String,nullable=True)

    @hybrid_property
    def file_date_str(self):
        return self._file_date_str
    @file_date_str.setter
    def file_date_str(self,val):
        self.file_date = date_from_str(val)
        self._file_date_str = val

class ODYTRAFService(ODYTRAFCaseTable, TableBase):
    __tablename__ = 'odytraf_services'

    id = Column(Integer, primary_key=True)
    service_type = Column(String, nullable=False)
    requested_by = Column(String, nullable=True)
    issued_date = Column(Date,nullable=True)
    _issued_date_str = Column('issued_date_str',String,nullable=True)
    service_status = Column(String,nullable=True)

    @hybrid_property
    def issued_date_str(self):
        return self._issued_date_str
    @issued_date_str.setter
    def issued_date_str(self,val):
        self.issued_date = date_from_str(val)
        self._issued_date_str = val

# Note that consumers may not be called in order
class ODYTRAFParser(CaseDetailsParser):
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
        self.delete_previous(db, ODYTRAF)

        case = ODYTRAF(self.case_number)
        section_header = self.first_level_header(soup,'Case Information')

        case_info_table = self.table_next_first_column_prompt(section_header,'Court System:')
        case.court_system = self.value_first_column(case_info_table,'Court System:',remove_newlines=True)
        case.location = self.value_first_column(case_info_table,'Location:')
        citation_number = self.value_first_column(case_info_table,'Citation Number:')
        if self.case_number not in citation_number:
            raise ParserError('Case number "%s" in case details page does not match given: %s' % (citation_number, self.case_number))
        case.case_title = self.value_first_column(case_info_table,'Case Title:')
        case.case_type = self.value_first_column(case_info_table,'Case Type:')
        case.filing_date_str = self.value_first_column(case_info_table,'Filing Date:')
        case.violation_date_str = self.value_first_column(case_info_table,'Violation Date:')
        case.violation_time_str = self.value_column(case_info_table,'Violation Time:')
        case.violation_county = self.value_first_column(case_info_table,'Violation County:')
        case.agency_name = self.value_first_column(case_info_table,'Agency Name:')
        case.officer_id = self.value_first_column(case_info_table,'Officer ID:')
        case.officer_name = self.value_column(case_info_table,'Officer Name:')
        case.case_status = self.value_first_column(case_info_table,'Case Status:')
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
            prompt_re = re.compile('^([\w ]+)\s*:\s*$')
            prompt_span = t.find('span',class_='FirstColumnPrompt',string=prompt_re)
            if not prompt_span:
                break
            ref_num = ODYTRAFReferenceNumber(self.case_number)
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

            # Name, Agency
            try:
                subsection_header = self.immediate_sibling(prev_obj,'h5')
            except ParserError:
                break
            self.mark_for_deletion(subsection_header)
            prev_obj = subsection_header
            try:
                name_table = self.table_next_first_column_prompt(subsection_header,'Name:')
            except ParserError:
                pass
            else:
                party_type = self.format_value(subsection_header.string)
                # print(party_type)
                # Attorneys for defendants and plaintiffs are listed in two different ways
                if party_type == 'Attorney for Defendant' and plaintiff_id:
                    party = ODYTRAFAttorney(self.case_number)
                    party.party_id = defendant_id
                elif party_type == 'Attorney for Plaintiff' and plaintiff_id:
                    party = ODYTRAFAttorney(self.case_number)
                    party.party_id = plaintiff_id
                elif party_type == 'Defendant':
                    party = ODYTRAFDefendant(self.case_number)
                else:
                    party = ODYTRAFInvolvedParty(self.case_number)
                    party.party_type = party_type
                party.name = self.value_first_column(name_table,'Name:')
                party.agency_name = self.value_first_column(name_table,'AgencyName:',ignore_missing=True)
                prev_obj = name_table

                # Address
                try:
                    address_table = self.immediate_sibling(name_table,'table')
                except ParserError:
                    pass
                else:
                    if 'Address:' in address_table.stripped_strings:
                        prev_obj = address_table
                        rows = address_table.find_all('tr')
                        party.address_1 = self.value_first_column(address_table,'Address:')
                        if len(rows) == 3:
                            party.address_2 = self.format_value(rows[1].find('span',class_='Value').string)
                            self.mark_for_deletion(rows[1])
                        party.city = self.value_first_column(address_table,'City:')
                        party.state = self.value_column(address_table,'State:')
                        party.zip_code = self.value_column(address_table,'Zip Code:',ignore_missing=True)

                # Demographic information
                try:
                    demographics_table = self.immediate_sibling(prev_obj)
                except ParserError:
                    pass
                else:
                    if 'Race:' in demographics_table.stripped_strings:
                        prev_obj = demographics_table
                        party.race = self.value_combined_first_column(demographics_table,'Race:')
                        party.sex = self.value_column(demographics_table,'Sex:')
                        party.height = self.value_column(demographics_table,'Height:')
                        party.weight = self.value_column(demographics_table,'Weight:',numeric=True)
                        party.DOB_str = self.value_combined_first_column(demographics_table,'DOB:',ignore_missing=True)

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
                            alias_ = ODYTRAFAlias(self.case_number)
                            if type(party) == ODYTRAFDefendant:
                                alias_.defendant_id = party.id
                            else:
                                alias_.party_id = party.id
                            prompt_re = re.compile('^([\w ]+)\s*:\s*$')
                            alias_.alias = self.value_first_column(row, span.string)
                            alias_.alias_type = prompt_re.fullmatch(span.string).group(1)
                            db.add(alias_)
                    elif 'Attorney(s) for the' in subsection_name:
                        for span in subsection_table.find_all('span',class_='FirstColumnPrompt',string='Name:'):
                            attorney = ODYTRAFAttorney(self.case_number)
                            if type(party) == ODYTRAFDefendant:
                                attorney.defendant_id = party.id
                            else:
                                attorney.party_id = party.id
                            name_row = span.find_parent('tr')
                            attorney.name = self.value_first_column(name_row,'Name:')
                            address_row = self.row_next_first_column_prompt(name_row,'Address Line 1:')
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
            schedule = ODYTRAFCourtSchedule(self.case_number)
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
            charge = ODYTRAFCharge(self.case_number)
            charge.charge_number = self.value_multi_column(t1,'Charge No:')
            charge.statute_code = self.value_column(t1,'Statute Code:')
            t2 = self.immediate_sibling(t1,'table')
            charge.charge_description = self.value_multi_column(t2,'Charge Description:')
            t3 = self.immediate_sibling(t2,'table')
            t4 = t3.find('table')  # weird nested table shit
            charge.speed_limit = self.value_multi_column(t4,'Speed Limit:')
            charge.recorded_speed = self.value_multi_column(t4,'Recorded Speed:')
            charge.location_stopped = self.value_multi_column(t4,'Location Stopped:')
            t5 = self.immediate_sibling(t4,'table')
            charge.probable_cause_indicator = self.value_multi_column(t5,'Probable Cause Indicator:',boolean_value=True)
            charge.charge_contributed_to_accident = self.value_multi_column(t5,'Contributed to Accident:',boolean_value=True)
            charge.charge_personal_injury = self.value_multi_column(t5,'Personal Injury:',boolean_value=True)
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
                t3 = self.immediate_sibling(t2,'table')
                charge.disposition = self.value_multi_column(t3,'Disposition:')
                charge.disposition_date_str = self.value_column(t3,'Disposition Date:')

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
                charge.jail_life_death = self.value_multi_column(t,'Life/Death:')
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
                    charge.jail_suspended_years = self.value_column(suspended_row,'Yrs:')
                    charge.jail_suspended_months = self.value_column(suspended_row,'Mos:')
                    charge.jail_suspended_days = self.value_column(suspended_row,'Days:')
                    charge.jail_suspended_hours = self.value_column(suspended_row,'Hours:')
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
            warrant = ODYTRAFWarrant(self.case_number)
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
            self.mark_for_deletion(row)
            vals = row.find_all('span',class_='Value')
            bail_bond = ODYTRAFBailBond(self.case_number)
            bail_bond.bond_type = self.format_value(vals[0].string)
            bail_bond.bond_amount_set = self.format_value(vals[1].string,money=True)
            bail_bond.bond_status_date_str = self.format_value(vals[2].string)
            bail_bond.bond_status = self.format_value(vals[3].string)
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
            bond_setting = ODYTRAFBondSetting(self.case_number)
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
        container = self.immediate_sibling(section_header,'div',class_='AltBodyWindow1')
        for t in container.find_all('table'):
            doc = ODYTRAFDocument(self.case_number)
            doc.file_date_str = self.value_first_column(t,'File Date:')
            doc.filed_by = self.value_first_column(t,'Filed By:')
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
            self.mark_for_deletion(row)
            vals = row.find_all('span',class_='Value')
            service = ODYTRAFService(self.case_number)
            service.service_type = self.format_value(vals[0].string)
            service.requested_by = self.format_value(vals[1].string)
            service.issued_date_str = self.format_value(vals[2].string,money=True)
            service.service_status = self.format_value(vals[3].string)
            db.add(service)
