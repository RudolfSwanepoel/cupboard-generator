"""Validation. Criticals block the export; warnings do not.

Every rule here exists because a real job got it wrong. The finding reference
in each message points at docs/RULES.md so the reason is never lost.
"""
from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import List

from .engine import front_stack_check, generate_cabinet
from .model import Cabinet, Job, Panel, material_board, tape_for
from .room import (above_ceiling, blocked_openings, cab_corner_outline,
                   clashes as room_clashes, closure_error, corner_offset,
                   gaps as room_gaps, geometry, overlaps as room_overlaps,
                   placed, plinth_choice_for, runs as room_runs, tip_problems,
                   triangulate)
from .standard import Standard, STANDARD

CRITICAL = "critical"
WARNING = "warning"

ALLOWED_EDGE = {
    "", "PVC WOOD", "PVC WHITE", "PVC SOLID", "PVC BROOKHILL",
    "1mm WOOD", "2mm WOOD", "1mm SOLID", "2mm SOLID", "2mm BROOKHILL", "1mm BROOKHILL",
}


@dataclass
class Issue:
    level: str
    where: str
    message: str
    ref: str = ""

    def __str__(self):
        tag = "CRITICAL" if self.level == CRITICAL else "warning"
        ref = f"  [{self.ref}]" if self.ref else ""
        return f"{tag:>8}  {self.where:<12} {self.message}{ref}"


def validate(job: Job, panels: List[Panel]) -> List[Issue]:
    std = job.std
    out: List[Issue] = []
    out += _panel_fits_board(panels, std)
    out += _cabinet_structure(job.cabinets, std)
    out += _front_stacks(job.cabinets, std)
    out += _shelf_clears_back(job.cabinets, panels, std)
    out += _labels_unique(panels)
    out += _edge_materials(panels)
    out += _grain_on_decor(panels)
    out += _zero_quantities(panels)
    out += _drawer_boxes(job.cabinets)
    out += _boards_and_tapes(job)
    out += _supports(job.cabinets)
    out += _room(job, std)
    out += _gaps(job, std)
    out += _plinth(job, std)
    out += _placement_clashes(job, std)
    out += _room_heights(job, std)
    out += _outlines(job, std)
    return sorted(out, key=lambda i: (i.level != CRITICAL, i.where))


def _panel_fits_board(panels, std):
    """W2 — a 2882 mm strip was ordered off a 2750 mm board and quietly shortened."""
    out = []
    for p in panels:
        long_side, short_side = max(p.length, p.width), min(p.length, p.width)
        if long_side > std.sheet_l or short_side > std.sheet_w:
            out.append(Issue(CRITICAL, p.label,
                             f"{p.length}x{p.width} does not fit a {std.sheet_l}x{std.sheet_w} board",
                             "W2"))
    return out


def _cabinet_structure(cabinets, std):
    """D1 — cabinets 45 and 49 went to Plazaboard with no side panels."""
    out = []
    for c in cabinets:
        if c.doors and c.width <= 0:
            out.append(Issue(CRITICAL, str(c.number), "door on a cabinet with no width"))
        if c.drawer_list:
            runner = std.pick_runner(c.depth)
            if runner is None:
                out.append(Issue(
                    CRITICAL, str(c.number),
                    f"{c.depth} mm deep is too shallow for any runner "
                    f"(shortest is {min(std.runner_lengths)}, needs {std.runner_clearance} behind)"))
        if c.shelves and c.back == "none":
            out.append(Issue(WARNING, str(c.number),
                             "shelves in a cabinet with no back — check the shelf depth is intentional"))
    return out


def _front_stacks(cabinets, std):
    """W5 / D2 — cabinet 30's faces left 75 mm of open gap."""
    out = []
    for c in cabinets:
        res = front_stack_check(c, std)
        if res is None:
            continue
        expected, actual, gap = res
        if gap != 0:
            level = CRITICAL if abs(gap) > 2 * std.stack_gap else WARNING
            out.append(Issue(level, str(c.number),
                             f"front stack is {actual} in a {expected} opening ({gap:+d} mm)",
                             "W5"))
    return out


