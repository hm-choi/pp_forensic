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

DEFAULT_MAX_COUNT = 32                       # C used for the main table
MAX_COUNTS = [32, 256, 2048]                 # C values checked in step 7


def extremes(out, plain):
    """Worst reading among the non-matching rows, and worst/best among the matching."""
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

#=======================#
##  2. Load Dataset    ##
#=======================#
car_data = pd.read_csv('../../datasets/niro_call.csv')

#=========================#
##  3. Do Preprocessing  ##
#=========================#
# Numbers are stored as integers, so every value is zero-padded back to 11 digits.
WIDTHS = (3, 4, 4)                           # 010 / 2013 / 2924
DENOMS = tuple(10 ** w - 1 for w in WIDTHS)  # 999 / 9999 / 9999
NDIGIT = sum(WIDTHS)
UNOBSERVED_PREFIX = 999                      # a prefix no real number uses
MARGIN = 0.5                                 # half interval width, in digit units


def split_phone(value):
    """Split an integer phone number into the digit groups given by WIDTHS."""
    d = str(int(value)).zfill(NDIGIT)
    out, pos = [], 0
    for w in WIDTHS:
        out.append(int(d[pos:pos + w]))
        pos += w
    return out


def bump(num, i):
    """Return num with the digit at position i replaced. One digit is worth
    about 1e-3 in the first group and about 1e-4 in the other two."""
    d = list(num)
    d[i] = str((int(d[i]) + 1) % 10)
    return ''.join(d)


def grouped(num):
    """Write a number as its digit groups, e.g. 010-2013-2924."""
    out, pos = [], 0
    for w in WIDTHS:
        out.append(num[pos:pos + w])
        pos += w
    return '-'.join(out)


raw = np.pad(car_data['Peer_number'].to_numpy(),
             (0, slot_count - len(car_data)), constant_values=-1)

# Rows with no number (-1) get the prefix 999 so they never match any target.
segs = np.zeros((len(WIDTHS), slot_count))
for idx, value in enumerate(raw):
    if value == -1:
        segs[0][idx] = UNOBSERVED_PREFIX / DENOMS[0]
    else:
        for k, part in enumerate(split_phone(value)):
            segs[k][idx] = part / DENOMS[k]

#=====================#
##  4. Encrypt Data  ##
#=====================#
enc_segs = [ho.encrypt(segs[k]) for k in range(len(WIDTHS))]

#=========================================#
##  5. Build the query list               ##
#=========================================#
# Every number in the log, plus variants differing in exactly one digit.
# Taking the queries from the log is an experiment convenience: in the protocol
# the requester supplies a number it already holds.
obs = pd.Series(raw[raw != -1])
real = [str(int(v)).zfill(NDIGIT) for v in obs.value_counts().index]   # most frequent first

QUERIES = []
for num in real:
    QUERIES.append((num, 'original', 1))
    QUERIES.append((bump(num, 10), 'one digit, last group', 0))
for num in real[:1]:
    QUERIES.append((bump(num, 1), 'one digit, first group', 0))
    QUERIES.append((bump(num, 5), 'one digit, middle group', 0))
QUERIES.append(('01011112222', 'not in the log', 0))

print(f"\nNiro call log: {len(car_data)} rows   {int((raw != -1).sum())} recorded numbers   "
      f"{len(real)} distinct")
print(f"Number split {WIDTHS}   normalization denominators {DENOMS}")

#=========================================#
##  6. Test the phone number match check  ##
#=========================================#
print(f"\nPer-row match and existence bit at C = {DEFAULT_MAX_COUNT}")
print("query number   description              exp  answer   exist value    plain  cipher"
      "   agreement   nonmatch worst   match worst    MATCH TIME  EXIST TIME  ENC TIME  PLAIN TIME")
print('-' * 150)

rows = []
slot_rows = []
wrong = 0
match_cache = {}

