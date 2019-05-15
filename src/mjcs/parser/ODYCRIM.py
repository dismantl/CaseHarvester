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

class ODYCRIM(CaseTable, TableBase):
    __tablename__ = 'odycrim'

    id = Column(Integer, primary_key=True)
    court_system = Column(String)
    location = Column(String)
    case_title = Column(String)
    case_type = Column(String, nullable=True)
    filing_date = Column(Date, nullable=True)
    _filing_date_str = Column('filing_date_str',String, nullable=True)
    case_status = Column(String, nullable=True)
    tracking_numbers = Column(String, nullable=True)

    @hybrid_property
    def filing_date_str(self):
        return self._filing_date_str
    @filing_date_str.setter
    def filing_date_str(self,val):
        self.filing_date = date_from_str(val)
        self._filing_date_str = val

class ODYCRIMCaseTable(CaseTable):
    @declared_attr
    def case_number(cls):
        return Column(String, ForeignKey('odycrim.case_number', ondelete='CASCADE'), index=True)

class ODYCRIMReferenceNumber(ODYCRIMCaseTable, TableBase):
    __tablename__ = 'odycrim_reference_numbers'

    id = Column(Integer, primary_key=True)
    ref_num = Column(String, nullable=False)
    ref_num_type = Column(String, nullable=False)

class ODYCRIMDefendant(ODYCRIMCaseTable, Defendant, TableBase):
    __tablename__ = 'odycrim_defendants'

    height = Column(String, nullable=True)
    hair_color = Column(String, nullable=True)
    eye_color = Column(String, nullable=True)

class ODYCRIMInvolvedParty(ODYCRIMCaseTable, TableBase):
    __tablename__ = 'odycrim_involved_parties'

    id = Column(Integer, primary_key=True)
    party_type = Column(String, nullable=False)
    name = Column(String, nullable=False)
    agency_name = Column(String, nullable=True)
    address_1 = Column(String, nullable=True)
    address_2 = Column(String, nullable=True)
    city = Column(String, nullable=True)
    state = Column(String, nullable=True)
    zip_code = Column(String, nullable=True)

class ODYCRIMAlias(ODYCRIMCaseTable, TableBase):
    __tablename__ = 'odycrim_aliases'

    id = Column(Integer, primary_key=True)
    alias = Column(String, nullable=False)
    alias_type = Column(String, nullable=False)
    defendant_id = Column(Integer, ForeignKey('odycrim_defendants.id'),nullable=True)
    party_id = Column(Integer, ForeignKey('odycrim_involved_parties.id'),nullable=True)

class ODYCRIMAttorney(ODYCRIMCaseTable, TableBase):
    __tablename__ = 'odycrim_attorneys'

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=True)
    address_1 = Column(String, nullable=True)
    address_2 = Column(String, nullable=True)
    address_3 = Column(String, nullable=True)
    city = Column(String, nullable=True)
    state = Column(String, nullable=True)
    zip_code = Column(String, nullable=True)
    defendant_id = Column(Integer, ForeignKey('odycrim_defendants.id'),nullable=True)
    party_id = Column(Integer, ForeignKey('odycrim_involved_parties.id'),nullable=True)

class ODYCRIMCourtSchedule(ODYCRIMCaseTable, TableBase):
    __tablename__ = 'odycrim_court_schedule'

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

class ODYCRIMCharge(ODYCRIMCaseTable, TableBase):
    __tablename__ = 'odycrim_charges'

    id = Column(Integer, primary_key=True)
    charge_number = Column(Integer)
    cjis_code = Column(String)
    statute_code = Column(String, nullable=True)
    charge_description = Column(String, nullable=True)
    charge_class = Column(String)
    probable_cause = Column(Boolean)
    offense_date_from = Column(Date, nullable=True)
    _offense_date_from_str = Column('offense_date_from_str', String, nullable=True)
    offense_date_to = Column(Date, nullable=True)
    _offense_date_to_str = Column('offense_date_to_str', String, nullable=True)
    agency_name = Column(String)
    officer_id = Column(String)
    plea = Column(String, nullable=True)
    plea_date = Column(Date, nullable=True)
    _plea_date_str = Column('plea_date_str', String, nullable=True)
    disposition = Column(String, nullable=True)
    disposition_date = Column(Date, nullable=True)
    _disposition_date_str = Column('disposition_date_str', String, nullable=True)
    converted_disposition = Column(String, nullable=True)
    jail_life = Column(Boolean, nullable=True)
    jail_death = Column(Boolean, nullable=True)
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
    def offense_date_from_str(self):
        return self._offense_date_from_str
    @offense_date_from_str.setter
    def offense_date_from_str(self,val):
        self.offense_date_from = date_from_str(val)
        self._offense_date_from_str = val

    @hybrid_property
    def offense_date_to_str(self):
        return self._offense_date_to_str
    @offense_date_to_str.setter
    def offense_date_to_str(self,val):
        self.offense_date_to = date_from_str(val)
        self._offense_date_to_str = val

    @hybrid_property
    def jail_start_date_str(self):
        return self._jail_start_date_str
    @jail_start_date_str.setter
    def jail_start_date_str(self,val):
        self.jail_start_date = date_from_str(val)
        self._jail_start_date_str = val

