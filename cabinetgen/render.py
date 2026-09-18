"""Front elevation of a job, as SVG.

Cabinets are drawn side by side to scale, with doors, drawer faces and shelf
lines shown. It is a sanity check, not a working drawing: if a cabinet looks
wrong here it is wrong in the cut list too.
"""
from html import escape
from typing import List

from .model import Cabinet, Job, hinge_side
from .room import (LAYERS, cabinet_footprint, carcass_z, clashes, corner_points,
                   gap_outline, gaps, geometry, overlaps, placed, plinth_choice_for,
                   plinth_lengths, pullout_envelope, return_profiles, run_key, runs,
                   swing_envelopes, to_world, wall_frames)
from .standard import Standard, STANDARD

INK = "#191c1a"
RULE = "#aab1a9"
FAINT = "#d3d7d0"
CARC = "#f2f3f0"
DOOR = "#dceaea"
FACE = "#f5ebd6"
MUTED = "#767e78"
CRIT = "#a4303f"


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
            if c.template == "none":
                continue
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
    cabs = [c for c in job.cabinets]
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
    H = int(max_h * scale) + pad * 2 + 14        # room under the floor for the tapes

    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
           f'viewBox="0 0 {W} {H}" font-family="system-ui,sans-serif">',
           f'<rect width="{W}" height="{H}" fill="none"/>']
    x = pad
    floor = H - pad - 14
    for c in cabs:
        w = c.width * scale
        h = c.height * scale
        y = floor - h
        out.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" '
                   f'fill="{CARC}" stroke="{INK}" stroke-width="1.4"/>')
        out += _interior(c, x, y, w, h, scale, std)
        out.append(f'<text x="{x + w / 2:.1f}" y="{floor + 16:.1f}" font-size="11" '
                   f'text-anchor="middle" fill="{INK}">{c.number}</text>')
        out.append(f'<text x="{x + w / 2:.1f}" y="{floor + 29:.1f}" font-size="9.5" '
                   f'text-anchor="middle" fill="{MUTED}">{c.width}x{c.height}x{c.depth}</text>')
        x += w + gap_mm * scale

    out.append(f'<line x1="{pad - 8}" y1="{floor:.1f}" x2="{W - pad + 8}" y2="{floor:.1f}" '
               f'stroke="{INK}" stroke-width="1.6"/>')
    out += _tape_note(job, pad, H - 8, W - pad * 2)
    out.append("</svg>")
    return "\n".join(out)


LAYER_FILL = {"base": CARC, "wall": DOOR, "tall": FACE}


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
    H = int(top * scale) + pad_t + pad_b

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
        out.append(f'<text x="{pad_l}" y="{H - 32}" font-size="8.5" fill="{MUTED}">'
                   f'Shaded outlines at the corners are the runs on the walls either side, '
                   f'seen end on.</text>')

    for c, p, lay, g in on_wall:
        z0 = carcass_z(c, p, std)
        cx, cy, cw, ch = X(p.x), Y(z0 + g.height), g.width * scale, g.height * scale
        stroke, sw = (CRIT, "2") if c.number in bad else (INK, "1.3")
        # One group per cabinet — the carcass, what is inside it and its number —
        # so a drag moves the whole thing rather than an empty outline.
        out.append(f'<g class="ecabg" data-cab="{c.number}">')
        out.append(f'<rect class="ecab" data-cab="{c.number}" x="{cx:.1f}" y="{cy:.1f}" '
                   f'width="{cw:.1f}" height="{ch:.1f}" fill="{LAYER_FILL.get(lay, CARC)}" '
                   f'stroke="{stroke}" stroke-width="{sw}"/>')
        out += _interior(c, cx, cy, cw, ch, scale, std, flip=p.flip)
        out.append(f'<text x="{cx + 4:.1f}" y="{cy + 11:.1f}" font-size="9.5" '
                   f'fill="{INK}">{c.number}</text>')
        if p.z == 0 and lay != "wall" and c.number not in boarded and cw >= 30:
            # no board covers these legs, so say what the space under the carcass is;
            # where each leg stands is not in Standard, so none is drawn
            out.append(f'<text x="{cx + cw / 2:.1f}" y="{Y(std.leg_height / 2) + 3:.1f}" '
                       f'font-size="8" text-anchor="middle" fill="{MUTED}">legs</text>')
        out.append('</g>')

    if any(c.door_count for c, _p, _lay, _g in on_wall):
        out.append(f'<text x="{pad_l}" y="{H - 20}" font-size="8.5" fill="{MUTED}">'
                   f'Hinges drawn {std.hinge_inset_drawn} mm in from each door end, any '
                   f'between spread evenly — indicative only, not a drilling reference.'
                   f'</text>')
    out += _tape_note(job, pad_l, H - 8, W - pad_l - pad_r)

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
    H = int(span_y * scale) + pad * 2

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
        out += _plan_cabinet(rm, cab, p, lay, T, faint=True, bad=False)
    for cab, p, lay in solid:
        out += _plan_cabinet(rm, cab, p, lay, T, faint=False,
                             bad=cab.number in colliding)
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


