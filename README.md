# py-nastran-aero-flutter

This project is intended to analyse the Supersonic Panel Flutter using the NASTRAN software.

The project uses the pyNastran, the Femap's COM interface and the python scientific packeges (i.e scipy, numpy, matplotlib).

Currently, the focus is to use the aerodynamic Piston Theory, available on NASTRAN with the CAERO5 element.
But it can be extended to use with any aerodynamic element.

This software is result of a research project of the Department of Mechanical Engineering
at the Federal University of Minas Gerais (UFMG).

## Instalation

To use the Femap interface you must `pip install pywin32` and run the script
```python3
import sys
from win32com.client import makepy
sys.argv = ["makepy", "-o PyFemap.py", r"{YOUR FEMAP INSTALATION DIRECTORY}\femap.tlb"]
makepy.main()
```
source: https://community.sw.siemens.com/s/article/writing-the-femap-api-in-python

## Use

An exemple of utilization is on the `aero5mesh.py` script.

First it exports some BDF file from Femap. The Femap instance must be running,
and some analysis already made (e.g. Normal Mode Analysis).

```python
femap = Femap()
femap.export_bdf_model(input_file)
```
Then you can import he file to the analysis object. The AeroelasticAnalysis class is a wrapper of the pyNastran's BDF class.

```python
analysis = AeroelasticAnalysis()
analysis.import_from_bdf(input_file)
```
You can import the main parameter of analysis from a YAML file with this.

```python
analysis.load_analysis_from_yaml(analysis_file)
```

The file must follow this template.

TODO: Add template.

You can add "super" panels, that is just a wrapper of CAEROx elements that make one element.
These panels properties can be setted from Femap interface.

```python
spanel = SuperAeroPanel5()
spanel.init_from_femap(femap)
analysis.add_superpanel(spanel)
```

After adding all panels and properties of the analysis you can write all properties to the BDF instance and export the BDF file.

```python
analysis.write_cards(1)
analysis.export_to_bdf(output_file)
```

Then you can run the analysis and post-processes.
