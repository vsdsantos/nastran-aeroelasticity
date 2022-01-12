
from typing import List
from pyNastran.bdf.bdf import BDF

from nastran.geometry.panels import RectangularPlate
from nastran.structures.composite import Ply, OrthotropicMaterial, Sheet
from pyNastran.bdf.cards.properties.shell import PSHELL
from nastran.utils import IdUtility

import numpy as np


class StructuralPlate(RectangularPlate):

    def __init__(self, p1, p2, p3, p4, nspan, nchord, pid, firstNid=1, firstEid=1) -> None:
        super().__init__(p1, p2, p3, p4)
        self.bdf = BDF()
        self.nspan = nspan
        self.nchord = nchord
        self.pid = pid
        self.firstNid = firstNid
        self.firstEid = firstEid

    def __repr__(self) -> str:
        return self.bdf.get_bdf_stats()

    def limit_nodes(self, mode="a"): 
        if mode == "a":
            return [
                self.chordwise_nodes[0],
                self.chordwise_nodes[-1],
                self.spanwise_nodes[0],
                self.spanwise_nodes[-1],
            ]
        raise Exception("Not implemented")

    @property
    def corner_nodes(self):
        n1 = self.firstNid
        n4 = n1 + self.nspan
        n2 = n1 + self.nspan*(self.nchord+1)
        n3 = n2 + self.nspan
        return n1, n2, n3, n4

    @property
    def chordwise_nodes(self):
        n0 = self.firstNid
        nodes = []
        for i in range(self.nchord+1):
            n1 = n0 + i*(self.nchord+1)
            nodes.append(list(range(n1, n1+self.nspan+1)))
        return nodes

    @property
    def spanwise_nodes(self):
        n0 = self.firstNid
        nodes = []
        for i in range(self.nspan+1):
            s = self.nspan
            n1 = n0 + i
            nds = [n1+s*j+1*j for j in range(0,self.nchord+1)]
            nodes.append(nds)
        return nodes
    
    @property
    def corner_elements(self):
        pass

    @property
    def chordwise_elements(self):
        pass

    @property
    def spanwise_elements(self):
        pass

    def set_mesh_size(self, nspan, nchord) -> None:
        self.nspan = nspan
        self.nchord = nchord

    def _generate_material(self) -> None:
        pass

    def _generate_property(self) -> None:
        pass

    def _generate_grid(self):
        counter = 0
        for i in range(self.nchord+1):
            for j in range(self.nspan+1):
                xyz = self.p1 + self.d12*i/self.nchord + self.d14*j/self.nspan
                self.bdf.add_grid(self.firstNid + counter, xyz)
                counter += 1

    def _generate_elements(self):
        counter = 0
        for i in range(self.nchord):
            for j in range(self.nspan):
                g1 = self.firstNid + i + j + i*self.nspan
                g2 = g1 + 1
                g3 = g2 + self.nspan + 1
                g4 = g1 + self.nspan + 1
                self.bdf.add_cquad4(self.firstEid + counter, self.pid, [g1, g2, g3, g4], theta_mcid=90.0)
                counter += 1

    def generate_mesh(self) -> BDF:
        self._generate_material()
        self._generate_property()
        self._generate_grid()
        self._generate_elements()
        

class IsotropicPlate(StructuralPlate):
    
    def __init__(self, p1, p2, p3, p4, nspan, nchord, prop, mat, **args) -> None:
        super().__init__(p1, p2, p3, p4, nspan, nchord, prop.pid, **args)
        self.prop = prop
        self.mat = mat

    def _generate_material(self) -> None:
        self.bdf._add_structural_material_object(self.mat.to_mat1())
        
    def _generate_property(self) -> None:
        self.bdf.properties[self.pid] = self.prop

    @classmethod
    def create_plate(cls, p1, p2, p3, p4, nspan, nchord, pid, thick, mat):
        shell = PSHELL(pid, mat.mid, thick, mat.mid)
        plate = IsotropicPlate(p1, p2, p3, p4, nspan, nchord, shell, mat)
        plate.generate_mesh()
        return plate
    
class LaminatedStructuralPlate(StructuralPlate):

    def __init__(self, p1, p2, p3, p4, nspan, nchord, ply: Ply, **args) -> None:
        super().__init__(p1, p2, p3, p4, nspan, nchord, ply.pid, **args)
        self.ply = ply
    
    def _generate_material(self) -> None:
        mids = list(set(self.ply.mids)) # unique
        for mid in mids:
            mat = self.ply.get_mat(mid)
            self.bdf._add_structural_material_object(mat.to_mat8())
            # if mat.alpha1 or mat.alpha2:
                # self.bdf._add_thermal_material_object(mat.to_mat5())

    def _generate_property(self) -> None:
        self.bdf.properties[self.pid] = self.ply.to_pcomp()

    @classmethod
    def create_sawyer_plate(cls, p1, p2, p3, p4, nspan, nchord, pid, theta, nplies, thick, mat):
        ply = Ply.angle_ply(pid, theta, nplies, thick, mat)
        plate = LaminatedStructuralPlate(p1, p2, p3, p4, nspan, nchord, ply)
        plate.generate_mesh()
        return plate