def _shelf_clears_back(cabinets, panels, std):
    """D3 — shelves ran the full carcass depth into a 16 mm inset back.

    The carcass depth is what the side panels are, not what the cabinet declares,
    and a shelf is any panel in the Shelve role whatever its designation.
    """
    out = []
    mine = defaultdict(list)
    for p in panels:
        mine[p.cabinet].append(p)
    for c in cabinets:
        if c.back == "none":
            continue
        sides = [p.width for p in mine[c.number] if p.role == "Side"]
        if not sides:
            continue
        limit = std.back_face_from_front(max(sides))
        for p in mine[c.number]:
            if p.role == "Shelve" and p.width > limit:
                out.append(Issue(CRITICAL, p.label,
                                 f"shelf {p.width} deep fouls the back at {limit}", "D3"))
    return out


def _labels_unique(panels):
    """D13 — labels 918, 919, 920, 917 and 314 each covered several different sizes.

    Generated panels are born with distinct designations (105a, 105b), so what
    this catches now is a bespoke or loose panel defined with the same
    designation as another of a different size. The fix is in the job, not here:
    the cut list never renames a panel.
    """
    sizes = defaultdict(set)
    for p in panels:
        sizes[p.label].add((p.material, p.length, p.width))
    return [Issue(WARNING, lab,
                  f"one designation on {len(v)} different panels: " +
                  ", ".join(f"{m} {l}x{w}" for m, l, w in sorted(v)) +
                  " — give each its own in the job", "D13")
            for lab, v in sizes.items() if len(v) > 1]


def _edge_materials(panels):
    """D6 / W10 — 'SOLID' is a board, not a tape; '2mm WOOD' and '2mm PVC Wood' are the same thing."""
    out = []
    for p in panels:
        if p.edge_material not in ALLOWED_EDGE:
            out.append(Issue(WARNING, p.label,
                             f"edge material {p.edge_material!r} is not in the lookup", "W10"))
        if (p.edge_l or p.edge_w) and not p.edge_material:
            out.append(Issue(CRITICAL, p.label, "edges specified but no edge material"))
    return out


def _grain_on_decor(panels):
    """W8 / D9 — grain was zero on 60 woodgrain panels; Plazaboard caught it, not us."""
    return [Issue(CRITICAL, p.label, "décor panel with grain not set", "W8")
            for p in panels if p.material == "DECOR" and not p.grain]


def _zero_quantities(panels):
    """W9 — qty 0 rows travelled all the way into the order."""
    return [Issue(WARNING, p.label, "quantity is zero", "W9") for p in panels if p.qty <= 0]


def _drawer_boxes(cabinets):
    """A box side taller than its own face would show above the drawer front.

    A face of no height at all is caught first and said plainly: it means the
    fixed rows in the stack have eaten the whole opening, and the share rows
    have nothing left to divide.
    """
    out = []
    for c in cabinets:
        for i, d in enumerate(c.drawer_list, start=1):
            if d.face_height <= 0:
                out.append(Issue(CRITICAL, str(c.number),
                                 f"drawer {i}: face height is {d.face_height} — the fixed "
                                 f"faces over-run the opening, leaving nothing for the "
                                 f"shared ones"))
                continue
            if d.box_height >= d.face_height:
                out.append(Issue(CRITICAL, str(c.number),
                                 f"drawer {i}: box {d.box_height} is not shorter than "
                                 f"its face {d.face_height}"))
    return out


