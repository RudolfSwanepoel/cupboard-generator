"""Request handlers. Thin — they call cabinetgen and return JSON.

Nothing here decides a dimension. Every number in a response came out of the
engine; this module only moves it from a dataclass into a dict.
"""
import glob
import json
import os
import re
import threading
import time
from dataclasses import asdict, fields as dc_fields, replace
from http.server import BaseHTTPRequestHandler

from cabinetgen import boards as B
from cabinetgen import nest as N
from cabinetgen.drawers import (divide, equal_shares, graduated_shares,
                                opening_for, remainder, split_pair, stack)
from cabinetgen.engine import generate_job, panel_of
from cabinetgen.export_plaza import (effective_price, estimate_cost, summarise,
                                     write_csvs)
from cabinetgen.model import (ALL_KINDS, BOARD_ALIASES, CODES, EXTERIOR_TAPES,
                              MATERIALS, NO_COLOUR, PANEL_CODE,
                              PANEL_ORIENTATIONS, PanelSpec, Placement,
                              SUPPORT_EDGES,
                              grain_of, hinge_side, is_thin, material_board,
                              material_colour, material_has_edging,
                              material_offers, material_price,
                              material_record, material_thickness, tape_for)
from cabinetgen.render import elevation_svg, plan_svg, wall_elevation_svg
from cabinetgen.room import (LAYERS, add_wall, carcass_z, clashes as room_clashes,
                             closure_error, free_x, gaps as room_gaps, geometry,
                             layer_of, overlaps as room_overlaps,
                             panel_clashes as room_panel_clashes, placed_panels,
                             placement_for, plinth_choice_for, plinth_lengths,
                             rectangular, runs as room_runs, snap_points,
                             z_snap_points)
from cabinetgen.standard import STANDARD
from cabinetgen.store import (job_from_dict, job_to_dict, load, next_number,
                              room_from_dict, room_to_dict, save)
from cabinetgen.validate import (ALLOWED_EDGE, BOARD_GUIDELINE, blocking,
                                 validate)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JOBS_DIR = os.path.join(ROOT, "jobs")
OUT_DIR = os.path.join(ROOT, "out")

# nest_job records its winning heuristic in module globals, so one nest at a time.
NEST_LOCK = threading.Lock()


# --- helpers ---------------------------------------------------------------

def _job(payload):
    """Build a fresh Job from the posted dict.

    Fresh every request on purpose: engine.suffix_labels rewrites panel codes in
    place, so a reused Job would grow a second suffix on every compute.
    """
    job = job_from_dict(payload.get("job") or {})
    for cab in job.cabinets:
        # An item whose kind is Panel has a panel record, decided here and not
        # in the browser. Nothing else about the cabinet is touched: switching
        # kind keeps every field, so switching back brings the cupboard with it.
        if cab.is_panel and cab.panel is None:
            cab.panel = PanelSpec()
    return job


def _panel_row(p, std):
    d = asdict(p)
    d["label"] = p.label
    d["edging_m"] = round(p.edging_m(std), 3)
    d["holes_total"] = p.pot_holes * p.qty      # Plazaboard's column is the line total
    return d


def _job_path(name):
    """A .json file inside jobs/ — basename() keeps a posted name from escaping."""
    base = os.path.basename(str(name or "").strip())
    if not base:
        raise ValueError("no job name given")
    if not base.endswith(".json"):
        base += ".json"
    return os.path.join(JOBS_DIR, base)


def _as_spec(v):
    """Drawer spec off the wire: a count, a list of weights, or a list of heights."""
    if isinstance(v, list):
        return [float(x) if float(x) != int(float(x)) else int(x) for x in v]
    return int(v)


# --- endpoints -------------------------------------------------------------

def defaults(payload):
    """Everything the front end would otherwise be tempted to hardcode."""
    return {
        "ok": True,
        "standard": {k: v for k, v in asdict(STANDARD).items()
                     if isinstance(v, (int, float, str))},
        "runner_lengths": list(STANDARD.runner_lengths),
        "codes": CODES,
        "edge_materials": sorted(x for x in ALLOWED_EDGE if x),
        "kinds": ["tall", "upper", "base", "panel"],
        # The three orientations, each said in the words the editor shows and
        # with the two typed extents named for that orientation. The browser
        # labels its fields from this rather than holding its own copy.
        "panel_orientations": [
            {"key": "upright", "name": "Upright, facing the room",
             "a": "Width along the wall", "b": "Height",
             "a_short": "width", "b_short": "height",
             "hint": "a panel standing up and facing into the room, like a door "
                     "leaf or a bulkhead front"},
            {"key": "flat", "name": "Flat (horizontal)",
             "a": "Width along the wall", "b": "Depth out from the wall",
             "a_short": "width", "b_short": "depth",
             "hint": "a panel lying flat, like the underside of a bulkhead or a "
                     "shelf standing on its own"},
            {"key": "end", "name": "Upright, side-on to the wall",
             "a": "Depth out from the wall", "b": "Height",
             "a_short": "depth", "b_short": "height",
             "hint": "a panel standing up but turned side-on, like the end cap "
                     "that closes a bulkhead"},
        ],
        "panel_code": PANEL_CODE,
        "corner_styles": ["", "mitre", "ell"],
        "hinge_sides": ["L", "R"],
        "face_modes": ["share", "fixed"],
        "face_presets": ["equal", "graduated"],
        "backs": ["four", "three", "none"],
        "bases": ["board", "melamine"],
        # the house board records, for a job that has not named its own
        "materials": sorted(MATERIALS),
        "material_records": {k: dict(v) for k, v in MATERIALS.items()},
        "support_edges": list(SUPPORT_EDGES),
        "exterior_tapes": list(EXTERIOR_TAPES),
        "thicknesses": list(B.THICKNESSES),
        "edging_kinds": list(B.TAPE_KINDS),
        "edging_prefix": dict(B.TAPE_PREFIX),
        "no_colour": NO_COLOUR,
        "grains": list(B.GRAINS),
        "board_guideline": BOARD_GUIDELINE,
        "opening_kinds": ["door", "window", "arch"],
        "obstruction_kinds": ["plug", "isolator", "waste", "water", "pipe", "meter"],
        "layers": list(LAYERS),
    }


