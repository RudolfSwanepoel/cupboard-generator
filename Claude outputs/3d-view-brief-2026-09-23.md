# Brief for Claude Code — Part F: the 3D view, and one editor across every view

23 September 2026. Written in Cowork with Rudolf. **This replaces Part F of
`claude-code-brief-boards-colour-panels-3d-2026-09-20.md`** wherever the two
differ: that draft predates `room.solid_parts`, the mitre and blind corner
constructions, the Finish view and the line-weight table, so it proposed a
separate `assembly.py` and "simplified" corner units. None of that is needed
now.

Read this whole brief before writing code. Then read `CLAUDE.md` in full (it
is long, and most of what you need to know about how this app behaves is
there), `docs/ROOM-LAYOUT-SPEC.md` → **3D view**, and the code named in
**Step 0**.

---------------------------------------------------------------------------

## 1. What Rudolf asked for

> A new tab called **3D view**. Clever zoom and pan, like any parametric
> model — natural and intuitive. Select cupboards there, and the detail
> settings per cupboard shown and adjustable. Likewise for the elevation and
> plan views. Done the way a professional developer would enhance this
> application.

In practice that is four things:

1. **A 3D tab** that draws the room and every placed cabinet and panel from the
   same model the cut list comes from, in the boards' real colours and
   pictures.
2. **CAD-grade navigation**: orbit about the point you pressed on, zoom
   towards the cursor, pan that keeps the grabbed point under the cursor, a
   view cube, fit, standard views, perspective and orthographic.
3. **One editor, available everywhere**: selecting in 3D, in the plan or in
   the elevation brings up the same cabinet editor beside the drawing, and an
   edit redraws every view.
4. **Moving things in 3D**, built last, through the same snaps the plan and
   elevation already use.

## 2. Rulings recorded with this brief (23 September 2026)

| Question | Ruling |
|---|---|
| Parts whose position the app does not model (shelves, supports, drawer boxes, legs) | **Left out of the 3D view.** Nothing is guessed onto a drawing. The view draws what `room.solid_parts` draws (sides, top, bottom, fronts, blind panel, mitre construction, panels), plus the **back panel** and the **plinth boards** and **fillers** that were chosen, but only where the position comes out of rules already in `Standard` or `room.py`. Anything that cannot be placed that way is left out, and the view's legend says what is not drawn. |
| Mouse scheme | **Left-drag orbits, right-drag or middle-drag pans, wheel and pinch zoom towards the cursor.** Click selects. Shift+left-drag and Space+left-drag also pan, for trackpad use. |
| Dragging in 3D | **Yes, as the last stage (F6)**, along the wall and up/down, through `/api/drag`. Built only after F1-F5 pass their acceptance. |
| The editor across views | **One docked editor.** The same single `#editor` sits as a right-hand column on the Cabinets, Room and 3D tabs, follows the one selection, and can be collapsed. It is never copied: two editors would be two things that can disagree. |

Settled before this brief and still in force: three.js, **vendored**, no CDN;
the browser computes no dimension; all trigonometry in `room.py`; a drawing is
a read-only view of the model and nothing reads one back.

## 3. Hard rules (all existing, restated because 3D is where they get tested)

1. **The 3D scene is a drawing.** It never feeds a check, a cut-list line, a
   cost or a validation. `tools/check_scene.py` fails if `engine`, `validate`,
   `export_plaza`, `nest`, `room` or `store` imports the new scene module.
2. **The browser computes no dimension.** The server sends world-space
   vertices, heights, hinge axes, swing angles, snap targets and every figure
   the view prints. The browser builds meshes from them, rotates a door by the
   angle it is given, and picks the nearest snap from the list it is given.
   What it may do by itself is camera maths (orbit, pan, zoom, projection),
   because that moves the viewer and not the model.
3. **All trigonometry lives in `room.py`.** The scene module composes what
   `room.py` already answers. If it needs a new frame or projection, that
   function goes into `room.py` and is tested there.
4. **Declared width, height and depth are labels.** Every solid comes from
   `room.solid_parts` / `room.geometry`, never from `cab.width` and friends.
