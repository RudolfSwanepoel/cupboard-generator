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


ALL_KINDS = tuple(TAPE_PREFIX)                     # ('pvc', '1mm', '2mm')
NO_COLOUR = "#d9d6cf"      # a board nobody has coloured yet: neutral, not a finish


def material_offers(materials: dict, key: str) -> tuple:
    """The edging kinds this board offers, in the order PVC, 1mm, 2mm.

    Empty when the board has no edging ("Has Edging" unticked in the library).
    A record with neither key — every job written before the tickbox — offers
    all three, which is what it was quoted with, so nothing already priced moves.
    """
    rec = material_record(materials, key)
    if rec.get("has_edging") is False:
        return ()
    kinds = rec.get("edging_kinds")
    if kinds is None:
        return ALL_KINDS
    return tuple(k for k in ALL_KINDS if k in kinds)


def material_has_edging(materials: dict, key: str) -> bool:
    return bool(material_offers(materials, key))


def material_colour(materials: dict, key: str) -> str:
    """The board's on-screen colour, '#rrggbb'. Read from the job's copy of the
    library record and from nowhere else; a board with none is neutral."""
    return str(material_record(materials, key).get("colour") or "") or NO_COLOUR


def is_thin(materials: dict, key: str) -> bool:
    """A sheet too thin to build a carcass, a door or a drawer from — the 3 mm
    backing. The threshold is the one `export_plaza.cut_rate` already sorts by
    (the masonite saw takes the 3 mm, the beam saw the rest), so the dropdowns
    and the costing agree about what a thin board is."""
    return material_thickness(materials, key) <= 3


def tape_for(materials: dict, key: str, thickness: str) -> str:
    """`PVC WOOD`, `2mm WOOD` ... generated, never mapped. '' when the board does
    not offer that edging, or has nothing to generate a name from — either way the
    validator names it rather than guessing."""
    token = material_token(materials, key)
    if not token or thickness not in material_offers(materials, key):
        return ""
    return f"{TAPE_PREFIX[thickness]} {token}"


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
    edge: str = "front"    # legacy: 'front' | 'white' | 'none'. See `board`/`kind`.
    qty: int = 1
    # What this row is edged in, said outright (20 September 2026): any board the
    # project has selected, and any edging kind THAT board offers on the Boards
    # tab. Both blank means the row predates the control and is read from `edge`,
    # so every job written before it is edged exactly as it was quoted.
    board: str = ""        # EDGING COLOUR. '' = derive from `edge`
    kind: str = ""         # '' = derive from `edge`; otherwise 'pvc' | '1mm' | '2mm'
    # What the rail itself is CUT FROM (20 September 2026). The single Board
    # column before this set only the edging colour, so picking the white board
    # to get a white edge also meant asking for a white rail — it did not give
    # one, and the two questions are now asked separately. Blank follows the
    # cabinet's carcass board, which is what a support has always been cut from.
    cut_board: str = ""


SUPPORT_EDGES = ("none", "front", "white")

# What a legacy "white-edged" support row was asking for.
#
# Edging is no longer stated anywhere but the Boards record (20 September 2026),
# so this is NOT an answer any more — nothing returns it as an edging name. It
# is kept as the description of what such a row meant, and `white_edge_board`
# finds the project board that actually means it. Every job written so far
# carries the white melamine that does, so none of them move.
WHITE_EDGE = "PVC WHITE"
WHITE_TOKEN = "WHITE"      # the token a legacy 'white' row was always asking for


def white_edge_board(materials: dict, prefer: str = "") -> str:
    """The board a legacy 'white-edged' support row resolves to.

    The first board in the project that offers PVC under the token WHITE — which
    for every job written so far is the white melamine the row already meant, so
    nothing quoted moves. '' when the project has no such board, and then the
    caller falls back to WHITE_EDGE and the validator says why.
    """
    keys = list(materials or {})
    if prefer and prefer in keys:
        keys = [prefer] + [k for k in keys if k != prefer]
    for key in keys:
        if ("pvc" in material_offers(materials, key)
                and material_token(materials, key).strip().upper() == WHITE_TOKEN):
            return key
    return ""


# The cut-list code an independent panel takes. Ruled 20 September 2026 (Q2):
# code 08, the existing Exposed Panel, with the role "Panel". Plazaboard's CSV
# writes the Component column from `Panel.label` alone - the digits, e.g. 1508 -
# so a new code would have to be signed off with them exactly as 10 and 11 still
# have to be, and it would say nothing on the order that 08 does not. The role
# is what tells the two apart in the app's own cut list. One constant, so a code
# they do sign off later is one edit.
PANEL_CODE = "08"