def _panel_info(job, cab):
    """The panel record, and the cut-list line it produces.

    The line is `engine.panel_of`'s, not one the browser assembles: what it says
    is what will be cut, down to the edging name and which way the grain locks.
    """
    spec = cab.panel_spec
    p = panel_of(cab, job.materials)
    along = "a" if spec.grain_along == "a" else "b"
    return {
        "board": spec.board, "orientation": spec.orientation,
        "a": spec.a, "b": spec.b, "grain_along": along,
        "edge_kind": spec.edge_kind, "edge_board": spec.edge_board,
        "edge_long": spec.edge_long, "edge_short": spec.edge_short,
        # what the engine makes of it
        "line": {"label": p.label, "code": p.code, "role": p.role,
                 "material": p.material, "length": p.length, "width": p.width,
                 "qty": p.qty, "grain": p.grain, "edge_l": p.edge_l,
                 "edge_w": p.edge_w, "edge_material": p.edge_material},
        # which typed extent became the cut list's Length, said in the editor's
        # own words, so the browser never works the grain rule out for itself
        "length_is": along if p.grain else ("a" if spec.a >= spec.b else "b"),
        "thickness": material_thickness(job.materials, spec.board),
    }


def _geometry_info(job, cab, std):
    g = geometry(cab, std, job.materials)
    # One leaf per door panel that was actually cut, so a bespoke or corner unit
    # gets a hinge control too — cab.doors is 0 on those. The side is the engine's
    # own answer, the same one the plan swings from and the elevation draws.
    p = placement_for(job, cab.number)
    flip = bool(p.flip) if p is not None else False
    n = len(g.door_widths)
    return {"width": g.width, "depth": g.depth, "height": g.height,
            "source": g.source, "points": len(g.footprint),
            "footprint": [list(pt) for pt in g.footprint],
            "mitre_deg": g.mitre_deg,               # an output, never an input
            "face_lengths": g.face_lengths,
            "doors": g.door_widths,
            # what the two tickboxes actually resolve to, so the browser reads
            # the state back rather than working the rule out a second time
            "corner_on": cab.corner_on,
            "drawers_on": bool(cab.drawer_list),
            "doors_on": bool(cab.door_count),
            "door_count": cab.door_count,
            # Which board each leaf is cut from, resolved, and which of those was
            # actually chosen rather than inherited from the exterior board.
            "door_boards": [cab.door_board(i) for i in range(n)],
            "door_boards_set": [cab.door_boards[i] if i < len(cab.door_boards) else ""
                                for i in range(n)],
            "drawer_carcass": cab.drawer_carcass,
            "drawer_face": cab.drawer_face,
            "drawer_carcass_set": cab.drawer_carcass_board,
            "drawer_face_set": cab.drawer_face_board,
            # Edging, as the engine resolves it: a thickness, a colour board and
            # the name those two generate. The browser shows these; it builds no
            # tape name of its own.
            "edging": {
                "door": {"kind": cab.door_edge_kind or cab.exterior_tape,
                         "board": cab.door_edge_board or cab.exterior_board,
                         "name": cab.door_tape(job.materials)},
                "drawer": {"kind": (cab.drawer_edge_kind or cab.door_edge_kind
                                    or cab.exterior_tape),
                           "board": (cab.drawer_edge_board or cab.door_edge_board
                                     or cab.exterior_board),
                           "name": cab.drawer_face_tape(job.materials)},
                "carcass": {"name": cab.carcass_tape(job.materials)},
                "drawer_box": {"name": cab.drawer_box_tape(job.materials)},
            },
            # A job file may carry a flat edging name written before the two
            # dropdowns existed. It still wins, so it is reported rather than
            # letting the dropdowns show something the cut list does not say.
            "edge_override": cab.door_edge,
            # The tapes in force and where each came from. Derived values are the
            # engine's answer read back, never worked out in the browser.
            "tapes": cab.tapes(job.materials),
            "exterior_tape": cab.exterior_tape,
            "carcass_thickness": material_thickness(job.materials, cab.carcass_board),
            "exterior_thickness": material_thickness(job.materials, cab.exterior_board),
            "tape_overrides": {"carcass_edge": cab.carcass_edge,
                               "door_edge": cab.door_edge,
                               "drawer_box_edge": cab.drawer_box_edge},
            # Each row as it will be cut: what it is edged in, and the name that
            # produces. Both are the engine's answer — the editor shows them, it
            # does not work them out.
            # EVERY row the editor shows, not just the ones that reach the cut
            # list: a row sitting at qty 0 is still on screen and still has to
            # show the engine's answer, and dropping it here put the editor's
            # rows and this list out of step by one.
            "supports": [{"edge": r.edge, "qty": r.qty,
                          "board": r.board, "kind": r.kind,
                          "cut_board": r.cut_board,
                          # what the row resolves to, so the editor shows the
                          # engine's answer rather than working one out
                          "eff_cut_board": cab.support_row_cut_board(r),
                          "eff_board": cab.support_row_board(job.materials, r),
                          "eff_kind": cab.support_row_kind(r),
                          "name": cab.support_row_tape(job.materials, r),
                          "legacy": not (r.board or r.kind or r.cut_board)}
                         for r in (cab.support_rows or cab.support_list)],
            # the edging each legacy kind of support row gets, off the engine
            "support_edging": {e: cab.support_tape(job.materials, e)
                               for e in SUPPORT_EDGES},
            "support_total": cab.support_total,
            "supports_migrated": not cab.support_rows,
            "hinges": [hinge_side(cab, i, n, flip) for i in range(n)],
            "hinges_set": [cab.door_hinges[i] if i < len(cab.door_hinges) else ""
                           for i in range(n)],
            "opening": opening_for(cab.height,
                                   (cab.door_height or (cab.height - std.door_height_gap))
                                   if cab.door_count else 0, std),
            # An independent panel: what it is, and the line it cuts. Absent on
            # everything else, which is how the editor knows what to show.
            "is_panel": cab.is_panel,
            "panel": _panel_info(job, cab) if cab.is_panel else None}


def _board_payload(job, key):
    """One board as the job holds it: what it is, what it cost, what tape it makes."""
    return {"id": key,
            "board": material_board(job.materials, key),
            "name": material_board(job.materials, key),
            "price": material_price(job.materials, key),
            "thickness": material_thickness(job.materials, key),
            "grain": B.Board(id=key, grain=str(
                (job.materials or {}).get(key, {}).get("grain", "plain"))).grain
            if isinstance((job.materials or {}).get(key), dict) else "plain",
            "pvc": tape_for(job.materials, key, "pvc"),
            "1mm": tape_for(job.materials, key, "1mm"),
            "2mm": tape_for(job.materials, key, "2mm"),
            # what the board offers, how it looks, and whether it is a sheet you
            # can build from — read off the job's copy of the library record, so
            # the dropdowns filter and the drawings colour from the one place a
            # board is described
            "has_edging": material_has_edging(job.materials, key),
            "edging_kinds": list(material_offers(job.materials, key)),
            "colour": material_colour(job.materials, key),
            "colour_set": bool(material_record(job.materials, key).get("colour")),
            "thin": is_thin(job.materials, key),
            "selected": key in job.board_ids}


