import numpy as np
import pandas as pd
import time
import os
import sys

import heaan as hn
from engine.engine import HEEngine
from operators.operator import HEOperator
from operators.forensic_operator import HEForensicTest


#=========================#
##  0. Console logging   ##
#=========================#
# Everything printed below also goes to results/result2.txt.
os.makedirs('results', exist_ok=True)
LOG_FILE = open('results/result2.txt', 'w', encoding='utf-8')


class Tee:
    """Write to the terminal and to the log file at the same time."""

    def __init__(self, *streams):
        self.streams = streams

    def write(self, text):
        for s in self.streams:
            s.write(text)
            s.flush()

    def flush(self):
        for s in self.streams:
            s.flush()


sys.stdout = Tee(sys.__stdout__, LOG_FILE)
sys.stderr = Tee(sys.__stderr__, LOG_FILE)

#==========================#
##  1. Generate HEEngine  ##
#==========================#
engine = HEEngine(device_type="cpu",
    log_slots=15,
    warmup_bootstrap=True)

hft = HEForensicTest(engine)
ho = HEOperator(engine)

slot_count = 32768


def extremes(out, plain):
    """Worst decrypted value on each side of the decision.

    The first return value is the reading furthest from 0 among the slots the
    query excludes, and the second and third are the readings furthest from and
    closest to 1 among the slots the query includes. Every other slot is closer
    to its ideal value than these, so the pair bounds the whole result.
    """
    z = out[plain == 0]
    o = out[plain == 1]
    zmax = float(np.abs(z).max()) if z.size else float('nan')
    omin = float(o.min()) if o.size else float('nan')
    omax = float(o.max()) if o.size else float('nan')
    return zmax, omin, omax


def dump_slots(out, plain, n=20):
    """Print the first n decrypted slots exactly as they come out of decrypt().

    This is the raw evidence: slots the query includes read as values within
    about 1e-9 of 1, and slots it excludes read as values within about 1e-9 of 0.
    """
    print("  first", n, "slots :", out[:n].tolist())
    print("  plain            :", plain[:n].tolist())


def fmt(v):
    """Print a decrypted value with enough digits to see the error."""
    return '  n/a  ' if v != v else f'{v:.10f}'

# Radii chosen around the resolution of the cell-tower table, which places a
# vehicle within roughly 2 km, and inside the range an investigative query would
# actually name.
RADIUS_LIST = [0.5, 1.0, 2.0, 3.0, 5.0, 10.0]          # km
CENTER_LAT = 37.18897
CENTER_LON = 127.11443

#=======================#
##  2. Load Dataset    ##
#=======================#
car_data = pd.read_csv('../../datasets/sorento_drive.csv')
used = min(len(car_data), slot_count)

#=========================#
##  3. Do Preprocessing  ##
#=========================#
raw_lat = np.pad(
    car_data['기지국_위도_x1e5'].to_numpy()[:used],
    (0, slot_count - used),
    constant_values=-1
).astype(float)
raw_lon = np.pad(
    car_data['기지국_경도_x1e5'].to_numpy()[:used],
    (0, slot_count - used),
    constant_values=-1
).astype(float)

# Rows with no coordinate (-1) are pushed to a point far southwest of the Korean
# peninsula, so they never fall inside any queried radius.
lat = np.where(raw_lat == -1, 33.06 * 1e5, raw_lat) / 1e5
lon = np.where(raw_lon == -1, 124.36 * 1e5, raw_lon) / 1e5
observed = (raw_lat != -1) & (raw_lon != -1)

#=====================#
##  4. Encrypt Data  ##
#=====================#
lat_ctxt = ho.encrypt(lat)
lon_ctxt = ho.encrypt(lon)

# Plaintext answer. Used only to check the homomorphic answer, never to produce it.
K_LAT = 110.574
K_LON = 111.320 * np.cos(np.radians(CENTER_LAT))
dist_km = np.sqrt(((lat - CENTER_LAT) * K_LAT) ** 2 + ((lon - CENTER_LON) * K_LON) ** 2)

#=========================================#
##  5. Test the geofence over radii      ##
#=========================================#
print("\nSorento cell-tower log:", used, "of", len(car_data), "rows used,",
      int(observed.sum()), "rows with cell coordinates")
print("Query center", CENTER_LAT, CENTER_LON)
print("\n  stat    radius     plain   cipher     agreement   outside worst   inside worst   inside best      TIME     PLAIN TIME")

rows = []
slots = []
# A fixed sample of slots followed through every radius, spread evenly over the
# range of true distances so that rows on both sides of every radius appear,
# plus two rows that carry no coordinate at all.
obs_idx = np.where(observed)[0]
obs_sorted = obs_idx[np.argsort(dist_km[obs_idx])]
pick = np.unique(np.linspace(0, len(obs_sorted) - 1, 40).astype(int))
keep = np.concatenate([obs_sorted[pick], np.where(~observed)[0][:2]])

for radius in RADIUS_LIST:
    START_TIME = time.time()
    result = hft.compute_geofence_score(lat_ctxt, lon_ctxt, CENTER_LAT, CENTER_LON, radius)
    HE_TIME = time.time() - START_TIME

    START_TIME = time.time()
    plain = (dist_km <= radius).astype(int)
    PLAIN_TIME = time.time() - START_TIME

    out = np.array(ho.decrypt(result))[:slot_count]
    cipher = (out > 0.5).astype(int)
    agree = int((cipher == plain).sum())
    zmax, omin, omax = extremes(out, plain)
    mark = 'OK' if agree == slot_count else 'X '

    print(f"  {mark}    {radius:6.1f} km   {int(plain.sum()):6d}   {int(cipher.sum()):6d}   "
          f"{agree}/{slot_count}     {zmax:.3e}     {fmt(omin)}   {fmt(omax)}   "
          f"{HE_TIME:6.2f}s   {PLAIN_TIME*1000:8.3f}ms")

    rows.append(('sorento', radius, int(plain.sum()), int(cipher.sum()),
                 agree, slot_count, zmax, omin, omax, HE_TIME, PLAIN_TIME))

    # Raw per-slot readings for this radius, kept for the paper.
    dump_slots(out, plain)
    for i in keep:
        slots.append((radius, int(i), float(dist_km[i]), int(plain[i]), float(out[i])))

#=====================#
##  6. Save Results  ##
#=====================#
pd.DataFrame(rows, columns=['dataset', 'radius', 'plain', 'cipher', 'agree', 'total',
                            'zero_max', 'one_min', 'one_max', 'he_sec', 'plain_sec']
             ).to_csv('results/exp1_sorento_summary.csv', index=False)
pd.DataFrame(slots, columns=['radius', 'slot', 'dist_km', 'plain', 'decrypted']
             ).to_csv('results/exp1_sorento_slots.csv', index=False)

print("\n", len(rows), "queries in total,",
      sum(1 for r in rows if r[4] != slot_count), "mismatched")
print("Saved: results/result2.txt, results/exp1_sorento_summary.csv, "
      "results/exp1_sorento_slots.csv")

#=========================#
##  7. Close the log     ##
#=========================#
sys.stdout = sys.__stdout__
sys.stderr = sys.__stderr__
LOG_FILE.close()
