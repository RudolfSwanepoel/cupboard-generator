"""Room geometry. The one place trigonometry is allowed.

Local axes, standing in the room facing a wall:

    x   along the wall, from its start corner
    y   out from the wall face, into the room
    z   up from the floor

World axes: X to the right, Y into the room from wall A, Z up. Plan views map
world (X, Y) straight onto SVG (x, y) with no flip, which is why Y runs the way
it does.

Everything downstream — plan view, elevations, 3D, DXF, the SolidWorks table —
calls `to_world`. Nothing else does its own trig. That is the whole point of
this module: one place to be wrong, and one place to fix.

Walls chain in list order, clockwise as drawn in plan. Each corner turns
90 degrees less the measured deviation from square.
"""
import math
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from .model import (MATERIALS, Cabinet, Room, Wall, hinge_side,
                    material_thickness)
from .standard import STANDARD, Standard

Point = Tuple[float, float]


def rectangular(length: int, width: int, name: str = "room", **kw) -> Room:
    """A square room, walls A-D clockwise. Most rooms start here and get measured.

        rectangular(4000, 3000)  ->  Room
    """
    return Room(name=name, walls=[
        Wall("A", length), Wall("B", width), Wall("C", length), Wall("D", width),
    ], **kw)


# The fixtures the worked examples below are checked against by
# tools/check_examples.py. A 4 x 3 m square room, walls A-D clockwise.
EXAMPLE_ROOM = rectangular(4000, 3000)

# Cabinet 7 of the October 2025 job by its measured figures (spec item 14), but
# as a TEMPLATE cabinet: the real one is bespoke and stays that way, so that the
# benchmark cannot move. Every mitre worked example is checked against it, which
# is what ties the derived figures to a unit that was actually built.
EXAMPLE_MITRE = Cabinet(number=7, width=850, height=2400, depth=500,
                        back="none", supports=0, doors=1,
                        corner_unit=True, corner_style="mitre",
                        arm_a=850, arm_b=850, face_a=500, face_b=500)
# The worked blind example from the 22 September 2026 ruling: W 1000, B 500,
# t 16 -> opening 468, door 497, blind panel 500.
EXAMPLE_BLIND = Cabinet(number=1, width=1000, height=720, depth=560,
                        doors=1, corner_unit=True, corner_style="blind",
                        blind_width=500)


def next_wall_id(rm: Room) -> str:
    """The first letter not already naming a wall."""
    used = {w.id for w in rm.walls}
    letter = "A"
    while letter in used:
        letter = chr(ord(letter) + 1)
    return letter


def add_wall(rm: Room, at: str, length: int) -> Wall:
    """Add a wall at the start or the end of the wall sequence, and return it.

    This is how a straight run becomes an L or a U: a wall added at the end turns
    the corner at the last wall's end, and one added at the start meets the first
    wall at its start corner. It starts square at both corners.

    Placements name walls by id, not position, so nothing already placed moves
    along its wall. Adding at the start does re-origin the chain — the new wall
    now runs along +X — and makes it the "earlier" wall at that corner for the
    plinth butt rule.
    """
    wall = Wall(next_wall_id(rm), length)
    if at == "start":
        rm.walls.insert(0, wall)
    elif at == "end":
        rm.walls.append(wall)
    else:
        raise ValueError(f"a wall goes at the 'start' or the 'end', not {at!r}")
    return wall


def _wall(rm: Room, wall_id: str) -> Wall:
    for w in rm.walls:
        if w.id == wall_id:
            return w
    raise ValueError(f"room {rm.name!r} has no wall {wall_id!r}")


def corner_offset(rm: Room, i: int) -> Tuple[int, int]:
    """The offset describing the corner after wall `i`, and how far the two
    measurements of that corner disagree.

    Every corner is measured twice on site — once from each of the walls that
    meet there. Where both are given they describe one physical angle and should
    agree. Where they do not, that is a measuring error, so it is reported by
    the validator rather than averaged away. Where only one is given, it is
    used, so a corner need only be measured from whichever side is reachable.

        corner_offset(EXAMPLE_ROOM, 0)  ->  (0, 0)
    """
    n = len(rm.walls)
    here = rm.walls[i].offset_end
    nxt = rm.walls[(i + 1) % n].offset_start
    if here and nxt:
        return here, abs(here - nxt)
    return (here or nxt), 0


def wall_frames(rm: Room) -> Dict[str, Tuple[Point, Point, Point]]:
    """Chain the walls around the room.

    Returns wall id -> (start point, unit direction, unit inward normal).
    """
    out: Dict[str, Tuple[Point, Point, Point]] = {}
    px, py = 0.0, 0.0
    theta = 0.0                       # wall A runs along +X
    for i, w in enumerate(rm.walls):
        dx, dy = math.cos(theta), math.sin(theta)
        out[w.id] = ((px, py), (dx, dy), (-dy, dx))
        px += w.length * dx
        py += w.length * dy
        offset, _ = corner_offset(rm, i)
        deviation = math.atan2(offset, rm.offset_depth)
        theta += math.pi / 2 - deviation
    return out


def corner_points(rm: Room) -> List[Point]:
    """The corner where each wall starts, in wall order, plus where the last
    wall ends. On a room that closes, the final point equals the first."""
    frames = wall_frames(rm)
    pts = [frames[w.id][0] for w in rm.walls]
    if rm.walls:
        last = rm.walls[-1]
        (sx, sy), (dx, dy), _ = frames[last.id]
        pts.append((sx + last.length * dx, sy + last.length * dy))
    return pts


def closure_error(rm: Room) -> int:
    """How far the last wall's end misses the first wall's start, in mm.

    A room that does not close means the measurements disagree with each other.
    An open run of walls has nothing to close, so it reports 0.

        closure_error(EXAMPLE_ROOM)  ->  0
    """
    if not rm.closed or len(rm.walls) < 3:
        return 0
    pts = corner_points(rm)
    return round(math.dist(pts[0], pts[-1]))


def to_world(rm: Room, wall_id: str, x: int, y: int = 0, z: int = 0) -> Tuple[int, int, int]:
    """Wall-local (x along, y into the room, z up) to world (X, Y, Z), in mm.

    Rounded to the millimetre: the chain is carried in floating point and only
    the answer is rounded, so corners do not accumulate error.

        to_world(EXAMPLE_ROOM, 'A', 1000, 0, 0)  ->  (1000, 0, 0)
        to_world(EXAMPLE_ROOM, 'A', 0, 600, 0)  ->  (0, 600, 0)
        to_world(EXAMPLE_ROOM, 'B', 0, 0, 0)  ->  (4000, 0, 0)
        to_world(EXAMPLE_ROOM, 'C', 0, 0, 0)  ->  (4000, 3000, 0)
    """
    (sx, sy), (dx, dy), (nx, ny) = wall_frames(rm)[_wall(rm, wall_id).id]
    return (round(sx + dx * x + nx * y),
            round(sy + dy * x + ny * y),
            round(z))


# --- what a cabinet actually is: read off its panels, never off its labels -----

CARCASS_ROLES = ("Side", "Top", "Bottom", "Shelve", "Divider")


@dataclass
class CabinetGeometry:
    """A cabinet's real size and shape, from its panel set and its outline.

    Declared width, height and depth are inputs to panel generation and labels
    for display. No geometric check reads them — the corner unit declares 500
    deep and has an 834 side, and depth drives the tip-up diagonal, so a check on
    the declared figure under-reports in the unsafe direction. Every check reads
    this instead, and this reads what was actually cut: the sides say how tall
    and how deep, the top or bottom how wide, the door panels how far a door
    swings, the drawer sides how far a drawer comes out.
    """
    number: int
    footprint: List[Tuple[int, int]]   # cabinet frame: x along the wall from its left edge, y out
    height: int                        # the tallest side
    panel_depth: int                   # the deepest carcass panel
    panel_width: Optional[int]         # top, bottom or rail length plus two sides; None if none
    door_widths: List[int]             # one per door, from the door panels
    runner: Optional[int]              # drawer side length, if it has drawers
    source: str                        # 'panel' | 'corner' | 'outline' | 'panels' | 'declared'

    @property
    def width(self) -> int:
        """Extent along the wall."""
        xs = [x for x, _ in self.footprint]
        return max(xs) - min(xs)

    @property
    def depth(self) -> int:
        """How far it comes out from the wall."""
        return max(y for _, y in self.footprint)

    @property
    def tip_depth(self) -> int:
        """Depth for the tip-up diagonal: the deeper of the outline and the panels."""
        return max(self.depth, self.panel_depth)

    @property
    def front_faces(self) -> List[Tuple[Point, Point]]:
        """A corner unit's front face(s), each left to right as seen from the
        room: the mitre edge, or an ell's two faces off its notch. Empty for
        anything that is not a resolved corner unit."""
        if self.source != "corner":
            return []
        o = self.footprint
        if len(o) == 5:
            return [(o[4], o[3])]
        return [(o[5], o[4]), (o[4], o[3])]

    @property
    def face_lengths(self) -> List[int]:
        """How long each front face is — what a door and its reveal are read against."""
        return [round(math.dist(a, b)) for a, b in self.front_faces]

    @property
    def mitre_deg(self) -> Optional[float]:
        """A mitre's angle to wall A. An output of the four measurements, never an
        input, and nothing compares it with 45 (spec item 12). None unless a mitre.

        The ANGLE, not the direction the face happens to run in: a left-handed
        unit is the right-handed one mirrored, and a mitre a joiner would call 45
        does not become 135 because the unit was turned round. Right-handed units
        always run up and to the right (both extents are positive by the validity
        check above), so taking the magnitude changes nothing for them.
        """
        if self.source != "corner" or len(self.footprint) != 5:
            return None
        (x0, y0), (x1, y1) = self.front_faces[0]
        return round(math.degrees(math.atan2(abs(y1 - y0), abs(x1 - x0))), 1)


def rect_outline(width: int, depth: int) -> List[Tuple[int, int]]:
    """Front left, front right, back right, back left — the order every rectangle
    in this module has always used."""
    return [(0, depth), (width, depth), (width, 0), (0, 0)]


