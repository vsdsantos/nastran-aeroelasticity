from pyNastran.bdf.bdf import BDF, CaseControlDeck
from pyNastran.utils.nastran_utils import run_nastran
from AeroelasticAnalysis import IDUtility
from AeroelasticAnalysis import FlutterAnalysis, SuperAeroPanel5
from femap import Femap
import numpy as np
import matplotlib.pyplot as plt
import xlsxwriter
import os
import re


def femap_to_nastran(bdf_filename):
    """
    Connects with an open Femap intance and grabs user input to the aeroelastic model and analysis

    Parameters
    -----------
    bdf_filename : str
        file to output the .bdf current model
        Currently there is a need to run a previous analysis (e.g. Modal Analysis) so all the elements get printed

    Returns
    --------
     (analysis: AeroAnalysis, panel: AeroPanel)
        a set with an AeroAnalysis and AeroPanel objects, regarding all the information needed
    """

    # load Femap interface
    femap = Femap()
    spanel = SuperAeroPanel5(femap)
    analysis = FlutterAnalysis(femap)

    # get aerodynamic grid limits
    spanel.set_panel_limits()

    # aerodynamic mesh definition
    spanel.set_mesh_size()

    # generate the AeroPanel objects
    spanel.create_aero5_panels()

    # panel properties
    spanel.set_panel_properties_equally()

    # grid group id or node ids for spline interpolation
    # spanel.set_panels_grid_group()
    spanel.set_panels_grid_ids()

    # aeroelastic analysis properties
    analysis.set_aeroelastic_properties()

    # write model
    femap.export_bdf_model(bdf_filename)

    return analysis, spanel


