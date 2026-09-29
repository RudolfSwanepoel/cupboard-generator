"""Walls at any angle and Draw walls (brief of 29 September 2026) in the running
app, with a real mouse (Playwright, optional).

    python run_app.py --no-window --port 8766      # in another window
    python tools/ui_check_walls.py [--port 8766] [--stage draw|ell|corner|input|drag|side|3d|all]

Drives what check_room.py cannot: a 4-wall room drawn by clicks on Room ->
Plan and closed on its first corner; an L drawn with an outside corner; a
corner set to 270 in the Walls card turning the plan; a negative length and an
angle out of range refused at the input; and a cabinet dragged in the plan onto
a wall standing at 45 degrees; an open L drawn
both ways with its cabinets on the room side, and Flip side. Every job is built in the page (`adopt`), never
loaded from jobs/ and never saved. Screenshots go into
output/_checks/ui_check_walls/.

Playwright is the only third-party package anywhere near this app and only the
ui_check scripts need it; without it this says so and exits 0.
"""
import argparse
import json
import math
import os
import sys
import time

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, ROOT)
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

try:
    from playwright.sync_api import sync_playwright
except ImportError:                                            # pragma: no cover
    print("playwright is not installed — skipping the browser check (pip install playwright)")
    sys.exit(0)

from cabinetgen.model import Cabinet, Job, Placement, Room, Wall   # noqa: E402
from cabinetgen.store import job_to_dict                           # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--port", type=int, default=8766)
ap.add_argument("--stage", default="all")
ap.add_argument("--headed", action="store_true")
args = ap.parse_args()
URL = f"http://127.0.0.1:{args.port}/"
SHOTS = os.path.join(ROOT, "output", "_checks", "ui_check_walls")

FAILS = []


def check(label, got, want):
    ok = got == want
    print(f"  {'ok  ' if ok else 'FAIL'}  {label}: {got!r}" + ("" if ok else f"  (wanted {want!r})"))
    if not ok:
        FAILS.append(label)
    return ok


def shot(page, name, selector=None):
    os.makedirs(SHOTS, exist_ok=True)
    path = os.path.join(SHOTS, name + ".png")
    time.sleep(0.25)
    if selector:
        loc = page.locator(selector).first
        loc.scroll_into_view_if_needed()
        loc.screenshot(path=path)
    else:
        page.screenshot(path=path)
    print(f"      screenshot {os.path.relpath(path, ROOT)}")


def computed(page):
    """Run the compute the last edit scheduled now and await it, then redraw
    the plan and await that, so what is read next answers the job as it is."""
    time.sleep(0.05)
    page.evaluate("async () => { clearTimeout(computeTimer); computeTimer = null; await compute(); "
                  "if (S.tab === 'room' && S.roomSub === 'plan') await renderPlan(); }")
    page.wait_for_function("() => S.res && S.res.ok !== undefined", timeout=15000)
    time.sleep(0.1)


def open_page(browser, errors, dialogs):
    ctx = browser.new_context(viewport={"width": 1500, "height": 1000})
    page = ctx.new_page()
    page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
    page.on("pageerror", lambda e: errors.append(str(e)))

    def on_dialog(d):
        dialogs.append(d.message)
        d.accept()
    page.on("dialog", on_dialog)
    page.goto(URL)
    page.wait_for_function("() => S.def !== null && S.res", timeout=15000)
    return ctx, page


def adopt(page, job):
    page.evaluate("(j) => adopt(j)", job_to_dict(job))
    page.wait_for_function("() => S.job && S.job.name === %s" % json.dumps(job.name), timeout=15000)
    computed(page)


def room_plan(page):
    page.click('nav [data-tab="room"]')
    page.wait_for_function("() => S.tab === 'room'", timeout=5000)
    if page.evaluate("() => S.roomSub") != "plan":
        page.click('#roomsubs [data-roomsub="plan"]')
    computed(page)


def empty_job(name):
    return Job(name=name, cabinets=[], placements=[])


def at_mm(page, x, y):
    """Where a point in world plan mm is on screen, through the drawing canvas's
    own transform — the same one a click is read back through."""
    return page.evaluate("""([x, y]) => {
        const svg = document.querySelector('#drawsvg');
        const p = new DOMPoint(x, y).matrixTransform(svg.getScreenCTM());
        return [p.x, p.y]; }""", [x, y])


