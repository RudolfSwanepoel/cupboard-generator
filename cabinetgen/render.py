"""Front elevation of a job, as SVG.

Cabinets are drawn side by side to scale, with doors, drawer faces and shelf
lines shown. It is a sanity check, not a working drawing: if a cabinet looks
wrong here it is wrong in the cut list too.
"""
import math
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
                   runs, swing_envelopes, to_world, wall_frames, wall_height,
                   is_closed, blind_spans, front_outlines, return_faces,
                   polygons_overlap)
from .standard import Standard, STANDARD

INK = "#191c1a"
RULE = "#aab1a9"
FAINT = "#d3d7d0"
MUTED = "#767e78"
CRIT = "#a4303f"

PAPER = "#ffffff"
# The room side of a wall, shown (room redo Phase 1, 2 October 2026): a closed
# room's floor tinted, an open run's or a free wall's face side a band of
# ROOM_BAND_MM fading out, so which side the room is on can be seen and
# pointed at. Drawing only.
ROOM_TINT = "#cfe0f6"
ROOM_BAND_MM = 300

# Line weights, in screen pixels, for the plan and every elevation — one table,
# read by both (23 September 2026, brief item 3, confirmed by Rudolf). Every
# stroke is drawn with `vector-effect: non-scaling-stroke` (`STROKE_STYLE`), so
# zooming in makes the geometry bigger and leaves the lines at these weights —
# which is what makes a 16 mm panel readable between two carcasses.
#
# Base, wall and tall are no longer told apart by the outline in an elevation:
# the drawing already says which is which by where each one stands, and a
# heavier or dashed carcass line only competed with the fronts. A clash is
# still red and heavy.
WEIGHT = {"wall": "2", "carcass": "1", "panel": "0.75", "face": "0.75",
          "internal": "0.5", "above": "0.75", "dim": "0.5", "clash": "2"}
# Dashes only where they say something a solid line cannot (Rudolf: "no dashed
# lines unless they add real value"): a wall unit ABOVE the plan's cut, an
# opening across a wall line in plan, a neighbour seen through this wall's own
# units in the Line view, and an undecided gap. Everything else is solid.
ABOVE_DASH = ' stroke-dasharray="4 3"'
STROKE_STYLE = ('<style>.drw line,.drw rect,.drw polygon,.drw polyline,.drw circle,'
                '.drw path{vector-effect:non-scaling-stroke}'
                '.drw pattern *{vector-effect:none}</style>')
LEGEND_ROW = 15

# How a wall elevation is drawn — a view setting, never saved in the job and
# never a change to any geometry (23 September 2026, replacing the 22 September
# white-and-grey Line view, which was a misreading). Both draw this wall's own
# cabinets identically; they differ ONLY in the runs on the walls either side.
# LINE shows them as grey outlines end on, labelled with their wall and numbers.
# FINISH shows them as they would really be seen from this wall: every board
# face turned towards you, in the board it is cut from (`room.return_faces`).
VIEW_MODES = ("line", "finish")


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
                       f'stroke="{ink}" stroke-width="{WEIGHT["internal"]}" stroke-opacity="0.22"/>')
        else:
            out.append(f'<line x1="{x + 1:.1f}" y1="{y + at:.1f}" '
                       f'x2="{x + w - 1:.1f}" y2="{y + at:.1f}" '
                       f'stroke="{ink}" stroke-width="{WEIGHT["internal"]}" stroke-opacity="0.22"/>')
    return out


# A 16 mm panel is about four pixels wide on a wall elevation, which is nothing
# to aim a pointer at. Every panel carries an invisible rectangle at least this
# many pixels across so it can actually be picked up.
PANEL_GRAB = 16


# How big a board picture is tiled on a drawing, in pixels. Nothing reads it and
# it is not a dimension: it is how big the swatch is drawn. Small enough that a
# door shows the grain running rather than one smeared close-up of it.
PICTURE_TILE = 40

# The same tile in the 3D view, in MILLIMETRES of board (23 September 2026).
# An SVG has no real-world tile size — `PICTURE_TILE` is drawing pixels at
# whatever scale the drawing happens to be — so the 3D view, which draws in
# millimetres, needs the figure stated once. This is what 40 px comes to on a
# wall elevation at its usual scale (a 4 m wall in 1100 px). A drawing
# constant, sent to the browser with each board's look; nothing else reads it.
PICTURE_TILE_MM = 160

# The Run: the cabinets side by side, `RUN_GAP` mm apart, each at the width
# `run_widths` gives it. The 3D view with no room stands its cabinets on the
# same layout (`run_layout`) rather than deriving one of its own.
RUN_GAP = 20


def run_widths(job: Job, cabs) -> dict:
    """Number -> width along the Run. A corner unit's width along its wall is
    its geometry, never the declared label (hard rule 1): a mitre drawn at its
    declared 1200 when its arm is 1000 was one of the things that made the
    corner unit look broken."""
    return {c.number: (geometry(c, job.std, job.materials).width if c.corner_on else c.width)
            for c in cabs}


def run_layout(job: Job) -> list:
    """`(cabinet, x)` for every cabinet in the Run, in list order, `x` being
    where it starts along the run in mm. Panels are not in it — a panel has no
    place in a line of carcasses — exactly as `elevation_svg` leaves them out."""
    cabs = [c for c in job.cabinets if not c.is_panel]
    gw = run_widths(job, cabs)
    out, x = [], 0
    for c in cabs:
        out.append((c, x))
        x += gw[c.number] + RUN_GAP
    return out


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
    """Stroke colour, width and dash for a carcass outline in an elevation:
    `(ink, width, dash)`. One weight for every layer (`WEIGHT`) and no dash —
    an elevation shows which is which by where each one stands. A clash is red
    and heavy."""
    return (CRIT, WEIGHT["clash"], "") if bad else (INK, WEIGHT["carcass"], "")


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
        # capitals are wider than the 4.9 a character this used to allow, and a
        # board name in capitals ran into the next swatch
        entry = (look, text, 17 + sum(6.0 if ch.isupper() else 4.9 for ch in text) + 16)
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
                       f'stroke="{RULE}" stroke-width="{WEIGHT["internal"]}"/>')
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
                  pictures: str = PIC.ROUTE, mode: str = "line") -> str:
    """The Run: the cabinet list drawn side by side.

    `mode` is accepted and changes nothing: the two views differ only in how the
    walls either side are drawn, and the Run has none (`VIEW_MODES`).

    Panels are not in it, deliberately. A panel is not part of a cupboard run —
    it has no place in a line of carcasses — and keeping it out is also what
    keeps `wall_elevation_svg` with no room equal to this drawing, which
    tools/check_elevation.py asserts.

    `pictures` is where a board picture is fetched from — see `Fills`.
    """
    return _elevation_svg(job, max_width, pictures)


def _elevation_svg(job: Job, max_width: int, pictures: str) -> str:
    cabs = [c for c in job.cabinets if not c.is_panel]
    # A corner unit's width along its wall is its geometry, never the declared
    # label (hard rule 1): a mitre drawn at its declared 1200 when its arm is 1000
    # was one of the things that made the corner unit look broken.
    gw = run_widths(job, cabs)
    if not cabs:
        return ('<svg xmlns="http://www.w3.org/2000/svg" width="200" height="60">'
                f'<text x="10" y="34" font-size="13" fill="{MUTED}" '
                'font-family="sans-serif">No cabinets yet</text></svg>')

    std = job.std
    gap_mm = RUN_GAP
    total_w = sum(gw[c.number] for c in cabs) + gap_mm * (len(cabs) - 1)
    max_h = max(c.height for c in cabs)
    pad = 46
    scale = min((max_width - pad * 2) / total_w, 520 / max_h)
    W = int(total_w * scale) + pad * 2
    rows = _legend_rows(job, _boards_drawn(job, cabs), W - pad * 2)
    leg = _legend_height(rows)
    H = int(max_h * scale) + pad * 2 + 14 + leg   # under the floor: tapes, then boards

    fills = Fills(base=pictures)
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" class="drw" width="{W}" height="{H}" '
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
               f'stroke="{INK}" stroke-width="{WEIGHT["wall"]}"/>')
    out += _tape_note(job, pad, H - 8 - leg, W - pad * 2)
    out += _legend_svg(rows, pad, H - leg + 2, fills)
    out[defs_at] = f"{STROKE_STYLE}<defs>{fills.defs()}</defs>"
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
            f'stroke="{INK}" stroke-width="{WEIGHT["dim"]}"/>')


def _dim_h(x0, x1, y, value):
    out = [f'<line x1="{x0:.1f}" y1="{y:.1f}" x2="{x1:.1f}" y2="{y:.1f}" '
           f'stroke="{MUTED}" stroke-width="{WEIGHT["dim"]}"/>', _tick(x0, y), _tick(x1, y)]
    if x1 - x0 >= 18:
        out.append(f'<text class="dim" x="{(x0 + x1) / 2:.1f}" y="{y - 4:.1f}" '
                   f'font-size="8.5" text-anchor="middle" fill="{INK}">{value}</text>')
    return out


