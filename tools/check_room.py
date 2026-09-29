"""Room geometry regression check.

    python tools/check_room.py

Everything downstream of `room.to_world` — plan view, elevations, 3D, DXF, the
SolidWorks table — inherits whatever this function gets wrong, and a corner that
is a fraction of a degree out does not look wrong on screen. So the geometry is
pinned here by cases whose answers are known independently of the code:

  * a square room closes at exactly zero
  * a parallelogram, out of square at every corner but with the deviations
    cancelling, must also close at exactly zero — this is what proves the corner
    turn, since a wrong sign or a wrong axis still closes a square room
  * a wall lengthened by 150 mm must miss closing by exactly 150 mm

It also pins the rule that a job with `room=None` behaves as it did before rooms
existed, which is what keeps tools/regen_check.py honest.

And walls at any angle (29 September 2026, `angles()`): a room of 90-degree
corners gives float-for-float the frames the old turn gave, an L with one 270
closes, a 120 hexagon, a 135 splay and a 225 / 135 bay close, crossing walls
are a critical naming the pair, an outline drawn with the mouse becomes walls
either way round, a mitre in a 135 corner raises the ruling-4 critical, the
plinth butts at 90 and 135 and not at 180 or 270, and the elevations, the 3D
floor, overlaps, door swing, tip-up and the ceiling read the real angle.
"""
import json
import math
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
# the messages name corners "A→B"; a Windows console on cp1252 cannot print it
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from cabinetgen.model import (Cabinet, Job, Obstruction, Opening,          # noqa: E402
                              Placement, Room, Wall)
from cabinetgen.engine import generate_job                                 # noqa: E402
from cabinetgen.render import plan_svg                                     # noqa: E402
from cabinetgen.room import (add_wall, cabinet_footprint, closure_error,   # noqa: E402
                             corner_offset, corner_points, layer_of, placed,
                             rectangular, to_world)
from cabinetgen.store import job_from_dict, job_to_dict                    # noqa: E402
from cabinetgen.validate import validate                                   # noqa: E402

FAILS = []


def check(name, got, want):
    ok = got == want
    print(f"  {'ok   ' if ok else 'FAIL '} {name}: {got}" + ("" if ok else f"  want {want}"))
    if not ok:
        FAILS.append(name)


