"""The drawers / runners / supports brief (28 September 2026) in the running app,
with a real browser (Playwright, optional).

    python run_app.py --no-window --port 8766      # in another window
    python tools/ui_check_drawers.py [--port 8766] [--stage supports|catalogue|runners|drawers|3d|all]

Drives what the check_*.py scripts cannot: the Supports section's new words and
its Long / Short edge counts (Part 1), Catalogue -> Boards | Runners and the
runner library (Part 2), the drawer's runner and inner drawers in the editor
(Parts 2 and 4), and drawer boxes and runners in the 3D (Part 6). Against
`Test.json`, never saved: the top-bar Save is the only thing that writes.
Screenshots go into output/ui_check_drawers/.

Playwright is the only third-party package anywhere near this app and only the
ui_check scripts need it; without it this says so and exits 0.
"""
import argparse
import json
import os
import sys
import time

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, ROOT)

try:
    from playwright.sync_api import sync_playwright
except ImportError:                                            # pragma: no cover
    print("playwright is not installed — skipping the browser check (pip install playwright)")
    sys.exit(0)

ap = argparse.ArgumentParser()
ap.add_argument("--port", type=int, default=8766)
ap.add_argument("--stage", default="all")
ap.add_argument("--headed", action="store_true")
args = ap.parse_args()
URL = f"http://127.0.0.1:{args.port}/"
LAUNCH = ["--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist"]
SHOTS = os.path.join(ROOT, "output", "ui_check_drawers")

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


def new_page(browser, errors):
    ctx = browser.new_context(viewport={"width": 1500, "height": 950})
    page = ctx.new_page()
    page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.on("dialog", lambda d: d.accept())
    page.goto(URL)
    page.wait_for_function("() => S.def !== null && S.res", timeout=15000)
    return ctx, page


def load_job(page, name):
    page.wait_for_function("() => [...document.querySelectorAll('#joblist option')].some((o) => o.value === %s)"
                           % json.dumps(name + ".json"), timeout=15000)
    page.select_option("#joblist", name + ".json")
    page.click("#load")
    page.wait_for_function("() => S.job && S.res && S.job.name === %s" % json.dumps(name), timeout=15000)
    computed(page)


def computed(page):
    """Settle the edits: whatever compute the last one scheduled is run now and
    awaited, so what is read next is the answer to the job as it stands — no
    fixed sleep raced against a compute in flight."""
    time.sleep(0.05)
    page.evaluate("async () => { clearTimeout(computeTimer); computeTimer = null; await compute(); }")
    page.wait_for_function("() => S.res && S.res.ok !== undefined", timeout=15000)
    time.sleep(0.1)


def tab(page, name):
    page.click(f'nav [data-tab="{name}"]')
    page.wait_for_function(f"() => S.tab === '{name}'", timeout=5000)


def select(page, number):
    if page.evaluate("() => S.tab") != "cabinets":
        tab(page, "cabinets")
    page.evaluate("() => { selectCabinet(S.job.cabinets.findIndex((c) => c.number === %d), {isolate: false}); renderList(); }"
                  % number)
    page.wait_for_function(f"() => S.sel !== null && S.job.cabinets[S.sel].number === {number}", timeout=5000)
    time.sleep(0.1)


def text(page, sel):
    return page.evaluate(f"() => (document.querySelector({json.dumps(sel)}) || {{}}).textContent || ''")


# ---------------------------------------------------------------------------

