"""The Plazaboard CSV: the right columns, the right numbers, the right edging names.

    python tools/check_export.py

Ruled with Rudolf on 28 September 2026 (brief
`Claude outputs/plaza-csv-columns-brief-2026-09-28.md`), against Plazaboard's own
files for the October job in `Sample Plaza cutlist and quote/`:

  * **Columns.** `Customer Number` (the designation, Panel.label) in FRONT, then
    Plazaboard's template exactly: `Component` is their item number 1..n,
    restarting in each file, and `Material` is the board id. Before this the
    code wrote the item number under Component and the designation under
    Material, and the board was never written at all. The header is read off
    their CSV itself and compared byte for byte. A zero edging total is `0`, as
    theirs is; there are no padding rows.
  * **One number per panel, no merging.** Every line stays a line. Identical
    panels share a number (1517 x3); different panels under one code get their
    own letter at birth (404a, 404b x3, 404c). "Different" is any difference
    but the qty (model.panel_signature). So no number sits on two different
    panels in any file, and the D13 warning never fires on a generated job.
  * **Edging names are the Boards tab's.** Every edge mat is a kind plus an
    Edging Name some board in that project carries, exactly as typed. Typed
    edging names on a cabinet are retired, and a bespoke or loose panel's typed
    name that matches no board is read as the same kind in the board it was cut
    beside. No WOOD anywhere; the October job reads BROOKHILL.
  * **October against Plazaboard.** As a multiset per board, every compared
    field matches apart from the cabinets in regen_check.KNOWN — and every
    other difference is listed and pinned here, each with its reason, so a new
    one fails rather than hides.

Test.json is live workshop data, so the facts pinned about it are asked of a
frozen copy, `tools/fixtures/Test_export.json` (Test.json at 201d360); the
general rules are asked of the live file as well.
"""
import csv
import difflib
import os
import sys
import tempfile
from collections import Counter

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.dirname(__file__))

from fixture_jobs import FIXTURES, job_file                                # noqa: E402
from regen_check import KNOWN                                              # noqa: E402

from app import api                                                        # noqa: E402
from cabinetgen.engine import generate_job                                 # noqa: E402
from cabinetgen.export_plaza import (HEADER, PLAZA_HEADER, rows_for,      # noqa: E402
                                     write_csvs)
from cabinetgen.model import (TAPE_PREFIX, edging_label, edging_parts,     # noqa: E402
                              material_token, panel_signature)
from cabinetgen.store import load                                          # noqa: E402
from cabinetgen.validate import validate                                   # noqa: E402
from jobs.wardrobe_oct2025 import JOB as OCT                               # noqa: E402

SAMPLE = os.path.join(ROOT, "Sample Plaza cutlist and quote")
PLAZA_FILES = {"MEL": "RUDOLPH MEL 211025.csv", "BROOKHILL": "RUDOLPH BRK 211025.csv",
               "BACK": "RUDOLPH MAS 211025.csv"}
FROZEN_TEST = "Test_export.json"

FAILS = []


def check(name, got, want):
    ok = got == want
    print(f"  {'ok  ' if ok else 'FAIL'}  {name}: {got!r}" + ("" if ok else f"  want {want!r}"))
    if not ok:
        FAILS.append(name)


def read_csv(path):
    with open(path, encoding="utf-8-sig", newline="") as fh:
        return list(csv.reader(fh))


def jobs_to_check():
    """Every job the checks know: the benchmark, the live Test.json, and every
    frozen fixture."""
    out = [("wardrobe_oct2025", OCT), ("Test.json (live)", load(job_file("Test.json")))]
    for name in sorted(os.listdir(FIXTURES)):
        if name.endswith(".json"):
            out.append((name, load(os.path.join(FIXTURES, name))))
    return out


def exported(job, tmp):
    """Write the job's CSVs exactly as /api/export does and read them back,
    keyed by board id."""
    panels = generate_job(job)
    out = {}
    for path in write_csvs(job, panels, os.path.join(tmp, job.name or "job")):
        board = os.path.basename(path)[len(job.name) + 1:-len(".csv")]
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
        out[board] = (read_csv(path), text)
    return panels, out


