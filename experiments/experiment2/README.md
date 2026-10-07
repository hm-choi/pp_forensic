# Experiment 2: Call History

Section 6.3 and Table 7 of the paper.

## Task

Check whether a given phone number appears in the call records of Niro, without disclosing the phonebook, the call history or the queried number. Niro is not enrolled in a connected service, so no server-side custodian exists; the call records left in the IVI are used as a proxy for custodian-held data. The investigator receives a single bit.

## Data

`datasets/niro_call.csv`: Kia Niro (2018), Jellybean (Android 4.2.2) IVI, 204 records. The counterpart number (`Phone_number`) is taken from the `+CLCC`, `+CLIP` and `RepoCallersInfo` lines of `trace_log`. 19 records carry a number, and they reduce to 4 distinct numbers occurring 12, 3, 2 and 2 times. One begins with 006 rather than 01x. No record carries a complete coordinate pair.

The numbers were substituted after the experiments (middle digit group only, one to one). As in the paper, the middle group is masked as `$$$$` below.

## Predicates

- **Phone-number match**, Eq. (4) on each digit group, `HEForensicTest.detect_phone_match`. Each number is zero-padded to 11 digits, split into digit groups of 3, 4 and 4, and divided by 999, 9,999 and 9,999. An interval of half-width 1/2 around the target accepts exactly one integer per group, and the three group decisions are multiplied. Six step calls, 27 Btsp. The interval bounds are encrypted by the investigator.
- **Existence circuit** (Section 4.4), `HEForensicTest.detect_phone_exists`. The match decisions are summed over all slots, shifted by 0.5, divided by the declared bound C, and passed through Eq. (1) once. One step call, 4 Btsp. C is a public upper bound on the expected number of matches; C = 32 for the main table.
- Rows without a number are substituted with the leading digit group 999, which no real number uses.

The queries are the four numbers in the log, one variant of each with the last digit changed, two variants of the most frequent number with one digit changed in the first and in the middle group, and one unrelated number. A one-digit difference amounts to about 1e-3 in the first group and about 1e-4 in the two trailing groups, so the trailing groups are the harder case.

## Results (A100, 30 runs)

For all eleven queries, the per-slot match decisions agreed with the plaintext baseline on all 32,768 slots and the existence bit was correct in every run. The existence value is the worst case over the 30 runs.

| Queried number | Differing group | Matches (rows) | Existence value | Decision | Btsp. | Time (s) |
| --- | --- | --- | --- | --- | --- | --- |
| `010-$$$$-2924` | Original | 12 | 0.9999999998 | Present | 31 | 3.35 |
| `010-$$$$-9080` | Original | 3 | 0.9999999997 | Present | 31 | 3.33 |
| `010-$$$$-1582` | Original | 2 | 0.9999999995 | Present | 31 | 3.33 |
| `006-$$$$-4858` | Original | 2 | 0.9999999996 | Present | 31 | 3.33 |
| `010-$$$$-2925` | Last | 0 | -7.5e-10 | Absent | 31 | 3.32 |
| `010-$$$$-9081` | Last | 0 | -5.0e-10 | Absent | 31 | 3.32 |
| `010-$$$$-1583` | Last | 0 | -5.9e-10 | Absent | 31 | 3.33 |
| `006-$$$$-4859` | Last | 0 | -5.4e-10 | Absent | 31 | 3.33 |
| `010-$$$$-2924`† | Middle | 0 | -4.4e-10 | Absent | 31 | 3.33 |
| `020-$$$$-2924` | First | 0 | -5.9e-10 | Absent | 31 | 3.33 |
| `010-$$$$-2222` | Unrelated | 0 | -4.6e-10 | Absent | 31 | 3.33 |

Table 7 of the paper shows eight of these rows. † Differs from the first row only inside the masked middle group.

The time is the match (2.87 to 2.89 s) plus the existence circuit (0.46 s). The per-slot match decisions carry a larger error than the existence bit, reaching 0.99999960 in the worst case for matching rows and 1.3e-7 for non-matching rows, because three digit-group decisions are multiplied with bootstrapping in between.

The decisions remain unchanged when C is set to 32, 256 and 2,048 (checked on `010-$$$$-2924` and `010-$$$$-2222` in every run), so the investigator may declare a bound two orders of magnitude above the actual number of matches.

Encrypting the query parameters takes 0.26 to 0.28 s, since three interval pairs are encrypted.

## Run

```
export PYTHONPATH=<repo root> HE_DEVICE=gpu
cd <repo root>/experiments/experiment2
python3 -W ignore -u test.py
```

## Output

Written to `results/` next to the script. The 30 A100 runs are in `results/runs/run_XX/` of the repository root.

| File | Contents |
| --- | --- |
| `result2.txt` | Console output |
| `exp2_niro_match_summary.csv` | Per query: expected and returned bit, existence value, plaintext and ciphertext match counts, agreement, worst per-slot values, match and existence times, Btsp. |
| `exp2_niro_maxcount_sweep.csv` | Per declared bound C: returned bit, correctness, time |
| `exp2_niro_slots.csv` | Decrypted match value of each of the 204 records for every query |
