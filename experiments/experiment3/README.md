# Experiment 3 - Encrypted Geofence on GPS Coordinates

## Datasets

Two Kia K5 infotainment logs. Both store real GPS fixes, unlike the cell-tower
positions used in Experiment 2.

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
decrypting its coordinates. Both the center and the radius are query parameters,
so an investigator can supply the location and range written on a warrant.

- Rows without a coordinate are pushed to 33.06N / 124.36E, over 500 km away, so
  they always evaluate to 0.
- `compute_geofence_score` compares squared distance against squared radius and
  reads the sign with `he_step`.
- Only the 0/1 verdict is decrypted. Latitude and longitude stay encrypted.

## Results

Number of records judged inside the circle:

| Radius | K5 JellyBean | K5 KitKat |
|---|---|---|
| 0.5 km | 4 | 13 |
| 1 km | 5 | 52 |
| 5 km | 254 | 58 |
| 10 km | 258 | 72 |
| 50 km | 330 | 92 |
| 100 km | 330 | 110 |

All 12 queries matched the plaintext computation on every one of the 32,768
slots, with zero ambiguous slots. Each radius took 13 to 15 seconds.

The `gray` column in the summary CSV counts slots whose `he_step` output falls
between 0.01 and 0.99, which happens only for records sitting on the boundary.
For a 1 km query that band is about 6 m wide, and the closest record in these
logs was 14.2 m away.

## How to run

```bash
export PYTHONPATH=/pp_forensic
cd /pp_forensic/experiments/experiment3
python3 -W ignore -u test.py 2>&1 | tee results/result.txt
```

## Output

| File | Contents |
|---|---|
| `results/result.txt` | Console output |
| `results/exp3_<dataset>_summary.csv` | Per radius: plaintext count, ciphertext count, agreement, ambiguous slots, elapsed time |
| `results/exp3_<dataset>_curve.csv` | Per slot: `he_step` input and output, true distance in km |
