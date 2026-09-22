"""Per-wall elevation regression check.

    python tools/check_elevation.py

The elevation is the first drawing in the app meant to be *read off* — measured
from on site rather than glanced at. A plan that is a little out only looks odd;
a dimension that is wrong gets built.

What is pinned here, and why:

  * Every dimension chain closes. Widths run from the wall's start corner and
    heights from the floor, so the pieces of a chain add up to the wall and the
    ceiling. A chain that does not close is a drawing that is lying.
  * Every standing carcass is on its legs — always, kitchen or wardrobe, plinth
    board or not (corrected 14 Sept 2026). The board only covers the legs and
    must never move a height. One helper, `room.carcass_z`, answers for the
    elevation, the clash check, the opening check and the ceiling check.
  * The ceiling is a required measurement. Without one the job does not export;
    with one, a carcass that will not stand up under it is a critical.
  * The hinge side on the elevation is the hinge the plan swings from.
  * Hinges are drawn 100 mm in from each door end, any middle ones spread
    evenly — a drawing rule only. Nothing that orders, drills or validates may
    read it, and a test here makes sure nothing does.
  * With no room there is no datum, so the side-by-side drawing comes back
    exactly as it was.
"""
import math
import os
import re
import sys

ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, ROOT)

from cabinetgen.engine import generate_job                                    # noqa: E402
from cabinetgen.model import (Cabinet, GapChoice, Job, Obstruction,          # noqa: E402
                              Opening, Panel, Placement, PlinthChoice)
from cabinetgen.render import (elevation_svg, plan_svg,                       # noqa: E402
                               wall_elevation_dims, wall_elevation_svg)
from cabinetgen.room import (above_ceiling, carcass_z, clashes, geometry,      # noqa: E402
                             rectangular, swing_envelopes, tip_clearance, to_world)
from cabinetgen.standard import STANDARD                                      # noqa: E402
from cabinetgen.validate import blocking, validate                            # noqa: E402

FAILS = []


def check(name, got, want):
    ok = got == want
    print(f"  {'ok   ' if ok else 'FAIL '} {name}: {got}" + ("" if ok else f"  want {want}"))
    if not ok:
        FAILS.append(name)


def cab(n, w, h=720, d=580, kind="base", doors=0):
    return Cabinet(number=n, width=w, height=h, depth=d, kind=kind, doors=doors)


def room(ceiling=2700):
    return rectangular(4000, 3000, ceiling=ceiling)


def kitchen():
    """Two base units and an overhead on wall A, one base unit round on wall B."""
    return Job(name="e", room=room(),
               cabinets=[cab(1, 900, doors=2), cab(2, 600, doors=1),
                         cab(3, 900, h=700, d=330, kind="upper", doors=2),
                         cab(4, 600, doors=1)],
               placements=[Placement(1, "A", 0), Placement(2, "A", 1500),
                           Placement(3, "A", 0, z=1500), Placement(4, "B", 0)])


def diffs(chain):
    return [b - a for a, b in zip(chain, chain[1:])]


def dim_labels(svg):
    return set(re.findall(r'class="dim"[^>]*>(\d+)</text>', svg))


def hinge_marks(svg, number, door):
    group = re.search(rf'<g class="hinge" data-cab="{number}" data-door="{door}"[^>]*>(.*?)</g>',
                      svg, re.S)
    return [int(m) for m in re.findall(r'data-mm="(\d+)"', group.group(1))] if group else None


