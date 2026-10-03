"""The UI restructure, Session 1 (brief of 28 September 2026), in the running app.

    python run_app.py --no-window --port 8766      # in another window
    python tools/ui_check_restructure.py [--port 8766] [--stage tabs|plan|elev|cab3d|attach|place|export|all]

Needs Playwright, like `ui_check_3d.py` and `ui_check_attached.py`, and says so
and exits 0 when it is not installed. Headless Chromium with a real mouse; a
screenshot of every tab, every Room sub-tab and every Cabinets-tab 3D case is
written to `output/_checks/ui_check_restructure/` for looking at.

What it drives, against `jobs/Test.json` unless it says otherwise — the brief's
Session 1 verification list:

* tabs     the new order, the app opening on Catalogue -> Boards (and New going there), and
           the internal jumps still landing: Add with no board -> Catalogue -> Boards, the
           dock's issue line -> Validation, Show in cut list -> Cut list.
* plan     Room -> Plan: the plan, layer toggles, isolate, zoom both ways, a
           real-mouse drag of a cabinet, click-select into the docked editor,
           the walls and placements cards.
* elev     Room -> Elevation: the wall picker, Line / Finish, zoom both ways,
           a real-mouse drag of a cabinet (along and up), a drawer divider drag,
           click-select opening the editor, the legend and the dimension lines;
           and with no room, the prompt to add one (no Run).
* cab3d    the Cabinets tab's 3D: a base, a tall, a blind corner, a mitre and a
           standalone panel, each alone; selecting in the Plan updates it; a
           part pick opens that editor section; the controls (x-ray, fronts,
           labels, cube, help); the editor's Save refreshing it; nothing
           selected -> the first cabinet; no cabinets -> a prompt.
* attach   an attached panel dragged on its arrows in the Cabinets 3D: snapped
           to a carcass face, written to at_x, and the plan follows.
* place    an unplaced cabinet dragged from the slim list onto a wall in the
           Plan, the Elevation and the 3D tab.
* export   two of three walls ticked writes exactly those two elevations (and
           the plan), and no Run drawing.
"""
import argparse
import json
import math
import os
import shutil
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
SHOTS = os.path.join(ROOT, "output", "_checks", "ui_check_restructure")

FAILS = []


def check(label, got, want):
    ok = got == want
    print(f"  {'ok  ' if ok else 'FAIL'}  {label}: {got!r}" + ("" if ok else f"  (wanted {want!r})"))
    if not ok:
        FAILS.append(label)
    return ok


def check_true(label, got, detail=""):
    return check(label + (f" [{detail}]" if detail else ""), bool(got), True)


def shot(page, name, selector=None):
    os.makedirs(SHOTS, exist_ok=True)
    path = os.path.join(SHOTS, name + ".png")
    time.sleep(0.25)
    if selector:
        page.locator(selector).first.screenshot(path=path)
    else:
        page.screenshot(path=path)
    print(f"      screenshot {os.path.relpath(path, ROOT)}")


def new_page(browser, errors):
    ctx = browser.new_context(viewport={"width": 1500, "height": 950})
    page = ctx.new_page()
    page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.on("dialog", lambda d: d.accept())        # "discard unsaved changes?" — yes
    page.goto(URL)
    page.wait_for_function("() => S.def !== null && S.res", timeout=15000)
    return ctx, page


def load_job(page, name):
    # the option for THIS job, not "more than one": jobs/ holds Test.json alone since 28 September 2026
    page.wait_for_function("() => [...document.querySelectorAll('#joblist option')].some((o) => o.value === %s)"
                           % json.dumps(name + ".json"), timeout=15000)
    page.select_option("#joblist", name + ".json")
    page.click("#load")
    page.wait_for_function("() => S.job && S.res && S.job.name === %s" % json.dumps(name), timeout=15000)
    computed(page)


def computed(page):
    """Settle the last edit: run the compute it scheduled now and await it, so
    what is read next answers the job as it stands. It used to be a fixed
    sleep raced against the 180 ms debounce plus the compute, and read the
    previous compute's answer now and then (the race CLAUDE.md recorded on 28
    September 2026)."""
    time.sleep(0.05)
    # the compute redraws the drawing on show without awaiting it; redraw it
    # here and await that, so a locator cannot catch the SVG being replaced
    page.evaluate("async () => { clearTimeout(computeTimer); computeTimer = null; await compute(); "
                  "if (S.tab === 'room' && S.roomSub === 'elev') await renderElevation(); "
                  "else if (S.tab === 'room') await renderPlan(); }")
    page.wait_for_function("() => S.res && S.res.ok !== undefined", timeout=15000)
    time.sleep(0.1)


def tab(page, name):
    page.click(f'nav [data-tab="{name}"]')
    page.wait_for_function(f"() => S.tab === '{name}'", timeout=5000)


def room_sub(page, sub):
    tab(page, "room")
    if page.evaluate("() => S.roomSub") != sub:
        page.click(f'#roomsubs [data-roomsub="{sub}"]')
    page.wait_for_function(f"() => S.roomSub === '{sub}'", timeout=5000)


def select(page, number, isolate=False):
    page.evaluate("() => { selectCabinet(S.job.cabinets.findIndex((c) => c.number === %d), {isolate: %s}); renderList(); }"
                  % (number, "true" if isolate else "false"))
    time.sleep(0.1)


def number_sel(page):
    return page.evaluate("() => S.sel === null ? null : S.job.cabinets[S.sel].number")


