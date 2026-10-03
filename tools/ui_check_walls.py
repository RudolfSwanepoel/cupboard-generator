"""The Room tab re-laid out, walls as positioned segments (room redo Phase 1,
brief of 2 October 2026) in the running app, with a real mouse (Playwright,
optional).

    python run_app.py --no-window --port 8766      # in another window
    python tools/ui_check_walls.py [--port 8766] [--stage draw|one|flip|renumber|height|input|drag|3d|all]

Drives what check_room.py cannot: the toolbar, the Room card and the Wall card
in the dock; Draw walls ADDING walls to a room and starting on an existing
corner; a one-wall room that draws; Flip face on one wall; Renumber; a wall's
height; a negative length and an angle out of range refused at the input; a
cabinet dragged in the plan onto a wall at 45 degrees; and an L with a splay
in 3D. Every job is built in the page (`adopt`), never loaded from jobs/ and
never saved. Screenshots go into output/_checks/ui_check_walls/.

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
from cabinetgen.room import chain_walls, rectangular               # noqa: E402
from cabinetgen.store import job_to_dict                           # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--port", type=int, default=8766)
ap.add_argument("--stage", default="all")
ap.add_argument("--headed", action="store_true")
args = ap.parse_args()
URL = f"http://127.0.0.1:{args.port}/"
SHOTS = os.path.join(ROOT, "output", "_checks", "ui_check_walls")
LAUNCH = ["--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist"]

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
    """Where a point in world plan mm is on screen, through the plan's own
    mapping (`mmToScreen`) — the same one a click is read back through."""
    return page.evaluate("([x, y]) => mmToScreen(x, y)", [x, y])


def plan_svgs(page):
    """How many plan drawings there are on the Room tab (ruling 10: one, always)."""
    return page.evaluate("() => document.querySelectorAll('#tab-room svg.drw').length")


def click_mm(page, x, y, **kw):
    cx, cy = at_mm(page, x, y)
    page.mouse.move(cx, cy, steps=3)
    page.mouse.click(cx, cy, **kw)
    time.sleep(0.05)


def walls(page):
    """[id, length, corner after, drawn] per wall, in walk order, off the engine."""
    return page.evaluate("() => S.res.room.walls.map((w) => [w.id, w.length, w.after.angle, w.drawn])")


def points(page):
    return page.evaluate("() => S.res.room.walls.map((w) => [w.id, w.x0, w.y0, w.x1, w.y1])")


def issues(page, check_id):
    return page.evaluate("(c) => (S.res.issues || []).filter((i) => i.check === c)"
                         ".map((i) => i.message)", check_id)


def click_wall(page, wid):
    """A real click on a wall's hit line in the plan, at a point clear of the
    cabinets on it (walked from one end until the hit line is on top)."""
    el = page.locator(f'#plan .wallhit[data-wallhit="{wid}"]')
    bb = el.bounding_box()
    for f in (0.05, 0.15, 0.3, 0.5, 0.7, 0.85, 0.95):
        x, y = bb["x"] + bb["width"] * (0.5 if bb["width"] <= 20 else f), \
               bb["y"] + bb["height"] * (0.5 if bb["height"] <= 20 else f)
        top = page.evaluate("([x, y]) => { const e = document.elementFromPoint(x, y); "
                            "return e && e.dataset ? e.dataset.wallhit || null : null; }", [x, y])
        if top == wid:
            page.mouse.click(x, y)
            time.sleep(0.25)
            return True
    return False


def room_side(page, own_only=False):
    """Every placed cabinet's drawn footprint (the 3D scene's parts, world mm)
    against the room side of every wall's line — or only its own wall's — off
    the engine's wall points: the half-plane test check_room.py makes."""
    sc = page.evaluate("async () => await post('/api/scene', {job: S.job})")
    ws = page.evaluate("() => S.res.room.walls")
    out = []
    for item in sc["items"]:
        if not item["parts"]:
            continue
        ok = True
        for w in ws:
            if own_only and w["id"] != item["wall"]:
                continue
            ax, ay, bx, by = w["x0"], w["y0"], w["x1"], w["y1"]
            ln = math.hypot(bx - ax, by - ay)
            nx, ny = -(by - ay) / ln, (bx - ax) / ln
            for part in item["parts"]:
                for x, y in part["outline"]:
                    if (x - ax) * nx + (y - ay) * ny < -0.5:
                        ok = False
        out.append((item["number"], ok))
    return sorted(out)


# ---------------------------------------------------------------------------

