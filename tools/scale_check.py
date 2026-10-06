"""Fit runtime vs. ciphertexts on the small multiples only, then check how well it predicts the big one."""
import sys
import numpy as np, pandas as pd
d = pd.read_csv(sys.argv[1]); big = int(sys.argv[2]) if len(sys.argv) > 2 else 32
g = d.groupby(['pred', 'query', 'chunks'], sort=False).he_sec.agg(['mean', 'std', 'size']).reset_index()
print(g.to_string(index=False, float_format=lambda v: f'{v:.2f}'))
print()
for (p, q), s in g.groupby(['pred', 'query'], sort=False):
    sm, bg = s[s.chunks < big], s[s.chunks == big]
    a, b = np.polyfit(sm.chunks, sm['mean'], 1)
    r2 = np.corrcoef(s.chunks, s['mean'])[0, 1] ** 2
    line = f'{p} / {q}: slope {a:.2f} s/ct (fit on {list(sm.chunks)}), R^2 all points {r2:.4f}'
    if len(bg):
        pred, meas = a * big + b, float(bg['mean'].iloc[0])
        line += f' | {big} ct predicted {pred:.1f} s, measured {meas:.1f} s, error {100*(meas-pred)/pred:+.1f}%'
    print(line)