def cab3d_ready(page, number=None):
    page.wait_for_function("() => typeof V3C === 'object' && V3C !== null", timeout=30000)
    want = "true" if number is None else f"S.cab3dShown === {number}"
    page.wait_for_function(f"() => !S.cabSceneStale && cabTimer === null && {want}", timeout=20000)
    page.wait_for_function("() => V3C.idle()", timeout=10000)
    time.sleep(0.2)


def placement(page, number):
    return page.evaluate("() => S.job.placements.find((p) => p.cabinet === %d) || null" % number)


def mouse_drag(page, x0, y0, x1, y1, steps=14, pause=0.02):
    page.mouse.move(x0, y0)
    page.mouse.down()
    for i in range(1, steps + 1):
        page.mouse.move(x0 + (x1 - x0) * i / steps, y0 + (y1 - y0) * i / steps)
        time.sleep(pause)
    page.mouse.up()


# ---------------------------------------------------------------------------

def stage_tabs(pw):
    print("\ntabs — the new order, opening on Catalogue -> Boards, the internal jumps")
    browser = pw.chromium.launch(headless=not args.headed, args=LAUNCH)
    errors = []
    ctx, page = new_page(browser, errors)
    check("the tab order", page.locator("nav button").all_inner_texts(),
          ["Catalogue", "Cabinets", "Room", "3D view", "Cut list", "Nesting", "Validation"])
    # Boards became Catalogue -> Boards on 28 September 2026 (the drawers /
    # runners / supports brief); the board library itself did not change
    check("the app opens on Catalogue -> Boards", (page.evaluate("() => [S.tab, S.catSub]"),
                                      page.locator("#catboards").is_visible()), (["catalogue", "boards"], True))
    shot(page, "tab_1_boards_new_job")
    tab(page, "cabinets")
    page.click("#add")
    page.wait_for_function("() => S.tab === 'catalogue' && S.catSub === 'boards'", timeout=5000)
    check("Add cabinet with no board selected goes to Catalogue -> Boards", page.evaluate("() => [S.tab, S.catSub]"), ["catalogue", "boards"])
    load_job(page, "Test")
    for i, t in enumerate(["catalogue", "cabinets", "room", "view3d", "cutlist", "nesting", "validation"]):
        tab(page, t)
        if t == "cabinets":
            cab3d_ready(page)
        if t == "view3d":
            page.wait_for_function("() => typeof V3D === 'object' && V3D && !S.sceneStale", timeout=30000)
        time.sleep(0.5)
        check_true(f"{t}: its section shows, the others do not",
                   page.evaluate("(t) => ['catalogue','cabinets','room','view3d','cutlist','nesting','validation']"
                                 ".every((k) => document.getElementById('tab-' + k).hidden === (k !== t))", t))
        shot(page, f"tab_{i + 1}_{t}")
    # the jumps
    tab(page, "cabinets")
    with_issue = page.evaluate("() => { const s = new Set(); (S.res.issues || []).forEach((i) => { if (/^\\d+$/.test(i.where)) s.add(+i.where); }); return [...s]; }")
    if with_issue:
        select(page, with_issue[0], isolate=True)
        page.locator("#editor .dockissues div").first.click()
        check("a dock issue line still opens Validation", page.evaluate("() => S.tab"), "validation")
    tab(page, "cabinets")
    select(page, 2, isolate=True)
    label = page.evaluate("() => S.res.panels.find((p) => p.cabinet === 2).label")
    page.evaluate("(l) => showInCutList(l)", label)
    check("Show in cut list still lands on the Cut list row",
          (page.evaluate("() => S.tab"), page.locator("#cutlist tr.flash").get_attribute("data-label")),
          ("cutlist", label))
    page.click("#new")
    page.wait_for_function("() => S.job.name === 'untitled' && S.tab === 'catalogue' && S.catSub === 'boards'", timeout=10000)
    check("New goes to Catalogue -> Boards: a new job starts there", page.evaluate("() => [S.tab, S.catSub]"), ["catalogue", "boards"])
    check("no console errors", errors, [])
    ctx.close()
    browser.close()


