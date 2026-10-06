"""Collect every number Section 6 of the paper needs (Experiments 1 to 3) from the GPU runs.

usage: python3 tools/extract_gpu.py <dir holding run_01 ... run_30>
"""
import glob, sys
import numpy as np, pandas as pd
R = sys.argv[1] if len(sys.argv) > 1 else 'results/runs'
pd.set_option('display.width', 250); pd.set_option('display.max_columns', 40)
F = lambda v: f'{v:.10g}'

def cat(name):
    fs = sorted(glob.glob(f'{R}/run_*/{name}'))
    return pd.concat([pd.read_csv(f).assign(run=f.split('/')[-2]) for f in fs], ignore_index=True), len(fs)

def signed_worst(s):
    return s.iloc[np.argmax(np.abs(s.to_numpy()))]

d1, n = cat('exp1_all_summary.csv')
print(f'===== EXP1 ({n} runs)')
g1 = d1.groupby(['dataset', 'radius'], sort=False).agg(
    inside=('plain', 'first'), one_min=('one_min', 'min'), zero_max=('zero_max', 'max'),
    btsp=('bootstraps', 'first'), time=('he_sec', 'mean'), enc=('param_enc_sec', 'mean'),
    all_agree=('agree', lambda s: bool((s == d1.loc[s.index, 'total']).all())))
print(g1.to_string(float_format=F))
print('min one_min for radius >= 0.5 :', F(d1[d1.radius >= 0.5].one_min.min()))
print('max enc/time ratio            :', F((g1.enc / g1.time).max()))

d2, n = cat('exp2_niro_match_summary.csv')
print(f'\n===== EXP2 ({n} runs)')
d2['t'] = d2['match_sec'] + d2['exist_sec']
bs = [c for c in ('match_bs', 'exist_bs') if c in d2]
d2['btsp'] = d2[bs].sum(axis=1) if bs else np.nan
rows = []
for (tgt, desc), s in d2.groupby(['target', 'description'], sort=False):
    exp = int(s.expected.iloc[0])
    ev = s.exist_value.min() if exp == 1 else signed_worst(s.exist_value)
    rows.append((s.grouped.iloc[0], desc, exp, int(s.plain_hits.iloc[0]), F(ev),
                 bool((s.answer == exp).all()), int(s.btsp.iloc[0]), round(s.t.mean(), 2),
                 round(s.param_enc_sec.mean(), 3), F(s.one_min.min()), F(s.zero_max.max())))
print(pd.DataFrame(rows, columns=['number', 'description', 'expected', 'matches', 'existence_worst',
                                  'all_correct', 'btsp', 'time', 'enc', 'one_min', 'zero_max']).to_string(index=False))
m = d2[d2.expected == 1]
print('per-slot worst, matching rows   :', F(m.one_min.min()))
print('per-slot worst, non-matching    :', F(d2.zero_max.max()))
print('max enc/time ratio              :', F((d2.groupby('target').param_enc_sec.mean() / d2.groupby('target').t.mean()).max()))
sw, n = cat('exp2_niro_maxcount_sweep.csv')
print('C sweep (all runs correct?)')
print(sw.groupby(['target', 'max_count']).correct.all().to_string())

d3, n = cat('exp3_avante_summary.csv')
print(f'\n===== EXP3 ({n} runs)')
g3 = d3.groupby('predicate', sort=False).agg(btsp=('bootstraps', 'first'), time=('he_sec', 'mean'),
                                            enc=('param_enc_sec', 'mean'),
                                            all_agree=('agree', lambda s: bool((s == d3.loc[s.index, 'total']).all())))
print(g3.to_string(float_format=F))
print('max enc/time ratio:', F((g3.enc / g3.time).max()))
r3, n = cat('exp3_avante_rows.csv')
out = []
for i, s in r3.groupby('row'):
    line = [i, int(s.t_rel.iloc[0]), int(s.speed.iloc[0])]
    for p in ('incr', 'over', 'win'):
        v, pl = s[p + '_out'], s[p + '_plain'].iloc[0]
        line.append('.' if pd.isna(v).all() else F(v.min() if pl == 1 else signed_worst(v)))
    out.append(line)
print(pd.DataFrame(out, columns=['slot', 't_rel', 'speed', 'incr', 'over', 'win']).to_string(index=False))

ps = pd.concat([d1.plain_sec, d2.plain_sec, d3.plain_sec])
print(f'\nplaintext median per query: {ps.median()*1000:.3f} ms')
