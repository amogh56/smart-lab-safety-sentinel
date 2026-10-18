#!/usr/bin/env bash
# ==============================================================================
# CraftifAI PipeGen v0.5.1 - Official Pipeline Execution Script (run.sh)
# Target: NVIDIA Jetson Orin / Discrete Tensor Core GPU / Edge Vision Workstation
# ==============================================================================

set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd "$DIR"

echo "=================================================================="
echo "   CRAFTIFAI PIPEGEN v0.5.1 - RUNTIME DEPLOYMENT RUNNER           "
echo "=================================================================="

# Check if NVIDIA DeepStream is installed (NVIDIA Jetson / Linux GPU)
if command -v deepstream-app &> /dev/null && [ "$1" != "--python" ]; then
    echo "[+] NVIDIA DeepStream SDK detected: $(deepstream-app --version 2>&1 | head -n 1)"
    echo "[*] Launching DeepStream Application with PipeGen Config..."
    echo "[*] Config: pipegen/deepstream_app_config.txt"
    exec deepstream-app -c "$DIR/pipegen/deepstream_app_config.txt" "$@"
else
    # Development workstation / Python perception engine fallback
    echo "[*] DeepStream Native Binary not in PATH or Python execution selected."
    echo "[*] Launching PipeGen Hardware-Accelerated Perceptual Sentinel..."
    
    if [ -f "$DIR/.venv/bin/activate" ]; then
        source "$DIR/.venv/bin/activate"
    fi
    
    # Pass all incoming flags (e.g. --camera 0, --mock, --frames 300)
    exec python3 "$DIR/vision_sentinel/sentinel_vision.py" "$@"
fi
