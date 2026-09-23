"""Validation. Criticals block the export; warnings do not.

Every rule here exists because a real job got it wrong. The finding reference
in each message points at docs/RULES.md so the reason is never lost.
"""
from collections import Counter, defaultdict
from dataclasses import dataclass, replace
from typing import List

from .engine import front_stack_check, generate_cabinet, mitre_door_width
from .export_plaza import effective_price
from .model import (PANEL_ORIENTATIONS, TAPE_PREFIX, WHITE_TOKEN, Cabinet, Job,
                    Panel, grain_of, is_thin, material_board, material_offers,
                    material_thickness, material_token, tape_for)
from .room import (above_ceiling, arm_shelf_depth, arm_shelf_max_depth,
                   blind_door_width, blind_opening, blocked_openings,
                   cab_corner_outline, corner_shadow,
                   clashes as room_clashes, closure_error, corner_offset,
                   gaps as room_gaps, geometry, overlaps as room_overlaps,
                   panel_clashes as room_panel_clashes, placed,
                   plinth_choice_for, run_key, runs as room_runs, tip_inputs,
                   tip_problems,
                   triangulate)
from .engine import mitre_door_width
from .standard import Standard, STANDARD

CRITICAL = "critical"
WARNING = "warning"

# Tags an issue that says a cabinet needs an edging its board does not offer.
EDGING_REF = "EDGING"

# Above this many boards on one project, say so. A guideline about cost and
# complexity — every extra board is another part sheet and another offcut pile —
# and deliberately not a limit.
BOARD_GUIDELINE = 5

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
    # The stable id of the rule that raised it. Every critical carries one; it
    # is what an acceptance is stored against, so it never changes once given.
    check: str = ""
    # Filled in by `validate` from the job's acceptances, never by a rule:
    # whether this critical may be accepted at all (`ACCEPTABLE`), the reason it
    # was accepted with, and whether an acceptance was given and has lapsed.
    acceptable: bool = False
    accepted: str = ""
    lapsed: bool = False

    @property
    def blocks(self) -> bool:
        """A critical blocks the export unless it has been accepted."""
        return self.level == CRITICAL and not self.accepted

    def __str__(self):
        tag = "CRITICAL" if self.level == CRITICAL else "warning"
        if self.level == CRITICAL and self.accepted:
            tag = "ACCEPTED"
        ref = f"  [{self.ref}]" if self.ref else ""
        why = f"  — accepted: {self.accepted}" if self.accepted else ""
        return f"{tag:>8}  {self.where:<12} {self.message}{ref}{why}"


# --- accepting a site-dependent critical -------------------------------------
#
# Ruled 22 September 2026. Some criticals say something about the SITE rather
# than about the cut list, and the operator can accept one of those with a
# reason; the export then goes ahead. A critical that protects the cut list's
# integrity always blocks.
#
# A check becomes acceptable by being given an entry here and nowhere else: its
# id, and the function that fingerprints exactly the inputs it read. The
# fingerprint is what makes an acceptance lapse — it was given for one cabinet
# in one room, and if either changes it no longer holds.
#
# Today that is the tip-up check alone. The mitre door-swing critical was ruled
# blocking on purpose and is deliberately NOT here.

def _tip_fingerprint(job: Job, where: str):
    """The tip-up check's inputs for one cabinet: its geometry off the panel set
    (never the declared sizes), its legs, where it stands and the ceiling."""
    rm = job.room
    if rm is None:
        return None
    for cab, p, _lay in placed(job):
        if str(cab.number) == str(where):
            t = tip_inputs(cab, p, rm.ceiling, job.std)
            return (f"height {t['height']} · depth {t['depth']} · legs {t['legs']} · "
                    f"setback {t['setback']} · underside {t['underside']} · "
                    f"ceiling {t['ceiling']}")
    return None


ACCEPTABLE = {
    "tip-up": _tip_fingerprint,
}


def fingerprint(job: Job, check: str, where: str):
    """What an acceptance of this critical is stored with, or None if it cannot
    be accepted (not an acceptable check, or nothing there to fingerprint)."""
    fn = ACCEPTABLE.get(check)
    return fn(job, where) if fn else None


def lapsed_acceptances(job: Job) -> list:
    """The acceptances in the job that no longer hold: the check is no longer an
    acceptable one, or what it read has changed since it was given.

    Read-only, like everything else here. Dropping them from the job is the
    caller's business — the browser does it and says so.
    """
    return [a for a in (job.acceptances or [])
            if fingerprint(job, a.check, a.where) != a.fingerprint]


def _apply_acceptances(job: Job, issues: List[Issue]):
    """Mark each critical as acceptable, accepted or lapsed, off the job."""
    given = {(a.check, str(a.where)): a for a in (job.acceptances or [])}
    for i in issues:
        if i.level != CRITICAL or i.check not in ACCEPTABLE:
            continue
        i.acceptable = True
        a = given.get((i.check, str(i.where)))
        if a is None:
            continue
        if fingerprint(job, i.check, i.where) == a.fingerprint:
            i.accepted = a.reason.strip() or "accepted"
        else:
            i.lapsed = True


