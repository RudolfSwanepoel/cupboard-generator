"""The board library: every board the workshop buys, in one file, shared.

`boards.json` sits in the repo so both machines see the same list. It is a
library, not a job: a project *selects* from it, and selecting copies the
record into the job. That copy is what keeps a quoted job quoted — editing a
board's price here changes what the next job is priced at and never what an
existing one was (see `Job.materials`, and "Price capture" in CLAUDE.md).

Tape names are **generated from the board's tape token**, one token for all
three thicknesses:

    PVC <token>     the thin carcass tape
    1mm <token>     exterior option
    2mm <token>     exterior option

The token is a field of its own rather than the board's name, and that is
deliberate. Edging names are decided per order, not looked up from a fixed
catalogue name, and generating off the long description would put "PVC BROOKHILL
FUSION CHIP" on an order as an edging name. One token, three thicknesses,
still generated and never mapped per thickness. A board that leaves the token
blank generates off its name, which is right for a board whose name is already
the short one.

A board also says whether it has edging at all ("Has Edging") and, if it does,
which of the three it offers. A board that offers none — the 3 mm backing sheet
— generates no tape name, is not offered as an edging colour, and puts nothing
about edging on any drawing. Unticking keeps the token and the kinds in the file
(the same discipline as every other tickbox here), so re-ticking restores them.

The colour is what the board looks like on screen: one hex value, picked here
and nowhere else. Picture, grain and thickness are fields of this record too —
the drawings read every board attribute from the library's copy in the job and
never invent one.
"""
import json
import os
import re
from dataclasses import asdict, dataclass, field, fields
from typing import Dict, List, Optional

from .model import NO_COLOUR      # a board nobody has coloured: neutral, not a finish

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIBRARY = os.path.join(ROOT, "boards.json")

# What the thickness dropdown offers. 3 is not offered for a new board — it is
# here because the backing board really is 3 mm and a board already in the
# library must not lose its thickness by being opened in the editor.
THICKNESSES = (16, 25)
GRAINS = ("plain", "grain")
TAPE_KINDS = ("pvc", "1mm", "2mm")
TAPE_PREFIX = {"pvc": "PVC", "1mm": "1mm", "2mm": "2mm"}

_HEX = re.compile(r"^#?([0-9a-fA-F]{6})$")
_HEX3 = re.compile(r"^#?([0-9a-fA-F]{3})$")


def clean_colour(raw) -> str:
    """'#rrggbb' in lower case, or '' for anything that is not one. '#rgb' is
    expanded rather than dropped, because that is a colour somebody meant."""
    s = str(raw or "").strip()
    m = _HEX.match(s)
    if m:
        return "#" + m.group(1).lower()
    m = _HEX3.match(s)
    if m:
        return "#" + "".join(c * 2 for c in m.group(1).lower())
    return ""


def clean_kinds(raw) -> List[str]:
    """The ticked edging kinds, in the canonical order, without repeats and
    without anything that is not one of the three."""
    have = {str(k).strip().lower() for k in (raw or [])}
    return [k for k in TAPE_KINDS if k in have]


@dataclass
class Board:
    id: str                      # stable key; also the material name on a panel
    name: str = ""               # free text, and what the quote orders by
    tape: str = ""               # token the tape names are generated from
    thickness: int = 16          # 16 | 25 (3 exists on the backing board)
    grain: str = "plain"         # 'grain' locks every panel cut from it
    price: float = 0.0           # last price per board
    # Optional. A path relative to the repo (`Pictures/Storm Grey.jpg`) or a
    # data: URI. `cabinetgen.pictures` is what puts it in that shape and what
    # turns it into the URL a page asks for -- never an absolute path, because
    # this file is shared through git.
    picture: str = ""
    # "Has Edging", and which of PVC / 1mm / 2mm it offers. A record written
    # before these existed has neither key and reads as edged with all three,
    # which is what every job quoted before them was quoted with. Unticking keeps
    # the kinds and the token: nothing is forgotten, only ignored.
    has_edging: bool = True
    edging_kinds: List[str] = field(default_factory=lambda: list(TAPE_KINDS))
    colour: str = ""             # '#rrggbb'; what it looks like on screen

    @property
    def token(self) -> str:
        """What the tape names are built from."""
        return (self.tape or self.name).strip()

    @property
    def offered(self) -> List[str]:
        """The edging kinds this board actually offers: none when it has no edging."""
        return list(self.edging_kinds) if self.has_edging else []

    @property
    def shown_colour(self) -> str:
        """What to draw it in. A board nobody has coloured is neutral, and the
        legend says so — an unset colour is never guessed at."""
        return self.colour or NO_COLOUR

    @property
    def is_thin(self) -> bool:
        """The 3 mm backing sheet: no carcass, door, face or drawer box."""
        return self.thickness <= 3

    def tape_name(self, kind: str) -> str:
        """`PVC WOOD`, `2mm WOOD` ... or '' when the board does not offer that
        edging or there is nothing to build a name from."""
        token = self.token
        if not token or kind not in self.offered:
            return ""
        return f"{TAPE_PREFIX[kind]} {token}"

    @property
    def grain_flag(self) -> int:
        return 1 if self.grain == "grain" else 0


def board_from_dict(d: dict) -> Board:
    known = {f.name for f in fields(Board)}
    d = {k: v for k, v in (d or {}).items() if k in known}
    d.setdefault("id", d.get("name", ""))
    # A record with neither key keeps the dataclass defaults — edged, all three —
    # which is the legacy rule. Only a key that is actually present is sanitised.
    if "has_edging" in d:
        d["has_edging"] = bool(d["has_edging"])
    if "edging_kinds" in d:
        d["edging_kinds"] = clean_kinds(d["edging_kinds"])
    if "colour" in d:
        d["colour"] = clean_colour(d["colour"])
    return Board(**d)