def used_by(usage, board_id: str) -> list:
    """The saved jobs that use a board — under its own id, or under a former id
    it was renamed from (model.BOARD_ALIASES), named as such. A job quoted as
    DECOR is using BROOKHILL; listing it as unused would let the board be
    deleted out from under it."""
    names = list(usage.used_by.get(board_id, []))
    for old, new in BOARD_ALIASES.items():
        if new == board_id:
            names += [f"{n} (as {old})" for n in usage.used_by.get(old, [])
                      if n not in names]
    return names


def board_list(payload):
    """The library, plus which saved jobs use each board.

    A job that will not parse is reported by name, never skipped: a board shown
    as unused is how one gets edited out from under a real job.
    """
    lib = B.load()
    usage = B.scan_jobs(JOBS_DIR)
    return {"ok": True,
            "boards": [dict(asdict(b), token=b.token,
                            tapes={k: b.tape_name(k) for k in B.TAPE_KINDS},
                            offered=b.offered, shown_colour=b.shown_colour,
                            thin=b.is_thin,
                            used_by=used_by(usage, b.id))
                       for b in lib],
            "unreadable": usage.unreadable,
            "path": os.path.basename(B.LIBRARY)}


def clean_board_id(raw) -> str:
    """An id fit to be a material name.

    It goes on every panel cut from the board, into the Plazaboard CSV and into
    a file name, so it is upper case, letters digits and underscores only, and
    short. Same shaping `boards.next_id` applies to a generated one, applied to a
    typed one — an id is a key, not a description.
    """
    out = "".join(ch for ch in str(raw or "").upper()
                  if ch.isalnum() or ch == "_")
    return out[:12]


def rename_board_in_job(job, old_id: str, new_id: str) -> list:
    """Point everything in one job at a board's new id, and say what moved.

    A job normally keeps its own copy of a board under the id it was selected
    with — that is the price capture, and a saved job is never touched. This is
    for the project open on screen, where the rename is part of the same edit.
    Panel designations are not involved: a panel keeps its name and changes what
    it is cut from.
    """
    moved = []
    if old_id in (job.materials or {}):
        job.materials = {(new_id if k == old_id else k): v
                         for k, v in job.materials.items()}
    job.boards = [new_id if b == old_id else b for b in job.board_ids]
    # Every field a cabinet names a board in comes from `Cabinet.board_refs`,
    # so this and `board_swap` cannot remember different lists.
    for cab in job.cabinets:
        hit = cab.map_board_refs(lambda b: new_id if b == old_id else b)
        if hit:
            moved.append({"cabinet": cab.number, "fields": sorted(set(hit))})
    for p in job.loose:
        if p.material == old_id:
            p.material = new_id
    return moved


def board_save(payload):
    """Add or edit one board in the library, including changing its id.

    The library, and — only when the id changes — the project posted with it. A
    SAVED job keeps its own copy of every board it selected under the id it was
    selected with, so nothing already quoted moves whatever is done here; the
    reply names those jobs so it is never a surprise. The project on screen is
    a live edit, so it comes along.
    """
    lib = B.load()
    d = dict(payload.get("board") or {})
    name = str(d.get("name") or "").strip()
    if not name:
        return {"ok": False, "error": "a board needs a name"}

    old_id = clean_board_id(payload.get("from"))
    board_id = clean_board_id(d.get("id")) or old_id or B.next_id(lib, name)
    if not board_id:
        return {"ok": False, "error": "a board needs an id — it is the material "
                                      "name on every panel cut from it"}
    existing = B.by_id(lib)
    if board_id in existing and board_id != old_id:
        return {"ok": False,
                "error": f"{board_id} is already {existing[board_id].name} in the "
                         f"library — give this one an id of its own"}

    d["id"], d["name"] = board_id, name
    if "colour" in d and str(d.get("colour") or "").strip() and not B.clean_colour(d.get("colour")):
        return {"ok": False, "error": "the colour must be a hex value like #b4835a, "
                                      "or left empty for no colour set"}
    board = B.board_from_dict(d)
    # A board that says it has edging has to say what it is called and what it
    # offers: the edging name is the only thing the tape names are built from,
    # and a board with edging that offers nothing is a contradiction, not a choice.
    #
    # Asked of the Edging Name field itself, not of `board.token`. The token falls
    # back to the board's long name when the field is blank, so a check on the
    # token can never fire — and falling back is exactly what must not happen
    # here: it is what puts "PVC BROOKHILL FUSION CHIP" on an order as an edging
    # name. Ticking Has Edging is the point at which that name has to be said.
    if board.has_edging and not str(d.get("tape") or "").strip():
        return {"ok": False, "error": "Has Edging is ticked, so the board needs an "
                                      "edging name — the name the edging is ordered "
                                      "under, e.g. WHITE"}
    if board.has_edging and not board.edging_kinds:
        return {"ok": False, "error": "Has Edging is ticked, so tick at least one of "
                                      "PVC, 1mm, 2mm — or untick Has Edging"}
    if old_id and old_id in existing:
        lib = [board if b.id == old_id else b for b in lib]     # in place, order kept
    elif board_id in existing:
        lib = [board if b.id == board_id else b for b in lib]
    else:
        lib.append(board)
    B.save(lib)

    out = {"ok": True, "id": board_id, "renamed": bool(old_id and old_id != board_id),
           "from": old_id, "moved": [], "kept_by": [], "refreshed": []}
    job = _job(payload)
    if out["renamed"]:
        out["kept_by"] = B.scan_jobs(JOBS_DIR).used_by.get(old_id, [])
        out["moved"] = rename_board_in_job(job, old_id, board_id)
    # The project on screen follows the library for what a board IS — its name,
    # edging token, thickness, grain and picture — so an edit here shows in the
    # Structure dropdowns, the cut list and the edging names straight away.
    out["refreshed"] = refresh_from_library(job, lib, only={board_id})
    if out["renamed"] or out["refreshed"]:
        out["job"] = job_to_dict(job)
    return out


# What the library decides for a board in the project on screen. Price is not on
# the list: a job keeps the price it was quoted at ("Price capture").
LIVE_FIELDS = ("name", "board", "tape", "thickness", "grain", "picture",
               "has_edging", "edging_kinds", "colour")


def refresh_from_library(job, lib=None, only=None) -> list:
    """Bring the job's copy of each board up to date with the library.

    The library is where a board's details are edited, so the project on screen
    shows them: name, edging token, thickness, grain and picture. The price is
    the one thing kept — what this job was quoted at, or for a job written before
    boards carried a price, what the rate card quoted it at, written down now so
    a new name cannot lose it (the rate card is looked up by name).

    Returns the ids that changed. A board the library does not have is left as
    the job holds it.
    """
    lib = B.by_id(B.load()) if lib is None else (lib if isinstance(lib, dict)
                                                 else B.by_id(lib))
    changed = []
    for key in job.board_ids:
        if (only and key not in only) or key not in lib:
            continue
        held = (job.materials or {}).get(key)
        rec = material_record(job.materials, key)
        fresh = dict(B.to_material(lib[key]), price=effective_price(job, key))
        if isinstance(held, dict) and all(rec.get(f) == fresh.get(f) for f in LIVE_FIELDS):
            continue
        job.materials = dict(job.materials or {})
        job.materials[key] = fresh
        changed.append(key)
    return changed


