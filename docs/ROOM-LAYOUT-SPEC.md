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
same house style and colours as `elevation_svg`.

Draws: wall lines with lengths, openings as breaks in the wall, obstructions as
marked boxes, each cabinet as a rectangle at its true plan position, fillers
hatched, plinth setback as a light line, cabinet number and W x D labelled.
Gaps below the filler minimum are dimensioned in red.

## Drag placement

Interaction rules, in order of how much grief each one saves:

- A cabinet belongs to a wall and drags **along that wall only**. Free 2D
  dragging is what makes these interfaces unusable. Dragging it near a
  different wall re-parents it to that wall.
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

## 3D view

three.js, **vendored into `app/vendor/`** — not a CDN. The app runs locally and
must work offline. Modern three.js is ESM only; load it with an import map
pointing at the local files, which needs no build step and works in both the
browser and the pywebview window.

Render the actual panels, not solid boxes. The panel data already exists, so a
real-panel model doubles as an assembly check and costs almost nothing extra.

- Room shell: floor and walls; the wall nearest the camera auto-hides.
- Doors and drawer faces as separate surfaces, with an open / closed toggle so
  clearances can be seen.
- Orbit, pan, zoom. Click a panel to show its label, size and cut-list line.

That last point is the one that matters most for bespoke work: it ties the
picture to the order, so a panel cannot be admired in 3D and wrong on the list.

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
5. **Per-wall elevations,** dimensioned. — **status unclear: confirm with
   Claude Code whether this was folded into Phase 4's render.py work or is
   still ahead of 3D.**
6. **3D.**
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
