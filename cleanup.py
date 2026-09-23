# -*- coding: utf-8 -*-
"""One-off cleanup: Korean to English, dead code removal, type hints, headers."""
import pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parent
log = []

def read(p):  return (ROOT/p).read_text(encoding='utf-8')
def write(p, t): (ROOT/p).write_text(t, encoding='utf-8')

# ---------- 1. line-for-line Korean -> English ----------
ENG = {10:'        device_type="cpu",       # "cpu" or "gpu"',
15:'        warmup_bootstrap=False,  # False is recommended on CPU',
115:'            # The second argument may be optional depending on the HEaaN release',
126:'            # CPU objects stay on the default device',
159:'            print("Key loaded")',
162:'            print("Key load failed:", repr(exc))',
163:'            print("Generating new keys.")',
185:'            print("Key generation done")',
188:'        # Move objects to GPU only in GPU mode',
217:'        # Move the Message only in GPU mode',
226:'            f"Warm-up encrypt start "',
236:'        print("Warm-up encrypt done")',
237:'        print("Warm-up bootstrap start")',
244:'        print("Warm-up bootstrap done")'}

OPR = {13:'        # 1. Convert list input to a numpy array',
20:'        # Total number of ciphertexts needed, rounded up',
25:'        # 2. Chunk and pad',
30:'            # Zero-filled buffer of num_slots (padding)',
33:'            # Copy the real data into the front of the buffer',
36:'            # Build a Message and move it to the device (GPU/CPU)',
40:'            # Encrypt',
46:'        # 3. Return as an HEData object',
47:'        # level comes from the first ciphertext; scale follows the HEaaN setting.',
49:'        scale = 0 # placeholder (adjust to the HEaaN parameters)',
56:'        # 1. Take the ciphertexts held in HEData in order',
59:'            # Empty Message to receive the result',
62:'            # Decrypt with the engine decryptor and the secret key',
65:'            # Move the data from the device back to the host',
68:'            # 2. Convert to a numpy array, real or complex',
74:'            # The return type is a list, so convert and concatenate',
77:'        # 3. Drop the zero padding added at encryption time',
78:'        # Return only up to the original length using hedata.size()',
83:'        Add two HEData chunk-wise.',
87:'        A chunk present on only one side is copied into a new ciphertext.',
130:'                # Do not reference the original ciphertext object;',
131:'                # copy it into a new one.',
151:'        Add the constant con to every ciphertext slot of HEData.',
250:'                # NOTE: follows the Go logic (plain copy), but as this is a subtraction, evt.sub(0, ctxts2[i], res_ct) may be the mathematically correct form',
274:'        # Multiplication follows the Go logic: min covers only the intersection',
276:'        level = min(ct1.level(), ct2.level()) - 1 # one level is usually consumed',
289:'            # Recent HEaaN Python APIs handle relinearization and rescaling inside mult',
297:'        level = ct.level() - 1 # constant multiplication also usually consumes a level',
322:'            # HEaaN uses left_rotate (or right_rotate)',
349:'    #     Copy every ciphertext chunk of HEData and',
350:'    #     return a new HEData.',
352:'    #     HEaaN evaluator.add() writes into the output ciphertext and',
353:'    #     returns None, so store out rather than the return value.',
386:'        #     # Important:',
387:'        #     # evaluator.add() returns None and',
388:'        #     # the result is written into out.',
404:'    def sum(self, data, output_one:bool=False): # lowercase name to follow the Python naming convention',
411:'        # 1. Copy the first ciphertext (avoid in-place corruption of the original)',
412:'        # Depending on the HEaaN version this may need hn.Ciphertext(obj) or copy.deepcopy',
415:'        # 2. If several ciphertexts exist, fold them into one',
420:'        # 3. Accumulate every slot inside one ciphertext (tree based sum)',
422:'            # Temporary ciphertext to hold the rotated result',
425:'            # Rotate left by 2^i (1, 2, 4, 8, 16, ...)',
428:'            # Add the rotated ciphertext back into sum_ctxt',
431:'        # 4. Set the result to match the Go logic',
433:'        # The same sum_ctxt is copied and returned, so keep the fields consistent',
448:'        # Addition and rotation do not consume a level, so keep the original level'}

