# PP-Forensics

Privacy-preserving forensic analytics over vehicle software platform logs, built on CKKS homomorphic encryption.

An investigator asks a question about a vehicle log that a custodian holds. The custodian evaluates the question on ciphertext and returns a single bit. The custodian never learns what was asked, and the investigator never receives the log. Query parameters are encrypted under the investigator's key, so a warrant's location, threshold, time window or phone number stays hidden as well.

This repository holds the homomorphic-encryption half of the work: the predicate circuits, the experiments that validate them, and the measurement harness.

## Layout

```
engine/        HEaaN context, key management, bootstrapping
hedata/        Container holding one or more CKKS ciphertexts
operators/     Homomorphic operators, composite sign and step function,
               forensic predicates, bootstrapping counters
datasets/      Vehicle logs used by the experiments
experiments/   One folder per experiment
colab/         Scripts for the GPU runs on a Colab A100 (udocker)
tools/         Post-processing of the GPU runs
```

`operators/forensic_operator.py` is the entry point. Every predicate the experiments evaluate goes through it.

## Experiments

| Folder | Subject | Data |
| --- | --- | --- |
| `experiment1` | Radius predicate on GPS coordinates | Kia K5 infotainment, two platform versions |
| `experiment2` | Phone-number match and existence | Kia Niro Bluetooth call history |
| `experiment3` | Speed increase, speed threshold, time window | Hyundai Avante CN7 event data recorder |
| `experiment_scaling` | Runtime by number of ciphertexts (1, 2, 4, 8, 32; up to 1,048,576 rows) | Data of Experiments 1 to 3, tiled |

Experiments 1 to 3 each have their own README.

## Predicates

| Predicate | Column | Step calls | Bootstraps | Chebyshev evaluations |
| --- | --- | --- | --- | --- |
| Radius | `Lat_x1e5`, `Lon_x1e5` | 1 | 4 | 8 |
| Phone-number match | `Peer_number` | 6 | 27 | 48 |
| Existence (one-bit response) | match ciphertext | 1 | 4 | 8 |
| Speed increase | `Speed_kmh` | 1 | 4 | 8 |
| Speed threshold | `Speed_kmh` | 1 | 4 | 8 |
| Time window | `T_rel_ms` | 2 | 8 | 16 |

Counts are per ciphertext. Bootstraps counts the calls this framework issues explicitly. The Chebyshev evaluation routine bootstraps further on its own, which the SDK manages and which is not counted here.

Runtime follows the bootstrap count rather than the kind of predicate. In the runs of Experiments 1 to 3, measured time divided by bootstrap count is about 0.11 seconds on the GPU and between 2.9 and 3.6 seconds (about 3.2 on average) on the CPU (machines below). Phone-number matching is slow because it runs six step functions, not because matching a number is intrinsically harder than drawing a circle.

When the data spans several ciphertexts, every predicate runs once per ciphertext, so runtime grows linearly with the number of ciphertexts, about 0.44 seconds per ciphertext for each step call on the GPU (11 to 13 seconds on the CPU). The existence circuit is the exception: it sums all ciphertexts first and then runs once, so its cost does not grow with their number.

## Results at a glance

Mean of 30 runs. Every query agreed with the plaintext computation on every scored slot, on both machines.

| Circuit | Bootstraps | GPU (A100) | CPU |
| --- | --- | --- | --- |
| Radius (Experiment 1) | 4 | 0.44 to 0.46 s | 12.62 to 14.27 s |
| Phone-number match + existence (Experiment 2) | 31 | 3.32 to 3.35 s | about 90 to 97 s |
| Speed increase (Experiment 3) | 4 | 0.45 s | 14.33 s |
| Speed threshold (Experiment 3) | 4 | 0.43 s | 13.34 s |
| Time window (Experiment 3) | 8 | 0.88 s | 26.01 s |

The paper reports the GPU figures. The CPU figures are kept in the per-experiment READMEs for comparison.

Scaling (`experiment_scaling`, GPU, mean of 30 timed runs per point):

| Ciphertexts | Rows | Radius | Speed threshold | Time window | Phone match + existence |
| --- | --- | --- | --- | --- | --- |
| 1 | 32,768 | 0.45 s | 0.44 s | 0.89 s | 3.35 s |
| 2 | 65,536 | 0.89 s | 0.89 s | 1.78 s | 6.24 s |
| 4 | 131,072 | 1.79 s | 1.78 s | 3.55 s | 12.04 s |
| 8 | 262,144 | 3.58 s | 3.55 s | 7.11 s | 23.63 s |
| 32 | 1,048,576 | 14.21 s | 14.11 s | 28.25 s | 92.60 s |

R^2 is 1.0000 for every predicate. A line fitted on 1 to 8 ciphertexts predicts the 32-ciphertext time within 0.7%.

## Requirements

- CryptoLab HEaaN SDK, GPU or CPU build, FGb parameter set
- Python 3.10, numpy, pandas
- A key directory the engine can read and write

