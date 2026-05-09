#!/usr/bin/env python3
"""SessionStart: inject project-level memory from .claude/memory/project-context.md."""
import os

MEMORY_FILE = os.path.join(".claude", "memory", "project-context.md")


def main():
    try:
        with open(MEMORY_FILE, "r", encoding="utf-8") as f:
            content = f.read().strip()
    except OSError:
        return
    if content:
        print(f"PROJECT_MEMORY:\n{content}")


if __name__ == "__main__":
    main()
