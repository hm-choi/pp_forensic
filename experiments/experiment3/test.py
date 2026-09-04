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

# 좌표가 있는 CSV 는 컬럼명이 서로 다르다. 여기만 채우면 다른 파일도 그대로 돌아간다.
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

    # 좌표가 없는 행(-1)은 한반도 남서쪽 먼 지점으로 밀어내 어떤 반경에도 안 걸리게 한다.
    lat = np.where(raw_lat == -1, 33.06 * 1e5, raw_lat) / 1e5
    lon = np.where(raw_lon == -1, 124.36 * 1e5, raw_lon) / 1e5
    observed = (raw_lat != -1) & (raw_lon != -1)

    enc_lat = ho.encrypt(lat)
    enc_lon = ho.encrypt(lon)

    # 평문 정답지. 판정에는 쓰이지 않고 채점에만 쓴다.
    K_LAT = 110.574
    K_LON = 111.320 * np.cos(np.radians(CLAT))
    L = 8.0                                                # compute_geofence_score 의 정규화 폭
    dist_km   = np.sqrt(((lat - CLAT) * K_LAT) ** 2 + ((lon - CLON) * K_LON) ** 2)
    dist_norm = ((lat - CLAT) / L) ** 2 + ((lon - CLON) * K_LON / L / K_LAT) ** 2

    print("\n" + "=" * 78)
    print(f"[{tag}]  파일 {st['file']}   전체 {len(car)}행 중 {used}행 사용   좌표 관측 {int(observed.sum())}건")
    print(f"         질의 중심 {CLAT}, {CLON}")
    print("=" * 78)
    print("  판정      반경        평문   암호문   전수대조        애매   TIME")

    rows, curve = [], []
    keep = np.concatenate([np.where(observed)[0], np.where(~observed)[0][:1]])

    for r in RADIUS_LIST:
        threshold = (r / L / K_LAT) ** 2
        step_in = -(dist_norm - threshold)                 # he_step 에 실제로 들어가는 값

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
    print("전체 요약   (평문 = 정답지, 암호문 = 동형암호 판정 결과)")
    print("=" * 78)
    bad = 0
    for tag, r, pl, he, agree, gray, el in allrows:
        ok = agree == SLOTS
        bad += (not ok)
        print(f"  {tag:<14}{r:>7.1f}km  평문 {pl:>6}  암호문 {he:>6}   {'일치' if ok else '불일치'}")
    print(f"\n  총 {len(allrows)}건 중 불일치 {bad}건")

    try:
        os.chmod('results', 0o777)
        for f in os.listdir('results'):
            os.chmod(os.path.join('results', f), 0o666)
    except Exception:
        pass