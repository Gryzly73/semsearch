$ErrorActionPreference = "Stop"
$Root = Split-Path $PSScriptRoot -Parent
Set-Location $Root
$Python = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) {
    $Python = (Get-Command py -ErrorAction Stop).Source
    & $Python -3 -m demo.reset @args
} else {
    & $Python -m demo.reset @args
}
exit $LASTEXITCODE
