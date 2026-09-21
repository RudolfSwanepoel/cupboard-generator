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
"""
import json
import math
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

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
    check("wall units draw dashed", 'stroke-dasharray="5 3"' in plan_svg(j), True)
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
    check("an opening breaks the wall into two runs", s2.count("stroke-width=\"3\""), 5)
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

    print(f"\n{'ALL OK' if not FAILS else str(len(FAILS)) + ' FAILED: ' + str(FAILS)}")
    return 1 if FAILS else 0


if __name__ == "__main__":
    raise SystemExit(main())
