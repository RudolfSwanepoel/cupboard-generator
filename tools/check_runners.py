"""Runners: the catalogue, the legacy record, what a runner sizes, and the checks.

    python tools/check_runners.py

The drawers / runners / supports brief of 28 September 2026. Holds:

  * Part 2 — the runner catalogue. `hardware.json` holds the Gelmar record,
    and the built-in seed is as ruled (45 high, 13.5 a side, 12.7 rail,
    300-600, full, 35 kg, lift 5, setback 3) — the library's copy is a setting
    Rudolf edits, so its values are not pinned; a job saved before the
    catalogue names no runner and is cut on the built-in LEGACY record
    (350 / 450 / 500), so the October job and Test.json as it stood then —
    frozen as tools/fixtures/Test_drawers.json — cut exactly what they cut; the runner length is the longest on
    the record leaving runner_clearance behind; the box width is the opening
    less the clearance each side (Gelmar: 59 on the front, exactly the old
    deduct); selecting copies the record (price captured); the delete guard;
    a swap names the drawer lines that move; the job file round-trips;
  * Part 3 — the drawer setting: `room.drawer_layout`, the one place a box is
    placed, with the sketch's worked numbers;
  * Part 5 — the drawer checks, each with a stable id and worked numbers.

Repo root is the parent of tools/.
"""
import copy
import json
import os
import shutil
import sys
import tempfile

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, ROOT)
from fixture_jobs import job_file  # noqa: E402

from app import api                                                     # noqa: E402
from cabinetgen import hardware as H                                    # noqa: E402
from cabinetgen.engine import generate_job                              # noqa: E402
from cabinetgen.export_plaza import estimate_cost, summarise            # noqa: E402
from cabinetgen.model import MATERIALS, Cabinet, Drawer, Job, Support   # noqa: E402
from cabinetgen.standard import STANDARD                                # noqa: E402
from cabinetgen.store import job_from_dict, job_to_dict, load           # noqa: E402
from cabinetgen.validate import CRITICAL, validate                      # noqa: E402
from jobs.wardrobe_oct2025 import JOB as OCT                            # noqa: E402

FAILS = []


def check(name, got, want):
    ok = got == want
    print(f"  {'ok  ' if ok else 'FAIL'}  {name}: {got!r}" + ("" if ok else f"  (wanted {want!r})"))
    if not ok:
        FAILS.append(name)
    return ok


def box(**kw):
    kw.setdefault("number", 1)
    kw.setdefault("width", 600)
    kw.setdefault("height", 720)
    kw.setdefault("depth", 560)
    kw.setdefault("kind", "base")
    kw.setdefault("doors", 0)
    kw.setdefault("carcass_board", "MEL")
    kw.setdefault("exterior_board", "BROOKHILL")
    kw.setdefault("back_board", "BACK")
    kw.setdefault("drawers", [Drawer(face_height=240, box_height=150),
                              Drawer(face_height=240, box_height=150),
                              Drawer(face_height=233, box_height=150)])
    return Cabinet(**kw)


def job_of(*cabs, runners=None):
    return Job(name="r", boards=["MEL", "BROOKHILL", "BACK"], cabinets=list(cabs),
               materials={k: dict(v) for k, v in MATERIALS.items() if k in ("MEL", "BROOKHILL", "BACK")},
               runners=runners if runners is not None else {H.SEED_ID: H.to_record(H.SEED)})


def lines(job, roles=("Drawer Side", "Drawer Front", "Drawer Base")):
    return sorted((p.cabinet, p.label, p.role, p.length, p.width, p.qty)
                  for p in generate_job(job) if p.role in roles)


def issues(job, check_id, level=CRITICAL):
    return [i for i in validate(job, generate_job(job)) if i.check == check_id and i.level == level]