def board_delete(payload):
    """Remove a board from the library, but never one a saved job is using."""
    board_id = str(payload.get("id") or "")
    usage = B.scan_jobs(JOBS_DIR)
    used = used_by(usage, board_id)
    if used:
        return {"ok": False,
                "error": f"{board_id} is used by {', '.join(used)} — those jobs keep "
                         f"their own copy, but removing it from the library would "
                         f"leave nothing to select it from again"}
    B.save([b for b in B.load() if b.id != board_id])
    return {"ok": True}


def board_select(payload):
    """Select a library board into this project, or take one out.

    Selecting copies the library record into the job. That copy is the price
    capture: what the job was quoted at stays with the job.
    """
    job = _job(payload)
    board_id = str(payload.get("id") or "")
    if payload.get("on"):
        board = B.find(B.load(), board_id)
        if board is None:
            return {"ok": False, "error": f"no board {board_id!r} in the library"}
        job.materials = dict(job.materials or {})
        job.materials[board_id] = B.to_material(board)
        job.boards = [b for b in job.board_ids if b != board_id] + [board_id]
    else:
        # Every field, not just the carcass and exterior: a board used only as a
        # door leaf, a back, a drawer face or an edging colour was being taken
        # out of the project with the cabinet still pointing at it.
        using = []
        for c in job.cabinets:
            where = sorted({label for key, label in c.board_refs() if key == board_id})
            if where:
                using.append((c.number, where))
        if using:
            named = "; ".join(f"cabinet {n} ({', '.join(w)})" for n, w in using)
            return {"ok": False,
                    "error": f"{board_id} is still named by {named} — change those "
                             f"first, or swap the board instead"}
        job.boards = [b for b in job.board_ids if b != board_id]
        job.materials = {k: v for k, v in (job.materials or {}).items() if k != board_id}
    return {"ok": True, "job": job_to_dict(job)}


def _typed_panels(job):
    """Every panel whose material, grain and edging are TYPED, not derived.

    A bespoke cabinet's panels and the job's loose panels. `generate_job` is
    read-only with respect to them — they go onto the cut list exactly as the job
    defines them — so anything that changes what they are cut from has to change
    the rest of the record with it.
    """
    out = list(job.loose or [])
    for cab in job.cabinets:
        out.extend(cab.bespoke or [])
    return out


def _retype_panel(p, materials, old_id, new_id) -> dict:
    """Bring one typed panel's grain and edging into line with its new board.

    Grain is the board's, so it is simply re-read. The edging is matched by
    KIND: if the panel was edged in the old board's PVC, it is now edged in the
    new board's PVC. If the new board does not offer that kind there is no name
    to give, so the edging is cleared — and because the bands are left alone, the
    panel still says it wants edging and the validator raises the EDGING critical
    rather than letting it go out with the board that just left written on it.

    An edging that never matched the old board (a literal somebody typed) is left
    exactly as it is: it was not derived from the old board, so it does not
    follow it.
    """
    moved = {}
    grain = grain_of(materials, new_id)
    if p.grain != grain:
        moved["grain_from"], moved["grain_to"] = p.grain, grain
        p.grain = grain
    if p.edge_material:
        kind = next((k for k in ALL_KINDS
                     if tape_for(materials, old_id, k) == p.edge_material), "")
        if kind:
            fresh = tape_for(materials, new_id, kind)
            if fresh != p.edge_material:
                moved["kind"] = kind
                moved["tape_from"], moved["tape_to"] = p.edge_material, fresh
                p.edge_material = fresh
    return moved


def _grain_change(before_panels, after_panels):
    """Which panels change grain, and which way, with the size and direction.

    Grain is not a detail: `Length` IS the grain direction on a grained board,
    a locked panel cannot be turned by the nester, and W8/D9 was 60 panels going
    out at grain 0 on a woodgrain board with only Plazaboard's counter catching
    it. So a swap says which panels lock and which come free, and what direction
    the grain will run on each — it does not judge whether that direction is the
    right one to look at, which is not something the app can know.
    """
    was = {}
    for p in before_panels:
        was.setdefault((p.label, p.role, p.length, p.width), p.grain)
    out = []
    for p in after_panels:
        key = (p.label, p.role, p.length, p.width)
        if key not in was or was[key] == p.grain:
            continue
        out.append({"label": p.label, "role": p.role,
                    "length": p.length, "width": p.width, "qty": p.qty,
                    "board": p.material,
                    "from": was[key], "to": p.grain,
                    "locked": bool(p.grain),
                    # what the cut list means by it, said out loud
                    "runs": (f"along Length, {p.length} mm" if p.grain
                             else "either way — the nester may turn it")})
    return out


def _rotation_cost(job, before_panels, after_panels, before, after):
    """What the grain change costs on its own, separated from the board price.

    A locked panel cannot be turned, so the nester has fewer layouts to choose
    from and may need another board. Re-nesting the AFTER panels with every grain
    flag cleared says how much of the change is the lock rather than the board.
    """
    freed = [replace(p, grain=0) for p in after_panels]
    unlocked = _totals(job, freed)
    return {"boards_with_lock": after["boards"], "cost_with_lock": after["cost"],
            "boards_if_free": unlocked["boards"], "cost_if_free": unlocked["cost"],
            "cost_of_lock": round(after["cost"] - unlocked["cost"], 2)}


def _moved_by_board(before_panels, after_panels):
    """How many panels each material gained or lost, so the count is checkable."""
    def tally(ps):
        out = {}
        for p in ps:
            out[p.material] = out.get(p.material, 0) + max(p.qty, 0)
        return out
    a, b = tally(before_panels), tally(after_panels)
    return [{"board": m, "before": a.get(m, 0), "after": b.get(m, 0)}
            for m in sorted(set(a) | set(b)) if a.get(m, 0) != b.get(m, 0)]


