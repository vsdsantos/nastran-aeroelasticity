from aero.AeroelasticAnalysis import AeroelasticAnalysis
from aero.AeroelasticPanels import SuperAeroPanel5
from aero.AeroelasticPostProcessing import plot_flutter_data, plot_critical_flutter_data, export_flutter_data, read_f06
from pyNastran.utils.nastran_utils import run_nastran
from femap.femap import Femap
import pathlib
import os

if __name__ == '__main__':
    base_path = pathlib.Path().absolute()
    input_file = os.path.join(base_path, 'input-model.bdf')
    output_file = os.path.join(base_path, 'output-model.bdf')
    nastran_exe = r'D:\Programs\MSC.Software\NaPa_SE\2019fp1\Nastran\bin\nast20191.exe'

    analysis = AeroelasticAnalysis()
    femap = Femap()
    femap.export_bdf_model(input_file)
    analysis.import_from_bdf(input_file)
    analysis.load_analysis_from_yaml(os.path.join(base_path, r'analysis.yml'))
    spanel = SuperAeroPanel5(femap)
    spanel.init_from_femap()

    analysis.add_superpanel(spanel)
    analysis.write_cards(1)
    analysis.export_to_bdf(output_file)

    run_nastran(output_file, nastran_cmd=nastran_exe, keywords=['old=no'])

    for key, subcase in analysis.subcases.items():
        modes, critical_modes, flutter = read_f06(output_file.replace('.bdf', '.f06'), subcase)
        searched_modes = list(filter(lambda m: m['MODE'] <= subcase.n_modes, modes))
        plot_flutter_data(searched_modes, subcase)
        searched_crit_modes = list(filter(lambda m: m['MODE'] <= subcase.n_modes, critical_modes))
        if len(searched_crit_modes):
            plot_critical_flutter_data(searched_crit_modes)
        else:
            print('No flutter encountered in this analysis.')
        # export_flutter_data(modes, critical_modes, flutter, analysis.subcases[1], os.path.join(base_path, 'output-model.xlsx'))