def catalogue():
    print("\nthe library: hardware.json and the Gelmar seed")
    lib = H.load()
    g = H.find(lib, H.SEED_ID)
    check("hardware.json carries the Gelmar seed", g is not None, True)
    # The SEED is what the brief ruled; the library's copy is a changeable
    # setting (Rudolf set its setback to 2, 28 September 2026), so the live
    # file is asked only that the record is there — never what it holds.
    s = H.SEED
    check("  the seed as ruled", (s.height, s.side_clearance, s.rail_thickness, s.lengths, s.extension,
                                  s.capacity_kg, s.lift, s.setback, s.type),
          (45, 13.5, 12.7, [300, 350, 400, 450, 500, 550, 600], "full", 35, 5, 3,
           "side-mount ball-bearing"))
    raw = json.load(open(H.LIBRARY, encoding="utf-8"))
    check("  in a `runners` list, room left beside it for hinges and handles", isinstance(raw.get("runners"), list), True)
    check("the legacy record is 350 / 450 / 500, 13.5 a side, 45 high, lift 5, setback 3",
          (H.LEGACY.lengths, H.LEGACY.side_clearance, H.LEGACY.height, H.LEGACY.lift, H.LEGACY.setback, H.LEGACY.id),
          ([350, 450, 500], 13.5, 45, 5, 3, ""))
    check("  and it is not in the library (never offered)", H.find(lib, ""), None)
    check("Standard keeps runner_clearance 40", STANDARD.runner_clearance, 40)
    check("  and no longer holds the lengths", hasattr(STANDARD, "runner_lengths"), False)

    tmp = tempfile.mkdtemp()
    try:
        path = os.path.join(tmp, "hardware.json")
        with open(path, "w", encoding="utf-8") as fh:
            json.dump({"version": 1, "runners": [], "hinges": [{"id": "H1"}]}, fh)
        H.save([H.SEED], path)
        back = json.load(open(path, encoding="utf-8"))
        check("save keeps a list it does not know (hinges, later)", back.get("hinges"), [{"id": "H1"}])
        check("  and writes the runners", [r["id"] for r in back["runners"]], [H.SEED_ID])
    finally:
        shutil.rmtree(tmp)

    print("\nthe length is picked over the record's list; no length is special")
    for depth, want in ((560, 500), (570, 500), (600, 550), (640, 600), (700, 600), (460, 400),
                        (440, 400), (439, 350), (340, 300), (339, None)):
        check(f"  Gelmar in {depth} deep", H.SEED.pick(depth, STANDARD.runner_clearance), want)
    for depth, want in ((560, 500), (460, 350), (539, 450), (389, None)):
        check(f"  legacy in {depth} deep", H.LEGACY.pick(depth, STANDARD.runner_clearance), want)
    check("Standard.pick_runner reads the list it is given", STANDARD.pick_runner(460, H.SEED.lengths), 400)
    check("travel: full extension is the length", H.SEED.travel(450), 450)
    check("  a three-quarter runner travels 3/4 of it", H.runner_from_dict({"id": "X", "extension": "0.75"}).travel(400), 300)


def legacy_holds():
    print("\na job saved before the catalogue cuts exactly what it cut (LEGACY)")
    check("the October job names no runner", {c.runner for c in OCT.cabinets}, {""})
    check("  and selects none", OCT.runners, {})
    P = generate_job(OCT)
    sides = sorted({p.length for p in P if p.role == "Drawer Side"})
    check("  its drawer sides are legacy lengths", all(n in (350, 450, 500) for n in sides), True)
    summary = summarise(OCT, P)
    check("  the benchmark total is R28,363.50", estimate_cost(OCT, summary)["total_incl_vat"], 28363.5)
    test = load(job_file("Test_drawers"))
    got = lines(test)
    check("Test_drawers.json cabinets 4 and 7 are on legacy", sorted(c.number for c in test.cabinets if c.drawer_list and not c.runner), [4, 7])
    check("  sides 500 (570 deep), fronts internal width - 59",
          sorted({(c, r, a, b) for c, _, r, a, b, _ in got if r in ("Drawer Side", "Drawer Front")}),
          sorted({(4, "Drawer Front", 400 - 32 - 59, b) for c, _, r, a, b, _ in got if c == 4 and r == "Drawer Front"} |
                 {(4, "Drawer Side", 500, b) for c, _, r, a, b, _ in got if c == 4 and r == "Drawer Side"} |
                 {(7, "Drawer Front", 350 - 32 - 59, b) for c, _, r, a, b, _ in got if c == 7 and r == "Drawer Front"} |
                 {(7, "Drawer Side", 500, b) for c, _, r, a, b, _ in got if c == 7 and r == "Drawer Side"}))
    raw = json.load(open(job_file("Test_drawers"), encoding="utf-8"))
    check("Test_drawers.json round-trips byte for byte (no runner, no runners key)",
          json.dumps(job_to_dict(job_from_dict(raw)), indent=2, ensure_ascii=False)
          == json.dumps(raw, indent=2, ensure_ascii=False), True)
    check("  it writes no `runners` key", "runners" in job_to_dict(test), False)

    print("\nthe width reads the record's clearance")
    j = job_of(box(runner=H.SEED_ID))
    front = [p for p in generate_job(j) if p.role == "Drawer Front"][0]
    check("Gelmar 13.5 a side: front = 600 - 32 - 59 = 509 (width does not move)", front.length, 509)
    check("  box outside width 541 = opening 568 - 27", STANDARD.drawer_box_width(600, 13.5), 541)
    narrow = dict(H.to_record(H.SEED), id="N", side_clearance=12.5)
    j = job_of(box(runner="N"), runners={"N": narrow})
    front = [p for p in generate_job(j) if p.role == "Drawer Front"][0]
    check("a 12.5 clearance: front 568 - 25 - 32 = 511", front.length, 511)
    base = [p for p in generate_job(j) if p.role == "Drawer Base"][0]
    check("  the grooved base follows it: 511 + 12 wide", base.width, 523)

    print("\nthe job's copy is what cuts, and it is the price capture")
    shallow = dict(H.to_record(H.SEED), lengths=[300, 350])
    j = job_of(box(runner=H.SEED_ID), runners={H.SEED_ID: shallow})
    check("a job whose Gelmar copy lists 300/350 cuts 350, not the library's 500",
          {p.length for p in generate_job(j) if p.role == "Drawer Side"}, {350})
    j = job_of(box(runner=H.SEED_ID))
    j.runners[H.SEED_ID]["price"] = 88.5
    hw = api._hardware_summary(j)
    check("pairs per runner, priced off the job's copy: 3 pairs x R88.50",
          [(h["id"], h["pairs"], h["price"], h["total"]) for h in hw], [(H.SEED_ID, 3, 88.5, 265.5)])
    check("  and never in the Plazaboard total",
          estimate_cost(j, summarise(j, generate_job(j)))["total_incl_vat"]
          == estimate_cost(job_of(box(runner=H.SEED_ID)), summarise(job_of(box(runner=H.SEED_ID)),
                           generate_job(job_of(box(runner=H.SEED_ID)))))["total_incl_vat"], True)


