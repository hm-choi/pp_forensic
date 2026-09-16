import random
import heaan as hn
import numpy as np
import pandas as pd
from engine.engine import HEEngine
from operators.operator import HEOperator
from operators.inv_sqrt import HEStatistics
import time

class HEForensicTest:
    def __init__(self, engine:HEEngine):
        self._engine = engine
        self.__ho = HEOperator(engine)
        self.__hs = HEStatistics(engine)

    def encrypt_param(self, value):
        """Encrypt one query parameter, broadcast to every slot."""
        ho = self.__ho
        arr = np.full(self._engine.num_slots(), float(value), dtype=np.float64)
        return ho.encrypt(arr)

    def detect_speed_increase(self, speed_data, max_speed=200):
        """
        Detect whether vehicle speed increased between consecutive timestamps.
        No query parameter: the log is compared against itself.
        """
        ho = self.__ho
        hs = self.__hs
        norm_speed = ho.mult_const(speed_data, 1/max_speed)
        speed_ctxt = ho.rotation(norm_speed, 32768-1)
        speed_ctxt = ho.sub(norm_speed, speed_ctxt)
        return hs.he_step(speed_ctxt)

    def detect_overspeed(self, speed_data, enc_threshold, max_speed=200):
        """
        Mark slots above the threshold. enc_threshold holds the threshold in
        km/h. The subtraction comes before the normalization so that both
        operands are freshly encrypted and sit at the same level.
        """
        ho = self.__ho
        hs = self.__hs
        diff = ho.sub(speed_data, enc_threshold)
        speed_ctxt = ho.mult_const(diff, 1/max_speed)
        return hs.he_step(speed_ctxt)

    def time_range(self, time_ctxt, enc_start, enc_end, range):
        """
        Mark slots inside the observation window. Both bounds are ciphertexts;
        range is the public normalization width.
        """
        ho = self.__ho
        hs = self.__hs

        start_ctxt = ho.sub(time_ctxt, enc_start)
        start_ctxt = ho.mult_const(start_ctxt, 1/range)
        ctxt1 = hs.he_step(start_ctxt)

        end_ctxt = ho.sub(time_ctxt, enc_end)
        end_ctxt = ho.mult_const(end_ctxt, -1/range)
        ctxt2 = hs.he_step(end_ctxt)

        return ho.mult(ctxt1, ctxt2)

    def compute_geofence_score(self, enc_x, enc_y,
                               enc_center_x, enc_center_y, enc_radius):
        """
        Mark slots inside the query circle. Coordinates are EPSG:5186 metres
        divided by the public normalization width, both done in the clear
        before encryption, so the circuit holds no latitude dependent constant.
        The radius is normalized the same way and squared inside the circuit,
        which puts it at the level the squared distance reaches.
        """
        ho = self.__ho
        hs = self.__hs

        sub_x = ho.sub(enc_x, enc_center_x)
        sub_y = ho.sub(enc_y, enc_center_y)

        dx2 = ho.mult(sub_x, sub_x)
        dy2 = ho.mult(sub_y, sub_y)
        dist = ho.add(dx2, dy2)

        r2 = ho.mult(enc_radius, enc_radius)

        score = ho.sub(r2, dist)
        return hs.he_step(score)

    def detect_phone_match(self, enc_segs, enc_lowers, enc_uppers):
        """
        Mark slots whose phone number matches the target in every group.
        The bounds arrive as ciphertexts, so the target is never in the clear.
        """
        ho = self.__ho
        hs = self.__hs
        result = None
        for enc, enc_lower, enc_upper in zip(enc_segs, enc_lowers, enc_uppers):
            lower_ctxt = ho.sub(enc, enc_lower)
            ctxt1 = hs.he_step(lower_ctxt)

            upper_ctxt = ho.sub(enc, enc_upper)
            upper_ctxt = ho.mult_const(upper_ctxt, -1.0)
            ctxt2 = hs.he_step(upper_ctxt)

            seg = ho.mult(ctxt1, ctxt2)

            if result is None:
                result = seg
            else:
                result = ho.do_bootstrapping(result, 5)
                seg = ho.do_bootstrapping(seg, 5)
                result = ho.mult(result, seg)
        return result

    def detect_phone_exists(self, match_ctxt, max_count=32):
        """
        Return 1 if at least one slot matched, 0 otherwise.
        max_count is a public bound on the match count, declared in the clear.
        """
        ho = self.__ho
        hs = self.__hs
        total = ho.sum(match_ctxt, output_one=True)
        score = ho.sub_const(total, 0.5)
        score = ho.mult_const(score, 1.0 / max_count)
        score = ho.do_bootstrapping(score, 8)
        return hs.he_step(score)