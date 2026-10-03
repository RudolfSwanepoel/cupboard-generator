"""The catalogue of standard cupboards (ruling 9 of the cabinet round, 3 October 2026).

`cupboards.json` at the repo root, beside `boards.json` and `hardware.json`,
shared through git. A record is a cupboard as it was configured — every
setting (doors, drawers, supports, shelves, back, corner settings) and its
attached panels with their offsets — without its number, placement or note,
plus the boards and runners it names (id and name, and a snapshot of their
records so Catalogue -> Cupboards can draw it), an author and the date added.

The name is generated, `<Kind> <W>x<H>x<D>` (e.g. `Tall 800×2500×600`),
followed by the text the user types; the generated part is always there and
always first, and Rename changes only the text after it (Rudolf's change 4).
A name already in the catalogue, compared case-insensitively, is refused with
`importer.taken_message`, as Import and Save do.

Placing a record copies it into the project with the next free number (its
attached panels with theirs), unplaced — into the unplaced list. From then
on it is the project's own: no link back; editing either changes nothing in
the other. Any board the copy names that the project has not selected is
mapped to a project board first (default the first project board of the same
thickness), and a runner the project has not selected is mapped the same way
— or ticked in from the runner library if it is there, which is offered
first — so a catalogue cupboard never arrives with an unpriced board.

Decided here and testable without the UI: the name rule, the taken-name
refusal, the copy-in with next numbers, and the board / runner mapping.
"""
import json
import os
from dataclasses import asdict
from datetime import date
from typing import Dict, List, Optional

from . import boards as B
from . import hardware as H
from .model import Cabinet, Job, material_thickness
from .room import attached_panels, geometry
from .store import cabinet_from_dict, cabinet_to_dict, next_number

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CATALOGUE_FILE = "cupboards.json"
LIBRARY = os.path.join(ROOT, CATALOGUE_FILE)
NOTE = ("The catalogue of standard cupboards. Shared across every project and committed "
        "to the repo so both machines see the same cupboards. Placing one copies it into "
        "the project; nothing points back here (see docs/HOW-IT-WORKS.md, Catalogue).")


# --- the file -------------------------------------------------------------------

def load(path: Optional[str] = None) -> List[dict]:
    # Resolved at call time, not bound as a default at import, for the reason
    # boards.load gives: a check that redirects the library must never read —
    # or save over — the real cupboards.json.
    path = path or LIBRARY
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as fh:
        raw = json.load(fh)
    return [dict(r) for r in raw.get("cupboards", []) if isinstance(r, dict)]


def save(records: List[dict], path: Optional[str] = None):
    path = path or LIBRARY
    payload = {"version": 1, "note": NOTE, "cupboards": [dict(r) for r in records]}
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, ensure_ascii=False)
        fh.write("\n")


# --- names ------------------------------------------------------------------------

def same_name(a: str, b: str) -> bool:
    return str(a or "").casefold() == str(b or "").casefold()


def find(records: List[dict], name: str) -> Optional[dict]:
    return next((r for r in records if same_name(r.get("name"), name)), None)


def kind_word(cab: Cabinet) -> str:
    """`Base`, `Tall`, `Upper` — and a corner unit's type after it (`Base mitre`)."""
    word = {"base": "Base", "tall": "Tall", "upper": "Upper"}.get(cab.kind, str(cab.kind).capitalize())
    return f"{word} {cab.corner_kind}" if cab.corner_on and cab.corner_kind else word


def generated_name(cab: Cabinet, std=None, materials: dict = None) -> str:
    """The fixed, always-first part of a record's name: `<Kind> <W>×<H>×<D>`.
    A straight cupboard's figures are the ones its editor shows; a corner
    unit, which has no declared figures, gives its geometry's.

    >>> generated_name(Cabinet(number=1, width=800, height=2500, depth=600, kind="tall"))
    'Tall 800×2500×600'
    """
    if cab.corner_on:
        g = geometry(cab, std or cab_std(), materials)
        w, h, d = g.width, g.height, g.depth
    else:
        w, h, d = cab.width, cab.height, cab.depth
    return f"{kind_word(cab)} {w}×{h}×{d}"


def cab_std():
    from .standard import STANDARD
    return STANDARD


def full_name(prefix: str, text: str) -> str:
    """The prefix, then the text the user typed, if any."""
    text = " ".join(str(text or "").split())
    return f"{prefix} {text}" if text else prefix


