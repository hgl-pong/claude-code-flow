#!/usr/bin/env python
"""SessionStart: report git status and log session start."""
import subprocess, os, sys

FLOW_DIR = os.path.join(".claude", "flow")
SESSION_ID_FILE = os.path.join(FLOW_DIR, "session-id.txt")
LOG_EVENT = os.path.join(os.path.dirname(__file__), "log-event.py")

def main():
    # Generate session_id if not exists
    if not os.path.exists(SESSION_ID_FILE):
        from datetime import datetime, timezone
        os.makedirs(FLOW_DIR, exist_ok=True)
        sid = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S") + "-" + os.urandom(3).hex()
        with open(SESSION_ID_FILE, "w") as f:
            f.write(sid)

    # Report git status
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

    # Log session_start event
    try:
        subprocess.run(
            [sys.executable, LOG_EVENT, "session_start", f"branch={branch if 'branch' in dir() else 'unknown'}"],
            timeout=5, capture_output=True
        )
    except Exception:
        pass

if __name__ == "__main__":
    main()
