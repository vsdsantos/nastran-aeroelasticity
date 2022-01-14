from typing import Union

from copy import copy

from pandas.core.frame import DataFrame

from nastran.aero.analysis.flutter import FlutterSubcase
from nastran.aero.analysis.panel_flutter import PanelFlutterSubcase
from nastran.post.common import extract_tabulated_data, parse_text_value, F06Page

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

import re

FLUTTER_SUMMARY_SUBCASE = 2
FLUTTER_SUMMARY_INFO_LINES = (4, 5)
FLUTTER_SUMMARY_HEADER_LINE = 8
FLUTTER_SUMMARY_TABULAR_LINE = 9

FLUTTER_INFO_KEYS = {
    'CONFIGURATION',
    'XY-SYMMETRY',
    'XZ-SYMMETRY',
    'POINT',
    'MACH NUMBER',
    'DENSITY RATIO',
    'METHOD',
}

FLUTTER_DATA_KEYS = {
    'KFREQ': 'Frequency',
    '1./KFREQ': 'Inverse Frequency',
    'VELOCITY': 'Velocity',
    'DAMPING': 'Damping',
    'FREQUENCY': 'Frequency',
    'REALEIGVAL': 'Real Eigenvalue',
    'IMAGEIGVAL': 'Imag Eigenvalue',
}

SKIP_LINE_SET = {"*** USER INFORMATION MESSAGE", "A ZERO FREQUENCY"}

p_header = re.compile(r"(?P<label>.+(?=SUBCASE))(?P<subcase>SUBCASE\s\d+)")
p_info = {key:re.compile(r'\b{} =\s*\S*'.format(key)) for key in FLUTTER_INFO_KEYS}


class FlutterF06Page(F06Page):
    def __init__(self, df=None, info=None, meta=None):
        super().__init__(meta)
        self.df = df
        self.info = info

    def __repr__(self):
        return self.__str__()

    def __str__(self):
        return 'FLUTTER F06 PAGE\tSUBCASE={}\tLABEL={}\tMODE={}'.format(self.info['SUBCASE'],
                                                           self.info['LABEL'],
                                                           self.info['POINT'])


def join_flutter_pages(pages):
    new_pages = []
    last_idx = 0

    for i, page in enumerate(pages):
        if _is_continuation(i, pages):
            # count = range(last_idx_number+1,last_idx_number+1+len(df))
            page.df.index = range(last_idx+1,last_idx+1+len(page.df))
            # last_idx = page.df.index.stop - 1
            new_pages[-1].df = pd.concat([new_pages[-1].df, page.df])
        else:
            # page.df.index = create_multiindex()
            new_pages.append(copy(page))
        last_idx = page.df.index.stop - 1

    return new_pages


def flutter_pages_to_df(pages):
    data = []

    for page in pages:
        df = copy(page.df)
        # idx = range(df.index.start, df.index.stop, df.index.step)
        df.index = _create_multiindex(page.info, df.index)
        data.append(df)

    return pd.concat(data)


def parse_flutter_page(lines):

    raw_info = [lines[i] for i in FLUTTER_SUMMARY_INFO_LINES]
    info = _parse_summary_info(raw_info)

    label, subcase = _parse_label_subcase(lines[FLUTTER_SUMMARY_SUBCASE])
    info['LABEL'] = label
    info['SUBCASE'] = subcase

    a, b = _find_tabular_line_range(lines)
    parsed_data = extract_tabulated_data(lines[a:b])

    df = pd.DataFrame(parsed_data, columns=list(FLUTTER_DATA_KEYS.keys()))

    return FlutterF06Page(df, info)


def calc_sawyer_dyn_pressure(vel, mach, D, vref, a, rho):
    return (rho * (vel * vref) ** 2) * (a ** 3) / (np.sqrt(mach ** 2 - 1) * D)


# def parse_panel_flutter_results(analysis, case_files, theta_range, D11):
#
#     # df = read_and_concat_f06s(case_files, theta_range)
#
#     # print(df.info())
#
#     df['DYNPRSS'] = calc_sawyer_dyn_pressure(df.VELOCITY,
#                                          df.index.get_level_values('MACH NUMBER'),
#                                          [D11]*len(df),
#                                          analysis.subcases[1].vref,
#                                          analysis.subcases[1].ref_chord,
#                                          analysis.subcases[1].ref_rho)
#
#     return df


