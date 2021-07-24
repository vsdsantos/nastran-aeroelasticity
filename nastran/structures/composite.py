
from pyNastran.bdf.cards.properties.shell import PCOMP

def sym_sawyer_ply(theta, nplies):
    # theta, -theta, -theta, theta
    assert nplies % 2 == 0
    thetas = []
    for i in range(int(nplies/2)):
        if i % 2 == 0:
            thetas.append(float(-theta))
        else:
            thetas.append(float(theta))
    return thetas[::-1] + thetas

def create_pcomp(analysis, thetas, thick, nplies):
    mids = [analysis.model.materials[1].mid]*nplies
    thicknesses = [thick]*nplies
    return PCOMP(1, mids, thicknesses, thetas)
