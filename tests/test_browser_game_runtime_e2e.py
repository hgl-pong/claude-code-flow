"""Real browser runtime E2E contract for auto-mode browser-game output.

This test builds a tiny playable browser-game fixture in a temp project, serves it
with an actual HTTP server, drives it with Playwright, and verifies the runtime
signals auto-mode requires before a runnable game can be called complete.
"""

from __future__ import annotations

import contextlib
import functools
import http.server
import socketserver
import threading
from pathlib import Path

from playwright.sync_api import Page, sync_playwright


GAME_DOCS = {
    "GAME_DESIGN.md": """# Game Design\n\nPlayer fantasy: dodge hazards and survive.\nPrimary verbs: move, pause, restart.\nCore loop: read hazard, move, score, recover.\nFailure/recovery: collision causes game over; restart returns to play.\nScope boundaries: one arena, keyboard, desktop browser.\n""",
    "MECHANICS_SPEC.md": """# Mechanics Spec\n\nState: x/y/score/running/gameOver.\nInput maps physical keys to semantic actions.\nCollision: player overlaps hazard => failure.\nProgression: score increments while running.\n""",
    "CONTENT_PLAN.md": """# Content Plan\n\nOne arena. One player. One hazard. One HUD.\n""",
    "UX_PLAYTEST_PLAN.md": """# UX Playtest Plan\n\nVerify route load, canvas render surface, semantic input, visible core loop,\nfailure/restart, HUD readability, console status, screenshot evidence.\n""",
    "ASSET_BRIEF.md": """# Asset Brief\n\nUse code-drawn placeholder shapes. Manifest keys: player, hazard.\nNo external assets required.\n""",
}

INDEX_HTML = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Auto Mode Browser Game E2E</title>
  <style>
    body { margin: 0; font-family: sans-serif; background: #101820; color: white; }
    #hud { position: fixed; top: 8px; left: 8px; background: rgba(0,0,0,.65); padding: 8px; border-radius: 4px; }
    canvas { display: block; margin: 48px auto 0; background: #1f2f46; outline: 2px solid #6cf; }
    button { margin-left: 8px; }
  </style>
</head>
<body>
  <div id="hud" aria-live="polite">
    <span id="status">running</span>
    <span id="score">0</span>
    <button id="restart" type="button">Restart</button>
  </div>
  <canvas id="game" width="320" height="180" data-runtime="canvas"></canvas>
  <script type="module">
    const canvas = document.querySelector('#game')
    const ctx = canvas.getContext('2d')
    const status = document.querySelector('#status')
    const scoreEl = document.querySelector('#score')
    const restart = document.querySelector('#restart')
    const state = {
      x: 40, y: 100, score: 0, running: true, gameOver: false,
      lastAction: 'none', hazardX: 210, hazardY: 100
    }
    const actions = {
      ArrowLeft: 'move_left', KeyA: 'move_left',
      ArrowRight: 'move_right', KeyD: 'move_right',
      Space: 'pause', KeyR: 'restart'
    }
    function reset() {
      state.x = 40
      state.y = 100
      state.score = 0
      state.running = true
      state.gameOver = false
      state.lastAction = 'restart'
      status.textContent = 'running'
      scoreEl.textContent = '0'
      draw()
    }
    function applyAction(action) {
      state.lastAction = action
      if (action === 'restart') return reset()
      if (action === 'pause') state.running = !state.running
      if (!state.running || state.gameOver) return
      if (action === 'move_left') state.x = Math.max(10, state.x - 18)
      if (action === 'move_right') state.x = Math.min(310, state.x + 18)
      checkCollision()
      draw()
    }
    function checkCollision() {
      const dx = Math.abs(state.x - state.hazardX)
      const dy = Math.abs(state.y - state.hazardY)
      if (dx < 16 && dy < 16) {
        state.gameOver = true
        state.running = false
        status.textContent = 'game-over'
      }
    }
    function draw() {
      ctx.clearRect(0, 0, canvas.width, canvas.height)
      ctx.fillStyle = '#72f1b8'
      ctx.fillRect(state.x - 8, state.y - 8, 16, 16)
      ctx.fillStyle = '#ff4f64'
      ctx.fillRect(state.hazardX - 8, state.hazardY - 8, 16, 16)
      ctx.fillStyle = '#fff'
      ctx.fillText('Use arrows. Reach red to fail. R restarts.', 12, 24)
      scoreEl.textContent = String(state.score)
      window.__gameState = { ...state }
    }
    function tick() {
      if (state.running && !state.gameOver) state.score += 1
      draw()
      requestAnimationFrame(tick)
    }
    window.addEventListener('keydown', (event) => {
      const action = actions[event.code]
      if (action) {
        event.preventDefault()
        applyAction(action)
      }
    })
    restart.addEventListener('click', reset)
    window.__semanticActions = actions
    console.info('GAME_READY route=/ surface=canvas inputs=semantic')
    draw()
    requestAnimationFrame(tick)
  </script>
</body>
</html>
"""


class _ThreadingTCPServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True


@contextlib.contextmanager
def serve_directory(directory: Path):
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(directory))
    server = _ThreadingTCPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def _state(page: Page) -> dict:
    return page.evaluate("() => window.__gameState")


def test_auto_mode_browser_game_runtime_e2e_contract(tmp_path: Path):
    project = tmp_path / "game-project"
    evidence = project / ".claude" / "artifacts" / "auto-mode" / "browser-game-e2e"
    evidence.mkdir(parents=True)
    for name, body in GAME_DOCS.items():
        (project / name).write_text(body, encoding="utf-8")
    (project / "index.html").write_text(INDEX_HTML, encoding="utf-8")

    for name, body in GAME_DOCS.items():
        assert (project / name).exists()
        assert body.strip() in (project / name).read_text(encoding="utf-8")

    console_messages: list[str] = []
    with serve_directory(project) as base_url:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 640, "height": 420})
            page.on("console", lambda msg: console_messages.append(f"{msg.type}: {msg.text}"))
            page.goto(base_url + "/", wait_until="networkidle")

            assert page.locator("canvas#game[data-runtime='canvas']").is_visible()
            assert page.locator("#hud").is_visible()
            assert "GAME_READY route=/ surface=canvas inputs=semantic" in "\n".join(console_messages)

            initial = _state(page)
            assert initial["running"] is True
            assert initial["gameOver"] is False
            assert page.evaluate("() => window.__semanticActions.ArrowRight") == "move_right"

            page.keyboard.press("ArrowRight")
            moved = _state(page)
            assert moved["lastAction"] == "move_right"
            assert moved["x"] > initial["x"]

            page.wait_for_function("() => window.__gameState.score >= 5")
            assert _state(page)["score"] >= 5

            # Drive into the hazard to verify failure/recovery, not just boot.
            for _ in range(10):
                page.keyboard.press("ArrowRight")
                if _state(page)["gameOver"]:
                    break
            failed = _state(page)
            assert failed["gameOver"] is True
            assert page.locator("#status").inner_text() == "game-over"

            page.keyboard.press("KeyR")
            restarted = _state(page)
            assert restarted["lastAction"] == "restart"
            assert restarted["gameOver"] is False
            assert restarted["running"] is True
            assert page.locator("#status").inner_text() == "running"

            screenshot = evidence / "game-runtime.png"
            page.screenshot(path=str(screenshot))
            assert screenshot.exists()
            assert screenshot.stat().st_size > 0

            browser.close()

    joined_console = "\n".join(console_messages).lower()
    assert "error" not in joined_console
    assert "pageerror" not in joined_console
