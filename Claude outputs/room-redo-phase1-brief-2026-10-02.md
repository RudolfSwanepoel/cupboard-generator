# Brief — Room redo, Phase 1 of 4: walls become positioned segments

2 October 2026. From Cowork, agreed with Rudolf the same day. Background and
the survey of how comparable tools do this: `Claude outputs/room-redo-research-2026-10-02.md`
(also in the project as `claude/room-redo-research-2026-10-02.md`).

## Why

Rudolf's verdict on the Room tab: "terrible". Every complaint traces to one
design decision — **a wall has no position of its own**. A room is a chain;
each wall is a length and a corner angle, and the app walks the chain from the
first wall along +X to find where anything is. That is why a wall can only be
added at either end of the chain (and "+ Wall before A" re-origins the room),
why a single wall draws nothing (`plan_svg` needs two walls to find a shape),
why Draw walls has to REPLACE the room instead of adding to it, why a wall
cannot stand in the middle of a room or meet another wall part-way, and why
"which side is the room" is a consequence of walking order rather than
something you can see and point at. Every comparable tool (Sweet Home 3D,
Floorplanner, Chief Architect, Cabinet Vision, KCD, blueprint3d) stores walls
as positioned segments and derives the rest.

## The four phases (this brief is Phase 1 — build nothing from 2 to 4)

1. **The model and the Walls UI** — this brief: walls as segments with end
   points, the chain and corners DERIVED, migration of every job and fixture,
   wall height, lettering fixed for life plus Renumber, a one-wall room that
   draws, the room side shown and flippable per wall, Draw walls that ADDS,
   the Room tab re-laid out around one canvas and one dock.
2. **Drawing** — the integrated draw mode: typed lengths while drawing, join
   on an existing corner, a wall drawn onto a wall splits it (T-walls, nooks),
   drag a corner to reshape, drag a wall to move it parallel, a Nook tool.
3. **Openings and obstructions** — a palette (Door, Window, Arch,
   Obstruction) dragged onto a wall, edited in the dock and by drag in plan
   and elevation, a room door's swing into a cabinet as a WARNING.
4. **Free cabinets** — a placement either on a wall or free (position +
   angle), detach by pulling off the wall, magnet back on, rotate by handle in
   15° steps / R for 90° / typed, free-to-free snaps for islands.

Island as a cupboard Kind (finished back, plinth all round, free by default)
and the shelves / doors / defaults round come between the room phases and
Phase 4 — not in this brief.

## Rulings (2 Oct 2026) — build to these, don't reopen them

1. **Walls are positioned segments.** `Wall` stores `x0, y0, x1, y1` — its two
   end points in room millimetres, **integers, no decimals**. Length,
   direction, the corner angles, the walk order and whether the room is closed
   are all DERIVED. Nothing else stores a wall position.
2. **The room is on the RIGHT of x0→x1** — the drawn line is the inside face,
   exactly the convention the cabinet-trade tools use and the one the app has
   always had (walls clockwise). The thickness band is drawn on the LEFT (the
   back). **Flip face** on a wall swaps x0/x1 and re-measures its openings and
   obstructions from the other end, as `flip_side` does today per wall.
3. **One face per wall.** A partition that takes cabinets on both sides is two
   walls back to back ("Add back face", Phase 2). Every engine rule stays
   single-sided.
4. **Thickness is drawing only.** `Wall.thickness`, default `Standard.wall_thickness`
   110, written only when not the default. It moves no check in this phase.
5. **Wall height.** `Wall.height`, None = the room ceiling, written only when
   set. Drawn at that height in the elevation and in 3D. An opening whose head
   is above the wall's height is a CRITICAL (`opening-height`); a cabinet
   reaching above a wall lower than the ceiling is a WARNING (`above-wall`) —
   a tall unit can stand against a half wall.
6. **Letters are for life.** A wall keeps its letter whatever is drawn, added
   or deleted; a new wall takes the first unused letter (after Z, AA). The
   Walls table lists walls in **walk order**, free walls after. **Renumber**
   re-letters A, B, C… along the walk and updates every placement, gap and
   plinth that names a wall — a deliberate act, like Re-enter, behind a confirm
   that lists the changes. Nothing re-letters on its own.