def _dim_v(y_top, y_bot, x, value):
    out = [f'<line x1="{x:.1f}" y1="{y_top:.1f}" x2="{x:.1f}" y2="{y_bot:.1f}" '
           f'stroke="{MUTED}" stroke-width="{WEIGHT["dim"]}"/>', _tick(x, y_top), _tick(x, y_bot)]
    if y_bot - y_top >= 18:
        mid = (y_top + y_bot) / 2
        out.append(f'<text class="dim" x="{x - 4:.1f}" y="{mid:.1f}" font-size="8.5" '
                   f'text-anchor="middle" fill="{INK}" '
                   f'transform="rotate(-90 {x - 4:.1f} {mid:.1f})">{value}</text>')
    return out


def wall_elevation_svg(job: Job, wall_id: str, max_width: int = 1100,
                       pictures: str = PIC.ROUTE, mode: str = "line") -> str:
    """One wall, face on, as a dimensioned working drawing.

    Cabinets at their true positions and heights, with the wall, its openings and
    obstructions behind them, and the fillers and plinth boards that were chosen.
    Widths are chained from the wall's start corner and heights from the floor.
    With no room there is no datum, so it falls back to the side-by-side sanity
    check, unchanged. `pictures` is where a board picture is fetched from —
    see `Fills`. `mode` is the view, "line" (the default) or "finish" — see
    `VIEW_MODES`; the two differ only in how the walls either side are drawn.

    Every wall is drawn by the same rule, whatever the room's shape: standing in
    the room facing this wall, left and right as you see them, what is placed on
    it is drawn in full; the runs on the walls either side of it — found off the
    room's chain of corners (`return_profiles`), never off a letter — are grey
    outlines end on at the ends they meet it (Line) or what you would see of
    them from here, in their boards (Finish), labelled with their wall and their
    numbers; and an end with no wall beside it has nothing drawn there. A corner
    unit belongs to the wall it is placed on: drawn in full there, an outline
    end on everywhere else.
    """
    rm = job.room
    if rm is None:
        return elevation_svg(job, max_width, pictures, mode)
    return _wall_elevation_svg(job, wall_id, max_width, pictures, mode == "finish")


def _wall_elevation_svg(job: Job, wall_id: str, max_width: int, pictures: str,
                        finish: bool) -> str:
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
    faces = return_faces(job, wall_id, std) if finish else []
    drawn = _boards_drawn(job, [c for c, _p, _l, _g in on_wall] +
                          [c for c, _p, _g in on_panels])
    for f in faces:                  # Finish puts the neighbours' boards on the paper too
        _seen(drawn, f["board"])
    rows = _legend_rows(job, drawn, W - pad_l - pad_r)
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
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" class="drw" width="{W}" height="{H}" '
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

    # the wall itself, to ITS height (`Wall.height`, 2 October 2026; the ceiling
    # where none is set), and the ceiling as a datum line — only if measured —
    # dashed above a wall that stops short of it
    wh = wall_height(rm, wall)
    if wh:
        out.append(f'<rect x="{X(0):.1f}" y="{Y(wh):.1f}" '
                   f'width="{length * scale:.1f}" height="{wh * scale:.1f}" '
                   f'fill="none" stroke="{INK}" stroke-width="{WEIGHT["wall"]}"/>')
    if rm.ceiling and wh and wh < rm.ceiling:
        out.append(f'<line class="ceilingline" x1="{X(0):.1f}" y1="{Y(rm.ceiling):.1f}" '
                   f'x2="{X(length):.1f}" y2="{Y(rm.ceiling):.1f}" '
                   f'stroke="{RULE}" stroke-width="{WEIGHT["internal"]}" stroke-dasharray="6 4"/>')

    for op in wall.openings:
        kind = escape(op.kind)
        ox, oy = X(op.x), Y(op.head)
        ow, oh = op.width * scale, (op.head - op.sill) * scale
        out.append(f'<rect class="opening" x="{ox:.1f}" y="{oy:.1f}" width="{ow:.1f}" '
                   f'height="{oh:.1f}" fill="#fff" stroke="{RULE}" '
                   f'stroke-width="{WEIGHT["internal"]}"/>')
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
                       f'fill="{FAINT}" stroke="{RULE}" stroke-width="{WEIGHT["internal"]}"/>')

    for g in gaps(job, std):
        if g.wall != wall_id or g.treatment not in ("filler", "blind"):
            continue
        bound = everywhere.get(g.after if g.after is not None else g.before)
        z0 = carcass_z(bound[0], bound[1], std) if bound else 0
        gx, gy, gw, gh = X(g.x), Y(z0 + g.height), g.nominal * scale, g.height * scale
        if g.treatment == "filler":
            out.append(f'<rect class="filler" x="{gx:.1f}" y="{gy:.1f}" width="{gw:.1f}" '
                       f'height="{gh:.1f}" fill="url(#ehatch)" stroke="{INK}" '
                       f'stroke-width="{WEIGHT["panel"]}"/>')
            label = f"filler {g.filler_width(std)}"
        else:
            out.append(f'<rect class="blind" x="{gx:.1f}" y="{gy:.1f}" width="{gw:.1f}" '
                       f'height="{gh:.1f}" fill="{FAINT}" stroke="{RULE}" '
                       f'stroke-width="{WEIGHT["panel"]}"/>')
            label = "blind"
        if gw >= 12:
            out.append(f'<text x="{gx + gw / 2:.1f}" y="{gy + gh / 2:.1f}" font-size="8" '
                       f'text-anchor="middle" fill="{INK}" '
                       f'transform="rotate(-90 {gx + gw / 2:.1f} {gy + gh / 2:.1f})">'
                       f'{label}</text>')

    # The runs on the walls either side. `return_profiles` is what says which
    # cabinets they are and where, in both views: the one label per wall comes
    # off it. LINE draws them as it always has — light see-through outlines end
    # on, under this wall's own cabinets, with their lines again over the top.
    # FINISH draws what you would see of them from here (`_finish_faces`).
    shapes, walls_seen = {}, {}
    for r in return_profiles(job, wall_id, std):
        shapes.setdefault((r["x0"], r["x1"], r["z0"], r["height"], r["wall"]),
                          []).append(r["cabinet"])
    for (x0, x1, z0, hgt, other), nums in shapes.items():
        if not finish:
            sx, sy, sw_, sh = X(x0), Y(z0 + hgt), (x1 - x0) * scale, hgt * scale
            out.append(f'<g class="eside" data-wall="{escape(other)}" '
                       f'data-cabs="{" ".join(map(str, nums))}">'
                       f'<rect x="{sx:.1f}" y="{sy:.1f}" width="{sw_:.1f}" height="{sh:.1f}" '
                       f'fill="{FAINT}" fill-opacity="0.35" stroke="{MUTED}" '
                       f'stroke-width="{WEIGHT["above"]}"/>')
            out.append('</g>')
        seen = walls_seen.setdefault(other, [x0, x1, z0 + hgt, set()])
        seen[0], seen[1] = min(seen[0], x0), max(seen[1], x1)
        seen[2] = max(seen[2], z0 + hgt)
        seen[3].update(nums)
    # The outlines' lines and labels go on again over this wall's own cabinets,
    # below — see there.
    end_on = []
    if finish:
        under, over = _finish_faces(job, faces, on_wall, on_panels, X, Y, scale, fills)
        out += under
        end_on += over
    else:
        for (x0, x1, z0, hgt, other), nums in shapes.items():
            end_on.append(f'<rect class="esideline" x="{X(x0):.1f}" y="{Y(z0 + hgt):.1f}" '
                          f'width="{(x1 - x0) * scale:.1f}" height="{hgt * scale:.1f}" '
                          f'fill="none" stroke="{MUTED}" stroke-width="{WEIGHT["above"]}"'
                          f'{ABOVE_DASH} pointer-events="none"/>')
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
        note = ("Cabinets on the walls either side, as seen from this wall, each "
                "face in the board it is cut from." if finish else
                "Shaded outlines at the ends are the runs on the walls either side, "
                "seen end on, labelled with their wall and numbers.")
        out.append(f'<text x="{pad_l}" y="{H - 32 - leg}" font-size="8.5" fill="{MUTED}">'
                   f'{note}</text>')

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
    late = []
    for c, p, g in on_panels:
        spec = c.panel_spec
        z0 = carcass_z(c, p, std)
        px, py = X(p.x), Y(z0 + g.height)
        pw, ph = max(g.width * scale, 0.8), max(g.height * scale, 0.8)
        look = board_look(job, spec.board)
        crash = c.number in bad_panels
        stroke = CRIT if crash else INK
        out.append(f'<g class="ecabg epanel" data-cab="{c.number}"{_host_attr(c)}>')
        vert = _panel_grain_vertical(spec)
        out.append(f'<rect class="epan" data-cab="{c.number}" x="{px:.1f}" y="{py:.1f}" '
                   f'width="{pw:.1f}" height="{ph:.1f}" fill="{fills.of(look, vert)}" '
                   f'stroke="{stroke}" '
                   f'stroke-width="{WEIGHT["clash"] if crash else WEIGHT["panel"]}"/>')
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
            # beside the panel, so drawn last of all: over a neighbour's faces
            # in the Finish view rather than lost underneath them
            late.append(f'<text class="eplabel" data-cab="{c.number}" '
                        f'x="{px + pw + 3:.1f}" y="{py - 3:.1f}" font-size="8.5" '
                        f'fill="{INK}" pointer-events="none">{c.number} · '
                        f'{line.length}x{line.width}</text>')
        out.append('</g>')

    # A neighbour seen end on is often NEARER the viewer than this wall's own
    # front — a return run standing in front of a corner unit's far arm — so
    # its outline is drawn again over the top, dashed and unfilled, where it
    # can be seen, and its label with it. The fill stays underneath: the
    # drawing is still about this wall.
    out += end_on
    out += late

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
               f'y2="{Y(0):.1f}" stroke="{INK}" stroke-width="{WEIGHT["wall"]}"/>')

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

    out[1] = f"{STROKE_STYLE}<defs>{hatch}{fills.defs()}</defs>"
    out.append("</svg>")
    return "\n".join(out)


