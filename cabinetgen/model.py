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


@dataclass
class Panel:
    cabinet: int
    code: str
    role: str
    material: str          # 'MEL' | 'DECOR' | 'BACK'
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
    """One drawer. face_height is the visible front; box_height is the box side height."""
    face_height: int
    box_height: int
    base: str = "board"          # 'board' (3 mm, grooved) | 'melamine' (16 mm, housed)


@dataclass
class Cabinet:
    number: int
    width: int
    height: int
    depth: int

    kind: str = "tall"           # 'tall' | 'upper' | 'base'  ('base' has no top panel)
    back: str = "four"           # 'four' | 'three' | 'none'
    template: str = "standard"   # 'standard' | 'none' (bespoke only — generate nothing)

    supports: int = 4
    edged_supports: int = 0      # front rail(s), banded in carcass_edge
    white_supports: int = 0      # rear rail(s), banded in drawer_box_edge

    shelves: int = 0             # adjustable
    fixed_shelves: int = 0       # fitted, slightly deeper
    shelf_width: Optional[int] = None    # override when the interior is split by a divider

    divider_height: Optional[int] = None
    divider_count: int = 0

    doors: int = 0
    door_height: Optional[int] = None    # None = full height (H - 3)

    drawers: List[Drawer] = field(default_factory=list)

    exposed_sides: int = 0

    # finishes
    carcass_edge: str = "PVC WOOD"
    door_edge: str = "2mm WOOD"
    drawer_box_edge: str = "PVC WHITE"
    decor: str = "DECOR"

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

    # material name -> Plazaboard board description, for the export and the quote
    materials: dict = field(default_factory=lambda: {
        "MEL": "SUPER WHITE MELAMINE CHIP 9X6X16MM",
        "DECOR": "BROOKHILL FUSION CHIP",
        "BACK": "IMPORTED WHITE DECOR 9X6X3MM",
    })
