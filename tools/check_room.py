"""Room geometry regression check.

    python tools/check_room.py

Everything downstream of `room.to_world` — plan view, elevations, 3D, DXF, the
SolidWorks table — inherits whatever this module gets wrong, and a corner that
is a fraction of a degree out does not look wrong on screen. So the geometry is
pinned here by cases whose answers are known independently of the code.

WALLS ARE POSITIONED SEGMENTS (room redo Phase 1, 2 October 2026): a wall is
its two end points; the chain, the corners, the walk and whether the room
closes are derived. So this check pins:

  * `migration()` — every room saved in the old form (a length and a corner
    angle per wall, the chain walked from A along +X: the all-90 rectangle,
    the parallelogram and the open run with offsets, the L with a 270, the
    hexagon, the splay, the bay, and the fixture rooms) migrates to points
    within 1 mm of what the chain gave — exactly where every corner is 90 and
    every length whole — and load -> save -> load is stable
  * `walk()` — the walk order on a closed room, an L, two chains, a free wall
  * `renumber()` — the mapping applied to every record naming a wall
  * `flip_face()` — twice is identity; once re-measures openings,
    placements, gaps, plinths
  * `height()` — `opening-height` and `above-wall`
  * `single_wall()` — plan, elevation, gaps, runs and the 3D payload on a
    one-wall room
  * `touching()` — a T-wall is not a crossing; a real crossing still is
  * `delete()` — placements unplaced, no orphan

and keeps what it always pinned: a square room closes at exactly zero, a wall
lengthened by 150 mm opens the chain, a job with `room=None` behaves as it did
before rooms existed (which keeps tools/regen_check.py honest), the plan, the
layers, isolate, the job file, corner units only at 90, the plinth butt, gaps
at an angled corner, and the elevations, 3D, swing and ceiling on angled rooms.
"""
import json
import math
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
# the messages name corners "A→B"; a Windows console on cp1252 cannot print it
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from cabinetgen.model import (Cabinet, GapChoice, Job, Obstruction, Opening,  # noqa: E402
                              Placement, PlinthChoice, Room, Wall)
from cabinetgen.engine import generate_job                                 # noqa: E402
from cabinetgen.render import plan_svg, wall_elevation_svg                 # noqa: E402
from cabinetgen.room import (add_wall, cabinet_footprint, chain_walls,     # noqa: E402
                             chains, closure_error, connections, corner_angle,
                             corner_before, corner_points, crossing_walls,
                             is_closed, layer_of, next_wall, out_of_square, placed,
                             prev_wall, rectangular, set_corner, set_length,
                             set_out_of_square, to_world, walk_order, wall_frames,
                             walls_from_points, _legacy_frames)
from cabinetgen.room import flip_face as room_flip_face                    # noqa: E402
from cabinetgen.room import renumber_walls, delete_wall, wall_height       # noqa: E402
from cabinetgen.room import closure                                       # noqa: E402
from cabinetgen.room import corner_move as room_corner_move, wall_move as room_wall_move, room_snaps  # noqa: E402
from cabinetgen.room import split_wall as room_split_wall                  # noqa: E402
from cabinetgen.scene import build as scene_build                         # noqa: E402
from cabinetgen.render import _plan_room_side                             # noqa: E402
from cabinetgen.store import job_from_dict, job_to_dict, room_from_dict    # noqa: E402
from cabinetgen.validate import validate                                   # noqa: E402

FAILS = []
from cabinetgen.standard import STANDARD as STD_                          # noqa: E402


def check(name, got, want):
    ok = got == want
    print(f"  {'ok   ' if ok else 'FAIL '} {name}: {got}" + ("" if ok else f"  want {want}"))
    if not ok:
        FAILS.append(name)


def _issues(job, check_id):
    return [i for i in validate(job, generate_job(job)) if i.check == check_id]


def pts(rm):
    return [(w.id, w.x0, w.y0, w.x1, w.y1) for w in rm.walls]


