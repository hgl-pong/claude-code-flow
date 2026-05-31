import json
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = Path("scripts") / "statusline.sh"


def run_statusline(stdin_json=None, cwd=None, extra_env=None):
    env = os.environ.copy()
    if extra_env:
        env.update(extra_env)
    proc = subprocess.run(
        ["rtk", "bash", SCRIPT.as_posix()],
        input=json.dumps(stdin_json).encode() if stdin_json is not None else None,
        cwd=cwd or ROOT,
        env=env,
        capture_output=True,
        check=False,
    )
    return proc.returncode, proc.stdout.decode(), proc.stderr.decode()


def test_model_name_shown():
    code, out, err = run_statusline({"model": {"display_name": "Claude"}})
    assert code == 0
    assert "Claude" in out


def test_runtime_evidence_shown():
    code, out, err = run_statusline(
        {
            "runtime_verification": {
                "status": "passed",
                "smoke": "passed",
                "crash_detected": False,
                "hang_detected": False,
                "evidence_dir": ".claude/deliverables/sample",
            }
        }
    )
    assert code == 0
    assert "rt:passed" in out
    assert "smoke:passed" in out
