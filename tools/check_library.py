"""The board library: selection, generated tapes, captured prices, thickness.

    python tools/check_library.py

What is pinned here, and why:

  * **The library is a library, not a job.** `boards.json` is in the repo so both
    machines see the same boards. A project *selects* from it, and selecting
    copies the record into the job. Editing a board afterwards changes what the
    next job is quoted at and never what an existing one was — which is the whole
    of Part 5, and the reason the October job reopens at R28,363.50 for good.
  * **A project picks its boards before anything is cut.** No boards and a
    cabinet is a critical that names what is missing. Over five is a warning and
    never a block: it is a guideline about cost and complexity.
  * **Tape names are generated from one token per board**, for all three
    thicknesses. The token is its own field rather than the board's name because
    Plazaboard's Brookhill tape is "PVC WOOD" — "PVC BROOKHILL FUSION CHIP" is
    not a thing they sell, and ordering it is D6/W10 in the other direction.
  * **Exterior tape thickness is per cabinet and has no dimensional effect.** We
    supply finished sizes and Plazaboard deducts the tape, so 1 mm and 2 mm cut
    identically and differ only in what is ordered and what it costs.
  * **Grain is the board's Grain / Plain**, and a grain board locks every panel
    cut from it.
  * **16 mm is assumed throughout.** A board of another thickness is named in a
    warning rather than quietly cut to the wrong size; thickness-driven geometry
    is deferred and deliberately not built.
  * **A job that will not parse is listed, never skipped** — a board reported as
    unused is how one gets edited out from under a real job.
"""
import copy
import json
import os
import sys
import tempfile

ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, ROOT)

from app.api import board_swap                                               # noqa: E402
from cabinetgen import boards as B                                            # noqa: E402
from cabinetgen import nest as N                                             # noqa: E402
from cabinetgen.engine import generate_cabinet, generate_job                  # noqa: E402
from cabinetgen.export_plaza import estimate_cost, summarise                  # noqa: E402
from cabinetgen.model import Cabinet, Drawer, Job, grain_of, tape_for         # noqa: E402
from cabinetgen.standard import STANDARD as S                                 # noqa: E402
from cabinetgen.store import job_from_dict, job_to_dict, load                 # noqa: E402
from cabinetgen.validate import BOARD_GUIDELINE, blocking, validate           # noqa: E402
from jobs.wardrobe_oct2025 import JOB                                         # noqa: E402

FAILS = []


def check(name, got, want):
    ok = got == want
    print(f"  {'ok   ' if ok else 'FAIL '} {name}: {got}" + ("" if ok else f"  want {want}"))
    if not ok:
        FAILS.append(name)


def box(**kw):
    kw.setdefault("doors", 1)
    kw.setdefault("number", 1)
    return Cabinet(width=600, height=2000, depth=500, **kw)


def costed(job):
    ps = generate_job(job)
    return estimate_cost(job, summarise(job, ps, N.nest_job(N.nestable(ps, job.std),
                                                            job.std)))["total_incl_vat"]


