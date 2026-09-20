"""Independent panels: the cut list line, the geometry, and what they stay out of.

    python tools/check_panels.py

A panel is a `Cabinet` with `kind="panel"` and a `PanelSpec`, so it reuses the
numbering, the save and load, the cabinet table, the placement record and the
one `generate_job` loop — which is where the cost, the nesting and the CSV come
from for free. The price of that is this file: every place that assumes "a
cabinet is a box with doors" has to say what it does about a panel, and here is
where it is held to it.

The three that would bite hardest:

* **`kind` is the only thing that says panel.** The design note proposed
  `template="panel"` as well. It cannot be: switching an item back from Panel
  would then have to put `template` where it was, and there is nothing to put it
  back from — October cabinets 3 and 5 are `template="standard"` carrying
  hand-specified extras, so "it has bespoke panels, therefore it was bespoke" is
  wrong, and being wrong there rewrites a real cut list. Off `kind`, a round
  trip loses nothing, and that is checked below panel by panel.
* **`Length` IS the grain direction.** On a grained board the extent the grain
  runs along becomes the length whether it is the longer of the two or not, and
  the panel locks. On a plain board the longer extent is the length and the
  nester may turn it. Which means long-and-short edges are NOT the same question
  as edge_l-and-edge_w, and the mapping between them is checked here.
* **A panel is not a carcass.** It stands on no legs, closes no gap, carries no
  plinth board and is not in the Run drawing. `room.placed` skips it explicitly,
  which is what keeps gaps, runs, plinth and tip-up exactly as they were.
"""
import json
import os
import sys

ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, ROOT)

from cabinetgen import boards as B                                       # noqa: E402
from cabinetgen.engine import generate_cabinet, generate_job            # noqa: E402
from cabinetgen.model import (PANEL_CODE, PANEL_ORIENTATIONS, Cabinet,   # noqa: E402
                              Drawer, Job, Panel, PanelSpec, Support)
from cabinetgen.render import elevation_svg, tape_legend                 # noqa: E402
from cabinetgen.room import geometry, placed, stands_on_legs             # noqa: E402
from cabinetgen.store import (cabinet_from_dict, cabinet_to_dict,        # noqa: E402
                              job_from_dict, job_to_dict, load, next_number)
from cabinetgen.validate import validate                                 # noqa: E402

FAILS = []


def check(name, got, want):
    ok = got == want
    print(f"  {'ok   ' if ok else 'FAIL '} {name}: {got}" + ("" if ok else f"  want {want}"))
    if not ok:
        FAILS.append(name)


def library():
    """An in-memory library, not the workshop's.

    `check_library.py` used to read the live `boards.json` and died at line 184
    the day a board was renamed, with thirty checks after it silently not
    running. Nothing here reads it either.
    """
    return {
        "MEL": B.to_material(B.Board(id="MEL", name="WHITE MELAMINE", tape="WHITE",
                                     thickness=16, grain="plain", price=575.0)),
        "WOOD": B.to_material(B.Board(id="WOOD", name="WOODGRAIN", tape="WOOD",
                                      thickness=16, grain="grain", price=999.0)),
        "THIN": B.to_material(B.Board(id="THIN", name="3MM BACKING", tape="WHITE",
                                      thickness=3, grain="plain", price=310.0)),
        "BARE": B.to_material(B.Board(id="BARE", name="NO EDGING AT ALL", tape="BARE",
                                      thickness=16, grain="plain", price=400.0,
                                      has_edging=False)),
        "TWOMM": B.to_material(B.Board(id="TWOMM", name="2MM ONLY", tape="TWO",
                                       thickness=16, grain="plain", price=400.0,
                                       has_edging=True, edging_kinds=["2mm"])),
    }


MATS = library()


def panel(number=2, **spec):
    return Cabinet(number=number, width=0, height=0, depth=0, kind="panel",
                   panel=PanelSpec(**spec))


def job_of(*cabs):
    return Job(name="p", cabinets=list(cabs), boards=sorted(MATS), materials=dict(MATS))


def line(cab):
    return generate_cabinet(cab, materials=MATS)


