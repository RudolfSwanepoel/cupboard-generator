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

from .model import Room, Wall
from .standard import STANDARD, Standard

Point = Tuple[float, float]


def rectangular(length: int, width: int, name: str = "room", **kw) -> Room:
    """A square room, walls A-D clockwise. Most rooms start here and get measured.

        rectangular(4000, 3000)  ->  Room
    """
    return Room(name=name, walls=[
        Wall("A", length), Wall("B", width), Wall("C", length), Wall("D", width),
    ], **kw)


# The fixture the worked examples below are checked against by
# tools/check_examples.py. A 4 x 3 m square room, walls A-D clockwise.
EXAMPLE_ROOM = rectangular(4000, 3000)


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
    source: str                        # 'outline' | 'panels' | 'declared'

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
        input, and nothing compares it with 45 (spec item 12). None unless a mitre."""
        if self.source != "corner" or len(self.footprint) != 5:
            return None
        (x0, y0), (x1, y1) = self.front_faces[0]
        return round(math.degrees(math.atan2(y1 - y0, x1 - x0)), 1)


def rect_outline(width: int, depth: int) -> List[Tuple[int, int]]:
    """Front left, front right, back right, back left — the order every rectangle
    in this module has always used."""
    return [(0, depth), (width, depth), (width, 0), (0, 0)]


def corner_outline(style: str, arm_a, arm_b, face_a, face_b) -> Optional[List[Tuple[int, int]]]:
    """The plan outline of a parametric corner unit (ruled 14 Sept 2026, spec
    item 11), derived from its four measurements and a style. None when they do
    not describe a real shape — the caller falls back, and the validator raises
    a critical rather than let a bad shape through quietly.

    Frame: x runs along wall A from the cabinet's start corner, y out from wall
    A. Wall A is the face at y = 0; wall B the face at x = arm_a. There is no
    angle input — a mitre's angle is an output of these four numbers, 45° only
    when arm_a - face_b == arm_b - face_a.

        corner_outline("mitre", 850, 850, 500, 500)  ->  [(0, 0), (850, 0), (850, 850), (350, 850), (0, 500)]
        corner_outline("ell", 850, 850, 500, 500)  ->  [(0, 0), (850, 0), (850, 850), (350, 850), (350, 500), (0, 500)]

    A face measured wider than the arm it would have to fit inside describes no
    shape at all — `corner_outline("mitre", 850, 850, 900, 500)` is `None` —
    which check_drag.py checks, since this pattern only verifies list results.
    """
    if style not in ("mitre", "ell") or None in (arm_a, arm_b, face_a, face_b):
        return None
    if not (0 < face_b < arm_a and 0 < face_a < arm_b):
        return None
    if style == "mitre":
        return [(0, 0), (arm_a, 0), (arm_a, arm_b), (arm_a - face_b, arm_b), (0, face_a)]
    return [(0, 0), (arm_a, 0), (arm_a, arm_b), (arm_a - face_b, arm_b),
            (arm_a - face_b, face_a), (0, face_a)]


def cab_corner_outline(cab) -> Optional[List[Tuple[int, int]]]:
    """corner_outline read off a Cabinet's own fields, or None if it isn't one."""
    if not cab.corner_style:
        return None
    return corner_outline(cab.corner_style, cab.arm_a, cab.arm_b, cab.face_a, cab.face_b)


def geometry(cab, std: Standard = STANDARD) -> CabinetGeometry:
    """One code path for every cabinet, template or bespoke.

    The outline comes from the corner parameters if the cabinet is a resolved
    corner unit, otherwise the cabinet's own entered outline, otherwise the
    rectangle its panels make. `source` says which — 'declared' only when the
    panels could not even give a width, which the validator reports.
    """
    from .engine import generate_cabinet      # engine imports this module; import at call time only
    panels = generate_cabinet(cab, std)
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


def cabinet_footprint(rm: Room, placement, cab, std: Standard = STANDARD) -> List[Tuple[int, int]]:
    """A cabinet's outline in world plan coordinates, wherever it stands."""
    return [to_world(rm, placement.wall, placement.x + lx, ly)[:2]
            for lx, ly in geometry(cab, std).footprint]


