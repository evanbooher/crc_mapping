# One-time setup for the eCRC figures and Quarto report (Windows PowerShell).
# Run from the repo folder:   powershell -ExecutionPolicy Bypass -File setup.ps1
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

# 1. Find Python 3.13 / 3.12 / 3.11 (3.14 is too new for some mapping packages on Windows)
$ver = $null
foreach ($v in @("3.13", "3.12", "3.11")) {
    try {
        & py "-$v" -c "import sys" 2>$null
        if ($LASTEXITCODE -eq 0) { $ver = $v; break }
    } catch { }
}
if (-not $ver) {
    Write-Host "Need Python 3.11-3.13. Install one with:  py install 3.13   (then re-run this script)" -ForegroundColor Yellow
    exit 1
}
Write-Host "Using Python $ver"

# 2. Project virtual environment
if (-not (Test-Path ".venv\Scripts\python.exe")) { & py "-$ver" -m venv .venv }
$vpy = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"

# 3. Packages (includes Jupyter, papermill, and pip-system-certs for the agency network certificate)
& $vpy -m pip install --upgrade pip
& $vpy -m pip install -r requirements.txt
& $vpy -c "import geopandas, contextily, jupyter_core, nbclient, ipykernel, papermill; print('Python packages OK')"
if ($LASTEXITCODE -ne 0) { Write-Host "Package check failed; see the error above." -ForegroundColor Yellow; exit 1 }

# 4. Inputs and Quarto
$missing = @("data\pssp-2026-summary-v2.xlsx", "data\pssp-2026-by-month-v4.xlsx") | Where-Object { -not (Test-Path $_) }
foreach ($f in $missing) { Write-Host "Missing input workbook: $f  (copy it into the data folder)" -ForegroundColor Yellow }
if (-not (Get-Command quarto -ErrorAction SilentlyContinue)) {
    Write-Host "Quarto not found on PATH. Install from https://quarto.org (only needed for the HTML report)." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Setup complete. Next:" -ForegroundColor Green
Write-Host "  .\render.ps1 -P imagery:False     # quick draft, no satellite basemap"
Write-Host "  .\render.ps1                      # full report"
