from typing import Union

from pandas.core.frame import DataFrame

from nastran.aero.analysis.flutter import FlutterSubcase
from nastran.aero.analysis.panel_flutter import PanelFlutterSubcase

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

import xlsxwriter
import re

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

p_header = re.compile(r"(?P<label>.+(?=SUBCASE))(?P<subcase>SUBCASE\s\d+)")

def parse_summary_header(header):
    # assert len(header) == 3
    
    line1, line2, line3 = header[0], header[1], header[2]
    
    res = p_header.search(line1[1:])
    label = res.group('label').strip()
    subcase = res.group('subcase').replace('SUBCASE', '').strip()
    
    info = {}
    
    info['SUBCASE'] = int(subcase)
    info['LABEL'] = label
    
    raw = line2 + ' ' + line3
    for key in FLUTTER_INFO_KEYS:
        p = re.compile(r'\b{} =\s*\S*'.format(key))
        value = p.search(raw).group(0).replace('{} ='.format(key), '').strip()
        try:
            info[key] = float(value)
        except ValueError:
            info[key] = value
    
    return info


def parse_content(content):
    data = []
    for line in content:
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

SKIP_LINE_SET = {"*** USER INFORMATION MESSAGE", "A ZERO FREQUENCY"}

def check_skip_lines(line):
    return any(map(lambda k: k in line, SKIP_LINE_SET))

def parse_to_df(parsed_data, info, last_df):
    df = pd.DataFrame(parsed_data, 
                              columns=list(FLUTTER_DATA_KEYS.keys()))
    if type(last_df) is not type(None):
        last_index = last_df.index.droplevel('INDEX').unique().to_list()[0]
        is_continuation = last_index == (info['SUBCASE'],
                                        info['MACH NUMBER'],
                                        info['POINT'])
    else:
        is_continuation = False
    
    if is_continuation:
        last_idx_number = last_df.iloc[-1].name[-1]
        count = range(last_idx_number+1,last_idx_number+1+len(df))
    else:
        count = range(len(df))
        
    header = [
        [info['SUBCASE']],
        [info['MACH NUMBER']],
        [info['POINT']],
        # [info['DENSITY RATIO']],
        count
        ]
    
    index = pd.MultiIndex.from_product(header,
               names=['SUBCASE', 'MACH NUMBER', 'POINT', 'INDEX'])
    # names=['SUBCASE', 'POINT', 'MACH NUMBER', 'DENSITY RATIO', 'INDEX'])
    
    df.index = index
    return df

def read_f06(filename):
    with open(filename, 'r') as file:
        raw_lines = file.readlines()

    data = []
    
    for i, line in enumerate(raw_lines):
        if 'FLUTTER  SUMMARY' in line:
            raw_header = [raw_lines[i-1]] + raw_lines[i+1:i+3]
            info = parse_summary_header(raw_header)
            
            raw_content = []
            j = i+6 # linha após as labels de dados
            while raw_lines[j][0] != '1': # primeiro char na linha final da pagina é 1
                l = raw_lines[j]
                if check_skip_lines(l) or l.strip() == '':
                    break
                raw_content.append(l)
                j += 1

            parsed_data = parse_content(raw_content)
            
            df = parse_to_df(parsed_data, info,
                             data[-1] if len(data)>0 else None)
            
            data.append(df)
        
    return pd.concat(data)


def read_and_concat_f06s(case_files, labels, label_name="THETA"):
    
    if len(labels) != len(case_files):
        raise Exception("Collections should be of same size.")

    df_results = []
    
    for i, fn in enumerate(case_files):
        print("Reading... {}".format(fn))
        df_data = read_f06(fn)
        df_results.append(
            pd.concat(
                { labels[i]: df_data },
                names=[label_name]
            )
        )
        
    return pd.concat(df_results)


def calc_sawyer_dyn_pressure(vel, mach, D, vref, a, rho):
    return (rho * (vel * vref) ** 2) * (a ** 3) / (np.sqrt(mach ** 2 - 1) * D)