def stage_draw(pw):
    print("\nDraw walls: a 4-wall room by clicks, closed on its first corner; then more walls ADDED")
    browser = pw.chromium.launch(headless=not args.headed, args=LAUNCH)
    errors, dialogs = [], []
    ctx, page = open_page(browser, errors, dialogs)
    adopt(page, empty_job("draw4"))
    room_plan(page)
    check("the toolbar: Select on, Draw walls off",
          page.evaluate("() => [...document.querySelectorAll('#roomtools [data-tool]')].map((b) => [b.dataset.tool, b.classList.contains('on')])"),
          [["select", True], ["draw", False]])
    check("with no room the dock shows the Room card, offering a room",
          (page.locator("#roomdock #room").is_visible(), page.locator("#room #roomadd").count()), (True, 1))
    check("no plan drawing before drawing (no room yet)", plan_svgs(page), 0)
    page.click("#drawwalls")
    page.wait_for_selector("#plan svg #drawlayer", timeout=5000)
    check("Draw walls is the tool now", page.evaluate("() => $('drawwalls').classList.contains('on')"), True)
    check("drawing is ON the plan: one plan SVG, the grid laid over it, no canvas of its own",
          [plan_svgs(page), page.locator("#plan svg #drawlayer .drawgrid").count() > 0,
           page.locator("#drawsvg").count()], [1, True, 0])
    check("no room, so nothing is asked", dialogs, [])
    check("the hint says how", "Shift" in page.inner_text("#drawhint"), True)
    click_mm(page, 1000, 1000)
    cx, cy = at_mm(page, 5000, 1030)            # 30 mm off square: snapped to 0 degrees
    page.mouse.move(cx, cy, steps=4)
    time.sleep(0.05)
    band = page.evaluate("() => document.querySelector('#drawreadout').textContent")
    check("the rubber band reads the length in whole 10 mm, about 4000",
          band.endswith("0 mm") and abs(int(band.split()[0]) - 4000) <= 10, True)
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
    a0 = points(page)[0][1:3]
    check("the points are where they were drawn: A starts at (1000, 1000) within a step, nothing re-oriented",
          all(abs(v - 1000) <= 10 for v in a0), True)
    check("closed, and the plan tints the floor",
          (page.evaluate("() => S.res.room.closed"), page.locator("#plan polygon.roomside").count()), (True, 1))
    check("back on Select", page.evaluate("() => $('toolselect').classList.contains('on')"), True)
    check("  one plan SVG after, the grid gone", [plan_svgs(page), page.locator("#plan .drawgrid").count()], [1, 0])
    check("every drawn wall is a critical", len(issues(page, "wall-drawn")), 4)
    check("the Room card marks them drawn",
          page.evaluate("() => document.querySelectorAll('#room [data-wmeasured]').length"), 4)
    shot(page, "draw_closed")
    # measured: typed on A in the Room card's table, ticked on B
    page.fill('#room input[data-wall="A"][data-wk="length"]', str(got[0][1] + 10))
    page.press('#room input[data-wall="A"][data-wk="length"]', "Enter")
    page.wait_for_function("() => !S.job.room.walls.find((w) => w.id === 'A').drawn", timeout=5000)
    page.click('#room [data-wmeasured="B"]')
    page.wait_for_function("() => !S.job.room.walls.find((w) => w.id === 'B').drawn", timeout=5000)
    computed(page)
    check("typing a length or ticking measured clears it",
          [w[3] for w in walls(page)], [False, False, True, True])
    check("  the typed length moved the end point, and the walls after it followed", walls(page)[0][1], got[0][1] + 10)
    check("  so the loop opened by the 10 mm: reported as a near miss, the room an open run",
          page.evaluate("() => [S.res.room.closed, S.res.room.closure_error]"), [False, 10])
    page.fill('#room input[data-wall="A"][data-wk="length"]', str(got[0][1]))
    page.press('#room input[data-wall="A"][data-wk="length"]', "Enter")
    time.sleep(0.3)
    computed(page)
    check("  typed back: closed again", page.evaluate("() => [S.res.room.closed, S.res.room.closure_error]"), [True, 0])
    check("  and the critical with it", sorted(issues(page, "wall-drawn")),
          ["wall C: drawn, not measured — type its length, or tick it as measured",
           "wall D: drawn, not measured — type its length, or tick it as measured"])

    print("\nDrawing again ADDS walls, starting on an existing corner; nothing is asked")
    corner = points(page)[1][3:5]               # B's end: the far corner
    before_box = page.evaluate("() => { const r = document.querySelector('#plan svg').getBoundingClientRect(); "
                               "return [Math.round(r.width), Math.round(r.height)]; }")
    page.click("#drawwalls")
    page.wait_for_selector("#plan svg #drawlayer", timeout=5000)
    check("no 'Replace walls' question", dialogs, [])
    check("the plan is the same drawing at the same size, the walls solid (4 hit lines), "
          "the corners marked, the floor tint shown",
          page.evaluate("""() => { const r = document.querySelector('#plan svg').getBoundingClientRect();
            return [document.querySelectorAll('#tab-room svg.drw').length, Math.round(r.width), Math.round(r.height),
                    document.querySelectorAll('#plan .wallhit').length,
                    document.querySelectorAll('#plan #drawlayer .drawend').length,
                    document.querySelectorAll('#plan polygon.roomside').length]; }"""),
          [1] + before_box + [4, 8, 1])
    shot(page, "draw_on_plan", "#plancard")
    page.click('#planzoombar [data-zoom="0.8"]')
    page.click('#planzoombar [data-zoom="0.8"]')     # zoomed out: room round the plan to draw into
    time.sleep(0.2)
    click_mm(page, corner[0] + 40, corner[1] + 30)      # near the corner: starts on it
    check("the first click lands on the corner itself", page.evaluate("() => DRAW.pts[0]"), corner)
    click_mm(page, corner[0] + 2000, corner[1])
    cx, cy = at_mm(page, corner[0] + 2000, corner[1] + 1500)
    page.mouse.move(cx, cy, steps=3)
    page.mouse.dblclick(cx, cy)
    page.wait_for_function("() => !DRAW && S.job.room.walls.length === 6", timeout=10000)
    computed(page)
    check("two walls added with the next letters, the four kept",
          [w[0] for w in walls(page)], ["A", "B", "C", "D", "E", "F"])
    check("  E starts exactly on the corner it was clicked near", points(page)[4][1:3], corner)
    check("  E and F are drawn; A-D as they were",
          [w[3] for w in walls(page)], [False, False, True, True, True, True])
    check("  the room is still closed, E and F a run off its corner",
          page.evaluate("() => [S.res.room.closed, S.res.room.walk]"), [True, ["A", "B", "C", "D", "E", "F"]])
    shot(page, "draw_added", "#plancard")
    page.click("#drawwalls")
    page.wait_for_selector("#plan svg #drawlayer", timeout=5000)
    click_mm(page, 0, 0)
    page.keyboard.press("Escape")
    time.sleep(0.2)
    check("Esc cancels the drawing, keeps the room and returns to Select",
          [page.evaluate("() => !!DRAW"), len(walls(page)), page.evaluate("() => $('toolselect').classList.contains('on')")],
          [False, 6, True])
    check("no console errors", errors, [])
    ctx.close()
    browser.close()


