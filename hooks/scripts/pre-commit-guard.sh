#!/bin/bash
# Thin Claude shell wrapper around the shared Python pre-commit guard.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
exec python "$SCRIPT_DIR/pre-commit-guard.py"
