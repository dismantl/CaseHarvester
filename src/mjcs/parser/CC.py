from ..db import TableBase
from .base import CaseDetailsParser, consumer, ParserError
from .common import CaseTable, date_from_str, RelatedPerson, Event, Trial
from sqlalchemy import Column, Date, Numeric, Integer, String, Boolean, ForeignKey, Time, BigInteger, Text
from sqlalchemy.orm import relationship
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.ext.declarative import declared_attr
from datetime import *
import re

class CC(CaseTable, TableBase):
    __tablename__ = 'cc'

    id = Column(Integer, primary_key=True)
    court_system = Column(String)
    title = Column(String)
    case_type = Column(String,nullable=True)
    filing_date = Column(Date,nullable=True)
    _filing_date_str = Column('filing_date_str',String,nullable=True)
    case_status = Column(String,nullable=True)
    case_disposition = Column(String,nullable=True)
    disposition_date = Column(Date,nullable=True)
    _disposition_date_str = Column('disposition_date_str',String,nullable=True)

    @hybrid_property
    def filing_date_str(self):
        return self._filing_date_str
    @filing_date_str.setter
    def filing_date_str(self,val):
        self.filing_date = date_from_str(val)
        self._filing_date_str = val

    @hybrid_property
    def disposition_date_str(self):
        return self._disposition_date_str
    @disposition_date_str.setter
    def disposition_date_str(self,val):
        self.disposition_date = date_from_str(val)
        self._disposition_date_str = val

class CCCaseTable(CaseTable):
    @declared_attr
    def case_number(cls):
        return Column(String, ForeignKey('cc.case_number', ondelete='CASCADE'))

class CCDistrictCaseNumber(CCCaseTable, TableBase):
    __tablename__ = 'cc_district_case_numbers'

    id = Column(Integer, primary_key=True)
    district_case_number = Column(String) # TODO eventually make a ForeignKey relation

class Party:
    id = Column(Integer, primary_key=True)
    party_type = Column(String)
    party_number = Column(Integer,nullable=True)
    name = Column(String,nullable=True)
    business_org_name = Column(String,nullable=True)

class CCPlaintiff(Party, CCCaseTable, TableBase):
    __tablename__ = 'cc_plaintiffs'

class CCDefendant(Party, CCCaseTable, TableBase):
    __tablename__ = 'cc_defendants'

class CCRelatedPerson(Party, CCCaseTable, TableBase):
    __tablename__ = 'cc_related_persons'

class CCPartyAlias(CCCaseTable, TableBase):
    __tablename__ = 'cc_party_alias'

    id = Column(Integer, primary_key=True)
    plaintiff_id = Column(Integer, ForeignKey('cc_plaintiffs.id'),nullable=True)
    defendant_id = Column(Integer, ForeignKey('cc_defendants.id'),nullable=True)
    related_person_id = Column(Integer, ForeignKey('cc_related_persons.id'),nullable=True)
    name = Column(String)

class CCPartyAddress(CCCaseTable, TableBase):
    __tablename__ = 'cc_party_addresses'

    id = Column(Integer, primary_key=True)
    plaintiff_id = Column(Integer, ForeignKey('cc_plaintiffs.id'),nullable=True)
    defendant_id = Column(Integer, ForeignKey('cc_defendants.id'),nullable=True)
    related_person_id = Column(Integer, ForeignKey('cc_related_persons.id'),nullable=True)
    address = Column(String)
    city = Column(String)
    state = Column(String)
    zip_code = Column(String)

