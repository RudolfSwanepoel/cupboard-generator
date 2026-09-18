# Brief for Claude Code — cabinet editor rebuild + board rename fix

This replaces the 18 Sept brief. It is the full brief decomposed into one checklist
item per requirement, plus two bugs found on review that weren't in the original
brief. Track this as an explicit todo list — one todo per numbered item below, not
grouped into bigger buckets. Mark an item complete only after testing it live in
the browser, not just after writing the code for it.

Before starting: the working tree has an unrelated CRLF-only diff on
`Check It Still Works.bat`, `Finish Session.bat`, `Start Cupboard App.bat`,
`Start Session.bat`, `cabinetgen/drawers.py`, `cabinetgen/standard.py`,
`jobs/Test.json`, `jobs/Test_Build.json` — not part of this work, leave it alone
unless it actually conflicts with something below.

## Part A — Fix first: the DECOR→BROOKHILL rename is incomplete

`boards.json` was renamed (id `DECOR` → `BROOKHILL`, name "BROOKHILL FUSION").
That rename was never propagated through the Python engine. Confirmed still
hardcoded as `"DECOR"`:

- `cabinetgen/model.py` line ~271 — `Cabinet.exterior_board: str = "DECOR"` (the
  default every cabinet falls back to)
- `cabinetgen/model.py` line ~48 — the built-in `MATERIALS` fallback dict, keyed
  `"DECOR"`
- `cabinetgen/export_plaza.py` — `YIELD` map and hardcoded price/edge tables keyed
  `"DECOR"`
- Every `tools/check_*.py` script that references `"DECOR"` as a live board id
  (check_boards.py, check_library.py, check_drag.py, check_elevation.py,
  check_fillers.py, check_fronts.py)

**Important constraint:** `jobs/wardrobe_oct2025.py` (the Oct 2025 regression job)
references `"DECOR"` literally throughout, by design — it's a frozen historical
quote, matching the same "saved jobs keep their own copy under the old id" rule
used for the board rename UI. Don't touch it. That means `"DECOR"` must stay a
valid, resolvable id in `export_plaza.py`'s yield/price/edge tables (add it as an
alias alongside `BROOKHILL`, don't delete it) — but the *default* a new or
unset cabinet resolves to (`Cabinet.exterior_board`, the built-in `MATERIALS`
fallback) must point at `BROOKHILL`, since that's the library's canonical id now.

Acceptance:
- Grep the repo for `DECOR` — every remaining hit is either in
  `jobs/wardrobe_oct2025.py` (intentionally frozen) or an alias entry you added
  on purpose, nothing else.
- A brand-new cabinet's exterior board defaults to BROOKHILL, not DECOR.
- Re-run the regression benchmark and confirm it's still exactly
  272 MEL / 59 DECOR / 30 BACK, 92 pot holes, 18/9/6 boards, ~R28,363.50 — the
  panel-count label "DECOR" in that benchmark is historical and does not need to
  change, only the numbers need to match.
- Reload `jobs/Test.json` and `jobs/Test_Build.json` in the browser: the Board
  Library's BROOKHILL row should show ticked/in-project if the loaded job's
  cabinets are using it, and the Structure tab's exterior board dropdown should
  read cleanly as "BROOKHILL — BROOKHILL FUSION" (not "DECOR — BROOKHILL FUSION
  CHIP").

## Part B — Boards tab

1. Board ID must be editable (a plain text field, not read-only).
2. Renaming an id propagates: confirm dialog, updates every cabinet in the open
   project that references it, and does NOT rewrite already-saved job files —
   they keep their own copy under the old id.
3. DECOR renamed to BROOKHILL in the library (done in `boards.json` — verify).
4. "Swap" uses a dropdown to pick the target board, never a typed id.

## Part C — Layout

5. The cabinet editor / settings panel moves to its own column starting level
   with the line under Run / Wall A / Wall B (see reference image — the arrow
   points at that line), not further down the page.

## Part D — Structure tab

6. Rename all "tape" wording to "edging" throughout the app, not just Structure.
7. The first fields in Structure are the three board selections, in this order:
   Exterior board, Backing board, Carcass board — reading from their id, not a
   free-text "Decor" concept. No edging control appears in Structure at all —
   edging lives only in Doors and Drawers (see Part E, F).
8. `Shelves` vs `Fixed shelves` — this was a direct question, answer it in the
   UI, not just in code. The actual distinction in the engine
   (`cabinetgen/engine.py` + `standard.shelf_depth`): **Fixed shelves** are
   permanently fixed in place (cut with the smaller `shelf_gap_fixed`
   clearance); **Shelves** are adjustable/movable on shelf pegs (cut with the
   larger `shelf_gap_adjustable` clearance for peg movement). Add a one-line
   note under each field saying this in plain language.
9. Dividers don't work and can't be positioned. Grey out the "Dividers" and
   "Divider height" fields, each showing placeholder text "function
   unavailable" (already built as `unavailableField()` — verify both fields use
   it, not just one).