def stage_one(pw):
    print("\nA one-wall room draws and computes")
    browser = pw.chromium.launch(headless=not args.headed, args=LAUNCH)
    errors, dialogs = [], []
    ctx, page = open_page(browser, errors, dialogs)
    adopt(page, empty_job("one"))
    room_plan(page)
    page.click("#drawwalls")
    page.wait_for_selector("#plan svg #drawlayer", timeout=5000)
    click_mm(page, 0, 0)
    cx, cy = at_mm(page, 3000, 0)
    page.mouse.move(cx, cy, steps=3)
    page.mouse.dblclick(cx, cy)
    page.wait_for_function("() => !DRAW && S.job.room && S.job.room.walls.length === 1", timeout=10000)
    computed(page)
    one = walls(page)
    check("one wall, A, about 3000, free", (len(one), one[0][0], abs(one[0][1] - 3000) <= 10, one[0][2:]),
          (1, "A", True, [None, True]))
    L = one[0][1]
    check("the plan draws it", (page.locator("#plan svg").count(), page.locator("#plan .wallhit").count()), (1, 1))
    check("  with the room side tinted as a band on its face",
          page.locator('#plan polygon.roomside[data-wall="A"]').count(), 1)
    check("the Room card says open run, one wall",
          "open run" in page.inner_text("#closure") and "1 wall," in page.inner_text("#closure"), True)
    shot(page, "one_wall_plan", "#plancard")
    # a cabinet on it, placed from the Placements table
    page.evaluate("() => { S.job.cabinets.push({number: 1, width: 900, height: 720, depth: 580, kind: 'base', "
                  "template: 'standard', doors: 2, drawers: [], support_rows: [], bespoke: [], shelves: 1}); "
                  "S.job.placements = [{cabinet: 1, wall: 'A', x: 500, z: 0, y: 0, flip: false, layer: null}]; "
                  "placesSig = null; schedule(); }")
    computed(page)
    check("a cabinet placed on it is drawn", page.locator('#plan .cab[data-cab="1"]').count() > 0, True)
    g = page.evaluate("() => S.res.room.gaps.map((x) => [x.after, x.before, x.nominal, x.front])")
    check("gaps: to the start and to the end, no corner so no taper", g,
          [[None, 1, 500, 500], [1, None, L - 1400, L - 1400]])
    page.click('#roomsubs [data-roomsub="elev"]')
    page.wait_for_function("() => S.roomSub === 'elev'", timeout=5000)
    page.wait_for_selector("#elevation svg", timeout=10000)
    check("the elevation draws wall A", page.evaluate("() => document.querySelector('#elevation .etrack').dataset.wall"), "A")
    shot(page, "one_wall_elevation", "#elevcard")
    sc = page.evaluate("async () => await post('/api/scene', {job: S.job})")
    check("3D: one wall, the floor its own segment, open", (len(sc["room"]["walls"]), sc["room"]["closed"]), (1, False))
    check("no console errors", errors, [])
    ctx.close()
    browser.close()


