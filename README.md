# PP-Forensics

Implementation and experiment results of *PP-Forensics: Privacy-Preserving Forensic Analytics Framework for Heterogeneous Vehicle Software Platforms* (ACM SAC 2027).

An investigator asks a custodian, a third party that holds vehicle logs in plaintext, whether any record satisfies a forensic predicate. The custodian converts its records into a feature matrix, encrypts it under the investigator's public key, and evaluates the predicate over ciphertexts. The query parameters (a phone number, a center and a radius, a speed threshold, or the two ends of a time window) also arrive encrypted. The investigator decrypts a single bit, and the custodian learns neither the decision nor the query parameters.

## Layout

```
engine/        HEaaN context, keys and bootstrapping
hedata/        Container for one or more CKKS ciphertexts
operators/     Homomorphic operators, step function, forensic predicates,
               bootstrapping counter
datasets/      Feature matrices of the four vehicles
experiments/   experiment1 to experiment4, one folder per experiment
colab/         Scripts that ran all experiments on the A100
tools/         Post-processing of the A100 runs
results/       A100 results reported in the paper
aggregate.py   Aggregates the 30 runs of Experiments 1 to 3
```

## Experiments

| Folder | Section of the paper | Predicates | Data |
| --- | --- | --- | --- |
| `experiment1` | 6.2 Experiment 1: Location History (Table 6) | Radius | K5 JF (2017), K5 DL3 (2020) |
| `experiment2` | 6.3 Experiment 2: Call History (Table 7) | Phone-number match, existence circuit | Niro (2018) |
| `experiment3` | 6.4 Experiment 3: Speeding and Acceleration (Table 8) | Speed increase, speed threshold, time window | Avante CN7 (2021), EDR |
| `experiment4` | 6.5 Experiment 4: Scalability (Table 9) | Radius, speed threshold, time window, phone-number match | Data of Experiments 1 to 3, tiled to 1 to 32 ciphertexts |

Each folder has its own README with the setting and the results.

## Predicates

All five predicates are built from the step function of Eq. (1), a composite polynomial approximation of the sign function with 8 stages and a multiplicative depth of 32. Btsp. denotes the number of bootstrapping operations per ciphertext.

| Predicate | Input column | Step calls | Btsp. | Function in `operators/forensic_operator.py` |
| --- | --- | --- | --- | --- |
| Radius, Eq. (3) | `Lat_x1e5`, `Lon_x1e5` | 1 | 4 | `compute_geofence_score` |
| Phone-number match, Eq. (4) on three digit groups | `Phone_number` | 6 | 27 | `detect_phone_match` |
| Existence circuit (one-bit response) | match decisions | 1 | 4 | `detect_phone_exists` |
| Time window, Eq. (4) | `T_rel_ms` | 2 | 8 | `time_range` |
| Speed increase, Eq. (1) on adjacent slots | `Speed_kmh` | 1 | 4 | `detect_speed_increase` |
| Speed threshold, Eq. (1) | `Speed_kmh` | 1 | 4 | `detect_overspeed` |

The cost of a query is set by the number of step calls: about 0.11 s per bootstrapping operation on the A100.

## Datasets

| File | Vehicle | Records | Experiment |
| --- | --- | --- | --- |
| `k5_jellybean_drive.csv` | Kia K5 JF (2017), Jellybean (Android 4.2.2) IVI | 613, of which 330 carry a GPS fix | 1 |
| `k5_kitkat_drive.csv` | Kia K5 DL3 (2020), KitKat (Android 4.4.2) IVI | 6,820, of which 246 carry a GPS fix | 1 |
| `niro_call.csv` | Kia Niro (2018), Jellybean IVI | 204, of which 19 carry a phone number | 2 |
| `avante_accident.csv` | Hyundai Avante CN7 (2021), EDR report | 16 rows, of which 11 are pre-crash speed samples | 3 |

Column names follow the paper. A value of -1 marks an unobserved field. Coordinates are integers scaled by 10^5 (3731808 is 37.31808 degrees). `T_rel_ms` is the offset from the reference time T0.

The phone numbers, Bluetooth MAC address, IMEI, ICCID and the single location fix in `niro_call.csv` were substituted after the experiments. Each phone number keeps its first and last digit groups, and only the middle group is replaced, one to one, so every match count and every decision of Experiment 2 is unchanged.

## Encoding (Section 5.4)

Every input is divided by a public constant S so that it lies in [-1, 1].

