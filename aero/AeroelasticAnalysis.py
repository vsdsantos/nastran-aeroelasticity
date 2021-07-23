from pyNastran.bdf.bdf import BDF, CaseControlDeck
from abc import ABC, abstractmethod
import yaml

import numpy as np

from aero.AeroelasticPanels import SuperAeroPanel5, SuperAeroPanel1


class Subcase:
    """
    Represents a NASTRAN subcase with CASE CONTROL statements.
    """

    def __init__(self, case_control=None):
        self.case_control = case_control

    @classmethod
    def create_from_data(cls, data):
        obj = cls()
        _set_object_properties(obj, data)
        return obj


class FlutterSubcase(Subcase):
    """
    This class represents the requirements to the Aeroelastic Flutter Solution 145 of NASTRAN.
    """

    FMETHODS = {
        1: 'K',
        2: 'KE',
        3: 'PK',
        4: 'PKNL',
        5: 'PKS',  # only on recent MSC.Nastran versions
        6: 'PKNLS'  # only on recent MSC.Nastran versions
    }

    def __init__(self, *args, ref_rho=None, ref_chord=None, n_modes=None,
                 frequency_limits=None, densities_ratio=None, machs=None, alphas=None,
                 reduced_frequencies=None, velocities=None, method=None):
        super().__init__(*args)
        self.ref_rho = ref_rho
        self.ref_chord = ref_chord
        self.n_modes = n_modes
        self.frequency_limits = frequency_limits
        self.densities_ratio = densities_ratio
        self.machs = machs
        self.alphas = alphas
        self.reduced_frequencies = reduced_frequencies
        self.velocities = velocities
        self.method = method

    @classmethod
    def create_from_yaml(cls, file_name):
        with open(file_name, 'r') as file:
            data = yaml.safe_load(file)
        return FlutterSubcase.create_from_data(data)


class PanelFlutterSubcase(FlutterSubcase):

    def __init__(self, *args, plate_stiffness=None, vref=None):
        super().__init__(*args)
        self.plate_stiffness = plate_stiffness
        self.vref = vref


SUBCASE_TYPES = {
    'PANELFLUTTER': PanelFlutterSubcase,
    'FLUTTER': FlutterSubcase
}


class AnalysisModel(ABC):

    def __init__(self):
        self.model = BDF(debug=False)
        self.idutil = IDUtility(self.model)
        self.subcases = {}
        self.params = {}
        self.diags = []
        self.sol = None
        self.interface = None

    def import_from_bdf(self, bdf_file_name: str, sanitize: bool = True, reset_bdf: bool = False):
        # load models and utility
        base_model = BDF(debug=False)

        if reset_bdf:
            self.model = BDF(debug=False)
            self.idutil = IDUtility(self.model)

        print("Loading base bdf model to pyNastran...")
        base_model.read_bdf(bdf_file_name)

        # clears problematic entries from previous analysis
        # print("Sanitizing model...")
        cards = list(base_model.card_count.keys())
        # TODO: make whitelist of structural elements, properties and spcs or resolve the importing other way

        if sanitize:
            block_list = ['ENDDATA', 'PARAM', 'EIGR', 'CAERO1', 'CAERO2', 'PAERO1', 'PAERO2', 'SPLINE1', 'SPLINE2',
                          'EIGRL']
        else:
            block_list = []
        sanit_card_keys = list(filter(lambda c: c not in block_list, cards))
        sanit_cards = base_model.get_cards_by_card_types(sanit_card_keys)

        for key in sanit_cards:
            for card in sanit_cards[key]:
                lines = card.write_card().split('\n')
                comments = []
                while lines[0].strip('')[0] == '$':  # separate comments
                    comments.append(lines.pop(0))
                self.model.add_card_lines(lines, key, comment=comments)
        print('Done!')

    def load_analysis_from_yaml(self, yaml_file_name: str):
        with open(yaml_file_name, 'r') as file:
            data = yaml.safe_load(file)
        self.params = data['params']
        self.diags = data['diags']
        self.interface = data['interface']
        for key, subcase in data['subcases'].items():
            self.create_subcase_from_data(key, data=subcase)

    @abstractmethod
    def create_subcase_from_file(self, sub_id, subcase_file_name):
        pass

    @abstractmethod
    def create_subcase_from_data(self, sub_id, data):
        pass

    @abstractmethod
    def create_subcase(self, sub_id, sub_type):
        pass

    @abstractmethod
    def write_cards_from_subcase(self, sub_id):
        pass

    def write_executive_control_cards(self):
        # Executive Control
        self.model.sol = self.sol

        # TODO: diagnostic doesn't work
        # diagnostic = 'DIAG '
        # for diag in self.diags:
        #     diagnostic += '%d,' % diag
        # self.model.executive_control_lines = [diagnostic]

    def write_case_control_from_list(self, cc, idn, subcase):
        if subcase.case_control is not None:
            for card in subcase.case_control:
                cc.add_parameter_to_local_subcase(idn, card)

    def write_case_control_cards(self):
        # Case Control
        cc = CaseControlDeck([])

        for key, subcase in self.subcases.items():
            cc.create_new_subcase(key)
            self.write_case_control_from_list(cc, key, subcase)
        self.model.case_control_deck = cc

    def write_params(self):
        # params
        for key, param in self.params.items():
            if hasattr(param, '__iter__'):  # check if object is iterable
                self.model.add_param(key=key, values=list(param))
            else:
                self.model.add_param(key=key, values=[param])

    def write_cards(self):
        self.write_executive_control_cards()
        self.write_case_control_cards()
        self.write_params()

        # Validate
        self.model.validate()

    def export_to_bdf(self, output_bdf):
        # Write output
        print('Writing bdf file...')
        self.model.write_bdf(output_bdf, enddata=True)
        print('Done!')