PANEL_ORIENTATIONS = ("upright", "flat", "end")


@dataclass
class PanelSpec:
    """An independent panel: one part, cut and numbered on its own.

    Not part of any cupboard. Rudolf builds bulkheads out of several of them -
    a front upright, an underside flat, an end cap each side - and each is its
    own numbered item on the cut list, so they are described here rather than
    hung off a cabinet.

    `a` and `b` are the two typed extents, and which physical direction each one
    is depends on the orientation (the editor labels them per orientation):

        upright   a = along the wall,   b = height        (facing the room)
        flat      a = along the wall,   b = out from wall (horizontal)
        end       a = out from the wall, b = height       (upright, side-on)

    These are FINISHED CUT SIZES - what Plazaboard cuts, not a rough size.
    The third extent is the board's own thickness, which is why a panel never
    states one.

    `grain_along` names which of the two the grain runs along, and only means
    anything on a grained board: the cut list's `Length` IS the grain direction,
    so it is what decides which extent becomes the length and locks the nester.
    """
    board: str = ""
    orientation: str = "upright"       # 'upright' | 'flat' | 'end'
    a: int = 0
    b: int = 0
    grain_along: str = "b"             # 'a' | 'b' - only read on a grained board
    edge_kind: str = ""                # '' = no edging asked for
    edge_board: str = ""               # '' = the panel's own board
    edge_long: int = 0                 # how many of the two LONG edges are banded
    edge_short: int = 0                # how many of the two SHORT edges are banded
    # RESERVED, and nothing reads it. Ruled 20 September 2026: a panel stays
    # where it is put and does not follow a cabinet. The field is the seam for
    # the day that changes, and is written to the job file only when set.
    anchor: Optional[str] = None


