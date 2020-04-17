import pythoncom
from femap import PyFemap
import sys
from femap.PyFemap import constants


class Femap:
    """
    Femap Connection Interface
    """

    def __init__(self):
        try:
            existingobj = pythoncom.connect(PyFemap.model.CLSID)
            self.model = PyFemap.model(existingobj)
        except:
            self.model = None
            sys.exit("Femap not openned")
        self.model.feAppMessage(constants.FPS_MESSAGES, "Connection with Python openned!")

    def export_structural_model(self, file: str):
        self.model.feFileWriteNeutral(0, file, False, True, False, True, True, False, 20, 0.0, 0)

    def export_bdf_model(self, file: str):
        self.model.feFileWriteNastran(8, file)

    def get_xyz(self, text: str):
        [res, xyz] = self.model.feCoordPick(text)
        return xyz

    def get_node_ids_array(self, text: str):
        node_set = self.get_node_set(text)
        [rc, num, ids] = node_set.GetArray()
        return ids

    def get_ids_array_from_group(self, text: str):
        group = self.get_group(text)
        node_set = group.List(constants.FT_NODE)
        [rc, num, ids] = node_set.GetArray()
        return ids

    def get_group(self, text: str) -> PyFemap.Group:
        group_entity: PyFemap.Group = self.model.feGroup
        group_entity.SelectID(text)
        return group_entity

    def get_group_id(self, text: str) -> int:
        return self.get_group(text).ID

    def get_node(self, text: str) -> PyFemap.Node:
        node_entity: PyFemap.Node = self.model.feNode
        node_entity.SelectID(text)
        return node_entity

    def get_node_set(self, text: str) -> [int]:
        set_entity: PyFemap.Set = self.model.feSet
        set_entity.Select(constants.FT_NODE, True, text)
        return set_entity

    def user_int_input(self, text: str):
        [rc, val] = self.model.feGetInt(text, 1, 999999)
        return val
