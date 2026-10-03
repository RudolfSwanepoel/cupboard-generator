# Brief — Room touch-ups round 2, and Undo

3 October 2026. From Cowork, ruled by Rudolf after testing the first touch-ups
(`room-layout-touchups-brief-2026-10-03.md`). Layout, the plan's labels, and
an Undo in the browser. Nothing in `cabinetgen/` that cuts, nests or costs
changes; `/api/compute` unchanged; the benchmark must not move. One commit
per part. Run BEFORE the Import project brief.

## 1. Give the plan the screen

At 1360 × 900 the plan is about 450 px wide between Placements and the dock.
- **Placements collapses** to a slim strip on the left (the dock's own
  pattern: a chevron, the strip shows "Placements" vertically), remembered
  per viewer in `localStorage` behind `try/catch`. Default: collapsed.
- **The Room card is compact and always visible** (ruled: "a lot smaller,
  but must stay visible"). On the Room tab, with no cabinet or wall
  selected, the dock is ~360 px wide, not 560: Name, Ceiling (mm) and
  Offset depth (mm) on one row of short fields; the closed/open pill and
  the counts on one line; Draw walls · Renumber · Remove room as small
  buttons; the walls table compact (Wall · Length · Corner · Height · Flip ·
  ×, the Op. / Obs. counts folded into the row's tooltip); the help line
  behind a "?". It does not collapse on its own. When a cabinet is selected
  the dock widens to the editor's width as now, and returns to compact when
  the selection clears. The Wall card uses the compact width too.
- Screenshots at 1360 × 900 and 1920 × 1080, before and after.

## 2. Wall length labels: always outside, and readable over anything

- **Every wall's length label sits OUTSIDE the room**, beside the wall on its
  back side (the thickness band's side), turned to read along the wall —
  vertical walls included (Rudolf: "outside, up and down"). The collision
  step from the last round stays (a clash moves it further out on a leader).
- **The exported plan makes room for them, deliberately.** The plan SVG's
  viewBox is computed from the walls, the footprints AND the label boxes,
  plus a fixed margin (`render.PLAN_LABEL_MARGIN`, in mm), so a label is
  never past the edge — on screen and in `<job>_plan.svg`. The drawing
  scales down by the few percent that costs; nothing is clipped. Check:
  every exported plan of every fixture room has every label's box inside
  the viewBox.
- **A label over something gets a quiet backing.** Where a length label
  overlaps a cabinet, a panel, a face, another wall or a gap mark, it is
  drawn on a small white rounded box (opacity ~0.85, no border, 2 px
  padding) so it reads; where it overlaps nothing it has no box. The box
  takes no pointer events beyond the label's own (the label stays the
  click-to-edit field).
- `ui_check_walls.py --stage labels` extended: on Test.json's room and the
  nook room, every label is outside its wall's room side, none overlap, each
  over a cabinet carries the box, and the exported plan's viewBox holds them
  all.

## 3. Undo and Redo

A job-level undo in the browser.
- **Undo · Redo** buttons in the top bar beside Save, and **Ctrl+Z / Ctrl+Y**
  (Ctrl+Shift+Z too) — except while focus is in a text field, where the
  field's own undo applies.
- **What is undone:** any change to the job on screen — walls (typed,
  dragged, drawn, nook, split, flip, renumber, delete), placements (table,
  drag, drop from the unplaced list, attach / detach), cabinets and panels
  (every editor field, add, duplicate, delete), gaps, plinths, acceptances,
  board and runner selection in the project. One step per committed edit:
  a drop, a field's `change`, a button — never per keystroke or per pointer
  move.
- **How:** a stack of job snapshots (`structuredClone(S.job)`) pushed just
  before each committed edit, depth 50, in one place (`pushUndo()` called
  from the existing commit points: `markDirty` is the natural hook — audit
  that every edit path reaches it). Undo restores the snapshot and runs the
  ordinary compute; the selection is kept if the item still exists. A new
  edit clears Redo.
- **What is NOT undone, and says so in the button's tooltip:** Save, Load,
  New, Delete project, Export, snapshots, and edits to the shared LIBRARIES
  (Catalogue → Boards / Runners, pictures) — those write files straight
  away. Load and New clear the history. Undo marks the job unsaved like any
  edit; undoing back to the saved state clears the unsaved marker.
- Check: `ui_check_undo.py` (new, Playwright): drag a cabinet, type a wall
  length, delete a cabinet, change a drawer face — undo each in turn back to
  the loaded job (compare the job JSON), redo them all forward, then a new
  edit clears Redo; Ctrl+Z in a text field does not undo the job.

## Checks

`check_all` green; benchmark 272 / 59 / 30, 92 pot holes, 18 / 9 / 6,
R28,363.50 — **quote it in the report**; `snapshot.py --compare`: panels,
issues, totals identical (only the plan SVG moves, by its labels and
margin). All Playwright scripts re-run.

## Docs

CLAUDE.md Status entry; where-it-lives-now rows (Placements collapsible,
compact Room card, labels outside, Undo / Redo).

## Report back

The benchmark line, the screenshots' names, and any edit path that did not
reach `pushUndo()` and how it was fixed.