5. **Every colour comes off the Boards record** through `render.board_look`,
   and a picture wins over the colour **on a grained board only**, exactly as
   `render.Fills` rules it. No colour literal for a board anywhere in the 3D
   code; extend `check_colour.py` to scan the new files.
6. **Nothing reaches disk unasked.** View settings (camera, layers, display
   mode, fronts open, hidden items) are browser state, the same class of thing
   as `S.elevMode`. They are not written to the job file.
7. **The benchmark holds.** 272 MEL / 59 BROOKHILL / 30 BACK, 92 pot holes,
   18 / 9 / 6 boards, R28,363.50, and every `tools/check_*.py` green.
   `snapshot.py --compare` against the tree before this work must show **no
   change at all** to panels, issues, summaries, totals or drawings. This
   work adds a view; it must not move a single existing SVG byte.
8. **`Job.room is None` keeps working.** With no room the 3D view shows the
   cabinets side by side in the Run's order and spacing (taken from the same
   layout the Run drawing uses, not re-derived), on a plain floor, with a
   one-line banner saying there is no room.

---------------------------------------------------------------------------

## Step 0 — before any build

- **0.1** Run `Start Session.bat`'s equivalent: `git pull` on `master`. Note
  HEAD. The working tree is CRLF and HEAD is LF: review with
  `--ignore-space-at-eol`, and do not change any file's existing line endings.
  If `git status` shows modifications that are more than line endings, stop
  and ask Rudolf before touching them.
- **0.2** Run the full check list from `CLAUDE.md` and take a fresh snapshot
  (`tools/snapshot.py`) of the tree as it stands, to compare against at the
  end. `baseline.json` is known stale; use a new snapshot file for this work,
  do not overwrite `baseline.json`.
- **0.3** Read, in this order: `room.solid_parts`, `room.Part`,
  `room._placed_frame`, `room.front_outlines`, `room.wall_frames`,
  `room.to_world`, `room.carcass_z`, `room.geometry` / `CabinetGeometry`,
  `room.swing_envelopes` and the pull-out equivalent, `room.clashes`,
  `room.overlaps`, `room.runs` and the plinth panel code, `room.gaps` and the
  filler code, `room.snap_points` / `z_snap_points` / `y_snap_points`,
  `room.return_faces` (it already sorts and projects solids — the closest
  existing relative of what 3D needs), `render.board_look`, `render.Fills`
  (the picture tile size lives there), `render.elevation_svg` (the Run
  layout), `api.do_GET`, `api.drag`, `api.plan`, and in `app/index.html`:
  the tab switcher, `S`, `selectCabinet`, `paint`, `renderEditor`, the plan
  and elevation press handlers, and the zoom code.
- **0.4** Write down anything in this brief that the code contradicts, and
  resolve it in favour of the code's established rule, noting it in the final
  report. The brief was written without running the code.

---------------------------------------------------------------------------

## F1 — Vendoring, static routes, lazy loading

- **three.js**, vendored into `app/vendor/three/`, committed. Pin an exact
  version (the 20 Sept research found `three@0.186.0`, which needs
  `three.module.js` + `three.core.js`; use it or the current stable release,
  and record the choice and the file list in `CLAUDE.md`). Include its
  `LICENSE`. Only the addons actually used are vendored.
- **camera-controls** (yomotsu, MIT), vendored as its single ESM build into
  `app/vendor/`, with its `LICENSE`. It gives damped orbit/dolly/truck,
  `setOrbitPoint`, `dollyToCursor`, `fitToBox`/`fitToSphere`, animated
  `setLookAt`, and orthographic support, which is most of section F3 for free.
  Check the version is compatible with the pinned three.js. If it will not run
  in WebView2, fall back to three's `OrbitControls` (with `zoomToCursor`) and
  implement pivot-on-press yourself; say which was used.
- **Import map** in `index.html`: `three` → `/vendor/three/three.module.js`,
  addons and camera-controls under `/vendor/`. WebView2 supports import maps.
- **The 3D code is its own module, `app/view3d.js`**, not more of
  `index.html`. It is ~1,500 lines of a different kind of code, and loading it
  only when the 3D tab is first opened keeps start-up exactly as fast as it is
  now. `index.html` stays the whole of the rest of the UI and talks to the
  module through a small interface (`mount`, `update(scene)`, `select(n)`,
  `setLayers`, `dispose`). Vanilla JS, no build step, as everywhere else.
