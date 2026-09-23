"""The 3D scene, built here and only DRAWN in the browser (Part F, 23 Sept 2026).

A drawing, and nothing else. It never feeds a check, a cut-list line, a cost
or a validation: none of `engine`, `validate`, `export_plaza`, `nest`, `room`
or `store` imports this module, and `tools/check_scene.py` fails if one ever
does. It composes what `room.py` already answers — `solid_parts`, the
placement frame, `carcass_z`, the hinge rule, the envelopes, the plinth and
filler positions — into world-space solids the browser extrudes. It works out
no dimension of its own and does no trigonometry: every world point comes
through `room._to_plan` off `room._placed_frame`, or `room.to_world`.

What is in the scene, by ruling (23 September 2026): every board `solid_parts`
draws — sides, top, bottom, fronts, a blind corner's flush panel, a mitre's
construction, independent panels — plus the backing board (`room.back_part`)
and the plinth boards and fillers that were CHOSEN (`room.plinth_solids`,
`room.filler_solids`). Shelves, supports, drawer boxes, legs, hardware,
handles and worktops are left out: their positions are not modelled, and
nothing is guessed onto a drawing. The legend says so (`NOT_DRAWN`).

With no room the cabinets stand side by side on the Run's own layout
(`render.run_layout`) on a plain floor, and the reply carries a banner.
"""
import hashlib
import json
import math
import time
from typing import List, Optional

from . import pictures as PIC
from .engine import generate_cabinet, generate_job, resolved
from .model import Job, Placement, resolve_board, material_thickness
from .render import PICTURE_TILE_MM, Fills, board_look, run_layout
from .room import (Part, _from_plan, _placed_frame, _to_plan, back_part,
                   carcass_z, clashes, corner_points, door_hinges,
                   filler_solids, geometry, layer_of, overlaps, placed,
                   placed_panels, placement_for, plinth_solids,
                   pullout_envelope, solid_parts, swing_envelopes, wall_frames)
from .standard import STANDARD, Standard
from .validate import CRITICAL, validate

# How far the walls rise above the tallest item when the ceiling has not been
# measured. A DRAWING constant, named as one: the view has to stop the walls
# somewhere, and the room has no figure to stop them at. Read by nothing else.
DRAWING_MARGIN = 300

NOT_DRAWN = "Not drawn: shelves, supports, drawer boxes, legs (positions not modelled)."

# A part's role, as `room.Part` names it, to the cut-list role the engine gives
# the same board — which is how each solid is tied to its designation.
ROLE_TO_PANEL = {"side": "Side", "top": "Top", "bottom": "Bottom", "door": "Door",
                 "drawer": "Drawer Face", "blind": "Blind Panel", "panel": "Panel",
                 "back": "Backing", "plinth": "Plinth", "filler": "Filler"}


# --- tying a solid to its cut-list line ----------------------------------------

def _extents(outline, z0, z1):
    """The two FINISHED extents of a board-shaped solid, the thickness dropped.

    A four-point outline is a rectangle, square or turned (a mitre door), so its
    two adjacent edge lengths are its plan extents; anything else — the mitre
    blank — is measured on its bounding box, which is exactly the blank the top
    and bottom are cut from. The third extent is the height. The smallest of
    the three is the board's thickness and is not on the cut list.
    """
    if len(outline) == 4:
        a = math.dist(outline[0], outline[1])
        b = math.dist(outline[1], outline[2])
    else:
        xs = [x for x, _ in outline]
        ys = [y for _, y in outline]
        a, b = max(xs) - min(xs), max(ys) - min(ys)
    three = sorted([a, b, z1 - z0])
    return {int(round(three[1])), int(round(three[2]))}


def _line_for(role: str, board: str, extents: set, panels, mats) -> Optional[str]:
    """The designation of the cut-list line this solid is, or None."""
    want = ROLE_TO_PANEL.get(role)
    if want is None:
        return None
    mine = resolve_board(mats, board)
    for p in panels:
        if p.role != want or resolve_board(mats, p.material) != mine:
            continue
        if {p.length, p.width} == extents:
            return p.label
    return None


# --- one cabinet or panel ----------------------------------------------------

def _grain_vector(axis: Optional[str], frame) -> Optional[list]:
    """A part's grain as a world unit vector — the cabinet frame's axis turned
    onto the wall — or None where the part says nothing about it."""
    if axis is None:
        return None
    (_o, (dx, dy), (nx, ny)) = frame
    if axis == "x":
        return [round(dx, 6), round(dy, 6), 0.0]
    if axis == "y":
        return [round(nx, 6), round(ny, 6), 0.0]
    return [0.0, 0.0, 1.0]


