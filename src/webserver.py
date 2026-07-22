"""Local HTTP server that serves the web panel and the live match data.

The main loop calls update(payload) with the latest heartbeat snapshot; the
browser page (web/) polls /data and renders it. /quit stops the whole app.
"""

import json
import os
import socket
import sys
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer


def _web_dir():
    if getattr(sys, "frozen", False):
        base = os.path.dirname(sys.executable)
    else:
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, "web")


WEB_DIR = _web_dir()

_lock = threading.Lock()
_state = {"data": {"state": None, "players": {}}}
_on_quit = None
_on_lang = None
_info = {"lan_ip": None, "port": None}
# Panelin seçili dili (tarayıcı /lang ile bildirir). Discord RPC bunu izler.
_lang = {"value": "tr"}


def update(payload):
    """Thread-safe: store the latest snapshot for the browser to fetch."""
    with _lock:
        _state["data"] = payload


def get_lang():
    """Panelin en son bildirdiği dili döndürür ('tr' / 'en')."""
    with _lock:
        return _lang["value"]


class _Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=WEB_DIR, **kwargs)

    def log_message(self, *args):
        pass  # stay quiet

    def end_headers(self):
        # Never let the browser cache the panel files; always serve the latest
        # app.js/style.css/index.html so UI changes show up on a plain refresh.
        self.send_header("Cache-Control", "no-store, must-revalidate")
        super().end_headers()

    def _send_bytes(self, body, ctype="application/json; charset=utf-8"):
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        try:
            self.wfile.write(body)
        except Exception:
            pass

    def do_GET(self):
        path = self.path.split("?")[0]
        if path == "/data":
            with _lock:
                body = json.dumps(_state["data"]).encode("utf-8")
            self._send_bytes(body)
            return
        if path == "/info":
            body = json.dumps(_info).encode("utf-8")
            self._send_bytes(body)
            return
        if path == "/lang":
            # Panel dil seçimini bildirir: /lang?l=en . Discord RPC bunu izler.
            from urllib.parse import urlparse, parse_qs
            qs = parse_qs(urlparse(self.path).query)
            val = (qs.get("l") or [""])[0].lower()
            if val in ("tr", "en"):
                with _lock:
                    changed = _lang["value"] != val
                    _lang["value"] = val
                if changed and _on_lang:
                    try:
                        _on_lang(val)
                    except Exception:
                        pass
            self._send_bytes(b"ok", "text/plain")
            return
        if path == "/quit":
            self._send_bytes(b"ok", "text/plain")
            if _on_quit:
                threading.Thread(target=_on_quit, daemon=True).start()
            return
        if path == "/":
            self.path = "/index.html"
        return super().do_GET()


def get_lan_ip():
    """Best-effort local network IP so the panel can be opened from a phone
    on the same Wi-Fi. Returns None if it can't be determined."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # No packets are actually sent; this just picks the outbound interface.
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except Exception:
        return None
    finally:
        s.close()


def start(port, on_quit=None, host="0.0.0.0", on_lang=None):
    """Start the HTTP server on a background thread. Returns the server.

    Binds to 0.0.0.0 by default so the panel is reachable from other devices
    on the same local network (e.g. your phone over Wi-Fi). on_lang(lang) is
    called when the panel changes its language (for Discord RPC sync)."""
    global _on_quit, _on_lang
    _on_quit = on_quit
    _on_lang = on_lang
    _info["lan_ip"] = get_lan_ip()
    _info["port"] = port
    httpd = ThreadingHTTPServer((host, port), _Handler)
    httpd.daemon_threads = True
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd
