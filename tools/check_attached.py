"""Attached panels (spec of 28 September 2026), and the new cabinet's supports.

    python tools/check_attached.py

A panel FIXED TO a cabinet: `PanelSpec.attached_to` names the cabinet, and three
offsets place it in the cabinet's own frame — the supports spec's: x across the
width from the left side, y from the FRONT face of the sides towards the back, z
up from their underside. Where that puts it in the room is the cabinet's
placement applied to the offsets (`room.attached_placement`), worked out in one
place, so it moves, snaps and changes wall with the cabinet. What is held here:

* attach and detach are round trips: the number never changes, and the panel
  stands exactly where it stood, both ways;
* moving the cabinet, hanging it, or putting it on another wall moves the panel;
* the room checks read it as part of the cabinet — the run's gap, overlaps
  (critical), door swing, the ceiling — and the tip-up check does NOT;
* cutting into its own carcass is a warning, never a critical;
* deleting the cabinet: "No" leaves standalone panels where they stand (the
  server's `panel_detach`), "Yes" takes them too; duplicating the cabinet copies
  them with new numbers in the one series;
* the job file round-trips `attached_to`, and a standalone panel writes none of
  it — so every job on disk is byte for byte what it was;
* a new cabinet's support rows follow its kind (spec A).

Standalone panels are exactly what they were, and `check_panels.py` still says so.
"""
import copy
import json
import os
import sys

ROOT = os.path.join(os.path.dirname(__file__), "..")
from fixture_jobs import job_file  # noqa: E402  (jobs/ for Test.json, tools/fixtures/ for the rest)
sys.path.insert(0, ROOT)

from app import api                                                       # noqa: E402
from cabinetgen import scene as SC                                        # noqa: E402
from cabinetgen.engine import generate_job                                # noqa: E402
from cabinetgen.model import MATERIALS, Cabinet, Job, PanelSpec, Placement, Room, Wall  # noqa: E402
from cabinetgen.render import plan_svg, wall_elevation_svg                # noqa: E402
from cabinetgen.room import (above_ceiling, attach_offsets, attached_carcass_overlaps,  # noqa: E402
                             attached_panels, attached_placement, cabinet_footprint,
                             clashes, gaps, geometry, host_of, new_attached_panel,
                             overlaps, panel_clashes, placed, placed_panels,
                             placement_for, snap_points, tip_inputs, tip_problems,
                             to_world, y_snap_points, z_snap_points)
from cabinetgen.standard import STANDARD                                  # noqa: E402
from cabinetgen.store import (cabinet_to_dict, job_from_dict, job_to_dict,  # noqa: E402
                              load, next_number)
from cabinetgen.validate import CRITICAL, WARNING, blocking, validate     # noqa: E402

FAILS = []
std = STANDARD


def check(name, got, want):
    ok = got == want
    print(f"  {'ok   ' if ok else 'FAIL '} {name}: {got}" + ("" if ok else f"  want {want}"))
    if not ok:
        FAILS.append(name)


def box(number, x, kind="base", height=720, doors=0, **kw):
    return Cabinet(number=number, width=600, height=height, depth=560, kind=kind,
                   back="four", doors=doors, supports=0, **kw)


def panel(number, a=576, b=720, orientation="end", board="BROOKHILL", **kw):
    return Cabinet(number=number, width=0, height=0, depth=0, kind="panel", supports=0,
                   panel=PanelSpec(board=board, orientation=orientation, a=a, b=b,
                                   grain_along="b", **kw))


def job():
    """Two base units butting on wall A, one with a door on wall A further along,
    and a standalone end panel standing against cabinet 1's left side."""
    rm = Room("r", ceiling=2600, walls=[Wall("A", 0, 0, 4000, 0), Wall("B", 4000, 0, 4000, 3000),
                                        Wall("C", 4000, 3000, 0, 3000), Wall("D", 0, 3000, 0, 0)])
    j = Job("attached", room=rm, materials={k: dict(v) for k, v in MATERIALS.items()},
            boards=["MEL", "BROOKHILL", "BACK"])
    j.cabinets = [box(1, 1000), box(2, 1600), box(3, 3000, doors=1), panel(5)]
    j.placements = [Placement(1, "A", 1000), Placement(2, "A", 1600), Placement(3, "A", 3000),
                    Placement(5, "A", 984, z=100)]
    return j


