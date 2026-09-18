"""Fronts: the two tickboxes, hinge side per leaf, and drawer face heights.

    python tools/check_fronts.py

What is pinned here, and why:

  * **A tickbox turns something off; it never throws it away.** Unticking
    "Has drawers" or "Corner unit" leaves the stack and the four corner
    measurements in the job file exactly as they were, so ticking it back
    restores the cabinet panel for panel. That is the whole point of storing a
    tri-state rather than clearing the fields.
  * **A designation never moves.** A change removes panels or it leaves them
    alone. Nothing that survives a change comes back under a different name, and
    `what_if` — which is what the UI shows before anything is removed — names the
    designations that would go.
  * **Hinge side has one answer.** `model.hinge_side` is read by the plan's
    swing arcs and by the elevation's hinge marks and door leaves, so the drawing
    and the geometry cannot drift apart. A per-leaf choice wins; with none set,
    the rule that was always there still holds.
  * **A leaf hangs off its own edge.** A pair hinged at its outer edges is the
    default, but turning one leaf round puts its hinge in the middle of the
    opening, where it really is — not on the carcass end.
  * **Face heights are the engine's.** Fixed rows take their millimetres, the
    gaps come from Standard, and the share rows divide what is left. Fixed rows
    that over-run the opening leave faces at zero, which blocks the export
    rather than shipping a negative panel.
  * **Dragging a join moves two faces and no others.**
"""
import os
import re
import sys

ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, ROOT)

from app.api import what_if                                                  # noqa: E402
from cabinetgen.drawers import (divide, equal_shares, graduated_shares,      # noqa: E402
                                remainder, split_pair)
from cabinetgen.engine import generate_job                                   # noqa: E402
from cabinetgen.model import (Cabinet, Drawer, Job, Panel, Placement,        # noqa: E402
                              hinge_side)
from cabinetgen.render import wall_elevation_svg                             # noqa: E402
from cabinetgen.room import (geometry, rectangular, swing_envelopes,         # noqa: E402
                             to_world)
from cabinetgen.standard import STANDARD                                     # noqa: E402
from cabinetgen.store import job_to_dict                                     # noqa: E402
from cabinetgen.validate import blocking, validate                           # noqa: E402

FAILS = []


def check(name, got, want):
    ok = got == want
    print(f"  {'ok   ' if ok else 'FAIL '} {name}: {got}" + ("" if ok else f"  want {want}"))
    if not ok:
        FAILS.append(name)


def lines(job, number):
    """(designation, material, length, width, qty) for one cabinet, as ordered."""
    return sorted((p.label, p.material, p.length, p.width, p.qty)
                  for p in generate_job(job) if p.cabinet == number)


def bank(**kw):
    """A drawer bank: four faces under nothing, on a 790 vanity carcass."""
    kw.setdefault("drawers", [Drawer(195, 150), Drawer(195, 150),
                              Drawer(195, 150), Drawer(196, 150)])
    return Cabinet(number=30, width=350, height=790, depth=390, kind="base",
                   back="none", supports=4, edged_supports=1, **kw)


def corner(**kw):
    """The October fixture's cabinet 7, with its real measurements."""
    return Cabinet(number=7, width=850, height=2400, depth=500, back="none",
                   supports=0, template="none", corner_style="mitre",
                   arm_a=850, arm_b=850, face_a=500, face_b=500, bespoke=[
                       Panel(7, "01a", "Side", "MEL", 2400, 500, 2),
                       Panel(7, "01b", "Side", "MEL", 2400, 818, 1),
                       Panel(7, "01c", "Side", "MEL", 2400, 834, 1),
                       Panel(7, "02", "Top", "MEL", 818, 818, 1),
                       Panel(7, "07", "Door", "DECOR", 2397, 472, 1, grain=1)], **kw)


def kitchen(cabs, places=None, ceiling=2700):
    rm = rectangular(4000, 3000, ceiling=ceiling)
    return Job(name="f", room=rm, cabinets=cabs,
               placements=places or [Placement(c.number, "A", 0) for c in cabs])


