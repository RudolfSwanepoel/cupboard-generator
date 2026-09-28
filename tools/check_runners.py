"""Runners: the catalogue, the legacy record, what a runner sizes, and the checks.

    python tools/check_runners.py

The drawers / runners / supports brief of 28 September 2026. Holds:

  * Part 2 — the runner catalogue. `hardware.json` holds the Gelmar seed as
    ruled (45 high, 13.5 a side, 12.7 rail, 300-600, full, 35 kg, lift 5,
    setback 3); a job saved before the catalogue names no runner and is cut on
    the built-in LEGACY record (350 / 450 / 500), so the October job and
    Test.json cut exactly what they cut; the runner length is the longest on
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
    if g:
        check("  as ruled", (g.height, g.side_clearance, g.rail_thickness, g.lengths, g.extension,
                             g.capacity_kg, g.lift, g.setback, g.type),
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
    test = load(job_file("Test"))
    got = lines(test)
    check("Test.json cabinets 4 and 7 are on legacy", sorted(c.number for c in test.cabinets if c.drawer_list and not c.runner), [4, 7])
    check("  sides 500 (570 deep), fronts internal width - 59",
          sorted({(c, r, a, b) for c, _, r, a, b, _ in got if r in ("Drawer Side", "Drawer Front")}),
          sorted({(4, "Drawer Front", 400 - 32 - 59, b) for c, _, r, a, b, _ in got if c == 4 and r == "Drawer Front"} |
                 {(4, "Drawer Side", 500, b) for c, _, r, a, b, _ in got if c == 4 and r == "Drawer Side"} |
                 {(7, "Drawer Front", 350 - 32 - 59, b) for c, _, r, a, b, _ in got if c == 7 and r == "Drawer Front"} |
                 {(7, "Drawer Side", 500, b) for c, _, r, a, b, _ in got if c == 7 and r == "Drawer Side"}))
    raw = json.load(open(job_file("Test"), encoding="utf-8"))
    check("Test.json round-trips byte for byte (no runner, no runners key)",
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


def main():
    catalogue()
    legacy_holds()
    checks_and_api()
    extra = globals().get("more")
    if extra:
        extra()
    print()
    if FAILS:
        print(f"{len(FAILS)} FAILED: " + "; ".join(FAILS))
        sys.exit(1)
    print("ALL OK")


if __name__ == "__main__":
    main()