def board_swap(payload):
    """What changes if this project swaps one board for another — and, on apply,
    the swap itself.

    Nothing is written on a preview. The reply names every cabinet, every panel
    designation whose board changes, and what it does to the board count and the
    cost, so the answer is the engine's before anything moves.
    """
    job = _job(payload)
    old_id, new_id = str(payload.get("from") or ""), str(payload.get("to") or "")
    if old_id not in (job.materials or {}):
        return {"ok": False, "error": f"this project has no board {old_id!r}"}

    before_panels = generate_job(job)
    before = _totals(job, before_panels)
    before_issues = validate(job, before_panels)

    # Read the "before" board and edging off every panel NOW, while it is still
    # true. `engine.resolved` hands back a bespoke or loose panel as the very
    # same object the job holds, so the swap's in-place re-derivation below
    # rewrites these records too — and a diff taken afterwards would compare the
    # new values with themselves and report that nothing moved.
    #
    # Keyed by shape as well as designation: born_distinct lets two support lines
    # share a label when they are the same size, and keying on the label alone
    # would show one of them changing to a blank tape it never had.
    def key(p):
        return (p.label, p.role, p.length, p.width, p.edge_l, p.edge_w, p.qty)

    was = {key(p): (p.material, p.edge_material) for p in before_panels}

    # Swapping onto a board the project ALREADY carries merges the two: after it
    # there is nothing left to say which panels used to be which, so swapping
    # back does not undo it. The caller is told before it writes.
    merged = new_id in (job.materials or {}) and new_id != old_id

    board = B.find(B.load(), new_id)
    if new_id not in (job.materials or {}):
        if board is None:
            return {"ok": False, "error": f"no board {new_id!r} in the library"}
        job.materials = dict(job.materials)
        job.materials[new_id] = B.to_material(board)
        job.boards = [b for b in job.board_ids if b != new_id] + [new_id]

    # EVERY use of the old board moves (ruled 20 September 2026, overriding the
    # earlier choice to leave hand-specified panels alone): every field
    # `board_refs` knows about, every bespoke panel and every loose panel. A
    # board that is being swapped out must not still be named anywhere.
    # Held before anything moves: `map_board_refs` rewrites a bespoke panel's
    # material in place, so afterwards there is no way to tell which ones it was.
    typed = [p for p in _typed_panels(job) if p.material == old_id]

    touched = []
    for cab in job.cabinets:
        fields_hit = cab.map_board_refs(lambda b: new_id if b == old_id else b)
        if fields_hit:
            touched.append({"cabinet": cab.number, "fields": fields_hit})

    # A bespoke or loose panel stores `grain` and `edge_material` as TYPED
    # values, not derived ones — `generate_job` puts them on the cut list exactly
    # as the job defines them. So moving the board alone would leave a woodgrain
    # panel at grain 0, or an edging name belonging to the board that just left.
    # Both are re-derived here, and anything that cannot be is reported rather
    # than carried over.
    retyped, unmapped = [], []
    for p in typed:
        p.material = new_id          # a loose panel; already done for a bespoke one
        moved = _retype_panel(p, job.materials, old_id, new_id)
        if moved:
            retyped.append(dict(moved, label=p.label))
        if (p.edge_l or p.edge_w) and not p.edge_material:
            unmapped.append({"label": p.label, "was": moved.get("tape_from", ""),
                             "kind": moved.get("kind", "")})

    after_panels = generate_job(job)
    after = _totals(job, after_panels)

    panels = [{"label": p.label, "role": p.role,
               "from": was[key(p)][0], "to": p.material,
               "tape_from": was[key(p)][1], "tape_to": p.edge_material}
              for p in after_panels
              if key(p) in was and was[key(p)] != (p.material, p.edge_material)]

    # What the swap does to the validation, not just to the cost. A swap is how
    # Rudolf previews a design, so a grain lock that no longer fits a sheet, an
    # edging kind the new board does not offer, or a thickness that is wrong for
    # the job it landed in has to be visible before anything is written.
    def issue_key(i):
        return (i.level, i.where, i.message, i.ref)

    was_issues = {issue_key(i) for i in before_issues}
    now_issues = validate(job, after_panels)
    fresh = [i for i in now_issues if issue_key(i) not in was_issues]
    gone = [i for i in before_issues
            if issue_key(i) not in {issue_key(x) for x in now_issues}]

    def as_dict(i):
        return {"level": i.level, "where": i.where, "message": i.message, "ref": i.ref}

    out = {"ok": True, "from": old_id, "to": new_id,
           "cabinets": touched, "panels": panels,
           "retyped": retyped, "unmapped": unmapped,
           "merged": merged,
           "new_issues": [as_dict(i) for i in fresh],
           "fixed_issues": [as_dict(i) for i in gone],
           "blocks": any(i.level == "critical" for i in now_issues),
           "moved_by_board": _moved_by_board(before_panels, after_panels),
           "grain": _grain_change(before_panels, after_panels),
           "rotation": _rotation_cost(job, before_panels, after_panels, before, after),
           "before": before, "after": after}
    if payload.get("apply"):
        out["job"] = job_to_dict(job)
    return out


def _totals(job, panels):
    """Board count per material and the cost, off the engine, for a before/after."""
    with NEST_LOCK:
        nested = N.nest_job(N.nestable(panels, job.std), job.std)
        summary = summarise(job, panels, nested)
    return {"boards": {m: v["est_boards"] for m, v in summary["materials"].items()},
            "panels": {m: v["panels"] for m, v in summary["materials"].items()},
            "edging": summary["edging"],
            "cost": estimate_cost(job, summary)["total_incl_vat"]}


def _room_info(job):
    """Closure feedback and the layer census. Every number still from the engine."""
    rm = job.room
    if rm is None:
        return None
    counts = {lay: 0 for lay in LAYERS}
    unplaced = []
    places = {}
    panels = 0
    for cab in job.cabinets:
        p = placement_for(job, cab.number)
        if cab.is_panel:
            # "panels" is a fourth toggle over the three cabinet layers, not one
            # of them: `layer_of` is never asked about a panel. And an UNPLACED
            # panel is not reported — a panel cut and not put anywhere is normal.
            if p is None:
                continue
            panels += 1
            places[str(cab.number)] = {"wall": p.wall, "x": p.x, "z": p.z,
                                       "y": getattr(p, "y", 0) or 0,
                                       "layer": "panel", "override": False}
            continue
        if p is None:
            unplaced.append(cab.number)
            continue
        lay = layer_of(cab, p)          # derived here, never in the browser
        counts[lay] = counts.get(lay, 0) + 1
        places[str(cab.number)] = {"wall": p.wall, "x": p.x, "z": p.z, "y": 0,
                                   "layer": lay, "override": bool(p.layer)}
    return {
        "name": rm.name,
        "walls": [{"id": w.id, "length": w.length} for w in rm.walls],
        "closed": rm.closed,
        "closure_error": closure_error(rm),
        "placed": len(job.placements),
        "layers": counts,
        "panels": panels,
        "unplaced": unplaced,
        "placements": places,
        "gaps": [{"wall": g.wall, "layer": g.layer, "after": g.after,
                  "before": g.before, "width": g.width, "nominal": g.nominal,
                  "front": g.front, "taper": g.taper, "depth": g.depth,
                  "proposal": g.proposal, "treatment": g.treatment,
                  "filler_width": g.filler_width(job.std)}
                 for g in room_gaps(job, job.std)],
        "runs": [_run_info(job, r) for r in room_runs(job, job.std)],
        "overlaps": [{"a": o.a, "b": o.b, "wall": o.wall, "mm": o.mm}
                     for o in room_overlaps(job)],
        "clashes": [{"cabinet": c.cabinet, "kind": c.kind, "against": c.against}
                    for c in room_clashes(job, job.std)],
        "panel_clashes": [{"panel": c.panel, "against": c.against, "wall": c.wall}
                          for c in room_panel_clashes(job, job.std)],
    }


