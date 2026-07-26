[CmdletBinding()]
param(
    [switch]$Dev,
    [switch]$Vision
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Venv = Join-Path $Root ".venv"
$VenvPython = Join-Path $Venv "Scripts\python.exe"

Set-Location $Root

try {
    $Python311 = (& py -3.11 -c "import sys; print(sys.executable)" 2>$null).Trim()
} catch {
    throw "Python 3.11 non trovato. Installa Python 3.11 x64 da python.org e riprova."
}

if (-not $Python311 -or -not (Test-Path -LiteralPath $Python311)) {
    throw "Python 3.11 non trovato. Verifica con: py -0p"
}

if (-not (Test-Path -LiteralPath $VenvPython)) {
    Write-Host "Creo .venv con Python 3.11..."
    & $Python311 -m venv $Venv
    if ($LASTEXITCODE -ne 0) { throw "Creazione .venv fallita." }
} else {
    $VenvVersion = (& $VenvPython -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')").Trim()
    if ($VenvVersion -ne "3.11") {
        throw ".venv esiste ma usa Python $VenvVersion. Eliminala manualmente e riesegui lo script."
    }
    Write-Host ".venv Python 3.11 gia presente."
}

Write-Host "Aggiorno pip..."
& $VenvPython -m pip install --use-feature=truststore --upgrade pip
if ($LASTEXITCODE -ne 0) { throw "Aggiornamento pip fallito." }

$Requirements = "requirements.txt"
if ($Vision) {
    $Requirements = "requirements-vision.txt"
} elseif ($Dev) {
    $Requirements = "requirements-dev.txt"
}

Write-Host "Installazione da $Requirements..."
& $VenvPython -m pip install --use-feature=truststore -r $Requirements
if ($LASTEXITCODE -ne 0) { throw "Installazione dipendenze fallita." }

if (-not (Test-Path -LiteralPath (Join-Path $Root ".env"))) {
    Write-Host ""
    Write-Host "File .env non presente. Per crearlo senza sovrascrivere nulla:"
    Write-Host "Copy-Item .env.example .env"
} else {
    Write-Host "File .env esistente: non modificato."
}

Write-Host ""
Write-Host "Verifica ambiente..."
& $VenvPython scripts\check_environment.py
if ($LASTEXITCODE -ne 0) { throw "Verifica ambiente fallita." }

Write-Host ""
Write-Host "Setup completato."
Write-Host "Avvio: .\.venv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8000"