def validate(job: Job, panels: List[Panel]) -> List[Issue]:
    std = job.std
    out: List[Issue] = []
    out += _panel_fits_board(panels, std)
    out += _cabinet_structure(job.cabinets, std)
    out += _front_stacks(job.cabinets, std)
    out += _shelf_clears_back(job.cabinets, panels, std)
    out += _labels_unique(panels)
    # asked first, so a panel whose edging is missing for a reason already named
    # against its cabinet is not reported a second time, panel by panel
    tape_issues = _boards_and_tapes(job)
    out += _edge_materials(job, panels,
                           {i.where for i in tape_issues if i.ref == EDGING_REF})
    out += _grain_on_boards(job, panels)
    out += _zero_quantities(panels)
    out += _drawer_boxes(job.cabinets)
    out += _panels(job)
    out += _project_boards(job)
    out += tape_issues
    out += _carcass_thickness(job, std)
    out += _thin_boards(job)
    out += _board_prices(job, panels)
    out += _supports(job.cabinets)
    out += _support_edging(job)
    out += _corners(job, std)
    out += _room(job, std)
    out += _gaps(job, std)
    out += _plinth(job, std)
    out += _placement_clashes(job, std)
    out += _blind_clearance(job, std)
    out += _room_heights(job, std)
    out += _outlines(job, std)
    _apply_acceptances(job, out)
    return sorted(out, key=lambda i: (i.level != CRITICAL, i.where))


def _panel_fits_board(panels, std):
    """W2 — a 2882 mm strip was ordered off a 2750 mm board and quietly shortened.

    A grain-locked panel cannot be turned, so it is measured as it will be cut:
    length along the sheet's length, width across it. A panel that only fits
    rotated fits on a plain board and does not fit on a grained one, and the
    nester would silently reject it — which is how a board swap onto a grained
    board can take a panel off the layout without anything saying so. Checked
    against all three fixed jobs when this was tightened: no new issue on any of
    them, so nothing already quoted moves.
    """
    out = []
    for p in panels:
        # Too big whichever way round it goes: the original fault, worded as it
        # always was — check_boards and the stored snapshots pin it.
        rotated = (max(p.length, p.width) > std.sheet_l
                   or min(p.length, p.width) > std.sheet_w)
        locked = bool(p.grain) and (p.length > std.sheet_l or p.width > std.sheet_w)
        too_big = rotated or locked
        # The grain is only worth mentioning when it is the REASON: a panel that
        # would fit turned, on a board that will not let it turn.
        how = "" if rotated else " with the grain locked, so it cannot be turned"
        if too_big:
            out.append(Issue(CRITICAL, p.label,
                             f"{p.length}x{p.width} does not fit a "
                             f"{std.sheet_l}x{std.sheet_w} board{how}",
                             "W2", check="panel-fits-board"))
    return out


def _cabinet_structure(cabinets, std):
    """D1 — cabinets 45 and 49 went to Plazaboard with no side panels."""
    out = []
    for c in cabinets:
        if c.is_panel:
            continue                       # not a box: see _panels
        if c.door_count and c.width <= 0:
            out.append(Issue(CRITICAL, str(c.number), "door on a cabinet with no width", check="door-no-width"))
        if c.drawer_list:
            runner = std.pick_runner(c.depth)
            if runner is None:
                out.append(Issue(
                    CRITICAL, str(c.number),
                    f"{c.depth} mm deep is too shallow for any runner "
                    f"(shortest is {min(std.runner_lengths)}, needs {std.runner_clearance} behind)", check="runner-depth"))
        if c.shelves and c.back == "none":
            out.append(Issue(WARNING, str(c.number),
                             "shelves in a cabinet with no back — check the shelf depth is intentional"))
    return out


def _front_stacks(cabinets, std):
    """W5 / D2 — cabinet 30's faces left 75 mm of open gap."""
    out = []
    for c in cabinets:
        if c.is_panel:
            continue                       # no front to stack
        res = front_stack_check(c, std)
        if res is None:
            continue
        expected, actual, gap = res
        if gap != 0:
            level = CRITICAL if abs(gap) > 2 * std.stack_gap else WARNING
            out.append(Issue(level, str(c.number),
                             f"front stack is {actual} in a {expected} opening ({gap:+d} mm)",
                             "W5", check="front-stack"))
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
                                 f"shelf {p.width} deep fouls the back at {limit}", "D3", check="shelf-fouls-back"))
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


def _edge_materials(job, panels, covered=frozenset()):
    """D6 / W10 — 'SOLID' is a board, not a tape; '2mm WOOD' and '2mm PVC Wood'
    are the same thing.

    The lookup is the settled list plus everything this job's own boards can
    generate, one token times three thicknesses. A board added to the library
    after this file was written is a real tape and must not be reported as a
    typo; a name that matches neither still is.
    """
    allowed = set(ALLOWED_EDGE)
    for key in (job.materials or {}):
        allowed.update(tape_for(job.materials, key, k) for k in TAPE_PREFIX)
    allowed.discard("")
    allowed.add("")
    out = []
    for p in panels:
        if p.edge_material not in allowed:
            out.append(Issue(WARNING, p.label,
                             f"edge material {p.edge_material!r} is not in the lookup", "W10"))
        if ((p.edge_l or p.edge_w) and not p.edge_material
                and str(p.cabinet) not in covered):
            # Tagged EDGING like the rest: this is the one that catches a typed
            # panel — bespoke or loose — left banded with nothing to band it in,
            # which is what a board swap onto a board that does not offer the
            # kind produces. The wording is unchanged; check_edging.py pins it.
            out.append(Issue(CRITICAL, p.label, "edges specified but no edge material",
                             EDGING_REF, check="edge-material"))
    return out