def stage_plan(pw):
    print("\nRoom -> Plan — today's plan, unchanged")
    browser = pw.chromium.launch(headless=not args.headed, args=LAUNCH)
    errors = []
    ctx, page = new_page(browser, errors)
    load_job(page, "Test")
    room_sub(page, "plan")
    page.wait_for_selector("#plan svg", timeout=15000)
    check("Plan is the default sub-tab, the elevation card hidden",
          (page.locator("#plancard").is_visible(), page.locator("#elevcard").is_visible()), (True, False))
    # the Room redo (2 October 2026): the Walls card is the Room card in the
    # dock, shown while nothing is selected; Gaps and Plinth under the plan, and
    # Placements beside it, a strip until opened (touch-ups, 3 October 2026)
    check_true("the gaps and plinth cards are under it, Placements a strip beside it",
               all(page.locator(f"#{i}").is_visible() for i in ("gaps", "plinth", "placesopen")))
    page.click("#placesopen")
    check_true("  and the strip opens on the placements table", page.locator("#places").is_visible())
    check_true("and the Room card is in the dock with nothing selected",
               page.locator("#roomdock #room").is_visible() and page.locator("#room #walltable").count() == 1)
    check("the one editor is docked beside it",
          page.evaluate("() => document.getElementById('editor').parentElement.id"), "roomdock")
    # layer toggles
    page.click('#layers [data-layer="base"]')
    page.wait_for_function("() => planLayers().indexOf('base') < 0", timeout=5000)
    time.sleep(0.4)
    check_true("a layer switched off ghosts its units", page.locator('#plan [data-layer="base"][opacity="0.30"]').count() > 0
               or page.locator('#plan [opacity="0.30"]').count() > 0)
    page.click('#layers [data-layer="base"]')
    time.sleep(0.8)                                  # let that plan land before isolating
    # isolate from the list, and the way out
    select(page, 3, isolate=True)
    page.evaluate("() => renderPlan()")
    page.wait_for_selector("#unisolate", timeout=5000)
    check("isolate from the list shows the pill", page.locator("#unisolate").inner_text().strip(), "isolating 3 ×")
    page.click("#unisolate")
    page.wait_for_function("() => S.isolate === null", timeout=5000)
    # zoom both ways
    page.click('#planzoombar [data-zoom="1.25"]')
    check("zoom in", page.locator("#planzoom").inner_text(), "125%")
    page.click('#planzoombar [data-zoom="0.8"]')
    page.click('#planzoombar [data-zoom="0.8"]')
    check("zoom out", page.locator("#planzoom").inner_text(), "80%")
    box = page.locator("#plan").bounding_box()
    page.mouse.move(box["x"] + box["width"] / 2, box["y"] + 120)
    page.keyboard.down("Control")
    page.mouse.wheel(0, -300)
    page.keyboard.up("Control")
    time.sleep(0.2)
    check_true("Ctrl+wheel zooms", page.evaluate("() => S.zoom.plan") > 0.8, page.evaluate("() => S.zoom.plan"))
    # zoom speed (drawers redo, Part 8, 29 September 2026): a mouse notch is
    # exp(100 x 0.003) = 1.35; a pinch, many small ctrlKey steps, follows the
    # fingers one for one (Chromium's exp(-deltaY / 100)) — ten steps of -6.93
    # are one doubling
    zoom_after = """(steps) => { zoomReset('plan'); const el = $('plan');
        for (const dy of steps) el.dispatchEvent(new WheelEvent('wheel', {deltaY: dy, deltaMode: 0,
            ctrlKey: true, clientX: 400, clientY: 300, bubbles: true, cancelable: true}));
        return Math.round(S.zoom.plan * 100) / 100; }"""
    check("a Ctrl+wheel notch zooms the plan by 1.35", page.evaluate(zoom_after, [-100]), 1.35)
    check("a pinch of ten small steps summing to -69.3 doubles it", page.evaluate(zoom_after, [-6.93] * 10), 2.0)
    page.click('#planzoombar [data-zoom="reset"]')
    # a real-mouse drag of cabinet 2 along wall A
    time.sleep(0.4)
    p0 = placement(page, 2)
    cab = page.locator('#plan .cab[data-cab="2"]').first.bounding_box()
    track = page.evaluate("() => tracks().find((t) => t.wall === 'A')")
    ux, uy = track["dx"], track["dy"]
    n = math.hypot(ux, uy)
    svgbox = page.evaluate("() => { const s = document.querySelector('#plan svg'); const r = s.getBoundingClientRect(); return [r.width / s.viewBox.baseVal.width]; }")[0]
    px = 180 * (n / track["len"]) * svgbox
    cx, cy = cab["x"] + cab["width"] / 2, cab["y"] + cab["height"] / 2
    mouse_drag(page, cx, cy, cx + ux / n * px, cy + uy / n * px)
    computed(page)
    p1 = placement(page, 2)
    check_true("dragging cabinet 2 in the plan moved it along wall A", p1["x"] != p0["x"] and p1["wall"] == "A",
               f"{p0['x']} -> {p1['x']}")
    check("and selected it without isolating", (number_sel(page), page.evaluate("() => S.isolate")), (2, None))
    check_true("the editor in the dock shows it", "Cabinet 2" in page.locator("#roomdock #editor h2").first.text_content())
    shot(page, "room_plan")
    check("no console errors", errors, [])
    ctx.close()
    browser.close()


