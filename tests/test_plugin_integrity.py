import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read_text(path):
    return path.read_text(encoding="utf-8")


def frontmatter(path):
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n", read_text(path), re.S)
    if not match:
        raise AssertionError(f"missing YAML frontmatter: {path}")
    return match.group(1)


def frontmatter_dict(path):
    data = {}
    for line in frontmatter(path).splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        data[key.strip()] = value.strip().strip('"')
    return data


class PluginIntegrityTests(unittest.TestCase):
    def test_plugin_metadata_and_hooks_json_parse(self):
        for rel in [
            ".claude-plugin/plugin.json",
            ".claude-plugin/marketplace.json",
            "hooks/hooks.json",
        ]:
            with self.subTest(file=rel):
                json.loads(read_text(ROOT / rel))

    def test_markdown_assets_have_required_frontmatter(self):
        paths = []
        paths.extend((ROOT / "agents").glob("*.md"))
        paths.extend((ROOT / "commands").glob("*.md"))
        paths.extend((ROOT / "skills").glob("*/SKILL.md"))

        self.assertGreater(len(paths), 0, "expected plugin markdown assets")

        for path in paths:
            with self.subTest(file=path.relative_to(ROOT).as_posix()):
                fm = frontmatter(path)
                self.assertRegex(fm, r"(?m)^name:\s*.+")
                self.assertRegex(fm, r"(?m)^description:\s*.+")

    def test_figma_skills_are_built_in(self):
        expected = {
            "figma",
            "figma-code-connect-components",
            "figma-create-design-system-rules",
            "figma-create-new-file",
            "figma-generate-design",
            "figma-generate-library",
            "figma-implement-design",
            "figma-use",
        }

        for skill in expected:
            with self.subTest(skill=skill):
                self.assertTrue((ROOT / "skills" / skill / "SKILL.md").exists())

        self.assertFalse((ROOT / "temp").exists())

    def test_web_search_skill_removed(self):
        removed_skill = "web" + "-search"
        self.assertFalse((ROOT / "skills" / removed_skill).exists())

        text_paths = [
            *ROOT.glob("*.md"),
            *ROOT.glob("commands/*.md"),
            *ROOT.glob("skills/**/*.md"),
            *ROOT.glob("hooks/scripts/*.py"),
        ]
        banned_terms = ["tav" + "ily", "trav" + "ily", removed_skill, "~~" + removed_skill, "Web" + "Search", "TAV" + "ILY"]
        banned = re.compile("|".join(re.escape(term) for term in banned_terms), re.I)
        for path in text_paths:
            with self.subTest(file=path.relative_to(ROOT).as_posix()):
                self.assertIsNone(banned.search(read_text(path)))

    def test_hooks_reference_existing_scripts(self):
        hooks = json.loads(read_text(ROOT / "hooks/hooks.json"))
        commands = []
        for entries in hooks.get("hooks", {}).values():
            for entry in entries:
                for hook in entry.get("hooks", []):
                    command = hook.get("command", "")
                    if command:
                        commands.append(command)

        self.assertGreater(len(commands), 0, "expected hook commands")

        for command in commands:
            for rel in re.findall(r"\$\{CLAUDE_PLUGIN_ROOT\}/([^\s]+)", command):
                with self.subTest(command=command):
                    self.assertTrue((ROOT / rel).exists(), f"missing hook target: {rel}")

        hooks_text = read_text(ROOT / "hooks/hooks.json")
        self.assertIn("plan-detector.py", hooks_text)
        self.assertIn("plan-mode-guard.py", hooks_text)
        self.assertIn('"matcher": "EnterPlanMode"', hooks_text)
        self.assertTrue((ROOT / "hooks/scripts/plan-detector.py").exists())
        old_plan_command = "workflow" + "-plan"
        self.assertFalse((ROOT / "commands" / f"{old_plan_command}.md").exists())
        self.assertTrue((ROOT / "hooks/scripts/plan-mode-guard.py").exists())

        plan_cmd = read_text(ROOT / "commands/plan.md")
        workflow_status = read_text(ROOT / "commands/workflow-status.md")
        write_plan = read_text(ROOT / "commands/write-plan.md")
        using_flow = read_text(ROOT / "skills/using-claude-code-flow/SKILL.md")
        orchestrator = read_text(ROOT / "skills/dev-orchestrator/SKILL.md")
        writing_plans = read_text(ROOT / "skills/writing-plans/SKILL.md")
        readme = read_text(ROOT / "README.md")
        claude_md = read_text(ROOT / "CLAUDE.md")
        guard_text = read_text(ROOT / "hooks/scripts/plan-mode-guard.py")

        self.assertIn("/plan [--mode", plan_cmd)
        self.assertIn("EnterPlanMode", plan_cmd)
        self.assertIn("host plan mode", plan_cmd.lower())
        self.assertIn("plugin-side replacement", plan_cmd)
        self.assertIn("Plugin workflow active", workflow_status)
        self.assertIn("structured plan state", workflow_status.lower())
        self.assertIn("plan-state.json", write_plan)
        self.assertIn("plan-init", write_plan)
        self.assertIn("Use /plan instead.", guard_text)
        self.assertIn("avoid `EnterPlanMode`", using_flow)
        self.assertIn("prefer `plan`", using_flow.lower())
        self.assertIn("plan-state.json", orchestrator)
        self.assertIn("plan-brief.md", orchestrator)
        self.assertIn("workflow-state.json", orchestrator)
        self.assertIn("context envelope", writing_plans.lower())
        self.assertIn("source of truth", writing_plans.lower())
        self.assertIn("plan-state.json", readme.lower())
        self.assertIn("plan_hash", readme)
        self.assertIn("host-level plan transitions", readme.lower())
        self.assertIn("PreToolUse(EnterPlanMode)", claude_md)
        self.assertIn("Shift+Tab", claude_md)
        self.assertIn("`/plan` is the plugin planning entry", claude_md)
        self.assertNotIn(old_plan_command, claude_md)

    def test_python_hook_scripts_compile(self):
        scripts = sorted((ROOT / "hooks/scripts").glob("*.py"))
        self.assertGreater(len(scripts), 0, "expected Python hook scripts")

        for path in scripts:
            with self.subTest(file=path.relative_to(ROOT).as_posix()):
                compile(read_text(path), str(path), "exec")

    def test_keyword_router_prefers_dev_orchestrator_for_coordinated_delivery(self):
        script = ROOT / "hooks/scripts/keyword-router.py"
        prompts = [
            "execute the approved plan and coordinate agents",
            "implement this full-stack feature end-to-end",
            "build the multi-step workflow changes",
            "执行这个计划",
            "实现这个全栈功能",
            "迭代优化当前工作流",
        ]

        for prompt in prompts:
            with self.subTest(prompt=prompt):
                result = subprocess.run(
                    [sys.executable, str(script)],
                    input=json.dumps({"prompt": prompt}),
                    text=True,
                    capture_output=True,
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn("dev-orchestrator", result.stdout)

    def test_planning_prompts_are_owned_by_plan_detector(self):
        keyword_router = ROOT / "hooks/scripts/keyword-router.py"
        plan_detector = ROOT / "hooks/scripts/plan-detector.py"
        prompt = "I need to plan a multi-step feature that touches UI and backend files."

        keyword_result = subprocess.run(
            [sys.executable, str(keyword_router)],
            input=json.dumps({"prompt": prompt}),
            text=True,
            capture_output=True,
        )
        self.assertEqual(keyword_result.returncode, 0, keyword_result.stderr)
        self.assertEqual(json.loads(keyword_result.stdout), {})

        workflow_result = subprocess.run(
            [sys.executable, str(plan_detector)],
            input=json.dumps({"prompt": prompt}),
            text=True,
            capture_output=True,
        )
        self.assertEqual(workflow_result.returncode, 0, workflow_result.stderr)
        output = json.loads(workflow_result.stdout)
        self.assertIn("system_prompt_append", output)
        self.assertIn("Primary route: `/plan`", output["system_prompt_append"])
        self.assertIn("Do not separately invoke `using-claude-code-flow`", output["system_prompt_append"])

    def test_plan_detector_does_not_steal_other_slash_commands(self):
        script = ROOT / "hooks/scripts/plan-detector.py"
        for prompt in ["/brainstorm Improve onboarding", "/write-plan approved-spec.md", "/execute-plan plan.md", "/quick-fix Fix typo"]:
            with self.subTest(prompt=prompt):
                result = subprocess.run(
                    [sys.executable, str(script)],
                    input=json.dumps({"prompt": prompt}),
                    text=True,
                    capture_output=True,
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stdout, "")

    def test_keyword_router_scopes_workflow_intake_to_external_sources(self):
        script = ROOT / "hooks/scripts/keyword-router.py"

        result = subprocess.run(
            [sys.executable, str(script)],
            input=json.dumps({"prompt": "参考 https://github.com/example/agent-pack 优化工作流"}),
            text=True,
            capture_output=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("workflow-intake", result.stdout)

        false_positive_prompts = [
            "copy this text",
            "import the library",
        ]
        for prompt in false_positive_prompts:
            with self.subTest(prompt=prompt):
                result = subprocess.run(
                    [sys.executable, str(script)],
                    input=json.dumps({"prompt": prompt}),
                    text=True,
                    capture_output=True,
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertNotIn("workflow-intake", result.stdout)

        result = subprocess.run(
            [sys.executable, str(script)],
            input=json.dumps({"prompt": "import the data and implement the feature"}),
            text=True,
            capture_output=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("dev-orchestrator", result.stdout)

    def test_keyword_router_does_not_route_to_removed_web_search_skill(self):
        script = ROOT / "hooks/scripts/keyword-router.py"
        removed_skill = "web" + "-search"
        result = subprocess.run(
            [sys.executable, str(script)],
            input=json.dumps({"prompt": "look up the latest docs for this library"}),
            text=True,
            capture_output=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn(removed_skill, result.stdout)

    def test_shell_scripts_are_lf_only(self):
        scripts = list((ROOT / "hooks/scripts").glob("*.sh"))
        scripts.extend((ROOT / "scripts").glob("*.sh"))
        self.assertGreater(len(scripts), 0, "expected shell scripts")

        for path in scripts:
            with self.subTest(file=path.relative_to(ROOT).as_posix()):
                data = path.read_bytes()
                self.assertNotIn(b"\r\n", data, "shell scripts must use LF for bash compatibility")

    def test_gitattributes_pins_shell_scripts_to_lf(self):
        content = read_text(ROOT / ".gitattributes")
        self.assertIn("*.sh text eol=lf", content)

    def test_agent_model_effort_configuration_is_valid(self):
        expected_model = {
            "forge": "sonnet",
            "oracle": "opus",
            "prism": "sonnet",
            "sentinel": "sonnet",
            "artist": "haiku",
        }
        expected_effort = {
            "forge": "high",
            "oracle": "xhigh",
            "prism": "high",
            "sentinel": "high",
        }
        allowed_effort = {"low", "medium", "high", "xhigh", "max"}

        for path in sorted((ROOT / "agents").glob("*.md")):
            with self.subTest(file=path.relative_to(ROOT).as_posix()):
                fm = frontmatter_dict(path)
                name = fm["name"]
                model = fm.get("model")
                effort = fm.get("effort")

                self.assertEqual(model, expected_model[name])
                if model == "haiku":
                    # haiku agents may use medium effort for iterative tasks (e.g. image generation)
                    if effort is not None:
                        self.assertEqual(effort, "medium", "haiku agents may only use medium effort")
                else:
                    self.assertEqual(effort, expected_effort[name])
                    self.assertIn(effort, allowed_effort)

    def test_flow_state_get_merges_partial_state_with_defaults(self):
        with tempfile.TemporaryDirectory() as tmp:
            flow_dir = Path(tmp) / ".claude" / "flow"
            flow_dir.mkdir(parents=True)
            (flow_dir / "workflow-state.json").write_text(
                json.dumps({"verification_count": 2}),
                encoding="utf-8",
            )

            result = subprocess.run(
                [sys.executable, str(ROOT / "hooks/scripts/flow-state.py"), "get"],
                cwd=tmp,
                text=True,
                capture_output=True,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            state = json.loads(result.stdout)
            self.assertEqual(state["phase"], "idle")
            self.assertEqual(state["mode"], "standard")
            self.assertEqual(state["verification_count"], 2)
            self.assertIn("last_verification", state)

    def test_plan_state_round_trip(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "hooks/scripts/flow-state.py"),
                    "plan-init",
                    json.dumps(
                        {
                            "title": "Ship structured plans",
                            "goal": "Move planning state into script-managed JSON",
                            "tasks": [
                                {
                                    "title": "Add plan state",
                                    "test_command": "python -m unittest tests.test_plugin_integrity",
                                    "acceptance": ["plan state exists"],
                                },
                                {
                                    "title": "Export plan brief",
                                    "depends_on": [1],
                                    "acceptance": ["brief renders"],
                                },
                            ],
                        }
                    ),
                ],
                cwd=tmp,
                text=True,
                capture_output=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)

            state_path = Path(tmp) / ".claude" / "flow" / "workflow-state.json"
            plan_path = Path(tmp) / ".claude" / "flow" / "plan-state.json"
            brief_path = Path(tmp) / ".claude" / "flow" / "plan-brief.md"

            state = json.loads(state_path.read_text(encoding="utf-8"))
            plan = json.loads(plan_path.read_text(encoding="utf-8"))
            self.assertEqual(state["plan_hash"], plan["plan_hash"])
            self.assertEqual(state["plan_status"], "draft")
            self.assertEqual(state["plan_title"], "Ship structured plans")
            self.assertEqual(state["plan_task_total"], 2)

            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "hooks/scripts/flow-state.py"),
                    "plan-approve",
                    "Approved for execution",
                ],
                cwd=tmp,
                text=True,
                capture_output=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)

            state = json.loads(state_path.read_text(encoding="utf-8"))
            plan = json.loads(plan_path.read_text(encoding="utf-8"))
            brief = brief_path.read_text(encoding="utf-8")
            self.assertEqual(plan["status"], "approved")
            self.assertTrue(plan["approved"])
            self.assertEqual(state["plan_status"], "approved")
            self.assertEqual(state["plan_hash"], plan["plan_hash"])
            self.assertIn("# Ship structured plans Implementation Plan", brief)
            self.assertIn("**Goal:** Move planning state into script-managed JSON", brief)
            self.assertIn("### Task 1: Add plan state", brief)
            self.assertIn("### Task 2: Export plan brief", brief)
            self.assertIn("**Depends on:** 1", brief)

    def test_track_verification_records_bash_evidence(self):
        payload = {
            "tool_input": {"command": "npm test -- --runInBand"},
            "tool_response": {"exit_code": 0},
        }

        with tempfile.TemporaryDirectory() as tmp:
            result = subprocess.run(
                [sys.executable, str(ROOT / "hooks/scripts/track-verification.py")],
                cwd=tmp,
                input=json.dumps(payload),
                text=True,
                capture_output=True,
            )

            self.assertEqual(result.returncode, 0, result.stderr)

            flow_dir = Path(tmp) / ".claude" / "flow"
            evidence = json.loads((flow_dir / "last-verification.json").read_text(encoding="utf-8"))
            self.assertEqual(evidence["kind"], ["test"])
            self.assertEqual(evidence["status"], "pass")
            self.assertEqual(evidence["exit_code"], 0)

            state = json.loads((flow_dir / "workflow-state.json").read_text(encoding="utf-8"))
            self.assertEqual(state["verification_count"], 1)
            self.assertEqual(state["last_verification"]["status"], "pass")

    def test_metrics_collects_verification_counts(self):
        with tempfile.TemporaryDirectory() as tmp:
            flow_dir = Path(tmp) / ".claude" / "flow"
            flow_dir.mkdir(parents=True)
            entries = [
                {"ts": "2026-04-29T00:00:00Z", "session_id": "s1", "event": "session_start"},
                {"ts": "2026-04-29T00:00:01Z", "session_id": "s1", "event": "verification_evidence", "kind": ["test"], "status": "pass"},
                {"ts": "2026-04-29T00:00:02Z", "session_id": "s1", "event": "verification_evidence", "kind": ["build"], "status": "fail"},
            ]
            (flow_dir / "exec-log.jsonl").write_text(
                "\n".join(json.dumps(entry) for entry in entries) + "\n",
                encoding="utf-8",
            )

            result = subprocess.run(
                [sys.executable, str(ROOT / "hooks/scripts/metrics.py"), "collect"],
                cwd=tmp,
                text=True,
                capture_output=True,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            metrics = json.loads(result.stdout)
            self.assertEqual(metrics["verification_count"], 2)
            self.assertEqual(metrics["verification_failures"], 1)
            self.assertEqual(metrics["verification_by_kind"]["test"], 1)
            self.assertEqual(metrics["verification_by_kind"]["build"], 1)

    def test_metrics_collect_ignores_entries_without_session_id(self):
        with tempfile.TemporaryDirectory() as tmp:
            flow_dir = Path(tmp) / ".claude" / "flow"
            flow_dir.mkdir(parents=True)
            entries = [
                {"ts": "2026-04-29T00:00:00Z", "session_id": None, "event": "session_start"},
                {"ts": "2026-04-29T00:00:01Z", "session_id": None, "event": "verification_evidence", "kind": ["git"], "status": "unknown"},
                {"ts": "2026-04-29T00:00:02Z", "session_id": "s1", "event": "session_start"},
                {"ts": "2026-04-29T00:00:03Z", "session_id": "s1", "event": "verification_evidence", "kind": ["test"], "status": "pass"},
            ]
            (flow_dir / "exec-log.jsonl").write_text(
                "\n".join(json.dumps(entry) for entry in entries) + "\n",
                encoding="utf-8",
            )

            result = subprocess.run(
                [sys.executable, str(ROOT / "hooks/scripts/metrics.py"), "collect"],
                cwd=tmp,
                text=True,
                capture_output=True,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            metrics = json.loads(result.stdout)
            self.assertEqual(metrics["session_id"], "s1")
            self.assertEqual(metrics["verification_count"], 1)
            self.assertEqual(metrics["verification_by_kind"]["test"], 1)


    def test_memory_inject_missing_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = subprocess.run(
                [sys.executable, str(ROOT / "hooks/scripts/memory-inject.py")],
                cwd=tmp,
                text=True,
                capture_output=True,
            )
            self.assertEqual(result.returncode, 0)
            self.assertEqual(result.stdout, "")

    def test_memory_inject_empty_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            memory_dir = Path(tmp) / ".claude" / "memory"
            memory_dir.mkdir(parents=True)
            (memory_dir / "project-context.md").write_text("", encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(ROOT / "hooks/scripts/memory-inject.py")],
                cwd=tmp,
                text=True,
                capture_output=True,
            )
            self.assertEqual(result.returncode, 0)
            self.assertEqual(result.stdout, "")

    def test_memory_inject_with_content(self):
        with tempfile.TemporaryDirectory() as tmp:
            memory_dir = Path(tmp) / ".claude" / "memory"
            memory_dir.mkdir(parents=True)
            (memory_dir / "project-context.md").write_text("# My Project\n\nActive sprint: v2.", encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(ROOT / "hooks/scripts/memory-inject.py")],
                cwd=tmp,
                text=True,
                capture_output=True,
            )
            self.assertEqual(result.returncode, 0)
            self.assertIn("PROJECT_MEMORY:", result.stdout)
            self.assertIn("Active sprint: v2.", result.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)
