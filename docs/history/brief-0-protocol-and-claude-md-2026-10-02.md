# Brief 0 — the brief protocol, and CLAUDE.md slimmed (3 October 2026)

Brief: `Claude outputs/brief-0-protocol-and-claude-md-2026-10-02.md`. Run from
master at 219d15b, the only session on the repo. Documentation only: nothing
under `cabinetgen/`, `app/`, `tools/`, `jobs/`, `tools/fixtures/` or
`Claude outputs/` changed.

## What was done

- **`docs/BRIEF-PROTOCOL.md`** (new): the seven steps and the standing rules,
  in the brief's own words.
- **CLAUDE.md** slimmed to the brief's order: the one rule · the nine hard
  rules (verbatim; rule 9 names `docs/HOW-IT-WORKS.md`) and "Run every brief
  under `docs/BRIEF-PROTOCOL.md`" · Check before you commit · Status, one line
  per area · Layout plus four `docs/` lines · Key ruled numbers (verbatim) ·
  Conventions · Open items awaiting Rudolf's ruling · Things that will bite
  you · The demo build (a three-line pointer) · Where the detail lives. The
  sections that stay were not reworded.
- **`docs/HISTORY.md`** (new): the whole old Status section, newest first,
  one `###` heading per dated entry (the only text added to moved content —
  Status entries were bold lead-ins, not headings), the index of
  `docs/history/` at the top.
- **`docs/history/README.md`** (new, one line) and this write-up.
- **`docs/HOW-IT-WORKS.md`** (new): Demo build, Attached panels through
  Drawings, Boards through Not built yet, each under its old heading in its
  old order; "Where every moved function lives now (Session 1 checklist)"
  last, every row kept.
- **`docs/ROOM-LAYOUT-SPEC.md`**: item 9 Worktops carries the 2 Oct 2026
  ruling; three lines added after the open-items list (worktops, peninsula,
  table nook).

The move was done by a script that sliced the old file by line as bytes, so
every moved line is byte for byte what it was; every new file is CRLF like the
working tree.

## Evidence

- `wc -w CLAUDE.md`: **3,468** (was 50,783). `docs/HISTORY.md` 20,178,
  `docs/HOW-IT-WORKS.md` 28,664, `docs/BRIEF-PROTOCOL.md` 363.
- Heading map: all **67** old headings (`#`, `##`, `###`) found by full-line
  equality in exactly one of the three files — 7 in CLAUDE.md, 60 in
  HOW-IT-WORKS.md; HISTORY.md holds the Status entries under new headings.
- Word total: the three files against the old CLAUDE.md plus every addition,
  counted by the script on the same split: 53,168 vs 53,170 (−0.00 %).
- `python tools/check_all.py`: **24 of 24 passed**, before and after.
- Benchmark: BACK 30 · BROOKHILL 59 · MEL 272 panels, pot holes 92, ~6 / ~9 /
  ~18 boards, estimated total incl VAT R 28,363.50 — unchanged.
- `python tools/snapshot.py --compare` against the tree before: "identical
  apart from what was allowed".
- `git diff --stat --ignore-space-at-eol`: CLAUDE.md and
  docs/ROOM-LAYOUT-SPEC.md modified; docs/BRIEF-PROTOCOL.md, docs/HISTORY.md,
  docs/HOW-IT-WORKS.md and docs/history/ new. Nothing else.
- No Playwright run: nothing under `app/` moved and the brief's Done-when does
  not ask for one.

## What the brief did not foresee

- The old "Still open" paragraph's first two lines are the same items as the
  brief's six quoted open lines, so only its third line (the legs' position)
  was added, saying where it came from.
- The peninsula / table nook / worktop ruling text exists in the repo only in
  Brief 0 itself; it is cited as such.
- The under-3,500 target needed the ten Status lines and the open-question
  lines terse (Rudolf, at approval: 25 words a line at most).

## Ruled at approval (Rudolf, 3 October 2026)

On Import, a board or runner that differs only in price counts as identical
and this library's price is kept; the jobs a demo shipped with are left out of
an import. Recorded in CLAUDE.md's open items as ruled, not built yet —
follow-up brief.

## Open for Rudolf

Nothing new. The open items are the list in CLAUDE.md.