def stage_supports(pw):
    print("\nPart 1 — supports: the words, and edges as long / short counts")
    browser = pw.chromium.launch(headless=not args.headed, args=LAUNCH)
    errors = []
    ctx, page = new_page(browser, errors)
    load_job(page, "Test")
    select(page, 6)
    page.wait_for_selector("#supportbox .supblock", timeout=5000)
    labels = page.evaluate("() => [...document.querySelectorAll('#supportbox .supblock .f > label')].map((l) => l.textContent.trim())")
    check("Support Material / Edging Material / Edging Colour", all(x in labels for x in
          ("Support Material", "Edging Material", "Edging Colour")), True)
    check("  and no 'Cut from' / 'Colour' left", any(x in ("Cut from", "Colour", "Edging") for x in labels), False)
    check("Long edges banded / Short edges banded", ("Long edges banded" in labels, "Short edges banded" in labels), (True, True))
    check("no per-edge tickboxes", page.evaluate("() => document.querySelectorAll('#supportbox [data-sk^=\"edge:\"]').length"), 0)
    heads = page.evaluate("() => [...document.querySelectorAll('#supportbox .supblock h4 label')].map((l) => l.textContent.trim())")
    check("the first block reads Top Front", heads[0], "Top Front")
    # cabinet 6's Back row is stored as the REAR edge alone, not edged: not canonical
    idx = page.evaluate("() => S.job.cabinets[S.sel].support_rows.findIndex((r) => r.type === 'back')")
    check("cabinet 6's Back is stored as the rear edge", page.evaluate(f"() => S.job.cabinets[S.sel].support_rows[{idx}].edges"), ["rear"])
    note = page.evaluate("() => [...document.querySelectorAll('#supportbox .supblock.isback p.drawn')].map((p) => p.textContent).join(' ')")
    check("  the note under it says it is kept as stored", "kept and" in note and "outer edge" in note, True)
    shot(page, "supports_noncanonical", "#supportbox")
    # give it an edging kind, then a count: the server's canonical set replaces it
    page.select_option(f'#supportbox select[data-sup="{idx}"][data-sk="kind"]', "pvc")
    computed(page)
    page.select_option(f'#supportbox select[data-sup="{idx}"][data-sk="long"]', "2")
    page.wait_for_function(f"() => JSON.stringify(S.job.cabinets[S.sel].support_rows[{idx}].edges) === '[\"front\",\"rear\"]'", timeout=5000)
    computed(page)
    check("Long 2 stores both long edges", page.evaluate(f"() => S.job.cabinets[S.sel].support_rows[{idx}].edges"), ["front", "rear"])
    page.select_option(f'#supportbox select[data-sup="{idx}"][data-sk="short"]', "1")
    page.wait_for_function(f"() => S.job.cabinets[S.sel].support_rows[{idx}].edges.length === 3", timeout=5000)
    computed(page)
    check("Short 1 adds the left end", page.evaluate(f"() => S.job.cabinets[S.sel].support_rows[{idx}].edges"), ["front", "rear", "left"])
    note = page.evaluate("() => [...document.querySelectorAll('#supportbox .supblock.isback p.drawn')].map((p) => p.textContent).join(' ')")
    check("  the not-canonical note is gone", "kept and" in note, False)
    ordered = page.evaluate(f"() => document.querySelector('#supportbox [data-suprow=\"{idx}\"]').textContent")
    check("Ordered as reads as a panel's line", ordered.endswith("on 2 long + 1 short edges"), True)
    page.select_option(f'#supportbox select[data-sup="{idx}"][data-sk="long"]', "1")
    page.wait_for_function(f"() => S.job.cabinets[S.sel].support_rows[{idx}].edges.length === 2", timeout=5000)
    computed(page)
    ordered = page.evaluate(f"() => document.querySelector('#supportbox [data-suprow=\"{idx}\"]').textContent")
    check("  and one of each: 'on 1 long + 1 short edges'", ordered.endswith("on 1 long + 1 short edges"), True)
    shot(page, "supports_counts", "#supportbox")
    check("no console errors", errors, [])
    ctx.close()
    browser.close()


