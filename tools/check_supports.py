"""Shelves and supports — the agreed spec of 27 September 2026.

What is pinned here, from the build brief's worked numbers, in the spec's
carcass-local frame (x across the width, y from the FRONT face of the sides,
z up from their underside):

  * base W600 H720 D560, back "four": Front y 0-100 z 704-720 flat; Top Rear
    y 441-541 z 704-720 flat; Back 1 y 544-560 z 620-720 upright, edge down;
    Back 2 z 16-116 edge up; with three Backs the middle one z 318-418;
  * the same base with no backing: Top Rear y 460-560; Back 1 z 604-704;
  * tall H2400: Back 1 z 2284-2384, Front and Top Rear not offered;
  * a mitre and an ell take no supports; a blind corner goes by its kind;
  * the cut list: a typed row bands the edges chosen for it (edge_l long
    edges, edge_w ends), a legacy row one long edge as it always did; every
    support is Wi x 100, code 04, whatever its type;
  * the three criticals — a drawer box in the band under a Front / Top Rear,
    Front and Top Rear overlapping in depth, Backs that do not fit — and that
    legacy rows raise none of them;
  * "three" is not offered for a new cabinet and an old job carrying it cuts
    exactly as it did;
  * legacy rows load, save and cut unchanged: Test.json, Test_Build.json and
    the October fixture round-trip byte for byte and cut the same lines;
  * the 3D scene draws one part per rail and per shelf, tied to its cut-list
    line, and a tape band lies INSIDE the finished size on the chosen face;
  * the plan, the wall elevations and `solid_parts` do not move: shelves and
    supports are drawn only in 3D.
"""
import copy
import json
import os
import sys

ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, ROOT)

from app import api                                                      # noqa: E402
from cabinetgen import scene as SC                                       # noqa: E402
from cabinetgen.engine import SUPPORT_W, generate_cabinet, generate_job  # noqa: E402
from cabinetgen.model import (MATERIALS, Cabinet, Drawer, Job, Support,  # noqa: E402
                              support_types_for)
from cabinetgen.render import plan_svg, wall_elevation_svg               # noqa: E402
from cabinetgen.room import (EXAMPLE_MITRE, back_supports_fit,           # noqa: E402
                             interior_parts, shelf_layout, solid_parts,
                             support_layout, tape_solids)
from cabinetgen.standard import STANDARD                                 # noqa: E402
from cabinetgen.store import cabinet_from_dict, cabinet_to_dict, job_to_dict, load  # noqa: E402
from cabinetgen.validate import CRITICAL, validate                       # noqa: E402
from jobs.wardrobe_oct2025 import JOB as OCT                             # noqa: E402

FAILS = []


def check(name, got, want):
    ok = got == want
    print(f"  {'ok  ' if ok else 'FAIL'}  {name}: {got!r}" + ("" if ok else f"  (wanted {want!r})"))
    if not ok:
        FAILS.append(name)
    return ok


def box(**kw):
    kw.setdefault("number", 1)
    kw.setdefault("width", 600)
    kw.setdefault("height", 720)
    kw.setdefault("depth", 560)
    kw.setdefault("kind", "base")
    kw.setdefault("doors", 1)
    kw.setdefault("carcass_board", "MEL")
    kw.setdefault("exterior_board", "BROOKHILL")
    kw.setdefault("back_board", "BACK")
    return Cabinet(**kw)


def typed(front=0, top_rear=0, back=0, **over):
    rows = [Support(type="front", qty=front), Support(type="top_rear", qty=top_rear),
            Support(type="back", qty=back)]
    for r in rows:
        for k, v in over.items():
            setattr(r, k, v)
    return rows


def lay(cab):
    return {(u["type"], u["n"]): (u["y0"], u["y1"], u["z0"], u["z1"], u["upright"], u["faces"]["front"])
            for u in support_layout(cab, STANDARD, MATERIALS)}


def job_of(*cabs):
    return Job(name="s", boards=["MEL", "BROOKHILL", "BACK"], cabinets=list(cabs),
               materials={k: dict(v) for k, v in MATERIALS.items() if k in ("MEL", "BROOKHILL", "BACK")})


def crits(job, check_id):
    return [i for i in validate(job, generate_job(job)) if i.check == check_id and i.level == CRITICAL]