def corner_outline(style: str, arm_a, arm_b, face_a, face_b,
                   hand: str = "R") -> Optional[List[Tuple[int, int]]]:
    """The plan outline of a parametric corner unit (ruled 14 Sept 2026, spec
    item 11), derived from its four measurements, a style and a hand. None when
    they do not describe a real shape — the caller falls back, and the validator
    raises a critical rather than let a bad shape through quietly.

    Frame: x runs along wall A from the cabinet's start corner, y out from wall
    A. Wall A is the face at y = 0. There is no angle input — a mitre's angle is
    an output of these four numbers, 45° only when arm_a - face_b == arm_b - face_a.

    The HAND says which end of the unit stands in the corner, as you face it in
    the room (ruled 22 Sept 2026). 'R' is the right-hand end, which is what this
    app drew before the field existed: wall B is the face at x = arm_a, and
    `corner_shadow` turns onto the NEXT wall in the chain. 'L' is the mirror of
    it about the unit's own centre line — wall B at x = 0, the shadow on the
    PREVIOUS wall. Mirroring reverses a polygon's winding, so the points are
    reversed and rotated as well as reflected: `front_faces` reads the mitre off
    indices 3 and 4 and an ell off 3, 4 and 5, and it must keep reading them
    left to right as seen from the room whichever hand it is.

        corner_outline("mitre", 850, 850, 500, 500)  ->  [(0, 0), (850, 0), (850, 850), (350, 850), (0, 500)]
        corner_outline("ell", 850, 850, 500, 500)  ->  [(0, 0), (850, 0), (850, 850), (350, 850), (350, 500), (0, 500)]
        corner_outline("mitre", 850, 850, 500, 500, "L")  ->  [(0, 850), (0, 0), (850, 0), (850, 500), (500, 850)]
        corner_outline("ell", 850, 850, 500, 500, "L")  ->  [(0, 850), (0, 0), (850, 0), (850, 500), (500, 500), (500, 850)]

    A face measured wider than the arm it would have to fit inside describes no
    shape at all — `corner_outline("mitre", 850, 850, 900, 500)` is `None` —
    which check_drag.py checks, since this pattern only verifies list results.

    A BLIND corner is deliberately not here: its plan is a plain rectangle W x D
    like any other cabinet (ruled 22 Sept 2026), so it has no derived outline and
    `geometry` reads the rectangle its panels make, exactly as it always did. Its
    one corner-specific piece of plan geometry is its shadow — see `corner_shadow`.
    """
    if style not in ("mitre", "ell") or None in (arm_a, arm_b, face_a, face_b):
        return None
    if not (0 < face_b < arm_a and 0 < face_a < arm_b):
        return None
    if hand == "L":
        if style == "mitre":
            return [(0, arm_b), (0, 0), (arm_a, 0), (arm_a, face_a), (face_b, arm_b)]
        return [(0, arm_b), (0, 0), (arm_a, 0), (arm_a, face_a),
                (face_b, face_a), (face_b, arm_b)]
    if style == "mitre":
        return [(0, 0), (arm_a, 0), (arm_a, arm_b), (arm_a - face_b, arm_b), (0, face_a)]
    return [(0, 0), (arm_a, 0), (arm_a, arm_b), (arm_a - face_b, arm_b),
            (arm_a - face_b, face_a), (0, face_a)]


def cab_corner_outline(cab) -> Optional[List[Tuple[int, int]]]:
    """corner_outline read off a Cabinet's own fields, or None if it isn't one.

    `corner_on`, not `corner_style`: with the Corner unit tickbox off the four
    measurements stay in the job file untouched and nothing reads them.
    """
    if not cab.corner_on:
        return None
    return corner_outline(cab.corner_style, cab.arm_a, cab.arm_b,
                          cab.face_a, cab.face_b, cab.hand)


# ---- what a mitre actually measures ----------------------------------------
#
# Ruled 22 September 2026, and every figure below is derived from the four
# measurements and the board thickness. Nothing here is typed and nothing is
# guessed. The one line all of it hangs off is the INNER LINE: the surface a
# closed door's inside face rests on. That is not the outline's mitre face --
# the outline runs corner to corner of the carcass, and the blank the top, the
# bottom and the shelves are cut from is already a board thickness inside it on
# both edges. Cabinet 7 is the proof: its inner line is 472.35 long and its
# door, as really cut, is 472.


def _mitre_parts(cab, std: Standard = STANDARD):
    """(t, arm_a, arm_b, face_a, face_b) for a live mitre, or None.

    Every helper below starts here, so "is this a mitre with usable numbers" is
    answered in one place rather than five.
    """
    if cab.corner_kind != "mitre":
        return None
    if None in (cab.arm_a, cab.arm_b, cab.face_a, cab.face_b):
        return None
    t = std.board_t
    a_a, a_b = int(cab.arm_a), int(cab.arm_b)
    f_a, f_b = int(cab.face_a), int(cab.face_b)
    if not (0 < f_b < a_a and 0 < f_a < a_b):
        return None
    if a_a <= 2 * t or a_b <= 2 * t or f_a <= t or f_b <= t:
        return None
    return t, a_a, a_b, f_a, f_b


def mitre_blank(cab, std: Standard = STANDARD) -> Optional[Tuple[int, int]]:
    """The square blank the top, the bottom and every mitred shelf is cut from.

    (arm_a - 2t) x (arm_b - 2t): the interior the four side panels leave.

        mitre_blank(EXAMPLE_MITRE)  ->  (818, 818)
    """
    p = _mitre_parts(cab, std)
    if p is None:
        return None
    t, a_a, a_b, _f_a, _f_b = p
    return a_a - 2 * t, a_b - 2 * t


def mitre_inner_corners(cab, std: Standard = STANDARD):
    """The two ends of the inner line, in the cabinet frame, left to right.

    Each is the inner front corner of one open-face side panel. That panel is
    `face` deep measured from the wall, so its front edge is `face` from the
    carcass outside, and the blank meets it a board thickness in.

        mitre_inner_corners(EXAMPLE_MITRE)  ->  ((16, 500), (350, 834))
    """
    p = _mitre_parts(cab, std)
    if p is None:
        return None
    t, a_a, a_b, f_a, f_b = p
    if cab.hand == "L":
        return (f_b, a_b - t), (a_a - t, f_a)
    return (t, f_a), (a_a - f_b, a_b - t)


def mitre_inner_span(cab, std: Standard = STANDARD) -> Optional[float]:
    """How long the inner line is - the span a mitre door is cut to.

        mitre_inner_span(EXAMPLE_MITRE)  ->  472.35
    """
    ends = mitre_inner_corners(cab, std)
    if ends is None:
        return None
    return round(math.dist(*ends), 2)


def mitre_legs(cab, std: Standard = STANDARD, setback: int = 0):
    """(leg along arm A, leg along arm B) of the mitre cut on the blank.

    Measured from the blank's own cut-off corner along its two edges, which is
    what the fitter marks. `setback` moves the cut line back from the inner line,
    perpendicular to it, which is how a mitred shelf clears the closed door; at 0
    the cut is flush with the inner line, which is what the top and bottom get.

    The hand mirrors which corner of the blank comes off, and mirrors both legs
    with it, so the two figures are the same either way round.

        mitre_legs(EXAMPLE_MITRE)  ->  (334, 334)
        mitre_legs(EXAMPLE_MITRE, STANDARD, 3)  ->  (338, 338)
    """
    p = _mitre_parts(cab, std)
    if p is None:
        return None
    t, a_a, a_b, f_a, f_b = p
    dx = (a_a - f_b) - t                 # the inner line's extent along arm A
    dy = (a_b - t) - f_a                 # and along arm B
    if dx <= 0 or dy <= 0:
        return None
    span = math.hypot(dx, dy)
    return round(dx + setback * span / dy), round(dy + setback * span / dx)


