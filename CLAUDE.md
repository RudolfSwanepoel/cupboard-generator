# CupboardApp — working notes for Claude Code

A cut-list generator for melamine kitchens and wardrobes. Rudolf designs the
cabinets; the app produces the panel list, validates it, nests it, and exports
the files Plazaboard cuts from.

## The one rule that matters

**Every dimension comes from `cabinetgen/standard.py`.** If you find yourself
typing a number into a formula anywhere else, stop — it belongs in `Standard`,
or on the `Cabinet` if it genuinely varies per cabinet. Three earlier jobs were
built by hand and eleven "constants" turned out to differ between them. That is
the failure this app exists to prevent.

## Check before you commit

```
python tools/regen_check.py
python tools/check_examples.py
python tools/check_room.py
python tools/check_fillers.py
python tools/check_plinth.py
python tools/check_drag.py
python tools/check_elevation.py
python tools/check_fronts.py
python tools/check_boards.py
python tools/check_library.py
```

Regenerates the October 2025 wardrobe from cabinet definitions and diffs it
against the cut list that was really sent to Plazaboard. Current state:

- 22 of 30 cabinets reproduce exactly
- 272 MEL / 59 DECOR / 30 BACK panels — matches the real job exactly
- 92 pot holes — matches the invoice exactly
- board counts from the nester: 18 / 9 / 6 — matches the invoice exactly
- estimated cost within R41 of the R28,322.75 actually quoted (R28,363.50)

If a change drops the clean-cabinet count or moves the cost estimate, it broke
something. The eight cabinets that do not reproduce are listed in `KNOWN` in
that script, each tied to a logged finding — those differences are correct.

## Layout

```
cabinetgen/standard.py     every construction constant. Start here.
cabinetgen/boards.py       the board library: load, save, tape names, job usage
boards.json                the library itself, shared through the repo
cabinetgen/model.py        Panel, Drawer, Cabinet, Job
cabinetgen/engine.py       cabinet -> panels
cabinetgen/drawers.py      drawer stacks: equal, graduated, pinned or exact
cabinetgen/validate.py     criticals block export, warnings do not
cabinetgen/nest.py         guillotine nesting + sheet layout SVGs
cabinetgen/render.py       SVG drawings: side-by-side elevation, plan, per-wall elevations
cabinetgen/room.py         walls, corners, to_world. The only trigonometry.
cabinetgen/store.py        job files: JSON save / load
cabinetgen/export_plaza.py Plazaboard CSV + costing off the real rate card
run_app.py                 starts the local server, opens the window
app/api.py                 request handlers. Thin — they call cabinetgen.
app/index.html             the whole UI. Vanilla JS, no build step.
jobs/                      job definitions. wardrobe_oct2025.py is the fixture.
tools/regen_check.py       the regression check above
tools/check_examples.py    verifies the worked examples in docstrings are true
tools/check_room.py        room geometry: closure, corners, to_world
tools/check_fillers.py     gap detection, taper, scribe, filler panels
tools/check_plinth.py      runs, butt joints, long-run splits, plinth panels
tools/check_drag.py        overlaps, snap targets, door swings, pull-outs
tools/check_elevation.py   per-wall elevations: chains close, plinth heights, hinges
docs/RULES.md             where each rule came from and what it cost to learn
docs/ROOM-LAYOUT-SPEC.md  the room / plan / 3D build spec and its phasing
```

## Conventions

- All dimensions in mm, integers. No floats in panel sizes.
- `Length` is the larger dimension on grain-free panels; on décor it is the grain
  direction and must not be swapped.
- Panel codes follow Plazaboard's scheme. `09` (divider) is ours — the old lists
  coded the same part as `08` in some cabinets and `99` in others.
- A designation must never sit on two different panels, and **a designation
  never changes** (ruled 14 September 2026). Generated panels are named as they
  are created — `engine.born_distinct` gives 105a / 105b where one code covers
  two sizes — and nothing is renamed afterwards. `generate_job` is read-only
  with respect to the job: a bespoke or loose panel goes onto the cut list
  exactly as the job defines it, so a bespoke cabinet with two sides of
  different sizes must define them as 01a and 01b itself. The D13 warning is
  what tells you it did not; the fix is in the job, never in the generator.
- **Two tickboxes gate a section: "Corner unit" and "Has drawers".** Both are
  tri-state on the `Cabinet` — `corner_unit` / `has_drawers`, `None` meaning
  "derive it from what is stored", which is how every job written before them
  reads. Unticking sets `False` and **keeps every value**: the drawer stack and
  the four corner measurements stay in the job file untouched, so re-ticking
  restores the cabinet panel for panel. `Cabinet.corner_on` and
  `Cabinet.drawer_list` are what everything downstream reads; nothing reads
  `corner_style` or `drawers` directly any more.
  Unticking can take panels off the cut list, and that is never silent:
  `/api/what-if` is asked first and names the designations that would go. A
  designation is only ever removed — never renamed, never reused.
