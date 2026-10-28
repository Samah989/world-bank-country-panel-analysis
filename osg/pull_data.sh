#!/bin/bash
# ---------------------------------------------------------------------------
# OSG wrapper: pull all World Bank indicators. Installs pip deps to a local
# target dir (works with osgvo-ubuntu-20.04 which lacks python3-venv).
# ---------------------------------------------------------------------------
set -euo pipefail
export PS4='+ [pull_data $(date +%H:%M:%S)] '
set -x

echo "[pull_data] host=$(hostname)  start=$(date -Iseconds)"
echo "[pull_data] pwd=$(pwd)  ls -la:"
ls -la

mkdir -p data deps
python3 -m ensurepip --user 2>/dev/null || true
python3 -m pip install --upgrade --target=deps pip 2>/dev/null || python3 -m pip install --user --upgrade pip
python3 -m pip install --target=deps -r requirements-osg.txt

export PYTHONPATH="$PWD/deps:${PYTHONPATH:-}"
python3 pull_all_indicators.py

echo "[pull_data] done=$(date -Iseconds)  files:"
ls -lh data
