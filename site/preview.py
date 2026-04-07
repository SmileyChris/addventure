#!/usr/bin/env python3
"""Live-reload dev server for the Addventure site."""

import http.server
import os
import queue
import shutil
import socketserver
import subprocess
import sys
import threading
import time
import webbrowser
from pathlib import Path

try:
    from watchdog.events import FileSystemEventHandler
    from watchdog.observers import Observer
except ImportError:
    sys.exit("watchdog not installed — run: uv sync --group dev")

SITE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SITE_DIR.parent
BUILD_DIR = SITE_DIR / "build"
DOCS_DIR = PROJECT_DIR / "docs"

RELOAD_SNIPPET = b"""\
<script>
(function() {
  var es = new EventSource('/__reload');
  es.onmessage = function() { location.reload(); };
  es.onerror = function() {
    es.close();
    setTimeout(function() { location.reload(); }, 1500);
  };
})();
</script>"""

_sse_clients: list[queue.Queue] = []
_sse_lock = threading.Lock()
_last_overlay = 0.0


def broadcast_reload():
    with _sse_lock:
        for q in list(_sse_clients):
            try:
                q.put_nowait("reload")
            except queue.Full:
                pass


def copy_overlay():
    """Copy the landing page and assets into the build directory."""
    global _last_overlay
    now = time.monotonic()
    if now - _last_overlay < 1.0:
        return
    _last_overlay = now
    shutil.copy2(SITE_DIR / "index.html", BUILD_DIR / "index.html")
    dest = BUILD_DIR / "assets"
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(SITE_DIR / "assets", dest)


def rebuild_docs():
    """Rebuild docs via zensical, then re-apply overlay."""
    print("\033[33m\u27f3 Rebuilding docs\u2026\033[0m", flush=True)
    t0 = time.monotonic()
    result = subprocess.run(
        ["zensical", "build", "-c"],
        cwd=str(PROJECT_DIR),
        capture_output=True,
        text=True,
    )
    elapsed = time.monotonic() - t0
    if result.returncode == 0:
        copy_overlay()
        print(f"\033[32m\u2713 Docs rebuilt in {elapsed:.1f}s\033[0m", flush=True)
        broadcast_reload()
    else:
        print(f"\033[31m\u2717 Docs build failed ({elapsed:.1f}s)\033[0m", flush=True)
        if result.stderr:
            print(result.stderr, end="", flush=True)
        if result.stdout:
            print(result.stdout, end="", flush=True)


def reload_overlay():
    """Copy overlay and notify browser."""
    copy_overlay()
    print("\033[32m\u2713 Overlay updated\033[0m", flush=True)
    broadcast_reload()


class DebouncedHandler(FileSystemEventHandler):
    """Debounces file events and calls a callback."""

    def __init__(self, callback, delay=0.3):
        self._callback = callback
        self._delay = delay
        self._timer: threading.Timer | None = None
        self._lock = threading.Lock()

    def on_any_event(self, event):
        if event.is_directory:
            return
        name = os.path.basename(event.src_path)
        if name.startswith(".") or name == "__pycache__":
            return
        with self._lock:
            if self._timer:
                self._timer.cancel()
            self._timer = threading.Timer(self._delay, self._callback)
            self._timer.daemon = True
            self._timer.start()


class OverlayHandler(DebouncedHandler):
    """Watches site/ for overlay changes, ignoring build/ and .py files."""

    def on_any_event(self, event):
        if event.is_directory:
            return
        path = Path(event.src_path)
        if path.is_relative_to(BUILD_DIR):
            return
        if path.suffix == ".py" or path.suffix == ".sh":
            return
        super().on_any_event(event)


class ReloadHTTPHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(BUILD_DIR), **kwargs)

    def log_message(self, format, *args):
        pass  # silence request logs

    def do_GET(self):
        if self.path == "/__reload":
            return self._handle_sse()

        # Serve HTML with injected reload snippet
        path = self.translate_path(self.path)
        if os.path.isdir(path):
            path = os.path.join(path, "index.html")
        if path.endswith(".html") and os.path.isfile(path):
            with open(path, "rb") as f:
                content = f.read()
            content = content.replace(b"</body>", RELOAD_SNIPPET + b"\n</body>")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", len(content))
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            self.wfile.write(content)
            return

        super().do_GET()

    def _handle_sse(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("X-Accel-Buffering", "no")
        self.end_headers()

        q: queue.Queue = queue.Queue(maxsize=8)
        with _sse_lock:
            _sse_clients.append(q)
        try:
            self.wfile.write(b": connected\n\n")
            self.wfile.flush()
            while True:
                try:
                    msg = q.get(timeout=30)
                    self.wfile.write(f"data: {msg}\n\n".encode())
                    self.wfile.flush()
                except queue.Empty:
                    self.wfile.write(b": keepalive\n\n")
                    self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError, OSError):
            pass
        finally:
            with _sse_lock:
                _sse_clients.remove(q)


def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000

    # Initial build
    if not BUILD_DIR.is_dir():
        print("Building site\u2026", flush=True)
        subprocess.run(
            ["zensical", "build", "-c"], cwd=str(PROJECT_DIR), check=True
        )
    copy_overlay()

    # File watchers — watch source dirs only (not site/build/)
    observer = Observer()
    observer.schedule(DebouncedHandler(rebuild_docs), str(DOCS_DIR), recursive=True)
    overlay_handler = OverlayHandler(reload_overlay, delay=0.2)
    observer.schedule(overlay_handler, str(SITE_DIR / "assets"), recursive=True)
    observer.schedule(overlay_handler, str(SITE_DIR), recursive=False)
    observer.start()

    # Start server
    socketserver.TCPServer.allow_reuse_address = True
    socketserver.ThreadingTCPServer.daemon_threads = True
    try:
        with socketserver.ThreadingTCPServer(("", port), ReloadHTTPHandler) as server:
            url = f"http://localhost:{port}"
            print(f"\033[1mServing at {url}\033[0m (live reload)")
            print("Watching: docs/, site/index.html, site/assets/")
            threading.Timer(0.5, webbrowser.open, args=[url]).start()
            server.serve_forever()
    except OSError:
        sys.exit(f"Error: port {port} is already in use")
    except KeyboardInterrupt:
        pass
    finally:
        observer.stop()
        observer.join()


if __name__ == "__main__":
    main()
