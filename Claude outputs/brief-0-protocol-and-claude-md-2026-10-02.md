# Brief 0 — The brief protocol, and CLAUDE.md slimmed

Written 2 October 2026, brought up to date 3 October 2026 against master at
427f68b (room touch-ups round 2 and Undo). From Cowork, agreed with Rudolf.
Run ALONE, as the only session on the repo, from current master. No code
changes: the benchmark and every check must come out exactly as they went in.

## Why

Anthropic's own guidance for Claude Code: the context window is the one
constraint behind every other practice, performance degrades as it fills, and a
bloated CLAUDE.md "causes Claude to ignore your actual instructions". Ours is
the whole project history — 50,113 words at 427f68b, 21,023 of them the Status
section — read in full at the start of every session before a line of work is
done. The hard rules are not in it as a list at all. This brief moves the
history and the explanations out, keeps what a session must know, and writes
down once how every brief from now on is run.

## Part 1 — `docs/BRIEF-PROTOCOL.md` (new)

One page. Every brief from now on opens with "Run under
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
   foresee, the open items for Rudolf, a Status line in CLAUDE.md (one line —
   see Part 2), and the full write-up in `docs/history/<brief-file-name>.md`,
   listed from `docs/HISTORY.md`.

And the standing rules every brief inherits (written once here, not repeated
in each brief): **one session on the repo at a time** — a brief starts only
when the previous one has merged; never `checkout` / `reset` / `stash` without
asking; review diffs with `--ignore-space-at-eol`; a check never reads live
workshop data; the browser works out no geometry; hard rule 9 — nothing lost,
anything moved listed.

## Part 2 — CLAUDE.md slimmed

Target: **under 3,500 words** (measured at 427f68b, the sections that stay
come to about 2,350 words as they stand; the additions below about 700 more).
The test for every NEW line is Anthropic's: "would removing this cause Claude
to make mistakes?" Sections that stay are kept as they are — this brief does
not reword them. What CLAUDE.md holds, in this order:

1. **The one rule that matters** — as is.
2. **Hard rules** — the nine below, verbatim (they are the project
   instructions' text; CLAUDE.md does not have them as a list today). Rule 9's
   last line names the checklist's new home, nothing else changes. Then:
   "Run every brief under `docs/BRIEF-PROTOCOL.md`."

   > 1. **A declared dimension must never feed a geometric check.** Declared
   >    depth/width are display labels only. Every check (footprint, overlap,
   >    door swing, tip-up, ceiling clash, fillers, scribes, elevations) must
   >    derive its geometry from the actual panel set via `room.geometry(cab)`.
   > 2. **Panel designations never change once created.** No rename-in-place,
   >    no suffix matching. Generating a cut list is read-only with respect to
   >    the job model.
   > 3. **The regression benchmark must hold** (Oct 2025 wardrobe job): 272
   >    MEL / 59 DECOR(BROOKHILL) / 30 BACK panels, 92 pot holes, 18/9/6
   >    boards, R28,363.50. Re-run and confirm it after any change that could
   >    touch geometry, nesting or costing, and quote the figures in the report.
   > 4. Plazaboard cuts guillotine only, so no tapered or mitred cuts are
   >    possible. Tapers ship as rectangles at the widest dimension plus scribe
   >    allowance; mitres ship as square blanks and are cut on site.
   > 5. The cut list gives FINISHED sizes. Plazaboard deducts edge tape itself,
   >    so never deduct tape thickness. Edging never moves a part in the model
   >    either: tape is drawn inside the finished size.
   > 6. Every board characteristic (edging kinds, Edging Name, colour, picture)
   >    is entered only on the Boards tab. No hardcoded edging anywhere.
   > 7. Door and drawer-face grain runs VERTICAL (Length = face height). This
   >    is correct; never question it.
   > 8. Each dimension is entered in exactly one place in the editor. Panel →
   >    Panel design; corner unit → Corner Unit section; everything else is
   >    greyed and shows the derived value.
   > 9. No current function may be lost in any change. Anything that moves
   >    is listed in the "Where every moved function lives now" table in
   >    `docs/HOW-IT-WORKS.md`.

3. **Check before you commit** — as is.
4. **Status: at most ten lines**, one per area with its latest date (core and
   cut list; boards; panels and attached panels; corner units; supports,
   drawers and runners; 3D; UI; room — redo Phases 1–2, touch-ups, Undo; demo
   build; Import project, if its session has merged by then), then: "History and the reasoning behind each decision:
   `docs/HISTORY.md`." Every line is read off the current Status entries, not
   written from memory.
5. **Layout** — the table as is, plus lines for `docs/BRIEF-PROTOCOL.md`,
   `docs/HISTORY.md`, `docs/history/`, `docs/HOW-IT-WORKS.md`.
6. **Key ruled numbers** — verbatim:

   > Scribe allowance 15 mm · taper threshold 6 mm (across the cabinet's
   > depth) · filler width 50–150 mm · plinth height 100 mm, setback 50 mm ·
   > legs 98–122 mm (nominal 100), always present on base-family carcasses ·
   > rear leg setback 50 mm · back/base groove 8 mm deep, 6 mm engagement ·
   > 16 mm cavity behind backing · door gaps 3 mm single / 6 mm pair ·
   > hinge_clearance 50 mm · mitre_shelf_clear 3 mm · arm-shelf max depth
   > rounded down to the nearest 5 mm · panel and blind-panel code 08 ·
   > support W − 32 × 100, code 04 · new-cabinet supports: base Front + Top
   > Rear + 2 Back, wall 3 Back, tall 4 Back, mitre/ell none, blind by kind.

7. **Conventions** — as is.
8. **Open items awaiting Rudolf's ruling — don't guess these.** This list,
   then the lines of the old "Still open, and not to be guessed into
   `Standard`" paragraph (Per-wall elevations) and the open questions named in
   the old Status that are still unruled, each with where it was raised — no
   item added that the repo does not already name:

   > - `offset_depth` default and sign convention
   > - Plazaboard sign-off on codes 10 (Plinth) and 11 (Filler/Scribe)
   > - Kitchen appliances as room objects with clearances
   > - Worktops: ruled 2 Oct 2026 that worktops and table tops are post-form
   >   or stone, never cut by this app, drawing only, and later — how they are
   >   drawn is open
   > - Ell corner construction
   > - Bespoke cupboard shapes generally

   And, recorded as RULED (2 Oct 2026, from
   `Claude outputs/room-redo-phase1-brief-2026-10-02.md`, which asked for them
   to go into the spec and they did not): a **peninsula** is a run of ordinary
   base units of the island Kind standing end-on to a wall, placed free (room
   Phase 4), with an attached end panel; a **table nook** is out of scope.
   Add the same three lines to `docs/ROOM-LAYOUT-SPEC.md`'s open-items list
   (item 9 "Worktops" there gets the 2 Oct ruling beside it).

9. **Things that will bite you** — as is. Stays in CLAUDE.md only.
10. **Demo build** — a three-line pointer: what `Build Demo.bat` makes, that
    it expires 60 days after the build, and "Full detail: `docs/HOW-IT-WORKS.md`,
    Demo build." The full section moves.
11. **Where the detail lives**: `docs/ROOM-LAYOUT-SPEC.md`,
    `docs/HOW-IT-WORKS.md`, `docs/HISTORY.md` and `docs/history/`,
    `docs/RULES.md`, `docs/UI-BRIEF.md`, `Claude outputs/`.

Everything else moves, whole and unedited, into two new files:

- **`docs/HISTORY.md`** — the whole old `## Status` section (lines 115 to
  1931 at 427f68b) in the order it is in now, newest first, each entry under
  its own heading with its date — EXCEPT the "Where every moved function lives
  now" table, which goes to HOW-IT-WORKS. Nothing is cut: these are the
  reasons and the measured figures. At the top, a short index of
  `docs/history/` (empty for now).
- **`docs/history/`** — a folder with one README line: each brief's write-up
  goes here as `<brief-file-name>.md`, and `docs/HISTORY.md` lists it.
- **`docs/HOW-IT-WORKS.md`** — each of these sections under the same heading
  it has now, in the order it is in now: Demo build; Attached panels; The
  Cabinets tab's 3D; Placing from the unplaced list; The 3D view (and its
  sub-sections); Drawings (and its sub-sections); Boards, tapes and grain (and
  its sub-sections); Panels; Placing a panel; Zoom; Vertical snap in the wall
  elevation; Isolate; Corner units (and its sub-sections); Supports; The
  nester; The UI; The room; Geometry; Gaps, fillers and scribes; Plinth;
  Accepting a critical; Drag placement; Per-wall elevations; Not built yet.
  And **"Where every moved function lives now"** under its own heading, all
  rows kept, Room redo rows included; hard rule 9's list continues there.

Rules for the move: cut and paste, no rewording, no summarising, no "tidying"
— a later brief can prune a section it is working in. A heading CLAUDE.md
referred to by name keeps that name in its new file; a cross-reference inside
a moved section ("see **Corner units**") is left as it is. Each file keeps the
working tree's line endings.

## Done when

- `wc -w CLAUDE.md` under 3,500; the nine hard rules present by number and
  verbatim (rule 9's location line aside); the layout table, the check
  commands, the benchmark figures, the key ruled numbers and the open-items
  list present — quoted in the report.
- Every heading (`#`, `##`, `###`) of the old CLAUDE.md is found, by name, in
  exactly one of CLAUDE.md, `docs/HISTORY.md` or `docs/HOW-IT-WORKS.md` — the
  report lists the old headings and where each went (hard rule 9). The total
  word count of the three files is within 1 % of the old CLAUDE.md plus what
  Part 2 adds (nothing was dropped).
- `docs/BRIEF-PROTOCOL.md` exists with the seven steps and the standing rules;
  `docs/history/` exists with its README line.
- The only files changed: `CLAUDE.md`, `docs/` (new files, and the open-items
  lines in `ROOM-LAYOUT-SPEC.md`). Nothing under `cabinetgen/`, `app/`,
  `tools/`, `jobs/`, `tools/fixtures/` or `Claude outputs/` — `git diff --stat
  --ignore-space-at-eol` quoted.
- `python tools/check_all.py` the same count as on the tree before (23 of 23
  at 427f68b) — quote it; benchmark 272 / 59 / 30, 92 pot holes, 18 / 9 / 6,
  R28,363.50; `snapshot.py --compare` identical.
- One commit, pushed to master. Report back with the heading map and the word
  counts.