def open_l_job(name):
    rm = Room(name=name, ceiling=2600, walls=chain_walls([("A", 3000), ("B", 2000)], closed=False))
    return Job(name=name, room=rm,
               cabinets=[Cabinet(number=n, width=600, height=720, depth=560, kind="base") for n in (1, 2)],
               placements=[Placement(1, "A", 1000), Placement(2, "B", 700)])


def stage_flip(pw):
    print("\nFlip face: one wall's room side turned round, from its Wall card")
    browser = pw.chromium.launch(headless=not args.headed, args=LAUNCH)
    errors, dialogs = [], []
    ctx, page = open_page(browser, errors, dialogs)
    adopt(page, open_l_job("flip"))
    room_plan(page)
    check("both cabinets inside the L, on the room side of both walls", room_side(page), [(1, True), (2, True)])
    check("a click on wall A's hit line selects it", click_wall(page, "A") and page.evaluate("() => S.selWall"), "A")
    check("  and the dock shows its Wall card",
          (page.locator("#wallcard").is_visible(), page.locator("#wallcard h2").text_content().startswith("Wall A"),
           page.evaluate("() => $('room').hidden")), (True, True, True))
    check("  the hit line is marked selected", page.locator('#plan .wallhit.sel[data-wallhit="A"]').count(), 1)
    shot(page, "flip_wall_card", "#roomdock")
    page.click('#wallcard [data-wflip="A"]')
    page.wait_for_function("() => S.job.room.walls.find((w) => w.id === 'A').x0 === 3000", timeout=5000)
    computed(page)
    check("A's end points swapped; B untouched", points(page), [["A", 3000, 0, 0, 0], ["B", 3000, 0, 3000, 2000]])
    check("cabinet 1 keeps its place along A, x from the other end",
          page.evaluate("() => S.job.placements.map((p) => [p.cabinet, p.wall, p.x])"), [[1, "A", 1400], [2, "B", 700]])
    check("it stands on the room's side of its own wall — the outside of the L now",
          room_side(page, own_only=True), [(1, True), (2, True)])
    check("  and cabinet 2 on B is no longer on A's room side (1 is still on B's: B's half plane is the "
          "whole left side)", room_side(page), [(1, True), (2, False)])
    check("A and B no longer meet: two free walls, each with a band",
          (page.evaluate("() => S.res.room.walls.map((w) => w.free)"), page.locator("#plan polygon.roomside").count()),
          ([True, True], 2))
    shot(page, "flip_flipped", "#plancard")
    page.click('#wallcard [data-wflip="A"]')
    page.wait_for_function("() => S.job.room.walls.find((w) => w.id === 'A').x0 === 0", timeout=5000)
    computed(page)
    check("flipped again: back as it was",
          (points(page), page.evaluate("() => S.job.placements.map((p) => [p.cabinet, p.wall, p.x])")),
          ([["A", 0, 0, 3000, 0], ["B", 3000, 0, 3000, 2000]], [[1, "A", 1000], [2, "B", 700]]))
    page.click("#wallback")
    time.sleep(0.2)
    check("Room takes the dock back to the Room card",
          (page.locator("#room").is_visible(), page.evaluate("() => S.selWall")), (True, None))
    check("no console errors", errors, [])
    ctx.close()
    browser.close()


def stage_renumber(pw):
    print("\nRenumber: letters along the walk, behind a confirm that lists the changes")
    browser = pw.chromium.launch(headless=not args.headed, args=LAUNCH)
    errors, dialogs = [], []
    ctx, page = open_page(browser, errors, dialogs)
    rm = Room(name="rn", ceiling=2600, walls=chain_walls([("C", 4000), ("A", 3000), ("D", 4000), ("B", 3000)]))
    job = Job(name="rn", room=rm,
              cabinets=[Cabinet(number=n, width=600, height=720, depth=560, kind="base") for n in (1, 2)],
              placements=[Placement(1, "A", 100), Placement(2, "D", 200)])
    adopt(page, job)
    room_plan(page)
    check("the walk starts at the lowest letter of the loop: A, D, B, C — the table in that order",
          page.evaluate("() => [...document.querySelectorAll('#room tr[data-wallrow]')].map((r) => r.dataset.wallrow)"),
          ["A", "D", "B", "C"])
    page.click("#roomrenumber")
    page.wait_for_function("() => S.res.room.walk.join('') === 'ABCD'", timeout=10000)
    computed(page)
    check("it asked, listing the changes", dialogs[:1] and "D → B" in dialogs[0] and "B → C" in dialogs[0]
          and "C → D" in dialogs[0], True)
    check("the walls are A, B, C, D along the walk, their points untouched",
          points(page), [["A", 4000, 0, 4000, 3000], ["B", 4000, 3000, 0, 3000], ["C", 0, 3000, 0, 0], ["D", 0, 0, 4000, 0]])
    check("the placements followed their walls",
          page.evaluate("() => S.job.placements.map((p) => [p.cabinet, p.wall, p.x])"), [[1, "A", 100], [2, "B", 200]])
    check("nothing orphaned", issues(page, "placement-wall"), [])
    dialogs.clear()
    page.click("#roomrenumber")
    time.sleep(0.3)
    check("already in order: nothing asked, nothing changed", (dialogs, page.evaluate("() => S.res.room.walk")),
          ([], ["A", "B", "C", "D"]))
    shot(page, "renumbered", "#roomdock")
    check("no console errors", errors, [])
    ctx.close()
    browser.close()


