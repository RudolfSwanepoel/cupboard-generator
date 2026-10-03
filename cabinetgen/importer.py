"""Import project: bring a whole old Cupboard App folder's work across.

Brief of 3 October 2026 (`Claude outputs/import-project-brief-2026-10-03.md`,
ruled by Rudolf). A demo is a folder: a friend's jobs, any boards, runners and
pictures he added all live beside the exe. A new demo unzips to a new folder
that knows none of it, and the old one has usually expired by then. This is
the one tool that brings an old folder's work into the app running now — and
the same tool moves work between laptops.

Every DECISION lives here, so it is testable without the UI
(`tools/check_import.py`): which folder is a Cupboard App folder, what is
identical, what conflicts, the "(imported n)" name, and the re-pointing.
`app/api.py` only hands over the folder and the paths.

**It only ever READS the old folder.** Nothing there is changed, moved or run —
which is why it works on an expired demo's folder. What comes across (ruling 3):

- job files, `jobs/*.json` (not `jobs/_deleted/`);
- boards from its `boards.json` and runners from its `hardware.json`;
- board pictures from its `Pictures/`.

Not exports, snapshots, `output/`, `demo-seen.txt` or the app's own files.

**Two steps** (ruling 4): `scan` makes the preview — every item and what will
happen to it, `new`, `identical` (skipped), `renamed` (a name conflict), or
`broken` (a job that will not load) — and writes nothing. `run` scans again,
refuses if the folder changed since the preview, and writes.

**A conflict is renamed "(imported)", and the rename is real** (ruling 5). An
item whose name is taken here (compared case-insensitively, as Windows does)
and whose content differs comes in as `<name> (imported)`, then
`(imported 2)`, `(imported 3)`. Before taking a name, each candidate already
here is asked whether it is the SAME thing — so importing a folder a second
time finds `Test (imported)` identical and brings nothing. Re-pointing follows
the rename into everything imported:

- a picture renamed: every imported board (and job copy) naming it;
- a board renamed: a new id (`boards.next_id`), and every imported job that
  named the old id rewritten to the new one (`rename_board_in_job`) before it
  is saved. Otherwise opening it here would take THIS library's board of that
  id (`refresh_from_library` copies name, token, thickness, grain and picture
  by id) and quietly change what the job is cut from;
- a runner renamed: a new id (`hardware.next_id`), and every imported
  cabinet and job runner copy re-pointed.

A board renamed whose Edging Name was blank (so its edging was named off its
board name) is given the old name as its Edging Name: the edging on its jobs'
orders must not change because the board's NAME did. An imported job's
captured prices are its own and are never touched.

**A board a job's own copy describes differently from this library**, where
the old folder's library no longer had the board at all, is the same danger
in a quieter form (the job's copy was what it was cut from there, and opening
it here would refresh it from this library's record of that id). Such a copy
comes in as a board of its own, "(imported)", and that job is re-pointed.

**A price is not an identity** (follow-up brief, ruling 1, 3 October 2026).
A board or runner whose record differs from this library's only in its price
(`Board.price`, `Runner.price`) is identical: skipped, and this library's price
kept. Any other difference is a conflict as above.

**The jobs a demo shipped with are left out** (follow-up brief, ruling 2). A
demo carries `jobs/shipped-jobs.json`, the job file names `tools/build_demo.py`
put there; those jobs are listed `shipped` and never imported, whether or not
the friend changed them, and the list itself is never a job. A folder without
the list (the 30 September demo, another laptop) has every job considered, and
the report says so in one line.

**Old jobs come in through the normal migration** (ruling 9): `store`'s
`job_from_dict`, exactly as Load reads them, saved in the current format. A job
from a NEWER version — one carrying a field this app does not know — is brought
in as it stands (its raw JSON, only the name and the re-pointing changed) and
the report says so.
"""
import hashlib
import json
import os
import shutil
from dataclasses import asdict, dataclass, field, fields, replace
from typing import Callable, Dict, List, Optional

from . import boards as B
from . import hardware as H
from . import pictures as PIC
from .model import (Acceptance, Cabinet, Drawer, GapChoice, Job, Obstruction, Opening,
                    Panel, PanelSpec, Placement, PlinthChoice, Room, Shelf, Support, Wall,
                    material_record)
from .store import job_from_dict, job_to_dict
from . import catalogue as CAT

DEMO_EXE = "Cupboard App Demo.exe"     # tools/build_demo.py's EXE
DEMO_FOLDER = "Cupboard App Demo"      # tools/build_demo.py's APP_FOLDER
JOBS = "jobs"
BOARDS_FILE = "boards.json"
HARDWARE_FILE = "hardware.json"
SHIPPED_FILE = "shipped-jobs.json"     # tools/build_demo.py writes it into the demo's jobs/
NO_SHIPPED_LIST = "No list of shipped jobs in this folder: every job was considered."
KINDS = ("job", "board", "runner", "picture", "cupboard")
KIND_PLURAL = {"job": ("project", "projects"), "board": ("board", "boards"),
               "runner": ("runner", "runners"), "picture": ("picture", "pictures"),
               "cupboard": ("catalogue cupboard", "catalogue cupboards")}


