"""Data model: panels, drawers, cabinets, jobs."""
from dataclasses import dataclass, field
from typing import Optional, List

from .standard import Standard, STANDARD


# Panel codes. 01-08 and 17-20 are Plazaboard's existing scheme.
# 09 is new: the old lists coded a divider as 08 in some cabinets and 99 in others.
CODES = {
    "01": "Side",
    "02": "Top",
    "03": "Bottom",
    "04": "Support",
    "05": "Shelve",
    "06": "Backing",
    "07": "Door",
    "08": "Exposed Panel",
    "09": "Divider",
    # both proposed, pending Plazaboard sign-off (Standard.codes_confirmed)
    "10": "Plinth",
    "11": "Filler",
    "17": "Drawer Base",
    "18": "Drawer Side",
    "19": "Drawer Front",
    "20": "Drawer Face",
}


# The board records a job was quoted with. A job keeps its own copy of every
# board it selected from the library (cabinetgen/boards.py), so editing the
# library never moves a quoted job — see "Price capture" in CLAUDE.md.
#
# Tape names are GENERATED from the board's tape token, one token for all three
# thicknesses: "PVC <token>", "1mm <token>", "2mm <token>". The token is its own
# field rather than the board's name because edging names are decided per
# order, and a long board description reaching an order as an edging name is
# finding D6/W10 in the other direction.
TAPE_PREFIX = {"pvc": "PVC", "1mm": "1mm", "2mm": "2mm"}
EXTERIOR_TAPES = ("1mm", "2mm")

MATERIALS = {
    "MEL": {
        "board": "SUPER WHITE MELAMINE CHIP 9X6X16MM",
        "name": "SUPER WHITE MELAMINE CHIP 9X6X16MM",
        "tape": "WHITE", "thickness": 16, "grain": "plain", "price": 575.0,
    },
    "BROOKHILL": {
        "board": "BROOKHILL FUSION CHIP",
        "name": "BROOKHILL FUSION CHIP",
        "tape": "WOOD", "thickness": 16, "grain": "grain", "price": 999.0,
    },
    "BACK": {
        "board": "IMPORTED WHITE DECOR 9X6X3MM",
        "name": "IMPORTED WHITE DECOR 9X6X3MM",
        # a 3 mm back is grooved in on all sides; it is never edged
        "tape": "WHITE", "thickness": 3, "grain": "plain", "price": 310.0,
    },
}


# Ids a board used to go by, old -> current. A board renamed in the library keeps
# its old id in every job saved before the rename (that is the price capture), so
# the old id has to keep resolving. `DECOR` became `BROOKHILL` on 18 September
# 2026; the October 2025 wardrobe still names `DECOR` on its bespoke and loose
# panels, and is frozen, so this is what keeps it one board rather than two.
BOARD_ALIASES = {"DECOR": "BROOKHILL"}


def resolve_board(materials: dict, key: str) -> str:
    """The id this job actually carries for `key`.

    The id itself when the job has it. Otherwise the other name of the same board
    if the job carries that one — a former id resolving to the current one, or
    the current one resolving to the former id an older job was quoted under. So
    a new cabinet (exterior BROOKHILL) in a job quoted under DECOR is cut from
    that job's DECOR, and the frozen October job's literal DECOR panels are cut
    from the house BROOKHILL: one board, one sheet pile, either way round.
    """
    mats = materials or {}
    if not key or key in mats:
        return key
    current = BOARD_ALIASES.get(key)
    if current and current in mats:
        return current
    for old, new in BOARD_ALIASES.items():
        if new == key and old in mats:
            return old
    return key


