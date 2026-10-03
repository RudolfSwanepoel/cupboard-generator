# Brief — Import project, and renaming a project

3 October 2026. From Cowork, agreed with Rudolf the same day. **Build after
Room redo Phase 2 is in and tested, before the next demo is shipped.** Nothing
under `cabinetgen/` that cuts, nests or costs changes; the benchmark must not
move.

## Why

The demo is a folder: a friend's jobs, any boards, runners and pictures he
added, all live beside the exe. A new demo unzips to a new folder that knows
none of it, and the old one will usually have expired by then. Rudolf wants
one button that brings a whole old folder's work across, safely, and the
same tool for himself moving work between laptops.

## Rulings (3 Oct 2026) — build to these, don't reopen them

1. **One feature, everywhere.** A button **Import project** in the top bar,
   beside Save / Load / Delete. Identical in the normal app and the demo build
   (nothing in `app/demo.py` touches it). It works on an EXPIRED demo's folder:
   it only reads files there, never runs anything in it.
2. **Picking the folder.** The button opens the native folder picker
   (pywebview `FileDialog.FOLDER`, through the window `run_app.py` hands to
   `api.set_window`, as Browse… does for pictures). In the browser fallback
   (`--no-window`) there is no folder picker: the button says so and offers a
   typed path. The app checks the folder is a Cupboard App folder before
   doing anything — it has `jobs\` with at least one readable job, or the
   demo exe beside `jobs\` — and if not, says what it looked for and stops.
   The user may pick the demo's outer folder or the inner `Cupboard App Demo`
   folder; both are found.
3. **What comes across:** job files (`jobs\*.json`, not `jobs\_deleted\`),
   boards and runners from that folder's `boards.json` / `hardware.json` that
   the imported jobs or the library lack, and board pictures from its
   `Pictures\`. NOT exports, snapshots, `output\`, `demo-seen.txt`, or the
   app's own files. Nothing in the old folder is changed or moved — it is a
   COPY ("move across" in Rudolf's words means into the current app).
4. **A preview first, then Import.** After the folder is picked, a dialog
   lists every item that will come in, each with what will happen to it —
   new, identical (skipped), or a name conflict (renamed) — and an **Import**
   button. Nothing is written until Import is pressed. Cancel writes nothing.
5. **Conflicts are renamed "(imported)", and the rename is real.** An item
   whose name is already taken here and whose content differs comes in under
   `<name> (imported)` — `(imported 2)`, `(imported 3)` if that is taken too —
   and it is SAVED under that name and SHOWN under it wherever it is listed or
   selected. That holds for every kind:
   - a **job**: `Test (imported).json`, `job.name` "Test (imported)";
   - a **board**: name `<name> (imported)` and a new id (`boards.next_id`), and
     every imported job that named the old id is rewritten to the new id
     (`rename_board_in_job`) BEFORE it is saved — otherwise opening it would
     take this library's board of the same id (`refresh_from_library` copies
     name, token, thickness, grain and picture by id) and quietly change what
     his job is cut from;
   - a **runner**: name `<name> (imported)`, a new id (`hardware.next_id`),
     every imported cabinet and job runner copy re-pointed the same way;
   - a **picture**: `<file> (imported).jpg`, and every imported board that
     named it re-pointed.
   An item identical in content (job byte-for-byte after migration, board and
   runner record equal, picture bytes equal) is skipped and listed as such.
   An imported job's captured prices are its own and are never touched.
6. **Every one of those is renamable afterwards**, and a rename is carried
   to every place the name is used:
   - **Project (job) rename** — NEW: a **Rename** next to the project name in
     the top bar. It renames the job file in `jobs\`, `job.name`, the job's
     `output\<job>\` folder (named through `_safe_name`, including
     `cutlist\`, `nesting\`, `drawings\`, `snapshots\`, `_previous\`) and every
     file inside whose name starts with the old job name (`<job>_*.csv`,
     `<job>_accepted.txt`, `<job>_plan.svg`, `<job>_elevation_*.svg`,
     `<job>_3d_<n>.png`). The job open on screen follows; the job list
     refreshes. It is a move, not a copy — no second file is left behind.
   - **Board rename**: as built today (`board_save` with `from`), which
     already carries the id through the project on screen and names saved
     jobs keeping theirs.
   - **Runner rename**: its name is editable on Catalogue → Runners, as
     today; its id stays a key (say so in the report if a full id rename is
     needed for anything).
   - **Picture rename**: on the board's picture field, a Rename that renames
     the file in `Pictures\` and every board in the library and in every job
     under `jobs\` that names it.
7. **A name already taken is an ERROR and nothing is saved.** Renaming a
   project, board, runner or picture to a name that exists says **"<name>
   already exists — choose another name"** under the field and writes
   nothing; the user must change it. The same applies to **Save**: saving
   the project on screen under a name that is another saved job's file name
   is refused with that message (saving it under its OWN name, as now, is
   unchanged). Names compare case-insensitively, as Windows does.
8. **Import report.** After Import: "Imported 5 projects, 2 boards, 1 runner,
   3 pictures. Skipped 2 identical. Renamed: Test → Test (imported), GREY →
   GREY (imported)." Every imported job is test-loaded during the import
   (through the same load and migration a Load does); one that will not load
   is NOT imported and is named in the report with the reason. The report can
   be copied.
9. **Old jobs come in through the normal migration.** A job saved by an older
   version (the wall chain, before Phase 1) is migrated on import exactly as
   on Load, and saved in the current format. A job from a NEWER version than
   this app (a field this app does not know) is imported as it stands, and
   the report says it came from a newer version.

## Where it lives

- `app/api.py`: `/api/import-scan` (folder → the preview list of ruling 4,
  writes nothing), `/api/import-run` (the scan's list → writes, returns the
  report), `/api/pick-folder`, `/api/job-rename`, `/api/picture-rename`; Save
  gains the name-taken refusal. The decisions — what is identical, what
  conflicts, the `(imported n)` name, the re-pointing — live in one new
  module `cabinetgen/importer.py`, so they are testable without the UI.
- `app/index.html`: the Import project button, the preview dialog, the
  report, the project Rename, the picture Rename, the name-taken message on
  every rename field and on Save.
- CLAUDE.md: a Status entry, the where-it-lives-now rows, the layout table
  line for `importer.py`; the **Demo build** section gains: "To move to a new
  demo: unzip it, start it, Import project, pick the old folder."
  `READ ME FIRST.txt` in the demo zip says the same in three lines.

## Checks

- New `tools/check_import.py` (temp folders only, never the live `jobs\`):
  a fake old demo folder with jobs (one identical to a local one, one
  conflicting by name, one pre-Phase-1 room, one broken JSON), a
  `boards.json` with a new board, an identical board and a conflicting GREY,
  a runner conflict, pictures new / identical / conflicting. Assert: the
  preview lists each correctly and writes nothing; Import writes exactly the
  new and renamed items; the conflicting board's imported jobs name the new
  id and still cost exactly what they cost in the old folder; the broken job
  is reported and absent; the old folder is byte-identical afterwards;
  importing the same folder twice brings nothing the second time.
- Renames: project rename moves the file, the output folder and its
  prefixed files; refuses a taken name (any case) and writes nothing; Save
  onto another job's name refused; picture rename re-points library and jobs.
- `check_all` green; benchmark 272 / 59 / 30, 92 pot holes, 18 / 9 / 6,
  R28,363.50 — quote it; `snapshot.py --compare`: identical.
- A Playwright stage (`ui_check_import.py`): Import project with a typed
  path (the folder dialog cannot be driven headless), the preview, Import,
  the report, the renamed job in the list and opened, a project rename and
  its refusal.

## Report back

What the scan found that the brief did not foresee in a real old demo folder
(build one with `Build Demo.bat`, save a job in it, then import it); the
benchmark line.
