# Experiment 3 - Encrypted Phone Number Lookup

## Dataset

`datasets/niro_call.csv` - Bluetooth call history from a Kia Niro running an
Android JellyBean infotainment platform. 204 rows, 16 columns.

| Field | Rows with a value |
|---|---|
| Local timestamp and epoch milliseconds | 204 |
| Bluetooth profile identifier | 185 |
| Counterpart phone number | 19 |
| Call direction and call state | 14 |
| Paired device MAC address | 12 |
| Handset and SIM identifiers (IMEI, ICCID) | 1 |
| Coordinates | 1 latitude, no longitude |

The 19 recorded numbers reduce to 4 distinct values, appearing 12, 3, 2 and 2
times. One begins with 006, an international-dialling prefix, rather than a
domestic 01x prefix. A value of -1 marks a field that was not recorded.

Location queries are not possible on this log, since no row carries a complete
coordinate pair.

## Experiment

Answer "is there any record of a call with this number?" without decrypting the
call log. The output is a single 0 or 1, so how many calls took place, when they
took place, and which record matched are never revealed.

`he_step` expects an input between -1 and 1, so an 11-digit number cannot be fed
in directly.

- Zero-pad each number to 11 digits, recovering the leading zeros lost by integer
  storage.
- Split into groups of 3, 4 and 4 digits and divide by 999, 9999 and 9999.
- Per group, build a narrow interval indicator with two `he_step` calls, since
  `he_step` reads only a sign and equality must be expressed as interval
  membership.
- Multiply the three group indicators, so all three must match to yield 1.
- Sum every slot under encryption and apply `he_step` once more, reducing the
  result to a single answer.

Rows with no number are given the prefix 999, which no real number uses, so they
never match any target.

`detect_phone_match(enc_segs, target_segs, denoms, margin=0.5)` - margin is the
half-width of the accepted interval in integer units, so 0.5 matches exactly one
integer.

`detect_phone_exists(match_ctxt, max_count=32)` - max_count is the upper bound on
the number of matches that the requester declares in advance. It scales the
`he_step` input into [-1,1], so it must stay above the actual match count.

The script runs two checks. The first evaluates eleven queries at
`max_count = 32` and compares both the per-row match vector and the single answer
bit against plaintext. The second re-runs only the existence circuit at
`max_count` values of 32, 256 and 2048, on the most frequent number in the log
and on a number that never appears, to confirm the answer does not depend on how
generously the bound was declared.

## Results

Eleven queries: the four numbers present in the log, one variant of each with the
last digit changed, two further variants of the most frequent number with a digit
changed in the first and middle group, and one number that never appears.

| Query | Description | Expected | Answer | Plain hits | Cipher hits | Agreement |
|---|---|---|---|---|---|---|
| 01020132924 | original | 1 | 1 | 12 | 12 | 32768/32768 |
| 01020132925 | last digit differs | 0 | 0 | 0 | 0 | 32768/32768 |
| 01065749080 | original | 1 | 1 | 3 | 3 | 32768/32768 |
| 01065749081 | last digit differs | 0 | 0 | 0 | 0 | 32768/32768 |
| 01026731582 | original | 1 | 1 | 2 | 2 | 32768/32768 |
| 01026731583 | last digit differs | 0 | 0 | 0 | 0 | 32768/32768 |
| 00687524858 | original | 1 | 1 | 2 | 2 | 32768/32768 |
| 00687524859 | last digit differs | 0 | 0 | 0 | 0 | 32768/32768 |
| 02020132924 | first group differs | 0 | 0 | 0 | 0 | 32768/32768 |
| 01020232924 | middle group differs | 0 | 0 | 0 | 0 | 32768/32768 |
| 01011112222 | not in log | 0 | 0 | 0 | 0 | 32768/32768 |

All eleven matched expectation and agreed with the plaintext computation on every
slot. The match circuit took 76.15 to 84.84 seconds and the existence circuit
12.07 to 12.95 seconds, against 0.162 to 0.538 milliseconds on plaintext.

Dividing a 4-digit group by 9999 spaces adjacent values 0.0001 apart, so a single
differing digit separates cleanly.

The declared bound behaves the same way across two orders of magnitude.

| max_count | 01020132924 (present) | 01011112222 (absent) | Existence time |
|---|---|---|---|
| 32 | 1 | 0 | 12.84 s / 11.99 s |
| 256 | 1 | 0 | 12.95 s / 11.81 s |
| 2048 | 1 | 0 | 13.89 s / 11.75 s |

All six calls returned the expected answer, so the requester can declare a bound
well above the true match count without changing the result.

## How to run

```bash
export PYTHONPATH=/pp_forensic
cd /pp_forensic/experiments/experiment3
python3 -W ignore -u test2.py
```

The script writes its own transcript, so no shell redirect is needed.

## Output

| File | Contents |
|---|---|
| `results/result2.txt` | Console output |
| `results/exp3_niro_match_summary.csv` | Per query: expected answer, returned answer, plaintext and ciphertext hit counts, agreement, match and existence timings, plaintext timing |
| `results/exp3_niro_maxcount_sweep.csv` | Per bound: returned answer, whether it was correct, elapsed time |