def main() -> int:
    print("square room")
    r = rectangular(4000, 3000)
    check("closes", (closure_error(r), is_closed(r)), (0, True))
    check("corners", [(round(x), round(y)) for x, y in corner_points(r)],
          [(0, 0), (4000, 0), (4000, 3000), (0, 3000), (0, 0)])
    check("y runs into the room", to_world(r, "A", 2000, 600, 0), (2000, 600, 0))
    check("wall C runs back", to_world(r, "C", 1000, 0, 0), (3000, 3000, 0))
    check("wall D normal", to_world(r, "D", 0, 600, 0), (600, 3000, 0))
    check("every corner is 90, derived", [corner_angle(r, w.id) for w in r.walls], [90, 90, 90, 90])
    check("the room is on the RIGHT of x0 -> x1: wall A's normal is +Y",
          wall_frames(r)["A"][2], (-0.0, 1.0))

    print("\na typed length moves the end point and carries the chain")
    bad = rectangular(4000, 3000)
    set_length(bad, "C", 4150)
    check("C's end moved 150 along C, and D was carried with it",
          pts(bad)[2:], [("C", 4000, 3000, -150, 3000), ("D", -150, 3000, -150, 0)])
    check("so the loop opens by the 150, left where it is and reported (ruling 1, 3 Oct 2026)",
          (is_closed(bad), closure_error(bad), walk_order(bad)), (False, 150, ["A", "B", "C", "D"]))
    near = rectangular(4000, 3000)
    set_length(near, "C", 4010)
    check("a 10 mm miss is a near miss, reported", (is_closed(near), closure_error(near)), (False, 10))
    one = rectangular(4000, 3000)
    set_length(one, "C", 4001)
    check("within join_tolerance (1 mm) the ends still meet", (is_closed(one), closure_error(one)), (True, 0))

    print("\na typed corner angle turns the walls after it")
    t = rectangular(4000, 3000)
    set_corner(t, "A", 92.9)
    check("the A→B corner reads what was typed", corner_angle(t, "A"), 92.9)
    check("  and as the site measures it: 30 mm out at 600", out_of_square(corner_angle(t, "A"), 600), 30)
    check("  B leans away from the room by it", (t.walls[1].x1 > 4000, t.walls[1].y1), (True, 2996))
    set_out_of_square(t, "A", 0)
    check("typed back to 0 mm out of square: square again, to the mm",
          (corner_angle(t, "A"), pts(t)[1]), (90, ("B", 4000, 0, 4000, 3000)))
    check("B and C turned together, so B→C is still 90", corner_angle(t, "B"), 90)
    try:
        set_corner(rectangular(4000, 3000), "A", 400)
        refused = False
    except ValueError:
        refused = True
    check("an angle outside 0-360 is refused", refused, True)
    check("a corner far from square has no out-of-square figure", out_of_square(135, 600), None)
    last = rectangular(4000, 3000)
    set_corner(last, "D", 93)
    check("on a closed room the last corner (D→A) can be typed too: A, B, C turn about it, "
          "and the loop opens where the walk came back to A",
          (corner_angle(last, "D"), pts(last)[3], is_closed(last)), (93, ("D", 0, 3000, 0, 0), False))

    print("\ncabinet footprint")
    cab = Cabinet(number=1, width=600, height=720, depth=580)
    check("plan corners", cabinet_footprint(rectangular(4000, 3000),
                                            Placement(1, "A", 1000), cab),
          [(1000, 580), (1600, 580), (1600, 0), (1000, 0)])

    print("\nvalidation")
    check("no room and no placements is silent",
          validate(Job(name="t", cabinets=[cab]), []), [])
    check("a placement with no room warns",
          [i.message for i in validate(
              Job(name="t", cabinets=[cab], placements=[Placement(1, "A", 0)]), [])],
          ["placed on a wall but the job has no room"])
    # every room below has a measured ceiling, so each check sees only its own issue
    near.ceiling = 2700
    check("a 10 mm miss is a warning",
          [(i.level, i.check) for i in validate(Job(name="t", room=near), [])],
          [("warning", "room-closure")])
    bad.ceiling = 2700
    check("a 150 mm miss is an open run: nothing said about closing",
          [i.message for i in validate(Job(name="t", room=bad), []) if "clos" in i.message], [])
    check("bad wall, missing cabinet and overrun are all caught",
          len(validate(Job(name="t", cabinets=[cab],
                           room=rectangular(4000, 3000, ceiling=2700),
                           placements=[Placement(1, "Z", 0), Placement(9, "A", 0),
                                       Placement(1, "A", 3800)]), [])), 3)
    check("a duplicate wall id is critical",
          [i.message for i in validate(
              Job(name="t", room=Room(name="d", ceiling=2700,
                                      walls=[Wall("A", 0, 0, 1000, 0), Wall("A", 1000, 0, 1000, 1000),
                                             Wall("B", 1000, 1000, 0, 1000)])), [])],
          ["two walls share this id"])

    print("\nmeasurements the room cannot do without")
    check("a room has no ceiling until one is measured — there is no default",
          rectangular(4000, 3000).ceiling, None)
    check("and an unmeasured ceiling is a critical",
          [(i.level, i.message) for i in validate(Job(name="t", room=rectangular(4000, 3000)), [])],
          [("critical", "ceiling height not measured — it is a required site "
                        "measurement, and the ceiling check means nothing without it")])
    open_run = Room(name="o", ceiling=2700, walls=[Wall("A", 0, 0, 4000, 0), Wall("B", 4000, 0, 4000, 0)])
    check("so is an unmeasured wall, even on an open run where nothing closes",
          [(i.level, i.message) for i in validate(Job(name="t", room=open_run), [])],
          [("critical", "wall length not measured")])

    print("\nlayers")
    base = Cabinet(number=1, width=600, height=720, depth=580, kind="base")
    upper = Cabinet(number=2, width=600, height=400, depth=330, kind="upper")
    tall = Cabinet(number=3, width=600, height=2400, depth=580, kind="tall")
    check("base on the floor", layer_of(base, Placement(1, "A", 0)), "base")
    check("upper is a wall unit", layer_of(upper, Placement(2, "A", 0)), "wall")
    check("tall is its own layer", layer_of(tall, Placement(3, "A", 0)), "tall")
    check("a base carcass hung off the floor is a wall unit",
          layer_of(base, Placement(1, "A", 0, z=1500)), "wall")
    check("an override wins", layer_of(tall, Placement(3, "A", 0, layer="base")), "base")
    check("no placement at all still resolves", layer_of(base), "base")

    room = rectangular(4000, 3000)
    j = Job(name="l", cabinets=[base, upper, tall], room=room,
            placements=[Placement(1, "A", 0), Placement(2, "A", 700, z=1500),
                        Placement(3, "B", 0)])
    check("placed() reports each cabinet's layer",
          [(c.number, lay) for c, _, lay in placed(j)],
          [(1, "base"), (2, "wall"), (3, "tall")])
    check("an unplaced cabinet is not in the room",
          [c.number for c, _, _ in placed(Job(name="l", cabinets=[base], room=room))], [])

    print("\nplan view")
    svg = plan_svg(j)
    check("draws an svg", svg.startswith("<svg") and svg.endswith("</svg>"), True)
    for n in ("1", "2", "3"):
        check(f"cabinet {n} is drawn", f">{n}</text>" in svg, True)
    check("wall lengths are labelled", "A · 4000" in svg, True)
    only_base = plan_svg(j, show=("base",), ghost=("wall", "tall"))
    check("ghosted layers are still drawn", only_base.count('<polygon class="cab"'), 3)
    check("ghosted layers are faint", 'opacity="0.30"' in only_base, True)
    check("an unselected, unghosted layer is not drawn",
          plan_svg(j, show=("base",), ghost=()).count('<polygon class="cab"'), 1)
    check("wall units draw dashed: above the plan's cut", 'stroke-dasharray="4 3"' in plan_svg(j),
          True)
    check("no room draws a note, not a crash", "<text" in plan_svg(Job(name="x")), True)

    print("\nplan view: isolate")
    def ghosted(svg):
        """Which cabinets that plan drew faint, and which it drew solid."""
        out = {}
        for tag in re.findall(r'<polygon class="cab"[^>]*/>', svg):
            out[int(re.search(r'data-cab="([0-9]+)"', tag).group(1))] = (
                'opacity="0.30"' in tag)
        return out

    check("isolate off is exactly the plan as it was",
          plan_svg(j, isolate=None) == svg, True)
    check("isolated, everything is still drawn — ghosted, never hidden",
          sorted(ghosted(plan_svg(j, isolate=2))), [1, 2, 3])
    check("and all of it is faint but the one isolated",
          ghosted(plan_svg(j, isolate=2)), {1: True, 2: False, 3: True})
    check("whichever one it is", ghosted(plan_svg(j, isolate=3)),
          {1: True, 2: True, 3: False})
    off = plan_svg(j, show=("base",), ghost=("tall",), isolate=2)
    check("a layer toggled off still shows the item isolated out of it",
          ghosted(off), {1: True, 2: False, 3: True})
    check("...and isolate means ONE ITEM, not one layer: the base run it stood "
          "over is ghosted with the rest",
          ghosted(plan_svg(j, show=("base",), ghost=("tall",))),
          {1: False, 3: True})

    def deaf(svg):
        return len(re.findall(
            r'<polygon class="cab"[^>]*pointer-events="none"[^>]*/>', svg))

    check("every ghosted cabinet takes no pointer events while isolating",
          deaf(plan_svg(j, isolate=2)), 2)
    check("and none of them do when nothing is isolated — a layer ghosted by the "
          "TOGGLE keeps its events, which is what reveals its swing on hover",
          (deaf(svg), deaf(plan_svg(j, show=("base",), ghost=("wall", "tall")))),
          (0, 0))
    check("a number this plan does not draw isolates nothing, rather than "
          "greying out the whole room — which is a cabinet added and not yet "
          "given a wall",
          plan_svg(j, isolate=99) == svg, True)

    print("\nopenings and obstructions")
    withop = rectangular(4000, 3000)
    withop.walls[0].openings.append(Opening("door", 1000, 810))
    withop.walls[0].obstructions.append(Obstruction("waste", 2000, 400))
    s2 = plan_svg(Job(name="o", room=withop))
    check("an opening breaks the wall into two runs",
          s2.count('stroke-width="2" stroke-linecap="square"'), 5)
    check("the opening is labelled", "door 810" in s2, True)
    check("the obstruction is drawn", "wast" in s2, True)

    print("\njob files")
    full = Room(name="kitchen", ceiling=2650, walls=[
        Wall("A", 0, 0, 4000, 0,
             openings=[Opening("door", 1200, 810)],
             obstructions=[Obstruction("waste", 900, 400, 110, 110, 20)]),
        Wall("B", 4000, 0, 4000, 3000), Wall("C", 4000, 3000, 0, 3000), Wall("D", 0, 3000, 0, 0)])
    j = Job(name="rt", cabinets=[cab], room=full,
            placements=[Placement(1, "A", 250, 100, True)])
    d1 = job_to_dict(j)
    check("round trip is identical",
          job_to_dict(job_from_dict(json.loads(json.dumps(d1)))), d1)
    check("a wall at its defaults writes its points and nothing else",
          sorted(d1["room"]["walls"][1]), ["id", "obstructions", "openings", "x0", "x1", "y0", "y1"])
    check("and the room writes no `closed`: it is derived", "closed" in d1["room"], False)
    full.walls[1].height, full.walls[1].thickness, full.walls[1].drawn = 1200, 230, True
    d2 = job_to_dict(j)["room"]["walls"][1]
    check("height, thickness and drawn are written when set",
          (d2.get("height"), d2.get("thickness"), d2.get("drawn")), (1200, 230, True))
    check("and read back",
          [(w.height, w.thickness, w.drawn) for w in job_from_dict(json.loads(json.dumps(job_to_dict(j)))).room.walls][1],
          (1200, 230, True))
    plain = job_to_dict(Job(name="p", cabinets=[cab]))
    check("a roomless job writes no room key", "room" in plain, False)
    check("a roomless job writes no placements key", "placements" in plain, False)
    posted = job_to_dict(job_from_dict(dict(json.loads(json.dumps(plain)),
                                            placements=[])))
    check("an empty placements list posted back writes no key", posted, plain)

    print("\nadding a wall off either end of a run")
    run = Room(name="l", ceiling=2700, walls=[Wall("A", 0, 0, 3000, 0)])
    b = add_wall(run, after="A", length=2000)
    check("a wall added after A gets the next free letter", b.id, "B")
    check("and turns the corner at A's end at 90, making an L", pts(run)[1], ("B", 3000, 0, 3000, 2000))
    check("A→B is a corner now", (next_wall(run, "A"), corner_angle(run, "A")), ("B", 90))
    c = add_wall(run, before="A", length=1500)
    check("a wall added before A gets the next free letter too", c.id, "C")
    check("and ends at A's start, square, the room on its right: the run is a U",
          pts(run)[2], ("C", 0, 1500, 0, 0))
    check("the walk starts at the head of the chain: C, A, B", walk_order(run), ["C", "A", "B"])
    check("A still runs from (0, 0) along +X: nothing was re-origined", pts(run)[0], ("A", 0, 0, 3000, 0))
    u = Job(name="u", room=run,
            cabinets=[Cabinet(number=1, width=600, height=720, depth=580, kind="base")],
            placements=[Placement(1, "A", 200)])
    check("a cabinet already on A stays on A, at the same place along it",
          (u.placements[0].wall, u.placements[0].x), ("A", 200))
    check("and an open U raises nothing about closing",
          [i.message for i in validate(u, generate_job(u)) if "clos" in i.message], [])
    try:
        add_wall(rectangular(4000, 3000), after="D")
        refused = False
    except ValueError:
        refused = True
    check("an end that already meets a wall takes no new wall", refused, True)

    migration()
    walk()
    renumber()
    flip_face()
    height()
    single_wall()
    touching()
    delete()
    angled()
    closure_text()
    corner_move()
    wall_move()
    snaps()
    split()

    print(f"\n{'ALL OK' if not FAILS else str(len(FAILS)) + ' FAILED: ' + str(FAILS)}")
    return 1 if FAILS else 0