def stage_height(pw):
    print("\nWall height: a half wall, a tall unit against it, the elevation and 3D")
    browser = pw.chromium.launch(headless=not args.headed, args=LAUNCH)
    errors, dialogs = [], []
    ctx, page = open_page(browser, errors, dialogs)
    job = Job(name="height", room=rectangular(4000, 3000, ceiling=2600),
              cabinets=[Cabinet(number=1, width=600, height=2100, depth=580, kind="tall")],
              placements=[Placement(1, "B", 500)])
    adopt(page, job)
    room_plan(page)
    page.click('#room tr[data-wallrow="B"] td:first-child')
    page.wait_for_function("() => S.selWall === 'B'", timeout=5000)
    check("a row click selects the wall", page.locator("#wallcard h2").text_content().startswith("Wall B"), True)
    check("the Wall card shows both corners at 90, square",
          page.evaluate("() => ['angle_before', 'angle_after', 'square_before', 'square_after'].map((k) => "
                        "document.querySelector(`#wallcard [data-wk=\"${k}\"]`).value)"), ["90", "90", "0", "0"])
    page.fill('#wallcard input[data-wk="height"]', "1200")
    page.press('#wallcard input[data-wk="height"]', "Enter")
    page.wait_for_function("() => S.job.room.walls.find((w) => w.id === 'B').height === 1200", timeout=5000)
    computed(page)
    check("the height is stored on the wall, the others at the ceiling",
          page.evaluate("() => S.res.room.walls.map((w) => w.wall_height)"), [2600, 1200, 2600, 2600])
    check("a tall unit against the half wall is a WARNING", issues(page, "above-wall"),
          ["reaches 2200, above wall B, which is 1200 high"])
    check("  not a critical: nothing blocks",
          page.evaluate("() => S.res.issues.filter((i) => i.level === 'critical').length"), 0)
    shot(page, "height_wall_card", "#roomdock")
    page.click('#roomsubs [data-roomsub="elev"]')
    page.wait_for_function("() => S.roomSub === 'elev'", timeout=5000)
    page.wait_for_function("() => document.querySelector('#elevation .etrack') && document.querySelector('#elevation .etrack').dataset.wall === 'B'", timeout=10000)
    check("the elevation of B (selected, so shown) has the ceiling dashed above the wall",
          page.locator("#elevation .ceilingline").count(), 1)
    shot(page, "height_elevation", "#elevcard")
    page.click('nav [data-tab="view3d"]')
    page.wait_for_function("() => typeof V3D === 'object' && V3D !== null", timeout=30000)
    page.wait_for_selector("#v3dview canvas", timeout=15000)
    page.wait_for_function("() => !S.sceneStale && V3D.memory().groups > 0", timeout=30000)
    page.wait_for_function("() => V3D.idle()", timeout=15000)
    shell = page.evaluate("() => V3D.debugShell()")
    tops = {w["wall"]: round(w["max"][2]) for w in shell}
    check("3D: wall B stands 1200 high, the others to the ceiling", tops, {"A": 2600, "B": 1200, "C": 2600, "D": 2600})
    shot(page, "height_3d", "#v3dview")
    check("no console errors", errors, [])
    ctx.close()
    browser.close()