def _oblique_hatch(x0, top, w, h, ink, step=9.0):
    """Light diagonal lines across a face that is not square on to you — the
    drafting sign `_corner_interior` has used on a mitre door since 22 Sept."""
    out = []
    k = 0.0
    while k < w + h:
        ax0, ay0 = x0 + max(0.0, k - h), top + min(h, k)
        ax1, ay1 = x0 + min(w, k), top + max(0.0, k - w)
        out.append(f'<line x1="{ax0:.1f}" y1="{ay0:.1f}" x2="{ax1:.1f}" '
                   f'y2="{ay1:.1f}" stroke="{ink}" stroke-width="{WEIGHT["internal"]}" '
                   f'stroke-opacity="0.35"/>')
        k += step
    return out


def _face_svg(job: Job, f: dict, X, Y, scale, fills) -> list:
    """One face of a neighbouring run, as the Finish view paints it: in the
    board it is cut from, hatched when seen at an angle, and a mitre door's
    real width on it. No hinges, swings or drawer sizes — seen end on or at an
    angle they would be foreshortened, and misleading."""
    look = board_look(job, f["board"])
    x, y = X(f["x0"]), Y(f["z1"])
    w = max((f["x1"] - f["x0"]) * scale, 0.8)
    h = max((f["z1"] - f["z0"]) * scale, 0.8)
    out = [f'<rect class="eface" data-cab="{f["cabinet"]}" data-role="{f["role"]}" '
           f'data-wall="{escape(f["wall"])}" x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" '
           f'height="{h:.1f}" fill="{fills.of(look, f["vertical"])}" stroke="{INK}" '
           f'stroke-width="{WEIGHT["face"]}" pointer-events="none"/>']
    if look["grain"] and not fills.textured(look) and f["vertical"] is not None:
        out += _grain_lines(x, y, w, h, f["vertical"], look["ink"])
    ink = muted_on(look["colour"])
    if f["oblique"]:
        out += _oblique_hatch(x, y, w, h, ink)
    if f["label"] and h > 20 and w > 18:
        out.append(f'<text x="{x + w / 2:.1f}" y="{y + h / 2 + 3.5:.1f}" font-size="9" '
                   f'text-anchor="middle" fill="{ink}" paint-order="stroke" '
                   f'stroke="{look["colour"]}" stroke-width="3" pointer-events="none">'
                   f'{escape(f["label"])}</text>')
    return out


def _finish_faces(job: Job, faces, on_wall, on_panels, X, Y, scale, fills):
    """The Finish view's neighbouring runs: `(under, over)` this wall's own units.

    `faces` is `room.return_faces`, furthest from the viewer first, so painting
    them in order puts a nearer end panel over the carcass side behind it. A
    face is drawn OVER this wall's own cabinets and panels where it stands in
    front of every one of them it overlaps, and under them otherwise — the
    precedence the Line view's outlines already follow.

    Each item's number goes where some of it is actually seen: on the first
    of a few points, over its biggest faces, whose topmost paint is its own. An
    item hidden entirely is named in the wall label and nowhere else, rather
    than written on the panel standing in front of it.
    """
    std = job.std
    own = []                         # (x0, x1, z0, z1, how far out its front stands)
    for c, p, _lay, g in on_wall:
        z0 = carcass_z(c, p, std)
        proud = std.board_t if (c.door_count or c.drawer_list) else 0
        own.append((p.x, p.x + g.width, z0, z0 + g.height,
                    int(getattr(p, "y", 0) or 0) + g.depth + proud))
    for c, p, g in on_panels:
        z0 = carcass_z(c, p, std)
        own.append((p.x, p.x + g.width, z0, z0 + g.height,
                    int(getattr(p, "y", 0) or 0) + g.depth))

    def meets(f, o):
        return (min(f["x1"], o[1]) > max(f["x0"], o[0]) and
                min(f["z1"], o[3]) > max(f["z0"], o[2]))

    under, over = [], []
    for f in faces:
        behind = any(meets(f, o) and o[4] > f["out"] for o in own)
        (under if behind else over).append(f)

    # what ends up on top at any point, in the order it is painted
    painted = ([(f["x0"], f["x1"], f["z0"], f["z1"], f["cabinet"]) for f in under] +
               [(o[0], o[1], o[2], o[3], None) for o in own] +
               [(f["x0"], f["x1"], f["z0"], f["z1"], f["cabinet"]) for f in over])

    def top_at(u, z):
        for x0, x1, z0, z1, who in reversed(painted):
            if x0 <= u <= x1 and z0 <= z <= z1:
                return who
        return None

    labels = []
    reach = 6 / max(scale, 1e-9)     # the number's own half-width, in mm
    grid = [(i + 0.5) / 8 for i in range(8)]
    for n in _dedup([f["cabinet"] for f in faces]):
        best = None                  # (points seen, the one nearest the top middle, face)
        for f in faces:
            if (f["cabinet"] != n or (f["x1"] - f["x0"]) * scale < 14
                    or (f["z1"] - f["z0"]) * scale < 14):
                continue
            seen = []
            for fu in grid:
                for fz in grid:
                    u = f["x0"] + (f["x1"] - f["x0"]) * fu
                    z = f["z0"] + (f["z1"] - f["z0"]) * fz
                    if all(top_at(u + du, z) == n for du in (-reach, 0, reach)):
                        seen.append((abs(fu - 0.5) + abs(fz - 0.85), u, z))
            if seen and (best is None or len(seen) > best[0]):
                best = (len(seen), min(seen), f)
        if best:
            (_d, u, z), colour = best[1], board_look(job, best[2]["board"])["colour"]
            labels.append(f'<text class="efacelabel" x="{X(u):.1f}" y="{Y(z) + 3.5:.1f}" '
                          f'font-size="9.5" text-anchor="middle" fill="{ink_on(colour)}" '
                          f'pointer-events="none">{n}</text>')
    return ([e for f in under for e in _face_svg(job, f, X, Y, scale, fills)],
            [e for f in over for e in _face_svg(job, f, X, Y, scale, fills)] + labels)


# Room -> Plan is also the canvas walls are DRAWN on (room redo Phase 2, ruling
# 10, 3 October 2026): the plan the Room tab asks for carries this much room
# beyond the walls to draw into, and a room with no walls yet is an empty sheet
# of EMPTY_PLAN_MM from the origin. Drawing only; an export's plan has neither.
PLAN_MARGIN_MM = 800
EMPTY_PLAN_MM = (6000, 4000)


