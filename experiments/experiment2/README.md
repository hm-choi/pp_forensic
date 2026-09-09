# Experiment 2 - Encrypted Geofence on GPS Coordinates

## Datasets

Two Kia K5 infotainment logs. Both store real GPS fixes, unlike the cell-tower
positions used in Experiment 1.

| | k5_jellybean_drive.csv | k5_kitkat_drive.csv |
|---|---|---|
| Vehicle | Kia K5, 2017 | Kia K5 (DL3), 2020 |
| Platform | Android JellyBean | Android KitKat |
| Rows | 613 | 6,820 |
| Rows with GPS | 330 | 246 |
| Collection period | 2022-04-01 to 04-15, continuous | 2023-06 to 2025-06, sparse |
| Query center used | 37.86484, 127.05997 | 37.31808, 127.12741 |

Fields present in both logs: local timestamp, epoch milliseconds, latitude and
longitude as integers scaled by 100,000, speed in km/h, and heading in degrees.
JellyBean additionally records altitude and ignition on/off times. KitKat
additionally records a server-side timestamp (6,547 rows) and a navigation
destination identifier (25 rows).

A value of -1 marks a field that was not recorded. A stored value of 3731808
means 37.31808 degrees.

The two logs differ sharply in density. JellyBean holds two weeks of daily
driving, while KitKat spans two years but concentrates most of its fixes in three
weeks of 2024. Running the same predicate on both shows the method does not
depend on how the log was sampled.

## Experiment

Answer "was this vehicle inside a circle of radius R around point C?" without
decrypting its coordinates. The circuit is the one used in Experiment 1; only the
location layer differs.

- Rows without a coordinate are pushed to 33.06N / 124.36E, over 500 km away, so
  they always evaluate to 0.
- `compute_geofence_score` compares squared distance against squared radius and
  reads the sign with `he_step`.
- Only the 0/1 verdict is decrypted. Latitude and longitude stay encrypted.

The same decision is also computed on plaintext and timed, as a check on the
homomorphic result.

The swept radii are 0.2, 0.5, 1, 2, 3 and 5 km. Radii of 50 km and 100 km were
dropped from an earlier version of this sweep: both returned all 330 observed
rows of the JellyBean log, so the answer was yes regardless of where the vehicle
had been. A geofence query is only meaningful while the circle can exclude
something.

## Results

All twelve queries agreed with the plaintext computation on every one of the
32,768 slots. Each query took 11.45 to 15.55 seconds against 0.123 to 0.261
milliseconds on plaintext.

| Radius | KitKat plain | KitKat cipher | JellyBean plain | JellyBean cipher | Agreement |
|---|---|---|---|---|---|
| 0.2 km | 3 | 3 | 4 | 4 | 32768/32768 |
| 0.5 km | 13 | 13 | 4 | 4 | 32768/32768 |
| 1 km | 52 | 52 | 5 | 5 | 32768/32768 |
| 2 km | 56 | 56 | 5 | 5 | 32768/32768 |
| 3 km | 58 | 58 | 53 | 53 | 32768/32768 |
| 5 km | 58 | 58 | 254 | 254 | 32768/32768 |

Neither log is saturated at the widest radius: 58 of the 246 KitKat fixes and 254
of the 330 JellyBean fixes fall inside a 5 km circle, so every query in the sweep
still excludes part of the log.

## How to run

```bash
export PYTHONPATH=/pp_forensic
cd /pp_forensic/experiments/experiment2
python3 -W ignore -u test2.py
```

The script writes its own transcript, so no shell redirect is needed.

## Output

| File | Contents |
|---|---|
| `results/result2.txt` | Console output |
| `results/exp2_<dataset>_summary.csv` | Per radius: plaintext count, ciphertext count, agreement, elapsed time for both |
| `results/exp2_all_summary.csv` | Both datasets in one table |
