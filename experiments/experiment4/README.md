# Experiment 4: Scalability

Section 6.5 and Table 9 of the paper.

## Task

Show that the size of the data is not bounded by the 32,768 slots of a single ciphertext. The feature matrix of each experiment is tiled cyclically to fill 1, 2, 4, 8 and 32 ciphertexts; 32 ciphertexts hold 1,048,576 rows, about one million records. The homomorphic runtime depends on the number of ciphertexts and not on the values, so a tiled matrix costs what a genuinely longer log would.

## Setting

| Column of Table 9 | Data | Query |
| --- | --- | --- |
| Radius | K5 DL3 (2020), as in Experiment 1 | center 37.31808, 127.12741, radius 1 km |
| Speed threshold | Avante CN7 (2021) EDR, as in Experiment 3 | 60 km/h |
| Time window | Avante CN7 (2021) EDR, as in Experiment 3 | -3,000 to -1,000 ms |
| Phone-number match | Niro (2018), as in Experiment 2 | 010-5000-2924, match and existence circuit |

For each predicate and each number of ciphertexts, the input is encrypted once, the circuit is evaluated once as a warm-up and its decision is checked against plaintext on every row, and the same circuit is then timed 30 times. `colab/run_a100.sh` runs 1, 2, 4 and 8 ciphertexts in one process and 32 ciphertexts in a second process.

Tiling multiplies the matches of the phone number (61,680 at 32 ciphertexts), so the declared bound of the existence circuit is C = 65,536.

## Results (A100, mean of 30 timed runs)

Time (s) by the number of ciphertexts, Btsp. in parentheses. The decision was correct on every row at every point, and the standard deviation is at most 0.01 s.

| Ciphertexts | Rows | Radius | Speed threshold | Time window | Phone-number match |
| --- | --- | --- | --- | --- | --- |
| 1 | 32,768 | 0.45 (4) | 0.44 (4) | 0.89 (8) | 3.35 (31) |
| 2 | 65,536 | 0.89 (8) | 0.89 (8) | 1.78 (16) | 6.24 (58) |
| 4 | 131,072 | 1.79 (16) | 1.78 (16) | 3.55 (32) | 12.04 (112) |
| 8 | 262,144 | 3.58 (32) | 3.55 (32) | 7.11 (64) | 23.63 (220) |
| 32 | 1,048,576 | 14.21 (128) | 14.11 (128) | 28.25 (256) | 92.60 (868) |

Linear fit over all five points (`bench_summary.py`):

| Predicate | Per added ciphertext (s) | Intercept (s) | R^2 |
| --- | --- | --- | --- |
| Radius | 0.44 | 0.01 | 1.0000 |
| Speed threshold | 0.44 | 0.01 | 1.0000 |
| Time window | 0.88 | 0.02 | 1.0000 |
| Phone-number match | 2.88 | 0.52 | 1.0000 |

The runtime grows linearly with the number of ciphertexts, adding about 0.44 s per ciphertext for each step call. A line fitted on 1 to 8 ciphertexts only (`tools/scale_check.py`) predicts the runtime at 32 ciphertexts within 0.7% (radius 14.3 s predicted and 14.2 s measured; phone-number match 93.2 s and 92.6 s). About one million records are evaluated in 14.2 s for a radius query and in 92.6 s for phone-number matching.

For phone-number matching, the existence circuit runs once on the sum over all ciphertexts, so its cost does not grow with their number; this is the intercept of 0.52 s.

## Run

```
export PYTHONPATH=<repo root> HE_DEVICE=gpu
cd <repo root>/experiments/experiment4
python3 -W ignore -u bench.py > bench.log 2>&1
python3 bench_summary.py
```

`bench.py` reads `PREDS` (default `geo,edr,phone`), `MULTIPLES` (default `1,2,4,8,32`), `REPS` (default `30`) and `PHONE_C` (default `65536`) from the environment.

## Output

Written to `results/` next to the script. The A100 results are in `results/experiment4/` of the repository root.

| File | Contents |
| --- | --- |
| `bench_times_small.csv`, `bench_times_big.csv` | Every timed run for 1, 2, 4, 8 and for 32 ciphertexts: predicate, number of ciphertexts, rows, time, Btsp., correctness |
| `bench_summary.csv`, `bench_summary.txt` | Mean and standard deviation per point and the linear fit |
| `scale_check.txt` | Fit on 1 to 8 ciphertexts and its prediction for 32 |

In these files the radius predicate is labeled `geo` and the EDR predicates `edr`.