def plan_svg(job: Job, show=None, ghost=None, max_width: int = 1100,
             max_height: int = 620, isolate=None, margin: int = 0, _grow=None) -> str:
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
    if not rm.walls and not margin:
        return _note_svg("Add walls to see the plan")

    std = job.std
    show = tuple(LAYERS) if show is None else tuple(show)
    ghost = tuple(ghost or ())

    # the bounds come off the walls' own points (one wall or many) and the footprints
    corners = [(float(w.x0), float(w.y0)) for w in rm.walls] + \
              [(float(w.x1), float(w.y1)) for w in rm.walls]
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

    pts = list(corners) or [(0.0, 0.0), (float(EMPTY_PLAN_MM[0]), float(EMPTY_PLAN_MM[1]))]
    for cab, p, _ in items:
        pts += cabinet_footprint(rm, p, cab)
    for cab, p in pans:
        pts += cabinet_footprint(rm, p, cab, std, job.materials)
    # the labels' own boxes, in mm, from the pass before (see the end): the
    # drawing makes room for them rather than clipping them
    pts += list(_grow or ())
    xs = [q[0] for q in pts]
    ys = [q[1] for q in pts]
    if margin:
        xs += [min(xs) - margin, max(xs) + margin]
        ys += [min(ys) - margin, max(ys) + margin]
    pad = 66          # room for the thickness band and the length label outside the walls
    span_x = max(max(xs) - min(xs), 1)
    span_y = max(max(ys) - min(ys), 1)
    scale = min((max_width - pad * 2) / span_x, (max_height - pad * 2) / span_y)
    W = int(span_x * scale) + pad * 2
    rows = _legend_rows(job, _dedup([c.exterior_board for c, _p, _l in items] +
                                    [c.panel_spec.board for c, _p in pans]),
                        W - pad * 2)
    leg = _legend_height(rows)
    if margin and int(span_y * scale) + pad * 2 + leg > max_height:
        # the Room tab's plan fits its card WITH its legend (ruling 11)
        scale = min(scale, max(max_height - pad * 2 - leg, 40) / span_y)
        W = int(span_x * scale) + pad * 2
        rows = _legend_rows(job, _dedup([c.exterior_board for c, _p, _l in items] +
                                        [c.panel_spec.board for c, _p in pans]),
                            W - pad * 2)
        leg = _legend_height(rows)
    H = int(span_y * scale) + pad * 2 + leg

    def T(q):
        return (pad + (q[0] - min(xs)) * scale, pad + (q[1] - min(ys)) * scale)

    # The page reads world mm off a pointer through these (and works out no
    # geometry with them): mm = (svg - pad) / scale + the origin.
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" class="drw" width="{W}" height="{H}" '
           f'viewBox="0 0 {W} {H}" font-family="system-ui,sans-serif" '
           f'data-mmx="{min(xs):.3f}" data-mmy="{min(ys):.3f}" data-pad="{pad}" data-scale="{scale:.6f}">',
           STROKE_STYLE + '<defs><pattern id="hatch" width="6" height="6" '
           'patternUnits="userSpaceOnUse" patternTransform="rotate(45)">'
           f'<line x1="0" y1="0" x2="0" y2="6" stroke="{MUTED}" stroke-width="1.4"/>'
           '</pattern></defs>',
           f'<rect width="{W}" height="{H}" fill="none"/>']

    out += _plan_room_side(rm, T, std)
    walls_out, lengths = _plan_walls(rm, corners, T, scale, std)
    out += walls_out
    gap_shapes, labels, gap_polys = _plan_gaps(job, show, T)
    labels = lengths + labels      # a wall's length first: it is never dropped
    out += gap_shapes
    # a wall is selected by a click on it: a fat invisible line under the
    # cabinets (a panel's PANEL_GRAB, the same bargain), so a cabinet on the
    # wall line still wins the press
    out += _plan_wall_hits(rm, T)
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
        out += _plan_faces(job, cab, p, lay, T, std, faint=True)
    for cab, p, lay in solid:
        out += _plan_cabinet(rm, cab, p, lay, T, faint=False,
                             bad=cab.number in colliding,
                             colour=board_look(job, cab.exterior_board)["colour"])
        out += _plan_faces(job, cab, p, lay, T, std)
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
        labels += _plan_label(rm, cab, p, T)
    for cab, p in pans:
        if (cab.number == isolate if isolate is not None else "panels" in show):
            labels += _plan_label(rm, cab, p, T, std, job.materials)
    # what a wall's length may sit over, and then wants a backing to read
    # (round 2): cabinets, panels, faces, walls, gap marks — in drawing units
    under = [[T(q) for q in cabinet_footprint(rm, p, cab)] for cab, p, _l in items]
    under += [[T(q) for q in cabinet_footprint(rm, p, cab, std, job.materials)] for cab, p in pans]
    for cab, p, _l in items:
        under += [[T(q) for q in o] for _part, o in front_outlines(job, cab, p, std)]
    under += gap_polys
    for w in rm.walls:
        (ax, ay), (bx, by) = T((w.x0, w.y0)), T((w.x1, w.y1))
        L = math.hypot(bx - ax, by - ay)
        if L > 0:
            ux, uy = (by - ay) / L * 1.5, -(bx - ax) / L * 1.5
            under.append([(ax + ux, ay + uy), (bx + ux, by + uy), (bx - ux, by - uy), (ax - ux, ay - uy)])
    boxes = []
    out += _place_labels(labels, boxes=boxes, under=under)
    out += _plan_plinths(job, show, T)
    out += _plan_obstructions(rm, T)
    out += _plan_tracks(rm, corners, T)
    if margin:
        out += _plan_corner_handles(rm, T, std)
    out += _legend_svg(rows, pad, H - leg + 2)

    # Every label inside the drawing (round 2, 3 October 2026): a box past the
    # edge — a wall's length outside a wall at the edge, moved out further on
    # a leader — is taken into the bounds with PLAN_LABEL_MARGIN round it and
    # the plan drawn again, a few percent smaller. The exported plan too.
    past = [b for b in boxes if b[0] < 0 or b[1] < 0 or b[2] > W or b[3] > H - leg]
    if past and len(_grow or ()) < 200:
        def mm(x, y):
            return ((x - pad) / scale + min(xs), (y - pad) / scale + min(ys))
        m = PLAN_LABEL_MARGIN
        more = []
        for x0, y0, x1, y1 in past:
            (a, b), (c, d) = mm(x0, y0), mm(x1, y1)
            more += [(a - m, b - m), (c + m, d + m)]
        return plan_svg(job, show, ghost, max_width, max_height, isolate, margin,
                        _grow=list(_grow or ()) + more)

    out.append("</svg>")
    return "\n".join(out)


def _plan_room_side(rm, T, std):
    """WHICH SIDE THE ROOM IS, shown (2 October 2026): a closed room's floor is
    tinted; on an open run, and on a free wall, a band `ROOM_BAND_MM` deep on
    the face side of each wall is tinted, fading out into the room. The line
    is the inside face and the room is on its right (`wall_normal`)."""
    out = []
    from .room import closure, main_chain
    ids, _c = main_chain(rm, std)
    closed = closure(rm, std)["closed"]      # the one answer (ruling 2)
    if closed:
        pts = " ".join(f"{x:.1f},{y:.1f}" for x, y in (T(q) for q in corner_points(rm, std)[:-1]))
        out.append(f'<polygon class="roomside" points="{pts}" fill="{ROOM_TINT}" '
                   f'fill-opacity="0.35" stroke="none" pointer-events="none"/>')
    frames = wall_frames(rm)
    for w in rm.walls:
        if closed and w.id in ids:
            continue
        (sx, sy), (dx, dy), (nx, ny) = frames[w.id]
        L = w.length
        if L <= 0:
            continue
        d = ROOM_BAND_MM
        quad = [(w.x0, w.y0), (w.x1, w.y1), (w.x1 + nx * d, w.y1 + ny * d), (w.x0 + nx * d, w.y0 + ny * d)]
        pts = " ".join(f"{x:.1f},{y:.1f}" for x, y in (T(q) for q in quad))
        mx, my = (w.x0 + w.x1) / 2, (w.y0 + w.y1) / 2
        (gx0, gy0), (gx1, gy1) = T((mx, my)), T((mx + nx * d, my + ny * d))
        gid = f"side-{escape(w.id)}"
        out.append(f'<defs><linearGradient id="{gid}" gradientUnits="userSpaceOnUse" '
                   f'x1="{gx0:.1f}" y1="{gy0:.1f}" x2="{gx1:.1f}" y2="{gy1:.1f}">'
                   f'<stop offset="0" stop-color="{ROOM_TINT}" stop-opacity="0.55"/>'
                   f'<stop offset="1" stop-color="{ROOM_TINT}" stop-opacity="0"/>'
                   f'</linearGradient></defs>')
        out.append(f'<polygon class="roomside" data-wall="{escape(w.id)}" points="{pts}" '
                   f'fill="url(#{gid})" stroke="none" pointer-events="none"/>')
    return out


def _plan_corner_handles(rm, T, std):
    """A small round handle on every corner and free end, shown on hover, to
    drag it by (room redo Phase 2, ruling 3). The Room tab's plan only; it
    carries the corner in world mm (`data-cx`, `data-cy`)."""
    from .room import _corners
    out = []
    for x, y in _corners(rm, std):
        sx, sy = T((x, y))
        out.append(f'<circle class="cornerhandle" data-cx="{x}" data-cy="{y}" cx="{sx:.1f}" '
                   f'cy="{sy:.1f}" r="6"/>')            # coloured by the page's stylesheet
    return out