def click_mm(page, x, y, **kw):
    cx, cy = at_mm(page, x, y)
    page.mouse.move(cx, cy, steps=3)
    page.mouse.click(cx, cy, **kw)
    time.sleep(0.05)


def walls(page):
    return page.evaluate("() => S.job.room.walls.map((w) => [w.id, w.length, "
                         "w.corner_end === undefined ? 90 : w.corner_end, !!w.drawn])")


def issues(page, check_id):
    return page.evaluate("(c) => (S.res.issues || []).filter((i) => i.check === c)"
                         ".map((i) => i.message)", check_id)


# ---------------------------------------------------------------------------

def stage_draw(pw):
    print("\nDraw a 4-wall room by clicks and close it")
    browser = pw.chromium.launch(headless=not args.headed)
    errors, dialogs = [], []
    ctx, page = open_page(browser, errors, dialogs)
    adopt(page, empty_job("draw4"))
    room_plan(page)
    check("with no room, the plan offers Draw walls",
          page.evaluate("() => !document.querySelector('#drawwalls').hidden"), True)
    page.click("#drawwalls")
    page.wait_for_selector("#drawsvg", timeout=5000)
    check("no room to replace, so nothing is asked", dialogs, [])
    check("the hint says how", "Shift" in page.inner_text("#drawhint"), True)
    # A screen pixel is some 9 mm on this canvas, so a click lands within a
    # step of where it was aimed; the direction snap is what keeps each wall
    # square, and the length snap what keeps it in whole 10 mm.
    click_mm(page, 1000, 1000)
    cx, cy = at_mm(page, 5000, 1030)            # 30 mm off square: snapped to 0 degrees
    page.mouse.move(cx, cy, steps=4)
    time.sleep(0.05)
    band = page.evaluate("() => document.querySelector('#drawreadout').textContent")
    check("the rubber band reads the length in whole 10 mm, about 4000",
          band.endswith("0 mm") and abs(int(band.split()[0]) - 4000) <= 10, True)
    check("  on a square direction",
          page.evaluate("() => Math.abs(DRAW.at[1] - DRAW.pts[0][1]) < 1e-6"), True)
    page.mouse.click(cx, cy)
    cx, cy = at_mm(page, 5030, 4000)
    page.mouse.move(cx, cy, steps=4)
    time.sleep(0.05)
    band = page.evaluate("() => document.querySelector('#drawreadout').textContent")
    check("  and the corner it would make", band.split(" · ", 1)[1:], ["corner 90°"])
    page.mouse.click(cx, cy)
    click_mm(page, 1000, 4000)
    click_mm(page, 1000, 1400)
    check("four corners set", page.evaluate("() => DRAW.pts.length"), 5)
    page.keyboard.press("Backspace")
    time.sleep(0.05)
    check("Backspace takes the last corner off", page.evaluate("() => DRAW.pts.length"), 4)
    shot(page, "draw_rubber_band", "#plancard")
    click_mm(page, 1000, 1000)                  # the first corner: closes it
    page.wait_for_function("() => !DRAW && S.job.room && S.job.room.walls.length === 4",
                           timeout=10000)
    computed(page)
    got = walls(page)
    check("four walls A-D, every corner 90, each drawn",
          [(w[0], w[2], w[3]) for w in got],
          [("A", 90, True), ("B", 90, True), ("C", 90, True), ("D", 90, True)])
    check("  about 4000 x 3000, in whole 10 mm, opposite walls equal",
          [all(abs(w[1] - want) <= 10 and w[1] % 10 == 0 for w, want in zip(got, (4000, 3000) * 2)),
           got[0][1] == got[2][1], got[1][1] == got[3][1]], [True, True, True])
    check("closed", page.evaluate("() => S.job.room.closed"), True)
    check("the room closes", page.evaluate("() => S.res.room.closure_error"), 0)
    check("every drawn wall is a critical", len(issues(page, "wall-drawn")), 4)
    check("the Walls card marks them drawn",
          page.evaluate("() => document.querySelectorAll('#room [data-wmeasured]').length"), 4)
    shot(page, "draw_closed")
    # measured: typed on A, ticked on B
    page.fill('#room input[data-w="0"][data-wk="length"]', "4010")
    page.click('#room [data-wmeasured="1"]')
    computed(page)
    check("typing a length or ticking measured clears it",
          [w[3] for w in walls(page)], [False, False, True, True])
    check("  and the critical with it", sorted(issues(page, "wall-drawn")),
          ["wall C: drawn, not measured — type its length, or tick it as measured",
           "wall D: drawn, not measured — type its length, or tick it as measured"])

    print("\nDrawing again over a room asks first, and Esc cancels")
    page.evaluate("() => { S.job.placements.push({cabinet: 1, wall: 'A', x: 0, z: 0, y: 0, "
                  "flip: false, layer: null}); }")
    dialogs.clear()
    page.click("#drawwalls")
    time.sleep(0.2)
    check("it asks 'Replace walls A–D?'", dialogs[:1] and dialogs[0].startswith("Replace walls A–D?"),
          True)
    check("  saying placements keep their wall letter",
          "keep their wall letter" in (dialogs[0] if dialogs else ""), True)
    page.wait_for_selector("#drawsvg", timeout=5000)
    click_mm(page, 0, 0)
    page.keyboard.press("Escape")
    time.sleep(0.2)
    check("Esc cancels the whole drawing and keeps the room",
          [page.evaluate("() => !!DRAW"), len(walls(page))], [False, 4])
    check("no console errors", errors, [])
    ctx.close()
    browser.close()