def main() -> int:                                                  # noqa: C901
    print("the library is a file in the repo, shared by both machines")
    lib = B.load()
    check("boards.json sits beside the code", os.path.basename(B.LIBRARY), "boards.json")
    check("and it is in the repo root, not inside a job",
          os.path.dirname(B.LIBRARY) == os.path.abspath(ROOT), True)
    check("the October job's three boards are in it, as they were",
          [(b.id, b.name, b.thickness, b.grain, b.price) for b in lib],
          [("MEL", "SUPER WHITE MELAMINE CHIP 9X6X16MM", 16, "plain", 575.0),
           ("DECOR", "BROOKHILL FUSION CHIP", 16, "grain", 999.0),
           ("BACK", "IMPORTED WHITE DECOR 9X6X3MM", 3, "plain", 310.0)])

    print("\ntape names are generated from one token per board")
    brook = B.find(lib, "DECOR")
    check("three thicknesses, one token",
          [brook.tape_name(k) for k in B.TAPE_KINDS],
          ["PVC WOOD", "1mm WOOD", "2mm WOOD"])
    check("the token is not the name — the tape Plazaboard sell is PVC WOOD",
          (brook.token, brook.name), ("WOOD", "BROOKHILL FUSION CHIP"))
    check("a board with no token falls back to its name",
          B.Board(id="X", name="OAK").tape_name("pvc"), "PVC OAK")
    check("and one with neither generates nothing at all",
          B.Board(id="X").tape_name("pvc"), "")

    print("\nselecting a board copies its record into the job")
    j = Job(name="sel", boards=[], materials={})
    j.materials["DECOR"] = B.to_material(brook)
    j.boards = ["DECOR"]
    check("the job now carries the name, token, thickness, grain and price",
          {k: j.materials["DECOR"][k] for k in ("name", "tape", "thickness",
                                                "grain", "price")},
          {"name": "BROOKHILL FUSION CHIP", "tape": "WOOD", "thickness": 16,
           "grain": "grain", "price": 999.0})
    check("and generates its tapes from that copy",
          tape_for(j.materials, "DECOR", "2mm"), "2mm WOOD")

    print("\nprice capture: editing the library never moves a quoted job")
    before = costed(JOB)
    check("the October job costs what it was quoted", before, 28363.50)
    raised = copy.deepcopy(lib)
    B.find(raised, "DECOR").price = 1500.0
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "boards.json")
        B.save(raised, path)
        check("a board's price can be raised in the library",
              B.find(B.load(path), "DECOR").price, 1500.0)
    check("and the October job still costs what it was quoted", costed(JOB), 28363.50)
    fresh = copy.deepcopy(JOB)
    fresh.materials = {k: dict(v) for k, v in JOB.materials.items()}
    fresh.materials["DECOR"] = B.to_material(B.find(raised, "DECOR"))
    check("a job that selects the new price is priced at it",
          costed(fresh) > 28363.50, True)
    check("by exactly the nine Brookhill boards it buys",
          round(costed(fresh) - 28363.50, 2), round(9 * (1500.0 - 999.0), 2))

    print("\na project picks its boards before anything is cut from them")
    none_yet = Job(name="empty", boards=[], materials={}, cabinets=[box()])
    msgs = [i for i in validate(none_yet, []) if "no boards selected" in i.message]
    check("a cabinet with no board selected is a critical",
          [(i.level, i.message) for i in msgs],
          [("critical", "no boards selected — pick at least one board from the "
                        "library before adding cabinets; a cabinet has to be cut "
                        "from something")])
    check("so the job does not export", blocking(validate(none_yet, [])), True)
    check("a project with no cabinets yet is not nagged",
          [i for i in validate(Job(name="e", boards=[], materials={}), [])
           if "no boards selected" in i.message], [])

    print("\nover five boards is a guideline, not a limit")
    many = copy.deepcopy(JOB)
    many.boards = list(JOB.materials) + ["B4", "B5", "B6"]
    for extra in ("B4", "B5", "B6"):
        many.materials[extra] = B.to_material(B.Board(id=extra, name=extra, tape=extra))
    over = [i for i in validate(many, []) if "over the" in i.message]
    check("six boards says so", len(over), 1)
    check("as a warning", [i.level for i in over], ["warning"])
    check("and the guideline is five", BOARD_GUIDELINE, 5)
    check("three boards says nothing",
          [i for i in validate(JOB, []) if "over the" in i.message], [])

    print("\nexterior tape thickness is per cabinet, and changes no size")
    two = generate_cabinet(box(exterior_tape="2mm"), S, JOB.materials)
    one = generate_cabinet(box(exterior_tape="1mm"), S, JOB.materials)
    d2 = next(p for p in two if p.role == "Door")
    d1 = next(p for p in one if p.role == "Door")
    check("2 mm orders the 2 mm tape", d2.edge_material, "2mm WOOD")
    check("1 mm orders the 1 mm tape", d1.edge_material, "1mm WOOD")
    check("and the door is cut to exactly the same size either way",
          (d1.length, d1.width), (d2.length, d2.width))
    check("the carcass tape is the thin PVC whichever is chosen, not selectable",
          [next(p for p in c if p.role == "Side").edge_material for c in (one, two)],
          ["PVC WOOD", "PVC WOOD"])
    check("the whole panel list is size-identical",
          [(p.code, p.length, p.width, p.qty) for p in one],
          [(p.code, p.length, p.width, p.qty) for p in two])

    print("\ngrain is the board's Grain / Plain")
    check("the library says which", (B.find(lib, "DECOR").grain, B.find(lib, "MEL").grain),
          ("grain", "plain"))
    check("and the job reads it the same way",
          (grain_of(JOB.materials, "DECOR"), grain_of(JOB.materials, "MEL")), (1, 0))
    check("a grain board locks every panel cut from it",
          sorted({p.grain for p in generate_cabinet(box(carcass_board="DECOR"), S,
                                                    JOB.materials)
                  if p.material == "DECOR"}), [1])
    check("an int is still read, which is the shape before the library",
          grain_of({"X": {"name": "x", "tape": "x", "grain": 1}}, "X"), 1)

    print("\n16 mm is assumed throughout, so another thickness is named")
    thick = copy.deepcopy(JOB)
    thick.materials["MEL"] = dict(thick.materials["MEL"], thickness=25)
    msgs = [i.message for i in validate(thick, []) if "25 mm" in i.message]
    check("every cabinet cut from it is named", len(msgs), 17)
    check("and it says what is 16 mm arithmetic",
          all("internal width" in m and "plinth butt" in m for m in msgs), True)
    check("as a warning — thickness-driven geometry is deferred, not broken",
          sorted({i.level for i in validate(thick, []) if "25 mm" in i.message}),
          ["warning"])
    check("16 mm says nothing", [i for i in validate(JOB, []) if "25 mm" in i.message], [])
    check("nor does the 3 mm backing board, which is never a carcass",
          [i for i in validate(JOB, []) if "3 mm, but every size" in i.message], [])

    print("\nthe back board is chosen, not reached for")
    three = generate_cabinet(Cabinet(number=1, width=600, height=720, depth=500,
                                     carcass_board="MEL", exterior_board="DECOR",
                                     back_board="BACK", back="four",
                                     drawers=[Drawer(200, 150, "board")]),
                             S, JOB.materials)
    check("the backing panel takes it",
          [x.material for x in three if x.code[:2] == "06"], ["BACK"])
    check("and so does a drawer base grooved out of the same sheet",
          [x.material for x in three if x.code[:2] == "17"], ["BACK"])
    swapped = generate_cabinet(Cabinet(number=1, width=600, height=720, depth=500,
                                       carcass_board="MEL", exterior_board="DECOR",
                                       back_board="DECOR", back="four", doors=1,
                                       drawers=[Drawer(200, 150, "board")]),
                               S, JOB.materials)
    check("changing it moves both, and nothing else",
          [(x.code[:2], x.material) for x in swapped
           if x.code[:2] in ("01", "06", "07", "17", "18")],
          [("01", "MEL"), ("06", "DECOR"), ("18", "MEL"), ("17", "DECOR"),
           ("07", "DECOR")])
    check("a housed 16 mm base is the drawer box's board, not the back's",
          [x.material for x in generate_cabinet(
              Cabinet(number=1, width=600, height=790, depth=570, back="none",
                      back_board="DECOR", drawers=[Drawer(200, 150, "melamine")]),
              S, JOB.materials) if x.code[:2] == "17"], ["MEL"])

    print("\nand a project that has not selected one is told which cabinet")
    only_mel = Job(name="b", boards=["MEL"],
                   materials={"MEL": dict(JOB.materials["MEL"])},
                   cabinets=[Cabinet(number=1, width=600, height=720, depth=500,
                                     carcass_board="MEL", exterior_board="MEL",
                                     back_board="BACK", back="four")])
    msgs = [(i.level, i.where, i.message) for i in validate(only_mel, [])
            if "back board" in i.message]
    check("named on the cabinet, with what the project does have",
          msgs, [("critical", "1",
                  "back board 'BACK' is not one of the job's boards (MEL)")])
    check("and the export is blocked",
          blocking(validate(only_mel, generate_job(only_mel))), True)
    no_back = copy.deepcopy(only_mel)
    no_back.cabinets[0].back = "none"
    check("a cabinet with no back is not asked for a back board",
          [i for i in validate(no_back, generate_job(no_back))
           if "back board" in i.message], [])
    grooved = copy.deepcopy(no_back)
    grooved.cabinets[0].drawers = [Drawer(200, 150, "board")]
    grooved.cabinets[0].depth = 570
    check("but one with a grooved drawer base is",
          [i.level for i in validate(grooved, [])if "back board" in i.message],
          ["critical"])
    check("the cabinet knows which it is",
          (Cabinet(number=1, width=600, height=720, depth=500,
                   back="none").needs_back_board,
           Cabinet(number=1, width=600, height=720, depth=500,
                   back="four").needs_back_board), (False, True))

    print("\nevery job written before it names the board it was already using")
    check("the default is the board the engine always reached for",
          Cabinet(number=1, width=600, height=720, depth=500).back_board, "BACK")
    check("so a job file with no back_board migrates to it",
          job_from_dict({"name": "x", "cabinets": [
              {"number": 1, "width": 600, "height": 720, "depth": 500}
          ]}).cabinets[0].back_board, "BACK")
    for name in ("Test.json", "Test_Build.json"):
        j = load(os.path.join(ROOT, "jobs", name))
        check(f"{name} migrates every cabinet",
              sorted({c.back_board for c in j.cabinets}), ["BACK"])
        backs = [(x.label, x.material) for x in generate_job(j) if x.code[:2] == "06"]
        check(f"  and every back it cuts is still off that board",
              (len(backs) > 0, sorted({m for _, m in backs})), (True, ["BACK"]))
    check("the October job too",
          sorted({c.back_board for c in JOB.cabinets}), ["BACK"])
    check("and it round-trips through a job file",
          job_from_dict(job_to_dict(JOB)).cabinets[0].back_board, "BACK")

    print("\na board on the cut list that the project never priced is named")
    partial = Job(name="p", boards=["MEL"],
                  materials={"MEL": dict(JOB.materials["MEL"])},
                  cabinets=[Cabinet(number=1, width=600, height=720, depth=500,
                                    carcass_board="MEL", exterior_board="MEL",
                                    back="four")])
    ps = generate_job(partial)
    check("the backing board is reached for by the engine, never selected",
          sorted({x.material for x in ps}), ["BACK", "MEL"])
    check("so it is a critical that names the board",
          [(i.level, i.where) for i in validate(partial, ps) if "R0" in i.message],
          [("critical", "BACK")])
    check("and the export is blocked rather than quoting a board at nothing",
          blocking(validate(partial, ps)), True)
    priced = copy.deepcopy(partial)
    priced.boards = ["MEL", "BACK"]
    priced.materials["BACK"] = B.to_material(B.find(lib, "BACK"))
    check("selecting it clears the critical",
          [i for i in validate(priced, generate_job(priced)) if "R0" in i.message], [])
    free = copy.deepcopy(priced)
    free.materials["BACK"] = dict(free.materials["BACK"], price=0.0,
                                  name="NO SUCH BOARD", board="NO SUCH BOARD")
    check("a selected board with no price at all is a warning, not a silent zero",
          [(i.level, i.where) for i in validate(free, generate_job(free))
           if "R0" in i.message], [("warning", "BACK")])
    check("the October job prices every board it cuts",
          [i for i in validate(JOB, generate_job(JOB)) if "R0" in i.message], [])

    print("\nwhich jobs use which board — and which would not open")
    usage = B.scan_jobs(os.path.join(ROOT, "jobs"))
    # a subset, not the whole folder: saving a job must not fail this check
    check("the real jobs are found",
          {"Test.json", "Test_Build.json"} <= set(usage.used_by.get("DECOR", [])), True)
    check("and nothing in the folder is unreadable today", usage.unreadable, [])
    with tempfile.TemporaryDirectory() as tmp:
        with open(os.path.join(tmp, "good.json"), "w", encoding="utf-8") as fh:
            json.dump({"name": "g", "boards": ["MEL"], "cabinets": []}, fh)
        with open(os.path.join(tmp, "broken.json"), "w", encoding="utf-8") as fh:
            fh.write("{ this is not json")
        u = B.scan_jobs(tmp)
        check("a good job is counted", u.used_by.get("MEL"), ["good.json"])
        check("a broken one is listed by name, not skipped",
              [x["job"] for x in u.unreadable], ["broken.json"])
        check("with the reason", "JSONDecodeError" in u.unreadable[0]["error"], True)

    print("\nswapping a project board shows the change before writing it")
    d = job_to_dict(JOB)
    pre = board_swap({"job": d, "from": "MEL", "to": "DECOR"})
    check("every cabinet cut from it is named, with which field",
          (len(pre["cabinets"]), pre["cabinets"][0]),
          (19, {"cabinet": 1, "fields": ["carcass_board"]}))
    check("and every panel whose board or tape moves",
          len(pre["panels"]), 101)
    check("two support lines sharing a designation are told apart by shape",
          [(x["label"], x["tape_from"], x["tape_to"])
           for x in pre["panels"] if x["label"] == "104"],
          [("104", "", ""), ("104", "PVC WOOD", "PVC WOOD")])
    check("the board count before and after is the engine's",
          (pre["before"]["boards"]["MEL"], pre["after"]["boards"]["MEL"]), (18, 4))
    check("and so is the cost",
          (pre["before"]["cost"], pre["after"]["cost"]), (28363.50, 35358.75))
    check("a preview writes nothing", "job" in pre, False)
    check("and leaves the job it was asked about alone",
          sorted({c["carcass_board"] for c in d["cabinets"]}), ["MEL"])
    done = board_swap({"job": d, "from": "MEL", "to": "DECOR", "apply": True})
    check("applying it moves every cabinet",
          sorted({c.carcass_board for c in job_from_dict(done["job"]).cabinets}),
          ["DECOR"])
    check("no designation changes — a panel keeps its name and changes its board",
          sorted({x["label"] for x in pre["panels"]}) ==
          sorted({x["label"] for x in pre["panels"]}), True)
    check("swapping to a board the project has not selected brings it in priced",
          job_from_dict(done["job"]).materials["DECOR"]["price"], 999.0)

    print("\nthe job file carries the selection, and reads back identically")
    rt = job_from_dict(job_to_dict(JOB))
    check("boards round-trip", rt.board_ids, JOB.board_ids)
    check("prices round-trip", costed(rt), 28363.50)
    check("a job written before the library still names its boards",
          load(os.path.join(ROOT, "jobs", "Test.json")).board_ids,
          ["BACK", "DECOR", "MEL"])

    print(f"\n{'ALL OK' if not FAILS else str(len(FAILS)) + ' FAILED: ' + str(FAILS)}")
    return 1 if FAILS else 0


if __name__ == "__main__":
    raise SystemExit(main())
