#!/usr/bin/env bash
# One-time setup for the eCRC figures and Quarto report (Git Bash, MSYS2, macOS or Linux).
# Run from anywhere:   bash setup.sh
set -euo pipefail
cd "$(dirname "$0")"

# 1. Find Python 3.13 / 3.12 / 3.11 (3.14 is too new for some mapping packages on Windows)
PY=""
if command -v py >/dev/null 2>&1; then
  for v in 3.13 3.12 3.11; do
    if py "-$v" -c "import sys" >/dev/null 2>&1; then PY="py -$v"; break; fi
  done
fi
if [ -z "$PY" ]; then
  for c in python3.13 python3.12 python3.11 python3 python; do
    if command -v "$c" >/dev/null 2>&1 && "$c" -c "import sys; sys.exit(0 if (3,11) <= sys.version_info[:2] <= (3,13) else 1)" 2>/dev/null; then
      PY="$c"; break
    fi
  done
fi
if [ -z "$PY" ]; then
  echo "Need Python 3.11-3.13. On Windows: py install 3.13   (then re-run this script)"; exit 1
fi
echo "Using: $PY ($($PY -c 'import sys; print(sys.version.split()[0])'))"

# 2. Project virtual environment
[ -d .venv ] || $PY -m venv .venv
if [ -f .venv/Scripts/python.exe ]; then VPY=.venv/Scripts/python.exe; else VPY=.venv/bin/python; fi

# 3. Packages (call pip through python; MSYS2 cannot run the pip launcher directly)
"$VPY" -m pip install --upgrade pip
"$VPY" -m pip install -r requirements.txt
"$VPY" -c "import geopandas, contextily, jupyter_core, nbclient, ipykernel, papermill; print('Python packages OK')"

# 4. Inputs and Quarto
for f in data/pssp-2026-summary-v2.xlsx data/pssp-2026-by-month-v4.xlsx; do
  [ -f "$f" ] || echo "Missing input workbook: $f  (copy it into the data folder)"
done
command -v quarto >/dev/null 2>&1 || echo "Quarto not found on PATH. Install from https://quarto.org (only needed for the HTML report)."

echo
echo "Setup complete. Next:"
echo "  bash render.sh -P imagery:False     # quick draft, no satellite basemap"
echo "  bash render.sh                      # full report"
