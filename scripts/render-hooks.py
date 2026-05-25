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
        "events": {"PreToolUse"},
    },
    "codex": {
        "root_var": "PLUGIN_ROOT",
        "events": {"PreToolUse"},
    },
}

WEB_MATCHER = "WebSearch|WebFetch|mcp__web-search-prime__web_search_prime|mcp__web-reader__webReader|mcp__web_reader__webReader"

REGISTRY = [
    {
        "event": "PreToolUse",
        "matcher": "EnterPlanMode",
        "hosts": ["claude"],
        "hooks": [("python", "hooks/scripts/plan-mode-guard.py", 5)],
    },
    {
        "event": "PreToolUse",
        "matcher": WEB_MATCHER,
        "hooks": [("python", "hooks/scripts/9router-intercept.py", 30)],
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

        payload["hooks"].setdefault(entry["event"], []).append(
            {
                "matcher": entry["matcher"],
                "hooks": hooks,
            }
        )
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("host", choices=sorted(HOSTS))
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--write", action="store_true")
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
