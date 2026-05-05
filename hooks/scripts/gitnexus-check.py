#!/usr/bin/env python
"""SessionStart: check GitNexus CLI availability and index status."""
import shutil, subprocess, sys


def main():
    gn = shutil.which("gitnexus")
    if not gn:
        print("FLOW: GitNexus not found. Install with: npm install -g gitnexus")
        return

    try:
        result = subprocess.run(
            [gn, "status"], capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0 and "indexed" in (result.stdout + result.stderr).lower():
            return  # already indexed, nothing to report
    except Exception:
        pass

    print("FLOW: GitNexus installed but repo not indexed. Run: gitnexus analyze .")


if __name__ == "__main__":
    main()
