# Experiment 1 - Vehicle Behaviour Predicates on EDR Data

## Dataset

`datasets/avante_accident.csv` - Event Data Recorder (EDR) output from a Hyundai
Avante CN7, covering the seconds around a collision. 18 rows, 6 columns.

| Field | Rows with a value |
|---|---|
| Time relative to impact, in milliseconds (negative before the crash) | 16 |
| Speed in km/h | 11 |
| Engine RPM | 11 |
| Driver and passenger seatbelt status | 1 each |
| Call status | 0 |

An EDR keeps no absolute clock, so time is expressed as an offset from the crash
instead of a wall-clock timestamp. A value of -1 marks a field that was not
recorded.

## Experiment

Three predicates are evaluated on ciphertexts. Only the 0/1 verdict is decrypted.

- Speed increase: rotate the ciphertext by one slot, subtract, read the sign with
  `he_step`. Speed is normalized by a 200 km/h maximum so the input stays in the
  -1 to 1 range that `he_step` expects.
- Over-speed: subtract the normalized threshold and read the sign. The threshold
  is a query parameter, not a constant in the code.
- Time window: two `he_step` calls, one per bound, multiplied together.

## Results

Only the first 12 slots are printed, since the log has 18 rows and the remaining
slots are padding.

| Predicate | Query | Result |
|---|---|---|
| Speed increase | consecutive slots | slots 0-9 return 1, matching the rise from 42 to 68 km/h |
| Over-speed | threshold 60 km/h | slots 6-9 return 1 |
| Time window | -3000 ms to 5 ms | slot 4 (-3020 ms) outside, slot 5 (-2520 ms) inside |

## How to run

```bash
export PYTHONPATH=/pp_forensic
cd /pp_forensic/experiments/experiment1
python3 -W ignore -u test.py
```
