"""Attached panels in the running app, with a real mouse (Playwright, optional).

    python run_app.py --no-window --port 8766      # in another window
    python tools/ui_check_attached.py [--port 8766]

Drives what `check_attached.py` cannot: the editor's "+ Panel on this cabinet",
the Attached block in Panel design, the offsets typed there, the panel drawn in
the plan, the wall elevation and the 3D view, a real drag of its cabinet in the
plan carrying it along, Detach and Attach, delete-with-No and delete-with-Yes,
Duplicate, the Placements table, the 3D handles (none on an attached panel), and
the new cabinet's support defaults following its kind. Against `Test.json`,
never saved: the top-bar Save is the only thing that writes.

Playwright is the only third-party package anywhere near this app and only the
two ui_check scripts need it; without it this says so and exits 0.
"""
import argparse
import json
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

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
LAUNCH = ["--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist"]
FAILS = []


def check(label, got, want):
    ok = got == want
    print(f"  {'ok   ' if ok else 'FAIL '} {label}: {got}" + ("" if ok else f"  want {want}"))
    if not ok:
        FAILS.append(label)
    return ok


def load_job(page, name):
    page.wait_for_function("() => document.querySelectorAll('#joblist option').length > 1", timeout=15000)
    page.select_option("#joblist", name + ".json")
    page.click("#load")
    page.wait_for_function("() => S.job && S.res && S.job.name === %s" % json.dumps(name), timeout=15000)


def computed(page):
    """Wait for the compute the last edit scheduled to have landed."""
    page.wait_for_function("() => typeof computing === 'undefined' || !computing", timeout=15000)
    time.sleep(0.45)
    page.wait_for_function("() => S.res && S.res.ok !== undefined", timeout=15000)


def select_row(page, number):
    page.click(f'#cabtable tr[data-i] td.n:first-child:text-is("{number}")')
    page.wait_for_function(f"() => S.sel !== null && S.job.cabinets[S.sel].number === {number}", timeout=5000)


def geometry(page, number):
    return page.evaluate(f"() => S.res.geometry[String({number})]")


