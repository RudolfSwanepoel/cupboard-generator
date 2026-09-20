"""Front elevation of a job, as SVG.

Cabinets are drawn side by side to scale, with doors, drawer faces and shelf
lines shown. It is a sanity check, not a working drawing: if a cabinet looks
wrong here it is wrong in the cut list too.
"""
from html import escape
from typing import List

from .model import (NO_COLOUR, Cabinet, Job, grain_of, hinge_side,
                    material_board, material_colour, material_record)
from .room import (LAYERS, cabinet_footprint, carcass_z, clashes, corner_points,
                   gap_outline, gaps, geometry, layer_of, overlaps, placed,
                   plinth_choice_for, plinth_lengths, pullout_envelope,
                   return_profiles, run_key, runs, swing_envelopes, to_world,
                   wall_frames)
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


def board_look(job, board_id: str) -> dict:
    """What one board looks like on a drawing: `colour`, `grain`, `picture`.

    The one resolver. Every fill in the run, the wall elevations and the plan
    comes through here, and no drawing states a colour of its own, so what you
    see is what the cut list cuts. `job` is a Job or — for `_interior`, which is
    handed the materials and nothing else — the job's `materials` dict straight.

    A board nobody has coloured comes back NO_COLOUR with `set` False. That is
    what the legend says "no colour set" from; it is never a warning.

    `picture` is carried because the record has one. Nothing draws it yet.
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


def _legend_svg(rows, x, y) -> list:
    """One swatch per board: its colour, a grain mark when the board is grained,
    and `id - name`."""
    out = []
    for r, entries in enumerate(rows):
        at_y = y + r * LEGEND_ROW
        at_x = x
        for look, text, width in entries:
            out.append(f'<rect class="swatch" x="{at_x:.1f}" y="{at_y:.1f}" '
                       f'width="13" height="10" fill="{look["colour"]}" '
                       f'stroke="{RULE}" stroke-width="0.8"/>')
            if look["grain"]:
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


def elevation_svg(job: Job, max_width: int = 1100) -> str:
    """The Run: the cabinet list drawn side by side.

    Panels are not in it, deliberately. A panel is not part of a cupboard run —
    it has no place in a line of carcasses — and keeping it out is also what
    keeps `wall_elevation_svg` with no room equal to this drawing, which
    tools/check_elevation.py asserts.
    """
    cabs = [c for c in job.cabinets if not c.is_panel]
    if not cabs:
        return ('<svg xmlns="http://www.w3.org/2000/svg" width="200" height="60">'
                f'<text x="10" y="34" font-size="13" fill="{MUTED}" '
                'font-family="sans-serif">No cabinets yet</text></svg>')

    std = job.std
    gap_mm = 20
    total_w = sum(c.width for c in cabs) + gap_mm * (len(cabs) - 1)
    max_h = max(c.height for c in cabs)
    pad = 46
    scale = min((max_width - pad * 2) / total_w, 520 / max_h)
    W = int(total_w * scale) + pad * 2
    rows = _legend_rows(job, _boards_drawn(job, cabs), W - pad * 2)
    leg = _legend_height(rows)
    H = int(max_h * scale) + pad * 2 + 14 + leg   # under the floor: tapes, then boards

    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
           f'viewBox="0 0 {W} {H}" font-family="system-ui,sans-serif">',
           f'<rect width="{W}" height="{H}" fill="none"/>']
    x = pad
    floor = int(max_h * scale) + pad
    for c in cabs:
        look = board_look(job, c.carcass_board)
        stroke, sw, dash = _layer_outline(layer_of(c))
        w = c.width * scale
        h = c.height * scale
        y = floor - h
        # One group per cabinet, carrying its number — the run has no wall to
        # drag along, so the press selects rather than moves (C9).
        out.append(f'<g class="ecabg erun" data-cab="{c.number}">')
        out.append(f'<rect class="ecab" data-cab="{c.number}" x="{x:.1f}" y="{y:.1f}" '
                   f'width="{w:.1f}" height="{h:.1f}" fill="{look["colour"]}" '
                   f'stroke="{stroke}" stroke-width="{sw}"{dash}/>')
        out += _interior(c, x, y, w, h, scale, std, materials=job.materials)
        out.append(f'<text x="{x + w / 2:.1f}" y="{floor + 16:.1f}" font-size="11" '
                   f'text-anchor="middle" fill="{INK}">{c.number}</text>')
        out.append(f'<text x="{x + w / 2:.1f}" y="{floor + 29:.1f}" font-size="9.5" '
                   f'text-anchor="middle" fill="{MUTED}">{c.width}x{c.height}x{c.depth}</text>')
        out.append("</g>")
        x += w + gap_mm * scale

    out.append(f'<line x1="{pad - 8}" y1="{floor:.1f}" x2="{W - pad + 8}" y2="{floor:.1f}" '
               f'stroke="{INK}" stroke-width="1.6"/>')
    out += _tape_note(job, pad, H - 8 - leg, W - pad * 2)
    out += _legend_svg(rows, pad, H - leg + 2)
    out.append("</svg>")
    return "\n".join(out)


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
        "wall_chain": chain(hung, wall.length) if hung else [],
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


def wall_elevation_svg(job: Job, wall_id: str, max_width: int = 1100) -> str:
    """One wall, face on, as a dimensioned working drawing.

    Cabinets at their true positions and heights, with the wall, its openings and
    obstructions behind them, and the fillers and plinth boards that were chosen.
    Widths are chained from the wall's start corner and heights from the floor.
    With no room there is no datum, so it falls back to the side-by-side sanity
    check, unchanged.
    """
    rm = job.room
    if rm is None:
        return elevation_svg(job, max_width)
    wall = next((w for w in rm.walls if w.id == wall_id), None)
    if wall is None:
        return _note_svg(f"No wall {escape(str(wall_id))}")

    if wall.length <= 0:
        return _note_svg(f"Wall {escape(wall.id)}: length not measured")

    std = job.std
    dims = wall_elevation_dims(job, wall_id)
    everywhere = {c.number: (c, p) for c, p, _ in placed(job)}
    on_wall = [(c, p, lay, geometry(c, std)) for c, p, lay in placed(job) if p.wall == wall_id]
    bad = {n for o in overlaps(job, std)
           if o.wall == wall_id or (o.across and wall_id in o.wall.split("/"))
           for n in (o.a, o.b)}

    length, top = wall.length, dims["top"]
    pad_l, pad_r, pad_t, pad_b = 72, 30, 64, 80
    scale = min((max_width - pad_l - pad_r) / length, 540 / top)
    W = int(length * scale) + pad_l + pad_r
    rows = _legend_rows(job, _boards_drawn(job, [c for c, _p, _l, _g in on_wall]),
                        W - pad_l - pad_r)
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
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
           f'viewBox="0 0 {W} {H}" font-family="system-ui,sans-serif">',
           '<defs><pattern id="ehatch" width="6" height="6" '
           'patternUnits="userSpaceOnUse" patternTransform="rotate(45)">'
           f'<line x1="0" y1="0" x2="0" y2="6" stroke="{MUTED}" stroke-width="1.4"/>'
           '</pattern></defs>',
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
    shapes = {}
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
        if sw_ >= 14 and sh >= 14:
            # at the outline's right edge: two outlines level at the top but of
            # different depths (a wall unit beside a tall one) then label apart
            out.append(f'<text x="{sx + sw_ - 3:.1f}" y="{sy + 10:.1f}" font-size="8" '
                       f'text-anchor="end" fill="{MUTED}">{escape(other)}: '
                       f'{", ".join(map(str, sorted(nums)))}</text>')
        out.append('</g>')
    if shapes:
        out.append(f'<text x="{pad_l}" y="{H - 32 - leg}" font-size="8.5" fill="{MUTED}">'
                   f'Shaded outlines at the corners are the runs on the walls either side, '
                   f'seen end on.</text>')

    for c, p, lay, g in on_wall:
        z0 = carcass_z(c, p, std)
        cx, cy, cw, ch = X(p.x), Y(z0 + g.height), g.width * scale, g.height * scale
        look = board_look(job, c.carcass_board)
        stroke, sw, dash = _layer_outline(lay, c.number in bad)
        # One group per cabinet — the carcass, what is inside it and its number —
        # so a drag moves the whole thing rather than an empty outline.
        out.append(f'<g class="ecabg" data-cab="{c.number}">')
        out.append(f'<rect class="ecab" data-cab="{c.number}" x="{cx:.1f}" y="{cy:.1f}" '
                   f'width="{cw:.1f}" height="{ch:.1f}" fill="{look["colour"]}" '
                   f'stroke="{stroke}" stroke-width="{sw}"{dash}/>')
        out += _interior(c, cx, cy, cw, ch, scale, std, flip=p.flip,
                         materials=job.materials)
        out.append(f'<text x="{cx + 4:.1f}" y="{cy + 11:.1f}" font-size="9.5" '
                   f'fill="{look["ink"]}">{c.number}</text>')
        if p.z == 0 and lay != "wall" and c.number not in boarded and cw >= 30:
            # no board covers these legs, so say what the space under the carcass is;
            # where each leg stands is not in Standard, so none is drawn
            out.append(f'<text x="{cx + cw / 2:.1f}" y="{Y(std.leg_height / 2) + 3:.1f}" '
                       f'font-size="8" text-anchor="middle" fill="{MUTED}">legs</text>')
        out.append('</g>')

    if any(c.door_count for c, _p, _lay, _g in on_wall):
        out.append(f'<text x="{pad_l}" y="{H - 20 - leg}" font-size="8.5" fill="{MUTED}">'
                   f'Hinges drawn {std.hinge_inset_drawn} mm in from each door end, any '
                   f'between spread evenly — indicative only, not a drilling reference.'
                   f'</text>')
    out += _tape_note(job, pad_l, H - 8 - leg, W - pad_l - pad_r)
    out += _legend_svg(rows, pad_l, H - leg + 2)

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

    out.append("</svg>")
    return "\n".join(out)


def plan_svg(job: Job, show=None, ghost=None, max_width: int = 1100,
             max_height: int = 620) -> str:
    """Plan of the room, looking down. Read-only.

    `show` is the layers drawn solid; `ghost` those drawn faint. A layer in
    neither is not drawn at all. Ghosting rather than hiding is deliberate — an
    overhead means nothing without the base run underneath it.

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
    items = [(c, p, lay) for c, p, lay in placed(job) if lay in show or lay in ghost]

    pts = list(corners)
    for cab, p, _ in items:
        pts += cabinet_footprint(rm, p, cab)
    xs = [q[0] for q in pts]
    ys = [q[1] for q in pts]
    pad = 54
    span_x = max(max(xs) - min(xs), 1)
    span_y = max(max(ys) - min(ys), 1)
    scale = min((max_width - pad * 2) / span_x, (max_height - pad * 2) / span_y)
    W = int(span_x * scale) + pad * 2
    rows = _legend_rows(job, _dedup(c.exterior_board for c, _p, _l in items),
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
    # ghosted first so the selected layers sit on top of them
    solid = [i for i in items if i[2] in show]
    faint = [i for i in items if i[2] in ghost and i[2] not in show]
    clashing = {c.cabinet for c in clashes(job, std)}
    colliding = {n for o in overlaps(job) for n in (o.a, o.b)}
    for cab, p, lay in faint:
        out += _plan_cabinet(rm, cab, p, lay, T, faint=True, bad=False,
                             colour=board_look(job, cab.exterior_board)["colour"])
    for cab, p, lay in solid:
        out += _plan_cabinet(rm, cab, p, lay, T, faint=False,
                             bad=cab.number in colliding,
                             colour=board_look(job, cab.exterior_board)["colour"])
    # over the cabinets, not under them: a swing that fouls something has to be
    # visible against the thing it fouls
    out += _plan_fronts(job, solid, clashing, T, std)
    # labels after every shape: an overhead sits over the base run it belongs to,
    # and a number you cannot read is worse than no number
    for cab, p, lay in solid:
        out += _plan_label(rm, cab, p, T)
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
    out = ['<g id="tracks" style="pointer-events:none">']
    for i, w in enumerate(rm.walls):
        (ax, ay), (bx, by) = T(corners[i]), T(corners[i + 1])
        out.append(f'<line class="track" data-wall="{escape(w.id)}" data-len="{w.length}" '
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


def _plan_cabinet(rm, cab, p, layer, T, faint, bad=False, colour=None):
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
    return [f'<polygon class="cab" data-cab="{cab.number}" data-layer="{layer}" '
            f'points="{pts}" fill="{fill}"{fill_op} '
            f'stroke="{_stroke}" stroke-width="{width}"{dash}{op}/>']


def _plan_label(rm, cab, p, T):
    """Number and size at the middle of the outline, whatever shape it is."""
    fp = [T(q) for q in cabinet_footprint(rm, p, cab)]
    cx = sum(x for x, _ in fp) / len(fp)
    cy = sum(y for _, y in fp) / len(fp)
    side = min(max(x for x, _ in fp) - min(x for x, _ in fp),
               max(y for _, y in fp) - min(y for _, y in fp))
    if side <= 24:
        return []
    g = geometry(cab)
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
              materials=None):
    """Doors, drawer faces and shelf lines, drawn from the bottom up.

    `flip` turns on the hinge marks and says which way a single door hangs. Left
    as None it draws exactly what the side-by-side sanity check always drew.

    `materials` is the job's board records. Every fill here is the colour of the
    board the cut list cuts that part from, resolved through `board_look`, and
    no colour is stated here: leaf *i* is `door_board(i)`, a drawer face is
    `face_board_of(d)`, and what is left of the body is the carcass board. With
    none passed the whole thing falls back to the neutral colour, so a caller
    that has no job still draws.

    Two things here are handles rather than drawing: each door leaf carries its
    cabinet, its index and the edge it hangs from, so clicking it can turn it
    round; and each join between two drawer faces carries the pair's span in both
    mm and pixels, so a drag can be read back into millimetres. The browser
    projects onto them exactly as it projects onto the plan's wall tracks — it
    picks a position along a span the engine gave it, and the engine re-divides
    the stack on drop.
    """
    out = []
    mats = materials or {}
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
                   f'height="{fhh:.1f}" fill="{look["colour"]}" stroke="{RULE}" '
                   f'stroke-width="0.8"/>')
        if look["grain"]:
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
                       f'fill="{look["colour"]}" stroke="{RULE}" stroke-width="0.8"/>')
            if look["grain"]:
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