- **`Handler.do_GET` gains `/vendor/<file>` and `/app/view3d.js`**, built the
  way `_picture` is: a whitelist, the resolved path required to be inside its
  folder, correct `Content-Type` (`text/javascript`, `text/plain` for
  licences), and the same cache header as the rest.
- **Offline is the acceptance test.** With the network off, the 3D tab opens
  and works. The network log shows only `127.0.0.1` requests.
- **No WebGL** (old driver, blocked GPU): the tab says so in one line and the
  rest of the app is untouched. A lost WebGL context is caught and the view
  rebuilt when it is restored.

## F2 — `cabinetgen/scene.py` and `/api/scene`

**The scene is built on the server from `room.solid_parts`, and the browser
only draws it.** `solid_parts` already answers "what is this cabinet made of,
as solids in its own frame" for straight cabinets, mitres, blind corners,
panels, and — as one footprint solid, with no fronts — ells, bespoke cabinets
and anything else whose parts are not known. `room.front_outlines` already
shows the pattern for taking those solids into the world. Use both; do not
write a second assembly.

### What the scene contains

- **Every placed cabinet and panel** (`room.placed` + `room.placed_panels`):
  each `Part` taken into world plan coordinates through the placement frame,
  its z raised by `carcass_z`. An outline is convex and extruded straight up,
  so each part is sent as its world outline (list of XY points) plus `z0` and
  `z1`. The browser extrudes it; it does no trig.
- **The back panel**, added to the parts `solid_parts` returns — through a
  function in `room.py` (e.g. extend `solid_parts` behind a flag, or a
  `back_part` beside it) — positioned by `Standard.back_face_from_front` and
  sized by `Standard.back_size`, only when the cabinet actually cuts one. Not
  on a mitre (its back is the melamine wall panels, already drawn). If adding
  it to `solid_parts` itself would change any existing drawing, keep it out of
  `solid_parts` and add it only in the scene. Snapshot must show no drawing
  change.
- **Plinth boards and fillers that were chosen**, where `room.py` already knows
  where they stand (plinth: the run, `leg_height` high, `plinth_setback` back
  from the carcass front; filler: the gap it fills). If either position is not
  actually derivable from existing rules, leave it out and list it as not
  drawn. Do not add a constant to place it.
- **Not drawn, by ruling:** shelves, supports, drawer boxes, legs, hardware,
  hinges, handles, worktops. The view's legend has a short line: *Not drawn:
  shelves, supports, drawer boxes, legs (positions not modelled).* Base units
  therefore stand visibly on nothing at leg height where no plinth board was
  chosen. That is the truth, and it is what the plinth decision looks like.
- **The room**: the floor polygon, each wall as a plane from the floor to the
  ceiling along its face (`wall_frames`), each opening as a hole in its wall at
  its x, sill and head, obstructions as the data allows (a box if it has a
  depth, otherwise a marker on the wall face), and the ceiling height. An
  unmeasured ceiling sends no ceiling; the walls then stop a fixed drawing
  margin above the tallest unit and the view says the ceiling is not measured.
  That margin is a drawing constant in `scene.py`, named as one, read by
  nothing else.
- **No room**: the Run layout (see hard rule 8).

### What each part carries

| Field | Meaning |
|---|---|
| `id` | Stable across calls: `"<cabinet number>:<role>:<n>"`, keyed by cabinet **number**, never list index. The same job gives the same ids. |
| `cab` | The cabinet number, so a click can select it. |
| `role`, `index` | As on `Part`. |
| `board` | The board id; `look` gives its colour, grain and picture via `board_look`. Looks are sent once per board, not per part. |
| `outline`, `z0`, `z1` | World plan outline (mm) and heights. |
| `grain` | The grain direction as a world unit vector, or null. Used only to lay the picture texture the right way. |
| `line` | The cut-list designation this solid corresponds to (e.g. `0701`, `105a`), found by matching role and finished size against `generate_job`'s panels for that cabinet — or null with a reason (`"footprint only"`, `"not matched"`). |
| `layer` | Base / wall / tall / panels, from `room.layer_of` and the panel list. |
| `hinge` | Fronts only: the hinge axis as two world points and the opening angle with its sign, from `model.hinge_side` and `Standard.door_open_deg`. |
| `pull` | Drawer faces only: the pull-out direction and distance, from the same geometry the pull-out clash check uses. |