def _boards_and_tapes(job: Job):
    """Every board a cabinet names must exist, and must have the tape it needs.

    The tapes are a lookup on the board, never a name built out of one, so a board
    with no tape mapped is reported by name rather than guessed at (D6 / W10:
    'SOLID' reached a real order as a tape, and it is a board). Only the tapes a
    cabinet actually uses are asked for — a cabinet with no drawers and no
    white-edged support never needs a drawer-box tape.
    """
    mats = job.materials
    out = []
    for c in job.cabinets:
        if c.template == "none":
            continue                       # its panels name their own materials
        for board, what in ((c.carcass_board, "carcass board"),
                            (c.exterior_board, "exterior board")):
            if board not in (mats or {}):
                out.append(Issue(CRITICAL, str(c.number),
                                 f"{what} {board!r} is not one of the job's materials "
                                 f"({', '.join(sorted(mats or {})) or 'none'})"))

        wants = [("carcass_edge", c.carcass_edge, c.exterior_board, "pvc",
                  "the fronts of its sides, top, bottom, shelves and dividers")]
        if any(r.edge == "white" for r in c.support_list) or c.drawer_list:
            wants.append(("drawer_box_edge", c.drawer_box_edge, c.carcass_board, "pvc",
                          "its drawer boxes and white-edged supports"))
        if c.doors or c.drawer_list or c.exposed_sides:
            wants.append(("door_edge", c.door_edge, c.exterior_board, "2mm",
                          "its doors, drawer faces and exposed panels"))
        for field, override, board, thickness, bands in wants:
            if override is not None:
                continue                   # this cabinet was told what to use
            if board in (mats or {}) and not tape_for(mats, board, thickness):
                out.append(Issue(WARNING, str(c.number),
                                 f"no {thickness} tape is mapped for "
                                 f"{material_board(mats, board)!r}, so {field} cannot be "
                                 f"derived for {bands} — map one on the material, or "
                                 f"override it on this cabinet"))

        # A drawer box is cut from the white board but banded in the carcass
        # board's colour. Whether it should follow the carcass board has not been
        # ruled, so it is reported rather than decided.
        if c.drawer_list and c.carcass_board != "MEL":
            out.append(Issue(WARNING, str(c.number),
                             f"carcass board is {c.carcass_board} but the drawer box "
                             f"sides and fronts are still cut from MEL, banded in the "
                             f"{c.carcass_board} tape — confirm which board the box "
                             f"should be"))
    return out


def _supports(cabinets):
    """The three legacy support numbers, where they contradict each other.

    `edged + white` greater than the total implied a negative plain count, which
    the old engine dropped in silence. The rows model has no subtraction, so the
    only place this can still arise is a stored job that predates it — and it is
    named rather than migrated on a guess.
    """
    out = []
    for c in cabinets:
        if not c.legacy_supports_negative:
            continue
        out.append(Issue(WARNING, str(c.number),
                         f"supports {c.supports} with {c.edged_supports} front-edged and "
                         f"{c.white_supports} white-edged leaves {c.supports - c.edged_supports - c.white_supports} "
                         f"plain — the three numbers contradict each other. "
                         f"{c.support_total} supports are being cut, which is what the "
                         f"cut list has always said; set the rows to say what was meant"))
    return out


