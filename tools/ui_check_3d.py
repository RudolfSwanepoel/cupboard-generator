"""Drive the 3D view in the running app with a real (headless) browser.

    python run_app.py --no-window --port 8766      # in another window
    python tools/ui_check_3d.py [--port 8766] [--stage f1|f3|...|all]

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
import math
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
LAUNCH = ["--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist"]

FAILS = []


def check(label, got, want):
    ok = got == want
    print(f"  {'ok  ' if ok else 'FAIL'}  {label}: {got!r}" + ("" if ok else f"  (wanted {want!r})"))
    if not ok:
        FAILS.append(label)
    return ok


def check_true(label, got, detail=""):
    return check(label + (f" [{detail}]" if detail else ""), bool(got), True)


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


def wait_scene(page):
    page.wait_for_function("() => !S.sceneStale && V3D.memory().groups > 0", timeout=20000)
    settle(page)


def settle(page):
    page.wait_for_function("() => V3D.idle()", timeout=10000)
    time.sleep(0.15)


def viewport_origin(page):
    r = page.evaluate("() => { const r = document.querySelector('#v3dview canvas').getBoundingClientRect();"
                      " return [r.left, r.top, r.width, r.height]; }")
    return r


def project(page, x, y, z):
    return page.evaluate(f"() => V3D.project({x}, {y}, {z})")


def new_page(browser, errors):
    ctx = browser.new_context(viewport={"width": 1400, "height": 900})
    page = ctx.new_page()
    page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.on("dialog", lambda d: d.accept())        # "discard unsaved changes?" — yes
    return ctx, page


def edit_and_wait(page, js):
    """Run an edit in the page and wait until the 3D view has caught up with the
    compute it caused: the scene fetch after this edit has come back."""
    seq = page.evaluate("() => sceneSeq")
    page.evaluate(js)
    page.wait_for_function(f"() => sceneSeq > {seq} && !S.sceneStale && sceneTimer === null", timeout=15000)


# ---------------------------------------------------------------------------

def stage_f1(pw):
    print("\nF1 — vendoring, static routes, lazy loading, offline")
    browser = pw.chromium.launch(headless=not args.headed, args=LAUNCH)
    errors = []
    ctx, page = new_page(browser, errors)
    hosts, requests = set(), []

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
    wait_scene(page)
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
    check_true("the viewport fills the window below the tab bar (no page scroll)",
               h > 300 and page.evaluate("() => document.documentElement.scrollHeight <= window.innerHeight + 2"))
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
    page.click('nav [data-tab="cabinets"]')
    check("hidden tab: the view says it is not visible",
          page.evaluate("() => V3D.setVisible && document.getElementById('tab-view3d').hidden"), True)
    page.click('nav [data-tab="view3d"]')
    time.sleep(0.3)
    check("no console errors after switching tabs", errors, [])
    ctx.close()

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


# ---------------------------------------------------------------------------

def stage_f3(pw):
    print("\nF3 — drawing and navigation")
    browser = pw.chromium.launch(headless=not args.headed, args=LAUNCH)
    errors = []
    ctx, page = new_page(browser, errors)
    page.goto(URL)
    page.wait_for_function("() => S.def !== null", timeout=15000)
    load_job(page, "Test")
    open_3d(page)
    wait_scene(page)
    scene = page.request.post(URL.rstrip("/") + "/api/scene",
                              data=json.dumps({"job": page.evaluate("() => S.job")}),
                              headers={"Content-Type": "application/json"}).json()
    items = {it["number"]: it for it in scene["items"]}

    # 2. every placed cabinet and panel, in the right place, at the right height
    placed = sorted(n for n, it in items.items() if it["placed"])
    got = page.evaluate("() => [...Array(40).keys()].filter((n) => V3D.bounds(n) !== null)")
    check("every placed item has a group in the scene", got, placed)
    bad = []
    for n in placed:
        b = page.evaluate(f"() => V3D.bounds({n})")
        parts = items[n]["parts"]
        want_min = [min(x for q in parts for x, _ in q["outline"]), min(y for q in parts for _, y in q["outline"]),
                    min(q["z0"] for q in parts)]
        want_max = [max(x for q in parts for x, _ in q["outline"]), max(y for q in parts for _, y in q["outline"]),
                    max(q["z1"] for q in parts)]
        if any(abs(a - c) > 0.6 for a, c in zip(b["min"] + b["max"], want_min + want_max)):
            bad.append((n, b, want_min, want_max))
    check("and its bounds are the server's outlines and heights", bad, [])
    b2 = page.evaluate("() => V3D.bounds(2)")
    check("cabinet 2 stands on its legs: bottom at 100", b2["min"][2], 100)
    b5 = page.evaluate("() => V3D.bounds(5)")
    check("wall unit 5 hangs at its own z", b5["min"][2], items[5]["parts"][0]["z0"])
    b8 = page.evaluate("() => V3D.bounds(8)")
    check("panel 8 stands at its typed z", b8["min"][2], 100)

    # colours and pictures off the boards
    looks = scene["looks"]
    door = next(q for q in items[2]["parts"] if q["role"] == "door")
    info = page.evaluate(f"() => V3D.partInfo({json.dumps(door['id'])})")
    check("a door is drawn in its board's colour", info["colour"], looks[door["board"]]["colour"])
    check("a grained board with a picture is textured", info["map"], bool(looks[door["board"]]["picture"]))
    side = next(q for q in items[2]["parts"] if q["role"] == "side")
    info_s = page.evaluate(f"() => V3D.partInfo({json.dumps(side['id'])})")
    check("a plain board keeps its colour, no texture", (info_s["colour"], info_s["map"]),
          (looks[side["board"]]["colour"], False))
    mitre_door = next(q for q in items[13]["parts"] if q["role"] == "door")
    info_m = page.evaluate(f"() => V3D.partInfo({json.dumps(mitre_door['id'])})")
    check("the mitre door reads in BROOKHILL, as the Finish elevation has it",
          (mitre_door["board"], info_m["colour"]), ("BROOKHILL", looks["BROOKHILL"]["colour"]))
    p12 = items[12]["parts"][0]
    info_12 = page.evaluate(f"() => V3D.partInfo({json.dumps(p12['id'])})")
    check("panel 12 reads in its own board", info_12["colour"], looks[p12["board"]]["colour"])
    legend = page.locator("#v3dview .v3dlegend .rows").inner_text()
    check_true("the legend names the boards in view", all(b in legend for b in ("BROOKHILL", "WHITEMEL", "BACK")))
    check_true("and says what is not drawn", "Not drawn" in page.locator("#v3dview .v3dlegend .nd").inner_text())

    # 3. zoom to cursor: a cabinet corner stays under the cursor over ten wheel steps
    settle(page)
    corner = [door["outline"][1][0], door["outline"][1][1], door["z1"]]   # door 2's top right front corner
    left, top, w, hgt = viewport_origin(page)
    p = project(page, *corner)
    check_true("the corner is on screen", 0 < p["x"] < w and 0 < p["y"] < hgt, f"{p}")
    # the point the wheel is over is whatever the pick finds there: hold THAT
    # still, which is what "zoom towards the point under the cursor" means
    under = page.evaluate(f"() => V3D.unproject({left + p['x']}, {top + p['y']})")
    check_true("something is under the cursor there", under is not None, f"{under}")
    corner = under or corner
    p = project(page, *corner)
    page.mouse.move(left + p["x"], top + p["y"])
    for _ in range(10):
        page.mouse.wheel(0, -120)
        time.sleep(0.05)
    settle(page)
    q = project(page, *corner)
    drift = math.hypot(q["x"] - p["x"], q["y"] - p["y"])
    check_true("zoom to cursor: the corner stayed under the cursor over ten wheel steps",
               drift < 6, f"drift {drift:.1f} px")
    cam_d = page.evaluate("() => { const c = V3D.camera(); return Math.hypot(c.position[0]-c.target[0], c.position[1]-c.target[1], c.position[2]-c.target[2]); }")
    check_true("and it zoomed in", cam_d < 6000, f"distance {cam_d:.0f}")
    # pinch is a wheel with ctrl held: same path
    page.keyboard.down("Control")
    for _ in range(4):
        page.mouse.wheel(0, 120)
        time.sleep(0.05)
    page.keyboard.up("Control")
    settle(page)
    q2 = project(page, *corner)
    drift2 = math.hypot(q2["x"] - p["x"], q2["y"] - p["y"])
    check_true("pinch (Ctrl+wheel) zooms about the cursor too", drift2 < 6, f"drift {drift2:.1f} px")

    # 4. orbit about the pressed point: press on a door and orbit; it stays put
    page.keyboard.press("h")
    settle(page)
    az0 = page.evaluate("() => { const c = V3D.camera(); return Math.atan2(c.position[1]-c.target[1], c.position[0]-c.target[0]); }")
    face = [(door["outline"][0][0] + door["outline"][1][0]) / 2,
            door["outline"][1][1], (door["z0"] + door["z1"]) / 2]     # the middle of door 2's front
    p = project(page, *face)
    # what is really under the cursor there is the pressed point (a panel may
    # stand in front of the door from this angle): that is what must stay put
    face = page.evaluate(f"() => V3D.unproject({left + p['x']}, {top + p['y']})") or face
    p = project(page, *face)
    page.mouse.move(left + p["x"], top + p["y"])
    page.mouse.down()
    for i in range(1, 13):
        page.mouse.move(left + p["x"] + i * 12, top + p["y"] + i * 4)
        time.sleep(0.02)
    page.mouse.up()
    settle(page)
    q = project(page, *face)
    drift = math.hypot(q["x"] - p["x"], q["y"] - p["y"])
    check_true("orbit about the pressed point: the door stayed put while the room turned",
               drift < 6, f"drift {drift:.1f} px")
    az = page.evaluate("() => { const c = V3D.camera(); return Math.atan2(c.position[1]-c.target[1], c.position[0]-c.target[0]); }")
    check_true("and the camera did orbit", abs(az - az0) > 0.05, f"azimuth {az:.2f} from {az0:.2f}")

    # 5. pan: right-drag; the grabbed point stays under the cursor
    page.keyboard.press("h")
    settle(page)
    p = project(page, *face)
    face = page.evaluate(f"() => V3D.unproject({left + p['x']}, {top + p['y']})") or face
    p = project(page, *face)
    page.mouse.move(left + p["x"], top + p["y"])
    page.mouse.down(button="right")
    for i in range(1, 11):
        page.mouse.move(left + p["x"] + i * 10, top + p["y"] + i * 6)
        time.sleep(0.02)
    page.mouse.up(button="right")
    settle(page)
    q = project(page, *face)
    check_true("pan: the grabbed point moved with the cursor",
               abs((q["x"] - p["x"]) - 100) < 6 and abs((q["y"] - p["y"]) - 60) < 6,
               f"moved ({q['x'] - p['x']:.1f}, {q['y'] - p['y']:.1f}) for (100, 60)")

    # 6. views: H, T, 1-9, P, Fit, the cube
    def cam():
        return page.evaluate("() => V3D.camera()")

    def direction():
        c = cam()
        d = [c["position"][i] - c["target"][i] for i in range(3)]
        n = math.sqrt(sum(x * x for x in d)) or 1
        return [x / n for x in d]
    page.keyboard.press("t")
    settle(page)
    d = direction()
    check_true("T: looking straight down", d[2] > 0.98, f"{[round(x, 2) for x in d]}")
    page.keyboard.press("h")
    settle(page)
    d = direction()
    check_true("H: home looks at the runs from the side they face, from above",
               d[0] < -0.2 and d[1] > 0.2 and d[2] > 0.3, f"{[round(x, 2) for x in d]}")
    page.keyboard.press("1")
    settle(page)
    d = direction()
    check_true("1: face on to wall A, from the room", abs(d[1] - 1) < 0.05 and abs(d[2]) < 0.05, f"{[round(x, 2) for x in d]}")
    check("in orthographic", cam()["ortho"], True)
    page.keyboard.press("2")
    settle(page)
    d = direction()
    check_true("2: face on to wall B", abs(d[0] + 1) < 0.05, f"{[round(x, 2) for x in d]}")
    page.keyboard.press("p")
    settle(page)
    check("P: back to perspective", cam()["ortho"], False)
    page.keyboard.press("h")
    settle(page)
    c0 = cam()
    page.mouse.move(left + w * 0.5, top + hgt * 0.5)
    for _ in range(6):
        page.mouse.wheel(0, -120)
        time.sleep(0.04)
    settle(page)
    page.keyboard.press("f")
    settle(page)
    c1 = cam()
    d0 = math.dist(c0["position"], c0["target"])
    d1 = math.dist(c1["position"], c1["target"])
    check_true("F with nothing selected fits everything again (back out to the Home distance)",
               abs(d1 - d0) < d0 * 0.02, f"{d1:.0f} vs {d0:.0f}")
    # the cube: at Home its centre is the near corner; click it and the camera
    # goes to a corner view, animated
    cube = page.locator("#v3dview .v3dcube").bounding_box()
    page.mouse.click(cube["x"] + cube["width"] / 2, cube["y"] + cube["height"] * 0.22)
    moving = not page.evaluate("() => V3D.idle()")
    settle(page)
    d = direction()
    check_true("cube: clicking its top face looks down, animated",
               d[2] > 0.9 and moving, f"{[round(x, 2) for x in d]}, animating {moving}")
    page.keyboard.press("h")
    settle(page)
    page.mouse.click(cube["x"] + cube["width"] * 0.3, cube["y"] + cube["height"] * 0.66)   # a side face, seen from Home
    settle(page)
    d = direction()
    check_true("cube: a side face turns the view to that side", abs(d[2]) < 0.3, f"{[round(x, 2) for x in d]}")
    check_true("cube faces carry the wall letters",
               page.evaluate("() => V3D.state() !== null"))
    page.keyboard.press("h")
    settle(page)
    check("labels are on by default", page.evaluate("() => V3D.state().labels"), True)
    n_labels = page.evaluate("() => [...document.querySelectorAll('#v3dview .v3dlabel')].filter((e) => !e.hidden).length")
    check_true("item numbers are drawn as DOM labels, decluttered", 4 <= n_labels <= 13, f"{n_labels} of 13")
    page.keyboard.press("l")
    check("L hides them", page.evaluate("() => [...document.querySelectorAll('#v3dview .v3dlabel')].filter((e) => !e.hidden).length"), 0)
    page.keyboard.press("l")
    page.keyboard.press("x")
    info = page.evaluate(f"() => V3D.partInfo({json.dumps(door['id'])})")
    check("X: x-ray makes the parts translucent", info["opacity"] < 1, True)
    page.keyboard.press("x")
    check("no console errors", errors, [])

    # 15 (part): 30 edits in a row; memory counts steady, no console errors
    page.click('nav [data-tab="view3d"]')
    m0 = page.evaluate("() => V3D.memory()")
    cam0 = cam()
    for i in range(30):
        w = 450 + (i % 2)
        edit_and_wait(page, f"() => {{ S.job.cabinets[1].width = {w}; schedule(); }}")
    settle(page)
    m1 = page.evaluate("() => V3D.memory()")
    print(f"      renderer.info.memory before {m0} after {m1}")
    check("30 edits: geometry count returns to where it was", m1["geometries"], m0["geometries"])
    check("30 edits: texture count returns to where it was", m1["textures"], m0["textures"])
    check("30 edits: the camera did not move", cam(), cam0)
    check("30 edits: no console errors", errors, [])
    b2b = page.evaluate("() => V3D.bounds(2)")
    check("the edited cabinet is rebuilt at its new width", round(b2b["max"][0] - b2b["min"][0]), 451 + 0)

    # the October fixture: no room, ~360 parts, first draw
    seq = page.evaluate("() => sceneSeq")
    page.click("#fixture")
    page.wait_for_function(f"() => S.job && S.job.name !== 'Test' && S.res && sceneSeq > {seq} && !S.sceneStale", timeout=30000)
    settle(page)
    ms = page.evaluate("() => S.sceneMs")
    m2 = page.evaluate("() => V3D.memory()")
    print(f"      October: {m2['pickables']} parts, scene fetched and built in {ms} ms")
    check_true("October fixture draws with no room, in about a second or less", ms < 2500, f"{ms} ms")
    check_true("the banner says there is no room", "no room" in page.locator("#v3dview .v3dnote").text_content())
    check("no console errors on the October job", errors, [])
    ctx.close()
    browser.close()



# ---------------------------------------------------------------------------

def stage_f4(pw):
    print("\nF4 — selection, the part card, one editor across views")
    browser = pw.chromium.launch(headless=not args.headed, args=LAUNCH)
    errors = []
    ctx, page = new_page(browser, errors)
    page.goto(URL)
    page.wait_for_function("() => S.def !== null", timeout=15000)
    page.evaluate("() => { try { localStorage.clear(); } catch (e) {} }")
    load_job(page, "Test")
    open_3d(page)
    wait_scene(page)
    scene = page.request.post(URL.rstrip("/") + "/api/scene",
                              data=json.dumps({"job": page.evaluate("() => S.job")}),
                              headers={"Content-Type": "application/json"}).json()
    items = {it["number"]: it for it in scene["items"]}
    left, top, w, hgt = viewport_origin(page)

    def click_part(number, role="door"):
        # find a screen point where THAT cabinet's part is really under the cursor
        parts = items[number]["parts"]
        part = next((q for r in (role, "drawer", "door", "side") for q in parts if q["role"] == r), parts[0])
        x = sum(px for px, _ in part["outline"]) / len(part["outline"])
        y = sum(py for _, py in part["outline"]) / len(part["outline"])
        z = (part["z0"] + part["z1"]) / 2
        pr = project(page, x, y, z)
        hit = page.evaluate(f"() => V3D.unproject({left + pr['x']}, {top + pr['y']})")
        if hit is None:
            raise AssertionError(f"cabinet {number} not under the cursor")
        page.mouse.click(left + pr["x"], top + pr["y"])
        return part

    # 7. click cabinet 7 in 3D
    page.keyboard.press("h")
    settle(page)
    part = click_part(7)
    time.sleep(0.3)
    check("cabinet 7 is the selection", page.evaluate("() => S.job.cabinets[S.sel].number"), 7)
    check("and nothing is isolated by a click", page.evaluate("() => S.isolate"), None)
    check("the dock shows cabinet 7", page.locator("#v3ddock #editor h2").first.text_content().strip(), "Cabinet 7")
    check("the part card names the part's cut-list line",
          page.locator("#v3dview .v3dcard").inner_text().find(part["line"]) >= 0, True)
    check("the 3D list marks it", page.locator("#v3dlist .row.sel").get_attribute("data-n"), "7")
    page.click("#v3dview .v3dcard button.go")
    page.wait_for_function("() => S.tab === 'cutlist'")
    flash = page.locator("#cutlist tr.flash")
    check("Show in cut list lands on that row", flash.get_attribute("data-label"), part["line"])
    check_true("and the row is in view", page.evaluate("() => { const r = document.querySelector('#cutlist tr.flash').getBoundingClientRect(); return r.top >= 0 && r.bottom <= window.innerHeight; }"))
    page.click('nav [data-tab="room"]')
    page.wait_for_function("() => document.querySelector('#plan .cab.sel') !== null", timeout=10000)
    check("the plan shows it selected", page.locator("#plan .cab.sel").first.get_attribute("data-cab"), "7")
    page.click('nav [data-tab="cabinets"]')
    page.wait_for_function("() => document.querySelector('#elevation .ecabg.sel') !== null", timeout=10000)
    check("and the elevation", page.locator("#elevation .ecabg.sel").first.get_attribute("data-cab"), "7")
    check("the cabinet table too", page.locator("#cabtable tr.sel").first.get_attribute("data-i"),
          str(page.evaluate("() => S.sel")))

    # 10. the dock: one element, on three tabs, collapses, remembers
    page.evaluate("() => { document.getElementById('editor').dataset.mark = 'one'; }")
    check("Cabinets: the editor sits in its dock", page.evaluate("() => document.getElementById('editor').parentElement.id"), "cabdock")
    page.click('nav [data-tab="room"]')
    check("Room: the same element moved into the plan's dock",
          page.evaluate("() => [document.getElementById('editor').parentElement.id, document.getElementById('editor').dataset.mark]"), ["roomdock", "one"])
    page.click('nav [data-tab="view3d"]')
    check("3D: the same element again", page.evaluate("() => [document.getElementById('editor').parentElement.id, document.getElementById('editor').dataset.mark]"), ["v3ddock", "one"])
    check("it still shows cabinet 7", page.locator("#v3ddock #editor h2").first.text_content().strip(), "Cabinet 7")
    check("one editor: one h2", page.locator("#editor h2").count(), 1)
    page.click("#v3ddock .docktog")
    check("the dock collapses to a strip", page.evaluate("() => document.getElementById('v3ddock').classList.contains('closed')"), True)
    page.reload()
    page.wait_for_function("() => S.def !== null", timeout=15000)
    check("and remembers it across a reload", page.evaluate("() => document.getElementById('cabdock').classList.contains('closed')"), True)
    page.click("#cabdock .docktog")
    check("and opens again", page.evaluate("() => document.getElementById('cabdock').classList.contains('closed')"), False)
    load_job(page, "Test")
    check("with nothing selected the dock says what to do",
          "Select a cabinet" in page.locator("#editor").inner_text(), True)

    # 8. change cabinet 7's width in the dock -> 3D rebuilds 7 only, camera still
    open_3d(page)
    wait_scene(page)
    page.evaluate("() => selectCabinet(S.job.cabinets.findIndex((c) => c.number === 7))")
    page.evaluate("() => renderList()")
    page.wait_for_function("() => document.querySelector('#v3ddock #editor input[data-k=\"width\"]') !== null")
    ids0 = page.evaluate("() => V3D.groupIds()")
    cam0 = page.evaluate("() => V3D.camera()")
    seq = page.evaluate("() => sceneSeq")
    t0 = time.time()
    page.fill('#v3ddock #editor input[data-k="width"]', "380")
    page.dispatch_event('#v3ddock #editor input[data-k="width"]', "input")
    page.wait_for_function(f"() => sceneSeq > {seq} && !S.sceneStale && sceneTimer === null", timeout=15000)
    dt = (time.time() - t0) * 1000
    ids1 = page.evaluate("() => V3D.groupIds()")
    changed = sorted(n for n in ids0 if ids0[n] != ids1.get(n))
    check("only cabinet 7 was rebuilt", changed, ["7"])
    check("the camera did not move", page.evaluate("() => V3D.camera()"), cam0)
    b7 = page.evaluate("() => V3D.bounds(7)")
    check("3D shows the new width", round(b7["max"][0] - b7["min"][0]), 380)
    check("the engine agrees", page.evaluate("() => S.res.geometry['7'].width"), 380)
    print(f"      the edit reached 3D in {dt:.0f} ms (compute debounce included)")
    check_true("within a second of the keystroke", dt < 1500, f"{dt:.0f} ms")

    # 9. click in the plan selects without isolating; the list still isolates
    page.click('nav [data-tab="room"]')
    page.wait_for_function("() => document.querySelector('#plan .cab[data-cab=\"3\"]') !== null", timeout=10000)
    if page.locator("#unisolate").count():
        page.click("#unisolate")               # the plan's own way out of isolate
        page.wait_for_function("() => S.isolate === null && document.querySelector('#plan .cab[data-cab=\"3\"]').getAttribute('pointer-events') !== 'none'", timeout=10000)
    page.locator('#plan .cab[data-cab="3"]').first.click()
    page.wait_for_function("() => S.job.cabinets[S.sel] && S.job.cabinets[S.sel].number === 3", timeout=5000)
    check("plan click: cabinet 3 selected", page.evaluate("() => S.job.cabinets[S.sel].number"), 3)
    check("without isolating", page.evaluate("() => S.isolate"), None)
    page.locator('#plan .cab[data-cab="4"]').first.click()
    page.wait_for_function("() => S.job.cabinets[S.sel] && S.job.cabinets[S.sel].number === 4", timeout=5000)
    check("click another: that one", page.evaluate("() => S.job.cabinets[S.sel].number"), 4)
    check("still not isolating", page.evaluate("() => S.isolate"), None)
    page.click('nav [data-tab="cabinets"]')
    page.locator('#cabtable tr[data-i]').nth(1).click()
    check("the cabinet table still isolates", page.evaluate("() => [S.job.cabinets[S.sel].number, S.isolate]"),
          [2, 2])
    page.click('nav [data-tab="view3d"]')
    time.sleep(0.3)
    check("3D mirrors the isolate", page.evaluate("() => V3D.state().isolate"), 2)
    door3 = next(q for q in items[3]["parts"] if q["role"] == "door")["id"]
    info = page.evaluate("() => V3D.partInfo(%s)" % json.dumps(door3))
    check("everything else is ghosted in 3D", info["ghost"], True)
    page.click("#v3dbar button:has-text('Isolate')")
    check("the 3D Isolate toggle clears the plan's isolate too", page.evaluate("() => S.isolate"), None)

    # the item list and the context menu
    check("the item list has a row per item", page.locator("#v3dlist .row").count(), 13)
    page.locator('#v3dlist .row[data-n="13"]').click()
    settle(page)
    check("a list click selects and isolates", page.evaluate("() => [S.job.cabinets[S.sel].number, S.isolate]"), [13, 13])
    page.click("#v3dbar button:has-text('Isolate')")
    page.locator('#v3dlist .row[data-n="5"] .eye').click()
    info5 = page.evaluate("() => V3D.partInfo(%s)" % json.dumps(items[5]["parts"][0]["id"]))
    check("the eye hides an item in 3D", info5["visible"], False)
    page.locator('#v3dlist .row[data-n="5"] .eye').click()
    page.mouse.move(left + w / 2, top + hgt / 2)     # keys act with the pointer over the view
    page.keyboard.press("h")
    settle(page)
    part2 = next(q for q in items[2]["parts"] if q["role"] == "door")
    pr = project(page, (part2["outline"][0][0] + part2["outline"][1][0]) / 2, part2["outline"][1][1], (part2["z0"] + part2["z1"]) / 2)
    page.mouse.click(left + pr["x"], top + pr["y"], button="right")
    time.sleep(0.2)
    menu = page.locator("#v3dview .v3dctx")
    check("a right-click without a drag opens the context menu", menu.is_visible(), True)
    labels = menu.locator("button").all_inner_texts()
    check_true("with Fit, Isolate, fronts, Hide and Select in cut list",
               any("Fit" in l for l in labels) and any("Isolate" in l for l in labels)
               and any("fronts" in l for l in labels) and any("Hide" in l for l in labels)
               and any("cut list" in l for l in labels), f"{labels}")
    hit_line = [l for l in labels if "cut list" in l][0].split()[1]
    menu.locator("button:has-text('cut list')").click()
    page.wait_for_function("() => S.tab === 'cutlist'")
    check("Select in cut list lands on the row", page.locator("#cutlist tr.flash").get_attribute("data-label"), hit_line)

    # validation in the dock
    with_issue = page.evaluate("() => { const s = new Set(); (S.res.issues || []).forEach((i) => { if (/^\\d+$/.test(i.where)) s.add(+i.where); }); return [...s]; }")
    if with_issue:
        n = with_issue[0]
        page.click('nav [data-tab="cabinets"]')
        page.evaluate("() => { selectCabinet(S.job.cabinets.findIndex((c) => c.number === %d)); renderList(); }" % n)
        check(f"the dock lists cabinet {n}'s own issues", page.locator("#editor .dockissues div").count() > 0, True)
        page.locator("#editor .dockissues div").first.click()
        check("and a line opens the Validation tab", page.evaluate("() => S.tab"), "validation")
    check("no console errors", errors, [])
    ctx.close()
    browser.close()

STAGES = {"f1": stage_f1, "f3": stage_f3, "f4": stage_f4}

with sync_playwright() as pw:
    for name, fn in STAGES.items():
        if args.stage in ("all", name):
            fn(pw)

print()
if FAILS:
    print(f"{len(FAILS)} FAILED: " + "; ".join(FAILS))
    sys.exit(1)
print("ui_check_3d: all good")
