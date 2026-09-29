# Brief: the Drawers section redone (29 September 2026)

Agreed with Rudolf in Cowork after reviewing the section on Test.json cabinet
4. The section works but is cluttered and its words explain the code, not the
job. This brief redoes its layout and wording, adds four small things ruled
with it, and touches nothing about how a drawer is cut except where a ruling
below says so. Read CLAUDE.md's drawer entries (28 and 29 September) first;
"faces lead, boxes follow" and every drawer check stand.

Benchmark unchanged (272 / 59 / 30, 92 pot holes, 18 / 9 / 6, R28,363.50).
Every `check_*.py` green through `tools/check_all.py`. `snapshot.py --compare`
against the tree before this work: the October job identical; Test.json moves
ONLY through Part 6 (the runner re-point), and the report lists each line that
moved. Every job on disk round-trips byte for byte until it is saved.

Run **Local**: the 3D and the editor need to be seen. Build in the order below,
one commit per part, `check_all` green at each.

## Rulings recorded here (Rudolf, 29 September 2026)

R1. **Box edging has a thickness choice as well as a colour**: PVC / 1mm / 2mm,
    from what the chosen board offers, the same two controls as Doors. This
    REVERSES the 29 September "always PVC" ruling, which was Claude's proposal
    accepted for that build only. Default: PVC in the exterior board's colour,
    so nothing quoted moves.
