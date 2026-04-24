#!/usr/bin/env python
"""Apply approved evolution proposals. Usage: apply-evolution.py <proposal_id>"""
import json, os, sys, shutil
from datetime import datetime, timezone

FLOW_DIR = os.path.join(".claude", "flow")
PENDING_FILE = os.path.join(FLOW_DIR, "evolution-pending.md")
HISTORY_FILE = os.path.join(FLOW_DIR, "evolution-history.md")
BACKUP_DIR = os.path.join(FLOW_DIR, "evolution-backups")

def now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def backup_file(filepath):
    """Create a timestamped backup of the file before modification."""
    os.makedirs(BACKUP_DIR, exist_ok=True)
    rel = os.path.relpath(filepath).replace(os.sep, "_")
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup_path = os.path.join(BACKUP_DIR, f"{ts}_{rel}")
    shutil.copy2(filepath, backup_path)
    return backup_path

def apply_proposal(proposal_id):
    """Read proposal from pending file and apply changes."""
    if not os.path.exists(PENDING_FILE):
        print("Error: No pending proposals file", file=sys.stderr)
        sys.exit(1)

    with open(PENDING_FILE, "r") as f:
        content = f.read()

    # Find the proposal section
    marker = f"### [{proposal_id}]"
    start = content.find(marker)
    if start == -1:
        print(f"Error: Proposal {proposal_id} not found", file=sys.stderr)
        sys.exit(1)

    # Extract until next proposal or end of file
    next_proposal = content.find("\n### [EP-", start + len(marker))
    if next_proposal == -1:
        next_proposal = len(content)
    section = content[start:next_proposal]

    # Extract target file
    target_file = None
    for line in section.split("\n"):
        if line.strip().startswith("- **File**:"):
            target_file = line.split(":", 1)[1].strip().strip("`")
            break

    if not target_file or not os.path.exists(target_file):
        print(f"Error: Target file not found or inaccessible: {target_file}", file=sys.stderr)
        sys.exit(1)

    # Extract proposed change
    proposed = None
    in_proposed = False
    proposed_lines = []
    for line in section.split("\n"):
        if "- **Proposed change**:" in line:
            in_proposed = True
            continue
        if in_proposed:
            if line.strip().startswith("- **") or line.strip().startswith("##"):
                break
            proposed_lines.append(line)
    if proposed_lines:
        proposed = "\n".join(proposed_lines).strip()

    # Backup original
    backup_path = backup_file(target_file)
    print(f"BACKUP: {backup_path}")

    # Read current content
    with open(target_file, "r") as f:
        current = f.read()

    # Write proposal to history
    os.makedirs(FLOW_DIR, exist_ok=True)
    entry = f"## [{proposal_id}] Applied at {now()}\n"
    entry += f"- File: {target_file}\n"
    entry += f"- Backup: {backup_path}\n"
    if proposed:
        entry += f"- Change: {proposed}\n"
    entry += "\n"

    with open(HISTORY_FILE, "a") as f:
        f.write(entry)

    print(f"PROPOSAL {proposal_id}: staged for application to {target_file}")
    print("Note: Actual text replacement should be done by the Claude agent with full context.")
    return target_file, proposed

def main():
    proposal_id = sys.argv[1] if len(sys.argv) > 1 else ""
    if not proposal_id:
        print("Usage: apply-evolution.py <proposal_id>", file=sys.stderr)
        sys.exit(1)

    apply_proposal(proposal_id)

if __name__ == "__main__":
    main()