def _old_frames(walls, offset_depth):
    """wall_frames exactly as it stood before corners could turn by any angle
    (HEAD 8ccef9f), off the OLD wall records — kept only to prove the
    migration reproduces it."""
    def corner_offset(i):
        n = len(walls)
        here = int(walls[i].get("offset_end") or 0)
        nxt = int(walls[(i + 1) % n].get("offset_start") or 0)
        return here or nxt

    out = {}
    px, py, theta = 0.0, 0.0, 0.0
    for i, w in enumerate(walls):
        dx, dy = math.cos(theta), math.sin(theta)
        out[w["id"]] = ((px, py), (dx, dy), (-dy, dx))
        px += w["length"] * dx
        py += w["length"] * dy
        a = w.get("corner_end", 90)
        nominal = math.pi / 2 if a == 90 else math.radians(180 - a)
        theta += nominal - math.atan2(corner_offset(i), offset_depth)
    return out


def legacy(name, walls, closed=True, offset_depth=600, ceiling=2600):
    """A room record as a job file wrote it before 2 October 2026."""
    return {"name": name, "ceiling": ceiling, "offset_depth": offset_depth, "closed": closed,
            "walls": [dict({"offset_start": 0, "offset_end": 0, "openings": [], "obstructions": []}, **w)
                      for w in walls]}


def lw(wid, length, **kw):
    return dict({"id": wid, "length": length}, **kw)


LEGACY_ROOMS = {
    "square": legacy("sq", [lw("A", 4000), lw("B", 3000), lw("C", 4000), lw("D", 3000)]),
    "parallelogram": legacy("p", [lw("A", 4000, offset_start=-40, offset_end=40),
                                  lw("B", 3000, offset_start=40, offset_end=-40),
                                  lw("C", 4000, offset_start=-40, offset_end=40),
                                  lw("D", 3000, offset_start=40, offset_end=-40)]),
    "open run": legacy("o", [lw("A", 2317, offset_end=13), lw("B", 1911, offset_start=7, offset_end=-22),
                             lw("C", 2860)], closed=False),
    "L with a 270": legacy("L", [lw("A", 3000), lw("B", 1000, corner_end=270), lw("C", 1000),
                                 lw("D", 2000), lw("E", 4000), lw("F", 3000)]),
    "hexagon": legacy("hex", [lw(chr(65 + k), 2000, corner_end=120) for k in range(6)]),
    "splay": legacy("splay", [lw("A", 4000), lw("B", 3000), lw("C", 3000, corner_end=135),
                              lw("E", 1414, corner_end=135), lw("D", 2000)]),
    "bay": legacy("bay", [lw("A", 1000, corner_end=225), lw("B", 707, corner_end=135),
                          lw("C", 1000, corner_end=135), lw("D", 707, corner_end=225),
                          lw("E", 1000), lw("F", 3000), lw("G", 4000), lw("H", 3000)]),
    "Test.json (as saved before)": legacy("Test", [lw("A", 4000), lw("B", 3000)], closed=False),
    "Main Bedroom (as saved before)": legacy("Main bedroom", [lw("A", 3200), lw("B", 3800),
                                                             lw("C", 3200), lw("D", 3800)], ceiling=2800),
    "PhilipDemo (as saved before)": legacy("PhilipDemo", [lw("B", 3000), lw("C", 3000)]),
}


def migration():
    """Ruling 8 and 9 (2 October 2026): a room saved as a chain migrates ONCE
    to points, within 1 mm of what the chain gave, exactly where it should be,
    and load -> save -> load is then stable."""
    from fixture_jobs import job_file

    print("\nmigration: every room saved in the old form becomes points")
    exact = {"square", "L with a 270", "Test.json (as saved before)",
             "Main Bedroom (as saved before)", "PhilipDemo (as saved before)"}
    for name, rec in LEGACY_ROOMS.items():
        rm = room_from_dict(json.loads(json.dumps(rec)))
        old = _old_frames(rec["walls"], rec["offset_depth"])
        new = wall_frames(rm)
        worst = max(math.dist(old[i][0], new[i][0]) for i in old)
        dirs = max(math.dist(old[i][1], new[i][1]) for i in old)
        lengths = max(abs(w.length - r["length"]) for w, r in zip(rm.walls, rec["walls"]))
        check(f"{name}: every start point within 1 mm of the chain's (worst {worst:.3f}), "
              f"every length within 1 mm, every direction within 0.001",
              (worst <= 1.0, lengths <= 1, dirs <= 1e-3), (True, True, True))
        if name in exact:
            check(f"  {name}: exact — every corner 90 and every length whole, the chain's "
                  f"points rounded ARE the stored points",
                  (all((round(old[i][0][0]), round(old[i][0][1])) == (int(new[i][0][0]), int(new[i][0][1]))
                       for i in old), lengths), (True, 0))
        check(f"  {name}: closed as it was", is_closed(rm), rec["closed"] and len(rec["walls"]) > 2)
        check(f"  {name}: wall A still starts at (0, 0) along +X",
              (rm.walls[0].x0, rm.walls[0].y0, rm.walls[0].y1 == 0), (0, 0, True))
        d = job_to_dict(Job(name="m", room=rm))
        again = job_to_dict(job_from_dict(json.loads(json.dumps(d))))
        check(f"  {name}: load -> save -> load is stable", again, d)
        check(f"  {name}: the old keys are gone from the file",
              any(k in w for w in d["room"]["walls"] for k in ("length", "offset_start", "offset_end", "corner_end")),
              False)
    # the migrated corner angles are the nominal ones to 0.1, plus the offsets' deviation
    ell = room_from_dict(json.loads(json.dumps(LEGACY_ROOMS["L with a 270"])))
    check("the L's corners read 90 and 270 again, derived from the points",
          [corner_angle(ell, w.id) for w in ell.walls], [90, 270, 90, 90, 90, 90])
    hexa = room_from_dict(json.loads(json.dumps(LEGACY_ROOMS["hexagon"])))
    check("the hexagon's corners read 120 (within 0.1) off the rounded points",
          all(abs(corner_angle(hexa, w.id) - 120) <= 0.1 for w in hexa.walls), True)
    check("  and it still closes", (is_closed(hexa), closure_error(hexa)), (True, 0))
    para = room_from_dict(json.loads(json.dumps(LEGACY_ROOMS["parallelogram"])))
    check("the parallelogram's offsets became angles: 40 out at 600 is 93.8 and 86.2",
          [corner_angle(para, w.id) for w in para.walls], [93.8, 86.2, 93.8, 86.2])
    check("  read back as the site measured them, within a mm",
          [out_of_square(corner_angle(para, w.id), 600) for w in para.walls], [40, -40, 40, -40])
    orun = room_from_dict(json.loads(json.dumps(LEGACY_ROOMS["open run"])))
    check("the open run's last wall has no corner after it", corner_angle(orun, "C"), None)

    print("\nthe fixtures on disk are in the new form, and stable")
    for name in ("Test.json", "Test_Build.json", "Test_Panels.json", "Corner Unit Test.json",
                 "Test_drawers.json", "Test_3d.json", "Test_export.json"):
        with open(job_file(name), encoding="utf-8") as fh:
            raw = json.load(fh)
        if not raw.get("room"):
            continue
        check(f"{name}: points, no legacy keys, no `closed`",
              (all("x0" in w and "length" not in w for w in raw["room"]["walls"]),
               "closed" in raw["room"]), (True, False))
        j = job_from_dict(raw)
        check(f"  {name}: writes back byte for byte", job_to_dict(j), raw)