def taken_message(name: str) -> str:
    """Ruling 7, word for word: every rename field and Save say this."""
    return f"{name} already exists — choose another name"


def same_name(a: str, b: str) -> bool:
    """Names compare case-insensitively, as Windows does (ruling 7)."""
    return str(a or "").casefold() == str(b or "").casefold()


def candidates(base: str, ext: str = ""):
    """`base`, `base (imported)`, `base (imported 2)`, ... — for ever."""
    yield base + ext
    yield f"{base} (imported){ext}"
    n = 2
    while True:
        yield f"{base} (imported {n}){ext}"
        n += 1


# --- where it lives -----------------------------------------------------------

@dataclass
class Target:
    """The app being imported INTO: where its jobs, pictures and libraries are."""
    root: str
    jobs_dir: str
    pictures_dir: str
    boards_path: str
    hardware_path: str
    cupboards_path: str = ""          # the catalogue of cupboards (3 October 2026)

    @classmethod
    def at(cls, root: str, boards_path: str = "", hardware_path: str = "",
           cupboards_path: str = "") -> "Target":
        return cls(root=root, jobs_dir=os.path.join(root, JOBS),
                   pictures_dir=os.path.join(root, PIC.DIRNAME),
                   boards_path=boards_path or os.path.join(root, BOARDS_FILE),
                   hardware_path=hardware_path or os.path.join(root, HARDWARE_FILE),
                   cupboards_path=cupboards_path or os.path.join(root, CAT.CATALOGUE_FILE))

    @property
    def catalogue_path(self) -> str:
        return self.cupboards_path or os.path.join(self.root, CAT.CATALOGUE_FILE)


def _job_files(jobs_dir: str) -> List[str]:
    """The `*.json` file names directly in `jobs/` — never `_deleted/`, and
    never a demo's list of the jobs it shipped with, which is not a job."""
    if not os.path.isdir(jobs_dir):
        return []
    return sorted(n for n in os.listdir(jobs_dir)
                  if n.lower().endswith(".json") and not same_name(n, SHIPPED_FILE)
                  and os.path.isfile(os.path.join(jobs_dir, n)))


def shipped_jobs(jobs_dir: str):
    """The job file names a demo shipped with, from its `jobs/shipped-jobs.json`
    (a JSON list of names): a set of casefolded names, None when there is no
    such file, or the reason it cannot be read as a str."""
    path = os.path.join(jobs_dir, SHIPPED_FILE)
    if not os.path.isfile(path):
        return None
    try:
        with open(path, encoding="utf-8") as fh:
            names = json.load(fh)
    except (OSError, ValueError) as exc:
        return f"{type(exc).__name__}: {exc}"
    if not isinstance(names, list) or not all(isinstance(n, str) for n in names):
        return "it is not a list of job file names"
    return {n.casefold() for n in names}


def _readable_job(path: str) -> bool:
    try:
        with open(path, encoding="utf-8") as fh:
            return isinstance(json.load(fh), dict)
    except (OSError, ValueError):
        return False


def is_app_folder(folder: str) -> bool:
    """Ruling 2: `jobs/` with at least one readable job in it, or the demo exe
    beside `jobs/`."""
    jobs = os.path.join(folder, JOBS)
    if not os.path.isdir(jobs):
        return False
    if os.path.isfile(os.path.join(folder, DEMO_EXE)):
        return True
    return any(_readable_job(os.path.join(jobs, n)) for n in _job_files(jobs))


def find_folder(path: str, own_root: str = "") -> dict:
    """The Cupboard App folder at `path`, or why there is none.

    The picked folder itself is asked first, then `Cupboard App Demo` inside it
    (a demo unzips to an outer folder holding that one and `READ ME FIRST.txt`),
    then any other folder directly inside it. Either the outer or the inner
    folder may be picked; both are found. `{ok, folder}` or `{ok: False,
    error}` — the error says what was looked for.
    """
    raw = str(path or "").strip().strip('"').strip("'").strip()
    if not raw:
        return {"ok": False, "error": "no folder given"}
    folder = os.path.abspath(os.path.expanduser(raw))
    if not os.path.isdir(folder):
        return {"ok": False, "error": f"there is no folder at {raw}"}
    tried = [folder]
    inner = os.path.join(folder, DEMO_FOLDER)
    if os.path.isdir(inner):
        tried.append(inner)
    try:
        others = sorted(os.path.join(folder, n) for n in os.listdir(folder)
                        if os.path.isdir(os.path.join(folder, n)) and n != DEMO_FOLDER)
    except OSError:
        others = []
    tried += others
    found = next((f for f in tried if is_app_folder(f)), None)
    if found is None:
        return {"ok": False,
                "error": (f"{raw} is not a Cupboard App folder. Looked for a jobs\\ folder "
                          f"with at least one readable job in it, or {DEMO_EXE} beside a "
                          f"jobs\\ folder — in that folder and in the folders directly "
                          f"inside it. Nothing was imported.")}
    if own_root and os.path.normcase(os.path.realpath(found)) == \
            os.path.normcase(os.path.realpath(own_root)):
        return {"ok": False,
                "error": (f"{raw} is the folder this app runs from — its work is already "
                          f"here. Pick the OLD folder. Nothing was imported.")}
    return {"ok": True, "folder": found}


