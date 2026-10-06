#!/usr/bin/env bash
# Runs Experiments 1 to 4 of the paper on a Colab A100 via udocker. Re-running resumes: finished parts are skipped.
#   Exp 1-3 : N fresh processes (default 30)
#   Exp 4   : one process per batch (1,2,4,8 and 32 ciphertexts), warm-up then REPS timed runs per point
# env: N=30 REPS=30 REPS32=30 MULTIPLES=1,2,4,8 BIG=32 PHONE_C=65536 D=<drive dir>
# usage (Colab, after colab/setup_udocker.sh and mounting Drive):
#   cd /content/pp_forensic && nohup bash colab/run_a100.sh > /content/drive/MyDrive/run_a100.out 2>&1 &
# outputs in $D: runs/run_XX (Exp 1-3), experiment4/ (bench times, summary, scale_check.txt),
#   aggregated/, paper_numbers.txt, logs/ (per-run logs, main.log, gpu_monitor.csv in UTC)
R=/content/pp_forensic
D=${D:-/content/drive/MyDrive/pp_forensic_a100}
N=${N:-30}; REPS=${REPS:-30}; REPS32=${REPS32:-$REPS}
MULTIPLES=${MULTIPLES:-1,2,4,8}; BIG=${BIG:-32}; PHONE_C=${PHONE_C:-65536}
mkdir -p "$D/logs" "$D/runs" "$D/experiment4"
U() { udocker --allow-root run --volume=/content:/content \
        --env=PYTHONPATH=$R --env=HE_DEVICE=gpu --env=PHONE_C=$PHONE_C \
        --entrypoint=bash heaan -c "$1"; }
log() { echo "[$(TZ=Asia/Seoul date '+%F %T KST')] $*" | tee -a "$D/logs/main.log"; }

nvidia-smi --query-gpu=timestamp,utilization.gpu,memory.used,temperature.gpu,clocks.sm,power.draw,clocks_event_reasons.active \
  --format=csv -l 10 >> "$D/logs/gpu_monitor.csv" &
MON=$!
trap 'kill $MON 2>/dev/null' EXIT
log "start  N=$N REPS=$REPS MULTIPLES=$MULTIPLES BIG=$BIG REPS32=$REPS32 PHONE_C=$PHONE_C  commit $(git -C $R log -1 --format=%h)"

for i in $(seq -w 1 "$N"); do
  [ -d "$D/runs/run_$i" ] && continue
  rm -rf $R/experiments/experiment{1,2,3}/results
  if U "cd $R/experiments/experiment1 && python3 -W ignore -u test.py && \
        cd ../experiment2 && python3 -W ignore -u test.py && \
        cd ../experiment3 && python3 -W ignore -u test.py" > "$D/logs/run_$i.log" 2>&1; then
    mkdir -p "$D/runs/run_$i" && cp $R/experiments/experiment{1,2,3}/results/* "$D/runs/run_$i/"
    log "RUN $i saved  $(grep -h 'mismatched' "$D/logs/run_$i.log" | tr -s ' \n' ' ')"
  else
    log "RUN $i FAILED, see logs/run_$i.log"
  fi
done

S=$R/experiments/experiment4
bench() {
  [ -f "$D/experiment4/bench_times_$1.csv" ] && return
  rm -rf $S/results
  log "EXP4 $1 start (multiples $2, reps $3)"
  if U "cd $S && MULTIPLES=$2 REPS=$3 python3 -W ignore -u bench.py" > "$D/logs/exp4_$1.log" 2>&1 \
     && [ -f $S/results/bench_times.csv ]; then
    cp $S/results/bench_times.csv "$D/experiment4/bench_times_$1.csv"
    log "EXP4 $1 done  $(grep -c '^OK' "$D/logs/exp4_$1.log") OK / $(grep -c '^X ' "$D/logs/exp4_$1.log") X"
  else
    log "EXP4 $1 FAILED, see logs/exp4_$1.log"
  fi
}
bench small "$MULTIPLES" "$REPS"
bench big "$BIG" "$REPS32"

if [ -f "$D/experiment4/bench_times_small.csv" ] && [ -f "$D/experiment4/bench_times_big.csv" ]; then
  mkdir -p $S/results
  python3 - "$D/experiment4" "$S/results/bench_times.csv" <<'PY'
import sys, pandas as pd
d = sys.argv[1]
pd.concat([pd.read_csv(f'{d}/bench_times_small.csv'), pd.read_csv(f'{d}/bench_times_big.csv')]).to_csv(sys.argv[2], index=False)
PY
  U "cd $S && python3 bench_summary.py" > "$D/experiment4/bench_summary.txt" 2>&1
  cp $S/results/bench_summary.csv "$D/experiment4/" 2>/dev/null
  python3 $R/tools/scale_check.py "$S/results/bench_times.csv" "$BIG" > "$D/experiment4/scale_check.txt" 2>&1
fi
rm -rf $R/runs && cp -r "$D/runs" $R/runs
U "cd $R && python3 aggregate.py" > "$D/logs/aggregate.txt" 2>&1
rm -rf "$D/aggregated" && cp -r $R/aggregated "$D/" 2>/dev/null
python3 $R/tools/extract_gpu.py "$D/runs" > "$D/paper_numbers.txt" 2>&1
log "ALL DONE  runs $(ls -d "$D"/runs/run_* 2>/dev/null | wc -l)/$N   results in $D"