def _plan_cabinet(rm, cab, p, layer, T, faint, bad=False):
    fp = [T(q) for q in cabinet_footprint(rm, p, cab)]
    pts = " ".join(f"{x:.1f},{y:.1f}" for x, y in fp)
    # A wall unit sits over the base run, so it is drawn the way a kitchen plan
    # draws one: dashed, and translucent enough to read what is underneath.
    dash = ' stroke-dasharray="5 3"' if layer == "wall" else ""
    fill_op = ' fill-opacity="0.45"' if layer == "wall" else ""
    op = ' opacity="0.30"' if faint else ""
    fill = "#f6e0e3" if bad else LAYER_FILL.get(layer, CARC)
    stroke = CRIT if bad else INK
    width = "2" if bad else "1.1"
    return [f'<polygon class="cab" data-cab="{cab.number}" data-layer="{layer}" '
            f'points="{pts}" fill="{fill}"{fill_op} '
            f'stroke="{stroke}" stroke-width="{width}"{dash}{op}/>']


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


def _hinge_marks(c: Cabinet, x0, top, dw, dh, door_h, flip, std: Standard):
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
        left, right = x0 + i * dw, x0 + i * dw + dw - 1
        hinge_x, latch_x = (left, right) if side == "L" else (right, left)
        out.append(f'<g class="hinge" data-cab="{c.number}" data-door="{i}" '
                   f'data-side="{side}">'
                   f'<polyline points="{latch_x:.1f},{top:.1f} {hinge_x:.1f},{top + dh / 2:.1f} '
                   f'{latch_x:.1f},{top + dh:.1f}" fill="none" stroke="{MUTED}" '
                   f'stroke-width="0.7" stroke-dasharray="3 2"/>')
        for mm in marks:                      # measured up from the bottom of the door
            out.append(f'<circle class="hinge-at" data-mm="{mm}" '
                       f'cx="{hinge_x + (3 if side == "L" else -3):.1f}" '
                       f'cy="{top + dh - mm * per_mm:.1f}" r="1.8" fill="{MUTED}"/>')
        if dh > 30 and dw > 34:
            tx = hinge_x + (5 if side == "L" else -5)
            anchor = "start" if side == "L" else "end"
            out.append(f'<text x="{tx:.1f}" y="{top + dh - 5:.1f}" font-size="7.5" '
                       f'text-anchor="{anchor}" fill="{MUTED}">{hinges} hinges</text>')
        out.append("</g>")
    return out


def _interior(c: Cabinet, x, y, w, h, scale, std: Standard, flip=None):
    """Doors, drawer faces and shelf lines, drawn from the bottom up.

    `flip` turns on the hinge marks and says which way a single door hangs. Left
    as None it draws exactly what the side-by-side sanity check always drew.

    Two things here are handles rather than drawing: each door leaf carries its
    cabinet, its index and the edge it hangs from, so clicking it can turn it
    round; and each join between two drawer faces carries the pair's span in both
    mm and pixels, so a drag can be read back into millimetres. The browser
    projects onto them exactly as it projects onto the plan's wall tracks — it
    picks a position along a span the engine gave it, and the engine re-divides
    the stack on drop.
    """
    out = []
    stack = c.drawer_list
    leaves = c.door_count
    door_h = 0
    if leaves:
        door_h = c.door_height or (c.height - std.door_height_gap)

    cursor = y + h                      # bottom of the cabinet, in svg y
    tops = [0.0] * len(stack)           # svg y of each face's top edge
    for i in range(len(stack) - 1, -1, -1):
        d = stack[i]
        fh = d.face_height * scale
        cursor -= fh
        tops[i] = cursor
        out.append(f'<rect x="{x + 2:.1f}" y="{cursor + 1:.1f}" width="{w - 4:.1f}" '
                   f'height="{max(fh - 2, 1):.1f}" fill="{FACE}" stroke="{RULE}" '
                   f'stroke-width="0.8"/>')
        if fh > 13:
            out.append(f'<text x="{x + w / 2:.1f}" y="{cursor + fh / 2 + 3.5:.1f}" '
                       f'font-size="9" text-anchor="middle" fill="{MUTED}">'
                       f'{d.face_height}</text>')
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
            out.append(f'<rect class="edoor" data-cab="{c.number}" data-door="{i}" '
                       f'data-hinge="{side}" x="{x + 2 + i * dw:.1f}" y="{top:.1f}" '
                       f'width="{dw - 1:.1f}" height="{dh:.1f}" fill="{DOOR}" '
                       f'stroke="{RULE}" stroke-width="0.8"/>')
        if flip is not None:
            out += _hinge_marks(c, x + 2, top, dw, dh, door_h, flip, std)
        if dh > 20:
            out.append(f'<text x="{x + w / 2:.1f}" y="{top + dh / 2 + 3.5:.1f}" '
                       f'font-size="9" text-anchor="middle" fill="{MUTED}">'
                       f'{leaves} x {std.door_width(c.width, leaves)}</text>')
        cursor = top

    # shelves, spread through whatever the doors cover
    n = c.shelves + c.fixed_shelves
    if n and not stack:
        span = y + h - cursor if leaves else h
        base = cursor if leaves else y
        for i in range(1, n + 1):
            sy = base + span * i / (n + 1)
            out.append(f'<line x1="{x + 4:.1f}" y1="{sy:.1f}" x2="{x + w - 4:.1f}" '
                       f'y2="{sy:.1f}" stroke="{FAINT}" stroke-width="1" '
                       f'stroke-dasharray="4 3"/>')
    if c.divider_count:
        out.append(f'<line x1="{x + w / 2:.1f}" y1="{y + 4:.1f}" x2="{x + w / 2:.1f}" '
                   f'y2="{y + h - 4:.1f}" stroke="{FAINT}" stroke-width="1.2"/>')
    return out

