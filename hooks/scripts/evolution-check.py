#!/usr/bin/env python
"""SessionStart: check if evolution analysis is due and report pending proposals."""
import json, os, sys

FLOW_DIR = os.path.join(".claude", "flow")
EVOLUTION_CFG = os.path.join(FLOW_DIR, "evolution.json")
EXEC_LOG = os.path.join(FLOW_DIR, "exec-log.jsonl")
PENDING_FILE = os.path.join(FLOW_DIR, "evolution-pending.md")

def load_config():
    if not os.path.exists(EVOLUTION_CFG):
        return {"auto_analyze_after": 5, "disabled": False, "auto_apply_low_risk": False, "last_analysis_session_count": 0}
    with open(EVOLUTION_CFG, "r") as f:
        return json.load(f)

def count_completed_sessions():
    if not os.path.exists(EXEC_LOG):
        return 0
    count = 0
    with open(EXEC_LOG, "r") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
                if entry.get("event") == "workflow_stop":
                    count += 1
            except json.JSONDecodeError:
                pass
    return count

def count_pending_proposals():
    if not os.path.exists(PENDING_FILE):
        return 0
    with open(PENDING_FILE, "r") as f:
        content = f.read()
    return content.count("\n### [EP-")

def main():
    config = load_config()

    if config.get("disabled", False):
        return

    # Check for pending proposals first
    pending = count_pending_proposals()
    if pending > 0:
        print(f"EVOLUTION_PENDING: {pending} proposal(s) awaiting review in .claude/flow/evolution-pending.md")
        return

    # Check if enough sessions since last analysis
    threshold = config.get("auto_analyze_after", 5)
    last_count = config.get("last_analysis_session_count", 0)
    current_count = count_completed_sessions()
    sessions_since = current_count - last_count

    if sessions_since >= threshold:
        print(f"EVOLUTION_READY: {sessions_since} sessions since last analysis. Consider running evolver to generate improvement proposals.")

if __name__ == "__main__":
    main()
