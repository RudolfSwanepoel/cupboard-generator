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
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import json                                                                 # noqa: E402

from cabinetgen.engine import generate_job                                  # noqa: E402
from cabinetgen.model import (Cabinet, Drawer, Job, MATERIALS, Opening,     # noqa: E402
                             Panel, Placement)
from cabinetgen.engine import generate_cabinet, mitre_door_width           # noqa: E402
from cabinetgen.room import (_gap_along, arm_shelf_max_depth,              # noqa: E402
                             blind_door_width, blind_opening,
                             blind_panel_height, blind_spans,
                             clashes, convex_overlap,
                             corner_outline,
                             corner_shadow, gaps as room_gaps, geometry,
                             mitre_blank, mitre_inner_span, mitre_legs,
                             overlaps, polygons_overlap, pullout_envelope,
                             rectangular, runs as room_runs, snap_points,
                             swing_envelopes, triangulate, z_snap_points)
from cabinetgen.render import wall_elevation_svg                           # noqa: E402
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
        bespoke.append(Panel(number, "07", "Door", "BROOKHILL", height - 3, door_len,
                             doors, grain=1))
    return Cabinet(number=number, width=arm_a, height=height, depth=face_a,
                   kind="tall", back="none", template="none",
                   corner_style=style, arm_a=arm_a, arm_b=arm_b,
                   face_a=face_a, face_b=face_b, bespoke=bespoke)


def template_mitre(number=7, hand="", **kw):
    """Cabinet 7's measurements as a TEMPLATE cabinet, which is what Part C
    generates. The real cabinet 7 is bespoke and stays that way so the October
    benchmark cannot move; this is the same box, generated."""
    kw.setdefault("kind", "tall")
    return Cabinet(number=number, width=850, height=2400, depth=500,
                   back="none", supports=0, doors=1,
                   corner_unit=True, corner_style="mitre", corner_hand=hand,
                   arm_a=850, arm_b=850, face_a=500, face_b=500, **kw)


def blind_cab(number=1, width=1000, blind=500, hand="", depth=560, height=720, **kw):
    """The worked blind example: W 1000, B 500, t 16 -> opening 468, door 497."""
    kw.setdefault("kind", "base")
    kw.setdefault("back", "none")
    kw.setdefault("supports", 0)
    return Cabinet(number=number, width=width, height=height, depth=depth,
                   corner_unit=True, corner_style="blind",
                   corner_hand=hand, blind_width=blind, **kw)


def only(panels, role):
    """The one panel with this role. A blind unit cuts exactly one of each."""
    found = [p for p in panels if p.role == role]
    return found[0] if len(found) == 1 else None


def sizes(panels, role):
    return sorted((p.length, p.width, p.qty) for p in panels if p.role == role)