- Bespoke cabinets set `template="none"` and supply `bespoke=[Panel(...)]`.
  The corner unit and the overhead are both like this — do not try to
  generalise a template to fit them.
- **Declared width, height and depth are inputs to panel generation and labels
  for display. No geometric check reads them.** Every check reads
  `room.geometry(cab)`, which reads the panel set — sides for height and depth,
  top or bottom for width, door panels for the swing, drawer sides for the
  pull-out — and the cabinet's `footprint` outline. The corner unit declares
  500 deep and has an 834 side; a check on the declared figure is wrong in the
  unsafe direction. See "Geometry" below.

## Boards, tapes and grain

**`boards.json` in the repo is the board library.** It is shared through git, so
both machines see the same boards. `cabinetgen/boards.py` loads and saves it, and
the Boards tab is where boards are added, edited and ticked into a project. Each
record is a name, a tape token, a thickness, Grain or Plain, a last price and an
optional picture.

**A project selects from the library, and selecting copies the record into the
job.** `Job.boards` is the selection; `Job.materials[id]` is the copy. That copy
is the price capture — see below — and it is why editing a board never reaches a
job that has already been quoted. `Job.board_ids` falls back to the keys of
`materials`, so every job written before the library still names its boards.

**Nothing can be cut until a board is selected.** A job with cabinets and no
boards is a critical naming what is missing, and the UI refuses to add a cabinet
and sends you to the Boards tab. Above `validate.BOARD_GUIDELINE` (5) it warns
and does no more: every extra board is another part sheet and another offcut
pile, which is a guideline about cost and complexity, not a limit.

**A board on the cut list that the project never selected is a critical.** An
unpriced board quotes at R0 while the total still looks like a number, which is
the worst way to be wrong, so it blocks.

### The three boards on a cabinet

- `carcass_board` — sides (01), top (02), bottom (03), supports (04), shelves
  (05), dividers (09), and the plinth board that covers its legs.
- `exterior_board` — doors (07), drawer faces (20), exposed end panels (08).
- `back_board` — the backing panel (06), and the drawer base (17) when it is the
  grooved 3 mm one, because that is the same thin sheet.

**The back board is chosen, not reached for.** The engine used to type `"BACK"`
onto the backing panel, so a project could cut a board it had never selected and
quote it at R0 with a plausible-looking total. It is a third dropdown off the
project's boards now. The default is `"BACK"` — the board the engine always
reached for — so every job written before this names the board it was already
using and nothing moves.

It is only asked for when something is actually cut from it
(`Cabinet.needs_back_board`: a back, or a drawer on a grooved base). A cabinet
with neither is not nagged for one, and the editor says why rather than showing
an empty dropdown. The stored value is kept when the section hides, the same
discipline as the tickboxes.

Drawer box sides and fronts (18, 19) and the **housed 16 mm** drawer base (17)
are still cut from `MEL` — not from the carcass board. That was never ruled, so
it was not changed; a cabinet whose carcass board is not MEL warns and asks.

### Tapes are generated, not mapped

Three tape names come off **one token per board**:

```
PVC <token>    the thin carcass tape
1mm <token>    exterior option
2mm <token>    exterior option
```

**The token is its own field, not the board's name, and that is load-bearing.**
Plazaboard's Brookhill tape is "PVC WOOD". "PVC BROOKHILL FUSION CHIP" is not a
thing they sell, so generating off the long name would put an unbuyable product
on a real order — D6/W10 in the other direction, where a board name reached an
order as a tape. A board with a blank token generates off its name, which is
right for a board whose name is already the short one; a board with neither
generates nothing and the validator names it rather than inventing a tape.

Colour derivation is unchanged: **front edges take the EXTERIOR board, every
other banded edge takes the CARCASS board.**

| Field | Derived as |
|---|---|
| `carcass_edge` | PVC in the **exterior** colour. Fronts of the sides, top, bottom, shelves, dividers and front-edged supports — shelf and divider fronts match the front, not the box (ruled 14 Sept 2026). |
| `door_edge` | `Cabinet.exterior_tape` (1mm or 2mm) in the **exterior** colour. Doors, drawer faces, exposed ends. |
| `drawer_box_edge` | PVC in the **carcass** colour. Drawer sides and fronts, and white-edged supports. |

Each is `None` for "generate it" and a string for a per-cabinet override.