def stage_ell(pw):
    print("\nDraw an L with an outside corner, anticlockwise, as an open run and closed")
    browser = pw.chromium.launch(headless=not args.headed)
    errors, dialogs = [], []
    ctx, page = open_page(browser, errors, dialogs)
    adopt(page, empty_job("drawL"))
    room_plan(page)
    page.click("#drawwalls")
    page.wait_for_selector("#drawsvg", timeout=5000)
    # anticlockwise on screen: down first, then round
    for x, y in ((0, 0), (0, 3000), (4000, 3000), (4000, 1000), (3000, 1000), (3000, 0)):
        click_mm(page, x, y)
    click_mm(page, 0, 0)
    page.wait_for_function("() => !DRAW && S.job.room && S.job.room.walls.length === 6",
                           timeout=10000)
    computed(page)
    got = walls(page)
    check("six walls, the first drawn still A", [w[1] for w in got][:1], [3000])
    check("one outside corner, 270; the rest 90",
          sorted(w[2] for w in got), [90, 90, 90, 90, 90, 270])
    check("it closes", page.evaluate("() => S.res.room.closure_error"), 0)
    check("no wall crosses another", issues(page, "room-self-intersect"), [])
    shot(page, "ell_plan", "#plancard")
    shot(page, "ell_walls_card", "#room")

    print("\nan open run: double-click finishes it")
    page.click("#drawwalls")
    page.wait_for_selector("#drawsvg", timeout=5000)
    click_mm(page, 0, 0)
    click_mm(page, 3000, 0)
    cx, cy = at_mm(page, 3000, 2000)
    page.mouse.move(cx, cy, steps=3)
    page.mouse.dblclick(cx, cy)
    page.wait_for_function("() => !DRAW && S.job.room.walls.length === 2", timeout=10000)
    computed(page)
    check("two walls, an open run", [walls(page), page.evaluate("() => S.job.room.closed")],
          [[["A", 3000, 90, True], ["B", 2000, 90, True]], False])
    check("the open run's last wall has no corner",
          page.evaluate("() => document.querySelectorAll('#room select[data-wk=\"corner_pick\"]').length"), 1)
    check("no console errors", errors, [])
    ctx.close()
    browser.close()


def stage_corner(pw):
    print("\nSet a corner to 270 in the Walls card: the plan turns")
    browser = pw.chromium.launch(headless=not args.headed)
    errors, dialogs = [], []
    ctx, page = open_page(browser, errors, dialogs)
    job = empty_job("corner")
    job.room = Room(name="corner", ceiling=2600, closed=False,
                    walls=[Wall("A", 3000), Wall("B", 2000)])
    adopt(page, job)
    room_plan(page)
    before = page.evaluate("() => S.res.room.corners")
    check("A then B at 90: B runs into the room", before, [[0, 0], [3000, 0], [3000, 2000]])
    label = page.evaluate("() => document.querySelector('#room select[data-wk=\"corner_pick\"]')"
                          ".closest('td').textContent.trim().slice(0, 3)")
    check("the corner is labelled A→B", label, "A→B")
    shot(page, "corner_90", "#plancard")
    svg0 = page.evaluate("() => document.querySelector('#plan svg').outerHTML")
    page.select_option('#room select[data-w="0"][data-wk="corner_pick"]', "270")
    computed(page)
    check("270 stored on the wall before the corner",
          page.evaluate("() => S.job.room.walls[0].corner_end"), 270)
    check("B now turns back out", page.evaluate("() => S.res.room.corners"),
          [[0, 0], [3000, 0], [3000, -2000]])
    check("and the plan was redrawn",
          page.evaluate("() => document.querySelector('#plan svg').outerHTML") != svg0, True)
    shot(page, "corner_270", "#plancard")
    page.select_option('#room select[data-w="0"][data-wk="corner_pick"]', "custom")
    page.fill('#room input[data-w="0"][data-wk="corner_end"]', "112.5")
    computed(page)
    check("a custom angle, decimals allowed",
          page.evaluate("() => S.job.room.walls[0].corner_end"), 112.5)
    page.select_option('#room select[data-w="0"][data-wk="corner_pick"]', "90")
    computed(page)
    check("back to 90: nothing stored, as in a room nobody turned",
          page.evaluate("() => 'corner_end' in S.job.room.walls[0]"), False)
    check("no console errors", errors, [])
    ctx.close()
    browser.close()


