# Experiment 1 - Encrypted Geofence on GPS Coordinates

## Datasets

Two Kia K5 infotainment logs, both storing real GPS fixes.

| | k5_jellybean_drive.csv | k5_kitkat_drive.csv |
|---|---|---|
| Vehicle | Kia K5, 2017 | Kia K5 (DL3), 2020 |
| Platform | Android JellyBean | Android KitKat |
| Rows | 613 | 6,820 |
| Rows with GPS | 330 | 246 |
| Collection period | 2022-04-01 to 04-15, continuous | 2023-06 to 2025-06, sparse |
| Query centre used | 37.86484, 127.05997 | 37.31808, 127.12741 |

Fields present in both logs: local timestamp, epoch milliseconds, `Lat_x1e5`
and `Lon_x1e5` as integers scaled by 100,000, `Speed_kmh`, and heading in
degrees. JellyBean additionally records altitude and ignition on/off times.
KitKat additionally records a server-side timestamp (6,547 rows) and a
navigation destination identifier (25 rows).

A value of -1 marks a field that was not recorded. A stored value of 3731808
means 37.31808 degrees.

The two logs differ sharply in density. JellyBean holds two weeks of daily
driving, while KitKat spans two years but concentrates most of its fixes in
three weeks of 2024. Running the same predicate on both shows the method does
not depend on how the log was sampled.

## Experiment

Answer "was this vehicle inside a circle of radius R around point C?" without
decrypting the vehicle's coordinates and without disclosing C or R.

- Both the log coordinates and the query centre are projected to EPSG:5186
  metres before anything is encrypted, and then divided by a public width of
  884,592 m. The circuit is a plain Euclidean distance in that projected plane,
  so it carries no latitude-dependent constant. A constant derived from the
  centre latitude would have to be applied in the clear and would leak roughly
  where the circle is drawn.
- The centre and the squared radius are encrypted under the requester's key.
  The custodian receives ciphertexts only.
- `compute_geofence_score` compares squared distance against squared radius,
  which avoids a square root, then reads the sign with `he_step`.
- Rows without a coordinate are pushed to 33.06N / 124.36E, over 500 km away,
  so they always evaluate to 0.
- Only the 0/1 verdict is decrypted.

The same decision is computed on plaintext and timed, as a check on the
homomorphic result. It never produces the answer.

The swept radii are 0.2, 0.5, 1, 2, 3 and 5 km. Radii of 50 km and 100 km were
dropped from an earlier version of this sweep: both returned every observed row,
so the answer was yes regardless of where the vehicle had been. A geofence query
is only meaningful while the circle can exclude something.

## Results

All twelve queries agreed with the plaintext computation on every one of the
32,768 slots.

| Radius | KitKat plain | KitKat cipher | JellyBean plain | JellyBean cipher | Agreement |
|---|---|---|---|---|---|
| 0.2 km | 3 | 3 | 4 | 4 | 32768/32768 |
| 0.5 km | 13 | 13 | 4 | 4 | 32768/32768 |
| 1 km | 52 | 52 | 5 | 5 | 32768/32768 |
| 2 km | 56 | 56 | 5 | 5 | 32768/32768 |
| 3 km | 58 | 58 | 53 | 53 | 32768/32768 |
| 5 km | 58 | 58 | 254 | 254 | 32768/32768 |

Neither log is saturated at the widest radius: 58 of the 246 KitKat fixes and
254 of the 330 JellyBean fixes fall inside a 5 km circle, so every query in the
sweep still excludes part of the log.

### Cost

Mean of 30 runs.

| | Value |
|---|---|
| Explicit bootstraps per query | 4 |
| Chebyshev evaluations per query | 8 |
| Homomorphic time per query | 12.62 to 14.27 s |
| Query parameter encryption | about 0.02 s |
| Plaintext time per query | under 0.2 ms |

The geofence is the cheapest of the six circuits in this work, because it reads
one sign and therefore runs the step function once.

## How to run

```bash
export PYTHONPATH=/pp_forensic
cd /pp_forensic/experiments/experiment1
python3 -W ignore -u test.py
```

The script writes its own transcript, so no shell redirect is needed.

## Output

| File | Contents |
|---|---|
| `results/result1.txt` | Console output |
| `results/exp1_<dataset>_summary.csv` | Per radius: plaintext count, ciphertext count, agreement, worst decrypted value on each side of the decision, elapsed time |
| `results/exp1_all_summary.csv` | Both datasets in one table |
| `results/exp1_<dataset>_slots.csv` | A fixed sample of slots followed through every radius |
| `results/exp1_<dataset>_curve.csv` | Decrypted value against true distance |
