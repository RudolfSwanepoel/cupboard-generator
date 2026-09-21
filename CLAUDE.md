# CupboardApp — working notes for Claude Code

A cut-list generator for melamine kitchens and wardrobes. Rudolf designs the
cabinets; the app produces the panel list, validates it, nests it, and exports
the files Plazaboard cuts from.

## The one rule that matters

**Every dimension comes from `cabinetgen/standard.py`.** If you find yourself
typing a number into a formula anywhere else, stop — it belongs in `Standard`,
or on the `Cabinet` if it genuinely varies per cabinet. Three earlier jobs were
built by hand and eleven "constants" turned out to differ between them. That is
the failure this app exists to prevent.

## Check before you commit

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
python tools/snapshot.py --compare baseline.json
```

Regenerates the October 2025 wardrobe from cabinet definitions and diffs it
against the cut list that was really sent to Plazaboard. Current state:

- 22 of 30 cabinets reproduce exactly
- 272 MEL / 59 DECOR / 30 BACK panels — matches the real job exactly
- 92 pot holes — matches the invoice exactly
- board counts from the nester: 18 / 9 / 6 — matches the invoice exactly
- estimated cost within R41 of the R28,322.75 actually quoted (R28,363.50)

If a change drops the clean-cabinet count or moves the cost estimate, it broke
something. The eight cabinets that do not reproduce are listed in `KNOWN` in
that script, each tied to a logged finding — those differences are correct.

## Status

**Part A (boards record and edging), Part B (one source for which fields hold
a board) and Part C (board colour in the drawings) are built and checked.**
Against the brief in `Claude outputs/claude-code-brief-boards-colour-panels-3d-2026-09-20.md`:

- **A** — `has_edging`, `edging_kinds` and `colour` are fields on `Board`; the
  Boards form owns them; every edging control and every piece of edging text
  follows them. No edging name is stated anywhere but the Boards record.
- **B** — `Cabinet._board_slots` is the one list of which fields hold a board, and
  the swap, the un-select, the library scan and the validator all read it.
- **C** — every fill in the run, the wall elevations and the plan is the colour of
  the board that part is cut from, through `render.board_look`. See
  **Drawings** below.

Since then, and not in the brief: support rows carry a per-row **Cut from**
board; a swap moves every panel; the editors refresh themselves; deleting a
project moves its files to `jobs/_deleted/`; grain is shown in the swap step
and on the cut list.

**Part D (independent panels) is complete — D1 to D9, every one passing, and
exercised in the running app rather than only in Python.** Kind → Panel swaps
the cupboard sections for Panel design and says what stops being cut first; all
three orientations relabel their two extents and give the right geometry; a
board, an edging kind and the banded-edge counts produce the cut-list line the
engine derives, preview and all; Duplicate gives the next free number and copies
everything but the placement; and `jobs/Test_Panels.json` loads, edits and saves
back **byte-identical**. See **Panels** below.

**Part E (placing panels) is complete — E1 to E9, and exercised in the running
app rather than only in Python.** A panel has a place in the room: `Placement.y`,
`room.placed_panels`, the Placements table's Y column, panels drawn in the wall
elevation and the plan, the drag and every snap target it needs — cabinet tops
included, which is what a bulkhead lands on — the fat invisible hit area a 16 mm
panel needs to be grabbable at all, the Panels layer toggle, and the clash
WARNING. See **Placing a panel** below.

**Three things were decided beyond the brief** (21 September 2026, with Rudolf):
the layer toggle is **multi-select** rather than one radio (E3b), a newly-placed
cabinet or panel gets a **default position clear of what is already on that wall**
rather than 0 mm (E8), and the wall elevation and the plan take **scroll-wheel
zoom** (E9).

**Next: Part F (3D). It is not started.**

Also done since Part C, and not in the brief:

- **The editor no longer rebuilds its controls on every compute.** Dropdowns
  twitched because every `<select>` was destroyed and remade after each compute,
  and a drawer cabinet sitting untouched on screen computed about three times a
  second for ever (12 computes and 13 drawer-solves per 4 seconds, measured),
  lighting the unsaved-changes marker on a job nobody had edited. The editor is
  still rebuilt from the job every time — it has to be — but the HTML is now
  applied to the DOM that is already there, and a focused control is never
  touched. The cabinet table is painted the same way. See **The UI**.
- **The pre-library checks read a frozen fixture, not a live job.** Three checks
  pinned "a job written before the library still names DECOR" against
  `jobs/Test_Build.json`, and upgrading that job in the Boards tab broke all
  three. They read `tools/fixtures/Test_Build_pre_library.json` now. The one
  half still asked of the live folder, on purpose, is whether `jobs/` is
  readable. See **One source for "which fields hold a board"**.

**The benchmark held through all of it**, and is what says so: 272 MEL /
59 BROOKHILL / 30 BACK panels, 92 pot holes, 18 / 9 / 6 boards, R28,363.50,
`snapshot.py --compare` identical on all three fixed jobs, and every
`tools/check_*.py` green.

Open questions from the brief that Rudolf has not ruled: **Q1** line endings
and git hygiene (the working tree is CRLF, HEAD is LF; edit without changing a
file's existing endings and review with `--ignore-space-at-eol`), **Q5**
`WHITE_EDGE`. **Q2 is ruled: a panel takes code 08 with the role "Panel"**
(20 September 2026) — Plazaboard's CSV writes the Component column from
`Panel.label` alone, so a new code would need their sign-off and would say
nothing on the order that 08 does not. **Q3 is ruled: carcass-front edging the
exterior board does not offer is a CRITICAL.** **Q4 is ruled: drawer-face grain runs vertical, up
the face height, exactly as the cut list has it. Never question it.** The
proposed hard rules H5 and H6 are not in this file yet because they are his to
accept; Part C was built as though they hold.

## Drawings

**A drawing is a read-only view of the model. Nothing reads one back.** The
colours, the grain lines and the legend are output; no check, no cut list and
no validation derives anything from them.

**Every fill is the colour of the board that part is cut from**, resolved
through the one function `render.board_look(job, board_id)` — colour, grain
and picture off `Job.materials`, and nothing else. There is no colour literal
for a board anywhere in `render.py`; `tools/check_colour.py` fails on one. A
door leaf is `Cabinet.door_board(i)`, a drawer face `face_board_of(d)`, a
carcass body `carcass_board`, a plan footprint `exterior_board` — the same
resolvers the engine cuts from, so the paper and the cut list cannot disagree.
A board nobody has coloured draws neutral (`model.NO_COLOUR`) and the legend
says "no colour set". That is never a warning: a colour changes no cut.

**Base, wall and tall are in the outline, not the fill** (20 September 2026).
The fill was carrying the layer and now carries the board, so: base a normal
stroke, wall dashed, tall heavier. The dash is `7 4`, deliberately not the
`4 3` the shelf lines and openings use. The plan keeps its own `5 3` for a wall
unit — the kitchen convention it always drew, pinned in `check_room.py`. A
clash is still red and heavy, and keeps its layer's dash.

**Ink is computed, never stated.** A board colour is picked for the board, not
for the numbers that land on it, so `render.ink_on(fill)` takes whichever of
the dark ink and white gives the better contrast ratio, and `muted_on(fill)`
keeps the secondary text a step quieter without letting it vanish — a fixed
grey on a mid grey board was 1.04:1. Both clear 3:1 on every fill.

**Grain lines run the way the cut list cuts them.** `Length` is the grain
direction, and doors and drawer faces are both cut with `Length` up the front,
so both draw vertical lines. **Vertical on a drawer face is correct** (ruled 20
September 2026) — no note on the drawing, no change to the cut list, and never
raise it again. A plain board draws none.

**Only a hex value reaches an SVG fill.** A job file is a text file somebody
can edit, and a fill is written into the drawing as it stands, so `board_look`
puts every colour through `render._hex` and falls back to neutral.

**The run selects, it does not drag.** Its cabinets carry `data-cab` in a
`g.ecabg.erun`; there is no wall to move along, so a press selects the cabinet
and starts nothing. The run still ignores placements — it is the cabinet list
drawn side by side, not a view of the room.

## Layout

```
cabinetgen/standard.py     every construction constant. Start here.
cabinetgen/boards.py       the board library: load, save, tape names, job usage
boards.json                the library itself, shared through the repo
cabinetgen/model.py        Panel, Drawer, Cabinet, Job
cabinetgen/engine.py       cabinet -> panels
cabinetgen/drawers.py      drawer stacks: equal, graduated, pinned or exact
cabinetgen/validate.py     criticals block export, warnings do not
cabinetgen/nest.py         guillotine nesting + sheet layout SVGs
cabinetgen/render.py       SVG drawings: side-by-side elevation, plan, per-wall elevations
cabinetgen/room.py         walls, corners, to_world. The only trigonometry.
cabinetgen/store.py        job files: JSON save / load
cabinetgen/export_plaza.py Plazaboard CSV + costing off the real rate card
run_app.py                 starts the local server, opens the window
app/api.py                 request handlers. Thin — they call cabinetgen.
app/index.html             the whole UI. Vanilla JS, no build step.
jobs/                      job definitions. wardrobe_oct2025.py is the fixture.
                           Test_Panels.json is the panel fixture.
