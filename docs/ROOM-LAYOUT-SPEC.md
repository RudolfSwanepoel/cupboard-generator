# Room layout, plan view and 3D — build spec

Status: scope agreed 13 Sept 2026; scribe/filler numbers ruled 14 Sept 2026;
plinth numbers ruled 14 Sept 2026. Phase 1 and Phase 2 done, and the filler/
scribe half of Phase 3 is built and clean, regression untouched. Plinth
generation is the remaining piece of Phase 3. Remaining open items are
listed at the end.

## Purpose

Give the app a room. Today `Job.cabinets` is a flat list drawn side by side in
list order; nothing knows where a cabinet actually sits. Once cabinets have a
wall and a position, four things follow that cannot be done now:

- fillers and scribes calculated instead of hand-patched (the current known gap)
- corner clashes, door swings and drawer pull-out clearance checked
- out-of-square walls absorbed into the cut list instead of corrected on site
- real XYZ per panel, which is what a SolidWorks assembly needs

## The rule that governs scope

The room model exists to serve the cut list. Room geometry is entered only
where it changes a panel size or raises a clash. The moment this becomes a
general drawing program it stalls. No furniture, no finishes, no lighting.

## Decisions already taken

| Question | Decision |
|---|---|
| Coverage | Kitchens and wardrobes both |
| Placement | Drag to place in plan |
| Walls | Measured out-of-square supported |
| 3D | Full orbit and zoom |
| Site measuring | Wall lengths plus offsets at each end |
| Plinth | Adjustable legs plus a clip-on front, and plinth is optional per run |

## Backwards compatibility — non-negotiable

`Job.room = None` must behave exactly as today: cabinets drawn side by side in
list order, same panels, same nest, same cost. `tools/regen_check.py` must
still report 22 clean cabinets, 272 / 59 / 30 panels, 92 pot holes,
18 / 9 / 6 boards, cost within R41. The October 2025 fixture gains a room only
after the geometry is proven, and adding it must not move a single panel size.

## Data model — additions to `cabinetgen/model.py`

```python
@dataclass
class Opening:
    kind: str          # 'door' | 'window' | 'arch'
    x: int             # mm from wall start to the opening's left edge
    width: int
    sill: int = 0      # mm from floor
    head: int = 2100

@dataclass
class Obstruction:
    kind: str          # 'plug' | 'isolator' | 'waste' | 'water' | 'pipe' | 'meter'
    x: int
    z: int             # mm from floor to its centre
    width: int = 100
    height: int = 100
    proud: int = 0     # mm it stands off the wall face

@dataclass
class Wall:
    id: str            # 'A', 'B', 'C' ... clockwise
    length: int        # measured tight against the wall
    offset_start: int = 0   # deviation from square at the start corner
    offset_end: int = 0     # deviation from square at the end corner
    openings: List[Opening] = field(default_factory=list)
    obstructions: List[Obstruction] = field(default_factory=list)
    corner_end: float = 90  # nominal interior angle of the corner after it (29 Sept 2026)
    drawn: bool = False     # length drawn with the mouse, not yet measured (29 Sept 2026)

@dataclass
class Room:
    name: str
    ceiling: int = 2700
    offset_depth: int = 600   # depth at which the offsets were measured
    closed: bool = True       # walls form a loop
    walls: List[Wall] = field(default_factory=list)

@dataclass
class Placement:
    cabinet: int       # Cabinet.number
    wall: str          # Wall.id
    x: int             # mm from wall start to the cabinet's left edge, facing the wall
    z: int = 0         # mm from floor to the cabinet's underside
    flip: bool = False # handedness for corner and asymmetric units
```

`Job` gains `room: Optional[Room] = None` and
`placements: List[Placement] = field(default_factory=list)`.

`Cabinet` gains nothing. Layer selection reads the existing
`kind` field ('base' | 'upper' | 'tall') — no new tag.

### Offsets, precisely

For each wall the user enters the length measured against the wall, then at
each end the perpendicular deviation from square, taken `offset_depth` mm out
from the wall face. Zero means square. Positive means the return wall opens
away from the room; negative means it closes in.

The corner angle at each end follows from `atan(offset / offset_depth)`.

**Since 29 September 2026 that is the deviation from a NOMINAL angle, not from
90.** Each corner has a nominal interior angle (`Wall.corner_end`, on the wall
before the corner), and the offsets are the fine correction on top of it,
measured exactly as before. See **Ruled — 29 Sept 2026 (walls at any angle)**.

The app chains the walls around the room and reports the **closure error** in
mm. A room that does not close means the measurements disagree with each other.
Warn above 5 mm, block above 20 mm — a plan built on inconsistent measurements
is worse than no plan.

## The coordinate function

One function, in a new `cabinetgen/room.py`, is the foundation for plan view,
elevations, 3D, DXF and the SolidWorks table:

```python
Room.to_world(wall_id, x, y, z) -> (X, Y, Z)
```

Local axes, standing facing a wall: `x` runs left to right along it, `y` runs
out from the wall face into the room, `z` runs up from the floor.

Nothing downstream is allowed to do its own trigonometry. If a view needs a
coordinate it calls this.

Panel world positions come from a separate function,
`room.panel_placements(job)`, so that `engine.panels_for` and therefore the
cut list stay byte-identical.

## Out-of-square: fillers and scribes

Cabinets stay rectangular and square. The room absorbs the error. Two facts
force this and neither is negotiable:

1. Plazaboard cut on a beam saw. Guillotine only. **A tapered panel cannot be
   ordered.**
2. Therefore every filler is ordered as a rectangle at its widest dimension
   plus a scribe allowance, marked on the cut list as trim on site.

**Ruled 14 Sept 2026, from `Standard`:**

| Constant | Value |
|---|---|
| Scribe allowance | 15 mm |
| Taper threshold (parallel filler vs scribe warning) | 6 mm over the panel's length |
| Filler minimum width (below this, grow a cabinet instead) | 50 mm |
| Filler maximum width (above this, add a cabinet instead) | 150 mm |

### Gap treatment is a per-gap choice, not automatic

Important amendment: **the app must not silently insert a filler at every gap
where a run meets a wall or another run.** Rudolf's own kitchen samples use
three different treatments for a gap depending on the situation:

- a filler (parallel, or scribed if the taper exceeds the threshold)
- a blind corner unit
- deliberately left open (e.g. the wall units in the sample kitchens do not
  run wall-to-wall — the gap is intentional, not an error)

So: the app calculates the gap and **proposes** a treatment (filler if the
width falls between the min and max above; a note to consider a blind corner
or a full cabinet if it's near or past the max; nothing if it's below the
practical minimum), but the treatment on each gap is a field the user sets
per gap, defaulting to "filler" only when nothing else has been chosen. This
generalises the corner-treatment prompt already specified under "Drag
placement" to every gap, not only corners.

Rules to implement:

- A gap's `treatment` lives on the `Placement` data (or a small `Gap` record
  keyed by wall + position) — proposed default `"filler"`, overridable to
  `"blind_corner"`, `"open"`, or `"cabinet"` (grow/add a cabinet, handled by
  editing the layout, not a flag).
- Only gaps with `treatment == "filler"` get a filler panel generated. Width =
  nominal gap + computed taper + scribe allowance (15 mm).
- Where the computed taper over the filler's length exceeds 6 mm, the
  validator warns that a scribe is needed, not a parallel filler, and the
  note on the panel says so.
- Below 50 mm width, the validator suggests growing the neighbouring cabinet
  instead of proposing a filler. Above 150 mm, it suggests a cabinet or a
  blind corner unit instead. Both are suggestions on `treatment`, never a
  block — Rudolf decides per gap.
- Base units: an out-of-plumb back wall affects the worktop scribe, not the
  carcass. Do not adjust carcass depth for it.
- Filler panels must not exceed 2750 mm. Split and note the joint.

## Plinth

**Correction, 14 Sept 2026 — important structural fix.** Every base-family
carcass, kitchen or wardrobe, always stands on adjustable legs. There is no
kitchen/wardrobe distinction and no "floor-standing" case. What's optional is
only whether a **plinth board** clips on across the run to cover the legs —
that choice is the operator's, per run, independent of job type.