**`Cabinet.exterior_tape` is 1mm or 2mm, per cabinet, and has no dimensional
effect whatsoever.** We supply finished sizes and Plazaboard deduct the tape, so
the two cut identically and differ only in what is ordered and what it costs.
There is no deduction logic anywhere and none is wanted. The carcass tape is
always the thin PVC and is deliberately not selectable.

The resolved tape names show in the editor beside each edge and as a legend on
the elevation (`render.tape_legend`), naming the cabinets when they disagree — a
door taped in the carcass colour looks right on paper and wrong in the room.

### Grain

**Grain is the board's Grain / Plain**, read through `model.grain_of`, and a
grain board locks every panel cut from it. It was hardcoded `grain=1` on doors,
faces and exposed panels, which was only ever right because the exterior board
was always the woodgrain one — W8/D9 is 60 woodgrain panels going out at grain 0
with only Plazaboard's counter catching it.

### Price capture

**A saved job keeps the prices it was quoted at.** `material_price` reads the
captured figure and `export_plaza.effective_price` is the one place that decides
what a board costs this job, falling back to the rate card only for a job saved
before boards carried a price. Editing a board's Last price changes what the next
project to select it is quoted at and moves no existing job. The October job
reopens at R28,363.50 permanently, and `check_library.py` pins exactly that by
raising a price in a temporary library and re-costing it.

### Thickness — 16 mm is assumed, and that is not fixed

Every carcass size in the app is 16 mm arithmetic. Thickness-driven geometry is
**deferred and deliberately not built**; what exists instead is an assertion —
`validate._carcass_thickness` names any cabinet whose board is not
`Standard.board_t`, and says which figures are the 16 mm ones. The full list of
places that assume it:

| File | Function | Line | What it controls |
|---|---|---|---|
| standard.py | *(constant)* | 12 | `board_t = 16`, the source of all of it |
| standard.py | *(constant)* | 21 | `back_cavity = 16`, clear space behind the back |
| standard.py | *(constant)* | 37 | `drawer_base_offset = 16`, base groove height |
| standard.py | *(constant)* | 46 | `exposed_extra = 16`, exposed end finishing flush with the door |
| standard.py | `internal_width` | 103-104 | `W - 2t` — every shelf, support, top, bottom and divider width |
| standard.py | `back_face_from_front` | 108 | shelf depth and the back's position |
| standard.py | `back_size` | 120, 122, 124 | the backing panel, `W-20` / `H-20` / `H-10` |
| standard.py | `drawer_front_length` | 155 | drawer front and back length, via `internal_width` |
| standard.py | `drawer_base` | 161, 164 | drawer base, grooved and housed |
| engine.py | `generate_cabinet` | 32 | `Wi`, which sizes tops, bottoms, supports, shelves, dividers |
| engine.py | `generate_cabinet` | 78 | default divider height, `H - 2t` |
| engine.py | `generate_cabinet` | 135 | exposed end panel depth, `depth + 16` |
| room.py | `geometry` | 296 | panel width read back off a top or rail, `span + 2t` |
| room.py | `plinth_deduction` | 967 | the board a butted plinth loses at an internal corner |
| validate.py | `_outlines` | 597 | corner unit wall sides, one and two boards short of the arms |

Not on the list and worth saying so: pot hole positions are `std.hinge_positions`
and carry no thickness at all, and fillers and scribes are gap arithmetic
(`scribe_allowance`, `taper_threshold`) with no board thickness in them either.

## Supports

**A support is a cross rail spanning the internal width** (`W - 32` x 100, code
04) that ties the two sides together. It is called a support everywhere in the
UI — never a rail.

`Cabinet.support_rows` is a list of `Support(edge, qty)`, where `edge` is
`'front'` (carcass tape), `'white'` (drawer-box tape) or `'none'`. **The total is
the sum of the rows and nothing subtracts.** The old model was a total with two
subsets taken off it, so `edged + white` could exceed `supports` and the plain
count went negative — which `if plain > 0` then dropped in silence.

`Cabinet.support_list` is what the engine reads. With no rows it migrates the
three legacy numbers in the order the engine always emitted them — plain, then
front-edged, then white-edged — so a migrated cabinet cuts the same list in the
same order. A cabinet whose three numbers contradict each other keeps cutting
exactly what it always cut and is **named in a warning**; nothing is migrated on
a guess. `Test_Build.json` cabinet 4 is the one real case (0 total, 4 white).

## The nester

`cabinetgen/nest.py`. Guillotine only — Plazaboard cut on a beam saw, so every
cut runs edge to edge. A layout the saw cannot produce is worthless, however
tight it looks.

