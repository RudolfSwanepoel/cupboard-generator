"""Boards, derived edge tapes, and supports as rows.

    python tools/check_boards.py

What is pinned here, and why:

  * **A cabinet names two boards.** The carcass board is what the box is cut
    from — sides, top, bottom, supports, shelves, dividers — and the exterior
    board is what shows: doors, drawer faces, exposed ends. Before this, "MEL"
    was typed into the engine on every carcass panel, so a decor or microwave
    cupboard with a Brookhill carcass could not be expressed at all. Each board
    nests and prices as its own material.
  * **Tape is a lookup on the board, never a name built out of one.** "PVC WOOD"
    and "2mm WOOD" are what Plazaboard call the Brookhill tapes; nothing about
    "BROOKHILL FUSION CHIP" spells either. A board with no tape of the thickness
    a cabinet needs is named in a warning rather than guessed at — D6 / W10 is
    exactly that mistake reaching a real order.
  * **Derivation reproduces the October job.** Every tape on that job was
    reconciled against the stored value before the fields were switched over,
    with no mismatches, which is why the fixture states none of them any more.
  * **An override is per cabinet** and beats the derivation, which is how a job
    written before the boards keeps saying what it always said.
  * **Supports are rows, and nothing subtracts.** The old total-minus-subsets
    model let `edged + white` exceed the total and dropped the negative plain
    count in silence. A migrated cabinet cuts the same list in the same order,
    and one whose three numbers contradict each other is named.
"""
import os
import sys

ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, ROOT)

from cabinetgen.engine import generate_cabinet, generate_job                  # noqa: E402
from cabinetgen.model import (MATERIALS, Cabinet, Drawer, Job, Support,       # noqa: E402
                              grain_of, material_board, tape_for)
from cabinetgen.store import cabinet_from_dict, cabinet_to_dict, load         # noqa: E402
from cabinetgen.validate import validate                                      # noqa: E402
from jobs.wardrobe_oct2025 import JOB                                         # noqa: E402

FAILS = []

CARCASS_CODES = ("01", "02", "03", "04", "05", "09")
EXTERIOR_CODES = ("07", "08", "20")


def check(name, got, want):
    ok = got == want
    print(f"  {'ok   ' if ok else 'FAIL '} {name}: {got}" + ("" if ok else f"  want {want}"))
    if not ok:
        FAILS.append(name)


def box(**kw):
    """A cabinet with one of everything the boards touch."""
    kw.setdefault("doors", 1)
    kw.setdefault("shelves", 1)
    kw.setdefault("fixed_shelves", 1)
    kw.setdefault("divider_count", 1)
    kw.setdefault("exposed_sides", 1)
    kw.setdefault("drawers", [Drawer(200, 150)])
    kw.setdefault("support_rows", [Support("none", 1), Support("front", 1),
                                   Support("white", 1)])
    kw.setdefault("number", 1)
    return Cabinet(width=600, height=2000, depth=500, **kw)


def by_code(panels):
    return {p.code.rstrip("abcdefgh") or p.code: p for p in panels}


def mats_of(panels, codes):
    return sorted({p.material for p in panels if p.code[:2] in codes})


