"""Screenshots of the 3D views, the same four every time (3D realism brief,
29 September 2026).

    python run_app.py --no-window --port 8766      # in another window
    python tools/ui_shots_3d.py [--port 8766] [--out DIR] [--tag before|after]

Writes `<tag>_<view>.png` into DIR (default `Claude outputs/3d-realism-
screenshots/`): the 3D tab at Home on Test.json, the 3D tab face on to wall A
(key `1`), and the Cabinets tab's 3D on cabinet 4 with the fronts closed and
open. Before-and-after pairs of these are the brief's acceptance. Needs
Playwright, and says so and exits 0 without it, as the ui_check scripts do.
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
    print("playwright is not installed; skipping the screenshots")
    sys.exit(0)

ap = argparse.ArgumentParser()
ap.add_argument("--port", type=int, default=8766)
ap.add_argument("--out", default=os.path.join(ROOT, "Claude outputs", "3d-realism-screenshots"))
ap.add_argument("--tag", default="after")
args = ap.parse_args()
URL = f"http://127.0.0.1:{args.port}/"
LAUNCH = ["--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist"]


def load_job(page, name):
    page.wait_for_function("() => [...document.querySelectorAll('#joblist option')].some((o) => o.value === %s)"
                           % json.dumps(name + ".json"), timeout=15000)
    page.select_option("#joblist", name + ".json")
    page.click("#load")
    page.wait_for_function("() => S.job && S.res && S.job.name === %s" % json.dumps(name), timeout=15000)


def tab(page, name):
    page.click(f'nav [data-tab="{name}"]')
    page.wait_for_function(f"() => S.tab === '{name}'", timeout=5000)


def settle(page, view="V3D"):
    page.wait_for_function(f"() => {view}.idle()", timeout=10000)
    time.sleep(0.4)


def shot(page, name, selector):
    os.makedirs(args.out, exist_ok=True)
    path = os.path.join(args.out, f"{args.tag}_{name}.png")
    page.locator(selector).screenshot(path=path)
    print("  wrote", path)


with sync_playwright() as pw:
    browser = pw.chromium.launch(headless=True, args=LAUNCH)
    ctx = browser.new_context(viewport={"width": 1400, "height": 900})
    page = ctx.new_page()
    page.on("dialog", lambda d: d.accept())
    page.goto(URL)
    load_job(page, "Test")
    tab(page, "view3d")
    page.wait_for_function("() => typeof V3D === 'object' && V3D !== null", timeout=30000)
    page.wait_for_function("() => !S.sceneStale && V3D.memory().groups > 0", timeout=20000)
    settle(page)
    page.evaluate("() => V3D.viewHome(false)")
    settle(page)
    shot(page, "3d_home", "#v3dview")
    page.evaluate("() => V3D.viewWall(0, false)")
    settle(page)
    shot(page, "3d_wall_a", "#v3dview")
    tab(page, "cabinets")
    page.evaluate("() => { selectCabinet(S.job.cabinets.findIndex((c) => c.number === 4), {isolate: false}); renderList(); }")
    page.wait_for_function("() => typeof V3C === 'object' && V3C !== null", timeout=30000)
    page.wait_for_function("() => !S.cabSceneStale && cabTimer === null && S.cab3dShown === 4", timeout=20000)
    settle(page, "V3C")
    page.evaluate("() => V3C.viewHome(false)")
    settle(page, "V3C")
    shot(page, "cab4_closed", "#c3dview")
    page.click("#c3dbar button:has-text('Fronts')")
    page.wait_for_function("() => V3C.state().fronts === true", timeout=5000)
    settle(page, "V3C")
    time.sleep(0.6)
    shot(page, "cab4_open", "#c3dview")
    browser.close()
print("ui_shots_3d: done")