10. Shelf width only means anything once a divider exists. Grey it out the same
    way, with a note explaining why (already built — verify).
11. Decor tab removed completely (done — verify no stray "Decor" references
    remain anywhere in the UI, including tooltips and hint text).

## Part E — Doors

12. A door section is ticked on/off exactly like Drawers — ticking opens the
    configuration panel, unticking closes it.
13. Only 1 or 2 doors, never more (a job saved before this limit existed may
    still show a stale higher count — handle gracefully, don't crash).
14. One door: the opening side (left/right) is user-changeable.
15. Two doors: fixed — left leaf hinged left, right leaf hinged right, not
    user-changeable.
16. Each leaf's material defaults to the Exterior board (from Structure) but is
    changeable per leaf from the available boards.
17. A plain-language note states which board is in effect: "External board is
    <whichever is chosen>."
18. **Layout** — per the reference screenshot, the per-leaf material dropdown
    sits to the right of that leaf's hinge info, in the same row (the red
    circle in the screenshot marks that spot, next to "Leaf 1 ... hinged
    left"). Verify the current per-leaf `<select data-dboard>` is actually
    positioned there and not stacked awkwardly below — adjust CSS/layout if it
    isn't.
19. One single "Edging" control for the whole Doors section (not per leaf):
    a dropdown for 2mm/1mm (single choice) and a separate dropdown for the
    board/colour (single choice).

## Part F — Drawers

20. Board selection area (the "magenta line" area in the reference screenshot,
    which shows the BASE column) gets two explicit fields: **carcass material**
    and **face material**.
21. Carcass material defaults to the Carcass board (from Structure); face
    material defaults to the Exterior board (from Structure). Both are
    changeable per cabinet.
22. One single "Edging" control for the whole Drawers section: 2mm/1mm dropdown
    plus board/colour dropdown, same pattern as Doors.
23. Everything else in Drawers (share/fixed rows, presets, stack solving) was
    already correct — don't touch it beyond the above.

## Part G — Corner Unit

24. Leave exactly as is. No changes. Confirm nothing in the rest of this brief
    accidentally touched it.

## Part H — Back and Supports

25. Rename the "Back and Support" section to "Supports" everywhere it appears
    in the UI (tab label, any headings).
26. Keep all existing Supports functionality as is.
27. The front-facing support panels must reference the Exterior board that now
    lives in Structure (`c.exterior_board`), not any separate/legacy field.

## Part I — Elevation view

28. Remove the ability to click a cupboard in the elevation view to change its
    door opening/hinge side. The per-cabinet setup panel is the only place to
    change that now.
29. Add click-and-drag of a cupboard within the elevation wall view — both
    sideways along the wall and up/down — snapping to wall ends, neighbouring
    cabinet edges, the floor, and the ceiling.
30. Keep the cupboard number drawn on each cabinet in the elevation view.

## Final step

31. Re-run the full regression benchmark and every `tools/check_*.py` script.
    Confirm the Oct 2025 wardrobe job still produces exactly 272 MEL / 59 DECOR
    / 30 BACK, 92 pot holes, 18/9/6 boards, ~R28,363.50.
32. Drive the actual UI (not just the Python checks) through: Boards tab
    rename+swap, Structure board selection, Doors with 1 and 2 leaves, Drawers
    carcass/face selection, elevation drag in both axes, and confirm the
    cupboard number is visible. Report explicitly which of the 32 items above
    passed live testing and which didn't, rather than reporting the batch as
    done.
