# Brief for Claude Code — Boards & edging rebuild, board-colour drawings, independent Panels, 3D view

Written 20 Sep 2026 after a planning session with Rudolf. **Nothing in this brief is built in the repo.**
The data layer of Part A was prototyped in a scratch copy to prove it is safe (see Appendix 1); everything
else is design. Work from the repo (`C:\Dev\CupboardApp`, branch `master`), never the OneDrive copy.

---------------------------------------------------------------------------------------------------

## 0. How to work

1. **One todo per ID below** (`0.1`, `A3`, `D7` …), not grouped. Mark an item done only after you have
   exercised it in the running app, not after writing the code. Finish with a per-ID pass/fail report,
   never "done".
2. **Order and stops.** Step 0 → **A + B** → *stop, Rudolf tries it* → **C** → *stop* → **D + E** → *stop* →
   **F**. Do not start the next block until he has answered.
3. **Ask, don't guess.** Section 2 lists everything Rudolf has not ruled. Put those to him in **one batched
   round of tappable multiple-choice questions before you start** (his standing preference), using the
   defaults shown as the recommended option. Anything not in Section 2 that turns out to be a real judgment
   call: ask, don't assume.
4. **Rudolf's style**: concise, plain English, correct technical terms. Report in that style.
5. `git pull` at the start, `git push` at each clean stop (branch is `master`, not `main`). One commit per
   part. Stage files by name.
6. **Line endings.** Every working-tree file that matters is currently CRLF while HEAD holds LF (Q1 in
   Section 2 explains). Whatever you decide there, **edit files without changing their existing line endings** — a
   whole-file diff hides real changes. After every edit, run `git diff --ignore-space-at-eol --stat` and
   confirm it shows only the lines you meant to change.
7. Do not edit `jobs/wardrobe_oct2025.py` (frozen), `jobs/Test.json`, `jobs/Test_Build.json`. Make new
   fixture jobs instead (`jobs/Test_Panels.json`, etc.).

---------------------------------------------------------------------------------------------------

## 1. What Rudolf asked for, and what is already decided

**His four asks**

1. Draw cupboards in the Cabinets → Wall/Run elevation with the **real board colours**, like his
   kitchen-fronts reference picture.
2. A **3D view**.
3. **Independent Panels**: in the cabinet editor's *Size → Kind* dropdown he picks **"Panel"**, and the
   lower sections become **"Panel design"** — board, orientation, edging, grain direction. Panels are
   **numbered in the same series as cabinets** (his reference numbers panels 1, 12, 13, 15) and are **not
   part of any cupboard design**. He also builds **bulkhead panels** (e.g. for lighting above cupboards).
4. **Boards tab**: a **"Has Edging"** tick that reveals **PVC / 1mm / 2mm** ticks (any combination) and an
   **"Edging Name"**. Only the ticked kinds are selectable. A board without edging shows **no edging
   anywhere** (as the backing board should). **Every board characteristic is fixed in the Boards input and
   derived everywhere else.**

**Rulings already made (20 Sep 2026)**

