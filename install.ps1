#Requires -Version 5.1
<#
.SYNOPSIS
    Cross-platform local installer for dealflow (Windows PowerShell).
.DESCRIPTION
    Creates a project virtualenv (.venv), installs dealflow editable with the
    dev extra, and verifies the `dealflow` console script runs.
    Idempotent: re-running reuses the existing .venv.
#>
$ErrorActionPreference = 'Stop'

$RepoDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$VenvDir = Join-Path $RepoDir '.venv'
$VenvPy  = Join-Path $VenvDir 'Scripts\python.exe'
$VenvCli = Join-Path $VenvDir 'Scripts\dealflow.exe'

# Pick a boot Python interpreter (py launcher preferred on Windows).
$Boot = $null
foreach ($cand in @('py', 'python', 'python3')) {
    $cmd = Get-Command $cand -ErrorAction SilentlyContinue
    if ($cmd) {
        # `py` needs -3 to select Python 3.
        if ($cand -eq 'py') { $Boot = @('py', '-3') } else { $Boot = @($cmd.Source) }
        break
    }
}
if (-not $Boot) {
    Write-Error "Python 3.10+ is required but was not found. Install it from https://www.python.org/downloads/ (check 'Add to PATH') and re-run .\install.ps1"
    exit 1
}

Write-Host "==> Using boot interpreter: $($Boot -join ' ')"
& $Boot[0] $Boot[1..($Boot.Count-1)] --version

# Create the venv if it does not already exist (idempotent).
if (Test-Path $VenvPy) {
    Write-Host "==> Reusing existing virtualenv at $VenvDir"
} else {
    Write-Host "==> Creating virtualenv at $VenvDir"
    & $Boot[0] $Boot[1..($Boot.Count-1)] -m venv $VenvDir
}

Write-Host "==> Upgrading pip"
& $VenvPy -m pip install --upgrade pip | Out-Null

Write-Host "==> Installing dealflow (editable) with dev extra"
& $VenvPy -m pip install -e "$RepoDir[dev]"
if ($LASTEXITCODE -ne 0) {
    Write-Host "==> dev extra failed; installing base package only"
    & $VenvPy -m pip install -e $RepoDir
    if ($LASTEXITCODE -ne 0) { Write-Error "pip install failed"; exit 1 }
}

Write-Host "==> Verifying the dealflow console script"
if (Test-Path $VenvCli) {
    & $VenvCli --help | Select-Object -First 5
} else {
    Write-Host "   console script not found; falling back to 'python -m dealflow'"
    & $VenvPy -m dealflow --help | Select-Object -First 5
}

Write-Host @"

============================================================
 dealflow is installed in $VenvDir
============================================================
 Activate the virtualenv:

   PowerShell :  .\.venv\Scripts\Activate.ps1
   cmd.exe    :  .venv\Scripts\activate.bat

 (If activation is blocked, run once:
    Set-ExecutionPolicy -Scope CurrentUser RemoteSigned)

 Then run the CLI:

   dealflow --help
   dealflow forecast -p demos\01-basic\pipeline.yml -d demos\01-basic\deals.csv

 Or without activating:

   .\.venv\Scripts\dealflow.exe --help

 Run the tests:            .\.venv\Scripts\python.exe -m pytest -q
 Run all demo scenarios:   .\.venv\Scripts\python.exe demos\run_all.py
============================================================
"@