class ODYCRIMProbation(ODYCRIMCaseTable, TableBase):
    __tablename__ = 'odycrim_probation'

    id = Column(Integer, primary_key=True)
    probation_start_date = Column(Date, nullable=True)
    _probation_start_date_str = Column('probation_start_date_str', String, nullable=True)
    probation_supervised = Column(Boolean, nullable=True)
    probation_supervised_years = Column(Integer, nullable=True)
    probation_supervised_months = Column(Integer, nullable=True)
    probation_supervised_days = Column(Integer, nullable=True)
    probation_supervised_hours = Column(Integer, nullable=True)
    probation_usupervised = Column(Boolean, nullable=True)
    probation_unsupervised_years = Column(Integer, nullable=True)
    probation_unsupervised_months = Column(Integer, nullable=True)
    probation_unsupervised_days = Column(Integer, nullable=True)
    probation_unsupervised_hours = Column(Integer, nullable=True)

    @hybrid_property
    def probation_start_date_str(self):
        return self._probation_start_date_str
    @probation_start_date_str.setter
    def probation_start_date_str(self,val):
        self.probation_start_date = date_from_str(val)
        self._probation_start_date_str = val

class ODYCRIMRestitution(ODYCRIMCaseTable, TableBase):
    __tablename__ = 'odycrim_restitutions'

    id = Column(Integer, primary_key=True)
    restitution_amount = Column(Numeric, nullable=True)
    restitution_entered_date = Column(Date, nullable=True)
    _restitution_entered_date_str = Column('restitution_entered_date_str', String, nullable=True)

    @hybrid_property
    def restitution_entered_date_str(self):
        return self._restitution_entered_date_str
    @restitution_entered_date_str.setter
    def restitution_entered_date_str(self,val):
        self.restitution_entered_date = date_from_str(val)
        self._restitution_entered_date_str = val

class ODYCRIMWarrant(ODYCRIMCaseTable, TableBase):
    __tablename__ = 'odycrim_warrants'

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

class ODYCRIMBailBond(ODYCRIMCaseTable, TableBase):
    __tablename__ = 'odycrim_bail_bonds'

    id = Column(Integer, primary_key=True)
    bond_type = Column(String)
    bond_amount_posted = Column(String)
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

class ODYCRIMBondSetting(ODYCRIMCaseTable, TableBase):
    __tablename__ = 'odycrim_bond_settings'

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


class ODYCRIMDocument(ODYCRIMCaseTable, TableBase):
    __tablename__ = 'odycrim_documents'

    id = Column(Integer, primary_key=True)
    file_date = Column(Date,nullable=True)
    _file_date_str = Column('file_date_str',String,nullable=True)
    filed_by = Column(String,nullable=True)
    document_name = Column(String,nullable=False)

    @hybrid_property
    def file_date_str(self):
        return self._file_date_str
    @file_date_str.setter
    def file_date_str(self,val):
        self.file_date = date_from_str(val)
        self._file_date_str = val

