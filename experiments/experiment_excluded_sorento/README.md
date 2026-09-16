# Experiment 1 - Encrypted Geofence on Cell-Tower Coordinates

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
vehicle connected rather than exactly where it was. A value of -1 marks a field
that was not recorded.

Only the first 32,768 rows are used, since that is one ciphertext at
`log_slots = 15`. Within that window 20,462 rows carry a coordinate, and those
rows resolve to 11 distinct towers. The closest pair of towers is 1.893 km apart,
and the nearest tower to the query center used here is 2.077 km away.

## Experiment

Decide whether the vehicle was within a given radius of a given point, without
decrypting its recorded positions. Both the center and the radius are query
parameters, so an investigator can supply the location and range written on a
warrant. Only the 0/1 verdict is decrypted.

- Rows without a coordinate are pushed to 33.06N / 124.36E, far from any query
  center, so they always evaluate to 0.
- `compute_geofence_score` compares squared distance against squared radius,
  which avoids a square root, then reads the sign with `he_step`.

The same decision is also computed on plaintext and timed. The plaintext result
is used only to check the homomorphic result; it never produces the answer.

The radius is swept rather than fixed. Because the log records which tower the
vehicle connected to and not where it stood, the useful lower bound on a query
radius is set by the spacing of the towers.

## Results

All six queries agreed with the plaintext computation on every one of the 32,768
slots.

| Radius | Plaintext | Ciphertext | Agreement | HE time | Plaintext time |
|---|---|---|---|---|---|
| 0.5 km | 5,784 | 5,784 | 32768/32768 | 12.96 s | 0.153 ms |
| 1 km | 5,784 | 5,784 | 32768/32768 | 13.11 s | 0.128 ms |
| 2 km | 5,784 | 5,784 | 32768/32768 | 12.58 s | 0.132 ms |
| 3 km | 12,380 | 12,380 | 32768/32768 | 12.56 s | 0.117 ms |
| 5 km | 17,370 | 17,370 | 32768/32768 | 13.29 s | 0.141 ms |
| 10 km | 19,410 | 19,410 | 32768/32768 | 13.13 s | 0.103 ms |

The first three radii differ by a factor of four and return the same count,
because any radius below 2.077 km selects the center tower alone. The circuit
answers correctly every time; what bounds the query is the resolution of the
input. Experiment 2 runs the same circuit on GPS fixes, where the resolution is
metres rather than kilometres.

## How to run

```bash
export PYTHONPATH=/pp_forensic
cd /pp_forensic/experiments/experiment1
python3 -W ignore -u test2.py
```

The script writes its own transcript, so no shell redirect is needed.

## Output

| File | Contents |
|---|---|
| `results/result2.txt` | Console output |
| `results/exp1_sorento_summary.csv` | Per radius: plaintext count, ciphertext count, agreement, elapsed time for both |