**This means `carcass_z` (or whatever replaced it in Phase 4) must add the leg
lift unconditionally for every base cabinet — the plinth boolean must never
gate the z-lift.** It only gates whether a panel-code-10 plinth board is
generated for the cut list. If Phase 4 currently draws an unplinthed run
sitting on the floor (z = 0), that's the bug this correction fixes — check
`room.carcass_z` (or its renamed equivalent) and the clash/ceiling checks that
depend on it, since they were built against the old assumption.

**Ruled 14 Sept 2026, into `Standard`:**

| Constant | Value |
|---|---|
| Plinth height (floor to underside of carcass) | 100 mm |
| Setback behind the door face | 50 mm |
| Leg adjustment range | 98–122 mm |
| Plinth material | same board as the carcass (MEL) |
| Plinth edging | both long edges (top and bottom of the board along its
  length), for water sealing at floor level — not the short end cuts |
| Internal corner treatment | butt joint (one run continues past, the
  other stops square against it) |
| Nominal standing height with no plinth board | 100 mm (same as the plinth
  height — it's the leg setting, not the board, that sets carcass height) |

- The plinth is a **run-level** part, not a cabinet part. It spans continuous
  cabinets on one wall at one `z`.
- Length = the run's plan length along the wall face, less the setback geometry
  at each end.
- A run longer than 2750 mm is split, with the joint placed at a cabinet
  division and noted.
- New panel codes follow the `09` precedent: `10` Plinth (reserved, matches
  `11` Filler/Scribe already built). Both warn on every job with the panel
  present until Plazaboard signs off — flip `Standard.codes_confirmed` once
  confirmed.
- Plinth panels have no owning cabinet. Emit with `cabinet=0` and a run label
  in `note`, alongside the existing `Job.loose` mechanism, same pattern as
  the filler panels already built.

## Layers

Derived from `Cabinet.kind` plus `Placement.z`, with a manual override
available. The plan view toggles Base / Wall / Tall / All. Layers not selected
are **ghosted, not hidden** — you need to see the relationship between an
overhead and what sits under it. Wall units draw as a dashed outline over the
base run, which is the standard kitchen drawing convention.

## Plan view

`render.plan_svg(job, show=(...), ghost=(...))` in the existing `render.py`,
same house style as `elevation_svg`. Since 20 September 2026 the fill is the
board: each footprint is tinted faintly with its exterior board's colour
through `render.board_look`, and base / wall / tall are told apart by the
outline rather than by the fill — tall heavier, wall still dashed. See
**Drawings** in CLAUDE.md.

Draws: wall lines with lengths, openings as breaks in the wall, obstructions as
marked boxes, each cabinet as a rectangle at its true plan position, fillers
hatched, plinth setback as a light line, cabinet number and W x D labelled.
Gaps below the filler minimum are dimensioned in red.

## Drag placement

Interaction rules, in order of how much grief each one saves:

- ~~A cabinet belongs to a wall and drags **along that wall only**. Free 2D
  dragging is what makes these interfaces unusable.~~ **Overruled 2 October
  2026 for Phase 4 of the room redo** (free cabinets: a placement on a wall
  OR free, detach by pulling off the wall, magnet back on, rotate). In Phase
  1 a cabinet still drags along its wall exactly as before; dragging it near
  a different wall re-parents it to that wall.
- Snap to the wall face, to neighbouring cabinet edges, and to opening edges.
- Overlapping cabinets render red and raise a critical on export.
- A gap below the filler minimum shows its dimension and warns.
- Every gap (corner or straight run against a wall) gets a proposed
  treatment — filler, blind corner unit, or deliberately open — which the
  user can accept or override. See "Gap treatment is a per-gap choice" above.
- Door swing and drawer pull-out drawn on hover, checked against the adjacent
  wall, the return run, and the opposite run.
- Wall units drag in the same plan view, but only while the wall layer is
  active. Their height off floor is set in the elevation view, not the plan.

Everything the drag produces is a `Placement`. The browser computes no
dimension — it posts the placement and the server returns the geometry, same
discipline as `/api/compute` today.

## Per-wall elevations

`render.elevation_svg` generalises to `render.wall_elevation_svg(job, wall_id)`:
the cabinets on that wall, at their true positions and heights, with the wall
outline, openings and obstructions behind them. With `room=None` it falls back
to today's side-by-side drawing unchanged.

This is where the existing "no dimension lines, no hardware positions" gap gets
closed, because now there is a datum to dimension from.

## 3D view — Part F, built 23 September 2026

three.js 0.186.0 and camera-controls 3.1.2, **vendored under `app/vendor/`**
with their licences and served by the app itself — no CDN; the tab opens with
the network off. An import map in `index.html` points at the local files; the
3D code is its own module, `app/view3d.js`, imported the first time the tab is
opened, so start-up is untouched.

**The scene is built on the server and only drawn in the browser.**
`cabinetgen/scene.py` composes what `room.py` already answers —
`solid_parts`, the placement frame, `carcass_z`, `door_hinges`, the envelopes,
the chosen plinths and fillers — into world-space solids with their cut-list
designations, and `/api/scene` hands it over. The panels drawn are the real
ones: sides, top, bottom, fronts, the backing board, a blind corner's flush
panel, a mitre's construction, independent panels, plus the chosen plinth
boards and fillers. **Not drawn, by ruling:** shelves, supports, drawer boxes,
legs, hardware, handles, worktops — their positions are not modelled and
nothing is guessed onto a drawing; the legend says so.

- Room shell: floor and single-sided walls facing into the room, so the wall
  between the camera and the room is not drawn; openings as holes;
  obstructions never hidden.
- Doors turn about their hinge axes by the angle the server sends, drawer
  faces slide out by the runner's length; Clearances shows the swing and
  pull-out envelopes, red where `room.clashes` reports a clash.
- Orbit about the pressed point, pan at its depth, zoom about the point under
  the cursor; a view cube, named views, `1`-`9` face on to a wall in
  orthographic.
- **Click a part to see its label, size and cut-list line** — the part card,
  with Show in cut list landing on that row. This is the point that matters
  most for bespoke work: a panel cannot be admired in 3D and wrong on the list.
- One editor across Cabinets, Room and 3D (the same `#editor`, docked and
  moved, never copied); a click in any drawing selects without isolating.
- A selected item is moved on handles along its wall, up, and (a panel) out
  from the wall, through the same `/api/drag` and snaps as the plan.

**One correction to the frame as this spec had it.** World X right, Y into the
room, Z up, with the plan mapping onto SVG with no flip, is a left-handed
frame. A right-handed renderer draws it mirrored, hinge sides included, so the
3D view draws everything under a root that negates Y (`toRender` / `toRoom`
in `view3d.js`). `room.py` is unchanged; the plan and the elevations are
unchanged; only the 3D view's mapping onto the screen is the mirror the
drawings always implied.

## Independent panels — Part D, built 20 September 2026

A panel is a part that is cut, numbered, costed and nested on its own and
belongs to no carcass. Several make a bulkhead — a front, an underside and an
end cap each side — each its own numbered item.

**Model.** A `Cabinet` with `kind="panel"` carrying a `PanelSpec`: a board, an
orientation, two finished extents `a` and `b`, which extent the grain runs
along, an edging kind and colour board, and how many long and short edges are
banded. `template` is NOT used to say panel and is never rewritten when a kind
changes — there would be nothing to restore it from, and October cabinets 3 and
5 are `template="standard"` carrying hand-specified extras. `PanelSpec.anchor`
is reserved and nothing reads it: a panel stays where it is put.

**Geometry.** `room.panel_geometry`, reached through `room.geometry(cab, std,
materials)` with `source="panel"`. The third extent is always the board's own
thickness, which is why a panel never states one and why geometry needs the
job's materials for a panel and for nothing else:

| Orientation | along the wall | out from the wall | up |
|---|---|---|---|
| `upright` — facing the room | a | thickness | b |
| `flat` — horizontal | a | b | thickness |
| `end` — upright, side-on | thickness | a | b |

**Cut list.** `engine.panel_of` derives the line; nothing about it is typed.
Code 08 with the role "Panel" (`model.PANEL_CODE`) — Plazaboard's CSV writes the
Component column from `Panel.label` alone, so a new code would need their
sign-off and would say nothing on the order that 08 does not. qty is always 1;
identical panels are Duplicates, each with its own number.

`Length` IS the grain direction, so on a grained board the extent the grain runs
along becomes the length whether it is the longer of the two or not, and the
panel locks; a plain board takes the longer extent and stays free to turn. Which
means the operator's **long and short edges are not `edge_l` and `edge_w`** — a
panel cut across its grain has its long edges running the width — so the two are
mapped rather than assumed equal.

**Editor.** *Size → Kind → Panel* swaps the cupboard sections for a single
**Panel design** section: the board (any thickness — a panel is one board, not a
carcass), the orientation as three radio options with inline-SVG icons and plain
labels, the two extents labelled per orientation, *Grain runs along* on a grained
board only, the edging (kind, colour board, long and short counts) filtered by
what the Boards record offers, and a one-line preview of the cut-list line that
is `panel_of`'s own answer read back. Turning a configured cupboard into a panel
confirms first and names what stops being cut; nothing is emptied either way, so
picking a cupboard kind again brings it all back. The cabinet table shows a
panel's geometry figures, not its declared ones.

**What a panel takes no part in, and this is the load-bearing half.**
`room.placed` skips panels explicitly, so gaps, runs, plinth, tip-up, door
swings and overlaps are exactly what they were. A panel stands on no legs, so
`carcass_z` is its own z. It is not in the Run drawing — which is also what
keeps `wall_elevation_svg` with no room equal to `elevation_svg` — nor in the
edging legend, nor in the structure, door, drawer, support or carcass-thickness
checks.

**Placement — Part E, built 21 September 2026.** A panel is in the Placements
table with a Y column of its own, is drawn in the wall elevation and the plan,
and is dragged and snapped by the same pipeline as a cabinet. An unplaced panel
is still deliberately not a warning: a panel cut and not put anywhere is normal.

`Placement.y` is out from the wall face to the panel's back — 0 flush, and what
puts a bulkhead underside out over the units below it. It is serialised **only
when non-zero**, so cabinet placements written before it round-trip byte for
byte, and a cabinet is never given one: the table's Y cell is not offered on a
cabinet row.

`room.placed_panels(job)` is the panel-only twin of `placed()`, which stays
cabinet-only — that separation is the load-bearing half above, and keeping two
lists is what preserves it. `room._on_wall` reads the two together, and only
for the question of what something comes to rest against: `snap_points` and
`z_snap_points` offer wall ends, the floor, the ceiling, opening edges, other
panels and **cabinet tops**, which is what a bulkhead front lands on.

`room.panel_clashes` is a WARNING and never a critical: a panel is cut and
costed wherever it is, and a bulkhead front is meant to sit flush on the run.
Touching is clear, so a flush bulkhead raises nothing.

`room.free_x` puts a newly-placed cabinet or panel clear of what is already on
that wall instead of at 0 mm, off the same candidates a drag reads.

`tools/fixtures/Test_Panels.json` is the cut-only fixture (in `jobs/` until 28 September 2026); `tools/check_panels.py` is the
check, and it builds its own placed bulkhead in memory rather than reading a job
file — a check never reads live workshop data to pin a fact.

## Phasing

Each phase ends with `regen_check.py` and `check_examples.py` clean.

1. **Room model and geometry.** — **done**
2. **Plan view, read-only.** — **done**
3. **Fillers, scribes and plinth.** — **done**, including the legs-vs-plinth
   correction (every base-family carcass — base and tall units, kitchen or
   wardrobe — always gets the 100 mm leg lift; the plinth board is a
   separate, optional, operator-level choice).
4. **Drag placement.** — **done.** Collision, gaps, corner detection, door
   swings, ceiling-clash check, unmeasured-wall block. All checks clean,
   October regression byte-identical (272/59/30 panels, 92 pot holes,
   R28,363.50), roomless elevation fingerprint unchanged.
5. **Per-wall elevations,** dimensioned. — **done**, in the same render.py
   work as Phase 4.
5a. **Independent panels, cut only.** — **done** (Part D, 20 September 2026):
   the model, the engine, the geometry, the editor and the validation. A panel
   is cut, costed and nested and is not yet placed.
5b. **Placing panels.** — **done** (Part E, 21 September 2026): `Placement.y`
   (serialised only when non-zero), `room.placed_panels`, the Placements table's
   Y column, panels drawn in the wall elevation and the plan, the drag through
   the one existing pipeline, the snap targets including cabinet tops, the 16 px
   hit area a 16 mm panel needs to be grabbable, the Panels layer toggle and the
   clash warning. October regression byte-identical throughout (272/59/30
   panels, 92 pot holes, 18/9/6 boards, R28,363.50).

   **Three things beyond the brief, decided with Rudolf on 21 September 2026:**
   the plan's layer toggle is **multi-select** rather than one radio (Base, Wall,
   Tall and Panels each on and off on their own, all four on by default,
   everything not shown ghosted rather than hidden — the existing rule applied to
   the new toggle); a newly-placed cabinet or panel gets a **default position
   clear of what is already on that wall** (`room.free_x`, server-side, off the
   drag's own candidates); and the wall elevation and the plan take
   **scroll-wheel zoom** with a `100%` reset, done by scaling the SVG element's
   CSS size and leaving the viewBox alone, so every pointer-to-millimetre
   conversion stays exact at any zoom level.

   **Not built and not asked for:** dragging a panel in the plan (typed entry is
   what ships, and the plan's panel footprints take no pointer events so they
   cannot swallow a cabinet drag), and `PanelSpec.anchor`, which still nothing
   reads.
6. **3D.** — **done** (Part F, 23 September 2026): see **3D view** above and
   CLAUDE.md → **The 3D view**.
7. **CAD export** riding on the same coordinates — DXF plus the SolidWorks
   parameter table already on the not-built-yet list.

Phase 3 before phase 4 was deliberate. A drag interface that produces a wrong
cut list is worse than a form that produces a right one.

## Ruled — 14 Sept 2026 (fillers, scribes, plinth)

1. **Scribe allowance:** 15 mm.
2. **Taper threshold:** 6 mm, measured across the cabinet's depth (front to
   back) as `depth × tan(corner deviation)` — this is what an out-of-square
   corner actually produces in plan. Out-of-plumb walls (a vertical lean)
   would need a separate spirit-level reading per wall, which the current
   site-measuring method doesn't collect, so it's out of scope until it does.
