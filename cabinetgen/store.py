"""Job files. Plain JSON so they diff, back up and open in a text editor."""
import json
from dataclasses import asdict, fields

from .model import (Cabinet, Drawer, GapChoice, Job, Obstruction, Opening, Panel,
                    PanelSpec, Placement, PlinthChoice, Room, Support, Wall)


def _only_known(cls, d: dict) -> dict:
    known = {f.name for f in fields(cls)}
    return {k: v for k, v in d.items() if k in known}


def panel_to_dict(p: Panel) -> dict:
    return asdict(p)


def panel_from_dict(d: dict) -> Panel:
    known = {f.name for f in fields(Panel)}
    return Panel(**{k: v for k, v in d.items() if k in known})


def cabinet_to_dict(c: Cabinet) -> dict:
    d = asdict(c)
    d["drawers"] = [asdict(x) for x in c.drawers]
    # `board` and `kind` are written only when a row actually names them, so a
    # job saved before the control round-trips byte for byte and is still read
    # from `edge` — the same discipline as every other field added here.
    d["support_rows"] = [{k: v for k, v in asdict(x).items()
                          if v != "" or k not in ("board", "kind", "cut_board")}
                         for x in c.support_rows]
    d["bespoke"] = [panel_to_dict(x) for x in c.bespoke]
    # Only written when this item actually is a panel, and `anchor` only when it
    # is set — so a job with no panels is byte-identical to one written before
    # they existed. The same discipline as `room` and `placements` above.
    if c.panel is None:
        d.pop("panel", None)
    else:
        d["panel"] = {k: v for k, v in asdict(c.panel).items()
                      if k != "anchor" or v is not None}
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
    d["bespoke"] = [panel_from_dict(x) for x in d.get("bespoke", [])]
    d["panel"] = (PanelSpec(**_only_known(PanelSpec, d["panel"]))
                  if isinstance(d.get("panel"), dict) else None)
    known = {f.name for f in fields(Cabinet)}
    return Cabinet(**{k: v for k, v in d.items() if k in known})


def room_to_dict(room: Room) -> dict:
    d = asdict(room)
    d["walls"] = [asdict(w) for w in room.walls]
    return d


def room_from_dict(d: dict) -> Room:
    d = dict(d)
    d["walls"] = [Wall(**dict(_only_known(Wall, w),
                             openings=[Opening(**_only_known(Opening, o))
                                       for o in w.get("openings", [])],
                             obstructions=[Obstruction(**_only_known(Obstruction, o))
                                           for o in w.get("obstructions", [])]))
                  for w in d.get("walls", [])]
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
        d["placements"] = [asdict(p) for p in job.placements]
    if job.gaps:
        d["gaps"] = [asdict(g) for g in job.gaps]
    if job.plinths:
        d["plinths"] = [asdict(p) for p in job.plinths]
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