def main() -> int:
    print("square room")
    r = rectangular(4000, 3000)
    check("closes", closure_error(r), 0)
    check("corners", [(round(x), round(y)) for x, y in corner_points(r)],
          [(0, 0), (4000, 0), (4000, 3000), (0, 3000), (0, 0)])
    check("y runs into the room", to_world(r, "A", 2000, 600, 0), (2000, 600, 0))
    check("wall C runs back", to_world(r, "C", 1000, 0, 0), (3000, 3000, 0))
    check("wall D normal", to_world(r, "D", 0, 600, 0), (600, 3000, 0))

    print("\nparallelogram — out of square at every corner, still closes")
    o = 40
    p = Room(name="para", walls=[
        Wall("A", 4000, offset_start=-o, offset_end=+o),
        Wall("B", 3000, offset_start=+o, offset_end=-o),
        Wall("C", 4000, offset_start=-o, offset_end=+o),
        Wall("D", 3000, offset_start=+o, offset_end=-o),
    ])
    check("closes", closure_error(p), 0)
    dev = math.atan2(o, p.offset_depth)
    check("wall B leans by the measured deviation",
          to_world(p, "B", 3000, 0, 0)[:2],
          (round(4000 + 3000 * math.sin(dev)), round(3000 * math.cos(dev))))

    print("\nmeasurements that disagree")
    bad = rectangular(4000, 3000)
    bad.walls[2].length = 4150
    check("150 mm long wall misses by 150 mm", closure_error(bad), 150)
    run = rectangular(4000, 3000)
    run.closed = False
    check("an open run has nothing to close", closure_error(run), 0)

    print("\na corner is measured from both sides")
    d = rectangular(4000, 3000)
    d.walls[0].offset_end, d.walls[1].offset_start = 12, 3
    check("the first wall's figure drives the geometry", corner_offset(d, 0)[0], 12)
    check("the disagreement is reported", corner_offset(d, 0)[1], 9)
    one = rectangular(4000, 3000)
    one.walls[1].offset_start = 7
    check("measured from one side only still works", corner_offset(one, 0)[0], 7)

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
    bad.ceiling = 2700
    check("a 150 mm miss is critical",
          [i.level for i in validate(Job(name="t", room=bad), [])], ["critical"])
    warn = rectangular(4000, 3000, ceiling=2700)
    warn.walls[2].length = 4010
    check("a 10 mm miss is only a warning",
          [i.level for i in validate(Job(name="t", room=warn), [])], ["warning"])
    check("bad wall, missing cabinet and overrun are all caught",
          len(validate(Job(name="t", cabinets=[cab],
                           room=rectangular(4000, 3000, ceiling=2700),
                           placements=[Placement(1, "Z", 0), Placement(9, "A", 0),
                                       Placement(1, "A", 3800)]), [])), 3)
    check("a duplicate wall id is critical",
          [i.message for i in validate(
              Job(name="t", room=Room(name="d", ceiling=2700,
                                      walls=[Wall("A", 1000), Wall("A", 1000),
                                             Wall("B", 1000)])), [])],
          ["two walls share this id"])

    print("\nmeasurements the room cannot do without")
    check("a room has no ceiling until one is measured — there is no default",
          rectangular(4000, 3000).ceiling, None)
    check("and an unmeasured ceiling is a critical",
          [(i.level, i.message) for i in validate(Job(name="t", room=rectangular(4000, 3000)), [])],
          [("critical", "ceiling height not measured — it is a required site "
                        "measurement, and the ceiling check means nothing without it")])
    open_run = rectangular(4000, 3000, ceiling=2700)
    open_run.closed = False
    open_run.walls[1].length = 0
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
    # A cabinet that has landed underneath another one has nothing to click on,
    # so it is reached from the LIST and everything else is GHOSTED, not hidden
    # — the same treatment the layer toggle already uses, not a second
    # convention (21 September 2026).
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
    # P4: the layer toggle does not get a vote on the isolated item. Cabinet 2 is
    # the wall unit, and its layer is in neither list here.
    off = plan_svg(j, show=("base",), ghost=("tall",), isolate=2)
    check("a layer toggled off still shows the item isolated out of it",
          ghosted(off), {1: True, 2: False, 3: True})
    check("...and isolate means ONE ITEM, not one layer: the base run it stood "
          "over is ghosted with the rest",
          ghosted(plan_svg(j, show=("base",), ghost=("tall",))),
          {1: False, 3: True})
    # Ghosting alone is not enough: the item that is hidden is hidden UNDER
    # something, and that something would still swallow the click.
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
        Wall("A", 4000, offset_end=12,
             openings=[Opening("door", 1200, 810)],
             obstructions=[Obstruction("waste", 900, 400, 110, 110, 20)]),
        Wall("B", 3000, offset_start=12), Wall("C", 4000), Wall("D", 3000)])
    j = Job(name="rt", cabinets=[cab], room=full,
            placements=[Placement(1, "A", 250, 100, True)])
    d1 = job_to_dict(j)
    check("round trip is identical",
          job_to_dict(job_from_dict(json.loads(json.dumps(d1)))), d1)
    plain = job_to_dict(Job(name="p", cabinets=[cab]))
    check("a roomless job writes no room key", "room" in plain, False)
    check("a roomless job writes no placements key", "placements" in plain, False)
    # The browser always carries `placements: []` since 23 September 2026 (a new
    # job had none, and Add a room threw in renderPlaces). Posted back, it must
    # still write no key, or every roomless job file grows one on its next save.
    posted = job_to_dict(job_from_dict(dict(json.loads(json.dumps(plain)),
                                            placements=[])))
    check("an empty placements list posted back writes no key", posted, plain)

    print("\nadding a wall at either end of the run")
    run = Room(name="l", ceiling=2700, closed=False, walls=[Wall("A", 3000)])
    b = add_wall(run, "end", 2000)
    check("a wall added at the end gets the next free letter", b.id, "B")
    check("and goes after the last wall", [w.id for w in run.walls], ["A", "B"])
    check("turning the corner at A's end, making an L",
          to_world(run, "B", 0, 0, 0), to_world(run, "A", 3000, 0, 0))
    c = add_wall(run, "start", 1500)
    check("a wall added at the start gets the next free letter too", c.id, "C")
    check("and goes before the first", [w.id for w in run.walls], ["C", "A", "B"])
    check("meeting A at A's start corner, so the run is now a U",
          to_world(run, "A", 0, 0, 0), to_world(run, "C", 1500, 0, 0))
    check("a new wall starts square at both of its corners",
          (c.offset_start, c.offset_end, b.offset_start, b.offset_end), (0, 0, 0, 0))
    u = Job(name="u", room=run,
            cabinets=[Cabinet(number=1, width=600, height=720, depth=580, kind="base")],
            placements=[Placement(1, "A", 200)])
    check("a cabinet already on A stays on A, at the same place along it",
          (u.placements[0].wall, u.placements[0].x), ("A", 200))
    check("and an open U raises nothing about closing",
          [i.message for i in validate(u, generate_job(u)) if "clos" in i.message], [])
    closed = rectangular(4000, 3000, ceiling=2700)
    add_wall(closed, "end", 3000)
    check("a wall added to a closed room shows as a miss until the shape closes",
          closure_error(closed) > 0, True)

    angles()

    print(f"\n{'ALL OK' if not FAILS else str(len(FAILS)) + ' FAILED: ' + str(FAILS)}")
    return 1 if FAILS else 0


