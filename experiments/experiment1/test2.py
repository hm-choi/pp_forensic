import numpy as np
import pandas as pd
import time
import os
import sys

import heaan as hn
from engine.engine import HEEngine
from operators.operator import HEOperator
from operators.forensic_operator import HEForensicTest
from tm import to_tm


#=========================#
##  0. Console logging   ##
#=========================#
os.makedirs('results', exist_ok=True)
LOG_FILE = open('results/result2.txt', 'w', encoding='utf-8')


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

slot_count = 32768

L_M = 8.0 * 110.574 * 1000.0                 # public normalization width, metres


def extremes(out, plain):
    """Worst reading among the excluded slots, and worst/best among the included."""
    z = out[plain == 0]
    o = out[plain == 1]
    zmax = float(np.abs(z).max()) if z.size else float('nan')
    omin = float(o.min()) if o.size else float('nan')
    omax = float(o.max()) if o.size else float('nan')
    return zmax, omin, omax


def dump_slots(out, plain, n=20):
    """Print the first n decrypted slots as they come out of decrypt()."""
    print("  first", n, "slots :", out[:n].tolist())
    print("  plain            :", plain[:n].tolist())


def fmt(v):
    return '  n/a  ' if v != v else f'{v:.10f}'

# 50 km and 100 km are dropped: both return every observed row.
RADIUS_LIST = [0.2, 0.5, 1.0, 2.0, 3.0, 5.0]              # km

DATASETS = {
    'k5_kitkat':    dict(file='k5_kitkat_drive.csv',
                         lat='Lat_x1e5', lon='Lon_x1e5',
                         center=(37.31808, 127.12741)),
    'k5_jellybean': dict(file='k5_jellybean_drive.csv',
                         lat='Lat_x1e5', lon='Lon_x1e5',
                         center=(37.86484, 127.05997)),
}


def run(tag):
    st = DATASETS[tag]
    CENTER_LAT, CENTER_LON = st['center']

    #=======================#
    ##  2. Load Dataset    ##
    #=======================#
    car_data = pd.read_csv('../../datasets/' + st['file'])
    used = min(len(car_data), slot_count)

    #=========================#
    ##  3. Do Preprocessing  ##
    #=========================#
    raw_lat = np.pad(
        car_data[st['lat']].to_numpy()[:used],
        (0, slot_count - used),
        constant_values=-1
    ).astype(float)
    raw_lon = np.pad(
        car_data[st['lon']].to_numpy()[:used],
        (0, slot_count - used),
        constant_values=-1
    ).astype(float)

    # Rows with no coordinate (-1) are moved far southwest of the peninsula.
    lat = np.where(raw_lat == -1, 33.06 * 1e5, raw_lat) / 1e5
    lon = np.where(raw_lon == -1, 124.36 * 1e5, raw_lon) / 1e5
    observed = (raw_lat != -1) & (raw_lon != -1)

    # Both sides project to EPSG:5186 metres and divide by the public width
    # L_M, all in the clear, before anything is encrypted.
    x_m, y_m = to_tm(lat, lon)
    cx_m, cy_m = to_tm(CENTER_LAT, CENTER_LON)

    x = x_m / L_M
    y = y_m / L_M
    cx = float(cx_m) / L_M
    cy = float(cy_m) / L_M

    #=====================#
    ##  4. Encrypt Data  ##
    #=====================#
    x_ctxt = ho.encrypt(x)
    y_ctxt = ho.encrypt(y)

    # Query centre, encrypted by the requester.
    enc_center_x = hft.encrypt_param(cx)
    enc_center_y = hft.encrypt_param(cy)

    dist_km = np.sqrt((x_m - cx_m) ** 2 + (y_m - cy_m) ** 2) / 1000.0   # plaintext check

    #=========================================#
    ##  5. Test the geofence over radii      ##
    #=========================================#
    print("\n[" + tag + "]", used, "of", len(car_data), "rows used,",
          int(observed.sum()), "rows with coordinates")
    print("Query center", CENTER_LAT, CENTER_LON, " projected to", round(float(cx_m), 2), round(float(cy_m), 2))
    print("\n  stat    radius     plain   cipher     agreement   outside worst   inside worst   inside best      TIME    ENC TIME     PLAIN TIME")

    rows = []
    slots = []
    # Fixed slot sample followed through every radius, plus two rows with no coordinate.
    obs_idx = np.where(observed)[0]
    obs_sorted = obs_idx[np.argsort(dist_km[obs_idx])]
    pick = np.unique(np.linspace(0, len(obs_sorted) - 1, 40).astype(int))
    keep = np.concatenate([obs_sorted[pick], np.where(~observed)[0][:2]])

    for radius in RADIUS_LIST:
        # Normalized radius, encrypted. Timed apart: requester cost.
        ENC_START = time.time()
        enc_radius = hft.encrypt_param(radius * 1000.0 / L_M)
        ENC_TIME = time.time() - ENC_START

        START_TIME = time.time()
        result = hft.compute_geofence_score(x_ctxt, y_ctxt,
                                            enc_center_x, enc_center_y,
                                            enc_radius)
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
              f"{HE_TIME:6.2f}s   {ENC_TIME*1000:7.3f}ms   {PLAIN_TIME*1000:8.3f}ms")

        rows.append((tag, radius, int(plain.sum()), int(cipher.sum()),
                     agree, slot_count, zmax, omin, omax, HE_TIME, ENC_TIME, PLAIN_TIME))

        dump_slots(out, plain)
        for i in keep:
            slots.append((tag, radius, int(i), float(dist_km[i]), int(plain[i]), float(out[i])))

    #=====================#
    ##  6. Save Results  ##
    #=====================#
    pd.DataFrame(rows, columns=['dataset', 'radius', 'plain', 'cipher', 'agree', 'total',
                                'zero_max', 'one_min', 'one_max',
                                'he_sec', 'param_enc_sec', 'plain_sec']
                 ).to_csv('results/exp1_' + tag + '_summary.csv', index=False)
    pd.DataFrame(slots, columns=['dataset', 'radius', 'slot', 'dist_km', 'plain', 'decrypted']
                 ).to_csv('results/exp1_' + tag + '_slots.csv', index=False)
    return rows


if __name__ == '__main__':
    allrows = []
    for tag in DATASETS:
        allrows += run(tag)

    #==========================#
    ##  7. Summarize results  ##
    #==========================#
    pd.DataFrame(allrows, columns=['dataset', 'radius', 'plain', 'cipher', 'agree', 'total',
                                   'zero_max', 'one_min', 'one_max',
                                   'he_sec', 'param_enc_sec', 'plain_sec']
                 ).to_csv('results/exp1_all_summary.csv', index=False)

    print("\nSUMMARY")
    bad = 0
    for tag, radius, plain, cipher, agree, total, zmax, omin, omax, he_sec, enc_sec, plain_sec in allrows:
        ok = agree == total
        bad += (not ok)
        print(f"  {tag:<14}{radius:>7.1f} km  plain {plain:>6}  cipher {cipher:>6}   "
              f"{'match' if ok else 'mismatch'}   {he_sec:.2f}s / {plain_sec*1000:.3f}ms")
    print("\n", len(allrows), "queries in total,", bad, "mismatched")
    print("Saved: results/result2.txt, results/exp1_<dataset>_summary.csv, "
          "results/exp1_all_summary.csv")

    #=========================#
    ##  8. Close the log     ##
    #=========================#
    sys.stdout = sys.__stdout__
    sys.stderr = sys.__stderr__
    LOG_FILE = open('results/result1.txt', 'w', encoding='utf-8')