def stage_input(pw):
    print("\nRefused at the input: a negative length, an angle out of range")
    browser = pw.chromium.launch(headless=not args.headed, args=LAUNCH)
    errors, dialogs = [], []
    ctx, page = open_page(browser, errors, dialogs)
    job = empty_job("input")
    job.room = rectangular(4000, 3000, ceiling=2600)
    adopt(page, job)
    room_plan(page)
    page.fill('#room input[data-wall="C"][data-wk="length"]', "-4000")
    page.press('#room input[data-wall="C"][data-wk="length"]', "Enter")
    time.sleep(0.4)
    computed(page)
    check("a negative length is not stored", walls(page)[2][1], 4000)
    check("  and the note says how to turn instead", page.inner_text("#room .wallnote"),
          "Wall C: a length cannot be negative. To turn the other way, set the corner angle to 270.")
    page.fill('#room input[data-wall="C"][data-wk="length"]', "4100")
    page.press('#room input[data-wall="C"][data-wk="length"]', "Enter")
    time.sleep(0.4)
    computed(page)
    check("a good entry clears the note, and is stored", (page.inner_text("#room .wallnote"), walls(page)[2][1]), ("", 4100))
    page.fill('#room input[data-wall="B"][data-wk="angle_after"]', "400")
    page.press('#room input[data-wall="B"][data-wk="angle_after"]', "Enter")
    time.sleep(0.4)
    computed(page)
    check("an angle of 400 is not stored: the corner still reads 90", walls(page)[1][2], 90)
    check("  and is said", "between 0 and 360" in page.inner_text("#room .wallnote"), True)
    shot(page, "input_refused", "#roomdock")
    # a good angle turns the plan
    page.fill('#room input[data-wall="A"][data-wk="angle_after"]', "270")
    page.press('#room input[data-wall="A"][data-wk="angle_after"]', "Enter")
    page.wait_for_function("() => S.job.room.walls.find((w) => w.id === 'B').y1 === -3000", timeout=5000)
    computed(page)
    check("270 at A→B: B turns back out, the walls after it with it",
          points(page)[1], ["B", 4000, 0, 4000, -3000])
    check("  the room is an open run now, and the toast said so",
          page.evaluate("() => S.res.room.closed"), False)
    check("no console errors", errors, [])
    ctx.close()
    browser.close()


def stage_drag(pw):
    print("\nDrag a cabinet onto an angled wall")
    browser = pw.chromium.launch(headless=not args.headed, args=LAUNCH)
    errors, dialogs = [], []
    ctx, page = open_page(browser, errors, dialogs)
    # a 4 x 3 room with its C-D corner splayed: E runs at 45 degrees
    job = Job(name="splay", cabinets=[Cabinet(number=1, width=600, height=720, depth=560,
                                              kind="base")],
              placements=[Placement(1, "A", 1000)])
    job.room = Room(name="splay", ceiling=2600, walls=chain_walls(
        [("A", 4000), ("B", 3000), ("C", 2000), ("E", 2828), ("D", 1000)], corners=[90, 90, 135, 135, 90]))
    adopt(page, job)
    room_plan(page)
    check("the splayed room closes", page.evaluate("() => [S.res.room.closed, S.res.room.closure_error]"), [True, 0])
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
    check("the drag selected it: the editor shows in the dock",
          (page.locator("#roomdock #editor").is_visible(), page.evaluate("() => $('room').hidden")), (True, True))
    shot(page, "drag_angled_wall", "#plancard")
    check("no console errors", errors, [])
    ctx.close()
    browser.close()


def stage_3d(pw):
    print("\n3D: an L room with an outside corner and a splayed wall")
    browser = pw.chromium.launch(headless=not args.headed, args=LAUNCH)
    errors, dialogs = [], []
    ctx, page = open_page(browser, errors, dialogs)
    job = Job(name="ell3d", cabinets=[Cabinet(number=1, width=600, height=720, depth=560,
                                              kind="base"),
                                      Cabinet(number=2, width=600, height=720, depth=560,
                                              kind="base")],
              placements=[Placement(1, "A", 1200), Placement(2, "G", 600)])
    job.room = Room(name="ell3d", ceiling=2600, walls=chain_walls(
        [("A", 3000), ("B", 1000), ("C", 1000), ("D", 2000), ("G", 1414), ("E", 3000), ("F", 4000)],
        corners=[90, 270, 90, 135, 135, 90, 90]))
    adopt(page, job)
    check("the room closes", page.evaluate("() => [S.res.room.closed, S.res.room.closure_error]"), [True, 0])
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


def closure_job():
    """Test.json as frozen (tools/fixtures/Test_3d.json), its L closed into a
    rectangle with walls C and D, and a cabinet 99 on D in the D→A corner so
    the elevation of A has a neighbour to show — built here, never saved."""
    from cabinetgen.store import job_from_dict
    with open(os.path.join(ROOT, "tools", "fixtures", "Test_3d.json"), encoding="utf-8") as f:
        job = job_from_dict(json.load(f))
    job.name = "closure"
    job.room.walls += [Wall("C", 4000, 3000, 0, 3000), Wall("D", 0, 3000, 0, 0)]
    job.cabinets.append(Cabinet(number=99, width=600, height=720, depth=560, kind="base"))
    job.placements.append(Placement(99, "D", 2400))
    return job


