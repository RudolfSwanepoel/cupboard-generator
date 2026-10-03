# Brief — Room redo, Phase 2 of 4: drawing and editing walls on the plan

3 October 2026. From Cowork, agreed with Rudolf the same day. Builds on Phase 1
(`Claude outputs/room-redo-phase1-brief-2026-10-02.md`, commits db26c99,
dbd8d1b, e0d1bf5): walls are positioned segments, the chain is derived, the
Room tab is toolbar · plan · dock. **Build nothing from Phase 3 (openings) or
Phase 4 (free cabinets).**

## Why

Phase 1 fixed the model; the plan still edits like a form. Rudolf wants to
shape a room on the plan itself: grab a corner or a wall and pull, have it
snap square and line up with the rest of the room, click a length and type
the measured figure. And the loop opening when a figure is typed must be
said the same way everywhere it is shown.

## Rulings (3 Oct 2026) — build to these, don't reopen them (10 and 11 added the same day after Rudolf tested Phase 1)

1. **A typed length or angle on a closed room leaves the loop OPEN by the
   miss** (as Phase 1 built it). It is the closure check — a measuring
   mistake must not be absorbed into a wall. It is said as **"Loop opens by
   n mm at C→A — type the other walls or drag a corner"**, and it closes
   again on its own when the miss falls within `join_tolerance`.
2. **Open / closed has ONE source and every display follows it.** Before
   building, list every place the open/closed state is shown or used in the
   UI and the engine (the Room card pill at index.html ~5920, the toast at
   ~6985, the Walls table's last corner dash, the plan's floor tint vs face
   band, the 3D floor, the elevation's neighbours, `_room_info.closed`,
   Gaps, Plinth, anything else `grep` finds). Each reads `_room_info.closed`
   off the same compute; nothing in the browser decides it. Put the list in
   the report and pin it in `ui_check_walls.py` (`--stage closure`): type a
   length on Test.json's room, every display says open with the same miss;
   type it back, every display says closed.
3. **Dragging edits walls directly, in Select mode.**
   - **Drag a corner** (a joined end, or a free end): that point moves; every
     wall ending there follows. A small round handle shows on hover.
   - **Drag a wall** (its body): it moves parallel to itself, perpendicular
     to its length; the walls joined at its ends stretch (they keep their
     other end; their direction changes only if needed to stay joined — a
     90° neighbour stays 90° when the move is perpendicular).
   - **Placements on a moved wall** keep their x along it (clamped to the new
     length; an item that no longer fits is reported, never moved off). The
     wall's openings and obstructions likewise.
   - Esc during a drag restores. One undo-able compute per drop.
4. **Snaps while dragging AND while drawing**, in this priority, nearest
   within `Standard.snap_tolerance` (screen-scaled as the other drags are):
   1. an existing corner or wall end (join);
   2. a point on an existing wall (Draw only — splits it, ruling 6);
   3. **alignment**: the dragged point's X or Y equal to any other corner's
      X or Y in the room (wall directions in room frame; rooms whose walls
      are not on the axes align along each wall's own direction too) — a
      thin guide line is drawn from the matching corner to the point while
      it holds. This is what makes a return wall land in line with the
      opposite wall;
   4. **angle**: the wall being drawn or stretched turns to 90°, then 45°,
      then the `draw_angle_step` (15°) — relative to the wall it meets, and
      absolute (plan axes); 90 and 180 to the neighbour win ties;
   5. length to `draw_length_step` (10 mm).
   Holding **Shift** turns every snap off. The snap that applied is named
   beside the cursor ("in line with C", "90° to B", "on corner D→E").
   Snap candidates come from the server (`/api/room-snaps`, one call on the
   press, as `/api/drag` does); the browser only picks the nearest.
5. **Length labels on the plan are editable in place.** Each wall's length
   label is a text box on the plan (styled as a label until hovered). Click,
   type, Enter → `/api/wall-set` exactly as the Wall card does; Esc cancels;
   Tab moves to the next wall in walk order. The Wall card and the Room
   card's table stay; all three are the same field. Units shown ("3000 mm").
6. **Drawing (the Draw walls tool), finished.**
   - Starts from an existing corner or a point on an existing wall when
     clicked there; a point on a wall **splits** it into two walls at that
     point (the first keeps its letter, the second takes the next free
     letter; placements, openings, obstructions, gaps and plinth records go
     to whichever part holds them by x; an item spanning the split stays on
     the first and is reported). That is how a T-wall is made.
   - **Typing a length while drawing**: a digit opens a length box at the
     cursor; the direction freezes at that moment; Enter commits the wall at
     that length; Tab moves to an angle box (relative to the previous wall);
     Backspace in an empty box removes the last corner.
   - Click the start (or any existing corner) to end on it; double-click or
     Enter to end free; Esc out.
7. **Wall nook tool** (toolbar, beside Draw walls): click a wall, type width,
   depth and distance from the wall's start (mm); the wall is split and the
   recess (back, two returns at 270° / 90°) inserted, new letters, the room
   staying closed if it was. Depth negative = a projection (a nib) instead.
   One server call (`/api/wall-nook`).
8. **Add back face** on the Wall card: a new wall on the same line, opposite
   direction, offset by the wall's thickness, joined to nothing — a
   partition taking cupboards on both sides.
9. **Flip face on a wall of a CLOSED room** asks "Flip the whole room? (the
   room side goes to the outside of every wall)" with Flip room / Flip just
   B / Cancel. Flip room flips every wall in the chain.

