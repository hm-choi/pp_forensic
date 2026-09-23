# PP-Forensics

Privacy-preserving forensic analytics over vehicle software platform logs,
built on CKKS homomorphic encryption.

A requesting agency asks a question about a vehicle log that a custodian holds.
The custodian evaluates the question on ciphertext and returns a single bit.
The custodian never learns what was asked, and the agency never receives the
log. Query parameters are encrypted under the requester's key, so a warrant's
location, threshold, time window or phone number stays hidden as well.

This repository holds the homomorphic-encryption half of the work: the
predicate circuits, the experiments that validate them, and the measurement
harness.

## Layout

```
engine/        HEaaN context, key management, bootstrapping
hedata/        Container holding one or more CKKS ciphertexts
operators/     Homomorphic operators, composite sign and step function,
               forensic predicates, bootstrapping counters
datasets/      Vehicle logs used by the experiments
experiments/   One folder per experiment, each with its own README
```

`operators/forensic_operator.py` is the entry point. Every predicate the
experiments evaluate goes through it.

## Experiments

| Folder | Subject | Data |
|---|---|---|
| `experiment1` | Geofence on GPS coordinates | Kia K5 infotainment, two platform versions |
| `experiment2` | Phone number lookup | Kia Niro Bluetooth call history |
| `experiment3` | Vehicle behaviour predicates | Hyundai Avante CN7 event data recorder |

## Predicates

| Predicate | Column | Step calls | Bootstraps | Chebyshev evaluations |
|---|---|---|---|---|
| Geofence | `Lat_x1e5`, `Lon_x1e5` | 1 | 4 | 8 |
| Number match | `Peer_number` | 6 | 27 | 48 |
| Number existence | (match ciphertext) | 1 | 4 | 8 |
| Speed increase | `Speed_kmh` | 1 | 4 | 8 |
| Over-speed | `Speed_kmh` | 1 | 4 | 8 |
| Time window | `T_rel_ms` | 2 | 8 | 16 |

Bootstraps counts the calls this framework issues explicitly. The Chebyshev
evaluation routine bootstraps further on its own, which the SDK manages and
which is not counted here.

Runtime follows the bootstrap count rather than the kind of predicate. Across
all six circuits, measured time divided by bootstrap count falls between 2.9 and
3.6 seconds, averaging about 3.2 seconds on the machine below. Number match is
slow because it runs six step functions, not because matching a number is
intrinsically harder than drawing a circle.

## Requirements

- CryptoLab HEaaN SDK, CPU build, FGb parameter set
- Python 3.10, numpy, pandas
- A key directory the engine can read and write

The experiments run inside the vendor Docker image. Reference machine:
Intel Xeon Sapphire Rapids, 16 vCPU, 64 GB RAM.

## Running

Each experiment runs from its own folder.

```bash
export PYTHONPATH=<repo root>
cd <repo root>/experiments/experiment1
python3 -W ignore -u test.py
```

Results land in `results/` next to the script. The script installs its own
console tee, so the transcript is written for you and no shell redirect is
needed.

Reported figures are the mean of 30 repetitions. The first bootstrapping call
of a process is slower than the rest, so `HEEngine` is constructed with
`warmup_bootstrap=True` and a single run is not representative on its own.

## Encoding

Every input is normalized into the range that the composite step function
accepts, and every column is normalized differently.

| Column | Handling |
|---|---|
| Coordinates | Projected to EPSG:5186 metres, divided by 884,592 |
| Speed | Divided by 200 km/h |
| Time offset | Divided by 5,000 ms |
| Phone number | Zero-padded to 11 digits, split 3/4/4, divided by 999 / 9,999 / 9,999 |

Coordinates are projected before encryption so the circuit is a plain Euclidean
distance. A latitude-dependent scale factor would have to travel in the clear
and would disclose roughly where the query centre lies.

A value of `-1` marks a field the log did not record. Unrecorded rows are
substituted before encryption with a value that lies outside every queried
region: a point far off the peninsula for coordinates, the prefix 999 for phone
numbers. The substitution is plaintext preprocessing, so it costs no homomorphic
operations, and it lets the answer for those rows be checked rather than
excluded.

## Data

Logs collected from vehicles operated by the authors.

| File | Vehicle | Rows |
|---|---|---|
| `k5_jellybean_drive.csv` | Kia K5, 2017, Android JellyBean | 613 |
| `k5_kitkat_drive.csv` | Kia K5 DL3, 2020, Android KitKat | 6,820 |
| `niro_call.csv` | Kia Niro, Bluetooth call history | 204 |
| `avante_accident.csv` | Hyundai Avante CN7, event data recorder | 16 |

Column names follow the notation used in the paper. Coordinates are stored as
integers scaled by 100,000, so 3731808 means 37.31808 degrees.

### Before public release

The call history carries subscriber and device identifiers. These must be
substituted before the datasets are published, and the substitution has to
preserve digit length and group structure so that the encoding and the reported
results stay valid. This is open at the time of writing.

## Attribution

`engine/`, `hedata/`, `operators/operator.py` and `operators/inv_sqrt.py` are
adapted from the PP-STAT implementation by Hyunmin Choi, itself ported from an
earlier Go implementation.

> H. Choi, "PP-STAT: An Efficient Privacy-Preserving Statistical Analysis
> Framework Using Homomorphic Encryption," CIKM '25, pp. 448-457.

`operators/forensic_operator.py` and everything under `experiments/` are new to
this work.

The homomorphic backend is the HEaaN SDK by CryptoLab.

## Citation

To be added on acceptance.
