import pathlib, pandas as pd, numpy as np

ROOT = pathlib.Path('/home/ubuntu/pp_forensic/runs')
OUT = pathlib.Path('/home/ubuntu/pp_forensic/aggregated')
OUT.mkdir(exist_ok=True)

SPECS = [
    ('exp1_all_summary.csv', ['dataset', 'radius']),
    ('exp2_niro_match_summary.csv', ['target', 'description']),
    ('exp3_avante_summary.csv', ['predicate']),
]

WORST_MAX = {'zero_max', 'one_max'}
WORST_MIN = {'one_min'}

for name, keys in SPECS:
    files = sorted(ROOT.glob('run_*/' + name))
    if not files:
        print('missing', name); continue
    df = pd.concat([pd.read_csv(f).assign(run=f.parent.name) for f in files],
                   ignore_index=True)
    agg = {}
    for c in df.columns:
        if c in keys or c == 'run':
            continue
        if c.endswith('_sec'):
            agg[c] = 'mean'
        elif c in WORST_MAX:
            agg[c] = 'max'
        elif c in WORST_MIN:
            agg[c] = 'min'
        else:
            agg[c] = 'first'
    g = df.groupby(keys, sort=False).agg(agg).reset_index()
    for c in df.columns:
        if c.endswith('_sec'):
            g[c + '_std'] = df.groupby(keys, sort=False)[c].std().values
    g['runs'] = len(files)
    g.to_csv(OUT / name, index=False)

    varying = []
    for c in df.columns:
        if c in keys or c == 'run' or c.endswith('_sec') or c in WORST_MAX | WORST_MIN:
            continue
        if df.groupby(keys, sort=False)[c].nunique().max() > 1:
            varying.append(c)
    print(name, '->', len(files), 'runs')
    if varying:
        print('   WARNING: these varied across runs:', varying)
    else:
        print('   all decision columns identical across runs')

print('\nwritten to', OUT)