for path, table in (('engine/engine.py', ENG), ('operators/operator.py', OPR)):
    L = read(path).split('\n')
    for n, new in table.items(): L[n-1] = new
    write(path, '\n'.join(L)); log.append(f"{path}: {len(table)} Korean lines -> English")

# ---------- 2. exp3 Korean prints ----------
P3 = {'print("\\n속도 증가 여부 (1인 경우 속도가 증가한 것을 의미)")':
      'print("\\nSpeed increase (1 means the speed rose from the previous row)")',
      'print("\\n속도 위반 여부 (1인 경우 속도가 60보다 크다는 것을 의미)")':
      'print(f"\\nOverspeed (1 means the speed exceeds {THRESHOLD_SPEED:.0f} km/h)")',
      'print("\\n시간 범위:", START, ",", END)':
      'print("\\nTime window:", START, "to", END)'}
t = read('experiments/experiment3/test2.py'); c = 0
for a, b in P3.items():
    if a in t: t = t.replace(a, b); c += 1
write('experiments/experiment3/test2.py', t); log.append(f"experiment3/test2.py: {c} Korean prints -> English")

# ---------- 3. dead code ----------
def cut(path, ranges):
    L = read(path).split('\n')
    for a, b in sorted(ranges, reverse=True): del L[a-1:b]
    write(path, '\n'.join(L))
cut('operators/operator.py', [(344,403), (219,228)])
log.append("operators/operator.py: removed commented-out copy_new block and unused add_many")
cut('operators/inv_sqrt.py', [(193,229), (32,160), (9,15)])
write('operators/inv_sqrt.py', read('operators/inv_sqrt.py').replace('import math, json','import math'))
log.append("operators/inv_sqrt.py: removed duplicate SIGN_DATA_PPSTAT and 6 unreachable methods")

# ---------- 4. type hints ----------
TH = {'    def sub(self, ct1, ct2):':'    def sub(self, ct1: HEData, ct2: HEData) -> HEData:',
      '    def sub_const(self, ct, con: float):':'    def sub_const(self, ct: HEData, con: float) -> HEData:',
      '    def mult(self, ct1, ct2):':'    def mult(self, ct1: HEData, ct2: HEData) -> HEData:',
      '    def mult_const(self, ct, con: float):':'    def mult_const(self, ct: HEData, con: float) -> HEData:',
      '    def rotation(self, ct, rot_steps: int):':'    def rotation(self, ct: HEData, rot_steps: int) -> HEData:',
      '    def decrypt(self, hedata, isreal: bool = True) -> list:':'    def decrypt(self, hedata: HEData, isreal: bool = True) -> list:',
      '    def sum(self, data, output_one:bool=False):':'    def sum(self, data: HEData, output_one: bool = False) -> HEData:',
      '    def do_bootstrapping(self, data:HEData, level:int):':'    def do_bootstrapping(self, data: HEData, level: int) -> HEData:'}
t = read('operators/operator.py'); c = 0
for a, b in TH.items():
    if a in t: t = t.replace(a, b, 1); c += 1
write('operators/operator.py', t); log.append(f"operators/operator.py: {c} signatures annotated")

# ---------- 5. provenance headers ----------
HDR = ('"""{what}\n\n'
 'Adapted from the PP-STAT implementation by Hyunmin Choi, which was itself\n'
 'ported from an earlier Go implementation.\n'
 'Reference: H. Choi, "PP-STAT: An Efficient Privacy-Preserving Statistical\n'
 'Analysis Framework Using Homomorphic Encryption," CIKM \'25.\n"""\n')
WHAT = {'engine/engine.py':'HEaaN engine setup: context, keys and bootstrapping.',
        'operators/operator.py':'Homomorphic operator wrappers over the HEaaN evaluator.',
        'operators/inv_sqrt.py':'Composite sign and step function on CKKS ciphertexts.',
        'hedata/data.py':'Container holding one or more CKKS ciphertexts.'}
for path, what in WHAT.items():
    t = read(path)
    if t.lstrip().startswith('"""'): log.append(f"{path}: header already present, skipped"); continue
    write(path, HDR.format(what=what) + t); log.append(f"{path}: provenance header added")

print("\n".join("- " + x for x in log))