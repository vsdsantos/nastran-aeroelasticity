

from nastran.analysis import Subcase
from typing import Dict
import numpy as np
from pyNastran.bdf.bdf import BDF

from nastran.aero.superpanels import SuperAeroPanel5, SuperAeroPanel1
from nastran.aero.analysis.flutter import FlutterSubcase, FlutterAnalysisModel


class PanelFlutterSubcase(FlutterSubcase):

    def __init__(self, id, spc=None, fmethod=None, method=None,
                 plate_stiffness=None, vref=None, **args):
        super().__init__(id, spc=spc, fmethod=fmethod, method=method, **args)
        self.plate_stiffness = plate_stiffness
        self.vref = vref


class PanelFlutterAnalysisModel(FlutterAnalysisModel):
    """
    Class to model a panel flutter configuration in Nastran.
    """
    
    def __init__(self, model: BDF = None, global_case = None,
                 subcases: Dict[int, Subcase] = {},
                 params=None, diags=None, interface=None,superpanels=None):
        super().__init__(model=model, global_case=global_case,
                        subcases=subcases, params=params, diags=diags,
                        interface=interface)
        self.superpanels = superpanels if superpanels is not None else []

    def add_superpanel(self, superpanel):
        self.superpanels.append(superpanel)

    def write_cards(self):
        super().write_cards()
        
        for spanel in self.superpanels:
            self._write_superpanel_cards(spanel)

        # Validate
        self.model.validate()

        print('Aerodynamic Flutter solution created!')

    def _write_splines2_for_superpanel(self, superpanel, caeros, cords=None):
        # SET and SPLINE cards
        for i in range(superpanel.nchord):
            # TODO: Make optional use of set2 or set1
            # grid set (nodes) to the spline interpolation
            # struct = spanel.aeropanels[i].structural_ids
            # if type(struct) == int:
            #     grid_group = model.sets[struct]
            # elif len(list(struct)) > 0:
            #     grid_group = model.add_set1(idutil.get_next_set_id(), list(struct))
            # else:
            #     raise Exception('Structural grid set for Splines could not be created.')

            grid_group = self.model.add_set2(self.idutil.get_next_set_id(), caeros[i].eid, -0.01, 1.01, -0.01, 1.01)

            # Linear Spline (SPLINE2) element
            self.model.add_spline2(self.idutil.get_next_spline_id(),
                                   caero=caeros[i].eid,
                                   # Coordinate system of the CAERO5 element
                                   # (Y-Axis must be colinear with "Elastic Axis")
                                   cid=0 if cords is None else cords[i].cid,
                                   id1=caeros[i].eid,
                                   id2=caeros[i].eid + superpanel.nspan - 1,
                                   setg=grid_group.sid,
                                   # Detached bending and torsion (-1 -> infinity flexibility), only Z displacement
                                   # allowed to comply with the rigid chord necessity of the Piston Theory
                                   # and still model the plate bending (with N chord-wise elements).
                                   dthx=-1.,
                                   dthy=-1.,
                                   dz=0.)

    def _write_spline1_for_superpanel(self, elements):
        grid_group = self.model.add_set2(self.idutil.get_next_set_id(), elements['main'].eid, -0.01, 1.01, -0.01, 1.01)
        self.model.add_spline1(self.idutil.get_next_spline_id(),
                               caero=elements['main'].eid,
                               box1=elements['main'].eid,
                               box2=elements['main'].eid + elements['main'].nspan * elements['main'].nchord - 1,
                               setg=grid_group.sid)

    def _write_superpanel_cards(self, **args):
        pass


