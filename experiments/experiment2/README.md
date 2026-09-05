# Experiment 2 - Encrypted Geofence on Cell-Tower Coordinates

## Dataset

`datasets/sorento_drive.csv` - infotainment log from a Kia Sorento running the
ccNC platform. 154,272 rows, 27 columns.

| Field | Rows with a value |
|---|---|
| Local timestamp and epoch milliseconds | 154,272 |
| Cell-tower latitude and longitude, integers scaled by 100,000 | 135,739 |
| Speed in km/h | 131,002 |
| Cell identifiers (cell id, LAC, eNodeB id) | 153,794 |
| Door and seatbelt warning states | 2,175 to 24,363 |

The positions are cell-tower coordinates, not GPS fixes, so they mark where the
vehicle connected rather than exactly where it was. Only 12 distinct towers
appear. A value of -1 marks a field that was not recorded.

Only the first 32,768 rows are used, since that is one ciphertext at
`log_slots = 15`.

## Experiment

Decide whether the vehicle was within 1 km of a given point, without decrypting
its recorded positions.

- Rows without a coordinate are pushed to 33.06N / 124.36E, far from any query
  center, so they always evaluate to 0.
- `compute_geofence_score` compares squared distance against squared radius,
  which avoids a square root, then reads the sign with `he_step`.

## Results

The first 20 slots are printed. Slots inside the circle return values within
1e-10 of 1, and slots outside return values within 1e-10 of 0. The residual comes
from `he_step` being a polynomial approximation of a step function.

Because tower coordinates repeat across many rows, radii smaller than the spacing
between towers give identical counts. Experiment 3 uses real GPS fixes instead.

## How to run

```bash
export PYTHONPATH=/pp_forensic
cd /pp_forensic/experiments/experiment2
python3 -W ignore -u test.py
```
