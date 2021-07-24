
from nastran.geometry.panels import RectangularPlate
from nastran.aero.panels import AeroPanel, AeroPanel1, AeroPanel5

import numpy as np

class SuperAeroPanel(RectangularPlate):
    """
    A "superelement" which holds AeroPanel and its derivatives elements disposed chordwise.
    It's used to simulate chordwise flexibility with aerodynamic strip theories.
    """

    def __init__(self, p1, p2, p3, p4, eid, aeropanels=None):
        """
        Parameters
        ----------
            aeropanels : {int: AeroPanel}
        """
        super().__init__(p1, p2, p3, p4)
        self.eid = eid
        self.aeropanels = aeropanels

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

class SuperAeroPanel1(SuperAeroPanel):
    """

    """

    def __init__(self, p1, p2, p3, p4, eid, min_mach=np.sqrt(2)):
        super().__init__(p1, p2, p3, p4, eid)
        self.min_mach = min_mach

    def create_aero1_panels(self):
        self.aeropanels = {}

        main_panel = AeroPanel1(*self.limit_points, self.nspan, self.nchord)

        # angle of the mach cone
        mi = np.arccos(1./self.min_mach)  # mi = arccos(1/M)
        lateral_span = self.chord / np.tan(mi)  # the spanwise needed

        element_size = self.l14 / self.nspan  # element spanwise length
        lateral_n = int(np.ceil(lateral_span / element_size))  # number of span elements

        p1l = self.p1 - [0, element_size*lateral_n, 0]
        p2l = self.p2 - [0, element_size*lateral_n, 0]
        p3l = self.p2
        p4l = self.p1
        left_panel = AeroPanel1(p1l, p2l, p3l, p4l, lateral_n, self.nchord)

        p1r = self.p4
        p2r = self.p3
        p3r = self.p3 + [0, element_size * lateral_n, 0]
        p4r = self.p4 + [0, element_size * lateral_n, 0]
        right_panel = AeroPanel1(p1r, p2r, p3r, p4r, lateral_n, self.nchord)

        self.aeropanels['main'] = main_panel
        self.aeropanels['left'] = left_panel
        self.aeropanels['right'] = right_panel

    def init(self):
        # generate the AeroPanel objects
        self.create_aero1_panels()

class SuperAeroPanel5(SuperAeroPanel):
    """
    A superelement which holds CEARO5 elements (strips) for modeling chordwise flexiblity.
    """

    def __init__(self, p1, p2, p3, p4, eid, aeropanels=None, theory='PISTON'):
        super().__init__(p1, p2, p3, p4, eid, aeropanels)

        # generate the AeroPanel objects
        self.create_aero5_panels()

        # panel properties
        thickness_int = [0., 0., 0., 0., 0., 0.]  # TODO: calculate on time
        control_surf = [0. for _ in range(self.nspan)]  # for each strip TODO: make this customizable
        self.set_panel_properties_equally(theory, thickness_int, control_surf)

    def create_aero5_panels(self):
        panels = dict()
        for i in self.aeropanels.items():
            p1 = self.p1 + self.d12 * i / self.nchord
            p4 = self.p4 + self.d12 * i / self.nchord
            p2 = p1 + self.d12 / self.nchord
            p3 = p4 + self.d12 / self.nchord
            panels[i] = AeroPanel5(p1, p2, p3, p4, 1, self.nspan)

