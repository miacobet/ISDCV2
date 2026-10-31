#!/bin/bash
# Launches the ISDC tool using the project's virtual environment.
cd "$(dirname "$0")" || exit 1

PY=""
for candidate in ".venv/bin/python" "venv/bin/python" "python3"; do
    if command -v "$candidate" >/dev/null 2>&1 \
       && "$candidate" -c "import PyQt5, openpyxl, reportlab" >/dev/null 2>&1; then
        PY="$candidate"
        break
    fi
done

if [ -z "$PY" ]; then
    echo "ERROR: No Python environment with the required packages was found."
    echo "Set one up from this folder with:"
    echo "    python3 -m venv .venv"
    echo "    .venv/bin/pip install -r requirements.txt"
    read -r -p "Press Enter to close..."
    exit 1
fi

"$PY" main.py
status=$?
if [ $status -ne 0 ]; then
    echo
    echo "The tool exited with an error (code $status)."
    read -r -p "Press Enter to close..."
fi
exit $status
