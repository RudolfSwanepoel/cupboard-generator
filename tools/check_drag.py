"""Placement regression check: overlaps, snap targets, door swings, pull-outs.

    python tools/check_drag.py

Phase 4 lets a cabinet be dragged, and the spec's rule for that is blunt: the
browser computes no dimension. Every position a drag can settle on comes from
`snap_points`, and every clash it can cause is found here, in the engine. So
these are the numbers the interface is only allowed to pick between.

The geometry worth being careful about:

  * Touching is not overlapping. A cabinet butted against its neighbour is the
    normal case; only a genuine intersection is a collision.
  * Different layers cannot collide in plan. An overhead sitting above a base
    run is the point of drawing them on top of each other, not a fault.
  * A door swings away from its own wall, so it can never foul it — but it can
    easily foul the return wall, and that is the check worth having.
  * Heights matter. A base unit's door does not care about a wall unit two
    courses above it.
"""
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import json                                                                 # noqa: E402

from cabinetgen.engine import generate_job                                  # noqa: E402
from cabinetgen.model import Cabinet, Drawer, Job, Opening, Panel, Placement  # noqa: E402
from cabinetgen.room import (clashes, convex_overlap, corner_outline,       # noqa: E402
                             corner_shadow, gaps as room_gaps, geometry,
                             overlaps, polygons_overlap, pullout_envelope,
                             rectangular, runs as room_runs, snap_points,
                             swing_envelopes, triangulate)
from cabinetgen.standard import STANDARD                                    # noqa: E402
from cabinetgen.store import job_to_dict                                    # noqa: E402
from cabinetgen.validate import validate                                    # noqa: E402

FAILS = []


def check(name, got, want):
    ok = got == want
    print(f"  {'ok   ' if ok else 'FAIL '} {name}: {got}" + ("" if ok else f"  want {want}"))
    if not ok:
        FAILS.append(name)


def cab(n, w, d=580, h=720, kind="base", doors=0, drawers=0):
    c = Cabinet(number=n, width=w, height=h, depth=d, kind=kind, doors=doors)
    if drawers:
        c.drawers = [Drawer(150, 120) for _ in range(drawers)]
    return c


def job(cabs, places, room=None):
    return Job(name="d", room=room or rectangular(4000, 3000),
               cabinets=cabs, placements=places)


def corner_cab(number, arm_a=850, arm_b=850, face_a=500, face_b=500,
               style="mitre", doors=1, height=2400, side_b=None, wall_sides=None):
    """A parametric corner unit like cabinet 7 of the October fixture, cut down
    to just enough bespoke panels to exercise the geometry: the two open-face
    sides, the two wall sides (one board short of arm_a and two short of arm_b,
    because one wraps the other, unless `wall_sides` says otherwise) and a door
    across the mitre."""
    door_len = round(math.hypot(arm_a - face_b, arm_b - face_a)) - 23
    t = STANDARD.board_t
    wall_a, wall_b = wall_sides or (arm_a - t, arm_b - 2 * t)
    bespoke = [Panel(number, "01a", "Side", "MEL", height, face_a, 1),
               Panel(number, "01b", "Side", "MEL", height,
                     face_b if side_b is None else side_b, 1),
               Panel(number, "01c", "Side", "MEL", height, wall_a, 1),
               Panel(number, "01d", "Side", "MEL", height, wall_b, 1)]
    if doors:
        bespoke.append(Panel(number, "07", "Door", "DECOR", height - 3, door_len,
                             doors, grain=1))
    return Cabinet(number=number, width=arm_a, height=height, depth=face_a,
                   kind="tall", back="none", template="none",
                   corner_style=style, arm_a=arm_a, arm_b=arm_b,
                   face_a=face_a, face_b=face_b, bespoke=bespoke)


