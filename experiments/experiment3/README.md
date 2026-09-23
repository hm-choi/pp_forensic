# Experiment 3 - Vehicle Behaviour Predicates on EDR Data

## Dataset

`datasets/avante_accident.csv` - Event Data Recorder (EDR) output from a Hyundai
Avante CN7, covering the seconds around a collision. 16 rows, 6 columns. The
file ends with two blank lines, so a line count reports 18.

| Field | Rows with a value |
|---|---|
| `T_rel_ms`, time relative to impact in milliseconds (negative before the crash) | 16 |
| `Speed_kmh` | 11 |
| Engine RPM | 11 |
| Driver and passenger seatbelt status | 1 each |
| Call status | 0 |

An EDR keeps no absolute clock, so time is expressed as an offset from the crash
instead of a wall-clock timestamp. A value of -1 marks a field that was not
recorded. Speed is recorded for the eleven rows up to impact and marked -1
afterwards.

## Experiment

Three predicates are evaluated on ciphertexts. Only the 0/1 verdict is
decrypted, and the query parameters are encrypted under the requester's key, so
the custodian learns neither the threshold nor the window.

- Speed increase: rotate the ciphertext by one slot, subtract, read the sign
  with `he_step`. Speed is normalized by a 200 km/h maximum so the input stays
  in the -1 to 1 range that `he_step` expects. This predicate carries no query
  parameter.
- Over-speed: subtract the encrypted threshold and read the sign. The threshold
  is divided by the same public normalization constant before encryption,
  because the speed ciphertext is already normalized when the subtraction
  happens.
- Time window: two `he_step` calls, one per encrypted bound, multiplied
  together. The bounds are encrypted in the log's own unit, because the
  timestamp ciphertext is normalized (by 5,000 ms) only after the subtraction.

Each predicate is also computed on plaintext and timed, as a check on the
homomorphic result.

Two properties of the log decide what each predicate is scored on.

The speed predicates are scored on the eleven rows that carry a speed. Asking
whether an unrecorded speed rose is not a question the log can answer, so the
rows marked -1 are outside the query, in the same way that rows without a
coordinate are outside a geofence query.

The time window is `(-3000, -1000)` milliseconds, that is from three seconds
before impact to one second before impact. Neither bound coincides with a
recorded timestamp; a bound sitting exactly on a sample would ask whether a
value is strictly less than itself, which is not a well-posed query. The bounds
also place the padding value -1 outside the window, so every padded slot answers
0 and all 32,768 slots can be checked against the plaintext answer.

## Results

All three predicates agreed with the plaintext computation on every row scored.

| Predicate | Query | Scored | Plaintext | Ciphertext | Agreement |
|---|---|---|---|---|---|
| Speed increase | consecutive rows | 11 rows | 10 | 10 | 11/11 |
| Over-speed | threshold 60 km/h | 11 rows | 4 | 4 | 11/11 |
| Time window | -3000 to -1000 ms | 32,768 slots | 4 | 4 | 32768/32768 |

Per-row answers. A dot marks a row with no recorded speed, which the speed
predicates do not score.

| Row | T_rel_ms | Speed_kmh | Incr. cipher | Incr. plain | Over cipher | Over plain | Window cipher | Window plain |
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

### Cost

Mean of 30 runs.

| Predicate | Step calls | Bootstraps | Chebyshev | Homomorphic time | Plaintext time |
|---|---|---|---|---|---|
| Speed increase | 1 | 4 | 8 | 14.33 s | 0.35 ms |
| Over-speed | 1 | 4 | 8 | 13.34 s | 0.18 ms |
| Time window | 2 | 8 | 16 | 26.01 s | 0.29 ms |

Query parameter encryption takes about 0.07 s for all three parameters
together.

The time window costs roughly twice what the other two predicates cost, because
it calls `he_step` once per bound and multiplies the two results. Its bootstrap
count is twice theirs for the same reason. The cost of a predicate tracks the
number of comparisons it contains, not the kind of quantity being compared.

## How to run

```bash
export PYTHONPATH=/pp_forensic
cd /pp_forensic/experiments/experiment3
python3 -W ignore -u test.py
```

The script writes its own transcript, so no shell redirect is needed.

## Output

| File | Contents |
|---|---|
| `results/result3.txt` | Console output |
| `results/exp3_avante_summary.csv` | Per predicate: rows scored, plaintext count, ciphertext count, agreement, worst decrypted value on each side of the decision, elapsed time for both |
| `results/exp3_avante_rows.csv` | Per row: decrypted value, ciphertext answer and plaintext answer for each of the three predicates |