def _run_info(job, r):
    choice = plinth_choice_for(job, r)
    fitted = bool(choice and choice.fitted)
    return {"wall": r.wall, "layer": r.layer, "z": r.z, "first": r.first,
            "cabinets": r.cabinets, "length": r.length,
            "on_floor": r.z == 0, "fitted": fitted,
            "boards": [ln for ln, _ in plinth_lengths(job, r, job.std)] if fitted else []}


def compute(payload):
    """Panels, issues, summary, cost, elevation and nest layouts in one payload."""
    job = _job(payload)
    out = {
        "ok": True, "error": "",
        "name": job.name,
        # The boards this project selected, in selection order, each with the
        # record it was quoted with. The dropdowns offer these and nothing else.
        "boards": job.board_ids,
        "materials": {k: _board_payload(job, k) for k in (job.materials or {})},
        "room": _room_info(job),
        "elevation": elevation_svg(job),
        "panels": [], "issues": [], "blocking": False,
        "summary": {"materials": {}, "edging": {}, "potholes": 0},
        "cost": {"lines": [], "total_incl_vat": 0.0},
        "nest": {}, "rejects": [],
    }

    try:
        panels = generate_job(job)
    except Exception as exc:
        # A cabinet the engine refuses to build — too shallow for any runner, a
        # drawer opening that will not divide. Keep the elevation so the user can
        # see what they were building when it broke.
        out["ok"] = False
        out["error"] = str(exc)
        return out

    issues = validate(job, panels)
    out["issues"] = [asdict(i) for i in issues]
    out["blocking"] = blocking(issues)
    out["panels"] = [_panel_row(p, job.std) for p in panels]
    # what each cabinet actually is, off its panels — the editor shows it beside
    # the declared figures so a bespoke cabinet's label cannot pass for its size
    out["geometry"] = {str(c.number): _geometry_info(job, c, job.std)
                       for c in job.cabinets}

    with NEST_LOCK:
        nested = N.nest_job(N.nestable(panels, job.std), job.std)
        rejects = list(N.NEST_REJECTS)
        choice = dict(N.NEST_CHOICE)
        for mat, sheets in nested.items():
            used = sum(s.used_area for s in sheets)
            area = sum(s.area for s in sheets) or 1
            out["nest"][mat] = {
                "sheets": len(sheets),
                "yield": round(100.0 * used / area, 1),
                "used_m2": round(used / 1e6, 2),
                "area_m2": round(area / 1e6, 2),
                "sort": choice.get(mat, ("", ""))[0],
                "rule": choice.get(mat, ("", ""))[1],
                "detail": [{"panels": len(s.placements), "yield": round(s.yield_pct, 1)}
                           for s in sheets],
                "svg": N.sheets_svg(sheets, mat),
            }
        summary = summarise(job, panels, nested)

    out["rejects"] = [{"label": r[0], "length": r[1], "width": r[2]} for r in rejects]
    out["summary"] = summary
    out["cost"] = estimate_cost(job, summary)
    return out


def drawer_stack(payload):
    """Face heights for a stack. The arithmetic stays in cabinetgen.drawers."""
    height = int(payload["height"])
    door_height = int(payload.get("door_height") or 0)
    boxes = payload.get("boxes")
    boxes = [int(b) for b in boxes] if isinstance(boxes, list) else int(boxes)
    ds = stack(height, _as_spec(payload["spec"]), boxes,
               door_height=door_height, base=payload.get("base") or "board")
    return {
        "ok": True,
        "opening": opening_for(height, door_height),
        "drawers": [asdict(d) for d in ds],
    }


def drawer_solve(payload):
    """Face heights for a stack described row by row — Share or Fixed.

    Every number in the reply is drawers.divide's, including the running total
    and what is left over. The browser shows them; it works none of them out.
    """
    height = int(payload["height"])
    door_height = int(payload.get("door_height") or 0)
    rows = payload.get("rows") or []
    modes = ["fixed" if str(r.get("mode")) == "fixed" else "share" for r in rows]
    values = [float(r.get("value") or 0) for r in rows]
    opening = opening_for(height, door_height)
    heights = divide(opening, modes, values)
    used = sum(heights) + STANDARD.stack_gap * max(len(heights) - 1, 0)
    return {"ok": True, "opening": opening, "heights": heights,
            "used": used, "left": opening - used,
            "share_left": remainder(opening, modes, values),
            "gap": STANDARD.stack_gap}


def drawer_preset(payload):
    """Share numbers for the Equal and Graduated buttons. Both come from
    Standard, so the browser is not the one deciding what 'graduated' means."""
    n = max(int(payload.get("count") or 0), 0)
    which = str(payload.get("preset") or "equal")
    shares = graduated_shares(n) if which == "graduated" else equal_shares(n)
    return {"ok": True, "preset": which, "shares": shares}


def drawer_divider(payload):
    """Where a dragged join between two faces actually lands.

    The browser projects the pointer onto the pair's span, exactly as a plan drag
    projects onto a wall track, and posts the millimetre it reached. The two
    heights come back from drawers.split_pair; the rest of the stack is untouched.
    """
    top, bottom = split_pair(int(payload["top"]), int(payload["bottom"]),
                             int(payload["at"]),
                             int(payload.get("top_box") or 0),
                             int(payload.get("bottom_box") or 0))
    return {"ok": True, "top": top, "bottom": bottom}


def what_if(payload):
    """Which cut-list lines a change to one cabinet would take away.

    Asked before a tickbox is turned off, so nothing leaves the order without
    being named. It answers in designations and never proposes a new one: a
    designation belongs to its panel for good, so a change either leaves a panel
    alone or removes it — it never renames or reuses one.
    """
    job = _job(payload)
    number = int(payload["cabinet"])
    before = {}
    for p in generate_job(job):
        if p.cabinet == number:
            before.setdefault(p.label, p)

    cab = next((c for c in job.cabinets if c.number == number), None)
    if cab is None:
        return {"ok": False, "error": f"no cabinet {number}"}
    for k, v in (payload.get("set") or {}).items():
        # fields only: the resolved properties are read-only by design
        if any(f.name == k for f in dc_fields(cab)):
            setattr(cab, k, v)

    after = {p.label for p in generate_job(job) if p.cabinet == number}
    gone = [before[lab] for lab in before if lab not in after]
    return {"ok": True,
            "removed": [{"label": p.label, "role": p.role, "material": p.material,
                         "length": p.length, "width": p.width, "qty": p.qty}
                        for p in gone],
            "kept": sorted(after)}