def walk():
    print("\nwalk order: chain by chain, free walls last")
    sq = rectangular(4000, 3000)
    check("a closed room walks A, B, C, D", (walk_order(sq), chains(sq)),
          (["A", "B", "C", "D"], [(["A", "B", "C", "D"], True)]))
    con = connections(sq)
    check("each wall's end meets the next wall's start, round the loop",
          (con["next"], con["prev"]),
          ({"A": "B", "B": "C", "C": "D", "D": "A"}, {"A": "D", "B": "A", "C": "B", "D": "C"}))
    ell = Room(name="L", walls=chain_walls([("B", 3000), ("A", 2000)], closed=False))
    check("an L named B then A walks from its head: B, A — the letters do not decide",
          walk_order(ell), ["B", "A"])
    check("  and is open", (is_closed(ell), closure_error(ell)), (False, 0))
    two = Room(name="2", walls=[Wall("A", 0, 0, 3000, 0), Wall("B", 3000, 0, 3000, 2000),
                                Wall("C", 0, 6000, 4000, 6000), Wall("D", 4000, 6000, 4000, 8000)])
    check("two chains: each walked from its head, in order of lowest letter",
          chains(two), [(["A", "B"], False), (["C", "D"], False)])
    free = rectangular(4000, 3000)
    free.walls.append(Wall("E", 1000, 1000, 2000, 1000))
    check("a free wall — meeting nothing at either end — comes last",
          (walk_order(free), chains(free)[-1]), (["A", "B", "C", "D", "E"], (["E"], False)))
    check("  and the room is still closed: the loop is the room", is_closed(free), True)
    check("  it has no corner at either end", (corner_before(free, "E"), corner_angle(free, "E")), (None, None))
    check("  and nothing beside it", (prev_wall(free, "E"), next_wall(free, "E")), (None, None))
    lone = Room(name="A", walls=[Wall("B", 0, 0, 3000, 0)])
    check("after Z the letters go on: AA", (len(list(zip(range(27), __import__('cabinetgen.room', fromlist=['_letters'])._letters())))), 27)
    from cabinetgen.room import _letters, next_wall_id
    check("  the 27th letter is AA", list(zip(range(27), _letters()))[-1][1], "AA")
    check("  and the first unused letter is handed out", next_wall_id(lone), "A")


def renumber():
    print("\nRenumber: letters along the walk, every record follows")
    rm = Room(name="r", ceiling=2600, walls=chain_walls([("C", 4000), ("A", 3000), ("D", 4000), ("B", 3000)]))
    j = Job(name="r", room=rm,
            cabinets=[Cabinet(number=1, width=600, height=720, depth=580, kind="base"),
                      Cabinet(number=2, width=600, height=720, depth=580, kind="base")],
            placements=[Placement(1, "A", 100), Placement(2, "D", 200)],
            gaps=[GapChoice("A", None, 1, "base", "open")],
            plinths=[PlinthChoice("D", "base", 2)])
    before = job_to_dict(j)
    check("a closed loop's walk starts at its lowest letter: A, D, B, C",
          walk_order(rm), ["A", "D", "B", "C"])
    mapping = renumber_walls(j)
    check("the mapping follows the walk: A, D, B, C become A, B, C, D",
          mapping, {"A": "A", "D": "B", "B": "C", "C": "D"})
    check("the walls are re-lettered in place, their points untouched",
          pts(rm), [("D", 0, 0, 4000, 0), ("A", 4000, 0, 4000, 3000), ("B", 4000, 3000, 0, 3000),
                    ("C", 0, 3000, 0, 0)])
    check("placements follow", [(p.cabinet, p.wall, p.x) for p in j.placements], [(1, "A", 100), (2, "B", 200)])
    check("gap decisions follow", [(g.wall, g.after, g.before) for g in j.gaps], [("A", None, 1)])
    check("plinth decisions follow", [(c.wall, c.first) for c in j.plinths], [("B", 2)])
    check("the cut list did not move",
          [(p.label, p.length, p.width) for p in generate_job(j)],
          [(p.label, p.length, p.width) for p in generate_job(job_from_dict(before))])
    check("renumbering again changes nothing", renumber_walls(j), {k: k for k in "ABCD"})
    u = Room(name="u", walls=chain_walls([("C", 1500), ("A", 3000), ("B", 2000)], closed=False))
    free = Wall("Z", 9000, 9000, 9500, 9000)
    u.walls.append(free)
    check("an open U with a free wall: C, A, B, Z -> A, B, C, D",
          renumber_walls(Job(name="u", room=u)), {"C": "A", "A": "B", "B": "C", "Z": "D"})


def flip_face():
    print("\nFlip face: one wall's room side turned round")
    rm = Room(name="f", ceiling=2600, walls=chain_walls([("A", 3000), ("B", 2000)], closed=False))
    rm.walls[0].openings.append(Opening("door", 200, 700))
    rm.walls[0].obstructions.append(Obstruction("waste", 2500, 100))
    j = Job(name="f", room=rm,
            cabinets=[Cabinet(number=1, width=600, height=720, depth=580, kind="base"),
                      Cabinet(number=2, width=600, height=720, depth=580, kind="base"),
                      Cabinet(number=3, width=1000, height=720, depth=560, doors=1,
                              corner_unit=True, corner_style="blind", blind_width=500)],
            placements=[Placement(1, "A", 1000), Placement(2, "B", 700), Placement(3, "A", 2000)],
            gaps=[GapChoice("A", None, 1, "base", "open")],
            plinths=[PlinthChoice("A", "base", 1)])
    from cabinetgen.room import runs
    first_run = [r for r in runs(j) if r.wall == "A"][0]
    before = job_to_dict(j)
    cut_before = [(p.label, p.length, p.width, p.qty) for p in generate_job(j)]
    fp_before = cabinet_footprint(rm, j.placements[0], j.cabinets[0])
    room_flip_face(j, "A")
    check("A's end points are swapped; B is untouched",
          pts(rm), [("A", 3000, 0, 0, 0), ("B", 3000, 0, 3000, 2000)])
    check("A's normal now points the other way (−Y): the room is on its other side",
          wall_frames(rm)["A"][2], (0.0, -1.0))
    check("A no longer meets B: B's start was A's end, which is now A's start",
          (next_wall(rm, "A"), prev_wall(rm, "B")), (None, None))
    check("the opening keeps its place along the wall, x from the other end",
          [(o.x, o.width) for o in rm.walls[0].openings], [(2100, 700)])
    check("the obstruction too", [ob.x for ob in rm.walls[0].obstructions], [500])
    by = {p.cabinet: p for p in j.placements}
    check("cabinet 1 keeps its distance from A's far end", (by[1].wall, by[1].x), ("A", 1400))
    check("cabinet 2 on B is untouched", (by[2].wall, by[2].x), ("B", 700))
    check("the blind corner's hand swaps, so its corner end is still at that end",
          j.cabinets[2].corner_hand, "L")
    check("a gap decision on A swaps its sides", [(g.after, g.before) for g in j.gaps], [(1, None)])
    check("a plinth decision follows its run to the cabinet that now starts it",
          [(p.wall, p.first) for p in j.plinths], [("A", first_run.cabinets[-1])])
    check("the cut list does not move",
          [(p.label, p.length, p.width, p.qty) for p in generate_job(j)], cut_before)
    fp_after = cabinet_footprint(rm, by[1], j.cabinets[0])
    check("cabinet 1 stands on the other face of A: the same x along the wall, mirrored in y",
          (sorted(x for x, _ in fp_after) == sorted(x for x, _ in fp_before),
           sorted(y for _, y in fp_after)), (True, [-580, -580, 0, 0]))
    room_flip_face(j, "A")
    check("flipped twice: the job file is exactly what it was", job_to_dict(j) == before, True)
    sq = Job(name="c", room=rectangular(4000, 3000))
    room_flip_face(sq, "C")
    check("a closed room's wall can be flipped too: it then meets nothing, the room is an open "
          "run D, A, B and C is a free wall",
          (is_closed(sq.room), walk_order(sq.room)), (False, ["D", "A", "B", "C"]))