tools/regen_check.py       the regression check above
tools/check_examples.py    verifies the worked examples in docstrings are true
tools/check_room.py        room geometry: closure, corners, to_world
tools/check_fillers.py     gap detection, taper, scribe, filler panels
tools/check_plinth.py      runs, butt joints, long-run splits, plinth panels
tools/check_drag.py        overlaps, snap targets, door swings, pull-outs
tools/check_elevation.py   per-wall elevations: chains close, plinth heights, hinges
tools/check_edging.py      Has Edging, the kinds a board offers, its colour
tools/check_single_source.py  the one list of which cabinet fields hold a board
tools/check_swap.py        a swap moves every use of a board, and says what it does
tools/check_colour.py      board colour in the drawings, and the ink that reads on it
tools/check_panels.py      independent panels: the line they cut, and what they stay out of
tools/fixtures/            frozen job files the checks read. Never reachable from the app.
tools/snapshot.py          every panel, issue, cost and drawing hash, for --compare
docs/RULES.md             where each rule came from and what it cost to learn
docs/ROOM-LAYOUT-SPEC.md  the room / plan / 3D build spec and its phasing
```

## Conventions

- All dimensions in mm, integers. No floats in panel sizes.
- `Length` is the larger dimension on grain-free panels; on décor it is the grain
  direction and must not be swapped.
- Panel codes follow Plazaboard's scheme. `09` (divider) is ours — the old lists
  coded the same part as `08` in some cabinets and `99` in others.
- A designation must never sit on two different panels, and **a designation
  never changes** (ruled 14 September 2026). Generated panels are named as they
  are created — `engine.born_distinct` gives 105a / 105b where one code covers
  two sizes — and nothing is renamed afterwards. `generate_job` is read-only
  with respect to the job: a bespoke or loose panel goes onto the cut list
  exactly as the job defines it, so a bespoke cabinet with two sides of
  different sizes must define them as 01a and 01b itself. The D13 warning is
  what tells you it did not; the fix is in the job, never in the generator.
- **Two tickboxes gate a section: "Corner unit" and "Has drawers".** Both are
  tri-state on the `Cabinet` — `corner_unit` / `has_drawers`, `None` meaning
  "derive it from what is stored", which is how every job written before them
  reads. Unticking sets `False` and **keeps every value**: the drawer stack and
  the four corner measurements stay in the job file untouched, so re-ticking
  restores the cabinet panel for panel. `Cabinet.corner_on` and
  `Cabinet.drawer_list` are what everything downstream reads; nothing reads
  `corner_style` or `drawers` directly any more.
  Unticking can take panels off the cut list, and that is never silent:
  `/api/what-if` is asked first and names the designations that would go. A
  designation is only ever removed — never renamed, never reused.
- Bespoke cabinets set `template="none"` and supply `bespoke=[Panel(...)]`.
  The corner unit and the overhead are both like this — do not try to
  generalise a template to fit them.
- **Declared width, height and depth are inputs to panel generation and labels
  for display. No geometric check reads them.** Every check reads
  `room.geometry(cab)`, which reads the panel set — sides for height and depth,
  top or bottom for width, door panels for the swing, drawer sides for the
  pull-out — and the cabinet's `footprint` outline. The corner unit declares
  500 deep and has an 834 side; a check on the declared figure is wrong in the
  unsafe direction. See "Geometry" below.

## Boards, tapes and grain

**`boards.json` in the repo is the board library.** It is shared through git, so
both machines see the same boards. `cabinetgen/boards.py` loads and saves it, and
the Boards tab is where boards are added, edited and ticked into a project. Each
record is a name, a tape token, a thickness, Grain or Plain, a last price, an
optional picture, whether it has edging and which kinds it offers, and its
colour. Every one of those is stated there and nowhere else.

**A project selects from the library, and selecting copies the record into the
job.** `Job.boards` is the selection; `Job.materials[id]` is the copy. That copy
is the price capture — see below — and it is why editing a board never reaches a
job that has already been quoted. `Job.board_ids` falls back to the keys of
`materials`, so every job written before the library still names its boards.

**Nothing can be cut until a board is selected.** A job with cabinets and no
boards is a critical naming what is missing, and the UI refuses to add a cabinet
and sends you to the Boards tab. Above `validate.BOARD_GUIDELINE` (5) it warns
and does no more: every extra board is another part sheet and another offcut
pile, which is a guideline about cost and complexity, not a limit.

**A board on the cut list that the project never selected is a critical.** An
unpriced board quotes at R0 while the total still looks like a number, which is
the worst way to be wrong, so it blocks.

**A board's id is editable, and changing it renames the board** (18 September
2026). The id is the material name on every panel cut from it, so it is upper
case, alphanumeric and short — `api.clean_board_id` shapes a typed one exactly as
`boards.next_id` shapes a generated one. A SAVED job keeps its own copy under the
id it was quoted with and does not move; the reply names those jobs. The project
open on screen does come along (`api.rename_board_in_job`), and is named in a
confirm before anything is written. No panel designation changes: a panel keeps
its name and changes what it is cut from. `DECOR` was renamed `BROOKHILL` this
way; `jobs/Test*.json` still say `DECOR` on disk and still price exactly as
before, which is the price capture doing its job.

**A former id keeps resolving: `model.BOARD_ALIASES`** (`{"DECOR": "BROOKHILL"}`).
`Cabinet.exterior_board` and the house `MATERIALS` say `BROOKHILL`, but the
frozen October fixture names `DECOR` literally on its bespoke and loose panels
while its template cabinets take the default. Without the alias those would be
two boards on two sheet piles and the 9-board benchmark breaks. `resolve_board`
maps an id the job does not carry onto the other name it does, either way round,
and the engine resolves every panel's board through it (bespoke and loose panels
as copies — the job is never touched). The benchmark therefore prints
`59 BROOKHILL`; the numbers are the October job's exactly. Do not "tidy" DECOR
out of the alias map, `YIELD` or `RATES["cut"]`.

Opening a saved job in the UI (`api.upgrade_former_ids`) shows a former id under
the current one **only when the job never captured a price for it** — a
pre-library bare-string record, like both Test files. A captured record keeps its
old id. The file on disk is untouched until saved, and a toast says so. The
Boards tab lists `Test.json (as DECOR)` against BROOKHILL, and refuses to delete a
board a saved job uses under a former id.

**The library's BROOKHILL edging token is `BROOKHILL`, deliberately** (ruled 18
September 2026). New cabinets generate `2mm BROOKHILL` / `PVC BROOKHILL`. The
October job's `PVC WOOD` / `2mm WOOD` are what that one order was edged with,
kept because that job is frozen — not a catalogue name to steer new jobs towards.

**Yield and cut rate are read off what a board IS, not off its id.** Both used to
be dicts keyed `MEL` / `DECOR` / `BACK`, so a renamed or newly added board fell to
a house-average yield and — worse — a cutting charge of R0. `export_plaza.cut_rate`
goes by thickness (the masonite saw takes the 3 mm, the beam saw the rest) and
`board_yield` by grain and thickness, with the three original ids still pinned to
their measured figures so the October benchmark does not move.

### The boards on a cabinet

The three chosen in **Structure**, which everything else falls back to:

- `carcass_board` — sides (01), top (02), bottom (03), supports (04), shelves
  (05), dividers (09), and the plinth board that covers its legs.
- `exterior_board` — doors (07), drawer faces (20), exposed end panels (08).
- `back_board` — the backing panel (06), and the drawer base (17) when it is the
  grooved 3 mm one, because that is the same thin sheet.

And four more, each `None` for "follow Structure" (18 September 2026), so every
job written before them cuts exactly what it was quoted:

- `drawer_carcass_board` — drawer sides (18), fronts (19) and a **housed 16 mm**
  base (17). Follows `carcass_board`.
- `drawer_face_board` — drawer faces (20). Follows `exterior_board`.
- `Drawer.box_board` / `Drawer.face_board` — **per drawer** (18 September 2026),
  so one drawer in a stack can take a different finish. `None` follows the two
  cabinet-level fields above, which follow Structure. This is what the editor
  sets now — one column each in the drawer table; the cabinet-level pair is no
  longer offered in the UI and is only read as a fallback from older job files.
  The engine groups drawers by board as well as size, so an odd drawer comes out
  as its own line (`418a` / `418b`), and its box PVC follows its own box board.
- `door_boards[i]` — one per leaf, `""` for the exterior board. Two leaves cut
  from different boards come out as two cut-list lines, told apart by
  `born_distinct` because the material is part of the signature it reads
  (`107a` / `107b`).

**The back board is chosen, not reached for.** The engine used to type `"BACK"`
onto the backing panel, so a project could cut a board it had never selected and
quote it at R0 with a plausible-looking total. It is a third dropdown off the
project's boards now. The default is `"BACK"` — the board the engine always
reached for — so every job written before this names the board it was already
using and nothing moves.

It is only asked for when something is actually cut from it
(`Cabinet.needs_back_board`: a back, or a drawer on a grooved base). A cabinet
with neither is not nagged for one, and the editor says why rather than showing
an empty dropdown. The stored value is kept when the section hides, the same
discipline as the tickboxes.

Drawer box sides and fronts (18, 19) and the housed 16 mm base (17) used to be
hardcoded `MEL` in the engine whatever the cabinet was cut from, and all the
validator could do was ask about it. They are a chosen board now, defaulting to
the carcass, so the box and its edging agree by construction and the warning is
gone. A board swap moves them with the carcass, which is why
`check_library.py`'s swap figures are 102 panels and 3 MEL boards, not 101 and 4.

### Every board attribute is stated on the Boards record

**Ruled 20 September 2026.** A board says whether it has edging at all, which of
PVC / 1mm / 2mm it offers, and what colour it is, and nothing downstream states
one. `Board.has_edging`, `Board.edging_kinds` and `Board.colour` are real fields;
`Board.offered` is the kinds in force, and `tape_name` / `model.tape_for` return
`""` for a kind the board does not offer rather than generating a name it will
never sell.

**The legacy rule is what keeps the benchmark still.** A record carrying neither
key reads as edged with all three — which is what every job quoted before the
tickbox was quoted with — so old jobs and the frozen October fixture do not move.
The same holds for `Job.materials` copies. `tools/check_edging.py` pins it.

**Unticking keeps data**, the same discipline as "Has doors" and "Has drawers":
Has Edging off keeps the kinds and the edging name in the file and merely stops
anything reading them.

**A needed edging the board does not offer is a CRITICAL**, tagged `EDGING`,
naming the cabinet, the board, the kind and what to tick. It blocks the export.
This bites in one place by design: carcass fronts are PVC in the **exterior**
board's colour, so an exterior board ticked 2mm-only leaves them with no offered
edging. That is the rule working, not a bug — the per-cabinet `carcass_edge`
override is the escape hatch. A missing edging *name* stays a WARNING with its
wording unchanged (`check_boards.py` pins the phrase "no name to build edging
from"); the two are different faults. A cabinet named by an `EDGING` critical
does not also collect the per-panel "edges specified but no edge material"
critical — one problem, one message.

**Colour is picked on the Boards tab and nowhere else.** `model.NO_COLOUR`
(`#d9d6cf`) is what a board nobody has coloured draws as, and the legend says
"no colour set" rather than guessing a finish. An unset colour is never a
warning.