def export(payload):
    """Plazaboard CSVs and the sheet layouts. Criticals block it — that is the point."""
    job = _job(payload)
    panels = generate_job(job)
    issues = validate(job, panels)
    if blocking(issues):
        crit = [asdict(i) for i in issues if i.level == "critical"]
        return {"ok": False,
                "error": f"Export blocked by {len(crit)} critical issue(s).",
                "issues": crit}

    job.name = _safe_name(job.name)          # it names files; it must not name paths
    outdir = os.path.join(OUT_DIR, job.name)
    written = write_csvs(job, panels, outdir)
    with NEST_LOCK:
        nested = N.nest_job(N.nestable(panels, job.std), job.std)
        for mat, sheets in nested.items():
            path = os.path.join(outdir, f"nest_{mat}.svg")
            N.write_svg(sheets, path, title=mat)
            written.append(path)

    drawings = [(f"{job.name}_elevation.svg", elevation_svg(job))]
    if job.room is not None:
        # one face-on drawing per wall: the sheet that goes to site with the order
        drawings += [(f"{job.name}_elevation_{_safe_name(w.id)}.svg",
                      wall_elevation_svg(job, w.id)) for w in job.room.walls]
    for name, svg in drawings:
        path = os.path.join(outdir, name)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(svg)
        written.append(path)
    return {"ok": True, "dir": outdir, "files": [os.path.basename(p) for p in written]}


def job_list(payload):
    os.makedirs(JOBS_DIR, exist_ok=True)
    names = sorted(os.path.basename(p) for p in glob.glob(os.path.join(JOBS_DIR, "*.json")))
    return {"ok": True, "jobs": names}


# The jobs the checks run against. Deleting one does not break the repo — it is
# recoverable, and git has it — but it does stop `regen_check` and half the
# `check_*` scripts until it is put back, so it is said plainly before it happens.
FIXTURE_JOBS = ("Test.json", "Test_Build.json")

# Where a deleted job goes. Not unlink: a job is a quote somebody may need back,
# and "I deleted the wrong one" has no undo otherwise.
DELETED_DIR = os.path.join(JOBS_DIR, "_deleted")


def job_delete(payload):
    """Move a saved job out of jobs/, into jobs/_deleted/.

    Never a real delete, and never the job on screen: deleting what is open
    would leave the editor showing a job with nowhere to save it back to.
    """
    name = os.path.basename(str(payload.get("path") or "").strip())
    if not name:
        return {"ok": False, "error": "no job named"}
    path = _job_path(name)
    if not os.path.exists(path):
        return {"ok": False, "error": f"there is no saved job {name!r}"}

    # The job on screen is posted with the request, so this is asked of what is
    # actually open rather than of what the dropdown happens to be showing.
    open_name = os.path.basename(str(payload.get("open") or "").strip())
    if open_name and open_name.lower() == name.lower():
        return {"ok": False,
                "error": f"{name} is the job open here — load or start another one "
                         f"first, then delete it"}

    os.makedirs(DELETED_DIR, exist_ok=True)
    dest = os.path.join(DELETED_DIR, name)
    if os.path.exists(dest):
        stamp = time.strftime("%Y%m%d-%H%M%S")
        dest = os.path.join(DELETED_DIR, f"{name[:-5]}-{stamp}.json")
    os.replace(path, dest)
    return {"ok": True, "path": name,
            "moved_to": os.path.join("jobs", "_deleted", os.path.basename(dest)),
            "fixture": name in FIXTURE_JOBS}


def job_delete_info(payload):
    """What deleting this job would mean, asked before the confirm is shown."""
    name = os.path.basename(str(payload.get("path") or "").strip())
    path = _job_path(name) if name else ""
    open_name = os.path.basename(str(payload.get("open") or "").strip())
    return {"ok": True, "path": name,
            "exists": bool(path) and os.path.exists(path),
            "is_open": bool(open_name) and open_name.lower() == name.lower(),
            "fixture": name in FIXTURE_JOBS}


def job_save(payload):
    job = _job(payload)
    path = _job_path(payload.get("path") or job.name)
    os.makedirs(JOBS_DIR, exist_ok=True)
    save(job, path)
    return {"ok": True, "path": os.path.basename(path)}


def upgrade_former_ids(job) -> list:
    """Open a job under the library's current board ids, where that is safe.

    A board the job names by an id the library has since renamed (DECOR, now
    BROOKHILL) is shown under the new id — but only when the job never captured
    a price for it. A job written before the library carries a bare description
    and no price, so nothing it was quoted with is being overwritten: it was
    always priced off the rate card, and the library record is that same board.
    A job that DID capture a price keeps its own copy under the id it was quoted
    with, exactly as a rename leaves every saved job.

    This moves the project on screen only. The file on disk is not touched until
    somebody saves it, and the reply says what moved so it is never a surprise.
    """
    lib = B.by_id(B.load())
    moved = []
    for old, new in BOARD_ALIASES.items():
        mats = job.materials or {}
        if old not in mats or new in mats or new not in lib:
            continue
        if isinstance(mats[old], dict) and mats[old].get("price"):
            continue                    # a captured price: the quote stays as quoted
        cabs = rename_board_in_job(job, old, new)
        job.materials[new] = B.to_material(lib[new])
        moved.append({"from": old, "to": new, "cabinets": [c["cabinet"] for c in cabs]})
    return moved


def job_load(payload):
    path = _job_path(payload.get("path"))
    if not os.path.exists(path):
        return {"ok": False, "error": f"no job file {os.path.basename(path)}"}
    job = load(path)
    renamed = upgrade_former_ids(job)
    refreshed = refresh_from_library(job)
    return {"ok": True, "job": job_to_dict(job), "renamed": renamed,
            "refreshed": refreshed}


def job_fixture(payload):
    """The October 2025 wardrobe, as JSON. The regression fixture, openable in the UI."""
    from jobs.wardrobe_oct2025 import JOB
    return {"ok": True, "job": job_to_dict(JOB)}


def job_next_number(payload):
    return {"ok": True, "number": next_number(_job(payload))}