7. **Offsets are an input method, not a stored fact.** `offset_start`,
   `offset_end` and `corner_end` are READ for migration and never written
   again. The Wall card shows each corner's actual interior angle (derived,
   0.1°) and, when that angle is within 10° of 90, 180 or 270, an
   **out-of-square** figure beside it: the deviation at `Room.offset_depth`
   (600) in mm — the way a site is measured. Typing either writes the angle;
   the angle moves the end point. The open item on the `offset_depth` default
   and sign stays open.
8. **Byte-for-byte round trip is broken ONCE, deliberately, for jobs with a
   room.** Loading migrates the chain to points; saving writes points. Load →
   save → load must then be stable (idempotent, pinned). Every fixture with a
   room is re-saved in the new form in the same commit. Jobs with no room —
   the benchmark included — do not change by a byte.
9. **Migration within 1 mm.** Every fixture room's `wall_frames` after
   migration is within 1 mm of what the chain gave (exact where every corner
   is 90 and every length an integer). Angled fixture rooms may shift gaps by
   under a millimetre; the checks that pinned those figures are re-pinned.
10. **Units on screen.** Every length field and column says mm; angles say °.
11. **The spec's "a cabinet drags along its wall only" (ROOM-LAYOUT-SPEC
    265–267) and the 21 Sept 2026 deferral of islands are OVERRULED** — for
    Phase 4. In this phase cabinets still drag along their wall exactly as
    they do now.

## Part 1 — the model (`cabinetgen/model.py`, `room.py`, `store.py`)

- `Wall`: `id, x0, y0, x1, y1, height=None, thickness=None, drawn=False,
  openings, obstructions`. Drop `length`, `offset_start`, `offset_end`,
  `corner_end` from the dataclass; `store.wall_from_dict` accepts the old keys
  and migrates (below). `Room`: drop `closed` (derived); keep `name`,
  `ceiling`, `offset_depth`.
- **Derived, in `room.py`, one function each:** `wall_length(w)` (whole mm),
  `wall_dir(w)` (unit vector), `wall_normal(w)` (into the room: the right-hand
  normal), `wall_frames(rm)` — the SAME return shape as today, read off the
  points, so everything downstream that takes (start, dir, normal) is
  untouched; `connections(rm)` — which wall end meets which, by coincident
  end points within `Standard.join_tolerance` (1 mm); `walk_order(rm)` — start
  at the lowest letter, follow end→start connections, then the next unvisited
  letter, free walls last; `is_closed(rm)` — one chain that returns to its
  start; `corner_angle(rm, i)` — the interior angle at the corner AFTER wall i
  in the walk, from the two directions, or None when no wall meets there;
  `corner_points`, `closure_error` (the miss between the last wall's end and
  the first wall's start of a chain that nearly closes — within
  `closure_block` — otherwise the chain is open and nothing is said),
  `crossing_walls` — two segments crossing, NOT touching at an end point and
  NOT an end point lying on the other wall (a T-wall is legal geometry now).
- **Migration** (`store.wall_from_dict` / `room_from_dict`): a room whose walls
  carry `length` and no `x0` is run through the OLD chain arithmetic (keep it
  as `room._legacy_frames`, used by nothing else) to produce the points,
  rounded to whole mm. `drawn` carries over. The room is then exactly the room
  it was, translated nowhere: wall A still starts at (0,0) along +X.
- **Editing by typed number** (`/api/wall-set`): a typed length moves the end
  point along the direction and TRANSLATES every wall after it in the walk by
  the same vector (the chain follows, as it does today). A typed corner angle
  rotates the walls after the corner about it. Both server-side, whole mm. A
  closed room whose last wall then misses the first by more than
  `closure_block` is reported as now.
- **`add_wall(rm, after=id | before=id, length)`**: appends a wall at 90°
  (interior) off that wall's end or start, next free letter. Neither
  re-origins anything. `walls_from_points` (Draw walls) ADDS the drawn walls
  to `rm.walls` — no replacing, no re-orienting to +X (the points are
  absolute); a drawn first point within `snap_tolerance` of an existing wall
  end joins there.