# --- a job written by a newer version ----------------------------------------

# Keys an older version wrote that the migration reads and never writes again.
# Not "unknown": a job carrying them is OLD, not new.
LEGACY_KEYS = {
    Cabinet: {"decor"},
    Room: {"closed"},
    Wall: {"length", "offset_start", "offset_end", "corner_end"},
}
# The free dicts a job file carries keyed by board / runner id: not a schema.
_FREE = {"materials", "runners", "std"}


def _schema_walk(raw, cls, path, out):
    if not isinstance(raw, dict):
        return
    known = {f.name for f in fields(cls)} | LEGACY_KEYS.get(cls, set())
    for k, v in raw.items():
        if k not in known:
            out.append(path + k)
            continue
        sub = _NESTED.get((cls, k))
        if sub is None or k in _FREE:
            continue
        if isinstance(v, list):
            for i, item in enumerate(v):
                _schema_walk(item, sub, f"{path}{k}[{i}].", out)
        else:
            _schema_walk(v, sub, f"{path}{k}.", out)


_NESTED = {
    (Job, "cabinets"): Cabinet, (Job, "loose"): Panel, (Job, "room"): Room,
    (Job, "placements"): Placement, (Job, "gaps"): GapChoice,
    (Job, "plinths"): PlinthChoice, (Job, "acceptances"): Acceptance,
    (Cabinet, "drawers"): Drawer, (Cabinet, "support_rows"): Support,
    (Cabinet, "shelf_rows"): Shelf,
    (Cabinet, "bespoke"): Panel, (Cabinet, "panel"): PanelSpec,
    (Room, "walls"): Wall, (Wall, "openings"): Opening, (Wall, "obstructions"): Obstruction,
}


def unknown_fields(raw: dict) -> List[str]:
    """The fields of a job file this app does not know, by path
    (`cabinets[2].hinge_brand`). [] for a job this version, or an older one,
    wrote."""
    out: List[str] = []
    _schema_walk(raw, Job, "", out)
    return out


def _dumps(d: dict) -> str:
    """Exactly what `store.save` writes."""
    return json.dumps(d, indent=2, ensure_ascii=False)


# --- the plan -------------------------------------------------------------------

@dataclass
class Item:
    """One line of the preview: an item, and what will happen to it."""
    kind: str                  # job | board | runner | picture
    name: str                  # its name in the old folder
    action: str                # new | identical | renamed | broken | shipped
    to: str = ""               # the name it comes in under (renamed), or matched (identical)
    note: str = ""             # why, or what else to know
    id: str = ""               # board / runner: its id in the old folder
    to_id: str = ""            # board / runner: its id here


@dataclass
class Plan:
    source: str
    items: List[Item] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)
    # what `run` writes: (src path, dest name) / Board / Runner / (file name, text)
    pictures: List[tuple] = field(default_factory=list)
    boards: List[B.Board] = field(default_factory=list)
    runners: List[H.Runner] = field(default_factory=list)
    jobs: List[tuple] = field(default_factory=list)
    cupboards: List[dict] = field(default_factory=list)      # catalogue records, re-pointed

    @property
    def signature(self) -> str:
        """What the preview showed, as one hash: `run` refuses when the folder
        no longer gives the same list."""
        blob = json.dumps([asdict(i) for i in self.items], sort_keys=True)
        return hashlib.sha1(blob.encode("utf-8")).hexdigest()

    def as_dict(self) -> dict:
        return {"source": self.source, "items": [asdict(i) for i in self.items],
                "notes": list(self.notes), "signature": self.signature,
                "counts": self.counts()}

    def counts(self) -> dict:
        c = {a: 0 for a in ("new", "identical", "renamed", "broken", "shipped")}
        for i in self.items:
            c[i.action] = c.get(i.action, 0) + 1
        return c


def _read_bytes(path: str) -> Optional[bytes]:
    try:
        with open(path, "rb") as fh:
            return fh.read()
    except OSError:
        return None


def _board_record(b: B.Board) -> dict:
    """A board as it is compared under its own id and name: everything but the
    price (follow-up ruling 1 — a price-only difference is not a conflict)."""
    d = asdict(b)
    d.pop("price", None)
    return d


def _board_body(b: B.Board) -> dict:
    """A board with its id and name set aside: what makes two boards the same
    board under two names. The edging is compared by its TOKEN, which is what
    a renamed board keeps (see the module docstring). Not the price."""
    d = _board_record(b)
    for k in ("id", "name", "tape"):
        d.pop(k, None)
    d["token"] = b.token
    return d


