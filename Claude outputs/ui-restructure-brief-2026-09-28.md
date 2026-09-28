# UI restructure — build brief (28 Sept 2026)

Status: AGREED with Rudolf (27–28 Sept 2026). Not built. Supersedes nothing; builds on the
shelves-supports (27 Sept) and attached-panels (28 Sept) specs, both built.

OVERRIDING RULE: **absolutely no loss of any current function.** Every feature that exists
today must exist after, in its new place. Hard rules 1–8 in CLAUDE.md all apply.

Two sessions, in order. Do NOT mix them.

---------------------------------------------------------------------------------------
## SESSION 1 — Structure

### 1. Tab order
**Boards · Cabinets · Room · 3D view · Cut list · Nesting · Validation.**
Every internal `data-tab` jump (e.g. "go to Boards", "go to Validation", "go to Cut list")
keeps working. A new job still starts on Boards (board selection drives everything).

### 2. Room tab — two sub-tabs: Plan | Elevation
- **Plan:** today's plan, unchanged (layer toggles, isolate, drag, snap, zoom, dock editor,
  walls/room editor, Placements table).
- **Elevation:** today's Wall views moved from Cabinets, unchanged: wall picker (Wall A, B…),
  Line/Finish, zoom (buttons + Ctrl-scroll/pinch), drag handles (track, dividers, doors),
  vertical wall snap, click-to-select opening the one editor, board/tape legend, per-cupboard
  dimension lines, ceiling/plinth lines, attached panels travelling with their cabinet.
- No room defined: Elevation shows a prompt to add a room. No Run fallback.
- The ONE editor keeps being moved (never copied) into whichever dock is showing.

### 3. Run view — removed
- `render.elevation_svg` leaves the UI.
- **Export:** stop writing `<job>_elevation.svg`. Write **one SVG per wall**, with the walls
  **selectable at export** (a tick list, all ticked by default), plus the plan as today.
- Re-point, do not blindly delete, the tests that pin Run: check_elevation.py
  ("wall_elevation_svg(no room) == elevation_svg"), check_panels.py, check_colour.py,
  tools/snapshot.py. If `elevation_svg` stays as an internal helper, say so in CLAUDE.md.

### 4. Cabinets tab
- **Right:** the configuration editor, unchanged, with its Save (refresh-only; live
  updating stays; forces a complete refresh of every view the cabinet appears in).
- **Bottom left:** the cabinet list, unchanged in function.
- **Top left (was the Elevation card):** **3D of the single selected cabinet, alone** —
  same engine (`app/view3d.js`) and controls as the 3D tab: orbit, shaded/edges/x-ray,
  fronts open, labels, part pick, view cube, help card. Shelves, supports and attached
  panels drawn. No walls, no neighbours.
  - Selecting a cabinet anywhere (list, Plan, Elevation, 3D tab) sets what it shows.
  - Picking a part jumps the editor to that section (as the 3D tab does now).
  - A standalone panel, when selected, shows alone.
  - Nothing selected: the first cabinet, or an empty-state prompt if the job has none.
  - Any edit anywhere shows here at once (it is the live model).
- **Attached-panel drag (attached-panels spec B4, deferred until now):** in this view, drag an
  attached panel with snap to the carcass faces and edges; it writes `at_x/at_y/at_z` through
  the server (the browser works out no offset). Typed offsets remain the one place the value is
  entered (hard rule 8) — the drag writes to those same fields.
- NOT this round: the per-cabinet exploded view.

### 5. Drag-and-drop placement (reverses the 21 Sept "not needed")
- Room tab (Plan and Elevation) and the 3D tab get a slim list of **unplaced** cabinets and
  standalone panels (attached panels never appear — they travel with their cabinet).
- Drag one onto a wall to place it. Existing placement, snap, collision, clash and
  clear-of-neighbours rules apply unchanged; drop lands where released, snapped.

### Session 1 verification
- Benchmark exact (272/59/30, 92 pot holes, 18/9/6, R28,363.50); snapshot.py --compare
  identical on every job; all check_*.py green.
- Playwright, headless, with screenshots: each tab in the new order; Room → Plan and Room →
  Elevation doing every item listed in §2 (wall switch, Line/Finish, zoom both ways, drag a
  cabinet, drag a divider, click-select opens editor); Cabinets 3D for a base, a tall, a blind
  corner, a mitre and a standalone panel; select-from-Plan updates Cabinets 3D; editor Save;
  attached-panel drag in Cabinets 3D; drag an unplaced cabinet onto a wall in Plan, Elevation
  and 3D; export with two of three walls ticked writes exactly those two SVGs.
- Write a checklist in CLAUDE.md of every function that moved, and where it lives now.

---------------------------------------------------------------------------------------
## SESSION 2 — Fresh look (first round)

Styling only — no layout or behaviour change beyond Session 1. Rudolf asked for it built
directly this time (mockups later).
- Goal: clean, fresh, a well-rounded product. Tab bar, cards, buttons, inputs, tables,
  spacing, typography, the summary strip, toasts, the dock strip, the 3D toolbar.
- Keep the existing CSS custom properties as the single source of colours; add to them,
  don't scatter literals. Board colours and pictures in drawings are data, never restyled.
- Keep criticals/warnings unmistakable (colour AND icon/text, not colour alone).
- Must still work at the pywebview window's usual size and when narrowed.

### Session 2 verification
- Same benchmark and checks. Before/after screenshots of every tab and sub-tab.
- Re-run Session 1's Playwright scripts unchanged: all pass (proves nothing functional moved).
