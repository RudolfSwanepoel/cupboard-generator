# Brief — The cabinet round: doors, defaults, solid back, shelves, edging in 3D, per-cupboard drawings, catalogue

3 October 2026. From Cowork, every point agreed with Rudolf in chat the same
day. Run under `docs/BRIEF-PROTOCOL.md`, after the import follow-up has
merged, the only session on the repo. **Build before the next demo.**

This brief is long on purpose (Rudolf prefers one round over several). Build
the parts in order, one commit per part, `check_all` green and the benchmark
quoted at every commit. Where a part needs a ruling this brief does not give,
stop that part, say so, and carry on with the next — guess nothing into
`Standard`.

**Benchmark and old jobs.** The October job and every saved job must cut
exactly what they cut today: 272 / 59 / 30, 92 pot holes, 18 / 9 / 6,
R28,363.50, and `snapshot.py --compare` identical in panels, issues and
totals for every job and fixture. Everything below that changes behaviour
changes it for NEW cupboards or for a choice the operator makes; an existing
cupboard changes only when Rudolf edits it. A job file nobody edits
round-trips byte for byte (new fields written only when set, the
`store.LATE_CABINET_FIELDS` pattern).

## Rulings (Rudolf, 2–3 October 2026) — build to these, don't reopen them

1. **"Leaf" becomes "door"** everywhere the screen says it. A pair reads
   **Left door / Right door**. Words only; no stored field is renamed.
2. **Cupboard defaults for a NEW cupboard**: base 450 W × 790 H × 570 D; tall
   800 × 2500 × 600; upper 350 × 1100 × 300. An upper's first placement puts
   its underside at **1500** (with a tall on 100 mm legs at 2600, a default
   upper's top lines up with it). 2500 stays the tall default even though it
   raises above-ceiling / tip-up in a low room — that is the checks working.
3. **Support defaults for a NEW cupboard**:
   - **Top Front**: cut from the carcass board, edged PVC in the **exterior**
     board's colour, front long edge.
   - **Top Rear**: as today — carcass board, PVC in the carcass colour, front
     long edge.
   - **Back**: ONE row per cupboard, unedged — base qty **2**, wall qty **3**,
     tall qty **3** (tall was 4). Blind corner by its kind; mitre / ell none,
     as today. "+ Back support" still adds a separate row when one must differ.
4. **Solid back** — any cupboard may take one:
   - Cut from any board the project carries except a thin (3 mm) one; the
     default is the carcass board.
   - It sits INSIDE the carcass between the sides, its rear face flush with
     the sides' back edges: **(W − 2t) wide**. A cupboard with a top (tall,
     wall): between the top and bottom panels, **(H − 2t) high**. A base unit
     (no top): standing on the bottom panel up to the top of the sides,
     **(H − t) high**. Top and bottom keep their full depth.
   - It **replaces the Back supports AND the Top Rear**: a base unit keeps
     only its Top Front. Typed Back / Top Rear rows on a cupboard switched to
     a solid back stay in the file, are not cut, are greyed, and come back if
     the back is switched back (the tickbox bargain).
   - **Code 06, role "Solid back"**, grain from its board, **unedged by
     default** with long / short edge counts like Panel design.
   - Drawer units may take one too.
   - Existing jobs keep their `four` / `three` / `none` backs exactly.
5. **Shelves** get a section of their own, and "fixed vs adjustable" goes:
   - Shelves are added row by row, like drawers. Each row: **height** (default
     equal spacing; shown, and adjustable, always measured up from the
     bottom), **clearance to the face** (default 4 mm; − / + buttons, 1 mm a
     click), and **edging** chosen like a support row (material, colour, long
     / short counts). Default edging is what a shelf gets today: the front
     long edge in the exterior board's PVC.
   - The shelf sits against whatever is at the back (the backing board, or the
     solid back) and the clearance is at the FACE. Depth = the distance from
     the carcass front to the front face of the back, less the clearance:
     570 D with a backing board → 570 − 16 − 3 − 4 = **547** (as today); with
     a solid back → 570 − 16 − 4 = **550**. A smaller clearance makes a deeper
     shelf. The shelf length (across) is as today.
   - **Migration**: a job's `shelves` (adjustable) read as that many rows at
     clearance 4; `fixed_shelves` as rows at clearance 1 (today's
     `shelf_gap_fixed`) — so every old shelf cuts at exactly today's depth.
     Nothing is written to the file until the cupboard is edited.
   - **Heights are drawing and 3D only**: they never move a cut line (shelves
     are set at fitment).
6. **Edging shows in 3D on every part** — carcass sides, top and bottom,
   doors, drawer faces, panels, as well as the supports, shelves and drawer
   boxes that show it today — in BOTH 3D views (the 3D tab and the Cabinets
   tab's single cupboard). Bands are drawn inside the finished size (hard rule
   5).
7. **A drawing per cupboard**: a **front elevation plus a side section**,
   dimensioned, shown on the Cabinets tab, and exported one SVG per ticked
   cupboard.
8. **The Placements strip shows on Room → Elevation as well as Plan** — the
   same strip, the same collapsed state, the same Z column (an exact height
   off the floor is typed there).
