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
    
    def detect_speed_increase(self, speed_data, max_speed=200):
        """
        Detect whether vehicle speed increased between consecutive timestamps.
        """
        ho = self.__ho
        hs = self.__hs
        norm_speed = ho.mult_const(speed_data, 1/max_speed)
        speed_ctxt = ho.rotation(norm_speed, 32768-1)
        speed_ctxt = ho.sub(norm_speed, speed_ctxt)
        return hs.he_step(speed_ctxt)

    def detect_overspeed(self, speed_data, threas_hold=60.0, max_speed=200):
        ho = self.__ho
        hs = self.__hs
        norm_speed = ho.mult_const(speed_data, 1/max_speed)
        speed_ctxt = ho.sub_const(norm_speed, threas_hold/200)
        return hs.he_step(speed_ctxt)

    def time_range(self, time_ctxt, start_time, end_time, range):
        ho = self.__ho
        hs = self.__hs

        start_ctxt = ho.sub_const(time_ctxt, start_time)
        start_ctxt = ho.mult_const(start_ctxt, 1/range)
        ctxt1 = hs.he_step(start_ctxt)

        end_ctxt = ho.sub_const(time_ctxt, end_time)
        end_ctxt = ho.mult_const(end_ctxt, -1/range)
        ctxt2 = hs.he_step(end_ctxt)

        return ho.mult(ctxt1, ctxt2)