def _old_frames(rm):
    """wall_frames exactly as it stood before corners could turn by any angle
    (HEAD 8ccef9f), kept here only to prove the new one reproduces it."""
    out = {}
    px, py, theta = 0.0, 0.0, 0.0
    for i, w in enumerate(rm.walls):
        dx, dy = math.cos(theta), math.sin(theta)
        out[w.id] = ((px, py), (dx, dy), (-dy, dx))
        px += w.length * dx
        py += w.length * dy
        offset, _ = corner_offset(rm, i)
        theta += math.pi / 2 - math.atan2(offset, rm.offset_depth)
    return out


def _issues(job, check_id):
    return [i for i in validate(job, generate_job(job)) if i.check == check_id]


def angles():
    """Walls at any angle, either direction (brief of 29 September 2026)."""
    from cabinetgen.engine import plinth_panels
    from cabinetgen.model import PlinthChoice
    from cabinetgen.render import wall_elevation_svg
    from cabinetgen.room import (corner_angle, corner_shadow, crossing_walls, gaps,
                                 plinth_butt_wall, return_profiles, runs, walls_from_points,
                                 wall_frames)
    from cabinetgen.scene import build as build_scene
    from fixture_jobs import job_file

    print("\nevery corner at 90: every coordinate exactly what it always was")
    rooms = [rectangular(4000, 3000),
             Room(name="p", walls=[Wall("A", 4000, offset_start=-40, offset_end=40),
                                   Wall("B", 3000, offset_start=40, offset_end=-40),
                                   Wall("C", 4000, offset_start=-40, offset_end=40),
                                   Wall("D", 3000, offset_start=40, offset_end=-40)]),
             Room(name="o", closed=False, walls=[Wall("A", 2317, offset_end=13),
                                                 Wall("B", 1911, offset_start=7,
                                                      offset_end=-22),
                                                 Wall("C", 2860)])]
    for name in ("Test.json", "Test_Build.json", "Test_Panels.json", "Corner Unit Test.json",
                 "Test_drawers.json", "Test_3d.json", "Test_export.json"):
        with open(job_file(name), encoding="utf-8") as fh:
            j = job_from_dict(json.load(fh))
        if j.room is not None:
            rooms.append(j.room)
    same = all(wall_frames(r) == _old_frames(r) for r in rooms)
    check(f"wall_frames identical to the old turn, float for float ({len(rooms)} rooms)",
          same, True)
    check("and a 90 is written nowhere: a wall at its defaults writes no new key",
          any(k in job_to_dict(Job(name="k", room=rectangular(4000, 3000)))["room"]["walls"][0]
              for k in ("corner_end", "drawn")), False)

    print("\nan L room: one outside corner")
    ell = Room(name="L", ceiling=2600, walls=[
        Wall("A", 3000), Wall("B", 1000, corner_end=270), Wall("C", 1000), Wall("D", 2000),
        Wall("E", 4000), Wall("F", 3000)])
    check("closes", closure_error(ell), 0)
    check("corners", [(round(x), round(y)) for x, y in corner_points(ell)],
          [(0, 0), (3000, 0), (3000, 1000), (4000, 1000), (4000, 3000), (0, 3000), (0, 0)])
    check("the wall after the outside corner runs back out, into the room on its left",
          to_world(ell, "C", 500, 600), (3500, 1600, 0))
    check("no wall crosses another", crossing_walls(ell), [])

    print("\na hexagon, 120 at every corner")
    hexa = Room(name="hex", walls=[Wall(chr(65 + k), 2000, corner_end=120) for k in range(6)])
    check("closes", closure_error(hexa), 0)
    check("its third corner", [round(v) for v in corner_points(hexa)[2]], [3000, 1732])

    print("\na 135 splay, and a bay out and back (225 / 135)")
    splay = Room(name="splay", walls=[
        Wall("A", 4000), Wall("B", 3000), Wall("C", 3000, corner_end=135),
        Wall("E", 1414, corner_end=135), Wall("D", 2000)])
    check("a chamfered corner closes", closure_error(splay), 0)
    bay = Room(name="bay", walls=[
        Wall("A", 1000, corner_end=225), Wall("B", 707, corner_end=135),
        Wall("C", 1000, corner_end=135), Wall("D", 707, corner_end=225),
        Wall("E", 1000), Wall("F", 3000), Wall("G", 4000), Wall("H", 3000)])
    check("a bay closes", closure_error(bay), 0)
    check("the bay stands out behind the wall line (y < 0)",
          round(corner_points(bay)[2][1]), -500)
    check("a decimal angle is allowed", corner_angle(
        Room(name="d", walls=[Wall("A", 1000, corner_end=112.5)]), 0), 112.5)

    print("\nwalls that cross each other in plan")
    bow = Room(name="bow", ceiling=2600, walls=walls_from_points(
        [(0, 0), (4000, 0), (0, 3000), (4000, 3000)], True))
    for w in bow.walls:
        w.drawn = False
    check("named in pairs", crossing_walls(bow), [("B", "D")])
    bj = Job(name="bow", room=bow)
    check("a critical naming the two walls",
          [(i.level, i.where) for i in _issues(bj, "room-self-intersect")],
          [("critical", "B/D")])
    check("a clean room raises none",
          _issues(Job(name="r", room=rectangular(4000, 3000, ceiling=2600)),
                  "room-self-intersect"), [])

    print("\ndrawn with the mouse")
    rect = walls_from_points([(0, 0), (4000, 0), (4000, 3000), (0, 3000)], True)
    back = walls_from_points([(0, 0), (0, 3000), (4000, 3000), (4000, 0)], True)
    summary = [(w.id, w.length, w.corner_end) for w in rect]
    check("a rectangle", summary, [("A", 4000, 90), ("B", 3000, 90), ("C", 4000, 90),
                                   ("D", 3000, 90)])
    check("drawn anticlockwise comes out clockwise, the first wall drawn still A",
          [(w.id, w.length, w.corner_end) for w in back],
          [("A", 3000, 90), ("B", 4000, 90), ("C", 3000, 90), ("D", 4000, 90)])
    lw = walls_from_points([(0, 0), (3000, 0), (3000, 1000), (4000, 1000), (4000, 3000),
                            (0, 3000)], True)
    check("an L drawn round: its outside corner is 270",
          [w.corner_end for w in lw], [90, 270, 90, 90, 90, 90])
    run = walls_from_points([(0, 0), (3000, 0), (3000, -2000)], False)
    check("an open run turning the other way is walked back, room inside the L",
          [(w.id, w.length, w.corner_end) for w in run], [("A", 2000, 90), ("B", 3000, 90)])
    check("every drawn wall is marked drawn", all(w.drawn for w in rect + run), True)
    dj = Job(name="d", room=Room(name="d", ceiling=2600, walls=rect))
    check("a drawn wall is a critical until it is measured",
          [i.message for i in _issues(dj, "wall-drawn")][:1],
          ["wall A: drawn, not measured — type its length, or tick it as measured"])
    d1 = job_to_dict(dj)
    check("drawn is written while it holds", d1["room"]["walls"][0].get("drawn"), True)
    check("and read back", job_from_dict(json.loads(json.dumps(d1))).room.walls[0].drawn, True)
    for w in dj.room.walls:
        w.drawn = False
    check("measured: nothing raised", _issues(dj, "wall-drawn"), [])
    check("and the key is gone again", "drawn" in job_to_dict(dj)["room"]["walls"][0], False)
    j2 = job_to_dict(Job(name="l", room=ell))
    check("a 270 is written on the wall before its corner, and only there",
          [w.get("corner_end") for w in j2["room"]["walls"]],
          [None, 270, None, None, None, None])
    check("and read back", job_to_dict(job_from_dict(json.loads(json.dumps(j2)))), j2)

    print("\nwhich side is the room on an OPEN run drawn with the mouse")
    from cabinetgen.model import GapChoice
    from cabinetgen.room import flip_side

    def on_room_side(rm, pts, wall_ids):
        """Every point on the room side of each named wall's line."""
        fr = wall_frames(rm)
        return all(((x - fr[w][0][0]) * fr[w][2][0] + (y - fr[w][0][1]) * fr[w][2][1]) >= -0.5
                   for w in wall_ids for x, y in pts)

    def open_l(points):
        rm = Room(name="o", ceiling=2600, closed=False, walls=walls_from_points(points, False))
        j = Job(name="o", room=rm,
                cabinets=[Cabinet(number=1, width=600, height=720, depth=580, kind="base"),
                          Cabinet(number=2, width=600, height=720, depth=580, kind="base")],
                placements=[Placement(1, "A", 1000), Placement(2, "B", 700)])
        fps = [cabinet_footprint(rm, p, c) for c, p in zip(j.cabinets, j.placements)]
        return rm, j, fps

    # the same L on the page, clicked in each direction: right then down, and
    # up then left back along it
    ltr = [(0, 0), (3000, 0), (3000, 2000)]
    rtl = ltr[::-1]
    rm1, _j1, fp1 = open_l(ltr)
    rm2, _j2, fp2 = open_l(rtl)
    check("an L clicked left-to-right: A 3000 then B 2000, one 90 corner",
          [(w.id, w.length, w.corner_end) for w in rm1.walls], [("A", 3000, 90), ("B", 2000, 90)])
    check("clicked right-to-left: the same walls, the same corner",
          [(w.id, w.length, w.corner_end) for w in rm2.walls], [("A", 3000, 90), ("B", 2000, 90)])
    check("left-to-right: both cabinets inside the L, on the room side of BOTH walls",
          [on_room_side(rm1, fp, ["A", "B"]) for fp in fp1], [True, True])
    check("right-to-left: the same", [on_room_side(rm2, fp, ["A", "B"]) for fp in fp2],
          [True, True])
    check("  and they stand in the same places", fp1, fp2)
    down_right = [(0, 0), (0, 2000), (3000, 2000)]
    for name, pts in (("down-then-right", down_right), ("left-then-up", down_right[::-1])):
        rm3, _j3, fp3 = open_l(pts)
        check(f"an L drawn {name}: the room is inside it",
              ([w.corner_end for w in rm3.walls][:1],
               [on_room_side(rm3, fp, ["A", "B"]) for fp in fp3]), ([90], [True, True]))
    straight_a = walls_from_points([(0, 0), (3000, 0)], False)
    straight_b = walls_from_points([(3000, 0), (0, 0)], False)
    check("one straight wall gives no answer: it is taken as drawn, room on the right hand",
          [len(straight_a), len(straight_b), straight_a[0].length], [1, 1, 3000])

    print("\nFlip side: the room on the other side of an open run")
    rm, j, fp_before = open_l(ltr)
    j.cabinets.append(Cabinet(number=3, width=1000, height=720, depth=560, doors=1,
                              corner_unit=True, corner_style="blind", blind_width=500))
    j.placements.append(Placement(3, "A", 2000))
    rm.walls[0].offset_end, rm.walls[1].offset_start = 12, 10
    rm.walls[0].openings.append(Opening("door", 200, 700))
    j.gaps = [GapChoice("A", None, 1, "base", "open")]
    j.plinths = [PlinthChoice("A", "base", 1)]
    first_run = [r for r in runs(j) if r.wall == "A"][0]
    before = job_to_dict(j)
    cut_before = [(p.label, p.length, p.width, p.qty) for p in generate_job(j)]
    flip_side(j)
    check("the walls walked the other way, each keeping its letter",
          [(w.id, w.length) for w in rm.walls], [("B", 2000), ("A", 3000)])
    check("the corner is now 270 from the room's side", [w.corner_end for w in rm.walls][:1], [270])
    check("the offsets swap ends and change sign",
          (rm.walls[0].offset_end, rm.walls[1].offset_start), (-10, -12))
    check("an opening keeps its place along the wall, x from the other end",
          [(o.x, o.width) for o in rm.walls[1].openings], [(2100, 700)])
    by = {p.cabinet: p for p in j.placements}
    check("cabinet 1 keeps its distance from the corner (1400-2000 from it)",
          (by[1].wall, by[1].x), ("A", 1400))
    check("cabinet 2 on B the same, from B's other end", (by[2].wall, by[2].x), ("B", 700))
    check("a blind corner's hand swaps, so its corner end stays in the corner",
          j.cabinets[2].corner_hand, "L")
    check("a gap decision swaps its sides", [(g.after, g.before) for g in j.gaps], [(1, None)])
    check("a plinth decision follows its run to the cabinet that now starts it",
          [(p.wall, p.first) for p in j.plinths], [("A", first_run.cabinets[-1])])
    check("the cut list does not move",
          [(p.label, p.length, p.width, p.qty) for p in generate_job(j)], cut_before)
    check("cabinet 1 now stands on the other face of A (the room's)",
          on_room_side(rm, cabinet_footprint(rm, by[1], j.cabinets[0]), ["A"]), True)
    flip_side(j)
    check("flipped twice: the job file is exactly what it was", job_to_dict(j) == before, True)
    closed = Job(name="c", room=rectangular(4000, 3000))
    try:
        flip_side(closed)
        refused = False
    except ValueError:
        refused = True
    check("a closed room has no other side: refused", refused, True)

    print("\ncorner units only at a nominal 90 inside corner (ruling 4)")
    mitre = Cabinet(number=1, width=850, height=2400, depth=500, back="none", supports=0,
                    doors=1, corner_unit=True, corner_style="mitre",
                    arm_a=850, arm_b=850, face_a=500, face_b=500)
    at135 = Room(name="m", ceiling=2600, walls=[
        Wall("A", 4000, corner_end=135), Wall("B", 3000, corner_end=135),
        Wall("C", 2586), Wall("D", 3000), Wall("E", 4000 - 2121 + 0)])
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
    bj2.cabinets[0].corner_hand = "R"
    bj2.placements[0].x = 0
    bj2.cabinets[0].width = 1000
    bj2.room.walls[1].length = 1000
    check("at the outside corner (the end of B, 270): the critical",
          [i.message for i in _issues(bj2, "corner-unit-angle")],
          ["Corner unit at a 270° corner: construction not ruled."])
    sq = Job(name="s", room=rectangular(4000, 3000, ceiling=2600), cabinets=[mitre],
             placements=[Placement(1, "A", 3150)])
    check("the same mitre in a square room: no critical, and its shadow as before",
          (_issues(sq, "corner-unit-angle"), corner_shadow(sq.room, mitre, sq.placements[0])),
          ([], ("B", 0, 850, 500)))

    print("\nplinth butts at a 90 inside corner only (ruled 29 September 2026)")

    def butt(angle):
        rm = rectangular(4000, 3000, ceiling=2600)
        rm.walls[0].corner_end = angle
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
        rm.walls[0].corner_end = angle
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
    rm.walls[0].corner_end = 135
    ej = Job(name="e", room=rm, cabinets=[base(1)], placements=[Placement(1, "B", 0)])
    prof = return_profiles(ej, "A")
    check("at 135 the return run is seen end on, leaning: 580 deep reads 580 x cos 45",
          [(p["cabinet"], p["x0"], p["x1"]) for p in prof], [(1, 3590, 4000)])
    rm.walls[0].corner_end = 270
    check("at 270 it is behind this wall and not drawn", return_profiles(ej, "A"), [])
    check("the wall elevation draws either way",
          wall_elevation_svg(ej, "A").startswith("<svg"), True)

    print("\n3D and the checks that are already geometry: an angled room")
    rm = Room(name="a", ceiling=2400, walls=[
        Wall("A", 4000, corner_end=135), Wall("B", 2000, corner_end=135),
        Wall("C", 2586), Wall("D", 3414), Wall("E", 4000 - 1414)])
    tall = Cabinet(number=1, width=600, height=2350, depth=600, kind="tall")
    rm.ceiling = 2500              # the tall unit stands (2450) but cannot be tipped up
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
        r = Room(name="s", ceiling=2600, closed=False,
                 walls=[Wall("A", 3000, corner_end=angle), Wall("B", 3000)])
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


if __name__ == "__main__":
    raise SystemExit(main())
