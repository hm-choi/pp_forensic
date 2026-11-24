"""Re-randomization (noise flooding) check for the camera-ready version, Section 4.5.

The custodian adds, under EncKey, a vector that repeats one value eta ~ U[-delta, delta]
in every slot to the result ciphertext before returning it. This script takes every
decrypted Output recorded in the 30 A100 runs (results/runs), re-encrypts the values,
applies the flooding step homomorphically, decrypts, and checks that every decision
(value > 0.5) is unchanged. It also times the extra step (one encryption + one addition).

No GPU is needed: run it with the CPU distribution of HEaaN.Stat, for example
  udocker run --volume=$PWD:/w --entrypoint=bash heaan-cpu -c \
      "cd /w && PYTHONPATH=/w python3 tools/rerandomize_check.py"
`--dry` runs the same check in plain NumPy (no HE) for a quick sanity test.
"""
import argparse, glob, os, time
import numpy as np, pandas as pd

ap = argparse.ArgumentParser()
ap.add_argument('--runs', default='results/runs')
ap.add_argument('--delta', type=float, default=0.2)
ap.add_argument('--trials', type=int, default=20, help='independent noise draws per value block')
ap.add_argument('--dry', action='store_true')
a = ap.parse_args()

# ---- 1. collect recorded outputs and their plaintext decisions
vals, truth, src = [], [], []
def take(v, t, name):
    vals.extend(np.asarray(v, float)); truth.extend(np.asarray(t, int)); src.extend([name] * len(v))

for f in sorted(glob.glob(f'{a.runs}/run_*/exp1_*_slots.csv')):
    d = pd.read_csv(f); take(d.decrypted, d.plain, 'exp1 per-slot')
for f in sorted(glob.glob(f'{a.runs}/run_*/exp2_niro_match_summary.csv')):
    d = pd.read_csv(f); take(d.exist_value, d.expected, 'exp2 existence')
# worst per-slot values of every query (the slot files above hold only selected slots)
for f in sorted(glob.glob(f'{a.runs}/run_*/exp1_all_summary.csv')):
    d = pd.read_csv(f); d1 = d[d.plain > 0]
    take(d1.one_min, [1] * len(d1), 'exp1 worst inside'); take(d.zero_max, [0] * len(d), 'exp1 worst outside')
for f in sorted(glob.glob(f'{a.runs}/run_*/exp2_niro_match_summary.csv')):
    d = pd.read_csv(f); d1 = d[d.plain_hits > 0]
    take(d1.one_min, [1] * len(d1), 'exp2 worst match'); take(d.zero_max, [0] * len(d), 'exp2 worst non-match')
for f in sorted(glob.glob(f'{a.runs}/run_*/exp3_avante_rows.csv')):
    d = pd.read_csv(f); d = d[d.speed >= 0]                    # the 11 scored EDR samples
    take(d.over_out, d.over_plain, 'exp3 threshold'); take(d.win_out, d.win_plain, 'exp3 window')
    d = d[d.row > 0]; take(d.incr_out, d.incr_plain, 'exp3 increase')   # slot 0 is not scored
vals, truth, src = np.array(vals), np.array(truth), np.array(src)
assert ((vals > 0.5) == truth).all(), 'recorded outputs do not match their plaintext decisions'
ones, zeros = vals[truth == 1], vals[truth == 0]
print(f'{len(vals)} recorded outputs | lowest read as 1: {ones.min():.10f} | highest read as 0: {zeros.max():.3e}')
print(f'worst-case margin to 0.5: {min(ones.min() - 0.5, 0.5 - zeros.max()):.4f}  (delta = {a.delta})')

# ---- 2. flooding, homomorphically (or in NumPy with --dry)
rng = np.random.default_rng()
if a.dry:
    def flood(block):
        return [block + rng.uniform(-a.delta, a.delta) for _ in range(a.trials)], 0.0
else:
    import heaan as hn
    try:
        ctx = hn.make_context(hn.ParameterPreset.FGb)
    except TypeError:
        ctx = hn.make_context(hn.ParameterPreset.FGb, set())
    sk = hn.SecretKey(ctx); kg = hn.KeyGenerator(ctx, sk); kg.gen_common_keys(); pk = kg.keypack
    enc, dec, ev = hn.Encryptor(ctx), hn.Decryptor(ctx), hn.HomEvaluator(ctx, pk)
    N = 2 ** 15
    def flood(block):
        arr = np.zeros(N); arr[:len(block)] = block
        m = hn.Message(arr)                                    # same construction as colab/setup_udocker.sh
        c = hn.Ciphertext(ctx); enc.encrypt(m, pk, c)          # stands in for the result ciphertext
        outs, ts = [], []
        for _ in range(a.trials):
            t0 = time.perf_counter()
            eta = rng.uniform(-a.delta, a.delta)
            mn = hn.Message(np.full(N, eta))                   # same value in every slot
            cn = hn.Ciphertext(ctx); enc.encrypt(mn, pk, cn)
            cr = hn.Ciphertext(ctx); ev.add(c, cn, cr)         # the flooding step
            ts.append(time.perf_counter() - t0)
            r = hn.Message(15); dec.decrypt(cr, sk, r)
            outs.append(np.array(r, dtype=np.complex128)[:len(block)].real)
        return outs, float(np.mean(ts))

flips, steps = 0, []
for s in range(0, len(vals), 2 ** 15):
    block, tb = vals[s:s + 2 ** 15], truth[s:s + 2 ** 15]
    outs, t = flood(block); steps.append(t)
    for o in outs:
        flips += int(((o > 0.5) != tb).sum())
print(f'decision flips after flooding: {flips} over {len(vals)} values x {a.trials} draws')
if not a.dry:
    print(f'flooding step (encrypt noise + add) on CPU: {np.mean(steps):.3f} s per ciphertext')
print('OK' if flips == 0 else 'FLIPS FOUND')
