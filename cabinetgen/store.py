"""Job files. Plain JSON so they diff, back up and open in a text editor."""
import json
from dataclasses import asdict, fields

from .model import (Acceptance, Cabinet, Drawer, GapChoice, Job, Obstruction, Opening, Panel,
                    PanelSpec, Placement, PlinthChoice, Room, Shelf, Support, Wall)


def _only_known(cls, d: dict) -> dict:
    known = {f.name for f in fields(cls)}
    return {k: v for k, v in d.items() if k in known}


def panel_to_dict(p: Panel) -> dict:
    return asdict(p)


def panel_from_dict(d: dict) -> Panel:
    known = {f.name for f in fields(Panel)}
    return Panel(**{k: v for k, v in d.items() if k in known})


# Cabinet fields added after the job file format had settled. Each is written
# only when it is NOT at its default, so a job saved before it existed reads and
# writes byte for byte — which is what check_panels.py pins on Test.json and
# Test_Build.json, and the same discipline as `panel`, a support row's `board`
# and a placement's `y` below.
#
# A field added to Cabinet and not added here is what makes every job file on
# disk grow a key the next time it is saved.
LATE_CABINET_FIELDS = (
    "corner_hand", "blind_width", "blind_board", "blind_edge_kind",
    "arm_shelves", "arm_shelf_arm", "arm_shelf_depth", "mitred_shelves",
    "corner_door_width", "runner",
    "drawer_box_edge_board", "drawer_box_edge_kind", "drawer_base",
    # the solid back (3 October 2026)
    "solid_back_board", "solid_back_edge_kind", "solid_back_edge_board",
    "solid_back_long", "solid_back_short",
)


# Drawer fields written only when they are set: None means "follow the
# cabinet" (or the default offset), and a drawer saved before the field existed
# must write back byte for byte.
DRAWER_SET_ONLY = ("offset", "box_edge_board", "box_edge_kind", "base")


# The panel-record fields that say a panel is attached to a cabinet, and where.
# Written only when it is (`attached_to` set); see cabinet_to_dict.
ATTACH_FIELDS = ("attached_to", "at_x", "at_y", "at_z")


def cabinet_to_dict(c: Cabinet) -> dict:
    d = asdict(c)
    defaults = {f.name: f.default for f in fields(Cabinet)}
    for name in LATE_CABINET_FIELDS:
        if d.get(name) == defaults[name]:
            d.pop(name, None)
    # `inner` and `z` only on an inner drawer (28 September 2026), so every
    # drawer written before inner drawers round-trips byte for byte. `offset`,
    # `box_edge_board`, `box_edge_kind` and `base` only when set (None follows
    # the cabinet); `box_height` always, as `null` when it is Auto.
    d["drawers"] = [{k: v for k, v in asdict(x).items()
                     if (x.inner or k not in ("inner", "z"))
                     and (k not in DRAWER_SET_ONLY or v is not None)}
                    for x in c.drawers]
    # `board` and `kind` are written only when a row actually names them, so a
    # job saved before the control round-trips byte for byte and is still read
    # from `edge` — the same discipline as every other field added here.
    # `type` and `edges` (27 September 2026) the same way: a row that has
    # neither is a legacy row and is written exactly as it was read.
    d["support_rows"] = [{k: v for k, v in asdict(x).items()
                          if (v != "" or k not in ("board", "kind", "cut_board", "type"))
                          and (v is not None or k != "edges")}
                         for x in c.support_rows]
    d["bespoke"] = [panel_to_dict(x) for x in c.bespoke]
    # Shelf rows (3 October 2026) only when there are any — a job that never
    # heard of them is byte-identical — and within a row `height` only when
    # typed, `kind` / `board` / `note` only when set.
    if c.shelf_rows:
        d["shelf_rows"] = [{k: v for k, v in asdict(x).items()
                            if (v is not None or k != "height")
                            and (v != "" or k not in ("kind", "board", "note"))}
                           for x in c.shelf_rows]
    else:
        d.pop("shelf_rows", None)
    # Only written when this item actually is a panel, and `anchor` only when it
    # is set — so a job with no panels is byte-identical to one written before
    # they existed. The same discipline as `room` and `placements` above. The
    # attachment (`attached_to` and the three offsets, 28 September 2026) is
    # written only on an attached panel, so a standalone one is byte-identical
    # to one written before panels could be attached.
    if c.panel is None:
        d.pop("panel", None)
    else:
        attached = c.panel.attached_to is not None
        d["panel"] = {k: v for k, v in asdict(c.panel).items()
                      if (k != "anchor" or v is not None)
                      and (k not in ATTACH_FIELDS or attached)}
    return d


