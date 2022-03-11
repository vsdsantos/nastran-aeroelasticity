import pandas as pd
import numpy as np

from f06.common import extract_tabulated_data, parse_text_value, find_tabular_line_range, parse_label_subcase, F06Page

REALIGVAL_SUBCASE_LINE = 2
REALIGVAL_TABULAR_LINE = 7
REALEIGVAL_CHECK_AUGMENTATION_LINE = 5
REALEIGVAL_CHECK_AUGMENTATION_STR = 'AUGMENTATION OF RESIDUAL VECTORS'

REALIGVAL_KEYS = {
    'MODE': 'Mode No.',
    'EXTRACTIONORDER': 'Mode Extraction Order',
    'EIGENVALUE': 'Real Eigenvalue',
    'RADIANS': 'Frequency in Radians',
    'CYCLES': 'Frequency in Hz',
    'GENERALIZEDMASS': 'Generalized Mass',
    'GENERALIZEDSTIFF': 'Generalized Stiffness',
}

class RealEigValF06Page(F06Page):
    def __init__(self, df=None, info=None, raw_lines=None, meta=None):
        super().__init__(raw_lines, meta)
        self.df = df
        self.info = {} if info == None else info

    def __repr__(self):
        return self.__str__()

    def __str__(self):
        return 'REAL EIGVAL F06\tSUBCASE {}\tPAGE {}'.format(self.info['SUBCASE'], self.meta['page'])

def parse_realeigval_page(lines):
    
    a, b = find_tabular_line_range(lines, REALIGVAL_TABULAR_LINE)
    
    if REALEIGVAL_CHECK_AUGMENTATION_STR in lines[REALEIGVAL_CHECK_AUGMENTATION_LINE]:
        a += 1
     
    parsed_data = extract_tabulated_data(lines[a:b])

    df = pd.DataFrame(parsed_data, columns=list(REALIGVAL_KEYS.keys()))
    
    info = {}
    label, subcase = parse_label_subcase(lines[REALIGVAL_SUBCASE_LINE])
    info['LABEL'] = label
    info['SUBCASE'] = subcase
    
    return RealEigValF06Page(df, info, lines)

def summarize_real_eigvals(results, key='CYCLES'):
    vals = list(map(lambda p: (p.info['SUBCASE'], p.df[key]), results.eigval))
    df = pd.DataFrame(vals, columns=('SUBCASE', key)).set_index('SUBCASE')[key].apply(pd.Series)
    df = df.rename(columns = lambda x: x+1)
    df = df.groupby('SUBCASE').last()
    return df

## Modal Effective Mass Fraction Results


MODALMASSFRAC_LINE = 4
MODALMASSFRAC_STR = 'MODAL EFFECTIVE MASS FRACTION'

MODALMASSFRAC_SUBCASE_LINE = 2
MODALMASSFRAC_TABULAR_LINE = 10
MODALMASSFRAC_CHECK_TRANSLATION_LINE = 5
MODALMASSFRAC_CHECK_TRANSLATION_STR = 'FOR TRANSLATIONAL DEGREES OF FREEDOM'

MODALMASSFRAC_TRANSLATION_KEYS = {
    'MODE': 'Mode',
    'FREQUENCY': 'Frequency',
    'T1FRAC': 'T1 EMF',
    'T1SUM': 'T1 Cummulative EMF',
    'T2FRAC': 'T2 EMF',
    'T2SUM': 'T2 Cummulative EMF',
    'T3FRAC': 'T3 EMF',
    'T3SUM': 'T3 Cummulative EMF',
}

MODALMASSFRAC_ROTATION_KEYS = {
    'MODE': 'Mode',
    'FREQUENCY': 'Frequency',
    'R1FRAC': 'R1 EMF',
    'R1SUM': 'R1 Cummulative EMF',
    'R2FRAC': 'R2 EMF',
    'R2SUM': 'R2 Cummulative EMF',
    'R3FRAC': 'R3 EMF',
    'R3SUM': 'R3 Cummulative EMF',
}

class ModalEffectiveMassFractionF06Page(F06Page):
    
    def __init__(self, df=None, info=None, continuation=False, rawlines=None, meta=None):
        super().__init__(rawlines, meta)
        self.df = df
        self.info = {} if info == None else info
        self.continuation = continuation

    def parse_page(cls, lines, is_continuation=False):

        if is_continuation:
            return cls._parse_continuation_page(lines)
        
        a, b = find_tabular_line_range(lines, MODALMASSFRAC_TABULAR_LINE)

        mode = MODALMASSFRAC_ROTATION_KEYS
        if MODALMASSFRAC_CHECK_TRANSLATION_STR in lines[MODALMASSFRAC_CHECK_TRANSLATION_LINE]:
            mode = MODALMASSFRAC_TRANSLATION_KEYS

        parsed_data = extract_tabulated_data(lines[a:b])

        df = pd.DataFrame(parsed_data, columns=list(mode.keys()))

        info = {}
        label, subcase = parse_label_subcase(lines[MODALMASSFRAC_SUBCASE_LINE])
        info['LABEL'] = label
        info['SUBCASE'] = subcase

        return ModalEffectiveMassFractionF06Page(df, info, lines)
    
    def _parse_continuation_page(cls, lines):

        a, b = find_tabular_line_range(lines, 7)

        mode = MODALMASSFRAC_ROTATION_KEYS
        if 'T1' in lines[4]:
            mode = MODALMASSFRAC_TRANSLATION_KEYS

        parsed_data = extract_tabulated_data(lines[a:b])

        df = pd.DataFrame(parsed_data, columns=list(mode.keys()))

        info = {}
        label, subcase = parse_label_subcase(lines[MODALMASSFRAC_SUBCASE_LINE])
        info['LABEL'] = label
        info['SUBCASE'] = subcase

        return ModalEffectiveMassFractionF06Page(df, info, lines, True)
    
    def is_page_of_this_type(cls, lines, previous_page_type):
        
        if previous_page_type == 'ModalEffectiveMassFractionF06Page':
            return len(lines)-1 >= 5 and 'FRACTION' in lines[5]
        
        return len(lines)-1 >= MODALMASSFRAC_LINE and MODALMASSFRAC_STR in lines[MODALMASSFRAC_LINE]
    