#!/usr/bin/env bash
N=${1:-10}
for i in $(seq -w 1 $N); do
  echo "########## RUN $i  $(date '+%F %T') ##########"
  docker exec heaan-geo bash -lc "export PYTHONPATH=/pp_forensic && \
    cd /pp_forensic/experiments/experiment1 && python3 test2.py && \
    cd ../experiment2 && python3 test2.py && \
    cd ../experiment3 && python3 test2.py" || { echo "RUN $i FAILED"; exit 1; }
  docker exec heaan-geo bash -lc "mkdir -p /pp_forensic/runs/run_$i && \
    cp /pp_forensic/experiments/experiment{1,2,3}/results/* /pp_forensic/runs/run_$i/ && \
    rm -rf /pp_forensic/experiments/experiment{1,2,3}/results"
  echo "saved to runs/run_$i"
done
echo "ALL DONE $(date '+%F %T')"
