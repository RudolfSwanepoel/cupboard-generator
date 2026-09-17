"""Sheet nesting.

Plazaboard cut this on a beam saw, so every cut runs edge to edge — the layout
must be guillotine-cuttable. That rules out the tighter maxrects packings you
see in general bin-packing; a clever layout the saw cannot produce is worthless.

The approach is guillotine packing with a free-rectangle list: place a panel in
the best-fitting free rectangle, then split what is left with a single straight
cut. Several heuristics are tried and the best result kept, because no single
rule wins on every job.

Grain: a panel with grain=1 may not be rotated. On the October 2025 job that is
the entire Brookhill Fusion board — 9 sheets at R999 — and it is also the
material that nested worst, so the constraint is exactly where it hurts.
"""
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from .model import Panel
from .standard import Standard, STANDARD


@dataclass
class Placement:
    label: str
    role: str
    x: int
    y: int
    length: int          # along the sheet's long axis
    width: int
    rotated: bool = False


@dataclass
class Rect:
    x: int
    y: int
    l: int
    w: int

    @property
    def area(self):
        return self.l * self.w


@dataclass
class Sheet:
    material: str
    length: int
    width: int
    placements: List[Placement] = field(default_factory=list)
    free: List[Rect] = field(default_factory=list)

    @property
    def used_area(self):
        return sum(p.length * p.width for p in self.placements)

    @property
    def area(self):
        return self.length * self.width

    @property
    def yield_pct(self):
        return 100.0 * self.used_area / self.area


# ---------------------------------------------------------------------------


def _explode(panels: List[Panel]) -> List[Tuple[str, str, int, int, bool]]:
    """One entry per physical piece: (label, role, length, width, grain_locked)."""
    out = []
    for p in panels:
        for _ in range(max(0, p.qty)):
            out.append((p.label, p.role, p.length, p.width, bool(p.grain)))
    return out


def _fits(rect: Rect, l: int, w: int) -> bool:
    return l <= rect.l and w <= rect.w


def _choose_rect(free: List[Rect], l: int, w: int, locked: bool):
    """Best short-side fit, area as tiebreak. Returns (index, length, width, rotated)."""
    best = None
    for i, r in enumerate(free):
        for ll, ww, rot in ((l, w, False),) if locked else ((l, w, False), (w, l, True)):
            if not _fits(r, ll, ww):
                continue
            leftover = (r.l - ll, r.w - ww)
            score = (min(leftover), max(leftover), r.area)
            if best is None or score < best[0]:
                best = (score, i, ll, ww, rot)
    if best is None:
        return None
    _, i, ll, ww, rot = best
    return i, ll, ww, rot


def _split(rect: Rect, l: int, w: int, kerf: int, rule: str) -> List[Rect]:
    """Guillotine split of the leftover space after placing l x w at the rect origin.

    Standard guillotine heuristics. No single one wins on every job, so the
    caller tries them all and keeps the best result.
      slas/llas  shorter / longer leftover axis
      sas/las    shorter / longer axis of the rectangle itself
      minas/maxas  minimise / maximise the larger of the two leftovers
    """
    rem_l = rect.l - l - kerf
    rem_w = rect.w - w - kerf

    if rule == "slas":
        horizontal = rem_l < rem_w
    elif rule == "llas":
        horizontal = rem_l >= rem_w
    elif rule == "sas":
        horizontal = rect.l < rect.w
    elif rule == "las":
        horizontal = rect.l >= rect.w
    else:
        h_max = max(max(rem_l, 0) * w, rect.l * max(rem_w, 0))
        v_max = max(max(rem_l, 0) * rect.w, l * max(rem_w, 0))
        horizontal = (h_max < v_max) if rule == "minas" else (h_max >= v_max)

    out = []
    if horizontal:
        if rem_l > 0:
            out.append(Rect(rect.x + l + kerf, rect.y, rem_l, w))
        if rem_w > 0:
            out.append(Rect(rect.x, rect.y + w + kerf, rect.l, rem_w))
    else:
        if rem_l > 0:
            out.append(Rect(rect.x + l + kerf, rect.y, rem_l, rect.w))
        if rem_w > 0:
            out.append(Rect(rect.x, rect.y + w + kerf, l, rem_w))
    return [r for r in out if r.l > 0 and r.w > 0]


