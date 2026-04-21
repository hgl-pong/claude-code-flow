#!/bin/bash
# Session start check — report git status
if git rev-parse --is-inside-work-tree 2>/dev/null; then
  BRANCH=$(git branch --show-current 2>/dev/null)
  UNCOMMITTED=$(git status --porcelain 2>/dev/null | wc -l)
  if [ "$UNCOMMITTED" -gt 0 ]; then
    echo "FLOW: On branch '$BRANCH' with $UNCOMMITTED uncommitted file(s)."
  else
    echo "FLOW: On branch '$BRANCH', working tree clean."
  fi
else
  echo "FLOW: Not in a git repository."
fi
