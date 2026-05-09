#!/usr/bin/env python3
"""SessionStart: auto-configure statusline in ~/.claude/settings.json if absent."""
import json
import os
import sys
from pathlib import Path


def main():
    plugin_root = os.environ.get("CLAUDE_PLUGIN_ROOT", "")
    if not plugin_root:
        return

    script_path = Path(plugin_root) / "scripts" / "statusline.sh"
    if not script_path.exists():
        return

    settings_path = Path.home() / ".claude" / "settings.json"

    # Load existing settings (or start fresh)
    settings = {}
    if settings_path.exists():
        try:
            settings = json.loads(settings_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return  # Don't touch a corrupt settings file

    # Only auto-configure when statusLine is completely absent
    if "statusLine" in settings:
        return

    command = f"bash {script_path.as_posix()}"
    settings["statusLine"] = {"type": "command", "command": command}

    settings_path.parent.mkdir(parents=True, exist_ok=True)
    settings_path.write_text(
        json.dumps(settings, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"FLOW: Statusline auto-configured → {command}")
    print("FLOW: Reload Claude Code (or run /reload-plugins) to activate the status bar.")


if __name__ == "__main__":
    main()