def _room(job: Job, std):
    """A room built on measurements that contradict each other is worse than none.

    Nothing here runs when job.room is None, which is what keeps every job that
    predates the room model behaving exactly as it did.
    """
    rm = job.room
    if rm is None:
        return [Issue(WARNING, str(p.cabinet), "placed on a wall but the job has no room")
                for p in job.placements]

    out = []
    # Required site measurements. A default standing in for either would pass
    # every check below while meaning nothing.
    if not rm.ceiling or rm.ceiling <= 0:
        out.append(Issue(CRITICAL, rm.name,
                         "ceiling height not measured — it is a required site "
                         "measurement, and the ceiling check means nothing without it"))
    for w in rm.walls:
        if w.length <= 0:
            out.append(Issue(CRITICAL, f"wall {w.id}", "wall length not measured"))

    ids = [w.id for w in rm.walls]
    dupes = sorted({i for i in ids if ids.count(i) > 1})
    for i in dupes:
        out.append(Issue(CRITICAL, f"wall {i}", "two walls share this id"))
    if dupes:
        return out          # the chain is keyed by id; nothing below can be trusted

    err = closure_error(rm)
    if err > std.closure_block:
        out.append(Issue(CRITICAL, rm.name,
                         f"walls miss closing by {err} mm — the measurements "
                         f"contradict each other, remeasure before placing anything"))
    elif err > std.closure_warn:
        out.append(Issue(WARNING, rm.name, f"walls miss closing by {err} mm"))

    for i, w in enumerate(rm.walls):
        _, disagree = corner_offset(rm, i)
        if disagree > std.corner_disagree:
            nxt = rm.walls[(i + 1) % len(rm.walls)]
            out.append(Issue(WARNING, f"{w.id}-{nxt.id}",
                             f"corner measured {w.offset_end} from {w.id} but "
                             f"{nxt.offset_start} from {nxt.id}"))

    by_number = {c.number: c for c in job.cabinets}
    lengths = {w.id: w.length for w in rm.walls}
    for p in job.placements:
        if p.cabinet not in by_number:
            out.append(Issue(CRITICAL, str(p.cabinet),
                             "placement for a cabinet that does not exist"))
            continue
        if p.wall not in lengths:
            out.append(Issue(CRITICAL, str(p.cabinet),
                             f"placed on wall {p.wall!r}, which the room does not have"))
            continue
        end = p.x + by_number[p.cabinet].width
        if p.x < 0 or end > lengths[p.wall]:
            out.append(Issue(WARNING, str(p.cabinet),
                             f"sits {p.x}-{end} on wall {p.wall}, which is "
                             f"{lengths[p.wall]} long"))
    return out


def _gaps(job: Job, std):
    """Gaps, and what was decided about them.

    An undecided gap is a warning, not a critical: 'deliberately open' is a real
    answer and the app must not insert a filler on its own. But a gap nobody has
    ruled on is a filler nobody ordered, so it does not pass quietly either.
    """
    out = []
    fillers = 0
    for g in room_gaps(job, std):
        where = f"{g.wall}:{g.after if g.after is not None else 'start'}" \
                f"-{g.before if g.before is not None else 'end'}"
        if not g.treatment:
            out.append(Issue(WARNING, where,
                             f"{g.width} mm gap in the {g.layer} run with no treatment "
                             f"chosen — suggest {g.proposal}"))
            continue
        if g.treatment != "filler":
            continue
        fillers += 1
        if g.taper > std.taper_threshold:
            out.append(Issue(WARNING, where,
                             f"gap tapers {g.taper} mm over {g.depth} mm deep — the saw "
                             f"cannot cut a taper, so it ships {g.filler_width(std)} wide "
                             f"and is scribed on site"))
        if g.width < std.filler_min:
            out.append(Issue(WARNING, where,
                             f"{g.width} mm is under the {std.filler_min} mm filler "
                             f"minimum — growing a cabinet is the tidier fix"))
        elif g.width > std.filler_max:
            out.append(Issue(WARNING, where,
                             f"{g.width} mm is over the {std.filler_max} mm filler "
                             f"maximum — a cabinet or a blind corner suits it better"))

    if fillers and not std.codes_confirmed:
        out.append(Issue(WARNING, "11",
                         "panel code 11 (Filler) has not been confirmed with "
                         "Plazaboard — set Standard.codes_confirmed once it is"))
    return out