class FlutterAnalysisModel(AnalysisModel):
    """
    Class for the Nastran's SOL 145

    It can be used for conventional wing or aircraft flutter.
    """

    def __init__(self):
        super().__init__()
        self.panels = []
        self.sol = 145

    def write_machs_and_alphas(self, machs, alphas):
        # TODO: Vary with the used flutter solution method
        return self.model.add_aefact(self.idutil.get_next_aefact_id(),
                                     [v for ma in zip(machs, alphas) for v in ma])

    def create_subcase_from_file(self, sub_id, subcase_file_name):
        assert sub_id not in self.subcases.keys()
        sub = FlutterSubcase.create_from_yaml(subcase_file_name)
        self.subcases[sub_id] = sub
        return sub

    def create_subcase_from_data(self, sub_id, data):
        assert sub_id not in self.subcases.keys()
        # if data['type'] == 'PANELFLUTTER':
        #     sub = PanelFlutterSubcase.create_from_data(data)
        # else:
        #     sub = FlutterSubcase.create_from_data(data)
        sub = SUBCASE_TYPES[data['type']].create_from_data(data)
        self.subcases[sub_id] = sub
        return sub

    def create_subcase(self, sub_id, sub_type):
        assert sub_id not in self.subcases.keys()
        # if sub_type == 'PANELFLUTTER':
        #     sub = PanelFlutterSubcase()
        # else:
        #     sub = FlutterSubcase()
        sub = SUBCASE_TYPES[sub_type].create_from_data()
        self.subcases[sub_id] = sub
        return sub

    def write_cards_from_subcase(self, sub_id):
        subcase = self.subcases[sub_id]

        # defines FLFACT cards
        densities_ratio = self.model.add_flfact(self.idutil.get_next_flfact_id(), subcase.densities_ratio)
        machs = self.model.add_flfact(self.idutil.get_next_flfact_id(), subcase.machs)
        velocities = self.model.add_flfact(self.idutil.get_next_flfact_id(), subcase.velocities)

        # defines FLUTTER card for flutter subcase
        fmethod = self.model.add_flutter(self.idutil.get_next_flutter_id(),
                                         method=subcase.method,
                                         density=densities_ratio.sid,
                                         mach=machs.sid,
                                         reduced_freq_velocity=velocities.sid)

        # real eigenvalue method card
        method = self.model.add_eigrl(sid=self.idutil.get_next_method_id(),
                                      norm='MASS',
                                      nd=subcase.n_modes,
                                      v1=subcase.frequency_limits[0],
                                      v2=subcase.frequency_limits[1])

        # subcase.fmethod_sid = fmethod.sid
        # subcase.method_sid = method.sid

        # AERO card
        self.model.add_aero(cref=subcase.ref_chord, rho_ref=subcase.ref_rho, velocity=1.0)

        # MKAERO1 cards
        self.model.add_mkaero1(subcase.machs, subcase.reduced_frequencies)

        return fmethod.sid, method.sid

    def write_case_control_cards(self):
        # Case Control
        cc = CaseControlDeck([])

        for key, subcase in self.subcases.items():
            fmethod, method = self.write_cards_from_subcase(key)
            cc.create_new_subcase(key)
            self.write_case_control_from_list(cc, key, subcase)
            cc.add_parameter_to_local_subcase(1, 'FMETHOD = %d' % fmethod)  # the flutter card id
            cc.add_parameter_to_local_subcase(1, 'METHOD = %d' % method)  # the eigenval analysis card id
        self.model.case_control_deck = cc


