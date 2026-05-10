#!/usr/bin/env python
"""Design viewer server. Serves design-viewer.html and handles token saves.
Usage: python design-server.py [port]
"""
import json, os, re, sys
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path

FLOW_DIR = Path(".claude/flow")
DESIGN_MD = Path("DESIGN.md")  # DESIGN.md lives at project root (alongside CLAUDE.md)
TEMPLATE_SRC = Path(__file__).resolve().parent.parent / "templates" / "design-viewer.html"
HTML_DEST = FLOW_DIR / "design-viewer.html"

DEFAULT_PORT = 8765

SECTION_KEYWORDS = {
    "color": ["color", "palette"],
    "typography": ["typograph", "font", "type scale"],
    "spacing": ["spacing", "space"],
    "radius": ["radius", "border-radius", "corner"],
    "shadow": ["shadow", "elevation"],
}


def detect_section_type(header):
    h = header.lower()
    for stype, keywords in SECTION_KEYWORDS.items():
        for kw in keywords:
            if kw in h:
                return stype
    return None


HEADER_WORDS = {"token", "name", "property", "value", "usage", "description", "variable"}


def _is_header_row(cells):
    first = cells[0].lower().strip()
    if first in HEADER_WORDS:
        return all(c.lower().strip() in HEADER_WORDS for c in cells[:3] if c.strip())
    return False


def parse_tokens(content):
    """Parse DESIGN.md into {section_type: [{name, value, usage, line_index}]}."""
    tokens = {}
    current_type = None
    for i, line in enumerate(content.splitlines()):
        stripped = line.strip()
        if stripped.startswith("## "):
            current_type = detect_section_type(stripped[3:])
            continue
        if current_type and stripped.startswith("|") and not re.match(r"^\|\s*[-:]+", stripped):
            cells = [c.strip() for c in stripped.split("|")[1:-1]]
            if len(cells) >= 2 and cells[0] and not _is_header_row(cells):
                entry = {"name": cells[0], "value": cells[1], "line_index": i}
                if len(cells) >= 3:
                    entry["usage"] = cells[2]
                tokens.setdefault(current_type, []).append(entry)
    return tokens


def update_design_md(updates):
    """Update token values in DESIGN.md. updates: {token_name: new_value}."""
    if not DESIGN_MD.exists():
        return False, "DESIGN.md not found"
    content = DESIGN_MD.read_text(encoding="utf-8")
    lines = content.splitlines()
    current_type = None
    changed = 0
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("## "):
            current_type = detect_section_type(stripped[3:])
            continue
        if current_type and stripped.startswith("|") and not re.match(r"^\|\s*[-:]+", stripped):
            cells = [c.strip() for c in stripped.split("|")[1:-1]]
            if len(cells) >= 2 and cells[0] in updates and not _is_header_row(cells):
                new_val = updates[cells[0]]
                new_val = updates[cells[0]]
                cells[1] = f" {new_val} "
                while len("|".join([""] + cells + [""])) - len(stripped) < 0:
                    cells[1] += " "
                parts = stripped.split("|")
                parts[2] = f" {new_val} "
                lines[i] = "|".join(parts)
                changed += 1
    if changed > 0:
        DESIGN_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return True, f"Updated {changed} token(s)"


def ensure_html():
    """Copy HTML template to .claude/flow/ if not present or if template is newer."""
    FLOW_DIR.mkdir(parents=True, exist_ok=True)
    if not HTML_DEST.exists():
        import shutil
        shutil.copy2(TEMPLATE_SRC, HTML_DEST)
    elif TEMPLATE_SRC.exists() and TEMPLATE_SRC.stat().st_mtime > HTML_DEST.stat().st_mtime:
        import shutil
        shutil.copy2(TEMPLATE_SRC, HTML_DEST)


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass  # quiet logs

    def _send(self, code, content_type, body):
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        if isinstance(body, str):
            body = body.encode("utf-8")
        self.wfile.write(body)

    def do_GET(self):
        ensure_html()
        if self.path in ("/", ""):
            self.send_response(302)
            self.send_header("Location", "/design-viewer.html")
            self.end_headers()
        elif self.path == "/design-viewer.html":
            if HTML_DEST.exists():
                self._send(200, "text/html; charset=utf-8", HTML_DEST.read_text(encoding="utf-8"))
            else:
                self._send(404, "text/plain", "design-viewer.html not found")
        elif self.path == "/DESIGN.md":
            if DESIGN_MD.exists():
                self._send(200, "text/markdown; charset=utf-8", DESIGN_MD.read_text(encoding="utf-8"))
            else:
                self._send(404, "text/plain", "DESIGN.md not found")
        elif self.path == "/api/tokens":
            if DESIGN_MD.exists():
                tokens = parse_tokens(DESIGN_MD.read_text(encoding="utf-8"))
                self._send(200, "application/json", json.dumps(tokens))
            else:
                self._send(200, "application/json", "{}")
        else:
            self._send(404, "text/plain", "Not found")

    def do_POST(self):
        if self.path == "/api/save":
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length)
            try:
                data = json.loads(body)
                updates = data.get("tokens", {})
                ok, msg = update_design_md(updates)
                self._send(200, "application/json", json.dumps({"success": ok, "message": msg}))
            except Exception as e:
                self._send(500, "application/json", json.dumps({"success": False, "error": str(e)}))
        else:
            self._send(404, "text/plain", "Not found")


def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_PORT
    ensure_html()
    server = HTTPServer(("localhost", port), Handler)
    print(f"Design viewer: http://localhost:{port}")
    print(f"DESIGN.md: {DESIGN_MD.resolve()}")
    print("Press Ctrl+C to stop")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
        server.server_close()


if __name__ == "__main__":
    main()