**A 3 mm sheet is not something to build from.** `model.is_thin` uses the
threshold `export_plaza.cut_rate` already sorts by, so the dropdowns and the
costing cannot disagree about what a thin board is. The carcass, exterior,
door-leaf, drawer-face and drawer-box dropdowns exclude thin boards; the backing
dropdown lists only thin ones. A stored value that breaks the rule is kept,
flagged in the editor, and named by `validate._thin_boards`.

**No hardcoded edging anywhere, including supports** (ruled 20 September 2026).
A support row names a board — any board the project has selected — and one of
the kinds that board offers: `Support.board` and `Support.kind`. Both blank means
the row predates the control, and it is then read from its old `edge` and edged
exactly as that job was quoted: front-edged takes the carcass edging, and
white-edged resolves through `model.white_edge_board` — the project's board whose
PVC token is WHITE — rather than through a constant. `model.WHITE_EDGE` survives
only as the fallback when the project has no such board. `Test.json` cabinet 7 is
the case that proves it: a GREY carcass with three white-edged rows, which still
come out `PVC WHITE`. `board` and `kind` are written to the job file only when a
row actually names them, so a file saved before the control round-trips byte for
byte.

### A support row: cut from, and edged in

**Ruled 20 September 2026.** A support row asks two separate questions and they
used to be one. `Support.cut_board` is what the rail is **cut from** — any board
the project carries, blank meaning the carcass board, which is what the engine
has always cut a support from. `Support.board` is only the **edging colour**, and
`Support.kind` the edging kind. Before this the single Board column set the
colour alone, so picking the white board to get a white edge read as asking for a
white rail, and did not give one.

The rail carries its own board's **grain**, so a support cut from the grained
board locks like every other panel off it.

**Defaults:** the edging kind lists only what the colour board offers; the colour
list only boards that offer the chosen kind; and a new row's colour follows the
board it is cut from — its own edging.

**Migration, output unchanged.** A row with nothing stored is read from its old
`edge`: cut from the carcass board, and **front-edged takes the exterior board's
colour** (PVC in the exterior colour, the 14 September rule), **white-edged takes
the project board that yields `PVC WHITE`** via `white_edge_board`, and **none
stays none**. The October job and both Test files are byte-identical through it —
`snapshot.py --compare` proves it, and `check_edging.py` pins each case.

### The editor paints itself, and nothing reaches disk unasked

**Every dependent surface refreshes on every compute** (20 September 2026).
`renderEditor` used to leave the DOM alone when the selection had not changed and
update a fixed list of readouts, which is how "Ordered as" went stale — and it
was never only that: every dropdown whose OPTIONS depend on the boards kept
whatever the library said when the section was last built, so changing a board's
edging and coming back still offered the old kinds.

**So it is rebuilt every time — and PAINTED, not replaced** (20 September 2026).
Rebuilding it with `innerHTML` threw away 49 of the editor's 59 controls on every
compute: measured on Test.json cabinet 4, every control in Structure, Drawers and
Supports was a new object afterwards and a focused `<select>` was no longer in
the document at all. A native dropdown belongs to the node it was opened on, so
that closed it — the twitch — and took the caret, the hover and the scroll with
it. Worse, it never stopped: `renderDrawers` calls `solveStack`, which wrote the
engine's heights back and scheduled another compute unconditionally, so a drawer
cabinet sitting untouched on screen computed about three times a second for ever
and lit the unsaved-changes marker on a job nobody had edited.

`paint(box, html)` applies the new HTML to the DOM that is already there: a node
that has not changed is left alone, a changed value is written into the control
in place, and only a control that has genuinely changed shape — or gone — is
replaced. Two rules make it safe. **A focused control is never touched**, not its
options and not its value (focus is what an open dropdown is, and what is being
typed into); it catches up when focus leaves it. And **a slot div belongs to its
own render function** — `sectionHTML` emits it empty and `data-slot` keeps the
paint out of it. `solveStack` now schedules a compute only when a height actually
moved. Nothing in the editor attaches a listener to a control — they are all
delegated on `#editor` — so reusing a node cannot stack a second handler on it.

The flags that used to force a full rebuild (`S.selRendered = -2` on a board
change, a tickbox, a renumber, a drag) are gone: all they could do now is destroy
the control being used.

**The cabinet table is painted the same way**, through the same `slot()`
stand-in. It holds no dropdown, so nothing there was twitching, but it was being
rebuilt three times a second alongside the editor and taking the hover and the
focus ring with it.

**Save is the only thing that writes** (ruled 20 September 2026). A saved job is
the price capture, so an experiment must not be able to move one by itself. The
`unsaved changes` marker says when the screen and the disk disagree, and New,
Load, the fixture button and closing the window all ask first.

### Deleting a project

`jobs/_deleted/`, never `unlink`. A job is a quote somebody may want back, and
picking the wrong one has no undo otherwise; a second delete of the same name is
stamped rather than overwriting the first. The job **open on screen** cannot be
deleted — that would leave the editor with nowhere to save back to — and
`Test.json` and `Test_Build.json` say what they are before they go, because
`regen_check` and half the `check_*` scripts run against them.

### Grain is listed, never judged

`Length` IS the grain direction on a grained board and a locked panel cannot be
turned by the nester, so grain is said out loud rather than shown as a `1`. The
cut list's Grain column reads `locked along L <n>` or `free`. A board swap lists
every panel that locks or comes free, with its size, board and direction, and
**what the lost rotation costs**: the same panels re-nested with grain cleared,
so the price of the lock is separated from the price of the board. On the October
job, swapping MEL into Brookhill costs **one extra board, R1,066**, purely for
the lock. The app does not judge whether a direction is the right one to look at
— that is not something it can know, and the list is there to be checked.

### Swapping a board moves every use of it

**Ruled 20 September 2026**, overriding an earlier choice to leave hand-specified
panels alone. A swap moves every use of the old board in the open project: every
field `Cabinet.board_refs` knows about, every bespoke panel and every loose
panel. A board being swapped out must not still be named anywhere, or the cut
list quotes a board the project no longer carries. **No panel is renamed** — it
keeps its designation and changes what it is cut from (the 14 September rule),
pinned on a full merge of the October job where 254 panels change board.

**A bespoke or loose panel stores `grain` and `edge_material` as TYPED values**,
because `generate_job` is read-only with respect to them. Moving the board alone
would leave a woodgrain panel at grain 0 — W8/D9 exactly, the 60 décor panels
Plazaboard's counter caught and we did not. So a swap re-derives `grain` from the
new board, and maps `edge_material` **by kind**: a panel edged in the old board's
PVC comes out edged in the new board's PVC. An edging that never matched the old
board is a literal somebody typed, and is left alone. If the new board does not
offer the kind, the edging is cleared and the bands are left, so the panel still
says it wants edging and the `EDGING` critical fires. On the October job this is
9 panels, all of them grain 0 on a board that locks grain.

**The preview reports what the swap does to the VALIDATION**, not only to the
cost: new criticals and warnings, the ones that would go away, the panels each
board gains and loses, and which hand-specified panels were re-derived. A swap is
how a design gets previewed, so a problem it creates has to be on screen before
anything is written.

**`engine.resolved` hands a bespoke or loose panel back as the very same object
the job holds.** The swap re-derives those records in place, so the "before"
board and edging must be read *before* any of it — a diff taken afterwards
compares the new values with themselves and reports that nothing moved. That was
a real bug; `check_swap.py` pins it.

**Swapping onto a board the project already carries MERGES the two**, and
swapping back does not undo it: nothing records which panels used to be which.
The confirm step says so.

**A grain-locked panel is measured as it will be cut**, not turned
(`validate._panel_fits_board`). One that only fits rotated fits on a plain board
and does not fit on a grained one, and the nester would drop it without a word —
which is what a swap onto a grained board can produce. A panel too big whichever
way round it goes keeps its original wording, so the October job's `1808` reads
exactly as it always did.

### One source for "which fields hold a board"

**Ruled 20 September 2026.** `Cabinet._board_slots` is the single list of every
place a cabinet names a board, and `Cabinet.board_refs()` / `map_board_refs()`
are what everything reads. Four hand-written lists used to answer this question
and they disagreed: a swap moved only the carcass and exterior, un-selecting
checked only those plus the drawer boards, `boards.scan_jobs` missed the back,
the door leaves and the edging boards, and the validator had its own list again.
So a board could be swapped or taken out of a project with a cabinet still
pointing at it.

Each slot carries a **label a message says out loud** — "door leaf 2 board",
"drawer 1 face board" — so a refusal names the thing to go and change.

