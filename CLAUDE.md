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

## Hard rules

1. **A declared dimension must never feed a geometric check.** Declared
   depth/width are display labels only. Every check (footprint, overlap,
   door swing, tip-up, ceiling clash, fillers, scribes, elevations) must
   derive its geometry from the actual panel set via `room.geometry(cab)`.
2. **Panel designations never change once created.** No rename-in-place,
   no suffix matching. Generating a cut list is read-only with respect to
   the job model.
3. **The regression benchmark must hold** (Oct 2025 wardrobe job): 272
   MEL / 59 DECOR(BROOKHILL) / 30 BACK panels, 92 pot holes, 18/9/6
   boards, R28,363.50. Re-run and confirm it after any change that could
   touch geometry, nesting or costing, and quote the figures in the report.
4. Plazaboard cuts guillotine only, so no tapered or mitred cuts are
   possible. Tapers ship as rectangles at the widest dimension plus scribe
   allowance; mitres ship as square blanks and are cut on site.
5. The cut list gives FINISHED sizes. Plazaboard deducts edge tape itself,
   so never deduct tape thickness. Edging never moves a part in the model
   either: tape is drawn inside the finished size.
6. Every board characteristic (edging kinds, Edging Name, colour, picture)
   is entered only on the Boards tab. No hardcoded edging anywhere.
7. Door and drawer-face grain runs VERTICAL (Length = face height). This
   is correct; never question it.
8. Each dimension is entered in exactly one place in the editor. Panel →
   Panel design; corner unit → Corner Unit section; everything else is
   greyed and shows the derived value.
9. No current function may be lost in any change. Anything that moves
   is listed in the "Where every moved function lives now" table in
   `docs/HOW-IT-WORKS.md`.

Run every brief under `docs/BRIEF-PROTOCOL.md`.

## Check before you commit

```
python tools/check_all.py
python tools/snapshot.py --compare baseline.json
```

`check_all.py` runs `regen_check.py` and then every `tools/check_*.py` in name
order, each in its own process, and ends on a PASS / FAIL line per script and a
count; it exits non-zero if any failed. **There is no hand-kept list**: a new
`check_*.py` in `tools/` is run the next time. `Check It Still Works.bat` calls
it. It does not run the Playwright scripts (they need the app running) or the
snapshot compare (`baseline.json` is per-machine and known stale); it says so.
`regen_check` is a report, not a pass/fail — it fails there only by crashing —
so its benchmark lines are repeated in the summary to be read.

And, with the app running (`python run_app.py --no-window --port 8766`) and
Playwright installed, `python tools/ui_check_3d.py` drives the 3D view with a
real mouse in headless Chromium, `python tools/ui_check_attached.py` the
attached-panel editor, drags and dialogs, and `python tools/ui_check_restructure.py`
the UI restructure (tab order, Room -> Plan / Elevation, the Cabinets tab's 3D,
the attached-panel drag, placing from the unplaced list, export by wall), with
screenshots into `output/_checks/ui_check_restructure/`, and `python tools/ui_check_drawers.py`
the drawers / runners / supports brief (Supports' counts, Catalogue -> Boards |
Runners, the runner library and swap, drawer boxes in 3D) and the Drawers
section redo (stages `layout`, `lock`, `auto`; `3d` measures the runner's
inner member sliding), screenshots into
`output/_checks/ui_check_drawers/`, and `python tools/ui_check_walls.py` walls at
any angle and Draw walls (stages `draw`, `ell`, `corner`, `input`, `drag`, `3d`),
screenshots into `output/_checks/ui_check_walls/`, and `python tools/ui_check_undo.py`
Undo and Redo (four edits undone back to the loaded job and redone, one step
per edit, Ctrl+Z in a text field left to the field), and `python tools/ui_check_import.py`
Import project and the project Rename (stages `import`, `rename`) — this one STARTS
ITS OWN COPY of the app in a temp folder on a free port, because Import writes jobs
and libraries, so it needs no app running and never touches the live files;
screenshots into `output/_checks/ui_check_import/`. All seven are optional —
Playwright is the only third-party package anywhere near this app, and only
those scripts need it — and each says so and exits 0 when it is not installed.
`ui_check_3d.py --stage look` reads the drawn colour of a board off the canvas
(the 3D realism brief, 29 September 2026), and `python tools/ui_shots_3d.py`
takes the brief's four screenshots.
The cloud machine's Chromium is revision 1194, which is `playwright==1.56.0`.

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

