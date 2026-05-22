#!/usr/bin/env python
"""Shared helpers for portable stop hooks."""

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path


def read_hook_input():
    try:
        return json.loads(sys.stdin.read() or "{}")
    except json.JSONDecodeError:
        return {}


def load_json(path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def save_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def last_assistant_text(transcript_path):
    last = ""
    try:
        lines = Path(transcript_path).read_text(encoding="utf-8", errors="ignore").splitlines()
    except OSError:
        return None
    for line in lines[-200:]:
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        if entry.get("role") != "assistant":
            continue
        content = entry.get("message", {}).get("content", [])
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                last = item.get("text", "")
    return last


def mark_inactive(state_file, state):
    state["active"] = False
    state["completed_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    save_json(state_file, state)


def load_active_state(state_file):
    state = load_json(state_file, {})
    if not state or not state.get("active", False):
        return None
    return state


def session_matches(state, hook_input):
    state_session = state.get("session_id") or ""
    hook_session = hook_input.get("session_id") or ""
    return not state_session or state_session == hook_session


def completion_summary(last_output, tag):
    match = re.search(rf"<{tag}>(.*?)</{tag}>", last_output or "", re.S)
    if not match:
        return None
    summary = match.group(1).strip()
    return summary or "complete"
