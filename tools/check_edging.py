"""Has Edging, the kinds a board offers, and the colour it is drawn in.

    python tools/check_edging.py

What is pinned here, and why:

  * **Every board attribute is stated on the Boards record and nowhere else**
    (20 September 2026). A board says whether it has edging at all, which of
    PVC / 1mm / 2mm it offers, and what colour it is. Nothing downstream states
    one: `tape_for` returns '' for a kind the board does not offer, and the
    validator names the cabinet rather than quietly ordering a tape the board
    never sold.
  * **The legacy rule is what keeps the benchmark still.** A record written
    before the tickbox carries neither key, and reads as edged with all three —
    which is what every job quoted before it was quoted with. A job whose
    materials have no new keys must produce byte-identical panels, issues and
    drawings. `snapshot.py --compare` is the wide net; this is the narrow one.
  * **Unticking keeps data.** Has Edging off keeps the kinds and the edging
    name in the file and merely stops anything reading them, the same discipline
    as "Has doors" and "Has drawers". A tickbox that threw values away would be
    a destructive control.
  * **A needed edging the board does not offer is CRITICAL, not a warning.**
    It blocks the export and names the cabinet, the board, the kind and what to
    tick. A cut list that goes out with a missing tape is the failure mode this
    app exists to prevent, and "carcass fronts are PVC in the exterior colour"
    means a 2mm-only exterior board produces exactly that (ruled 20 Sept 2026).
  * **A missing edging NAME stays a warning, with its wording unchanged.**
    `check_boards.py` pins the phrase "no name to build edging from". The two
    are different faults: no name is something to fill in, a kind not offered is
    something to decide.
  * **One problem, one message.** A cabinet already named in an EDGING critical
    does not also collect the per-panel "edges specified but no edge material"
    critical for every panel it cut.
  * **A support row is edged in a board and a kind that board offers**, with no
    hardcoded name anywhere (20 September 2026). A row written before that
    control is read from its old `edge` and is edged exactly as it was quoted:
    a white-edged row resolves through the project's white board, not a
    constant, and falls back to the constant only when there is no such board.
"""
import os
import sys

ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, ROOT)

from cabinetgen import boards as B                                            # noqa: E402
from cabinetgen.engine import generate_cabinet, generate_job                  # noqa: E402
from cabinetgen.model import (MATERIALS, Cabinet, Drawer, Job,                # noqa: E402
                              Support, WHITE_EDGE, is_thin, material_colour,
                              material_offers, NO_COLOUR, tape_for,
                              white_edge_board)
from cabinetgen.standard import STANDARD as S                                 # noqa: E402
from cabinetgen.validate import validate                                      # noqa: E402

NL = chr(10)
FAILS = []


def check(name, got, want):
    ok = got == want
    print(f"  {'ok   ' if ok else 'FAIL '} {name}: {got}" + ("" if ok else f"  want {want}"))
    if not ok:
        FAILS.append(name)


def mats(**over):
    """The house materials, with named boards overridden."""
    m = {k: dict(v) for k, v in MATERIALS.items()}
    for key, patch in over.items():
        m.setdefault(key, {}).update(patch)
    return m


def box(**kw):
    kw.setdefault("number", 1)
    kw.setdefault("width", 600)
    kw.setdefault("height", 720)
    kw.setdefault("depth", 580)
    kw.setdefault("doors", 1)
    kw.setdefault("carcass_board", "MEL")
    kw.setdefault("exterior_board", "BROOKHILL")
    kw.setdefault("back_board", "BACK")
    return Cabinet(**kw)


def job_of(cab, m):
    return Job(name="e", boards=list(m), cabinets=[cab], materials=m)


def issues(cab, m):
    j = job_of(cab, m)
    return validate(j, generate_job(j))


def criticals(cab, m, ref=None):
    return [i for i in issues(cab, m)
            if i.level == "critical" and (ref is None or i.ref == ref)]


