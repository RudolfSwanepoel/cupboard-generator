"""Front elevation of a job, as SVG.

Cabinets are drawn side by side to scale, with doors, drawer faces and shelf
lines shown. It is a sanity check, not a working drawing: if a cabinet looks
wrong here it is wrong in the cut list too.
"""
from dataclasses import replace
from html import escape
from typing import List

from . import pictures as PIC
from .engine import panel_of
from .model import (NO_COLOUR, Cabinet, Job, grain_of, hinge_side,
                    material_board, material_colour, material_record)
from .room import (LAYERS, cabinet_footprint, carcass_z, clashes, corner_points,
                   gap_outline, gaps, geometry, layer_of, overlaps,
                   panel_clashes, placed, placed_panels, plinth_choice_for,
                   plinth_lengths, pullout_envelope, return_profiles, run_key,
                   runs, swing_envelopes, to_world, wall_frames,
                   blind_spans)
from .standard import Standard, STANDARD

INK = "#191c1a"
RULE = "#aab1a9"
FAINT = "#d3d7d0"
MUTED = "#767e78"
CRIT = "#a4303f"

PAPER = "#ffffff"

# base / wall / tall are told apart by the OUTLINE now, because the fill says
# which board a part is cut from (20 Sept 2026). The dash is 7 4, not the 4 3
# the shelf lines and the openings already use, so an outline is never read as
# one of those.
LAYER_STROKE = {"base": ("1.3", ""),
                "wall": ("1.3", ' stroke-dasharray="7 4"'),
                "tall": ("2.2", "")}
LEGEND_ROW = 15

# How an elevation is drawn — a view setting, never saved in the job and never a
# change to any geometry. FINISH is every part in its board's colour or picture;
# LINE is the same drawing on white paper, fronts white, lines and text in grey.
VIEW_MODES = ("finish", "line")
LINE_INK = MUTED


def _line_job(job: Job) -> Job:
    """The job as the LINE view draws it: every board white, plain, pictureless.

    Only what a board LOOKS like changes — the record is otherwise the one the
    job carries (`material_record`, normalised), so tape names, thickness and
    every size read exactly as in the Finish view. A copy: the job is untouched.
    """
    mats = {}
    for k in (job.materials or {}):
        rec = dict(material_record(job.materials, k))
        rec.update(colour=PAPER, grain="plain", picture="")
        mats[k] = rec
    return replace(job, materials=mats)


def _line_ink(svg: str) -> str:
    """Every dark ink in a drawing turned to the grey the end-on outlines use,
    and a board nobody coloured drawn as paper like the rest. Red stays red: a
    clash is still a clash in the Line view."""
    return (svg.replace(f'"{INK}"', f'"{LINE_INK}"')
               .replace(f'"{NO_COLOUR}"', f'"{PAPER}"'))


def board_look(job, board_id: str) -> dict:
    """What one board looks like on a drawing: `colour`, `grain`, `picture`.

    The one resolver. Every fill in the run, the wall elevations and the plan
    comes through here, and no drawing states a colour of its own, so what you
    see is what the cut list cuts. `job` is a Job or — for `_interior`, which is
    handed the materials and nothing else — the job's `materials` dict straight.

    A board nobody has coloured comes back NO_COLOUR with `set` False. That is
    what the legend says "no colour set" from; it is never a warning.

    `picture` is what the record stores. `Fills` is what turns it into a
    fill; a picture only ever wins over the colour on a GRAINED board, and
    the rule lives there so every drawing gets the same answer.
    """
    materials = job.materials if isinstance(job, Job) else (job or {})
    if not board_id:
        return {"colour": NO_COLOUR, "set": False, "grain": False,
                "picture": "", "ink": ink_on(NO_COLOUR)}
    rec = material_record(materials, board_id)
    colour = _hex(material_colour(materials, board_id))
    return {"colour": colour,
            "set": bool(_hex(str(rec.get("colour") or ""), "")),
            "grain": bool(grain_of(materials, board_id)),
            "picture": str(rec.get("picture") or ""),
            "ink": ink_on(colour)}


def _hex(colour: str, fallback: str = NO_COLOUR) -> str:
    """`colour` as #rrggbb, or the fallback when it is not one.

    Every fill in every drawing goes out through here. A colour picked in the
    Boards tab is already cleaned on the way in, but a job file is a text file
    somebody can edit, and a fill is written into the SVG as it stands — so
    what is written is a hex value or nothing.
    """
    raw = (colour or "").strip().lstrip("#").lower()
    if len(raw) == 3:
        raw = "".join(ch * 2 for ch in raw)
    if len(raw) != 6 or any(ch not in "0123456789abcdef" for ch in raw):
        return fallback
    return "#" + raw


def _luminance(colour: str) -> float:
    """Relative luminance of an #rrggbb — the sRGB definition WCAG contrast uses."""
    raw = (colour or "").strip().lstrip("#")
    if len(raw) == 3:
        raw = "".join(ch * 2 for ch in raw)
    if len(raw) != 6:
        return 1.0
    try:
        channels = [int(raw[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    except ValueError:
        return 1.0
    lin = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
           for c in channels]
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]


def ink_on(fill: str) -> str:
    """The ink that reads on a fill: dark on a light board, white on a dark one.

    A board colour is chosen for the board, not for the numbers that end up on
    it, so the ink is computed rather than stated — whichever of the two gives
    the better contrast ratio against that fill wins. Computed here, because the
    browser works out no dimension and no colour of its own.
    """
    lum = _luminance(fill)
    against_ink = (lum + 0.05) / (_luminance(INK) + 0.05)
    against_white = 1.05 / (lum + 0.05)
    return INK if against_ink >= against_white else PAPER


def _contrast(a: str, b: str) -> float:
    """The WCAG contrast ratio between two colours, 1 to 21."""
    la, lb = _luminance(a), _luminance(b)
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)


def _mix(a: str, b: str, t: float) -> str:
    """`a` moved `t` of the way towards `b`, as #rrggbb."""
    raw = [(c or "").strip().lstrip("#") for c in (a, b)]
    raw = ["".join(ch * 2 for ch in r) if len(r) == 3 else r for r in raw]
    if any(len(r) != 6 for r in raw):
        return b
    try:
        ends = [[int(r[i:i + 2], 16) for i in (0, 2, 4)] for r in raw]
    except ValueError:
        return b
    return "#" + "".join(f"{round(x + (y - x) * t):02x}"
                         for x, y in zip(ends[0], ends[1]))


def muted_on(fill: str) -> str:
    """The secondary ink on a fill — a face height, the size under a number.

    MUTED wherever MUTED still reads, which is every light board, so the
    drawings on white look exactly as they always have. On a mid or a dark
    board it disappears — grey on grey is 1.04:1 — so there it is the fill
    mixed most of the way towards whichever ink `ink_on` chose: a step quieter
    than the number beside it, and never invisible.
    """
    return MUTED if _contrast(fill, MUTED) >= 3.0 else _mix(fill, ink_on(fill), 0.78)


