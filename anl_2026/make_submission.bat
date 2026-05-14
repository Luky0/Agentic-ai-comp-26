@echo off
REM Creates a submission zip file for the ANL 2026 competition
REM
REM Usage: Simply run this script from the project root directory
REM   make_submission.bat
REM
REM Requirements: Windows with PowerShell (included in Windows 7+ by default)
REM
REM Excludes: examples, scenarios, report, tests, README.md, main.py, pyproject.toml, uv.lock, and dev files

set OUTPUT=submission.zip

REM Remove old submission if exists
if exist %OUTPUT% del %OUTPUT%

echo Creating submission.zip...
echo.

REM Use PowerShell to create zip with exclusions matching make_submission.sh
powershell -Command "$ProgressPreference = 'SilentlyContinue'; " ^
    "Get-ChildItem -Recurse -File | Where-Object { " ^
    "$_.FullName -notmatch '\\examples\\' -and " ^
    "$_.FullName -notmatch '\\scenarios\\' -and " ^
    "$_.FullName -notmatch '\\report\\' -and " ^
    "$_.FullName -notmatch '\\tests\\' -and " ^
    "$_.FullName -notmatch '\\.git\\' -and " ^
    "$_.FullName -notmatch '\\.venv\\' -and " ^
    "$_.FullName -notmatch '\\__pycache__\\' -and " ^
    "$_.FullName -notmatch '\\.ruff_cache\\' -and " ^
    "$_.FullName -notmatch '\\.pytest_cache\\' -and " ^
    "$_.FullName -notmatch '\\dist\\' -and " ^
    "$_.FullName -notmatch '\\.egg-info\\' -and " ^
    "$_.Name -ne 'README.md' -and " ^
    "$_.Name -ne 'main.py' -and " ^
    "$_.Name -ne 'pyproject.toml' -and " ^
    "$_.Name -ne 'uv.lock' -and " ^
    "$_.Name -ne '.gitignore' -and " ^
    "$_.Name -ne '.envrc' -and " ^
    "$_.Name -ne '.python-version' -and " ^
    "$_.Name -ne 'pyrightconfig.json' -and " ^
    "$_.Name -ne '.pre-commit-config.yaml' -and " ^
    "$_.Name -ne 'make_submission.sh' -and " ^
    "$_.Name -ne 'make_submission.bat' -and " ^
    "$_.Name -notlike '*.pyc' " ^
    "} | ForEach-Object { " ^
    "$relativePath = $_.FullName.Substring((Get-Location).Path.Length + 1); " ^
    "[PSCustomObject]@{Path = $_.FullName; RelativePath = $relativePath} " ^
    "} | ForEach-Object -Begin { " ^
    "$tempDir = Join-Path $env:TEMP ('anl2026_submission_' + (Get-Random)); " ^
    "New-Item -ItemType Directory -Path $tempDir -Force | Out-Null " ^
    "} -Process { " ^
    "$destPath = Join-Path $tempDir $_.RelativePath; " ^
    "$destDir = Split-Path $destPath -Parent; " ^
    "if (-not (Test-Path $destDir)) { New-Item -ItemType Directory -Path $destDir -Force | Out-Null }; " ^
    "Copy-Item $_.Path $destPath -Force " ^
    "} -End { " ^
    "Compress-Archive -Path (Join-Path $tempDir '*') -DestinationPath '%CD%\\%OUTPUT%' -Force; " ^
    "Remove-Item $tempDir -Recurse -Force " ^
    "}"

if exist %OUTPUT% (
    echo.
    echo Created %OUTPUT%
    echo Contents:
    echo.
    tar -tf %OUTPUT%
    echo.
) else (
    echo.
    echo ERROR: Failed to create submission.zip
    exit /b 1
)