def get_critical_roots(df: DataFrame, epsilon=1e-9):

    indexes = list(df.index.names)
    for label in ["INDEX", "POINT"]:
        indexes.remove(label)

    critic_idx = df.loc[df.DAMPING >= -epsilon, 'VELOCITY'].groupby(indexes).apply(lambda df: df.idxmin())

    critic_modes_idx = critic_idx.apply(lambda i: i[:-1])

    # critic = [df_.loc[idx] for idx in points.to_list()]

    interp_data = []

    for idx in critic_modes_idx.to_list():

        df_s = df.loc[idx]

        positive_damp_idx = df_s.DAMPING >= -epsilon
        if not any(positive_damp_idx):
            continue

        # first row after flutter (damp >= 0)
        upper_row = df_s.loc[positive_damp_idx].iloc[0,:]

        # row before the flutter condition
        if upper_row.name > 0:
            lower_row = df_s.loc[upper_row.name-1,:]
        else:
            lower_row = df_s.loc[upper_row.name,:]

        # new row with damp = 0 to be interpolated
        new_row = pd.Series([None, None, None, .0, None, None, None],
                            index=upper_row.index, name=-1)

        # concat rows and interpolate values
        interp_df = pd.concat([lower_row, new_row, upper_row], axis=1).T.interpolate()

        # get interpolated row
        interp_row = interp_df.loc[-1]

        # create a new DataFrame
        multi_idx = pd.MultiIndex.from_tuples([idx], names=df.index.names[:-1])
        refact_df = pd.DataFrame([interp_row.to_numpy()],
                                 index=multi_idx,
                                 columns=df.columns)

        interp_data.append(refact_df)

    if len(interp_data) == 0:
        print("WARNING: No critial roots were found... check episilon value or analysis parameters.")
        return pd.DataFrame([])
    return pd.concat(interp_data)


def _find_tabular_line_range(lines):
    k = len(lines)
    j = FLUTTER_SUMMARY_TABULAR_LINE # linha após as labels de dados
    while j < k: # primeiro char na linha final da pagina é 1
        l = lines[j]
        if _check_skip_lines(l) or l.strip() == '':
            break
        j += 1
    return (FLUTTER_SUMMARY_TABULAR_LINE, j)


def _parse_label_subcase(line):
    res = p_header.search(line[1:])
    label = res.group('label').strip()
    subcase = res.group('subcase').replace('SUBCASE', '').strip()
    return (label, int(subcase))


def _parse_summary_info(lines):

    line1, line2 = lines[0], lines[1]

    info = {}

    raw = line1 + ' ' + line2
    for key in FLUTTER_INFO_KEYS:
        p = p_info[key]
        value = p.search(raw).group(0).replace('{} ='.format(key), '').strip()
        info[key] = parse_text_value(value)

    return info


def _check_skip_lines(line):
    return any(map(lambda k: k in line, SKIP_LINE_SET))


def _is_continuation(i, pages):

    is_continuation = False
    if i > 0 and pages[i-1].df is not type(None):
        last_info = (pages[i-1].info['SUBCASE'],
                     pages[i-1].info['MACH NUMBER'],
                     pages[i-1].info['POINT'])
        is_continuation = last_info == (pages[i].info['SUBCASE'],
                                        pages[i].info['MACH NUMBER'],
                                        pages[i].info['POINT'])
    return is_continuation


def _create_multiindex(info, range):
    header = [
        [info['SUBCASE']],
        [info['MACH NUMBER']],
        [info['POINT']],
        # [info['DENSITY RATIO']],
        range
        ]

    return pd.MultiIndex.from_product(header,
               names=['SUBCASE', 'MACH NUMBER', 'POINT', 'INDEX'])
    # names=['SUBCASE', 'POINT', 'MACH NUMBER', 'DENSITY RATIO', 'INDEX'])