def stage_catalogue(pw):
    print("\nPart 2 — Catalogue: Boards | Runners, and every jump that lands on Boards")
    browser = pw.chromium.launch(headless=not args.headed, args=LAUNCH)
    errors = []
    ctx, page = new_page(browser, errors)
    check("the app opens on Catalogue -> Boards",
          page.evaluate("() => [S.tab, S.catSub, !document.querySelector('#catboards').hidden]"),
          ["catalogue", "boards", True])
    check("the first tab reads Catalogue", page.evaluate("() => document.querySelector('nav button').textContent"), "Catalogue")
    check("  and there is no Boards tab any more", page.evaluate("() => !!document.querySelector('nav [data-tab=\"boards\"]')"), False)
    check("Boards is the board library, as it was", page.evaluate("() => !!document.querySelector('#boards table')"), True)
    page.click('#catsubs [data-catsub="runners"]')
    page.wait_for_selector("#runners table", timeout=10000)
    check("Runners shows the library with the Gelmar seed",
          page.evaluate("() => S.rlib.runners.map((r) => r.id)"), ["GELMAR45"])
    row = page.evaluate("() => document.querySelector('#runners tbody tr').textContent")
    check("  its lengths 300-600, 13.5 clearance, 45 high",
          all(x in row for x in ("300 · 350 · 400 · 450 · 500 · 550 · 600", "13.5", "45")), True)
    shot(page, "catalogue_runners")
    # New goes to Catalogue -> Boards, from Runners
    page.click("#new")
    page.wait_for_function("() => S.job.name === 'untitled' && S.tab === 'catalogue' && S.catSub === 'boards'", timeout=10000)
    check("New goes to Catalogue -> Boards", page.evaluate("() => [S.tab, S.catSub]"), ["catalogue", "boards"])
    # Add cabinet with no board selected: the refusal lands on Catalogue -> Boards
    page.evaluate("() => { S.catSub = 'runners'; showCatSub(); }")
    tab(page, "cabinets")
    page.click("#add")
    page.wait_for_function("() => S.tab === 'catalogue'", timeout=5000)
    check("Add cabinet with no board goes to Catalogue -> Boards", page.evaluate("() => [S.tab, S.catSub]"), ["catalogue", "boards"])
    # a board ticked, a cabinet added: it takes the Gelmar runner, copied in
    first = page.evaluate("() => S.lib.boards.find((b) => !b.thin).id")
    page.check(f'#boards [data-pick="{first}"]')
    page.wait_for_function(f"() => (S.res.boards || []).indexOf({json.dumps(first)}) >= 0", timeout=10000)
    tab(page, "cabinets")
    page.click("#add")
    page.wait_for_function("() => S.job.cabinets.length === 1", timeout=10000)
    computed(page)
    check("a new cabinet names the Gelmar runner", page.evaluate("() => S.job.cabinets[0].runner"), "GELMAR45")
    check("  and the project carries its copy, price captured",
          page.evaluate("() => Object.keys(S.job.runners)"), ["GELMAR45"])
    check("no console errors", errors, [])
    ctx.close()
    browser.close()


