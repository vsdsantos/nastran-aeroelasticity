
from pyNastran.bdf.bdf import BDF

from nastran.geometry.panels import RectangularPlate

import numpy as np


class StructuralPlate(RectangularPlate):

    def __init__(self, p1, p2, p3, p4, nspan, nchord) -> None:
        super().__init__(p1, p2, p3, p4)
        self.bdf = BDF()
        self.nspan = nspan
        self.nchord = nchord

    def set_mesh_size(self, nspan, nchord) -> None:
        self.nspan = nspan
        self.nchord = nchord
    
    def generate_mesh(self) -> None:
        pass
