
from nastran.analysis import AnalysisModel


class BCType:
    
    def __init__(self, label, ids, desc):
        self.label = label
        self.ids = ids
        self.desc = desc

        
class PanelBC:
    
    def __init__(self, bcs, label):
        self.bcs = bcs
        self.label = label
        
    def get_bc_ids(self):
        return [ bc.ids for bc in self.bcs]

BCTYPES = {
    'S': BCType('S', '123', 'Simply Supported'),
    'C': BCType('C', '123456', 'Clamped'),
    'F': BCType('F', '', 'Free'),
    'V': BCType('V', '3', 'Vertical Constrained'),
}

def generate_bc_cases(labels_lst):
    return { i: generate_bc_case(l) for i, l in enumerate(labels_lst) }

def generate_bc_case(labels):
    """
        labels pattern -> '1234' -> 'SSCF'
        -------------------    ^ y
    V   |        F        |    |
    ->  |       (4)       |    --->
    ->  |                 |        x
    ->  | S(1)       (2)S |
    ->  |                 |
        |       (3)       |
        |        C        |
        -------------------
    """
    return PanelBC([BCTYPES[c] for c in labels], labels)
        
def create_spcs_and_subcases(analysis: AnalysisModel, cases, nodes, subcase_class):

    for label, spc in create_spcs(analysis, cases, nodes):
        sub_config = {
            'LABEL': label,
            'SPC': spc.conid,
        }
        analysis.create_subcase_from_dict(subcase_class, spc.conid, sub_config)

def create_global_case(analysis: AnalysisModel, spc):
    analysis.set_global_case_from_dict(subcase_class, i, sub_config)

def create_spcs(analysis: AnalysisModel, spcs_dict, nodes):
    for i, spcs in spcs_dict.items():
        spc_id = analysis.idutil.get_next_sid()
        for comp, nds in zip(spcs.get_bc_ids(), nodes):
            if comp == '':
                continue
            else:
                yield (spcs.label, analysis.model.add_spc1(spc_id, comp, nds, comment=spcs.label))

def create_springs(analysis, nodes):
    
    nid = analysis.idutil.get_next_node_id()
    eid = analysis.idutil.get_next_element_id()
    pid = 10 # analysis.idutil.get_next_pid()

    analysis.model.add_pbush(pid, [1000., 0., 0., 0., 0., 0.], [0.]*6, [0.]*6)

    dvec = [[-1, 0, 0], [1, 0, 0], [0, -1, 0], [0, 1, 0]]

    for nds, vec in zip(nodes, dvec):
        for grid in nds:
            g = analysis.model.add_grid(nid, analysis.model.nodes[grid].xyz + vec)
            analysis.model.add_cbush(eid, pid, [grid, g.nid], [0., 0., 1.], None)
            nid += 1
            eid += 1
            for k in analysis.model.spcs.keys():
                analysis.model.add_spc1(k, '123456', g.nid, comment='spring fixed')
            nid += 1
                                     