A slot is marked **hand-specified** when it is a bespoke panel's material, and
rename and swap differ on it deliberately: a *rename* says "this board is called
something else now", so every reference follows it, bespoke included, or it
points at an id the library no longer has; a *swap* says "cut this from a
different board", and a bespoke panel's material was typed out panel by panel.
On the October job that difference is eight panels and R848 of Brookhill.

`boards.cabinet_board_ids` is the one deliberate repeat — it reads raw JSON,
because a job file that will not parse has to be reported by name rather than
skipped. `tools/check_single_source.py` holds the two together **by reflection**:
a `_board` field added to `Cabinet` and not to `_board_slots` fails that check
rather than becoming the fifth list that disagrees.

**A check never reads live workshop data to pin a fact about the past.** It has
bitten twice, the same way both times.

`check_library.py` builds its own in-memory library fixture instead of reading
the live `boards.json`. It used to read it, so renaming `MEL` to `WHITEMEL` — an
ordinary thing to do in the Boards tab — made `B.find(lib, "MEL")` return None
and the file died at line 184, with about thirty checks after it silently not
running. `boards.load` and `boards.save` resolve `LIBRARY` at call time rather
than binding it as a default argument, so a check can point at a fixture without
writing the workshop's real library.

**`tools/fixtures/Test_Build_pre_library.json` is the same lesson for a job file**
(21 September 2026). Three checks pinned "a job written before the library still
names DECOR" against the LIVE `jobs/Test_Build.json`. Upgrading that job in the
Boards tab — again, an ordinary thing to do — renamed its DECOR to BROOKHILL and
broke all three. The upgrade was sound: the same 27 cut-list lines, the same
designations, sizes and total, with only the board id moving on five of them,
which is the rename and the price capture working exactly as designed. But a
fixture has to sit still, so the pre-library version is frozen here, taken
verbatim from `jobs/Test_Build.json` at the baseline commit (7daedb7): bare-string
materials, no `boards` key, `decor` rather than `exterior_board`. Nothing in the
app can reach it. `check_boards.py` and `check_library.py` read it by name.

The one half that still reads the real folder is `scan_jobs(jobs/).unreadable`,
and deliberately: that a job file will not parse has to be found live and
reported by name. Whether a board is found under a former id is asked of the
frozen copy, because that is a fact about the scan, not about what happens to be
in `jobs/` today.

### Tapes are generated, not mapped

Three tape names come off **one token per board**:

```
PVC <token>    the thin carcass tape
1mm <token>    exterior option
2mm <token>    exterior option
```

**The token is its own field, not the board's name.** Edging names are decided
per order — there is no fixed Plazaboard edging name to look up for a board (ruled
18 September 2026; the October job's "WOOD" was that order's choice for a
woodgrain board, not a catalogue rule). The token is what this workshop wants on
the order, and keeping it separate stops a long board description such as
"BROOKHILL FUSION CHIP" landing on an order as an edging name — D6/W10 in the
other direction, where a board name reached an order as a tape. A board with a
blank token generates off its name, which is right for a board whose name is
already the short one; a board with neither generates nothing and the validator
names it rather than inventing a tape.

Colour derivation is unchanged: **front edges take the EXTERIOR board, every
other banded edge takes the CARCASS board.**

| Field | Derived as |
|---|---|
| `carcass_edge` | PVC in the **exterior** colour. Fronts of the sides, top, bottom, shelves, dividers and front-edged supports — shelf and divider fronts match the front, not the box (ruled 14 Sept 2026). Not selectable anywhere; it follows the exterior board. |
| `door_edge` | `door_edge_kind` (1mm / 2mm) in `door_edge_board`'s colour. Doors and exposed ends. |
| `drawer_face_edge` | `drawer_edge_kind` in `drawer_edge_board`'s colour. Drawer faces. |
| `drawer_box_edge` | PVC in the **drawer box** board's colour. Drawer sides and fronts, and white-edged supports. |

**Edging is one control per section, and it is called edging, not tape** (18
September 2026). Doors and Drawers each carry a thickness dropdown and a colour
dropdown, and the colour is a *board*, so the name is still generated from that
board's token and a board name still cannot reach a real order as a tape. Each
half is `None` for "follow the cabinet", and the fall-through is
drawer → door → `Cabinet.exterior_tape` / `exterior_board`, so a job quoted
before the two were separable is edged exactly as it was quoted. The flat string
overrides (`carcass_edge`, `door_edge`, `drawer_box_edge`) are still read and
still win where a job file carries one; the editor says so and offers to clear it
rather than showing dropdowns the cut list is ignoring.

**`Cabinet.exterior_tape` is 1mm or 2mm, per cabinet, and has no dimensional
effect whatsoever.** It is the fallback the two section choices fall through to.
We supply finished sizes and Plazaboard deduct the tape, so the two cut
identically and differ only in what is ordered and what it costs. There is no
deduction logic anywhere and none is wanted.

The resolved edging names show in the editor beside each control and as a legend
on the elevation (`render.tape_legend`), naming the cabinets when they disagree —
a door edged in the carcass colour looks right on paper and wrong in the room.

### Grain

**Grain is the board's Grain / Plain**, read through `model.grain_of`, and a
grain board locks every panel cut from it. It was hardcoded `grain=1` on doors,
faces and exposed panels, which was only ever right because the exterior board
was always the woodgrain one — W8/D9 is 60 woodgrain panels going out at grain 0
with only Plazaboard's counter catching it.

### Price capture

**A saved job keeps the prices it was quoted at.** `material_price` reads the
captured figure and `export_plaza.effective_price` is the one place that decides
what a board costs this job, falling back to the rate card only for a job saved
before boards carried a price. Editing a board's Last price changes what the next
project to select it is quoted at and moves no existing job. The October job
reopens at R28,363.50 permanently, and `check_library.py` pins exactly that by
raising a price in a temporary library and re-costing it.

**Everything else about a board comes from the library** (ruled 18 September
2026). The library is where a board's details are edited, so the project on
screen uses them: name, edging token, thickness, grain and picture
(`api.LIVE_FIELDS`). `api.refresh_from_library` brings the job's copy up to date
when a saved job is opened (`job_load`) and when a board is saved in the Boards
tab (`board_save`, for the project open on screen) — so a changed description
shows in Structure, the cut list and the quote at once. **Price is the one field
kept**: the job's captured figure, or for a pre-library job the rate-card price,
written down before the name changes so a new name cannot lose it (the rate card
is keyed by name). The October fixture button loads the frozen quote as it was
and is never refreshed. Files on disk change only when saved.

### Thickness — 16 mm is assumed, and that is not fixed

Every carcass size in the app is 16 mm arithmetic. Thickness-driven geometry is
**deferred and deliberately not built**; what exists instead is an assertion —
`validate._carcass_thickness` names any cabinet whose board is not
`Standard.board_t`, and says which figures are the 16 mm ones. The full list of
places that assume it:

| File | Function | Line | What it controls |
|---|---|---|---|
| standard.py | *(constant)* | 12 | `board_t = 16`, the source of all of it |
| standard.py | *(constant)* | 21 | `back_cavity = 16`, clear space behind the back |
| standard.py | *(constant)* | 37 | `drawer_base_offset = 16`, base groove height |
| standard.py | *(constant)* | 46 | `exposed_extra = 16`, exposed end finishing flush with the door |
| standard.py | `internal_width` | 103-104 | `W - 2t` — every shelf, support, top, bottom and divider width |
| standard.py | `back_face_from_front` | 108 | shelf depth and the back's position |
| standard.py | `back_size` | 120, 122, 124 | the backing panel, `W-20` / `H-20` / `H-10` |
| standard.py | `drawer_front_length` | 155 | drawer front and back length, via `internal_width` |
| standard.py | `drawer_base` | 161, 164 | drawer base, grooved and housed |
| engine.py | `generate_cabinet` | 32 | `Wi`, which sizes tops, bottoms, supports, shelves, dividers |
| engine.py | `generate_cabinet` | 78 | default divider height, `H - 2t` |
| engine.py | `generate_cabinet` | 135 | exposed end panel depth, `depth + 16` |
| room.py | `geometry` | 296 | panel width read back off a top or rail, `span + 2t` |
| room.py | `plinth_deduction` | 967 | the board a butted plinth loses at an internal corner |
| validate.py | `_outlines` | 597 | corner unit wall sides, one and two boards short of the arms |

Not on the list and worth saying so: pot hole positions are `std.hinge_positions`
and carry no thickness at all, and fillers and scribes are gap arithmetic
(`scribe_allowance`, `taper_threshold`) with no board thickness in them either.

## Panels

**An independent panel is a part, not a cupboard.** It is cut, numbered, costed
and nested like everything else, and it belongs to no carcass. Several of them
make a bulkhead — a front, an underside and an end cap each side — and each is
its own numbered item, which is why they are numbered in the same series as the
cabinets rather than listed apart.

**A panel is a `Cabinet` with `kind="panel"` and a `PanelSpec`.** That buys the
numbering (`store.next_number`), the save and load, the cabinet table, the
`Placement` record and the one `generate_job` loop — which is where the cost,
the nesting and the CSV come from for nothing. What it costs is that every place
assuming "a cabinet is a box with doors" has to say what it does about a panel.
`tools/check_panels.py` is where they are held to it.

**`kind` is the only thing that says panel, and `template` is never rewritten.**
The brief proposed carrying it on `template` as well. It cannot be: switching an
item back from Panel would then have to put `template` where it was, and there
is nothing to put it back from — October cabinets 3 and 5 are
`template="standard"` carrying hand-specified extras, so "it has bespoke panels,
therefore it was bespoke" is wrong, and being wrong there rewrites a real cut
list. Off `kind` alone a round trip loses nothing: switch to Panel and back and
every field is where it was, template included. Same bargain as the tickboxes.

