"""Panel generation. One cabinet in, its full panel list out.

Every dimension here comes from Standard. There are no bare numbers in this file
except panel codes and the 100 mm support width, which is a fixed detail.
"""
from dataclasses import replace
from typing import List

from .model import (BLIND_CODE, MATERIALS, PANEL_CODE, Cabinet, Job, Panel,
                    grain_of, resolve_board, tape_for)
from .room import (arm_shelf_depth, arm_shelf_length, blind_door_width,
                   blind_panel_height, gaps, mitre_blank, mitre_legs,
                   mitre_inner_span, plinth_butt_wall, plinth_choice_for,
                   plinth_deduction, plinth_lengths, runs)
from .standard import Standard, STANDARD

SUPPORT_W = 100          # a support spans the internal width at this height


def panel_of(cab: Cabinet, materials: dict = None) -> Panel:
    """One independent panel, as the cut list carries it.

    Derived, never typed. What the operator types is the board, the orientation,
    two finished extents and how many long and short edges are banded; the cut
    list line falls out of that and the Boards record.

    Which extent becomes `Length` is the grain question, and only that:

    * a GRAINED board locks the panel, and `Length` IS the grain direction, so
      the extent the grain runs along is the length whether it is the longer of
      the two or not;
    * a PLAIN board has no direction, so the longer extent is the length and the
      nester is free to turn it.

    `edge_l` counts the edges whose run is `length` and `edge_w` those whose run
    is `width` (Standard.edging_m), which is NOT the same question as long and
    short: a grained panel cut across its length has its long edges running the
    width. So the two are mapped rather than assumed equal.

    Edging is the Boards record's answer and nothing else. A board with no
    edging, or one that does not offer the kind asked for, gives no name - and
    then nothing is banded either, so the panel does not go out asking for an
    edging that does not exist. The validator names it (`_panels`).
    """
    mats = MATERIALS if materials is None else materials
    spec = cab.panel_spec
    board = resolve_board(mats, spec.board)
    grain = grain_of(mats, board)
    a, b = int(spec.a or 0), int(spec.b or 0)
    if grain:
        length, width = (a, b) if spec.grain_along == "a" else (b, a)
    else:
        length, width = max(a, b), min(a, b)

    long_edges, short_edges = int(spec.edge_long or 0), int(spec.edge_short or 0)
    edge_l, edge_w = ((long_edges, short_edges) if length >= width
                      else (short_edges, long_edges))
    tape = tape_for(mats, spec.edge_board or board, spec.edge_kind) \
        if spec.edge_kind else ""
    if not tape:
        edge_l = edge_w = 0
    return Panel(cab.number, PANEL_CODE, "Panel", board, length, width, 1,
                 edge_l=edge_l, edge_w=edge_w, edge_material=tape,
                 grain=grain, note=cab.note)