def _grain_lines(x, y, w, h, vertical, ink, pitch=7.0):
    """Fine parallel lines over a fill, for a board whose record says `grain`.

    The direction is the cut list's. `Length` is the grain direction, and a door
    and a drawer face are both cut with `Length` up the front, so both get
    vertical lines. Vertical on a drawer face is right — ruled 20 Sept 2026.

    Decoration: nothing reads it back.
    """
    out = []
    if w < 4 or h < 4:
        return out
    span = w if vertical else h
    for i in range(1, int(span // pitch) + 1):
        at = i * pitch
        if vertical:
            out.append(f'<line x1="{x + at:.1f}" y1="{y + 1:.1f}" '
                       f'x2="{x + at:.1f}" y2="{y + h - 1:.1f}" '
                       f'stroke="{ink}" stroke-width="0.5" stroke-opacity="0.22"/>')
        else:
            out.append(f'<line x1="{x + 1:.1f}" y1="{y + at:.1f}" '
                       f'x2="{x + w - 1:.1f}" y2="{y + at:.1f}" '
                       f'stroke="{ink}" stroke-width="0.5" stroke-opacity="0.22"/>')
    return out


# A 16 mm panel is about four pixels wide on a wall elevation, which is nothing
# to aim a pointer at. Every panel carries an invisible rectangle at least this
# many pixels across so it can actually be picked up.
PANEL_GRAB = 16


# How big a board picture is tiled on a drawing, in pixels. Nothing reads it and
# it is not a dimension: it is how big the swatch is drawn. Small enough that a
# door shows the grain running rather than one smeared close-up of it.
PICTURE_TILE = 40


class Fills:
    r"""The board fills one drawing uses, and the ``<defs>`` they need.

    **A picture wins over the colour field, and only on a GRAINED board** (ruled
    22 September 2026). A board whose record carries a picture is drawn in that
    picture; everything else is drawn in its colour exactly as before -- no
    picture, or a plain board, because a photograph of a flat white sheet says
    nothing the colour does not and tiles into noise. That rule is stated here
    and nowhere else, so every fill in every drawing gets the same answer, the
    same way `board_look` is the one place a colour is resolved.

    The picture is tiled through an SVG ``<pattern>``, and the tile is TURNED
    onto the panel's own grain direction. Board pictures are supplied with the
    grain vertical (`pictures.grain_verdict` is what says so at upload time), so
    the turn is 0 or 90 degrees and never an angle worked out of a photograph --
    which is the whole reason for the convention.

    The board's colour sits under the image inside the pattern, so a picture
    that does not load leaves the part its colour rather than a hole.

    Patterns are collected while the drawing is built and spliced into the
    ``<defs>`` afterwards: which ones a drawing needs is only known once the
    parts that want them have been drawn.

    ``base`` is where an ``<image>`` points. On screen that is the server route;
    an exported drawing is a file on disk beside its pictures, so `api.export`
    hands over ``""`` and copies the files in alongside.
    """

    def __init__(self, base: str = PIC.ROUTE, tile: int = PICTURE_TILE):
        self.base = base
        self.tile = tile
        self._ids = {}
        self._defs = []

    def textured(self, look) -> bool:
        """Is this board drawn in a picture rather than a flat colour?

        Callers ask because a photograph of real grain does not want `_grain_lines`
        drawn over the top of it.
        """
        if self.base is None:                      # colours only: see `_FLAT`
            return False
        return bool(look.get("grain") and look.get("picture")
                    and PIC.url_for(look["picture"], base=self.base))

    def of(self, look, vertical: bool = True) -> str:
        """What to write into a ``fill=``: a hex colour, or ``url(#...)``.

        `vertical` is which way the grain runs on this part as drawn -- the cut
        list's direction, the same question `_grain_lines` is asked. `None` means
        the grain runs into the page and has no direction face on; the tile is
        left as supplied rather than turned on a guess.
        """
        if not self.textured(look):
            return look["colour"]
        href = PIC.url_for(look["picture"], base=self.base)
        turn = vertical is False
        key = (href, turn)
        name = self._ids.get(key)
        if name is None:
            name = "bpic%d" % (len(self._ids) + 1)
            self._ids[key] = name
            t = self.tile
            spin = f' patternTransform="rotate(90 {t / 2:.1f} {t / 2:.1f})"' if turn else ""
            self._defs.append(
                f'<pattern id="{name}" width="{t}" height="{t}" '
                f'patternUnits="userSpaceOnUse"{spin}>'
                f'<rect width="{t}" height="{t}" fill="{look["colour"]}"/>'
                f'<image href="{escape(href, {chr(34): "&quot;"})}" x="0" y="0" '
                f'width="{t}" height="{t}" preserveAspectRatio="xMidYMid slice"/>'
                f'</pattern>')
        return f"url(#{name})"

    def defs(self) -> str:
        """The patterns, as markup. '' when the drawing needs none."""
        return "".join(self._defs)


# For a caller with nowhere to put a `<defs>`: every fill comes back as its
# board's colour, which is exactly what every drawing did before pictures.
_FLAT = Fills(base=None)


def pictures_drawn(job: Job) -> list:
    """Which of this job's board pictures a drawing will actually ask for.

    `export` needs this to copy the files in beside the SVGs it writes, and it
    must not answer the question itself: whether a picture is drawn at all is
    `Fills.textured`'s rule and only its, or the export and the drawing would be
    the two lists that disagree. Stored values, not URLs — the caller is after
    the files.
    """
    fills = Fills()
    out = set()
    for board_id in job.board_ids:
        look = board_look(job, board_id)
        if fills.textured(look):
            out.add(look["picture"])
    return sorted(out)


def _panel_grain_vertical(spec):
    """Which way the grain lines run on a panel drawn face on: True for up the
    drawing, False for along it, None when the grain runs into the page.

    `Length` IS the grain direction and which physical direction that is depends
    on the orientation: `a` runs along the wall on an upright or a flat panel
    and out from the wall on an end cap; `b` runs up on an upright or an end cap
    and out from the wall on a flat one. A grain running out from the wall has
    no direction on an elevation, so nothing is drawn rather than a line that
    would say the wrong thing.
    """
    o = spec.orientation
    if spec.grain_along == "a":
        return False if o in ("upright", "flat") else None
    return True if o in ("upright", "end") else None


def _layer_outline(layer: str, bad: bool = False):
    """Stroke colour, width and dash for a carcass outline: `(ink, width, dash)`.

    A clash still wins — red and heavy — but keeps its layer's dash, so a wall
    unit in the way is still recognisably a wall unit.
    """
    width, dash = LAYER_STROKE.get(layer, ("1.3", ""))
    return (CRIT, "2", dash) if bad else (INK, width, dash)


def _seen(into: list, board_id: str):
    if board_id and board_id not in into:
        into.append(board_id)


def _boards_drawn(job: Job, cabs) -> list:
    """The boards a front elevation actually put on the paper, first drawn first.

    The legend names what is in the drawing, not what the project carries: the
    body's carcass board, each door leaf's, each drawer face's, and the boards
    whose colour bands them.
    """
    into = []
    for c in cabs:
        if c.is_panel:
            # A panel is one board, and the board whose colour bands it. None of
            # the cupboard questions below apply to it.
            spec = c.panel_spec
            _seen(into, spec.board)
            if spec.edge_kind and spec.edge_board:
                _seen(into, spec.edge_board)
            continue
        _seen(into, c.carcass_board)
        for i in range(c.door_count):
            _seen(into, c.door_board(i))
        for d in c.drawer_list:
            _seen(into, c.face_board_of(d))
        if c.door_count and c.door_tape(job.materials):
            _seen(into, c.door_edge_colour_board)
        if c.drawer_list and c.drawer_face_tape(job.materials):
            _seen(into, c.drawer_face_edge_colour_board)
    return into


def _legend_rows(job: Job, ids, width) -> list:
    """The legend, wrapped to the drawing's width. Wrapped, never truncated: an
    ellipsis would drop a board off a list whose whole job is to be complete."""
    mats = job.materials
    rows, row, used = [], [], 0.0
    for board_id in ids:
        look = board_look(mats, board_id)
        text = f"{board_id} — {material_board(mats, board_id)}"
        if not look["set"]:
            text += " (no colour set)"
        entry = (look, text, 17 + len(text) * 4.9 + 16)
        if row and used + entry[2] > width:
            rows.append(row)
            row, used = [], 0.0
        row.append(entry)
        used += entry[2]
    if row:
        rows.append(row)
    return rows


def _legend_height(rows) -> int:
    return LEGEND_ROW * len(rows) + 4 if rows else 0


def _legend_svg(rows, x, y, fills=None) -> list:
    """One swatch per board: what it is drawn in, a grain mark when the board is
    grained, and `id - name`.

    The swatch takes the same fill as the parts, through the same `Fills` — a
    legend that did not would be a key to a drawing it does not describe.
    """
    out = []
    fills = fills or _FLAT
    for r, entries in enumerate(rows):
        at_y = y + r * LEGEND_ROW
        at_x = x
        for look, text, width in entries:
            out.append(f'<rect class="swatch" x="{at_x:.1f}" y="{at_y:.1f}" '
                       f'width="13" height="10" fill="{fills.of(look, True)}" '
                       f'stroke="{RULE}" stroke-width="0.8"/>')
            if look["grain"] and not fills.textured(look):
                out += _grain_lines(at_x, at_y, 13, 10, True, look["ink"], pitch=3.0)
            out.append(f'<text x="{at_x + 17:.1f}" y="{at_y + 8.5:.1f}" '
                       f'font-size="8.5" fill="{MUTED}">{escape(text)}</text>')
            at_x += width
    return out


def tape_legend(job: Job) -> list:
    """Which tape bands what, as resolved for this job.

    The tape name is generated from the board, so it is worth putting on the
    drawing rather than leaving it to the cut list: a door taped in the carcass
    colour looks right on paper and wrong in the room. One line per distinct
    tape, naming the cabinets that use it when they do not all agree.
    """
    roles = (("doors", "door_edge"), ("drawer faces", "drawer_face_edge"),
             ("carcass fronts", "carcass_edge"), ("drawer boxes", "drawer_box_edge"))
    out = []
    for label, field in roles:
        seen = {}
        for c in job.cabinets:
            if c.is_panel or c.template == "none":
                continue    # both name their own edging, panel by panel
            tape = c.tapes(job.materials)[field]
            if tape:
                seen.setdefault(tape, []).append(c.number)
        for tape, cabs in seen.items():
            note = "" if len(seen) == 1 else f" (cab {', '.join(map(str, cabs))})"
            out.append(f"{label} {tape}{note}")
    return out


def _tape_note(job: Job, x, y, width) -> list:
    legend = tape_legend(job)
    if not legend:
        return []
    text = "Edging: " + "  ·  ".join(legend)
    if len(text) * 4.6 > width:            # one line only; the cut list has the rest
        text = text[:int(width / 4.6) - 1] + "…"
    return [f'<text class="tapes" x="{x:.1f}" y="{y:.1f}" font-size="8.5" '
            f'fill="{MUTED}">{escape(text)}</text>']


def elevation_svg(job: Job, max_width: int = 1100,
                  pictures: str = PIC.ROUTE, mode: str = "finish") -> str:
    """The Run: the cabinet list drawn side by side.

    `mode` is the view: "finish" (the default, and exactly what this has always
    drawn) or "line" — see `VIEW_MODES`.

    Panels are not in it, deliberately. A panel is not part of a cupboard run —
    it has no place in a line of carcasses — and keeping it out is also what
    keeps `wall_elevation_svg` with no room equal to this drawing, which
    tools/check_elevation.py asserts.

    `pictures` is where a board picture is fetched from — see `Fills`.
    """
    if mode == "line":
        return _line_ink(_elevation_svg(_line_job(job), max_width, pictures, False))
    return _elevation_svg(job, max_width, pictures, True)


def _elevation_svg(job: Job, max_width: int, pictures: str, legend: bool) -> str:
    cabs = [c for c in job.cabinets if not c.is_panel]
    # A corner unit's width along its wall is its geometry, never the declared
    # label (hard rule 1): a mitre drawn at its declared 1200 when its arm is 1000
    # was one of the things that made the corner unit look broken.
    gw = {c.number: (geometry(c, job.std, job.materials).width if c.corner_on else c.width)
          for c in cabs}
    if not cabs:
        return ('<svg xmlns="http://www.w3.org/2000/svg" width="200" height="60">'
                f'<text x="10" y="34" font-size="13" fill="{MUTED}" '
                'font-family="sans-serif">No cabinets yet</text></svg>')

    std = job.std
    gap_mm = 20
    total_w = sum(gw[c.number] for c in cabs) + gap_mm * (len(cabs) - 1)
    max_h = max(c.height for c in cabs)
    pad = 46
    scale = min((max_width - pad * 2) / total_w, 520 / max_h)
    W = int(total_w * scale) + pad * 2
    # the board key says what each colour is; the Line view has no colours
    rows = _legend_rows(job, _boards_drawn(job, cabs), W - pad * 2) if legend else []
    leg = _legend_height(rows)
    H = int(max_h * scale) + pad * 2 + 14 + leg   # under the floor: tapes, then boards

    fills = Fills(base=pictures)
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
           f'viewBox="0 0 {W} {H}" font-family="system-ui,sans-serif">',
           "",                          # the board patterns, spliced in below
           f'<rect width="{W}" height="{H}" fill="none"/>']
    defs_at = 1
    x = pad
    floor = int(max_h * scale) + pad
    for c in cabs:
        look = board_look(job, c.carcass_board)
        stroke, sw, dash = _layer_outline(layer_of(c))
        w = gw[c.number] * scale
        h = c.height * scale
        y = floor - h
        # One group per cabinet, carrying its number — the run has no wall to
        # drag along, so the press selects rather than moves (C9).
        out.append(f'<g class="ecabg erun" data-cab="{c.number}">')
        out.append(f'<rect class="ecab" data-cab="{c.number}" x="{x:.1f}" y="{y:.1f}" '
                   f'width="{w:.1f}" height="{h:.1f}" fill="{fills.of(look, True)}" '
                   f'stroke="{stroke}" stroke-width="{sw}"{dash}/>')
        out += _interior(c, x, y, w, h, scale, std, materials=job.materials,
                         fills=fills)
        out.append(f'<text x="{x + w / 2:.1f}" y="{floor + 16:.1f}" font-size="11" '
                   f'text-anchor="middle" fill="{INK}">{c.number}</text>')
        out.append(f'<text x="{x + w / 2:.1f}" y="{floor + 29:.1f}" font-size="9.5" '
                   f'text-anchor="middle" fill="{MUTED}">{_size_label(job, c)}</text>')
        out.append("</g>")
        x += w + gap_mm * scale

    out.append(f'<line x1="{pad - 8}" y1="{floor:.1f}" x2="{W - pad + 8}" y2="{floor:.1f}" '
               f'stroke="{INK}" stroke-width="1.6"/>')
    out += _tape_note(job, pad, H - 8 - leg, W - pad * 2)
    out += _legend_svg(rows, pad, H - leg + 2, fills)
    out[defs_at] = f"<defs>{fills.defs()}</defs>"
    out.append("</svg>")
    return "\n".join(out)


def _size_label(job, c) -> str:
    """The W x H x D under a cabinet in the Run. A corner unit's is its
    geometry and its type, never the declared figures, which it does not have."""
    if not c.corner_on:
        return f"{c.width}x{c.height}x{c.depth}"
    g = geometry(c, job.std, job.materials)
    if c.corner_kind in ("mitre", "ell") and g.source != "corner":
        return f"{c.corner_kind} {c.hand} · measurements incomplete"
    return f"{c.corner_kind} {c.hand} · {g.width}x{g.height}x{g.depth}"


def _note_svg(text: str, w: int = 260) -> str:
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="60">'
            f'<text x="10" y="34" font-size="13" fill="{MUTED}" '
            f'font-family="system-ui,sans-serif">{text}</text></svg>')