Per cabinet the scene also carries a **hash** of its parts, so the browser
rebuilds only cabinets that changed, and the figures the selected-cabinet
dimensions show (F4).

Clearance and validation overlays (F5) come in the same reply: the swing and
pull-out envelopes `room.py` already emits for the plan's hover, with their
height ranges, and the cabinet numbers carrying a critical or a warning from
the last validation, with the check id. Nothing is computed for the 3D view
that the plan or validation does not already compute.

### The endpoint

`/api/scene`, separate from `/api/compute` for the same reason `/api/plan` is:
a view change costs a redraw, not a re-nest. It takes the job and returns the
scene. It is read-only with respect to the job (pin it: deep-copy before,
compare after).

### `tools/check_scene.py`

- Ids unique, and identical across two calls on the same job.
- For every template cabinet in every job on disk: the union of its carcass
  parts, taken back into its own frame, matches `room.geometry`'s footprint
  and height; fronts stand proud by their board's real thickness.
- World vertices equal `room.to_world` of the cabinet-local corners (spot
  check several walls, including a non-square corner and a left-handed
  corner unit).
- z includes `carcass_z`: a standing base unit's bottom is at `leg_height`, a
  hung unit's at its own z, a panel's at its typed z.
- The hinge axis is on the side `model.hinge_side` names, for singles, pairs,
  a flipped placement and a mitre door.
- Every part with a `line` names a designation that exists on that cabinet's
  cut list; count the unmatched ones per job and pin the count (it should be
  zero for template cabinets).
- No part has a role that the ruling leaves out (shelf, support, drawer box).
- No room → parts in Run order, spacing equal to the Run drawing's.
- The scene call does not change the job.
- Grep test: none of `engine`, `validate`, `export_plaza`, `nest`, `room`,
  `store` imports `scene`.
- Timing: the October job's scene builds in well under a second; print it.

Add it to the check list in `CLAUDE.md` and to `Check It Still Works.bat`.

## F3 — The 3D view: drawing and navigation

### Layout of the tab

```
┌ toolbar: views ▾ | Persp/Ortho | display ▾ | Base Wall Tall Panels | Fronts | Clearances | Walls ▾ | Labels | Isolate | Snapshot | ? ┐
├──────────────┬─────────────────────────────────────────────────┬──────────────┤
│ item list    │                                     [view cube] │  editor      │
│ (collapsible)│                  viewport                       │  (docked,    │
│ #  kind  eye │                                                 │  collapsible)│
│              │ [part card]                        [legend]     │              │
├──────────────┴─────────────────────────────────────────────────┴──────────────┤
│ status line: what is under the cursor · hint for the current gesture          │
└────────────────────────────────────────────────────────────────────────────────┘
```

The viewport fills the height of the window below the tab bar; it never makes
the page scroll. It is resized with a `ResizeObserver`, pixel ratio capped at
2.

### Rendering

- **Z up, millimetres**: `camera.up = (0, 0, 1)`, world axes exactly as
  `room.py` defines them (X right, Y into the room from wall A, Z up). No axis
  swap anywhere.
- **Render on demand, not in a loop.** A frame is drawn when the camera moves,
  an animation runs, or the scene changes, and not otherwise. A laptop sitting
  on the 3D tab must not run its fan. Nothing renders while the tab is hidden.
- **Look**: a technical "shaded with edges" default — board colours on a
  standard material, hemisphere light plus one soft key light, thin dark edge
  lines on every part (`EdgesGeometry`), a light neutral background, a subtle
  100 / 1000 mm floor grid. The edge hierarchy follows `render.WEIGHT` in
  spirit (walls heaviest, then carcass, then fronts); the exact pixels are the
  view's choice. No shadows by default.
- **Display modes**: Shaded with edges (default), Shaded, X-ray (everything
  translucent so what is behind reads through). One dropdown.
