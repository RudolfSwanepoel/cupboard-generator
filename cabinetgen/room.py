"""Room geometry. The one place trigonometry is allowed.

Local axes, standing in the room facing a wall:

    x   along the wall, from its start corner
    y   out from the wall face, into the room
    z   up from the floor

World axes: X to the right, Y into the room from wall A, Z up. Plan views map
world (X, Y) straight onto SVG (x, y) with no flip, which is why Y runs the way
it does.

That frame is LEFT-handed (X right, Y into the room, Z up). The 3D view
negates Y when it draws, in `app/view3d.js` (`toRender` / `toRoom`), so the
room is not mirrored on screen; nothing here changes for it.

Everything downstream — plan view, elevations, 3D, DXF, the SolidWorks table —
calls `to_world`. Nothing else does its own trig. That is the whole point of
this module: one place to be wrong, and one place to fix.

WALLS ARE POSITIONED SEGMENTS (room redo Phase 1, ruled 2 October 2026). A
`Wall` stores its two end points in room mm; the drawn line is the inside
face and the room is on the RIGHT of x0 -> x1 (`wall_normal`, the right-hand
normal, which in this frame is the `(-dy, dx)` the chain always gave).
Everything a room used to store is DERIVED here, one function each: a wall's
length and direction, which wall end meets which (`connections`, end points
within `Standard.join_tolerance`), the walk round the room (`walk_order`),
whether it closes (`is_closed`), each corner's interior angle
(`corner_angle`), the corner chain (`corner_points`) and a loop that opened
(`closure`, the one answer every display reads). A wall that meets nothing at either end is FREE: its run
ends there with no corner, no butt, no shadow and nothing returned beside it.
Typed lengths and angles are edits that move end points (`set_length`,
`set_corner`); the old chain arithmetic survives only as `_legacy_frames`,
which migrates a room saved before this and is read by nothing else.
"""
import math
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from .model import (MATERIALS, Cabinet, PanelSpec, Placement, Room, Wall, hinge_side,
                    material_thickness, resolve_board)
from .standard import STANDARD, Standard

Point = Tuple[float, float]


def rectangular(length: int, width: int, name: str = "room", **kw) -> Room:
    """A square room, walls A-D clockwise, A along +X from (0, 0). Most rooms
    start here and get measured.

        rectangular(4000, 3000)  ->  Room
    """
    return Room(name=name, walls=[
        Wall("A", 0, 0, length, 0), Wall("B", length, 0, length, width),
        Wall("C", length, width, 0, width), Wall("D", 0, width, 0, 0),
    ], **kw)


def chain_walls(lengths, closed: bool = True, corners=None) -> List[Wall]:
    """Walls from a list of lengths — or `(id, length)` pairs — chained from
    (0, 0) along +X, each corner turning 90 inside (or `corners[i]` degrees,
    the interior angle after wall i, where given): the shape the typed Walls
    card used to build, for fixtures and checks. `closed` only decides whether
    the shape is meant to meet itself; the points say whether it does.

        [(w.id, w.x1, w.y1) for w in chain_walls([4000, 3000, 4000, 3000])]  ->  [('A', 4000, 0), ('B', 4000, 3000), ('C', 0, 3000), ('D', 0, 0)]
    """
    out = []
    px, py, theta = 0.0, 0.0, 0.0
    letters = _letters()
    for i, item in enumerate(lengths):
        wid, length = item if isinstance(item, (tuple, list)) else (next(letters), item)
        ex, ey = px + length * math.cos(theta), py + length * math.sin(theta)
        out.append(Wall(wid, int(round(px)), int(round(py)), int(round(ex)), int(round(ey))))
        px, py = ex, ey
        a = corners[i] if corners and i < len(corners) and corners[i] is not None else 90
        theta += math.pi / 2 if a == 90 else math.radians(180 - a)
    return out


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


# --- letters -------------------------------------------------------------------

def letter_key(wall_id: str):
    """Sort key putting A..Z before AA, AB… — the order letters are handed out."""
    return (len(wall_id), wall_id)


def _letters():
    k = 0
    while True:
        n, s = k, ""
        while True:
            s = chr(ord("A") + n % 26) + s
            n = n // 26 - 1
            if n < 0:
                break
        yield s
        k += 1


def next_wall_id(rm: Room) -> str:
    """The first letter not already naming a wall: A..Z, then AA, AB…

        next_wall_id(EXAMPLE_ROOM)  ->  'E'
    """
    used = {w.id for w in rm.walls}
    for letter in _letters():
        if letter not in used:
            return letter


def _wall(rm: Room, wall_id: str) -> Wall:
    for w in rm.walls:
        if w.id == wall_id:
            return w
    raise ValueError(f"room {rm.name!r} has no wall {wall_id!r}")


# --- one wall ------------------------------------------------------------------

def wall_length(w: Wall) -> int:
    """Whole mm between the two end points.

        wall_length(Wall('A', 0, 0, 4000, 0))  ->  4000
    """
    return w.length


def wall_dir(w: Wall) -> Point:
    """Unit vector from x0, y0 towards x1, y1. A wall of no length points along
    +X, so nothing downstream divides by zero.

        wall_dir(Wall('A', 0, 0, 4000, 0))  ->  (1.0, 0.0)
    """
    dx, dy = w.x1 - w.x0, w.y1 - w.y0
    n = math.hypot(dx, dy)
    if n < 1e-9:
        return (1.0, 0.0)
    return (dx / n, dy / n)


def wall_normal(w: Wall) -> Point:
    """Unit vector INTO the room: the right-hand normal of x0 -> x1 in this
    frame, `(-dy, dx)` — exactly the normal the chain always gave.

        wall_normal(Wall('A', 0, 0, 4000, 0))  ->  (-0.0, 1.0)
    """
    dx, dy = wall_dir(w)
    return (-dy, dx)


def wall_frames(rm: Room) -> Dict[str, Tuple[Point, Point, Point]]:
    """wall id -> (start point, unit direction, unit inward normal), read off
    the points. The same return shape the chain gave, so everything that takes
    (start, dir, normal) is untouched."""
    return {w.id: ((float(w.x0), float(w.y0)), wall_dir(w), wall_normal(w))
            for w in rm.walls}


def wall_height(rm: Room, w: Wall) -> Optional[int]:
    """How tall the wall is: its own height, else the room ceiling (None when
    neither is measured).

        wall_height(Room('r', ceiling=2600, walls=[Wall('A', 0, 0, 1000, 0)]), Wall('A', 0, 0, 1000, 0))  ->  2600
    """
    return w.height if w.height else rm.ceiling


# --- the chain, derived ----------------------------------------------------------

def connections(rm: Room, std: Standard = STANDARD) -> Dict[str, Dict[str, Optional[str]]]:
    """Which wall end meets which: `{"next": {id: id or None}, "prev": {...}}`.

    Wall B is A's next when B's START lies within `join_tolerance` of A's END
    — the corner after A. Each end meets at most one wall; where two candidates
    stand on one point the lower letter wins, so the answer is deterministic.
    A wall with neither is free.
    """
    tol = std.join_tolerance
    ordered = sorted(rm.walls, key=lambda w: letter_key(w.id))
    nxt = {w.id: None for w in rm.walls}
    prv = {w.id: None for w in rm.walls}
    for w in ordered:
        for v in ordered:
            if v is w or prv[v.id] is not None:
                continue
            if math.dist((w.x1, w.y1), (v.x0, v.y0)) <= tol:
                nxt[w.id] = v.id
                prv[v.id] = w.id
                break
    return {"next": nxt, "prev": prv}


def next_wall(rm: Room, wall_id: str, std: Standard = STANDARD) -> Optional[str]:
    """The wall that starts where this one ends, or None.

        next_wall(EXAMPLE_ROOM, 'A')  ->  'B'
    """
    return connections(rm, std)["next"].get(wall_id)


def prev_wall(rm: Room, wall_id: str, std: Standard = STANDARD) -> Optional[str]:
    """The wall that ends where this one starts, or None.

        prev_wall(EXAMPLE_ROOM, 'A')  ->  'D'
    """
    return connections(rm, std)["prev"].get(wall_id)


def chains(rm: Room, std: Standard = STANDARD) -> List[Tuple[List[str], bool]]:
    """The walls grouped into runs, each `(ids in order, closed)`.

    Each chain is walked from its head (the wall nothing leads into; for a loop,
    its lowest letter) along next-connections. Chains come in the order of
    their lowest letter, and walls meeting nothing at either end — free walls —
    come last. A loop is closed only with three or more walls.
    """
    con = connections(rm, std)
    ids = sorted((w.id for w in rm.walls), key=letter_key)
    seen = set()
    out = []
    for start in ids:
        if start in seen:
            continue
        head, guard = start, {start}
        while con["prev"][head] is not None and con["prev"][head] not in guard:
            head = con["prev"][head]
            guard.add(head)
        if con["prev"][head] is not None:          # walked round a loop: start on the lowest letter
            head = start
        chain, k = [], head
        while k is not None and k not in seen:
            chain.append(k)
            seen.add(k)
            k = con["next"][k]
        closed = k == head and len(chain) >= 3
        out.append((chain, closed))
    free = [c for c in out if len(c[0]) == 1 and con["next"][c[0][0]] is None
            and con["prev"][c[0][0]] is None]
    return [c for c in out if c not in free] + free


def walk_order(rm: Room, std: Standard = STANDARD) -> List[str]:
    """Every wall id in walk order: chain by chain, free walls last.

        walk_order(EXAMPLE_ROOM)  ->  ['A', 'B', 'C', 'D']
    """
    return [i for chain, _closed in chains(rm, std) for i in chain]


def main_chain(rm: Room, std: Standard = STANDARD) -> Tuple[List[str], bool]:
    """The chain that is the room: the first closed one, else the first.
    `([], False)` with no walls."""
    cs = chains(rm, std)
    for c in cs:
        if c[1]:
            return c
    return cs[0] if cs else ([], False)


def is_closed(rm: Room, std: Standard = STANDARD) -> bool:
    """Whether the room's walls form a loop.

        is_closed(EXAMPLE_ROOM)  ->  True
    """
    return main_chain(rm, std)[1]


def _chain_of(rm: Room, wall_id: str, std: Standard = STANDARD) -> List[str]:
    for chain, _closed in chains(rm, std):
        if wall_id in chain:
            return chain
    return [wall_id]


def _signed_turn(a: Wall, b: Wall) -> float:
    """Radians the direction turns from wall a to wall b, positive the way wall
    A turns into wall B in a clockwise room."""
    (ax, ay), (bx, by) = wall_dir(a), wall_dir(b)
    return math.atan2(ax * by - ay * bx, ax * bx + ay * by)


def _tidy_angle(a: float):
    a = round(a, 1)
    return int(a) if a == int(a) else a


def corner_angle_exact(rm: Room, wall, std: Standard = STANDARD) -> Optional[float]:
    """`corner_angle` unrounded, for the geometry that reads it (a gap's
    taper): the rounding is for people."""
    wall_id = wall.id if isinstance(wall, Wall) else wall
    nxt = next_wall(rm, wall_id, std)
    if nxt is None:
        return None
    a = 180 - math.degrees(_signed_turn(_wall(rm, wall_id), _wall(rm, nxt)))
    if a <= 0:
        a += 360
    if a >= 360:
        a -= 360
    return a


def corner_angle(rm: Room, wall, std: Standard = STANDARD):
    """The interior angle, in degrees to 0.1, of the corner AFTER this wall —
    inside the room between its face and the next wall's — or None where no
    wall meets its end. 90 an inside corner, 270 an outside one, 180 in line.

        corner_angle(EXAMPLE_ROOM, 'A')  ->  90
    """
    a = corner_angle_exact(rm, wall, std)
    return None if a is None else _tidy_angle(a)


def corner_before(rm: Room, wall, std: Standard = STANDARD):
    """The interior angle of the corner BEFORE this wall (after the wall that
    meets its start), or None where nothing does.

        corner_before(EXAMPLE_ROOM, 'A')  ->  90
    """
    wall_id = wall.id if isinstance(wall, Wall) else wall
    prv = prev_wall(rm, wall_id, std)
    return None if prv is None else corner_angle(rm, prv, std)


def _nominal(angle: float, std: Standard) -> Optional[int]:
    for nominal in (90, 180, 270):
        if abs(angle - nominal) <= std.square_within:
            return nominal
    return None


def out_of_square(angle, offset_depth: int, std: Standard = STANDARD) -> Optional[int]:
    """A corner near 90, 180 or 270 as a site would measure it: the deviation in
    mm at `offset_depth` out from the corner, positive when the return wall
    opens away from the room (the angle is over its nominal). None for a
    corner that is not near square.

        out_of_square(90, 600)  ->  0
        out_of_square(92.9, 600)  ->  30
    """
    if angle is None:
        return None
    nominal = _nominal(angle, std)
    if nominal is None:
        return None
    return int(round(offset_depth * math.tan(math.radians(angle - nominal))))


def angle_from_out_of_square(mm: int, offset_depth: int, nominal: int) -> float:
    """The interior angle a measured deviation means, the inverse of
    `out_of_square`, unrounded.

        angle_from_out_of_square(0, 600, 90)  ->  90.0
    """
    return nominal + math.degrees(math.atan2(mm, offset_depth))


def corner_points(rm: Room, std: Standard = STANDARD) -> List[Point]:
    """The corner where each wall of the room's chain starts, in walk order,
    plus where the last wall ends. On a room that closes, the final point
    equals the first."""
    ids, _closed = main_chain(rm, std)
    pts = [(float(_wall(rm, i).x0), float(_wall(rm, i).y0)) for i in ids]
    if ids:
        last = _wall(rm, ids[-1])
        pts.append((float(last.x1), float(last.y1)))
    return pts


def closure(rm: Room, std: Standard = STANDARD) -> dict:
    """Whether the room closes, and if not by how much — THE one answer (room
    redo Phase 2, ruling 2, 3 October 2026). The Room card, the toast, the
    plan's tint, the 3D view, the Validation tab and every check read this and
    nothing else; the browser decides none of it.

    `{"closed", "miss", "at", "level", "text"}`. A closed room: miss 0, level
    "ok", text "closed room". A main chain of three or more walls whose last end
    misses its first start by no more than `loop_miss_max` is a LOOP THAT OPENS
    (ruling 1: a typed figure leaves the miss where it is rather than absorbing
    it into a wall): `at` names the gap ("D→A"), the level is "crit" over
    `closure_block`, "warn" over `closure_warn`, else "info", and the text is
    "Loop opens by n mm at D→A — type the other walls or drag a corner". It
    closes again by itself once the ends come within `join_tolerance`. Anything
    else is an open run: miss 0, text "open run".

        closure(EXAMPLE_ROOM)["text"]  ->  'closed room'
    """
    ids, closed = main_chain(rm, std)
    if closed:
        return {"closed": True, "miss": 0, "at": "", "level": "ok", "text": "closed room"}
    if len(ids) >= 3:
        first, last = _wall(rm, ids[0]), _wall(rm, ids[-1])
        miss = math.dist((last.x1, last.y1), (first.x0, first.y0))
        if miss <= std.loop_miss_max:
            mm = max(1, int(round(miss)))
            at = f"{last.id}\u2192{first.id}"
            level = ("crit" if mm > std.closure_block else
                     "warn" if mm > std.closure_warn else "info")
            return {"closed": False, "miss": mm, "at": at, "level": level,
                    "text": f"Loop opens by {mm} mm at {at} \u2014 type the other walls "
                            f"or drag a corner"}
    return {"closed": False, "miss": 0, "at": "", "level": "ok", "text": "open run"}


def closure_error(rm: Room, std: Standard = STANDARD) -> int:
    """How far a loop that opened misses closing, in mm (`closure`'s `miss`):
    0 for a closed room and for an open run.

        closure_error(EXAMPLE_ROOM)  ->  0
    """
    return closure(rm, std)["miss"]


