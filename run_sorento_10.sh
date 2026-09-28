#!/usr/bin/env bash
N=${1:-10}
REPO=${2:-/workspace/pp_forensic}
for i in $(seq -w 1 $N); do
  echo "########## RUN $i  $(date '+%F %T') ##########"
  docker exec heaan-stat bash -lc "export PYTHONPATH=$REPO && \
    cd $REPO/experiments/experiment_multichunk_sorento && python3 -W ignore -u test2.py" \
    || { echo "RUN $i FAILED"; exit 1; }
  docker exec heaan-stat bash -lc "mkdir -p $REPO/runs_sorento/run_$i && \
    cp $REPO/experiments/experiment_multichunk_sorento/results/* $REPO/runs_sorento/run_$i/ && \
    rm -rf $REPO/experiments/experiment_multichunk_sorento/results"
  echo "saved to runs_sorento/run_$i"
done
echo "ALL DONE $(date '+%F %T')"