class CCAttorney(CCCaseTable, TableBase):
    __tablename__ = 'cc_attorneys'

    id = Column(Integer, primary_key=True)
    plaintiff_id = Column(Integer, ForeignKey('cc_plaintiffs.id'),nullable=True)
    defendant_id = Column(Integer, ForeignKey('cc_defendants.id'),nullable=True)
    related_person_id = Column(Integer, ForeignKey('cc_related_persons.id'),nullable=True)
    name = Column(String)
    appearance_date = Column(Date,nullable=True)
    _appearance_date_str = Column('appearance_date_str',String,nullable=True)
    removal_date = Column(Date,nullable=True)
    _removal_date_str = Column('removal_date_str',String,nullable=True)
    practice_name = Column(String,nullable=True)
    address_1 = Column(String)
    address_2 = Column(String,nullable=True)
    city = Column(String)
    state = Column(String)
    zip_code = Column(String)

    @hybrid_property
    def appearance_date_str(self):
        return self._appearance_date_str
    @appearance_date_str.setter
    def appearance_date_str(self,val):
        self.appearance_date = date_from_str(val)
        self._appearance_date_str = val

    @hybrid_property
    def removal_date_str(self):
        return self._removal_date_str
    @removal_date_str.setter
    def removal_date_str(self,val):
        self.removal_date = date_from_str(val)
        self._removal_date_str = val

class CCCourtSchedule(CCCaseTable, TableBase):
    __tablename__ = 'cc_court_schedule'

    id = Column(Integer, primary_key=True)
    event_type = Column(String)
    notice_date = Column(Date,nullable=True)
    _notice_date_str = Column('notice_date_str',String)
    event_date = Column(Date,nullable=True)
    _event_date_str = Column('event_date_str',String)
    event_time = Column(Time, nullable=True)
    _event_time_str = Column('event_time_str', String)
    result = Column(String)
    result_date = Column(Date,nullable=True)
    _result_date_str = Column('result_date_str',String)

    @hybrid_property
    def notice_date_str(self):
        return self._notice_date_str
    @notice_date_str.setter
    def notice_date_str(self,val):
        self.notice_date = date_from_str(val)
        self._notice_date_str = val

    @hybrid_property
    def event_date_str(self):
        return self._event_date_str
    @event_date_str.setter
    def event_date_str(self,val):
        self.event_date = date_from_str(val)
        self._event_date_str = val

    @hybrid_property
    def event_time_str(self):
        return self._event_time_str
    @event_time_str.setter
    def event_time_str(self,val):
        try:
            self.time = datetime.strptime(val,'%I:%M %p').time()
        except:
            try:
                self.time = datetime.strptime(val,'%I:%M').time()
            except:
                pass
        self._event_time_str = val

    @hybrid_property
    def result_date_str(self):
        return self._result_date_str
    @result_date_str.setter
    def result_date_str(self,val):
        self.result_date = date_from_str(val)
        self._result_date_str = val

class CCDocument(CCCaseTable, TableBase):
    __tablename__ = 'cc_documents'

    id = Column(Integer, primary_key=True)
    document_number = Column(Integer)
    sequence_number = Column(Integer)
    file_date = Column(Date,nullable=True)
    _file_date_str = Column('file_date_str',String,nullable=True)
    entered_date = Column(Date,nullable=True)
    _entered_date_str = Column('entered_date_str',String,nullable=True)
    decision = Column(String,nullable=True)
    party_type = Column(String,nullable=True) # TODO could eventually map this and party_number to case parties
    party_number = Column(Integer,nullable=True)
    document_name = Column(String,nullable=True)
    text = Column(Text,nullable=True)

class CCJudgment(CCCaseTable, TableBase):
    __tablename__ = 'cc_judgments'

    id = Column(Integer, primary_key=True)
    judgment_type = Column(String)
    entered_date = Column(Date,nullable=True)
    _entered_date_str = Column('entered_date_str',String)
    amount = Column(Numeric)
    amount_other = Column(String,nullable=True)
    prejudgment_interest = Column(Numeric)
    appearance_fee = Column(Numeric)
    filing_fee = Column(Numeric)
    other_fee = Column(Numeric)
    service_fee = Column(Numeric)
    witness_fee = Column(Numeric)
    attorney_fee = Column(Numeric)
    total_indexed_judgment = Column(Numeric)
    tij_other = Column(String,nullable=True)
    comments = Column(String,nullable=True)

    @hybrid_property
    def entered_date_str(self):
        return self._entered_date_str
    @entered_date_str.setter
    def entered_date_str(self,val):
        self.entered_date = date_from_str(val)
        self._entered_date_str = val