3. **Filler minimum / maximum width:** 50 mm / 150 mm. See also the gap
   treatment amendment above — these are proposal thresholds, not automatic
   triggers.
4. **Plinth numbers:** height 100 mm, setback 50 mm, leg range 98–122 mm,
   material same as carcass MEL, edging on both long edges (water sealing),
   internal corners butt joint.
5. **Legs vs plinth (correction):** every base carcass stands on adjustable
   legs always. Plinth is only whether a board covers them — an operator
   choice per run, not tied to kitchen vs wardrobe. Nominal standing height
   is 100 mm whether or not a board is fitted.

## Ruled — 14 Sept 2026 (drag placement / Phase 4)

6. **Hinge drawing (plan/elevation only, not a drilling reference):**
   outer hinges 100 mm from each end of the door; on a 4-hinge door the
   middle two divide the remaining length evenly. Rudolf's own confidence in
   this number is low — Plazaboard's own hardware spec likely governs the
   real position. Treat this as good enough for the drawing; do not treat it
   as authoritative for actual drilling, and don't let validation block on
   it.
7. **Ceiling height is now a required site measurement**, not optional with
   a default. The ceiling-clash check can only be trusted once every room
   has a real measured ceiling; a room without one should warn/block same as
   an unmeasured wall does.
8. **Obstruction cut-outs on backing panels: deferred**, same reasoning as
   the sliding-door rule already in CLAUDE.md — don't guess real numbers
   into `Standard`, wait for an actual job with a real pipe position. Keep
   drawing the obstruction in plan; don't generate a cut-out yet.

## Ruled — 14 Sept 2026 (Phase 4 close-out)

9. **New room defaults:** keep the 4000×3000 pre-fill (no need to force
   blank walls). Instead, the room-editing UI must make it easy to add a
   wall onto either end of the sequence — extending a straight run into an
   L or U shape — not just edit the four default walls.
10. **Tip-up clearance for tall units: build it, not deferred.** Confirmed —
   all carcasses (kitchen and wardrobe) are built flat and tipped upright
   as one assembled piece by two or more people, so a ceiling too low to
   complete that tip is a real installation failure, not a hypothetical.
   Don't ask for a guessed clearance margin — derive the exact clearance
   geometrically from the panel's final height, the leg height/pivot point,
   and (if it matters to the geometry) the room depth in front of the wall.
   Show the derivation/formula in the report so it can be sanity-checked
   against real experience, the same way the taper-across-depth formula was
   checked earlier.

