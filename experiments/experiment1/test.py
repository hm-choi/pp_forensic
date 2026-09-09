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

hft = HEForensicTest(engine)
ho = HEOperator(engine)

#=======================#
##  2. Load Dataset    ##
#=======================# 
car_data = pd.read_csv('../../datasets/sorento_drive.csv')
slot_count = 32768

#=========================#
##  3. Do Preprocessing  ##
#=========================# 
raw_lon = car_data['기지국_경도_x1e5'][0:slot_count].to_numpy()
lon = np.where(raw_lon == -1, 124.36*100000.0, raw_lon)
raw_lat = car_data['기지국_위도_x1e5'][0:slot_count].to_numpy()
lat = np.where(raw_lat == -1, 33.06*100000.0, raw_lat)

lon = lon/100000.0
lat = lat/100000.0
 
enc_lon = ho.encrypt(lon)
enc_lat = ho.encrypt(lat) 

center_lon = 127.11443
center_lat = 37.18897
radius_km = 1.0
START_TIME = time.time()
result = hft.compute_geofence_score(enc_lat, enc_lon, center_lat, center_lon, radius_km)
END_TIME = time.time() - START_TIME
print("center에 반경", radius_km, "안에 차량이 존재한 경우 TEST")
print(ho.decrypt(result)[:20])
print("TIME", END_TIME, "s")