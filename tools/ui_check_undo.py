"""Undo and Redo in the running app (room touch-ups round 2, 3 October 2026),
with a real mouse (Playwright, optional).

    python run_app.py --no-window --port 8766      # in another window
    python tools/ui_check_undo.py [--port 8766]

Four edits of four kinds — a cabinet dragged in the plan, a wall's length typed
in the Room card, a cabinet deleted, a drawer face changed — then Undo each in
turn back to the job as loaded (the job's JSON compared at every step), Redo
them all forward, a new edit clearing Redo; one step per edit, never per
keystroke; Ctrl+Z / Ctrl+Y, and Ctrl+Z inside a text field left to the field;
the unsaved marker on an undo, and off again back at the loaded job. The job
is built in the page from tools/fixtures/Test_3d.json (`adopt`), never loaded
from jobs/ and never saved.

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
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

try:
    from playwright.sync_api import sync_playwright
except ImportError:                                            # pragma: no cover
    print("playwright is not installed — skipping the browser check (pip install playwright)")
    sys.exit(0)

ap = argparse.ArgumentParser()
ap.add_argument("--port", type=int, default=8766)
ap.add_argument("--headed", action="store_true")
args = ap.parse_args()
URL = f"http://127.0.0.1:{args.port}/"
SHOTS = os.path.join(ROOT, "output", "_checks", "ui_check_undo")
LAUNCH = ["--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist"]

FAILS = []


def check(label, got, want):
    ok = got == want
    print(f"  {'ok  ' if ok else 'FAIL'}  {label}: {got!r}" + ("" if ok else f"  (wanted {want!r})"))
    if not ok:
        FAILS.append(label)
    return ok


def computed(page):
    """The compute the last edit scheduled, run now and awaited."""
    time.sleep(0.3)
    page.evaluate("async () => { clearTimeout(computeTimer); computeTimer = null; await compute(); "
                  "if (S.tab === 'room' && S.roomSub === 'plan') await renderPlan(); }")
    time.sleep(0.4)          # a drawer stack re-solves after the paint
    page.evaluate("async () => { clearTimeout(computeTimer); computeTimer = null; await compute(); }")


def key(page):
    return page.evaluate("() => undoKey()")


def state(page):
    return page.evaluate("() => [S.undo.length, S.redo.length, !$('undo').disabled, !$('redo').disabled, S.dirty]")


def main() -> int:
    with open(os.path.join(ROOT, "tools", "fixtures", "Test_3d.json"), encoding="utf-8") as f:
        job = json.load(f)
    job["name"] = "undo-check"
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=not args.headed, args=LAUNCH)
        page = browser.new_page(viewport={"width": 1500, "height": 1000})
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.on("dialog", lambda d: d.accept())
        page.goto(URL)
        page.wait_for_function("() => S.def !== null && S.res", timeout=15000)
        page.evaluate("(j) => adopt(j)", job)
        page.wait_for_function("() => S.job && S.job.name === 'undo-check'", timeout=15000)
        computed(page)
        print("\nUndo and Redo: the buttons, the history, the four kinds of edit")
        check("the buttons sit beside Save, both off with nothing to undo",
              page.evaluate("() => [$('save').nextElementSibling.id, $('undo').nextElementSibling.id, "
                            "$('undo').disabled, $('redo').disabled]"), ["undo", "redo", True, True])
        check("  the tooltip says what is not undone",
              all(w in page.get_attribute("#undo", "title") for w in
                  ("Save", "Load", "New", "Delete project", "Export", "snapshots", "Boards / Runners", "pictures")), True)
        j0 = key(page)
        check("loaded: no history, not unsaved", state(page), [0, 0, False, False, False])

        # 1. a cabinet dragged in the plan
        page.click('nav [data-tab="room"]')
        page.wait_for_function("() => S.tab === 'room' && document.querySelector('#plan svg')", timeout=10000)
        computed(page)
        x0 = page.evaluate("() => S.job.placements.find((p) => p.cabinet === 2).x")
        box = page.locator('#plan svg [data-cab="2"]').first.bounding_box()
        cx, cy = box["x"] + box["width"] / 2, box["y"] + box["height"] / 2
        page.mouse.move(cx, cy)
        page.mouse.down()
        for k in range(1, 11):
            page.mouse.move(cx - 6 * k, cy)
            time.sleep(0.03)
        page.mouse.up()
        page.wait_for_function(f"() => S.job.placements.find((p) => p.cabinet === 2).x !== {x0}", timeout=10000)
        computed(page)
        j1 = key(page)
        check("1. a drag in the plan: one step, unsaved", state(page), [1, 0, True, False, True])

        # 2. a wall's length typed in the Room card, a keystroke at a time
        page.evaluate("() => selectRoom()")
        time.sleep(0.2)
        sel = '#room input[data-wall="A"][data-wk="length"]'
        page.click(sel, click_count=3)
        page.keyboard.type("4150", delay=60)
        time.sleep(0.4)
        check("  typing: no step per keystroke", page.evaluate("() => S.undo.length"), 1)
        page.keyboard.press("Enter")
        page.wait_for_function("() => S.job.room.walls.find((w) => w.id === 'A').x1 === 4150", timeout=10000)
        computed(page)
        j2 = key(page)
        check("2. a wall length typed: one step", state(page)[:2], [2, 0])

        # 3. a cabinet deleted
        page.click('nav [data-tab="cabinets"]')
        page.wait_for_selector('#cabtable tr[data-i] [data-del]', timeout=10000)
        n_before = page.evaluate("() => S.job.cabinets.length")
        num = page.evaluate("() => S.job.cabinets[2].number")
        page.click('#cabtable tr[data-i="2"] [data-del]')
        page.wait_for_function(f"() => S.job.cabinets.length === {n_before - 1}", timeout=10000)
        computed(page)
        j3 = key(page)
        check(f"3. cabinet {num} deleted: one step", state(page)[:2], [3, 0])

        # 4. a drawer face changed (cabinet 7's second, a Fixed row; the Share row above takes up the difference)
        i4 = page.evaluate("() => S.job.cabinets.findIndex((c) => c.number === 7)")
        page.click(f'#cabtable tr[data-i="{i4}"] td:first-child')
        page.wait_for_selector('#drawerbox input[data-dk="face_height"]', timeout=10000)
        fsel = '#drawerbox input[data-d="1"][data-dk="face_height"]'
        was = page.input_value(fsel)
        page.click(fsel, click_count=3)
        page.keyboard.type(str(int(was) + 10), delay=60)
        page.keyboard.press("Tab")
        computed(page)
        j4 = key(page)
        check("4. a drawer face changed: one step (the solver's heights go with it)",
              [state(page)[:2], j4 != j3], [[4, 0], True])
        os.makedirs(SHOTS, exist_ok=True)
        page.screenshot(path=os.path.join(SHOTS, "undo_four_edits.png"))

        # undo each in turn
        page.click("body", position={"x": 5, "y": 990})
        for k, (want, name) in enumerate(((j3, "the drawer face"), (j2, "the delete"), (j1, "the wall length"),
                                          (j0, "the drag"))):
            if k % 2:
                page.click("#undo")
            else:
                page.keyboard.press("Control+z")
            computed(page)
            check(f"Undo {name} ({'button' if k % 2 else 'Ctrl+Z'}): the job as it was before it", key(page) == want, True)
        check("  back at the loaded job: nothing to undo, everything to redo, saved again",
              state(page), [0, 4, False, True, False])
        check("  the deleted cabinet is back, and the plan's drag undone",
              page.evaluate(f"() => [S.job.cabinets.some((c) => c.number === {num}), "
                            "S.job.placements.find((p) => p.cabinet === 2).x]"), [True, x0])
        # redo them all forward
        for k, (want, name) in enumerate(((j1, "the drag"), (j2, "the wall length"), (j3, "the delete"),
                                          (j4, "the drawer face"))):
            if k == 1:
                page.keyboard.press("Control+Shift+z")
            elif k % 2:
                page.click("#redo")
            else:
                page.keyboard.press("Control+y")
            computed(page)
            check(f"Redo {name}: the job as after it", key(page) == want, True)
        check("  all redone: four to undo, none to redo, unsaved", state(page), [4, 0, True, False, True])
        # a new edit clears Redo
        page.click("#undo")
        computed(page)
        check("one undone: one to redo", state(page)[:2], [3, 1])
        page.click('nav [data-tab="room"]')
        page.evaluate("() => selectRoom()")
        time.sleep(0.2)
        page.fill('#room input[data-r="ceiling"]', "2550")
        page.press('#room input[data-r="ceiling"]', "Tab")
        computed(page)
        check("a new edit (the ceiling): a step, and Redo cleared", state(page)[:4], [4, 0, True, False])
        # Ctrl+Z in a text field is the field's
        before = (key(page), state(page))
        page.click('#room input[data-r="name"]')
        page.keyboard.press("End")
        page.keyboard.type("xy")
        page.keyboard.press("Control+z")
        time.sleep(0.3)
        check("Ctrl+Z inside a text field does not undo the job",
              [page.evaluate("() => S.undo.length"), page.evaluate("() => S.job.room.ceiling")], [before[1][0], 2550])
        # a placement taken out and given a wall again in the Placements table:
        # the engine's free x (an answer that lands after the `change`) is
        # part of the step, not a step of its own
        page.keyboard.press("Escape")
        page.click("body", position={"x": 5, "y": 990})
        page.click("#placesopen")
        page.wait_for_selector('#places select[data-p="2"]', timeout=10000)
        n0 = page.evaluate("() => S.undo.length")
        # a press on the dropdown first, as a hand on the mouse makes one
        page.dispatch_event('#places select[data-p="2"]', "pointerdown")
        page.select_option('#places select[data-p="2"]', "")
        computed(page)
        page.dispatch_event('#places select[data-p="2"]', "pointerdown")
        page.select_option('#places select[data-p="2"]', "B")
        page.wait_for_function("() => { const p = S.job.placements.find((q) => q.cabinet === 2); return p && p.wall === 'B'; }",
                               timeout=10000)
        computed(page)
        time.sleep(0.5)
        landed = page.evaluate("() => S.job.placements.find((q) => q.cabinet === 2).x")
        check("the Placements table: taken out, then onto wall B where the engine puts it — two steps, not three",
              [page.evaluate("() => S.undo.length") - n0, landed > 0], [2, True])
        page.click("#undo")
        computed(page)
        check("  Undo: not placed (never the half-way x 0)",
              page.evaluate("() => S.job.placements.some((q) => q.cabinet === 2)"), False)
        check("no page errors", errors, [])
        browser.close()
    print(f"\n{'ALL OK' if not FAILS else str(len(FAILS)) + ' FAILED: ' + str(FAILS)}")
    return 1 if FAILS else 0


if __name__ == "__main__":
    raise SystemExit(main())