**The cabinet-by-cabinet diff needs the real cut list, which is not in the repo.**
It is expected at `..\..\Wardrobes\R Swanepoel Cutlist.xlsx`, two levels above
`CupboardApp` — a machine without it gets everything above except the 22-of-30
line, and `regen_check` says so rather than failing. Every other figure in this
list comes out of the engine and is checked on any machine.

## Status

- **Core and cut list** — Plazaboard CSV columns and edging names; export
  folder organised (28 Sept 2026).
- **Boards** — every attribute on the Boards record; colour and pictures
  drawn (Parts A–C, 20–22 Sept 2026).
- **Panels and attached panels** — cut and placed (20–21 Sept 2026); attached
  to a cabinet (28 Sept 2026).
- **Corner units** — mitre and blind generated, ell shape-only, blind panel
  inset (22 Sept 2026).
- **Supports, drawers and runners** — typed supports (27 Sept); runners, FACES
  LEAD, BOXES FOLLOW (28 Sept); Drawers redone (29 Sept 2026).
- **3D** — the 3D view, one editor everywhere (23 Sept 2026); drawn
  realistically, Rounds 1–2 (29 Sept 2026).
- **UI** — restructure Sessions 1–2 (28 Sept 2026); one maximised window,
  `check_all` (29 Sept 2026).
- **Room** — walls at any angle (29 Sept 2026); redo Phases 1–2, touch-ups,
  Undo (2–3 Oct 2026); Phases 3–4 not built.
- **Demo build** — Nuitka zip, expires 60 days after the build (30 Sept 2026).
- **Import project and project renaming** — preview, report, Rename, a taken
  name refused (3 Oct 2026).

History and the reasoning behind each decision: `docs/HISTORY.md`.

## Layout

