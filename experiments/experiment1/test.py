import random
import heaan as hn
import numpy as np
import pandas as pd
from engine.engine import HEEngine
from operators.operator import HEOperator
from operators.forensic_operator import HEForensicTest
import time


#==========================#
##  1. Generate HEEngine  ##
#==========================# 
engine = HEEngine(device_type="cpu",
    log_slots=15,
    warmup_bootstrap=True)

test1 = [1.0 for _ in range(engine.num_slots())]
hft = HEForensicTest(engine)
ho = HEOperator(engine)

#=======================#
##  2. Load Dataset    ##
#=======================# 
car_data = pd.read_csv('../../datasets/avante_accident.csv')
slot_count = 32768

#=========================#
##  3. Do Preprocessing  ##
#=========================# 
t_real = np.pad(
    car_data['t_real'].to_numpy(),
    (0, slot_count - len(car_data)),
    constant_values=-1
)
speed = np.pad(
    car_data['speed'].to_numpy(),
    (0, slot_count - len(car_data)),
    constant_values=0
)
rpm = np.pad(
    car_data['rpm'].to_numpy(),
    (0, slot_count - len(car_data)),
    constant_values=-1
)
seatbelt_d = np.pad(
    car_data['seatbelt_d'].to_numpy(),
    (0, slot_count - len(car_data)),
    constant_values=-1
)
seatbelt_p = np.pad(
    car_data['seatbelt_p'].to_numpy(),
    (0, slot_count - len(car_data)),
    constant_values=-1
)
call = np.pad(
    car_data['call'].to_numpy(),
    (0, slot_count - len(car_data)),
    constant_values=-1
)
 
#=====================#
##  4. Encrypt Data  ##
#=====================# 
t_real_ctxt = ho.encrypt(t_real)
speed_ctxt = ho.encrypt(speed)
rpm_ctxt = ho.encrypt(rpm)
seatbelt_d_ctxt = ho.encrypt(seatbelt_d)
call_ctxt = ho.encrypt(call)


#=====================================================#
##  5. Test the acceleration and deceleration test   ##
#=====================================================#
START_TIME = time.time()
result = hft.detect_speed_increase(speed_ctxt)
END_TIME = time.time() - START_TIME
print("속도 증가 여부 (1인 경우 속도가 증가한 것을 의미)")
print(ho.decrypt(result)[:12])
print("TIME", END_TIME, "s")
#===========================================#
##  5. Test the Speeding violation check   ##
#===========================================#
START_TIME = time.time()
THRESHOLD_TIME = 60.0
result2 = hft.detect_overspeed(speed_ctxt, THRESHOLD_TIME)
END_TIME = time.time() - START_TIME
print("속도 위반 여부 (1인 경우 속도가 60보다 크다는 것을 의미)")
print(ho.decrypt(result2)[:12])
print("TIME", END_TIME, "s")
 