# ---------------------------------------------------------------------------
def header():
    print("the header: Customer Number, then Plazaboard's template byte for byte")
    theirs = read_csv(os.path.join(SAMPLE, PLAZA_FILES["MEL"]))[0]
    for fn in PLAZA_FILES.values():
        check(f"  {fn} carries the same template header",
              read_csv(os.path.join(SAMPLE, fn))[0], theirs)
    check("PLAZA_HEADER is theirs exactly", PLAZA_HEADER, theirs)
    check("HEADER is one column in front of it", HEADER, ["Customer Number"] + theirs)
    check("  JOB NO keeps its trailing space", HEADER[7], "JOB NO ")


def columns_and_numbers():
    print("\nevery job, every file: designation, item number, board id; no merging")
    with tempfile.TemporaryDirectory() as tmp:
        for name, job in jobs_to_check():
            panels, files = exported(job, tmp)
            by_board = {}
            for p in panels:
                by_board.setdefault(p.material, []).append(p)
            bad = []
            for board, (rows, text) in files.items():
                ps = by_board[board]
                body = rows[1:]
                if rows[0] != HEADER:
                    bad.append(f"{board}: header")
                if len(body) != len(ps):
                    bad.append(f"{board}: {len(body)} rows for {len(ps)} lines (merged or padded)")
                if [r[0] for r in body] != [p.label for p in ps]:
                    bad.append(f"{board}: column 1 is not the designations in order")
                if [r[1] for r in body] != [str(i) for i in range(1, len(body) + 1)]:
                    bad.append(f"{board}: column 2 is not 1..n")
                if {r[2] for r in body} != {board}:
                    bad.append(f"{board}: column 3 is not the board id")
                if any(r[17] == "0.0" for r in body):
                    bad.append(f"{board}: a zero edging total written 0.0")
                # no number on two DIFFERENT panels (qty aside), read off the file
                seen = {}
                for r in body:
                    qty = int(r[5] or 0)
                    holes = int(r[11]) // qty if r[11] and qty else 0
                    sig = (r[2], r[3], r[4], r[8], r[9], r[10], holes, r[12])
                    if seen.setdefault(r[0], sig) != sig:
                        bad.append(f"{board}: {r[0]} on two different panels")
                if "WOOD" in text.upper():
                    bad.append(f"{board}: WOOD on the order")
            # ... and the same off the panel list itself
            sigs = {}
            for p in panels:
                sigs.setdefault(p.label, set()).add(panel_signature(p))
            bad += [f"{lab} on {len(s)} different panels" for lab, s in sigs.items() if len(s) > 1]
            d13 = [i.where for i in validate(job, panels) if i.ref == "D13"]
            if d13:
                bad.append(f"D13 fires on {d13}")
            check(f"{name}: {sum(len(v[0]) - 1 for v in files.values())} lines in "
                  f"{len(files)} files", bad, [])


def edging_names():
    print("\nevery edge mat is a kind + an Edging Name a board in that project carries")
    with tempfile.TemporaryDirectory() as tmp:
        for name, job in jobs_to_check():
            names = {material_token(job.materials, k) for k in (job.materials or {})} - {""}
            prefixes = set(TAPE_PREFIX.values())
            wrong = set()
            _, files = exported(job, tmp)
            for board, (rows, _text) in files.items():
                for r in rows[1:]:
                    mat = r[12]
                    if not mat:
                        continue
                    kind, token = edging_parts(mat)
                    if kind is None or mat.split(" ", 1)[0] not in prefixes or token not in names:
                        wrong.add(mat)
            check(f"{name}", sorted(wrong), [])
    check("GREY's is written as the Boards tab has it, case included",
          sorted({p.edge_material for p in generate_job(load(job_file(FROZEN_TEST)))
                  if "Grey" in p.edge_material or "GREY" in p.edge_material}),
          ["1mm Grey", "2mm Grey", "PVC Grey"])