def _plan_wall_hits(rm, T):
    """One fat, invisible line per wall for a click to select it by
    (`data-wallhit`); the selected one is coloured by the page's stylesheet."""
    out = []
    for w in rm.walls:
        (ax, ay), (bx, by) = T((w.x0, w.y0)), T((w.x1, w.y1))
        out.append(f'<line class="wallhit" data-wallhit="{escape(w.id)}" '
                   f'x1="{ax:.1f}" y1="{ay:.1f}" x2="{bx:.1f}" y2="{by:.1f}" '
                   f'stroke="transparent" stroke-width="{PANEL_GRAB}" stroke-linecap="round" '
                   f'style="pointer-events:stroke;cursor:pointer"/>')
    return out


def _plan_walls(rm, corners, T, scale, std: Standard = STANDARD):
    """Wall lines, their lengths, openings as breaks, obstructions as boxes;
    and the wall's thickness as a hatched band on its BACK (`Wall.thickness`,
    drawing only, `Standard.wall_thickness` where none is set). Returns
    `(shapes, length labels)`: the lengths go through `_place_labels`."""
    out, lengths = [], []
    frames = wall_frames(rm)
    for w in rm.walls:
        (ax, ay), (bx, by) = T((w.x0, w.y0)), T((w.x1, w.y1))
        (_s, _d, (nx, ny)) = frames[w.id]
        t = w.thickness if w.thickness else std.wall_thickness
        if w.length > 0 and t > 0:
            back = [(w.x0, w.y0), (w.x1, w.y1), (w.x1 - nx * t, w.y1 - ny * t), (w.x0 - nx * t, w.y0 - ny * t)]
            pts = " ".join(f"{x:.1f},{y:.1f}" for x, y in (T(q) for q in back))
            out.append(f'<polygon class="wallband" points="{pts}" fill="url(#hatch)" '
                       f'fill-opacity="0.45" stroke="none" pointer-events="none"/>')
        spans = _wall_spans(w)
        for s0, s1 in spans:
            p0 = T(to_world(rm, w.id, s0, 0)[:2])
            p1 = T(to_world(rm, w.id, s1, 0)[:2])
            out.append(f'<line x1="{p0[0]:.1f}" y1="{p0[1]:.1f}" '
                       f'x2="{p1[0]:.1f}" y2="{p1[1]:.1f}" '
                       f'stroke="{INK}" stroke-width="{WEIGHT["wall"]}" stroke-linecap="square"/>')
        for op in w.openings:
            q0 = T(to_world(rm, w.id, op.x, 0)[:2])
            q1 = T(to_world(rm, w.id, op.x + op.width, 0)[:2])
            out.append(f'<line x1="{q0[0]:.1f}" y1="{q0[1]:.1f}" '
                       f'x2="{q1[0]:.1f}" y2="{q1[1]:.1f}" '
                       f'stroke="{RULE}" stroke-width="{WEIGHT["internal"]}" stroke-dasharray="3 3"/>')
            mid = ((q0[0] + q1[0]) / 2, (q0[1] + q1[1]) / 2)
            out.append(f'<text x="{mid[0]:.1f}" y="{mid[1] - 6:.1f}" font-size="8.5" '
                       f'text-anchor="middle" fill="{MUTED}">{escape(op.kind)} {op.width}</text>')
        # length label, pushed outside the room along the outward normal, clear
        # of the thickness band; placed with every other label by
        # `_place_labels`, and where it would sit on another, moved further out
        # along the same normal on a short leader — never dropped (touch-ups,
        # 3 October 2026). Its box is the one the page draws over it: the
        # figure in a text box and "mm" beside it (`planLengths`).
        # Round 2 (3 October 2026): always OUTSIDE — on the back, beyond the
        # thickness band — and turned to read along the wall, a wall up the
        # page included (reading upwards). `off` is to the label's middle.
        off = t * scale + 4 + 10
        mx, my = (ax + bx) / 2, (ay + by) / 2
        rot = math.degrees(math.atan2(by - ay, bx - ax))
        if rot >= 90:
            rot -= 180
        elif rot < -90:
            rot += 180
        text = f"{w.id} · {w.length}"
        lb = _label(mx - nx * off, my - ny * off + 4, text, 10.5, INK, prio=0)
        lb["w"] = len(f"{text} mm") * 10.5 * 0.58 + 12
        lb["top"], lb["bottom"] = 14, 6      # the field the page lays over it
        lb["rot"] = round(rot, 1)
        lb["steps"] = [(-nx * LENGTH_STEP * k, -ny * LENGTH_STEP * k) for k in range(1, LENGTH_STEPS + 1)]
        lb["attrs"] = f' class="walllen" data-wall="{escape(w.id)}"'
        lengths.append(lb)
    return out, lengths