def arm_shelf_max_depth(cab, std: Standard = STANDARD, arm: str = "a") -> Optional[int]:
    """The deepest an arm shelf along `arm` may be cut, rounded DOWN to a step.

    Two things bound it, and the tighter one wins (ruled 22 September 2026):

    (a) the closed door. The shelf stays behind the inner line by
        `Standard.mitre_shelf_clear`, and over the shelf's whole length that
        line comes nearest at the open-face end, where it is `face` from the
        carcass outside.
    (b) the hinge. The shelf ends against an open-face side panel, and the
        concealed hinge's mounting plate is fixed to that panel's inside face
        behind its front edge, so the shelf stops `Standard.hinge_clearance`
        short of it. Applied whichever side the door is hinged, because that can
        be changed without the shelf being recut.

    Both are measured from the wall side's inner face, a board thickness in, so
    both start from `face - t`. The answer is rounded DOWN to a multiple of
    `Standard.arm_shelf_step` before it is offered; a depth typed by hand is
    taken as typed and only has to come under it.

        arm_shelf_max_depth(EXAMPLE_MITRE)  ->  430
    """
    p = _mitre_parts(cab, std)
    if p is None:
        return None
    t, _a_a, _a_b, f_a, f_b = p
    face = f_b if arm == "b" else f_a
    limit = min((face - t) - std.mitre_shelf_clear,
                (face - t) - std.hinge_clearance)
    step = max(1, std.arm_shelf_step)
    return max(0, limit // step * step)


def arm_shelf_length(cab, std: Standard = STANDARD, arm: str = "a") -> Optional[int]:
    """How long an arm shelf is: that arm's internal span, wall side to wall side.

        arm_shelf_length(EXAMPLE_MITRE)  ->  818
    """
    blank = mitre_blank(cab, std)
    if blank is None:
        return None
    return blank[1] if arm == "b" else blank[0]


def arm_shelf_depth(cab, std: Standard = STANDARD) -> Optional[int]:
    """The depth an arm shelf is actually cut at: what was typed, or the maximum.

    A blank depth is not an error - the maximum is the sensible default and is
    what the editor offers. A depth OVER the maximum is a critical, raised by the
    validator, and is never silently clamped here: quietly cutting something
    other than what was typed is the one thing this app must not do.
    """
    top = arm_shelf_max_depth(cab, std, cab.arm_shelf_arm)
    if top is None:
        return None
    typed = cab.arm_shelf_depth
    return int(typed) if typed else top


# ---- what a blind corner measures ------------------------------------------


def blind_opening(cab, std: Standard = STANDARD) -> Optional[int]:
    """The clear opening a blind unit's door closes over: W - 2t - B.

        blind_opening(EXAMPLE_BLIND)  ->  468
    """
    if cab.corner_kind != "blind" or not cab.blind_width:
        return None
    return int(cab.width) - 2 * std.board_t - int(cab.blind_width)


def blind_door_width(cab, std: Standard = STANDARD) -> Optional[int]:
    """A blind unit's door, derived exactly as any other door is.

    An ordinary door covers its opening plus the two sides, less the single-door
    gap, so here that is (O + 2t) - door_single_gap = W - B - door_single_gap.
    The blind panel is no part of it: that is cut at exactly B, the width it was
    measured at, because the board size is the board size (ruled 22 Sept 2026).

        blind_door_width(EXAMPLE_BLIND)  ->  497
    """
    opening = blind_opening(cab, std)
    if opening is None:
        return None
    return opening + 2 * std.board_t - std.door_single_gap


def blind_panel_height(cab, std: Standard = STANDARD) -> Optional[int]:
    """A blind unit's flush panel, top to bottom: H - 2t.

    The panel sits INSIDE the carcass at the corner end, between the corner-end
    side panel and the opening, with its face flush with the carcass front edges
    so the whole front reads as one flush face (ruled 22 September 2026). It runs
    between the top and the bottom, which is H - 2t on a tall or a wall unit.

    A BASE unit has no top, and the figure is the same: the panel stands on the
    bottom and runs up to the underside of the front support, which is cut from
    the same board and lies flat with its face flush with the carcass top edge.
    That is the same H - 2t the engine already takes as a divider's default
    height, for the same reason, so nothing here is a second answer to it.

        blind_panel_height(EXAMPLE_BLIND)  ->  688
    """
    if cab.corner_kind != "blind" or not (cab.height or 0) > 0:
        return None
    return int(cab.height) - 2 * std.board_t


def blind_spans(cab, std: Standard = STANDARD):
    """Where a blind unit's three visible parts sit across its front.

    `(side, blind, door)`, each a `(start, end)` in cabinet-local mm from the
    unit's left edge as you face it - the frame `geometry`, the plan diagram and
    the wall elevation all use. Both drawings read this rather than laying the
    parts out themselves, so they cannot disagree with each other or with the
    cut list.

    * SIDE  - the corner-end side panel's front edge, one board wide.
    * BLIND - the flush panel, the full B, inside the carcass with its face on
      the front line. It starts one board in from the corner end, which is what
      changed on 22 September 2026: it used to be drawn across the corner end
      with no side beyond it.
    * DOOR  - an ordinary overlay door, half the single-door gap in from the far
      end, lapping the far side panel and the blind panel's face by
      `t - door_single_gap / 2` each. Its WIDTH is `blind_door_width` and is not
      derived again here; the inset construction did not move it.

        blind_spans(EXAMPLE_BLIND)  ->  ((984, 1000), (484, 984), (1.5, 498.5))
    """
    dw = blind_door_width(cab, std)
    if dw is None or dw <= 0:
        return None
    w, t, b = int(cab.width), std.board_t, int(cab.blind_width)
    gap = std.door_single_gap / 2
    if cab.hand == "L":
        return (0, t), (t, t + b), (w - gap - dw, w - gap)
    return (w - t, w), (w - t - b, w - t), (gap, gap + dw)


def panel_geometry(cab, std: Standard = STANDARD,
                   materials: dict = None) -> CabinetGeometry:
    """An independent panel's real size and shape, off its panel record.

    The two typed extents are two of the three; the third is the board's own
    thickness, which is why a panel never states one. Which physical direction
    each extent is depends on the orientation:

        upright   along the wall = a,  out from the wall = t,  up = b
        flat      along the wall = a,  out from the wall = b,  up = t
        end       along the wall = t,  out from the wall = a,  up = b

    A board the project does not carry has no thickness to read, and the
    validator names it; rather than a zero-depth footprint, the carcass board
    thickness stands in until it does.
    """
    spec = cab.panel_spec
    mats = MATERIALS if materials is None else materials
    t = material_thickness(mats, spec.board) or std.board_t
    a, b = int(spec.a or 0), int(spec.b or 0)
    if spec.orientation == "flat":
        width, depth, height = a, b, t
    elif spec.orientation == "end":
        width, depth, height = t, a, b
    else:                                      # upright, facing the room
        width, depth, height = a, t, b
    return CabinetGeometry(cab.number, rect_outline(width, depth), height,
                           depth, width, [], None, "panel")


def geometry(cab, std: Standard = STANDARD, materials: dict = None) -> CabinetGeometry:
    """One code path for every cabinet, template, bespoke or panel.

    The outline comes from the panel record if the item is a panel, then the
    corner parameters if the cabinet is a resolved corner unit, otherwise the
    cabinet's own entered outline, otherwise the rectangle its panels make.
    `source` says which — 'declared' only when the panels could not even give a
    width, which the validator reports.

    `materials` is only read for a panel, whose depth is its board's thickness.
    Nothing else here depends on it: the engine reads the boards for tapes and
    grain, never for a size, so every caller that leaves it out gets exactly the
    answer it always got.
    """
    from .engine import generate_cabinet      # engine imports this module; import at call time only
    if cab.is_panel:
        return panel_geometry(cab, std, materials)
    panels = generate_cabinet(cab, std, materials)
    sides = [p for p in panels if p.role == "Side"]
    carcass = [p for p in panels if p.role in CARCASS_ROLES]
    height = max((p.length for p in sides), default=0) or \
        max((p.length for p in carcass), default=cab.height)
    panel_depth = max((p.width for p in carcass), default=cab.depth)
    spans = [p.length for p in panels if p.role in ("Top", "Bottom")] or \
        [p.length for p in panels if p.role == "Support"]
    panel_width = max(spans) + 2 * std.board_t if spans else None

    corner = cab_corner_outline(cab)
    if corner is not None:
        outline = corner
        source = "corner"
    elif cab.footprint:
        outline = [(int(x), int(y)) for x, y in cab.footprint]
        source = "outline"
    elif panel_width is not None:
        outline = rect_outline(panel_width, panel_depth)
        source = "panels"
    else:
        outline = rect_outline(cab.width, panel_depth)
        source = "declared"
    door_widths = [p.width for p in panels if p.role == "Door" for _ in range(max(p.qty, 0))]
    runner = max((p.length for p in panels if p.role == "Drawer Side"), default=None)
    return CabinetGeometry(cab.number, outline, height, panel_depth, panel_width,
                           door_widths, runner, source)


def cabinet_footprint(rm: Room, placement, cab, std: Standard = STANDARD,
                      materials: dict = None) -> List[Tuple[int, int]]:
    """A cabinet's or a panel's outline in world plan coordinates.

    `Placement.y` is the standoff from the wall face. It is 0 on every carcass —
    a cabinet is against the wall it is placed on — and is what puts a bulkhead
    underside out over the units below it, which is where y is actually visible.
    """
    off = int(getattr(placement, "y", 0) or 0)
    return [to_world(rm, placement.wall, placement.x + lx, off + ly)[:2]
            for lx, ly in geometry(cab, std, materials).footprint]


def corner_shadow(rm: Room, cab, p, std: Standard = STANDARD):
    """(wall, x, width, depth) that a flush corner unit fills on the wall it
    turns onto — or None.

    A corner unit's `arm_a` runs along the wall it is placed on; its `arm_b`
    then runs on, physically, along whatever wall meets that one at the corner
    it stands in, because that is where wall B is in the cabinet's own frame.
    Gaps and runs are still found one wall at a time, and neither would
    otherwise know that space is filled — a straight run started flush against
    the corner would see nothing there and propose a filler for a gap that is
    not a gap. This is None unless the unit actually sits flush in that corner.

    The HAND says which corner that is (ruled 22 September 2026), and it decides
    both halves of the answer:

    * 'R' — the unit's right-hand end is in the corner, so cabinet-local
      x = `reach` has to land on the wall's END, wall B is the NEXT wall in the
      chain, and the shadow starts at its x = 0. That is what this function did
      before the hand existed, so a job written before it is unchanged.
    * 'L' — the left-hand end is in the corner, so the unit has to start at the
      wall's x = 0, wall B is the PREVIOUS wall, and the shadow sits at the END
      of it.

    A BLIND unit casts one too (ruled 22 September 2026). It is a plain
    rectangle, so its far arm is simply its own depth: it fills the first
    `depth` mm of the return wall, and the run there starts past it. Without
    this, `gaps` would offer a filler for the space the blind unit is standing
    in, which is exactly what a blind corner exists to avoid.
    """
    if not cab.corner_on:
        return None
    if cab.corner_kind == "blind":
        g = geometry(cab, std)
        # The unit's own footprint, never its declared figures: hard rule 1.
        reach, width, depth = g.width, g.depth, g.depth
    else:
        if geometry(cab, std).source != "corner":
            return None
        reach, width, depth = cab.arm_a, cab.arm_b, cab.face_b
    if not reach or not width or not depth:
        return None
    try:
        w = _wall(rm, p.wall)
    except ValueError:
        return None
    wall_ids = [x.id for x in rm.walls]
    i = wall_ids.index(p.wall)
    if cab.hand == "L":
        if p.x != 0:
            return None
        if not rm.closed and i == 0:
            return None
        prev_id = wall_ids[(i - 1) % len(wall_ids)]
        return prev_id, max(0, _wall(rm, prev_id).length - width), width, depth
    if p.x + reach != w.length:
        return None
    if not rm.closed and i == len(wall_ids) - 1:
        return None
    return wall_ids[(i + 1) % len(wall_ids)], 0, width, depth


def _shadow_geometry(cab, width: int, depth: int, std: Standard) -> CabinetGeometry:
    """A corner unit's far arm, described as its own rectangle purely so gaps
    and runs on the wall it lands on can treat it like any other occupant."""
    return CabinetGeometry(cab.number, rect_outline(width, depth),
                           geometry(cab, std).height, depth, width, [], None, "corner-shadow")


def _signed_area(poly) -> float:
    return sum(x0 * y1 - x1 * y0
               for (x0, y0), (x1, y1) in zip(poly, poly[1:] + poly[:1])) / 2


def _cross(o, a, b) -> float:
    return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])


