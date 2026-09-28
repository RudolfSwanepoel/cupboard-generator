# Brief — organise the export folder (28 September 2026)

Agreed with Rudolf in Cowork. Small, file-location only. No cut-list, nesting,
costing or drawing content changes. Benchmark must be unchanged
(272 / 59 / 30, 92 pot holes, 18 / 9 / 6, R28,363.50).

## Layout — `output/<job>/`

| Subfolder    | What goes in it                                                        | Written by |
|--------------|------------------------------------------------------------------------|------------|
| `cutlist/`   | `<job>_<BOARD>.csv` (Plazaboard CSVs), `<job>_accepted.txt`            | `/api/export` |
| `nesting/`   | `nest_<BOARD>.svg`                                                     | `/api/export`, `tools/regen_check.py` |
| `drawings/`  | `<job>_plan.svg`, `<job>_elevation_<wall>.svg`, and the board picture files copied beside them (`api._export_pictures` — the SVGs reference the bare file name, so the pictures MUST sit in `drawings/` with them) | `/api/export` |
| `snapshots/` | `<job>_3d_<n>.png`                                                     | `/api/snapshot` |
| `_previous/` | the last export's `cutlist/`, `nesting/`, `drawings/`, as they were    | `/api/export` |

## Export: clear and rewrite (ruled)

Export overwrites in place today, so files it no longer writes linger
(`Test_elevation.svg` from 22 Sept, before the Run was removed; a wall
elevation for a wall since unticked or deleted). From now on:

1. Before writing, move the existing `cutlist/`, `nesting/` and `drawings/`
   into `output/<job>/_previous/` (replacing whatever `_previous/` held — one
   level of undo, nothing older).
2. Write the new export fresh into the three folders.
3. **Never touch `snapshots/`.** Snapshots are not export output.
4. The export's reply / toast names `output/<job>/` and the folders written.

## Snapshots

`/api/snapshot` writes into `output/<job>/snapshots/`; the numbering
(`_3d_<n>`, never overwriting) counts files in that folder. Update the toast
and the Snapshot button's title (`view3d.js`), and the comment in `index.html`.

## Checks and tools to update

- `tools/regen_check.py` → `output/wardrobe_oct2025/nesting/`, and its message.
- `tools/check_elevation.py` `ui_restructure()` export test (around line 644):
  expect the new subfolders; add a check that a second export moves the first
  into `_previous/`, that a stale file does not survive into the new export,
  and that `snapshots/` is untouched by export.
- `tools/ui_check_3d.py` stage 13 → `output/Test/snapshots/`, toast text.
- `tools/ui_check_restructure.py` (~line 665-693) reads the export folder — follow it.
- Recommended, low stakes: the Playwright screenshot folders
  `output/ui_check_drawers/` and `output/ui_check_restructure/` sit beside job
  folders and could collide with a job of that name. Move them to
  `output/_checks/<name>/`.
- `CLAUDE.md`: update **Where the exports land**, the 3D Snapshot line, the
  nester's "Sheet layouts render to" line, and add rows to the "where it lives
  now" checklist (hard rule 9).

## Already done by Cowork on Rudolf's laptop

`output/Test/` and `output/wardrobe_oct2025/` were moved by hand into this
layout (nothing deleted; the stale `Test_elevation.svg` is in
`output/Test/_previous/`). `output/` is local and gitignored, so a cloud
session will not see this — build and check against a fresh export.

Not in scope: the legacy `out/` folder at the repo root and the root-level
`snapshot-3d-step0*.json` files — Rudolf chose to leave them.
