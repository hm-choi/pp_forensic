import numpy as np
import pandas as pd
import time
import os
import sys

import heaan as hn
from engine.engine import HEEngine
from operators.operator import HEOperator
from operators.forensic_operator import HEForensicTest
from operators import bscount


#=========================#
##  0. Console logging   ##
#=========================#
os.makedirs('results', exist_ok=True)
LOG_FILE = open('results/result3.txt', 'w', encoding='utf-8')


class Tee:
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


def extremes(out, plain):
    """Worst reading among the false rows, and worst/best among the true rows."""
    z = out[plain == 0]
    o = out[plain == 1]
    zmax = float(np.abs(z).max()) if z.size else float('nan')
    omin = float(o.min()) if o.size else float('nan')
    omax = float(o.max()) if o.size else float('nan')
    return zmax, omin, omax


def report(name, out, plain):
    zmax, omin, omax = extremes(out, plain)
    print(f"  rows where false   worst reading  {zmax:.3e}")
    print(f"  rows where true    worst reading  {omin:.10f}   best {omax:.10f}")
    return zmax, omin, omax

#=======================#
##  2. Load Dataset    ##
#=======================#
car_data = pd.read_csv('../../datasets/avante_accident.csv')
slot_count = 32768
row_count = len(car_data)          # 16 recorded rows, the rest is padding

#=========================#
##  3. Do Preprocessing  ##
#=========================#
t_rel = np.pad(car_data['T_rel_ms'].to_numpy(),
               (0, slot_count - row_count), constant_values=-1).astype(float)
speed = np.pad(car_data['Speed_kmh'].to_numpy(),
               (0, slot_count - row_count), constant_values=0).astype(float)

# Speed is recorded only for the rows before impact, so the speed predicates
# are scored on those rows.
speed_rows = int((car_data['Speed_kmh'].to_numpy() != -1).sum())

#=====================#
##  4. Encrypt Data  ##
#=====================#
t_rel_ctxt = ho.encrypt(t_rel)
speed_ctxt = ho.encrypt(speed)

MAX_SPEED = 200.0                  # public normalization constant
THRESHOLD_SPEED = 60.0

# Window in the log's own unit (ms before impact). Neither bound sits on a
# recorded timestamp, and the padding value -1 falls outside, so all 32,768
# slots can be checked against the plaintext answer.
START = -3000.0
END = -1000.0
RANGE = 5000.0

# Query parameters, encrypted by the requester in the log's own units. Each
# circuit subtracts them from a freshly encrypted data ciphertext and
# normalizes afterwards, so the two operands always sit at the same level.
# detect_speed_increase carries no parameter.
PARAM_ENC_START = time.time()
enc_threshold = hft.encrypt_param(THRESHOLD_SPEED)
enc_start = hft.encrypt_param(START)
enc_end = hft.encrypt_param(END)
PARAM_ENC_TIME = time.time() - PARAM_ENC_START

print("\nAvante EDR log:", row_count, "recorded rows,", speed_rows, "rows with a recorded speed")
print("Query parameters encrypted in", round(PARAM_ENC_TIME * 1000, 3), "ms")

#=====================================================#
##  5. Test the acceleration and deceleration test   ##
#=====================================================#
START_TIME = time.time()
bscount.reset()
result = hft.detect_speed_increase(speed_ctxt)
HE_TIME = time.time() - START_TIME
BS1, CHEB1 = bscount.snapshot()

# np.roll(speed, 1)[i] is speed[i-1], what the one-slot rotation computes.
START_TIME = time.time()
plain1 = (speed - np.roll(speed, 1) > 0).astype(int)
PLAIN_TIME = time.time() - START_TIME

out1 = np.array(ho.decrypt(result))[:row_count]
he1 = (out1 > 0.5).astype(int)
agree1 = int((he1[:speed_rows] == plain1[:speed_rows]).sum())

print("\nSpeed increase (1 means the speed rose from the previous row)")
print("  cipher", he1[:speed_rows].tolist())
print("  plain ", plain1[:speed_rows].tolist())
print("  agree ", agree1, "/", speed_rows)
z1, n1, x1 = report('speed increase', out1[:speed_rows], plain1[:speed_rows])
print("  TIME", round(HE_TIME, 2), "s   PLAIN TIME", round(PLAIN_TIME * 1000, 3), "ms   BS", BS1, " CHEB", CHEB1)

#===========================================#
##  6. Test the Speeding violation check   ##
#===========================================#
START_TIME = time.time()
bscount.reset()
result2 = hft.detect_overspeed(speed_ctxt, enc_threshold)
HE_TIME2 = time.time() - START_TIME
BS2, CHEB2 = bscount.snapshot()

START_TIME = time.time()
plain2 = (speed > THRESHOLD_SPEED).astype(int)
PLAIN_TIME2 = time.time() - START_TIME

