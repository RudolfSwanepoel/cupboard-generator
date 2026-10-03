# CupboardApp — history

Every Status entry as CLAUDE.md held it, newest first, unedited. The reasons
and the measured figures behind each decision are here; what a session must
know is in `CLAUDE.md`, and how each area works in `docs/HOW-IT-WORKS.md`.

## Brief write-ups in `docs/history/`

- `brief-0-protocol-and-claude-md-2026-10-02.md` — the brief protocol, and
  CLAUDE.md slimmed (3 October 2026)
- `import-followup-brief-2026-10-03.md` — Import follow-up: a price-only
  difference identical, the jobs a demo shipped with left out, two Playwright
  checks repaired, CLAUDE.md under 3,400 words (3 October 2026)

## Status entries, newest first

### Import follow-up (3 October 2026)

**Import follow-up (3 October 2026, brief
`Claude outputs/import-followup-brief-2026-10-03.md`, ruled by Rudolf).** On
Import a board or runner differing from this library's only in its price is
identical (skipped, this library's price kept); the jobs a demo shipped with
(`jobs\shipped-jobs.json`, written by `tools/build_demo.py`) are listed
`shipped` and left out; a folder without that list has every job considered
and the report says so. `ui_check_3d.py` stage `room` repaired (the script);
`ui_check_walls.py`'s nook-room label line repaired (the app: Esc refits a
typed wall length's box, approved by Rudolf). Benchmark unchanged. Write-up:
`docs/history/import-followup-brief-2026-10-03.md`.

### CLAUDE.md's ten Status lines, as they stood before the fold (3 October 2026)

Folded into one line in CLAUDE.md by the import follow-up brief (Part 3);
kept here word for word.

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

### Import project, and renaming a project (3 October 2026)

**Import project, and renaming a project (3 October 2026, brief
`Claude outputs/import-project-brief-2026-10-03.md`, ruled by Rudolf).**
Nothing under `cabinetgen/` that cuts, nests or costs moved: benchmark
unchanged (272 / 59 / 30, 92 pot holes, 18 / 9 / 6, R28,363.50), `check_all`
24 of 24 (`check_import.py` new), `snapshot.py --compare`: identical. One commit
per ruling group: 3 / 5 / 9 (the importer), 1 / 2 / 4 / 8 (the button, the
folder, the preview, the report), 6 / 7 (renames, a taken name refused).

1. **Import project** (top bar, beside Delete; the same in the demo —
   `app/demo.py` does not touch it). The native folder picker
   (`/api/pick-folder`, pywebview `FileDialog.FOLDER` on the window
   `api.set_window` holds); with no window (`--no-window`, the browser
   fallback) the dialog says there is no folder picker and takes a typed path.
   **`cabinetgen/importer.py` decides everything**: `find_folder` (the picked
   folder, then `Cupboard App Demo` inside it, then any folder directly inside
   it, must have `jobs\` with a readable job, or `Cupboard App Demo.exe`
   beside `jobs\`; this app's own folder is refused), `scan` (the preview,
   writes nothing: every item `new`, `identical`, `renamed` or `broken`, and a
   `signature`), `run` (scans again, refuses if the folder changed since the
   preview, writes pictures, then the libraries, then each job — test-loaded
   first through the app's own Load path, `api._import_test_load`). Reads the
   old folder only: `jobs\*.json` (never `_deleted\`), `boards.json`,
   `hardware.json`, `Pictures\`; never `output\`, `demo-seen.txt` or the app's
   files.
2. **A conflict comes in as `<name> (imported)`, `(imported 2)` …**, names
   compared case-insensitively; every candidate already here is first asked
   whether it is the SAME thing (a board or runner equal but for id and name, a
   picture's bytes, a job's text) — which is why importing a folder twice
   brings nothing. A renamed board gets `boards.next_id`, a renamed runner
   `hardware.next_id`, never an id any imported job names; every imported job
   is re-pointed (`rename_board_in_job` — moved to `cabinetgen/boards.py`
   with `LIVE_FIELDS`, `api` re-exports both) BEFORE it is saved, and its
   runner copy re-keyed and shown under the new name; a renamed picture
   re-points every imported board and job copy. **Two things the brief did not
   spell out, done to keep its rule "costs exactly what it cost there":** (a) a
   board renamed whose Edging Name was blank (named off its board name) takes
   the old name as its Edging Name, so the edging on the order does not change
   with the board's name; (b) a job naming a board the OLD library no longer
   has, whose own copy differs from THIS library's board of that id, would be
   refreshed into this library's board on Load: that copy comes in as a board
   of its own, "(imported)", and the job is re-pointed. A job's captured
   prices are never touched (its copy is re-keyed only; Load's
   `refresh_from_library` brings the new name and keeps the price).
3. **Old jobs through `store.job_from_dict`** (a chain room migrated) and
   saved in the current format; **a newer version's job** (a field this app
   does not know — `importer.unknown_fields`, against the dataclasses'
   fields and the legacy keys migration reads) as it stands: its raw JSON,
   only the name and the re-pointing changed (`boards.map_cabinet_board_ids`,
   the raw twin of `rename_board_in_job`, held equal to it in
   `check_import.py`); the report says so. Every job in the repo's history
   reads as not newer.
4. **The report** (copyable): "Imported 4 projects, 3 boards, 2 runners, 2
   pictures. Skipped 5 identical. Renamed: Test → Test (imported), …", then a
   line per job not imported (with the reason) and the newer-version jobs.
5. **Renames.** Project: **Rename** beside the job name → `/api/job-rename`:
   the file in `jobs\`, `job.name` in it, `output\<_safe_name>\` and every
   file in it whose name starts with the old safe name (`cutlist\`,
   `nesting\`, `drawings\`, `snapshots\`, `_previous\`), a move; the job on
   screen follows (`S.file`, the undo history's snapshots take the new name);
   a project never saved changes only its name on screen. Picture: **Rename…**
   on the board's picture field → `/api/picture-rename`: the file in
   `Pictures\` (its ending kept), every library board and every saved job's
   copy naming it, and the project on screen. Board: as built (`board_save`
   with `from`). Runner: its name, as built — **its id stays a key; nothing
   needs it renamed** (it is never shown where a name is).
6. **A name taken is an ERROR and nothing is written** (`importer.taken_message`,
   "<name> already exists — choose another name"), case-insensitively, under
   the field: the project Rename, a picture rename, a board's or runner's
   name changed or new (asked only when the name changes, so a library already
   holding two of a name can still have either edited), and **Save**: the
   browser sends the file it came from (`open`, `S.file`, set by Load and
   Save, cleared by New); saving under another saved job's file name is
   refused, under its own name (any case) it writes its own file as ever.
7. **The top bar** gained two buttons and is held to one row at 1360 wide with
   "unsaved changes" showing: gaps 5, button padding 5 / 8, the name box 150,
   the job list 150.

Playwright: `ui_check_import` (new, both stages), `ui_check_undo`,
`ui_check_restructure` (all its lines, the three `attach` lines included),
`ui_check_attached`, `ui_check_drawers` pass; `ui_check_walls` but for
`--stage labels`' "the nook room: none on another" (`A/G`), and `ui_check_3d`
but for stage `room` timing out on its plan drag (every other stage passes) —
both exactly the same on the tree before this work (427f68b, run in a
worktree): not this brief.

**A real old demo folder, simulated** (the 30 September build's data, run on
that commit's own code, a job saved, a board added with its own picture, a
board's price edited, a snapshot taken; then imported into a copy of this
app): the folder held nothing the brief did not name — `jobs\`, the two
libraries, `Pictures\`, `output\` (`demo-seen.txt`, the snapshot), the
app's own `app\` files, the exe. What it showed: **(a)** the jobs the demo
SHIPPED (Test.json) come back "(imported)" whenever yours have moved on since
the build — they are not the friend's work; **(b)** a board whose only
difference is its Last price comes in as "<name> (imported)", and the
friend's jobs on it are re-pointed to it (the record differs, ruling 5) —
their cost does not move, the price is captured in the job; **(c)** the
friend's job, saved by the 30 September code as a wall chain, is migrated
and loads.

**For Rudolf:** (a) and (b) above — whether a price-only difference should
count as identical (the library keeping its own price), and whether the jobs
a demo ships should be left out of an import, are yours to rule; built as
the brief says.

### Room touch-ups round 2, and Undo (3 October 2026)

**Room touch-ups round 2, and Undo (3 October 2026, brief
`Claude outputs/room-touchups-2-and-undo-brief-2026-10-03.md`, ruled by
Rudolf).** One commit per part; nothing that cuts, nests or costs moved:
benchmark unchanged (272 / 59 / 30, 92 pot holes, 18 / 9 / 6, R28,363.50),
`check_all` 23 of 23, `snapshot.py --compare`: panels, issues and totals
identical, Test.json's plan SVG moved (its labels, and their backing).

1. **The plan has the screen.** Placements collapses to a slim strip (the
   dock's pattern, "Placements" down its side), collapsed by default,
   remembered per viewer (`cupboard.places`, `placesShow`). The Room card and
   the Wall card are **compact, 360 wide** and always shown — the dock's
   collapse is the editor's (`.dock.cardmode`): Name · Ceiling · Offset depth
   on one row, the pill and counts on one line, small buttons, the table Wall
   · Length · Corner · Height · Flip · × with the openings / obstructions in
   the row's tooltip, the help behind "?" (`S.helpOpen` keeps a "?" open
   across repaints). A cabinet selected: the editor's width, as before. At
   1360 x 900 the plan's card went from about 450 px to 890.
2. **Wall lengths outside, turned along the wall, inside the drawing, backed
   over anything.** On the wall's back beyond the thickness band, rotated to
   read along it (a wall up the page reads upwards; `data-cx`, `data-cy`,
   `data-rot`; the field the page lays over it turned to match); the
   collision step moves one further out on a leader. `plan_svg` draws again
   with every placed label's box in its bounds and `render.PLAN_LABEL_MARGIN`
   (150 mm) round it when one would be past the edge (`_grow`), so the
   exported plan clips none. Over a cabinet, panel, face, wall or gap mark a
   label sits on a white rounded backing (`rect.lenback`, 0.85, no pointer
   events); over nothing it has none. `check_room.py` `plan_labels()` (every
   fixture room, a nook, an open L, one wall, a hexagon, a partition) and
   `ui_check_walls.py --stage labels` (the nook room, Test.json's room, a
   partition; the exported plan's viewBox measured in the page).
3. **Undo and Redo.** See **Undo** under The UI. `ui_check_undo.py` (new).
   **Edit paths that did not reach `pushUndo()`, and how each was fixed:** (a)
   ticking a board into the project (`/api/board-select`) and the board swap
   (`/api/board-swap`) never called `markDirty` at all — so they never lit
   "unsaved changes" either: both do now; (b) Equal / Graduated (`applyPreset`)
   wrote the shares and reached the job only through the drawer solver's
   compute: it marks the job dirty itself now; (c) a drawer face typed
   re-solves the stack on every keystroke without `markDirty`, and the
   solver's write-back would have folded the typed figure into the base:
   while a field typed into has focus the step is held for it; (d) the
   Placements table's wall dropdown redraws the table in its `input`
   handler, so its `change` never reached the document: a dropdown's or tick
   box's `input` commits; (e) the server's answer that lands after a field's
   `change` already made the step (a placement's free x, a room field's
   reply) is folded into that step, not made a second. Not undone, by the
   brief: the board and runner LIBRARY saves that change the job on screen
   (`undoRebase`).

Playwright: `ui_check_undo` (new), `ui_check_walls`, `ui_check_attached`,
`ui_check_drawers` pass; `ui_check_restructure` but for its three
pre-existing `attach` lines (its Room line re-pointed at the Placements
strip); `ui_check_3d` but for f6's "nothing was recomputed for it" (Esc in
a 3D drag), which failed 1 run in 3 here and 1 in 4 on the tree before
Undo (run in a worktree) — the known flake, not this brief.

### Room tab touch-ups after Phase 2 (3 October 2026)

**Room tab touch-ups after Phase 2 (3 October 2026, brief
`Claude outputs/room-layout-touchups-brief-2026-10-03.md`, ruled by Rudolf).**
Layout and the plan's labels only; one commit per item; nothing that cuts,
nests or costs moved: benchmark unchanged (272 / 59 / 30, 92 pot holes,
18 / 9 / 6, R28,363.50), `check_all` 23 of 23, `snapshot.py --compare`:
panels, issues and totals identical, Test.json's plan SVG moved (the length
labels are placed with the others). (1) Select · Draw walls · Wall nook are a
segmented control in the strip right of Plan | Elevation (`#roomstrip`,
`#roomtools`), Plan only. (2) **Placements** is the left column beside the
plan, the plan's height (`fitPlaces`, a ResizeObserver, which also redraws the
plan when its box changes width), its table narrowed, scrolled within; Plinth
under Gaps on its own. (3) Length labels: through `_place_labels` first, out
along their wall's normal on a leader, never dropped; the field and the label
sized to their content (`planLenFit`). `ui_check_walls.py --stage labels`
(a nook room, a five-digit wall, at 50 / 93 / 150 %) and `--stage layout`
re-pointed; screenshots `touchup_*` in `output/_checks/ui_check_walls/`.
`ui_check_walls`, `ui_check_attached`, `ui_check_drawers`, `ui_check_3d` pass;
`ui_check_restructure` but for its three pre-existing `attach` lines.
**Phase 2's two open decisions are ruled: `loop_miss_max` 1000 accepted; a
corner unit keeping its x on a wall drag, flagged by Validation, accepted**
(`docs/ROOM-LAYOUT-SPEC.md`, Ruled — 3 Oct 2026). Seen, not touched: a length
label on a wall running up the page is centred 22 px out, so its text
straddles the wall line (as before).

### Room redo, Phase 2 of 4 — drawing and editing walls on the plan (3 October 2026)

**Room redo, Phase 2 of 4 — drawing and editing walls on the plan (3 October
2026, brief `Claude outputs/room-redo-phase2-brief-2026-10-03.md`, ruled by
Rudolf; Phases 3-4 — openings, free cabinets — NOT built).** Six commits, one
per ruling group (1-2, 10-11, 3-4, 5, 6, 7-9); `check_all` 23 of 23 at each;
benchmark unchanged (272 / 59 / 30, 92 pot holes, 18 / 9 / 6, R28,363.50);
`snapshot.py --compare` against the tree before: every panel, issue and total
identical on every job, only Test.json's plan SVG moved (its `<svg>` carries
the mm mapping, its labels their wall). `ui_check_walls` passes every stage
(old and new); `ui_check_restructure`, `ui_check_attached`, `ui_check_drawers`
pass; `ui_check_3d` fails f3's zoom-to-cursor drift (6.4 px) every run and f4's
"within a second of the keystroke" (1.7-2 s) in one run of two — both the
same on the tree before this work (6e87fcf, run in a worktree): this
machine's SwiftShader, not this brief. Full write-up in `docs/ROOM-LAYOUT-SPEC.md`, **Ruled — 3 Oct
2026**. The short form:

1. **Open / closed has one source, `room.closure`** (`{closed, miss, at,
   level, text}`). A typed figure leaves a loop open by the miss, said
   everywhere as "Loop opens by n mm at D→A — type the other walls or drag a
   corner" — the Room card pill, the table's open corner, the Wall card, the
   toast (now off the COMPUTE, `closureToast`, not the edit's reply), the
   plan's tint, the 3D note, Validation's `room-closure` — and it closes by
   itself within `join_tolerance`. `Standard.loop_miss_max` 1000 (NEW,
   display only) tells a loop that opened from an open run on purpose.
2. **Draw walls is a mode of the plan** (the `#drawsvg` canvas is gone): the
   plan carries its mm mapping (`data-mmx`, `data-mmy`, `data-pad`,
   `data-scale`; `planMap` / `mmToSvg` / `svgToMm` / `mmToScreen`) and, on the
   Room tab, `render.PLAN_MARGIN_MM` 800 to draw into; cabinets ghost while
   drawing; a grid over it (`gridSvg`); an empty room is a 6 x 4 m sheet. The
   plan is asked for at its card's size, so 100% fits (the 100% button re-fits); Gaps full
   width, Plinth | Placements side by side, notes behind "?".
3. **Drags**: a corner's handle (`.cornerhandle`, on hover) → `room.corner_move`;
   a wall's body → `room.wall_move` (neighbours keep their direction, a 90
   stays 90); what stands on a changed wall keeps its x, clamped and reported
   (`room.keep_on_walls`). **Snaps** off `room.room_snaps` (`/api/room-snaps`,
   one call per press): corner, point on a wall (Draw), alignment through
   every other corner, angle (90/180 to the neighbour, plan axes, 45, 15),
   length step; named beside the cursor; Shift frees; Esc restores.
