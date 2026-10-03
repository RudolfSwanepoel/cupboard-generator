"""Data model: panels, drawers, cabinets, jobs."""
import math
from dataclasses import dataclass, field, replace
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
    # Edging Name BROOKHILL, as the library record has it (ruled 28 September
    # 2026). The October order's sheet said "WOOD"; Plazaboard keyed it as
    # Brookhill (their CSV: PVC BROOKHILL, 2MM BROOKHILL; the quote:
    # EDGING-IMP BROOKHILL), and the job now reads BROOKHILL. The metres per
    # kind, and so the cost, are exactly what they were.
    "BROOKHILL": {
        "board": "BROOKHILL FUSION CHIP",
        "name": "BROOKHILL FUSION CHIP",
        "tape": "BROOKHILL", "thickness": 16, "grain": "grain", "price": 999.0,
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
    """`PVC BROOKHILL`, `2mm Grey` ... generated, never mapped: the kind, then the
    board's Edging Name exactly as typed on the Boards tab, case included. ''
    when the board does not offer that edging, or has nothing to generate a name
    from — either way the validator names it rather than guessing."""
    token = material_token(materials, key)
    if not token or thickness not in material_offers(materials, key):
        return ""
    return f"{TAPE_PREFIX[thickness]} {token}"


def edging_label(materials: dict, key: str) -> str:
    """What an Edging Colour dropdown shows for a board: its Edging Name, the
    very text the order carries after the kind (ruled 28 September 2026).

    Where another board in the project has the same Edging Name — WHITEMEL and
    BACK are both WHITE — the id follows in brackets, `WHITE (WHITEMEL)`, so the
    two can be told apart. The stored value is still the board id; only what is
    shown changes. A board with no Edging Name shows its id.
    """
    token = material_token(materials, key)
    if not token:
        return key
    same = [k for k in (materials or {})
            if k != key and material_token(materials, k).upper() == token.upper()]
    return f"{token} ({key})" if same else token


def edging_parts(name: str):
    """A typed edging name taken apart: (kind, the rest), kind one of
    TAPE_PREFIX's keys, matched without regard to case (Plazaboard key `2MM`).
    (None, name) when it starts with no kind this app knows."""
    head, _, rest = str(name or "").strip().partition(" ")
    for kind, prefix in TAPE_PREFIX.items():
        if head.upper() == prefix.upper() and rest.strip():
            return kind, rest.strip()
    return None, str(name or "")


def resolve_edging(materials: dict, name: str, beside: str) -> str:
    """A TYPED edging name — a bespoke or loose panel's `edge_material` — read
    through the Boards record, as every generated edging is (28 September 2026).

    Its kind is kept. Its colour is the project board whose Edging Name it
    carries (case aside), written exactly as that board has it; a name that
    matches no project board's Edging Name — the October job's `2mm WOOD`, a
    name that order's sheet used and no board carries — is read as the same
    kind in `beside`, the board it was cut beside (the cabinet's exterior
    board, which is what front edges take). '' when that board does not offer
    the kind, which the validator then names. Blank, and anything that does not
    start with a kind, comes back as it is.
    """
    kind, token = edging_parts(name)
    if kind is None:
        return name
    named = [key for key in (materials or {})
             if material_token(materials, key).upper() == token.upper()]
    for key in named:
        got = tape_for(materials, key, kind)
        if got:
            return got
    if named:
        return ""           # the board it names does not offer the kind
    return tape_for(materials, beside, kind) if beside else name


def panel_signature(p: "Panel") -> tuple:
    """What makes two cut-list lines the SAME panel: everything but the qty —
    board, size, grain, banded-edge counts, pot holes and edging name (ruled 28
    September 2026). Lines with one signature share a designation; one code
    over several signatures is lettered at birth (engine.born_distinct), and
    the D13 warning is the same question asked of the finished list."""
    return (p.material, p.length, p.width, p.grain, p.edge_l, p.edge_w,
            p.pot_holes, p.edge_material)


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
    # None is AUTO (29 September 2026, ruled by Rudolf): the tallest box that
    # fits its face at its offset — `drawer_layout`'s `max_box`, face less
    # offset — read through `Cabinet.box_height_of`, so it follows the face when
    # Share or a preset moves it. A typed figure is kept as typed; every job
    # saved before Auto carries one. Written as `null` only when Auto.
    box_height: Optional[int]
    # 'board' (3 mm, grooved) | 'melamine' (16 mm, housed). None follows the
    # cabinet's `drawer_base`, then 'board' (29 September 2026); every saved
    # job's typed base stays as typed. None is written as nothing.
    base: Optional[str] = None
    mode: str = "fixed"          # 'fixed' (height as typed) | 'share' (a slice of the rest)
    share: float = 1.0           # the slice's weight, when mode is 'share'
    # Which board this one drawer's box and face are cut from, so one drawer in a
    # stack can take a different finish from the rest (18 September 2026). None
    # follows the cabinet — the box its carcass board, the face its exterior
    # board — which is how every job written before these reads.
    box_board: Optional[str] = None
    face_board: Optional[str] = None
    # An INNER drawer (28 September 2026): it sits behind the cabinet's door,
    # and its face is the size of the box's own carcass so the box sides are
    # hidden — face width = the box's outside width (opening - 2 x the runner
    # clearance), face height = box height, still a code-20 line off its face
    # board. The face front is on the shelves' line, flush with the carcass
    # front edges (ruled by Rudolf: "the same as the recess for shelves"), so
    # the box starts a face thickness behind it. No face-stack arithmetic
    # applies: `z` is where its box bottom stands above the carcass underside,
    # typed per drawer, generated equally spaced from the bottom
    # (`room.inner_drawer_z`) whenever the count changes, and None reads that
    # default. A cabinet's drawers are all inner or all outer (ruled). Both
    # fields are written to the job file only on an inner drawer.
    inner: bool = False
    z: Optional[int] = None
    # How far an OUTER drawer's box bottom stands above its own face's bottom
    # (ruled by Rudolf, 28 September 2026: faces lead, boxes follow). None is
    # the default, `room.drawer_rise` — 21, the bottom panel plus the runner's
    # lift, so the bottom box's runner stands on the bottom panel. Editable per
    # drawer: the bottom drawer may be raised, never lowered below 21; an upper
    # one may go either way. Whatever it is, the box must lie within its own
    # face's height (`drawer-box-face`). Not read on an inner drawer, whose face
    # is its box. Written to the job file only when set.
    offset: Optional[int] = None
    # Which board this drawer's box sides (18) and fronts (19) are EDGED in the
    # colour of (29 September 2026, ruled by Rudolf). None is the default, the
    # cabinet's EXTERIOR board — not the box board — for every drawer, the
    # October job's included, because that is what Plazaboard keyed and cut.
    # None follows the cabinet's `drawer_box_edge_board`, then the exterior
    # board. The name comes off the board's record through `tape_for`. Written
    # to the job file only when set.
    box_edge_board: Optional[str] = None
    # How thick that edging is: 'pvc' | '1mm' | '2mm', from what the board
    # offers (29 September 2026, ruled by Rudolf, REVERSING the same day's
    # "always PVC"). None follows the cabinet's `drawer_box_edge_kind`, then
    # PVC, so nothing quoted moves. Written to the job file only when set.
    box_edge_kind: Optional[str] = None


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
    # WHICH support this row is (27 September 2026, shelves-and-supports spec):
    # 'front' (flat, at the top front of a base unit, 0 or 1), 'top_rear' (flat,
    # at the top back of a base unit, 0 or 1) or 'back' (upright in the cavity
    # behind the backing, 0..n). '' means the row predates the types — a legacy
    # row, cut EXACTLY as it always was and only PLACED for drawing by the
    # legacy rule in `room.support_layout`. Nothing converts a legacy row.
    type: str = ""
    # Which edges of a typed row are banded, chosen edge by edge: any of
    # SUPPORT_EDGE_NAMES. None means the type's default — the front long edge
    # (`SUPPORT_DEFAULT_EDGES`); [] means none. The cut list records the counts
    # (edge_l = long edges, edge_w = ends), exactly as before. A legacy row keeps
    # its one long edge and never reads this.
    edges: Optional[List[str]] = None


SUPPORT_EDGES = ("none", "front", "white")


@dataclass
class Shelf:
    """One shelf of a straight carcass (the shelves brief, 3 October 2026).

    Shelves are rows, like drawers; "fixed vs adjustable" is gone. A row says
    where it is drawn, how far it stops short of the back, and what it is edged
    in. It is always cut from the carcass board, across the internal width (or
    `Cabinet.shelf_width`), code 05, role Shelve.

    `height` — top face of the bottom panel to the top face of the shelf, mm.
    DRAWING AND 3D ONLY: shelves are set at fitment, and a height never moves
    a cut line. None means its equal-spacing slot (`room.shelf_layout`).
    `clearance` — at the FACE, between the shelf's front edge and the carcass
    front: depth = the distance from the carcass front to the front face of the
    back, less this (`Standard.shelf_depth`). A smaller clearance is a deeper
    shelf. The ruled 4 (adjustable) and 1 (fixed) are what a migrated row reads.
    `kind` / `board` — its edging kind and colour board; blank is today's default,
    PVC in the exterior board's colour (`Cabinet.carcass_tape`).
    `long` / `short` — how many long edges (front and rear) and ends are banded:
    long 1 is the front edge, 2 both; short 1 the left end, 2 both — the rule
    `support_edges_for_counts` already states. The default is the front edge.
    `note` — "fixed" on a row migrated from `fixed_shelves`, so the cut-list line
    reads exactly as it did; typed rows carry none.
    """
    height: Optional[int] = None
    clearance: int = 4
    kind: str = ""
    board: str = ""
    long: int = 1
    short: int = 0
    note: str = ""

# The three support types, in cut-list order, and where each is offered.
# Front and Top Rear are flat rails at the top of a BASE unit, which has no top
# panel to tie the sides at the top; a tall or wall unit has a top and takes
# Back supports only. A mitre and an ell take none (RULES W13).
SUPPORT_TYPES = ("front", "top_rear", "back")
# What a person reads. The stored type 'front' is shown as "Top Front" (28
# September 2026) — it is the flat rail at the TOP front, beside the Top Rear.
# The stored value and every check id stay as they were.
SUPPORT_TYPE_LABEL = {"front": "Top Front", "top_rear": "Top Rear", "back": "Back"}
# The four edges of a support, in the row's own terms: the two long edges and
# the two ends. On a flat rail 'front' faces the room and 'rear' the wall; on an
# upright Back support 'front' is the long edge facing INTO the cabinet (down on
# Back 1, up on the rest) and 'rear' the one against the top or bottom panel.
SUPPORT_EDGE_NAMES = ("front", "rear", "left", "right")
SUPPORT_LONG_EDGES = ("front", "rear")
SUPPORT_DEFAULT_EDGES = ("front",)


def support_edges_of(row: "Support") -> List[str]:
    """The edges a typed row bands: its own list, or the type's default."""
    if row.edges is None:
        return list(SUPPORT_DEFAULT_EDGES)
    return [e for e in row.edges if e in SUPPORT_EDGE_NAMES]


def support_edges_for_counts(long: int, short: int) -> List[str]:
    """The canonical edges for a count of long edges and ends — the same two
    numbers Panel design asks for (28 September 2026). The rule, decided here
    and nowhere else:

        long 1   the row's 'front' long edge: the room-facing edge of a Top
                 Front or Top Rear, and on a Back the edge facing INTO the
                 cabinet — down on Back 1, up on every other Back (which is
                 what 'front' already means on a Back)
        long 2   both long edges
        short 1  the left end
        short 2  both ends

    >>> support_edges_for_counts(1, 0)
    ['front']
    >>> support_edges_for_counts(2, 1)
    ['front', 'rear', 'left']
    """
    long = max(0, min(2, int(long or 0)))
    short = max(0, min(2, int(short or 0)))
    return list(SUPPORT_LONG_EDGES[:long]) + ["left", "right"][:short]


def support_edges_canonical(row: "Support") -> bool:
    """Whether a typed row's stored edges are the canonical set for its own
    counts. One that is not (a rear edge alone, say) is KEPT and drawn as
    stored until a count is changed; the editor says so under the row."""
    got = support_edges_of(row)
    longs = sum(1 for e in got if e in SUPPORT_LONG_EDGES)
    return sorted(got) == sorted(support_edges_for_counts(longs, len(got) - longs))


def default_support_kind(materials: dict, board: str) -> str:
    """The edging kind a NEW support row starts with: the board's own — the
    first kind it offers, PVC before 1mm before 2mm — or '' for a board with no
    edging (ruled 27 September 2026). A kind with no edge ticked orders no
    edging; it only says what the edging is the moment an edge is ticked."""
    offered = material_offers(materials, board) if board else ()
    return offered[0] if offered else ""


def support_types_for(kind: str, corner_kind: str = "", solid_back: bool = False) -> List[str]:
    """Which support types a carcass of this kind may carry, in cut-list order.

    A base unit (no top panel): Front, Top Rear and Back. Anything with a top —
    tall, upper, and whatever else the engine gives a top — Back only. A blind
    corner is a straight carcass and goes by its kind; a mitre or an ell takes
    none. A SOLID back (3 October 2026) replaces the Top Rear and the Backs: a
    base unit keeps only its Top Front, anything with a top takes none.

    >>> support_types_for("base", solid_back=True)
    ['front']
    >>> support_types_for("tall", solid_back=True)
    []
    """
    if corner_kind in ("mitre", "ell"):
        return []
    if solid_back:
        return ["front"] if kind == "base" else []
    if kind == "base":
        return list(SUPPORT_TYPES)
    return ["back"]

# What a legacy "white-edged" support row was asking for.
#
# Edging is stated nowhere but the Boards record (20 September 2026), and the
# old WHITE_EDGE constant ("PVC WHITE") is gone (28 September 2026): nothing
# returned it any more. This token has to stay, and it is not an edging name: a
# legacy 'white' row names no board, only the word, so the one way to find the
# board it meant is to look for the project board whose Edging Name IS that
# word — which is reading the Boards record, not stating an edging. Every job
# written so far carries the white melamine that answers it, so none move.
WHITE_TOKEN = "WHITE"      # the Edging Name a legacy 'white' row was asking for


def white_edge_board(materials: dict, prefer: str = "") -> str:
    """The board a legacy 'white-edged' support row resolves to.

    The first board in the project that offers PVC under the token WHITE — which
    for every job written so far is the white melamine the row already meant, so
    nothing quoted moves. '' when the project has no such board, and then the
    row has no edging name and the validator says why.
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
# code 08, the existing Exposed Panel, with the role "Panel". The CSV carries
# `Panel.label` alone - the digits, e.g. 1508, in its Customer Number column -
# so a new code would have to be signed off with them exactly as 10 and 11 still
# have to be, and it would say nothing on the order that 08 does not. The role
# is what tells the two apart in the app's own cut list. One constant, so a code
# they do sign off later is one edit.
PANEL_CODE = "08"

# A blind corner's flush panel, ruled 22 September 2026 (Q3), on exactly the
# reasoning above: the CSV carries `Panel.label` (Customer Number) and never
# the role, so a code of its own would need their sign-off as 10 and 11
# still do, and would say nothing on the order that 08 does not. The role is
# what tells it from an exposed end in the app's own cut list. One constant, so
# a code they do sign off later is one edit.
BLIND_CODE = "08"

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

    # ---- attached panels (28 September 2026) -------------------------------
    # A panel FIXED TO a cabinet: `attached_to` is that cabinet's number, and
    # the three offsets place the panel in the cabinet's own frame — the
    # supports spec's: x across the width from the cabinet's left side, y from
    # the FRONT face of the sides (0) towards the back, z up from the underside
    # of the sides — each to the panel's own near corner (its left, front and
    # bottom). Negative values are ordinary: an end panel stands at x = -t, and
    # one finishing flush with the doors at y = -(door thickness). The world
    # position is the cabinet's placement applied to these (`room.
    # attached_placement`), so the panel moves, snaps and changes wall with the
    # cabinet. None means a standalone panel, exactly as every panel was before
    # this existed; the four are written to the job file only when attached.
    # Everything else about the panel — board, size, orientation, edging, code
    # 08, its number — is exactly as a standalone panel's.
    attached_to: Optional[int] = None
    at_x: int = 0
    at_y: int = 0
    at_z: int = 0


@dataclass
class Cabinet:
    number: int
    width: int
    height: int
    depth: int

    # 'tall' | 'upper' | 'base' ('base' has no top panel) | 'panel' (not a
    # cupboard at all: an independent panel, see `is_panel` and PanelSpec)
    kind: str = "tall"
    back: str = "four"           # 'four' | 'three' | 'none' | 'solid'
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

    shelves: int = 0  # adjustable  — LEGACY: read only until shelf_rows is written
    fixed_shelves: int = 0  # fitted, slightly deeper — LEGACY, as above
    # The shelves as rows (3 October 2026): `Shelf` per shelf. Empty means the
    # two numbers above are the shelves, read as rows at the ruled clearances
    # (`shelf_list`); the editor writes the rows — and zeroes the numbers — the
    # first time the section is touched, and never before.
    shelf_rows: List[Shelf] = field(default_factory=list)
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

    # A SOLID back (ruled 3 October 2026): `back == "solid"`, cut from any
    # full-thickness board the project carries — blank means the carcass board —
    # sitting inside the carcass flush with the sides' back edges. Unedged by
    # default; `solid_back_long` / `solid_back_short` count its banded edges
    # like Panel design, in `solid_back_edge_kind` (None: the board's own first
    # kind) and the colour of `solid_back_edge_board` (None: the board it is
    # cut from). All five are written only when set (store.LATE_CABINET_FIELDS).
    solid_back_board: str = ""
    solid_back_edge_kind: Optional[str] = None
    solid_back_edge_board: Optional[str] = None
    solid_back_long: int = 0
    solid_back_short: int = 0

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
    # The Drawers section's own defaults (29 September 2026): what every drawer
    # takes unless its row says it differs. The box edging's colour board and
    # thickness (None: the exterior board, PVC) and the bottom (None: 'board',
    # the grooved 3 mm sheet). Each written to the job file only when set.
    drawer_box_edge_board: Optional[str] = None
    drawer_box_edge_kind: Optional[str] = None
    drawer_base: Optional[str] = None

    # ---- retired typed edging names (28 September 2026) --------------------
    # A job file may still carry a flat edging string here ("PVC WOOD", "2mm
    # WOOD" on five Test.json cabinets). They are kept so the file round-trips
    # byte for byte, and NOTHING READS THEM: the edging follows the board picked,
    # through tape_for, so the name on the order is the Boards-tab Edging Name
    # and the screen and the order can never say two different things.
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
    corner_style: str = ""               # '' | 'mitre' | 'ell' | 'blind'
    arm_a: Optional[int] = None          # how far the box runs along wall A
    arm_b: Optional[int] = None          # how far it runs along wall B
    face_a: Optional[int] = None         # open face on the wall-A side: depth of the run butting it
    face_b: Optional[int] = None         # open face on the wall-B side: likewise
    # Which end of the unit stands in the corner, as you face it in the room:
    # 'R' the right-hand end, 'L' the left. '' means the answer this app gave
    # before the field existed, which is R — the corner at the wall's END, wall B
    # the NEXT wall in the chain (room.corner_shadow has always read it that way),
    # so cabinet 7 and every job written before this reads exactly as it did.
    # 'L' mirrors the outline, the front faces, the hinge rule and the shadow onto
    # the PREVIOUS wall. Wall-local x runs left to right as you face the wall —
    # that is not an assumption: it is what model.hinge_side already means by
    # 'L'/'R' (room.swing_envelopes hinges 'L' at the low-x end) and what
    # render.wall_elevation_svg draws.
    corner_hand: str = ""                # '' (= 'R') | 'L' | 'R'

    # ---- blind corner ------------------------------------------------------
    # A blind unit is a straight carcass with a flush panel INSIDE the corner end
    # - between the corner-end side and the opening, face flush with the front
    # edges, top to bottom - and one door at the far end lapping onto it (ruled
    # 22 September 2026). width / height / depth above are its carcass, exactly
    # as on any other cabinet; this is the only extra MEASUREMENT.
    blind_width: Optional[int] = None    # the blind panel's width, as cut
    # The blind panel is selectable in its own right (ruled 22 September 2026):
    # the board it is cut from, and the thickness of the one edge it carries.
    # Blank / None means "follow" - the exterior board, so the strip visible
    # between the door and the return run matches the doors, and the doors'
    # edging thickness. Both are written to the job file only when they are set
    # (store.LATE_CABINET_FIELDS), so every job written before them is unchanged.
    blind_board: str = ""                # '' = the exterior board
    blind_edge_kind: Optional[str] = None   # None = the doors' thickness

    # ---- mitre shelves -----------------------------------------------------
    # A mitre takes two kinds of shelf and can carry both (ruled 22 September
    # 2026). They replace `shelves` / `fixed_shelves` on a mitre, which are not
    # read there — a mitre's interior is not a rectangle, so a straight shelf
    # size would be wrong in the unsafe direction.
    #
    #   arm shelf     a rectangle running along one arm, behind the mitre. Its
    #                 length is that arm's internal span; its depth is typed, and
    #                 room.arm_shelf_max_depth is the most it may be.
    #   mitred shelf  the same square blank as the top and bottom, mitred on site
    #                 Standard.mitre_shelf_clear behind the closed door.
    arm_shelves: int = 0
    arm_shelf_arm: str = "a"             # 'a' | 'b' — which arm it runs along
    arm_shelf_depth: Optional[int] = None    # None = the derived maximum
    mitred_shelves: int = 0
    # The corner door's width, overriding the derived one. Blank means derived,
    # which is what it normally is.
    corner_door_width: Optional[int] = None
    # The "Corner unit" tickbox. None derives it from the style, which is how
    # every job predating the tickbox reads. False keeps all four measurements
    # and the style in the job file but stops anything reading them.
    corner_unit: Optional[bool] = None
    # The drawer runner this cabinet's drawers hang on (28 September 2026): the
    # id of a runner the job selected from Catalogue -> Runners. Blank is the
    # built-in LEGACY record (350 / 450 / 500), which is what every job saved
    # before the catalogue reads, so none of them moves; it is never offered
    # for a new cabinet. See `runner_rec` and `cabinetgen.hardware`.
    runner: str = ""

    # ---- what is actually live, once the tickboxes have had their say ------

    @property
    def runner_rec(self):
        """The runner record this cabinet is built on (`hardware.Runner`): the
        job's copy of the one it names — bound by `Job.bind_runners` — or, for
        a blank id or the seed id, the built-in record. None when it names a
        runner nobody can find; the engine then cuts on LEGACY and the
        validator blocks the export (`runner-not-selected`)."""
        from . import hardware as H
        bound = getattr(self, "_runner_bound", None)
        if bound is not None and bound[0] == self.runner:
            return bound[1]
        return H.resolve(self.runner, None)

    @property
    def runner_or_legacy(self):
        """`runner_rec`, or LEGACY where that is None — what is cut."""
        from . import hardware as H
        return self.runner_rec or H.LEGACY

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
    def attached_to(self) -> Optional[int]:
        """The cabinet this panel is fixed to, or None: a standalone panel, or
        not a panel at all. Read off the panel record and nowhere else."""
        if not self.is_panel or self.panel is None or self.panel.attached_to is None:
            return None
        return int(self.panel.attached_to)

    @property
    def is_attached(self) -> bool:
        return self.attached_to is not None

    @property
    def corner_on(self) -> bool:
        """Whether the corner measurements drive this cabinet's plan outline."""
        if self.corner_unit is None:
            return bool(self.corner_style)
        return bool(self.corner_unit) and bool(self.corner_style)

    @property
    def corner_ticked(self) -> bool:
        """Whether the Corner unit box is ticked, whether or not a type is chosen.

        `corner_on` needs a type as well, because everything downstream reads the
        four measurements through it. This is the other half of that question:
        ticked but with no type chosen is a cabinet that looks like a corner on
        screen and cuts a straight box, which is what the UI's "Choose a corner
        type" line and the validator's warning are both about.
        """
        if self.corner_unit is None:
            return bool(self.corner_style)
        return bool(self.corner_unit)

    @property
    def corner_kind(self) -> str:
        """'mitre' | 'ell' | 'blind', or '' when this is not a live corner unit."""
        return self.corner_style if self.corner_on else ""

    @property
    def hand(self) -> str:
        """'L' or 'R'. Blank reads as 'R' — the corner at the wall's end, which is
        what this app did before the field existed."""
        return "L" if self.corner_hand == "L" else "R"

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

        The label is what a message says out loud — "door 2 board",
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
        simple("solid_back_board", "solid back board")
        simple("solid_back_edge_board", "solid back edging board")
        simple("blind_board", "blind panel board")
        simple("drawer_carcass_board", "drawer carcass board")
        simple("drawer_face_board", "drawer face board")
        simple("drawer_box_edge_board", "drawer box edging board")
        simple("door_edge_board", "door edging board")
        simple("drawer_edge_board", "drawer edging board")
        for i in range(len(self.door_boards or [])):
            slots.append((f"door {i + 1} board",
                          lambda i=i: self.door_boards[i] or "",
                          lambda v, i=i: self.door_boards.__setitem__(i, v), False))
        for i, d in enumerate(self.drawers or []):
            for attr, what in (("box_board", "box board"), ("face_board", "face board"),
                               ("box_edge_board", "box edging board")):
                slots.append((f"drawer {i + 1} {what}",
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

    def box_edge_board_of(self, d: "Drawer") -> str:
        """The board one drawer's box sides and fronts are edged in the colour
        of: its own choice, the section's (`drawer_box_edge_board`), or the
        cabinet's exterior board (ruled 29 September 2026 — not the box board,
        which is what it followed before)."""
        return d.box_edge_board or self.drawer_box_edge_board or self.exterior_board

    def box_edge_kind_of(self, d: "Drawer") -> str:
        """How thick one drawer's box edging is: its own choice, the section's
        (`drawer_box_edge_kind`), or PVC — what every drawer was edged in
        before the choice existed (R1, 29 September 2026)."""
        return d.box_edge_kind or self.drawer_box_edge_kind or "pvc"

    def base_of(self, d: "Drawer") -> str:
        """How one drawer's bottom is held: its own `base`, the section's
        (`drawer_base`), or 'board' — the grooved 3 mm sheet."""
        return d.base or self.drawer_base or "board"

    def drawer_rise_of(self, std: Standard = STANDARD) -> int:
        """The default box offset over its face bottom: the bottom panel plus
        the runner's lift (16 + 5 = 21). `room.drawer_rise` is this."""
        return std.board_t + int(round(self.runner_or_legacy.lift))

    def box_offset_of(self, d: "Drawer", std: Standard = STANDARD) -> int:
        """One outer drawer's box bottom above its own face bottom: its
        `offset`, or the default rise."""
        return self.drawer_rise_of(std) if d.offset is None else int(d.offset)

    def face_bottom_of(self, d: "Drawer", std: Standard = STANDARD) -> int:
        """Where one OUTER drawer's face starts above the carcass underside:
        the faces below it and a `stack_gap` each — the face stack exactly as
        `room.drawer_layout` sets it out (the last drawer in the list lowest)."""
        at = 0
        for x in reversed(self.drawer_list):
            if x.inner:
                continue
            if x is d:
                return at
            at += int(x.face_height or 0) + std.stack_gap
        return at

    def support_band_underside(self, std: Standard = STANDARD) -> Optional[int]:
        """The underside of the 16 mm band a typed Top Front / Top Rear makes
        across the top of a base unit, above the carcass underside: H - t,
        exactly `room.support_layout`'s flat rails less their thickness (the
        `under` the support-drawer-foul check reads; `check_runners.py` holds the
        two equal on every job it knows). None where there is no such band — no
        typed flat support, or a carcass `support_layout` does not place."""
        if (self.is_panel or self.template == "none"
                or self.corner_kind in ("mitre", "ell") or not self.supports_typed):
            return None
        if not any(r.qty > 0 and r.type in ("front", "top_rear") for r in self.support_list):
            return None
        return int(self.height) - std.board_t

    def box_top_limit_of(self, d: "Drawer", std: Standard = STANDARD) -> int:
        """The highest one outer drawer's box top may reach: its face's top less
        `drawer_box_clear` — a box never sits flush in its face (ruled 29
        September 2026) — and no higher than a Top Front / Top Rear band's
        underside less the same clear, so an Auto box, which fills to this,
        never runs into the band on its own (29 September 2026)."""
        limit = (self.face_bottom_of(d, std) + int(d.face_height or 0)
                 - std.drawer_box_clear)
        band = self.support_band_underside(std)
        if band is not None:
            limit = min(limit, band - std.drawer_box_clear)
        return limit

    def box_height_of(self, d: "Drawer", std: Standard = STANDARD) -> int:
        """The box height one drawer is CUT at. A typed figure as typed; AUTO
        (None) the tallest box its face takes at its offset — up to its top
        limit (`box_top_limit_of`) from its bottom — which is exactly
        `room.drawer_layout`'s `max_box`, so an Auto box lies within its face
        by construction and follows the face when it moves. An inner drawer's
        face IS its box, so there is no face to fill: an Auto inner box reads
        the standard new-row height."""
        if d.box_height is not None:
            return int(d.box_height)
        if d.inner:
            return int(std.box_height_default)
        bottom = self.face_bottom_of(d, std) + self.box_offset_of(d, std)
        return max(self.box_top_limit_of(d, std) - bottom, 0)

    def face_board_of(self, d: "Drawer") -> str:
        """The board one drawer's face is cut from: its own, or the cabinet's."""
        return d.face_board or self.drawer_face

    @property
    def drawer_list(self) -> List[Drawer]:
        """The drawers that are actually built. Unticking keeps `drawers` in the
        job file untouched — nothing here empties it."""
        return [] if self.has_drawers is False else list(self.drawers)

    @property
    def outer_drawers(self) -> List[Drawer]:
        """The built drawers whose faces are on the front — the face stack.
        Every face-stack rule (the H - 3 fill, the elevation, the plan faces,
        the door above them) reads this, never `drawer_list`."""
        return [d for d in self.drawer_list if not d.inner]

    @property
    def inner_drawers(self) -> List[Drawer]:
        """The built drawers behind the door (`Drawer.inner`)."""
        return [d for d in self.drawer_list if d.inner]

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
            offered = self.support_types_offered
            # A typed row of a type this carcass does not take — a Front left on
            # a cabinet since made tall, a Back or Top Rear under a solid back —
            # stays in the file and cuts nothing, the tickbox bargain; the editor
            # shows it greyed and the validator names it. A legacy row (no type)
            # is cut wherever it is — except under a solid back, below.
            rows = [r for r in self.support_rows
                    if r.qty > 0 and (not r.type or r.type in offered)]
            return self._solid_back_legacy(rows) if self.solid_back else rows
        plain = self.supports - self.edged_supports - self.white_supports
        rows = [Support("none", plain), Support("front", self.edged_supports),
                Support("white", self.white_supports)]
        rows = [r for r in rows if r.qty > 0]
        return self._solid_back_legacy(rows) if self.solid_back else rows

    def _solid_back_legacy(self, rows: List[Support]) -> List[Support]:
        """What a LEGACY (untyped) support row cuts under a solid back: placed by
        the rule `room.support_layout` already draws them by — on a base unit
        the first front-edged rail is the Top Front and is cut, the rest are
        Backs and are replaced by the solid back; on a carcass with a top all
        are Backs and none is cut. A typed row is not touched here (it was
        filtered by type already). Nothing is converted or renamed."""
        out = []
        front_done = self.kind != "base"
        for r in rows:
            if r.type:
                out.append(r)
            elif not front_done and r.edge == "front":
                out.append(replace(r, qty=1) if r.qty != 1 else r)
                front_done = True
        return out

    @property
    def support_total(self) -> int:
        """The sum of the rows. Nothing subtracts."""
        return sum(r.qty for r in self.support_list)

    @property
    def support_types_offered(self) -> List[str]:
        """Which support types this cabinet may carry (`support_types_for`); a
        solid back takes the place of the Top Rear and the Backs."""
        return support_types_for(self.kind, self.corner_kind, self.solid_back)

    # ---- shelves as rows (3 October 2026) ----------------------------------

    @property
    def shelf_list(self) -> List[Shelf]:
        """The shelves that are cut and drawn, in order. The rows when any are
        written; otherwise the migration — `fixed_shelves` rows first at
        `Standard.shelf_gap_fixed` with note "fixed", then `shelves` rows at
        `Standard.shelf_gap_adjustable` — which is exactly what the two numbers
        cut before rows existed, line for line and in the same order. Nothing
        is written here."""
        if self.shelf_rows:
            return list(self.shelf_rows)
        return ([Shelf(clearance=STANDARD.shelf_gap_fixed, note="fixed")
                 for _ in range(int(self.fixed_shelves or 0))] +
                [Shelf(clearance=STANDARD.shelf_gap_adjustable)
                 for _ in range(int(self.shelves or 0))])

    def shelf_kind(self, row: Shelf) -> str:
        """A shelf row's edging kind: its own, else PVC (today's carcass edging)."""
        return row.kind or "pvc"

    def shelf_board(self, row: Shelf) -> str:
        """The board whose colour a shelf row is edged in: its own, else the
        exterior board (today's rule, 14 September 2026)."""
        return row.board or self.exterior_board

    def shelf_tape(self, materials: dict, row: Shelf) -> str:
        """The tape a shelf row orders: nothing with no edge counted, else its
        kind in its colour board — the Boards tab's answer."""
        if not (int(row.long or 0) or int(row.short or 0)):
            return ""
        return tape_for(materials, self.shelf_board(row), self.shelf_kind(row))

    @staticmethod
    def shelf_edge_counts(row: Shelf) -> tuple:
        """(edge_l, edge_w) for a shelf line. A shelf's Length is always its
        run across the cabinet (`shelf_width` or Wi) and its front edge runs
        along that, so `long` (front, then rear) is `edge_l` and `short` (the
        ends) is `edge_w` whatever the two sizes are — the October job's 400 x
        481 shelves in cabinets 11 and 12 are deeper than they are wide and
        band their front edge as edge_l, as they always did."""
        return (max(0, min(2, int(row.long or 0))), max(0, min(2, int(row.short or 0))))

    # ---- the solid back (ruled 3 October 2026) ------------------------------

    @property
    def solid_back(self) -> bool:
        """Whether the back is one full-thickness board inside the carcass."""
        return self.back == "solid"

    @property
    def solid_back_cut_board(self) -> str:
        """The board a solid back is cut from: its own, else the carcass board."""
        return self.solid_back_board or self.carcass_board

    @property
    def solid_back_edge_colour_board(self) -> str:
        """The board whose colour its edging is: its own, else the one it is cut from."""
        return self.solid_back_edge_board or self.solid_back_cut_board

    def solid_back_kind(self, materials: dict) -> str:
        """Its edging kind: the one chosen, else the edging board's own first
        kind ('' for a board with no edging) — the same default a support row
        starts on."""
        if self.solid_back_edge_kind is not None:
            return self.solid_back_edge_kind
        return default_support_kind(materials, self.solid_back_edge_colour_board)

    def solid_back_tape(self, materials: dict) -> str:
        """The tape a solid back orders: nothing until an edge is counted, then
        its kind in its edging board's colour (the Boards tab's answer)."""
        if not (self.solid_back_long or self.solid_back_short):
            return ""
        kind = self.solid_back_kind(materials)
        return tape_for(materials, self.solid_back_edge_colour_board, kind) if kind else ""

    @property
    def supports_typed(self) -> bool:
        """True when the rows are in the new form — every stored row carries a
        type. A cabinet with no rows reads its legacy numbers, and is not."""
        return bool(self.support_rows) and all(r.type for r in self.support_rows)

    def support_row_edge_counts(self, row: "Support") -> tuple:
        """(edge_l, edge_w) the cut list records for one row, BEFORE asking
        whether it has an edging at all: a typed row counts its chosen long
        edges and ends; a legacy row is one long edge, as it always was."""
        if not row.type:
            return 1, 0
        chosen = support_edges_of(row)
        return (sum(1 for e in chosen if e in SUPPORT_LONG_EDGES),
                sum(1 for e in chosen if e not in SUPPORT_LONG_EDGES))

    def new_support(self, materials: dict, type: str, qty: int = 1) -> "Support":
        """A fresh typed row of this type, with the defaults ruled 27 September
        2026 and 3 October 2026: cut from the carcass board; a Back or a Top
        Rear edged in that board's own edging (`default_support_kind`; '' for a
        board with no edging); a Top Front edged PVC in the EXTERIOR board's
        colour (3 October) — the board's own first kind where it offers no PVC.
        A Back has NO edge ticked, so it is unedged until one is; a Front or
        Top Rear starts on the type's default, its front long edge."""
        board = self.carcass_board
        edge_board = board
        kind = default_support_kind(materials, board)
        if type == "front" and self.exterior_board:
            edge_board = self.exterior_board
            offered = material_offers(materials, edge_board)
            kind = "pvc" if "pvc" in offered else (offered[0] if offered else "")
        return Support(edge="none", qty=qty, type=type, cut_board=board, board=edge_board,
                       kind=kind,
                       edges=[] if type == "back" else list(SUPPORT_DEFAULT_EDGES))

    def default_supports(self, materials: dict) -> List[Support]:
        """The support rows a NEW cabinet of this kind starts with (ruled 3
        October 2026, replacing the 28 September rows):

            base          Top Front 1 (exterior PVC), Top Rear 1, ONE Back row qty 2
            wall (upper)  one Back row qty 3
            tall          one Back row qty 3   (was four rows of 1)
            blind corner  by its kind, as above
            mitre / ell   none

        The Backs are one row per cupboard, unedged; "+ Back support" still adds
        a separate row when one must differ. Each row is `new_support`'s
        defaults. Only ever applied to a cabinet being made or one whose rows
        are still these untouched defaults; an existing cabinet and a legacy
        row are never rewritten by it.
        """
        offered = self.support_types_offered
        if not offered:
            return []
        if "front" in offered:
            return [self.new_support(materials, "front"),
                    self.new_support(materials, "top_rear"),
                    self.new_support(materials, "back", qty=2)]
        return [self.new_support(materials, "back", qty=3)]

    def reentered_supports(self, materials: dict) -> List[Support]:
        """The legacy rows rewritten as typed rows — Rudolf's explicit act.

        Each legacy row keeps its own qty and exactly what the engine resolved
        it to be cut from and edged in, so the cut list and the cost do not
        move (ruled 27 September 2026, replacing a Back block that folded
        every row into one edging). Placed by the legacy drawing rule: on a
        base unit the first front-edged rail is the Front, everything else is
        a Back, one typed row per legacy row; on a carcass with a top, all
        Backs. An edged row bands its front long edge, which is the one long
        edge a legacy row always banded; an unedged row ticks nothing. No Top
        Rear is guessed. Cut-list order is Front, then Backs in legacy order.
        """
        offered = self.support_types_offered
        out: List[Support] = []
        backs: List[Support] = []
        front_done = "front" not in offered
        for row in self.support_list:
            cut = self.support_row_cut_board(row)
            kind = self.support_row_kind(row)
            board = self.support_row_board(materials, row) if kind else cut
            edges = list(SUPPORT_DEFAULT_EDGES) if kind else []
            qty = row.qty
            if not front_done and row.edge == "front":
                out.append(Support(edge="none", qty=1, type="front", cut_board=cut,
                                   board=board, kind=kind, edges=list(SUPPORT_DEFAULT_EDGES)))
                front_done = True
                qty -= 1
            if qty > 0:
                backs.append(Support(edge="none", qty=qty, type="back", cut_board=cut,
                                     board=board, kind=kind, edges=edges))
        return out + backs

    @property
    def legacy_supports_negative(self) -> bool:
        """The three legacy numbers contradict each other: edged + white is more
        than the total, so the plain count they imply is below zero."""
        return (not self.support_rows
                and self.supports - self.edged_supports - self.white_supports < 0)

    # ---- tapes: always the board's (typed overrides retired 28 Sept 2026) ---

    def carcass_tape(self, materials: dict) -> str:
        """PVC in the EXTERIOR board's colour. It bands the front edges of the
        sides, top and bottom, and the front edges of shelves and dividers, which
        were ruled to match the front rather than the box (14 Sept 2026)."""
        return tape_for(materials, self.exterior_board, "pvc")

    def door_tape(self, materials: dict) -> str:
        """The doors' edging, and an exposed end's: a thickness and a colour.

        Both are chosen in the Doors section; with neither chosen it is the
        cabinet's exterior tape thickness in the exterior board's colour, which
        is what this always was. A flat `door_edge` string in the job file is
        no longer read (28 September 2026).
        """
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
    def blind_panel_board(self) -> str:
        """The board a blind unit's flush panel is cut from.

        Its own choice, or the cabinet's exterior board. The default is the
        exterior board because the strip of panel the door does not cover is
        seen from the room, beside the doors, and has to match them.
        """
        return self.blind_board or self.exterior_board

    @property
    def blind_edge_thickness(self) -> str:
        """1mm or 2mm: the blind panel's own choice, then the doors'.

        Offered separately from the doors because reaching into the cupboard
        rubs against that one edge, so it may want the heavier band whatever the
        doors carry (ruled 22 September 2026). With nothing chosen it is the
        doors' thickness, which is what the panel was edged in before the
        control existed.
        """
        kind = self.blind_edge_kind or self.door_edge_kind or self.exterior_tape
        if kind not in EXTERIOR_TAPES:
            kind = "2mm"
        return kind

    def blind_tape(self, materials: dict) -> str:
        """The blind panel's edging: its own thickness, in its OWN board's colour.

        One long edge only - the vertical edge facing the opening, which is the
        one seen and rubbed when the door is open. The colour is the panel's own
        board rather than the doors', because it is that board's own edge; where
        the panel follows the exterior board the two are the same name anyway.
        """
        return tape_for(materials, self.blind_panel_board, self.blind_edge_thickness)

    @property
    def drawer_face_edge_colour_board(self) -> str:
        """The same, for drawer faces: their own choice, then the doors', then the
        cabinet's exterior board."""
        return (self.drawer_edge_board or self.door_edge_board
                or self.exterior_board)

    def drawer_box_tape(self, materials: dict) -> str:
        """The section's drawer-box edging — its own board and thickness, else
        PVC in the EXTERIOR board's colour (29 September 2026) — what a drawer
        naming none of its own is edged in. Drawer sides and fronts only;
        supports have their own."""
        return tape_for(materials, self.drawer_box_edge_board or self.exterior_board,
                        self.drawer_box_edge_kind or "pvc")

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
        if row.type:
            # a typed row says what it means: no colour board named is its own
            return self.support_row_cut_board(row)
        if row.edge == "front":
            return self.exterior_board
        if row.edge == "white":
            return white_edge_board(materials)
        return self.support_row_cut_board(row)

    def support_row_kind(self, row: "Support") -> str:
        """Which edging kind a support row asks for. '' means none."""
        if row.kind:
            return row.kind
        if row.type:
            return ""                      # a typed row with no kind is not edged
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
        """The edging on one drawer's box sides and fronts: its thickness
        (`box_edge_kind_of`, PVC by default) in the colour of its box edging
        board (`box_edge_board_of`: its own, the section's, else the exterior
        board)."""
        return tape_for(materials, self.box_edge_board_of(d), self.box_edge_kind_of(d))

    @property
    def needs_back_board(self) -> bool:
        """Whether anything on this cabinet is actually cut from the back board:
        a grooved backing (four / three), or a drawer on a grooved 3 mm base. A
        solid back is cut from `solid_back_cut_board`, not from this."""
        return (self.back not in ("none", "solid")
                or any(self.base_of(d) == "board" for d in self.drawer_list))

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
    """One wall: a positioned segment (room redo Phase 1, 2 October 2026).

    `x0, y0` -> `x1, y1` are its two end points in room millimetres, whole
    numbers. The drawn line is the INSIDE face, and the room is on the RIGHT of
    x0 -> x1 (walls clockwise, as the app has always had them): wall A of a
    4000 x 3000 room runs (0, 0) -> (4000, 0) and the room is at +Y. Length,
    direction, the inward normal, which wall meets which, the corner angles,
    the walk order and whether the room closes are all DERIVED in `room.py`;
    nothing else stores a wall position. A wall's letter is for life: nothing
    re-letters one but `room.renumber_walls`, a deliberate act.

    `height` is None for the room ceiling; `thickness` None for
    `Standard.wall_thickness` (drawing only — it moves no check). `drawn` says
    the segment came off a mouse sketch on Room -> Plan, not a tape: a
    CRITICAL until it is typed or ticked as measured, so a cut list never goes
    out on a drawn length. Each is written to the job file only when set
    (`store.wall_to_dict`).

    A room saved before this (walls as a length and a corner angle, the chain
    walked from wall A along +X) is migrated ONCE on load by
    `store.room_from_dict` through the old chain arithmetic
    (`room._legacy_frames`), to whole mm; saving then writes points.
    """
    id: str                # 'A', 'B', 'C' ... (after Z, AA)
    x0: int = 0
    y0: int = 0
    x1: int = 0
    y1: int = 0
    height: Optional[int] = None       # None: the room ceiling
    thickness: Optional[int] = None    # None: Standard.wall_thickness; drawing only
    drawn: bool = False                # drawn with the mouse, not yet measured
    openings: List[Opening] = field(default_factory=list)
    obstructions: List[Obstruction] = field(default_factory=list)

    @property
    def length(self) -> int:
        """The wall's length in whole mm, off its two end points."""
        return int(round(math.hypot(self.x1 - self.x0, self.y1 - self.y0)))


@dataclass
class Room:
    name: str
    # A required site measurement, deliberately without a default: the ceiling
    # check is only worth trusting against a real figure, so a room with no
    # ceiling blocks the export until one is measured.
    ceiling: Optional[int] = None
    offset_depth: int = 600    # depth an out-of-square figure is read at (the Wall card)
    walls: List[Wall] = field(default_factory=list)


@dataclass
class Placement:
    """Where one cabinet or one independent panel stands. Geometry lives in
    room.py, never here.

    `y` is the one field a panel needs and a cabinet does not: a carcass sits
    against the wall it is placed on, so its y is 0 and stays 0, while a panel
    may stand off the wall — a bulkhead underside projects out over the units
    below it. It is written to the job file ONLY when it is non-zero, so every
    cabinet placement written before this round-trips byte for byte.
    """
    cabinet: int           # Cabinet.number
    wall: str              # Wall.id
    x: int                 # mm from wall start to the cabinet's left edge, facing the wall
    z: int = 0             # 0 stands on the floor, on its legs; above 0, a hung unit's underside
    flip: bool = False     # handedness for corner and asymmetric units
    layer: Optional[str] = None   # override; normally derived from kind and z
    y: int = 0             # out from the wall face to the back of an independent panel


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
class Acceptance:
    """A critical the operator has accepted, with the reason why.

    Only a site-dependent critical can be accepted — one that says something
    about the room rather than about the cut list (`validate.ACCEPTABLE` is the
    list, and today it is the tip-up check alone). A critical that protects the
    cut list is never accepted, whatever is stored here.

    `fingerprint` is exactly the inputs the check used when the acceptance was
    given, as `validate.fingerprint` wrote them. When they no longer match, the
    acceptance has lapsed: it was given for a different cabinet or a different
    ceiling, and the critical blocks again until somebody looks at it afresh.
    """
    check: str                 # the stable id of the check, e.g. "tip-up"
    where: str                 # what the issue names — for tip-up, the cabinet number
    reason: str
    fingerprint: str = ""


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

    # Site-dependent criticals the operator has accepted, each with its reason.
    # Written to the job file only when there is one, so every job saved before
    # acceptances existed reads and writes byte for byte.
    acceptances: List[Acceptance] = field(default_factory=list)

    # board id -> the record this job was quoted with. A snapshot taken when the
    # board was selected, never a pointer at the library: editing a board's price
    # there changes what the next job costs and never what this one did.
    materials: dict = field(default_factory=lambda: {k: dict(v)
                                                     for k, v in MATERIALS.items()})

    # runner id -> the record this job was quoted with (28 September 2026),
    # copied in from Catalogue -> Runners when the runner is ticked into the
    # project, price and all: the same price capture `materials` is for a board.
    # Written to the job file only when there is one, so every job saved before
    # it round-trips byte for byte. In selection order.
    runners: dict = field(default_factory=dict)

    def __post_init__(self):
        self.bind_runners()

    def bind_runners(self):
        """Hand every cabinet the job's copy of the runner it names, so
        `Cabinet.runner_rec` — read wherever a drawer is sized, however deep in
        the geometry — is this job's record and not a default. Called on
        construction and by `generate_job` / `validate`; a cabinet whose runner
        changes afterwards falls back to the built-in records until then."""
        from . import hardware as H
        for cab in self.cabinets:
            cab._runner_bound = (cab.runner, H.resolve(cab.runner, self.runners))

    @property
    def board_ids(self) -> List[str]:
        """The boards a cabinet may be cut from, in a stable order."""
        return list(self.boards) if self.boards else sorted(self.materials or {})
