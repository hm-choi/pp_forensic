#!/bin/bash
set -e
export PYTHONPATH=/pp_forensic

for d in experiment3 experiment1 experiment2; do
    echo ""
    echo "==================== $d ===================="
    date
    cd /pp_forensic/experiments/$d
    python3 -W ignore -u test.py
done

echo ""
echo "==================== done ===================="
date
