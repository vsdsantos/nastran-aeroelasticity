[![DeepSource](https://static.deepsource.io/deepsource-badge-light-mini.svg)](https://deepsource.io/gh/zuckberj/nastran-aero-flutter/?ref=repository-badge)
# nastran-aero-flutter

This project is intended to analyse the Supersonic Panel Flutter using the NASTRAN software.

The project uses the pyNastran and the python scientific packeges (i.e scipy, numpy, matplotlib).

Currently, the focus is to use the aerodynamic Piston Theory, available on NASTRAN with the CAERO5 element.
But it can be extended to use with any aerodynamic element.

This software is result of a research project of the Department of Mechanical Engineering
at the Federal University of Minas Gerais (UFMG).

## Use

An exemple of utilization is on the `run_analysis.py` script.

First it generates the plate structure and required properties.

```python
import numpy as np
from nastran.structures.panel import LaminatedStructuralPlate
from nastran.structures.composite import OrthotropicMaterial

a, b = 100, 100

p1 = np.array([0, 0, 0])
p2 = p1 + np.array([a, 0, 0])
p3 = p1 + np.array([a, b, 0])
p4 = p1 + np.array([0, b, 0])

cfrp = OrthotropicMaterial(1, 54000., 18000., 0.3, 7200., 2.6e-9)

nchord, nspan = 10, 10

lam = LaminatedStructuralPlate.create_sawyer_plate(p1, p2, p3, p4, nspan, nchord, 1, 45, 6, 0.1, cfrp)
```

Then you can add the analysis properties for SOL 145 Aeroelastic Dynamic Flutter. The PanelFlutterPistonAnalysisModel class is a wrapper of the pyNastran's BDF class.

```python
from nastran.aero.analysis.panel_flutter import PanelFlutterPistonAnalysisModel

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
```

You can add "super" panels, that is just a wrapper of CAEROx elements that make one element.

```python
from nastran.aero.superpanels import SuperAeroPanel5

spanel_p = SuperAeroPanel5(1, p1, p2, p3, p4, nchord, nspan, theory='VANDYKE')
analysis.add_superpanel(spanel_p)
```

You can set multiple subcases for example varing the boundary conditions.

```python
cases_labels = {
    1: "Loaded edges SS & unloaded edges SS",
    2: "Loaded edges SS & unloaded edges CP",
    3: "Loaded edges SS & unloaded edges SS/CP",
}

spc_cases = {
    1: ('123', '123', '123', '123'),             # loaded edges SS, unloaded edges SS
    2: ('123', '123', '123456', '123456'),       # loaded edges SS, unloaded edges CP
    3: ('123', '123', '123', '123456'),          # loaded edges SS, unloaded edges SS/CP
}

for i, spcs in spc_cases.items():
    spc_id = analysis.idutil.get_next_sid()
    for comp, nds in zip(list(spcs), lam.limit_nodes()):
        if comp == '':
            continue
        analysis.model.add_spc1(spc_id, comp, nds, comment=cases_labels[i])
    sub_config = {
        'LABEL': cases_labels[i],
        'SPC': spc_id,
    }
    analysis.create_subcase_from_dict(PanelFlutterSubcase, i, sub_config)
```
Then you must write all cards to the BDF object and export the file.

```python
analysis.write_cards()
analysis.model.write_bdf('pflutter.bdf', enddata=True)
```

Then you can run the analysis and post-processes.

## Outputs

The postprocessing generates `DataFrame`s objects from the .f06 result files.

```py

from nastran.aero.post import read_f06, get_critical_roots, plot_vf_vg

df = read_f06("pflutter.f06")

critic_df = get_critical_roots(df)

fig = plot_vf_vg(df.xs((1,3.5))) # Subcase, Mach
fig.show()

```

And Plots

![V-f](https://i.imgur.com/4yHdjqo.png)

![V-g](https://i.imgur.com/fnTF7IR.png)
