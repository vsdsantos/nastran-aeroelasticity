from typing import Union

from aero.AeroelasticAnalysis import FlutterAnalysis, PanelFlutterAnalysis

import numpy as np
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
    'VELOCITY': 'Velocity',
    'DAMPING': 'Damping',
    'FREQUENCY': 'Frequency',
    'REALEIGVAL': 'Real Eigenvalue',
    'IMAGEIGVAL': 'Imag Eigenvalue',
}


def read_f06(filename, analysis: Union[FlutterAnalysis, PanelFlutterAnalysis]):
    with open(filename, 'r') as file:
        content = file.readlines()

    flutter_summaries = []
    for i, line in enumerate(content):
        if 'FLUTTER  SUMMARY' in line:
            flutter_summaries.append(content[i + 1:i + 6 + len(analysis.velocities)])

    modes = []
    flutter_conditions = []
    critical_modes = []
    for summary in flutter_summaries:
        raw_data = []
        data = {}

        # pop information from the 2 first lines
        raw = summary.pop(0) + ' ' + summary.pop(0)
        for key in FLUTTER_INFO_KEYS:
            rgxp = re.compile(r'\b{} =\s*\S*'.format(key))
            value = rgxp.search(raw).group(0).replace('{} ='.format(key), '').strip()
            try:
                data[key] = float(value)
            except ValueError:
                data[key] = value

        # ignore 2 blank lines and data header, split data, and parse
        for line in summary[3:]:
            raw_data.append(list(map(lambda entry: float(entry), line.split())))

        data['KFREQ'] = np.array(list(map(lambda args: args[0], raw_data)))
        data['inv_KFREQ'] = np.array(list(map(lambda args: args[1], raw_data)))
        data['VELOCITY'] = np.array(list(map(lambda args: args[2], raw_data)))
        data['DAMPING'] = np.array(list(map(lambda args: args[3], raw_data)))
        data['FREQUENCY'] = np.array(list(map(lambda args: args[4], raw_data)))
        data['REALEIGVAL'] = np.array(list(map(lambda args: args[5], raw_data)))
        data['IMAGEIGVAL'] = np.array(list(map(lambda args: args[6], raw_data)))

        data['MODE'] = ((int(data['POINT']) - 1) % (len(flutter_summaries)//len(analysis.machs))) + 1

        if any(map(lambda v: v > 0, data['DAMPING'])):
            idx = np.where(data['DAMPING'] > 0)[0][0] + 1
            critic_vel = np.interp(0, data['DAMPING'][:idx], data['VELOCITY'][:idx])
            critic_freq = np.interp(critic_vel, data['VELOCITY'][:idx], data['FREQUENCY'][:idx])
            if type(analysis) is PanelFlutterAnalysis:
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
    fig = plt.figure(figsize=figsize)
    fig.suptitle(title)
    ax = fig.gca()
    for mode, label in zip(list(modes), labels):
        ax.plot(mode[x_key], mode[y_key], marker, label=label)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.grid()
    ax.legend(bbox_to_anchor=(1.2, 1), fancybox=True, shadow=True)
    plt.show()


def plot_vg(modes, labels, title):
    plot_figure(modes, 'VELOCITY', 'DAMPING', labels, title, 'Velocidade (m/s)', 'Amortecimento')


def plot_vf(modes, labels, title):
    plot_figure(modes, 'VELOCITY', 'FREQUENCY', labels, title, 'Velocidade (m/s)', 'Frequência (Hz)')


def plot_complex(modes, labels, title):
    plot_figure(modes, 'REALEIGVAL', 'IMAGEIGVAL', labels, title, 'Real', 'Imag')


def filter_modes(modes, mach, dr):
    return filter(lambda m: m['MACH NUMBER'] == mach and m['DENSITY RATIO'] == dr, modes)


def plot_flutter_data(modes, analysis: FlutterAnalysis):
    for mach in analysis.machs:
        for dens_ratio in analysis.densities_ratio:
            modes = list(filter_modes(modes, mach, dens_ratio))
            labels = ['Mode {}'.format(mode['MODE']) for mode in modes]

            plot_vg(modes, labels, 'V-g, Mach {}, Density Ratio {}, AoA {}°'.format(mach, dens_ratio, 0))
            plot_vf(modes, labels, 'V-f, Mach {}, Density Ratio {}, AoA {}°'.format(mach, dens_ratio, 0))
            # plot_complex(modes, labels,
            #              'Autovalores Complexos, Mach {}, Density Ratio {}, AoA {}°'.format(mach, dens_ratio, 0))
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