def displays(page):
    """Every place open / closed is shown, read off the page (ruling 2)."""
    out = {}
    out["room"] = page.evaluate("() => S.res.room.closure")
    out["pill"] = page.evaluate("() => { const p = document.querySelector('#closure .pill'); "
                                "return p ? [p.dataset.closure, p.textContent.trim()] : null; }")
    out["table"] = page.evaluate("() => [...document.querySelectorAll('#room [data-loopgap]')]"
                                 ".map((e) => [e.dataset.loopgap, e.textContent.trim()])")
    out["tint"] = page.evaluate("() => [document.querySelectorAll('#plan polygon.roomside:not([data-wall])').length, "
                                "document.querySelectorAll('#plan polygon.roomside[data-wall]').length]")
    out["issue"] = issues(page, "room-closure")
    sc = page.evaluate("async () => await post('/api/scene', {job: S.job})")
    out["scene"] = sc["room"]["closure"]
    el = page.evaluate("async () => (await post('/api/elevation', {job: S.job, wall: 'A'})).svg")
    out["elev_D"] = "D: 99" in el
    return out


def stage_closure(pw):
    print("\nOpen / closed: ONE source, every display says the same (ruling 2)")
    browser = pw.chromium.launch(headless=not args.headed, args=LAUNCH)
    errors, dialogs = [], []
    ctx, page = open_page(browser, errors, dialogs)
    adopt(page, closure_job())
    room_plan(page)
    d = displays(page)
    check("closed: the engine says closed room", d["room"]["text"], "closed room")
    check("  the Room card pill", d["pill"], ["closed", "closed room"])
    check("  no open gap in the walls table", d["table"], [])
    check("  the plan tints the floor, no face bands", d["tint"], [1, 0])
    check("  no room-closure issue", d["issue"], [])
    check("  the 3D scene says closed", d["scene"]["closed"], True)
    check("  the elevation of A sees the run on D round the corner", d["elev_D"], True)
    page.fill('#room input[data-wall="A"][data-wk="length"]', "4100")
    page.press('#room input[data-wall="A"][data-wk="length"]', "Enter")
    page.wait_for_function("() => S.res.room.closure && !S.res.room.closure.closed", timeout=10000)
    computed(page)
    text = "Loop opens by 100 mm at D\u2192A \u2014 type the other walls or drag a corner"
    d = displays(page)
    check("A typed 4100: the engine says the loop opens by 100 at D→A", d["room"]["text"], text)
    check("  the toast, off the compute, in the same words", page.inner_text("#toast"), text)
    check("  the Room card pill", d["pill"], ["loop", text])
    check("  the walls table's D corner: open by the same 100", d["table"], [["D", "— opens 100 mm"]])
    check("  the plan: no floor tint, a face band per wall", d["tint"], [0, 4])
    check("  Validation: the same words, critical", d["issue"], [text])
    check("  the 3D scene: the same closure", d["scene"], d["room"])
    check("  the elevation of A no longer sees D round a corner", d["elev_D"], False)
    page.click('#room tr[data-wallrow="D"] td:first-child')
    page.wait_for_function("() => S.selWall === 'D'", timeout=5000)
    check("  wall D's card: its corner after reads the same text",
          page.evaluate("() => document.querySelector('#wallcard [data-loopgap]').textContent.trim()"), text)
    shot(page, "closure_open", None)
    page.click('nav [data-tab="view3d"]')
    page.wait_for_function("() => typeof V3D === 'object' && V3D !== null", timeout=30000)
    page.wait_for_function("() => !S.sceneStale && V3D.memory().groups > 0", timeout=30000)
    check("  the 3D view says it too", text in page.inner_text("#v3dview"), True)
    page.click('nav [data-tab="room"]')
    page.wait_for_function("() => S.tab === 'room'", timeout=5000)
    page.click("#wallback")
    time.sleep(0.2)
    page.fill('#room input[data-wall="A"][data-wk="length"]', "4000")
    page.press('#room input[data-wall="A"][data-wk="length"]', "Enter")
    page.wait_for_function("() => S.res.room.closure && S.res.room.closure.closed", timeout=10000)
    computed(page)
    d = displays(page)
    check("typed back: every display says closed",
          [d["room"]["text"], d["pill"], d["table"], d["tint"], d["issue"], d["scene"]["closed"], d["elev_D"]],
          ["closed room", ["closed", "closed room"], [], [1, 0], [], True, True])
    check("  and the toast says it closed", page.inner_text("#toast"), "The loop closes again.")
    page.click('nav [data-tab="view3d"]')
    page.wait_for_function("() => S.tab === 'view3d' && !S.sceneStale", timeout=30000)
    time.sleep(0.3)
    check("  the 3D view's note is gone once it catches up", text in page.inner_text("#v3dview"), False)
    check("no console errors", errors, [])
    ctx.close()
    browser.close()


