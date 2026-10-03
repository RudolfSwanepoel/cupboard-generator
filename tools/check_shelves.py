"""Shelves as rows — ruling 5 of the cabinet round brief (3 October 2026).

What is pinned here, from the brief's "Done when" line:

  * an old job's `shelves` read as rows at clearance 4 and its `fixed_shelves`
    as rows at clearance 1 (note "fixed"), fixed first — and cut exactly what
    they cut: the benchmark's cabinets 1 and 4 line for line, every fixture's
    05 lines unchanged, nothing written to the file;
  * a clearance click moves the depth by 1 and the cut line with it; a height
    moves no cut line (it is drawing and 3D only);
  * a new shelf's edging is the front long edge in the exterior board's PVC;
  * the depth reads the back actually chosen (backing 547, solid 550 at 570);
  * the rows are written only when there are any, each key only when set, and
    read back; the first edit zeroes the two numbers (the browser's bargain,
    pinned on the API's migrated rows);
  * where a shelf is drawn: an unedited job on the equal-spacing rule exactly
    as before; a typed height puts the top face that far above the bottom
    panel's top face; the bands follow the row's counts;
  * the benchmark does not move.
"""
import json
import os
import sys

ROOT = os.path.join(os.path.dirname(__file__), "..")
from fixture_jobs import job_file  # noqa: E402
sys.path.insert(0, ROOT)

from app import api                                                      # noqa: E402
from cabinetgen.engine import generate_cabinet, generate_job             # noqa: E402
from cabinetgen.model import MATERIALS, Cabinet, Job, Shelf              # noqa: E402
from cabinetgen.room import interior_parts, shelf_layout                 # noqa: E402
from cabinetgen.standard import STANDARD                                 # noqa: E402
from cabinetgen.store import cabinet_from_dict, cabinet_to_dict, job_to_dict, load  # noqa: E402
from cabinetgen.validate import WARNING, validate                        # noqa: E402
from jobs.wardrobe_oct2025 import JOB as OCT                             # noqa: E402

FAILS = []
std = STANDARD


def check(name, got, want):
    ok = got == want
    print(f"  {'ok  ' if ok else 'FAIL'}  {name}: {got!r}" + ("" if ok else f"  (wanted {want!r})"))
    if not ok:
        FAILS.append(name)
    return ok


def mats():
    return {k: dict(v) for k, v in MATERIALS.items() if k in ("MEL", "BROOKHILL", "BACK")}


def job_of(*cabs):
    return Job(name="s", boards=["MEL", "BROOKHILL", "BACK"], cabinets=list(cabs), materials=mats())


def cab(**kw):
    kw.setdefault("number", 1)
    kw.setdefault("width", 600)
    kw.setdefault("height", 2400)
    kw.setdefault("depth", 570)
    kw.setdefault("kind", "tall")
    kw.setdefault("carcass_board", "MEL")
    kw.setdefault("exterior_board", "BROOKHILL")
    kw.setdefault("back_board", "BACK")
    kw.setdefault("doors", 1)
    return Cabinet(**kw)


def shelves(c):
    return [(p.label, p.length, p.width, p.qty, p.edge_l, p.edge_w, p.edge_material, p.note)
            for p in generate_cabinet(c, std, mats()) if p.role == "Shelve"]