def material_record(materials: dict, key: str) -> dict:
    """One board's record, whatever shape the job file wrote it in.

    Three shapes have existed and all three still read. A bare string is the
    board description. A record with `pvc` / `2mm` keys is the mapped-tape shape
    that came before generation — its token is recovered by taking the mapped
    name apart, so a job written then still generates the tapes it was quoted
    with. Anything else is read as it stands.
    """
    key = resolve_board(materials, key)
    value = (materials or {}).get(key)
    if isinstance(value, str):
        known = MATERIALS.get(BOARD_ALIASES.get(key, key))
        if known and known["board"] == value:
            return known
        return {"board": value, "name": value}
    if not isinstance(value, dict):
        return {}
    if value.get("tape") or not any(k in value for k in ("pvc", "1mm", "2mm")):
        return value
    # the mapped-tape shape: "PVC WOOD" -> token "WOOD"
    out = dict(value)
    for kind, prefix in TAPE_PREFIX.items():
        mapped = value.get(kind, "")
        if mapped.startswith(prefix + " "):
            out["tape"] = mapped[len(prefix) + 1:]
            break
    if isinstance(out.get("grain"), int):
        out["grain"] = "grain" if out["grain"] else "plain"
    return out


def material_board(materials: dict, key: str) -> str:
    """The description the quote orders by."""
    rec = material_record(materials, key)
    return rec.get("name") or rec.get("board") or key


def material_token(materials: dict, key: str) -> str:
    """What this board's tape names are generated from."""
    rec = material_record(materials, key)
    return str(rec.get("tape") or rec.get("name") or rec.get("board") or "").strip()


def tape_for(materials: dict, key: str, thickness: str) -> str:
    """`PVC WOOD`, `2mm WOOD` ... generated, never mapped. '' when the board has
    nothing to generate from, which the validator names rather than guessing."""
    token = material_token(materials, key)
    return f"{TAPE_PREFIX[thickness]} {token}" if token else ""


def material_price(materials: dict, key: str) -> float:
    """What this job was quoted per board. 0 when the job never captured one."""
    try:
        return float(material_record(materials, key).get("price") or 0.0)
    except (TypeError, ValueError):
        return 0.0


def material_thickness(materials: dict, key: str) -> int:
    """The board's thickness. The engine assumes Standard.board_t throughout, so
    this exists to be checked against it, not to drive geometry (deferred)."""
    try:
        return int(material_record(materials, key).get("thickness") or 0)
    except (TypeError, ValueError):
        return 0


def grain_of(materials: dict, key: str) -> int:
    """Whether the board has a direction, which locks a panel's rotation.

    It belongs to the board, not to the job the panel is cut for: a Brookhill
    carcass side runs with the grain exactly as a Brookhill door does. Reading it
    off the panel's role instead is how 60 woodgrain panels went out at grain 0
    and only Plazaboard's counter caught it (W8 / D9). The library says Grain or
    Plain; an int is the shape the record had before the library existed.
    """
    value = material_record(materials, key).get("grain", 0)
    if isinstance(value, str):
        return 1 if value.strip().lower() == "grain" else 0
    return int(value or 0)


@dataclass
class Panel:
    cabinet: int
    code: str
    role: str
    material: str          # a board id: 'MEL' | 'BROOKHILL' | 'BACK' | ...
    length: int
    width: int
    qty: int = 1
    edge_l: int = 0
    edge_w: int = 0
    edge_material: str = ""
    pot_holes: int = 0     # per panel
    grain: int = 0
    note: str = ""

    @property
    def label(self) -> str:
        return f"{self.cabinet}{self.code}"

    def edging_m(self, std: Standard = STANDARD) -> float:
        return std.edging_m(self.length, self.width, self.edge_l, self.edge_w, self.qty)

    def area_mm2(self) -> int:
        return self.length * self.width * self.qty