def crossing_walls(rm: Room) -> List[Tuple[str, str]]:
    """Pairs of walls whose segments CROSS in plan — the outline cutting itself,
    which no real room does. Meeting at an end point, or an end point lying on
    the other wall (a T-wall), is legal geometry and is not a crossing.

        crossing_walls(EXAMPLE_ROOM)  ->  []
    """
    ws = sorted(rm.walls, key=lambda w: letter_key(w.id))
    return [(a.id, b.id) for i, a in enumerate(ws) for b in ws[i + 1:]
            if _segments_cross(((a.x0, a.y0), (a.x1, a.y1)), ((b.x0, b.y0), (b.x1, b.y1)))]


def _segments_cross(s, t, eps: float = 1e-6) -> bool:
    """Whether two plan segments cross each other PROPERLY: each cuts the
    other's interior. Touching at an end, or an end lying on the other, is
    not a crossing."""
    (a, b), (c, d) = s, t

    def orient(p, q, r):
        v = (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0])
        return 0 if abs(v) < eps else (1 if v > 0 else -1)

    o1, o2, o3, o4 = orient(a, b, c), orient(a, b, d), orient(c, d, a), orient(c, d, b)
    return o1 * o2 < 0 and o3 * o4 < 0


def _legacy_frames(walls: List[dict], offset_depth: int, closed: bool) -> List[Tuple[str, Point, Point]]:
    """The chain arithmetic as it stood before walls had positions (HEAD at 2
    October 2026): wall A along +X from (0, 0), each corner turning by 180 less
    its nominal `corner_end` less the deviation the offsets measured. Read by
    `store.room_from_dict` to migrate a room saved in that form, and by
    nothing else. Gives `(id, start, end)` per wall, in floating point."""
    out = []
    n = len(walls)
    px, py, theta = 0.0, 0.0, 0.0
    for i, w in enumerate(walls):
        length = int(w.get("length") or 0)
        dx, dy = math.cos(theta), math.sin(theta)
        ex, ey = px + length * dx, py + length * dy
        out.append((w["id"], (px, py), (ex, ey)))
        px, py = ex, ey
        here = int(w.get("offset_end") or 0)
        nxt = int(walls[(i + 1) % n].get("offset_start") or 0) if n else 0
        offset = here or nxt
        deviation = math.atan2(offset, offset_depth or 600)
        try:
            a = float(w.get("corner_end", 90))
        except (TypeError, ValueError):
            a = 90
        if math.isnan(a) or not 0 < a < 360:
            a = 90
        nominal = math.pi / 2 if a == 90 else math.radians(180 - a)
        theta += nominal - deviation
    return out


def to_world(rm: Room, wall_id: str, x: int, y: int = 0, z: int = 0) -> Tuple[int, int, int]:
    """Wall-local (x along, y into the room, z up) to world (X, Y, Z), in mm.

    Rounded to the millimetre: the direction is carried in floating point and
    only the answer is rounded.

        to_world(EXAMPLE_ROOM, 'A', 1000, 0, 0)  ->  (1000, 0, 0)
        to_world(EXAMPLE_ROOM, 'A', 0, 600, 0)  ->  (0, 600, 0)
        to_world(EXAMPLE_ROOM, 'B', 0, 0, 0)  ->  (4000, 0, 0)
        to_world(EXAMPLE_ROOM, 'C', 0, 0, 0)  ->  (4000, 3000, 0)
    """
    (sx, sy), (dx, dy), (nx, ny) = wall_frames(rm)[_wall(rm, wall_id).id]
    return (round(sx + dx * x + nx * y),
            round(sy + dy * x + ny * y),
            round(z))


# --- editing the walls: typed numbers move end points -----------------------------

def _translate(rm: Room, ids: List[str], dx: int, dy: int) -> None:
    for i in ids:
        w = _wall(rm, i)
        w.x0 += dx
        w.y0 += dy
        w.x1 += dx
        w.y1 += dy


def set_length(rm: Room, wall_id: str, length: int, std: Standard = STANDARD) -> None:
    """A typed length: the end point moves along the wall's direction, and
    every wall after it in its chain is carried along by the same vector — the
    chain follows, as it always did. Whole mm. A closed room whose last wall
    then misses the first by more than `closure_block` is an open run."""
    w = _wall(rm, wall_id)
    if length < 0:
        raise ValueError("a wall's length cannot be negative")
    dx, dy = wall_dir(w)
    nx, ny = int(round(w.x0 + dx * length)), int(round(w.y0 + dy * length))
    tx, ty = nx - w.x1, ny - w.y1
    chain = _chain_of(rm, wall_id, std)
    w.x1, w.y1 = nx, ny
    if tx or ty:
        _translate(rm, chain[chain.index(wall_id) + 1:], tx, ty)


def set_corner(rm: Room, wall_id: str, angle: float, std: Standard = STANDARD) -> None:
    """A typed interior angle for the corner after this wall: the walls after
    the corner in its chain are rotated about it by the difference — on a
    closed room every wall but this one, round the loop, so the loop opens
    where the walk returns to its head. Refused where no wall meets its end,
    or for an angle not strictly between 0 and 360."""
    if not 0 < float(angle) < 360:
        raise ValueError("a corner angle is between 0 and 360 degrees")
    w = _wall(rm, wall_id)
    now = corner_angle_exact(rm, wall_id, std)
    if now is None:
        raise ValueError(f"nothing meets the end of wall {wall_id}: it has no corner there")
    rot = math.radians(now - float(angle))
    if abs(rot) < 1e-12:
        return
    chain, closed = next(c for c in chains(rm, std) if wall_id in c[0])
    k = chain.index(wall_id)
    after = chain[k + 1:] + (chain[:k] if closed else [])
    cx, cy = w.x1, w.y1
    c, s = math.cos(rot), math.sin(rot)

    def turn(x, y):
        return (int(round(cx + (x - cx) * c - (y - cy) * s)),
                int(round(cy + (x - cx) * s + (y - cy) * c)))

    for i in after:
        v = _wall(rm, i)
        v.x0, v.y0 = turn(v.x0, v.y0)
        v.x1, v.y1 = turn(v.x1, v.y1)


def set_out_of_square(rm: Room, wall_id: str, mm: int, std: Standard = STANDARD) -> None:
    """A corner typed the way a site measures it: `mm` out of square at
    `Room.offset_depth`, against the nominal (90, 180 or 270) the corner is
    nearest. The angle follows (`angle_from_out_of_square`) and the walls
    after the corner turn to it."""
    now = corner_angle_exact(rm, wall_id, std)
    if now is None:
        raise ValueError(f"nothing meets the end of wall {wall_id}: it has no corner there")
    nominal = _nominal(now, std) or 90
    set_corner(rm, wall_id, angle_from_out_of_square(int(mm), rm.offset_depth, nominal), std)


def add_wall(rm: Room, after: str = None, before: str = None, length: int = 3000,
             std: Standard = STANDARD) -> Wall:
    """Add a wall at 90 (interior) off another wall's end (`after`) or start
    (`before`), the next free letter, `length` long. Neither re-origins
    anything: the new wall takes its place off the one it meets. Refused where
    that end already meets a wall.

        add_wall(rectangular(4000, 3000), after='D').id  ->  'E'
    """
    if (after is None) == (before is None):
        raise ValueError("a wall goes after one wall or before one")
    if length < 0:
        raise ValueError("a wall's length cannot be negative")
    w = _wall(rm, after if after is not None else before)
    dx, dy = wall_dir(w)
    if after is not None:
        met = next_wall(rm, w.id, std)
        if met is not None:
            raise ValueError(f"the end of wall {w.id} already meets wall {met}")
        nx, ny = -dy, dx                           # turned 90 inside
        x0, y0 = w.x1, w.y1
        x1, y1 = int(round(x0 + nx * length)), int(round(y0 + ny * length))
    else:
        met = prev_wall(rm, w.id, std)
        if met is not None:
            raise ValueError(f"the start of wall {w.id} already meets wall {met}")
        nx, ny = dy, -dx
        x1, y1 = w.x0, w.y0
        x0, y0 = int(round(x1 - nx * length)), int(round(y1 - ny * length))
    wall = Wall(next_wall_id(rm), x0, y0, x1, y1)
    rm.walls.append(wall)
    return wall


def walls_from_points(rm: Room, points, closed: bool, std: Standard = STANDARD) -> List[Wall]:
    """Walls off an outline drawn with the mouse on Room -> Plan — the corners
    clicked, in world plan mm — ADDED to the room, each the next free letter,
    each marked `drawn`. The points are absolute: nothing is re-oriented and
    nothing is replaced. A first point within `snap_tolerance` of an existing
    wall's end joins it there.

    WHICH SIDE IS THE ROOM: the room is on the right of each wall. A closed
    outline is walked clockwise whichever way it was drawn (the first corner
    clicked still first); an open run is walked the way it turns on balance —
    the inside of an L or a U, whichever way round it was clicked — and a run
    that does not turn (one wall, a step whose turns cancel) is taken as
    drawn. Neither is always what was meant, so the Wall card offers Flip face.
    Pinned in tools/check_room.py.
    """
    pts = []
    for x, y in points:
        q = (float(x), float(y))
        if not pts or math.dist(q, pts[-1]) >= 1:      # a point on the last adds no wall
            pts.append(q)
    if closed and len(pts) > 1 and math.dist(pts[0], pts[-1]) < 1:
        pts.pop()
    if not pts:
        return []
    # start on an existing corner when the first click lands near one
    ends = [(w.x0, w.y0) for w in rm.walls] + [(w.x1, w.y1) for w in rm.walls]
    near = [e for e in ends if math.dist(e, pts[0]) <= std.snap_tolerance]
    if near:
        pts[0] = min(near, key=lambda e: math.dist(e, pts[0]))

    if closed and len(pts) > 2:
        area = sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(pts, pts[1:] + pts[:1])) / 2
        if area < 0:                       # anticlockwise: walk it the other way, first corner first
            pts = [pts[0]] + pts[1:][::-1]
        segs = list(zip(pts, pts[1:] + pts[:1]))
    else:
        segs = list(zip(pts, pts[1:]))

        def turn(s, t):
            d = (math.atan2(t[1][1] - t[0][1], t[1][0] - t[0][0]) -
                 math.atan2(s[1][1] - s[0][1], s[1][0] - s[0][0]))
            while d <= -math.pi:
                d += 2 * math.pi
            while d > math.pi:
                d -= 2 * math.pi
            return d

        if sum(turn(s, t) for s, t in zip(segs, segs[1:])) < -1e-9:
            rev = pts[::-1]
            segs = list(zip(rev, rev[1:]))

    new = []
    for (ax, ay), (bx, by) in segs:
        w = Wall(next_wall_id(rm), int(round(ax)), int(round(ay)), int(round(bx)), int(round(by)),
                 drawn=True)
        rm.walls.append(w)
        new.append(w)
    return new


def flip_face(job, wall_id: str, std: Standard = STANDARD) -> None:
    """Turn one wall's face round, in place: the room is on the right of
    x0 -> x1, so swapping the two end points puts it on the other side. Along
    the wall x now runs from the other end, so an opening, an obstruction, a
    cabinet and a placed panel are each given the x that keeps them where they
    are along it (`L - x - width`), and they stand against the other face —
    the room's. A corner unit's hand swaps with it, so the end in the corner is
    still the end in the corner; a gap decision swaps its two sides; a plinth
    decision follows its run to the cabinet that now starts it. Nothing is cut
    differently; flipping twice gives the job file back exactly.
    """
    rm = job.room
    w = _wall(rm, wall_id)
    L = w.length
    mats = job.materials
    was = {}
    for r in runs(job, std):
        if r.wall != wall_id:
            continue
        c = plinth_choice_for(job, r)
        if c is not None:
            was[id(c)] = r.cabinets[-1]

    w.x0, w.y0, w.x1, w.y1 = w.x1, w.y1, w.x0, w.y0
    for o in w.openings:
        o.x = L - o.x - o.width
    for ob in w.obstructions:
        ob.x = L - ob.x

    by = {c.number: c for c in job.cabinets}
    for p in job.placements:
        cab = by.get(p.cabinet)
        if cab is None or p.wall != wall_id:
            continue
        reach = geometry(cab, std, mats).width
        p.x = L - p.x - reach
        if cab.corner_on:
            # R is written as its default, blank, so flipping twice is exact
            cab.corner_hand = "" if cab.hand == "L" else "L"
    for g in job.gaps:
        if g.wall == wall_id:
            g.after, g.before = g.before, g.after
    for c in job.plinths:
        if id(c) in was:
            c.first = was[id(c)]


def renumber_walls(job, std: Standard = STANDARD) -> Dict[str, str]:
    """Re-letter the walls A, B, C… along the walk (`walk_order`), and rewrite
    every record naming a wall — placements, gap and plinth decisions, an
    acceptance's `where` — to match. A deliberate act behind a confirm in the
    UI; nothing re-letters on its own. Returns `{old: new}` for every wall,
    changed or not."""
    rm = job.room
    order = walk_order(rm, std)
    mapping = {old: new for old, new in zip(order, _letters())}
    for w in rm.walls:
        w.id = mapping[w.id]
    for p in job.placements:
        if p.wall in mapping:
            p.wall = mapping[p.wall]
    for g in job.gaps:
        if g.wall in mapping:
            g.wall = mapping[g.wall]
    for c in job.plinths:
        if c.wall in mapping:
            c.wall = mapping[c.wall]
    for a in job.acceptances:
        if a.where in mapping:
            a.where = mapping[a.where]
    return mapping


def delete_wall(job, wall_id: str) -> dict:
    """Take a wall out of the room. Whatever was placed on it becomes UNPLACED
    (its placement record removed — never an orphan `placement-wall`
    critical), and its gap and plinth decisions go with it. Says what went:
    `{"unplaced": [numbers], "gaps": n, "plinths": n}`."""
    rm = job.room
    _wall(rm, wall_id)
    rm.walls = [w for w in rm.walls if w.id != wall_id]
    gone = [p.cabinet for p in job.placements if p.wall == wall_id]
    job.placements = [p for p in job.placements if p.wall != wall_id]
    gaps_n = sum(1 for g in job.gaps if g.wall == wall_id)
    job.gaps = [g for g in job.gaps if g.wall != wall_id]
    plinths_n = sum(1 for c in job.plinths if c.wall == wall_id)
    job.plinths = [c for c in job.plinths if c.wall != wall_id]
    return {"unplaced": gone, "gaps": gaps_n, "plinths": plinths_n}


# --- editing on the plan: drags move points (room redo Phase 2, 3 Oct 2026) -----

def _ends_at(rm: Room, point, std: Standard = STANDARD) -> List[Tuple[str, int]]:
    """Every wall end standing on `point` (within `join_tolerance`):
    `(wall id, 0 for its start | 1 for its end)`."""
    out = []
    for w in rm.walls:
        if math.dist((w.x0, w.y0), point) <= std.join_tolerance:
            out.append((w.id, 0))
        if math.dist((w.x1, w.y1), point) <= std.join_tolerance:
            out.append((w.id, 1))
    return out


