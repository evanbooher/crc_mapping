# eCRC Puget Sound figures (PSSP 2026)

Maps and plots of eCRC sampling metrics by marine catch area (Marine Areas 5-13) used in the
October 2026 Puget Sound Sampling Unit eCRC post-season review.

## Files

| File | Purpose |
|---|---|
| `ecrc_maps.py` | Builds all eight figures (maps 01-05, plots 06-08) |
| `validate_figures.py` | Independent check of every drawn value and deck number against the source workbooks |
| `data/context_boundaries.geojson` | WA, neighboring states and BC outlines for the locator inset (us-atlas / world-atlas 1:10m) |
| `CRC.gdb.zip` | WDFW Catch Record Card area polygons (existing) |
| `crc map.R` | Original statewide creel coverage map (existing, unchanged) |

Input workbooks are not stored in the repo. Pass their paths on the command line.

## Setup

Conda (recommended on Windows; geopandas installs cleanly from conda-forge):

    conda create -n ecrc -c conda-forge python=3.12 geopandas pyogrio matplotlib openpyxl contextily
    conda activate ecrc

Or pip:

    python -m venv .venv
    .venv\Scripts\activate        # Windows  (macOS/Linux: source .venv/bin/activate)
    pip install -r requirements.txt

The satellite basemap is fetched from `server.arcgisonline.com` (Esri World Imagery) at run time,
so the machine needs internet access. Set `NO_IMAGERY=1` to skip it (values are unchanged).

## Run

    python ecrc_maps.py "<summary.xlsx>" "<by-month.xlsx>" figures
    python ecrc_maps.py "<summary.xlsx>" "<by-month.xlsx>" figures_slide --slide

- Without `--slide`: figures with titles and data captions (for reports).
- With `--slide`: same figures without titles/captions (slide titles carry them). These are the
  versions in the deck; the five imagery maps were inserted as JPEG (quality 93).
- Output is 400 dpi PNG. A full run with imagery takes several minutes (tile downloads).

Inputs used for the deck: `pssp-2026-summary-v2.xlsx` (version with the Barcode scans column)
and `pssp-2026-by-month-v4.xlsx`.

## Validate

PowerShell:

    $env:NO_IMAGERY="1"; $env:ECRC_LOG="fig_log.json"
    python ecrc_maps.py "<summary.xlsx>" "<by-month.xlsx>" figures_check
    python validate_figures.py "<summary.xlsx>" "<by-month.xlsx>" fig_log.json "<deck.pptx>" validation_report.csv

macOS/Linux: `NO_IMAGERY=1 ECRC_LOG=fig_log.json python ecrc_maps.py ...`

The deck-text checks in `validate_figures.py` match the slide wording at the time of writing; if
slide text has been edited, those rows may fail on wording rather than numbers.

## Quarto report

`ecrc_figures.qmd` runs both scripts and renders one self-contained HTML page: methods, a season
table by area, all eight figures, and the validation summary.

Extra packages: `conda install -c conda-forge jupyter ipykernel papermill` (papermill is only
needed for `-P` overrides). Check with `quarto check jupyter`.

    quarto render ecrc_figures.qmd -P summary_xlsx:"C:/data/pssp-2026-summary-v2.xlsx" -P monthly_xlsx:"C:/data/pssp-2026-by-month-v4.xlsx"

Or edit the parameters cell at the top of the .qmd and run `quarto render ecrc_figures.qmd`.
Add `-P imagery:False` for a fast draft (no satellite basemap). If Quarto picks up the wrong
Python (common in MSYS2/Git Bash), point it at the conda one first:
`export QUARTO_PYTHON="$(conda run -n ecrc python -c 'import sys; print(sys.executable)')"`.

## Figures

| # | File | Content |
|---|---|---|
| 01 | `01_season_pct_fish_ecrc.png` | Estimated % of harvested fish from eCRC anglers, by area |
| 02 | `02_season_refusal_rate.png` | % of eCRC anglers refusing the barcode scan, by area |
| 03 | `03_season_ecrc_sample_size.png` | eCRC interviews (outer circle) and barcode scans (inner) |
| 04 | `04_monthly_map_pct_fish_ecrc.png` | Monthly maps of eCRC fish share |
| 05 | `05_monthly_map_refusal.png` | Monthly maps of refusal rate |
| 06 | `06_monthly_lines_all_areas.png` | Monthly fish share and refusal rate, all areas (theme_bw style) |
| 07 | `07_monthly_lines_by_area.png` | Same, faceted by area |
| 08 | `08_scans_refusals_by_area.png` | Scans and refusal interviews per eCRC interview vs. 60% question rate |

Notes: eCRC fish share = total fish × eCRC licenses ÷ (paper + eCRC licenses) within each area.
Cells with fewer than 10 eCRC interviews are hatched (maps) or hollow, unconnected points (plots).
Percent labels on maps round halves up (9/40 = 22.5% shows as 23%).
