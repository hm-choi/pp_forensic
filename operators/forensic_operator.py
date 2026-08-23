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
        return hs.he_sign(speed_ctxt)

    def detect_overspeed(self, speed_data, threas_hold=60.0, max_speed=200):
        ho = self.__ho
        hs = self.__hs
        norm_speed = ho.mult_const(speed_data, 1/max_speed)
        speed_ctxt = ho.sub_const(norm_speed, threas_hold/200)
        return hs.he_sign(speed_ctxt)