def keep_on_walls(job, lengths_before: Dict[str, int], std: Standard = STANDARD) -> dict:
    """After walls change length, everything placed on them KEEPS ITS x along
    the wall (ruling 3, 3 October 2026), clamped so it still stands on the
    wall: a cabinet or placed panel to `length - its width`, an opening to
    `length - its width`, an obstruction's centre to the length. Nothing is
    moved off its wall. Says what had to move, and what no longer fits at all:
    `{"clamped": [[number, wall, from, to]], "too_long": [[number, wall]],
    "openings": [[wall, kind, from, to]]}`. Attached panels follow their
    cabinet and are not touched here."""
    rm = job.room
    rep = {"clamped": [], "too_long": [], "openings": []}
    by = {c.number: c for c in job.cabinets}
    walls = {w.id: w for w in rm.walls}
    for p in job.placements:
        w = walls.get(p.wall)
        cab = by.get(p.cabinet)
        if w is None or cab is None or cab.is_attached:
            continue
        if lengths_before.get(w.id) == w.length:
            continue
        width = geometry(cab, std, job.materials).width
        hi = max(w.length - width, 0)
        if width > w.length:
            rep["too_long"].append([p.cabinet, w.id])
        if p.x > hi:
            rep["clamped"].append([p.cabinet, w.id, p.x, hi])
            p.x = hi
    for w in rm.walls:
        if lengths_before.get(w.id) == w.length:
            continue
        for o in w.openings:
            hi = max(w.length - o.width, 0)
            if o.x > hi:
                rep["openings"].append([w.id, o.kind, o.x, hi])
                o.x = hi
        for ob in w.obstructions:
            if ob.x > w.length:
                rep["openings"].append([w.id, ob.kind, ob.x, w.length])
                ob.x = w.length
    return rep


def corner_move(job, point, to, std: Standard = STANDARD) -> dict:
    """Drag a corner (ruling 3): every wall end standing on `point` moves to
    `to`, whole mm, so the walls joined there follow it; a free end moves
    alone. Everything on a wall that changed keeps its x (`keep_on_walls`).
    Dropped on another corner, the ends join it — which is how a loop that
    opened is closed again by hand. Refused where no wall ends at `point`."""
    rm = job.room
    ends = _ends_at(rm, point, std)
    if not ends:
        raise ValueError("no wall ends there")
    before = {w.id: w.length for w in rm.walls}
    tx, ty = int(round(to[0])), int(round(to[1]))
    for wid, k in ends:
        w = _wall(rm, wid)
        if k == 0:
            w.x0, w.y0 = tx, ty
        else:
            w.x1, w.y1 = tx, ty
    rep = keep_on_walls(job, before, std)
    rep["moved"] = [wid for wid, _k in ends]
    return rep


def _line_meet(p, d, q, e) -> Optional[Point]:
    """Where the line p + t d meets the line q + s e; None if parallel."""
    den = d[0] * e[1] - d[1] * e[0]
    if abs(den) < 1e-9:
        return None
    t = ((q[0] - p[0]) * e[1] - (q[1] - p[1]) * e[0]) / den
    return (p[0] + t * d[0], p[1] + t * d[1])


def wall_move(job, wall_id: str, offset: int, std: Standard = STANDARD) -> dict:
    """Drag a wall by its body (ruling 3): it moves parallel to itself by
    `offset` mm along its normal (positive into the room). The walls joined at
    its ends STRETCH: each keeps its other end and its direction, and the
    joint slides along it to the moved wall's new line — so a 90 neighbour
    stays 90. Only a neighbour in line with it (parallel) has to turn, its
    joint carried straight across. Everything on a wall that changed length
    keeps its x (`keep_on_walls`)."""
    rm = job.room
    w = _wall(rm, wall_id)
    con = connections(rm, std)
    before = {v.id: v.length for v in rm.walls}
    nx, ny = wall_normal(w)
    d = wall_dir(w)
    a0 = (w.x0 + nx * offset, w.y0 + ny * offset)
    a1 = (w.x1 + nx * offset, w.y1 + ny * offset)
    new0, new1 = a0, a1
    prv, nxt = con["prev"].get(wall_id), con["next"].get(wall_id)
    if prv is not None and prv != wall_id:
        v = _wall(rm, prv)
        m = _line_meet((v.x0, v.y0), wall_dir(v), a0, d)
        if m is not None:
            new0 = m
    if nxt is not None and nxt != wall_id:
        v = _wall(rm, nxt)
        m = _line_meet((v.x1, v.y1), wall_dir(v), a0, d)
        if m is not None:
            new1 = m
    p0 = (int(round(new0[0])), int(round(new0[1])))
    p1 = (int(round(new1[0])), int(round(new1[1])))
    if prv is not None and prv != wall_id:
        v = _wall(rm, prv)
        v.x1, v.y1 = p0
    if nxt is not None and nxt != wall_id:
        v = _wall(rm, nxt)
        v.x0, v.y0 = p1
    w.x0, w.y0 = p0
    w.x1, w.y1 = p1
    rep = keep_on_walls(job, before, std)
    rep["moved"] = [i for i in (prv, wall_id, nxt) if i is not None]
    return rep


def _part_of(cut: int, x: int, width: int) -> Optional[int]:
    """Which part of a wall split at `cut` an item from x to x + width lies on:
    0 the first, 1 the second, None spanning the cut."""
    if x + width <= cut:
        return 0
    if x >= cut:
        return 1
    return None


def split_wall(job, wall_id: str, at: int, std: Standard = STANDARD) -> dict:
    """Split a wall in two at `at` mm from its start (ruling 6, 3 October
    2026): the first part keeps its letter and runs to the split, the second
    takes the next free letter and runs on to the old end, the same height,
    thickness and drawn state. Each record goes to the part that holds it by
    x — placements, openings and obstructions (x re-measured from the second
    part's start), gap and plinth decisions with the cabinets that bound them;
    an item spanning the split stays on the first part and is reported. The
    wall that met the old end now meets the second part. That is how a T-wall
    is made: a wall drawn from a point on another. Says
    `{"first", "second", "spanning": [numbers], "openings": [kinds]}`."""
    rm = job.room
    w = _wall(rm, wall_id)
    L = w.length
    cut = int(round(at))
    if not 0 < cut < L:
        raise ValueError(f"a split falls inside wall {wall_id}: between 0 and {L} mm")
    d = wall_dir(w)
    sx, sy = int(round(w.x0 + d[0] * cut)), int(round(w.y0 + d[1] * cut))
    second = Wall(next_wall_id(rm), sx, sy, w.x1, w.y1, height=w.height,
                  thickness=w.thickness, drawn=w.drawn)
    w.x1, w.y1 = sx, sy
    rm.walls.append(second)
    rep = {"first": w.id, "second": second.id, "spanning": [], "openings": []}
    by = {c.number: c for c in job.cabinets}
    moved = set()
    for p in job.placements:
        cab = by.get(p.cabinet)
        if p.wall != wall_id or cab is None or cab.is_attached:
            continue
        width = geometry(cab, std, job.materials).width
        part = _part_of(cut, p.x, width)
        if part == 1:
            p.wall, p.x = second.id, p.x - cut
            moved.add(p.cabinet)
        elif part is None:
            rep["spanning"].append(p.cabinet)
    keep_o, keep_b = [], []
    for o in w.openings:
        part = _part_of(cut, o.x, o.width)
        if part == 1:
            o.x -= cut
            second.openings.append(o)
        else:
            if part is None:
                rep["openings"].append(o.kind)
            keep_o.append(o)
    for ob in w.obstructions:
        if ob.x >= cut:
            ob.x -= cut
            second.obstructions.append(ob)
        else:
            keep_b.append(ob)
    w.openings, w.obstructions = keep_o, keep_b
    for g in job.gaps:
        if g.wall != wall_id:
            continue
        lead = g.after if g.after is not None else g.before
        if (lead is not None and lead in moved) or (lead is None and g.after is None and g.before is None):
            g.wall = second.id
    for c in job.plinths:
        if c.wall == wall_id and c.first in moved:
            c.wall = second.id
    return rep


def wall_nook(job, wall_id: str, at: int, width: int, depth: int,
              std: Standard = STANDARD) -> dict:
    """A recess in a wall (ruling 7, 3 October 2026): `width` wide, `depth`
    deep, starting `at` mm from the wall's start. The wall is split at both
    sides of the mouth (`split_wall`); the middle part becomes the BACK of the
    recess, `depth` behind the face, the same direction and length, so what
    stood in the mouth keeps its x on it; two new returns join it to the face,
    at 270 and 90 where a recess turns away from the room. A negative depth is
    a projection — a nib — standing into the room, the corners the other way
    round. New letters, nothing re-lettered; a closed room stays closed.
    Says `{"walls": [face, return, back, return, face], "spanning": [...]}`."""
    rm = job.room
    w = _wall(rm, wall_id)
    at, width, depth = int(round(at)), int(round(width)), int(round(depth))
    if width <= 0:
        raise ValueError("a nook's width is a positive number of mm")
    if depth == 0:
        raise ValueError("a nook's depth cannot be 0: positive is a recess, negative a projection")
    if at <= 0 or at + width >= w.length:
        raise ValueError(f"the nook must lie inside wall {wall_id}: from more than 0 to less "
                         f"than {w.length} mm, with its width")
    nx, ny = wall_normal(w)
    one = split_wall(job, wall_id, at, std)
    back = _wall(rm, one["second"])
    two = split_wall(job, back.id, width, std)
    face2 = _wall(rm, two["second"])
    p1, p2 = (back.x0, back.y0), (back.x1, back.y1)
    q1 = (int(round(p1[0] - nx * depth)), int(round(p1[1] - ny * depth)))
    q2 = (int(round(p2[0] - nx * depth)), int(round(p2[1] - ny * depth)))
    back.x0, back.y0, back.x1, back.y1 = q1[0], q1[1], q2[0], q2[1]
    r1 = Wall(next_wall_id(rm), p1[0], p1[1], q1[0], q1[1], height=w.height,
              thickness=w.thickness, drawn=w.drawn)
    rm.walls.append(r1)
    r2 = Wall(next_wall_id(rm), q2[0], q2[1], p2[0], p2[1], height=w.height,
              thickness=w.thickness, drawn=w.drawn)
    rm.walls.append(r2)
    return {"walls": [w.id, r1.id, back.id, r2.id, face2.id],
            "spanning": one["spanning"] + two["spanning"],
            "openings": one["openings"] + two["openings"]}


def add_back_face(rm: Room, wall_id: str, std: Standard = STANDARD) -> Wall:
    """The other face of a wall (ruling 8): a new wall on the same line, the
    opposite way, a wall's thickness behind it, joined to nothing — a
    partition taking cupboards on both sides. The room side of each is its
    own face. The next free letter, the same height and thickness.

        add_back_face(rectangular(4000, 3000), 'A').y0  ->  -110
    """
    w = _wall(rm, wall_id)
    t = w.thickness if w.thickness else std.wall_thickness
    nx, ny = wall_normal(w)
    new = Wall(next_wall_id(rm), int(round(w.x1 - nx * t)), int(round(w.y1 - ny * t)),
               int(round(w.x0 - nx * t)), int(round(w.y0 - ny * t)),
               height=w.height, thickness=w.thickness)
    rm.walls.append(new)
    return new


def flip_room(job, wall_id: str, std: Standard = STANDARD) -> List[str]:
    """Flip the whole room (ruling 9): every wall in the chain holding
    `wall_id` turned round (`flip_face`), so the room side goes to the outside
    of every wall and the loop is walked the other way, still closed.
    Twice gives the job back exactly. Says which walls turned."""
    chain = _chain_of(job.room, wall_id, std)
    for wid in chain:
        flip_face(job, wid, std)
    return chain


def corner_name(rm: Room, point, std: Standard = STANDARD) -> str:
    """How a corner is said: "D→E" where wall D ends and E starts on it,
    else "the end of C" / "the start of C"."""
    ends = _ends_at(rm, point, std)
    finish = sorted((w for w, k in ends if k == 1), key=letter_key)
    start = sorted((w for w, k in ends if k == 0), key=letter_key)
    if finish and start:
        return f"{finish[0]}\u2192{start[0]}"
    if finish:
        return f"the end of {finish[0]}"
    if start:
        return f"the start of {start[0]}"
    return "a corner"


def _corners(rm: Room, std: Standard = STANDARD) -> List[Tuple[int, int]]:
    out = []
    for w in sorted(rm.walls, key=lambda v: letter_key(v.id)):
        for q in ((w.x0, w.y0), (w.x1, w.y1)):
            if not any(math.dist(q, r) <= std.join_tolerance for r in out):
                out.append(q)
    return out


def _unit(dx, dy):
    n = math.hypot(dx, dy)
    return (dx / n, dy / n) if n > 1e-9 else (1.0, 0.0)


def _angle_rays(rm: Room, anchor, ref_dir, ref_name, std: Standard) -> List[dict]:
    """Directions a wall from `anchor` may snap to (ruling 4): relative to the
    wall it meets there (`ref_dir`, the direction of travel INTO the anchor)
    and absolute, on the plan's axes, every `draw_angle_step`. Each carries a
    rank — 0 the neighbour at 90 or 180, 1 the plan's axes, 2 any 45, 3 the
    step — and the reason said beside the cursor."""
    step = std.draw_angle_step or 15
    out = []
    seen = []

    def add(theta, rank, why):
        d = (math.cos(theta), math.sin(theta))
        for q in seen:
            if abs(q[0] - d[0]) < 1e-9 and abs(q[1] - d[1]) < 1e-9:
                return
        seen.append(d)
        out.append({"p": [anchor[0], anchor[1]], "d": [round(d[0], 9), round(d[1], 9)],
                    "rank": rank, "why": why})

    cands = []
    if ref_dir is not None:
        base = math.atan2(ref_dir[1], ref_dir[0])
        for k in range(0, 360, step):
            turn = k if k <= 180 else k - 360
            interior = 180 - turn            # the corner it makes, read inside
            a = abs(turn)
            rank = 0 if a in (90, 0) else 2 if a % 45 == 0 else 3
            if a == 180:
                continue                      # straight back along the wall it meets
            why = (f"in line with {ref_name}" if a == 0 else
                   f"{abs(interior) if abs(interior) <= 180 else 360 - abs(interior)}\u00b0 to {ref_name}")
            cands.append((rank, k, base + math.radians(turn), why))
    for k in range(0, 360, step):
        rank = 1 if k % 90 == 0 else 2 if k % 45 == 0 else 3
        cands.append((rank + (0.5 if rank == 1 else 0), k, math.radians(k),
                      "square to the plan" if k % 90 == 0 else f"{k}\u00b0 on the plan"))
    for rank, _k, theta, why in sorted(cands, key=lambda c: (c[0], c[1])):
        add(theta, int(rank), why)
    return out


