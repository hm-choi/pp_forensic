# Multi-Chunk Scaling on the Encrypted Geofence

## Motivation

Every other experiment in this repository keeps its data at or under
`num_slots` (32,768 at `log_slots = 15`), so it always fits in a single
ciphertext. `HEOperator` is written to also cover data longer than that,
splitting it into several ciphertext chunks. This experiment is the one that
actually exercises that path, and measures how homomorphic time scales as the
chunk count grows:

> Currently every experiment stays within one ciphertext's worth of slots, but
> the PP-Forensics code also covers longer inputs. The only expected cost is
> that homomorphic time scales with the number of ciphertexts, which can be
> reported as a result rather than left as a Discussion point.

## Dataset

`datasets/sorento_drive.csv`, the same Kia Sorento cell-tower log used
elsewhere. At `log_slots = 15` its 154,272 rows already span 5 ciphertext
chunks, so it is tiled cyclically (`np.resize`) up to each swept length rather
than truncated to one chunk. This is a ciphertext-count scaling test, not a
claim about a longer drive.

## Experiment

The circuit is unchanged: `compute_geofence_score`, the same one used in the
other geofence experiments. Only the input length changes.

- `SLOT_MULTIPLES = [1, 2, 3, 4, 5]` — 1x is one ciphertext chunk (32,768
  rows), 5x is five (163,840 rows).
- The query centre and radius are encrypted with `encrypt_param(value,
  size=...)`, broadcasting to the same chunk count as the coordinate data,
  so every chunk is compared against the same query.
- `RADIUS_LIST` and the query centre are the same as the other Sorento
  geofence runs, swept at every multiple.
- Each run also counts bootstrap and Chebyshev-evaluation calls
  (`operators/bscount.py`), which should scale linearly with the chunk count
  since each chunk is processed independently.

## Results

10 runs, `run_sorento_10.sh` / `aggregate_sorento.py`. All 10 runs agreed on
every decision bit at every multiple and every radius (0 mismatches, 30
queries per run). Figures below are the mean over the 6 radii and 10 runs.

| Multiple | Chunks | Rows | HE time (mean ± std) | Param enc. time | Plaintext time | Bootstraps | Chebyshev evals |
|---|---|---|---|---|---|---|---|
| 1x | 1 | 32,768 | 12.67 s ± 0.59 s | 22.1 ms | 0.33 ms | 4 | 8 |
| 2x | 2 | 65,536 | 23.20 s ± 0.86 s | 43.0 ms | 1.29 ms | 8 | 16 |
| 3x | 3 | 98,304 | 33.91 s ± 0.80 s | 63.1 ms | 0.72 ms | 12 | 24 |
| 4x | 4 | 131,072 | 45.09 s ± 1.26 s | 85.6 ms | 0.42 ms | 16 | 32 |
| 5x | 5 | 163,840 | 55.80 s ± 1.15 s | 108.4 ms | 0.60 ms | 20 | 40 |

HE time grows linearly with the chunk count (roughly 12.7 s per chunk, close
to the single-chunk figure reported for the other geofence experiments), and
so do the bootstrap and Chebyshev-evaluation counts, at a fixed 4 bootstraps
and 8 Chebyshev evaluations per chunk. Each run scores 30 queries (5
multiples x 6 radii); all 30 matched the plaintext computation in every one
of the 10 runs.

The tables below are the per-radius detail from one representative run
(`results/exp_sorento_<N>x_summary.csv`), the same breakdown the single-chunk
Sorento experiment reports, at each swept multiple. Agreement is out of the
full slot count at that multiple.

### 1x (1 chunk, 32,768 rows)

| Radius | Plaintext | Ciphertext | Agreement | HE time | Plaintext time |
|---|---|---|---|---|---|
| 0.5 km | 5,784 | 5,784 | 32768/32768 | 13.81 s | 0.152 ms |
| 1 km | 5,784 | 5,784 | 32768/32768 | 11.90 s | 0.096 ms |
| 2 km | 5,784 | 5,784 | 32768/32768 | 11.85 s | 0.118 ms |
| 3 km | 12,380 | 12,380 | 32768/32768 | 12.18 s | 0.149 ms |
| 5 km | 17,370 | 17,370 | 32768/32768 | 12.60 s | 0.130 ms |
| 10 km | 19,410 | 19,410 | 32768/32768 | 11.83 s | 0.167 ms |

### 2x (2 chunks, 65,536 rows)