def _rounded(pts):
    return [[round(x, 1), round(y, 1)] for x, y in pts]


def _parts_for(job: Job, cab, p, frame, z: int, std: Standard, mats: dict) -> List[dict]:
    """Every solid of one cabinet or panel, in world plan coordinates."""
    g = geometry(cab, std, mats)
    parts = list(solid_parts(cab, std, mats))
    back = back_part(cab, std, mats)
    if back is not None:
        parts.append(back)
    panels = generate_cabinet(cab, std, mats) if not cab.is_panel else \
        [generate_cabinet(cab, std, mats)[0]]
    hinges = door_hinges(cab, g, p) if g.door_widths and not cab.is_panel else []
    (_o, (dx, dy), (nx, ny)) = frame
    layer = "panels" if cab.is_panel else layer_of(cab, p)
    footprint_only = cab.template == "none" or cab.corner_kind == "ell"
    counters: dict = {}
    out = []
    for q in parts:
        n = counters.get(q.role, 0)
        counters[q.role] = n + 1
        world = [_to_plan(frame, v) for v in q.outline]
        ext = _extents(q.outline, q.z0, q.z1)
        if q.role == "carcass":
            line, reason = None, ("footprint only — bespoke" if cab.template == "none"
                                  else "footprint only — ell" if cab.corner_kind == "ell"
                                  else "footprint only")
        else:
            line = _line_for(q.role, q.board, ext, panels, mats)
            reason = "" if line else "not matched"
        d = {"id": f"{cab.number}:{q.role}:{n}", "cab": cab.number, "role": q.role,
             "index": q.index, "board": resolve_board(mats, q.board),
             "outline": _rounded(world), "z0": round(z + q.z0, 1), "z1": round(z + q.z1, 1),
             "grain": _grain_vector(q.grain, frame), "line": line, "reason": reason,
             "layer": layer, "label": q.label, "hinge": None, "pull": None}
        if q.role == "door" and 0 <= q.index < len(hinges):
            (hx, hy), _a0, sign, _w = hinges[q.index]
            X, Y = _to_plan(frame, (hx, hy))
            d["hinge"] = {"axis": [[round(X, 1), round(Y, 1), d["z0"]],
                                   [round(X, 1), round(Y, 1), d["z1"]]],
                          "angle": sign * std.door_open_deg}
        if q.role == "drawer" and g.runner:
            d["pull"] = {"dir": [round(nx, 6), round(ny, 6), 0.0], "distance": g.runner}
        out.append(d)
    return out


def _dims(g) -> dict:
    return {"width": g.width, "height": g.height, "depth": g.depth, "source": g.source}


def _hash(parts) -> str:
    return hashlib.sha1(json.dumps(parts, sort_keys=True).encode()).hexdigest()[:16]


# --- the room shell -----------------------------------------------------------

def _room_payload(job: Job, top: float) -> Optional[dict]:
    rm = job.room
    if rm is None:
        return None
    frames = wall_frames(rm)
    corners = corner_points(rm)
    walls = []
    for i, w in enumerate(rm.walls):
        (sx, sy), (dx, dy), (nx, ny) = frames[w.id]
        ex, ey = sx + dx * w.length, sy + dy * w.length
        walls.append({
            "id": w.id, "length": w.length,
            "start": [round(sx, 1), round(sy, 1)], "end": [round(ex, 1), round(ey, 1)],
            "dir": [round(dx, 6), round(dy, 6)], "normal": [round(nx, 6), round(ny, 6)],
            # each opening's two jambs as world points, and its sill and head
            "openings": [{"kind": o.kind, "x": o.x, "width": o.width, "sill": o.sill,
                          "head": o.head,
                          "p0": [round(sx + dx * o.x, 1), round(sy + dy * o.x, 1)],
                          "p1": [round(sx + dx * (o.x + o.width), 1),
                                 round(sy + dy * (o.x + o.width), 1)]}
                         for o in w.openings],
            # an obstruction's centre on the wall face; `proud` is how far it
            # stands off it — a box when it does, a marker on the face when not
            "obstructions": [{"kind": ob.kind, "x": ob.x, "z": ob.z, "width": ob.width,
                              "height": ob.height, "proud": ob.proud,
                              "centre": [round(sx + dx * ob.x, 1), round(sy + dy * ob.x, 1)]}
                             for ob in w.obstructions],
        })
    return {"name": rm.name, "closed": rm.closed, "ceiling": rm.ceiling,
            "top": round(top, 1),
            "floor": [[round(x, 1), round(y, 1)] for x, y in corners],
            "walls": walls}