@dataclass
class Drawer:
    """One drawer. face_height is the visible front; box_height is the box side height.

    `face_height` is the ordered figure and the only one the engine reads — what
    was ordered is still a list of heights. `mode` and `share` are the authoring
    recipe kept beside it so a stack can be picked up and re-divided later: a
    'fixed' row is the height as typed, a 'share' row takes its slice of whatever
    the fixed rows leave. Every job file written before the per-row modes existed
    loads as 'fixed' at the heights it already carried.
    """
    face_height: int
    box_height: int
    base: str = "board"          # 'board' (3 mm, grooved) | 'melamine' (16 mm, housed)
    mode: str = "fixed"          # 'fixed' (height as typed) | 'share' (a slice of the rest)
    share: float = 1.0           # the slice's weight, when mode is 'share'
    # Which board this one drawer's box and face are cut from, so one drawer in a
    # stack can take a different finish from the rest (18 September 2026). None
    # follows the cabinet — the box its carcass board, the face its exterior
    # board — which is how every job written before these reads.
    box_board: Optional[str] = None
    face_board: Optional[str] = None


@dataclass
class Support:
    """One line of cross supports.

    A support is a cross rail spanning the internal width (W - 32 x 100, code 04)
    that ties the two sides together. A row is a kind and a quantity, and the
    cabinet's total is the sum of its rows — there is no total to subtract from,
    which is what the three-number model got wrong: `edged + white` could exceed
    `supports` and the plain count went negative in silence.
    """
    edge: str = "front"    # 'front' (carcass tape) | 'white' (drawer-box tape) | 'none'
    qty: int = 1


SUPPORT_EDGES = ("none", "front", "white")


