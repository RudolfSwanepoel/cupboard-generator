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
    and "2mm WOOD" are what the October order was edged with; nothing about
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
from cabinetgen.model import (BOARD_ALIASES, MATERIALS, Cabinet, Drawer,     # noqa: E402
                              Job, Panel, Support, grain_of, material_board,
                              resolve_board, tape_for)
from cabinetgen.standard import STANDARD as S                              # noqa: E402
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
    check("what shows takes the exterior board", mats_of(p, EXTERIOR_CODES), ["BROOKHILL"])

    swapped = generate_cabinet(box(carcass_board="BROOKHILL"))
    check("a Brookhill carcass cuts its box from Brookhill",
          mats_of(swapped, CARCASS_CODES), ["BROOKHILL"])
    check("and what shows is untouched by it",
          mats_of(swapped, EXTERIOR_CODES), ["BROOKHILL"])
    both = generate_cabinet(box(carcass_board="BROOKHILL", exterior_board="MEL"))
    check("the two are independent",
          (mats_of(both, CARCASS_CODES), mats_of(both, EXTERIOR_CODES)),
          (["BROOKHILL"], ["MEL"]))
    check("every carcass code is covered, none left saying MEL by hand",
          sorted({c for c in (x.code[:2] for x in swapped) if c in CARCASS_CODES}),
          ["01", "02", "03", "04", "05", "09"])
    check("the backing board is its own material, not either of them",
          sorted({x.material for x in p if x.code[:2] == "06"}), ["BACK"])

    print("\nit nests and prices as that material")
    job = Job(name="b", cabinets=[box(number=1, carcass_board="BROOKHILL")])
    panels = generate_job(job)
    check("a Brookhill carcass reaches the cut list as BROOKHILL",
          sorted({x.material for x in panels if x.code[:2] in CARCASS_CODES}), ["BROOKHILL"])
    check("and BROOKHILL is a board the quote knows the price of",
          material_board(job.materials, "BROOKHILL"), "BROOKHILL FUSION CHIP")

    print("\ntape names are generated from the board's token, not mapped")
    check("PVC, 1 mm and 2 mm all come off one token",
          [tape_for(MATERIALS, "BROOKHILL", k) for k in ("pvc", "1mm", "2mm")],
          ["PVC WOOD", "1mm WOOD", "2mm WOOD"])
    check("the white board generates its own three the same way",
          [tape_for(MATERIALS, "MEL", k) for k in ("pvc", "1mm", "2mm")],
          ["PVC WHITE", "1mm WHITE", "2mm WHITE"])
    # The token is a field of its own, and this is why: edging names are decided
    # per order, and generating off the long description would put the board's
    # full name on an order as an edging name.
    check("the token is not the board's name, and the tape proves it",
          (tape_for(MATERIALS, "BROOKHILL", "pvc"),
           "PVC " + material_board(MATERIALS, "BROOKHILL")),
          ("PVC WOOD", "PVC BROOKHILL FUSION CHIP"))
    renamed = {"MEL": dict(MATERIALS["MEL"]),
               "BROOKHILL": dict(MATERIALS["BROOKHILL"], board="SOME OTHER CHIP",
                             name="SOME OTHER CHIP")}
    check("so renaming the board does not move the tape",
          box().carcass_tape(renamed), "PVC WOOD")
    check("a board with nothing to build from generates nothing, and invents nothing",
          tape_for({"X": {"name": "", "tape": ""}}, "X", "pvc"), "")

    print("\ngrain follows the board, not what the panel is for")
    check("the white board has no direction; the woodgrain one does",
          (grain_of(MATERIALS, "MEL"), grain_of(MATERIALS, "BROOKHILL"),
           grain_of(MATERIALS, "BACK")), (0, 1, 0))
    white = generate_cabinet(box())
    check("a white carcass is grain 0, as it always was",
          sorted({x.grain for x in white if x.code[:2] in CARCASS_CODES}), [0])
    check("and what shows on it is grain 1, as it always was",
          sorted({x.grain for x in white if x.code[:2] in EXTERIOR_CODES}), [1])
    brook = generate_cabinet(box(carcass_board="BROOKHILL"))
    check("a Brookhill carcass runs with the grain on every carcass panel",
          sorted({x.grain for x in brook if x.code[:2] in CARCASS_CODES}), [1])
    check("which is how cabinet 13 of the October job was hand-built",
          sorted({x.grain for x in
                  next(c for c in JOB.cabinets if c.number == 13).bespoke}), [1])
    plain = generate_cabinet(box(exterior_board="MEL", door_edge="2mm SOLID"))
    check("a white door is grain 0 — grain was never a property of being a door",
          sorted({x.grain for x in plain if x.code[:2] in EXTERIOR_CODES}), [0])
    brook_job = Job(name="g", cabinets=[box(carcass_board="BROOKHILL")])
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
          box(carcass_board="BROOKHILL").drawer_box_tape(MATERIALS), "PVC WOOD")

    print("\na board with nothing to generate from is named, never guessed at")
    nameless = {"MEL": {"name": "", "tape": "", "thickness": 16, "grain": "plain"},
                "BROOKHILL": dict(MATERIALS["BROOKHILL"])}
    naked = Job(name="n", boards=["MEL", "BROOKHILL"],
                cabinets=[box(exterior_board="MEL")], materials=nameless)
    msgs = [i.message for i in validate(naked, generate_job(naked))
            if "no name to build edging from" in i.message]
    check("the warning names the board and the field", len(msgs) >= 1, True)
    check("and no tape name is invented in its place",
          by_code(generate_cabinet(box(exterior_board="MEL"), S, nameless))["07"].edge_material,
          "")
    check("an override silences it, because the cabinet was told what to use",
          [i.message for i in validate(
              Job(name="n3", boards=["MEL", "BROOKHILL"], materials=nameless,
                  cabinets=[box(exterior_board="MEL", door_edge="2mm SOLID")]), [])
           if "no name to build edging from" in i.message and "door_edge" in i.message],
          [])

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
    # Test.json is a working file — it is opened, edited and saved in the app
    # (re-saved under BROOKHILL with GREY cabinets, 18 Sept 2026), so nothing
    # pins its contents. Test_Build.json is the untouched pre-library DECOR job.
    for name, want in (("Test_Build.json", 27),):
        j = load(os.path.join(ROOT, "jobs", name))
        check(f"{name} generates the same number of panel lines",
              len(generate_job(j)), want)
        check(f"  and its tapes are unchanged",
              sorted({x.edge_material for x in generate_job(j) if x.edge_material}),
              ["2mm WOOD", "PVC WHITE", "PVC WOOD"])

    print("\nDECOR is BROOKHILL's former id, and still resolves (18 Sept 2026)")
    check("the only alias is the one rename", BOARD_ALIASES, {"DECOR": "BROOKHILL"})
    check("a new cabinet's exterior board is BROOKHILL",
          Cabinet(1, 600, 720, 580).exterior_board, "BROOKHILL")
    check("and the house records name BROOKHILL, not DECOR", sorted(MATERIALS),
          ["BACK", "BROOKHILL", "MEL"])
    check("an id the job carries resolves to itself",
          resolve_board({"DECOR": {}, "BROOKHILL": {}}, "DECOR"), "DECOR")
    check("a former id resolves to the current one the job carries",
          resolve_board(MATERIALS, "DECOR"), "BROOKHILL")
    check("and the current id to the former one an older job was quoted under",
          resolve_board({"DECOR": "BROOKHILL FUSION CHIP"}, "BROOKHILL"), "DECOR")
    check("DECOR prices, grains and tapes as the board it is",
          (material_board(MATERIALS, "DECOR"), grain_of(MATERIALS, "DECOR"),
           tape_for(MATERIALS, "DECOR", "2mm")), ("BROOKHILL FUSION CHIP", 1, "2mm WOOD"))
    wood = sorted({p.material for p in generate_job(JOB)} - {"MEL", "BACK"})
    check("the October job's literal DECOR panels and its template doors are one board",
          wood, ["BROOKHILL"])
    check("and generating it moved nothing in the job: its bespoke panels still say DECOR",
          sorted({p.material for c in JOB.cabinets for p in c.bespoke} - {"MEL", "BACK"}),
          ["DECOR"])
    t = load(os.path.join(ROOT, "jobs", "Test_Build.json"))
    t.cabinets.append(Cabinet(99, 600, 720, 580, kind="base", doors=1))
    check("a new cabinet in a job quoted under DECOR is cut from that job's DECOR",
          sorted({p.material for p in generate_job(t)
                  if p.cabinet == 99 and p.code[:2] == "07"}), ["DECOR"])
    mixed = Job(name="m", cabinets=[Cabinet(1, 600, 720, 580, kind="base", doors=1,
                                            door_boards=["DECOR"])])
    check("a leaf naming DECOR beside the BROOKHILL exterior is one line, not 107a / 107b",
          [(p.code, p.qty) for p in generate_job(mixed) if p.code[:2] == "07"], [("07", 1)])
    loose = Job(name="l", loose=[Panel(0, "08", "Filler", "DECOR", 500, 50, 1, grain=1)])
    check("a loose DECOR panel reaches the cut list as BROOKHILL",
          [p.material for p in generate_job(loose)], ["BROOKHILL"])
    check("without the job's own panel being touched", loose.loose[0].material, "DECOR")

    print("\neach drawer names its own box and face board (18 Sept 2026)")
    three = [Drawer(200, 150), Drawer(200, 150), Drawer(300, 150)]
    plain = Cabinet(1, 600, 720, 560, kind="base", back="none", drawers=three)
    lines = lambda cab, code: sorted((p.code, p.material, p.length, p.width, p.qty)  # noqa: E731
                                     for p in generate_cabinet(cab, S, MATERIALS)
                                     if p.code[:2] == code)
    check("with none named, every box follows the carcass and every face the exterior",
          ({x[1] for x in lines(plain, "18")}, {x[1] for x in lines(plain, "20")}),
          ({"MEL"}, {"BROOKHILL"}))
    odd = Cabinet(1, 600, 720, 560, kind="base", back="none",
                  drawers=[Drawer(200, 150), Drawer(200, 150, box_board="BROOKHILL",
                                                    face_board="MEL"),
                           Drawer(300, 150)])
    check("one drawer's box in another board is its own line, the rest stay together",
          [(x[1], x[4]) for x in lines(odd, "18")], [("MEL", 4), ("BROOKHILL", 2)])
    check("and told apart by designation, not by a rename",
          sorted(x[0] for x in lines(odd, "18")), ["18a", "18b"])
    check("its face likewise, while the same-size face beside it keeps the exterior",
          [(x[1], x[2], x[4]) for x in lines(odd, "20")],
          [("BROOKHILL", 200, 1), ("MEL", 200, 1), ("BROOKHILL", 300, 1)])
    check("the box's PVC follows that drawer's box board",
          sorted({p.edge_material for p in generate_cabinet(odd, S, MATERIALS)
                  if p.code[:2] == "18"}), ["PVC WHITE", "PVC WOOD"])
    check("nothing else on the cabinet moves",
          lines(odd, "01") == lines(plain, "01") and lines(odd, "07") == lines(plain, "07"),
          True)
    check("and the panel count is the same — only boards change",
          sum(p.qty for p in generate_cabinet(odd, S, MATERIALS)),
          sum(p.qty for p in generate_cabinet(plain, S, MATERIALS)))
    back = cabinet_from_dict(cabinet_to_dict(odd))
    check("a drawer's boards round-trip through the job file",
          [(d.box_board, d.face_board) for d in back.drawers],
          [(None, None), ("BROOKHILL", "MEL"), (None, None)])
    grey = {"MEL": dict(MATERIALS["MEL"]),
            "GREY": {"name": "Grey", "tape": "Grey", "thickness": 16, "grain": "plain"}}
    gcab = Cabinet(1, 600, 720, 560, kind="base", carcass_board="GREY",
                   exterior_board="GREY",
                   support_rows=[Support("white", 3), Support("front", 1)])
    check("a white-edged support is edged white on a grey carcass, not PVC Grey",
          [(p.qty, p.edge_material) for p in generate_cabinet(gcab, S, grey)
           if p.code[:2] == "04"], [(3, "PVC WHITE"), (1, "PVC Grey")])
    check("and the editor is told the same name the cut list carries",
          {e: gcab.support_tape(grey, e) for e in ("none", "front", "white")},
          {"none": "", "front": "PVC Grey", "white": "PVC WHITE"})
    from app.api import rename_board_in_job                           # noqa: E402
    rj = Job(name="r", cabinets=[cabinet_from_dict(cabinet_to_dict(odd))])
    rename_board_in_job(rj, "BROOKHILL", "BRK2")
    check("renaming a board moves a drawer that names it",
          (rj.cabinets[0].drawers[1].box_board, rj.cabinets[0].drawers[1].face_board),
          ("BRK2", "MEL"))

    print(f"\n{'ALL OK' if not FAILS else str(len(FAILS)) + ' FAILED: ' + str(FAILS)}")
    return 1 if FAILS else 0


if __name__ == "__main__":
    raise SystemExit(main())