out2 = np.array(ho.decrypt(result2))[:row_count]
he2 = (out2 > 0.5).astype(int)
agree2 = int((he2[:speed_rows] == plain2[:speed_rows]).sum())

print(f"\nOverspeed (1 means the speed exceeds {THRESHOLD_SPEED:.0f} km/h)")
print("  cipher", he2[:speed_rows].tolist())
print("  plain ", plain2[:speed_rows].tolist())
print("  agree ", agree2, "/", speed_rows)
z2, n2, x2 = report('overspeed', out2[:speed_rows], plain2[:speed_rows])
print("  TIME", round(HE_TIME2, 2), "s   PLAIN TIME", round(PLAIN_TIME2 * 1000, 3), "ms   BS", BS2, " CHEB", CHEB2)

#=====================================#
##  7. Test the time window check    ##
#=====================================#
START_TIME = time.time()
bscount.reset()
result3 = hft.time_range(t_rel_ctxt, enc_start, enc_end, RANGE)
HE_TIME3 = time.time() - START_TIME
BS3, CHEB3 = bscount.snapshot()

START_TIME = time.time()
plain3 = ((t_rel > START) & (t_rel < END)).astype(int)
PLAIN_TIME3 = time.time() - START_TIME

full3 = np.array(ho.decrypt(result3))[:slot_count]
he3_all = (full3 > 0.5).astype(int)
agree3 = int((he3_all == plain3).sum())
he3 = he3_all[:row_count]
out3 = full3[:row_count]

print("\nTime window:", START, "to", END)
print("  cipher", he3.tolist())
print("  plain ", plain3[:row_count].tolist())
print("  agree ", agree3, "/", slot_count, "  (padding included)")
z3, n3, x3 = report('time window', full3, plain3)
print("  TIME", round(HE_TIME3, 2), "s   PLAIN TIME", round(PLAIN_TIME3 * 1000, 3), "ms   BS", BS3, " CHEB", CHEB3)

#===============================#
##  8. Per-row answers         ##
#===============================#
# A dot marks a row with no recorded speed.
print("\nrow  t_rel  speed |    incr out  p |     over out  p |      win out  p")
print("-" * 74)
for i in range(row_count):
    if i < speed_rows:
        c1, p1 = f"{out1[i]:.10f}", str(plain1[i])
        c2, p2 = f"{out2[i]:.10f}", str(plain2[i])
    else:
        c1 = p1 = c2 = p2 = '.'
    print(f"{i:>3}{int(t_rel[i]):>8}{int(speed[i]):>7} |"
          f"{c1:>14}{p1:>3} |{c2:>14}{p2:>3} |{out3[i]:>14.10f}{plain3[i]:>3}")

#=====================#
##  9. Save Results  ##
#=====================#
pd.DataFrame(
    [('speed increase', speed_rows, int(plain1[:speed_rows].sum()),
      int(he1[:speed_rows].sum()), agree1, speed_rows, z1, n1, x1, HE_TIME, PLAIN_TIME, BS1, CHEB1, PARAM_ENC_TIME),
     ('overspeed', speed_rows, int(plain2[:speed_rows].sum()),
      int(he2[:speed_rows].sum()), agree2, speed_rows, z2, n2, x2, HE_TIME2, PLAIN_TIME2, BS2, CHEB2, PARAM_ENC_TIME),
     ('time window', slot_count, int(plain3.sum()),
      int(he3_all.sum()), agree3, slot_count, z3, n3, x3, HE_TIME3, PLAIN_TIME3, BS3, CHEB3, PARAM_ENC_TIME)],
    columns=['predicate', 'scored', 'plain', 'cipher', 'agree', 'total',
             'zero_max', 'one_min', 'one_max', 'he_sec', 'plain_sec', 'bootstraps', 'chebyshev', 'param_enc_sec']
).to_csv('results/exp3_avante_summary.csv', index=False)

pd.DataFrame({
    'row': np.arange(row_count),
    't_rel': t_rel[:row_count].astype(int),
    'speed': speed[:row_count].astype(int),
    'incr_out': out1, 'incr_cipher': he1, 'incr_plain': plain1[:row_count],
    'over_out': out2, 'over_cipher': he2, 'over_plain': plain2[:row_count],
    'win_out': out3, 'win_cipher': he3, 'win_plain': plain3[:row_count],
}).to_csv('results/exp3_avante_rows.csv', index=False)

bad = (agree1 != speed_rows) + (agree2 != speed_rows) + (agree3 != slot_count)
print("\n 3 predicates in total,", bad, "mismatched")
print("Saved: results/result2.txt, results/exp3_avante_summary.csv, "
      "results/exp3_avante_rows.csv")

#==========================#
##  10. Close the log     ##
#==========================#
sys.stdout = sys.__stdout__
sys.stderr = sys.__stderr__
LOG_FILE.close()