def issues(j):
    return validate(j, generate_job(j))


def fp(j, n):
    return cabinet_footprint(j.room, placement_for(j, n), next(c for c in j.cabinets if c.number == n),
                             std, j.materials)


def main():
    j = job()
    t = 16
    D = geometry(j.cabinets[0], std, j.materials).depth
    check("the fixture's carcass is 560 deep off its panels", D, 560)

    print("\nmaking one: + Panel on this cabinet (the engine's defaults, off the cabinet)")
    n = next_number(j)
    fresh = new_attached_panel(j, j.cabinets[0], n)
    sp = fresh.panel
    check("it takes the next free number", fresh.number, 4)
    check("an end panel in the exterior board, carcass depth + exposed_extra deep, carcass high",
          (sp.orientation, sp.board, sp.a, sp.b), ("end", "BROOKHILL", 560 + std.exposed_extra, 720))
    check("against the left side, brought forward by the exposed extra, level underneath",
          (sp.attached_to, sp.at_x, sp.at_y, sp.at_z), (1, -t, -std.exposed_extra, 0))
    j.cabinets.append(fresh)
    p = placement_for(j, 4)
    check("its place is derived from the cabinet's: wall A, 16 left of it, back flush, on the legs",
          (p.wall, p.x, p.y, p.z), ("A", 984, 0, 100))
    check("and it is one of the placed panels", [c.number for c, _p in placed_panels(j)], [5, 4])
    check("its cut-list line is a panel's, code 08, its own number",
          [(q.label, q.role, q.length, q.width) for q in generate_job(j) if q.cabinet == 4],
          [("408", "Panel", 720, 576)])
    r = api.panel_new_attached({"job": job_to_dict(j), "index": 0})
    check("/api/panel-new-attached hands the same panel back", (r["ok"], r["number"], r["cabinet"]["panel"]["at_x"]),
          (True, 6, -t))
    r = api.panel_new_attached({"job": job_to_dict(j), "index": 3})
    check("  and refuses a panel as a host", r["ok"], False)

    print("\nattach and detach: the number never changes, and the panel does not move")
    j = job()
    before = fp(j, 5)
    r = api.panel_attach({"job": job_to_dict(j), "cabinet": 5, "to": 1})
    check("/api/panel-attach: offsets worked out from where it stands", (r["ok"], r["number"], r["panel"]["attached_to"],
          r["panel"]["at_x"], r["panel"]["at_y"], r["panel"]["at_z"]), (True, 5, 1, -t, -t, 0))
    j2 = job()
    j2.cabinets[3].panel = PanelSpec(**r["panel"])
    j2.placements = [p for p in j2.placements if p.cabinet != 5]
    check("  attached, its world footprint is exactly what it was", fp(j2, 5), before)
    stale = copy.deepcopy(j2)
    stale.placements.append(Placement(5, "A", 3000, z=900))
    check("  a stale placement record left in the job is never read for it",
          (placement_for(stale, 5).x, placement_for(stale, 5).z), (984, 100))
    d = api.panel_detach({"job": job_to_dict(j2), "cabinet": 5})
    check("/api/panel-detach: standalone again, number kept, standing where it stood",
          (d["ok"], [q["number"] for q in d["panels"]], d["panels"][0]["panel"].get("attached_to"),
           [(q["cabinet"], q["wall"], q["x"], q["z"], q.get("y", 0)) for q in d["placements"]]),
          (True, [5], None, [(5, "A", 984, 100, 0)]))
    j3 = copy.deepcopy(j2)
    j3.cabinets[3].panel = PanelSpec(**d["panels"][0]["panel"])
    j3.placements.append(Placement(**d["placements"][0]))
    check("  detached, the world footprint is still exactly what it was", fp(j3, 5), before)
    check("  and the two ways round leave the job as it started", job_to_dict(j3) == job_to_dict(job()), True)
    # a panel placed on another wall keeps its near corner when attached
    j4 = job()
    j4.placements[3] = Placement(5, "B", 500, z=100)
    corner = fp(j4, 5)
    x, y, z = attach_offsets(j4, j4.cabinets[3], j4.cabinets[0])
    j4.cabinets[3].panel.attached_to, j4.cabinets[3].panel.at_x = 1, x
    j4.cabinets[3].panel.at_y, j4.cabinets[3].panel.at_z = y, z
    after = fp(j4, 5)
    check("attached from another wall, it keeps its place (its box's near corner) and its size",
          (min(q[0] for q in after), max(q[1] for q in after), placement_for(j4, 5).z),
          (min(q[0] for q in corner), max(q[1] for q in corner), 100))
    # an unplaced panel lands beside the cabinet
    j5 = job()
    j5.placements = [p for p in j5.placements if p.cabinet != 5]
    check("an unplaced panel attaches beside the left side, flush and level",
          attach_offsets(j5, j5.cabinets[3], j5.cabinets[0]), (-t, 0, 0))

    print("\nit travels with the cabinet")
    j = job()
    j.cabinets[3].panel.attached_to = 1
    j.cabinets[3].panel.at_x, j.cabinets[3].panel.at_y = -t, -t
    j.placements = [p for p in j.placements if p.cabinet != 5]
    placement_for(j, 1).x = 1200
    check("moved along the wall: the panel goes with it", (placement_for(j, 5).x, placement_for(j, 5).wall), (1184, "A"))
    placement_for(j, 1).wall = "B"
    p = placement_for(j, 5)
    check("onto another wall: the panel changes wall and turns with it", (p.wall, p.x), ("B", 1184))
    want = to_world(j.room, "B", 1184, 0)[:2]
    check("  its world footprint has a corner where wall B's frame puts it", want in fp(j, 5), True)
    j.cabinets[0].kind = "upper"
    placement_for(j, 1).z = 1500
    check("hung: the panel's underside follows the carcass underside", placement_for(j, 5).z, 1500)
    j.cabinets[3].panel.at_z = -100
    check("  an offset below the underside (a plinth end) is honoured", placement_for(j, 5).z, 1400)
    j.cabinets[0].kind = "base"
    placement_for(j, 1).z = 0
    check("standing: the underside is the legs' height plus the offset", placement_for(j, 5).z, 0)
    j.placements = [p for p in j.placements if p.cabinet != 1]
    check("cabinet not placed: nor is its panel", placement_for(j, 5), None)
    check("  and it is not among the placed panels", [c.number for c, _p in placed_panels(j)], [])

    print("\nthe room checks: footprint, overlaps, door swing, ceiling — and not tip-up")
    j = job()
    j.cabinets[3].panel.attached_to = 1
    j.cabinets[3].panel.at_x, j.cabinets[3].panel.at_y = -t, -t
    j.placements = [p for p in j.placements if p.cabinet != 5]
    g = [x for x in gaps(j) if x.after is None and x.wall == "A"]
    check("the run's gap to the corner counts the end panel: 984, not 1000", (g[0].nominal, g[0].before), (984, 1))
    plain = job()
    plain.cabinets.pop(3)
    plain.placements = [p for p in plain.placements if p.cabinet != 5]
    check("  a standalone panel there closes no gap (as before)",
          [x.nominal for x in gaps(job()) if x.after is None and x.wall == "A"], [1000])
    bulk = copy.deepcopy(j)
    bulk.cabinets[3].panel.orientation = "upright"
    bulk.cabinets[3].panel.a, bulk.cabinets[3].panel.b = 2000, 300
    bulk.cabinets[3].panel.at_x, bulk.cabinets[3].panel.at_y, bulk.cabinets[3].panel.at_z = -500, 0, 1000
    check("  a bulkhead attached above the carcass is not in its run",
          [x.nominal for x in gaps(bulk) if x.after is None and x.wall == "A"], [1000])
    check("no overlap while it stands beside the cabinet", overlaps(j), [])
    check("  nor a clash of any kind", (clashes(j), panel_clashes(j), attached_carcass_overlaps(j)), ([], [], []))
    right = copy.deepcopy(j)
    right.cabinets[3].panel.at_x = 600 - 8          # 8 mm into cabinet 2
    o = overlaps(right)
    check("into the neighbour: a CRITICAL overlap naming the panel and the cabinet",
          [(x.a, x.b, x.wall, x.mm) for x in o], [(2, 5, "A", 8)])
    crit = [i for i in issues(right) if i.check == "overlap"]
    check("  the validator says which is which", [(i.level, i.message) for i in crit],
          [(CRITICAL, "cabinet 2 and panel 5 (attached to cabinet 1) overlap by 8 mm on wall A")])
    check("  and it blocks the export", blocking(issues(right)), True)
    check("  panel_clashes does not say it a second time", [(c.panel, c.against) for c in panel_clashes(right)], [])
    own = copy.deepcopy(j)
    own.cabinets[3].panel.at_x = 0                  # inside its own carcass
    check("into its OWN carcass: a warning, not a critical", attached_carcass_overlaps(own), [(5, 1)])
    w = [i for i in issues(own) if i.check == "attached-into-carcass"]
    check("  said once, as a warning naming both", [(i.level, i.where) for i in w], [(WARNING, "5")])
    check("  it does not block", blocking(issues(own)), False)
    check("  and is not an overlap", overlaps(own), [])
    touch = copy.deepcopy(j)
    touch.cabinets[3].panel.at_x = 600              # against the right side of 1 ...
    placement_for(touch, 2).x = 1616                # ... and cabinet 2 moved up against it
    check("touching both cabinets is clear, as everywhere", (overlaps(touch), attached_carcass_overlaps(touch)), ([], []))
    swing = copy.deepcopy(j)
    swing.cabinets[3].panel.at_x, swing.cabinets[3].panel.at_y = 2000, -300   # x 3000, proud 300, in front of cabinet 3's door
    check("cabinet 3's door swings into the panel: a door clash naming the panel and its cabinet",
          [(c.cabinet, c.kind, c.against) for c in clashes(swing)], [(3, "door", "panel 5 on cabinet 1")])
    check("  without the panel, no clash", clashes(plain), [])
    tall = copy.deepcopy(j)
    tall.cabinets[3].panel.b = 2700
    check("a panel up past the ceiling is above_ceiling", above_ceiling(tall), [(5, 100 + 2700, 2600)])
    ac = [i for i in issues(tall) if i.check == "above-ceiling"]
    check("  the critical names the panel and its cabinet", [i.message for i in ac],
          ["top of panel 5, attached to cabinet 1, is at 2800 mm, above the 2600 mm ceiling"])
    j.room.ceiling = 1000                            # low: a base unit at 100 + 720 clears it standing
    tip_with = tip_problems(j)
    j.cabinets[3].panel.b = 5000                     # absurd: a panel no ceiling would clear
    check("tip-up ignores the panel however tall it is", tip_problems(j), tip_with)
    check("  and none of the tip-up inputs read it",
          tip_inputs(j.cabinets[0], placement_for(j, 1), j.room.ceiling),
          tip_inputs(plain.cabinets[0], placement_for(plain, 1), j.room.ceiling))
    check("  a panel is never a tip-up problem itself", [n for n, *_ in tip_problems(tall)], [])
    check("nothing about a panel reaches placed()", [c.number for c, _p, _l in placed(tall)], [1, 2, 3])

    print("\nsnapping and dragging: a cabinet's own panels move with it")
    j = job()
    j.cabinets[3].panel.attached_to = 1
    j.cabinets[3].panel.at_x, j.cabinets[3].panel.at_y = -t, -t
    j.placements = [p for p in j.placements if p.cabinet != 5]
    sn = snap_points(j, 1, "A")
    check("dragging cabinet 1, its own end panel is not a snap target", [s for s in sn if "5" in s["why"]], [])
    check("  but the neighbour still is", sorted(s["why"] for s in sn if "2" in s["why"]), ["left of 2", "right of 2"])
    check("  nor a height", [s for s in z_snap_points(j, 1, "A") if "5" in s["why"]], [])
    sn2 = snap_points(j, 2, "A")
    check("dragging cabinet 2, cabinet 1's panel IS one", sorted(s["why"] for s in sn2 if "5" in s["why"]), ["left of 5", "right of 5"])
    r = api.drag({"job": job_to_dict(j), "cabinet": 5})
    check("/api/drag refuses the panel and names its cabinet", (r["ok"], r["attached"]), (False, 1))
    r = api.drag({"job": job_to_dict(j), "cabinet": 1})
    check("  and hands the cabinet its model as before", (r["ok"], r["cabinet"]), (True, 1))
    layers = ["base", "wall", "tall", "panels"]      # the plan draws panels when the toggle says so
    check("the plan carries data-host on the panel, for the drag preview", 'data-host="1"' in plan_svg(j, show=layers), True)
    check("  so does the wall elevation", 'data-host="1"' in wall_elevation_svg(j, "A"), True)
    check("  a standalone panel's drawings carry none", 'data-host' in plan_svg(job(), show=layers) or 'data-host' in wall_elevation_svg(job(), "A"), False)

    print("\nthe 3D scene")
    s = SC.build(j)
    it = next(x for x in s["items"] if x["number"] == 5)
    check("the panel is placed, marked attached to 1, and has its parts", (it["placed"], it["attached"], len(it["parts"]) > 0), (True, 1, True))
    check("  its outline is where the derived placement puts it",
          sorted(map(tuple, it["parts"][0]["outline"])), sorted(fp(j, 5)))
    check("  a cabinet's entry says it is attached to nothing", next(x for x in s["items"] if x["number"] == 1)["attached"], None)

    print("\ndeleting the cabinet: No leaves standalone panels where they stand; Yes takes them")
    j = job()
    j.cabinets[3].panel.attached_to = 1
    j.cabinets[3].panel.at_x, j.cabinets[3].panel.at_y = -t, -t
    j.placements = [p for p in j.placements if p.cabinet != 5]
    j.cabinets.append(new_attached_panel(j, j.cabinets[0], next_number(j)))
    stood = {n: fp(j, n) for n in (5, 4)}
    d = api.panel_detach({"job": job_to_dict(j), "host": 1})
    check("No: every panel on it is detached, numbers kept", sorted(q["number"] for q in d["panels"]), [4, 5])
    jn = copy.deepcopy(j)
    for q in d["panels"]:
        next(c for c in jn.cabinets if c.number == q["number"]).panel = PanelSpec(**q["panel"])
    jn.placements += [Placement(**q) for q in d["placements"]]
    jn.cabinets.pop(0)
    jn.placements = [p for p in jn.placements if p.cabinet != 1]
    check("  with the cabinet gone they stand exactly where they stood", {n: fp(jn, n) for n in (5, 4)}, stood)
    check("  as standalone panels", [c.attached_to for c in jn.cabinets if c.is_panel], [None, None])
    check("  and nothing is left pointing at cabinet 1", [i for i in issues(jn) if i.check == "attached-host"], [])
    jy = copy.deepcopy(j)
    jy.cabinets = [c for c in jy.cabinets if c.number not in (1, 4, 5)]
    jy.placements = [p for p in jy.placements if p.cabinet != 1]
    check("Yes: the cabinet and its panels are gone, the rest untouched", [c.number for c in jy.cabinets], [2, 3])
    jo = copy.deepcopy(j)
    jo.cabinets.pop(0)
    jo.placements = [p for p in jo.placements if p.cabinet != 1]
    check("a panel left pointing at a cabinet that is gone stands nowhere ...", placement_for(jo, 5), None)
    check("  ... cuts as it is, and is a WARNING saying what to do",
          [(i.level, i.check) for i in issues(jo) if i.where == "5"], [(WARNING, "attached-host")])
    check("  host_of is None for it", host_of(jo, jo.cabinets[2]), None)
    jp = copy.deepcopy(j)
    jp.cabinets[3].panel.attached_to = 4               # a panel on a panel
    check("a panel cannot hang off a panel", (host_of(jp, jp.cabinets[3]), [i.check for i in issues(jp) if i.where == "5"]),
          (None, ["attached-host"]))

    print("\nduplicating the cabinet copies its panels, new numbers in the one series")
    r = api.duplicate({"job": job_to_dict(j), "index": 0})
    nums = [c["number"] for c in r["cabinets"]]
    check("the copy and its two panels take the next free numbers", nums, [6, 7, 8])
    check("  the panels are attached to the COPY, at the same offsets",
          [(c["panel"]["attached_to"], c["panel"]["at_x"], c["panel"]["at_y"], c["panel"]["at_z"]) for c in r["cabinets"][1:]],
          [(6, -t, -t, 0), (6, -t, -std.exposed_extra, 0)])
    check("  the copy is a cabinet like the original", (r["cabinets"][0]["kind"], r["cabinets"][0]["width"]), ("base", 600))
    check("  it is spliced in after the original", r["index"], 1)
    jd = copy.deepcopy(j)
    jd.cabinets[1:1] = [job_from_dict({"cabinets": [c]}).cabinets[0] for c in r["cabinets"]]
    check("  the originals still hang off cabinet 1", [c.number for c in attached_panels(jd, 1)], [5, 4])
    check("  and the copies off cabinet 6, unplaced until it is placed",
          ([c.number for c in attached_panels(jd, 6)], placement_for(jd, 7)), ([7, 8], None))
    check("  every number in the job is distinct", len({c.number for c in jd.cabinets}), len(jd.cabinets))
    r = api.duplicate({"job": job_to_dict(j), "index": 3})
    check("duplicating an attached PANEL copies it onto the same cabinet, next number",
          [(c["number"], c["panel"]["attached_to"]) for c in r["cabinets"]], [(6, 1)])

    print("\nthe job file: attached_to round-trips, and a standalone panel writes none of it")
    raw = json.dumps(job_to_dict(j), indent=2)
    back = job_from_dict(json.loads(raw))
    check("attached_to and the offsets survive save and load",
          [(c.number, c.panel.attached_to, c.panel.at_x, c.panel.at_y, c.panel.at_z) for c in back.cabinets if c.is_panel],
          [(5, 1, -t, -t, 0), (4, 1, -t, -std.exposed_extra, 0)])
    check("  and write back identically", json.dumps(job_to_dict(back), indent=2) == raw, True)
    check("  no placement record is written for an attached panel", [p["cabinet"] for p in job_to_dict(j)["placements"]], [1, 2, 3])
    d = cabinet_to_dict(job().cabinets[3])["panel"]
    check("a standalone panel's record carries no attachment keys", [k for k in d if k.startswith("at")], [])
    for name in ("Test", "Test_Panels", "Test_Build", "Corner Unit Test"):
        path = job_file(name)
        if not os.path.exists(path):
            continue
        on_disk = json.load(open(path, encoding="utf-8"))
        check(f"{name}.json writes back byte for byte", json.dumps(job_to_dict(job_from_dict(on_disk)), indent=2, ensure_ascii=False)
              == json.dumps(on_disk, indent=2, ensure_ascii=False), True)
    tj = load(job_file("Test"))
    check("Test.json's placed panel 8 is standalone, exactly as it was",
          (tj.cabinets[7].attached_to, placement_for(tj, 8).x), (None, 814))
    y8 = y_snap_points(tj, 8, "A")
    check("  and its y snaps are what they were", bool(y8) and all("y" in s for s in y8), True)

    print("\nA: a new cabinet's supports follow its kind (ruled 28 September 2026)")
    mats = job().materials
    rows = lambda c: [(r.type, r.qty, r.cut_board, r.kind, r.edges) for r in c.default_supports(mats)]
    check("base: Front, Top Rear, Back, Back", rows(box(1, 0, kind="base", carcass_board="MEL")),
          [("front", 1, "MEL", "pvc", ["front"]), ("top_rear", 1, "MEL", "pvc", ["front"]),
           ("back", 1, "MEL", "pvc", []), ("back", 1, "MEL", "pvc", [])])
    check("wall: three Backs", [r[0] for r in rows(box(1, 0, kind="upper"))], ["back"] * 3)
    check("tall: four Backs", [r[0] for r in rows(box(1, 0, kind="tall"))], ["back"] * 4)
    check("blind corner, base: by its kind", [r[0] for r in rows(box(1, 0, kind="base", corner_style="blind", blind_width=300))],
          ["front", "top_rear", "back", "back"])
    check("blind corner, tall: by its kind", [r[0] for r in rows(box(1, 0, kind="tall", corner_style="blind", blind_width=300))], ["back"] * 4)
    check("mitre: none", rows(box(1, 0, kind="tall", corner_style="mitre", arm_a=850, arm_b=850, face_a=500, face_b=500)), [])
    check("ell: none", rows(box(1, 0, kind="base", corner_style="ell", arm_a=850, arm_b=850, face_a=500, face_b=500)), [])
    r = api.support_defaults({"job": job_to_dict(job()), "index": 0})
    check("/api/support-defaults hands them back for the cabinet's kind", [x["type"] for x in r["rows"]], ["front", "top_rear", "back", "back"])
    check("an existing cabinet's rows are not touched by any of it", job().cabinets[0].support_rows, [])

    restructure()

    print()
    if FAILS:
        print(f"{len(FAILS)} FAILED: {FAILS}")
        sys.exit(1)
    print("ALL OK")