# --- per-wall elevations ------------------------------------------------------

def wall_elevation_dims(job: Job, wall_id: str) -> dict:
    """The dimension chains for one wall, as numbers.

    Kept apart from the drawing so they can be checked. Every chain is a list of
    breakpoints running from a datum — the wall's start corner, or the floor — so
    its segments always add up to the whole. A chain that does not close is a
    drawing that is lying.
    """
    rm = job.room
    std = job.std
    wall = next(w for w in rm.walls if w.id == wall_id)
    on_wall = [(c, p, lay, geometry(c, std)) for c, p, lay in placed(job) if p.wall == wall_id]

    def chain(points, end):
        return sorted({0, end} | {min(max(v, 0), end) for v in points})

    # widths and heights off the panels, never the declared figures
    floor = [v for c, p, lay, g in on_wall if lay != "wall" for v in (p.x, p.x + g.width)]
    hung = [v for c, p, lay, g in on_wall if lay == "wall" for v in (p.x, p.x + g.width)]
    heights = []
    for c, p, _lay, g in on_wall:
        z0 = carcass_z(c, p, std)
        heights += [z0, z0 + g.height]
    # An unmeasured ceiling is not drawn as if it were a figure: the chain closes
    # on the tallest carcass instead, and the drawing says the ceiling is missing.
    top = max([rm.ceiling or 0] + heights) or 1
    return {
        "wall": wall_id,
        "length": wall.length,
        "ceiling": rm.ceiling,
        "top": top,
        "floor_chain": chain(floor, wall.length),
        # The top chain breaks wherever EITHER run does (22 September 2026).
        # It used to break only at the overheads, so a wall with one wall unit
        # over a row of base units dimensioned that unit and then handed you one
        # figure spanning every cupboard past it — a number you cannot set
        # anything out from. Same data as the bottom chain, read at the same
        # resolution. A wall with no overheads still gets no top chain: there is
        # nothing up there to dimension, and the bottom already says it.
        "wall_chain": chain(hung + floor, wall.length) if hung else [],
        "height_chain": chain(heights, top),
    }


def _tick(x, y):
    return (f'<line x1="{x - 3:.1f}" y1="{y + 3:.1f}" x2="{x + 3:.1f}" y2="{y - 3:.1f}" '
            f'stroke="{INK}" stroke-width="0.9"/>')


def _dim_h(x0, x1, y, value):
    out = [f'<line x1="{x0:.1f}" y1="{y:.1f}" x2="{x1:.1f}" y2="{y:.1f}" '
           f'stroke="{MUTED}" stroke-width="0.7"/>', _tick(x0, y), _tick(x1, y)]
    if x1 - x0 >= 18:
        out.append(f'<text class="dim" x="{(x0 + x1) / 2:.1f}" y="{y - 4:.1f}" '
                   f'font-size="8.5" text-anchor="middle" fill="{INK}">{value}</text>')
    return out


def _dim_v(y_top, y_bot, x, value):
    out = [f'<line x1="{x:.1f}" y1="{y_top:.1f}" x2="{x:.1f}" y2="{y_bot:.1f}" '
           f'stroke="{MUTED}" stroke-width="0.7"/>', _tick(x, y_top), _tick(x, y_bot)]
    if y_bot - y_top >= 18:
        mid = (y_top + y_bot) / 2
        out.append(f'<text class="dim" x="{x - 4:.1f}" y="{mid:.1f}" font-size="8.5" '
                   f'text-anchor="middle" fill="{INK}" '
                   f'transform="rotate(-90 {x - 4:.1f} {mid:.1f})">{value}</text>')
    return out


def wall_elevation_svg(job: Job, wall_id: str, max_width: int = 1100,
                       pictures: str = PIC.ROUTE, mode: str = "finish") -> str:
    """One wall, face on, as a dimensioned working drawing.

    Cabinets at their true positions and heights, with the wall, its openings and
    obstructions behind them, and the fillers and plinth boards that were chosen.
    Widths are chained from the wall's start corner and heights from the floor.
    With no room there is no datum, so it falls back to the side-by-side sanity
    check, unchanged. `pictures` is where a board picture is fetched from —
    see `Fills`. `mode` is the view, "finish" or "line" (`VIEW_MODES`).

    Every wall is drawn by the same rule, whatever the room's shape: standing in
    the room facing this wall, left and right as you see them, what is placed on
    it is drawn in full; the runs on the walls either side of it — found off the
    room's chain of corners (`return_profiles`), never off a letter — are grey
    outlines end on at the ends they meet it, labelled with their wall and their
    numbers; and an end with no wall beside it has nothing drawn there. A corner
    unit belongs to the wall it is placed on: drawn in full there, an outline
    end on everywhere else.
    """
    rm = job.room
    if rm is None:
        return elevation_svg(job, max_width, pictures, mode)
    if mode == "line":
        return _line_ink(_wall_elevation_svg(_line_job(job), wall_id, max_width,
                                             pictures, False))
    return _wall_elevation_svg(job, wall_id, max_width, pictures, True)