class PanelFlutterAnalysisModel(FlutterAnalysisModel):
    """
    Class to model a panel flutter configuration in Nastran.
    """

    def __init__(self):
        super().__init__()
        self.superpanels = []

    def add_superpanel(self, superpanel):
        self.superpanels.append(superpanel)

    def write_superpanel1_cards(self, superpanel, subcase):
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
        self.write_splines2_for_panel(superpanel, elements['main'])

    def write_spline1_for_panel(self, elements):
        grid_group = self.model.add_set2(self.idutil.get_next_set_id(), elements['main'].eid, -0.01, 1.01, -0.01, 1.01)
        self.model.add_spline1(self.idutil.get_next_spline_id(),
                               caero=elements['main'].eid,
                               box1=elements['main'].eid,
                               box2=elements['main'].eid + elements['main'].nspan * elements['main'].nchord - 1,
                               setg=grid_group.sid)

    def write_superpanel5_cards(self, superpanel, subcase):
        # AEFACT cards
        
        thickness_integrals = self.model.add_aefact(self.idutil.get_next_aefact_id(),
                                                    superpanel.aeropanels[0].thickness_integrals)

        machs_n_alphas = self.write_machs_and_alphas(self.subcases[subcase].machs, self.subcases[subcase].alphas)

        # PAERO5 card
        paero = self.model.add_paero5(self.idutil.get_next_paero_id(),
                                      caoci=superpanel.aeropanels[0].control_surface_ratios,
                                      nalpha=1,
                                      lalpha=machs_n_alphas.sid)

        caeros, cords = self.write_caero5_as_panel(superpanel, paero, thickness_integrals)
        self.write_splines2_for_panel(superpanel, caeros, cords)

    def write_caero5_as_panel(self, superpanel, paero, thickness_integrals):
        # CORD2R and CAERO5 cards
        # wind_x_vector = np.array([1., 0., 0.])
        caeros = []
        cords = []
        id_increment = self.idutil.get_last_element_id()
        for i, panel in superpanel.aeropanels.items():
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
                                      origin + panel.orthogonal_vector,
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
                                      x43=panel.l43,
                                      ntheory=panel.theory)
            )
            id_increment = panel.nspan - 1
        return caeros, cords

    def write_splines2_for_panel(self, superpanel, caeros, cords=None):
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
                                   cid=0 if cords else cords[i].cid,
                                   id1=caeros[i].eid,
                                   id2=caeros[i].eid + superpanel.nspan - 1,
                                   setg=grid_group.sid,
                                   # Detached bending and torsion (-1 -> infinity flexibility), only Z displacement
                                   # allowed to comply with the rigid chord necessity of the Piston Theory
                                   # and still model the plate bending (with N chord-wise elements).
                                   dthx=-1.,
                                   dthy=-1.,
                                   dz=0.)

    def write_cards(self):
        super().write_cards()
        
        for subcase in self.subcases:
            for spanel in self.superpanels:
                if type(spanel) == SuperAeroPanel1:
                    self.write_superpanel1_cards(spanel, subcase)
                elif type(spanel) == SuperAeroPanel5:
                    self.write_superpanel5_cards(spanel, subcase)
                else:
                    pass

        # Validate
        self.model.validate()

        print('Aerodynamic Flutter solution created!')


def _set_object_properties(obj, data):
    for key, val in data.items():
        setattr(obj, key, val)


def _get_last_id_from_ids(elements):
    return elements[-1] if elements else 0


class IDUtility:
    """
        This class is a utility to work with IDs in the BDF format using pyNastran
    """

    def __init__(self, model):
        self.model = model

    def get_last_element_id(self):
        return _get_last_id_from_ids(list(self.model.element_ids))

    def get_next_element_id(self):
        return self.get_last_element_id() + 1

    def get_last_caero_id(self):
        return _get_last_id_from_ids(list(self.model.caeros.keys()))

    def get_next_caero_id(self):
        return self.get_last_caero_id() + 1

    def get_last_node_id(self):
        return _get_last_id_from_ids(list(self.model.node_ids))

    def get_next_node_id(self):
        return self.get_last_node_id() + 1

    def get_last_flfact_id(self):
        return _get_last_id_from_ids(list(self.model.flfacts.keys()))

    def get_next_flfact_id(self):
        return self.get_last_flfact_id() + 1

    def get_last_flutter_id(self):
        return _get_last_id_from_ids(list(self.model.flutters.keys()))

    def get_next_flutter_id(self):
        return self.get_last_flutter_id() + 1

    def get_last_method_id(self):
        return _get_last_id_from_ids(list(self.model.methods.keys()))

    def get_next_method_id(self):
        return self.get_last_method_id() + 1

    def get_last_aefact_id(self):
        return _get_last_id_from_ids(list(self.model.aefacts.keys()))

    def get_next_aefact_id(self):
        return self.get_last_aefact_id() + 1

    def get_last_paero_id(self):
        return _get_last_id_from_ids(list(self.model.paeros.keys()))

    def get_next_paero_id(self):
        return self.get_last_paero_id() + 1

    def get_last_spline_id(self):
        return _get_last_id_from_ids(list(self.model.splines.keys()))

    def get_next_spline_id(self):
        return self.get_last_spline_id() + 1

    def get_last_set_id(self):
        return _get_last_id_from_ids(list(self.model.sets.keys()))

    def get_next_set_id(self):
        return self.get_last_set_id() + 1

    def get_last_coord_id(self):
        return _get_last_id_from_ids(list(self.model.coords.keys()))

    def get_next_coord_id(self):
        return self.get_last_coord_id() + 1
