
import numpy as np

class Plate:

    def __init__(self, p1, p2, p3, p4) -> None:
        self.p1 = np.array(p1)
        self.p2 = np.array(p2)
        self.p3 = np.array(p3)
        self.p4 = np.array(p4)
    
    @property
    def d12(self):
        return self.p2 - self.p1
    
    @property
    def l12(self):
        return np.linalg.norm(self.d12)

    @property
    def d14(self):
        return self.p4 - self.p1

    @property
    def l14(self):
        return np.linalg.norm(self.d14)

    @property
    def d43(self):
        return self.p3 - self.p4

    @property
    def l43(self):
        return np.linalg.norm(self.d43)

    @property
    def d23(self):
        return self.p3 - self.p2

    @property
    def l23(self):
        return np.linalg.norm(self.d23)

    @property
    def limit_points(self):
        return self.p1, self.p2, self.p3, self.p4

    def set_plate_limits(self, p1, p2, p3, p4):
        self.p1 = p1
        self.p2 = p2
        self.p3 = p3
        self.p4 = p4


class RectangularPlate(Plate):
    """
    Generic rectangular plate defined by 4 points in the space.
    """

    def __init__(self, p1, p2, p3, p4):
        super().__init__(p1, p2, p3, p4)

    @property
    def n12(self):
        return self.d12/self.chord

    @property
    def n14(self):
        return self.d14/self.span

    @property
    def normal(self):
        vec = np.cross(self.d12, self.d14)
        return vec/np.linalg.norm(vec)

    @property
    def span(self):
        return np.linalg.norm(self.d14)

    @property
    def b(self):
        return self.span

    @property
    def chord(self):
        return np.linalg.norm(self.d12)

    @property
    def a(self):
        return self.chord