def gen_aero_bdf(input_bdf, analysis, spanel, output_bdf):
    """
    Generates the .bdf file for NASTRAN Solution 145 - Aeroelastic Flutter

    Parameters
    ----------
    input_bdf : str
        the input .bdf file name (with the structural model and other elements)
    analysis : AeroAnalysis5
        object containing information about the analysis
    spanel : SuperAeroPanel5
        object containing information about the panel
    output_bdf : str
        the .bdf output file with the aeroelastic card
    """

    # load models and utility
    base_model = BDF()
    model = BDF()
    idutil = IDUtility(model)

    print("Loading base bdf model to pyNastran...")
    base_model.read_bdf(input_bdf)

    # print(base_model.get_bdf_stats())

    # clears problematic entries from previous analysis
    print("Sanitizing model...")
    cards = list(base_model.card_count.keys())
    black_list = ['ENDDATA', 'PARAM', 'EIGR', 'CAERO1', 'CAERO2', 'PAERO1', 'PAERO2', 'SPLINE1', 'SPLINE2'
                  'EIGRL']  # TODO: make whitelist of structural elements, properties and spcs
    sanit_card_keys = list(filter(lambda c: c not in black_list, cards))
    sanit_cards = base_model.get_cards_by_card_types(sanit_card_keys)

    for key in sanit_cards:
        for card in sanit_cards[key]:
            lines = card.write_card().split('\n')
            comments = []
            while lines[0].strip('')[0] == '$':  # separate comments
                comments.append(lines.pop(0))
            model.add_card_lines(lines, key, comment=comments)

    # print(model.get_bdf_stats())

    print("Writing cards...")

    # defines FLFACT cards
    densities_ratio = model.add_flfact(idutil.get_next_flfact_id(), analysis.densities_ratio)
    machs = model.add_flfact(idutil.get_next_flfact_id(), analysis.machs)
    velocities = model.add_flfact(idutil.get_next_flfact_id(), analysis.velocities)

    # defines FLUTTER card for flutter analysis
    flutter = model.add_flutter(idutil.get_next_flutter_id(),
                                method=analysis.method,
                                density=densities_ratio.sid,
                                mach=machs.sid,
                                reduced_freq_velocity=velocities.sid)

    # reference velocity param card
    model.add_param(key="VREF", values=[analysis.ref_velocity])
    model.add_param(key='GRDPNT', values=[1])
    model.add_param(key='WTMASS', values=[0.0025907])  # 1/g -> entries are in "weight density"
    model.add_param(key='COUPMASS', values=[1])
    model.add_param(key='OPPHIPA', values=[1])

    # real eigenvalue method card
    eigrl = model.add_eigrl(sid=idutil.get_next_method_id(),
                            norm='MAX',
                            nd=analysis.n_modes,
                            v1=analysis.frequency_limits[0],
                            v2=analysis.frequency_limits[1])

    # AERO card
    model.add_aero(analysis.ref_velocity, analysis.ref_chord, analysis.ref_rho)

    # AEFACT cards
    thickness_integrals = model.add_aefact(idutil.get_next_aefact_id(),
                                           spanel.aeropanels[0].thickness_integrals)
    machs_n_alphas = model.add_aefact(idutil.get_next_aefact_id(),
                                      [v for ma in zip(analysis.machs, analysis.alphas) for v in ma])

    # MKAERO1 cards
    model.add_mkaero1(analysis.machs, analysis.reduced_frequencies)

    # PAERO5 cards
    paero = model.add_paero5(idutil.get_next_paero_id(),
                             caoci=spanel.aeropanels[0].control_surface_ratios,
                             nalpha=1,
                             lalpha=machs_n_alphas.sid)

    # CORD2R and CAERO5 cards
    # wind_x_vector = np.array([1., 0., 0.])
    caeros = []
    cords = []
    id_increment = idutil.get_last_element_id()
    for i, panel in spanel.aeropanels.items():
        # set origin to element mid chord (linear spline requires the Y axis to be colinear with the
        # "elastic axis" of the structure, since it is a plate chord-wise divided,
        # the elastic axis should be at mid chord)
        origin = panel.p1 + panel.d12 / 2

        # point in the XZ plane to define the coordinate system
        # this hardcodes the Y axis of the local aerodynamic coordinate system
        # to be colinear with the element Y axis (i.e. the vector of p1 to p4)
        pxz_i = origin + panel.d12

        # local aerodynamic coordinate system
        cords.append(
            model.add_cord2r(idutil.get_next_coord_id(),
                             origin,
                             panel.orthogonal_vector,
                             pxz_i))

        # CAERO5 element
        caeros.append(
            model.add_caero5(idutil.get_next_caero_id() + id_increment,
                             pid=paero.pid,
                             cp=0,
                             nspan=panel.nspan,
                             nthick=thickness_integrals.sid,
                             p1=panel.p1,
                             x12=panel.l12,
                             p4=panel.p4,
                             x43=panel.l43,
                             ntheory=panel.theory)
        )
        id_increment = panel.nspan - 1

    # SET and SPLINE cards
    for i, elem in enumerate(caeros):
        # grid set (nodes) to the spline interpolation
        struct = spanel.aeropanels[i].structural_ids
        if type(struct) == int:
            grid_group = model.sets[struct]
        elif len(list(struct)) > 0:
            grid_group = model.add_set1(idutil.get_next_set_id(), list(struct))  # TODO: use SET2
        else:
            raise Exception('Structural grid set for Splines could not be created.')

        # Linear Spline (SPLINE2) element
        model.add_spline2(idutil.get_next_spline_id(),
                          caero=elem.eid,
                          # Coordinate system of the CAERO5 element
                          # (Y-Axis must be colinear with "Elastic Axis")
                          cid=cords[i].cid,
                          id1=elem.eid,
                          id2=elem.eid + spanel.nspan - 1,
                          setg=grid_group.sid,
                          # Detached bending and torsion (-1 -> infinity flexibility), only Z displacement
                          # allowed to comply with the rigid chord necessity of the Piston Theory
                          # and still model the plate bending (with N chord-wise elements).
                          dthx=-1.,
                          dthy=-1.,
                          dz=0)

    # Executive Control
    model.sol = 145  # Aerodynamic Flutter

    # Case Control
    cc = CaseControlDeck(['ECHO = BOTH'])
    cc.create_new_subcase(1)  # TODO: custom multiple subcases
    cc.add_parameter_to_local_subcase(1, 'FMETHOD = %d' % flutter.sid)
    cc.add_parameter_to_local_subcase(1, 'METHOD = %d' % eigrl.sid)
    cc.add_parameter_to_local_subcase(1, 'SPC = %d' % list(model.spcs.keys())[0])  # BC ID TODO: Let User Select
    # cc.add_parameter_to_local_subcase(1, 'DISP = ALL')
    model.case_control_deck = cc
    # model.add_param('POST', [-1])  # output op2 file
    model.add_param('UNITSYS', ['LBF-IN-C'])  # misc units information

    # Validate
    model.validate()

    print('Aerodynamic Flutter solution created...')
    # print(model.get_bdf_stats())

    # Write output
    print('Writing bdf file...')
    model.write_bdf(output_bdf)
    print('Done!')


