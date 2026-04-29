#!/usr/bin/env python3
"""
Analyze token usage from Claude Code session transcripts (.jsonl files).
Shows per-agent breakdown: main session + all subagents spawned via Task tool.

Usage:
  python3 analyze-token-usage.py <session-file.jsonl>

Finding session files:
  ls -lt ~/.claude/projects/<encoded-project-path>/*.jsonl | head -5
"""

import json
import sys
from pathlib import Path
from collections import defaultdict


def analyze_session(filepath: str):
    main_usage = dict(input=0, output=0, cache_create=0, cache_read=0, messages=0)
    subagents = defaultdict(lambda: dict(
        input=0, output=0, cache_create=0, cache_read=0, messages=0, description=None
    ))

    with open(filepath) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
            except json.JSONDecodeError:
                continue

            # Main-session assistant messages
            if data.get("type") == "assistant" and "message" in data:
                u = data["message"].get("usage", {})
                main_usage["messages"] += 1
                main_usage["input"]        += u.get("input_tokens", 0)
                main_usage["output"]       += u.get("output_tokens", 0)
                main_usage["cache_create"] += u.get("cache_creation_input_tokens", 0)
                main_usage["cache_read"]   += u.get("cache_read_input_tokens", 0)

            # Subagent tool results
            if data.get("type") == "user" and "toolUseResult" in data:
                r = data["toolUseResult"]
                if "usage" not in r or "agentId" not in r:
                    continue
                aid = r["agentId"]
                u   = r["usage"]
                if subagents[aid]["description"] is None:
                    raw = r.get("prompt", "")
                    first = raw.split("\n")[0].lstrip("You are ").strip()
                    subagents[aid]["description"] = first[:60] or f"agent-{aid}"
                subagents[aid]["messages"]     += 1
                subagents[aid]["input"]        += u.get("input_tokens", 0)
                subagents[aid]["output"]       += u.get("output_tokens", 0)
                subagents[aid]["cache_create"] += u.get("cache_creation_input_tokens", 0)
                subagents[aid]["cache_read"]   += u.get("cache_read_input_tokens", 0)

    return main_usage, dict(subagents)


def cost(u, input_rate=3.0, output_rate=15.0):
    total_in = u["input"] + u["cache_create"] + u["cache_read"]
    return total_in * input_rate / 1_000_000 + u["output"] * output_rate / 1_000_000


def fmt(n):
    return f"{n:,}"


def main():
    if len(sys.argv) < 2:
        print("Usage: analyze-token-usage.py <session.jsonl>")
        sys.exit(1)

    fpath = sys.argv[1]
    if not Path(fpath).exists():
        print(f"Error: file not found: {fpath}")
        sys.exit(1)

    main_u, subs = analyze_session(fpath)

    W = 110
    print("=" * W)
    print("TOKEN USAGE ANALYSIS")
    print("=" * W)
    print()
    print(f"  Session file: {fpath}")
    print()

    header = f"{'Agent':<16} {'Description':<40} {'Msgs':>5} {'Input':>10} {'Output':>10} {'Cache-R':>10} {'Cost':>8}"
    sep    = "-" * W
    print("Usage Breakdown:")
    print(sep)
    print(header)
    print(sep)

    # Main session row
    c = cost(main_u)
    print(f"{'main':<16} {'Main session (coordinator)':<40} "
          f"{main_u['messages']:>5} "
          f"{fmt(main_u['input']):>10} "
          f"{fmt(main_u['output']):>10} "
          f"{fmt(main_u['cache_read']):>10} "
          f"${c:>7.2f}")

    # Subagent rows (sorted by agent ID)
    for aid in sorted(subs):
        u   = subs[aid]
        c   = cost(u)
        desc = (u["description"] or f"agent-{aid}")[:40]
        print(f"{aid:<16} {desc:<40} "
              f"{u['messages']:>5} "
              f"{fmt(u['input']):>10} "
              f"{fmt(u['output']):>10} "
              f"{fmt(u['cache_read']):>10} "
              f"${c:>7.2f}")

    print(sep)

    # Totals
    total = dict(input=main_u["input"], output=main_u["output"],
                 cache_create=main_u["cache_create"], cache_read=main_u["cache_read"],
                 messages=main_u["messages"])
    for u in subs.values():
        for k in ("input","output","cache_create","cache_read","messages"):
            total[k] += u[k]

    total_in  = total["input"] + total["cache_create"] + total["cache_read"]
    total_all = total_in + total["output"]
    total_cost = cost(total)

    print()
    print("TOTALS:")
    print(f"  Messages:               {fmt(total['messages'])}")
    print(f"  Input tokens:           {fmt(total['input'])}")
    print(f"  Output tokens:          {fmt(total['output'])}")
    print(f"  Cache creation tokens:  {fmt(total['cache_create'])}")
    print(f"  Cache read tokens:      {fmt(total['cache_read'])}")
    print()
    print(f"  Total input (incl cache): {fmt(total_in)}")
    print(f"  Total tokens:             {fmt(total_all)}")
    print()
    print(f"  Estimated cost: ${total_cost:.2f}")
    print("  (rates: $3/$15 per M input/output tokens)")
    print()
    print("=" * W)


if __name__ == "__main__":
    main()
