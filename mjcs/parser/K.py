from ..models import (K, KDefendant,
                     KRelatedPerson, KPartyAlias, KPartyAddress, KAttorney,
                     KCourtSchedule, KJudgment, KJudgmentModification,
                     KJudgmentAgainst, KJudgmentInFavor, KSupportOrder,
                     KDocument, KCharge, KSentencingNetTools)
from .base import CaseDetailsParser, consumer, ParserError, ChargeFinder
import re

class KParser(CaseDetailsParser, ChargeFinder):
    inactive_statuses = [
        'Closed/Inactive'
    ]

    def header(self, soup):
        header = soup.find('div',class_='Header')
        header.decompose()
        goback = soup.find('a',string='Go Back Now')
        if not goback:
            raise ParserError('Missing expected "Go Back Now" link')
        goback = goback.find_parent('div')
        goback.decompose()

    def footer(self, soup):
        footer = soup.find('div',class_='InfoStatement',string=re.compile('This is an electronic case record'))
        footer.decompose()

    #########################################################
    # CASE INFORMATION
    #########################################################
    def case(self, db, soup):
        section_header = self.first_level_header(soup,'Case Information')
        t1 = self.table_next_first_column_prompt(section_header,'Court System:')

        case = K(case_number=self.case_number)
        case.court_system = self.value_first_column(t1,'Court System:',remove_newlines=True)
        case_number = self.value_first_column(t1,'Case Number:')
        if case_number != self.case_number:
            raise ParserError('Case number "%s" in case details page does not match given: %s' % (case_number, self.case_number))
        case.title = self.value_first_column(t1,'Title:')
        case.case_type = self.value_first_column(t1,'Case Type:',ignore_missing=True)
        case.filing_date_str = self.value_column(t1,'Filing Date:',ignore_missing=True)
        case.case_status = self.value_first_column(t1,'Case Status:',ignore_missing=True)
        self.case_status = case.case_status
        case.case_disposition = self.value_first_column(t1,'Case Disposition:',ignore_missing=True)
        case.disposition_date_str = self.value_column(t1,'Disposition Date:',ignore_missing=True)
        db.add(case)
        db.flush()

    ###########################################################
    # Party (Defendant, Related Person) Information
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
            just_attorney = False
            try:
                t1 = self.table_next_first_column_prompt(prev_obj,'Party Type:')
            except ParserError:
                try:
                    t1 = self.table_next_first_column_prompt(prev_obj,'Name:')
                except ParserError:
                    try:
                        if list(self.immediate_sibling(prev_obj, 'table').stripped_strings) == ['Attorney(s) for the Related Person']:
                            just_attorney = True
                    except ParserError:
                        break
            party_id = None
            if not just_attorney:
                t2 = self.immediate_sibling(t1,'table')
                t3 = self.immediate_sibling(t2,'table')

                p = party_cls(case_number=self.case_number)
                p.party_type = self.value_combined_first_column(t1,'Party Type:',ignore_missing=True)
                if not p.party_type:
                    p.party_type = party_str
                # p.party_number = self.value_column(t1,'Party No.:',ignore_missing=True)
                name_table = t1
                if name_table:
                    p.name = self.value_combined_first_column(name_table,'Name:',ignore_missing=True)
                    if not p.name:
                        p.name = self.value_first_column(name_table,'Name:',ignore_missing=True)
                    # p.business_org_name = self.value_first_column(name_table,'Business or Organization Name:',ignore_missing=True)
                db.add(p)
                db.flush()
                party_id = p.id

                if party_str == 'Defendant':
                    demographics_table = t2
                    address_table = t3
                    address_table_2 = t3
                else:
                    demographics_table = None
                    address_table = t2
                    address_table_2 = t3

                if demographics_table:
                    p.race = self.value_first_column(demographics_table,'Race:',ignore_missing=True)
                    p.sex = self.value_first_column(demographics_table,'Sex:')
                    p.height = self.value_column(demographics_table,'Height:')
                    p.weight = self.value_column(demographics_table,'Weight:')
                    p.DOB_str = self.value_column(demographics_table,'DOB:')

                if address_table:
                    if address_table == address_table_2:
                        for span in address_table.find_all('span',class_='FirstColumnPrompt',string='City:'):
                            city_row = span.find_parent('tr')
                            addr_row = city_row.find_previous_sibling('tr')
                            addr = KPartyAddress(case_number=self.case_number)
                            setattr(addr,party_id_param,party_id)
                            addr.address_1 = self.value_combined_first_column(addr_row,'Address:',ignore_missing=True)
                            if not addr.address_1:
                                addr.address_1 = self.value_first_column(addr_row,'Address:',ignore_missing=True)
                            if len(address_table.find_all('span',class_='FirstColumnPrompt',string='Address:')) == 2:
                                row = address_table.find_all('span',class_='FirstColumnPrompt',string='Address:')[1].find_parent('tr')
                                addr.address_2 = self.value_combined_first_column(row,'Address:')
                                if not addr.address_2:
                                    addr.address_2 = self.value_first_column(row,'Address:')
                            addr.city = self.value_first_column(city_row,'City:')
                            addr.state = self.value_column(city_row,'State:')
                            addr.zip_code = self.value_column(city_row,'Zip Code:')
                            db.add(addr)
                    else:
                        addr = KPartyAddress(case_number=self.case_number)
                        setattr(addr,party_id_param,party_id)
                        addr.address_1 = self.value_combined_first_column(address_table,'Address:',ignore_missing=True)
                        if not addr.address_1:
                            addr.address_1 = self.value_first_column(address_table,'Address:',ignore_missing=True)
                        if len(address_table.find_all('span',class_='FirstColumnPrompt',string='Address:')) > 1:
                            row = address_table.find_all('span',class_='FirstColumnPrompt',string='Address:')[1].find_parent('tr')
                            addr.address_2 = self.value_combined_first_column(row,'Address:')
                            if not addr.address_2:
                                addr.address_2 = self.value_first_column(row,'Address:')
                            try:
                                row = address_table.find_all('span',class_='FirstColumnPrompt',string='Address:')[2].find_parent('tr')
                            except IndexError:
                                pass
                            else:
                                addr.address_3 = self.value_combined_first_column(row,'Address:')
                                if not addr.address_3:
                                    addr.address_3 = self.value_first_column(row,'Address:')
                        addr.city = self.value_first_column(address_table_2,'City:')
                        addr.state = self.value_column(address_table_2,'State:')
                        addr.zip_code = self.value_column(address_table_2,'Zip Code:')
                        db.add(addr)

                prev_obj = t3

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
                    for name in attorney_table.find_all('span',class_='FirstColumnPrompt',string='Name:'):
                        a = KAttorney(case_number=self.case_number)
                        setattr(a,party_id_param,party_id)
                        row = name.find_parent('tr')
                        a.name = self.value_first_column(row,'Name:')
                        row = self.immediate_sibling(row,'tr')
                        prompt = row.find('span',class_='FirstColumnPrompt').string
                        while prompt != 'Name:':
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
                elif '%s Aliases' % party_str in t4.text:
                    self.mark_for_deletion(t4)
                    alias_table = t5
                    for row in alias_table.find_all('tr'):
                        alias = KPartyAlias(case_number=self.case_number)
                        setattr(alias,party_id_param,party_id)
                        alias.name = self.value_first_column(row,'Name:')
                        db.add(alias)
            try:
                separator = self.immediate_sibling(prev_obj,'hr')
            except ParserError:
                break
            prev_obj = separator

    #########################################################
    # Defendant Information
    #########################################################
    @consumer
    def defendant(self, db, soup):
        return self.party(db, soup, 'Defendant', KDefendant, 'defendant_id')

    #########################################################
    # Related Persons Information
    #########################################################
    @consumer
    def related_persons(self, db, soup):
        return self.party(db, soup, 'Related Person', KRelatedPerson, 'related_person_id')

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

            s = KCourtSchedule(case_number=self.case_number)
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
            o = KSupportOrder(case_number=self.case_number)
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
            o.support_amount = self.value_first_column(support_row,'Support Amt:',money=True)
            o.support_frequency = self.value_column(support_row,'Freq:')
            o.support_to = self.value_column(support_row,'To:')
            arrears_row = t1\
                .find('span',class_='FirstColumnPrompt',string='Arrears Amt:')\
                .find_parent('tr')
            o.arrears_amount = self.value_first_column(arrears_row,'Arrears Amt:',money=True)
            o.arrears_frequency = self.value_column(arrears_row,'Freq:')
            o.arrears_to = self.value_column(arrears_row,'To:')
            mapr_row = t1\
                .find('span',class_='FirstColumnPrompt',string='MAPR Amt:')\
                .find_parent('tr')
            o.mapr_amount = self.value_first_column(mapr_row,'MAPR Amt:',money=True)
            o.mapr_frequency = self.value_column(mapr_row,'Freq:')
            o.medical_insurance_report_date_str = self.value_first_column(t1,'Medical Insurance Report Date:')
            btr_row = t1\
                .find('span',class_='FirstColumnPrompt',string='BTR Amt:')\
                .find_parent('tr')
            o.btr_amount = self.value_first_column(btr_row,'BTR Amt:',money=True)
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
            j = KJudgment(case_number=self.case_number)
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
            db.flush()

            against_prompt = t1.find('span',class_='FirstColumnPrompt',string='Judgment Against:')
            self.mark_for_deletion(against_prompt)
            t2 = against_prompt.find_parent('td').find_next_sibling('td').find('table')
            for value in t2.find_all('span',class_='Value'):
                if value.string:
                    self.mark_for_deletion(value)
                    j_against = KJudgmentAgainst(case_number=self.case_number)
                    j_against.judgment_id = j.id
                    j_against.name = self.format_value(value.string).rstrip(',')
                    db.add(j_against)

            in_favor_prompt = t1.find('span',class_='FirstColumnPrompt',string='Judgment in Favor of:')
            self.mark_for_deletion(in_favor_prompt)
            t2 = in_favor_prompt.find_parent('td').find_next_sibling('td').find('table')
            for value in t2.find_all('span',class_='Value'):
                if value.string:
                    self.mark_for_deletion(value)
                    j_in_favor = KJudgmentInFavor(case_number=self.case_number)
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
                m = KJudgmentModification(case_number=self.case_number)
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
                m.comments = self.value_first_column(t2,'Comments:',ignore_missing=True)
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

            d = KDocument(case_number=self.case_number)
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

    #########################################################
    # CHARGE AND DISPOSITION INFORMATION
    #########################################################
    @consumer
    def charge_and_disposition(self, db, soup):
        try:
            section_header = self.second_level_header(soup,'Charge and Disposition Information')
        except ParserError:
            return
        info_charge_statement = self.info_charge_statement(section_header)

        prev_obj = info_charge_statement
        new_charges = []
        while True:
            try:
                charge_section = self.immediate_sibling(prev_obj,'div',class_='AltBodyWindow1')
                separator = self.immediate_sibling(charge_section,'hr')
                prev_obj = separator
            except ParserError:
                break
            new_charge = self.parse_charge(charge_section)
            new_charges.append(new_charge)

        for new_charge in new_charges:
            db.add(new_charge)
        new_charge_numbers = [c.charge_number for c in new_charges]
        self.find_charges(db, new_charge_numbers)

    def parse_charge(self, container):
        charge = KCharge(case_number=self.case_number)
        charge_table_1 = self.table_first_columm_prompt(container,'Charge No:')
        charge.charge_number = int(self.value_first_column(charge_table_1,'Charge No:'))
        charge.statute_code = self.value_column(charge_table_1,'Statute Code:')
        charge.cjis_code = self.value_column(charge_table_1,'CJIS Code:')

        charge_table_2 = self.table_next_first_column_prompt(charge_table_1,'Charge Description:')
        charge.charge_description = self.value_first_column(charge_table_2,'Charge Description:') # TODO see if this is always same as charge_description

        charge_table_3 = self.table_next_first_column_prompt(charge_table_2,'Offense Date From:')
        charge.offense_date_from_str = self.value_first_column(charge_table_3,'Offense Date From:')
        charge.offense_date_to_str = self.value_column(charge_table_3,'To:')
        charge.arrest_tracking_number = self.value_first_column(charge_table_3,'Arrest Tracking No:')
        charge.citation = self.value_column(charge_table_3,'Citation:')
        charge.charge_amend_number = self.value_first_column(charge_table_3,'Charge Amend No:')
        charge.sentence_version = self.value_column(charge_table_3,'Sentence Version:')
        charge.charge_class = self.value_column(charge_table_3,'Charge Class:')

        try:
            disposition_header = self.fifth_level_header(container,'Disposition')
        except ParserError:
            pass
        else:
            disposition_table = self.table_next_first_column_prompt(disposition_header,'Plea:')
            charge.plea = self.value_first_column(disposition_table,'Plea:')
            charge.plea_date_str = self.value_column(disposition_table,'Plea Date:')
            charge.disposition = self.value_first_column(disposition_table,'Disposition:')
            charge.disposition_date_str = self.value_combined_first_column(disposition_table,'Disposition Date:')
            charge.disposition_merged_text = self.value_first_column(disposition_table,'Merged Text:',ignore_missing=True)

        try:
            jail_header = self.fifth_level_header(container,'Jail')
        except ParserError:
            pass
        else:
            jail_table = self.table_next_first_column_prompt(jail_header,'Life/Death:')
            charge.jail_life = self.value_first_column(jail_table,'Life/Death:')
            jail_row = self.row_first_label(jail_table,'Jail Term:')
            charge.jail_years = self.value_column(jail_row,'Yrs:')
            charge.jail_months = self.value_column(jail_row,'Mos:')
            charge.jail_days = self.value_column(jail_row,'Days:')
            charge.jail_hours = self.value_column(jail_row,'Hours:')
            suspended_row = self.row_first_label(jail_table,'Suspended Term:')
            charge.jail_suspended_years = self.value_column(suspended_row,'Yrs:')
            charge.jail_suspended_months = self.value_column(suspended_row,'Mos:')
            charge.jail_suspended_days = self.value_column(suspended_row,'Days:')
            charge.jail_suspended_hours = self.value_column(suspended_row,'Hours:')
            unsuspended_row = self.row_first_label(jail_table,'UnSuspended Term:')
            charge.jail_unsuspended_years = self.value_column(unsuspended_row,'Yrs:')
            charge.jail_unsuspended_months = self.value_column(unsuspended_row,'Mos:')
            charge.jail_unsuspended_days = self.value_column(unsuspended_row,'Days:')
            charge.jail_unsuspended_hours = self.value_column(unsuspended_row,'Hours:')
            charge.jail_text = self.value_first_column(jail_table,'Jail  Text:',ignore_missing=True)

        try:
            probation_header = self.fifth_level_header(container,'Probation')
        except ParserError:
            pass
        else:
            probation_table = self.table_next_first_column_prompt(probation_header,'Probation:')
            probation_row = self.row_first_label(probation_table,'Probation:')
            charge.probation_years = self.value_column(probation_row,'Yrs:')
            charge.probation_months = self.value_column(probation_row,'Mos:')
            charge.probation_days = self.value_column(probation_row,'Days:')
            charge.probation_hours = self.value_column(probation_row,'Hours:')
            supervised_row = self.row_first_label(probation_table,'Supervised :')
            charge.probation_supervised_years = self.value_column(supervised_row,'Yrs:')
            charge.probation_supervised_months = self.value_column(supervised_row,'Mos:')
            charge.probation_supervised_days = self.value_column(supervised_row,'Days:')
            charge.probation_supervised_hours = self.value_column(supervised_row,'Hours:')
            unsupervised_row = self.row_first_label(probation_table,'UnSupervised :')
            charge.probation_unsupervised_years = self.value_column(unsupervised_row,'Yrs:')
            charge.probation_unsupervised_months = self.value_column(unsupervised_row,'Mos:')
            charge.probation_unsupervised_days = self.value_column(unsupervised_row,'Days:')
            charge.probation_unsupervised_hours = self.value_column(unsupervised_row,'Hours:')
            charge.probation_text = self.value_first_column(probation_table,'Probation Text:',ignore_missing=True)
        
        try:
            fine_header = self.fifth_level_header(container,'Fine')
        except ParserError:
            pass
        else:
            fine_table = self.table_next_first_column_prompt(fine_header,'Fine Amt:')
            charge.fine_amount = self.value_first_column(fine_table,'Fine Amt:')
            charge.fine_suspended_amount = self.value_column(fine_table,'Fine Suspended Amt:')
            charge.fine_due = self.value_column(fine_table,'Fine Due:')
            charge.fine_first_payment_due = self.value_column(fine_table,'First Pmt Due:')
        
        try:
            cws_header = self.fifth_level_header(container,'Community Work Service')
        except ParserError:
            pass
        else:
            cws_table = self.table_next_first_column_prompt(cws_header,'Hours:')
            charge.community_work_service_hours = self.value_first_column(cws_table,'Hours:')
            charge.community_work_service_complete_by = self.value_column(cws_table,'Complete By:')
            charge.community_work_service_report_to = self.value_first_column(cws_table,'Report To:')
            charge.community_work_service_report_date = self.value_first_column(cws_table,'Report Date:')
        
        return charge

    #########################################################
    # SENTENCING NET TOTALS INFORMATION
    #########################################################
    @consumer
    def sentencing_net_totals(self, db, soup):
        try:
            section_header = self.first_level_header(soup,'Sentencing Net Totals')
        except ParserError:
            return
        section = self.immediate_sibling(section_header,'div',class_='AltBodyWindow1')
        snt = KSentencingNetTools(case_number=self.case_number)

        serve_time_row = self.row_first_label(section,'Serve Time:')
        snt.serve_time_years = self.value_column(serve_time_row,'Yrs:')
        snt.serve_time_months = self.value_column(serve_time_row,'Mos:')
        snt.serve_time_days = self.value_column(serve_time_row,'Days:')
        snt.serve_time_hours = self.value_column(serve_time_row,'Hours:')

        probation_row = self.row_first_label(section,'Probation :')
        snt.probation_years = self.value_column(probation_row,'Yrs:')
        snt.probation_months = self.value_column(probation_row,'Mos:')
        snt.probation_days = self.value_column(probation_row,'Days:')
        snt.probation_hours = self.value_column(probation_row,'Hours:')

        snt.fine_amount = self.value_first_column(section,'Fine Amount:')
        snt.fine_due_date_str = self.value_column(section,'Fine Due Date:')
        snt.cws_hours = self.value_column(section,'CWS Hours:')
        snt.credit_time_served = self.value_column(section,'Credit Time Served:')

        db.add(snt)