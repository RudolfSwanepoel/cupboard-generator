"""The October 2025 main-bedroom wardrobe and vanity, as cabinet definitions.

This is the regression fixture. It is the real job Plazaboard cut on quotation
VRG_SOQ497999, rebuilt from cabinet parameters only. Running tools/regen_check.py
compares what the engine produces against the cut list that was actually sent,
so any change to the rules shows up immediately as a diff.

Note it is defined CORRECTLY, not as-built. Where the real sheet had an error
(cabinet 30's drawer faces, cabinets 8-10's bottoms) this file carries the right
value and the comparison reports the difference against the logged finding.
"""
from cabinetgen.drawers import equal_faces, graduated_faces, make_drawers, opening_for, stack
from cabinetgen.model import Cabinet, Drawer, Job, Panel
from cabinetgen.standard import STANDARD

# The tapes the real order was quoted with. No template cabinet states them any
# more — every one is what its boards derive: PVC and 2 mm in the exterior
# board's colour, PVC in the carcass board's. That was reconciled against the
# stored values cabinet by cabinet, with no mismatches, before the fields were
# switched over. The names stay because the bespoke panels of cabinets 7 and 13
# are hand-specified and carry their own edge material.
DECOR_EDGE = "2mm WOOD"
CARC_EDGE = "PVC WOOD"


def tall(number, width, **kw):
    kw.setdefault("height", 2400)
    kw.setdefault("depth", 500)
    return Cabinet(number=number, width=width, **kw)


def _drawer_bank(number, width, n_drawers, door_height, box_h=150):
    """Door over a drawer stack. Faces are sized to fill what the door leaves."""
    return tall(number, width,
                supports=5, edged_supports=1,
                fixed_shelves=1, shelves=3,
                doors=2, door_height=door_height,
                drawers=stack(2400, n_drawers, box_h, door_height=door_height))