def main() -> int:                                                  # noqa: C901
    print("a cabinet names two boards, and every panel takes the right one")
    p = generate_cabinet(box())
    check("carcass panels take the carcass board", mats_of(p, CARCASS_CODES), ["MEL"])
    check("what shows takes the exterior board", mats_of(p, EXTERIOR_CODES), ["DECOR"])

    swapped = generate_cabinet(box(carcass_board="DECOR"))
    check("a Brookhill carcass cuts its box from Brookhill",
          mats_of(swapped, CARCASS_CODES), ["DECOR"])
    check("and what shows is untouched by it",
          mats_of(swapped, EXTERIOR_CODES), ["DECOR"])
    both = generate_cabinet(box(carcass_board="DECOR", exterior_board="MEL"))
    check("the two are independent",
          (mats_of(both, CARCASS_CODES), mats_of(both, EXTERIOR_CODES)),
          (["DECOR"], ["MEL"]))
    check("every carcass code is covered, none left saying MEL by hand",
          sorted({c for c in (x.code[:2] for x in swapped) if c in CARCASS_CODES}),
          ["01", "02", "03", "04", "05", "09"])
    check("the backing board is its own material, not either of them",
          sorted({x.material for x in p if x.code[:2] == "06"}), ["BACK"])

    print("\nit nests and prices as that material")
    job = Job(name="b", cabinets=[box(number=1, carcass_board="DECOR")])
    panels = generate_job(job)
    check("a Brookhill carcass reaches the cut list as DECOR",
          sorted({x.material for x in panels if x.code[:2] in CARCASS_CODES}), ["DECOR"])
    check("and DECOR is a board the quote knows the price of",
          material_board(job.materials, "DECOR"), "BROOKHILL FUSION CHIP")

    print("\ntape is a lookup on the board, never built out of its name")
    check("the white board has a PVC tape", tape_for(MATERIALS, "MEL", "pvc"), "PVC WHITE")
    check("no 2 mm tape is claimed for it — none has ever been ordered",
          tape_for(MATERIALS, "MEL", "2mm"), "")
    check("Brookhill has both", (tape_for(MATERIALS, "DECOR", "pvc"),
                                 tape_for(MATERIALS, "DECOR", "2mm")),
          ("PVC WOOD", "2mm WOOD"))
    check("a 3 mm back is never edged, so it maps no tape",
          (tape_for(MATERIALS, "BACK", "pvc"), tape_for(MATERIALS, "BACK", "2mm")),
          ("", ""))
    # A concatenation rule would give "PVC BROOKHILL FUSION CHIP"; the real tape
    # is "PVC WOOD", which nothing about the board description spells.
    check("a tape is not the thickness stuck in front of the board description",
          (tape_for(MATERIALS, "DECOR", "pvc"),
           "PVC " + material_board(MATERIALS, "DECOR")),
          ("PVC WOOD", "PVC BROOKHILL FUSION CHIP"))
    renamed = {"MEL": dict(MATERIALS["MEL"]),
               "DECOR": dict(MATERIALS["DECOR"], board="SOME OTHER CHIP")}
    check("so renaming the board does not move the tape",
          box().carcass_tape(renamed), "PVC WOOD")

    print("\ngrain follows the board, not what the panel is for")
    check("the white board has no direction; the woodgrain one does",
          (grain_of(MATERIALS, "MEL"), grain_of(MATERIALS, "DECOR"),
           grain_of(MATERIALS, "BACK")), (0, 1, 0))
    white = generate_cabinet(box())
    check("a white carcass is grain 0, as it always was",
          sorted({x.grain for x in white if x.code[:2] in CARCASS_CODES}), [0])
    check("and what shows on it is grain 1, as it always was",
          sorted({x.grain for x in white if x.code[:2] in EXTERIOR_CODES}), [1])
    brook = generate_cabinet(box(carcass_board="DECOR"))
    check("a Brookhill carcass runs with the grain on every carcass panel",
          sorted({x.grain for x in brook if x.code[:2] in CARCASS_CODES}), [1])
    check("which is how cabinet 13 of the October job was hand-built",
          sorted({x.grain for x in
                  next(c for c in JOB.cabinets if c.number == 13).bespoke}), [1])
    plain = generate_cabinet(box(exterior_board="MEL", door_edge="2mm SOLID"))
    check("a white door is grain 0 — grain was never a property of being a door",
          sorted({x.grain for x in plain if x.code[:2] in EXTERIOR_CODES}), [0])
    brook_job = Job(name="g", cabinets=[box(carcass_board="DECOR")])
    check("so a Brookhill carcass raises no grain critical, and exports",
          [i.message for i in validate(brook_job, generate_job(brook_job))
           if "grain" in i.message], [])

    print("the three tapes come off the two boards")
    c = box()
    check("carcass edge is PVC in the exterior colour", c.carcass_tape(MATERIALS), "PVC WOOD")
    check("door edge is 2 mm in the exterior colour", c.door_tape(MATERIALS), "2mm WOOD")
    check("drawer box edge is PVC in the carcass colour",
          c.drawer_box_tape(MATERIALS), "PVC WHITE")
    d = by_code(generate_cabinet(c))
    check("shelf and divider fronts match the front, not the box (ruled 14 Sept 2026)",
          (d["05"].edge_material, d["09"].edge_material), ("PVC WOOD", "PVC WOOD"))
    check("drawer sides and fronts take the box tape",
          (d["18"].edge_material, d["19"].edge_material), ("PVC WHITE", "PVC WHITE"))
    check("a Brookhill carcass takes its drawer boxes in the Brookhill PVC",
          box(carcass_board="DECOR").drawer_box_tape(MATERIALS), "PVC WOOD")

    print("\na board with no tape mapped is named, never guessed at")
    naked = Job(name="n", cabinets=[box(exterior_board="MEL")])
    msgs = [i.message for i in validate(naked, generate_job(naked))
            if "no 2mm tape" in i.message]
    check("the warning names the board and the field",
          msgs, ["no 2mm tape is mapped for 'SUPER WHITE MELAMINE CHIP 9X6X16MM', so "
                 "door_edge cannot be derived for its doors, drawer faces and exposed "
                 "panels — map one on the material, or override it on this cabinet"])
    check("and no tape name is invented in its place",
          by_code(generate_cabinet(box(exterior_board="MEL"))) ["07"].edge_material, "")
    check("a cabinet that needs no 2 mm tape is not asked for one",
          [i.message for i in validate(
              Job(name="n2", cabinets=[Cabinet(number=1, width=600, height=720, depth=500,
                                               exterior_board="MEL")]), [])
           if "no 2mm tape" in i.message], [])
    check("an override silences it, because the cabinet was told what to use",
          [i.message for i in validate(
              Job(name="n3", cabinets=[box(exterior_board="MEL", door_edge="2mm SOLID")]), [])
           if "no 2mm tape" in i.message], [])

    print("\nan override beats the derivation, per cabinet")
    over = by_code(generate_cabinet(box(carcass_edge="PVC BROOKHILL")))
    check("the override is what lands on the panel", over["01"].edge_material,
          "PVC BROOKHILL")
    check("and the tapes it does not name are still derived",
          over["07"].edge_material, "2mm WOOD")

    print("\nthe October job derives exactly what it was quoted with")
    stated = {"carcass_edge": "PVC WOOD", "door_edge": "2mm WOOD",
              "drawer_box_edge": "PVC WHITE"}
    mismatches = [(c.number, f, c.tapes(JOB.materials)[f], v)
                  for c in JOB.cabinets if c.template != "none"
                  for f, v in stated.items() if c.tapes(JOB.materials)[f] != v]
    check("every template cabinet, every tape", mismatches, [])
    check("and none of them states a tape any more",
          [c.number for c in JOB.cabinets
           if (c.carcass_edge, c.door_edge, c.drawer_box_edge) != (None, None, None)], [])

    print("\nsupports are rows, and nothing subtracts")
    rows = box(support_rows=[Support("front", 1), Support("white", 2), Support("none", 3)])
    check("the total is the sum of the rows", rows.support_total, 6)
    got = [(x.qty, x.edge_material) for x in generate_cabinet(rows) if x.code[:2] == "04"]
    check("one cut-list line per row, in row order",
          got, [(1, "PVC WOOD"), (2, "PVC WHITE"), (3, "")])
    check("a zero-quantity row makes nothing",
          [x.qty for x in generate_cabinet(box(support_rows=[Support("front", 0),
                                                             Support("none", 2)]))
           if x.code[:2] == "04"], [2])

    print("\nthe three old numbers migrate to the same cut list, in the same order")
    legacy = Cabinet(number=1, width=600, height=2000, depth=500,
                     supports=4, edged_supports=1, white_supports=1)
    check("plain, then front-edged, then white-edged — as the engine always emitted",
          [(r.edge, r.qty) for r in legacy.support_list],
          [("none", 2), ("front", 1), ("white", 1)])
    check("and the panels come out that way",
          [(x.qty, x.edge_material) for x in generate_cabinet(legacy) if x.code[:2] == "04"],
          [(2, ""), (1, "PVC WOOD"), (1, "PVC WHITE")])
    check("rows win over the old numbers once they exist",
          [(r.edge, r.qty) for r in Cabinet(number=1, width=600, height=2000, depth=500,
                                            supports=4, edged_supports=1, white_supports=1,
                                            support_rows=[Support("none", 9)]).support_list],
          [("none", 9)])

    print("\nnumbers that contradict each other are named, not migrated on a guess")
    bad = Cabinet(number=3, width=600, height=2000, depth=500,
                  supports=0, edged_supports=0, white_supports=4)
    check("the old model implied minus four plain supports",
          bad.legacy_supports_negative, True)
    check("the cut list is what it always was — four white, no plain",
          [(x.qty, x.edge_material) for x in generate_cabinet(bad) if x.code[:2] == "04"],
          [(4, "PVC WHITE")])
    check("and the cabinet is named, with what is being cut",
          [i.message for i in validate(Job(name="s", cabinets=[bad]), [])
           if "contradict" in i.message],
          ["supports 0 with 0 front-edged and 4 white-edged leaves -4 plain — the three "
           "numbers contradict each other. 4 supports are being cut, which is what the "
           "cut list has always said; set the rows to say what was meant"])
    check("a cabinet whose numbers agree says nothing",
          [i.message for i in validate(Job(name="s2", cabinets=[legacy]), [])
           if "contradict" in i.message], [])

    print("\njob files: the two renames, and nothing dropped")
    old_file = {"number": 5, "width": 600, "height": 2000, "depth": 500,
                "decor": "DECOR", "carcass_edge": "PVC WOOD", "door_edge": "2mm WOOD",
                "drawer_box_edge": "PVC WHITE", "supports": 4, "white_supports": 2}
    back = cabinet_from_dict(old_file)
    check("decor is read as the exterior board", back.exterior_board, "DECOR")
    check("and the carcass board defaults to the white it always was",
          back.carcass_board, "MEL")
    check("a tape it stated is kept as the override it now is",
          (back.carcass_edge, back.door_edge, back.drawer_box_edge),
          ("PVC WOOD", "2mm WOOD", "PVC WHITE"))
    check("its supports migrate", [(r.edge, r.qty) for r in back.support_list],
          [("none", 2), ("white", 2)])
    roundtrip = cabinet_from_dict(cabinet_to_dict(box(support_rows=[Support("front", 2)])))
    check("a cabinet written today reads back identically",
          cabinet_to_dict(roundtrip), cabinet_to_dict(box(support_rows=[Support("front", 2)])))

    print("\nstored jobs still cut what they cut")
    for name, want in (("Test.json", 36), ("Test_Build.json", 27)):
        j = load(os.path.join(ROOT, "jobs", name))
        check(f"{name} generates the same number of panel lines",
              len(generate_job(j)), want)
        check(f"  and its tapes are unchanged",
              sorted({x.edge_material for x in generate_job(j) if x.edge_material}),
              ["2mm WOOD", "PVC WHITE", "PVC WOOD"])

    print(f"\n{'ALL OK' if not FAILS else str(len(FAILS)) + ' FAILED: ' + str(FAILS)}")
    return 1 if FAILS else 0


if __name__ == "__main__":
    raise SystemExit(main())
