
# AutoMarketing launcher (Windows PowerShell 5.1 compatible, ASCII only)
# Usage: powershell -ExecutionPolicy Bypass -File .\start.ps1
#
# NOTE: do not set $ErrorActionPreference = "Stop" here. In PowerShell 5.1,
# stderr output from a native command (python traceback, pip WARNING) becomes
# a terminating NativeCommandError. We check $LASTEXITCODE explicitly instead.

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root
$ErrorActionPreference = "Continue"

$venvDir = Join-Path $root ".venv"
$venvPython = Join-Path $venvDir "Scripts\python.exe"
$reqFile = Join-Path $root "requirements.txt"

$logDir = Join-Path $root "logs"
if (-not (Test-Path $logDir)) { New-Item -ItemType Directory -Path $logDir | Out-Null }
$pipLog = Join-Path $logDir "pip-install.log"

# The code uses typing.NotRequired (Python 3.11+), and 3.13+ has no consistent
# dependency set for these packages. Target 3.11/3.12 explicitly.
$baseCandidates = @(
    (Join-Path $env:USERPROFILE ".conda\envs\A2Aagent\python.exe"),
    (Join-Path $env:USERPROFILE ".conda\envs\edu_agent\python.exe")
)

function Find-BasePython {
    foreach ($c in $baseCandidates) {
        if (Test-Path $c) { return $c }
    }
    $cmd = Get-Command python -ErrorAction SilentlyContinue
    if ($cmd) {
        $v = & $cmd.Source -c "import sys; print('%d.%d' % sys.version_info[:2])" 2>&1
        if ("$v".Trim() -match "^3\.(11|12)$") { return $cmd.Source }
    }
    return $null
}

function Test-Dependencies {
    if (-not (Test-Path $venvPython)) { return $false }
    $check = "import langgraph, langgraph.checkpoint.sqlite, langchain_openai, langchain_mcp_adapters, fastapi, uvicorn, streamlit, playwright, dashscope, mcp"
    & $venvPython -c $check 2>&1 | Out-Null
    return ($LASTEXITCODE -eq 0)
}

function Install-Dependencies {
    Write-Host "      Saving pip output to $pipLog" -ForegroundColor DarkGray
    & $venvPython -m pip install -U pip 2>&1 | Tee-Object -FilePath $pipLog
    if ($LASTEXITCODE -ne 0) {
        Write-Host "      WARNING: pip self-upgrade failed, using the bundled pip." -ForegroundColor Yellow
    }
    & $venvPython -m pip install -r $reqFile 2>&1 | Tee-Object -FilePath $pipLog -Append
    return ($LASTEXITCODE -eq 0)
}

if (Test-Dependencies) {
    Write-Host "[1/4] Dependencies OK" -ForegroundColor Green
} else {
    # Reuse an existing 3.10/3.11/3.12 venv and just fill in whatever is missing.
    $venvVersion = $null
    if (Test-Path $venvPython) {
        $venvVersion = & $venvPython -c "import sys; print('%d.%d' % sys.version_info[:2])" 2>&1
    }

    if ($venvVersion -and ("$venvVersion" -match "^3\.(11|12)$")) {
        Write-Host "[1/4] Repairing existing .venv (Python $venvVersion) ..." -ForegroundColor Cyan
        if (-not (Install-Dependencies)) {
            Write-Host "ERROR: pip install failed. Full output saved to: $pipLog" -ForegroundColor Red
            exit 1
        }
    } else {
        if (Test-Path $venvDir) {
            Write-Host "[1/4] Removing incompatible .venv ..." -ForegroundColor Yellow
            Remove-Item -Recurse -Force $venvDir -ErrorAction SilentlyContinue
            if (Test-Path $venvDir) {
                Write-Host "ERROR: cannot remove $venvDir. Close any process using it and rerun." -ForegroundColor Red
                exit 1
            }
        }

        $basePython = Find-BasePython
        if (-not $basePython) {
            Write-Host "ERROR: no Python 3.11/3.12 interpreter found. Install one and rerun." -ForegroundColor Red
            exit 1
        }

        Write-Host "[1/4] Creating virtual environment with:" -ForegroundColor Cyan
        Write-Host "      $basePython"
        & $basePython -m venv $venvDir
        if ($LASTEXITCODE -ne 0) {
            Write-Host "ERROR: failed to create the virtual environment." -ForegroundColor Red
            exit 1
        }
        & $venvPython --version

        Write-Host "[2/4] Installing dependencies (first run may take 5-10 minutes) ..." -ForegroundColor Cyan
        if (-not (Install-Dependencies)) {
            Write-Host ""
            Write-Host "ERROR: pip install failed. Dependencies are NOT installed." -ForegroundColor Red
            Write-Host "Full pip output saved to: $pipLog" -ForegroundColor Yellow
            exit 1
        }

        Write-Host "[3/4] Installing Playwright Chromium ..." -ForegroundColor Cyan
        & $venvPython -m playwright install chromium
        if ($LASTEXITCODE -ne 0) {
            Write-Host "WARNING: Chromium install failed. Image generation still works," -ForegroundColor Yellow
            Write-Host "         but auto-publishing will fail until it is installed." -ForegroundColor Yellow
        }
    }

    # Catch a half-finished install: pip exited 0 but a module is still missing.
    if (-not (Test-Dependencies)) {
        Write-Host "ERROR: dependencies are still incomplete after install." -ForegroundColor Red
        Write-Host "Check $pipLog, then rerun this script." -ForegroundColor Yellow
        exit 1
    }
}

$envFile = Join-Path $root ".env"
if (-not (Test-Path $envFile)) {
    Copy-Item (Join-Path $root ".env.example") $envFile
    Write-Host "Created .env from .env.example. Please fill in MODEL_API_KEY." -ForegroundColor Yellow
}

$envContent = Get-Content $envFile -Raw
if ($envContent -match "(?m)^MODEL_API_KEY=\s*$") {
    Write-Host "WARNING: MODEL_API_KEY is empty. The UI will open, but generation will fail." -ForegroundColor Yellow
    Write-Host "         Edit $envFile and rerun this script." -ForegroundColor Yellow
}

Write-Host "[4/4] Starting FastAPI at http://127.0.0.1:8000" -ForegroundColor Green
Write-Host "      Keep this window open. Press CTRL+C to stop." -ForegroundColor DarkGray
& $venvPython (Join-Path $root "__002__fastapi\__001__server.py")