def stage_input(pw):
    print("\nRefused at the input: a negative length, an angle out of range")
    browser = pw.chromium.launch(headless=not args.headed)
    errors, dialogs = [], []
    ctx, page = open_page(browser, errors, dialogs)
    job = empty_job("input")
    job.room = Room(name="input", ceiling=2600, walls=[Wall("A", 4000), Wall("B", 3000),
                                                       Wall("C", 4000), Wall("D", 3000)])
    adopt(page, job)
    room_plan(page)
    page.fill('#room input[data-w="2"][data-wk="length"]', "-4000")
    time.sleep(0.2)
    check("a negative length is not stored", page.evaluate("() => S.job.room.walls[2].length"),
          4000)
    check("  and the note says how to turn instead", page.inner_text("#wallnote"),
          "Wall C: a length cannot be negative. To turn the other way, set the corner angle to 270.")
    page.fill('#room input[data-w="2"][data-wk="length"]', "4000")
    time.sleep(0.2)
    check("a good entry clears the note", page.evaluate("() => $('wallnote').style.display"), "none")
    page.select_option('#room select[data-w="1"][data-wk="corner_pick"]', "custom")
    page.fill('#room input[data-w="1"][data-wk="corner_end"]', "400")
    time.sleep(0.2)
    check("an angle of 400 is not stored",
          page.evaluate("() => 'corner_end' in S.job.room.walls[1]"), False)
    check("  and is said", "between 0 and 360" in page.inner_text("#wallnote"), True)
    shot(page, "input_refused", "#room")
    check("no console errors", errors, [])
    ctx.close()
    browser.close()


def stage_drag(pw):
    print("\nDrag a cabinet onto an angled wall")
    browser = pw.chromium.launch(headless=not args.headed)
    errors, dialogs = [], []
    ctx, page = open_page(browser, errors, dialogs)
    # a 4 x 3 room with its C-D corner splayed: E runs at 45 degrees
    job = Job(name="splay", cabinets=[Cabinet(number=1, width=600, height=720, depth=560,
                                              kind="base")],
              placements=[Placement(1, "A", 1000)])
    job.room = Room(name="splay", ceiling=2600, walls=[
        Wall("A", 4000), Wall("B", 3000), Wall("C", 2000, corner_end=135),
        Wall("E", 2828, corner_end=135), Wall("D", 1000)])
    adopt(page, job)
    room_plan(page)
    check("the splayed room closes", page.evaluate("() => S.res.room.closure_error"), 0)
    # the middle of wall E and a point 300 mm into the room from it, on screen
    tr = page.evaluate("""() => { const t = [...document.querySelectorAll('#plan .track')]
        .find((k) => k.dataset.wall === 'E');
        const r = t.ownerSVGElement.getBoundingClientRect(), vb = t.ownerSVGElement.viewBox.baseVal;
        const k = r.width / vb.width;
        return {x1: r.left + (+t.getAttribute('x1') - vb.x) * k, y1: r.top + (+t.getAttribute('y1') - vb.y) * k,
                x2: r.left + (+t.getAttribute('x2') - vb.x) * k, y2: r.top + (+t.getAttribute('y2') - vb.y) * k,
                nx: +t.dataset.nx, ny: +t.dataset.ny}; }""")
    mx, my = (tr["x1"] + tr["x2"]) / 2, (tr["y1"] + tr["y2"]) / 2
    grab = page.evaluate("""() => { const el = document.querySelector('#plan .cab[data-cab="1"]');
        const b = el.getBoundingClientRect(); return [b.left + b.width / 2, b.top + b.height / 2]; }""")
    page.mouse.move(*grab)
    page.mouse.down()
    for k in range(1, 13):
        f = k / 12
        page.mouse.move(grab[0] + (mx + tr["nx"] * 20 - grab[0]) * f,
                        grab[1] + (my + tr["ny"] * 20 - grab[1]) * f)
        time.sleep(0.03)
    readout = page.evaluate("() => document.querySelector('#dragreadout').textContent")
    check("the readout names wall E while over it", readout.startswith("wall E"), True)
    page.mouse.up()
    computed(page)
    p = page.evaluate("() => S.job.placements.find((q) => q.cabinet === 1)")
    check("dropped on wall E", p["wall"], "E")
    check("  near its middle (1414 less half the cabinet, within a snap)",
          abs(p["x"] - (1414 - 300)) <= 60, True)
    fp = page.evaluate("() => S.res.room.placements['1']")
    check("the engine has it on E", fp["wall"], "E")
    check("no overlap raised", page.evaluate("() => S.res.room.overlaps"), [])
    shot(page, "drag_angled_wall", "#plancard")
    check("no console errors", errors, [])
    ctx.close()
    browser.close()


