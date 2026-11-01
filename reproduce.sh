#!/bin/bash
# Full pipeline from scratch on an Apple-silicon Mac. data/ already holds every intermediate file,
# so to recompute only the tables and figures, run the analysis steps at the end.
set -e
cd "$(dirname "$0")"
python harness/memguard.py &   # optional safety net: kills runaway experiment processes if memory runs low
GUARD=$!
trap "kill $GUARD 2>/dev/null" EXIT
python scripts/00_validate_harness.py   # every reference solution must pass its own tests (about 20 s)
python scripts/01_generate.py 16        # 16 samples per problem from Qwen2.5-Coder-1.5B-Instruct (about 25 min)
python scripts/02_execute.py            # run every unique sample on the hidden tests in a sandbox (about 10 min)
python scripts/03_build_cheats.py      # plant and execution-check the cheats (CPU, about 2 min)
python scripts/04_monitor.py score A   # monitor A, Qwen2.5-7B-Instruct (about 35 min)
python scripts/04_monitor.py score B   # monitor B, Llama-3.1-8B-Instruct (about 50 min)
python scripts/04_monitor.py analyze
python scripts/05_ensemble.py
python scripts/04_monitor.py disguise  # greedy execution-checked disguise search against monitor A (about 30 min)
python scripts/04_monitor.py transfer  # score the final disguises with monitor B (about 5 min)
python scripts/06_analyze_disguise.py