FLUTTER_INFO_KEYS = {'CONFIGURATION', 'XY-SYMMETRY', 'XZ-SYMMETRY', 'POINT', 'MACH NUMBER', 'DENSITY RATIO', 'METHOD'}


def read_f06(filename, analysis: FlutterAnalysis):
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

        data['MODE'] = ((int(data['POINT']) - 1) % analysis.n_modes) + 1

        if any(map(lambda v: v > 0, data['DAMPING'])):
            idx = np.where(data['DAMPING'] > 0)[0][0] + 1
            critic_vel = np.interp(0, data['DAMPING'][:idx], data['VELOCITY'][:idx])
            critic_freq = np.interp(critic_vel, data['VELOCITY'][:idx], data['FREQUENCY'][:idx])
            D = 65.93
            vref = 12
            a = 10
            rho = 1.1468e-7
            lamb_critc = (rho * (critic_vel * vref) ** 2) * (a ** 3) / (
                    np.sqrt(data['MACH NUMBER'] ** 2 - 1) * D)
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


def plot_flutter_data(modes, analysis):
    figsize = (9, 5)
    for i, mach in enumerate(analysis.machs):
        m_modes = filter(lambda m: m['MACH NUMBER'] == mach, modes)

        fig1 = plt.figure(i * 3 + 1, figsize=figsize)
        fig2 = plt.figure(i * 3 + 2, figsize=figsize)
        fig3 = plt.figure(i * 3 + 3, figsize=figsize)

        fig1.suptitle(r'V-g, Mach {}, Density Ratio {}, AoA {}°'.format(mach, 0.5, 0))
        fig2.suptitle(r'V-f, Mach {}, Density Ratio {}, AoA {}°'.format(mach, 0.5, 0))
        fig3.suptitle(r'Complex Eigenvalues, Mach {}, Density Ratio {}, AoA {}°'.format(mach, 0.5, 0))

        for mode in m_modes:
            ax = fig1.gca()
            ax.plot(mode['VELOCITY'], mode['DAMPING'], '.-', label='Mode {}'.format(mode['MODE']))

            ax = fig2.gca()
            ax.plot(mode['VELOCITY'], mode['FREQUENCY'], '.-', label='Mode {}'.format(mode['MODE']))

            ax = fig3.gca()
            ax.plot(mode['REALEIGVAL'], mode['IMAGEIGVAL'], label='Mode {}'.format(mode['MODE']))

        ax = fig1.gca()
        ax.set_xlabel('Velocidade')
        ax.set_ylabel('Amortecimento')
        ax.grid()
        ax.legend(bbox_to_anchor=(1.2, 1), fancybox=True, shadow=True)

        ax = fig2.gca()
        ax.set_xlabel('Velocidade')
        ax.set_ylabel('Frequência')
        ax.grid()
        ax.legend(bbox_to_anchor=(1.2, 1), fancybox=True, shadow=True)

        ax = fig3.gca()
        ax.set_xlabel('Real')
        ax.set_ylabel('Imag')
        ax.grid()
        ax.legend(bbox_to_anchor=(1.2, 1), fancybox=True, shadow=True)

    plt.show()