def _grain_on_boards(job, panels):
    """W8 / D9 — grain was zero on 60 woodgrain panels; Plazaboard caught it, not us.

    Asked of the board's own record rather than of one board id, so it holds for
    any grained board in the library and not only the one that was in it the day
    this was written.
    """
    return [Issue(CRITICAL, p.label,
                  f"{material_board(job.materials, p.material)} is a grained board "
                  f"and this panel has grain not set", "W8", check="grain-on-board")
            for p in panels
            if grain_of(job.materials, p.material) and not p.grain]


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
        # A cabinet switched to Panel keeps its drawer stack in the job file and
        # builds nothing from it — the house pattern — so it must not be
        # reported on either.
        if c.is_panel:
            continue
        for i, d in enumerate(c.drawer_list, start=1):
            if d.face_height <= 0:
                out.append(Issue(CRITICAL, str(c.number),
                                 f"drawer {i}: face height is {d.face_height} — the fixed "
                                 f"faces over-run the opening, leaving nothing for the "
                                 f"shared ones", check="drawer-face-overrun"))
                continue
            if d.box_height >= d.face_height:
                out.append(Issue(CRITICAL, str(c.number),
                                 f"drawer {i}: box {d.box_height} is not shorter than "
                                 f"its face {d.face_height}", check="drawer-box-height"))
    return out


def _panels(job: Job):
    """An independent panel: a board, a size that can be cut, and edging the
    board actually offers.

    Deliberately short. What a panel shares with everything else on the cut list
    is already checked where it always was, and repeating it here would be two
    messages for one problem: a panel too big for a sheet is `_panel_fits_board`,
    a board the project never selected is `_board_prices`, an unreadable edging
    name is `_edge_materials`. What is left is what only a panel can get wrong.

    An UNPLACED panel is not a fault. A panel cut and not put anywhere is
    normal — it is a part on an order, not a cupboard missing from a room.
    """
    out = []
    mats = job.materials
    for c in job.cabinets:
        if not c.is_panel:
            continue
        spec = c.panel_spec
        where = str(c.number)
        if not spec.board:
            out.append(Issue(CRITICAL, where,
                             "panel with no board — pick what it is cut from in "
                             "Panel design", check="panel-board"))
        if spec.orientation not in PANEL_ORIENTATIONS:
            out.append(Issue(CRITICAL, where,
                             f"panel orientation {spec.orientation!r} is not one of "
                             f"{', '.join(PANEL_ORIENTATIONS)} — it cannot be drawn "
                             f"or placed until it is one of them", check="panel-orientation"))
        for name, v in (("a", spec.a), ("b", spec.b)):
            if int(v or 0) <= 0:
                out.append(Issue(CRITICAL, where,
                                 f"panel size {name} is {int(v or 0)} — both extents "
                                 f"have to be a real finished size", check="panel-size"))
        # Edging asked for that the board does not sell. Same shape and the same
        # tag as A9: it blocks, and it says what to tick.
        banded = int(spec.edge_long or 0) + int(spec.edge_short or 0)
        colour = spec.edge_board or spec.board
        if spec.edge_kind and banded and not tape_for(mats, colour, spec.edge_kind):
            out.append(Issue(CRITICAL, where,
                             f"panel is edged {TAPE_PREFIX.get(spec.edge_kind, spec.edge_kind)} "
                             f"in {colour or 'no board'}, which does not offer it — tick "
                             f"that kind on {colour or 'the board'} in the Boards tab, or "
                             f"choose another edging",
                             EDGING_REF, check="panel-edging"))
    return out


def _project_boards(job: Job):
    """A project picks its boards before anything is cut from them.

    Nothing can be chosen until at least one board is selected, so a job with
    cabinets and no boards is a critical that names what is missing. More than
    five is a guideline about cost and complexity, not a limit — every extra
    board is another part sheet and another offcut pile — so it warns and
    nothing more.
    """
    out = []
    ids = job.board_ids
    if job.cabinets and not ids:
        out.append(Issue(CRITICAL, job.name,
                         "no boards selected — pick at least one board from the "
                         "library before adding cabinets; a cabinet has to be cut "
                         "from something", check="project-boards"))
    if len(ids) > BOARD_GUIDELINE:
        out.append(Issue(WARNING, job.name,
                         f"{len(ids)} boards selected ({', '.join(ids)}) — over the "
                         f"{BOARD_GUIDELINE} the job usually wants. Each one is a "
                         f"part sheet of its own and its own offcut pile. A guideline "
                         f"about cost and complexity, not a limit"))
    return out


def _board_prices(job: Job, panels):
    """Every board on the cut list has to be one this project priced.

    A backing board is not chosen the way a carcass is — the engine reaches for
    it — so a project can end up cutting a board it never selected, and a board
    nobody selected has no captured price. That quotes it at R0 and the total
    still looks like a number, which is the worst way to be wrong. Named here
    rather than discovered on an invoice.
    """
    out = []
    for mat in sorted({p.material for p in panels if p.material}):
        if mat not in (job.materials or {}):
            out.append(Issue(CRITICAL, mat,
                             f"panels are cut from {mat!r}, which this project has not "
                             f"selected — it has no price, so it is quoted at R0. Tick "
                             f"it into the project on the Boards tab, or change the "
                             f"cabinets that name it", check="board-unselected"))
        elif not effective_price(job, mat):
            out.append(Issue(WARNING, mat,
                             f"{material_board(job.materials, mat)!r} has no price on "
                             f"it, so its boards are quoted at R0 — set a Last price on "
                             f"it in the library and re-select it"))
    return out


