# Brief — Supports edging wording, runner catalogue, drawer setting (28 Sept 2026)

Agreed with Rudolf in Cowork, 28 September 2026. Read `CLAUDE.md` first. The hard
rules in it and in the project instructions hold throughout. Sketch:
`Claude outputs/drawer-setting-sketch-v2.svg` (confirmed correct by Rudolf).

Build in this order. Commit after each part with the benchmark unchanged
(272 / 59 / 30, 92 pot holes, 18 / 9 / 6, R28,363.50), every `check_*.py` green, and
`snapshot.py --compare` showing no movement except where this brief says so.
Quote the figures in the report.

---

## Part 1 — Supports: wording and edge counts (UI only, no cut-list change)

1. **Labels.** In the support rows: `Cut from` → **Support Material**, `Edging` →
   **Edging Material**, `Colour` → **Edging Colour**. The type `Front` is shown as
   **Top Front** everywhere a person reads it (the editor, the 3D part label, the
   part card, messages). The stored `Support.type` value `front` does NOT change,
   and neither does any check id, so every job file round-trips byte for byte.
2. **Edges as counts, the same language as Panel design.** Replace the four
   tickboxes (Front / Rear / Left end / Right end, and Inner / Outer on a Back) with
   two controls, exactly as a panel has them: **Long edges 0 / 1 / 2** and
   **Short edges 0 / 1 / 2**. `Ordered as` reads the way a panel's line does.
3. **Which edge a count means is a rule, decided on the server** (the browser works
   out nothing):
   - Long ×1: **Top Front** and **Top Rear** — the front long edge. **Back 1** — its
     bottom edge (facing down). **Every other Back** — its top edge (facing up).
     (These are today's defaults.)
   - Long ×2: both long edges. Short ×1: the left end. Short ×2: both ends.
4. **Data model unchanged.** `Support.edges` stays the stored form. The server maps
   counts → the canonical `edges` list and back. A stored `edges` set that is not
   canonical for its counts (e.g. rear edge only) is **kept as stored and drawn as
   stored** until the operator changes a count; then it becomes canonical. Say so in
   a one-line note under the row when it happens.
5. The cut list, the tape metres and the cost cannot move: they already read counts
   (`support_row_edge_counts`). Pin that in `check_supports.py`.

## Part 2 — Runner catalogue (like Boards)

**Rudolf wants hardware derived from a catalogue, as boards are. This round is
runners only. Hinges and handles come later, so leave room for them in the design
(a `hardware.json` with a `runners` list is enough).**

0. **The Boards tab becomes Catalogue** (ruled by Rudolf). The top-level tab is
   renamed **Catalogue** and holds two sub-tabs, **Boards | Runners**, the same
   sub-tab pattern as Room's Plan | Elevation. **Boards is exactly what the Boards
   tab is today**: nothing about it changes except where it sits. Every internal jump
   that lands on Boards (New, "select a board first", the add-cabinet refusal) lands
   on Catalogue -> Boards. The app still opens there. Update the Playwright scripts
   and the "where it lives now" checklist.
1. **`runners.json` in the repo** (or `hardware.json` → `runners`), loaded and saved
   by `cabinetgen/hardware.py`, edited on **Catalogue -> Runners** with **the same
   functionality as Boards**: a library list, add / edit / delete, tick into the
   project (a copy goes into the job, price captured), and a used-by-jobs guard on
   delete. A record:
   - name, supplier, SKU, price per pair (captured into the job as board prices are)
   - type: `side-mount ball-bearing` (the only type built now; the field exists so
     soft-close and undermount can be added later)
   - `height` (mm), `side_clearance` (mm per side), `rail_thickness` (information)
   - `lengths`: the list of lengths available
   - `extension`: `full` (travel = length) or a fraction
   - `capacity_kg`
   - `lift`: how far the drawer side's bottom sits above the rail's bottom (see Part 3)
   - `setback`: how far the inner member starts behind the box front
2. **Seed record — Gelmar 45 mm full-extension ball-bearing** (drawing
   04227.XXX-58B, SKU family 7011–7017):
   height 45, side clearance 13.5, rail 12.7, **lengths 300, 350, 400, 450, 500, 550,
   600** (drawing sizes 12"–24", A = B), extension full, 35 kg, lift **5**, setback **3**.
   Gelmar's rule: drawer width = cabinet opening − 27 (13.5 each side). With 16 mm
   drawer sides that is today's `drawer_front_deduct` 59 exactly, so width does not
   move.
3. **A job selects its runner(s) the way it selects boards**: a copy goes into the
   job (price capture). A cabinet with drawers names its runner (default: the job's
   first; new cabinets get the Gelmar record).
4. **Length is picked, not fixed at 450.** The runner length is the **longest length
   the chosen runner offers that leaves at least `runner_clearance` (40) behind it**
   in the carcass depth, exactly as `pick_runner` does now, but over the record's
   list. The box length = the runner length. No length is special. `Standard`
   keeps `runner_clearance`; `runner_lengths` becomes the legacy record (below).
5. **The benchmark must not move.** A job saved before this (no runner named) reads
   a built-in **legacy runner** record: lengths 350 / 450 / 500, side clearance 13.5,
   height 45, lift 5, setback 3. It is never offered for new cabinets. That keeps the
   October job and Test.json cutting exactly what they cut. Pin it in a new
   `tools/check_runners.py`. Note: re-pointing an old job at the Gelmar record may
   legitimately change drawer lengths (e.g. a depth that now takes 400 or 550) —
   that is a design change the operator makes, and the swap preview should say
   which drawer lines move.
6. Everything a runner drives reads the record: box width (clearance), box length
   (length), the "no runner fits" critical (names the shortest length on the record),
   and the 3D.

## Part 3 — The drawer setting (geometry, drawing only unless stated)

From the sketch, confirmed by Rudolf. In the carcass frame:

- The runner's outer rail stands **on the bottom panel**, against the carcass side,
  its front at the carcass front edge.
- The inner member runs **centred in the outer rail**, so the drawer side's bottom is
  **`lift` (5) above the bottom panel's top face**: the lowest box bottom =
  bottom-panel top + 5 (= 21 above the carcass underside with a 16 bottom).
- **Order of work (confirmed by Rudolf):** first space the FACES exactly as today;
  then hang each box off its own face, its bottom at the face bottom + the bottom
  drawer's offset (21 with a 16 bottom: face flush with the carcass underside, box on
  a runner standing on the bottom panel, lifted 5); then check the interferences
  (Part 5). No box position is ever used to move a face.
