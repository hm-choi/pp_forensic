# Experiment 2 - Encrypted Phone Number Lookup

## Dataset

`datasets/niro_call.csv` - Bluetooth call history from a Kia Niro running an
Android JellyBean infotainment platform. 204 rows, 16 columns.

| Field | Rows with a value |
|---|---|
| Local timestamp and epoch milliseconds | 204 |
| Bluetooth profile identifier | 185 |
| `Peer_number`, the counterpart phone number | 19 |
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
call log and without disclosing the number being looked up. The output is a
single 0 or 1, so how many calls took place, when they took place, and which
record matched are never revealed.

`he_step` reads a sign and expects an input between -1 and 1, so an 11-digit
number cannot be fed in directly and equality cannot be asked for directly.

- Zero-pad each number to 11 digits, recovering the leading zeros lost by
  integer storage. A domestic 01x number loses one zero, an international 006
  prefix loses two.
- Split into groups of 3, 4 and 4 digits and divide by 999, 9999 and 9999.
- Per group, express equality as interval membership: two `he_step` calls give a
  narrow indicator around the target, with a half-width of 0.5 in integer digit
  units, so exactly one integer is accepted.
- Multiply the three group indicators, so all three must match to yield 1.
- Sum every slot under encryption and apply `he_step` once more, reducing the
  result to a single answer.

The interval bounds are encrypted under the requester's key, so the custodian
evaluates the lookup without learning the number.

Rows with no number are given the prefix 999, which no real number uses, so they
never match any target.

`detect_phone_exists(match_ctxt, max_count=C)` divides the slot sum by a public
constant C before the final step, so C is an upper bound on the match count that
the requester declares in advance. It describes the protocol rather than the
target, so it travels in the clear; only the interval bounds carry the queried
number. C must stay above the true match count.

The script runs two checks. The first evaluates eleven queries at C = 32 and
compares both the per-row match vector and the single answer bit against
plaintext. The second re-runs only the existence circuit at C values of 32, 256
and 2048, on the most frequent number in the log and on a number that never
appears, to confirm the answer does not depend on how generously the bound was
declared.

## Results

Eleven queries: the four numbers present in the log, one variant of each with
the last digit changed, two further variants of the most frequent number with a
digit changed in the first and middle group, and one number that never appears.

| Query | Description | Expected | Answer | Plain hits | Cipher hits | Agreement |
|---|---|---|---|---|---|---|
| 010-2013-2924 | original | 1 | 1 | 12 | 12 | 32768/32768 |
| 010-2013-2925 | last group differs | 0 | 0 | 0 | 0 | 32768/32768 |
| 010-6574-9080 | original | 1 | 1 | 3 | 3 | 32768/32768 |
| 010-6574-9081 | last group differs | 0 | 0 | 0 | 0 | 32768/32768 |
| 010-2673-1582 | original | 1 | 1 | 2 | 2 | 32768/32768 |
| 010-2673-1583 | last group differs | 0 | 0 | 0 | 0 | 32768/32768 |
| 006-8752-4858 | original | 1 | 1 | 2 | 2 | 32768/32768 |
| 006-8752-4859 | last group differs | 0 | 0 | 0 | 0 | 32768/32768 |
| 020-2013-2924 | first group differs | 0 | 0 | 0 | 0 | 32768/32768 |
| 010-2023-2924 | middle group differs | 0 | 0 | 0 | 0 | 32768/32768 |
| 010-1111-2222 | not in the log | 0 | 0 | 0 | 0 | 32768/32768 |

All eleven matched expectation and agreed with the plaintext computation on
every slot.

Which group a differing digit falls in decides how much separation the circuit
has to resolve. Dividing a 3-digit group by 999 spaces adjacent values about
1e-3 apart, while a 4-digit group divided by 9999 spaces them about 1e-4 apart.
The 4-digit groups are therefore the harder case, and the variants above cover
both.

The declared bound behaves the same way across two orders of magnitude.

| C | 010-2013-2924 (present) | 010-1111-2222 (absent) |
|---|---|---|
| 32 | 1 | 0 |
| 256 | 1 | 0 |
| 2048 | 1 | 0 |

All six calls returned the expected answer, so the requester can declare a bound
well above the true match count without changing the result.

### Cost

Mean of 30 runs.

| | Match circuit | Existence circuit |
|---|---|---|
| Step function calls | 6 | 1 |
| Explicit bootstraps | 27 | 4 |
| Chebyshev evaluations | 48 | 8 |
| Homomorphic time | 78.45 to 84.50 s | 12.05 to 12.87 s |
| Plaintext time | under 0.5 ms | |

Query parameter encryption takes about 0.12 s, higher than the other
experiments because three interval pairs are encrypted rather than a single
scalar.

The match circuit is the most expensive in this work. It runs six step functions
where the geofence runs one, and the time ratio between them tracks that count.

## How to run

```bash
export PYTHONPATH=/pp_forensic
cd /pp_forensic/experiments/experiment2
python3 -W ignore -u test.py
```

The script writes its own transcript, so no shell redirect is needed.

## Output

| File | Contents |
|---|---|
| `results/result2.txt` | Console output |
| `results/exp2_niro_match_summary.csv` | Per query: expected answer, returned answer, decrypted existence value, plaintext and ciphertext hit counts, agreement, match and existence timings, plaintext timing |
| `results/exp2_niro_maxcount_sweep.csv` | Per declared bound C: returned answer, whether it was correct, elapsed time |
| `results/exp2_niro_slots.csv` | Per-slot decrypted values for the sampled rows |
