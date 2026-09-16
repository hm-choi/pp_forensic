# Experiment 2 - Encrypted Phone Number Lookup

## Dataset

`datasets/niro_call.csv` - Bluetooth call history from a Kia Niro on an Android
JellyBean infotainment platform. 204 rows, 16 columns.

| Field | Rows with a value |
|---|---|
| Local timestamp and epoch milliseconds | 204 |
| Bluetooth profile identifier | 185 |
| Counterpart phone number | 19 |
| Call direction and call state | 14 |
| Paired device MAC address | 12 |

The 19 recorded numbers reduce to 4 distinct values, appearing 12, 3, 2 and 2
times. One begins with 006, an international prefix, rather than a domestic 01x
prefix. A value of -1 marks a field that was not recorded.

## Experiment

Answer "is there any record of a call with this number?" without decrypting the
call log, and without disclosing the number to the custodian. The output is a
single 0 or 1, so how many calls took place, when, and which record matched are
never revealed.

`he_step` takes an input between -1 and 1, so an 11-digit number cannot be fed in
directly.

- Zero-pad each number to 11 digits, recovering the leading zeros lost to integer
  storage.
- Split into groups of 3, 4 and 4 digits and divide by 999, 9999 and 9999.
- Per group, the requester encrypts the two interval bounds and the custodian
  builds an interval indicator with two `he_step` calls. Equality has to be
  expressed as interval membership because `he_step` reads only a sign.
- Multiply the three group indicators, so all three must match.
- Sum every slot under encryption and apply `he_step` once more, reducing the
  result to a single answer.

Rows with no number are given the prefix 999, which no real number uses.

`MARGIN = 0.5` is the half-width of the accepted interval in integer digit units,
so exactly one integer is accepted. It is applied before encryption, on the
requester side.

`detect_phone_exists(match_ctxt, max_count=C)` - C is an upper bound on the match
count that scales the `he_step` input into [-1,1]. It describes the protocol, not
the target, so it is declared in the clear and is not part of the encrypted query.
It must stay above the actual match count.

Taking the query numbers from the log is a convenience of the experiment. In the
protocol the requester supplies a number it already holds, and the custodian
never sees it either way.

## Results

Eleven queries: the four numbers in the log, one variant of each with the last
digit changed, two further variants of the most frequent number with a digit
changed in the first and middle group, and one number that never appears.

| Query | Description | Expected | Answer |
|---|---|---|---|
| 01020132924 | original | 1 | 1 |
| 01020132925 | last digit differs | 0 | 0 |
| 01065749080 | original | 1 | 1 |
| 01065749081 | last digit differs | 0 | 0 |
| 01026731582 | original | 1 | 1 |
| 01026731583 | last digit differs | 0 | 0 |
| 00687524858 | original | 1 | 1 |
| 00687524859 | last digit differs | 0 | 0 |
| 02020132924 | first group differs | 0 | 0 |
| 01020232924 | middle group differs | 0 | 0 |
| 01011112222 | not in the log | 0 | 0 |

All eleven agreed with the plaintext computation on every one of the 32,768
slots. Dividing a 4-digit group by 9999 spaces adjacent values 0.0001 apart while
`he_step` resolves to about 1e-8, so a single differing digit separates cleanly.

Step 7 re-runs only the existence circuit for C in {32, 256, 2048}, reusing the
match ciphertext, to check the answer holds as the declared bound grows.

## How to run

```bash
export PYTHONPATH=<repo root>
cd <repo root>/experiments/experiment2
python3 -W ignore -u test2.py
```

Console output is written to `results/result2.txt` automatically, so do not pipe
through `tee`.

## Output

| File | Contents |
|---|---|
| `results/result2.txt` | Console output |
| `results/exp2_niro_match_summary.csv` | Per query: expected and returned answer, existence value before thresholding, agreement, worst decrypted value on each side, elapsed times |
| `results/exp2_niro_maxcount_sweep.csv` | Existence bit over C in {32, 256, 2048} |
| `results/exp2_niro_slots.csv` | Per slot decrypted values |

The `plain` and `cipher` columns are a scoring aid, not part of the decision.