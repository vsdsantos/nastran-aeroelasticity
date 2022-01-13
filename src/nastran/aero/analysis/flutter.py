
from typing import Dict
from pyNastran.bdf.bdf import BDF, CaseControlDeck

from nastran.analysis import AnalysisModel, Subcase

# import yaml

FMETHODS = {
    1: 'K',
    2: 'KE',
    3: 'PK',
    4: 'PKNL',
    5: 'PKS',  # only on recent MSC.Nastran versions
    6: 'PKNLS'  # only on recent MSC.Nastran versions
}

class FlutterSubcase(Subcase):
    """
    This class represents the requirements to the Aeroelastic Flutter Solution 145 of NASTRAN.
    """

    def __init__(self, id, spc=None, fmethod=None, method=None, **args):
        super().__init__(id, spc=spc, load=None, **args)
        self.fmethod = fmethod
        self.method = method



class FlutterAnalysisModel(AnalysisModel):
    """
    Class for the Nastran's SOL 145

    It can be used for conventional wing or aircraft flutter.
    """

    def __init__(self, model: BDF = None, global_case = None,
                 subcases: Dict[int, Subcase] = {},
                 params=None, diags=None, interface=None):
        super().__init__(model=model,
            global_case=global_case, subcases=subcases,
            params=params, diags=diags,
            sol=145, interface=interface)

    def write_cards(self):
        super().write_cards()

    def _write_machs_and_alphas(self, machs, alphas):
        # TODO: Vary with the used flutter solution method

        if self.global_case.method == 'PK':
            aefact = self.model.add_aefact(self.idutil.get_next_aefact_id(),
                                     [v for ma in zip(machs, alphas) for v in ma])
        else:
            raise Exception('Selected {} method is not implemented'.format(self.global_case.method)) 

        return aefact

    def _write_global_analysis_cards(self):

        # defines FLFACT cards
        densities_ratio = self.model.add_flfact(self.idutil.get_next_flfact_id(), self.global_case.densities_ratio)
        machs = self.model.add_flfact(self.idutil.get_next_flfact_id(), self.global_case.machs)
        velocities = self.model.add_flfact(self.idutil.get_next_flfact_id(), self.global_case.velocities)


        # defines FLUTTER card for flutter subcase
        fmethod = self.model.add_flutter(self.idutil.get_next_flutter_id(),
                                         method=self.global_case.method,
                                         density=densities_ratio.sid,
                                         mach=machs.sid,
                                         reduced_freq_velocity=velocities.sid)

        # real eigenvalue method card
        method = self.model.add_eigrl(sid=self.idutil.get_next_method_id()+100,
                                      norm='MASS',
                                      nd=self.global_case.n_modes,
                                      v1=self.global_case.frequency_limits[0],
                                      v2=self.global_case.frequency_limits[1])
        
        # AERO card
        self.model.add_aero(cref=self.global_case.ref_chord, rho_ref=self.global_case.ref_rho, velocity=1.0)

        # MKAERO1 cards
        self.model.add_mkaero1(self.global_case.machs, self.global_case.reduced_frequencies)

        cc = self.model.case_control_deck

        cc.add_parameter_to_global_subcase('FMETHOD = %d' % fmethod.sid)  # the flutter card id
        cc.add_parameter_to_global_subcase('METHOD = %d' % method.sid)  # the eigenval analysis card id


        