It tries 7 panel sort orders against 6 guillotine split heuristics (42 packings,
about 0.3 s) and keeps the fewest sheets. On the October job it lands on
**18 MEL / 9 DECOR / 6 BACK — exactly what Plazaboard achieved**. Yields 88.9 /
77.3 / 79.8 %. If a change drops below that, it regressed.

Grain-locked panels are never rotated. `NEST_CHOICE` records which heuristic
won per material; `NEST_REJECTS` lists panels too big for a bare board.

Sheet layouts render to `out/nest_<material>.svg` — open in any browser.

Worth trying if more yield is wanted: cross-sheet offcut reuse (keep a stock of
leftovers between jobs), and simulated annealing over the panel order. The
77 % on Brookhill is the one worth attacking — it is the R999 board.

## The UI

`python run_app.py`. See `docs/UI-BRIEF.md` for why it is shaped the way it is.

The cabinet editor is eight sections, each a bold heading over its own coloured
block: **Size · Outline · Structure · Doors · Drawers · Corner Unit · Back &
Supports · Decor**. Drawers and Corner Unit are the tickbox sections above.
**Back & Supports** carries the support rows; **Decor** carries the two board
dropdowns and the three tapes, each showing the derived value with an override
beside it. Both boards are dropdowns off `Job.materials` — free text there used
to create a fourth material silently, which nested on its own sheet and priced
at zero.

Four tabs over one `POST /api/compute`. The handlers in `app/api.py` decide no
dimension — every number in a response came out of the engine. Keep it that way:
if the UI needs a number, add it to `cabinetgen`, do not compute it in the
browser. `nest.nestable()` exists for exactly that reason — the UI and
`regen_check` must agree on which panels reach the nester or the board counts
drift apart.

Drawer face heights are authored **one row per face**, top to bottom. A row is
either **Fixed** — the height as typed — or **Share**, a slice of whatever the
fixed rows leave, split in proportion to its share number. The gaps come from
`Standard` and are never typed per drawer. `drawers.divide` does the arithmetic
and `/api/drawer-solve` hands it back, so the millimetres shown live beside each
row as it is typed are the engine's, not the browser's; `Equal` and `Graduated`
come from `/api/drawer-preset` for the same reason (`Standard.graduated_step`).
Fixed rows that over-run the opening leave the share rows at zero, which is a
critical and blocks the export rather than ordering a negative panel.

`face_height` is still the ordered figure and still the only one the engine
reads — what was ordered is a list of heights. `Drawer.mode` and `Drawer.share`
ride alongside it so a stack can be picked up and re-divided later instead of
retyped; nothing downstream reads them.

Dragging the join between two faces in the elevation pins **those two only**: the
SVG carries each pair's span in both mm and pixels (`class="fdiv"`), the browser
reads its drop back into millimetres the same way a plan drag projects onto a
wall track, and `drawers.split_pair` divides the pair server-side. The rest of
the stack is untouched, and each face is held back far enough to clear its own
box side — which is the existing rule, not a new number.

Not editable in the UI yet: loose panels, the bespoke panel lists on
`template="none"` cabinets, and a wall's openings and obstructions. All are
carried through the job file faithfully but must be edited there. A cabinet's
outline *is* editable — the Outline field in the editor — and the editor shows
what the engine's checks are actually using beside it.

## The room

`docs/ROOM-LAYOUT-SPEC.md` is the spec and the phasing. **Phases 1 to 5 are
done:** the dataclasses, `room.py`, `to_world`, the closure check, a wall-entry
form, `render.plan_svg` with the layer toggle, placements by form, gap detection
with fillers and scribes, plinth, drag placement with collisions, snapping and
front-clearance checks, and dimensioned per-wall elevations.

Phase 6 is 3D.

`Job.room is None` is the default and must stay behaving exactly as it did
before rooms existed — same panels, same nest, same cost, and no `room` or
`placements` key written to the job file. That is what keeps `regen_check`
meaningful, so it is pinned in `tools/check_room.py`.

All trigonometry lives in `room.py`. Plan view, elevations, 3D, DXF and the
SolidWorks table all call `to_world(room, wall_id, x, y, z)` and none of them
does its own. Wall-local axes are x along the wall from its start corner, y out
from the wall face into the room, z up. World is X right, Y into the room from
wall A, Z up — which maps onto SVG with no flip.

Two things about corners that are easy to get wrong:

- Every corner is measured **twice**, once from each wall that meets there
  (`walls[i].offset_end` and `walls[i+1].offset_start` are the same physical
  angle). The first wall's figure drives the geometry; the second is
  cross-checked and a disagreement is reported, never averaged. If only one is
  given, it is used — so a corner need only be measured from the reachable side.
