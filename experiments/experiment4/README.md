# Experiment 4 - Encrypted Phone Number Lookup

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

`detect_phone_exists(match_ctxt, max_count=32)` - max_count is the expected upper
bound on the number of matches. It scales the he_step input into [-1,1], so it
must stay above the actual match count.

## Results

Eleven queries: the four numbers present in the log, one variant of each with the
last digit changed, two further variants of the most frequent number with a digit
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
| 01011112222 | not in log | 0 | 0 |

All eleven matched expectation and agreed with the plaintext computation on every
one of the 32,768 slots. Each query took 100 to 112 seconds.

Dividing a 4-digit group by 9999 spaces adjacent values 0.0001 apart, while
`he_step` resolves down to about 1.5e-8, so a single differing digit separates
cleanly.

## How to run

```bash
export PYTHONPATH=/pp_forensic
cd /pp_forensic/experiments/experiment4
python3 -W ignore -u test.py 2>&1 | tee result.txt
```

## Output

`result.txt` holds the console output. The `plain` and `cipher` columns are a
scoring aid, not part of the decision.