def _plinth(job: Job, std):
    """Plinth runs, and whether the legs can actually reach."""
    if job.room is None:
        return []
    out = []
    if not (std.leg_min <= std.leg_height <= std.leg_max):
        out.append(Issue(CRITICAL, "legs",
                         f"leg height {std.leg_height} is outside the "
                         f"{std.leg_min}-{std.leg_max} leg range — the legs "
                         f"cannot stand the carcass at that height"))

    live = {(r.wall, r.layer, r.first) for r in room_runs(job, std)}
    fitted = 0
    for r in room_runs(job, std):
        c = plinth_choice_for(job, r)
        if c is None or not c.fitted:
            continue
        if r.z != 0:
            out.append(Issue(WARNING, f"{r.wall}:{r.first}",
                             f"plinth asked for on a run {r.z} mm off the floor — "
                             f"a hung run stands on nothing, so none is made"))
            continue
        fitted += 1
    for c in job.plinths:
        if c.fitted and (c.wall, c.layer, c.first) not in live:
            out.append(Issue(WARNING, f"{c.wall}:{c.first}",
                             "plinth was chosen for a run that no longer starts "
                             "at that cabinet — no plinth is being made for it"))

    if fitted and not std.codes_confirmed:
        out.append(Issue(WARNING, "10",
                         "panel code 10 (Plinth) has not been confirmed with "
                         "Plazaboard — set Standard.codes_confirmed once it is"))
    return out


def _placement_clashes(job: Job, std):
    """Two cabinets in the same place, and fronts that cannot open.

    An overlap is a critical: two carcasses cannot occupy one stretch of wall,
    and a cut list built on that is wrong however good it looks. A door or
    drawer that fouls something is a warning — it is a real defect, but which
    way a door hangs is a judgement, and blocking the export over it would be
    the app overruling the person who measured the room.
    """
    out = []
    for o in room_overlaps(job):
        out.append(Issue(CRITICAL, f"{o.a}/{o.b}",
                         f"cabinets {o.a} and {o.b} overlap by {o.mm} mm on "
                         f"wall {o.wall}"))
    for c in room_clashes(job, std):
        thing = "door swing" if c.kind == "door" else "drawer pull-out"
        out.append(Issue(WARNING, str(c.cabinet),
                         f"{thing} fouls {c.against}"))
    return out


def _room_heights(job: Job, std):
    """What the plan cannot show and the elevation can: height against the room.

    A carcass that will not stand up under the ceiling is a critical. The ceiling
    is a required measurement now, so the check can be trusted, and a cabinet that
    cannot be stood in the room is as wrong as two that overlap. A cabinet across
    an opening stays a warning: opening sizes are site figures, and a unit hung
    across a window is sometimes exactly what was meant.
    """
    out = []
    for number, top, ceiling in above_ceiling(job, std):
        out.append(Issue(CRITICAL, str(number),
                         f"top of the carcass is at {top} mm, above the "
                         f"{ceiling} mm ceiling"))
    # Built flat and tipped up in one piece: a ceiling it clears standing but not
    # on the way up is an installation failure, so it blocks the same way.
    for number, top, need, ceiling in tip_problems(job, std):
        out.append(Issue(CRITICAL, str(number),
                         f"stands at {top} mm but cannot be tipped upright under the "
                         f"{ceiling} mm ceiling — built flat, it needs {need} mm to "
                         f"come up"))
    for b in blocked_openings(job, std):
        out.append(Issue(WARNING, str(b.cabinet),
                         f"stands across the {b.opening} on wall {b.wall} "
                         f"({b.x}-{b.x + b.width})"))
    return out