def main() -> int:
    std = STANDARD
    legs = std.leg_height

    print("dimension chains close")
    j = kitchen()
    d = wall_elevation_dims(j, "A")
    check("widths along the floor, from the wall's start corner",
          d["floor_chain"], [0, 900, 1500, 2100, 4000])
    check("and they add up to the wall", sum(diffs(d["floor_chain"])), 4000)
    # 22 September 2026: the top chain used to break only where the overheads
    # do, so past the last one it handed over a single figure spanning every
    # cupboard below it. It reads at the bottom chain's resolution now.
    check("the top chain breaks wherever either run does",
          d["wall_chain"], [0, 900, 1500, 2100, 4000])
    check("and it still closes on the wall", sum(diffs(d["wall_chain"])), 4000)
    check("heights: legs, carcass, up to the overhead, the overhead, to the ceiling",
          d["height_chain"], [0, legs, legs + 720, 1500, 2200, 2700])
    check("which add up to the ceiling", sum(diffs(d["height_chain"])), 2700)
    check("a wall with no overheads draws no overhead chain",
          wall_elevation_dims(j, "B")["wall_chain"], [])

    print("\nevery standing carcass is on its legs, board or no board")
    c = {x.number: x for x in j.cabinets}
    p = {x.cabinet: x for x in j.placements}
    check("a base unit with no plinth board still stands on its legs",
          carcass_z(c[1], p[1], std), legs)
    check("so does a tall unit, which is what a wardrobe is",
          carcass_z(cab(5, 600, h=2100, kind="tall"), Placement(5, "A", 0), std), legs)
    check("a hung unit is where it was hung", carcass_z(c[3], p[3], std), 1500)
    before = wall_elevation_dims(j, "A")["height_chain"]
    j.plinths = [PlinthChoice("A", "base", 1)]
    check("fitting a plinth board moves no height at all",
          wall_elevation_dims(j, "A")["height_chain"], before)
    check("the carcass stays where the legs put it", carcass_z(c[1], p[1], std), legs)

    print("\nthe drawing")
    j = kitchen()
    j.room.walls[0].openings.append(Opening("window", 2400, 1200, sill=900, head=2100))
    j.room.walls[0].obstructions.append(Obstruction("waste", 1800, 300, 110, 110))
    svg = wall_elevation_svg(j, "A")
    check("is an svg", svg.startswith("<svg") and svg.rstrip().endswith("</svg>"), True)
    check("draws the cabinets on this wall",
          all(f'class="ecab" data-cab="{n}"' in svg for n in (1, 2, 3)), True)
    check("and not the one round the corner", 'class="ecab" data-cab="4"' in svg, False)
    # "3100" was the old top chain's one figure past the last overhead. It is
    # broken at every cupboard now, so the top reads 900 / 600 / 600 / 1900 —
    # the bottom's own segments, which is the point.
    want = {"900", "600", "1900", "4000", str(legs), "720", "680", "700", "500"}
    check("every chain segment is labelled", sorted(want - dim_labels(svg)), [])
    check("and nothing spans several cupboards at the top any more",
          "3100" in dim_labels(svg), False)
    check("the window, with its sill and head", "sill 900 · head 2100" in svg, True)
    check("the waste, with where to find it", "waste @ 1800, 300 up" in svg, True)
    check("the space under an unboarded run says it is legs", ">legs</text>" in svg, True)

    print("\nhinges: side and count from the order, positions for the drawing only")
    sides = dict(re.findall(r'data-cab="(\d+)" data-door="\d+" data-side="(L|R)"', svg))
    pair = re.findall(r'data-cab="1" data-door="(\d)" data-side="(L|R)"', svg)
    check("a pair hangs from its outer edges", pair, [("0", "L"), ("1", "R")])
    check("a single door hangs left by default", sides.get("2"), "L")
    j.placements[1].flip = True
    flipped = wall_elevation_svg(j, "A")
    check("and right when the placement is flipped",
          re.findall(r'data-cab="2" data-door="0" data-side="(L|R)"', flipped), ["R"])
    for flip in (False, True):
        j.placements[1].flip = flip
        cab2, p2 = j.cabinets[1], j.placements[1]
        hinge = swing_envelopes(j, cab2, p2, std)[0][0]
        plan_side = "L" if hinge == to_world(j.room, "A", p2.x, cab2.depth)[:2] else "R"
        drawn = re.findall(r'data-cab="2" data-door="0" data-side="(L|R)"',
                           wall_elevation_svg(j, "A"))
        check(f"the elevation hangs it where the plan swings it (flip={flip})",
              drawn, [plan_side])
    door = 720 - std.door_height_gap
    check("the hinge count is the pot-hole figure on the order",
          f"{std.hinges(door)} hinges" in svg, True)
    check(f"two hinges on a {door} mm door, {std.hinge_inset_drawn} mm in from each end",
          hinge_marks(svg, 1, 0), [100, door - 100])
    check("a 2097 mm door takes four", std.hinges(2097), 4)
    four = std.hinge_positions(2097)
    check("outer two 100 mm from the ends, middle two spreading the rest evenly",
          four, [100, 732, 1365, 1997])
    check("evenly, to the millimetre", max(diffs(four)) - min(diffs(four)) <= 1, True)
    wardrobe = Job(name="w", room=room(), cabinets=[cab(6, 600, h=2100, kind="tall", doors=1)],
                   placements=[Placement(6, "A", 0)])
    check("and that is what the elevation draws on it",
          hinge_marks(wall_elevation_svg(wardrobe, "A"), 6, 0), four)
    check("the drawing says the positions are not a drilling reference",
          "not a drilling reference" in svg, True)
    readers = [f for f in ("engine.py", "export_plaza.py", "validate.py", "nest.py")
               if re.search(r"hinge_positions|hinge_inset_drawn",
                            open(os.path.join(ROOT, "cabinetgen", f), encoding="utf-8").read())]
    check("nothing that orders, drills or validates reads the drawn positions", readers, [])

    print("\nchosen parts appear, and only chosen ones")
    j = kitchen()
    check("no plinth board drawn unless one was asked for",
          wall_elevation_svg(j, "A").count('class="plinth"'), 0)
    j.plinths = [PlinthChoice("A", "base", 1)]
    check("a plinth board when it was", wall_elevation_svg(j, "A").count('class="plinth"'), 1)
    j = kitchen()
    j.gaps = [GapChoice("A", 1, 2, "base", "filler")]
    check("a filler where one was chosen", wall_elevation_svg(j, "A").count('class="filler"'), 1)
    j.gaps = [GapChoice("A", 1, 2, "base", "open")]
    check("nothing where the gap was left open",
          wall_elevation_svg(j, "A").count('class="filler"'), 0)

    print("\ncollisions are drawn red")
    j = kitchen()
    j.placements[1].x = 800
    rect = re.search(r'<rect class="ecab" data-cab="2"[^>]*>', wall_elevation_svg(j, "A")).group(0)
    check("an overlapping carcass", 'stroke="#a4303f"' in rect, True)

    print("\nthe ceiling is a required measurement")
    unmeasured = kitchen()
    unmeasured.room.ceiling = None
    issues = validate(unmeasured, [])
    check("a room without one is a critical",
          [(i.level, i.message) for i in issues if "not measured" in i.message],
          [("critical", "ceiling height not measured — it is a required site "
                        "measurement, and the ceiling check means nothing without it")])
    check("so the job will not export", blocking(issues), True)
    check("nothing is compared against a ceiling that was never measured",
          above_ceiling(unmeasured, std), [])
    s = wall_elevation_svg(unmeasured, "A")
    check("the elevation still draws, and says what is missing",
          s.startswith("<svg") and "ceiling NOT MEASURED" in s, True)
    check("its height chain closes on the tallest carcass instead",
          wall_elevation_dims(unmeasured, "A")["height_chain"][-1], 2200)

    print("\nheights against a measured ceiling")
    def standing(h, plinth=False):
        jj = Job(name="t", room=room(), cabinets=[cab(5, 600, h=h, kind="tall")],
                 placements=[Placement(5, "A", 2500)])
        if plinth:
            jj.plinths = [PlinthChoice("A", "base", 5)]      # a tall unit is in the floor run
        return [(i.level, i.message) for i in validate(jj, []) if "above the" in i.message]
    check("2550 on its legs tops out at 2650 and fits", standing(2550), [])
    check("2650 on its legs does not — a critical, with no board needed to cause it",
          standing(2650),
          [("critical", "top of the carcass is at 2750 mm, above the 2700 mm ceiling")])
    check("and a board makes no difference either way",
          standing(2650, plinth=True), standing(2650))

    print("\ntip-up: built flat on its back, tipped upright on its legs")
    check("a 2400 wardrobe, 580 deep, on 100 mm legs needs sqrt(580² + 2500²)",
          tip_clearance(2400, 580, 100), math.ceil(math.hypot(580, 2500)))
    check("which is more than it stands at: 2500 standing, 2567 on the way up",
          (2400 + legs, tip_clearance(2400, 580, 100)), (2500, 2567))
    check("rear legs set further in need less, but never less than standing height",
          2500 < tip_clearance(2400, 580, 100, 100) < tip_clearance(2400, 580, 100), True)
    check("no leg position between the faces needs more than legs at the back edge",
          all(tip_clearance(h, 580, 100, s) <= tip_clearance(h, 580, 100)
              for h in (720, 900, 2100, 2400) for s in range(0, 581, 20)), True)
    check("with the rear legs well in, a base unit's back-edge pivot can govern",
          tip_clearance(720, 580, 100, 200), math.ceil(math.hypot(580, 720)))

    def tipping(c, ceiling, z=0):
        jj = Job(name="t", room=room(ceiling), cabinets=[c],
                 placements=[Placement(c.number, "A", 2500, z=z)])
        return [(i.level, i.message) for i in validate(jj, []) if "tipped" in i.message]
    wardrobe_2400 = cab(5, 600, h=2400, kind="tall")
    check("the check uses the ruled rear leg setback", std.leg_setback, 50)
    check("which puts the wardrobe's sweep at 2556, inside the 2567 legs-at-the-edge bound",
          tip_clearance(2400, 580, 100, std.leg_setback), 2556)
    check("a 2600 ceiling clears the 2556 sweep, so that is fine",
          tipping(wardrobe_2400, 2600), [])
    check("under a 2550 ceiling it stands, but cannot be tipped up — a critical",
          tipping(wardrobe_2400, 2550),
          [("critical", "stands at 2500 mm but cannot be tipped upright under the 2550 mm "
                        "ceiling — built flat, it needs 2556 mm to come up")])
    check("under 2556 it just comes up", tipping(wardrobe_2400, 2556), [])

    print("\ntip-up: a bespoke carcass tips on its deepest panel, not its declared depth")
    corner = Cabinet(number=7, width=850, height=2400, depth=500, kind="tall",
                     template="none", back="none", bespoke=[
                         Panel(7, "01a", "Side", "MEL", 2400, 500, 2),
                         Panel(7, "01b", "Side", "MEL", 2400, 818, 1),
                         Panel(7, "01c", "Side", "MEL", 2400, 834, 1),
                         Panel(7, "02", "Top", "MEL", 818, 818, 1),
                         Panel(7, "07", "Door", "BROOKHILL", 2397, 472, 1, grain=1)])
    g = geometry(corner)
    check("the corner unit declares 500 but its deepest side is 834",
          (corner.depth, g.tip_depth), (500, 834))
    check("and declares 850, which its 818 top plus two sides confirms", g.width, 850)
    corner_job = Job(name="c", room=room(2600), cabinets=[corner],
                     placements=[Placement(7, "A", 0)])
    before = [(p.code, p.length, p.width) for p in corner.bespoke]
    generate_job(corner_job)
    check("the cut list leaves its designations exactly as defined",
          [(p.code, p.length, p.width) for p in corner.bespoke], before)
    check("which decides a 2600 ceiling: 2541 on the declared depth, 2621 on the real one",
          (tip_clearance(2400, 500, 100, 50), tip_clearance(2400, 834, 100, 50)), (2541, 2621))
    check("so under 2600 the corner unit is caught",
          [i.level for i in validate(corner_job, []) if "tipped" in i.message], ["critical"])
    check("a template carcass tips on its declared depth, which is what its sides are",
          geometry(cab(1, 900)).tip_depth, 580)
    check("and a bespoke carcass with no carcass panels falls back to its declared depth",
          geometry(Cabinet(number=8, width=600, height=720, depth=580, template="none",
                           bespoke=[Panel(8, "07", "Door", "BROOKHILL", 717, 597, 1, grain=1)])).tip_depth,
          580)
    check("too tall to stand is not also reported as too tall to tip",
          tipping(cab(5, 600, h=2600, kind="tall"), 2650), [])
    check("a wall unit is tipped up with no legs: sqrt(300² + 700²) = 762",
          tipping(cab(7, 600, h=700, d=300, kind="upper"), 750, z=0),
          [("critical", "stands at 700 mm but cannot be tipped upright under the 750 mm "
                        "ceiling — built flat, it needs 762 mm to come up")])

    print("\nopenings: the legs count")
    def under_window(c, z=0):
        rm = room()
        rm.walls[0].openings.append(Opening("window", 1000, 1200, sill=900, head=2100))
        jj = Job(name="w", room=rm, cabinets=[c],
                 placements=[Placement(c.number, "A", 1200, z=z)])
        return [i.message for i in validate(jj, []) if "stands across" in i.message]
    check("a 720 unit tops out at 820 on its legs, clear of a 900 sill",
          under_window(cab(6, 600)), [])
    check("an 800 unit reaches the sill exactly: touching, not across",
          under_window(cab(6, 600, h=800)), [])
    check("a 900 unit clears the sill on paper but not on its legs",
          under_window(cab(6, 600, h=900)), ["stands across the window on wall A (1000-2200)"])
    check("an overhead hung across the window is across it",
          under_window(cab(6, 600, h=700, d=330, kind="upper"), z=1400),
          ["stands across the window on wall A (1000-2200)"])

    print("\nthe clash check stands on the legs too")
    def overhead_at(z, plinth=False):
        jj = Job(name="c", room=room(),
                 cabinets=[cab(1, 900), cab(2, 600, h=700, d=330, kind="upper", doors=1)],
                 placements=[Placement(1, "A", 2000), Placement(2, "A", 2000, z=z)])
        if plinth:
            jj.plinths = [PlinthChoice("A", "base", 1)]
        return [x.against for x in clashes(jj, std) if x.cabinet == 2]
    check("an overhead door at 780 fouls a base unit topping out at 820 on its legs",
          overhead_at(780), ["cabinet 1"])
    check("with a plinth board or without", overhead_at(780, plinth=True), ["cabinet 1"])
    check("hung at 830 it clears", overhead_at(830), [])

    print("\nno room, no datum")
    plain = kitchen()
    plain.room, plain.placements = None, []
    check("falls back to the side-by-side drawing, byte for byte",
          wall_elevation_svg(plain, "A") == elevation_svg(plain), True)
    check("an unknown wall says so instead of crashing",
          "No wall Q" in wall_elevation_svg(kitchen(), "Q"), True)

    print("\nnames from the job file are text, not markup")
    j = kitchen()
    j.room.walls[0].openings.append(Opening("<b>x</b>", 2400, 600))
    for label, drawing in (("elevation", wall_elevation_svg(j, "A")), ("plan", plan_svg(j))):
        check(f"escaped in the {label}", "<b>" not in drawing and "&lt;b&gt;" in drawing, True)

    print("\nthe runs either side, seen end on (18 Sept 2026)")
    from cabinetgen.room import rectangular, return_profiles              # noqa: E402
    from cabinetgen.model import Cabinet as _Cab, Job as _Job, Placement as _Pl  # noqa: E402
    ra = _Cab(1, 600, 720, 580, kind="base")
    rb = _Cab(2, 600, 2100, 580, kind="tall")
    rc = _Cab(3, 600, 720, 580, kind="base")
    rj = _Job(name="r", cabinets=[ra, rb, rc], room=rectangular(4000, 3000, ceiling=2600),
              placements=[_Pl(1, "A", 3400), _Pl(2, "A", 0), _Pl(3, "B", 700)])
    prof = return_profiles(rj, "B")
    check("face on to B, wall A's cabinets show end on at B's start corner",
          sorted((r["cabinet"], r["x0"], r["x1"]) for r in prof),
          [(1, 0, 580), (2, 0, 580)])
    check("at their real heights, legs included",
          sorted((r["cabinet"], r["z0"], r["height"]) for r in prof),
          [(1, 100, 720), (2, 100, 2100)])
    check("the one nearest the viewer — furthest out from B — is drawn last",
          [r["cabinet"] for r in prof], [1, 2])
    check("B's own cabinet is not a profile on B",
          any(r["cabinet"] == 3 for r in prof), False)
    check("and face on to A, B's cabinet shows at A's far end",
          [(r["cabinet"], r["x0"], r["x1"]) for r in return_profiles(rj, "A")],
          [(3, 3420, 4000)])
    check("the opposite wall is behind the viewer, so C sees B's run and nothing of A",
          sorted({r["wall"] for r in return_profiles(rj, "C")}), ["B"])
    rsvg = wall_elevation_svg(rj, "B")
    check("the drawing carries them as their own class, not as draggable cabinets",
          (rsvg.count('class="eside"'), 'data-cab="1"' in rsvg.split('class="eside"')[0]),
          (2, False))

    print(f"\n{'ALL OK' if not FAILS else str(len(FAILS)) + ' FAILED: ' + str(FAILS)}")
    return 1 if FAILS else 0


if __name__ == "__main__":
    raise SystemExit(main())
