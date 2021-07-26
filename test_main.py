#%%
import numpy as np

from nastran.structures.panel import StructuralPlate, LaminatedStructuralPlate
from nastran.structures.composite import OrthotropicMaterial
from nastran.aero.superpanels import SuperAeroPanel5
from nastran.aero.analysis.panel_flutter import PanelFlutterAnalysisModel, PanelFlutterSubcase

#%%

## Setup structural model
a, b = 100, 100
p1 = np.array([0, 0, 0])
p2 = p1 + np.array([a, 0, 0])
p3 = p1 + np.array([a, b, 0])
p4 = p1 + np.array([0, b, 0])

# plate = StructuralPlate(p1, p2, p3, p4, 3, 3, 1)

cfrp = OrthotropicMaterial(1, 10, 10, 0.3, 10, 1)
lam = LaminatedStructuralPlate.create_sawyer_plate(p1, p2, p3, p4, 3, 3, 1, 45, 6, 0.1, cfrp)


#%%

config = {
    'type': 'PANELFLUTTER',
    'vref': 1000.,                      # used to calculate the non-dimensional dynamic pressure must be the same in control case (mm/s in the case)
    'ref_rho': 1.225e-12,               # air density reference (ton/mm^3 in the case)
    'ref_chord': 300.,                  # reference chord (mm in the case)
    'n_modes': 15,                      # number searched modes in modal analysis
    'frequency_limits': 
        [.0, 3000.],                    # the range of frequency (Hz) in modal analysis
    'method': 'PK',                     # the method for solving flutter (it will determine the next parameters
    'densities_ratio': [.5],            # rho/rho_ref -> 1/2 simulates the "one side flow" of the panel
    'machs': [3.5, 4.5, 5.5, 6.5],      # Mach number
    'alphas': [.0, .0, .0, .0],         # AoA (°) -> 0 is more conservative
    'reduced_frequencies': 
        [.001, .01, .1, .2, .4, .8],    # reduced frequencies (k)
    'velocities':                       # velocities (mm/s in the case)
        np.linspace(0, 100, 10)*1000
    }


analysis = PanelFlutterAnalysisModel(lam.bdf)

#%%

analysis.create_subcase_from_dict(1, config)

#
spanel_p = SuperAeroPanel5(1)  # init panel
xyz = [analysis.model.nodes[i].xyz for i in corner_nodes]
spanel_p.set_panel_limits(*xyz)
a = 20
b_opt = {1: 20, 2: 10, 6: 6, 7: 20, 0.5: 40}
spanel_p.set_mesh_size(b_opt[ab], a)
spanel_p.init()

analysis.add_superpanel(spanel_p)
analysis.write_cards()  # write the panels on the pyNastran bdf interface

spanel_p = SuperAeroPanel5()  # init panel
xyz = [analysis.model.nodes[i].xyz for i in corner_nodes]
spanel_p.set_panel_limits(*xyz)
a = 20
b_opt = {1: 20, 2: 10, 6: 6, 7: 20, 0.5: 40}
spanel_p.set_mesh_size(b_opt[ab], a)
spanel_p.init()

analysis.add_superpanel(spanel_p)
analysis.write_cards()  # write the panels on the pyNastran bdf interface

del analysis.model.case_control_deck.subcases[1]

for i, label in cases.items():
    analysis.model.case_control_deck.create_new_subcase(i)
    analysis.model.case_control_deck.add_parameter_to_local_subcase(i, 'LABEL = {}'.format(label))
    analysis.model.case_control_deck.add_parameter_to_local_subcase(i, 'METHOD = 1')
    analysis.model.case_control_deck.add_parameter_to_local_subcase(i, 'FMETHOD = 1')
    analysis.model.case_control_deck.add_parameter_to_local_subcase(i, 'ECHO=NONE')
    # analysis.model.case_control_deck.add_parameter_to_local_subcase(i, 'DISP=ALL')
    analysis.model.case_control_deck.add_parameter_to_local_subcase(i, 'SPC = {}'.format(i))

# analysis.model.add_param('POST', [-1])
analysis.model.add_param('VREF', [1000.0])
analysis.model.add_param('COUPMASS', [1])
analysis.model.add_param('LMODES', [20])

for i, spcs in spc_cases.items():
    for comp, nds in zip(list(spcs), edges_nodes_ids.values()):
        if comp == '':
            continue
        analysis.model.add_spc1(i, comp, nds, comment=cases[i])

prefix = "PFLUTTER-CFRP-AB-{}-NPLIES-{}-SYM".format(ab, nplies)

case_files = dict()
D11 = 0
D11s = dict()

for i, theta in enumerate(theta_range):
    filename = "{prefix}-THETA-{}.bdf".format(theta, prefix=prefix)
    pcomp = create_pcomp(analysis, theta, thick, nplies)
    analysis.model.properties[pcomp.pid] = pcomp
    analysis.model.properties[pcomp.pid].cross_reference(analysis.model)
    D = analysis.model.properties[pcomp.pid].get_individual_ABD_matrices()[2]
    
    if theta == 0:
        D11 = D[0][0]
    
    D11s[theta] = D[0][0]
        
    analysis.export_to_bdf("analysis-bdf/"+filename)  # exports to bdf file
    case_files[i+1] = filename

data_rows_size = len(machs)*n_vel*len(cases)*len(theta_range)*15

print(D11s)

print("Expected data rows: {} rows.".format(data_rows_size))
print("Expected data size: {} MB".format(data_rows_size*64*7/8e6))

print("D11(theta=0) = {}".format(D11))    