def height():
    print("\nwall height: a wall lower than the ceiling")
    rm = rectangular(4000, 3000, ceiling=2600)
    rm.walls[1].height = 1200
    check("a wall's height is its own, else the ceiling",
          [wall_height(rm, w) for w in rm.walls], [2600, 1200, 2600, 2600])
    tall = Cabinet(number=1, width=600, height=2100, depth=580, kind="tall")
    base = Cabinet(number=2, width=600, height=720, depth=580, kind="base")
    j = Job(name="h", room=rm, cabinets=[tall, base],
            placements=[Placement(1, "B", 500), Placement(2, "B", 1500)])
    check("a tall unit against the half wall is a WARNING, naming the wall and its height",
          [(i.level, i.where, i.message) for i in _issues(j, "above-wall")],
          [("warning", "1", "reaches 2200, above wall B, which is 1200 high")])
    check("the base unit under it says nothing", [i.where for i in _issues(j, "above-wall") if i.where == "2"], [])
    check("it is not above the ceiling", _issues(j, "above-ceiling"), [])
    j.placements[0].wall = "A"
    check("on a full-height wall nothing is said", _issues(j, "above-wall"), [])
    rm.walls[1].openings.append(Opening("window", 500, 900, sill=900, head=1500))
    check("an opening whose head is above its wall is a CRITICAL",
          [(i.level, i.where, i.message) for i in _issues(j, "opening-height")],
          [("critical", "wall B", "wall B: the window's head at 1500 is above the wall, which is 1200 high")])
    rm.walls[1].height = None
    check("with the wall at the ceiling the same window is fine", _issues(j, "opening-height"), [])
    rm.walls[1].openings[0].head = 2700
    check("above the ceiling, it is not", len(_issues(j, "opening-height")), 1)
    rm.walls[1].openings = []
    rm.walls[1].height = 1200
    svg = wall_elevation_svg(j, "B")
    rect = re.search(r'<rect x="[0-9.]+" y="([0-9.]+)" width="[0-9.]+" height="([0-9.]+)" fill="none" stroke=', svg)
    scale = float(re.search(r'data-scale="([0-9.]+)"', svg).group(1))
    check("the elevation draws wall B to its height (1200), with the ceiling dashed above it",
          (round(float(rect.group(2)) / scale), 'class="ceilingline"' in svg, 'stroke-dasharray="6 4"' in svg),
          (1200, True, True))
    svga = wall_elevation_svg(j, "A")
    recta = re.search(r'<rect x="[0-9.]+" y="([0-9.]+)" width="[0-9.]+" height="([0-9.]+)" fill="none" stroke=', svga)
    scalea = float(re.search(r'data-scale="([0-9.]+)"', svga).group(1))
    check("  and wall A to the ceiling (2600), no dashed line",
          (round(float(recta.group(2)) / scalea), 'class="ceilingline"' in svga), (2600, False))
    from cabinetgen.scene import build as build_scene
    sc = build_scene(j)
    check("3D: each wall carries its height", [w["height"] for w in sc["room"]["walls"]], [2600, 1200, 2600, 2600])


def single_wall():
    print("\na one-wall room draws and computes")
    from cabinetgen.room import gaps, runs
    from cabinetgen.scene import build as build_scene
    rm = Room(name="one", ceiling=2600, walls=[Wall("A", 0, 0, 3000, 0)])
    j = Job(name="one", room=rm,
            cabinets=[Cabinet(number=1, width=900, height=720, depth=580, kind="base"),
                      Cabinet(number=2, width=600, height=720, depth=580, kind="base")],
            placements=[Placement(1, "A", 0), Placement(2, "A", 1000)],
            plinths=[PlinthChoice("A", "base", 1)])
    svg = plan_svg(j)
    check("the plan draws", (svg.startswith("<svg"), "A · 3000" in svg, svg.count('<polygon class="cab"')),
          (True, True, 2))
    check("the elevation draws", wall_elevation_svg(j, "A").startswith("<svg"), True)
    g = gaps(j)
    check("gaps: one between the cabinets, one to the far end; the ends have no corner so no taper",
          [(x.after, x.before, x.nominal, x.front) for x in g], [(1, 2, 100, 100), (2, None, 1400, 1400)])
    r = runs(j)
    check("runs: two, the gap undecided breaking the run", [(x.cabinets, x.x0, x.x1) for x in r],
          [([1], 0, 900), ([2], 1000, 1600)])
    check("no plinth butt and no plinth corner on a wall meeting nothing",
          [i.check for i in validate(j, generate_job(j)) if i.check in ("plinth-corner",)], [])
    sc = build_scene(j)
    check("3D: one wall, the floor its own segment, the room open",
          (len(sc["room"]["walls"]), sc["room"]["floor"], sc["room"]["closed"]),
          (1, [[0.0, 0.0], [3000.0, 0.0]], False))
    check("nothing about closing, nothing about crossing, nothing orphaned",
          [i.check for i in validate(j, generate_job(j))
           if i.check in ("room-closure", "room-self-intersect", "placement-wall")], [])
    from cabinetgen.room import return_profiles
    check("the elevation sees nothing beside it", return_profiles(j, "A"), [])


def touching():
    print("\ncrossing walls: a T-wall is legal, a real crossing is not")
    tee = rectangular(4000, 3000, ceiling=2600)
    tee.walls.append(Wall("E", 1500, 0, 1500, 1200))       # a nib off wall A into the room
    check("a wall starting ON another wall is not a crossing", crossing_walls(tee), [])
    check("  and raises nothing", _issues(Job(name="t", room=tee), "room-self-intersect"), [])
    check("  the nib is a free wall: it meets nothing at either end",
          (prev_wall(tee, "E"), next_wall(tee, "E")), (None, None))
    bow = Room(name="bow", ceiling=2600)
    walls_from_points(bow, [(0, 0), (4000, 0), (0, 3000), (4000, 3000)], True)
    for w in bow.walls:
        w.drawn = False
    check("walls crossing each other are named in pairs", crossing_walls(bow), [("B", "D")])
    check("  a critical naming the two walls",
          [(i.level, i.where) for i in _issues(Job(name="bow", room=bow), "room-self-intersect")],
          [("critical", "B/D")])
    cross = rectangular(4000, 3000, ceiling=2600)
    cross.walls.append(Wall("E", 2000, -500, 2000, 500))   # through wall A
    check("a wall cutting through another IS a crossing", crossing_walls(cross), [("A", "E")])
    check("a clean room raises none",
          _issues(Job(name="r", room=rectangular(4000, 3000, ceiling=2600)), "room-self-intersect"), [])


def delete():
    print("\ndeleting a wall: what was on it is unplaced, nothing is orphaned")
    rm = rectangular(4000, 3000, ceiling=2600)
    j = Job(name="d", room=rm,
            cabinets=[Cabinet(number=1, width=600, height=720, depth=580, kind="base"),
                      Cabinet(number=2, width=600, height=720, depth=580, kind="base")],
            placements=[Placement(1, "B", 100), Placement(2, "A", 200)],
            gaps=[GapChoice("B", None, 1, "base", "open")],
            plinths=[PlinthChoice("B", "base", 1), PlinthChoice("A", "base", 2)])
    gone = delete_wall(j, "B")
    check("it says what went", gone, {"unplaced": [1], "gaps": 1, "plinths": 1})
    check("the wall is gone and the room is an open run of three", (walk_order(rm), is_closed(rm)),
          (["C", "D", "A"], False))
    check("cabinet 1 is unplaced; cabinet 2 on A stays",
          [(p.cabinet, p.wall) for p in j.placements], [(2, "A")])
    check("its gap and plinth decisions went with it; A's stays",
          (j.gaps, [(c.wall, c.first) for c in j.plinths]), ([], [("A", 2)]))
    check("no placement-wall critical", _issues(j, "placement-wall"), [])
    try:
        delete_wall(j, "Q")
        refused = False
    except ValueError:
        refused = True
    check("a wall the room does not have is refused", refused, True)


