
from engine.engine import HEEngine
import heaan as hn
import numpy as np
from hedata.data import HEData
from operators.operator import HEOperator
import math, json

SIGN_DATA_PPSTAT = [
    [0.0, 0.6390288304082614, 0.0, -0.21980608429103932, 0.0, 0.1414400337738291, 0.0, -0.5606627743680413],
    [0.0, 0.6371463326157922, 0.0, -0.21380325827579392, 0.0, 0.13004393762977677, 0.0, -0.09488428074246866, 0.0, 0.07604178502209895, 0.0, -0.06477148515021864, 0.0, 0.05779044360437681, 0.0, -0.5275634049964796],
    [0.0, 0.6371468493346175, 0.0, -0.21380342955981532, 0.0, 0.13004403924162435, 0.0, -0.09488435206009798, 0.0, 0.07604183915280832, 0.0, -0.06477152803371908, 0.0, 0.05779047842540584, 0.0, -0.5275630145730114],
    [0.0, 1.2734862773297655, 0.0, -0.42515524234253814, 0.0, 0.25589093343467156, 0.0, -0.1836449020797226, 0.0, 0.14374882333912232, 0.0, -0.11856926750825473, 0.0, 0.10132742430142789, 0.0, -0.08886318390233084, 0.0, 0.07950707992755427, 0.0, -0.07229645059378168, 0.0, 0.06663972992977957, 0.0, -0.06215617007060851, 0.0, 0.05859285562339639, 0.0, -0.055779073936309355, 0.0, 0.053600206686888685, 0.0, -1.0262829544919159]
]

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
  
    def he_inv_sqrt(self, ct:HEData, degree=6):
        if ct.level() < degree+3:
            self._ho.do_bootstrapping(ct, 11)
        tmp = self.chebyshev_inv_sqrt(ct, B = 2, degree=degree)
        tmp = self._ho.do_bootstrapping(tmp, 11)
        return self.he_newtons_method(ct, tmp, 7)

    def he_newtons_method(self, x:HEData, y:HEData, iteration:int=10):
        N = 2.0

        x = self._ho.mult_const(x, 0.5)
        if x.level() <= 4:
            x = self._ho.do_bootstrapping(x, 11)

        tmp_a = self._ho.copy_new(x)
        tmp_b = self._ho.copy_new(y)

        for iter in range(iteration):
            if y.level() <= 4:
                y = self._ho.do_bootstrapping(y, 11)

            tmp_a = self._ho.mult_const(y, (N+1)/(N))
            tmp_b = self._ho.mult(x, y)

            y_sqr = self._ho.mult(y, y)

            tmp_b = self._ho.mult(tmp_b, y_sqr)
            y = self._ho.sub(tmp_a, tmp_b)
        return y
 

    def chebyshev_inv_sqrt(self, ct:HEData, B = 1, degree:int=6):
        mode = 3
        if degree == 9:
            with open("hmchoi2/coefficients/Cbsb510.json", "r") as f:
                data = json.load(f)
        elif degree == 8:
            with open("hmchoi2/coefficients/Cbsp254.json", "r") as f:
                data = json.load(f)
        elif degree == 7:
            with open("hmchoi2/coefficients/Cbsp126.json", "r") as f:
                data = json.load(f)
        elif degree == 6:
            with open("hmchoi2/coefficients/Cbsp62.json", "r") as f:
                data = json.load(f)
        elif degree == 5:
            with open("hmchoi2/coefficients/Cbsp30.json", "r") as f:
                data = json.load(f)
        elif degree == 4:
            with open("hmchoi2/coefficients/Cbsp14.json", "r") as f:
                data = json.load(f)


        ctxts = []
        for c in ct.ciphertexts():

            new_ct = hn.Ciphertext(c)

            if mode == 1:
                if degree == 8:
                    self._engine.evaluator().mult(ct, 2/B, new_ct)
                cbsp = [np.float64(x[0]) / ((B/2) ** (1/2)) for x in data]
            elif mode == 2:
                cbsp = [np.float64(x[0]) / (B ** (1/2)) for x in data]
            elif mode == 3:
                cbsp = [np.float64(x[0]) for x in data]
            else:
                return None

            self._engine.evaluator().sub(new_ct, 1, new_ct)
            
            hn_cbsp = hn.math.approx.ChebyshevCoefficients(np.array(cbsp), len(cbsp))

            ret = hn.math.approx.evaluate_chebyshev_expansion(self._engine.evaluator(), self._engine.bootstrapping(), new_ct, hn_cbsp, 1.0)

            ctxts.append(ret)
        
        return HEData(ctxts, ct.size(), ret.level, ct.scale())
 
    def chebyshev_sqrt(self, ct:HEData, B = 1, degree:int=8):
        mode = 3
        if degree == 9:
            with open("hmchoi2/coefficients/Sqrt_Cheb510.json", "r") as f:
                data = json.load(f)
        elif degree == 8:
            with open("hmchoi2/coefficients/Sqrt_Cheb254.json", "r") as f:
                data = json.load(f)
        elif degree == 7:
            with open("hmchoi2/coefficients/Sqrt_Cheb126.json", "r") as f:
                data = json.load(f)
        elif degree == 6:
            with open("hmchoi2/coefficients/Sqrt_Cheb62.json", "r") as f:
                data = json.load(f)
        elif degree == 5:
            with open("hmchoi2/coefficients/Sqrt_Cheb30.json", "r") as f:
                data = json.load(f)
        # elif degree == 4:
        #     with open("hmchoi2/coefficients/Cbsp14.json", "r") as f:
        #         data = json.load(f)


        ctxts = []
        for c in ct.ciphertexts():

            new_ct = hn.Ciphertext(c)
            mode = 3
            if mode == 1:
                if degree == 8:
                    self._engine.evaluator().mult(ct, 2/B, new_ct)
                cbsp = [np.float64(x[0]) / ((B/2) ** (1/2)) for x in data]
            elif mode == 2:
                cbsp = [np.float64(x[0]) / (B ** (1/2)) for x in data]
            elif mode == 3:
                cbsp = [np.float64(x[0]) for x in data]
            else:
                return None

            self._engine.evaluator().sub(new_ct, 1, new_ct)
            
            hn_cbsp = hn.math.approx.ChebyshevCoefficients(np.array(cbsp), len(cbsp))

            ret = hn.math.approx.evaluate_chebyshev_expansion(self._engine.evaluator(), self._engine.bootstrapping(), new_ct, hn_cbsp, 1.0)

            ctxts.append(ret)
        
        return HEData(ctxts, ct.size(), ret.level, ct.scale())

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
                if i != len(coeffs) - 1:
                    next_depth = math.ceil(math.log2(len(coeffs[i + 1]) - 1))
                    if tmp_ct.level - next_depth < 3:
                        self._engine.bootstrapping().bootstrap(tmp_ct, tmp_ct)
            result_ctxt.append(tmp_ct)    
        return HEData(result_ctxt, x.size(), result_ctxt[0].level, x.scale())

    def inv_sqrt_without_bts(self, x:HEData, y:HEData, iteration:int=10):
        N = 2.0
    
        x = self._ho.mult_const(x, 0.5)
        if x.level() <= 4:
            tmp = self._ho.decrypt(x, True)
            x = self._ho.encrypt(tmp)


        tmp_a = self._ho.copy_new(x)
        tmp_b = self._ho.copy_new(y)

        for iter in range(iteration):
            if y.level() < 4:
                tmp = self._ho.decrypt(y, True)
                y = self._ho.encrypt(tmp)

            tmp_a = self._ho.mult_const(y, (N+1)/(N))
            tmp_b = self._ho.mult(x, y)

            y_sqr = self._ho.mult(y, y)

            tmp_b = self._ho.mult(tmp_b, y_sqr)
            y = self._ho.sub(tmp_a, tmp_b)
        return y

    def inv_without_bts(self, x:HEData, y:HEData, iteration:int=10):
        inv_sqrt = self.inv_sqrt_without_bts(x, y, iteration)
        if inv_sqrt.level() < 4:
            tmp = self._ho.decrypt(inv_sqrt, True)
            inv_sqrt = self._ho.encrypt(tmp)
        inv = self._ho.mult(inv_sqrt, inv_sqrt)
        return inv

 