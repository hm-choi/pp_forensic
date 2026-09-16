# Experiment 3 - Encrypted Predicates on an EDR Log

## Dataset

`datasets/avante_accident.csv` - event data recorder readout from a Hyundai
Avante, covering the seconds around an impact. 16 rows.

| Field | Contents |
|---|---|
| `t_real` | Milliseconds relative to impact, negative before |
| `speed` | Vehicle speed in km/h, -1 once recording stops |

Speed is recorded for the 11 rows before impact. The remaining slots of the
32,768-slot ciphertext are padding, and `t_real` is padded with -1.

This log is short enough to print in full, so every decrypted value can be read
directly rather than summarized.

## Experiment

Evaluate three warrant conditions on one encrypted log without decrypting it, and
without disclosing the thresholds or the window to the custodian.

| Predicate | Question | Query parameter |
|---|---|---|
| `detect_speed_increase` | Did speed rise between consecutive samples? | none |
| `detect_overspeed` | Was speed above 60 km/h? | threshold, encrypted |
| `time_range` | Is the sample inside the observation window? | both bounds, encrypted |

- Every parameter is encrypted in the log's own unit. Each circuit subtracts it
  from a freshly encrypted data ciphertext first and normalizes afterwards, so
  the two operands always sit at the same level.
- `detect_speed_increase` compares the log against itself with a one-slot
  rotation, so it carries no query parameter.
- The window predicate costs two `he_step` calls, one per boundary, so it takes
  about twice as long as a single-sided comparison.

The window is -3000 ms to -1000 ms. Neither bound sits on a recorded timestamp,
since a bound on a sample would ask whether a value is strictly less than itself.
The padding value -1 also falls outside, so all 32,768 slots can be checked
against the plaintext answer.

## Results

Three predicates, all agreeing with the plaintext computation. The speed
predicates are scored on the 11 rows carrying a speed; the window predicate is
scored on all 32,768 slots including padding.

Per-row decrypted values are printed as a table and saved to
`exp3_avante_rows.csv`. Elapsed times are in the `he_sec` column of the summary
CSV. Query parameter encryption is timed separately and reported once, before the
predicates run.

## How to run

```bash
export PYTHONPATH=<repo root>
cd <repo root>/experiments/experiment3
python3 -W ignore -u test2.py
```

Console output is written to `results/result2.txt` automatically, so do not pipe
through `tee`.

## Output

| File | Contents |
|---|---|
| `results/result2.txt` | Console output |
| `results/exp3_avante_summary.csv` | Per predicate: plaintext count, ciphertext count, agreement, worst decrypted value on each side, elapsed times |
| `results/exp3_avante_rows.csv` | Per row: timestamp, speed, and the decrypted value, ciphertext verdict and plaintext verdict of each predicate |