def main() -> int:
    std = STANDARD

    print("overlaps")
    j = job([cab(1, 900), cab(2, 600)], [Placement(1, "A", 0), Placement(2, "A", 900)])
    check("butted neighbours are not a collision", overlaps(j), [])
    j = job([cab(1, 900), cab(2, 600)], [Placement(1, "A", 0), Placement(2, "A", 800)])
    o = overlaps(j)
    check("a real overlap is found", [(x.a, x.b, x.mm) for x in o], [(1, 2, 100)])
    check("and it is a critical",
          [i.level for i in validate(j, []) if "overlap" in i.message], ["critical"])
    j = job([cab(1, 900), cab(2, 600, d=330, h=700, kind="upper")],
            [Placement(1, "A", 0), Placement(2, "A", 0, z=1500)])
    check("an overhead over a base run is not a collision", overlaps(j), [])
    j = job([cab(1, 900), cab(2, 600)], [Placement(1, "A", 0), Placement(2, "B", 0)])
    check("nor are cabinets on different walls", overlaps(j), [])
    j = job([cab(1, 900), cab(2, 600, h=2100, kind="tall")],
            [Placement(1, "A", 0), Placement(2, "A", 600)])
    check("but a tall unit standing into a base unit is — it is heights, not layers",
          [(o.a, o.b, o.mm) for o in overlaps(j)], [(1, 2, 300)])
    j = job([cab(1, 900, h=2100, kind="tall"), cab(2, 600, d=330, h=700, kind="upper")],
            [Placement(1, "A", 0), Placement(2, "A", 600, z=1500)])
    check("and so is an overhead hung into a tall unit",
          [(o.a, o.b) for o in overlaps(j)], [(1, 2)])

    print("\nsnap points come from the engine")
    j = job([cab(1, 900), cab(2, 600)], [Placement(1, "A", 0), Placement(2, "A", 2000)])
    snaps = snap_points(j, 2, "A", std)
    xs = [s["x"] for s in snaps]
    check("the wall's start", 0 in xs, True)
    check("the wall's end, allowing for the cabinet's width",
          4000 - 600 in xs, True)
    check("butted to the right of cabinet 1", 900 in xs, True)
    check("every candidate leaves the cabinet on the wall",
          all(0 <= x <= 4000 - 600 for x in xs), True)
    check("and they are unique and in order", xs == sorted(set(xs)), True)

    rm = rectangular(4000, 3000)
    rm.walls[0].openings.append(Opening("door", 1500, 900))
    j = job([cab(1, 600)], [Placement(1, "A", 0)], room=rm)
    why = {s["x"]: s["why"] for s in snap_points(j, 1, "A", std)}
    check("clear of the far side of an opening", why.get(2400), "clear of the door")
    check("clear of the near side too", why.get(900), "clear of the door")

    print("\nthe separating-axis test")
    box = [(0, 0), (100, 0), (100, 100), (0, 100)]
    check("overlapping boxes", convex_overlap(box, [(50, 50), (150, 50),
                                                    (150, 150), (50, 150)]), True)
    check("touching edge to edge is clear",
          convex_overlap(box, [(100, 0), (200, 0), (200, 100), (100, 100)]), False)
    check("apart is clear", convex_overlap(box, [(200, 200), (300, 200),
                                                 (300, 300), (200, 300)]), False)

    print("\ndoor swings")
    j = job([cab(1, 600, doors=1)], [Placement(1, "A", 0)])
    env = swing_envelopes(j, j.cabinets[0], j.placements[0], std)
    check("a single door sweeps one quarter disc", len(env), 1)
    j.cabinets[0].doors = 2
    check("a pair sweeps two",
          len(swing_envelopes(j, j.cabinets[0], j.placements[0], std)), 2)
    j.cabinets[0].doors = 0
    check("a cabinet with no doors sweeps nothing",
          swing_envelopes(j, j.cabinets[0], j.placements[0], std), [])

    print("\na door in the open, and one at a corner")
    j = job([cab(1, 600, doors=1)], [Placement(1, "A", 2000)])
    check("out in the open it is clear", clashes(j, std), [])
    # Hinged at the start corner, the door pivots on the corner and finishes flat
    # against the return wall. It grazes it; it does not swing through it.
    j = job([cab(1, 600, doors=1)], [Placement(1, "A", 0)])
    check("a door hinged at a corner opens flat against the return, not into it",
          clashes(j, std), [])
    check("and never fouls its own wall",
          any(c.against == "wall A" for c in clashes(j, std)), False)

    print("\na door against the return run — the case worth catching")
    # cabinet 1 at the end of wall A, right-hinged, swinging across the corner
    # into a cabinet standing on wall B
    j = job([cab(1, 600, doors=1), cab(3, 600)],
            [Placement(1, "A", 3000, flip=True), Placement(3, "B", 0)])
    hits = {(c.kind, c.against) for c in clashes(j, std)}
    check("the swing reaches the cabinet on the return wall",
          ("door", "cabinet 3") in hits, True)
    check("which is a warning, not a critical",
          sorted({i.level for i in validate(j, []) if "fouls" in i.message}),
          ["warning"])

    print("\na door against the run opposite, in a galley")
    narrow = rectangular(4000, 900)          # only 900 mm across the room
    j = job([cab(1, 600, doors=1), cab(2, 600, doors=0)],
            [Placement(1, "A", 1000), Placement(2, "C", 2400)], room=narrow)
    hits = {(c.cabinet, c.against) for c in clashes(j, std)}
    check("the swing reaches the cabinet opposite", (1, "cabinet 2") in hits, True)
    check("and the wall behind it", (1, "wall C") in hits, True)
    wide = rectangular(4000, 3000)
    j = job([cab(1, 600, doors=1), cab(2, 600, doors=0)],
            [Placement(1, "A", 1000), Placement(2, "C", 2400)], room=wide)
    check("given room to open, nothing is flagged", clashes(j, std), [])

    print("\nheights are respected")
    j = job([cab(1, 900, doors=2), cab(2, 600, d=330, h=700, kind="upper")],
            [Placement(1, "A", 0), Placement(2, "A", 0, z=1500)])
    check("a base door ignores a wall unit above it",
          [c for c in clashes(j, std) if c.against == "cabinet 2"], [])

    print("\ndrawer pull-out")
    j = job([cab(1, 600, doors=0, drawers=3)], [Placement(1, "A", 1000)])
    env = pullout_envelope(j, j.cabinets[0], j.placements[0], std)
    check("reaches out by the runner the engine picked",
          env is not None and len(env) == 4, True)
    j = job([cab(1, 600)], [Placement(1, "A", 1000)])
    check("no drawers, no envelope",
          pullout_envelope(j, j.cabinets[0], j.placements[0], std), None)
    narrow = rectangular(4000, 800)
    j = job([cab(1, 600, drawers=3), cab(2, 600)],
            [Placement(1, "A", 1000), Placement(2, "C", 2400)], room=narrow)
    check("a pull-out that hits the run opposite is caught",
          any(c.kind == "drawer" and c.against == "cabinet 2"
              for c in clashes(j, std)), True)
    j = job([cab(1, 600, drawers=3), cab(2, 600)],
            [Placement(1, "A", 1000), Placement(2, "C", 2400)],
            room=rectangular(4000, 3000))
    check("in a room with space, it is clear", clashes(j, std), [])

    print("\nany shape: an outline is a polygon, and a corner box is an L")
    # a 850 x 834 corner box with a 250 x 254 notch out of its front-left corner
    L = [[0, 580], [250, 580], [250, 834], [850, 834], [850, 0], [0, 0]]
    corner = Cabinet(number=7, width=850, height=2400, depth=500, kind="tall",
                     template="none", back="none", footprint=L, bespoke=[
                         Panel(7, "01a", "Side", "MEL", 2400, 500, 2),
                         Panel(7, "01c", "Side", "MEL", 2400, 834, 1),
                         Panel(7, "02", "Top", "MEL", 818, 818, 1)])
    g = geometry(corner)
    check("the outline is read as entered", (g.source, len(g.footprint)), ("outline", 6))
    check("and gives the checks 850 along the wall and 834 out, not the declared 500",
          (g.width, g.depth), (850, 834))
    check("the L splits into triangles", len(triangulate(L)), 4)
    check("a rectangle is a rectangle in the same type",
          (geometry(cab(1, 900)).source, len(geometry(cab(1, 900)).footprint)), ("panels", 4))
    notch = [(0, 580), (250, 580), (250, 834), (0, 834)]
    check("a shape tucked exactly into the notch does not overlap the L",
          polygons_overlap(L, notch), False)
    check("pushed 1 mm into the L's leg, it does",
          polygons_overlap(L, [(0, 580), (251, 580), (251, 834), (0, 834)]), True)
    check("the same shape twice overlaps", polygons_overlap(L, L), True)
    check("touching along a whole edge is clear",
          polygons_overlap(L, [(850, 0), (1450, 0), (1450, 580), (850, 580)]), False)

    j = job([corner, cab(2, 600)], [Placement(7, "A", 0), Placement(2, "A", 850)])
    check("a straight unit butted to the corner box is clear", overlaps(j), [])
    j = job([corner, cab(2, 600)], [Placement(7, "A", 0), Placement(2, "A", 600)])
    check("pushed into the box's leg it collides, reported by the outlines not the spans",
          [(o.a, o.b) for o in overlaps(j)], [(7, 2)])
    j = job([corner, cab(2, 600)], [Placement(7, "A", 0), Placement(2, "A", 0)])
    check("the whole overlap is the extent along the wall", overlaps(j)[0].mm, 600)

    print("\na parametric corner: derived, not typed")
    # the October fixture's cabinet 7: arm_a/arm_b 850, face_a/face_b 500, mitre
    check("the outline is the spec's worked example",
          corner_outline("mitre", 850, 850, 500, 500),
          [(0, 0), (850, 0), (850, 850), (350, 850), (0, 500)])
    check("a face wider than the arm it has to fit inside describes nothing",
          corner_outline("mitre", 850, 850, 900, 500), None)
    seven = corner_cab(7)
    g = geometry(seven)
    check("geometry reads it off the corner parameters, not a typed outline",
          (g.source, g.footprint), ("corner", corner_outline("mitre", 850, 850, 500, 500)))
    check("and gives the checks 850 x 850, the bounding box a fallback would miss",
          (g.width, g.depth), (850, 850))

    print("\nthe mitre angle and face lengths are outputs, never inputs")
    from jobs.wardrobe_oct2025 import JOB as OCT
    g7 = geometry(next(c for c in OCT.cabinets if c.number == 7))
    check("the October corner unit's mitre comes out at 45: 850 - 500 on both arms",
          g7.mitre_deg, 45.0)
    check("its door face is 350 root 2", g7.face_lengths, [495])
    check("which takes its 472 door with a 23 mm reveal, as spec item 14 has it",
          g7.face_lengths[0] - g7.door_widths[0], 23)
    check("a 600 run meeting a 500 run makes whatever angle the geometry makes",
          geometry(corner_cab(20, arm_a=1000, arm_b=1000, face_a=600, face_b=500)).mitre_deg, 38.7)
    check("there is no angle to enter", [f for f in Cabinet.__dataclass_fields__ if "angle" in f], [])
    ell = geometry(corner_cab(21, arm_a=1000, arm_b=1000, face_a=600, face_b=500, style="ell"))
    check("an ell has two faces off its notch and no mitre", (ell.face_lengths, ell.mitre_deg), ([500, 400], None))
    check("a straight cabinet has neither", (geometry(cab(22, 600)).face_lengths,
                                             geometry(cab(22, 600)).mitre_deg), ([], None))

    print("\nits door hinges off the mitre edge, not the outline's extreme corner")
    room = rectangular(4000, 3000, ceiling=2700)
    # flush in the corner: cabinet-local x = arm_a lands exactly on wall A's end
    flush = job([seven], [Placement(7, "A", 3150)], room=room)
    env = swing_envelopes(flush, seven, flush.placements[0], STANDARD)
    check("one door, one envelope", len(env), 1)
    check("unflipped, it hinges at the wall-A end of the mitre edge",
          env[0][0], (3150, 500))
    flipped = job([seven], [Placement(7, "A", 3150, flip=True)], room=room)
    check("flipped, it hinges at the wall-B end instead",
          swing_envelopes(flipped, seven, flipped.placements[0], STANDARD)[0][0],
          (3500, 850))
    check("never at the outline's own far corner, which is not on the door face at all",
          swing_envelopes(flush, seven, flush.placements[0], STANDARD)[0][0] != (3150, 850),
          True)

    print("\na flush corner unit fills the start of the next wall's run")
    straight = cab(2, 600)
    # 850 (the corner's shadow) + a real 150 mm gap before cabinet 2
    gapped = job([seven, straight], [Placement(7, "A", 3150), Placement(2, "B", 1000)],
                room=room)
    b_gaps = [(g.after, g.before, g.x, g.nominal) for g in room_gaps(gapped, STANDARD)
             if g.wall == "B"]
    check("the gap starts where the corner's shadow ends, not at the wall's start",
          (7, 2, 850, 150) in b_gaps, True)
    check("and there is no separate 'wall start' gap under the corner unit",
          any(after is None for after, _b, _x, _n in b_gaps), False)
    flush_next = job([seven, straight], [Placement(7, "A", 3150), Placement(2, "B", 850)],
                     room=room)
    check("butted flush against the shadow, the 850 mm gap is gone, not just resized",
          [g for g in room_gaps(flush_next, STANDARD) if g.wall == "B" and g.after == 7], [])
    b_runs = [r for r in room_runs(flush_next, STANDARD) if r.wall == "B"]
    check("wall B's run is seen as starting at the corner, cabinet 7 included",
          (b_runs[0].cabinets, b_runs[0].x0, b_runs[0].touches_start), ([7, 2], 0, True))
    check("without the corner unit, the same wall shows the naive 1000 mm gap at its start",
          [(g.after, g.before, g.nominal) for g in room_gaps(job([straight], [Placement(2, "B", 1000)], room=room), STANDARD)
           if g.wall == "B" and g.after is None],
          [(None, 2, 1000)])
    check("not flush in the corner, there is no shadow to find",
          corner_shadow(room, seven, Placement(7, "A", 3000), STANDARD), None)

    print("\nand overlaps are checked across the corner, not only within one wall")
    inside_shadow = job([seven, straight], [Placement(7, "A", 3150), Placement(2, "B", 400)],
                        room=room)
    check("a cabinet placed into the shadow's own space is a real, cross-wall overlap",
          [(o.a, o.b) for o in overlaps(inside_shadow)], [(7, 2)])

    print("\nvalidation of the corner parameters themselves")
    unresolved = corner_cab(9, face_b=900)          # wider than the arm it has to fit inside
    j = job([unresolved], [Placement(9, "A", 3150)], room=room)
    crits = [i.message for i in validate(j, []) if i.level == "critical" and "9" in i.where]
    check("parameters that cannot resolve to a shape are a critical, not a silent fallback",
          any("corner parameters do not resolve" in m for m in crits), True)
    mismatched = corner_cab(11, face_a=500, face_b=400, side_b=450)  # 01b cut 450, not 400
    j = job([mismatched], [Placement(11, "A", 3150)], room=room)
    warns = [i.message for i in validate(j, []) if str(11) == i.where]
    check("a face that matches no side panel is a warning naming the mismatch",
          any("face_b is 400 but no side panel is cut that wide" in m for m in warns), True)
    j = job([seven], [Placement(7, "A", 3150)], room=room)
    check("a resolved corner unit whose panels agree raises nothing about its outline",
          [i for i in validate(j, []) if str(7) == i.where and
           ("outline" in i.message or "corner parameters" in i.message or "side panel" in i.message)],
          [])

    print("\nthe arms are checked against the wall sides, one wrapping the other")
    from dataclasses import replace as dc_replace
    from jobs.wardrobe_oct2025 import JOB as OCT
    oct7 = next(c for c in OCT.cabinets if c.number == 7)

    def wall_side_warnings(c):
        jj = job([c], [Placement(7, "A", 4000 - c.arm_a)], room=room)
        return [i.message for i in validate(jj, []) if i.where == "7" and "wall sides" in i.message]
    check("cabinet 7's 850 arms agree with its 834 and 818 sides", wall_side_warnings(oct7), [])
    msgs = wall_side_warnings(dc_replace(oct7, arm_a=900))
    check("an arm mistyped as 900 disagrees with them, and the warning says what it wanted",
          len(msgs) == 1 and "want wall sides of 884 and 818 (or 868 and 834)" in msgs[0]
          and "[818, 834]" in msgs[0], True)
    check("a wall side cut a board short on the wrong wall still agrees — either may wrap",
          wall_side_warnings(corner_cab(7, wall_sides=(818, 834))), [])
    check("a helper corner with no wall sides at all is caught",
          bool(wall_side_warnings(corner_cab(7, wall_sides=(500, 500)))), True)

    print("\nan ell with one door hangs it on the shortest face it fits")
    from cabinetgen.room import _corner_door_hinges, cabinet_footprint

    def one_door_ell(width, flip=False):
        c = corner_cab(24, arm_a=1000, arm_b=1000, face_a=600, face_b=500, style="ell", doors=0)
        c.bespoke.append(Panel(24, "07", "Door", "DECOR", 2397, width, 1, grain=1))
        pl = Placement(24, "A", 0, flip=flip)
        jj = job([c], [pl], room=rectangular(4000, 3000, ceiling=2700))
        clear = not polygons_overlap(swing_envelopes(jj, c, pl)[0], cabinet_footprint(jj.room, pl, c))
        return _corner_door_hinges(geometry(c), pl)[0][0], clear
    # faces: wall-A side (0,600)-(500,600) is 500 long; wall-B side (500,600)-(500,1000) is 400
    check("a 397 door fits both; it takes the 400 face, hung from its outer end, sweeping clear",
          one_door_ell(397), ((500, 1000), True))
    check("flipped, it hangs from that face's inner end, at the notch",
          one_door_ell(397, flip=True), ((500, 600), True))
    check("a 450 door only fits the 500 face, so it goes there",
          one_door_ell(450), ((0, 600), True))
    check("flipped, the notch end of that face", one_door_ell(450, flip=True), ((500, 600), True))
    check("a 600 door fits neither, so it takes the longest face — and being wider than "
          "the face, its sweep runs back into the box past the notch",
          one_door_ell(600), ((0, 600), False))

    print("\na door wider than any face it could hang on is flagged")

    def too_wide(c):
        jj = job([c], [Placement(c.number, "A", 4000 - c.arm_a)], room=room)
        return [i.message for i in validate(jj, [])
                if i.where == str(c.number) and "wider than any face" in i.message]

    def ell_with_door(width):
        c = corner_cab(25, arm_a=1000, arm_b=1000, face_a=600, face_b=500, style="ell", doors=0)
        c.bespoke.append(Panel(25, "07", "Door", "DECOR", 2397, width, 1, grain=1))
        return c
    check("the 600 door on the 500 / 400 ell is flagged, naming the longest face",
          too_wide(ell_with_door(600)),
          ["cabinet 25: its 600 door is wider than any face it could hang on (the longest is "
           "500 mm) — check the door against arm_a/arm_b and face_a/face_b"])
    check("a 450 door that fits the 500 face is not", too_wide(ell_with_door(450)), [])
    wide_mitre = corner_cab(26, doors=0)
    wide_mitre.bespoke.append(Panel(26, "07", "Door", "DECOR", 2397, 510, 1, grain=1))
    check("a 510 door on a 495 mitre is flagged", len(too_wide(wide_mitre)), 1)
    check("cabinet 7's 472 door in its 495 face is not", too_wide(oct7), [])

    print("\nthe cut list is read-only with respect to the job")
    shelved = Cabinet(number=5, width=900, height=720, depth=580, kind="base",
                      shelves=1, fixed_shelves=1)          # two shelf sizes under code 05
    j = job([corner, shelved, cab(3, 600, drawers=3)],
            [Placement(7, "A", 0), Placement(5, "A", 850), Placement(3, "A", 1750)])
    snapshot = json.dumps(job_to_dict(j), sort_keys=True)
    labels = sorted(p.label for p in generate_job(j))
    check("generating the cut list changes nothing in the job",
          json.dumps(job_to_dict(j), sort_keys=True) == snapshot, True)
    check("generated panels are born with distinct designations where a code covers two sizes",
          [lab for lab in labels if lab.startswith("505")], ["505a", "505b"])
    check("bespoke designations are what the job says, untouched",
          [lab for lab in labels if lab.startswith("7")], ["701a", "701c", "702"])
    check("generating twice gives the same list", sorted(p.label for p in generate_job(j)), labels)

    print("\nno geometric check reads a declared figure")
    fat = Cabinet(number=9, width=600, height=720, depth=580, template="none", bespoke=[
        Panel(9, "01", "Side", "MEL", 900, 700, 2), Panel(9, "03", "Bottom", "MEL", 768, 700, 1)])
    g = geometry(fat)
    check("declared 600 x 580 x 720; the panels say 800 wide, 700 deep, 900 high",
          (g.width, g.depth, g.height), (800, 700, 900))
    j = job([fat, cab(2, 600)], [Placement(9, "A", 0), Placement(2, "A", 700)])
    check("so the overlap check sees the 800, not the 600",
          [(o.a, o.b, o.mm) for o in overlaps(j)], [(9, 2, 100)])
    check("and the snap targets clear the real width",
          [s["x"] for s in snap_points(j, 2, "A", std) if s["why"] == "right of 9"], [800])

    print("\na job with no room is untouched by all of it")
    plain = Job(name="x", cabinets=[cab(1, 900, doors=2)])
    check("no overlaps", overlaps(plain), [])
    check("no clashes", clashes(plain, std), [])
    check("no snap points", snap_points(plain, 1, "A", std), [])
    check("and nothing to say about it",
          [i for i in validate(plain, []) if "overlap" in i.message or "fouls" in i.message],
          [])

    print(f"\n{'ALL OK' if not FAILS else str(len(FAILS)) + ' FAILED: ' + str(FAILS)}")
    return 1 if FAILS else 0


if __name__ == "__main__":
    raise SystemExit(main())
