# %%

from nastran.aero.analysis.flutter import FlutterSubcase
import numpy as np

from nastran.structures.panel import StructuralPlate, LaminatedStructuralPlate
from nastran.structures.composite import OrthotropicMaterial
from nastran.aero.superpanels import SuperAeroPanel5
from nastran.aero.analysis.panel_flutter import PanelFlutterPistonAnalysisModel, PanelFlutterSubcase


# %%

## Setup structural model
a, b = 100, 100
p1 = np.array([0, 0, 0])
p2 = p1 + np.array([a, 0, 0])
p3 = p1 + np.array([a, b, 0])
p4 = p1 + np.array([0, b, 0])

# plate = StructuralPlate(p1, p2, p3, p4, 3, 3, 1)

cfrp = OrthotropicMaterial(1, 54000, 18000, 0.3, 7200, 2.6e-9)
nchord, nspan = 10, 10
lam = LaminatedStructuralPlate.create_sawyer_plate(p1, p2, p3, p4, nspan, nchord, 1, 45, 6, 0.1, cfrp)


# %%

config = {
    'vref': 1000.,                      # used to calculate the non-dimensional dynamic pressure must be the same in control case (mm/s in the case)
    'ref_rho': 1.225e-12,               # air density reference (ton/mm^3 in the case)
    'ref_chord': 300.,                  # reference chord (mm in the case)
    'n_modes': 15,                      # number searched modes in modal analysis
    'frequency_limits': 
        [.0, 3000.],                    # the range of frequency (Hz) in modal analysis
    'method': 'PK',                     # the method for solving flutter (it will determine the next parameters
    'densities_ratio': [.5],            # rho/rho_ref -> 1/2 simulates the "one side flow" of the panel (? reference ?)
    'machs': [3.5, 4.5, 5.5, 6.5],      # Mach numbers
    'alphas': [.0, .0, .0, .0],         # AoA (°) -> 0 is more conservative (? reference ?)
    'reduced_frequencies': 
        [.001, .01, .1, .2, .4, .8],    # reduced frequencies (k) (check influence)
    'velocities':                       # velocities (mm/s in the case)
        np.linspace(10, 100, 10)*1000,
}

params =  {
    'VREF': 1000.0,
    'COUPMASS': 1,
    'LMODES': 20,
    # 'POST': [-1]
}

analysis = PanelFlutterPistonAnalysisModel(lam.bdf, params=params)
analysis.set_global_case_from_dict(config)


# %%

spanel_p = SuperAeroPanel5(1, p1, p2, p3, p4, nchord, nspan, theory='VANDYKE')
analysis.add_superpanel(spanel_p)

cases_labels = {
    1: "Loaded edges SS & unloaded edges SS",
    2: "Loaded edges SS & unloaded edges CP",
    3: "Loaded edges SS & unloaded edges SS/CP",
    4: "Loaded edges SS & unloaded edges SS/FF",
    5: "Loaded edges SS & unloaded edges CP/FF",
    6: "Loaded edges SS & unloaded edges FF",
    7: "Loaded edges CP & unloaded edges SS",
    8: "Loaded edges CP & unloaded edges CP",
    9: "Loaded edges CP & unloaded edges SS/CP",
    10: "Loaded edges CP & unloaded edges SS/FF",
    11: "Loaded edges CP & unloaded edges CP/FF",
    12: "Loaded edges CP & unloaded edges FF",
}

spc_cases = {
    1: ('123', '123', '123', '123'),             # loaded edges SS, unloaded edges SS
    2: ('123', '123', '123456', '123456'),       # loaded edges SS, unloaded edges CP
    # 3: ('123', '123', '123', '123456'),          # loaded edges SS, unloaded edges SS/CP
    # 4: ('123', '123', '123', ''),                # loaded edges SS, unloaded edges SS/FF
    # 5: ('123', '123', '123456', ''),             # loaded edges SS, unloaded edges CP/FF
    # 6: ('123', '123', '', ''),                   # loaded edges SS, unloaded edges FF
    # 7: ('123456', '123456', '123', '123'),       # loaded edges CP, unloaded edges SS
    # 8: ('123456', '123456', '123456', '123456'), # loaded edges CP, unloaded edges CP
    # 9: ('123456', '123456', '123', '123456'),    # loaded edges CP, unloaded edges SS & CP
    # 10:('123456', '123456', '123', ''),          # loaded edges CP, unloaded edges SS & FF
    # 11:('123456', '123456', '123456', ''),       # loaded edges CP, unloaded edges CP & FF
    # 12:('123456', '123456', '', ''),             # loaded edges CP, unloaded edges FF
}


limit_nodes = [
    lam.chordwise_nodes[0],
    lam.chordwise_nodes[-1],
    lam.spanwise_nodes[0][1:-1],
    lam.spanwise_nodes[-1][1:-1],
    ]

for i, spcs in spc_cases.items():
    spc_id = analysis.idutil.get_next_sid()
    for comp, nds in zip(list(spcs), list(limit_nodes)):
        if comp == '':
            continue
        analysis.model.add_spc1(spc_id, comp, nds, comment=cases_labels[i])
    sub_config = {
        'LABEL': cases_labels[i],
        'SPC': spc_id,
    }
    analysis.create_subcase_from_dict(PanelFlutterSubcase, i, sub_config)


# %%

analysis.write_cards()

# %%
analysis.model.write_bdf('test.bdf', enddata=True)