```
cabinetgen/standard.py     every construction constant. Start here. (drawer_box_clear 2: a
                           drawer box never flush in its face — 29 Sept 2026)
cabinetgen/boards.py       the board library: load, save, tape names, job usage
boards.json                the library itself, shared through the repo
cabinetgen/hardware.py     the hardware catalogue: runners (LEGACY, the Gelmar seed, load,
                           save, resolve; the inner member and its estimate; REQUIRED /
                           missing, what a record must state); hinges and handles later
hardware.json              the catalogue itself (`runners` list), shared through the repo
cabinetgen/pictures.py     board pictures: Pictures/, what is stored, what is served
Pictures/                  the board pictures themselves, shared through the repo
cabinetgen/model.py        Panel, Drawer, Cabinet, Job
cabinetgen/engine.py       cabinet -> panels
cabinetgen/drawers.py      drawer stacks: equal, graduated, pinned or exact
cabinetgen/validate.py     criticals block export, warnings do not
cabinetgen/nest.py         guillotine nesting + sheet layout SVGs
cabinetgen/render.py       SVG drawings: side-by-side elevation, plan, per-wall elevations
cabinetgen/scene.py        the 3D scene, built here from room.solid_parts and only DRAWN
                           in the browser. Nothing reads it back.
cabinetgen/room.py         walls as positioned segments (2 Oct 2026): connections, the walk,
                           corner angles, closure derived; set_length / set_corner / add_wall /
                           flip_face / renumber_walls / delete_wall; walls_from_points (Draw
                           walls, adds); _legacy_frames (migration only); to_world. Phase 2
                           (3 Oct): closure (THE open/closed answer), corner_move, wall_move,
                           keep_on_walls, room_snaps, split_wall, wall_nook, add_back_face,
                           flip_room. The only trigonometry.
cabinetgen/store.py        job files: JSON save / load
cabinetgen/importer.py     Import project: which folder is an app folder, the preview (scan),
                           identical / renamed "(imported n)" / broken, the re-pointing, and
                           writing it (run). Reads the old folder only
cabinetgen/export_plaza.py Plazaboard CSV + costing off the real rate card
run_app.py                 starts the local server, opens the window (maximised); under
                           pythonw logs to output/app.log and says in a message box
                           when it cannot start or is already running
output/app.log             the last pythonw run's output (a refused second launch
                           appends). Not in git — output/ is ignored
Make Desktop Shortcut.bat  run once per laptop: Cupboard App.lnk on the desktop,
                           pythonw run_app.py, no console
Start Cupboard App.bat     the console launch, for when something breaks
Check It Still Works.bat   python tools\check_all.py, then the 22-cabinets reminder
Build Demo.bat             the demo zip: python tools\build_demo.py (see Demo build)
app/demo.py                demo mode: off unless the build wrote app/_demo_build.py
tools/build_demo.py        Nuitka build, data copied in by name, zip, zip listing
demo/, build-demo/         the demo zips and Nuitka's working folders. Not in git
app/cupboard.ico           the shortcut's icon
app/api.py                 request handlers. Thin — they call cabinetgen.
app/index.html             the whole UI. Vanilla JS, no build step.
app/view3d.js              the 3D view: a module loaded the first time a 3D view is shown;
                           `createView()` makes one view — the 3D tab's and the
                           Cabinets tab's single-cabinet one
app/vendor/three/          three.js 0.186.0 — three.module.js, three.core.js, LICENSE
app/vendor/camera-controls/  camera-controls 3.1.2 — camera-controls.module.js, LICENSE
app/vendor/three/addons/   three r186's own addons the view imports as `three/addons/…`
                           (the importmap): lines/ — LineSegments2, LineSegmentsGeometry,
                           LineMaterial (the selection outline, the fronts' lines);
                           postprocessing/ GTAOPass, Pass; shaders/ GTAOShader,
                           PoissonDenoiseShader, CopyShader; math/ SimplexNoise
                           (ambient occlusion, Round 2); LICENSE
jobs/                      the live job folder: Test.json (the working file; its
                           cabinet 8 is the PLACED panel fixture) and
                           wardrobe_oct2025.py, the benchmark. Nothing else the
                           checks read lives here — see tools/fixtures/.
                           _deleted/ is the app's bin.
tools/check_all.py         runs regen_check then every tools/check_*.py, found not
                           listed; a PASS / FAIL summary; non-zero if any failed
tools/check_launch.py      the launcher: no-console logging, "already running", the
                           exclusive bind, the maximised window call. Windows only:
                           anywhere else "skipped: Windows only", exit 0
tools/regen_check.py       the regression check above
tools/check_examples.py    verifies the worked examples in docstrings are true
tools/check_room.py        room geometry on points: migration (every legacy room within 1 mm,
                           exact where it should be, load->save->load stable), walk, renumber,
                           flip_face, height, single_wall, touching, delete; closure, to_world,
                           the plan, isolate, the job file; the angled-room pins (L / hexagon /
                           splay / bay, crossing walls, drawn walls, ruling 4, plinth butt,
                           gaps, elevations, 3D floor, swing, tip-up); Phase 2: closure_text,
                           corner_move, wall_move, snaps, split, nook, backface, flip_all
tools/check_fillers.py     gap detection, taper, scribe, filler panels
tools/check_plinth.py      runs, butt joints, long-run splits, plinth panels
tools/check_drag.py        overlaps, snap targets both axes, swings, pull-outs;
                           and what a corner unit cuts, mitre and blind
tools/check_elevation.py   per-wall elevations: chains close, plinth heights, hinges;
                           Line / Finish, plan faces, line weights
tools/check_edging.py      Has Edging, the kinds a board offers, its colour
tools/check_single_source.py  the one list of which cabinet fields hold a board
tools/check_swap.py        a swap moves every use of a board, and says what it does
tools/check_colour.py      board colour in the drawings, and the ink that reads on it
tools/check_panels.py      independent panels: the line they cut, and what they stay out of
tools/check_pictures.py    board pictures: stored, served, drawn, grain-checked
tools/check_accept.py      accepting a site-dependent critical, and the acceptance lapsing
tools/check_scene.py       the 3D scene: ids, parts vs geometry, to_world, carcass_z, hinge
                           sides, cut-list lines, Run order, read-only, no reader of it
tools/check_supports.py    typed supports: the worked positions, what each cuts, the three
                           criticals, legacy rows unchanged, tape inside the size, the scene
tools/check_runners.py     runners: the catalogue, LEGACY, the length and width a runner gives, the
                           swap, the delete guard; the drawer setting; the drawer checks;
                           drawer box edging per drawer (29 Sept 2026); the Drawers redo:
                           section defaults, overrides, box edging thickness, the inner
                           member, R4, Auto, Test.json onto Gelmar (29 Sept 2026)
tools/check_export.py      the Plazaboard CSV: columns, one number per panel, Boards-tab edging
                           names, and the October job against Plazaboard's own files
Sample Plaza cutlist and quote/  Plazaboard's CSVs and quotation for the October job — the
                           reference check_export.py compares against
tools/ui_check_drawers.py  the drawers / runners / supports brief, and the Drawers section
                           redo (layout, lock, auto), in the running app (Playwright)
tools/check_attached.py    attached panels: derived place, attach/detach round trip, moves with
                           the cabinet, the room checks in and tip-up out, delete, duplicate,
                           the job file; and a new cabinet's supports by kind
tools/ui_check_3d.py       the 3D view in the running app, with a real mouse (Playwright);
                           --stage look: a board's colour on screen, the outline selection
tools/ui_shots_3d.py       the four 3D screenshots the realism brief compares, before and after
                           (Playwright), into Claude outputs/3d-realism-screenshots/
tools/ui_check_attached.py attached panels in the running app (Playwright)
tools/check_import.py      Import project and the renames, on temp folders only: a fake old demo
                           (identical / conflicting / chain-room / broken / newer jobs, boards,
                           runners, pictures), preview writes nothing, exactly what is written,
                           the cost loaded there and here, twice brings nothing, every rename
                           and every taken name
tools/ui_check_import.py   Import project and Rename in the running app (Playwright) — starts its
                           OWN copy of the app in a temp folder; stages import, rename
tools/ui_check_undo.py     Undo and Redo in the running app (Playwright): a plan drag, a typed wall
                           length, a delete, a drawer face, undone back to the loaded job and redone;
                           a new edit clears Redo; Ctrl+Z in a field is the field's; the Placements pick
tools/ui_check_walls.py    the Room tab on positioned walls (Playwright): the toolbar, the Room
                           and Wall cards, Draw walls ON the plan, a one-wall room, Flip face,
                           Renumber, wall height, refused inputs, a drag onto a 45-degree wall,
                           3D; Phase 2: closure (every display), layout, cornerdrag, walldrag,
                           align, angle, label, typedraw, split, nook, flipall; screenshots
                           into output/_checks/ui_check_walls/
tools/ui_check_restructure.py  the UI restructure in the running app (Playwright),
                           with screenshots into output/_checks/ui_check_restructure/
tools/fixtures/            frozen job files the checks read. Never reachable from the app.
                           Test_Build.json, Test_Panels.json (the cut-only panel
                           fixture) and Corner Unit Test.json since 28 September 2026,
                           beside Test_Build_pre_library.json and Test_legacy_supports.json;
                           Test_drawers.json (Test.json before f4d87b0) for check_runners;
                           Test_export.json (Test.json at 201d360) for check_export;
                           Test_3d.json (Test.json at 14a5ea7) for ui_check_3d and
                           ui_shots_3d.
tools/fixture_jobs.py      job_file(name): jobs/ for Test.json, tools/fixtures/ for the
                           rest. Every check and snapshot.py read job files through it.
tools/snapshot.py          every panel, issue, cost and drawing hash, for --compare
docs/RULES.md             where each rule came from and what it cost to learn
docs/ROOM-LAYOUT-SPEC.md  the room / plan / 3D build spec and its phasing
docs/BRIEF-PROTOCOL.md    how every brief is run, in seven steps
docs/HOW-IT-WORKS.md      how each area works; "Where every moved function lives now"
docs/HISTORY.md           every Status entry as written, newest first; index of docs/history/
docs/history/             one write-up per brief, <brief-file-name>.md
```