def _clean(poly):
    """Drop repeated and collinear vertices; they stall ear clipping."""
    pts = [tuple(p) for p in poly]
    changed = True
    while changed and len(pts) > 3:
        changed = False
        for i in range(len(pts)):
            a, b, c = pts[i - 1], pts[i], pts[(i + 1) % len(pts)]
            if b == a or _cross(a, b, c) == 0:
                pts.pop(i)
                changed = True
                break
    return pts


def _in_triangle(p, a, b, c) -> bool:
    d1, d2, d3 = _cross(a, b, p), _cross(b, c, p), _cross(c, a, p)
    return not ((d1 < 0 or d2 < 0 or d3 < 0) and (d1 > 0 or d2 > 0 or d3 > 0))


def triangulate(poly) -> List[tuple]:
    """Ear clipping. Any simple polygon, either winding, into triangles."""
    pts = _clean(poly)
    if len(pts) < 3:
        return []
    if _signed_area(pts) < 0:
        pts.reverse()
    idx = list(range(len(pts)))
    tris = []
    while len(idx) > 3:
        for k in range(len(idx)):
            i0, i1, i2 = idx[k - 1], idx[k], idx[(k + 1) % len(idx)]
            a, b, c = pts[i0], pts[i1], pts[i2]
            if _cross(a, b, c) <= 0:
                continue                                    # reflex corner, not an ear
            if any(_in_triangle(pts[j], a, b, c) for j in idx if j not in (i0, i1, i2)):
                continue
            tris.append((a, b, c))
            idx.pop(k)
            break
        else:
            break                                           # not simple; keep what we have
    if len(idx) == 3:
        tris.append(tuple(pts[i] for i in idx))
    return tris


def _is_convex(poly) -> bool:
    signs = {(_cross(poly[i - 1], poly[i], poly[(i + 1) % len(poly)]) > 0)
             for i in range(len(poly))
             if _cross(poly[i - 1], poly[i], poly[(i + 1) % len(poly)]) != 0}
    return len(signs) <= 1


def polygons_overlap(a, b) -> bool:
    """True when two plan shapes share any area. Any simple polygon, any shape.

    A non-convex outline — a corner box's L — is split into triangles and each
    piece tested with the separating-axis test, which is exact for convex shapes
    and treats touching as clear. Two shapes that only share an edge, or one
    tucked exactly into the other's notch, do not overlap.
    """
    a, b = [tuple(p) for p in a], [tuple(p) for p in b]
    pieces_a = [a] if len(a) < 3 or _is_convex(a) else triangulate(a)
    pieces_b = [b] if len(b) < 3 or _is_convex(b) else triangulate(b)
    return any(convex_overlap(pa, pb) for pa in pieces_a for pb in pieces_b)


def placement_for(job, number: int) -> Optional[object]:
    """The placement of one cabinet, or None if it has not been placed."""
    for p in job.placements:
        if p.cabinet == number:
            return p
    return None


LAYERS = ("base", "wall", "tall")


def layer_of(cab, placement=None) -> str:
    """Which drawing layer a cabinet belongs to.

    Read off Cabinet.kind and Placement.z, with Placement.layer overriding both:

        kind 'tall'                 -> tall
        kind 'upper'                -> wall
        anything else with z above 0 -> wall, because that is what hung means
        otherwise                   -> base

    No new threshold is invented for the z test. Pinned in tools/check_room.py,
    not in a docstring example — the example checker cannot evaluate a call that
    has to build a Cabinet first.
    """
    if placement is not None and getattr(placement, "layer", None):
        return placement.layer
    if cab.kind == "tall":
        return "tall"
    if cab.kind == "upper":
        return "wall"
    if placement is not None and placement.z > 0:
        return "wall"
    return "base"


def run_key(layer: str) -> str:
    """Which run a cabinet belongs to: 'base' for anything standing on the floor,
    tall units included, 'wall' for anything hung.

    Layers are for drawing — base, wall and tall each get a toggle. Runs are
    about what shares the floor: a tall unit next to a base unit is in the same
    run, closes the same gaps and carries the same plinth board. Grouping runs by
    drawing layer made a tall unit invisible to the base run beside it.
    """
    return "wall" if layer == "wall" else "base"


def placed(job):
    """(cabinet, placement, layer) for every cabinet that has a place in the room.

    Cabinets with no placement are not in the room and are simply not returned —
    the caller reports them, it does not guess where they go.
    """
    out = []
    for cab in job.cabinets:
        # Cabinets only, explicitly. Gaps, runs, plinth, tip-up, door swing and
        # overlaps all come through here, and an independent panel takes part in
        # none of them — a panel is not a carcass standing on the floor and must
        # not close a gap or carry a plinth board.
        if cab.is_panel:
            continue
        p = placement_for(job, cab.number)
        if p is None:
            continue
        out.append((cab, p, layer_of(cab, p)))
    return out


def placed_panels(job):
    """(panel, placement) for every independent panel that has a place in the room.

    The panel-only twin of `placed()`, which stays cabinet-only. They are two
    lists rather than one on purpose: a panel is a part, not a carcass, so it
    must never reach gaps, runs, plinth, tip-up or door swing — but it is very
    much something to draw, to snap against and to report a clash with, and
    those callers come here.

    No layer: `room.LAYERS` is the three cabinet layers and `layer_of` is not
    asked about a panel. Panels are their own toggle in the plan, and in the
    wall elevation they are simply drawn.
    """
    out = []
    for cab in job.cabinets:
        if not cab.is_panel:
            continue
        p = placement_for(job, cab.number)
        if p is None:
            continue           # a panel cut and not put anywhere is normal
        out.append((cab, p))
    return out


def return_profiles(job, wall_id: str, std: Standard = STANDARD) -> List[dict]:
    """The cabinets on the walls either side, as this wall's elevation sees them.

    Face on to wall B, the run on wall A comes towards you at B's start corner,
    and what you see of it is the cabinets' sides, end on. Each cabinet on the
    two neighbouring walls is projected into this wall's frame off its real plan
    outline (`geometry`), so an out-of-square corner or a corner unit's L lands
    where it really is: `x0`/`x1` is the stretch of this wall it covers, clipped
    to the wall, and `z0`/`height` its real height (`carcass_z`). `out` is how far
    it stands out from this wall's face — the viewer is out in the room, so the
    larger it is the nearer the viewer, and the drawing puts those on top.

    The opposite wall is not included: it is behind anyone looking at this one.
    Nothing here is a new dimension — it is the same outline the plan draws, seen
    from the side.
    """
    rm = job.room
    if rm is None:
        return []
    ids = [w.id for w in rm.walls]
    if wall_id not in ids:
        return []
    i = ids.index(wall_id)
    beside = set()
    for j in (i - 1, i + 1):
        if 0 <= j < len(ids) or rm.closed:
            if len(ids) > 1:
                beside.add(ids[j % len(ids)])
    beside.discard(wall_id)
    here = _wall(rm, wall_id)
    (sx, sy), (dx, dy), (nx, ny) = wall_frames(rm)[here.id]
    out = []
    for cab, p, lay in placed(job):
        if p.wall not in beside:
            continue
        g = geometry(cab, std)
        pts = []
        for fx, fy in g.footprint:
            wx, wy, _ = to_world(rm, p.wall, p.x + fx, fy)
            pts.append(((wx - sx) * dx + (wy - sy) * dy,
                        (wx - sx) * nx + (wy - sy) * ny))
        if not pts:
            continue
        x0 = max(min(x for x, _ in pts), 0)
        x1 = min(max(x for x, _ in pts), here.length)
        if x1 <= x0 or min(y for _, y in pts) < -1:
            continue                     # not in front of this wall at all
        out.append({"cabinet": cab.number, "wall": p.wall, "layer": lay,
                    "x0": int(round(x0)), "x1": int(round(x1)),
                    "z0": carcass_z(cab, p, std), "height": g.height,
                    "out": int(round(min(y for _, y in pts)))})
    # nearest this wall first, so the one nearest the viewer is drawn last, on top
    out.sort(key=lambda r: r["out"])
    return out


# --- gaps -------------------------------------------------------------------

@dataclass
class Gap:
    """A gap the app found. Geometry and a suggestion — never a decision.

    `nominal` is the gap at the wall face and `front` the gap at the front of the
    run. They differ when the corner is out of square, and that difference is the
    taper: a parallel strip cannot fill a tapered gap, and the beam saw cannot
    cut a tapered one, so the panel goes out at its widest and gets scribed.
    """
    wall: str
    layer: str
    after: Optional[int]
    before: Optional[int]
    x: int                 # where the gap starts along the wall
    nominal: int           # width at the wall face
    front: int             # width at the front of the run
    depth: int
    height: int
    board: str             # the exterior board of the cabinet that bounds it
    proposal: str          # 'filler' | 'grow' | 'cabinet'
    treatment: str         # what was decided, or '' for undecided

    @property
    def width(self) -> int:
        """The widest the gap gets. A filler is cut to this, plus the scribe."""
        return max(self.nominal, self.front)

    @property
    def taper(self) -> int:
        return abs(self.front - self.nominal)

    def filler_width(self, std: Standard = STANDARD) -> int:
        return self.width + std.scribe_allowance


# --- placement: overlaps, snapping, swings ----------------------------------

@dataclass
class Overlap:
    """Two cabinets trying to occupy the same stretch of wall."""
    a: int
    b: int
    wall: str
    layer: str
    mm: int

    @property
    def across(self) -> bool:
        """Whether the two stand on different walls (wall reads 'A/B'). The wall
        elevation read this and it did not exist, so any overlap at all made the
        elevation fail with an AttributeError (found 22 Sept 2026)."""
        return "/" in self.wall


def _z_span(cab, p, g, std) -> Tuple[int, int]:
    z0 = carcass_z(cab, p, std)
    return z0, z0 + g.height


