#!/usr/bin/env python
"""PreCompact: preserve workflow state before context compaction."""
import glob, json, os
from datetime import datetime, timezone

FLOW_DIR = os.path.join(".claude", "flow")
STATE_FILE = os.path.join(FLOW_DIR, "workflow-state.json")
MODIFIED_FILES_JSONL = os.path.join(FLOW_DIR, "modified-files.jsonl")
VERIFICATION_EVIDENCE = os.path.join(FLOW_DIR, "verification-evidence.jsonl")
PRE_COMPACT = os.path.join(FLOW_DIR, "pre-compact-context.md")

# Base list — slug-namespaced files (plans/*/…, ulw/*/…, uli/*/…) are added dynamically in main()
CRITICAL_FILES_BASE = [
    "workflow-state.json",
    "modified-files.jsonl", "verification-evidence.jsonl",
    "last-verification.json", "ui-research.md",
]

def now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def slug_namespaced_files() -> list[str]:
    """Discover current plan-brief.md and phase-context.md under slug-named subdirs."""
    found = []
    for pattern in [
        "plans/*/plan-brief.md", "plans/*/phase-context.md",
        "ulw/*/phase-context.md",
        "uli/*/plan-brief.md",
    ]:
        for path in sorted(glob.glob(os.path.join(FLOW_DIR, pattern))):
            found.append(os.path.relpath(path, FLOW_DIR).replace("\\", "/"))
    return found


def main():
    os.makedirs(FLOW_DIR, exist_ok=True)
    sections = []
    critical_files = CRITICAL_FILES_BASE + slug_namespaced_files()

    # 1. Current state
    state = {}
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r") as f:
                state = json.load(f)
        except (json.JSONDecodeError, Exception):
            pass

    sections.append(f"# Pre-Compact Context ({now()})\n")
    sections.append("## Current State")
    sections.append(f"- Phase: {state.get('phase', 'unknown')}")
    sections.append(f"- Mode: {state.get('mode', 'standard')}")
    sections.append(f"- Tasks: {state.get('task_done', 0)}/{state.get('task_total', 0)}")
    sections.append(f"- Current agent: {state.get('current_agent', 'none')}")
    sections.append(f"- Retry count: {state.get('retry_count', 0)}")
    last_verification = state.get("last_verification") or {}
    if last_verification:
        sections.append(f"- Last verification: {last_verification.get('status', '?')} {last_verification.get('kind', '?')} -- `{last_verification.get('command', '')}`")
    sections.append("")

    # 2. Recent file modifications (last 10 from modified-files.jsonl)
    if os.path.exists(MODIFIED_FILES_JSONL):
        try:
            with open(MODIFIED_FILES_JSONL, "r") as f:
                lines = [l.strip() for l in f.readlines() if l.strip()]
            recent = lines[-10:] if lines else []
            if recent:
                sections.append("## Recent File Modifications")
                for line in reversed(recent):
                    try:
                        entry = json.loads(line)
                        sections.append(f"- [{entry.get('action', '?')}] {entry.get('file', '?')} ({entry.get('agent', '?')})")
                    except json.JSONDecodeError:
                        sections.append(f"- {line}")
                sections.append("")
        except Exception:
            pass

    # 3. Recent verification evidence (last 10 from verification-evidence.jsonl)
    if os.path.exists(VERIFICATION_EVIDENCE):
        try:
            with open(VERIFICATION_EVIDENCE, "r", encoding="utf-8") as f:
                lines = [l.strip() for l in f.readlines() if l.strip()]
            recent = lines[-10:] if lines else []
            if recent:
                sections.append("## Recent Verification Evidence")
                for line in reversed(recent):
                    try:
                        entry = json.loads(line)
                        sections.append(f"- [{entry.get('status', '?')}] {entry.get('kind', '?')}: `{entry.get('command', '')}`")
                    except json.JSONDecodeError:
                        sections.append(f"- {line}")
                sections.append("")
        except Exception:
            pass

    # 4. Key decisions from phase-context (last 30 lines; check slug-namespaced paths first)
    phase_context_candidates = (
        sorted(glob.glob(os.path.join(FLOW_DIR, "plans/*/phase-context.md"))) +
        sorted(glob.glob(os.path.join(FLOW_DIR, "ulw/*/phase-context.md")))
    )
    for pc_path in phase_context_candidates:
        if os.path.exists(pc_path):
            try:
                with open(pc_path, "r") as f:
                    lines = f.readlines()
                if lines:
                    label = os.path.relpath(pc_path, FLOW_DIR).replace("\\", "/")
                    sections.append(f"## Phase Context — {label} (recent)")
                    for line in lines[-30:]:
                        sections.append(line.rstrip())
                    sections.append("")
            except Exception:
                pass

    content = "\n".join(sections)
    with open(PRE_COMPACT, "w") as f:
        f.write(content)

    # Output hint for the orchestrator to re-read critical files
    # Claude Code's createPostCompactFileAttachments() restores recently-read files
    print(f"FLOW: Pre-compact context saved. Critical files: {', '.join(critical_files)}")
    print(f"FLOW: Phase={state.get('phase', 'unknown')}, Tasks={state.get('task_done', 0)}/{state.get('task_total', 0)}")

if __name__ == "__main__":
    main()