def test_json():
    print("\nTest.json (frozen as tools/fixtures/Test_export.json)")
    job = load(job_file(FROZEN_TEST))
    panels = generate_job(job)
    labels = [p.label for p in panels]
    check("404 is lettered at birth, identical ones sharing",
          [(p.label, p.qty, p.edge_l, p.edge_material) for p in panels
           if p.label.startswith("404")],
          [("404a", 1, 1, "PVC Grey"), ("404b", 1, 1, "PVC WHITE"),
           ("404b", 1, 1, "PVC WHITE"), ("404b", 1, 1, "PVC WHITE"),
           ("404c", 1, 2, "PVC WHITE")])
    check("1517 differs only in qty, so keeps its number, three lines",
          [p.label for p in panels if p.label.startswith("1517")], ["1517"] * 3)
    check("the codes that now carry letters",
          sorted({lab.rstrip("abc") for lab in labels if lab[-1] in "abc"
                  and lab.rstrip("abc")[-2:] == "04"}),
          ["1504", "204", "304", "404", "604", "704"])
    check("no WOOD anywhere on its cut list",
          [p.label for p in panels if "WOOD" in p.edge_material.upper()], [])
    check("the five cabinets still carry their typed names in the file, unread",
          sorted(c.number for c in job.cabinets
                 if (c.carcass_edge or "").endswith("WOOD")), [1, 2, 3, 4, 5])
    check("and each is edged in its own exterior board instead",
          {c.number: c.carcass_tape(job.materials) for c in job.cabinets
           if (c.carcass_edge or "").endswith("WOOD")},
          {1: "PVC BROOKHILL", 2: "PVC BROOKHILL", 3: "PVC BROOKHILL",
           4: "PVC Grey", 5: "PVC Grey"})

    print("\nthe Edging Colour dropdowns show the Edging Name, not the id")
    labels = {k: api._board_payload(job, k)["edging_label"] for k in job.materials}
    check("two boards sharing WHITE carry their id in brackets",
          (labels.get("WHITEMEL"), labels.get("BACK")), ("WHITE (WHITEMEL)", "WHITE (BACK)"))
    check("a name no other board shares is the name alone",
          (labels.get("GREY"), labels.get("BROOKHILL")), ("Grey", "BROOKHILL"))
    check("the payload names the Edging Name the order writes",
          api._board_payload(job, "GREY")["edging_name"], "Grey")
    check("and a board with none shows its id",
          edging_label({"X": {"name": "", "tape": ""}}, "X"), "X")


def october_typed_edging():
    print("\nthe October job's typed edging names, read through the Boards record")
    typed = [p for c in OCT.cabinets for p in c.bespoke] + list(OCT.loose)
    out = {(p.cabinet, p.code): p.edge_material for p in typed}
    gen = {(p.cabinet, p.code): p.edge_material for p in generate_job(OCT)
           if (p.cabinet, p.code) in out}
    touched = sorted(f"{c}{code}: {out[(c, code)]} -> {gen[(c, code)]}"
                     for (c, code) in out if out[(c, code)] != gen[(c, code)])
    for line in touched:
        print(f"        {line}")
    check("the typed panels this touched (WOOD -> BROOKHILL, kind kept)", touched, [
        "1301: PVC WOOD -> PVC BROOKHILL", "1302: PVC WOOD -> PVC BROOKHILL",
        "1307: 2mm WOOD -> 2mm BROOKHILL", "2408: PVC WOOD -> PVC BROOKHILL",
        "305b: PVC WOOD -> PVC BROOKHILL", "505b: PVC WOOD -> PVC BROOKHILL",
        "608: 2mm WOOD -> 2mm BROOKHILL", "701a: PVC WOOD -> PVC BROOKHILL",
        "701b: PVC WOOD -> PVC BROOKHILL", "701c: PVC WOOD -> PVC BROOKHILL",
        "702: PVC WOOD -> PVC BROOKHILL", "703: PVC WOOD -> PVC BROOKHILL",
        "705: PVC WOOD -> PVC BROOKHILL", "707: 2mm WOOD -> 2mm BROOKHILL"])
    check("and the job itself is untouched: they still say WOOD in the fixture",
          sorted({p.edge_material for p in typed if p.edge_material}),
          ["2mm WOOD", "PVC WOOD"])
    panels = generate_job(OCT)
    check("the six support codes lettered, as Rudolf agreed",
          sorted({p.label.rstrip("abc") for p in panels if p.label[-1] in "abc"
                  and p.code[:2] == "04"}),
          ["104", "2704", "2804", "2904", "3004", "404"])
    check("lines per file, one per line sent (Plazaboard kept 112 / 35 / 19)",
          {m: sum(1 for p in panels if p.material == m) for m in PLAZA_FILES},
          {"MEL": 111, "BROOKHILL": 35, "BACK": 19})