def _prune(free: List[Rect], min_side: int = 40) -> List[Rect]:
    """Drop slivers nothing will ever fit in, and rectangles wholly inside another."""
    keep = [r for r in free if r.l >= min_side and r.w >= min_side]
    out = []
    for i, a in enumerate(keep):
        covered = False
        for j, b in enumerate(keep):
            if i != j and a.x >= b.x and a.y >= b.y and \
               a.x + a.l <= b.x + b.l and a.y + a.w <= b.y + b.w and a.area < b.area:
                covered = True
                break
        if not covered:
            out.append(a)
    return out


def _pack(pieces, material, std: Standard, rule: str):
    """Returns (sheets, rejected). Rejected panels do not fit a bare sheet."""
    sheets: List[Sheet] = []
    rejected = []
    for label, role, l, w, locked in pieces:
        # best fit across every open sheet, not the first one that happens to fit
        best = None
        for sh in sheets:
            pick = _choose_rect(sh.free, l, w, locked)
            if pick is None:
                continue
            i, ll, ww, rot = pick
            r = sh.free[i]
            leftover = (r.l - ll, r.w - ww)
            score = (min(leftover), max(leftover), r.area)
            if best is None or score < best[0]:
                best = (score, sh, i, ll, ww, rot)
        if best is not None:
            _, sh, i, ll, ww, rot = best
            r = sh.free.pop(i)
            sh.placements.append(Placement(label, role, r.x, r.y, ll, ww, rot))
            sh.free.extend(_split(r, ll, ww, std.kerf, rule))
            sh.free = _prune(sh.free)
        else:
            sh = Sheet(material, std.sheet_l, std.sheet_w,
                       free=[Rect(0, 0, std.sheet_l, std.sheet_w)])
            pick = _choose_rect(sh.free, l, w, locked)
            if pick is None:
                rejected.append((label, l, w))
                continue
            i, ll, ww, rot = pick
            r = sh.free.pop(i)
            sh.placements.append(Placement(label, role, r.x, r.y, ll, ww, rot))
            sh.free.extend(_split(r, ll, ww, std.kerf, rule))
            sheets.append(sh)
    return sheets, rejected


NEST_REJECTS = []
NEST_CHOICE = {}

SORTS = {
    "long_side": lambda p: (-max(p[2], p[3]), -p[2] * p[3]),
    "area": lambda p: (-p[2] * p[3], -max(p[2], p[3])),
    "width": lambda p: (-p[3], -p[2]),
    "length": lambda p: (-p[2], -p[3]),
    "short_side": lambda p: (-min(p[2], p[3]), -max(p[2], p[3])),
    "perimeter": lambda p: (-(p[2] + p[3]), -p[2] * p[3]),
    "squareness": lambda p: (abs(p[2] - p[3]), -p[2] * p[3]),
}
RULES = ("slas", "llas", "sas", "las", "minas", "maxas")


def nest_material(panels: List[Panel], material: str, std: Standard = STANDARD):
    """Try every sort/split combination, keep the one using fewest sheets."""
    pieces = _explode([p for p in panels if p.material == material])
    if not pieces:
        return []
    best = None
    for sname, skey in SORTS.items():
        ordered = sorted(pieces, key=skey)
        for rule in RULES:
            sheets, rejected = _pack(ordered, material, std, rule)
            score = (len(sheets), -sum(s.used_area for s in sheets))
            if best is None or score < best[0]:
                best = (score, sheets, sname, rule, rejected)
    NEST_REJECTS.extend(best[4])
    NEST_CHOICE[material] = (best[2], best[3])
    return best[1]