**Code 08, role "Panel"** (`model.PANEL_CODE`, ruled 20 September 2026, Q2).
Plazaboard's CSV writes the Component column from `Panel.label` — the digits,
`1508` — and never from `CODES[code]` or `Panel.role`, so a new code would need
their sign-off exactly as 10 and 11 still do, and would say nothing on the order
that 08 does not. The role is what tells a panel from an exposed end in the
app's own cut list. One constant, so a code they do sign off later is one edit.

**What is typed, and what is derived.** The operator types a board, an
orientation, two FINISHED extents and how many long and short edges are banded.
Everything else is `engine.panel_of`'s: which extent becomes the cut list's
`Length`, whether the panel locks, and what its edging is called. The editor's
preview line is that answer read back, not one the browser assembles.

**`Length` IS the grain direction, so it is not simply the longer side.** On a
grained board the extent the grain runs along becomes the length whether it is
longer or not, and `grain=1` locks it. On a plain board the longer extent is the
length and the nester may turn it. Which means **long and short edges are not
`edge_l` and `edge_w`**: a panel cut across its grain has its long edges running
the width, so the two are mapped rather than assumed equal. Pinned in
`check_panels.py`, both ways round.

**Three orientations, and the third extent is always the board's thickness** —
which is why a panel never states one, and why `room.geometry` needs the job's
materials to answer for it (`geometry(cab, std, materials)`; nothing else reads
that argument, because the engine reads the boards for tapes and grain and never
for a size).

| Orientation | along the wall | out from the wall | up |
|---|---|---|---|
| `upright` — facing the room | a | thickness | b |
| `flat` — horizontal | a | b | thickness |
| `end` — upright, side-on | thickness | a | b |

**Declared width, height and depth on a panel are labels and nothing else.** The
cabinet table shows `room.geometry`'s figures for one, not the declared ones.

**A panel is not a carcass.** `room.placed` skips it explicitly, so gaps, runs,
plinth, tip-up, door swing and overlaps are exactly what they were; it stands on
no legs (`stands_on_legs` is false, so `carcass_z` is its own z); it is not in
the Run drawing, which is also what keeps `wall_elevation_svg` with no room
equal to `elevation_svg`; and it is not in the edging legend, the structure,
door, drawer, support or carcass-thickness checks. A cabinet switched to Panel
keeps its drawer stack and its support rows in the job file and is reported on
for neither. Where it IS placed, drawn and snapped against is **Placing a
panel** below — through `room.placed_panels`, which is a separate list for
exactly this reason.

**`validate._panels` is deliberately short.** What a panel shares with
everything else on the cut list is already checked where it always was — too big
for a sheet is `_panel_fits_board`, a board the project never selected is
`_board_prices` — and repeating it would be two messages for one problem. What
is left is a missing board, a size of zero, an orientation the model does not
know, and an edging the board does not offer (CRITICAL, tagged `EDGING`, the
same shape as Part A's). **An unplaced panel is not a fault**: a panel cut and
not put anywhere is normal.

**A panel is always qty 1.** Identical panels are a **Duplicate** — the next
free number, everything copied except the placement, from the cabinet table's
Dup or the button in Panel design.

`PanelSpec.anchor` is reserved and nothing reads it. It is written to the job
file only when set. Ruled 20 September 2026: a panel stays where it is put and
does not follow a cabinet; the field is the seam for the day that changes.
Part E did not change that — it gave a panel a place, not an owner.

## Placing a panel

**A panel has a place in the room, and the cabinets do not notice.** Part E, 21
September 2026. What it added is one field, one list and one warning; everything
else is the machinery that was already there, taught that a panel exists.

**`Placement.y` is the one field a panel needs and a cabinet does not.** Out
from the wall face to the panel's back: 0 is flush, and it is what puts a
bulkhead underside out over the units below it, or holds an end cap behind the
front that laps it. A carcass sits against the wall it is placed on, so its y is
0 and stays 0 — the Placements table's Y cell is not even offered on a cabinet
row. **It is written to the job file only when it is non-zero**, so every
placement written before panels could be placed round-trips byte for byte.

    x   left edge along the wall, from the start corner
    y   out from the wall face to the back of the panel
    z   the bottom edge — a panel stands on NO legs, so this is its underside
        exactly as typed (`room.stands_on_legs` is false for it, and
        `room.carcass_z` hands back `p.z`)

**`room.placed_panels(job)` is the panel-only twin of `placed()`, which stays
cabinet-only.** Two lists, not one, on purpose: `placed()` is what gaps, runs,
plinth, tip-up and door swing come through, and a panel takes part in none of
them. `room._on_wall` is the one place the two are read together, because what
something comes to rest against does not care what kind of thing it is.

**A panel is dragged by the same pipeline as a cabinet**, not a second one: it
gets the same `g.ecabg` group with the same `data-cab`, so one press handler,
one `/api/drag`, one set of snap rules. `snap_points` and `z_snap_points` read
both lists, so a bulkhead front snaps to **the cabinet tops below it** as well
as to wall ends, the floor, the ceiling, opening edges and other panels.

**`/api/drag` says how far off the floor `z = 0` really is, and the browser
stops working it out.** `leg_lift` is `room.carcass_z` asked at z 0: the leg
height for a standing carcass, 0 for a hung unit and 0 for a panel. The browser
used to derive that from the layer, which would have stood every panel 100 mm
off the floor.

**The boards are read for a panel's geometry, everywhere it is asked.** A
panel's third extent is its board's thickness, so `snap_points`,
`z_snap_points`, `api.drag`, `cabinet_footprint`, `overlaps` and the drawings
all pass `job.materials` through to `room.geometry`. Nothing a cabinet answers
changes — the engine reads the boards for tapes and grain and never for a size.

**A 16 mm panel is a few pixels of target, so every one carries an invisible hit
rectangle at least `render.PANEL_GRAB` (16) px across** with `pointer-events`
on. Without it a bulkhead front cannot be picked up at all.

**In the plan a panel is a thin rectangle in its own board's colour, drawn over
the cabinets and taking no pointer events.** `y` is visible there and nowhere
else. It is not draggable in the plan — a panel is placed by typing, and the
plan drag knows nothing about y — and a bulkhead underside is 570 deep on plan,
so left grabbable it would have put an undraggable sheet over every cabinet it
caps.

**Grain lines on a panel run the way the cut list cuts it, or not at all.**
`render._panel_grain_vertical` maps the grain direction onto the drawing through
the orientation; a grain running out from the wall has no direction face on, so
nothing is drawn rather than a line that would say the wrong thing.

**A panel clash is a WARNING, never a critical** (`room.panel_clashes`). Two
carcasses sharing a stretch of wall is a critical because the cut list built on
it is wrong. A panel is different: it is cut and costed wherever it is, its
position moves no figure on the order, and a bulkhead front is *meant* to sit
flush on the run and hard against the ceiling. Touching is clear, as everywhere
else, so a flush bulkhead raises nothing. The tests are the ones already here —
`polygons_overlap` on the outlines, `_z_span` on the heights, and for an opening
the same across-and-level test `blocked_openings` makes for a carcass.

**The plan's layer toggle is multi-select** (E3b, ruled 21 September 2026). Base,
Wall, Tall and Panels each switch on and off on their own; it used to be one
radio, so choosing a layer meant giving up every other one. Default is all four
on, which is exactly what the old "All" drew. **Everything not shown is ghosted,
not hidden** — the existing rule, applied to the new toggle as well: an overhead
means nothing without the base run underneath it, and Panels follows suit rather
than being the one toggle that behaves differently. `room.LAYERS` is still the
three CABINET layers and `layer_of` is never asked about a panel; `"panels"` is a
fourth toggle over the top, and `render.plan_svg` is the only place the word
means anything.

**A new placement lands clear of what is already on that wall** (E8, ruled 21
September 2026). Giving a cabinet or a panel a wall used to put it at 0 mm
whatever was there, which dropped it on top of the first thing on that wall and
out of sight underneath it. `room.free_x` answers it, off the same candidates a
drag reads — the wall start and the right-hand edge of everything already placed
— and the browser asks `/api/drag` and uses the figure. Nothing is worked out in
the browser. An item that fits nowhere comes to rest against the end of the run,
clamped to the wall: an honest overlap the validator will name, which beats a
position nothing worked out.

**Not built, and not asked for: dragging a panel in the plan, and `PanelSpec.anchor`.**
A panel still stays where it is put and does not follow a cabinet.

## Zoom

**The wall elevation and the plan zoom on the scroll wheel** (E9, 21 September
2026), with `−` / `100%` / `+` beside each drawing; the percentage is the way
back. Zoom only — panning is the box's own scrollbars, and nothing was asked for
beyond that.

**The drawing is scaled by setting the SVG element's CSS size, and the viewBox is
left alone.** That is the whole trick: every conversion from a pointer to
millimetres — `elevPoint`, `svgPoint`, the plan's wall tracks, the elevation's
`.etrack` mapping and the panels' hit areas — reads `getBoundingClientRect()`
against the same viewBox, so it is exact at any zoom level without one line of
that arithmetic changing. Measured on the real app: a cabinet and a panel both
move the right number of millimetres at 64 %, 100 % and 156 %.

**A wheel over a drawing zooms it rather than scrolling the page.** That is what
was asked for, and it is worth knowing before you reach for the wheel to scroll
past the plan.

## Supports

**A support is a cross rail spanning the internal width** (`W - 32` x 100, code
04) that ties the two sides together. It is called a support everywhere in the
UI — never a rail.

`Cabinet.support_rows` is a list of `Support(edge, qty)`, where `edge` is
`'front'` (carcass tape), `'white'` or `'none'`. **The total is
the sum of the rows and nothing subtracts.** The old model was a total with two
subsets taken off it, so `edged + white` could exceed `supports` and the plain
count went negative — which `if plain > 0` then dropped in silence.

`Cabinet.support_list` is what the engine reads. With no rows it migrates the
three legacy numbers in the order the engine always emitted them — plain, then
front-edged, then white-edged — so a migrated cabinet cuts the same list in the
same order. A cabinet whose three numbers contradict each other keeps cutting
exactly what it always cut and is **named in a warning**; nothing is migrated on
a guess. `Test_Build.json` cabinet 4 is the one real case (0 total, 4 white).

**White-edged means edged white: `PVC WHITE`, whatever the boards are** (ruled 18
September 2026, `model.WHITE_EDGE`). It used to take the drawer-box tape, which
follows the carcass board, so on a GREY carcass a row labelled "White-edged" went
out as `PVC Grey`. `Cabinet.support_tape` is the one answer; the engine cuts from
it and the editor's Edging column shows it. The October job is unaffected (its
white supports were on MEL, already `PVC WHITE`); `check_library`'s what-if swap
to a Brookhill carcass moved R34,716.75 → R34,723.50 because of it.

