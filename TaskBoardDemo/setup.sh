#!/bin/bash
# Sets up TaskBoard: creates a Python virtual environment and installs its dependencies.
# Safe to run again; it only fills in what's missing.
set -euo pipefail
cd "$(dirname "$0")"

# Apps started from Finder get a minimal PATH, so include Homebrew's, where python3 may live.
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"

if ! command -v python3 >/dev/null; then
    echo "Python 3 wasn't found. Install it from python.org or with: brew install python" >&2
    exit 1
fi
if ! python3 -c 'import sys; sys.exit(sys.version_info < (3, 9))'; then
    echo "TaskBoard needs Python 3.9 or newer; this is $(python3 --version)." >&2
    exit 1
fi
if [ ! -x .venv/bin/python ]; then
    echo "Creating the virtual environment…"
    python3 -m venv .venv
fi
echo "Installing dependencies…"
.venv/bin/python -m pip install --quiet --upgrade pip
.venv/bin/python -m pip install --quiet -r requirements.txt

echo "Done. Open TaskBoard.app, or run: .venv/bin/python -m taskboard"
