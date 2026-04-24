#!/usr/bin/env python
"""Skill detector — analyze unmatched tasks and propose new skills. Usage: skill-detector.py <action>"""
import json, os, sys
from collections import Counter
from datetime import datetime, timezone

FLOW_DIR = os.path.join(".claude", "flow")
SEEDS_FILE = os.path.join(FLOW_DIR, "skill-seeds.json")
UNMATCHED_FILE = os.path.join(FLOW_DIR, "unmatched-tasks.jsonl")
PROPOSALS_FILE = os.path.join(FLOW_DIR, "skill-proposals.md")

def now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def load_seeds():
    if os.path.exists(SEEDS_FILE):
        try:
            with open(SEEDS_FILE, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, Exception):
            return {"skills": []}
    return {"skills": []}

def match_skill(task_description):
    """Match a task description against known skill patterns. Returns (skill_name, confidence) or (None, 0)."""
    seeds = load_seeds()
    desc_lower = task_description.lower()
    best_match = None
    best_score = 0

    for skill in seeds.get("skills", []):
        if skill.get("status") != "active":
            continue
        score = 0
        for pattern in skill.get("trigger_patterns", []):
            if pattern.lower() in desc_lower:
                score += 1
        if score > best_score:
            best_score = score
            best_match = skill

    if best_match and best_score > 0:
        return best_match, best_score
    return None, 0

def record_unmatched(task_description):
    """Record a task that didn't match any skill."""
    os.makedirs(FLOW_DIR, exist_ok=True)
    entry = {
        "ts": now(),
        "task": task_description,
    }
    with open(UNMATCHED_FILE, "a") as f:
        f.write(json.dumps(entry) + "\n")

def increment_usage(skill_name):
    """Increment usage count for a matched skill."""
    seeds = load_seeds()
    for skill in seeds.get("skills", []):
        if skill.get("name") == skill_name:
            skill["usage_count"] = skill.get("usage_count", 0) + 1
            break
    os.makedirs(FLOW_DIR, exist_ok=True)
    with open(SEEDS_FILE, "w") as f:
        json.dump(seeds, f, indent=2)

def detect_proposals(min_occurrences=3):
    """Analyze unmatched tasks and propose new skills."""
    if not os.path.exists(UNMATCHED_FILE):
        return []

    tasks = []
    with open(UNMATCHED_FILE, "r") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    tasks.append(json.loads(line))
                except json.JSONDecodeError:
                    pass

    if not tasks:
        return []

    # Extract keywords and find common patterns
    # Simple approach: group by similar task descriptions (shared significant words)
    stop_words = {"the", "a", "an", "and", "or", "to", "for", "of", "in", "on", "with", "is", "are", "it", "add", "create", "make", "build", "fix", "update", "implement", "write", "set", "up"}
    task_groups = {}

    for task in tasks:
        desc = task.get("task", "").lower()
        words = [w for w in desc.split() if len(w) > 3 and w not in stop_words]
        key = tuple(sorted(words))
        if key not in task_groups:
            task_groups[key] = []
        task_groups[key].append(task.get("task", ""))

    proposals = []
    for key, group_tasks in task_groups.items():
        if len(group_tasks) >= min_occurrences:
            proposals.append({
                "keywords": list(key),
                "count": len(group_tasks),
                "examples": group_tasks[:3],
            })

    return proposals

def write_proposals(proposals):
    """Write skill proposals to file."""
    if not proposals:
        return

    os.makedirs(FLOW_DIR, exist_ok=True)
    lines = [f"# Skill Proposals\nGenerated: {now()}\n"]

    for i, p in enumerate(proposals, 1):
        lines.append(f"## Proposal {i}: {' '.join(p['keywords'][:3])}")
        lines.append(f"- **Frequency**: {p['count']} unmatched tasks")
        lines.append(f"- **Keywords**: {', '.join(p['keywords'])}")
        lines.append(f"- **Example tasks**:")
        for ex in p["examples"]:
            lines.append(f"  - \"{ex}\"")
        lines.append(f"- **Suggested agents**: oracle(plan) -> forge(impl) -> prism(tests) -> sentinel(review)")
        lines.append("")

    with open(PROPOSALS_FILE, "w") as f:
        f.write("\n".join(lines))

def main():
    action = sys.argv[1] if len(sys.argv) > 1 else ""

    if action == "match":
        task = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else ""
        if not task:
            print("Usage: skill-detector.py match <task_description>", file=sys.stderr)
            sys.exit(1)
        skill, score = match_skill(task)
        if skill:
            print(f"MATCH: {skill['name']} (score={score})")
            # Increment usage
            increment_usage(skill["name"])
        else:
            print("NO_MATCH")
            record_unmatched(task)

    elif action == "detect":
        min_occ = int(sys.argv[2]) if len(sys.argv) > 2 else 3
        proposals = detect_proposals(min_occ)
        if proposals:
            write_proposals(proposals)
            print(f"OK: {len(proposals)} proposal(s) written to {PROPOSALS_FILE}")
        else:
            print("OK: no new skill proposals (need {min_occ}+ similar unmatched tasks)")

    elif action == "list":
        seeds = load_seeds()
        for skill in seeds.get("skills", []):
            status = skill.get("status", "unknown")
            count = skill.get("usage_count", 0)
            print(f"{skill['name']}|{status}|usage={count}|patterns={','.join(skill.get('trigger_patterns', []))}")

    elif action == "stats":
        seeds = load_seeds()
        skills = seeds.get("skills", [])
        total = len(skills)
        active = sum(1 for s in skills if s.get("status") == "active")
        total_usage = sum(s.get("usage_count", 0) for s in skills)
        print(f"Total skills: {total}")
        print(f"Active: {active}")
        print(f"Total usage: {total_usage}")
        # Unmatched count
        if os.path.exists(UNMATCHED_FILE):
            with open(UNMATCHED_FILE, "r") as f:
                unmatched = sum(1 for line in f if line.strip())
            print(f"Unmatched tasks: {unmatched}")
        else:
            print("Unmatched tasks: 0")

    else:
        print(f"Unknown action: {action}", file=sys.stderr)
        print("Usage: skill-detector.py <match|detect|list|stats>", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
