# CupboardApp — how it works

Each area of the app, section by section, as CLAUDE.md held it. The hard
rules, the checks and the layout are in `CLAUDE.md`; the history of each
decision in `docs/HISTORY.md`; the room / plan / 3D rulings in
`docs/ROOM-LAYOUT-SPEC.md`.

## Demo build

**`Build Demo.bat`** (one click, repo root; the work is `tools/build_demo.py`)
makes `demo\Cupboard App Demo <build date>.zip`: the whole app, compiled by
Nuitka to machine code (no `.py` / `.pyc` of this repo inside — the build lists
the zip and fails if there is), which a friend unzips and double-clicks. No
Python needed on their machine. It stops working 60 days after the build.

1. `pip install nuitka` if missing; Nuitka downloads its own C compiler
   (MinGW) the first time. Its cache is `%USERPROFILE%\NuitkaCache`
   (`NUITKA_CACHE_DIR`): **Store Python hides what it writes under AppData in a
   private folder, and the downloaded gcc then cannot find `windows.h`.**
2. Writes `app/_demo_build.py` (`DEMO = True`, `EXPIRES` = today + 60), builds,
   and deletes it again whatever happened (gitignored, never committed).
3. Standalone FOLDER build, not onefile — onefile unpacks to a temp folder on
   every run, and `ROOT` comes from `__file__`, so saved jobs, `output/` and new
   pictures would vanish. The folder build keeps them beside the exe (proved:
   a save, an export, a snapshot and a new picture all landed in the unzipped
   folder). No console; `app/cupboard.ico`; `Cupboard App Demo.exe`.
   `jobs.wardrobe_oct2025` is named for Nuitka (imported inside a function).
   pywebview (WebView2 through pythonnet / clr_loader) needed no flags: Nuitka's
   own package config brings its DLLs.
4. Copies in by NAME, never by exclusion: `boards.json`, `hardware.json`,
   `jobs/*.json` (**not `jobs/_deleted/`**, ruled 30 Sept 2026), `Pictures/`,
   `app/index.html`, `app/view3d.js`, `app/vendor/`, `app/cupboard.ico`.
   `READ ME FIRST.txt` sits beside the `Cupboard App Demo` folder in the zip.
   `jobs/shipped-jobs.json` lists the job files it copied (the zip listing names
   it): Import leaves those out, Load does not offer the list (3 Oct 2026).

**Demo mode is `app/demo.py`**, off unless `_demo_build.py` exists, so a normal
run behaves exactly as before. On: start-up past `EXPIRES` shows "This demo of
Cupboard App expired on <date>. Contact Rudolf for a new copy." in a message box
and exits; every request asks again (`api.Handler._demo_stopped`), and the page
shows the reason over everything (`demoStop` in `index.html`); the latest date
seen is kept in `output/demo-seen.txt`, and a clock more than 1 day behind it is
refused. The window is titled `Cupboard App — Demo (until 29 Nov 2026)`.
Geometry, nesting, costing and export are untouched.

**To move to a new demo: unzip it, start it, Import project, pick the old
folder** (the outer folder or the `Cupboard App Demo` inside it). It brings the
old folder's jobs, boards, runners and pictures across and only reads the old
folder, so an expired demo's work comes across too. See **Import project**
under Status.

**To extend a demo: build again** — the date is baked in. `Build Demo.bat
--test-expired` makes a throwaway copy that expired yesterday (a test; the zip
says TEST-EXPIRED — never send it, and delete it after). Building needs the
Python that runs the app (it must have pywebview). `build-demo/` and `demo/` are
gitignored; never commit an .exe or a zip.

## Attached panels

**A panel fixed to a cabinet** (spec of 28 September 2026). A Panel item in
every respect — Kind = Panel, its own number in the one series, its own code-08
line, board, size, orientation and edging exactly as a standalone panel — that
carries `PanelSpec.attached_to`, a cabinet number, and three offsets.

**The offsets are in the supports spec's carcass frame**, typed in Panel design
and nowhere else: `at_x` across the width from the cabinet's left side, `at_y`
from the FRONT face of the sides towards the back, `at_z` up from the underside
of the sides, each to the panel's own near corner (left, front, bottom).
Negative values are ordinary: an end panel stands at x = −t, and one finishing
flush with the doors at y = −(door thickness). The drawing frame has y OUT from
the wall, so the two meet at `y_cab = D − y_spec`, D the carcass depth off
`geometry` — in `room.attached_placement`, the one place the world position is
worked out:

    x = cabinet x + at_x
    y = D − at_y − (the panel's extent out from the wall)     (Placement.y is its BACK)
    z = the cabinet's underside on its legs (carcass_z) + at_z

**Its place is derived, never stored.** `room.placement_for` hands the derived
`Placement` back for an attached panel, so `placed_panels`, the plan, the wall
elevation, the scene, `_on_wall`, the snaps and `panel_clashes` all read it
without a line changing. `store` writes no placement record for it (a stale one
left in a file is never read), and `api.drag` refuses it — its cabinet is what
moves. A cabinet's own attached panels are excluded from its snap targets with
it (`_on_wall(exclude=…)`), so it cannot snap to a panel that moves with it.
While the cabinet is not placed, neither is the panel.

**Where the browser shows it.** Panel design: an Attached block — the cabinet,
Show cabinet, Detach, the three offsets, and the engine's readout of where that
puts it (`placed_at`). A standalone panel gets a dropdown and Attach instead.
A cabinet's editor: an **Attached panels** section listing them, with
**+ Panel on this cabinet** (`room.new_attached_panel`: an end panel, side-on,
in the exterior board, `depth + exposed_extra` deep, carcass high, against the
left side, brought forward by the extra — a starting point off `Standard`, not
a rule). The Placements table shows it "with N", not editable. The cabinet
table says `panel · on N`; the 3D item list `panel on N`. The plan and the
elevation put `data-host="N"` on its shapes, so a drag of cabinet N carries
them in the preview and the drop's compute places them; in 3D the cabinet's
handle drag moves their groups too, and an attached panel gets no handles of
its own. A press on one in the plan or the elevation selects it and says how
it is moved.

**Room checks (spec B6).** It counts as part of its cabinet's geometry:

- `gaps` — the run's extent along the wall is `room.attached_extent`, the
  carcass plus any attached panel LEVEL with it, so an end panel closes the
  gap to the corner by its thickness; a bulkhead attached above is not in the
  run. A standalone panel still closes nothing.
- `overlaps` — an attached panel standing in another cabinet is the same
  CRITICAL as the carcass standing there (`overlap`, the message names the
  panel and its cabinet); `panel_clashes` does not repeat it.
- `clashes` — a door or drawer of ANY cabinet, its own included, sweeping into
  it is a clash "panel N on cabinet M". Touching is clear, as everywhere.
- `above_ceiling` — up past the ceiling is the same critical as a carcass.
- **`tip_problems` and `tip_inputs` do not read it**: attached panels are
  fitted on site after the carcass is stood up. `placed()` is still cabinets
  only, and that is what tip-up reads.
- Cutting INTO its own carcass — overlapping, not touching — is a WARNING
  (`attached-into-carcass`, `room.attached_carcass_overlaps`), never a critical.
- `attached_to` naming nothing the job has (a deleted cabinet, a panel, itself)
  is a WARNING (`attached-host`); the panel cuts as it is and stands nowhere.

**Attach, detach, delete, duplicate — all decided on the server.**
`/api/panel-attach` works the offsets out from where the panel stands
(`room.attach_offsets`: the exact inverse on the cabinet's wall; from another
wall its box's near corner is carried across in world coordinates; unplaced,
`default_offsets` — beside the left side, flush and level) and the browser
drops its placement record. `/api/panel-detach` hands back the derived
placement as the record to store; with `host` it detaches every panel on a
cabinet, which is the "No" of the delete question. "Yes" removes them with the
cabinet. `/api/duplicate` copies a cabinet AND its attached panels, each with
the next free number, the panels attached to the copy at the same offsets;
duplicating an attached panel copies it onto the same cabinet. Numbers never
change through any of it (hard rule 2).

**Job file.** `attached_to` and the three offsets are written only on an
attached panel (`store.ATTACH_FIELDS`), so every standalone panel and every job
on disk writes back byte for byte. `tools/check_attached.py` holds all of the
above, and `tools/ui_check_attached.py` drives the UI.

**The drag in the single-cabinet 3D view (spec B4)** is built with the UI
restructure: see **The Cabinets tab's 3D**. `PanelSpec.anchor` is still
reserved and unread.

## The Cabinets tab's 3D

**The selected cabinet alone** (UI restructure, 28 September 2026). The same
engine and controls as the 3D tab — `app/view3d.js` is now a factory,
`createView(opts)`, and the Cabinets tab has its own instance (`V3C`,
`createView({single: true})`) beside the 3D tab's (`V3D`). Orbit, pan, zoom,
shaded / edges / x-ray, fronts open, labels, the part pick and card, the view
cube and the help card; no layers, walls, ceiling, isolate, clearances,
snapshot or item list — there is nothing of the room to act on.

- **What it draws** is `scene.build_cabinet(job, number)` behind
  `/api/scene-cabinet`: the cabinet's own parts exactly as `build` draws them
  (carcass, fronts, backing, supports, shelves, bands; the same cut-list lines),
  standing in its own frame — x across from its left side, y out from its back,
  on the floor as `Placement.z` 0 stands it — plus **its attached panels**, put
  where `room.attached_placement` puts them off that placement, so the room and
  this cannot disagree. No room, no walls, no neighbours, no overlays. It is
  read-only, and it draws an unplaced cabinet as well as a placed one.
- **What it shows**: the selection (`cabShown()`): a selected ATTACHED panel
  shows its cabinet with it; a standalone panel alone; nothing selected, the
  first item in the job (the heading says so); no items, a prompt to add one.
  Selecting anywhere — the list, the plan, the elevation, the 3D tab — changes
  it (`sync3D`), and every compute refreshes it while the tab is showing
  (`refreshScene` -> `refreshCabScene`); hidden, it catches up when shown.
- **A part pick** selects its item (an empty click keeps the selection — this
  view IS the selection) and **opens the editor at that part's section**
  (`jumpToSection`, `PART_SECTION`: door -> Doors, support -> Supports, a panel
  -> Panel design…). The 3D tab's pick does the same now.
- **The attached-panel drag (spec B4).** A selected attached panel gets three
  arrows in its cabinet's frame: across (`at_x`), back (`at_y`, towards the
  back — `-y` in the room frame) and up (`at_z`). One `/api/attach-snaps` on
  the press — `room.attach_snap_points`: every face or edge of the carcass
  meeting a face or edge of the panel (outside / inside each side, both edges
  level; the front face, flush with the fronts, the back face; level
  underneath, on top, under, on the bottom panel), sorted, one reason each —
  listening before it lands, the nearest within `snap_tolerance`, and the drop
  through `/api/attach-move`, which hands back the whole-millimetre offsets to
  store in the panel's own `at_x` / `at_y` / `at_z` — **the same fields Panel
  design types** (hard rule 8). The browser works out no offset. Pinned in
  `check_attached.py`'s `restructure()`.

## Placing from the unplaced list

**Room -> Plan, Room -> Elevation and the 3D tab each carry a slim line of the
cabinets and standalone panels with no placement** (`renderUnplaced`); never an
attached panel, which stands where its cabinet puts it; nothing without a room.
Drag a chip onto a wall. The same bargain as every drag: one `/api/drag` on the
press, listening before it lands; the pointer onto a wall — the plan's nearest
track, the elevation's `.etrack`, or in 3D the wall under the cursor
(`V3D.wallAt`: over the floor, the nearest wall, standing); the item held by
its middle; the nearest snap the engine named within tolerance — in the
elevation and 3D the elevation drag's own rule, factored out as `elevSnap` so
the two cannot disagree; in the plan z 0, as the Placements table puts it. The
drop writes one placement where it was released, snapped, runs a corner unit
into its corner (`cornerFollowUp`, as the table does), selects it and
recomputes, so overlaps, clashes and every other check are the engine's answer.
The Placements table's wall picker, which lands an item clear of its neighbours
(`free_x`, E8), is unchanged.

## The 3D view

**A drawing, and nothing else** (Part F, 23 September 2026). `cabinetgen/scene.py`
builds the scene on the server and `app/view3d.js` only draws it: it extrudes
the outlines it is given, turns a door by the angle it is given, and picks the
nearest snap from a list it is given. None of `engine`, `validate`,
`export_plaza`, `nest`, `room` or `store` imports `scene`; `check_scene.py`
fails if one ever does, and `check_colour.py` holds `scene.py` to no colour
literal and `view3d.js` to its one `PAPER` block of paper colours (and, since
29 September 2026, its `LOOK` block of light and surface figures, which
states no colour). The only thing the browser works out for itself is the
camera.

### What is drawn, and what is not

Every board `room.solid_parts` draws — sides, top, bottom, fronts, a blind
corner's flush panel, a mitre's construction, independent panels — each
`Part` taken into world plan coordinates through `room._placed_frame` and
raised by `carcass_z`; plus the **backing board** (`room.back_part`, kept OUT
of `solid_parts` so the Finish view does not move, positioned by
`back_face_from_front` and sized by `back_size`, only where the engine cuts
one — not on a mitre); plus the **plinth boards and fillers that were chosen**
(`room.plinth_solids`, `room.filler_solids`), where the plan already draws
them. **Not drawn, by ruling: legs, hinges, handles, worktops** — their
positions are not modelled and nothing is guessed onto a drawing; the legend
says so (`scene.NOT_DRAWN`). Shelves and supports have been drawn since 27
September 2026, and **drawer boxes and runners since 28 September 2026**
(`room.drawer_parts`, off `room.drawer_layout`: two sides, a front, a back and
a base per drawer, tied to their cut-list lines; an inner drawer's face with
its box; each runner as two grey blocks a side since 29 September 2026 — the
outer channel, role `runner_outer`, fixed, and the inner member,
`runner_inner`, a lighter grey, sliding with the box — board `''`,
"hardware — a runner is bought, not cut", behind the **Runners** toggle). A base unit therefore stands visibly on
nothing at leg height where no plinth board was chosen; that is the truth.
An ell, a bespoke cabinet or an entered non-rectangular outline is its
footprint as one solid, with no fronts, as `solid_parts` rules.

**The room**: the floor polygon, each wall as a single-sided plane from the
floor to the ceiling facing into the room — so a wall between the camera and
the room is simply not drawn, which is the "nearest wall hides" with no
special code (Walls: auto / all / none) — openings as holes, obstructions as
warning-colour boxes (`proud` > 0) or markers, never hidden. An unmeasured
ceiling stops the walls `scene.DRAWING_MARGIN` (300) above the tallest item
and the view says the ceiling is not measured. **No room**: the cabinets
stand on the Run's own layout (`render.run_layout`, shared with
`elevation_svg` byte for byte), panels not among them — a panel has no place
in a line of carcasses — and a banner says there is no room.

### The scene payload (`/api/scene`)

