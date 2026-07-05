#!/usr/bin/env sh
# Cross-platform local installer for dealflow (macOS / Linux).
# Creates a project virtualenv (.venv), installs dealflow editable with the
# dev extra, and verifies the `dealflow` console script runs.
# Idempotent: re-running reuses the existing .venv.
set -e

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_DIR="$REPO_DIR/.venv"

# Pick a Python interpreter: prefer python3, fall back to python.
if command -v python3 >/dev/null 2>&1; then
    PY_BOOT=python3
elif command -v python >/dev/null 2>&1; then
    PY_BOOT=python
else
    echo "ERROR: Python 3.10+ is required but neither python3 nor python was found." >&2
    echo "Install it from https://www.python.org/downloads/ and re-run ./install.sh" >&2
    exit 1
fi

echo "==> Using boot interpreter: $($PY_BOOT --version 2>&1) ($(command -v $PY_BOOT))"

# Create the venv if it does not already exist (idempotent).
if [ -x "$VENV_DIR/bin/python" ]; then
    echo "==> Reusing existing virtualenv at $VENV_DIR"
else
    echo "==> Creating virtualenv at $VENV_DIR"
    "$PY_BOOT" -m venv "$VENV_DIR"
fi

VENV_PY="$VENV_DIR/bin/python"

echo "==> Upgrading pip"
"$VENV_PY" -m pip install --upgrade pip >/dev/null

echo "==> Installing dealflow (editable) with dev extra"
if ! "$VENV_PY" -m pip install -e "$REPO_DIR[dev]"; then
    echo "==> dev extra failed; installing base package only"
    "$VENV_PY" -m pip install -e "$REPO_DIR"
fi

echo "==> Verifying the dealflow console script"
if "$VENV_DIR/bin/dealflow" --help >/dev/null 2>&1; then
    "$VENV_DIR/bin/dealflow" --help | head -n 5
else
    echo "   console script not on venv path; falling back to 'python -m dealflow'"
    "$VENV_PY" -m dealflow --help | head -n 5
fi

cat <<EOF

============================================================
 dealflow is installed in $VENV_DIR
============================================================
 Activate the virtualenv for your shell:

   bash/zsh :   source .venv/bin/activate
   fish     :   source .venv/bin/activate.fish

 Then run the CLI:

   dealflow --help
   dealflow forecast -p demos/01-basic/pipeline.yml -d demos/01-basic/deals.csv

 Or without activating:

   .venv/bin/dealflow --help

 Run the tests:            make test   (or: .venv/bin/python -m pytest -q)
 Run all demo scenarios:   make demo   (or: .venv/bin/python demos/run_all.py)
============================================================
EOF
