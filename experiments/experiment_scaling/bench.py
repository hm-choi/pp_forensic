"""Runtime of each predicate when the input spans several ciphertexts (Experiment 4).

Only runtime is the target. For every predicate and every multiple, the input
is encrypted once, the circuit is evaluated once as a warm-up (and that one
result is checked against plaintext on every row), and then the same circuit
is timed REPS times in this process. The logs are tiled cyclically up to
multiple x 32,768 rows; HE time depends on the number of ciphertexts, not on
the values, so a tiled log costs what a genuinely longer log would.

The paper's figures use MULTIPLES=1,2,4,8,32 on the GPU (32 ciphertexts hold
1,048,576 rows). colab/run_a100.sh runs 1,2,4,8 and 32 as two processes; each
process warms up once and times every point back to back, as on the CPU.

Environment:
  HE_DEVICE  gpu or cpu, default cpu
  PREDS      which predicates, default "geo,edr,phone"
  MULTIPLES  default "1,2,4,8,32" (the earlier CPU run used "1,2,3,4,5")
  REPS       timed repetitions per point, default 30
  REPS_phone (etc.)  per-predicate override of REPS
  PHONE_C    public bound C of the existence circuit, default 65536; it must
             exceed the match count of the tiled log (61,680 at 32x)
"""
import os
import sys
import time
import numpy as np
import pandas as pd

from engine.engine import HEEngine
from operators.operator import HEOperator
from operators.forensic_operator import HEForensicTest
from operators import bscount
from tm import to_tm

PREDS = os.environ.get('PREDS', 'geo,edr,phone').split(',')
MULTIPLES = [int(m) for m in os.environ.get('MULTIPLES', '1,2,4,8,32').split(',')]
REPS = int(os.environ.get('REPS', '30'))
OUT = 'results/bench_times.csv'


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


os.makedirs('results', exist_ok=True)
LOG_FILE = open('results/bench_log.txt', 'a', encoding='utf-8')
sys.stdout = Tee(sys.__stdout__, LOG_FILE)
sys.stderr = Tee(sys.__stderr__, LOG_FILE)

engine = HEEngine(device_type=os.environ.get("HE_DEVICE", "cpu"), log_slots=15, warmup_bootstrap=True)
hft = HEForensicTest(engine)
ho = HEOperator(engine)
NS = engine.num_slots()


def dec(res, used):
    return np.array(ho.decrypt(res))[:used]


def bench(pred, query, m, chunks, used, evaluate, check):
    """Warm up once (and verify), then time `evaluate` reps times."""
    reps = int(os.environ.get(f'REPS_{pred}', REPS))
    bscount.reset()
    t0 = time.time()
    res = evaluate()
    warm = time.time() - t0
    bs, cheb = bscount.snapshot()
    ok = bool(check(res))
    del res

    times = []
    for _ in range(reps):
        t0 = time.time()
        evaluate()
        times.append(time.time() - t0)

    t = np.array(times)
    print(f"{'OK' if ok else 'X '} {pred:5s} {query:<18s} {m}x  {chunks} ct  {used:7d} rows  "
          f"mean {t.mean():7.2f}s  std {t.std(ddof=1) if reps > 1 else 0:5.2f}s  "
          f"(warm-up {warm:6.2f}s)  bs {bs:3d}  cheb {cheb:4d}  reps {reps}", flush=True)

    df = pd.DataFrame({'pred': pred, 'query': query, 'multiple': m, 'chunks': chunks, 'rows': used,
                       'rep': np.arange(1, reps + 1), 'he_sec': t,
                       'bootstraps': bs, 'chebyshev': cheb, 'correct': ok})
    df.to_csv(OUT, mode='a', header=not os.path.exists(OUT), index=False)