# --- October against Plazaboard's own files ---------------------------------
FIELD_NAMES = ("Length", "Width", "qty", "Grain", "edge l", "edge w", "holes",
               "edge mat", "edge flags", "edging metres")


def fields(row):
    """The compared fields of a row in Plazaboard's layout (Component first)."""
    return (str(row[2]), str(row[3]), str(row[4]), str(row[7]), str(row[8]),
            str(row[9]), str(row[10]), str(row[11]).upper(),
            "".join("1" if x else "-" for x in row[12:16]),
            "%.3f" % float(row[16] or 0))


def size(f):
    return tuple(sorted(f[:2]))


def compare_board(board, fn, panels):
    """Every difference between our lines and theirs for one board, outside
    the KNOWN cabinets, as short strings. Their file carries no designation, so
    a line of theirs is put to a cabinet by aligning the two files on size —
    theirs follows the sheet sent, cabinet by cabinet — and only to decide
    whether it belongs to a KNOWN cabinet; the comparison itself is a multiset."""
    theirs = [(r[0], fields(r)) for r in read_csv(os.path.join(SAMPLE, fn))[1:] if r[2]]
    ps = [p for p in panels if p.material == board]
    ours = list(zip(ps, [fields(r[1:]) for r in rows_for(ps)]))
    sm = difflib.SequenceMatcher(None, [size(f) for _, f in ours],
                                 [size(f) for _, f in theirs], autojunk=False)
    cab_of = {}
    for _op, i1, i2, j1, j2 in sm.get_opcodes():
        for k, j in enumerate(range(j1, j2)):
            i = i1 + min(k, i2 - i1 - 1) if i2 > i1 else max(i1 - 1, 0)
            cab_of[j] = ours[i][0].cabinet
    o = [(p.label, f) for p, f in ours if p.cabinet not in KNOWN]
    t = [(n, f) for j, (n, f) in enumerate(theirs) if cab_of[j] not in KNOWN]
    tk = [(n, f) for j, (n, f) in enumerate(theirs) if cab_of[j] in KNOWN]
    # the multiset: what matches exactly, outside the KNOWN cabinets
    common = Counter(f for _, f in o) & Counter(f for _, f in t)
    ro, rt = list(o), list(t)
    for f in common.elements():
        ro.remove(next(x for x in ro if x[1] == f))
        rt.remove(next(x for x in rt if x[1] == f))
    out = []
    for lab, f in ro:
        # the same size among theirs, in order; else a line the alignment put
        # to a KNOWN cabinet that is really this one (a loose panel sent out of
        # our order), exactly first
        m = (next((x for x in rt if size(x[1]) == size(f)), None)
             or next((x for x in tk if x[1] == f), None)
             or next((x for x in tk if size(x[1]) == size(f)), None))
        if m:
            (rt if m in rt else tk).remove(m)
            diff = [FIELD_NAMES[i] for i in range(len(f)) if f[i] != m[1][i]]
            out.append(f"{lab} ~ item {m[0]}: {', '.join(diff)}")
        else:
            out.append(f"{lab} ours only: {f[0]}x{f[1]} x{f[2]}")
    out += [f"item {n} theirs only: {f[0]}x{f[1]} x{f[2]}" for n, f in rt]
    return out


def edge_mats_in_known(panels):
    """Inside the KNOWN cabinets the SIZES are the finding; what the edging is
    called there is not, so it is listed too rather than hidden by KNOWN."""
    out = Counter()
    for board, fn in PLAZA_FILES.items():
        theirs = Counter((size(fields(r)), fields(r)[2], fields(r)[7])
                         for r in read_csv(os.path.join(SAMPLE, fn))[1:] if r[2])
        for p in panels:
            if p.material != board or p.cabinet not in KNOWN or not p.edge_material:
                continue
            f = fields(rows_for([p])[0][1:])
            if (size(f), f[2], f[7]) not in theirs:
                alt = [k[2] for k in theirs if k[0] == size(f) and k[1] == f[2]]
                if alt:
                    out[f"{p.label}: ours {p.edge_material}, theirs {alt[0]}"] += 1
    return sorted(out)