def _runner_record(r: H.Runner) -> dict:
    """A runner as it is compared under its own id and name: its record, all
    but the price (per pair) — follow-up ruling 1."""
    d = H.to_record(r)
    d.pop("price", None)
    return d


def _runner_body(r: H.Runner) -> dict:
    d = _runner_record(r)
    d.pop("id", None)
    d.pop("name", None)
    return d


def _record_body(rec: dict) -> dict:
    """A catalogue record with its name, text, author and date set aside: the
    cupboard itself (its configuration, its panels, the boards and runners it
    names) — what makes two records the same cupboard under two names."""
    d = {k: v for k, v in rec.items() if k not in ("name", "text", "author", "added")}
    return json.loads(json.dumps(d, sort_keys=True))


class _Scanner:
    def __init__(self, folder: str, target: Target):
        self.src = folder
        self.t = target
        self.plan = Plan(source=folder)
        # everything here, as it will be once the plan is written
        self.lib = B.load(target.boards_path) if os.path.exists(target.boards_path) else []
        self.rlib = H.load(target.hardware_path) if os.path.exists(target.hardware_path) else []
        self.pic_names = {}            # casefold -> actual file name here (or planned)
        if os.path.isdir(target.pictures_dir):
            for n in os.listdir(target.pictures_dir):
                if os.path.isfile(os.path.join(target.pictures_dir, n)):
                    self.pic_names[n.casefold()] = n
        self.planned_pics: Dict[str, str] = {}      # casefold -> src path (planned)
        self.job_names = {n.casefold(): n for n in _job_files(target.jobs_dir)}
        self.planned_jobs: Dict[str, str] = {}      # casefold -> text (planned)
        self.pic_map: Dict[str, str] = {}           # src picture name (casefold) -> name here
        self.board_map: Dict[str, str] = {}         # src board id -> id here
        self.runner_map: Dict[str, str] = {}        # src runner id -> id here
        self.runner_names: Dict[str, str] = {}      # id here -> its name, for job copies
        self.src_lib: List[B.Board] = []
        self.src_rlib: List[H.Runner] = []
        self.reserved_ids = set()                   # ids an imported job names: never a new id
        self.cat = CAT.load(target.catalogue_path) if os.path.exists(target.catalogue_path) else []

    # -- pictures --
    def pictures(self):
        folder = os.path.join(self.src, PIC.DIRNAME)
        if not os.path.isdir(folder):
            return
        for name in sorted(os.listdir(folder)):
            path = os.path.join(folder, name)
            stem, ext = os.path.splitext(name)
            if not os.path.isfile(path) or ext.lower() not in PIC.TYPES:
                continue
            blob = _read_bytes(path)
            if blob is None:
                self.plan.notes.append(f"Pictures\\{name} could not be read — left out.")
                continue
            for k, cand in enumerate(candidates(stem, ext)):
                key = cand.casefold()
                here = self.pic_names.get(key)
                if here is not None:
                    there = (_read_bytes(self.planned_pics[key]) if key in self.planned_pics
                             else _read_bytes(os.path.join(self.t.pictures_dir, here)))
                    if there == blob:
                        self.pic_map[name.casefold()] = here
                        if key not in self.planned_pics:
                            self.plan.items.append(Item("picture", name, "identical", to=here))
                        break
                    continue
                self.pic_names[key] = cand
                self.planned_pics[key] = path
                self.pic_map[name.casefold()] = cand
                self.plan.pictures.append((path, cand))
                self.plan.items.append(Item(
                    "picture", name, "new" if k == 0 else "renamed",
                    to=cand if k else "",
                    note="" if k == 0 else f"a different {name} is already here"))
                break

    def repoint_picture(self, value):
        """A stored picture value after the picture renames. A picture is drawn
        by its file name (`pictures.url_for` serves the basename), so the name
        is what is matched; a value whose picture kept its name is left exactly
        as it was."""
        s = str(value or "")
        if not s or PIC.is_data_uri(s):
            return value
        name = os.path.basename(PIC.clean(s, self.src).replace("\\", "/"))
        here = self.pic_map.get(name.casefold())
        if here is None or here == name:
            return value
        return PIC.DIRNAME + "/" + here

    # -- boards --
    def _new_board_id(self, name: str) -> str:
        pool = self.lib + [B.Board(id=i) for i in self.reserved_ids]
        return B.next_id(pool, name)

    def _place_board(self, b: B.Board, note_from: str = "", item: bool = True) -> str:
        """Decide one board: identical, new or renamed. Returns its id here."""
        for k, cand in enumerate(candidates(b.name)):
            if k == 0:
                same_id = B.find(self.lib, b.id)
                same_nm = next((x for x in self.lib if same_name(x.name, b.name)), None)
                if same_id is not None and _board_record(same_id) == _board_record(b):
                    if item:
                        self.plan.items.append(Item("board", b.name, "identical", to=b.name,
                                                    id=b.id, to_id=b.id))
                    return b.id
                if same_id is None and same_nm is None:
                    self.lib.append(b)
                    self.plan.boards.append(b)
                    if item:
                        self.plan.items.append(Item("board", b.name, "new", id=b.id,
                                                    to_id=b.id, note=note_from))
                    return b.id
                continue
            have = next((x for x in self.lib if same_name(x.name, cand)), None)
            if have is not None:
                if _board_body(have) == _board_body(b):
                    planned = any(x is have for x in self.plan.boards)
                    if item and not planned:
                        self.plan.items.append(Item("board", b.name, "identical", to=have.name,
                                                    id=b.id, to_id=have.id,
                                                    note="imported before"))
                    return have.id
                continue
            new = replace(b, id=self._new_board_id(cand), name=cand,
                          tape=b.tape or b.token)
            self.lib.append(new)
            self.plan.boards.append(new)
            if item:
                taken = B.find(self.lib, b.id)
                why = (f"{b.id} here is {taken.name}, and differs" if taken is not None
                       and taken is not new else f"a different {b.name} is already here")
                self.plan.items.append(Item("board", b.name, "renamed", to=cand, id=b.id,
                                            to_id=new.id,
                                            note=note_from or why))
            return new.id
        raise AssertionError("unreachable")

    def boards(self):
        path = os.path.join(self.src, BOARDS_FILE)
        if not os.path.exists(path):
            return
        try:
            self.src_lib = B.load(path)
        except (OSError, ValueError, TypeError) as exc:
            self.plan.notes.append(f"{BOARDS_FILE} could not be read ({type(exc).__name__}: "
                                   f"{exc}) — no boards come from it.")
            return
        self.reserved_ids |= {b.id for b in self.src_lib}
        for b in self.src_lib:
            b2 = replace(b, picture=self.repoint_picture(b.picture),
                         edging_kinds=list(b.edging_kinds))
            self.board_map[b.id] = self._place_board(b2)

    # -- runners --
    def runners(self):
        path = os.path.join(self.src, HARDWARE_FILE)
        if not os.path.exists(path):
            return
        try:
            self.src_rlib = H.load(path)
        except (OSError, ValueError, TypeError) as exc:
            self.plan.notes.append(f"{HARDWARE_FILE} could not be read ({type(exc).__name__}: "
                                   f"{exc}) — no runners come from it.")
            return
        reserved = {r.id for r in self.src_rlib}
        for r in self.src_rlib:
            self.runner_map[r.id] = self._place_runner(r, reserved)

    def _place_runner(self, r: H.Runner, reserved) -> str:
        for k, cand in enumerate(candidates(r.name)):
            if k == 0:
                same_id = H.find(self.rlib, r.id)
                same_nm = next((x for x in self.rlib if same_name(x.name, r.name)), None)
                if same_id is not None and _runner_record(same_id) == _runner_record(r):
                    self.plan.items.append(Item("runner", r.name, "identical", to=r.name,
                                                id=r.id, to_id=r.id))
                    self.runner_names[r.id] = r.name
                    return r.id
                if same_id is None and same_nm is None:
                    self.rlib.append(r)
                    self.plan.runners.append(r)
                    self.plan.items.append(Item("runner", r.name, "new", id=r.id, to_id=r.id))
                    self.runner_names[r.id] = r.name
                    return r.id
                continue
            have = next((x for x in self.rlib if same_name(x.name, cand)), None)
            if have is not None:
                if _runner_body(have) == _runner_body(r):
                    self.plan.items.append(Item("runner", r.name, "identical", to=have.name,
                                                id=r.id, to_id=have.id, note="imported before"))
                    self.runner_names[have.id] = have.name
                    return have.id
                continue
            pool = self.rlib + [H.Runner(id=i) for i in reserved]
            new = replace(r, id=H.next_id(pool, cand), name=cand, lengths=list(r.lengths))
            self.rlib.append(new)
            self.plan.runners.append(new)
            self.runner_names[new.id] = cand
            self.plan.items.append(Item("runner", r.name, "renamed", to=cand, id=r.id,
                                        to_id=new.id,
                                        note=f"a different {r.name} is already here"))
            return new.id
        raise AssertionError("unreachable")

    # -- the catalogue of cupboards (3 October 2026) --
    def cupboards(self):
        """The old folder's catalogue, brought across the way boards are: a
        record identical to one here (same name, any case, and the same
        cupboard once its board and runner ids are re-pointed) is skipped;
        a new name comes in; a different cupboard under a taken name comes in
        as `<name> (imported n)` — the text after the fixed prefix carrying the
        suffix, the same name-taken rule as everywhere."""
        path = os.path.join(self.src, CAT.CATALOGUE_FILE)
        if not os.path.exists(path):
            return
        try:
            src = CAT.load(path)
        except (OSError, ValueError, TypeError) as exc:
            self.plan.notes.append(f"{CAT.CATALOGUE_FILE} could not be read ({type(exc).__name__}: "
                                   f"{exc}) — no catalogue cupboards come from it.")
            return
        for rec in src:
            name = str(rec.get("name") or "")
            if not name:
                continue
            moved = self._repoint_record(rec)
            for k, cand_text in enumerate(candidates(str(rec.get("text") or ""))):
                cand = CAT.full_name(str(rec.get("prefix") or name), cand_text) if rec.get("prefix") else (
                    name if k == 0 else cand_text)
                have = CAT.find(self.cat, cand)
                if have is not None:
                    if _record_body(have) == _record_body(moved):
                        self.plan.items.append(Item("cupboard", name, "identical", to=have["name"],
                                                    note="" if k == 0 else "imported before"))
                        break
                    continue
                new = dict(moved, name=cand, text=" ".join(cand_text.split()))
                self.cat.append(new)
                self.plan.cupboards.append(new)
                self.plan.items.append(Item("cupboard", name, "new" if k == 0 else "renamed",
                                            to=cand if k else "",
                                            note="" if k == 0 else f"a different {name} is already here"))
                break

    def _repoint_record(self, rec: dict) -> dict:
        """A catalogue record with its board and runner ids as they are here."""
        d = json.loads(json.dumps(rec))
        fn = lambda b: self.board_map.get(b, b)                               # noqa: E731
        for c in [d.get("cabinet")] + list(d.get("panels") or []):
            if isinstance(c, dict):
                B.map_cabinet_board_ids(c, fn)
                if c.get("runner") in self.runner_map:
                    c["runner"] = self.runner_map[c["runner"]]
        d["boards"] = [dict(b, id=fn(b.get("id"))) for b in d.get("boards") or []]
        d["materials"] = {fn(k): v for k, v in (d.get("materials") or {}).items()}
        for rec_r in d.get("runners") or []:
            rec_r["id"] = self.runner_map.get(rec_r.get("id"), rec_r.get("id"))
        d["runner_records"] = {self.runner_map.get(k, k): v for k, v in (d.get("runner_records") or {}).items()}
        for v in d["materials"].values():
            if isinstance(v, dict) and v.get("picture"):
                v["picture"] = self.repoint_picture(v["picture"])
        return d

    # -- jobs --
    def _board_moves(self, job_name: str, materials: dict) -> Dict[str, str]:
        """old id -> id here, for one job: the library's renames, and any board
        whose own copy in this job would be refreshed into something else here."""
        moves = {}
        src_ids = {b.id for b in self.src_lib}
        for bid in list(materials or {}):
            if bid in self.board_map:
                if self.board_map[bid] != bid:
                    moves[bid] = self.board_map[bid]
                continue
            if bid in src_ids or not isinstance(materials.get(bid), dict):
                continue
            here = B.find(self.lib, bid)
            if here is None:
                continue
            rec = dict(material_record(materials, bid))
            rec["picture"] = self.repoint_picture(rec.get("picture"))
            fresh = B.to_material(here)
            if all(rec.get(f) == fresh.get(f) for f in B.LIVE_FIELDS):
                continue
            own = B.board_from_dict({
                "id": bid, "name": rec.get("name") or rec.get("board") or bid,
                "tape": rec.get("tape") or "", "thickness": rec.get("thickness", 16),
                "grain": rec.get("grain", "plain"), "price": rec.get("price") or 0,
                "picture": rec.get("picture") or "",
                "has_edging": rec.get("has_edging", True),
                "edging_kinds": rec.get("edging_kinds", list(B.TAPE_KINDS)),
                "colour": rec.get("colour", "")})
            moves[bid] = self._place_board(
                own, note_from=f"{job_name}'s own copy — {bid} here is {here.name}")
        return moves

    def _repoint_job(self, job: Job, moves: Dict[str, str]):
        for old, new in moves.items():
            B.rename_board_in_job(job, old, new)
        for rec in (job.materials or {}).values():
            if isinstance(rec, dict) and rec.get("picture"):
                rec["picture"] = self.repoint_picture(rec["picture"])
        rmoves = {o: n for o, n in self.runner_map.items() if o != n}
        if rmoves:
            if job.runners:
                job.runners = {rmoves.get(k, k): (dict(v, id=rmoves[k],
                                                       name=self.runner_names.get(rmoves[k],
                                                                                  v.get("name")))
                                                  if k in rmoves and isinstance(v, dict) else v)
                               for k, v in job.runners.items()}
            for c in job.cabinets:
                if c.runner in rmoves:
                    c.runner = rmoves[c.runner]

    def _repoint_raw(self, d: dict, moves: Dict[str, str]):
        """The same re-pointing on a newer version's raw JSON."""
        fn = lambda b: moves.get(b, b)                                       # noqa: E731
        if isinstance(d.get("materials"), dict):
            d["materials"] = {fn(k): v for k, v in d["materials"].items()}
            for rec in d["materials"].values():
                if isinstance(rec, dict) and rec.get("picture"):
                    rec["picture"] = self.repoint_picture(rec["picture"])
        if isinstance(d.get("boards"), list):
            d["boards"] = [fn(b) for b in d["boards"]]
        for c in d.get("cabinets") or []:
            B.map_cabinet_board_ids(c, fn)
        for p in d.get("loose") or []:
            if isinstance(p, dict) and p.get("material"):
                p["material"] = fn(p["material"])
        rmoves = {o: n for o, n in self.runner_map.items() if o != n}
        if rmoves:
            if isinstance(d.get("runners"), dict):
                d["runners"] = {rmoves.get(k, k): (dict(v, id=rmoves[k],
                                                        name=self.runner_names.get(rmoves[k],
                                                                                   v.get("name")))
                                                   if k in rmoves and isinstance(v, dict) else v)
                                for k, v in d["runners"].items()}
            for c in d.get("cabinets") or []:
                if isinstance(c, dict) and c.get("runner") in rmoves:
                    c["runner"] = rmoves[c["runner"]]

    def _here_text(self, name: str) -> List[str]:
        """A job file here, as it stands and as it reads after migration."""
        key = name.casefold()
        if key in self.planned_jobs:
            return [self.planned_jobs[key]]
        path = os.path.join(self.t.jobs_dir, self.job_names[key])
        out = []
        try:
            with open(path, encoding="utf-8") as fh:
                raw = fh.read()
            out.append(raw)
            out.append(_dumps(job_to_dict(job_from_dict(json.loads(raw)))))
        except (OSError, ValueError, TypeError, KeyError, AttributeError):
            pass
        return out

    def read_jobs(self):
        """Every job file in the old folder, read and migrated as Load reads one.
        First, so the ids they name are known before any new id is given out."""
        src_jobs = os.path.join(self.src, JOBS)
        self.parsed = []
        shipped = shipped_jobs(src_jobs)
        if shipped is None:
            self.plan.notes.append(NO_SHIPPED_LIST)
        elif isinstance(shipped, str):
            self.plan.notes.append(f"jobs\\{SHIPPED_FILE} could not be read ({shipped}) — "
                                   f"every job was considered.")
            shipped = None
        for fname in _job_files(src_jobs):
            if shipped is not None and fname.casefold() in shipped:
                # Ruling 2: never read, never imported — its board ids reserve nothing.
                self.plan.items.append(Item("job", fname[:-5], "shipped"))
                continue
            path = os.path.join(src_jobs, fname)
            try:
                with open(path, encoding="utf-8") as fh:
                    raw = json.load(fh)
                if not isinstance(raw, dict):
                    raise ValueError("the file is not a job (not a JSON object)")
                job = job_from_dict(raw)
                job_to_dict(job)
            except Exception as exc:                                  # noqa: BLE001
                self.plan.items.append(Item("job", fname[:-5], "broken",
                                            note=f"{type(exc).__name__}: {exc}"))
                continue
            self.parsed.append((fname, raw, job))
            self.reserved_ids |= set(job.materials or {}) | set(job.board_ids)

    def jobs(self):
        parsed = self.parsed
        for fname, raw, job in parsed:
            stem = fname[:-5]
            moves = self._board_moves(stem, job.materials)
            newer = unknown_fields(raw)
            if newer:
                body = json.loads(json.dumps(raw))
                self._repoint_raw(body, moves)
            else:
                self._repoint_job(job, moves)
                body = job_to_dict(job)
            note = ""
            if newer:
                shown = ", ".join(newer[:4]) + (" …" if len(newer) > 4 else "")
                note = (f"from a newer version of the app — brought in as it stands "
                        f"(fields this app does not know: {shown})")
            if moves:
                said = ", ".join(f"{o} → {n}" for o, n in moves.items())
                note = (note + "; " if note else "") + f"boards re-pointed: {said}"
            for k, cand in enumerate(candidates(stem, ".json")):
                key = cand.casefold()
                text = _dumps(dict(body, name=cand[:-5]) if k else body)
                if key in self.job_names or key in self.planned_jobs:
                    if text in self._here_text(cand if key not in self.job_names
                                               else self.job_names[key]):
                        self.plan.items.append(Item(
                            "job", stem, "identical", to=cand[:-5],
                            note="imported before" if k else ""))
                        break
                    continue
                self.planned_jobs[key] = text
                self.plan.jobs.append((cand, text))
                self.plan.items.append(Item(
                    "job", stem, "new" if k == 0 else "renamed", to=cand[:-5] if k else "",
                    note=((f"a different {stem} is already here; " if k else "") + note).strip("; ")))
                break


