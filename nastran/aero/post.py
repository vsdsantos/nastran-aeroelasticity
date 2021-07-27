from typing import Union

from nastran.aero.analysis import FlutterSubcase, PanelFlutterSubcase

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
    
    info = dict()
    
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
        data.append(list(map(lambda entry: float(entry), line.split())))
        # for i, k in enumerate(FLUTTER_DATA_KEYS):
            # data.append(np.array(list(map(lambda args: args, raw_data))))
        
    return data

    # data['KFREQ'] = np.array(list(map(lambda args: args[0], raw_data)))
    # data['inv_KFREQ'] = np.array(list(map(lambda args: args[1], raw_data)))
    # data['VELOCITY'] = np.absolute(np.array(list(map(lambda args: args[2], raw_data))))  # makes velocities positive
    # data['DAMPING'] = np.array(list(map(lambda args: args[3], raw_data)))
    # data['FREQUENCY'] = np.array(list(map(lambda args: args[4], raw_data)))
    # data['REALEIGVAL'] = np.array(list(map(lambda args: args[5], raw_data)))
    # data['IMAGEIGVAL'] = np.array(list(map(lambda args: args[6], raw_data)))

    # data['MODE'] = ((int(data['POINT']) - 1) % (len(flutter_summaries)//len(analysis.machs))) + 1

SKIP_LINE_SET = {"*** USER INFORMATION MESSAGE"}

def check_skip_lines(line):
    return any([ (k in line) for k in SKIP_LINE_SET])

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

def read_f06(filename, analysis: Union[FlutterSubcase, PanelFlutterSubcase]):
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
                if check_skip_lines(l):
                    break
                raw_content.append(l)
                j += 1

            parsed_data = parse_content(raw_content)
            
            df = parse_to_df(parsed_data, info,
                             data[-1] if len(data)>0 else None)
            
            data.append(df)
            
            # flutter_summaries.append(content[i + 1 : i + 6 + len(analysis.velocities)])
        
    return pd.concat(data)
    # return process_data(flutter_summaries)


def process_df(df):
    pass

def process_data(flutter_summaries):
    
    modes = []
    flutter_conditions = []
    critical_modes = []
    
    for summary in flutter_summaries:
        raw_data = []
        data = {}

        # pop information from the 2 first lines

        # ignore 2 blank lines and data header, split data, and parse
    
        if any(map(lambda v: v > 0, data['DAMPING'])):
            idx = np.where(data['DAMPING'] > 0)[0][0] + 1
            critic_vel = np.interp(0, data['DAMPING'][:idx], data['VELOCITY'][:idx])
            critic_freq = np.interp(critic_vel, data['VELOCITY'][:idx], data['FREQUENCY'][:idx])
            if type(analysis) is PanelFlutterSubcase:
                D = analysis.plate_stiffness
                vref = analysis.vref
                a = analysis.ref_chord
                rho = analysis.ref_rho
                lamb_critc = (rho * (critic_vel * vref) ** 2) * (a ** 3) / (
                        np.sqrt(data['MACH NUMBER'] ** 2 - 1) * D)
            else:
                lamb_critc = None
            critic_data = {
                'VELOCITY': critic_vel,
                'FREQUENCY': critic_freq,
                'LAMBDA': lamb_critc,
                'MODE': data['MODE'],
                'MACH': data['MACH NUMBER'],
                'DENSITY RATIO': data['DENSITY RATIO']
            }
    
            flutter_conditions.append(critic_data)
            critical_modes.append(data)
        modes.append(data)
        
    return modes, critical_modes, flutter_conditions

def filter_modes_by_list(modes, mode_list):
    return list(filter(lambda m: m['MODE'] in mode_list, modes))


def plot_figure(modes, x_key, y_key, labels, title, xlabel='x', ylabel='y', marker='.-'):
    figsize = (9, 5)
    fig = plt.figure(figsize=figsize, constrained_layout=True)
    ax = fig.gca()
    for mode, label in zip(list(modes), labels):
        ax.plot(mode[x_key], mode[y_key], marker, label=label)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.set_title(title, fontsize=16)
    ax.grid()
    ax.legend(bbox_to_anchor=(1.2, 1), fancybox=True, shadow=True)
    plt.show()


def plot_vg(modes, labels, title):
    plot_figure(modes, 'VELOCITY', 'DAMPING', labels, title, 'Velocity (m/s)', 'Damping')