def checks_and_api():
    print("\nthe checks a runner raises")
    j = job_of(box(runner=H.SEED_ID, depth=330))
    try:
        generate_job(j)
        raised = ""
    except ValueError as exc:
        raised = str(exc)
    check("no Gelmar length fits 330 deep: the engine says so, naming the shortest (300)",
          "300" in raised and "340" in raised, True)
    j = job_of(box(runner=H.SEED_ID, depth=330))
    got = [i for i in validate(j, []) if i.check == "runner-depth"]
    check("  and the critical keeps its id, naming the record's shortest",
          (len(got), got and "shortest is 300" in got[0].message), (1, True))
    j = job_of(box(runner=H.SEED_ID), runners={})
    got = issues(j, "runner-not-selected")
    check("a runner the project never selected is a critical", len(got), 1)
    j = job_of(box(runner=""), runners={})
    check("  a blank runner (legacy) is not", issues(j, "runner-not-selected"), [])

    print("\nthe API: select, default, swap, delete guard")
    d = job_to_dict(job_of(box(number=1, runner=""), box(number=2, depth=460, runner=""), runners={}))
    r = api.runner_default({"job": d})
    check("a new cabinet in a project with no runner gets the seed, copied in",
          (r["id"], r["added"], list(r["runners"])), (H.SEED_ID, True, [H.SEED_ID]))
    d["runners"] = r["runners"]
    r = api.runner_default({"job": d})
    check("  and with one selected, the project's first", (r["id"], r["added"]), (H.SEED_ID, False))
    sw = api.runner_swap({"job": d, "to": H.SEED_ID})
    check("Use for all drawers: both drawer cabinets", sw["cabinets"], [1, 2])
    moved = {(m["cabinet"], m["role"], m["before"][0], m["after"][0]) for m in sw["moves"]}
    check("  names what moves: cabinet 2 at 460 deep, sides 350 -> 400 and the base with them",
          sorted(moved), [(2, "Drawer Base", 330, 380), (2, "Drawer Side", 350, 400)])
    check("  and cabinet 1 at 560 deep moves nothing", [m for m in sw["moves"] if m["cabinet"] == 1], [])
    check("  a preview writes nothing", "job" in sw, False)
    ap = api.runner_swap({"job": d, "to": H.SEED_ID, "apply": True})
    check("  applied, every drawer cabinet names the runner", [c["runner"] for c in ap["job"]["cabinets"]], [H.SEED_ID] * 2)
    check("  and no designation changed", [x[1] for x in lines(job_from_dict(ap["job"]))],
          [x[1] for x in lines(job_from_dict(d))])
    check("a swap onto a runner the project has not selected is refused",
          api.runner_swap({"job": d, "to": "NOPE"})["ok"], False)
    un = api.runner_select({"job": ap["job"], "id": H.SEED_ID, "on": False})
    check("unticking a runner a cabinet names is refused", (un["ok"], "cabinets 1, 2" in un.get("error", "")), (False, True))

    tmp = tempfile.mkdtemp()
    old_jobs, old_lib = api.JOBS_DIR, H.LIBRARY
    try:
        api.JOBS_DIR = tmp
        os.makedirs(os.path.join(tmp, "lib"))
        H.LIBRARY = os.path.join(tmp, "lib", "hardware.json")
        H.save([H.SEED, H.runner_from_dict({"id": "SPARE", "name": "Spare", "lengths": [400]})])
        with open(os.path.join(tmp, "quoted.json"), "w", encoding="utf-8") as fh:
            json.dump(ap["job"], fh)
        r = api.runner_delete({"id": H.SEED_ID})
        check("the delete guard: a runner a saved job uses is refused, naming it",
              (r["ok"], "quoted.json" in r.get("error", "")), (False, True))
        check("  a runner nobody uses deletes", api.runner_delete({"id": "SPARE"})["ok"], True)
        check("  and is gone", [x.id for x in H.load()], [H.SEED_ID])
        r = api.runner_save({"runner": {"name": "Blum Tandem", "lengths": "450 300, 500", "height": 40,
                                        "side_clearance": 12, "price": "120"}})
        check("runner-save makes an id off the name and cleans the lengths",
              (r["id"], H.find(H.load(), r["id"]).lengths, H.find(H.load(), r["id"]).price),
              ("BLUMTANDEM", [300, 450, 500], 120))
        check("  a runner with no lengths is refused",
              api.runner_save({"runner": {"name": "X", "lengths": ""}})["ok"], False)
        sel = api.runner_select({"job": job_to_dict(job_of(box(), runners={})), "id": "BLUMTANDEM", "on": True})
        check("selecting copies the record in, price captured", sel["job"]["runners"]["BLUMTANDEM"]["price"], 120)
        # editing the library's price does not move the job's copy
        api.runner_save({"runner": dict(H.to_record(H.find(H.load(), "BLUMTANDEM")), price=999), "from": "BLUMTANDEM"})
        check("  editing the library afterwards leaves the job's price", sel["job"]["runners"]["BLUMTANDEM"]["price"], 120)
        fol = api.runner_save({"runner": dict(H.to_record(H.find(H.load(), "BLUMTANDEM")), lengths=[300, 350]),
                               "from": "BLUMTANDEM", "job": sel["job"]})
        check("  the project on screen follows every other field, its price kept",
              (fol["job"]["runners"]["BLUMTANDEM"]["lengths"], fol["job"]["runners"]["BLUMTANDEM"]["price"]),
              ([300, 350], 120))
    finally:
        api.JOBS_DIR, H.LIBRARY = old_jobs, old_lib
        shutil.rmtree(tmp)

    print("\nthe job file")
    j = job_of(box(runner=H.SEED_ID))
    d = job_to_dict(j)
    check("a cabinet naming a runner writes it", d["cabinets"][0].get("runner"), H.SEED_ID)
    check("  and the job its copy", list(d["runners"]), [H.SEED_ID])
    j2 = job_from_dict(json.loads(json.dumps(d)))
    check("  and reads both back", (j2.cabinets[0].runner, j2.cabinets[0].runner_rec.lengths),
          (H.SEED_ID, H.SEED.lengths))
    check("a legacy cabinet writes no runner key", "runner" in job_to_dict(job_of(box(runner="")))["cabinets"][0], False)


