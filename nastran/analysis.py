from abc import ABC, abstractmethod

import yaml
from pyNastran.bdf.bdf import BDF, CaseControlDeck

from nastran.utils import IdUtility, set_object_properties


class Subcase:
    """
    Represents a NASTRAN subcase with CASE CONTROL statements.
    """

    def __init__(self, case_control=None):
        self.case_control = case_control

    @classmethod
    def create_from_dict(cls, data):
        obj = cls()
        set_object_properties(obj, data)
        return obj

class AnalysisModel(ABC):

    def __init__(self):
        self.model = BDF(debug=False)
        self.idutil = IdUtility(self.model)
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
            self.idutil = IdUtility(self.model)

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
            self.create_subcase_from_dict(key, data=subcase)

    @abstractmethod
    def create_subcase_from_file(self, sub_id, subcase_file_name):
        pass

    @abstractmethod
    def create_subcase_from_dict(self, sub_id, data):
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

    def write_case_control_from_list(self, cc, subid, subcase):
        if subcase.case_control is not None:
            for card in subcase.case_control:
                cc.add_parameter_to_local_subcase(subid, card)

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

