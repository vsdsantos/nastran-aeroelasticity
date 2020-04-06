import os

from pyNastran.op2.op2 import read_op2
import numpy as np

base_path = r'c:\users\victor\pycharmprojects\aero-5-mesh-gen'
output_file = base_path + r'\output-model.op2'
matrices = read_op2(output_file)