class CCJudgmentModification(CCCaseTable, TableBase):
    __tablename__ = 'cc_judgment_modifications'

    id = Column(Integer, primary_key=True)
    judgment_id = Column(Integer, ForeignKey('cc_judgments.id'))
    judgment_against = Column(String)
    judgment_for = Column(String)
    entered_date = Column(Date,nullable=True)
    _entered_date_str = Column('entered_date_str',String)
    amount = Column(Numeric)
    amount_other = Column(String,nullable=True)
    status_date = Column(Date,nullable=True)
    _status_date_str = Column('status_date_str',String)
    status = Column(String)
    comments = Column(String,nullable=True)

    @hybrid_property
    def entered_date_str(self):
        return self._entered_date_str
    @entered_date_str.setter
    def entered_date_str(self,val):
        self.entered_date = date_from_str(val)
        self._entered_date_str = val

    @hybrid_property
    def status_date_str(self):
        return self._status_date_str
    @status_date_str.setter
    def status_date_str(self,val):
        self.status_date = date_from_str(val)
        self._status_date_str = val

class CCJudgmentAgainst(CCCaseTable, TableBase):
    __tablename__ = 'cc_judgments_against'

    id = Column(Integer, primary_key=True)
    judgment_id = Column(Integer, ForeignKey('cc_judgments.id'))
    name = Column(String)

class CCJudgmentInFavor(CCCaseTable, TableBase):
    __tablename__ = 'cc_judgments_in_favor'

    id = Column(Integer, primary_key=True)
    judgment_id = Column(Integer, ForeignKey('cc_judgments.id'))
    name = Column(String)

class CCSupportOrder(CCCaseTable, TableBase):
    __tablename__ = 'cc_support_orders'

    id = Column(Integer, primary_key=True)
    order_id = Column(Integer)
    version = Column(Integer)
    order_date = Column(Date,nullable=True)
    _order_date_str = Column('order_date_str',String)
    obligor = Column(String)
    effective_date = Column(Date,nullable=True)
    _effective_date_str = Column('effective_date_str',String)
    effective_date_text = Column(String,nullable=True) # TODO confirm data type
    status = Column(String)
    date = Column(Date,nullable=True)
    _date_str = Column('date_str',String)
    reason = Column(String,nullable=True)
    support_amount = Column(Numeric)
    support_frequency = Column(String,nullable=True)
    support_to = Column(String,nullable=True)
    arrears_amount = Column(Numeric)
    arrears_frequency = Column(String,nullable=True)
    arrears_to = Column(String,nullable=True)
    mapr_amount = Column(Numeric)
    mapr_frequency = Column(String,nullable=True)
    medical_insurance_report_date = Column(Date,nullable=True)
    _medical_insurance_report_date_str = Column('medical_insurance_report_date_str',String,nullable=True)
    btr_amount = Column(Numeric)
    btr_frequency = Column(String,nullable=True)
    lien = Column(String)
    provisions = Column(String,nullable=True) # TODO confirm data type

    @hybrid_property
    def order_date_str(self):
        return self._order_date_str
    @order_date_str.setter
    def order_date_str(self,val):
        self.order_date = date_from_str(val)
        self._order_date_str = val

    @hybrid_property
    def effective_date_str(self):
        return self._effective_date_str
    @effective_date_str.setter
    def effective_date_str(self,val):
        self.effective_date = date_from_str(val)
        self._effective_date_str = val

    @hybrid_property
    def date_str(self):
        return self._date_str
    @date_str.setter
    def date_str(self,val):
        self.date = date_from_str(val)
        self._date_str = val

    @hybrid_property
    def medical_insurance_report_date_str(self):
        return self._medical_insurance_report_date_str
    @medical_insurance_report_date_str.setter
    def medical_insurance_report_date_str(self,val):
        self.medical_insurance_report_date = date_from_str(val)
        self._medical_insurance_report_date_str = val

