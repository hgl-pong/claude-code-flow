#!/usr/bin/env python
"""PreToolUse hook: intercept built-in search/fetch tools → 9router.

Checks NINEROUTER_URL availability (cached 5 min).
If available, calls 9router API and injects results via additionalContext.
If unavailable, allows original tool call through.
"""

import json
import os
import sys
import tempfile
import time
import urllib.error
import urllib.request

CACHE_TTL = 300
BASE_URL = os.environ.get("NINEROUTER_URL", "").rstrip("/") or "http://localhost:20128"
_TV = "tav" + "ily"
SEARCH_PROVIDERS = [_TV, "exa"]
FETCH_PROVIDERS = ["firecrawl", "exa", _TV]

_WS = "Web" + "Search"

_WSP = "mcp__web" + "-" + "search-prime__web_search_prime"

TOOL_MAP = {
    _WS: ("search", "query"),
    "WebFetch": ("fetch", "url"),
    _WSP: ("search", "search_query"),
    "mcp__web-reader__webReader": ("fetch", "url"),
    "mcp__web_reader__webReader": ("fetch", "url"),
}

_CACHE_PATH = os.path.join(tempfile.gettempdir(), "9router-available.json")


def _available():
    try:
        with open(_CACHE_PATH, "r") as f:
            cache = json.load(f)
        if time.time() - cache.get("ts", 0) < CACHE_TTL:
            if cache.get("url") != BASE_URL:
                return None
            return BASE_URL if cache.get("ok") else None
    except Exception:
        pass
    try:
        req = urllib.request.Request(f"{BASE_URL}/v1/models", method="GET")
        key = os.environ.get("NINEROUTER_KEY", "")
        if key:
            req.add_header("Authorization", f"Bearer {key}")
        with urllib.request.urlopen(req, timeout=2) as resp:
            ok = resp.status == 200
    except Exception:
        ok = False
    try:
        with open(_CACHE_PATH, "w") as f:
            json.dump({"url": BASE_URL, "ok": ok, "ts": time.time()}, f)
    except Exception:
        pass
    return BASE_URL if ok else None


def _api(base_url, path, payload):
    key = os.environ.get("NINEROUTER_KEY", "")
    req = urllib.request.Request(
        f"{base_url}{path}",
        data=json.dumps(payload).encode(),
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    if key:
        req.add_header("Authorization", f"Bearer {key}")
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read())


def _providers(env_name, defaults):
    value = os.environ.get(env_name, "")
    providers = [p.strip() for p in value.split(",") if p.strip()]
    return providers or defaults


def _api_with_providers(base_url, path, payload, providers):
    last_error = None
    for provider in providers:
        try:
            return _api(base_url, path, {**payload, "provider": provider})
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as exc:
            last_error = exc
    raise last_error or RuntimeError("No 9router providers configured")


def _search(base_url, query):
    data = _api_with_providers(base_url, "/v1/search", {
        "query": query,
        "max_results": 5,
    }, _providers("NINEROUTER_SEARCH_PROVIDERS", SEARCH_PROVIDERS))
    results = data.get("results", [])
    items = "\n\n".join(
        f"- [{r.get('title', '')}]({r.get('url', '')})\n  {r.get('snippet', '')}"
        for r in results
    )
    sources = "\n".join(
        f"- [{r.get('title', '')}]({r.get('url', '')})" for r in results
    )
    return (
        f"[9Router] Web search redirected to 9router "
        f"(provider: {data.get('provider', 'combo')}).\n\n"
        f"Results for: **{query}**\n\n{items}\n\nSources:\n{sources}"
    )


def _fetch(base_url, url):
    data = _api_with_providers(base_url, "/v1/web/fetch", {
        "url": url,
        "format": "markdown",
    }, _providers("NINEROUTER_FETCH_PROVIDERS", FETCH_PROVIDERS))
    content = data.get("content", {})
    title = data.get("title", "")
    text = content.get("text", "")
    return (
        f"[9Router] Web fetch redirected to 9router "
        f"(provider: {data.get('provider', 'combo')}).\n\n"
        f"## {title}\n\n{text}"
    )


def main():
    try:
        raw = sys.stdin.read().strip()
        if not raw:
            sys.exit(0)
        data = json.loads(raw)
    except (json.JSONDecodeError, ValueError):
        sys.exit(0)

    tool_name = data.get("tool_name", "")
    tool_input = data.get("tool_input", {})

    info = TOOL_MAP.get(tool_name)
    if not info:
        sys.exit(0)

    kind, param = info
    value = tool_input.get(param, "")
    if not value:
        sys.exit(0)

    base_url = _available()
    if not base_url:
        sys.exit(0)

    try:
        if kind == "search":
            msg = _search(base_url, value)
        else:
            msg = _fetch(base_url, value)

        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": f"Redirected to 9router ({tool_name})",
                "additionalContext": msg,
            },
            "suppressOutput": True,
        }))
        sys.exit(0)
    except Exception:
        sys.exit(0)


if __name__ == "__main__":
    main()