def _boards_and_tapes(job: Job):
    """Every board a cabinet names must exist, and must be able to name its tape.

    A tape name is generated from the board's token, so what can go wrong is no
    longer a missing mapping but a board with nothing to generate from. That is
    reported by name rather than a plausible-looking tape being invented for it
    (D6 / W10: 'SOLID' reached a real order as a tape, and it is a board).
    """
    mats = job.materials
    out = []
    for c in job.cabinets:
        if c.is_panel or c.template == "none":
            continue    # bespoke names its own materials; a panel is _panels'
        # The back board is only asked for when something is actually cut from it
        # — a back, or a drawer on a grooved 3 mm base. A cabinet with no back and
        # no board bases never touches it, so it is not nagged about one.
        chosen = [(c.carcass_board, "carcass board"),
                  (c.exterior_board, "exterior board")]
        if c.needs_back_board:
            chosen.append((c.back_board, "back board"))
        # The drawer box and face, and any leaf cut from a board of its own, are
        # selections in their own right now, so they are checked like the rest.
        if c.drawer_list:
            chosen.append((c.drawer_carcass, "drawer box board"))
            chosen.append((c.drawer_face, "drawer face board"))
            for i, d in enumerate(c.drawer_list, start=1):
                if d.box_board:
                    chosen.append((d.box_board, f"drawer {i} box board"))
                if d.face_board:
                    chosen.append((d.face_board, f"drawer {i} face board"))
        for i in range(c.door_count):
            if c.door_boards[i:i + 1] and c.door_boards[i]:
                chosen.append((c.door_boards[i], f"door leaf {i + 1} board"))
        # Everything else the cabinet names — the two edging boards, a support
        # row's board, a bespoke panel's material — off the one list, so a board
        # the project does not carry cannot reach the cut list through a field
        # this check had not heard of. Only ids not already named above: the
        # blank ones are "follow Structure", which is not a missing choice.
        named = {b for b, _ in chosen}
        for board, label in c.board_refs():
            if board not in named:
                chosen.append((board, label))
                named.add(board)
        for board, what in chosen:
            if not board:
                out.append(Issue(CRITICAL, str(c.number),
                                 f"no {what} chosen — pick one from the boards this "
                                 f"project selected "
                                 f"({', '.join(job.board_ids) or 'none yet'})", check="cabinet-board-missing"))
            elif board not in (mats or {}):
                out.append(Issue(CRITICAL, str(c.number),
                                 f"{what} {board!r} is not one of the job's boards "
                                 f"({', '.join(sorted(mats or {})) or 'none'})", check="cabinet-board-unknown"))
            elif board not in job.board_ids:
                out.append(Issue(WARNING, str(c.number),
                                 f"{what} {board!r} is not among the boards this "
                                 f"project selected ({', '.join(job.board_ids)})"))

        wants = [("carcass_edge", c.carcass_edge, c.exterior_board, "pvc",
                  "the fronts of its sides, top, bottom, shelves and dividers")]
        if c.drawer_list:
            wants.append(("drawer_box_edge", c.drawer_box_edge, c.carcass_board, "pvc",
                          "its drawer boxes"))
        if c.door_count or c.exposed_sides:
            wants.append(("door_edge", c.door_edge,
                          c.door_edge_board or c.exterior_board,
                          c.door_edge_kind or c.exterior_tape,
                          "its doors and exposed panels"))
        if c.drawer_list:
            wants.append(("drawer_face_edge", c.door_edge,
                          c.drawer_edge_board or c.door_edge_board or c.exterior_board,
                          c.drawer_edge_kind or c.door_edge_kind or c.exterior_tape,
                          "its drawer faces"))
        # The blind panel names its own board and its own thickness, so it is
        # asked the same question as everything else: does that board sell that
        # edging. Its one banded edge is the one reached past every time the
        # cupboard is opened, so going out unedged in silence is not an option.
        if c.corner_kind == "blind" and c.blind_width:
            wants.append(("blind_edge", None, c.blind_panel_board,
                          c.blind_edge_thickness, "its blind panel"))
        for field, override, board, thickness, bands in wants:
            if override is not None:
                continue                   # this cabinet was told what to use
            if board not in (mats or {}) or tape_for(mats, board, thickness):
                continue
            name = material_board(mats, board)
            if thickness not in material_offers(mats, board):
                # The board says it has no such edging. That is a decision made
                # on the Boards tab, so the cut list cannot quietly go out
                # without the tape, or with a name the board never offered.
                offered = [TAPE_PREFIX[k] for k in material_offers(mats, board)]
                has = (f"only offers {', '.join(offered)}" if offered
                       else "has no edging (Has Edging is off)")
                out.append(Issue(CRITICAL, str(c.number),
                                 f"{bands} need {TAPE_PREFIX[thickness]} edging in "
                                 f"{name!r}, which {has}. Tick "
                                 f"{TAPE_PREFIX[thickness]} on that board in the "
                                 f"Boards tab, or choose another board here",
                                 EDGING_REF, check="edging-offered"))
            elif not material_token(mats, board):
                out.append(Issue(WARNING, str(c.number),
                                 f"{name!r} has no name to build "
                                 f"edging from, so {field} cannot be generated for "
                                 f"{bands} — give the board an edging name in the "
                                 f"library, or override the edging on this cabinet"))
        if c.exterior_tape not in ("1mm", "2mm"):
            out.append(Issue(WARNING, str(c.number),
                             f"exterior edging {c.exterior_tape!r} is neither 1mm nor "
                             f"2mm — 2mm is being used"))

        # The drawer box is a chosen board now, not a hardcoded MEL, so there is
        # nothing left to query — the box and its edging agree by construction.
    return out


