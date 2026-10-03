# Import follow-up, two checks repaired, CLAUDE.md under the limit (3 October 2026)

Brief: `Claude outputs/import-followup-brief-2026-10-03.md`. Run under
`docs/BRIEF-PROTOCOL.md` from master at 72dbc18, the only session on the
repo. Plan approved by Rudolf with two decisions (Status folded to one line;
`shipped-jobs.json` hidden from Load) and two additions (apply the Esc fix;
reword protocol step 7). Nothing that cuts, nests or costs changed.

Commits: 50c5bc7 (Part 1), ccc8cd9 (Part 2), 229285e (Part 3), and the
review's one finding fixed after it (below).

## Part 1 — the two import rulings

- **Ruling 1, a price is not an identity.** `cabinetgen/importer.py`:
  `_board_record` / `_runner_record` are a record without its price, and
  `_board_body` / `_runner_body` (the comparison under another name) are
  built on them. Both decisions — the same id under the same name, and a
  candidate `(imported n)` — compare them. A board or runner differing only
  in `Board.price` / `Runner.price` is `identical`: skipped, so this
  library's record and price are never written. Any other difference is a
  conflict as before. An imported job's captured prices are its own, as before.
- **Ruling 2, the jobs a demo shipped with.** `tools/build_demo.py`
  `assemble()` writes `jobs/shipped-jobs.json`, a JSON list of the job file
  names it copied; `inspect()` names it and its list in the zip listing (or
  says `NO LIST`). `importer.shipped_jobs` reads it; `read_jobs` lists each
  named job as `shipped` (not parsed, its board ids reserve nothing) and
  never imports it. `_job_files` never lists `shipped-jobs.json`, so the list
  is never a job, nor "broken". No list: the note "No list of shipped jobs in
  this folder: every job was considered." in the preview and the report. The
  report: "Left out N projects shipped with the demo: …". `READ ME FIRST.txt`
  unchanged.
- **Rudolf's decision 2:** `api.job_list` does not offer `shipped-jobs.json`
  to Load (the demo's own job list would otherwise show it, and opening it
  would fail).
- The preview (`index.html`): `shipped` rows read "shipped with the demo —
  left out", muted; the summary counts them.

## Part 2 — two Playwright checks that failed on master

Found by running each commit's own scripts against its own app, extracted
with `git archive` into a scratch folder (no checkout).

- **`ui_check_3d.py`, stage `room`** — passed at 8d7a720, failed from
  **2b84d3e** (Room touch-ups 1; then at the placement step). Its failure on
  master dates from **9b1343e** (Placements the left column beside the plan)
  and 948813a (Placements collapsed to a strip, which the script opens): the
  plan is ~300 px wide in the 1400 × 900 test window, so the script's fixed
  120 px drag ran past the end of the 4000 mm wall A and the cabinet landed
  on wall B at x 0 — x never changed and the wait timed out. **The script was
  out of date**: it now drags 1000 mm at the plan's own scale
  (`mmPerPx(planMap())`) and asserts the cabinet stayed on wall A
  (`[0 -> A 1000]`).
- **`ui_check_walls.py`, "the nook room: none on another"** — failing since
  **ed7552f**, the commit that added the line. **An app fault**: typing
  123456 into wall A's length and pressing Esc put the figure back (1000) but
  not its box, which stayed six digits wide (88 against 75) and overlapped G's
  label; before the typing, at the same zoom, no overlap. Against Phase 2
  ruling 5 (Esc cancels) and the touch-ups' item 3 (each length's field sized
  to its figure). Cause: the Esc handler set the value without `planLenFit`
  (a value set in code fires no input event). **Fixed in the app, approved by
  Rudolf**: `inp.value = was; planLenFit(inp); inp.blur();`.

## Part 3 — CLAUDE.md

`wc -w` counts as the laptop does under a UTF-8 locale (`LC_ALL=C.UTF-8 wc -w`
here; the C locale gives 66 fewer). 3,536 before → **3,379** after. The ten
Status lines are one line naming every area with its dates (Rudolf's decision
1); the lines as they were are kept word for word in `docs/HISTORY.md`. The
two import rulings left the open-items list. `docs/BRIEF-PROTOCOL.md` step 7
now says to update the date of the brief's area in the Status line, adding an
area only when it is new (Rudolf's addition).

## Evidence

- `python tools/check_all.py`: **24 of 24 passed** at each commit.
  `check_import.py` 91 → 118 PASS lines (one existing line moved: the
  preview's counts gained `"shipped": 0`).
- Benchmark: **272 MEL / 59 BROOKHILL / 30 BACK, 92 pot holes, 18 / 9 / 6
  boards, R28,363.50.** The 22-of-30 cabinet diff needs the real cut list,
  which is not on the cloud machine.
- `snapshot.py --compare` against 72dbc18: identical.
- Playwright (cloud machine, Chromium 1194, software 3D):
  - `ui_check_import.py` all passed (37; stage `shipped` new);
    `ui_check_walls.py` ALL OK (224); `ui_check_attached.py` ALL OK (34);
    `ui_check_restructure.py` all good (100); `ui_check_undo.py` ALL OK (25);
    `ui_check_drawers.py` all good (126).
  - `ui_check_3d.py` runs every stage to the end (213 ok); stage `room` passes.
    Two lines are flaky here and fail the same way on master's copy, left
    exactly as they are (Rudolf, 3 Oct 2026) — to be confirmed on the laptop:
    "zoom to cursor" (limit < 6 px): 6.4, 6.4, 6.4 px in three full runs,
    6.3 on master's copy, 5.5 (ok) and 6.3 px running stage `f3` alone;
    "within a second of the keystroke" (limit < 1500 ms): 2130, 1095 (ok),
    2037 ms, 1786 ms on master's copy.

## What the brief did not foresee

- `shipped-jobs.json` in `jobs\` would have shown in the demo's Load list
  (hidden, decision 2) and been read as a broken job by the importer
  (excluded from `_job_files`).
- **Found by the fresh-context review:** the Boards tab's job scan
  (`boards.scan_jobs`) also read it, so every new demo's Boards tab would have
  shown "1 job could not be read — shipped-jobs.json". It now skips the list
  (any other unreadable file is still reported), pinned in `check_import.py`
  (`board_list` reports nothing unreadable in the assembled demo).
- A list that cannot be read is treated as no list, with a note naming it.
- The list is by file name, as ruled: a friend who renames a shipped job
  brings it in; one who deletes a shipped job and saves his own under the
  same name has it left out.
- The `shipped` preview check runs as its own stage of `ui_check_import.py`:
  inside stage `import` it left the following `rename` stage timing out on
  the Cabinets tab's first 3D draw. CLAUDE.md still names that script's
  stages as `import`, `rename` (Part 3 changed nothing else in CLAUDE.md).
