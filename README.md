# py-nastran-aero-flutter

This project is intended to analyse the Supersonic Panel Flutter using the NASTRAN software.

The project uses the pyNastran, the Femap's COM interface and the python scientific packeges (i.e scipy, numpy, matplotlib)

Currently, the focus is to use the aerodynamic Piston Theory, available on NASTRAN, to model the problem,
but it can be extended to use with any aerodynamic element.

***

To use the Femap interface you must `pip install pywin32` and run the script
```python
import sys
from win32com.client import makepy
sys.argv = ["makepy", "-o Pyfemap.py", r"C:\FEMAPv1132\femap.tlb"]
makepy.main()
```
source: https://community.sw.siemens.com/s/article/writing-the-femap-api-in-python