def _thin_boards(job: Job):
    """A 3 mm sheet where a sheet has to be built from, or a thick board on a back.

    The editor does not offer either, but a stored choice is never silently
    changed — an old job, a board that was thinned in the library, or a hand-edited
    file can all carry one, and a 3 mm door is a real defect that would otherwise
    be cut. Named here so the flag in the editor has something behind it.
    """
    out = []
    for c in job.cabinets:
        if c.is_panel or c.template == "none":
            continue    # bespoke is specified by hand; a panel may be any thickness
        wants = [(c.carcass_board, "carcass board"), (c.exterior_board, "exterior board")]
        if c.blind_board:
            wants.append((c.blind_board, "blind panel board"))
        for i, b in enumerate(c.door_boards or []):
            if b:
                wants.append((b, f"door leaf {i + 1} board"))
        for i, d in enumerate(c.drawer_list or []):
            if d.box_board:
                wants.append((d.box_board, f"drawer {i + 1} box board"))
            if d.face_board:
                wants.append((d.face_board, f"drawer {i + 1} face board"))
        for board, what in wants:
            if board and board in (job.materials or {}) and is_thin(job.materials, board):
                out.append(Issue(WARNING, str(c.number),
                                 f"{what} {material_board(job.materials, board)!r} is "
                                 f"{material_thickness(job.materials, board)} mm — that "
                                 f"is a backing sheet, not something to build from. "
                                 f"Choose a board of full thickness here"))
        if (c.needs_back_board and c.back_board
                and c.back_board in (job.materials or {})
                and not is_thin(job.materials, c.back_board)):
            out.append(Issue(WARNING, str(c.number),
                             f"backing board {material_board(job.materials, c.back_board)!r} "
                             f"is {material_thickness(job.materials, c.back_board)} mm — "
                             f"the back is grooved for a 3 mm sheet. Choose the backing "
                             f"board, or change the back fixing"))
    return out


def _carcass_thickness(job: Job, std):
    """The engine assumes a `Standard.board_t` carcass from end to end.

    Internal width is W - 2t, an exposed end is depth + t, the back is grooved
    2 x groove_engage into a 2t deduction, a plinth butt loses t, and a corner
    unit's wall sides are one and two boards short of its arms. None of that
    reads the board's own thickness, and thickness-driven geometry is deferred —
    so a board of any other thickness is named here rather than quietly cut to
    the wrong size.
    """
    out = []
    for c in job.cabinets:
        # A panel is one board, whatever thickness it is — the 16 mm arithmetic
        # this names is carcass arithmetic, and a panel does none of it.
        if c.is_panel or c.template == "none":
            continue                       # its panels are specified by hand
        for board, what in ((c.carcass_board, "carcass board"),
                            (c.exterior_board, "exterior board")):
            t = material_thickness(job.materials, board)
            if t and t != std.board_t:
                out.append(Issue(WARNING, str(c.number),
                                 f"{what} {material_board(job.materials, board)!r} is "
                                 f"{t} mm, but every size here is cut for a "
                                 f"{std.board_t} mm board — internal width, the back "
                                 f"groove, an exposed end and a plinth butt are all "
                                 f"{std.board_t} mm arithmetic. Thickness-driven "
                                 f"geometry is not built; check this cabinet by hand"))
    return out


