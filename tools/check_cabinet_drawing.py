"""A drawing per cupboard — ruling 7 of the cabinet round brief (3 October 2026).

What is pinned here, from the brief's "Done when" line:

  * `render.cabinet_section_dims` closes its chains on H and D (and W) for a
    tall with shelves, a base with drawers, and a solid-back cupboard: every
    chain runs from its datum to the whole, and the segments add up;
  * the shelves are dimensioned from the top face of the bottom panel to the
    top face of each shelf — the figure the Shelves section shows — and their
    depths read the clearance at the FACE (the shelf against the back);
  * `render.cabinet_svg` draws the front and the section, every chain segment
    wide enough to carry a label is labelled, the overall W, H and D always,
    the shelf heights and depths, the supports; legs are a note, not drawn;
  * a mitre and a blind corner draw their own construction; an ell says
    "construction not ruled"; a Panel has no cupboard drawing;
  * the export writes one `<job>_cabinet_<n>.svg` per TICKED cupboard, none
    for an unticked one, every cupboard when none is named, never a Panel —
    with or without a room (the "no room, no drawing" ruling is about room
    drawings), and the pictures beside them;
  * /api/cabinet-drawing answers with the SVG and the numbers; nothing moves
    on the benchmark.
"""
import os
import re
import shutil
import sys
import tempfile

ROOT = os.path.join(os.path.dirname(__file__), "..")
from fixture_jobs import job_file  # noqa: E402
sys.path.insert(0, ROOT)

from app import api                                                      # noqa: E402
from cabinetgen.engine import generate_job                               # noqa: E402
from cabinetgen.model import MATERIALS, Cabinet, Drawer, Job, Shelf, Support, PanelSpec  # noqa: E402
from cabinetgen.render import cabinet_section_dims, cabinet_svg          # noqa: E402
from cabinetgen.room import rectangular                                  # noqa: E402
from cabinetgen.standard import STANDARD                                 # noqa: E402
from cabinetgen.store import job_to_dict, load                           # noqa: E402
from jobs.wardrobe_oct2025 import JOB as OCT                             # noqa: E402

FAILS = []
std = STANDARD


def check(name, got, want):
    ok = got == want
    print(f"  {'ok  ' if ok else 'FAIL'}  {name}: {got!r}" + ("" if ok else f"  (wanted {want!r})"))
    if not ok:
        FAILS.append(name)
    return ok


def diffs(chain):
    return [b - a for a, b in zip(chain, chain[1:])]


def dim_labels(svg):
    return set(re.findall(r'class="dim"[^>]*>(\d+)</text>', svg))


def mats():
    return {k: dict(v) for k, v in MATERIALS.items() if k in ("MEL", "BROOKHILL", "BACK")}


def job_of(*cabs):
    return Job(name="d", boards=["MEL", "BROOKHILL", "BACK"], cabinets=list(cabs), materials=mats())


def cab(**kw):
    kw.setdefault("number", 1)
    kw.setdefault("carcass_board", "MEL")
    kw.setdefault("exterior_board", "BROOKHILL")
    kw.setdefault("back_board", "BACK")
    kw.setdefault("doors", 1)
    return Cabinet(**kw)


