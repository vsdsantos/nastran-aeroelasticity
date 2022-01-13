from abc import ABC, abstractmethod
from typing import Dict, Type
from numpy.lib.utils import deprecate

# import yaml
from pyNastran.bdf.bdf import BDF, CaseControlDeck

from nastran.utils import IdUtility, set_object_properties

class ExecutiveControl:
    pass

class CaseControl:

    @classmethod
    def create_from_dict(cls, data, **args):
        cc = cls()
        set_object_properties(cc, data)
        return cc

class Subcase(CaseControl):
    """
    Represents a NASTRAN subcase with CASE CONTROL statements.
    """

    def __init__(self, id, spc=None, load=None, **args):
        self.id = id
        self.spc = spc
        self.load = load
        set_object_properties(self, args)

    @property
    def properties(self):
        return self.__dict__

    # @classmethod
    # def create_from_yaml(cls, file_name):
    #     with open(file_name, 'r') as file:
    #         data = yaml.safe_load(file)
    #     return cls.create_from_dict(data['id'], data)

    @classmethod
    def create_from_dict(cls, sub_id, data):
        subcase = cls(sub_id)
        set_object_properties(subcase, data)
        return subcase

class AnalysisModel(ABC):
    
    def __init__(self, model:BDF=None,
                 global_case=None,
                 subcases:Dict[int,Subcase]=None,
                 params=None,
                 diags=None,
                 sol=None,
                 interface=None):
        self.model = model if model is not None else BDF(debug=False)
        self.idutil = IdUtility(self.model)
        self.global_case = global_case if global_case is not None else CaseControl()
        self.subcases = subcases if subcases is not None else {}
        self.params = params
        self.diags = diags
        self.sol = sol
        self.interface = interface

    def __repr__(self) -> str:
        return self.model.get_bdf_stats()

    @deprecate
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

    # @deprecate
    # def load_analysis_from_yaml(self, yaml_file_name: str):
    #     with open(yaml_file_name, 'r') as file:
    #         data = yaml.safe_load(file)
    #     self.params = data['params']
    #     self.diags = data['diags']
    #     self.interface = data['interface']
    #     for key, subcase in data['subcases'].items():
    #         self.create_subcase_from_dict(Subcase, key, subcase)

    def set_global_case_from_dict(self, data):
        self.global_case = CaseControl.create_from_dict(data)

#     def create_subcase_from_yaml(self, sub_type: Type[Subcase], sub_id, subcase_file_name):
#         # assert sub_id not in self.subcases.keys()
        
#         sub = sub_type.create_from_yaml(subcase_file_name)
#         self.subcases[sub_id] = sub

#         return sub

    def create_subcase_from_dict(self, sub_type: Type[Subcase], sub_id, sub_dict):
        # assert sub_id not in self.subcases.keys()

        sub = sub_type.create_from_dict(sub_id, sub_dict)
        self.subcases[sub_id] = sub

        return sub

    def create_subcase(self, sub_type: Type[Subcase], sub_id):
        # assert sub_id not in self.subcases.keys()
        
        sub = sub_type.create_from_dict()
        self.subcases[sub_id] = sub

        return sub

    def export_to_bdf(self, output_bdf):
        # Write output
        print('Writing bdf file...')
        self.model.write_bdf(output_bdf, enddata=True)
        print('Done!')

    def write_cards(self):
        self.model.case_control_deck = CaseControlDeck([])
        self._write_executive_control_cards()
        self._write_case_control_cards()
        self._write_params()

        # Validate
        self.model.validate()

    def _write_executive_control_cards(self):
        # Executive Control
        self.model.sol = self.sol

        # TODO: diagnostic doesn't work
        # diagnostic = 'DIAG '
        # for diag in self.diags:
        #     diagnostic += '%d,' % diag
        # self.model.executive_control_lines = [diagnostic]

    def _write_case_control_subcase(self, subcase: Subcase):
        # if subcase.case_control is not None:
        for key, value in subcase.properties.items():
            if key in ['id',] or value is None:
                continue
            self.model.case_control_deck.add_parameter_to_local_subcase(
                subcase.id,
                '{} = {}'.format(key.upper(), value))

    def _write_case_control_cards(self):
        # Case Control
        cc = self.model.case_control_deck

        self._write_global_analysis_cards()

        for _, subcase in self.subcases.items():
            cc.create_new_subcase(subcase.id)
            self._write_case_control_subcase(subcase)
        self.model.case_control_deck = cc

    def _write_global_analysis_cards(self):
        pass

    def _write_params(self):
        # params
        for key, param in self.params.items():
            if hasattr(param, '__iter__'):  # check if object is iterable
                self.model.add_param(key=key, values=list(param))
            else:
                self.model.add_param(key=key, values=[param])