4. **Lengths typed on the plan**: each label a text box (`planLengths`),
   Enter → `/api/wall-set`, Esc, Tab to the next wall in walk order.
5. **Drawing finished**: start on a wall to split it (`room.split_wall`,
   `/api/wall-split`) — a T-wall; a digit opens a length box (Tab: the
   corner's angle; Backspace in an empty box: the last corner off); end on
   any corner.
6. **Wall nook** (`room.wall_nook`, `/api/wall-nook`, a toolbar mode), **Add
   back face** (`room.add_back_face`, the Wall card), **Flip room**
   (`room.flip_room`, `/api/room-flip-all`, asked when Flip face is pressed
   on a wall of a closed room — `in_loop` on each wall in `_room_info`).

**For Rudolf:** (a) `loop_miss_max` 1000 is Claude's figure — a closed room's
loop opened by more than a metre by a typed figure reads as an open run;
(b) a corner unit in a corner is not re-run into the corner when a wall is
dragged (its x is kept, as ruled), so Validation's out-of-corner warning is
what tells you; (c) Test.json's own room is an open L, so the `closure` stage
closes it with walls C and D in the page (never saved).

### Room redo, Phase 1 of 4 — walls become positioned segments (2 October 2026)

**Room redo, Phase 1 of 4 — walls become positioned segments (2 October 2026,
brief `Claude outputs/room-redo-phase1-brief-2026-10-02.md`, ruled by Rudolf;
Phases 2-4 — the draw mode, openings and obstructions, free cabinets — NOT
built).** Three commits, Parts 1 to 3; `check_all` 23 of 23 at each; benchmark
unchanged (272 / 59 / 30, 92 pot holes, 18 / 9 / 6, R28,363.50); `snapshot.py
--compare` against the tree before: the benchmark and every panel, issue and
total identical, Test.json's plan moved by the room-side tint and the wall hit
lines only (its elevations byte for byte). Every Playwright script passes
(`ui_check_walls` rewritten, `ui_check_restructure`'s Room and export stages
re-pointed; `ui_check_3d`, `ui_check_attached`, `ui_check_drawers` unchanged).

1. **The model.** `Wall` is `id, x0, y0, x1, y1` (whole mm), `height` (None =
   the ceiling), `thickness` (None = `Standard.wall_thickness` 110, drawing
   only), `drawn`; `length`, `offset_start`, `offset_end` and `corner_end` are
   gone from the dataclass (`Wall.length` is a property off the points),
   `Room.closed` is derived. The drawn line is the inside face and **the room
   is on the RIGHT of x0 → x1** (`wall_normal`, `(-dy, dx)` — the normal the
   chain always gave). `room.py` derives the rest, one function each:
   `wall_frames` (same shape), `connections` (ends within
   `Standard.join_tolerance` 1 mm), `chains` / `walk_order` / `main_chain` /
   `is_closed`, `corner_angle` (after a wall, to 0.1°; `corner_angle_exact`
   for geometry), `corner_before`, `out_of_square` (mm at `offset_depth` when
   within `Standard.square_within` 10° of 90 / 180 / 270), `corner_points`,
   `closure_error` (a near miss within `closure_block` only — a bigger miss is
   an open run and nothing is said), `crossing_walls` (proper crossings only:
   a T-wall is legal). A wall meeting nothing at either end is **free**: no
   corner, no butt, no shadow, nothing beside it.
2. **Edits move points, server-side, whole mm**: `set_length` (the chain
   after it follows), `set_corner` (the walls after the corner turn; on a loop
   every other wall, so the last corner can be typed too and the loop opens
   where the walk came back), `set_out_of_square`, `add_wall(after= |
   before=)` at 90 off a FREE end (refused where the end meets a wall; nothing
   re-origined), `walls_from_points(rm, …)` ADDS drawn walls (no replacing, no
   re-orienting; a first point within `snap_tolerance` of an existing corner
   joins it), `flip_face` per wall (`flip_side` is gone), `renumber_walls`
   along the walk (placements, gap and plinth decisions, an acceptance's
   `where` follow; letters are otherwise for life, A..Z then AA),
   `delete_wall` (placements unplaced, decisions dropped, never an orphan).
3. **Migration, once** (ruling 8): `store.room_from_dict` runs a room saved as
   a chain through `room._legacy_frames` (the old arithmetic, read by nothing
   else) and writes points; every job and fixture with a room was re-saved in
   the new form in Part 1's commit — all exact, every corner 90. Load → save →
   load is stable; a job with no room does not change by a byte.
4. **Height**: `wall_height(rm, w)`; the elevation draws the wall to it with
   the ceiling dashed above a lower wall, 3D draws each wall to it; new
   `opening-height` (CRITICAL, an opening's head above its wall) and
   `above-wall` (WARNING, a cabinet reaching above a wall lower than the
   ceiling — a tall unit can stand against a half wall). `corner-angle` and
   the corner-disagreement check are gone; `room-closure` is the near miss.
5. **The Room tab**: a toolbar (Select · Draw walls, Esc back to Select), the
   plan, one dock showing the **Room card** (nothing / the room selected), a
   **Wall card** (a wall clicked in the plan or in the table) or the editor;
   Placements, Gaps and Plinth under the plan. The room side is SHOWN (a
   closed room's floor tinted, an open run's or a free wall's face side a
   band fading out, the thickness hatched on the back); a one-wall room
   draws; Draw walls adds. Units on screen: mm and °. See **The UI → Room**
   and the where-it-lives-now table.
6. **API**: `/api/wall-set` (length / angle_after / angle_before /
   square_after / square_before / height / thickness / drawn), `/api/wall-add`,
   `/api/wall-delete` (an `ask` step for the confirm), `/api/wall-flip`,
   `/api/room-renumber` (a dry run for the confirm), `/api/room-draw` (adds),
   `/api/room-new`; `/api/room-extend` and `/api/room-flip` are gone.
   `_room_info` carries per wall the points, length, height, thickness, drawn,
   `free`, the corner before and after (angle, out-of-square, the wall met),
   and `closed`, `walk`, `closure_error`, `crossing`, `corners`.
7. **Checks**: `check_room.py` rewritten (migration, walk, renumber,
   flip_face, height, single_wall, touching, delete, the angled-room pins on
   points); `check_attached`, `check_elevation`, `check_fillers`,
   `check_plinth` and `check_scene` build their rooms with points, `chain_walls`,
   `set_corner` / `set_out_of_square`. No pinned figure moved: every fixture
   room is 90 at every corner, so the migration is exact.

**What the audit found and changed** (every chain-by-index read, Part 1):
`corner_shadow` and `unit_corner` (prev / next wall by connection; `unit_corner`
now names the wall whose corner-after it is), `_beside` (so `return_profiles`
and `return_faces`), `clashes` (each wall's own segment, not the corner
chain), `_plinth_meets` / `plinth_butt_wall` / `plinth_open_corners` (the
previous wall by connection), `gaps`' `_corner_indices` → `_corner_walls` and
`_deviation` / `_front_gap` (the real angle, one formula: `nominal − depth ·
cot(angle)`, the nominal at 180 and beyond), `scene._room_payload` (walls off
their points, `is_closed`), `render._plan_walls` / `_plan_tracks` (own points),
`plan_svg`'s bounds (walls and footprints, one wall or many), `validate._room`
and `api._room_info`. `corner_offset`, `corner_turn`, `corner_exists`,
`flip_side` and `next_wall_id`'s A-Z limit are gone.

**What a free wall or a one-wall room made the engine do**: nothing the brief
did not foresee. A one-wall room gaps to both ends with no taper, runs end at
the wall's ends with no butt and no plinth-corner warning, the elevation sees
nothing beside it, 3D draws the one wall over a one-segment "floor" (the
corner chain is two points; three's floor shape is degenerate and draws
nothing), and a corner unit on it is told it is not standing in a corner. A
flipped wall in a closed room meets nothing afterwards: the room becomes an
open run and the flipped wall a free wall (the walk puts it last).

**For Rudolf:** (a) typing a length or an angle on a closed room opens the
loop by the difference — the toast says so and the Room card reads "open run";
type the matching figure on the opposite wall, or Draw walls, to close it
again (Phase 2's corner drag is the real answer); (b) the `offset_depth`
default and sign stay open, as ruled; (c) the plan's room-side tint moved
Test.json's plan SVG in the snapshot — by design.

### The demo build (30 September 2026)

**The demo build (30 September 2026, brief
`Claude outputs/demo-build-brief-2026-09-29.md`).** See **Demo build** above.
Nothing in `cabinetgen/` changed; `check_all` 23 of 23 with demo mode off;
benchmark unchanged (272 / 59 / 30, 92 pot holes, 18 / 9 / 6, R28,363.50). The
first zip, `demo\Cupboard App Demo 2026-09-30.zip`, 16 MB, expires 29 Nov 2026.
Tested unzipped on the Desktop with every Python folder off the PATH (the only
`python312.dll` loaded was the zip's own): the window, its title and the board
pictures; Test.json and the Oct 2025 job (272 / 59 / 30, 92, 18 / 9 / 6,
R28,363.50 inside the exe); `ui_check_restructure.py` and `ui_check_3d.py`
pointed at the exe (`--port`) pass but for their known lines — the three
`attach` lines, the flaky Esc `sceneStale` line (failed on the normal app too),
and the lines that look for an export or a snapshot in the REPO's `output/`,
which went to the demo's own folder instead. Expired copy and clock roll-back
both refuse in a message box; the left-open case shows the message over the page.

### Walls at any angle, either direction, and Draw walls (29 September 2026)

**Walls at any angle, either direction, and Draw walls (29 September 2026,
brief `Claude outputs/room-walls-any-angle-brief-2026-09-29.md`, ruled by
Rudolf).** The 22 September hold on outside corners is LIFTED for the walls;
corner units still stand only in a nominal 90 inside corner. Nothing in the
cut list moved: benchmark unchanged (272 / 59 / 30, 92 pot holes, 18 / 9 / 6,
R28,363.50); `check_all` 23 of 23; `snapshot.py --compare` against the tree
before: identical on every job; every job file and fixture round-trips byte
for byte. Full write-up in `docs/ROOM-LAYOUT-SPEC.md`, **Ruled — 29 Sept 2026
(walls at any angle, Draw walls)**. The short form:

1. **`Wall.corner_end`**: the nominal interior angle of the corner after the
   wall (90 inside, 270 outside, 135 / 225 a splay, 180 in line, any value
   strictly between 0 and 360), written only when not 90. The offsets stay the
   fine correction. `room.corner_turn` turns the chain by 180 − angle − the
   deviation; at 90 it is `math.pi / 2` itself, and `check_room.py` proves
   every fixture room's frames float-for-float equal to the old turn.
2. **Walls card**: a **Corner** column (`B→C`, quick picks 90 inside · 270
   outside · 135 · 225 · 180 in line · custom; a dash on an open run's last
   wall). A negative length is refused at the input ("to turn the other way,
   set the corner angle to 270"); an angle outside 0-360 likewise.
3. **Draw walls** on Room -> Plan: click the corners on a millimetre canvas,
   15-degree direction snap (Shift free), 10 mm length snap (both in
   `Standard`), click the start to close, double-click / Enter for an open run,
   Esc cancels, Backspace undoes. `/api/room-draw` -> `room.walls_from_points`
   names, measures and angles the walls and puts them clockwise (anticlockwise
   drawn: walked the other way, the first wall drawn still A). Drawing over a
   room asks "Replace walls A–D?". Every drawn wall is `drawn` — a CRITICAL
   (`wall-drawn`) until typed or ticked **measured**. The model puts A along
   +X, so the plan shows a drawn room turned that way.
4. **New criticals**: `room-self-intersect` (walls crossing in plan, named in
   pairs), `wall-drawn`, `corner-angle` (a hand-edited angle out of range),
   `corner-unit-angle` — ruling 4: "Corner unit at a 135° corner: construction
   not ruled.", for a mitre or blind unit whose hand-end corner is not a
   nominal 90; no shadow is cast there.
5. **What learnt about angles**: the plinth butts (16 mm) only at a nominal
   90 inside corner — see the follow-up rulings below; a gap meeting an angled inside corner is measured
   at the front against the real return wall (135: 100 at the wall is 680 at
   the front of a 580 run — a cabinet, not a filler), at an outside corner
   the run just ends; the plan drag picks the nearest wall SEGMENT, not the
   nearest wall line (an L's inner wall line runs through the room); an
   obstruction on an angled wall draws turned; the 3D contact shadow on an
   angled wall turns with the item. Elevations, 3D walls / floor / ceiling /
   tiles / Grid, door swing, tip-up, ceiling and overlaps were already
   geometry and are pinned on angled rooms.
6. **Checks**: `check_room.py` `angles()`; `tools/ui_check_walls.py` (new,
   Playwright: draw a 4-wall room and close it, an L with an outside corner
   drawn anticlockwise, an open run by double-click, 270 in the Walls card
   turning the plan, the input refusals, a cabinet dragged onto a 45-degree
   wall, and the L + splay in 3D) passes every stage. `ui_check_attached`
   and `ui_check_drawers` pass; `ui_check_restructure` but for its three
   pre-existing `attach` lines; `ui_check_3d` passed on rerun — once, run in
   parallel with other scripts, f6's "and nothing was recomputed for it"
   (Esc during a 3D drag) read `sceneStale` true, and passed four runs alone.

**Follow-up rulings, Rudolf, 29 September 2026 (the same evening):**

- **Gap front width at an angled inside corner: the real angle, as built.**
- **Plinth at an inside corner that is not 90: no butt deduction.** Each
  plinth ends where its run ends, and a WARNING names the corner
  (`plinth-corner`, `room.plinth_open_corners`): "Plinth at the A→B 135°
  corner: the boards don't meet, cut a closing piece on site" — raised where
  two fitted plinths on the floor meet there. The 16 mm butt stays for 90
  inside corners only (`plinth_butt_wall`). Pinned in `check_plinth.py` and
  `check_room.py` (90 butts; 135 and 60 warn; 180 and 270 neither).
- **Drawn-room lettering and winding: accepted as built.**
- **Which side is the room on an OPEN run** (asked, answered): the side the
  run turns towards on balance — the inside of an L or a U, whichever way it
  was clicked (`walls_from_points`). An L clicked left-to-right and
  right-to-left gives the same walls, and its cabinets stand inside the L on
  the room side of both walls — proved in `check_room.py` and in the running
  app (`ui_check_walls.py --stage side`). A run that does not turn on balance
  (one straight wall, a step whose turns cancel) cannot say, and is taken as
  drawn: the room on the right hand of the direction drawn. And an L may be
  meant round the OUTSIDE of a nib. So the Walls card has **Flip side** on an
  open run: `room.flip_side` (`/api/room-flip`) walks the same walls the other
  way — each keeps its letter, each corner becomes 360 less itself, offsets
  swap ends and change sign, openings, obstructions, cabinets and placed
  panels keep their places along each wall (x from the other end), a corner
  unit's hand swaps, a gap decision swaps its sides, a plinth decision follows
  its run. Nothing is cut differently; flipping twice gives the job file back
  exactly. Refused on a closed room, which has no other side.

**For Rudolf:** Liam_Room is not saved or touched — set its lengths positive
and its corners in the new Corner column. A drawn room is re-oriented with
wall A along +X once made.

### The 3D view drawn realistically — Round 2 (29 September 2026)

**The 3D view drawn realistically — Round 2 (29 September 2026, Rudolf's notes
`Claude outputs/3d-realism-round2-notes-2026-09-29.md`, reference photo
`Claude outputs/3d-realism-screenshots/reference-kitchen-brookhill-grey.jpg`).**
`app/view3d.js`, vendored three.js addons and the checks only: nothing under
`cabinetgen/` or in `app/api.py` changed, so `/api/scene` is byte-identical.
Built 1 to 6, one commit each. Benchmark unchanged (272 / 59 / 30, 92 pot
holes, 18 / 9 / 6, R28,363.50); `check_all` 23 of 23; `ui_check_3d`,
`ui_check_attached`, `ui_check_drawers` pass, `ui_check_restructure` but for
its three pre-existing `attach` lines. Screenshots `r2_after1_*`, `r2_after3_*`,
`r2_after5_*` beside Round 1's in `Claude outputs/3d-realism-screenshots/`.
Figures measured in headless Chromium (SwiftShader) unless they say otherwise.

1. **BROOKHILL: colour and tile.** The picture was already tagged sRGB. The
   orange came from the material's base colour — the board's fallback swatch
   `#c6a65d` — MULTIPLYING the map: a board drawn in its picture takes white
   now (`showPicture`), the swatch only while no picture has landed.
   `partInfo().colour` is still the board's own colour; `tint` is what
   multiplies the picture. And the tile is the elevation's: its `<pattern>`
   holds the picture `xMidYMid slice` in a square, so the 3D cuts the
   picture's middle square out once (`squareTile`) and tiles that at
   `tile_mm`, where before the whole 1135 x 953 picture was stretched into
   the square. **Measured face on to wall B, cabinet 1's left leaf** (the
   notes name "cabinet 10's 600 door"; in Test.json 10 is an end panel, and
   the 600 front beside it is cabinet 1's pair): picture mean **175.3 / 161.8
   / 146.2**; 3D before 147.2 / 120.4 / 75.1, after item 1 174.2 / 160.9 /
   145.5, after item 4's light **180.8 / 166.8 / 150.5** (+5.5 / +5.0 / +4.3);
   elevation 174.7 / 161.3 / 145.7. Tile period: 3D **160 mm** (158-162
   measured); the elevation's is 40 px at the wall's drawing scale, which on
   BOTH of Test.json's walls is 0.2077 px / mm — **192.6 mm**, not 160.
   `render.PICTURE_TILE_MM` says 160 "at its usual scale"; the two agree only
   there. **For Rudolf:** the picture is about seven planks wide, so a 160 mm
   tile draws planks of some 25 mm in both drawings; the wide planks of the
   photo need the picture laid at its real width (about 1.3 m), which is a
   figure on the Boards record and a `cabinetgen` change, outside this brief.
2. **Door and drawer gaps read.** Every front (door, drawer face, blind panel:
   `isFront`) draws its whole perimeter at `PAPER.edgeFront`, full strength,
   in Shaded as well as Shaded + edges, as FAT lines (`frontLineMaterial`,
   `LOOK.front` 1.25 px): a GL line on a front's face lost the depth test to
   the face, which its polygon offset pulls forward. Carcass and interior
   parts keep the 20 degree threshold at 0.55. At the 3D tab's Home the seams
   of cabinets 1, 11, 4 and 7 stand 26 to 49 units off the nearer face.
3. **The Cabinets-tab view draws no selection outline**: only the part PICKED
   (`V.picked`, a click on it) takes the accent outline and the part under
   the pointer the lighter one. An attached panel selected beside its cabinet
   is still outlined as an item. The 3D tab is unchanged.
4. **Light and depth.** The key stands above and in front of the fronts
   (`LOOK.keyFrom`: 55 degrees up; along the inward normals of the walls
   carrying something, each counted once; with no room +y turned 25 degrees)
   and is stated as the IRRADIANCE it puts on a front (`LOOK.key` 1.4; the
   light's intensity follows in `fitKey`), over an environment of 0.7. GREY
   front **80 / 79 / 78 on wall A and on wall B** (swatch 80 / 79 / 78),
   81 / 80 / 79 in the Cabinets 3D; a white carcass reads **top 247, side
   208**. A room with runs on three walls lights the middle run's fronts and
   leaves the two facing each other on the environment alone. **Shadows**:
   three r186 has REMOVED `PCFSoftShadowMap` ("Using PCFShadowMap instead"),
   so this is `PCFShadowMap` with radius 3, 2048 square, fitted to the scene
   bounds on every rebuild, `autoUpdate` off and drawn when `shadowsDirty`
   says the scene or the light changed; every board casts and receives, a
   ghost and an x-ray cast nothing; a contact shadow under every item
   standing within 200 mm of the floor (`buildContacts`). **AO**: three's
   `GTAOPass`, vendored with what it imports, behind the **AO** button, off
   under X-ray, **driven directly and not through `EffectComposer`**: a
   composer tone-maps the whole frame in its output pass — paper lines and
   background with it — and loses the canvas's antialiasing, so the
   occlusion is multiplied over the frame already on screen. Its figures are
   in mm (`LOOK.ao`), it is denoised three times (once leaves grain on pale
   boards), and the paper lines are on their own layer and drawn after it.
   **Frame time, Test.json's room at Home, this laptop's Intel graphics
   (ANGLE D3D11): 11-13 ms with AO against 6-8 ms without at 882 x 768, 15-17
   ms against 6-7 ms at 1323 x 1152** — kept, on by default. In software
   (SwiftShader) 1.1 s against 0.2 s, so on a software renderer it starts
   off (`softwareRendered`). Snapshot and the checks' pixel reads go through
   the one `draw()`.
5. **The room.** Shaded modes: pale 600 mm tiles with a faint joint (reads
   225 / 228 / 222; `PAPER.floorTile` is stated darker than it reads, a floor
   is lit from above), plaster walls (208 / 200 / 186), an off-white ceiling;
   X-ray keeps the drawing's paper room. The drawing grid is on with edges
   and in X-ray, off in Shaded, and the **Grid** button flips the one in
   force (`V.gridOn`).
6. `check_launch.py` prints "skipped: Windows only" and exits 0 off Windows;
   `ui_check_3d.py --stage look` holds BROOKHILL's mean-colour rule, the tile
   period, the seams, the form, the shadow map's updates, AO and the room.

**`ui_check_3d.py` and `ui_shots_3d.py` read `tools/fixtures/Test_3d.json`**
(Test.json at 14a5ea7), not the live file: on 29 September Test.json was
edited and saved in the app while the checks ran (cabinet 4's drawer faces,
panel 8's depth) and three lines failed. The fifth time for this lesson.
`ui_check_restructure.py` reads the editor's 1.2 s flash before its
screenshot. Seen once in three full runs and not touched:
`ui_check_3d`'s "cube … animated" line, which asks whether a 300 ms fly is
still running after the click returns.

**For Rudolf:** (a) the plank width, above; (b) the elevation's tile is 193 mm
on Test.json's walls against the 160 the 3D is told; (c) white on a front is
still 241, Round 1's trade-off; (d) AO, the key and the plaster want looking
at on the laptop; (e) `jobs/Test.json` and a new `jobs/Liam_Room.json` were
saved in the app during this work and are left uncommitted.

### The 3D view drawn realistically — Round 1 of two (29 September 2026)

**The 3D view drawn realistically — Round 1 of two (29 September 2026, brief
`Claude outputs/3d-realism-brief-2026-09-29.md`, agreed with Rudolf; Round 2
built since, above).** `app/view3d.js` and the vendored libraries only: nothing under
`cabinetgen/` changed, `/api/scene` is byte-identical. Benchmark unchanged
(272 / 59 / 30, 92 pot holes, 18 / 9 / 6, R28,363.50); `check_all` 22 of 23 —
`check_launch.py` fails on the cloud machine at HEAD too (its child stubs
`ctypes.windll`, which only Windows has; run it on the laptop). Before-and-after
screenshots of the brief's four views are in
`Claude outputs/3d-realism-screenshots/` (`tools/ui_shots_3d.py` takes them,
the same four every time). Every figure below is measured in headless Chromium
(SwiftShader) off the drawing buffer through the view's new `pixel()`.

1. **A board's colour on screen is its colour — physically lit.** No
   hemisphere light; the diffuse light and the reflections come from an
   image-based environment through `PMREMGenerator`, one directional key
   light (0.4, from (−0.5, −0.8, 1) as before) gives the form, and the
   renderer tone-maps with `NeutralToneMapping` (Khronos PBR Neutral — no
   tint) at exposure 1.0, `outputColorSpace` sRGB, every picture tagged
   sRGB. **The environment is NOT three's `RoomEnvironment`**, which the
   brief named: vendored and measured first, it is a studio set with one
   bright side — env only, exposure 1, the four horizontal directions gave
   irradiance 3.9 : 1.0 : 0.9 : 1.3, so a front's colour would have depended
   on which wall its cabinet stood on. It is a neutral grey box instead
   (`makeEnvironment`: ceiling 1.2, the four walls 1.0, floor 0.5, radiances
   in `LOOK.sky`, blurred 0.1), turned +90° about X so its ceiling is our +Z
   (measured, not reasoned: three's `environmentRotation` Euler is applied
   in the map's frame). The measured result, a front face face-on, unselected:
   GREY `#504f4e` reads **81 / 80 / 79 on wall A and 80 / 79 / 78 on wall B**
   (+1 and 0), BROOKHILL's fallback `#c6a65d` (pictures stripped) **198 / 166
   / 94** (0 / 0 / +1), WHITEMEL `#ffffff` **241** on a front and 245 on a
   top (−14 / −10). **White is the one outside the brief's 8**, and it is the
   tone map, not the light: Neutral's shoulder starts at linear 0.76 (sRGB
   ~226) and compresses everything above it, so white reaches 247 only at
   about 1.4× the exposure — which puts BROOKHILL +37, GREY +12 and every
   board picture some 20 % light. Exposure 1.0 keeps the mid-tones, the darks
   and the pictures true and holds white at 241; ruled here, **for Rudolf to
   look at**. In the Cabinets 3D at Home (perspective, front-left, elevated)
   the same GREY face reads 85 (+5): the sheen, seen at an angle. Pinned in
   `ui_check_3d.py --stage look`.
2. **Melamine**: `MeshPhysicalMaterial`, roughness 0.45, metalness 0,
   clearcoat 0.12, clearcoat roughness 0.5 (`LOOK.board`; the edging bands
   the same, `LOOK.tape`, in their own board's colour; runners
   `MeshStandardMaterial` 0.45 / 0.3, grey, unchanged). **One material per
   board, shared** by every part cut from it, in three variants — solid,
   ghost, x-ray — so a part changes its look by being handed another shared
   material (`boardMaterial` / `tapeMaterial` / `runnerMaterial`, cached in
   `V.materials`; `applyDisplay` picks the variant; `disposeObject` skips
   what is shared). A board whose look changes on the Boards tab is brought
   up to date IN PLACE (`refreshLooks`: the part hashes do not carry the
   look, so nothing used to rebuild — a colour edit did not reach 3D until
   the cabinet itself changed). `LOOK` is the one block of light, surface
   and line figures, beside `PAPER`; `check_colour.py` holds it to no colour
   and holds the file to no emissive but the obstruction's.
3. **A grained board draws its picture** (it did already; made right): the
   picture is fetched **once per board** (`loadPicture`) and each rotation is
   a clone sharing the image (`pictureFor`), sRGB, repeat-wrapped, tiled at
   `PICTURE_TILE_MM`, turned onto the part's grain vector by 0 or 90° as
   before, anisotropy at the renderer's maximum (was 4). A material has no
   map until the picture lands (`applyPictures` fills it), so a part keeps
   its colour while loading and on a failed load — before, three drew an
   unloaded map black.
4. **Selection is an outline, not a tint.** The emissive glow (accent at
   0.14, which turned GREY navy) is gone: a selected item's edges are drawn
   again as fat lines — three's `LineSegments2` / `LineSegmentsGeometry` /
   `LineMaterial`, vendored from r186's `examples/jsm/lines/` under
   `app/vendor/three/addons/lines/` with the licence, imported as
   `three/addons/…` through the importmap — 2 px in the accent; a hovered
   item 1.4 px in `PAPER.hover` at 0.85. Built lazily from the part's own
   `EdgesGeometry` the first time it is selected, a child of the part so it
   opens and slides with it. **Found on the way:** a fat line's quads are
   built in clip space by its shader, so their winding is not the mirrored
   root's, and under `V.root` (scale 1, −1, 1) a one-sided `LineMaterial`
   is culled entirely — `side: DoubleSide`. The board colour under the
   outline does not move (pinned: the face pixel is identical selected and
   not). The obstruction's warning emissive and the clash red stay.
5. **Edges quieter**: the thin edges in Shaded + edges at opacity 0.55
   (`LOOK.edge.opacity`), only where faces meet at over 20° (the threshold
   `EdgesGeometry` already had — coplanar seams were never drawn, so that
   half of the brief was already so); the three weights in `PAPER` keep
   their roles. X-ray unchanged (edges at 1). Every paper line — edges,
   walls, the grid, overlays, the pivot dot, the dimension lines — is
   `toneMapped: false`, so a `PAPER` colour lands as written.
6. **The room is matte and neutral**: floor, walls and ceiling at roughness
   0.9; the grid 0.22 / 0.4 (was 0.35 / 0.55); the background a slight
   top-to-bottom gradient, `PAPER.bgTop` `#f4f5f2` over `PAPER.bgBottom`
   `#e6e8e3`, a 1 × 64 canvas as `scene.background` tagged sRGB (three then
   neither tone-maps nor converts it), so a snapshot carries it.

Also: `ui_check_3d.py --stage f1` names the three line files among what is
fetched off `/vendor/`, and `/vendor/three/addons/LICENSE` is served. The
view's interface gains `pixel(x, y)` (the drawn colour at a canvas point),
`look()` (the figures in force) and `tune({…})` (try a figure in the running
view — browser state, the tuning harness only). `check_scene.py` unchanged.
**Not done, by the brief:** Round 2 (shadows, AO, the snapshot with them).
**For Rudolf:** (a) white at 241 versus the brief's 247 — the exposure choice
above; (b) the sheen and the key at 0.4 — to be felt on the laptop.

### Drawers section fixes after Rudolf's review (29 September 2026, evening)

**Drawers section fixes after Rudolf's review (29 September 2026, evening,
brief `Claude outputs/drawers-fixes-brief-2026-09-29b.md`).** Parts 1-5 one
commit each, `check_all` 23 of 23 at every one; Part 6 a report, no change.
Benchmark unchanged (272 / 59 / 30, 92 pot holes, 18 / 9 / 6, R28,363.50).
`snapshot.py --compare` against the tree before: the October job identical;
Test.json gains ONE critical (Part 2, below) and nothing else moves.

1. **The editor jumped on Equal, Graduated and size changes — fixed at the
   cause.** The dock's issue list was emitted only when the cabinet had
   issues; when the first appeared, `#editor`'s children shifted by one, the
   paint paired the old `.body` with the new issue list (two plain divs),
   rebuilt every section with empty slots and the dock's scroll was clamped
   away (measured: Equal from y 461 to 1041). Now the container is always
   there (hidden when empty), `alike()` never pairs two divs of different
   kinds (first class), `renderEditor` keeps the scroll and holds the
   focused control where it was on screen (`keepPlace`; the browser's own
   `overflow-anchor` off on the dock), and the stack readout `#dtot` — filled
   after the solve, emptied by every paint, growing back 18 px later — is a
   slot the paint leaves alone. `ui_check_drawers.py --stage scroll`.
2. **A box never sits flush in its face** (NEW RULE, Rudolf, 29 Sept):
   `Standard.drawer_box_clear` 2. See **FACES LEAD, BOXES FOLLOW**, rules 1
   and 5. Test.json cabinet 7 drawer 3 (face 171, box 150; 148 fits) now
   raises `drawer-box-face` — the one snapshot change. Cabinet 4 does not
   (its boxes 90 / 150 / 141 / 136 fit).
3. **Auto put the top box into the Top Front — fixed.** The limit a box top
   may reach (`Cabinet.box_top_limit_of`) is the lower of the face top and a
   Top Front / Top Rear band's underside (`Cabinet.support_band_underside`,
   H − t, held equal to `support_layout`'s band on every fixture), each less
   the clear. `max_box`, `≤` and Auto read it; `support-drawer-foul` fires
   within 2 of the band too. Test_drawers cabinet 4 after Equal, all Auto:
   top box stops at 762 under the band at 764, nothing raised.
4. **The offset's floor.** What it was: the checks DID read the offset on the
   way down (negative → `drawer-box-face`, the bottom drawer under 21 →
   `drawer-bottom-offset`); the FIELD took any number, an Auto box's cell had
   no red state and its `≤` grew as it slid down, 0-20 on an upper drawer
   was legal under the old rule, and the critical landed in the dock's issue
   list, which Part 1's jump scrolled away. Now `drawer_layout` gives each
   outer drawer `offset_min` (21 bottom, 2 upper) and `offset_max` (the most
   at which the typed box — or for Auto the runner's height — still fits),
   `/api/compute` passes them, and the Offset field carries min / max, is
   written on commit (`change`) clamped to them, blank or not a number = the
   default. A stored value outside the range loads as it is, red, with the
   critical, and cuts as it stands until changed. An Auto box that does not
   fit shows its cell red (`drawer_layout`'s `fits`).
5. **Box board and Face board** each have their own label over their control.
6. **Report only — why cabinet 4 reads navy / near black in the Cabinets 3D
   and mid grey in the elevation.** Measured in the running app (Test.json
   cabinet 4, the Cabinets tab's Home view, which is front-left; pixels read
   off a screenshot): GREY is `#504f4e` off `render.board_look` (a PLAIN
   board, so its picture `Storm Grey.jpg` is not used — `Fills.textured`'s
   rule), and `view3d.js` gives the material exactly that colour. The GREY
   drawer faces are DRAWN `#364362`; with the selection tint off, `#353433`.
   The WHITEMEL left side (`#ffffff`) is drawn `#9ea2ae`, untinted
   `#9d9d9c`; even a white bottom facing up tops out at `#f5f6f7`. Why:
   (a) **the lighting is physical and dim.** three.js r186 has no legacy
   lights: Lambert diffuse is albedo / π, and the rig (`makeLights`) is a
   hemisphere 1.15 (sky white, ground `#8f8f86`) plus one directional 1.0
   from (−0.5, −0.8, 1) in the render frame. A front face gets irradiance
   ≈ 0.58 (key) + 0.73 (hemisphere) = 1.31, × 1/π = 0.42 of its albedo in
   LINEAR light — `#504f4e` (linear 0.080) comes out 0.033, sRGB `#333`; a
   side the key barely reaches gets 0.35 of white, `#9e9e9e`. Every board is
   drawn at roughly 40 % of its swatch in linear light, ~65 % in sRGB.
   (b) **the selection tint** (`applySelection` → `tintMesh`): the selected
   cabinet gets `PAPER.accent` `#1f6fd0` as EMISSIVE at 0.14 — linear
   (0.002, 0.022, 0.088) ADDED to every face. On a dark board that is more
   blue than the board reflects (0.088 against 0.033), so GREY turns navy
   (`#353433` → `#364362`, which the arithmetic reproduces to the unit); on
   white it only cools it. In the Cabinets tab the cabinet shown IS the
   selection, so it is always tinted, and its edges are drawn in the accent
   too. (c) **the elevation is a flat SVG fill** of `#504f4e`, no light and
   no tint. For the realism brief: raise the light (or scale by π), add a
   fill light, consider tone mapping, and make the selection an outline
   rather than an emissive that recolours dark boards.

Found, not touched: `hardware.json`'s Gelmar record carries
`inner_height` 37 and `inner_thickness` 6 in the working tree, saved after
the redo's last commit (the Runners form's estimate) — left uncommitted, as
workshop data; commit it when the figures are confirmed off drawing 04227.
`ui_check_restructure.py --stage attach` still fails its three
pre-existing lines.

### The Drawers section redone (29 September 2026)

**The Drawers section redone (29 September 2026, brief
`Claude outputs/drawers-section-redo-brief-2026-09-29.md`, agreed with
Rudolf).** Built Parts 1 to 8 in order, one commit each, `check_all` 23 of 23
at every one. Benchmark unchanged (272 / 59 / 30, 92 pot holes, 18 / 9 / 6,
R28,363.50). `snapshot.py --compare` against the tree before this work:
**identical on every job** — Test.json's re-point (Part 6) moved no line.
`ui_check_drawers.py` (every stage), `ui_check_3d.py` and `ui_check_attached.py`
pass; `ui_check_restructure.py` passes except three lines — see below. What it is:

1. **The model.** `Drawer.box_edge_kind` (R1: PVC / 1mm / 2mm off what the
   board offers, None = PVC — **replaces the same day's "always PVC"**, which
   was Claude's proposal for that build only). `Drawer.base` Optional (None =
   the cabinet's). `Drawer.box_height` None = **Auto** (R2). The section's own
   defaults on the cabinet — `drawer_carcass_board` / `drawer_face_board`
   (offered again), and new `drawer_box_edge_board`, `drawer_box_edge_kind`,
   `drawer_base` — each written only when set (`store.LATE_CABINET_FIELDS`;
   per drawer `store.DRAWER_SET_ONLY`), `drawer_box_edge_board` a board slot
   (and in `boards.CABINET_BOARD_FIELDS`). Resolution per drawer: its own
   value -> the section's -> the fallback (box: carcass; face: exterior; box
   edging: exterior + PVC; bottom: board), each through ONE resolver on
   `Cabinet`: `box_board_of`, `face_board_of`, `box_edge_board_of`,
   `box_edge_kind_of`, `base_of`, `box_height_of`. Engine, room, validator,
   3D bands and `needs_back_board` read them. `Runner.inner_height` /
   `inner_thickness` (R3); SEED and LEGACY carry **estimates** (height - 8 =
   37, 6) until Rudolf reads Gelmar drawing 04227 and edits the record; a
   record not stating them reads the estimate (`inner_h` / `inner_t`) and the
   Runners tab says **estimated: confirm** (`Runner.estimated`). **R4:**
   `api.runner_save` refuses a record missing — or not sending — any of name,
   a length, height, side clearance, rail thickness, lift, setback, inner
   height, inner thickness (each > 0), naming every one (`missing`); the
   Runners form marks them required and lights those refused. A record's
   unstated inner fields are left out of the file (`hardware.to_record`), so
   `hardware.json` does not grow nulls.
2. **The section** — see **The UI → Drawers**. Setup (type, runner and ONE
   status line, bottom, box board · face board, box edging, face edging),
   the stack (five columns), a `differs…` sub-row per drawer. The three
   paragraphs of prose are gone; the brief's help lines are verbatim.
   **Found on the way, fixed:** the editor's repaint skipped the FOCUSED
   element whatever it was, so a button just clicked (differs…, a lock, Auto)
   kept its old label; only value controls (input, select, textarea) are
   skipped now (`morphNode`). Structure's "backing board" need reads the
   engine's `needs_back_board` instead of the rows.
3. **The runner in 3D is two members a side** (R3): `runner_outer` (rail
   thickness x height x length, on the carcass, does not slide) and
   `runner_inner` (inner thickness x inner height, against the box side,
   centred in the channel, from `setback` behind the box front to the
   channel's back, slides with the box by the travel); both off the record,
   both hardware, both under **Runners**, the inner a lighter grey
   (`PAPER.runnerInner`). Roles use underscores like every other role (the
   brief wrote `runner-outer`).
4. **Auto** is cut at `drawer_layout`'s `max_box` (face less offset) and
   follows the face; `drawer-box-face` cannot fire on it; `drawer-runner-height`
   still can and, for Auto, says the FACE is too short and how tall it must
   be. The divider drag holds an Auto face to the runner's height over its
   offset and writes faces only; making an Auto drawer inner writes down the
   figure it came to. A new drawer row starts Auto.
5. **Wording**: went in with Part 2 (and Part 7's Plan shape line).
6. **Test.json onto Gelmar**: cabinets 4 and 7 through the Use-for-all path
   (`api.runner_swap`, apply). **No drawer line moved** — both are 570 deep,
   a 500 runner on either record, 13.5 a side on both; only the two `runner`
   keys were written (setback 3 -> 2 moves the 3D only). Fixtures untouched;
   the UI stages that needed the legacy runner read `Test_drawers.json`.
7. **Outline is Plan shape**, shown only on a `template == "none"` cabinet or
   one already carrying a footprint, the engine's readout kept.
8. **Zoom speed**: a mouse notch 1.25x in 3D (`WHEEL_ZOOM` 0.0022, was
   0.0011) and 1.35x on the plan / elevation (`ZOOM_WHEEL` 0.003, was
   0.0015); a trackpad pinch has its own `PINCH_ZOOM` 0.01 in both — Chromium
   sizes pinch steps so its page zoom is exp(-deltaY / 100), so 0.01 follows
   the fingers one for one. A pinch step is told from a notch by size (under
   50 px, pixel mode). **To be felt on the laptop.**

A section default changed carries the drawers holding the OLD section value
with it (they were not saying they differ; `drawerSectionSet`) — otherwise the
typed `base: "board"` every saved drawer carries would make the Bottom control
do nothing on every existing cabinet. What a drawer chose differently stays.

**Seen and not touched:** `ui_check_restructure.py --stage attach` fails three
lines ("dragging the across arrow wrote at_x…: -16, wanted 450") — the same
on the tree BEFORE this work (203b675, checked in a worktree on port 8767), so
not from this brief. And `ui_check_drawers.py` used to die on this laptop's
cp1252 console printing `≤`; it writes UTF-8 now.

**Report back — open, for Rudolf.** (a) The Gelmar inner member is an
estimate (37 x 6): read drawing 04227 and edit the record (the Runners tab
says "estimated: confirm" until then). (b) The pinch factor wants trying on
the laptop's trackpad. (c) Nothing on Test.json moved with the runner.

### One window, maximised, and a complete check (29 September 2026)

**One window, maximised, and a complete check (29 September 2026, brief
`Claude outputs/launch-and-checks-brief-2026-09-29.md`, agreed with Rudolf).**
Nothing in `cabinetgen/` changed. Benchmark unchanged (272 / 59 / 30, 92 pot
holes, 18 / 9 / 6, R28,363.50); `check_all.py` 23 of 23.

1. **`tools/check_all.py`** replaces the hand-kept lists. `Check It Still
   Works.bat` had stopped running `check_room`, `check_fillers`,
   `check_plinth`, `check_fronts` and `check_export`, and this file's list had
   dropped `check_boards`. **Every `check_*.py` already exits non-zero on a
   failed check** — proved by running each with its first and then its last
   `check()` forced to fail (`check_examples` read by eye: `return 1 if bad`);
   none needed fixing.
2. **No console: the desktop shortcut runs `pythonw run_app.py`.** Under pythonw
   `sys.stdout` / `sys.stderr` are None; `main()` holds output in memory until
   the port is ours, then writes **`output/app.log`**, overwritten each start,
   line-buffered. (`api.Handler.log_message` was already silenced, so requests
   log nothing; what the redirect catches is a traceback from a thread.) Under
   `python.exe` nothing changes.
3. **A failure to start is seen**: the traceback goes to the log and, with no
   console, a message box says it did not start and where the log is. **A port
   already taken is "The Cupboard App is already running, or port 8765 is in
   use"** — and a refused second launch APPENDS to the log, so the running
   app's log is not wiped. No second port is tried.
4. **Found on the way, fixed: a second launch used to start a second server on
   8765.** `HTTPServer` sets SO_REUSEADDR, which on Windows lets two sockets
   bind one port, so the "already running" case could never have been reached.
   `run_app.Server` binds with `allow_reuse_address = False` and
   SO_EXCLUSIVEADDRUSE; it is refused against a plain socket, an old-style
   server and itself (pinned).
5. **Maximised**: `webview.create_window(..., width=1360, height=900,
   maximized=True)` (`run_app.WINDOW`) — maximised, not full screen. pywebview
   6.2.1's WinForms backend sets `FormWindowState.Maximized` from it; checked on
   this laptop through Explorer (IsZoomed, the rect the work area). Started from
   a tool's own background process the window can come up minimised instead —
   the parent's show-state, not the app.
6. **`Make Desktop Shortcut.bat`**, once per laptop: `Cupboard App.lnk` on the
   desktop, target the `pythonw.exe` beside the `python` that `where python`
   finds first (so the same interpreter and pywebview as the console launch),
   argument the full path of `run_app.py`, start in the repo, icon
   `app/cupboard.ico` (drawn in Python, 16-256 px). Through PowerShell's
   `WScript.Shell`; no new package. Pin it to the taskbar by hand.
7. **`Start Cupboard App.bat`** is the console launch for when something breaks;
   it gains the maximised window and one line saying normal use is the shortcut.
   `--no-window` and the browser fallback are unchanged.
8. **`tools/check_launch.py`** pins 2-5 (a child with the streams None; the port
   held three ways; a stand-in `webview` module reading the window call). It
   never writes the real `output/app.log`.

**Tested by hand, 29 September 2026, on this laptop:** the shortcut gives one
`pythonw` process, one window, maximised, no console; a second launch while it
is open shows the "already running" box, and dismissing it leaves the first app
serving; `Start Cupboard App.bat` shows its console and the app, maximised.
Rudolf to run `Make Desktop Shortcut.bat` once on the other laptop.

### Drawer box edging chosen per drawer; above the ceiling acceptable (29 September 2026)

**Drawer box edging chosen per drawer; above the ceiling acceptable (29
September 2026, brief `Claude outputs/drawer-edging-ceiling-accept-brief-2026-09-29.md`,
agreed with Rudolf).** Benchmark unchanged (272 / 59 / 30, 92 pot holes,
18 / 9 / 6, R28,363.50); every `check_*.py` green; all four Playwright
scripts pass. What it is:

1. **`Drawer.box_edge_board`** — the board a drawer box's sides (18) and
   fronts (19) are edged in the colour of, ~~always PVC~~ — **PVC / 1mm / 2mm
   since the Drawers redo (R1, the same day), `Drawer.box_edge_kind`, PVC by
   default** — the name off the board through `tape_for`. **Default (None): the cabinet's EXTERIOR board**, not
   the box board (ruled, for every existing drawer, October included).
   `Cabinet.box_edge_board_of(d)` is the one answer; `drawer_box_tape_of`
   and the cabinet-level `drawer_box_tape` read it. Written to the job file
   only when set. In `_board_slots` as "drawer N box edging board" and in
   `boards.DRAWER_BOARD_FIELDS`, so swap, un-select, rename and the library
   scan find it. The engine emits the sides and fronts once per edging board
   inside a box group (`118a` / `118b`, lettered at birth); the base (17) is
   not edged and stays one line. An edging board offering no PVC is the
   ordinary `EDGING` critical (`edging-offered`), naming the drawers ("drawers
   1, 2 box sides and fronts (Box edging)"). **Supports are not touched.**
   In 3D each box's sides, front and back carry a band on their top edge in
   that board (`room._drawer_tapes`, off `drawer_layout`'s `box_edge_board`).
2. **The editor: a Box edging row UNDER each drawer row**, not a tenth column
   — the table already filled the 560 px column (the two material columns are
   69 px, measured), so a column would have squeezed them (hard rule 9). The
   dropdown lists the project's boards offering PVC by their Edging Name, blank
   = "(the exterior's name)", with the engine's name beside it
   (`edging.drawer_box.rows` on `/api/compute`). Inner drawers the same.
   **Ruled by Rudolf, 29 September 2026.**
3. **What moved.** October: 118, 119, 418, 419, 2718, 2719, 3018, 3019
   `PVC WHITE` -> `PVC BROOKHILL` (PVC BROOKHILL 167.082 -> 199.152 m, PVC
   WHITE 33.484 -> 1.414 m — the white-edged supports of 27-29 only); the
   total does not move (edging priced by kind; the per-name metre round-up
   comes to 202 m either way). `check_export.py`'s edging-names-inside-KNOWN
   list drops 118, 119, 2719, 3019, 418, 419 and keeps 2704c / 2804c / 2904c
   (supports). Test.json: 418a-d / 419a-d -> `PVC Grey`, 718, 719,
   1518a-c, 1519a-c -> `PVC BROOKHILL`; its total **R11,257.50 -> R11,250.75**
   (the same PVC metres, one metre less of round-up across the names).
   Test_Build: 418 / 419 -> `PVC BROOKHILL`, total unchanged. No issue moved
   on any job; October's elevation legend line ("drawer boxes") moved.
4. **`above-ceiling` is acceptable** (Rudolf, 29 September 2026, changing the
   22 September ruling). `validate.ACCEPTABLE["above-ceiling"]`, fingerprinted
   over `room.ceiling_inputs` — underside (`carcass_z`), height (`geometry`)
   and the ceiling — which `above_ceiling` itself compares, so it lapses when
   any of them moves. `ceiling-measured`, `panel-fits-board` and every other
   critical still block; `/api/accept` refuses them. The "Assembled in place"
   preset is offered on tip-up only. Pinned in `check_accept.py`
   (`above_ceiling_accepted`: accepted, exported into `<job>_accepted.txt`,
   lapsing on the ceiling and on the height; `ceiling-measured` refused).
5. Pinned in `check_runners.py` `box_edging()` (default exterior, a choice
   wins, no PVC is `EDGING`, the file round trip, the slot, the scan, the swap,
   the 3D band, October's boxes) and `ui_check_drawers.py --stage boxedge`.

**Ruled by Rudolf, 29 September 2026 — all three accepted:** (a) the Box
edging dropdown stays on its own row under each drawer; (b) Test.json's total
moving R6.75 (R11,250.75) through the per-name metre round-up is right; (c) an
exterior board with no PVC raising two EDGING criticals on a drawer cabinet
(carcass fronts, and the drawer boxes) is right — both are real and name
different parts.

### The Plazaboard CSV: right columns, right numbers, right edging names (28 September 2026)

**The Plazaboard CSV: right columns, right numbers, right edging names (28
September 2026, brief `Claude outputs/plaza-csv-columns-brief-2026-09-28.md`,
agreed with Rudolf; reference: Plazaboard's own files for the October job in
`Sample Plaza cutlist and quote/`).** Benchmark unchanged (272 / 59 / 30, 92 pot
holes, 18 / 9 / 6, R28,363.50 — the edging is priced by kind, and the metres per
kind did not move); every `check_*.py` green, twenty-one now with
`tools/check_export.py`. What it is:

1. **Columns.** The code used to write the item number under `Component` and
   the designation under `Material`, and never wrote the board — whatever this
   file said about "Component is written from `Panel.label`" was wrong. Now
   `export_plaza.HEADER` is **`Customer Number`** (the designation,
   `Panel.label`) in front of `PLAZA_HEADER`, Plazaboard's template byte for
   byte (`JOB NO ` with its trailing space, four blank headings, two `total
   edging`): `Component` is their item number 1…n restarting per file,
   `Material` the board id. `holes` stays the line total; a zero edging total
   is written `0` (theirs), not `0.0`; no padding rows.
2. **One number per panel, no merging.** Every line stays a line. What makes
   two lines the same panel is `model.panel_signature` — everything but the
   qty: board, size, grain, edge counts, pot holes, edging name.
   `engine.born_distinct` letters by it at birth (it used to read board and
   size only), and D13 asks the same question of the finished list, so it
   never fires on a generated job (pinned for every job the checks know).
   Lettered for the first time: October **104, 404, 2704, 2804, 2904, 3004**
   (supports differing only in edging); Test.json **204, 304, 404, 604, 704,
   1504** (404 reads `404a, 404b, 404b, 404b, 404c`); 1517 differs only in qty
   and keeps its number. Letters follow the order the lines are born in, so
   re-entering Test.json cabinet 7's legacy supports (Front first) swaps
   704a / 704b — the same lines, the same cost (pinned in `check_supports.py`).
3. **Edging names: the Boards tab's, and nothing else.** The edge mat is the
   kind + the board's Edging Name exactly as typed (`PVC Grey`). The flat
   `carcass_edge` / `door_edge` / `drawer_box_edge` strings are **no longer
   read** — kept in the file for the byte-for-byte round trip, the editor's
   "Clear it" offer gone, `/api/compute`'s `edge_override` / `tape_overrides`
   gone. A bespoke or loose panel's typed `edge_material` goes through
   `model.resolve_edging` (in `engine.resolved`): kept if it names a project
   board's Edging Name (case aside, rewritten exactly as the board has it),
   otherwise the same kind in the board it was cut beside — the cabinet's
   exterior board (`engine.loose_beside` for a loose panel: the cabinet of that
   number, else the exterior board most cabinets take). The house `MATERIALS`
   BROOKHILL token is `BROOKHILL` (was `WOOD`). `model.WHITE_EDGE` is gone;
   `WHITE_TOKEN` stays and says why (a legacy white row names only the word, so
   the board is found by its Edging Name). `validate.ALLOWED_EDGE` is `{""}` —
   the hardcoded WOOD / SOLID names are gone; W10 asks only what the project's
   boards generate. Every Edging Colour dropdown — doors, drawers, supports,
   Panel design — shows the board's **Edging Name** (`model.edging_label`,
   served as `edging_label` on each board: `WHITE (WHITEMEL)` where two boards
   share one), the stored value still the id. The blind panel's dropdown picks
   the board it is CUT from (its edging colour follows), so it keeps the board
   names; its "Ordered as" is the generated name.
4. **What moved.** October: every `PVC WOOD` / `2mm WOOD` is `PVC BROOKHILL` /
   `2mm BROOKHILL` (metres 167.082 / 179.272, as before); the typed panels this
   touched are 305b, 505b, 701a-c, 702, 703, 705, 707, 1301, 1302, 1307, 608 and
   2408, listed in `check_export.py`. Test.json: cabinets 1-3's WOOD
   overrides read BROOKHILL, **cabinets 4 and 5's read `Grey`** (their exterior
   board is GREY — the brief expected BROOKHILL), and **cabinet 4's drawer
   faces go from `2mm WOOD` to `1mm Grey`**, the 1 mm its Drawers section
   chose, which the `door_edge` override had been masking; its total R11,316.00
   → R11,257.50. `Test_Build.json` reads BROOKHILL, total unchanged.
   `snapshot.py --compare` against the tree before: only designations
   (`code`), edging names, the edging summary, Test's total, and the edging
   legend line on the drawings; no issue moved on any job.
5. **Found on the way, fixed:** the board swap's "each board gains and loses"
   tally was taken of the before list AFTER the in-place re-derivation had
   rewritten the bespoke and loose panels under it (the `engine.resolved`
   identity lesson again): October's MEL -> BROOKHILL read 254 / 77 before,
   and is the true 272 / 59 now. `board_swap` copies the before list.
6. **`tools/check_export.py`** pins it: the header off Plazaboard's own CSV;
   columns 1-3 for every job (benchmark, live Test.json, every fixture); no
   number on two different panels, read off the files; no WOOD; every edge mat
   a kind + an Edging Name in that project; the frozen Test.json facts (404,
   1517, the dropdown labels) off **`tools/fixtures/Test_export.json`** (Test.json
   at 201d360 — a check never reads live workshop data); and **the October job
   against Plazaboard's files**, as a multiset per board outside
   `regen_check.KNOWN`, every remaining difference listed and pinned with its
   reason: their MEL file drops the four edge-flag columns from item 29 on
   (27 lines), cabinet 7's corner sides / top / bottom are edged in our job and
   not in theirs, their extra 2730 x 1300 line in MEL and BRK, the W2 filler
   (our 2882, their 2730), and four backs keyed the other way round. Also
   listed rather than hidden: inside the KNOWN cabinets Plazaboard keyed every
   MEL edging as PVC BROOKHILL, including our 9 PVC WHITE lines (drawer sides,
   white-edged supports).

**Report back — open, for Rudolf.** (a) Plazaboard keyed the October job's
white edging (33.5 m of drawer sides and white-edged supports) as PVC
BROOKHILL; the job still says PVC WHITE. (b) Test.json cabinets 4 and 5 now
order Grey edging, and cabinet 4's drawer faces 1 mm rather than 2 mm — check
that is what is wanted. (c) Their files carry a 2730 x 1300 line in MEL and in
BRK that is on no sheet we sent.

### The export folder, organised (28 September 2026)

**The export folder, organised (28 September 2026, brief
`Claude outputs/output-folders-brief-2026-09-28.md`, agreed with Rudolf).**
File locations only: no cut-list, nesting, costing or drawing content moved.
Benchmark unchanged (272 / 59 / 30, 92 pot holes, 18 / 9 / 6, R28,363.50);
`snapshot.py --compare` against the tree before identical. `output/<job>/` is
now `cutlist/` (the CSVs, `<job>_accepted.txt`), `nesting/` (`nest_<BOARD>.svg`),
`drawings/` (plan, wall elevations, and the board pictures they name — they
must sit beside them), `snapshots/` (`<job>_3d_<n>.png`) and `_previous/`.
**Export clears and rewrites** (ruled): `api._retire_export` moves the last
export's three folders into `_previous/` (replacing it — one level of undo),
then writes fresh, so a file it no longer writes (the old Run drawing, a wall
since unticked) cannot linger; **`snapshots/` is never touched by an export**.
The reply carries `folders` (per folder, the files), `rel` (`output/<job>/`)
and `previous`, and the toast names them. `check_elevation.py`
`ui_restructure()` pins the folders, the move into `_previous/`, a stale file
not surviving, snapshots untouched and numbered in their own folder. The
Playwright screenshot folders moved to `output/_checks/<script>/` so they
cannot collide with a job's folder. Not touched, by Rudolf's choice: the
legacy root `out/` and the root `snapshot-3d-step0*.json` files; loose files a
pre-brief export left at the top of `output/<job>/` are also left where they
are (only the three folders are retired).

### check_runners.py read live data — frozen (28 September 2026)

**`check_runners.py` read live data — frozen (28 September 2026).** Commit
f4d87b0 ("New drawer cupboard added to test") changed `jobs/Test.json` (cabinet
15 added with drawers, cabinet 4's drawers re-set so its criticals cleared, a
`runners` key written) and `hardware.json` (Gelmar setback 3 -> 2), and five
checks pinned those live files. **Ruled by Rudolf: setback 2 is right, and a
runner record in the library is a changeable setting** — so the catalogue check
now pins the built-in `hardware.SEED` — **setback 2 as well, ruled the same
day** (only the fallback when the library has lost the record; `LEGACY` and
the field default stay 3, so no saved job moves) — and asks the live
`hardware.json` only that the Gelmar record is there. The Test.json checks read
`tools/fixtures/Test_drawers.json`, Test.json verbatim from the commit before
f4d87b0 (cabinet 4 at faces 110 / 165 / 220 over boxes 90 / 150 / 200), and so
does `ui_check_drawers.py --stage offset` (through `load_fixture`, as
`ui_check_3d.py` does). The fourth time for this lesson.

### Drawers, runners and supports (28 September 2026)

**Drawers, runners and supports (28 September 2026, brief
`Claude outputs/drawers-runners-supports-brief-2026-09-28.md`, agreed with
Rudolf; sketch `drawer-setting-sketch-v2.svg`).** Built in order, Parts 1 to 6,
each committed with the benchmark unchanged (272 / 59 / 30, 92 pot holes,
18 / 9 / 6, R28,363.50) and every `check_*.py` green. Exercised in the running
app with `tools/ui_check_drawers.py` (Playwright, stages per part, screenshots
into `output/_checks/ui_check_drawers/`).

1. **Supports: wording and edge counts** (UI only, no cut-list change). Support
   rows read **Support Material / Edging Material / Edging Colour**; the stored
   type `front` is shown as **Top Front** everywhere a person reads it
   (`SUPPORT_TYPE_LABEL`, the 3D label, messages) — the stored value and every
   check id unchanged. The four per-edge tickboxes are gone: **Long edges
   0/1/2** and **Short edges 0/1/2**, as Panel design asks. Which edge a count
   means is `model.support_edges_for_counts`, behind `/api/support-edges` (long
   1 = the row's `front` edge — a Top Front's / Top Rear's front, Back 1's
   bottom, every other Back's top; long 2 both; short 1 the left end, short 2
   both). `Support.edges` is still what is stored. A stored set that is not
   canonical for its counts (`support_edges_canonical`, e.g. Test.json cabinet
   6's Back, rear edge only) is kept and drawn as stored, and a note under the
   row says so until a count is changed. Ordered as reads as a panel's line
   ("PVC WHITE on 1 long + 1 short edges"). Pinned in `check_supports.py`
   `counts_not_ticks()`: the same counts cut the same line and cost whichever
   edges they name.
2. **Runner catalogue, and Boards became Catalogue.** The top tab is
   **Catalogue** with two sub-tabs, **Boards | Runners** (`S.catSub`, the Room
   Plan | Elevation pattern); Boards is the board library exactly as it was,
   and every jump that landed on Boards (start-up, New, Add cabinet with no
   board) lands on Catalogue -> Boards through `openCatalogue`. Runners is
   `hardware.json` (a `runners` list — `save` keeps any other list, so hinges
   and handles can sit beside it) through `cabinetgen/hardware.py`: add / edit /
   delete, tick into the project (the record is copied into `Job.runners`,
   price per pair captured, written only when there is one), a used-by-saved-
   jobs guard on delete, and **Use for all drawers**. Seed: **Gelmar 45 mm
   full-extension ball-bearing** (`GELMAR45`: 45 high, 13.5 a side, 12.7 rail,
   300-600, full, 35 kg, lift 5, setback 3 — **2 since, ruled 28 September
   2026**). A cabinet names its runner
   (`Cabinet.runner`, written only when set); a new cabinet takes the job's
   first, or the Gelmar seed copied in (`/api/runner-default`). **The length
   is picked over the record's list** (`Standard.pick_runner(depth, lengths)`:
   the longest leaving `runner_clearance` 40 behind), **the box width off its
   clearance** (`Standard.drawer_box_width` / `drawer_front_length`: opening −
   2 × 13.5, then two 16 mm sides — the old 59 exactly). `Standard.runner_lengths`
   and `drawer_front_deduct` are gone: a cabinet naming no runner — every job
   saved before this — is cut on the built-in **`hardware.LEGACY`** record
   (350 / 450 / 500, 13.5, 45, lift 5, setback 3), never offered for new work,
   so the October job and Test.json cut exactly what they cut. The runner
   record is reached through `Cabinet.runner_rec`, bound to the job's copy by
   `Job.bind_runners` (on construction, and by `generate_job` / `validate`), so
   every geometry call reads it without a new argument. Re-pointing a cabinet
   (its Drawers section's **Runner** dropdown) or the job (**Use for all
   drawers**) asks `/api/runner-swap` first and names the drawer lines that
   move (a depth that now takes 400 or 550 — a design change the operator
   makes). A cabinet naming a runner the project never selected is a CRITICAL
   (`runner-not-selected`); `runner-depth` keeps its id and names the record's
   shortest. Runner pairs are priced off the job's copy in `hardware` on the
   compute reply and on Catalogue -> Runners — **not** in the Plazaboard
   estimate. `tools/check_runners.py` pins it.
3. **The drawer setting** (sketch v2, confirmed by Rudolf). `room.drawer_layout`
   is THE one place a box is placed; `drawer_box_tops` (the support-foul
   critical), the drawer checks and the 3D all read it. In the supports
   spec's carcass frame: faces spaced exactly as always (bottom face flush with
   the carcass underside, `stack_gap` 2 between, the door 3 short at the top);
   then each box hangs off its OWN face, its bottom `room.drawer_rise` — the
   bottom panel 16 + the runner's `lift` 5 = **21** — above the face bottom (the
   bottom box on a runner standing on the bottom panel); box front flush with
   the carcass front, the runner's length long, the opening less the
   clearance each side wide; outer rails against the sides from the carcass
   front, `lift` under the box; inner member `setback` (Gelmar 2, legacy 3)
   behind the box front.
   No box position ever moves a face. Worked numbers pinned in
   `check_runners.py` `drawer_setting()`. The divider drag (`drawers.split_pair`,
   `/api/drawer-divider` with the job) now holds each face to box + 21.
   **Snapshot moved, as the brief says it must:** Test.json cabinet 4's top
   box (90 in a 110 face at 667) now reads 688-778, into the band under its
   Top Front / Top Rear at 764 — a new `support-drawer-foul` CRITICAL. Before,
   the box stood on its face bottom (757) and cleared it. Nothing else moved.
4. **Inner drawers** (`Drawer.inner`, `Drawer.z`, both written only on an
   inner drawer). Behind the door; the face is the size of the box's carcass
   — the box's outside width (opening − 27) × the box height — a code-20 line
   off its face board (note `inner`), grain up the height, edged like any face.
   **Ruled by Rudolf on the three things the geometry did not settle:** the
   face front sits "the same as the recess for shelves" — on the shelves'
   line, flush with the carcass front edges, so the box and the runner start a
   face thickness back; heights are **typed per drawer** (`z`, the box bottom
   above the carcass underside), and **equally spaced from the bottom** — the
   lowest on a runner standing on the bottom panel (21), the rest at the foot
   of equal slots of the inside height (`room.inner_drawer_z`) — regenerated
   whenever the count changes (`/api/inner-drawers`); a cabinet's drawers are
   **all inner or all outer**; and an inner drawer's runner is picked **over
   the depth less the face** (545 deep: outer 500, inner 450). Inner drawers
   take no part in the face stack: `Cabinet.outer_drawers` is what
   `front_stack_check`, `solid_parts` (the plan faces, the door above them)
   and the elevation read. Three criticals: `drawer-inner-no-door`,
   `drawer-inner-mixed`, `drawer-inner-range` (runner under the bottom panel,
   or box into the top). Editor: Drawers -> **Drawer type** Outer | Inner; for
   inner, **Number of drawers** and a Height per row, with the engine's face
   size and box top beside it. Pinned in `check_runners.py` `inner_drawers()`.
**FACES LEAD, BOXES FOLLOW — ruled by Rudolf, 28 September 2026, later the
same day. It REPLACES the box-height rules of Part 5 below and anything said
earlier about box height.** The faces are spaced first, exactly as ever
(bottom face flush with the carcass bottom, `stack_gap` 2, `door_height_gap` 3
at the top); no box position ever moves a face. Then each box is placed
against its OWN face:

- **Outer drawers.** (1) Every box lies entirely within its own face's height
  — box bottom >= face bottom AND box top <= face top — or `drawer-box-face`
  (CRITICAL): a box is never mounted higher or lower than its own face.
  **Since 29 September 2026 (evening) never FLUSH either:**
  `Standard.drawer_box_clear` 2 — bottom >= face bottom + 2, top <= face top
  − 2, and top <= a Top Front / Top Rear band's underside − 2 (else
  `support-drawer-foul`); an upper drawer's least offset is therefore 2. (2)
  Each box sits at the bottom of its face, `Drawer.offset` up — per drawer,
  editable in the drawer row (**Off.**), blank = the default `drawer_rise`,
  21; written to the job file only when set. (3) The BOTTOM drawer may be
  raised, never set below 21: `drawer-bottom-offset` (CRITICAL). (4) An upper
  drawer may go lower or higher, still under rule 1. (5) The tallest box that
  fits is face − offset (`drawer_layout`'s `max_box`), shown as `≤n` beside
  Box h, red when the box is over it — **since 29 Sept: up to
  `Cabinet.box_top_limit_of`, the face top or the support band, less the 2,
  and Auto fills exactly that; red off `drawer_layout`'s `fits`. The Offset
  field is held to `offset_min` / `offset_max` off the engine.**
- **Inner drawers.** (6) Equal spacing as built. (7) At least
  `Standard.inner_drawer_min_gap` (30) clear between adjacent inner boxes, or
  `drawer-inner-gap` (CRITICAL).
- **Kept.** (8) `drawer-box-clash` — a box into the box above (not repeated
  where `drawer-box-face` already named that drawer; between inner boxes, an
  overlap rather than a short gap). (9) `support-drawer-foul`. (10) The runner
  checks: `runner-depth`, `drawer-runner-height`, `drawer-inner-range`.
- **Retired:** `drawer-box-height` ("box not shorter than its face"), which the
  face rule replaces — a box as tall as its face at offset 0 lies within it.
- The divider drag holds each face to its own box + its own offset
  (`split_pair(..., rise, bottom_rise)`, `/api/drawer-divider` with `above` /
  `below`).
- Test.json (not edited; frozen since as `tools/fixtures/Test_drawers.json`,
  which is what the checks read): cabinet 4 at the default offsets — drawers 1-3
  `drawer-box-face` (1, 6 and 1 mm over), the top drawer still
  `support-drawer-foul`. Snapshot: only those three messages' wording moved.
  Pinned in `check_runners.py` `drawer_checks()`; `ui_check_drawers.py
  --stage offset` drives the Offset column in the running app.
- Also fixed with it, both in the scripts and both pre-existing (seen on the
  tree before the drawers brief): `ui_check_3d.py`'s arrow drag now awaits
  the drop's compute and scene before the next arrow is read (it failed 1 run
  in 4 on "snapped it to 'on top of 6'"), and its no-WebGL stage waits for the
  cabinet table to paint before counting its rows.

5. **The drawer checks** (as first built — see the ruling above, which
   replaces the box-height parts), all CRITICAL, all off `room.drawer_layout`
   (`validate._drawer_setting`), pinned in `check_runners.py`
   `drawer_checks()` with worked numbers: **`drawer-box-face`** — a box's top
   above its OWN face's top, every box (**ruled strict by Rudolf**, not only
   the top one): with the 21 rise a face must be at least box + 21 (face 170,
   box 150: 171 > 170, "the face needs to be at least 171, or the box 149");
   the old `drawer-box-height` (box not shorter than its face) keeps its id and
   is not repeated. **`drawer-box-clash`** — a box into the box above; with
   every outer box hung the same 21 off its face that can only follow one of
   the two above, so in practice it is inner drawers at typed heights (21 and
   160, boxes 150: 171 into 160). **`drawer-runner-height`** — a box lower than
   its runner (44 on a 45 runner). **`runner-depth`** keeps its id and names
   the record's shortest length. The support-foul critical reads the same
   layout (Part 3). **Snapshot moved, as ruled:** Test.json cabinet 4's
   drawers 1-3 (faces 110 / 165 / 220 over boxes 90 / 150 / 200) now reach 1, 6
   and 1 mm above their faces — three `drawer-box-face` criticals. The October
   job raises none of them.
6. **Drawer boxes and runners in 3D** (`room.drawer_parts`, carried by
   `interior_parts` — never `solid_parts` — so the plan, Finish and every wall
   elevation are unchanged: `check_runners.py` draws them all with the boxes
   taken out and gets the same SVG, and the snapshot's drawing hashes did not
   move). Per drawer, off `drawer_layout`: two sides (the runner's length,
   grain along it), a front and a back between them, a grooved 3 mm base 16 up
   and 6 into all four (a housed 16 mm one on the bottom edge), each tied to
   its cut-list line (`scene.ROLE_TO_PANEL`); an inner drawer's face with its
   box. **Fronts open slides the face, box and base out together**, as far as
   the runner travels (`pull.distance` = the layout's `travel`: its length on
   full extension, 375 of 500 on a three-quarter runner); the runner stays.
   **Runners are simple blocks** — rail thickness × height × length, one per
   side, grey (`PAPER.runner` in `view3d.js`), not a board, "hardware — a
   runner is bought, not cut" instead of a line — behind a **Runners** toggle
   in both 3D toolbars. `check_scene.py`'s old "no drawer-box part" pin is now
   "one drawer box per drawer", and the runner is the one part allowed no
   line. `tools/ui_check_drawers.py --stage 3d` opens the fronts in the
   Cabinets tab's 3D and measures the slide (500) and the runner not moving.

**Report back — open, for Rudolf.** Nothing from Part 4's question remains
open: the inner-drawer face sits on the shelves' line (his answer), heights
are typed and auto-spaced, all-inner-or-all-outer, runner over depth − 16.
Two things to look at in Test.json: cabinet 4's drawers now raise four
criticals (three `drawer-box-face`, one `support-drawer-foul`) — boxes 90 /
150 / 200 in faces 110 / 165 / 220 need to drop to 89 / 144 / 199 (or their
offsets lower), and the top box to 76 to clear the Top Front band (since the
2 mm clear, 29 Sept: 87 / 142 / 197, and 74) — so
Test.json does not export until they are changed; and the Gelmar price per pair is R0.00 in `hardware.json`
until it is typed in.

### UI restructure, Session 2 — Fresh look, first round (28 September 2026)

**UI restructure, Session 2 — Fresh look, first round (28 September 2026,
the same brief, "styling only").** One `<style>` block in `app/index.html`
changed and nothing else: no markup moved (one inline `style` attribute on the
export dialog went into the stylesheet), no handler, no id or class the
scripts drive. Benchmark unchanged (272 / 59 / 30, 92 pot holes, 18 / 9 / 6,
R28,363.50); every `check_*.py` green; `snapshot.py --compare` identical; and
**Session 1's three Playwright scripts re-run UNCHANGED and pass**, which is
what proves nothing functional moved. Before-and-after screenshots of every
tab and sub-tab are in `Claude outputs/ui-session2-screenshots/`. What it is:

- **The palette is `:root` and nothing else.** The drawings' inks (`--ink`,
  `--muted`, `--rule`, `--faint`, `--carc`, `--door`, `--face`) keep their
  values — the elevation and nest SVGs share them. Added: `--accent` (the
  selection blue view3d.js already drew, `#1f6fd0`, now the one accent:
  primary buttons, the tab underline, every `.on` toggle, a selected row),
  `--accent-soft` / `--accent-line`, the soft status pair per level
  (`--crit-soft` / `--crit-line`, warn, ok, info), `--surface` (card
  headers, table heads, the strip), `--surface-2`, `--viewport`, the radii
  (`--r-s` / `--r` / `--r-l`), two shadows, the focus ring, the font stack,
  and the editor's seven section tints (`--sec-doors`…), which used to be
  literals on the `.sec` rules. Every hex that was scattered through the
  stylesheet — the selection blue in five places, the pill tints, the flash
  row, the issue backgrounds — now reads a token. Board colours and
  pictures in a drawing are data and do not come through any of it.
- **Criticals and warnings carry a MARK as well as a colour**, by CSS
  `::before` so no text a script reads changes: `✕` on a critical, `▲` on a
  warning, `✓` on ok / accepted — on the strip's pills, every `.pill`, the
  Validation level badges (now pills), the cut-list row notes, the dock's
  issue links, the lapse note, a field's problem line, the door-swing
  verdict, and the two toasts (a tick, a cross).
- **Tab bar, cards, buttons, inputs, tables, strip, toasts, dock strip, 3D
  toolbar**, as the brief lists them: accent underline tabs; cards with a
  tinted header band, larger radius and a hairline shadow; 6 px controls
  with a hover, a pressed state and an accent focus ring (keyboard focus is
  `:focus-visible`, so a click shows none); table heads on `--surface`;
  the strip as cells divided by hairlines; toasts with an icon column and a
  short rise-in; the dock's chevron as a round button on a hairline; the 3D
  toolbar's toggles in the accent; Room's Plan | Elevation as a segmented
  control; the empty states as dashed boxes; a thin scrollbar.
- **Narrowed** (`@media (max-width:1080px)`): the dock wraps under the
  drawing with the editor full width, the two-column card rows stack, and
  nothing else moves. The pywebview window opens at 1360 x 900, where the
  layout is exactly Session 1's.
- **One pre-existing nit fixed in CSS:** the 3D toolbar's dropdown box is
  created empty and unhidden and only filled on its first open, so until the
  first click anywhere it drew as a stray white pill under "Views";
  `.v3dmenu:empty` is hidden now.

**Not done, by the brief:** mockups (Rudolf asked for it built directly); the
per-cabinet exploded view.

**Seen and left alone — a race in the UI scripts' own waits, not in the app.
FIXED since, in the drawers brief (Part 5):** both scripts' `computed()` now
clear the debounce and await `compute()` (and, in `ui_check_restructure.py`,
the drawing on show), which is the fix described below; three full runs of
each passed. The original note:
`ui_check_restructure.py`'s `computed()` is a fixed 0.35 s sleep and
`ui_check_attached.py`'s a 0.45 s one, each raced against the compute a drop
starts (`compute()` straight after `/api/attach-move`, no debounce). Read too
early, the derived place (`placed_at`) and the editor's readout are the
previous compute's, and the line "the room follows: its place on the wall
moved by the same" (or Attach's "it stands exactly where it did") reports 0
while the write itself has already passed. Seen in two of five full runs on
the cloud machine, the same line each time, never in the stage run alone, and
identically on the tree before Session 2's stylesheet. The scripts were left
unchanged because the brief runs them unchanged; the fix, when one is wanted,
is a wait on the compute in flight (`computing` false AND a `S.res` newer than
the one before the drop) rather than a sleep.

### UI restructure, Session 1 — Structure (28 September 2026)

**UI restructure, Session 1 — Structure (28 September 2026, brief
`Claude outputs/ui-restructure-brief-2026-09-28.md`, agreed with Rudolf).** Benchmark unchanged (272 / 59 / 30, 92 pot
holes, 18 / 9 / 6, R28,363.50 — `regen_check`'s output byte-identical to the
tree before); every `check_*.py` green, still twenty; `snapshot.py --compare`
against the tree before identical on every job (the Run's hash included — it is
an internal helper now, unchanged); every job on disk round-trips byte for byte.
Exercised in the running app with Playwright: `ui_check_restructure.py` (new,
seven stages, screenshots), and `ui_check_3d.py` and `ui_check_attached.py`
re-pointed to where things now live and passing. The short form:

1. **Tabs: Boards · Cabinets · Room · 3D view · Cut list · Nesting · Validation.**
   The app opens on Boards, and New goes there (a new job starts on Boards);
   Load leaves the tab as it is. Every internal jump still lands.
2. **Room has two sub-tabs, Plan | Elevation** (`S.roomSub`). Plan is the Room
   tab as it was — plan, layers, isolate, drag, zoom, and the Walls, Placements,
   Gaps and Plinth cards under it. Elevation is the wall views moved from the
   Cabinets tab, unchanged (wall picker, Line / Finish, zoom, cabinet and divider
   drags, vertical snap, click-select, legend, dimension lines). With no room it
   asks for one (**Add a room**). The one editor is docked beside either.
3. **The Run left the UI.** `/api/compute` no longer sends it; `/api/elevation`
   needs a wall. **Export** writes one elevation per wall TICKED in a dialog (all
   ticked by default; `walls` in the payload, all when absent) **plus the plan**
   (`<job>_plan.svg` — the brief says "the plan as today", but no export ever
   wrote one, so it is new), and no `<job>_elevation.svg`: a job with no room
   now exports no drawing. `render.elevation_svg` stays as an **internal
   helper** — the no-room fallback of `wall_elevation_svg`, pinned byte for byte
   — and its layout, `run_layout`, is still what the 3D tab stands a room-less
   job on. The checks that pinned the Run say so; `check_elevation.py`'s
   `ui_restructure()` pins the export and the Run's absence from the UI.
4. **The Cabinets tab: the selected cabinet alone in 3D** over the cabinet list,
   the editor on the right. See **The Cabinets tab's 3D** below. It includes
   **the attached-panel drag (spec B4)**, built here.
5. **Placing from a list of unplaced items** — Room (Plan and Elevation) and
   the 3D tab (reverses the 21 September "not needed"). See **Placing from the
   unplaced list** below.

**Two pre-existing faults found by the Session 1 checks, fixed:** (a) a drawer
**divider drag never stuck** — the press also selects the cabinet, which asks
`/api/drawer-solve` for the rows as they WERE, and that reply landed after the
divider's write and put the old heights back (`solveStack` now drops a reply
whose rows changed while it was in flight; the same on HEAD before this work,
checked on a worktree); (b) the **plan, elevation, divider and 3D drags never
lit "unsaved changes"** — they call `compute()` directly; each now marks the job
dirty. Nothing else about either changed.

### Attached panels, and a new cabinet's supports by its kind (28 September 2026)

**Attached panels, and a new cabinet's supports by its kind (28 September 2026,
spec `Claude outputs/attached-panels-spec-2026-09-28.md`, agreed with Rudolf).**
Benchmark unchanged (272 / 59 / 30, 92 pot holes, 18 / 9 / 6, R28,363.50);
every `check_*.py` green — twenty now, `check_attached.py` added; `snapshot.py
--compare` against the tree before this work identical, and every job on disk
round-trips byte for byte. Exercised in the running app with Playwright
(`tools/ui_check_attached.py`): + Panel on this cabinet, the offsets, the plan
and elevation drawing it, a real drag of its cabinet carrying it, Detach and
Attach, Duplicate, delete with No and with Yes, the 3D handles, and the support
defaults following the kind. See **Attached panels** below. The short form:

1. **A panel can be FIXED TO a cabinet** — `PanelSpec.attached_to` and three
   offsets (`at_x`, `at_y`, `at_z`) in the supports spec's carcass frame. Its
   place is DERIVED: `room.attached_placement` applies the cabinet's placement
   to the offsets, and `placement_for` hands that back, so every drawing, snap
   and check that reads a placed panel reads it unchanged. No placement record
   is stored for it; `api.drag` refuses it (move the cabinet, or type the
   offsets). Standalone panels are exactly what they were.
2. **It counts as part of the cabinet** in the run's gap (level with the
   carcass), in `overlaps` (a CRITICAL against another cabinet), in `clashes`
   (a door or drawer sweeping into it) and in `above_ceiling`; **not in
   tip-up**, which still reads `placed()` alone. Cutting into its OWN carcass
   is a WARNING (`attached-into-carcass`). Attached to nothing the job has is a
   WARNING (`attached-host`) and it stands nowhere.
3. **Made, attached, detached, duplicated and deleted through the server**:
   `/api/panel-new-attached` (an end panel off the cabinet's geometry),
   `/api/panel-attach` (offsets worked out so it does not move),
   `/api/panel-detach` (one panel, or every panel on a cabinet — the "No" of
   "Also delete its N attached panels?"), `/api/duplicate` (a cabinet's copy
   brings copies of its panels, new numbers in the one series). The browser
   works out no offset and no number.
4. **A new cabinet's support rows follow its kind** (`Cabinet.default_supports`,
   `/api/support-defaults`): base Front + Top Rear + 2 Backs, wall 3 Backs,
   tall 4, a blind corner by its kind, a mitre or an ell none — and they follow
   a kind change only while they are still those untouched defaults. Existing
   cabinets and legacy rows are untouched.
5. **`check_supports.py` no longer reads the live `Test.json` to pin "nothing
   types a legacy row on its own"**: Rudolf re-entered cabinets 2 and 7 on 28
   September (commit 0fda4a9), which is the operator typing them, and the three
   checks that read the live file broke. They read the frozen
   `tools/fixtures/Test_legacy_supports.json` now — the same lesson as
   `Test_Build_pre_library.json`.

**Not built, by the spec's scope:** the drag in the single-cabinet 3D view
(B4) and the UI restructure — **both built since**, in Session 1 of the UI
restructure (above).

### Every Back support carries its OWN edging (ruled 27 September 2026)

**Every Back support carries its OWN edging (ruled 27 September 2026, later the
same day, replacing the spec's single Back edging).** A Back is a row of its
own — `Cabinet.new_support` and `/api/support-new` give a new one its defaults:
cut from the carcass, in that board's own edging kind (`default_support_kind`,
PVC before 1mm before 2mm; `''` for a board with no edging) and NO edge ticked,
so it is unedged and orders no tape until an edge is ticked (the engine writes
no `edge_material` on a typed row with nothing banded). The editor's Back block
is one block per row with **+ Back support** and a remove button; a re-entered
row of several identical supports shows as `Back 1–4`. **Re-enter keeps each
legacy row's own qty, cut board and edging** — `Cabinet.reentered_supports`,
behind `/api/support-reenter`, decided on the server — so the cut list and the
cost do not move: Test.json cabinet 6 (4 unedged, 1 PVC WHITE, 1 1mm WHITE)
re-enters as three Back rows line for line, and the job total to the cent;
cabinet 7's front-edged rail becomes the Front and its three white ones one
Back row, the same lines with the Front first. Both pinned in
`check_supports.py`. Benchmark, every check and the snapshot unchanged.

### Shelves and supports — typed supports, drawn in 3D (27 September 2026)

**Shelves and supports — typed supports, drawn in 3D (27 September 2026, spec
`Claude outputs/shelves-supports-spec-2026-09-27.md`, agreed with Rudolf).**
Benchmark unchanged (272 / 59 / 30, 92 pot holes, 18 / 9 / 6, R28,363.50);
every `check_*.py` green — nineteen now, `check_supports.py` added; `snapshot.py
--compare` against the tree before this work identical; and every job on disk
(all six in `jobs/` and the October fixture) produces the same panels, the same
issues and the same file byte for byte. Exercised in the running app with
Playwright against `Test.json`: the legacy read-only view, Re-enter, the three
blocks, the drawer-fouling critical blocking the export, the editor's Save, and
the 3D tab with fronts open and in X-ray. See **Supports** below. The short form:

1. **A support row has a TYPE** — `Support.type`: `front` and `top_rear` (flat,
   across the top of a BASE unit, one or none each) and `back` (upright in the
   16 mm cavity, any number) — and says edge by edge which of its four edges
   are banded (`Support.edges`). `room.support_layout` is the one place a rail
   is positioned, in the spec's carcass-local frame; `tools/check_supports.py`
   asserts the brief's worked numbers exactly.
2. **Legacy rows are untouched**: no type, cut EXACTLY as before (one long edge
   banded), only PLACED for drawing by the legacy rule (base: one front-edged
   rail is the Front and the rest Backs; a carcass with a top: all Backs). The
   editor shows them read-only "as quoted" with a **Re-enter** button — Rudolf's
   explicit act — which keeps every row's own edging (the later ruling above;
   the one-row Back block that folded edgings away is gone). Nothing converts
   a legacy row on its own.
3. **Shelves and supports are DRAWN in 3D** (`room.interior_parts`, kept OUT of
   `solid_parts` so the Finish elevation, the plan and every wall elevation are
   byte-identical). Each banded edge is a band of the edging board's colour
   INSIDE the finished size (`room.tape_solids`, `scene.TAPE_BAND_MM`); no
   position depends on whether an edge is taped. Shelves are spaced evenly from
   the bottom panel's top face to the top of the sides, display only, and the
   legend says so. `scene.NOT_DRAWN` then listed drawer boxes and legs only
   (drawer boxes drawn since 28 September 2026 — legs only now).
4. **Three criticals on typed rows** (`validate._support_layout`): a drawer box
   into the 16 mm band under a Front / Top Rear (`support-drawer-foul`), Front
   and Top Rear overlapping in depth (`support-depth-overlap`; D >= 219 with a
   backing, 200 without), Backs that do not fit (`support-back-fit`); plus a
   WARNING for a Front / Top Rear stored on a carcass with a top, which cuts
   nothing (the tickbox bargain).
5. **Back "three" is not offered for a new cabinet** (`api.defaults` backs are
   `four` / `none`); a job carrying it — the benchmark's vanity units 27-29,
   Test.json cabinets 2-5 — loads, shows it "as quoted, no longer offered" and
   cuts exactly as it did.
6. **The editor's Save button is a refresh, not a write** (`saveRefresh`):
   computes now rather than after the debounce and redraws every place the
   cabinet appears; the top-bar Save is still the only thing that writes.

**Not built, by the brief's scope:** the UI restructure, attached panels, and
the single-cabinet 3D view — supports and shelves show in the existing 3D tab.
**For Rudolf to run locally:** the 22-of-30 cabinet diff in `regen_check`
needs the Wardrobes xlsx, which the cloud machine does not have.

### "Add a room" did nothing outside 3D — fixed (23 September 2026)

**"Add a room" did nothing outside 3D — fixed (23 September 2026, brief
`Claude outputs/room-add-bug-brief-2026-09-23.md`).** A new job, and any file
saved with no room, reaches the browser with no `placements` key; Add a room
then threw in `renderPlaces` and the plan, Gaps and Plinth never drew (3D only
worked because `refreshScene` runs first). Every read now goes through one
helper, `places()` in `index.html`, which makes it an array; `blankJob`,
`adopt` and Add a room call it too. `store` still writes no `placements` key
when the list is empty, so every job on disk round-trips byte for byte —
pinned in `check_room.py`. And each Room-tab card renders through `guarded`,
so one that throws says so in its own card and the others still draw.
`ui_check_3d.py --stage room` drives it: New, `Test_Panels` and `untitled`,
then a board, a cabinet placed from the table and dragged in the plan and in
3D. Benchmark, every check and the snapshot unchanged. **Seen and not
touched:** a closed four-wall room given a fifth wall reports the closure miss
but the plan still looks closed — not yet looked into.

### Part F — the 3D view, and one editor across every view (23 September 2026)

**Part F — the 3D view, and one editor across every view (23 September 2026,
brief `Claude outputs/3d-view-brief-2026-09-23.md`, on branch `3d-view`).**
Built F1 to F6 in order, each committed with the benchmark unchanged
(272 / 59 / 30, 92 pot holes, 18 / 9 / 6, R28,363.50), every `check_*.py`
green — eighteen now, `check_scene.py` added — and `snapshot.py --compare`
against the tree at Step 0 showing no panel, issue, summary, total or drawing
moved. Exercised in the running app with a real mouse in headless Chromium
(`tools/ui_check_3d.py`, six stages), not only in Python. See **The 3D view**
below for what was built; the short form:

1. **F1** three.js 0.186.0 and camera-controls 3.1.2 vendored under
   `app/vendor/` with their licences, served by `Handler._static` off a
   whitelist; a "3D view" tab whose module `app/view3d.js` is imported the
   first time it is opened; offline is the acceptance.
2. **F2** `cabinetgen/scene.py` and `/api/scene`: the scene built on the
   server from `room.solid_parts`, plus the backing board (`room.back_part`)
   and the chosen plinths and fillers (`room.plinth_solids`,
   `room.filler_solids`); every part tied to its cut-list designation; hinge
   axes off `room.door_hinges`, factored out of `swing_envelopes` unchanged.
3. **F3** the drawing and CAD-grade navigation: orbit about the pressed
   point, pan at its depth, zoom about the point under the cursor (this
   module's own, exact by construction), view cube, named views, perspective
   and orthographic, render on demand.
4. **F4** one selection and one docked editor across Cabinets, Room and 3D;
   the part card with Show in cut list; the item list; the context menu;
   **a click in the plan now selects without isolating** (a change to the 21
   September isolate ruling — see **Isolate**).
5. **F5** fronts open on their hinge axes, clearances red where
   `room.clashes` says so, validation badges, one layer toggle with the plan,
   Snapshot to `output/<job>/<job>_3d_<n>.png`.
6. **F6** moving a cabinet or panel in 3D on move handles, through the same
   `/api/drag` and the same snaps as the plan and the elevation.

**One thing the brief did not know: `room.py`'s world frame is left-handed.**
X right, Y into the room, Z up, and a plan that maps onto SVG with no flip —
that is a left-handed frame, and drawn as it stands in a right-handed renderer
the room came out as its own mirror image, hinge sides included. The 3D view
draws every solid under a root that negates Y (`toRender` / `toRoom` in
`view3d.js` is the one place the two frames meet), so face on to wall A from
inside the room its x runs left to right exactly as the wall elevation draws
it. Not one number the server sends is changed. See **The 3D view**.

### Line / Finish redone, faces in the plan, one set of line weights (23 September 2026)

**Line / Finish redone, faces in the plan, one set of line weights (23
September 2026, brief of that date).** Benchmark unchanged (272 / 59 / 30, 92
pot holes, 18 / 9 / 6, R28,363.50); every `check_*.py` passes; `snapshot.py
--compare` against the tree before moves no panel, issue, summary or total —
only drawings. Exercised in the running app in headless Chromium: both views of
Test.json wall A, the plan with faces, zoomed, and real-mouse drags of a plan
cabinet, a plan panel and elevation panel 8.

1. **Line and Finish.** The 22 September white-and-grey Line view is gone. LINE
   is what the Finish button used to show, unchanged, and is the default;
   FINISH draws the runs on the walls either side as they are really seen from
   this wall. See **Drawings → Finish and Line**. On the Run the toggle is
   greyed out (the two would be identical there) and keeps its choice.
2. **Door and drawer faces in the plan**, per leaf and per drawer in their own
   boards, off `room.front_outlines`. See **Drawings → Faces in the plan**.
3. **Line weights**, ruled by Rudolf with one change: no dashes unless they add
   real value. See **Drawings → Line weights**.

Also: the Boards tab's `.swatch` CSS was resizing every drawing legend's
swatch to 26 px over its own text (`.swatch:not(rect)` now), capitals in a
board name no longer run into the next legend entry, and a thin placed panel's
number is drawn after the neighbours so Finish cannot bury it (it moves with
the drag, `elevTags`).

### Placed panels drag in the plan (22 September 2026)

**Placed panels drag in the plan (22 September 2026, follow-up brief).** Along
their wall and off it, z untouched, through the same `/api/drag` and a new depth
snap, `room.y_snap_points`. See **Dragging a panel in the plan** under **Placing
a panel**. Exercised with a real mouse in headless Chromium on Test.json's end
panel 8 and an upright panel: grabbed on its grab area and not its number, no
jump off-centre, nearest snap on both axes (y 19 lands on 14 "front level with
1", not on the wall), a quick drag, z unchanged, the elevation at the new x
straight after, the reverse, and cabinets dragging exactly as before. Benchmark
and every check unchanged.

### Plan drag, accepting criticals, wall elevations on one rule, Line / Finish view (22 September 2026)

**Plan drag, accepting criticals, wall elevations on one rule, Line / Finish
view (22 September 2026, brief `claude-code-brief` of that date, items 1-5).**
Benchmark unchanged (272 / 59 / 30, 92 pot holes, 18 / 9 / 6, R28,363.50);
every `check_*.py` passes, sixteen of them now; `snapshot.py --compare` against
the tree before this work moves no panel, issue, summary or total on any job —
only Test.json's drawings, which is the point of items 3 and 4.

1. **Plan drag.** The listen-before-await race the brief describes had already
   been fixed that morning (919e73c) and was not the stutter. Measured in a
   headless browser with a real mouse, three faults were: every plan label took
   the pointer, so a press on the MIDDLE of a cabinet — on its number — did
   nothing, and a panel's number beside it left a dead strip over the next
   cabinet (`#plan svg text{pointer-events:none}`); the drag put the cabinet's
   middle under the pointer, so grabbing it off-centre jumped it ~180 mm on the
   first move (it now keeps the grab offset, as the elevation always has); and
   it took the first snap within tolerance, not the nearest (the elevation's
   rule since 21 September). Panels are still not dragged in the plan — the
   existing ruling — and drag in the elevation, checked the same way.
2. **Accepting a site-dependent critical.** See **Accepting a critical** below.
   Tip-up only (above-ceiling too since 29 September 2026).
3. **Every wall drawn by one rule.** See **Per-wall elevations**. The "white box
   labelled side on the return wall" was a MITRE's own open-face side, drawn by
   `_corner_interior` with that label; the label is gone and the side stays in
   its board. Blind corners were already drawing their panel in its own board.
4. **Line / Finish** in the elevation header. See **Drawings**.
5. **"Shelf 968 deep fouls the back at 965" was a MITRE, not a blind corner.**
   Reproduced exactly: a tall mitre with arms 1000 and a mitred shelf cuts that
   shelf as the 968 x 968 blank the top and bottom are, and D3 measures it
   against a 3 mm back the mitre does not have (its back is the melamine wall
   panels; `back` stays "four" in the file). Derived shelves on blind corners —
   base 600, wall 600 and 350, tall 1000 — never trip it, pinned in
   `check_drag.py`. **Left as is — ruled** (below).

Also: `check_edging.py` was failing on `Test.json` cabinet 13 before any of
this — a mitre keeps its support rows and cuts none, exactly as a panel does,
and the check now skips it the same way.

**Ruled on these results the same day:** the classification of criticals is
accepted as proposed — **tip-up is the only acceptable critical**, and every
other one blocks, above-ceiling, ceiling-measured, wall-length and room-closure
included. **Changed 29 September 2026: above-ceiling is acceptable too** (see
**Accepting a critical**); ceiling-measured still blocks. And **`shelf-fouls-back` on a mitre stays as it is**: Rudolf ruled
against skipping it when no back panel is cut. Do not change it.

Rulings recorded with this brief: **blind corners are intended mainly for base
and wall-hung units; tall corners are mitres. External corners** (outside
angles, peninsulas, walls not at 90°) **are awaiting Rudolf's sketch of his own
kitchen — build nothing towards them yet.** **Lifted for the WALLS on 29
September 2026** (walls at any angle — see Status): outside corners and any
angle are in scope for walls; corner units still stand only in a nominal 90
inside corner (ruling 4).

### A blind corner's panel is INSET, selectable, and edged on one robust edge (22 September 2026)

**A blind corner's panel is INSET, selectable, and edged on one robust edge
(22 September 2026, Rudolf's final ruling; brief in
`Claude outputs/blind-corner-inset-brief-2026-09-22.md`).** The door and the
opening did not move — the panel's construction did. It sits inside the carcass
between the corner-end side and the opening, face flush with the front edges, so
the unit reads as one flush front, and it runs between the top and the bottom:
**(H − 2t) × B**. W 1000 / H 2400 / B 500 cuts **2368 × 500**, beside the same
**2397 × 497** door over the same **468** opening. A base unit is the same
figure and it was checked rather than assumed — its front support is the same
16 mm board lying flat with its face flush with the carcass top edge, which is
also the figure the engine already takes as a divider's default height; H 790 →
758. The panel names its own board (`blind_board`, blank = the exterior board,
because the strip beside the door is seen from the room) and its own edging
thickness (`blind_edge_kind`, None = the doors'), and it carries **one** banded
edge: the vertical one facing the opening, the one rubbed when reaching in.
`room.blind_spans` is the one place the layout along the wall is worked out, and
the wall elevation and the Corner Unit plan diagram both read it. See **Corner
units → A blind corner** below, and spec items 25 and 29.

Benchmark unchanged (272 / 59 / 30, 92 pot holes, R28,363.50, 22 cabinets
reproduce), all fifteen `check_*.py` pass, and every job file on disk still
round-trips byte for byte. Exercised in the running app, not only in Python:
the two new controls, the readout, the plan diagram, the wall elevation and the
cut-list line were all driven in a headless browser against
`jobs/Corner Unit Test.json`.

### Corner units made usable (22 September 2026)

**Corner units made usable (22 September 2026, Cowork, after Rudolf reported
the corner unit "doesn't work, nothing is right").** The engine side built
earlier the same day was sound; what failed was everything the operator sees.
Fixed, each checked in a headless browser against `jobs/Corner Unit Test.json`:

- **Corner Unit sits directly under Size.** Size says "Set in Corner Unit below";
  the section it pointed at used to be four sections further down.
- **A scaled plan diagram** in the section, drawn off the engine's outline, with
  each measurement lettered A-D the same as its field, the door face in colour
  and the runs the unit meets drawn dashed. Blind corners get their own.
- **Problems are said under the field that causes them**, in red
  (`api.corner_field_problems`), not as one sentence in Validation. A corner with
  no shape shows a dash in Size and the cabinet table, never the declared figures.
- **Choosing Mitre/Ell with nothing measured** fills cabinet 7's proportions off
  the cabinet's depth (open ends = depth, lengths = depth + 350); choosing
  Mitre or Blind turns doors on.
- **A corner unit is moved into its corner** whenever its type, hand, length
  along the wall or wall changes (`cornerFollowUp`), and Validation warns if one
  is dragged out of it.
- **Drawings**: `render._corner_interior` draws a mitre's door where it really
  is, at its projected width, hatched, labelled with its real width; a blind
  unit's blind panel and door at their cut widths; an ell says it is not
  decided. The Run uses the geometry width and labels the corner type.
- **Two real bugs**: the "sits x-y on wall" check read the declared width (hard
  rule 1); `Overlap.across` did not exist, so any overlap broke the wall
  elevation.

Benchmark unchanged (272 / 59 / 30, 92 pot holes, R28,363.50, 22 cabinets
reproduce) and all fifteen `check_*.py` pass.

### Parts A, B and C — the boards record, one board-slot list, board colour in the drawings (20 September 2026)

**Part A (boards record and edging), Part B (one source for which fields hold
a board) and Part C (board colour in the drawings) are built and checked.**
Against the brief in `Claude outputs/claude-code-brief-boards-colour-panels-3d-2026-09-20.md`:

- **A** — `has_edging`, `edging_kinds` and `colour` are fields on `Board`; the
  Boards form owns them; every edging control and every piece of edging text
  follows them. No edging name is stated anywhere but the Boards record.
- **B** — `Cabinet._board_slots` is the one list of which fields hold a board, and
  the swap, the un-select, the library scan and the validator all read it.
- **C** — every fill in the run, the wall elevations and the plan is the colour of
  the board that part is cut from, through `render.board_look`. Since 22
  September a grained board with a picture is drawn in the PICTURE instead,
  through `render.Fills`, and the colour is the fallback. See **Drawings**
  below. (A later session read a screenshot as "Part C was never built". It was
  built; the screenshot was an isolated cabinet.)

Since then, and not in the brief: support rows carry a per-row **Cut from**
board; a swap moves every panel; the editors refresh themselves; deleting a
project moves its files to `jobs/_deleted/`; grain is shown in the swap step
and on the cut list.

### The checks read frozen fixtures, and only Test.json live (28 September 2026)

**The checks read frozen fixtures, and only `Test.json` live (28 September
2026).** Rudolf deleted every project but Test.json in the app (commit 2673ad8
— the files went to `jobs/_deleted/`, as Delete does), and `check_boards`,
`check_library`, `check_scene` and `check_panels` died while `check_accept`,
`check_attached`, `check_edging`, `check_supports` and `snapshot.py` silently
skipped the jobs they could not find. The same lesson as
`Test_Build_pre_library.json`, learnt a third time: **a check never reads live
workshop data.** `Test_Build.json`, `Test_Panels.json` and `Corner Unit
Test.json` are frozen under `tools/fixtures/` now, taken verbatim from the
tree before the delete, and every check, `snapshot.py` and `ui_check_3d.py`
(which loads them through `adopt`, exactly as Load would, since the app's Load
cannot list them) read them through `tools/fixture_jobs.job_file`. `jobs/`
holds Test.json and the benchmark; `api.FIXTURE_JOBS` names Test.json alone.
Benchmark, every check and the snapshot unchanged.

### Part D — independent panels (20 September 2026)

**Part D (independent panels) is complete — D1 to D9, every one passing, and
exercised in the running app rather than only in Python.** Kind → Panel swaps
the cupboard sections for Panel design and says what stops being cut first; all
three orientations relabel their two extents and give the right geometry; a
board, an edging kind and the banded-edge counts produce the cut-list line the
engine derives, preview and all; Duplicate gives the next free number and copies
everything but the placement; and `jobs/Test_Panels.json` loads, edits and saves
back **byte-identical**. See **Panels** below.

### Part E — placing panels (21 September 2026)

**Part E (placing panels) is complete — E1 to E9, and exercised in the running
app rather than only in Python.** A panel has a place in the room: `Placement.y`,
`room.placed_panels`, the Placements table's Y column, panels drawn in the wall
elevation and the plan, the drag and every snap target it needs — cabinet tops
included, which is what a bulkhead lands on — the fat invisible hit area a 16 mm
panel needs to be grabbable at all, the Panels layer toggle, and the clash
WARNING. See **Placing a panel** below.

**Three things were decided beyond the brief** (21 September 2026, with Rudolf):
the layer toggle is **multi-select** rather than one radio (E3b), a newly-placed
cabinet or panel gets a **default position clear of what is already on that wall**
rather than 0 mm (E8), and the wall elevation and the plan take **scroll-wheel
zoom** (E9).

### Corner units built — mitre and blind generated, ell shape-only (22 September 2026)

**Corner units are built — mitre and blind generated, ell shape-only (22
September 2026).** Not a lettered Part. Ticking "Corner unit" on a template
cabinet used to reshape the plan and change not one line of the cut list: the
box still came out W × D square, and nothing said so. `engine.py` had no corner
branch at all, and the Style dropdown defaulted to blank so `corner_on` was
false anyway — cabinet 7 only ever "worked" because its panels are typed out by
hand. A mitre is now generated from its four measurements, a blind corner from
its carcass and its blind panel, an ell has a shape and a critical saying its
construction is not decided, and every corner unit has a **hand** saying which
end of it stands in the corner. Size is greyed on a corner unit exactly as it is
on a panel. See **Corner units** below, and spec items 21-28.

**Part F (3D) is built — the Status entry at the top, and **The 3D view**.**

### Vertical snap in the wall elevation, and isolate in the plan (21 September 2026)

**A standalone fix, not a lettered Part (21 September 2026): vertical snap in
the wall elevation, and isolate in the plan.** Two things Rudolf hit while
using it. The vertical snap had no twin for a horizontal target it has always
offered — an opening — and reported a standing neighbour's underside as the
floor rather than the plinth top, which is a leg height out and is why
`Test.json`'s own placed panel could not be dragged back to where it sits. And
a cabinet given a wall can land underneath one already there, with nothing to
click on, so it is now reached from the LIST instead. See **Vertical snap** and
**Isolate** below.

### A board's picture is what its parts are drawn in; the top dimension line (22 September 2026)

**A third standalone fix, not a lettered Part (22 September 2026): a board's
PICTURE is what its parts are drawn in, and the top dimension line reads per
cupboard.** A session before this one concluded from a screenshot that doors and
drawer faces "were never built" in the wall elevation. **That was wrong, and the
screenshot was not what it looked like.** Part C was built, and is: doors, drawer
faces and the carcass body have been filled with the real board colour through
`render.board_look` since 20 September, with hinge counts, drawer-face heights
and the door-swing triangle on top. The plainer screenshot was an ISOLATED
cabinet — everything else ghosted at `opacity="0.30"`, which is isolate working,
not a missing feature. **The diagonals in each door are the swing triangle**
(`render._hinge_marks`, its point on the hinge side), the standard elevation
convention, not grain. Grain was drawn, as `_grain_lines` — fine vertical
hairlines at 22 % opacity.

What was genuinely missing is what this stop added. **A board's picture was
carried and never drawn** — `board_look` said so in as many words. Now:
`render.Fills` tiles it as an SVG `<pattern>`, and **a picture wins over the
colour field, on a GRAINED board only** (ruled 22 September 2026). A plain board
keeps its colour even when it carries a picture: a photograph of a flat white
sheet says nothing the colour does not and tiles into noise. **Board pictures are
supplied grain-vertical**, and an upload warns when one is not. **The top
dimension line breaks at every cupboard**, as the bottom one always did. See
**Board pictures in the drawings** and **The two dimension lines** below.

### Board pictures, and out/ renamed output/ (22 September 2026)

**A second standalone fix, not a lettered Part (22 September 2026): board
pictures, and `out/` renamed `output/`.** A board picture had never once
displayed, and the reason was not the path: the server had no static route at
all, so an `<img src>` naming a Windows path resolved against
`http://127.0.0.1:<port>/` and 404'd. There is a `/pictures/<name>` route now,
a picture is chosen with Browse… or dropped on the swatch rather than typed,
and whichever way it arrives the server copies it into `Pictures/` and stores a
path relative to the repo. `Pictures/` is in git. Exercised in the running app,
not only in Python: both swatches decode, a real drop lands, Browse… opens the
native dialog, and an export writes `output/<job>/`. See **Board pictures** and
**Where the exports land** below.

Also done since Part C, and not in the brief:

- **The editor no longer rebuilds its controls on every compute.** Dropdowns
  twitched because every `<select>` was destroyed and remade after each compute,
  and a drawer cabinet sitting untouched on screen computed about three times a
  second for ever (12 computes and 13 drawer-solves per 4 seconds, measured),
  lighting the unsaved-changes marker on a job nobody had edited. The editor is
  still rebuilt from the job every time — it has to be — but the HTML is now
  applied to the DOM that is already there, and a focused control is never
  touched. The cabinet table is painted the same way. See **The UI**.
- **The pre-library checks read a frozen fixture, not a live job.** Three checks
  pinned "a job written before the library still names DECOR" against
  `jobs/Test_Build.json`, and upgrading that job in the Boards tab broke all
  three. They read `tools/fixtures/Test_Build_pre_library.json` now. The one
  half still asked of the live folder, on purpose, is whether `jobs/` is
  readable. See **One source for "which fields hold a board"**.

### The benchmark, the open questions and baseline.json (20–22 September 2026)

**The benchmark held through all of it**, and is what says so: 272 MEL /
59 BROOKHILL / 30 BACK panels, 92 pot holes, 18 / 9 / 6 boards from the nester,
R28,363.50, and every `tools/check_*.py` green — fifteen of them, `regen_check`
and `Check It Still Works.bat` included.

Open questions from the brief that Rudolf has not ruled: **Q1** line endings
and git hygiene (the working tree is CRLF, HEAD is LF; edit without changing a
file's existing endings and review with `--ignore-space-at-eol`), **Q5**
`WHITE_EDGE` (gone since 28 September 2026). **Q2 is ruled: a panel takes code 08 with the role "Panel"**
(20 September 2026) — the CSV carries the designation (`Panel.label`, in the
Customer Number column since 28 September 2026) and never the role, so a new
code would need their sign-off and would say nothing on the order that 08 does
not. **Q3 is ruled: carcass-front edging the
exterior board does not offer is a CRITICAL.** **Q4 is ruled: drawer-face grain runs vertical, up
the face height, exactly as the cut list has it. Never question it.** The
proposed hard rules H5 and H6 are not in this file yet because they are his to
accept; Part C was built as though they hold.

**Dragging a new cabinet straight from a list onto the plan** was left unbuilt
here (awaiting a ruling) — and was then ruled IN by the UI restructure brief (28
September 2026), for the Plan, the Elevation and the 3D tab. See **Placing from
the unplaced list**.

Open and not a fault — **`baseline.json` is stale, and deliberately not
regenerated** (22 September 2026). It is per-machine and gitignored, and
`snapshot.py --compare baseline.json` reports Test differing: `jobs/Test.json`
has genuinely changed since the baseline was taken — a ninth cabinet, and two
drawer faces moved from 192/195 share to 187/200 fixed — so the new gaps, total
and drawings are correct, not a regression. Proved rather than assumed: the code
AS IT WAS, before the picture work, produces the same diff against the same
baseline from the same `Test.json`. Regenerate it when Test.json settles; a
stale baseline that is known to be stale is safer than one refreshed over a
difference nobody looked at.