def main() -> int:                                                  # noqa: C901
    std = STANDARD

    print("a tickbox turns something off; it never throws it away")
    on = bank()
    built = lines(Job(name="a", cabinets=[on]), 30)
    off = bank(has_drawers=False)
    check("with the tickbox untouched a stack is built, as it always was",
          sorted(x[0] for x in built),
          ["3001", "3003", "3004", "3004", "3017", "3018", "3019", "3020a", "3020b"])
    check("unticked, none of it is", lines(Job(name="b", cabinets=[off]), 30),
          sorted(x for x in built if not x[0].startswith(("3017", "3018", "3019", "3020"))))
    check("and the stack is still there in the job file, face for face",
          [(d.face_height, d.box_height) for d in off.drawers],
          [(195, 150), (195, 150), (195, 150), (196, 150)])
    back = bank(has_drawers=True)
    check("ticking it back builds exactly what it built before",
          lines(Job(name="c", cabinets=[back]), 30), built)

    print("\nwhat goes is named first, and nothing is ever renamed")
    job = Job(name="d", cabinets=[bank()])
    r = what_if({"job": job_to_dict(job), "cabinet": 30, "set": {"has_drawers": False}})
    check("the panels that would go, by designation",
          sorted(x["label"] for x in r["removed"]),
          ["3017", "3018", "3019", "3020a", "3020b"])
    check("and the ones that stay", r["kept"], ["3001", "3003", "3004"])
    kept_before = {x[0]: x[1:] for x in built if x[0] in set(r["kept"])}
    kept_after = {x[0]: x[1:] for x in lines(Job(name="e", cabinets=[off]), 30)}
    check("every designation that survives is the same panel it was",
          kept_after, kept_before)
    check("nothing the job already owns is touched by asking",
          [(d.face_height, d.box_height) for d in job.cabinets[0].drawers],
          [(195, 150), (195, 150), (195, 150), (196, 150)])

    print("\nthe corner tickbox: an outline, not a panel")
    seven = corner()
    check("ticked, the outline comes off the four measurements",
          (geometry(seven).source, geometry(seven).footprint),
          ("corner", [(0, 0), (850, 0), (850, 850), (350, 850), (0, 500)]))
    dark = corner(corner_unit=False)
    check("unticked, it falls back to the rectangle its panels make",
          (geometry(dark).source, geometry(dark).width, geometry(dark).depth),
          ("panels", 850, 834))
    check("with all four measurements still in the job file",
          (dark.corner_style, dark.arm_a, dark.arm_b, dark.face_a, dark.face_b),
          ("mitre", 850, 850, 500, 500))
    check("and re-ticking gives the same outline back",
          geometry(corner(corner_unit=True)).footprint, geometry(seven).footprint)
    cj = Job(name="g", cabinets=[corner()])
    check("turning it off removes no panel — it is a shape, not a part",
          what_if({"job": job_to_dict(cj), "cabinet": 7,
                   "set": {"corner_unit": False}})["removed"], [])

    print("\nhinge side: one answer, read by the plan and the drawing alike")
    pair = Cabinet(number=1, width=900, height=720, depth=580, kind="base", doors=2)
    single = Cabinet(number=2, width=600, height=720, depth=580, kind="base", doors=1)
    check("a pair still hangs from its outer edges",
          [hinge_side(pair, i, 2, False) for i in range(2)], ["L", "R"])
    check("a single door still follows the placement's flip",
          [hinge_side(single, 0, 1, f) for f in (False, True)], ["L", "R"])
    turned = Cabinet(number=2, width=600, height=720, depth=580, kind="base",
                     doors=1, door_hinges=["R"])
    check("a per-leaf choice wins over the flip, either way",
          [hinge_side(turned, 0, 1, f) for f in (False, True)], ["R", "R"])
    check("a blank entry hands it back to the rule",
          hinge_side(Cabinet(number=2, width=600, height=720, depth=580, doors=1,
                             door_hinges=[""]), 0, 1, True), "R")

    print("\na leaf hangs off its own edge, not the carcass end")
    j = kitchen([pair], [Placement(1, "A", 500)])
    hinges = [e[0] for e in swing_envelopes(j, pair, j.placements[0], std)]
    g = geometry(pair, std)
    check("a pair, as it was: hinges on the two outer edges",
          hinges, [to_world(j.room, "A", 500, g.depth)[:2],
                   to_world(j.room, "A", 500 + g.width, g.depth)[:2]])
    # Ruled 18 September 2026: a pair is not a choice. Two leaves hang from their
    # outer edges whatever a job file says, so an override written before the
    # rule is simply not read — the drawing and the plan both stop offering it.
    inner = Cabinet(number=1, width=900, height=720, depth=580, kind="base",
                    doors=2, door_hinges=["R", "L"])
    j2 = kitchen([inner], [Placement(1, "A", 500)])
    check("a pair is fixed: an override on either leaf is not read",
          [e[0] for e in swing_envelopes(j2, inner, j2.placements[0], std)], hinges)
    single = Cabinet(number=1, width=900, height=720, depth=580, kind="base",
                     doors=1, door_hinges=["R"])
    j3 = kitchen([single], [Placement(1, "A", 500)])
    gs = geometry(single, std)
    check("a single door is the choice, and hangs off the edge it is given",
          [e[0] for e in swing_envelopes(j3, single, j3.placements[0], std)],
          [to_world(j3.room, "A", 500 + gs.width, gs.depth)[:2]])
    check("and unticking Has doors takes the swing away with the panel",
          [e[0] for e in swing_envelopes(
              kitchen([Cabinet(number=1, width=900, height=720, depth=580,
                               kind="base", doors=1, has_doors=False)],
                      [Placement(1, "A", 500)]),
              Cabinet(number=1, width=900, height=720, depth=580, kind="base",
                      doors=1, has_doors=False),
              Placement(1, "A", 500), std)], [])

    print("\nthe elevation hangs every leaf where the plan swings it")
    for cab, places in ((pair, [Placement(1, "A", 500)]),
                        (inner, [Placement(1, "A", 500)])):
        jj = kitchen([cab], places)
        svg = wall_elevation_svg(jj, "A")
        drawn = re.findall(r'class="edoor" data-cab="1" data-door="(\d)" data-hinge="(L|R)"', svg)
        marks = re.findall(r'class="hinge" data-cab="1" data-door="(\d)" data-side="(L|R)"', svg)
        want = [(str(i), hinge_side(cab, i, cab.door_count, False))
                for i in range(cab.door_count)]
        check(f"cabinet {cab.number} {cab.door_hinges or 'default'}: the door you click",
              drawn, want)
        check("  and the hinge marks drawn on it", marks, want)

    print("\na corner unit's door follows the same control")
    for side, want_at in (("L", (0, 500)), ("R", (350, 850))):
        c = corner(door_hinges=[side])
        jj = kitchen([c], [Placement(7, "A", 0)])
        check(f"hinged {side} on the mitre face",
              swing_envelopes(jj, c, jj.placements[0], std)[0][0],
              to_world(jj.room, "A", *want_at)[:2])

    print("\nface heights: fixed rows take theirs, the share rows divide the rest")
    check("four shares fill a 787 opening exactly",
          divide(787, ["share"] * 4, [1, 1, 1, 1]), [195, 195, 195, 196])
    check("and the gaps come from Standard, never typed per drawer",
          sum(divide(787, ["share"] * 4, [1] * 4)) + 3 * std.stack_gap, 787)
    check("one fixed row and two shares",
          divide(787, ["fixed", "share", "share"], [300, 1, 1]), [300, 241, 242])
    check("shares need not be equal",
          divide(787, ["share", "share"], [1, 3]), [196, 589])
    check("a fixed-only stack is honoured as typed, shortfall and all",
          divide(787, ["fixed", "fixed"], [300, 300]), [300, 300])
    check("Equal and Graduated both come out of Standard",
          (equal_shares(3), graduated_shares(3)), ([1.0, 1.0, 1.0], [1.0, 1.5, 2.0]))
    check("graduated puts the smallest face at the top",
          divide(787, ["share"] * 4, graduated_shares(4)), [111, 167, 223, 280])

    print("\nfixed rows that over-run the opening block the export")
    check("the remainder goes negative before anything else does",
          remainder(787, ["fixed", "fixed", "share"], [400, 400, 1]), -17)
    over = bank(drawers=[Drawer(0, 150, mode="share"), Drawer(400, 150, mode="fixed"),
                         Drawer(400, 150, mode="fixed")])
    over.drawers[0].face_height = divide(787, ["share", "fixed", "fixed"],
                                         [1, 400, 400])[0]
    check("which leaves the shared face at nothing, not at a negative",
          over.drawers[0].face_height, 0)
    issues = validate(Job(name="o", cabinets=[over]), [])
    check("and that is a critical, in as many words",
          [i.message for i in issues if "over-run" in i.message],
          ["drawer 1: face height is 0 — the fixed faces over-run the opening, "
           "leaving nothing for the shared ones"])
    check("so the job does not export", blocking(issues), True)

    print("\ndragging a join moves two faces and no others")
    check("the pair's own span is all that is divided", split_pair(195, 196, 120),
          (120, 271))
    check("and it is preserved to the millimetre",
          sum(split_pair(195, 196, 120)) + std.stack_gap, 195 + std.stack_gap + 196)
    check("a face is held back far enough to clear its own box side",
          split_pair(195, 196, 10, 150, 150), (151, 240))
    check("dragged the other way, the same", split_pair(195, 196, 900, 150, 150),
          (240, 151))
    stack = bank()
    a, b = split_pair(stack.drawers[1].face_height, stack.drawers[2].face_height, 120)
    stack.drawers[1].face_height, stack.drawers[1].mode = a, "fixed"
    stack.drawers[2].face_height, stack.drawers[2].mode = b, "fixed"
    check("the faces above and below the pair are untouched",
          [stack.drawers[0].face_height, stack.drawers[3].face_height], [195, 196])
    check("and the stack still fills its opening",
          sum(d.face_height for d in stack.drawers) + 3 * std.stack_gap, 787)

    print("\nthe drawing carries what a drag needs, and nothing it could get wrong")
    jj = kitchen([bank()], [Placement(30, "A", 0)])
    svg = wall_elevation_svg(jj, "A")
    joins = re.findall(r'class="fdiv" data-cab="30" data-above="(\d)" data-below="(\d)" '
                       r'data-mm="(\d+)"', svg)
    check("one grab handle per join between two faces, three for four faces",
          [(a, b) for a, b, _ in joins], [("0", "1"), ("1", "2"), ("2", "3")])
    check("each carrying its pair's span in mm — the two faces and the gap",
          [int(mm) for _, _, mm in joins],
          [195 + std.stack_gap + 195, 195 + std.stack_gap + 195,
           195 + std.stack_gap + 196])
    check("and the same span in pixels, so the browser converts rather than computes",
          all(re.search(rf'data-mm="{mm}" data-top="[\d.]+" data-px="[\d.]+"', svg)
              for _, _, mm in joins), True)
    check("an unticked stack draws no handles at all",
          'class="fdiv"' in wall_elevation_svg(
              kitchen([bank(has_drawers=False)], [Placement(30, "A", 0)]), "A"), False)

    print(f"\n{'ALL OK' if not FAILS else str(len(FAILS)) + ' FAILED: ' + str(FAILS)}")
    return 1 if FAILS else 0


if __name__ == "__main__":
    raise SystemExit(main())
