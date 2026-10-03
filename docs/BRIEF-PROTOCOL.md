# Brief protocol

Every brief from now on opens with "Run under `docs/BRIEF-PROTOCOL.md`". The
session follows this page in order.

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
   foresee, the open items for Rudolf, a Status line in CLAUDE.md (one line),
   and the full write-up in `docs/history/<brief-file-name>.md`, listed from
   `docs/HISTORY.md`.

## Standing rules every brief inherits

Written once here, not repeated in each brief:

- **One session on the repo at a time** — a brief starts only when the
  previous one has merged.
- Never `checkout` / `reset` / `stash` without asking.
- Review diffs with `--ignore-space-at-eol`.
- A check never reads live workshop data.
- The browser works out no geometry.
- Hard rule 9 — nothing lost, anything moved listed.