def stage_runners(pw):
    print("\nPart 2 — runners: tick in, the Drawers section, a swap that moves drawer lines, add / delete")
    browser = pw.chromium.launch(headless=not args.headed, args=LAUNCH)
    errors = []
    ctx, page = new_page(browser, errors)
    dialogs = []
    page.on("dialog", lambda d: dialogs.append(d.message))
    load_job(page, "Test")
    select(page, 4)
    page.wait_for_selector("#drawerbox select[data-runner]", timeout=5000)
    check("cabinet 4 (saved before the catalogue) is on the legacy runner",
          page.evaluate("() => document.querySelector('#drawerbox select[data-runner]').value"), "")
    read = text(page, "#drawerbox [data-runread]")
    check("  the readout is the engine's: 500 long, 70 behind", ("500" in read and "70 left behind" in read), True)
    openc = page.evaluate("() => { document.querySelector('#druncat').click(); return [S.tab, S.catSub]; }")
    check("Catalogue… in the Drawers section opens Catalogue -> Runners", openc, ["catalogue", "runners"])
    page.wait_for_selector('#runners [data-rpick="GELMAR45"]', timeout=10000)
    page.check('#runners [data-rpick="GELMAR45"]')
    page.wait_for_function("() => (S.res.runners || []).indexOf('GELMAR45') >= 0", timeout=10000)
    check("ticking copies the record into the project", page.evaluate("() => S.job.runners.GELMAR45.lengths"),
          [300, 350, 400, 450, 500, 550, 600])
    # make cabinet 7 shallower: legacy picks 350 there, Gelmar 400 — a real move
    page.evaluate("() => { const c = S.job.cabinets.find((x) => x.number === 7); c.depth = 460; }")
    computed(page)
    before = page.evaluate("() => S.res.panels.filter((p) => p.cabinet === 7 && p.role === 'Drawer Side').map((p) => p.length)")
    check("at 460 deep the legacy runner cuts 350 sides", before, [350] * len(before))
    dialogs.clear()
    page.click('#runners [data-rswap="GELMAR45"]')
    page.wait_for_function("() => S.job.cabinets.filter((c) => c.drawers.length && c.kind !== 'panel').every((c) => c.runner === 'GELMAR45')", timeout=10000)
    computed(page)
    check("Use for all drawers asked first, naming the lines that move",
          bool(dialogs) and "350 x" in dialogs[0] and "400 x" in dialogs[0], True)
    after = page.evaluate("() => S.res.panels.filter((p) => p.cabinet === 7 && p.role === 'Drawer Side').map((p) => p.length)")
    check("  and cabinet 7's sides are 400 now", after, [400] * len(after))
    four = page.evaluate("() => S.res.panels.filter((p) => p.cabinet === 4 && p.role === 'Drawer Side').map((p) => p.length)")
    check("  cabinet 4 at 570 deep is 500 either way", four, [500] * len(four))
    shot(page, "runners_in_project")
    # a runner added in the library, then deleted (it names no saved job)
    page.click("#rnew")
    page.fill("#rf-name", "Check runner")
    page.fill("#rf-lengths", "300, 400 350")
    page.click("#rf-save")
    page.wait_for_function("() => S.rlib && S.rlib.runners.some((r) => r.id === 'CHECKRUNNER')", timeout=10000)
    check("Add runner saves it, lengths cleaned and sorted",
          page.evaluate("() => S.rlib.runners.find((r) => r.id === 'CHECKRUNNER').lengths"), [300, 350, 400])
    page.click('#runners [data-rdel="CHECKRUNNER"]')
    page.wait_for_function("() => S.rlib && !S.rlib.runners.some((r) => r.id === 'CHECKRUNNER')", timeout=10000)
    check("  and Del takes it out again", True, True)
    # the per-cabinet control: back onto nothing but GELMAR45 is offered
    select(page, 7)
    page.wait_for_selector("#drawerbox select[data-runner]", timeout=5000)
    opts = page.evaluate("() => [...document.querySelectorAll('#drawerbox select[data-runner] option')].map((o) => o.value)")
    check("the Drawers section offers the project's runners, and not legacy", opts, ["GELMAR45"])
    check("no console errors", errors, [])
    ctx.close()
    browser.close()


