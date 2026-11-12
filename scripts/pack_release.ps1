# Build a sanitized release zip of this project.
# Usage:
#   powershell -ExecutionPolicy Bypass -File .\scripts\pack_release.ps1
#   powershell -ExecutionPolicy Bypass -File .\scripts\pack_release.ps1 -IncludePersonalDocs -IncludeDemo
#
# What is excluded: .env, .venv, .git, .idea, .vscode, .cursor, cookie/, data/, logs/, picture/,
# output/, __pycache__/, *.pyc, *.log, *.db, *.sqlite, *.zip.
# Also excluded by default: __005__* (resume / interview notes),
# __000__demo (scratch demos containing another machine's absolute paths),
# and docs/AutoMarketing_*.html.
# Re-include with -IncludePersonalDocs / -IncludeDemo.

param(
    [string]$OutDir = [Environment]::GetFolderPath("Desktop"),
    [switch]$IncludePersonalDocs,
    [switch]$IncludeDemo
)

$ErrorActionPreference = "Continue"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$root = Split-Path -Parent $scriptDir
Set-Location $root

$excludeDirs = @(
    ".git", ".venv", "venv", ".idea", ".vscode", ".cursor", ".pytest_cache",
    "__pycache__", "cookie", "data", "logs", "picture", "output", "site"
)
$excludeFiles = @(
    ".env", "*.pyc", "*.pyo", "*.log", "*.db", "*.sqlite", "*.sqlite3",
    "*.zip", "*.bak", "*.tmp", "toutiao_state.json"
)
if (-not $IncludePersonalDocs) {
    # resume / interview material folder (name starts with __005__)
    $excludeDirs += "__005__*"
}
if (-not $IncludeDemo) {
    # scratch learning demos; some contain absolute paths from another machine
    $excludeDirs += "__000__demo"
}

$stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$stage = Join-Path $env:TEMP "automarketing_release_$stamp"
New-Item -ItemType Directory -Path $stage -Force | Out-Null

Write-Host "[1/4] Copying files to a clean staging folder ..." -ForegroundColor Cyan
$copied = 0
Get-ChildItem -LiteralPath $root -Recurse -Force -File | ForEach-Object {
    $rel = $_.FullName.Substring($root.Length + 1)
    $segments = $rel.Split([char]'\')
    $name = $segments[$segments.Length - 1]

    if (-not $IncludePersonalDocs -and $rel -like "docs\AutoMarketing_*") { return }

    foreach ($s in $segments) {
        foreach ($d in $excludeDirs) {
            if ($s -like $d) { return }
        }
    }
    foreach ($pattern in $excludeFiles) {
        if ($name -like $pattern) { return }
    }

    $dest = Join-Path $stage $rel
    $destDir = Split-Path -Parent $dest
    if (-not (Test-Path $destDir)) { New-Item -ItemType Directory -Path $destDir -Force | Out-Null }
    Copy-Item -LiteralPath $_.FullName -Destination $dest -Force
    $script:copied++
}
Write-Host "      $copied files staged at $stage"

Write-Host "[2/4] Scanning staged files for secrets ..." -ForegroundColor Cyan
$secretValues = @()
$envFile = Join-Path $root ".env"
if (Test-Path $envFile) {
    Get-Content $envFile | ForEach-Object {
        # Only treat KEY/TOKEN/SECRET-like values as secrets; plain values such as
        # "baidu" or "qwen-image-2.1-pro" legitimately appear in docs and README.
        if ($_ -match "^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(\S.*?)\s*$") {
            $name = $Matches[1]
            $v = $Matches[2].Trim()
            if ($name -match "(?i)(key|token|secret|password|passwd|pwd)" -and $v.Length -ge 12) {
                $secretValues += $v
            }
        }
    }
}

$scanExtensions = @(".py", ".md", ".txt", ".jsx", ".js", ".html", ".json", ".ps1",
                    ".example", ".cfg", ".ini", ".toml", ".yml", ".yaml", ".env")
$findings = @()

Get-ChildItem -LiteralPath $stage -Recurse -Force -File | ForEach-Object {
    if ($scanExtensions -notcontains $_.Extension.ToLower()) { return }
    $text = Get-Content -LiteralPath $_.FullName -Raw -ErrorAction SilentlyContinue
    if (-not $text) { return }
    $rel = $_.FullName.Substring($stage.Length + 1)

    foreach ($v in $secretValues) {
        if ($text.Contains($v)) {
            $script:findings += "$rel  <- contains a real value from .env"
            break
        }
    }
    if ($text -match "sk-[A-Za-z0-9_\-]{20,}") {
        $script:findings += "$rel  <- looks like an API key (sk-...)"
    }
}

if ($findings.Count -gt 0) {
    Write-Host ""
    Write-Host "ABORTED: potential secrets found in the staged copy:" -ForegroundColor Red
    $findings | Sort-Object -Unique | ForEach-Object { Write-Host "  $_" -ForegroundColor Red }
    Write-Host ""
    Write-Host "Nothing was zipped. Remove the offending lines, then run this script again." -ForegroundColor Yellow
    Write-Host "Staging folder kept for inspection: $stage"
    exit 1
}
Write-Host "      No secrets found" -ForegroundColor Green

Write-Host "[3/4] Writing RELEASE_NOTES.txt ..." -ForegroundColor Cyan
$notes = @(
    "AutoMarketing - sanitized release package",
    "Built: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')",
    "",
    "This package contains source code and docs only.",
    "Excluded on purpose:",
    "  - .env (API keys), cookie/ (login state), data/ (checkpoints)",
    "  - picture/, output/, logs/ (generated artifacts)",
    "  - .venv/, .git/, .idea/, __pycache__/",
    "",
    "Before running:",
    "  1. copy .env.example to .env and fill in MODEL_API_KEY",
    "  2. run start.ps1 (Windows PowerShell)",
    ""
)
Set-Content -LiteralPath (Join-Path $stage "RELEASE_NOTES.txt") -Value $notes -Encoding UTF8

if (-not (Test-Path $OutDir)) {
    Write-Host "WARNING: output folder does not exist, using the project root." -ForegroundColor Yellow
    $OutDir = $root
}
$zipPath = Join-Path $OutDir "AutoMarketing_sanitized_$stamp.zip"

Write-Host "[4/4] Compressing ..." -ForegroundColor Cyan
Compress-Archive -Path (Join-Path $stage "*") -DestinationPath $zipPath -Force
if (-not (Test-Path $zipPath)) {
    Write-Host "ERROR: compression failed." -ForegroundColor Red
    exit 1
}

Remove-Item -Recurse -Force $stage -ErrorAction SilentlyContinue

$sizeMb = [math]::Round((Get-Item $zipPath).Length / 1MB, 2)
Write-Host ""
Write-Host "Done: $zipPath ($sizeMb MB)" -ForegroundColor Green
Write-Host "Review the zip contents before publishing." -ForegroundColor Yellow