## Open items — Rudolf to rule (not blocking current work)

5. **`offset_depth` default.** 600 for kitchens, carcass depth for wardrobes,
   or one number for both? (Phase 1 shipped with the proposed default —
   confirm or override.)
6. **Offset sign convention.** Confirm: positive means the return wall opens
   away from the room. (Also shipped as proposed in Phase 1.)
7. **Panel codes 10 and 11.** Confirm with Plazaboard before they appear on a
   real list. Both currently warn on every job until
   `Standard.codes_confirmed` is flipped.
8. **Kitchen appliances.** Do oven, hob, fridge, dishwasher and sink need to be
   in the room model as objects with clearances, or are they just cabinet
   openings you size by hand?
9. **Worktops.** In scope as a plan object with its own scribe, or out of
   scope because Plazaboard does not cut them?

## Ruled — 14 Sept 2026 (corner units)

11. **Corner units are parametric, not hand-typed coordinates.** A corner
    carcass is described by four measurements and a style. The plan outline
    is *derived* from them — the operator never types an `x,y` list for a
    corner unit, and `Cabinet.footprint` for one is generated, not entered.

    - `arm_a` — how far the box runs along wall A
    - `arm_b` — how far the box runs along wall B
    - `face_a` — the open face on the wall-A side; this is the depth of the
      run that butts onto it
    - `face_b` — the open face on the wall-B side; likewise
    - `corner_style` — `mitre` or `ell`

    Frame: x runs along wall A from the cabinet's start corner, y runs out
    from wall A. Wall A is the face at y = 0; wall B is the face at
    x = `arm_a`.

    `mitre` — one straight front face:

        0,0   arm_a,0   arm_a,arm_b   (arm_a-face_b),arm_b   0,face_a

    `ell` — two front faces meeting at a right angle, leaving the re-entrant
    notch that takes two doors:

        0,0   arm_a,0   arm_a,arm_b   (arm_a-face_b),arm_b
        (arm_a-face_b),face_a   0,face_a

12. **The mitre angle is an output, never an input.** It falls out of the two
    run depths. It is 45° only in the special case
    `arm_a - face_b == arm_b - face_a`. Two runs of different depth — a 600
    kitchen run meeting a 500 one — produce a mitre at whatever angle the
    geometry requires, correctly, with nothing for the operator to specify.
    Do not add an angle field, do not default to 45°, and do not warn when
    the angle is not 45°.

13. **Corner-unit door swing comes off the real face.** Because the front
    face is now known geometry, the swing envelope hinges on the mitre edge
    (or, for `ell`, on whichever of the two front faces carries the door) —
    not on the outline's extreme corners. This closes the approximation
    noted at the Phase 5 close-out.

14. **Cabinet 7 of the October 2025 fixture — measured values.** Derived from
    `Wardrobes/Main Bed Cupboard Assembly Planview.pdf` (vector geometry, not
    scaled off an image) and cross-checked against the cabinet's own cut list:

        arm_a = 850   arm_b = 850   face_a = 500   face_b = 500
        corner_style = mitre

    Outline: `0,0  850,0  850,850  350,850  0,500`
    Mitre legs 350 × 350, so exactly 45°; door face 350√2 = 495 mm.

    Cross-checks, all consistent:
    - `01a` Side 500 × 2 — the two open faces
    - `01c` Side 834 = 850 − 16 and `01b` Side 818 = 850 − 32 — the two wall
      sides, one wrapping the other. This is what fixes the overall at 850
      rather than the 834 a panel-extents fallback produces.
    - `02`/`03` Top and Bottom 818 × 818 — the square blank, mitred on site
    - `07` Door 472 in a 495 opening — 23 mm reveal

    Note: scaling off the declared 850 puts the open faces at 503; scaling
    off a 500 face puts the overall at 844. 0.7% drafting slop either way.
    The intended figures are 850 / 500 / 350, since 850 − 500 = 350 exactly.

15. **Panel-extents fallback stays, but says so.** A bespoke cabinet with no
    outline and no corner parameters still falls back to the rectangle its
    panels make, and still warns. That fallback is 16 mm short on a box whose
    outer side wraps another (see 14) — so it is an approximation, not a
    measurement, and the warning text should say which cabinet is running on
    it.

## Ruled — 17 September 2026 (fronts and the editor)

16. **A tickbox turns a section off; it never throws its values away.**
    "Corner unit" and "Has drawers" are tri-state fields on the `Cabinet`
    (`None` derives the answer from what is stored, which is how every earlier
    job reads). Unticking keeps the drawer stack and the four corner
    measurements in the job file exactly as they were, so ticking it back
    restores the cabinet panel for panel. Clearing the fields instead would
    make the tickbox a destructive control, which is the one thing it must
    not be.

17. **Removing panels is allowed; renaming them is not.** Unticking can take
    lines off the cut list. It is never silent — `/api/what-if` is asked first
    and the designations that would go are named in the confirmation. Nothing
    that survives a change comes back under a different designation, which is
    the 14 September 2026 rule applied to the new controls.

18. **Hinge side is per door leaf, and there is one function that answers.**
    `model.hinge_side` is read by the plan's swing arcs, by the elevation's
    hinge marks and by its clickable door leaves. `Cabinet.door_hinges` holds
    one 'L'/'R' per leaf; blank falls back to the standing rule (a single door
    follows `Placement.flip`, a pair hinges at its outer edges), so nothing
    that predates the control changes. A leaf hangs off its own edge, not the
    carcass end — turning one half of a pair round puts its hinge in the middle
    of the opening, which is where it really is. The swing check re-runs on
    every change because every change goes through `/api/compute`, and the
    envelope comes off `room.geometry(cab)` — for a corner unit, its mitred
    face, never the declared width.

19. **Drawer faces are authored one row per face, Share or Fixed.** Fixed rows
    take their millimetres; the gaps come from `Standard` and are never typed
    per drawer; whatever is left is split among the Share rows in proportion to
    their share numbers. `drawers.divide` does it and the browser shows the
    result — the live millimetres beside each row, the running total and the
    remainder are all the engine's. Fixed rows that over-run the opening leave
    the Share rows at zero, which is a critical and blocks the export rather
    than ordering a negative panel. `Equal` and `Graduated` are presets off
    `Standard.graduated_step`, an authoring aid and not a construction
    dimension. `face_height` is still the ordered figure and still the only one
    the engine reads; `mode` and `share` ride alongside so a stack can be
    re-divided later instead of retyped.

20. **Dragging the join between two faces moves those two and no others.** The
    pair's own span is fixed, so what the top face gains the bottom one loses,
    and both rows become Fixed at the dragged heights. Each face is held back
    far enough to clear its own box side — the existing rule that a box the
    same height as its face shows above the front, not a new number. The
    browser reads the drag back into millimetres from the span the SVG carries
    in both mm and pixels, exactly as a plan drag projects onto a wall track;
    `drawers.split_pair` does the dividing.

## Ruled — 22 Sept 2026 (corner units: mitre, ell, blind)

21. **A corner unit has a TYPE and a HAND, and until it has both it is not one.**
    The type is `mitre`, `ell` or `blind` — `corner_style` gains the third. The
    hand is `corner_hand`, `'L'` or `'R'`, and it says which end of the unit
    stands in the corner **as you face it in the room**.

    Right is the wall's far end: cabinet-local `x = arm_a` lands on the wall's
    length, and the unit turns onto the **next** wall in the chain. Left is the
    wall's start, and it turns onto the **previous** one. That is not a
    convention invented here — wall-local x runs left to right as you face a
    wall, which is already what `model.hinge_side` means by 'L' and 'R'
    (`room.swing_envelopes` hinges 'L' at the low-x end) and what
    `render.wall_elevation_svg` draws. A blank hand reads as R, which is what
    this app did before the field existed, so cabinet 7 and every job written
    before it are unchanged.

    A left-handed unit is the right-handed one mirrored: the outline, the front
    faces, the hinge rule and the shadow all reflect, and **nothing resizes**.
    Its panels are the same panels. `room.corner_shadow` returns `(wall, x,
    width, depth)` now rather than assuming x = 0, because a left-handed unit's
    shadow lands at the far end of the previous wall.

    **Ticking Corner unit with no type chosen is what "the corner unit does
    nothing" actually was.** `corner_on` needs a style, the Style dropdown
    defaulted to blank, and a template cabinet with the box ticked went on cutting
    a straight W × D box with nothing said about it. The editor now shows
    "Choose a corner type" and the validator warns, naming the box it is really
    cutting.

