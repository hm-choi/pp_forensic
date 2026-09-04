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
# 전화번호는 정수로 저장되어 선행 0 이 소실되어 있다.
# 국내 이동전화(01x)는 0 이 하나, 국제전화 식별번호(006)는 0 이 두 개 빠지므로
# 자릿수 분기 없이 11자리로 zero-pad 하여 통일한다.
WIDTHS = (3, 4, 4)                           # 010 / 2013 / 2924
DENOMS = tuple(10 ** w - 1 for w in WIDTHS)  # 999 / 9999 / 9999
NDIGIT = sum(WIDTHS)
UNOBSERVED_PREFIX = 999                      # 실제 번호에 없는 앞 3자리


def split_phone(value):
    d = str(int(value)).zfill(NDIGIT)
    out, pos = [], 0
    for w in WIDTHS:
        out.append(int(d[pos:pos + w]))
        pos += w
    return out


def bump(num, i):
    """num 의 i 번째 자리 하나만 다른 숫자로 바꾼다."""
    d = list(num)
    d[i] = str((int(d[i]) + 1) % 10)
    return ''.join(d)


raw = np.pad(car['상대번호'].to_numpy(), (0, SLOTS - len(car)), constant_values=-1)

# 미관측(-1)은 앞 3자리를 999 로 밀어내 어떤 타겟과도 일치하지 않게 한다.
# geofence 에서 미관측 좌표를 먼 지점으로 밀어낸 것과 같은 방식이다.
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
# 로그에 실제로 있는 번호를 뽑고, 각 번호마다 한 자리만 바꾼 변형을 함께 만든다.
obs  = pd.Series(raw[raw != -1])
real = [str(int(v)).zfill(NDIGIT) for v in obs.value_counts().index]   # 등장 횟수 많은 순

QUERIES = []
for num in real:
    QUERIES.append((num, '원본', 1))
    QUERIES.append((bump(num, 10), '끝자리 하나 다름', 0))
for num in real[:1]:                         # 대표 번호 하나는 앞자리와 중간자리도 본다
    QUERIES.append((bump(num, 1), '앞자리 하나 다름', 0))
    QUERIES.append((bump(num, 5), '중간자리 하나 다름', 0))
QUERIES.append(('01011112222', '로그에 없는 번호', 0))

#=========================================#
##  5. Test the phone number match check  ##
#=========================================#
print(f"\n니로 통화 로그 {len(car)}행   상대번호 관측 {int((raw != -1).sum())}건   고유 번호 {len(real)}개")
print(f"번호 분할 {WIDTHS}   정규화 분모 {DENOMS}")
print("\n조회 번호      설명                 기대  최종답   평문  암호문      전수대조     TIME")
print('-' * 90)

wrong = 0
for target, why, expect in QUERIES:
    tsegs = split_phone(int(target))

    T = time.time()
    match  = hft.detect_phone_match(enc_segs, tsegs, DENOMS)
    exists = hft.detect_phone_exists(match)
    el = time.time() - T

    answer = int(round(float(ho.decrypt(exists)[0])))       # 최종 답 0 또는 1
    out    = np.array(ho.decrypt(match))[:SLOTS]
    he_hit = (out > 0.5).astype(int)
    pl_hit = np.array([1 if v != -1 and split_phone(v) == tsegs else 0 for v in raw])
    agree  = int((he_hit == pl_hit).sum())

    ok = (answer == expect) and (agree == SLOTS)
    wrong += (not ok)
    mark = ' ' if ok else ' X'

    print(f"{target:<14}{why:<20}{expect:>4}{answer:>7}{int(pl_hit.sum()):>7}"
          f"{int(he_hit.sum()):>7}{agree:>10}/{SLOTS}{el:>8.2f}s{mark}")

print('-' * 90)
print(f"총 {len(QUERIES)}건 질의   기대와 다른 결과 {wrong}건")
print("\n최종답 1 = 이 번호와 통화한 기록이 있다,  0 = 없다")
print("한 자리만 달라도 0 이 나오는지 위 표의 '다름' 행에서 확인할 수 있다")