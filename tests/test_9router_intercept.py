"""Tests for hooks/scripts/9router-intercept.py.

Covers:
- Passthrough when 9router is unreachable (original tool allowed)
- Interception when 9router is reachable (tool blocked, results via systemMessage)
- Passthrough for non-matching tool names
- Passthrough when tool input is empty
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from threading import Thread

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "hooks" / "scripts" / "9router-intercept.py"
CACHE_FILE = os.path.join(tempfile.gettempdir(), "9router-available.json")


def _run_hook(tool_name, tool_input):
    payload = json.dumps({"tool_name": tool_name, "tool_input": tool_input})
    result = subprocess.run(
        [sys.executable, str(SCRIPT)],
        input=payload,
        capture_output=True,
        text=True,
        timeout=30,
    )
    return result


class _Fake9Router(BaseHTTPRequestHandler):
    """Minimal fake 9router for testing reachability."""

    RESPONSES = {}

    def do_GET(self):
        if self.path == "/v1/models":
            self._json(200, {"data": []})
        else:
            self._json(404, {"error": "not found"})

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))))
        key = self.path.strip("/")
        if key in self.RESPONSES:
            self._json(200, self.RESPONSES[key])
        else:
            self._json(200, {})

    def _json(self, code, data):
        raw = json.dumps(data).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def log_message(self, *args):
        pass


def _start_server(responses=None):
    _Fake9Router.RESPONSES = responses or {}
    server = HTTPServer(("127.0.0.1", 0), _Fake9Router)
    port = server.server_address[1]
    t = Thread(target=server.serve_forever, daemon=True)
    t.start()
    return server, port


def _clear_cache():
    try:
        os.remove(CACHE_FILE)
    except FileNotFoundError:
        pass


class PassthroughUnreachable(unittest.TestCase):
    """When 9router is not reachable, allow original tool call."""

    def setUp(self):
        _clear_cache()

    def test_websearch_passthrough(self):
        r = _run_hook("WebSearch", {"query": "test"})
        self.assertEqual(r.returncode, 0)
        self.assertEqual(r.stdout.strip(), "")

    def test_web_fetch_passthrough(self):
        r = _run_hook("mcp__web-reader__webReader", {"url": "https://example.com"})
        self.assertEqual(r.returncode, 0)

    def test_search_prime_passthrough(self):
        r = _run_hook("mcp__web-search-prime__web_search_prime", {"search_query": "test"})
        self.assertEqual(r.returncode, 0)


class PassthroughEdgeCases(unittest.TestCase):
    """Edge cases that always passthrough regardless of 9router state."""

    def test_non_matching_tool(self):
        r = _run_hook("Bash", {"command": "echo hi"})
        self.assertEqual(r.returncode, 0)

    def test_empty_query(self):
        r = _run_hook("WebSearch", {"query": ""})
        self.assertEqual(r.returncode, 0)

    def test_missing_param(self):
        r = _run_hook("WebSearch", {})
        self.assertEqual(r.returncode, 0)

    def test_empty_url(self):
        r = _run_hook("mcp__web_reader__webReader", {"url": ""})
        self.assertEqual(r.returncode, 0)

    def test_malformed_stdin(self):
        result = subprocess.run(
            [sys.executable, str(SCRIPT)],
            input="not json",
            capture_output=True,
            text=True,
            timeout=10,
        )
        self.assertEqual(result.returncode, 0)

    def test_empty_stdin(self):
        result = subprocess.run(
            [sys.executable, str(SCRIPT)],
            input="",
            capture_output=True,
            text=True,
            timeout=10,
        )
        self.assertEqual(result.returncode, 0)


class InterceptReachable(unittest.TestCase):
    """When 9router is reachable, intercept and return results."""

    @classmethod
    def setUpClass(cls):
        _clear_cache()
        search_resp = {
            "provider": "tavily",
            "results": [
                {"title": "Test Result", "url": "https://example.com", "snippet": "A test snippet"},
            ],
        }
        fetch_resp = {
            "provider": "jina-reader",
            "title": "Example Page",
            "content": {"format": "markdown", "text": "Page content here", "length": 16},
        }
        cls.server, cls.port = _start_server({
            "v1/search": search_resp,
            "v1/web/fetch": fetch_resp,
        })

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()

    def setUp(self):
        _clear_cache()

    def _run_with_base(self, tool_name, tool_input):
        payload = json.dumps({"tool_name": tool_name, "tool_input": tool_input})
        env = os.environ.copy()
        env["NINEROUTER_URL"] = f"http://localhost:{self.port}"
        result = subprocess.run(
            [sys.executable, str(SCRIPT)],
            input=payload,
            capture_output=True,
            text=True,
            timeout=30,
            env=env,
        )
        return result

    def test_websearch_blocked(self):
        r = self._run_with_base("WebSearch", {"query": "test query"})
        self.assertEqual(r.returncode, 2)
        resp = json.loads(r.stdout)
        self.assertEqual(resp["decision"], "block")
        self.assertIn("9Router", resp["systemMessage"])
        self.assertIn("test query", resp["systemMessage"])

    def test_websearch_has_results(self):
        r = self._run_with_base("WebSearch", {"query": "test query"})
        resp = json.loads(r.stdout)
        self.assertIn("Test Result", resp["systemMessage"])
        self.assertIn("https://example.com", resp["systemMessage"])

    def test_web_fetch_blocked(self):
        r = self._run_with_base("mcp__web-reader__webReader", {"url": "https://example.com"})
        self.assertEqual(r.returncode, 2)
        resp = json.loads(r.stdout)
        self.assertEqual(resp["decision"], "block")
        self.assertIn("Example Page", resp["systemMessage"])
        self.assertIn("Page content here", resp["systemMessage"])

    def test_web_reader_blocked(self):
        r = self._run_with_base("mcp__web_reader__webReader", {"url": "https://example.com"})
        self.assertEqual(r.returncode, 2)
        resp = json.loads(r.stdout)
        self.assertEqual(resp["decision"], "block")

    def test_search_prime_blocked(self):
        r = self._run_with_base("mcp__web-search-prime__web_search_prime", {"search_query": "hello"})
        self.assertEqual(r.returncode, 2)
        resp = json.loads(r.stdout)
        self.assertEqual(resp["decision"], "block")
        self.assertIn("hello", resp["systemMessage"])

    def test_block_reason_contains_tool_name(self):
        r = self._run_with_base("WebSearch", {"query": "test"})
        resp = json.loads(r.stdout)
        self.assertIn("9router", resp["reason"])
        self.assertIn("WebSearch", resp["reason"])


class InterceptApiError(unittest.TestCase):
    """Reachable health check but API call fails → passthrough."""

    @classmethod
    def setUpClass(cls):
        _clear_cache()

        class _BrokenApi(_Fake9Router):
            def do_POST(self):
                self.send_error(500, "internal error")

        cls.server = HTTPServer(("127.0.0.1", 0), _BrokenApi)
        cls.port = cls.server.server_address[1]
        Thread(target=cls.server.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()

    def setUp(self):
        _clear_cache()

    def test_api_error_passthrough(self):
        env = os.environ.copy()
        env["NINEROUTER_URL"] = f"http://localhost:{self.port}"
        payload = json.dumps({"tool_name": "WebSearch", "tool_input": {"query": "test"}})
        r = subprocess.run(
            [sys.executable, str(SCRIPT)], input=payload,
            capture_output=True, text=True, timeout=30, env=env,
        )
        self.assertEqual(r.returncode, 0)


class CachedAvailability(unittest.TestCase):
    """Cache: once reachable, skip health check on subsequent calls."""

    @classmethod
    def setUpClass(cls):
        _clear_cache()
        cls.server, cls.port = _start_server()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()

    def setUp(self):
        _clear_cache()

    def test_cache_stores_reachable(self):
        env = os.environ.copy()
        env["NINEROUTER_URL"] = f"http://localhost:{self.port}"
        payload = json.dumps({"tool_name": "WebSearch", "tool_input": {"query": "q"}})
        r = subprocess.run(
            [sys.executable, str(SCRIPT)], input=payload,
            capture_output=True, text=True, timeout=30, env=env,
        )
        self.assertEqual(r.returncode, 2)
        with open(CACHE_FILE) as f:
            cache = json.load(f)
        self.assertTrue(cache["ok"])

    def test_cache_stores_unreachable(self):
        env = os.environ.copy()
        env["NINEROUTER_URL"] = "http://localhost:1"
        payload = json.dumps({"tool_name": "WebSearch", "tool_input": {"query": "q"}})
        r = subprocess.run(
            [sys.executable, str(SCRIPT)], input=payload,
            capture_output=True, text=True, timeout=30, env=env,
        )
        self.assertEqual(r.returncode, 0)
        with open(CACHE_FILE) as f:
            cache = json.load(f)
        self.assertFalse(cache["ok"])


if __name__ == "__main__":
    unittest.main()