def stage_elev(pw):
    print("\nRoom -> Elevation — the wall views, moved from Cabinets, unchanged")
    browser = pw.chromium.launch(headless=not args.headed, args=LAUNCH)
    errors = []
    ctx, page = new_page(browser, errors)
    load_job(page, "Test")
    room_sub(page, "elev")
    page.wait_for_selector("#elevation svg", timeout=15000)
    check("Elevation shows, the plan and its cards hidden",
          (page.locator("#elevcard").is_visible(), page.locator("#plancard").is_visible(),
           page.locator("#roomplanonly").is_visible()), (True, False, False))
    check("the wall picker: a button per wall, no Run",
          page.locator("#elevpick [data-elev]").all_inner_texts(), ["Wall A", "Wall B"])
    check("wall A first", page.evaluate("() => S.elev"), "A")
    check("the one editor docked beside it",
          page.evaluate("() => document.getElementById('editor').parentElement.id"), "roomdock")
    svg = page.locator("#elevation").inner_html()
    check_true("the board / edging legend and the dimension lines are drawn",
               'class="dim"' in svg and ("legend" in svg or "swatch" in svg))
    check_true("the ceiling line is drawn", "ceiling" in svg.lower())
    shot(page, "room_elevation_A_line")
    # wall switch
    page.click('#elevpick [data-elev="B"]')
    page.wait_for_function("() => S.elev === 'B' && document.querySelector('#elevpick [data-elev=\"B\"].on')", timeout=5000)
    page.wait_for_function("() => document.querySelector('#elevation .etrack').dataset.wall === 'B'", timeout=10000)
    check("switching to wall B draws wall B", page.evaluate("() => document.querySelector('#elevation .etrack').dataset.wall"), "B")
    # Line / Finish
    line_b = page.locator("#elevation").inner_html()
    page.click('#elevpick [data-elevmode="finish"]')
    page.wait_for_function("() => S.elevMode === 'finish' && document.querySelector('#elevpick [data-elevmode=\"finish\"].on')", timeout=5000)
    time.sleep(0.6)
    fin_b = page.locator("#elevation").inner_html()
    check_true("Finish draws the neighbours as seen from this wall", fin_b != line_b and "as seen from this wall" in fin_b)
    shot(page, "room_elevation_B_finish")
    page.click('#elevpick [data-elevmode="line"]')
    page.click('#elevpick [data-elev="A"]')
    page.wait_for_function("() => document.querySelector('#elevation .etrack').dataset.wall === 'A'", timeout=10000)
    # zoom both ways
    page.click('#elevzoombar [data-zoom="1.25"]')
    check("zoom in", page.locator("#elevzoom").inner_text(), "125%")
    page.click('#elevzoombar [data-zoom="0.8"]')
    page.click('#elevzoombar [data-zoom="0.8"]')
    check("zoom out", page.locator("#elevzoom").inner_text(), "80%")
    box = page.locator("#elevation").bounding_box()
    page.mouse.move(box["x"] + box["width"] / 2, box["y"] + 100)
    page.keyboard.down("Control")
    page.mouse.wheel(0, 300)
    page.keyboard.up("Control")
    time.sleep(0.2)
    check_true("Ctrl+wheel zooms (out)", page.evaluate("() => S.zoom.elevation") < 0.8, page.evaluate("() => S.zoom.elevation"))
    page.click('#elevzoombar [data-zoom="reset"]')
    time.sleep(0.4)
    # click-select opens the editor
    g = page.locator('#elevation .ecabg[data-cab="3"] .ecab').first.bounding_box()
    page.mouse.click(g["x"] + g["width"] / 2, g["y"] + g["height"] * 0.8)
    page.wait_for_function("() => S.sel !== null && S.job.cabinets[S.sel].number === 3", timeout=5000)
    # the editor paints after the selection lands: wait for it, not the first frame
    page.wait_for_function("() => ((document.querySelector('#roomdock #editor h2') || {}).textContent || '')"
                           ".includes('Cabinet 3')", timeout=5000)
    check_true("a click selects cabinet 3 and the docked editor shows it",
               "Cabinet 3" in page.locator("#roomdock #editor h2").first.text_content())
    computed(page)
    # drag cabinet 5 (the wall unit) along and down with a real mouse
    p0 = placement(page, 5)
    t = page.evaluate("() => { const t = elevTrack(); const r = t.svg.getBoundingClientRect(); return {scale: t.scale * r.width / t.svg.viewBox.baseVal.width}; }")
    g = page.locator('#elevation .ecabg[data-cab="5"] .ecab').first.bounding_box()
    cx, cy = g["x"] + g["width"] / 2, g["y"] + g["height"] / 2
    mouse_drag(page, cx, cy, cx - 120 * t["scale"], cy + 60 * t["scale"])
    computed(page)
    p1 = placement(page, 5)
    check_true("dragging cabinet 5 moved it along the wall and down it",
               p1["x"] != p0["x"] and p1["z"] != p0["z"], f"{p0['x']},{p0['z']} -> {p1['x']},{p1['z']}")
    # a drawer divider (cabinet 4 or 7 carries a drawer stack on wall A)
    line = page.locator("#elevation .fdiv").first
    lb = line.bounding_box()
    cab = int(line.get_attribute("data-cab"))
    above = int(line.get_attribute("data-above"))
    h0 = page.evaluate(f"() => S.job.cabinets.find((c) => c.number === {cab}).drawers.map((d) => d.face_height)")
    mouse_drag(page, lb["x"] + lb["width"] / 2, lb["y"] + lb["height"] / 2,
               lb["x"] + lb["width"] / 2, lb["y"] + lb["height"] / 2 + 25 * t["scale"], steps=8)
    computed(page)
    h1 = page.evaluate(f"() => S.job.cabinets.find((c) => c.number === {cab}).drawers.map((d) => d.face_height)")
    check_true(f"dragging the divider under drawer {above + 1} of cabinet {cab} moved that pair only",
               h1[above] != h0[above] and h1[above] + h1[above + 1] == h0[above] + h0[above + 1]
               and h1[:above] + h1[above + 2:] == h0[:above] + h0[above + 2:], f"{h0} -> {h1}")
    check("  and it is an unsaved edit", page.evaluate("() => S.dirty"), True)
    shot(page, "room_elevation_after_drags")
    # attached panels travel with their cabinet: the drawing marks them
    page.evaluate("async () => { const i = S.job.cabinets.findIndex((c) => c.number === 2); "
                  "const r = await post('/api/panel-new-attached', {job: S.job, index: i}); "
                  "S.job.cabinets.push(r.cabinet); await compute(); await renderElevation(); }")
    page.wait_for_function("() => document.querySelector('#elevation [data-host=\"2\"]') !== null", timeout=10000)
    check_true("a panel attached to cabinet 2 is drawn as cabinet 2's, to travel with it",
               page.locator('#elevation [data-host="2"]').count() > 0)
    # no room: a prompt, no Run
    page.click("#new")
    page.wait_for_function("() => S.job.name === 'untitled'", timeout=10000)
    room_sub(page, "elev")
    page.wait_for_selector("#elevaddroom", timeout=5000)
    check_true("no room: the Elevation asks for one, and draws no Run",
               "No room yet" in page.locator("#elevation").inner_text() and page.locator("#elevation svg").count() == 0)
    shot(page, "room_elevation_no_room")
    page.click("#elevaddroom")
    page.wait_for_selector("#elevation svg", timeout=10000)
    check("Add a room from there draws wall A", page.evaluate("() => S.elev"), "A")
    check("no console errors", errors, [])
    ctx.close()
    browser.close()


