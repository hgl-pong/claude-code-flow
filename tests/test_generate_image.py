"""Tests for scripts/generate-image.py.

Tests cover arg parsing, env validation, and API call via subprocess + mock HTTP server.
"""

import json
import os
import subprocess
import sys
import threading
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "generate-image.py"


def run_script(*args, env_extra=None):
    env = os.environ.copy()
    env.pop("NINEROUTER_URL", None)
    env.pop("NINEROUTER_KEY", None)
    if env_extra:
        env.update(env_extra)
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True,
        text=True,
        env=env,
    )
    return proc.returncode, proc.stdout.strip(), proc.stderr.strip()


def test_missing_prompt_exits_2():
    code, _, err = run_script("--output", "out.png")
    assert code == 2


def test_missing_output_exits_2():
    code, _, err = run_script("--prompt", "test")
    assert code == 2


def test_missing_ninerouter_url_exits_2():
    code, _, err = run_script(
        "--prompt", "cat", "--output", "out.png",
        env_extra={"NINEROUTER_KEY": "test-key"},
    )
    assert code == 2
    assert "NINEROUTER_URL" in err


def test_missing_ninerouter_key_exits_2():
    code, _, err = run_script(
        "--prompt", "cat", "--output", "out.png",
        env_extra={"NINEROUTER_URL": "http://localhost:3000"},
    )
    assert code == 2
    assert "NINEROUTER_KEY" in err


class MockHandler(BaseHTTPRequestHandler):
    """Mock 9Router API server."""
    response_body = b"\x89PNG\r\n\x1a\nfake"
    response_code = 200
    last_request = None

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)
        MockHandler.last_request = json.loads(body)
        self.send_response(MockHandler.response_code)
        self.end_headers()
        self.wfile.write(MockHandler.response_body)

    def log_message(self, *args):
        pass  # suppress log noise


@pytest.fixture
def mock_server():
    MockHandler.last_request = None
    MockHandler.response_body = b"\x89PNG\r\n\x1a\nfake"
    MockHandler.response_code = 200
    server = HTTPServer(("127.0.0.1", 0), MockHandler)
    port = server.server_address[1]
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    yield f"http://127.0.0.1:{port}"
    server.shutdown()


def test_success_writes_file_and_manifest(tmp_path, mock_server):
    out_file = tmp_path / "images" / "test.png"
    code, stdout, stderr = run_script(
        "--prompt", "watercolor cat",
        "--output", str(out_file),
        env_extra={
            "NINEROUTER_URL": mock_server,
            "NINEROUTER_KEY": "test-key",
        },
    )

    assert code == 0, f"stderr: {stderr}"
    assert out_file.exists()
    assert out_file.read_bytes() == b"\x89PNG\r\n\x1a\nfake"

    manifest = json.loads(stdout)
    assert manifest["model"] == "cx/gpt-5.5-image"
    assert manifest["output"] == str(out_file).replace("/", "\\") or manifest["output"] == str(out_file)
    assert manifest["prompt"] == "watercolor cat"
    assert manifest["size"] == "1024x1024"
    assert manifest["quality"] == "high"

    # Verify request sent correct payload
    assert MockHandler.last_request["model"] == "cx/gpt-5.5-image"
    assert MockHandler.last_request["prompt"] == "watercolor cat"


def test_api_error_exits_1(tmp_path, mock_server):
    MockHandler.response_code = 429
    MockHandler.response_body = b"rate limited"

    out_file = tmp_path / "test.png"
    code, stdout, stderr = run_script(
        "--prompt", "cat",
        "--output", str(out_file),
        env_extra={
            "NINEROUTER_URL": mock_server,
            "NINEROUTER_KEY": "test-key",
        },
    )

    assert code == 1
    assert "429" in stderr


def test_custom_size_and_quality(tmp_path, mock_server):
    out_file = tmp_path / "wide.png"
    code, stdout, _ = run_script(
        "--prompt", "panoramic cityscape",
        "--output", str(out_file),
        "--size", "1792x1024",
        "--quality", "low",
        env_extra={
            "NINEROUTER_URL": mock_server,
            "NINEROUTER_KEY": "test-key",
        },
    )

    assert code == 0
    manifest = json.loads(stdout)
    assert manifest["size"] == "1792x1024"
    assert manifest["quality"] == "low"
    assert MockHandler.last_request["size"] == "1792x1024"
    assert MockHandler.last_request["quality"] == "low"