def scan(path: str, target: Target) -> dict:
    """The preview (ruling 4). Writes nothing. `{ok, plan}` with `plan` the
    `Plan`, or `{ok: False, error}` when the folder is not a Cupboard App one."""
    found = find_folder(path, own_root=target.root)
    if not found["ok"]:
        return found
    s = _Scanner(found["folder"], target)
    s.read_jobs()
    s.pictures()
    s.boards()
    s.runners()
    s.cupboards()
    s.jobs()
    order = {k: i for i, k in enumerate(KINDS)}
    s.plan.items.sort(key=lambda i: order[i.kind])
    return {"ok": True, "plan": s.plan}


# --- writing it -------------------------------------------------------------------

def _plural(n: int, kind: str) -> str:
    one, many = KIND_PLURAL[kind]
    return f"{n} {one if n == 1 else many}"


def report_text(rep: dict) -> str:
    """Ruling 8: one paragraph, fit to copy."""
    done = rep["imported"]
    # the four kinds as the line always read them; catalogue cupboards named
    # only when any came in (3 October 2026), so a report without them is
    # word for word what it was
    parts = [_plural(done[k], k) for k in KINDS if k != "cupboard" or done.get(k)]
    lines = []
    if any(done.values()):
        lines.append("Imported " + ", ".join(parts) + ".")
    else:
        lines.append("Nothing new to import.")
    if rep["identical"]:
        lines.append(f"Skipped {rep['identical']} identical.")
    if rep.get("shipped"):
        lines.append(f"Left out {_plural(len(rep['shipped']), 'job')} shipped with the demo: "
                     + ", ".join(rep["shipped"]) + ".")
    if rep["renamed"]:
        lines.append("Renamed: " + ", ".join(f"{a} → {b}" for a, b in rep["renamed"]) + ".")
    for name, why in rep["failed"]:
        lines.append(f"Not imported: {name} — {why}.")
    if rep["newer"]:
        lines.append("From a newer version of the app, imported as it stands: "
                     + ", ".join(rep["newer"]) + ".")
    for n in rep["notes"]:
        lines.append(n)
    return " ".join(lines[:3]) + ("\n" + "\n".join(lines[3:]) if len(lines) > 3 else "")