def stage_cab3d(pw):
    print("\nthe Cabinets tab's 3D — one cabinet alone")
    browser = pw.chromium.launch(headless=not args.headed, args=LAUNCH)
    errors = []
    ctx, page = new_page(browser, errors)
    tab(page, "cabinets")
    cab3d_ready(page)
    check_true("no cabinets: a prompt to add one", page.locator("#c3dempty").is_visible()
               and "No cabinets yet" in page.locator("#c3dempty").inner_text())
    shot(page, "cab3d_0_empty", "#cab3dcard")
    load_job(page, "Test")
    tab(page, "cabinets")
    cab3d_ready(page)
    first = page.evaluate("() => S.job.cabinets[0].number")
    check("nothing selected: the first cabinet", page.evaluate("() => S.cab3dShown"), first)
    check("the editor is on the right, the list below the 3D",
          (page.evaluate("() => document.getElementById('editor').parentElement.id"),
           page.evaluate("() => document.getElementById('cab3dcard').getBoundingClientRect().bottom <= document.getElementById('cablist').getBoundingClientRect().top")),
          ("cabdock", True))
    # a blind corner, made from cabinet 2 in the page
    page.evaluate("async () => { const r = await post('/api/duplicate', {job: S.job, index: 1}); "
                  "const c = r.cabinets[0]; c.corner_unit = true; c.corner_style = 'blind'; c.blind_width = 400; "
                  "c.width = 1000; c.has_doors = true; c.doors = 1; S.job.cabinets.push(c); "
                  "S.job.placements = places().filter((p) => p.cabinet !== c.number); await compute(); }")
    blind = page.evaluate("() => S.job.cabinets[S.job.cabinets.length - 1].number")
    cases = [(2, "base"), (1, "tall"), (blind, "blind corner"), (13, "mitre"), (8, "standalone panel")]
    for n, what in cases:
        tab(page, "cabinets")
        select(page, n)
        cab3d_ready(page, n)
        items = page.evaluate("() => V3C.memory()")
        roles = page.evaluate(f"async () => {{ const r = await post('/api/scene-cabinet', {{job: S.job, number: {n}}}); "
                              f"return [r.items.map((i) => i.number), [...new Set(r.items[0].parts.map((q) => q.role))]]; }}")
        check(f"{what} {n}: drawn alone", roles[0], [n])
        check_true(f"  one group in the view, and nothing of the room", items["groups"] == 1, f"{items}")
        if what in ("base", "tall"):
            check_true("  its shelves and supports drawn", "support" in roles[1] or "shelf" in roles[1], f"{roles[1]}")
        if what == "blind corner":
            check_true("  its blind panel drawn", "blind" in roles[1], f"{roles[1]}")
        if what == "standalone panel":
            check("  a panel is one board", roles[1], ["panel"])
        shot(page, f"cab3d_{what.replace(' ', '_')}_{n}", "#cab3dcard")
    # select from the Plan updates the Cabinets 3D
    room_sub(page, "plan")
    page.wait_for_selector('#plan .cab[data-cab="3"]', timeout=10000)
    if page.evaluate("() => S.isolate !== null"):
        page.evaluate("() => { S.isolate = null; renderPlan(); }")
        time.sleep(0.4)
    page.locator('#plan .cab[data-cab="3"]').first.click()
    page.wait_for_function("() => S.sel !== null && S.job.cabinets[S.sel].number === 3", timeout=5000)
    tab(page, "cabinets")
    cab3d_ready(page, 3)
    check("selecting cabinet 3 in the Plan: the Cabinets 3D shows 3", page.evaluate("() => S.cab3dShown"), 3)
    # the controls
    view = page.locator("#c3dview canvas").first.bounding_box()
    page.mouse.move(view["x"] + view["width"] / 2, view["y"] + view["height"] / 2)
    page.keyboard.press("x")
    check("X: x-ray", page.evaluate("() => V3C.state().display"), "xray")
    page.keyboard.press("x")
    page.click("#c3dbar button:has-text('Fronts')")
    time.sleep(0.6)
    check("Fronts: open", page.evaluate("() => V3C.state().fronts"), True)
    page.click("#c3dbar button:has-text('Labels')")
    check("Labels toggle", page.evaluate("() => V3C.state().labels"), False)
    page.click("#c3dbar button:has-text('Labels')")
    check_true("the view cube is there", page.locator("#c3dview .v3dcube").count() == 1)
    page.click("#c3dbar button:has-text('?')")
    check_true("the help card opens", page.locator("#c3dview .v3dhelp").is_visible())
    page.click("#c3dbar button:has-text('?')")
    # orbit with a real mouse
    cam0 = page.evaluate("() => V3C.camera()")
    mouse_drag(page, view["x"] + view["width"] * 0.3, view["y"] + view["height"] * 0.6,
               view["x"] + view["width"] * 0.55, view["y"] + view["height"] * 0.5)
    page.wait_for_function("() => V3C.idle()", timeout=10000)
    check_true("left-drag orbits", page.evaluate("() => V3C.camera()") != cam0)
    shot(page, "cab3d_controls_fronts_open", "#cab3dcard")
    page.click("#c3dbar button:has-text('Fronts')")
    time.sleep(0.6)
    # part pick -> the editor jumps to that section (keys act with the pointer over the view)
    page.mouse.move(view["x"] + view["width"] / 2, view["y"] + view["height"] / 2)
    page.keyboard.press("h")
    page.wait_for_function("() => V3C.idle()", timeout=10000)
    time.sleep(0.3)
    scene = page.evaluate("async () => (await post('/api/scene-cabinet', {job: S.job, number: 3})).items[0]")
    door = next((q for q in scene["parts"] if q["role"] == "door"), None)
    if door:
        xs = [v[0] for v in door["outline"]]
        ys = [v[1] for v in door["outline"]]
        pr = page.evaluate(f"() => V3C.project({(min(xs) + max(xs)) / 2}, {max(ys)}, {(door['z0'] + door['z1']) / 2})")
        r = page.evaluate("() => { const r = document.querySelector('#c3dview canvas').getBoundingClientRect(); return [r.left, r.top]; }")
        page.mouse.click(r[0] + pr["x"], r[1] + pr["y"])
        time.sleep(0.4)
        # read the flash BEFORE the screenshot: it lasts 1.2 s, and a software-
        # rendered screenshot of the 3D card can take longer than what is left
        check("picking a door opens the editor at Doors",
              page.evaluate("() => { const f = document.querySelector('#editor .sec.flash'); return f && f.classList.contains('s-doors') ? 'Doors' : f && f.className; }"),
              "Doors")
        shot(page, "cab3d_part_pick", "#cab3dcard")
        check_true("  and the part card names its cut-list line",
                   door["line"] and door["line"] in page.locator("#c3dview .v3dcard").inner_text())
    # the editor's Save: an edit shows at once, Save refreshes
    w0 = page.evaluate("() => V3C.bounds(3)")
    page.fill('#editor [data-k="width"]', "700")
    page.dispatch_event('#editor [data-k="width"]', "input")
    page.click("#edsave")
    page.wait_for_function("() => { const b = V3C.bounds(3); return b && Math.round(b.max[0] - b.min[0]) >= 700; }", timeout=15000)
    w1 = page.evaluate("() => V3C.bounds(3)")
    check_true("an edit and Save: the 3D shows the new width at once",
               round(w1["max"][0] - w1["min"][0]) > round(w0["max"][0] - w0["min"][0]),
               f"{round(w0['max'][0] - w0['min'][0])} -> {round(w1['max'][0] - w1['min'][0])}")
    check("no console errors", errors, [])
    ctx.close()
    browser.close()


