"""Import project, and renaming a project (brief of 3 October 2026).

    python tools/check_import.py

Temp folders only — never the live `jobs/`, `boards.json`, `hardware.json` or
`Pictures/`. Two app folders are built from the frozen fixtures:

  * HERE — the app being imported into: Test.json (tools/fixtures/Test_export.json),
    Shared.json, the repo's boards.json, hardware.json and pictures;
  * an OLD demo folder, unzipped the way a demo unzips — an outer folder holding
    `Cupboard App Demo/` (with `Cupboard App Demo.exe` beside `jobs/`) and
    `READ ME FIRST.txt` — whose work is:
      - Test.json (tools/fixtures/Test_3d.json): a different job of the same name;
      - Shared.json, identical to HERE's;
      - Old.json, a room saved as a wall chain (before Phase 1);
      - Broken.json, not JSON; Newer.json, a field this app does not know;
      - jobs/_deleted/Gone.json, output/, output/demo-seen.txt — never read;
      - boards.json: the repo's, but GREY grained, coloured and pictured
        differently (a conflict), and a new board OAK;
      - hardware.json: GELMAR45 at another price and setback (a conflict), and a
        new runner;
      - Pictures/: Brookhill.png identical, Storm Grey.jpg different bytes (a
        conflict), Oak.jpg new.

What is pinned (the brief's Checks section):

  * the folder is found from the outer or the inner folder; anything else, or
    this app's own folder, is refused saying what was looked for;
  * the preview lists every item correctly and writes NOTHING;
  * Import writes exactly the new and renamed items, and nothing else;
  * the conflicting board's imported jobs name the new id, and cost exactly what
    they cost in the old folder — loaded there and here through the app's own
    Load (the cost DIFFERS if the job is not re-pointed, so the check bites);
  * the broken job is reported and absent; the newer job is imported as it
    stands and said to be newer; the chain room is migrated;
  * the old folder is byte-identical afterwards;
  * importing the same folder twice brings nothing the second time;
  * a preview the folder no longer matches is refused;
  * the raw-JSON re-pointing (a newer job's) agrees with `rename_board_in_job`.
"""
import copy
import hashlib
import json
import os
import shutil
import sys
import tempfile

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fixture_jobs import job_file                                          # noqa: E402
from app import api                                                         # noqa: E402
from cabinetgen import boards as B                                          # noqa: E402
from cabinetgen import hardware as H                                        # noqa: E402
from cabinetgen import importer as IMP                                      # noqa: E402
from cabinetgen.engine import generate_job                                  # noqa: E402
from cabinetgen.store import job_from_dict, job_to_dict                     # noqa: E402

FAILS = []


def check(name, got, want):
    ok = got == want
    print(("PASS  " if ok else "FAIL  ") + name + ("" if ok else f"\n        got  {got!r}\n        want {want!r}"))
    if not ok:
        FAILS.append(name)


def tree(folder):
    """Every file under `folder` -> its sha1: what 'unchanged' means."""
    out = {}
    for base, _dirs, files in os.walk(folder):
        for n in files:
            p = os.path.join(base, n)
            with open(p, "rb") as fh:
                out[os.path.relpath(p, folder).replace("\\", "/")] = hashlib.sha1(fh.read()).hexdigest()
    return out


