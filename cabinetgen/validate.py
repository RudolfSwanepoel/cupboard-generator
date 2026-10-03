"""Validation. Criticals block the export; warnings do not.

Every rule here exists because a real job got it wrong. The finding reference
in each message points at docs/RULES.md so the reason is never lost.
"""
import math
from collections import Counter, defaultdict
from dataclasses import dataclass, replace
from typing import List

from .engine import front_stack_check, generate_cabinet, mitre_door_width
from .export_plaza import effective_price
from .model import (PANEL_ORIENTATIONS, TAPE_PREFIX, WHITE_TOKEN, Cabinet, Job,
                    Panel, grain_of, is_thin, material_board, material_offers,
                    material_thickness, material_token, panel_signature, tape_for)
from .room import (above_ceiling, arm_shelf_depth, arm_shelf_max_depth,
                   attached_carcass_overlaps, cabinet_by_number, host_of,
                   blind_door_width, blind_opening, blocked_openings,
                   cab_corner_outline, corner_angle, corner_shadow,
                   clashes as room_clashes, closure_error, above_wall,
                   crossing_walls, low_openings, unit_corner,
                   gaps as room_gaps, geometry, overlaps as room_overlaps,
                   panel_clashes as room_panel_clashes, placed,
                   plinth_choice_for, plinth_open_corners, run_key, runs as room_runs, tip_inputs,
                   ceiling_inputs_for,
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

# The edging names allowed on a cut list whatever the project carries: none.
# Every other name is what the job's own boards generate (_edge_materials).
# The settled list of WOOD / SOLID / BROOKHILL names that used to sit here was
# hardcoded edging, and retired with the typed overrides (28 September 2026).
ALLOWED_EDGE = {""}


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
# Today that is tip-up and, since 29 September 2026 (Rudolf), above-ceiling —
# a carcass top above the MEASURED ceiling, which is a site matter (a bulkhead
# to be cut, a ceiling measured low). Everything else blocks: no ceiling
# measured (`ceiling-measured`) is a missing site figure, a panel longer than
# the board can never be cut, and the mitre door-swing critical was ruled
# blocking on purpose. None of those is here, deliberately.

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


def _ceiling_fingerprint(job: Job, where: str):
    """The above-ceiling check's inputs for one item: where it stands, its
    height off the panel set (never declared) and the measured ceiling —
    `room.ceiling_inputs`, exactly what `above_ceiling` compares."""
    t = ceiling_inputs_for(job, where, job.std)
    if t is None:
        return None
    return f"underside {t['underside']} · height {t['height']} · ceiling {t['ceiling']}"


ACCEPTABLE = {
    "tip-up": _tip_fingerprint,
    "above-ceiling": _ceiling_fingerprint,
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
    job.bind_runners()
    out: List[Issue] = []
    out += _panel_fits_board(panels, std)
    out += _runners(job)
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
    out += _inner_drawers(job)
    out += _drawer_setting(job)
    out += _panels(job)
    out += _project_boards(job)
    out += tape_issues
    out += _carcass_thickness(job, std)
    out += _thin_boards(job)
    out += _board_prices(job, panels)
    out += _supports(job.cabinets)
    out += _support_edging(job)
    out += _support_layout(job)
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


def _runners(job: Job):
    """A cabinet whose drawers hang on a runner the project never selected
    (28 September 2026). The same reasoning as a board the project never
    selected: nothing captured a price for it, and a record the job does not
    carry is one the next edit of the library can change under it. CRITICAL.
    A blank runner is the built-in LEGACY record every job before the catalogue
    was quoted on, and is not a fault."""
    out = []
    for c in job.cabinets:
        if c.is_panel or not c.drawer_list or not c.runner:
            continue
        if c.runner not in (job.runners or {}):
            known = c.runner_rec is not None
            out.append(Issue(CRITICAL, str(c.number),
                             f"its drawers hang on runner {c.runner}, which this project "
                             f"has not selected — tick it on Catalogue -> Runners"
                             + ("" if known else " (it is not in the catalogue either; "
                                "the drawers are cut on the legacy lengths until it is)"),
                             check="runner-not-selected"))
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
            rr = c.runner_or_legacy
            runner = std.pick_runner(c.depth, rr.lengths)
            if runner is None:
                out.append(Issue(
                    CRITICAL, str(c.number),
                    f"{c.depth} mm deep is too shallow for any length of "
                    f"{rr.name or 'its runner'} (shortest is {rr.shortest}, needs "
                    f"{std.runner_clearance} behind)", check="runner-depth"))
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
    # "Different" is any difference but the qty (ruled 28 September 2026):
    # board, size, grain, edge counts, pot holes, edging name — the signature
    # born_distinct letters generated panels by, so this never fires on one.
    sigs = defaultdict(list)
    for p in panels:
        sig = panel_signature(p)
        if sig not in sigs[p.label]:
            sigs[p.label].append(sig)

    def said(sig):
        m, l, w, grain, el, ew, holes, edge = sig
        return (f"{m} {l}x{w}" + (" grain" if grain else "") +
                (f" {edge or 'unedged'} {el}L/{ew}S" if (el or ew or edge) else "") +
                (f" {holes} holes" if holes else ""))
    return [Issue(WARNING, lab,
                  f"one designation on {len(v)} different panels: " +
                  ", ".join(said(x) for x in v) +
                  " — give each its own in the job", "D13")
            for lab, v in sigs.items() if len(v) > 1]


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
    """A face of no height at all, said plainly: it means the fixed rows in the
    stack have eaten the whole opening, and the share rows have nothing left
    to divide. Where a box stands against its face is `_drawer_setting`'s."""
    out = []
    for c in cabinets:
        # A cabinet switched to Panel keeps its drawer stack in the job file and
        # builds nothing from it — the house pattern — so it must not be
        # reported on either.
        if c.is_panel:
            continue
        for i, d in enumerate(c.drawer_list, start=1):
            if d.inner:
                continue                   # its face IS its box: see _inner_drawers
            if d.face_height <= 0:
                out.append(Issue(CRITICAL, str(c.number),
                                 f"drawer {i}: face height is {d.face_height} — the fixed "
                                 f"faces over-run the opening, leaving nothing for the "
                                 f"shared ones", check="drawer-face-overrun"))
                continue
            # "box not shorter than its face" (drawer-box-height) is retired:
            # replaced by the face rule in _drawer_setting (ruled 28 Sept 2026,
            # "faces lead, boxes follow") — a box may be as tall as its face
            # at offset 0, if it then lies within it.
    return out


def _drawer_setting(job: Job):
    """The drawer checks — "faces lead, boxes follow" (ruled by Rudolf, 28
    September 2026, replacing the brief's Part 5 box-height rules). The faces
    are spaced exactly as always; each box then sits at the bottom of its own
    face, its drawer's `offset` up (default 21). Every position is
    `room.drawer_layout`'s — the one place a box is placed — so these, the
    support-foul critical and the 3D cannot disagree. All CRITICAL, stable ids:

    * `drawer-box-face` (rule 1): an outer box not entirely within its own
      face's height — its bottom below the face bottom, or its top above the
      face top. A box can never be mounted higher or lower than its own face.
      The tallest box a face takes is its height less the offset.
    * `drawer-bottom-offset` (rule 3): the BOTTOM drawer's offset below the
      default (21) — its runner would stand below the bottom panel. It may be
      raised, never lowered.
    * `drawer-box-clash` (rule 8): a box into the box above it. Where
      `drawer-box-face` has already named the drawer it is not repeated (an
      outer box within its own face cannot reach the next); between inner
      drawers it is a box overlapping the one above.
    * `drawer-inner-gap` (rule 7): less than `Standard.inner_drawer_min_gap`
      (30) clear between two inner boxes, one over the other, where they do
      not already overlap.
    * `drawer-runner-height`: a box lower than its runner's `height` (45).
      The runner checks are otherwise unchanged (`runner-depth`, and the
      inner drawers' `drawer-inner-range`).
    """
    from .room import drawer_layout, drawer_rise
    out = []
    std = job.std
    for c in job.cabinets:
        if c.is_panel or not c.drawer_list:
            continue
        try:
            lay = drawer_layout(c, std, job.materials)
        except ValueError:
            continue                       # no runner fits: runner-depth says so
        rr = c.runner_or_legacy
        drawers = c.drawer_list
        rise = drawer_rise(c, std)
        outer = [u for u in lay if not u["inner"]]
        lowest = min(outer, key=lambda u: u["face"][0]) if outer else None
        named = set()
        clear = std.drawer_box_clear
        for u in outer:
            f0, f1 = u["face"]
            if f1 <= f0:
                continue                   # no face at all: drawer-face-overrun says so
            b0, b1 = u["box"][4], u["box"][5]
            # never flush: drawer_box_clear inside the face both ends (29 Sept 2026)
            if b0 < f0 + clear or b1 > f1 - clear:
                where = (f"{f0 + clear - b0} too low — its bottom must be {clear} mm above "
                         f"the face bottom at {f0}" if b0 < f0 + clear
                         else f"{b1 - (f1 - clear)} too high — its top must be {clear} mm "
                              f"under the face top at {f1}")
                out.append(Issue(CRITICAL, str(c.number),
                                 f"drawer {u['n']}: its box runs {b0}-{b1}, {where}. A box "
                                 f"lies within its own face and never flush with it. At an "
                                 f"offset of {u['offset']} the tallest box this face takes "
                                 f"is {u['max_box']}", check="drawer-box-face"))
                named.add(u["n"])
        if lowest is not None and lowest["offset"] < rise:
            out.append(Issue(CRITICAL, str(c.number),
                             f"drawer {lowest['n']} is the bottom drawer and its box is set "
                             f"{lowest['offset']} above its face bottom — below {rise}, its "
                             f"runner would stand below the bottom panel. Raise it to at "
                             f"least {rise}", check="drawer-bottom-offset"))
        order = sorted(lay, key=lambda u: u["box"][4])
        for lo, hi in zip(order, order[1:]):
            gap = hi["box"][4] - lo["box"][5]
            if gap < 0 and lo["n"] not in named:
                out.append(Issue(CRITICAL, str(c.number),
                                 f"drawer {lo['n']}: its box reaches {lo['box'][5]}, into "
                                 f"drawer {hi['n']}'s box above, which starts at {hi['box'][4]}",
                                 check="drawer-box-clash"))
            elif 0 <= gap < std.inner_drawer_min_gap and lo["inner"] and hi["inner"]:
                out.append(Issue(CRITICAL, str(c.number),
                                 f"inner drawers {lo['n']} and {hi['n']}: {gap} clear between "
                                 f"their boxes ({lo['box'][5]} to {hi['box'][4]}) — at least "
                                 f"{std.inner_drawer_min_gap} is needed", check="drawer-inner-gap"))
        for u in lay:
            d = drawers[u["index"]]
            bh = c.box_height_of(d, std)
            if bh >= rr.height:
                continue
            if d.box_height is None and not d.inner and \
                    c.box_top_limit_of(d, std) < u["face"][1] - std.drawer_box_clear:
                # an Auto box held down by a Top Front / Top Rear band
                out.append(Issue(CRITICAL, str(c.number),
                                 f"drawer {u['n']}: the support band across the top leaves "
                                 f"room for a box of only {bh} (Auto) — lower than its "
                                 f"{rr.height:g} mm runner ({rr.name or 'runner'}). Lower the "
                                 f"offset or drop the support", check="drawer-runner-height"))
            elif d.box_height is None and not d.inner:
                # an Auto box is the tallest its face takes: the FACE is short
                out.append(Issue(CRITICAL, str(c.number),
                                 f"drawer {u['n']}: its face is too short for the "
                                 f"{rr.height:g} mm runner ({rr.name or 'runner'}) — at an "
                                 f"offset of {u['offset']} the tallest box it takes (Auto) is "
                                 f"{bh}. The face needs to be at least "
                                 f"{u['offset'] + math.ceil(rr.height) + std.drawer_box_clear}, "
                                 f"or the offset lower", check="drawer-runner-height"))
            else:
                out.append(Issue(CRITICAL, str(c.number),
                                 f"drawer {u['n']}: box {bh} is lower than its "
                                 f"{rr.height:g} mm runner ({rr.name or 'runner'}) — the "
                                 f"runner cannot be fixed to it", check="drawer-runner-height"))
    return out


def _inner_drawers(job: Job):
    """Inner drawers — behind the door, faces the size of their boxes (28
    September 2026). What only they can get wrong:

    * CRITICAL `drawer-inner-no-door`: inner drawers on a cabinet with no door —
      there is nothing for them to sit behind;
    * CRITICAL `drawer-inner-mixed`: inner and outer drawers on one cabinet —
      ruled all one or the other (Rudolf: "it's either all internal or
      external"); two carcasses one over the other is how both are built;
    * CRITICAL `drawer-inner-range`: an inner drawer whose runner would stand
      below the bottom panel, or whose box would rise into the top — its typed
      height puts it outside the carcass it hangs in.
    """
    from .room import drawer_layout, drawer_rise, geometry
    out = []
    for c in job.cabinets:
        if c.is_panel or not c.inner_drawers:
            continue
        if not c.door_count:
            out.append(Issue(CRITICAL, str(c.number),
                             f"{len(c.inner_drawers)} inner drawer"
                             f"{'s' if len(c.inner_drawers) > 1 else ''} but no door to sit "
                             f"behind — tick Has doors, or make them outer drawers",
                             check="drawer-inner-no-door"))
        if c.outer_drawers:
            out.append(Issue(CRITICAL, str(c.number),
                             "inner and outer drawers on one cabinet — a cabinet's drawers "
                             "are all inner or all outer; build two carcasses one over "
                             "the other for both", check="drawer-inner-mixed"))
        t = job.std.board_t
        lowest = drawer_rise(c, job.std)
        try:
            top = geometry(c, job.std, job.materials).height - t
            lay = drawer_layout(c, job.std, job.materials)
        except ValueError:
            continue                       # no runner fits: runner-depth says so
        for u in lay:
            if not u["inner"]:
                continue
            z0, z1 = u["box"][4], u["box"][5]
            if z0 < lowest:
                out.append(Issue(CRITICAL, str(c.number),
                                 f"inner drawer {u['n']} starts at {z0} — its runner would "
                                 f"stand below the bottom panel; the lowest a box can start "
                                 f"is {lowest}", check="drawer-inner-range"))
            elif z1 > top:
                out.append(Issue(CRITICAL, str(c.number),
                                 f"inner drawer {u['n']} box reaches {z1}, into the top at "
                                 f"{top} — lower it or make the box shallower",
                                 check="drawer-inner-range"))
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
        # An attached panel names a cabinet. One that names nothing the job has
        # — a deleted cabinet, another panel, itself — is cut exactly as it is
        # and simply stands nowhere, so it is a warning that says what to do.
        if spec.attached_to is not None and host_of(job, c) is None:
            named = cabinet_by_number(job, spec.attached_to)
            why = ("which is a panel — a panel hangs off a cabinet, not off another panel"
                   if named is not None and named.is_panel and named.number != c.number
                   else "which the job does not have")
            out.append(Issue(WARNING, where,
                             f"panel is attached to cabinet {spec.attached_to}, {why} — "
                             f"detach it in Panel design, or attach it to another cabinet",
                             check="attached-host"))
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

        # A flat edging string in the job file (carcass_edge, door_edge,
        # drawer_box_edge) is no longer read (28 September 2026), so every one
        # of these is asked of its board.
        wants = [("carcass_edge", c.exterior_board, "pvc",
                  "the fronts of its sides, top, bottom, shelves and dividers")]
        # Drawer box sides and fronts, per drawer (29 September 2026): each is
        # edged in its own box edging board, the exterior board by default.
        # Drawers sharing one board are named together — one problem, one message.
        # The thickness is chosen too since R1 (29 September 2026), PVC by
        # default, so the question is asked per board AND kind.
        by_edge = {}
        for i, d in enumerate(c.drawer_list, start=1):
            by_edge.setdefault((c.box_edge_board_of(d), c.box_edge_kind_of(d)),
                               []).append(i)
        for (board, kind), nums in by_edge.items():
            which = (f"drawer {nums[0]}" if len(nums) == 1 else
                     f"drawers {', '.join(map(str, nums))}")
            wants.append(("drawer_box_edge", board, kind,
                          f"{which} box sides and fronts (Box edging)"))
        if c.door_count or c.exposed_sides:
            wants.append(("door_edge",
                          c.door_edge_board or c.exterior_board,
                          c.door_edge_kind or c.exterior_tape,
                          "its doors and exposed panels"))
        if c.drawer_list:
            wants.append(("drawer_face_edge",
                          c.drawer_edge_board or c.door_edge_board or c.exterior_board,
                          c.drawer_edge_kind or c.door_edge_kind or c.exterior_tape,
                          "its drawer faces"))
        # The blind panel names its own board and its own thickness, so it is
        # asked the same question as everything else: does that board sell that
        # edging. Its one banded edge is the one reached past every time the
        # cupboard is opened, so going out unedged in silence is not an option.
        if c.corner_kind == "blind" and c.blind_width:
            wants.append(("blind_edge", c.blind_panel_board,
                          c.blind_edge_thickness, "its blind panel"))
        for field, board, thickness, bands in wants:
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
                                 f"{bands} — give the board an Edging Name in the "
                                 f"library, or choose another board here"))
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
        if c.drawer_list:
            for attr, what in (("drawer_carcass_board", "drawers' box board"),
                               ("drawer_face_board", "drawers' face board")):
                if getattr(c, attr):
                    wants.append((getattr(c, attr), what))
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


