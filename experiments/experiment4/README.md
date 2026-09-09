# Experiment 4 - Vehicle Behaviour Predicates on EDR Data

## Dataset

`datasets/avante_accident.csv` - Event Data Recorder (EDR) output from a Hyundai
Avante CN7, covering the seconds around a collision. 16 rows, 6 columns. The file
ends with two blank lines, so a line count reports 18.

| Field | Rows with a value |
|---|---|
| Time relative to impact, in milliseconds (negative before the crash) | 16 |
| Speed in km/h | 11 |
| Engine RPM | 11 |
| Driver and passenger seatbelt status | 1 each |
| Call status | 0 |

An EDR keeps no absolute clock, so time is expressed as an offset from the crash
instead of a wall-clock timestamp. A value of -1 marks a field that was not
recorded. Speed is recorded for the eleven rows up to impact and marked -1
afterwards.

## Experiment

Three predicates are evaluated on ciphertexts. Only the 0/1 verdict is decrypted.

- Speed increase: rotate the ciphertext by one slot, subtract, read the sign with
  `he_step`. Speed is normalized by a 200 km/h maximum so the input stays in the
  -1 to 1 range that `he_step` expects.
- Over-speed: subtract the normalized threshold and read the sign. The threshold
  is a query parameter, not a constant in the code.
- Time window: two `he_step` calls, one per bound, multiplied together.

Each predicate is also computed on plaintext and timed, as a check on the
homomorphic result.

Two properties of the log decide what each predicate is evaluated on.

The speed predicates are scored on the eleven rows that carry a speed. Asking
whether an unrecorded speed rose is not a question the log can answer, so the
rows marked -1 are outside the query, in the same way that rows without a
coordinate are outside a geofence query.

The time window is `(-3000, -1000)` milliseconds, that is from three seconds
before impact to one second before impact. Neither bound coincides with a
recorded timestamp; a bound sitting exactly on a sample would ask whether a value
is strictly less than itself, which is not a well-posed query. The bounds also
place the padding value -1 outside the window, so every padded slot answers 0 and
all 32,768 slots can be checked against the plaintext answer.

## Results

All three predicates agreed with the plaintext computation on every row scored.

| Predicate | Query | Scored | Plaintext | Ciphertext | Agreement | HE time | Plaintext time |
|---|---|---|---|---|---|---|---|
| Speed increase | consecutive rows | 11 rows | 10 | 10 | 11/11 | 15.78 s | 0.347 ms |
| Over-speed | threshold 60 km/h | 11 rows | 4 | 4 | 11/11 | 13.19 s | 0.133 ms |
| Time window | -3000 to -1000 ms | 32,768 slots | 4 | 4 | 32768/32768 | 27.06 s | 0.192 ms |

Per-row answers. A dot marks a row with no recorded speed, which the speed
predicates do not cover.

| row | t_real | speed | incr | plain | over | plain | win | plain |
|---|---|---|---|---|---|---|---|---|
| 0 | -5020 | 42 | 1 | 1 | 0 | 0 | 0 | 0 |
| 1 | -4520 | 46 | 1 | 1 | 0 | 0 | 0 | 0 |
| 2 | -4020 | 50 | 1 | 1 | 0 | 0 | 0 | 0 |
| 3 | -3520 | 53 | 1 | 1 | 0 | 0 | 0 | 0 |
| 4 | -3020 | 56 | 1 | 1 | 0 | 0 | 0 | 0 |
| 5 | -2520 | 59 | 1 | 1 | 0 | 0 | 1 | 1 |
| 6 | -2020 | 61 | 1 | 1 | 1 | 1 | 1 | 1 |
| 7 | -1520 | 64 | 1 | 1 | 1 | 1 | 1 | 1 |
| 8 | -1020 | 66 | 1 | 1 | 1 | 1 | 1 | 1 |
| 9 | -520 | 68 | 1 | 1 | 1 | 1 | 0 | 0 |
| 10 | -20 | 5 | 0 | 0 | 0 | 0 | 0 | 0 |
| 11 | -20 | -1 | . | . | . | . | 0 | 0 |
| 12 | -3 | -1 | . | . | . | . | 0 | 0 |
| 13 | 0 | -1 | . | . | . | . | 0 | 0 |
| 14 | 5 | -1 | . | . | . | . | 0 | 0 |
| 15 | 11 | -1 | . | . | . | . | 0 | 0 |

The reconstruction the three predicates give is the expected one: the vehicle
accelerates from 42 to 68 km/h over the five seconds before impact, exceeds
60 km/h from 2.02 seconds before impact onward, and the queried window isolates
rows 5 to 8.

The time window costs roughly twice what the other two predicates cost, because
it calls `he_step` once per bound and multiplies the two results. The cost of a
predicate tracks the number of comparisons it contains.

## How to run

```bash
export PYTHONPATH=/pp_forensic
cd /pp_forensic/experiments/experiment4
python3 -W ignore -u test2.py
```

The script writes its own transcript, so no shell redirect is needed.

## Output

| File | Contents |
|---|---|
| `results/result2.txt` | Console output |
| `results/exp4_avante_summary.csv` | Per predicate: rows scored, plaintext count, ciphertext count, agreement, elapsed time for both |
| `results/exp4_avante_rows.csv` | Per row: ciphertext and plaintext answer for each of the three predicates |
