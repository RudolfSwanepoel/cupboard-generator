"""Import project and the project Rename in the running app (brief of 3 October
2026), with a real mouse (Playwright, optional).

    python tools/ui_check_import.py [--port N] [--stage import|rename|shipped]

Unlike the other ui_check scripts this one STARTS ITS OWN APP: Import writes
jobs, boards, runners and pictures, and a check never writes live workshop
data. So it copies the app (app/, cabinetgen/, run_app.py, the libraries and
Pictures/) into a temp folder with tools/fixtures/Test_export.json as its
Test.json, runs `run_app.py --no-window` there on its own port, and builds the
old demo folder `check_import.py` builds beside it. Everything is deleted
afterwards.

Stages:
  import  Import project with a typed path (the native folder dialog cannot be
          driven headless, and under --no-window there is none: the dialog
          says so and asks for the path): a folder that is not an app folder
          refused, the preview, nothing written by it, Import, the report, the
          renamed job in the list and opened, the renamed board on
          Catalogue -> Boards.
  rename  The project Rename beside the job name: a taken name (any case)
          refused under the field and nothing written; a free name moves the
          file and the output folder, and the job on screen follows; Save onto
          another job's name refused.
  shipped A demo whose jobs\\shipped-jobs.json lists the jobs it shipped with:
          the preview shows each as a `shipped` row, left out, and the
          friend's own job as new (follow-up brief, 3 October 2026).

Screenshots into output/_checks/ui_check_import/.
Playwright is the only third-party package anywhere near this app and only the
ui_check scripts need it; without it this says so and exits 0.
"""
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

try:
    from playwright.sync_api import sync_playwright
except ImportError:                                            # pragma: no cover
    print("playwright is not installed — skipping the browser check (pip install playwright)")
    sys.exit(0)

import check_import as CI                                      # noqa: E402  (the old folder)

ap = argparse.ArgumentParser()
ap.add_argument("--port", type=int, default=0, help="default: a free one")
ap.add_argument("--stage", default="", help="import | rename | shipped (default: all)")
ap.add_argument("--headed", action="store_true")
args = ap.parse_args()
if not args.port:
    # a port nothing holds — not even a socket of our own last run in TIME_WAIT,
    # which run_app's exclusive bind refuses
    import socket
    with socket.socket() as _s:
        _s.bind(("127.0.0.1", 0))
        args.port = _s.getsockname()[1]
URL = f"http://127.0.0.1:{args.port}/"
SHOTS = os.path.join(ROOT, "output", "_checks", "ui_check_import")

FAILS = []


def check(label, got, want):
    ok = got == want
    print(f"  {'ok  ' if ok else 'FAIL'}  {label}: {got!r}" + ("" if ok else f"  (wanted {want!r})"))
    if not ok:
        FAILS.append(label)
    return ok


def tree(folder):
    out = {}
    for base, _d, files in os.walk(folder):
        if "__pycache__" in base:
            continue
        for n in files:
            p = os.path.join(base, n)
            with open(p, "rb") as fh:
                out[os.path.relpath(p, folder)] = hashlib.sha1(fh.read()).hexdigest()
    return out


def shot(page, name):
    os.makedirs(SHOTS, exist_ok=True)
    page.screenshot(path=os.path.join(SHOTS, name + ".png"))


def settle(page):
    """The compute a typed name scheduled, run now and awaited."""
    time.sleep(0.3)
    page.evaluate("async () => { clearTimeout(computeTimer); computeTimer = null; await compute(); }")


