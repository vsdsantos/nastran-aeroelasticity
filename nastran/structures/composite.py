
from typing import List
from pyNastran.bdf.cards.properties.shell import PCOMP
from pyNastran.bdf.cards.materials import MAT8


class OrthotropicMaterial:

    def __init__(self, mid, E1, E2, nu12, G12, rho) -> None:
        self.mid = mid
        self.E1 = E1
        self.E2 = E2
        self.nu12 = nu12
        self.G12 = G12
        self.rho = rho

    def to_mat8(self) -> MAT8:
        return MAT8(self.mid, self.E1, self.E2, self.nu12, self.G12, self.rho)


class Sheet:

    def __init__(self, mat: OrthotropicMaterial, thick: float, theta=0.0) -> None:
        self.mat = mat
        self.thick = thick
        self.theta = theta

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
    def create_sawyer_ply(cls, pid, theta, nplies, thick, mat):
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