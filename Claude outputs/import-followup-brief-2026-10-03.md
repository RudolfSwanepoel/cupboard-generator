# Brief — Import follow-up, two checks repaired, CLAUDE.md under the limit

3 October 2026. From Cowork, agreed with Rudolf the same day. Run under
`docs/BRIEF-PROTOCOL.md`, from master at 4a47ee2 or later, the only session
on the repo. **Build before the next demo is built and shipped.** Nothing
that cuts, nests or costs changes; the benchmark must not move.

## Rulings (Rudolf, 3 October 2026) — build to these, don't reopen them

1. **A price-only difference is not a conflict.** On import, a board whose
   record differs from this library's only in `Board.price` (Last price), or a
   runner whose record differs only in `Runner.price` (per pair), counts as
   IDENTICAL: it is skipped, listed as identical, and this library's price is
   kept. Any other difference is a conflict exactly as now (ruling 5 of the
   import brief). An imported JOB's own captured prices are untouched, as now.
2. **The jobs a demo shipped with are left out of an import** — whether or not
   the friend changed them. They are listed in the preview as "shipped with
   the demo — left out" and counted in the report, never imported.

## Part 1 — the two import rulings

- **Ruling 1** in `cabinetgen/importer.py`: the board and runner comparison
  (`_board_body`, `_runner_body` and the decisions that read them) leaves the
  price out. Nothing else about identity changes.
- **Ruling 2** needs the demo to say what it shipped, so:
  - `tools/build_demo.py` `assemble()` writes `jobs\shipped-jobs.json` into the
    demo folder beside the jobs it copies: the list of job file names it put
    there. The build's own zip listing (`inspect`) names it. It is data, not
    code, so the no-`.py` rule is untouched.
  - `importer` reads `jobs\shipped-jobs.json` when the picked folder has one
    and leaves those jobs out (preview action `shipped`, not `new` /
    `identical` / `renamed`). The file itself is never imported.
  - A folder with NO such file — the 30 September demo, or Rudolf's other
    laptop — imports its jobs exactly as now, and the report says one line:
    "No list of shipped jobs in this folder: every job was considered."
  - `READ ME FIRST.txt` is unchanged.

**Done when:** `check_import.py` gains (temp folders only, never live data):
a board differing only in price → identical, this library's price kept; a
board differing in price AND colour → renamed as before; the same pair for a
runner; a demo folder with `shipped-jobs.json` naming two jobs, one of them
edited by the friend → both left out, listed `shipped`, the friend's own new
job imported; the same folder without the file → today's behaviour and the
report line. `ui_check_import.py` shows a `shipped` row in the preview. Both
pass.

## Part 2 — two Playwright checks that fail on master

Both failed identically on the tree before the import work (import report,
3 Oct 2026), so they predate it — most likely the room redo changed what they
drive.

- `tools/ui_check_3d.py`, stage `room`: times out on a plan drag, which stops
  the script, so every stage after it has not run since.
- `tools/ui_check_walls.py`: the line "the nook room: none on another".

For each: find the cause first, against the commit where it started failing
(name it). **If the script is out of date with the app, fix the script.** If
the APP is wrong against a ruling in `docs/ROOM-LAYOUT-SPEC.md`, stop and
report it with the evidence and the proposed fix — do not change app
behaviour in this brief.

**Done when:** `ui_check_3d.py` runs every stage to the end and passes, and
`ui_check_walls.py` passes every line — or the report names an app fault with
its evidence and the script is left asserting the ruled behaviour.

## Part 3 — CLAUDE.md under 3,500 words

`wc -w CLAUDE.md` reads 3,536 on the laptop at 4a47ee2 (the Brief 0 report's
own count was 3,468; the two methods count "·" and "—" differently). Use
`wc -w` from now on, and get under 3,500 with room to spare by folding the
oldest Status lines together (for example Boards, Panels and Corner units into
one line naming each with its date) and adding this brief's one line. Nothing
else in CLAUDE.md changes; nothing moves out.

**Done when:** `wc -w CLAUDE.md` under 3,400, quoted; every area the ten
Status lines named is still named.

## Docs

The write-up goes in `docs/history/import-followup-brief-2026-10-03.md`,
listed from `docs/HISTORY.md`. `docs/HOW-IT-WORKS.md`, Demo build: one line on
`shipped-jobs.json`. CLAUDE.md's open items: the two import rulings move from
"ruled, not built" to built (out of the list).

## Checks

- `python tools/check_all.py` all green, quote the count; benchmark 272 / 59 /
  30, 92 pot holes, 18 / 9 / 6, R28,363.50; `snapshot.py --compare` against
  the tree before: identical.
- Every Playwright script run and its result quoted, the two repaired ones
  included.
- One commit per part, pushed to master.

## Report back

The cause of each Playwright failure and the commit it started at; anything
the shipped-jobs list did not foresee; the benchmark line; the word count.
