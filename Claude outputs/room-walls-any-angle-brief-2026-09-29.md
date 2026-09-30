# Brief — walls at any angle, either direction, and drawing walls with the mouse

29 September 2026. From Cowork, ruled by Rudolf the same day.

## Why

Liam_Room shows the limit: every corner turns the same way (90° inside,
clockwise), so a wall can't turn back out, and a negative length was the only
way Rudolf could find to "turn" a wall. It doesn't turn anything; it runs the
wall backwards, and C and D raise criticals.

## What this supersedes

The 22 September ruling that outside corners wait for Rudolf's sketch is
**lifted**. Outside corners and any other angle are now in scope for the
**walls**. Corner units are not (see Part 3).

## Rulings (29 Sept) — build to these, don't reopen them

1. **Corner entry = nominal angle + the existing offsets.** Each corner gets a
   nominal interior angle. The measured offsets (`offset_start`/`offset_end`,
   `offset_depth`) stay exactly as they are, as the fine correction on top of
   the nominal angle. Site measuring doesn't change. The open item on the
   `offset_depth` default and sign convention stays open; don't touch it.
2. **Draw walls with the mouse on Room → Plan.** Yes, this round.
3. **Reference lines, panelling outlines, markup:** later, not this round.
   Build nothing towards them.
4. **Corner units (mitre, blind) only at a nominal 90° inside corner.** Placed
   in any other corner, they raise a critical: "Corner unit at a
   {angle}° corner: construction not ruled." Their corner shadow is not
   applied there.
5. **At any corner the run ends.** Each wall's run stops at its corners, inside
   or outside. The app builds nothing special at an outside corner. Overlaps and
   gaps come from real footprints (hard rule 1), as now.

## Part 1 — the model

- Interior angle, measured inside the room between the two wall faces:
  - 90 = today's inside corner
  - 270 = outside corner (the wall turns back towards the room: chimney breast,
    step, nib)
  - 135 / 225 = a bay or splayed corner, in and out
  - 180 = walls in line (allowed; harmless)
  - Any value strictly between 0 and 360. Decimals allowed.
- Store it per corner, on the wall *before* the corner (e.g. `corner_end`,
  your naming). Default 90. **Write it to the job file only when it isn't 90**,
  so every existing job round-trips byte for byte, as `Placement.y` does.
- `wall_frames` turns by (180° − interior angle − measured deviation) instead of
  (90° − deviation). At 90 on every corner, every coordinate must come out
  **identical** to today's. Prove it in a check.
- Everything downstream already goes through `wall_frames` / `to_world`: plan,
  elevations, 3D (floor/ceiling via `triangulate`), SVG export, DXF,
  SolidWorks table. Keep it that way: no new trig outside room.py.
- Closed room: `closure_error` must still work and be 0 for a correctly entered
  shape (a hexagon at 120° ×6, an L room with one 270°, a room with a 135° bay).
- New critical: walls cross each other in plan (the room outline
  self-intersects). Name the two walls.
- A negative wall length: reject it at the input with a short note ("to turn
  the other way, set the corner angle to 270"), rather than only raising the
  critical later. The existing critical stays for old files.

## Part 2 — the Walls card

- Add a **Corner** column: the corner after each wall, labelled like `B→C`.
  Quick picks: 90 inside · 270 outside · 135 · 225 · 180 · custom (number).
- Closed room: the last wall's corner is back to the first wall. Open run: the
  last wall has no end corner (show a dash).
- "+ Wall before / after" still add walls at 90°. The angle is then changed in
  the Corner column.
- Plan redraws live as angles change, like lengths do now.

## Part 3 — what has to learn about angles (audit every one)

Search for anything that assumes the next wall is 90° away. At least:

- `corner_shadow`: return None unless the nominal corner is 90° inside (ruling 4).
- The corner-unit critical in ruling 4.
- `plinth_butt_wall`: butt applies at inside corners (interior < 180°) of any
  angle. At 180° and outside corners there is no butt: each plinth ends at the
  corner.
- Gaps: a run still ends at the corner; gap sizes along each wall unchanged. At
  an inside corner that isn't 90°, adjacent cabinets can clash near the corner;
  the overlap check (real footprints) reports it. Don't auto-resolve.
- Wall snap and drag-onto-wall in Room → Plan and 3D must work on walls at any
  angle.
- Elevations: per wall, so unchanged. Check any return-wall stub drawn at a
  corner uses the real angle, or is omitted where it can't be drawn truthfully.
- 3D: walls, floor, ceiling, tiles/plaster and the Grid toggle on a
  non-rectangular room.
- Ceiling clash, door swing, tip-up: already geometry-based; confirm with an
  angled-room check.

## Part 4 — drawing walls with the mouse (Room → Plan)

- A **Draw walls** button on Plan. In draw mode:
  - Click to start. Each click sets a corner. A rubber-band line shows live
    length (mm) and corner angle.
  - Direction snaps to **15° steps**; hold **Shift** for a free angle. Length
    snaps to 10 mm.
  - Click on the start point to close the room (closed = yes). Double-click or
    Enter finishes an open run. Esc cancels the whole drawing; Backspace removes
    the last corner.
- Walls are named A, B, C… in drawing order. Their lengths and corner angles go
  into the Walls card exactly as if typed. The drawn direction decides the
  winding. If drawn anticlockwise, re-order so the model stays clockwise, and
  say nothing to the user about it.
- **Drawn lengths are a sketch, not a measurement.** Each drawn wall is marked
  "drawn" in the Walls card until its length is typed or ticked as measured.
  Any drawn wall still unconfirmed raises a critical ("wall C: drawn, not
  measured"), so a cut list never goes out on a mouse length.
- Drawing on a room that already has walls asks first: "Replace walls A–D?"
  If cabinets are placed, say how many, and that placements keep their wall
  letter. Any placement that no longer fits its wall shows through the
  existing checks.
- Not this round: dragging a corner of an existing room to reshape it.

## Checks

- `check_room`: all-90 rooms reproduce today's coordinates exactly; L with one
  270°; hexagon 120°×6 closes; 135° bay closes; self-intersection critical;
  mitre in a 135° corner raises the ruling-4 critical; plinth butt at 90/135
  yes, at 270 no.
- Old jobs (Test.json, every fixture) round-trip byte for byte.
- Benchmark holds: 272 MEL / 59 DECOR(BROOKHILL) / 30 BACK, 92 pot holes,
  18/9/6 boards, R28,363.50. Quote the figures.
- `check_all` passes.
- Playwright: draw a 4-wall room by clicks and close it; draw an L with an
  outside corner; set a corner to 270 in the Walls card and see the plan turn;
  drag a cabinet onto an angled wall.
- Don't save Liam_Room. Rudolf fixes it himself (lengths positive, corners set).

## Docs

- `docs/ROOM-LAYOUT-SPEC.md`: corner angle model, draw mode, ruling 4 and 5,
  22 Sept outside-corner hold lifted.
- `CLAUDE.md` Status and the "where it lives now" list (hard rule 9).
- room.py module docstring: replace "Each corner turns 90 degrees less the
  measured deviation" with the new rule.
