#!/usr/bin/env python
"""SessionStart: report git status."""
import subprocess

def main():
    try:
        branch = subprocess.check_output(
            ["git", "branch", "--show-current"], stderr=subprocess.DEVNULL, text=True
        ).strip()
        result = subprocess.check_output(
            ["git", "status", "--porcelain"], stderr=subprocess.DEVNULL, text=True
        )
        count = len([l for l in result.splitlines() if l.strip()])
        if count > 0:
            print(f"FLOW: On branch '{branch}' with {count} uncommitted file(s).")
        else:
            print(f"FLOW: On branch '{branch}', working tree clean.")
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("FLOW: Not in a git repository.")

if __name__ == "__main__":
    main()
