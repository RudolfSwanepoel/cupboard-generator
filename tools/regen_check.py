"""Regenerate the October 2025 wardrobe and diff it against the cut list that was sent.

    python tools/regen_check.py ["..\\Wardrobes\\R Swanepoel Cutlist.xlsx"]

Differences are expected and are the point. Each one should fall into one of:
  STANDARD   the 6 mm engagement decision, which resized every back and drawer base
  FINDING    a logged error in the original sheet (W1-W14 in docs/RULES.md)
  NEW        neither — the engine is wrong, or the job definition is
"""
import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from cabinetgen.engine import generate_job                 # noqa: E402
from cabinetgen.export_plaza import estimate_cost, summarise  # noqa: E402
from cabinetgen import nest as N                            # noqa: E402
from cabinetgen.validate import blocking, report, validate  # noqa: E402
from jobs.wardrobe_oct2025 import JOB                      # noqa: E402
from cabinetgen.model import resolve_board                 # noqa: E402

DEFAULT_CUTLIST = os.path.join(
    os.path.dirname(__file__), "..", "..", "Wardrobes", "R Swanepoel Cutlist.xlsx")

# The sheet says "Wood"; the job called it DECOR, which is BROOKHILL since the
# library rename. Resolved through the job so the diff compares like with like.
SHEET_TO_MAT = {"MEL": "MEL", "Wood": resolve_board(JOB.materials, "DECOR"),
                "Backing": "BACK"}

# Cabinets whose original rows are known to be wrong. Keyed by cabinet number.
KNOWN = {
    1: "W3 — drawer front/base differ from cabinet 4 by 1 mm",
    4: "W3 — drawer front/base differ from cabinet 1 by 1 mm",
    8: "W4 — bottom cut 468x501 against a top of 468x500",
    9: "W4 — bottom cut 468x501 against a top of 468x500",
    10: "W4 — bottom cut 468x501 against a top of 468x500",
    14: "W1 — doors specced 4 pot holes, rule gives 2",
    27: "W6/W15 — back cut 440 wide (rule gives 480); melamine drawer base cut 377x520",
    30: "W5 — faces cut 178 each (+ runner standardised 340->350)",
    28: "STANDARD — back 778 as cut, 780 under the 6 mm engagement rule",
    29: "STANDARD — back 778 as cut, 780 under the 6 mm engagement rule",
}


def load_cutlist(path):
    import openpyxl
    ws = openpyxl.load_workbook(path, data_only=True).worksheets[0]
    rows = []
    for r in ws.iter_rows(min_row=2, values_only=True):
        if r[0] is None:
            continue
        lab = str(r[0])
        rows.append({
            "cabinet": int(lab[:-2]), "code": lab[-2:],
            "material": SHEET_TO_MAT.get(r[1], r[1]),
            "length": r[2], "width": r[3], "qty": r[4] or 0,
        })
    return rows


def key(d):
    """Backs and bases carry no grain, so orientation is not a difference."""
    a, b = d["length"], d["width"]
    if d["material"] == "BACK":
        a, b = max(a, b), min(a, b)
    return (d["material"], a, b)


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_CUTLIST
    panels = generate_job(JOB)

    print("=" * 78)
    print("VALIDATION")
    print("=" * 78)
    issues = validate(JOB, panels)
    print(report(issues))
    print(f"\nexport would be {'BLOCKED' if blocking(issues) else 'allowed'}")

    print()
    print("=" * 78)
    print("SUMMARY")
    print("=" * 78)
    nested = N.nest_job(N.nestable(panels, JOB.std), JOB.std)
    s = summarise(JOB, panels, nested)
    for mat, v in sorted(s["materials"].items()):
        print(f"  {mat:<6} {v['panels']:>4} panels  {v['area_m2']:>7.2f} m2  "
              f"{v['net_sheets']:>6.2f} net sheets  ~{v['est_boards']} boards")
    print(f"  pot holes {s['potholes']}")
    if N.NEST_REJECTS:
        print(f"  NOT NESTED (too big for a board): {N.NEST_REJECTS}")
    for k, v in sorted(s["edging"].items()):
        print(f"  edging {k:<14} {v:>8.3f} m")
    est = estimate_cost(JOB, s)
    print(f"  estimated total incl VAT  R {est['total_incl_vat']:,.2f}")
    print("  (quotation VRG_SOQ497999 was R 28,322.75 for 9 DECOR / 18 MEL / 6 BACK)")

    # One job, one folder — the same rule /api/export follows, so a second job's
    # sheets can never land on this one's.
    outdir = os.path.join(os.path.dirname(__file__), "..", "output", JOB.name)
    os.makedirs(outdir, exist_ok=True)
    for mat, sheets in nested.items():
        N.write_svg(sheets, os.path.join(outdir, f"nest_{mat}.svg"), title=mat)
    print(f"  sheet layouts written to output/{JOB.name}/nest_*.svg")

    if not os.path.exists(path):
        print(f"\n! cut list not found at {path} — skipping the diff")
        return
    print()
    print("=" * 78)
    print("DIFF vs the cut list that was sent")
    print("=" * 78)
    real = load_cutlist(path)
    gen = [{"cabinet": p.cabinet, "code": p.code, "material": p.material,
            "length": p.length, "width": p.width, "qty": p.qty} for p in panels]

    rb, gb = defaultdict(list), defaultdict(list)
    for d in real:
        rb[d["cabinet"]].append(d)
    for d in gen:
        gb[d["cabinet"]].append(d)

    clean = 0
    for cab in sorted(set(rb) | set(gb)):
        r = defaultdict(int)
        g = defaultdict(int)
        for d in rb.get(cab, []):
            r[key(d)] += d["qty"]
        for d in gb.get(cab, []):
            g[key(d)] += d["qty"]
        only_r = {k: v for k, v in r.items() if g.get(k) != v}
        only_g = {k: v for k, v in g.items() if r.get(k) != v}
        if not only_r and not only_g:
            clean += 1
            continue
        tag = KNOWN.get(cab, "")
        print(f"\ncabinet {cab}" + (f"   [{tag}]" if tag else "   [NEW — investigate]"))
        for k, v in sorted(only_r.items()):
            print(f"    sent      {k[0]:<6} {k[1]}x{k[2]} x{v}")
        for k, v in sorted(only_g.items()):
            print(f"    generated {k[0]:<6} {k[1]}x{k[2]} x{v}")

    print(f"\n{clean} cabinets reproduce exactly.")


if __name__ == "__main__":
    main()