CABINETS = [
    _drawer_bank(1, 700, 5, 1297),
    tall(2, 550, supports=4, shelves=2, doors=2),
    # Bespoke panels carry their own designations from the day they are defined —
    # the cut list never renames anything. The half-width shelf is 05b because
    # the cabinet's generated full-width shelf is 05.
    tall(3, 1000, supports=4, shelves=1, divider_count=1, divider_height=2050, doors=2,
         bespoke=[Panel(3, "05b", "Shelve", "MEL", 476, 477, 1,
                        edge_l=1, edge_material=CARC_EDGE, note="half-width, right of divider")]),
    _drawer_bank(4, 700, 5, 1297),
    tall(5, 1000, supports=4, shelves=1, divider_count=1, divider_height=2050, doors=2,
         bespoke=[Panel(5, "05b", "Shelve", "MEL", 476, 477, 1,
                        edge_l=1, edge_material=CARC_EDGE, note="half-width, right of divider")]),

    # 7 — corner carcass. Not a template; three different side widths and no back.
    # Its declared 850 x 500 is a label: the sides are 818 and 834 deep. Its plan
    # outline is a mitre, parametric per docs/ROOM-LAYOUT-SPEC.md item 14 —
    # arm_a/arm_b 850, face_a/face_b 500, giving the 850,0 850,850 350,850 0,500
    # outline and the 350x350 (495 mm) mitre door face.
    Cabinet(number=7, width=850, height=2400, depth=500, back="none", supports=0,
            template="none",
            note="corner box, hand-built",
            corner_style="mitre", arm_a=850, arm_b=850, face_a=500, face_b=500,
            bespoke=[
                Panel(7, "01a", "Side", "MEL", 2400, 500, 2, edge_l=1, edge_material=CARC_EDGE),
                Panel(7, "01b", "Side", "MEL", 2400, 818, 1, edge_l=1, edge_material=CARC_EDGE),
                Panel(7, "01c", "Side", "MEL", 2400, 834, 1, edge_l=1, edge_material=CARC_EDGE),
                Panel(7, "02", "Top", "MEL", 818, 818, 1, edge_l=1, edge_material=CARC_EDGE),
                Panel(7, "03", "Bottom", "MEL", 818, 818, 1, edge_l=1, edge_material=CARC_EDGE),
                Panel(7, "05", "Shelve", "MEL", 818, 350, 6, edge_l=1, edge_material=CARC_EDGE),
                Panel(7, "07", "Door", "DECOR", 2397, 472, 1, edge_l=2, edge_w=2,
                      edge_material=DECOR_EDGE, pot_holes=4, grain=1),
            ]),

    tall(8, 500, supports=4, shelves=7, doors=1),
    tall(9, 500, supports=4, shelves=7, doors=1),
    tall(10, 500, supports=4, shelves=7, doors=1, exposed_sides=1),
    tall(11, 1000, supports=4, shelves=7, shelf_width=400,
         divider_count=1, divider_height=2368, doors=2),
    tall(12, 1000, supports=4, shelves=7, shelf_width=400,
         divider_count=1, divider_height=2368, doors=2),

    # 13 — overhead in décor board: sides and a top, no bottom, no back.
    Cabinet(number=13, width=850, height=2000, depth=500, back="none", supports=0,
            template="none",
            note="overhead, décor carcass",
            bespoke=[
                Panel(13, "01", "Side", "DECOR", 2000, 500, 2, edge_l=1,
                      edge_material=CARC_EDGE, grain=1),
                Panel(13, "02", "Top", "DECOR", 818, 500, 1, edge_l=1,
                      edge_material=CARC_EDGE, grain=1),
                Panel(13, "07", "Door", "DECOR", 1997, 422, 2, edge_l=2, edge_w=2,
                      edge_material=DECOR_EDGE, pot_holes=4, grain=1),
            ]),

    Cabinet(number=14, width=850, height=400, depth=450, kind="upper", back="four",
            supports=2, doors=2),

    tall(25, 750, depth=600, supports=4, shelves=5, doors=2),
    tall(26, 350, depth=600, supports=4, shelves=3, doors=1),

    # --- vanity, 790 high -------------------------------------------------
    Cabinet(number=27, width=500, height=790, depth=570, kind="base", back="three",
            supports=4, edged_supports=1, white_supports=1,
            drawers=[Drawer(787, 200, "melamine")],
            note="vanity, single full-height drawer"),
    Cabinet(number=28, width=400, height=790, depth=390, kind="base", back="three",
            supports=4, edged_supports=1, white_supports=1, shelves=1, doors=1,
            note="vanity side cupboard"),
    Cabinet(number=29, width=400, height=790, depth=390, kind="base", back="three",
            supports=4, edged_supports=1, white_supports=1, shelves=1, doors=1,
            note="vanity side cupboard"),
    Cabinet(number=30, width=350, height=790, depth=390, kind="base", back="none",
            supports=4, edged_supports=1,
            # Equal faces. For a graduated stack instead, either of these works:
            #   stack(790, [1, 1.5, 1.5, 2.4], [90, 116, 116, 200])
            #   stack(790, [120, 183, 183, 296], [90, 116, 116, 200])
            drawers=stack(790, 4, 150),
            note="vanity drawer bank; as-built faces were 178 each — see finding W5"),
]

# Loose panels: exposed sides sold as a group, and the filler strips.
LOOSE = [
    Panel(6, "08", "Exposed Panel", "DECOR", 2400, 516, 5, edge_l=1,
          edge_material=DECOR_EDGE, grain=1),
    Panel(15, "08", "Filler", "DECOR", 2400, 80, 1, grain=1),
    Panel(16, "08", "Filler", "DECOR", 1596, 50, 1, grain=1),
    Panel(17, "08", "Filler", "DECOR", 484, 50, 1, grain=1),
    Panel(18, "08", "Filler", "DECOR", 2882, 50, 1, grain=1,
          note="as ordered — exceeds the board, see finding W2"),
    Panel(19, "08", "Filler", "DECOR", 484, 50, 2, grain=1),
    Panel(20, "08", "Filler", "DECOR", 484, 50, 2, grain=1),
    Panel(21, "08", "Filler", "DECOR", 2300, 50, 0, grain=1, note="cancelled"),
    Panel(22, "08", "Filler", "DECOR", 500, 50, 0, grain=1, note="cancelled"),
    Panel(23, "08", "Filler", "DECOR", 1750, 50, 0, grain=1, note="cancelled"),
    Panel(24, "08", "Filler", "MEL", 2400, 100, 4, edge_l=1, edge_material=CARC_EDGE),
]

JOB = Job(name="wardrobe_oct2025", cabinets=CABINETS, loose=LOOSE)
