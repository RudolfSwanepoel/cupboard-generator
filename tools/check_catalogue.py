"""The catalogue of standard cupboards — ruling 9 of the cabinet round brief (3 October 2026).

Temp files only: the library is redirected to a temp folder for the whole run
and the live cupboards.json is never read or written. What is pinned, from the
brief's "Done when" line and Rudolf's change 4:

  * add -> the record and its name: `<Kind> W×H×D` generated and always first,
    the text after it; the author and the date; the cupboard without its
    number, placement or note; its attached panels with their offsets; the
    boards and runners it names; a Panel refused;
  * a taken name refused, any case, with the one message, and nothing written;
  * place -> the next free numbers, the attached panels with theirs, unplaced
    (no placement), and cutting exactly what the original cut when the boards
    are the same;
  * a board the project lacks is mapped (default the first project board of
    the same thickness) and the copy names the mapped id; a runner the project
    lacks is ticked in from the library or mapped; unmapped, nothing lands;
  * editing the copy leaves the catalogue byte-identical, and vice versa;
  * Rename changes only the text after the fixed prefix (change 4); a taken
    name is refused; delete; the API; Import brings catalogue cupboards across
    (new / identical / "(imported)"); the demo build and the import UI check
    copy the file by name.
"""
import copy
import json
import os
import shutil
import sys
import tempfile

ROOT = os.path.join(os.path.dirname(__file__), "..")
from fixture_jobs import job_file  # noqa: E402
sys.path.insert(0, ROOT)

from app import api                                                      # noqa: E402
from cabinetgen import boards as B                                       # noqa: E402
from cabinetgen import catalogue as CAT                                  # noqa: E402
from cabinetgen import hardware as H                                     # noqa: E402
from cabinetgen import importer as IMP                                   # noqa: E402
from cabinetgen.engine import generate_cabinet, generate_job             # noqa: E402
from cabinetgen.model import MATERIALS, Cabinet, Job, PanelSpec, Shelf, material_thickness  # noqa: E402
from cabinetgen.room import attached_panels                              # noqa: E402
from cabinetgen.store import job_to_dict, load                           # noqa: E402

FAILS = []


def check(name, got, want):
    ok = got == want
    print(f"  {'ok  ' if ok else 'FAIL'}  {name}: {got!r}" + ("" if ok else f"  (wanted {want!r})"))
    if not ok:
        FAILS.append(name)
    return ok


def lines(job, c):
    return [(p.code, p.role, p.material, p.length, p.width, p.qty, p.edge_l, p.edge_w, p.edge_material, p.grain)
            for p in generate_cabinet(c, job.std, job.materials)]


def file_bytes(path):
    with open(path, "rb") as fh:
        return fh.read()


def main():
    print(__doc__.strip().splitlines()[0])
    top = tempfile.mkdtemp(prefix="check_catalogue_")
    saved = (CAT.LIBRARY, B.LIBRARY, H.LIBRARY, api.ROOT, api.JOBS_DIR, api.PICTURES_DIR, api.OUT_DIR, api.DELETED_DIR)
    live = file_bytes(os.path.join(ROOT, "cupboards.json")) if os.path.exists(os.path.join(ROOT, "cupboards.json")) else None
    try:
        CAT.LIBRARY = os.path.join(top, "cupboards.json")
        shutil.copyfile(os.path.join(ROOT, "boards.json"), os.path.join(top, "boards.json"))
        shutil.copyfile(os.path.join(ROOT, "hardware.json"), os.path.join(top, "hardware.json"))
        B.LIBRARY = os.path.join(top, "boards.json")
        H.LIBRARY = os.path.join(top, "hardware.json")
        run(top)
    finally:
        (CAT.LIBRARY, B.LIBRARY, H.LIBRARY, api.ROOT, api.JOBS_DIR, api.PICTURES_DIR, api.OUT_DIR, api.DELETED_DIR) = saved
        shutil.rmtree(top, ignore_errors=True)
    now = file_bytes(os.path.join(ROOT, "cupboards.json")) if os.path.exists(os.path.join(ROOT, "cupboards.json")) else None
    check("the live cupboards.json was never touched", now == live, True)
    print()
    if FAILS:
        print(f"{len(FAILS)} FAILED: {FAILS}")
        return 1
    print("ALL OK")
    return 0


