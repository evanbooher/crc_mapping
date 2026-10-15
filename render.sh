#!/usr/bin/env bash
# Render the eCRC Quarto report with the project's Python (Git Bash, MSYS2, macOS or Linux).
# Usage:  bash render.sh                        full report
#         bash render.sh -P imagery:False       quick draft, no satellite basemap
set -euo pipefail
cd "$(dirname "$0")"
if [ -f .venv/Scripts/python.exe ]; then VPY=.venv/Scripts/python.exe; else VPY=.venv/bin/python; fi
[ -f "$VPY" ] || { echo "No .venv found. Run: bash setup.sh"; exit 1; }
QP="$(pwd)/$VPY"
command -v cygpath >/dev/null 2>&1 && QP="$(cygpath -w "$QP")"   # Windows path for Quarto under MSYS2/Git Bash
export QUARTO_PYTHON="$QP"
quarto render ecrc_figures.qmd "$@"