def main():
    print(__doc__.strip().splitlines()[0])

    print("\nan old job's two numbers read as rows: fixed first at 1, then adjustable at 4")
    old = cab(shelves=3, fixed_shelves=1)
    rows = old.shelf_list
    check("four rows, fixed first", [(r.clearance, r.note, r.height) for r in rows],
          [(1, "fixed", None), (4, "", None), (4, "", None), (4, "", None)])
    check("every migrated row is the front edge in the default edging", {(r.kind, r.board, r.long, r.short) for r in rows},
          {("", "", 1, 0)})
    check("and they cut the two lines they always cut: fixed 550 x1 noted, adjustable 547 x3",
          shelves(old), [("105a", 568, 550, 1, 1, 0, "PVC BROOKHILL", "fixed"), ("105b", 568, 547, 3, 1, 0, "PVC BROOKHILL", "")])
    rowsc = cab(shelf_rows=[Shelf(clearance=1, note="fixed")] + [Shelf()] * 3)
    check("the same four rows written out cut the identical lines", shelves(rowsc), shelves(old))
    o1 = next(c for c in OCT.cabinets if c.number == 1)
    o4 = next(c for c in OCT.cabinets if c.number == 4)
    check("the benchmark's cabinet 1 (fixed 1 + 3): rows", [(r.clearance, r.note) for r in o1.shelf_list],
          [(1, "fixed"), (4, ""), (4, ""), (4, "")])
    oct_sh = [(p.cabinet, p.label, p.length, p.width, p.qty, p.edge_l, p.edge_w, p.edge_material, p.note)
              for p in generate_job(OCT) if p.role == "Shelve" and p.cabinet in (1, 4)]
    check("  cabinets 1 and 4 cut 480 x1 fixed and 477 x3, as always",
          oct_sh, [(1, "105a", 668, 480, 1, 1, 0, "PVC BROOKHILL", "fixed"), (1, "105b", 668, 477, 3, 1, 0, "PVC BROOKHILL", ""),
                   (4, "405a", 668, 480, 1, 1, 0, "PVC BROOKHILL", "fixed"), (4, "405b", 668, 477, 3, 1, 0, "PVC BROOKHILL", "")])
    check("  nothing is written: no cabinet in the benchmark has rows", [c.number for c in OCT.cabinets if c.shelf_rows], [])
    check("  the 400-wide shelves of 11 and 12 (deeper than wide) still band their front edge as edge_l",
          {(p.length, p.width, p.edge_l, p.edge_w) for p in generate_job(OCT) if p.role == "Shelve" and p.cabinet in (11, 12)},
          {(400, 477, 1, 0)})

    print("\na clearance click moves the depth by 1 and the cut line with it; a height moves nothing")
    c3 = cab(shelf_rows=[Shelf(clearance=3), Shelf(clearance=4)])
    check("clearance 3 beside 4: 548 and 547, two lines", [(l[2], l[3]) for l in shelves(c3)], [(548, 1), (547, 1)])
    c0 = cab(shelf_rows=[Shelf(clearance=0)])
    check("clearance 0 reaches the back's face: 551 with a backing (570 - 19)", [l[2] for l in shelves(c0)], [551])
    c0.back = "solid"
    check("  and 554 with a solid back (570 - 16)", [l[2] for l in shelves(c0)], [554])
    hts = cab(shelf_rows=[Shelf(height=300), Shelf(height=1200), Shelf()])
    flat = cab(shelf_rows=[Shelf(), Shelf(), Shelf()])
    check("typed heights: the cut list is identical to no heights", shelves(hts), shelves(flat))
    check("  one line of three", [(l[3]) for l in shelves(hts)], [3])
    check("the depth reads the back chosen: backing 547, solid 550, at clearance 4",
          (shelves(cab(shelf_rows=[Shelf()]))[0][2], shelves(cab(back="solid", shelf_rows=[Shelf()]))[0][2]), (547, 550))

    print("\na new shelf: the front long edge in the exterior board's PVC")
    n = Shelf()
    check("Shelf() is clearance 4, no height, 1 long 0 short, default kind and colour",
          (n.height, n.clearance, n.kind, n.board, n.long, n.short, n.note), (None, 4, "", "", 1, 0, ""))
    check("/api/shelf-new hands it over", api.shelf_new({})["row"],
          {"height": None, "clearance": 4, "kind": "", "board": "", "long": 1, "short": 0, "note": ""})
    one = cab(shelf_rows=[n])
    check("it cuts banded on one long edge in PVC BROOKHILL", shelves(one)[0][4:7], (1, 0, "PVC BROOKHILL"))
    two = cab(shelf_rows=[Shelf(long=2, short=2, kind="2mm", board="MEL")])
    check("its own kind and colour, all four edges", shelves(two)[0][4:7], (2, 2, "2mm WHITE"))
    none = cab(shelf_rows=[Shelf(long=0, short=0)])
    check("no edge counted: unedged, no tape", shelves(none)[0][4:7], (0, 0, ""))
    check("a row's long edges are front then rear, ends left then right (the supports' rule) in 3D",
          [sorted(t.side for t in tapes) for q, tapes in interior_parts(two, std, mats()) if q.role == "shelf"],
          [["x0", "x1", "y0", "y1"]])
    check("  the default row bands the front (y1) only",
          [[t.side for t in tapes] for q, tapes in interior_parts(one, std, mats()) if q.role == "shelf"], [["y1"]])

    print("\nwhere a shelf is drawn")
    lay = shelf_layout(old, std, mats())
    n4 = 4; H, t = 2400, 16
    gap = (H - t - n4 * t) / (n4 + 1)
    want = [round(t + gap * (k + 1) + t * k, 1) for k in range(n4)]
    check("an unedited job: the equal-spacing slots, exactly as before", [u["z0"] for u in lay], want)
    check("  fixed first, shown heights = the top face above the bottom panel's top face",
          [(u["fixed"], u["height"], u["typed"]) for u in lay], [(True, want[0], False)] + [(False, h, False) for h in want[1:]])
    lay2 = shelf_layout(hts, std, mats())
    check("typed 300 and 1200: top faces at 316 and 1216 off the carcass underside; the third on its slot",
          [(u["z0"], u["z1"], u["typed"]) for u in lay2], [(300, 316, True), (1200, 1216, True), (round(t + ((H - t - 3 * t) / 4) * 3 + t * 2, 1), round(t + ((H - t - 3 * t) / 4) * 3 + t * 2 + t, 1), False)])
    check("  depth and clearance per row", [(u["depth"], u["clearance"]) for u in lay2], [(547, 4)] * 3)

    print("\nthe job file")
    d = cabinet_to_dict(old)
    check("no rows: no shelf_rows key, the two numbers as they were", ("shelf_rows" in d, d["shelves"], d["fixed_shelves"]), (False, 3, 1))
    d2 = cabinet_to_dict(cab(shelf_rows=[Shelf(), Shelf(height=900, clearance=2, kind="2mm", board="MEL", long=2, short=1, note="fixed")]))
    check("rows written with only the keys that are set", d2["shelf_rows"],
          [{"clearance": 4, "long": 1, "short": 0},
           {"height": 900, "clearance": 2, "kind": "2mm", "board": "MEL", "long": 2, "short": 1, "note": "fixed"}])
    back = cabinet_from_dict(json.loads(json.dumps(d2)))
    check("and read back", [(r.height, r.clearance, r.kind, r.board, r.long, r.short, r.note) for r in back.shelf_rows],
          [(None, 4, "", "", 1, 0, ""), (900, 2, "2mm", "MEL", 2, 1, "fixed")])
    for name in ("Test.json", "Test_Build.json", "Test_Panels.json", "Corner Unit Test.json", "Test_drawers.json"):
        j = load(job_file(name))
        check(f"{name}: no cabinet gains a shelf_rows key on a round trip",
              [c["number"] for c in job_to_dict(j)["cabinets"] if "shelf_rows" in c], [])
    jt = load(job_file("Test.json"))
    sh_before = [(p.cabinet, p.label, p.length, p.width, p.qty, p.edge_l, p.edge_material) for p in generate_job(jt) if p.role == "Shelve"]
    check("Test.json's shelves: five cabinets' lines, 05 unlettered where one size", len(sh_before) > 0 and all(l[1].endswith("05") for l in sh_before), True)

    print("\nthe API: the editor is handed the rows it will copy in on the first edit")
    g = api.compute({"job": job_to_dict(job_of(old))})["geometry"]["1"]["shelves"]
    check("migrated, four rows, each with its depth, shown height and tape", (g["migrated"], len(g["rows"])), (True, 4))
    check("  row 1 is the fixed one at 1: depth 550, note fixed", (g["rows"][0]["clearance"], g["rows"][0]["depth"], g["rows"][0]["note"]), (1, 550, "fixed"))
    check("  row 2: clearance 4, depth 547, PVC BROOKHILL, typed False, shown on its slot",
          (g["rows"][1]["clearance"], g["rows"][1]["depth"], g["rows"][1]["name"], g["rows"][1]["typed"], g["rows"][1]["shown_height"]),
          (4, 547, "PVC BROOKHILL", False, want[1]))
    g2 = api.compute({"job": job_to_dict(job_of(rowsc))})["geometry"]["1"]["shelves"]
    check("rows written: not migrated", g2["migrated"], False)
    check("hidden on a mitre", api.compute({"job": job_to_dict(job_of(cab(corner_style="mitre", arm_a=850, arm_b=850, face_a=500, face_b=500, depth=500)))})["geometry"]["1"]["shelves"]["hidden"], True)

    print("\nthe validator and the elevation read the rows")
    w = [i for i in validate(job_of(cab(back="none", shelf_rows=[Shelf()])), generate_job(job_of(cab(back="none", shelf_rows=[Shelf()]))))
         if i.level == WARNING and "no back" in i.message]
    check("shelves in a cabinet with no back still warn", len(w), 1)

    print("\nthe benchmark")
    P = generate_job(OCT)
    check("272 / 59 / 30", (sum(p.qty for p in P if p.material == "MEL"), sum(p.qty for p in P if p.material == "BROOKHILL"),
                            sum(p.qty for p in P if p.material == "BACK")), (272, 59, 30))

    print()
    if FAILS:
        print(f"{len(FAILS)} FAILED: {FAILS}")
        return 1
    print("ALL OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