def mitre_door_width(cab: Cabinet, std: Standard = STANDARD) -> int:
    """How wide a mitre's door leaf is cut.

    Ruled 22 September 2026, and it replaces "the outline face less a gap". The
    door is cut to the INNER SPAN — the line between the two open-face side
    panels' inner front corners, which is the surface its inside face rests on —
    rounded DOWN to the whole millimetre, with no gap deducted. It sits within
    that span rather than overlaying the side edges, because the sides meet it at
    an angle and there is nothing there to overlay.

    Cabinet 7 is the check: its inner span is 472.35, and its door as really cut
    is 472. The outline's own face is 495, which is a different measurement and
    is not what a door is cut to.

    A pair divides the same span, less `door_pair_gap`. `Cabinet.corner_door_width`
    overrides the lot, and is blank on every cabinet that has not been overridden.
    """
    if cab.corner_door_width:
        return int(cab.corner_door_width)
    span = mitre_inner_span(cab, std)
    if not span:
        return 0
    leaves = max(1, cab.door_count)
    if leaves == 1:
        return int(span)
    return int((span - std.door_pair_gap) // leaves)


def mitre_panels(cab: Cabinet, std: Standard = STANDARD,
                 materials: dict = None) -> List[Panel]:
    """A mitre corner unit's panels, off its four measurements and nothing else.

    Ruled 22 September 2026, and it is one construction for tall, base and wall
    alike: a melamine top AND bottom, two melamine open-face sides, and a
    melamine back that is the two wall panels themselves — one wrapping the
    other, exactly as cabinet 7 is built. So:

    * a base mitre DOES get a top. That overrides the standing base rule, for
      corners only, and straight cabinets are untouched. It is what braces the
      box, which is why there is no bracing warning;
    * there is no 3 mm backing board and no groove. `Cabinet.back` is not read;
    * there are no supports. `Cabinet.support_rows` stays in the job file and
      nothing is cut from it (RULES W13);
    * an upper mitre hangs by fixing through its melamine wall panels, so it
      needs no hanging warning either.

    The wall panels are coded as SIDES, as cabinet 7 codes them. Nothing is
    renamed: `born_distinct` gives 01a / 01b / 01c at the moment they are made.

    The two shelf kinds are `Cabinet.arm_shelves` and `Cabinet.mitred_shelves`,
    and a mitre may carry both. `shelves` / `fixed_shelves` are NOT read here: a
    mitre's interior is not a rectangle, so a straight shelf size would be wrong
    in the unsafe direction.
    """
    mats = MATERIALS if materials is None else materials
    blank = mitre_blank(cab, std)
    legs = mitre_legs(cab, std)
    if blank is None or legs is None:
        # The measurements do not describe a box. The validator says so by name;
        # inventing a shape here would put a real panel on a real order.
        return []
    t, n = std.board_t, cab.number
    bl, bw = blank
    carc = resolve_board(mats, cab.carcass_board)
    carc_tape = cab.carcass_tape(mats)
    carc_grain = grain_of(mats, carc)
    P: List[Panel] = []

    def side(width, qty, what):
        P.append(Panel(n, "01", "Side", carc, cab.height, width, qty,
                       edge_l=1, edge_material=carc_tape, grain=carc_grain,
                       note=what))

    # ---- sides: the two open faces, then the two wall panels ---------------
    # The open faces are each the depth of the run that butts onto them, and the
    # wall panels are one board short of one arm and two short of the other,
    # because one wraps the other. Which one wraps is a construction choice, not
    # a consequence of the hand: mirroring the unit mirrors the joint with it, so
    # both hands cut the same two figures. Wall A wraps, as cabinet 7 does it.
    faces = [(int(cab.face_a), "open face, wall-A side"),
             (int(cab.face_b), "open face, wall-B side")]
    if faces[0][0] == faces[1][0]:
        side(faces[0][0], 2, "open faces")
    else:
        for width, what in faces:
            side(width, 1, what)
    side(int(cab.arm_a) - t, 1, "wall A side, wraps the wall B side")
    side(int(cab.arm_b) - 2 * t, 1, "wall B side")

    # ---- top and bottom: the square blank, mitred on site ------------------
    # Plazaboard cut guillotine only, so the mitre never leaves the factory cut:
    # the blank goes out square and the note carries the two legs to mark it by.
    cut = f"mitre on site: legs {legs[0]} along arm A and {legs[1]} along arm B"
    for code, role in (("02", "Top"), ("03", "Bottom")):
        P.append(Panel(n, code, role, carc, bl, bw, 1, edge_l=1,
                       edge_material=carc_tape, grain=carc_grain, note=cut))

    # ---- shelves -----------------------------------------------------------
    if cab.arm_shelves > 0:
        arm = cab.arm_shelf_arm
        length = arm_shelf_length(cab, std, arm)
        depth = arm_shelf_depth(cab, std)
        if length and depth:
            P.append(Panel(n, "05", "Shelve", carc, length, depth, cab.arm_shelves,
                           edge_l=1, edge_material=carc_tape, grain=carc_grain,
                           note=f"arm shelf, along arm {arm.upper()}"))
    if cab.mitred_shelves > 0:
        back = mitre_legs(cab, std, std.mitre_shelf_clear)
        P.append(Panel(n, "05", "Shelve", carc, bl, bw, cab.mitred_shelves,
                       edge_l=1, edge_material=carc_tape, grain=carc_grain,
                       note=(f"mitred shelf, mitre on site: legs {back[0]} along arm A "
                             f"and {back[1]} along arm B, which holds it "
                             f"{std.mitre_shelf_clear} mm clear of the closed door")))

    # ---- door --------------------------------------------------------------
    leaves = cab.door_count
    if leaves > 0:
        h = cab.door_height or (cab.height - std.door_height_gap)
        w = mitre_door_width(cab, std)
        door_tape = cab.door_tape(mats)
        leaf_boards = [resolve_board(mats, cab.door_board(i)) for i in range(leaves)]
        for board in _dedupe(leaf_boards):
            P.append(Panel(n, "07", "Door", board, h, w, leaf_boards.count(board),
                           edge_l=2, edge_w=2, edge_material=door_tape,
                           pot_holes=std.hinges(h), grain=grain_of(mats, board)))
    return P


def generate_cabinet(cab: Cabinet, std: Standard = STANDARD,
                    materials: dict = None) -> List[Panel]:
    """One cabinet in, its full panel list out.

    `materials` is the job's board records, which is where the edge tapes come
    from: a cabinet names two boards and the tapes follow from them unless it
    overrides one. Nothing but the tapes reads it, so a caller that only wants a
    cabinet's geometry — room.geometry, the validator's structure checks — leaves
    it out and gets the house records.
    """
    mats = MATERIALS if materials is None else materials
    # the job's own panels, exactly as defined — only a board id the job knows
    # by its other name is read as that name (see model.resolve_board)
    if cab.is_panel:
        return [panel_of(cab, mats)]
    bespoke = resolved(cab.bespoke, mats)
    if cab.template == "none":
        return bespoke
    # A corner unit is its own construction, not a straight box wearing a
    # different outline. Before this branch existed, ticking Corner unit on a
    # template cabinet reshaped the plan and changed not one line of the cut
    # list — the box still came out W x D square.
    #
    # A BLIND corner is deliberately not here: it IS a straight box, so it takes
    # the whole path below unchanged and differs only in its door and its one
    # extra panel (ruled 22 September 2026).
    if cab.corner_kind == "mitre":
        return born_distinct(mitre_panels(cab, std, mats), bespoke)
    if cab.corner_kind == "ell":
        # Rudolf has never built one and the construction is not decided, so
        # nothing is invented: it cuts nothing and the validator raises a
        # critical saying so. An ell with template="none" and its own bespoke
        # panels returns above, exactly as cabinet 7 does.
        return born_distinct([], bespoke)

    def R(board):
        return resolve_board(mats, board)
    P: List[Panel] = []
    n = cab.number
    Wi = std.internal_width(cab.width)
    # the two boards, and the three tapes those boards imply (or the overrides)
    carc, ext, back = R(cab.carcass_board), R(cab.exterior_board), R(cab.back_board)
    carc_tape = cab.carcass_tape(mats)
    door_tape = cab.door_tape(mats)
    face_tape = cab.drawer_face_tape(mats)
    # Grain follows the board, not the panel's job: a Brookhill carcass side runs
    # with the grain exactly as a Brookhill door does, and a white one does not.
    carc_grain = grain_of(mats, carc)
    ext_grain = grain_of(mats, ext)

    # ---- sides -------------------------------------------------------------
    P.append(Panel(n, "01", "Side", carc, cab.height, cab.depth, 2,
                   edge_l=1, edge_material=carc_tape, grain=carc_grain))

    # ---- top and bottom ----------------------------------------------------
    if cab.kind != "base":
        P.append(Panel(n, "02", "Top", carc, Wi, cab.depth, 1,
                       edge_l=1, edge_material=carc_tape, grain=carc_grain))
    P.append(Panel(n, "03", "Bottom", carc, Wi, cab.depth, 1,
                   edge_l=1, edge_material=carc_tape, grain=carc_grain))

    # ---- supports ----------------------------------------------------------
    # One line per row, in row order. `support_list` resolves them, including
    # reading the three legacy numbers on a job that predates the rows. Nothing
    # here subtracts anything from anything.
    for row in cab.support_list:
        tape = cab.support_row_tape(mats, row)
        # The rail is cut from the row's own board (blank = the carcass board,
        # which is what it always was), and its grain is that board's — a support
        # cut from the grained board locks like every other panel off it.
        sup_board = R(cab.support_row_cut_board(row))
        P.append(Panel(n, "04", "Support", sup_board, Wi, SUPPORT_W, row.qty,
                       edge_l=1 if tape else 0, edge_material=tape,
                       grain=grain_of(mats, sup_board)))

    # ---- shelves -----------------------------------------------------------
    sw = cab.shelf_width or Wi
    if cab.fixed_shelves > 0:
        P.append(Panel(n, "05", "Shelve", carc, sw, std.shelf_depth(cab.depth, fixed=True),
                       cab.fixed_shelves, edge_l=1, edge_material=carc_tape,
                       grain=carc_grain, note="fixed"))
    if cab.shelves > 0:
        P.append(Panel(n, "05", "Shelve", carc, sw, std.shelf_depth(cab.depth),
                       cab.shelves, edge_l=1, edge_material=carc_tape,
                       grain=carc_grain))

    # ---- divider -----------------------------------------------------------
    if cab.divider_count > 0:
        dh = cab.divider_height or (cab.height - 2 * std.board_t)
        P.append(Panel(n, "09", "Divider", carc, dh, std.shelf_depth(cab.depth),
                       cab.divider_count, edge_l=1, edge_material=carc_tape,
                       grain=carc_grain))

    # ---- back --------------------------------------------------------------
    if cab.back != "none":
        bw, bh = std.back_size(cab.width, cab.height, cab.back)
        # house convention: the longer dimension is always Length
        P.append(Panel(n, "06", "Backing", back, max(bw, bh), min(bw, bh), 1,
                       grain=grain_of(mats, back)))

    # ---- drawers -----------------------------------------------------------
    # cab.drawer_list, never cab.drawers: with "Has drawers" unticked the stack
    # stays in the job file and nothing is built from it.
    stack = cab.drawer_list
    if stack:
        runner = std.pick_runner(cab.depth)
        if runner is None:
            raise ValueError(
                f"cabinet {n}: no runner fits a {cab.depth} mm deep box "
                f"(need {min(std.runner_lengths) + std.runner_clearance} mm)")
        front_len = std.drawer_front_length(cab.width)
        # The box is a board of its own and so is the face. Both default to the
        # cabinet's — box from the carcass, face from the exterior — so a job
        # written before they could be chosen cuts exactly what it was quoted.
        # Each drawer may name its own box and face board (a stack with one drawer
        # in a different finish); with none named it is the cabinet's, as above.
        def box_of(d):
            return R(cab.box_board_of(d))

        def face_of(d):
            return R(cab.face_board_of(d))

        # group identical drawers so the cut list stays short — the board is part
        # of what makes two drawers identical
        for key in _dedupe([(d.box_height, d.base, box_of(d)) for d in stack]):
            box_h, base_mat, box_board = key
            group = [d for d in stack if (d.box_height, d.base, box_of(d)) == key]
            count = len(group)
            row_tape = cab.drawer_box_tape_of(mats, group[0])
            box_grain = grain_of(mats, box_board)
            P.append(Panel(n, "18", "Drawer Side", box_board, runner, box_h, 2 * count,
                           edge_l=1, edge_material=row_tape, grain=box_grain))
            P.append(Panel(n, "19", "Drawer Front", box_board, front_len, box_h, 2 * count,
                           edge_l=1, edge_material=row_tape, grain=box_grain))
            bl, bwid = std.drawer_base(front_len, runner, base_mat)
            # a grooved base is the same thin sheet as the back; a housed one is
            # 16 mm, cut from the drawer box's own board
            base_board = back if base_mat == "board" else box_board
            P.append(Panel(n, "17", "Drawer Base", base_board, bl, bwid, count,
                           grain=grain_of(mats, base_board)))

        for key in _dedupe([(d.face_height, face_of(d)) for d in stack]):
            face_h, face_board = key
            count = sum(1 for d in stack if (d.face_height, face_of(d)) == key)
            P.append(Panel(n, "20", "Drawer Face", face_board,
                           face_h, cab.width - std.door_single_gap, count,
                           edge_l=2, edge_w=2, edge_material=face_tape,
                           grain=grain_of(mats, face_board)))

    # ---- doors -------------------------------------------------------------
    # cab.door_count, never cab.doors: with "Has doors" unticked the count stays
    # in the job file and nothing is built from it.
    #
    # A blind corner is the one exception, and it is a ruling rather than a
    # convenience (22 September 2026): it has exactly one door, at the far end
    # from the corner, and that door is cut to the opening the blind panel
    # leaves — W - B - door_single_gap — not to the carcass width. Its own
    # `doors` count stays in the job file and is not read.
    blind = cab.corner_kind == "blind"
    leaves = 1 if blind else cab.door_count
    # A blind unit with no blind panel width typed yet has no opening to cut a
    # door into. The validator names it; a zero-width door does not reach a saw.
    w = 0 if leaves <= 0 else (
        (blind_door_width(cab, std) or 0) if blind
        else std.door_width(cab.width, leaves))
    if w > 0:
        h = cab.door_height or (cab.height - std.door_height_gap)
        # One line per board the leaves are cut from, in leaf order. Where they
        # all take the same board — the usual case — that is one line of qty
        # `leaves`, exactly as it always was. Where two differ, born_distinct
        # gives each its own designation because the material is part of the
        # signature it reads.
        leaf_boards = [R(cab.door_board(i)) for i in range(leaves)]
        for board in _dedupe(leaf_boards):
            count = leaf_boards.count(board)
            P.append(Panel(n, "07", "Door", board, h, w, count,
                           edge_l=2, edge_w=2, edge_material=door_tape,
                           pot_holes=std.hinges(h), grain=grain_of(mats, board)))

    # ---- the blind corner's flush panel -------------------------------------
    # INSIDE the carcass at the corner end, between the corner-end side panel and
    # the opening, with its face flush with the carcass front edges so the unit
    # reads as one flush front (ruled 22 September 2026, replacing a panel that
    # stood across the corner end at door height). So it runs between the top and
    # the bottom — `blind_panel_height`, H - 2t — and is exactly B wide: the
    # board size is the board size. The door in front of it is an ordinary
    # overlay door and did not move.
    #
    # Its own board (blank = the exterior board, so the strip the door does not
    # cover matches the doors) and its own edging thickness, on ONE long edge:
    # the vertical edge facing the opening, which is the one seen and rubbed
    # when the door is open. Grain runs up the height, as on a door, which is
    # why that edge is a LONG one. It is fixed, so it takes no pot holes. Code 08
    # with the role "Blind Panel" (Q3) — see model.BLIND_CODE for why it is not a
    # code of its own.
    if blind and cab.blind_width:
        blind_board = R(cab.blind_panel_board)
        P.append(Panel(n, BLIND_CODE, "Blind Panel", blind_board,
                       blind_panel_height(cab, std) or 0,
                       int(cab.blind_width), 1,
                       edge_l=1, edge_w=0, edge_material=cab.blind_tape(mats),
                       grain=grain_of(mats, blind_board)))

    # ---- exposed end panels ------------------------------------------------
    if cab.exposed_sides > 0:
        P.append(Panel(n, "08", "Exposed Panel", ext,
                       cab.height, cab.depth + std.exposed_extra, cab.exposed_sides,
                       edge_l=1, edge_material=door_tape, grain=ext_grain))

    return born_distinct(P, bespoke)


def resolved(panels: List[Panel], materials: dict) -> List[Panel]:
    """The job's own panels with each board id as this job carries it.

    A panel whose id already resolves to itself is returned as the very same
    object; only one naming a board by its other id (DECOR for BROOKHILL, or the
    other way) comes back as a copy with that one field changed. The job is never
    touched and no designation moves.
    """
    out = []
    for p in panels:
        mat = resolve_board(materials, p.material)
        out.append(p if mat == p.material else replace(p, material=mat))
    return out


def born_distinct(generated: List[Panel], bespoke: List[Panel]) -> List[Panel]:
    """Give generated panels distinct designations where one code covers several
    sizes (D13: 105a, 105b), taking the cabinet's bespoke panels into account so
    nothing generated lands on a designation a bespoke panel already carries.

    Designations are assigned here, at the moment the panels come into being,
    and never afterwards. The bespoke panels are the job's own and are returned
    exactly as they are — a bespoke cabinet with two sides of different sizes
    carries distinct designations from the day it is defined, and the validator
    says so if it does not.
    """
    sigs: dict = {}
    for p in generated + list(bespoke):
        group = sigs.setdefault(p.label, [])
        sig = (p.material, p.length, p.width)
        if sig not in group:
            group.append(sig)
    out = []
    for p in generated:
        group = sigs[p.label]
        if len(group) > 1:
            idx = group.index((p.material, p.length, p.width))
            p.code = p.code + chr(ord("a") + idx)      # p is new: this names it, it renames nothing
        out.append(p)
    return out + list(bespoke)


def _dedupe(seq):
    seen = []
    for x in seq:
        if x not in seen:
            seen.append(x)
    return seen


def room_panels(job: Job) -> List[Panel]:
    """Fillers, for the gaps somebody chose to fill and only those.

    A gap left undecided produces nothing and a validation warning. Filler and
    plinth parts belong to no cabinet, so they carry cabinet 0 and name their run
    in the note, the same way Job.loose already works.

    The panel goes out as a rectangle at the gap's widest point plus the scribe
    allowance. It cannot go out tapered: Plazaboard cut on a beam saw and every
    cut runs edge to edge.
    """
    std = job.std
    out: List[Panel] = []
    for g in gaps(job, std):
        if g.treatment != "filler":
            continue
        note = f"filler, wall {g.wall} {g.layer} run — trim on site"
        if g.taper > std.taper_threshold:
            note += (f"; SCRIBE, gap tapers {g.taper} mm over {g.depth} mm deep "
                     f"({g.nominal} at the wall, {g.front} at the front)")
        out.append(Panel(0, "11", "Filler", g.board, g.height, g.filler_width(std), 1,
                         grain=grain_of(job.materials, g.board), note=note))
    return out


def plinth_panels(job: Job) -> List[Panel]:
    """Plinth boards, for the runs somebody asked for one on.

    Opt-in per run — the operator's choice, whatever the job. The legs are under
    every standing carcass either way; this decides only whether a code-10 board
    is cut to cover them, so it is leg_height wide and changes no height. Carcass
    board, banded on both long edges to seal it against water at floor level —
    the short end cuts are not banded.
    """
    std = job.std
    by_number = {c.number: c for c in job.cabinets}
    out: List[Panel] = []
    for run in runs(job, std):
        if run.z != 0:
            continue                    # a hung run stands on nothing
        choice = plinth_choice_for(job, run)
        if choice is None or not choice.fitted:
            continue
        lead = by_number[run.first]
        pieces = plinth_lengths(job, run, std)
        butts_into = plinth_butt_wall(job, run, std)
        butted = plinth_deduction(job, run, std)
        for i, (length, _at) in enumerate(pieces):
            note = (f"plinth, wall {run.wall} {run.layer} run, "
                    f"cabinets {run.cabinets[0]}-{run.cabinets[-1]}")
            if len(pieces) > 1:
                note += f"; piece {i + 1} of {len(pieces)}, joint at a cabinet division"
            if butts_into and i == 0:
                note += (f"; butts into the wall {butts_into} plinth, "
                         f"{butted} mm off")
            # the board and the tape are the lead cabinet's carcass, not a
            # hardcoded white: a run of Brookhill carcasses gets a Brookhill plinth
            out.append(Panel(0, "10", "Plinth", lead.carcass_board, length,
                             std.leg_height, 1, edge_l=2,
                             edge_material=lead.carcass_tape(job.materials),
                             grain=grain_of(job.materials, lead.carcass_board),
                             note=note))
    return out


def generate_job(job: Job) -> List[Panel]:
    """The cut list. Read-only with respect to the job: it creates panels and
    names them as it creates them, and touches nothing the job already owns —
    not a bespoke panel, not a loose one, not a code. Pinned in check_drag.py."""
    out: List[Panel] = []
    for cab in job.cabinets:
        out.extend(generate_cabinet(cab, job.std, job.materials))
    out.extend(resolved(job.loose, job.materials))
    # room parts are born here too, so they are named here too: 011a, 011b
    out.extend(born_distinct(resolved(room_panels(job) + plinth_panels(job),
                                      job.materials), []))
    return out


def front_stack_check(cab: Cabinet, std: Standard = STANDARD):
    """Door + drawer faces + 2 mm gaps must fill H - 3. Returns (expected, actual, gap)."""
    stack = cab.drawer_list
    faces = sum(d.face_height for d in stack)
    door = 0
    if cab.door_count:
        door = cab.door_height or (cab.height - std.door_height_gap)
    n_items = len(stack) + (1 if cab.door_count else 0)
    if n_items == 0:
        return None
    expected = cab.height - std.door_height_gap
    actual = faces + door + std.stack_gap * max(0, n_items - 1)
    return expected, actual, expected - actual