def _wall_elevation_svg(job: Job, wall_id: str, max_width: int, pictures: str,
                        legend: bool) -> str:
    rm = job.room
    wall = next((w for w in rm.walls if w.id == wall_id), None)
    if wall is None:
        return _note_svg(f"No wall {escape(str(wall_id))}")

    if wall.length <= 0:
        return _note_svg(f"Wall {escape(wall.id)}: length not measured")

    std = job.std
    dims = wall_elevation_dims(job, wall_id)
    everywhere = {c.number: (c, p) for c, p, _ in placed(job)}
    on_wall = [(c, p, lay, geometry(c, std)) for c, p, lay in placed(job) if p.wall == wall_id]
    # Panels are drawn but take part in nothing else: no run, no plinth, no
    # dimension chain, no tip-up. They come from their own list for exactly that
    # reason, and are drawn over the cabinets because a bulkhead front is in
    # front of the units it caps.
    on_panels = [(c, p, geometry(c, std, job.materials))
                 for c, p in placed_panels(job) if p.wall == wall_id]
    bad = {n for o in overlaps(job, std)
           if o.wall == wall_id or (o.across and wall_id in o.wall.split("/"))
           for n in (o.a, o.b)}
    bad_panels = {c.panel for c in panel_clashes(job, std) if c.wall == wall_id}

    length, top = wall.length, dims["top"]
    # pad_b leaves the three footnotes clear of the overall dimension under the
    # floor chain — at 80 the first of them was written across it
    pad_l, pad_r, pad_t, pad_b = 72, 30, 64, 96
    scale = min((max_width - pad_l - pad_r) / length, 540 / top)
    W = int(length * scale) + pad_l + pad_r
    rows = (_legend_rows(job, _boards_drawn(job, [c for c, _p, _l, _g in on_wall] +
                                            [c for c, _p, _g in on_panels]),
                         W - pad_l - pad_r) if legend else [])
    leg = _legend_height(rows)
    H = int(top * scale) + pad_t + pad_b + leg

    def X(v):
        return pad_l + v * scale

    def Y(z):
        return pad_t + (top - z) * scale

    wid = escape(wall.id)
    if rm.ceiling:
        heading, heading_ink = f"{length} long, ceiling {rm.ceiling}", INK
    else:
        heading, heading_ink = (f"{length} long, ceiling NOT MEASURED — "
                                f"required before export", CRIT)
    fills = Fills(base=pictures)
    hatch = ('<pattern id="ehatch" width="6" height="6" '
             'patternUnits="userSpaceOnUse" patternTransform="rotate(45)">'
             f'<line x1="0" y1="0" x2="0" y2="6" stroke="{MUTED}" stroke-width="1.4"/>'
             '</pattern>')
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
           f'viewBox="0 0 {W} {H}" font-family="system-ui,sans-serif">',
           "",                  # the hatch and the board patterns, spliced below
           f'<rect width="{W}" height="{H}" fill="none"/>',
           f'<text x="{pad_l}" y="20" font-size="12" fill="{heading_ink}">Wall {wid} — '
           f'{heading}</text>']

    # What a drag reads back: where 0 mm along the wall and the floor sit on the
    # drawing, and how many pixels a millimetre is. The browser converts with
    # these and works out no dimension of its own — the same bargain the plan's
    # wall tracks make, in two axes instead of one.
    out.append(f'<rect class="etrack" data-wall="{wid}" data-len="{length}" '
               f'data-scale="{scale:.6f}" data-x0="{X(0):.2f}" data-y0="{Y(0):.2f}" '
               f'data-ceiling="{rm.ceiling or 0}" x="0" y="0" width="0" height="0" '
               f'fill="none" pointer-events="none"/>')

    # the wall itself, with the ceiling as a datum line — only if it was measured
    if rm.ceiling:
        out.append(f'<rect x="{X(0):.1f}" y="{Y(rm.ceiling):.1f}" '
                   f'width="{length * scale:.1f}" height="{rm.ceiling * scale:.1f}" '
                   f'fill="none" stroke="{RULE}" stroke-width="1"/>')

    for op in wall.openings:
        kind = escape(op.kind)
        ox, oy = X(op.x), Y(op.head)
        ow, oh = op.width * scale, (op.head - op.sill) * scale
        out.append(f'<rect class="opening" x="{ox:.1f}" y="{oy:.1f}" width="{ow:.1f}" '
                   f'height="{oh:.1f}" fill="#fff" stroke="{RULE}" stroke-width="1" '
                   f'stroke-dasharray="4 3"/>')
        out.append(f'<text x="{ox + ow / 2:.1f}" y="{oy + 12:.1f}" font-size="8.5" '
                   f'text-anchor="middle" fill="{MUTED}">{kind} {op.width}</text>')
        out.append(f'<text x="{ox + ow / 2:.1f}" y="{oy + 23:.1f}" font-size="8" '
                   f'text-anchor="middle" fill="{MUTED}">sill {op.sill} · head {op.head}</text>')

    boarded = set()                 # cabinets whose legs a plinth board covers
    for r in runs(job, std):
        choice = plinth_choice_for(job, r)
        if r.wall != wall_id or r.z != 0 or not (choice and choice.fitted):
            continue
        boarded.update(r.cabinets)
        for board, at in plinth_lengths(job, r, std):
            out.append(f'<rect class="plinth" x="{X(at):.1f}" y="{Y(std.leg_height):.1f}" '
                       f'width="{board * scale:.1f}" height="{std.leg_height * scale:.1f}" '
                       f'fill="{FAINT}" stroke="{RULE}" stroke-width="0.9"/>')

    for g in gaps(job, std):
        if g.wall != wall_id or g.treatment not in ("filler", "blind"):
            continue
        bound = everywhere.get(g.after if g.after is not None else g.before)
        z0 = carcass_z(bound[0], bound[1], std) if bound else 0
        gx, gy, gw, gh = X(g.x), Y(z0 + g.height), g.nominal * scale, g.height * scale
        if g.treatment == "filler":
            out.append(f'<rect class="filler" x="{gx:.1f}" y="{gy:.1f}" width="{gw:.1f}" '
                       f'height="{gh:.1f}" fill="url(#ehatch)" stroke="{INK}" '
                       f'stroke-width="0.8"/>')
            label = f"filler {g.filler_width(std)}"
        else:
            out.append(f'<rect class="blind" x="{gx:.1f}" y="{gy:.1f}" width="{gw:.1f}" '
                       f'height="{gh:.1f}" fill="{FAINT}" stroke="{RULE}" '
                       f'stroke-width="0.8"/>')
            label = "blind"
        if gw >= 12:
            out.append(f'<text x="{gx + gw / 2:.1f}" y="{gy + gh / 2:.1f}" font-size="8" '
                       f'text-anchor="middle" fill="{INK}" '
                       f'transform="rotate(-90 {gx + gw / 2:.1f} {gy + gh / 2:.1f})">'
                       f'{label}</text>')

    # The runs on the walls either side, end on — what you see of wall A's
    # cabinets standing face on to wall B. Drawn light and see-through, under
    # this wall's own cabinets, so none of them hides another: the drawing is
    # about this wall. Cabinets that land on exactly the same outline share one
    # label rather than stacking their numbers on one spot.
    shapes, walls_seen = {}, {}
    for r in return_profiles(job, wall_id, std):
        shapes.setdefault((r["x0"], r["x1"], r["z0"], r["height"], r["wall"]),
                          []).append(r["cabinet"])
    for (x0, x1, z0, hgt, other), nums in shapes.items():
        sx, sy, sw_, sh = X(x0), Y(z0 + hgt), (x1 - x0) * scale, hgt * scale
        out.append(f'<g class="eside" data-wall="{escape(other)}" '
                   f'data-cabs="{" ".join(map(str, nums))}">'
                   f'<rect x="{sx:.1f}" y="{sy:.1f}" width="{sw_:.1f}" height="{sh:.1f}" '
                   f'fill="{FAINT}" fill-opacity="0.35" stroke="{MUTED}" '
                   f'stroke-width="0.9"/>')
        out.append('</g>')
        seen = walls_seen.setdefault(other, [x0, x1, z0 + hgt, set()])
        seen[0], seen[1] = min(seen[0], x0), max(seen[1], x1)
        seen[2] = max(seen[2], z0 + hgt)
        seen[3].update(nums)
    # The outlines' lines and labels go on again over this wall's own cabinets,
    # below — see there.
    end_on = []
    for (x0, x1, z0, hgt, other), nums in shapes.items():
        end_on.append(f'<rect class="esideline" x="{X(x0):.1f}" y="{Y(z0 + hgt):.1f}" '
                      f'width="{(x1 - x0) * scale:.1f}" height="{hgt * scale:.1f}" '
                      f'fill="none" stroke="{MUTED}" stroke-width="0.8" '
                      f'stroke-dasharray="5 3" pointer-events="none"/>')
    # ONE label per neighbouring wall, over the top of everything of it that is
    # seen end on: "B: 11, 13". A label per outline put one number on top of
    # another wherever two outlines shared a top edge, and the one underneath
    # vanished — which is how cabinet 13 went unnamed on wall A.
    for other, (x0, x1, ztop, nums) in walls_seen.items():
        mid = (X(x0) + X(x1)) / 2
        end_on.append(f'<text class="esidelabel" data-wall="{escape(other)}" '
                      f'x="{mid:.1f}" y="{Y(ztop) - 4:.1f}" font-size="8.5" '
                      f'text-anchor="middle" fill="{MUTED}" pointer-events="none">'
                      f'{escape(other)}: '
                      f'{", ".join(map(str, sorted(nums)))}</text>')
    if shapes:
        out.append(f'<text x="{pad_l}" y="{H - 32 - leg}" font-size="8.5" fill="{MUTED}">'
                   f'Shaded outlines at the ends are the runs on the walls either side, '
                   f'seen end on, labelled with their wall and numbers.</text>')

    for c, p, lay, g in on_wall:
        z0 = carcass_z(c, p, std)
        cx, cy, cw, ch = X(p.x), Y(z0 + g.height), g.width * scale, g.height * scale
        look = board_look(job, c.carcass_board)
        stroke, sw, dash = _layer_outline(lay, c.number in bad)
        # One group per cabinet — the carcass, what is inside it and its number —
        # so a drag moves the whole thing rather than an empty outline.
        out.append(f'<g class="ecabg" data-cab="{c.number}">')
        out.append(f'<rect class="ecab" data-cab="{c.number}" x="{cx:.1f}" y="{cy:.1f}" '
                   f'width="{cw:.1f}" height="{ch:.1f}" fill="{fills.of(look, True)}" '
                   f'stroke="{stroke}" stroke-width="{sw}"{dash}/>')
        out += _interior(c, cx, cy, cw, ch, scale, std, flip=p.flip,
                         materials=job.materials, fills=fills)
        out.append(f'<text x="{cx + 4:.1f}" y="{cy + 11:.1f}" font-size="9.5" '
                   f'fill="{look["ink"]}">{c.number}</text>')
        if p.z == 0 and lay != "wall" and c.number not in boarded and cw >= 30:
            # no board covers these legs, so say what the space under the carcass is;
            # where each leg stands is not in Standard, so none is drawn
            out.append(f'<text x="{cx + cw / 2:.1f}" y="{Y(std.leg_height / 2) + 3:.1f}" '
                       f'font-size="8" text-anchor="middle" fill="{MUTED}">legs</text>')
        out.append('</g>')

    # One numbered part each, drawn in the board it is cut from, over the
    # cabinets. `carcass_z` is still the one answer to how high it really is —
    # a panel stands on no legs, so its z IS its underside, exactly as typed.
    for c, p, g in on_panels:
        spec = c.panel_spec
        z0 = carcass_z(c, p, std)
        px, py = X(p.x), Y(z0 + g.height)
        pw, ph = max(g.width * scale, 0.8), max(g.height * scale, 0.8)
        look = board_look(job, spec.board)
        crash = c.number in bad_panels
        stroke = CRIT if crash else INK
        out.append(f'<g class="ecabg epanel" data-cab="{c.number}">')
        vert = _panel_grain_vertical(spec)
        out.append(f'<rect class="epan" data-cab="{c.number}" x="{px:.1f}" y="{py:.1f}" '
                   f'width="{pw:.1f}" height="{ph:.1f}" fill="{fills.of(look, vert)}" '
                   f'stroke="{stroke}" stroke-width="{"2" if crash else "1.3"}"/>')
        if look["grain"] and not fills.textured(look) and vert is not None:
            out += _grain_lines(px, py, pw, ph, vert, look["ink"])
        # E4: a 16 mm panel is a few pixels of target. This is invisible, catches
        # the pointer for the whole group, and is what makes one grabbable at all.
        hw, hh = max(pw, PANEL_GRAB), max(ph, PANEL_GRAB)
        out.append(f'<rect class="ehit" x="{px + pw / 2 - hw / 2:.1f}" '
                   f'y="{py + ph / 2 - hh / 2:.1f}" width="{hw:.1f}" height="{hh:.1f}" '
                   f'fill="none" pointer-events="all"/>')
        # the number beside a thin panel, inside a fat one — either way legible
        line = panel_of(c, job.materials)
        if pw >= 26 and ph >= 22:
            out.append(f'<text x="{px + 4:.1f}" y="{py + 11:.1f}" font-size="9.5" '
                       f'fill="{look["ink"]}">{c.number}</text>')
            if ph >= 34:
                out.append(f'<text x="{px + 4:.1f}" y="{py + 21:.1f}" font-size="8" '
                           f'fill="{muted_on(look["colour"])}">'
                           f'{line.length}x{line.width}</text>')
        else:
            out.append(f'<text x="{px + pw + 3:.1f}" y="{py - 3:.1f}" font-size="8.5" '
                       f'fill="{INK}">{c.number} · {line.length}x{line.width}</text>')
        out.append('</g>')

    # A neighbour seen end on is often NEARER the viewer than this wall's own
    # front — a return run standing in front of a corner unit's far arm — so
    # its outline is drawn again over the top, dashed and unfilled, where it
    # can be seen, and its label with it. The fill stays underneath: the
    # drawing is still about this wall.
    out += end_on

    if any(c.door_count for c, _p, _lay, _g in on_wall):
        out.append(f'<text x="{pad_l}" y="{H - 20 - leg}" font-size="8.5" fill="{MUTED}">'
                   f'Hinges drawn {std.hinge_inset_drawn} mm in from each door end, any '
                   f'between spread evenly — indicative only, not a drilling reference.'
                   f'</text>')
    out += _tape_note(job, pad_l, H - 8 - leg, W - pad_l - pad_r)
    out += _legend_svg(rows, pad_l, H - leg + 2, fills)

    for ob in wall.obstructions:
        kind = escape(ob.kind)
        bx, by = X(ob.x - ob.width / 2), Y(ob.z + ob.height / 2)
        out.append(f'<rect class="obstruction" x="{bx:.1f}" y="{by:.1f}" '
                   f'width="{ob.width * scale:.1f}" height="{ob.height * scale:.1f}" '
                   f'fill="#f6e0e3" stroke="{CRIT}" stroke-width="1"/>')
        out.append(f'<text x="{bx + ob.width * scale + 4:.1f}" y="{by + 8:.1f}" '
                   f'font-size="8" fill="{CRIT}">{kind} @ {ob.x}, {ob.z} up</text>')

    out.append(f'<line x1="{X(0) - 10:.1f}" y1="{Y(0):.1f}" x2="{X(length) + 10:.1f}" '
               f'y2="{Y(0):.1f}" stroke="{INK}" stroke-width="1.8"/>')

    # dimensions: widths along the floor run, the wall units above, heights at the side
    fc = dims["floor_chain"]
    for a, b in zip(fc, fc[1:]):
        out += _dim_h(X(a), X(b), Y(0) + 24, b - a)
    out += _dim_h(X(0), X(length), Y(0) + 52, length)
    wc = dims["wall_chain"]
    for a, b in zip(wc, wc[1:]):
        out += _dim_h(X(a), X(b), Y(top) - 14, b - a)
    hc = dims["height_chain"]
    for a, b in zip(hc, hc[1:]):
        out += _dim_v(Y(b), Y(a), X(0) - 30, b - a)

    out[1] = f"<defs>{hatch}{fills.defs()}</defs>"
    out.append("</svg>")
    return "\n".join(out)


