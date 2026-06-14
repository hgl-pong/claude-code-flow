#!/usr/bin/env bash
# E2E Test: Auto-Mode Browser Game Real Pipeline (claude --print)
#
# Validates actual Claude Code auto-mode behavior for game development:
#   1. claude --print activates auto-mode via the plugin
#   2. Browser-game planning docs are created before/with implementation
#   3. A runnable browser game is created
#   4. Runtime evidence is gathered with a real HTTP server + Playwright browser
#   5. Auto-mode state/audit artifacts exist
#
# LONG_RUNNING: uses real LLM API and launches a real browser.
# Requires RUN_LONG_TESTS=true.
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PLUGIN_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
source "$SCRIPT_DIR/test-helpers.sh"

echo "========================================"
echo " E2E: Auto-Mode Browser Game Pipeline"
echo "========================================"
echo ""

if [ "${RUN_LONG_TESTS:-}" != "true" ]; then
    echo "SKIP: Set RUN_LONG_TESTS=true to run this test (real LLM + browser)."
    exit 0
fi

TEST_PROJECT=$(create_test_project)
echo "Test project: $TEST_PROJECT"
cleanup_on_exit() {
    if [ "${KEEP_TEST_PROJECT:-}" = "true" ] || [ "${FAILURES:-0}" -ne 0 ]; then
        echo "Keeping test project for debugging: $TEST_PROJECT"
    else
        cleanup_test_project "$TEST_PROJECT"
    fi
}
trap cleanup_on_exit EXIT

cd "$TEST_PROJECT"

git init -q
git config user.email "e2e-test@example.com"
git config user.name "E2E Test"
cat > package.json <<'JSONEOF'
{
  "name": "auto-browser-game-e2e",
  "private": true,
  "scripts": {
    "test": "node -e \"const fs=require('fs'); const html=fs.existsSync('index.html'); const docs=['GAME_DESIGN.md','MECHANICS_SPEC.md','CONTENT_PLAN.md','UX_PLAYTEST_PLAN.md','ASSET_BRIEF.md'].filter(f=>fs.existsSync(f)); if(!html) throw new Error('missing index.html'); if(docs.length < 3) throw new Error('missing game design docs: '+docs.length); console.log('static contract ok');\""
  }
}
JSONEOF

prompt='Build a tiny 2D browser game MVP in this empty project. Use auto-mode. Requirements: create lightweight game planning docs before implementation (GAME_DESIGN.md, MECHANICS_SPEC.md, CONTENT_PLAN.md, UX_PLAYTEST_PLAN.md, ASSET_BRIEF.md when relevant), then implement a runnable browser game at / with index.html. The game must have a visible canvas or equivalent render surface, a readable HUD, semantic keyboard controls, a visible core loop, failure and restart behavior, no external dependencies, and evidence-ready runtime behavior. Keep scope tiny: one player, one hazard or collectible, one screen. Add any minimal test/static verification needed.'

auto_log="$TEST_PROJECT/auto-browser-game-output.jsonl"
set +e
claude --print "/claude-code-flow:auto-mode $prompt" \
    --plugin-dir "$PLUGIN_DIR" \
    --max-turns "${AUTO_GAME_E2E_MAX_TURNS:-25}" \
    --output-format stream-json \
    --verbose \
    > "$auto_log" 2>&1
CLAUDE_EXIT=$?
set -e

echo "  claude exit code: $CLAUDE_EXIT"
if [ -s "$auto_log" ]; then
    echo "--- claude output tail ---"
    tail -80 "$auto_log" || true
    echo "--- end claude output tail ---"
fi

echo "--- top-level files after claude ---"
find . -maxdepth 2 -type f | sort | sed 's#^./#  #' | head -120 || true
echo "--- end top-level files ---"

if grep -qi 'API Error:' "$auto_log" 2>/dev/null; then
    fail "Claude runtime: API error occurred before game implementation completed"
fi

if [ -d ".claude/auto" ]; then
    pass "Auto-mode: .claude/auto/ directory exists"
else
    fail "Auto-mode: .claude/auto/ NOT created"
fi

STATE_FILES=$(find .claude/auto -name state.json -type f 2>/dev/null || true)
if [ -n "$STATE_FILES" ]; then
    pass "Auto-mode: state.json created"
else
    fail "Auto-mode: state.json NOT created"
fi

required_docs=(GAME_DESIGN.md MECHANICS_SPEC.md CONTENT_PLAN.md UX_PLAYTEST_PLAN.md ASSET_BRIEF.md)
doc_count=0
for doc in "${required_docs[@]}"; do
    if [ -s "$doc" ]; then
        pass "Game planning: $doc exists"
        doc_count=$((doc_count + 1))
    else
        fail "Game planning: $doc missing or empty"
    fi
done

if [ -f index.html ]; then
    pass "Runtime: index.html exists"
else
    fail "Runtime: index.html missing"
fi

if grep -qiE 'canvas|svg|webgl|phaser|three' index.html 2>/dev/null; then
    pass "Runtime: render surface marker found"
else
    fail "Runtime: no render surface marker in index.html"