- **Board pictures**: on a grained board with a picture, the picture is the
  texture, tiled at the **same real-world tile size `render.Fills` uses** (the
  server sends it with the look — no new number in the browser), laid with its
  vertical along the part's `grain` vector, and turned 90° where the grain
  requires, exactly as the elevation does. A plain board keeps its colour. A
  picture that fails to load leaves the colour. Textures are loaded from
  `/pictures/<name>`, one texture per board, shared across parts.
- **No z-fighting.** Fronts sit exactly on the carcass front face, and coplanar
  faces flicker. Fix it with material polygon offset per role (fronts pulled
  towards the camera), never by moving geometry. Near and far planes follow
  the scene's size so depth precision holds on a 6 m room and on a single
  cabinet.
- **Walls hide themselves.** Each wall plane is single-sided, facing into the
  room, so a wall between the camera and the room is simply not drawn from
  that side — the "nearest wall auto-hides" of the spec with no special code.
  Walls menu: Auto (default), All, None. Openings are holes. Ceiling: off by
  default, a toggle.
- **Obstructions are never lost**: drawn in a strong warning colour, and with
  Walls set to None they still show. Same principle as the plan, where they
  are drawn last.
- **Labels**: each item's number as a screen-space label over it (DOM overlay,
  not textured sprites), decluttered so labels do not sit on one another —
  the plan's rule (`render._place_labels`) applied in screen space: nearer
  items win, a label that does not fit is hidden, never stacked. Toggle.
- **Legend** (bottom-right, collapsible): the boards in view with their fill,
  exactly as the drawings' legend, plus the "Not drawn" line.
- **Updates keep the camera.** An edit anywhere rebuilds only the cabinets
  whose hash changed, disposes their old geometries, materials and textures,
  and never moves the camera or re-fits. Only an explicit Fit, a view preset
  or a double-click moves it.
- **No leaks.** After 30 consecutive edits `renderer.info.memory` returns to
  the same geometry and texture counts. Check it and report the numbers.

### Navigation (the "clever" part)