- A square room closes even if the corner turn has the wrong sign. The
  parallelogram case in `check_room.py` is what actually proves it; do not
  delete it.

Thresholds live in `Standard` like every other dimension: `closure_warn`,
`closure_block`, `corner_disagree`.

**Layers** come from `room.layer_of`: kind `tall` is tall, kind `upper` is wall,
anything else off the floor (`Placement.z > 0`) is wall, everything else is
base. `Placement.layer` overrides it. No z threshold was invented — hung is
hung. The browser never derives a layer; `/api/compute` returns the layer per
cabinet and the UI reads it back.

**Layers are for drawing; runs are about the floor.** `room.run_key` folds
tall into base: a tall unit stands on the same floor as the base unit beside it,
so it is in the same run, closes the same gaps and carries the same plinth
board. Grouping runs by drawing layer made a tall unit invisible to the base run
next to it (found 14 September 2026, fixed). Overlaps do not group at all —
they compare anything on the same wall whose heights overlap, so an overhead
hung into a tall unit is caught too.

## Geometry

`room.geometry(cab)` is the one code path, template or bespoke, and returns
`CabinetGeometry`: the outline in the cabinet's own frame (x along the wall from
its left edge, y out from the wall face), height, the deepest carcass panel, the
width the panels make, door widths, runner. Read off `engine.generate_cabinet`
at call time — engine imports room, so room imports engine only inside the
function.

- **`Cabinet.footprint` is any shape.** A polygon in that frame, in the job
  file, entered in the editor as `x,y` pairs. Empty means "the rectangle its
  panels make", which is right for every template cabinet. A corner box is an
  L and must be entered — the validator warns when a bespoke cabinet has none.
  A standard cabinet is a four-point rectangle *in the same type*: one field,
  one code path, no special case.
- **Non-convex outlines are real polygons, not bounding boxes.** `room.
  polygons_overlap` triangulates (ear clipping) and runs the separating-axis
  test per piece; touching is clear, a unit tucked exactly into an L's notch is
  clear, and two identical rectangles overlap. Pinned in `check_drag.py`.
- The validator cross-checks an entered outline against the panels (depth
  against the deepest side, width against top or bottom plus two sides) and
  says which one is wrong; it rejects an outline that is not a polygon.
- What still reads declared figures, on purpose: `engine.generate_cabinet` (it
  makes the panels from them), the spec checks in `validate._cabinet_structure`
  (runner fits the declared depth — the engine would raise otherwise), the size
  captions on drawings, `render.elevation_svg` (the pre-room side-by-side sanity
  check, pinned byte-identical), and `render._interior` (door and drawer face
  rectangles from the spec that made those panels — same numbers).

The plan view ghosts unselected layers rather than hiding them, draws wall units
dashed and translucent so the base run reads underneath, draws every label after
every shape so an overhead cannot bury the number beneath it, and draws
obstructions last of all — a waste pipe behind a carcass is the one thing on
that drawing you cannot afford to miss.

`/api/plan` is separate from `/api/compute` on purpose: flipping a layer should
cost a redraw, not a re-nest.

**Walls are added at either end of the sequence** — `room.add_wall(rm, "start" |
"end", length)`, behind `/api/room-extend` and the "+ Wall before / after" buttons.
That is how a straight run becomes an L or a U; the 4000 × 3000 pre-fill for a new
room stays (ruled 14 September 2026). A new wall takes the next free letter and
starts square. Placements name walls by id, so nothing moves along its wall, but a
wall added at the start re-origins the chain and becomes the "earlier" wall at that
corner for the plinth butt rule.

## Gaps, fillers and scribes

**The app proposes; it never inserts.** Ruled 14 September 2026, after the
earlier "every run gets a filler" rule proved too rigid — real kitchens use
fillers, blind corners and deliberately open gaps depending on the situation. A
gap with no treatment chosen emits no panel and raises a warning. Do not be
tempted to default it to `filler`; that is precisely the wrong cut list going
out unnoticed.

`room.gaps(job)` finds them, per wall **and per run** (`run_key`: the floor
run, tall units included, and the hung run) — a gap in the base run is not a gap
in the overheads above it. Suggestions come from the ruled numbers
in `Standard`: under `filler_min` (50) grow a cabinet, up to `filler_max` (150)
fit a filler, above that add a cabinet or a blind corner.

The taper is the whole point. A gap that meets an out-of-square corner is wider
at the front of the run than at the wall, by `depth × tan(corner deviation)`.
Plazaboard cut on a beam saw, so **a tapered panel cannot be ordered**: the
filler ships as a rectangle at the gap's widest point plus `scribe_allowance`
(15), and the note on the panel says to scribe it. Above `taper_threshold` (6)
the validator says so too.

