import json
import os
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
    def test_local_runtime_mirrors_are_ignored(self):
        ignore_text = read_text(ROOT / ".gitignore")
        for rel in [".claude/", ".codex/", ".agents/"]:
            with self.subTest(path=rel):
                self.assertIn(rel, ignore_text)

    def test_plugin_metadata_and_hooks_json_parse(self):
        for rel in [
            ".claude-plugin/plugin.json",
            ".claude-plugin/marketplace.json",
            ".codex-plugin/plugin.json",
            ".agents/plugins/marketplace.json",
            "hooks/codex-hooks.json",
            "hooks/hooks.json",
        ]:
            with self.subTest(file=rel):
                json.loads(read_text(ROOT / rel))

    def test_codex_manifest_exposes_skills_and_hooks(self):
        manifest = json.loads(read_text(ROOT / ".codex-plugin/plugin.json"))
        self.assertEqual(manifest["name"], "claude-code-flow")
        self.assertEqual(manifest["skills"], "./skills/")
        self.assertEqual(manifest["hooks"], "./hooks/codex-hooks.json")
        self.assertEqual(manifest["mcpServers"], "./.mcp.json")
        self.assertEqual(manifest["license"], "MIT")

        interface = manifest["interface"]
        self.assertEqual(interface["displayName"], "Claude Code Flow")
        self.assertEqual(interface["category"], "Productivity")
        self.assertIn("Interactive", interface["capabilities"])
        self.assertLessEqual(len(interface["defaultPrompt"]), 3)
        for prompt in interface["defaultPrompt"]:
            self.assertLessEqual(len(prompt), 128)

        hooks = json.loads(read_text(ROOT / "hooks/codex-hooks.json"))
        commands = []
        for entries in hooks.get("hooks", {}).values():
            for entry in entries:
                for hook in entry.get("hooks", []):
                    command = hook.get("command", "")
                    if command:
                        commands.append(command)

        self.assertGreater(len(commands), 0, "expected Codex hook commands")
        for command in commands:
            with self.subTest(command=command):
                self.assertIn("${PLUGIN_ROOT}", command)
                self.assertNotIn("${CLAUDE_PLUGIN_ROOT}", command)
                self.assertNotRegex(command, r"^\s*bash\b")
                for rel in re.findall(r"\$\{PLUGIN_ROOT\}/([^\s]+)", command):
                    self.assertTrue((ROOT / rel).exists(), f"missing hook target: {rel}")

    def test_claude_and_codex_share_root_skills_and_agents(self):
        claude_manifest = json.loads(read_text(ROOT / ".claude-plugin/plugin.json"))
        codex_manifest = json.loads(read_text(ROOT / ".codex-plugin/plugin.json"))

        self.assertEqual(codex_manifest["skills"], "./skills/")
        self.assertTrue((ROOT / "skills/dev-orchestrator/SKILL.md").exists())
        self.assertNotIn("skills", claude_manifest)

        root_agents = sorted(path.stem for path in (ROOT / "agents").glob("*.md"))
        self.assertEqual(root_agents, ["forge", "oracle", "prism", "sentinel"])
        self.assertFalse((ROOT / ".claude" / "agents").exists())
        self.assertFalse((ROOT / ".codex" / "agents").exists())

        overlay = read_text(ROOT / "skills/dev-orchestrator/agents/openai.yaml")
        self.assertIn("display_name: \"Claude Code Flow Agents\"", overlay)
        self.assertIn('source: "../../../agents"', overlay)
        for agent in root_agents:
            self.assertIn(f"    - {agent}", overlay)

    def test_codex_shared_surfaces_use_host_neutral_root_in_commands(self):
        codex_loaded_paths = [
            *ROOT.glob("skills/**/*.md"),
            *ROOT.glob("agents/*.md"),
        ]
        command_re = re.compile(r"`[^`]*(?:python|bash|node|npx)\s+\$\{CLAUDE_PLUGIN_ROOT\}[^`]*`")
        for path in codex_loaded_paths:
            with self.subTest(file=path.relative_to(ROOT).as_posix()):
                self.assertIsNone(command_re.search(read_text(path)))

    def test_codex_marketplace_points_to_this_plugin(self):
        marketplace = json.loads(read_text(ROOT / ".agents/plugins/marketplace.json"))
        self.assertEqual(marketplace["name"], "claude-code-flow")
        self.assertEqual(marketplace["interface"]["displayName"], "Claude Code Flow")

        entries = marketplace["plugins"]
        self.assertEqual(len(entries), 1)
        entry = entries[0]
        self.assertEqual(entry["name"], "claude-code-flow")
        self.assertEqual(entry["source"], {"source": "local", "path": "../.."})
        self.assertEqual(
            entry["policy"],
            {"installation": "AVAILABLE", "authentication": "ON_INSTALL"},
        )
        self.assertEqual(entry["category"], "Productivity")
        plugin_manifest = (
            ROOT / ".agents/plugins" / entry["source"]["path"] / ".codex-plugin/plugin.json"
        ).resolve()
        self.assertTrue(plugin_manifest.exists())

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
        workflow_metrics = read_text(ROOT / "commands/workflow-metrics.md")
        workflow_timeline = read_text(ROOT / "commands/workflow-timeline.md")
        code_review = read_text(ROOT / "commands/code-review.md")
        workflow_review = read_text(ROOT / "commands/workflow-review.md")
        write_plan = read_text(ROOT / "commands/write-plan.md")
        orchestrator = read_text(ROOT / "skills/dev-orchestrator/SKILL.md")
        diagnostics = read_text(ROOT / "skills/dev-orchestrator/references/diagnostics.md")
        review_reference = read_text(ROOT / "skills/dev-orchestrator/references/review.md")
        pipeline_operations = read_text(ROOT / "skills/dev-orchestrator/references/pipeline-operations.md")
        writing_plans = read_text(ROOT / "skills/planning/SKILL.md")
        readme = read_text(ROOT / "README.md")
        claude_md = read_text(ROOT / "CLAUDE.md")
        agents_md = read_text(ROOT / "AGENTS.md")
        guard_text = read_text(ROOT / "hooks/scripts/plan-mode-guard.py")
        plan_detector = read_text(ROOT / "hooks/scripts/plan-detector.py")

        self.assertIn("/plan [--mode", plan_cmd)
        self.assertIn("EnterPlanMode", plan_cmd)
        self.assertIn("host plan mode", plan_cmd.lower())
        self.assertIn("plugin-side replacement", plan_cmd)
        self.assertIn("Plugin workflow active", workflow_status)
        self.assertIn("structured plan state", workflow_status.lower())
        self.assertIn("plan-state.json", write_plan)
        self.assertIn("plan-init", write_plan)
        self.assertIn("Use /plan instead.", guard_text)
        self.assertIn("enforce the plan command hard stops", plan_detector)
        self.assertIn("applicable design artifacts", plan_detector)
        self.assertIn("avoid `EnterPlanMode`", orchestrator)
        self.assertIn("prefer `plan`", orchestrator.lower())
        self.assertIn("plan-state.json", orchestrator)
        self.assertIn("plan-brief.md", orchestrator)
        self.assertIn("workflow-state.json", orchestrator)
        self.assertIn("context envelope", writing_plans.lower())
        self.assertIn("source of truth", writing_plans.lower())
        self.assertIn("plan-state.json", readme.lower())
        self.assertIn("plan_hash", readme)
        self.assertIn("host-level plan transitions", readme.lower())
        self.assertIn("Source of Truth", readme)
        self.assertNotIn(".claude/skills", claude_md)
        self.assertNotIn(".claude/skills", agents_md)
        self.assertIn("Source of Truth", claude_md)
        self.assertIn("Source of Truth", agents_md)
        self.assertIn("Shift+Tab", claude_md)
        self.assertIn("`/plan` is the plugin planning entry", claude_md)
        self.assertNotIn(old_plan_command, claude_md)

        self.assertIn("skills/dev-orchestrator/references/pipeline-operations.md", plan_cmd)
        self.assertIn("Source of Truth", plan_cmd)
        for duplicated_gate_detail in [
            "Research (if checked)",
            "Reference Intake (if checked)",
            "Document auto-review",
            "UI Research (if checked",
            "NEVER use `subagent_type",
        ]:
            self.assertNotIn(duplicated_gate_detail, plan_cmd)

        self.assertIn("Workflow Diagnostics Reference", diagnostics)
        self.assertIn("metrics.py collect", diagnostics)
        for diagnostic_cmd in [workflow_status, workflow_metrics, workflow_timeline]:
            self.assertIn("skills/dev-orchestrator/references/diagnostics.md", diagnostic_cmd)
            self.assertIn("read-only command", diagnostic_cmd.lower())
        for duplicated_diagnostic_detail in [
            "Read `.claude/flow/workflow-state.json` and `.claude/flow/plan-state.json`",
            "Color-code by event type",
            "### Session Overview",
            "### Agent Efficiency",
            "### Guard Activity",
        ]:
            self.assertNotIn(duplicated_diagnostic_detail, workflow_status)
            self.assertNotIn(duplicated_diagnostic_detail, workflow_metrics)
            self.assertNotIn(duplicated_diagnostic_detail, workflow_timeline)

        self.assertIn("Review Workflow Reference", review_reference)
        self.assertIn("Sentinel Dispatch Contract", review_reference)
        self.assertIn("Stop after 3 review rounds", review_reference)
        self.assertIn("skills/dev-orchestrator/references/review.md", code_review)
        self.assertIn("skills/dev-orchestrator/references/review.md", workflow_review)
        self.assertIn("references/review.md", pipeline_operations)
        self.assertIn("skills/dev-orchestrator/references/review.md", readme)
        self.assertIn("skills/dev-orchestrator/references/review.md", claude_md)
        self.assertIn("skills/dev-orchestrator/references/review.md", agents_md)
        for duplicated_review_detail in [
            "Identify review target",
            "Gather context",
            "Max Review Rounds",
            "Critical issues (must fix)",
            "Warnings (should fix)",
            "Suggestions (nice to have)",
            "Verified understanding of each feedback item",
        ]:
            self.assertNotIn(duplicated_review_detail, code_review)
            self.assertNotIn(duplicated_review_detail, workflow_review)

    def test_top_level_docs_do_not_duplicate_workflow_tables(self):
        docs = {
            "README.md": read_text(ROOT / "README.md"),
            "CLAUDE.md": read_text(ROOT / "CLAUDE.md"),
            "AGENTS.md": read_text(ROOT / "AGENTS.md"),
        }
        forbidden = [
            "| Agent | Model | Effort",
            "Plan + Architecture (oracle)",
            "Testing + Acceptance (prism)",
            "| Mode | Research | Architecture",
            "| Mode | Use Case | Research",
            "| Event | Purpose |",
            "SubagentStart / SubagentStop",
        ]
        for name, text in docs.items():
            for phrase in forbidden:
                with self.subTest(file=name, phrase=phrase):
                    self.assertNotIn(phrase, text)

    def test_readme_is_clean_utf8_without_mojibake(self):
        readme = read_text(ROOT / "README.md")
        mojibake_markers = [
            "\ufffd",
            "\u9239",
            "\u4e63",
            "\u6d5c\u5b22\u7584",
            "\u93cd\u5fc3",
            "\u935b\u4ee4\u62a4",
            "\u59af",
            "\u9396",
        ]
        for phrase in mojibake_markers:
            with self.subTest(phrase=phrase):
                self.assertNotIn(phrase, readme)

    def test_hook_manifests_match_renderer(self):
        for host in ["claude", "codex"]:
            with self.subTest(host=host):
                result = subprocess.run(
                    [sys.executable, str(ROOT / "scripts/render-hooks.py"), host, "--check"],
                    text=True,
                    capture_output=True,
                )
                self.assertEqual(result.returncode, 0, result.stderr or result.stdout)

    def test_python_hook_scripts_compile(self):
        scripts = sorted((ROOT / "hooks/scripts").glob("*.py"))
        scripts.extend(sorted((ROOT / "scripts").glob("*.py")))
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
        self.assertIn("Do not separately invoke `using-claude-code-flow`", output["system_prompt_append"])  # plan-detector still mentions old name for context

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

    def test_agent_completion_reads_root_agent_metadata(self):
        payload = {"name": "oracle"}

        with tempfile.TemporaryDirectory() as tmp:
            result = subprocess.run(
                [sys.executable, str(ROOT / "hooks/scripts/on-agent-complete.py")],
                cwd=tmp,
                input=json.dumps(payload),
                text=True,
                capture_output=True,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            log_path = Path(tmp) / ".claude" / "flow" / "exec-log.jsonl"
            entry = json.loads(log_path.read_text(encoding="utf-8").splitlines()[-1])
            self.assertEqual(entry["agent"], "oracle")
            self.assertEqual(entry["model"], "opus")

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
            namespaced_brief_path = Path(tmp) / ".claude" / "flow" / "plans" / "ship-structured-plans" / "plan-brief.md"
            phase_context_path = Path(tmp) / ".claude" / "flow" / "plans" / "ship-structured-plans" / "phase-context.md"

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
            namespaced_brief = namespaced_brief_path.read_text(encoding="utf-8")
            self.assertTrue(phase_context_path.exists())
            self.assertEqual(brief, namespaced_brief)
            self.assertEqual(plan["output_dir"], os.path.join(".claude", "flow", "plans", "ship-structured-plans"))
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

    def test_track_verification_records_python_test_evidence(self):
        commands = [
            "python -m unittest tests.test_plugin_integrity",
            "python tests/run-tests.py",
        ]

        for command in commands:
            with self.subTest(command=command):
                payload = {
                    "tool_input": {"command": command},
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
                    evidence = json.loads((Path(tmp) / ".claude" / "flow" / "last-verification.json").read_text(encoding="utf-8"))
                    self.assertEqual(evidence["kind"], ["test"])
                    self.assertEqual(evidence["status"], "pass")

    def test_orchestrator_references_harness_control_plane(self):
        orchestrator = read_text(ROOT / "skills/dev-orchestrator/SKILL.md")
        pipeline = read_text(ROOT / "skills/dev-orchestrator/references/pipeline-operations.md")
        dispatch = read_text(ROOT / "skills/dev-orchestrator/references/parallel-dispatch.md")
        prompts = read_text(ROOT / "skills/dev-orchestrator/references/subagent-prompts.md")

        self.assertIn("control plane", orchestrator.lower())
        self.assertIn("workflow-state.json", orchestrator)
        self.assertIn("verification-evidence.jsonl", orchestrator)
        self.assertIn("Policy Trace", pipeline)
        self.assertIn("Decision Trace", dispatch)
        self.assertIn("Handoff Artifact", prompts)

    def test_workflow_requires_documented_research_plan_and_md_self_review(self):
        pipeline = read_text(ROOT / "skills/dev-orchestrator/references/pipeline-operations.md")
        planning = read_text(ROOT / "skills/planning/SKILL.md")
        research = read_text(ROOT / "skills/research/SKILL.md")

        self.assertIn("local file inspection", pipeline.lower())
        self.assertIn("external research", pipeline.lower())
        self.assertIn("before plan", pipeline.lower())
        self.assertIn("before implementation", pipeline.lower())
        self.assertIn("Generated Markdown Document Review", pipeline)
        self.assertIn("self-review loop", pipeline.lower())
        self.assertIn("plan document", planning.lower())
        self.assertIn("Local Research", planning)
        self.assertIn("External Research", planning)
        self.assertIn("Self Review Result", planning)
        self.assertIn("research artifact", research.lower())

    def test_workflow_defines_lightweight_and_heavy_size_thresholds(self):
        orchestrator = read_text(ROOT / "skills/dev-orchestrator/SKILL.md")
        pipeline = read_text(ROOT / "skills/dev-orchestrator/references/pipeline-operations.md")
        dispatch = read_text(ROOT / "skills/dev-orchestrator/references/parallel-dispatch.md")
        prompts = read_text(ROOT / "skills/dev-orchestrator/references/subagent-prompts.md")

        self.assertIn("default to non-trivial", orchestrator)
        for allowed in [
            "changing only a few lines",
            "touching 1-2 files",
            "adding 1-2 small files",
        ]:
            self.assertIn(allowed, pipeline)
            self.assertIn(allowed, prompts)
        for trigger in [
            "more than 5 touched files",
            "more than 3 newly created files",
            "broad\n    behavior/workflow/prompt/hook/test changes",
            "architecture/UI changes",
            "design system website/multi-page UI request",
        ]:
            self.assertIn(trigger, pipeline)
        self.assertIn("touches more than 5 files", dispatch)
        self.assertIn("creates more than 3 files", dispatch)
        self.assertIn("1-2 small new files", dispatch)
        self.assertIn("design system website", dispatch)
        self.assertIn("multi-page UI", dispatch)
        self.assertIn("broad, high-impact, multi-step, cross-domain", orchestrator)
        self.assertIn("quality-sensitive", orchestrator)
        self.assertIn("outcome-oriented without exact implementation scope", orchestrator)
        self.assertIn("never quick/lightweight", orchestrator)
        self.assertIn("clarification", orchestrator)
        self.assertIn("applicable domain design", orchestrator)
        self.assertIn("Frontend/UI/site work is one example", orchestrator)
        self.assertIn("touches more than 5 files", prompts)
        self.assertIn("creates more than 3 files", prompts)
        self.assertIn("design system website", prompts)
        self.assertIn("2+ subtasks or acceptance checks", dispatch)
        self.assertNotIn("3+ subtasks or acceptance checks", dispatch)

    def test_long_task_harness_coordination_is_documented(self):
        pipeline = read_text(ROOT / "skills/dev-orchestrator/references/pipeline-operations.md")
        dispatch = read_text(ROOT / "skills/dev-orchestrator/references/parallel-dispatch.md")
        prompts = read_text(ROOT / "skills/dev-orchestrator/references/subagent-prompts.md")

        for required in ["TeamCreate", "TaskList", "SendMessage", "team_name", "stable", "idle"]:
            self.assertIn(required, dispatch + prompts + pipeline)
        self.assertIn("3+ task nodes", pipeline)
        self.assertIn("multiple dispatch waves", pipeline)
        self.assertIn("Team Mode Ritual", dispatch)
        self.assertIn("request the TaskList update", prompts)
        self.assertIn("orchestrator validates scope/evidence and performs `TaskUpdate`", prompts)

    def test_subagent_templates_use_handoff_artifacts_without_commits(self):
        prompts = read_text(ROOT / "skills/dev-orchestrator/references/subagent-prompts.md")

        self.assertNotIn("Commit your work", prompts)
        self.assertGreaterEqual(prompts.count("## Handoff Artifact"), 5)
        sections = ["## Forge (Implementer)", "## Sentinel Stage 1", "## Sentinel Stage 2", "## Prism", "## Research"]
        for section, next_section in zip(sections, sections[1:]):
            start = prompts.index(section)
            end = prompts.index(next_section)
            body = prompts[start:end]
            self.assertIn("## Handoff Artifact", body)
            self.assertIn("TaskList update", body)
            self.assertIn("run_in_background: true", body)
            for field in ["team_name", "taskId", "expected owner", "file scope", "completed dependencies", "may claim more tasks"]:
                self.assertIn(field, body)

    def test_external_research_is_materiality_scoped(self):
        pipeline = read_text(ROOT / "skills/dev-orchestrator/references/pipeline-operations.md")

        self.assertIn("Research MUST include local file inspection", pipeline)
        self.assertIn("Include external research only", pipeline)
        self.assertIn("materially affect the solution", pipeline)
        self.assertIn("when research is required", pipeline)

    def test_vague_requests_require_clarification(self):
        orchestrator = read_text(ROOT / "skills/dev-orchestrator/SKILL.md")
        pipeline = read_text(ROOT / "skills/dev-orchestrator/references/pipeline-operations.md")

        self.assertIn("requirements are vague or underspecified", orchestrator)
        self.assertIn("ask clarifying questions before classification or implementation", orchestrator)
        self.assertIn("Gate 0: Requirement Clarification", pipeline)
        self.assertIn("any\n    request is vague or underspecified", pipeline)
        self.assertIn("missing concrete scope, constraints", pipeline)
        self.assertIn("expected behavior", pipeline)
        self.assertIn("Do not answer \"I'll do the minimal version\"", pipeline)
        self.assertIn("what to build/change", pipeline)
        self.assertIn("acceptance\n    criteria", pipeline)
        self.assertIn("Product/UI/site/design-system\n    outcomes require extra care", pipeline)

    def test_quick_fix_cannot_claim_vague_or_broad_work(self):
        quick_fix = read_text(ROOT / "commands/quick-fix.md")

        self.assertIn("Broad, high-impact, multi-step, cross-domain", quick_fix)
        self.assertIn("quality-sensitive", quick_fix)
        self.assertIn("outcome-oriented requests", quick_fix)
        self.assertIn("exact implementation scope", quick_fix)
        self.assertIn("Vague or underspecified requests", quick_fix)
        self.assertIn("normal gates", quick_fix)

    def test_plan_route_enforces_full_workflow_for_broad_work(self):
        plan_command = read_text(ROOT / "commands/plan.md")
        planning = read_text(ROOT / "skills/planning/SKILL.md")
        plan_detector = read_text(ROOT / "hooks/scripts/plan-detector.py")

        for text in [plan_command, planning, plan_detector]:
            lowered = text.lower()
            self.assertIn("broad, high-impact, multi-step, cross-domain", lowered)
            self.assertIn("quality-sensitive", text)
            self.assertIn("outcome-oriented requests", text)
            self.assertIn("exact implementation scope", text)
            self.assertIn("chat proposal", text)
            self.assertIn("plan-brief.md", text)
            self.assertIn("applicable design", text)
            self.assertIn("explicit", text)
            self.assertIn("approval", text)
            self.assertIn("Frontend/UI/site", text)
            self.assertIn("example", text)
            self.assertIn("DESIGN.md", text)
        self.assertIn("local research", plan_command.lower())
        self.assertIn("material external/domain research", plan_command)
        self.assertIn("do not hand off to implementation", plan_command.lower())

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
