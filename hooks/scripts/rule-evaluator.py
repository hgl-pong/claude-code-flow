#!/usr/bin/env python
"""Rule evaluator. Usage: rule-evaluator.py <action> [args]"""
import json, os, sys, glob
from datetime import datetime, timezone

FLOW_DIR = os.path.join(".claude", "flow")
RULES_FILE = os.path.join(FLOW_DIR, "rules.json")

def load_rules():
    if os.path.exists(RULES_FILE):
        try:
            with open(RULES_FILE, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, Exception):
            return {"rules": []}
    return {"rules": []}

def save_rules(data):
    os.makedirs(FLOW_DIR, exist_ok=True)
    with open(RULES_FILE, "w") as f:
        json.dump(data, f, indent=2)

def now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def next_id(rules):
    ids = [r.get("id", "R000") for r in rules.get("rules", [])]
    nums = []
    for i in ids:
        try:
            nums.append(int(i.replace("R", "")))
        except ValueError:
            pass
    return f"R{max(nums, default=0) + 1:03d}"

def check_file(filepath, rules_data):
    """Check a file against all rules. Returns list of violations."""
    if not os.path.exists(filepath):
        return []
    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
    except Exception:
        return []

    violations = []
    for rule in rules_data.get("rules", []):
        pattern = rule.get("pattern", "")
        if not pattern:
            continue
        # Simple keyword-based check (case-insensitive)
        if pattern.lower() in content.lower():
            # Check if this is actually a violation or if the rule is being followed
            # For now, just flag potential violations based on pattern presence
            context = rule.get("context", "general")
            violations.append({
                "rule_id": rule.get("id"),
                "pattern": pattern,
                "context": context,
            })

    # Increment trigger count for matched rules
    rules_data_mod = rules_data
    for rule in rules_data_mod.get("rules", []):
        if any(v["rule_id"] == rule.get("id") for v in violations):
            rule["trigger_count"] = rule.get("trigger_count", 0) + 1
            rule["last_triggered"] = now()
    save_rules(rules_data_mod)

    return violations

def propose_rule(description, context="general", source="correction"):
    """Add a new rule proposal."""
    rules_data = load_rules()
    rid = next_id(rules_data)
    rule = {
        "id": rid,
        "pattern": description,
        "context": context,
        "source": source,
        "trigger_count": 0,
        "created_at": now(),
        "last_triggered": None,
    }
    rules_data.setdefault("rules", []).append(rule)
    save_rules(rules_data)
    print(f"OK: rule {rid} added: {description}")
    return rid

def evaluate_rules():
    """Find stale rules (never triggered or long inactive)."""
    rules_data = load_rules()
    stale = []
    active = []
    for rule in rules_data.get("rules", []):
        if rule.get("trigger_count", 0) == 0:
            stale.append(rule)
        else:
            active.append(rule)
    return {"active": len(active), "stale": len(stale), "stale_rules": stale}

def main():
    action = sys.argv[1] if len(sys.argv) > 1 else ""

    if action == "check":
        filepath = sys.argv[2] if len(sys.argv) > 2 else ""
        if not filepath:
            print("Usage: rule-evaluator.py check <file_path>", file=sys.stderr)
            sys.exit(1)
        rules_data = load_rules()
        violations = check_file(filepath, rules_data)
        if violations:
            for v in violations:
                print(f"VIOLATION [{v['rule_id']}] {v['pattern']} (context: {v['context']})")
        else:
            print("OK: no violations")

    elif action == "propose":
        description = sys.argv[2] if len(sys.argv) > 2 else ""
        context = sys.argv[3] if len(sys.argv) > 3 else "general"
        if not description:
            print("Usage: rule-evaluator.py propose <description> [context]", file=sys.stderr)
            sys.exit(1)
        propose_rule(description, context)

    elif action == "evaluate":
        result = evaluate_rules()
        print(f"Active rules: {result['active']}")
        print(f"Stale rules (never triggered): {result['stale']}")
        for r in result["stale_rules"]:
            print(f"  {r['id']}: {r['pattern']} (created: {r.get('created_at', '?')})")

    elif action == "stats":
        rules_data = load_rules()
        rules = rules_data.get("rules", [])
        print(f"Total rules: {len(rules)}")
        for r in rules:
            tc = r.get("trigger_count", 0)
            lt = r.get("last_triggered", "never")
            print(f"  {r['id']}: {r['pattern']} | triggered: {tc} | last: {lt}")

    elif action == "list":
        rules_data = load_rules()
        rules = rules_data.get("rules", [])
        for r in rules:
            print(f"{r['id']}|{r.get('context', 'general')}|{r['pattern']}")

    else:
        print(f"Unknown action: {action}", file=sys.stderr)
        print("Usage: rule-evaluator.py <check|propose|evaluate|stats|list>", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
