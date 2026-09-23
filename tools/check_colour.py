"""Board colour in the drawings: one resolver, and ink that reads on it.

    python tools/check_colour.py

The drawings used to fill a door teal, a drawer face cream and a carcass by its
layer, so the colours on the paper said nothing about the boards the cut list
cuts. Now every fill is the colour of the board that part is cut from, read
through `render.board_look` and from nowhere else.

What is pinned here:

  * **one resolver.** No hex literal for a board sits anywhere in `render.py`
    outside the small set of paper colours (ink, rule, faint, muted, critical).
    A fill written straight into a drawing is the fifth list all over again.
  * **the fills follow the fields the engine reads** - door leaf *i* from
    `door_board(i)`, a drawer face from `face_board_of(d)`, the body from
    `carcass_board`, the plan's footprint from `exterior_board`.
  * **the layer is in the outline, not the fill.** Base plain, wall dashed,
    tall heavier; a clash still red, and still dashed when it is a wall unit.
  * **text reads on whatever colour the board is.** The ink is computed from
    the fill's luminance, and both inks clear 3:1 on every fill, including the
    mid greys where a fixed muted grey used to vanish at 1.04:1.
  * **grain runs the way the cut list cuts it** - vertical on doors and on
    drawer faces (ruled 20 Sept 2026), and only on a board whose record says
    grain.
  * **an unset colour is neutral and says so on the legend**, and is not a
    validation issue - nobody wants a warning on every job for a colour that
    does not change a cut.
  * **the run selects.** Its cabinets carry `data-cab`, marked `erun` so the
    drag handler knows there is no wall to move along.
"""
import os
import re
import sys

ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, ROOT)

from cabinetgen import render as R                                        # noqa: E402
from cabinetgen.model import NO_COLOUR, Cabinet, Drawer, Job, Placement   # noqa: E402
from cabinetgen.room import rectangular                                   # noqa: E402
from cabinetgen.validate import validate                                  # noqa: E402

FAILS = []


def check(name, got, want):
    ok = got == want
    print(f"  {'ok   ' if ok else 'FAIL '} {name}: {got}" + ("" if ok else f"  want {want}"))
    if not ok:
        FAILS.append(name)


MATS = {
    "WHITE": {"name": "White", "tape": "WHITE", "thickness": 16, "grain": "plain",
              "colour": "#ffffff", "has_edging": True,
              "edging_kinds": ["pvc", "1mm", "2mm"]},
    "WOOD": {"name": "Woodgrain", "tape": "WOOD", "thickness": 16, "grain": "grain",
             "colour": "#d2b36a", "has_edging": True,
             "edging_kinds": ["pvc", "1mm", "2mm"]},
    "DARK": {"name": "Dark", "tape": "DARK", "thickness": 16, "grain": "plain",
             "colour": "#1a1a1a", "has_edging": True,
             "edging_kinds": ["pvc", "1mm", "2mm"]},
    "BLANK": {"name": "Uncoloured", "tape": "BLANK", "thickness": 16,
              "grain": "plain", "colour": "", "has_edging": True,
              "edging_kinds": ["pvc", "1mm", "2mm"]},
}


def job():
    """One base unit with a woodgrain door and dark drawer faces, on a wall."""
    c = Cabinet(1, 900, 720, 580, kind="base", doors=1,
                carcass_board="WHITE", exterior_board="WOOD", back_board="WHITE",
                drawer_face_board="DARK", drawer_carcass_board="WHITE")
    c.drawers = [Drawer(face_height=200, box_height=150),
                 Drawer(face_height=200, box_height=150)]
    c.doors = 0
    tall = Cabinet(2, 600, 2100, 580, kind="tall", doors=2,
                   carcass_board="WHITE", exterior_board="WOOD", back_board="WHITE")
    upper = Cabinet(3, 600, 720, 330, kind="upper", doors=1,
                    carcass_board="BLANK", exterior_board="BLANK",
                    back_board="WHITE")
    j = Job(name="colour", cabinets=[c, tall, upper], materials=dict(MATS),
            boards=["WHITE", "WOOD", "DARK", "BLANK"],
            room=rectangular(4000, 3000, ceiling=2600),
            placements=[Placement(1, "A", 0), Placement(2, "A", 1000),
                        Placement(3, "A", 2000, z=1400)])
    return j