def stage_layout(pw):
    print("\nThe Room tab's cards fit (ruling 11), at 1360 x 900 and at full HD")
    from cabinetgen.store import job_from_dict
    with open(os.path.join(ROOT, "tools", "fixtures", "Test_3d.json"), encoding="utf-8") as f:
        job = job_from_dict(json.load(f))
    job.name = "layout"
    job.placements = [p for p in job.placements if p.cabinet != 15]     # one unplaced: the strip shows
    browser = pw.chromium.launch(headless=not args.headed, args=LAUNCH)
    for w, h in ((1360, 900), (1920, 1080)):
        errors = []
        ctx = browser.new_context(viewport={"width": w, "height": h})
        page = ctx.new_page()
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.goto(URL)
        page.wait_for_function("() => S.def !== null && S.res", timeout=15000)
        adopt(page, job)
        room_plan(page)
        fit = page.evaluate("""() => { const box = $('plan'), svg = box.querySelector('svg');
            const b = box.getBoundingClientRect(), r = svg.getBoundingClientRect();
            return {inW: r.width <= box.clientWidth, inH: r.height <= box.clientHeight,
                    fills: Math.max(r.width / (box.clientWidth - 24), r.height / (box.clientHeight - 16)),
                    scrollX: box.scrollWidth > box.clientWidth + 1, scrollY: box.scrollHeight > box.clientHeight + 1,
                    pct: $('planzoom').textContent}; }""")
        check(f"{w}: the plan fits its card, width and height, at 100%",
              [fit["inW"], fit["inH"], fit["fills"] > 0.9, fit["scrollX"], fit["scrollY"], fit["pct"]],
              [True, True, True, False, False, "100%"])
        page.click('#planzoombar [data-zoom="1.25"]')
        page.click('#planzoom')
        computed(page)
        check(f"{w}:   and Fit brings it back", page.evaluate(
            "() => { const box = $('plan'); return [box.scrollWidth <= box.clientWidth + 1, $('planzoom').textContent]; }"),
            [True, "100%"])
        g = page.evaluate("""() => { const c = $('gapscard'), t = c.querySelector('table');
            const ths = [...t.querySelectorAll('th')].map((x) => x.getBoundingClientRect().right <= c.getBoundingClientRect().right + 0.5);
            return {full: Math.abs(c.getBoundingClientRect().width - $('roomplanonly').getBoundingClientRect().width) < 2,
                    noScroll: t.getBoundingClientRect().width <= c.clientWidth + 1, cols: ths.every(Boolean),
                    under: c.getBoundingClientRect().top > $('plancard').getBoundingClientRect().bottom - 1}; }""")
        check(f"{w}: Gaps the full width under the plan, every column visible, no sideways scroll",
              [g["full"], g["noScroll"], g["cols"], g["under"]], [True, True, True, True])
        sb = page.evaluate("""() => { const a = $('plinthcard').getBoundingClientRect(), b = $('placescard').getBoundingClientRect(),
            gp = $('gapscard').getBoundingClientRect();
            const nat = (id) => { const c = $(id), t = c.querySelector('table'); return t ? t.getBoundingClientRect().width <= c.clientWidth + 1 : true; };
            return [Math.abs(a.top - b.top) < 2, a.right <= b.left, a.top > gp.bottom - 1, nat('plinthcard'), nat('placescard')]; }""")
        check(f"{w}: Plinth and Placements side by side under Gaps, each table whole",
              sb, [True, True, True, True, True])
        check(f"{w}: the notes are behind a '?', hidden",
              page.evaluate("() => ['gapshelp', 'plinthhelp', 'placeshelp'].map((id) => $(id).hidden)"), [True, True, True])
        page.click('#placescard .qhelp')
        check(f"{w}:   '?' shows them", page.evaluate("() => !$('placeshelp').hidden && $('placeshelp').innerText.includes('X is from')"), True)
        page.click('#placescard .qhelp')
        check(f"{w}: the unplaced strip stays above the plan",
              page.evaluate("() => $('unplaced-room').getBoundingClientRect().bottom <= $('plancard').getBoundingClientRect().top + 1 "
                            "&& $('unplaced-room').querySelectorAll('.upchip').length"), 1)
        os.makedirs(SHOTS, exist_ok=True)
        page.screenshot(path=os.path.join(SHOTS, f"layout_after_{w}x{h}.png"), full_page=True)
        print(f"      screenshot output/_checks/ui_check_walls/layout_after_{w}x{h}.png")
        check(f"{w}: no console errors", errors, [])
        ctx.close()
    browser.close()


STAGES = {"draw": stage_draw, "one": stage_one, "flip": stage_flip, "renumber": stage_renumber,
          "height": stage_height, "input": stage_input, "drag": stage_drag, "3d": stage_3d,
          "closure": stage_closure, "layout": stage_layout}


def main() -> int:
    with sync_playwright() as pw:
        for name, fn in STAGES.items():
            if args.stage in ("all", name):
                fn(pw)
    print(f"\n{'ALL OK' if not FAILS else str(len(FAILS)) + ' FAILED: ' + str(FAILS)}")
    return 1 if FAILS else 0


if __name__ == "__main__":
    raise SystemExit(main())
