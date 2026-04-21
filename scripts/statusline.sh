#!/bin/bash
# Claude Code Flow statusline — shows workflow state
# Configure in settings.json:
#   "statusLine": { "type": "command", "command": "bash <path-to-this-script>" }

TRACK_FILE=".claude/flow/modified-files.txt"

if [ ! -f "$TRACK_FILE" ] || [ ! -s "$TRACK_FILE" ]; then
  echo "flow: idle"
  exit 0
fi

COUNT=$(wc -l < "$TRACK_FILE")
LAST_FILE=$(tail -1 "$TRACK_FILE" 2>/dev/null)
# Truncate long filenames
if [ ${#LAST_FILE} -gt 30 ]; then
  LAST_FILE="...${LAST_FILE: -27}"
fi

echo "flow: $COUNT modified | last: $LAST_FILE"