def angled():
    """Walls at any angle (brief of 29 September 2026), on points."""
    from cabinetgen.engine import plinth_panels
    from cabinetgen.room import (corner_shadow, gaps, plinth_butt_wall, return_profiles, runs)
    from cabinetgen.scene import build as build_scene

    print("\nan L room: one outside corner")
    ell = Room(name="L", ceiling=2600, walls=chain_walls(
        [("A", 3000), ("B", 1000), ("C", 1000), ("D", 2000), ("E", 4000), ("F", 3000)],
        corners=[90, 270, 90, 90, 90, 90]))
    check("closes", (closure_error(ell), is_closed(ell)), (0, True))
    check("corners", [(round(x), round(y)) for x, y in corner_points(ell)],
          [(0, 0), (3000, 0), (3000, 1000), (4000, 1000), (4000, 3000), (0, 3000), (0, 0)])
    check("the outside corner reads 270", [corner_angle(ell, w.id) for w in ell.walls], [90, 270, 90, 90, 90, 90])
    check("the wall after the outside corner runs back out, into the room on its left",
          to_world(ell, "C", 500, 600), (3500, 1600, 0))
    check("no wall crosses another", crossing_walls(ell), [])

    print("\ndrawn with the mouse: walls ADDED to the room")
    rm = Room(name="d", ceiling=2600)
    rect = walls_from_points(rm, [(0, 0), (4000, 0), (4000, 3000), (0, 3000)], True)
    check("a rectangle, A-D, every corner 90", ([w.id for w in rect], [corner_angle(rm, w.id) for w in rect]),
          (["A", "B", "C", "D"], [90, 90, 90, 90]))
    check("  the points are kept as drawn, nothing re-oriented", pts(rm)[0], ("A", 0, 0, 4000, 0))
    rm2 = Room(name="d2", ceiling=2600)
    walls_from_points(rm2, [(0, 0), (0, 3000), (4000, 3000), (4000, 0)], True)
    check("drawn anticlockwise comes out clockwise, the first corner still first",
          pts(rm2), [("A", 0, 0, 4000, 0), ("B", 4000, 0, 4000, 3000), ("C", 4000, 3000, 0, 3000), ("D", 0, 3000, 0, 0)])
    check("  so the room is inside it", is_closed(rm2) and all(corner_angle(rm2, w.id) == 90 for w in rm2.walls), True)
    more = walls_from_points(rm, [(5000, 0), (8000, 0), (8000, 2000)], False)
    check("drawn again, the new walls are added with the next letters, the old ones kept",
          ([w.id for w in more], len(rm.walls)), (["E", "F"], 6))
    joined = walls_from_points(rm, [(4010, 2990), (6000, 3000)], False)
    check("a first point near an existing corner joins it there",
          pts(rm)[-1], ("G", 4000, 3000, 6000, 3000))
    check("  and is a free wall no longer: wall C... no, it starts on C's end, so C→G is a corner... "
          "C's end already meets D, so G is a T off that corner, meeting nothing",
          (prev_wall(rm, "G"), corner_before(rm, "G")), (None, None))
    check("every drawn wall is marked drawn", all(w.drawn for w in rm.walls), True)
    dj = Job(name="d", room=rm2)
    check("a drawn wall is a critical until it is measured",
          [i.message for i in _issues(dj, "wall-drawn")][:1],
          ["wall A: drawn, not measured — type its length, or tick it as measured"])
    for w in rm2.walls:
        w.drawn = False
    check("measured: nothing raised", _issues(dj, "wall-drawn"), [])
    run_rm = Room(name="o", ceiling=2600)
    walls_from_points(run_rm, [(0, 0), (3000, 0), (3000, -2000)], False)
    check("an open run turning the other way is walked back, room inside the L",
          pts(run_rm), [("A", 3000, -2000, 3000, 0), ("B", 3000, 0, 0, 0)])

    print("\nwhich side is the room on an OPEN run drawn with the mouse")

    def on_room_side(rm, points, wall_ids):
        fr = wall_frames(rm)
        return all(((x - fr[w][0][0]) * fr[w][2][0] + (y - fr[w][0][1]) * fr[w][2][1]) >= -0.5
                   for w in wall_ids for x, y in points)

    def open_l(points):
        rm = Room(name="o", ceiling=2600)
        walls_from_points(rm, points, False)
        j = Job(name="o", room=rm,
                cabinets=[Cabinet(number=1, width=600, height=720, depth=580, kind="base"),
                          Cabinet(number=2, width=600, height=720, depth=580, kind="base")],
                placements=[Placement(1, "A", 1000), Placement(2, "B", 700)])
        fps = [cabinet_footprint(rm, p, c) for c, p in zip(j.cabinets, j.placements)]
        return rm, j, fps

    ltr = [(0, 0), (3000, 0), (3000, 2000)]
    rm1, _j1, fp1 = open_l(ltr)
    rm2b, _j2, fp2 = open_l(ltr[::-1])
    check("an L clicked left-to-right: A 3000 then B 2000, one 90 corner",
          [(w.id, w.length, corner_angle(rm1, w.id)) for w in rm1.walls], [("A", 3000, 90), ("B", 2000, None)])
    check("clicked right-to-left: the same walls", pts(rm2b), pts(rm1))
    check("both cabinets inside the L, on the room side of BOTH walls",
          ([on_room_side(rm1, fp, ["A", "B"]) for fp in fp1], fp1 == fp2), ([True, True], True))

    print("\ncorner units only at a 90 inside corner (ruling 4)")
    mitre = Cabinet(number=1, width=850, height=2400, depth=500, back="none", supports=0,
                    doors=1, corner_unit=True, corner_style="mitre",
                    arm_a=850, arm_b=850, face_a=500, face_b=500)
    at135 = Room(name="m", ceiling=2600, walls=chain_walls(
        [("A", 4000), ("B", 3000), ("C", 2586), ("D", 3000), ("E", 4000 - 2121)],
        corners=[135, 135, 90, 90, 90]))
    mj = Job(name="m", room=at135, cabinets=[mitre], placements=[Placement(1, "A", 3150)])
    check("a mitre flush in a 135 corner: the ruling-4 critical",
          [(i.level, i.message) for i in _issues(mj, "corner-unit-angle")],
          [("critical", "Corner unit at a 135° corner: construction not ruled.")])
    check("and it casts no shadow there", corner_shadow(at135, mitre, mj.placements[0]), None)
    check("nor is it also told it is out of its corner",
          [i.message for i in validate(mj, generate_job(mj))
           if "not standing in a corner" in i.message], [])
    blind = Cabinet(number=2, width=1000, height=720, depth=560, doors=1,
                    corner_unit=True, corner_style="blind", blind_width=500)
    bj2 = Job(name="b", room=ell, cabinets=[blind], placements=[Placement(2, "A", 2000)])
    check("a blind unit at the L's 90 corner: nothing", _issues(bj2, "corner-unit-angle"), [])
    bj2.placements = [Placement(2, "B", 0)]
    check("at the outside corner (the end of B, 270): the critical",
          [i.message for i in _issues(bj2, "corner-unit-angle")],
          ["Corner unit at a 270° corner: construction not ruled."])
    sq = Job(name="s", room=rectangular(4000, 3000, ceiling=2600), cabinets=[mitre],
             placements=[Placement(1, "A", 3150)])
    check("the same mitre in a square room: no critical, and its shadow as before",
          (_issues(sq, "corner-unit-angle"), corner_shadow(sq.room, mitre, sq.placements[0])),
          ([], ("B", 0, 850, 500)))
    fr = Room(name="free", ceiling=2600, walls=[Wall("A", 0, 0, 4000, 0)])
    fj = Job(name="f", room=fr, cabinets=[mitre], placements=[Placement(1, "A", 3150)])
    check("on a free wall a corner unit has no corner to stand in: no shadow, a warning says so",
          (corner_shadow(fr, mitre, fj.placements[0]),
           [i.level for i in validate(fj, generate_job(fj)) if "not standing in a corner" in i.message]),
          (None, ["warning"]))

    print("\nplinth butts at a 90 inside corner only (ruled 29 September 2026)")

    def butt(angle):
        rm = rectangular(4000, 3000, ceiling=2600)
        set_corner(rm, "A", angle)
        j = Job(name="c", room=rm,
                cabinets=[Cabinet(number=1, width=900, height=720, depth=580, kind="base"),
                          Cabinet(number=2, width=600, height=720, depth=580, kind="base")],
                placements=[Placement(1, "A", 3100), Placement(2, "B", 0)],
                plinths=[PlinthChoice("A", "base", 1), PlinthChoice("B", "base", 2)])
        r = [x for x in runs(j) if x.wall == "B"][0]
        return (plinth_butt_wall(j, r), sorted(p.length for p in plinth_panels(j)),
                [(i.level, i.message) for i in _issues(j, "plinth-corner")])

    check("at 90: the 16 mm butt, no warning", butt(90), ("A", [584, 900], []))
    check("at 135: no butt, each board ends with its run, and a warning naming the corner",
          butt(135), (None, [600, 900], [("warning", "Plinth at the A→B 135° corner: the "
                                          "boards don't meet, cut a closing piece on site")]))
    check("at 60 the same", butt(60)[:2] + (len(butt(60)[2]),), (None, [600, 900], 1))
    check("at 180 none: each ends at the corner, nothing said", butt(180), (None, [600, 900], []))
    check("at 270 none", butt(270), (None, [600, 900], []))

    print("\ngaps at an angled corner")

    def gap_at(angle, x):
        rm = rectangular(4000, 3000)
        set_corner(rm, "A", angle)
        j = Job(name="g", room=rm,
                cabinets=[Cabinet(number=1, width=900, height=720, depth=580, kind="base")],
                placements=[Placement(1, "A", x)])
        return [(g.nominal, g.front) for g in gaps(j) if g.before is None]

    check("at 90 a square gap, as always", gap_at(90, 3000), [(100, 100)])
    check("at 135 the return wall leans away: the gap at the front is the real one",
          gap_at(135, 3000), [(100, 680)])
    check("at 270 the run just ends at the corner", gap_at(270, 3000), [(100, 100)])

    print("\nthe elevations see the neighbours at their real angle")
    base = lambda n: Cabinet(number=n, width=600, height=720, depth=580, kind="base")  # noqa
    rm = rectangular(4000, 3000, ceiling=2600)
    set_corner(rm, "A", 135)
    ej = Job(name="e", room=rm, cabinets=[base(1)], placements=[Placement(1, "B", 0)])
    prof = return_profiles(ej, "A")
    check("at 135 the return run is seen end on, leaning: 580 deep reads 580 x cos 45",
          [(p["cabinet"], p["x0"], p["x1"]) for p in prof], [(1, 3590, 4000)])
    set_corner(rm, "A", 270)
    check("at 270 it is behind this wall and not drawn", return_profiles(ej, "A"), [])
    check("the wall elevation draws either way",
          wall_elevation_svg(ej, "A").startswith("<svg"), True)

    print("\n3D and the checks that are already geometry: an angled room")
    rm = Room(name="a", ceiling=2500, walls=chain_walls(
        [("A", 4000), ("B", 2000), ("C", 2586), ("D", 3414), ("E", 4000 - 1414)],
        corners=[135, 135, 90, 90, 90]))
    tall = Cabinet(number=1, width=600, height=2350, depth=600, kind="tall")
    aj = Job(name="a", room=rm, cabinets=[tall, base(2)],
             placements=[Placement(1, "B", 700), Placement(2, "A", 3400)])
    sc = build_scene(aj)
    check("the 3D floor is the corner chain",
          sc["room"]["floor"], [[round(x, 1), round(y, 1)] for x, y in corner_points(rm)])
    fr = wall_frames(rm)["B"]
    check("a wall on the diagonal carries its own direction and normal",
          [round(v, 3) for v in fr[1] + fr[2]], [0.707, 0.707, -0.707, 0.707])
    fp = cabinet_footprint(rm, aj.placements[0], tall)
    check("a cabinet on it stands on it: its back corners on the wall line",
          [to_world(rm, "B", 700)[:2] in fp, to_world(rm, "B", 1300)[:2] in fp], [True, True])
    from cabinetgen.room import tip_problems
    flat = Job(name="f", room=rectangular(4000, 3000, ceiling=2500), cabinets=[tall],
               placements=[Placement(1, "A", 700)])
    check("tip-up on the diagonal wall: the same answer as on a square wall",
          tip_problems(aj), tip_problems(flat))
    check("and it is one (stands at 2450, needs more to tip up under 2500)",
          [(n, top) for n, top, _need, _c in tip_problems(aj)], [(1, 2450)])
    from cabinetgen.room import overlaps
    check("apart along the two walls, nothing overlaps", overlaps(aj), [])
    aj.placements[0].x = 0
    check("pushed into the 135 corner, the real footprints overlap and it is said",
          sorted((o.a, o.b) for o in overlaps(aj)), [(1, 2)])

    from cabinetgen.room import above_ceiling, clashes

    def swing(angle):
        r = Room(name="s", ceiling=2600, walls=chain_walls([("A", 3000), ("B", 3000)], closed=False,
                                                           corners=[angle]))
        c = Cabinet(number=1, width=600, height=720, depth=580, kind="base", doors=1,
                    door_hinges=["R"])
        return [(x.cabinet, x.against) for x in clashes(
            Job(name="d", room=r, cabinets=[c], placements=[Placement(1, "A", 2400)]))]

    check("a door hinged at a 90 corner grazes the return wall: clear, as always",
          swing(90), [])
    check("at a 60 corner the return wall is in its swing", swing(60), [(1, "wall B")])
    check("at 135 it leans away: clear", swing(135), [])
    aj.room.ceiling = 2400
    check("above the ceiling on the diagonal wall, as anywhere",
          [n for n, *_ in above_ceiling(aj)], [1])



