#!/usr/bin/env python3
"""Keyword-based skill router for UserPromptSubmit hook.

Detects task patterns in user prompts and suggests matching skills
via additionalContext. Complements (doesn't replace) using-claude-code-flow.
"""
import json
import re
import sys

EXTERNAL_SOURCE_PATTERN = (
    r'\bhttps?://\S*(github|gitlab)\S*'
    r'|(\b(reference|borrow|port|migrate|inspired by|compare with)\b'
    r'.{0,60}\b(repo|repository|plugin|agent pack|workflow|github|gitlab)\b)'
    r'|(\b(repo|repository|plugin|agent pack|workflow|github|gitlab)\b'
    r'.{0,60}\b(reference|borrow|port|migrate|inspired by|compare with)\b)'
    r'|((参考|借鉴|对比|移植|迁移).{0,30}(仓库|插件|工作流|智能体|代理|github|gitlab|repo|plugin|workflow|agent))'
)

COORDINATED_DELIVERY_PATTERN = (
    r'\b(execute|implement|build|deliver|ship|finish|complete|orchestrate|coordinate)\b'
    r'.*\b(plan|feature|workflow|pipeline|task|tasks|implementation|change|changes|fix|refactor|agents?)\b'
    r'|\b(multi[- ]?step|end[- ]?to[- ]?end|full[- ]?stack|cross[- ]?(file|domain|module)'
    r'|approved plan|run the pipeline|handoff to agents?)\b'
    r'|(执行|实施|实现|构建|交付|完成|编排|协调).{0,30}(计划|方案|功能|工作流|流水线|任务|改动|修改|修复|重构|智能体|代理)'
    r'|(迭代|优化|增强|改进).{0,30}(工作流|流水线|流程|编排|触发|技能|智能体|代理)'
    r'|(多步骤|端到端|全栈|跨文件|跨模块|跨领域|已批准的计划|执行计划|运行流水线)'
)

DEDICATED_PLAN_PATTERN = re.compile(
    r"(?:/plan\b|\bplan\s+mode\b|"
    r"\bneed\s+a\s+plan\b|\bhelp\s+me\s+plan\b|\bplan\s+first\b|"
    r"\bplanning\b|\bplan\s+(?:a|an|the|this)\b|\boutline\b|\bnext\s+steps\b|"
    r"\bmulti[- ]step\s+plan\b|\bcross[- ]?domain\s+plan\b|"
    r"\barchitecture\s+plan\b|\broadmap\b|\borchestrat(?:e|ion)\s+plan\b)",
    re.IGNORECASE,
)

ROUTING_RULES = [
    (EXTERNAL_SOURCE_PATTERN, 'workflow-intake', 'External workflow intake detected'),
    (COORDINATED_DELIVERY_PATTERN, 'dev-orchestrator', 'Coordinated implementation detected'),
    (r'\b(debug|fix|broken|crash|error|failing|bug)\b', 'systematic-debugging', 'Debug pattern detected'),
    (r'\b(review|code.?quality|refactor|clean.?up)\b', 'code-quality', 'Review pattern detected'),
    (r'\b(test|spec|coverage|unit.?test|integration.?test)\b', 'testing-strategy', 'Testing pattern detected'),
    (r'\b(plan|architect|design|blueprint)\b', 'plan', 'Planning pattern detected'),
    (r'\b(brainstorm|idea|explore|spike)\b', 'brainstorming', 'Brainstorm pattern detected'),
    (r'\b(verify|acceptance|done|complete|ship)\b', 'verification-before-completion', 'Verification pattern detected'),
    (r'\b(write|create|implement|build|add)\b.*\b(plan|spec|design)\b', 'writing-plans', 'Plan writing detected'),
]

# Skip routing if these are present (already routed by other hooks)
SKIP_PATTERNS = [
    r'^\s*/',  # slash commands already routed
    r'\b(ulw|ultrawork|uli)\b',  # autonomous modes handled by dedicated hooks
]


def route_keywords(prompt_text):
    """Match prompt against routing rules, return skill suggestions."""
    if not prompt_text or not prompt_text.strip():
        return None

    # Skip if already routed
    for pattern in SKIP_PATTERNS:
        if re.search(pattern, prompt_text, re.IGNORECASE):
            return None

    # Let the dedicated plan hook own planning prompts so the model
    # does not receive two independent skill suggestions for one task.
    if DEDICATED_PLAN_PATTERN.search(prompt_text):
        return None

    matches = []
    for pattern, skill, reason in ROUTING_RULES:
        if re.search(pattern, prompt_text, re.IGNORECASE):
            matches.append((skill, reason))

    if not matches:
        return None

    # Return first match (highest priority)
    skill, reason = matches[0]
    return (
        f"[keyword-router] {reason}. Primary skill: {skill}. "
        "Use this route unless the active command/skill explicitly asks for a companion skill; "
        "do not invoke using-claude-code-flow just to re-check routing."
    )


def main():
    try:
        input_data = json.loads(sys.stdin.read())
    except (json.JSONDecodeError, EOFError):
        sys.exit(0)

    prompt = input_data.get("prompt", "")
    result = route_keywords(prompt)

    if result:
        output = {
            "hookSpecificOutput": {
                "hookEventName": "UserPromptSubmit",
                "additionalContext": result
            }
        }
        print(json.dumps(output))
    else:
        print("{}")


if __name__ == "__main__":
    main()
