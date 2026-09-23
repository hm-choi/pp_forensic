import numpy as np
import pandas as pd
import time

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

#=======================#
##  2. Load Dataset    ##
#=======================#
car = pd.read_csv('../../datasets/niro_call.csv')

#=========================#
##  3. Do Preprocessing  ##
#=========================#
# Phone numbers are stored as integers, so leading zeros are lost.
# A domestic mobile number (01x) loses one zero and an international prefix (006)
# loses two, so every value is zero-padded back to 11 digits instead of
# branching on length.
WIDTHS = (3, 4, 4)                           # 010 / 2013 / 2924
DENOMS = tuple(10 ** w - 1 for w in WIDTHS)  # 999 / 9999 / 9999
NDIGIT = sum(WIDTHS)
UNOBSERVED_PREFIX = 999                      # a 3-digit prefix no real number uses


def split_phone(value):
    d = str(int(value)).zfill(NDIGIT)
    out, pos = [], 0
    for w in WIDTHS:
        out.append(int(d[pos:pos + w]))
        pos += w
    return out


def bump(num, i):
    """Return num with exactly one digit at position i replaced."""
    d = list(num)
    d[i] = str((int(d[i]) + 1) % 10)
    return ''.join(d)


raw = np.pad(car['상대번호'].to_numpy(), (0, SLOTS - len(car)), constant_values=-1)

# Rows with no number (-1) get the prefix 999 so they never match any target.
# This mirrors how the geofence experiment pushes unrecorded coordinates far away.
segs = np.zeros((len(WIDTHS), SLOTS))
for idx, value in enumerate(raw):
    if value == -1:
        segs[0][idx] = UNOBSERVED_PREFIX / DENOMS[0]
    else:
        for k, part in enumerate(split_phone(value)):
            segs[k][idx] = part / DENOMS[k]

enc_segs = [ho.encrypt(segs[k]) for k in range(len(WIDTHS))]

#=========================================#
##  4. Build the query list               ##
#=========================================#
# Take every number that actually appears in the log, then derive variants that
# differ in exactly one digit.
obs  = pd.Series(raw[raw != -1])
real = [str(int(v)).zfill(NDIGIT) for v in obs.value_counts().index]   # most frequent first

QUERIES = []
for num in real:
    QUERIES.append((num, 'original', 1))
    QUERIES.append((bump(num, 10), 'last digit differs', 0))
for num in real[:1]:                         # the most frequent number also gets first- and middle-group variants
    QUERIES.append((bump(num, 1), 'first group differs', 0))
    QUERIES.append((bump(num, 5), 'middle group differs', 0))
QUERIES.append(('01011112222', 'not in log', 0))

#=========================================#
##  5. Test the phone number match check  ##
#=========================================#
print(f"\nNiro call log: {len(car)} rows   {int((raw != -1).sum())} recorded numbers   {len(real)} distinct")
print(f"Number split {WIDTHS}   normalization denominators {DENOMS}")
print("\nquery number  description             exp  answer  plain  cipher   agreement      TIME")
print('-' * 92)

wrong = 0
for target, why, expect in QUERIES:
    tsegs = split_phone(int(target))

    T = time.time()
    match  = hft.detect_phone_match(enc_segs, tsegs, DENOMS)
    exists = hft.detect_phone_exists(match)
    el = time.time() - T

    answer = int(round(float(ho.decrypt(exists)[0])))       # final answer, 0 or 1
    out    = np.array(ho.decrypt(match))[:SLOTS]
    he_hit = (out > 0.5).astype(int)
    pl_hit = np.array([1 if v != -1 and split_phone(v) == tsegs else 0 for v in raw])
    agree  = int((he_hit == pl_hit).sum())

    ok = (answer == expect) and (agree == SLOTS)
    wrong += (not ok)
    mark = ' ' if ok else ' X'

    print(f"{target:<14}{why:<22}{expect:>4}{answer:>7}{int(pl_hit.sum()):>7}{int(he_hit.sum()):>7}{agree:>10}/{SLOTS}{el:>8.2f}s{mark}")