def closure_text():
    """Ruling 1 and 2 (3 October 2026): a typed figure leaves the loop open by
    the miss; ONE answer, `room.closure`, names it and every reader agrees."""
    print("\nclosure: one miss, one corner, one text — and every reader agrees")
    r = rectangular(4000, 3000)
    set_length(r, "A", 4100)
    cl = closure(r)
    check("A typed 4100: the loop opens by 100 at D→A, in the ruled words",
          cl, {"closed": False, "miss": 100, "at": "D\u2192A", "level": "crit",
               "text": "Loop opens by 100 mm at D\u2192A \u2014 type the other walls or drag a corner"})
    job = Job(name="cl", room=r, cabinets=[], placements=[])
    iss = _issues(job, "room-closure")
    check("  the Validation tab says the same words, a critical over closure_block",
          [(i.level, i.message) for i in iss], [("critical", cl["text"])])
    sc = scene_build(job)
    check("  the 3D scene carries the same closure", (sc["room"]["closed"], sc["room"]["closure"]), (False, cl))
    check("  the plan draws the face bands, not the floor tint",
          sum('data-wall=' in x for x in _plan_room_side(r, lambda q: q, STD_)) > 0 and
          not any('data-wall=' not in x and "roomside" in x for x in _plan_room_side(r, lambda q: q, STD_)), True)
    small = rectangular(4000, 3000)
    set_length(small, "A", 4003)
    check("3 mm: said (info), and nothing in Validation", (closure(small)["level"], closure(small)["miss"],
          _issues(Job(name="s", room=small), "room-closure")), ("info", 3, []))
    w12 = rectangular(4000, 3000)
    set_length(w12, "A", 4012)
    check("12 mm: a warning in the same words", [(i.level, i.message) for i in _issues(Job(name="w", room=w12), "room-closure")],
          [("warning", closure(w12)["text"])])
    set_length(r, "A", 4000)
    check("typed back: closed again, all by itself", closure(r)["text"], "closed room")
    set_length(r, "A", 4001)
    check("within join_tolerance it still closes", closure(r)["closed"], True)
    u = Room(name="U", walls=chain_walls([("A", 3000), ("B", 4000), ("C", 3000)], closed=False))
    check("a U is an open run on purpose (its open side is beyond loop_miss_max): nothing said",
          (closure(u)["text"], closure(u)["miss"]), ("open run", 0))
    ell = Room(name="L", walls=chain_walls([("A", 3000), ("B", 2000)], closed=False))
    check("two walls never make a loop", closure(ell)["text"], "open run")


def _box_job(room):
    cabs = [Cabinet(number=1, width=600, height=720, depth=560, kind="base"),
            Cabinet(number=2, width=600, height=720, depth=560, kind="base")]
    return Job(name="drag", room=room, cabinets=cabs,
               placements=[Placement(1, "B", 2200), Placement(2, "C", 500)])


def corner_move():
    """Ruling 3: a corner dragged moves every wall end on it; what stands on a
    wall that changed keeps its x, clamped to the wall, and is reported."""
    print("\ncorner_move: the joined ends move together; placements keep x, clamped and reported")
    job = _box_job(rectangular(4000, 3000))
    job.room.walls[1].openings.append(Opening("window", 2000, 900, 900, 2100))
    rep = room_corner_move(job, (4000, 3000), (4000, 2500))
    check("B's end and C's start moved together, the loop still closed",
          (pts(job.room)[1:3], closure(job.room)["closed"]),
          ([("B", 4000, 0, 4000, 2500), ("C", 4000, 2500, 0, 3000)], True))
    check("cabinet 1 on B (x 2200, 600 wide) clamped to 1900 and said; cabinet 2 on C keeps its x",
          ([[p.cabinet, p.wall, p.x] for p in job.placements], rep["clamped"]),
          ([[1, "B", 1900], [2, "C", 500]], [[1, "B", 2200, 1900]]))
    check("the window on B kept to the wall too", (job.room.walls[1].openings[0].x, rep["openings"]),
          (1600, [["B", "window", 2000, 1600]]))
    short = _box_job(rectangular(4000, 3000))
    rep = room_corner_move(short, (4000, 3000), (4000, 500))
    check("a wall shorter than an item: it is never moved off, and said",
          (short.placements[0].x, rep["too_long"]), (0, [[1, "B"]]))
    free = Job(name="f", room=Room(name="f", walls=[Wall("A", 0, 0, 3000, 0)]))
    room_corner_move(free, (3000, 0), (3500, 0))
    check("a free end moves alone", pts(free.room), [("A", 0, 0, 3500, 0)])
    opened = Job(name="o", room=rectangular(4000, 3000))
    set_length(opened.room, "A", 4100)
    check("a loop opened by a typed length...", closure(opened.room)["miss"], 100)
    d = [w for w in opened.room.walls if w.id == "D"][0]
    room_corner_move(opened, (d.x1, d.y1), (0, 0))
    check("  ...closes when its open end is dragged onto the other corner", closure(opened.room)["text"], "closed room")
    try:
        room_corner_move(job, (1234, 5678), (0, 0))
        check("no wall ends there: refused", False, True)
    except ValueError:
        check("no wall ends there: refused", True, True)


