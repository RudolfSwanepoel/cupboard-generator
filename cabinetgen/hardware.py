"""The hardware catalogue: runners today, hinges and handles later.

`hardware.json` sits in the repo beside `boards.json`, for the same reason: both
machines see the same catalogue. It is a library, not a job. A project SELECTS a
runner from it, and selecting copies the record into the job (`Job.runners`),
price and all — that copy is the price capture, exactly as a board's is, so
editing a runner here never moves a job that was already quoted.

The file holds one list per kind of hardware. Only `runners` is built (28
September 2026); a `hinges` or `handles` list added later sits beside it, and
`save` keeps any list it does not know about rather than dropping it.

A drawer's box is sized off its runner (sketch `drawer-setting-sketch-v2.svg`,
confirmed by Rudolf):

    box outside width  = opening - 2 x side_clearance      (Gelmar: opening - 27)
    box length         = the runner length, the longest on the record that
                         leaves Standard.runner_clearance behind it
    box bottom         = bottom panel top + lift            (the inner member is
                         centred in the 45 mm outer rail)
    inner member       = starts `setback` behind the box front
    travel             = length (full extension) or length x the fraction

A job saved before runners existed names none, and reads `LEGACY`: the three
lengths the app always picked from (350 / 450 / 500) with the Gelmar-style
clearance, so the October job and Test.json cut exactly what they cut. It is
never offered for a new cabinet.
"""
import json
import os
from dataclasses import asdict, dataclass, field, fields
from typing import Dict, List, Optional, Union

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIBRARY = os.path.join(ROOT, "hardware.json")

# The only type built. The field exists so soft-close and undermount can be
# added when a spec sheet gives their fitting data (Gelmar's undermount pages
# give none).
RUNNER_TYPES = ("side-mount ball-bearing",)


@dataclass
class Runner:
    id: str                          # stable key; what a cabinet names
    name: str = ""
    supplier: str = ""
    sku: str = ""
    price: float = 0.0               # per PAIR — captured into the job
    type: str = RUNNER_TYPES[0]
    height: float = 45               # the outer rail, mm
    side_clearance: float = 13.5     # mm each side, between carcass side and box side
    rail_thickness: float = 12.7     # information: drawn in 3D, sizes nothing
    lengths: List[int] = field(default_factory=list)
    extension: Union[str, float] = "full"   # 'full' (travel = length) or a fraction
    capacity_kg: float = 0
    lift: float = 5                  # drawer side bottom above the rail's bottom
    setback: float = 3               # inner member starts this far behind the box front

    def travel(self, length: int) -> int:
        """How far a drawer on this runner pulls out, for a runner `length`."""
        if self.extension in ("full", "", None):
            return int(length)
        try:
            return int(round(length * float(self.extension)))
        except (TypeError, ValueError):
            return int(length)

    def pick(self, depth: int, clearance: int) -> Optional[int]:
        """The longest length on the record that leaves `clearance` behind it in
        a carcass `depth` deep; None if none does. No length is special.

        >>> SEED.pick(560, 40)
        500
        >>> LEGACY.pick(560, 40)
        500
        >>> SEED.pick(450, 40)
        400
        >>> LEGACY.pick(450, 40)
        350
        """
        fits = [n for n in self.lengths if n <= depth - clearance]
        return max(fits) if fits else None

    @property
    def shortest(self) -> Optional[int]:
        return min(self.lengths) if self.lengths else None


# The runner every job saved before the catalogue was quoted on: the three
# lengths `Standard.runner_lengths` used to hold, and the clearance
# `drawer_front_deduct` 59 was (13.5 a side + two 16 mm box sides). Its id is
# blank because that is what such a cabinet stores. Never offered for new work.
LEGACY = Runner(id="", name="Legacy runners (as quoted)", supplier="",
                height=45, side_clearance=13.5, rail_thickness=12.7,
                lengths=[350, 450, 500], extension="full", capacity_kg=0,
                lift=5, setback=3)

# The seed record (drawing 04227.XXX-58B, SKU family 7011-7017). Gelmar's rule:
# drawer width = opening - 27, which with 16 mm drawer sides is exactly the old
# 59 deduct, so width does not move. The library file is where it is edited;
# this copy is what a new cabinet falls back to if the library has lost it.
SEED_ID = "GELMAR45"
SEED = Runner(id=SEED_ID, name="Gelmar 45 mm full-extension ball-bearing",
              supplier="Gelmar", sku="7011-7017", price=0.0,
              type=RUNNER_TYPES[0], height=45, side_clearance=13.5,
              rail_thickness=12.7, lengths=[300, 350, 400, 450, 500, 550, 600],
              extension="full", capacity_kg=35, lift=5, setback=2)

_NUM = ("price", "height", "side_clearance", "rail_thickness", "capacity_kg",
        "lift", "setback")


def _num(v, default=0.0):
    try:
        f = float(v)
    except (TypeError, ValueError):
        return default
    return int(f) if f == int(f) else f


