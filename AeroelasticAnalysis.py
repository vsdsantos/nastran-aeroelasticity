import numpy as np


class FlutterAnalysis:
    FMETHODS = {1: 'K', 2: 'PK', 3: 'PKNL', 4: 'KE'}
    EIGRMETHODS = {1: 'LAN', 2: 'AHOU'}

    def __init__(self, femap, ref_rho=None, ref_chord=None, ref_velocity=None, n_modes=None,
                 frequency_limits=None, densities_ratio=None, machs=None, alphas=None,
                 reduced_frequencies=None, velocities=None, method=None, eig_method=None):
        self.femap = femap
        self.ref_rho = ref_rho
        self.ref_chord = ref_chord
        self.ref_velocity = ref_velocity
        self.n_modes = n_modes
        self.frequency_limits = frequency_limits
        self.densities_ratio = densities_ratio
        self.machs = machs
        self.alphas = alphas
        self.reduced_frequencies = reduced_frequencies
        self.velocities = velocities
        self.method = method
        self.eig_method = eig_method

    def set_aeroelastic_properties(self):
        self._set_ref_flow_properties()
        self._set_modal_analysis_properties()
        self._set_flutter_analysis_properties()

    def _set_ref_flow_properties(self):
        # flow reference properties
        self.ref_rho = 1.23E-12  # 1.1468e-7  # float(self.femap.user_int_input('Reference air density:'))
        self.ref_chord = 1000.  # float(self.femap.user_int_input('Reference chord:'))
        self.ref_velocity = 1.  # float(self.femap.user_int_input('Reference velocity:'))

    def _set_modal_analysis_properties(self):
        # modal analysis properties
        self.n_modes = 15  # int(self.femap.user_int_input('Number of modes:'))
        self.frequency_limits = [0.0, 3000.0]
        self.eig_method = self.EIGRMETHODS[1]

    def _set_flutter_analysis_properties(self):
        # flutter analysis properties
        self.densities_ratio = [.5]
        self.machs = [2.0, 3.0]
        self.alphas = [0.0, 0.0]
        self.reduced_frequencies = [.001, .1, .2, .4]
        self.velocities = [21600.0, 22800.0, 23400.0, 24000.0, 26400.0, 28800.0, 29400.0, 30000.0, 31200.0]
        self.method = self.FMETHODS[2]


class IDUtility:

    def __init__(self, model):
        self.model = model

    @classmethod
    def _get_last_id_from_ids(cls, elements):
        return elements[-1] if elements else 0

    def get_last_element_id(self):
        return IDUtility._get_last_id_from_ids(list(self.model.element_ids))

    def get_next_element_id(self):
        return self.get_last_element_id() + 1

    def get_last_caero_id(self):
        return IDUtility._get_last_id_from_ids(list(self.model.caeros.keys()))

    def get_next_caero_id(self):
        return self.get_last_caero_id() + 1

    def get_last_node_id(self):
        return IDUtility._get_last_id_from_ids(list(self.model.node_ids))

    def get_next_node_id(self):
        return self.get_last_node_id() + 1

    def get_last_flfact_id(self):
        return IDUtility._get_last_id_from_ids(list(self.model.flfacts.keys()))

    def get_next_flfact_id(self):
        return self.get_last_flfact_id() + 1

    def get_last_flutter_id(self):
        return IDUtility._get_last_id_from_ids(list(self.model.flutters.keys()))

    def get_next_flutter_id(self):
        return self.get_last_flutter_id() + 1

    def get_last_method_id(self):
        return IDUtility._get_last_id_from_ids(list(self.model.methods.keys()))

    def get_next_method_id(self):
        return self.get_last_method_id() + 1

    def get_last_aefact_id(self):
        return IDUtility._get_last_id_from_ids(list(self.model.aefacts.keys()))

    def get_next_aefact_id(self):
        return self.get_last_aefact_id() + 1

    def get_last_paero_id(self):
        return IDUtility._get_last_id_from_ids(list(self.model.paeros.keys()))

    def get_next_paero_id(self):
        return self.get_last_paero_id() + 1

    def get_last_spline_id(self):
        return IDUtility._get_last_id_from_ids(list(self.model.splines.keys()))

    def get_next_spline_id(self):
        return self.get_last_spline_id() + 1

    def get_last_set_id(self):
        return IDUtility._get_last_id_from_ids(list(self.model.sets.keys()))

    def get_next_set_id(self):
        return self.get_last_set_id() + 1

    def get_last_coord_id(self):
        return IDUtility._get_last_id_from_ids(list(self.model.coords.keys()))

    def get_next_coord_id(self):
        return self.get_last_coord_id() + 1


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
            # if i % 4 == 0:  # TODO: Remove this
            self.aeropanels[k].set_panel_grid_ids("Select the nodes id for the Panel {}".format(k+1))
            # self.aeropanels[k + 1].structural_ids = self.aeropanels[k].structural_ids
            # self.aeropanels[k + 2].structural_ids = self.aeropanels[k].structural_ids
            # self.aeropanels[k + 3].structural_ids = self.aeropanels[k].structural_ids

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