def run(top):
    print("\nadd: the record and its name")
    job = load(job_file("Test.json"))
    host = next(c for c in job.cabinets if not c.is_panel and attached_panels(job, c.number))
    pans = attached_panels(job, host.number)
    check(f"Test.json cabinet {host.number} has attached panels to carry", len(pans) > 0, True)
    recs = []
    rec = CAT.add(job, host.number, " Rudolf ", "  with end panel ", recs, today="2026-10-03")
    g = (host.width, host.height, host.depth)
    check("the name: <Kind> W×H×D generated, always first, then the text",
          (rec["prefix"], rec["name"]), (f"{CAT.kind_word(host)} {g[0]}×{g[1]}×{g[2]}", f"{CAT.kind_word(host)} {g[0]}×{g[1]}×{g[2]} with end panel"))
    check("author and date, trimmed", (rec["author"], rec["added"]), ("Rudolf", "2026-10-03"))
    check("the cupboard without its number or note", (rec["cabinet"]["number"], rec["cabinet"]["note"]), (0, ""))
    check("  and no placement anywhere in the record", "placement" in json.dumps(rec), False)
    check("its attached panels, with their offsets, their host the record's head",
          [(p["panel"]["attached_to"], p["panel"]["at_x"], p["panel"]["at_y"], p["panel"]["at_z"]) for p in rec["panels"]],
          [(0, p.panel.at_x, p.panel.at_y, p.panel.at_z) for p in pans])
    everything = [host] + list(pans)
    want_boards = []
    for c in everything:
        for bid in c.board_ids_used():
            if bid not in want_boards:
                want_boards.append(bid)
    check("the boards it names, id and name", [b["id"] for b in rec["boards"]], want_boards)
    check("  with their thickness", all(b["thickness"] in (3, 16) for b in rec["boards"]), True)
    check("  and their records snapshotted", sorted(rec["materials"]), sorted(want_boards))
    check("the runner it names", [r["id"] for r in rec["runners"]], [host.runner] if host.runner else [])
    plain = CAT.add(job, next(c.number for c in job.cabinets if not c.is_panel and c.number != host.number and not attached_panels(job, c.number)),
                    "", "", recs, today="2026-10-03")
    check("no text: the name is the prefix alone", plain["name"], plain["prefix"])
    pan = next(c for c in job.cabinets if c.is_panel)
    try:
        CAT.add(job, pan.number, "R", "x", recs)
        check("a Panel is refused", False, True)
    except ValueError as exc:
        check("a Panel is refused", "not a cupboard" in str(exc), True)
    check("  and nothing was added for it", len(recs), 2)

    print("\na taken name is refused, any case, and nothing is written")
    CAT.save(recs)
    before = file_bytes(CAT.LIBRARY)
    for text in ("with end panel", "WITH END PANEL", " with  End Panel "):
        try:
            CAT.add(job, host.number, "R", text, recs)
            check(f"{text!r}: refused", False, True)
        except ValueError as exc:
            check(f"{text!r}: refused with the one message", str(exc), IMP.taken_message(CAT.full_name(rec["prefix"], text)))
    check("  the list is unchanged", len(recs), 2)
    r = api.catalogue_add({"job": job_to_dict(job), "cabinet": host.number, "author": "R", "text": "With End Panel"})
    check("/api/catalogue-add refuses it too, naming the field", (r["ok"], r.get("taken"), r.get("field")), (False, True, "text"))
    check("  and the file is byte-identical", file_bytes(CAT.LIBRARY) == before, True)

    print("\nplace: next free numbers, the panels with theirs, unplaced, the same cut")
    target = load(job_file("Test.json"))                         # the same boards: nothing to map
    n_before = len(target.cabinets)
    used = {c.number for c in target.cabinets}
    placed = CAT.place(target, rec)
    nums = [c.number for c in placed]
    check("the head and its panels got the next free numbers, in order",
          (len(placed), all(n not in used for n in nums), nums == sorted(nums)), (1 + len(pans), True, True))
    check("  the panels attach to the new head", [c.panel.attached_to for c in placed[1:]], [placed[0].number] * len(pans))
    check("  unplaced: no placement for any of them", [p for p in target.placements if p.cabinet in nums], [])
    check("  appended to the job", len(target.cabinets), n_before + len(placed))
    check("the copy cuts exactly what the original cut", lines(target, placed[0]), lines(job, host))
    check("  and its panels theirs", [lines(target, c) for c in placed[1:]], [lines(job, p) for p in pans])
    check("no note, no number carried over", (placed[0].note, placed[0].number == host.number), ("", False))

    print("\na board the project lacks is mapped; the copy names the mapped id")
    lacking = load(job_file("Test_Build.json"))
    missing = [b["id"] for b in rec["boards"] if b["id"] not in lacking.boards]
    check("Test_Build lacks a board the record names", len(missing) > 0, True)
    need = CAT.needs_mapping(lacking, rec)
    check("needs_mapping names exactly those", [b["id"] for b in need["boards"]], missing)
    for b in need["boards"]:
        same = [k for k in lacking.boards if material_thickness(lacking.materials, k) == b["thickness"]]
        check(f"  {b['id']}: the default is the first project board of the same thickness ({b['thickness']} mm)",
              b["default"], same[0] if same else lacking.boards[0])
        check(f"  {b['id']}: the options are the project's boards", b["options"], list(lacking.boards))
    try:
        CAT.place(lacking, rec)
        check("unmapped, nothing lands", False, True)
    except ValueError as exc:
        check("unmapped, nothing lands (refused by name)", all(m in str(exc) for m in missing), True)
    r = api.catalogue_place({"job": job_to_dict(lacking), "name": rec["name"]})
    check("/api/catalogue-place answers `needs` and no cabinets", (r["ok"], r["needs"] is not None, r["cabinets"]), (True, True, []))
    bmap = {b["id"]: b["default"] for b in need["boards"]}
    rmap = {q["id"]: q["default"] for q in need["runners"]}
    copies = CAT.place(lacking, rec, bmap, rmap)
    refs = {bid for c in copies for bid in c.board_ids_used()}
    check("placed with the map: the copies name the mapped ids and no missing one",
          (all(m not in refs for m in missing), all(bmap[m] in refs for m in missing)), (True, True))
    check("  every board the copies name is selected in the project", refs <= set(lacking.boards), True)
    r = api.catalogue_place({"job": job_to_dict(load(job_file("Test_Build.json"))), "name": rec["name"],
                             "map": {"boards": bmap, "runners": rmap}})
    check("  the API lands it the same way", (r["ok"], r["needs"], len(r["cabinets"])), (True, None, len(copies)))

    print("\na runner the project lacks: the library's record ticked in, or a project runner")
    lib_runner = H.load()[0]
    rj = load(job_file("Test.json"))
    withr = next(c for c in rj.cabinets if not c.is_panel and c.drawer_list and c.runner)
    recs_r = []
    rec_r = CAT.add(rj, withr.number, "R", "drawers", recs_r, today="2026-10-03")
    check("the record names its runner", [q["id"] for q in rec_r["runners"]], [withr.runner])
    bare = load(job_file("Test.json"))
    bare.runners = {}
    for c in bare.cabinets:
        c.runner = ""
    need = CAT.needs_mapping(bare, rec_r)
    check("a project with no runner: the library's record is offered first", [(q["id"], q["in_library"], q["default"]) for q in need["runners"]],
          [(withr.runner, True, "library")])
    got = CAT.place(bare, rec_r, {}, {withr.runner: "library"})
    check("  'library' ticks it into the project and the copy keeps its runner", (withr.runner in bare.runners, got[0].runner), (True, withr.runner))
    other = load(job_file("Test.json"))
    other.runners = {"OTHER": dict(H.to_record(lib_runner), id="OTHER", name="Other runner")}
    for c in other.cabinets:
        c.runner = "OTHER"
    need = CAT.needs_mapping(other, rec_r)
    got = CAT.place(other, rec_r, {}, {withr.runner: "OTHER"})
    check("mapped to a project runner: the copy names it", got[0].runner, "OTHER")
    try:
        CAT.place(load(job_file("Test_Build.json")), rec_r, {}, {withr.runner: "NOPE"})
        check("a runner mapped to nothing the project has is refused", False, True)
    except ValueError as exc:
        check("a runner mapped to nothing the project has is refused", "must be mapped" in str(exc), True)

    print("\nediting the copy leaves the catalogue byte-identical, and vice versa")
    CAT.save(recs)
    before = file_bytes(CAT.LIBRARY)
    placed[0].width = 999
    placed[0].shelf_rows = [Shelf(), Shelf()]
    placed[0].note = "changed"
    check("the file after editing the copy", file_bytes(CAT.LIBRARY) == before, True)
    check("  and the record in memory", recs[0]["cabinet"]["width"], rec["cabinet"]["width"])
    snap = copy.deepcopy(job_to_dict(target))
    recs[0]["cabinet"]["width"] = 123
    recs[0]["text"] = "renamed later"
    CAT.save(recs)
    check("editing the record leaves the placed copy exactly as it was", job_to_dict(target), snap)
    recs[0]["cabinet"]["width"] = rec["cabinet"]["width"]
    recs[0]["text"] = rec["text"]

    print("\nRename: only the text after the fixed prefix (change 4)")
    r2 = CAT.rename(recs, rec["name"], "  tall robe ")
    check("the prefix is kept, always first", (r2["prefix"], r2["name"]), (rec["prefix"], rec["prefix"] + " tall robe"))
    check("  the text stored trimmed", r2["text"], "tall robe")
    # a collision needs the same prefix: a second record off the same cupboard
    two = CAT.add(job, host.number, "R", "two", recs, today="2026-10-03")
    check("a second record off the same cupboard: the same prefix, its own text", (two["prefix"], two["name"]), (rec["prefix"], rec["prefix"] + " two"))
    try:
        CAT.rename(recs, r2["name"], "TWO")
        check("renaming onto a taken name is refused", False, True)
    except ValueError as exc:
        check("renaming onto a taken name is refused (any case)", str(exc), IMP.taken_message(rec["prefix"] + " TWO"))
    r3 = CAT.rename(recs, r2["name"], "TALL ROBE")
    check("a case change of its own text is allowed", r3["name"], rec["prefix"] + " TALL ROBE")
    CAT.save(recs)
    r = api.catalogue_rename({"name": r3["name"], "text": "x"})
    check("/api/catalogue-rename", (r["ok"], r["cupboard"]["name"]), (True, rec["prefix"] + " x"))
    r = api.catalogue_rename({"name": rec["prefix"] + " x", "text": "two"})
    check("  refuses a taken name under the field", (r["ok"], r.get("field")), (False, "text"))
    recs = CAT.load()
    check("delete", [x["name"] for x in CAT.delete(recs, rec["prefix"] + " x")], [plain["name"], two["name"]])
    r = api.catalogue_delete({"name": rec["prefix"] + " x"})
    check("/api/catalogue-delete", (r["ok"], [x["name"] for x in CAT.load()]), (True, [plain["name"], two["name"]]))
    r = api.catalogue_list({})
    check("/api/catalogue lists the words only", (r["ok"], r["path"], [x["name"] for x in r["cupboards"]], "cabinet" in r["cupboards"][0]),
          (True, "cupboards.json", [plain["name"], two["name"]], False))
    r = api.catalogue_prefix({"job": job_to_dict(job), "cabinet": host.number})
    check("/api/catalogue-prefix", r["prefix"], rec["prefix"])
    sc = api.catalogue_scene({"name": plain["name"]})
    check("/api/catalogue-scene draws it from its own snapshots", (sc["ok"], len(sc["items"]) >= 1, len(sc["items"][0]["parts"]) > 0), (True, True, True))

    print("\nImport brings catalogue cupboards across")
    old = os.path.join(top, "Old")
    os.makedirs(os.path.join(old, "jobs"))
    with open(os.path.join(old, IMP.DEMO_EXE), "wb") as fh:
        fh.write(b"MZ not really an exe")
    shutil.copyfile(os.path.join(ROOT, "boards.json"), os.path.join(old, "boards.json"))
    shutil.copyfile(os.path.join(ROOT, "hardware.json"), os.path.join(old, "hardware.json"))
    # the old folder's catalogue: one identical to ours, one new, one a different cupboard under our name
    here_recs = CAT.load()
    diff = copy.deepcopy(here_recs[0]); diff["cabinet"]["height"] = diff["cabinet"]["height"] + 100
    newr = copy.deepcopy(here_recs[0]); newr["name"] = newr["prefix"] + " brand new"; newr["text"] = "brand new"
    CAT.save([copy.deepcopy(here_recs[0]), newr, diff], os.path.join(old, "cupboards.json"))
    here = os.path.join(top, "Here")
    os.makedirs(os.path.join(here, "jobs"))
    shutil.copyfile(os.path.join(ROOT, "boards.json"), os.path.join(here, "boards.json"))
    shutil.copyfile(os.path.join(ROOT, "hardware.json"), os.path.join(here, "hardware.json"))
    CAT.save(here_recs, os.path.join(here, "cupboards.json"))
    tgt = IMP.Target.at(here)
    got = IMP.scan(old, tgt)
    check("the preview names the three", sorted((i.name, i.action, i.to) for i in got["plan"].items if i.kind == "cupboard"),
          sorted([(here_recs[0]["name"], "identical", here_recs[0]["name"]),
                  (newr["name"], "new", ""),
                  (here_recs[0]["name"], "renamed", here_recs[0]["prefix"] + " (imported)")]))
    rep = IMP.run(old, tgt, signature=got["plan"].signature)
    check("Import writes the new and the renamed, counts them", (rep["ok"], rep["report"]["imported"]["cupboard"]), (True, 2))
    check("  the report line names them", "2 catalogue cupboards" in rep["report"]["text"], True)
    after = CAT.load(os.path.join(here, "cupboards.json"))
    check("  the catalogue here", [x["name"] for x in after],
          [here_recs[0]["name"], here_recs[1]["name"], newr["name"], here_recs[0]["prefix"] + " (imported)"])
    check("  the renamed one keeps its prefix first and the suffix in its text", after[3]["text"], "(imported)")
    again = IMP.run(old, tgt)
    check("a second Import brings nothing", again["report"]["imported"]["cupboard"], 0)

    print("\nthe demo build and the import UI check copy the file by name")
    with open(os.path.join(ROOT, "tools", "build_demo.py"), encoding="utf-8") as fh:
        check("build_demo.py DATA_FILES names cupboards.json", '"cupboards.json"' in fh.read(), True)
    with open(os.path.join(ROOT, "tools", "ui_check_import.py"), encoding="utf-8") as fh:
        check("ui_check_import.py copies it into its own app", '"cupboards.json"' in fh.read(), True)
    check("the file is at the repo root beside boards.json and hardware.json",
          os.path.exists(os.path.join(ROOT, "cupboards.json")) and CAT.CATALOGUE_FILE == "cupboards.json", True)


if __name__ == "__main__":
    raise SystemExit(main())
