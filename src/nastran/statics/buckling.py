from nastran.analysis import AnalysisModel, Subcase


class LinearBucklingSubcase(Subcase):

    def __init__(self, id, spc=None, **args):
        super().__init__(id, spc=spc, load=None, **args)

        
class LinearBucklingAnalysis(AnalysisModel):
    
    def __init__(self,
                 model=None,
                 global_case=None,
                 subcases=None,
                 params=None,
                 diags=None,
                 v1=0.0,
                 v2=None,
                 nd=5):
        
        super().__init__(model=model,
                 global_case=global_case,
                 subcases=subcases,
                 params=params,
                 diags=diags,
                 sol=105,
                 interface=None)
        
        self.v1 = v1
        self.v2 = v2
        self.nd = nd
        
        self.model.add_eigrl(1, v1=v1, v2=v2, nd=nd)
        
    def _write_global_analysis_cards(self):
        super()._write_global_analysis_cards()
        self.model.case_control_deck.add_parameter_to_global_subcase("METHOD = 1")
        
        