@dataclass
class Cabinet:
    number: int
    width: int
    height: int
    depth: int

    kind: str = "tall"           # 'tall' | 'upper' | 'base'  ('base' has no top panel)
    back: str = "four"           # 'four' | 'three' | 'none'
    template: str = "standard"   # 'standard' | 'none' (bespoke only — generate nothing)

    # Supports, as rows: a kind and a quantity each, summing to the total. Empty
    # means "read the three legacy numbers below", which is how every job written
    # before the rows does. See `support_list`.
    support_rows: List[Support] = field(default_factory=list)
    # The three-number model these replace. Kept as the migration source and
    # nothing else — once support_rows is set, these are not read.
    supports: int = 4
    edged_supports: int = 0      # front-edged, banded in the carcass tape
    white_supports: int = 0      # white-edged, banded in the drawer-box tape

    shelves: int = 0             # adjustable
    fixed_shelves: int = 0       # fitted, slightly deeper
    shelf_width: Optional[int] = None    # override when the interior is split by a divider

    divider_height: Optional[int] = None
    divider_count: int = 0

    doors: int = 0
    door_height: Optional[int] = None    # None = full height (H - 3)

    # Which edge each door leaf hangs from, facing the cabinet: 'L' or 'R', one
    # per leaf, top-level index 0 being the leftmost. Short or empty falls back
    # to the default rule (a single door follows Placement.flip, a pair hangs
    # from its outer edges), which is how every job predating the control reads.
    door_hinges: List[str] = field(default_factory=list)

    # The "Has doors" tickbox, the same thing "Has drawers" is for drawers. None
    # derives it from the count, which is how every job written before the box
    # reads. False keeps `doors` in the job file and builds nothing from it, so
    # re-ticking restores the doors rather than asking for them to be typed again.
    has_doors: Optional[bool] = None

    # Which board each leaf is cut from, one per leaf, index 0 being the
    # leftmost. Empty, short, or "" on a leaf falls back to `exterior_board`,
    # which is how every job predating the control reads. Two leaves cut from
    # different boards come out as two cut-list lines with distinct designations.
    door_boards: List[str] = field(default_factory=list)

    drawers: List[Drawer] = field(default_factory=list)
    # The "Has drawers" tickbox. None derives it from the list, which is how
    # every job written before the tickbox reads. False keeps the list in the
    # job file but builds nothing from it, so re-ticking restores the stack
    # rather than asking for it to be typed again.
    has_drawers: Optional[bool] = None

    exposed_sides: int = 0

    # ---- boards ------------------------------------------------------------
    # Two boards, each a key into Job.materials. The carcass board is what the
    # box is cut from — sides, top, bottom, supports, shelves and dividers — so a
    # decor or microwave cupboard with a Brookhill carcass is just a cabinet with
    # a different carcass board. The exterior board is what shows: doors, drawer
    # faces and exposed end panels. Each nests and prices as its own material.
    carcass_board: str = "MEL"
    exterior_board: str = "BROOKHILL"
    # The thin sheet the back (06) is cut from, and the grooved drawer base (17)
    # with it — they are the same board. It used to be reached for by the engine
    # rather than chosen, which is how a project could cut a board it had never
    # selected and quote it at R0. "BACK" is the default because that is the
    # board the engine always reached for, so every job written before this
    # names the board it was already using.
    back_board: str = "BACK"

    # Which exterior tape this cabinet takes, 1 mm or 2 mm. It changes the tape
    # ordered and what it costs, and nothing else: we supply finished sizes and
    # Plazaboard deducts the tape, so there is deliberately no dimensional effect
    # anywhere. The carcass tape is always the thin PVC and is not selectable.
    exterior_tape: str = "2mm"           # '1mm' | '2mm'

    # ---- edging, chosen in one place per section ---------------------------
    # A thickness and a colour, and the colour is a board — so the edging name is
    # still generated from that board's token exactly as every other one is, and
    # a board name can never reach an order as a tape. None on either half means
    # "follow the cabinet": the exterior tape thickness, and the exterior board's
    # colour. That is what every job written before these already had, so nothing
    # they were quoted with moves.
    door_edge_kind: Optional[str] = None      # '1mm' | '2mm' for the doors
    door_edge_board: Optional[str] = None     # board the door edging colour comes from
    drawer_edge_kind: Optional[str] = None    # '1mm' | '2mm' for the drawer faces
    drawer_edge_board: Optional[str] = None   # board the face edging colour comes from

    # The drawer box and the drawer face, each its own board. The box used to be
    # hardcoded MEL in the engine whatever the cabinet was cut from, which the
    # validator could only report after the fact. None follows the cabinet: the
    # box takes the carcass board, the face takes the exterior board.
    drawer_carcass_board: Optional[str] = None
    drawer_face_board: Optional[str] = None

    # ---- edge tapes: derived from the boards, overridable per cabinet -------
    # None means "derive it" (see carcass_tape / door_tape / drawer_box_tape).
    # A string is an override for this cabinet only. The three are kept separate
    # because they are genuinely different tapes: the door edge is 2 mm and the
    # carcass edge is thin PVC, same colour, different thickness and price.
    carcass_edge: Optional[str] = None
    door_edge: Optional[str] = None
    drawer_box_edge: Optional[str] = None

    bespoke: List[Panel] = field(default_factory=list)   # hand-specified extras
    note: str = ""

    # Plan outline, any shape, in the cabinet's own frame: x along the wall from
    # its left edge, y out from the wall face. Empty means "the rectangle its
    # panels make", which is right for every template cabinet. A corner unit's is
    # never typed — it is derived from the corner parameters below. width / depth
    # / height above are inputs to panel generation and labels for display — no
    # geometric check reads them; every check reads room.geometry.
    footprint: List[List[int]] = field(default_factory=list)

    # A corner unit is described, never drawn (ruled 14 Sept 2026): four
    # measurements and a style, and room.corner_outline derives its outline and
    # front faces. Frame: x along wall A from the cabinet's start, y out from wall
    # A; wall A is the face at y = 0, wall B the face at x = arm_a. There is no
    # angle field — a mitre's angle is an output of these four numbers.
    corner_style: str = ""               # '' | 'mitre' | 'ell'
    arm_a: Optional[int] = None          # how far the box runs along wall A
    arm_b: Optional[int] = None          # how far it runs along wall B
    face_a: Optional[int] = None         # open face on the wall-A side: depth of the run butting it
    face_b: Optional[int] = None         # open face on the wall-B side: likewise
    # The "Corner unit" tickbox. None derives it from the style, which is how
    # every job predating the tickbox reads. False keeps all four measurements
    # and the style in the job file but stops anything reading them.
    corner_unit: Optional[bool] = None

    # ---- what is actually live, once the tickboxes have had their say ------

    @property
    def corner_on(self) -> bool:
        """Whether the corner measurements drive this cabinet's plan outline."""
        if self.corner_unit is None:
            return bool(self.corner_style)
        return bool(self.corner_unit) and bool(self.corner_style)

    @property
    def door_count(self) -> int:
        """How many door leaves are actually built. Unticking "Has doors" keeps
        `doors` in the job file untouched — nothing here zeroes it."""
        return 0 if self.has_doors is False else int(self.doors or 0)

    def door_board(self, i: int) -> str:
        """The board leaf `i` is cut from — its own, or the cabinet's exterior."""
        chosen = self.door_boards[i] if 0 <= i < len(self.door_boards) else ""
        return chosen or self.exterior_board

    @property
    def drawer_carcass(self) -> str:
        """The board a drawer box is cut from: sides, fronts and a housed base."""
        return self.drawer_carcass_board or self.carcass_board

    @property
    def drawer_face(self) -> str:
        """The board a drawer face is cut from."""
        return self.drawer_face_board or self.exterior_board

    def box_board_of(self, d: "Drawer") -> str:
        """The board one drawer's box is cut from: its own, or the cabinet's."""
        return d.box_board or self.drawer_carcass

    def face_board_of(self, d: "Drawer") -> str:
        """The board one drawer's face is cut from: its own, or the cabinet's."""
        return d.face_board or self.drawer_face

    @property
    def drawer_list(self) -> List[Drawer]:
        """The drawers that are actually built. Unticking keeps `drawers` in the
        job file untouched — nothing here empties it."""
        return [] if self.has_drawers is False else list(self.drawers)

    @property
    def support_list(self) -> List[Support]:
        """The support rows that are actually built, in cut-list order.

        With rows set, they are it. With none, the three legacy numbers are read
        in the order the engine has always emitted them — plain, then front-edged,
        then white-edged — so a migrated cabinet cuts the same list in the same
        order. `plain` is clamped at zero exactly as the old `if plain > 0` did,
        and the validator names any cabinet whose numbers made it negative.
        """
        if self.support_rows:
            return [r for r in self.support_rows if r.qty > 0]
        plain = self.supports - self.edged_supports - self.white_supports
        rows = [Support("none", plain), Support("front", self.edged_supports),
                Support("white", self.white_supports)]
        return [r for r in rows if r.qty > 0]

    @property
    def support_total(self) -> int:
        """The sum of the rows. Nothing subtracts."""
        return sum(r.qty for r in self.support_list)

    @property
    def legacy_supports_negative(self) -> bool:
        """The three legacy numbers contradict each other: edged + white is more
        than the total, so the plain count they imply is below zero."""
        return (not self.support_rows
                and self.supports - self.edged_supports - self.white_supports < 0)

    # ---- tapes: the override if there is one, otherwise the board's ---------

    def carcass_tape(self, materials: dict) -> str:
        """PVC in the EXTERIOR board's colour. It bands the front edges of the
        sides, top and bottom, and the front edges of shelves and dividers, which
        were ruled to match the front rather than the box (14 Sept 2026)."""
        if self.carcass_edge is not None:
            return self.carcass_edge
        return tape_for(materials, self.exterior_board, "pvc")

    def door_tape(self, materials: dict) -> str:
        """The doors' edging, and an exposed end's: a thickness and a colour.

        Both are chosen in the Doors section; with neither chosen it is the
        cabinet's exterior tape thickness in the exterior board's colour, which
        is what this always was. The string override still wins where a job file
        carries one.
        """
        if self.door_edge is not None:
            return self.door_edge
        kind = self.door_edge_kind or self.exterior_tape
        if kind not in EXTERIOR_TAPES:
            kind = "2mm"
        return tape_for(materials, self.door_edge_board or self.exterior_board, kind)

    def drawer_face_tape(self, materials: dict) -> str:
        """The drawer faces' edging, chosen in the Drawers section.

        Its own thickness and colour. With neither chosen it falls through to the
        doors' choice and then to the cabinet's, so a job written before the two
        were separable is edged exactly as it was quoted.
        """
        if self.door_edge is not None:
            return self.door_edge
        kind = self.drawer_edge_kind or self.door_edge_kind or self.exterior_tape
        if kind not in EXTERIOR_TAPES:
            kind = "2mm"
        board = (self.drawer_edge_board or self.door_edge_board
                 or self.exterior_board)
        return tape_for(materials, board, kind)

    def drawer_box_tape(self, materials: dict) -> str:
        """PVC in the DRAWER CARCASS board's colour: drawer sides and fronts, and
        the white-edged supports. With no drawer carcass chosen that is the
        cabinet's carcass board, which is what it always was."""
        if self.drawer_box_edge is not None:
            return self.drawer_box_edge
        return tape_for(materials, self.drawer_carcass, "pvc")

    def drawer_box_tape_of(self, materials: dict, d: "Drawer") -> str:
        """PVC in one drawer's own box board colour — the same rule as
        drawer_box_tape, for a drawer whose box may differ from the cabinet's."""
        if self.drawer_box_edge is not None:
            return self.drawer_box_edge
        return tape_for(materials, self.box_board_of(d), "pvc")

    @property
    def needs_back_board(self) -> bool:
        """Whether anything on this cabinet is actually cut from the back board:
        a back, or a drawer on a grooved 3 mm base."""
        return self.back != "none" or any(d.base == "board" for d in self.drawer_list)

    def tapes(self, materials: dict) -> dict:
        return {"carcass_edge": self.carcass_tape(materials),
                "door_edge": self.door_tape(materials),
                "drawer_face_edge": self.drawer_face_tape(materials),
                "drawer_box_edge": self.drawer_box_tape(materials)}