9. **Catalogue of standard cupboards**:
   - `cupboards.json` at the repo root, beside `boards.json` / `hardware.json`,
     shared through git; a third sub-tab, **Catalogue → Boards | Runners |
     Cupboards**: list, a small preview, delete, rename.
   - **Add to catalogue** in the cupboard editor saves the cupboard as it is
     configured — every setting (doors, drawers, supports, shelves, back,
     corner settings) and its attached panels with their offsets — without
     its number, placement or note. An **author** is typed. The name is
     generated `<Kind> <W>×<H>×<D>` (e.g. `Tall 800×2500×600`) followed by
     the text the user types; the generated part is always there and always
     first. A name already in the catalogue (case-insensitive) is refused
     with "<name> already exists — choose another name", as Import does.
     Offered for cupboards, not for a standalone Panel.
   - **Place from catalogue** on the Cabinets tab copies it into the project
     with the next free number (its attached panels with theirs), unplaced —
     into the unplaced list. From then on it is the project's own: no link
     back; editing either changes nothing in the other.
   - **Boards on placing**: any board the copy names that the project has not
     selected is mapped in a small dialog to a project board — default the
     first project board of the same thickness — before the copy lands, so a
     catalogue cupboard never arrives with an unpriced board. A runner the
     project has not selected is mapped the same way (or ticked in from the
     runner library if it is there, which the dialog offers first).

## Part 1 — Wording and defaults (rulings 1, 2, 3)

- Find every "leaf" a person reads (38 in `app/index.html`, more in
  `api.py`, `render.py`, `room.py`, `validate.py`, `model.py`, `engine.py`
  messages and labels) and say "door"; code identifiers and stored keys stay.
- **The new-cupboard sizes move out of the browser.** `blankCabinet` in
  `index.html` types 600 × 2400 × 500 itself today — a dimension computed in
  the browser. Put the three default sizes in `Standard` (per kind) and hand
  them to the browser through `/api/defaults`. A new cupboard takes its
  kind's size, and follows a kind change while its size is still that
  untouched default (the same rule its support rows follow today).
- `Standard.upper_z` 1500: the first placement of an upper (Placements' wall
  picker, the unplaced-list drag drop, `free_x`) stands its underside there.
- `Cabinet.default_supports` / `new_support` to ruling 3.
- CLAUDE.md's key ruled numbers line on new-cabinet supports is updated to
  ruling 3.

**Done when:** no "leaf" left in any text a person reads (grep quoted, code
identifiers listed as kept); a new base / tall / upper gets its size from
`/api/defaults` and the browser types no dimension; a new upper dropped on a
wall lands at z 1500; a new base's supports are Top Front (exterior PVC) +
Top Rear + one Back row qty 2 unedged, wall and tall one Back row qty 3
unedged; no saved job's supports or sizes move.

## Part 2 — Solid back (ruling 4)

- The model: a fourth back choice, `solid`, and the board it is cut from
  (default the carcass board; in `Cabinet._board_slots` so swap / un-select /
  rename / the library scan find it — `check_single_source.py` holds that),
  and its edge counts.
- The engine: the code-06 line at the ruled size; no backing-board line; no
  Back or Top Rear supports cut. The bottom, top and sides unchanged.
- Everything that reads where the back is — shelf depth, `back_face_from_front`
  and its callers, the runner pick and its 40 mm clearance, `support_layout`,
  `drawer_layout`, the shelf-fouls-back check, `room.geometry`, the 3D
  (`room.back_part`), the elevation and plan — reads it from the back actually
  chosen. List every one in the plan.
- The Structure section: Back = Four sides / None / **Solid**, and with Solid
  the board and edging controls; the Supports section greys Back and Top Rear
  rows with one line saying why.

**Done when:** a 600 × 2400 × 570 tall with a solid back cuts a 06 line of
568 × 2368 in the carcass board and no backing line, and a shelf of 550 at 4
mm; a 450 × 790 × 570 base with a solid back cuts 418 × 774 and keeps only
its Top Front; switching back to Four restores the support rows untouched;
a drawer unit's runner is picked over its real inside depth; pinned in a
`check_*.py` with these numbers; benchmark unchanged.

## Part 3 — Shelves (ruling 5)

- A Shelves section of its own (out of Structure), rows like the Drawers
  stack: `#` · Height (from the bottom, mm) · Clearance (mm, − / +) · Depth
  (derived, shown) · Edging · ×; **+ Shelf**; **Equal** re-spaces the heights.
- Show what "from the bottom" is measured to in the column's help line (the
  top face of the bottom panel to the top face of the shelf), and draw it so
  in the per-cupboard drawing (Part 5).
- Mitre corner units keep their own arm shelf / mitred shelf as today; this
  section is for straight carcasses.
- Migration exactly as ruling 5. The benchmark job's shelves and fixed
  shelves must cut identically — it has both.

**Done when:** an old job's shelves show as rows at 4 and fixed shelves at 1,
cutting exactly what they cut (snapshot identical); a clearance click moves
the depth by 1 and the cut line with it; heights move no cut line; a new
shelf's edging is the front long edge in the exterior PVC; pinned in a check.

