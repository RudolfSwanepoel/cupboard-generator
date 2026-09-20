"""One source for "which fields hold a board".

    python tools/check_single_source.py

Four hand-written lists used to answer this question and they disagreed:

  * `api.board_swap` moved only the carcass and the exterior board, so swapping
    a board left a door leaf, a back, a drawer face or an edging colour pointing
    at the board the project was about to stop carrying;
  * `api.board_select` with `off` refused only on the carcass, the exterior and
    the drawer boards, so a board used *only* as an edging colour could be taken
    out of a project while a cabinet still named it;
  * `boards.scan_jobs` missed the back, the door leaves and the edging boards,
    so a board a saved job really used could show as unused — and be deleted
    from the library out from under it;
  * `validate._boards_and_tapes` had its own list again.

Now `Cabinet._board_slots` is the list, `board_refs` / `map_board_refs` read it,
and everything above goes through those. This check is the guard: **by
reflection**, every `str` field on `Cabinet` whose name ends in `_board`, every
entry of `door_boards`, every drawer's board fields and every support row's
board are set to a sentinel, and each one must come back from `board_refs()`.
A board field added to the dataclass and not to `_board_slots` fails here rather
than becoming the fifth list that disagrees.

`boards.cabinet_board_ids` is the one deliberate repeat — it reads raw JSON,
because a job file that will not parse has to be reported by name rather than
skipped — so it is held against the dataclass here too.
"""
import os
import sys
from dataclasses import fields

ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, ROOT)

from cabinetgen import boards as B                                            # noqa: E402
from cabinetgen.export_plaza import (RATES, YIELD, board_yield,              # noqa: E402
                                     cut_rate, effective_price)
from cabinetgen.model import (Cabinet, Drawer, Job, Panel, PanelSpec,         # noqa: E402
                              Support)
from cabinetgen.store import cabinet_to_dict                                  # noqa: E402

NL = chr(10)
FAILS = []


def check(name, got, want):
    ok = got == want
    print(f"  {'ok   ' if ok else 'FAIL '} {name}: {got}" + ("" if ok else f"  want {want}"))
    if not ok:
        FAILS.append(name)


def loaded_cabinet():
    """A cabinet with every board-holding slot filled with its own sentinel."""
    cab = Cabinet(number=1, width=600, height=720, depth=580)
    seen = {}
    for f in fields(Cabinet):
        if f.type in ("str", "Optional[str]") or f.name.endswith("_board"):
            if not f.name.endswith("_board"):
                continue
            token = "SENT_" + f.name.upper()
            setattr(cab, f.name, token)
            seen[token] = f.name
    cab.door_boards = ["SENT_DOOR0", "SENT_DOOR1"]
    seen["SENT_DOOR0"] = "door_boards[0]"
    seen["SENT_DOOR1"] = "door_boards[1]"
    cab.drawers = [Drawer(face_height=150, box_height=120,
                          box_board="SENT_DBOX", face_board="SENT_DFACE")]
    seen["SENT_DBOX"] = "drawers[0].box_board"
    seen["SENT_DFACE"] = "drawers[0].face_board"
    cab.support_rows = [Support(edge="none", qty=1, board="SENT_SUPROW", kind="pvc")]
    seen["SENT_SUPROW"] = "support_rows[0].board"
    cab.bespoke = [Panel(cabinet=1, code="01", role="Side", material="SENT_BESPOKE",
                         length=100, width=100)]
    seen["SENT_BESPOKE"] = "bespoke[0].material"
    # A panel names two boards of its own, and by reflection again: a board
    # field added to PanelSpec and not to _board_slots fails here too.
    cab.panel = PanelSpec()
    for f in fields(PanelSpec):
        if f.name == "board" or f.name.endswith("_board"):
            token = "SENT_PANEL_" + f.name.upper()
            setattr(cab.panel, f.name, token)
            seen[token] = "panel." + f.name
    return cab, seen