| Radius | Plaintext | Ciphertext | Agreement | HE time | Plaintext time |
|---|---|---|---|---|---|
| 0.5 km | 5,784 | 5,784 | 65536/65536 | 25.38 s | 0.257 ms |
| 1 km | 5,784 | 5,784 | 65536/65536 | 25.16 s | 0.240 ms |
| 2 km | 5,784 | 5,784 | 65536/65536 | 24.25 s | 0.176 ms |
| 3 km | 12,380 | 12,380 | 65536/65536 | 25.35 s | 0.806 ms |
| 5 km | 17,370 | 17,370 | 65536/65536 | 23.90 s | 0.198 ms |
| 10 km | 19,410 | 19,410 | 65536/65536 | 22.92 s | 0.173 ms |

### 3x (3 chunks, 98,304 rows)

| Radius | Plaintext | Ciphertext | Agreement | HE time | Plaintext time |
|---|---|---|---|---|---|
| 0.5 km | 5,784 | 5,784 | 98304/98304 | 36.68 s | 0.336 ms |
| 1 km | 5,784 | 5,784 | 98304/98304 | 34.03 s | 0.205 ms |
| 2 km | 5,784 | 5,784 | 98304/98304 | 35.55 s | 0.236 ms |
| 3 km | 12,380 | 12,380 | 98304/98304 | 33.90 s | 0.931 ms |
| 5 km | 26,728 | 26,728 | 98304/98304 | 34.16 s | 0.239 ms |
| 10 km | 39,330 | 39,330 | 98304/98304 | 34.87 s | 0.207 ms |

### 4x (4 chunks, 131,072 rows)

| Radius | Plaintext | Ciphertext | Agreement | HE time | Plaintext time |
|---|---|---|---|---|---|
| 0.5 km | 14,540 | 14,540 | 131072/131072 | 44.93 s | 0.307 ms |
| 1 km | 14,540 | 14,540 | 131072/131072 | 47.36 s | 0.362 ms |
| 2 km | 14,540 | 14,540 | 131072/131072 | 44.82 s | 1.647 ms |
| 3 km | 28,789 | 28,789 | 131072/131072 | 44.65 s | 0.681 ms |
| 5 km | 48,141 | 48,141 | 131072/131072 | 44.71 s | 0.398 ms |
| 10 km | 69,156 | 69,156 | 131072/131072 | 43.63 s | 0.433 ms |

### 5x (5 chunks, 163,840 rows)

| Radius | Plaintext | Ciphertext | Agreement | HE time | Plaintext time |
|---|---|---|---|---|---|
| 0.5 km | 16,880 | 16,880 | 163840/163840 | 58.25 s | 0.745 ms |
| 1 km | 16,880 | 16,880 | 163840/163840 | 56.17 s | 1.254 ms |
| 2 km | 16,880 | 16,880 | 163840/163840 | 55.49 s | 0.655 ms |
| 3 km | 33,695 | 33,695 | 163840/163840 | 55.24 s | 0.990 ms |
| 5 km | 54,881 | 54,881 | 163840/163840 | 55.18 s | 0.700 ms |
| 10 km | 78,297 | 78,297 | 163840/163840 | 54.85 s | 0.774 ms |

Row counts grow with the multiple because the log is tiled, not because a
wider radius is catching more of the same fixed set of towers, so plaintext
and ciphertext counts should be compared within a multiple, not across
multiples.

## How to run

```bash
export PYTHONPATH=/pp_forensic
cd /pp_forensic/experiments/experiment_multichunk_sorento
python3 -W ignore -u test2.py
```

For repeated runs (mean/standard deviation across runs), from the repo root:

```bash
./run_sorento_10.sh 10
python3 aggregate_sorento.py
```

`run_sorento_10.sh` saves each run's `results/` under `runs_sorento/run_NN/`
and `aggregate_sorento.py` combines them into
`aggregated_sorento/exp_sorento_all_summary.csv` (mean and standard deviation
of every `_sec` column, grouped by multiple and radius). Both `runs_sorento/`
and `aggregated_sorento/` are local-only (`.gitignore`); the `results/`
folder here holds one representative run.

## Output

| File | Contents |
|---|---|
| `results/result2.txt` | Console output |
| `results/exp_sorento_<N>x_summary.csv` | Per radius at multiple N: plaintext count, ciphertext count, agreement, elapsed time, bootstrap/Chebyshev counts |
| `results/exp_sorento_<N>x_slots.csv` | Per-slot decrypted readings for a fixed sample, at multiple N |
| `results/exp_sorento_all_summary.csv` | Every multiple and radius in one table |