def room_snaps(job, mode: str, point=None, wall_id: str = None, points=None,
               std: Standard = STANDARD) -> dict:
    """Everything a drag or a drawing on the plan may snap to (ruling 4, 3
    October 2026), worked out once on the press; the browser only projects the
    pointer and picks the nearest, in this priority: a corner (join) — a point
    on a wall (Draw only) — ALIGNMENT, a line through another corner along the
    plan's axes or along any wall's own direction — an ANGLE for the wall being
    drawn or stretched — and the length step. Each candidate says why.

    `mode` "corner": `point` is the corner dragged; "wall": `wall_id` is moved
    parallel (candidates are `offsets` along its normal); "draw": `points` are
    the corners clicked so far. Whole mm in, unit vectors out."""
    rm = job.room
    std = std or job.std
    moving = []
    if mode == "corner" and point is not None:
        moving = [tuple(point)]
    corners = [c for c in _corners(rm, std)
               if not any(math.dist(c, m) <= std.join_tolerance for m in moving)]
    drawn = [tuple(q) for q in (points or [])]
    out = {"mode": mode, "tolerance": std.snap_tolerance, "step": std.draw_length_step,
           "corners": [{"p": [c[0], c[1]], "why": f"on corner {corner_name(rm, c, std)}"}
                       for c in corners],
           "segments": [], "lines": [], "rays": [], "offsets": []}
    if mode == "draw":
        out["segments"] = [{"a": [w.x0, w.y0], "b": [w.x1, w.y1], "wall": w.id,
                            "why": f"on wall {w.id}"} for w in sorted(rm.walls, key=lambda v: letter_key(v.id))]
    # alignment: through every other corner (and a drawing's own corners but the
    # last), along the plan's axes and along every wall direction not on them
    dirs = [((0.0, 1.0), "x"), ((1.0, 0.0), "y")]
    for w in rm.walls:
        d = wall_dir(w)
        for e in (d, (-d[1], d[0])):
            if abs(e[0]) > 1e-6 and abs(e[1]) > 1e-6 and not any(
                    abs(abs(e[0] * f[0] + e[1] * f[1]) - 1) < 1e-9 for f, _t in dirs):
                dirs.append((e, "dir"))
    throughs = [(c, corner_name(rm, c, std)) for c in corners]
    throughs += [(q, f"drawn corner {k + 1}") for k, q in enumerate(drawn[:-1])]
    for c, name in throughs:
        for e, kind in dirs:
            out["lines"].append({"p": [c[0], c[1]], "d": [round(e[0], 9), round(e[1], 9)],
                                 "kind": kind, "why": f"in line with {name}"})
    if mode == "corner" and point is not None:
        # each wall ending at the corner stretches about its OTHER end: rays
        # from there, relative to the wall that meets that far end
        con = connections(rm, std)
        for wid, k in _ends_at(rm, tuple(point), std):
            w = _wall(rm, wid)
            if k == 1:          # the dragged point is its end: anchored at its start
                anchor, nb = (w.x0, w.y0), con["prev"].get(wid)
                ref = wall_dir(_wall(rm, nb)) if nb else None
            else:               # its start: anchored at its end, walked backwards
                anchor, nb = (w.x1, w.y1), con["next"].get(wid)
                ref = None
                if nb:
                    d = wall_dir(_wall(rm, nb))
                    ref = (-d[0], -d[1])
            out["rays"] += [dict(r, wall=wid) for r in _angle_rays(rm, anchor, ref, nb or "", std)]
    elif mode == "draw" and drawn:
        last = drawn[-1]
        ref, name = None, ""
        if len(drawn) >= 2:
            ref = _unit(last[0] - drawn[-2][0], last[1] - drawn[-2][1])
            name = "the last wall"
        else:
            for wid, k in _ends_at(rm, last, std):
                w = _wall(rm, wid)
                ref, name = (wall_dir(w) if k == 1 else tuple(-v for v in wall_dir(w))), wid
                break
        out["rays"] = _angle_rays(rm, last, ref, name, std)
    elif mode == "wall" and wall_id is not None:
        w = _wall(rm, wall_id)
        nx, ny = wall_normal(w)
        out["normal"] = [nx, ny]
        out["origin"] = [w.x0, w.y0]
        own = {(w.x0, w.y0), (w.x1, w.y1)}
        for c in corners:
            if any(math.dist(c, o) <= std.join_tolerance for o in own):
                continue
            off = (c[0] - w.x0) * nx + (c[1] - w.y0) * ny
            out["offsets"].append({"d": round(off, 3), "p": [c[0], c[1]],
                                   "why": f"in line with {corner_name(rm, c, std)}"})
    return out


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
    # Only at a 90-degree inside corner (ruling 4, 29 September 2026): a mitre
    # or a blind unit in any other corner is a construction nobody has ruled,
    # and it is named by a critical rather than given a shadow. Which wall
    # meets which comes off the end points (`connections`), so a wall meeting
    # nothing at that end — a free wall, an open run's end — casts none.
    k = unit_corner(rm, cab, p, std)
    if k is None or corner_angle(rm, k, std) != 90:
        return None
    if cab.hand == "L":
        if p.x != 0:
            return None
        prev_id = prev_wall(rm, p.wall, std)
        if prev_id is None:
            return None
        return prev_id, max(0, _wall(rm, prev_id).length - width), width, depth
    if p.x + reach != w.length:
        return None
    next_id = next_wall(rm, p.wall, std)
    if next_id is None:
        return None
    return next_id, 0, width, depth


def unit_corner(rm: Room, cab, p, std: Standard = STANDARD) -> Optional[str]:
    """The corner a corner unit belongs in — the one at its HAND end of the wall
    it is placed on — named as the wall whose corner-AFTER it is (the argument
    `corner_angle` takes): a right-handed unit's is its own wall's, a
    left-handed unit's is the wall before. None where that end of the wall
    meets no wall (an open run's ends, a free wall) or the room has no such
    wall. Whether it is flush there is not asked."""
    if p.wall not in {w.id for w in rm.walls}:
        return None
    if cab.hand == "L":
        return prev_wall(rm, p.wall, std)
    return p.wall if next_wall(rm, p.wall, std) is not None else None


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
    """The placement of one cabinet or panel, or None if it has not been placed.

    An ATTACHED panel (28 September 2026) has no placement record of its own:
    where it stands is its cabinet's placement applied to its local offsets,
    worked out by `attached_placement` — so it moves, snaps and changes wall
    with the cabinet, and a stale record left in `job.placements` is never
    read for it. Every reader of a panel's position comes through here.
    """
    cab = cabinet_by_number(job, number)
    if cab is not None and cab.is_attached:
        return attached_placement(job, cab)
    for p in job.placements:
        if p.cabinet == number:
            return p
    return None


def cabinet_by_number(job, number) -> Optional[object]:
    """The cabinet or panel with this number, or None."""
    for c in job.cabinets:
        if c.number == number:
            return c
    return None


# --- attached panels ----------------------------------------------------------
#
# A panel FIXED TO a cabinet (spec of 28 September 2026). It is a Panel item in
# every other respect — its own number, its own cut-list line — and carries
# `PanelSpec.attached_to` plus three offsets in the supports spec's carcass
# frame: x across the width from the cabinet's left side, y from the FRONT face
# of the sides towards the back, z up from the underside of the sides, each to
# the panel's own near corner. The cabinet frame every drawing uses has y OUT
# from the wall, so the two meet at y_cab = D - y_spec, D being the carcass
# depth off `geometry` (never the declared one). This is the one place the two
# frames meet; nothing else works an attached panel's position out.

def host_of(job, panel) -> Optional[object]:
    """The cabinet an attached panel is fixed to, or None: a standalone panel,
    a number the job does not carry, itself, or something that is not a
    carcass (a panel cannot hang off a panel)."""
    n = getattr(panel, "attached_to", None)
    if n is None:
        return None
    host = cabinet_by_number(job, n)
    if host is None or host.is_panel or host.number == panel.number:
        return None
    return host


def attached_panels(job, host_number: int) -> list:
    """Every panel attached to this cabinet, in job order."""
    return [c for c in job.cabinets if c.is_panel and c.attached_to == host_number]


def _attach_frame(job, host, std: Standard, materials: dict):
    """(host placement, D, host underside z) — or None while the host is not
    placed, when its panels are not placed either."""
    hp = None
    for p in job.placements:
        if p.cabinet == host.number:
            hp = p
            break
    if hp is None:
        return None
    g = geometry(host, std, materials)
    return hp, g.depth, carcass_z(host, hp, std)


def attached_placement(job, panel, std: Standard = None, materials: dict = None):
    """Where an attached panel stands: its cabinet's placement applied to its
    offsets. None while the cabinet itself is not placed, or names nothing.

        x  = cabinet x + at_x
        y  = D - at_y - (the panel's extent out from the wall)   (Placement.y is
             the panel's BACK, out from the wall face)
        z  = the cabinet's underside (on its legs) + at_z

    A derived record, never stored: `store` writes no placement for an
    attached panel, and the drop of a drag never lands here (`api.drag`
    refuses an attached panel — its cabinet is what moves).
    """
    std = job.std if std is None else std
    materials = job.materials if materials is None else materials
    host = host_of(job, panel)
    if host is None:
        return None
    frame = _attach_frame(job, host, std, materials)
    if frame is None:
        return None
    hp, D, z0 = frame
    spec = panel.panel_spec
    pg = panel_geometry(panel, std, materials)
    return Placement(cabinet=panel.number, wall=hp.wall,
                     x=int(hp.x + int(spec.at_x or 0)),
                     z=int(z0 + int(spec.at_z or 0)), flip=False, layer=None,
                     y=int(D - int(spec.at_y or 0) - pg.depth))


def attach_offsets(job, panel, host, std: Standard = None, materials: dict = None):
    """The offsets that put a panel exactly where it stands now, as it is
    attached to `host` — so attaching does not move it. (at_x, at_y, at_z).

    On the host's own wall the inverse of `attached_placement` to the
    millimetre. On another wall the panel's near corner is carried across
    through world coordinates (its box is read into the host's frame), so it
    keeps its place and its size; its long axis now runs with the host's wall.
    An UNPLACED panel, or an unplaced host, gets `default_offsets`.
    """
    std = job.std if std is None else std
    materials = job.materials if materials is None else materials
    p = None
    for q in job.placements:
        if q.cabinet == panel.number:
            p = q
            break
    frame = _attach_frame(job, host, std, materials)
    if p is None or frame is None or job.room is None:
        return default_offsets(job, panel, host, std, materials)
    hp, D, z0 = frame
    pg = panel_geometry(panel, std, materials)
    if p.wall == hp.wall:
        return (int(p.x - hp.x), int(D - int(p.y or 0) - pg.depth), int(p.z - z0))
    try:
        hf = _placed_frame(job.room, hp)
        pts = [_from_plan(hf, q) for q in cabinet_footprint(job.room, p, panel, std, materials)]
    except ValueError:
        return default_offsets(job, panel, host, std, materials)
    x0 = min(x for x, _ in pts)
    y1 = max(y for _, y in pts)
    return (int(round(x0)), int(round(D - y1)), int(p.z - z0))


def default_offsets(job, panel, host, std: Standard = None, materials: dict = None):
    """Where a panel that has no place of its own is put on a cabinet: standing
    against the cabinet's LEFT side, its front flush with the front of the
    sides, its underside level with theirs — an end panel's place, and a
    starting point to type over, never a rule."""
    std = job.std if std is None else std
    materials = job.materials if materials is None else materials
    pg = panel_geometry(panel, std, materials)
    return (-int(pg.width), 0, 0)


def attach_snap_points(job, panel, host, std: Standard = None, materials: dict = None) -> dict:
    """Every offset an attached panel's drag may settle on, per axis, in the
    supports spec's carcass frame — the drag in the Cabinets tab's 3D view
    (spec B4, built with the UI restructure, 28 September 2026).

    Each is a face or an edge of the carcass meeting a face or an edge of the
    panel: `x` the panel's left edge (at_x), `y` its front edge back from the
    front face of the sides (at_y), `z` its underside up from theirs (at_z).
    The browser picks the nearest within `Standard.snap_tolerance` and works
    out no offset of its own; what it drops is written to the same three
    fields Panel design types (hard rule 8). Sorted, one reason per value.

        {"x": [{"v": -16, "why": "against the left side, outside"}, ...],
         "y": [...], "z": [...]}
    """
    std = job.std if std is None else std
    materials = job.materials if materials is None else materials
    g = geometry(host, std, materials)
    pg = panel_geometry(panel, std, materials)
    xs = [x for x, _ in g.footprint] or [0, g.width]
    W, D, H, t = int(round(max(xs) - min(xs))), int(g.depth), int(g.height), std.board_t
    pw, pd, ph = int(pg.width), int(pg.depth), int(pg.height)
    # a door or a drawer face stands proud by its own board's thickness: an end
    # panel brought forward by that much finishes flush with the fronts
    front = host.door_board(0) if (g.door_widths or host.drawer_list) else host.exterior_board
    ft = _front_t(materials, front, std)

    def axis(cands):
        seen, out = set(), []
        for v, why in cands:
            v = int(v)
            if v in seen:
                continue
            seen.add(v)
            out.append({"v": v, "why": why})
        return sorted(out, key=lambda c: c["v"])

    return {
        "x": axis([(-pw, "against the left side, outside"), (0, "left edges level"),
                   (t, "against the left side, inside"),
                   (W - t - pw, "against the right side, inside"),
                   (W - pw, "right edges level"), (W, "against the right side, outside")]),
        "y": axis([(0, "front flush with the carcass"), (-ft, "front flush with the fronts"),
                   (-pd, "in front of the carcass"), (D - pd, "back flush with the carcass"),
                   (D, "behind the carcass")]),
        "z": axis([(0, "bottoms level"), (H - ph, "tops level"), (H, "on top of the carcass"),
                   (-ph, "under the carcass"), (t, "on the bottom panel")]),
    }


def new_attached_panel(job, host, number: int, std: Standard = None):
    """A fresh panel on this cabinet, as "+ Panel on this cabinet" makes it: an
    end panel, side-on, cut from the cabinet's exterior board, the carcass
    depth plus `Standard.exposed_extra` deep — the exposed end's own figure,
    finishing flush with the doors — and the carcass height tall; standing
    against the left side (`default_offsets`), brought forward by that extra
    so its back is flush with the back of the sides. Every figure is off
    `geometry` and `Standard`; the operator types over any of them.
    """
    std = job.std if std is None else std
    g = geometry(host, std, job.materials)
    board = resolve_board(job.materials, host.exterior_board) \
        if host.exterior_board in (job.materials or {}) else host.exterior_board
    spec = PanelSpec(board=board, orientation="end",
                     a=int(g.depth + std.exposed_extra), b=int(g.height),
                     grain_along="b", attached_to=host.number)
    panel = Cabinet(number=number, width=0, height=0, depth=0, kind="panel",
                    template="standard", supports=0, doors=0,
                    carcass_board=host.carcass_board, exterior_board=host.exterior_board,
                    back_board=host.back_board, panel=spec)
    x, _y, z = default_offsets(job, panel, host, std, job.materials)
    spec.at_x, spec.at_y, spec.at_z = x, -int(std.exposed_extra), z
    return panel


def attached_box(job, panel, std: Standard = None, materials: dict = None):
    """An attached panel's world footprint and height span, or None."""
    std = job.std if std is None else std
    materials = job.materials if materials is None else materials
    p = attached_placement(job, panel, std, materials)
    if p is None or job.room is None:
        return None
    g = geometry(panel, std, materials)
    return cabinet_footprint(job.room, p, panel, std, materials), _z_span(panel, p, g, std)


def attached_carcass_overlaps(job, std: Standard = STANDARD) -> list:
    """(panel, host) for every attached panel that cuts INTO its own cabinet's
    carcass — overlapping it, not merely touching. A WARNING: the panel is cut
    and costed wherever it stands, and how far it laps the carcass is the
    fitter's business; it does not block the export (spec B6)."""
    rm = job.room
    if rm is None:
        return []
    out = []
    for cab in job.cabinets:
        if not cab.is_attached:
            continue
        host = host_of(job, cab)
        box = attached_box(job, cab, std, job.materials)
        if host is None or box is None:
            continue
        hp = placement_for(job, host.number)
        hg = geometry(host, std, job.materials)
        hz = _z_span(host, hp, hg, std)
        fp, zs = box
        if zs[0] >= hz[1] or hz[0] >= zs[1]:
            continue
        if polygons_overlap(fp, cabinet_footprint(rm, hp, host, std, job.materials)):
            out.append((cab.number, host.number))
    return out


