# Session summary — 20–21 September 2026

Panels, the twitching editor, and a check that was reading live data.

Three commits, all on `master`, all pushed:

| | |
|---|---|
| `ec2df6a` | Editor: stop rebuilding controls on every compute |
| `043d773` | Part D: independent panels |
| `e10ca0e` | The pre-library checks read a frozen fixture, not a live job |

The benchmark held through all three and is what says so: **272 MEL /
59 BROOKHILL / 30 BACK panels, 92 pot holes, 18 / 9 / 6 boards, R28,363.50**,
`snapshot.py --compare` identical on all three fixed jobs, and every
`tools/check_*.py` green at the end.

---

## 1. The twitching dropdowns

**Reported:** dropdowns in the cabinet editor flicker, worst in the Drawers
table and in Structure.

**Measured, in the running app on `Test.json` cabinet 4:**

- **49 of the editor's 59 controls were new DOM objects after a single
  compute.** The ten that survived were Size, Outline and Corner Unit — the
  sections `renderEditor` was not rebuilding, which is why some controls felt
  fine and others did not.
- A **focused `<select>` was removed from the document** and a fresh one focused
  in its place. A native dropdown belongs to the node it was opened on, so that
  closes it. That is the twitch.
- **It never stopped.** With a drawer cabinet selected and nobody touching
  anything: **12 computes and 13 drawer-solves every 4 seconds, for ever.**
  `renderDrawers` → `solveStack` → wrote the engine's heights back → called
  `schedule()` unconditionally → compute → `renderDrawers`. It also lit the
  *unsaved changes* marker on a job nobody had edited, so closing the window
  asked to save.

**Fixed at the root.** The editor is still rebuilt in full from the job on every
compute — it has to be, or a dropdown keeps the options the library had when its
section was last built, which is how "Ordered as" went stale. But the HTML is
now *applied* to the DOM that is already there (`paint`): an unchanged node is
left alone, a changed value is written into the control in place, and only a
control that has genuinely changed shape — or gone — is replaced.

Two rules make it safe:

- **A focused control is never touched**, not its options and not its value.
  Focus is what an open dropdown is, and it is also what is being typed into. It
  catches up the moment focus leaves it.
- **A slot div belongs to its own render function.** `sectionHTML` emits it
  empty and `data-slot` keeps the paint out of it.

`solveStack` now schedules a compute only when a height actually moved. The
`S.selRendered = -2` flags that forced a full rebuild are gone — all they could
do afterwards was destroy the control being used.

**Verified live, per section.** Change a control, let the compute land, check
the node survived and the value held:

| Section | |
|---|---|
| Size | 5/5 |
| Outline | 1/1 |
| Structure | 6/6 |
| Doors | 5/5 |
| Drawers | 18/18 (4 rows × 4, plus 2 edging) |
| Corner Unit | 5/5 |
| Supports | 8/8 |

All 59 controls survived **eleven consecutive computes**. Idle computes went
from 12-in-4-seconds to **none**. The editor's scroll position holds. The
cabinet table is painted the same way — it holds no dropdown, but it was being
rebuilt three times a second too.

**The staleness this replaced did not come back:** cutting BROOKHILL to 2mm-only
on the Boards tab immediately narrowed the support edging lists and flagged
"PVC not offered by BROOKHILL" in the editor, with no reload.

Checked by code only, not driven live: the cabinet drag in the wall elevation
(the change there was removing a force-rebuild flag).

---

## 2. Part D — independent panels

D1 to D9, all passing. A panel is a part that is cut, numbered, costed and
nested on its own and belongs to no carcass; several make a bulkhead, each its
own numbered item.

**Q2 was ruled before building:** code **08**, role **"Panel"**. The fact that
decided it — Plazaboard's CSV writes the Component column from `Panel.label`
alone, never from `CODES[code]` or `Panel.role`, so a new code would need their
sign-off and would say nothing on the order that 08 does not.