def plan(payload):
    """The plan view. Separate from /api/compute so flipping a layer costs a
    redraw and not a whole re-nest."""
    job = _job(payload)
    # "panels" is not one of room.LAYERS — those are the three cabinet layers —
    # so it is allowed through here as the fourth toggle it is, and plan_svg is
    # the only place the word means anything.
    allowed = LAYERS + ("panels",)
    keep = lambda v: tuple(x for x in (v or ()) if x in allowed)   # noqa: E731
    show = keep(payload.get("show")) or allowed
    # Isolate: one item drawn solid whatever the layer toggle says, everything
    # else ghosted, so a cabinet that has landed underneath another one can be
    # got at. An item the job does not carry is simply not isolated — a stale
    # number from a deleted cabinet draws the plan as it always was.
    iso = payload.get("isolate")
    iso = int(iso) if iso not in (None, "") else None
    if iso is not None and not any(c.number == iso for c in job.cabinets):
        iso = None
    return {"ok": True, "isolate": iso,
            "svg": plan_svg(job, show=show, ghost=keep(payload.get("ghost")),
                            isolate=iso)}


def elevation(payload):
    """One wall face on, or the whole job side by side when no wall is named.

    Separate from /api/compute for the same reason as /api/plan: switching which
    wall you are looking at should cost a redraw, not a re-nest.
    """
    job = _job(payload)
    wall = payload.get("wall")
    svg = wall_elevation_svg(job, str(wall)) if wall else elevation_svg(job)
    return {"ok": True, "svg": svg}


def _safe_name(name) -> str:
    """A job or wall name fit to go into a file name inside out/.

    Both come from the job file, and a name like '../x' must not be able to
    write outside the export folder.
    """
    cleaned = re.sub(r"[^A-Za-z0-9_.-]", "_", str(name or "")).strip(".")
    return cleaned or "untitled"


def drag(payload):
    """Everything a drag needs, worked out once when it starts.

    The browser projects the pointer onto a wall track and picks the nearest of
    these snap points. It invents no position of its own, and on drop the whole
    job is recomputed server-side, so what ends up on the cut list is the
    engine's answer and not the interface's.
    """
    job = _job(payload)
    number = int(payload["cabinet"])
    cab = next((c for c in job.cabinets if c.number == number), None)
    if cab is None or job.room is None:
        return {"ok": False, "error": "no such cabinet, or the job has no room"}
    here = placement_for(job, number)
    # A panel's third extent is its board's thickness, so the boards are read:
    # without them a dragged panel would be measured against the house records.
    g = geometry(cab, job.std, job.materials)
    ceiling = job.room.ceiling or 0
    # How far the underside is off the floor when Placement.z is 0. A standing
    # carcass is up on its legs; a hung unit and a PANEL are not. The browser
    # used to work this out from the layer, which would have lifted every panel
    # 100 mm — it reads this figure now and derives nothing.
    lift = carcass_z(cab, Placement(cabinet=number, wall=here.wall if here else "",
                                    x=0, z=0), job.std)
    return {
        "ok": True,
        "cabinet": number,
        "panel": cab.is_panel,
        "width": g.width,                           # its real extent, off the panels
        "height": g.height,
        "depth": g.depth,
        "layer": layer_of(cab, here),
        "leg_lift": lift,
        "tolerance": job.std.snap_tolerance,
        "ceiling": ceiling,
        # How high the underside may go. 0 is the floor, where the carcass stands
        # on its legs; above it is a hung unit's underside. None with no ceiling
        # measured — there is nothing to cap it against, and the ceiling check
        # blocks the export until one is taken.
        "max_z": max(ceiling - g.height, 0) if ceiling else None,
        "walls": {w.id: {"length": w.length,
                         "max_x": max(w.length - g.width, 0),
                         # where it would land if it were newly given this wall,
                         # clear of what is already on it (E8)
                         "free_x": free_x(job, number, w.id, job.std),
                         "snaps": snap_points(job, number, w.id, job.std),
                         # every height, each with the stretch of wall it
                         # applies over — the cabinet crosses several on the way
                         "z_snaps": z_snap_points(job, number, w.id, job.std,
                                                  spans=True)}
                  for w in job.room.walls},
    }


def room_extend(payload):
    """Add a wall at either end of the room's wall sequence — how a straight run
    becomes an L or a U. The length is a starting figure to be measured, like the
    pre-filled room's walls."""
    rm = room_from_dict(payload.get("room") or {})
    add_wall(rm, str(payload.get("at") or "end"), int(payload.get("length") or 3000))
    return {"ok": True, "room": room_to_dict(rm)}


def room_new(payload):
    """A fresh square room to start measuring from. The browser does not invent
    wall lists any more than it invents panel sizes."""
    return {"ok": True, "room": room_to_dict(rectangular(
        int(payload.get("length") or 4000),
        int(payload.get("width") or 3000),
        name=str(payload.get("name") or "room")))}


ROUTES = {
    "/api/defaults": defaults,
    "/api/compute": compute,
    "/api/drawers": drawer_stack,
    "/api/drawer-solve": drawer_solve,
    "/api/drawer-preset": drawer_preset,
    "/api/drawer-divider": drawer_divider,
    "/api/what-if": what_if,
    "/api/boards": board_list,
    "/api/board-save": board_save,
    "/api/board-delete": board_delete,
    "/api/board-select": board_select,
    "/api/board-swap": board_swap,
    "/api/export": export,
    "/api/jobs": job_list,
    "/api/save": job_save,
    "/api/job-delete": job_delete,
    "/api/job-delete-info": job_delete_info,
    "/api/load": job_load,
    "/api/fixture": job_fixture,
    "/api/next-number": job_next_number,
    "/api/room-new": room_new,
    "/api/plan": plan,
    "/api/drag": drag,
    "/api/elevation": elevation,
    "/api/room-extend": room_extend,
}


# --- server ----------------------------------------------------------------

class Handler(BaseHTTPRequestHandler):
    server_version = "CupboardApp"

    def log_message(self, fmt, *args):
        pass

    def _send(self, code, body, ctype):
        if isinstance(body, str):
            body = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, code, obj):
        self._send(code, json.dumps(obj), "application/json; charset=utf-8")

    def do_GET(self):
        path = self.path.split("?", 1)[0]
        if path in ("/", "/index.html"):
            try:
                with open(os.path.join(ROOT, "app", "index.html"), encoding="utf-8") as fh:
                    return self._send(200, fh.read(), "text/html; charset=utf-8")
            except OSError as exc:
                return self._send(500, f"cannot read index.html: {exc}", "text/plain")
        if path in ROUTES:
            return self._dispatch(path, {})
        self._send(404, "not found", "text/plain")

    def do_POST(self):
        path = self.path.split("?", 1)[0]
        if path not in ROUTES:
            return self._send(404, "not found", "text/plain")
        try:
            n = int(self.headers.get("Content-Length") or 0)
            payload = json.loads(self.rfile.read(n) or b"{}")
        except (ValueError, TypeError) as exc:
            return self._json(400, {"ok": False, "error": f"bad request body: {exc}"})
        self._dispatch(path, payload)

    def _dispatch(self, path, payload):
        try:
            self._json(200, ROUTES[path](payload))
        except Exception as exc:
            self._json(200, {"ok": False, "error": f"{type(exc).__name__}: {exc}"})