## Key ruled numbers

Scribe allowance 15 mm · taper threshold 6 mm (across the cabinet's
depth) · filler width 50–150 mm · plinth height 100 mm, setback 50 mm ·
legs 98–122 mm (nominal 100), always present on base-family carcasses ·
rear leg setback 50 mm · back/base groove 8 mm deep, 6 mm engagement ·
16 mm cavity behind backing · door gaps 3 mm single / 6 mm pair ·
hinge_clearance 50 mm · mitre_shelf_clear 3 mm · arm-shelf max depth
rounded down to the nearest 5 mm · panel and blind-panel code 08 ·
support W − 32 × 100, code 04 · new-cabinet supports: base Front + Top
Rear + 2 Back, wall 3 Back, tall 4 Back, mitre/ell none, blind by kind.

## Conventions

- All dimensions in mm, integers. No floats in panel sizes.
- `Length` is the larger dimension on grain-free panels; on décor it is the grain
  direction and must not be swapped.
- Panel codes follow Plazaboard's scheme. `09` (divider) is ours — the old lists
  coded the same part as `08` in some cabinets and `99` in others.
- A designation must never sit on two different panels, and **a designation
  never changes** (ruled 14 September 2026). Generated panels are named as they
  are created — `engine.born_distinct` gives 105a / 105b where one code covers
  two different panels (any difference but the qty: `model.panel_signature`,
  28 September 2026), identical ones sharing a letter and staying separate
  lines — and nothing is renamed afterwards. `generate_job` is read-only
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