def plan_svg(job: Job, show=None, ghost=None, max_width: int = 1100,
             max_height: int = 620, isolate=None) -> str:
    """Plan of the room, looking down. Read-only.

    `show` is the layers drawn solid; `ghost` those drawn faint. A layer in
    neither is not drawn at all. Ghosting rather than hiding is deliberate — an
    overhead means nothing without the base run underneath it.

    Independent panels answer to the name `"panels"` in either list. It is not
    one of `room.LAYERS` — those are the three CABINET layers and `layer_of` is
    never asked about a panel — it is a fourth toggle over the top of them, and
    this is the only place that word means anything.

    `isolate` is one item's number, and it overrides both lists: that item is the
    only thing drawn solid and it is drawn whatever its layer is doing, so a
    cabinet that has landed underneath another one can be got at (21 September
    2026). Everything else is GHOSTED, not hidden — the same treatment the layer
    toggle already uses, because there is one convention for "not the focus" and
    a plan with the rest of the room taken out of it is not a plan. A panel is
    isolated exactly as a cabinet is: it is occluded the same way.

    Wall units draw dashed over the base run, which is the usual kitchen
    drawing convention.
    """
    rm = job.room
    if rm is None:
        return _note_svg("This job has no room")
    if len(rm.walls) < 2:
        return _note_svg("Add walls to see the plan")

    std = job.std
    show = tuple(LAYERS) if show is None else tuple(show)
    ghost = tuple(ghost or ())

    corners = corner_points(rm)
    # The isolated item is drawn whatever the layer toggle says about it: the
    # whole point is that selecting it from the list always reaches it.
    items = [(c, p, lay) for c, p, lay in placed(job)
             if lay in show or lay in ghost or c.number == isolate]
    # The plan is where `Placement.y` is actually visible: a panel standing off
    # the wall is drawn off the wall line.
    pans = [(c, p) for c, p in placed_panels(job)
            if "panels" in show or "panels" in ghost or c.number == isolate]
    # Isolating something this plan does not draw would grey out the whole room
    # for nothing. A newly added cabinet is exactly that case: it is selected,
    # and so isolated, before it has been given a wall.
    if isolate is not None and not any(
            c.number == isolate for c, _p, _l in items) and not any(
            c.number == isolate for c, _p in pans):
        isolate = None

    pts = list(corners)
    for cab, p, _ in items:
        pts += cabinet_footprint(rm, p, cab)
    for cab, p in pans:
        pts += cabinet_footprint(rm, p, cab, std, job.materials)
    xs = [q[0] for q in pts]
    ys = [q[1] for q in pts]
    pad = 54
    span_x = max(max(xs) - min(xs), 1)
    span_y = max(max(ys) - min(ys), 1)
    scale = min((max_width - pad * 2) / span_x, (max_height - pad * 2) / span_y)
    W = int(span_x * scale) + pad * 2
    rows = _legend_rows(job, _dedup([c.exterior_board for c, _p, _l in items] +
                                    [c.panel_spec.board for c, _p in pans]),
                        W - pad * 2)
    leg = _legend_height(rows)
    H = int(span_y * scale) + pad * 2 + leg

    def T(q):
        return (pad + (q[0] - min(xs)) * scale, pad + (q[1] - min(ys)) * scale)

    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
           f'viewBox="0 0 {W} {H}" font-family="system-ui,sans-serif">',
           '<defs><pattern id="hatch" width="6" height="6" '
           'patternUnits="userSpaceOnUse" patternTransform="rotate(45)">'
           f'<line x1="0" y1="0" x2="0" y2="6" stroke="{MUTED}" stroke-width="1.4"/>'
           '</pattern></defs>',
           f'<rect width="{W}" height="{H}" fill="none"/>']

    out += _plan_walls(rm, corners, T, scale)
    out += _plan_gaps(job, show, T)
    under_at = len(out)          # a wide panel's grab area goes here, under the cabinets
    # ghosted first so the selected layers sit on top of them
    if isolate is None:
        solid = [i for i in items if i[2] in show]
        faint = [i for i in items if i[2] in ghost and i[2] not in show]
    else:
        solid = [i for i in items if i[0].number == isolate]
        faint = [i for i in items if i[0].number != isolate]
    clashing = {c.cabinet for c in clashes(job, std)}
    colliding = {n for o in overlaps(job) for n in (o.a, o.b)}
    for cab, p, lay in faint:
        out += _plan_cabinet(rm, cab, p, lay, T, faint=True, bad=False,
                             colour=board_look(job, cab.exterior_board)["colour"],
                             deaf=isolate is not None)
    for cab, p, lay in solid:
        out += _plan_cabinet(rm, cab, p, lay, T, faint=False,
                             bad=cab.number in colliding,
                             colour=board_look(job, cab.exterior_board)["colour"])
    # over the cabinets, not under them: a swing that fouls something has to be
    # visible against the thing it fouls
    out += _plan_fronts(job, solid, clashing, T, std)
    # Panels over the cabinets, thin and in their own board's colour: a bulkhead
    # front is in front of the units it caps. Draggable here since 22 September
    # 2026, along the wall and off it, through a grab area of their own — see
    # `_plan_panel_hit`. A THIN one's grab area goes on top; a wide one (a
    # bulkhead underside over the run) was spliced in under the cabinets above,
    # so it never takes a press from a cabinet it lies over.
    bad_panels = {c.panel for c in panel_clashes(job, std)}
    live = [(cab, p) for cab, p in pans
            if (cab.number == isolate if isolate is not None else "panels" in show)]
    for cab, p in pans:
        out += _plan_panel(job, rm, cab, p, T, std,
                           faint=(cab.number != isolate if isolate is not None
                                  else "panels" not in show),
                           bad=cab.number in bad_panels)
    for cab, p in live:
        hit, thin = _plan_panel_hit(job, rm, cab, p, T, std, scale)
        if thin or cab.number == isolate:
            out += hit
        else:
            out[under_at:under_at] = hit
    # labels after every shape: an overhead sits over the base run it belongs to,
    # and a number you cannot read is worse than no number
    for cab, p, lay in solid:
        out += _plan_label(rm, cab, p, T)
    for cab, p in pans:
        if (cab.number == isolate if isolate is not None else "panels" in show):
            out += _plan_label(rm, cab, p, T, std, job.materials)
    out += _plan_plinths(job, show, T)
    out += _plan_obstructions(rm, T)
    out += _plan_tracks(rm, corners, T)
    out += _legend_svg(rows, pad, H - leg + 2)

    out.append("</svg>")
    return "\n".join(out)