def stage_side(pw):
    print("\nAn OPEN run drawn with the mouse: which side is the room")
    browser = pw.chromium.launch(headless=not args.headed)
    errors, dialogs = [], []
    ctx, page = open_page(browser, errors, dialogs)

    def draw_open(points):
        page.click("#drawwalls")
        page.wait_for_selector("#drawsvg", timeout=5000)
        for x, y in points[:-1]:
            click_mm(page, x, y)
        cx, cy = at_mm(page, *points[-1])
        page.mouse.move(cx, cy, steps=3)
        page.mouse.dblclick(cx, cy)
        page.wait_for_function("() => !DRAW", timeout=10000)
        computed(page)

    def room_side(own_only=False):
        """Every placed cabinet's drawn footprint (the 3D scene's parts, world
        mm) against the room side of every wall line — or only its own wall's
        — off the engine's corners: the half-plane test check_room.py makes.
        Inside an L the room is on the room side of both walls; round the
        outside of one it is on the room side of each cabinet's own."""
        sc = page.evaluate("async () => await post('/api/scene', {job: S.job})")
        corners = page.evaluate("() => S.res.room.corners")
        ids = page.evaluate("() => S.res.room.walls.map((w) => w.id)")
        out = []
        for item in sc["items"]:
            if not item["parts"]:
                continue
            ok = True
            for k in range(len(corners) - 1):
                if own_only and ids[k] != item["wall"]:
                    continue
                (ax, ay), (bx, by) = corners[k], corners[k + 1]
                ln = math.hypot(bx - ax, by - ay)
                nx, ny = -(by - ay) / ln, (bx - ax) / ln
                for part in item["parts"]:
                    for x, y in part["outline"]:
                        if (x - ax) * nx + (y - ay) * ny < -0.5:
                            ok = False
            out.append((item["number"], ok))
        return sorted(out)

    def place_two():
        page.evaluate("() => { S.job.placements = [{cabinet: 1, wall: 'A', x: 1000, z: 0, y: 0, "
                      "flip: false, layer: null}, {cabinet: 2, wall: 'B', x: 500, z: 0, y: 0, "
                      "flip: false, layer: null}]; placesSig = null; schedule(); }")
        computed(page)

    job = Job(name="side", cabinets=[Cabinet(number=n, width=600, height=720, depth=560,
                                             kind="base") for n in (1, 2)])
    adopt(page, job)
    room_plan(page)
    ltr = [(0, 0), (3000, 0), (3000, 2000)]
    for name, pts in (("left to right", ltr), ("right to left", ltr[::-1])):
        page.evaluate("() => { S.job.room = null; S.job.placements = []; schedule(); }")
        computed(page)
        draw_open(pts)
        check(f"an L drawn {name}: A 3000, B 2000, corner 90", walls(page),
              [["A", 3000, 90, True], ["B", 2000, 90, True]])
        place_two()
        check(f"  both cabinets inside the L, on the room side of both walls", room_side(),
              [(1, True), (2, True)])
        shot(page, "side_" + name.replace(" ", "_"), "#plancard")
    check("Flip side is offered on an open run",
          page.evaluate("() => !!document.querySelector('#roomflip')"), True)
    page.click("#roomflip")
    computed(page)
    check("Flip side: the walls walked the other way, the corner now 270",
          walls(page), [["B", 2000, 270, True], ["A", 3000, 90, True]])
    check("  the cabinets keep their places along the walls, x from the other end",
          page.evaluate("() => S.job.placements.map((p) => [p.cabinet, p.wall, p.x])"),
          [[1, "A", 1400], [2, "B", 900]])
    check("  and stand on the room's side of their own walls — the outside of the L now",
          room_side(own_only=True), [(1, True), (2, True)])
    check("  no longer inside the L", room_side(), [(1, False), (2, False)])
    shot(page, "side_flipped", "#plancard")
    page.click("#roomflip")
    computed(page)
    check("Flip side again: back as it was",
          page.evaluate("() => S.job.placements.map((p) => [p.cabinet, p.wall, p.x])"),
          [[1, "A", 1000], [2, "B", 500]])
    page.select_option('#room select[data-r="closed"]', "yes")
    computed(page)
    page.evaluate("() => renderRoom(true)")
    check("not offered on a closed room",
          page.evaluate("() => !!document.querySelector('#roomflip')"), False)
    check("no console errors", errors, [])
    ctx.close()
    browser.close()