def drawer_setting():
    """Part 3: the sketch's worked numbers, off `room.drawer_layout`."""
    from cabinetgen.room import drawer_box_tops, drawer_layout, support_layout
    print("\nthe drawer setting (sketch v2): faces as always, each box hung off its face")
    c = box(runner=H.SEED_ID)
    j = job_of(c)
    L = {u["n"]: u for u in drawer_layout(c, STANDARD, j.materials)}
    check("three drawers, numbered top to bottom", sorted(L), [1, 2, 3])
    d3 = L[3]
    check("drawer 3 (the lowest): face flush with the carcass underside, 0-233", d3["face"], (0, 233))
    check("  its box bottom = bottom panel 16 + lift 5 = 21, top 21 + 150", d3["box"][4:], (21, 171))
    check("  the box front flush with the carcass front, as long as the runner (500 in 560)", d3["box"][2:4], (0, 500))
    check("  the box's outside width: 13.5 in from each side (541 wide)", (d3["box"][0], d3["box"][1], d3["box"][1] - d3["box"][0]),
          (29.5, 570.5, 541))
    check("  the outer rail stands on the bottom panel, 45 high: z 16-61", d3["rail"][2:], (16, 61))
    check("  against each carcass side, 12.7 thick", d3["rails"], [(16, 28.7), (600 - 16 - 12.7, 584)])
    check("  its front at the carcass front, the runner's length back", d3["rail"][:2], (0, 500))
    check("  the inner member starts 3 behind the box front", d3["inner_y0"], 3)
    check("  the space behind: 560 - 500 = 60 (>= 40)", 560 - d3["box"][3], 60)
    check("  full extension: travel = 500", d3["travel"], 500)
    check("drawer 2: the face 2 above drawer 3's, 235-475", L[2]["face"], (235, 475))
    check("  its box hung off its own face: 235 + 21 = 256, to 406", L[2]["box"][4:], (256, 406))
    check("  its runner hangs 5 under its box: 251-296", L[2]["rail"][2:], (251, 296))
    check("drawer 1 (top): face 477-717, box 498-648", (L[1]["face"], L[1]["box"][4:]), ((477, 717), (498, 648)))
    check("the faces fill H - 3 exactly as before: top face at 717 = 720 - 3", L[1]["face"][1], 720 - STANDARD.door_height_gap)
    check("drawer_box_tops reads the same layout", drawer_box_tops(c, STANDARD, j.materials), [(1, 648), (2, 406), (3, 171)])
    shallow = box(runner=H.SEED_ID, depth=460)
    L = {u["n"]: u for u in drawer_layout(shallow, STANDARD, j.materials)}
    check("a 460 deep carcass on Gelmar: a 400 box, 60 behind", (L[3]["box"][3], 460 - L[3]["box"][3]), (400, 60))
    leg = box(runner="", depth=460)
    L = {u["n"]: u for u in drawer_layout(leg, STANDARD, j.materials)}
    check("  the same carcass on legacy: 350", L[3]["box"][3], 350)

    print("\nthe support-foul critical reads the same layout")
    rows = [Support(type="front", qty=1), Support(type="top_rear", qty=1), Support(type="back", qty=2)]
    # 720 high: the band under the Top Front runs 688-704 (the rail 704-720)
    c = box(runner=H.SEED_ID, support_rows=rows,
            drawers=[Drawer(face_height=200, box_height=180), Drawer(face_height=515, box_height=150)])
    j = job_of(c)
    top = dict(drawer_box_tops(c, STANDARD, j.materials))[1]
    check("drawer 1: face 517-717, box 517 + 21 = 538 up to 718", top, 718)
    got = issues(j, "support-drawer-foul")
    check("  into the band under the Top Front (above 688): critical", (len(got), got and "718" in got[0].message), (1, True))
    c = box(runner=H.SEED_ID, support_rows=rows,
            drawers=[Drawer(face_height=200, box_height=150), Drawer(face_height=515, box_height=150)])
    check("  a 150 box tops out at 688, exactly the band's underside: clear",
          (dict(drawer_box_tops(c, STANDARD, j.materials))[1], issues(job_of(c), "support-drawer-foul")), (688, []))


