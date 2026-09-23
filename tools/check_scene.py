"""The 3D scene (`cabinetgen/scene.py`, `/api/scene`) — Part F, 23 September 2026.

What is pinned here, from the brief:

  * ids are unique, and identical across two calls on the same job;
  * for every template cabinet in every job on disk, the union of its carcass
    parts taken back into its own frame is `room.geometry`'s footprint and
    height, and its fronts stand proud by their board's real thickness;
  * world vertices equal `room.to_world` of the cabinet-local corners, on a
    square room, a NON-square corner and a LEFT-handed corner unit;
  * z includes `carcass_z`: a standing base unit's bottom is at `leg_height`,
    a hung unit's at its own z, a panel's at its typed z;
  * the hinge axis is on the side `model.hinge_side` names — singles, pairs, a
    flipped placement, a per-leaf choice, and a mitre door;
  * every part with a `line` names a designation that exists on that
    cabinet's cut list, and the unmatched count is zero for template cabinets;
  * no part has a role the ruling leaves out (shelf, support, drawer box);
  * no room -> parts in Run order, spacing equal to the Run drawing's;
  * the scene call does not change the job;
  * none of engine, validate, export_plaza, nest, room or store imports scene;
  * the October job's scene builds in well under a second (printed).

And beyond the brief: the backing board is drawn where the engine cuts one and
nowhere else; a chosen plinth board and a chosen filler are drawn where the
plan draws them, tied to their cut-list lines; an unmeasured ceiling stops the
walls a drawing margin above the tallest item; and a board's look is
`render.board_look`'s, the picture only on a grained board.
"""
import copy
import os
import re
import sys
import time

ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, ROOT)

from app import api                                                         # noqa: E402
from cabinetgen import scene as SC                                          # noqa: E402
from cabinetgen.engine import generate_cabinet, generate_job                # noqa: E402
from cabinetgen.model import (Cabinet, GapChoice, Job, Placement,           # noqa: E402
                              PlinthChoice, Room, Wall, hinge_side)
from cabinetgen.render import RUN_GAP, run_layout, PICTURE_TILE_MM          # noqa: E402
from cabinetgen.room import (EXAMPLE_MITRE, geometry, rectangular,          # noqa: E402
                             to_world, carcass_z, placement_for)
from cabinetgen.standard import STANDARD                                    # noqa: E402
from cabinetgen.store import job_to_dict, load                              # noqa: E402
from jobs.wardrobe_oct2025 import JOB as OCT                                # noqa: E402

FAILS = []


def check(name, got, want):
    ok = got == want
    print(f"  {'ok  ' if ok else 'FAIL'}  {name}: {got!r}" + ("" if ok else f"  (wanted {want!r})"))
    if not ok:
        FAILS.append(name)
    return ok


def near(a, b, tol=0.6):
    return abs(a - b) <= tol


def job_files():
    out = {}
    for n in ("Test", "Test_Build", "Test_Panels", "Corner Unit Test"):
        p = os.path.join(ROOT, "jobs", n + ".json")
        if os.path.exists(p):
            out[n] = load(p)
    out["oct2025"] = OCT
    return out


def straight_cab(number, width=600, height=720, depth=560, kind="base", doors=1, **kw):
    return Cabinet(number=number, width=width, height=height, depth=depth, kind=kind,
                   doors=doors, carcass_board="MEL", exterior_board="BROOKHILL",
                   back_board="BACK", **kw)


