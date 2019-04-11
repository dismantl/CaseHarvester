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

class ODYTRAFDefendantAlias(ODYTRAFCaseTable, TableBase):
    __tablename__ = 'odytraf_defendant_aliases'

    id = Column(Integer, primary_key=True)
    alias = Column(String, nullable=False)
    alias_type = Column(String, nullable=False)

class ODYTRAFNAmeAddress:
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    address = Column(String, nullable=True)
    city = Column(String, nullable=True)
    state = Column(String, nullable=True)
    zip_code = Column(String, nullable=True)

class ODYTRAFBondsman(ODYTRAFCaseTable, ODYTRAFNAmeAddress, TableBase):
    __tablename__ = 'odytraf_bondsmen'

class ODYTRAFSurety(ODYTRAFCaseTable, ODYTRAFNAmeAddress, TableBase):
    __tablename__ = 'odytraf_sureties'

class ODYTRAFProbationOfficer(ODYTRAFCaseTable, ODYTRAFNAmeAddress, TableBase):
    __tablename__ = 'odytraf_probation_officers'

class ODYTRAFInterpreter(ODYTRAFCaseTable, ODYTRAFNAmeAddress, TableBase):
    __tablename__ = 'odytraf_interpreters'

class ODYTRAFPlaintiff(ODYTRAFCaseTable, TableBase):
    __tablename__ = 'odytraf_plaintiffs'

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)

class ODYTRAFOfficer(ODYTRAFCaseTable, TableBase):
    __tablename__ = 'odytraf_officers'

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=True)
    agency_name = Column(String, nullable=False)
    address_1 = Column(String, nullable=True)
    address_2 = Column(String, nullable=True)
    city = Column(String, nullable=True)
    state = Column(String, nullable=True)
    zip_code = Column(String, nullable=True)
    role = Column(String, nullable=False)

class ODYTRAFAttorney(ODYTRAFCaseTable, TableBase):
    __tablename__ = 'odytraf_attorneys'

    id = Column(Integer, primary_key=True)
    plaintiff_id = Column(Integer, ForeignKey('odytraf_plaintiffs.id'),nullable=True)
    defendant_id = Column(Integer, ForeignKey('odytraf_defendants.id'),nullable=True)
    name = Column(String, nullable=True)
    address_1 = Column(String, nullable=True)
    address_2 = Column(String, nullable=True)
    address_3 = Column(String, nullable=True)
    city = Column(String, nullable=True)
    state = Column(String, nullable=True)
    zip_code = Column(String, nullable=True)

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

