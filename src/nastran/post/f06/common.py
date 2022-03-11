from pandas.core.frame import DataFrame

import pandas as pd
import numpy as np
import re
import calendar
import datetime
import time

SKIP_LINE_SET = {"*** USER INFORMATION MESSAGE", "A ZERO FREQUENCY"}

p_header = re.compile(r"(?P<label>.+(?=SUBCASE))(?P<subcase>SUBCASE\s\d+)")

re_date = re.compile(r'(?P<month>\w+)\s+(?P<day>\d{1,2}),\s+(?P<year>\d{4})')
re_version = re.compile(r'(?P<vname>[^\d]*)(?P<vdate>\d{1,2}\/\d{1,2}\/\d{1,2})')
re_page = re.compile(r'PAGE\s+(?P<page>\d+)$')

class F06Page:

    def __init__(self, raw_lines=None, meta=None):
        self.raw_lines = raw_lines
        self.meta = {} if meta == None else meta
        self.parse_page_metadata_header()
    
    def parse_page_metadata_header(self):
        first_line = self.raw_lines[0]
        
        date = re_date.search(first_line)
        self.meta['run-date'] = datetime.date(
            int(date.group('year').strip()),
            list(calendar.month_name).index(date.group('month').strip().title()),
            int(date.group('day').strip())
        )
        
        version = re_version.search(first_line)
        self.meta['run-version-name'] = version.group('vname').strip()
        self.meta['run-version-date'] = datetime.date(
            *time.strptime(
                version.group('vdate').strip(),
                '%m/%d/%y')[:3]
        )
        
        self.meta['page'] = int(re_page.search(first_line).group('page'))
    

    
def find_tabular_line_range(lines, shift):
    k = len(lines)
    j = shift # linha após as labels de dados
    while j < k: # primeiro char na linha final da pagina é 1
        l = lines[j]
        if _check_skip_lines(l) or l.strip() == '':
            break
        j += 1
    return (shift, j)        
        
def extract_tabulated_data(lines):
    data = []
    for line in lines:
        entries = line.split()
        inner_data = []
        for entry in entries:
            try:
                e = float(entry)
            except ValueError:
                e = np.nan
            finally:
                inner_data.append(e)
        data.append(inner_data)
    return data


def parse_label_subcase(line):
    res = p_header.search(line[1:])
    label = res.group('label').strip()
    subcase = res.group('subcase').replace('SUBCASE', '').strip()
    return (label, int(subcase))


def parse_text_value(value):
    try:
        return int(value)
    except ValueError:
        try:
            return float(value)
        except ValueError:
            return value

def _check_skip_lines(line):
    return any(map(lambda k: k in line, SKIP_LINE_SET))

# def read_and_concat_f06s(case_files, labels, label_name="THETA"):
#
#     if len(labels) != len(case_files):
#         raise Exception("Collections should be of same size.")
#
#     df_results = []
#
#     for i, fn in enumerate(case_files):
#         print("Reading... {}".format(fn))
#         df_data = read_f06(fn)
#         df_results.append(
#             pd.concat(
#                 { labels[i]: df_data },
#                 names=[label_name]
#             )
#         )
#
#     return pd.concat(df_results)