Note what the taper is measured across: the run's **depth**, not the panel's
height. The room model has plan geometry and no plumb data, so an out-of-plumb
wall is not modelled and cannot be. If Rudolf meant taper over the panel's
length, that needs a plumb measurement per wall first — ask before changing it.

Fillers carry `cabinet=0` and name their run in the note, alongside the existing
`Job.loose` mechanism. Several fillers in one job get suffixed labels (011a,
011b) by the existing `suffix_labels`.

Panel codes `10` and `11` are **not yet confirmed with Plazaboard**. The
validator warns whenever a plinth or filler exists; flip
`Standard.codes_confirmed` when they sign off and both warnings stop.

## Plinth

**Legs are never optional; the plinth board is.** Corrected 14 September 2026,
after the first build got it backwards. Every carcass that stands on the floor
stands on adjustable legs — kitchen or wardrobe, always — so the height lift
belongs to the legs: `Standard.leg_height` 100 (the spec's "plinth height"),
within `leg_min` 98 to `leg_max` 122. `room.carcass_z` adds it to every standing
cabinet unconditionally and never asks whether a board is fitted. **Do not let a
plinth flag anywhere near a height again** — that was the bug, and it moved the
clash, opening and ceiling checks with it. `check_elevation.py` pins that fitting
a board changes no height.

The plinth *board* covers the legs. It is `leg_height` wide, set back
`plinth_setback` 50, carcass board, banded on both long edges (`edge_l=2`) to
seal it against water at floor level — the short end cuts are not banded.

**The board is opt-in per run**, the operator's call, whatever the job. Nothing
is made unless a `PlinthChoice` asks for it; the flag gates the code-10 panel and
nothing else. Same discipline as the gaps: the app shows you the runs, you decide.

`room.runs()` finds the runs, and what counts as one run is the load-bearing
decision: a filler or a blind corner **continues** a run, an open gap **breaks**
it, because a plinth board cannot span an appliance space. An undecided gap
breaks it too — conservative, and it already carries its own warning.

Two things that would be wrong if done naively:

- **Internal corners butt**, so exactly one of the two boards at a corner loses
  a board thickness. Never both (that leaves a gap) and never neither (it does
  not fit). The rule: the run on the *earlier* wall continues past, the one on
  the later wall stops square against it and loses 16 mm off its start. The
  panel note names the wall it butts into.
- **A run longer than a board splits at a cabinet division**, not wherever
  2750 mm lands, so the joint falls behind a carcass side. `plinth_lengths`
  takes the last division that still fits.

A run whose cabinets sit off the floor gets no plinth and a warning saying why.
A `PlinthChoice` whose run no longer starts at that cabinet is orphaned: no
panel, and a warning — the safe way round.

## Drag placement

**The browser computes no dimension.** That is the spec's rule and it shapes the
whole design. On pointerdown the UI asks `/api/drag` for that cabinet's snap
targets — wall ends, neighbouring cabinet edges, opening edges — all from
`room.snap_points`. The drag then only *picks the nearest of them*; it never
works out a position of its own. On drop the whole job is recomputed
server-side, so what reaches the cut list is always the engine's answer.

The plan SVG carries what a drag needs: `data-cab` on each cabinet, and an
invisible `#tracks` group with one line per wall giving its screen ends and its
length. The browser projects the pointer onto the nearest track. A drag near a
different wall re-parents the cabinet to it, which is why the snap model covers
every wall, not just the current one.

Drag listeners live on `window`, not on the element — a drag that runs off the
plan has to finish rather than stick to the pointer. Ghosted layers are not
draggable, so a wall unit only moves while the wall layer is the one shown
solid.

**Overlaps are critical; clashes are warnings.** Two carcasses cannot share a
stretch of wall, and a cut list built on that is wrong however good it looks. A
door or drawer that fouls something is a real defect, but which way a door hangs
is a judgement — blocking the export over it would be the app overruling the
person who measured the room.

Swing and pull-out geometry is in `room.py` and every envelope is emitted into
the plan hidden, so hovering costs nothing and the browser never computes an
arc. Two things about the checks that are easy to get wrong:

- **A door never fouls its own wall.** It pivots on the front face and sweeps
  away from it. A door hinged right at a corner finishes flat against the return
  wall — it grazes it, it does not swing through it, and that is not a clash.
  The cases worth catching are the return run, the run opposite, and the wall
  opposite in a galley.
- **Heights matter.** A base unit's door does not care about a wall unit two
  courses above it, so clashes only count where the vertical ranges overlap.
  Overlaps work the same way — heights, never layers — so a tall unit standing
  into a base unit, or an overhead hung into a tall unit, is a collision, while
  an overhead sitting over a base run is not.

`Standard.door_open_deg` is 90 — the drawing convention, not a construction
dimension. If a real job needs 110 the clash check follows the constant.

**Hinge side has one answer: `model.hinge_side`.** The plan's swing arcs, the
elevation's hinge marks and the clickable door leaves all read it, so they
cannot drift apart. `Cabinet.door_hinges` holds a per-leaf 'L'/'R' — one entry
per leaf, blank meaning "use the rule" — and the rule, when nothing is set, is
the one that was always here: a single door follows `Placement.flip`, a pair
hinges at its outer edges. A leaf hangs off **its own** edge, so turning one half
of a pair round puts its hinge in the middle of the opening, which is where it
really is.

The editor gives one Left/Right control per door panel the engine actually cut —
`len(geometry(cab).door_widths)`, not `cab.doors` — so a bespoke or corner unit
gets one too. Clicking a door in the elevation toggles it. Every change goes
through `/api/compute`, so the swing check re-runs on each one and the editor
reads the result back. The elevation only draws leaves for template cabinets
(`render._interior` works off the spec that made the panels, on purpose), so a
bespoke cabinet's leaf is turned round from the editor rather than the drawing.

## Per-wall elevations

`render.wall_elevation_svg(job, wall_id)` draws one wall face on, as a drawing
meant to be measured from: cabinets at their true x and height, the wall and its
ceiling, openings with sill and head, obstructions with where to find them, the
fillers and plinth boards that were *chosen*, hinge side and count, and dimension
chains. With `room=None` it returns `elevation_svg(job)` unchanged — pinned byte
for byte in `check_elevation.py`. `/api/elevation` is separate from compute for
the same reason as `/api/plan`, and export writes one `_elevation_<wall>.svg` per
wall.

The chain numbers come from `render.wall_elevation_dims`, kept apart from the
drawing so they can be tested. Widths chain from the wall's start corner (the
floor run and the wall units separately), heights from the floor. **Every chain
closes** on the wall length or the ceiling — a chain that does not close is a
drawing that is lying.