def parse_panel_flutter_results(analysis, case_files, theta_range, D11):
    
    df = read_and_concat_f06s(case_files, theta_range)
    
    # print(df.info())
        
    df['DYNPRSS'] = calc_sawyer_dyn_pressure(df.VELOCITY,
                                         df.index.get_level_values('MACH NUMBER'),
                                         [D11]*len(df),
                                         analysis.subcases[1].vref,
                                         analysis.subcases[1].ref_chord,
                                         analysis.subcases[1].ref_rho)

    return df


def get_critical_roots(df: DataFrame, epsilon=1e-3):

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


def plot_vf_vg(df, only_critic=False, epsilon=1e-3):
    fig, axs = plt.subplots(2)
    
    for point, df in df.groupby(level="POINT"):

        if only_critic and not any(df.DAMPING >= epsilon):
            continue

        axs[0].plot(df.VELOCITY, df.FREQUENCY, label="Mode {}".format(int(point)), markevery=4)
        axs[1].plot(df.VELOCITY, df.DAMPING, markevery=4)
    
    axs[0].grid()
    axs[1].grid()

    fig.legend()

    return fig


# Old code \/

# def process_data(flutter_summaries):
    
#     modes = []
#     flutter_conditions = []
#     critical_modes = []
    
#     for summary in flutter_summaries:
#         raw_data = []
#         data = {}

#         # pop information from the 2 first lines

#         # ignore 2 blank lines and data header, split data, and parse
    
#         if any(map(lambda v: v > 0, data['DAMPING'])):
#             idx = np.where(data['DAMPING'] > 0)[0][0] + 1
#             critic_vel = np.interp(0, data['DAMPING'][:idx], data['VELOCITY'][:idx])
#             critic_freq = np.interp(critic_vel, data['VELOCITY'][:idx], data['FREQUENCY'][:idx])
#             if type(analysis) is PanelFlutterSubcase:
#                 D = analysis.plate_stiffness
#                 vref = analysis.vref
#                 a = analysis.ref_chord
#                 rho = analysis.ref_rho
#                 lamb_critc = (rho * (critic_vel * vref) ** 2) * (a ** 3) / (
#                         np.sqrt(data['MACH NUMBER'] ** 2 - 1) * D)
#             else:
#                 lamb_critc = None
#             critic_data = {
#                 'VELOCITY': critic_vel,
#                 'FREQUENCY': critic_freq,
#                 'LAMBDA': lamb_critc,
#                 'MODE': data['MODE'],
#                 'MACH': data['MACH NUMBER'],
#                 'DENSITY RATIO': data['DENSITY RATIO']
#             }
    
#             flutter_conditions.append(critic_data)
#             critical_modes.append(data)
#         modes.append(data)
        
#     return modes, critical_modes, flutter_conditions

# def filter_modes_by_list(modes, mode_list):
#     return list(filter(lambda m: m['MODE'] in mode_list, modes))


# def plot_figure(modes, x_key, y_key, labels, title, xlabel='x', ylabel='y', marker='.-'):
#     figsize = (9, 5)
#     fig = plt.figure(figsize=figsize, constrained_layout=True)
#     ax = fig.gca()
#     for mode, label in zip(list(modes), labels):
#         ax.plot(mode[x_key], mode[y_key], marker, label=label)
#     ax.set_xlabel(xlabel)
#     ax.set_ylabel(ylabel)
#     ax.set_title(title, fontsize=16)
#     ax.grid()
#     ax.legend(bbox_to_anchor=(1.2, 1), fancybox=True, shadow=True)
#     plt.show()


# def plot_vg(modes, labels, title):
#     plot_figure(modes, 'VELOCITY', 'DAMPING', labels, title, 'Velocity (m/s)', 'Damping')


# def plot_vf(modes, labels, title):
#     plot_figure(modes, 'VELOCITY', 'FREQUENCY', labels, title, 'Velocity (m/s)', 'Frequency (Hz)')


# def plot_complex(modes, labels, title):
#     plot_figure(modes, 'REALEIGVAL', 'IMAGEIGVAL', labels, title, 'Real', 'Imag')


# def filter_modes(modes, mach, dr):
#     return filter(lambda m: m['MACH NUMBER'] == mach and m['DENSITY RATIO'] == dr, modes)