def _refuse_taken(records: List[dict], name: str, keep: Optional[dict] = None):
    from .importer import taken_message
    have = find(records, name)
    if have is not None and have is not keep:
        raise ValueError(taken_message(name))


# --- the record -----------------------------------------------------------------

def _strip_cabinet(c: Cabinet) -> dict:
    """A cabinet as stored: its whole configuration, without its number, its
    note or anything about where it stands."""
    d = cabinet_to_dict(c)
    d["number"] = 0
    d["note"] = ""
    for q in d.get("bespoke") or []:
        q["cabinet"] = 0
    if d.get("panel"):
        # an attached panel's offsets stay; its host is the record's head
        if d["panel"].get("attached_to") is not None:
            d["panel"]["attached_to"] = 0
    return d


def add(job: Job, number: int, author: str, text: str, records: List[dict],
        today: Optional[str] = None) -> dict:
    """Save the cupboard `number` as it is configured. Refuses a Panel, and a
    name the catalogue already has (any case). Returns the record; the caller
    saves `records`."""
    cab = next((c for c in job.cabinets if c.number == number), None)
    if cab is None:
        raise ValueError(f"no cabinet {number}")
    if cab.is_panel:
        raise ValueError("a Panel is not a cupboard — Add to catalogue is for cupboards")
    prefix = generated_name(cab, job.std, job.materials)
    name = full_name(prefix, text)
    _refuse_taken(records, name)
    panels = attached_panels(job, cab.number)
    everything = [cab] + list(panels)
    board_ids = []
    for c in everything:
        for bid in c.board_ids_used():
            if bid not in board_ids:
                board_ids.append(bid)
    mats = job.materials or {}
    runners = []
    if cab.runner:
        runners.append({"id": cab.runner,
                        "name": ((job.runners or {}).get(cab.runner) or {}).get("name", cab.runner)})
    rec = {
        "name": name, "prefix": prefix, "text": " ".join(str(text or "").split()),
        "author": " ".join(str(author or "").split()), "added": today or date.today().isoformat(),
        "kind": cab.kind,
        "cabinet": _strip_cabinet(cab),
        "panels": [_strip_cabinet(p) for p in panels],
        "boards": [{"id": bid, "name": (mats.get(bid) or {}).get("board") or (mats.get(bid) or {}).get("name") or bid,
                    "thickness": material_thickness(mats, bid) if bid in mats else None}
                   for bid in board_ids],
        "runners": runners,
        # snapshots, so the catalogue can draw and price the cupboard on its own
        "materials": {bid: dict(mats[bid]) for bid in board_ids if isinstance(mats.get(bid), dict)},
        "runner_records": {r["id"]: dict((job.runners or {}).get(r["id"]) or {}) for r in runners
                           if isinstance((job.runners or {}).get(r["id"]), dict)},
    }
    records.append(rec)
    return rec


def rename(records: List[dict], name: str, text: str) -> dict:
    """Change the free text after the fixed prefix (Rudolf's change 4). The
    prefix never changes; the new name is refused if taken (any case)."""
    rec = find(records, name)
    if rec is None:
        raise ValueError(f"no cupboard {name!r} in the catalogue")
    new = full_name(rec.get("prefix") or rec["name"], text)
    _refuse_taken(records, new, keep=rec)
    rec["text"] = " ".join(str(text or "").split())
    rec["name"] = new
    return rec


def delete(records: List[dict], name: str) -> List[dict]:
    rec = find(records, name)
    if rec is None:
        raise ValueError(f"no cupboard {name!r} in the catalogue")
    return [r for r in records if r is not rec]


# --- placing ----------------------------------------------------------------------

def needs_mapping(job: Job, rec: dict) -> dict:
    """What the project must decide before this record can land: every board
    the record names that the project has not selected (default the first
    project board of the same thickness), and every runner it names that the
    project has not selected (the runner library's own record offered first
    where it is there, else the project's first runner). Empty lists mean it
    can land as it is."""
    mats = job.materials or {}
    selected = list(job.boards or [])
    boards = []
    for b in rec.get("boards") or []:
        if b["id"] in selected:
            continue
        same = [k for k in selected if b.get("thickness") is not None
                and material_thickness(mats, k) == b["thickness"]]
        boards.append({"id": b["id"], "name": b.get("name") or b["id"], "thickness": b.get("thickness"),
                       "default": (same or selected or [""])[0], "options": selected})
    runners = []
    have = list(job.runners or {})
    lib = {r.id: r for r in H.load()}
    for r in rec.get("runners") or []:
        if r["id"] in have:
            continue
        in_lib = r["id"] in lib
        runners.append({"id": r["id"], "name": r.get("name") or r["id"], "in_library": in_lib,
                        "default": "library" if in_lib else (have[0] if have else ""),
                        "options": have})
    return {"boards": boards, "runners": runners}