@dataclass
class Cabinet:
    number: int
    width: int
    height: int
    depth: int

    # 'tall' | 'upper' | 'base' ('base' has no top panel) | 'panel' (not a
    # cupboard at all: an independent panel, see `is_panel` and PanelSpec)
    kind: str = "tall"
    back: str = "four"           # 'four' | 'three' | 'none'
    # 'standard' | 'none' (bespoke only — generate nothing)
    # A panel is NOT a template: see `is_panel`, which reads `kind`. This field
    # is never rewritten when an item's kind changes, so switching to Panel and
    # back leaves a bespoke cabinet bespoke and a standard one standard.
    #
    # A panel is a Cabinet so that it reuses the numbering, the save and load,
    # the cabinet table, the placement record and the one generate_job loop —
    # which is where the cost, the nesting and the CSV come from for free. What
    # it costs is that every place assuming "a cabinet is a box with doors" has
    # to say what it does about panels; `is_panel` is what they ask.
    template: str = "standard"

    # Supports, as rows: a kind and a quantity each, summing to the total. Empty
    # means "read the three legacy numbers below", which is how every job written
    # before the rows does. See `support_list`.
    support_rows: List[Support] = field(default_factory=list)
    # The three-number model these replace. Kept as the migration source and
    # nothing else — once support_rows is set, these are not read.
    supports: int = 4
    edged_supports: int = 0      # front-edged, banded in the carcass tape
    white_supports: int = 0      # white-edged, banded in PVC WHITE

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
    #
    # LEGACY DEFAULTS (audited 20 September 2026, kept deliberately). These three
    # ids are read by the frozen October fixture and by every job file written
    # before the boards were chosen, so they stay. Nothing that CREATES a cabinet
    # now relies on them — the editor's `blankCabinet` sends blanks and the user
    # picks in Structure — and no new code should: ask the job what it carries
    # (`Job.board_ids`, `Job.materials`), never assume these names exist.
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

    # The panel record, when this item is a panel rather than a cupboard. None
    # on every cabinet, and written to the job file only when it is not — so a
    # job with no panels reads and writes exactly as it did before they existed.
    panel: Optional[PanelSpec] = None

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
    def is_panel(self) -> bool:
        """Whether this item is an independent panel rather than a cupboard.

        Read off `kind`, and off nothing else. The design note proposed carrying
        it on `template` as well; it cannot be, safely. Switching an item's kind
        back from Panel would then have to put `template` back to what it was,
        and there is nothing to put it back from: October cabinets 3 and 5 are
        `template="standard"` carrying hand-specified extras, so "it has bespoke
        panels, therefore it was bespoke" is wrong, and being wrong there
        rewrites a real cut list.

        Off `kind` alone, nothing is lost. Switch to Panel and back and every
        field is exactly where it was, `template` included, which is the same
        bargain the two tickboxes strike.

        Declared width/height/depth on a panel are labels only; its real size is
        its panel record, read through `room.geometry`.
        """
        return self.kind == "panel"

    @property
    def panel_spec(self) -> "PanelSpec":
        """The panel record, or an empty one. A panel with nothing typed into it
        yet is a zero-sized panel the validator names, not a crash."""
        return self.panel or PanelSpec()

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

    # ---- which fields hold a board -----------------------------------------
    #
    # ONE list, and everything that renames, swaps, un-selects or audits a board
    # reads it. There used to be four hand-written lists and they disagreed:
    # a swap moved only the carcass and exterior, un-selecting checked only
    # those plus the drawer boards, and the library scan missed the back, the
    # door leaves and the edging boards — so a board could be swapped or taken
    # out of a project while a cabinet still pointed at it, and the cut list
    # quietly named a board the project no longer had.
    #
    # A board field added to `Cabinet` and not added here is what
    # `tools/check_single_source.py` fails on.

    def _board_slots(self):
        """Every place this cabinet names a board, as `(label, get, set, hand)`.

        The label is what a message says out loud — "door leaf 2 board",
        "drawer 1 face board" — so a refusal can name the thing to go and change.

        `hand` marks a HAND-SPECIFIED panel: a bespoke panel names its own
        material, panel by panel, and `generate_job` puts it on the cut list
        exactly as the job defines it. It counts as naming the board — it has to,
        or the board could be deleted from the library or un-selected from the
        project out from under it — but a caller that is changing what things are
        cut from can leave it alone. See `map_board_refs`.
        """
        slots = []

        def simple(attr, label):
            slots.append((label,
                          lambda a=attr: getattr(self, a, "") or "",
                          lambda v, a=attr: setattr(self, a, v), False))

        simple("carcass_board", "carcass board")
        simple("exterior_board", "exterior board")
        simple("back_board", "backing board")
        simple("drawer_carcass_board", "drawer carcass board")
        simple("drawer_face_board", "drawer face board")
        simple("door_edge_board", "door edging board")
        simple("drawer_edge_board", "drawer edging board")
        for i in range(len(self.door_boards or [])):
            slots.append((f"door leaf {i + 1} board",
                          lambda i=i: self.door_boards[i] or "",
                          lambda v, i=i: self.door_boards.__setitem__(i, v), False))
        for i, d in enumerate(self.drawers or []):
            for attr, what in (("box_board", "box"), ("face_board", "face")):
                slots.append((f"drawer {i + 1} {what} board",
                              lambda d=d, a=attr: getattr(d, a, "") or "",
                              lambda v, d=d, a=attr: setattr(d, a, v), False))
        for i, r in enumerate(self.support_rows or []):
            slots.append((f"support row {i + 1} board",
                          lambda r=r: r.cut_board or "",
                          lambda v, r=r: setattr(r, "cut_board", v), False))
            slots.append((f"support row {i + 1} edging board",
                          lambda r=r: r.board or "",
                          lambda v, r=r: setattr(r, "board", v), False))
        if self.panel is not None:
            slots.append(("panel board",
                          lambda: self.panel.board or "",
                          lambda v: setattr(self.panel, "board", v), False))
            slots.append(("panel edging board",
                          lambda: self.panel.edge_board or "",
                          lambda v: setattr(self.panel, "edge_board", v), False))
        for p in (self.bespoke or []):
            slots.append((f"bespoke panel {p.label}",
                          lambda p=p: p.material or "",
                          lambda v, p=p: setattr(p, "material", v), True))
        return slots

    def board_refs(self, hand=True):
        """Every board id this cabinet names, as `(board_id, label)`.

        A blank slot is "follow Structure", not a name, so it is not reported.
        `hand=False` leaves out hand-specified bespoke panels.
        """
        return [(get(), label) for label, get, _, h in self._board_slots()
                if get() and (hand or not h)]

    def board_ids_used(self):
        """Just the ids, deduped, in the order they are named."""
        out = []
        for key, _ in self.board_refs():
            if key not in out:
                out.append(key)
        return out

    def map_board_refs(self, fn, hand=True) -> list:
        """Rewrite every board this cabinet names through `fn(board_id)`.

        Returns the labels that actually changed. Rename and swap both go
        through here, so neither can miss a field the other remembers.

        `hand` is what they differ on, and deliberately:

        * a RENAME says "this board is called something else now", so every
          reference has to follow it, hand-specified panels included — leaving
          one behind would point it at an id the library no longer has;
        * a SWAP says "cut this from a different board", and a bespoke panel's
          material was typed out panel by panel for a reason. On the October job
          that is eight panels and R848 of Brookhill, so it is not something to
          change on the way past.
        """
        hit = []
        for label, get, put, h in self._board_slots():
            if h and not hand:
                continue
            old = get()
            if not old:
                continue
            new = fn(old)
            if new and new != old:
                put(new)
                hit.append(label)
        return hit

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
        return tape_for(materials, self.door_edge_colour_board, kind)

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
        return tape_for(materials, self.drawer_face_edge_colour_board, kind)

    @property
    def door_edge_colour_board(self) -> str:
        """Which board the doors' edging takes its COLOUR from — its own choice,
        or the cabinet's exterior board. One chain, so the tape name the cut list
        carries and the band the drawing puts round a door leaf cannot name two
        different boards."""
        return self.door_edge_board or self.exterior_board

    @property
    def drawer_face_edge_colour_board(self) -> str:
        """The same, for drawer faces: their own choice, then the doors', then the
        cabinet's exterior board."""
        return (self.drawer_edge_board or self.door_edge_board
                or self.exterior_board)

    def drawer_box_tape(self, materials: dict) -> str:
        """PVC in the DRAWER CARCASS board's colour: drawer sides and fronts, and
        the white-edged supports. With no drawer carcass chosen that is the
        cabinet's carcass board, which is what it always was."""
        if self.drawer_box_edge is not None:
            return self.drawer_box_edge
        return tape_for(materials, self.drawer_carcass, "pvc")

    def support_row_cut_board(self, row: "Support") -> str:
        """What the rail itself is cut from.

        Its own choice when it has one, otherwise the cabinet's carcass board —
        which is what the engine has always cut a support from, so a row written
        before this control cuts exactly what it always cut.
        """
        return row.cut_board or self.carcass_board

    def support_row_board(self, materials: dict, row: "Support") -> str:
        """Which board a support row is edged in the COLOUR of.

        Its own choice when it has one. For a row written before the control,
        the legacy meaning of `edge`: front-edged faces the front and takes the
        exterior board (PVC in the exterior colour, the 14 September rule),
        white-edged takes whichever board in the project is the white one.

        With nothing stored and no legacy meaning either, the default is the
        board the rail is cut from — its own edging, which is the answer that
        needs no second thought when a row is added.
        """
        if row.board:
            return row.board
        if row.edge == "front":
            return self.exterior_board
        if row.edge == "white":
            return white_edge_board(materials)
        return self.support_row_cut_board(row)

    def support_row_kind(self, row: "Support") -> str:
        """Which edging kind a support row asks for. '' means none."""
        if row.kind:
            return row.kind
        return "pvc" if row.edge in ("front", "white") else ""

    def support_row_tape(self, materials: dict, row: "Support") -> str:
        """The edging on one row of supports, read from the Boards record.

        A row that names a board and a kind is that board's name for that kind,
        and nothing else — '' if the board no longer offers it, which the
        validator reports rather than substituting something.

        A row that names neither predates the control and keeps exactly what it
        was quoted with: front-edged takes the carcass edging (PVC in the
        exterior colour), white-edged resolves to the project's white board, and
        falls back to the constant only when the project has no such board.
        """
        kind = self.support_row_kind(row)
        if not kind:
            return ""
        # Through a BOARD, never through a constant: no edging is stated anywhere
        # but the Boards record (20 Sept 2026). With no board to mean it there is
        # no name to give, and the validator names the row rather than putting a
        # tape on the order that no board in the project sells.
        board = self.support_row_board(materials, row)
        return tape_for(materials, board, kind) if board else ""

    def support_tape(self, materials: dict, edge: str) -> str:
        """The edging a legacy row of the given kind gets. Kept for the callers
        that ask by `edge` rather than by row."""
        return self.support_row_tape(materials, Support(edge=edge, qty=1))

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
