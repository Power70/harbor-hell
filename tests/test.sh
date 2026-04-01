#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"
pip install -r requirements.txt -q 2>/dev/null
pytest test_outputs.py -v --tb=short 2>&1
