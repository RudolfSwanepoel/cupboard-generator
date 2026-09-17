"""Panel generation. One cabinet in, its full panel list out.

Every dimension here comes from Standard. There are no bare numbers in this file
except panel codes and the 100 mm support rail width, which is a fixed detail.
"""
from typing import List

from .model import Cabinet, Job, Panel
from .room import (gaps, plinth_butt_wall, plinth_choice_for, plinth_deduction,
                   plinth_lengths, runs)
from .standard import Standard, STANDARD

SUPPORT_W = 100


def generate_cabinet(cab: Cabinet, std: Standard = STANDARD) -> List[Panel]:
    if cab.template == "none":
        return list(cab.bespoke)          # the job's own panels, exactly as defined

    P: List[Panel] = []
    n = cab.number
    Wi = std.internal_width(cab.width)

    # ---- sides -------------------------------------------------------------
    P.append(Panel(n, "01", "Side", "MEL", cab.height, cab.depth, 2,
                   edge_l=1, edge_material=cab.carcass_edge))

    # ---- top and bottom ----------------------------------------------------
    if cab.kind != "base":
        P.append(Panel(n, "02", "Top", "MEL", Wi, cab.depth, 1,
                       edge_l=1, edge_material=cab.carcass_edge))
    P.append(Panel(n, "03", "Bottom", "MEL", Wi, cab.depth, 1,
                   edge_l=1, edge_material=cab.carcass_edge))

    # ---- support rails -----------------------------------------------------
    plain = cab.supports - cab.edged_supports - cab.white_supports
    if plain > 0:
        P.append(Panel(n, "04", "Support", "MEL", Wi, SUPPORT_W, plain))
    if cab.edged_supports > 0:
        P.append(Panel(n, "04", "Support", "MEL", Wi, SUPPORT_W, cab.edged_supports,
                       edge_l=1, edge_material=cab.carcass_edge))
    if cab.white_supports > 0:
        P.append(Panel(n, "04", "Support", "MEL", Wi, SUPPORT_W, cab.white_supports,
                       edge_l=1, edge_material=cab.drawer_box_edge))

    # ---- shelves -----------------------------------------------------------
    sw = cab.shelf_width or Wi
    if cab.fixed_shelves > 0:
        P.append(Panel(n, "05", "Shelve", "MEL", sw, std.shelf_depth(cab.depth, fixed=True),
                       cab.fixed_shelves, edge_l=1, edge_material=cab.carcass_edge,
                       note="fixed"))
    if cab.shelves > 0:
        P.append(Panel(n, "05", "Shelve", "MEL", sw, std.shelf_depth(cab.depth),
                       cab.shelves, edge_l=1, edge_material=cab.carcass_edge))

    # ---- divider -----------------------------------------------------------
    if cab.divider_count > 0:
        dh = cab.divider_height or (cab.height - 2 * std.board_t)
        P.append(Panel(n, "09", "Divider", "MEL", dh, std.shelf_depth(cab.depth),
                       cab.divider_count, edge_l=1, edge_material=cab.carcass_edge))

    # ---- back --------------------------------------------------------------
    if cab.back != "none":
        bw, bh = std.back_size(cab.width, cab.height, cab.back)
        # house convention: the longer dimension is always Length
        P.append(Panel(n, "06", "Backing", "BACK", max(bw, bh), min(bw, bh), 1))

    # ---- drawers -----------------------------------------------------------
    if cab.drawers:
        runner = std.pick_runner(cab.depth)
        if runner is None:
            raise ValueError(
                f"cabinet {n}: no runner fits a {cab.depth} mm deep box "
                f"(need {min(std.runner_lengths) + std.runner_clearance} mm)")
        front_len = std.drawer_front_length(cab.width)

        # group identical drawers so the cut list stays short
        for key in _dedupe([(d.box_height, d.base) for d in cab.drawers]):
            box_h, base_mat = key
            count = sum(1 for d in cab.drawers if (d.box_height, d.base) == key)
            P.append(Panel(n, "18", "Drawer Side", "MEL", runner, box_h, 2 * count,
                           edge_l=1, edge_material=cab.drawer_box_edge))
            P.append(Panel(n, "19", "Drawer Front", "MEL", front_len, box_h, 2 * count,
                           edge_l=1, edge_material=cab.drawer_box_edge))
            bl, bwid = std.drawer_base(front_len, runner, base_mat)
            P.append(Panel(n, "17", "Drawer Base",
                           "BACK" if base_mat == "board" else "MEL",
                           bl, bwid, count))

        for key in _dedupe([d.face_height for d in cab.drawers]):
            count = sum(1 for d in cab.drawers if d.face_height == key)
            P.append(Panel(n, "20", "Drawer Face", cab.decor,
                           key, cab.width - std.door_single_gap, count,
                           edge_l=2, edge_w=2, edge_material=cab.door_edge, grain=1))

    # ---- doors -------------------------------------------------------------
    if cab.doors > 0:
        h = cab.door_height or (cab.height - std.door_height_gap)
        w = std.door_width(cab.width, cab.doors)
        P.append(Panel(n, "07", "Door", cab.decor, h, w, cab.doors,
                       edge_l=2, edge_w=2, edge_material=cab.door_edge,
                       pot_holes=std.hinges(h), grain=1))

    # ---- exposed end panels ------------------------------------------------
    if cab.exposed_sides > 0:
        P.append(Panel(n, "08", "Exposed Panel", cab.decor,
                       cab.height, cab.depth + std.exposed_extra, cab.exposed_sides,
                       edge_l=1, edge_material=cab.door_edge, grain=1))

    return born_distinct(P, cab.bespoke)


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
        out.append(Panel(0, "11", "Filler", g.decor, g.height, g.filler_width(std), 1,
                         grain=1, note=note))
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
            out.append(Panel(0, "10", "Plinth", "MEL", length, std.leg_height, 1,
                             edge_l=2, edge_material=lead.carcass_edge, note=note))
    return out


def generate_job(job: Job) -> List[Panel]:
    """The cut list. Read-only with respect to the job: it creates panels and
    names them as it creates them, and touches nothing the job already owns —
    not a bespoke panel, not a loose one, not a code. Pinned in check_drag.py."""
    out: List[Panel] = []
    for cab in job.cabinets:
        out.extend(generate_cabinet(cab, job.std))
    out.extend(job.loose)
    # room parts are born here too, so they are named here too: 011a, 011b
    out.extend(born_distinct(room_panels(job) + plinth_panels(job), []))
    return out


def front_stack_check(cab: Cabinet, std: Standard = STANDARD):
    """Door + drawer faces + 2 mm gaps must fill H - 3. Returns (expected, actual, gap)."""
    faces = sum(d.face_height for d in cab.drawers)
    door = 0
    if cab.doors:
        door = cab.door_height or (cab.height - std.door_height_gap)
    n_items = len(cab.drawers) + (1 if cab.doors else 0)
    if n_items == 0:
        return None
    expected = cab.height - std.door_height_gap
    actual = faces + door + std.stack_gap * max(0, n_items - 1)
    return expected, actual, expected - actual
