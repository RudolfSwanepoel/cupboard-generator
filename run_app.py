"""Start the local server and open the app.

    python run_app.py [--port 8765] [--no-window]

Uses pywebview for a desktop window when it is installed, otherwise the default
browser. Either way it is the same server on 127.0.0.1, so the endpoints can be
driven directly by a test or by curl.
"""
import argparse
import os
import sys
import threading
import webbrowser
from http.server import ThreadingHTTPServer

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.api import Handler  # noqa: E402


def serve(port: int) -> ThreadingHTTPServer:
    httpd = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--no-window", action="store_true",
                    help="serve only; do not open a window or browser")
    args = ap.parse_args()

    httpd = serve(args.port)
    url = f"http://127.0.0.1:{httpd.server_address[1]}/"
    print(f"CupboardApp serving on {url}")

    if args.no_window:
        print("Ctrl-C to stop.")
        try:
            threading.Event().wait()
        except KeyboardInterrupt:
            pass
        return

    try:
        import webview
    except ImportError:
        print("pywebview not installed — opening the default browser instead.")
        webbrowser.open(url)
        print("Ctrl-C to stop.")
        try:
            threading.Event().wait()
        except KeyboardInterrupt:
            pass
        return

    webview.create_window("CupboardApp", url, width=1360, height=900)
    webview.start()


if __name__ == "__main__":
    main()
