#!/usr/bin/env python3
"""Render host-specific hook manifests from one canonical registry."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

HOSTS = {
    "claude": {
        "root_var": "CLAUDE_PLUGIN_ROOT",
        "matchers": {
            "shell": "Bash",
            "agent": "Agent",
            "write": "Write|Edit",
        },
        "events": {
            "UserPromptSubmit",
            "PreToolUse",
            "SessionStart",
            "PostToolUse",
            "SubagentStart",
            "SubagentStop",
            "TaskCreated",
            "TaskCompleted",
            "Stop",
            "PreCompact",
            "PostCompact",
            "SessionEnd",
        },
    },
    "codex": {
        "root_var": "PLUGIN_ROOT",
        "matchers": {
            "shell": "Bash|shell_command|functions.shell_command",
            "agent": "Agent|spawn_agent|send_input|wait_agent",
            "write": "Write|Edit|apply_patch|functions.apply_patch",
        },
        "events": {
            "UserPromptSubmit",
            "PreToolUse",
            "SessionStart",
            "PostToolUse",
            "Stop",
        },
    },
}

REGISTRY = [
    {
        "event": "UserPromptSubmit",
        "matcher": "",
        "hooks": [
            ("python", "hooks/scripts/ulw-detector.py", 3),
            ("python", "hooks/scripts/uli-detector.py", 3),
            ("python", "hooks/scripts/plan-detector.py", 3),
            ("python", "hooks/scripts/keyword-router.py", 3),
        ],
    },
    {
        "event": "PreToolUse",
        "matcher": "EnterPlanMode",
        "hosts": ["claude"],
        "hooks": [("python", "hooks/scripts/plan-mode-guard.py", 5)],
    },
    {
        "event": "PreToolUse",
        "matcher_key": "shell",
        "hooks": [
            ("bash", "hooks/scripts/pre-commit-guard.sh", 10, ["claude"]),
            ("python", "hooks/scripts/pre-commit-guard.py", 10, ["codex"]),
        ],
    },
    {
        "event": "PreToolUse",
        "matcher_key": "agent",
        "hooks": [
            ("bash", "hooks/scripts/pre-agent-guard.sh", 10, ["claude"]),
            ("python", "hooks/scripts/pre-agent-guard.py", 10, ["codex"]),
        ],
    },
    {
        "event": "SessionStart",
        "matcher": "",
        "hooks": [
            ("python", "hooks/scripts/memory-inject.py", 5),
            ("python", "hooks/scripts/auto-statusline.py", 5, ["claude"]),
            ("python", "hooks/scripts/session-check.py", 10),
            ("python", "hooks/scripts/flow-state.py snapshot", 5),
        ],
    },
    {
        "event": "PostToolUse",
        "matcher_key": "write",
        "hooks": [
            ("python", "hooks/scripts/track-changes.py", 10),
            ("python", "hooks/scripts/comment-checker.py", 5),
        ],
    },
    {
        "event": "PostToolUse",
        "matcher_key": "shell",
        "hooks": [("python", "hooks/scripts/track-verification.py", 10)],
    },
    {
        "event": "SubagentStart",
        "matcher": "",
        "hosts": ["claude"],
        "hooks": [("python", "hooks/scripts/on-agent-start.py", 10)],
    },
    {
        "event": "SubagentStop",
        "matcher": "",
        "hosts": ["claude"],
        "hooks": [("python", "hooks/scripts/on-agent-complete.py", 10)],
    },
    {
        "event": "TaskCreated",
        "matcher": "",
        "hosts": ["claude"],
        "hooks": [("python", "hooks/scripts/on-task-created.py", 5)],
    },
    {
        "event": "TaskCompleted",
        "matcher": "",
        "hosts": ["claude"],
        "hooks": [("python", "hooks/scripts/on-task-completed.py", 5)],
    },
    {
        "event": "Stop",
        "matcher": "",
        "hooks": [
            ("python", "hooks/scripts/todo-enforcer.py", 5),
            ("bash", "hooks/scripts/ulw-stop-hook.sh", 10, ["claude"]),
            ("bash", "hooks/scripts/uli-stop-hook.sh", 10, ["claude"]),
            ("python", "hooks/scripts/ulw-stop-hook.py", 10, ["codex"]),
            ("python", "hooks/scripts/uli-stop-hook.py", 10, ["codex"]),
            ("python", "hooks/scripts/on-workflow-stop.py", 10),
        ],
    },
    {
        "event": "PreCompact",
        "matcher": "",
        "hosts": ["claude"],
        "hooks": [("python", "hooks/scripts/on-compact.py", 10)],
    },
    {
        "event": "PostCompact",
        "matcher": "",
        "hosts": ["claude"],
        "hooks": [("python", "hooks/scripts/on-post-compact.py", 10)],
    },
    {
        "event": "SessionEnd",
        "matcher": "",
        "hosts": ["claude"],
        "hooks": [("python", "hooks/scripts/flow-state.py snapshot", 5)],
    },
]


def hook_command(executable: str, relative_command: str, root_var: str) -> str:
    path, *args = relative_command.split(" ", 1)
    command = f"{executable} ${{{root_var}}}/{path}"
    if args:
        command = f"{command} {args[0]}"
    return command


def render_hook(hook: tuple, root_var: str) -> dict:
    executable, relative_command, timeout = hook[:3]
    return {
        "type": "command",
        "command": hook_command(executable, relative_command, root_var),
        "timeout": timeout,
    }


def render(host: str) -> dict:
    config = HOSTS[host]
    payload = {"hooks": {}}
    for entry in REGISTRY:
        if host not in entry.get("hosts", HOSTS.keys()):
            continue
        if entry["event"] not in config["events"]:
            continue

        hooks = []
        for hook in entry["hooks"]:
            if len(hook) > 3 and host not in hook[3]:
                continue
            hooks.append(render_hook(hook, config["root_var"]))
        if not hooks:
            continue

        matcher = entry.get("matcher", config["matchers"].get(entry.get("matcher_key", ""), ""))
        payload["hooks"].setdefault(entry["event"], []).append(
            {
                "matcher": matcher,
                "hooks": hooks,
            }
        )
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("host", choices=sorted(HOSTS))
    parser.add_argument("--check", action="store_true", help="Compare rendered output to hooks/<host>-hooks.json")
    parser.add_argument("--write", action="store_true", help="Write rendered output to hooks/<host>-hooks.json as UTF-8")
    args = parser.parse_args()

    rendered = render(args.host)
    target = ROOT / "hooks" / ("hooks.json" if args.host == "claude" else "codex-hooks.json")
    formatted = json.dumps(rendered, indent=2) + "\n"

    if args.check:
        existing = json.loads(target.read_text(encoding="utf-8"))
        if existing != rendered:
            raise SystemExit(f"{target} is out of sync with scripts/render-hooks.py")
        return

    if args.write:
        target.write_text(formatted, encoding="utf-8")
        return

    print(formatted, end="")


if __name__ == "__main__":
    main()
