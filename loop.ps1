$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
$Python = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) {
    $Python = (Get-Command py -ErrorAction Stop).Source
    & $Python -3 -m harness.loop @args
} else {
    & $Python -m harness.loop @args
}
exit $LASTEXITCODE