def wall_move():
    """Ruling 3: a wall dragged parallel; its neighbours keep their other end
    and their direction, so a 90 stays 90."""
    print("\nwall_move: the neighbours stretch, a 90 stays 90")
    job = _box_job(rectangular(4000, 3000))
    rep = room_wall_move(job, "B", 300)            # into the room: the room 300 shorter
    check("B moved 300 into the room; A and C stretch (shorten) to it",
          pts(job.room), [("A", 0, 0, 3700, 0), ("B", 3700, 0, 3700, 3000),
                          ("C", 3700, 3000, 0, 3000), ("D", 0, 3000, 0, 0)])
    check("every corner still 90, the room closed",
          ([corner_angle(job.room, w) for w in "ABCD"], closure(job.room)["closed"]), ([90] * 4, True))
    check("cabinet 2 on C keeps its x from C's start, which moved with B (x 500)",
          [[p.cabinet, p.wall, p.x] for p in job.placements], [[1, "B", 2200], [2, "C", 500]])
    check("  reported as moved: A, B, C", rep["moved"], ["A", "B", "C"])
    sp = Job(name="splay", room=Room(name="s", walls=chain_walls(
        [("A", 4000), ("B", 3000), ("C", 2000), ("E", 2828), ("D", 1000)], corners=[90, 90, 135, 135, 90])))
    before = corner_angle(sp.room, "C")
    room_wall_move(sp, "E", 100)
    check("a splayed wall moved: its neighbours keep their directions, the 135s stay 135",
          ([corner_angle(sp.room, "C"), corner_angle(sp.room, "E")], before), ([135, 135], 135))
    check("  the room stays closed", closure(sp.room)["closed"], True)
    line = Job(name="l", room=Room(name="l", walls=[Wall("A", 0, 0, 2000, 0), Wall("B", 2000, 0, 4000, 0)]))
    room_wall_move(line, "B", 200)
    check("a neighbour in line has to turn: its joint carried straight across",
          pts(line.room), [("A", 0, 0, 2000, 200), ("B", 2000, 200, 4000, 200)])


def snaps():
    """Ruling 4: the candidates, each with its reason, in the ruled priority."""
    print("\nsnaps: corners, alignment, angles, offsets — each with its reason")
    ell = Job(name="L", room=Room(name="L", walls=chain_walls([("A", 4000), ("B", 3000)], closed=False)))
    sn = room_snaps(ell, "corner", point=(4000, 3000))
    check("an L's free end: the other corners are joins, named",
          sorted(c["why"] for c in sn["corners"]), ["on corner A→B", "on corner the start of A"])
    xs = sorted({(l["p"][0], l["why"]) for l in sn["lines"] if l["d"] == [0.0, 1.0]})
    check("  alignment: a vertical line through each other corner (the X the return lines up with)",
          xs, [(0, "in line with the start of A"), (4000, "in line with A→B")])
    rays = [(r["d"], r["rank"], r["why"]) for r in sn["rays"] if r["rank"] == 0]
    check("  angles: B stretches about its start; in line with A and 90 to A rank first",
          rays, [([1.0, 0.0], 0, "in line with A"), ([0.0, 1.0], 0, "90° to A"), ([0.0, -1.0], 0, "90° to A")])
    ranks = [r["rank"] for r in sn["rays"]]
    check("  the priority order: the neighbour's 90 / 180, the plan's axes, 45s, the step",
          ranks == sorted(ranks) and ranks[0] == 0 and 1 in ranks and 2 in ranks and 3 in ranks, True)
    u = Job(name="U", room=Room(name="U", walls=chain_walls([("A", 3000), ("B", 4000), ("C", 2800)], closed=False)))
    sn = room_snaps(u, "corner", point=(200, 4000))
    al = [l["why"] for l in sn["lines"] if l["d"] == [0.0, 1.0] and l["p"][0] == 0]
    check("a U: dragging C's free end, a vertical line through A's start lands it on A's X",
          al, ["in line with the start of A"])
    sn = room_snaps(u, "wall", wall_id="C")
    check("a wall drag: the offsets that put its line through another corner",
          sorted((o["d"], o["why"]) for o in sn["offsets"]),
          [(4000.0, "in line with A→B"), (4000.0, "in line with the start of A")])
    sq = Job(name="sq", room=rectangular(4000, 3000))
    sn = room_snaps(sq, "draw", points=[(1000, 1000), (2000, 1000)])
    check("drawing: corners, the walls as segments (for a split), and rays from the last corner",
          (len(sn["corners"]), [g["wall"] for g in sn["segments"]], sn["rays"][0]["p"], sn["rays"][0]["why"]),
          (4, ["A", "B", "C", "D"], [2000, 1000], "in line with the last wall"))
    check("  a drawing's own earlier corners line up too",
          any(l["why"] == "in line with drawn corner 1" for l in sn["lines"]), True)

def split():
    """Ruling 6: a wall split in two; the first keeps its letter, the second
    takes the next; records follow by x; one spanning the split is reported."""
    print("\nsplit_wall: letters, records follow by x, a spanning item reported")
    job = Job(name="split", room=rectangular(4000, 3000),
              cabinets=[Cabinet(number=n, width=600, height=720, depth=560, kind="base") for n in (1, 2, 3)],
              placements=[Placement(1, "A", 200), Placement(2, "A", 1200), Placement(3, "A", 2600)],
              gaps=[GapChoice("A", after=2, before=3, treatment="open")],
              plinths=[PlinthChoice("A", first=3)])
    job.room.walls[0].openings.append(Opening("window", 2200, 1200, 900, 2100))
    job.room.walls[0].obstructions.append(Obstruction("plug", 3500, 300))
    rep = room_split_wall(job, "A", 1500)
    check("A keeps its letter to the split; E runs on to A's old end",
          pts(job.room)[0::4], [("A", 0, 0, 1500, 0), ("E", 1500, 0, 4000, 0)])
    check("  the loop still closes, walked A, E, B, C, D",
          (closure(job.room)["text"], walk_order(job.room)), ("closed room", ["A", "E", "B", "C", "D"]))
    check("  cabinet 1 stays on A, 3 goes to E re-measured, 2 spans the split: stays on A, reported",
          ([[p.cabinet, p.wall, p.x] for p in job.placements], rep["spanning"]),
          ([[1, "A", 200], [2, "A", 1200], [3, "E", 1100]], [2]))
    e = [w for w in job.room.walls if w.id == "E"][0]
    check("  the window and the plug follow by x", ([(o.kind, o.x) for o in e.openings],
          [(o.kind, o.x) for o in e.obstructions], job.room.walls[0].openings), ([("window", 700)], [("plug", 2000)], []))
    check("  the plinth decision follows its cabinet", [c.wall for c in job.plinths], ["E"])
    t = Job(name="t", room=rectangular(4000, 3000))
    room_split_wall(t, "A", 1500)
    new = walls_from_points(t.room, [(1500, 0), (1500, 1200)], False)
    check("a wall drawn from the split point is a T-wall: free at its far end, the loop intact",
          ([w.id for w in new], closure(t.room)["text"], crossing_walls(t.room),
           next_wall(t.room, "A"), prev_wall(t.room, new[0].id)),
          (["F"], "closed room", [], "E", None))
    try:
        room_split_wall(job, "A", 0)
        check("a split at an end is refused", False, True)
    except ValueError:
        check("a split at an end is refused", True, True)



if __name__ == "__main__":
    raise SystemExit(main())