- **Flip face**: `flip_face(job, wall_id)` — swap the end points; openings and
  obstructions re-measured `L − x − width` / `L − x`; placements on it
  re-measured the same way (`L − x − reach`), a corner unit's hand swapped,
  gap and plinth records on it swapped end for end, exactly as `flip_side`
  does today for one wall. `flip_side` (whole run) goes; its check becomes
  flip-face-twice-is-identity.
- **Renumber**: `renumber_walls(job)` — letters along `walk_order`; rewrite
  `Placement.wall`, `GapChoice.wall`, `PlinthChoice.wall`, `Acceptance.where`
  and anything else `grep` finds naming a wall id. Returns the mapping.
- **Delete a wall**: placements on it become UNPLACED (the record removed, the
  item in the unplaced list), its gap and plinth records dropped; the confirm
  names what will happen. Never an orphan `placement-wall` critical from a
  delete. Renaming a wall id by hand is gone (Renumber is the one way).
- **Height**: `wall_height(rm, w)` = `w.height or rm.ceiling`. Read by the
  elevation (the wall rect to that height, the ceiling line dashed above it),
  3D (`wallMesh` to that height), `blocked_openings` / `above_ceiling` are
  unchanged (the ceiling is still the ceiling); new `above_wall` WARNING and
  `opening-height` CRITICAL in `validate._room`.
- **Everything that walked the chain by index** — `_corner_indices`,
  `_beside`, `corner_shadow`, `plinth_butt_wall` / `_plinth_meets`,
  `plinth_open_corners`, `return_profiles`, `return_faces`, `gaps`' next /
  previous wall, `clashes`' wall segments, `scene._room_payload`'s floor
  polygon — reads `connections` / `walk_order` instead. A free wall has no
  neighbour at either end: its run ends there with no corner, no butt, no
  shadow, nothing returned beside it. Audit every `rm.walls[i + 1]` /
  `[i - 1]` / `% len` in the repo; list each in the report.
- `validate._room`: `wall-length` (zero length), `wall-drawn`, unique id,
  `closure` (a chain that nearly closes and misses), `room-self-intersect`,
  `placement-wall`, "sits x–end on wall", `corner-unit-angle`, "not standing
  in a corner" — all re-read off the derived figures; `corner-angle` and the
  corner-disagreement check go (there is nothing to disagree any more).

## Part 2 — the Room tab, re-laid out

One canvas, one dock, the toolbar the next phases fill:

- **Left, a slim toolbar**: Select (default) · Draw walls. (Phase 3 adds
  Door · Window · Arch · Obstruction; Phase 2 adds Nook.) Esc returns to
  Select.
- **Centre, the plan**, full height of the viewport, the zoom controls and
  layer chips in its header as now. Click a wall to select it (a fat
  invisible hit line like a panel's `PANEL_GRAB`); click a cabinet to select
  it as now; click empty canvas to select the room.
- **Right, the dock shows what is selected**:
  - nothing / the room → the **Room card**: name, ceiling (mm), offset depth
    (mm), **Draw walls**, **Renumber**, **Remove room**, and the **Walls
    table** in walk order — Wall · Length (mm) · Corner after (°) · Height
    (mm) · Face (Flip) · Openings · Obstructions · × — a row click selects
    that wall in the plan.
  - a wall → the **Wall card**: letter, length (mm), the corner before and
    after it (° and the out-of-square mm at 600 when near square), height
    (mm, blank = ceiling n), thickness (mm), Flip face, "+ Wall after" / "+
    Wall before", Delete. Its openings and obstructions listed read-only
    ("edit in Phase 3").
  - a cabinet or panel → the editor, exactly as now.
- **Below the plan**: Gaps and Plinth cards as they are; the Placements card
  as it is (it is a typed way to place; Phase 4 revisits it).
- **The room side is SHOWN.** A closed room's floor is tinted; on an open run
  or a free wall a 300 mm band on the face side is tinted, fading out. The
  thickness band is drawn on the back side, hatched, at `thickness`. The
  paragraph of help text under the Walls card goes; one line stays: "The line
  is the inside face; the room is the tinted side. Flip face turns it round."
- **A one-wall room draws.** `plan_svg` takes its bounds off the walls and the
  footprints, one wall or many; the elevation, gaps, runs and 3D already cope
  with an open run of one wall — prove it.
- **Draw walls** stays as built (the grid canvas, 15° / 10 mm snaps, click
  the start to close, Enter, Esc, Backspace) with three changes: it ADDS to
  the room, it starts from an existing corner when clicked near one, and
  there is no "Replace walls" confirm and no re-orientation. The full draw
  mode is Phase 2.
- Where every moved function lives now goes into CLAUDE.md's checklist (hard
  rule 9): Walls card → Room card + Wall card; "+ Wall before / after" → the
  Wall card; Flip side → Flip face per wall; the Corner column → the Wall
  card's corner before / after; `Room.closed` → derived; offsets → the
  out-of-square field.