def main():
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=not args.headed, args=LAUNCH)
        ctx = browser.new_context(viewport={"width": 1500, "height": 950})
        page = ctx.new_page()
        errors = []
        page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
        page.on("pageerror", lambda e: errors.append(str(e)))
        answer = {"accept": True}
        seen = []
        page.on("dialog", lambda d: (seen.append(d.message), d.accept() if answer["accept"] else d.dismiss()))
        page.goto(URL)
        page.wait_for_function("() => S.def !== null", timeout=15000)
        load_job(page, "Test")

        print("\n+ Panel on this cabinet, from cabinet 1's editor")
        select_row(page, 1)
        page.wait_for_selector("#attachedbox #padd", timeout=5000)
        check("cabinet 1 has no attached panels to start with",
              page.evaluate("() => document.querySelectorAll('#attachedbox tbody tr').length"), 0)
        n0 = page.evaluate("() => S.job.cabinets.length")
        page.click("#attachedbox #padd")
        page.wait_for_function(f"() => S.job.cabinets.length === {n0 + 1}", timeout=5000)
        computed(page)
        num = page.evaluate("() => S.job.cabinets[S.job.cabinets.length - 1].number")
        spec = page.evaluate("() => S.job.cabinets[S.job.cabinets.length - 1].panel")
        check("a new panel is made, selected, attached to 1 with the engine's offsets",
              (page.evaluate("() => S.job.cabinets[S.sel].number") == num, spec["attached_to"],
               spec["at_x"], spec["at_y"], spec["orientation"]), (True, 1, -16, -16, "end"))
        page.wait_for_selector("#panelbox #pdetach", timeout=5000)
        check("Panel design shows the Attached block with Detach and the three offsets",
              page.evaluate("() => ['at_x','at_y','at_z'].map((k) => !!document.querySelector(`#panelbox [data-pk=${k}]`))"),
              [True, True, True])
        g = geometry(page, num)
        check("the readout is the engine's derived place", bool(g["panel"]["placed_at"]), True)
        host_place = page.evaluate("() => places().find((p) => p.cabinet === 1)")
        check("  16 left of cabinet 1, on its wall", (g["panel"]["placed_at"]["wall"], g["panel"]["placed_at"]["x"]),
              (host_place["wall"], host_place["x"] - 16))
        check("the cabinet table says what it hangs off",
              page.evaluate(f"() => [...document.querySelectorAll('#cabtable tr')].some((tr) => tr.textContent.includes('panel · on 1'))"), True)

        print("\ntyping an offset moves it; the plan and the elevation draw it")
        page.fill('#panelbox [data-pk="at_z"]', "150")
        page.dispatch_event('#panelbox [data-pk="at_z"]', "input")
        computed(page)
        check("Z typed as 150 lifts the panel's underside 150 above the legs",
              geometry(page, num)["panel"]["placed_at"]["z"], 100 + 150)
        page.click('nav [data-tab="room"]')
        page.wait_for_function(f"() => document.querySelector('#plan [data-host=\"1\"]') !== null", timeout=10000)
        check("the plan draws it, marked as cabinet 1's",
              page.evaluate(f"() => document.querySelectorAll('#plan [data-panel=\"{num}\"][data-host=\"1\"]').length > 0"), True)
        page.click('nav [data-tab="cabinets"]')
        page.click(f'#elevpick [data-elev="{host_place["wall"]}"]')      # the wall the cabinet stands on
        page.wait_for_function(f"() => document.querySelector('#elevation .epanel[data-cab=\"{num}\"]') !== null", timeout=10000)
        check("the wall elevation draws it, marked as cabinet 1's",
              page.evaluate(f"() => !!document.querySelector('#elevation .epanel[data-cab=\"{num}\"][data-host=\"1\"]')"), True)

        print("\ndragging cabinet 1 in the plan carries the panel with it")
        page.click('nav [data-tab="room"]')
        page.wait_for_selector('#plan .cab[data-cab="1"]', timeout=10000)
        # selecting from the table isolates (by design), and an isolated plan
        # drags only the isolated item: end it, as a click on empty canvas does
        page.evaluate("() => { S.isolate = null; renderPlan(); }")
        page.wait_for_function("() => S.isolate === null && document.querySelector('#plan .cab[data-cab=\"1\"]')", timeout=10000)
        time.sleep(0.3)
        before = geometry(page, num)["panel"]["placed_at"]
        x_before = page.evaluate("() => places().find((p) => p.cabinet === 1).x")
        box = page.evaluate("() => { const r = document.querySelector('#plan .cab[data-cab=\"1\"]').getBoundingClientRect(); return [r.left + r.width / 2, r.top + r.height / 2]; }")
        # along the wall the cabinet stands on, whichever way that runs on the page
        d = page.evaluate(f"() => {{ const t = tracks().find((t) => t.wall === {json.dumps(host_place['wall'])}); const L = Math.hypot(t.dx, t.dy) || 1; return [t.dx / L, t.dy / L]; }}")
        page.mouse.move(box[0], box[1])
        page.mouse.down()
        time.sleep(0.6)                                # let the drag model land
        for i in range(1, 9):
            page.mouse.move(box[0] + d[0] * 8 * i, box[1] + d[1] * 8 * i)
            time.sleep(0.03)
        moved_preview = page.evaluate(f"() => !!document.querySelector('#plan [data-host=\"1\"]').getAttribute('transform')")
        page.mouse.up()
        computed(page)
        x_after = page.evaluate("() => places().find((p) => p.cabinet === 1).x")
        after = geometry(page, num)["panel"]["placed_at"]
        check("the drag moved the cabinet", x_after != x_before, True)
        check("  the panel's shapes moved with it in the preview", moved_preview, True)
        check("  and after the drop the panel is exactly as far along as the cabinet",
              after["x"] - before["x"], x_after - x_before)
        check("  no placement record was written for the panel",
              page.evaluate(f"() => places().some((p) => p.cabinet === {num})"), False)
        check("the Placements table shows it with cabinet 1, not editable",
              page.evaluate(f"() => {{ const tr = document.querySelector('#places tr[data-cab=\"{num}\"]'); return tr && tr.textContent.includes('with 1') && [...tr.querySelectorAll('input')].every((i) => i.disabled); }}"), True)

        print("\nthe 3D view: drawn, listed as cabinet 1's, no handles of its own")
        page.click('nav [data-tab="view3d"]')
        page.wait_for_function("() => typeof V3D === 'object' && V3D !== null", timeout=30000)
        page.wait_for_function("() => !S.sceneStale && V3D.memory().groups > 0", timeout=20000)
        page.wait_for_function("() => V3D.idle()", timeout=10000)
        ids = page.evaluate("() => V3D.groupIds()")
        check("the panel has a group in the scene", str(num) in ids, True)
        page.evaluate(f"() => V3D.select({num})")
        time.sleep(0.3)
        check("selected in 3D it gets NO move handles", page.evaluate("() => V3D.dragInfo().handles.length"), 0)
        page.evaluate("() => V3D.select(1)")
        time.sleep(0.3)
        check("  cabinet 1 still gets its two", page.evaluate("() => V3D.dragInfo().handles.length"), 2)
        check("the item list says 'panel on 1'",
              page.evaluate(f"() => [...document.querySelectorAll('#v3dlist .row, .v3dlist .row, [data-n=\"{num}\"]')].some((r) => r.textContent.includes('panel on 1'))"), True)

        print("\nDetach and Attach, through the editor")
        page.click('nav [data-tab="cabinets"]')
        select_row(page, num)
        page.wait_for_selector("#panelbox #pdetach", timeout=5000)
        page.click("#panelbox #pdetach")
        page.wait_for_function(f"() => places().some((p) => p.cabinet === {num})", timeout=5000)
        computed(page)
        rec = page.evaluate(f"() => places().find((p) => p.cabinet === {num})")
        check("Detach: a placement record where it stood, number unchanged",
              (rec["wall"], rec["x"], rec["z"], rec.get("y", 0)), (after["wall"], after["x"], after["z"], after["y"]))
        check("  the panel is standalone", page.evaluate("() => S.job.cabinets[S.sel].panel.attached_to"), None)
        page.wait_for_selector("#panelbox #pattachgo", timeout=5000)
        page.select_option("#panelbox #pattach", "1")
        page.click("#panelbox #pattachgo")
        page.wait_for_function("() => S.job.cabinets[S.sel].panel.attached_to === 1", timeout=5000)
        computed(page)
        spec = page.evaluate("() => S.job.cabinets[S.sel].panel")
        check("Attach: back on cabinet 1 with the offsets that keep it where it stood",
              (spec["at_x"], spec["at_y"], spec["at_z"]), (-16, -16, 150))
        check("  the record is gone again", page.evaluate(f"() => places().some((p) => p.cabinet === {num})"), False)
        check("  and it stands exactly where it did", geometry(page, num)["panel"]["placed_at"], after)

        print("\nDuplicate cabinet 1: the copy brings a copy of the panel")
        count = page.evaluate("() => S.job.cabinets.length")
        page.click('#cabtable tr[data-i="0"] [data-dup]')
        page.wait_for_function(f"() => S.job.cabinets.length === {count + 2}", timeout=5000)
        computed(page)
        copies = page.evaluate("() => S.job.cabinets.slice(1, 3).map((c) => [c.number, c.kind, c.panel ? c.panel.attached_to : null])")
        kind1 = page.evaluate("() => S.job.cabinets[0].kind")
        check("two new items: the cabinet, and its panel attached to the copy",
              (copies[0][1], copies[1][1], copies[1][2]), (kind1, "panel", copies[0][0]))
        check("  new numbers, all distinct",
              page.evaluate("() => new Set(S.job.cabinets.map((c) => c.number)).size === S.job.cabinets.length"), True)

        print("\ndeleting the copy: No keeps its panel standalone; Yes takes the panel too")
        copy_no, copy_panel = copies[0][0], copies[1][0]
        answer["accept"] = False                        # Cancel = No, keep them
        page.evaluate(f"() => places().push({{cabinet: {copy_no}, wall: 'A', x: 3300, z: 0, y: 0, flip: false, layer: null}})")
        computed(page)
        page.click('#cabtable tr[data-i="1"] [data-del]')
        page.wait_for_function(f"() => !S.job.cabinets.some((c) => c.number === {copy_no})", timeout=5000)
        computed(page)
        check("the question was asked", any("attached panel" in m for m in seen), True)
        left = page.evaluate(f"() => S.job.cabinets.find((c) => c.number === {copy_panel})")
        rec = page.evaluate(f"() => places().find((p) => p.cabinet === {copy_panel})")
        check("No: the panel stays, standalone, with a place of its own",
              (left is not None, left and left["panel"].get("attached_to"), rec is not None and rec["wall"]), (True, None, "A"))
        seen.clear()
        answer["accept"] = True                          # OK = Yes, delete them too
        select_row(page, 1)
        n_before = page.evaluate("() => S.job.cabinets.length")
        page.click('#cabtable tr[data-i="0"] [data-del]')
        page.wait_for_function(f"() => S.job.cabinets.length === {n_before - 2}", timeout=5000)
        computed(page)
        check("Yes: cabinet 1 and its panel are both gone",
              page.evaluate(f"() => S.job.cabinets.some((c) => c.number === 1 || c.number === {num})"), False)

        print("\nA: a new cabinet's supports follow its kind while untouched")
        page.click("#add")
        page.wait_for_function(f"() => S.job.cabinets.length === {n_before - 1}", timeout=5000)
        computed(page)
        live = "() => S.job.cabinets[S.sel].support_rows.filter((r) => (r.qty || 0) > 0).map((r) => r.type)"
        check("a new (tall) cabinet: four Backs", page.evaluate(live), ["back"] * 4)
        page.select_option('#editor [data-k="kind"]', "base")
        page.dispatch_event('#editor [data-k="kind"]', "input")
        page.wait_for_function("() => S.job.cabinets[S.sel].support_rows.some((r) => r.type === 'front')", timeout=5000)
        computed(page)
        check("made base: Front, Top Rear, two Backs", page.evaluate(live), ["front", "top_rear", "back", "back"])
        page.select_option('#editor [data-k="kind"]', "upper")
        page.dispatch_event('#editor [data-k="kind"]', "input")
        page.wait_for_function("() => S.job.cabinets[S.sel].support_rows.filter((r) => (r.qty || 0) > 0).length === 3", timeout=5000)
        computed(page)
        check("made wall: three Backs", page.evaluate(live), ["back"] * 3)
        # an edit by hand, to a row that counts (the qty-0 Front the block makes up is not one)
        page.evaluate("() => { S.job.cabinets[S.sel].support_rows.find((r) => r.type === 'back').edges = ['front']; }")
        page.select_option('#editor [data-k="kind"]', "base")
        page.dispatch_event('#editor [data-k="kind"]', "input")
        computed(page)
        time.sleep(0.5)
        check("once a row is edited, the kind no longer rewrites the rows", page.evaluate(live), ["back"] * 3)
        check("an existing cabinet's rows were never touched",
              page.evaluate("() => S.job.cabinets.find((c) => c.number === 2).support_rows.filter((r) => (r.qty || 0) > 0).map((r) => r.type)"),
              ["front", "top_rear", "back"])

        check("no console or page errors", errors, [])
        browser.close()

    print()
    if FAILS:
        print(f"{len(FAILS)} FAILED: {FAILS}")
        sys.exit(1)
    print("ALL OK")


if __name__ == "__main__":
    main()
