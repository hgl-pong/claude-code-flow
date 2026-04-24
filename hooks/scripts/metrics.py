#!/usr/bin/env python
"""Workflow metrics collector. Usage: metrics.py <action> [session_id]"""
import json, os, sys
from collections import defaultdict
from datetime import datetime, timezone

FLOW_DIR = os.path.join(".claude", "flow")
EXEC_LOG = os.path.join(FLOW_DIR, "exec-log.jsonl")

def load_exec_log():
    if not os.path.exists(EXEC_LOG):
        return []
    entries = []
    with open(EXEC_LOG, "r") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return entries

def parse_ts(ts_str):
    try:
        return datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None

def fmt_duration(td):
    if td is None:
        return "N/A"
    total_seconds = td.total_seconds()
    if total_seconds < 60:
        return f"{total_seconds:.0f}s"
    minutes = int(total_seconds // 60)
    seconds = int(total_seconds % 60)
    return f"{minutes}m{seconds}s"

def collect(entries, session_id=None):
    """Collect metrics for a specific session (or latest session)."""
    if session_id:
        filtered = [e for e in entries if e.get("session_id") == session_id]
    else:
        # Use latest session
        sessions = set(e.get("session_id") for e in entries)
        if not sessions:
            return None
        latest_sid = max(sessions)
        filtered = [e for e in entries if e.get("session_id") == latest_sid]
        session_id = latest_sid

    if not filtered:
        return None

    # Agent stats
    agent_stats = defaultdict(lambda: {"count": 0, "statuses": defaultdict(int)})
    for e in filtered:
        if e.get("event") == "agent_complete":
            agent = e.get("agent", "unknown")
            agent_stats[agent]["count"] += 1
            agent_stats[agent]["statuses"][e.get("status", "unknown")] += 1

    # Phase durations
    phase_transitions = [e for e in filtered if e.get("event") == "phase_transition"]
    phase_durations = {}
    sorted_transitions = sorted(phase_transitions, key=lambda x: x.get("ts", ""))
    for i in range(len(sorted_transitions)):
        curr = sorted_transitions[i]
        to_phase = curr.get("to", "")
        ts_curr = parse_ts(curr.get("ts", ""))
        if i + 1 < len(sorted_transitions):
            ts_next = parse_ts(sorted_transitions[i + 1].get("ts", ""))
            if ts_curr and ts_next:
                phase_durations[to_phase] = fmt_duration(ts_next - ts_curr)
        elif ts_curr:
            phase_durations[to_phase] = "in progress"

    # Guard blocks
    guard_blocks = [e for e in filtered if e.get("event") == "tool_guard_block"]

    # Review results
    reviews = [e for e in filtered if e.get("event") == "review_result"]

    return {
        "session_id": session_id,
        "total_events": len(filtered),
        "agent_stats": dict(agent_stats),
        "phase_durations": phase_durations,
        "guard_blocks": len(guard_blocks),
        "review_count": len(reviews),
    }

def aggregate(entries):
    """Aggregate metrics across all sessions."""
    sessions = defaultdict(list)
    for e in entries:
        sessions[e.get("session_id", "unknown")].append(e)

    total_sessions = len(sessions)
    if total_sessions == 0:
        return None

    # Global agent stats
    global_agent = defaultdict(lambda: {"total_calls": 0, "sessions": 0})
    # Completion tracking
    completed = 0
    interrupted = 0

    for sid, events in sessions.items():
        # Agent calls
        seen_agents = set()
        for e in events:
            if e.get("event") == "agent_complete":
                agent = e.get("agent", "unknown")
                global_agent[agent]["total_calls"] += 1
                seen_agents.add(agent)
        for a in seen_agents:
            global_agent[a]["sessions"] += 1

        # Check if workflow completed (ended with workflow_stop in idle or review phase)
        stop_events = [e for e in events if e.get("event") == "workflow_stop"]
        if stop_events:
            last_stop = stop_events[-1]
            if last_stop.get("task_done", 0) >= last_stop.get("task_total", 0) and last_stop.get("task_total", 0) > 0:
                completed += 1
            else:
                interrupted += 1
        else:
            interrupted += 1

    # Guard blocks total
    guard_total = sum(1 for e in entries if e.get("event") == "tool_guard_block")

    return {
        "total_sessions": total_sessions,
        "completed": completed,
        "interrupted": interrupted,
        "completion_rate": f"{completed / total_sessions * 100:.0f}%" if total_sessions > 0 else "N/A",
        "global_agent_stats": dict(global_agent),
        "guard_blocks_total": guard_total,
    }

def main():
    action = sys.argv[1] if len(sys.argv) > 1 else ""
    session_id = sys.argv[2] if len(sys.argv) > 2 else None

    entries = load_exec_log()

    if action == "collect":
        result = collect(entries, session_id)
        if result:
            print(json.dumps(result, indent=2))
        else:
            print("No session data found", file=sys.stderr)
            sys.exit(1)

    elif action == "aggregate":
        result = aggregate(entries)
        if result:
            print(json.dumps(result, indent=2))
        else:
            print("No historical data found", file=sys.stderr)
            sys.exit(1)

    elif action == "raw":
        # Output last N entries (for timeline display)
        n = int(sys.argv[2]) if len(sys.argv) > 2 else 20
        for e in entries[-n:]:
            ts = e.get("ts", "")
            event = e.get("event", "")
            details = []
            for k, v in e.items():
                if k not in ("ts", "session_id", "event"):
                    details.append(f"{k}={v}")
            detail_str = " ".join(details)
            print(f"{ts} [{event}] {detail_str}")

    else:
        print(f"Unknown action: {action}", file=sys.stderr)
        print("Usage: metrics.py <collect|aggregate|raw> [args]", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
