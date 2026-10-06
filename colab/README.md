# GPU runs on Google Colab

The GPU figures in the paper were measured on a Colab runtime with an NVIDIA
A100-SXM4-80GB. Colab has no Docker daemon, so the vendor GPU image
`cryptolabinc/heaan-stat:1.0.0-gpu` is run with [udocker](https://github.com/indigo-dc/udocker),
which needs neither root privileges on the host nor a daemon.

The image is built against CUDA 11.8. It ran on the A100; the Blackwell GPUs
Colab also offers (RTX PRO 6000) are not supported by that build.

## Steps

1. Select an A100 runtime and mount Google Drive, where all results are written.
2. Get the code.

```bash
   cd /content && git clone -b dhkim <repository URL> pp_forensic
   cd pp_forensic
```

3. Set up udocker, the image and the container once per runtime. The script ends
   with a small GPU computation that must print `SANITY OK`.

```bash
   bash colab/setup_udocker.sh
```

4. Start the runs in the background. The script resumes: if the runtime is
   interrupted, starting it again skips what is already in Drive.

```bash
   nohup bash colab/run_a100.sh > /content/drive/MyDrive/run_a100.out 2>&1 &
   tail -f /content/drive/MyDrive/run_a100.out
```

5. Disconnect and delete the runtime when `ALL DONE` appears, since an idle
   runtime keeps using compute units.

## What runs

| Part | Protocol | Time on the A100 |
| --- | --- | --- |
| Experiments 1 to 3 | 30 separate processes | about 76 min |
| Experiment 4, 1/2/4/8 ciphertexts | one process, warm-up then 30 timed runs per point | about 38 min |
| Experiment 4, 32 ciphertexts | one process, warm-up then 30 timed runs per point | about 78 min |

Inside the container `HE_DEVICE=gpu` is set, so the same scripts as on the CPU
are used. `PHONE_C=65536` keeps the existence bound above the 61,680 matches of
the 32-ciphertext log.

## Output (in `/content/drive/MyDrive/pp_forensic_a100`)

| Path | Contents |
| --- | --- |
| `runs/run_01` to `run_30` | Results of Experiments 1 to 3 for each run |
| `aggregated/` | `aggregate.py` over the 30 runs |
| `paper_numbers.txt` | Worst-case decrypted values and mean times, from `tools/extract_gpu.py` |
| `exp4/bench_times_small.csv`, `bench_times_big.csv` | Every timed run of Experiment 4 |
| `exp4/bench_summary.txt` | Mean per point and linear fit, from `bench_summary.py` |
| `exp4/scale_check.txt` | Fit on 1 to 8 ciphertexts, checked against 32, from `tools/scale_check.py` |
| `logs/` | Per-run logs, `main.log`, and `gpu_monitor.csv` (every 10 s, timestamps in UTC) |

`gpu_monitor.csv` records the SM clock and the active clock-event reasons. A
value of `0x0000000000000000` throughout means the GPU was never throttled.

## Troubleshooting

- `manifest not found` or a skipped setup after an interrupted pull: list the
  containers with `udocker --allow-root ps`, remove the unnamed ones with
  `udocker --allow-root rm <id>`, and run `setup_udocker.sh` again.
- `nvidia-smi` is not available inside the container; check the GPU on the host.
  The sanity test is the check that HEaaN reaches the GPU.