| Topic | Ruling |
|---|---|
| Edging Name | The **existing "Edging name" field** (`bf-tape`, the token behind `PVC <t>` / `1mm <t>` / `2mm <t>`) moves under Has Edging. The board keeps its own long name elsewhere. |
| A needed edging the board doesn't offer | **CRITICAL** — blocks export, names the cabinet, the board and the kind. |
| Board colour | A **colour picker on the Boards tab**. Picture, texture and any other render attribute also live on the Boards record and are entered nowhere else. |
| Panel follows a moving cabinet? | **No — a panel stays where it is** (independent). He can imagine choosing what a panel is locked to later → leave one reserved, unused field (`anchor`), see D1. |
| Panel size | **Typed**, not derived from a neighbour (bulkheads mean "match the neighbour" isn't the real use). A "match neighbour" helper is deferred until he asks. |
| Bulkheads | Several panels make one bulkhead (front upright + underside flat + end caps), **each its own numbered item**. A panel can stand **off the wall**, so placement needs an out-from-wall offset `y` from v1. |
| Panel orientations | Support **all three** (upright facing the room, flat, upright side-on). Same engine code; orientation only changes what is typed and how it is drawn. He did not follow the original question — explain it in plain words in the UI, with small icons. |
| Drawer-face grain | **Vertical, up the face height, as the cut list has it — ruled, correct, never question it (Q4).** |

---------------------------------------------------------------------------------------------------

## 2. Open items — do not guess. Ask in the first batched round.

Each has a **default** that applies until he answers.

- **Q1 — Line endings / git hygiene.** Working tree shows ~11,137 lines of CRLF-only churn across ~22
  files; only **two real changes** exist (`boards.json` MEL→WHITEMEL, `jobs/Test.json` rename + depth edits).
  Options: (a) **add `.gitattributes` (`* text=auto eol=lf`, `*.bat text eol=crlf`), renormalise once in its own
  commit, then commit the two real changes separately** (recommended); (b) leave as is and always review with
  `--ignore-space-at-eol`. *Default until answered: (b), and commit nothing you didn't change.*
- **Q2 — Panel cut-list code.** Reuse code **08** (currently "Exposed Panel") or add a new code? A new code
  needs Plazaboard sign-off (10 and 11 are still unconfirmed). *Default: reuse 08 with role `"Panel"`. First
  check whether `export_plaza.rows_for` writes the component name from `CODES[code]` or from `Panel.role`;
  tell Rudolf which one Plazaboard would see.*
- **Q3 — Carcass-front edging when the exterior board doesn't offer PVC.** Carcass fronts are PVC in the
  *exterior* board's colour (ruled 14 Sept). So a board ticked **2mm only** used as a cabinet's exterior board
  leaves the carcass fronts without an offered edging. This is a direct consequence of his rule, not a bug.
  Options: (a) **CRITICAL, message names the fix** (recommended; the per-cabinet `carcass_edge` override
  already exists), (b) fall back to the carcass board's PVC, (c) let the carcass-front colour be chosen per
  cabinet. *Default: (a) — that is what the prototype does.*
- **Q4 — Drawer-face grain. RULED (20 Sep 2026): grain runs VERTICAL, up the face height, exactly as the cut
  list has it (`Length = face height`). Correct — never call it wrong, never suggest horizontal, do not ask
  again. No note in the legend, no change to the cut list.**
- **Q5 — `WHITE_EDGE = "PVC WHITE"`** (`model.py:245`) is hardcoded for "white-edged" support rows. That breaks
  "derived from Boards". Options: (a) a **job-level "white edging board"** chosen from boards that offer PVC
  (default WHITEMEL → still `PVC WHITE`, benchmark unmoved), (b) keep the constant, add a WARNING when no board
  in the job offers PVC with token `WHITE`, (c) per-row board choice on the supports table. *Default: (b).*
- **Q6 — Commit the two real changes now?** (only if Q1 = (b)).

Existing open items from CLAUDE.md stay open and are **not** to be decided here: `offset_depth` default and
sign; panel codes 10/11 (`Standard.codes_confirmed`); appliances as room objects; worktops; bespoke cupboard
shapes.

**Not questions, but tell him in your first message:** (i) his four boards need his input on the Boards tab
once Part A lands — which kinds each offers and each colour (see A11; don't invent colours); (ii) the
consequence in Q3.

---------------------------------------------------------------------------------------------------

## 3. Hard rules — and where this work presses on them

From CLAUDE.md, unchanged:

1. **A declared dimension never feeds a geometric check.** Every check derives from the actual panel set via
   `room.geometry(cab)`. → **Panels** must give `geometry()` a branch derived from the panel + orientation.
   **3D** boxes are a drawing; nothing may read them for a check (D/F).
2. **Panel designations never change once created**; generating a cut list is read-only on the job model
   (`engine.generate_job`, pinned in `check_drag.py`). → Panel numbers come from `store.next_number`; changing
   a panel's kind never renumbers.
3. **Benchmark must hold**: 272 MEL / 59 DECOR / 30 BACK, 92 pot holes, 18/9/6 boards, ~R28,363.50.
4. **Plazaboard cuts guillotine only.** Panels are rectangles.

Project conventions this work must keep:

- **All trig lives in `room.py`** (`to_world`). The browser computes no dimension — including 3D: the server
  sends world positions/axes, three.js only draws.
- **`Job.room is None` behaves exactly as before.** A job with no panels behaves exactly as before — pin it
  in a check.
- `DECOR` alias stays valid (`model.BOARD_ALIASES`, `export_plaza` tables). Don't touch it.
- Unticking keeps data (the house pattern: "Has doors", "Has drawers"): unticking **Has Edging** keeps the
  board's kinds and name in the file and merely stops anything reading them.

**Proposed additions to CLAUDE.md** (put to Rudolf — do not add unilaterally):
*H5 — Every board attribute (edging, colour, thickness, grain, price) is read from the Boards record; nothing
else states one.* *H6 — Drawings (colour, grain lines, 3D) are read-only views of the model and never feed a
check.*

---------------------------------------------------------------------------------------------------

## 4. How the app works today (verified against the code, 20 Sep 2026)

Line numbers are as of that date — grep by name if they've moved.

**Inputs**

- **Boards tab → `boards.json`.** Record: `id, name, tape (edging token), thickness, grain, price, picture`
  (`cabinetgen/boards.py`). No colour, no Has Edging today.
- **Ticking a board into a project** → `api.board_select` copies the record into `Job.materials`. The **price
  is frozen** ("price capture"); `api.LIVE_FIELDS` (name, board, tape, thickness, grain, picture) refresh from
  the library on edit/load. Every board dropdown lists `S.res.boards` = `Job.board_ids`.
- **Cabinet editor** (right column) → a `Cabinet` record: board ids (`carcass_board`, `exterior_board`,
  `back_board`, `drawer_carcass_board`, `drawer_face_board`, `door_boards[]`, `door_edge_board`,
  `drawer_edge_board`, per-drawer `box_board`/`face_board`), doors/drawers/supports/shelves, edging kind.
- **Room tab and drags** → only `Job.placements` (`wall, x, z, flip`, optional `layer`) or a drawer-face split.
  A drag never writes a dimension.

**Engine** — every edit POSTs the whole job to `/api/compute` (`api.py:533`); a fresh `Job` is built each
request. `engine.generate_cabinet` → `Panel`s (board id, size, `grain`, `edge_material` via `model.tape_for`)
→ `validate.validate` (criticals block export) → `nest` → `export_plaza` cost → Plazaboard CSV.
`room.geometry(cab)` (`room.py:279`) reads the **panels** for footprint/height/depth (hard rule 1).

**Edging derivation (model.py `Cabinet`)** — carcass fronts: PVC in the **exterior** board's colour;
doors: 1mm/2mm in `door_edge_board` (default exterior); drawer faces likewise; drawer boxes: PVC in the
drawer-box board's colour; supports `front` = carcass tape, `white` = `WHITE_EDGE`. All go through
`tape_for(materials, board, kind)` = `"<PVC|1mm|2mm> <token>"`.

**Grain** — the cut list's `Length` is the grain direction; `Panel.grain = 1` means locked (nester can't
rotate). Doors: `Length = door height`. **Drawer faces: `Panel(length=face_h, width=W-3)`** → grain runs up.

**Outputs** — three drawings plus tables:
- **Run** = `render.elevation_svg` (`render.py:63`): `job.cabinets` in **list order**, **declared** sizes,
  **ignores placements** (a wall unit sits on the floor in Run and hangs at z=1400 in Wall A). It has **no
  click-to-select**.
- **Wall** = `render.wall_elevation_svg` (`:177`): placements + geometry from panels; has drag handles
  (`.ecabg` groups, `.etrack`, `.fdiv`, `.edoor`).
- **Plan** = `render.plan_svg` (`:375`).
- Run and Wall share `render._interior` (`:696`), which draws doors and drawer faces with **hardcoded**
  colours `DOOR` teal, `FACE` cream, and a cabinet body filled by **layer** (`LAYER_FILL`: base/wall/tall).
  That is why colours look arbitrary today.

**Corrections to Rudolf's mental model — say these to him plainly**
- **Run is not the master input.** It is one drawing of the cabinet list. The master inputs are the **Boards
  tab** and the **cabinet editor**. The look must derive from the `Cabinet` record's board fields through the
  same resolvers the engine uses (`Cabinet.door_board(i)`, `face_board_of(d)`, `exterior_board`,
  `carcass_board`), never from a parallel copy.
- **Run doesn't select.** There is no click-to-select in Run; add it (C9).
- **Run ignores placement.** Not changed here; say so once so he isn't surprised.

**Facts you'd otherwise rediscover**

- `Cabinet.template` already has `'standard' | 'none'` (`none` = bespoke, `Cabinet.bespoke` panels, "generate
  nothing"). Every `template == "none"` site: `engine.py:31`, `render.py:41`, `validate.py:290`, `:373`,
  `:670`, `index.html:490`, `:732`. The frozen Oct job uses `template="none"` for two cabinets. **Do not
  overload `none` for panels** — add a third value (`"panel"`, D1).
- `Job.loose: List[Panel]` exists (cut-only spare panels, cabinet number 0 or a used number) and
  `store.next_number` counts cabinets **and** loose panels. `Job.loose` has no placement, so it is *not* the
  place for placeable panels.
- `room.to_world(rm, wall_id, x, y=0, z=0)` (`:148`) **already takes `y`** (out from the wall).
- `room.placed(job)` (`:484`) is the single choke point returning `(cab, placement, layer)`; gaps, runs,
  plinth, tip-up, door-swing, overlaps all go through it (or `job.cabinets`).
- `room.carcass_z(cab, p)` (`:1151`) adds the leg height when a cabinet stands on the floor; panels must not.
- `Standard.back_face_from_front(d) = d - back_cavity(16) - back_t(3)` — the back's position is derivable.
- `Handler.do_GET` (`api.py:~915`) serves only `/` and API routes. No static route exists (needed for 3D).
- `tools/check_elevation.py` **only asserts that `wall_elevation_svg` with no room equals `elevation_svg`**
  (function equality). There is **no stored SVG hash** to re-baseline. (An earlier note said otherwise — that
  was wrong.)
- `tools/check_library.py` currently **aborts at line 184** (`B.find(lib, "MEL")` → `None`) because the live
  `boards.json` no longer has id `MEL` after his WHITEMEL rename. Everything after line 184 (~30 checks) is
  therefore **not running**. Pre-existing, not caused by this work; fix in B5. `check_boards.py` etc. also
  hardcode `"MEL"` (82 hits across tools) — those still pass today.
- The 3D library: `three@0.186.0` needs **`three.module.js` + `three.core.js`** (the module imports
  `./three.core.js`) **+ `OrbitControls.js`** (imports bare `'three'`) **+ `LICENSE`**, wired with an
  **import map**. WebView2 (pywebview on Windows) supports import maps.

---------------------------------------------------------------------------------------------------

## Step 0 — Before any build

- **0.1** `git pull`. Note HEAD.
- **0.2** Resolve Q1 (line endings) with Rudolf. Do not proceed to A until decided.
- **0.3** **Baseline** (untouched tree): run `python tools/regen_check.py`, every `tools/check_*.py`, and
  `python tools/snapshot.py --out baseline.json` (Appendix 2). Record: which checks pass, that `check_library`
  aborts at 184, the benchmark numbers, and the snapshot's line `{'oct2025': (165, 4, 28363.5), 'Test': (62, 3,
  6257.25), 'Test_Build': (27, 1, 3374.25)}` (panel lines, issues, total). Keep `baseline.json` outside the
  repo (or gitignored).
- **0.4** Run `Check It Still Works.bat` (real Python + openpyxl) once for the openpyxl-backed panel counts.
  Your own test Python lacks openpyxl and can't verify those.

Acceptance: you can state the benchmark numbers from a run you did, and you have `baseline.json`.

---------------------------------------------------------------------------------------------------

## PART A — Boards record, Boards form, edging that follows the board

**Goal.** The Boards tab is the only place a board's edging, colour, thickness, grain and price are stated.
Has Edging / kinds / Edging Name are real fields; every edging control and every piece of edging text follows
them.

**A1 — Record.** Add to `Board` (`boards.py`): `has_edging: bool`, `edging_kinds: List[str]` ⊆
`["pvc","1mm","2mm"]`, `colour: str` (`#rrggbb` lower-case, or `""`). `tape` stays and is the *Edging Name*.
- **Legacy rule (this keeps the benchmark still):** a record with **neither** `has_edging` nor `edging_kinds`
  keys reads as `has_edging=True`, all three kinds. Same for `Job.materials` records. Old jobs and the frozen
  Oct job therefore do not move.