def overlaps(job, std: Standard = STANDARD) -> List[Overlap]:
    """Cabinets that collide: heights that overlap, outlines that share area.

    Checked in world coordinates, across every wall at once — not grouped by
    wall first — because a corner unit's far arm genuinely stands in the next
    wall's space, and a cabinet placed too close to it there is a real clash a
    same-wall-only check would never see. For two cabinets on the same wall
    this is exactly the old same-wall check, just carried out after mapping
    both footprints through the same wall's frame, which changes nothing about
    whether they overlap.

    Outlines, not spans, so a straight unit tucked into a corner box's notch is
    not a collision even though their extents along the wall overlap. Heights,
    not layers: an overhead passes above the base run, but a tall unit stands on
    the same floor as the base unit beside it and can very much hit it.
    """
    if job.room is None:
        return []
    rm = job.room
    wall_ids = {w.id for w in rm.walls}
    items = []
    for cab, p, lay in placed(job):
        if p.wall not in wall_ids:
            continue        # not a real wall; _room() reports that on its own
        g = geometry(cab, std, job.materials)
        items.append((cab, p, g, lay, cabinet_footprint(rm, p, cab, std, job.materials),
                      _z_span(cab, p, g, std)))
    out = []
    for i, (a, pa, ga, la, fa, za) in enumerate(items):
        for b, pb, gb, _lb, fb, zb in items[i + 1:]:
            if za[0] >= zb[1] or zb[0] >= za[1]:
                continue                           # they pass at different heights
            if not polygons_overlap(fa, fb):
                continue
            if pa.wall == pb.wall:
                along = max(min(pa.x + ga.width, pb.x + gb.width) - max(pa.x, pb.x), 0)
                wall = pa.wall
            else:
                along = 0          # not one stretch of one wall — nothing to measure "along"
                wall = f"{pa.wall}/{pb.wall}"
            out.append(Overlap(a=a.number, b=b.number, wall=wall, layer=run_key(la), mm=along))
    return out


def _on_wall(job, wall_id: str, std: Standard, exclude: int = None):
    """Everything already standing on one wall, carcass or panel alike:
    `(item, placement, geometry, layer, z_span)`, the layer being `"panel"` for
    a panel, which has none of the three cabinet layers.

    `placed()` and `placed_panels()` are deliberately two lists — a panel must
    never reach gaps, runs, plinth or tip-up. This is the one place they are
    read together, because coming to rest against something does not care what
    kind of thing it is: a bulkhead front lands on the cabinet tops below it,
    and the second panel of a bulkhead butts against the first.

    The boards are read for the geometry, because a panel's third extent is its
    board's own thickness. Nothing a cabinet answers changes for it.
    """
    mats = job.materials
    out = []
    for cab, p, lay in placed(job):
        if p.wall != wall_id or cab.number == exclude:
            continue
        g = geometry(cab, std, mats)
        out.append((cab, p, g, lay, _z_span(cab, p, g, std)))
    for cab, p in placed_panels(job):
        if p.wall != wall_id or cab.number == exclude:
            continue
        g = geometry(cab, std, mats)
        out.append((cab, p, g, "panel", _z_span(cab, p, g, std)))
    return out


def free_x(job, number: int, wall_id: str, std: Standard = STANDARD) -> int:
    """Where a newly-placed item goes so it lands clear of what is already there.

    Giving a cabinet or a panel a wall used to put it at 0 mm whatever else was
    on that wall, which dropped it straight on top of the first thing there and
    out of sight underneath it. The candidates are the ones a drag already
    reads — the wall start, and the right-hand edge of everything already
    placed — and the first that leaves this item clear of all of them wins.
    Worked out here, never in the browser.

    An item that fits nowhere on the wall comes to rest against the end of the
    run, clamped to the wall. That is an honest overlap the validator will name,
    which is better than a position nothing worked out.
    """
    rm = job.room
    if rm is None:
        return 0
    cab = next((c for c in job.cabinets if c.number == number), None)
    if cab is None:
        return 0
    try:
        w = _wall(rm, wall_id)
    except ValueError:
        return 0
    width = geometry(cab, std, job.materials).width
    max_x = max(w.length - width, 0)
    taken = []
    for other, op, og, other_lay, _oz in _on_wall(job, wall_id, std, exclude=number):
        # Nothing is placed yet, so there is no height to compare against: the
        # same fallback `snap_points` makes, which is the run it will land in.
        # A panel has no run and is kept clear of everything on the wall.
        if not cab.is_panel and other_lay != "panel" and            run_key(other_lay) != run_key(layer_of(cab)):
            continue
        taken.append((op.x, op.x + og.width))
    if not taken:
        return 0
    for x in sorted({0} | {b for _a, b in taken}):
        if x > max_x:
            break
        if all(x >= b or x + width <= a for a, b in taken):
            return int(x)
    return int(min(max(b for _a, b in taken), max_x))


def snap_points(job, number: int, wall_id: str, std: Standard = STANDARD):
    """Where a cabinet or a panel may come to rest on a wall, and why.

    The engine decides every candidate. A drag in the browser only picks the
    nearest of these — it never works one out for itself.
    """
    rm = job.room
    if rm is None:
        return []
    cab = next((c for c in job.cabinets if c.number == number), None)
    if cab is None:
        return []
    try:
        w = _wall(rm, wall_id)
    except ValueError:
        return []

    here = placement_for(job, number)
    g = geometry(cab, std, job.materials)
    width = g.width
    mine = _z_span(cab, here, g, std) if here else None
    out = [(0, "wall start"), (max(w.length - width, 0), "wall end")]

    for other, op, og, other_lay, oz in _on_wall(job, wall_id, std, exclude=number):
        if mine is None:
            # not placed yet, so no height to compare: the run it will land in.
            # A panel has no run, and butts against whatever is there.
            if not cab.is_panel and other_lay != "panel" and                run_key(other_lay) != run_key(layer_of(cab)):
                continue
        elif mine[0] >= oz[1] or oz[0] >= mine[1]:
            continue                               # nothing to butt against up there
        out.append((op.x + og.width, f"right of {other.number}"))
        out.append((op.x - width, f"left of {other.number}"))
    for op in w.openings:
        out.append((op.x + op.width, f"clear of the {op.kind}"))
        out.append((op.x - width, f"clear of the {op.kind}"))

    seen, keep = set(), []
    for x, why in sorted(out):
        if 0 <= x <= w.length - width and x not in seen:
            seen.add(x)
            keep.append({"x": int(x), "why": why})
    return keep


def _gap_along(mine, span) -> int:
    """How far apart two stretches of one wall are, 0 where they touch or overlap.

    `span` of None is a datum that runs the whole wall — the floor, the ceiling,
    an opening's sill or head — which is never "far" from anything.
    """
    if span is None:
        return 0
    return max(0, span[0] - mine[1], mine[0] - span[1])


def _hangs_clear(z: int, cab, std: Standard = STANDARD) -> bool:
    """Whether `z` is a height this item could really come to rest at.

    The floor is offered separately and unconditionally, so all this ever rules
    out is the strip between the floor and the plinth top.

    A carcass that stands on the floor stands on its legs, so hanging one in that
    strip would put it lower than its own legs would stand it — and worse, any z
    above 0 reads as hung (`layer_of`), so a base unit snapped to the plinth top
    would quietly change drawing layer while standing exactly where it already
    was. It is offered nothing there; z of 0 is the honest answer.

    A PANEL stands on nothing and an upper is hung by definition, so for those any
    height clear of the floor is real — a bulkhead end cap 60 mm up is a part put
    where it is put, and `Test.json`'s panel 8 lives on the plinth top itself.
    """
    if z <= 0:
        return False
    if cab.is_panel or cab.kind == "upper":
        return True
    return z > std.leg_height


