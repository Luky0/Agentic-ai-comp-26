#!/bin/bash
# Creates a submission zip file for the ANL 2026 competition
# Excludes: examples, scenarios, report, tests, README.md, main.py, pyproject.toml, uv.lock, and dev files

set -e

OUTPUT="submission.zip"

# Remove old submission if exists
rm -f "$OUTPUT"

# Create the zip file
zip -r "$OUTPUT" . \
    -x "examples/*" \
    -x "scenarios/*" \
    -x "report/*" \
    -x "tests/*" \
    -x "README.md" \
    -x "main.py" \
    -x "pyproject.toml" \
    -x "uv.lock" \
    -x ".git/*" \
    -x ".venv/*" \
    -x "__pycache__/*" \
    -x "*.pyc" \
    -x ".ruff_cache/*" \
    -x ".pytest_cache/*" \
    -x ".gitignore" \
    -x ".envrc" \
    -x ".python-version" \
    -x "pyrightconfig.json" \
    -x ".pre-commit-config.yaml" \
    -x "make_submission.sh" \
    -x "make_submission.bat" \
    -x "dist/*" \
    -x "pyrightconfig.json" \
    -x "dist" \
    -x "*.egg-info/*"

echo ""
echo "Created $OUTPUT"
echo "Contents:"
unzip -l "$OUTPUT"
