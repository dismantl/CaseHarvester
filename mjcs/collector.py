from .models import Case
from .util import db_session, send_to_queue
from .config import config
from pypdf import PdfReader
from datetime import datetime
from sqlalchemy import select
import json
import re
import io
import requests
import logging

MDEC_URL = 'https://mdcourts.gov/data/case'
BALT_URL = 'https://mdcourts.gov/data/nonmdec/bccases'

logger = logging.getLogger('mjcs')
invalid_court_patterns = [
    r'^$',
    r'^Page:$',
    r'^\d+$',
]
invalid_case_number_patterns = [
    r'^$',
    r'^Page:$',
    r'^\d+$',
    r'^Charges:$',
    r'^Case Number$',
]

mdec_first_column_x = 17.28
mdec_third_column_x = 358.848
mdec_fourth_column_x = 523.08
mdec_header_row_y = 235
mdec_court_row_y = 252
mdec_date_format = '%m/%d/%Y'

bc_first_column_x = 90.3
bc_third_column_x = 341.34
bc_fourth_column_x = 425.02
bc_header_row_y = 781
bc_court_row_y = 796
bc_date_format = '%m-%d-%Y'


class TextItem:
    def __init__(self, text, x, y, font_dict, font_size):
        self.text = text.strip()
        self.x = x
        self.y = y
        self.font_dict = font_dict
        self.font_size = font_size


class Collector:
    def __init__(self, url, case_number_x, case_type_x, filing_date_x, header_row_y, court_row_y, date_format):
        self.url = url
        self.case_number_x = case_number_x
        self.case_type_x = case_type_x
        self.filing_date_x = filing_date_x
        self.header_row_y = header_row_y
        self.court_row_y = court_row_y
        self.date_format = date_format
        self.current_court = None
        self.current_case = None
        self.cases = {}

    def collect_case_numbers(self, target_date=None):
        target_date = target_date or datetime.now().date()
        response = requests.get(f'{self.url}/file{target_date.strftime("%Y-%m-%d")}.pdf')
        pdfio = io.BytesIO(response.content)
        reader = PdfReader(pdfio)
        with db_session() as db:
            for i, page in enumerate(reader.pages):
                logger.info(f'Parsing page {i+1}')
                page.extract_text(visitor_text = self.parse_pdf_text)
            logger.info(f'Found {len(self.cases)} case numbers, submitting to database')

            # See which cases need to be added to DB
            existing_cases = db.scalars(
                select(Case.case_number)
                .where(Case.case_number.in_(self.cases.keys()))
            ).all()
            new_case_numbers = set(self.cases.keys()) - set(existing_cases)
            new_cases = [self.cases[x] for x in new_case_numbers]

            # Save new cases to database
            db.add_all(new_cases)

            # Then send them to the scraper queue
            messages = [json.dumps({'case_number': case_number}) for case_number in self.cases.keys()]
            send_to_queue(config.scraper_queue, messages)

    def parse_pdf_text(self, text, cm, tm, font_dict, font_size):
        if not text.strip():
            return True
        
        x = tm[4]
        y = tm[5]
        item = TextItem(text, x, y, font_dict, font_size)

        if self.text_is_court(item) and self.current_court != item.text:
            self.current_court = item.text
        elif self.text_is_case_number(item) and not self.current_case:
            self.current_case = Case(case_number=item.text.replace('-',''), court=self.current_court)
        elif self.text_is_case_type(item) and self.current_case:
            self.current_case.case_type = item.text
        elif self.text_is_filing_date(item) and self.current_case:
            self.current_case.filing_date = datetime.strptime(item.text, self.date_format)
            self.cases[self.current_case.case_number] = self.current_case
            self.current_case = None

    def text_is_court(self, item):
        return self.text_is_court_row(item) and self.text_is_case_number_column(item) and self.text_is_not_invalid(item, invalid_court_patterns)

    def text_is_case_number(self, item):
        return not self.text_is_header(item) and self.text_is_case_number_column(item) and self.text_is_not_invalid(item, invalid_case_number_patterns)

    def text_is_case_type(self, item):
        return not self.text_is_header(item) and self.text_is_case_type_column(item)

    def text_is_filing_date(self, item):
        return not self.text_is_header(item) and self.text_is_filing_date_column(item)

    def text_is_case_number_column(self, item):
        return item.x <= self.case_number_x
    
    def text_is_case_type_column(self, item):
        return item.x == self.case_type_x
    
    def text_is_filing_date_column(self, item):
        return item.x == self.filing_date_x

    def text_is_header(self, item):
        return (self.text_is_court_row(item) or self.text_is_header_row(item)) and self.font_is_bold(item)

    def text_is_court_row(self, item):
        return round(item.y) == self.court_row_y

    def text_is_header_row(self, item):
        return round(item.y) == self.header_row_y

    def font_is_bold(self, item):
        if item.font_dict is not None:
            return item.font_dict['/BaseFont'] == '/Times-Bold'
        return False

    def text_is_not_invalid(self, item, invalid_patterns):
        for pattern in invalid_patterns:
            matches = re.search(pattern, item.text or '', re.IGNORECASE)
            if matches is not None:
                return False
        return True


class MDECCollector(Collector):
    def __init__(self):
        super(MDECCollector, self).__init__(
            MDEC_URL,
            mdec_first_column_x,
            mdec_third_column_x,
            mdec_fourth_column_x,
            mdec_header_row_y,
            mdec_court_row_y,
            mdec_date_format
        )


class BaltCityCollector(Collector):
    def __init__(self):
        super(BaltCityCollector, self).__init__(
            BALT_URL,
            bc_first_column_x,
            bc_third_column_x,
            bc_fourth_column_x,
            bc_header_row_y,
            bc_court_row_y,
            bc_date_format
        )