# ---------------------------------------------------------------- radius
def run_geo():
    L_M = 8.0 * 110.574 * 1000.0
    center = (37.31808, 127.12741)       # K5 DL3 query centre, as in Experiment 1
    radius = 1.0                         # km; runtime does not depend on the radius
    d = pd.read_csv('../../datasets/k5_kitkat_drive.csv')
    blat = d['Lat_x1e5'].to_numpy().astype(float)
    blon = d['Lon_x1e5'].to_numpy().astype(float)
    cx, cy = (float(v) for v in to_tm(*center))

    for m in MULTIPLES:
        used = m * NS
        rlat, rlon = np.resize(blat, used), np.resize(blon, used)
        lat = np.where(rlat == -1, 33.06e5, rlat) / 1e5
        lon = np.where(rlon == -1, 124.36e5, rlon) / 1e5
        x, y = to_tm(lat, lon)
        xc, yc = ho.encrypt(x / L_M), ho.encrypt(y / L_M)
        ecx = hft.encrypt_param(cx / L_M, size=used)
        ecy = hft.encrypt_param(cy / L_M, size=used)
        er = hft.encrypt_param(radius * 1000.0 / L_M, size=used)
        plain = (np.hypot(x - cx, y - cy) / 1000.0 <= radius).astype(int)

        bench('geo', f'radius {radius} km', m, len(xc.ciphertexts()), used,
              lambda: hft.compute_geofence_score(xc, yc, ecx, ecy, er),
              lambda r: ((dec(r, used) > 0.5).astype(int) == plain).all())


# ---------------------------------------------------------------- EDR
def run_edr():
    d = pd.read_csv('../../datasets/avante_accident.csv')
    bt = d['T_rel_ms'].to_numpy().astype(float)
    bv = d['Speed_kmh'].to_numpy().astype(float)
    TH, S, E, R = 60.0, -3000.0, -1000.0, 5000.0   # as in Experiment 3

    for m in MULTIPLES:
        used = m * NS
        t, v = np.resize(bt, used), np.resize(bv, used)
        tc, vc = ho.encrypt(t), ho.encrypt(v)
        chunks = len(vc.ciphertexts())
        eth = hft.encrypt_param(TH, size=used)
        es = hft.encrypt_param(S, size=used)
        ee = hft.encrypt_param(E, size=used)
        p_th = (v > TH).astype(int)
        p_win = ((t > S) & (t < E)).astype(int)

        bench('edr', 'speed threshold', m, chunks, used,
              lambda: hft.detect_overspeed(vc, eth, max_speed=200.0),
              lambda r: ((dec(r, used) > 0.5).astype(int) == p_th).all())
        bench('edr', 'time window', m, chunks, used,
              lambda: hft.time_range(tc, es, ee, R),
              lambda r: ((dec(r, used) > 0.5).astype(int) == p_win).all())


# ---------------------------------------------------------------- phone
def run_phone():
    DEN = (999, 9999, 9999)
    MARGIN = 0.5
    # Public bound on the match count. Tiling multiplies the matches (9,636 at 5x, 61,680 at 32x),
    # so the bound must exceed the count at the largest multiple; 65536 covers runs up to 32x.
    C = int(os.environ.get('PHONE_C', '65536'))
    d = pd.read_csv('../../datasets/niro_call.csv')
    base = pd.to_numeric(d['Peer_number'], errors='coerce').fillna(-1).astype('int64').to_numpy()
    target = int(pd.Series(base[base != -1]).value_counts().index[0])
    tseg = [target // 10**8, (target // 10**4) % 10**4, target % 10**4]

    for m in MULTIPLES:
        used = m * NS
        raw = np.resize(base, used)
        un = raw == -1
        segs = [np.where(un, 999, raw // 10**8) / DEN[0],
                np.where(un, 0, (raw // 10**4) % 10**4) / DEN[1],
                np.where(un, 0, raw % 10**4) / DEN[2]]
        enc = [ho.encrypt(s) for s in segs]
        lo = [hft.encrypt_param(s / q - MARGIN / q, size=used) for s, q in zip(tseg, DEN)]
        hi = [hft.encrypt_param(s / q + MARGIN / q, size=used) for s, q in zip(tseg, DEN)]
        plain = (raw == target).astype(int)
        assert plain.sum() < C, f"C={C} below match count {plain.sum()}"

        def evaluate():
            match = hft.detect_phone_match(enc, lo, hi)
            return match, hft.detect_phone_exists(match, max_count=C)

        def check(r):
            match, exists = r
            return (((dec(match, used) > 0.5).astype(int) == plain).all()
                    and float(ho.decrypt(exists)[0]) > 0.5)

        bench('phone', 'match + existence', m, len(enc[0].ciphertexts()), used, evaluate, check)


print(f"\n==== bench start {time.strftime('%F %T')}  PREDS={PREDS} MULTIPLES={MULTIPLES} REPS={REPS}")
for p in PREDS:
    {'geo': run_geo, 'edr': run_edr, 'phone': run_phone}[p]()
print(f"==== bench done {time.strftime('%F %T')}")

sys.stdout = sys.__stdout__
sys.stderr = sys.__stderr__
LOG_FILE.close()