def hinge_side(cab: Cabinet, i: int, leaves: int, flip: bool = False) -> str:
    """Which edge door leaf `i` of `leaves` hangs from, facing the cabinet: 'L' or 'R'.

    One function, so the elevation's hinge marks and the plan's swing arcs cannot
    disagree.

    A pair is not a choice: two leaves hang from their outer edges, left and
    right, always (ruled 18 September 2026). A single door is the choice — 'L' or
    'R' on the cabinet, or the placement's own handedness with none set. More
    than two leaves is a corner or bespoke unit, where the per-leaf choice still
    wins over the outer-edges rule.
    """
    if leaves == 2:
        return "L" if i == 0 else "R"
    chosen = cab.door_hinges[i] if 0 <= i < len(cab.door_hinges) else ""
    if chosen in ("L", "R"):
        return chosen
    if leaves <= 1:
        return "R" if flip else "L"
    return "L" if i < leaves / 2 else "R"


@dataclass
class Opening:
    """A hole in a wall. Sizes a filler or blocks a cabinet; nothing more."""
    kind: str              # 'door' | 'window' | 'arch'
    x: int                 # mm from wall start to the opening's left edge
    width: int
    sill: int = 0          # mm from floor
    head: int = 2100


@dataclass
class Obstruction:
    """Something on the wall face a carcass has to miss or be cut around."""
    kind: str              # 'plug' | 'isolator' | 'waste' | 'water' | 'pipe' | 'meter'
    x: int
    z: int                 # mm from floor to its centre
    width: int = 100
    height: int = 100
    proud: int = 0         # mm it stands off the wall face