22. **A mitre is ONE construction for tall, base and wall alike.** Melamine top
    AND bottom, two melamine open-face sides, and a melamine back that is the two
    wall panels themselves — one wrapping the other, `arm_a - t` and
    `arm_b - 2t`, exactly as cabinet 7 is built. No 3 mm backing board, no
    groove, no supports (RULES W13).

    So a **base mitre does get a top**, overriding the standing base rule for
    corners only. That top is what braces the box, which is why there is no
    bracing warning to raise. An upper mitre hangs by fixing through its melamine
    wall panels, so it needs no hanging warning either. Straight cabinets are
    untouched by all of it. The wall panels stay coded as **sides**, as cabinet 7
    codes them, and nothing is renamed: `engine.born_distinct` gives 01a / 01b /
    01c at the moment the panels are made.

23. **A mitre door is cut to the INNER SPAN, rounded down, with no gap
    deducted.** The inner span is the line between the two open-face side
    panels' inner front corners — the surface the closed door's inside face
    actually rests on. It is **not** the outline's mitre face: the outline runs
    corner to corner of the carcass, and the blank the top, bottom and shelves
    are cut from is already a board thickness inside it on both edges.

    The door sits *within* that span rather than overlaying the side edges,
    because the sides meet it at an angle and there is nothing there to overlay.
    A pair divides the same span less `door_pair_gap`. Height is `H - 3` as on
    any door, and `Cabinet.corner_door_width` overrides the lot.

    Cabinet 7 is the proof: its inner span is **472.35** and its door, as really
    cut, is **472**. Spec item 14 calls that a "23 mm reveal" against the 495
    outline face — it is not a reveal, it is a different measurement, and 495 is
    not what a door is cut to. The swing check and the arm shelf's door clearance
    both read this same line.

24. **A mitre takes TWO kinds of shelf and may carry both.** `shelves` and
    `fixed_shelves` are not read on one: a mitre's interior is not a rectangle,
    so a straight shelf size would be wrong in the unsafe direction.

    - **Arm shelf** — a rectangle running along one arm, behind the mitre. Its
      length is that arm's internal span (`arm - 2t`); its depth is typed, and
      `room.arm_shelf_max_depth` is the most it may be. Two things bound that and
      the tighter wins: the closed door, which it must stay `mitre_shelf_clear`
      behind, and the concealed hinge's mounting plate on the open-face side
      panel it ends against, which it must stop `hinge_clearance` short of.
      Both measure from `face - t`. The answer is rounded **down** to a multiple
      of `arm_shelf_step`; a depth typed by hand is taken as typed and only has
      to come under it. Over it is a CRITICAL naming the maximum. On cabinet 7
      the maximum is 430, and its own 350 is accepted.
    - **Mitred shelf** — the same square blank as the top and bottom, mitred on
      site, but set back `mitre_shelf_clear` perpendicular from the inner line so
      the door closes on it. On cabinet 7 that is legs of 338 against the top and
      bottom's 334. The panel note carries both legs, because the fitter marks to
      them.

    **Nothing is said or generated about how a shelf is fixed** — that is the
    assembler's choice. Nothing is said about hinges on a mitred shelf either:
    shelf heights are not modelled anywhere in this app, `Standard.hinge_positions`
    stays drawing-only (`check_elevation.py` fails if the engine, the export, the
    nester or the validator reads it), and the assembler places shelves clear of
    the hinges. Shelf heights are a separate piece of work and nothing here is
    built towards them.

    Three new constants, and they are the only figures a mitre needs that its
    four measurements do not give: `mitre_shelf_clear` 3, `hinge_clearance` 50,
    `arm_shelf_step` 5. **No edging thickness is deducted** in working the
    clearance out — this app deducts no tape anywhere, and that holds here.

25. **A blind corner is a straight cupboard, not a shaped one.** A carcass W × H
    × D with a flush panel at the corner end (inside it — see item 29) and **one
    door**, always, at the
    far end. The run on the return wall is ordinary cabinets and is no part of
    this unit.

        opening  O = W - 2t - B
        door     derived from the opening exactly as any other door is,
                 (O + 2t) - door_single_gap = W - B - door_single_gap
        blind    exactly B wide - the board size is the board size - INSIDE the
                 carcass between the top and the bottom, fixed, no pot holes
                 (see item 29 for what it is cut from and how it is edged)

    W 1000, B 500, t 16 → opening 468, door 497, blind panel 500.

    Its plan is a plain rectangle, so it has no derived outline and
    `room.corner_outline` returns None for one **by design** — the validator's
    "parameters do not resolve to a shape" critical skips it. Everything else in
    Structure — back, supports, shelves — is the ordinary engine path, unchanged.
    The blind panel is **code 08 with the role "Blind Panel"** (`model.BLIND_CODE`),
    on the same reasoning as a panel's 08: Plazaboard write the Component column
    from `Panel.label`, so a code of its own would need their sign-off and would
    say nothing on the order that 08 does not.

    It casts a shadow on the return wall like any corner unit, its own depth wide,
    so `gaps` does not offer a filler for the space it is standing in.

26. **A corner unit's door swing that fouls something BLOCKS the export.** This
    is a deliberate exception to the house rule in `validate._room`, which keeps
    an ordinary door-swing foul a WARNING, and ordinary doors stay that way.

    The reason it is different: an ordinary door can be rehung, moved or lived
    with, and which way it hangs is the fitter's judgement. A mitre's door cannot
    — it hangs on the mitre face or nowhere, and its width is derived from the
    arms rather than chosen — so a swing that fouls the runs either side of it is
    a unit that cannot be built as drawn. The message says **the widest door that
    would clear**, found by trying widths against the real swing check rather
    than by a formula, so there is something to do about it. Widening the arms is
    the other way out and the message says so, but it resolves to no single
    figure: bigger arms move the face further into the room and widen the derived
    door at the same time.

    A **blind** unit whose door opening the return run reaches across blocks for
    the same reason and in the same words: the unit exists for exactly that
    clearance, and no amount of fitting will fix it. What reaches is the return
    cabinet's own depth plus its door front, and **no handle clearance** is added
    — if a real job needs one it belongs in Standard, not guessed at.

    Do not tidy either of these back into one rule.

27. **Every dimension a corner unit has is entered in the Corner Unit section,
    and the Size fields are greyed.** Same rule as a panel, whose dimensions all
    live in Panel design, and for the same reason: it must be obvious to somebody
    who has not read the code where a number goes.

    A greyed field shows the **engine's** figure, never the declared one — hard
    rule 1 says declared width, height and depth are labels and no check reads
    them, so echoing a stale declared figure back into a field that looks
    authoritative would be showing the wrong number. Kind, Number and Note stay
    live throughout; Kind because a corner can be top-hung, base or tall.

    The **Outline** is greyed for a mitre and an ell, where `geometry` genuinely
    ignores an entered footprint. It stays live on a **blind** unit, because
    there the footprint IS read like any other cabinet's, and greying a field
    that is still being read would be a lie.

    Nothing is thrown away by any of it: switching the type or the tick back
    brings every value with it, the same bargain the tickboxes strike (item 16).

28. **An ell is shape only, and says so.** Rudolf has never built one and has
    deferred the construction, so the outline, the hand, the plan drawing,
    overlaps, the shadow, the gaps and the face-length readout all work, and the
    engine generates **nothing**. That is a CRITICAL naming what to do about it —
    add bespoke panels in the job file, or change the type — rather than an empty
    cabinet quietly costing R0. An ell with `template="none"` and its own bespoke
    panels works exactly as cabinet 7 does and is untouched by it.