Separate from `/api/compute` for the same reason `/api/plan` is: a view change
costs a redraw, not a re-nest. Read-only with respect to the job (pinned). Per
part: `id` (`"<number>:<role>:<n>"`, stable across calls, keyed by cabinet
number never index), `cab`, `role`, `index`, `board`, `outline` (world plan
mm), `z0`/`z1`, `grain` (a world unit vector, only to lay the picture),
`line` (the cut-list designation, found by role, board and finished size —
zero unmatched on every template cabinet in every job, pinned — or a reason:
`footprint only — ell / bespoke`), `layer`, `hinge` (axis as two world points
and the turn with its sign, off `room.door_hinges`, the same rule as the plan's
arcs and the elevation's marks), `pull` (a drawer face's — and since 28
September 2026 its box's — direction and the runner's TRAVEL, off
`drawer_layout`: its length on a full-extension runner). Per cabinet a hash of its parts, so the browser rebuilds
only cabinets that changed, and `room.geometry`'s width, height and depth for
the dimension lines. Looks are sent once per board off `render.board_look`,
the picture URL only on a grained board (`Fills.textured`'s rule) with
`render.PICTURE_TILE_MM` — a drawing constant, 160, what 40 px comes to on a
wall elevation at its usual scale; an SVG has no real-world tile size, so the
figure had to be stated once. Overlays: the swing and pull-out envelopes the
plan hovers with their height range and `room.clashes`' verdict, the overlaps,
and each cabinet's issues from `validate` with the check id.

### Light, surface, picture, selection (Round 1, 29 September 2026)

**Round 2 (29 September 2026) re-balanced this**: environment 0.7, the key
above and in front at `LOOK.key` 1.4 (the irradiance on a front), shadows,
contact shadows, ambient occlusion, a board in its picture multiplied by
white, fronts outlined in every mode, the Cabinets tab's view with no
selection outline, and a room of tiles and plaster — see the Status entry.
What follows is Round 1 as built.

**Lighting is physical.** An image-based environment — a neutral grey box,
ceiling 1.2, walls 1.0, floor 0.5 (`LOOK.sky`), pre-filtered once through
`PMREMGenerator`, turned so its ceiling is our +Z — gives the diffuse light
and the reflections; one directional key at `LOOK.key` 0.4 gives the form;
`NeutralToneMapping` at `LOOK.exposure` 1.0 maps it to sRGB without a tint.
Exposure is set so a plain board's front reads its swatch: GREY and the
BROOKHILL fallback within 1 unit, white 241 (Neutral's shoulder — see the
Status entry, and the trade-off ruled there). three's `RoomEnvironment` was
measured and rejected (3.9 : 1 across the horizontal directions). No
hemisphere light.

**Surface**: `MeshPhysicalMaterial`, `LOOK.board` (roughness 0.45,
clearcoat 0.12 / 0.5), one material per board shared by every part in three
variants (solid / ghost / x-ray, `boardMaterial`), tapes the same in their own
board (`tapeMaterial`), runners grey `MeshStandardMaterial` (`runnerMaterial`);
`V.materials` is the cache, `dropLooks` empties it of boards the job no longer
carries, `refreshLooks` updates a board whose colour or picture changed in
place. **Picture**: fetched once per board (`loadPicture`), one rotated clone
per (board, turn) sharing the image (`pictureFor`), anisotropy at the
renderer's maximum, sRGB, tiled at `PICTURE_TILE_MM`; a material carries no
map until the picture lands, so the colour shows meanwhile and on a failure.
**Selection**: an outline (`outlineMesh`), fat lines from `LineSegments2`
(vendored, `app/vendor/three/addons/lines/`), `LOOK.outline` 2 px accent
selected, 1.4 px `PAPER.hover` hovered, `DoubleSide` because the mirrored root
would cull them; no emissive on any board — the obstruction's warning glow is
the only emissive in the file (`check_colour.py`). **Edges**: `LOOK.edge`,
opacity 0.55 at a 20° threshold; every paper line `toneMapped: false`.
**Room**: `LOOK.room` roughness 0.9, `LOOK.grid` 0.22 / 0.4, the background
gradient `PAPER.bgTop` / `bgBottom` as an sRGB canvas texture. Pinned in
`ui_check_3d.py --stage look` (the face pixel within 8 of the swatch, and
unchanged when selected); the four views before and after are
`tools/ui_shots_3d.py`'s.

### Room frame and render frame

`room.py`'s world (X right, Y into the room from wall A, Z up; the plan drawn
with no flip) is **left-handed**. Drawn as it stands in a right-handed renderer
the room is its mirror image — facing wall A from inside the room its x ran to
the left, and every door hung on the wrong side. So every solid lives under a
root group that negates Y, and `toRender` / `toRoom` in `view3d.js` is the one
place the two frames meet: points and vectors from the payload go in with Y
negated, the camera, the raycasts and the labels work in the render frame,
and what the checks read back (`project`, `unproject`, `bounds`, `camera`)
is given in the room frame. The server's numbers are untouched.

### Navigation

Left-drag orbits about the point pressed on (raycast on the press, the orbit
point set before camera-controls sees it, a pivot dot while orbiting; nothing
hit keeps the current pivot). Right-, middle-, Shift+left- and Space+left-drag
pan at that depth. The wheel, Ctrl+wheel and a trackpad pinch (a wheel with
ctrlKey set) zoom about the point under the cursor: **this module's own**, a
scaling of the camera about that point — exact by construction, clamped never
to pass through it — because camera-controls' dolly-to-cursor holds the
target's depth plane still and reads the target as the screen centre, which
drifts on a nearer surface and breaks the moment an orbit pivot is set
off-centre. camera-controls' `fitToBox` rounds the rotation to the nearest
axis, so Fit projects the box's corners into the camera frame itself. Home
looks from the side the runs face (the walls' inward normals weighted by what
stands on them). `1`-`9` are face on to wall A, B, C… in orthographic, the 3D
twin of the wall elevation; `P` switches projection keeping the size at the
pivot. The view cube carries the wall letters. Render on demand: a loop runs
only while something moves and stops itself — started by the input, never by
camera-controls' `wake`, which is only raised from inside `update()`. Camera
per job per session, never saved; a newly loaded job opens at Home.

### One selection, one editor

`S.sel` is the one selection. `selectCabinet(i, {isolate})` splits selecting
from isolating: the cabinet table, Add, Duplicate and the 3D item list isolate
(how a buried item is reached); a click in the plan, a press in the elevation
and a click in 3D select **without** isolating, and isolate follows the
selection while on. The single `#editor` is **moved** into whichever tab's
dock is showing — Cabinets, a new column beside the plan on Room, and 3D —
never cloned; its listeners are delegated on the element and travel with it.
The dock collapses to a strip, resizes by dragging the strip, and remembers
both per viewer in `localStorage` behind `try/catch`. The selected cabinet's
own issues sit at the top of the dock, each a link to the Validation tab.
The part card shows a clicked part's cut-list line read from the compute
reply by the `line` the scene gave, with **Show in cut list** landing on that
row; a part with no line says why. Layers in 3D are the plan's `S.layers`;
the 3D Isolate toggle is the plan's isolate. Snapshot saves the view as a PNG
through `/api/snapshot` into `output/<job>/snapshots/<job>_3d_<n>.png`,
numbered in that folder, never overwriting; an export never touches
`snapshots/`.

### Moving things in 3D (F6)

A selected, placed item shows an arrow along its wall, an arrow up, and for a
panel an arrow out from the wall. Dragging an arrow moves it on that axis
only; a left-drag on the part itself still orbits. The press makes one
`/api/drag` call, listening before it awaits and replaying the last move and a
release once the model lands — the exact shape of `moveDrag` / `finishDrag`.
The pointer is projected onto the axis (the point on the axis nearest the
cursor's ray, camera maths), the grab offset held by construction, and the
nearest candidate within `Standard.snap_tolerance` taken, ties to the nearest
neighbour along the wall; z candidates are filtered by the stretch they apply
over, and an underside at or below leg height is "on the floor". The drop
writes `Placement.x`, `.z` (and `.y` for a panel) and nothing else; Esc
restores. No moving onto another wall in 3D, no rotating.

## Drawings

### Finish and Line

**Ruled 23 September 2026, replacing the 22 September white-and-grey Line
view, which was a misreading.** A two-way toggle in the elevation header, Line
first and the default. Both draw a wall's OWN cabinets identically — colour,
pictures, doors, drawers, hinges, dimensions. They differ only in the runs on
the walls either side:

- **LINE** — grey outlines end on, labelled "B: 11, 12, 13"; the drawing that
  used to be called Finish, unchanged.
- **FINISH** — what you would actually see standing in front of this wall: a
  true orthographic view, nothing unfolded or turned. `room.return_faces` takes
  every board of each neighbouring cabinet and placed panel (`room.solid_parts`),
  keeps the faces turned towards the viewer, projects them onto this wall's
  plane and sorts them furthest first; `render._finish_faces` paints them in
  that order in the board each is cut from, so a nearer end panel covers the
  carcass side behind it — no special case for panels versus sides. A face
  standing in front of every own unit it overlaps is drawn over them, else
  under. A face at an angle (a mitre door) is hatched and carries its real cut
  width; no hinges, swings or drawer sizes on a neighbour. Each item's number
  goes where some of it is actually seen, or nowhere (the wall label still
  names it). The legend names the neighbours' boards too.

A view setting: not saved in the job (`S.elevMode`), no geometry moves, and with
no room the wall elevation is `elevation_svg` byte for byte. The export writes
Line. `check_elevation.py` holds it on a copy of Test.json's corner — panel 12's
GREY and mitre 13's BROOKHILL seen from wall A, and with 12 gone cabinet 11's
own white end.

**`room.solid_parts` is drawing geometry, and nothing else reads it.** Sizes
come off `geometry` and the corner helpers; the one thing laid out rather than
read is where a leaf sits across its carcass (spread evenly — no cut list
says). Fronts stand proud at their board's real thickness; drawer faces stack
from the bottom as the elevation stacks them. An ell, a bespoke cabinet or an
entered non-rectangular outline is its footprint as one solid, with no fronts:
nothing is guessed onto a drawing.

### Faces in the plan

Every door leaf, drawer face and blind panel is a thin strip in front of its
carcass (`room.front_outlines`, lowest first so the top one shows), in its own
board — along a mitre's angled face, and on a blind corner where
`blind_spans` puts them. `pointer-events="none"`, so drag, select and the
hover swing are untouched. A wall unit's faces take its lighter dashed line
and ghost with it.

### Line weights

**One table, `render.WEIGHT`, for the plan and every elevation** (ruled 23
September 2026): walls 2, carcass 1, panels and faces 0.75, internal lines
0.5, items above 0.75, dimensions 0.5, a clash 2 and red. Every drawing is
`class="drw"` with `STROKE_STYLE` — `vector-effect: non-scaling-stroke` — so
zooming makes the geometry bigger, not the lines fatter. Coincident edges of
neighbours land on the same pixels with opaque strokes, so they read as one.

**Dashes only where they add real value** (Rudolf): a wall unit in the plan
(above the cut, `ABOVE_DASH` 4 3), an opening across a wall line in plan, a
neighbour's outline seen through this wall's units in Line, and an undecided
gap in red. Elevation cabinets are no longer told apart by outline — base, wall
and tall all at the carcass weight, undashed; shelves and the swing triangle
are solid.

**Plan labels never sit on each other** (`render._place_labels`): wall
lengths first (touch-ups, 3 Oct 2026), then cabinet numbers, then panel
numbers, then sizes, then gap widths; a label that does not fit moves a short
step on a leader, a size is dropped rather than moved. A wall's length moves
only out along its wall's normal (`LENGTH_STEP` 8 px, up to `LENGTH_STEPS`
16) and is never dropped; its box is the field the page lays over it
(`planLengths`, `planLenFit`: the input as wide as its figure, the label as
wide as its content, at every zoom).
Since round 2 (3 Oct 2026) it sits outside the wall, on its back, turned
to read along it (`data-cx` / `data-cy` / `data-rot` on the text, the field
turned to match); `plan_svg` draws again with the label boxes in its bounds
(`_grow`, `PLAN_LABEL_MARGIN`) when one would be past the edge; and one
lying over a cabinet, panel, face, wall or gap mark is on a white backing
(`rect.lenback`, `LABEL_BACKING_OPACITY`).

**A drawing is a read-only view of the model. Nothing reads one back.** The
colours, the grain lines and the legend are output; no check, no cut list and
no validation derives anything from them.

**Every fill is the colour of the board that part is cut from**, resolved
through the one function `render.board_look(job, board_id)` — colour, grain
and picture off `Job.materials`, and nothing else. There is no colour literal
for a board anywhere in `render.py`; `tools/check_colour.py` fails on one. A
door leaf is `Cabinet.door_board(i)`, a drawer face `face_board_of(d)`, a
carcass body `carcass_board`, a plan footprint `exterior_board` — the same
resolvers the engine cuts from, so the paper and the cut list cannot disagree.
A board nobody has coloured draws neutral (`model.NO_COLOUR`) and the legend
says "no colour set". That is never a warning: a colour changes no cut.

### Board pictures in the drawings

**A picture wins over the colour field, and only on a GRAINED board** (ruled 22
September 2026). `render.Fills` is the one place that rule lives, and every fill
in both elevations and in the legend goes through it — `Fills.of(look, vertical)`
gives back a hex colour or a `url(#...)`, and no drawing decides for itself. A
plain board keeps its colour even when it carries a picture: a photograph of a
flat white sheet says nothing the colour does not, and tiles into noise. No
picture, or nothing readable: the colour, exactly as before.

**The picture is TILED as an SVG `<pattern>`, and the tile is turned onto the
panel's own grain direction.** Board pictures are supplied with the grain running
vertically, so the turn is 0 or 90 degrees and never an angle worked out of a
photograph — that convention is the whole reason this is possible. A door and a
drawer face are cut with `Length` up the front, so neither turns; a panel asks
`_panel_grain_vertical`, and a grain running into the page is left as supplied
rather than turned on a guess. One pattern per board per direction, no more.

**The board's colour sits under the image inside the pattern**, so a picture that
does not load leaves the part its colour rather than a hole. That is not
theoretical — it is what you see when the SVG is opened somewhere its pictures
cannot be reached.

**A picture replaces the grain hairlines, it does not sit under them.**
`_grain_lines` is skipped wherever `Fills.textured` is true: real grain in a
photograph does not want fake grain drawn over it.

**The legend swatch takes the same fill as the parts.** A key to a drawing it
does not describe is worse than no key.

**On screen a picture is asked for over `/pictures/<name>`; an exported drawing
asks for the bare file name and the file is copied in beside it.** An export
folder gets opened, zipped and emailed, and the route would 404 the moment it
left the machine. `render.pictures_drawn(job)` is what says which files to copy —
`api._export_pictures` must not answer that itself, or the export and the drawing
become the two lists that disagree.

**The plan is deliberately left on flat colour.** A plan is a top view: you are
looking at a board's edge, not its face, so a face texture there would be saying
something untrue — and at footprint scale it reads as mud.

### The two dimension lines

**The top chain breaks wherever either run does** (22 September 2026). It used to
break only at the overheads, so a wall with one wall unit over a row of base
units dimensioned that unit and then handed over a single figure spanning every
cupboard past it — on `Test.json` wall A, `632 | 300 | 3068`. It is
`chain(hung + floor, wall.length)` now, so the top reads at the bottom's
resolution and still closes on the wall. A wall with no overheads still gets no
top chain at all: there is nothing up there to dimension and the bottom already
says it.

**The fill carries the board, not the layer** (20 September 2026). Since 23
September the elevation no longer marks the layer in the outline either — base,
wall and tall all at the carcass weight, undashed (see **Line weights**). The
plan dashes a wall unit `4 3`, above its cut, pinned in `check_room.py`. A
clash is red and heavy.

**Ink is computed, never stated.** A board colour is picked for the board, not
for the numbers that land on it, so `render.ink_on(fill)` takes whichever of
the dark ink and white gives the better contrast ratio, and `muted_on(fill)`
keeps the secondary text a step quieter without letting it vanish — a fixed
grey on a mid grey board was 1.04:1. Both clear 3:1 on every fill.

**Grain lines run the way the cut list cuts them.** `Length` is the grain
direction, and doors and drawer faces are both cut with `Length` up the front,
so both draw vertical lines. **Vertical on a drawer face is correct** (ruled 20
September 2026) — no note on the drawing, no change to the cut list, and never
raise it again. A plain board draws none, and neither does a board drawn in its
picture — see **Board pictures in the drawings**.

**The diagonals across a door leaf are the SWING, not the grain.**
`render._hinge_marks` draws the opening triangle with its point on the hinge
side, the standard elevation convention, paired with the hinge count underneath.
It has been read as grain at least once; the grain is the fine vertical
hairlines at 22 % opacity, or the picture.

**Only a hex value reaches an SVG fill.** A job file is a text file somebody
can edit, and a fill is written into the drawing as it stands, so `board_look`
puts every colour through `render._hex` and falls back to neutral.

**The run selects, it does not drag.** Its cabinets carry `data-cab` in a
`g.ecabg.erun`; there is no wall to move along, so a press selects the cabinet
and starts nothing. The run still ignores placements — it is the cabinet list
drawn side by side, not a view of the room. **Since 28 September 2026 the Run
is not in the UI or the export** — `elevation_svg` is an internal helper, the
no-room fallback of `wall_elevation_svg`; see the Status entry for the UI
restructure.

## Boards, tapes and grain

**`boards.json` in the repo is the board library.** It is shared through git, so
both machines see the same boards. `cabinetgen/boards.py` loads and saves it, and
the Boards tab is where boards are added, edited and ticked into a project. Each
record is a name, a tape token, a thickness, Grain or Plain, a last price, an
optional picture, whether it has edging and which kinds it offers, and its
colour. Every one of those is stated there and nowhere else.

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

