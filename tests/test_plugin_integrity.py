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

    def test_python_hook_scripts_compile(self):
        scripts = sorted((ROOT / "hooks/scripts").glob("*.py"))
        self.assertGreater(len(scripts), 0, "expected Python hook scripts")

        for path in scripts:
            with self.subTest(file=path.relative_to(ROOT).as_posix()):
                compile(read_text(path), str(path), "exec")

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
            "atlas": "opus",
            "chronicler": "haiku",
            "designer": "sonnet",
            "evolver": "opus",
            "forge": "sonnet",
            "oracle": "opus",
            "pd": "sonnet",
            "prism": "sonnet",
            "scout": "sonnet",
            "sentinel": "sonnet",
            "validator": "haiku",
            "weaver": "sonnet",
            "anvil": "haiku",
        }
        expected_effort = {
            "atlas": "xhigh",
            "designer": "high",
            "evolver": "high",
            "forge": "high",
            "oracle": "xhigh",
            "pd": "medium",
            "prism": "high",
            "scout": "medium",
            "sentinel": "high",
            "weaver": "high",
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
                    self.assertIsNone(effort, "haiku agents should stay fast and omit effort")
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


if __name__ == "__main__":
    unittest.main(verbosity=2)