def inner_drawers():
    """Part 4: inner drawers behind the door (ruled with Rudolf, 28 September
    2026): face = the box's carcass size, front on the shelves' line, heights
    typed per drawer and equally spaced from the bottom when the count changes,
    all inner or all outer, the runner picked over the depth less the face."""
    from cabinetgen.engine import front_stack_check
    from cabinetgen.room import drawer_layout, inner_drawer_z, solid_parts
    from cabinetgen.store import cabinet_to_dict
    print("\ninner drawers: behind the door, the face the box's size")

    def inner(n=2, box_h=150, **kw):
        return [Drawer(face_height=box_h, box_height=box_h, inner=True) for _ in range(n)]

    c = box(runner=H.SEED_ID, doors=1, drawers=inner(2))
    j = job_of(c)
    check("W 600 H 720 (inside 688), two inner drawers: equally spaced from 21",
          inner_drawer_z(c, STANDARD, j.materials), [21, 365])
    check("  four: 21, 193, 365, 537", inner_drawer_z(c, STANDARD, j.materials, 4), [21, 193, 365, 537])
    faces = [p for p in generate_job(j) if p.role == "Drawer Face"]
    check("the face is the box's carcass size: 150 high x 541 wide (opening 568 - 27)",
          [(p.length, p.width, p.qty, p.note) for p in faces], [(150, 541, 2, "inner")])
    check("  a code-20 line off its face board, grain up the height, edged like any face",
          (faces[0].label[-2:], faces[0].material, faces[0].grain, faces[0].edge_l, faces[0].edge_w),
          ("20", "BROOKHILL", 1, 2, 2))
    check("  the box is cut exactly as an outer one's",
          sorted((p.role, p.length, p.width) for p in generate_job(j) if p.role in ("Drawer Side", "Drawer Front")),
          [("Drawer Front", 509, 150), ("Drawer Side", 500, 150)])
    L = {u["n"]: u for u in drawer_layout(c, STANDARD, j.materials)}
    check("drawer 2 (the lowest) at 21, drawer 1 at 365 — face = box, no stack arithmetic",
          (L[2]["face"], L[2]["box"][4:], L[1]["face"]), ((21, 171), (21, 171), (365, 515)))
    check("  its face front on the shelves' line (the carcass front), 16 thick", L[2]["face_y"], (0, 16))
    check("  the box and the runner start a face thickness back", (L[2]["box"][2], L[2]["rail"][0]), (16, 16))
    check("  the face spans the box's outside width", L[2]["face_x"], (29.5, 570.5))
    check("no face-stack arithmetic: the door is H - 3 and the stack check is quiet",
          front_stack_check(c, STANDARD)[2], 0)
    check("  and nothing inner is drawn on the front (solid_parts: the door only)",
          sorted(q.role for q in solid_parts(c, STANDARD, j.materials) if q.front), ["door"])
    typed = box(runner=H.SEED_ID, doors=1, drawers=inner(2))
    typed.drawers[0].z = 400
    L = {u["n"]: u for u in drawer_layout(typed, STANDARD, j.materials)}
    check("a typed height is where the box stands; the other keeps its default",
          (L[1]["box"][4], L[2]["box"][4]), (400, 21))

    print("\nthe runner is picked over the depth less the face")
    deep = box(runner=H.SEED_ID, doors=1, depth=545, drawers=inner(1))
    check("545 deep: outer drawers get 500 (505 usable) ...", H.SEED.pick(545, 40), 500)
    check("  an inner one 450 (545 - 16 - 40 = 489)",
          {p.length for p in generate_job(job_of(deep)) if p.role == "Drawer Side"}, {450})
    L = drawer_layout(deep, STANDARD, job_of(deep).materials)[0]
    check("  which leaves 545 - 16 - 450 = 79 behind the box", 545 - L["box"][3], 79)

    print("\nthe job file, and the API")
    d = cabinet_to_dict(box(drawers=[Drawer(face_height=200, box_height=150)]))
    check("an outer drawer writes no inner / z", ("inner" in d["drawers"][0], "z" in d["drawers"][0]), (False, False))
    d = cabinet_to_dict(typed)
    check("an inner drawer writes both", (d["drawers"][0]["inner"], d["drawers"][0]["z"]), (True, 400))
    jd = job_to_dict(job_of(box(runner=H.SEED_ID, doors=1, height=2400, kind="tall",
                                drawers=[Drawer(face_height=300, box_height=180),
                                         Drawer(face_height=250, box_height=150)])))
    r = api.inner_drawers({"job": jd, "index": 0, "inner": True})
    check("make them inner: every height on the equal spacing (inside 2368 / 2)",
          [(x["inner"], x["z"], x["box_height"]) for x in r["drawers"]], [(True, 1205, 180), (True, 21, 150)])
    check("  face heights kept, so turning them back restores the stack",
          [x["face_height"] for x in r["drawers"]], [300, 250])
    jd["cabinets"][0]["drawers"] = r["drawers"]
    r3 = api.inner_drawers({"job": jd, "index": 0, "inner": True, "count": 3})
    check("a count change puts every height back on the spacing: 21, 810, 1600",
          [x["z"] for x in r3["drawers"]], [1600, 810, 21])
    back = api.inner_drawers({"job": jd, "index": 0, "inner": False})
    check("  and outer again: off the inner list, the faces as they were",
          [(x.get("inner", False), "z" in x, x["face_height"]) for x in back["drawers"]],
          [(False, False, 300), (False, False, 250)])

    print("\nthe inner-drawer criticals")
    check("inner drawers and no door: drawer-inner-no-door",
          len(issues(job_of(box(runner=H.SEED_ID, doors=0, drawers=inner(2))), "drawer-inner-no-door")), 1)
    mixed = box(runner=H.SEED_ID, doors=1, drawers=inner(1) + [Drawer(face_height=200, box_height=150)])
    check("inner and outer on one cabinet: drawer-inner-mixed", len(issues(job_of(mixed), "drawer-inner-mixed")), 1)
    low = box(runner=H.SEED_ID, doors=1, drawers=inner(1))
    low.drawers[0].z = 10
    got = issues(job_of(low), "drawer-inner-range")
    check("a box starting at 10 — its runner under the bottom panel: drawer-inner-range",
          (len(got), got and "lowest a box can start is 21" in got[0].message), (1, True))
    high = box(runner=H.SEED_ID, doors=1, drawers=inner(1))
    high.drawers[0].z = 600
    got = issues(job_of(high), "drawer-inner-range")
    check("  a 150 box at 600 reaches 750, past the top at 704: the same",
          (len(got), got and "750" in got[0].message and "704" in got[0].message), (1, True))
    check("  and the two defaults raise none of it",
          [i.check for i in validate(j, generate_job(j)) if i.check.startswith("drawer-inner")], [])