**A board's id is editable, and changing it renames the board** (18 September
2026). The id is the material name on every panel cut from it, so it is upper
case, alphanumeric and short — `api.clean_board_id` shapes a typed one exactly as
`boards.next_id` shapes a generated one. A SAVED job keeps its own copy under the
id it was quoted with and does not move; the reply names those jobs. The project
open on screen does come along (`api.rename_board_in_job`), and is named in a
confirm before anything is written. No panel designation changes: a panel keeps
its name and changes what it is cut from. `DECOR` was renamed `BROOKHILL` this
way; `jobs/Test*.json` still say `DECOR` on disk and still price exactly as
before, which is the price capture doing its job.

**A former id keeps resolving: `model.BOARD_ALIASES`** (`{"DECOR": "BROOKHILL"}`).
`Cabinet.exterior_board` and the house `MATERIALS` say `BROOKHILL`, but the
frozen October fixture names `DECOR` literally on its bespoke and loose panels
while its template cabinets take the default. Without the alias those would be
two boards on two sheet piles and the 9-board benchmark breaks. `resolve_board`
maps an id the job does not carry onto the other name it does, either way round,
and the engine resolves every panel's board through it (bespoke and loose panels
as copies — the job is never touched). The benchmark therefore prints
`59 BROOKHILL`; the numbers are the October job's exactly. Do not "tidy" DECOR
out of the alias map, `YIELD` or `RATES["cut"]`.

Opening a saved job in the UI (`api.upgrade_former_ids`) shows a former id under
the current one **only when the job never captured a price for it** — a
pre-library bare-string record, like both Test files. A captured record keeps its
old id. The file on disk is untouched until saved, and a toast says so. The
Boards tab lists `Test.json (as DECOR)` against BROOKHILL, and refuses to delete a
board a saved job uses under a former id.

**The library's BROOKHILL edging token is `BROOKHILL`, deliberately** (ruled 18
September 2026). New cabinets generate `2mm BROOKHILL` / `PVC BROOKHILL`. The
October job's sheet said `PVC WOOD` / `2mm WOOD`; Plazaboard keyed it as
Brookhill (`PVC BROOKHILL`, `2MM BROOKHILL`; the quote `EDGING-IMP BROOKHILL`),
and since 28 September 2026 the job reads BROOKHILL too — the house record's
token is BROOKHILL, and its typed WOOD literals resolve through
`model.resolve_edging`.

**Yield and cut rate are read off what a board IS, not off its id.** Both used to
be dicts keyed `MEL` / `DECOR` / `BACK`, so a renamed or newly added board fell to
a house-average yield and — worse — a cutting charge of R0. `export_plaza.cut_rate`
goes by thickness (the masonite saw takes the 3 mm, the beam saw the rest) and
`board_yield` by grain and thickness, with the three original ids still pinned to
their measured figures so the October benchmark does not move.

### The boards on a cabinet

The three chosen in **Structure**, which everything else falls back to:

- `carcass_board` — sides (01), top (02), bottom (03), supports (04), shelves
  (05), dividers (09), and the plinth board that covers its legs.
- `exterior_board` — doors (07), drawer faces (20), exposed end panels (08).
- `back_board` — the backing panel (06), and the drawer base (17) when it is the
  grooved 3 mm one, because that is the same thin sheet.

And four more, each `None` for "follow Structure" (18 September 2026), so every
job written before them cuts exactly what it was quoted:

- `drawer_carcass_board` — drawer sides (18), fronts (19) and a **housed 16 mm**
  base (17). Follows `carcass_board`.
- `drawer_face_board` — drawer faces (20). Follows `exterior_board`.
- `Drawer.box_board` / `Drawer.face_board` — **per drawer** (18 September 2026),
  so one drawer in a stack can take a different finish. `None` follows the two
  cabinet-level fields above, which follow Structure. This is what the editor
  sets now — one column each in the drawer table; the cabinet-level pair is no
  longer offered in the UI and is only read as a fallback from older job files.
  The engine groups drawers by board as well as size, so an odd drawer comes out
  as its own line (`418a` / `418b`). Its box edging follows its own **Box
  edging** board and thickness (`box_edge_board`, `box_edge_kind`), then the
  section's (`drawer_box_edge_board` / `_kind`), then the exterior board in
  PVC (29 Sept 2026) — no longer the box board. Since the Drawers redo the
  cabinet-level pair is offered again, as the section's Box board · Face
  board, and a drawer's own choice is its **differs…** sub-row.
- `door_boards[i]` — one per leaf, `""` for the exterior board. Two leaves cut
  from different boards come out as two cut-list lines, told apart by
  `born_distinct` because the material is part of the signature it reads
  (`107a` / `107b`).
- `blind_board` — a blind corner's flush panel (08), `""` for the exterior
  board, which is the default because the strip beside the door is seen from
  the room (22 September 2026). See **A blind corner** under **Corner units**.

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

Drawer box sides and fronts (18, 19) and the housed 16 mm base (17) used to be
hardcoded `MEL` in the engine whatever the cabinet was cut from, and all the
validator could do was ask about it. They are a chosen board now, defaulting to
the carcass, so the box and its edging agree by construction and the warning is
gone. A board swap moves them with the carcass, which is why
`check_library.py`'s swap figures are 102 panels and 3 MEL boards, not 101 and 4.

### Every board attribute is stated on the Boards record

**Ruled 20 September 2026.** A board says whether it has edging at all, which of
PVC / 1mm / 2mm it offers, and what colour it is, and nothing downstream states
one. `Board.has_edging`, `Board.edging_kinds` and `Board.colour` are real fields;
`Board.offered` is the kinds in force, and `tape_name` / `model.tape_for` return
`""` for a kind the board does not offer rather than generating a name it will
never sell.

**The legacy rule is what keeps the benchmark still.** A record carrying neither
key reads as edged with all three — which is what every job quoted before the
tickbox was quoted with — so old jobs and the frozen October fixture do not move.
The same holds for `Job.materials` copies. `tools/check_edging.py` pins it.

**Unticking keeps data**, the same discipline as "Has doors" and "Has drawers":
Has Edging off keeps the kinds and the edging name in the file and merely stops
anything reading them.