10. **Draw walls happens ON THE PLAN, not on a canvas of its own.** Rudolf's
    original ask: "it must be the same window — just a select to draw or
    not." As Phase 1 left it, Draw walls still swaps the plan for a separate
    grid canvas showing the room as a dashed outline, and hides the
    cabinets. Retire that canvas (`drawPaint`'s own SVG, `#drawsvg`): Draw
    walls is a MODE of the plan itself — same drawing, same zoom and scroll,
    walls solid, cabinets and the room tint shown (cabinets ghosted at the
    usual 0.30 while drawing), the grid laid over the plan only while the
    mode is on, the new walls drawn live on top. Leaving the mode (Select,
    Esc) changes nothing on screen but the cursor and the grid. The same
    holds for the Nook tool. `ui_check_walls.py --stage draw` asserts there
    is one plan SVG before, during and after drawing.
11. **The Room tab's cards fit.** As Phase 1 left it, the plan sits small at
    the left of a wide card with empty space beside it, the Gaps table
    scrolls sideways (Suggestion and Treatment cut off), and the Plinth
    card's note runs the full width under a short table. Fix the layout,
    styling and markup only:
    - the plan **fits its card** on load and on Fit (width and height), the
      zoom percentage measured from there;
    - **Gaps** takes the full width under the plan, every column visible at
      1360 px without a horizontal scrollbar (the suggestion text wraps;
      Treatment keeps its width);
    - **Plinth** and **Placements** sit side by side under Gaps, each table
      at its natural width, the explanatory notes collapsed behind a "?"
      beside the card title (the same one-line help pattern as the Drawers
      section);
    - the unplaced-items strip stays above the plan, wrapping;
    - nothing removed (hard rule 9); screenshots at 1360 × 900 and at full
      HD before and after into `output/_checks/ui_check_walls/`.

## API

`/api/room-snaps` (candidates for a drag or a draw: corners, wall segments,
alignment lines, angle references — with a reason each), `/api/corner-move`
(a point, its new position → every joined end moves), `/api/wall-move`
(perpendicular offset), `/api/wall-split` (wall, x), `/api/wall-nook`,
`/api/wall-backface`, `/api/room-flip-all`. `/api/room-draw` gains the
start-on-wall split. All whole mm; everything decided in `room.py`; the
browser works out no geometry beyond projecting the pointer and choosing the
nearest candidate.

## Checks

- `check_room.py`: `corner_move()` (joined ends move together, placements
  keep x and are clamped/reported), `wall_move()` (neighbours stretch, a 90°
  stays 90), `split()` (letters, records follow by x, spanning item
  reported), `nook()` (closed room stays closed, a nib), `backface()`,
  `snaps()` (alignment candidates for an L and a U; angle candidates; the
  priority order), `closure_text()` (the one miss and its corner),
  `flip_all()` twice is identity.
- `ui_check_walls.py`: new stages `closure` (ruling 2), `cornerdrag`,
  `walldrag`, `align` (drag a return wall's end until "in line with …" and
  it lands exactly on the other corner's X), `angle` (a drag near 90 lands on
  90; Shift does not), `label` (click a plan length, type, Enter, the wall
  and the Wall card both change), `typedraw`, `split` (a T-wall), `nook`,
  `flipall`. Screenshots into `output/_checks/ui_check_walls/`.
- `check_all` green; benchmark 272 / 59 / 30, 92 pot holes, 18 / 9 / 6,
  R28,363.50 — quote it; `snapshot.py --compare` against the tree before:
  every panel, issue and total unchanged on every job.

## Docs

CLAUDE.md Status entry and the where-it-lives-now rows (plan labels editable;
corner and wall drag; Nook; Add back face; Flip room). `docs/ROOM-LAYOUT-SPEC.md`:
**Ruled — 3 Oct 2026** with the eleven rulings.

## Report back

The open/closed display list (ruling 2) and what each now reads; anything a
drag does to cabinets that the brief did not foresee; and the benchmark line.