# Every difference outside regen_check.KNOWN, each with its reason. A new one,
# or one of these going away, fails the check: look at it before changing this.
PLAZA_DIFFERENCES = {
    "MEL": [
        # Their file stops writing the four edge-flag columns from item 29 on,
        # though edge l still says 1 and the metres are the same. Theirs, not ours.
        *[f"{lab} ~ item {n}: edge flags" for lab, n in (
            ("501", 31), ("502", 32), ("503", 33), ("505", 35), ("509", 37),
            ("505b", 36), ("701a", 38), ("705", 43), ("1101", 59), ("1102", 60),
            ("1103", 61), ("1105", 63), ("1109", 64), ("1201", 65), ("1202", 66),
            ("1203", 67), ("1205", 69), ("1209", 70), ("2501", 76), ("2502", 77),
            ("2503", 78), ("2505", 80), ("2601", 81), ("2602", 82), ("2603", 83),
            ("2605", 85))],
        # Cabinet 7's corner sides, top and bottom are defined edged on one long
        # edge (the job's bespoke panels); Plazaboard's lines carry no edging.
        "701b ~ item 39: edge l, edge mat, edge flags, edging metres",
        "701c ~ item 40: edge l, edge mat, edge flags, edging metres",
        "702 ~ item 41: edge l, edge mat, edge flags, edging metres",
        "703 ~ item 42: edge l, edge mat, edge flags, edging metres",
        # The loose MEL filler strip, sent after cabinet 14 on the sheet: the
        # same line, flags dropped as above.
        "2408 ~ item 75: edge flags",
        # A full 2730 x 1300 line at the end of their file, in no line we sent.
        "item 112 theirs only: 2730x1300 x1",
    ],
    "BROOKHILL": [
        # W2: the 2882 filler exceeds the board; Plazaboard cut it 2730.
        "1808 ours only: 2882x50 x1",
        "item 31 theirs only: 2730x50 x1",
        "item 37 theirs only: 2730x1300 x1",
    ],
    "BACK": [
        # The backs are grain-free; they keyed these four the other way round.
        "1106 ~ item 11: Length, Width",
        "1206 ~ item 12: Length, Width",
        "2506 ~ item 14: Length, Width",
        "2606 ~ item 15: Length, Width",
    ],
}

# Inside KNOWN cabinets: Plazaboard keyed every MEL edging as PVC BROOKHILL,
# including the white-edged supports of 27-29, which our job edges WHITE. The
# drawer boxes (118, 119, 2719, 3019, 418, 419) dropped out on 29 September
# 2026: a box is edged in the exterior board's PVC by default now, BROOKHILL,
# which is what Plazaboard keyed. Supports keep their own Edging Colour.
EDGE_MATS_IN_KNOWN = sorted(f"{lab}: ours PVC WHITE, theirs PVC BROOKHILL" for lab in (
    "2704c", "2804c", "2904c"))


def october_vs_plazaboard():
    print("\nOctober against Plazaboard's own files, outside regen_check.KNOWN")
    panels = generate_job(OCT)
    for board, fn in PLAZA_FILES.items():
        got = compare_board(board, fn, panels)
        print(f"    {fn}: {len(got)} differences")
        for line in got:
            print(f"        {line}")
        check(f"  {board}: exactly the listed differences",
              sorted(got), sorted(PLAZA_DIFFERENCES[board]))
    known = edge_mats_in_known(panels)
    print("    edging names inside the KNOWN cabinets (listed, not hidden):")
    for line in known:
        print(f"        {line}")
    check("  and those are exactly the listed ones", known, EDGE_MATS_IN_KNOWN)


def main():
    print(__doc__.strip().splitlines()[0])
    header()
    columns_and_numbers()
    edging_names()
    test_json()
    october_typed_edging()
    october_vs_plazaboard()
    print()
    if FAILS:
        print(f"{len(FAILS)} FAILED: " + "; ".join(FAILS))
        sys.exit(1)
    print("ALL OK")


if __name__ == "__main__":
    main()
