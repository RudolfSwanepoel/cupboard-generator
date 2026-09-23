"""Drive the 3D view in the running app with a real (headless) browser.

    python run_app.py --no-window --port 8766      # in another window
    python tools/ui_check_3d.py [--port 8766] [--stage f1]

Needs Playwright (`pip install playwright && python -m playwright install
chromium`) — the ONLY third-party dependency anywhere near this app, and only
for this script: the engine, the server and the UI have none. If it is not
installed this script says so and exits 0 rather than failing a check that was
never run.

WebGL in headless Chromium is software-rendered through SwiftShader, which is
what `--use-angle=swiftshader --enable-unsafe-swiftshader` asks for.

What is exercised is the brief's acceptance list, stage by stage, against
`jobs/Test.json` unless a check says otherwise. The Python checks in
`tools/check_scene.py` are the unit level; this is the "in the running app,
with a real mouse" level that the brief asks for on top of them.
"""
import argparse
import json
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

try:
    from playwright.sync_api import sync_playwright
except ImportError:                                            # pragma: no cover
    print("playwright is not installed; skipping the browser checks "
          "(pip install playwright && python -m playwright install chromium)")
    sys.exit(0)

ap = argparse.ArgumentParser()
ap.add_argument("--port", type=int, default=8766)
ap.add_argument("--stage", default="all")
ap.add_argument("--headed", action="store_true")
args = ap.parse_args()
URL = f"http://127.0.0.1:{args.port}/"

FAILS = []


def check(label, got, want):
    ok = got == want
    print(f"  {'ok  ' if ok else 'FAIL'}  {label}: {got!r}" + ("" if ok else f"  (wanted {want!r})"))
    if not ok:
        FAILS.append(label)
    return ok


def check_true(label, got):
    return check(label, bool(got), True)


def load_job(page, name):
    """Open a saved job by name, through the app's own controls."""
    page.wait_for_function("() => document.querySelectorAll('#joblist option').length > 1",
                           timeout=15000)
    page.select_option("#joblist", name + ".json")
    page.click("#load")
    page.wait_for_function("() => S.job && S.res && S.job.name === %s" % json.dumps(name),
                           timeout=15000)


def open_3d(page):
    page.click('nav [data-tab="view3d"]')
    page.wait_for_function("() => typeof V3D === 'object' && V3D !== null", timeout=30000)
    page.wait_for_selector("#v3dview canvas", timeout=15000)


def stage_f1(pw):
    print("\nF1 — vendoring, static routes, lazy loading, offline")
    browser = pw.chromium.launch(headless=not args.headed, args=[
        "--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist"])
    ctx = browser.new_context(viewport={"width": 1400, "height": 900})
    page = ctx.new_page()
    hosts, errors, requests = set(), [], []
    page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
    page.on("pageerror", lambda e: errors.append(str(e)))

    # Offline acceptance: anything that is not this server is refused, and the
    # tab has to work anyway.
    def route(r):
        from urllib.parse import urlparse
        host = urlparse(r.request.url).hostname
        hosts.add(host)
        requests.append(r.request.url)
        if host != "127.0.0.1":
            return r.abort()
        r.continue_()
    page.route("**/*", route)

    page.goto(URL)
    page.wait_for_function("() => S.def !== null", timeout=15000)
    before = set(requests)
    check("view3d.js is not loaded before the tab is opened",
          any("view3d.js" in u for u in before), False)
    check("nor is three.js", any("/vendor/" in u for u in before), False)
    load_job(page, "Test")
    open_3d(page)
    time.sleep(0.8)
    check("every request went to this server only", sorted(hosts), ["127.0.0.1"])
    fetched = [u.split("/", 3)[3] for u in requests if "/vendor/" in u or "view3d" in u]
    check("the module and the two libraries were fetched, and nothing else off /vendor/",
          sorted(set(fetched)),
          ["app/view3d.js", "vendor/camera-controls/camera-controls.module.js",
           "vendor/three/three.core.js", "vendor/three/three.module.js"])
    check("no console errors", errors, [])
    check_true("a WebGL canvas is in the viewport",
               page.evaluate("() => { const c = document.querySelector('#v3dview canvas');"
                             " return !!(c && (c.getContext('webgl2') || c.getContext('webgl'))); }"))
    h = page.evaluate("() => document.getElementById('v3d').getBoundingClientRect().height")
    win = page.evaluate("() => window.innerHeight")
    check_true("the viewport fills the window below the tab bar (no page scroll)",
               h > 300 and page.evaluate("() => document.documentElement.scrollHeight <= window.innerHeight + 2"))
    # Content types and the whitelist.
    for path, ctype in (("/vendor/three/three.module.js", "text/javascript"),
                        ("/vendor/three/LICENSE", "text/plain"),
                        ("/vendor/camera-controls/LICENSE", "text/plain"),
                        ("/app/view3d.js", "text/javascript")):
        r = page.request.get(URL.rstrip("/") + path)
        check(f"{path} served as {ctype}", (r.status, r.headers.get("content-type", "").split(";")[0]),
              (200, ctype))
    for path in ("/vendor/../api.py", "/vendor/three/../../api.py", "/app/api.py",
                 "/vendor/three/nope.js", "/vendor/", "/vendor/three/"):
        r = page.request.get(URL.rstrip("/") + path)
        check(f"{path} is refused", r.status, 404)
    check("the static route sends the house cache header",
          page.request.get(URL.rstrip("/") + "/app/view3d.js").headers.get("cache-control"), "no-store")

    # Switching away stops rendering; coming back renders again.
    page.click('nav [data-tab="cabinets"]')
    check("hidden tab: the view says it is not visible",
          page.evaluate("() => V3D.setVisible && document.getElementById('tab-view3d').hidden"), True)
    page.click('nav [data-tab="view3d"]')
    time.sleep(0.3)
    check("no console errors after switching tabs", errors, [])
    ctx.close()

    # No WebGL: one line, the rest of the app untouched.
    ctx2 = browser.new_context(viewport={"width": 1400, "height": 900})
    page2 = ctx2.new_page()
    errs2 = []
    page2.on("pageerror", lambda e: errs2.append(str(e)))
    page2.add_init_script("""
      const orig = HTMLCanvasElement.prototype.getContext;
      HTMLCanvasElement.prototype.getContext = function (kind, ...rest) {
        if (kind === 'webgl' || kind === 'webgl2' || kind === 'experimental-webgl') return null;
        return orig.call(this, kind, ...rest);
      };""")
    page2.goto(URL)
    page2.wait_for_function("() => S.def !== null", timeout=15000)
    load_job(page2, "Test")
    page2.click('nav [data-tab="view3d"]')
    page2.wait_for_function("() => typeof V3D === 'object' && V3D !== null", timeout=30000)
    note = page2.locator("#v3dview .v3dnote").text_content()
    check_true("without WebGL the tab says so in one line", "WebGL" in note)
    check("and nothing else broke", errs2, [])
    page2.click('nav [data-tab="cabinets"]')
    check_true("the rest of the app still works",
               page2.evaluate("() => document.querySelectorAll('#cabtable tr').length > 3"))
    ctx2.close()
    browser.close()


STAGES = {"f1": stage_f1}

with sync_playwright() as pw:
    for name, fn in STAGES.items():
        if args.stage in ("all", name):
            fn(pw)

print()
if FAILS:
    print(f"{len(FAILS)} FAILED: " + "; ".join(FAILS))
    sys.exit(1)
print("ui_check_3d: all good")
