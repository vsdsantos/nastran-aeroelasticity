import pandas as pd

import datetime

from f06.flutter import parse_flutter_page, FlutterF06Page
from f06.eigval import parse_realeigval_page, RealEigValF06Page, summarize_real_eigvals, ModalEffectiveMassFractionF06Page

PAGE_PARSING_FUNCTIONS = {
    'flutter': parse_flutter_page,
    'eigvalsummary': '',
    'realeigval': parse_realeigval_page,
    'ModalEffectiveMassFractionF06Page': ModalEffectiveMassFractionF06Page.parse_page,
    'text': lambda ls: '\n'.join(ls)
}

FLUTTER_CHECK_LINE = 3
FLUTTER_CHECK_STR = 'FLUTTER  SUMMARY'

EIGVALSUMMARY_CHECK_LINE = 6
EIGVALSUMMARY_CHECK_STR = 'E I G E N V A L U E  A N A L Y S I S   S U M M A R Y'

REALEIGVAL_CHECK_LINE = 4
REALEIGVAL_CHECK_STR = 'R E A L   E I G E N V A L U E S'


METADATA_DICT = {
    'TOTAL PAGES: ': lambda res: len(res.pages),
    'HAS EIGVAL RESULTS: ': lambda res: len(res.eigval) > 0,
    'HAS FLUTTER RESULTS: ': lambda res: len(res.eigval) > 0,
    'F06 EXPORTED AT ': lambda res: datetime.datetime.now(),
}

class F06Results:

    def __init__(self, pages=None):
        self.pages = pages

    def __repr__(self):
        return 'F06 Results with {} pages.'.format(len(self.pages))

    @property
    def flutter(self):
        return list(filter(lambda p: isinstance(p, FlutterF06Page), self.pages))
    
    @property
    def eigval(self):
        return list(filter(lambda p: isinstance(p, RealEigValF06Page), self.pages))
    
    @property
    def modalmassfrac(self):
        return list(filter(lambda p: isinstance(p, ModalEffectiveMassFractionF06Page), self.pages))
    
    @property
    def nottext(self):
        return list(filter(lambda p: not isinstance(p, str), self.pages))
    
    def to_excel(self, filename: str):
        with pd.ExcelWriter(filename, engine='openpyxl') as writer:
            wb = writer.book
            ws_meta = wb.create_sheet('META')
            
            i = 1
            for k, v in METADATA_DICT.items():
                ws_meta.cell(i, 1).value = k
                ws_meta.cell(i, 2).value = v(self)
                i += 1
            ws_meta.cell(i, 1).value = 'CREDITS: @vsdsantos'
            
            if len(self.eigval) > 0:
                summarize_real_eigvals(self).to_excel(writer, sheet_name='EIGVAL SUMMARY')
            
            # if len(self.flutter) > 0:
                # summarize_real_eigvals(self.flutter).to_excel(writer, sheet_name='FLUTTER SUMMARY')
    
def read_f06(filename: str):
    with open(filename, 'r') as file:
        raw_lines = file.readlines()

    groups = _group_lines_by_page(raw_lines)

    pages = []

    for lines in groups:
        # TODO: Check Page Type and automatically send to function
        T = _check_page_type(lines, T)
        pages.append(PAGE_PARSING_FUNCTIONS[T](lines, ))

    return F06Results(pages)


def _check_page_type(lines, previous_page_type=None):
    if len(lines)-1 >= FLUTTER_CHECK_LINE and FLUTTER_CHECK_STR in lines[FLUTTER_CHECK_LINE]:
        return 'flutter'
    elif len(lines)-1 >= EIGVALSUMMARY_CHECK_LINE and EIGVALSUMMARY_CHECK_STR in lines[EIGVALSUMMARY_CHECK_LINE]:
        return 'text' # TODO: add support for the eigenval summary data
    elif len(lines)-1 >= REALEIGVAL_CHECK_LINE and REALEIGVAL_CHECK_STR in lines[REALEIGVAL_CHECK_LINE]:
        return 'realeigval'
    elif ModalEffectiveMassFractionF06Page.is_page_of_this_type(lines, previous_page_type):
        return 'ModalEffectiveMassFractionF06Page'
    else:
        return 'text'


def _group_lines_by_page(lines):
    groups = []
    group = []
    for i, line in enumerate(lines):
        if line[0] == '1' and len(group) > 0:
            groups.append(group)
            group = []
        group.append(line)
    return groups