def z_snap_points(job, number: int, wall_id: str, std: Standard = STANDARD,
                  at_x=None, spans: bool = False):
    """How high a cabinet may come to rest on a wall, and why.

    The vertical twin of `snap_points`, under the same discipline: the engine
    names every height a drag is allowed to settle on and the browser picks the
    nearest of them, so a dragged cabinet can never come to rest at a height
    nothing worked out.

    The figure is `Placement.z` — 0 meaning it stands on the floor, where the
    carcass is lifted by its legs, and anything above it the underside of a hung
    unit. Only cabinets that actually overlap this one along the wall count: a
    unit three metres away is nothing to sit on top of.

    Brought to parity with `snap_points` on 21 September 2026. Every datum the
    horizontal axis offers has a vertical twin: the wall ends answer to the floor
    and the ceiling, a neighbour's left and right edges to its top and its
    underside — which is `carcass_z`, the PLINTH TOP, never 0 — and an opening's
    two jambs to its sill and its head. Openings were the one real gap: the wall
    elevation has drawn both lines since it was built and nothing could snap to
    either. Every figure still comes off `geometry` and the placements; nothing
    here reads a declared height.

    `at_x` asks the question at a position other than where the cabinet stands —
    a drag that has moved sideways is asking about where it is going, not where
    it started. `spans` hands back every candidate with the stretch of wall it
    applies over (`x0`/`x1`, both None for the floor and the ceiling) instead of
    filtering to one position, which is what a drag needs: the cabinet crosses
    several of them on the way, and re-asking the engine on every pointer move
    would be a round trip per pixel. The browser then tests overlap and picks the
    nearest — a comparison between candidates the engine named, which is the same
    bargain the plan drag already makes.
    """
    rm = job.room
    if rm is None:
        return []
    cab = next((c for c in job.cabinets if c.number == number), None)
    if cab is None:
        return []
    try:
        w = _wall(rm, wall_id)
    except ValueError:
        return []

    here = placement_for(job, number)
    g = geometry(cab, std, job.materials)
    x0 = at_x if at_x is not None else (here.x if here is not None else 0)
    x1 = x0 + g.width
    # (z, why, applies over x0..x1, applies everywhere except over nx0..nx1)
    out = [(0, "on the floor", None, None, None, None)]
    if rm.ceiling:
        out.append((max(rm.ceiling - g.height, 0), "tight to the ceiling",
                    None, None, None, None))

    for other, op, og, _lay, _oz in _on_wall(job, wall_id, std, exclude=number):
        ox0, ox1 = op.x, op.x + og.width
        over = not (ox0 >= x1 or ox1 <= x0)    # above or below it, at this position
        oz = carcass_z(other, op, std)
        if spans or over:
            out.append((oz + og.height, f"on top of {other.number}", ox0, ox1, None, None))
            under = oz - g.height
            if _hangs_clear(under, cab, std):
                out.append((under, f"under {other.number}", ox0, ox1, None, None))
        # Lining up with a neighbour rather than stacking on it (18 Sept 2026): a
        # wall unit beside a tall unit wants its top level with the tall unit's
        # top, and two wall units want their undersides level. That holds anywhere
        # along the wall EXCEPT over or under the other cabinet, where level tops
        # would put one inside the other — so it carries the stretch it does not
        # apply over.
        #
        # The neighbour's underside is `carcass_z`, never 0: a carcass standing on
        # the floor stands on its legs, so its bottom edge is the PLINTH TOP. It
        # was reported as 0, which is a leg height out for anything lining up with
        # it — and `Test.json`'s own placed panel sits at exactly that height with
        # nothing to drag it back to (21 September 2026).
        if spans or not over:
            for z, why in ((oz + og.height - g.height, f"tops level with {other.number}"),
                           (oz, f"bottoms level with {other.number}")):
                if _hangs_clear(z, cab, std):
                    out.append((z, why, None, None, ox0, ox1))

    # An opening is a datum, the same as a neighbour and the same as the ceiling:
    # a wall unit goes above the head, a base unit's top comes under the sill, and
    # a run lines up with either. `snap_points` has offered both jambs since the
    # drag was built and this offered nothing at all, which is the one place the
    # two axes really diverged (21 September 2026). A datum runs the length of the
    # wall, so these carry no stretch — lining up with a window head beside the
    # window is as much the point as sitting over it.
    for op in w.openings:
        kind = op.kind
        for z, why in ((op.head, f"above the {kind}"),
                       (op.sill - g.height, f"below the {kind}"),
                       (op.head - g.height, f"tops level with the {kind} head"),
                       (op.sill, f"bottoms level with the {kind} sill")):
            if _hangs_clear(z, cab, std):
                out.append((z, why, None, None, None, None))

    # A measured ceiling caps how high the underside may go. The floor is never
    # capped out of the list: standing on the floor is where a carcass starts,
    # and a ceiling too low for the cabinet is the ceiling check's to report, not
    # something to answer by offering nowhere to put it.
    limit = rm.ceiling - g.height if rm.ceiling else None

    def near(row):
        """How far along the wall the neighbour this candidate came from is.

        Several cabinets standing on the floor put their undersides on the same
        line, so a whole row of candidates can share one z and differ only in
        which one they name. Sorted on the reason alone that was answered
        alphabetically — `Test.json`'s panel 8 read "bottoms level with 1" with
        cabinet 7 the one touching it. Every one of them is true; the nearest is
        the one worth saying, and in the list without `spans` it is the only one
        that survives the de-duplication below (21 September 2026).

        A stack row carries its neighbour's stretch in x0/x1, a level line in
        not_x0/not_x1, and a wall-wide datum carries neither.
        """
        _z, _why, a, b, na, nb = row
        span = (a, b) if a is not None else ((na, nb) if na is not None else None)
        return _gap_along((x0, x1), span)

    seen, keep = set(), []
    for z, why, a, b, na, nb in sorted(out, key=lambda r: (r[0], near(r), r[1])):
        z = int(z)
        key = (z, a, b, na, nb) if spans else z
        if z < 0 or key in seen or (limit is not None and z > limit and z != 0):
            continue
        seen.add(key)
        row = {"z": z, "why": why}
        if spans:
            row["x0"], row["x1"] = a, b
            if na is not None:
                row["not_x0"], row["not_x1"] = na, nb
        keep.append(row)
    return keep


def _arc(cx, cy, r, a0, a1, steps=10):
    return [(cx + r * math.cos(a0 + (a1 - a0) * i / steps),
             cy + r * math.sin(a0 + (a1 - a0) * i / steps))
            for i in range(steps + 1)]


def _edge_hinge(outline, p0: Point, p1: Point, hinge_at_p0: bool):
    """A door hinge on one end of a front-face edge p0->p1, taken in the
    outline's own point order — the hinge point, the closed-door angle, and
    which way it turns to sweep into the room.

    Works for either winding: the room lies 90 degrees from the edge direction,
    on whichever side is *not* the polygon's own interior, so the turn's sign
    just follows the polygon's winding, whichever end carries the hinge.
    """
    ccw = _signed_area(outline) > 0
    turn = -1 if ccw else 1
    if hinge_at_p0:
        return p0, math.atan2(p1[1] - p0[1], p1[0] - p0[0]), turn
    return p1, math.atan2(p0[1] - p1[1], p0[0] - p1[0]), -turn


def _corner_door_hinges(cab, g: CabinetGeometry, p):
    """Hinge points for a corner unit's doors, off its real front face(s) —
    the mitre edge, or for an ell whichever of its two faces carries the door —
    rather than the outline's extreme corners (ruled 14 Sept 2026, spec item
    13). On a mitre, `flip` picks the wall-B-side hinge over the default
    wall-A-side one, the same handedness switch a single door on a straight
    cabinet uses. An ell with two doors hangs one on each face, from the ends
    away from the notch. An ell with one door hangs it on the shortest face it
    fits — the longest if it fits neither — from that face's outer end, or its
    inner end (the notch) if flipped.
    """
    outline = g.footprint
    n = len(g.door_widths)
    # 'R' is the wall-B-side end on a mitre and the notch end on an ell — the
    # same handedness Placement.flip has always meant, now nameable per leaf.
    right = [hinge_side(cab, i, n, p.flip) == "R" for i in range(max(n, 1))]
    if len(outline) == 5:                    # mitre: one diagonal front face
        d, e = outline[3], outline[4]
        pt, a0, sign = _edge_hinge(outline, d, e, hinge_at_p0=right[0])
        return [(pt, a0, sign, g.door_widths[0])]
    d, e, f = outline[3], outline[4], outline[5]     # ell: two faces off the notch
    if len(g.door_widths) >= 2:
        h1 = _edge_hinge(outline, e, f, hinge_at_p0=False)
        h2 = _edge_hinge(outline, d, e, hinge_at_p0=True)
        return [(*h1, g.door_widths[0]), (*h2, g.door_widths[-1])]
    w = g.door_widths[0]
    # (edge as the outline orders it, its outer end is p0?, length)
    faces = [((e, f), False, math.dist(e, f)),       # wall-A side: outer end is f
             ((d, e), True, math.dist(d, e))]        # wall-B side: outer end is d
    fits = [fc for fc in faces if fc[2] >= w]
    (p0, p1), outer_is_p0, _ = min(fits, key=lambda fc: fc[2]) if fits \
        else max(faces, key=lambda fc: fc[2])
    hinge = _edge_hinge(outline, p0, p1, hinge_at_p0=outer_is_p0 != right[0])
    return [(*hinge, w)]


def swing_envelopes(job, cab, p, std: Standard = STANDARD):
    """The quarter discs a cabinet's doors sweep, in world plan coordinates.

    Which edge each leaf hangs from is `model.hinge_side` — the per-leaf choice on
    the cabinet, or the old rule when none is set: a pair at its outer edges
    opening from the middle, a single door left unless the placement is flipped.
    The elevation's hinge marks read the same function, so the two drawings
    cannot disagree. A corner unit hinges off its real front face instead — see
    `_corner_door_hinges`.
    """
    if job.room is None:
        return []
    g = geometry(cab, std)
    if not g.door_widths:
        return []
    rm = job.room
    span = math.radians(std.door_open_deg)

    if g.source == "corner":
        hinge_specs = _corner_door_hinges(cab, g, p)
    else:
        xs = [x for x, _ in g.footprint]
        left, right = min(xs), max(xs)
        n = len(g.door_widths)

        def front_at(x):    # the outline's front edge at that end, where a hinge sits
            at = [y for px, y in g.footprint if px == x]
            return max(at) if at else max(y for _, y in g.footprint)

        # Each leaf hangs off its own end, not the carcass's: leaf i covers its
        # share of the opening, and hinges left or right within that share. With
        # no per-leaf choice set this is exactly what it always was — a single
        # door on the carcass edge, a pair on the two outer edges.
        hinge_specs = []
        for i, w in enumerate(g.door_widths):
            a = left + (right - left) * i / n
            b = left + (right - left) * (i + 1) / n
            if hinge_side(cab, i, n, p.flip) == "R":
                hinge_specs.append(((b, front_at(b)), math.pi, -1, w))
            else:
                hinge_specs.append(((a, front_at(a)), 0.0, +1, w))

    out = []
    for (hx, hy), a0, sign, w in hinge_specs:
        a1 = a0 + span * sign
        pts = [(p.x + hx, hy)] + _arc(p.x + hx, hy, w, a0, a1)
        out.append([to_world(rm, p.wall, int(round(lx)), int(round(ly)))[:2]
                    for lx, ly in pts])
    return out


def pullout_envelope(job, cab, p, std: Standard = STANDARD):
    """The box a drawer needs in front of the cabinet to come all the way out —
    as far as the drawer sides that were actually cut are long."""
    if job.room is None:
        return None
    g = geometry(cab, std)
    if g.runner is None:
        return None
    xs = [x for x, _ in g.footprint]
    x0, x1, d = p.x + min(xs), p.x + max(xs), g.depth
    local = [(x0, d), (x1, d), (x1, d + g.runner), (x0, d + g.runner)]
    return [to_world(job.room, p.wall, lx, ly)[:2] for lx, ly in local]


def _axes(poly):
    for i in range(len(poly)):
        (x0, y0), (x1, y1) = poly[i], poly[(i + 1) % len(poly)]
        dx, dy = x1 - x0, y1 - y0
        if dx or dy:
            yield (-dy, dx)


