"""Tests for hooks/scripts/keyword-router.py."""

import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "hooks" / "scripts" / "keyword-router.py"


def _route(prompt):
    payload = json.dumps({"prompt": prompt})
    r = subprocess.run(
        [sys.executable, str(SCRIPT)],
        input=payload, capture_output=True, text=True, timeout=10,
    )
    if not r.stdout.strip() or r.stdout.strip() == "{}":
        return None
    data = json.loads(r.stdout)
    return data.get("hookSpecificOutput", {}).get("additionalContext", "")


class SpecificRouting(unittest.TestCase):
    """Known patterns route to their dedicated skills."""

    def test_debug_routes_to_systematic(self):
        ctx = _route("fix this crash in the login module")
        self.assertIn("systematic-debugging", ctx)

    def test_review_routes_to_code_review(self):
        ctx = _route("review the auth changes")
        self.assertIn("code-review", ctx)

    def test_plan_keyword_skipped(self):
        ctx = _route("plan a new feature")
        self.assertIsNone(ctx)

    def test_slash_command_skipped(self):
        ctx = _route("/plan implement auth")
        self.assertIsNone(ctx)


class DefaultRouting(unittest.TestCase):
    """Non-trivial non-question prompts → dev-orchestrator."""

    def test_implement_task(self):
        ctx = _route("implement user authentication with JWT")
        self.assertIn("dev-orchestrator", ctx)
        self.assertIn("Default entry", ctx)

    def test_short_task(self):
        ctx = _route("add a logout button to the header")
        self.assertIn("dev-orchestrator", ctx)

    def test_chinese_task(self):
        ctx = _route("实现用户登录功能并添加单元测试")
        self.assertIn("dev-orchestrator", ctx)

    def test_multi_word_action(self):
        ctx = _route("create a new API endpoint for payments")
        self.assertIn("dev-orchestrator", ctx)


class NoRouting(unittest.TestCase):
    """Short or question prompts get no routing."""

    def test_question_mark(self):
        ctx = _route("how does the auth middleware work?")
        self.assertIsNone(ctx)

    def test_chinese_question_mark(self):
        ctx = _route("这个函数是做什么的？")
        self.assertIsNone(ctx)

    def test_question_word_start(self):
        ctx = _route("what is the best way to handle errors")
        self.assertIsNone(ctx)

    def test_too_short(self):
        ctx = _route("ok")
        self.assertIsNone(ctx)

    def test_empty(self):
        ctx = _route("")
        self.assertIsNone(ctx)

    def test_show_me(self):
        ctx = _route("show me the auth module")
        self.assertIsNone(ctx)

    def test_explain(self):
        ctx = _route("explain how the pipeline works")
        self.assertIsNone(ctx)


class PriorityOverride(unittest.TestCase):
    """Specific patterns take priority over default."""

    def test_debug_over_default(self):
        ctx = _route("debug the failing payment integration test")
        self.assertIn("systematic-debugging", ctx)
        self.assertNotIn("Default entry", ctx)

    def test_review_over_default(self):
        ctx = _route("review the refactored code quality in the API layer")
        self.assertIn("code-review", ctx)
        self.assertNotIn("Default entry", ctx)


if __name__ == "__main__":
    unittest.main()