def make_app(top):
    """A copy of the app to run, with its own jobs, libraries and pictures."""
    here = os.path.join(top, "App")
    ign = shutil.ignore_patterns("__pycache__", "_demo_build.py")
    for d in ("app", "cabinetgen"):
        shutil.copytree(os.path.join(ROOT, d), os.path.join(here, d), ignore=ign)
    for f in ("run_app.py", "boards.json", "hardware.json", "cupboards.json"):
        shutil.copyfile(os.path.join(ROOT, f), os.path.join(here, f))
    shutil.copytree(os.path.join(ROOT, "Pictures"), os.path.join(here, "Pictures"))
    os.makedirs(os.path.join(here, "jobs"))
    for f in ("__init__.py", "wardrobe_oct2025.py"):
        shutil.copyfile(os.path.join(ROOT, "jobs", f), os.path.join(here, "jobs", f))
    shutil.copyfile(os.path.join(ROOT, "tools", "fixtures", "Test_export.json"),
                    os.path.join(here, "jobs", "Test.json"))
    shutil.copyfile(os.path.join(ROOT, "tools", "fixtures", "Test_Build.json"),
                    os.path.join(here, "jobs", "Main.json"))
    shutil.copyfile(os.path.join(CI.make_here(os.path.join(top, "ref")), "jobs", "Shared.json"),
                    os.path.join(here, "jobs", "Shared.json"))
    return here


def start(here):
    log = open(os.path.join(os.path.dirname(here), "app.log"), "w+")
    proc = subprocess.Popen([sys.executable, "run_app.py", "--no-window", "--port", str(args.port)],
                            cwd=here, stdout=log, stderr=subprocess.STDOUT)
    for _ in range(150):
        try:
            urllib.request.urlopen(URL, timeout=1).read()
            return proc
        except OSError:
            time.sleep(0.1)
    proc.kill()
    log.seek(0)
    raise SystemExit(f"the copy of the app did not start on port {args.port}:\n{log.read()}")


def stage_import(page, here, top, outer, app):
    print("\nImport project: typed path, preview, Import, report")
    page.click("#importproj")
    page.wait_for_selector("#importdlg[open] #importpath", timeout=5000)
    check("no window: the dialog says there is no folder picker and asks for the path",
          "no folder picker" in page.inner_text("#importbody"), True)
    plain = os.path.join(top, "Holiday photos")
    os.makedirs(plain, exist_ok=True)
    page.fill("#importpath", plain)
    page.click("#importlook")
    page.wait_for_function("() => $('importerr') && $('importerr').textContent.length > 0", timeout=5000)
    err = page.inner_text("#importerr")
    check("a folder that is not an app folder: says what it looked for",
          all(w in err for w in ("jobs\\", "readable job", "Cupboard App Demo.exe")), True)

    before_here, before_old = tree(here), tree(outer)
    page.fill("#importpath", outer)
    page.keyboard.press("Enter")
    page.wait_for_selector("#importdlg #importgo", timeout=10000)
    shot(page, "import_preview")
    rows = page.evaluate("() => [...document.querySelectorAll('#importdlg [data-impitem]')]"
                         ".map((r) => [r.dataset.impitem, r.children[2].textContent.trim()])")
    got = dict(rows)
    check("the preview lists every item", len(rows), 17)
    check("  Test: a name taken here, comes in renamed",
          got.get("job:Test"), "name taken here — comes in as Test (imported)")
    check("  Shared: identical, skipped", got.get("job:Shared"), "identical — skipped")
    check("  Broken: will not load", got.get("job:Broken"), "will not load — not imported")
    check("  the board GREY: renamed",
          got.get("board:STORMGREY"), "name taken here — comes in as STORMGREY (imported)")
    check("the preview wrote nothing here", tree(here) == before_here, True)
    check("  and nothing in the old folder", tree(outer) == before_old, True)

    page.click("#importgo")
    page.wait_for_selector("#importdlg #importreport", timeout=15000)
    rep = page.input_value("#importreport")
    shot(page, "import_report")
    check("the report", rep.split("\n")[0].startswith(
        "Imported 4 projects, 3 boards, 2 runners, 2 pictures. Skipped 5 identical. "
        "Renamed: Test → Test (imported), STORMGREY → STORMGREY (imported)"), True)
    check("  it names the job that would not load", "Not imported: Broken.json" in rep, True)
    page.click("#importdlg [data-imp='copy']")
    check("  Copy says so", page.inner_text("#toast").startswith("Report copied"), True)
    check("the old folder is unchanged", tree(outer) == before_old, True)
    page.click("#importdlg [data-imp='cancel']")

    jobs = page.evaluate("() => [...$('joblist').options].map((o) => o.value)")
    check("the renamed job is in the job list", "Test (imported).json" in jobs, True)
    page.select_option("#joblist", "Test (imported).json")
    page.click("#load")
    page.wait_for_function("() => S.job && S.job.name === 'Test (imported)'", timeout=10000)
    check("opened, it is shown under its new name", page.input_value("#jobname"), "Test (imported)")
    boards = page.evaluate("() => Object.values(S.job.materials).map((m) => m.name)")
    check("  and its board is the imported one", "STORMGREY (imported)" in boards, True)
    page.click('nav [data-tab="catalogue"]')
    page.wait_for_function("() => S.lib && S.lib.boards", timeout=10000)
    check("Catalogue -> Boards lists the imported board",
          "STORMGREY (imported)" in page.inner_text("#boards"), True)
    shot(page, "import_boards")


