#!/usr/bin/env python
"""PostToolUse(Write|Edit): track modified files for review pipeline."""
import json, os, sys

TRACK_FILE = os.path.join(".claude", "flow", "modified-files.txt")

def main():
    os.makedirs(os.path.dirname(TRACK_FILE), exist_ok=True)
    try:
        data = json.loads(sys.stdin.read())
    except (json.JSONDecodeError, Exception):
        return

    file_path = data.get("tool_input", {}).get("file_path", "")
    if not file_path:
        return

    # Normalize to relative path
    try:
        rel = os.path.relpath(file_path)
    except ValueError:
        rel = file_path

    # Append if not already tracked
    existing = set()
    if os.path.exists(TRACK_FILE):
        with open(TRACK_FILE, "r") as f:
            existing = {line.strip() for line in f if line.strip()}

    if rel not in existing:
        with open(TRACK_FILE, "a") as f:
            f.write(rel + "\n")

if __name__ == "__main__":
    main()
