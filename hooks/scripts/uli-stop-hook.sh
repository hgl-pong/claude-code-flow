#!/bin/bash
# Thin Claude shell wrapper around the shared Python ULI stop hook.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
exec python "$SCRIPT_DIR/uli-stop-hook.py"