def stage_shipped(page, top):
    """Follow-up ruling 2: a demo that lists the jobs it shipped with previews
    them as `shipped` — left out — and its owner's own job as new."""
    print("\nImport project: a demo's shipped jobs are left out")
    souter, _ = CI.make_demo(top, "Demo with list", ["Test.json", "Demo Kitchen.json"])
    page.click("#importproj")
    page.wait_for_selector("#importdlg[open] #importpath", timeout=5000)
    page.fill("#importpath", souter)
    page.keyboard.press("Enter")
    page.wait_for_selector("#importdlg #importgo", timeout=10000)
    shot(page, "import_shipped")
    rows = dict(page.evaluate("() => [...document.querySelectorAll('#importdlg [data-impitem]')]"
                              ".map((r) => [r.dataset.impitem, [r.children[2].className, "
                              "r.children[2].textContent.trim()]])"))
    check("a demo's shipped jobs: a shipped row each in the preview",
          [rows.get("job:Test"), rows.get("job:Demo Kitchen")],
          [["act-shipped", "shipped with the demo — left out"]] * 2)
    check("  the friend's own job comes in", rows.get("job:Mine"), ["act-new", "new — comes in"])
    check("  the summary counts them",
          "2 shipped with the demo left out" in page.inner_text("#importbody"), True)
    page.click("#importdlg [data-imp='cancel']")