def main():
    print("one resolver, and no board colour stated anywhere else")
    src = open(os.path.join(ROOT, "cabinetgen", "render.py"), encoding="utf-8-sig").read()
    paper = {R.INK, R.RULE, R.FAINT, R.MUTED, R.CRIT, R.PAPER, "#dfe3dd",
             "#f6e0e3", "#fff"}
    stray = sorted({h for h in re.findall(r'"#[0-9a-fA-F]{3,6}"', src)
                    if h.strip('"') not in paper})
    check("no hex literal in render.py but the paper colours", stray, [])
    # The 3D view (Part F): scene.py states no colour at all — every look comes
    # off board_look — and view3d.js keeps its own paper colours (background,
    # grid, edges, the selection, the warning colour for an obstruction) in
    # the one PAPER block at the top, with no literal anywhere else in it.
    scene_src = open(os.path.join(ROOT, "cabinetgen", "scene.py"), encoding="utf-8-sig").read()
    check("no hex literal at all in scene.py",
          re.findall(r'"#[0-9a-fA-F]{3,6}"|0x[0-9a-fA-F]{6}\b', scene_src), [])
    js = open(os.path.join(ROOT, "app", "view3d.js"), encoding="utf-8-sig").read()
    block = re.search(r"const PAPER = \{.*?\n\};", js, re.S)
    check("view3d.js has its PAPER block", block is not None, True)
    outside = js[:block.start()] + js[block.end():] if block else js
    check("no colour literal in view3d.js outside PAPER",
          re.findall(r'"#[0-9a-fA-F]{3,6}"|\'#[0-9a-fA-F]{3,6}\'|0x[0-9a-fA-F]{6}\b', outside), [])
    check("and no board is named in PAPER",
          [w for w in ("MEL", "BROOKHILL", "GREY", "BACK", "DECOR") if block and w in block.group(0)], [])
    check("the fill comes back on the record's colour",
          R.board_look(MATS, "WOOD")["colour"], "#d2b36a")
    check("a board nobody coloured is neutral, and says so",
          (R.board_look(MATS, "BLANK")["colour"], R.board_look(MATS, "BLANK")["set"]),
          (NO_COLOUR, False))
    check("so is a board the project does not carry",
          R.board_look(MATS, "NOSUCH")["colour"], NO_COLOUR)
    check("grain is the record's, not the panel's role",
          (R.board_look(MATS, "WOOD")["grain"], R.board_look(MATS, "WHITE")["grain"]),
          (True, False))
    check("a Job and its materials give the same answer",
          R.board_look(job(), "WOOD"), R.board_look(MATS, "WOOD"))
    check("only a real hex reaches a fill",
          (R.board_look({"B": {"colour": '"/><script>'}}, "B")["colour"],
           R.board_look({"B": {"colour": "#FA0"}}, "B")["colour"]),
          (NO_COLOUR, "#ffaa00"))

    print("\nthe fills are the boards the cut list cuts")
    j = job()
    svg = R.wall_elevation_svg(j, "A")
    doors = re.findall(r'class="edoor"[^>]*fill="(#[0-9a-f]{6})"', svg)
    faces = re.findall(r'<rect x="[^"]*" y="[^"]*" width="[^"]*" height="[^"]*" '
                       r'fill="(#[0-9a-f]{6})" stroke="' + R.RULE, svg)
    bodies = re.findall(r'class="ecab"[^>]*fill="(#[0-9a-f]{6})"', svg)
    check("a woodgrain door draws woodgrain, an uncoloured one neutral",
          sorted(set(doors)), ["#d2b36a", NO_COLOUR])
    check("dark drawer faces draw dark", sorted(set(faces)), ["#1a1a1a"])
    check("the bodies are their carcass boards, the uncoloured one neutral",
          bodies, ["#ffffff", "#ffffff", NO_COLOUR])
    j.cabinets[0].door_boards = ["DARK"]
    j.cabinets[0].doors = 1
    check("a leaf with its own board draws its own board",
          re.findall(r'class="edoor" data-cab="1"[^>]*fill="(#[0-9a-f]{6})"',
                     R.wall_elevation_svg(j, "A")),
          ["#1a1a1a"])

    print("\nthe layer is in the outline, not the fill")
    j = job()
    svg = R.wall_elevation_svg(j, "A")
    got = re.findall(r'class="ecab" data-cab="(\d)"[^>]*stroke-width="([\d.]+)"'
                     r'(?: stroke-dasharray="([^"]*)")?', svg)
    # One weight for every layer since 23 Sept 2026 (brief item 3): an
    # elevation says which is which by where it stands, and no dash is drawn
    # that says nothing.
    check("base, tall and wall at the one carcass weight, none dashed", got,
          [("1", R.WEIGHT["carcass"], ""), ("2", R.WEIGHT["carcass"], ""),
           ("3", R.WEIGHT["carcass"], "")])
    j.placements[1].x = 100                       # cabinet 2 now overlaps cabinet 1
    clash = re.search(r'<rect class="ecab" data-cab="2"[^>]*>',
                      R.wall_elevation_svg(j, "A")).group(0)
    check("a clash is still red", R.CRIT in clash, True)
    check("and the plan dashes a wall unit, which is above its cut",
          'stroke-dasharray="4 3"' in R.plan_svg(job()), True)

    print("\ntext reads on whatever colour the board is")
    for fill in ("#ffffff", "#000000", "#1a1a1a", "#d2b36a", "#7f7f7f", "#a0a0a0",
                 "#606060", "#767676", NO_COLOUR):
        check(f"ink and muted both clear 3:1 on {fill}",
              (round(R._contrast(fill, R.ink_on(fill)), 2) >= 3.0,
               round(R._contrast(fill, R.muted_on(fill)), 2) >= 3.0),
              (True, True))
    check("a white board keeps the ink it always had", R.ink_on("#ffffff"), R.INK)
    check("a black one turns the ink over", R.ink_on("#000000"), R.PAPER)

    print("\ngrain runs the way the cut list cuts it")
    lines = re.findall(r'<line x1="([\d.]+)"[^>]*x2="([\d.]+)"[^>]*stroke-opacity="0.22"',
                       R.wall_elevation_svg(job(), "A"))
    check("every grain line is vertical, the way Length runs up a front",
          bool(lines) and all(a == b for a, b in lines), True)
    plain = job()
    for cab in plain.cabinets:
        cab.exterior_board = cab.carcass_board = "WHITE"
        cab.drawer_face_board = "WHITE"
    check("a plain board draws none",
          'stroke-opacity="0.22"' in R.wall_elevation_svg(plain, "A"), False)

    print("\nthe legend names what the drawing drew")
    svg = R.wall_elevation_svg(job(), "A")
    check("one swatch per board the drawing put on the paper",
          svg.count('class="swatch"'), 4)
    legend = svg[svg.index('class="swatch"'):]
    check("an unset colour says so, and the legend never truncates",
          ("BLANK — Uncoloured (no colour set)" in svg, "…" in legend),
          (True, False))
    check("the plan names the exterior boards it tinted with",
          R.plan_svg(job()).count('class="swatch"'), 2)
    check("and a board the project carries but did not draw is not on it",
          "DARK — Dark" in R.wall_elevation_svg(job(), "B"), False)

    print("\nan unset colour is not a validation issue")
    issues = validate(job(), [])
    check("nothing warns about colour",
          [i.message for i in issues if "colour" in i.message.lower()], [])

    print("\nthe run selects, and says it is not a wall")
    run = R.elevation_svg(job())
    check("every cabinet in the run carries its number",
          re.findall(r'<g class="ecabg erun" data-cab="(\d)"', run), ["1", "2", "3"])
    check("marked erun, so the drag handler knows there is no wall",
          'class="ecabg" data-cab=' in run, False)
    check("the wall's groups are unmarked, and still drag",
          'class="ecabg" data-cab="1"' in R.wall_elevation_svg(job(), "A"), True)

    print("\nnothing else moved")
    plain = job()
    plain.room, plain.placements = None, []
    check("no room still falls back to the run, byte for byte",
          R.wall_elevation_svg(plain, "A") == R.elevation_svg(plain), True)
    check("a job with no materials at all still draws",
          R.elevation_svg(Job(name="x", cabinets=[Cabinet(1, 600, 720, 580)])
                          ).startswith("<svg"), True)

    print(f"\n{'ALL OK' if not FAILS else str(len(FAILS)) + ' FAILED: ' + str(FAILS)}")
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