def _outlines(job: Job, std):
    """Whether each placed cabinet's geometry can be trusted.

    Every geometric check reads room.geometry, which reads the panels and the
    entered outline, or the corner parameters for a corner unit. So what needs
    saying is where a corner unit's parameters do not resolve to a shape, where
    an entered outline and a corner unit's panels disagree with what they
    declare, where no outline was entered for a shape that needs one, and where
    an outline is not a polygon at all.
    """
    out = []
    for cab, _p, _lay in placed(job):
        g = geometry(cab, std)
        where = str(cab.number)
        if cab.corner_on and cab_corner_outline(cab) is None:
            out.append(Issue(CRITICAL, where,
                             f"cabinet {cab.number}: corner parameters do not resolve to a "
                             f"shape — check corner_style, arm_a/arm_b and face_a/face_b"))
        if g.source in ("outline", "corner"):
            if len(g.footprint) < 3 or not triangulate(g.footprint):
                out.append(Issue(CRITICAL, where,
                                 "outline is not a polygon — checks cannot run on it"))
                continue
            if g.source == "corner":
                # A corner unit's outline is generated, not entered, so there is
                # nothing to cross-check the way an entered outline is checked
                # against panel_depth/panel_width below — its own outer sides
                # legitimately wrap the panels by a board thickness (spec item
                # 14). What is worth checking instead: that the two open faces
                # it declares actually match a side panel that was cut that wide,
                # and that the arms match the two wall sides — one board short of
                # its arm on one wall and two on the other, because one wraps the
                # other (cabinet 7: 834 = 850 - 16, 818 = 850 - 32).
                cut = Counter(p.width for p in generate_cabinet(cab, std)
                              if p.role == "Side" for _ in range(max(p.qty, 0)))
                for face, name in ((cab.face_a, "face_a"), (cab.face_b, "face_b")):
                    if face not in cut:
                        out.append(Issue(WARNING, where,
                                         f"cabinet {cab.number}: {name} is {face} but no side "
                                         f"panel is cut that wide — check the bespoke panels "
                                         f"match the corner parameters"))
                t = std.board_t
                rest = cut - Counter([cab.face_a, cab.face_b])
                walls = [(cab.arm_a - t, cab.arm_b - 2 * t), (cab.arm_a - 2 * t, cab.arm_b - t)]
                if not any(not (Counter(w) - rest) for w in walls):
                    (a1, b1), (a2, b2) = walls
                    out.append(Issue(WARNING, where,
                                     f"cabinet {cab.number}: arms {cab.arm_a}/{cab.arm_b} want wall "
                                     f"sides of {a1} and {b1} (or {a2} and {b2}), one wrapping the "
                                     f"other, but the sides cut besides the open faces are "
                                     f"{sorted(rest.elements())} — check arm_a/arm_b against the "
                                     f"bespoke sides"))
                # A door wider than every face it could hang on cannot close in
                # the opening, and its swing runs back into the box.
                longest = max(g.face_lengths, default=None)
                for w in sorted(set(g.door_widths)):
                    if longest is not None and w > longest:
                        out.append(Issue(WARNING, where,
                                         f"cabinet {cab.number}: its {w} door is wider than any "
                                         f"face it could hang on (the longest is {longest} mm) — "
                                         f"check the door against arm_a/arm_b and face_a/face_b"))
            else:
                if g.depth != g.panel_depth:
                    out.append(Issue(WARNING, where,
                                     f"outline comes out {g.depth} but its deepest panel is "
                                     f"{g.panel_depth} — one of them is wrong"))
                if g.panel_width is not None and g.width != g.panel_width:
                    out.append(Issue(WARNING, where,
                                     f"outline is {g.width} along the wall but its panels make "
                                     f"{g.panel_width} — one of them is wrong"))
        elif cab.template == "none":
            out.append(Issue(WARNING, where,
                             f"cabinet {cab.number}: no outline entered — approximated as the "
                             f"{g.width}x{g.depth} rectangle its panels make, which is not a "
                             f"measurement. A corner box is an L — enter its real outline or "
                             f"its corner parameters"))
        if g.source == "declared":
            out.append(Issue(WARNING, where,
                             "no top, bottom or rail to read a width from, and no outline — "
                             "checks are using the declared width"))
    return out


def report(issues: List[Issue]) -> str:
    if not issues:
        return "No issues."
    crit = sum(1 for i in issues if i.level == CRITICAL)
    lines = [f"{crit} critical, {len(issues) - crit} warnings", ""]
    lines += [str(i) for i in issues]
    return "\n".join(lines)


def blocking(issues: List[Issue]) -> bool:
    return any(i.level == CRITICAL for i in issues)