def _plan_walls(rm, corners, T, scale):
    """Wall lines, their lengths, openings as breaks, obstructions as boxes."""
    out = []
    frames = wall_frames(rm)
    for i, w in enumerate(rm.walls):
        a, b = corners[i], corners[i + 1]
        (ax, ay), (bx, by) = T(a), T(b)
        spans = _wall_spans(w)
        for s0, s1 in spans:
            p0 = T(to_world(rm, w.id, s0, 0)[:2])
            p1 = T(to_world(rm, w.id, s1, 0)[:2])
            out.append(f'<line x1="{p0[0]:.1f}" y1="{p0[1]:.1f}" '
                       f'x2="{p1[0]:.1f}" y2="{p1[1]:.1f}" '
                       f'stroke="{INK}" stroke-width="3" stroke-linecap="square"/>')
        for op in w.openings:
            q0 = T(to_world(rm, w.id, op.x, 0)[:2])
            q1 = T(to_world(rm, w.id, op.x + op.width, 0)[:2])
            out.append(f'<line x1="{q0[0]:.1f}" y1="{q0[1]:.1f}" '
                       f'x2="{q1[0]:.1f}" y2="{q1[1]:.1f}" '
                       f'stroke="{RULE}" stroke-width="1" stroke-dasharray="3 3"/>')
            mid = ((q0[0] + q1[0]) / 2, (q0[1] + q1[1]) / 2)
            out.append(f'<text x="{mid[0]:.1f}" y="{mid[1] - 6:.1f}" font-size="8.5" '
                       f'text-anchor="middle" fill="{MUTED}">{escape(op.kind)} {op.width}</text>')
        # length label, pushed outside the room along the outward normal
        (_, _, (nx, ny)) = frames[w.id]
        mx, my = (ax + bx) / 2, (ay + by) / 2
        out.append(f'<text x="{mx - nx * 22:.1f}" y="{my - ny * 22 + 4:.1f}" font-size="10.5" '
                   f'text-anchor="middle" fill="{INK}">{escape(w.id)} · {w.length}</text>')
    return out


def _plan_gaps(job, show, T):
    """Fillers hatched, undecided gaps dimensioned in red.

    Red is for the ones still needing a ruling, not for the small ones: the app
    proposes and the user decides, so an undecided gap is the thing that wants
    attention regardless of its size.
    """
    out = []
    shown = {run_key(lay) for lay in show}
    for g in gaps(job, job.std):
        if g.layer not in shown:
            continue
        pts = [T(q) for q in gap_outline(job.room, g)]
        poly = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
        cx = sum(x for x, _ in pts) / 4
        cy = sum(y for _, y in pts) / 4
        if g.treatment == "filler":
            out.append(f'<polygon class="gap" points="{poly}" fill="url(#hatch)" '
                       f'stroke="{INK}" stroke-width="0.9"/>')
        elif g.treatment == "blind":
            out.append(f'<polygon class="gap" points="{poly}" fill="{FAINT}" '
                       f'stroke="{RULE}" stroke-width="0.9"/>')
            out.append(f'<text x="{cx:.1f}" y="{cy + 3:.1f}" font-size="7.5" '
                       f'text-anchor="middle" fill="{MUTED}">blind</text>')
        elif g.treatment == "open":
            continue                       # deliberately nothing there
        else:
            out.append(f'<polygon class="gap" points="{poly}" fill="none" stroke="{CRIT}" '
                       f'stroke-width="1.2" stroke-dasharray="4 3"/>')
            out.append(f'<text x="{cx:.1f}" y="{cy + 3:.1f}" font-size="8.5" '
                       f'text-anchor="middle" fill="{CRIT}">{g.width}</text>')
    return out


def _plan_plinths(job, show, T):
    """The plinth face, as a light line set back behind the door face.

    One line per board, so where a long run splits the joint shows on the plan
    in the same place the cut list says it is.
    """
    rm = job.room
    std = job.std
    out = []
    shown = {run_key(lay) for lay in show}
    for run in runs(job, std):
        if run.z != 0 or run.layer not in shown:
            continue
        choice = plinth_choice_for(job, run)
        if choice is None or not choice.fitted:
            continue
        y = max(run.depth - std.plinth_setback, 0)
        for length, at in plinth_lengths(job, run, std):
            p0 = T(to_world(rm, run.wall, at, y)[:2])
            p1 = T(to_world(rm, run.wall, at + length, y)[:2])
            out.append(f'<line x1="{p0[0]:.1f}" y1="{p0[1]:.1f}" '
                       f'x2="{p1[0]:.1f}" y2="{p1[1]:.1f}" '
                       f'stroke="{RULE}" stroke-width="2.2" stroke-linecap="butt"/>')
    return out


def _plan_fronts(job, solid, clashing, T, std):
    """Door swings and drawer pull-outs, hidden until the cabinet is hovered.

    Emitted for every cabinet rather than fetched on demand, so hovering costs
    nothing and the browser never has to work out an arc for itself. One that
    fouls something is drawn in red.
    """
    out = []
    for cab, p, _lay in solid:
        shapes = swing_envelopes(job, cab, p, std)
        pull = pullout_envelope(job, cab, p, std)
        if pull:
            shapes = shapes + [pull]
        if not shapes:
            continue
        bad = cab.number in clashing
        stroke = CRIT if bad else RULE
        parts = []
        for shape in shapes:
            pts = " ".join(f"{x:.1f},{y:.1f}" for x, y in (T(q) for q in shape))
            parts.append(f'<polygon points="{pts}" fill="{stroke}" fill-opacity="0.13" '
                         f'stroke="{stroke}" stroke-width="0.9"/>')
        out.append(f'<g class="front" data-front="{cab.number}" '
                   f'style="opacity:0">{"".join(parts)}</g>')
    return out


def _plan_tracks(rm, corners, T):
    """Invisible per-wall rails, so a drag knows where each wall is on screen.

    The browser projects the pointer onto one of these. Every number it needs —
    the wall's ends and its length — comes from here, computed by the engine.
    """
    frames = wall_frames(rm)
    out = ['<g id="tracks" style="pointer-events:none">']
    for i, w in enumerate(rm.walls):
        (ax, ay), (bx, by) = T(corners[i]), T(corners[i + 1])
        # The unit direction INTO THE ROOM off this wall, on the drawing. The
        # plan maps world onto the page with one scale and no flip, so it is the
        # wall's own normal; a panel's drag reads its depth off the wall with it.
        _s, _d, (nx, ny) = frames[w.id]
        out.append(f'<line class="track" data-wall="{escape(w.id)}" data-len="{w.length}" '
                   f'data-nx="{nx + 0.0:.6f}" data-ny="{ny + 0.0:.6f}" '
                   f'x1="{ax:.2f}" y1="{ay:.2f}" x2="{bx:.2f}" y2="{by:.2f}" '
                   f'stroke="none"/>')
    out.append("</g>")
    return out