## Part 4 — Edging in 3D on every part (ruling 6)

Extend the band drawing (`room.tape_solids`, today carried by
`interior_parts`) to every part `room.solid_parts` and `back_part` draw that
has a banded edge on its cut-list line, in both 3D views. No position or size
moves; `/api/scene` changes only by the added bands.

**Done when:** in `ui_check_3d.py --stage look` (or a new stage) a carcass
side's front edge reads the exterior board's edging colour in the 3D tab and
in the Cabinets tab's 3D; `check_scene.py` asserts every banded edge of every
part has its band.

## Part 5 — A drawing per cupboard (ruling 7)

- `render.cabinet_svg(job, number)`: a **front elevation** (doors, drawer
  faces, hinges, board colours and pictures as the wall elevation draws them)
  beside a **side section** through the middle of the width, looking at the
  inside of the left side: sides' profile, top and bottom, the back (backing
  board in its slot with the 16 mm cavity, or the solid back), supports,
  shelves at their heights and depths with their face clearance, drawer boxes
  and runners. Dimensioned: overall W, H, D; shelf heights from the bottom;
  shelf depths; support positions. Legs are not drawn (still not modelled) —
  the leg height is a note.
- Shown on the Cabinets tab: a toggle **3D | Drawing** over the cupboard
  view.
- Export: the export dialog gains a list of cupboards to tick (all ticked by
  default), one `<job>_cabinet_<n>.svg` each into `drawings/`. These are
  written **with or without a room** (the "no room, no drawing" ruling is
  about room drawings).
- Corner units: mitre and blind drawn as their own construction; ell says
  construction not ruled, as elsewhere.

**Done when:** `check_elevation.py` (or a new check) holds the section's
dimension chains closing on H and D for a tall, a base with drawers and a
solid-back cupboard; the export writes one file per ticked cupboard; a
Playwright stage shows the toggle and the drawing.

## Part 6 — Placements on Room → Elevation (ruling 8)

The left Placements strip of Room → Plan shows on Room → Elevation too:
the same element or the same render, the same collapsed state, the Z column
typed there moving the cupboard in the elevation at once.

**Done when:** a Playwright stage opens Elevation, expands Placements, types
a Z and the cupboard's underside in the elevation reads it; Plan unchanged.

## Part 7 — Catalogue (ruling 9)

- `cabinetgen/catalogue.py`: load / save `cupboards.json` (the `boards.py`
  pattern), a record = name, author, date added, the cupboard record and its
  attached panels, the boards and runners it names (id and name). The name
  rule, the taken-name refusal, the copy-in with next numbers, and the board /
  runner mapping are decided here, testable without the UI.
- API: `/api/catalogue` (list), `/api/catalogue-add`, `/api/catalogue-place`
  (the mapping in, the new cupboard out), `/api/catalogue-delete`,
  `/api/catalogue-rename`.
- UI: Catalogue → Cupboards sub-tab (list, author, date, the single-cupboard
  3D preview, delete, rename); **Add to catalogue** in the cupboard editor
  (author, the generated prefix shown, the free text); **Place from
  catalogue** on the Cabinets tab with the mapping dialog.
- The demo build copies `cupboards.json` in by name (`tools/build_demo.py`),
  and Import project brings across catalogue cupboards the same way it brings
  boards (new / identical / "(imported)"), with the same name-taken rule.

**Done when:** `check_catalogue.py` (temp files only): add → the record and
name; a taken name refused (any case) and nothing written; place → next free
numbers, attached panels with theirs, unplaced, and cutting exactly what the
original cut when the boards are the same; a board the project lacks is
mapped and the copy names the mapped id; editing the copy leaves the
catalogue byte-identical and vice versa. A Playwright stage: add, see it on
Catalogue → Cupboards, place it, map a board.

## Docs

The write-up in `docs/history/cabinet-round-brief-2026-10-03.md`, listed from
`docs/HISTORY.md`; one Status line in CLAUDE.md (keep `wc -w CLAUDE.md` under
3,500); the layout table's new lines (`catalogue.py`, `cupboards.json`, the
new checks); `docs/HOW-IT-WORKS.md` — the sections this touches (Supports,
The UI, Drawings, Boards…) get the new behaviour, and **every moved
function** gets its row in "Where every moved function lives now": shelves
from Structure to Shelves; fixed / adjustable shelves to clearance rows; the
browser's new-cupboard size to `Standard`; Placements on Elevation.

## Checks

- `check_all` green at every commit, the count quoted; benchmark 272 / 59 /
  30, 92 pot holes, 18 / 9 / 6, R28,363.50 at every commit; `snapshot.py
  --compare` against the tree before: panels, issues and totals identical for
  every job and fixture, drawings and the 3D payload allowed to move by the
  bands only.
- Every Playwright script run at the end and quoted.

## Report back

Every place that read the back's position and what it reads now; anything
about shelves or the solid back the rulings did not settle; the benchmark
line; the word count of CLAUDE.md.