| Input | Action |
|---|---|
| Left-drag | **Orbit about the point pressed on.** On press, raycast the parts, walls and floor; the hit becomes the orbit pivot (shown as a small dot while orbiting). Nothing hit → keep the current pivot. The camera does not jump when the pivot changes. |
| Right-drag, middle-drag, Shift+left-drag, Space+left-drag | **Pan, with the grabbed point staying under the cursor** (pan at the depth of the point pressed on; nothing hit → at the pivot's depth). |
| Wheel, Ctrl+wheel, trackpad pinch | **Zoom towards the point under the cursor.** Speed proportional to distance, smooth, and clamped so the camera never passes through the point it is zooming to. In orthographic, zoom about the cursor too. The canvas owns the wheel: it is a full-height viewport, so there is no page to scroll behind it. |
| Click (press and release within ~4 px) | Select what is under the cursor (F4). Empty space clears the selection. |
| Double-click a part | Select its cabinet and fly to frame it. |
| Double-click empty | Fit all. |
| Right-click without dragging | Context menu (F4). |
| `F` | Fit selection, or everything if nothing is selected. |
| `H` | Home: the default isometric view of the whole room. |
| `T`, `I` | Top (plan), Isometric. |
| `1`-`9` | Face-on to wall A, B, C… in orthographic (the 3D twin of the wall elevation). |
| `P` | Perspective ↔ orthographic, keeping what is in view the same size at the pivot. |
| `O`, `C`, `X`, `L` | Fronts open, Clearances, X-ray, Labels. |
| `Esc` | Clear selection; cancel a drag in progress and restore. |
| `?` | Shortcut card. |

Shortcuts act only while the pointer is over the viewport or it has focus, and
never while a field is being typed in. **There is no destructive shortcut in
3D** — nothing is deleted or duplicated from a key.

- **View cube**, top-right: click a face, an edge or a corner to animate to
  that view (~300 ms, eased); drag it to orbit. It carries the wall letters on
  its sides where a wall faces that way, so "look at wall B" is one click.
  The views menu repeats these as named views (Iso, Top, Front of wall A…).
- **Orbit limits**: no roll; the camera may go a little below the floor
  (looking up under a wall unit is useful) but not flip over the pole.
- **Transitions are animated and interruptible**: a new gesture during a
  fly-to takes over at once.
- **Camera per job, per session**: switching away from the tab and back
  returns to the same view. Not saved to the job file. A newly loaded job
  opens at Home.
- **Trackpad**: two-finger click-drag is right-drag and pans; pinch zooms;
  Shift+drag pans. Put this on the `?` card; do not try to detect a trackpad.

## F4 — Selection, the part card and one editor across views

### One selection

`S.sel` stays the one selection in the app. A click in the 3D view, a click in
the plan, a press in the elevation, a row in the cabinet table or the 3D item
list all set it, and every view shows it: the 3D view with a highlight
(accent-tinted edges and a light emissive tint on its parts), the plan and
elevation as they do now.

**Selecting and isolating separate, for clicks in a drawing.** Today
`selectCabinet(i)` always isolates, which is right for a selection from the
list (it is how a cabinet hidden under another is reached — ruled 21
September). But in the plan an isolated view takes pointer events away from
everything else, so clicking to select would leave nothing else clickable.
So:

- `selectCabinet(i, {isolate: true})` from the cabinet table, Add, Duplicate
  and the 3D item list — unchanged behaviour.
- `selectCabinet(i, {isolate: false})` from a click in the plan, a press in
  the elevation, and a click in 3D. A click in the plan on a cabinet (press
  and release without moving) now selects it, which it did not before; a drag
  still drags and also selects what it dragged.
- The existing ways to end isolate are unchanged.

This changes one detail of the 21 September isolate ruling (clicking in the
plan now selects, without isolating). Say so in `CLAUDE.md` under **Isolate**.

In the 3D view, **Isolate** is a toolbar toggle (and context-menu item): it
ghosts everything but the selection at the house `0.30` opacity and makes the
ghosted parts unpickable, the same convention as the plan. It follows the
selection while on.

### Hover and the part card

- Hover highlights the part and its cabinet faintly; the status line names it:
  `7 · Tall · Door leaf 2 · BROOKHILL`.
- Clicking a part selects its cabinet and fills the **part card** (bottom-left
  overlay): cabinet number and kind, the part's role, its cut-list line
  (designation, finished L × W × thickness, board, grain `locked along L` or
  `free`, edging) read from the compute reply by the `line` the scene gave,
  and **Show in cut list**, which opens the Cut list tab scrolled to that row
  and highlighted. A part with no line says why (`footprint only — ell /
  bespoke`), which is the point of the spec's rule: "a panel cannot be
  admired in 3D and wrong on the list".
- **Selected-cabinet dimensions**: the selected cabinet shows three dimension
  lines — width, height, depth — drawn in 3D with DOM labels, the figures being
  `room.geometry`'s (sent by the server), never the declared ones.

### Context menu (right-click without drag)

Fit to this · Isolate · Open / close its fronts · Hide in 3D · Show all ·
Select in cut list. Hide is a view state (the item list's eye), not saved, and
the item list shows what is hidden so nothing is lost.

### The item list (left, collapsible)

Number, kind, a short description, an eye. Click selects **and isolates**
(like the cabinet table) and flies to it; this is how an item buried behind
others is reached, the same reasoning that put isolate on the list in the
plan. Unplaced items are listed greyed with "not placed".

### One docked editor

- The single `#editor` element is **moved** (re-parented, not cloned) into the
  dock slot of whichever of Cabinets, Room and 3D is showing. Its listeners are
  delegated on `#editor` itself, so they travel with it; `paint()` keeps
  working unchanged. Check that moving it loses no state and stacks no second
  handler.
- The Room tab gets a dock to the right of the plan. The Walls, Placements,
  Gaps and Plinth cards stay below as now.
- The dock collapses to a thin strip with a chevron; its open/closed state and
  width are remembered per viewer in `localStorage`, every access wrapped in
  `try/catch`, and the app works without it.
- With nothing selected the dock says "Select a cabinet in the drawing or the
  list" rather than showing an empty box.
- Every edit goes through `/api/compute` as now; the 3D view then asks
  `/api/scene` (debounced, only while the 3D tab is showing — a hidden tab
  refreshes when it is next shown) and rebuilds the changed cabinets. Target:
  an edit is visible in 3D within ~300 ms on `Test.json`.
- **Validation in the dock**: the selected cabinet's own criticals and
  warnings show at the top of the dock, one line each, linking to the
  Validation tab. They come from the compute reply.

## F5 — Fronts, clearances, layers and output

- **Fronts open / closed** (toolbar toggle for all; context menu for one
  cabinet). A door rotates about its `hinge` axis by the angle sent; a drawer
  face slides out along `pull`. Animated ~400 ms. Because drawer boxes are not
  drawn, a pulled-out face moves on its own; the clearances overlay shows the
  envelope it needs.
- **Clearances overlay**: the swing and pull-out envelopes `room.py` already
  computes for the plan hover, extruded over their height range, translucent;
  red where `room.clashes` reports a clash, neutral otherwise. Overlaps
  (criticals) outline both cabinets in red. All from the server.
- **Validation markers**: a small badge over a cabinet with a critical (red)
  or warning (amber); clicking it selects the cabinet and the dock shows the
  issue. Accepted criticals (tip-up) show greyed, as in the Validation list.
- **Layers**: Base, Wall, Tall, Panels, multi-select, **sharing `S.layers`
  with the plan** — one answer to "what am I looking at". Not shown is
  ghosted, not hidden, and a ghosted item keeps its hover, the plan's rule.
- **Snapshot**: saves the current view as a PNG into `output/<job>/`
  (`<job>_3d_<n>.png`, never overwriting) through a new endpoint that writes
  the bytes it is sent under `api._safe_name`. The toast names the file. For
  showing a client the design.
- **Export** is unchanged — the Plazaboard CSV and drawings — the 3D view adds
  nothing to the export folder unless Snapshot is pressed.

## F6 — Moving cabinets and panels in 3D (last stage)

Build only once F1-F5 pass their acceptance.

- A **selected** item shows a move handle: an arrow along its wall, an arrow
  up, and for a panel an arrow out from the wall. Dragging an arrow moves the
  item along that axis only. Dragging the item's body does nothing special —
  a left-drag on a part still orbits — so moving is always deliberate.
- On press, one `/api/drag` call (as the plan and elevation do) gives the
  snap targets, `leg_lift`, the wall's direction and normal in world terms and
  the mm-per-unit mapping. The browser projects the pointer onto the chosen
  axis, applies the grab offset, and takes the **nearest** candidate within
  `Standard.snap_tolerance`, ties broken the way the plan breaks them. It
  works out no position of its own.
- **Listen before awaiting**: the press attaches its listeners and calls
  `preventDefault` before awaiting `/api/drag`, and replays the last move and
  a release once the reply lands — the exact shape of `moveDrag` /
  `finishDrag`. A quick drag must not stick to the pointer.
- The status line shows the live figure and the snap reason ("level with 5",
  "on top of 3").
- The drop writes `Placement.x`, `.z` (and `.y` for a panel) and nothing else,
  then recomputes; overlaps and clashes show from that one compute. `Esc`
  during the drag restores the start position.
- **No moving onto another wall in 3D**, and no rotating. Changing wall stays
  in the plan.
- A cabinet on a ghosted layer or hidden in 3D cannot be moved.

## F7 — Optional, only if F1-F6 are done and time remains

Each is independent; build none of them at the expense of F1-F6.

- **Section plane**: a horizontal cut at an adjustable height (a live plan
  section) and a vertical cut parallel to a chosen wall, with three.js
  clipping planes. View only.
- **Measure**: pick two part corners (snapping to vertices the scene already
  sent) and read the distance, **computed by the server** (`/api/measure`),
  shown as a temporary dimension line. Not saved.

---------------------------------------------------------------------------

## Acceptance — live, in the running app

Exercise all of it in the app itself, driven by a real mouse in headless
Chromium as previous work has been (WebGL there needs SwiftShader:
`--use-angle=swiftshader --enable-unsafe-swiftshader`), and then report what
was exercised. Unit-level Python checks alone do not count.

On `jobs/Test.json` (13 items, a mitre, two placed panels):

1. The 3D tab opens with the network disabled; only local requests are made.
2. Every placed cabinet and panel is there, in the right place, at the right
   height, in its board's colour or picture; the mitre and panel 12 read the
   same as in the Finish elevation of wall A.
3. **Zoom to cursor**: wheel over a cabinet's corner; that corner stays under
   the cursor within a few pixels over ten wheel steps. Pinch the same.
4. **Orbit about the pressed point**: press on a door and orbit; the door
   stays put on screen while the room turns around it.
5. **Pan**: right-drag; the grabbed point stays under the cursor.
6. View cube faces, `H`, `T`, `1`-`9`, `P` and Fit all do what they say, and
   animate.
7. Click cabinet 7 in 3D → the dock shows cabinet 7, the plan and elevation
   show it selected, the part card shows the clicked part's cut-list line, and
   **Show in cut list** lands on that row.
8. Change cabinet 7's width in the dock → 3D rebuilds cabinet 7 only, the
   camera does not move, and the elevation and plan agree.
9. Click a cabinet in the plan → it is selected without isolating; click
   another → that one is selected. The list still isolates.
10. The dock appears on Cabinets, Room and 3D, is the same element, collapses,
    and remembers its state.
11. Fronts open: every door swings towards the side its hinge marks show in
    the elevation; drawer faces slide out. Clearances show red where
    Validation lists a clash.
12. Layers in 3D and in the plan are the same toggle.
13. Snapshot writes a PNG into `output/Test/`.
14. F6: move a wall unit along the wall and up onto "on top of N"; move panel
    8 out from the wall; a quick flick-drag does not stick; `Esc` restores.
15. 30 edits in a row: memory counts steady, no console errors.

Also: `jobs/Corner Unit Test.json` (blind corner inset panel and door where
`blind_spans` puts them), `jobs/Test_Panels.json` (all three orientations),
and the October fixture (no room → the Run layout, ~360 parts, orbiting
smooth, first draw in about a second or less).

## Verification protocol (after every stage)

1. `python tools/regen_check.py` — 272 / 59 / 30, 92 pot holes, 18 / 9 / 6,
   R28,363.50.
2. Every `tools/check_*.py`, including the new `check_scene.py`, passes.
3. `python tools/snapshot.py --compare <the snapshot from Step 0>` — **no
   difference at all**. This work adds a view; if an existing drawing, panel,
   issue or total moves, it is a bug until proven otherwise and reported.
4. Every job file on disk loads and saves back byte for byte.

## Documentation to update

- `CLAUDE.md`: a **3D view** section (what is drawn and not drawn and why, the
  scene payload, navigation, the one-editor dock, the select/isolate split,
  F6's drag), the new files in **Layout**, `check_scene.py` in the check list,
  the vendored versions, and the **Status** entry for this work in the same
  style as the others. Move "Next: Part F (3D). It is not started." to done.
- `docs/ROOM-LAYOUT-SPEC.md` → **3D view** and Phase 6: rewrite to what was
  built. Note that the spec's "Click a panel to show its label, size and
  cut-list line" is met by the part card.
- `docs/UI-BRIEF.md`: the dock and the 3D tab's layout.

## Not in this brief — do not build

- Shelves, supports, drawer boxes, legs, hardware, handles, worktops,
  appliances in 3D (ruled out today; shelf heights are their own future
  piece of work).
- An ell's or a bespoke cabinet's individual panels (still one footprint
  solid, as `solid_parts` rules).
- Editing geometry by pushing faces in 3D, rotating items, moving an item to
  another wall in 3D.
- Undo/redo (the app has none; do not start one here).
- Exploded view, CAD / DXF export, rendering to photo quality, VR.
- External corners (awaiting Rudolf's sketch).

## Report back with

- What was built per stage, and anything built differently from this brief
  and why.
- The acceptance list above, item by item, with what was actually exercised.
- Benchmark, check list, snapshot comparison and memory figures.
- Anything the code contradicted in this brief (Step 0.4).
- Open questions for Rudolf, if any, as short multiple-choice items.
- The exact commit message for Rudolf to paste into `Finish Session.bat`.