def _plan_gaps(job, show, T):
    """Fillers hatched, undecided gaps dimensioned in red: `(shapes, labels)`.

    The labels go on over everything, through `_place_labels`, with the rest.

    Red is for the ones still needing a ruling, not for the small ones: the app
    proposes and the user decides, so an undecided gap is the thing that wants
    attention regardless of its size.
    """
    out, labels, polys = [], [], []
    shown = {run_key(lay) for lay in show}
    for g in gaps(job, job.std):
        if g.layer not in shown:
            continue
        pts = [T(q) for q in gap_outline(job.room, g)]
        poly = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
        cx = sum(x for x, _ in pts) / 4
        cy = sum(y for _, y in pts) / 4
        if g.treatment != "open":
            polys.append(pts)
        if g.treatment == "filler":
            out.append(f'<polygon class="gap" points="{poly}" fill="url(#hatch)" '
                       f'stroke="{INK}" stroke-width="{WEIGHT["panel"]}"/>')
        elif g.treatment == "blind":
            out.append(f'<polygon class="gap" points="{poly}" fill="{FAINT}" '
                       f'stroke="{RULE}" stroke-width="{WEIGHT["panel"]}"/>')
            labels.append(_label(cx, cy + 3, "blind", 7.5, MUTED, prio=4, leader=True))
        elif g.treatment == "open":
            continue                       # deliberately nothing there
        else:
            out.append(f'<polygon class="gap" points="{poly}" fill="none" stroke="{CRIT}" '
                       f'stroke-width="1.2" stroke-dasharray="4 3"/>')
            labels.append(_label(cx, cy + 3, str(g.width), 8.5, CRIT, prio=4, leader=True))
    return out, labels, polys


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
                       f'stroke="{RULE}" stroke-width="{WEIGHT["panel"]}" stroke-linecap="butt"/>')
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
                         f'stroke="{stroke}" stroke-width="{WEIGHT["internal"]}"/>')
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
    for w in rm.walls:
        (ax, ay), (bx, by) = T((w.x0, w.y0)), T((w.x1, w.y1))
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
            (_s, (dx, dy), _n) = wall_frames(rm)[w.id]
            if abs(dx) < 1e-9 or abs(dy) < 1e-9:
                x0, y0 = min(c0[0], c1[0]), min(c0[1], c1[1])
                out.append(f'<rect x="{x0:.1f}" y="{y0:.1f}" '
                           f'width="{abs(c1[0] - c0[0]):.1f}" height="{abs(c1[1] - c0[1]):.1f}" '
                           f'fill="#f6e0e3" stroke="{CRIT}" stroke-width="1"/>')
            else:
                # a wall at an angle (29 September 2026): the box turned with
                # it, not the rectangle its two corners would span square
                q = [T(to_world(rm, w.id, ob.x + sx * (ob.width // 2), dep)[:2])
                     for sx, dep in ((-1, 0), (1, 0), (1, depth), (-1, depth))]
                pts = " ".join(f"{a:.1f},{b:.1f}" for a, b in q)
                out.append(f'<polygon points="{pts}" '
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
    read for where things are before it is read for what they are made of. A
    wall unit is ABOVE the plan's cut, so it is drawn lighter and dashed — the
    kitchen-drawing convention, and the one dash in the plan that says something
    a solid line cannot (`WEIGHT`, `ABOVE_DASH`). Everything else is the carcass
    weight, and a clash red and heavy.
    """
    fp = [T(q) for q in cabinet_footprint(rm, p, cab)]
    pts = " ".join(f"{x:.1f},{y:.1f}" for x, y in fp)
    _stroke, width, _dash = _layer_outline(layer, bad)
    dash = ""
    if layer == "wall":
        dash = ABOVE_DASH
        width = width if bad else WEIGHT["above"]
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


def _plan_faces(job, cab, p, layer, T, std, faint=False):
    """A cabinet's door leaves, drawer faces and blind panel, seen from above.

    Each is a thin strip at its board's real thickness where it really is —
    along a mitre's angled face, and on a blind corner the door and the flush
    panel beside it — in its own board's colour, leaf by leaf and drawer by
    drawer as the cut list cuts them (`room.front_outlines`). Lowest first, so
    the one you would see from above is drawn last.

    Drawing only: they take no pointer events, so a press still lands on the
    cabinet, and the door swings on hover are untouched. A wall unit's faces
    follow its layer — the lighter dashed line — and ghost with it.
    """
    op = ' opacity="0.30"' if faint else ""
    width, dash = ((WEIGHT["above"], ABOVE_DASH) if layer == "wall"
                   else (WEIGHT["face"], ""))
    out = []
    for part, outline in front_outlines(job, cab, p, std):
        pts = " ".join(f"{x:.1f},{y:.1f}" for x, y in (T(q) for q in outline))
        out.append(f'<polygon class="face" data-cab="{cab.number}" '
                   f'data-role="{part.role}" points="{pts}" '
                   f'fill="{board_look(job, part.board)["colour"]}" stroke="{INK}" '
                   f'stroke-width="{width}"{dash}{op} pointer-events="none"/>')
    return out


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
    return [f'<polygon class="pan" data-panel="{cab.number}"{_host_attr(cab)} points="{pts}" '
            f'fill="{"#f6e0e3" if bad else colour}" fill-opacity="0.9" '
            f'stroke="{CRIT if bad else INK}" pointer-events="none" '
            f'stroke-width="{WEIGHT["clash"] if bad else WEIGHT["panel"]}"{op}/>']


def _host_attr(cab) -> str:
    """`data-host="N"` on an attached panel's drawn shapes, so a drag of cabinet
    N carries them with it on screen; nothing on a standalone panel, so every
    drawing of one is byte for byte what it was."""
    return f' data-host="{cab.attached_to}"' if cab.is_attached else ""


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
             f'data-panel="{cab.number}" data-layer="panels"{_host_attr(cab)} '
             f'points="{" ".join(f"{x:.1f},{y:.1f}" for x, y in pts)}" '
             f'fill="none" stroke="none" pointer-events="all"/>'], thin)


def _plan_label(rm, cab, p, T, std: Standard = STANDARD, materials: dict = None):
    """Number and size at the middle of the outline, whatever shape it is — as
    label specs for `_place_labels`, which keeps them off each other."""
    fp = [T(q) for q in cabinet_footprint(rm, p, cab, std, materials)]
    cx = sum(x for x, _ in fp) / len(fp)
    cy = sum(y for _, y in fp) / len(fp)
    side = min(max(x for x, _ in fp) - min(x for x, _ in fp),
               max(y for _, y in fp) - min(y for _, y in fp))
    if cab.is_panel:
        # A panel is a few pixels across the thin way, so the number goes beside
        # it rather than in it — inside, `side <= 24` would drop every one.
        cx = max(x for x, _ in fp) + 4
        return [_label(cx, cy + 3, str(cab.number), 9, INK, anchor="start",
                       prio=2, leader=True)]
    if side <= 24:
        return []
    g = geometry(cab, std, materials)
    number = _label(cx, cy - 1, str(cab.number), 10, INK, prio=1, leader=True)
    out = [number]
    if side > 40:
        # the size is the first thing to go when there is no room for it
        out.append(_label(cx, cy + 10, f"{g.width}x{g.depth}", 8, MUTED, prio=3,
                          drop=True, beside=number))
    return out


# How far a label may be moved off its spot, on a short leader, before it is
# given up on: pixels, and nothing reads it but `_place_labels`.
LEADER_STEPS = ((0, -13), (0, 13), (16, 0), (-16, 0), (14, -13), (-14, -13),
                (14, 13), (-14, 13), (0, -24), (0, 24), (26, 0), (-26, 0))
# A wall's length label moves only out along its wall's outward normal, this
# far a step, up to this many steps: pixels, read by `_plan_walls` alone.
LENGTH_STEP = 8
LENGTH_STEPS = 16
# Room the plan keeps round every label's box, mm (round 2, 3 October 2026):
# the bounds take the labels in, so none is past the drawing's edge.
PLAN_LABEL_MARGIN = 150
# A wall's length over something is drawn on this (round 2): white, a little
# see-through, no border, 2 px round the field.
LABEL_BACKING_OPACITY = 0.85


def _label(x, y, text, size, fill, anchor="middle", prio=1, drop=False,
           leader=False, beside=None) -> dict:
    """One plan label, to be placed by `_place_labels`. `drop` may be left out
    when there is no room; `leader` may be moved off its spot on a short line;
    `beside` is a label it only makes sense next to, left where it was."""
    return {"x": x, "y": y, "text": text, "size": size, "fill": fill,
            "anchor": anchor, "prio": prio, "drop": drop, "leader": leader,
            "beside": beside, "at": None}


def _label_box(lb, dx=0.0, dy=0.0):
    w = lb.get("w") or len(lb["text"]) * lb["size"] * 0.58
    x0 = lb["x"] + dx - (w / 2 if lb["anchor"] == "middle" else 0)
    if lb.get("rot") is not None:   # turned along its wall
        cx, cy = lb["x"] + dx, lb["y"] + dy - (lb["top"] - lb["bottom"]) / 2
        a = math.radians(lb["rot"])
        hw, hh = w / 2 + 1, (lb["top"] + lb["bottom"]) / 2
        ex = abs(math.cos(a)) * hw + abs(math.sin(a)) * hh
        ey = abs(math.sin(a)) * hw + abs(math.cos(a)) * hh
        return (cx - ex, cy - ey, cx + ex, cy + ey)
    if "top" in lb:          # a box of its own: a wall length's field, 20 high
        return (x0 - 1, lb["y"] + dy - lb["top"], x0 + w + 1, lb["y"] + dy + lb["bottom"])
    y1 = lb["y"] + dy + lb["size"] * 0.2
    return (x0 - 1, y1 - lb["size"] * 0.95, x0 + w + 1, y1)


def _turned_field(lb, dx, dy, grow=0.0):
    """A turned wall-length label's field as its four corners, drawing units."""
    cx, cy = lb["x"] + dx, lb["y"] + dy - (lb["top"] - lb["bottom"]) / 2
    a = math.radians(lb["rot"])
    c, s = math.cos(a), math.sin(a)
    hw, hh = lb["w"] / 2 + grow, (lb["top"] + lb["bottom"]) / 2 + grow
    return [(cx + c * u - s * v, cy + s * u + c * v)
            for u, v in ((-hw, -hh), (hw, -hh), (hw, hh), (-hw, hh))]


def _place_labels(labels, boxes=None, under=()) -> list:
    """Plan labels, placed so none sits on another (23 September 2026).

    Most important first: cabinet numbers, then panel numbers, then sizes, then
    gap widths. Each goes where it was asked for if that is clear; if not, a
    label that may move is tried a short step off in each direction and drawn
    there with a leader back to its spot, and a size is simply left out — the
    number is what matters. A label that fits nowhere is drawn where it was
    asked for: a number on top of another beats a number missing.

    A wall's length (round 2, 3 October 2026) is turned along its wall, and
    where its field lies over anything in `under` — a cabinet, a panel, a
    face, a wall, a gap mark — it is drawn on a quiet white backing so it
    reads; over nothing it has none. `boxes`, when given, collects every
    placed label's box, for the drawing to make room for.
    """
    placed, out = [], []

    def clear(box):
        return all(box[2] <= b[0] or box[0] >= b[2] or box[3] <= b[1] or box[1] >= b[3]
                   for b in placed)

    for lb in sorted(labels, key=lambda lb: lb["prio"]):
        if lb["beside"] is not None and lb["beside"]["at"] != (0, 0):
            continue                     # its number was moved: the size goes
        steps = [(0, 0)] + (lb["steps"] if lb.get("steps")
                            else list(LEADER_STEPS) if lb["leader"] else [])
        at = next((d for d in steps if clear(_label_box(lb, *d))), None)
        if at is None:
            if lb["drop"]:
                continue
            at = (0, 0)
        lb["at"] = at
        box = _label_box(lb, *at)
        placed.append(box)
        if boxes is not None:
            boxes.append(box)
        dx, dy = at
        if at != (0, 0):
            # from the label's own spot to the nearest edge of where it went
            ox, oy = lb["x"], lb["y"] - lb["size"] * 0.35
            ex = min(max(ox, box[0]), box[2])
            ey = min(max(oy, box[1]), box[3])
            out.append(f'<line class="leader" x1="{ox:.1f}" y1="{oy:.1f}" '
                       f'x2="{ex:.1f}" y2="{ey:.1f}" stroke="{MUTED}" '
                       f'stroke-width="{WEIGHT["dim"]}" pointer-events="none"/>')
        anchor = "" if lb["anchor"] == "start" else f' text-anchor="{lb["anchor"]}"'
        turn = ""
        if lb.get("rot") is not None:
            cx, cy = lb["x"] + dx, lb["y"] + dy - (lb["top"] - lb["bottom"]) / 2
            turn = (f' data-cx="{cx:.1f}" data-cy="{cy:.1f}" data-rot="{lb["rot"]}"'
                    + (f' transform="rotate({lb["rot"]} {cx:.1f} {cy:.1f})"' if lb["rot"] else ""))
            field = _turned_field(lb, dx, dy)
            if any(polygons_overlap(field, u) for u in under if len(u) >= 3):
                h = lb["top"] + lb["bottom"] - 4
                out.append(f'<rect class="lenback" data-wall="{escape(lb["text"].split(" ")[0])}" '
                           f'x="{cx - lb["w"] / 2 - 2:.1f}" y="{cy - h / 2 - 2:.1f}" '
                           f'width="{lb["w"] + 4:.1f}" height="{h + 4:.1f}" rx="4" fill="#ffffff" '
                           f'fill-opacity="{LABEL_BACKING_OPACITY}" stroke="none" pointer-events="none"'
                           + (f' transform="rotate({lb["rot"]} {cx:.1f} {cy:.1f})"' if lb["rot"] else "")
                           + '/>')
        out.append(f'<text{lb.get("attrs", "")}{turn} x="{lb["x"] + dx:.1f}" y="{lb["y"] + dy:.1f}" '
                   f'font-size="{lb["size"]}"{anchor} fill="{lb["fill"]}">'
                   f'{escape(lb["text"])}</text>')
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
                   f'stroke-width="{WEIGHT["internal"]}"/>')
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
    # the face stack: an inner drawer is behind the door and not on the front
    stack = c.outer_drawers
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
                   f'stroke-width="{WEIGHT["face"]}"/>')
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
                       f'fill="{fills.of(look, True)}" stroke="{RULE}" stroke-width="{WEIGHT["face"]}"/>')
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
    n = len(c.shelf_list)
    if n and not stack:
        span = y + h - cursor if leaves else h
        base = cursor if leaves else y
        for i in range(1, n + 1):
            sy = base + span * i / (n + 1)
            out.append(f'<line x1="{x + 4:.1f}" y1="{sy:.1f}" x2="{x + w - 4:.1f}" '
                       f'y2="{sy:.1f}" stroke="{inside}" stroke-width="{WEIGHT["internal"]}" '
                       f'stroke-opacity="0.55"/>')
    if c.divider_count:
        out.append(f'<line x1="{x + w / 2:.1f}" y1="{y + 4:.1f}" x2="{x + w / 2:.1f}" '
                   f'y2="{y + h - 4:.1f}" stroke="{inside}" stroke-width="{WEIGHT["internal"]}" '
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
                   f'fill="{fills.of(look, True)}" stroke="{RULE}" stroke-width="{WEIGHT["face"]}"/>')
        if door_edge:
            out.extend(_edge_band(x0, top, lw, dh, door_edge))
        ink = muted_on(look["colour"])
        if angled:
            out.extend(_oblique_hatch(x0, top, lw, dh, ink))
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
                   f'stroke="{RULE}" stroke-width="{WEIGHT["internal"]}"/>')
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
                       f'stroke-width="{WEIGHT["face"]}"/>')
            # The flush panel, in ITS OWN board, across its full B. The door is
            # drawn over it afterwards, so what is left showing is exactly the
            # strip the door does not cover — which is what you see in the room.
            look = board_look(mats, c.blind_panel_board)
            out.append(f'<rect class="eblind" x="{px(b0):.1f}" y="{top:.1f}" '
                       f'width="{(b1 - b0) * scale:.1f}" height="{dh:.1f}" '
                       f'fill="{fills.of(look, True)}" stroke="{INK}" stroke-width="{WEIGHT["face"]}"/>')
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