def place(job: Job, rec: dict, board_map: Optional[Dict[str, str]] = None,
          runner_map: Optional[Dict[str, str]] = None) -> List[Cabinet]:
    """Copy the record into the project: the cupboard with the next free
    number, its attached panels with theirs, every board it names mapped
    through `board_map` (a board the project has not selected MUST be mapped
    — refused otherwise, so nothing arrives unpriced), its runner through
    `runner_map` ("library" ticks the library's record into the project).
    No placement: the copies go into the unplaced list. Appended to
    `job.cabinets` and returned."""
    need = needs_mapping(job, rec)
    board_map = dict(board_map or {})
    runner_map = dict(runner_map or {})
    selected = list(job.boards or [])
    missing = [b["id"] for b in need["boards"] if board_map.get(b["id"]) not in selected]
    if missing:
        raise ValueError("these boards are not selected in this project and must be mapped first: "
                         + ", ".join(missing))
    for r in need["runners"]:
        choice = runner_map.get(r["id"])
        if choice == "library":
            lr = H.find(H.load(), r["id"]) or H.builtin(r["id"])
            if lr is None:
                raise ValueError(f"runner {r['id']} is not in the runner library")
            job.runners = dict(job.runners or {})
            job.runners[r["id"]] = H.to_record(lr)
            runner_map[r["id"]] = r["id"]
        elif choice in (job.runners or {}):
            pass
        elif choice in ("", None) and not (job.runners or {}):
            runner_map[r["id"]] = ""            # no runner in the project: the LEGACY record
        else:
            raise ValueError(f"runner {r['id']} is not selected in this project and must be mapped first")

    def fn(bid):
        return board_map.get(bid, bid)

    out = []

    def clone(d: dict, number: int) -> Cabinet:
        d = json.loads(json.dumps(d))
        d["number"] = number
        for q in d.get("bespoke") or []:
            q["cabinet"] = number
        c = cabinet_from_dict(d)
        c.map_board_refs(fn, hand=True)
        if c.runner in runner_map:
            c.runner = runner_map[c.runner]
        job.cabinets.append(c)                   # so next_number sees it
        out.append(c)
        return c

    head = clone(rec["cabinet"], next_number(job))
    for p in rec.get("panels") or []:
        twin = clone(p, next_number(job))
        if twin.panel is not None:
            twin.panel.attached_to = head.number
    return out


def preview_job(rec: dict) -> Job:
    """A one-cupboard job built from the record's own snapshots, for the
    catalogue's 3D preview: the cupboard at number 1, its panels after it,
    its boards and runner as it was saved with."""
    job = Job(name="catalogue", boards=[b["id"] for b in rec.get("boards") or []],
              materials={k: dict(v) for k, v in (rec.get("materials") or {}).items()},
              runners={k: dict(v) for k, v in (rec.get("runner_records") or {}).items()})
    cabs = []
    head = cabinet_from_dict(json.loads(json.dumps(rec["cabinet"])))
    head.number = 1
    for q in head.bespoke:
        q.cabinet = 1
    cabs.append(head)
    for i, p in enumerate(rec.get("panels") or [], start=2):
        c = cabinet_from_dict(json.loads(json.dumps(p)))
        c.number = i
        if c.panel is not None:
            c.panel.attached_to = 1
        cabs.append(c)
    job.cabinets = cabs
    return job


def summary(rec: dict) -> dict:
    """What the list shows: no cabinet record, just the words."""
    return {"name": rec.get("name", ""), "prefix": rec.get("prefix", ""), "text": rec.get("text", ""),
            "author": rec.get("author", ""), "added": rec.get("added", ""), "kind": rec.get("kind", ""),
            "boards": list(rec.get("boards") or []), "runners": list(rec.get("runners") or []),
            "panels": len(rec.get("panels") or [])}
