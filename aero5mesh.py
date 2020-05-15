import os
import pathlib

from pyNastran.utils.nastran_utils import run_nastran

from aero.AeroelasticAnalysis import PanelFlutterAnalysisModel
from aero.AeroelasticPanels import SuperAeroPanel5
from aero.AeroelasticPostProcessing import plot_flutter_data, plot_critical_flutter_data, read_f06
from femap.femap import Femap

# This script analyzes a panel flutter with Piston Theory on Nastran.

if __name__ == '__main__':
    # paths for input, output and the nastran exec
    base_path = pathlib.Path().absolute()
    input_file = os.path.join(base_path, r'sandbox\input-model.bdf')
    output_file = os.path.join(base_path, r'sandbox\output-model.bdf')
    nastran_exe = r'D:\Programs\MSC.Software\NaPa_SE\2019fp1\Nastran\bin\nastran.exe'

    # init the analysis and the femap interface
    analysis = PanelFlutterAnalysisModel()
    femap = Femap()

    femap.export_bdf_model(input_file)  # export loaded bdf model from femap
    analysis.import_from_bdf(input_file)  # import bdf model

    analysis.load_analysis_from_yaml(os.path.join(base_path, r'analysis.yml'))  # import analysis setup

    spanel = SuperAeroPanel5()  # init panel
    spanel.init_from_femap(femap)  # popup femap interface to insert the location and config of the panel

    analysis.add_superpanel(spanel)
    analysis.write_cards()  # write the panels on the pyNastran bdf interface

    analysis.export_to_bdf(output_file)  # exports to bdf file

    # run nastran
    run_nastran(output_file, nastran_cmd=nastran_exe, keywords=['old=no'])

    # plots on console and matplotlib
    for key, subcase in analysis.subcases.items():
        print('SUBCASE {}'.format(key))
        modes, critical_modes, flutter = read_f06(output_file.replace('.bdf', '.f06'), subcase)
        searched_modes = list(filter(lambda m: m['MODE'] <= subcase.n_modes, modes))
        plot_flutter_data(searched_modes, subcase)
        searched_crit_modes = list(filter(lambda m: m['MODE'] <= subcase.n_modes, critical_modes))
        if len(searched_crit_modes):
            # plot_critical_flutter_data(searched_crit_modes)
            for flut in flutter:
                print('Flutter found on MODE {}'.format(flut['MODE']))
                print('\tMACH \t{}'.format(flut['MACH']))
                print('\tVELOCITY \t{}'.format(flut['VELOCITY']))
                print('\tLAMBDA \t{}'.format(flut['LAMBDA']))
        else:
            print('No flutter encountered in subcase {}.'.format(key))
        # export_flutter_data(modes, critical_modes, flutter, subcase[1], os.path.join(base_path, 'output-model.xlsx'))