def stage_rename(page, here):
    print("\nRename: the project, Save onto another's name, a picture, a board")
    if not page.evaluate("() => S.file"):
        page.select_option("#joblist", "Test.json")
        page.click("#load")
        page.wait_for_function("() => S.file === 'Test.json'", timeout=10000)
    page.click('nav [data-tab="cabinets"]')
    old = page.evaluate("() => S.file")
    safe = page.evaluate("() => S.job.name").replace(" ", "_").replace("(", "_").replace(")", "_")
    snap = os.path.join(here, "output", safe, "snapshots", f"{safe}_3d_1.png")
    os.makedirs(os.path.dirname(snap), exist_ok=True)
    with open(snap, "wb") as fh:
        fh.write(b"\x89PNG snapshot")
    before = tree(here)

    page.click("#jobrename")
    page.wait_for_selector("#renamedlg[open]", timeout=5000)
    page.fill("#renameto", "main")
    page.click("#renamego")
    page.wait_for_function("() => $('renamemsg').textContent.length > 0", timeout=5000)
    check("a taken name (another case) is refused under the field",
          page.inner_text("#renamemsg"), "main already exists — choose another name")
    check("  the dialog stays open", page.evaluate("() => $('renamedlg').open"), True)
    check("  nothing is written", tree(here) == before, True)
    shot(page, "rename_taken")
    page.fill("#renameto", "Kitchen 2")
    page.keyboard.press("Enter")
    page.wait_for_function("() => !$('renamedlg').open", timeout=5000)
    check("renamed: the job on screen follows",
          page.evaluate("() => [S.file, S.job.name, $('jobname').value]"),
          ["Kitchen 2.json", "Kitchen 2", "Kitchen 2"])
    jobs = page.evaluate("() => [...$('joblist').options].map((o) => o.value)")
    check("  the job list refreshes", ("Kitchen 2.json" in jobs, old in jobs), (True, False))
    check("  the file is moved, not copied",
          (os.path.exists(os.path.join(here, "jobs", "Kitchen 2.json")),
           os.path.exists(os.path.join(here, "jobs", old))), (True, False))
    check("  the output folder and its files follow",
          os.path.exists(os.path.join(here, "output", "Kitchen_2", "snapshots", "Kitchen_2_3d_1.png")),
          True)
    check("  not unsaved by it", page.evaluate("() => S.dirty"), False)

    before = tree(here)
    page.fill("#jobname", "MAIN")
    page.click("#save")
    page.wait_for_function("() => !$('jobnamemsg').hidden", timeout=5000)
    check("Save onto another job's name is refused under the name",
          page.inner_text("#jobnamemsg"), "MAIN already exists — choose another name")
    check("  nothing is written", tree(here) == before, True)
    shot(page, "save_taken")
    page.fill("#jobname", "Kitchen 2")
    check("  typing clears it", page.evaluate("() => $('jobnamemsg').hidden"), True)
    page.click("#save")
    page.wait_for_function("() => !S.dirty", timeout=5000)
    check("  saving under its own name is as ever", page.evaluate("() => S.file"), "Kitchen 2.json")

    # the board on screen pictured in Storm Grey (GREY, or the imported one)
    bid = page.evaluate("() => Object.entries(S.job.materials).find(([k, m]) => "
                        "m && m.picture && m.picture.indexOf('Storm') >= 0)[0]")
    page.click('nav [data-tab="catalogue"]')
    page.wait_for_function("() => S.lib && S.lib.boards", timeout=10000)
    settle(page)             # a compute repaints the Boards tab, editor and all
    page.click(f'[data-bedit="{bid}"]')
    pic = page.input_value("#bf-picture")
    page.wait_for_selector("#bf-picrename:not([hidden])", timeout=5000)
    page.click("#bf-picrename")
    page.fill("#bf-picrenameto", "cascade grey")
    page.click("#bf-picrenamego")
    page.wait_for_function("() => $('bf-picrenamemsg').textContent.length > 0", timeout=5000)
    check("a picture renamed to a taken name is refused under the field",
          page.inner_text("#bf-picrenamemsg"), "cascade grey.jpg already exists — choose another name")
    page.fill("#bf-picrenameto", "Storm 2")
    page.click("#bf-picrenamego")
    page.wait_for_function("() => $('bf-picture').value === 'Pictures/Storm 2.jpg'", timeout=5000)
    check("  a free name renames the file",
          (os.path.exists(os.path.join(here, "Pictures", "Storm 2.jpg")),
           os.path.exists(os.path.join(here, *pic.split("/")))), (True, False))
    check("  and the project on screen follows",
          page.evaluate(f"() => S.job.materials['{bid}'].picture"), "Pictures/Storm 2.jpg")
    page.fill("#bf-name", "cascade GREY")
    page.click("#bf-save")
    page.wait_for_function("() => $('bf-namemsg') && $('bf-namemsg').textContent.length > 0",
                           timeout=5000)
    check("a board renamed to a taken name is refused under the field",
          page.inner_text("#bf-namemsg"), "cascade GREY already exists — choose another name")
    shot(page, "board_taken")