def corner_shadow(rm: Room, cab, p, std: Standard = STANDARD):
    """(next wall, width, depth) the far arm of a flush corner unit fills on
    the wall it turns onto — or None.

    A corner unit's `arm_a` runs along the wall it is placed on; its `arm_b`
    then runs on, physically, along whatever wall comes next in the chain,
    because that is where wall B is in the cabinet's own frame. Gaps and runs
    are still found one wall at a time, and neither would otherwise know that
    space is filled — a straight run started flush against the corner would
    see nothing there and propose a filler for a gap that is not a gap. This
    is None unless the unit actually sits flush in that corner: cabinet-local
    x = arm_a has to land exactly on the wall's end.
    """
    g = geometry(cab, std)
    if g.source != "corner":
        return None
    try:
        w = _wall(rm, p.wall)
    except ValueError:
        return None
    if p.x + cab.arm_a != w.length:
        return None
    wall_ids = [x.id for x in rm.walls]
    i = wall_ids.index(p.wall)
    if not rm.closed and i == len(wall_ids) - 1:
        return None
    return wall_ids[(i + 1) % len(wall_ids)], cab.arm_b, cab.face_b


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
        p = placement_for(job, cab.number)
        if p is None:
            continue
        out.append((cab, p, layer_of(cab, p)))
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
    decor: str
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
        g = geometry(cab, std)
        items.append((cab, p, g, lay, cabinet_footprint(rm, p, cab, std), _z_span(cab, p, g, std)))
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


def snap_points(job, number: int, wall_id: str, std: Standard = STANDARD):
    """Where a cabinet may come to rest on a wall, and why.

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
    g = geometry(cab, std)
    width = g.width
    mine = _z_span(cab, here, g, std) if here else None
    out = [(0, "wall start"), (max(w.length - width, 0), "wall end")]

    for other, op, other_lay in placed(job):
        if other.number == number or op.wall != wall_id:
            continue
        og = geometry(other, std)
        if mine is None:
            if run_key(other_lay) != run_key(layer_of(cab)):
                continue
        else:
            oz = _z_span(other, op, og, std)
            if mine[0] >= oz[1] or oz[0] >= mine[1]:
                continue                           # nothing to butt against up there
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


def _corner_door_hinges(g: CabinetGeometry, p):
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
    if len(outline) == 5:                    # mitre: one diagonal front face
        d, e = outline[3], outline[4]
        pt, a0, sign = _edge_hinge(outline, d, e, hinge_at_p0=bool(p.flip))
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
    hinge = _edge_hinge(outline, p0, p1, hinge_at_p0=outer_is_p0 != bool(p.flip))
    return [(*hinge, w)]


def swing_envelopes(job, cab, p, std: Standard = STANDARD):
    """The quarter discs a cabinet's doors sweep, in world plan coordinates.

    A pair is hinged at its outer edges and opens from the middle. A single door
    is hinged left unless the placement is flipped, which is what `flip` is for.
    A corner unit hinges off its real front face instead — see
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
        hinge_specs = _corner_door_hinges(g, p)
    else:
        xs = [x for x, _ in g.footprint]
        left, right = min(xs), max(xs)

        def front_at(x):    # the outline's front edge at that end, where a hinge sits
            return max(y for px, y in g.footprint if px == x)

        if len(g.door_widths) >= 2:
            hinge_specs = [((left, front_at(left)), 0.0, +1, g.door_widths[0]),
                           ((right, front_at(right)), math.pi, -1, g.door_widths[-1])]
        elif p.flip:
            hinge_specs = [((right, front_at(right)), math.pi, -1, g.door_widths[0])]
        else:
            hinge_specs = [((left, front_at(left)), 0.0, +1, g.door_widths[0])]

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
        next_id, width, depth = shadow
        grouped.setdefault((next_id, run_key(lay)), []).append(
            (0, cab, p, _shadow_geometry(cab, width, depth, std)))

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
    """
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
        next_id, width, depth = shadow
        runs.setdefault((next_id, run_key(lay)), []).append(
            (0, cab, _shadow_geometry(cab, width, depth, std)))

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
                           height=height, decor=bounds[0].decor,
                           proposal=proposal,
                           treatment=chosen.treatment if chosen else ""))
    return out