def stage_drawers(pw):
    print("\nPart 4 — inner drawers: the type, the count, a height typed on its own")
    browser = pw.chromium.launch(headless=not args.headed, args=LAUNCH)
    errors = []
    ctx, page = new_page(browser, errors)
    load_job(page, "Test")
    select(page, 1)                                    # tall, a pair of doors, no drawers
    page.wait_for_selector('#editor [data-tick="has_drawers"]', timeout=5000)
    page.check('#editor [data-tick="has_drawers"]')
    page.wait_for_selector("#drawerbox select[data-dtype]", timeout=5000)
    page.select_option("#drawerbox select[data-dtype]", "inner")
    page.wait_for_function("() => S.job.cabinets[S.sel].drawers.length === 1 && S.job.cabinets[S.sel].drawers[0].inner", timeout=10000)
    computed(page)
    check("Inner with no drawers yet: one, on the bottom (21)",
          page.evaluate("() => S.job.cabinets[S.sel].drawers.map((d) => d.z)"), [21])
    page.fill("#drawerbox input[data-dcount]", "3")
    page.dispatch_event("#drawerbox input[data-dcount]", "change")
    page.wait_for_function("() => S.job.cabinets[S.sel].drawers.length === 3", timeout=10000)
    computed(page)
    check("three: equally spaced from the bottom (inside 2368 / 3)",
          page.evaluate("() => S.job.cabinets[S.sel].drawers.map((d) => d.z)"), [1600, 810, 21])
    page.fill('#drawerbox input[data-d="0"][data-dk="z"]', "1500")
    page.dispatch_event('#drawerbox input[data-d="0"][data-dk="z"]', "change")
    computed(page)
    check("drawer 1 typed to 1500 on its own; the others stay",
          page.evaluate("() => S.job.cabinets[S.sel].drawers.map((d) => d.z)"), [1500, 810, 21])
    faces = page.evaluate("() => S.res.panels.filter((p) => p.cabinet === 1 && p.role === 'Drawer Face').map((p) => [p.length, p.width, p.qty])")
    check("the cut list: one inner face line, the box's size (150 x 541)", faces, [[150, 541, 3]])
    read = text(page, '#drawerbox [data-innerread="0"]')
    check("the row reads the engine's face and box top", read.strip(), "541×150top 1650")
    shot(page, "inner_drawers", "#drawerbox")
    page.fill("#drawerbox input[data-dcount]", "2")
    page.dispatch_event("#drawerbox input[data-dcount]", "change")
    page.wait_for_function("() => S.job.cabinets[S.sel].drawers.length === 2", timeout=10000)
    computed(page)
    check("a count change puts the typed height back on the spacing",
          page.evaluate("() => S.job.cabinets[S.sel].drawers.map((d) => d.z)"), [1205, 21])
    check("no inner-drawer critical on it (it has doors)",
          page.evaluate("() => S.res.issues.filter((i) => i.where === '1' && /drawer-inner/.test(i.check)).length"), 0)
    page.select_option("#drawerbox select[data-dtype]", "outer")
    page.wait_for_function("() => !S.job.cabinets[S.sel].drawers.some((d) => d.inner)", timeout=10000)
    computed(page)
    check("back to Outer: the face stack table, no inner height left",
          page.evaluate("() => [!!document.querySelector('#drawerbox [data-dk=\"mode\"]'), S.job.cabinets[S.sel].drawers.some((d) => 'z' in d && d.z !== null)]"),
          [True, False])
    check("no console errors", errors, [])
    ctx.close()
    browser.close()


def cab3d_ready(page, number):
    page.wait_for_function("() => typeof V3C === 'object' && V3C !== null", timeout=30000)
    page.wait_for_function(f"() => !S.cabSceneStale && cabTimer === null && S.cab3dShown === {number}", timeout=20000)
    page.wait_for_function("() => V3C.idle()", timeout=10000)
    time.sleep(0.2)


def stage_3d(pw):
    print("\nPart 6 — drawer boxes and runners in the Cabinets tab's 3D; fronts open slides them out")
    browser = pw.chromium.launch(headless=not args.headed, args=LAUNCH)
    errors = []
    ctx, page = new_page(browser, errors)
    load_job(page, "Test")
    select(page, 4)                                     # four drawers, legacy runner, 570 deep
    cab3d_ready(page, 4)
    ids = ["4:drawer:3", "4:drawer_side:0", "4:drawer_front:0", "4:drawer_back:0", "4:drawer_base:0", "4:runner:0"]
    info = {i: page.evaluate(f"() => V3C.partInfo({json.dumps(i)})") for i in ids}
    check("every box part and a runner are drawn", [bool(v and v["visible"]) for v in info.values()], [True] * len(ids))
    check("  the legend no longer says drawer boxes are not drawn",
          "drawer boxes" in page.evaluate("() => document.querySelector('#cab3d').textContent"), False)
    shot(page, "cab3d_drawers_closed", "#cab3d")
    page.click("#c3dbar button:has-text('Fronts')")
    page.wait_for_function("() => V3C.state().fronts === true", timeout=5000)
    page.wait_for_function("() => V3C.idle()", timeout=10000)
    time.sleep(0.6)
    moved = {}
    for i in ids:
        v = page.evaluate(f"() => V3C.partInfo({json.dumps(i)})")
        rest, now = v["rest"]
        moved[i] = round(sum((a - b) ** 2 for a, b in zip(now, rest)) ** 0.5)
    check("Fronts: the face and the whole box slide out together, the runner's travel (500)",
          [moved[i] for i in ids[:5]], [500] * 5)
    check("  the runner stays where it is", moved["4:runner:0"], 0)
    shot(page, "cab3d_drawers_open", "#cab3d")
    page.click("#c3dbar button:has-text('Runners')")
    page.wait_for_function("() => V3C.state().runners === false", timeout=5000)
    check("the Runners toggle hides the runners, and only them",
          (page.evaluate("() => V3C.partInfo('4:runner:0').visible"),
           page.evaluate("() => V3C.partInfo('4:drawer_side:0').visible")), (False, True))
    check("no console errors", errors, [])
    ctx.close()
    browser.close()


