#!/usr/bin/env bash
# Run all errata checks. Needs: iverilog and the project .venv (cocotb 2.0.1, pytest).
#   source .venv/bin/activate && cd docs/errata/test && ./run_checks.sh
set -e
cd "$(dirname "$0")"

python -m pytest -q test_host.py
for variant in fixed unbiased submitted regression; do
    echo "=== VARIANT=$variant"
    make VARIANT=$variant
done
echo "All errata checks passed."