class ODYCRIMService(ODYCRIMCaseTable, TableBase):
    __tablename__ = 'odycrim_services'

    id = Column(Integer, primary_key=True)
    service_type = Column(String, nullable=False)
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
class ODYCRIMParser(CaseDetailsParser):
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
        self.delete_previous(db, ODYCRIM)

        case = ODYCRIM(self.case_number)
        section_header = self.first_level_header(soup,'Case Information')

        case_info_table = self.table_next_first_column_prompt(section_header,'Court System:')
        case.court_system = self.value_first_column(case_info_table,'Court System:',remove_newlines=True)
        case.location = self.value_first_column(case_info_table,'Location:')
        case_number = self.value_first_column(case_info_table,'Case Number:')
        if self.case_number != case_number.replace('-',''):
            raise ParserError('Case number "%s" in case details page does not match given: %s' % (case_number, self.case_number))
        case.case_title = self.value_first_column(case_info_table,'Title:')
        case.case_type = self.value_first_column(case_info_table,'Case Type:')
        case.filing_date_str = self.value_first_column(case_info_table,'Filing Date:')
        case.case_status = self.value_first_column(case_info_table,'Case Status:')
        case.tracking_numbers = self.value_first_column(case_info_table,'Tracking Number\(s\):')
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
            ref_num = ODYCRIMReferenceNumber(self.case_number)
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
            # Name, Agency
            try:
                subsection_header = self.immediate_sibling(prev_obj,'h5')
                name_table = self.table_next_first_column_prompt(subsection_header,'Name:')
            except ParserError:
                break
            self.mark_for_deletion(subsection_header)
            party_type = self.format_value(subsection_header.string)
            # print(party_type)
            # Attorneys for defendants and plaintiffs are listed in two different ways
            if party_type == 'Attorney for Defendant' and plaintiff_id:
                party = ODYCRIMAttorney(self.case_number)
                party.party_id = defendant_id
            elif party_type == 'Attorney for Plaintiff' and plaintiff_id:
                party = ODYCRIMAttorney(self.case_number)
                party.party_id = plaintiff_id
            elif party_type == 'Defendant':
                party = ODYCRIMDefendant(self.case_number)
            else:
                party = ODYCRIMInvolvedParty(self.case_number)
                party.party_type = party_type
            party.name = self.value_first_column(name_table,'Name:')
            party.agency_name = self.value_first_column(name_table,'AgencyName:',ignore_missing=True)
            prev_obj = name_table

            try:
                t2 = self.immediate_sibling(name_table,'table')
            except ParserError:
                pass
            else:
                prev_obj = t2
                demographics_table = None
                address_table = None
                if 'HairColor:' in t2.stripped_strings:
                    demographics_table = t2
                elif len(list(t2.stripped_strings)) > 0:
                    address_table = t2

                if not address_table:
                    try:
                        address_table = self.table_next_first_column_prompt(t2,'Address:')
                        prev_obj = address_table
                    except ParserError:
                        pass

                # Demographic information
                if demographics_table:
                    party.race = self.value_first_column(demographics_table,'Race:')
                    party.sex = self.value_column(demographics_table,'Sex:')
                    party.height = self.value_column(demographics_table,'Height:')
                    party.weight = self.value_column(demographics_table,'Weight:',numeric=True)
                    party.hair_color = self.value_first_column(demographics_table,'HairColor:')
                    party.eye_color = self.value_column(demographics_table,'EyeColor:')
                    party.DOB_str = self.value_first_column(demographics_table,'DOB:',ignore_missing=True)

                # Address
                if address_table:
                    rows = address_table.find_all('tr')
                    party.address_1 = self.value_first_column(address_table,'Address:')
                    if len(rows) == 3:
                        party.address_2 = self.format_value(rows[1].find('span',class_='Value').string)
                        self.mark_for_deletion(rows[1])
                    party.city = self.value_first_column(address_table,'City:')
                    party.state = self.value_column(address_table,'State:')
                    party.zip_code = self.value_column(address_table,'Zip Code:',ignore_missing=True)

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
                        alias_ = ODYCRIMAlias(self.case_number)
                        if type(party) == ODYCRIMDefendant:
                            alias_.defendant_id = party.id
                        else:
                            alias_.party_id = party.id
                        prompt_re = re.compile('^([\w ]+)\s*:\s*$')
                        alias_.alias = self.value_first_column(row, span.string)
                        alias_.alias_type = prompt_re.fullmatch(span.string).group(1)
                        db.add(alias_)
                elif 'Attorney(s) for the' in subsection_name:
                    for span in subsection_table.find_all('span',class_='FirstColumnPrompt',string='Name:'):
                        attorney = ODYCRIMAttorney(self.case_number)
                        if type(party) == ODYCRIMDefendant:
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
            schedule = ODYCRIMCourtSchedule(self.case_number)
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
            charge = ODYCRIMCharge(self.case_number)
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
            probation = ODYCRIMProbation(self.case_number)
            probation.probation_start_date_str = self.value_multi_column(r1,'Start Date:')
            probation_supervised = self.value_multi_column(supervised_row,'^Supervised\s*:\s*')
            probation.probation_supervised = True if probation_supervised == 'true' else False
            probation.probation_supervised_years = self.value_column(supervised_row,'Yrs:')
            probation.probation_supervised_months = self.value_column(supervised_row,'Mos:')
            probation.probation_supervised_days = self.value_column(supervised_row,'Days:')
            probation.probation_supervised_hours = self.value_column(supervised_row,'Hours:')
            probation_unsupervised = self.value_multi_column(unsupervised_row,'^UnSupervised\s*:\s*')
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
                restitution = ODYCRIMRestitution(self.case_number)
                restitution.restitution_amount = self.value_multi_column(row,'Restitution Amount:',money=True)
                restitution.restitution_entered_date_str = self.value_column(row,'Entered Date:')
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
            warrant = ODYCRIMWarrant(self.case_number)
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
            bail_bond = ODYCRIMBailBond(self.case_number)
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
            bond_setting = ODYCRIMBondSetting(self.case_number)
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
            doc = ODYCRIMDocument(self.case_number)
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
            service = ODYCRIMService(self.case_number)
            service.service_type = self.format_value(vals[0].string)
            service.issued_date_str = self.format_value(vals[1].string,money=True)
            service.service_status = self.format_value(vals[2].string)
            db.add(service)