def _plan_obstructions(rm, T):
    """Drawn last, over the cabinets. A waste pipe hidden behind a carcass is the
    one thing on this drawing you cannot afford to miss."""
    out = []
    for w in rm.walls:
        for ob in w.obstructions:
            depth = max(ob.proud, 60)
            c0 = T(to_world(rm, w.id, ob.x - ob.width // 2, 0)[:2])
            c1 = T(to_world(rm, w.id, ob.x + ob.width // 2, depth)[:2])
            x0, y0 = min(c0[0], c1[0]), min(c0[1], c1[1])
            out.append(f'<rect x="{x0:.1f}" y="{y0:.1f}" '
                       f'width="{abs(c1[0] - c0[0]):.1f}" height="{abs(c1[1] - c0[1]):.1f}" '
                       f'fill="#f6e0e3" stroke="{CRIT}" stroke-width="1"/>')
            out.append(f'<text x="{(c0[0] + c1[0]) / 2:.1f}" y="{(c0[1] + c1[1]) / 2 + 3:.1f}" '
                       f'font-size="7.5" text-anchor="middle" fill="{CRIT}">'
                       f'{escape(ob.kind[:4])}</text>')
    return out


def _wall_spans(w):
    """The solid stretches of a wall, with its openings taken out."""
    cuts = sorted((max(0, o.x), min(w.length, o.x + o.width)) for o in w.openings)
    spans = []
    at = 0
    for s0, s1 in cuts:
        if s0 > at:
            spans.append((at, s0))
        at = max(at, s1)
    if at < w.length:
        spans.append((at, w.length))
    return spans or [(0, w.length)]


def _dedup(ids) -> list:
    into = []
    for board_id in ids:
        _seen(into, board_id)
    return into


def _plan_cabinet(rm, cab, p, layer, T, faint, bad=False, colour=None,
                  deaf=False):
    """One footprint, tinted with the exterior board's colour.

    A tint, not a fill: the number and the size go on top of it, and a plan is
    read for where things are before it is read for what they are made of. The
    layer is in the outline, the way it is in the elevations — a tall unit drawn
    heavier, and a wall unit dashed. The plan keeps its own 5 3 dash rather than
    the elevations' 7 4: that is the kitchen-drawing convention it has always
    used and tools/check_room.py pins it.
    """
    fp = [T(q) for q in cabinet_footprint(rm, p, cab)]
    pts = " ".join(f"{x:.1f},{y:.1f}" for x, y in fp)
    _stroke, width, _dash = _layer_outline(layer, bad)
    dash = ' stroke-dasharray="5 3"' if layer == "wall" else ""
    fill = "#f6e0e3" if bad else (colour or NO_COLOUR)
    fill_op = ' fill-opacity="0.22"' if layer == "wall" else ' fill-opacity="0.35"'
    if bad:
        fill_op = ''
    op = ' opacity="0.30"' if faint else ""
    # `deaf` is isolate: ghosting alone would not be enough, because the item
    # that is hidden is hidden UNDER something, and that something would still
    # take the click. Only isolate sets it — a layer ghosted by the toggle keeps
    # its pointer events, which is what reveals its door swing on hover.
    ears = ' pointer-events="none"' if deaf else ""
    return [f'<polygon class="cab" data-cab="{cab.number}" data-layer="{layer}" '
            f'points="{pts}" fill="{fill}"{fill_op} '
            f'stroke="{_stroke}" stroke-width="{width}"{dash}{op}{ears}/>']


def _plan_panel(job, rm, cab, p, T, std, faint=False, bad=False):
    """One panel's footprint: a thin rectangle in the board it is cut from.

    16 mm on plan is under a pixel at most scales, so the outline is what is
    actually seen and the fill is there for the colour.

    It takes no pointer events itself. A panel is picked up by its grab area,
    `_plan_panel_hit`, which is placed so that a bulkhead underside 570 deep on
    plan never puts a sheet over the cabinets it caps. `data-panel` is what the
    drag moves with it.
    """
    fp = [T(q) for q in cabinet_footprint(rm, p, cab, std, job.materials)]
    pts = " ".join(f"{x:.1f},{y:.1f}" for x, y in fp)
    colour = board_look(job, cab.panel_spec.board)["colour"]
    op = ' opacity="0.30"' if faint else ""
    return [f'<polygon class="pan" data-panel="{cab.number}" points="{pts}" '
            f'fill="{"#f6e0e3" if bad else colour}" fill-opacity="0.9" '
            f'stroke="{CRIT if bad else INK}" pointer-events="none" '
            f'stroke-width="{"2" if bad else "1.3"}"{op}/>']


def _plan_panel_hit(job, rm, cab, p, T, std, scale):
    """The invisible area a panel is picked up by in the plan, and whether the
    panel is THIN there (either extent under `PANEL_GRAB` pixels).

    A 16 mm panel is under three pixels on plan, so, as in the elevation (E4),
    its footprint is grown about its middle to at least `PANEL_GRAB` pixels each
    way, in the wall's own frame so it turns with the wall. It carries `.cab` —
    one press handler, one `/api/drag` — with `data-layer="panels"`, which is the
    toggle that says whether it is live, and `data-panel` so the drag knows to
    move it off the wall as well as along it.
    """
    g = geometry(cab, std, job.materials)
    grow = PANEL_GRAB / max(scale, 1e-9)            # PANEL_GRAB pixels, in mm
    w, d = max(g.width, grow), max(g.depth, grow)
    x0 = p.x + g.width / 2 - w / 2
    y0 = int(getattr(p, "y", 0) or 0) + g.depth / 2 - d / 2
    pts = [T(to_world(rm, p.wall, x, y)[:2])
           for x, y in ((x0, y0), (x0 + w, y0), (x0 + w, y0 + d), (x0, y0 + d))]
    thin = min(g.width, g.depth) * scale < PANEL_GRAB
    return ([f'<polygon class="cab panhit" data-cab="{cab.number}" '
             f'data-panel="{cab.number}" data-layer="panels" '
             f'points="{" ".join(f"{x:.1f},{y:.1f}" for x, y in pts)}" '
             f'fill="none" stroke="none" pointer-events="all"/>'], thin)


def _plan_label(rm, cab, p, T, std: Standard = STANDARD, materials: dict = None):
    """Number and size at the middle of the outline, whatever shape it is."""
    fp = [T(q) for q in cabinet_footprint(rm, p, cab, std, materials)]
    cx = sum(x for x, _ in fp) / len(fp)
    cy = sum(y for _, y in fp) / len(fp)
    side = min(max(x for x, _ in fp) - min(x for x, _ in fp),
               max(y for _, y in fp) - min(y for _, y in fp))
    if cab.is_panel:
        # A panel is a few pixels across the thin way, so the number goes beside
        # it rather than in it — inside, `side <= 24` would drop every one.
        cx = max(x for x, _ in fp) + 4
        return [f'<text x="{cx:.1f}" y="{cy + 3:.1f}" font-size="9" '
                f'fill="{INK}">{cab.number}</text>']
    if side <= 24:
        return []
    g = geometry(cab, std, materials)
    out = [f'<text x="{cx:.1f}" y="{cy - 1:.1f}" font-size="10" '
           f'text-anchor="middle" fill="{INK}">{cab.number}</text>']
    if side > 40:
        out.append(f'<text x="{cx:.1f}" y="{cy + 10:.1f}" font-size="8" '
                   f'text-anchor="middle" fill="{MUTED}">{g.width}x{g.depth}</text>')
    return out


def _hinge_side(c: Cabinet, i: int, flip: bool) -> str:
    """Which edge door i hangs from, facing the cabinet: 'L' or 'R'.

    The one function room.swing_envelopes reads too, so the elevation and the
    plan's swing arcs cannot disagree: the per-leaf choice on the cabinet, or,
    with none set, a single door hanging left unless the placement is flipped and
    a pair hanging from its outer edges.
    """
    return hinge_side(c, i, c.door_count, bool(flip))


def _hinge_marks(c: Cabinet, x0, top, dw, dh, door_h, flip, std: Standard,
                 materials=None):
    """The opening triangle, point on the hinge side, the hinges and their count.

    The count is the pot-hole figure the cut list already orders. The positions
    follow the drawing rule ruled 14 Sept 2026 — hinge_inset_drawn in from each
    end, any between spread evenly — with low confidence, so they are marks on a
    picture and nothing more: pot holes are drilled to Plazaboard's hardware
    spec, and no order, drilling file or validation reads these.
    """
    out = []
    hinges = std.hinges(door_h)
    marks = std.hinge_positions(door_h)
    per_mm = dh / door_h
    for i in range(c.door_count):
        side = _hinge_side(c, i, flip)
        # on the leaf's own colour: a grey door swallows a muted mark
        mark = muted_on(board_look(materials or {}, c.door_board(i))["colour"])
        left, right = x0 + i * dw, x0 + i * dw + dw - 1
        hinge_x, latch_x = (left, right) if side == "L" else (right, left)
        out.append(f'<g class="hinge" data-cab="{c.number}" data-door="{i}" '
                   f'data-side="{side}">'
                   f'<polyline points="{latch_x:.1f},{top:.1f} {hinge_x:.1f},{top + dh / 2:.1f} '
                   f'{latch_x:.1f},{top + dh:.1f}" fill="none" stroke="{mark}" '
                   f'stroke-width="0.7" stroke-dasharray="3 2"/>')
        for mm in marks:                      # measured up from the bottom of the door
            out.append(f'<circle class="hinge-at" data-mm="{mm}" '
                       f'cx="{hinge_x + (3 if side == "L" else -3):.1f}" '
                       f'cy="{top + dh - mm * per_mm:.1f}" r="1.8" fill="{mark}"/>')
        if dh > 30 and dw > 34:
            tx = hinge_x + (5 if side == "L" else -5)
            anchor = "start" if side == "L" else "end"
            out.append(f'<text x="{tx:.1f}" y="{top + dh - 5:.1f}" font-size="7.5" '
                       f'text-anchor="{anchor}" fill="{mark}">{hinges} hinges</text>')
        out.append("</g>")
    return out


def _interior(c: Cabinet, x, y, w, h, scale, std: Standard, flip=None,
              materials=None, fills=None):
    """Doors, drawer faces and shelf lines, drawn from the bottom up.

    `flip` turns on the hinge marks and says which way a single door hangs. Left
    as None it draws exactly what the side-by-side sanity check always drew.

    `materials` is the job's board records. Every fill here is the colour of the
    board the cut list cuts that part from, resolved through `board_look`, and
    no colour is stated here: leaf *i* is `door_board(i)`, a drawer face is
    `face_board_of(d)`, and what is left of the body is the carcass board. With
    none passed the whole thing falls back to the neutral colour, so a caller
    that has no job still draws.

    `fills` is the drawing's `Fills`, which turns a grained board's picture into
    a tiled fill and collects the `<defs>` that needs. A caller with nowhere to
    put a `<defs>` passes none and gets flat colours, exactly as before.

    Two things here are handles rather than drawing: each door leaf carries its
    cabinet, its index and the edge it hangs from, so clicking it can turn it
    round; and each join between two drawer faces carries the pair's span in both
    mm and pixels, so a drag can be read back into millimetres. The browser
    projects onto them exactly as it projects onto the plan's wall tracks — it
    picks a position along a span the engine gave it, and the engine re-divides
    the stack on drop.
    """
    if c.corner_on and c.corner_kind in ("mitre", "ell", "blind"):
        return _corner_interior(c, x, y, w, h, scale, std, flip, materials, fills)
    out = []
    mats = materials or {}
    fills = fills or _FLAT
    body = board_look(mats, c.carcass_board)
    stack = c.drawer_list
    leaves = c.door_count
    door_h = 0
    if leaves:
        door_h = c.door_height or (c.height - std.door_height_gap)

    # The band round a front is the colour of the board its edging is named
    # from, and it is only there when the front carries edging at all — the same
    # answer the cut list gives, through the same chain.
    face_edge = (board_look(mats, c.drawer_face_edge_colour_board)["colour"]
                 if stack and c.drawer_face_tape(mats) else "")
    door_edge = (board_look(mats, c.door_edge_colour_board)["colour"]
                 if leaves and c.door_tape(mats) else "")

    cursor = y + h                      # bottom of the cabinet, in svg y
    tops = [0.0] * len(stack)           # svg y of each face's top edge
    for i in range(len(stack) - 1, -1, -1):
        d = stack[i]
        look = board_look(mats, c.face_board_of(d))
        fh = d.face_height * scale
        cursor -= fh
        tops[i] = cursor
        fx, fy, fw, fhh = x + 2, cursor + 1, w - 4, max(fh - 2, 1)
        out.append(f'<rect x="{fx:.1f}" y="{fy:.1f}" width="{fw:.1f}" '
                   f'height="{fhh:.1f}" fill="{fills.of(look, True)}" stroke="{RULE}" '
                   f'stroke-width="0.8"/>')
        if look["grain"] and not fills.textured(look):
            out += _grain_lines(fx, fy, fw, fhh, True, look["ink"])
        if face_edge:
            out += _edge_band(fx, fy, fw, fhh, face_edge)
        if fh > 13:
            out.append(f'<text x="{x + w / 2:.1f}" y="{cursor + fh / 2 + 3.5:.1f}" '
                       f'font-size="9" text-anchor="middle" '
                       f'fill="{muted_on(look["colour"])}">{d.face_height}</text>')
        cursor -= std.stack_gap * scale

    # the join between two faces, as a grab handle. Its span is the two faces and
    # the gap between them — dragging divides that span and leaves the rest alone.
    for k in range(len(stack) - 1):
        pair_mm = stack[k].face_height + std.stack_gap + stack[k + 1].face_height
        line_y = tops[k] + stack[k].face_height * scale + std.stack_gap * scale / 2
        out.append(f'<line class="fdiv" data-cab="{c.number}" data-above="{k}" '
                   f'data-below="{k + 1}" data-mm="{pair_mm}" '
                   f'data-top="{tops[k]:.2f}" data-px="{pair_mm * scale:.2f}" '
                   f'x1="{x + 2:.1f}" y1="{line_y:.2f}" x2="{x + w - 2:.1f}" '
                   f'y2="{line_y:.2f}" stroke="{RULE}" stroke-width="5" '
                   f'stroke-opacity="0" pointer-events="stroke"/>')

    if leaves:
        dh = door_h * scale
        top = cursor - dh
        dw = (w - 4) / leaves
        for i in range(leaves):
            side = _hinge_side(c, i, bool(flip))
            look = board_look(mats, c.door_board(i))
            dx = x + 2 + i * dw
            out.append(f'<rect class="edoor" data-cab="{c.number}" data-door="{i}" '
                       f'data-hinge="{side}" x="{dx:.1f}" y="{top:.1f}" '
                       f'width="{dw - 1:.1f}" height="{dh:.1f}" '
                       f'fill="{fills.of(look, True)}" stroke="{RULE}" stroke-width="0.8"/>')
            if look["grain"] and not fills.textured(look):
                out += _grain_lines(dx, top, dw - 1, dh, True, look["ink"])
            if door_edge:
                out += _edge_band(dx, top, dw - 1, dh, door_edge)
        if flip is not None:
            out += _hinge_marks(c, x + 2, top, dw, dh, door_h, flip, std, mats)
        if dh > 20:
            lead = board_look(mats, c.door_board(0))
            out.append(f'<text x="{x + w / 2:.1f}" y="{top + dh / 2 + 3.5:.1f}" '
                       f'font-size="9" text-anchor="middle" '
                       f'fill="{muted_on(lead["colour"])}">'
                       f'{leaves} x {std.door_width(c.width, leaves)}</text>')
        cursor = top

    # shelves, spread through whatever the doors cover. Their ink follows the
    # body's colour: a hairline in FAINT vanishes on a dark carcass.
    inside = muted_on(body["colour"])
    n = c.shelves + c.fixed_shelves
    if n and not stack:
        span = y + h - cursor if leaves else h
        base = cursor if leaves else y
        for i in range(1, n + 1):
            sy = base + span * i / (n + 1)
            out.append(f'<line x1="{x + 4:.1f}" y1="{sy:.1f}" x2="{x + w - 4:.1f}" '
                       f'y2="{sy:.1f}" stroke="{inside}" stroke-width="1" '
                       f'stroke-opacity="0.55" stroke-dasharray="4 3"/>')
    if c.divider_count:
        out.append(f'<line x1="{x + w / 2:.1f}" y1="{y + 4:.1f}" x2="{x + w / 2:.1f}" '
                   f'y2="{y + h - 4:.1f}" stroke="{inside}" stroke-width="1.2" '
                   f'stroke-opacity="0.55"/>')
    return out


def _corner_interior(c: Cabinet, x, y, w, h, scale, std: Standard, flip=None,
                     materials=None, fills=None):
    """A corner unit's front, seen square on to the wall it is placed on.

    Before 22 September 2026 a corner unit went through the straight-cabinet
    drawing and came out as one door the full declared width ("1 x 1197" on a
    mitre whose real door is 543). What is drawn now:

    * MITRE - the door where it really is, seen at its angle: across the stretch
      of wall the mitre face covers, which is shorter than the door itself. It is
      labelled with its REAL width and cross-hatched lightly, the drafting sign
      for a face that is not square on to you. Beyond it, the unit's open-face
      side on the return wall, plain carcass.
    * BLIND - the corner-end side edge, the flush panel inside the carcass
      beside it, and the overlay door lapping onto that panel's face. Every
      figure is `room.blind_spans`, so the drawing cannot lay the unit out
      differently from the cut list.
    * ELL - the box only: its construction is not decided, so there is no front
      to draw, and it says so.

    Every millimetre is the engine's (`geometry`, `blind_spans`); `w` is
    already the unit's real reach along the wall, so x is scaled off it.
    """
    out = []
    mats = materials or {}
    fills = fills or _FLAT
    g = geometry(c, std, mats)
    kind, hand = c.corner_kind, c.hand
    t = std.board_t
    door_h = c.door_height or (c.height - std.door_height_gap)
    dh = door_h * scale
    top = y + h - dh
    px = lambda mm: x + mm * scale          # noqa: E731 - cabinet-local mm to svg x
    door_edge = (board_look(mats, c.door_edge_colour_board)["colour"]
                 if c.door_tape(mats) else "")

    def leaf(x0, x1, i, angled, text):
        look = board_look(mats, c.door_board(i))
        lw = max(x1 - x0, 1)
        out.append(f'<rect class="edoor" data-cab="{c.number}" data-door="{i}" '
                   f'x="{x0:.1f}" y="{top:.1f}" width="{lw:.1f}" height="{dh:.1f}" '
                   f'fill="{fills.of(look, True)}" stroke="{RULE}" stroke-width="0.8"/>')
        if door_edge:
            out.extend(_edge_band(x0, top, lw, dh, door_edge))
        ink = muted_on(look["colour"])
        if angled:
            step = 9.0
            k = 0.0
            while k < lw + dh:
                ax0, ay0 = x0 + max(0.0, k - dh), top + min(dh, k)
                ax1, ay1 = x0 + min(lw, k), top + max(0.0, k - lw)
                out.append(f'<line x1="{ax0:.1f}" y1="{ay0:.1f}" x2="{ax1:.1f}" '
                           f'y2="{ay1:.1f}" stroke="{ink}" stroke-width="0.5" '
                           f'stroke-opacity="0.35"/>')
                k += step
        if text and dh > 20:
            out.append(f'<text x="{x0 + lw / 2:.1f}" y="{top + dh / 2 + 3.5:.1f}" '
                       f'font-size="9" text-anchor="middle" fill="{ink}" '
                       f'paint-order="stroke" stroke="{look["colour"]}" stroke-width="3">'
                       f'{escape(text)}</text>')
        return lw

    if kind == "mitre" and g.source == "corner":
        a, fb = int(c.arm_a), int(c.face_b)
        # where the door's inside line runs, projected onto this wall
        s0, s1 = (t, a - fb) if hand == "R" else (fb, a - t)
        doors = g.door_widths if c.door_count else []
        n = len(doors)
        if n:
            span = (s1 - s0) * scale / n
            for i in range(n):
                x0 = px(s0) + i * span
                leaf(x0, x0 + span, i, True, f"{doors[i]}")
            if flip is not None:
                out += _hinge_marks(c, px(s0), top, span, dh, door_h, flip, std, mats)
        # The open-face side at the end of the other arm, square on to this
        # wall: part of this cabinet, drawn in the board it is cut from and
        # nothing else. It used to carry a "side on the return wall" label,
        # which read as a second, different thing standing in the corner —
        # every wall now draws a neighbour the one way, as an outline end on.
        e0, e1 = (a - fb, a) if hand == "R" else (0, fb)
        out.append(f'<line x1="{px(e0 if hand == "R" else e1):.1f}" y1="{y:.1f}" '
                   f'x2="{px(e0 if hand == "R" else e1):.1f}" y2="{y + h:.1f}" '
                   f'stroke="{RULE}" stroke-width="0.8"/>')
    elif kind == "blind":
        B = int(c.blind_width or 0)
        spans = blind_spans(c, std)
        if B > 0 and spans:
            (s0, s1), (b0, b1), (d0, d1) = spans
            # The corner-end side panel's front edge. It is only one board wide,
            # but it is what the flush front runs into, so it is drawn rather
            # than left as bare carcass: the panel no longer reaches the corner.
            body = board_look(mats, c.carcass_board)
            out.append(f'<rect class="eside" x="{px(s0):.1f}" y="{top:.1f}" '
                       f'width="{(s1 - s0) * scale:.1f}" height="{dh:.1f}" '
                       f'fill="{fills.of(body, True)}" stroke="{RULE}" '
                       f'stroke-width="0.8"/>')
            # The flush panel, in ITS OWN board, across its full B. The door is
            # drawn over it afterwards, so what is left showing is exactly the
            # strip the door does not cover — which is what you see in the room.
            look = board_look(mats, c.blind_panel_board)
            out.append(f'<rect class="eblind" x="{px(b0):.1f}" y="{top:.1f}" '
                       f'width="{(b1 - b0) * scale:.1f}" height="{dh:.1f}" '
                       f'fill="{fills.of(look, True)}" stroke="{INK}" stroke-width="0.9"/>')
            if c.door_count:
                dw = int(round(d1 - d0))
                leaf(px(d0), px(d1), 0, False, f"1 x {dw}")
                if flip is not None:
                    out += _hinge_marks(c, px(d0), top, (d1 - d0) * scale + 1, dh,
                                        door_h, flip, std, mats)
            # The label goes on the strip that is still showing, not on the
            # middle of a panel whose middle is behind the door.
            shown = ((b0, min(b1, d0)) if hand == "L" else (max(b0, d1), b1))
            if dh > 20 and (shown[1] - shown[0]) * scale > 30:
                out.append(f'<text x="{px(sum(shown) / 2):.1f}" '
                           f'y="{top + dh / 2 + 3.5:.1f}" '
                           f'font-size="9" text-anchor="middle" '
                           f'fill="{muted_on(look["colour"])}">blind {B}</text>')
    else:
        why = ("ell corner: construction not decided yet" if kind == "ell"
               else "fix the corner measurements")
        out.append(f'<text x="{x + w / 2:.1f}" y="{y + h / 2:.1f}" font-size="9" '
                   f'text-anchor="middle" fill="{CRIT}">{escape(why)}</text>')
    return out


def _edge_band(x, y, w, h, colour):
    """The edging on a front, as a thin line just inside its outline.

    Inside rather than instead of the outline: a door edged in its own colour
    would otherwise have nothing to show, and the front would lose its edge.
    """
    if w < 4 or h < 4:
        return []
    return [f'<rect class="eband" x="{x + 1:.1f}" y="{y + 1:.1f}" '
            f'width="{w - 2:.1f}" height="{h - 2:.1f}" fill="none" '
            f'stroke="{colour}" stroke-width="1.3"/>']