for target, why, expect in QUERIES:
    tsegs = split_phone(int(target))

    # Interval bounds, encrypted by the requester. Timed apart: requester cost.
    ENC_START = time.time()
    enc_lowers = [hft.encrypt_param(t / d - MARGIN / d) for t, d in zip(tsegs, DENOMS)]
    enc_uppers = [hft.encrypt_param(t / d + MARGIN / d) for t, d in zip(tsegs, DENOMS)]
    ENC_TIME = time.time() - ENC_START

    START_TIME = time.time()
    match = hft.detect_phone_match(enc_segs, enc_lowers, enc_uppers)
    MATCH_TIME = time.time() - START_TIME

    START_TIME = time.time()
    exists = hft.detect_phone_exists(match, max_count=DEFAULT_MAX_COUNT)
    EXIST_TIME = time.time() - START_TIME

    # Plaintext answer, on the stored integers.
    START_TIME = time.time()
    plain_hit = (raw == int(target)).astype(int)
    plain_any = int(plain_hit.sum() > 0)
    PLAIN_TIME = time.time() - START_TIME

    exist_value = float(ho.decrypt(exists)[0])       # answer bit before thresholding
    answer = 1 if exist_value > 0.5 else 0
    out = np.array(ho.decrypt(match))[:slot_count]
    cipher_hit = (out > 0.5).astype(int)
    agree = int((cipher_hit == plain_hit).sum())
    zmax, omin, omax = extremes(out, plain_hit)

    ok = (answer == expect) and (answer == plain_any) and (agree == slot_count)
    wrong += (not ok)
    mark = '' if ok else '  X'

    print(f"{grouped(target):<15}{why:<25}{expect:>4}{answer:>8}  {exist_value:>13.10f}"
          f"{int(plain_hit.sum()):>7}{int(cipher_hit.sum()):>7}{agree:>10}/{slot_count}"
          f"     {zmax:.3e}     {fmt(omin)}"
          f"{MATCH_TIME:>10.2f}s{EXIST_TIME:>10.2f}s{ENC_TIME*1000:>8.3f}ms{PLAIN_TIME*1000:>10.3f}ms{mark}")

    rows.append((target, grouped(target), why, expect, answer, exist_value,
                 int(plain_hit.sum()), int(cipher_hit.sum()),
                 agree, slot_count, zmax, omin, omax,
                 MATCH_TIME, EXIST_TIME, ENC_TIME, PLAIN_TIME))
    match_cache[target] = match

    if plain_hit.sum() or target == real[0]:
        dump_slots(out[:len(car_data)], plain_hit[:len(car_data)])
    slot_rows.append((target, grouped(target), why, exist_value,
                      [float(v) for v in out[:len(car_data)]]))

print("\n", len(QUERIES), "queries in total,", wrong, "wrong")

#=========================================#
##  7. Test the summation bound C         ##
#=========================================#
# C is a public bound the requester declares in advance, not part of the
# encrypted query. The match ciphertext is reused, so only the existence
# circuit is re-run.
PROBES = [(real[0], 1), ('01011112222', 0)]

print("\nExistence bit as the declared bound C grows")
print("query number        C   exp  answer    exist value   verdict      EXIST TIME")
print('-' * 104)

sweep = []
for target, expect in PROBES:
    for C in MAX_COUNTS:
        START_TIME = time.time()
        exists = hft.detect_phone_exists(match_cache[target], max_count=C)
        EXIST_TIME = time.time() - START_TIME

        exist_value = float(ho.decrypt(exists)[0])
        answer = 1 if exist_value > 0.5 else 0
        ok = (answer == expect)

        print(f"{grouped(target):<15}{C:>8}{expect:>6}{answer:>8}  {exist_value:>13.10f}"
              f"{'   correct' if ok else '   WRONG  ':>12}{EXIST_TIME:>14.2f}s")
        sweep.append((target, C, expect, answer, exist_value, int(ok), EXIST_TIME))

#=====================#
##  8. Save Results  ##
#=====================#
pd.DataFrame(rows, columns=['target', 'grouped', 'description', 'expected', 'answer', 'exist_value',
                            'plain_hits', 'cipher_hits', 'agree', 'total',
                            'zero_max', 'one_min', 'one_max',
                            'match_sec', 'exist_sec', 'param_enc_sec', 'plain_sec']
             ).to_csv('results/exp2_niro_match_summary.csv', index=False)
pd.DataFrame(sweep, columns=['target', 'max_count', 'expected', 'answer', 'exist_value',
                             'correct', 'exist_sec']
             ).to_csv('results/exp2_niro_maxcount_sweep.csv', index=False)
pd.DataFrame([(t, g, w, e, i, v)
              for t, g, w, e, vs in slot_rows
              for i, v in enumerate(vs)],
             columns=['target', 'grouped', 'description', 'exist_value', 'slot', 'decrypted']
             ).to_csv('results/exp2_niro_slots.csv', index=False)

print("\nSUMMARY")
print("  match check ", len(QUERIES), "queries,", wrong, "wrong")
print("  bound check ", len(sweep), "existence calls over C in", MAX_COUNTS, ",",
      sum(1 for s in sweep if not s[5]), "wrong")
print("Saved: results/result2.txt, results/exp2_niro_match_summary.csv, "
      "results/exp2_niro_maxcount_sweep.csv")

#=========================#
##  9. Close the log     ##
#=========================#
sys.stdout = sys.__stdout__
sys.stderr = sys.__stderr__
LOG_FILE = open('results/result2.txt', 'w', encoding='utf-8')