# Note that consumers may not be called in order
class ODYTRAFParser(CaseDetailsParser):
    def __init__(self, case_number, html):
        # <body> should only have a single child div that holds the data
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
        a = datetime.now()
        self.delete_previous(db, ODYTRAF)
        print("Took %s seconds to delete previous ODYTRAF" % (datetime.now() - a).total_seconds())

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
            if t.find('span',class_='FirstColumnPrompt',string=re.compile('Same Incident')):
                ref_num = ODYTRAFReferenceNumber(self.case_number)
                ref_num.ref_num = self.value_first_column(t,'Same Incident')
                ref_num.ref_num_type = 'Same Incident'
            elif t.find('span',class_='FirstColumnPrompt',string=re.compile('Conversion Default Case Cross Reference Numbers')):
                ref_num = ODYTRAFReferenceNumber(self.case_number)
                ref_num.ref_num = self.value_first_column(t,'Conversion Default Case Cross Reference Numbers')
                ref_num.ref_num_type = 'Conversion Default Case Cross Reference Numbers'
            elif t.find('span',class_='FirstColumnPrompt',string=re.compile('Related Case')):
                ref_num = ODYTRAFReferenceNumber(self.case_number)
                ref_num.ref_num = self.value_first_column(t,'Related Case')
                ref_num.ref_num_type = 'Related Case'
            else:
                break
            db.add(ref_num)
            prev_obj = t

    #########################################################
    # DEFENDENT INFORMATION
    #########################################################
    @consumer
    def defendant(self, db, soup):
        section_header = self.first_level_header(soup,'Defendant Information')
        defendant = ODYTRAFDefendant(self.case_number)
        subsection_header = self.second_level_header(soup, '^Defendant$')

        name_table = self.table_next_first_column_prompt(subsection_header,'Name:')
        defendant.name = self.value_first_column(name_table,'Name:')

        address_table = self.table_next_first_column_prompt(name_table,'Address:')
        address_row1 = self.row_first_columm_prompt(address_table,'Address:')
        defendant.address_1 = self.value_first_column(address_row1,'Address:')
        try:
            address_row2 = self.row_next_first_column_prompt(address_row1,'Address:')
        except ParserError:
            pass
        else:
            defendant.address_2 = self.value_first_column(address_row2,'Address:')
        defendant.city = self.value_first_column(address_table,'City:')
        defendant.state = self.value_column(address_table,'State:')
        defendant.zip_code = self.value_column(address_table,'Zip Code:')

        demographics_table = self.immediate_sibling(address_table,'table')
        if list(demographics_table.stripped_strings):
            defendant.race = self.value_combined_first_column(demographics_table,'Race:')
            defendant.sex = self.value_column(demographics_table,'Sex:')
            defendant.height = self.value_column(demographics_table,'Height:')
            defendant.weight = self.value_column(demographics_table,'Weight:')
            defendant.DOB_str = self.value_combined_first_column(demographics_table,'DOB:')
        db.add(defendant)
        db.flush()

        # Defendent Aliases
        try:
            subsection_header = self.first_level_header(soup,'Aliases')
        except ParserError:
            pass
        else:
            prev_obj = subsection_header
            while True:
                try:
                    alias_table = self.immediate_sibling(prev_obj,'table')
                except ParserError:
                    break
                if alias_table.find('span',class_='FirstColumnPrompt',string=re.compile('Nickname')):
                    def_alias = ODYTRAFDefendantAlias(self.case_number)
                    def_alias.alias = self.value_first_column(alias_table,'Nickname')
                    def_alias.alias_type = 'Nickname'
                elif alias_table.find('span',class_='FirstColumnPrompt',string=re.compile('Standard')):
                    def_alias = ODYTRAFDefendantAlias(self.case_number)
                    def_alias.alias = self.value_first_column(alias_table,'Standard')
                    def_alias.alias_type = 'Standard'
                else:
                    break
                db.add(def_alias)
                prev_obj = alias_table

        # Defendant attorney(s)
        try:
            subsection_header = self.first_level_header(soup,'Attorney\(s\) for the\s+Defendant')
        except ParserError:
            pass
        else:
            attorney_table = self.table_next_first_column_prompt(subsection_header,'Name:')
            for span in attorney_table.find_all('span',class_='FirstColumnPrompt',string='Name:'):
                attorney = ODYTRAFAttorney(self.case_number)
                attorney.defendant_id = defendant.id
                name_row = span.find_parent('tr')
                attorney.name = self.value_first_column(name_row,'Name:')
                address_row = self.row_next_first_column_prompt(name_row,'Address Line 1:')
                attorney.address_1 = self.value_first_column(address_row,'Address Line 1:')
                prev_obj = address_row
                try:
                    address_row_2 = self.row_next_first_column_prompt(address_row,'Address Line 2:')
                except ParserError:
                    pass
                else:
                    prev_obj = address_row_2
                    attorney.address_2 = self.value_first_column(address_row_2,'Address Line 2:')
                    try:
                        address_row_3 = self.row_next_first_column_prompt(address_row_2,'Address Line 3:')
                    except ParserError:
                        pass
                    else:
                        prev_obj = address_row_3
                        attorney.address_3 = self.value_first_column(address_row_3,'Address Line 3:')
                city_row = self.row_next_first_column_prompt(prev_obj,'City:')
                attorney.city = self.value_first_column(city_row,'City:')
                attorney.state = self.value_column(city_row,'State:')
                attorney.zip_code = self.value_column(city_row,'Zip Code:')
                db.add(attorney)

    #########################################################
    # INVOLVED PARTIES INFORMATION
    #########################################################
    @consumer
    def involved_parties(self, db, soup):
        try:
            section_header = self.first_level_header(soup, 'Involved Parties Information')
        except ParserError:
            return
        plaintiff = ODYTRAFPlaintiff(self.case_number)
        subsection_header = self.second_level_header(soup, '^Plaintiff$')
        name_table = self.table_next_first_column_prompt(subsection_header,'Name:')
        plaintiff.name = self.value_first_column(name_table,'Name:')
        db.add(plaintiff)
        db.flush()

        # Attorney(s) for the Plaintiff
        try:
            subsection_header = self.first_level_header(soup,'Attorney\(s\) for the\s+Plaintiff')
        except ParserError:
            pass
        else:
            attorney_table = self.table_next_first_column_prompt(subsection_header,'Name:')
            for span in attorney_table.find_all('span',class_='FirstColumnPrompt',string='Name:'):
                attorney = ODYTRAFAttorney(self.case_number)
                attorney.plaintiff_id = plaintiff.id
                name_row = span.find_parent('tr')
                attorney.name = self.value_first_column(name_row,'Name:')
                address_row = self.row_next_first_column_prompt(name_row,'Address Line 1:')
                attorney.address_1 = self.value_first_column(address_row,'Address Line 1:')
                prev_obj = address_row
                try:
                    address_row_2 = self.row_next_first_column_prompt(address_row,'Address Line 2:')
                except ParserError:
                    pass
                else:
                    prev_obj = address_row_2
                    attorney.address_2 = self.value_first_column(address_row_2,'Address Line 2:')
                    try:
                        address_row_3 = self.row_next_first_column_prompt(address_row_2,'Address Line 3:')
                    except ParserError:
                        pass
                    else:
                        prev_obj = address_row_3
                        attorney.address_3 = self.value_first_column(address_row_3,'Address Line 3:')
                city_row = self.row_next_first_column_prompt(prev_obj,'City:')
                attorney.city = self.value_first_column(city_row,'City:')
                attorney.state = self.value_column(city_row,'State:')
                attorney.zip_code = self.value_column(city_row,'Zip Code:')
                db.add(attorney)

        # Bond Remitter/Bondsman
        try:
            subsection_header = self.second_level_header(soup,'Bond Remitter/Bondsman')
        except ParserError:
            pass
        else:
            bondsman = ODYTRAFBondsman(self.case_number)
            name_table = self.table_next_first_column_prompt(subsection_header,'Name:')
            bondsman.name = self.value_first_column(name_table,'Name:')
            address_table = self.table_next_first_column_prompt(name_table,'Address:')
            bondsman.address = self.value_first_column(address_table,'Address:')
            bondsman.city = self.value_first_column(address_table,'City:')
            bondsman.state = self.value_column(address_table,'State:')
            bondsman.zip_code = self.value_column(address_table,'Zip Code:')
            db.add(bondsman)

        # Surety
        try:
            subsection_header = self.second_level_header(soup,'Surety')
        except ParserError:
            pass
        else:
            surety = ODYTRAFSurety(self.case_number)
            name_table = self.table_next_first_column_prompt(subsection_header,'Name:')
            surety.name = self.value_first_column(name_table,'Name:')
            address_table = self.table_next_first_column_prompt(name_table,'Address:')
            surety.address = self.value_first_column(address_table,'Address:')
            surety.city = self.value_first_column(address_table,'City:')
            surety.state = self.value_column(address_table,'State:')
            surety.zip_code = self.value_column(address_table,'Zip Code:')
            db.add(surety)

        # Probation Officer
        try:
            subsection_header = self.second_level_header(soup,'Probation Officer')
        except ParserError:
            pass
        else:
            officer = ODYTRAFProbationOfficer(self.case_number)
            name_table = self.table_next_first_column_prompt(subsection_header,'Name:')
            officer.name = self.value_first_column(name_table,'Name:')
            address_table = self.table_next_first_column_prompt(name_table,'Address:')
            officer.address = self.value_first_column(address_table,'Address:')
            officer.city = self.value_first_column(address_table,'City:')
            officer.state = self.value_column(address_table,'State:')
            officer.zip_code = self.value_column(address_table,'Zip Code:')
            db.add(officer)

    #########################################################
    # OFFICER - ARRESTING/COMPLAINT
    #########################################################
    @consumer
    def arresting_officer(self, db, soup):
        try:
            section_header = self.second_level_header(soup, 'Officer - Arresting/Complainant')
        except ParserError:
            return
        officer = ODYTRAFOfficer(self.case_number)
        officer.role = 'Officer - Arresting/Complainant'
        name_table = self.table_next_first_column_prompt(section_header,'Name:')
        officer.name = self.value_first_column(name_table,'Name:')
        officer.agency_name = self.value_first_column(name_table,'AgencyName:')
        try:
            address_table = self.table_next_first_column_prompt(name_table,'Address:')
        except ParserError:
            pass
        else:
            officer.address_1 = self.value_first_column(address_table,'Address:')
            addr_spans = address_table.find_all('span',class_='FirstColumnPrompt',string='Address:')
            if len(addr_spans) == 2:
                row_2 = addr_spans[1].find_parent('tr')
                officer.address_2 = self.value_first_column(row_2,'Address:')
            officer.city = self.value_first_column(address_table,'City:')
            officer.state = self.value_column(address_table,'State:')
            officer.zip_code = self.value_column(address_table,'Zip Code:')
        db.add(officer)

    #########################################################
    # POLICE OFFICER
    #########################################################
    @consumer
    def officer(self, db, soup):
        officer_headers = soup.find_all('h5',string='Police Officer')
        if not officer_headers:
            return
        for section_header in officer_headers:
            self.mark_for_deletion(section_header)
            officer = ODYTRAFOfficer(self.case_number)
            officer.role = 'Police Officer'
            name_table = self.table_next_first_column_prompt(section_header,'Name:')
            officer.name = self.value_first_column(name_table,'Name:')
            officer.agency_name = self.value_first_column(name_table,'AgencyName:')
            address_table = self.table_next_first_column_prompt(name_table,'Address:')
            officer.address_1 = self.value_first_column(address_table,'Address:')
            addr_spans = address_table.find_all('span',class_='FirstColumnPrompt',string='Address:')
            if len(addr_spans) == 2:
                row_2 = addr_spans[1].find_parent('tr')
                officer.address_2 = self.value_first_column(row_2,'Address:')
            officer.city = self.value_first_column(address_table,'City:')
            officer.state = self.value_column(address_table,'State:')
            officer.zip_code = self.value_column(address_table,'Zip Code:')
            db.add(officer)

    #########################################################
    # INTERPRETER
    #########################################################
    @consumer
    def interpeter(self, db, soup):
        try:
            section_header = self.second_level_header(soup, 'Interpreter')
        except ParserError:
            return
        interpreter = ODYTRAFInterpreter(self.case_number)
        name_table = self.table_next_first_column_prompt(section_header,'Name:')
        interpreter.name = self.value_first_column(name_table,'Name:')
        address_table = self.table_next_first_column_prompt(name_table,'Address:')
        interpreter.address = self.value_first_column(address_table,'Address:')
        interpreter.city = self.value_first_column(address_table,'City:')
        interpreter.state = self.value_column(address_table,'State:')
        interpreter.zip_code = self.value_column(address_table,'Zip Code:')
        db.add(interpreter)

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
            prev_obj = row

    #########################################################
    # CHARGE AND DISPOSITION INFORMATION
    #########################################################
    @consumer
    def charge_and_disposition(self, db, soup):
        try:
            section_header = self.first_level_header(soup,'Charge and Disposition Information')
        except ParserError:
            return
        container = self.immediate_sibling(section_header,'div',class_='AltBodyWindow1')
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
        charge.fine_amount_owed = self.value_column(t7,'Fine Amount Owed:')
        t8 = self.immediate_sibling(t7,'table')
        charge.vehicle_tag = self.value_multi_column(t8,'Vehicle Tag:')
        charge.state = self.value_multi_column(t8,'State:')
        charge.vehicle_description = self.value_multi_column(t8,'Vehicle Description:')

        # Disposition
        try:
            subsection_header = soup.find('i',string='Disposition').find_parent('left')
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
            subsection_header = soup.find('i',string='Converted Disposition:').find_parent('left')
        except (ParserError, AttributeError):
            pass
        else:
            self.mark_for_deletion(subsection_header)
            t = self.immediate_sibling(subsection_header,'table')
            list_no = t.find('td',string='1. ')
            self.mark_for_deletion(list_no)
            span = t.find('span',class_='Value')
            charge.converted_disposition = self.format_value(span.string)
            self.mark_for_deletion(span)

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
            self.mark_for_deletion(row)
            vals = row.find_all('span',class_='Value')
            warrant = ODYTRAFWarrant(self.case_number)
            warrant.warrant_type = self.format_value(vals[0].string)
            warrant.issue_date_str = self.format_value(vals[1].string)
            warrant.last_status = self.format_value(vals[2].string)
            warrant.status_date_str = self.format_value(vals[3].string)
            db.add(warrant)
            prev_obj = row

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
