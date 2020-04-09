from pyNastran.bdf.bdf import BDF, CaseControlDeck
import yaml


class AeroelasticAnalysis:

    def __init__(self):
        self.model = BDF(debug=False)
        self.idutil = IDUtility(self.model)
        self.subcases = {}
        self.superpanels = []
        self.params = {}
        self.diags = []

    def import_from_bdf(self, bdf_file):
        # load models and utility
        base_model = BDF()

        print("Loading base bdf model to pyNastran...")
        base_model.read_bdf(bdf_file)

        # clears problematic entries from previous analysis
        print("Sanitizing model...")
        cards = list(base_model.card_count.keys())
        # TODO: make whitelist of structural elements, properties and spcs or resolve the importing other way
        black_list = ['ENDDATA', 'PARAM', 'EIGR', 'CAERO1', 'CAERO2', 'PAERO1', 'PAERO2', 'SPLINE1', 'SPLINE2', 'EIGRL']
        sanit_card_keys = list(filter(lambda c: c not in black_list, cards))
        sanit_cards = base_model.get_cards_by_card_types(sanit_card_keys)

        for key in sanit_cards:
            for card in sanit_cards[key]:
                lines = card.write_card().split('\n')
                comments = []
                while lines[0].strip('')[0] == '$':  # separate comments
                    comments.append(lines.pop(0))
                self.model.add_card_lines(lines, key, comment=comments)

        print('Done!')

    def load_analysis_from_yaml(self, yaml_file):
        with open(yaml_file, 'r') as file:
            data = yaml.safe_load(file)
        self.params = data['params']
        self.diags = data['diags']
        for key, subcase in data['subcases'].items():
            self.create_subcase(key, data=subcase)

    def add_superpanel(self, superpanel):
        self.superpanels.append(superpanel)

    def create_subcase(self, sub_id, config_file=None, data=None):
        assert sub_id not in self.subcases.keys()
        if config_file is None and data is None:
            self.subcases[sub_id] = FlutterAnalysis()
        elif config_file is None and data is not None:
            self.subcases[sub_id] = FlutterAnalysis.create_from_data(data)
        elif config_file is not None and data is None:
            self.subcases[sub_id] = FlutterAnalysis.create_from_yaml_file(config_file)
        else:
            raise Exception('You cannot specify a config file and a data at the same time.')

    def write_cards_from_subcase(self, sub_id):
        analysis = self.subcases[sub_id]
        return self.write_cards_from_analysis(analysis)

    def write_cards_from_analysis(self, analysis):
        # defines FLFACT cards
        densities_ratio = self.model.add_flfact(self.idutil.get_next_flfact_id(), analysis.densities_ratio)
        machs = self.model.add_flfact(self.idutil.get_next_flfact_id(), analysis.machs)
        velocities = self.model.add_flfact(self.idutil.get_next_flfact_id(), analysis.velocities)

        # defines FLUTTER card for flutter analysis
        fmethod = self.model.add_flutter(self.idutil.get_next_flutter_id(),
                                         method=analysis.method,
                                         density=densities_ratio.sid,
                                         mach=machs.sid,
                                         reduced_freq_velocity=velocities.sid)

        # real eigenvalue method card
        method = self.model.add_eigrl(sid=self.idutil.get_next_method_id(),
                                      norm='MASS',
                                      nd=analysis.n_modes,
                                      v1=analysis.frequency_limits[0],
                                      v2=analysis.frequency_limits[1])

        # analysis.fmethod_sid = fmethod.sid
        # analysis.method_sid = method.sid

        # AERO card
        self.model.add_aero(cref=analysis.ref_chord, rho_ref=analysis.ref_rho, velocity=1.0)

        # MKAERO1 cards
        self.model.add_mkaero1(analysis.machs, analysis.reduced_frequencies)

        return fmethod.sid, method.sid

    def write_superpanel_cards(self, superpanel, analysis):
        # AEFACT cards
        thickness_integrals = self.model.add_aefact(self.idutil.get_next_aefact_id(),
                                                    superpanel.aeropanels[0].thickness_integrals)

        machs_n_alphas = self.model.add_aefact(self.idutil.get_next_aefact_id(),
                                               [v for ma in zip(analysis.machs, analysis.alphas) for v in ma])

        # PAERO5 cards
        paero = self.model.add_paero5(self.idutil.get_next_paero_id(),
                                      caoci=superpanel.aeropanels[0].control_surface_ratios,
                                      nalpha=1,
                                      lalpha=machs_n_alphas.sid)

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

        # SET and SPLINE cards
        for i, elem in enumerate(caeros):
            # grid set (nodes) to the spline interpolation
            # struct = spanel.aeropanels[i].structural_ids
            # if type(struct) == int:
            #     grid_group = model.sets[struct]
            # elif len(list(struct)) > 0:
            #     grid_group = model.add_set1(idutil.get_next_set_id(), list(struct))  # TODO: use SET2
            # else:
            #     raise Exception('Structural grid set for Splines could not be created.')

            grid_group = self.model.add_set2(self.idutil.get_next_set_id(), elem.eid, -0.01, 1.01, -0.01, 1.01)

            # Linear Spline (SPLINE2) element
            self.model.add_spline2(self.idutil.get_next_spline_id(),
                                   caero=elem.eid,
                                   # Coordinate system of the CAERO5 element
                                   # (Y-Axis must be colinear with "Elastic Axis")
                                   cid=cords[i].cid,
                                   id1=elem.eid,
                                   id2=elem.eid + superpanel.nspan - 1,
                                   setg=grid_group.sid,
                                   # Detached bending and torsion (-1 -> infinity flexibility), only Z displacement
                                   # allowed to comply with the rigid chord necessity of the Piston Theory
                                   # and still model the plate bending (with N chord-wise elements).
                                   dthx=-1.,
                                   dthy=-1.,
                                   dz=0)

    def write_cards(self, subcase_id):
        print("Writing cards...")

        # Executive Control
        self.model.sol = 145  # Aerodynamic Flutter
        diagnostic = 'DIAG '
        for diag in self.diags:
            diagnostic += '%d,' % diag
        self.model.executive_control_lines = [diagnostic]

        # Case Control
        cc = CaseControlDeck([])

        for key in self.subcases.keys():
            fmethod, method = self.write_cards_from_subcase(key)
            cc.create_new_subcase(key)
            cc.add_parameter_to_local_subcase(1, 'DISPLACEMENT = ALL')
            cc.add_parameter_to_local_subcase(1, 'FMETHOD = %d' % fmethod)
            cc.add_parameter_to_local_subcase(1, 'METHOD = %d' % method)
            # BC ID TODO: let user select the SPC
            cc.add_parameter_to_local_subcase(1, 'SPC = %d' % list(self.model.spcs.keys())[0])
        self.model.case_control_deck = cc

        # params
        for key, param in self.params.items():
            if hasattr(param, '__iter__'):
                self.model.add_param(key=key, values=list(param))
            else:
                self.model.add_param(key=key, values=[param])

        for spanel in self.superpanels:
            self.write_superpanel_cards(spanel, self.subcases[subcase_id])

        # Validate
        self.model.validate()

        print('Aerodynamic Flutter solution created!')
        # print(model.get_bdf_stats())

    def export_to_bdf(self, output_bdf):
        # Write output
        print('Writing bdf file...')
        self.model.write_bdf(output_bdf)
        print('Done!')


class FlutterAnalysis:
    """
    This class represents the requirements to the Aeroelastic Flutter Solution 145 of NASTRAN.
    """

    FMETHODS = {
        1: 'K',
        2: 'PK',
        3: 'PKNL',
        4: 'KE',
    }

    def __init__(self, ref_rho=None, ref_chord=None, n_modes=None,
                 frequency_limits=None, densities_ratio=None, machs=None, alphas=None,
                 reduced_frequencies=None, velocities=None, method=None):
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
    def create_from_data(cls, data):
        return FlutterAnalysis(
            ref_rho=data['ref_rho'],
            ref_chord=data['ref_chord'],
            n_modes=data['n_modes'],
            frequency_limits=data['frequency_limits'],
            densities_ratio=data['densities_ratio'],
            machs=data['machs'],
            alphas=data['alphas'],
            reduced_frequencies=data['reduced_frequencies'],
            velocities=data['velocities'],
            method=data['method']
        )

    @classmethod
    def create_from_yaml_file(cls, file):
        with open(file, 'r') as file:
            data = yaml.safe_load(file)
        return FlutterAnalysis.create_from_data(data)


def _get_last_id_from_ids(elements):
    return elements[-1] if elements else 0


class IDUtility:

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