def main():
    std = STANDARD
    print("the worked numbers — base W600 H720 D560, back 'four' (Wi 568, backing face 541)")
    c = box(support_rows=typed(1, 1, 3))
    L = lay(c)
    check("Front: y 0-100, z 704-720, flat", L[("front", 1)][:5], (0, 100, 704, 720, False))
    check("Top Rear: y 441-541, z 704-720, flat", L[("top_rear", 1)][:5], (441, 541, 704, 720, False))
    check("Back 1: y 544-560, z 620-720, upright, edge DOWN", L[("back", 1)], (544, 560, 620, 720, True, "z0"))
    check("Back 2: z 16-116, edge UP", L[("back", 2)], (544, 560, 16, 116, True, "z1"))
    check("three Backs: the middle one z 318-418 (equal 202 gaps)", L[("back", 3)][2:4], (318, 418))
    check("with two Backs there is no middle one", sorted(k for k in lay(box(support_rows=typed(0, 0, 2)))),
          [("back", 1), ("back", 2)])
    check("one Back alone is Back 1, under the top of the sides", lay(box(support_rows=typed(0, 0, 1)))[("back", 1)][2:4], (620, 720))
    check("a Front alone: Back 1 not moved by it", lay(box(support_rows=typed(1, 0, 1)))[("back", 1)][2:4], (620, 720))

    print("\nthe same base with no backing")
    c = box(back="none", support_rows=typed(1, 1, 3))
    L = lay(c)
    check("Top Rear: y 460-560, flush with the back of the sides", L[("top_rear", 1)][:4], (460, 560, 704, 720))
    check("Back 1 hangs under it: z 604-704", L[("back", 1)][2:4], (604, 704))
    check("Back plane is the same with or without a backing", L[("back", 1)][:2], (544, 560))
    c = box(back="none", support_rows=typed(1, 0, 2))
    check("no backing and no Top Rear: Back 1 to the top of the sides", lay(c)[("back", 1)][2:4], (620, 720))

    print("\ntall H2400 (top panel z 2384-2400)")
    c = box(kind="tall", height=2400, support_rows=typed(0, 0, 4))
    L = lay(c)
    check("Back 1 z 2284-2384 under the top panel", L[("back", 1)][2:4], (2284, 2384))
    check("Back 2 on the bottom panel", L[("back", 2)][2:4], (16, 116))
    check("Front and Top Rear not offered on a tall", support_types_for("tall"), ["back"])
    check("nor on a wall unit", support_types_for("upper"), ["back"])
    check("all three on a base", support_types_for("base"), ["front", "top_rear", "back"])
    check("none on a mitre or an ell", (support_types_for("base", "mitre"), support_types_for("tall", "ell")), ([], []))
    check("a blind corner goes by its kind", support_types_for("base", "blind"), ["front", "top_rear", "back"])
    c = box(kind="tall", height=2400, support_rows=typed(1, 1, 2))
    check("a Front stored on a tall is not cut", [r.type for r in c.support_list], ["back"])
    check("and the layout draws none", sorted({u["type"] for u in support_layout(c)}), ["back"])
    j = job_of(c)
    check("but it is named in a warning", [i.check for i in validate(j, generate_job(j)) if i.check == "support-type-off"],
          ["support-type-off", "support-type-off"])
    m = copy.deepcopy(EXAMPLE_MITRE)
    m.support_rows = typed(0, 0, 3)
    check("a mitre draws no supports", support_layout(m), [])
    check("and cuts none", [p for p in generate_cabinet(m) if p.role == "Support"], [])

    print("\nwhat a typed row cuts — Wi x 100, code 04, its chosen edges")
    c = box(support_rows=typed(1, 1, 3, kind="pvc"))
    sup = [p for p in generate_cabinet(c, std, MATERIALS) if p.role == "Support"]
    check("three lines, in type order, one per row", [(p.code, p.qty) for p in sup], [("04", 1), ("04", 1), ("04", 3)])
    check("each Wi x 100", {(p.length, p.width) for p in sup}, {(568, SUPPORT_W)})
    check("default edging: the front long edge only", [(p.edge_l, p.edge_w) for p in sup], [(1, 0)] * 3)
    check("edged in its own board's PVC", {p.edge_material for p in sup}, {"PVC WHITE"})
    rows = typed(1, 0, 2, kind="pvc")
    rows[0].edges = ["front", "rear", "left", "right"]
    rows[2].edges = ["left", "right"]
    sup = [p for p in generate_cabinet(box(support_rows=rows), std, MATERIALS) if p.role == "Support"]
    check("all four edges: edge_l 2, edge_w 2", (sup[0].edge_l, sup[0].edge_w), (2, 2))
    check("ends only: edge_l 0, edge_w 2", (sup[1].edge_l, sup[1].edge_w), (0, 2))
    rows = typed(1, 0, 0)
    rows[0].edges = ["front", "rear"]
    sup = [p for p in generate_cabinet(box(support_rows=rows), std, MATERIALS) if p.role == "Support"]
    check("no edging kind: nothing banded whatever is ticked", (sup[0].edge_l, sup[0].edge_w, sup[0].edge_material), (0, 0, ""))
    rows = typed(0, 0, 1, kind="2mm", board="BROOKHILL", cut_board="MEL")
    sup = [p for p in generate_cabinet(box(support_rows=rows), std, MATERIALS) if p.role == "Support"]
    check("cut from one board, edged in another's 2mm", (sup[0].material, sup[0].edge_material), ("MEL", "2mm WOOD"))
    legacy = [p for p in generate_cabinet(box(support_rows=[Support(edge="front", qty=2)]), std, MATERIALS) if p.role == "Support"]
    check("a legacy row bands one long edge, as it always did", (legacy[0].edge_l, legacy[0].edge_w), (1, 0))

    print("\nthe three criticals, on typed rows only")
    d = box(doors=0, drawers=[Drawer(face_height=237, box_height=150), Drawer(face_height=237, box_height=150),
                              Drawer(face_height=237, box_height=150)], back="none",
            support_rows=typed(1, 0, 2))
    check("boxes clear of the band: no critical", crits(job_of(d), "support-drawer-foul"), [])
    d2 = copy.deepcopy(d)
    d2.drawers[0].box_height = 230          # the top drawer's box: 478 + 230 = 708 > 704
    got = crits(job_of(d2), "support-drawer-foul")
    check("a box into the 16 mm band under the Front is a critical", len(got), 1)
    check("and it blocks the export", api.blocking(validate(job_of(d2), generate_job(job_of(d2)))), True)
    d3 = copy.deepcopy(d2)
    d3.support_rows = typed(0, 0, 2)
    check("with no Front or Top Rear the same box is fine", crits(job_of(d3), "support-drawer-foul"), [])
    d4 = copy.deepcopy(d2)
    d4.support_rows = [Support(edge="front", qty=1), Support(edge="none", qty=2)]
    check("legacy rows raise none of this", crits(job_of(d4), "support-drawer-foul"), [])
    shallow = box(depth=210, support_rows=typed(1, 1, 1))
    check("D 210 with backing: Front and Top Rear overlap (needs 219)", len(crits(job_of(shallow), "support-depth-overlap")), 1)
    check("D 219 with backing: they just clear", crits(job_of(box(depth=219, support_rows=typed(1, 1, 1))), "support-depth-overlap"), [])
    check("D 200 no backing: they just clear", crits(job_of(box(depth=200, back="none", support_rows=typed(1, 1, 1))), "support-depth-overlap"), [])
    check("D 199 no backing: overlap", len(crits(job_of(box(depth=199, back="none", support_rows=typed(1, 1, 1))), "support-depth-overlap")), 1)
    check("Front alone on a shallow carcass: nothing to overlap", crits(job_of(box(depth=150, support_rows=typed(1, 0, 1))), "support-depth-overlap"), [])
    check("seven Backs in 720: need 700, have 704", back_supports_fit(box(support_rows=typed(0, 0, 7))), (700, 704))
    check("  and that is a fit", crits(job_of(box(support_rows=typed(0, 0, 7))), "support-back-fit"), [])
    check("eight do not fit", len(crits(job_of(box(support_rows=typed(0, 0, 8))), "support-back-fit")), 1)
    check("nor do seven under a Top Rear with no backing (Back 1 drops 16)",
          len(crits(job_of(box(back="none", support_rows=typed(0, 1, 7))), "support-back-fit")), 1)

    print("\nback 'three' is legacy: readable, cut as it was, not offered")
    d = api.defaults({})
    check("not offered for a new cabinet", d["backs"], ["four", "none"])
    check("named as legacy", d["backs_legacy"], ["three"])
    three = box(back="three")
    bk = [p for p in generate_cabinet(three, std, MATERIALS) if p.role == "Backing"]
    check("an old job's 'three' still cuts H - 10", (bk[0].length, bk[0].width), (710, 580))
    vanity = [c for c in OCT.cabinets if c.back == "three"]
    check("the benchmark's vanity units still say 'three'", [c.number for c in vanity], [27, 28, 29])

    print("\nlegacy rows load, save and cut unchanged")
    for name in ("Test", "Test_Build", "Corner Unit Test", "Test_Panels"):
        path = os.path.join(ROOT, "jobs", name + ".json")
        if not os.path.exists(path):
            continue
        raw = open(path, encoding="utf-8").read()
        job = load(path)
        again = json.dumps(job_to_dict(job), indent=2, ensure_ascii=False)
        same = json.loads(raw) == json.loads(again)
        check(f"{name}: round-trips with no new keys", same, True)
        typed_cabs = [c.number for c in job.cabinets if c.supports_typed]
        check(f"{name}: no cabinet was silently typed", typed_cabs, [])
    row = Support(edge="front", qty=2)
    d = cabinet_to_dict(box(support_rows=[row]))
    check("a legacy row writes neither type nor edges", sorted(d["support_rows"][0]), ["edge", "qty"])
    t = typed(1, 0, 1)[0]
    d = cabinet_to_dict(box(support_rows=[t]))
    check("a typed row writes its type and not a None edges", sorted(d["support_rows"][0]), ["edge", "qty", "type"])
    t.edges = ["front", "left"]
    d = cabinet_to_dict(box(support_rows=[t]))
    check("edges written once chosen", d["support_rows"][0]["edges"], ["front", "left"])
    back = cabinet_from_dict(d)
    check("and read back", (back.support_rows[0].type, back.support_rows[0].edges), ("front", ["front", "left"]))
    oct_sup = [(p.cabinet, p.label, p.material, p.length, p.width, p.qty, p.edge_l, p.edge_w, p.edge_material)
               for p in generate_job(OCT) if p.role == "Support"]
    check("the October job's support lines", (len(oct_sup), sum(q for *_, q, _a, _b, _c in oct_sup)), (26, 68))
    check("  all one long edge or none, as quoted", {(a, b) for *_, a, b, _c in oct_sup}, {(1, 0), (0, 0)})

    print("\nlegacy rows are only PLACED for drawing: base one Front + Backs, tall all Backs")
    L = lay(box(support_rows=[Support(edge="none", qty=2), Support(edge="front", qty=1), Support(edge="white", qty=1)]))
    check("base: one front-edged rail is the Front", [k for k in L if k[0] == "front"], [("front", 1)])
    check("  and the other three are Backs", sorted(k for k in L if k[0] == "back"), [("back", 1), ("back", 2), ("back", 3)])
    check("  no Top Rear is guessed", [k for k in L if k[0] == "top_rear"], [])
    L = lay(box(kind="tall", height=2400, supports=4))
    check("tall, from the three old numbers: all Backs", sorted(L), [("back", 1), ("back", 2), ("back", 3), ("back", 4)])
    L = lay(box(supports=3, edged_supports=1))
    check("base, old numbers with one front-edged: Front + 2 Backs", sorted(L), [("back", 1), ("back", 2), ("front", 1)])

    print("\nshelves are drawn evenly and nothing validates them")
    c = box(kind="tall", height=2400, shelves=3, fixed_shelves=1)
    sh = shelf_layout(c)
    check("four shelves, fixed first", [s["fixed"] for s in sh], [True, False, False, False])
    gaps = [sh[0]["z0"] - 16] + [sh[i + 1]["z0"] - sh[i]["z1"] for i in range(3)] + [2400 - sh[3]["z1"]]
    check("equal gaps from the bottom panel's top face to the top of the sides", len({round(g, 1) for g in gaps}), 1)
    check("depth off Standard: fixed deeper", (sh[0]["depth"], sh[1]["depth"]), (std.shelf_depth(560, fixed=True), std.shelf_depth(560)))
    parts = interior_parts(c, std, MATERIALS)
    shelves = [(p, t) for p, t in parts if p.role == "shelf"]
    check("each drawn in the carcass board", {p.board for p, _ in shelves}, {"MEL"})
    check("front edge in the exterior board's PVC — the carcass edging", {(t[0].side, t[0].board, t[0].kind) for _, t in shelves}, {("y1", "BROOKHILL", "pvc")})
    check("no shelf issue exists", [i for i in validate(job_of(c), generate_job(job_of(c))) if "shelf" in i.check], [])

    print("\ntape is drawn INSIDE the finished size, and never moves a part")
    rows = typed(1, 0, 1, kind="pvc")
    rows[0].edges = ["front", "rear", "left", "right"]
    c = box(support_rows=rows)
    parts = dict((p.label, (p, t)) for p, t in interior_parts(c, std, MATERIALS))
    p, t = parts["Front"]
    check("the Front rail in the cabinet frame: x 16-584, y 460-560 (the front is at D), z 704-720",
          (p.outline, p.z0, p.z1), ([(16, 460), (584, 460), (584, 560), (16, 560)], 704, 720))
    check("its front edge is the y1 face (the room side), the rear y0", sorted(x.side for x in t), ["x0", "x1", "y0", "y1"])
    bands = tape_solids(p, t, 2)
    inside = all(min(x for x, _ in b.outline) >= 16 and max(x for x, _ in b.outline) <= 584
                 and min(y for _, y in b.outline) >= 460 and max(y for _, y in b.outline) <= 560
                 and b.z0 >= 704 and b.z1 <= 720 for b in bands)
    check("every band lies inside the rail", inside, True)
    check("in the edging board", {b.board for b in bands}, {"MEL"})
    p1, t1 = parts["Back 1"]
    check("Back 1's edged edge faces down (z0)", [x.side for x in t1], ["z0"])
    p2 = parts.get("Back 2")
    check("with one Back there is no Back 2", p2, None)
    unedged = box(support_rows=typed(1, 0, 1))
    up = dict((p.label, p) for p, _ in interior_parts(unedged, std, MATERIALS))
    check("edged or not, the rail is the same size in the same place",
          (up["Front"].outline, up["Front"].z0, up["Front"].z1), (p.outline, p.z0, p.z1))

    print("\nthe 3D scene: a part per rail and per shelf, tied to its line; nothing else moves")
    job = load(os.path.join(ROOT, "jobs", "Test.json"))
    s = SC.build(job)
    inside = [q for it in s["items"] for q in it["parts"] if q["role"] in ("support", "shelf")]
    check("Test.json: supports and shelves are in the scene", len(inside) > 0, True)
    check("every one has its cut-list line", [q["label"] for q in inside if q["line"] is None], [])
    check("the legend no longer lists them as not drawn", "support" in s["not_drawn"] or "helves are drawn" not in s["not_drawn"], False)
    check("the band depth is sent as a drawing constant", s["tape_mm"], SC.TAPE_BAND_MM)
    shelfq = next((q for q in inside if q["role"] == "shelf"), None)
    check("a shelf carries its front-edge band", bool(shelfq and shelfq["tapes"]), True)
    before_solid = [(p.role, p.outline, p.z0, p.z1) for c in job.cabinets for p in solid_parts(c, std, job.materials)]
    check("solid_parts has no shelf or support in it", {r for r, *_ in before_solid} & {"shelf", "support"}, set())
    tj = copy.deepcopy(job)
    for c in tj.cabinets:
        if c.kind == "base" and not c.is_panel and c.template != "none" and c.corner_kind is None:
            c.support_rows = typed(1, 1, 3, kind="pvc")
            break
    wall = tj.room.walls[0].id
    check("typed rows move no wall elevation", wall_elevation_svg(tj, wall) == wall_elevation_svg(job, wall), True)
    check("nor the plan", plan_svg(tj) == plan_svg(job), True)

    print("\nthe API says which types a cabinet takes and where each rail is drawn")
    r = api.compute({"job": job_to_dict(job)})
    g = next(v for k, v in r["geometry"].items() if v["support_types_offered"] == ["front", "top_rear", "back"])
    check("a base offers all three", g["support_types_offered"], ["front", "top_rear", "back"])
    check("legacy rows are reported as not typed", g["supports_typed"], False)
    check("and every row carries its edge counts", all("edge_counts" in x for x in g["supports"]), True)
    check("the layout is given in the spec frame", all(set(u) >= {"type", "n", "y0", "y1", "z0", "z1"} for u in g["support_layout"]), True)

    print()
    if FAILS:
        print(f"{len(FAILS)} FAILED: " + "; ".join(FAILS))
        sys.exit(1)
    print("ALL OK")


if __name__ == "__main__":
    main()