- `Board.offered` = `edging_kinds` if `has_edging` else `[]`. `Board.tape_name(kind)` = `""` unless
  `has_edging` and kind ∈ offered and a token exists.
- Sanitisers: `clean_kinds` (dedupe, drop unknowns, fixed order pvc,1mm,2mm), `clean_colour` (`#rgb` →
  `#rrggbb`, lower-case, else `""`).
- `to_material(board)` emits the three new keys; `model.py` gains `ALL_KINDS`, `NO_COLOUR = "#d9d6cf"`,
  `material_offers(mats, key)`, `material_has_edging`, `material_colour`. **`model.tape_for` returns `""` when
  the token is missing or the kind isn't offered.**
- **Reference implementation: Appendix 1** (verified byte-identical on the snapshot). Port it; don't reinvent.

**A2 — Boards form** (`drawBoardEditor`, `index.html:1495`; new-board template `:1594`; save handler `:1643`).
Layout, top to bottom: id, name, thickness, grain, price, **Colour**, picture, then **[ ] Has Edging**. Ticking
it reveals a row of three ticks **PVC · 1mm · 2mm** (any combination, at least one) and the **Edging Name**
field (moved from its current position). Unticked → the whole block is hidden; stored values are kept.
- Colour: `<input type="color">` and a hex text field, kept in sync; empty allowed (means "no colour set").
- The live preview line (`#bf-tapes`, `:1545`) lists **only ticked kinds**, e.g. `2mm WHITE`.
- New board defaults: Has Edging **off**, no kinds, no colour (the record-level legacy default is only for old
  data).
- Inline validation message under the field, not just a toast.

**A3 — Boards table** (`drawBoards`, `:1412`): a swatch column (empty/hollow swatch when no colour); the
three-line edging cell (`:1436`) shows `—` if no edging, otherwise only the offered names. Same swatch in the
swap picker (`drawSwapPicker`, `:1554`).

**A4 — Save rules** (`api.board_save`, `:286`): reject Has Edging without a name, or without any kind; colour
must be `#rrggbb` or empty. Error text says what to do. Client checks the same first.