## The nester

`cabinetgen/nest.py`. Guillotine only — Plazaboard cut on a beam saw, so every
cut runs edge to edge. A layout the saw cannot produce is worthless, however
tight it looks.

It tries 7 panel sort orders against 6 guillotine split heuristics (42 packings,
about 0.3 s) and keeps the fewest sheets. On the October job it lands on
**18 MEL / 9 DECOR / 6 BACK — exactly what Plazaboard achieved**. Yields 88.9 /
77.3 / 79.8 %. If a change drops below that, it regressed.

Grain-locked panels are never rotated. `NEST_CHOICE` records which heuristic
won per material; `NEST_REJECTS` lists panels too big for a bare board.

Sheet layouts render to `out/nest_<material>.svg` — open in any browser.

Worth trying if more yield is wanted: cross-sheet offcut reuse (keep a stock of
leftovers between jobs), and simulated annealing over the panel order. The
77 % on Brookhill is the one worth attacking — it is the R999 board.

## The UI

`python run_app.py`. See `docs/UI-BRIEF.md` for why it is shaped the way it is.

The elevation and the cabinet list stack in the left column; the **settings panel
is a column of its own**, starting level with the top of the drawing.

The cabinet editor is seven sections, each a bold heading over its own coloured
block: **Size · Outline · Structure · Doors · Drawers · Corner Unit ·
Supports**. An item whose **Kind** is Panel shows **Size · Panel design** and
none of the cupboard sections — hidden, never emptied, so picking a cupboard
kind again brings all of it back (see **Panels**). Turning a configured cupboard
into a panel says what stops being cut before it does. Doors, Drawers and Corner Unit are tickbox sections — unticking keeps
everything in the job file and builds nothing from it, and says which cut-list
lines would go before it does.

- **Structure** is where the boards are chosen — exterior, backing, carcass, in
  that order — then how the back is fixed, then the shelves. Every board is a
  dropdown off `Job.materials`; free text there used to create a material
  silently, which nested on its own sheet and priced at zero. **Structure
  mentions no edging at all**, on purpose.
- **Shelves** are adjustable, on pot holes, 4 mm clear of the back. **Fixed
  shelves** are fitted into the carcass and run 3 mm deeper, 1 mm clear of it.
- **Dividers, divider height and shelf width are shown greyed and labelled
  "function unavailable"** — a divider cannot be positioned yet and shelves do
  not divide around one. Shown rather than removed, because an option that
  silently does nothing is worse than one that says so.
- **Doors** is one or two leaves and no more. A pair is fixed, left and right; a
  single door is the choice. Each leaf names the board it is cut from, and the
  section carries one edging control.
- **Drawers** carries the face table — with a box-material and a face-material
  column per drawer, defaulting to Structure's Carcass and Exterior boards — and
  one edging control for the whole section. Each box's own PVC edging follows
  that drawer's box board and is not chosen. The settings column is 560 wide to
  fit the table's nine columns.
- **Supports** is the support rows and nothing else. The **Decor** section is
  gone — added panels (exposed ends, code 08) come back with that work.

Six tabs over one `POST /api/compute`. The handlers in `app/api.py` decide no
dimension — every number in a response came out of the engine. Keep it that way:
if the UI needs a number, add it to `cabinetgen`, do not compute it in the
browser. `nest.nestable()` exists for exactly that reason — the UI and
`regen_check` must agree on which panels reach the nester or the board counts
drift apart.

Drawer face heights are authored **one row per face**, top to bottom. A row is
either **Fixed** — the height as typed — or **Share**, a slice of whatever the
fixed rows leave, split in proportion to its share number. The gaps come from
`Standard` and are never typed per drawer. `drawers.divide` does the arithmetic
and `/api/drawer-solve` hands it back, so the millimetres shown live beside each
row as it is typed are the engine's, not the browser's; `Equal` and `Graduated`
come from `/api/drawer-preset` for the same reason (`Standard.graduated_step`).
Fixed rows that over-run the opening leave the share rows at zero, which is a
critical and blocks the export rather than ordering a negative panel.

`face_height` is still the ordered figure and still the only one the engine
reads — what was ordered is a list of heights. `Drawer.mode` and `Drawer.share`
ride alongside it so a stack can be picked up and re-divided later instead of
retyped; nothing downstream reads them.

**A cabinet is dragged in the wall elevation, sideways and up and down** (18
September 2026). Same bargain as the plan: `/api/drag` hands over every position
(`room.snap_points`) and every height (`room.z_snap_points`) the engine will
allow, with the reason for each, and the browser only picks the nearest within
`Standard.snap_tolerance`. A height that belongs to another cabinet carries the
stretch of wall it applies over, because the drag crosses several on the way and
a round trip per pointer move is not on; testing that overlap is a comparison
between candidates the engine named, not a dimension. The drawing carries the
mapping in `class="etrack"` — where 0 mm and the floor are, and the scale — and
one `class="ecabg"` group per cabinet so the whole thing moves rather than an
empty outline. The vertical figure is `Placement.z`: 0 is the floor, where the
carcass stands on its legs, and above it is a hung unit's underside.

Two things about that drag that were wrong and are pinned only by hand (the UI
has no test harness): the press does all its synchronous work — listeners,
`preventDefault` — *before* awaiting `/api/drag`, and replays the last pointer
position and the release once the model arrives. Awaiting first meant a quick
drag let go before anything listened, and the cabinet stuck to the pointer. And
the floor snap is compared where a standing carcass really is (its underside on
the legs), not at `z = 0`; an underside below leg height is "on the floor". Before,
a sideways drag with a 2 px wobble hung a base unit 86 mm up.

**Lining up, not only stacking** (18 September 2026). Besides "on top of" and
"under", which only apply over or under the other cabinet, `z_snap_points` offers
"tops level with N" and "bottoms level with N" for every cabinet on the wall. Those
carry the stretch they do **not** apply over (`not_x0`/`not_x1`): beside a tall
unit a wall unit's top can come level with it, but directly over a base unit
level tops would put one inside the other. Nothing below `leg_height` is offered.

**Hinge naming.** `L` / `R` is the edge the leaf hangs from, facing the cabinet —
the plan's swing pivot, the elevation's hinge dots and the point of its dashed
triangle all sit on that side, and they were checked to agree. The editor says
"hinged left / hinged right". It used to say "opens from the left" for `L`, which
reads as the handle side — the one thing that was inverted.

**Clicking a door in the elevation no longer turns it round.** Which edge a leaf
hangs from is set in the Doors section, where the answer can be read instead of
guessed at from a picture, and a pair is not a choice at all.

Dragging the join between two faces in the elevation pins **those two only**: the
SVG carries each pair's span in both mm and pixels (`class="fdiv"`), the browser
reads its drop back into millimetres the same way a plan drag projects onto a
wall track, and `drawers.split_pair` divides the pair server-side. The rest of
the stack is untouched, and each face is held back far enough to clear its own
box side — which is the existing rule, not a new number.

Not editable in the UI yet: loose panels, the bespoke panel lists on
`template="none"` cabinets, and a wall's openings and obstructions. All are
carried through the job file faithfully but must be edited there. A cabinet's
outline *is* editable — the Outline field in the editor — and the editor shows
what the engine's checks are actually using beside it.

## The room

`docs/ROOM-LAYOUT-SPEC.md` is the spec and the phasing. **Phases 1 to 5 are
done:** the dataclasses, `room.py`, `to_world`, the closure check, a wall-entry
form, `render.plan_svg` with the layer toggle, placements by form, gap detection
with fillers and scribes, plinth, drag placement with collisions, snapping and
front-clearance checks, and dimensioned per-wall elevations.

Phase 6 is 3D.

`Job.room is None` is the default and must stay behaving exactly as it did
before rooms existed — same panels, same nest, same cost, and no `room` or
`placements` key written to the job file. That is what keeps `regen_check`
meaningful, so it is pinned in `tools/check_room.py`.

All trigonometry lives in `room.py`. Plan view, elevations, 3D, DXF and the
SolidWorks table all call `to_world(room, wall_id, x, y, z)` and none of them
does its own. Wall-local axes are x along the wall from its start corner, y out
from the wall face into the room, z up. World is X right, Y into the room from
wall A, Z up — which maps onto SVG with no flip.

Two things about corners that are easy to get wrong:

- Every corner is measured **twice**, once from each wall that meets there
  (`walls[i].offset_end` and `walls[i+1].offset_start` are the same physical
  angle). The first wall's figure drives the geometry; the second is
  cross-checked and a disagreement is reported, never averaged. If only one is
  given, it is used — so a corner need only be measured from the reachable side.
- A square room closes even if the corner turn has the wrong sign. The
  parallelogram case in `check_room.py` is what actually proves it; do not
  delete it.

Thresholds live in `Standard` like every other dimension: `closure_warn`,
`closure_block`, `corner_disagree`.

**Layers** come from `room.layer_of`: kind `tall` is tall, kind `upper` is wall,
anything else off the floor (`Placement.z > 0`) is wall, everything else is
base. `Placement.layer` overrides it. No z threshold was invented — hung is
hung. The browser never derives a layer; `/api/compute` returns the layer per
cabinet and the UI reads it back.

**Layers are for drawing; runs are about the floor.** `room.run_key` folds
tall into base: a tall unit stands on the same floor as the base unit beside it,
so it is in the same run, closes the same gaps and carries the same plinth
board. Grouping runs by drawing layer made a tall unit invisible to the base run
next to it (found 14 September 2026, fixed). Overlaps do not group at all —
they compare anything on the same wall whose heights overlap, so an overhead
hung into a tall unit is caught too.

## Geometry

`room.geometry(cab)` is the one code path, template or bespoke, and returns
`CabinetGeometry`: the outline in the cabinet's own frame (x along the wall from
its left edge, y out from the wall face), height, the deepest carcass panel, the
width the panels make, door widths, runner. Read off `engine.generate_cabinet`
at call time — engine imports room, so room imports engine only inside the
function.

- **`Cabinet.footprint` is any shape.** A polygon in that frame, in the job
  file, entered in the editor as `x,y` pairs. Empty means "the rectangle its
  panels make", which is right for every template cabinet. A corner box is an
  L and must be entered — the validator warns when a bespoke cabinet has none.
  A standard cabinet is a four-point rectangle *in the same type*: one field,
  one code path, no special case.
- **Non-convex outlines are real polygons, not bounding boxes.** `room.
  polygons_overlap` triangulates (ear clipping) and runs the separating-axis
  test per piece; touching is clear, a unit tucked exactly into an L's notch is
  clear, and two identical rectangles overlap. Pinned in `check_drag.py`.
- The validator cross-checks an entered outline against the panels (depth
  against the deepest side, width against top or bottom plus two sides) and
  says which one is wrong; it rejects an outline that is not a polygon.
- What still reads declared figures, on purpose: `engine.generate_cabinet` (it
  makes the panels from them), the spec checks in `validate._cabinet_structure`
  (runner fits the declared depth — the engine would raise otherwise), the size
  captions on drawings, `render.elevation_svg` (the pre-room side-by-side sanity
  check, pinned byte-identical), and `render._interior` (door and drawer face
  rectangles from the spec that made those panels — same numbers).

The plan view ghosts unselected layers rather than hiding them, draws wall units
dashed and translucent so the base run reads underneath, draws every label after
every shape so an overhead cannot bury the number beneath it, and draws
obstructions last of all — a waste pipe behind a carcass is the one thing on
that drawing you cannot afford to miss.

`/api/plan` is separate from `/api/compute` on purpose: flipping a layer should
cost a redraw, not a re-nest.

**Walls are added at either end of the sequence** — `room.add_wall(rm, "start" |
"end", length)`, behind `/api/room-extend` and the "+ Wall before / after" buttons.
That is how a straight run becomes an L or a U; the 4000 × 3000 pre-fill for a new
room stays (ruled 14 September 2026). A new wall takes the next free letter and
starts square. Placements name walls by id, so nothing moves along its wall, but a
wall added at the start re-origins the chain and becomes the "earlier" wall at that
corner for the plinth butt rule.

## Gaps, fillers and scribes

**The app proposes; it never inserts.** Ruled 14 September 2026, after the
earlier "every run gets a filler" rule proved too rigid — real kitchens use
fillers, blind corners and deliberately open gaps depending on the situation. A
gap with no treatment chosen emits no panel and raises a warning. Do not be
tempted to default it to `filler`; that is precisely the wrong cut list going
out unnoticed.

`room.gaps(job)` finds them, per wall **and per run** (`run_key`: the floor
run, tall units included, and the hung run) — a gap in the base run is not a gap
in the overheads above it. Suggestions come from the ruled numbers
in `Standard`: under `filler_min` (50) grow a cabinet, up to `filler_max` (150)
fit a filler, above that add a cabinet or a blind corner.

The taper is the whole point. A gap that meets an out-of-square corner is wider
at the front of the run than at the wall, by `depth × tan(corner deviation)`.
Plazaboard cut on a beam saw, so **a tapered panel cannot be ordered**: the
filler ships as a rectangle at the gap's widest point plus `scribe_allowance`
(15), and the note on the panel says to scribe it. Above `taper_threshold` (6)
the validator says so too.

Note what the taper is measured across: the run's **depth**, not the panel's
height. The room model has plan geometry and no plumb data, so an out-of-plumb
wall is not modelled and cannot be. If Rudolf meant taper over the panel's
length, that needs a plumb measurement per wall first — ask before changing it.

Fillers carry `cabinet=0` and name their run in the note, alongside the existing
`Job.loose` mechanism. Several fillers in one job get suffixed labels (011a,
011b) by the existing `suffix_labels`.

Panel codes `10` and `11` are **not yet confirmed with Plazaboard**. The
validator warns whenever a plinth or filler exists; flip
`Standard.codes_confirmed` when they sign off and both warnings stop.

## Plinth

**Legs are never optional; the plinth board is.** Corrected 14 September 2026,
after the first build got it backwards. Every carcass that stands on the floor
stands on adjustable legs — kitchen or wardrobe, always — so the height lift
belongs to the legs: `Standard.leg_height` 100 (the spec's "plinth height"),
within `leg_min` 98 to `leg_max` 122. `room.carcass_z` adds it to every standing
cabinet unconditionally and never asks whether a board is fitted. **Do not let a
plinth flag anywhere near a height again** — that was the bug, and it moved the
clash, opening and ceiling checks with it. `check_elevation.py` pins that fitting
a board changes no height.

The plinth *board* covers the legs. It is `leg_height` wide, set back
`plinth_setback` 50, carcass board, banded on both long edges (`edge_l=2`) to
seal it against water at floor level — the short end cuts are not banded.

**The board is opt-in per run**, the operator's call, whatever the job. Nothing
is made unless a `PlinthChoice` asks for it; the flag gates the code-10 panel and
nothing else. Same discipline as the gaps: the app shows you the runs, you decide.

`room.runs()` finds the runs, and what counts as one run is the load-bearing
decision: a filler or a blind corner **continues** a run, an open gap **breaks**
it, because a plinth board cannot span an appliance space. An undecided gap
breaks it too — conservative, and it already carries its own warning.

Two things that would be wrong if done naively:

- **Internal corners butt**, so exactly one of the two boards at a corner loses
  a board thickness. Never both (that leaves a gap) and never neither (it does
  not fit). The rule: the run on the *earlier* wall continues past, the one on
  the later wall stops square against it and loses 16 mm off its start. The
  panel note names the wall it butts into.
- **A run longer than a board splits at a cabinet division**, not wherever
  2750 mm lands, so the joint falls behind a carcass side. `plinth_lengths`
  takes the last division that still fits.

A run whose cabinets sit off the floor gets no plinth and a warning saying why.
A `PlinthChoice` whose run no longer starts at that cabinet is orphaned: no
panel, and a warning — the safe way round.

## Drag placement

**The browser computes no dimension.** That is the spec's rule and it shapes the
whole design. On pointerdown the UI asks `/api/drag` for that cabinet's snap
targets — wall ends, neighbouring cabinet edges, opening edges — all from
`room.snap_points`. The drag then only *picks the nearest of them*; it never
works out a position of its own. On drop the whole job is recomputed
server-side, so what reaches the cut list is always the engine's answer.

The plan SVG carries what a drag needs: `data-cab` on each cabinet, and an
invisible `#tracks` group with one line per wall giving its screen ends and its
length. The browser projects the pointer onto the nearest track. A drag near a
different wall re-parents the cabinet to it, which is why the snap model covers
every wall, not just the current one.

Drag listeners live on `window`, not on the element — a drag that runs off the
plan has to finish rather than stick to the pointer. Ghosted layers are not
draggable, so a wall unit only moves while the wall layer is the one shown
solid.

**Overlaps are critical; clashes are warnings.** Two carcasses cannot share a
stretch of wall, and a cut list built on that is wrong however good it looks. A
door or drawer that fouls something is a real defect, but which way a door hangs
is a judgement — blocking the export over it would be the app overruling the
person who measured the room.

Swing and pull-out geometry is in `room.py` and every envelope is emitted into
the plan hidden, so hovering costs nothing and the browser never computes an
arc. Two things about the checks that are easy to get wrong:

- **A door never fouls its own wall.** It pivots on the front face and sweeps
  away from it. A door hinged right at a corner finishes flat against the return
  wall — it grazes it, it does not swing through it, and that is not a clash.
  The cases worth catching are the return run, the run opposite, and the wall
  opposite in a galley.
- **Heights matter.** A base unit's door does not care about a wall unit two
  courses above it, so clashes only count where the vertical ranges overlap.
  Overlaps work the same way — heights, never layers — so a tall unit standing
  into a base unit, or an overhead hung into a tall unit, is a collision, while
  an overhead sitting over a base run is not.

`Standard.door_open_deg` is 90 — the drawing convention, not a construction
dimension. If a real job needs 110 the clash check follows the constant.

**Hinge side has one answer: `model.hinge_side`.** The plan's swing arcs, the
elevation's hinge marks and the clickable door leaves all read it, so they
cannot drift apart. `Cabinet.door_hinges` holds a per-leaf 'L'/'R' — one entry
per leaf, blank meaning "use the rule" — and the rule, when nothing is set, is
the one that was always here: a single door follows `Placement.flip`, a pair
hinges at its outer edges. A leaf hangs off **its own** edge, so turning one half
of a pair round puts its hinge in the middle of the opening, which is where it
really is.

The editor gives one Left/Right control per door panel the engine actually cut —
`len(geometry(cab).door_widths)`, not `cab.doors` — so a bespoke or corner unit
gets one too. Clicking a door in the elevation toggles it. Every change goes
through `/api/compute`, so the swing check re-runs on each one and the editor
reads the result back. The elevation only draws leaves for template cabinets
(`render._interior` works off the spec that made the panels, on purpose), so a
bespoke cabinet's leaf is turned round from the editor rather than the drawing.

## Per-wall elevations

**The runs either side show end on** (18 September 2026). Face on to wall B, wall
A's run comes towards you at B's start corner, and what you see is the cabinets'
sides. `room.return_profiles` projects each cabinet on the two neighbouring walls
into this wall's frame off its real plan outline (`to_world` there, the inverse
here — still all trig in `room.py`), and the drawing shows them light and
see-through under this wall's own cabinets, one label per identical outline. The
opposite wall is behind the viewer and is not drawn. They are drawing only — not
draggable, and not part of any dimension chain.