def stage_3d(pw):
    print("\n3D: an L room with an outside corner and a splayed wall")
    browser = pw.chromium.launch(headless=not args.headed, args=[
        "--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist"])
    errors, dialogs = [], []
    ctx, page = open_page(browser, errors, dialogs)
    job = Job(name="ell3d", cabinets=[Cabinet(number=1, width=600, height=720, depth=560,
                                              kind="base"),
                                      Cabinet(number=2, width=600, height=720, depth=560,
                                              kind="base")],
              placements=[Placement(1, "A", 1200), Placement(2, "G", 600)])
    job.room = Room(name="ell3d", ceiling=2600, walls=[
        Wall("A", 3000), Wall("B", 1000, corner_end=270), Wall("C", 1000),
        Wall("D", 2000, corner_end=135), Wall("G", 1414, corner_end=135),
        Wall("E", 3000), Wall("F", 4000)])
    adopt(page, job)
    check("the room closes", page.evaluate("() => S.res.room.closure_error"), 0)
    page.click('nav [data-tab="view3d"]')
    page.wait_for_function("() => typeof V3D === 'object' && V3D !== null", timeout=30000)
    page.wait_for_selector("#v3dview canvas", timeout=15000)
    page.wait_for_function("() => !S.sceneStale && V3D.memory().groups > 0", timeout=30000)
    page.wait_for_function("() => V3D.idle()", timeout=15000)
    shell = page.evaluate("() => V3D.debugShell()")
    check("a wall mesh per wall", sorted(w["wall"] for w in shell),
          ["A", "B", "C", "D", "E", "F", "G"])
    g = [w for w in shell if w["wall"] == "G"][0]
    check("wall G stands on the diagonal: its box spans both x and y",
          (round(g["max"][0] - g["min"][0]), round(g["max"][1] - g["min"][1])), (1000, 1000))
    for mode in ("shaded", "edges", "xray"):
        page.evaluate(f"() => {{ V3D.setDisplay('{mode}'); V3D.viewTop(false); }}")
        page.wait_for_function("() => V3D.idle()", timeout=15000)
        shot(page, f"ell3d_top_{mode}", "#v3dview")
    page.evaluate("() => { V3D.setDisplay('shaded'); V3D.viewHome(false); }")
    page.wait_for_function("() => V3D.idle()", timeout=15000)
    page.click("#v3dbar button:has-text('Grid')")
    check("the Grid toggle works on it", page.evaluate("() => V3D.state().grid"), True)
    page.click("#v3dbar button:has-text('Grid')")
    shot(page, "ell3d_home", "#v3dview")
    check("no console errors", errors, [])
    ctx.close()
    browser.close()


STAGES = {"draw": stage_draw, "ell": stage_ell, "corner": stage_corner,
          "input": stage_input, "drag": stage_drag, "side": stage_side, "3d": stage_3d}


def main() -> int:
    with sync_playwright() as pw:
        for name, fn in STAGES.items():
            if args.stage in ("all", name):
                fn(pw)
    print(f"\n{'ALL OK' if not FAILS else str(len(FAILS)) + ' FAILED: ' + str(FAILS)}")
    return 1 if FAILS else 0


if __name__ == "__main__":
    raise SystemExit(main())
