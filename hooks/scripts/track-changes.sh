#!/bin/bash
# Track modified files for review pipeline
TRACK_FILE=".claude/flow/modified-files.txt"
mkdir -p .claude/flow

INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | sed -n 's/.*"file_path"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' | head -1)

if [ -n "$FILE_PATH" ]; then
  REL_PATH=$(realpath --relative-to=. "$FILE_PATH" 2>/dev/null || echo "$FILE_PATH")
  grep -qxF "$REL_PATH" "$TRACK_FILE" 2>/dev/null || echo "$REL_PATH" >> "$TRACK_FILE"
fi
