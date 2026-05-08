#!/usr/bin/env python
"""Stop: auto-update GitNexus index when files were modified during the session."""
import os, shutil, subprocess, sys


FLOW_DIR = os.path.join(".claude", "flow")
TRACK_FILE = os.path.join(FLOW_DIR, "modified-files.jsonl")


def main():
    gn = shutil.which("gitnexus")
    if not gn:
        return

    has_changes = False
    if os.path.exists(TRACK_FILE):
        with open(TRACK_FILE, "r") as f:
            has_changes = any(line.strip() for line in f if '"file"' in line)

    if not has_changes:
        return

    try:
        subprocess.run([gn, "analyze", "."], capture_output=True, timeout=30)
    except Exception:
        pass


if __name__ == "__main__":
    main()
