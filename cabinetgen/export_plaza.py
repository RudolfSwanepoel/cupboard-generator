"""Plazaboard export and job costing.

One CSV per board type, in Plazaboard's own column order, with their edging and
hole maths pre-computed so the counter file matches ours line for line.
"""
import csv
import math
import os
from collections import defaultdict
from typing import List

from .model import Job, Panel, grain_of, material_board, material_price, material_thickness
from .standard import Standard, STANDARD

HEADER = ["Component", "Material", "Length", "Width", "qty", "Invoice Number", "JOB NO ",
          "Grain", "edge l", "edge w", "holes", "edge mat", "", "", "", "",
          "total edging", "total edging"]

# Rate card, quotation VRG_SOQ497999, 21 Oct 2025. Incl VAT.
#
# Board prices here are a FALLBACK only, for a job saved before boards carried
# their own captured price. A job that has one is priced off its own record.
# Nesting yield per board, for the board estimate before the nester has run.
# Keyed by board id for the three the October job used, and otherwise read off
# what the board IS: a grained board cannot be rotated, so it nests worse, and
# the thin backing sheet is cut on the masonite saw. A board added to the library
# after this was written gets the right figure rather than a house average.
YIELD = {"MEL": 0.89, "DECOR": 0.78, "BACK": 0.80}
YIELD_BY_KIND = {"grain": 0.78, "thin": 0.80, "plain": 0.89}


def board_yield(job: Job, mat: str) -> float:
    if mat in YIELD:
        return YIELD[mat]
    if material_thickness(job.materials, mat) <= 3:
        return YIELD_BY_KIND["thin"]
    return YIELD_BY_KIND["grain" if grain_of(job.materials, mat) else "plain"]


# What Plazaboard charge to cut one board. The rate card is by saw, not by board
# name: the beam saw takes the 16 mm boards, the masonite saw the thin backing.
# Keyed off thickness so a board renamed or added to the library is still
# charged for cutting — the id lookup it replaced quietly charged a new board R0.
CUT_BY_THICKNESS = {3: 34.00, 16: 67.00, 25: 67.00}
CUT_DEFAULT = 67.00


def cut_rate(job: Job, mat: str) -> float:
    if mat in RATES["cut"]:
        return RATES["cut"][mat]
    t = material_thickness(job.materials, mat)
    return CUT_BY_THICKNESS.get(t, 34.00 if t and t <= 3 else CUT_DEFAULT)

RATES = {
    "board": {
        "BROOKHILL FUSION CHIP": 999.00,
        "SUPER WHITE MELAMINE CHIP 9X6X16MM": 575.00,
        "IMPORTED WHITE DECOR 9X6X3MM": 310.00,
    },
    "cut": {          # per board
        "MEL": 67.00, "DECOR": 67.00, "BACK": 34.00,
    },
    "edging": {       # per metre: (tape, application)
        "2mm": (12.00, 7.50),
        "1mm": (8.00, 5.00),
        "PVC": (2.75, 4.00),
    },
    "pothole": 3.00,
}


def effective_price(job: Job, mat: str) -> float:
    """What this job pays per board of `mat`.

    The price captured when the board was selected, or the rate card for a job
    saved before boards carried one. Zero means neither knows — which the
    validator reports, because a board line at R0 is a quote that is wrong in the
    direction nobody notices.
    """
    return (material_price(job.materials, mat)
            or RATES["board"].get(material_board(job.materials, mat), 0.0))


def rows_for(panels: List[Panel], std: Standard = STANDARD):
    out = []
    for i, p in enumerate(panels, start=1):
        el, ew = p.edge_l, p.edge_w
        flags = ["1" if el >= 1 else "", "1" if el >= 2 else "",
                 "1" if ew >= 1 else "", "1" if ew >= 2 else ""]
        out.append([
            i, p.label, p.length, p.width, p.qty, "", "",
            p.grain, el or "", ew or "",
            p.pot_holes * p.qty or "",       # Plazaboard's holes column is the line total
            p.edge_material, *flags,
            round(p.edging_m(std), 3), "",
        ])
    return out


def write_csvs(job: Job, panels: List[Panel], outdir: str) -> List[str]:
    os.makedirs(outdir, exist_ok=True)
    by_mat = defaultdict(list)
    for p in panels:
        by_mat[p.material].append(p)
    written = []
    for mat, ps in by_mat.items():
        path = os.path.join(outdir, f"{job.name}_{mat}.csv")
        with open(path, "w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow(HEADER)
            running = 0.0
            for row in rows_for(ps, job.std):
                running += row[16]
                row[17] = round(running)
                w.writerow(row)
        written.append(path)
    return written


def summarise(job: Job, panels: List[Panel], nested: dict = None) -> dict:
    """Board counts, edging metres and pot holes — everything the quotation charges."""
    std = job.std
    sheet = std.sheet_l * std.sheet_w
    out = {"materials": {}, "edging": defaultdict(float), "potholes": 0}
    by_mat = defaultdict(list)
    for p in panels:
        by_mat[p.material].append(p)
        out["potholes"] += p.pot_holes * p.qty
        if p.edge_material:
            out["edging"][p.edge_material] += p.edging_m(std)

    for mat, ps in by_mat.items():
        area = sum(p.area_mm2() for p in ps)
        net = area / sheet
        out["materials"][mat] = {
            "panels": sum(p.qty for p in ps),
            "area_m2": round(area / 1e6, 2),
            "net_sheets": round(net, 2),
            # real board count when the nester has run, otherwise the yield
            # Plazaboard achieved per material on the Oct 2025 job
            "est_boards": (len(nested[mat]) if nested and mat in nested
                           else math.ceil(net / board_yield(job, mat))),
            "nested": bool(nested and mat in nested),
        }
    out["edging"] = {k: round(v, 3) for k, v in out["edging"].items()}
    return out


def estimate_cost(job: Job, summary: dict) -> dict:
    lines = []
    total = 0.0
    for mat, s in summary["materials"].items():
        desc = material_board(job.materials, mat)
        boards = s["est_boards"]
        # What this job was quoted at, not what the board costs today. The price
        # was captured into the job when the board was selected, so editing the
        # library afterwards reprices the next job and never this one.
        price = effective_price(job, mat)
        cut = cut_rate(job, mat)
        lines.append((desc, boards, price, boards * price))
        lines.append((f"Cutting — {desc}", boards, cut, boards * cut))
        total += boards * price + boards * cut

    for tape, metres in summary["edging"].items():
        m = math.ceil(metres)
        key = "2mm" if "2mm" in tape else "1mm" if "1mm" in tape else "PVC"
        rate, apply = RATES["edging"][key]
        lines.append((f"Edging {tape}", m, rate, m * rate))
        lines.append((f"Apply {tape}", m, apply, m * apply))
        total += m * rate + m * apply

    holes = summary["potholes"]
    lines.append(("Pot holes", holes, RATES["pothole"], holes * RATES["pothole"]))
    total += holes * RATES["pothole"]
    return {"lines": lines, "total_incl_vat": round(total, 2)}