@dataclass
class Wall:
    """One wall, measured on site.

    `offset_start` / `offset_end` are the perpendicular deviation from square at
    each corner, taken Room.offset_depth mm out from this wall's face. Zero is
    square; positive means the return wall opens away from the room. The corner
    angle follows from atan(offset / offset_depth).
    """
    id: str                # 'A', 'B', 'C' ... clockwise
    length: int            # measured tight against the wall
    offset_start: int = 0
    offset_end: int = 0
    openings: List[Opening] = field(default_factory=list)
    obstructions: List[Obstruction] = field(default_factory=list)


@dataclass
class Room:
    name: str
    # A required site measurement, deliberately without a default: the ceiling
    # check is only worth trusting against a real figure, so a room with no
    # ceiling blocks the export until one is measured.
    ceiling: Optional[int] = None
    offset_depth: int = 600    # depth at which the offsets were measured
    closed: bool = True        # walls form a loop
    walls: List[Wall] = field(default_factory=list)


@dataclass
class Placement:
    """Where one cabinet stands. Geometry lives in room.py, never here."""
    cabinet: int           # Cabinet.number
    wall: str              # Wall.id
    x: int                 # mm from wall start to the cabinet's left edge, facing the wall
    z: int = 0             # 0 stands on the floor, on its legs; above 0, a hung unit's underside
    flip: bool = False     # handedness for corner and asymmetric units
    layer: Optional[str] = None   # override; normally derived from kind and z