- The box front is flush with the carcass front edges; the face overlays it.
- The inner member starts `setback` (3) behind the box front.
- Box length = runner length; the space behind is carcass depth − runner length
  (≥ 40 by construction).
- **Face stack is unchanged**: the bottom face is flush with the carcass bottom,
  `stack_gap` 2 between faces, `door_height_gap` 3 at the top. Rudolf confirmed
  both figures.

`room.drawer_box_tops` already exists for the support-foul critical. Make it, and
everything else that places a box, read this one layout (`room.drawer_layout` or
similar, one place), so the support check, the new checks and the 3D cannot disagree.

## Part 4 — Inner drawers (behind a door)

Rudolf builds them. An inner drawer's **face is the size of the drawer box's
carcass**, so the box sides are hidden: face width = box outside width (opening − 27),
face height = box height. It sits behind the door. Add it as a per-drawer choice
(`Drawer.inner`, written only when true). It needs a door on the cabinet. Its face
is still a code-20 line off its face board. No gap arithmetic from the stack
applies to it. Ask before inventing anything the geometry doesn't settle; in
particular, **ask Rudolf how far behind the door face the inner drawer face sits**
(door hinge and bumper clearance). Do not guess that number into `Standard`.

## Part 5 — Checks (criticals unless stated)

1. **Box taller than its face allows**: the box top above the face top, or into the
   next face's box (for the bottom box: its top above its own face top). Critical.
2. **Box clashes with the box above**: box top above the next box's bottom (using
   the Part 3 layout). Critical.
3. **Box does not fit its runner**: box height < the runner's `height`, or no
   length on the record fits the depth (this one already exists — keep its id).
   Critical.
4. The existing support-foul critical stays, now reading the same layout.

Stable check ids, pinned in `check_runners.py` with worked numbers.

## Part 6 — 3D detailing

1. **Drawer boxes drawn in 3D**: sides, front, back and base, from the cut-list
   panels in the Part 3 layout. Remove "drawer boxes" from `scene.NOT_DRAWN`.
2. **Fronts open slides the boxes out** with their faces, to full extension
   (travel = runner length × extension).
3. **Runners drawn as simple blocks** (rail thickness × height × length), grey,
   one layer toggle. Rudolf: "simple preview only, or leave out if it is too
   complicated" — if the blocks cost more than a small amount of code, leave them
   out and say so.
4. Nothing drawn moves the Finish elevation, the plan or any wall elevation: same
   discipline as shelves and supports (`interior_parts`, not `solid_parts`).

## Not in this round

Hinges and handles in the catalogue; soft-close and undermount runners (Gelmar's
undermount pages give no fitting data — a spec sheet is needed first); the
per-cabinet exploded view.

## Report back

The benchmark figures, the checks, what the snapshot moved and why, the new
tab's location, and the open question in Part 4. Update `CLAUDE.md`'s Status and
the "where it lives now" checklist (hard rule 9).
