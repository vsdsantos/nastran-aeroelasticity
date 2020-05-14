from femap.femap import Femap
import numpy as np
from abc import abstractmethod


class Panel:
    """
    Generic Panel defined by four points in the space and a n x m mesh.
    """
    def __init__(self, p1=None, p2=None, p3=None, p4=None, nchord=None, nspan=None):
        self.p1 = p1
        self.p2 = p2
        self.p3 = p3
        self.p4 = p4
        self.nchord = nchord
        self.nspan = nspan

    @property
    def d12(self):
        return self.p2 - self.p1

    @property
    def d43(self):
        return self.p3 - self.p4

    @property
    def d14(self):
        return self.p4 - self.p1

    @property
    def d23(self):
        return self.p3 - self.p2

    @property
    def orthogonal_vector(self):
        return np.cross(self.d12, self.d14)

    @property
    def span(self):
        return np.linalg.norm(self.d14)

    @property
    def chord(self):
        return np.linalg.norm(self.d12)

    @property
    def l12(self):
        return np.linalg.norm(self.d12)

    @property
    def l43(self):
        return np.linalg.norm(self.d43)

    def set_panel_limits(self, p1, p2, p3, p4):
        self.p1 = p1
        self.p2 = p2
        self.p3 = p3
        self.p4 = p4

    def set_panel_limits_from_femap(self, femap: Femap):
        p1 = np.array(list(femap.get_xyz('Please select the Aerodynamic Panel Point 1:')))
        p2 = np.array(list(femap.get_xyz('Please select the Aerodynamic Panel Point 2:')))
        p3 = np.array(list(femap.get_xyz('Please select the Aerodynamic Panel Point 3:')))
        p4 = np.array(list(femap.get_xyz('Please select the Aerodynamic Panel Point 4:')))
        self.set_panel_limits(p1, p2, p3, p4)

    def set_mesh_size(self, nspan, nchord):
        self.nspan = nspan
        self.nchord = nchord

    def set_mesh_size_from_femap(self, femap: Femap):
        nspan = int(femap.user_int_input('Number of elements span wise:'))
        nchord = int(femap.user_int_input('Number of elements chord wise:'))
        self.set_mesh_size(nspan, nchord)


class AeroPanel(Panel):
    """
    Aerodynamic Panel with N-Chord subdivision and M-Span subdivisions (all equally), and IDs of the structural nodes,
    or the ID of the set, that it will correlate.
    """

    def __init__(self, nchord=None, nspan=None, structural_ids=None):
        super().__init__()
        self.structural_ids = structural_ids

    def set_panel_grid_group_from_femap(self, femap: Femap, text="Select the node group for the Panel"):
        self.structural_ids = int(femap.get_group_id(text))

    def set_panel_grid_ids_from_femap(self, femap: Femap, text="Select the nodes for the Panel"):
        self.structural_ids = femap.get_node_ids_array(text)

    @abstractmethod
    def set_panel_properties(self, *args):
        pass


class AeroPanel5(AeroPanel):
    """
    Aerodynamic Panel using the Piston Theory (CEARO5 Nastran's element).
    """

    THEORIES = {'PISTON': 0, 'VANDYKE': 1, 'VDSWEEP': 2}

    def __init__(self, thickness_integrals=None, control_surface_ratios=None, theory=None):
        super().__init__()
        self.thickness_integrals = thickness_integrals
        self.control_surface_ratios = control_surface_ratios
        self.theory = theory
        self.nchord = 1

    def set_panel_properties(self, theory, thickness_int, control_surf):
        assert len(control_surf) == self.nspan
        self.thickness_integrals = thickness_int
        self.control_surface_ratios = control_surf
        self.theory = self.THEORIES[theory]


class SuperAeroPanel(Panel):
    """
    A "superelement" which holds AeroPanel and its derivatives elements disposed chordwise.
    It's used to simulate chordwise flexibility with aerodynamic strip theories.
    """

    def __init__(self, ide, aeropanels=None):
        """
        Parameters
        ----------
            femap : Femap
            aeropanels : {int: AeroPanel}
        """
        super().__init__()
        self.ide = ide
        self.aeropanels = aeropanels

    def set_panels_grid_group_from_femap(self):
        for k in self.aeropanels.keys():
            self.aeropanels[k].set_panel_grid_group("Select the node group for the Panel {}".format(k+1))

    def set_panels_grid_ids_from_femap(self):
        for i, k in enumerate(self.aeropanels.keys()):
            self.aeropanels[k].set_panel_grid_ids("Select the nodes id for the Panel {}".format(k+1))

    def set_panel_properties_equally(self, *args):
        self.aeropanels[0].set_panel_properties(*args)
        ignored_props = vars(AeroPanel(None))
        for k, panel in self.aeropanels.items():
            if k == 0:
                continue
            for prop in vars(panel).keys():
                if prop in ignored_props:
                    continue
                setattr(panel, prop, getattr(self.aeropanels[0], prop))


class SuperAeroPanel5(SuperAeroPanel):
    """
    A superelement which holds CEARO5 elements.
    """

    def __init__(self, ide, superpanels=None):
        super().__init__(ide, superpanels)

    def create_aero5_panels(self):
        self.aeropanels = {i: AeroPanel5() for i in range(self.nchord)}
        for i, panel in self.aeropanels.items():
            panel.nspan = self.nspan

            panel.p1 = self.p1 + self.d12 * i / self.nchord
            panel.p4 = self.p4 + self.d43 * i / self.nchord
            panel.p2 = panel.p1 + self.d12 / self.nchord
            panel.p3 = panel.p4 + self.d43 / self.nchord

    def init_from_femap(self, femap):

        # get aerodynamic grid limits
        self.set_panel_limits_from_femap(femap)

        # aerodynamic mesh definition
        self.set_mesh_size_from_femap(femap)

        # generate the AeroPanel objects
        self.create_aero5_panels()

        # panel properties
        theory = 'VANDYKE'
        thickness_int = [0., 0., 0., 0., 0.]  # TODO: calculate on time
        control_surf = [0. for _ in range(self.nspan)]  # for each strip TODO: make this customizable
        self.set_panel_properties_equally(theory, thickness_int, control_surf)