def stage_attach(pw):
    print("\nan attached panel dragged in the Cabinets 3D (spec B4)")
    browser = pw.chromium.launch(headless=not args.headed, args=LAUNCH)
    errors = []
    ctx, page = new_page(browser, errors)
    load_job(page, "Test")
    tab(page, "cabinets")
    select(page, 2)
    page.wait_for_selector("#attachedbox #padd", timeout=5000)
    page.click("#attachedbox #padd")
    page.wait_for_function("() => S.job.cabinets.some((c) => c.panel && c.panel.attached_to === 2)", timeout=10000)
    computed(page)
    num = page.evaluate("() => S.job.cabinets.find((c) => c.panel && c.panel.attached_to === 2).number")
    select(page, num)
    cab3d_ready(page, 2)
    check("the attached panel shows with its cabinet", page.evaluate("() => V3C.memory().groups"), 2)
    page.wait_for_function("() => V3C.dragInfo().handles.length === 3", timeout=10000)
    check("selected, it gets three arrows: across, back, up",
          sorted(h["axis"] for h in page.evaluate("() => V3C.dragInfo().handles")), ["x", "y", "z"])
    spec0 = page.evaluate(f"() => S.job.cabinets.find((c) => c.number === {num}).panel")
    x_before = page.evaluate(f"() => S.res.geometry['{num}'].panel.placed_at.x")
    # look straight at the front so "across" reads left to right
    view = page.locator("#c3dview canvas").first.bounding_box()
    page.mouse.move(view["x"] + view["width"] / 2, view["y"] + view["height"] / 2)
    page.keyboard.press("h")
    page.wait_for_function("() => V3C.idle()", timeout=10000)
    time.sleep(0.3)
    info = page.evaluate("() => V3C.dragInfo()")
    hd = next(h for h in info["handles"] if h["axis"] == "x")
    o, d = hd["origin"], hd["dir"]
    p0 = page.evaluate(f"() => V3C.project({o[0] + d[0] * 140}, {o[1] + d[1] * 140}, {o[2] + d[2] * 140})")
    p1 = page.evaluate(f"() => V3C.project({o[0] + d[0] * 340}, {o[1] + d[1] * 340}, {o[2] + d[2] * 340})")
    per_mm = math.hypot(p1["x"] - p0["x"], p1["y"] - p0["y"]) / 200
    ux, uy = (p1["x"] - p0["x"]) / (per_mm * 200), (p1["y"] - p0["y"]) / (per_mm * 200)
    width = page.evaluate("() => S.res.geometry['2'].width")
    # from at_x -16 (outside the left side) to the far side: width + 16, snapped to "outside the right"
    target = width + 16 - 7
    sx, sy = view["x"] + p0["x"], view["y"] + p0["y"]
    mouse_drag(page, sx, sy, sx + ux * per_mm * target, sy + uy * per_mm * target, steps=16)
    page.wait_for_function("() => !V3C.dragInfo().dragging", timeout=10000)
    computed(page)
    spec1 = page.evaluate(f"() => S.job.cabinets.find((c) => c.number === {num}).panel")
    check("dragging the across arrow wrote at_x, snapped to the right side, outside",
          spec1["at_x"], width)
    check("  and nothing else about the panel", {k: v for k, v in spec1.items() if k != "at_x"},
          {k: v for k, v in spec0.items() if k != "at_x"})
    check("  the room follows: its place on the wall moved by the same",
          page.evaluate(f"() => S.res.geometry['{num}'].panel.placed_at.x") - x_before, width + 16)
    check("  and Panel design's offsets read the same figure",
          page.evaluate("() => { const e = document.querySelector('#panelbox [data-pk=\"at_x\"]'); return e ? +e.value : null; }"),
          width)
    shot(page, "cab3d_attached_panel_dragged", "#cab3dcard")
    check("no console errors", errors, [])
    ctx.close()
    browser.close()


