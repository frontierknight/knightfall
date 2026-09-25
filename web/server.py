"""Knightfall web gateway (E3, serving slice) — serve the replay console and past trajectories.

A tiny stdlib HTTP server so a browser can open the replay viewer against a running range and load
real trajectories from trajectories/, instead of only drag-and-drop. This is the "serve it" part of
the web console (DESIGN §13.5); the live terminal relay (E3/E4) builds on top later.

Routes:
  GET /                      -> web/replay.html
  GET /replay.html           -> web/replay.html
  GET /api/trajectories      -> JSON: [{"name","scenario","outcome","score","max"}...] (newest first)
  GET /api/trajectory?name=X -> raw JSONL for that trajectory (X must be a *.jsonl basename)

Safety: only files directly inside trajectories/ with a .jsonl name are served; the name is reduced
to its basename so path traversal cannot escape the directory. Binds to 127.0.0.1 by default.

Run:  python3 run.py web            # then open http://127.0.0.1:8000
Env:  KNIGHTFALL_WEB_HOST (default 127.0.0.1), KNIGHTFALL_WEB_PORT (default 8000)
"""
from __future__ import annotations
import json
import os
import sys
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.join(HERE, "..")
TRAJ_DIR = os.path.join(REPO, "trajectories")
PAGE = os.path.join(HERE, "replay.html")
sys.path.insert(0, os.path.join(REPO, "harness"))
sys.path.insert(0, os.path.join(REPO, "challenges"))
from session import Session  # noqa: E402


class SessionManager:
    """Drives live challenge sessions server-side so a browser can play one (E4 core).

    `make` is injectable (defaults to the challenge registry) so this is unit-testable without ROS:
    a test passes a fake make() returning (scenario, fake_backend). Each browser session is one
    harness Session, keyed by an opaque id; ground truth stays server-side, never sent to the client
    beyond the confirmed checkpoint names.
    """

    def __init__(self, make=None):
        self._make = make
        self._sessions = {}

    def _resolve_make(self):
        if self._make:
            return self._make
        from registry import make  # imported lazily; only needed for real play
        return make

    def start(self, task):
        scenario, backend = self._resolve_make()(task)
        sid = uuid.uuid4().hex
        out = os.path.join(TRAJ_DIR, f"{scenario['id']}_web_{sid[:8]}.jsonl")
        s = Session(scenario, backend, actor_kind="human", actor_name=f"web:{sid[:8]}", out_path=out)
        briefing, err = s.start()
        if err:
            return {"error": err}
        self._sessions[sid] = s
        return {"id": sid, "scenario": scenario["id"], "briefing": briefing,
                "budget_left": s.budget_left()}

    def action(self, sid, cmd):
        s = self._sessions.get(sid)
        if not s:
            return {"error": "unknown session"}
        obs = s.run_command(cmd)
        return {"observation": obs, "checkpoints": sorted(s.backend.confirm_checkpoints()),
                "budget_left": s.budget_left(), "over_budget": s.over_budget()}

    def submit(self, sid, value):
        s = self._sessions.get(sid)
        if not s:
            return {"error": "unknown session"}
        ok = s.submit(value)
        return {"accepted": ok, "checkpoints": sorted(s.backend.confirm_checkpoints()),
                "budget_left": s.budget_left(), "over_budget": s.over_budget()}

    def finish(self, sid):
        s = self._sessions.pop(sid, None)
        if not s:
            return {"error": "unknown session"}
        return s.finish()


def _list_trajectories():
    out = []
    try:
        names = [n for n in os.listdir(TRAJ_DIR) if n.endswith(".jsonl")]
    except OSError:
        names = []
    for n in names:
        path = os.path.join(TRAJ_DIR, n)
        meta, result = {}, {}
        try:
            with open(path) as fh:
                for line in fh:
                    if not line.strip():
                        continue
                    rec = json.loads(line)
                    if rec.get("type") == "meta":
                        meta = rec
                    elif rec.get("type") == "result":
                        result = rec
        except (OSError, ValueError):
            continue
        out.append({
            "name": n,
            "scenario": meta.get("scenario_id", "?"),
            "actor": (meta.get("actor") or {}).get("name", "?"),
            "outcome": result.get("outcome"),
            "score": result.get("final_score"),
            "max": result.get("max_score") or meta.get("max_score"),
            "mtime": os.path.getmtime(path),
        })
    out.sort(key=lambda r: r["mtime"], reverse=True)
    return out


def _safe_traj_path(name):
    """Resolve `name` to a *.jsonl file directly inside trajectories/, or None."""
    base = os.path.basename(name or "")
    if not base.endswith(".jsonl"):
        return None
    path = os.path.join(TRAJ_DIR, base)
    if os.path.dirname(os.path.abspath(path)) != os.path.abspath(TRAJ_DIR):
        return None
    return path if os.path.isfile(path) else None


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, body, ctype="application/json"):
        data = body if isinstance(body, bytes) else body.encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        u = urlparse(self.path)
        if u.path in ("/", "/replay.html"):
            try:
                with open(PAGE, "rb") as fh:
                    self._send(200, fh.read(), "text/html; charset=utf-8")
            except OSError:
                self._send(404, b"replay.html not found", "text/plain")
        elif u.path == "/api/trajectories":
            self._send(200, json.dumps(_list_trajectories()))
        elif u.path == "/api/trajectory":
            name = (parse_qs(u.query).get("name") or [""])[0]
            path = _safe_traj_path(name)
            if not path:
                self._send(404, json.dumps({"error": "not found"}))
                return
            with open(path, "rb") as fh:
                self._send(200, fh.read(), "application/x-ndjson")
        else:
            self._send(404, json.dumps({"error": "not found"}))

    def do_POST(self):
        u = urlparse(self.path)
        routes = {
            "/api/session/start":  lambda b: MANAGER.start(b.get("task", "")),
            "/api/session/action": lambda b: MANAGER.action(b.get("id", ""), b.get("cmd", "")),
            "/api/session/submit": lambda b: MANAGER.submit(b.get("id", ""), b.get("value", "")),
            "/api/session/finish": lambda b: MANAGER.finish(b.get("id", "")),
        }
        fn = routes.get(u.path)
        if not fn:
            self._send(404, json.dumps({"error": "not found"}))
            return
        try:
            n = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(n) or "{}") if n else {}
            if not isinstance(body, dict):
                raise ValueError("body must be an object")
        except (ValueError, OSError):
            self._send(400, json.dumps({"error": "bad request body"}))
            return
        try:
            self._send(200, json.dumps(fn(body)))
        except Exception as e:  # noqa: BLE001 - report, don't crash the server
            self._send(500, json.dumps({"error": str(e)}))

    def log_message(self, *a):
        pass  # quiet


MANAGER = SessionManager()


def main():
    host = os.environ.get("KNIGHTFALL_WEB_HOST", "127.0.0.1")
    port = int(os.environ.get("KNIGHTFALL_WEB_PORT", "8000"))
    srv = ThreadingHTTPServer((host, port), Handler)
    print(f"Knightfall replay console on http://{host}:{port}  (Ctrl-C to stop)")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        srv.server_close()


if __name__ == "__main__":
    main()