**A needed edging the board does not offer is a CRITICAL**, tagged `EDGING`,
naming the cabinet, the board, the kind and what to tick. It blocks the export.
This bites in one place by design: carcass fronts are PVC in the **exterior**
board's colour, so an exterior board ticked 2mm-only leaves them with no offered
edging. That is the rule working, not a bug — choose another exterior board, or
tick PVC on it (the per-cabinet `carcass_edge` override that used to be the
escape hatch is no longer read, 28 September 2026). A missing edging *name* stays a WARNING with its
wording unchanged (`check_boards.py` pins the phrase "no name to build edging
from"); the two are different faults. A cabinet named by an `EDGING` critical
does not also collect the per-panel "edges specified but no edge material"
critical — one problem, one message.

**Colour is picked on the Boards tab and nowhere else.** `model.NO_COLOUR`
(`#d9d6cf`) is what a board nobody has coloured draws as, and the legend says
"no colour set" rather than guessing a finish. An unset colour is never a
warning.

**A 3 mm sheet is not something to build from.** `model.is_thin` uses the
threshold `export_plaza.cut_rate` already sorts by, so the dropdowns and the
costing cannot disagree about what a thin board is. The carcass, exterior,
door-leaf, drawer-face and drawer-box dropdowns exclude thin boards; the backing
dropdown lists only thin ones. A stored value that breaks the rule is kept,
flagged in the editor, and named by `validate._thin_boards`.

**No hardcoded edging anywhere, including supports** (ruled 20 September 2026).
A support row names a board — any board the project has selected — and one of
the kinds that board offers: `Support.board` and `Support.kind`. Both blank means
the row predates the control, and it is then read from its old `edge` and edged
exactly as that job was quoted: front-edged takes the carcass edging, and
white-edged resolves through `model.white_edge_board` — the project's board whose
PVC token is WHITE — rather than through a constant; a project with no such
board gives the row no name and the validator says why (`model.WHITE_EDGE` is
gone, 28 September 2026). `Test.json` cabinet 7 is
the case that proves it: a GREY carcass with three white-edged rows, which still
come out `PVC WHITE`. `board` and `kind` are written to the job file only when a
row actually names them, so a file saved before the control round-trips byte for
byte.

### Board pictures

**A board picture had never once displayed, and the path was never the problem**
(22 September 2026). The server served `/` and the API routes and 404'd
everything else, so `<img src="C:\Dev\CupboardApp\Pictures\Storm Grey.jpg">`
resolved against `http://127.0.0.1:<port>/` and came back 404. Taking the stray
quote characters out of the path changed nothing, because nothing was ever
being fetched. A `file:` src would not have helped either — every engine blocks
a `file:` sub-resource on an `http:` page.

**`cabinetgen/pictures.py` is the one answer to all three halves of it.** Where
a picture lives (`Pictures/`, flat), what is stored (`Pictures/Storm Grey.jpg`,
relative to the repo) and what a page asks for (`/pictures/Storm%20Grey.jpg`,
through `url_for`). No colour-literal rule as such, but the same shape: the
browser is handed `picture_url` off `/api/boards` as a derived field beside
`tapes` and `offered`, and never works one out from a stored path.

**It is copied in, not pointed at.** `boards.json` is shared through git, so an
absolute path in it is one machine's answer written down as if it were
everybody's — and a path typed by hand is a path somebody can mistype, which is
exactly how the quotes got in. Browse… and a drop both end at `install` /
`install_bytes`, which put the file into `Pictures/` — suffixing `-2` rather
than overwriting a different file of the same name — and hand back the relative
path. The field in the editor is **read-only**: there is nothing to type any
more.

**Two ways in, one route back.** Browse… is pywebview's native Open dialog,
opened by `/api/pick-picture` on the window `run_app.py` hands to
`api.set_window`. Under `--no-window` or in the browser fallback there is no
window, so the reply says `no_window` and the browser's own file input takes
over; that and a drop both go to `/api/drop-picture`. **A drop carries the
file's CONTENTS and no path** — WebView2 does not expose `File.path` the way
Electron does, and pywebview 6.2.1 has no file-drop event — so the bytes are
what is sent, and that is not a limitation worth working around. Cancelling the
dialog is `cancelled`, not an error, and says nothing.

**A stray drop anywhere else on the window is swallowed.** The browser's default
is to navigate to the dropped file, which would throw the app and the unsaved
job away.

**The route is a basename lookup into one flat folder.** The name comes from a
file somebody can edit, so it may not name a parent, a drive or anything outside
`Pictures/`, and the extension has to be one of `pictures.TYPES` — which also
keeps the route from becoming a way to read the repo. `safe_name` flattens a
traversal rather than refusing it.

**On save, a picture that names no readable image is refused, and says so.** Not
dropped quietly: a picture that silently does not arrive is the whole bug. A
stored absolute path inside `Pictures/` is squared up to the relative form on
the way through, so an old record migrates the first time it is saved — and
**`url_for` draws it either way**, so a saved job carrying the old absolute form
still shows its picture without being rewritten. Files on disk change only when
saved.

**A `data:` URI passes through all of it untouched.** It is already the picture
rather than a pointer at one.

**The grain must run VERTICALLY in the source image, and an upload says so when
it does not** (ruled 22 September 2026). That convention is what lets a drawing
turn the tile onto each panel's length direction through 0 or 90 degrees instead
of trying to detect an arbitrary angle. `pictures.grain_verdict` is the one
answer: gradient energy along x against along y, so it measures the direction the
texture is COHERENT in and knows nothing about wood. It **warns and never
blocks** — the picture is already in `Pictures/` by then and stays there, the
same bargain everything but a critical strikes. A picture with no texture to have
a direction, or none decisive enough to name, is **not asked the question and
nothing is said**: a warning nobody can act on is worse than silence.

**The browser samples and the app judges.** Decoding a JPEG is the one thing the
browser can do that this app cannot — it has a decoder and the app has no
third-party dependency, and taking one on for an advisory would be a large price.
So the browser draws the picture into a 64-square canvas, which area-averages it,
and posts the luminance to `/api/picture-grain`; the verdict is reached in
`cabinetgen.pictures`, so there is one answer and it is testable without a
picture at all. **Area averaging is not an incidental detail**: point-sampling
the real 1135-wide `Brookhill.png` aliases the grain away and the direction stops
being readable (+0.08, indistinguishable from noise), while area-averaging gives
+0.29 and holds from a 32-square grid to a 128-square one.

`tools/check_pictures.py` holds the lot: the cleaning, the URL, the traversal,
the refusals, and that `boards.json` names nothing absolute. A saved job is
reported on and never failed — it is a price capture, and it is not rewritten
under the operator.

### Where the exports land

**`output/`, one folder per job** (renamed from `out/` on 22 September 2026).
`/api/export` already wrote `out/<job name>/`; `tools/regen_check.py` was the
one thing dropping loose `nest_*.svg` at the root, and it writes
`output/wardrobe_oct2025/` now. So one job's files can never land on another's.
`api._safe_name` is still what keeps a job called `../x` from writing outside
it. The old `out/` stays in `.gitignore` so a stale folder left on a machine
does not turn up as untracked.

**Inside the job folder, one subfolder per kind of file** (28 September 2026):

| Folder | What | Written by |
|---|---|---|
| `cutlist/` | `<job>_<BOARD>.csv`, `<job>_accepted.txt` | `/api/export` |
| `nesting/` | `nest_<BOARD>.svg` | `/api/export`, `tools/regen_check.py` |
| `drawings/` | `<job>_plan.svg`, `<job>_elevation_<wall>.svg`, the board pictures they name | `/api/export` |
| `snapshots/` | `<job>_3d_<n>.png` | `/api/snapshot` only |
| `_previous/` | the last export's `cutlist/`, `nesting/`, `drawings/`, as they were | `/api/export` |

An export **clears and rewrites**: `api._retire_export` moves the three export
folders into `_previous/` (replacing whatever it held — one level, nothing
older), then the export writes fresh. `snapshots/` is not export output and an
export never touches it. `api.EXPORT_DIRS` names the three. The pictures go in
`drawings/` because an exported SVG asks for them by bare file name. The
Playwright scripts' screenshots are under `output/_checks/<script>/`, not
beside the job folders.

### A support row: cut from, and edged in

**Ruled 20 September 2026.** A support row asks two separate questions and they
used to be one. `Support.cut_board` is what the rail is **cut from** — any board
the project carries, blank meaning the carcass board, which is what the engine
has always cut a support from. `Support.board` is only the **edging colour**, and
`Support.kind` the edging kind. Before this the single Board column set the
colour alone, so picking the white board to get a white edge read as asking for a
white rail, and did not give one.

The rail carries its own board's **grain**, so a support cut from the grained
board locks like every other panel off it.

**Defaults:** the edging kind lists only what the colour board offers; the colour
list only boards that offer the chosen kind; and a new row's colour follows the
board it is cut from — its own edging.

**Migration, output unchanged.** A row with nothing stored is read from its old
`edge`: cut from the carcass board, and **front-edged takes the exterior board's
colour** (PVC in the exterior colour, the 14 September rule), **white-edged takes
the project board that yields `PVC WHITE`** via `white_edge_board`, and **none
stays none**. The October job and both Test files are byte-identical through it —
`snapshot.py --compare` proves it, and `check_edging.py` pins each case.

### The editor paints itself, and nothing reaches disk unasked

**Every dependent surface refreshes on every compute** (20 September 2026).
`renderEditor` used to leave the DOM alone when the selection had not changed and
update a fixed list of readouts, which is how "Ordered as" went stale — and it
was never only that: every dropdown whose OPTIONS depend on the boards kept
whatever the library said when the section was last built, so changing a board's
edging and coming back still offered the old kinds.

**So it is rebuilt every time — and PAINTED, not replaced** (20 September 2026).
Rebuilding it with `innerHTML` threw away 49 of the editor's 59 controls on every
compute: measured on Test.json cabinet 4, every control in Structure, Drawers and
Supports was a new object afterwards and a focused `<select>` was no longer in
the document at all. A native dropdown belongs to the node it was opened on, so
that closed it — the twitch — and took the caret, the hover and the scroll with
it. Worse, it never stopped: `renderDrawers` calls `solveStack`, which wrote the
engine's heights back and scheduled another compute unconditionally, so a drawer
cabinet sitting untouched on screen computed about three times a second for ever
and lit the unsaved-changes marker on a job nobody had edited.

`paint(box, html)` applies the new HTML to the DOM that is already there: a node
that has not changed is left alone, a changed value is written into the control
in place, and only a control that has genuinely changed shape — or gone — is
replaced. Two rules make it safe. **A focused control is never touched**, not its
options and not its value (focus is what an open dropdown is, and what is being
typed into); it catches up when focus leaves it. And **a slot div belongs to its
own render function** — `sectionHTML` emits it empty and `data-slot` keeps the
paint out of it. `solveStack` now schedules a compute only when a height actually
moved. Nothing in the editor attaches a listener to a control — they are all
delegated on `#editor` — so reusing a node cannot stack a second handler on it.

The flags that used to force a full rebuild (`S.selRendered = -2` on a board
change, a tickbox, a renumber, a drag) are gone: all they could do now is destroy
the control being used.

**The cabinet table is painted the same way**, through the same `slot()`
stand-in. It holds no dropdown, so nothing there was twitching, but it was being
rebuilt three times a second alongside the editor and taking the hover and the
focus ring with it.

**Save is the only thing that writes** (ruled 20 September 2026). A saved job is
the price capture, so an experiment must not be able to move one by itself. The
`unsaved changes` marker says when the screen and the disk disagree, and New,
Load, the fixture button and closing the window all ask first.

### Deleting a project

`jobs/_deleted/`, never `unlink`. A job is a quote somebody may want back, and
picking the wrong one has no undo otherwise; a second delete of the same name is
stamped rather than overwriting the first. The job **open on screen** cannot be
deleted — that would leave the editor with nowhere to save back to — and
`Test.json` says what it is before it goes, because half the `check_*` scripts
run against it. Every other job the checks read is frozen under
`tools/fixtures/`, so deleting a project can no longer break a check.

### Grain is listed, never judged

`Length` IS the grain direction on a grained board and a locked panel cannot be
turned by the nester, so grain is said out loud rather than shown as a `1`. The
cut list's Grain column reads `locked along L <n>` or `free`. A board swap lists
every panel that locks or comes free, with its size, board and direction, and
**what the lost rotation costs**: the same panels re-nested with grain cleared,
so the price of the lock is separated from the price of the board. On the October
job, swapping MEL into Brookhill costs **one extra board, R1,066**, purely for
the lock. The app does not judge whether a direction is the right one to look at
— that is not something it can know, and the list is there to be checked.

### Swapping a board moves every use of it

**Ruled 20 September 2026**, overriding an earlier choice to leave hand-specified
panels alone. A swap moves every use of the old board in the open project: every
field `Cabinet.board_refs` knows about, every bespoke panel and every loose
panel. A board being swapped out must not still be named anywhere, or the cut
list quotes a board the project no longer carries. **No panel is renamed** — it
keeps its designation and changes what it is cut from (the 14 September rule),
pinned on a full merge of the October job where 254 panels change board.

**A bespoke or loose panel stores `grain` and `edge_material` as TYPED values**,
because `generate_job` is read-only with respect to them. Moving the board alone
would leave a woodgrain panel at grain 0 — W8/D9 exactly, the 60 décor panels
Plazaboard's counter caught and we did not. So a swap re-derives `grain` from the
new board, and maps `edge_material` **by kind**: a panel edged in the old board's
PVC comes out edged in the new board's PVC. An edging that never matched the old
board is a literal somebody typed, and is left alone. If the new board does not
offer the kind, the edging is cleared and the bands are left, so the panel still
says it wants edging and the `EDGING` critical fires. On the October job this is
9 panels, all of them grain 0 on a board that locks grain.

**The preview reports what the swap does to the VALIDATION**, not only to the
cost: new criticals and warnings, the ones that would go away, the panels each
board gains and loses, and which hand-specified panels were re-derived. A swap is
how a design gets previewed, so a problem it creates has to be on screen before
anything is written.

**`engine.resolved` hands a bespoke or loose panel back as the very same object
the job holds.** The swap re-derives those records in place, so the "before"
board and edging must be read *before* any of it — a diff taken afterwards
compares the new values with themselves and reports that nothing moved. That was
a real bug; `check_swap.py` pins it.

**Swapping onto a board the project already carries MERGES the two**, and
swapping back does not undo it: nothing records which panels used to be which.
The confirm step says so.

**A grain-locked panel is measured as it will be cut**, not turned
(`validate._panel_fits_board`). One that only fits rotated fits on a plain board
and does not fit on a grained one, and the nester would drop it without a word —
which is what a swap onto a grained board can produce. A panel too big whichever
way round it goes keeps its original wording, so the October job's `1808` reads
exactly as it always did.

### One source for "which fields hold a board"

**Ruled 20 September 2026.** `Cabinet._board_slots` is the single list of every
place a cabinet names a board, and `Cabinet.board_refs()` / `map_board_refs()`
are what everything reads. Four hand-written lists used to answer this question
and they disagreed: a swap moved only the carcass and exterior, un-selecting
checked only those plus the drawer boards, `boards.scan_jobs` missed the back,
the door leaves and the edging boards, and the validator had its own list again.
So a board could be swapped or taken out of a project with a cabinet still
pointing at it.

Each slot carries a **label a message says out loud** — "door leaf 2 board",
"drawer 1 face board" — so a refusal names the thing to go and change.

A slot is marked **hand-specified** when it is a bespoke panel's material, and
rename and swap differ on it deliberately: a *rename* says "this board is called
something else now", so every reference follows it, bespoke included, or it
points at an id the library no longer has; a *swap* says "cut this from a
different board", and a bespoke panel's material was typed out panel by panel.
On the October job that difference is eight panels and R848 of Brookhill.

`boards.cabinet_board_ids` is the one deliberate repeat — it reads raw JSON,
because a job file that will not parse has to be reported by name rather than
skipped. `tools/check_single_source.py` holds the two together **by reflection**:
a `_board` field added to `Cabinet` and not to `_board_slots` fails that check
rather than becoming the fifth list that disagrees.

**A check never reads live workshop data to pin a fact about the past.** It has
bitten twice, the same way both times.

`check_library.py` builds its own in-memory library fixture instead of reading
the live `boards.json`. It used to read it, so renaming `MEL` to `WHITEMEL` — an
ordinary thing to do in the Boards tab — made `B.find(lib, "MEL")` return None
and the file died at line 184, with about thirty checks after it silently not
running. `boards.load` and `boards.save` resolve `LIBRARY` at call time rather
than binding it as a default argument, so a check can point at a fixture without
writing the workshop's real library.

**`tools/fixtures/Test_Build_pre_library.json` is the same lesson for a job file**
(21 September 2026). Three checks pinned "a job written before the library still
names DECOR" against the LIVE `jobs/Test_Build.json`. Upgrading that job in the
Boards tab — again, an ordinary thing to do — renamed its DECOR to BROOKHILL and
broke all three. The upgrade was sound: the same 27 cut-list lines, the same
designations, sizes and total, with only the board id moving on five of them,
which is the rename and the price capture working exactly as designed. But a
fixture has to sit still, so the pre-library version is frozen here, taken
verbatim from `jobs/Test_Build.json` at the baseline commit (7daedb7): bare-string
materials, no `boards` key, `decor` rather than `exterior_board`. Nothing in the
app can reach it. `check_boards.py` and `check_library.py` read it by name.

The one half that still reads the real folder is `scan_jobs(jobs/).unreadable`,
and deliberately: that a job file will not parse has to be found live and
reported by name. Whether a board is found under a former id is asked of the
frozen copy, because that is a fact about the scan, not about what happens to be
in `jobs/` today.

### Tapes are generated, not mapped

Three tape names come off **one token per board**:

```
PVC <token>    the thin carcass tape
1mm <token>    exterior option
2mm <token>    exterior option
```

**The token is its own field, not the board's name.** Edging names are decided
per order — there is no fixed Plazaboard edging name to look up for a board (ruled
18 September 2026; the October sheet's "WOOD" was that order's choice for a
woodgrain board, not a catalogue rule — and Plazaboard keyed it as BROOKHILL
anyway). The token is what this workshop wants on
the order, and keeping it separate stops a long board description such as
"BROOKHILL FUSION CHIP" landing on an order as an edging name — D6/W10 in the
other direction, where a board name reached an order as a tape. A board with a
blank token generates off its name, which is right for a board whose name is
already the short one; a board with neither generates nothing and the validator
names it rather than inventing a tape.

Colour derivation is unchanged: **front edges take the EXTERIOR board, every
other banded edge takes the CARCASS board.**

| Field | Derived as |
|---|---|
| `carcass_edge` | PVC in the **exterior** colour. Fronts of the sides, top, bottom, shelves, dividers and front-edged supports — shelf and divider fronts match the front, not the box (ruled 14 Sept 2026). Not selectable anywhere; it follows the exterior board. |
| `door_edge` | `door_edge_kind` (1mm / 2mm) in `door_edge_board`'s colour. Doors and exposed ends. |
| `drawer_face_edge` | `drawer_edge_kind` in `drawer_edge_board`'s colour. Drawer faces. |
| `drawer_box_edge` | The drawer's **Box edging** thickness (`box_edge_kind`, PVC / 1mm / 2mm — R1, 29 Sept 2026) in its board's colour (`box_edge_board`), each else the section's, else PVC in the **exterior** board. Drawer sides and fronts only — supports carry their own Edging Colour. |

**Edging is one control per section, and it is called edging, not tape** (18
September 2026). Doors and Drawers each carry a thickness dropdown and a colour
dropdown, and the colour is a *board*, so the name is still generated from that
board's token and a board name still cannot reach a real order as a tape. Each
half is `None` for "follow the cabinet", and the fall-through is
drawer → door → `Cabinet.exterior_tape` / `exterior_board`, so a job quoted
before the two were separable is edged exactly as it was quoted. **The flat
string overrides (`carcass_edge`, `door_edge`, `drawer_box_edge`) are retired**
(28 September 2026): kept in a job file that carries them, so it round-trips
byte for byte, and read by nothing — the edging is always the Boards-tab Edging
Name of the board picked, so the screen and the order cannot disagree.

**An Edging Colour dropdown shows the board's Edging Name**, not its id
(`model.edging_label`, the `edging_label` field of each board on
`/api/compute`): `Grey`, `BROOKHILL`, and `WHITE (WHITEMEL)` / `WHITE (BACK)`
where two project boards share a name. The stored value is the id.

**`Cabinet.exterior_tape` is 1mm or 2mm, per cabinet, and has no dimensional
effect whatsoever.** It is the fallback the two section choices fall through to.
We supply finished sizes and Plazaboard deduct the tape, so the two cut
identically and differ only in what is ordered and what it costs. There is no
deduction logic anywhere and none is wanted.

The resolved edging names show in the editor beside each control and as a legend
on the elevation (`render.tape_legend`), naming the cabinets when they disagree —
a door edged in the carcass colour looks right on paper and wrong in the room.

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

**Everything else about a board comes from the library** (ruled 18 September
2026). The library is where a board's details are edited, so the project on
screen uses them: name, edging token, thickness, grain and picture
(`api.LIVE_FIELDS`). `api.refresh_from_library` brings the job's copy up to date
when a saved job is opened (`job_load`) and when a board is saved in the Boards
tab (`board_save`, for the project open on screen) — so a changed description
shows in Structure, the cut list and the quote at once. **Price is the one field
kept**: the job's captured figure, or for a pre-library job the rate-card price,
written down before the name changes so a new name cannot lose it (the rate card
is keyed by name). The October fixture button loads the frozen quote as it was
and is never refreshed. Files on disk change only when saved.

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
| standard.py | `drawer_box_width`, `drawer_front_length` | 180-195 | drawer box width (opening less the runner's clearance) and front / back length (less two `board_t` box sides), via `internal_width` |
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

## Panels

**An independent panel is a part, not a cupboard.** It is cut, numbered, costed
and nested like everything else, and it belongs to no carcass. Several of them
make a bulkhead — a front, an underside and an end cap each side — and each is
its own numbered item, which is why they are numbered in the same series as the
cabinets rather than listed apart.

**A panel is a `Cabinet` with `kind="panel"` and a `PanelSpec`.** That buys the
numbering (`store.next_number`), the save and load, the cabinet table, the
`Placement` record and the one `generate_job` loop — which is where the cost,
the nesting and the CSV come from for nothing. What it costs is that every place
assuming "a cabinet is a box with doors" has to say what it does about a panel.
`tools/check_panels.py` is where they are held to it.

**`kind` is the only thing that says panel, and `template` is never rewritten.**
The brief proposed carrying it on `template` as well. It cannot be: switching an
item back from Panel would then have to put `template` where it was, and there
is nothing to put it back from — October cabinets 3 and 5 are
`template="standard"` carrying hand-specified extras, so "it has bespoke panels,
therefore it was bespoke" is wrong, and being wrong there rewrites a real cut
list. Off `kind` alone a round trip loses nothing: switch to Panel and back and
every field is where it was, template included. Same bargain as the tickboxes.

**Code 08, role "Panel"** (`model.PANEL_CODE`, ruled 20 September 2026, Q2).
The CSV writes the designation, `Panel.label` — the digits, `1508` — in its
Customer Number column (28 September 2026; `Component` is Plazaboard's item
number), and never `CODES[code]` or `Panel.role`, so a new code would need
their sign-off exactly as 10 and 11 still do, and would say nothing on the order
that 08 does not. The role is what tells a panel from an exposed end in the
app's own cut list. One constant, so a code they do sign off later is one edit.

**What is typed, and what is derived.** The operator types a board, an
orientation, two FINISHED extents and how many long and short edges are banded.
Everything else is `engine.panel_of`'s: which extent becomes the cut list's
`Length`, whether the panel locks, and what its edging is called. The editor's
preview line is that answer read back, not one the browser assembles.

**`Length` IS the grain direction, so it is not simply the longer side.** On a
grained board the extent the grain runs along becomes the length whether it is
longer or not, and `grain=1` locks it. On a plain board the longer extent is the
length and the nester may turn it. Which means **long and short edges are not
`edge_l` and `edge_w`**: a panel cut across its grain has its long edges running
the width, so the two are mapped rather than assumed equal. Pinned in
`check_panels.py`, both ways round.

**Three orientations, and the third extent is always the board's thickness** —
which is why a panel never states one, and why `room.geometry` needs the job's
materials to answer for it (`geometry(cab, std, materials)`; nothing else reads
that argument, because the engine reads the boards for tapes and grain and never
for a size).

| Orientation | along the wall | out from the wall | up |
|---|---|---|---|
| `upright` — facing the room | a | thickness | b |
| `flat` — horizontal | a | b | thickness |
| `end` — upright, side-on | thickness | a | b |

**Declared width, height and depth on a panel are labels and nothing else.** The
cabinet table shows `room.geometry`'s figures for one, not the declared ones.

**A panel is not a carcass.** `room.placed` skips it explicitly, so gaps, runs,
plinth, tip-up, door swing and overlaps are exactly what they were; it stands on
no legs (`stands_on_legs` is false, so `carcass_z` is its own z); it is not in
the Run drawing, which is also what keeps `wall_elevation_svg` with no room
equal to `elevation_svg`; and it is not in the edging legend, the structure,
door, drawer, support or carcass-thickness checks. A cabinet switched to Panel
keeps its drawer stack and its support rows in the job file and is reported on
for neither. Where it IS placed, drawn and snapped against is **Placing a
panel** below — through `room.placed_panels`, which is a separate list for
exactly this reason.

**`validate._panels` is deliberately short.** What a panel shares with
everything else on the cut list is already checked where it always was — too big
for a sheet is `_panel_fits_board`, a board the project never selected is
`_board_prices` — and repeating it would be two messages for one problem. What
is left is a missing board, a size of zero, an orientation the model does not
know, and an edging the board does not offer (CRITICAL, tagged `EDGING`, the
same shape as Part A's). **An unplaced panel is not a fault**: a panel cut and
not put anywhere is normal.

**A panel is always qty 1.** Identical panels are a **Duplicate** — the next
free number, everything copied except the placement, from the cabinet table's
Dup or the button in Panel design.

`PanelSpec.anchor` is reserved and nothing reads it. It is written to the job
file only when set. Ruled 20 September 2026: a panel stays where it is put and
does not follow a cabinet; the field is the seam for the day that changes.
Part E did not change that — it gave a panel a place, not an owner.

## Placing a panel

**A panel has a place in the room, and the cabinets do not notice.** Part E, 21
September 2026. What it added is one field, one list and one warning; everything
else is the machinery that was already there, taught that a panel exists.

**`Placement.y` is the one field a panel needs and a cabinet does not.** Out
from the wall face to the panel's back: 0 is flush, and it is what puts a
bulkhead underside out over the units below it, or holds an end cap behind the
front that laps it. A carcass sits against the wall it is placed on, so its y is
0 and stays 0 — the Placements table's Y cell is not even offered on a cabinet
row. **It is written to the job file only when it is non-zero**, so every
placement written before panels could be placed round-trips byte for byte.

    x   left edge along the wall, from the start corner
    y   out from the wall face to the back of the panel
    z   the bottom edge — a panel stands on NO legs, so this is its underside
        exactly as typed (`room.stands_on_legs` is false for it, and
        `room.carcass_z` hands back `p.z`)

**`room.placed_panels(job)` is the panel-only twin of `placed()`, which stays
cabinet-only.** Two lists, not one, on purpose: `placed()` is what gaps, runs,
plinth, tip-up and door swing come through, and a panel takes part in none of
them. `room._on_wall` is the one place the two are read together, because what
something comes to rest against does not care what kind of thing it is.

**A panel is dragged by the same pipeline as a cabinet**, not a second one: it
gets the same `g.ecabg` group with the same `data-cab`, so one press handler,
one `/api/drag`, one set of snap rules. `snap_points` and `z_snap_points` read
both lists, so a bulkhead front snaps to **the cabinet tops below it** as well
as to wall ends, the floor, the ceiling, opening edges and other panels.

**`/api/drag` says how far off the floor `z = 0` really is, and the browser
stops working it out.** `leg_lift` is `room.carcass_z` asked at z 0: the leg
height for a standing carcass, 0 for a hung unit and 0 for a panel. The browser
used to derive that from the layer, which would have stood every panel 100 mm
off the floor.

**The boards are read for a panel's geometry, everywhere it is asked.** A
panel's third extent is its board's thickness, so `snap_points`,
`z_snap_points`, `api.drag`, `cabinet_footprint`, `overlaps` and the drawings
all pass `job.materials` through to `room.geometry`. Nothing a cabinet answers
changes — the engine reads the boards for tapes and grain and never for a size.

**A 16 mm panel is a few pixels of target, so every one carries an invisible hit
rectangle at least `render.PANEL_GRAB` (16) px across** with `pointer-events`
on. Without it a bulkhead front cannot be picked up at all.

**In the plan a panel is a thin rectangle in its own board's colour, drawn over
the cabinets.** `y` is visible there and nowhere else. The drawn rectangle takes
no pointer events; the panel is picked up by its own grab area — see **Dragging
a panel in the plan** below.

**Dragging a panel in the plan** (22 September 2026, replacing E5's "not
built"). Along its OWN wall (x) and off it (y); never onto another wall and never
up or down — z is the elevation's. One press handler and one `/api/drag`, as for
a cabinet:

- `render._plan_panel_hit` is the grab area: the footprint grown about its middle
  to at least `PANEL_GRAB` px each way, in the wall's frame, class `cab panhit`,
  `data-layer="panels"` so the Panels toggle decides whether it is live. A THIN
  panel's goes over the cabinets (E4, as in the elevation); a WIDE one — a
  bulkhead underside over the run — goes under them, so it never takes a press
  from a cabinet it lies over, and is reached where it is clear or by isolating
  it. Plan text takes no pointer events, so its number never catches the press.
- `room.y_snap_points` is the depth twin of `snap_points`: the wall (0), each
  carcass or panel's front ("in front of N"), fronts level ("front level with
  N"), and another panel's back ("back level with N", "behind N"). NOT filtered
  by height — a bulkhead front lines up with base-unit fronts far below it. Each
  carries N's stretch of wall only for the tie-break. `/api/drag` hands it over
  per wall as `y_snaps`, and a carcass gets none.
- Each track carries `data-nx`/`data-ny`, the wall's own normal into the room;
  the plan is one scale and no flip, so that IS the direction on the page. The
  browser reads y off it and works out no dimension.
- Both axes keep the grab offset and take the NEAREST candidate within
  tolerance, ties to the nearest along the wall at the live position.
- The drop writes `Placement.x` and `Placement.y` of that panel and nothing
  else, then recomputes: the clash warnings, the plan and the elevation all come
  from that one compute. `check_drag.py` pins that only placements move and the
  cut list does not.

**Grain lines on a panel run the way the cut list cuts it, or not at all.**
`render._panel_grain_vertical` maps the grain direction onto the drawing through
the orientation; a grain running out from the wall has no direction face on, so
nothing is drawn rather than a line that would say the wrong thing.

**A panel clash is a WARNING, never a critical** (`room.panel_clashes`). Two
carcasses sharing a stretch of wall is a critical because the cut list built on
it is wrong. A panel is different: it is cut and costed wherever it is, its
position moves no figure on the order, and a bulkhead front is *meant* to sit
flush on the run and hard against the ceiling. Touching is clear, as everywhere
else, so a flush bulkhead raises nothing. The tests are the ones already here —
`polygons_overlap` on the outlines, `_z_span` on the heights, and for an opening
the same across-and-level test `blocked_openings` makes for a carcass.

**The plan's layer toggle is multi-select** (E3b, ruled 21 September 2026). Base,
Wall, Tall and Panels each switch on and off on their own; it used to be one
radio, so choosing a layer meant giving up every other one. Default is all four
on, which is exactly what the old "All" drew. **Everything not shown is ghosted,
not hidden** — the existing rule, applied to the new toggle as well: an overhead
means nothing without the base run underneath it, and Panels follows suit rather
than being the one toggle that behaves differently. `room.LAYERS` is still the
three CABINET layers and `layer_of` is never asked about a panel; `"panels"` is a
fourth toggle over the top, and `render.plan_svg` is the only place the word
means anything.

**A new placement lands clear of what is already on that wall** (E8, ruled 21
September 2026). Giving a cabinet or a panel a wall used to put it at 0 mm
whatever was there, which dropped it on top of the first thing on that wall and
out of sight underneath it. `room.free_x` answers it, off the same candidates a
drag reads — the wall start and the right-hand edge of everything already placed
— and the browser asks `/api/drag` and uses the figure. Nothing is worked out in
the browser. An item that fits nowhere comes to rest against the end of the run,
clamped to the wall: an honest overlap the validator will name, which beats a
position nothing worked out.

**`Test.json` cabinet 8 is the placed-panel fixture** (21 September 2026): an
`end` panel, 586 x 780 in BROOKHILL, standing on wall A at x 2800 beside the run,
which is also why cabinet 6 is 570 deep rather than 500. `check_panels.py` and
`check_edging.py` both read it, so do not take the panel back out — and
`check_edging`'s support-row comparison skips panels, because a panel keeps its
support rows in the file and the engine cuts none of them.

**`PanelSpec.anchor` is still reserved and unread.** A STANDALONE panel stays where
it is put. A panel that follows a cabinet is an ATTACHED panel (28 September
2026) — `attached_to` and three offsets, see **Attached panels** — not this
field. (Dragging a standalone panel in the plan is built — above.)

## Zoom

**The wall elevation and the plan zoom on Ctrl+scroll and on a trackpad pinch**
(E9, 21 September 2026), with `−` / `100%` / `+` beside each drawing; the
percentage is the way back. Zoom only — panning is the box's own scrollbars, and
nothing was asked for beyond that.

**The drawing is scaled by setting the SVG element's CSS size, and the viewBox is
left alone.** That is the whole trick: every conversion from a pointer to
millimetres — `elevPoint`, `svgPoint`, the plan's wall tracks, the elevation's
`.etrack` mapping and the panels' hit areas — reads `getBoundingClientRect()`
against the same viewBox, so it is exact at any zoom level without one line of
that arithmetic changing. Measured on the real app: a cabinet and a panel both
move the right number of millimetres at 64 %, 100 % and 156 %.

**A PLAIN wheel is left alone.** It first zoomed on every wheel event, which
hijacked ordinary scrolling: a two-finger trackpad scroll arrives as a wheel
event too, so scrolling past the plan zoomed it. The handler returns without
calling `preventDefault` unless `e.ctrlKey` is set (corrected 21 September 2026).

**One check covers both gestures, and that is deliberate.** A trackpad PINCH is
reported as a wheel event with `ctrlKey` true — how Chrome, Firefox and Safari
all report it — so pinch and an explicit Ctrl+scroll on a mouse come down the
same path. There is no separate pinch detection, and none is wanted.

## Vertical snap in the wall elevation

**Brought to parity with the sideways snap on 21 September 2026.** Both come
off one `/api/drag` reply and one browser handler, on the same 20 mm
`Standard.snap_tolerance`; what diverged was the set of targets each one names.

Every datum the sideways snap offers now has a vertical twin. The wall ends
answer to the floor and the ceiling; a neighbour's left and right edges to its
top and its underside; and an opening's two jambs to its **sill and its head**.
Openings were the real gap — `render.wall_elevation_svg` has drawn both lines
since it was built and nothing could snap to either, though a kitchen is set out
off both. Four per opening, named for what they are: `above the <kind>`,
`below the <kind>`, `tops level with the <kind> head`, `bottoms level with the
<kind> sill`. A datum runs the length of the wall, so unlike a neighbour's top
it carries **no stretch**: lining a run up with a window head beside the window
is as much the point as sitting over it.

**A standing neighbour's underside is `carcass_z` — the PLINTH TOP, never 0.**
Every carcass on the floor is on its legs, so `bottoms level with N` used to be
a leg height out. `Test.json`'s panel 8 is the case that proves it: it sits at
exactly 100, level with the plinth line and with every base carcass beside it,
and before this there was no target there and nothing to drag it back to.

**`room._hangs_clear` is the one rule about the strip between the floor and the
plinth top**, and it is what `under N` and both level lines ask. A carcass that
stands on the floor is offered nothing in that strip: it stands on its legs, and
worse, any z above 0 reads as hung (`layer_of`), so snapping a base unit to the
plinth top would quietly change its drawing layer while it stood exactly where
it already was. A **panel** stands on nothing and an upper is hung by
definition, so for those any height clear of the floor is real. The floor itself
is offered unconditionally, always, so all the rule ever does is rule out that
strip.

**The browser picks the NEAREST candidate within tolerance, not the first one it
finds** — both axes, corrected 21 September 2026. The engine hands them over
sorted and the docstrings always said "nearest"; the code took the first, which
only started to matter when an opening's datums landed among the neighbours'.

**And the reason names the nearest neighbour along the wall, not whichever sorts
first alphabetically** (21 September 2026). Several cabinets on the floor put
their undersides on one line, so a whole row of candidates share a height and
differ only in which one they name — panel 8 read `bottoms level with 1` with
cabinet 7 the one touching it. They are all true; the nearest is the one worth
saying, and in the list without `spans` it is the only one that survives the
de-duplication. `room._gap_along` is the one rule: how far apart two stretches
of one wall are, 0 where they touch or overlap, and 0 for a wall-wide datum,
which is never far from anything. `z_snap_points` sorts on `(z, that gap, the
reason)`. **The browser tie-breaks the same way at the LIVE position**, because
the engine can only sort for where the drag started and a drag crosses the wall;
it is choosing between candidates the engine named, and works out no height of
its own.

**A vertical move is checked exactly like a sideways one.** `room.overlaps`
reads `_z_span`, which reads `carcass_z`, so dropping a wall unit down into the
base run below it is the same critical as sliding it sideways into a neighbour
— and touching is still clear, so the snap target `on top of N` is not a
collision.

## Isolate

**One item drawn solid, everything else ghosted, reached from the LIST** (21
September 2026). A cabinet given a wall can come to rest underneath one already
there — `room.free_x` keeps it clear only of its OWN run, so a new wall unit
lands over the base run quite legitimately — and once it is under something
there is nothing to click on. So isolate is triggered by SELECTING the item, not
by clicking it in the plan: clicking is exactly what does not work.

**Ghosted, not hidden**, at the same `opacity="0.30"` the layer toggle uses.
One convention for "not the focus", not two, and a plan with the rest of the
room taken out of it is not a plan.

**It overrides the layer toggle for that one item and changes it for nothing
else.** An item isolated out of a layer that is switched off is still drawn
solid and still draggable; every other toggle stays exactly where it was.

**Ghosting alone is not enough, so a ghosted cabinet takes no pointer events.**
The thing that is hidden is hidden UNDER something, and that something would
still swallow the click. Only isolate does this — a layer ghosted by the toggle
keeps its events, which is what reveals its door swing on hover.

**A panel isolates exactly as a cabinet does**: it is occluded the same way, and
isolated its grab area goes on top whatever its size, so a bulkhead underside
lying over the run can always be got at and dragged.

**`plan_svg(isolate=...)` falls back to the ordinary plan when the number names
nothing it draws**, rather than greying out the whole room for nothing. A newly
added cabinet is exactly that case: it is selected, and so isolated, before it
has been given a wall.

**Where it is set.** `S.isolate` in the browser, one number or null, sent to
`/api/plan` and decided nowhere else. `selectCabinet(i, {isolate})` is the
single place it moves. **Changed on 23 September 2026 (Part F):** a selection
from the cabinet table, Duplicate, Add cabinet (a new cabinet is selected on
creation, so it is isolated on creation) and the 3D item list still isolates;
a click in the plan — which now selects, where before it did nothing — a
press in the wall elevation and a click in 3D select **without** isolating,
because an isolated view takes pointer events away from everything else and
clicking to select would leave nothing else clickable. While isolate is on it
follows the selection. It ends on a click on empty plan canvas, on the
`isolating N ×` pill beside the layer toggles, on the 3D Isolate toggle, or by
a list selection of something else, which isolates that instead. Loading or
starting a job clears it. The 3D view mirrors it and decides nothing.

## Corner units

**Three types, and a hand.** Ruled 22 September 2026. `corner_style` is `mitre`,
`ell` or `blind`; `corner_hand` is `'L'` or `'R'` and says which end of the unit
stands in the corner **as you face it in the room**.

**"The corner unit does nothing" was two faults, not one.** `engine.py` had no
corner branch at all, so a template cabinet with the box ticked still cut a
straight W × D box — the four measurements only reshaped the plan outline, and
not one line of the cut list moved. And the Style dropdown defaulted to blank,
which `Cabinet.corner_on` reads as "not a corner unit", so on a fresh cabinet
ticking the box did nothing whatsoever and nothing said why. Cabinet 7 only ever
worked because it is `template="none"` with its panels typed out by hand.

### The hand

**Right is the wall's far end; left is the wall's start.** A right-handed unit
has cabinet-local `x = arm_a` landing on the wall's length and turns onto the
**next** wall in the chain. A left-handed one starts at `x = 0` and turns onto
the **previous** one.

That mapping is not a convention invented here, and it was checked rather than
assumed: wall-local x runs left to right as you face a wall, which is already
what `model.hinge_side` means by 'L' and 'R' — `room.swing_envelopes` hinges 'L'
at the low-x end — and what `render.wall_elevation_svg` draws.

**A blank hand reads as R**, which is exactly what this app did before the field
existed, so cabinet 7 and every job written before it are unchanged.

**Left is the mirror of right, and nothing resizes.** The outline, the front
faces, the hinge rule and the shadow all reflect; the panels are the same
panels, to the millimetre. Which wall panel wraps the other is a construction
choice, not a consequence of the hand — mirroring the box mirrors the joint with
it — so both hands cut `arm_a − t` and `arm_b − 2t`, as cabinet 7 does.

**`room.corner_shadow` returns `(wall, x, width, depth)` now**, not
`(wall, width, depth)`: a left-handed unit's shadow lands at the far end of the
previous wall rather than at x = 0, and both callers read the x.

**Ticked with no type chosen is now said out loud.** The editor shows "Choose a
corner type" instead of an empty section, and the validator warns, naming the
straight box it is really cutting.

### A mitre is one construction for tall, base and wall alike

Melamine top **and** bottom, two melamine open-face sides, and a melamine back
that is the two wall panels themselves — one wrapping the other, `arm_a − t` and
`arm_b − 2t`, exactly as cabinet 7 is built. **No 3 mm backing board, no groove,
no supports** (RULES W13). `Cabinet.back` and `Cabinet.support_rows` stay in the
job file and nothing is cut from them.

**A base mitre does get a top.** That overrides the standing base rule, for
corners only; straight cabinets are untouched. The top is what braces the box,
which is why there is no bracing warning to raise, and an upper mitre hangs by
fixing through its melamine wall panels so it needs no hanging warning either.

The wall panels stay coded as **sides**, as cabinet 7 codes them. Nothing is
renamed: `engine.born_distinct` gives 01a / 01b / 01c at the moment they are made.

### The inner line, and what a mitre door is cut to

**The door is cut to the INNER SPAN, rounded down, with no gap deducted**
(ruled 22 September 2026, replacing the brief's "face length − 3"). The inner
span is the line between the two open-face side panels' inner front corners —
the surface a closed door's inside face actually rests on.

It is **not** the outline's mitre face. The outline runs corner to corner of the
carcass; the blank the top, bottom and shelves are cut from is already a board
thickness inside it on both edges. The door sits *within* the span rather than
overlaying the side edges, because the sides meet it at an angle and there is
nothing there to overlay.

**Cabinet 7 is the proof.** Its inner span is 472.35 and its door, as really cut,
is 472. Spec item 14 calls that a "23 mm reveal" against the 495 outline face —
it is not a reveal, it is a different measurement, and 495 is not what a door is
cut to. A pair divides the same span less `door_pair_gap`;
`Cabinet.corner_door_width` overrides the lot. The swing check and the arm
shelf's door clearance both read this same line.

`room.mitre_inner_corners`, `mitre_inner_span`, `mitre_blank` and `mitre_legs`
are the one place any of this is worked out.

### The two mitre shelves

**A mitre takes two kinds and may carry both.** `shelves` and `fixed_shelves` are
not read on one: a mitre's interior is not a rectangle, so a straight shelf size
would be wrong in the unsafe direction. Structure says so and sends you here.

**Arm shelf** — a rectangle along one arm, behind the mitre. Length is that arm's
internal span (`arm − 2t`); depth is typed, and `room.arm_shelf_max_depth` is the
most it may be. Two things bound it and the tighter wins: the closed door, which
it stays `Standard.mitre_shelf_clear` behind, and the concealed hinge's mounting
plate on the open-face side panel it ends against, which it stops
`Standard.hinge_clearance` short of. Both measure from `face − t`. **Applied
whichever side the door is hinged**, because that can change without the shelf
being recut. The answer is rounded **down** to a multiple of
`Standard.arm_shelf_step`; a depth typed by hand is taken as typed and only has
to come under it, and over it is a CRITICAL naming the maximum. On cabinet 7 the
maximum is 430 and its own 350 is accepted.

**Mitred shelf** — the same square blank as the top and bottom, mitred on site,
set back `mitre_shelf_clear` perpendicular from the inner line so the door closes
on it. On cabinet 7 that is legs of 338 against the top and bottom's 334. The
panel note carries both legs, because that is what the fitter marks to.

**Nothing is said or generated about how a shelf is fixed** — the assembler's
choice. **And nothing is said about hinges on a mitred shelf**: shelf heights are
not modelled anywhere in this app, `Standard.hinge_positions` stays drawing-only
(`check_elevation.py` fails if the engine, the export, the nester or the
validator reads it), and the assembler places shelves clear of the hinges. Shelf
heights are a separate piece of work — do not build towards them here.

**Three new constants, and no tape deduction.** `mitre_shelf_clear` 3,
`hinge_clearance` 50, `arm_shelf_step` 5. The clearance is worked out with no
edging thickness deducted: this app deducts no tape anywhere and that holds here
too (ruled 22 September 2026, after the question was asked).

### A blind corner is a straight cupboard

A carcass W × H × D with a flush panel INSIDE the corner end and **one door**,
always, at the far end. The run on the return wall is ordinary cabinets and is no
part of this unit.

```
opening  O = W - 2t - B
door     derived from the opening exactly as any other door is:
         (O + 2t) - door_single_gap = W - B - door_single_gap
blind    exactly B wide - the board size is the board size - and (H - 2t) long,
         fixed, no pot holes

along the wall, from the far end (right-handed):
         side t | opening O | blind B | side t
         door   from door_single_gap / 2, W - B - 3 wide
```

W 1000, B 500, t 16 → **opening 468, door 497, blind panel 500 wide**; at
H 2400 the panel cuts **2368 × 500** beside a **2397 × 497** door.

**The panel sits INSIDE the carcass** (ruled 22 September 2026, replacing a panel
that stood across the corner end at door height): between the corner-end side
panel and the opening, front face flush with the carcass front edges like the
sides, the top and the bottom, so the unit reads as one flush front. So it runs
between the top and the bottom — `room.blind_panel_height`, **H − 2t**.

**A base unit has no top and it is the same figure, and that was checked rather
than assumed.** The panel stands on the bottom and runs up to the underside of
the front support, which is cut from the same board at the same thickness and
lies flat with its face flush with the carcass top edge. It is also the figure
the engine already takes as a divider's default height (`H - 2 * std.board_t`),
so the two agree by construction. H 790 → 758.

**The door is an ordinary overlay door and did not move.** It overlays the far
side panel and the blind panel's face by `t − door_single_gap / 2` = 14.5 mm
each. `room.blind_spans` is the one place that layout is worked out — `(side,
blind, door)`, each a `(start, end)` in cabinet-local mm — and the wall elevation
and the Corner Unit plan diagram both read it rather than laying the unit out for
themselves.

**The panel names its own board and its own edging thickness.**
`Cabinet.blind_board` is blank for "the exterior board", which is the default
because the strip of panel the door does not cover is seen from the room beside
the doors. It is in `Cabinet._board_slots`, so the swap, the un-select, the
rename and the library scan all find it, and `check_single_source.py` is what
says so. `Cabinet.blind_edge_kind` is 1mm or 2mm, None meaning the doors' —
offered separately because reaching into the cupboard rubs against that one
edge.

**Edging is ONE long edge**: the vertical one facing the opening. Grain runs up
the height as on a door, which is why that edge is a long one — `edge_l = 1`,
`edge_w = 0`. The colour is the panel's **own** board's edging, through the same
`tape_for` chain as everything else; a kind that board does not offer is the
ordinary `EDGING` critical, and no edging name is stated anywhere but the Boards
record.

Both new fields are in `store.LATE_CABINET_FIELDS`, so every job file on disk
round-trips byte for byte.

**Its plan is a plain rectangle**, so it has no derived outline and
`room.corner_outline` returns None for one *by design* — the validator's
"parameters do not resolve to a shape" critical skips it, and the Outline field
stays live because the footprint really is read. Everything in Structure — back,
supports, shelves — is the ordinary engine path, unchanged.

**The blind panel is code 08 with the role "Blind Panel"** (`model.BLIND_CODE`,
Q3), on the same reasoning as a panel's 08: the CSV carries `Panel.label` (in
Customer Number), never the role, so a code of its own would need their sign-off and would say
nothing on the order that 08 does not.

It casts a shadow on the return wall like any corner unit, its own depth wide, so
`gaps` does not propose a filler for the space it is standing in.

### A corner unit's door swing BLOCKS the export

**This is a deliberate exception** to the house rule in `validate._room`, which
keeps an ordinary door-swing foul a WARNING. Ordinary doors stay that way. Do not
tidy the two back into one rule.

An ordinary door can be rehung, moved or lived with, and which way it hangs is
the fitter's judgement. A mitre's door cannot — it hangs on the mitre face or
nowhere, and its width is derived from the arms rather than chosen — so a swing
that fouls the runs either side of it is a unit that cannot be built as drawn.
The message says **the widest door that would clear**, found by trying widths
against the real swing check (`validate._door_that_clears` sets
`corner_door_width` and asks `room.clashes` again) rather than by a formula, so
there is something to do about it. Widening the arms is the other way out and the
message says so, but it resolves to no single figure: bigger arms move the face
further into the room and widen the derived door at the same time.

**A blind unit whose door the return run reaches across blocks for the same
reason** (`validate._blind_clearance`, Q4). The unit exists for exactly that
clearance. What reaches is the return cabinet's own depth plus its door front,
and **no handle clearance** is added — if a real job needs one it belongs in
Standard, not guessed at here.

**The threshold is B, and it stays B now the panel is inset.** That is the
re-read the inset construction asked for, and the answer is that nothing moves:
the clear OPENING is a board further from the corner than it was — `t + B` — but
the DOOR is what the return run blocks, and the door did not move. Its
corner-end edge still stands `B + door_single_gap / 2` from the corner, lapping
the panel's face. A return run reaching between B and B + t clears the opening
and still stops the door opening, so measuring against the opening would be
wrong in the unsafe direction. `check_drag.py` pins the discriminating case.

### An ell is shape only

Rudolf has never built one and has deferred the construction, so the outline, the
hand, the plan, overlaps, the shadow, the gaps and the face-length readout all
work and **the engine generates nothing**. That is a CRITICAL naming what to do
about it — add bespoke panels in the job file, or change the type — rather than
an empty cabinet quietly costing R0. An ell with `template="none"` and its own
bespoke panels works exactly as cabinet 7 does and is untouched by it.

### Where a corner unit's dimensions are typed

**Every one of them is in the Corner Unit section, and Size is greyed** — the
same rule as a panel, whose dimensions all live in Panel design, and for the same
reason: it must be obvious to somebody who has not read the code where a number
goes.

A greyed field shows the **engine's** figure, never the declared one. Declared
width, height and depth are labels and no check reads them, so echoing a stale
declared figure back into a field that looks authoritative would be showing the
wrong number. **Kind, Number and Note stay live** — Kind because a corner can be
top-hung, base or tall.

**Outline is greyed for a mitre and an ell only.** There `geometry` genuinely
ignores an entered footprint. On a blind unit the footprint IS read like any
other cabinet's, and greying a field that is still being read would be a lie.

**Nothing is thrown away.** Switching the type or the tick back brings every
value with it, the same bargain the tickboxes strike.

**New `Cabinet` fields are written to the job file only when they are not at
their default** (`store.LATE_CABINET_FIELDS`): `corner_hand`, `blind_width`,
`arm_shelves`, `arm_shelf_arm`, `arm_shelf_depth`, `mitred_shelves`,
`corner_door_width`. `cabinet_to_dict` is `asdict`, so a field added to `Cabinet`
and not added to that tuple makes every job file on disk grow a key the next time
it is saved — which is what broke `check_panels.py`'s byte-for-byte round trip
the first time round.

## Supports

**A support is a cross rail spanning the internal width** (`W - 32` x 100, code
04) that ties the two sides together. It is called a support everywhere in the
UI — never a rail.

### Three types, placed by the engine (27 September 2026)

`Support.type` is `front`, `top_rear` or `back`; `''` is a legacy row. Which
types a carcass takes is `model.support_types_for` / `Cabinet.support_types_offered`:
a BASE unit all three, anything with a top panel (tall, wall) Back only, a blind
corner by its kind, a mitre or an ell none. A typed Front or Top Rear stored on
a carcass that has since gained a top stays in the file, is not cut
(`support_list` filters it), is greyed in the editor and named by a warning.

Where each one stands is `room.support_layout`, in the spec's carcass-local
frame (x across, y from the FRONT face of the sides, z up from their underside;
`room.interior_parts` turns it into the cabinet frame with `y_part = D - y`):

- **Front** — flat, y 0..100, z H-16..H, top flush with the sides.
- **Top Rear** — flat at the same height; with a backing its rear edge is on
  the backing's front face (y D-119..D-19), with none it is flush with the back
  of the sides (y D-100..D).
- **Back** — upright in the cavity, y D-16..D, 100 tall, the same plane with
  or without a backing. Back 1 hangs under whatever is at the top back (a top
  panel, or a Top Rear at the back — base with no backing — put it at H-16;
  otherwise H). Back 2 stands on the bottom panel. Back 3..n are spaced with
  equal gaps between the two. One alone is Back 1. Back 1's edged long edge
  faces DOWN, every other Back's UP.

Worked (W600 H720 D560, back four): Front y 0-100 z 704-720; Top Rear y 441-541;
Back 1 z 620-720; Back 2 z 16-116; three Backs put the middle one at 318-418.
No backing: Top Rear y 460-560, Back 1 z 604-704. Tall 2400: Back 1 z 2284-2384.
All pinned in `check_supports.py`.

**Edging is chosen edge by edge** — `Support.edges`, any of `front`, `rear`,
`left`, `right` in the row's own terms (on a Back, `front` is the long edge
facing INTO the cabinet). `None` means the type's default, the front long edge;
`[]` means none. The cut list records the counts exactly as before: `edge_l`
long edges, `edge_w` ends (`Cabinet.support_row_edge_counts`); a legacy row is
one long edge, as it always was. No kind chosen means nothing banded whatever
is ticked, and no edge ticked means no tape ordered whatever the kind — the
engine blanks `edge_material` on such a row.

**Every Back support has an edging of its own** (ruled 27 September 2026,
replacing the spec's one Back block with one edging). A Back row is one
support (or several identical ones, `qty`, which is what a re-entered legacy
row is); each carries its own `cut_board`, `board`, `kind` and `edges`, and
`support_layout` numbers them Back 1, 2, 3… across the rows in order. A new
Back (`Cabinet.new_support`, `/api/support-new`, the editor's **+ Back
support** and a new cabinet's four) is cut from the carcass, in that board's
own edging kind (`default_support_kind`: the first it offers, `''` for a board
with no edging) with **no edge ticked** — unedged until one is. A Front or Top
Rear starts on its front long edge as before.

**Legacy rows are cut exactly as they always were and are never converted.**
Only their DRAWING placement is decided, by the legacy rule in
`support_layout`: on a base unit one front-edged rail is the Front and the rest
are Backs; on a carcass with a top, all Backs. The editor shows them read-only
"as quoted" with a Re-enter button; re-entering (`Cabinet.reentered_supports`,
behind `/api/support-reenter` — the browser writes the rows and works out
nothing) gives every legacy row a typed row OF ITS OWN with its qty and exactly
what it resolved to be cut from and edged in, so the cut list and the cost do
not move; an edged row ticks its front long edge, an unedged one nothing, and
no Top Rear is guessed. The three old numbers are left where they are; a job
with none of this written round-trips byte for byte (`type` and `edges` are
written only when set, `store.cabinet_to_dict`).

**Three criticals, on typed rows only** (`validate._support_layout`): a drawer
box reaching into the 16 mm band under a Front or Top Rear — a box hangs 21
above its own face's bottom (the drawer setting, 28 September 2026:
`room.drawer_layout`, read through `room.drawer_box_tops`) — blocks the export; Front
and Top Rear overlapping in depth (D >= 219 with a backing, 200 without); Back
supports that do not fit between Back 1 and the bottom panel
(`room.back_supports_fit`). Legacy rows raise none of them.

**Drawn in 3D only.** `room.interior_parts` gives the supports (role `support`,
label `Front` / `Top Rear` / `Back n`) and the shelves (role `shelf`, spaced
evenly from the bottom panel's top face to the top of the sides, fixed first,
display only) as `Part`s plus their `Tape`s; `room.tape_solids` turns each tape
into a band `scene.TAPE_BAND_MM` deep INSIDE the finished size on that face, in
the edging board (`support_row_board`; a shelf's front edge in the exterior
board's PVC, the carcass edging). Edged or not, a part is the same size in the
same place. `solid_parts` does not carry them, so Finish, the plan and the wall
elevations are unchanged; `scene._line_for` tells a Front and a Back of one
size apart by their band counts. The browser (`buildTape`) only extrudes the
band it is given, with a polygon offset so it draws over the face rather than
being moved off it.

`Cabinet.support_rows` is a list of `Support(edge, qty)`, where `edge` is
`'front'` (carcass tape), `'white'` or `'none'`. **The total is
the sum of the rows and nothing subtracts.** The old model was a total with two
subsets taken off it, so `edged + white` could exceed `supports` and the plain
count went negative — which `if plain > 0` then dropped in silence.

`Cabinet.support_list` is what the engine reads. With no rows it migrates the
three legacy numbers in the order the engine always emitted them — plain, then
front-edged, then white-edged — so a migrated cabinet cuts the same list in the
same order. A cabinet whose three numbers contradict each other keeps cutting
exactly what it always cut and is **named in a warning**; nothing is migrated on
a guess. `Test_Build.json` cabinet 4 is the one real case (0 total, 4 white).

**White-edged means edged white: `PVC WHITE`, whatever the boards are** (ruled 18
September 2026; through `model.white_edge_board`, the project board whose Edging
Name is WHITE, since `model.WHITE_EDGE` went on 28 September 2026). It used to take the drawer-box tape, which
follows the carcass board, so on a GREY carcass a row labelled "White-edged" went
out as `PVC Grey`. `Cabinet.support_tape` is the one answer; the engine cuts from
it and the editor's Edging column shows it. The October job is unaffected (its
white supports were on MEL, already `PVC WHITE`); `check_library`'s what-if swap
to a Brookhill carcass moved R34,716.75 → R34,723.50 because of it.

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

Sheet layouts render to `output/<job>/nesting/nest_<material>.svg` — open in any browser.

Worth trying if more yield is wanted: cross-sheet offcut reuse (keep a stock of
leftovers between jobs), and simulated annealing over the panel order. The
77 % on Brookhill is the one worth attacking — it is the R999 board.

## The UI

`python run_app.py`. See `docs/UI-BRIEF.md` for why it is shaped the way it is.

**Since the UI restructure (28 September 2026)** the Cabinets tab is the selected
cabinet alone in 3D over the cabinet list, in the left column; the **settings
panel is a column of its own**, starting level with the top of the 3D view. The
wall elevations are in Room -> Elevation. See the Status entry and **The
Cabinets tab's 3D**.

**Undo** (round 2, 3 October 2026): **Undo · Redo** beside Save, Ctrl+Z /
Ctrl+Y / Ctrl+Shift+Z (in a text field the field's own undo applies). A stack
of job snapshots (`structuredClone`), 50 deep, pushed by `pushUndo()` from
`markDirty(true)` and every field's `change`: the job as it was before the
edit (`S.undoBase`, kept since the last step) goes on the stack, and a new
step clears Redo. One step per committed edit — a typed field commits when it
loses focus, never per keystroke; a pointer move never makes one; what the
page writes back on the engine's say-so (`S.noUndo`, `undoAbsorb`: the drawer
solver, a lapsed acceptance) and the server's answer just after a step
(`UNDO_FOLLOW_MS` 3000, with nothing pressed between) go with the step they
followed. Undo restores the snapshot and runs the ordinary compute, keeping
the selection when the item still exists; back at the saved job the unsaved
marker clears (`S.savedKey`). Load and New clear the history (`undoReset` in
`adopt`). Not undone, and the tooltip says so: Save, Load, New, Delete
project, Export, snapshots, and the libraries (Catalogue → Boards / Runners,
pictures), which write files at once — a library write the job follows is
folded into the base (`undoRebase`). Every new edit path must reach
`markDirty(true)` or a `change` event.

**Room -> Plan since the room redo (2 October 2026)**: a slim toolbar on the
left (Select, the default; Draw walls; Wall nook (Phase 2); Esc returns to
Select — Phase 3 adds the openings palette). Since Phase 2 (3 Oct) the plan is
also where walls are drawn, dragged by a corner or the body, and their
lengths typed — see the Status entry; the plan in the middle (zoom and layer
chips in its header; click a wall's line to select it, a cabinet to select it,
empty canvas to select the room), and the dock on the right showing what is
selected: the **Room card** (name, ceiling mm, offset depth mm, Draw walls,
Renumber, Remove room, the walls in walk order — Wall · Length (mm) · Corner
after (°) · Height (mm) · Face (Flip) · Op. · Obs. · ×; a row click selects
that wall), a **Wall card** (length, the corner before and after it with the
out-of-square mm where near square, height blank = the ceiling, thickness,
drawn / measured, Flip face, + Wall after / before where that end is free,
Delete, its openings and obstructions read-only until Phase 3), or the one
editor for a cabinet or panel. Placements, Gaps and Plinth are under the plan.
Every figure on a card is the engine's; every wall edit is a server call and
the room comes back (`takeRoomReply`); a refused entry is said in the card
(`wallNote`, held in state across repaints). The one help line: "The line is
the inside face; the room is the tinted side. Flip face turns it round."

The cabinet editor is seven sections, each a bold heading over its own coloured
block: **Size · Outline · Structure · Doors · Drawers · Corner Unit ·
Supports**. An item whose **Kind** is Panel shows **Size · Panel design** and
none of the cupboard sections — hidden, never emptied, so picking a cupboard
kind again brings all of it back (see **Panels**). Turning a configured cupboard
into a panel says what stops being cut before it does. Doors, Drawers and Corner Unit are tickbox sections — unticking keeps
everything in the job file and builds nothing from it, and says which cut-list
lines would go before it does.

**Size is greyed wherever the dimensions are entered somewhere else**, and each
greyed field says where: "Set in Panel design below" on a panel, "Set in Corner
Unit below" on a corner unit of any type. A greyed field shows the ENGINE's
figure, not the declared one — declared sizes are labels and no check reads
them. Kind, Number and Note stay live throughout. Outline is greyed on a mitre
and an ell, where the outline really is derived, and stays live on a blind
corner, where the footprint is read like any other cabinet's. See **Corner
units**.

- **Structure** is where the boards are chosen — exterior, backing, carcass, in
  that order — then how the back is fixed, then the shelves. Every board is a
  dropdown off `Job.materials`; free text there used to create a material
  silently, which nested on its own sheet and priced at zero. **Structure
  mentions no edging at all**, on purpose.
- **Shelves** are adjustable, on pot holes, 4 mm clear of the back. **Fixed
  shelves** are fitted into the carcass and run 3 mm deeper, 1 mm clear of it.
- **Dividers, divider height and shelf width are shown greyed and labelled
  "function unavailable"** — a divider cannot be positioned yet and shelves do
  not divide around one. Shown rather than removed, because an option that
  silently does nothing is worse than one that says so.
- **Doors** is one or two leaves and no more. A pair is fixed, left and right; a
  single door is the choice. Each leaf names the board it is cut from, and the
  section carries one edging control.
- **Drawers** (redone 29 September 2026) is two headed blocks in its tint.
  **Setup**: Drawer type (Outer | Inner), Runner (dropdown, Catalogue…, ONE
  status line — `Gelmar 45 · 500 long · box 500 × 291 · pulls out 500`, or
  `Legacy lengths (350 / 450 / 500), as quoted` with what to do), Bottom
  (3 mm grooved sheet | 16 mm housed melamine), Box board · Face board, Box
  edging and Face edging (thickness + colour each, the names in the tooltip).
  **The stack**: `# · Face height · Box height · Offset · differs… ×` — the
  lock (Fixed / Share and its weight), Box height `Auto (≤n)` or typed with
  `≤n` and Auto, the readout `opening · faces + gaps · left`, and Equal ·
  Graduated · + Drawer; inner drawers put Height where Offset is. A drawer's
  **differs…** sub-row holds its own box board, face board, bottom and box
  edging (a face's edging stays the section's, as Doors); a drawer naming any
  shows it open with a dot, and **same as section** clears them all. One
  help line under each control, the brief's words. The settings column stays
  560 wide.
- **Supports** is the support rows and nothing else. The **Decor** section is
  gone — added panels (exposed ends, code 08) come back with that work.
- **Corner Unit** is the type, the hand and every dimension the unit has. A
  mitre or an ell turns Drawers and Supports off outright and greys Structure's
  back fixing and shelves, each saying why; a blind corner is a straight box and
  only its Drawers go, with its Doors fixed at one. A blind corner also carries
  the blind panel's own board and its own edging thickness, under the panel
  width, and the readout states the line it cuts. Off, not emptied, as
  everywhere else. See **Corner units**.

Six tabs over one `POST /api/compute`. The handlers in `app/api.py` decide no
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

**A cabinet is dragged in the wall elevation, sideways and up and down** (18
September 2026). Same bargain as the plan: `/api/drag` hands over every position
(`room.snap_points`) and every height (`room.z_snap_points`) the engine will
allow, with the reason for each, and the browser only picks the nearest within
`Standard.snap_tolerance`. A height that belongs to another cabinet carries the
stretch of wall it applies over, because the drag crosses several on the way and
a round trip per pointer move is not on; testing that overlap is a comparison
between candidates the engine named, not a dimension. The drawing carries the
mapping in `class="etrack"` — where 0 mm and the floor are, and the scale — and
one `class="ecabg"` group per cabinet so the whole thing moves rather than an
empty outline. The vertical figure is `Placement.z`: 0 is the floor, where the
carcass stands on its legs, and above it is a hung unit's underside.

Two things about **the elevation drag** that were wrong and are pinned only by
hand (the UI has no test harness): its press does all its synchronous work —
listeners, `preventDefault` — *before* awaiting `/api/drag`, and replays the last
pointer position and the release once the model arrives. Awaiting first meant a
quick drag let go before anything listened, and the cabinet stuck to the pointer.
**The plan's press does the same, and does it the same way** — one shape, not
two pipelines; it was fixed on 22 September 2026, having been found on the 21st
and missed by the 18 September fix. And the floor snap is compared where a
standing carcass really is (its underside on the legs), not at `z = 0`; an
underside below leg height is "on the floor". Before, a sideways drag with a
2 px wobble hung a base unit 86 mm up.

**Lining up, not only stacking** (18 September 2026). Besides "on top of" and
"under", which only apply over or under the other cabinet, `z_snap_points` offers
"tops level with N" and "bottoms level with N" for every cabinet on the wall. Those
carry the stretch they do **not** apply over (`not_x0`/`not_x1`): beside a tall
unit a wall unit's top can come level with it, but directly over a base unit
level tops would put one inside the other. Nothing below `leg_height` is offered.

**Hinge naming.** `L` / `R` is the edge the leaf hangs from, facing the cabinet —
the plan's swing pivot, the elevation's hinge dots and the point of its dashed
triangle all sit on that side, and they were checked to agree. The editor says
"hinged left / hinged right". It used to say "opens from the left" for `L`, which
reads as the handle side — the one thing that was inverted.

**Clicking a door in the elevation no longer turns it round.** Which edge a leaf
hangs from is set in the Doors section, where the answer can be read instead of
guessed at from a picture, and a pair is not a choice at all.

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

**Walls are positioned segments** (room redo Phase 1, ruled 2 October 2026).
A `Wall` is its two end points, `x0, y0 → x1, y1`, whole mm; nothing else
stores a wall position. The drawn line is the inside face and **the room is
on the right of x0 → x1** — the right-hand normal, which in this frame is
`(-dy, dx)`, the normal the old chain gave; the thickness band is drawn on
the left, the back. Everything a room used to store is derived in `room.py`:

- `wall_length`, `wall_dir`, `wall_normal`, `wall_frames` (the same return
  shape as ever, so everything that takes (start, dir, normal) is untouched).
- `connections`: B is A's next when B's start lies within
  `Standard.join_tolerance` (1 mm) of A's end. Each end meets at most one
  wall; the lower letter wins a tie. A wall meeting nothing at either end is
  **free** — no corner, no butt, no shadow, nothing returned beside it.
- `chains` / `walk_order` / `main_chain` / `is_closed`: each chain is walked
  from its head (for a loop, its lowest letter); chains come in the order of
  their lowest letter, free walls last; the room is the first closed chain,
  else the first chain. `corner_points` is the main chain; `closure_error`
  is now `room.closure`'s miss (Phase 2, ruling 1): a main chain of three or
  more walls missing by up to `loop_miss_max` is a LOOP THAT OPENED, said as
  "Loop opens by n mm at D→A — …" by every display; a bigger miss is an open
  run and nothing is said.
- `corner_angle(rm, wall)` is the interior angle AFTER that wall, to 0.1°
  (`corner_angle_exact` for geometry — a gap's taper); `corner_before` the
  one before it; `out_of_square` the mm a site would read at
  `Room.offset_depth` when the angle is within `Standard.square_within` (10°)
  of 90, 180 or 270, positive opening away from the room.
- `crossing_walls` names proper crossings only: meeting at an end, or an end
  lying on another wall (a T-wall), is legal geometry.
- **Edits move points**: `set_length` (the end moves along the wall; the
  walls after it in its chain follow), `set_corner` (the walls after the
  corner turn about it — round a loop, every other wall, so the last corner
  can be typed and the loop opens where the walk came back), `set_out_of_square`,
  `add_wall(after= | before=)` at 90 off a free end, `walls_from_points` adds,
  `flip_face` swaps the ends and re-measures what is on the wall from the
  other end, `renumber_walls` re-letters along the walk, `delete_wall`;
  since Phase 2 `corner_move`, `wall_move` (what stands on a changed wall
  keeps its x, `keep_on_walls`), `split_wall`, `wall_nook`, `add_back_face`,
  `flip_room`, and `room_snaps` for every drag and drawing on the plan.
- **Letters are for life**: nothing re-letters a wall but Renumber. A new
  wall takes the first unused letter, AA after Z (`next_wall_id`).
- **Migration, once**: `store.room_from_dict` reads the old keys (`length`,
  `offset_start`, `offset_end`, `corner_end`, the room's `closed`) through
  `room._legacy_frames` — the old chain arithmetic, used by nothing else —
  and writes points; the old keys are never written again. The parallelogram
  with offsets at every corner is now a migration case in `check_room.py`.

Thresholds live in `Standard` like every other dimension: `closure_warn`,
`closure_block`, `loop_miss_max`, `join_tolerance`, `wall_thickness`,
`square_within`.

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

**Every corner's angle is derived from the two walls' directions** (since 2
October 2026; before that `Wall.corner_end` was typed and the chain turned by
it): 90 inside, 270 outside, anything strictly between 0 and 360. Typing an
angle in the Wall card turns the walls after the corner (`room.set_corner`).
See the Status entry and `docs/ROOM-LAYOUT-SPEC.md`, **Ruled — 2 Oct 2026**.

**Walls are added off a free end** — `room.add_wall(rm, after=id | before=id,
length)`, behind `/api/wall-add` and the Wall card's "+ Wall after / before",
offered only where that end meets nothing. That is how a straight run becomes
an L or a U; the 4000 × 3000 pre-fill for a new room stays (ruled 14 September
2026). A new wall takes the next free letter and starts at 90. Nothing is
re-origined: wall A stays where it is, and which wall is "earlier" at a corner
for the plinth butt rule is the walk (`walk_order`).

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

## Accepting a critical

**Ruled 22 September 2026.** Some criticals depend on the SITE, not on the cut
list; the operator can accept one with a reason and the export goes ahead. A
critical that protects the cut list always blocks. **Today tip-up and
above-ceiling are acceptable** — above-ceiling since 29 September 2026
(Rudolf), changing the 22 September "tip-up only". **Still blocking:**
`ceiling-measured` (no ceiling measured — a missing site figure),
`panel-fits-board` (a panel can never be longer than the board), the mitre door
swing (deliberately), and every other critical.

- Every critical carries a stable **check id** (`Issue.check`, e.g. `tip-up`,
  `overlap`, `mitre-door-swing`). Never rename one: acceptances are stored
  against it.
- A check becomes acceptable by an entry in `validate.ACCEPTABLE` and nowhere
  else — its id and the function that FINGERPRINTS exactly the inputs it read.
  Tip-up's is `room.tip_inputs`, the same dict `tip_problems` works from:
  height and depth off `geometry` (never declared), legs, setback, underside and
  ceiling, written readably into the job file. Above-ceiling's is
  `room.ceiling_inputs` — underside (`carcass_z`), height (`geometry`) and the
  ceiling — the same dict `above_ceiling` compares, attached panels included.
- `Job.acceptances` holds `{check, where, reason, fingerprint}`, written only
  when there is one, so every job on disk round-trips byte for byte.
- `validate` marks each critical `acceptable`, `accepted` (the reason) or
  `lapsed`, and never writes to the job. `blocking` ignores accepted ones.
  `/api/compute` returns `lapsed`; the BROWSER drops those from the job, marks
  it unsaved and says why in one line. A stored acceptance for a check that is
  not acceptable is lapsed by definition — it can never unblock anything.
- `/api/accept` hands back the fingerprint and refuses any check not in
  `ACCEPTABLE`. The reason is required; "Assembled in place" is a one-click
  preset on tip-up only.
- Accepted items stay in the Validation list greyed with an Undo, show on the
  cut list, and go into the export folder as `<job>_accepted.txt`. **Never into
  the Plazaboard CSV.**

## Drag placement

**Three things a press in the plan must get right** (22 September 2026, all
measured with a real mouse in a headless browser): text in the plan takes no
pointer events, or the number over a cabinet's middle swallows the press; the
drag keeps where along the cabinet it was grabbed (`d.grab`, projected on the
press onto the cabinet's own wall track), or it jumps to centre on the first
move; and it takes the NEAREST snap within tolerance.

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

**The press listens before it asks** (22 September 2026). It attaches those
listeners and calls `preventDefault` first, and only then awaits `/api/drag`;
while the model is in flight a move is remembered as `d.last` and a release as
`d.released`, and both are replayed the moment it lands. Awaiting first — which
is what the plan did, and the elevation did until 18 September — meant a quick
drag could let go before anything was listening, and the cabinet then stuck to
the pointer: measured on 21 September with an instant synthetic drag at 100 %
zoom, the cabinet did not move at all, while the same drag with a 700 ms pause
after the press worked. One shape for both drawings, `moveDrag`/`finishDrag`
beside `moveElevDrag`/`finishElevDrag`, not a second pipeline.

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

**One rule for every wall, however many there are** (22 September 2026).
Standing in the room facing the wall: what is placed on it is drawn in full; the
runs on the walls either side are grey outlines end on, at their true depth and
height off `room.geometry`, **one label per neighbouring wall** naming its
numbers ("B: 11, 13") — a label per outline hid one number under another, which
is how cabinet 13 went unnamed on wall A; an end with no wall beside it has
nothing drawn. The neighbours come off the chain of corners in
`room.return_profiles`, never a letter, and include placed PANELS. A corner unit
belongs to the wall it is placed on. The end-on outlines are filled under this
wall's cabinets as before, and their dashed lines and labels drawn again OVER
them: a return run often stands nearer the viewer than a corner unit's far arm,
and was being hidden behind it. Checked on three- and four-wall rooms in
`check_elevation.py`.

**The runs either side show end on** (18 September 2026). Face on to wall B, wall
A's run comes towards you at B's start corner, and what you see is the cabinets'
sides. `room.return_profiles` projects each cabinet on the two neighbouring walls
into this wall's frame off its real plan outline (`to_world` there, the inverse
here — still all trig in `room.py`), and the drawing shows them light and
see-through under this wall's own cabinets, one label per identical outline. The
opposite wall is behind the viewer and is not drawn. They are drawing only — not
draggable, and not part of any dimension chain.

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
`../x` cannot write outside `output/`.

Still open, and **not to be guessed into `Standard`**:

- whether kitchen appliances need to be room objects with clearances, and whether
  worktops are in scope;
- the offset measuring depth and sign convention (shipped with the spec's
  proposed defaults, still awaiting confirmation);
- where the legs stand, for drawing them — only the rear setback (50) is ruled,
  and only the tip-up check uses it, so legs are still not drawn.

Corner units are parametric (ruled 14 Sept 2026, spec items 11-15; what one
actually CUTS was ruled 22 Sept 2026 — see **Corner units** below):
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

0. **An ell corner's construction.** The shape is built and so is everything
   that reads it — the outline, the hand, the plan, overlaps, the shadow, the
   gaps, the face-length readout. What an ell is actually MADE of, Rudolf has
   never built, and it is deliberately not guessed: the engine generates nothing
   for one and the validator raises a CRITICAL saying so. An ell with
   `template="none"` and its own bespoke panels works like cabinet 7 and is
   untouched by that. When it is ruled it goes beside `engine.mitre_panels`, not
   inside it.
1. **Dividers.** `divider_count` / `divider_height` still generate a code-09
   panel, but nothing positions one and shelves do not divide around it, so the
   three controls are greyed in the editor and labelled unavailable. Whatever is
   built has to answer where a divider stands before it answers anything else.
   Added panels — exposed ends (08) and the rest — come with the same piece of
   work.
2. **CAD export.** DXF per panel plus a parameter table SolidWorks can drive a
   configuration from, so the model and the cut list cannot diverge.
3. **Obstruction cut-outs on backing panels.** Deferred 14 September 2026 for the
   same reason as sliding doors: an obstruction behind a carcass is drawn, but no
   cut-out goes on the cut list until a real job supplies a real pipe position.
4. **Sliding doors.** Not urgent, but leave the seam. A hinged door is a
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

### Where every moved function lives now (Session 1 checklist)

| Function | Was | Now |
|---|---|---|
| Wall elevations (one wall face on) | Cabinets tab, top-left card | Room -> Elevation |
| Wall picker (Wall A, B…) | Cabinets, elevation header | Room -> Elevation header |
| The Run (side-by-side) button and drawing | Cabinets, elevation header | **Removed** (brief). `elevation_svg` internal only |
| Line / Finish toggle | Cabinets, elevation header | Room -> Elevation header |
| Elevation zoom (−/100%/+, Ctrl-wheel, pinch) | Cabinets | Room -> Elevation |
| Drag a cabinet / panel along and up the wall, vertical snap | Cabinets elevation | Room -> Elevation (same handlers on `#elevation`) |
| Drag a drawer divider | Cabinets elevation | Room -> Elevation (and it sticks now) |
| Click-select in the elevation, opening the editor | Cabinets elevation | Room -> Elevation, editor in the Room dock |
| Board / tape legend, dimension lines, ceiling / plinth lines | Cabinets elevation | Room -> Elevation (same SVG) |
| Attached panels travelling with their cabinet's drag | Cabinets elevation | Room -> Elevation (`data-host`) |
| Plan, layers, isolate, plan drag, plan zoom | Room tab | Room -> Plan |
| Walls, Placements, Gaps, Plinth cards | Room tab | Room -> Plan (hidden on Elevation) |
| The one editor (dock) | Cabinets / Room / 3D docks | the same three docks; Room's serves both sub-tabs |
| Editor's Save (refresh-only) | editor | editor — now also refreshes the Cabinets 3D |
| Cabinet list (select, Dup, Del, Add) | Cabinets, below the elevation | Cabinets, below the 3D |
| `<job>_elevation.svg` in the export | always written | **Removed** (brief) |
| `<job>_elevation_<wall>.svg` | every wall | the walls ticked at export |
| Plan in the export | — (never written) | `<job>_plan.svg`, always with a room |
| Starting tab | Cabinets | Boards (start-up and New) — **Catalogue -> Boards** since the drawers brief |
| 3D tab (room, handles, list, card, snapshot…) | 3D tab | 3D tab, unchanged; its module is now one `createView()` instance |
| Attached-panel drag in 3D (spec B4) | not built | Cabinets tab's 3D |
| Placing an item by drag from a list | not built (ruled not needed 21 Sept) | Room -> Plan, Room -> Elevation, 3D tab |
| Board library (list, add / edit / delete, tick, swap, pictures) | Boards tab | **Catalogue -> Boards**, unchanged (drawers brief, 28 Sept) |
| Runner lengths 350 / 450 / 500 | `Standard.runner_lengths` | `hardware.LEGACY` — a cabinet naming no runner; new work picks from Catalogue -> Runners |
| Drawer front deduct 59 | `Standard.drawer_front_deduct` | derived: 2 × the runner's `side_clearance` + two box sides (`Standard.drawer_front_length`) |
| A support's per-edge tickboxes (Front / Rear / Left / Right, Inner / Outer) | Supports section | **Long edges** and **Short edges** 0 / 1 / 2 in the same row; which edge a count means is `support_edges_for_counts` |
| "Cut from" / "Edging" / "Colour" on a support row | Supports section | **Support Material / Edging Material / Edging Colour**, same controls |
| Face-stack rules (H − 3 fill, elevation faces, plan faces, door above the stack) | read `drawer_list` | read `Cabinet.outer_drawers` — inner drawers are behind the door |
| "Box not shorter than its face" (`drawer-box-height`) | Validation | **Retired** — replaced by `drawer-box-face`, a box within its own face at its offset (ruling of 28 Sept) |
| A drawer box's height above its face | fixed at 21 | **Off.** column in the drawer row (`Drawer.offset`, blank = 21) |
| Plazaboard CSVs, `<job>_accepted.txt` | `output/<job>/` | `output/<job>/cutlist/` (output-folders brief, 28 Sept) |
| Sheet layouts `nest_<BOARD>.svg` | `output/<job>/` | `output/<job>/nesting/` (export and `regen_check`) |
| Plan, wall elevations, their board pictures | `output/<job>/` | `output/<job>/drawings/` |
| 3D snapshots `<job>_3d_<n>.png` | `output/<job>/` | `output/<job>/snapshots/` — never touched by an export |
| The last export, when a new one is written | overwritten in place (stale files lingered) | `output/<job>/_previous/`, one level |
| Playwright screenshots | `output/ui_check_restructure/`, `output/ui_check_drawers/` | `output/_checks/<script>/` |
| Runner dropdown, Catalogue…, the runner readout | Drawers, under the table | Drawers -> **Setup**, second row, ONE status line (Drawers redo, 29 Sept) |
| Drawer Mode (Share / Fixed), Value and mm columns | Drawers table | the **lock** in the Face height cell: locked = Fixed (typed), unlocked = Share, mm greyed beside the weight |
| Box h and its `≤` | Drawers table | **Box height**: `Auto (≤n)`, or the typed figure with `≤n` and an **Auto** button |
| Off. | Drawers table | **Offset**, the same field |
| Base per drawer | Drawers table | **Bottom** in Setup (the section's), and per drawer in its **differs…** sub-row |
| Box mat. / Face mat. per drawer | Drawers table | **Box board · Face board** in Setup, and per drawer in **differs…** |
| Box edging colour per drawer | the Box edging row under each drawer | **Box edging** (thickness + colour) in Setup, and per drawer in **differs…** |
| Face edging | Drawers, under the table | **Face edging** in Setup |
| The tape names beside the edging controls | printed beside them | the control's tooltip, the row's tooltip, and the cut list |
| + Face | Drawers | **+ Drawer** (a new row: Share, box Auto) |
| The three hint paragraphs | Drawers | **Gone**; one help line under each control |
| Outline section | every cupboard | **Plan shape**, only on a `template "none"` cabinet or one with a footprint |
| A wall turning the other way | a negative length (ran the wall backwards) | **Corner** column in Room -> Plan's Walls card: the angle of the corner after each wall, `B→C`, 90 / 270 / 135 / 225 / 180 / custom (walls brief, 29 Sept 2026) |
| Entering walls | typed, one row at a time | typed as before, **or Draw walls** on Room -> Plan (click the corners); drawn lengths marked **drawn** in the Walls card until measured |
| Walls card (Room -> Plan, under the plan) | one card: name, ceiling, offset depth, closed / open, the wall table | **Room card** in the Room tab's dock (nothing or the room selected): name, ceiling (mm), offset depth (mm), Draw walls, Renumber, Remove room, the walls in walk order; and a **Wall card** per wall (click it in the plan, or its row) — room redo Phase 1, 2 Oct 2026 |
| "+ Wall before / after" | the Walls card's two buttons, at either end of the chain | the **Wall card**'s "+ Wall after" / "+ Wall before", offered where that end meets nothing; at 90, the next free letter, nothing re-origined |
| Flip side (the whole open run) | the Walls card | **Flip face** per wall, in the Room card's Face column and the Wall card; a closed room's wall can be flipped too (it then meets nothing) |
| The Corner column (nominal angle, quick picks) | the Walls card | the Room card's **Corner after (°)** column (typed, derived off the points), and the Wall card's **corner before / after**: the angle to 0.1° and, near 90 / 180 / 270, the **out-of-square** mm at the offset depth |
| Offsets (offset start / end per wall) | the Walls card | gone from the model (read once for migration); the Wall card's out-of-square field is the way a site figure is typed |
| `Room.closed` ("walls form a loop") | typed on the room | **derived** (`room.is_closed`): the walls close when the chain returns to its start |
| A wall's id, typed by hand | the Walls card's first column | gone; **Renumber** (the Room card) re-letters along the walk, behind a confirm that lists the changes |
| Removing a wall | × on its row, the placements on it left orphaned | × on its row or **Delete** on its card, behind a confirm naming what becomes unplaced; the placements and decisions on it go |
| Draw walls | a button in the plan's header; REPLACED the room, re-oriented to +X | the **toolbar**'s Draw walls (Select is the default, Esc returns to it) and the Room card's button; ADDS to the room, starts on an existing corner clicked near, the points kept as drawn |
| Which side the room is | not shown | **shown**: a closed room's floor tinted; an open run's or a free wall's face side a fading band; the thickness hatched on the back |
| Wall height | — | the Room card's **Height (mm)** column and the Wall card (blank = the ceiling); the elevation and 3D draw the wall to it |
| Open / closed, the loop's miss | the Room card's own pill, the toast off `/api/wall-set` | **one answer, `room.closure`** — the pill, the table's open corner, the Wall card, the toast (off the compute), the plan, the 3D note, Validation — room redo Phase 2, 3 Oct 2026 |
| Draw walls' canvas | a grid canvas of its own (`#drawsvg`) swapped in for the plan | **the plan itself** (a mode: grid over it, cabinets ghosted, `#drawlayer`) |
| A wall's length | typed in the Room card or the Wall card | also **on the plan**: its length label is a text box (Enter, Esc, Tab to the next wall) |
| Reshaping the room | typed lengths and angles only | also **drag a corner** (its handle, on hover) or **drag a wall** by its body, with snaps (corner, alignment, angle, length), Shift free, Esc restores |
| Typed lengths while drawing | — | a digit opens a length box at the cursor; Tab the corner angle |
| A T-wall | — | Draw walls starting on a point of a wall: it is split there |
| A recess / nib | — | the toolbar's **Wall nook**: click a wall, width, depth, distance |
| A partition (two faces) | — | the Wall card's **Add back face** |
| Flip face on a closed room | flipped the one wall | asks: **Flip room** / Flip just B / Cancel |
| Gaps, Placements, Plinth cards | three cards side by side under the plan, notes in the cards | **Gaps** full width; **Plinth** and **Placements** side by side under it; notes behind a **?** |
| Select · Draw walls · Wall nook | a column of buttons left of the plan | the **strip** at the top of the Room tab, right of Plan \| Elevation, a segmented control, Plan only (touch-ups, 3 Oct 2026) |
| Placements card; Plinth's row | Placements beside Plinth under Gaps | **Placements** the left column beside the plan, the plan's height, its table narrowed (Item · Wall · X · Z · Y · Layer, five-digit inputs), scrolled within, Plan only; **Plinth** under Gaps on its own (touch-ups, 3 Oct 2026) |
| Placements (open / collapsed) | always open in the left column | **collapses** to a slim strip (chevron, "Placements" down its side), collapsed by default, remembered per viewer (`cupboard.places`) (round 2, 3 Oct 2026) |
| Room card / Wall card width | the editor's width (560, or as dragged) | **compact, 360**, always shown (the dock's collapse is the editor's); the Room card's fields on one row, small buttons, Wall · Length · Corner · Height · Flip · ×, Op. / Obs. in the row's tooltip, the help behind a **?**; the editor's width when a cabinet is selected (round 2) |
| A wall's length on the plan | outside along the normal, level whatever the wall's direction, clipped at the edge of an exported plan | **outside on the wall's back, turned to read along it** (a wall up the page reads upwards); the plan's bounds take every label in with `render.PLAN_LABEL_MARGIN` (150 mm) round it; a white backing (`rect.lenback`, 0.85) where it lies over a cabinet, panel, face, wall or gap mark (round 2, 3 Oct 2026) |
| Bringing another folder's work in (an old demo, the other laptop) | copied by hand | **Import project** in the top bar: pick the folder (or type its path without a window), a preview of every item, Import, a report (3 Oct 2026) |
| Renaming a project | Save under a new name, delete the old (output folder left behind) | **Rename** beside the job name: the file, `job.name`, `output\<job>\` and its files (3 Oct 2026) |
| Renaming a board picture's file | — | **Rename…** on the board's picture field: the file, every library board and saved job naming it (3 Oct 2026) |
| A name already taken (project, board, runner, picture; Save onto another job's file) | Save overwrote the other job; boards / runners took a duplicate name | refused, "<name> already exists — choose another name", under the field (3 Oct 2026) |
| `rename_board_in_job`, `LIVE_FIELDS` | `app/api.py` | `cabinetgen/boards.py` (api re-exports both) |
| Undo / Redo | — (none; a mistake was put right by hand) | **Undo · Redo** beside Save in the top bar, Ctrl+Z / Ctrl+Y / Ctrl+Shift+Z (not while typing in a field); 50 steps of the job on screen; Save, Load, New, Delete project, Export, snapshots and library edits are not undone (round 2, 3 Oct 2026) |
