
def set_object_properties(obj, data_dict):
    for key, val in data_dict.items():
        setattr(obj, key, val)

def _get_last_id_from_ids(elements):
    return elements[-1] if elements else 0

class IdUtility:
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
    
    def get_last_sid(self):
        return _get_last_id_from_ids(list(self.model.spcs.keys()))

    def get_next_sid(self):
        return self.get_last_sid() + 1