def _support_edging(job: Job):
    """A support row that asks for an edging the Boards tab cannot supply.

    Nothing states an edging but the Boards record (20 September 2026), so a row
    whose board no longer offers its kind — and a row written before the control
    that was asking for white when the project carries no white board — has no
    name to be given. It is named here rather than going out unedged in silence
    or carrying a tape no board in the project sells.
    """
    mats = job.materials
    out = []
    for c in job.cabinets:
        if c.is_panel or c.template == "none":
            continue                       # neither cuts a support
        for i, row in enumerate(c.support_list, start=1):
            kind = c.support_row_kind(row)
            if not kind or c.support_row_tape(mats, row):
                continue                   # not edged, or edged fine
            if row.board or row.kind:
                board = c.support_row_board(mats, row)
                offered = [TAPE_PREFIX[k] for k in material_offers(mats, board)]
                has = (f"only offers {', '.join(offered)}" if offered
                       else "has no edging (Has Edging is off)")
                out.append(Issue(CRITICAL, str(c.number),
                                 f"support row {i} asks for {TAPE_PREFIX[kind]} edging "
                                 f"in {material_board(mats, board)!r}, which {has}. "
                                 f"Tick {TAPE_PREFIX[kind]} on that board in the "
                                 f"Boards tab, or choose another board for the row",
                                 EDGING_REF, check="support-edging"))
            else:
                out.append(Issue(CRITICAL, str(c.number),
                                 f"support row {i} is white-edged, but no board in "
                                 f"this project offers PVC under the name "
                                 f"{WHITE_TOKEN!r}. Give the row a board and an "
                                 f"edging of its own, or tick PVC on the white "
                                 f"board in the Boards tab", EDGING_REF, check="support-white-edge"))
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
        if c.is_panel:
            continue                       # cuts no supports
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
                         "measurement, and the ceiling check means nothing without it", check="ceiling-measured"))
    for w in rm.walls:
        if w.length <= 0:
            out.append(Issue(CRITICAL, f"wall {w.id}", "wall length not measured", check="wall-length"))

    ids = [w.id for w in rm.walls]
    dupes = sorted({i for i in ids if ids.count(i) > 1})
    for i in dupes:
        out.append(Issue(CRITICAL, f"wall {i}", "two walls share this id", check="wall-id-unique"))
    if dupes:
        return out          # the chain is keyed by id; nothing below can be trusted

    err = closure_error(rm)
    if err > std.closure_block:
        out.append(Issue(CRITICAL, rm.name,
                         f"walls miss closing by {err} mm — the measurements "
                         f"contradict each other, remeasure before placing anything", check="room-closure"))
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
                             "placement for a cabinet that does not exist", check="placement-cabinet"))
            continue
        if by_number[p.cabinet].is_panel:
            continue        # panels take no part in the room checks yet (Part E)
        if p.wall not in lengths:
            out.append(Issue(CRITICAL, str(p.cabinet),
                             f"placed on wall {p.wall!r}, which the room does not have", check="placement-wall"))
            continue
        cab = by_number[p.cabinet]
        # its real reach along the wall, never the declared width (hard rule 1):
        # a mitre declared 1200 wide with a 1000 arm used to be reported as
        # running 200 mm past the end of a wall it was sitting flush against
        reach = geometry(cab, std).width
        end = p.x + reach
        if p.x < 0 or end > lengths[p.wall]:
            out.append(Issue(WARNING, str(p.cabinet),
                             f"sits {p.x}-{end} on wall {p.wall}, which is "
                             f"{lengths[p.wall]} long"))
        # A corner unit stands in a corner. The editor moves it there whenever
        # its type, hand or length changes; this catches one dragged back out.
        if cab.corner_on and cab.corner_kind in ("mitre", "ell", "blind") \
                and geometry(cab, std).source in ("corner", "panels") \
                and corner_shadow(rm, cab, p, std) is None:
            want = 0 if cab.hand == "L" else lengths[p.wall] - reach
            out.append(Issue(WARNING, str(p.cabinet),
                             f"corner unit {cab.number} is not standing in a corner: "
                             f"its {'left' if cab.hand == 'L' else 'right'}-hand end "
                             f"belongs at the {'start' if cab.hand == 'L' else 'end'} "
                             f"of wall {p.wall} (x = {want}), and it is at x = {p.x}"))
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
                         f"cannot stand the carcass at that height", check="leg-range"))

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



def _corners(job: Job, std):
    """What only a corner unit can get wrong. Ruled 22 September 2026.

    This runs over every cabinet, placed or not, because all of it is about what
    the unit CUTS rather than where it stands — and a corner unit that cuts the
    wrong thing is wrong on the bench whether or not it has been given a wall.

    The first two are what "the corner unit does nothing" looked like from the
    outside. Ticking Corner unit left the Style dropdown on its blank option, so
    `corner_on` stayed false and a straight W x D box went on the cut list with
    nothing said; and an ell has no ruled construction, so it must say so rather
    than quietly cutting nothing.
    """
    out = []
    for cab in job.cabinets:
        if cab.is_panel:
            continue
        where = str(cab.number)
        if cab.corner_ticked and not cab.corner_style:
            out.append(Issue(WARNING, where,
                             f"cabinet {cab.number}: Corner unit is ticked but no type is "
                             f"chosen, so it is being cut as a straight "
                             f"{cab.width}x{cab.depth} box — choose Mitre, Ell or Blind"))
            continue
        kind = cab.corner_kind
        if kind == "ell":
            # Rudolf has never built one and has deferred the construction, so
            # the shape is all there is. Nothing is invented: it cuts nothing,
            # and this says so rather than letting an empty cabinet cost R0.
            if cab.template != "none" and not cab.bespoke:
                out.append(Issue(CRITICAL, where,
                                 f"cabinet {cab.number}: ell corner — construction not decided "
                                 f"yet, so this unit cuts nothing. Add bespoke panels in the "
                                 f"job file or change the type", check="ell-construction"))
        elif kind == "mitre":
            out += _mitre(cab, where, std)
        elif kind == "blind":
            out += _blind(cab, where, std)
    return out