def main():
    std = STANDARD
    jobs = job_files()

    print("ids, roles, lines — every job on disk and the October fixture")
    for name, job in jobs.items():
        before = job_to_dict(job)
        s1 = SC.build(job)
        s2 = SC.build(job)
        check(f"{name}: the scene call does not change the job", job_to_dict(job) == before, True)
        ids1 = [q["id"] for it in s1["items"] for q in it["parts"]] + [q["id"] for q in s1["room_parts"]]
        ids2 = [q["id"] for it in s2["items"] for q in it["parts"]] + [q["id"] for q in s2["room_parts"]]
        check(f"{name}: ids unique", len(ids1), len(set(ids1)))
        check(f"{name}: and identical across two calls", ids1, ids2)
        roles = {q["role"] for it in s1["items"] for q in it["parts"]}
        check(f"{name}: no shelf, support or drawer-box part", roles & {"shelf", "support", "box", "drawer_box"}, set())
        cabs = {c.number: c for c in job.cabinets}
        bad, unmatched_template = [], []
        for it in s1["items"]:
            c = cabs[it["number"]]
            labels = {p.label for p in generate_cabinet(c, std, job.materials)}
            for q in it["parts"]:
                if q["line"] is not None and q["line"] not in labels:
                    bad.append((it["number"], q["role"], q["line"]))
                if q["line"] is None and c.template != "none" and c.corner_kind != "ell":
                    unmatched_template.append((it["number"], q["role"], q["reason"]))
        check(f"{name}: every line names a designation on that cabinet's cut list", bad, [])
        check(f"{name}: unmatched parts on template cabinets", unmatched_template, [])
        for it in s1["items"]:
            c = cabs[it["number"]]
            has_back = any(q["role"] == "back" for q in it["parts"])
            want = (it["placed"] and not c.is_panel and c.template != "none"
                    and c.corner_kind not in ("mitre", "ell") and c.back != "none")
            if has_back != want:
                bad.append((it["number"], "back", has_back, want))
        check(f"{name}: a backing board exactly where the engine cuts one", bad, [])

    print("\ncarcass parts back in their own frame are room.geometry's footprint and height")
    for name, job in jobs.items():
        if job.room is None:
            continue
        s = SC.build(job)
        cabs = {c.number: c for c in job.cabinets}
        for it in s["items"]:
            c = cabs[it["number"]]
            if not it["placed"] or c.is_panel or c.template == "none" or c.corner_kind == "ell":
                continue
            g = geometry(c, std, job.materials)
            p = placement_for(job, c.number)
            z = carcass_z(c, p, std)
            carc = [q for q in it["parts"] if q["role"] in ("side", "top", "bottom")]
            pts = [v for q in carc for v in SC.local_outline(job, c.number, q["outline"])]
            xs, ys = [x for x, _ in pts], [y for _, y in pts]
            fx = [x for x, _ in g.footprint]
            fy = [y for _, y in g.footprint]
            ok = (near(min(xs), min(fx)) and near(max(xs), max(fx))
                  and near(min(ys), min(fy)) and near(max(ys), max(fy))
                  and near(min(q["z0"] for q in carc), z) and near(max(q["z1"] for q in carc), z + g.height))
            check(f"{name} cabinet {c.number}: carcass union = footprint {g.width}x{g.depth}, height {g.height} at z {z}", ok, True)
            for q in it["parts"]:
                if q["role"] in ("door", "drawer", "blind") and c.corner_kind != "mitre":
                    loc = SC.local_outline(job, c.number, q["outline"])
                    t = s["looks"][q["board"]]["thickness"] or std.board_t
                    ymax, ymin = max(y for _, y in loc), min(y for _, y in loc)
                    if q["role"] == "blind":
                        ok = near(ymax, g.depth) and near(ymax - ymin, t)
                    else:
                        ok = near(ymin, g.depth) and near(ymax - ymin, t)
                    if not ok:
                        check(f"{name} cabinet {c.number} {q['id']} stands proud by its board's thickness", (round(ymin, 1), round(ymax, 1)), (g.depth, g.depth + t))
        check(f"{name}: fronts stand proud by their board's real thickness", [f for f in FAILS if "proud" in f], [])

    print("\nworld vertices are room.to_world of the cabinet-local corners")
    rm = rectangular(4000, 3000)
    rm.walls[0].offset_end = 60                      # a corner well out of square
    rm.ceiling = 2600
    job = Job(name="w", room=rm, cabinets=[straight_cab(1), straight_cab(2, kind="upper", height=720)],
              placements=[Placement(1, "B", 500), Placement(2, "B", 500, z=1400)])
    s = SC.build(job)
    for it in s["items"]:
        c = job.cabinets[it["number"] - 1]
        p = placement_for(job, c.number)
        for q in it["parts"]:
            if q["role"] != "side":
                continue
            loc = SC.local_outline(job, c.number, q["outline"])
            want = [to_world(rm, p.wall, p.x + int(round(lx)), int(round(ly)))[:2] for lx, ly in loc]
            ok = all(near(a[0], b[0]) and near(a[1], b[1]) for a, b in zip(q["outline"], want))
            check(f"non-square corner, cabinet {c.number} {q['id']}: vertices = to_world of local corners", ok, True)
    check("a hung unit's bottom is at its own z", [q["z0"] for q in s["items"][1]["parts"] if q["role"] == "bottom"], [1400])
    check("a standing base unit's bottom is at leg_height", [q["z0"] for q in s["items"][0]["parts"] if q["role"] == "bottom"], [std.leg_height])

    mitre_l = copy.deepcopy(EXAMPLE_MITRE)
    mitre_l.corner_hand = "L"
    mitre_l.carcass_board, mitre_l.exterior_board = "MEL", "BROOKHILL"
    rm2 = rectangular(4000, 3000)
    rm2.ceiling = 2600
    job2 = Job(name="l", room=rm2, cabinets=[mitre_l], placements=[Placement(7, "B", 0)])
    s2 = SC.build(job2)
    g7 = geometry(mitre_l, std)
    parts7 = s2["items"][0]["parts"]
    for q in parts7:
        loc = SC.local_outline(job2, 7, q["outline"])
        want = [to_world(rm2, "B", int(round(lx)), int(round(ly)))[:2] for lx, ly in loc]
        ok = all(near(a[0], b[0]) and near(a[1], b[1]) for a, b in zip(q["outline"], want))
        if not ok:
            check(f"left-handed mitre {q['id']}: vertices = to_world of local corners", ok, True)
    check("left-handed mitre: every part's vertices are to_world of its local corners", [f for f in FAILS if "left-handed" in f], [])
    pts = [v for q in parts7 if q["role"] in ("side", "top", "bottom") for v in SC.local_outline(job2, 7, q["outline"])]
    check("left-handed mitre: carcass union spans the footprint",
          (near(min(x for x, _ in pts), 0), near(max(x for x, _ in pts), g7.width), near(max(y for _, y in pts), g7.depth)), (True, True, True))

    print("\nthe hinge axis is on the side model.hinge_side names")
    def hinge_end(job, number, leaf):
        s = SC.build(job)
        it = next(i for i in s["items"] if i["number"] == number)
        door = next(q for q in it["parts"] if q["role"] == "door" and q["index"] == leaf)
        loc = SC.local_outline(job, number, door["outline"])
        hx, hy = SC._from_plan(SC._placed_frame(job.room, placement_for(job, number)), door["hinge"]["axis"][0][:2])
        xs = [x for x, _ in loc]
        return ("L" if abs(hx - min(xs)) < abs(hx - max(xs)) else "R",
                door["hinge"]["angle"], near(door["hinge"]["axis"][1][2], door["z1"]))
    rm3 = rectangular(4000, 3000)
    rm3.ceiling = 2600
    single = straight_cab(1, doors=1)
    pair = straight_cab(2, width=900, doors=2)
    chosen = straight_cab(3, doors=1, door_hinges=["R"])
    mitre = copy.deepcopy(EXAMPLE_MITRE)
    mitre.carcass_board, mitre.exterior_board = "MEL", "BROOKHILL"
    job3 = Job(name="h", room=rm3, cabinets=[single, pair, chosen, mitre],
               placements=[Placement(1, "A", 0), Placement(2, "A", 700), Placement(3, "A", 1700),
                           Placement(7, "B", 0)])
    check("single door hinges left by default", hinge_end(job3, 1, 0), ("L", std.door_open_deg, True))
    job3.placements[0].flip = True
    check("flipped, it hinges right, and the turn is the other way", hinge_end(job3, 1, 0), ("R", -std.door_open_deg, True))
    check("a pair hinges at its outer edges", (hinge_end(job3, 2, 0)[0], hinge_end(job3, 2, 1)[0]), ("L", "R"))
    check("a per-leaf choice wins", hinge_end(job3, 3, 0)[0], hinge_side(chosen, 0, 1, False))
    check("the mitre door hinges on the side hinge_side names", hinge_end(job3, 7, 0)[0], hinge_side(mitre, 0, 1, False))
    job3.placements[3].flip = True
    check("and on the other side when flipped", hinge_end(job3, 7, 0)[0], hinge_side(mitre, 0, 1, True))

    print("\nno room: the Run's order and spacing")
    for name in ("Test_Build", "Test_Panels", "oct2025"):
        job = jobs[name]
        s = SC.build(job)
        got = [(it["number"], it.get("x")) for it in s["items"] if it["placed"]]
        want = [(c.number, x) for c, x in run_layout(job)]
        check(f"{name}: parts in Run order at the Run's x", got, want)
        check(f"{name}: with the banner saying there is no room", "no room" in s["banner"], True)
        check(f"{name}: panels are not stood in the Run", [it["number"] for it in s["items"] if it["panel"] and it["placed"]], [])
    check("the Run's gap is the drawing's", RUN_GAP, 20)
    s = SC.build(jobs["Test_Build"])
    xs = [it["x"] for it in s["items"]]
    ws = [it["dims"]["width"] for it in s["items"]]
    check("consecutive cabinets are one width plus the gap apart",
          [b - a for a, b in zip(xs, xs[1:])], [w + RUN_GAP for w in ws[:-1]])

    print("\nplinth boards and fillers that were chosen")
    rm4 = rectangular(4000, 3000)
    rm4.ceiling = 2600
    job4 = Job(name="p", room=rm4,
               cabinets=[straight_cab(1, width=900, depth=580), straight_cab(2, depth=580)],
               placements=[Placement(1, "A", 0), Placement(2, "A", 1000)],
               gaps=[GapChoice(wall="A", after=1, before=2, layer="base", treatment="filler")],
               plinths=[PlinthChoice(wall="A", layer="base", first=1, fitted=True)])
    s4 = SC.build(job4)
    roles = sorted(q["role"] for q in s4["room_parts"])
    check("one plinth board and one filler", roles, ["filler", "plinth"])
    labels = {p.label: p for p in generate_job(job4) if p.cabinet == 0}
    for q in s4["room_parts"]:
        check(f"the {q['role']} names its cut-list line", q["line"] in labels, True)
    pl = next(q for q in s4["room_parts"] if q["role"] == "plinth")
    ys = [y for _, y in pl["outline"]]
    check("the plinth face stands plinth_setback behind the run's front, one board thick",
          (max(ys), max(ys) - min(ys)), (580 - std.plinth_setback, std.board_t))
    check("from the floor to leg_height", (pl["z0"], pl["z1"]), (0, std.leg_height))
    check("and runs the whole run", (min(x for x, _ in pl["outline"]), max(x for x, _ in pl["outline"])), (0, 1600))
    fl = next(q for q in s4["room_parts"] if q["role"] == "filler")
    check("the filler stands in the gap, on the legs, the cabinets' height",
          (min(x for x, _ in fl["outline"]), max(x for x, _ in fl["outline"]), fl["z0"], fl["z1"]),
          (900, 1000, std.leg_height, std.leg_height + 720))
    job4.gaps[0].treatment = ""
    job4.plinths[0].fitted = False
    check("undecided gap and no plinth board: nothing drawn", SC.build(job4)["room_parts"], [])

    print("\nthe room shell")
    rm5 = rectangular(4000, 3000)
    job5 = Job(name="c", room=rm5, cabinets=[straight_cab(1, height=2100, kind="tall")],
               placements=[Placement(1, "A", 0)])
    s5 = SC.build(job5)
    check("no ceiling: the walls stop a drawing margin above the tallest item",
          (s5["ceiling_measured"], s5["room"]["top"]), (False, std.leg_height + 2100 + SC.DRAWING_MARGIN))
    rm5.ceiling = 2500
    s5 = SC.build(job5)
    check("a measured ceiling is the top", (s5["ceiling_measured"], s5["room"]["top"]), (True, 2500))
    check("the floor is the corner chain", len(s5["room"]["floor"]), 5)
    rm5.walls[0].openings.append(type("O", (), {})())
    from cabinetgen.model import Opening, Obstruction
    rm5.walls[0].openings = [Opening("window", 1000, 1200, 900, 2100)]
    rm5.walls[1].obstructions = [Obstruction("waste", 500, 300, proud=40)]
    s5 = SC.build(job5)
    op = s5["room"]["walls"][0]["openings"][0]
    check("an opening carries its jambs as world points and its sill and head",
          (op["p0"], op["p1"], op["sill"], op["head"]), ([1000.0, 0.0], [2200.0, 0.0], 900, 2100))
    ob = s5["room"]["walls"][1]["obstructions"][0]
    check("an obstruction carries its centre on the wall face and how proud it stands",
          (ob["centre"], ob["proud"]), ([4000.0, 500.0], 40))

    print("\nlooks come off the Boards record, and the picture only on a grained board")
    job = jobs["Test"]
    s = SC.build(job)
    from cabinetgen.render import board_look
    for bid, look in s["looks"].items():
        want = board_look(job, bid)
        check(f"{bid}: colour and grain are board_look's", (look["colour"], look["grain"]), (want["colour"], want["grain"]))
        if look["picture"]:
            check(f"{bid}: a picture is sent only on a grained board", look["grain"], True)
        check(f"{bid}: the tile is the one drawing constant", look["tile_mm"], PICTURE_TILE_MM)
    check("no colour literal anywhere in scene.py",
          re.findall(r'"#[0-9a-fA-F]{3,6}"', open(os.path.join(ROOT, "cabinetgen", "scene.py"), encoding="utf-8").read()), [])

    print("\nthe scene is a drawing: nothing reads it back")
    readers = [f for f in ("engine.py", "validate.py", "export_plaza.py", "nest.py", "room.py", "store.py")
               if re.search(r"^\s*(from\s+\.?\s*scene\b|import\s+.*\bscene\b|from\s+\.\s+import\s+.*\bscene\b)",
                            open(os.path.join(ROOT, "cabinetgen", f), encoding="utf-8").read(), re.M)]
    check("none of engine, validate, export_plaza, nest, room, store imports scene", readers, [])
    check("scene reads no drawn hinge positions",
          re.search(r"hinge_positions|hinge_inset_drawn",
                    open(os.path.join(ROOT, "cabinetgen", "scene.py"), encoding="utf-8").read()) is None, True)
    check("/api/scene is routed", "/api/scene" in api.ROUTES, True)
    r = api.scene({"job": job_to_dict(jobs["Test"])})
    check("and answers with the scene", (r["ok"], len(r["items"])), (True, len(jobs["Test"].cabinets)))

    print("\ntiming")
    t0 = time.perf_counter()
    for _ in range(3):
        SC.build(OCT)
    ms = (time.perf_counter() - t0) * 1000 / 3
    print(f"  the October job's scene builds in {ms:.0f} ms")
    check("well under a second", ms < 1000, True)

    print()
    if FAILS:
        print(f"{len(FAILS)} FAILED: " + "; ".join(FAILS))
        sys.exit(1)
    print("ALL OK")


if __name__ == "__main__":
    main()