def stage_place(pw):
    print("\nplacing from the list of unplaced items: Plan, Elevation, 3D")
    browser = pw.chromium.launch(headless=not args.headed, args=LAUNCH)
    errors = []
    ctx, page = new_page(browser, errors)
    load_job(page, "Test")

    def new_unplaced():
        page.evaluate("async () => { const r = await post('/api/duplicate', {job: S.job, index: 1}); "
                      "S.job.cabinets.push(r.cabinets[0]); await compute(); renderUnplaced(); }")
        return page.evaluate("() => S.job.cabinets[S.job.cabinets.length - 1].number")

    def chip(n, box):
        page.wait_for_selector(f'#{box} .upchip[data-up="{n}"]', timeout=10000)
        return page.locator(f'#{box} .upchip[data-up="{n}"]').bounding_box()

    # the list: unplaced cabinets and standalone panels, never an attached panel
    room_sub(page, "plan")
    page.evaluate("async () => { const i = S.job.cabinets.findIndex((c) => c.number === 2); "
                  "const r = await post('/api/panel-new-attached', {job: S.job, index: i}); "
                  "S.job.cabinets.push(r.cabinet); await compute(); renderUnplaced(); }")
    att = page.evaluate("() => S.job.cabinets[S.job.cabinets.length - 1].number")
    check("an attached panel never appears in the list", page.locator(f'#unplaced-room .upchip[data-up="{att}"]').count(), 0)

    # Plan
    n = new_unplaced()
    b = chip(n, "unplaced-room")
    check_true("a new cabinet with no placement is listed in the Plan", b is not None)
    shot(page, "place_list_plan")
    wall = page.evaluate("() => { const t = tracks().find((k) => k.wall === 'B'); const s = document.querySelector('#plan svg'); "
                         "const r = s.getBoundingClientRect(); const k = r.width / s.viewBox.baseVal.width; "
                         "return [r.left + (t.x1 + t.dx * 0.8) * k, r.top + (t.y1 + t.dy * 0.8) * k]; }")
    mouse_drag(page, b["x"] + b["width"] / 2, b["y"] + b["height"] / 2, wall[0], wall[1], steps=20)
    computed(page)
    p = placement(page, n)
    check_true("dropped on wall B in the Plan: placed on wall B", p and p["wall"] == "B", f"{p}")
    check("  and no longer listed", page.locator(f'#unplaced-room .upchip[data-up="{n}"]').count(), 0)
    check_true("  the engine placed it (it is in the compute's placements)",
               page.evaluate(f"() => !!S.res.room.placements['{n}']"))

    # Elevation
    room_sub(page, "elev")
    page.wait_for_selector("#elevation svg", timeout=10000)
    n = new_unplaced()
    b = chip(n, "unplaced-room")
    t = page.evaluate("() => { const t = elevTrack(); const r = t.svg.getBoundingClientRect(); const k = r.width / t.svg.viewBox.baseVal.width; "
                      "return [r.left + (t.x0 + 250 * t.scale) * k, r.top + (t.y0 - 1700 * t.scale) * k, t.wall]; }")
    mouse_drag(page, b["x"] + b["width"] / 2, b["y"] + b["height"] / 2, t[0], t[1], steps=20)
    computed(page)
    p = placement(page, n)
    check_true(f"dropped on wall {t[2]} in the Elevation: placed on it, hung where released",
               p and p["wall"] == t[2] and p["z"] > 0, f"{p}")
    shot(page, "place_dropped_elevation")

    # 3D
    tab(page, "view3d")
    page.wait_for_function("() => typeof V3D === 'object' && V3D && !S.sceneStale", timeout=30000)
    page.wait_for_function("() => V3D.idle()", timeout=10000)
    n = new_unplaced()
    page.wait_for_function("() => !S.sceneStale && sceneTimer === null", timeout=15000)
    b = chip(n, "unplaced-3d")
    view = page.locator("#v3dview canvas").first.bounding_box()
    page.mouse.move(view["x"] + view["width"] / 2, view["y"] + view["height"] / 2)
    page.keyboard.press("t")                      # the plan from above: the floor is under the cursor
    page.wait_for_function("() => V3D.idle()", timeout=10000)
    time.sleep(0.3)
    wall_b = page.evaluate("() => { const w = S.job.room.walls.find((k) => k.id === 'B'); return w; }")
    hit_at = None
    for fx, fy in ((0.5, 0.5), (0.4, 0.6), (0.6, 0.4), (0.3, 0.3), (0.7, 0.7)):
        cand = page.evaluate(f"() => V3D.wallAt({view['x'] + view['width'] * fx}, {view['y'] + view['height'] * fy})")
        if cand:
            hit_at = (view["x"] + view["width"] * fx, view["y"] + view["height"] * fy, cand)
            break
    check_true("the 3D view says which wall a point in it is nearest", hit_at is not None)
    mouse_drag(page, b["x"] + b["width"] / 2, b["y"] + b["height"] / 2, hit_at[0], hit_at[1], steps=20)
    computed(page)
    p = placement(page, n)
    check_true(f"dropped in 3D over the floor: placed on the nearest wall ({hit_at[2]['wall']}), standing",
               p and p["wall"] == hit_at[2]["wall"] and p["z"] == 0, f"{p}")
    page.wait_for_function(f"() => !S.sceneStale && V3D.bounds({n}) !== null", timeout=15000)
    check_true("  and the 3D view draws it", page.evaluate(f"() => V3D.bounds({n}) !== null"))
    shot(page, "place_dropped_3d")
    del wall_b
    check("no console errors", errors, [])
    ctx.close()
    browser.close()


