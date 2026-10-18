#!/usr/bin/env bash
# ==============================================================================
# CraftifAI PipeGen v0.5.1 - Smart Lab Safety Sentinel Demo Runner
# ==============================================================================

set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd "$DIR"

echo "=================================================================="
echo "   CRAFTIFAI PIPEGEN v0.5.1 - EDGE AI VISION SENTINEL RUNNER      "
echo "=================================================================="

# Activate virtual environment if present
if [ -f "$DIR/.venv/bin/activate" ]; then
    source "$DIR/.venv/bin/activate"
fi

echo "1. Validating PipeGen v0.5.1 End-to-End Pipeline Traceability Suite..."
python3 tests/test_e2e_traceability.py

echo ""
echo "2. Validating Pipeline IR Intermediate Representation (9 DAG Nodes)..."
python3 pipegen/cli.py ir validate

echo ""
echo "3. Profiling TensorRT Precision Benchmark (FP32, FP16, INT8 Quantization)..."
python3 pipegen/compile_tensorrt_engine.py pipegen

echo ""
echo "4. Checking Sentinel Mission Control Cockpit Server..."
if pgrep -f "http.server 8080" > /dev/null; then
    echo "[+] Mission Control Cockpit active at: http://localhost:8080/index.html"
else
    echo "[*] Launching Mission Control Cockpit on port 8080..."
    python3 -m http.server 8080 --directory web_sentinel_dashboard &
    echo "[+] Mission Control Cockpit running at: http://localhost:8080/index.html"
fi

echo ""
echo "=================================================================="
echo "   SUCCESS: PIPEGEN PIPELINE VERIFIED & COCKPIT READY             "
echo "=================================================================="
echo "To explore the interactive Mission Control Cockpit, open:"
echo "👉 http://localhost:8080/index.html"
echo ""
echo "To execute the real-time live camera perception pipeline:"
echo "👉 ./run.sh --camera 0"
echo "=================================================================="