| Column | Encoding |
| --- | --- |
| `Lat_x1e5`, `Lon_x1e5` | Projected to EPSG:5186 meters, divided by the normalization width L = 884,592 m |
| `Speed_kmh` | Divided by 200 |
| `T_rel_ms` | Divided by 5,000, the maximum width of the time window |
| `Phone_number` | Zero-padded to 11 digits, split into digit groups of 3, 4 and 4, divided by 999, 9,999 and 9,999 |

Unobserved fields are substituted before encryption with values fixed independently of any query: coordinates with a point more than 500 km from every recorded location, and phone numbers with the leading digit group 999, which no real number uses. Time and speed are left as they are.

## Environment

| | |
| --- | --- |
| HE library | CryptoLab HEaaN SDK, GPU distribution, FGb parameter set (32,768 slots) |
| Image | `cryptolabinc/heaan-stat:1.0.0-gpu` |
| Machine | Google Colab instance, NVIDIA A100-SXM4 GPU with 80 GB of memory |
| Python | 3.10, numpy, pandas |

Colab has no Docker daemon, so the image is run with udocker.

```
bash colab/setup_udocker.sh                          # once per runtime, ends with SANITY OK
nohup bash colab/run_a100.sh > run_a100.out 2>&1 &   # all experiments, results to Google Drive
```

`run_a100.sh` runs Experiments 1 to 3 in 30 separate processes and Experiment 4 at 1, 2, 4, 8 and 32 ciphertexts with 30 timed runs per point, then aggregates the results. The whole run took about 3 hours 10 minutes, and the folder it writes is what `results/` holds.

To run a single experiment inside the container:

```
export PYTHONPATH=<repo root> HE_DEVICE=gpu
cd <repo root>/experiments/experiment1
python3 -W ignore -u test.py
```

With `HE_DEVICE=gpu`, `HEEngine` creates the context on the GPU and moves the keys there. The same code runs on the CPU distribution of HEaaN when `HE_DEVICE` is not set.

## Results

All runtimes are means over 30 runs on the A100. Every query agreed with the plaintext decision on every scored slot. The plaintext baselines take a median of 0.126 ms per query.

| Experiment | Queries | Btsp. | Time (s) | Query encryption (s) |
| --- | --- | --- | --- | --- |
| 1: radius | 12 | 4 | 0.44 to 0.46 | 0.04 to 0.05 |
| 2: phone-number match and existence circuit | 11 | 31 | 3.32 to 3.35 | 0.26 to 0.28 |
| 3: speed increase, speed threshold, time window | 3 | 4, 4, 8 | 0.45, 0.43, 0.88 | 0.13 |

Experiment 4, time (s) by the number of ciphertexts with Btsp. in parentheses (Table 9):

| Ciphertexts | Rows | Radius | Speed threshold | Time window | Phone-number match |
| --- | --- | --- | --- | --- | --- |
| 1 | 32,768 | 0.45 (4) | 0.44 (4) | 0.89 (8) | 3.35 (31) |
| 2 | 65,536 | 0.89 (8) | 0.89 (8) | 1.78 (16) | 6.24 (58) |
| 4 | 131,072 | 1.79 (16) | 1.78 (16) | 3.55 (32) | 12.04 (112) |
| 8 | 262,144 | 3.58 (32) | 3.55 (32) | 7.11 (64) | 23.63 (220) |
| 32 | 1,048,576 | 14.21 (128) | 14.11 (128) | 28.25 (256) | 92.60 (868) |

The runtime grows linearly with the number of ciphertexts (R^2 >= 0.9999), adding about 0.44 s per ciphertext for each step call.

### Result files

| Path | Contents |
| --- | --- |
| `results/runs/run_01` to `run_30` | Output of Experiments 1 to 3 for each of the 30 runs |
| `results/aggregated/` | `aggregate.py` over the 30 runs: mean times and worst-case decision values |
| `results/paper_numbers.txt` | The numbers of Tables 6 to 8 and Section 6, from `tools/extract_gpu.py` |
| `results/experiment4/` | Every timed run of Experiment 4, its summary and the linear fit (Table 9) |
| `results/logs/` | Console log of each run, `main.log`, and `gpu_monitor.csv` (GPU clock and throttle reasons every 10 s, timestamps in UTC) |

## Attribution

`engine/`, `hedata/`, `operators/operator.py` and `operators/inv_sqrt.py` are adapted from the PP-STAT implementation, which also provides the Chebyshev coefficients of the step function. `operators/forensic_operator.py` and everything under `experiments/` are new to this work. The homomorphic encryption backend is the HEaaN SDK by CryptoLab.

> H. Choi, "PP-STAT: An Efficient Privacy-Preserving Statistical Analysis Framework Using Homomorphic Encryption," CIKM '25, pp. 448-457.
