
from pyNastran.bdf.cards.materials import MAT8, MAT5, MAT2, MAT1

class IsotropicMaterial:
    
    def __init__(self, mid, E, nu, G, rho, alpha=None) -> None:
        self.mid = int(mid)
        self.E = float(E)
        self.nu = float(nu)
        self.G = float(G)
        self.rho = float(rho)
        self.alpha = float(alpha) if alpha else None

    def to_mat1(self) -> MAT1:
        return MAT1(self.mid, self.E, self.G, self.nu, rho=self.rho, a=self.alpha)
    

class OrthotropicMaterial:

    def __init__(self, mid, E1, E2, nu12, G12, rho, alpha1=None, alpha2=None) -> None:
        self.mid = int(mid)
        self.E1 = float(E1)
        self.E2 = float(E2)
        self.nu12 = float(nu12)
        self.G12 = float(G12)
        self.rho = float(rho)
        self.alpha1 = float(alpha1) if alpha1 else None
        self.alpha2 = float(alpha2) if alpha2 else None

    def to_mat8(self) -> MAT8:
        return MAT8(self.mid, self.E1, self.E2, self.nu12, g12=self.G12, rho=self.rho, a1=self.alpha1, a2=self.alpha2)
    
    # def to_mat5(self) -> MAT5:
        # return MAT5(self.mid, self.alpha1, self.alpha2)