# --- overlays: swings, pull-outs, overlaps, issues ------------------------------

def _overlays(job: Job, std: Standard, items_by_number: dict) -> dict:
    rm = job.room
    swings, over, issues = [], [], []
    if rm is not None:
        bad = {(c.cabinet, c.kind) for c in clashes(job, std)}
        for cab, p, _lay in placed(job):
            g = geometry(cab, std, job.materials)
            z0 = carcass_z(cab, p, std)
            z1 = z0 + g.height
            for poly in swing_envelopes(job, cab, p, std):
                swings.append({"cabinet": cab.number, "kind": "door",
                               "outline": _rounded(poly), "z0": z0, "z1": z1,
                               "clash": (cab.number, "door") in bad})
            pull = pullout_envelope(job, cab, p, std)
            if pull:
                swings.append({"cabinet": cab.number, "kind": "drawer",
                               "outline": _rounded(pull), "z0": z0, "z1": z1,
                               "clash": (cab.number, "drawer") in bad})
        over = [{"a": o.a, "b": o.b, "wall": o.wall, "mm": o.mm} for o in overlaps(job, std)]
    numbers = set(items_by_number)
    for i in validate(job, generate_job(job)):
        n = _cabinet_of(i.where, numbers)
        if n is None:
            continue
        issues.append({"cabinet": n, "level": "critical" if i.level == CRITICAL else "warning",
                       "check": i.check, "message": i.message, "ref": i.ref,
                       "accepted": bool(i.accepted)})
    return {"swings": swings, "overlaps": over, "issues": issues}


def _cabinet_of(where: str, numbers: set) -> Optional[int]:
    """Which cabinet an issue's `where` names: the number itself, or the cabinet
    prefix of a panel designation, or the leading number of a longer phrase."""
    s = str(where or "").strip()
    head = s.split(" ")[0]
    if head.isdigit():
        if int(head) in numbers:
            return int(head)
        # a designation: the longest cabinet number it starts with, leaving a code
        for k in range(len(head) - 2, 0, -1):
            if int(head[:k]) in numbers:
                return int(head[:k])
    return None


# --- the scene ----------------------------------------------------------------

def _looks(job: Job) -> dict:
    """One look per board, as `render.board_look` resolves it: the colour, the
    grain, the picture URL where the drawings would draw it (a picture wins
    over the colour on a GRAINED board only — `Fills` rule), and the tile."""
    fills = Fills()
    out = {}
    for bid in job.board_ids:
        look = board_look(job, bid)
        pic = PIC.url_for(look["picture"], base=PIC.ROUTE) if fills.textured(look) else ""
        out[bid] = {"colour": look["colour"], "set": look["set"], "grain": look["grain"],
                    "picture": pic, "tile_mm": PICTURE_TILE_MM, "ink": look["ink"],
                    "thickness": material_thickness(job.materials, bid)}
    return out


def _room_parts(job: Job, std: Standard, mats: dict) -> List[dict]:
    """Plinth boards and fillers that were chosen, tied to their cut-list lines."""
    room_lines = [p for p in generate_job(job) if p.cabinet == 0 and p.role in ("Plinth", "Filler")]
    out = []
    for i, s in enumerate(plinth_solids(job, std)):
        want = f"wall {s['wall']} {s['layer']} run, cabinets {s['cabinets'][0]}-{s['cabinets'][-1]}"
        line = next((p.label for p in room_lines
                     if p.role == "Plinth" and p.length == s["length"] and want in p.note
                     and (s["pieces"] == 1 or f"piece {s['piece'] + 1} of" in p.note)), None)
        out.append({"id": f"plinth:{s['wall']}:{s['first']}:{s['piece']}", "cab": 0,
                    "role": "plinth", "index": s["piece"], "board": resolve_board(mats, s["board"]),
                    "outline": _rounded(s["outline"]), "z0": s["z0"], "z1": s["z1"],
                    "grain": [0.0, 0.0, 0.0], "line": line, "reason": "" if line else "not matched",
                    "layer": "base", "label": "", "hinge": None, "pull": None,
                    "wall": s["wall"], "cabinets": s["cabinets"]})
    for s in filler_solids(job, std):
        want = f"filler, wall {s['wall']} {s['layer']} run"
        line = next((p.label for p in room_lines
                     if p.role == "Filler" and p.length == s["height"] and p.width == s["width"]
                     and p.note.startswith(want)), None)
        out.append({"id": f"filler:{s['wall']}:{s['after']}:{s['before']}", "cab": 0,
                    "role": "filler", "index": -1, "board": resolve_board(mats, s["board"]),
                    "outline": _rounded(s["outline"]), "z0": s["z0"], "z1": s["z1"],
                    "grain": [0.0, 0.0, 1.0], "line": line, "reason": "" if line else "not matched",
                    "layer": s["layer"], "label": "", "hinge": None, "pull": None,
                    "wall": s["wall"]})
    # A plinth board's grain is along its length: the run's direction. Filled in
    # from the outline's first edge, which runs along the wall.
    for d in out:
        if d["role"] == "plinth":
            (x0, y0), (x1, y1) = d["outline"][0], d["outline"][1]
            L = math.hypot(x1 - x0, y1 - y0) or 1.0
            d["grain"] = [round((x1 - x0) / L, 6), round((y1 - y0) / L, 6), 0.0]
    return out


