
from typing import List
from pyNastran.bdf.cards.properties.shell import PCOMP
from pyNastran.bdf.cards.materials import MAT8, MAT5, MAT2

from nastran.structures.material import OrthotropicMaterial

class Sheet:

    def __init__(self, mat: OrthotropicMaterial, thick: float, theta=0.0) -> None:
        self.mat = mat
        self.thick = float(thick)
        self.theta = float(theta)

class Ply:

    def __init__(self, pid, sheets: List[Sheet]) -> None:
        self.pid = pid
        self.sheets = sheets
    
    @property
    def mids(self) -> List[int]:
        return [s.mat.mid for s in self.sheets]
    
    @property
    def thicknesses(self) -> List[float]:
        return [s.thick for s in self.sheets]
    
    @property
    def thetas(self) -> List[float]:
        return [s.theta for s in self.sheets]
    
    @property
    def N(self):
        return len(self.sheets)

    def get_mat(self, mid):
        return next(filter(lambda s: s.mat.mid == mid, self.sheets)).mat

    def to_pcomp(self):
        return PCOMP(self.pid, self.mids, self.thicknesses, self.thetas)
    
    @classmethod
    def angle_ply(cls, pid, theta, nplies, thick, mat):
        # theta, -theta, -theta, theta
        # assert nplies % 2 == 0
        thetas = []
        for i in range(int(nplies/2)):
            if i % 2 == 0:
                thetas.append(float(-theta))
            else:
                thetas.append(float(theta))
        thetas =  thetas[::-1] + thetas
        return Ply(pid, [Sheet(mat, thick, angle) for angle in thetas])