def stage_export(pw):
    print("\nexport — two of three walls ticked")
    browser = pw.chromium.launch(headless=not args.headed, args=LAUNCH)
    errors = []
    ctx, page = new_page(browser, errors)
    load_job(page, "Test")
    room_sub(page, "plan")
    # a third wall off B's free end: the Wall card's "+ Wall after" (room redo
    # Phase 1, 2 October 2026 — the Walls card's "+ Wall after" went with it)
    page.click('#room tr[data-wallrow="B"] td:first-child')
    page.wait_for_function("() => S.selWall === 'B'", timeout=5000)
    page.click('#wallcard [data-wadd="after"]')
    page.wait_for_function("() => S.job.room.walls.length === 3", timeout=10000)
    computed(page)
    name = "ui_restructure_export"
    shutil.rmtree(os.path.join(ROOT, "output", name), ignore_errors=True)
    page.fill("#jobname", name)
    page.dispatch_event("#jobname", "input")
    computed(page)
    # This stage tests the export, not Test.json's design: live data that
    # carries a drawer critical (since the drawer setting of 28 September 2026,
    # cabinet 4's top box fouls its Top Front) would disable Export. Take the
    # drawers off any cabinet a drawer critical names, in memory only.
    page.evaluate("""() => {
      const bad = new Set((S.res.issues || []).filter((i) => i.level === 'critical' &&
        /^(drawer-|support-drawer-foul)/.test(i.check || '')).map((i) => i.where));
      S.job.cabinets.forEach((c) => { if (bad.has(String(c.number))) c.has_drawers = false; });
    }""")
    page.evaluate("async () => { await compute(); }")
    page.wait_for_function("() => !document.getElementById('export').disabled", timeout=15000)
    page.click("#export")
    page.wait_for_selector("#exportdlg[open]", timeout=5000)
    walls = page.evaluate("() => [...document.querySelectorAll('#exportwalls [data-exwall]')].map((x) => [x.dataset.exwall, x.checked])")
    check("a tick per wall, all ticked by default", walls, [["A", True], ["B", True], ["C", True]])
    shot(page, "export_dialog")
    page.uncheck('#exportwalls [data-exwall="B"]')
    page.click("#exportgo")
    page.wait_for_function("() => S.lastExport && S.lastExport.dir && S.lastExport.dir.endsWith(%s)" % json.dumps(name),
                           timeout=30000)
    files = page.evaluate("() => S.lastExport.files")
    svgs = sorted(f for f in files if f.endswith(".svg") and not f.startswith("nest_"))
    check("exactly the two ticked walls' elevations, and the plan",
          svgs, [f"{name}_elevation_A.svg", f"{name}_elevation_C.svg", f"{name}_plan.svg"])
    on_disk = sorted(f for f in os.listdir(os.path.join(ROOT, "output", name, "drawings"))
                     if f.endswith(".svg"))
    check("and on disk, in drawings/: no Run drawing, no wall B", on_disk, svgs)
    check("the export's folders", sorted(os.listdir(os.path.join(ROOT, "output", name))),
          ["cutlist", "drawings", "nesting"])
    toast = page.locator("#toast").text_content()
    check("the toast names output/<job>/ and the folders written",
          (f"output/{name}/" in toast, "cutlist/" in toast, "nesting/" in toast,
           "drawings/" in toast), (True, True, True, True))
    check("no console errors", errors, [])
    ctx.close()
    browser.close()


STAGES = {"tabs": stage_tabs, "plan": stage_plan, "elev": stage_elev, "cab3d": stage_cab3d,
          "attach": stage_attach, "place": stage_place, "export": stage_export}

with sync_playwright() as pw:
    for key, fn in STAGES.items():
        if args.stage in ("all", key):
            fn(pw)

print(f"\nui_check_restructure: {'all good' if not FAILS else str(len(FAILS)) + ' FAILED: ' + str(FAILS)}")
sys.exit(1 if FAILS else 0)