def main():
    print(__doc__.strip().splitlines()[0])

    cab, seen = loaded_cabinet()

    print("\nevery board field on the dataclass is found by reflection")
    check("the PanelSpec board fields",
          sorted(f.name for f in fields(PanelSpec)
                 if f.name == "board" or f.name.endswith("_board")),
          ["board", "edge_board"])
    declared = sorted(f.name for f in fields(Cabinet) if f.name.endswith("_board"))
    check("the _board fields", declared,
          ["back_board", "carcass_board", "door_edge_board", "drawer_carcass_board",
           "drawer_edge_board", "drawer_face_board", "exterior_board"])

    print("\nand every one of them comes back from board_refs()")
    reported = {key for key, _ in cab.board_refs()}
    missing = sorted(what for token, what in seen.items() if token not in reported)
    check("nothing is missed", missing, [])

    print("\nevery slot has a label a message can name out loud")
    labels = {key: label for key, label in cab.board_refs()}
    check("door leaf 2 is named as such", labels.get("SENT_DOOR1"), "door leaf 2 board")
    check("drawer 1's face is named", labels.get("SENT_DFACE"), "drawer 1 face board")
    check("the support row's board is named", labels.get("SENT_SUPROW"),
          "support row 1 edging board")
    check("the panel's own board is named", labels.get("SENT_PANEL_BOARD"),
          "panel board")
    check("and the board its edging colour comes from",
          labels.get("SENT_PANEL_EDGE_BOARD"), "panel edging board")
    check("no label is blank", sorted({bool(v) for v in labels.values()}), [True])

    print("\na blank slot is 'follow Structure', not a name")
    plain = Cabinet(number=2, width=600, height=720, depth=580,
                    carcass_board="MEL", exterior_board="BRK", back_board="")
    check("only what is actually named", sorted(k for k, _ in plain.board_refs()),
          ["BRK", "MEL"])

    print("\nmap_board_refs rewrites every one of them, and says which moved")
    cab2, seen2 = loaded_cabinet()
    moved = cab2.map_board_refs(lambda b: "NEW" if b in seen2 else b)
    check("as many labels as slots", len(moved), len(seen2))
    check("and nothing is left behind",
          sorted({k for k, _ in cab2.board_refs()}), ["NEW"])

    print("\nthe raw-JSON scan sees the same board ids as the dataclass")
    d = cabinet_to_dict(cab)
    check("scan and dataclass agree",
          sorted(B.cabinet_board_ids(d)), sorted({k for k, _ in cab.board_refs()}))

    print("\nand it still reads the pre-library 'decor' field")
    check("decor is an exterior board", sorted(B.cabinet_board_ids({"decor": "DECOR"})),
          ["DECOR"])
    check("a cabinet that is not a dict is not a crash",
          B.cabinet_board_ids("nonsense"), set())

    # --- no hardcoded board id decides what a board costs -------------------
    #
    # `export_plaza.YIELD` and `RATES` still pin the three original ids to their
    # measured figures, which is what holds the October benchmark. Everything
    # else falls through on grain and thickness. A board added in the Boards tab
    # has an id nobody pinned, and the failure this guards against is silent: a
    # cutting charge of R0 and a house-average yield, on a total that still
    # looks like a number.
    print(NL + "a board nobody pinned still gets a real yield, cut rate and price")
    fresh = B.Board(id="NEWBOARD", name="A BOARD ADDED TODAY", tape="NEW",
                    thickness=16, grain="plain", price=1234.0)
    job = Job(name="y", boards=["NEWBOARD"],
              materials={"NEWBOARD": B.to_material(fresh)})
    check("its id is in none of the pinned tables",
          "NEWBOARD" in YIELD or "NEWBOARD" in RATES["cut"], False)
    check("yield comes off grain and thickness", board_yield(job, "NEWBOARD") > 0, True)
    check("and matches the plain 16 mm figure", board_yield(job, "NEWBOARD"), 0.89)
    check("the cut rate is not R0", cut_rate(job, "NEWBOARD") > 0, True)
    check("and the price is the one the job captured",
          effective_price(job, "NEWBOARD"), 1234.0)

    grained = B.Board(id="NEWGRAIN", name="A GRAINED BOARD", tape="G",
                      thickness=16, grain="grain", price=999.0)
    thin = B.Board(id="NEWTHIN", name="A THIN BOARD", tape="T",
                   thickness=3, grain="plain", price=310.0)
    job2 = Job(name="y2", boards=["NEWGRAIN", "NEWTHIN"],
               materials={"NEWGRAIN": B.to_material(grained),
                          "NEWTHIN": B.to_material(thin)})
    check("a grained board yields the grained figure",
          board_yield(job2, "NEWGRAIN"), 0.78)
    check("a 3 mm board yields the thin figure", board_yield(job2, "NEWTHIN"), 0.80)
    check("and the masonite saw rate is not the beam saw's",
          cut_rate(job2, "NEWTHIN") != cut_rate(job2, "NEWGRAIN"), True)

    print()
    if FAILS:
        print(f"{len(FAILS)} FAILED: " + ", ".join(FAILS))
        return 1
    print("ALL OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