**One deliberate deviation from the brief's design note.** It proposed carrying
"panel" on `template` as well as `kind`. It cannot be: switching an item back
from Panel would then have to put `template` where it was, and there is nothing
to put it back from — **October cabinets 3 and 5 are `template="standard"`
carrying hand-specified extras**, so "it has bespoke panels, therefore it was
bespoke" is wrong, and being wrong there rewrites a real cut list. `is_panel`
reads `kind` alone and `template` is never rewritten, so a round trip loses
nothing. Pinned in `check_panels.py`.

**Two things that are easy to get backwards, and are checked both ways round:**

- `Length` IS the grain direction, so on a grained board the extent the grain
  runs along becomes the length whether it is the longer of the two or not.
- Which means the operator's **long and short edges are not `edge_l` and
  `edge_w`** — a panel cut across its grain has its long edges running the
  width. The two are mapped, not assumed equal.

**Exercised in the running app, not only in Python:** Kind → Panel on a new
cabinet; all three orientations relabelling their extents and giving the right
geometry; board, edging kind and banded-edge counts producing the right cut-list
line; the criticals firing and clearing; Duplicate; the Run excluding panels
while the nester includes them; and `jobs/Test_Panels.json` loading, editing and
saving back **byte-identical**.

**Decided beyond the brief, and worth knowing:**

1. `is_panel` from `kind`, above.
2. `room.placed()` skips panels explicitly. The brief puts that in E1; it was
   brought forward because without it a panel could close a gap or carry a
   plinth board the moment anyone gave it a placement.
3. An unknown orientation is a CRITICAL. Silently treating a typo as "upright"
   would put a wrong-sized part in the room.
4. `room.geometry()` takes an optional `materials` — a panel's depth is its
   board's thickness. No other caller's answer changes.

---

## 3. The Test_Build.json check mismatch

Three checks pinned *"a job written before the library still names DECOR"*
against **`jobs/Test_Build.json`, a live job file**. Upgrading that job in the
Boards tab — an ordinary thing to do — renamed its DECOR to BROOKHILL and broke
all three.

**The upgrade was sound.** Same 27 cut-list lines, same designations, sizes,
quantities, grain, edging and total; only the board id moved, on five lines.
That is the rename and the price capture working exactly as designed. Nothing
needed rescuing — the checks were pinning a fact about the past against data the
workshop is free to change.

So the pre-library version is frozen at
**`tools/fixtures/Test_Build_pre_library.json`**, taken verbatim from
`jobs/Test_Build.json` at the baseline commit (`7daedb7`), the only version of
that file in history. It sits outside `jobs/` on purpose: in there the app would
list it as a project and `scan_jobs` would pick it up again, which is the whole
failure repeating.

`check_library`'s folder scan was **split rather than moved**, because it was
asking two questions at once. Whether a board is found under a former id is now
asked of the frozen copy — a fact about the scan. Whether the real folder still
opens is still asked of **the live `jobs/`**, because a job file that will not
parse has to be found live and reported by name.

**Proved, not assumed:** renaming BROOKHILL to something else in the live
`jobs/Test_Build.json` and re-running both scripts gives ALL OK, where before
they died. The live file was restored byte-for-byte afterwards.

This was the **second** time this shape of bug bit. The first was
`check_library` reading the live `boards.json` and dying at line 184 the day MEL
was renamed, with about thirty checks after it silently not running. CLAUDE.md
now states the rule once, for both: **a check never reads live workshop data to
pin a fact about the past.**

---

## Where it stands

**Next: Part E (placing panels), then F (3D). Neither is started.**

One piece of E is already done and **must not be built twice**: `room.placed()`
skips panels. What E still has to build is `Placement.y` (serialised only when
non-zero), `room.placed_panels`, the Placements table's Y column, drawing panels
in the wall elevation and the plan, the drag and its snap targets — including
cabinet tops, for bulkheads — the fat invisible hit area a 16 mm panel needs to
be grabbable at all, the Panels layer toggle, and the clash WARNING.

**Still open, and yours to rule:** **Q1** (line endings and git hygiene — the
working tree is CRLF, HEAD is LF; edits kept each file's existing endings and
`--ignore-space-at-eol` shows only real changes) and **Q5** (`WHITE_EDGE`). The
proposed hard rules **H5** and **H6** are still not in CLAUDE.md, because they
are yours to accept.
