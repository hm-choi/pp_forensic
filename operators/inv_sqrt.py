"""Composite sign and step function on CKKS ciphertexts.

Adapted from the PP-STAT implementation by Hyunmin Choi, which was itself
ported from an earlier Go implementation.
Reference: H. Choi, "PP-STAT: An Efficient Privacy-Preserving Statistical
Analysis Framework Using Homomorphic Encryption," CIKM '25.
"""
from . import bscount
from engine.engine import HEEngine
import heaan as hn
import numpy as np
from hedata.data import HEData
from operators.operator import HEOperator
import math

SIGN_DATA_PPSTAT = [
	[0, 0.639028938435711219, 0, -0.219806118878047092, 0, 0.141440053455946451, 0, -0.560662696277302517],
	[0, 0.639029489633228222, 0, -0.219806297800259927, 0, 0.141440154749489224, 0, -0.560662301247238699],
	[0, 0.637154696201570660, 0, -0.213806030962452086, 0, 0.130045580652836942, 0, -0.094885435152665168, 0, 0.076042662624281770, 0, -0.064772177102166506, 0, 0.057791006255316676, 0, -0.527557080198263608],
	[0, 0.637252723778154157, 0, -0.213838525423059134, 0, 0.130064857400618902, 0, -0.094898964641665779, 0, 0.076052931457460596, 0, -0.064780312107983876, 0, 0.057797611601832795, 0, -0.527483011957071916],
	[0, 0.638492548163143535, 0, -0.214249489332586510, 0, 0.130308633915153971, 0, -0.095070037868134732, 0, 0.076182750613643440, 0, -0.064883127935866152, 0, 0.057881063854726339, 0, -0.526546163851403631],
	[0, 0.654072536322215222, 0, -0.219411111586902031, 0, 0.133367149639755852, 0, -0.097212758106646793, 0, 0.077804778872091079, 0, -0.066163376778950260, 0, 0.058915286191840665, 0, -0.514764737657234364],
	[0, 0.985321201923117642, 0, -0.328119170883870823, 0, 0.196617511234660686, 0, -0.140045613570337270, 0, 0.108634034466585055, 0, -0.088498752002149384, 0, 0.074572306762014301, 0, -0.064287415234822877, 0, 0.056401814845377282, 0, -0.050183389367761095, 0, 0.045086211659977983, 0, -0.040959900956987588, 0, 0.037395730021827179, 0, -0.034512330854589498, 0, 0.031915520720098515, 0, -0.241509663775553008],
	[0, 1.262673861720083096, 0, -0.393697035515367173, 0, 0.206535085221700125, 0, -0.120395410087615135, 0, 0.071169308776617400, 0, -0.041082546981498569, 0, 0.022667637149739957, 0, -0.011770429894589077, 0, 0.005672674575918509, 0, -0.002500516475970389, 0, 0.000990582083790523, 0, -0.000344556747529926, 0, 0.000101727287456808, 0, -0.000024132899916296, 0, 0.000004146320405856, 0, -0.000000395353444811],
]

class HEStatistics:
    def __init__(self, engine:HEEngine):
        self._engine = engine 
        self._ho = HEOperator(engine)
  
    def he_sign(self, x:HEData):
        if x is None:
            raise ValueError("ciphertext is None")
        coeffs = [np.array(row, dtype=np.float64) for row in SIGN_DATA_PPSTAT]

        ret = self._ho.copy_new(x)

        result_ctxt = []

        for ct in ret.ciphertexts():
            tmp_ct = ct
            for i, c in enumerate(coeffs):
                deg = len(c) - 1
                if (deg & (deg + 1)) == 0:
                    hn_cbsp = hn.math.approx.ChebyshevCoefficients(c, deg + 1)
                else:
                    hn_cbsp = hn.math.approx.ChebyshevCoefficients(c, deg)
                tmp_ct = hn.math.approx.evaluate_chebyshev_expansion(self._engine.evaluator(), self._engine.bootstrapping(), tmp_ct, hn_cbsp, 1.0)
                bscount.add_chebyshev()
                if i != len(coeffs) - 1:
                    next_depth = math.ceil(math.log2(len(coeffs[i + 1]) - 1))
                    if tmp_ct.level - next_depth < 3:
                        self._engine.bootstrapping().bootstrap(tmp_ct, tmp_ct)
                        bscount.add_bootstrap()
            result_ctxt.append(tmp_ct)    
        return HEData(result_ctxt, x.size(), result_ctxt[0].level, x.scale())

    def he_step(self, x:HEData):

        signed = self.he_sign(x)
        x = self._ho.mult_const(signed, 0.5)
        return self._ho.add_const(x, 0.5)