def plot_critical_flutter_data(modes):
    figsize = (9, 5)

    fig1 = plt.figure(1, figsize=figsize)
    fig2 = plt.figure(2, figsize=figsize)
    fig3 = plt.figure(3, figsize=figsize)

    fig1.suptitle(r'V-g, Density Ratio {}, AoA {}°'.format(0.5, 0))
    fig2.suptitle(r'V-f, Density Ratio {}, AoA {}°'.format(0.5, 0))
    fig3.suptitle(r'Complex Eigenvalues, Density Ratio {}, AoA {}°'.format(0.5, 0))

    ax = fig1.gca()
    ax.set_xlabel('Velocidade')
    ax.set_ylabel('Amortecimento')
    ax.grid()
    #

    ax = fig2.gca()
    ax.set_xlabel('Velocidade')
    ax.set_ylabel('Frequência')
    ax.grid()
    # ax.legend(bbox_to_anchor=(1.2, 1), fancybox=True, shadow=True)

    ax = fig3.gca()
    ax.set_xlabel('Real')
    ax.set_ylabel('Imag')
    ax.grid()
    # ax.legend(bbox_to_anchor=(1.2, 1), fancybox=True, shadow=True)

    for mode in modes:
        ax = fig1.gca()
        ax.plot(mode['VELOCITY'],
                mode['DAMPING'],
                '.-',
                label='Mode {}; Mach {}'.format(mode['MODE'], mode['MACH NUMBER']))
        ax.legend(bbox_to_anchor=(1.1, 1), fancybox=True, shadow=True)

        ax = fig2.gca()
        ax.plot(mode['VELOCITY'],
                mode['FREQUENCY'],
                '.-',
                label='Mode {}; Mach {}'.format(mode['MODE'], mode['MACH NUMBER']))
        ax.legend(bbox_to_anchor=(1.1, 1), fancybox=True, shadow=True)

        ax = fig3.gca()
        ax.plot(mode['REALEIGVAL'],
                mode['IMAGEIGVAL'],
                label='Mode {}; Mach {}'.format(mode['MODE'], mode['MACH NUMBER']))
        ax.legend(bbox_to_anchor=(1.1, 1), fancybox=True, shadow=True)
    plt.show()


FLUTTER_DATA_KEYS = {'VELOCITY': 'Velocity',
                     'DAMPING': 'Damping',
                     'FREQUENCY': 'Frequency',
                     'REALEIGVAL': 'Real Eigenvalue',
                     'IMAGEIGVAL': 'Imag Eigenvalue'}


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


def main():
    base_path = r'c:\users\victor\pycharmprojects\aero-5-mesh-gen'
    input_file = os.path.join(base_path, 'input-model.bdf')
    output_file = os.path.join(base_path, 'output-model.bdf')
    nastran_exe = r'c:\FEMAPv112\nastran\bin\nastran64.exe'
    analysis, spanel = femap_to_nastran(input_file)
    gen_aero_bdf(input_file, analysis, spanel, output_file)
    run_nastran(output_file, nastran_cmd=nastran_exe, keywords=['old=no'])
    modes, critical_modes, flutter = read_f06(output_file.replace('.bdf', '.f06'), analysis)
    plot_flutter_data(modes, analysis)
    plot_critical_flutter_data(critical_modes)
    # export_flutter_data(modes, critical_modes, flutter, analysis, '')
    return modes, critical_modes, flutter, analysis, spanel


if __name__ == '__main__':
    modes, critical_modes, flutter_speeds, analysis, spanel = main()
    # base_path = r'c:\users\victor\pycharmprojects\aero-5-mesh-gen'
    # input_file = os.path.join(base_path, 'input-model.bdf')
    # output_file = os.path.join(base_path, 'output-model.bdf')
    # nastran_exe = r'c:\FEMAPv112\nastran\bin\nastran64.exe'
    # analysis = AeroAnalysis5(Femap())
    # analysis.machs = [2., 3.]
    # analysis.velocities = list(range(9))
    # analysis.n_modes = 15
    # modes, critical_modes, flutter = read_f06(output_file.replace('.bdf', '.f06'), analysis)
    # export_flutter_data(modes, critical_modes, flutter, analysis, os.path.join(base_path, 'test.xlsx'))