def main():
    print(__doc__.strip().splitlines()[0])

    # ---- D3: one panel in, one cut-list line out --------------------------
    print("\nD3 — a panel is one line on the cut list, derived and never typed")
    p = line(panel(12, board="WOOD", orientation="upright", a=1200, b=300,
                   grain_along="a", edge_kind="2mm", edge_long=1))
    check("one panel, one line", len(p), 1)
    one = p[0]
    check("numbered in the cabinet series, coded 08", (one.label, one.code),
          ("1208", PANEL_CODE))
    check("and its role tells it from an exposed end", one.role, "Panel")
    check("cut from the board it names", one.material, "WOOD")
    check("at the size that was typed", (one.length, one.width), (1200, 300))
    check("qty is always 1 — identical panels are duplicates, each numbered",
          one.qty, 1)
    check("edged as the board offers", one.edge_material, "2mm WOOD")
    check("and the note comes across",
          line(panel(12, board="MEL", a=10, b=20))[0].note, "")

    # ---- the grain rule ---------------------------------------------------
    print("\nLength IS the grain direction, so it is not simply the longer side")
    g = line(panel(board="WOOD", a=1200, b=300, grain_along="b"))[0]
    check("a grained board, grain along the SHORTER extent: that is the length",
          (g.length, g.width, g.grain), (300, 1200, 1))
    g = line(panel(board="WOOD", a=1200, b=300, grain_along="a"))[0]
    check("grain along the longer one: so is that", (g.length, g.width, g.grain),
          (1200, 300, 1))
    pl = line(panel(board="MEL", a=300, b=1200, grain_along="b"))[0]
    check("a plain board ignores it and takes the longer extent, unlocked",
          (pl.length, pl.width, pl.grain), (1200, 300, 0))

    print("\nlong and short edges are not edge_l and edge_w, so they are mapped")
    e = line(panel(board="MEL", a=900, b=400, edge_kind="pvc",
                   edge_long=2, edge_short=1))[0]
    check("length is the longer side: long edges are the L ones",
          (e.length, e.width, e.edge_l, e.edge_w), (900, 400, 2, 1))
    e = line(panel(board="WOOD", a=900, b=400, grain_along="b", edge_kind="pvc",
                   edge_long=2, edge_short=1))[0]
    check("cut across the grain, the long edges run the WIDTH",
          (e.length, e.width, e.edge_l, e.edge_w), (400, 900, 1, 2))
    check("and the edging metres follow the sizes, not the labels",
          round(e.edging_m(), 3), round((1 * 400 + 2 * 900 + 70 * 3) / 1000.0, 3))

    # ---- edging comes from the Boards record, or not at all ---------------
    print("\nD6 — edging is the Boards record's answer, and nothing is invented")
    b = line(panel(board="BARE", a=900, b=400, edge_kind="2mm", edge_long=2))[0]
    check("a board with Has Edging off bands nothing and names nothing",
          (b.edge_l, b.edge_w, b.edge_material), (0, 0, ""))
    b = line(panel(board="TWOMM", a=900, b=400, edge_kind="pvc", edge_long=2))[0]
    check("nor does a kind the board does not offer", (b.edge_l, b.edge_material),
          (0, ""))
    b = line(panel(board="MEL", a=900, b=400, edge_kind="pvc", edge_board="WOOD",
                   edge_long=1))[0]
    check("the colour may be another board, and the name is that board's",
          b.edge_material, "PVC WOOD")
    b = line(panel(board="THIN", a=900, b=400))[0]
    check("a 3 mm sheet is a perfectly good panel — it is not a carcass",
          (b.material, b.length, b.width), ("THIN", 900, 400))

    # ---- D5: geometry per orientation -------------------------------------
    print("\nD5 — the third extent is the board's thickness, and orientation says where")
    for orient, want in (("upright", (1200, 16, 300)),
                         ("flat", (1200, 300, 16)),
                         ("end", (16, 1200, 300))):
        gm = geometry(panel(board="MEL", orientation=orient, a=1200, b=300),
                      materials=MATS)
        check(f"{orient}: width, depth, height", (gm.width, gm.depth, gm.height), want)
        check(f"{orient}: and it says where that came from", gm.source, "panel")
    check("the orientations the editor offers are the ones the model knows",
          sorted(PANEL_ORIENTATIONS), ["end", "flat", "upright"])
    gm = geometry(panel(board="THIN", orientation="upright", a=800, b=600),
                  materials=MATS)
    check("depth is the board's real thickness, not an assumed 16", gm.depth, 3)
    check("declared width/height/depth are labels — geometry reads none of them",
          (geometry(Cabinet(number=2, width=999, height=999, depth=999, kind="panel",
                            panel=PanelSpec(board="MEL", a=400, b=500)),
                    materials=MATS).width), 400)

    # ---- D1 / D4: switching kind keeps everything -------------------------
    print("\nD1 — switching kind keeps every field, and the number never moves")
    cab = Cabinet(number=7, width=600, height=780, depth=570, kind="base",
                  template="none", doors=2, shelves=3,
                  drawers=[Drawer(face_height=150, box_height=120)],
                  support_rows=[Support(edge="front", qty=2)],
                  bespoke=[Panel(7, "01", "Side", "MEL", 700, 500)])
    before = [(x.label, x.role, x.length, x.width) for x in line(cab)]
    cab.kind = "panel"
    cab.panel = PanelSpec(board="MEL", a=1000, b=200)
    mid = [(x.label, x.role) for x in line(cab)]
    cab.kind = "base"
    after = [(x.label, x.role, x.length, x.width) for x in line(cab)]
    check("as a panel it cuts one line, its own", mid, [("708", "Panel")])
    check("and back again it cuts exactly what it cut before", after, before)
    check("the number never changed", cab.number, 7)
    check("nor did its template — there is nothing to reconstruct it from",
          cab.template, "none")
    check("and every cupboard field is still there",
          (cab.doors, cab.shelves, len(cab.drawers), len(cab.support_rows),
           len(cab.bespoke)), (2, 3, 1, 1, 1))
    check("the panel record is kept too, so switching back and forth is free",
          (cab.panel.board, cab.panel.a, cab.panel.b), ("MEL", 1000, 200))
    check("is_panel reads kind and nothing else",
          (Cabinet(1, 1, 1, 1, kind="panel").is_panel,
           Cabinet(1, 1, 1, 1, kind="base").is_panel), (True, False))

    # ---- D1: the job file -------------------------------------------------
    print("\nD1 — a job with no panels writes exactly what it always wrote")
    plain = Cabinet(number=1, width=600, height=780, depth=570)
    check("no panel key on an ordinary cabinet", "panel" in cabinet_to_dict(plain), False)
    d = cabinet_to_dict(panel(3, board="WOOD", orientation="flat", a=1200, b=580,
                              grain_along="a"))
    check("a panel writes its record", d["panel"]["board"], "WOOD")
    check("and not the reserved anchor, which nothing reads yet",
          "anchor" in d["panel"], False)
    back = cabinet_from_dict(d)
    check("which reads back identically", cabinet_to_dict(back), d)
    check("a job file that predates panels reads as no panel",
          cabinet_from_dict({"number": 1, "width": 600, "height": 780,
                             "depth": 570}).panel, None)

    # ---- D2: what a panel stays out of ------------------------------------
    print("\nD2 — a panel is not a carcass, and the cabinet checks leave it alone")
    pan = panel(2, board="MEL", a=1200, b=300)
    # a panel carrying a whole cupboard's worth of hidden settings
    loaded = panel(3, board="MEL", a=1200, b=300)
    loaded.drawers = [Drawer(face_height=0, box_height=120)]   # would be a critical
    loaded.doors = 2
    loaded.width = 0                                           # would be a critical
    loaded.supports, loaded.edged_supports, loaded.white_supports = 0, 2, 2
    j = job_of(pan, loaded)
    issues = validate(j, generate_job(j))
    check("a hidden drawer stack on a panel raises nothing",
          [i.message for i in issues if i.where == "3"], [])
    check("nor does anything else it is carrying but not building",
          [i.level for i in issues], [])
    check("placed() is cabinets only", placed(job_of(pan)), [])
    check("a panel stands on no legs",
          stands_on_legs(pan, type("P", (), {"z": 0, "layer": ""})()), False)
    check("the Run drawing leaves it out",
          elevation_svg(job_of(pan)).count("No cabinets yet"), 1)
    cup = Cabinet(number=1, width=600, height=780, depth=570, doors=1,
                  carcass_board="MEL", exterior_board="WOOD", back_board="THIN")
    check("the Run draws the cupboards beside it, and only those",
          elevation_svg(job_of(cup, pan)) == elevation_svg(job_of(cup)), True)
    check("and the edging legend names no panel",
          tape_legend(job_of(cup, pan)) == tape_legend(job_of(cup)), True)

    # ---- D6: what a panel is held to --------------------------------------
    print("\nD6 — and what only a panel can get wrong")

    def issues_for(cab):
        j = job_of(cab)
        return [(i.level, i.ref, i.message) for i in validate(j, generate_job(j))
                if i.where == str(cab.number)]

    check("a well-formed panel that is nowhere is not a fault — cut-only is normal",
          issues_for(panel(2, board="MEL", a=1200, b=300)), [])
    check("no board at all is a critical",
          [m for _, _, m in issues_for(panel(2, a=1200, b=300))],
          ["panel with no board — pick what it is cut from in Panel design"])
    check("a size of zero is a critical",
          [m for _, _, m in issues_for(panel(2, board="MEL", a=0, b=300))],
          ["panel size a is 0 — both extents have to be a real finished size"])
    bad = issues_for(panel(2, board="TWOMM", a=900, b=400, edge_kind="pvc",
                           edge_long=1))
    check("an edging the board does not offer is a critical, tagged EDGING",
          [(lv, ref) for lv, ref, _ in bad], [("critical", "EDGING")])
    check("and it says what to tick", "tick that kind on TWOMM" in bad[0][2], True)
    check("asking for a kind but banding no edges asks for nothing, so it is clear",
          issues_for(panel(2, board="TWOMM", a=900, b=400, edge_kind="pvc")), [])
    check("an orientation the model does not know is a critical",
          [ref for _, ref, _ in issues_for(panel(2, board="MEL", a=9, b=9,
                                                 orientation="sideways"))], [""])

    # ---- B1 / B4: the panel's boards are board_refs' -----------------------
    print("\nB — the one list of which fields hold a board knows about a panel")
    pb = panel(2, board="WOOD", a=900, b=400, edge_kind="2mm", edge_board="MEL")
    labels = {lab: key for key, lab in pb.board_refs()}
    check("the panel's own board is named", labels.get("panel board"), "WOOD")
    check("and its edging colour", labels.get("panel edging board"), "MEL")
    moved = pb.map_board_refs(lambda b: "NEW" if b in ("WOOD", "MEL") else b)
    check("a rename moves both", sorted(m for m in moved if "panel" in m),
          ["panel board", "panel edging board"])
    check("the raw-JSON scan sees them too",
          sorted(B.cabinet_board_ids(cabinet_to_dict(
              panel(2, board="WOOD", edge_board="MEL", a=1, b=1)))),
          ["BACK", "BROOKHILL", "MEL", "WOOD"])

    # ---- the whole fixture -------------------------------------------------
    print("\nD9 — the fixture, end to end")
    path = os.path.join(ROOT, "jobs", "Test_Panels.json")
    if not os.path.exists(path):
        check("jobs/Test_Panels.json is there", False, True)
    else:
        fix = load(path)
        panels = generate_job(fix)
        check("it carries one of each orientation",
              sorted({c.panel.orientation for c in fix.cabinets if c.is_panel}),
              ["end", "flat", "upright"])
        lines = {p.label: p for p in panels if p.role == "Panel"}
        check("one cut-list line per panel, each its own number",
              sorted(lines), ["208", "308", "408", "508", "608", "708"])
        check("every one of them is coded 08",
              sorted({p.code for p in lines.values()}), [PANEL_CODE])
        check("the grained ones are locked and the plain ones are not",
              {k: v.grain for k, v in sorted(lines.items())},
              {"208": 1, "308": 1, "408": 0, "508": 0, "608": 0, "708": 0})
        check("the bulkhead front is 1200 x 300, banded on one long edge",
              (lines["208"].length, lines["208"].width, lines["208"].edge_l,
               lines["208"].edge_material), (1200, 300, 1, "2mm BROOKHILL"))
        check("the 3 mm panel carries no edging, because its board offers none",
              (lines["708"].material, lines["708"].edge_material), ("BACK", ""))
        check("the fixture is clean", [i.message for i in validate(fix, panels)], [])
        check("it round-trips through the job file",
              job_to_dict(job_from_dict(job_to_dict(fix))) == job_to_dict(fix), True)
        check("and a panel takes its turn in the numbering",
              next_number(fix), 8)

        print("\n  generate_job is still read-only with respect to the job")
        before = json.dumps(job_to_dict(fix), sort_keys=True)
        generate_job(fix)
        generate_job(fix)
        check("two cut lists later, the job is untouched",
              json.dumps(job_to_dict(fix), sort_keys=True) == before, True)

    # ---- the three fixed jobs have not moved -------------------------------
    print("\nand a job with no panels is exactly what it was")
    for name in ("Test", "Test_Build"):
        path = os.path.join(ROOT, "jobs", name + ".json")
        if not os.path.exists(path):
            check(f"{name}.json is there", False, True)
            continue
        with open(path, encoding="utf-8") as fh:
            raw = json.load(fh)
        job = job_from_dict(raw)
        check(f"{name}: no cabinet is a panel",
              any(c.is_panel for c in job.cabinets), False)
        check(f"{name}: and it writes back byte for byte",
              json.dumps(job_to_dict(job), indent=2, ensure_ascii=False)
              == json.dumps(raw, indent=2, ensure_ascii=False), True)

    print()
    if FAILS:
        print(f"{len(FAILS)} FAILED: {FAILS}")
        sys.exit(1)
    print("ALL OK")


if __name__ == "__main__":
    main()
