#!/bin/bash
export PATH="$HOME/.local/bin:$PATH"
cd "$(dirname "$0")"
make clean
make 2>&1
echo "MAKE_EXIT_CODE=$?"
echo "---RESULTS---"
cat results.xml 2>/dev/null || echo "NO RESULTS FILE"
