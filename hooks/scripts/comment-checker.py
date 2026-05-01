#!/usr/bin/env python
"""PostToolUse(Write|Edit): detect AI-generated comment slop patterns."""
import json, os, sys, re
from datetime import datetime, timezone

FLOW_DIR = os.path.join(".claude", "flow")

AI_PHRASES = [
    re.compile(r"#\s*(let me|here we|this function does|note:|important:|todo: add|todo: implement)", re.I),
    re.compile(r"//\s*(let me|here we|this function does|note:|important:|todo: add|todo: implement)", re.I),
]

REDUNDANT_PATTERN = re.compile(
    r"^\s*(#|//)\s*"
    r"(increment|decrement|set|get|return|assign|update|add|remove|delete|check|validate|initialize)"
    r"\s+\w+"
    r"\s*$", re.I
)

COMMENTED_CODE = re.compile(r"^\s*(#|//)\s*\S.*[;=({<>}]")

def now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def find_slop(content, file_path):
    warnings = []
    lines = content.splitlines()
    consecutive_commented_code = 0

    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if not stripped:
            consecutive_commented_code = 0
            continue

        for pat in AI_PHRASES:
            if pat.search(stripped):
                warnings.append({"line": i, "type": "ai_phrase", "text": stripped[:80]})
                break

        if REDUNDANT_PATTERN.match(stripped):
            next_line = lines[i] if i < len(lines) else ""
            if next_line.strip() and not next_line.strip().startswith(("#", "//")):
                warnings.append({"line": i, "type": "redundant_comment", "text": stripped[:80]})

        if COMMENTED_CODE.match(stripped) and not any(kw in stripped.lower() for kw in ["http", "see ", "e.g.", "ref:", "src:"]):
            consecutive_commented_code += 1
            if consecutive_commented_code >= 3:
                warnings.append({"line": i, "type": "commented_code_block", "text": f"block ends at line {i}"})
                consecutive_commented_code = 0
        else:
            consecutive_commented_code = 0

    return warnings

def main():
    os.makedirs(FLOW_DIR, exist_ok=True)
    try:
        data = json.loads(sys.stdin.read())
    except (json.JSONDecodeError, Exception):
        return

    file_path = data.get("tool_input", {}).get("file_path", "")
    if not file_path or not os.path.exists(file_path):
        return

    skip_exts = {".json", ".jsonl", ".lock", ".map", ".min.js", ".min.css", ".svg", ".png", ".jpg", ".gif"}
    _, ext = os.path.splitext(file_path)
    if ext.lower() in skip_exts or file_path.endswith(".min.js") or file_path.endswith(".min.css"):
        return

    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
    except Exception:
        return

    warnings = find_slop(content, file_path)
    if not warnings:
        return

    rel = os.path.relpath(file_path)
    entry = {
        "ts": now(),
        "event": "comment_slop_warning",
        "file": rel,
        "warnings": warnings,
    }

    log_file = os.path.join(FLOW_DIR, "exec-log.jsonl")
    with open(log_file, "a") as f:
        f.write(json.dumps(entry) + "\n")

if __name__ == "__main__":
    main()