def corner_checks():
    """Part C and Part D: what a corner unit actually cuts, and which end of it
    stands in the corner. Ruled 22 September 2026.

    Before this, ticking Corner unit on a template cabinet reshaped the plan and
    changed nothing on the cut list - the box still came out W x D square, and
    nothing said so. Cabinet 7 only ever "worked" because its panels are typed
    out by hand in the job file.
    """
    std = STANDARD
    print("\na mitre is generated from its four measurements")
    m = template_mitre()
    P = generate_cabinet(m)
    check("sides: the two open faces, then the two wall sides one wrapping the other",
          sizes(P, "Side"), [(2400, 500, 2), (2400, 818, 1), (2400, 834, 1)])
    check("top and bottom are the square blank, both of them",
          (sizes(P, "Top"), sizes(P, "Bottom")),
          ([(818, 818, 1)], [(818, 818, 1)]))
    check("the door is cut to the inner span, rounded down, with no gap taken off",
          (mitre_inner_span(m), sizes(P, "Door")), (472.35, [(2397, 472, 1)]))
    check("which is cabinet 7's real door, and not the 495 outline face less 3",
          [p.width for p in P if p.role == "Door"], [472])
    check("pot holes follow the door length exactly as on any other door",
          [p.pot_holes for p in P if p.role == "Door"], [4])
    check("no backing panel and no supports on a mitre (RULES W13)",
          [p.role for p in P if p.role in ("Backing", "Support")], [])

    print("\na BASE mitre still gets its top - that is what braces it")
    base_m = template_mitre(kind="base")
    check("a straight base cabinet has no top",
          [p.role for p in generate_cabinet(cab(1, 600, kind="base")) if p.role == "Top"],
          [])
    check("but a base mitre does, and it is the same square blank",
          sizes(generate_cabinet(base_m), "Top"), [(818, 818, 1)])
    check("and an upper mitre is the same box again",
          sizes(generate_cabinet(template_mitre(kind="upper")), "Top"), [(818, 818, 1)])

    print("\nthe two mitre shelves, and where the mitre cut falls on each")
    check("the blank every one of them is cut from", mitre_blank(m), (818, 818))
    check("the top and bottom mitre flush with the inner line",
          mitre_legs(m), (334, 334))
    check("a mitred shelf sits mitre_shelf_clear behind the closed door",
          mitre_legs(m, std, std.mitre_shelf_clear), (338, 338))
    check("an arm shelf runs wall side to wall side along its arm",
          [(p.length, p.width, p.qty) for p in
           generate_cabinet(template_mitre(arm_shelves=6, arm_shelf_depth=350))
           if p.role == "Shelve"], [(818, 350, 6)])
    check("cabinet 7's own 350 is under the maximum, so it is accepted",
          (arm_shelf_max_depth(m), 350 <= arm_shelf_max_depth(m)), (430, True))
    over = template_mitre(arm_shelves=1, arm_shelf_depth=470)
    check("deeper than the maximum is a critical that names the maximum",
          [(i.level, "430" in i.message) for i in validate(Job(name="x", cabinets=[over]), [])
           if "arm shelf" in i.message], [("critical", True)])
    check("a blank depth takes the maximum rather than nothing",
          [(p.length, p.width) for p in
           generate_cabinet(template_mitre(arm_shelves=1)) if p.role == "Shelve"],
          [(818, 430)])
    both = generate_cabinet(template_mitre(arm_shelves=2, arm_shelf_depth=350,
                                           mitred_shelves=1))
    check("both kinds at once come out as two distinct designations",
          sorted((p.label, p.length, p.width, p.qty) for p in both if p.role == "Shelve"),
          [("705a", 818, 350, 2), ("705b", 818, 818, 1)])

    print("\nthe hand mirrors the unit, and nothing else about it")
    left = template_mitre(hand="L")
    check("a right-handed outline is what this app always drew",
          geometry(m).footprint, corner_outline("mitre", 850, 850, 500, 500))
    check("and a left-handed one is its mirror image",
          geometry(left).footprint, corner_outline("mitre", 850, 850, 500, 500, "L"))
    check("both read as the same 45 degree mitre - a mirrored 45 is not a 135",
          (geometry(m).mitre_deg, geometry(left).mitre_deg), (45.0, 45.0))
    check("the same front face, the same inner span and the same door",
          (geometry(left).face_lengths, mitre_inner_span(left), mitre_door_width(left)),
          (geometry(m).face_lengths, mitre_inner_span(m), mitre_door_width(m)))
    check("and the very same panels: mirroring a box does not resize it",
          sorted((p.label, p.length, p.width, p.qty) for p in generate_cabinet(left)),
          sorted((p.label, p.length, p.width, p.qty) for p in P))
    check("a blank hand reads as R, so every job written before it is unmoved",
          geometry(template_mitre(hand="")).footprint, geometry(m).footprint)

    print("\nand it decides which corner the unit is standing in")
    room = rectangular(4000, 3000, ceiling=2700)
    check("right-handed: flush at the wall's END, turning onto the NEXT wall",
          corner_shadow(room, m, Placement(7, "A", 3150), std), ("B", 0, 850, 500))
    check("and nothing at the wall's start, which is the other corner",
          corner_shadow(room, m, Placement(7, "A", 0), std), None)
    check("left-handed: flush at the wall's START, turning onto the PREVIOUS wall",
          corner_shadow(room, left, Placement(7, "B", 0), std), ("A", 3150, 850, 500))
    check("and nothing at the wall's end",
          corner_shadow(room, left, Placement(7, "B", 2150), std), None)

    print("\na mitre door that cannot open BLOCKS the export - the one exception")
    deep = cab(2, 600, d=900, h=2400, kind="tall", doors=1)
    clash = job([template_mitre(1, hand="L", door_hinges=["L"]), deep],
                [Placement(1, "B", 0), Placement(2, "B", 900)], room=room)
    said = [i for i in validate(clash, generate_job(clash)) if "door swing" in i.message]
    check("it is a critical, not the warning an ordinary door gets",
          [i.level for i in said], ["critical"])
    check("and it says the widest door that would clear",
          [("widest that clears" in i.message) for i in said], [True])
    ordinary = job([cab(1, 600, doors=1), cab(3, 600)],
                   [Placement(1, "A", 3000, flip=True), Placement(3, "B", 0)], room=room)
    check("the same foul on an ordinary door is still only a warning",
          sorted({i.level for i in validate(ordinary, [])
                  if "door swing fouls" in i.message}), ["warning"])

    print("\nan ell is shape only, and says so rather than cutting nothing quietly")
    ell = template_mitre(3)
    ell.corner_style = "ell"
    check("it still has a shape, and two front faces",
          (geometry(ell).source, geometry(ell).face_lengths), ("corner", [350, 350]))
    check("but it cuts nothing at all", generate_cabinet(ell), [])
    check("and that is a critical naming what to do about it",
          [(i.level, "construction not decided" in i.message)
           for i in validate(Job(name="x", cabinets=[ell]), []) if "ell corner" in i.message],
          [("critical", True)])
    hand_typed = corner_cab(4, style="ell")
    check("an ell with its own bespoke panels is untouched by that",
          (len(generate_cabinet(hand_typed)) > 0,
           [i for i in validate(Job(name="x", cabinets=[hand_typed]), [])
            if "ell corner" in i.message]), (True, []))

    print("\nticked with no type chosen is what 'it does nothing' looked like")
    silent = Cabinet(number=5, width=850, height=2400, depth=500, kind="tall",
                     corner_unit=True, arm_a=850, arm_b=850, face_a=500, face_b=500)
    check("it really does cut a straight box",
          sizes(generate_cabinet(silent), "Side"), [(2400, 500, 2)])
    check("and now it says so, rather than saying nothing",
          [(i.level, "no type is chosen" in i.message)
           for i in validate(Job(name="x", cabinets=[silent]), [])
           if "Corner unit is ticked" in i.message], [("warning", True)])

    print("\na blind corner: a straight box, one door, and a flush panel")
    b = blind_cab(shelves=1)
    BP = generate_cabinet(b)
    check("the worked example: W 1000, B 500, t 16",
          (blind_opening(b), blind_door_width(b)), (468, 497))
    check("the door is derived from the opening exactly as any other door is",
          sizes(BP, "Door"), [(717, 497, 1)])
    check("the blind panel is cut at exactly B, the width it was measured at",
          sizes(BP, "Blind Panel"), [(688, 500, 1)])
    check("and it is code 08 with its own role, so the cut list can tell it apart",
          sorted({(p.label, p.role) for p in BP if p.role == "Blind Panel"}),
          [("108", "Blind Panel")])
    check("one long edge only, the vertical one facing the opening, and no pot holes",
          [(p.edge_l, p.edge_w, p.pot_holes) for p in BP if p.role == "Blind Panel"],
          [(1, 0, 0)])

    # ---- the panel sits INSIDE the carcass (ruled 22 September 2026) --------
    #
    # It used to stand across the corner end at door height. It is between the
    # top and the bottom now, flush with the front edges, with the corner-end
    # side panel beyond it and an ordinary overlay door lapping onto its face.
    # The door and the opening did not move: only the panel's construction did.
    print("\nthe flush panel is between the top and the bottom, inside the carcass")
    big = blind_cab(1, height=2400, depth=500)
    BIG = generate_cabinet(big)
    check("the brief's worked unit: W 1000, H 2400, D 500, B 500, t 16",
          (blind_opening(big), blind_door_width(big), blind_panel_height(big)),
          (468, 497, 2368))
    check("blind panel 2368 x 500, code 08, one long edge",
          [(p.code, p.length, p.width, p.qty, p.edge_l, p.edge_w)
           for p in BIG if p.role == "Blind Panel"], [("08", 2368, 500, 1, 1, 0)])
    check("and the door beside it is the one it always was",
          sizes(BIG, "Door"), [(2397, 497, 1)])
    check("it is H - 2t, the figure a divider's default height already uses",
          blind_panel_height(big), 2400 - 2 * std.board_t)
    # A BASE unit has no top: it stands on the bottom and runs up to the
    # underside of the front support, which is the same 16 mm board lying flat
    # with its face flush with the carcass top edge. So the clear span is the
    # same H - 2t, and the engine's own support line is what says so - a support
    # is cut from the carcass board at the same thickness as a top.
    base = blind_cab(1, height=790, depth=500, kind="base", supports=1)
    BASE = generate_cabinet(base)
    check("a base unit with no top is the same figure, H - 2t",
          [(p.length, p.width) for p in BASE if p.role == "Blind Panel"], [(758, 500)])
    check("because its support is cut from the carcass board like a top is",
          sorted({(p.role, p.material) for p in BASE
                  if p.role in ("Support", "Bottom")}),
          [("Bottom", "MEL"), ("Support", "MEL")])
    check("and a base blind unit really has no top to measure to",
          [p.role for p in BASE if p.role == "Top"], [])

    print("\nwhere the three parts sit across the front, and what laps what")
    side, panel, door = blind_spans(big)
    t, gap = std.board_t, std.door_single_gap / 2
    check("right-handed: the corner-end side is the last board on the wall",
          (side, panel, door), ((984, 1000), (484, 984), (1.5, 498.5)))
    check("the panel starts one board in from the corner, not at it",
          1000 - panel[1], t)
    check("the door laps onto the panel's face by t - half the door gap",
          door[1] - panel[0], t - gap)
    check("and laps the far side panel by the same",
          t - door[0], t - gap)
    check("left-handed is the mirror of it, to the millimetre",
          blind_spans(blind_cab(1, height=2400, hand="L")),
          ((0, 16), (16, 516), (501.5, 998.5)))
    check("the door is exactly the width the cut list cuts",
          round(door[1] - door[0]), blind_door_width(big))

    print("\nthe panel names its own board and its own edging, and nothing else does")
    check("blank follows the exterior board, which is what it was",
          (blind_cab(1).blind_panel_board, blind_cab(1, exterior_board="X").blind_panel_board),
          ("BROOKHILL", "X"))
    own = blind_cab(1, height=2400, blind_board="MEL")
    check("choosing another board changes what the line is cut from",
          [(p.material, p.grain) for p in generate_cabinet(own) if p.role == "Blind Panel"],
          [("MEL", 0)])
    check("and the grain it locks is that board's, not the doors'",
          [p.grain for p in BIG if p.role == "Blind Panel"], [1])
    check("the edging follows the doors' thickness with nothing chosen",
          (blind_cab(1).blind_edge_thickness,
           blind_cab(1, door_edge_kind="1mm").blind_edge_thickness), ("2mm", "1mm"))
    check("and its COLOUR is the panel's own board, not the doors'",
          only(generate_cabinet(own), "Blind Panel").edge_material,
          "2mm WHITE")
    one_mm = blind_cab(1, height=2400, blind_edge_kind="1mm")
    two_mm = blind_cab(1, height=2400, blind_edge_kind="2mm")
    check("1mm and 2mm change the edging NAME and nothing else",
          [(only(generate_cabinet(c), "Blind Panel").edge_material,
            only(generate_cabinet(c), "Blind Panel").length,
            only(generate_cabinet(c), "Blind Panel").width)
           for c in (one_mm, two_mm)],
          [("1mm WOOD", 2368, 500), ("2mm WOOD", 2368, 500)])

    print("\nand it is in the one list of which fields hold a board")
    named = blind_cab(1, blind_board="ONLYHERE")
    check("board_refs names it, so a swap and a rename both find it",
          [label for board, label in named.board_refs() if board == "ONLYHERE"],
          ["blind panel board"])
    swapped = blind_cab(1, height=2400, blind_board="MEL")
    swapped.map_board_refs(lambda b: "BROOKHILL" if b == "MEL" else b)
    check("a swap moves it with everything else",
          [(p.material, p.grain) for p in generate_cabinet(swapped)
           if p.role == "Blind Panel"], [("BROOKHILL", 1)])

    print("\nan edging the panel's board does not offer is the usual CRITICAL")
    mats = {k: dict(v) for k, v in MATERIALS.items()}
    mats["BROOKHILL"] = dict(mats["BROOKHILL"], edging_kinds=["pvc", "2mm"])
    thin_edge = Job(name="x", boards=list(mats), materials=mats,
                    cabinets=[blind_cab(1, height=2400, blind_edge_kind="1mm")])
    check("it blocks, and it says which board to tick it on",
          [(i.level, i.ref) for i in validate(thin_edge, generate_job(thin_edge))
           if "blind panel" in i.message], [("critical", "EDGING")])
    check("the carcass is the ordinary path: back, supports and shelves all cut",
          sorted({p.role for p in generate_cabinet(blind_cab(back="four", supports=4,
                                                             shelves=1))}
                 & {"Backing", "Support", "Shelve"}),
          ["Backing", "Shelve", "Support"])
    check("its plan is a plain rectangle, not a derived corner shape",
          (geometry(b).source, geometry(b).width, geometry(b).depth),
          ("panels", 1000, 560))
    check("two doors are never cut on one: it is one door, always",
          len([p for p in generate_cabinet(blind_cab(doors=2)) if p.role == "Door"]), 1)

    print("\nand a blind unit fills the return wall the same way a mitre does")
    check("right-handed, flush at the wall's end",
          corner_shadow(room, b, Placement(1, "A", 3000), std), ("B", 0, 560, 560))
    check("left-handed, at the end of the previous wall",
          corner_shadow(room, blind_cab(hand="L"), Placement(1, "B", 0), std),
          ("A", 3440, 560, 560))
    ret = cab(2, 600, d=600, doors=1)
    tight = job([blind_cab(1, blind=500), ret],
                [Placement(1, "A", 3000), Placement(2, "B", 560)], room=room)
    check("a return run reaching past the blind panel BLOCKS the export",
          [(i.level, "at least 616" in i.message) for i in validate(tight, generate_job(tight))
           if "into the door" in i.message], [("critical", True)])
    roomy = job([blind_cab(1, blind=700), ret],
                [Placement(1, "A", 3000), Placement(2, "B", 560)], room=room)
    check("and a blind panel wide enough for it clears",
          [i for i in validate(roomy, generate_job(roomy))
           if "into the door" in i.message], [])
    # The re-read the inset panel asked for. Moving the panel inside the carcass
    # put the clear OPENING one board further from the corner — it starts at
    # t + B now — but the DOOR did not move: its corner-end edge still stands
    # B + half a door gap from the corner. So a return run reaching between B
    # and B + t clears the opening and still stops the door opening, and the
    # threshold stays at B. Reading it off the opening would be wrong in the
    # unsafe direction, and this is the case that would show it.
    near = cab(2, 600, d=492, doors=1)          # reach 508: past B, inside B + t
    between = job([blind_cab(1, blind=500), near],
                  [Placement(1, "A", 3000), Placement(2, "B", 492)], room=room)
    check("a run reaching past B but not past B + t still blocks the DOOR",
          [(i.level, "at least 508" in i.message)
           for i in validate(between, generate_job(between))
           if "into the door" in i.message], [("critical", True)])

    print("\ntwo ways a blind corner is not one, both of them blocking")
    for why, c, phrase in (
            ("no blind panel width", blind_cab(1, blind=0), "no blind panel width"),
            ("a panel wider than the carcass", blind_cab(1, blind=980), "no opening at all")):
        check(why, [i.level for i in validate(Job(name="x", cabinets=[c]), [])
                    if phrase in i.message], ["critical"])
    # The limit is W - 2t, and it is where it says it is: a panel one millimetre
    # under it still leaves an opening and cuts a door. Anything that would leave
    # no door at all is already over that limit, which is why the "door <= 0"
    # critical is a guard and not something the editor can reach.
    edge = blind_cab(1, blind=967)
    check("one millimetre under the limit still leaves an opening and a door",
          (blind_opening(edge), blind_door_width(edge)), (1, 30))
    check("and nothing blocks it",
          [i.level for i in validate(Job(name="x", cabinets=[edge]), [])
           if "blind" in i.message], [])


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
        c.bespoke.append(Panel(24, "07", "Door", "BROOKHILL", 2397, width, 1, grain=1))
        pl = Placement(24, "A", 0, flip=flip)
        jj = job([c], [pl], room=rectangular(4000, 3000, ceiling=2700))
        clear = not polygons_overlap(swing_envelopes(jj, c, pl)[0], cabinet_footprint(jj.room, pl, c))
        return _corner_door_hinges(c, geometry(c), pl)[0][0], clear
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
        c.bespoke.append(Panel(25, "07", "Door", "BROOKHILL", 2397, width, 1, grain=1))
        return c
    check("the 600 door on the 500 / 400 ell is flagged, naming the longest face",
          too_wide(ell_with_door(600)),
          ["cabinet 25: its 600 door is wider than any face it could hang on (the longest is "
           "500 mm) — check the door against arm_a/arm_b and face_a/face_b"])
    check("a 450 door that fits the 500 face is not", too_wide(ell_with_door(450)), [])
    wide_mitre = corner_cab(26, doors=0)
    wide_mitre.bespoke.append(Panel(26, "07", "Door", "BROOKHILL", 2397, 510, 1, grain=1))
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

    print("\ndragging in the elevation: how high it may come to rest")
    # The vertical twin of the snap targets. Same rule as the plan: the engine
    # names every height, the browser only picks between them.
    base = cab(1, 900)
    base.height, base.depth = 720, 580
    up = cab(2, 900)
    up.kind, up.height, up.depth = "upper", 700, 330
    jz = job([base, up], [Placement(1, "A", 0), Placement(2, "A", 0, z=1500)])
    jz.room.ceiling = 2700
    check("the floor, the top of the base unit, and tight to the ceiling",
          [(s["z"], s["why"]) for s in z_snap_points(jz, 2, "A", std)],
          [(0, "on the floor"), (820, "on top of 1"), (2000, "tight to the ceiling")])
    check("the base unit's own top is leg height up, not zero",
          [s["z"] for s in z_snap_points(jz, 2, "A", std) if s["why"] == "on top of 1"],
          [std.leg_height + base.height])
    jz.placements[0] = Placement(1, "A", 3000)
    check("a cabinet that shares no span is nothing to sit on — but both its edges line up",
          [s["why"] for s in z_snap_points(jz, 2, "A", std)],
          ["on the floor", "bottoms level with 1", "tops level with 1",
           "tight to the ceiling"])
    jz.room.ceiling = None
    check("with no ceiling measured there is nothing to cap it against",
          [s["why"] for s in z_snap_points(jz, 2, "A", std)],
          ["on the floor", "bottoms level with 1", "tops level with 1"])

    # A drag crosses several of these on the way, so it asks for all of them with
    # the stretch of wall each applies over rather than a round trip per pixel.
    jz.room.ceiling = 2700
    spanned = z_snap_points(jz, 2, "A", std, spans=True)
    check("every candidate, with the stretch it applies over",
          [(s["z"], s["why"], s["x0"], s["x1"]) for s in spanned],
          [(0, "on the floor", None, None),
           (std.leg_height, "bottoms level with 1", None, None),
           (120, "tops level with 1", None, None),
           (820, "on top of 1", 3000, 3900), (2000, "tight to the ceiling", None, None)])
    check("and a level line carries the stretch it does NOT apply over — over the "
          "other cabinet, level tops would put one inside the other",
          [(s["why"], s.get("not_x0"), s.get("not_x1")) for s in spanned
           if "level" in s["why"]],
          [("bottoms level with 1", 3000, 3900), ("tops level with 1", 3000, 3900)])

    print("\ndragging in the elevation: lining up with a neighbour")
    # Rudolf's case: a wall unit moved up beside a tall unit snaps to its side
    # but should also be able to bring its top level with the tall unit's top.
    tall = cab(1, 600)
    tall.kind, tall.height, tall.depth = "tall", 2100, 580
    wu = cab(2, 600)
    wu.kind, wu.height, wu.depth = "upper", 700, 330
    wu2 = cab(3, 600)
    wu2.kind, wu2.height, wu2.depth = "upper", 500, 330
    jt = job([tall, wu, wu2], [Placement(1, "A", 0), Placement(2, "A", 600, z=1400),
                               Placement(3, "A", 1200, z=1650)])
    jt.room.ceiling = 2700
    zs = {s["why"]: s["z"] for s in z_snap_points(jt, 2, "A", std)}
    check("beside a tall unit, its top can come level with the tall unit's top",
          zs.get("tops level with 1"), std.leg_height + 2100 - 700)
    check("so the two tops really are one line",
          zs["tops level with 1"] + wu.height, std.leg_height + tall.height)
    check("and beside another wall unit, the undersides and the tops both line up",
          (zs.get("bottoms level with 3"), zs.get("tops level with 3")),
          (1650, 1650 + 500 - 700))
    # A standing neighbour's underside is `carcass_z` — the PLINTH TOP, because
    # every carcass on the floor is on its legs. It used to be reported as 0,
    # which is a leg height out, and `Test.json`'s panel 8 sits at exactly that
    # height with nothing to drag it back to (21 September 2026).
    check("a standing neighbour's underside is the plinth top, not the floor",
          zs.get("bottoms level with 1"), std.leg_height)
    check("and that is a real height for a hung unit to come to rest at",
          all(z > 0 for why, z in zs.items() if "level" in why), True)
    # Not for a carcass that stands on the floor, though: it stands on its legs,
    # so there is nothing for it between the floor and the plinth top — and any z
    # above 0 reads as hung (`layer_of`), so it would quietly change drawing layer
    # standing exactly where it already was.
    jb = job([tall, cab(4, 600)], [Placement(1, "A", 0), Placement(4, "A", 600)])
    jb.room.ceiling = 2700
    check("a legged carcass is offered nothing between the floor and the plinth top",
          [(s["z"], s["why"]) for s in z_snap_points(jb, 4, "A", std)
           if 0 < s["z"] <= std.leg_height], [])
    check("...and the floor itself is still there, unconditionally",
          [s["why"] for s in z_snap_points(jb, 4, "A", std)][0], "on the floor")
    print("\ndragging in the elevation: the reason names the NEAREST neighbour")
    # Every carcass on the floor puts its underside on one line, so a whole row of
    # candidates share a height and differ only in which cabinet they name. Sorted
    # on the reason alone that was answered alphabetically, and `Test.json`'s
    # panel 8 read "bottoms level with 1" with cabinet 7 the one touching it. They
    # are all true; the nearest is the one worth saying, and without `spans` it is
    # the only one that survives the de-duplication (21 September 2026).
    row = [cab(n, 600) for n in (1, 2, 3, 4)]
    hung = cab(5, 400)
    hung.kind, hung.height, hung.depth = "upper", 700, 330
    jn = job(row + [hung], [Placement(1, "A", 0), Placement(2, "A", 600),
                            Placement(3, "A", 1200), Placement(4, "A", 1800),
                            Placement(5, "A", 2600, z=1500)])
    jn.room.ceiling = 2700
    check("four cabinets on the floor put four candidates on one line",
          [(s["z"], s["why"]) for s in z_snap_points(jn, 5, "A", std, spans=True)
           if s["z"] == std.leg_height],
          [(std.leg_height, f"bottoms level with {n}") for n in (4, 3, 2, 1)])
    check("nearest first — 4 is the one it is beside, 1 is two metres away",
          [s["why"] for s in z_snap_points(jn, 5, "A", std)
           if s["z"] == std.leg_height], ["bottoms level with 4"])
    # And it is really about distance, not about the number: move the same hung
    # unit to the other end and the answer follows it, not the alphabet. It lands
    # OVER cabinet 1 there, where a level line does not apply at all — level
    # bottoms would put one inside the other — so the nearest it can line up with
    # is 2, which is the two rules working together.
    jn.placements[4] = Placement(5, "A", 0, z=1500)
    check("moved to the other end, the same drag names the other neighbour",
          [s["why"] for s in z_snap_points(jn, 5, "A", std)
           if s["z"] == std.leg_height], ["bottoms level with 2"])
    check("asked at a position it has not reached yet, it answers for THERE",
          [s["why"] for s in z_snap_points(jn, 5, "A", std, at_x=2600)
           if s["z"] == std.leg_height], ["bottoms level with 4"])
    check("a wall-wide datum is never far from anything — the floor, the "
          "ceiling and an opening carry no stretch to be far along",
          _gap_along((0, 600), None), 0)
    check("and a stretch that touches is not far either",
          (_gap_along((600, 1200), (0, 600)), _gap_along((600, 1200), (1200, 1800)),
           _gap_along((600, 1200), (0, 900)), _gap_along((600, 1200), (1800, 2400))),
          (0, 0, 0, 600))

    check("asked at a position it has not reached yet, the top is a candidate",
          [s["why"] for s in z_snap_points(jz, 2, "A", std, at_x=3000)],
          ["on the floor", "on top of 1", "tight to the ceiling"])

    print("\ndragging in the elevation: an opening is a datum, both ways")
    # The one place the two axes really diverged (21 September 2026). `snap_points`
    # has offered both jambs since the drag was built; `z_snap_points` offered
    # nothing at all for an opening, though the wall elevation draws its sill and
    # its head and a kitchen is set out off both.
    jo = job([cab(1, 600, kind="upper", h=700)], [Placement(1, "A", 2400, z=1500)])
    jo.room.ceiling = 3000
    jo.room.walls[0].openings.append(Opening("window", 1000, 1200, sill=900, head=2100))
    check("sideways, both jambs — as they always were",
          sorted(s["x"] for s in snap_points(jo, 1, "A", std)
                 if s["why"] == "clear of the window"), [400, 2200])
    zo = {s["why"]: s["z"] for s in z_snap_points(jo, 1, "A", std)}
    check("and now the head and the sill, my underside on each",
          (zo.get("above the window"), zo.get("bottoms level with the window sill")),
          (2100, 900))
    check("and my top on each, which is how a run is set out under a window",
          (zo.get("tops level with the window head"), zo.get("below the window")),
          (2100 - 700, 900 - 700))
    check("a datum runs the whole wall, so it carries no stretch — lining up "
          "beside the window is as much the point as sitting over it",
          [(s.get("x0"), s.get("not_x0")) for s in
           z_snap_points(jo, 1, "A", std, spans=True) if "window" in s["why"]],
          [(None, None)] * 4)
    tallo = cab(2, 600, kind="tall", h=2400)
    jo2 = job([tallo], [Placement(2, "A", 2400)])
    jo2.room.ceiling = 2700
    jo2.room.walls[0].openings.append(Opening("window", 1000, 1200, sill=900, head=2100))
    check("a 2400 unit cannot get its underside up to a 2100 head, and is not "
          "offered it — the ceiling caps the list as it always did",
          [s["why"] for s in z_snap_points(jo2, 2, "A", std) if "window" in s["why"]],
          [])

    print("\nthe drawing carries what an elevation drag reads back")
    jz.room.ceiling = 2700
    jz.placements[0] = Placement(1, "A", 0)
    svg = wall_elevation_svg(jz, "A")
    track = re.search(r'<rect class="etrack"[^>]*>', svg).group(0)
    check("where 0 mm along the wall is, and the floor, and the scale",
          all(k in track for k in ('data-wall="A"', 'data-len="4000"', "data-scale=",
                                   "data-x0=", "data-y0=", 'data-ceiling="2700"')), True)
    check("and one group per cabinet, so a drag moves the whole thing",
          sorted(re.findall(r'<g class="ecabg" data-cab="(\d+)"', svg)), ["1", "2"])

    corner_checks()

    print("\na job with no room is untouched by all of it")
    plain = Job(name="x", cabinets=[cab(1, 900, doors=2)])
    check("no overlaps", overlaps(plain), [])
    check("no clashes", clashes(plain, std), [])
    check("no snap points", snap_points(plain, 1, "A", std), [])
    check("and nothing to say about it",
          [i for i in validate(plain, []) if "overlap" in i.message or "fouls" in i.message],
          [])

    # Brief item 5, 22 September 2026: a blind corner is meant mainly for base
    # and wall-hung units, so the engine must not contradict itself on one. A
    # shelf DERIVED by the engine (no depth typed anywhere) has to clear the
    # back it derived, on every kind. The "shelf 968 deep fouls the back at 965"
    # that prompted this came off a MITRE's mitred shelf, not a blind corner,
    # and is awaiting a ruling — it is deliberately not pinned here.
    print("\na blind corner's derived shelves clear its back, base, wall and tall")
    fouls = []
    for kind, h, d in (("base", 790, 600), ("upper", 720, 600), ("upper", 720, 350),
                       ("tall", 2400, 1000)):
        bc = Cabinet(number=1, width=1000, height=h, depth=d, kind=kind, doors=1,
                     shelves=3, fixed_shelves=1, corner_unit=True,
                     corner_style="blind", corner_hand="L", blind_width=500)
        bj = Job("b", cabinets=[bc])
        bp = generate_job(bj)
        if not any(p.role == "Shelve" for p in bp):
            fouls.append((kind, d, "no shelf cut"))
        fouls += [(kind, d, str(i)) for i in validate(bj, bp) if "fouls the back" in i.message]
    check("not one fouls the back", fouls, [])

    print(f"\n{'ALL OK' if not FAILS else str(len(FAILS)) + ' FAILED: ' + str(FAILS)}")
    return 1 if FAILS else 0


if __name__ == "__main__":
    raise SystemExit(main())
