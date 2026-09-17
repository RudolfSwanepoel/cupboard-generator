"""Job files. Plain JSON so they diff, back up and open in a text editor."""
import json
from dataclasses import asdict, fields

from .model import (Cabinet, Drawer, GapChoice, Job, Obstruction, Opening, Panel,
                    Placement, PlinthChoice, Room, Wall)


def panel_to_dict(p: Panel) -> dict:
    return asdict(p)


def panel_from_dict(d: dict) -> Panel:
    known = {f.name for f in fields(Panel)}
    return Panel(**{k: v for k, v in d.items() if k in known})


def cabinet_to_dict(c: Cabinet) -> dict:
    d = asdict(c)
    d["drawers"] = [asdict(x) for x in c.drawers]
    d["bespoke"] = [panel_to_dict(x) for x in c.bespoke]
    return d


def cabinet_from_dict(d: dict) -> Cabinet:
    d = dict(d)
    d["drawers"] = [Drawer(**x) for x in d.get("drawers", [])]
    d["bespoke"] = [panel_from_dict(x) for x in d.get("bespoke", [])]
    known = {f.name for f in fields(Cabinet)}
    return Cabinet(**{k: v for k, v in d.items() if k in known})


def _only_known(cls, d: dict) -> dict:
    known = {f.name for f in fields(cls)}
    return {k: v for k, v in d.items() if k in known}


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
        materials=d.get("materials") or Job("x").materials,
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