def cabinet_from_dict(d: dict) -> Cabinet:
    """A cabinet off the wire, with the two renames a job file may predate.

    `decor` became `exterior_board` when a cabinet gained a carcass board of its
    own, and the three edge tapes became overrides that default to "derive it
    from the boards". A job file written before either still says exactly what it
    always said, so it is read as it always meant: its decor is its exterior
    board, and a tape it states is carried across as the override it now is.
    Nothing is guessed and nothing is dropped — a field silently lost here would
    put a different panel on a real order.
    """
    d = dict(d)
    if "exterior_board" not in d and "decor" in d:
        d["exterior_board"] = d["decor"]
    d["drawers"] = [Drawer(**_only_known(Drawer, x)) for x in d.get("drawers", [])]
    d["support_rows"] = [Support(**_only_known(Support, x))
                         for x in d.get("support_rows", [])]
    d["shelf_rows"] = [Shelf(**_only_known(Shelf, x)) for x in d.get("shelf_rows", [])]
    d["bespoke"] = [panel_from_dict(x) for x in d.get("bespoke", [])]
    d["panel"] = (PanelSpec(**_only_known(PanelSpec, d["panel"]))
                  if isinstance(d.get("panel"), dict) else None)
    known = {f.name for f in fields(Cabinet)}
    return Cabinet(**{k: v for k, v in d.items() if k in known})


def placement_to_dict(p: Placement) -> dict:
    """`y` only when it is non-zero. A cabinet is always against its wall, so
    every placement written before panels could be placed says exactly what it
    always said and the file does not move."""
    d = asdict(p)
    if not d.get("y"):
        d.pop("y", None)
    return d


# Wall fields written only when set (room redo Phase 1, 2 October 2026): a
# height of None is the room ceiling, a thickness of None is
# Standard.wall_thickness, and `drawn` is the mouse-sketch marker.
LATE_WALL_FIELDS = ("height", "thickness", "drawn")

# What a wall record said before walls had positions: a length, the offsets
# and the nominal corner angle, the chain walked from wall A along +X. READ
# for migration (`wall_from_dict` / `room_from_dict`) and never written again.
LEGACY_WALL_FIELDS = ("length", "offset_start", "offset_end", "corner_end")


def wall_to_dict(w: Wall) -> dict:
    d = asdict(w)
    defaults = {f.name: f.default for f in fields(Wall)}
    for name in LATE_WALL_FIELDS:
        if d.get(name) == defaults[name]:
            d.pop(name, None)
    return d


def room_to_dict(room: Room) -> dict:
    d = asdict(room)
    d["walls"] = [wall_to_dict(w) for w in room.walls]
    return d


def wall_from_dict(d: dict) -> Wall:
    """One wall off the wire or the file. A record carrying the old keys and no
    `x0` is read with its points at the origin along +X: `room_from_dict`
    places it, because the old form only means anything as a chain."""
    w = dict(_only_known(Wall, d))
    if "x0" not in d and d.get("length") is not None:
        w.update(x0=0, y0=0, x1=int(d.get("length") or 0), y1=0)
    for k in ("x0", "y0", "x1", "y1"):
        w[k] = int(round(float(w.get(k) or 0)))
    for k in ("height", "thickness"):
        if w.get(k) in ("", 0, None):
            w[k] = None
        else:
            w[k] = int(w[k])
    w["drawn"] = bool(w.get("drawn", False))
    w["openings"] = [Opening(**_only_known(Opening, o)) for o in d.get("openings", [])]
    w["obstructions"] = [Obstruction(**_only_known(Obstruction, o))
                         for o in d.get("obstructions", [])]
    return Wall(**w)