def stage_offset(pw):
    print("\nfaces lead, boxes follow — the Offset column and the tallest box (ruled 28 Sept)")
    browser = pw.chromium.launch(headless=not args.headed, args=LAUNCH)
    errors = []
    ctx, page = new_page(browser, errors)
    load_job(page, "Test")
    select(page, 4)                          # faces 110 / 165 / 220 / 276, boxes 90 / 150 / 200 / 240
    page.wait_for_selector('#drawerbox input[data-dk="offset"]', timeout=5000)
    check("an Offset cell per drawer, blank = the default 21",
          page.evaluate("() => [...document.querySelectorAll('#drawerbox input[data-dk=\"offset\"]')].map((x) => [x.value, x.placeholder])"),
          [["", "21"]] * 4)
    maxes = page.evaluate("() => [...document.querySelectorAll('#drawerbox [data-maxbox]')].map((x) => x.textContent)")
    check("beside each Box h, the tallest box its face takes: face less 21", maxes, ["≤89", "≤144", "≤199", "≤255"])
    crit = lambda cid: page.evaluate(f"() => S.res.issues.filter((i) => i.where === '4' && i.check === {json.dumps(cid)}).length")
    check("at the defaults, drawers 1-3 are outside their faces (Test.json not edited)", crit("drawer-box-face"), 3)
    page.fill('#drawerbox input[data-d="1"][data-dk="box_height"]', "144")
    page.dispatch_event('#drawerbox input[data-d="1"][data-dk="box_height"]', "change")
    computed(page)
    check("drawer 2's box down to its 144: one fewer outside its face", crit("drawer-box-face"), 2)
    page.fill('#drawerbox input[data-d="3"][data-dk="offset"]', "15")
    page.dispatch_event('#drawerbox input[data-d="3"][data-dk="offset"]', "change")
    computed(page)
    check("the bottom drawer's offset to 15: drawer-bottom-offset", crit("drawer-bottom-offset"), 1)
    check("  and its tallest box reads 276 - 15 = 261",
          page.evaluate("() => document.querySelector('#drawerbox [data-maxbox=\"3\"]').textContent"), "≤261")
    page.fill('#drawerbox input[data-d="3"][data-dk="offset"]', "")
    page.dispatch_event('#drawerbox input[data-d="3"][data-dk="offset"]', "change")
    computed(page)
    check("cleared, it is the default again (stored as nothing)",
          (page.evaluate("() => S.job.cabinets[S.sel].drawers[3].offset"), crit("drawer-bottom-offset")), (None, 0))
    shot(page, "drawer_offsets", "#drawerbox")
    check("no console errors", errors, [])
    ctx.close()
    browser.close()


STAGES = {"supports": stage_supports, "catalogue": stage_catalogue, "runners": stage_runners,
          "drawers": stage_drawers, "3d": stage_3d, "offset": stage_offset}

with sync_playwright() as pw:
    for key, fn in STAGES.items():
        if args.stage in ("all", key):
            fn(pw)

print(f"\nui_check_drawers: {'all good' if not FAILS else str(len(FAILS)) + ' FAILED: ' + str(FAILS)}")
sys.exit(1 if FAILS else 0)