class PanelFlutterPistonAnalysisModel(PanelFlutterAnalysisModel):
    """
    Class to model a panel flutter configuration with Piston Theory in Nastran.
    """
    
    # def __init__(self, model: BDF = None, global_case = None,
    #              subcases: Dict[int, Subcase] = {},
    #              params=None, diags=None, interface=None,superpanels=[]):
    #     super().__init__(model=model, global_case=global_case, subcases=subcases,
    #                      params=params, diags=diags, interface=interface,
    #                      superpanels=superpanels)

    def _write_superpanel_cards(self, superpanel: SuperAeroPanel5):
        # AEFACT cards
        thickness_integrals = self.model.add_aefact(self.idutil.get_next_aefact_id(),
                                                    superpanel.thick_int)

        machs_n_alphas = self._write_machs_and_alphas(self.global_case.machs, self.global_case.alphas)

        # PAERO5 card
        paero = self.model.add_paero5(self.idutil.get_next_paero_id(),
                                      caoci=superpanel.ctrl_surf,
                                      nalpha=1,
                                      lalpha=machs_n_alphas.sid)

        caeros, cords = self._write_caero5_as_panel(superpanel, paero, thickness_integrals)
        self._write_splines2_for_superpanel(superpanel, caeros, cords)

    def _write_caero5_as_panel(self, superpanel: SuperAeroPanel5, paero, thickness_integrals):
        # CORD2R and CAERO5 cards
        # wind_x_vector = np.array([1., 0., 0.])

        caeros = []
        cords = []

        id_increment = self.idutil.get_last_element_id()
        for _, panel in superpanel.aeropanels.items():
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
                                      pxz_i))

            # CAERO5 element
            caeros.append(
                self.model.add_caero5(self.idutil.get_next_caero_id() + id_increment,
                                      pid=paero.pid,
                                      cp=0,
                                      nspan=panel.nspan,
                                      lspan=None,
                                      nthick=thickness_integrals.sid,
                                      p1=panel.p1,
                                      x12=panel.l12,
                                      p4=panel.p4,
                                      x43=panel.l12,
                                      ntheory=panel.theory)
            )
            id_increment = panel.nspan - 1
        return caeros, cords


class PanelFlutterPistonZAEROAnalysisModel(PanelFlutterAnalysisModel):

    # def __init__(self, model: BDF = None, global_case = None,
    #              subcases: Dict[int, Subcase] = {},
    #              params=None, diags=None, interface=None,superpanels=[]):
    #     super().__init__(model=model, global_case=global_case, subcases=subcases,
    #                      params=params, diags=diags, interface=interface,
    #                      superpanels=superpanels)
    
    def _write_superpanel_cards(self, superpanel: SuperAeroPanel1):
        paero = self.model.add_paero1(self.idutil.get_next_paero_id())

        elements = {}

        last_id = self.idutil.get_last_element_id()

        pot = int(np.ceil(np.log10(last_id))) + 1

        # TODO: improve eid handle
        main = superpanel.aeropanels['main']
        left = superpanel.aeropanels['left']
        right = superpanel.aeropanels['right']

        elements['main'] = self.model.add_caero1(int(10 ** pot + 1),
                                                 pid=paero.pid,
                                                 nspan=main.nspan,
                                                 nchord=main.nchord,
                                                 igroup=1,
                                                 p1=main.p1,
                                                 p4=main.p4,
                                                 x12=main.l12,
                                                 x43=main.l43)

        elements['left'] = self.model.add_caero1(self.idutil.get_next_caero_id() + main.nspan * main.nchord,
                                                 pid=paero.pid,
                                                 nspan=left.nspan,
                                                 nchord=left.nchord,
                                                 igroup=1,
                                                 p1=left.p1,
                                                 p4=left.p4,
                                                 x12=left.l12,
                                                 x43=left.l43)

        elements['right'] = self.model.add_caero1(self.idutil.get_next_caero_id() + left.nspan * left.nchord,
                                                  pid=paero.pid,
                                                  nspan=right.nspan,
                                                  nchord=right.nchord,
                                                  igroup=1,
                                                  p1=right.p1,
                                                  p4=right.p4,
                                                  x12=right.l12,
                                                  x43=right.l43)
        
        # self.write_spline1_for_panel(elements)
        self.write_splines2_for_superpanel(superpanel, elements['main'])