def _mitre(cab, where: str, std):
    """A mitre's own measurements, against what they have to describe."""
    out = []
    if cab.template == "none":
        return out                      # hand-typed panels; the job is the answer
    if cab.arm_shelves > 0:
        top = arm_shelf_max_depth(cab, std, cab.arm_shelf_arm)
        depth = arm_shelf_depth(cab, std)
        if top is not None and depth is not None and depth > top:
            arm = cab.arm_shelf_arm.upper()
            out.append(Issue(CRITICAL, where,
                             f"cabinet {cab.number}: arm shelf is {depth} mm deep on arm {arm}, "
                             f"and the deepest that clears both the closed door "
                             f"({std.mitre_shelf_clear} mm) and the hinge plate "
                             f"({std.hinge_clearance} mm) is {top} mm", check="arm-shelf-depth"))
    return out


def _blind(cab, where: str, std):
    """A blind corner's three ways of not being a blind corner (Q4 ruling).

    All three are CRITICAL, because each of them means the door on the cut list
    cannot be the door that gets fitted.
    """
    out = []
    if cab.template == "none":
        return out
    if not cab.blind_width:
        out.append(Issue(CRITICAL, where,
                         f"cabinet {cab.number}: blind corner with no blind panel width — "
                         f"nothing says how much of the {cab.width} mm carcass the panel "
                         f"covers, so neither the panel nor the door can be cut", check="blind-width-missing"))
        return out
    b, t = int(cab.blind_width), std.board_t
    if b >= cab.width - 2 * t:
        out.append(Issue(CRITICAL, where,
                         f"cabinet {cab.number}: blind panel is {b} mm in a {cab.width} mm "
                         f"carcass, which leaves no opening at all (the two sides take "
                         f"{2 * t} mm) — the panel has to be under {cab.width - 2 * t} mm", check="blind-width-too-wide"))
        return out
    if (blind_door_width(cab, std) or 0) <= 0:
        out.append(Issue(CRITICAL, where,
                         f"cabinet {cab.number}: blind corner leaves a door "
                         f"{blind_door_width(cab, std)} mm wide — check the carcass width "
                         f"against the {b} mm blind panel", check="blind-door-width"))
    return out


def _placement_clashes(job: Job, std):
    """Two cabinets in the same place, and fronts that cannot open.

    An overlap is a critical: two carcasses cannot occupy one stretch of wall,
    and a cut list built on that is wrong however good it looks. A door or
    drawer that fouls something is a warning — it is a real defect, but which
    way a door hangs is a judgement, and blocking the export over it would be
    the app overruling the person who measured the room.

    A PANEL standing in something is a warning for the same reason: a bulkhead
    front is meant to sit flush on the run below it, and how far it laps a
    carcass is a judgement about how the job is built. A panel is cut and
    costed whether or not it is placed, so its position moves no figure on the
    order and must not block one.

    A CORNER UNIT'S DOOR IS THE ONE EXCEPTION, and it is a deliberate one
    (ruled 22 September 2026). An ordinary door that fouls something can be
    rehung, moved or lived with, and which way it hangs is the fitter's
    judgement. A mitre's door cannot: it hangs on the mitre face, there is no
    other edge to hang it from, and its width is derived from the arms rather
    than chosen — so a swing that fouls the runs either side of it is a unit
    that cannot be built as drawn, not a preference. It blocks the export, and
    the message says the widest door that would clear so there is something to
    do about it.

    Ordinary doors stay WARNINGS. Do not "tidy" this into one rule.
    """
    out = []
    by_number = {c.number: c for c in job.cabinets}
    for o in room_overlaps(job):
        out.append(Issue(CRITICAL, f"{o.a}/{o.b}",
                         f"cabinets {o.a} and {o.b} overlap by {o.mm} mm on "
                         f"wall {o.wall}", check="overlap"))
    for c in room_clashes(job, std):
        thing = "door swing" if c.kind == "door" else "drawer pull-out"
        cab = by_number.get(c.cabinet)
        if c.kind == "door" and cab is not None and cab.corner_kind == "mitre":
            out.append(Issue(CRITICAL, str(c.cabinet),
                             f"corner unit {c.cabinet}: its door swing fouls {c.against}, "
                             f"and a mitre door hangs on the mitre face or nowhere — "
                             f"{_door_that_clears(job, cab, std)}", check="mitre-door-swing"))
            continue
        out.append(Issue(WARNING, str(c.cabinet),
                         f"{thing} fouls {c.against}"))
    for c in room_panel_clashes(job, std):
        out.append(Issue(WARNING, str(c.panel),
                         f"panel stands in {c.against} on wall {c.wall}"))
    return out



def _door_that_clears(job: Job, cab, std) -> str:
    """The widest this mitre's door could be cut and still swing clear.

    Said out loud because a critical that only says "it fouls" leaves nothing to
    do. The answer is found by trying widths against the real swing check rather
    than by a formula: `Cabinet.corner_door_width` is the override the operator
    would set, so the trial sets exactly that and asks `room.clashes` again. The
    search only runs when a corner door has already fouled something, which is
    rare, and it costs about nine passes.

    Widening the arms is the other way out, and the message says so, but there
    is no single figure for it: bigger arms move the face further into the room
    and widen the derived door at the same time, so the two do not resolve to
    one number the way a door width does.
    """
    def fouls(width):
        trial = replace(cab, corner_door_width=width)
        rest = [trial if c.number == cab.number else c for c in job.cabinets]
        return any(x.cabinet == cab.number and x.kind == "door"
                   for x in room_clashes(replace(job, cabinets=rest), std))

    top = max(1, mitre_door_width(cab, std))
    if fouls(1):
        return ("no door width clears it at all — the arms have to grow or "
                "whatever it fouls has to move")
    lo, hi = 1, top                     # lo always clears, hi always fouls
    while hi - lo > 1:
        mid = (lo + hi) // 2
        if fouls(mid):
            hi = mid
        else:
            lo = mid
    return (f"the widest that clears is {lo} mm against the {top} mm derived from "
            f"the arms — set the door width override, or grow the arms")