# def plot_flutter_data(modes, analysis: FlutterSubcase):
#     for mach in analysis.machs:
#         for dens_ratio in analysis.densities_ratio:
#             modes = list(filter_modes(modes, mach, dens_ratio))
#             labels = ['Mode {}'.format(mode['MODE']) for mode in modes]

#             plot_vg(modes, labels, 'V-g, Mach {}, AoA {}°'.format(mach, 0))
#             plot_vf(modes, labels, 'V-f, Mach {}, AoA {}°'.format(mach, 0))
#             plot_complex(modes, labels,
#                          'Complex Eigenvalues, Mach {}, AoA {}°'.format(mach, 0))
#     plt.show()


# def plot_critical_flutter_data(modes):
#     labels = ['Mode {}; Mach {}'.format(mode['MODE'], mode['MACH NUMBER']) for mode in modes]

#     plot_vg(modes, labels, 'V-g')
#     plot_vf(modes, labels, 'V-f')
#     # plot_complex(modes, labels, 'Autovalores Complexos')
#     plt.show()


# def export_flutter_data(modes, critical_modes, flutter_data, analysis, filename):
#     workbook = xlsxwriter.Workbook(filename)

#     worksheet = workbook.add_worksheet('Flutter Resume')

#     for i, key in enumerate(flutter_data[0].keys()):
#         worksheet.write(1, i + 1, key)

#     for i, data in enumerate(flutter_data):
#         for j, (key, value) in enumerate(data.items()):
#             worksheet.write(i + 2, j + 1, value)

#     worksheet = workbook.add_worksheet('Critical Modes')

#     for i, mode in enumerate(critical_modes):
#         for j, key in enumerate(FLUTTER_DATA_KEYS):
#             worksheet.write(1 + i * len(mode[key]), j + 1, FLUTTER_DATA_KEYS[key])
#             worksheet.write_column(2 + i * len(mode[key]), j + 1, mode[key])

#     for mach in analysis.machs:
#         m_modes = filter(lambda m: m['MACH NUMBER'] == mach, modes)
#         for mode in m_modes:
#             worksheet = workbook.add_worksheet('MODE {}; M {}; DR {}'.format(
#                 mode['MODE'], mode['MACH NUMBER'], mode['DENSITY RATIO']))

#             for j, key in enumerate(FLUTTER_INFO_KEYS):
#                 worksheet.write('B{}'.format(2 + j), key)
#                 worksheet.write('C{}'.format(2 + j), mode[key])
#             # worksheet.write('A{}'.format(3 + len(FLUTTER_DATA_KEYS)), '')
#             # worksheet.write('B{}'.format(3 + len(FLUTTER_DATA_KEYS)), '')

#             for j, key in enumerate(FLUTTER_DATA_KEYS):
#                 worksheet.write(1, j + 4, FLUTTER_DATA_KEYS[key])
#                 worksheet.write_column(2, j + 4, mode[key])

#     workbook.close()


# def panel_flutter_analysis(analysis, output_file):
#     for key, subcase in analysis.subcases.items():
#         print('SUBCASE {}'.format(key))
#         modes, critical_modes, flutter = read_f06(output_file.replace('.bdf', '.f06'), subcase)
#         searched_modes = list(filter(lambda m: m['MODE'] <= subcase.n_modes-10, modes))
#         plot_flutter_data(searched_modes, subcase)
#         searched_crit_modes = list(filter(lambda m: m['MODE'] <= subcase.n_modes, critical_modes))
#         if len(searched_crit_modes) > 0:
#             # plot_critical_flutter_data(searched_crit_modes)
#             for flut in flutter:
#                 print('Flutter found on MODE {}'.format(flut['MODE']))
#                 print('\tMACH \t{}'.format(flut['MACH']))
#                 print('\tVELOCITY \t{}'.format(flut['VELOCITY']))
#                 print('\tLAMBDA \t{}'.format(flut['LAMBDA']))
#         else:
#             print('No flutter encountered in subcase {}.'.format(key))
#         # export_flutter_data(modes, critical_modes, flutter, subcase[1], os.path.join(base_path, 'output-model.xlsx'))