def run(path: str, target: Target, signature: str = "",
        test_load: Optional[Callable[[str], None]] = None) -> dict:
    """Write what the preview listed (ruling 4), and report (ruling 8).

    Scans again first: if the old folder no longer gives the preview's list
    (`signature`), nothing is written and it says so. Order: pictures, then
    the libraries, then each job — test-loaded first through `test_load`
    (the app's own Load path), and a job that will not load is NOT written
    and is named in the report with the reason.
    """
    got = scan(path, target)
    if not got["ok"]:
        return got
    plan = got["plan"]
    if signature and signature != plan.signature:
        return {"ok": False, "error": "The folder changed since the preview — Import "
                                      "project again to see what it holds now. Nothing "
                                      "was imported."}
    done = {k: 0 for k in KINDS}
    renamed, failed, newer, shipped = [], [], [], []
    if plan.pictures:
        os.makedirs(target.pictures_dir, exist_ok=True)
    for src, name in plan.pictures:
        shutil.copyfile(src, os.path.join(target.pictures_dir, name))
        done["picture"] += 1
    if plan.boards:
        lib = B.load(target.boards_path) if os.path.exists(target.boards_path) else []
        B.save(lib + plan.boards, target.boards_path)
        done["board"] += len(plan.boards)
    if plan.runners:
        rlib = H.load(target.hardware_path) if os.path.exists(target.hardware_path) else []
        H.save(rlib + plan.runners, target.hardware_path)
        done["runner"] += len(plan.runners)
    if plan.cupboards:
        cat = CAT.load(target.catalogue_path) if os.path.exists(target.catalogue_path) else []
        CAT.save(cat + plan.cupboards, target.catalogue_path)
        done["cupboard"] += len(plan.cupboards)
    written = set()
    if plan.jobs:
        os.makedirs(target.jobs_dir, exist_ok=True)
    for fname, text in plan.jobs:
        try:
            job = job_from_dict(json.loads(text))
            if test_load is not None:
                test_load(text)
            else:
                job.bind_runners()
        except Exception as exc:                                      # noqa: BLE001
            failed.append((fname, f"it would not load here ({type(exc).__name__}: {exc})"))
            continue
        with open(os.path.join(target.jobs_dir, fname), "w", encoding="utf-8") as fh:
            fh.write(text)
        written.add(fname[:-5])
        done["job"] += 1
    identical = 0
    for i in plan.items:
        if i.action == "identical":
            identical += 1
        elif i.action == "shipped":
            shipped.append(i.name + ".json")
        elif i.action == "broken":
            failed.append((i.name + ".json" if i.kind == "job" else i.name, i.note))
        elif i.action == "renamed":
            if i.kind != "job" or i.to in written:
                renamed.append((i.name, i.to))
        if i.kind == "job" and i.action in ("new", "renamed") and "newer version" in i.note:
            newer.append((i.to or i.name) + ".json")
    rep = {"imported": done, "identical": identical, "shipped": shipped, "renamed": renamed,
           "failed": failed, "newer": newer, "notes": list(plan.notes),
           "jobs": sorted(written)}
    rep["text"] = report_text(rep)
    return {"ok": True, "report": rep}