@dataclass
class GapChoice:
    """What to do about one gap between cabinets, or between a run and a corner.

    The app proposes a treatment; this records what was actually decided. It is
    never written automatically — a gap left undecided produces no panel and a
    validation warning, because a filler nobody asked for is how the wrong
    cut list gets sent.

    A gap is identified by what bounds it rather than by an index, so a decision
    survives cabinets moving along the wall.
    """
    wall: str
    after: Optional[int] = None    # cabinet to the left; None means the wall's start corner
    before: Optional[int] = None   # cabinet to the right; None means the wall's end corner
    layer: str = "base"
    treatment: str = ""            # 'filler' | 'blind' | 'open'; empty means undecided
    note: str = ""


@dataclass
class PlinthChoice:
    """Whether one run carries a plinth board.

    Opt-in, never assumed: the board is the operator's choice per run, whatever
    the job. The legs are under every standing carcass either way — this decides
    only whether a code-10 board is cut to cover them, and never moves a height.
    A run is named by its first cabinet, so if the run is
    broken up the choice is simply orphaned and no plinth is emitted — which is
    the safe way round, and the UI shows the run as unplinthed.
    """
    wall: str
    layer: str = "base"
    first: int = 0             # the run's first cabinet, which identifies it
    fitted: bool = True
    note: str = ""


@dataclass
class Job:
    name: str
    cabinets: List[Cabinet] = field(default_factory=list)
    loose: List[Panel] = field(default_factory=list)     # filler strips, spare panels
    std: Standard = STANDARD

    # room is optional and must stay so: room=None behaves exactly as before it existed
    room: Optional[Room] = None
    placements: List[Placement] = field(default_factory=list)
    gaps: List[GapChoice] = field(default_factory=list)
    plinths: List[PlinthChoice] = field(default_factory=list)

    # The boards this project selected out of the library, by id. Empty means
    # "whatever `materials` already carries", which is how every job written
    # before the library reads.
    boards: List[str] = field(default_factory=list)

    # board id -> the record this job was quoted with. A snapshot taken when the
    # board was selected, never a pointer at the library: editing a board's price
    # there changes what the next job costs and never what this one did.
    materials: dict = field(default_factory=lambda: {k: dict(v)
                                                     for k, v in MATERIALS.items()})

    @property
    def board_ids(self) -> List[str]:
        """The boards a cabinet may be cut from, in a stable order."""
        return list(self.boards) if self.boards else sorted(self.materials or {})
