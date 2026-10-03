# Brief 0 — The brief protocol, and CLAUDE.md slimmed

2 October 2026. From Cowork, agreed with Rudolf the same day. Run AFTER the
room-redo Phase 1 session has pushed and before Brief A. No code changes: the
benchmark and every check must come out exactly as they went in.

## Why

Anthropic's own guidance for Claude Code: the context window is the one
constraint behind every other practice, performance degrades as it fills, and a
bloated CLAUDE.md "causes Claude to ignore your actual instructions". Ours is the
whole project history, read in full at the start of every session before a line
of work is done. The hard rules are buried in it. This brief moves the history
out, keeps what a session must know, and writes down once how every brief from
now on is run.

## Part 1 — `docs/BRIEF-PROTOCOL.md` (new)

One page. Every brief from Brief A on opens with "Run under
docs/BRIEF-PROTOCOL.md". Its content, which the session follows in order:

1. **Read** the brief, CLAUDE.md and whatever CLAUDE.md points at for the area
   the brief touches. Nothing else yet.
2. **Plan** (plan mode): explore the files the brief names, write the
   implementation plan — files, functions, order of parts, which existing
   checks each part will move — and stop for Rudolf's approval. Where the brief
   leaves a ruling open, the plan says so and proposes nothing in its place;
   the hard rules and the open-items list in CLAUDE.md are not reopened.
3. **Task list**: one task per numbered item of the brief, each carrying its
   "Done when" line verbatim. Done is what the line says, not a judgement.
4. **Build in order**, one commit per part, `python tools/check_all.py` green
   at every commit. A part that cannot be finished without a ruling stops
   there and says so; nothing is guessed into `Standard`.
5. **Evidence, not assertion**: the report quotes the `check_all` summary, the
   benchmark line (272 / 59 / 30, 92 pot holes, 18 / 9 / 6, R28,363.50), each
   Playwright stage's result, and `snapshot.py --compare` against the tree
   before — and lists every figure that moved, with the brief's reason.
6. **Review in a fresh context** before reporting done: a subagent that sees
   only the diff and the brief checks that every item is implemented, every
   "Done when" is proven, and nothing outside the brief's scope changed.
   Gaps that affect correctness or the stated requirements only; fix and
   re-review.
7. **Report back**: the evidence, what moved and why, what the brief did not
   foresee, the open items for Rudolf, and the Status entry written to
   CLAUDE.md (short — see Part 2) with the full write-up in `docs/HISTORY.md`.

And the standing rules every brief inherits (so they are written once here and
not repeated in each brief): **one session on the repo at a time** — a brief
starts only when the previous one has merged; never `checkout` / `reset` /
`stash` without asking; review diffs with `--ignore-space-at-eol`; a check
never reads live workshop data; the browser works out no geometry; hard rule
9 — nothing lost, anything moved listed. Each brief writes its write-up to its
own file, `docs/history/<brief-name>.md`, listed from `docs/HISTORY.md`; the
CLAUDE.md Status stays ten lines, one per area.

## Part 2 — CLAUDE.md slimmed

Target: **under 2,500 words**. The test for every line is Anthropic's: "would
removing this cause Claude to make mistakes?" What stays, in this order:

1. The one rule that matters (every dimension from `Standard`).
2. **Hard rules 1–9** as a numbered list, verbatim from the project
   instructions (the Cowork project-instructions doc has the current text;
   CLAUDE.md scatters them). Add: "Run every brief under
   `docs/BRIEF-PROTOCOL.md`."
3. Check before you commit: the two commands, what `check_all` does, the
   Playwright scripts in one paragraph, the benchmark figures and what the
   22-of-30 line needs.
4. **Status: ten lines at most** — what is built, as a list of areas with a
   date, and a pointer: "History and the reasoning behind each decision:
   `docs/HISTORY.md`." The current Status entries move there whole.
5. Layout table (as is — it is the map).
6. Key ruled numbers (the block from the project instructions).
7. Conventions (the current section, trimmed to rules only).
8. Open items awaiting Rudolf's ruling (the list from the project
   instructions; the "Still open, not to be guessed into Standard" lines fold
   into it).
9. Where the detail lives: `docs/ROOM-LAYOUT-SPEC.md`, `docs/HOW-IT-WORKS.md`,
   `docs/HISTORY.md`, `docs/RULES.md`, `Claude outputs/`.

Everything else moves, whole and unedited, into two new files:

- **`docs/HISTORY.md`** — every Status entry, in the order they are in now,
  newest first, each under its own heading with its date. Nothing is cut:
  these are the reasons and the measured figures, and a session that needs
  one reads that heading.
- **`docs/HOW-IT-WORKS.md`** — the explanatory sections, each under the same
  heading it has now: Attached panels; The Cabinets tab's 3D; Placing from the
  unplaced list; The 3D view (and its sub-sections); Drawings; Boards, tapes
  and grain (and its sub-sections); Panels; Placing a panel; Zoom; Vertical
  snap; Isolate; Corner units; Supports; The nester; The UI; The room;
  Geometry; Gaps, fillers and scribes; Plinth; Accepting a critical; Drag
  placement; Per-wall elevations; Not built yet; Things that will bite you.
  The **"Where every moved function lives now" table** goes here under its
  own heading, and hard rule 9's list continues there from now on.

"Things that will bite you" stays in CLAUDE.md as well (it is short and every
line prevents a mistake).

Rules for the move: cut and paste, no rewording, no summarising, no "tidying"
— a later brief can prune a section it is working in. A heading that CLAUDE.md
referred to by name is referred to by the same name in its new file. The
CRLF/LF convention of each file is kept.

## Done when

- `wc -w CLAUDE.md` under 2,500; every one of the nine hard rules present by
  number; the layout table, the check commands, the benchmark figures and the
  key ruled numbers present — checked by reading, quoted in the report.
- Every section heading of the old CLAUDE.md is found, by name, in exactly one
  of CLAUDE.md, `docs/HISTORY.md` or `docs/HOW-IT-WORKS.md` — the report lists
  the old headings and where each went (hard rule 9).
- `docs/BRIEF-PROTOCOL.md` exists with the seven steps and the standing rules;
  `docs/history/` exists (empty but for a README line saying what goes there).
- No file under `cabinetgen/`, `app/`, `tools/`, `jobs/` or `tools/fixtures/`
  changed: `git diff --stat` names only `CLAUDE.md` and `docs/`.
- `python tools/check_all.py` 23 of 23 (or whatever Phase 1 left it at — quote
  it); benchmark 272 / 59 / 30, 92 pot holes, 18 / 9 / 6, R28,363.50;
  `snapshot.py --compare` identical.
- One commit. Report back with the heading map and the word count.
