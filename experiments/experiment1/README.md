# Experiment 1 - Encrypted Geofence on GPS Coordinates

## Datasets

Two Kia K5 infotainment logs holding real GPS fixes.

| | k5_kitkat_drive.csv | k5_jellybean_drive.csv |
|---|---|---|
| Vehicle | Kia K5 (DL3), 2020 | Kia K5, 2017 |
| Platform | Android KitKat | Android JellyBean |
| Rows | 6,820 | 613 |
| Rows with GPS | 246 | 330 |
| Collection period | 2023-06 to 2025-06, sparse | 2022-04-01 to 04-15, continuous |
| Query center | 37.31808, 127.12741 | 37.86484, 127.05997 |

Latitude and longitude are stored as integers scaled by 100,000, so 3731808
means 37.31808 degrees. A value of -1 marks a field that was not recorded.
Only the first 32,768 rows are used, which is one ciphertext at `log_slots = 15`.

The two logs differ in density on purpose: JellyBean is two weeks of daily
driving, KitKat spans two years. Running the same query on both shows the method
does not depend on how the log was sampled.

## Experiment

Answer "was this vehicle inside a circle of radius R around point C?" without
decrypting the coordinates, and without disclosing C or R to the custodian.

- Both sides project to EPSG:5186 metres with `tm.py` and divide by the public
  width `L_M`, all in the clear, before encrypting. The circuit is then a plain
  Euclidean distance and holds no latitude dependent constant, which is what
  keeps the query centre hidden.
- The requester encrypts the centre and the normalized radius. The custodian
  receives ciphertexts only.
- `compute_geofence_score` squares both sides and compares, avoiding a square
  root, then reads the sign with `he_step`. Squaring the radius inside the
  circuit puts it at the same level as the squared distance, so no level
  adjustment is needed.
- Rows without a coordinate are pushed to 33.06N / 124.36E, so they always
  evaluate to 0.
- Only the 0/1 verdict is decrypted.

## Results

Records judged inside the circle, over 12 queries:

| Radius | K5 KitKat | K5 JellyBean |
|---|---|---|
| 0.2 km | 3 | 4 |
| 0.5 km | 13 | 4 |
| 1 km | 52 | 5 |
| 2 km | 56 | 5 |
| 3 km | 58 | 53 |
| 5 km | 58 | 254 |

Radii of 50 km and 100 km were dropped: both return every observed row, and an
answer that is always yes carries no information.

Every query agreed with the plaintext computation on all 32,768 slots. Elapsed
times are in the `he_sec` column of the summary CSV; `param_enc_sec` is the
requester-side cost of encrypting the radius, kept separate from the circuit.

## How to run

```bash
export PYTHONPATH=<repo root>
cd <repo root>/experiments/experiment1
python3 -W ignore -u test2.py
```

`tm.py` must sit in this folder. Console output is written to
`results/result2.txt` automatically, so do not pipe through `tee`.

## Output

| File | Contents |
|---|---|
| `results/result2.txt` | Console output |
| `results/exp1_<dataset>_summary.csv` | Per radius: plaintext count, ciphertext count, agreement, worst decrypted value on each side, elapsed times |
| `results/exp1_<dataset>_slots.csv` | Per slot: true distance, plaintext verdict, decrypted value |
| `results/exp1_all_summary.csv` | Both datasets combined |