def drawer_checks():
    """The drawer checks — "faces lead, boxes follow", ruled by Rudolf on 28
    September 2026 (replacing the brief's Part 5 box-height rules): worked
    numbers for every rule and every stable id."""
    from cabinetgen.room import drawer_layout
    print("\nfaces lead, boxes follow (ruled 28 September 2026) — the drawer checks")

    def two(top_face=545, low_face=170, low_box=150, low_off=None, top_box=150, top_off=None):
        # W 600 H 720: the lower drawer is the last in the list, face 0-low_face;
        # the upper face starts 2 above it
        return box(runner=H.SEED_ID, drawers=[
            Drawer(face_height=top_face, box_height=top_box, offset=top_off),
            Drawer(face_height=low_face, box_height=low_box, offset=low_off)])

    print("  rules 2 and 5: each box sits its offset (default 21) above its own face bottom")
    c = two(low_face=200)
    L = {u["n"]: u for u in drawer_layout(c, STANDARD, job_of(c).materials)}
    check("bottom drawer, face 0-200, box 150 at the default: box 21-171", (L[2]["offset"], L[2]["box"][4:]), (21, (21, 171)))
    check("  the tallest box that face takes is 200 - 21 = 179", L[2]["max_box"], 179)
    check("upper drawer, face 202-747: box 223-373, the tallest 747 - 223 = 524",
          (L[1]["box"][4:], L[1]["max_box"]), ((223, 373), 524))
    c = two(low_face=200, low_off=40)
    L = {u["n"]: u for u in drawer_layout(c, STANDARD, job_of(c).materials)}
    check("the bottom drawer raised to 40: box 40-190, the tallest 160", (L[2]["box"][4:], L[2]["max_box"]), ((40, 190), 160))
    check("  and raising it is not a fault", [i.check for i in validate(job_of(c), generate_job(job_of(c)))
                                           if i.check.startswith("drawer-")], [])

    print("  rule 1: every box within its own face (drawer-box-face)")
    got = issues(job_of(two()), "drawer-box-face")
    check("face 170, box 150 at 21: the box runs 21-171, 1 above the face top at 170",
          (len(got), got and "runs 21-171, 1 above the face top at 170" in got[0].message), (1, True))
    check("  and says the tallest box it takes: 149", bool(got) and "tallest box this face takes is 149" in got[0].message, True)
    check("face 171, box 150: its top level with the face top is inside", issues(job_of(two(low_face=171)), "drawer-box-face"), [])
    c = two(low_face=200, top_off=-5)
    got = issues(job_of(c), "drawer-box-face")
    check("an upper box set 5 BELOW its own face bottom: 5 below the face bottom at 202",
          (len(got), got and "5 below the face bottom at 202" in got[0].message), (1, True))
    c = two(low_face=200, top_off=0, top_box=545)
    check("an upper box as tall as its face at offset 0 lies within it: allowed now",
          issues(job_of(c), "drawer-box-face"), [])
    check("  (drawer-box-height, 'box not shorter than its face', is retired)",
          [i.check for i in validate(job_of(c), generate_job(job_of(c))) if i.check == "drawer-box-height"], [])
    c = two(low_face=200, top_off=400)
    got = issues(job_of(c), "drawer-box-face")
    check("an upper box raised to 400 in a 545 face: 150 + 400 runs past the top by 5",
          (len(got), got and "5 above the face top at 747" in got[0].message), (1, True))
    test = load(job_file("Test_drawers"))
    got = sorted((i.where, i.message.split(":")[0]) for i in validate(test, generate_job(test))
                 if i.check == "drawer-box-face")
    check("Test_drawers.json cabinet 4 at default offsets (faces 110 / 165 / 220, boxes 90 / 150 / 200): drawers 1-3",
          got, [("4", "drawer 1"), ("4", "drawer 2"), ("4", "drawer 3")])
    check("  and its top drawer is still support-foul", sorted(i.where for i in validate(test, generate_job(test))
                                                          if i.check == "support-drawer-foul"), ["4"])

    print("  rule 3: the bottom drawer never below 21 (drawer-bottom-offset)")
    got = issues(job_of(two(low_face=200, low_off=15)), "drawer-bottom-offset")
    check("the bottom drawer set to 15: below 21, its runner under the bottom panel",
          (len(got), got and "set 15 above its face bottom" in got[0].message), (1, True))
    check("  21 exactly is the default and fine", issues(job_of(two(low_face=200, low_off=21)), "drawer-bottom-offset"), [])
    check("  an UPPER drawer may go lower than 21 (10)", issues(job_of(two(low_face=200, top_off=10)), "drawer-bottom-offset"), [])

    print("  rules 7 and 8: inner drawers' gap, and boxes clashing")
    def inner(z_top, z_low=21, h=150):
        return box(runner=H.SEED_ID, doors=1, drawers=[
            Drawer(face_height=h, box_height=h, inner=True, z=z_top),
            Drawer(face_height=h, box_height=h, inner=True, z=z_low)])
    check("Standard.inner_drawer_min_gap is 30", STANDARD.inner_drawer_min_gap, 30)
    got = issues(job_of(inner(160)), "drawer-box-clash")
    check("inner at 21 and 160, boxes 150: 171 into 160 — drawer-box-clash",
          (len(got), got and "drawer 2: its box reaches 171, into drawer 1's box above, which starts at 160"
           in got[0].message), (1, True))
    check("  and not also a gap message", issues(job_of(inner(160)), "drawer-inner-gap"), [])
    got = issues(job_of(inner(190)), "drawer-inner-gap")
    check("inner at 21 and 190: 19 clear, under 30 — drawer-inner-gap",
          (len(got), got and "19 clear" in got[0].message), (1, True))
    check("  at 201: 30 clear, fine", (issues(job_of(inner(201)), "drawer-inner-gap"),
                                      issues(job_of(inner(201)), "drawer-box-clash")), ([], []))
    check("  the equal spacing's own defaults (21 / 365 in 720) are clear",
          [i.check for i in validate(job_of(inner(None)), generate_job(job_of(inner(None))))
           if i.check.startswith("drawer-")], [])

    print("  kept: the runner checks")
    c = two(low_face=200, low_box=44)
    got = issues(job_of(c), "drawer-runner-height")
    check("a 44 box on a 45 runner: drawer-runner-height", (len(got), got and "44" in got[0].message), (1, True))
    check("  45 on 45 fits", issues(job_of(two(low_face=200, low_box=45)), "drawer-runner-height"), [])
    check("no length fitting is still runner-depth (its id kept)",
          len([i for i in validate(job_of(box(runner=H.SEED_ID, depth=330)), [])
               if i.check == "runner-depth"]), 1)
    ids = {i.check for i in validate(OCT, generate_job(OCT)) if i.check.startswith("drawer-")}
    check("the October job raises none of them", ids, set())

    print("  the job file, and the divider drag")
    from cabinetgen.store import cabinet_to_dict
    from cabinetgen.drawers import split_pair
    d = cabinet_to_dict(two())
    check("a default offset is not written", any("offset" in x for x in d["drawers"]), False)
    d = cabinet_to_dict(two(low_off=40))
    check("  a set one is", [x.get("offset") for x in d["drawers"]], [None, 40])
    check("split_pair holds each face to its own box + offset (top 21, bottom 40)",
          split_pair(200, 300, 10, 90, 116, None, STANDARD, 21, 40), (111, 389))
    check("  and the bottom face to 116 + 40 when dragged down", split_pair(200, 300, 400, 90, 116, None, STANDARD, 21, 40),
          (502 - 2 - 156, 156))