**A5 — Project copy and refresh.** `api._board_payload` and `to_material` carry the new fields;
`LIVE_FIELDS` (`:339`) gains `has_edging`, `edging_kinds`, `colour` (they refresh from the library like name/
picture; **price stays frozen**). `defaults()` returns `edging_kinds` and `no_colour` to the browser.

**A6 — Edging controls follow the board** (`edgingHTML`, `:1285`, used by Doors and Drawers; also the new
Panel design, D5).
- Kind dropdown lists only kinds offered by **at least one** project board. Doors and Drawers stay limited to
  1mm/2mm as today (`S.def.exterior_tapes`; PVC is the carcass edging and isn't selectable there); Panels
  (D4) may use all three.
- Colour dropdown lists only boards that **offer the chosen kind**.
- If a cabinet's stored choice is no longer offered: keep it shown, marked red "(not offered)", and let
  validation block export. **Never silently change a stored choice.**
- If no project board has any edging: replace the control with one line — "No board in this project has
  edging — tick Has Edging on a board in the Boards tab."

**A7 — Edging text disappears where a board has none.** Enumerate and fix every surface (grep
`tape|edging|edge` in `index.html`, `render.py`, `api.py`, `export_plaza.py`, `validate.py`):
`data-edgename` readout (today shows "none mapped" — make it "no edging" grey for a board with none, red
"not offered" for a kind the board lacks); `render.tape_legend` (`:27`) and `_tape_note` (`:52`) skip empty
tapes; the cut-list Edge column stays blank; validation messages; cost lines only for panels that carry edging;
the Plazaboard CSV. **Acceptance:** with every board's Has Edging off, no rendered surface or exported file
mentions PVC/1mm/2mm/edging other than the Boards tab's own controls.

**A8 — Thin boards don't appear where they can't be used.** Add `model.is_thin(materials, key)` (thickness
≤ 3, the rule `export_plaza` already uses). The carcass, exterior, door-leaf, drawer-face and drawer-box
dropdowns exclude thin boards (today the door-leaf dropdown offers the 3 mm backing); the back-board dropdown
lists **only** thin boards. A stored value that fails the rule stays displayed, flagged, and validation
reports it.

**A9 — Validation** (reference: Appendix 1). In `_boards_and_tapes` (`validate.py:287`): a needed kind not
offered → **CRITICAL**, `ref="EDGING"`, naming cabinet, board and kind, and saying what to tick. A missing
token stays a WARNING **with its current wording byte-identical** (`check_boards.py:172` pins the phrase
"no name to build edging from" — the first prototype pass broke this; don't repeat it). In
`_edge_materials`, a cabinet already covered by an `EDGING` critical does not also get the per-panel "edges
specified but no edge material" critical (one problem, one message).

**A10 — Legacy check.** A job whose materials have no new keys yields **identical** panels, issues and drawings
(`snapshot.py --compare baseline.json` → identical). Pin it in a new check.

**A11 — Migrate `boards.json`** (Rudolf's data — show him, don't decide): proposed starting point — `BACK`:
Has Edging **off** (`model.MATERIALS` already comments "a 3 mm back … is never edged"); `WHITEMEL`,
`BROOKHILL`, `GREY`: Has Edging **on**, all three kinds (that is what they do today); colours **blank**. Then
tell Rudolf to set the real kinds and colours in the Boards tab. Until he does, drawings use the neutral colour
and the legend says "no colour set". **Do not invent colours.**

**A12 — Tests.** New `tools/check_edging.py`, in the style of the other checks: legacy record = all kinds;
Has Edging off ⇒ `tape_for` empty for every kind, and a CRITICAL when a cabinet needs one; only-PVC board ⇒
CRITICAL for a door needing 2mm; only-2mm board ⇒ CRITICAL for carcass fronts (Q3 default); `clean_kinds`/
`clean_colour` edge cases; `board_save` rejections; the warning text pin; an old job round-trips unchanged.

**Part A acceptance (live).** (1) Boards tab: tick/untick Has Edging shows/hides the kinds and name; save
rejects each invalid combination with a clear message. (2) Tick only 2mm on one board: a Doors edging dropdown
offers 2mm only, and its colour list shows only boards that offer 2mm. (3) Untick a board's Has Edging: its
name appears nowhere except the Boards tab; a cabinet needing its edging shows a red critical and export is
blocked. (4) Reload `Test.json` and `Test_Build.json`: identical to baseline. (5) Benchmark exact.

---------------------------------------------------------------------------------------------------

## PART B — One source for "which fields hold a board"

**Why.** Four hand-written lists of board-holding fields disagree today: `api.board_swap` (`:416`) moves only
carcass/exterior; `api.board_select` with `off` (`:385`) checks carcass/exterior/drawer boards only;
`boards.scan_jobs` misses back, door-leaf and edging boards; `api.rename_board_in_job` (`:243`) is the fullest.
So swapping or un-selecting a board can silently leave a cabinet pointing at a board the project no longer has.

- **B1** `Cabinet.board_refs()` → every board id a cabinet names, each with a label
  (`"door leaf 2 board"`, `"drawer 1 face board"` …): `carcass_board, exterior_board, back_board,
  drawer_carcass_board, drawer_face_board, door_boards[i], door_edge_board, drawer_edge_board`, each drawer's
  `box_board`/`face_board`, and (after D) the panel's board and edging board. Plus a mapper
  `Cabinet.map_board_refs(fn)` for rename/swap that rewrites via the same list.
- **B2** Rebuild `rename_board_in_job`, `board_swap`, `board_select(off)`, `boards.scan_jobs` and
  `validate._boards_and_tapes`' "chosen" list on `board_refs()`. Behaviour must not change except where a list
  was wrong; where it *was* wrong, say what it now catches.
- **B3 — Leaks: audited, verdicts.**
  - `Cabinet` defaults `"MEL"/"BROOKHILL"/"BACK"` (`model.py`): **leave** — frozen jobs and old files read
    them. Add a comment that they are legacy; make sure no *new* creation path relies on them (the UI's
    `blankCabinet` already sends blanks).
  - `model.MATERIALS` fallback: **leave** for jobs that carry no materials; verify every live path passes
    `job.materials` (grep `MATERIALS`).
  - `export_plaza.YIELD` / `RATES["cut"]` / `RATES["board"]`: already fall back by thickness/kind for unknown
    boards. **Leave**, and add a test that a new library board (e.g. `GREY`) gets non-zero yield, cut rate and
    price without an id entry.
  - `validate.ALLOWED_EDGE`: legacy allow-list; the dynamic set built from job materials already covers new
    boards. **Leave.**
  - `WHITE_EDGE`: Q5.
  - Door-leaf dropdown offering thin boards: A8.
- **B4 — Guard.** `tools/check_single_source.py`: by **reflection**, set every `str` field whose name ends in
  `_board` (and each item of `door_boards`, each drawer's boards) on a `Cabinet` to a sentinel and assert
  `board_refs()` reports it. A future board field that isn't added to the list fails this check.
- **B5 — Repair `check_library.py`.** Build its own in-memory library fixture (ids `MEL`, `BROOKHILL`, `BACK`)
  instead of reading the live `boards.json`, so Rudolf renaming a board never breaks it again. Then run it end
  to end — it has been silently not running since line 184. Report anything the newly-running checks find; do
  not "fix" a real finding without telling him.

**Part B acceptance.** Swap a board whose id is used only as a door-leaf board, only as a back board, only as a
drawer-face board: each is moved. Un-select a board used only as an edging colour: refused with the cabinet
named. `check_library` runs to the end. `snapshot.py --compare` identical.

**Stop after A + B. Rudolf tries it live.**

---------------------------------------------------------------------------------------------------

## PART C — Board colour in the drawings

**Goal.** Run, Wall and Plan show each cabinet in its real board colours — doors and drawer faces in their
own boards' colours, body in the carcass board's — with grain and legend, derived from the same fields the cut
list uses.

- **C1 Resolver.** One function in `render.py`: `board_look(job, board_id)` →
  `{colour, grain, picture}` from `job.materials` (`material_colour` → `NO_COLOUR` when blank). Every fill in
  the three drawings goes through it. **No colour literal for a board anywhere else.**
- **C2 `_interior` signature.** It currently takes `(c, x, y, w, h, scale, std, flip)` and has no access to
  materials. Add `materials`, keeping the no-room equality (`wall_elevation_svg` without a room `==`
  `elevation_svg`) true — `tools/check_elevation.py` asserts exactly that.
- **C3 Fills.** Door leaf *i* → `cab.door_board(i)`; drawer face → `cab.face_board_of(d)`; cabinet body →
  `carcass_board`. Replace `DOOR`/`FACE`/`LAYER_FILL` colours. (Reference constants at `render.py:18–24`,
  `:104`.)
- **C4 Layers by outline, not fill.** The base/wall/tall distinction used the fill; move it to the outline:
  base = normal stroke, wall = dashed outer stroke, tall = heavier stroke. Don't reuse the dashed style already
  used for shelf lines inside; check how the non-shown layers are dimmed in Wall so the new colours still
  read as "not this layer".
- **C5 Text stays readable.** Numbers, dimensions and `2 x 396` labels sit on coloured fills. Compute ink
  colour from the fill's relative luminance (server side, in `render.py`).
- **C6 Grain.** For boards with `grain == "grain"`, draw fine parallel lines in the direction the **cut list**
  gives: doors and drawer faces have `Length` vertical → vertical lines. Vertical on drawer faces is **correct
  and ruled** (Q4) — no legend note, no comment. Plain boards: no lines.
- **C7 Edging outline (optional but wanted).** Doors/faces get a thin outer stroke in the **edging board's**
  colour when they carry edging; none when the board has none (consistent with A7).
- **C8 Legend.** Under each drawing, one swatch per board used in that view: `id — name`, a grain mark for
  grained boards, and "no colour set" for boards with none. Wrap to a second line rather than truncate (the
  current `_tape_note` truncates with "…").
- **C9 Click-to-select.** Add `data-cab` to the cabinet group in **Run** and select that cabinet on click
  (Wall already selects on press — confirm, don't duplicate). Clicking must not start a drag in Run.
- **C10 Plan (last, optional).** Tint each footprint faintly with its exterior board colour without
  obscuring the number/labels. Skip if it fights the existing colours (clash red, gap fills).
- **C11** No new validation noise for colour (an unset colour is shown on the legend and the Boards table, not
  as a warning on every job).

**Part C acceptance.** `snapshot.py --compare baseline.json --allow svg` reports **only** drawings changed.
Live: set distinct colours on WHITEMEL/BROOKHILL/GREY → a cabinet with a Brookhill door and grey drawer faces
draws exactly that in Run and Wall, legend correct; Brookhill shows grain lines, WHITEMEL doesn't; change a
colour in the Boards tab → the drawings follow after the next compute; a job with unset colours is neutral
with "no colour set"; text legible on the darkest and lightest colours you can pick; Run click selects.
`check_elevation.py` passes.

**Stop after C.**

---------------------------------------------------------------------------------------------------

## PART D — Independent Panels

**Design decision (please follow):** a panel is a **`Cabinet` with `kind="panel"` and `template="panel"`**,
carrying a small `panel` record. Reasons: it reuses numbering (`store.next_number`), save/load, the cabinet
table, `Placement`, `generate_job` (one loop → cost, nesting, CSV for free) and `room.geometry`. A separate
list would need all of that rebuilt. The price is that every place that assumes "a cabinet is a box with
doors" needs a decision — D2 makes that explicit.

**D1 Model** (`model.py`, `store.py`).
- `Cabinet.template` gains `"panel"`; `kind` gains `"panel"` (also `api.defaults()["kinds"]`, `api.py:92`).
- New dataclass `PanelSpec`: `board: str`; `orientation: "upright" | "flat" | "end"`; `a: int`, `b: int` (the
  two extents named in D4); `grain_along: "a" | "b"` (only meaningful for grained boards); `edge_kind: str`
  (`""` = none); `edge_board: str` (`""` = the panel's own board); `edge_long: int` 0–2; `edge_short: int` 0–2;
  `anchor: Optional[str] = None` — **reserved, documented "nothing reads this yet"**.
- `Cabinet.panel: Optional[PanelSpec]`. Serialise like `drawers` in `store.py`
  (`cabinet_to_dict`/`cabinet_from_dict`, `_only_known`). A job with no panel cabinets writes and reads exactly
  as before.
- `Cabinet.is_panel` property. Declared `width/height/depth` of a panel are **labels only**; the table shows
  values from `geometry`, not the declared ones (hard rule 1).
- One panel per item: `qty` is always 1. Identical panels are a **Duplicate** (D8), each with its own number.

**D2 Audit every "cabinet" assumption.** Grep `job.cabinets`, `.cabinets`, `for c in`, and every
`template == "none"` site listed in Section 4. For **each hit record a decision — include panels / exclude
panels / handle specially** — in the commit message or a short table in the PR. Defaults: exclude panels from
`tape_legend`, `_boards_and_tapes`' cabinet checks, `_carcass_thickness`, structure/door/drawer/support checks,
the Run drawing, and `room.placed()`; include them in the cabinet table, Placements table, cut list, cost,
nesting, and (via `placed_panels`, E1) Wall and Plan. Don't rely on my list being complete.

**D3 Engine.** In `engine.generate_cabinet`, before the standard path: `if cab.template == "panel": return
[panel_of(cab, mats)]`. `panel_of` builds one `Panel(cabinet=cab.number, code=<Q2>, role="Panel", material=<board>,
length, width, qty=1, edge_l, edge_w, edge_material, grain, note=cab.note)`:
- Thickness `t` = `material_thickness(board)` (not `std.board_t` — a 3 mm panel is legal).
- **Length/width:** a grained board → `length` = the extent the grain runs along (`grain_along`), `width` = the
  other, `grain=1`. A plain board → `length` = the larger, `grain=0`.
- `edge_l`/`edge_w` = the long/short counts, but only if the board has edging and the kind is offered; else 0
  and no edge material. `edge_material = tape_for(mats, edge_board or board, edge_kind)`.
- The cut list is **derived**, never typed.

**D4 Editor.** Extend the *Size → Kind* dropdown (`SECTIONS`, `index.html:588`; options from
`api.defaults()["kinds"]`) with **Panel**. For `kind == "panel"`, `renderEditor` shows only **Size (number,
kind, note)** and **Panel design**; hide Outline, Structure, Doors, Drawers, Supports, Corner. Switching kind
**keeps data** both ways and never changes the number; switching a configured cabinet to Panel asks for
confirmation first (state what stays hidden but kept). `blankCabinet` (`index.html:335`) is unchanged. The
`template` value must be set with the kind (server-side in `api._job`/normaliser, not the browser guessing).
**Panel design** fields:
- **Board** — project boards; all thicknesses allowed.
- **Orientation** — three options with small inline-SVG icons and plain labels:
  *Upright, facing the room* (width along wall × height), *Flat (horizontal)* (width along wall × depth out
  from the wall), *Upright, side-on to the wall* (depth out × height). The two typed sizes are labelled per
  orientation. These are the **finished cut sizes**.
- **Grain runs along** — only for grained boards; the two named extents; default = height for upright/side-on,
  width for flat.
- **Edging** (only if the board has edging): kind (kinds the board offers), colour board (boards that offer
  that kind, default own board), *long edges banded 0/1/2*, *short edges banded 0/1/2* — one control, the same
  pattern as Doors/Drawers (`edgingHTML`).
- A one-line live preview of the cut-list line: `15 08 · BROOKHILL · 1200 × 300 · grain along length · 2mm
  BROOKHILL × 1 long`.

**D5 Geometry** (`room.geometry`, `:279`). New first branch: `if cab.is_panel`: derive from the generated
panel + `panel.orientation`, `source="panel"`:
- upright → footprint `(a × t)`, vertical extent `b`; flat → footprint `(a × b)`, vertical extent `t`;
  side-on → footprint `(t × a)` with `a` = depth, vertical extent `b`.
- `height` = vertical extent, `panel_depth` = out-from-wall extent, `panel_width` = along-wall extent,
  `door_widths=[]`, `runner=None`.
- `room.carcass_z(cab, p)` returns `p.z` for a panel (no leg lift); `stands_on_legs` is false.
- Never read `cab.width/height/depth` for a panel.

**D6 Validation** (panel-specific; new `_panels(job)` in `validate.py`):
CRITICAL — board missing/not in project; a size ≤ 0; a cut size that cannot fit a sheet (use whatever the
nester rejects); edging needed but not offered (`ref="EDGING"` — same pattern as A9). An **unplaced** panel is
**not** a warning (a cut-only panel is normal). Don't invent further thresholds.

**D7 Where panels appear.** Cabinet table: yes, kind "panel", W/H/D from geometry. **Run: no** (panels aren't
part of a cupboard run; keep `wall_elevation_svg(no room) == elevation_svg` true). Cut list/cost/nesting/CSV:
yes, automatically. Wall elevation, Plan, Placements: Part E.

**D8 Duplicate.** A **Duplicate** button on a panel: new number from `next_number`, all fields copied,
placement not copied. (Bulkheads are several panels; typing five by hand is the pain.)

**D9 Tests / fixtures.** `jobs/Test_Panels.json` (new): one panel per orientation, one grained, one plain, one
with edging, one board with no edging, one thin board. `tools/check_panels.py`: cut list line per panel
(number, code, size, grain flag, edge material), designation unchanged after a kind round-trip, geometry per
orientation, criticals, **a job with no panel cabinets is byte-identical to baseline**, `generate_job` still
read-only.

**Part D acceptance (live).** Kind → Panel on a new cabinet: lower sections swap to Panel design. Type
1200 × 300, Brookhill, grain along length, one long edge 2mm: the cut list shows `<n>08`, 1200 × 300, grain
locked, edging correct; numbering continues the cabinet series; untick Has Edging on the board → the edging
control disappears and the cut list shows no edging, or a critical if one is still requested. Kind back to
Base → the cabinet's old design reappears untouched. Benchmark exact; snapshot identical for the three jobs.

---------------------------------------------------------------------------------------------------

## PART E — Placing panels

**Goal.** Put a panel on a wall — including standing off it — precisely, with snapping, without touching
cabinets' behaviour.

- **E1 Model and choke point.** `Placement` gains `y: int = 0` (out-from-wall distance to the panel's back
  face; 0 = against the wall) — cabinets keep 0 and are unaffected. Serialise `y` **only when non-zero**, so old
  files load unchanged and cabinet placements round-trip byte-identical. **Keep `room.placed()`
  cabinet-only** (make it skip `is_panel` explicitly) so gaps, runs, plinth, tip-up, door swing and fillers are
  untouched; add **`room.placed_panels(job)`** returning `(cab, placement)`. Meaning of `x, y, z` per
  orientation: `x` = left edge along the wall; `y` = out from the wall to the panel's back face; `z` = bottom
  edge (for a flat panel, its underside). `to_world` already takes `y`.
- **E2 Placements table** (Room tab, `renderPlaces`, `:2258`): panels listed with the same columns plus **Y**.
  Typed numeric entry is the reliable path and ships first.
- **E3 Wall elevation:** draw placed panels (`.epanel`, board colour, grain lines, number + size label),
  draggable in x and z with the same snapping machinery: extend `room.snap_points` (`:652`) and
  `z_snap_points` (`:700`) so a panel snaps to wall ends, cabinet edges, floor, ceiling, **cabinet tops (for
  bulkheads)** and other panels. The drag API (`api.drag`, `:814`) accepts a panel number; a drag writes only
  a placement.
  Panels get their own **"Panels" layer toggle** beside base/wall/tall (`renderLayers`, `index.html:2084`;
  `room.LAYERS` stays the three cabinet layers — `layer_of` is not used for panels).
- **E4 Grab area.** A 16 mm panel is ~4 px wide at typical scale. Draw an invisible hit rectangle at least
  ~16 px wide/tall around each thin panel, with `pointer-events` on it, so it can actually be picked.
- **E5 Plan:** draw panel footprints as thin coloured rectangles with the number; `y` is visible here. Dragging
  in Plan is optional (numeric first).
- **E6 Clashes (WARNING, not critical):** a panel whose box intersects a cabinet, another panel, or a
  wall opening — reuse `_z_span`/`polygons_overlap` (`room.py:604`, `:422`). Panels do not take part in gaps,
  runs, plinth or tip-up checks (deferred, Section 8).
- **E7 Tests:** `check_room.py`-style: `placed()` unchanged with panels present (same cabinets, same order);
  a wall-mounted bulkhead set (upright + flat + two end caps, each its own number) round-trips through
  save/load; snapping targets; a cabinet's tip-up/door-swing results identical with and without panels in the
  job.

**Part E acceptance (live).** Build a bulkhead over the Wall A cabinets from four panels; drag the front panel
along and up so it snaps flush to the cabinet tops and the wall end; set `y` on the underside panel so it
projects; the Placements table shows the same numbers; a deliberate overlap shows the WARNING; cabinets'
drag and snap behave exactly as before; benchmark and snapshot unchanged.

**Stop after D + E.**

---------------------------------------------------------------------------------------------------

## PART F — 3D view

**Rule:** the 3D scene is a **drawing**. It never feeds a check, it computes no dimension in the browser, and
all trig stays in `room.py`.

- **F1 Vendoring and static route.** Download `three@0.186.0` (`three.module.js`, `three.core.js`,
  `examples/jsm/controls/OrbitControls.js`, `LICENSE`) into `app/vendor/`, committed to the repo, **no CDN**.
  Add to `Handler.do_GET` a route `/vendor/<file>`: whitelist by filename, resolve the real path and require it
  to be inside `app/vendor/`, serve `text/javascript` (LICENSE as `text/plain`), `Cache-Control: no-store` like
  the rest. Import map in `index.html`: `three` → `/vendor/three.module.js`; addons → `/vendor/`. **Acceptance:**
  the network log shows only `localhost` requests; blocking the internet changes nothing.
- **F2 `cabinetgen/assembly.py`.** Panel → box, in the cabinet's frame (x along the wall from the left edge, y
  out, z up from the underside): `boxes_for(cab, std, materials) -> List[Box]`, `Box(label, role, board,
  x0,y0,z0,x1,y1,z1, provenance)`. Imported by nothing but the scene API and its checks.
  - **Derived from rules the engine already has** (`provenance="placed"`): sides at both ends full height;
    top/bottom; back at `Standard.back_face_from_front(d)` (16 mm cavity + 3 mm board); doors at the front
    face (leaf width from the door panels, hinge side from `model.hinge_side`, flipped by `Placement.flip`).
  - **Positions no data defines** (`provenance="indicative"`): shelf heights (spread evenly, the way
    `render._interior` already draws them), support positions, drawer-box depth position. Do **not** invent new
    dimension constants; the UI marks these parts (e.g. an "indicative" legend and a toggle).
  - **Corner units and `template="none"` cabinets:** v1 draws the **extruded footprint** from
    `room.geometry().footprint` (translucent, labelled "simplified"), not individual panels.
  - Panel items: one box each from D5 geometry, with `t` thickness.
- **F3 `/api/scene`** (`api.py` `ROUTES`): for each placed cabinet and panel, world-space boxes via
  `room.to_world` — send `origin` (min corner) + three world axis unit vectors + three sizes, so the browser
  builds a `BoxGeometry` and a basis from them and does **no trig**. Also the room: floor, wall slabs from
  `room.wall_frames` (`:103`) and corner offsets, ceiling height. Per box: label, role, board, `colour`
  (from `board_look`), `grain`, and the cabinet number (so a click can find the cut-list line).
- **F4 UI.** New **3D** tab. OrbitControls (orbit/pan/zoom), Fit, Front/Top/Isometric presets, layer toggles
  (base / wall / tall / panels), **door open/closed** toggle (each leaf rotates ~95° about its hinge edge), edge
  outlines for legibility, selection: **click a part → highlight, and show its cut-list line** (designation,
  role, board, size, edging) and select that cabinet in the editor. Colours come from the Boards record.
  Board `picture`, if a **data URI**, can be a texture; a bare filesystem path cannot be loaded by the browser
  — say so rather than failing silently.
- **F5 Tests.** `tools/check_assembly.py`: every box's extents equal its panel's size (± thickness rule);
  carcass boxes' bounding box equals `room.geometry(cab)` footprint and height for every template cabinet in
  all three jobs (this catches assembly mistakes against the engine); box volume sum equals panel area × board
  thickness for placed boxes; nothing in `validate.py`/`room.py` imports `assembly` (grep-test, enforces "a
  drawing never feeds a check"); scene JSON for the Oct job has the right box counts.

**Part F acceptance (live).** Open 3D on `Test.json`: orbit/pan/zoom work in the app window; Fit and presets
work; toggling door open swings leaves about their hinge side; click a door → its cut-list line and cabinet
selected; a wall unit hangs at its z; panels (from `Test_Panels.json`) appear at their placements and offsets;
colours match the drawings; nothing requests a remote URL; the scene loads in a reasonable time on the Oct
wardrobe (~360 panels); Wall/Run/Plan and every check unchanged.

---------------------------------------------------------------------------------------------------

## 5. Verification protocol (applies after every part)

1. `python tools/regen_check.py` — **272 MEL / 59 DECOR / 30 BACK, 92 pot holes, 18/9/6 boards,
   ~R28,363.50**. (Its comparison with the real cut-list xlsx is skipped if the file isn't present; say so.)
2. Every `tools/check_*.py` passes, including the new ones. `check_library` must run to the end (B5).
3. `python tools/snapshot.py --compare baseline.json` — **identical** after A, B, D (for the three existing
   jobs), E, F; **only drawings** after C (`--allow svg`). Any other difference is a bug until proven
   intended.
4. `Check It Still Works.bat` (real Python + openpyxl).
5. **Drive the real UI**, not just the Python: the part's live acceptance list above. Screenshot the result of
   each. Report **per ID: pass / fail / not tested**.
6. Save/load round trip on `Test_Panels.json` and an old job: reload gives identical panels.

## 6. Where things are (starting points, not a substitute for reading)

- `app/index.html` (~2760 lines): state `S` `:293`; `compute` `:367`; `renderElevation` `:426`; `SECTIONS`
  `:585`; `renderEditor` `:712` (input handler ~`:743–830`: `data-dboard`, `data-edge`/`data-ek`, `data-k`);
  `renderDoors` `:975`; `renderDrawers` `:1069`; `boardSel` `:1267`; `edgingHTML` `:1285`;
  `renderStructure` `:1318`; `refreshEdging` `:1375`; Boards tab `drawBoards` `:1412`, `drawBoardEditor`
  `:1495`; elevation handlers `.fdiv`/`.ecabg` `~:1776–1980`; `renderRoom` `:1999`; `renderPlaces` `:2258`.
- `cabinetgen/render.py`: constants `:18–24`; `tape_legend` `:27`; `elevation_svg` `:63`; `LAYER_FILL` `:104`;
  `wall_elevation_svg` `:177`; `plan_svg` `:375`; `_interior` `:696`.
- `cabinetgen/room.py`: `to_world` `:148`; `geometry` `:279`; `layer_of` `:447`; `placed` `:484`;
  `overlaps` `:609`; `snap_points` `:652`; `z_snap_points` `:700`; `runs` `:1027`; `carcass_z` `:1151`;
  `gaps` `:1333`.
- `cabinetgen/model.py`: `CODES` `:10`; `tape_for` `:136`; `Panel` `:176`; `WHITE_EDGE` `:245`; `Cabinet`
  `:249`; `Placement` `:608`; `Job` `:657`. `engine.py`: `generate_cabinet` `:17`; `generate_job` `:287`.
  `store.py`: `next_number` `:124`. `api.py`: `compute` `:533`; `drag` `:814`; `board_*` `:213–470`;
  `ROUTES` `:872`; `Handler` `:901`.

## 7. Docs to update (at each clean stop)

- `CLAUDE.md`: Status (what's done); the new open items; and — **if Rudolf agrees** — hard rules H5/H6.
- `docs/ROOM-LAYOUT-SPEC.md`: add **Panels** (model, geometry, placement, `y`) and rewrite **Phase 6 (3D)**
  with what F actually built (vendoring, `/vendor/`, `assembly.py`, `/api/scene`, indicative parts).
- `README.md` if it lists checks or tabs. Add `tools/check_edging.py`, `check_single_source.py`,
  `check_panels.py`, `check_assembly.py`, `snapshot.py` wherever checks are listed (and to
  `Check It Still Works.bat` if it enumerates them).
- Save a short summary of each stop as a doc in the Project (`claude/…`).

## 8. Deferred — do not build now

- Panels following a cabinet (the `anchor` seam only).
- A "match neighbour" size helper.
- Panels taking part in gap/run/plinth/tip-up logic — including a placed panel counting as the *treatment*
  of a gap between cabinets.
- Individual-panel 3D for corner units and bespoke cabinets.
- Textures beyond a data-URI `picture`.
- Any change to `offset_depth`, codes 10/11, appliances, worktops, bespoke shapes, Phase 7 CAD export.
- Changing drawer-face cut orientation (Q4).

---------------------------------------------------------------------------------------------------

## Appendix 1 — Reference implementation of the data layer (tested, not applied)

`Claude outputs/reference-data-layer.patch` (attached; unified diff against the current working tree with line endings
stripped, so it is a **reference to port by hand**, not something to `git apply` onto CRLF files). It touches
`cabinetgen/boards.py`, `cabinetgen/model.py`, `cabinetgen/validate.py`, `app/api.py` and implements A1, A4,
A5, A9 and the model helpers. Tested in a scratch copy:

- `snapshot.py` on the three jobs is **identical** to the untouched tree (panels, issues, totals, drawings).
- `check_boards.py` ALL OK (after restoring the original warning wording — see A9).
- Behaviours confirmed: PVC-only board → CRITICAL for a door needing 2mm, message names the board and the
  kind; Has Edging off → `tape_for` empty and CRITICALs for carcass fronts and drawer boxes.

Not in the patch: the whole browser side (A2, A3, A6, A7, A8), B, and everything after A.

## Appendix 2 — `tools/snapshot.py`

Attached as `Claude outputs/snapshot.py`. Copy it to `tools/snapshot.py` (it finds the repo from its own location). `--out baseline.json` on the untouched tree, `--compare baseline.json` after each
part, `--allow svg` for Part C. It keys every panel by designation + role + occurrence so two lines with the
same designation are both kept, and it exits non-zero on any difference not named by `--allow`.

## Appendix 3 — What I verified vs what is judgement

- **Verified in code:** the data flow in Section 4; the `check_elevation` pin (equality only); `placed()` as
  the choke point; `to_world` taking `y`; the `template == "none"` sites; `Job.loose`/`next_number`;
  `Handler.do_GET` having no static route; the three.js file set; the `check_library` abort at line 184;
  the benchmark numbers on the untouched tree.
- **Judgement, challenge it:** the `Cabinet(kind="panel", template="panel")` route (chosen over a separate
  list to reuse numbering/placement/engine); three orientations named `upright/flat/end`; the layer-by-outline
  scheme in C4; "simplified" corner units in 3D; the thin-board threshold reusing `≤ 3`.