fi

if grep -qiE 'keydown|KeyboardEvent|addEventListener\(.keydown|semantic|controls|Arrow|WASD' index.html 2>/dev/null; then
    pass "Runtime: keyboard/semantic input marker found"
else
    fail "Runtime: no keyboard/semantic input marker found"
fi

if grep -qiE 'restart|reset|game.?over|fail|collision|score|loop' index.html 2>/dev/null; then
    pass "Runtime: core loop/failure/restart marker found"
else
    fail "Runtime: no core loop/failure/restart marker found"
fi

if [ -f index.html ]; then
python - <<'PY'
from pathlib import Path
import contextlib, functools, http.server, socketserver, threading, sys
try:
    from playwright.sync_api import sync_playwright
except Exception as exc:
    print(f"PLAYWRIGHT_IMPORT_FAILED: {exc}")
    sys.exit(2)

project = Path.cwd()
evidence = project / ".claude" / "artifacts" / "auto-mode" / "browser-game-claude-p-e2e"
evidence.mkdir(parents=True, exist_ok=True)

class Server(socketserver.ThreadingTCPServer):
    allow_reuse_address = True

handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(project))
server = Server(("127.0.0.1", 0), handler)
thread = threading.Thread(target=server.serve_forever, daemon=True)
thread.start()
url = f"http://127.0.0.1:{server.server_address[1]}/"
console = []
try:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 800, "height": 600})
        page.on("console", lambda msg: console.append(f"{msg.type}: {msg.text}"))
        page.goto(url, wait_until="networkidle")
        surface = page.locator("canvas, svg, [data-runtime], [role='img']").first
        if surface.count() == 0 or not surface.is_visible():
            raise AssertionError("no visible render surface")
        body_text = page.locator("body").inner_text(timeout=2000)
        if not body_text.strip():
            raise AssertionError("empty body text/HUD")
        before = surface.bounding_box()
        page.keyboard.press("ArrowRight")
        page.keyboard.press("ArrowLeft")
        page.keyboard.press("Space")
        page.keyboard.press("KeyR")
        page.wait_for_timeout(500)
        after = surface.bounding_box()
        if not before or not after:
            raise AssertionError("render surface missing bounding box")
        shot = evidence / "claude-p-browser-game.png"
        page.screenshot(path=str(shot))
        if not shot.exists() or shot.stat().st_size == 0:
            raise AssertionError("screenshot not written")
        errors = [line for line in console if line.lower().startswith("error")]
        if errors:
            raise AssertionError("console errors: " + "\n".join(errors[:5]))
        browser.close()
finally:
    server.shutdown()
    server.server_close()
    thread.join(timeout=5)

print("RUNTIME_E2E_OK", url, str(evidence / "claude-p-browser-game.png"))
PY
RUNTIME_EXIT=$?
if [ "$RUNTIME_EXIT" -eq 0 ]; then
    pass "Runtime: real browser Playwright smoke passed"
else
    fail "Runtime: real browser Playwright smoke failed (exit $RUNTIME_EXIT)"
fi
else
    fail "Runtime: skipped Playwright smoke because index.html was not created"
fi

if [ -n "$STATE_FILES" ]; then
    FIRST_STATE=$(echo "$STATE_FILES" | head -1)
    if python3 -c "import json; json.load(open('$FIRST_STATE')); print('ok')" 2>/dev/null | grep -q ok; then
        pass "State: valid JSON"
        STATUS=$(python3 -c "import json; s=json.load(open('$FIRST_STATE')); print(s.get('status', '?'))" 2>/dev/null || echo "?")
        PHASE=$(python3 -c "import json; s=json.load(open('$FIRST_STATE')); print(s.get('phase', '?'))" 2>/dev/null || echo "?")
        echo "  State: phase=$PHASE status=$STATUS"
    else
        fail "State: invalid JSON"
    fi
fi

AUDIT_COUNT=$(find .claude/auto -type f 2>/dev/null | wc -l | tr -d ' ')
if [ "$AUDIT_COUNT" -ge 1 ]; then
    pass "Audit: $AUDIT_COUNT artifacts in .claude/auto/"
else
    fail "Audit: no artifacts"
fi

if grep -q 'GAME_DESIGN.md\|MECHANICS_SPEC.md\|UX_PLAYTEST_PLAN.md\|ASSET_BRIEF.md' "$auto_log" 2>/dev/null || \
   grep -R -q 'GAME_DESIGN.md\|MECHANICS_SPEC.md\|UX_PLAYTEST_PLAN.md\|ASSET_BRIEF.md' .claude/auto 2>/dev/null; then
    pass "Audit/log: game planning docs mentioned"
else
    fail "Audit/log: game planning docs not mentioned"
fi

echo ""
echo "========================================"
echo " Test Summary"
echo "========================================"
echo "Docs present: $doc_count/${#required_docs[@]}"
echo "State files: $(find .claude/auto -name state.json 2>/dev/null | wc -l)"
echo "Audit files: $(find .claude/auto -type f 2>/dev/null | wc -l)"
echo ""

report_failures
