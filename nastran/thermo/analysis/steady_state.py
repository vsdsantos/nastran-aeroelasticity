
from typing import Dict
from pyNastran.bdf.bdf import BDF, CaseControlDeck
from nastran.aero.superpanels import SuperAeroPanel5

from nastran.analysis import AnalysisModel, Subcase

import numpy as np

class ThermoSubcase(Subcase):
    """
    This class represents the requirements to the Aeroelastic Flutter Solution 145 of NASTRAN.
    """

    def __init__(self, id, spc=None, temp=None, **args):
        super().__init__(id, spc=spc, load=None, **args)
        self.temp = temp


class SteadyStateThermoAnalysisModel(AnalysisModel):
    """
    Class for the Nastran's SOL 153

    """

    def __init__(self, model: BDF = None, global_case = None,
                 subcases: Dict[int, Subcase] = {},
                 params=None, diags=None, interface=None):
        super().__init__(model=model,
            global_case=global_case, subcases=subcases,
            params=params, diags=diags,
            sol=153, interface=interface)
        self.init_temp = None
        self.max_temp = None
        self.ni = None

    def write_cards(self):
        super().write_cards()

    def _write_global_analysis_cards(self):

        cc = self.model.case_control_deck

        self.model.add_tempd(1, 0.0)
        cc.add_parameter_to_global_subcase('TEMP(INIT) = %d' % 1)

        temp_cases = np.linspace(self.init_temp, self.max_temp, self.ni)

        for i, t in enumerate(temp_cases):
            self.model.add_tempd(10+i, t)
            self.model.add_nlparm(10+i, 1, kmethod='ITER', kstep=1, int_out='YES')
            cc.create_new_subcase(1+i)
            cc.add_parameter_to_local_subcase(1+i, 'TEMP(LOAD) = %d' % (10+i))
            cc.add_parameter_to_local_subcase(1+i, 'NLPARM = %d' % (10+i))

    def write_cord2r_cards(self, superpanel: SuperAeroPanel5):
        cords = []

        for panel in superpanel.aeropanels.values():
            # set origin to element mid chord (linear spline requires the Y axis to be colinear with the
            # "elastic axis" of the structure, since it is a plate chord-wise divided,
            # the elastic axis should be at mid chord)
            origin = panel.p1 + panel.d12 / 2

            # point in the XZ plane to define the coordinate system
            # this hardcodes the Y axis of the local aerodynamic coordinate system
            # to be colinear with the element Y axis (i.e. the vector of p1 to p4)
            pxz_i = origin + panel.d12

            # local aerodynamic coordinate system
            cords.append(
                self.model.add_cord2r(self.idutil.get_next_coord_id(),
                                      origin,
                                      origin + panel.normal,
                                      pxz_i)
                        )
        return cords
