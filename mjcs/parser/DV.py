from ..models import DV, DVDefendant, DVHearing, DVEvent, DVDefendantAttorney
from .base import CaseDetailsParser, consumer, ParserError
import re

class DVParser(CaseDetailsParser):
    inactive_statuses = [
        'COMPLETE',
        'CLOSED'
    ]

    def header(self, soup):
        header = soup.find('div',class_='Header')
        header.decompose()
        subheader = soup.find('div',class_='Subheader')
        if not subheader:
            raise ParserError('Missing subheader')
        subheader.decompose()
        goback = soup.find('a',string='Go Back Now')
        if not goback:
            goback = soup.find('a',string='Go Back')
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
        t1 = self.table_first_columm_prompt(soup,'Court System:')

        case = DV(case_number=self.case_number)
        case.court_system = self.value_combined_first_column(t1,'Court System:',remove_newlines=True)
        case_number = self.value_combined_first_column(t1,'Case Number:')
        if case_number.replace('-','') != self.case_number:
            raise ParserError('Case number "%s" in case details page does not match given: %s' % (case_number, self.case_number))
        case.case_status = self.value_column(t1,'Case Status:')
        self.case_status = case.case_status
        case.case_type = self.value_combined_first_column(t1,'Case Type:')
        case.order_valid_thru_str = self.value_column(t1,'Order Valid Thru:',ignore_missing=True)
        case.filing_date_str = self.value_combined_first_column(t1,'Filing Date:')
        db.add(case)
        db.flush()
    
    #########################################################
    # DEFENDENT INFORMATION
    #########################################################
    @consumer
    def defendant(self, db, soup):
        try:
            t1 = self.table_first_columm_prompt(soup,'Defendant Name:')
        except ParserError:
            return
        defendant = DVDefendant(case_number=self.case_number)
        defendant.name = self.value_combined_first_column(t1,'Defendant Name:')
        defendant.city = self.value_combined_first_column(t1,'City:',ignore_missing=True)
        defendant.state = self.value_column(t1,'State:',ignore_missing=True)
        defendant.DOB_str = self.value_column(t1,'DOB:',ignore_missing=True)
        db.add(defendant)

        for span in soup.find_all('span',class_='FirstColumnPrompt',string='Defendant Attorney:'):
            row = span.find_parent('tr')
            attorney = DVDefendantAttorney(case_number=self.case_number)
            attorney.name = self.value_combined_first_column(row,'Defendant Attorney:')
            db.add(attorney)
    
    #########################################################
    # HEARINGS
    #########################################################
    @consumer
    def hearings(self, db, soup):
        for span in soup.find_all('span',class_='FirstColumnPrompt',string='Hearing Date:'):
            t = span.find_parent('table')
            hearing = DVHearing(case_number=self.case_number)
            hearing.hearing_date_str = self.value_first_column(t,'Hearing Date:')
            hearing.hearing_time_str = self.value_column(t,'Hearing Time:')
            hearing.room = self.value_column(t,'Room:',ignore_missing=True)
            hearing.location = self.value_first_column(t,'Hearing Location:')
            hearing.served_date_str = self.value_first_column(t,'Served Date:',ignore_missing=True)
            hearing.hearing_type = self.value_first_column(t,'Hearing Type:',ignore_missing=True)
            result_span = t.find('span',class_='FirstColumnPrompt',string='Result:')
            if result_span:
                result_val_span = result_span.find_parent('td')\
                    .find_next_sibling('td')\
                    .find('span',class_='Value')
                hearing.result = "\n".join(result_val_span.stripped_strings)
                self.mark_for_deletion(result_span)
                self.mark_for_deletion(result_val_span)
            db.add(hearing)
    
    #########################################################
    # OTHER EVENTS
    #########################################################
    @consumer
    def other_events(self, db, soup):
        section_header = soup.find('h4',string='Other Events')
        if not section_header:
            return
        self.mark_for_deletion(section_header)
        
        prev_obj = section_header
        while True:
            try:
                t1 = self.table_next_first_column_prompt(prev_obj,'Date:')
            except ParserError:
                break
            prev_obj = t1
            event = DVEvent(case_number=self.case_number)
            event.event_date_str = self.value_first_column(t1,'Date:')
            event.description = self.value_first_column(t1,'Description:')
            db.add(event)