def _overlap_on(axis, a, b):
    ax, ay = axis
    pa = [ax * x + ay * y for x, y in a]
    pb = [ax * x + ay * y for x, y in b]
    return min(pa) < max(pb) and min(pb) < max(pa)


def convex_overlap(a, b) -> bool:
    """Separating-axis test. True when two convex shapes genuinely intersect.

    Touching exactly counts as clear: a cabinet butted against its neighbour is
    the normal case, not a clash.
    """
    if len(a) < 2 or len(b) < 2:
        return False
    return all(_overlap_on(ax, a, b) for ax in list(_axes(a)) + list(_axes(b)))


@dataclass
class Clash:
    cabinet: int
    kind: str          # 'door' | 'drawer'
    against: str
    detail: str = ""


def clashes(job, std: Standard = STANDARD) -> List[Clash]:
    """Doors that cannot open and drawers that cannot come out.

    Checked against the other cabinets whose heights actually overlap, and
    against every wall but the one the cabinet stands on. A door never fouls its
    own wall, because it opens away from it.
    """
    rm = job.room
    if rm is None:
        return []
    items = placed(job)
    corners = corner_points(rm)
    out: List[Clash] = []

    geoms = {cab.number: geometry(cab, std) for cab, _p, _l in items}
    for cab, p, _lay in items:
        z0 = carcass_z(cab, p, std)          # on its legs, if it stands on the floor
        zt = (z0, z0 + geoms[cab.number].height)
        envelopes = [("door", e) for e in swing_envelopes(job, cab, p, std)]
        pull = pullout_envelope(job, cab, p, std)
        if pull:
            envelopes.append(("drawer", pull))

        for kind, env in envelopes:
            for other, op, _ol in items:
                if other.number == cab.number:
                    continue
                oz0 = carcass_z(other, op, std)
                oz = (oz0, oz0 + geoms[other.number].height)
                if zt[0] >= oz[1] or oz[0] >= zt[1]:
                    continue                      # they pass at different heights
                if polygons_overlap(env, cabinet_footprint(rm, op, other, std)):
                    out.append(Clash(cab.number, kind, f"cabinet {other.number}"))
            for i, w in enumerate(rm.walls):
                if w.id == p.wall:
                    continue
                if convex_overlap(env, [corners[i], corners[i + 1]]):
                    out.append(Clash(cab.number, kind, f"wall {w.id}"))
    seen, keep = set(), []
    for c in out:
        key = (c.cabinet, c.kind, c.against)
        if key not in seen:
            seen.add(key)
            keep.append(c)
    return keep


@dataclass
class PanelClash:
    """An independent panel standing in something else's space."""
    panel: int
    against: str           # what it stands in, in words
    wall: str


def panel_clashes(job, std: Standard = STANDARD) -> List[PanelClash]:
    """Panels that stand in something else's space. A WARNING, never a critical.

    Two carcasses sharing a stretch of wall is a critical because the cut list
    built on it is wrong. A panel is a different kind of thing: a bulkhead front
    is MEANT to sit flush on the cabinet tops and hard against the ceiling, and
    exactly how far it laps a carcass is a judgement about how the job is built,
    not an arithmetic error. So this reports and does not block.

    The tests are the ones already here and nothing new: `polygons_overlap` on
    the plan outlines — which treats touching as clear, so a panel resting on a
    run is not a clash — and `_z_span` on the heights, so a bulkhead above a
    base run does not read as standing in it. An opening uses the same
    across-and-level test `blocked_openings` makes for a carcass.
    """
    rm = job.room
    if rm is None:
        return []
    mats = job.materials
    walls = {w.id: w for w in rm.walls}
    mine = []
    for cab, p in placed_panels(job):
        if p.wall not in walls:
            continue           # not a real wall; _room() reports that on its own
        g = geometry(cab, std, mats)
        mine.append((cab, p, g, cabinet_footprint(rm, p, cab, std, mats),
                     _z_span(cab, p, g, std)))
    if not mine:
        return []
    boxes = []
    for cab, p, _lay in placed(job):
        if p.wall not in walls:
            continue
        g = geometry(cab, std, mats)
        boxes.append((f"cabinet {cab.number}",
                      cabinet_footprint(rm, p, cab, std, mats),
                      _z_span(cab, p, g, std)))

    out = []
    for i, (cab, p, g, fp, zs) in enumerate(mine):
        against = list(boxes)
        for other, _op, _og, ofp, ozs in mine[i + 1:]:
            against.append((f"panel {other.number}", ofp, ozs))
        for what, ofp, ozs in against:
            if zs[0] >= ozs[1] or ozs[0] >= zs[1]:
                continue                          # they pass at different heights
            if polygons_overlap(fp, ofp):
                out.append(PanelClash(cab.number, what, p.wall))
        w = walls[p.wall]
        for op in w.openings:
            across = p.x < op.x + op.width and op.x < p.x + g.width
            level = zs[0] < op.head and op.sill < zs[1]
            if across and level:
                out.append(PanelClash(cab.number, f"the {op.kind} on wall {w.id}",
                                      p.wall))
    return out


@dataclass
class Run:
    """A continuous stretch of cabinetry on one wall at one height.

    A filler or a blind corner continues a run; a gap left open breaks it,
    because a plinth board cannot span an appliance space. An undecided gap
    breaks it too — the conservative way round, and it already carries a warning
    of its own.
    """
    wall: str
    layer: str
    z: int
    cabinets: List[int]
    x0: int
    x1: int
    depth: int
    divisions: List[int]       # cabinet joins inside the run, where a long plinth splits
    touches_start: bool        # reaches the wall's start corner
    touches_end: bool

    @property
    def first(self) -> int:
        return self.cabinets[0]

    @property
    def length(self) -> int:
        return self.x1 - self.x0


CONTINUES = ("filler", "blind")


def runs(job, std: Standard = STANDARD) -> List[Run]:
    """Every continuous run of cabinetry, per wall and per layer."""
    rm = job.room
    if rm is None:
        return []
    wall_ids = [w.id for w in rm.walls]
    found = {(g.wall, g.layer, g.after, g.before): g for g in gaps(job, std)}

    grouped: Dict[Tuple[str, str], list] = {}
    for cab, p, lay in placed(job):
        if p.wall in wall_ids:
            grouped.setdefault((p.wall, run_key(lay)), []).append((p.x, cab, p, geometry(cab, std)))
    for cab, p, lay in placed(job):
        shadow = corner_shadow(rm, cab, p, std)
        if shadow is None:
            continue
        next_id, at, width, depth = shadow
        grouped.setdefault((next_id, run_key(lay)), []).append(
            (at, cab, p, _shadow_geometry(cab, width, depth, std)))

    out: List[Run] = []
    for (wid, lay), items in sorted(grouped.items()):
        items.sort(key=lambda t: t[0])
        w = _wall(rm, wid)

        segments = [[items[0]]]
        for (_, prev, _p0, _g0), item in zip(items, items[1:]):
            g = found.get((wid, lay, prev.number, item[1].number))
            if g is not None and g.treatment not in CONTINUES:
                segments.append([item])
            else:
                segments[-1].append(item)

        for si, seg in enumerate(segments):
            x0 = seg[0][0]
            x1 = seg[-1][0] + seg[-1][3].width
            touches_start = x0 == 0
            touches_end = x1 == w.length
            if si == 0:
                lead = found.get((wid, lay, None, seg[0][1].number))
                if lead is not None and lead.treatment in CONTINUES:
                    x0, touches_start = 0, True
            if si == len(segments) - 1:
                tail = found.get((wid, lay, seg[-1][1].number, None))
                if tail is not None and tail.treatment in CONTINUES:
                    x1, touches_end = w.length, True
            out.append(Run(
                wall=wid, layer=lay, z=min(p.z for _, _, p, _ in seg),
                cabinets=[c.number for _, c, _, _ in seg], x0=x0, x1=x1,
                depth=max(g.depth for _, _, _, g in seg),
                divisions=[x + g.width for x, _, _, g in seg[:-1]],
                touches_start=touches_start, touches_end=touches_end))
    return out


def plinth_choice_for(job, run: Run):
    for p in job.plinths:
        if (p.wall, p.layer, p.first) == (run.wall, run.layer, run.first):
            return p
    return None


def plinth_butt_wall(job, run: Run, std: Standard = STANDARD) -> Optional[str]:
    """The wall whose plinth this run's board butts into, if any.

    Internal corners butt: one run continues past, the other stops square
    against it. The run on the earlier wall continues, so each corner shortens
    exactly one of the two boards — never both, which would leave a gap, and
    never neither, which would not fit.
    """
    rm = job.room
    if rm is None or not run.touches_start:
        return None
    wall_ids = [w.id for w in rm.walls]
    i = wall_ids.index(run.wall)
    if i == 0 and not rm.closed:
        return None
    prev_id = wall_ids[i - 1]
    for other in runs(job, std):
        if (other.wall == prev_id and other.z == run.z and other.touches_end
                and _plinth_fitted(job, other)):
            return prev_id
    return None


def plinth_deduction(job, run: Run, std: Standard = STANDARD) -> int:
    """How much this run's plinth loses to a butt joint at its start corner."""
    return std.board_t if plinth_butt_wall(job, run, std) else 0


def _plinth_fitted(job, run: Run) -> bool:
    c = plinth_choice_for(job, run)
    return bool(c and c.fitted)


def plinth_lengths(job, run: Run, std: Standard = STANDARD) -> List[Tuple[int, int]]:
    """(length, start offset) of each board this run's plinth needs.

    A run longer than a board gets split at a cabinet division rather than
    wherever the arithmetic lands, so the joint falls behind a carcass side.
    """
    start = run.x0 + plinth_deduction(job, run, std)
    total = run.x1 - start
    if total <= 0:
        return []
    if total <= std.sheet_l:
        return [(total, start)]

    out = []
    at = start
    divisions = [d for d in run.divisions if d > start] + [run.x1]
    while run.x1 - at > std.sheet_l:
        usable = [d for d in divisions if d > at and d - at <= std.sheet_l]
        if not usable:
            break                      # one cabinet wider than a board; W2 will say so
        cut = max(usable)
        out.append((cut - at, at))
        at = cut
    out.append((run.x1 - at, at))
    return out