# --- a drawing per cupboard (ruling 7 of the cabinet round, 3 October 2026) ---

def cabinet_section_dims(job: Job, number: int) -> dict:
    """The numbers behind one cupboard's drawing, kept apart from the SVG so
    they can be checked (the `wall_elevation_dims` discipline). Every chain is
    a list of breakpoints from a datum, so its segments add up to the whole:

    * `height_chain` — up the side, from the carcass underside: the bottom
      panel's top face, each shelf's top face, each Back support's two edges,
      the top's underside where there is a top, and H;
    * `depth_chain` — from the wall face (the sides' back edges) to the
      carcass front: the back (the backing in its slot, or the solid back),
      each flat support's two edges, each shelf's front edge, and D;
    * `width_chain` — across the front: the two sides and W.

    `shelves` says where each shelf is drawn and how deep it is (height from
    the top face of the bottom panel to the top face of the shelf, exactly as
    the Shelves section measures it), `supports` where each rail is, `back`
    what is at the back, and `legs` the leg height — a note, since where each
    leg stands is not in Standard and none is drawn. Geometry comes off the
    panel set (`room.geometry`) and the same `room` placements the 3D draws,
    never the declared figures (hard rule 1).
    """
    from .room import back_part, interior_parts, shelf_layout, support_layout, solid_parts
    std, mats = job.std, job.materials
    cab = next((c for c in job.cabinets if c.number == number), None)
    if cab is None or cab.is_panel:
        return {}
    g = geometry(cab, std, mats)
    W, H, D, t = g.width, g.height, g.depth, std.board_t
    parts = solid_parts(cab, std, mats)
    has_top = any(q.role == "top" for q in parts)
    footprint_only = any(q.role == "carcass" for q in parts) or not parts
    heights, depths = {0, H}, {0, D}
    if not footprint_only:
        heights.add(t)
        if has_top:
            heights.add(H - t)
    shelves = []
    for sh in shelf_layout(cab, std, mats):
        front = D - sh["clearance"]
        shelves.append({"height": sh["height"], "z0": sh["z0"], "z1": sh["z1"],
                        "depth": sh["depth"], "clearance": sh["clearance"],
                        "y0": front - sh["depth"], "y1": front, "typed": sh["typed"],
                        "fixed": sh["fixed"]})
        heights.add(sh["z1"])
        depths.add(front)
    supports = []
    for u in support_layout(cab, std, mats):
        # the spec frame's y runs from the front; the drawing's from the wall
        entry = {"type": u["type"], "n": u["n"], "y0": D - u["y1"], "y1": D - u["y0"],
                 "z0": u["z0"], "z1": u["z1"], "upright": u["upright"]}
        supports.append(entry)
        if u["upright"]:
            heights.update((u["z0"], u["z1"]))
        else:
            depths.update((entry["y0"], entry["y1"]))
    bp = back_part(cab, std, mats)
    back = None
    if bp is not None:
        ys = [y for _, y in bp.outline]
        back = {"kind": "solid" if bp.role == "solid_back" else "backing", "board": bp.board,
                "y0": min(ys), "y1": max(ys), "z0": bp.z0, "z1": bp.z1,
                "cavity": std.back_cavity if bp.role == "back" else 0}
        depths.update((back["y0"], back["y1"]))

    def chain(points, end):
        return sorted({0, end} | {round(min(max(v, 0), end), 1) for v in points})

    return {
        "number": number, "width": W, "height": H, "depth": D, "has_top": has_top,
        "footprint_only": footprint_only, "source": g.source,
        "height_chain": chain(heights, H),
        "depth_chain": chain(depths, D),
        "width_chain": chain({0, t, W - t, W} if not footprint_only else {0, W}, W),
        "shelves": shelves, "supports": supports, "back": back,
        "legs": std.leg_height if (not cab.is_panel and cab.kind != "upper") else 0,
        "note": ("construction not ruled — an ell is drawn as its footprint" if cab.corner_kind == "ell"
                 else "hand-built — its parts are not modelled; the front and the outline only"
                 if cab.template == "none" else ""),
    }