def _blind_clearance(job: Job, std):
    """A return run standing across a blind unit's door opening.

    CRITICAL, ruled 22 September 2026 (Q4) — the same exception as a mitre's
    door swing, for the same reason. A blind corner exists for exactly one
    purpose: to hold its door far enough from the corner that the run on the
    return wall does not block it. A return run that reaches past the blind
    panel defeats the whole unit, and no amount of fitting will fix it, so it
    blocks rather than warns.

    What reaches: the return cabinet's own depth, plus its door front, and
    nothing else. No handle clearance is added (ruled 22 September 2026) — if a
    real job needs one it belongs in Standard, not guessed at here.

    What it is measured against is the DOOR, and that is the re-read the inset
    blind panel asked for (22 September 2026). Moving the panel inside the
    carcass moved the clear OPENING one board further from the corner — it now
    starts at t + B rather than at B — but the door in front of it did not move:
    its corner-end edge still stands `B + door_single_gap / 2` from the corner,
    lapping the panel's face. A return run reaching between B and B + t clears
    the opening and still stops the door opening, so the threshold stays at B,
    which is half a gap inside the door edge and therefore the safe side of it.
    Testing the opening instead would be wrong in the unsafe direction.

    Nothing is checked unless the unit actually sits flush in a corner, because
    `corner_shadow` is what says which wall the return run is on, and until it
    does there is no return run to be in the way of.
    """
    rm = job.room
    if rm is None:
        return []
    out = []
    items = placed(job)
    for cab, p, lay in items:
        if cab.corner_kind != "blind" or not cab.blind_width:
            continue
        shadow = corner_shadow(rm, cab, p, std)
        if shadow is None:
            continue
        wall_id, _at, _w, _d = shadow
        # Everything else standing on the same wall in the same run. A wall unit
        # over the return run is not what blocks a base unit's door.
        same = [(o, op) for o, op, ol in items
                if o.number != cab.number and op.wall == wall_id
                and run_key(ol) == run_key(lay)]
        if not same:
            continue
        # The one nearest the corner. The shadow starts at the corner end, and
        # which end that is follows the hand: a right-handed unit turns onto the
        # START of the next wall, a left-handed one onto the END of the previous.
        if cab.hand == "L":
            other, _op = max(same, key=lambda t: t[1].x + geometry(t[0], std).width)
        else:
            other, _op = min(same, key=lambda t: t[1].x)
        og = geometry(other, std)
        reach = og.depth + (std.board_t if og.door_widths else 0)
        b = int(cab.blind_width)
        if reach > b:
            out.append(Issue(CRITICAL, str(cab.number),
                             f"cabinet {cab.number}: cabinet {other.number} on wall {wall_id} "
                             f"reaches {reach} mm off that wall (its {og.depth} mm depth"
                             + (f" and a {std.board_t} mm door front" if og.door_widths else "")
                             + f"), past the {b} mm blind panel and into the door — "
                             f"the blind panel has to be at least {reach} mm, or the return "
                             f"run shallower", check="blind-clearance"))
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
                         f"{ceiling} mm ceiling", check="above-ceiling"))
    # Built flat and tipped up in one piece: a ceiling it clears standing but not
    # on the way up is an installation failure, so it blocks the same way.
    for number, top, need, ceiling in tip_problems(job, std):
        out.append(Issue(CRITICAL, str(number),
                         f"stands at {top} mm but cannot be tipped upright under the "
                         f"{ceiling} mm ceiling — built flat, it needs {need} mm to "
                         f"come up", check="tip-up"))
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
        # A BLIND corner is deliberately shapeless here: its plan is a plain
        # rectangle W x D like any other cabinet, so `cab_corner_outline` gives
        # None for one by design and that is not a fault (ruled 22 Sept 2026).
        if (cab.corner_on and cab.corner_kind != "blind"
                and cab_corner_outline(cab) is None):
            out.append(Issue(CRITICAL, where,
                             f"cabinet {cab.number}: corner parameters do not resolve to a "
                             f"shape — check corner_style, arm_a/arm_b and face_a/face_b", check="corner-shape"))
        if g.source in ("outline", "corner"):
            if len(g.footprint) < 3 or not triangulate(g.footprint):
                out.append(Issue(CRITICAL, where,
                                 "outline is not a polygon — checks cannot run on it", check="outline-polygon"))
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
    crit = sum(1 for i in issues if i.blocks)
    took = sum(1 for i in issues if i.level == CRITICAL and i.accepted)
    warn = sum(1 for i in issues if i.level != CRITICAL)
    head = f"{crit} critical, {warn} warnings"
    if took:
        head += f", {took} accepted"
    lines = [head, ""]
    lines += [str(i) for i in issues]
    return "\n".join(lines)


def blocking(issues: List[Issue]) -> bool:
    """Any critical that has not been accepted. Only a site-dependent critical
    can be accepted (`ACCEPTABLE`); every other one blocks as it always has."""
    return any(i.blocks for i in issues)