def _legacy_room(d: dict) -> bool:
    walls = d.get("walls") or []
    return any("x0" not in w and w.get("length") is not None for w in walls) \
        or (bool(walls) and all("x0" not in w for w in walls) and "closed" in d)


def room_from_dict(d: dict) -> Room:
    """A room off the wire or the file. A room saved before walls had positions
    — walls as a length and a corner angle, with `closed` on the room — is
    MIGRATED once here (ruling 8, 2 October 2026): the old chain arithmetic
    (`room._legacy_frames`) places every wall, rounded to whole mm, so the room
    is exactly the room it was, wall A still from (0, 0) along +X. Saving then
    writes points, and load -> save -> load is stable."""
    from .room import _legacy_frames
    d = dict(d)
    raw = d.get("walls", [])
    walls = [wall_from_dict(w) for w in raw]
    if _legacy_room(d):
        frames = _legacy_frames(raw, int(d.get("offset_depth") or 600), bool(d.get("closed", True)))
        for w, (_id, (sx, sy), (ex, ey)) in zip(walls, frames):
            w.x0, w.y0, w.x1, w.y1 = (int(round(sx)), int(round(sy)),
                                      int(round(ex)), int(round(ey)))
    d["walls"] = walls
    return Room(**_only_known(Room, d))


def job_to_dict(job: Job) -> dict:
    d = {
        "name": job.name,
        # The boards this project selected, and the records it was quoted with.
        # `board_ids`, not `boards`: a job written before the library implied its
        # selection through `materials`, and saving makes that implication
        # explicit instead of leaving it to be re-derived every time.
        "boards": job.board_ids,
        "materials": job.materials,
        "cabinets": [cabinet_to_dict(c) for c in job.cabinets],
        "loose": [panel_to_dict(p) for p in job.loose],
    }
    # Only written when there is one, so job files predating rooms stay byte-identical.
    if job.room is not None:
        d["room"] = room_to_dict(job.room)
    if job.placements:
        d["placements"] = [placement_to_dict(p) for p in job.placements]
    if job.gaps:
        d["gaps"] = [asdict(g) for g in job.gaps]
    if job.plinths:
        d["plinths"] = [asdict(p) for p in job.plinths]
    # Only when one has been given: a job with none is byte-identical to one
    # written before criticals could be accepted.
    if job.acceptances:
        d["acceptances"] = [asdict(a) for a in job.acceptances]
    # The runners this project selected, and the records it was quoted with —
    # only when there is one, so a job saved before the catalogue is
    # byte-identical.
    if job.runners:
        d["runners"] = job.runners
    return d


def job_from_dict(d: dict) -> Job:
    return Job(
        name=d.get("name", "untitled"),
        cabinets=[cabinet_from_dict(c) for c in d.get("cabinets", [])],
        loose=[panel_from_dict(p) for p in d.get("loose", [])],
        boards=list(d.get("boards") or []),
        # An explicit {} means "this project has selected no boards yet", which is
        # what a new one says. Only a missing or null key falls back to the house
        # boards, which is how every job written before the library reads.
        materials=(d["materials"] if isinstance(d.get("materials"), dict)
                   else Job("x").materials),
        room=room_from_dict(d["room"]) if d.get("room") else None,
        placements=[Placement(**_only_known(Placement, p))
                    for p in d.get("placements", [])],
        gaps=[GapChoice(**_only_known(GapChoice, g)) for g in d.get("gaps", [])],
        plinths=[PlinthChoice(**_only_known(PlinthChoice, p))
                 for p in d.get("plinths", [])],
        acceptances=[Acceptance(**_only_known(Acceptance, a))
                     for a in d.get("acceptances", []) if isinstance(a, dict)],
        runners=(dict(d["runners"]) if isinstance(d.get("runners"), dict) else {}),
    )


def save(job: Job, path: str):
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(job_to_dict(job), fh, indent=2, ensure_ascii=False)


def load(path: str) -> Job:
    with open(path, encoding="utf-8") as fh:
        return job_from_dict(json.load(fh))


def next_number(job: Job) -> int:
    used = {c.number for c in job.cabinets} | {p.cabinet for p in job.loose}
    n = 1
    while n in used:
        n += 1
    return n