## Part 3 — API

`/api/wall-set` (length / angle / height / thickness / drawn), `/api/wall-add`,
`/api/wall-delete`, `/api/wall-flip`, `/api/room-renumber`, `/api/room-draw`
(adds), `/api/room-new` (the 4000 × 3000 pre-fill, four walls, as now).
`/api/room-extend` and `/api/room-flip` go. `_room_info` on `/api/compute`
carries, per wall, the points, length, height, the corner before and after
(angle, out-of-square, the wall met) and `free` (no connection at either end);
plus `closed`, `walk`, `closure_error`, `crossing`. The browser works out no
geometry (the rule stands: if the UI needs a number, add it to `cabinetgen`).

## Checks

- `check_room.py`: rewrite `angles()` as `migration()` — every fixture room
  (all-90, the L with 270, hexagon, splay, bay, open runs) migrates within
  1 mm, exact where it should be, and load → save → load is stable; `walk()`
  — walk order on a closed room, an L, two chains, a free wall;
  `renumber()` — mapping applied to every record type; `flip_face()` twice
  is identity, and one flip re-measures openings, placements, gaps, plinths;
  `height()` — the two new issues; `single_wall()` — plan, elevation, gaps,
  runs, 3D payload on a one-wall room; `touching()` — a T-wall is not a
  crossing, a real crossing still is; `delete()` — placements unplaced, no
  orphan.
- `check_drag.py`, `check_elevation.py`, `check_plinth.py`, `check_fillers.py`,
  `check_scene.py`, `check_accept.py`: re-run; every room fixture they build
  by hand (`rectangular(...)`, `Wall(...)` literals) is built with points.
  Where a figure moves by the sub-millimetre migration, re-pin it and say so.
- `tools/ui_check_walls.py`: re-pointed to the toolbar, the Room card and the
  Wall card; stages `draw` (adds to the room, starts on a corner), `one`
  (a one-wall room draws), `flip`, `renumber`, `height`, `input`, `drag`
  (a cabinet onto a 45° wall, unchanged), `3d`. `ui_check_restructure.py`'s
  Room stages re-pointed.
- `check_all` 23 of 23 (or more); benchmark 272 / 59 / 30, 92 pot holes,
  18 / 9 / 6, R28,363.50 — quote it; `snapshot.py --compare` against the tree
  before: the benchmark identical, every room job's drawings allowed to move
  by the migration only, and every panel, issue and total unchanged.

## Docs

CLAUDE.md: a Status entry for this phase, the model section under **The
room** rewritten (points, derived chain, the right-hand rule, Flip face,
Renumber, height, thickness), the layout table, the where-it-lives-now rows.
`docs/ROOM-LAYOUT-SPEC.md`: a **Ruled — 2 Oct 2026** section with the eleven
rulings above and the four phases; strike the "drags along that wall only"
sentence with a note that it is overruled for Phase 4.

## Report back

The audit list from Part 1 (every chain-by-index read and what it became);
which fixture figures moved under the migration and by how much; anything a
free wall or a one-wall room made the engine do that this brief did not
foresee; and the usual benchmark line.