def stage_catalogue(page, here):
    """Ruling 9 of the cabinet round (3 October 2026), in this copy of the app
    (its own cupboards.json, never the live one): Add to catalogue from the
    cupboard editor (the generated prefix fixed, the text typed, a taken name
    refused under the field), the record on Catalogue -> Cupboards with its
    preview, Place from catalogue into a project that lacks one of its boards
    — the mapping dialog, defaulted — and the copy landing unplaced with the
    next free number."""
    print("\nCatalogue: add, see it on Catalogue -> Cupboards, place it, map a board")
    page.select_option("#joblist", "Test.json")
    page.click("#load")
    page.wait_for_function("() => S.file === 'Test.json' && S.res", timeout=15000)
    page.click('nav [data-tab="cabinets"]')
    # a cupboard that names GREY, which Main.json (Test_Build) does not carry
    num = page.evaluate("() => (S.job.cabinets.find((c) => c.kind !== 'panel' && (c.door_boards || []).includes('GREY')) || S.job.cabinets.find((c) => c.kind !== 'panel' && c.exterior_board === 'GREY') || {}).number")
    check(f"Test.json has a cupboard on the GREY board [{num}]", bool(num), True)
    page.evaluate(f"() => {{ selectCabinet(S.job.cabinets.findIndex((c) => c.number === {num})); renderList(); }}")
    page.wait_for_selector("#editor #edcat", timeout=10000)
    page.click("#editor #edcat")
    page.wait_for_selector("#cataddlg[open]", timeout=5000)
    prefix = page.inner_text("#cataddprefix")
    size = page.evaluate(f"() => {{ const c = S.job.cabinets.find((c) => c.number === {num}); return `${{c.width}}×${{c.height}}×${{c.depth}}`; }}")
    check(f"the generated prefix is shown, fixed: <Kind> W×H×D [{prefix}]", bool(prefix.endswith(size) and prefix[0].isupper()), True)
    page.fill("#cataddauthor", "Rudolf")
    page.fill("#cataddtext", "grey doors")
    page.click("#cataddgo")
    page.wait_for_function("() => !$('cataddlg').open", timeout=10000)
    cat = os.path.join(here, "cupboards.json")
    with open(cat, encoding="utf-8") as fh:
        recs = json.load(fh)["cupboards"]
    check("the record is in this copy's cupboards.json, named prefix + text", [r["name"] for r in recs], [prefix + " grey doors"])
    check("  by its author, without the number", (recs[0]["author"], recs[0]["cabinet"]["number"]), ("Rudolf", 0))
    # the same name again, another case: refused under the field, nothing written
    page.click("#editor #edcat")
    page.wait_for_selector("#cataddlg[open]", timeout=5000)
    page.fill("#cataddtext", "GREY DOORS")
    page.click("#cataddgo")
    page.wait_for_function("() => $('cataddmsg').textContent.length > 0", timeout=5000)
    check("a taken name (another case) is refused under the field",
          page.inner_text("#cataddmsg"), f"{prefix} GREY DOORS already exists — choose another name")
    check("  the dialog stays open", page.evaluate("() => $('cataddlg').open"), True)
    with open(cat, encoding="utf-8") as fh:
        check("  nothing was written", len(json.load(fh)["cupboards"]), 1)
    shot(page, "catalogue_add_taken")
    page.click("#cataddcancel")
    # on Catalogue -> Cupboards, with its preview
    page.evaluate("() => openCatalogue('cupboards')")
    page.wait_for_selector("#cattable [data-catrow]", timeout=15000)
    rows = page.evaluate("() => [...document.querySelectorAll('#cattable [data-catrow]')].map((r) => r.dataset.catrow)")
    check("Catalogue -> Cupboards lists it", rows, [prefix + " grey doors"])
    page.click("#cattable [data-catrow]")
    page.wait_for_function("() => typeof V3K === 'object' && V3K !== null && V3K.groupIds && Object.keys(V3K.groupIds()).length > 0", timeout=30000)
    check("clicking it draws the preview in its own 3D view", page.evaluate("() => Object.keys(V3K.groupIds()).length > 0"), True)
    shot(page, "catalogue_cupboards")
    # place it into Main.json (Test_Build), which lacks GREY: the mapping dialog
    page.select_option("#joblist", "Main.json")
    page.click("#load")
    page.wait_for_function("() => S.file === 'Main.json' && S.res", timeout=15000)
    page.click('nav [data-tab="cabinets"]')
    n_before = page.evaluate("() => S.job.cabinets.length")
    check("Main.json does not carry GREY", page.evaluate("() => S.job.boards.includes('GREY')"), False)
    page.click("#placecat")
    page.wait_for_selector("#catpickdlg[open]", timeout=5000)
    page.click("#catpickgo")
    page.wait_for_selector("#catmapdlg[open]", timeout=10000)
    sel = page.evaluate("() => [...document.querySelectorAll('#catmaplist [data-catmap=\"board\"]')].map((s) => [s.dataset.id, s.value, s.options.length])")
    check(f"the mapping dialog asks for GREY, defaulted to a project board of the same thickness [{sel}]",
          bool(sel and sel[0][0] == "GREY" and sel[0][1] in ("BROOKHILL", "MEL", "WHITEMEL")), True)
    shot(page, "catalogue_map")
    page.click("#catmapgo")
    page.wait_for_function(f"() => S.job.cabinets.length > {n_before}", timeout=15000)
    new = page.evaluate(f"() => S.job.cabinets[{n_before}]")          # the head; its attached panel follows it
    nums = page.evaluate("() => S.job.cabinets.map((c) => c.number)")
    check("placed: the next free number, unplaced",
          (nums.count(new["number"]), page.evaluate(f"() => S.job.placements.some((p) => p.cabinet === {new['number']})")), (1, False))
    tail = page.evaluate(f"() => S.job.cabinets.slice({n_before}).map((c) => [c.kind, c.panel ? c.panel.attached_to : null])")
    check("  its attached panel came with it, attached to the copy", tail[1:], [["panel", new["number"]]] if len(tail) > 1 else [])
    check("  the copy names the mapped board and no GREY",
          ("GREY" in json.dumps(new), new["door_boards"] and new["door_boards"][0] in ("BROOKHILL", "MEL", "WHITEMEL") or new["exterior_board"] in ("BROOKHILL", "MEL", "WHITEMEL")),
          (False, True))
    check("  it is selected and in the editor", page.evaluate(f"() => S.job.cabinets[S.sel].number"), new["number"])
    check("  the catalogue file is unchanged by placing", len(json.load(open(cat, encoding="utf-8"))["cupboards"]), 1)


def main() -> int:
    top = tempfile.mkdtemp(prefix="ui_check_import_")
    proc = None
    try:
        here = make_app(top)
        outer, app = CI.make_old(top)
        proc = start(here)
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=not args.headed)
            page = browser.new_page(viewport={"width": 1500, "height": 1000})
            errors = []
            page.on("pageerror", lambda e: errors.append(str(e)))
            page.on("dialog", lambda d: d.accept())
            page.goto(URL)
            page.wait_for_function("() => S.def !== null && S.res", timeout=15000)
            if args.stage in ("", "import"):
                stage_import(page, here, top, outer, app)
            if args.stage in ("", "rename"):
                stage_rename(page, here)
            if args.stage in ("", "shipped"):
                stage_shipped(page, top)
            if args.stage in ("", "catalogue"):
                stage_catalogue(page, here)
            check("no script errors in the page", errors, [])
            browser.close()
    finally:
        if proc is not None:
            proc.terminate()
            proc.wait(timeout=10)
        shutil.rmtree(top, ignore_errors=True)
    print(f"\n{len(FAILS)} failed" if FAILS else "\nall passed")
    return 1 if FAILS else 0


if __name__ == "__main__":
    raise SystemExit(main())
