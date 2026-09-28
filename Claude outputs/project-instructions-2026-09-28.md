# CupboardApp — Working Notes for Claude Code

## What this is
Rudolf's melamine kitchen/wardrobe design and cut-list generator, feeding
Plazaboard for cutting. Local desktop app (pywebview), single user. This
repo is the whole app.

## Repo state
- GitHub: https://github.com/RudolfSwanepoel/cupboard-generator.git
- Default branch is `master` (not `main`); set that explicitly when
  pushing or cloning.
- The working copy lives at `C:\Dev\CupboardApp` on each machine, NOT the
  OneDrive folder. The OneDrive copy at
  `2 PROJECT\Cupboard generator\CupboardApp` is stale/legacy: don't
  edit it, and don't treat it as a source of truth.
- Two machines share this repo: "swanepoelr-nb" (work laptop) and
  "desktop-rl1odqo" (home laptop). Cloud sessions (Claude Code → Cloud →
  cupboard-generator → master) build with the laptop off and push to
  master themselves.
- Never run two sessions against the repo at once, and never run
  `git checkout`, `reset` or `stash`, or anything else that discards
  Rudolf's changes, without asking.
- The working tree is CRLF and HEAD is LF. Review diffs with
  `--ignore-space-at-eol`.
- `jobs/` holds only Test.json and the benchmark (wardrobe_oct2025.py).
  Every other job a check needs lives in `tools/fixtures/` and is read
  through `tools/fixture_jobs.job_file`.

## Hard rules — never break these
1. **A declared dimension must never feed a geometric check.** Declared
   depth/width are display labels only. Every check (footprint, overlap,
   door swing, tip-up, ceiling clash, fillers, scribes, elevations) must
   derive its geometry from the actual panel set via `room.geometry(cab)`.
2. **Panel designations never change once created.** No rename-in-place,
   no suffix matching. Generating a cut list is read-only with respect to
   the job model.
3. **The regression benchmark must hold** (Oct 2025 wardrobe job): 272
   MEL / 59 DECOR(BROOKHILL) / 30 BACK panels, 92 pot holes, 18/9/6
   boards, R28,363.50. Re-run and confirm it after any change that could
   touch geometry, nesting or costing, and quote the figures in the report.
4. Plazaboard cuts guillotine only, so no tapered or mitred cuts are
   possible. Tapers ship as rectangles at the widest dimension plus scribe
   allowance; mitres ship as square blanks and are cut on site.
5. The cut list gives FINISHED sizes. Plazaboard deducts edge tape itself,
   so never deduct tape thickness. Edging never moves a part in the model
   either: tape is drawn inside the finished size.
6. Every board characteristic (edging kinds, Edging Name, colour, picture)
   is entered only on the Boards tab. No hardcoded edging anywhere.
7. Door and drawer-face grain runs VERTICAL (Length = face height). This
   is correct; never question it.
8. Each dimension is entered in exactly one place in the editor. Panel →
   Panel design; corner unit → Corner Unit section; everything else is
   greyed and shows the derived value.
9. No current function may be lost in any change. Anything that moves
   is listed in CLAUDE.md's "where it lives now" checklist.

## Where the detail lives
- `CLAUDE.md` in the repo: the full working notes. Claude Code keeps its
  Status section current.
- `docs/ROOM-LAYOUT-SPEC.md`: the room layout / plan / corner-unit spec.
- `Claude outputs/`: briefs and rulings from Cowork. Newest:
  `shelves-supports-spec-2026-09-27.md`, `attached-panels-spec-2026-09-28.md`,
  `ui-restructure-brief-2026-09-28.md`. For corners,
  `corner-units-rulings-2026-09-22.md` wins over the corner brief.

## Status (28 Sept 2026)
- Core app: rule engine, validation, guillotine nester, Plazaboard CSV
  export, job save/load, drawings. Done.
- Room layout Phases 1–5, Boards Parts A–C, independent and placed panels,
  wall snap, plan isolate, output folder, board pictures: done.
