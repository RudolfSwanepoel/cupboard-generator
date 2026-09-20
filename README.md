# CupboardApp

Cut-list generator for melamine kitchens and wardrobes, built to replace a
hand-maintained spreadsheet that had 34 logged errors across three real jobs.

## Run the app

```
python run_app.py
```

Opens a desktop window if `pywebview` is installed, otherwise the default
browser, against a local server on `127.0.0.1:8765`. `--no-window` serves
without opening anything, which is how the endpoints get tested.

Four tabs — cabinets, cut list, nesting, validation — over one `POST
/api/compute` that returns panels, issues, board counts, cost, the elevation and
the sheet layouts in a single payload. **Oct 2025** loads the regression
fixture. Export writes the Plazaboard CSVs and the layout SVGs to
`out/<job name>/`, and refuses while any critical is outstanding.

## Run the regression check

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
python tools/check_edging.py
python tools/check_library.py
python tools/check_single_source.py
python tools/check_swap.py
python tools/check_colour.py
python tools/check_panels.py
```

The first rebuilds the October 2025 wardrobe from cabinet definitions and
compares it with the cut list actually sent to Plazaboard. The second checks
every worked example in a docstring still evaluates to what it claims. The rest
pin the room geometry, the filler arithmetic, the plinth, the placement checks
behind dragging, the fronts, the board library, the edging a board offers, the
one list of which cabinet fields hold a board, the board colours the drawings
are filled with, and independent panels.

And the wider net, which catches a change that leaves the benchmark numbers
alone and moves something else:

```
python tools/snapshot.py --out baseline.json      # once, on a known-good tree
python tools/snapshot.py --compare baseline.json  # after a change
```

It dumps every panel, every validation issue, the cost and a hash of each
drawing for the three fixed jobs, and exits non-zero on any difference
`--allow` does not name.

Requires `openpyxl` for the comparison only; the engine itself has no
dependencies, and neither does the UI.

## Status

Engine, validation, nesting, Plazaboard export, costing and the UI are working.

Room layout follows `docs/ROOM-LAYOUT-SPEC.md`. Phases 1 to 4 are built: walls,
corners, coordinates and the closure check; a plan view with a Base / Wall /
Tall layer toggle; gap detection with fillers and scribes; plinth, opt-in per
run, splitting at a cabinet division and butting at internal corners; and drag
placement, where a cabinet slides along its wall, snaps to targets the engine
supplies, re-parents when dragged to another wall, turns red if it overlaps
another carcass, and shows its door swing and drawer pull-out on hover.

Throughout, the app proposes and you decide — it never fits a filler or a plinth
on its own, and the browser never works out a dimension: every position a drag
can settle on comes from the engine, and the drop is recomputed server-side.

Phase 5 adds a dimensioned elevation of each wall, face on: cabinets at their
true positions and heights, openings with their sill and head, obstructions with
where to find them, the chosen fillers and plinth boards, which way each door
hangs, and dimension chains from the wall's start corner and the floor. Pick a
wall above the elevation on the Cabinets tab; export writes one drawing per wall.

3D and CAD export follow. A job without a room behaves exactly as it always has.

Read `docs/RULES.md` before changing any dimension.