The experiments run inside the vendor Docker image.

| | GPU (reported in the paper) | CPU |
| --- | --- | --- |
| Image | `cryptolabinc/heaan-stat:1.0.0-gpu` | CPU image of the same SDK |
| Machine | Google Colab, NVIDIA A100-SXM4-80GB | Intel Xeon Sapphire Rapids, 16 vCPU, 64 GB RAM |
| Selected by | `HE_DEVICE=gpu` | `HE_DEVICE` unset or `cpu` (default) |

Colab has no Docker daemon, so the GPU image is run with udocker. `colab/` holds the setup and run scripts; see `colab/README.md`.

## Running

Each experiment runs from its own folder.

```
export PYTHONPATH=<repo root>
export HE_DEVICE=gpu            # omit for the CPU build
cd <repo root>/experiments/experiment1
python3 -W ignore -u test.py
```

With `HE_DEVICE=gpu`, `HEEngine` creates the context on the GPU, loads every key file from the key directory and moves the keys to the device; plaintext messages and rotation masks are moved there before use. Nothing else in the circuits changes between the two builds.

Results land in `results/` next to the script. The script installs its own console tee, so the transcript is written for you and no shell redirect is needed.

Reported figures are the mean of 30 repetitions. The first bootstrapping call of a process is slower than the rest, so `HEEngine` is constructed with `warmup_bootstrap=True` and a single run is not representative on its own.

The scaling experiment is run the same way, then summarized:

```
cd <repo root>/experiments/experiment_scaling
python3 -W ignore -u bench.py > bench.log 2>&1
python3 bench_summary.py
```

`bench.py` reads `PREDS` (default `geo,edr,phone`), `MULTIPLES` (default `1,2,4,8,32`), `REPS` (default `30`) and `PHONE_C` (default `65536`) from the environment. `PHONE_C` is the public bound on the match count used by the existence circuit; tiling multiplies the matches (61,680 at 32 ciphertexts), so it must exceed that. The earlier CPU run used `MULTIPLES=1,2,3,4,5` and `PHONE_C=16384`. Each point is checked against plaintext on every row before it is timed. Times are appended to `results/bench_times.csv`, and `bench_summary.py` writes `results/bench_summary.csv` with a linear fit per predicate. This script does not tee its output, so redirect it as above.

## Encoding

Every input is normalized into the range that the composite step function accepts, and every column is normalized differently.

| Column | Handling |
| --- | --- |
| Coordinates | Projected to EPSG:5186 meters, divided by 884,592 |
| Speed | Divided by 200 km/h |
| Time offset | Divided by 5,000 ms |
| Phone number | Zero-padded to 11 digits, split 3/4/4, divided by 999 / 9,999 / 9,999 |

Coordinates are projected before encryption so the circuit is a plain Euclidean distance. A latitude-dependent scale factor would have to travel in the clear and would disclose roughly where the query center lies.

A value of -1 marks a field the log did not record. Unrecorded rows are substituted before encryption with a value chosen independently of any query: for coordinates, a fixed point more than 500 km from every recorded location; for phone numbers, the prefix 999, which no real number uses. The substitution is plaintext preprocessing, so it costs no homomorphic operations, and it lets the answer for those rows be checked rather than excluded.

## Data

Logs collected from vehicles operated by the authors.

| File | Vehicle | Rows |
| --- | --- | --- |
| `k5_jellybean_drive.csv` | Kia K5 JF, 2017, Android Jellybean | 613 |
| `k5_kitkat_drive.csv` | Kia K5 DL3, 2020, Android KitKat | 6,820 |
| `niro_call.csv` | Kia Niro, Bluetooth call history | 204 |
| `avante_accident.csv` | Hyundai Avante CN7, event data recorder | 16 |

Column names follow the notation used in the paper. Coordinates are stored as integers scaled by 100,000, so 3731808 means 37.31808 degrees.

## Identifier substitution

Subscriber and device identifiers in `niro_call.csv` (phone numbers, Bluetooth MAC address, IMEI, ICCID) and its single location fix were substituted after the experiments were run. Each phone number keeps its first and last digit groups, and only the middle group is replaced, one-to-one, so every match count and every decision in Experiment 2 is unchanged. Rerunning Experiment 2 on the substituted data can change the decrypted values only in their last digits. The other identifiers and the location fix are not used by any experiment.

## Attribution

`engine/`, `hedata/`, `operators/operator.py` and `operators/inv_sqrt.py` are adapted from the PP-STAT implementation by Hyunmin Choi, itself ported from an earlier Go implementation.

> H. Choi, "PP-STAT: An Efficient Privacy-Preserving Statistical Analysis Framework Using Homomorphic Encryption," CIKM '25, pp. 448-457.

`operators/forensic_operator.py` and everything under `experiments/` are new to this work.

The homomorphic backend is the HEaaN SDK by CryptoLab.

## Citation

To be added on acceptance.
