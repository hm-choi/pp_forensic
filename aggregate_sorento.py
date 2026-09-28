import pathlib, pandas as pd

BASE = pathlib.Path(__file__).resolve().parent
ROOT = BASE / 'runs_sorento'
OUT = BASE / 'aggregated_sorento'
OUT.mkdir(exist_ok=True)

NAME = 'exp_sorento_all_summary.csv'
KEYS = ['multiple', 'chunks', 'used_slots', 'radius']

WORST_MAX = {'zero_max', 'one_max'}
WORST_MIN = {'one_min'}

files = sorted(ROOT.glob('run_*/' + NAME))
if not files:
    print('missing', NAME)
else:
    df = pd.concat([pd.read_csv(f).assign(run=f.parent.name) for f in files],
                   ignore_index=True)
    agg = {}
    for c in df.columns:
        if c in KEYS or c == 'run':
            continue
        if c.endswith('_sec'):
            agg[c] = 'mean'
        elif c in WORST_MAX:
            agg[c] = 'max'
        elif c in WORST_MIN:
            agg[c] = 'min'
        else:
            agg[c] = 'first'
    g = df.groupby(KEYS, sort=False).agg(agg).reset_index()
    for c in df.columns:
        if c.endswith('_sec'):
            g[c + '_std'] = df.groupby(KEYS, sort=False)[c].std().values
    g['runs'] = len(files)
    g.to_csv(OUT / NAME, index=False)

    varying = []
    for c in df.columns:
        if c in KEYS or c == 'run' or c.endswith('_sec') or c in WORST_MAX | WORST_MIN:
            continue
        if df.groupby(KEYS, sort=False)[c].nunique().max() > 1:
            varying.append(c)
    print(NAME, '->', len(files), 'runs')
    if varying:
        print('   WARNING: these varied across runs:', varying)
    else:
        print('   all decision columns identical across runs')

    print('\nwritten to', OUT / NAME)
