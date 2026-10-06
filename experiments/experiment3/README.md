# Experiment 3: Speeding and Acceleration

Section 6.4 and Table 8 of the paper.

## Task

Answer yes-or-no questions about the speed of a vehicle before a crash. In a controlled crash test, an Avante CN7 strikes the vehicle ahead and the driver then releases the accelerator. The same vehicle sent a crash notification to the manufacturer's server 4.8 s after deployment, so the custodian is taken to hold the crash data, and the EDR report stands in for that record. The response consists of three bits, so the pre-crash speed values themselves are not disclosed.

## Data

`datasets/avante_accident.csv`: EDR report of the airbag control unit of a Hyundai Avante CN7 (2021).

- The 11 rows with a speed are the pre-crash speed samples at 0.5 s intervals, from 42 km/h five seconds before T0 to 68 km/h at -0.5 s, followed by 5 km/h at T0. The remaining 5 rows carry no speed (-1).
- The EDR has no absolute clock. `T_rel_ms` is the offset from T0, the EDR time zero, which lies 20 ms before the airbag deployment command logged in `telematics.log` (13:09:50.233). The 11 samples occupy consecutive slots in time order.
- Speed (`Speed_kmh`) is divided by 200 and time (`T_rel_ms`) by 5,000.

## Predicates

| Predicate | Function | Query parameter | Step calls | Btsp. | Scored on |
| --- | --- | --- | --- | --- | --- |
| Speed increase, Eq. (1) on adjacent slots | `detect_speed_increase` | none | 1 | 4 | the 11 speed samples |
| Speed threshold, Eq. (1) | `detect_overspeed` | 60 km/h | 1 | 4 | the 11 speed samples |
| Time window, Eq. (4) | `time_range` | -3,000 to -1,000 ms | 2 | 8 | all 32,768 slots |

The threshold and the two bounds of the time window are chosen by the investigator and reach the custodian only as ciphertexts. The window runs from three seconds to one second before T0. Neither bound coincides with a recorded time, and the value -1 lies outside the window, so every padded slot can be checked against the plaintext decision. The speed predicates are scored on the rows that carry a speed.

## Results (A100, 30 runs)

All three predicates agreed with the plaintext decision on every scored slot in every run. Decrypted values per slot, worst case over the 30 runs:

| Slot | T_rel_ms | Speed | Speed increase | Speed threshold | Time window |
| --- | --- | --- | --- | --- | --- |
| | | | 4 Btsp., 0.45 s | 4 Btsp., 0.43 s | 8 Btsp., 0.88 s |
| 0 | -5020 | 42 | 0.9999999999 | -0.0000000004 | -0.0000000008 |
| 1 | -4520 | 46 | 0.9999999985 | -0.0000000014 | 0.0000000008 |
| 2 | -4020 | 50 | 0.9999999983 | 0.0000000015 | 0.0000000012 |
| 3 | -3520 | 53 | 1.0000000000 | -0.0000000004 | -0.0000000005 |
| 4 | -3020 | 56 | 0.9999999994 | 0.0000000013 | -0.0000000012 |
| 5 | -2520 | 59 | 0.9999999994 | 0.0000000018 | 0.9999999993 |
| 6 | -2020 | 61 | 0.9999999997 | 0.9999999993 | 0.9999999983 |
| 7 | -1520 | 64 | 0.9999999992 | 0.9999999988 | 0.9999999989 |
| 8 | -1020 | 66 | 0.9999999991 | 0.9999999993 | 0.9999999986 |
| 9 | -520 | 68 | 0.9999999999 | 0.9999999999 | -0.0000000006 |
| 10 | -20 | 5 | 0.0000000004 | -0.0000000003 | 0.0000000004 |

The circumstances reconstructed from the three bits are consistent with the EDR report: the vehicle accelerated continuously from five seconds before T0, exceeded 60 km/h from 2.02 s before T0 onward, and the queried window isolates four rows (slots 5 to 8) of that acceleration segment.

The time window costs twice the other two predicates because it calls the step function once per bound. Encrypting the three query parameters takes 0.13 s.

## Run

```
export PYTHONPATH=<repo root> HE_DEVICE=gpu
cd <repo root>/experiments/experiment3
python3 -W ignore -u test.py
```

## Output

Written to `results/` next to the script. The 30 A100 runs are in `results/runs/run_XX/` of the repository root.

| File | Contents |
| --- | --- |
| `result3.txt` | Console output |
| `exp3_avante_summary.csv` | Per predicate: scored rows, plaintext and ciphertext counts, agreement, worst decrypted values, times, Btsp. The speed threshold is labeled `overspeed`. |
| `exp3_avante_rows.csv` | Per row: decrypted value, ciphertext decision and plaintext decision of each predicate |
