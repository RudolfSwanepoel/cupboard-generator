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
"""
import json
import os
from dataclasses import asdict, dataclass, field, fields
from typing import Dict, List, Optional

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIBRARY = os.path.join(ROOT, "boards.json")

# What the thickness dropdown offers. 3 is not offered for a new board — it is
# here because the backing board really is 3 mm and a board already in the
# library must not lose its thickness by being opened in the editor.
THICKNESSES = (16, 25)
GRAINS = ("plain", "grain")
TAPE_KINDS = ("pvc", "1mm", "2mm")
TAPE_PREFIX = {"pvc": "PVC", "1mm": "1mm", "2mm": "2mm"}


@dataclass
class Board:
    id: str                      # stable key; also the material name on a panel
    name: str = ""               # free text, and what the quote orders by
    tape: str = ""               # token the tape names are generated from
    thickness: int = 16          # 16 | 25 (3 exists on the backing board)
    grain: str = "plain"         # 'grain' locks every panel cut from it
    price: float = 0.0           # last price per board
    picture: str = ""            # optional; a path or a data URI

    @property
    def token(self) -> str:
        """What the tape names are built from."""
        return (self.tape or self.name).strip()

    def tape_name(self, kind: str) -> str:
        """`PVC WOOD`, `2mm WOOD` ... or '' when there is nothing to build from."""
        token = self.token
        return f"{TAPE_PREFIX[kind]} {token}" if token else ""

    @property
    def grain_flag(self) -> int:
        return 1 if self.grain == "grain" else 0


def board_from_dict(d: dict) -> Board:
    known = {f.name for f in fields(Board)}
    d = {k: v for k, v in (d or {}).items() if k in known}
    d.setdefault("id", d.get("name", ""))
    return Board(**d)


def load(path: str = LIBRARY) -> List[Board]:
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as fh:
        raw = json.load(fh)
    return [board_from_dict(b) for b in raw.get("boards", [])]


def save(boards: List[Board], path: str = LIBRARY):
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
            "price": board.price, "picture": board.picture}


# --- which jobs use which board ---------------------------------------------

@dataclass
class Usage:
    """Which saved jobs use a board, and which could not be read at all.

    A job that will not parse is listed by name rather than skipped: a board
    quietly reported as unused is how one gets edited out from under a real job.
    """
    used_by: Dict[str, List[str]] = field(default_factory=dict)   # board id -> job files
    unreadable: List[Dict[str, str]] = field(default_factory=list)


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
                for f in ("carcass_board", "exterior_board", "decor"):
                    if cab.get(f):
                        keys.add(cab[f])
                for d in cab.get("drawers") or []:
                    for f in ("box_board", "face_board"):
                        if isinstance(d, dict) and d.get(f):
                            keys.add(d[f])
        except Exception as exc:                                  # noqa: BLE001
            out.unreadable.append({"job": name, "error": f"{type(exc).__name__}: {exc}"})
            continue
        for k in sorted(keys):
            out.used_by.setdefault(k, []).append(name)
    return out
