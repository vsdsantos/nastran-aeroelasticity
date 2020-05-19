import os
import pathlib

import numpy as np

from pyNastran.utils.nastran_utils import run_nastran

from aero.AeroelasticAnalysis import PanelFlutterAnalysisModel
from aero.AeroelasticPanels import SuperAeroPanel5, SuperAeroPanel1
from aero.AeroelasticPostProcessing import plot_flutter_data, plot_critical_flutter_data, read_f06
from femap.femap import Femap


def panel_flutter_analysis(analysis, output_file):
    for key, subcase in analysis.subcases.items():
        print('SUBCASE {}'.format(key))
        modes, critical_modes, flutter = read_f06(output_file.replace('.bdf', '.f06'), subcase)
        searched_modes = list(filter(lambda m: m['MODE'] <= subcase.n_modes, modes))
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

# This script analyzes a panel flutter with Piston Theory and ZONA51 on Nastran.
#%% paths for input, output and the nastran exec
base_path = pathlib.Path().absolute()
input_file = os.path.join(base_path, r'sandbox\input-model.bdf')
output_file = os.path.join(base_path, r'sandbox\output-model.bdf')
nastran_exe = r'D:\Programs\MSC.Software\NaPa_SE\2019fp1\Nastran\bin\nastran.exe'

# init the analysis
analysis = PanelFlutterAnalysisModel()
analysis.load_analysis_from_yaml(os.path.join(base_path, r'analysis.yml'))  # import analysis setup

# init femap interface
femap = Femap()
femap.export_bdf_model(input_file)  # export loaded bdf model from femap

#%% Piston Theory analysis
analysis.import_from_bdf(input_file)  # import bdf model

spanel_p = SuperAeroPanel5(1)  # init panel
spanel_p.init_from_femap(femap)  # popup femap interface to insert the location and config of the panel

analysis.add_superpanel(spanel_p)
analysis.write_cards()  # write the panels on the pyNastran bdf interface

analysis.export_to_bdf(output_file)  # exports to bdf file

# run nastran
run_nastran(output_file, nastran_cmd=nastran_exe, keywords=['old=no'])

# output results
panel_flutter_analysis(analysis, output_file)

#%% now with the ZONA51 theory
analysis = PanelFlutterAnalysisModel()
analysis.load_analysis_from_yaml(os.path.join(base_path, r'analysis.yml'))
analysis.import_from_bdf(input_file)  # reset the bdf file

# analysis.import_from_bdf(input_file, reset_bdf=True)  # reset the bdf file

analysis.subcases[1].method = 'PK'

# you may supply a value of minimum Mach number in your analysis, by default this value is sqrt(2) (i.e. 45° -> square)
spanel = SuperAeroPanel1(1, np.min(analysis.subcases[1].machs))

# just copy the configuration
# spanel.p1 = spanel_p.p1
# spanel.p2 = spanel_p.p2
# spanel.p3 = spanel_p.p3
# spanel.p4 = spanel_p.p4
# spanel.nchord = spanel_p.nchord
# spanel.nspan = spanel_p.nspan

spanel.init_from_femap(femap)
analysis.add_superpanel(spanel)

analysis.write_cards()
analysis.export_to_bdf(output_file)

nastran_exe = r'C:\FEMAPv112\nastran\bin\nastran.exe'
run_nastran(output_file, nastran_cmd=nastran_exe, keywords=['old=no'])

panel_flutter_analysis(analysis, output_file)
