from .config import config
from .db import TableBase, column_windows, db_session
from sqlalchemy import Column, Boolean, Date, Integer, String, DateTime
from sqlalchemy.sql import select
import zlib
import concurrent.futures

def total_cases(db):
    return db.query(Case).count()

def cases_batch_filter(db, filter=None, batch_size=None):
    if not batch_size:
        batch_size = config.CASE_BATCH_SIZE
    for whereclause in column_windows(db, Case.case_number, batch_size, filter=filter):
        yield whereclause

def cases_batch(db, batch_filter):
    return db.query(Case).filter(batch_filter)

class Case(TableBase):
    __tablename__ = 'cases'

    case_number = Column(String, primary_key=True)
    court = Column(String)
    query_court = Column(String, nullable=True)
    case_type = Column(String, nullable=True)
    filing_date = Column(Date, nullable=True)
    filing_date_original = Column(String, nullable=True)
    status = Column(String, nullable=True)
    caption = Column(String, nullable=True)
    loc = Column(Integer)
    detail_loc = Column(String)
    url = Column(String)
    last_scrape = Column(DateTime, nullable=True)
    last_parse = Column(DateTime, nullable=True)
    scrape_exempt = Column(Boolean, default=False)
    parse_exempt = Column(Boolean, default=False)

    def dict(self):
        return {
            'case_number': self.case_number,
            'court': self.court,
            'query_court': self.query_court,
            'case_type': self.case_type,
            'filing_date': self.filing_date,
            'filing_date_original': self.filing_date_original,
            'status': self.status,
            'caption': self.caption,
            'loc': self.loc,
            'detail_loc': self.detail_loc,
            'url': self.url
        }

def get_detail_loc(case_number):
    with db_session() as db:
        detail_loc = db.execute(
                select([Case.detail_loc])\
                .where(Case.case_number == case_number)
            ).scalar()
    return detail_loc

def process_cases(func, cases, on_success=None, on_error=None, threads=1, counter=None):
    to_process = [_ for _ in cases]
    continue_processing = True
    caught_exception = None
    while to_process and continue_processing:
        if threads == 1:
            for case in to_process:
                case_number = case['case_number'] if type(case) == dict else case
                if counter:
                    print('Processing case %s (%s of %s)' % (case_number,counter['count'],counter['total']))
                    counter['count'] += 1
                try:
                    func(case)
                # except NotImplementedError:
                #     pass
                except Exception as e:
                    continue_processing = False
                    print(type(e))
                    print(str(e))
                    print("!!! Failed to process %s !!!" % case_number)
                    if on_error:
                        action = on_error(e, case)
                        if action == 'delete':
                            to_process.remove(case)
                        if action == 'continue' or action == 'delete':
                            continue_processing = True
                    else:
                        caught_exception = e
                    break
                else:
                    if on_success:
                        on_success(case)
                    to_process.remove(case)
        else:
            with concurrent.futures.ThreadPoolExecutor(max_workers=threads) as executor:
                future_to_case = {}
                for case in to_process:
                    future_to_case[executor.submit(func, case)] = case
                for future in concurrent.futures.as_completed(future_to_case):
                    case = future_to_case[future]
                    case_number = case['case_number'] if type(case) == dict else case
                    try:
                        future.result()
                    except concurrent.futures.CancelledError:
                        pass
                    except Exception as e: # Won't catch KeyboardInterrupt, which is raised in as_completed
                        continue_processing = False
                        # cancel all remaining tasks
                        for future in future_to_case:
                            future.cancel()
                        print(type(e))
                        print(str(e))
                        print("!!! Failed to process %s !!!" % case_number)
                        if on_error:
                            action = on_error(e, case)
                            if action == 'delete':
                                to_process.remove(case)
                            if action == 'continue' or action == 'delete':
                                continue_processing = True
                            if counter:
                                counter['count'] += 1
                                print('Processed case %s (%s of %s)' % (case_number,counter['count'],counter['total']))
                        else:
                            caught_exception = e
                    else:
                        if on_success:
                            on_success(case)
                        to_process.remove(case)
                        if counter:
                            counter['count'] += 1
                            print('Processed case %s (%s of %s)' % (case_number,counter['count'],counter['total']))
        if caught_exception:
            raise caught_exception