## Open items awaiting Rudolf's ruling — don't guess these

- `offset_depth` default and sign convention
- Plazaboard sign-off on codes 10 (Plinth) and 11 (Filler/Scribe)
- Kitchen appliances as room objects with clearances
- Worktops: ruled 2 Oct 2026 that worktops and table tops are post-form
  or stone, never cut by this app, drawing only, and later — how they are
  drawn is open
- Ell corner construction
- Bespoke cupboard shapes generally
- where the legs stand, for drawing them — only the rear setback (50) is
  ruled (Per-wall elevations; that paragraph also names the offset and the
  appliances / worktops above)
- Q1 line endings and git hygiene; proposed hard rules H5 / H6 (Parts A–C,
  20 Sept 2026)
- a corner unit at a corner that is not a nominal 90: construction not ruled
  (walls, 29 Sept 2026)
- Plazaboard keyed PVC WHITE as BROOKHILL; Test.json cabinets 4–5's edging;
  their 2730 × 1300 line (CSV, 28 Sept 2026)
- Test.json cabinet 4's drawer criticals; the Gelmar price and inner member
  37 × 6 until drawing 04227 is read (drawers, 28–29 Sept 2026)
- pinch zoom, AO, key light, plaster, white 241 not 247, plank width, the
  193 / 160 mm tile — felt on the laptop (3D realism, 29 Sept 2026)

Ruled 2 Oct 2026 (Brief 0): a **peninsula** is a run of ordinary base units of
the island Kind standing end-on to a wall, placed free (room Phase 4), with an
attached end panel; a **table nook** is out of scope. Ruled 3 Oct 2026, not
built yet — follow-up brief: on Import a board or runner differing only in
price is identical, this library's price kept; the jobs a demo shipped with
are left out.

## Things that will bite you

- Plazaboard's `holes` column is the **line total** (per panel × qty). Ours is
  per panel. `export_plaza.rows_for` does the multiplication — don't double it.
- The CSV is `Customer Number` (our designation) in front of Plazaboard's
  template, byte for byte: `Component` is THEIR item number and `Material` the
  board id. `check_export.py` reads their header off their own file. Never
  merge lines, never pad.
- Edging includes a **70 mm trim allowance per banded edge**. The formula in
  `Standard.edging_m` is exact on all 166 edged rows of the real job. Don't
  "simplify" it.
- Grain must be 1 on every décor panel. On the last job it was 0 on all 60 and
  only Plazaboard's counter caught it.
- A panel longer than 2750 mm cannot be cut. One got through last time and came
  back 152 mm short with nobody told.

## The demo build

`Build Demo.bat` makes `demo\Cupboard App Demo <build date>.zip`: the whole
app, compiled by Nuitka, no Python needed. It stops working 60 days after the
build — build again to extend. Full detail: `docs/HOW-IT-WORKS.md`, Demo build.

## Where the detail lives

`docs/ROOM-LAYOUT-SPEC.md` (the room / plan / 3D spec and every ruling),
`docs/HOW-IT-WORKS.md` (how each area works), `docs/HISTORY.md` and
`docs/history/` (every entry and brief write-up), `docs/RULES.md`,
`docs/UI-BRIEF.md`, `Claude outputs/` (the briefs themselves).
