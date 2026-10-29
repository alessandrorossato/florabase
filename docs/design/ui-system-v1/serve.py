"""Read-only loopback preview for Gate A; never imported by the application."""

import json
import mimetypes
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[3]
DOCS = Path(__file__).resolve().parent
ASSETS = Path(
    "/home/alessandro/.codex/visualizations/2026/10/26/"
    "01a178c9-0d81-73f2-96a2-42047619aba9/ui-system-v1"
)
OLD = ASSETS.parent / "release-visual-audit-001"
CAPS = {
    c["id"]: c["file"]
    for c in json.loads(
        (ROOT / "docs/review/release-visual-audit-001/capture-index.json").read_text()
    )
}


def target_for(request_path: str) -> Path:
    """Allow only design files and explicitly mapped review assets."""
    path = unquote(urlsplit(request_path).path)
    if path == "/tokens.css":
        return ROOT / "frontend/src/styles/tokens.css"
    if path.startswith("/baseline/"):
        key = Path(path).stem
        if key not in CAPS:
            raise FileNotFoundError(key)
        return OLD / CAPS[key]
    roots = {
        "/photos/": ROOT / "scripts/fixtures/botanical-v5",
        "/fonts/": ASSETS / "fonts",
        "/renders/": ASSETS / "renders",
    }
    for prefix, base in roots.items():
        if path.startswith(prefix):
            relative = path.removeprefix(prefix)
            break
    else:
        base, relative = DOCS, path.lstrip("/") or "index.html"
    target = (base / relative).resolve()
    if not target.is_relative_to(base.resolve()):
        raise PermissionError("Outside design asset root")
    return target


class Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        try:
            target = target_for(self.path)
        except PermissionError:
            self.send_error(403)
            return
        except FileNotFoundError:
            self.send_error(404)
            return
        if not target.is_file():
            self.send_error(404)
            return
        data = target.read_bytes()
        self.send_response(200)
        self.send_header(
            "Content-Type",
            mimetypes.guess_type(target.name)[0] or "application/octet-stream",
        )
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *_args: object) -> None:
        pass


if __name__ == "__main__":
    print(
        "Gate A design preview: http://localhost:15283 (read-only, no application API)",
        flush=True,
    )
    ThreadingHTTPServer(("127.0.0.1", 15283), Handler).serve_forever()
