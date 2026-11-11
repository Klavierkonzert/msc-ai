#!/usr/bin/env bash
# ==============================================================================
# Evolutionary Design Environment Setup Script
# ==============================================================================
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=== [1/5] Checking Python Dependencies ==="
if command -v pip &> /dev/null; then
    echo "Installing requirements from requirements.txt..."
    pip install -r requirements.txt
elif command -v python3 &> /dev/null; then
    python3 -m pip install -r requirements.txt
elif command -v python &> /dev/null; then
    python -m pip install -r requirements.txt
else
    echo "ERROR: Neither pip nor python could be found. Please ensure Python is installed and added to PATH."
    exit 1
fi

echo ""
echo "=== [2/5] Locating Framsticks Simulator ==="
# Find Framsticks directory (picks the highest version, e.g. Framsticks55)
FRAMS_DIR=$(ls -d Framsticks* 2>/dev/null | grep -E 'Framsticks[0-9]+$' | sort -V | tail -n 1 || true)

if [ -z "$FRAMS_DIR" ] || [ ! -d "$FRAMS_DIR" ]; then
    echo "ERROR: Framsticks directory (e.g. Framsticks55) not found in '$SCRIPT_DIR'."
    echo "Please download the latest Framsticks build from http://www.framsticks.com/apps-devel"
    echo "and extract it into '$SCRIPT_DIR/'."
    exit 1
fi
echo "Found Framsticks distribution at: $FRAMS_DIR"

echo ""
echo "=== [3/5] Verifying framspy Directory ==="
if [ ! -d "framspy-download" ]; then
    echo "ERROR: 'framspy-download' directory not found in '$SCRIPT_DIR'."
    echo "Download it using SVN:"
    echo "  svn checkout https://www.framsticks.com/svn/framsticks/framspy/ framspy-download"
    exit 1
fi
echo "Found framspy-download directory."

echo ""
echo "=== [4/5] Copying Simulation Files (*.sim) ==="
mkdir -p "$FRAMS_DIR/data"
cp -v framspy-download/*.sim "$FRAMS_DIR/data/" 2>/dev/null || true

if [ ! -f "$FRAMS_DIR/data/uneven-ground.sim" ]; then
    echo "Downloading uneven-ground.sim to $FRAMS_DIR/data/..."
    curl -k -sSL -o "$FRAMS_DIR/data/uneven-ground.sim" "https://www.cs.put.poznan.pl/mkomosinski/uneven-ground.sim"
    echo "Downloaded uneven-ground.sim successfully."
else
    echo "uneven-ground.sim is already present in $FRAMS_DIR/data/."
fi

echo ""
echo "=== [5/5] Testing Simulator Interoperation ==="
# Determine shared library extension based on OS
case "$(uname -s)" in
    CYGWIN*|MINGW*|MSYS*)
        LIB_NAME="frams-objects.dll"
        ;;
    Darwin*)
        LIB_NAME="frams-objects.dylib"
        ;;
    *)
        LIB_NAME="frams-objects.so"
        ;;
esac

LIB_PATH="$SCRIPT_DIR/$FRAMS_DIR/$LIB_NAME"
# Fallback for Windows native environments running git-bash:
if [ ! -f "$LIB_PATH" ] && [ -f "$SCRIPT_DIR/$FRAMS_DIR/frams-objects.dll" ]; then
    LIB_PATH="$SCRIPT_DIR/$FRAMS_DIR/frams-objects.dll"
fi

if [ ! -f "$LIB_PATH" ]; then
    echo "WARNING: Could not find library '$LIB_NAME' in '$FRAMS_DIR'."
    echo "Available libraries in $FRAMS_DIR:"
    ls -l "$FRAMS_DIR"/frams-objects.* 2>/dev/null || true
    exit 1
fi

echo "Found Framsticks library: $LIB_PATH"
PYTHON_CMD="python"
if ! command -v python &> /dev/null && command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
fi

$PYTHON_CMD framspy-download/frams-test.py "$FRAMS_DIR"

echo ""
echo "=============================================================================="
echo " Setup complete! Evolutionary Design environment is configured and ready."
echo "=============================================================================="
