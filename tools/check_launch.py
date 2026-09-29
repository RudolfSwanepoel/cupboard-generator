"""The launcher: no console, one server, a maximised window.

    python tools/check_launch.py

- with sys.stdout / sys.stderr None (what pythonw gives), `main()` sends both to
  the log, requests to the running server are served (api.Handler logs none of
  them — its log_message is silenced), and a traceback from a thread, the one
  thing that would still write to stderr, lands in the log;
- a port already taken is refused and reported as "already running" — with the
  port held by a plain socket, and by an old-style server that set SO_REUSEADDR,
  which on Windows used to let a second server bind the same port;
- without a console that is a message box and a line in the log;
- the window is asked for maximised, restoring to 1360 x 900 (a stand-in
  `webview` module records the call; no window is opened).

Nothing here writes the real output/app.log: the subprocess runs point LOG at a
temporary file.
"""
import os
import socket
import subprocess
import sys
import tempfile
import textwrap
import types
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import run_app  # noqa: E402

FAILS = []


def check(name, got, want):
    ok = got == want
    print(f"  {'ok   ' if ok else 'FAIL '} {name}: {got!r}" + ("" if ok else f"  want {want!r}"))
    if not ok:
        FAILS.append(name)


def free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


# Run in a child with no console streams, the way pythonw starts it. The child
# can print nothing, so it reports through the log file and its exit code; a
# message box is replaced by a line in the log.
HEADLESS = textwrap.dedent('''
    import sys, threading, time, urllib.request
    sys.path.insert(0, {root!r})
    import ctypes
    import run_app
    run_app.LOG = {log!r}
    ctypes.windll.user32.MessageBoxW = lambda h, text, title, flags: print("MESSAGEBOX", text.splitlines()[0])
    sys.stdout = sys.stderr = None
    mode, port = {mode!r}, {port!r}
    if mode == "serve":
        threading.Thread(target=run_app.main, args=(["--port", str(port), "--no-window"],), daemon=True).start()
        for _ in range(100):
            try:
                body = urllib.request.urlopen("http://127.0.0.1:%d/" % port, timeout=2).read()
                break
            except OSError:
                time.sleep(0.1)
        print("GOT", len(body))
        try:
            urllib.request.urlopen("http://127.0.0.1:%d/no-such-thing" % port, timeout=2)
        except Exception as e:
            print("MISSING", getattr(e, "code", e))
        # what can still reach stderr from a thread: a traceback
        t = threading.Thread(target=lambda: 1 / 0)
        t.start()
        t.join()
        sys.stdout.flush()
        raise SystemExit(0)
    raise SystemExit(run_app.main(["--port", str(port), "--no-window"]))
''')


def headless(mode, port, seed=""):
    fd, log = tempfile.mkstemp(suffix=".log")
    os.close(fd)
    with open(log, "w", encoding="utf-8") as fh:
        fh.write(seed)
    code = subprocess.run([sys.executable, "-c", HEADLESS.format(root=ROOT, log=log, mode=mode, port=port)],
                          cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=60).returncode
    with open(log, encoding="utf-8") as fh:
        text = fh.read()
    os.remove(log)
    return code, text


def no_console():
    print("no console: stdout and stderr go to the log")
    port = free_port()
    code, log = headless("serve", port)
    check("the child exits cleanly", code, 0)
    check("the log says where it is serving", f"serving on http://127.0.0.1:{port}/" in log, True)
    check("a request is served", "GOT " in log and "GOT 0" not in log, True)
    check("and an unknown path is a 404, not a dead handler", "MISSING 404" in log, True)
    # api.Handler silences log_message, so requests themselves write nothing;
    # what does reach stderr from a thread is a traceback, and it lands here
    check("one traceback in the log, the deliberate one", log.count("Traceback"), 1)
    check("a thread's traceback lands in the log", "ZeroDivisionError" in log, True)
    check("the log is overwritten at each start, not appended to", _overwrites(), True)


def _overwrites():
    saved = sys.stdout, sys.stderr
    fd, log = tempfile.mkstemp(suffix=".log")
    os.close(fd)
    with open(log, "w", encoding="utf-8") as fh:
        fh.write("the last run\n")
    try:
        fh = run_app.redirect_to_log(log)
        print("this run")
        fh.close()
    finally:
        sys.stdout, sys.stderr = saved
    with open(log, encoding="utf-8") as fh:
        text = fh.read()
    os.remove(log)
    return text == "this run\n"


def port_in_use():
    print("\na port already taken is 'already running', and no second server starts")
    said = []
    real_tell = run_app.tell
    run_app.tell = lambda message, headless: said.append((message, headless))
    try:
        s = socket.socket()
        s.bind(("127.0.0.1", 0))
        s.listen()
        port = s.getsockname()[1]
        code = run_app.main(["--port", str(port), "--no-window"])
        s.close()
        check("held by a socket: main() returns 1", code, 1)
        check("  and says the app is already running",
              bool(said) and said[-1][0].startswith(f"The Cupboard App is already running, or port {port} is in use"), True)

        said.clear()
        old = ThreadingHTTPServer(("127.0.0.1", 0), BaseHTTPRequestHandler)   # SO_REUSEADDR, as before
        port = old.server_address[1]
        code = run_app.main(["--port", str(port), "--no-window"])
        old.server_close()
        check("held by an old-style SO_REUSEADDR server: refused too", code, 1)
        check("  already running", bool(said) and "already running" in said[-1][0], True)

        said.clear()
        first = run_app.serve(free_port())
        port = first.server_address[1]
        code = run_app.main(["--port", str(port), "--no-window"])
        first.shutdown()
        first.server_close()
        check("held by the app itself (a second launch): refused", code, 1)
        check("  already running", bool(said) and "already running" in said[-1][0], True)
    finally:
        run_app.tell = real_tell

    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    s.listen()
    code, log = headless("start", s.getsockname()[1], seed="the running app's log\n")
    s.close()
    check("with no console: exits 1", code, 1)
    check("  shows a message box saying so",
          "MESSAGEBOX The Cupboard App is already running" in log, True)
    check("  and appends to the running app's log rather than wiping it",
          log.startswith("the running app's log\n"), True)


def maximised():
    print("\nthe window is asked for maximised")
    calls = []
    fake = types.ModuleType("webview")
    fake.create_window = lambda *a, **k: calls.append((a, k)) or object()
    fake.start = lambda *a, **k: None
    real = sys.modules.get("webview")
    sys.modules["webview"] = fake
    try:
        code = run_app.main(["--port", str(free_port())])
    finally:
        if real is None:
            sys.modules.pop("webview", None)
        else:
            sys.modules["webview"] = real
        from app.api import set_window
        set_window(None)
    check("main() returns 0 once the window closes", code, 0)
    check("one window", len(calls), 1)
    k = calls[0][1] if calls else {}
    check("maximized=True", k.get("maximized"), True)
    check("restoring to 1360 x 900", (k.get("width"), k.get("height")), (1360, 900))
    check("not full screen", k.get("fullscreen", False), False)


def main():
    no_console()
    port_in_use()
    maximised()
    print(f"\n{'ALL OK' if not FAILS else str(len(FAILS)) + ' FAILED: ' + str(FAILS)}")
    return 1 if FAILS else 0


if __name__ == "__main__":
    raise SystemExit(main())