def scene_3d():
    """Part 6: drawer boxes and runners drawn in 3D, off the one layout, kept
    out of the drawings."""
    from cabinetgen import scene as SC
    from cabinetgen.render import plan_svg, wall_elevation_svg
    from cabinetgen.room import drawer_parts, interior_parts, solid_parts
    print("\nPart 6 — drawer boxes and runners in 3D")
    check("the legend no longer lists drawer boxes as not drawn", "drawer box" in SC.NOT_DRAWN, False)
    c = box(runner=H.SEED_ID, drawers=[Drawer(face_height=545, box_height=150),
                                       Drawer(face_height=170, box_height=120)])
    j = job_of(c)
    parts = drawer_parts(c, STANDARD, j.materials)
    low = [q for q in parts if q.index == 1]
    roles = sorted(q.role for q in low)
    check("per drawer: two sides, a front, a back, a base and two runners",
          roles, ["drawer_back", "drawer_base", "drawer_front", "drawer_side", "drawer_side", "runner", "runner"])

    def ext(q):
        xs, ys = [x for x, _ in q.outline], [y for _, y in q.outline]
        return (round(min(xs), 1), round(max(xs), 1), round(min(ys), 1), round(max(ys), 1), q.z0, q.z1)
    by = {}
    for q in low:
        by.setdefault(q.role, []).append(ext(q))
    # D 560: the spec's y 0..500 from the front is the part frame's 60..560
    check("the left side: x 29.5-45.5, the runner's length 60-560 (front flush with the carcass), z 21-141",
          by["drawer_side"][0], (29.5, 45.5, 60, 560, 21, 141))
    check("the front between the sides, at the carcass front", by["drawer_front"][0], (45.5, 554.5, 544, 560, 21, 141))
    check("the back at the far end", by["drawer_back"][0], (45.5, 554.5, 60, 76, 21, 141))
    check("a grooved 3 mm base 16 up the sides, 6 into all four",
          by["drawer_base"][0], (39.5, 560.5, 70, 550, 37, 40))
    check("the runners: 12.7 against each side, the runner's length, standing on the bottom panel",
          sorted(by["runner"]), [(16, 28.7, 60, 560, 16, 61), (571.3, 584, 60, 560, 16, 61)])
    s = SC.build_cabinet(j, 1) if hasattr(SC, "build_cabinet") else None
    it = s["items"][0] if s else None
    if it:
        mine = [q for q in it["parts"] if q["role"] in ("drawer_side", "drawer_front", "drawer_back", "drawer_base")]
        cut = {p.label: p.role for p in generate_job(j) if p.cabinet == 1}
        check("every box part names its cut-list line, of its own role",
              sorted({(q["role"], cut.get(q["line"])) for q in mine}),
              [("drawer_back", "Drawer Front"), ("drawer_base", "Drawer Base"),
               ("drawer_front", "Drawer Front"), ("drawer_side", "Drawer Side")])
        faces = [q for q in it["parts"] if q["role"] == "drawer"]
        check("fronts open: box and face slide out together, as far as the runner travels (500)",
              {tuple(q["pull"]["dir"]) + (q["pull"]["distance"],) for q in mine + faces},
              {tuple(faces[0]["pull"]["dir"]) + (500,)})
        runners = [q for q in it["parts"] if q["role"] == "runner"]
        check("a runner does not slide, and says it is hardware",
              ({q["pull"] for q in runners}, {q["reason"] for q in runners}),
              ({None}, {"hardware — a runner is bought, not cut"}))
    three_q = dict(H.to_record(H.SEED), id="TQ", extension=0.75)
    t = box(runner="TQ", drawers=[Drawer(face_height=717, box_height=150)])
    jt = job_of(t, runners={"TQ": three_q})
    s = SC.build_cabinet(jt, 1)
    check("a three-quarter runner travels 375 of 500",
          {q["pull"]["distance"] for q in s["items"][0]["parts"] if q["role"] == "drawer_base"}, {375})
    inner = box(runner=H.SEED_ID, doors=1, drawers=[Drawer(face_height=150, box_height=150, inner=True)])
    ji = job_of(inner)
    s = SC.build_cabinet(ji, 1)
    face = [q for q in s["items"][0]["parts"] if q["role"] == "drawer"]
    check("an inner drawer's face is drawn with its box, labelled inner, and slides out",
          ([q["label"] for q in face], face and face[0]["pull"] is not None), (["inner"], True))

    print("\nnothing drawn moves the plan, Finish or any wall elevation")
    check("solid_parts carries no drawer box and no runner",
          {q.role for q in solid_parts(c, STANDARD, j.materials)} & {"drawer_side", "drawer_front",
                                                                      "drawer_back", "drawer_base", "runner"}, set())
    check("interior_parts carries them (the 3D's list)",
          {"drawer_side", "runner"} <= {q.role for q, _ in interior_parts(c, STANDARD, j.materials)}, True)
    import cabinetgen.room as RM
    test = load(job_file("Test_drawers"))
    walls = [w.id for w in test.room.walls]

    def drawings():
        return ([plan_svg(test)] + [wall_elevation_svg(test, w) for w in walls]
                + [wall_elevation_svg(test, w, mode="finish") for w in walls])
    with_boxes = drawings()
    keep = RM.drawer_parts
    RM.drawer_parts = lambda *a, **k: []
    try:
        without = drawings()
    finally:
        RM.drawer_parts = keep
    check("Test_drawers.json: the plan and every wall elevation, Line and Finish, are the same with the "
          "boxes and runners taken out", [a == b for a, b in zip(with_boxes, without)], [True] * len(with_boxes))


def main():
    catalogue()
    legacy_holds()
    checks_and_api()
    drawer_setting()
    inner_drawers()
    drawer_checks()
    scene_3d()
    print()
    if FAILS:
        print(f"{len(FAILS)} FAILED: " + "; ".join(FAILS))
        sys.exit(1)
    print("ALL OK")


if __name__ == "__main__":
    main()
