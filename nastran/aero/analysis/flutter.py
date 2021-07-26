
from pyNastran.bdf.bdf import CaseControlDeck

from nastran.analysis import AnalysisModel, Subcase

import yaml

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

    def __init__(self, model=None, method='PK', ref_rho=None, ref_chord=None, n_modes=None,
                 frequency_limits=None, densities_ratio=None, machs=None, alphas=None,
                 reduced_frequencies=None, velocities=None, spc=None):
        super().__init__(model=model)
        self.panels = []
        self.sol = 145
        self.method = method
        self.ref_rho = ref_rho
        self.ref_chord = ref_chord
        self.n_modes = n_modes
        self.frequency_limits = frequency_limits
        self.densities_ratio = densities_ratio
        self.machs = machs
        self.alphas = alphas
        self.reduced_frequencies = reduced_frequencies
        self.velocities = velocities
        self.spc = spc

    def write_machs_and_alphas(self, machs, alphas):
        # TODO: Vary with the used flutter solution method

        if self.method == 'PK':
            aefact = self.model.add_aefact(self.idutil.get_next_aefact_id(),
                                     [v for ma in zip(machs, alphas) for v in ma])
        else:
            raise Exception('Flutter method not implemented') 

        return aefact

    def write_global_analysis_cards(self):

        # defines FLFACT cards
        densities_ratio = self.model.add_flfact(self.idutil.get_next_flfact_id(), self.densities_ratio)
        machs = self.model.add_flfact(self.idutil.get_next_flfact_id(), self.machs)
        velocities = self.model.add_flfact(self.idutil.get_next_flfact_id(), self.velocities)


        # defines FLUTTER card for flutter subcase
        fmethod = self.model.add_flutter(self.idutil.get_next_flutter_id(),
                                         method=self.method,
                                         density=densities_ratio.sid,
                                         mach=machs.sid,
                                         reduced_freq_velocity=velocities.sid)

        # real eigenvalue method card
        method = self.model.add_eigrl(sid=self.idutil.get_next_method_id(),
                                      norm='MASS',
                                      nd=self.n_modes,
                                      v1=self.frequency_limits[0],
                                      v2=self.frequency_limits[1])
        
        # AERO card
        self.model.add_aero(cref=self.ref_chord, rho_ref=self.ref_rho, velocity=1.0)

        # MKAERO1 cards
        self.model.add_mkaero1(self.machs, self.reduced_frequencies)

        return fmethod.sid, method.sid


    def write_case_control_cards(self):
        # Case Control
        cc = CaseControlDeck([])

        fmethod, method = self.write_global_analysis_cards()

        cc.add_parameter_to_global_subcase('FMETHOD = %d' % fmethod)  # the flutter card id
        cc.add_parameter_to_global_subcase('METHOD = %d' % method)  # the eigenval analysis card id

        for key, subcase in self.subcases.items():
            cc.create_new_subcase(key)
            self.write_case_control_from_list(cc, key, subcase)

        self.model.case_control_deck = cc