def nestable(panels: List[Panel], std: Standard = STANDARD) -> List[Panel]:
    """The panels the nester can actually place.

    Cancelled rows and anything too big for a bare sheet are excluded — an
    oversize panel is a validation critical, not a nesting problem, and letting
    it through here would cost a sheet it can never be cut from.
    """
    return [p for p in panels
            if p.qty > 0
            and max(p.length, p.width) <= std.sheet_l
            and min(p.length, p.width) <= std.sheet_w]


def nest_job(panels: List[Panel], std: Standard = STANDARD) -> dict:
    NEST_REJECTS.clear()
    NEST_CHOICE.clear()
    out = {}
    for material in sorted({p.material for p in panels}):
        out[material] = nest_material(panels, material, std)
    return out


def summarise(nested: dict) -> str:
    lines = []
    total_sheets = 0
    for mat, sheets in sorted(nested.items()):
        if not sheets:
            continue
        used = sum(s.used_area for s in sheets)
        area = sum(s.area for s in sheets)
        total_sheets += len(sheets)
        lines.append(f"  {mat:<6} {len(sheets):>2} sheets   "
                     f"{used / 1e6:>6.2f} of {area / 1e6:>6.2f} m2   "
                     f"yield {100.0 * used / area:>5.1f}%")
        for i, s in enumerate(sheets, 1):
            lines.append(f"       sheet {i}: {len(s.placements):>3} panels, "
                         f"{s.yield_pct:>5.1f}%")
    lines.append(f"  {'TOTAL':<6} {total_sheets:>2} sheets")
    return "\n".join(lines)


def sheets_svg(sheets: List[Sheet], title: str = "") -> str:
    """One sheet per row, panels labelled. Opens in any browser."""
    if not sheets:
        return ""
    scale = 0.25
    sw, sh = sheets[0].length, sheets[0].width
    pad = 40
    W = int(sw * scale) + pad * 2
    H = (int(sh * scale) + pad) * len(sheets) + pad
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
             f'viewBox="0 0 {W} {H}" font-family="sans-serif">',
             f'<rect width="{W}" height="{H}" fill="#fff"/>']
    colours = ["#dceaea", "#f5ebd6", "#dfede4", "#f7e3df", "#eaece7", "#e6e0ef"]
    for si, s in enumerate(sheets):
        oy = pad + si * (int(sh * scale) + pad)
        parts.append(f'<text x="{pad}" y="{oy - 10}" font-size="13" fill="#191c1a">'
                     f'{title} sheet {si + 1} — {s.material} — {len(s.placements)} panels, '
                     f'{s.yield_pct:.1f}% yield</text>')
        parts.append(f'<rect x="{pad}" y="{oy}" width="{sw * scale}" height="{sh * scale}" '
                     f'fill="#fafafa" stroke="#191c1a" stroke-width="1.5"/>')
        for pi, p in enumerate(s.placements):
            x = pad + p.x * scale
            y = oy + p.y * scale
            w = p.length * scale
            h = p.width * scale
            parts.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" '
                         f'fill="{colours[pi % len(colours)]}" stroke="#4a514c" stroke-width="0.6"/>')
            if w > 34 and h > 16:
                parts.append(f'<text x="{x + w / 2:.1f}" y="{y + h / 2 + 3:.1f}" '
                             f'font-size="9" text-anchor="middle" fill="#191c1a">'
                             f'{p.label}</text>')
                if h > 28:
                    parts.append(f'<text x="{x + w / 2:.1f}" y="{y + h / 2 + 14:.1f}" '
                                 f'font-size="7.5" text-anchor="middle" fill="#767e78">'
                                 f'{p.length}x{p.width}</text>')
    parts.append("</svg>")
    return "\n".join(parts)


def write_svg(sheets: List[Sheet], path: str, title: str = ""):
    svg = sheets_svg(sheets, title)
    if svg:
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(svg)
