"""Summarize results/bench_times.csv: mean and std per predicate and multiple, plus the linear fit."""
import numpy as np
import pandas as pd

d = pd.read_csv('results/bench_times.csv')
g = (d.groupby(['pred', 'query', 'multiple', 'chunks', 'rows'], sort=False)
       .agg(mean_sec=('he_sec', 'mean'), std_sec=('he_sec', 'std'), reps=('he_sec', 'size'),
            bootstraps=('bootstraps', 'first'), correct=('correct', 'all'))
       .reset_index())
g.to_csv('results/bench_summary.csv', index=False)
print(g.to_string(index=False, float_format=lambda v: f'{v:.2f}'))
for (p, q), s in g.groupby(['pred', 'query'], sort=False):
    if len(s) > 1:
        slope, icpt = np.polyfit(s['chunks'], s['mean_sec'], 1)
        r2 = np.corrcoef(s['chunks'], s['mean_sec'])[0, 1] ** 2
        print(f'{p} / {q}: {slope:.2f} s per added ciphertext, intercept {icpt:.2f} s, R^2 {r2:.4f}')
print('\nsaved results/bench_summary.csv')