def load(path: Optional[str] = None) -> List[Board]:
    # Resolved at call time, not bound as a default at import: a default would
    # capture LIBRARY once, so a check that redirects the library to a fixture
    # would still read — and worse, save over — the real boards.json.
    path = path or LIBRARY
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as fh:
        raw = json.load(fh)
    return [board_from_dict(b) for b in raw.get("boards", [])]


def save(boards: List[Board], path: Optional[str] = None):
    path = path or LIBRARY        # call time, for the reason in load()
    payload = {
        "version": 1,
        "note": ("The board library. Shared across every project and committed to "
                 "the repo so both machines see the same boards. A job does not "
                 "point at this file: selecting a board copies its record into the "
                 "job, which is what keeps a quoted job quoted (see Job.materials "
                 "and CLAUDE.md, 'Price capture')."),
        "boards": [asdict(b) for b in boards],
    }
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, ensure_ascii=False)
        fh.write("\n")


def by_id(boards: List[Board]) -> Dict[str, Board]:
    return {b.id: b for b in boards}


def find(boards: List[Board], board_id: str) -> Optional[Board]:
    return by_id(boards).get(board_id)


def next_id(boards: List[Board], name: str) -> str:
    """A stable key off the name: it becomes the material a panel is cut from,
    so it goes onto the cut list and into a file name."""
    base = "".join(ch for ch in (name or "board").upper() if ch.isalnum()) or "BOARD"
    base = base[:12]
    used = {b.id for b in boards}
    if base not in used:
        return base
    n = 2
    while f"{base}{n}" in used:
        n += 1
    return f"{base}{n}"


# --- what a board is selected into ------------------------------------------

def to_material(board: Board) -> dict:
    """The record a job keeps once it selects this board.

    A snapshot, deliberately: the price is what this job was quoted at, and the
    name, token, thickness and grain are what it was quoted with. Editing the
    library afterwards moves neither.
    """
    return {"board": board.name, "name": board.name, "tape": board.token,
            "thickness": board.thickness, "grain": board.grain,
            "price": board.price, "picture": board.picture,
            "has_edging": board.has_edging,
            "edging_kinds": list(board.edging_kinds), "colour": board.colour}


# --- which jobs use which board ---------------------------------------------

@dataclass
class Usage:
    """Which saved jobs use a board, and which could not be read at all.

    A job that will not parse is listed by name rather than skipped: a board
    quietly reported as unused is how one gets edited out from under a real job.
    """
    used_by: Dict[str, List[str]] = field(default_factory=dict)   # board id -> job files
    unreadable: List[Dict[str, str]] = field(default_factory=list)


# Every field a cabinet names a board in, read straight off the JSON.
#
# This scan cannot build a `Cabinet` — a job file that will not parse has to be
# reported by name, not skipped, so it reads the raw dict. It is therefore the
# one place that repeats `Cabinet._board_slots`, and `tools/check_single_source.py`
# holds the two together: a board field added to the dataclass and not here
# would let a board be deleted from the library out from under a saved job.
CABINET_BOARD_FIELDS = ("carcass_board", "exterior_board", "back_board",
                        "drawer_carcass_board", "drawer_face_board",
                        "door_edge_board", "drawer_edge_board",
                        "decor")          # the pre-library name for the exterior
DRAWER_BOARD_FIELDS = ("box_board", "face_board")


def cabinet_board_ids(cab: dict) -> set:
    """Every board id one cabinet dict names, blanks dropped."""
    keys = set()
    if not isinstance(cab, dict):
        return keys
    for f in CABINET_BOARD_FIELDS:
        if cab.get(f):
            keys.add(cab[f])
    for b in cab.get("door_boards") or []:
        if b:
            keys.add(b)
    for d in cab.get("drawers") or []:
        if isinstance(d, dict):
            for f in DRAWER_BOARD_FIELDS:
                if d.get(f):
                    keys.add(d[f])
    for r in cab.get("support_rows") or []:
        if isinstance(r, dict):
            for f in ("board", "cut_board"):
                if r.get(f):
                    keys.add(r[f])
    for p in cab.get("bespoke") or []:
        if isinstance(p, dict) and p.get("material"):
            keys.add(p["material"])
    p = cab.get("panel")
    if isinstance(p, dict):
        for f in ("board", "edge_board"):
            if p.get(f):
                keys.add(p[f])
    return keys


def scan_jobs(jobs_dir: str) -> Usage:
    out = Usage()
    if not os.path.isdir(jobs_dir):
        return out
    for name in sorted(os.listdir(jobs_dir)):
        if not name.endswith(".json"):
            continue
        path = os.path.join(jobs_dir, name)
        try:
            with open(path, encoding="utf-8") as fh:
                data = json.load(fh)
            if not isinstance(data, dict):
                raise ValueError("not a job object")
            keys = set(data.get("materials") or {})
            keys.update(data.get("boards") or [])
            for cab in data.get("cabinets") or []:
                keys.update(cabinet_board_ids(cab))
        except Exception as exc:                                  # noqa: BLE001
            out.unreadable.append({"job": name, "error": f"{type(exc).__name__}: {exc}"})
            continue
        for k in sorted(keys):
            out.used_by.setdefault(k, []).append(name)
    return out
