#!/bin/bash
# Thin Claude shell wrapper around the shared Python ULW stop hook.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
exec python "$SCRIPT_DIR/ulw-stop-hook.py"
