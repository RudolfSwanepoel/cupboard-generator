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
                              Drawer, Job, Panel, PanelSpec, Placement,
                              Support)
from cabinetgen.render import elevation_svg, tape_legend                 # noqa: E402
from cabinetgen.room import (cabinet_footprint, clashes as room_clashes,  # noqa: E402
                             free_x, geometry, panel_clashes, placed,
                             placed_panels, rectangular, snap_points,
                             stands_on_legs, tip_problems, z_snap_points)
from cabinetgen.store import (cabinet_from_dict, cabinet_to_dict,        # noqa: E402
                              job_from_dict, job_to_dict, load, next_number,
                              placement_to_dict)
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

    # ---- E: placing a panel ------------------------------------------------
    print("\nE — a panel has a place in the room, and the cabinets do not notice")

    def bulkhead():
        """Wall A: two base units, and a bulkhead of four panels capping them.

        Front upright, underside flat, an end cap each side — each its own
        number, which is the whole reason a bulkhead is several panels rather
        than one part with a shape.
        """
        cups = [Cabinet(number=n, width=600, height=780, depth=570, doors=1,
                        carcass_board="MEL", exterior_board="WOOD",
                        back_board="THIN")
                for n in (1, 2)]
        pans = [panel(3, board="WOOD", orientation="upright", a=1200, b=400),
                panel(4, board="MEL", orientation="flat", a=1200, b=570),
                panel(5, board="MEL", orientation="end", a=570, b=400),
                panel(6, board="MEL", orientation="end", a=570, b=400)]
        j = job_of(*(cups + pans))
        j.room = rectangular(4000, 3000, ceiling=2700)
        # The two units on the floor, the bulkhead capping them: 780 high on
        # 100 mm legs, so its underside is at 880. The end caps sit BEHIND the
        # front, at y = 16 — which is exactly what y is for, and without it they
        # would genuinely be in the same space as the front and say so.
        j.placements = [Placement(1, "A", 0), Placement(2, "A", 600),
                        Placement(3, "A", 0, z=880),
                        Placement(4, "A", 0, z=1280),
                        Placement(5, "A", 0, z=880, y=16),
                        Placement(6, "A", 1184, z=880, y=16)]
        return j

    j = bulkhead()
    plain = job_of(*[c for c in j.cabinets if not c.is_panel])
    plain.room, plain.placements = j.room, j.placements[:2]
    check("placed() returns the cabinets and only the cabinets, in order",
          [c.number for c, _p, _l in placed(j)], [1, 2])
    check("and exactly what it returned before the panels were placed",
          [(c.number, p.x, lay) for c, p, lay in placed(j)],
          [(c.number, p.x, lay) for c, p, lay in placed(plain)])
    check("placed_panels() is the other four",
          [c.number for c, _p in placed_panels(j)], [3, 4, 5, 6])
    check("an unplaced panel is simply not in it — cut-only is normal",
          [c.number for c, _p in placed_panels(job_of(panel(9, board="MEL",
                                                            a=10, b=10)))], [])
    check("tip-up is unmoved by them", tip_problems(j), tip_problems(plain))
    check("and so is the door swing",
          [(c.cabinet, c.against) for c in room_clashes(j)],
          [(c.cabinet, c.against) for c in room_clashes(plain)])

    print("\n  x, y and z, and the third extent that is the board's own thickness")
    g = {c.number: geometry(c, j.std, j.materials) for c, _p in placed_panels(j)}
    check("upright: along the wall, thick, up",
          (g[3].width, g[3].depth, g[3].height), (1200, 16, 400))
    check("flat: along the wall, out from the wall, thick",
          (g[4].width, g[4].depth, g[4].height), (1200, 570, 16))
    check("end: thick, out from the wall, up",
          (g[5].width, g[5].depth, g[5].height), (16, 570, 400))
    check("z is the underside exactly as typed — a panel stands on no legs",
          [p.z for _c, p in placed_panels(j)], [880, 1280, 880, 880])
    front = next(c for c in j.cabinets if c.number == 3)
    at0 = cabinet_footprint(j.room, Placement(3, "A", 0), front, j.std, j.materials)
    at60 = cabinet_footprint(j.room, Placement(3, "A", 0, y=60), front, j.std,
                             j.materials)
    check("y moves the footprint out from the wall, and nothing else",
          [(x, y - 60) for x, y in at60], at0)

    print("\n  the job file: y is written only when it is not zero")
    check("a cabinet placement says exactly what it always said",
          placement_to_dict(Placement(1, "A", 300)),
          {"cabinet": 1, "wall": "A", "x": 300, "z": 0, "flip": False,
           "layer": None})
    check("and a panel standing off the wall says so",
          placement_to_dict(Placement(4, "A", 0, z=1280, y=60)).get("y"), 60)
    check("the bulkhead round-trips through save and load",
          job_to_dict(job_from_dict(job_to_dict(j))) == job_to_dict(j), True)
    back = job_from_dict(job_to_dict(j))
    check("with every y intact", [p.y for p in back.placements],
          [0, 0, 0, 0, 16, 16])
    check("and only the placements that need one carry the key",
          [("y" in placement_to_dict(p)) for p in j.placements],
          [False, False, False, False, True, True])

    print("\n  what a panel may come to rest on")
    tops = {s["why"] for s in z_snap_points(j, 3, "A", j.std, spans=True)}
    check("a bulkhead front lands on the cabinet tops below it",
          ("on top of 1" in tops, "on top of 2" in tops), (True, True))
    check("and on the floor and the ceiling",
          ("on the floor" in tops, "tight to the ceiling" in tops), (True, True))
    check("the underside lands on the front panel beside it",
          "on top of 3" in {s["why"] for s in
                            z_snap_points(j, 4, "A", j.std, spans=True)}, True)
    xs = {s["why"]: s["x"] for s in snap_points(j, 6, "A", j.std)}
    check("sideways, an end cap butts the panels it is up there with",
          (xs.get("right of 3"), xs.get("right of 5")), (1200, 16))
    check("and not the cabinets a course below it — heights decide, as ever",
          [w for w in xs if w.endswith(" of 1") or w.endswith(" of 2")], [])
    low = bulkhead()
    low.placements[5] = Placement(6, "A", 2000)             # down on the floor
    check("brought down beside the run, it butts the run",
          {s["why"]: s["x"] for s in snap_points(low, 6, "A", low.std)
           }.get("right of 2"), 1200)
    check("a cabinet's own sideways snaps are what they were with no panels",
          snap_points(j, 1, "A", j.std), snap_points(plain, 1, "A", j.std))
    unplaced = bulkhead()
    unplaced.placements = unplaced.placements[:2]
    check("and its heights are, while the panels are only cut and not placed",
          z_snap_points(j, 1, "A", j.std) == z_snap_points(unplaced, 1, "A", j.std),
          False)
    check("...where 'only cut' is the same job as one with no panels in it",
          z_snap_points(unplaced, 1, "A", j.std),
          z_snap_points(plain, 1, "A", j.std))
    check("placed, the bulkhead is something for a cabinet to come up under",
          "under 3" in {s["why"] for s in z_snap_points(j, 1, "A", j.std,
                                                        spans=True)}, True)

    print("\n  a clash is a WARNING: a panel is cut and costed wherever it is")
    check("a bulkhead sitting flush on the run is not a clash", panel_clashes(j), [])
    into = bulkhead()
    into.placements[2] = Placement(3, "A", 0, z=400)        # down into the units
    hits = panel_clashes(into)
    check("a panel driven down into the cabinets is",
          sorted(c.against for c in hits), ["cabinet 1", "cabinet 2"])
    check("reported against the panel, on its wall",
          sorted({(c.panel, c.wall) for c in hits}), [(3, "A")])
    issues = [i for i in validate(into, generate_job(into)) if i.where == "3"]
    check("and it warns rather than blocking — no cut changes",
          sorted({i.level for i in issues}), ["warning"])
    check("the cut list itself is identical either way",
          [p.label for p in generate_job(into)], [p.label for p in generate_job(j)])
    two = bulkhead()
    two.placements[4] = Placement(5, "A", 100, z=880)   # cap in front of the front
    check("panel against panel is caught too",
          sorted(c.against for c in panel_clashes(two) if c.panel == 3), ["panel 5"])
    check("which is the y that was holding it clear, and nothing else",
          [c.against for c in panel_clashes(two) if c.panel == 3
           and c.against == "panel 6"], [])

    print("\n  E8 — a new placement lands clear of what is already there")
    empty = bulkhead()
    empty.placements = []
    check("nothing on the wall: it starts at the corner",
          free_x(empty, 1, "A", empty.std), 0)
    one = bulkhead()
    one.placements = [Placement(1, "A", 0)]
    check("one unit there: the next goes beside it, not on top of it",
          free_x(one, 2, "A", one.std), 600)
    check("and a panel is kept clear of the run as well",
          free_x(one, 3, "A", one.std), 600)
    apart = bulkhead()
    apart.placements = [Placement(1, "A", 0), Placement(2, "A", 1800)]
    check("a gap wide enough in the middle is used before the end",
          free_x(apart, 3, "A", apart.std), 600)
    tight = bulkhead()
    tight.placements = [Placement(1, "A", 0), Placement(2, "A", 700)]
    check("a gap too narrow for it is passed over",
          free_x(tight, 3, "A", tight.std), 1300)
    check("and a narrow item does fit that same gap",
          free_x(tight, 5, "A", tight.std), 600)

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