def cabinet_svg(job: Job, number: int, max_width: int = 1100,
                pictures: str = PIC.ROUTE) -> str:
    """One cupboard on one sheet: its front elevation beside a side section,
    dimensioned (ruling 7 of the cabinet round, 3 October 2026).

    The FRONT is what the wall elevation draws for this cabinet — doors, drawer
    faces, hinges, board colours and pictures, the edging bands — through the
    same `_interior` (a corner unit through `_corner_interior`), so the two
    drawings cannot disagree. The SECTION is through the middle of the width,
    looking at the inside of the LEFT side: the front is on the right, the
    wall on the left. Every solid is where the 3D draws it (`room.solid_parts`,
    `back_part`, `interior_parts`): the side's profile, the top and bottom,
    the back — the backing in its slot with the 16 mm cavity behind it
    hatched, or the solid back — the supports, the shelves at their heights
    and depths with their face clearance, the drawer boxes and their runners,
    the fronts standing proud. Dimensioned off `cabinet_section_dims`:
    overall W, H and D, the shelves' heights from the bottom panel and their
    depths, the supports' positions. Legs are not drawn (where each stands is
    not ruled); the leg height is a note. A mitre and a blind corner draw
    their own construction (their parts, projected); an ell and a hand-built
    cabinet say so.
    """
    from .room import back_part, interior_parts, solid_parts
    std, mats = job.std, job.materials
    cab = next((c for c in job.cabinets if c.number == number), None)
    if cab is None:
        return _note_svg(f"no cabinet {number}")
    if cab.is_panel:
        return _note_svg("a Panel has no cupboard drawing — see Panel design", 360)
    d = cabinet_section_dims(job, number)
    W, H, D = d["width"], d["height"], d["depth"]
    fw = run_widths(job, [cab])[cab.number]           # a corner unit's width along its wall
    t = std.board_t
    pad, gutter, gap, under = 48, 34, 60, 70
    gw = fw + gap + D
    scale = min((max_width - pad * 2 - gutter * 2) / max(gw, 1), 520 / max(H, 1))
    fx = pad + gutter                                   # the front's left edge
    sx = fx + fw * scale + gap * scale                  # the section's left edge (the wall)
    floor = pad + H * scale
    nsh = len(d["shelves"])
    stagger = 12                                        # one running dimension per shelf
    right = sx + D * scale + 14 + stagger * nsh + 30    # the overall H dim stands past them
    Wpx = int(right + pad)
    rows = _legend_rows(job, _boards_drawn(job, [cab]), Wpx - pad * 2)
    leg = _legend_height(rows)
    Hpx = int(floor + under + leg + 24)
    fills = Fills(base=pictures)
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" class="drw cabdrw" width="{Wpx}" height="{Hpx}" '
           f'viewBox="0 0 {Wpx} {Hpx}" font-family="system-ui,sans-serif" data-cab="{number}">',
           "",
           f'<rect width="{Wpx}" height="{Hpx}" fill="{PAPER}"/>']
    defs_at = 1

    def X(y_mm):                     # section: depth from the wall → right
        return sx + y_mm * scale

    def Y(z_mm):                     # both views: up from the carcass underside
        return floor - z_mm * scale

    def rect(x0, x1, z0, z1, fill, stroke=INK, sw=WEIGHT["internal"], cls="", extra=""):
        return (f'<rect class="{cls}" x="{min(x0, x1):.1f}" y="{Y(max(z0, z1)):.1f}" '
                f'width="{abs(x1 - x0):.1f}" height="{abs(z1 - z0) * scale:.1f}" '
                f'fill="{fill}" stroke="{stroke}" stroke-width="{sw}"{extra}/>')

    # ---- the front elevation ---------------------------------------------
    look = board_look(job, cab.carcass_board)
    out.append(f'<g class="cabfront" data-cab="{number}">')
    out.append(f'<text x="{pad:.1f}" y="{pad - 30:.1f}" font-size="10" fill="{INK}">'
               f'Cabinet {number} · {escape(_size_label(job, cab))} · '
               f'{escape(cab.kind)}{" · " + escape(cab.corner_kind) if cab.corner_on else ""}</text>')
    out.append(f'<text x="{pad:.1f}" y="{pad - 16:.1f}" font-size="8.5" fill="{MUTED}">'
               f'FRONT on the left · SECTION on the right: mid-width, looking at the inside of the '
               f'left side (wall left, front right)</text>')
    out.append(f'<rect class="ecab" x="{fx:.1f}" y="{Y(H):.1f}" width="{fw * scale:.1f}" '
               f'height="{H * scale:.1f}" fill="{fills.of(look, True)}" stroke="{INK}" '
               f'stroke-width="{WEIGHT["carcass"]}"/>')
    out += _interior(cab, fx, Y(H), fw * scale, H * scale, scale, std, flip=False,
                     materials=mats, fills=fills)
    out.append("</g>")
    # width: the two sides and the overall
    wc = d["width_chain"]
    for a, b in zip(wc, wc[1:]):
        out += _dim_h(fx + a * scale, fx + b * scale, floor + 14, int(round(b - a)))
    out += _dim_h(fx, fx + fw * scale, floor + 30, int(round(fw)))
    # height: the chain on the left of the front, the overall outside it
    hc = d["height_chain"]
    for a, b in zip(hc, hc[1:]):
        out += _dim_v(Y(b), Y(a), fx - 10, int(round(b - a)))
    out += _dim_v(Y(H), Y(0), fx - 26, H)

    # ---- the side section -------------------------------------------------
    out.append(f'<g class="cabsection" data-cab="{number}">')
    parts = solid_parts(cab, std, mats)
    if d["footprint_only"]:
        out.append(rect(X(0), X(D), 0, H, fills.of(look, True), INK, WEIGHT["carcass"], "side"))
        out.append(f'<text x="{X(D / 2):.1f}" y="{Y(H / 2):.1f}" font-size="9" text-anchor="middle" '
                   f'fill="{MUTED}">{escape(d["note"])}</text>')
    else:
        # the left side's inside face, as the background
        out.append(rect(X(0), X(D), 0, H, fills.of(look, True), INK, WEIGHT["carcass"], "side"))
        if not fills.textured(look):
            out += _grain_lines(X(0), Y(H), D * scale, H * scale, True, look["ink"])

        def proj(q):
            ys = [y for _, y in q.outline]
            return min(ys), max(ys)

        # the cavity behind a backing board: hatched, so the 16 mm reads
        back = d["back"]
        if back and back["cavity"]:
            out.append(rect(X(0), X(back["y0"]), t, H - t if d["has_top"] else H, "none", FAINT,
                            WEIGHT["internal"], "cavity"))
            out += _oblique_hatch(X(0), Y(H - t if d["has_top"] else H), back["y0"] * scale,
                                  ((H - t if d["has_top"] else H) - t) * scale, FAINT)
        for q in parts:
            if q.role in ("side", "carcass"):
                continue
            y0, y1 = proj(q)
            fill = fills.of(board_look(job, q.board), q.role in ("door", "drawer", "blind"))
            cls = {"top": "top", "bottom": "bottom", "door": "front", "drawer": "front",
                   "blind": "front"}.get(q.role, q.role)
            out.append(rect(X(y0), X(y1), q.z0, q.z1, fill, INK, WEIGHT["internal"], cls))
        bp = back_part(cab, std, mats)
        if bp is not None:
            y0, y1 = proj(bp)
            out.append(rect(X(y0), X(y1), bp.z0, bp.z1, fills.of(board_look(job, bp.board), True),
                            INK, WEIGHT["internal"], "back"))
        for q, _tapes in interior_parts(cab, std, mats):
            y0, y1 = proj(q)
            if q.role in ("runner_outer", "runner_inner"):
                out.append(rect(X(y0), X(y1), q.z0, q.z1, FAINT, MUTED, WEIGHT["internal"], q.role))
                continue
            if q.role == "drawer" and q.label == "inner":
                continue                       # an inner face sits inside its box's profile
            fill = fills.of(board_look(job, q.board), False)
            out.append(rect(X(y0), X(y1), q.z0, q.z1, fill, INK, WEIGHT["internal"], q.role))
            if q.role == "support" and q.label:
                out.append(f'<text x="{X((y0 + y1) / 2):.1f}" y="{Y(q.z1) - 2:.1f}" font-size="7" '
                           f'text-anchor="middle" fill="{MUTED}">{escape(q.label)}</text>')
        for sh in d["shelves"]:
            # the shelf's depth on the shelf, and its face clearance at the front
            out.append(f'<text class="shelfdepth" x="{X((sh["y0"] + sh["y1"]) / 2):.1f}" '
                       f'y="{Y(sh["z1"]) - 2:.1f}" font-size="7.5" text-anchor="middle" '
                       f'fill="{INK}">{sh["depth"]}</text>')
            if sh["clearance"]:
                out.append(f'<text class="shelfclear" x="{X(D) + 2:.1f}" y="{Y(sh["z0"]) + 2:.1f}" '
                           f'font-size="6.5" fill="{MUTED}">{sh["clearance"]}</text>')
    out.append("</g>")
    # depth: the chain under the section, the overall under it
    dc = d["depth_chain"]
    for a, b in zip(dc, dc[1:]):
        out += _dim_h(X(a), X(b), floor + 14, int(round(b - a)))
    out += _dim_h(X(0), X(D), floor + 30, D)
    # the shelves' heights, from the top face of the bottom panel to each top
    # face, on the right of the section — read the way the Shelves section
    # measures them
    for i, sh in enumerate(d["shelves"]):
        out += _dim_v(Y(sh["z1"]), Y(t), X(D) + 14 + stagger * i, int(round(sh["height"])))
    out += _dim_v(Y(H), Y(0), right, H)

    # ---- notes, tapes, legend ---------------------------------------------
    note = (f"legs {d['legs']} mm, not drawn — the carcass stands on them" if d["legs"]
            else "hung: no legs")
    if d["note"]:
        note += " · " + d["note"]
    if d["back"]:
        note += (" · solid back" if d["back"]["kind"] == "solid"
                 else f" · backing board in its slot, {d['back']['cavity']} mm cavity behind it")
    elif not d["footprint_only"]:
        note += " · no back"
    out.append(f'<text x="{pad:.1f}" y="{floor + 50:.1f}" font-size="8.5" fill="{MUTED}">'
               f'{escape(note)}</text>')
    out += _tape_note(job, pad, Hpx - 8 - leg, Wpx - pad * 2)
    out += _legend_svg(rows, pad, Hpx - leg + 2, fills)
    out[defs_at] = f"{STROKE_STYLE}<defs>{fills.defs()}</defs>"
    out.append("</svg>")
    return "\n".join(out)
