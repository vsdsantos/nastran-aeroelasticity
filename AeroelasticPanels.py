from femap import Femap
import numpy as np


class Panel:
    """
    Generic Panel defined by four points in the space.
    """
    def __init__(self, femap, p1=None, p2=None, p3=None, p4=None):
        self.femap = femap
        self.p1 = p1
        self.p2 = p2
        self.p3 = p3
        self.p4 = p4

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

    def set_panel_limits(self):
        self.p1 = np.array(list(self.femap.get_xyz('Please select the Aerodynamic Panel Point 1:')))
        self.p2 = np.array(list(self.femap.get_xyz('Please select the Aerodynamic Panel Point 2:')))
        self.p3 = np.array(list(self.femap.get_xyz('Please select the Aerodynamic Panel Point 3:')))
        self.p4 = np.array(list(self.femap.get_xyz('Please select the Aerodynamic Panel Point 4:')))


class AeroPanel(Panel):
    """
    Aerodynamic Panel with N-Chord subdivision and M-Span subdivisions (all equally), and IDs of the structural nodes,
    or the ID of the set, that it will correlate.
    """

    def __init__(self, femap, nchord=None, nspan=None, structural_ids=None):
        super().__init__(femap)
        self.nchord = nchord
        self.nspan = nspan
        self.structural_ids = structural_ids

    def set_mesh_size(self):
        self.nspan = int(self.femap.user_int_input('Number of elements span wise:'))
        self.nchord = int(self.femap.user_int_input('Number of elements chord wise:'))

    def set_panel_grid_group(self, text="Select the node group for the Panel"):
        self.structural_ids = int(self.femap.get_group_id(text))

    def set_panel_grid_ids(self, text="Select the nodes for the Panel"):
        self.structural_ids = self.femap.get_node_ids_array(text)

    def set_panel_properties(self):
        pass


class AeroPanel5(AeroPanel):
    """
    Aerodynamic Panel using the Piston Theory (CEARO5 Nastran's element).
    """

    def __init__(self, femap, thickness_integrals=None, control_surface_ratios=None, theory=None):
        super().__init__(femap)
        self.thickness_integrals = thickness_integrals
        self.control_surface_ratios = control_surface_ratios
        self.theory = theory
        self.nchord = 1

    def set_panel_properties(self):
        self.thickness_integrals = [0., 0., 0., 0., 0., 0.]  # TODO: calculate on time
        self.control_surface_ratios = [0. for _ in range(self.nspan)]  # for each strip TODO: make this customizable
        self.theory = 1


class SuperAeroPanel(AeroPanel):
    """
    A "superelement" which holds AeroPanel and its derivatives elements disposed chordwise.
    It's used to simulate chordwise flexibility with aerodynamic strip theories.
    """

    def __init__(self, femap, aeropanels=None):
        """
        Parameters
        ----------
            femap : Femap
            aeropanels : {int: AeroPanel}
        """
        super().__init__(femap)
        self.aeropanels: {int: AeroPanel} = aeropanels

    def set_panel_grid_group(self, text=''):
        """ Do not use this with "Super Elements"."""
        pass

    def set_panel_grid_ids(self, text=''):
        """ Do not use this with "Super Elements"."""
        pass

    def set_panels_grid_group(self):
        for k in self.aeropanels.keys():
            self.aeropanels[k].set_panel_grid_group("Select the node group for the Panel {}".format(k+1))

    def set_panels_grid_ids(self):
        for i, k in enumerate(self.aeropanels.keys()):
            self.aeropanels[k].set_panel_grid_ids("Select the nodes id for the Panel {}".format(k+1))

    def set_panel_properties_equally(self):
        self.aeropanels[0].set_panel_properties()
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

    def __init__(self, femap):
        super().__init__(femap)

    def create_aero5_panels(self):
        self.aeropanels = {i: AeroPanel5(self.femap) for i in range(self.nchord)}
        for i, panel in self.aeropanels.items():
            panel.nspan = self.nspan

            panel.p1 = self.p1 + self.d12 * i / self.nchord
            panel.p4 = self.p4 + self.d43 * i / self.nchord
            panel.p2 = panel.p1 + self.d12 / self.nchord
            panel.p3 = panel.p4 + self.d43 / self.nchord

    def init_from_femap(self):
        """
        Connects with an open Femap intance and grabs user input to the aeroelastic model and analysis

        Parameters
        -----------
        bdf_filename : str
            file to output the .bdf current model
            Currently there is a need to run a previous analysis (e.g. Modal Analysis) so all the elements get printed

        Returns
        --------
         (analysis: AeroAnalysis, panel: AeroPanel)
            a set with an AeroAnalysis and AeroPanel objects, regarding all the information needed
        """

        # get aerodynamic grid limits
        self.set_panel_limits()

        # aerodynamic mesh definition
        self.set_mesh_size()

        # generate the AeroPanel objects
        self.create_aero5_panels()

        # panel properties
        self.set_panel_properties_equally()