def _support_layout(job: Job):
    """Typed support rows that cannot stand where their type puts them
    (agreed 27 September 2026). Legacy rows are cut and placed as they always
    were and raise nothing here — this is about the new form only.

    * CRITICAL: a drawer box reaching into the 16 mm band under a Front or a
      Top Rear (its top above H - t) — the rail and the box want the same
      space, and the drawer will not close;
    * CRITICAL: a Front and a Top Rear overlapping in depth — with a backing
      the carcass needs D >= 219, without one D >= 200;
    * CRITICAL: Back supports that do not fit between Back 1 and the bottom
      panel;
    * WARNING: a Front or a Top Rear stored on a carcass that has a top panel,
      which cuts nothing (the row stays in the file, as an unticked box does).
    """
    from .room import back_supports_fit, drawer_box_tops, support_layout
    from .model import SUPPORT_TYPE_LABEL
    std = job.std
    out = []
    for c in job.cabinets:
        if c.is_panel or c.template == "none" or not c.supports_typed:
            continue
        offered = c.support_types_offered
        for row in c.support_rows:
            if row.qty > 0 and row.type not in offered:
                out.append(Issue(WARNING, str(c.number),
                                 f"a {SUPPORT_TYPE_LABEL.get(row.type, row.type)} support "
                                 f"is stored, but this carcass has a top panel and takes "
                                 f"Back supports only — it is not cut. Untick it, or make "
                                 f"the cabinet a base unit", check="support-type-off"))
        lay = support_layout(c, std, job.materials)
        if not lay:
            continue
        flats = [u for u in lay if u["type"] in ("front", "top_rear")]
        if flats:
            band = std.board_t
            under = max(u["z1"] for u in flats) - band
            clear = std.drawer_box_clear
            names = " / ".join(sorted({SUPPORT_TYPE_LABEL[u["type"]] for u in flats}))
            # at least drawer_box_clear under the band, as under a face top
            # (29 September 2026)
            for i, top in drawer_box_tops(c, std, job.materials):
                if top > under - clear:
                    where = (f"into the {band} mm band under the {names} support at {under}"
                             if top > under else
                             f"within {clear} mm of the {names} support's underside at {under}")
                    out.append(Issue(CRITICAL, str(c.number),
                                     f"drawer {i} box reaches {top} up the carcass, {where}. "
                                     f"Lower the box side (the tallest is Auto) or drop the support",
                                     check="support-drawer-foul"))
            front = [u for u in flats if u["type"] == "front"]
            rear = [u for u in flats if u["type"] == "top_rear"]
            if front and rear and front[0]["y1"] > rear[0]["y0"]:
                need = front[0]["y1"] + (rear[0]["y1"] - rear[0]["y0"]) + (
                    std.back_cavity + std.back_t if c.back != "none" else 0)
                out.append(Issue(CRITICAL, str(c.number),
                                 f"the Top Front and Top Rear supports overlap in depth — "
                                 f"the Top Rear starts {rear[0]['y0']} from the front and "
                                 f"the Top Front ends at {front[0]['y1']}. The carcass needs "
                                 f"D >= {need} for both; drop one, or deepen it",
                                 check="support-depth-overlap"))
        need, have = back_supports_fit(c, std, job.materials)
        if need > have:
            out.append(Issue(CRITICAL, str(c.number),
                             f"the Back supports need {need} of height between Back 1 and "
                             f"the bottom panel and there is {have}. Fewer Backs, or a "
                             f"taller carcass", check="support-back-fit"))
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
        elif getattr(w, "drawn", False):
            # A length off a mouse sketch (29 September 2026) is not a site
            # figure, and a cut list never goes out on one.
            out.append(Issue(CRITICAL, f"wall {w.id}",
                             f"wall {w.id}: drawn, not measured — type its length, or tick "
                             f"it as measured", check="wall-drawn"))

    ids = [w.id for w in rm.walls]
    dupes = sorted({i for i in ids if ids.count(i) > 1})
    for i in dupes:
        out.append(Issue(CRITICAL, f"wall {i}", "two walls share this id", check="wall-id-unique"))
    if dupes:
        return out          # every record names a wall by id; nothing below can be trusted

    # A chain that NEARLY closes and misses (2 October 2026): the walls are
    # positioned, so a miss within `closure_block` is measurements that
    # disagree; a bigger miss is simply an open run, and nothing is said.
    err = closure_error(rm, std)
    if err > std.closure_block:
        out.append(Issue(CRITICAL, rm.name,
                         f"walls miss closing by {err} mm — the measurements "
                         f"contradict each other, remeasure before placing anything", check="room-closure"))
    elif err > std.closure_warn:
        out.append(Issue(WARNING, rm.name, f"walls miss closing by {err} mm", check="room-closure"))

    # Walls that cross each other in plan cannot be built as drawn. Meeting at
    # an end, or an end on another wall (a T-wall), is legal geometry. Not
    # asked while a wall has no length: that is its own critical.
    unmeasured = any(w.length <= 0 for w in rm.walls)
    for a, b in ([] if unmeasured else crossing_walls(rm)):
        out.append(Issue(CRITICAL, f"{a}/{b}",
                         f"walls {a} and {b} cross each other in plan — check the corner "
                         f"angles and the lengths", check="room-self-intersect"))

    # Wall height (2 October 2026): an opening cannot be taller than its wall;
    # a cabinet reaching above a wall lower than the ceiling is a warning — a
    # tall unit can stand against a half wall.
    for wid, kind, head, h in low_openings(rm):
        out.append(Issue(CRITICAL, f"wall {wid}",
                         f"wall {wid}: the {kind}'s head at {head} is above the wall, "
                         f"which is {h} high", check="opening-height"))
    for number, top, h, wid in above_wall(job, std):
        out.append(Issue(WARNING, str(number),
                         f"reaches {top}, above wall {wid}, which is {h} high",
                         check="above-wall"))

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
        # A mitre or a blind unit only at a nominal 90-degree inside corner
        # (ruling 4, 29 September 2026). In any other corner its construction
        # has not been ruled: a critical, and no shadow is cast there — so the
        # "not standing in a corner" warning below is not said as well.
        k = unit_corner(rm, cab, p, std) if cab.corner_on else None
        if (k is not None and cab.corner_kind in ("mitre", "blind")
                and corner_angle(rm, k, std) != 90):
            out.append(Issue(CRITICAL, str(p.cabinet),
                             f"Corner unit at a {corner_angle(rm, k, std):g}° corner: "
                             f"construction not ruled.", check="corner-unit-angle"))
            continue
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
    # An inside corner that is not a nominal 90 (ruled 29 September 2026): no
    # butt, each board ends with its run, and the gap is closed on site.
    for a, b, angle in plinth_open_corners(job, std):
        out.append(Issue(WARNING, f"{a}-{b}",
                         f"Plinth at the {a}→{b} {angle:g}° corner: the boards "
                         f"don't meet, cut a closing piece on site", check="plinth-corner"))
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

    def name(n):
        c = by_number.get(n)
        return (f"panel {n} (attached to cabinet {c.attached_to})"
                if c is not None and c.is_attached else f"cabinet {n}")

    for o in room_overlaps(job):
        a, b = by_number.get(o.a), by_number.get(o.b)
        if (a is not None and a.is_panel) or (b is not None and b.is_panel):
            # an attached panel is part of its cabinet's geometry (spec B6), so
            # this is the same critical as the carcass standing there
            out.append(Issue(CRITICAL, f"{o.a}/{o.b}",
                             f"{name(o.a)} and {name(o.b)} overlap by {o.mm} mm on "
                             f"wall {o.wall}", check="overlap"))
            continue
        out.append(Issue(CRITICAL, f"{o.a}/{o.b}",
                         f"cabinets {o.a} and {o.b} overlap by {o.mm} mm on "
                         f"wall {o.wall}", check="overlap"))
    # An attached panel cutting INTO its own carcass — overlapping it, not
    # merely touching — is a warning, never a critical (spec B6): the panel is
    # cut and costed wherever it stands, and how far it laps the carcass is the
    # fitter's business. It is said so the offsets get looked at.
    for n, host in attached_carcass_overlaps(job, std):
        out.append(Issue(WARNING, str(n),
                         f"panel {n} cuts into the carcass of cabinet {host}, which it is "
                         f"attached to — check its offsets in Panel design",
                         check="attached-into-carcass"))
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
    by_number = {c.number: c for c in job.cabinets}
    for number, top, ceiling in above_ceiling(job, std):
        c = by_number.get(number)
        what = (f"top of panel {number}, attached to cabinet {c.attached_to}, is"
                if c is not None and c.is_attached else "top of the carcass is")
        out.append(Issue(CRITICAL, str(number),
                         f"{what} at {top} mm, above the "
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