**`room.carcass_z` is the one answer to "how high is it really".** `Placement.z`
of 0 means standing on the floor, and every standing carcass is on its legs, so
it starts `leg_height` up — board or no board (see Plinth). A hung unit is at its
own z. The elevation, the clash check, the opening check and the ceiling check all
ask `carcass_z`, so they cannot disagree: an overhead door at 780 fouls a base unit
topping out at 820 on its legs, and a 900-high unit under a 900 sill stands across
the window, not below it.

**Hinges: side and count from the order, positions for the drawing only.** Side
follows the same rule as the plan's swing arcs, and `check_elevation.py` checks the
two agree; the opening triangle's point is on the hinge side. Count is
`std.hinges`, the pot-hole figure already on the order. Positions come from
`std.hinge_positions` — `hinge_inset_drawn` (100) in from each end, any between
spread evenly — ruled with low confidence and **for drawings only**: pot holes are
drilled to Plazaboard's hardware spec. The drawing says so in a footnote, nothing
validates against the positions, and `check_elevation.py` fails if engine, export,
nest or validate ever reads them.

**The ceiling is a required site measurement.** `Room.ceiling` has no default; a
room without one is a critical and the job does not export — the same as a wall
with no length. Against a measured ceiling, a carcass top above it is a critical
too: a cabinet that cannot be stood in the room is as wrong as two that overlap.
A cabinet standing across an opening stays a warning (a top touching the sill
counts as clear), because opening sizes are site figures. An unmeasured ceiling is
never compared against; the elevation draws without it and says it is missing.

**Tip-up clearance.** Every carcass is built flat on its back and tipped up in one
piece, so a ceiling it clears standing but not on the way up is a critical too
(ruled 14 September 2026). `room.tip_clearance(H, D, L, s)` is exact: it pivots on
the bottom back edge until the rear feet touch down (tan angle = L / s), then on
the rear feet, and the top front edge peaks at `sqrt((D - s)² + (H + L)²)` on the
feet or `sqrt(D² + H²)` on the edge, whichever that phase actually reaches.
`Standard.leg_setback` is ruled at 50; it only moves the answer within about a
12 mm band, so build nothing else around it. The worked examples in the docstring
are checked by `check_examples.py`. A cabinet too tall to stand is reported once,
as that, not twice.

