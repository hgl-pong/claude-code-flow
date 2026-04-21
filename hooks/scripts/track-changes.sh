#!/bin/bash
# Track modified files for review pipeline
TRACK_FILE=".claude/flow/modified-files.txt"
mkdir -p .claude/flow

# Read tool input for the file path
# The PostToolUse hook receives the tool input; we extract the file path from stdin
INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | grep -oP '"file_path"\s*:\s*"\K[^"]+' || echo "")

if [ -n "$FILE_PATH" ]; then
  # Use relative path
  REL_PATH=$(realpath --relative-to=. "$FILE_PATH" 2>/dev/null || echo "$FILE_PATH")
  # Add to tracking file if not already present
  grep -qxF "$REL_PATH" "$TRACK_FILE" 2>/dev/null || echo "$REL_PATH" >> "$TRACK_FILE"
fi
