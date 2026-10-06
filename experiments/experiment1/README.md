# Experiment 1: Location History

Section 6.2 and Table 6 of the paper.

## Task

Decide whether a vehicle passed through a given area. The custodian is taken to be the cloud of a map service provider that holds the location history. The investigator sends the query center and the radius as ciphertexts and receives only the decision.

## Data

| | K5 JF (2017) | K5 DL3 (2020) |
| --- | --- | --- |
| File | `datasets/k5_jellybean_drive.csv` | `datasets/k5_kitkat_drive.csv` |
| IVI platform | Jellybean (Android 4.2.2) | KitKat (Android 4.4.2) |
| Source of the coordinates | vehicle big-data JSON (`infobigdata.everylog.json`, Base64 decoded) | `[CMM]VI-185 wdwStatus` lines of `telematics.log` |
| Records | 613 | 6,820 |
| Records with a GPS fix | 330 | 246 |
| Query center | 37.86484, 127.05997 | 37.31808, 127.12741 |

The rows of each feature matrix are placed in the 32,768 slots of a single ciphertext.

## Predicate

Radius predicate, Eq. (3), `HEForensicTest.compute_geofence_score`.

- Both the log coordinates and the query center are projected to EPSG:5186 meters before encryption and divided by the public normalization width L = 884,592 m. The circuit is a plain Euclidean distance in that plane, so no latitude-dependent factor stays in the circuit.
- The squared distance is compared with the squared radius, which avoids a square root. One step call, 4 Btsp.
- Rows without a coordinate are substituted with 33.06 N, 124.36 E, more than 500 km from every recorded location, so they always evaluate to 0.
- Radii of 0.2, 0.5, 1, 2, 3 and 5 km, corresponding to a building, an intersection and an administrative neighborhood. Wider radii return every observed coordinate.

## Results (A100, 30 runs)

All twelve queries matched the plaintext decision on all 32,768 slots in every run. Decrypted values are the worst case over all slots and all 30 runs.

| Radius (km) | Inside rows | Inside, decrypted | Outside rows | Outside, decrypted | Btsp. | Time (s) |
| --- | --- | --- | --- | --- | --- | --- |
| **K5 JF (2017)** | | | | | | |
| 0.2 | 4 | 0.9961677324 | 32,764 | 3.8e-9 | 4 | 0.44 |
| 0.5 | 4 | 0.9999999985 | 32,764 | 4.7e-9 | 4 | 0.44 |
| 1 | 5 | 0.9999999988 | 32,763 | 4.7e-9 | 4 | 0.44 |
| 2 | 5 | 0.9999999982 | 32,763 | 3.9e-9 | 4 | 0.44 |
| 3 | 53 | 0.9999999980 | 32,715 | 4.1e-9 | 4 | 0.44 |
| 5 | 254 | 0.9999999975 | 32,514 | 4.0e-9 | 4 | 0.44 |
| **K5 DL3 (2020)** | | | | | | |
| 0.2 | 3 | 0.7649887983 | 32,765 | 4.4e-9 | 4 | 0.46 |
| 0.5 | 13 | 0.9999999986 | 32,755 | 4.2e-9 | 4 | 0.44 |
| 1 | 52 | 0.9999999972 | 32,716 | 4.5e-9 | 4 | 0.44 |
| 2 | 56 | 0.9999999979 | 32,712 | 4.4e-9 | 4 | 0.44 |
| 3 | 58 | 0.9999999970 | 32,710 | 3.8e-9 | 4 | 0.44 |
| 5 | 58 | 0.9999999977 | 32,710 | 3.4e-9 | 4 | 0.44 |

For radii of 0.5 km and above, every slot inside the circle decrypts to at least 0.999999997. At 0.2 km, two records lying 10 m and 40 m inside the query boundary fall to 0.76 and 0.996, which correspond to step-function margins of 5.2e-9 and 1.8e-8. Every input whose margin is at least 3e-8 decrypts to 0.999999997 or above, so the resolution of the approximation is on the order of 1e-8, a few tens of meters from the boundary.

Encrypting the query parameters takes 0.04 to 0.05 s.

## Run

```
export PYTHONPATH=<repo root> HE_DEVICE=gpu
cd <repo root>/experiments/experiment1
python3 -W ignore -u test.py
```

## Output

Written to `results/` next to the script. The 30 A100 runs are in `results/runs/run_XX/` of the repository root.

| File | Contents |
| --- | --- |
| `result1.txt` | Console output |
| `exp1_all_summary.csv` | Both vehicles: per radius, plaintext and ciphertext counts, agreement, worst decrypted value inside and outside, times, Btsp. |
| `exp1_k5_jellybean_summary.csv`, `exp1_k5_kitkat_summary.csv` | The same per vehicle |
| `exp1_k5_jellybean_slots.csv`, `exp1_k5_kitkat_slots.csv` | A fixed sample of slots followed through every radius: distance, plaintext decision, decrypted value |