D is `room.carcass_depth`: the **deepest carcass panel**, never just the declared
depth. A bespoke corner unit declares 500 and has an 834 side, and depth drives
the diagonal, so the declared figure under-reports — the unsafe way to be wrong.
Only sides, top, bottom, shelves and dividers count, matched on the first two
characters of the code because `suffix_labels` may already have made "01" into
"01b" on the bespoke panel itself. Room depth does not enter the formula, and
there is **no clear-floor check for laying a carcass out** — ruled out of scope,
because laying out elsewhere and walking it in is normal practice.

Names from the job file — wall ids, opening and obstruction kinds — go into SVG
escaped, and into export file names through `api._safe_name`, so a job called
`../x` cannot write outside `out/`.

Still open, and **not to be guessed into `Standard`**:

- whether kitchen appliances need to be room objects with clearances, and whether
  worktops are in scope;
- the offset measuring depth and sign convention (shipped with the spec's
  proposed defaults, still awaiting confirmation);
- where the legs stand, for drawing them — only the rear setback (50) is ruled,
  and only the tip-up check uses it, so legs are still not drawn.

Corner units are parametric (ruled 14 Sept 2026, spec items 11-15):
`corner_style` ('mitre' | 'ell') plus `arm_a`, `arm_b`, `face_a`, `face_b` on
`Cabinet`; `room.corner_outline` derives the plan outline and `room.geometry`
uses it as `source == "corner"`, ahead of an entered `footprint`. There is no
angle field — a mitre's angle falls out of the four measurements, 45° only
when `arm_a - face_b == arm_b - face_a`, and nothing compares it with 45. It is
reported, never entered: `CabinetGeometry.mitre_deg` and `.face_lengths` (read
off `.front_faces`) go out through `/api/compute` and show in the editor's
readout, which is how a door and its reveal are read against the face it hangs
on — cabinet 7's 472 door in a 495 face. `swing_envelopes` hinges a corner
unit's door off its real front face (the mitre edge, or for an ell whichever
face carries the door) rather than the outline's extreme corner. An ell with one
door hangs it on the shortest face it fits (the longest if neither), from the
outer end, or the notch end if flipped; with two, one per face from the ends away
from the notch. The validator checks the four measurements against the sides that
were cut: each open face must match a side, and the two remaining wall sides must
be one board short of one arm and two short of the other (cabinet 7: 834 / 818).
A door wider than the longest face it could hang on is a warning too — it cannot
close in the opening, and its swing runs back into the box.
`room.corner_shadow` is what lets a corner unit placed flush in a corner fill
the start of the *next* wall's run for `gaps`/`runs` purposes too, and
`overlaps` is checked in world coordinates across every wall at once rather
than one wall at a time, so a cabinet placed into that shadow is still caught.
The October fixture's cabinet 7 carries its real measurements — `arm_a`/`arm_b`
850, `face_a`/`face_b` 500, mitre — cross-checked against its own panels in
`docs/ROOM-LAYOUT-SPEC.md` item 14. A corner unit with no outline and no
corner parameters still falls back to the panel-extents rectangle, with a
warning that names the cabinet and calls it an approximation, not a
measurement.

Everything the filler, plinth and hinge-drawing work needed was ruled on
14 September 2026 and is in `Standard`.

## Not built yet

1. **CAD export.** DXF per panel plus a parameter table SolidWorks can drive a
   configuration from, so the model and the cut list cannot diverge.
2. **Obstruction cut-outs on backing panels.** Deferred 14 September 2026 for the
   same reason as sliding doors: an obstruction behind a carcass is drawn, but no
   cut-out goes on the cut list until a real job supplies a real pipe position.
3. **Sliding doors.** Not urgent, but leave the seam. A hinged door is a
   property of one carcass; a slider spans an opening that may cover several.
   When it is built it needs a `DoorSet` above `Cabinet`, not more fields on it.
   The arithmetic that changes:
   - height = H - top track - bottom track  (roughly 40-50 and 10-20)
   - width  = (opening + overlap x (n-1)) / n, overlap around 50
   - pot holes = 0
   - carcass depth reduced by the track depth, around 100, decided per run
   - framed doors: board panel is smaller than the door by the frame section,
     and usually carries no edging
   Real numbers come from a real job, the same way everything else here was
   derived. Do not guess them into Standard before then.

## Things that will bite you

- Plazaboard's `holes` column is the **line total** (per panel × qty). Ours is
  per panel. `export_plaza.rows_for` does the multiplication — don't double it.
- Edging includes a **70 mm trim allowance per banded edge**. The formula in
  `Standard.edging_m` is exact on all 166 edged rows of the real job. Don't
  "simplify" it.
- Grain must be 1 on every décor panel. On the last job it was 0 on all 60 and
  only Plazaboard's counter caught it.
- A panel longer than 2750 mm cannot be cut. One got through last time and came
  back 152 mm short with nobody told.