def attached_extent(job, host, hp, hg, std: Standard = STANDARD):
    """(x0, x1) along the wall that a cabinet and its attached panels take up
    at carcass height — what a run's gap is measured from. Only a panel level
    with the carcass counts: a bulkhead attached above a base unit is not in
    its run. The carcass alone when nothing is attached, so no existing job
    moves."""
    x0, x1 = hp.x, hp.x + hg.width
    hz = _z_span(host, hp, hg, std)
    for pan in attached_panels(job, host.number):
        p = attached_placement(job, pan, std, job.materials)
        if p is None or p.wall != hp.wall:
            continue
        g = geometry(pan, std, job.materials)
        zs = _z_span(pan, p, g, std)
        if zs[0] >= hz[1] or hz[0] >= zs[1]:
            continue
        x0, x1 = min(x0, p.x), max(x1, p.x + g.width)
    return x0, x1


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

    Which walls are "either side" comes off the chain of corners — the wall
    before this one and the wall after it, and round the end only in a closed
    room — never off a letter, so a three- or four-wall room answers the same
    way as two. Placed PANELS on those walls are included (`panel` True): an end
    cap or a bulkhead on the return wall is seen end on exactly as a carcass is.
    """
    rm = job.room
    if rm is None:
        return []
    if wall_id not in [w.id for w in rm.walls]:
        return []
    beside = _beside(rm, wall_id)
    here = _wall(rm, wall_id)
    (sx, sy), (dx, dy), (nx, ny) = wall_frames(rm)[here.id]
    out = []
    items = ([(cab, p, lay, False) for cab, p, lay in placed(job)] +
             [(cab, p, "panel", True) for cab, p in placed_panels(job)])
    for cab, p, lay, is_panel in items:
        if p.wall not in beside:
            continue
        g = geometry(cab, std, job.materials)
        pts = []
        for fx, fy in g.footprint:
            wx, wy, _ = to_world(rm, p.wall, p.x + fx, fy + getattr(p, "y", 0))
            pts.append(((wx - sx) * dx + (wy - sy) * dy,
                        (wx - sx) * nx + (wy - sy) * ny))
        if not pts:
            continue
        x0 = max(min(x for x, _ in pts), 0)
        x1 = min(max(x for x, _ in pts), here.length)
        if x1 <= x0 or min(y for _, y in pts) < -1:
            continue                     # not in front of this wall at all
        out.append({"cabinet": cab.number, "wall": p.wall, "layer": lay,
                    "panel": is_panel,
                    "x0": int(round(x0)), "x1": int(round(x1)),
                    "z0": carcass_z(cab, p, std), "height": g.height,
                    "out": int(round(min(y for _, y in pts)))})
    # nearest this wall first, so the one nearest the viewer is drawn last, on top
    out.sort(key=lambda r: r["out"])
    return out


# --- what a cabinet is made of, as solids in the room ------------------------
#
# Added 23 September 2026 for two drawings: the plan's door and drawer faces,
# and the Finish view of a wall, which shows the runs either side as what you
# would really see standing in front of it. Both are read-only views, so this
# is drawing geometry and nothing more — no cut, check or cost reads it. Every
# size comes off `geometry` (the panel set) and the same corner helpers the cut
# list uses; the only thing laid out here rather than read is where across its
# carcass a leaf sits, which is spread evenly because no cut list says.


@dataclass
class Part:
    """One board of a cabinet as a solid: a plan outline extruded up.

    `outline` is convex, in the cabinet's own frame (x along its wall from its
    left edge, y out from the wall face); `z0`/`z1` are up from the carcass
    underside. `grain` is the cabinet-frame axis the grain runs along — 'x',
    'y' or 'z' — or None on a part that says nothing about it. `label` is a
    real size worth printing on the part where it is seen at an angle (a mitre
    door's cut width), and `index` is the leaf or drawer it is.
    """
    role: str                          # side top bottom door drawer blind panel carcass
    board: str
    outline: List[Point]
    z0: float
    z1: float
    grain: Optional[str] = "z"
    label: str = ""
    index: int = -1

    @property
    def front(self) -> bool:
        """A door, a drawer face or a blind corner's flush panel."""
        return self.role in ("door", "drawer", "blind")


def _box(role, board, x0, x1, y0, y1, z0, z1, grain="z", label="", index=-1):
    return Part(role, board, [(x0, y0), (x1, y0), (x1, y1), (x0, y1)],
                z0, z1, grain, label, index)


def _front_t(materials, board: str, std: Standard) -> int:
    """A front's real thickness: its board's, or the carcass figure if the
    board carries none."""
    return material_thickness(materials, board) or std.board_t


def _door_z(cab, std: Standard, above: float = 0) -> Tuple[float, float]:
    """Where a door leaf runs up the carcass — its bottom at `above`, the top of
    any drawer stack under it, exactly as the elevation stacks them."""
    h = cab.door_height or (cab.height - std.door_height_gap)
    return above, above + h


def _spread(total: float, widths: List[int]) -> List[Tuple[float, float]]:
    """Leaves of the given widths spread evenly across `total`, left to right."""
    gap = max(total - sum(widths), 0) / (len(widths) + 1)
    out, at = [], gap
    for w in widths:
        out.append((at, at + w))
        at += w + gap
    return out


def _panel_grain_axis(spec) -> Optional[str]:
    """Which cabinet-frame axis a panel's grain runs along, off its orientation
    — the same table `panel_geometry` reads its extents from."""
    along = {"upright": ("x", "z"), "flat": ("x", "y"), "end": ("y", "z")}
    a, b = along.get(spec.orientation, ("x", "z"))
    return a if spec.grain_along == "a" else b


def _mitre_solid(cab, g, std: Standard, mats) -> List[Part]:
    """A mitre's boards, off its four measurements — the construction
    `engine.mitre_panels` cuts: two open-face sides, the two wall panels (wall A
    wrapping), the mitred top and bottom, and the door on the inner line."""
    t, a_a, a_b, f_a, f_b = _mitre_parts(cab, std)
    H, carc = g.height, cab.carcass_board
    blank = [(t, t), (a_a - t, t), (a_a - t, a_b - t), (a_a - f_b, a_b - t), (t, f_a)]
    parts = [_box("side", carc, 0, t, 0, f_a, 0, H),                  # open face, wall A
             _box("side", carc, t, a_a, 0, t, 0, H),                  # wall A, wraps
             _box("side", carc, a_a - t, a_a, t, a_b - t, 0, H),      # wall B
             _box("side", carc, a_a - f_b, a_a, a_b - t, a_b, 0, H),  # open face, wall B
             Part("bottom", carc, blank, 0, t, "x"),
             Part("top", carc, blank, H - t, H, "x")]
    doors = g.door_widths if cab.door_count else []
    if doors:
        (x0, y0), (x1, y1) = (t, f_a), (a_a - f_b, a_b - t)   # the inner line, hand R
        span = math.hypot(x1 - x0, y1 - y0)
        ux, uy = (x1 - x0) / span, (y1 - y0) / span
        nx, ny = -uy, ux                                      # out into the room
        z0, z1 = _door_z(cab, std)
        for i, (s0, s1) in enumerate(_spread(span, doors)):
            board = cab.door_board(i)
            d = _front_t(mats, board, std)
            p0 = (x0 + ux * s0, y0 + uy * s0)
            p1 = (x0 + ux * s1, y0 + uy * s1)
            parts.append(Part("door", board,
                              [p0, p1, (p1[0] + nx * d, p1[1] + ny * d),
                               (p0[0] + nx * d, p0[1] + ny * d)],
                              z0, z1, "z", str(doors[i]), i))
    if cab.hand == "L":                  # the mirror of R about the unit's centre line
        for p in parts:
            p.outline = [(a_a - x, y) for x, y in p.outline]
    return parts


def solid_parts(cab, std: Standard = STANDARD, materials: dict = None) -> List[Part]:
    """What a cabinet or a panel is made of, as solids in its own frame.

    Drawing geometry only (see above). A panel is one board. A straight
    cabinet is its two sides, its bottom, its top if the panel set has one, and
    its fronts standing proud of the carcass at their boards' real thickness: the
    drawer faces stacked from the bottom with `stack_gap` between them, then the
    doors, as the elevation stacks them. A mitre is `engine.mitre_panels`'
    construction; a blind corner a straight box with its flush panel inset
    (`blind_spans`) and its one door. An ell, a bespoke cabinet, or anything
    whose parts are not known is its footprint as one solid in the carcass
    board, and no fronts — nothing is guessed onto a drawing.
    """
    mats = MATERIALS if materials is None else materials
    g = geometry(cab, std, mats)
    if cab.is_panel:
        spec = cab.panel_spec
        return [_box("panel", spec.board, 0, g.width, 0, g.depth, 0, g.height,
                     _panel_grain_axis(spec))]
    if cab.corner_kind == "mitre" and g.source == "corner" and _mitre_parts(cab, std):
        return _mitre_solid(cab, g, std, mats)
    xs = [x for x, _ in g.footprint]
    W, D, H, t = max(xs) - min(xs), g.depth, g.height, std.board_t
    rect = g.source in ("panels", "declared") or (
        g.source == "outline" and len(g.footprint) == 4 and
        sorted(g.footprint) == sorted(rect_outline(W, D)))
    if cab.template == "none" or cab.corner_kind == "ell" or not rect or H <= 0:
        return [Part("carcass", cab.carcass_board, list(g.footprint), 0, H, "z")]
    from .engine import generate_cabinet      # engine imports this module
    roles = {p.role for p in generate_cabinet(cab, std, mats)}
    carc = cab.carcass_board
    parts = [_box("side", carc, 0, t, 0, D, 0, H),
             _box("side", carc, W - t, W, 0, D, 0, H),
             _box("bottom", carc, t, W - t, 0, D, 0, t, "x")]
    if "Top" in roles:
        parts.append(_box("top", carc, t, W - t, 0, D, H - t, H, "x"))

    if cab.corner_kind == "blind":
        spans = blind_spans(cab, std)
        if spans:
            (_s0, _s1), (b0, b1), (d0, d1) = spans
            board = cab.blind_panel_board
            parts.append(_box("blind", board, b0, b1,
                              D - _front_t(mats, board, std), D, t, H - t))
            z0, z1 = _door_z(cab, std)
            board = cab.door_board(0)
            parts.append(_box("door", board, d0, d1, D, D + _front_t(mats, board, std),
                              z0, z1, index=0))
        return parts

    gap = std.door_single_gap
    at = 0.0
    # the face stack only: an inner drawer is behind the door, and its face is
    # drawn in 3D with its box (`interior_parts`), never on the front
    stack = cab.outer_drawers
    for i in range(len(stack) - 1, -1, -1):             # the bottom face is the last
        d = stack[i]
        board = cab.face_board_of(d)
        parts.append(_box("drawer", board, gap / 2, W - gap / 2,
                          D, D + _front_t(mats, board, std),
                          at, at + d.face_height, index=i))
        at += d.face_height + std.stack_gap
    if g.door_widths:
        z0, z1 = _door_z(cab, std, at if stack else 0)
        for i, (x0, x1) in enumerate(_spread(W, g.door_widths)):
            board = cab.door_board(i)
            parts.append(_box("door", board, x0, x1, D, D + _front_t(mats, board, std),
                              z0, z1, index=i))
    return parts


def _placed_frame(rm: Room, p):
    """A placement's frame in world plan terms, unrounded: where cabinet-local
    (0, 0) is, the unit direction along its wall and the one into the room."""
    (sx, sy), (dx, dy), (nx, ny) = wall_frames(rm)[_wall(rm, p.wall).id]
    off = int(getattr(p, "y", 0) or 0)
    return (sx + dx * p.x + nx * off, sy + dy * p.x + ny * off), (dx, dy), (nx, ny)


def _to_plan(frame, q) -> Point:
    (ox, oy), (dx, dy), (nx, ny) = frame
    return ox + dx * q[0] + nx * q[1], oy + dy * q[0] + ny * q[1]


def _from_plan(frame, q) -> Point:
    """The inverse of `_to_plan`: world plan -> the cabinet's own frame."""
    (ox, oy), (dx, dy), (nx, ny) = frame
    u, v = q[0] - ox, q[1] - oy
    return u * dx + v * dy, u * nx + v * ny


def back_part(cab, std: Standard = STANDARD, materials: dict = None) -> Optional[Part]:
    """The backing board as a solid in the cabinet's frame — for the 3D view.

    Kept OUT of `solid_parts` on purpose (23 September 2026): `return_faces`
    reads that list for the Finish elevation, and a board inside the carcass
    would change that drawing. The scene asks here as well.

    Only where the engine actually cuts one: a straight template cabinet — a
    blind corner included, it is a straight box — whose `back` is not 'none'.
    A mitre's back is its two wall panels, already in `solid_parts`; an ell, a
    bespoke cabinet and a panel cut no backing board through the engine's
    template path, so none is drawn for them.

    Positioned by `Standard.back_face_from_front` and sized by
    `Standard.back_size`, exactly as the engine sizes it: the board's front face
    is `back_face_from_front` in from the carcass front, so it lies between
    `back_cavity` and `back_cavity + back_t` off the wall. Grooved into the sides
    it starts `board_t - groove_engage` in from each edge — the same figure the
    `W - 20` is made of — and runs `H - 20` between top and bottom on a four-way
    back, or from the floor of the carcass to the top groove on a three-way one.
    """
    if cab.is_panel or cab.template == "none" or cab.corner_kind in ("mitre", "ell"):
        return None
    if cab.back == "none":
        return None
    mats = MATERIALS if materials is None else materials
    parts = solid_parts(cab, std, mats)
    if not parts or any(q.role == "carcass" for q in parts):
        return None                      # footprint only: nothing is inside it
    g = geometry(cab, std, mats)
    xs = [x for x, _ in g.footprint]
    W, H, t = max(xs) - min(xs), g.height, std.board_t
    bw, bh = std.back_size(W, H, cab.back)
    inset = t - std.groove_engage
    y0 = std.back_cavity
    y1 = y0 + std.back_t
    z0 = inset if cab.back == "four" else 0
    board = cab.back_board
    return _box("back", board, inset, inset + bw, y0, y1, z0, z0 + bh,
                "z" if bh >= bw else "x")


# --- shelves and supports, for the 3D view only (27 September 2026) -----------
#
# Where each support and each shelf stands inside the carcass. DRAWING geometry,
# like `solid_parts` and `back_part`: nothing on the cut list reads a position
# here, and nothing here decides a size — every extent is the engine's (Wi x
# SUPPORT_W x t for a support, the shelf sizes off Standard). Kept OUT of
# `solid_parts` for the same reason `back_part` is: `return_faces` reads that
# list for the Finish elevation, and the plan and the wall elevations are
# unchanged by this work.
#
# Frames. `support_layout` answers in the spec's CARCASS-LOCAL frame — x across
# the width, y from the FRONT face of the sides (0) to their back (D), z up from
# the underside of the sides — which is the frame the worked numbers are stated
# in and `tools/check_supports.py` asserts. `interior_parts` turns that into a
# `Part` in the cabinet's frame (y out from the WALL face), the one every other
# solid is in: y_part = D - y_spec.

SUPPORT_SIDES = ("x0", "x1", "y0", "y1", "z0", "z1")


def support_layout(cab, std: Standard = STANDARD, materials: dict = None) -> List[dict]:
    """Every support of a straight carcass, one entry each, in the spec frame.

    Per entry: `type` ('front' | 'top_rear' | 'back'), `n` (1-based within the
    type — Back 1 is the one under the top), `row` (the Support it comes from),
    `y0`/`y1`, `z0`/`z1`, `upright`, and `faces`: which physical face of the
    rail each of the row's four edge names is on, as one of SUPPORT_SIDES in
    this frame ('y0' is the front face of a flat rail; 'z0' the underside).

    The rules (agreed 27 September 2026):

    * FRONT (base units only): flat, y 0..100, z H-16..H — top flush with the
      sides, front flush with their fronts.
    * TOP REAR (base units only): flat at the same height. With a backing its
      rear edge is against the backing's front face, y (D-119)..(D-19); with
      none it is flush with the back of the sides, y (D-100)..D.
    * BACK: upright in the 16 mm cavity, y (D-16)..D, 100 tall, the same plane
      with or without a backing. Back 1 hangs under whatever is at the top back:
      the top panel (tall, wall) or a Top Rear that sits at the back (base, no
      backing) put its top at H-16, otherwise it is flush with the top of the
      sides at H. Back 2 stands on the top face of the bottom panel. Back 3..n
      are spaced with equal gaps between the two. One Back alone is Back 1.
    * Back 1's edged long edge faces DOWN; every other Back's faces UP.

    Typed rows are placed by their type. LEGACY rows — the three old numbers,
    or rows written before the types — are cut exactly as they always were and
    only PLACED here, by the legacy rule: on a base unit one front-edged rail
    is the Front and the rest are Backs; on a carcass with a top, all Backs.
    Nothing converts or renames a legacy row.

    Empty for a panel, a bespoke cabinet, a mitre, an ell, and any carcass whose
    parts are not known (`solid_parts` gives a footprint only).

        >>> from cabinetgen.model import Cabinet
        >>> c = Cabinet(number=1, width=600, height=720, depth=560, kind="base",
        ...             carcass_board="MEL", exterior_board="BROOKHILL")
        >>> [(u["type"], u["n"], u["y0"], u["y1"], u["z0"], u["z1"])
        ...  for u in support_layout(c) if u["n"] == 1]
        [('back', 1, 544, 560, 620, 720)]
    """
    from .engine import SUPPORT_W, generate_cabinet      # engine imports this module
    from .model import SUPPORT_DEFAULT_EDGES
    if cab.is_panel or cab.template == "none" or cab.corner_kind in ("mitre", "ell"):
        return []
    rows = cab.support_list
    if not rows:
        return []
    mats = MATERIALS if materials is None else materials
    parts = solid_parts(cab, std, mats)
    if not parts or any(q.role == "carcass" for q in parts):
        return []
    g = geometry(cab, std, mats)
    D, H, t, sw = g.depth, g.height, std.board_t, SUPPORT_W
    has_top = "Top" in {q.role for q in generate_cabinet(cab, std, mats)}
    has_back = cab.back != "none"

    units: List[Tuple[str, "Support"]] = []
    if cab.supports_typed:
        for row in rows:
            units += [(row.type, row)] * row.qty
    else:
        front_done = has_top                     # nothing flat on a carcass with a top
        for row in rows:
            for _ in range(row.qty):
                if not front_done and row.edge == "front":
                    units.append(("front", row))
                    front_done = True
                else:
                    units.append(("back", row))

    out = []
    counts: dict = {}
    top_rear_at_back = any(k == "top_rear" for k, _ in units) and not has_back
    back1_top = H - t if (has_top or top_rear_at_back) else H
    n_back = sum(1 for k, _ in units if k == "back")
    # Back 3..n: equal gaps between Back 2's top (t + sw) and Back 1's underside.
    lo, hi = t + sw, back1_top - sw
    mid = max(n_back - 2, 0)
    gap = (hi - lo - mid * sw) / (mid + 1) if mid else 0.0
    for kind, row in units:
        n = counts.get(kind, 0) + 1
        counts[kind] = n
        if kind == "front":
            entry = dict(type=kind, n=n, row=row, y0=0, y1=sw, z0=H - t, z1=H, upright=False,
                         faces={"front": "y0", "rear": "y1", "left": "x0", "right": "x1"})
        elif kind == "top_rear":
            y1 = std.back_face_from_front(D) if has_back else D
            entry = dict(type=kind, n=n, row=row, y0=y1 - sw, y1=y1, z0=H - t, z1=H,
                         upright=False,
                         faces={"front": "y0", "rear": "y1", "left": "x0", "right": "x1"})
        else:
            if n == 1:
                z1 = back1_top
                faces = {"front": "z0", "rear": "z1", "left": "x0", "right": "x1"}
            elif n == 2:
                z1 = t + sw
                faces = {"front": "z1", "rear": "z0", "left": "x0", "right": "x1"}
            else:
                z1 = lo + gap * (n - 2) + sw * (n - 2)
                faces = {"front": "z1", "rear": "z0", "left": "x0", "right": "x1"}
            z1 = int(round(z1)) if float(z1).is_integer() else z1
            entry = dict(type=kind, n=n, row=row, y0=D - t, y1=D, z0=z1 - sw, z1=z1,
                         upright=True, faces=faces)
        out.append(entry)
    return out


def drawer_rise(cab, std: Standard = STANDARD) -> int:
    """How far every box's bottom stands above its own face's bottom: the
    bottom panel (t) plus the runner's lift — 16 + 5 = 21. The bottom box sits
    on a runner standing on the bottom panel, and every box above hangs off its
    own face by the same figure (drawer setting, 28 September 2026)."""
    return cab.drawer_rise_of(std)


def inner_drawer_z(cab, std: Standard = STANDARD, materials: dict = None,
                   count: Optional[int] = None) -> List[int]:
    """Where `count` inner drawers stand by default — each box's bottom above
    the carcass underside, bottom drawer first (ruled by Rudolf, 28 September
    2026): the lowest box on a runner standing on the bottom panel
    (`drawer_rise`, 21), and the rest EQUALLY SPACED up the carcass — the inside
    height between the bottom panel and the top (H - 2t, off `geometry`) split
    into `count` equal slots, one box starting at the foot of each. Whole
    millimetres; typed per drawer afterwards, and regenerated whenever the count
    changes.

    W 600 H 720 (inside 688), two drawers: 21 and 365; four: 21, 193, 365, 537.
    """
    mats = MATERIALS if materials is None else materials
    n = len(cab.inner_drawers) if count is None else int(count)
    if n <= 0:
        return []
    inside = geometry(cab, std, mats).height - 2 * std.board_t
    rise = drawer_rise(cab, std)
    return [rise + int(round(k * inside / n)) for k in range(n)]


def drawer_layout(cab, std: Standard = STANDARD, materials: dict = None) -> List[dict]:
    """Where every drawer's face, box and runners stand — THE one place a box is
    placed (28 September 2026, sketch `drawer-setting-sketch-v2.svg`, confirmed
    by Rudolf). The support check, the drawer checks and the 3D all read this,
    so none of them can disagree.

    In the supports spec's carcass-local frame: x across from the left side, y
    from the FRONT face of the sides towards the back, z up from the underside
    of the sides. Order of work, as ruled:

      1. the FACES are spaced exactly as they always were — the bottom face
         flush with the carcass underside, `stack_gap` between faces, the last
         drawer in the list lowest; a door (if any) above them;
      2. each box sits at the bottom of its OWN face: its bottom is the face
         bottom plus the drawer's `offset` — by default `drawer_rise`, the
         bottom panel (t) plus the runner's `lift`, 16 + 5 = 21, so the bottom
         box sits on a runner standing on the bottom panel. The offset is
         editable per drawer (ruled 28 September 2026, "faces lead, boxes
         follow"): the bottom drawer may be raised, never lowered below 21;
         an upper one either way; every box within its own face's height,
         and never flush: `drawer_box_clear` (2) clear of the face's top and
         bottom (ruled 29 September 2026) — `max_box` reads it;
      3. the checks read the result. No box position ever moves a face.

    The box front is flush with the carcass front (y 0) and the face overlays
    it; the box is the runner's length long (the drawer side as cut, off
    `geometry`); its outside width is the opening less the runner's side
    clearance each way. Each runner's outer rail is against its carcass side,
    its front at the carcass front edge, its bottom `lift` below the box's; the
    inner member starts `setback` behind the box front. Per drawer, in stack
    order (drawer 1 is the top of the list):

        n, face (z0, z1), box (x0, x1, y0, y1, z0, z1), rails [(x0, x1)],
        rail (y0, y1, z0, z1), inner_y0, travel, inner

    Worked (W 600, 3 drawers of face 240 / 240 / 233, boxes 150, legacy or
    Gelmar, 560 deep): drawer 3 (the lowest) face 0-233, box z 21-171, box x
    29.5-570.5, y 0-500, rails z 16-61; drawer 2 face 235-475, box z 256-406.
    Pinned in check_runners.py. Nothing here is a cut size.

    An INNER drawer (`Drawer.inner`) is behind the door and outside the face
    stack: its box bottom is its own `z` (or `inner_drawer_z`'s default), its
    face is the box's size — the box's outside width, the box's height —
    with its front on the shelves' line, flush with the carcass front edges,
    so the box and the runner start a face thickness back (`face_y`). Its
    runner length is picked over the depth less that thickness, as the engine
    cuts it. `face_x` / `face_y` say where each face stands across and in
    depth: an outer face spans the width less `door_single_gap` and stands
    proud of the carcass front (negative y).
    """
    stack = cab.drawer_list
    if cab.is_panel or not stack:
        return []
    mats = MATERIALS if materials is None else materials
    g = geometry(cab, std, mats)
    xs = [x for x, _ in g.footprint]
    W = max(xs) - min(xs)
    t = std.board_t
    rr = cab.runner_or_legacy
    clear = rr.side_clearance
    offset = drawer_rise(cab, std)
    rail_t = rr.rail_thickness
    rails = [(t, t + rail_t), (W - t - rail_t, W - t)]
    gap = std.door_single_gap
    out = []

    def one(i, d, fz0, fz1, bz0, y0, length, face_x, face_y, limit=None):
        bh = cab.box_height_of(d, std)          # Auto: the tallest that fits
        return {"n": i + 1, "index": i, "inner": bool(d.inner),
                "face": (fz0, fz1), "offset": bz0 - fz0,
                # the tallest box this face takes at this offset (rule 5):
                # up to the face top less drawer_box_clear on an outer drawer,
                # and under a Top Front / Top Rear band less the same
                "max_box": (fz1 if limit is None else limit) - bz0,
                # whether the box as it stands keeps to that: inside its face
                # by the clear both ends, and under the band — what the
                # editor's red <= says (an inner drawer's face is its box)
                "fits": limit is None or (bz0 >= fz0 + std.drawer_box_clear
                                          and bz0 + bh <= limit),
                "face_x": face_x, "face_y": face_y,
                "face_board": cab.face_board_of(d),
                "box": (t + clear, W - t - clear, y0, y0 + length, bz0, bz0 + bh),
                "rails": rails,
                "rail": (y0, y0 + length, bz0 - rr.lift, bz0 - rr.lift + rr.height),
                "inner_y0": y0 + rr.setback,
                "travel": rr.travel(length) if length else 0,
                "box_h": bh, "auto": d.box_height is None,
                "base": cab.base_of(d), "box_board": cab.box_board_of(d),
                # the board the box's top edges are banded in the colour of
                # (29 September 2026), '' when that resolves to no edging
                "box_edge_board": (cab.box_edge_board_of(d)
                                   if cab.drawer_box_tape_of(mats, d) else ""),
                "box_edge_kind": cab.box_edge_kind_of(d)}

    # the face stack, exactly as it always was
    at = 0
    outer_len = std.pick_runner(cab.depth, rr.lengths) or 0
    for i in range(len(stack) - 1, -1, -1):          # the bottom face is the last
        d = stack[i]
        if d.inner:
            continue
        fh = int(d.face_height or 0)
        ft = _front_t(mats, cab.face_board_of(d), std)
        # the box sits at the bottom of its OWN face, its drawer's offset up —
        # 21 unless the drawer says otherwise (faces lead, boxes follow)
        rise = offset if d.offset is None else int(d.offset)
        out.append(one(i, d, at, at + fh, at + rise, 0, outer_len,
                       (gap / 2, W - gap / 2), (-ft, 0), cab.box_top_limit_of(d, std)))
        at += fh + std.stack_gap
    # behind the door: each at its own height, its face the box's size
    inner = [(i, d) for i, d in enumerate(stack) if d.inner]
    auto = inner_drawer_z(cab, std, mats, len(inner))
    for k, (i, d) in enumerate(reversed(inner)):     # the last in the list lowest
        ft = _front_t(mats, cab.face_board_of(d), std)
        z = int(d.z) if d.z is not None else auto[k]
        length = std.pick_runner(cab.depth - ft, rr.lengths) or 0
        out.append(one(i, d, z, z + cab.box_height_of(d, std), z, ft, length,
                       (t + clear, W - t - clear), (0, ft)))
    # Each outer drawer's allowed OFFSET (29 September 2026, the fixes brief):
    # at least `drawer_rise` (21) for the bottom drawer — its runner stands on
    # the bottom panel — and `drawer_box_clear` for an upper one; at most the
    # offset at which the box still fits under its top limit: the typed box,
    # or for Auto the smallest box its runner allows (the runner's height).
    # The editor's Offset field is held to this; the checks name what falls
    # outside it, and a stored value outside it is cut as it stands.
    outer = [u for u in out if not u["inner"]]
    lowest = min(outer, key=lambda u: u["face"][0])["n"] if outer else None
    for u in outer:
        d = stack[u["index"]]
        f0 = u["face"][0]
        limit = cab.box_top_limit_of(d, std)
        need = (int(d.box_height) if d.box_height is not None
                else int(math.ceil(rr.height)))
        u["offset_min"] = offset if u["n"] == lowest else std.drawer_box_clear
        u["offset_max"] = limit - f0 - need
    return sorted(out, key=lambda u: u["n"])


def drawer_box_tops(cab, std: Standard = STANDARD, materials: dict = None) -> List[Tuple[int, int]]:
    """(drawer number, top of its box) for each drawer, up the carcass — read
    off `drawer_layout`, the one place a box is placed."""
    return [(u["n"], u["box"][5]) for u in drawer_layout(cab, std, materials)]


def back_supports_fit(cab, std: Standard = STANDARD, materials: dict = None) -> Tuple[int, int]:
    """(needed, available) height for the Back supports: how much the stack of
    them takes between Back 1's top and the bottom panel, and how much there is.
    Needed <= available means they fit (a zero gap is a fit)."""
    from .engine import SUPPORT_W
    lay = support_layout(cab, std, materials)
    backs = [u for u in lay if u["type"] == "back"]
    if not backs:
        return 0, 0
    top = max(u["z1"] for u in backs if u["n"] == 1)
    return len(backs) * SUPPORT_W, int(top - std.board_t)


def shelf_layout(cab, std: Standard = STANDARD, materials: dict = None) -> List[dict]:
    """Where each shelf is DRAWN: spaced evenly from the top face of the bottom
    panel to the top of the sides, fixed shelves listed first. Display only —
    real heights are set at fitment and nothing validates them. Per entry
    `fixed`, `z0`, `z1`, `depth` (the engine's, off Standard) and `width`."""
    if cab.is_panel or cab.template == "none" or cab.corner_kind in ("mitre", "ell"):
        return []
    n_fixed, n_adj = int(cab.fixed_shelves or 0), int(cab.shelves or 0)
    if n_fixed + n_adj <= 0:
        return []
    mats = MATERIALS if materials is None else materials
    parts = solid_parts(cab, std, mats)
    if not parts or any(q.role == "carcass" for q in parts):
        return []
    g = geometry(cab, std, mats)
    xs = [x for x, _ in g.footprint]
    W, D, H, t = max(xs) - min(xs), g.depth, g.height, std.board_t
    n = n_fixed + n_adj
    gap = (H - t - n * t) / (n + 1)
    out = []
    for k in range(n):
        fixed = k < n_fixed
        z0 = t + gap * (k + 1) + t * k
        out.append(dict(fixed=fixed, z0=round(z0, 1), z1=round(z0 + t, 1),
                        depth=std.shelf_depth(D, fixed=fixed),
                        width=cab.shelf_width or std.internal_width(W)))
    return out


@dataclass
class Tape:
    """One banded edge of a Part, for drawing: which face of the box it is on
    (SUPPORT_SIDES, in the Part's own frame), the board whose edging colour it
    is, and the kind."""
    side: str
    board: str
    kind: str


def interior_parts(cab, std: Standard = STANDARD, materials: dict = None) -> List[Tuple[Part, List[Tape]]]:
    """The supports and shelves of a straight carcass as solids in the
    cabinet's frame, each with the edges it is banded on — for the 3D view.

    `(part, tapes)` per rail and per shelf. A support is `Part` role 'support',
    labelled 'Top Front', 'Top Rear' or 'Back n', in the board its row is cut from;
    its tapes are the row's chosen edges in the row's edging board, only when
    the row resolves to an edging at all. A shelf is role 'shelf' in the carcass
    board, its front edge in the carcass edging (the exterior board's colour),
    and its label says 'fixed' where it is. Tape is a colour on a face and never
    moves a part (hard rule 5).
    """
    from .model import support_edges_of
    mats = MATERIALS if materials is None else materials
    lay = support_layout(cab, std, mats)
    shelves = shelf_layout(cab, std, mats)
    drawers = drawer_parts(cab, std, mats)
    if not lay and not shelves:
        return _drawer_tapes(cab, drawers, std, mats)
    g = geometry(cab, std, mats)
    xs = [x for x, _ in g.footprint]
    W, D, t = max(xs) - min(xs), g.depth, std.board_t
    # the spec frame's y runs from the front; the Part's from the wall
    flip = {"y0": "y1", "y1": "y0"}
    out = []
    for u in lay:
        row = u["row"]
        label = {"front": "Top Front", "top_rear": "Top Rear"}.get(u["type"], f"Back {u['n']}")
        part = _box("support", cab.support_row_cut_board(row), t, W - t,
                    D - u["y1"], D - u["y0"], u["z0"], u["z1"], "x", label)
        tapes = []
        if cab.support_row_tape(mats, row):
            board, kind = cab.support_row_board(mats, row), cab.support_row_kind(row)
            edges = support_edges_of(row) if row.type else ["front"]
            for e in edges:
                side = u["faces"][e]
                tapes.append(Tape(flip.get(side, side), board, kind))
        out.append((part, tapes))
    for sh in shelves:
        part = _box("shelf", cab.carcass_board, t, t + sh["width"], D - sh["depth"], D,
                    sh["z0"], sh["z1"], "x", "fixed" if sh["fixed"] else "")
        tapes = [Tape("y1", cab.exterior_board, "pvc")] if cab.carcass_tape(mats) else []
        out.append((part, tapes))
    return out + _drawer_tapes(cab, drawers, std, mats)


def _drawer_tapes(cab, drawers: List[Part], std: Standard, mats: dict):
    """Each drawer part with its bands: a box's sides, front and back are
    banded on their TOP long edge (edge_l 1 on lines 18 and 19) in the colour
    of the drawer's box edging board (29 September 2026); nothing else is."""
    try:
        edge = {u["index"]: (u["box_edge_board"], u["box_edge_kind"])
                for u in drawer_layout(cab, std, mats)}
    except ValueError:
        edge = {}
    out = []
    for q in drawers:
        board, kind = edge.get(q.index, ("", ""))
        tapes = ([Tape("z1", board, kind)]
                 if board and q.role in ("drawer_side", "drawer_front", "drawer_back")
                 else [])
        out.append((q, tapes))
    return out


# The parts of a drawer that slide out with its face when the fronts open.
DRAWER_MOVING = ("drawer", "drawer_side", "drawer_front", "drawer_back", "drawer_base",
                 "runner_inner")

# The runner's two members (R3, 29 September 2026): hardware, drawn, not cut.
RUNNER_ROLES = ("runner_outer", "runner_inner")


def drawer_parts(cab, std: Standard = STANDARD, materials: dict = None) -> List[Part]:
    """Every drawer's box — two sides, a front, a back and a base — its inner
    face where it is an inner drawer, and its two runners' outer rails, as
    solids in the cabinet's frame, for the 3D view (Part 6, 28 September 2026).

    Placed by `drawer_layout` and nothing else, and sized as the cut list cuts
    them: the sides the runner's length (grain along it), the front and back
    between the sides, a grooved 3 mm base `drawer_base_offset` up the sides
    and `groove_engage` into all four, a housed 16 mm one between them on the
    bottom edge. Each carries its drawer's `index`, which is how the scene
    slides it out with its face. A runner is TWO members a side (R3, 29
    September 2026), both board '' — hardware, not a cut-list line — sized off
    the catalogue record, never Standard:

      * `runner_outer`, the channel fixed to the carcass side: rail_thickness
        x height x length, against the side from the carcass front, `lift`
        under the box — it does not slide;
      * `runner_inner`, the member fixed to the drawer side: inner_thickness x
        inner_height, against the box side, centred vertically in the outer,
        from `setback` behind the box front to the outer's back — nested in
        the channel when closed, and sliding out with the box.

    Kept out of `solid_parts`, so the plan, Finish and every wall elevation
    are unchanged.
    """
    mats = MATERIALS if materials is None else materials
    try:
        lay = drawer_layout(cab, std, mats)
    except ValueError:
        return []                  # no runner fits: nothing is cut, nothing drawn
    if not lay:
        return []
    D = geometry(cab, std, mats).depth
    t, e = std.board_t, std.groove_engage
    rr = cab.runner_or_legacy
    it, ih = rr.inner_t, rr.inner_h
    out = []
    for u in lay:
        i, n = u["index"], u["n"]
        bx0, bx1, by0, by1, bz0, bz1 = u["box"]
        # spec y (from the front) to the part frame's (from the wall)
        py0, py1 = D - by1, D - by0
        board = u["box_board"]
        label = f"drawer {n}"
        out.append(_box("drawer_side", board, bx0, bx0 + t, py0, py1, bz0, bz1, "y", label, i))
        out.append(_box("drawer_side", board, bx1 - t, bx1, py0, py1, bz0, bz1, "y", label, i))
        out.append(_box("drawer_front", board, bx0 + t, bx1 - t, py1 - t, py1, bz0, bz1, "x", label, i))
        out.append(_box("drawer_back", board, bx0 + t, bx1 - t, py0, py0 + t, bz0, bz1, "x", label, i))
        if u["base"] == "board":
            z0 = bz0 + std.drawer_base_offset
            out.append(_box("drawer_base", cab.back_board, bx0 + t - e, bx1 - t + e,
                            py0 + t - e, py1 - t + e, z0, z0 + std.back_t, "y", label, i))
        else:
            out.append(_box("drawer_base", board, bx0 + t, bx1 - t, py0 + t, py1 - t,
                            bz0, bz0 + t, "y", label, i))
        if u["inner"]:
            fx0, fx1 = u["face_x"]
            fy0, fy1 = u["face_y"]
            out.append(_box("drawer", u["face_board"], fx0, fx1, D - fy1, D - fy0,
                            u["face"][0], u["face"][1], "z", "inner", i))
        ry0, ry1, rz0, rz1 = u["rail"]
        for rx0, rx1 in u["rails"]:
            out.append(_box("runner_outer", "", rx0, rx1, D - ry1, D - ry0, rz0, rz1, None,
                            f"runner, drawer {n}", i))
        # the inner members: against each box side, on the side facing its
        # channel, centred on the channel's height
        mid = (rz0 + rz1) / 2
        iy0 = u["inner_y0"]
        for ix0, ix1 in ((bx0 - it, bx0), (bx1, bx1 + it)):
            out.append(_box("runner_inner", "", ix0, ix1, D - ry1, D - iy0,
                            mid - ih / 2, mid + ih / 2, None, f"runner, drawer {n}", i))
    return out


def tape_solids(part: Part, tapes: List[Tape], band: float) -> List[Part]:
    """The bands a Part's tapes are drawn as: a thin box `band` deep INSIDE the
    finished size on each banded face, role 'tape', in the tape's board, its
    kind as the label. Nothing is moved and nothing grows (hard rule 5)."""
    xs = [x for x, _ in part.outline]
    ys = [y for _, y in part.outline]
    x0, x1, y0, y1, z0, z1 = min(xs), max(xs), min(ys), max(ys), part.z0, part.z1
    out = []
    for tp in tapes:
        bx0, bx1, by0, by1, bz0, bz1 = x0, x1, y0, y1, z0, z1
        if tp.side == "x0":
            bx1 = x0 + band
        elif tp.side == "x1":
            bx0 = x1 - band
        elif tp.side == "y0":
            by1 = y0 + band
        elif tp.side == "y1":
            by0 = y1 - band
        elif tp.side == "z0":
            bz1 = z0 + band
        elif tp.side == "z1":
            bz0 = z1 - band
        else:
            continue
        out.append(_box("tape", tp.board, bx0, bx1, by0, by1, bz0, bz1, None, tp.kind))
    return out


def front_outlines(job, cab, p, std: Standard = STANDARD) -> List[Tuple[Part, List[Point]]]:
    """A cabinet's fronts in world plan coordinates, bottom first, for the plan.

    `(part, outline)` per door leaf, drawer face and blind panel, lowest first,
    so drawn in order the one seen from above ends up on top.
    """
    if job.room is None or cab.is_panel:
        return []
    frame = _placed_frame(job.room, p)
    fronts = [q for q in solid_parts(cab, std, job.materials) if q.front]
    fronts.sort(key=lambda q: q.z1)
    return [(q, [_to_plan(frame, v) for v in q.outline]) for q in fronts]


def _beside(rm: Room, wall_id: str) -> set:
    """The walls either side of this one, off the corners its ends make — the
    wall meeting its start and the wall meeting its end (`connections`). A
    free wall, or the end of an open run, has nothing beside it there."""
    con = connections(rm)
    beside = {con["prev"].get(wall_id), con["next"].get(wall_id)}
    beside.discard(None)
    beside.discard(wall_id)
    return beside


def return_faces(job, wall_id: str, std: Standard = STANDARD) -> List[dict]:
    """The runs on the walls either side as you would SEE them from this wall.

    For the Finish view (23 September 2026). Every board of every cabinet and
    placed panel on the two neighbouring walls (`solid_parts`) is turned into
    this wall's frame, and each face of it that looks towards someone standing
    in front of this wall is projected straight onto the wall's plane — a true
    orthographic view, nothing unfolded or turned. A vertical face always lands
    as a rectangle: `x0`/`x1` along this wall, `z0`/`z1` off the floor
    (`carcass_z`, so legs are in it). `out` is how far out from this wall the
    face stands, which is how near the viewer it is: sorted furthest first, so
    painted in order a nearer end panel covers the carcass side behind it.

    `oblique` is a face not square on to the viewer — a mitre door — and
    `vertical` is which way its grain runs as seen: True up, False along, None
    into the page. Faces edge on to the viewer are left out; they have no area.
    """
    rm = job.room
    if rm is None or wall_id not in [w.id for w in rm.walls]:
        return []
    beside = _beside(rm, wall_id)
    here = _wall(rm, wall_id)
    (sx, sy), (dx, dy), (nx, ny) = wall_frames(rm)[here.id]

    def local(q):                        # world plan -> (along this wall, out from it)
        return ((q[0] - sx) * dx + (q[1] - sy) * dy,
                (q[0] - sx) * nx + (q[1] - sy) * ny)

    items = ([(cab, p) for cab, p, _lay in placed(job)] + placed_panels(job))
    out = []
    for cab, p in items:
        if p.wall not in beside:
            continue
        frame = _placed_frame(rm, p)
        (_o, (wdx, wdy), (wnx, wny)) = frame
        z = carcass_z(cab, p, std)
        for part in solid_parts(cab, std, job.materials):
            pts = [local(_to_plan(frame, v)) for v in part.outline]
            cx = sum(u for u, _ in pts) / len(pts)
            cy = sum(v for _, v in pts) / len(pts)
            if part.grain in ("x", "y"):
                ex, ey = ((wdx, wdy) if part.grain == "x" else (wnx, wny))
                along = abs(ex * dx + ey * dy)
            for k, (ua, va) in enumerate(pts):
                ub, vb = pts[(k + 1) % len(pts)]
                length = math.hypot(ub - ua, vb - va)
                if length < 1e-6:
                    continue
                # the edge's normal, turned away from the part's own middle
                fx, fy = (vb - va) / length, -(ub - ua) / length
                if fx * ((ua + ub) / 2 - cx) + fy * ((va + vb) / 2 - cy) < 0:
                    fx, fy = -fx, -fy
                if fy <= 0.05:           # faces away from the viewer, or edge on
                    continue
                x0 = max(min(ua, ub), 0)
                x1 = min(max(ua, ub), here.length)
                if x1 - x0 < 0.5 or min(va, vb) < -1:
                    continue
                if part.grain == "z":
                    vertical = True
                elif part.grain in ("x", "y"):
                    vertical = False if along > 0.5 else None
                else:
                    vertical = None
                out.append({"cabinet": cab.number, "wall": p.wall,
                            "panel": cab.is_panel, "role": part.role,
                            "board": part.board, "index": part.index,
                            "label": part.label,
                            "x0": round(x0, 1), "x1": round(x1, 1),
                            "z0": z + part.z0, "z1": z + part.z1,
                            "out": round((va + vb) / 2, 1),
                            "oblique": fy < 0.99, "vertical": vertical})
    out.sort(key=lambda f: f["out"])
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
    # An ATTACHED panel is part of its cabinet's geometry (spec B6): standing
    # in another cabinet is the same critical as the carcass standing there.
    # Against its OWN cabinet it is `attached_carcass_overlaps`' warning, and
    # against another panel `panel_clashes`' — neither is repeated here.
    for cab, p in placed_panels(job):
        if not cab.is_attached or p.wall not in wall_ids:
            continue
        g = geometry(cab, std, job.materials)
        items.append((cab, p, g, "panel", cabinet_footprint(rm, p, cab, std, job.materials),
                      _z_span(cab, p, g, std)))
    out = []
    for i, (a, pa, ga, la, fa, za) in enumerate(items):
        for b, pb, gb, lb, fb, zb in items[i + 1:]:
            if a.is_panel and b.is_panel:
                continue                           # panel_clashes' warning
            if a.is_panel and a.attached_to == b.number or \
                    b.is_panel and b.attached_to == a.number:
                continue                           # attached_carcass_overlaps' warning
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
            layer = run_key(lb if a.is_panel else la)
            out.append(Overlap(a=a.number, b=b.number, wall=wall, layer=layer, mm=along))
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
        # A cabinet's own attached panels move with it, so they are no more a
        # thing for it to come to rest against than its own sides are.
        if p.wall != wall_id or cab.number == exclude or \
                (exclude is not None and cab.attached_to == exclude):
            continue
        g = geometry(cab, std, mats)
        out.append((cab, p, g, "panel", _z_span(cab, p, g, std)))
    return out


def free_z(cab, std: Standard = STANDARD) -> int:
    """Where a newly-placed item's underside goes: an upper hangs at
    `Standard.upper_z` (ruled 2-3 October 2026), everything else stands on the
    floor at 0. The elevation drag keeps whatever height it was dropped at;
    this is for the three places that used to write z 0 for every kind — the
    Placements wall picker, the plan drop and the 3D drop. Nothing caps it
    against the ceiling: the ceiling and tip-up checks say what they say.

        >>> from cabinetgen.model import Cabinet
        >>> free_z(Cabinet(number=1, width=600, height=720, depth=300, kind="upper"))
        1500
        >>> free_z(Cabinet(number=1, width=600, height=720, depth=560, kind="base"))
        0
    """
    return int(std.upper_z) if cab.kind == "upper" else 0


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


def y_snap_points(job, number: int, wall_id: str, std: Standard = STANDARD):
    """How far off a wall a PANEL may come to rest, and why — `Placement.y`.

    The depth twin of `snap_points`, for the plan drag (22 September 2026). Only
    a panel has a y: a carcass stands against the wall it is placed on. The
    candidates are the wall itself and every face of what already stands on that
    wall, carcass or panel (`_on_wall`), whatever its height — a bulkhead front
    lines up with the fronts of the base units two metres below it, which is
    exactly why it is not filtered by height the way the sideways snap is:

        against the wall            y = 0, the back of every carcass
        in front of N               its back on N's front face
        front level with N          its front face on N's front face
        behind N / back level with N    against another panel's back

    Each carries the stretch of wall N stands on (`x0`/`x1`), so the browser
    can prefer the neighbour nearest along the wall when two share a depth; it
    never limits where the target applies. Sorted by depth. Nothing negative:
    a panel cannot go into the wall.
    """
    rm = job.room
    cab = next((c for c in job.cabinets if c.number == number), None)
    if rm is None or cab is None or not cab.is_panel:
        return []
    mine = geometry(cab, std, job.materials).depth
    out = [(0, "against the wall", None, None)]
    for other, op, og, lay, _z in _on_wall(job, wall_id, std, exclude=number):
        span = (op.x, op.x + og.width)
        oy = int(getattr(op, "y", 0) or 0) if lay == "panel" else 0
        front = oy + og.depth
        out.append((front, f"in front of {other.number}") + span)
        out.append((front - mine, f"front level with {other.number}") + span)
        if lay == "panel":
            out.append((oy, f"back level with {other.number}") + span)
            out.append((oy - mine, f"behind {other.number}") + span)
    keep, seen = [], set()
    for y, why, x0, x1 in sorted(out, key=lambda t: (t[0], t[1])):
        if y < 0 or (y, why) in seen:
            continue
        seen.add((y, why))
        keep.append({"y": int(y), "why": why, "x0": x0, "x1": x1})
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


def door_hinges(cab, g: CabinetGeometry, p):
    """Where each door leaf hangs, in the cabinet's own frame.

    One entry per leaf, in leaf order: `((x, y), closed angle, turn, width)` —
    the hinge point on the outline's front edge, the direction the closed leaf
    lies in from it, the sign of the turn that sweeps it into the room, and
    the leaf's cut width. Factored out of `swing_envelopes` for the 3D view (23
    September 2026), so the plan's arcs and a 3D door's hinge axis are the one
    answer; the envelopes are unchanged by it.

    Which edge each leaf hangs from is `model.hinge_side` — the per-leaf choice
    on the cabinet, or the old rule when none is set: a pair at its outer edges
    opening from the middle, a single door left unless the placement is
    flipped. A corner unit hinges off its real front face instead — see
    `_corner_door_hinges`.
    """
    if not g.door_widths:
        return []
    if g.source == "corner":
        return _corner_door_hinges(cab, g, p)
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
    return hinge_specs


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
    hinge_specs = door_hinges(cab, g, p)

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
    out: List[Clash] = []

    geoms = {cab.number: geometry(cab, std) for cab, _p, _l in items}
    attached = []
    for pan, pp in placed_panels(job):
        if pan.is_attached and pp.wall in {w.id for w in rm.walls}:
            pg = geometry(pan, std, job.materials)
            attached.append((pan, cabinet_footprint(rm, pp, pan, std, job.materials),
                             _z_span(pan, pp, pg, std)))
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
            # An attached panel is part of its cabinet's geometry (spec B6), its
            # own cabinet's included: a door sweeping into an end panel that
            # stands proud of it is a real foul. Touching is clear, as ever.
            for pan, fp, zs in attached:
                if zt[0] >= zs[1] or zs[0] >= zt[1]:
                    continue
                if polygons_overlap(env, fp):
                    out.append(Clash(cab.number, kind,
                                     f"panel {pan.number} on cabinet {pan.attached_to}"))
            for w in rm.walls:
                if w.id == p.wall:
                    continue
                if convex_overlap(env, [(w.x0, w.y0), (w.x1, w.y1)]):
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
        # An ATTACHED panel against a carcass is not this list's: its own
        # cabinet is `attached_carcass_overlaps`' warning and any other
        # cabinet is `overlaps`' critical (spec B6). Against another panel and
        # across an opening it is reported here like any panel.
        against = [] if cab.is_attached else list(boxes)
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

    Only at a nominal 90-degree INSIDE corner (ruled 29 September 2026). At
    any other inside angle the boards do not meet: each plinth ends where its
    run ends, and `plinth_open_corners` names the corner for a closing piece
    cut on site. Walls in line or an outside corner give no butt either.
    """
    rm = job.room
    prev_id = _plinth_meets(job, run, std)
    if prev_id is None:
        return None
    return prev_id if corner_angle(rm, prev_id, std) == 90 else None


def _plinth_meets(job, run: Run, std: Standard = STANDARD) -> Optional[str]:
    """The wall before this run's start corner, when a fitted plinth on that
    wall runs into the same corner at the same height — whatever the angle
    there. None where no two plinths meet at this run's start."""
    rm = job.room
    if rm is None or not run.touches_start:
        return None
    prev_id = prev_wall(rm, run.wall, std)
    if prev_id is None:
        return None
    for other in runs(job, std):
        if (other.wall == prev_id and other.z == run.z and other.touches_end
                and _plinth_fitted(job, other)):
            return prev_id
    return None


def plinth_open_corners(job, std: Standard = STANDARD) -> List[Tuple[str, str, float]]:
    """(wall before, wall after, angle) for every INSIDE corner that is not a
    nominal 90 where two fitted plinths meet (ruled 29 September 2026). There
    is no butt deduction: each board ends where its run ends, and the gap
    between them is closed with a piece cut on site — a WARNING, never a
    critical, because the boards on the order are right as they stand."""
    rm = job.room
    if rm is None:
        return []
    out = []
    for run in runs(job, std):
        if run.z != 0 or not _plinth_fitted(job, run):
            continue
        prev_id = _plinth_meets(job, run, std)
        if prev_id is None:
            continue
        a = corner_angle(rm, prev_id, std)
        if a != 90 and a < 180:
            out.append((prev_id, run.wall, a))
    return out


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


def plinth_solids(job, std: Standard = STANDARD) -> List[dict]:
    """The plinth boards that were CHOSEN, as solids in world plan coordinates —
    for the 3D view (23 September 2026).

    One per board `plinth_lengths` cuts, so a long run's joint is where the cut
    list says it is. It stands where the plan draws its face: `plinth_setback`
    behind the run's carcass front (`run.depth`, off `geometry`), one board
    thick behind that line, from the floor to `leg_height` — which is the
    board's own width, since it covers the legs. Board and edging are the lead
    cabinet's carcass, as `engine.plinth_panels` cuts it. A run with no
    `PlinthChoice`, or one hung off the floor, has nothing here.
    """
    rm = job.room
    if rm is None:
        return []
    by_number = {c.number: c for c in job.cabinets}
    out = []
    for run in runs(job, std):
        if run.z != 0:
            continue
        choice = plinth_choice_for(job, run)
        if choice is None or not choice.fitted:
            continue
        lead = by_number[run.first]
        face = max(run.depth - std.plinth_setback, 0)
        back = max(face - std.board_t, 0)
        pieces = plinth_lengths(job, run, std)
        for i, (length, at) in enumerate(pieces):
            local = [(at, back), (at + length, back), (at + length, face), (at, face)]
            out.append({"wall": run.wall, "layer": run.layer, "first": run.first,
                        "cabinets": list(run.cabinets), "piece": i, "pieces": len(pieces),
                        "board": lead.carcass_board, "length": length,
                        "outline": [to_world(rm, run.wall, x, y)[:2] for x, y in local],
                        "z0": 0, "z1": std.leg_height})
    return out


def filler_solids(job, std: Standard = STANDARD) -> List[dict]:
    """The fillers that were CHOSEN, as solids in world plan coordinates — for
    the 3D view (23 September 2026).

    A filler stands in the gap it fills: `gap_outline`, the run's depth, from
    the underside of the cabinet that bounds it (`carcass_z`, so a base run's
    filler stands on the legs' height like the carcasses beside it) up the
    gap's height. It is drawn at the gap, not at the oversize it is cut to —
    the scribe allowance is trimmed on site and the drawing shows the room.
    """
    rm = job.room
    if rm is None:
        return []
    by_number = {c.number: c for c in job.cabinets}
    out = []
    for g in gaps(job, std):
        if g.treatment != "filler":
            continue
        n = g.after if g.after is not None else g.before
        cab = by_number.get(n)
        p = placement_for(job, n) if cab is not None else None
        if cab is None or p is None:
            continue
        z0 = carcass_z(cab, p, std)
        out.append({"wall": g.wall, "layer": g.layer, "after": g.after,
                    "before": g.before, "board": g.board, "height": g.height,
                    "width": g.filler_width(std),
                    "outline": gap_outline(rm, g), "z0": z0, "z1": z0 + g.height})
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
        t = tip_inputs(cab, p, rm.ceiling, std)
        top = t["underside"] + t["height"]
        need = tip_clearance(t["height"], t["depth"], t["legs"], t["setback"])
        if top <= rm.ceiling < need:
            out.append((cab.number, top, need, rm.ceiling))
    return out


def tip_inputs(cab, p, ceiling, std: Standard = STANDARD) -> dict:
    """Every figure the tip-up check reads, and nothing else.

    `tip_problems` works from exactly this, and so does the fingerprint an
    accepted tip-up critical is stored with (`validate.fingerprint`) — so an
    acceptance lapses when, and only when, something the check used has moved.
    Height and depth are the panel set's (`geometry`), never the declared ones.
    """
    g = geometry(cab, std)
    return {"height": g.height, "depth": g.tip_depth,
            "legs": std.leg_height if stands_on_legs(cab, p) else 0,
            "setback": std.leg_setback,
            "underside": carcass_z(cab, p, std),
            "ceiling": ceiling}


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
    Every figure is `ceiling_inputs`', which is also what an accepted
    above-ceiling critical is fingerprinted with.
    """
    rm = job.room
    if rm is None or not rm.ceiling:
        return []
    out = []
    for t in _ceiling_items(job, std):
        top = t["underside"] + t["height"]
        if top > rm.ceiling:
            out.append((t["number"], top, rm.ceiling))
    return out


def _ceiling_items(job, std: Standard = STANDARD) -> List[dict]:
    rm = job.room
    out = []
    for cab, p, _lay in placed(job):
        out.append(ceiling_inputs(cab, p, rm.ceiling, std))
    # An attached panel is part of its cabinet's geometry (spec B6): one that
    # runs up past the ceiling cannot be fitted any more than the carcass
    # could. A standalone panel is not compared — it stays exactly as it was.
    for cab, p in placed_panels(job):
        if cab.is_attached:
            out.append(ceiling_inputs(cab, p, rm.ceiling, std, job.materials))
    return out


def above_wall(job, std: Standard = STANDARD) -> List[Tuple[int, int, int, str]]:
    """(cabinet, top of carcass, wall height, wall) for anything standing on a
    wall LOWER than the ceiling and reaching above it (`Wall.height`, 2
    October 2026). A WARNING, never a critical: a tall unit can stand against
    a half wall. Not said where the item is above the ceiling too — that is
    `above_ceiling`'s, and one problem gets one message.
    """
    rm = job.room
    if rm is None:
        return []
    heights = {w.id: w.height for w in rm.walls if w.height}
    items = [(cab, p) for cab, p, _lay in placed(job)]
    items += [(cab, p) for cab, p in placed_panels(job) if cab.is_attached]
    out = []
    for cab, p in items:
        h = heights.get(p.wall)
        if h is None:
            continue
        top = carcass_z(cab, p, std) + geometry(cab, std, job.materials).height
        if top > h and not (rm.ceiling and top > rm.ceiling):
            out.append((cab.number, top, h, p.wall))
    return out


def low_openings(rm: Room) -> List[Tuple[str, str, int, int]]:
    """(wall, kind, head, wall height) for every opening whose head is above
    its wall — a window taller than the wall it is in cannot be. A CRITICAL
    (`opening-height`). Nothing is said of a wall whose height is unknown.
    """
    out = []
    for w in rm.walls:
        h = wall_height(rm, w)
        if not h:
            continue
        for o in w.openings:
            if o.head > h:
                out.append((w.id, o.kind, o.head, h))
    return out


def ceiling_inputs(cab, p, ceiling, std: Standard = STANDARD, materials: dict = None) -> dict:
    """Every figure the above-ceiling check reads, and nothing else: where the
    carcass stands (`carcass_z`), its height off the panel set (`geometry`,
    never the declared figure) and the ceiling. The fingerprint of an accepted
    above-ceiling critical is this (29 September 2026), so the acceptance
    lapses when, and only when, one of them moves."""
    g = geometry(cab, std, materials) if materials is not None else geometry(cab, std)
    return {"number": cab.number, "underside": carcass_z(cab, p, std),
            "height": g.height, "ceiling": ceiling}


def ceiling_inputs_for(job, number, std: Standard = STANDARD):
    """`ceiling_inputs` for the item numbered `number`, or None where the
    check reads nothing (no room, no measured ceiling, not placed)."""
    rm = job.room
    if rm is None or not rm.ceiling:
        return None
    for t in _ceiling_items(job, std):
        if str(t["number"]) == str(number):
            return t
    return None


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


def _front_gap(rm: Room, corner_wall, nominal: int, depth: int,
               std: Standard = STANDARD) -> int:
    """A gap that meets a corner, measured at the front of the run `depth` out
    from the wall face: `nominal` at the wall face, widened or narrowed by how
    the return wall runs away from the corner, at its real interior angle
    (`corner_angle` of the wall whose corner it is). At 90 that is exactly the
    nominal; a corner a few degrees open gives the taper a filler is scribed
    to; a splayed 135 shows the gap it really leaves at the front. At an
    outside corner, or walls in line, no return wall stands in front of the
    run at all: the gap is what it is at the wall, and the run simply ends at
    the corner (ruling 5). `corner_wall` None is no corner at all.
    """
    a = None if corner_wall is None else corner_angle_exact(rm, corner_wall, std)
    if a is None or a >= 180 - 1e-9:
        return nominal
    real = math.radians(a)
    return nominal - round(depth * math.cos(real) / math.sin(real))


def _corner_walls(rm: Room, wall_id: str, std: Standard = STANDARD):
    """(the wall whose corner-after is this wall's START corner, this wall where
    a wall meets its END) — None at either where the run just stops."""
    return (prev_wall(rm, wall_id, std),
            wall_id if next_wall(rm, wall_id, std) is not None else None)


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
            g = geometry(cab, std)
            # the cabinet's reach along the wall includes an attached panel
            # level with its carcass (spec B6: footprint) — an end panel closes
            # the gap to the wall by its own thickness
            x0, x1 = attached_extent(job, cab, p, g, std)
            runs.setdefault((p.wall, run_key(lay)), []).append((x0, cab, g, x1))
    for cab, p, lay in placed(job):
        shadow = corner_shadow(rm, cab, p, std)
        if shadow is None:
            continue
        next_id, at, width, depth = shadow
        runs.setdefault((next_id, run_key(lay)), []).append(
            (at, cab, _shadow_geometry(cab, width, depth, std), at + width))

    out: List[Gap] = []
    for (wall_id, lay), items in sorted(runs.items()):
        items.sort(key=lambda t: t[0])
        w = _wall(rm, wall_id)
        before_corner, after_corner = _corner_walls(rm, wall_id, std)
        geoms = {c.number: g for _, c, g, _e in items}

        edges = []
        first_x, first_cab, _, _ = items[0]
        if first_x > 0:
            edges.append((None, first_cab, 0, first_x, before_corner))
        for (x0, c0, g0, end0), (x1, c1, _g1, _e1) in zip(items, items[1:]):
            if x1 > end0:
                edges.append((c0, c1, end0, x1 - end0, None))
        last_x, last_cab, last_g, end = items[-1]
        if w.length > end:
            edges.append((last_cab, None, end, w.length - end, after_corner))

        for left, right, x, nominal, corner in edges:
            bounds = [c for c in (left, right) if c is not None]
            depth = max(geoms[c.number].depth for c in bounds)
            height = max(geoms[c.number].height for c in bounds)
            front = _front_gap(rm, corner, nominal, depth, std)
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