`render.wall_elevation_svg(job, wall_id)` draws one wall face on, as a drawing
meant to be measured from: cabinets at their true x and height, the wall and its
ceiling, openings with sill and head, obstructions with where to find them, the
fillers and plinth boards that were *chosen*, hinge side and count, and dimension
chains. With `room=None` it returns `elevation_svg(job)` unchanged — pinned byte
for byte in `check_elevation.py`. `/api/elevation` is separate from compute for
the same reason as `/api/plan`, and export writes one `_elevation_<wall>.svg` per
wall.

The chain numbers come from `render.wall_elevation_dims`, kept apart from the
drawing so they can be tested. Widths chain from the wall's start corner (the
floor run and the wall units separately), heights from the floor. **Every chain
closes** on the wall length or the ceiling — a chain that does not close is a
drawing that is lying.

**`room.carcass_z` is the one answer to "how high is it really".** `Placement.z`
of 0 means standing on the floor, and every standing carcass is on its legs, so
it starts `leg_height` up — board or no board (see Plinth). A hung unit is at its
own z. The elevation, the clash check, the opening check and the ceiling check all
ask `carcass_z`, so they cannot disagree: an overhead door at 780 fouls a base unit
topping out at 820 on its legs, and a 900-high unit under a 900 sill stands across
the window, not below it.

**Hinges: side and count from the order, positions for the drawing only.** Side
follows the same rule as the plan's swing arcs, and `check_elevation.py` checks the
two agree; the opening triangle's point is on the hinge side. Count is
`std.hinges`, the pot-hole figure already on the order. Positions come from
`std.hinge_positions` — `hinge_inset_drawn` (100) in from each end, any between
spread evenly — ruled with low confidence and **for drawings only**: pot holes are
drilled to Plazaboard's hardware spec. The drawing says so in a footnote, nothing
validates against the positions, and `check_elevation.py` fails if engine, export,
nest or validate ever reads them.

**The ceiling is a required site measurement.** `Room.ceiling` has no default; a
room without one is a critical and the job does not export — the same as a wall
with no length. Against a measured ceiling, a carcass top above it is a critical
too: a cabinet that cannot be stood in the room is as wrong as two that overlap.
A cabinet standing across an opening stays a warning (a top touching the sill
counts as clear), because opening sizes are site figures. An unmeasured ceiling is
never compared against; the elevation draws without it and says it is missing.

**Tip-up clearance.** Every carcass is built flat on its back and tipped up in one
piece, so a ceiling it clears standing but not on the way up is a critical too
(ruled 14 September 2026). `room.tip_clearance(H, D, L, s)` is exact: it pivots on
the bottom back edge until the rear feet touch down (tan angle = L / s), then on
the rear feet, and the top front edge peaks at `sqrt((D - s)² + (H + L)²)` on the
feet or `sqrt(D² + H²)` on the edge, whichever that phase actually reaches.
`Standard.leg_setback` is ruled at 50; it only moves the answer within about a
12 mm band, so build nothing else around it. The worked examples in the docstring
are checked by `check_examples.py`. A cabinet too tall to stand is reported once,
as that, not twice.

D is `room.carcass_depth`: the **deepest carcass panel**, never just the declared
depth. A bespoke corner unit declares 500 and has an 834 side, and depth drives
the diagonal, so the declared figure under-reports — the unsafe way to be wrong.
Only sides, top, bottom, shelves and dividers count, matched on the first two
characters of the code because `suffix_labels` may already have made "01" into
"01b" on the bespoke panel itself. Room depth does not enter the formula, and
there is **no clear-floor check for laying a carcass out** — ruled out of scope,
because laying out elsewhere and walking it in is normal practice.

Names from the job file — wall ids, opening and obstruction kinds — go into SVG
escaped, and into export file names through `api._safe_name`, so a job called
`../x` cannot write outside `out/`.

Still open, and **not to be guessed into `Standard`**:

- whether kitchen appliances need to be room objects with clearances, and whether
  worktops are in scope;
- the offset measuring depth and sign convention (shipped with the spec's
  proposed defaults, still awaiting confirmation);
- where the legs stand, for drawing them — only the rear setback (50) is ruled,
  and only the tip-up check uses it, so legs are still not drawn.

Corner units are parametric (ruled 14 Sept 2026, spec items 11-15):
`corner_style` ('mitre' | 'ell') plus `arm_a`, `arm_b`, `face_a`, `face_b` on
`Cabinet`; `room.corner_outline` derives the plan outline and `room.geometry`
uses it as `source == "corner"`, ahead of an entered `footprint`. There is no
angle field — a mitre's angle falls out of the four measurements, 45° only
when `arm_a - face_b == arm_b - face_a`, and nothing compares it with 45. It is
reported, never entered: `CabinetGeometry.mitre_deg` and `.face_lengths` (read
off `.front_faces`) go out through `/api/compute` and show in the editor's
readout, which is how a door and its reveal are read against the face it hangs
on — cabinet 7's 472 door in a 495 face. `swing_envelopes` hinges a corner
unit's door off its real front face (the mitre edge, or for an ell whichever
face carries the door) rather than the outline's extreme corner. An ell with one
door hangs it on the shortest face it fits (the longest if neither), from the
outer end, or the notch end if flipped; with two, one per face from the ends away
from the notch. The validator checks the four measurements against the sides that
were cut: each open face must match a side, and the two remaining wall sides must
be one board short of one arm and two short of the other (cabinet 7: 834 / 818).
A door wider than the longest face it could hang on is a warning too — it cannot
close in the opening, and its swing runs back into the box.
`room.corner_shadow` is what lets a corner unit placed flush in a corner fill
the start of the *next* wall's run for `gaps`/`runs` purposes too, and
`overlaps` is checked in world coordinates across every wall at once rather
than one wall at a time, so a cabinet placed into that shadow is still caught.
The October fixture's cabinet 7 carries its real measurements — `arm_a`/`arm_b`
850, `face_a`/`face_b` 500, mitre — cross-checked against its own panels in
`docs/ROOM-LAYOUT-SPEC.md` item 14. A corner unit with no outline and no
corner parameters still falls back to the panel-extents rectangle, with a
warning that names the cabinet and calls it an approximation, not a
measurement.

Everything the filler, plinth and hinge-drawing work needed was ruled on
14 September 2026 and is in `Standard`.

## Not built yet

0. **Dividers.** `divider_count` / `divider_height` still generate a code-09
   panel, but nothing positions one and shelves do not divide around it, so the
   three controls are greyed in the editor and labelled unavailable. Whatever is
   built has to answer where a divider stands before it answers anything else.
   Added panels — exposed ends (08) and the rest — come with the same piece of
   work.
1. **CAD export.** DXF per panel plus a parameter table SolidWorks can drive a
   configuration from, so the model and the cut list cannot diverge.
2. **Obstruction cut-outs on backing panels.** Deferred 14 September 2026 for the
   same reason as sliding doors: an obstruction behind a carcass is drawn, but no
   cut-out goes on the cut list until a real job supplies a real pipe position.
3. **Sliding doors.** Not urgent, but leave the seam. A hinged door is a
   property of one carcass; a slider spans an opening that may cover several.
   When it is built it needs a `DoorSet` above `Cabinet`, not more fields on it.
   The arithmetic that changes:
   - height = H - top track - bottom track  (roughly 40-50 and 10-20)
   - width  = (opening + overlap x (n-1)) / n, overlap around 50
   - pot holes = 0
   - carcass depth reduced by the track depth, around 100, decided per run
   - framed doors: board panel is smaller than the door by the frame section,
     and usually carries no edging
   Real numbers come from a real job, the same way everything else here was
   derived. Do not guess them into Standard before then.

## Things that will bite you

- Plazaboard's `holes` column is the **line total** (per panel × qty). Ours is
  per panel. `export_plaza.rows_for` does the multiplication — don't double it.
- Edging includes a **70 mm trim allowance per banded edge**. The formula in
  `Standard.edging_m` is exact on all 166 edged rows of the real job. Don't
  "simplify" it.
- Grain must be 1 on every décor panel. On the last job it was 0 on all 60 and
  only Plazaboard's counter caught it.
- A panel longer than 2750 mm cannot be cut. One got through last time and came
  back 152 mm short with nobody told.
