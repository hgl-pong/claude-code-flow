#!/usr/bin/env python
"""Evaluation gate for self-evolution changes. Usage: eval-gate.py <action> [args]"""
import json, os, sys, re

def validate_prompt_change(agent_file):
    """Validate a proposed prompt change to an agent file."""
    if not os.path.exists(agent_file):
        return {"result": "FAIL", "reason": f"Agent file not found: {agent_file}"}

    with open(agent_file, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()

    checks = []

    # Check 1: File has proper frontmatter
    if not content.startswith("---"):
        checks.append(("FAIL", "Missing YAML frontmatter"))

    # Check 2: File has name field
    if "name:" not in content.split("---")[1] if "---" in content else "":
        checks.append(("FAIL", "Missing 'name' field in frontmatter"))

    # Check 3: File has description field
    if "description:" not in content.split("---")[1] if "---" in content else "":
        checks.append(("WARN", "Missing 'description' field in frontmatter"))

    # Check 4: File has system prompt content (markdown heading OR substantial frontmatter)
    has_heading = bool(re.search(r"^# .+", content, re.MULTILINE))
    has_substantial_frontmatter = len(content) > 500
    if not has_heading and not has_substantial_frontmatter:
        checks.append(("FAIL", "No markdown heading and file is too short — agent seems to have no system prompt"))

    # Check 5: File is not empty or too short
    if len(content) < 200:
        checks.append(("WARN", "Agent file is very short (< 200 chars) — may be incomplete"))

    # Check 6: No contradictory instructions (basic heuristic)
    if "never" in content.lower() and "always" in content.lower():
        # Check if "never" and "always" appear close together
        lines = content.lower().split("\n")
        for i, line in enumerate(lines):
            if "never" in line and i + 1 < len(lines) and "always" in lines[i + 1]:
                checks.append(("WARN", "Potentially contradictory instructions (never/always on adjacent lines)"))
                break

    # Check 7: Core safety features preserved
    safety_terms = ["guard", "safety", "block", "validate", "check"]
    # This is informational only — not a hard requirement since not all agents need safety

    # Determine overall result
    fails = [c for c in checks if c[0] == "FAIL"]
    warns = [c for c in checks if c[0] == "WARN"]

    if fails:
        return {"result": "FAIL", "checks": checks, "reason": "; ".join(f[1] for f in fails)}
    elif warns:
        return {"result": "WARN", "checks": checks, "reason": "; ".join(w[1] for w in warns)}
    else:
        return {"result": "PASS", "checks": []}

def validate_skill(skill_file):
    """Validate a new skill file."""
    if not os.path.exists(skill_file):
        return {"result": "FAIL", "reason": f"Skill file not found: {skill_file}"}

    with open(skill_file, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()

    checks = []

    # Check 1: YAML frontmatter with name and description
    if not content.startswith("---"):
        checks.append(("FAIL", "Missing YAML frontmatter"))
    else:
        frontmatter = content.split("---")[1] if len(content.split("---")) > 1 else ""
        if "name:" not in frontmatter:
            checks.append(("FAIL", "Missing 'name' in skill frontmatter"))
        if "description:" not in frontmatter:
            checks.append(("WARN", "Missing 'description' in skill frontmatter"))

    # Check 2: Has markdown content (heading)
    if not re.search(r"^# .+", content, re.MULTILINE):
        checks.append(("FAIL", "No markdown heading — skill has no content"))

    # Check 3: Has Process or Instructions section
    if not re.search(r"^## .*(Process|Instructions|Steps|Usage)", content, re.MULTILINE):
        checks.append(("WARN", "No Process/Instructions section found"))

    fails = [c for c in checks if c[0] == "FAIL"]
    warns = [c for c in checks if c[0] == "WARN"]

    if fails:
        return {"result": "FAIL", "checks": checks, "reason": "; ".join(f[1] for f in fails)}
    elif warns:
        return {"result": "WARN", "checks": checks, "reason": "; ".join(w[1] for w in warns)}
    else:
        return {"result": "PASS", "checks": []}

def validate_rule(rule_text):
    """Validate a proposed rule."""
    checks = []

    if not rule_text or len(rule_text) < 10:
        checks.append(("FAIL", "Rule text too short (< 10 chars)"))
    if len(rule_text) > 500:
        checks.append(("WARN", "Rule text is very long (> 500 chars) — may be too broad"))

    # Check for overly broad patterns
    broad_terms = ["always", "never", "everything", "all files", "every time"]
    for term in broad_terms:
        if term in rule_text.lower():
            checks.append(("WARN", f"Contains broad term '{term}' — rule may be too general"))
            break

    fails = [c for c in checks if c[0] == "FAIL"]
    warns = [c for c in checks if c[0] == "WARN"]

    if fails:
        return {"result": "FAIL", "checks": checks, "reason": "; ".join(f[1] for f in fails)}
    elif warns:
        return {"result": "WARN", "checks": checks, "reason": "; ".join(w[1] for w in warns)}
    else:
        return {"result": "PASS", "checks": []}

def main():
    action = sys.argv[1] if len(sys.argv) > 1 else ""

    if action == "validate-prompt-change":
        agent_file = sys.argv[2] if len(sys.argv) > 2 else ""
        if not agent_file:
            print("Usage: eval-gate.py validate-prompt-change <agent_file>", file=sys.stderr)
            sys.exit(1)
        result = validate_prompt_change(agent_file)
        print(json.dumps(result, indent=2))
        sys.exit(0 if result["result"] != "FAIL" else 1)

    elif action == "validate-skill":
        skill_file = sys.argv[2] if len(sys.argv) > 2 else ""
        if not skill_file:
            print("Usage: eval-gate.py validate-skill <skill_file>", file=sys.stderr)
            sys.exit(1)
        result = validate_skill(skill_file)
        print(json.dumps(result, indent=2))
        sys.exit(0 if result["result"] != "FAIL" else 1)

    elif action == "validate-rule":
        rule_text = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else ""
        if not rule_text:
            print("Usage: eval-gate.py validate-rule <rule_text>", file=sys.stderr)
            sys.exit(1)
        result = validate_rule(rule_text)
        print(json.dumps(result, indent=2))
        sys.exit(0 if result["result"] != "FAIL" else 1)

    else:
        print(f"Unknown action: {action}", file=sys.stderr)
        print("Usage: eval-gate.py <validate-prompt-change|validate-skill|validate-rule>", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