def plot_vf(modes, labels, title):
    plot_figure(modes, 'VELOCITY', 'FREQUENCY', labels, title, 'Velocity (m/s)', 'Frequency (Hz)')


def plot_complex(modes, labels, title):
    plot_figure(modes, 'REALEIGVAL', 'IMAGEIGVAL', labels, title, 'Real', 'Imag')


def filter_modes(modes, mach, dr):
    return filter(lambda m: m['MACH NUMBER'] == mach and m['DENSITY RATIO'] == dr, modes)


def plot_flutter_data(modes, analysis: FlutterSubcase):
    for mach in analysis.machs:
        for dens_ratio in analysis.densities_ratio:
            modes = list(filter_modes(modes, mach, dens_ratio))
            labels = ['Mode {}'.format(mode['MODE']) for mode in modes]

            plot_vg(modes, labels, 'V-g, Mach {}, AoA {}°'.format(mach, 0))
            plot_vf(modes, labels, 'V-f, Mach {}, AoA {}°'.format(mach, 0))
            plot_complex(modes, labels,
                         'Complex Eigenvalues, Mach {}, AoA {}°'.format(mach, 0))
    plt.show()


def plot_critical_flutter_data(modes):
    labels = ['Mode {}; Mach {}'.format(mode['MODE'], mode['MACH NUMBER']) for mode in modes]

    plot_vg(modes, labels, 'V-g')
    plot_vf(modes, labels, 'V-f')
    # plot_complex(modes, labels, 'Autovalores Complexos')
    plt.show()


def export_flutter_data(modes, critical_modes, flutter_data, analysis, filename):
    workbook = xlsxwriter.Workbook(filename)

    worksheet = workbook.add_worksheet('Flutter Resume')

    for i, key in enumerate(flutter_data[0].keys()):
        worksheet.write(1, i + 1, key)

    for i, data in enumerate(flutter_data):
        for j, (key, value) in enumerate(data.items()):
            worksheet.write(i + 2, j + 1, value)

    worksheet = workbook.add_worksheet('Critical Modes')

    for i, mode in enumerate(critical_modes):
        for j, key in enumerate(FLUTTER_DATA_KEYS):
            worksheet.write(1 + i * len(mode[key]), j + 1, FLUTTER_DATA_KEYS[key])
            worksheet.write_column(2 + i * len(mode[key]), j + 1, mode[key])

    for mach in analysis.machs:
        m_modes = filter(lambda m: m['MACH NUMBER'] == mach, modes)
        for mode in m_modes:
            worksheet = workbook.add_worksheet('MODE {}; M {}; DR {}'.format(
                mode['MODE'], mode['MACH NUMBER'], mode['DENSITY RATIO']))

            for j, key in enumerate(FLUTTER_INFO_KEYS):
                worksheet.write('B{}'.format(2 + j), key)
                worksheet.write('C{}'.format(2 + j), mode[key])
            # worksheet.write('A{}'.format(3 + len(FLUTTER_DATA_KEYS)), '')
            # worksheet.write('B{}'.format(3 + len(FLUTTER_DATA_KEYS)), '')

            for j, key in enumerate(FLUTTER_DATA_KEYS):
                worksheet.write(1, j + 4, FLUTTER_DATA_KEYS[key])
                worksheet.write_column(2, j + 4, mode[key])

    workbook.close()


def panel_flutter_analysis(analysis, output_file):
    for key, subcase in analysis.subcases.items():
        print('SUBCASE {}'.format(key))
        modes, critical_modes, flutter = read_f06(output_file.replace('.bdf', '.f06'), subcase)
        searched_modes = list(filter(lambda m: m['MODE'] <= subcase.n_modes-10, modes))
        plot_flutter_data(searched_modes, subcase)
        searched_crit_modes = list(filter(lambda m: m['MODE'] <= subcase.n_modes, critical_modes))
        if len(searched_crit_modes) > 0:
            # plot_critical_flutter_data(searched_crit_modes)
            for flut in flutter:
                print('Flutter found on MODE {}'.format(flut['MODE']))
                print('\tMACH \t{}'.format(flut['MACH']))
                print('\tVELOCITY \t{}'.format(flut['VELOCITY']))
                print('\tLAMBDA \t{}'.format(flut['LAMBDA']))
        else:
            print('No flutter encountered in subcase {}.'.format(key))
        # export_flutter_data(modes, critical_modes, flutter, subcase[1], os.path.join(base_path, 'output-model.xlsx'))
