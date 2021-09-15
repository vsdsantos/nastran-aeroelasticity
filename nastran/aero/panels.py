
from abc import abstractmethod

from nastran.geometry.panels import RectangularPlate

class AeroPanel(RectangularPlate):
    """
    Aerodynamic Panel with N-Chord subdivision and M-Span subdivisions (all equally),
    and IDs of the structural nodes, or the ID of the set, that it will correlate.
    """

    def __init__(self, p1, p2, p3, p4, nchord, nspan, structural_ids=None):
        super().__init__(p1, p2, p3, p4)
        self.nchord = nchord
        self.nspan = nspan
        self.structural_ids = structural_ids
    

    def set_mesh_size(self, nspan, nchord) -> None:
        self.nspan = nspan
        self.nchord = nchord

    @abstractmethod
    def set_panel_properties(self, *args):
        pass


class AeroPanel1(AeroPanel):
    """
    """

    def __init__(self, p1, p2, p3, p4, nchord, nspan):
        super().__init__(p1, p2, p3, p4, nchord, nspan)


class AeroPanel5(AeroPanel):
    """
    Aerodynamic Panel using the Piston Theory (CEARO5 Nastran's element).
    """

    THEORIES = {'PISTON': 0, 'VANDYKE': 1, 'VDSWEEP': 2}

    def __init__(self, p1, p2, p3, p4, nchord, nspan,
            thickness_integrals=None,
            control_surface_ratios=None,
            theory='PISTON'):
        super().__init__(p1, p2, p3, p4, nchord, nspan)
        self.set_panel_properties(theory, thickness_integrals, control_surface_ratios)

    def set_panel_properties(self, theory, thickness_int, control_surf):        
        # assert control_surf == None or len(control_surf) == self.nspan

        self.thickness_integrals = thickness_int
        self.control_surface_ratios = control_surf
        if theory not in self.THEORIES:
            raise Exception('Theory {} for CAERO5 is not present.'.format(theory))
        self.theory = self.THEORIES[theory]