def main():
    print(__doc__.strip().splitlines()[0])
    t = std.board_t

    print("\na tall with shelves: the chains close on H and D")
    tall = cab(width=600, height=2400, depth=570, kind="tall", shelf_rows=[Shelf(), Shelf(height=900), Shelf(clearance=2)],
               support_rows=[Support(type="back", qty=3, cut_board="MEL", board="MEL", kind="pvc", edges=[])])
    d = cabinet_section_dims(job_of(tall), 1)
    check("the height chain adds up to H", sum(diffs(d["height_chain"])), 2400)
    check("  it starts at 0, has the bottom's top face and the top's underside, ends at H",
          (d["height_chain"][0], t in d["height_chain"], 2400 - t in d["height_chain"], d["height_chain"][-1]), (0, True, True, 2400))
    check("the depth chain adds up to D", sum(diffs(d["depth_chain"])), 570)
    check("  the backing in its slot: 16 and 19 off the wall", (16 in d["depth_chain"], 19 in d["depth_chain"]), (True, True))
    check("the width chain adds up to W, the two sides in it", (sum(diffs(d["width_chain"])), d["width_chain"]), (600, [0, 16, 584, 600]))
    check("three shelves: heights as the Shelves section shows them (typed 900 second)",
          [(s["height"], s["typed"]) for s in d["shelves"]], [(d["shelves"][0]["height"], False), (900, True), (d["shelves"][2]["height"], False)])
    check("  each top face is a breakpoint of the height chain", all(s["z1"] in d["height_chain"] for s in d["shelves"]), True)
    check("  depths 547, 547, 549 — the clearance at the face, the shelf against the back",
          [(s["depth"], s["clearance"], s["y0"], s["y1"]) for s in d["shelves"]], [(547, 4, 19, 566), (547, 4, 19, 566), (549, 2, 19, 568)])
    check("  each front edge is a breakpoint of the depth chain", all(s["y1"] in d["depth_chain"] for s in d["shelves"]), True)
    check("three Back supports, upright, their edges in the height chain",
          ([(u["type"], u["upright"]) for u in d["supports"]], all(u["z0"] in d["height_chain"] and u["z1"] in d["height_chain"] for u in d["supports"])),
          ([("back", True)] * 3, True))
    check("legs are a note: 100", d["legs"], 100)
    svg = cabinet_svg(job_of(tall), 1, pictures="")
    labels = dim_labels(svg)
    check("the SVG carries the overall W, H and D", {"600", "2400", "570"} <= labels, True)
    check("  and each shelf height", {str(int(round(s["height"]))) for s in d["shelves"]} <= labels, True)
    check("  and each shelf depth on the shelf", sorted(re.findall(r'class="shelfdepth"[^>]*>(\d+)<', svg)), ["547", "547", "549"])
    check("  the front and the section are both there", ('class="cabfront"' in svg, 'class="cabsection"' in svg), (True, True))
    check("  legs are not drawn: the note says so", "legs 100 mm, not drawn" in svg, True)
    # every chain segment that is wide enough for a label (18 px) is labelled
    scale = min((1100 - 48 * 2 - 34 * 2) / (600 + 60 + 570), 520 / 2400)
    want = {str(int(round(b - a))) for ch in (d["height_chain"], d["depth_chain"], d["width_chain"])
            for a, b in zip(ch, ch[1:]) if (b - a) * scale >= 18}
    check("  every chain segment wide enough for a label is labelled", sorted(want - labels), [])

    print("\na base with drawers")
    base = cab(width=600, height=720, depth=560, kind="base", doors=0, has_doors=False,
               drawers=[Drawer(face_height=200, box_height=150), Drawer(face_height=200, box_height=150), Drawer(face_height=314, box_height=150)],
               support_rows=[Support(type="front", qty=1, cut_board="MEL", board="BROOKHILL", kind="pvc", edges=["front"]),
                             Support(type="top_rear", qty=1, cut_board="MEL", board="MEL", kind="pvc", edges=["front"]),
                             Support(type="back", qty=2, cut_board="MEL", board="MEL", kind="pvc", edges=[])])
    d = cabinet_section_dims(job_of(base), 1)
    check("height chain closes on H (no top: no H - t)", (sum(diffs(d["height_chain"])), 720 - t in d["height_chain"]), (720, False))
    check("depth chain closes on D, the flat rails' edges in it",
          (sum(diffs(d["depth_chain"])), d["depth_chain"]), (560, [0, 16, 19, 119, 460, 560]))
    check("the four rails", [(u["type"], u["n"]) for u in d["supports"]], [("front", 1), ("top_rear", 1), ("back", 1), ("back", 2)])
    svg = cabinet_svg(job_of(base), 1, pictures="")
    check("drawer boxes and runners are in the section",
          (svg.count('class="drawer_side"') >= 3, 'class="runner_outer"' in svg, svg.count('class="front"') >= 3), (True, True, True))
    check("W, H, D labelled", {"600", "720", "560"} <= dim_labels(svg), True)

    print("\na solid-back cupboard")
    sol = cab(width=450, height=790, depth=570, kind="base", back="solid", shelf_rows=[Shelf()],
              support_rows=[Support(type="front", qty=1, cut_board="MEL", board="BROOKHILL", kind="pvc", edges=["front"])])
    d = cabinet_section_dims(job_of(sol), 1)
    check("height chain closes on H", sum(diffs(d["height_chain"])), 790)
    check("depth chain closes on D: the solid back 0..16, the shelf's face at 566, the Front",
          d["depth_chain"], [0, 16, 470, 566, 570])
    check("the back is the solid one, flush with the sides' back edges", (d["back"]["kind"], d["back"]["y0"], d["back"]["y1"], d["back"]["cavity"]), ("solid", 0, 16, 0))
    check("the shelf: 550 deep at 4, against the solid back", [(s["depth"], s["y0"], s["y1"]) for s in d["shelves"]], [(550, 16, 566)])
    svg = cabinet_svg(job_of(sol), 1, pictures="")
    check("drawn with the solid back and no cavity hatch", ('class="back"' in svg, 'class="cavity"' in svg, "solid back" in svg), (True, False, True))

    print("\ncorner units, a Panel, a hand-built cabinet")
    cj = load(job_file("Corner Unit Test.json"))
    mit = next(c for c in cj.cabinets if c.corner_kind == "mitre")
    svg = cabinet_svg(cj, mit.number, pictures="")
    dm = cabinet_section_dims(cj, mit.number)
    check("a mitre draws (its parts projected), chains closing on its geometry",
          (len(svg) > 2000, sum(diffs(dm["height_chain"])) == dm["height_chain"][-1], sum(diffs(dm["depth_chain"])) == dm["depth_chain"][-1]), (True, True, True))
    ell = cab(number=9, width=900, height=720, depth=560, kind="base", corner_style="ell", arm_a=900, arm_b=900, face_a=560, face_b=560)
    check("an ell says construction not ruled", "construction not ruled" in cabinet_svg(job_of(ell), 9, pictures=""), True)
    pan = cab(number=3, width=600, height=720, depth=16, kind="panel", panel=PanelSpec(board="BROOKHILL", orientation="upright", a=600, b=720))
    check("a Panel has no cupboard drawing", ("no cupboard drawing" in cabinet_svg(job_of(pan), 3), cabinet_section_dims(job_of(pan), 3)), (True, {}))
    hand = cab(number=5, width=600, height=720, depth=560, kind="base", template="none")
    check("a hand-built cabinet: footprint only, and says so", (cabinet_section_dims(job_of(hand), 5)["footprint_only"], "hand-built" in cabinet_svg(job_of(hand), 5, pictures="")), (True, True))

    print("\nthe export: one file per ticked cupboard, with or without a room")
    out = tempfile.mkdtemp(prefix="cabinet_drawing_")
    was = api.OUT_DIR
    try:
        api.OUT_DIR = out
        j = job_of(cab(number=1, width=600, height=720, depth=560, kind="base"),
                   cab(number=2, width=600, height=2400, depth=560, kind="tall"),
                   cab(number=3, width=600, height=720, depth=16, kind="panel", panel=PanelSpec(board="BROOKHILL", orientation="upright", a=600, b=720)))
        j.name = "cd"
        # the house record carries no picture; a job's board does when the Boards
        # tab gave it one (Test.json's Brookhill), and the drawing then asks for it
        j.materials["BROOKHILL"]["picture"] = "Pictures/Brookhill.png"
        r = api.export({"job": job_to_dict(j)})
        check("no room, nothing named: every cupboard's drawing, no Panel, no room drawing",
              sorted(f for f in r["files"] if f.endswith(".svg") and not f.startswith("nest_")), ["cd_cabinet_1.svg", "cd_cabinet_2.svg"])
        r = api.export({"job": job_to_dict(j), "cabinets": [2]})
        check("cabinet 2 ticked alone: its file alone", sorted(f for f in r["files"] if "_cabinet_" in f), ["cd_cabinet_2.svg"])
        check("  and on disk", sorted(f for f in os.listdir(os.path.join(out, "cd", "drawings")) if f.endswith(".svg")), ["cd_cabinet_2.svg"])
        check("  the picture of the grained board beside it", any(not f.endswith(".svg") for f in os.listdir(os.path.join(out, "cd", "drawings"))), True)
        r = api.export({"job": job_to_dict(j), "cabinets": []})
        check("none ticked: none written", [f for f in r["files"] if "_cabinet_" in f], [])
        j.room = rectangular(4000, 3000, ceiling=2700)
        r = api.export({"job": job_to_dict(j), "walls": [], "cabinets": [1]})
        check("with a room, no wall ticked, cabinet 1 ticked: the plan and cabinet 1",
              sorted(f for f in r["files"] if f.endswith(".svg") and not f.startswith("nest_")), ["cd_cabinet_1.svg", "cd_plan.svg"])
        check("export_cabinets: every cupboard when none is named, in job order, never a Panel",
              api.export_cabinets(j, {}), [1, 2])
    finally:
        api.OUT_DIR = was
        shutil.rmtree(out, ignore_errors=True)

    print("\nthe API")
    r = api.cabinet_drawing({"job": job_to_dict(job_of(tall)), "number": 1})
    check("/api/cabinet-drawing: the SVG and the numbers", (r["ok"], r["svg"].startswith("<svg"), r["dims"]["height"]), (True, True, 2400))
    check("  a number the job lacks is refused", api.cabinet_drawing({"job": job_to_dict(job_of(tall)), "number": 7})["ok"], False)
    check("  routed", "/api/cabinet-drawing" in api.ROUTES, True)

    print("\nthe benchmark")
    P = generate_job(OCT)
    check("272 / 59 / 30", (sum(p.qty for p in P if p.material == "MEL"), sum(p.qty for p in P if p.material == "BROOKHILL"),
                            sum(p.qty for p in P if p.material == "BACK")), (272, 59, 30))
    for c in OCT.cabinets[:6]:
        dd = cabinet_section_dims(OCT, c.number)
        check(f"October cabinet {c.number}: chains close", (sum(diffs(dd["height_chain"])) == dd["height"], sum(diffs(dd["depth_chain"])) == dd["depth"]), (True, True))

    print()
    if FAILS:
        print(f"{len(FAILS)} FAILED: {FAILS}")
        return 1
    print("ALL OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
