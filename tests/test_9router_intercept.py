"""Tests for hooks/scripts/9router-intercept.py.

Covers:
- Passthrough when 9router is unreachable (original tool allowed)
- Interception when 9router is reachable (tool denied, results via additionalContext)
- Passthrough for non-matching tool names
- Passthrough when tool input is empty
"""

import atexit
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from threading import Thread

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "hooks" / "scripts" / "9router-intercept.py"
CACHE_DIR = tempfile.mkdtemp(prefix="9router-test-")
CACHE_FILE = os.path.join(CACHE_DIR, "available.json")
atexit.register(shutil.rmtree, CACHE_DIR, ignore_errors=True)


def _run_hook(tool_name, tool_input):
    payload = json.dumps({"tool_name": tool_name, "tool_input": tool_input})
    env = os.environ.copy()
    env["NINEROUTER_URL"] = "http://localhost:1"
    env["NINEROUTER_CACHE_FILE"] = CACHE_FILE
    result = subprocess.run(
        [sys.executable, str(SCRIPT)],
        input=payload,
        capture_output=True,
        text=True,
        timeout=30,
        env=env,
    )
    return result


class _Fake9Router(BaseHTTPRequestHandler):
    """Minimal fake 9router for testing reachability."""

    RESPONSES = {}
    REQUESTS = []

    def do_GET(self):
        if self.path == "/v1/models":
            self._json(200, {"data": []})
        else:
            self._json(404, {"error": "not found"})

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))))
        self.REQUESTS.append((self.path, body))
        key = self.path.strip("/")
        response = self.RESPONSES.get(key)
        if isinstance(response, list):
            response = response.pop(0)
        if isinstance(response, tuple):
            self._json(response[0], response[1])
        elif response is not None:
            self._json(200, response)
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
    _Fake9Router.REQUESTS = []
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
        cls.server, cls.port = _start_server()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()

    def setUp(self):
        _clear_cache()
        _Fake9Router.RESPONSES = {
            "v1/search": {
                "provider": "tavily",
                "results": [
                    {"title": "Test Result", "url": "https://example.com", "snippet": "A test snippet"},
                ],
            },
            "v1/web/fetch": {
                "provider": "jina-reader",
                "title": "Example Page",
                "content": {"format": "markdown", "text": "Page content here", "length": 16},
            },
        }
        _Fake9Router.REQUESTS = []

    def _run_with_base(self, tool_name, tool_input):
        payload = json.dumps({"tool_name": tool_name, "tool_input": tool_input})
        env = os.environ.copy()
        env["NINEROUTER_URL"] = f"http://localhost:{self.port}"
        env["NINEROUTER_CACHE_FILE"] = CACHE_FILE
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
        self.assertEqual(r.returncode, 0)
        resp = json.loads(r.stdout)
        output = resp["hookSpecificOutput"]
        self.assertEqual(output["hookEventName"], "PreToolUse")
        self.assertEqual(output["permissionDecision"], "deny")
        self.assertIn("9Router", output["additionalContext"])
        self.assertIn("test query", output["additionalContext"])

    def test_websearch_has_results(self):
        r = self._run_with_base("WebSearch", {"query": "test query"})
        resp = json.loads(r.stdout)
        context = resp["hookSpecificOutput"]["additionalContext"]
        self.assertIn("Test Result", context)
        self.assertIn("https://example.com", context)

    def test_websearch_uses_documented_default_provider(self):
        self._run_with_base("WebSearch", {"query": "test query"})
        self.assertIn(("/v1/search", {"query": "test query", "max_results": 5, "provider": "tavily"}), _Fake9Router.REQUESTS)

    def test_web_fetch_blocked(self):
        r = self._run_with_base("mcp__web-reader__webReader", {"url": "https://example.com"})
        self.assertEqual(r.returncode, 0)
        resp = json.loads(r.stdout)
        output = resp["hookSpecificOutput"]
        self.assertEqual(output["permissionDecision"], "deny")
        self.assertIn("Example Page", output["additionalContext"])
        self.assertIn("Page content here", output["additionalContext"])

    def test_web_fetch_uses_documented_default_provider(self):
        self._run_with_base("mcp__web-reader__webReader", {"url": "https://example.com"})
        self.assertIn(("/v1/web/fetch", {"url": "https://example.com", "format": "markdown", "provider": "firecrawl"}), _Fake9Router.REQUESTS)

    def test_builtin_web_fetch_blocked(self):
        r = self._run_with_base("WebFetch", {"url": "https://example.com"})
        self.assertEqual(r.returncode, 0)
        resp = json.loads(r.stdout)
        output = resp["hookSpecificOutput"]
        self.assertEqual(output["permissionDecision"], "deny")
        self.assertIn("Example Page", output["additionalContext"])
        self.assertIn(("/v1/web/fetch", {"url": "https://example.com", "format": "markdown", "provider": "firecrawl"}), _Fake9Router.REQUESTS)

    def test_web_reader_blocked(self):
        r = self._run_with_base("mcp__web_reader__webReader", {"url": "https://example.com"})
        self.assertEqual(r.returncode, 0)
        resp = json.loads(r.stdout)
        self.assertEqual(resp["hookSpecificOutput"]["permissionDecision"], "deny")

    def test_search_prime_blocked(self):
        r = self._run_with_base("mcp__web-search-prime__web_search_prime", {"search_query": "hello"})
        self.assertEqual(r.returncode, 0)
        resp = json.loads(r.stdout)
        output = resp["hookSpecificOutput"]
        self.assertEqual(output["permissionDecision"], "deny")
        self.assertIn("hello", output["additionalContext"])

    def test_search_falls_back_to_next_provider(self):
        _Fake9Router.RESPONSES["v1/search"] = [
            (429, {"error": {"message": "quota exceeded"}}),
            {"provider": "exa", "results": [{"title": "Fallback", "url": "https://example.com/fallback", "snippet": "ok"}]},
        ]
        r = self._run_with_base("WebSearch", {"query": "fallback query"})
        self.assertEqual(r.returncode, 0)
        resp = json.loads(r.stdout)
        self.assertIn("Fallback", resp["hookSpecificOutput"]["additionalContext"])
        self.assertIn(("/v1/search", {"query": "fallback query", "max_results": 5, "provider": "tavily"}), _Fake9Router.REQUESTS)
        self.assertIn(("/v1/search", {"query": "fallback query", "max_results": 5, "provider": "exa"}), _Fake9Router.REQUESTS)

    def test_fetch_falls_back_to_next_provider(self):
        _Fake9Router.RESPONSES["v1/web/fetch"] = [
            (429, {"error": {"message": "quota exceeded"}}),
            {"provider": "exa", "title": "Fallback Page", "content": {"text": "fallback content"}},
        ]
        r = self._run_with_base("mcp__web-reader__webReader", {"url": "https://example.com"})
        self.assertEqual(r.returncode, 0)
        resp = json.loads(r.stdout)
        self.assertIn("Fallback Page", resp["hookSpecificOutput"]["additionalContext"])
        self.assertIn(("/v1/web/fetch", {"url": "https://example.com", "format": "markdown", "provider": "firecrawl"}), _Fake9Router.REQUESTS)
        self.assertIn(("/v1/web/fetch", {"url": "https://example.com", "format": "markdown", "provider": "exa"}), _Fake9Router.REQUESTS)

    def test_block_reason_contains_tool_name(self):
        r = self._run_with_base("WebSearch", {"query": "test"})
        resp = json.loads(r.stdout)
        reason = resp["hookSpecificOutput"]["permissionDecisionReason"]
        self.assertIn("9router", reason)
        self.assertIn("WebSearch", reason)


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
        env["NINEROUTER_CACHE_FILE"] = CACHE_FILE
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
        env["NINEROUTER_CACHE_FILE"] = CACHE_FILE
        payload = json.dumps({"tool_name": "WebSearch", "tool_input": {"query": "q"}})
        r = subprocess.run(
            [sys.executable, str(SCRIPT)], input=payload,
            capture_output=True, text=True, timeout=30, env=env,
        )
        self.assertEqual(r.returncode, 0)
        with open(CACHE_FILE) as f:
            cache = json.load(f)
        self.assertTrue(cache["ok"])

    def test_cache_stores_unreachable(self):
        env = os.environ.copy()
        env["NINEROUTER_URL"] = "http://localhost:1"
        env["NINEROUTER_CACHE_FILE"] = CACHE_FILE
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
