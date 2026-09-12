#!/bin/bash
# Double-click launcher: sets up (first run only) and starts the
# Echosounder Bathymetry tool in a dedicated conda environment, then opens
# it in your browser. See README.md for what this does and how to fix it
# if double-clicking doesn't work the first time (macOS Gatekeeper).
set -e
cd "$(dirname "$0")"

ENV_NAME="seastrong-echosounder"

echo "Looking for a conda installation..."
CONDA_BASE=""
if command -v conda >/dev/null 2>&1; then
    CONDA_BASE="$(conda info --base)"
else
    for candidate in "$HOME/anaconda3" "$HOME/opt/anaconda3" "$HOME/miniconda3" "$HOME/miniforge3" "/opt/anaconda3" "/opt/miniconda3" "/opt/homebrew/anaconda3" "/opt/homebrew/Caskroom/miniconda/base"; do
        if [ -f "$candidate/etc/profile.d/conda.sh" ]; then
            CONDA_BASE="$candidate"
            break
        fi
    done
fi

if [ -z "$CONDA_BASE" ] || [ ! -f "$CONDA_BASE/etc/profile.d/conda.sh" ]; then
    echo ""
    echo "Could not find an Anaconda/Miniconda installation."
    echo "Install Anaconda from https://www.anaconda.com/download, then try again."
    echo ""
    read -p "Press Enter to close this window..."
    exit 1
fi

# shellcheck disable=SC1091
source "$CONDA_BASE/etc/profile.d/conda.sh"

if ! conda env list | grep -q "^${ENV_NAME} "; then
    echo ""
    echo "First run -- creating the '${ENV_NAME}' conda environment."
    echo "This installs Streamlit, pyTMD, and the other packages this tool"
    echo "needs, without touching your other conda environments. It can take"
    echo "a few minutes; later runs skip straight to launching the app."
    echo ""
    conda create -y -n "${ENV_NAME}" python=3.11
fi

conda activate "${ENV_NAME}"

echo "Checking dependencies are up to date..."
pip install -q -r requirements.txt

echo ""
echo "Starting the app -- your browser should open automatically."
echo "To stop it, close this window or press Ctrl+C."
echo ""
streamlit run app.py