def clean_lengths(raw) -> List[int]:
    """Whole millimetres, positive, sorted, no repeats. Accepts a list or a
    string like '300, 350 400'."""
    if isinstance(raw, str):
        raw = raw.replace(",", " ").split()
    out = set()
    for v in raw or []:
        try:
            n = int(round(float(v)))
        except (TypeError, ValueError):
            continue
        if n > 0:
            out.add(n)
    return sorted(out)


def clean_extension(raw):
    """'full', or a fraction between 0 and 1 (0.75 for three-quarter)."""
    s = str(raw if raw is not None else "full").strip().lower()
    if s in ("", "full", "1", "1.0"):
        return "full"
    try:
        f = float(s)
    except ValueError:
        return "full"
    return f if 0 < f < 1 else "full"


def runner_from_dict(d: dict) -> Runner:
    known = {f.name for f in fields(Runner)}
    d = {k: v for k, v in (d or {}).items() if k in known}
    d.setdefault("id", "")
    for k in _NUM:
        if k in d:
            d[k] = _num(d[k])
    if "lengths" in d:
        d["lengths"] = clean_lengths(d["lengths"])
    if "extension" in d:
        d["extension"] = clean_extension(d["extension"])
    return Runner(**d)


def to_record(r: Runner) -> dict:
    """The copy a job keeps once it selects this runner: a snapshot, price
    included, never a pointer at the library."""
    return asdict(r)


def builtin(runner_id: str) -> Optional[Runner]:
    """The records the code itself knows: LEGACY for a blank id (every job
    saved before runners), and the seed for its id."""
    if not runner_id:
        return LEGACY
    if runner_id == SEED_ID:
        return SEED
    return None


def resolve(runner_id: str, records: Optional[Dict[str, dict]]) -> Optional[Runner]:
    """What a cabinet naming `runner_id` is built on: blank is LEGACY; an id
    the job selected is the job's copy; otherwise the built-in record if there
    is one (the validator names a runner the job never selected), else None."""
    if not runner_id:
        return LEGACY
    rec = (records or {}).get(runner_id)
    if isinstance(rec, dict):
        return runner_from_dict(dict(rec, id=runner_id))
    return builtin(runner_id)


# --- the library file --------------------------------------------------------

def _read(path: str) -> dict:
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as fh:
        raw = json.load(fh)
    return raw if isinstance(raw, dict) else {}


def load(path: Optional[str] = None) -> List[Runner]:
    """The runners in the library. Resolved at call time, like boards.load, so a
    check can point at a fixture without writing the real file."""
    path = path or LIBRARY
    return [runner_from_dict(r) for r in _read(path).get("runners", [])
            if isinstance(r, dict)]


def save(runners: List[Runner], path: Optional[str] = None):
    """Write the runners, keeping every other list in the file (hinges, handles
    — whatever is added later) exactly as it was."""
    path = path or LIBRARY
    raw = _read(path)
    raw["version"] = raw.get("version", 1)
    raw["note"] = ("The hardware catalogue. Shared across every project and "
                   "committed to the repo, like boards.json. A job does not point "
                   "at this file: selecting a runner copies its record into the "
                   "job, which is what keeps a quoted job quoted.")
    raw["runners"] = [asdict(r) for r in runners]
    order = ["version", "note", "runners"]
    out = {k: raw[k] for k in order}
    out.update({k: v for k, v in raw.items() if k not in order})
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=2, ensure_ascii=False)
        fh.write("\n")


def find(runners: List[Runner], runner_id: str) -> Optional[Runner]:
    return next((r for r in runners if r.id == runner_id), None)


def next_id(runners: List[Runner], name: str) -> str:
    base = "".join(ch for ch in (name or "runner").upper() if ch.isalnum())[:12] or "RUNNER"
    used = {r.id for r in runners}
    if base not in used:
        return base
    n = 2
    while f"{base}{n}" in used:
        n += 1
    return f"{base}{n}"


def clean_id(raw) -> str:
    return "".join(ch for ch in str(raw or "").upper() if ch.isalnum() or ch == "_")[:12]


def scan_jobs(jobs_dir: str) -> Dict[str, List[str]]:
    """runner id -> the saved job files that select it or name it on a
    cabinet. A job that will not parse is skipped here: `boards.scan_jobs`
    already names it on the Boards side, and the delete guard below errs the
    safe way for anything it can read."""
    out: Dict[str, List[str]] = {}
    if not os.path.isdir(jobs_dir):
        return out
    for name in sorted(os.listdir(jobs_dir)):
        if not name.endswith(".json"):
            continue
        try:
            with open(os.path.join(jobs_dir, name), encoding="utf-8") as fh:
                data = json.load(fh)
        except Exception:                                          # noqa: BLE001
            continue
        if not isinstance(data, dict):
            continue
        sel = data.get("runners")
        keys = set(sel) if isinstance(sel, dict) else set()
        for cab in data.get("cabinets") or []:
            if isinstance(cab, dict) and cab.get("runner"):
                keys.add(cab["runner"])
        for k in sorted(keys):
            out.setdefault(k, []).append(name)
    return out