class CCParser(CaseDetailsParser):
    def header(self, soup):
        header = soup.find('div',class_='Header')
        header.decompose()
        subheader = soup.find('a',string='Go Back Now').find_parent('div')
        subheader.decompose()

    def footer(self, soup):
        footer = soup.find('div',class_='InfoStatement',string=re.compile('This is an electronic case record'))
        footer.decompose()

    #########################################################
    # CASE INFORMATION
    #########################################################
    def case(self, db, soup):
        a = datetime.now()
        self.delete_previous(db, CC)
        print("Took %s seconds to delete previous CC" % (datetime.now() - a).total_seconds())

        section_header = self.second_level_header(soup,'Case Information')
        t1 = self.table_next_first_column_prompt(section_header,'Court System:')

        case = CC(self.case_number)
        case.court_system = self.value_first_column(t1,'Court System:',remove_newlines=True)
        case_number = self.value_first_column(t1,'Case Number:')
        if case_number != self.case_number:
            raise ParserError('Case number "%s" in case details page does not match given: %s' % (case_number, self.case_number))
        case.title = self.value_first_column(t1,'Title:')
        case.case_type = self.value_first_column(t1,'Case Type:',ignore_missing=True)
        case.filing_date_str = self.value_column(t1,'Filing Date:',ignore_missing=True)
        case.case_status = self.value_first_column(t1,'Case Status:',ignore_missing=True)
        case.case_disposition = self.value_first_column(t1,'Case Disposition:',ignore_missing=True)
        case.disposition_date_str = self.value_column(t1,'Disposition Date:',ignore_missing=True)
        db.add(case)
        db.flush()

        if 'District Case No:' in t1.text:
            row = self.row_first_columm_prompt(t1,'District Case No:')
            while row:
                self.mark_for_deletion(row)
                d = CCDistrictCaseNumber(self.case_number)
                d.district_case_number = self.format_value(row.find('span',class_='Value').string)
                db.add(d)
                try:
                    row = self.immediate_sibling(row,'tr')
                except ParserError:
                    break


    ###########################################################
    # Party (Plaintiff, Defendant, Related Persons) Information
    ###########################################################
    def party(self, db, soup, party_str, party_cls, party_id_param):
        try:
            section_header = self.second_level_header(soup,'%s Information' % party_str)
        except ParserError:
            return
        info_charge_statement = self.info_charge_statement(section_header)

        prev_obj = info_charge_statement
        while True:
            name_table = None
            address_table = None
            attorney_table = None
            alias_table = None
            try:
                t1 = self.table_next_first_column_prompt(prev_obj,'Party Type:')
                t2 = self.immediate_sibling(t1,'table')
            except ParserError:
                break
            try:
                t3 = self.immediate_sibling(t2,'table')
                if 'Attorney(s) for the %s' % party_str in t3.text \
                        or 'Aliases %s' % party_str in t3.text:
                    raise ParserError('')
                prev_obj = t3
            except ParserError:
                t3 = None
                prev_obj = t2
            if 'Name:' in t2.text:
                name_table = t2
            elif 'Address:' in t2.text:
                address_table = t2
            if t3 and 'Address:' in t3.text:
                address_table = t3
            while True:
                try:
                    t4 = self.immediate_sibling(prev_obj,'table')
                    t5 = self.immediate_sibling(t4,'table')
                    prev_obj = t5
                except ParserError:
                    break
                if 'Attorney(s) for the %s' % party_str in t4.text:
                    self.mark_for_deletion(t4)
                    attorney_table = t5
                elif 'Aliases %s' % party_str in t4.text:
                    self.mark_for_deletion(t4)
                    alias_table = t5
            separator = self.immediate_sibling(prev_obj,'hr')
            prev_obj = separator

            p = party_cls(self.case_number)
            p.party_type = self.value_first_column(t1,'Party Type:')
            p.party_number = self.value_column(t1,'Party No.:',ignore_missing=True)
            if name_table:
                p.name = self.value_first_column(name_table,'Name:',ignore_missing=True)
                p.business_org_name = self.value_first_column(name_table,'Business or Organization Name:',ignore_missing=True)
            db.add(p)

            if address_table:
                for address_span in address_table.find_all('span',class_='FirstColumnPrompt',string='Address:'):
                    r1 = address_span.find_parent('tr')
                    r2 = self.immediate_sibling(r1,'tr')
                    addr = CCPartyAddress(self.case_number)
                    setattr(addr,party_id_param,p.id)
                    addr.address = self.value_first_column(r1,'Address:')
                    addr.city = self.value_first_column(r2,'City:')
                    addr.state = self.value_column(r2,'State:')
                    addr.zip_code = self.value_column(r2,'Zip Code:')
                    db.add(addr)

            if alias_table:
                for row in alias_table.find_all('tr'):
                    alias = CCPartyAlias(self.case_number)
                    setattr(alias,party_id_param,p.id)
                    alias.name = self.value_first_column(row,'Name:')
                    db.add(alias)

            if attorney_table:
                for name in attorney_table.find_all('span',class_='FirstColumnPrompt',string='Name:'):
                    a = CCAttorney(self.case_number)
                    setattr(a,party_id_param,p.id)
                    row = name.find_parent('tr')
                    a.name = self.value_first_column(row,'Name:')
                    row = self.immediate_sibling(row,'tr')
                    prompt = row.find('span',class_='FirstColumnPrompt').string
                    while prompt != 'Name:':
                        # print(prompt)
                        if prompt == 'Practice Name:':
                            a.practice_name = self.value_first_column(row,prompt)
                        elif prompt == 'Appearance Date:':
                            a.appearance_date_str = self.value_first_column(row,prompt)
                        elif prompt == 'Removal Date:':
                            a.removal_date_str = self.value_first_column(row,prompt)
                        elif prompt == 'Address:':
                            a.address_1 = self.value_first_column(row,prompt)
                        elif prompt == 'City:':
                            a.city = self.value_first_column(row,prompt)
                            a.state = self.value_column(row,'State:')
                            a.zip_code = self.value_column(row,'Zip Code:')
                        elif not prompt:
                            address_2 = row\
                                .find('span',class_='Value')\
                                .string
                            self.mark_for_deletion(address_2.parent)
                            a.address_2 = self.format_value(address_2)
                        else:
                            raise Exception('Unknown prompt %s' % prompt)
                        try:
                            row = self.immediate_sibling(row,'tr')
                        except ParserError:
                            break
                        prompt = row.find('span',class_='FirstColumnPrompt').string
                    db.add(a)

    #########################################################
    # Plaintiff/Petitioner Information
    #########################################################
    @consumer
    def plaintiff(self, db, soup):
        return self.party(db, soup, 'Plaintiff/Petitioner', CCPlaintiff, 'plaintiff_id')

    #########################################################
    # Defendant/Respondent Information
    #########################################################
    @consumer
    def defendant(self, db, soup):
        return self.party(db, soup, 'Defendant/Respondent', CCDefendant, 'defendant_id')

    #########################################################
    # Related Persons Information
    #########################################################
    @consumer
    def related_persons(self, db, soup):
        return self.party(db, soup, 'Related Persons', CCRelatedPerson, 'related_person_id')

    #########################################################
    # Court Scheduling Information
    #########################################################
    @consumer
    def court_scheduling(self, db, soup):
        try:
            section_header = self.second_level_header(soup,'Court Scheduling Information')
        except ParserError:
            return

        prev_obj = section_header
        while True:
            try:
                t1 = self.table_next_first_column_prompt(prev_obj,'Event Type:')
                separator = self.immediate_sibling(t1,'hr')
                prev_obj = separator
            except ParserError:
                break

            s = CCCourtSchedule(self.case_number)
            s.event_type = self.value_first_column(t1,'Event Type:')
            s.notice_date_str = self.value_column(t1,'Notice Date:')
            s.event_date_str = self.value_first_column(t1,'Event Date:')
            s.event_time_str = self.value_column(t1,'Event Time:')
            s.result = self.value_first_column(t1,'Result:')
            s.result_date_str = self.value_column(t1,'Result Date:')
            db.add(s)

    #########################################################
    # Support Order Information
    #########################################################
    @consumer
    def support_order(self, db, soup):
        try:
            section_header = self.second_level_header(soup,'Support Order Information')
        except ParserError:
            return
        info_charge_statement = self.info_charge_statement(section_header)

        prev_obj = info_charge_statement
        while True:
            try:
                t1 = self.table_next_first_column_prompt(prev_obj,'Order ID:')
                separator = self.immediate_sibling(t1,'hr')
                prev_obj = separator
            except ParserError:
                break
            o = CCSupportOrder(self.case_number)
            o.order_id = self.value_first_column(t1,'Order ID:')
            o.version = self.value_column(t1,'Ver:')
            o.order_date_str = self.value_first_column(t1,'Order Date:')
            o.obligor = self.value_column(t1,'Obligor:')
            o.effective_date_str = self.value_first_column(t1,'Effective Date:')
            o.effective_date_text = self.value_column(t1,'Eff. Date Text:')
            o.status = self.value_first_column(t1,'Status:')
            o.date_str = self.value_column(t1,'Date:')
            o.reason = self.value_column(t1,'Reason:')
            support_row = t1\
                .find('span',class_='FirstColumnPrompt',string='Support Amt:')\
                .find_parent('tr')
            o.support_amount = self.value_first_column(support_row,'Support Amt:')
            o.support_frequency = self.value_column(support_row,'Freq:')
            o.support_to = self.value_column(support_row,'To:')
            arrears_row = t1\
                .find('span',class_='FirstColumnPrompt',string='Arrears Amt:')\
                .find_parent('tr')
            o.arrears_amount = self.value_first_column(arrears_row,'Arrear   s Amt:')
            o.arrears_frequency = self.value_column(arrears_row,'Freq:')
            o.arrears_to = self.value_column(arrears_row,'To:')
            mapr_row = t1\
                .find('span',class_='FirstColumnPrompt',string='MAPR Amt:')\
                .find_parent('tr')
            o.mapr_amount = self.value_first_column(mapr_row,'MAPR Amt:')
            o.mapr_frequency = self.value_column(mapr_row,'Freq:')
            o.medical_insurance_report_date = self.value_first_column(t1,'Medical Insurance Report Date:')
            btr_row = t1\
                .find('span',class_='FirstColumnPrompt',string='BTR Amt:')\
                .find_parent('tr')
            o.btr_amount = self.value_first_column(btr_row,'BTR Amt:')
            o.btr_frequency = self.value_column(btr_row,'Freq:')
            o.lien = self.value_first_column(t1,'Lien:')
            o.provisions = self.value_column(t1,'Provisions:')
            db.add(o)

    #########################################################
    # Judgment Information
    #########################################################
    @consumer
    def judgments(self, db, soup):
        try:
            section_header = self.second_level_header(soup,'Judgment Information')
        except ParserError:
            return
        section = self.immediate_sibling(section_header,'div',class_='AltBodyWindow1')
        self.judgment(db, section, 'money')
        self.judgment(db, section, 'non-money')
        self.judgment(db, section, 'costs')

    def judgment(self, db, section, judgment_str):
        for judgment in section.find_all('span',class_='Value',string=judgment_str.upper() + ' JUDGMENT'):
            t1 = judgment.find_parent('table')
            self.mark_for_deletion(judgment)
            self.mark_for_deletion(t1.find('h6',string='ORIGINAL JUDGMENT'))
            j = CCJudgment(self.case_number)
            j.judgment_type = judgment_str
            j.entered_date_str = self.value_first_column(t1,'Judgment Entered Date:')
            j.other_fee = self.value_first_column(t1,'Other Fee:',money=True)
            j.amount = self.value_first_column(t1,'Amount of Judgment:',money=True)
            if j.amount:
                try:
                    float(j.amount)
                except ValueError:
                    j.amount_other = j.amount
                    j.amount = 0
            j.service_fee = self.value_first_column(t1,'Service Fee:',money=True)
            j.prejudgment_interest = self.value_first_column(t1,'PreJudgment Interest:',money=True)
            j.witness_fee = self.value_first_column(t1,'Witness Fee:',money=True)
            j.appearance_fee = self.value_first_column(t1,'Appearance Fee:',money=True)
            j.attorney_fee = self.value_first_column(t1,'Attorney Fee:',money=True)
            j.filing_fee = self.value_first_column(t1,'Filing Fee:',money=True)
            j.total_indexed_judgment = self.value_first_column(t1,'Total Indexed Judgment:',money=True)
            if j.total_indexed_judgment:
                try:
                    float(j.total_indexed_judgment)
                except ValueError:
                    j.tij_other = j.total_indexed_judgment
                    j.total_indexed_judgment = 0
            j.comments = self.value_first_column(t1,'Comments:',ignore_missing=True)
            db.add(j)

            against_prompt = t1.find('span',class_='FirstColumnPrompt',string='Judgment Against:')
            self.mark_for_deletion(against_prompt)
            t2 = against_prompt.find_parent('td').find_next_sibling('td').find('table')
            for value in t2.find_all('span',class_='Value'):
                if value.string:
                    self.mark_for_deletion(value)
                    j_against = CCJudgmentAgainst(self.case_number)
                    j_against.judgment_id = j.id
                    j_against.name = self.format_value(value.string).rstrip(',')
                    db.add(j_against)

            in_favor_prompt = t1.find('span',class_='FirstColumnPrompt',string='Judgment in Favor of:')
            self.mark_for_deletion(in_favor_prompt)
            t2 = in_favor_prompt.find_parent('td').find_next_sibling('td').find('table')
            for value in t2.find_all('span',class_='Value'):
                if value.string:
                    self.mark_for_deletion(value)
                    j_in_favor = CCJudgmentAgainst(self.case_number)
                    j_in_favor.judgment_id = j.id
                    j_in_favor.name = self.format_value(value.string).rstrip(',')
                    db.add(j_in_favor)

            try:
                modifications_header = self.immediate_sibling(t1,'h6',string='JUDGMENT MODIFICATIONS')
            except ParserError:
                continue
            self.mark_for_deletion(modifications_header)
            prev_obj = modifications_header
            while True:
                try:
                    t2 = self.table_next_first_column_prompt(prev_obj,'Against:')
                    prev_obj = t2
                except ParserError:
                    break
                m = CCJudgmentModification(self.case_number)
                m.judgment_id = j.id
                m.judgment_against = self.value_first_column(t2,'Against:')
                m.judgment_for = self.value_first_column(t2,'For:')
                m.entered_date_str = self.value_first_column(t2,'Judgment Entered Date:')
                m.amount = self.value_first_column(t2,'Amount:',money=True)
                if m.amount:
                    try:
                        float(m.amount)
                    except ValueError:
                        m.amount_other = m.amount
                        m.amount = 0
                m.status_date_str = self.value_first_column(t2,'Status Date:')
                m.status = self.value_first_column(t2,'Status:')
                m.comments = self.value_first_column(t2,'Comments:')
                db.add(m)

    #########################################################
    # Document Tracking
    #########################################################
    @consumer
    def document_tracking(self, db, soup):
        try:
            section_header = self.second_level_header(soup,'Document Tracking')
        except ParserError:
            return
        info_charge_statement = self.info_charge_statement(section_header)

        prev_obj = info_charge_statement
        while True:
            try:
                t1 = self.table_next_first_column_prompt(prev_obj,'Doc No./Seq No.:')
                separator = self.immediate_sibling(t1,'hr')
                prev_obj = separator
            except ParserError:
                break

            d = CCDocument(self.case_number)
            doc_seq = self.value_first_column(t1,'Doc No./Seq No.:')
            d.document_number, d.sequency_number = doc_seq.split('/')
            d.file_date_str = self.value_first_column(t1,'File Date:',ignore_missing=True)
            d.entered_date_str = self.value_column(t1,'Entered Date:',ignore_missing=True)
            d.decision = self.value_column(t1,'Decision:',ignore_missing=True)
            d.party_type = self.value_first_column(t1,'Party Type:',ignore_missing=True)
            d.party_number = self.value_column(t1,'Party No.:',ignore_missing=True)
            d.document_name = self.value_first_column(t1,'Document Name:',ignore_missing=True)
            last_row = list(t1.find_all('tr'))[-1]
            if not last_row.find('span',class_='FirstColumnPrompt').string:
                text = last_row\
                    .find('span',class_='Value')\
                    .string
                if text:
                    self.mark_for_deletion(text.parent)
                    d.text = self.format_value(text)
            db.add(d)