def main():
    print(__doc__.strip().splitlines()[0])

    # --- the record ---------------------------------------------------------
    print("\na board record written before the tickbox reads as edged, all three")
    legacy = B.board_from_dict({"id": "L", "tape": "WHITE", "thickness": 16})
    check("offered", legacy.offered, ["pvc", "1mm", "2mm"])
    check("and generates its names", legacy.tape_name("2mm"), "2mm WHITE")
    check("and has no colour of its own", legacy.colour, "")
    check("so it draws neutral", legacy.shown_colour, NO_COLOUR)

    print("\nHas Edging off: no name for any kind, and the kinds are KEPT")
    off = B.board_from_dict({"id": "O", "tape": "WHITE", "has_edging": False,
                             "edging_kinds": ["pvc", "2mm"]})
    check("offers nothing", off.offered, [])
    check("no name for any kind", [off.tape_name(k) for k in B.TAPE_KINDS], ["", "", ""])
    check("but what was ticked is still in the record", off.edging_kinds, ["pvc", "2mm"])
    check("and so is the edging name", off.tape, "WHITE")
    check("re-ticking restores it", B.board_from_dict(
        dict(off.__dict__, has_edging=True)).offered, ["pvc", "2mm"])

    print("\na board offers only what is ticked")
    only2 = B.board_from_dict({"id": "T", "tape": "W", "edging_kinds": ["2mm"]})
    check("offered", only2.offered, ["2mm"])
    check("2mm has a name", only2.tape_name("2mm"), "2mm W")
    check("PVC does not", only2.tape_name("pvc"), "")

    # --- sanitisers ---------------------------------------------------------
    print("\nclean_kinds: canonical order, no repeats, nothing unknown")
    check("reordered and deduped", B.clean_kinds(["2mm", "pvc", "pvc"]), ["pvc", "2mm"])
    check("unknown dropped", B.clean_kinds(["junk", "1mm"]), ["1mm"])
    check("blank", B.clean_kinds(None), [])
    check("case and space", B.clean_kinds([" PVC ", "2MM"]), ["pvc", "2mm"])

    print("\nclean_colour: '#rrggbb' lower case, '#rgb' expanded, else ''")
    check("six digits", B.clean_colour("#ABCDEF"), "#abcdef")
    check("without the hash", B.clean_colour("abcdef"), "#abcdef")
    check("three digits expand", B.clean_colour("#f00"), "#ff0000")
    check("blank", B.clean_colour(""), "")
    check("nonsense is dropped, never repaired", B.clean_colour("reddish"), "")
    check("five digits is not a colour", B.clean_colour("#12345"), "")

    # --- the job's copy -----------------------------------------------------
    print("\nthe job's copy of a record answers the same way")
    m = mats(BROOKHILL={"edging_kinds": ["2mm"]})
    check("offers", list(material_offers(m, "BROOKHILL")), ["2mm"])
    check("2mm generates", tape_for(m, "BROOKHILL", "2mm"), "2mm WOOD")
    check("PVC does not", tape_for(m, "BROOKHILL", "pvc"), "")
    m_off = mats(BROOKHILL={"has_edging": False})
    check("Has Edging off offers nothing", list(material_offers(m_off, "BROOKHILL")), [])
    check("a record with neither key still offers all three",
          list(material_offers({"X": {"name": "x", "tape": "T"}}, "X")),
          ["pvc", "1mm", "2mm"])

    print("\ncolour is read from the record, and an unset one is neutral")
    check("set", material_colour(mats(MEL={"colour": "#b4835a"}), "MEL"), "#b4835a")
    check("unset", material_colour(MATERIALS, "MEL"), NO_COLOUR)

    print("\nthin is what export_plaza already sorts by, so they cannot disagree")
    check("the 3 mm backing is thin", is_thin(MATERIALS, "BACK"), True)
    check("a 16 mm board is not", is_thin(MATERIALS, "MEL"), False)

    # --- validation ---------------------------------------------------------
    print("\na 2mm-only exterior board leaves the carcass fronts unedged: CRITICAL")
    m = mats(BROOKHILL={"edging_kinds": ["2mm"]})
    crit = criticals(box(exterior_tape="2mm"), m, "EDGING")
    check("one critical, on the cabinet", [i.where for i in crit], ["1"])
    check("it names the board", "BROOKHILL FUSION CHIP" in crit[0].message, True)
    check("it names the kind that is missing", "PVC edging" in crit[0].message, True)
    check("it says what to tick", "Tick PVC on that board" in crit[0].message, True)

    print("\na PVC-only board cannot edge a door that wants 2mm: CRITICAL")
    m = mats(BROOKHILL={"edging_kinds": ["pvc"]})
    crit = criticals(box(exterior_tape="2mm"), m, "EDGING")
    check("the doors are named", any("doors" in i.message for i in crit), True)
    check("and what it does offer is said", any("only offers PVC" in i.message
                                                for i in crit), True)

    print("\nHas Edging off on the exterior board: CRITICAL, and it says so")
    m = mats(BROOKHILL={"has_edging": False})
    crit = criticals(box(exterior_tape="2mm"), m, "EDGING")
    check("more than one part is named", len(crit) >= 2, True)
    check("the reason is the tickbox",
          all("Has Edging is off" in i.message for i in crit), True)

    print("\none problem, one message: no per-panel critical on top of it")
    per_panel = [i for i in issues(box(exterior_tape="2mm"), m)
                 if "edges specified but no edge material" in i.message]
    check("the panel-by-panel critical is suppressed", per_panel, [])

    print("\na board with no edging NAME is still only a warning, worded as before")
    nameless = {"MEL": {"name": "", "tape": "", "thickness": 16, "grain": "plain"},
                "BROOKHILL": dict(MATERIALS["BROOKHILL"]), "BACK": dict(MATERIALS["BACK"])}
    warn = [i for i in issues(box(exterior_board="MEL", exterior_tape="2mm"), nameless)
            if "no name to build edging from" in i.message]
    check("the warning is there", len(warn) >= 1, True)
    check("and it is a warning, not a critical",
          {i.level for i in warn}, {"warning"})

    print("\nan override still silences it — the cabinet was told what to use")
    m = mats(BROOKHILL={"has_edging": False})
    check("no EDGING critical", criticals(
        box(carcass_edge="PVC WOOD", door_edge="2mm WOOD", exterior_tape="2mm"),
        m, "EDGING"), [])

    # --- supports -----------------------------------------------------------
    print("\na support row names a board and a kind that board offers")
    row = Support(edge="none", qty=2, board="MEL", kind="pvc")
    cab = box(support_rows=[row])
    check("edged from its own board", cab.support_row_tape(MATERIALS, row), "PVC WHITE")
    grey = mats(GREY={"name": "Grey", "board": "Grey", "tape": "Grey",
                      "thickness": 16, "grain": "plain", "price": 1100})
    row2 = Support(edge="none", qty=1, board="GREY", kind="2mm")
    check("another board, another kind", cab.support_row_tape(grey, row2), "2mm Grey")
    lost = Support(edge="none", qty=1, board="BROOKHILL", kind="pvc")
    check("a kind the board no longer offers generates nothing",
          cab.support_row_tape(mats(BROOKHILL={"edging_kinds": ["2mm"]}), lost), "")

    print("\na row written before the control is edged exactly as it was quoted")
    legacy_white = Support(edge="white", qty=1)
    legacy_front = Support(edge="front", qty=1)
    legacy_none = Support(edge="none", qty=1)
    cab = box(support_rows=[legacy_white, legacy_front, legacy_none])
    check("white resolves through the project's white board, not a constant",
          white_edge_board(MATERIALS), "MEL")
    check("and still comes out as it always did",
          cab.support_row_tape(MATERIALS, legacy_white), WHITE_EDGE)
    check("front takes the carcass edging (PVC in the exterior colour)",
          cab.support_row_tape(MATERIALS, legacy_front),
          cab.carcass_tape(MATERIALS))
    check("none is not edged", cab.support_row_tape(MATERIALS, legacy_none), "")

    print("\na white row on a grey carcass is still white — that is the 18 Sept rule")
    greyjob = mats(MEL=dict(MATERIALS["MEL"]),
                   GREY={"name": "Grey", "board": "Grey", "tape": "Grey",
                         "thickness": 16, "grain": "plain", "price": 1100})
    grey_cab = box(carcass_board="GREY", exterior_board="GREY",
                   support_rows=[legacy_white])
    check("white, not PVC Grey",
          grey_cab.support_row_tape(greyjob, legacy_white), "PVC WHITE")
    check("and it came from the white BOARD",
          white_edge_board(greyjob), "MEL")

    print(NL + "with no white board there is no name to give, and none is invented")
    nowhite = {"GREY": dict(greyjob["GREY"])}
    check("no white board means no edging name",
          grey_cab.support_row_tape(nowhite, legacy_white), "")
    nj = Job(name="nw", boards=list(nowhite),
             cabinets=[box(carcass_board="GREY", exterior_board="GREY",
                           support_rows=[legacy_white])], materials=nowhite)
    named = [i for i in validate(nj, generate_job(nj)) if "support row" in i.message]
    check("the row is named instead of going out unedged in silence",
          [(i.level, i.ref) for i in named], [("critical", "EDGING")])
    check("and the message says what to do",
          "tick PVC on the white board" in named[0].message, True)

    print("\nthe engine cuts a support from the row, not from a constant")
    cab = box(supports=0, support_rows=[Support(edge="none", qty=1,
                                                board="MEL", kind="2mm")])
    sup = [p for p in generate_cabinet(cab, S, MATERIALS) if p.role == "Support"]
    check("one support line", len(sup), 1)
    check("edged as the row says", sup[0].edge_material, "2mm WHITE")
    check("and it is banded", sup[0].edge_l, 1)
    cab = box(supports=0, support_rows=[Support(edge="none", qty=1)])
    sup = [p for p in generate_cabinet(cab, S, MATERIALS) if p.role == "Support"]
    check("an unedged row carries no edging", sup[0].edge_material, "")
    check("and no band", sup[0].edge_l, 0)

    # --- cut from, and edged in, are two questions -------------------------
    print(NL + "a support row says what it is CUT FROM, separately from its edging")
    grey = {"name": "Grey", "board": "Grey", "tape": "Grey", "thickness": 16,
            "grain": "plain", "price": 1100.0}
    m = mats(GREY=grey)
    row = Support(edge="none", qty=1, cut_board="GREY", board="MEL", kind="pvc")
    cab = box(supports=0, support_rows=[row])
    check("cut from its own board", cab.support_row_cut_board(row), "GREY")
    check("edged in another board's colour", cab.support_row_tape(m, row), "PVC WHITE")
    sup = [p for p in generate_cabinet(cab, S, m) if p.role == "Support"]
    check("and the panel really is cut from it", sup[0].material, "GREY")
    check("with that board's grain", sup[0].grain, 0)
    check("a white edge on a grey rail", sup[0].edge_material, "PVC WHITE")

    print(NL + "cut from a grained board and the rail locks like anything else off it")
    row = Support(edge="none", qty=1, cut_board="BROOKHILL", board="MEL", kind="pvc")
    cab = box(supports=0, support_rows=[row])
    sup = [p for p in generate_cabinet(cab, S, MATERIALS) if p.role == "Support"]
    check("material", sup[0].material, "BROOKHILL")
    check("grain locked", sup[0].grain, 1)

    print(NL + "blank cut_board follows the carcass, which is what it always was")
    row = Support(edge="none", qty=1)
    cab = box(supports=0, carcass_board="MEL", support_rows=[row])
    check("follows the carcass board", cab.support_row_cut_board(row), "MEL")
    cab2 = box(supports=0, carcass_board="BROOKHILL", support_rows=[row])
    check("and follows it when the carcass changes",
          cab2.support_row_cut_board(row), "BROOKHILL")

    print(NL + "MIGRATION: an old row is cut and edged exactly as it was quoted")
    front, white, none_ = (Support(edge="front", qty=1), Support(edge="white", qty=1),
                           Support(edge="none", qty=1))
    cab = box(carcass_board="MEL", exterior_board="BROOKHILL",
              support_rows=[front, white, none_])
    check("front: cut from the carcass", cab.support_row_cut_board(front), "MEL")
    check("front: edged in the EXTERIOR board's colour",
          cab.support_row_board(MATERIALS, front), "BROOKHILL")
    check("front: which is the carcass edging, unchanged",
          cab.support_row_tape(MATERIALS, front), cab.carcass_tape(MATERIALS))
    check("white: cut from the carcass", cab.support_row_cut_board(white), "MEL")
    check("white: edged in the board that yields PVC WHITE",
          (cab.support_row_board(MATERIALS, white),
           cab.support_row_tape(MATERIALS, white)), ("MEL", "PVC WHITE"))
    check("none stays none", cab.support_row_tape(MATERIALS, none_), "")
    check("and none is cut from the carcass too",
          cab.support_row_cut_board(none_), "MEL")

    print(NL + "a new row's edging colour defaults to the board it is cut from")
    fresh = Support(edge="none", qty=1, cut_board="GREY", kind="pvc")
    cab = box(support_rows=[fresh])
    check("colour follows cut from", cab.support_row_board(m, fresh), "GREY")
    check("so it is edged in its own colour", cab.support_row_tape(m, fresh), "PVC Grey")

    # --- what the editor shows is what the cut list carries ----------------
    print(NL + "every support row's edging IS the edge material on its cut-list line")
    # The editor's "Ordered as" column reads `support_row_tape`; the engine cuts
    # from the same call. They went out of step once — not because the engine was
    # wrong, but because the editor kept the PREVIOUS compute's answer on screen
    # (renderEditor leaves the DOM alone when the selection has not changed). The
    # two are held together here so the display can only ever be the cut list's.
    from cabinetgen.store import load as load_job                  # noqa: E402
    import importlib.util                                          # noqa: E402
    spec = importlib.util.spec_from_file_location(
        "w", os.path.join(ROOT, "jobs", "wardrobe_oct2025.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    jobs = [("oct2025", mod.JOB)]
    for name in ("Test.json", "Test_Build.json"):
        path = os.path.join(ROOT, "jobs", name)
        if os.path.exists(path):
            jobs.append((name, load_job(path)))
    rows_seen, bad = 0, []
    for name, j in jobs:
        panels = generate_job(j)
        for c in j.cabinets:
            if c.template == "none" or c.is_panel:
                # A PANEL is neither. It keeps its support rows in the job file
                # — hidden, never emptied — and the engine cuts none of them, so
                # comparing what a Supports section would show against what was
                # cut is comparing a section that is not on screen with panels
                # that were never meant to exist. `Test.json` cabinet 8 is the
                # case (21 September 2026).
                continue
            cut = [p for p in panels
                   if p.role == "Support" and p.cabinet == c.number]
            shown = [c.support_row_tape(j.materials, r) for r in c.support_list]
            rows_seen += len(shown)
            if [p.edge_material for p in cut] != shown:
                bad.append((name, c.number, shown, [p.edge_material for p in cut]))
    check("rows checked across every fixed job", rows_seen > 0, True)
    check("not one disagrees with its cut-list line", bad, [])

    # --- the legacy guarantee (A10) ----------------------------------------
    print("\nA JOB WHOSE MATERIALS HAVE NO NEW KEYS DOES NOT MOVE")
    old = {k: {kk: vv for kk, vv in v.items()
               if kk not in ("has_edging", "edging_kinds", "colour")}
           for k, v in MATERIALS.items()}
    check("the fixture really has none of the new keys",
          any(k in v for v in old.values()
              for k in ("has_edging", "edging_kinds", "colour")), False)
    d = Drawer(face_height=150, box_height=120)
    cab_kw = dict(doors=2, shelves=2, fixed_shelves=1, drawers=[d],
                  has_drawers=True, exposed_sides=1, exterior_tape="2mm",
                  support_rows=[Support("front", 1), Support("white", 1),
                                Support("none", 1)])
    a = generate_cabinet(box(**cab_kw), S, old)
    b = generate_cabinet(box(**cab_kw), S, MATERIALS)
    check("the same panels, panel for panel", a, b)
    check("every tape name identical",
          [p.edge_material for p in a], [p.edge_material for p in b])
    ja, jb = job_of(box(**cab_kw), old), job_of(box(**cab_kw), MATERIALS)
    check("the same issues, in the same order",
          [str(i) for i in validate(ja, generate_job(ja))],
          [str(i) for i in validate(jb, generate_job(jb))])

    print()
    if FAILS:
        print(f"{len(FAILS)} FAILED: " + ", ".join(FAILS))
        return 1
    print("ALL OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