def read(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def write(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if isinstance(data, (bytes, bytearray)):
        with open(path, "wb") as fh:
            fh.write(data)
        return
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(data if isinstance(data, str) else json.dumps(data, indent=2, ensure_ascii=False))


# --- the two folders ----------------------------------------------------------

def make_here(top):
    here = os.path.join(top, "Here")
    test = read(job_file("Test_export.json"))
    write(os.path.join(here, "jobs", "Test.json"), test)
    shared = read(job_file("Test_Build.json"))
    shared["name"] = "Shared"
    write(os.path.join(here, "jobs", "Shared.json"),
          json.dumps(job_to_dict(job_from_dict(shared)), indent=2, ensure_ascii=False))
    shutil.copyfile(os.path.join(ROOT, "boards.json"), os.path.join(here, "boards.json"))
    shutil.copyfile(os.path.join(ROOT, "hardware.json"), os.path.join(here, "hardware.json"))
    shutil.copytree(os.path.join(ROOT, "Pictures"), os.path.join(here, "Pictures"))
    return here


LEGACY_ROOM = {"name": "Old room", "ceiling": 2400, "offset_depth": 600, "closed": True,
               "walls": [{"id": w, "length": n, "offset_start": 0, "offset_end": 0,
                          "openings": [], "obstructions": []}
                         for w, n in (("A", 3000), ("B", 2000), ("C", 3000), ("D", 2000))]}


def make_old(top):
    outer = os.path.join(top, "Cupboard App Demo 2026-09-30")
    app = os.path.join(outer, IMP.DEMO_FOLDER)
    write(os.path.join(outer, "READ ME FIRST.txt"), "Cupboard App — Demo\n")
    write(os.path.join(app, IMP.DEMO_EXE), b"MZ not really an exe")
    write(os.path.join(app, "jobs", "Test.json"), read(job_file("Test_3d.json")))
    shared = read(job_file("Test_Build.json"))
    shared["name"] = "Shared"
    write(os.path.join(app, "jobs", "Shared.json"), shared)     # old format: same after migration
    old = read(job_file("Test_Build.json"))
    old["name"] = "Old"
    old["room"] = LEGACY_ROOM
    write(os.path.join(app, "jobs", "Old.json"), old)
    write(os.path.join(app, "jobs", "Broken.json"), "{ this is not json")
    newer = read(job_file("Test_Build.json"))
    newer["name"] = "Newer"
    newer["cabinets"][0]["hinge_brand"] = "Blum"
    newer["mood_board"] = ["oak", "brass"]
    write(os.path.join(app, "jobs", "Newer.json"), newer)
    # a board the old library no longer has, whose own copy in the job differs
    # from this library's board of that id
    own = read(job_file("Test_Build.json"))
    own["name"] = "Own"
    casc = next(b for b in read(os.path.join(ROOT, "boards.json"))["boards"] if b["id"] == "CASCADE")
    own["materials"]["CASCADE"] = {"board": casc["name"], "name": casc["name"],
                                   "tape": casc["tape"], "thickness": 16, "grain": "plain",
                                   "price": 777.0, "picture": casc["picture"],
                                   "has_edging": True, "edging_kinds": ["pvc", "1mm", "2mm"],
                                   "colour": casc["colour"]}
    own["boards"] = list(own.get("boards") or own["materials"]) + ["CASCADE"]
    own["cabinets"][0]["exterior_board"] = "CASCADE"
    write(os.path.join(app, "jobs", "Own.json"), own)
    write(os.path.join(app, "jobs", "_deleted", "Gone.json"), read(job_file("Test_Panels.json")))
    write(os.path.join(app, "output", "demo-seen.txt"), "2026-11-02")
    write(os.path.join(app, "output", "Test", "cutlist", "Test_GREY.csv"), "x")

    lib = read(os.path.join(ROOT, "boards.json"))
    for b in lib["boards"]:
        if b["id"] == "GREY":
            b["grain"] = "grain"
            b["colour"] = "#556070"
            b["tape"] = ""                  # its edging named off its board name
    lib["boards"] = [b for b in lib["boards"] if b["id"] != "CASCADE"]
    lib["boards"].append({"id": "OAK", "name": "Natural Oak", "tape": "Oak", "thickness": 16,
                          "grain": "grain", "price": 990.0, "picture": "Pictures/Oak.jpg",
                          "has_edging": True, "edging_kinds": ["pvc", "1mm"],
                          "colour": "#b98b55"})
    write(os.path.join(app, "boards.json"), lib)

    hw = read(os.path.join(ROOT, "hardware.json"))
    hw["runners"][0]["price"] = 85.0
    hw["runners"][0]["setback"] = 3
    hw["runners"].append(dict(hw["runners"][0], id="SOFT45", name="Soft-close 45",
                              price=150.0))
    write(os.path.join(app, "hardware.json"), hw)

    pics = os.path.join(ROOT, "Pictures")
    write(os.path.join(app, "Pictures", "Brookhill.png"),
          open(os.path.join(pics, "Brookhill.png"), "rb").read())
    write(os.path.join(app, "Pictures", "Storm Grey.jpg"), b"\xff\xd8 another storm grey")
    write(os.path.join(app, "Pictures", "Oak.jpg"), b"\xff\xd8 oak")
    return outer, app


def point_api(root):
    """Every path the app reads, at one folder."""
    api.ROOT = root
    api.JOBS_DIR = os.path.join(root, "jobs")
    api.PICTURES_DIR = os.path.join(root, "Pictures")
    api.OUT_DIR = os.path.join(root, "output")
    api.DELETED_DIR = os.path.join(api.JOBS_DIR, "_deleted")
    B.LIBRARY = os.path.join(root, "boards.json")
    H.LIBRARY = os.path.join(root, "hardware.json")


def loaded_cost(root, name):
    """Load a job through the app's own Load in the app folder `root`, and cost
    it: what the operator sees on opening it there."""
    point_api(root)
    r = api.job_load({"path": name})
    assert r["ok"], r
    job = job_from_dict(r["job"])
    panels = generate_job(job)
    return api._totals(job, panels)["cost"], job


# --- the checks -----------------------------------------------------------------

def finding(top, here, outer, app):
    print("\n-- which folder")
    check("the outer demo folder finds the inner one",
          IMP.find_folder(outer, here), {"ok": True, "folder": os.path.abspath(app)})
    check("the inner folder is found as itself",
          IMP.find_folder(app, here), {"ok": True, "folder": os.path.abspath(app)})
    plain = os.path.join(top, "Holiday photos")
    write(os.path.join(plain, "beach.jpg"), b"x")
    r = IMP.find_folder(plain, here)
    check("a folder that is not an app folder is refused", r["ok"], False)
    check("... saying what it looked for",
          all(s in r["error"] for s in ("jobs\\", "readable job", IMP.DEMO_EXE)), True)
    check("this app's own folder is refused", IMP.find_folder(here, here)["ok"], False)
    check("no folder at all is refused", IMP.find_folder(os.path.join(top, "nope"), here)["ok"], False)
    bare = os.path.join(top, "Bare demo")
    write(os.path.join(bare, IMP.DEMO_EXE), b"MZ")
    os.makedirs(os.path.join(bare, "jobs"))
    check("an empty jobs\\ beside the demo exe is still a demo folder",
          IMP.find_folder(bare, here)["ok"], True)


def preview(here, outer, app):
    print("\n-- the preview writes nothing")
    before_here, before_old = tree(here), tree(os.path.dirname(app))
    point_api(here)
    r = api.import_scan({"path": outer})
    check("the scan answers", r["ok"], True)
    check("the scan wrote nothing here", tree(here), before_here)
    check("the scan wrote nothing in the old folder", tree(os.path.dirname(app)), before_old)
    got = {(i["kind"], i["name"]): (i["action"], i["to"]) for i in r["items"]}
    want = {
        ("picture", "Brookhill.png"): ("identical", "Brookhill.png"),
        ("picture", "Oak.jpg"): ("new", ""),
        ("picture", "Storm Grey.jpg"): ("renamed", "Storm Grey (imported).jpg"),
        ("board", "SUPER WHITE MELAMINE 16MM"): ("identical", "SUPER WHITE MELAMINE 16MM"),
        ("board", "BROOKHILL FUSION"): ("identical", "BROOKHILL FUSION"),
        ("board", "WHITE MASONITE BACKING 3MM"): ("identical", "WHITE MASONITE BACKING 3MM"),
        ("board", "STORMGREY"): ("renamed", "STORMGREY (imported)"),
        ("board", "Cascade Grey"): ("renamed", "Cascade Grey (imported)"),
        ("board", "Natural Oak"): ("new", ""),
        ("runner", "Gelmar 45 mm full-extension ball-bearing"):
            ("renamed", "Gelmar 45 mm full-extension ball-bearing (imported)"),
        ("runner", "Soft-close 45"): ("new", ""),
        ("job", "Broken"): ("broken", ""),
        ("job", "Newer"): ("new", ""),
        ("job", "Old"): ("new", ""),
        ("job", "Own"): ("new", ""),
        ("job", "Shared"): ("identical", "Shared"),
        ("job", "Test"): ("renamed", "Test (imported)"),
    }
    check("every item, and what will happen to it", got, want)
    check("_deleted/ is not offered", any(i["name"] == "Gone" for i in r["items"]), False)
    newer = next(i for i in r["items"] if i["name"] == "Newer")
    check("the newer job is said to be from a newer version",
          "newer version" in newer["note"] and "hinge_brand" in newer["note"], True)
    test = next(i for i in r["items"] if i["name"] == "Test")
    grey = next(i for i in r["items"] if i["name"] == "STORMGREY")
    check("Test's note names the board it is re-pointed to",
          f"GREY → {grey['to_id']}" in test["note"], True)
    check("the counts", r["counts"], {"new": 6, "identical": 5, "renamed": 5, "broken": 1})
    return r


def importing(here, outer, app, scan):
    print("\n-- Import")
    old_tree = tree(os.path.dirname(app))
    before = tree(here)
    point_api(here)
    r = api.import_run({"path": outer, "signature": scan["signature"]})
    check("Import answers", r["ok"], True)
    rep = r["report"]
    check("the report's counts", rep["imported"],
          {"job": 4, "board": 3, "runner": 2, "picture": 2})
    check("the report's first line",
          rep["text"].split("\n")[0],
          "Imported 4 projects, 3 boards, 2 runners, 2 pictures. Skipped 5 identical. "
          "Renamed: Test → Test (imported), STORMGREY → STORMGREY (imported), "
          "Cascade Grey → Cascade Grey (imported), "
          "Gelmar 45 mm full-extension ball-bearing → Gelmar 45 mm full-extension ball-bearing "
          "(imported), Storm Grey.jpg → Storm Grey (imported).jpg.")
    check("the broken job is named with its reason",
          any(n == "Broken.json" and "JSONDecodeError" in why for n, why in rep["failed"]), True)
    check("the newer job is named as newer", rep["newer"], ["Newer.json"])
    check("the old folder is byte-identical afterwards", tree(os.path.dirname(app)), old_tree)

    after = tree(here)
    added = sorted(set(after) - set(before))
    changed = sorted(k for k in before if before[k] != after.get(k))
    check("exactly the new and renamed files are written",
          added, ["Pictures/Oak.jpg", "Pictures/Storm Grey (imported).jpg",
                  "jobs/Newer.json", "jobs/Old.json", "jobs/Own.json",
                  "jobs/Test (imported).json"])
    check("... and the two libraries, nothing else changed", changed,
          ["boards.json", "hardware.json"])
    check("the broken job is absent", os.path.exists(os.path.join(here, "jobs", "Broken.json")), False)
    check("Test.json here is untouched", before["jobs/Test.json"], after["jobs/Test.json"])

    lib = B.load(os.path.join(here, "boards.json"))
    grey2 = next(b for b in lib if b.name == "STORMGREY (imported)")
    check("the renamed board has a new id", grey2.id not in ("GREY", ""), True)
    check("... its picture is the renamed picture", grey2.picture,
          "Pictures/Storm Grey (imported).jpg")
    check("... and keeps its edging name (it was named off the board name)",
          grey2.token, "STORMGREY")
    check("the library's own GREY is untouched",
          B.find(lib, "GREY").grain, "plain")
    oak = B.find(lib, "OAK")
    check("the new board comes in as it was", (oak.name, oak.picture, oak.price),
          ("Natural Oak", "Pictures/Oak.jpg", 990.0))
    rl = H.load(os.path.join(here, "hardware.json"))
    g2 = next(x for x in rl if x.name.endswith("(imported)"))
    check("the renamed runner has a new id and its own record",
          (g2.id != "GELMAR45", g2.price, g2.setback), (True, 85.0, 3))
    check("the library's own GELMAR45 is untouched",
          H.find(rl, "GELMAR45").setback, 2)

    imp = read(os.path.join(here, "jobs", "Test (imported).json"))
    check("the imported job is named as its file", imp["name"], "Test (imported)")
    check("it names the new board id, not GREY",
          (grey2.id in imp["materials"], "GREY" in imp["materials"]), (True, False))
    named = set()
    for c in imp["cabinets"]:
        named |= B.cabinet_board_ids(c)
    check("no cabinet still names GREY", "GREY" in named, False)
    check("its runner copy and its cabinets name the new runner",
          (list(imp["runners"]), {c.get("runner") for c in imp["cabinets"] if c.get("runner")}),
          ([g2.id], {g2.id}))
    check("its runner copy is shown under the new name", imp["runners"][g2.id]["name"], g2.name)
    src_test = read(os.path.join(app, "jobs", "Test.json"))
    check("its captured prices are its own",
          imp["materials"][grey2.id]["price"], src_test["materials"]["GREY"]["price"])

    print("\n-- the cost, loaded there and here")
    old_cost, old_job = loaded_cost(app, "Test.json")
    new_cost, new_job = loaded_cost(here, "Test (imported).json")
    check("the imported job costs exactly what it cost in the old folder", new_cost, old_cost)
    check("... and it is cut from a grained board here too",
          new_job.materials[grey2.id]["grain"], "grain")
    # The same job NOT re-pointed, opened here: this library's plain GREY.
    point_api(here)
    plain = job_from_dict(read(os.path.join(app, "jobs", "Test.json")))
    api.refresh_from_library(plain)
    plain_cost = api._totals(plain, generate_job(plain))["cost"]
    check("(without the re-pointing it would cost something else)", plain_cost != old_cost, True)
    check("the same panels, the same sizes", sorted((p.label, p.length, p.width, p.qty)
                                                    for p in generate_job(new_job)),
          sorted((p.label, p.length, p.width, p.qty) for p in generate_job(old_job)))

    casc = next(b for b in lib if b.name == "Cascade Grey (imported)")
    check("a job's own copy unlike this library's board comes in as a board of its own",
          (casc.grain, casc.price, B.find(lib, "CASCADE").grain), ("plain", 777.0, "grain"))
    own = read(os.path.join(here, "jobs", "Own.json"))
    check("... and the job is re-pointed to it",
          (casc.id in own["materials"], "CASCADE" in own["materials"],
           own["cabinets"][0]["exterior_board"]), (True, False, casc.id))
    check("... and costs here what it cost there",
          loaded_cost(here, "Own.json")[0], loaded_cost(app, "Own.json")[0])

    old = read(os.path.join(here, "jobs", "Old.json"))
    check("the chain room is migrated: walls are points",
          [sorted(k for k in w if k in ("x0", "y0", "x1", "y1", "length")) for w in old["room"]["walls"]],
          [["x0", "x1", "y0", "y1"]] * 4)
    check("... and closed (the walk returns)", "closed" in old["room"], False)
    newer = read(os.path.join(here, "jobs", "Newer.json"))
    check("the newer job keeps the fields this app does not know",
          (newer["cabinets"][0].get("hinge_brand"), newer.get("mood_board")),
          ("Blum", ["oak", "brass"]))

    print("\n-- the same folder again")
    point_api(here)
    before2 = tree(here)
    again = api.import_scan({"path": app})
    check("the second preview: nothing new, nothing renamed",
          sorted({i["action"] for i in again["items"]}), ["broken", "identical"])
    r2 = api.import_run({"path": app, "signature": again["signature"]})
    check("the second Import brings nothing", r2["report"]["imported"],
          {"job": 0, "board": 0, "runner": 0, "picture": 0})
    check("... and writes nothing", tree(here), before2)
    check("... and says so", r2["report"]["text"].startswith("Nothing new to import."), True)

    print("\n-- a preview the folder no longer matches")
    write(os.path.join(app, "jobs", "Later.json"), read(job_file("Test_Build.json")))
    r3 = api.import_run({"path": app, "signature": again["signature"]})
    check("refused", r3["ok"], False)
    check("... writing nothing", tree(here), before2)
    os.remove(os.path.join(app, "jobs", "Later.json"))


def raw_repoint():
    print("\n-- a newer job's re-pointing agrees with rename_board_in_job")
    for name in ("Test_export.json", "Test_Panels.json", "Corner Unit Test.json"):
        raw = read(job_file(name))
        job = job_from_dict(copy.deepcopy(raw))
        B.rename_board_in_job(job, "GREY", "NEWGREY")
        d = job_to_dict(job_from_dict(copy.deepcopy(raw)))
        for c in d["cabinets"]:
            B.map_cabinet_board_ids(c, lambda b: "NEWGREY" if b == "GREY" else b)
        d["materials"] = {("NEWGREY" if k == "GREY" else k): v for k, v in d["materials"].items()}
        d["boards"] = ["NEWGREY" if b == "GREY" else b for b in d["boards"]]
        check(f"{name}: the raw rewrite is rename_board_in_job", d, job_to_dict(job))


def main():
    top = tempfile.mkdtemp(prefix="check_import_")
    saved = (api.ROOT, api.JOBS_DIR, api.PICTURES_DIR, api.OUT_DIR, api.DELETED_DIR,
             B.LIBRARY, H.LIBRARY)
    live = tree(os.path.join(ROOT, "jobs")), tree(os.path.join(ROOT, "Pictures"))
    try:
        here = make_here(top)
        outer, app = make_old(top)
        finding(top, here, outer, app)
        scan = preview(here, outer, app)
        importing(here, outer, app, scan)
        raw_repoint()
    finally:
        (api.ROOT, api.JOBS_DIR, api.PICTURES_DIR, api.OUT_DIR, api.DELETED_DIR,
         B.LIBRARY, H.LIBRARY) = saved
        shutil.rmtree(top, ignore_errors=True)
    check("the live jobs/ and Pictures/ were never touched",
          (tree(os.path.join(ROOT, "jobs")), tree(os.path.join(ROOT, "Pictures"))), live)
    print(f"\n{len(FAILS)} failed" if FAILS else "\nall passed")
    return 1 if FAILS else 0


if __name__ == "__main__":
    raise SystemExit(main())
