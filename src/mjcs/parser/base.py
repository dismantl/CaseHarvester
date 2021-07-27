from abc import ABC, abstractmethod
from bs4 import BeautifulSoup, SoupStrainer
from ..util import db_session
from ..models import Case
from . import BaseParserError
import re
from sqlalchemy.sql import select, text
from datetime import datetime
import inspect

class ParserError(BaseParserError):
    def __init__(self, message, content=None):
        self.message = message
        self.content = content

class UnparsedDataError(BaseParserError):
    def __init__(self, message, content):
        self.message = message
        self.content = content

def consumer(func):
    func.consumer = True
    return func

class CaseDetailsParser(ABC):
    inactive_statuses = []

    def __init__(self, case_number, html):
        # <body> should only have a single child div that holds the data
        self.case_number = case_number
        strainer = SoupStrainer('div')
        self.soup = BeautifulSoup(html,'html.parser',parse_only=strainer)
        if len(self.soup.contents) != 1 or not self.soup.div:
            raise ParserError("Unexpected HTML format", self.soup)
        self.marked_for_deletion = []
        self.case_status = None
        self.allow_unparsed_data = self.allow_unparsed_data()

    def allow_unparsed_data(self):
        with db_session() as db:
            return db.execute(
                select(Case.allow_unparsed_data)\
                .where(Case.case_number == self.case_number)
            ).scalar()

    def parse(self):
        # All parsing is done within a single database transaction, so no partial data is added or destroyed
        with db_session() as db:
            self.header(self.soup)
            self.delete_previous(db)
            self.case(db, self.soup)
            db.flush() # so related subtables can satisfy foreign key constraint
            self.consume_all(db)
            self.footer(self.soup)
            self.finalize(db)

    def mark_for_deletion(self, obj):
        for marked in self.marked_for_deletion:
            if obj is marked:  # compare for identity, not equality (https://www.crummy.com/software/BeautifulSoup/bs4/doc/#comparing-objects-for-equality)
                return
        self.marked_for_deletion.append(obj)

    def consume_all(self, db):
        for attr in dir(self):
            f = getattr(self,attr)
            if hasattr(f,'consumer') and type(f) != BeautifulSoup:
                # print("Calling consumer %s for %s" % (f.__name__,self.case_number))
                f(db, self.soup) # this will call all @consumer methods in both sub and super classes

    def finalize(self, db):
        for obj in self.marked_for_deletion:
            obj.decompose()
        if list(self.soup.stripped_strings) and not self.allow_unparsed_data:
            raise UnparsedDataError("Data remaining in DOM after parsing:",list(self.soup.stripped_strings))
        # update last_parse in DB
        db.execute(
            Case.__table__.update()\
                .where(Case.case_number == self.case_number)\
                .values(last_parse = datetime.now(), active = self.is_active())
        )

    def is_active(self):
        if self.case_status and self.case_status not in self.inactive_statuses:
            return True
        return False

    @abstractmethod
    def header(self, soup):
        raise NotImplementedError

    @abstractmethod
    def footer(self, soup):
        raise NotImplementedError

    @abstractmethod
    def case(self, db, soup):
        raise NotImplementedError

    def delete_previous(self, db):
        # Disable foreign key on delete cascade triggers for performance
        db.execute(text('SET session_replication_role = replica'))
        for _, cls in inspect.getmembers(inspect.getmodule(self), lambda obj: hasattr(obj, '__tablename__')):
            db.execute(cls.__table__.delete()\
                .where(cls.case_number == self.case_number))
        db.execute(text('SET session_replication_role = DEFAULT'))

    def immediate_previous_sibling(self, next_sibling, *args, **kwargs):
        obj_prev = next_sibling.find_previous_sibling(True)
        if not obj_prev:
            raise ParserError('No previous siblings')
        obj_find = next_sibling.find_previous_sibling(*args, **kwargs)
        if obj_prev is not obj_find:
            raise ParserError(
                'Unexpected immediate previous sibling',
                obj_prev
            )
        return obj_prev

    def immediate_sibling(self, prev_sibling, *args, **kwargs):
        obj_next = prev_sibling.find_next_sibling(True)
        if not obj_next:
            raise ParserError('No subsequent siblings')
        obj_find = prev_sibling.find_next_sibling(*args, **kwargs)
        if obj_next is not obj_find:
            raise ParserError(
                'Unexpected immediate next sibling',
                obj_next
            )
        return obj_next

    def info_charge_statement(self, prev_sibling):
        try:
            div = self.immediate_sibling(prev_sibling,class_='InfoChargeStatement')
        except ParserError:
            raise ParserError('Unable to retrieve InfoChargeStatement')
        self.mark_for_deletion(div)
        return div

    def first_level_header(self, soup, header_name):
        try:
            table = soup\
                .find('h5',string=re.compile(header_name))\
                .find_parent('table')
        except AttributeError:
            raise ParserError('First level header "%s" not found' % header_name)
        if not table:
            raise ParserError('First level header "%s" not found' % header_name)
        self.mark_for_deletion(table)
        return table

    def second_level_header(self, soup, header_name):
        h5 = soup\
            .find('h5',string=re.compile(header_name))
        if not h5:
            raise ParserError('Second level header "%s" not found' % header_name)
        self.mark_for_deletion(h5)
        return h5

    def third_level_header(self, base, header_name):
        try:
            left = base\
                .find('i',string=re.compile(header_name))\
                .find_parent('h5')\
                .find_parent('left')
        except AttributeError:
            raise ParserError('Third level header "%s" not found' % header_name)
        if not left:
            raise ParserError('Third level header "%s" not found' % header_name)
        self.mark_for_deletion(left)
        return left

    def fourth_level_header(self, base, header_name):
        h6 = base\
            .find('h6',string=re.compile(header_name))
        if not h6:
            raise ParserError('Fourth level header "%s" not found' % header_name)
        self.mark_for_deletion(h6)
        return h6

    def table_next_first_column_prompt(self, prev_sibling, first_column_prompt):
        obj = self.immediate_sibling(prev_sibling,'table')
        try:
            self.table_first_columm_prompt(obj, first_column_prompt)
        except ParserError:
            raise ParserError(
                'Next table does not contain first column prompt %s' % first_column_prompt,
                obj
            )
        return obj

    def table_next_prompt(self, prev_sibling, prompt):
        obj = self.immediate_sibling(prev_sibling,'table')
        try:
            self.table_prompt(obj, prompt)
        except ParserError:
            raise ParserError(
                'Next table does not contain prompt %s' % prompt,
                obj
            )
        return obj

    def table_first_columm_prompt(self, base, first_column_prompt):
        if type(first_column_prompt) == list:
            first_column_prompt = [re.compile(p) for p in first_column_prompt]
        elif type(first_column_prompt) == str:
            first_column_prompt = re.compile(first_column_prompt)
        try:
            return base\
                .find('span',class_='FirstColumnPrompt',string=first_column_prompt)\
                .find_parent('table')
        except AttributeError:
            raise ParserError('Table with first column prompt "%s" not found' % first_column_prompt)

    def table_prompt(self, base, prompt):
        if type(prompt) == list:
            prompt = [re.compile(p) for p in prompt]
        elif type(prompt) == str:
            prompt = re.compile(prompt)
        try:
            return base\
                .find('span',class_='Prompt',string=prompt)\
                .find_parent('table')
        except AttributeError:
            raise ParserError('Table with prompt "%s" not found' % prompt)

    def row_first_label(self, base, first_column_prompt):
        prompt_span = base\
            .find('span',class_='FirstColumnPrompt',string=re.compile(first_column_prompt))
        if not prompt_span:
            raise ParserError('Row header "%s" not found' % first_column_prompt)
        self.mark_for_deletion(prompt_span)
        return prompt_span\
            .find_parent('tr')

    def row_label(self, base, prompt):
        prompt_span = base\
            .find('span',class_='Prompt',string=re.compile(prompt))
        if not prompt_span:
            raise ParserError('Row header "%s" not found' % prompt)
        self.mark_for_deletion(prompt_span)
        return prompt_span\
            .find_parent('tr')

    def row_first_columm_prompt(self, base, first_column_prompt):
        if type(first_column_prompt) == list:
            first_column_prompt = [re.compile(p) for p in first_column_prompt]
        elif type(first_column_prompt) == str:
            first_column_prompt = re.compile(first_column_prompt)
        try:
            return base\
                .find('span',class_='FirstColumnPrompt',string=first_column_prompt)\
                .find_parent('tr')
        except AttributeError:
            raise ParserError('Row with first column prompt "%s" not found' % first_column_prompt)

    def row_next_first_column_prompt(self, prev_sibling, first_column_prompt):
        obj = self.immediate_sibling(prev_sibling,'tr')
        try:
            self.row_first_columm_prompt(obj, first_column_prompt)
        except ParserError:
            raise ParserError(
                'Next row does not contain first column prompt %s' % first_column_prompt,
                obj
            )
        return obj

    def format_value(self,
            val,
            strip=True,
            remove_extra_spaces=True,
            remove_newlines=False,
            boolean_value=False,
            numeric=False,
            money=False):
        if boolean_value:
            return val and val.lower() != 'false' and val.lower() != 'no'
        if not val:
            return None
        if strip:
            val = val.strip()
        if remove_extra_spaces:
            val = re.sub('[ \t]+',' ',val)
        if remove_newlines:
            val = val.replace('\n','')
        if numeric or money:
            val = val.replace(',','')
        if money:
            val = val.replace('$','')
        return val

    def value_first_column(self, base, first_column_prompt, ignore_missing=False, **format_args):
        prompt_span = base\
            .find('span',class_='FirstColumnPrompt',string=re.compile(first_column_prompt))
        if not prompt_span:
            if ignore_missing:
                return None
            raise ParserError('Unable to find first column prompt %s' % first_column_prompt)
        self.mark_for_deletion(prompt_span)
        value_span = prompt_span\
            .find_parent('td')\
            .find_next_sibling('td')\
            .find('span',class_='Value')
        if value_span:
            self.mark_for_deletion(value_span)
            return self.format_value(value_span.string, **format_args)
        return None

    def value_combined_first_column(self, base, first_column_prompt, ignore_missing=False, **format_args):
        prompt_span = base\
            .find('span',class_='FirstColumnPrompt',string=re.compile(first_column_prompt))
        if not prompt_span:
            if ignore_missing:
                return None
            raise ParserError('Unable to find combined first column prompt %s' % first_column_prompt)
        self.mark_for_deletion(prompt_span)
        value_span = prompt_span\
            .find_next_sibling('span',class_='Value')
        if value_span:
            self.mark_for_deletion(value_span)
            return self.format_value(value_span.string, **format_args)
        return None

    def value_column(self, base, prompt, ignore_missing=False, **format_args):
        prompt_span = base\
            .find('span',class_='Prompt',string=re.compile(prompt))
        if not prompt_span:
            if ignore_missing:
                return None
            raise ParserError('Unable to find column prompt %s' % prompt)
        self.mark_for_deletion(prompt_span)
        value_span = prompt_span\
            .find_next_sibling('span',class_='Value')
        if value_span:
            self.mark_for_deletion(value_span)
            return self.format_value(value_span.string, **format_args)
        return None

    def value_multi_column(self, base, prompt, ignore_missing=False, **format_args):
        prompt_span = base\
            .find('span',class_='Prompt',string=re.compile(prompt))
        if not prompt_span:
            if ignore_missing:
                return None
            raise ParserError('Unable to find column prompt %s' % prompt)
        self.mark_for_deletion(prompt_span)
        value_span = prompt_span\
            .find_parent('td')\
            .find_next_sibling('td')\
            .find('span',class_='Value')
        if value_span:
            self.mark_for_deletion(value_span)
            return self.format_value(value_span.string, **format_args)
        return None

    def value_multi_column_table(self, base, prompt, ignore_missing=False, **format_args):
        prompt_span = base\
            .find('span',class_='Prompt',string=re.compile(prompt))
        if not prompt_span:
            if ignore_missing:
                return None
            raise ParserError('Unable to find column prompt %s' % prompt)
        self.mark_for_deletion(prompt_span)
        value_table = prompt_span\
            .find_parent('td')\
            .find_next_sibling('td')\
            .find('table')
        if value_table:
            value_strings = list(value_table.stripped_strings)
            if len(value_strings) > 1:
                raise ParserError(f'Invalid table value {value_table}')
            self.mark_for_deletion(value_table)
            if value_strings:
                return self.format_value(value_strings[0], **format_args)
        return None
    
    def value_first_column_table(self, base, prompt, ignore_missing=False, **format_args):
        prompt_span = base\
            .find('span',class_='FirstColumnPrompt',string=re.compile(prompt))
        if not prompt_span:
            if ignore_missing:
                return None
            raise ParserError('Unable to find first column prompt %s' % prompt)
        self.mark_for_deletion(prompt_span)
        value_table = prompt_span\
            .find_parent('td')\
            .find_next_sibling('td')\
            .find('table')
        if value_table:
            value_strings = list(value_table.stripped_strings)
            if len(value_strings) > 1:
                raise ParserError(f'Invalid table value {value_table}')
            self.mark_for_deletion(value_table)
            if value_strings:
                return self.format_value(value_strings[0], **format_args)
        return None