R2. **Box height can be Auto**: the tallest box that fits its face at its
    offset (`drawer_layout`'s `max_box`, the `≤` figure). Auto follows a face
    when Share or a preset moves it. A typed height is kept as typed.
R3. **The runner is two members per side**: an outer channel fixed to the
    carcass and an inner member fixed to the drawer side, nested when closed,
    the inner travelling with the box. Their sizes come from the catalogue
    record, never from Standard.
R4. **A runner record cannot be saved without its dimensions**: name, at
    least one length, height, side clearance, rail thickness, lift, setback,
    inner member height and inner member thickness. Today lift and setback
    silently default; that stops.
R5. Hinges and handles are NOT in this brief. They come to the catalogue
    soon, in their own brief.
R6. No mockup round: build to the layout below; Rudolf reviews it in the app.

## Part 1: the model

- `Drawer.box_edge_kind: Optional[str]` (None = PVC). Read through a new
  `Cabinet.box_edge_kind_of(d)`. Written only when set (`store`).
- `Drawer.box_height` may be **None = Auto**. The engine cuts Auto at
  `drawer_layout`'s `max_box` for that drawer. Every saved job has a typed
  figure and keeps it. The `drawer-box-face` check cannot fire on an Auto box
  by construction; `drawer-runner-height` still can (a face too short for the
  runner) and its message says so. Written as `null` only when Auto.
- **Cabinet-level defaults for the section**, each `None` = the existing
  fallback, written only when set, all in `_board_slots` where they name a
  board: `drawer_carcass_board` and `drawer_face_board` (exist; offered again),
  `drawer_box_edge_board` + `drawer_box_edge_kind` (new), `drawer_base`
  (new, `'board'` | `'melamine'`; `Drawer.base` becomes Optional, None =
  the cabinet's, and every saved job's typed `base` stays as typed).
  Resolution per drawer: its own value → the cabinet default → today's
  fallback (box: carcass; face: exterior; box edge: exterior + PVC; base:
  board). Pinned in `check_runners.py`.
- `Runner` gains `inner_height` and `inner_thickness` (mm). `SEED` and
  `LEGACY` get values marked **estimated** in a comment: inner height =
  height − 8, inner thickness = 6, until Rudolf reads them off Gelmar drawing
  04227 and edits the record. `api.runner_save` refuses a record missing any
  R4 field (`> 0`), naming the field; the Runners form marks them required.
  `hardware.json` records missing the two new fields load with the SEED
  estimates and the Runners tab shows "estimated: confirm" beside them.

## Part 2: the section layout

The settings column stays 560 px. Four blocks in this order, each a
sub-heading inside the Drawers tint, one short help line under each control
(the copy is in Part 5, use it verbatim):

**A. Setup**
- Drawer type (Outer | Inner), as now.
- **Runner** (moved from the bottom to here): the dropdown, Catalogue…,
  and ONE status line: `Gelmar 45 · 500 long · box 500 × 291 · pulls out 500`.
  On a legacy cabinet the line reads `Legacy lengths (350 / 450 / 500), as
  quoted` and the help line says what to do (Part 5). No paragraph.
- Bottom: `3 mm grooved sheet` | `16 mm housed melamine` (the stored values
  unchanged).
- Box board · Face board (two dropdowns on one row, full width shared).
- Box edging: thickness + colour (one row). Face edging: thickness + colour
  (one row). Same controls and labels as Doors (`edging_label`). The
  resolved tape name is NOT printed beside them; it shows in the row's
  tooltip and on the cut list, as everywhere else.

**B. The stack** — one table, five columns, room to breathe:
`# · Face height · Box height · Offset · (remove)`.
- **Face height**: the mm figure. A **lock** toggle in the cell: locked =
  Fixed (typed), unlocked = Share, the cell then shows the engine's mm
  greyed with the share weight in a small field beside it (default 1). Same
  `mode` / `share` / `face_height` stored; no Mode, Value or MM columns.
- **Box height**: `Auto (≤171)` when Auto, or the typed figure with `≤171`
  beside it, red when over. A small Auto button restores Auto.
- **Offset**: as now, blank = 21, tooltip says what it is.
- A row marked as differing (C) shows a dot in its # cell.
- Under the table: the readout `opening 777 · faces + gaps 777 · left 0`
  and the buttons **Equal · Graduated · + Drawer**.
- Inner drawers: the same table with **Height** (z) in place of Offset, as
  now.

**C. Per-drawer overrides**: a `differs…` link at the right of each row
opens a sub-row under it with that drawer's Box board, Face board, Bottom,
Box edging (thickness + colour), Face board's edging is the section's (a
face's edging stays per section; ruled so it matches Doors). Blank = the
section's. A row with nothing set shows no sub-row; `differs…` becomes
`same as section` to clear all four. Existing jobs whose drawers carry per-
drawer boards show those sub-rows open.

**D.** Nothing else in the section. The three paragraphs of prose go.

Every current function stays (hard rule 9): Fixed/Share, presets, add /
remove, per-drawer box and face board, per-drawer box edging colour, offset,
inner drawers with typed heights, the runner dropdown and swap warning, the
divider drag in the elevation. Add each move to CLAUDE.md's "where it lives
now" table.

## Part 3: the runner in 3D

`room.drawer_parts` emits, per side, `runner-outer` (as the block is today:
rail thickness × height × length, fixed to the carcass) and `runner-inner`
(inner thickness × inner height × length, centred vertically in the outer,
against the box side, fixed to the box). On Fronts open the inner member
travels with the box by `travel`; the outer stays. Both under the Runners
toggle, both "hardware: a runner is bought, not cut", `PAPER.runner` for the
outer and a slightly lighter tone for the inner so the two read apart.
`check_scene.py`'s "one runner part allowed no line" becomes "runner parts".
`ui_check_drawers.py --stage 3d` measures the inner member moving 500 and the
outer not.

## Part 4: box height Auto in the engine and the checks

`engine` cuts an Auto box at `max_box`; `drawers.split_pair` and the presets
leave Auto alone (it follows). `check_runners.py`: Auto equals `max_box`,
follows a face change, a typed box is untouched, the file round trip
(`null` only when Auto), `drawer-box-face` silent on Auto.

## Part 5: the wording (use verbatim)

Section help lines, one under each control:
- Drawer type: *Outer: the faces show on the front. Inner: the drawers sit
  behind a door and each face is the size of its box.*
- Runner: *Sets the box length and width, how far it pulls out and where it
  sits. All figures come from the catalogue record.*
- Runner, legacy cabinet: *Quoted on the old lengths and cut exactly as
  quoted. Pick a catalogue runner to update it; the drawer lines that change
  are listed before anything moves.*
- Bottom: *3 mm sheet grooved into all four sides (the backing board), or
  16 mm melamine housed between them.*
- Box board / Face board: *Every drawer in this cabinet, unless its row says
  it differs.*
- Box edging: *The top edge of the box sides and fronts.*
- Face edging: *All four edges of every face.*
- Stack: *Faces are set out from the bottom: 2 mm between faces, 3 mm under
  the top. Type a height, or unlock a row to let the app share out what is
  left. Box: Auto is the tallest that fits in its face. Offset: the box
  bottom above the face bottom; 21 is the bottom panel plus the runner's
  lift, and the bottom drawer cannot go lower.*
- Tooltips: Offset *"Box bottom above its face's bottom, mm"*; ≤ *"Tallest
  box that fits this face at this offset"*; lock *"Locked: height as typed.
  Unlocked: shared out of what the fixed rows leave"*.
- Outline (Part 7): *The cabinet's shape in plan, for a hand-built unit
  that is not a rectangle. x along the wall, y out from it, in mm. Leave
  blank for the rectangle its panels make.*

## Part 6: Test.json onto Gelmar

Re-point every drawer cabinet in `jobs/Test.json` to `GELMAR45` (through the
same path as **Use for all drawers**), so the legacy message is gone from the
working file. Report the drawer lines that move (a depth now taking 400 or
550). Fixtures under `tools/fixtures/` are NOT touched; the checks that pin
legacy behaviour keep reading them.

## Part 7: Outline

Rename the field **Plan shape**, show it only on a `template == "none"`
cabinet or one that already carries a footprint, keep the engine's readout
line, use the Part 5 help line. Nothing about what it does changes.

## Part 8: zoom speed

One factor per view: `view3d.js` wheel zoom, and the plan / elevation
Ctrl+wheel and pinch in `index.html`. Roughly double the step per wheel
notch. A trackpad pinch arrives as many small ctrlKey wheel events, so give
the pinch path its own factor and check both on the laptop. Report the two
figures chosen.

## Checks

`check_runners.py` for Parts 1, 4 and 6 (a legacy fixture cabinet still cuts
exactly as before); `check_single_source.py` picks up the new board slots by
reflection; `check_scene.py` for Part 3; `check_export.py` unchanged;
`ui_check_drawers.py` new stages: `layout` (the four blocks, the five
columns, the differs sub-row), `lock` (unlock a row, the mm follows), `auto`
(Auto follows a face change), `3d` (the inner member slides). Screenshots
into `output/_checks/ui_check_drawers/`.

## Report and commit

Update CLAUDE.md: Status, the drawer entries where a ruling here changes
them (R1 replaces the 29 September "always PVC"), the "where it lives now"
table, Layout. Give Rudolf the commit message to paste.