# --- heights ----------------------------------------------------------------

def carcass_z(cab, p, std: Standard = STANDARD) -> int:
    """Floor to the underside of the carcass, in mm.

    Every carcass that stands on the floor stands on its legs — always, kitchen
    or wardrobe, plinth board or not. So a standing cabinet (Placement.z of 0,
    and not a hung unit) starts leg_height up. The plinth board only covers the
    legs; it never changes this height, and nothing here asks whether one is
    fitted. Corrected 14 Sept 2026: the first version lifted only plinthed runs.

    The elevation, the clash check, the opening check and the ceiling check all
    ask here, so they cannot disagree about how high a cabinet really is.
    """
    return std.leg_height if stands_on_legs(cab, p) else p.z


def stands_on_legs(cab, p) -> bool:
    """Whether a carcass stands on the floor — and so, always, on its legs.

    Placement.z of 0 and not a hung unit. There is no standing case without legs,
    so this is the one question every height check asks.

    A panel is never on legs: it is a part, put where it is put, so its z is its
    underside exactly as typed.
    """
    if cab.is_panel:
        return False
    return p.z == 0 and layer_of(cab, p) != "wall"


def tip_clearance(height: int, depth: int, legs: int, setback: Optional[int] = None) -> int:
    """Ceiling height needed to tip a carcass upright, in mm, rounded up.

    Every carcass is built flat on its back and tipped up in one piece. From the
    side it is a D x H rectangle with legs L below its bottom, the rear legs set s
    in from the back face. On the way up it pivots first on its bottom back edge,
    then — once the rear feet touch down, where tan(angle from upright) = L / s —
    on the rear feet. The top front edge is always the highest point:

        on the rear feet    (D - s) sin t + (H + L) cos t    peak  sqrt((D - s)^2 + (H + L)^2)
        on the back edge     D sin t + H cos t               peak  sqrt(D^2 + H^2)

    A peak counts only if its angle falls inside that phase; otherwise the phase is
    highest where it ends. The clearance is the larger of the two. Room depth does
    not enter: the sweep is a rotation about a point on the floor.

    The check passes Standard.leg_setback, ruled at 50. `setback` None takes s = 0,
    legs at the back edge — exact there, and the upper bound for any leg position
    between the faces, which is what the examples without a setback show.

        tip_clearance(2400, 580, 100)  ->  2567
        tip_clearance(2400, 580, 100, 50)  ->  2556
        tip_clearance(720, 580, 100)  ->  1005
        tip_clearance(720, 580, 100, 200)  ->  925
        tip_clearance(700, 300, 0)  ->  762
    """
    s = 0 if setback is None else setback
    switch = math.atan2(legs, s)          # angle from upright at which the rear feet land

    def peak(a, b, lo, hi):
        best = math.atan2(a, b)
        if lo <= best <= hi:
            return math.hypot(a, b)
        return max(a * math.sin(t) + b * math.cos(t) for t in (lo, hi))

    on_feet = peak(depth - s, height + legs, 0.0, switch)
    on_edge = peak(depth, height, switch, math.pi / 2)
    return math.ceil(max(on_feet, on_edge))


def tip_problems(job, std: Standard = STANDARD) -> List[Tuple[int, int, int, int]]:
    """(cabinet, standing top, tip-up clearance, ceiling) for every carcass that
    would stand under the ceiling but cannot be tipped up to get there.

    Height and depth come from the panel set: the corner unit declares 500 deep
    and has an 834 side, and depth drives the diagonal. Anything already too tall
    to stand is left to above_ceiling — one critical per cabinet is enough. A
    hung unit is tipped up on the floor with no legs.
    """
    rm = job.room
    if rm is None or not rm.ceiling:
        return []
    out = []
    for cab, p, _lay in placed(job):
        g = geometry(cab, std)
        legs = std.leg_height if stands_on_legs(cab, p) else 0
        top = carcass_z(cab, p, std) + g.height
        need = tip_clearance(g.height, g.tip_depth, legs, std.leg_setback)
        if top <= rm.ceiling < need:
            out.append((cab.number, top, need, rm.ceiling))
    return out


@dataclass
class Blocked:
    """A cabinet standing across a door, window or arch."""
    cabinet: int
    wall: str
    opening: str
    x: int
    width: int


def blocked_openings(job, std: Standard = STANDARD) -> List[Blocked]:
    """Cabinets that stand in front of an opening, at a height that matters.

    A base unit under a window is the ordinary kitchen and is clear while its top
    stays below the sill. Touching the sill counts as clear, the same way a
    butted neighbour is not an overlap.
    """
    rm = job.room
    if rm is None:
        return []
    walls = {w.id: w for w in rm.walls}
    out = []
    for cab, p, _lay in placed(job):
        w = walls.get(p.wall)
        if w is None:
            continue
        g = geometry(cab, std)
        z0 = carcass_z(cab, p, std)          # the legs count: a 900 unit tops out at 1000
        z1 = z0 + g.height
        for op in w.openings:
            across = p.x < op.x + op.width and op.x < p.x + g.width
            level = z0 < op.head and op.sill < z1
            if across and level:
                out.append(Blocked(cab.number, w.id, op.kind, op.x, op.width))
    return out


def above_ceiling(job, std: Standard = STANDARD) -> List[Tuple[int, int, int]]:
    """(cabinet, top of carcass, ceiling) for anything that would not stand up.

    Nothing is compared against a ceiling that was never measured — that is its
    own critical in the validator, not a comparison against a made-up figure.
    """
    rm = job.room
    if rm is None or not rm.ceiling:
        return []
    out = []
    for cab, p, _lay in placed(job):
        top = carcass_z(cab, p, std) + geometry(cab, std).height
        if top > rm.ceiling:
            out.append((cab.number, top, rm.ceiling))
    return out


def gap_outline(rm: Room, g: "Gap") -> List[Tuple[int, int]]:
    """The four plan corners of a gap, world coordinates.

    Square on the cabinet side, leaning on the wall side — which is the whole
    reason a filler has to go out oversize and be scribed rather than cut to fit.
    """
    d = g.depth
    if g.after is None:                 # meets the wall's start corner
        local = [(g.x, 0), (g.x + g.nominal, 0),
                 (g.x + g.nominal, d), (g.x + g.nominal - g.front, d)]
    elif g.before is None:              # meets the wall's end corner
        local = [(g.x, 0), (g.x + g.nominal, 0), (g.x + g.front, d), (g.x, d)]
    else:                               # between two square cabinets
        local = [(g.x, 0), (g.x + g.nominal, 0), (g.x + g.nominal, d), (g.x, d)]
    return [to_world(rm, g.wall, lx, ly)[:2] for lx, ly in local]


def _deviation(rm: Room, corner_index: int) -> float:
    """Radians the corner departs from square. Positive opens away from the room."""
    if corner_index is None:
        return 0.0
    offset, _ = corner_offset(rm, corner_index)
    return math.atan2(offset, rm.offset_depth)


def _corner_indices(rm: Room, wall_index: int):
    """(corner before this wall, corner after it). None where the run just stops."""
    n = len(rm.walls)
    if rm.closed:
        return (wall_index - 1) % n, wall_index
    return (wall_index - 1 if wall_index > 0 else None,
            wall_index if wall_index < n - 1 else None)


def _choice_for(job, wall, layer, after, before):
    for g in job.gaps:
        if (g.wall, g.layer, g.after, g.before) == (wall, layer, after, before):
            return g
    return None


def gaps(job, std: Standard = STANDARD) -> List[Gap]:
    """Every gap in every run, with a suggested treatment.

    Runs are per wall and per run key — the floor run, tall units included, and
    the hung run: a gap in the base run is not a gap in the overheads above it.
    Gaps between two cabinets are parallel, because cabinets are square; only
    the two that meet a corner can taper.
    """
    rm = job.room
    if rm is None:
        return []
    wall_ids = [w.id for w in rm.walls]
    runs: Dict[Tuple[str, str], list] = {}
    for cab, p, lay in placed(job):
        if p.wall in wall_ids:
            runs.setdefault((p.wall, run_key(lay)), []).append((p.x, cab, geometry(cab, std)))
    for cab, p, lay in placed(job):
        shadow = corner_shadow(rm, cab, p, std)
        if shadow is None:
            continue
        next_id, at, width, depth = shadow
        runs.setdefault((next_id, run_key(lay)), []).append(
            (at, cab, _shadow_geometry(cab, width, depth, std)))

    out: List[Gap] = []
    for (wall_id, lay), items in sorted(runs.items()):
        items.sort(key=lambda t: t[0])
        w = _wall(rm, wall_id)
        before_corner, after_corner = _corner_indices(rm, wall_ids.index(wall_id))
        geoms = {c.number: g for _, c, g in items}

        edges = []
        first_x, first_cab, _ = items[0]
        if first_x > 0:
            edges.append((None, first_cab, 0, first_x, _deviation(rm, before_corner)))
        for (x0, c0, g0), (x1, c1, _g1) in zip(items, items[1:]):
            end0 = x0 + g0.width
            if x1 > end0:
                edges.append((c0, c1, end0, x1 - end0, 0.0))
        last_x, last_cab, last_g = items[-1]
        end = last_x + last_g.width
        if w.length > end:
            edges.append((last_cab, None, end, w.length - end,
                          _deviation(rm, after_corner)))

        for left, right, x, nominal, dev in edges:
            bounds = [c for c in (left, right) if c is not None]
            depth = max(geoms[c.number].depth for c in bounds)
            height = max(geoms[c.number].height for c in bounds)
            front = nominal + round(depth * math.tan(dev))
            width = max(nominal, front)
            proposal = ("grow" if width < std.filler_min
                        else "filler" if width <= std.filler_max else "cabinet")
            after = left.number if left is not None else None
            before = right.number if right is not None else None
            chosen = _choice_for(job, wall_id, lay, after, before)
            out.append(Gap(wall=wall_id, layer=lay, after=after, before=before,
                           x=x, nominal=nominal, front=front, depth=depth,
                           height=height, board=bounds[0].exterior_board,
                           proposal=proposal,
                           treatment=chosen.treatment if chosen else ""))
    return out