def restructure():
    """The Cabinets tab's 3D (UI restructure, 28 September 2026): one cabinet
    alone with its attached panels (`scene.build_cabinet`), and the drag of an
    attached panel there (spec B4) — snap targets off the carcass faces and
    edges (`room.attach_snap_points`), and the drop written to the very
    offsets Panel design types (`/api/attach-move`)."""
    from cabinetgen.room import attach_snap_points
    print("\nthe Cabinets tab's 3D: one cabinet alone, with its attached panels")
    j = job()
    j.cabinets.append(new_attached_panel(j, j.cabinets[0], 4))
    before = json.dumps(job_to_dict(j), sort_keys=True)
    one = SC.build_cabinet(j, 1)
    check("cabinet 1 with its one attached panel, and nothing else",
          (one["ok"], one["single"], [(i["number"], i["attached"]) for i in one["items"]]),
          (True, 1, [(1, None), (4, 1)]))
    check("no room, no walls, no overlays", (one["room"], one["room_parts"], one["overlays"]["swings"]),
          (None, [], []))
    check("the attached panel carries its offsets", one["items"][1]["at"], {"x": -16, "y": -16, "z": 0})
    room = SC.build(j)
    by = {i["number"]: i for i in room["items"]}

    def ext(item, k):
        return min(v[k] for q in item["parts"] for v in q["outline"])
    rel = lambda items: (ext(items[4], 0) - ext(items[1], 0), ext(items[4], 1) - ext(items[1], 1),
                         min(q["z0"] for q in items[4]["parts"]) - min(q["z0"] for q in items[1]["parts"]))
    single_by = {i["number"]: i for i in one["items"]}
    check("the panel stands where the room has it, relative to its cabinet", rel(single_by), rel(by))
    check("the same parts, tied to the same cut-list lines",
          [(q["role"], q["line"]) for q in single_by[1]["parts"]], [(q["role"], q["line"]) for q in by[1]["parts"]])
    check("selecting the attached panel shows its cabinet, with it",
          (SC.build_cabinet(j, 4)["single"], [i["number"] for i in SC.build_cabinet(j, 4)["items"]]), (1, [1, 4]))
    check("a standalone panel shows alone", [i["number"] for i in SC.build_cabinet(j, 5)["items"]], [5])
    check("a cabinet with none, alone", [i["number"] for i in SC.build_cabinet(j, 2)["items"]], [2])
    unplaced = copy.deepcopy(j)
    unplaced.placements = []
    u = SC.build_cabinet(unplaced, 1)
    check("an unplaced cabinet is drawn all the same, its panel with it",
          ([i["number"] for i in u["items"]], len(u["items"][0]["parts"]) > 0), ([1, 4], True))
    check("unknown number: said", SC.build_cabinet(j, 99)["ok"], False)
    check("read-only with respect to the job", json.dumps(job_to_dict(j), sort_keys=True) == before, True)
    r = api.scene_cabinet({"job": job_to_dict(j), "number": 1})
    check("/api/scene-cabinet is that", [i["number"] for i in r["items"]], [1, 4])

    print("\ndragging an attached panel there: the carcass faces and edges, the same offsets")
    pan = next(c for c in j.cabinets if c.number == 4)
    snaps = attach_snap_points(j, pan, j.cabinets[0])
    xs = {c["v"]: c["why"] for c in snaps["x"]}
    check("across: outside and inside each side, and both edges level",
          sorted(xs), sorted({-16, 0, 16, 600 - 16 - 16, 600 - 16, 600}))
    check("  -16 is against the left side, outside — where + Panel puts it", xs[-16], "against the left side, outside")
    ys = {c["v"] for c in snaps["y"]}
    check("back: the front face, the fronts, and the back face", {0, -16, 560, -576} <= ys, True)
    zs = {c["v"] for c in snaps["z"]}
    check("up: level underneath, on top, under, on the bottom panel", {0, 720, -720, 16} <= zs, True)
    check("each axis sorted, one reason per value",
          all([c["v"] for c in snaps[k]] == sorted({c["v"] for c in snaps[k]}) for k in "xyz"), True)
    m = api.attach_snaps({"job": job_to_dict(j), "cabinet": 4})
    check("/api/attach-snaps: where it is, the tolerance, the targets",
          (m["ok"], m["host"], m["at"], m["tolerance"], len(m["x"]) > 0), (True, 1, {"x": -16, "y": -16, "z": 0}, 20, True))
    check("  refused for a standalone panel", api.attach_snaps({"job": job_to_dict(j), "cabinet": 5})["ok"], False)
    mv = api.attach_move({"job": job_to_dict(j), "cabinet": 4, "at": {"x": 584.4, "y": -16, "z": 0}})
    check("the drop: whole millimetres, into at_x / at_y / at_z",
          (mv["ok"], mv["panel"]["attached_to"], mv["panel"]["at_x"], mv["panel"]["at_y"], mv["panel"]["at_z"]),
          (True, 1, 584, -16, 0))
    check("  which puts it against the right side, on cabinet 1's wall", (mv["placed_at"]["wall"], mv["placed_at"]["x"]),
          ("A", 1000 + 584))
    k = copy.deepcopy(j)
    kp = next(c for c in k.cabinets if c.number == 4)
    kp.panel = PanelSpec(**{**kp.panel.__dict__, "at_x": 584})
    check("  and the cut list is what it was: only the place moved",
          [(q.label, q.length, q.width, q.material) for q in generate_job(k)],
          [(q.label, q.length, q.width, q.material) for q in generate_job(j)])
    check("  refused for a panel attached to nothing",
          api.attach_move({"job": job_to_dict(j), "cabinet": 5, "at": {"x": 0}})["ok"], False)


if __name__ == "__main__":
    main()