29. **The blind panel sits INSIDE the carcass, and it is selectable.** Ruled
    22 September 2026, replacing the second half of item 25. The cut sizes of the
    door and the opening do not change; the panel's construction does.

    It sits between the corner-end side panel and the opening, with its front
    face flush with the carcass front edges like the sides, the top and the
    bottom, so the unit reads as one flush front. It runs between the top and the
    bottom, so its length is **H − 2t**. A base unit has no top and is the same
    figure: it stands on the bottom and runs up to the underside of the front
    support, which is the same 16 mm board — which is also the figure the engine
    already takes as a divider's default height.

    The door is an ordinary overlay door on the outside, following the same
    overlap rules as every other door: it overlays the far side panel and the
    blind panel's face by `t − door_single_gap / 2` each, which is 14.5 mm.

        blind panel  (H - 2t) x B
        door         W - B - door_single_gap, unchanged
        along the wall, from the far end:
            side t | opening O | blind B | side t          (right-handed)
            door from door_single_gap / 2, W - B - 3 wide

    W 1000, H 2400, D 500, B 500, t 16 → blind panel **2368 × 500**, door
    **2397 × 497**, opening **468**. A base unit at H 790 → blind panel 758 × B.
    `room.blind_spans` is the one place that layout is worked out, and the wall
    elevation and the Corner Unit plan diagram both read it.

    **Board:** `Cabinet.blind_board`, blank meaning the exterior board — the
    default, because the strip visible between the door and the return run is
    seen from the room beside the doors. It is in `Cabinet._board_slots`, so the
    swap, the un-select, the rename and the library scan all see it.

    **Edging: one long edge only**, the vertical edge facing the opening, which
    is the one seen and rubbed when the door is open. Grain runs vertical
    (Length = height), as on a door, so it is `edge_l = 1`, `edge_w = 0`. The
    thickness is `Cabinet.blind_edge_kind`, 1 mm or 2 mm, None meaning the
    doors' — offered separately because reaching into the cupboard rubs against
    that edge. The colour is the panel's **own** board's edging, through the
    existing `tape_for` chain; a kind that board does not offer is the existing
    EDGING critical, and nothing states an edging name anywhere but the Boards
    record (hard rule 6).

    **The return-run clearance check (item 26's blind half) keeps its threshold
    at B.** Moving the panel inside the carcass moved the clear OPENING one board
    further from the corner — it starts at t + B now — but the door did not move:
    its corner-end edge still stands `B + door_single_gap / 2` from the corner.
    A return run reaching between B and B + t clears the opening and still stops
    the door opening, so measuring against the opening would be wrong in the
    unsafe direction.

## Ruled — 29 Sept 2026 (walls at any angle, Draw walls)

Brief `Claude outputs/room-walls-any-angle-brief-2026-09-29.md`, ruled by
Rudolf. Found on Liam_Room: every corner turned the same way (90 inside,
clockwise), so a wall could not turn back out, and a negative length was the
only way to "turn" one — which runs the wall backwards and turns nothing.

**The 22 September hold on outside corners is lifted — for the walls.** Outside
corners and any other angle are in scope for walls. Corner units are not (4).

1. **Corner entry = nominal angle + the existing offsets.** `Wall.corner_end`
   is the interior angle of the corner after the wall, measured inside the
   room between the two wall faces: 90 an inside corner, 270 an outside one
   (chimney breast, step, nib), 135 / 225 a splay in and out, 180 walls in
   line; any value strictly between 0 and 360, decimals allowed. On a closed
   room the last wall's is the corner back to the first; on an open run the
   last wall's is not read. Default 90, written to the job file only when it
   is not 90 (`store.LATE_WALL_FIELDS`), so every room saved before it
   round-trips byte for byte. The offsets are unchanged and still the fine
   correction; the open item on the `offset_depth` default and sign stays
   open. `room.wall_frames` turns by 180 − angle − the measured deviation
   (`room.corner_turn`); at a nominal 90 the turn is `math.pi / 2` itself, so
   a room of 90-degree corners comes out float for float what it always did —
   pinned in `check_room.py` on every fixture room. Nothing downstream does
   its own trig: plan, elevations, 3D and export all read `wall_frames` /
   `to_world`.
2. **Draw walls with the mouse** on Room -> Plan. A **Draw walls** button; in
   draw mode each click sets a corner, and a rubber band shows the length and
   the corner angle it would make. Direction snaps to
   `Standard.draw_angle_step` (15 degrees; Shift for a free angle), length to
   `draw_length_step` (10 mm). Click the first corner to close the room;
   double-click or Enter finishes an open run; Esc cancels the whole drawing;
   Backspace takes the last corner off. The corners (world plan mm — the
   canvas's viewBox is millimetres) go to `/api/room-draw`, and
   `room.walls_from_points` names the walls A, B, C…, rounds each length to
   the mm, works out each corner's angle (to 0.1 degree) and puts the chain
   clockwise: an outline drawn anticlockwise is walked the other way, a closed
   one still starting on the first wall drawn, and nothing is said. The
   room's name, ceiling and offset depth are kept; its walls, and their
   openings and obstructions, are replaced. Drawing over a room with walls
   asks first ("Replace walls A–D?", with how many items are placed and that
   placements keep their wall letter). **Drawn lengths are a sketch**: every
   drawn wall carries `drawn`, is marked in the Walls card, and is a CRITICAL
   (`wall-drawn`: "wall C: drawn, not measured") until its length is typed or
   it is ticked **measured**. The model puts wall A along +X, so a drawn room
   is shown turned that way once it is made. Not built: dragging a corner of
   an existing room to reshape it.
3. **Reference lines, panelling outlines, markup: later.** Nothing built
   towards them.
4. **Corner units (mitre, blind) only at a nominal 90 inside corner.** The
   corner a unit belongs in is the one at its HAND end of its wall
   (`room.unit_corner`). In any other corner: CRITICAL `corner-unit-angle`,
   "Corner unit at a {angle}° corner: construction not ruled.", and
   `corner_shadow` casts no shadow there (so the "not standing in a corner"
   warning is not said as well).
5. **At any corner the run ends**, inside or outside; nothing special is built
   at an outside corner. Overlaps and gaps come from real footprints.

**What learnt about angles** (Part 3 of the brief, audited):

- `plinth_butt_wall`: the 16 mm butt applies at a nominal 90 inside corner
  only (ruled the same evening, replacing "any inside angle"). At any other
  inside angle there is no deduction: each plinth ends where its run ends, and
  where two fitted plinths meet there a WARNING names the corner
  (`plinth-corner`: "Plinth at the B→C 135° corner: the boards don't meet, cut
  a closing piece on site"). At 180 and at an outside corner each plinth ends
  at the corner and nothing is said.
- Gaps: the nominal gap along the wall is unchanged. The width at the FRONT of
  the run (`room._front_gap`) is measured against the real return wall: at a
  nominal 90 exactly as before (the measured deviation alone); at any other
  inside corner by the real angle, so a 100 mm gap at a 135 splay is 680 at
  the front of a 580 run and proposes a cabinet, not a filler; at an outside
  corner or walls in line there is no return wall in front of the run and the
  front is the nominal. Cabinets near an inside corner can clash, and the
  overlap check says so; nothing is auto-resolved.
- The plan drag and a drop from the unplaced list pick the nearest WALL, not
  the nearest wall LINE (`project` in `index.html` measures to the segment):
  in an L a wall's line runs on through the room. The 3D `wallAt` already did.
- Elevations: the neighbours either side are projected off their real plan
  outlines (`return_profiles`, `return_faces`), so a 135 return is seen at its
  angle, and a run behind an outside corner (behind this wall's face) is not
  drawn. No change needed; pinned in `check_room.py`.
- Plan: an obstruction on a wall at an angle is drawn as its box turned with
  the wall (it was the axis-aligned box of its two corners). On a wall along
  an axis the drawing is byte for byte what it was.
- 3D: walls, floor and ceiling (three's `ShapeGeometry`, any simple polygon),
  tiles, plaster and the Grid toggle needed nothing; the contact shadow under
  an item on a wall at an angle is turned with it (it was the axis-aligned
  box). `tools/ui_check_walls.py --stage 3d`.
- Door swing, tip-up, the ceiling, overlaps: geometry already; pinned on an
  angled room in `check_room.py` (a door hinged at a 60 corner fouls the
  return wall, at 90 it grazes, at 135 it is clear).
- New criticals: walls crossing each other in plan (`room-self-intersect`,
  naming the two walls; not asked while a wall has no length), a corner angle
  outside 0-360 in a hand-edited file (`corner-angle`; the chain turns 90
  there meanwhile), a drawn wall (`wall-drawn`), and ruling 4's
  (`corner-unit-angle`).
- A negative wall length is refused at the input in the Walls card, with "to
  turn the other way, set the corner angle to 270"; the `wall-length` critical
  stays for files that carry one.

**The Walls card** gains a **Corner** column — the corner after each wall,
labelled `B→C`, quick picks 90 inside · 270 outside · 135 · 225 · 180 in line ·
custom (a number); a dash on an open run's last wall — and the **drawn** marker
with its **measured** button. "+ Wall before / after" still add walls at 90.
The plan redraws as angles change, as it does for lengths.

**Follow-up rulings, the same evening.** Gap front width at an angled inside
corner: the real angle, as built. Plinth: as above, the butt at 90 only.
Drawn-room lettering and winding: accepted as built.

**Which side is the room on an OPEN run.** The side the run turns towards on
balance — the inside of an L or a U, whichever way round it was clicked
(`room.walls_from_points`; an L clicked left-to-right and right-to-left comes
out the same walls, its cabinets on the room side of both walls — pinned in
`check_room.py` and `ui_check_walls.py --stage side`). A run that does not turn
on balance — one straight wall, a step whose turns cancel — cannot say, and is
taken as drawn: the room on the right hand of the direction drawn. And an L
may be meant round the outside of a nib. So the Walls card offers **Flip
side** on an open run (`room.flip_side`, `/api/room-flip`): the same walls
walked the other way, each keeping its letter; each corner 360 less itself;
offsets swapped end for end and negated; openings, obstructions, cabinets and
placed panels kept where they are along each wall (x from the other end); a
corner unit's hand swapped; a gap decision's two sides swapped; a plinth
decision moved to the cabinet that now starts its run. No cut changes, and
flipping twice gives the job file back exactly. A closed room has no other
side and is refused.

## Ruled — 2 Oct 2026 (room redo, Phase 1: walls become positioned segments)

Brief `Claude outputs/room-redo-phase1-brief-2026-10-02.md`, agreed with
Rudolf; the survey of comparable tools in
`Claude outputs/room-redo-research-2026-10-02.md`. Rudolf's verdict on the
Room tab was "terrible", and every complaint traced to one decision: a wall
had no position of its own. Four phases; this is the first.

1. **The model and the Walls UI** — built: walls as segments with end points,
   the chain and corners derived, migration of every job and fixture, wall
   height, lettering fixed for life plus Renumber, a one-wall room that
   draws, the room side shown and flippable per wall, Draw walls that adds,
   the Room tab re-laid out around one canvas and one dock.
2. **Drawing** — the integrated draw mode: typed lengths while drawing, join
   on an existing corner, a wall drawn onto a wall splits it (T-walls,
   nooks), drag a corner to reshape, drag a wall to move it parallel, a Nook
   tool. **Built 3 October 2026** — see **Ruled — 3 Oct 2026** below.
3. **Openings and obstructions** — a palette (Door, Window, Arch,
   Obstruction) dragged onto a wall, edited in the dock and by drag in plan
   and elevation, a room door's swing into a cabinet as a WARNING. Not built.
4. **Free cabinets** — a placement either on a wall or free (position +
   angle), detach by pulling off the wall, magnet back on, rotate by handle in
   15° steps / R for 90° / typed, free-to-free snaps for islands. Not built.

Island as a cupboard Kind and the shelves / doors / defaults round come
between the room phases and Phase 4.

**The eleven rulings** (build to these; don't reopen them):

1. **Walls are positioned segments.** `Wall` stores `x0, y0, x1, y1`, whole
   mm. Length, direction, the corner angles, the walk order and whether the
   room is closed are DERIVED (`room.connections`, `walk_order`, `is_closed`,
   `corner_angle`, `corner_points`, `closure_error`). Nothing else stores a
   wall position.
2. **The room is on the RIGHT of x0 → x1** — the drawn line is the inside
   face (`wall_normal`, the right-hand normal, `(-dy, dx)` in this frame —
   walls clockwise as the app always had them). The thickness band is drawn
   on the left, the back. **Flip face** (`room.flip_face`, `/api/wall-flip`)
   swaps x0 / x1 and re-measures the wall's openings, obstructions,
   placements (`L − x − width`), a corner unit's hand, its gap and plinth
   decisions from the other end — one wall at a time; `flip_side` is gone.
3. **One face per wall.** A partition taking cabinets on both sides is two
   walls back to back ("Add back face", Phase 2). Every engine rule stays
   single-sided.
4. **Thickness is drawing only.** `Wall.thickness`, default
   `Standard.wall_thickness` 110, written only when set; the hatched band on
   the back of the face line. It moves no check.
5. **Wall height.** `Wall.height`, None = the room ceiling, written only when
   set (`room.wall_height`). The elevation draws the wall to it with the
   ceiling dashed above a lower wall; 3D draws each wall to it. An opening
   whose head is above the wall's height is a CRITICAL (`opening-height`); a
   cabinet reaching above a wall lower than the ceiling is a WARNING
   (`above-wall`) — a tall unit can stand against a half wall.
6. **Letters are for life.** A wall keeps its letter whatever is drawn, added
   or deleted; a new wall takes the first unused letter (after Z, AA). The
   Room card lists walls in walk order, free walls last. **Renumber**
   (`room.renumber_walls`, `/api/room-renumber`) re-letters A, B, C… along
   the walk and rewrites every placement, gap and plinth decision and
   acceptance naming a wall — a deliberate act behind a confirm listing the
   changes. Nothing re-letters on its own.
7. **Offsets are an input method, not a stored fact.** `offset_start`,
   `offset_end` and `corner_end` are read for migration and never written
   again. The Wall card shows each corner's actual interior angle (derived,
   0.1°) and, within `Standard.square_within` (10°) of 90, 180 or 270, an
   **out-of-square** figure: the deviation at `Room.offset_depth` (600) in
   mm, positive opening away from the room. Typing either writes the angle
   (`set_corner` / `set_out_of_square`); the angle moves the end points. The
   open item on the `offset_depth` default and sign stays open.
8. **Byte-for-byte round trip broken ONCE, deliberately, for jobs with a
   room.** Loading migrates the chain to points (`store.room_from_dict`
   through `room._legacy_frames`); saving writes points. Load → save → load
   is stable (pinned). Every fixture with a room was re-saved in the new form
   in the same commit. Jobs with no room — the benchmark included — did not
   change by a byte.
9. **Migration within 1 mm.** Every fixture room's `wall_frames` after
   migration is within 1 mm of what the chain gave — exact where every
   corner is 90 and every length an integer, which is every fixture and job
   on disk, so no pinned figure moved. The angled legacy rooms (the
   parallelogram, the hexagon, the splay, the bay) are migration cases in
   `check_room.py`.
10. **Units on screen.** Every length field and column says mm; angles say °.
11. **The spec's "a cabinet drags along its wall only" (above) and the 21
    Sept 2026 deferral of islands are OVERRULED** — for Phase 4. In this
    phase cabinets still drag along their wall exactly as they do now.

**Built beyond the rulings, as the brief asked:** `closure_error` is a near
miss within `closure_block` only — a chain missing by more is an open run and
nothing is said; a typed length or angle on a closed room therefore opens the
loop by the difference, the toast says so, and the Room card reads "open
run". A typed corner on a closed loop turns every other wall round the loop,
so the last corner of the walk can be typed too. `crossing_walls` names
proper crossings only — a T-wall, and an end point lying on another wall,
are legal. `/api/wall-set`, `wall-add` (off a free end only), `wall-delete`
(with an `ask` step naming what becomes unplaced), `wall-flip`,
`room-renumber` (a dry run for the confirm) and `room-draw` (adds; a first
point within `snap_tolerance` of an existing corner joins it) are the API;
`/api/room-extend` and `/api/room-flip` are gone. The room side is SHOWN in
the plan: a closed room's floor tinted, an open run's or a free wall's face
side a 300 mm band fading out (`render.ROOM_TINT`, `ROOM_BAND_MM`).


## Ruled — 3 Oct 2026 (room redo, Phase 2: drawing and editing walls on the plan)

Brief `Claude outputs/room-redo-phase2-brief-2026-10-03.md`, agreed with
Rudolf the same day (rulings 10 and 11 added after he tested Phase 1).
Nothing from Phase 3 (openings) or Phase 4 (free cabinets) is built. One
commit per ruling group: 1-2, 10-11, 3-4, 5, 6, 7-9; `check_all` green at
each, the benchmark unchanged (272 / 59 / 30, 92 pot holes, 18 / 9 / 6,
R28,363.50), `snapshot.py --compare` against the tree before: every panel,
issue and total identical on every job — only Test.json's plan SVG moved
(the plan now carries its mm mapping and its labels' wall ids).

**The eleven rulings** (build to these; don't reopen them):

1. **A typed length or angle on a closed room leaves the loop OPEN by the
   miss.** It is the closure check: a measuring mistake is never absorbed
   into a wall. Said everywhere as **"Loop opens by n mm at D→A — type the
   other walls or drag a corner"**, and it closes by itself once the miss is
   within `join_tolerance`. A main chain of three or more walls whose ends
   miss by up to `Standard.loop_miss_max` (1000, NEW, display only, for
   Rudolf to confirm) is a loop that opened; beyond it the walls are an open
   run on purpose (a U's open side) and nothing is said. Validation: over
   `closure_block` a CRITICAL, over `closure_warn` a WARNING, in the same
   words (`room-closure`).
2. **Open / closed has ONE source: `room.closure(rm)`** — `{closed, miss,
   at, level, text}`. Every display reads it off the same compute:

   | Display | Reads |
   |---|---|
   | Room card pill | `_room_info.closure` (text and level) |
   | Toast when the loop opens / closes | the compute's `closure` against the previous compute's (`closureToast`), not the edit's reply |
   | Room card table, the open corner | `closure.at` — "— opens n mm" |
   | Wall card, corner before / after | `closure.at` — the full text |
   | Plan: floor tint vs face bands | `render._plan_room_side` → `closure` |
   | 3D: the note over the view | the scene's `room.closure` (the same function) |
   | Validation `room-closure` | `closure` |
   | `_room_info.closed` / `closure_error` | `closure`'s `closed` / `miss` |
   | Gaps (corner taper), Plinth (butt, `plinth-corner`), the elevation's neighbours, corner shadows | `room.connections`, which `closure` is derived from |

   Pinned in `check_room.py` `closure_text()` and `ui_check_walls.py --stage
   closure` (Test.json as frozen in `Test_3d.json`, its L closed into a
   rectangle in the page — Test.json's own room is an open L, which a typed
   length cannot open).
3. **Dragging edits walls directly, in Select mode.** A corner's round
   handle (shown on hover) drags it: every wall end on it moves
   (`room.corner_move`, `/api/corner-move`); dropped on another corner it
   joins it. A wall's body drags it parallel (`room.wall_move`,
   `/api/wall-move`, offset along its normal, + into the room): each wall
   joined at its ends keeps its other end and its direction and the joint
   slides along it, so a 90 stays 90; only a neighbour in line with it turns.
   What stands on a wall that changed keeps its x, clamped so it stays on the
   wall and reported, never moved off (`room.keep_on_walls`: placements,
   openings, obstructions). Esc restores; one compute per drop.
4. **Snaps while dragging and drawing**, in priority: a corner (join); a
   point on a wall (Draw only — the split); ALIGNMENT, a line through every
   other corner along the plan's axes and along every wall direction not on
   them, a dashed guide drawn while it holds; the ANGLE of the wall being
   stretched or drawn — 90 / 180 to the wall it meets (rank 0), the plan's
   axes (1), 45s (2), the `draw_angle_step` (3); the length step. An angle
   and an alignment holding together land where they cross. Shift: no snap.
   The snap applied is named beside the cursor. Candidates from
   `room.room_snaps` (`/api/room-snaps`, one call per press, per corner set
   while drawing); the browser projects the pointer and picks (`pickSnap`).
   Tolerance: `snap_tolerance`, or 8 screen px where that is more.
5. **Length labels on the plan are editable in place**: a text box over each
   wall's label (a foreignObject, so it zooms with the drawing), styled as
   the label until hovered; Enter → `/api/wall-set` as the Wall card; Esc
   cancels; Tab commits and moves to the next wall in walk order. Units shown.
6. **Drawing finished.** Starting on a point of a wall splits it there
   (`room.split_wall`, `/api/wall-split`, and `/api/room-draw`'s `split`):
   the first part keeps its letter, the second takes the next; placements,
   openings, obstructions, gap and plinth decisions follow by x; one spanning
   the split stays on the first part and is reported. A T-wall is free at
   its far end. A digit while drawing opens a length box (direction frozen);
   Enter sets the corner; Tab moves to an angle box (the corner made with the
   previous wall; for the first wall, degrees on the plan from +X);
   Backspace in an empty box takes the last corner off. Clicking the start
   closes; clicking any other existing corner ends there; double-click or
   Enter ends free; Esc out.
7. **Wall nook** (toolbar): click a wall, type width, depth and distance from
   its start; `room.wall_nook` (`/api/wall-nook`) splits the wall at both
   sides of the mouth, the middle part becomes the back (`depth` behind,
   keeping what stood there by x) and two new returns join it at 270 / 90; a
   closed room stays closed. Negative depth = a nib. A mode of the plan, as
   Draw walls is.
8. **Add back face** (Wall card): `room.add_back_face` (`/api/wall-backface`)
   — the same line, the other way, the wall's thickness behind, joined to
   nothing.
9. **Flip face on a wall of a closed room asks** "Flip the whole room? (the
   room side goes to the outside of every wall)": Flip room
   (`room.flip_room`, `/api/room-flip-all`, every wall of the chain; twice is
   identity) / Flip just B / Cancel. `_room_info` walls carry `in_loop`.
10. **Draw walls happens ON THE PLAN.** The separate canvas (`#drawsvg`) is
    retired: the plan is the same drawing, zoom and scroll; cabinets ghosted
    while drawing; a grid laid over it only while the mode is on; new walls
    live on top (`#drawlayer`). The Room tab's plan carries
    `render.PLAN_MARGIN_MM` (800) to draw into, an empty room is a 6 x 4 m
    sheet (`EMPTY_PLAN_MM`), and the plan's own mm mapping is on its `<svg>`
    (`data-mmx`, `data-mmy`, `data-pad`, `data-scale`). Zoomed out, the box
    round the plan takes clicks too. The same for the Nook tool.
11. **The Room tab's cards fit**: the plan asked for at its card's size (100%
    fits; the 100% button re-fits), Gaps the full width with every column, Plinth
    and Placements side by side under it at their natural widths, each
    card's notes behind a "?". Screenshots before and after at 1360 x 900 and
    1920 x 1080 in `output/_checks/ui_check_walls/layout_*`.

**What a drag does that the brief did not foresee:** a corner unit standing
in a corner keeps its x along its wall like anything else, so a corner
dragged away from it leaves it standing where it was along the wall — out of
the corner, which Validation already warns about; nothing re-runs it into
the corner. A cabinet on the wall that is moved parallel moves with the wall
(its x is measured from the wall's start, which slides along the
neighbour); the cabinets on a stretched neighbour keep their x from its start, so on a
neighbour whose START is the moved joint they shift in the room by the
stretch.


**Ruled by Rudolf, 3 October 2026, on Phase 2's two open decisions:**

- `Standard.loop_miss_max` 1000 — **accepted**: a closed room's loop opened
  by more than a metre by a typed figure reads as an open run.
- A corner unit keeps its x when walls are dragged, and Validation's
  out-of-corner warning flags it — **accepted**; nothing re-runs it into the
  corner.

**Touch-ups after Phase 2 (3 October 2026, brief
`Claude outputs/room-layout-touchups-brief-2026-10-03.md`).** Layout and the
plan's labels only. (1) Select · Draw walls · Wall nook are a segmented
control in the strip at the top of the Room tab, right of Plan | Elevation,
on Plan only. (2) Placements is the left column beside the plan, the plan's
height, its table narrowed (Item · Wall · X · Z · Y · Layer, five-digit
inputs), scrolled within; under the plan Gaps full width and Plinth under it
(item 11's side-by-side Plinth | Placements replaced). (3) Wall lengths go
through `render._place_labels` with the other labels, first, moved only out
along their wall's normal on a leader and never dropped; the page sizes each
length's field to its figure and its label to its content, at every zoom.
