import numpy as np
import pandas as pd
import time, os

import heaan as hn
from engine.engine import HEEngine
from operators.operator import HEOperator
from operators.forensic_operator import HEForensicTest

#==========================#
##  1. Generate HEEngine  ##
#==========================#
engine = HEEngine(device_type="cpu", log_slots=15, warmup_bootstrap=True)
hft = HEForensicTest(engine)
ho  = HEOperator(engine)

SLOTS = 32768
RADIUS_LIST = [0.5, 1.0, 5.0, 10.0, 50.0, 100.0]          # km

# Column names differ between logs, so each dataset declares its own here.
# Adding another log only requires one more entry.
DATASETS = {
    'k5_kitkat':    dict(file='k5_kitkat_drive.csv',
                         lat='위도_x1e5', lon='경도_x1e5',
                         center=(37.31808, 127.12741)),
    'k5_jellybean': dict(file='k5_jellybean_drive.csv',
                         lat='위도_x1e5', lon='경도_x1e5',
                         center=(37.86484, 127.05997)),
}


def run(tag):
    st = DATASETS[tag]
    CLAT, CLON = st['center']

    car = pd.read_csv('../../datasets/' + st['file'])
    used = min(len(car), SLOTS)
    pad = SLOTS - used

    raw_lat = np.pad(car[st['lat']].to_numpy()[:used], (0, pad), constant_values=-1).astype(float)
    raw_lon = np.pad(car[st['lon']].to_numpy()[:used], (0, pad), constant_values=-1).astype(float)

    # Rows with no coordinate (-1) are pushed to a point far southwest of the
    # Korean peninsula, so they never fall inside any queried radius.
    lat = np.where(raw_lat == -1, 33.06 * 1e5, raw_lat) / 1e5
    lon = np.where(raw_lon == -1, 124.36 * 1e5, raw_lon) / 1e5
    observed = (raw_lat != -1) & (raw_lon != -1)

    enc_lat = ho.encrypt(lat)
    enc_lon = ho.encrypt(lon)

    # Plaintext ground truth. Used only for scoring, never for the decision.
    K_LAT = 110.574
    K_LON = 111.320 * np.cos(np.radians(CLAT))
    L = 8.0                                                # normalization width used by compute_geofence_score
    dist_km   = np.sqrt(((lat - CLAT) * K_LAT) ** 2 + ((lon - CLON) * K_LON) ** 2)
    dist_norm = ((lat - CLAT) / L) ** 2 + ((lon - CLON) * K_LON / L / K_LAT) ** 2

    print("\n" + "=" * 78)
    print(f"[{tag}]  file {st['file']}   {used} of {len(car)} rows used   {int(observed.sum())} rows with coordinates")
    print(f"         query center {CLAT}, {CLON}")
    print("=" * 78)
    print("  stat    radius     plain   cipher     agreement    gray   TIME")

    rows, curve = [], []
    keep = np.concatenate([np.where(observed)[0], np.where(~observed)[0][:1]])

    for r in RADIUS_LIST:
        threshold = (r / L / K_LAT) ** 2
        step_in = -(dist_norm - threshold)                 # the value actually fed to he_step

        T = time.time()
        ct = hft.compute_geofence_score(enc_lat, enc_lon, CLAT, CLON, r)
        el = time.time() - T

        out = np.array(ho.decrypt(ct))[:SLOTS]
        he  = (out > 0.5).astype(int)
        pl  = (dist_km <= r).astype(int)
        agree = int((he == pl).sum())
        gray  = int(((out > 0.01) & (out < 0.99)).sum())
        mark  = 'OK' if agree == SLOTS else 'X '

        print(f"  {mark}    {r:6.1f} km   {int(pl.sum()):6d}   {int(he.sum()):6d}   "
              f"{agree}/{SLOTS}   {gray:5d}   {el:.2f}s")

        rows.append((tag, r, int(pl.sum()), int(he.sum()), agree, gray, el))
        for i in keep:
            curve.append((r, int(i), float(step_in[i]), float(out[i]), float(dist_km[i])))

    os.makedirs('results', exist_ok=True)
    pd.DataFrame(rows, columns=['dataset', 'radius', 'plain', 'cipher', 'agree', 'gray', 'sec']
                 ).to_csv('results/exp3_' + tag + '_summary.csv', index=False)
    pd.DataFrame(curve, columns=['radius', 'slot', 'step_input', 'he_output', 'dist_km']
                 ).to_csv('results/exp3_' + tag + '_curve.csv', index=False)
    return rows


if __name__ == '__main__':
    allrows = []
    for tag in DATASETS:
        allrows += run(tag)

    print("\n" + "=" * 78)
    print("SUMMARY   (plain = ground truth, cipher = homomorphic decision)")
    print("=" * 78)
    bad = 0
    for tag, r, pl, he, agree, gray, el in allrows:
        ok = agree == SLOTS
        bad += (not ok)
        print(f"  {tag:<14}{r:>7.1f}km  plain {pl:>6}  cipher {he:>6}   {'match' if ok else 'mismatch'}")
    print(f"\n  {len(allrows)} queries in total, {bad} mismatched")

    try:
        os.chmod('results', 0o777)
        for f in os.listdir('results'):
            os.chmod(os.path.join('results', f), 0o666)
    except Exception:
        pass