def build(job: Job) -> dict:
    """The whole scene for one job. Read-only with respect to the job."""
    t0 = time.perf_counter()
    std = job.std
    mats = job.materials
    items = []
    tallest = 0.0
    banner = ""
    if job.room is not None:
        frames = {}
        for cab, p, _lay in placed(job):
            frames[cab.number] = (p, _placed_frame(job.room, p))
        for cab, p in placed_panels(job):
            frames[cab.number] = (p, _placed_frame(job.room, p))
        for cab in job.cabinets:
            g = geometry(cab, std, mats)
            entry = {"number": cab.number, "kind": cab.kind, "panel": cab.is_panel,
                     "corner": cab.corner_kind, "template": cab.template,
                     "placed": cab.number in frames, "wall": None,
                     "layer": "panels" if cab.is_panel else layer_of(cab, placement_for(job, cab.number)),
                     "dims": _dims(g), "parts": [], "hash": ""}
            if cab.number in frames:
                p, frame = frames[cab.number]
                z = carcass_z(cab, p, std)
                entry["wall"] = p.wall
                entry["parts"] = _parts_for(job, cab, p, frame, z, std, mats)
                entry["x"] = p.x
                entry["z"] = p.z
                entry["y"] = int(getattr(p, "y", 0) or 0)
                entry["flip"] = bool(p.flip)
            entry["hash"] = _hash(entry["parts"])
            for q in entry["parts"]:
                tallest = max(tallest, q["z1"])
            items.append(entry)
        room_parts = _room_parts(job, std, mats)
    else:
        banner = "This job has no room: the cabinets stand side by side as the Run draws them."
        at = {c.number: x for c, x in run_layout(job)}
        for cab in job.cabinets:
            g = geometry(cab, std, mats)
            entry = {"number": cab.number, "kind": cab.kind, "panel": cab.is_panel,
                     "corner": cab.corner_kind, "template": cab.template,
                     "placed": cab.number in at, "wall": None,
                     "layer": "panels" if cab.is_panel else layer_of(cab),
                     "dims": _dims(g), "parts": [], "hash": ""}
            if cab.number in at:
                # the Run's floor: a placement at that x, standing on the floor
                p = Placement(cabinet=cab.number, wall="", x=at[cab.number], z=0)
                frame = ((float(at[cab.number]), 0.0), (1.0, 0.0), (0.0, 1.0))
                z = carcass_z(cab, p, std)
                entry["parts"] = _parts_for(job, cab, p, frame, z, std, mats)
                entry["x"] = at[cab.number]
            entry["hash"] = _hash(entry["parts"])
            for q in entry["parts"]:
                tallest = max(tallest, q["z1"])
            items.append(entry)
        room_parts = []
    by_number = {it["number"]: it for it in items}
    ceiling = job.room.ceiling if job.room is not None else None
    top = ceiling if ceiling else tallest + DRAWING_MARGIN
    return {
        "ok": True,
        "banner": banner,
        "room": _room_payload(job, top),
        "ceiling_measured": bool(ceiling),
        "looks": _looks(job),
        "items": items,
        "room_parts": room_parts,
        "overlays": _overlays(job, std, by_number),
        "not_drawn": NOT_DRAWN,
        "tolerance": std.snap_tolerance,
        "build_ms": round((time.perf_counter() - t0) * 1000, 1),
    }


def local_outline(job: Job, number: int, outline) -> Optional[list]:
    """A world outline taken back into that cabinet's own frame — for the
    checks, which want to compare what was sent with `room.geometry`."""
    p = placement_for(job, number)
    if p is None or job.room is None:
        return None
    frame = _placed_frame(job.room, p)
    return [_from_plan(frame, q) for q in outline]