- Corner units: mitre and blind generated; ell shape-only (construction
  not ruled, cuts nothing, raises a critical).
- 3D: done — the 3D tab (whole room) and the single-cabinet 3D on the
  Cabinets tab. Shelves, supports and attached panels drawn; drawer boxes
  and legs not yet.
- Shelves and supports (27 Sept): typed Front / Top Rear / Back supports,
  each with its own Cut-from and per-edge edging; placed by rule; legacy
  rows cut as quoted with a Re-enter button; three criticals.
- Attached panels (28 Sept): a panel linked to a cabinet travels with it;
  attach/detach both ways, numbers unchanged; counts in room checks except
  tip-up; delete asks about its panels; duplicate copies them.
- UI restructure (28 Sept): tabs Boards · Cabinets · Room (Plan | Elevation)
  · 3D view · Cut list · Nesting · Validation. Run view removed from the UI;
  export writes one SVG per ticked wall plus the plan (a job with no room
  exports no drawing — ruled). Unplaced items drag onto a wall from Room
  and 3D. Editor Save = full refresh (top-bar Save writes the file).
  Styling round 1 done; mockup-based design round later.
- Deferred: per-cabinet exploded view, CAD export (Phase 7), island
  placement, sliding doors, obstruction cut-outs.
- Known: two Playwright scripts that drag an attached panel wait a fixed
  time after the drop and occasionally read the previous compute. Fix in
  the scripts (wait for the compute), not the app.
- Spot-check with `Check It Still Works.bat` (real Python + openpyxl, and
  the 22-of-30 cabinet diff, which needs the Wardrobes xlsx the cloud
  machine lacks).

## Open items awaiting Rudolf's ruling — don't guess these
- `offset_depth` default and sign convention
- Plazaboard sign-off on codes 10 (Plinth) and 11 (Filler/Scribe)
- Kitchen appliances as room objects with clearances; worktops in scope
- Ell corner construction
- Bespoke cupboard shapes generally

## Key ruled numbers
Scribe allowance 15 mm · taper threshold 6 mm (across the cabinet's depth)
· filler width 50–150 mm · plinth height 100 mm, setback 50 mm · legs
98–122 mm (nominal 100), always present on base-family carcasses · rear
leg setback 50 mm · back/base groove 8 mm deep, 6 mm engagement · 16 mm
cavity behind backing · door gaps 3 mm single / 6 mm pair ·
hinge_clearance 50 mm · mitre_shelf_clear 3 mm · arm-shelf max depth
rounded down to the nearest 5 mm · panel and blind-panel code 08 ·
support W − 32 × 100, code 04 · new-cabinet supports: base Front + Top
Rear + 2 Back, wall 3 Back, tall 4 Back, mitre/ell none, blind by kind.

## Running it locally
Four batch files at C:\Dev\CupboardApp do everything. Name these, never
raw git commands: Start Session.bat (pull, at the start), Finish
Session.bat (commit + push, at the end), Start Cupboard App.bat (launch —
close and relaunch after every pull), Check It Still Works.bat
(real-Python regression check).

## Working across chat threads
Claude Code sessions do NOT share conversational memory with each other.
They share this repo, so `CLAUDE.md`, the specs and `Claude outputs/` are
how context carries over, not the chat history. A cloud session only sees
what is pushed, so a new brief is pushed (Finish Session.bat) before the
session starts. When finishing a session, give Rudolf the exact commit
message to paste.

## When Rudolf types "workflow"
Give the real workflow for where he is right now, not a fixed script. Short numbered next steps, one line each, in order. Name the batch file to run, the Claude Code settings (Local or cloud, model, effort, worktree unticked), and put anything he must paste in a copy box. Say what to check at the end. No git commands, no explanation beyond the steps.
Example of the style:
1. Open Claude Code: Local, CupboardApp, master, worktree unticked, Opus 5.5 on Medium.
2. Paste: [the exact line, in a copy box]
3. When it says it's done, run Check It Still Works.bat.
4. Run Start Cupboard App.bat and test the change.
