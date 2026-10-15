# Render the eCRC Quarto report with the project's Python (Windows PowerShell).
# Usage:  .\render.ps1                        full report
#         .\render.ps1 -P imagery:False       quick draft, no satellite basemap
# If scripts are blocked: powershell -ExecutionPolicy Bypass -File render.ps1
Set-Location $PSScriptRoot
$vpy = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $vpy)) { Write-Host "No .venv found. Run setup.ps1 first." -ForegroundColor Yellow; exit 1 }
$env:QUARTO_PYTHON = $vpy
quarto render ecrc_figures.qmd @args
