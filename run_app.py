"""Start the local server and open the app.

    python run_app.py [--port 8765] [--no-window]
    pythonw run_app.py                      # no console: the desktop shortcut

Uses pywebview for a desktop window when it is installed, otherwise the default
browser. Either way it is the same server on 127.0.0.1, so the endpoints can be
driven directly by a test or by curl.

Under pythonw there is no console: `sys.stdout` and `sys.stderr` are None, and
`http.server` logs every request to stderr, so both are pointed at
`output/app.log` (the last run's only). Until the port is ours the output is
held in memory, so a second launch refused because the app is already open
appends to the running app's log rather than wiping it. A failure to start is written there and
shown in a message box, since nothing else would show it.

A demo build (`Build Demo.bat`, `app/demo.py`) refuses to start past its date,
or with the clock put back, in a message box, and titles its window with the
date it runs until. Anywhere else `demo.DEMO` is False and nothing changes.
"""
import argparse
import errno
import io
import os
import socket
import sys
import threading
import traceback
import webbrowser
from http.server import ThreadingHTTPServer

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)

from app import demo  # noqa: E402  — off unless `Build Demo.bat` built this

LOG = os.path.join(ROOT, "output", "app.log")
DEFAULT_PORT = 8765
TITLE = "Cupboard App"

# The window opens maximised; this is the size it restores to.
WINDOW = {"width": 1360, "height": 900, "maximized": True}


class PortInUse(Exception):
    """The port is taken, which almost always means the app is already open."""


class Server(ThreadingHTTPServer):
    """Refuses a port something else already holds.

    `HTTPServer` sets SO_REUSEADDR, and on Windows that lets a second server bind
    a port the first is still listening on, so a second launch used to start a
    second server on 8765 without a word. An exclusive bind makes the second one
    fail, which is what lets it say the app is already running."""
    allow_reuse_address = False

    def server_bind(self):
        if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        super().server_bind()


def serve(port: int) -> ThreadingHTTPServer:
    from app.api import Handler
    try:
        httpd = Server(("127.0.0.1", port), Handler)
    except OSError as e:
        # 10048 is WSAEADDRINUSE; 10013 is what Windows says when the holder
        # bound it exclusively.
        if e.errno in (errno.EADDRINUSE, errno.EACCES) or getattr(e, "winerror", None) in (10048, 10013):
            raise PortInUse(port) from e
        raise
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd


def no_console() -> bool:
    return sys.stdout is None or sys.stderr is None


def redirect_to_log(path: str = None, mode: str = "w"):
    """Point stdout and stderr at the log, line-buffered: overwritten ("w") on a
    real start, appended to ("a") by a launch that was refused. Whatever was
    held in memory before it is written first."""
    path = path or LOG
    held = sys.stdout.getvalue() if isinstance(sys.stdout, io.StringIO) else ""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fh = open(path, mode, encoding="utf-8", buffering=1)
    fh.write(held)
    sys.stdout = sys.stderr = fh
    return fh


def holding() -> bool:
    return isinstance(sys.stdout, io.StringIO)


def tell(message: str, headless: bool):
    """Say something that must be seen: a message box when there is no console."""
    print(message, flush=True)
    if headless and sys.platform == "win32":
        import ctypes
        # MB_OK | MB_ICONERROR | MB_SETFOREGROUND | MB_TOPMOST
        ctypes.windll.user32.MessageBoxW(None, message, demo.title() if demo.DEMO else TITLE,
                                         0x10 | 0x10000 | 0x40000)


def wait_forever():
    print("Ctrl-C to stop.")
    try:
        threading.Event().wait()
    except KeyboardInterrupt:
        pass


def main(argv=None) -> int:
    headless = no_console()
    if headless:
        sys.stdout = sys.stderr = io.StringIO()   # held until the port is ours
    stop = demo.refusal()                         # None outside a demo build
    if stop:
        # A demo is double-clicked, so the box shows even with a console.
        tell(stop, sys.platform == "win32")
        return 1
    try:
        return start(argv)
    except PortInUse as e:
        if holding():
            redirect_to_log(mode="a")
        tell(f"The Cupboard App is already running, or port {e.args[0]} is in use.\n\n"
             f"Look for its window on the taskbar.", headless)
    except Exception:
        if holding():
            redirect_to_log()
        traceback.print_exc()
        tell(f"The Cupboard App did not start.\n\nThe reason is in\n{LOG}"
             if headless else "The Cupboard App did not start. The reason is above.", headless)
    return 1


def start(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=DEFAULT_PORT)
    ap.add_argument("--no-window", action="store_true",
                    help="serve only; do not open a window or browser")
    args = ap.parse_args(argv)

    httpd = serve(args.port)
    if holding():
        redirect_to_log()
    url = f"http://127.0.0.1:{httpd.server_address[1]}/"
    print(f"CupboardApp serving on {url}", flush=True)

    if args.no_window:
        wait_forever()
        return 0

    try:
        import webview
    except ImportError:
        print("pywebview not installed — opening the default browser instead.")
        webbrowser.open(url)
        wait_forever()
        return 0

    from app.api import set_window
    # The handlers need the window for one thing only: the native Open dialog
    # behind Browse… on a board picture. Everything else is the HTTP server, and
    # under --no-window or the browser fallback there is simply no window — the
    # picker says so and the browser's own file input takes over.
    set_window(webview.create_window(demo.title() if demo.DEMO else "CupboardApp", url, **WINDOW))
    webview.start()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
