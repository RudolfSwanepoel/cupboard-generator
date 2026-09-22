# Stop — board pictures, Pictures/ in git, out/ → output/

22 September 2026. Standalone work, not part of the lettered Part A–F sequence.
Branch `master`, repo `C:\Dev\CupboardApp`.

---

## The one thing worth remembering

**A board picture had never once displayed, and the path was never the cause.**
The server answered `/` and the API routes and 404'd everything else. There was
no static-file route at all, so `<img src="C:\Dev\CupboardApp\Pictures\Storm
Grey.jpg">` resolved against `http://127.0.0.1:<port>/` and came back 404.
Taking the stray quote characters out of the path changed nothing because
nothing was ever being fetched — and a `file:` src would not have helped either,
since every engine blocks a `file:` sub-resource on an `http:` page.

Two sessions were spent on the path. The path was a symptom.

---

## Diagnosis (B1–B3)

### B1 — why STORMGREY did not display

`app/api.py` `do_GET` served `/` and `ROUTES` and nothing else. Confirmed live
against a running server: `/` → 200, the absolute path → 404,
`/Pictures/Storm Grey.jpg` → 404.

Against the three sub-questions in the brief:

- **(a) the library / captured-copy split was not it.** The quotes were gone
  from both `boards.json` and `jobs/Test.json`'s captured copy, and they agreed.
- **(b) not a cache.** Nothing was ever served, so there was nothing to cache.
- **(c) both files existed and were readable** — `Storm Grey.jpg` 9 KB,
  `Brookhill.png` 972 KB. Brookhill did not display either, for the same reason.

### B2 — picker and drag-and-drop

pywebview **6.2.1**, backend `winforms`, renderer `edgechromium` (WebView2),
pythonnet 3.1.0.

- **`create_file_dialog` works, called from a background thread** — which is
  where the HTTP handler lives. Tested live inside the real app: the native
  "Open" dialog opened, blocked 3.2 s, and returned `None` on cancel.
- **Drag-and-drop cannot give a filesystem path on this backend.** pywebview
  6.2.1 has no `file_drop` event (its events are closed / closing / loaded /
  before_load / before_show / initialized / shown / minimized / maximized /
  restored / resized / moved / request_sent / response_received), and WebView2
  does not expose `File.path` to JS the way Electron does.
- **It can give the bytes, reliably.** Standard HTML5 drop → `FileReader` → POST
  the contents, and the server writes them into `Pictures/`. That is real
  drag-and-drop, not a fake; it uploads rather than links.

### B3 — output folder (one correction to the brief)

It was literally `out`, but **per-job subfolders already existed**: `export()`
wrote `os.path.join(OUT_DIR, job.name)`. So D2's premise was already satisfied
for the app's own export. The only thing writing to the root of `out/` was
`tools/regen_check.py`, dropping loose `nest_*.svg`.

### D3 — confirmed unrelated

The external cut list is `tools/../../Wardrobes/R Swanepoel Cutlist.xlsx`, two
levels above the repo. Nothing to do with `out`. It is not present on this
machine, so `regen_check` already skips that diff (and therefore does not print
the "22 cabinets reproduce exactly" line).

---

## What was built

### `cabinetgen/pictures.py` — the one answer

Where a picture lives (`Pictures/`, flat), what is stored
(`Pictures/Storm Grey.jpg`, relative to the repo) and what a page asks for
(`/pictures/Storm%20Grey.jpg`, through `url_for`). The browser is handed
`picture_url` off `/api/boards` as a derived field beside `tapes` and `offered`,
and never works a URL out from a stored path.

- **Stored relative, never absolutely.** `boards.json` is shared through git, so
  an absolute path in it is one machine's answer written down as if it were
  everybody's.
- **Copied in, not pointed at.** Browse… and a drop both end at `install` /
  `install_bytes`, which put the file into `Pictures/` — suffixing `-2` rather
  than overwriting a different file of the same name.
- **A `data:` URI passes through untouched.** It is already the picture rather
  than a pointer at one.

### The route

`GET /pictures/<name>` — a **basename lookup into one flat folder** with an
extension from `pictures.TYPES`. The name comes from a file somebody can edit,
so it may not name a parent, a drive or anything else in the repo, and the
extension check also keeps the route from becoming a way to read the repo.
`safe_name` flattens a traversal rather than refusing it.

### The two ways in

- **Browse…** → `/api/pick-picture` → pywebview's native Open dialog on the
  window `run_app.py` now hands to `api.set_window`. Cancelling is `cancelled`,
  not an error, and says nothing.
- **No window** (`--no-window`, or the browser fallback) → the reply says
  `no_window` and the browser's own file input takes over.
- **A drop on the swatch**, and the file input, both → `/api/drop-picture`,
  which takes the bytes.

The picture field in the editor is **read-only**: there is nothing to type any
more, which is what removes the quote-character failure mode entirely rather
than guarding against it.

**A stray drop anywhere else on the window is swallowed** — the browser's
default is to navigate to the dropped file, which would throw the app and the
unsaved job away.

### On save

A picture that names no readable image is **refused, with a sentence saying
why** — never dropped quietly, because a picture that silently does not arrive
is the whole bug. A stored absolute path inside `Pictures/` squares up to the
relative form on the way through, so an old record migrates the first time it is
saved — and **`url_for` draws it either way**, so a saved job carrying the old
absolute form still shows its picture without being rewritten. Files on disk
change only when saved.

### `Pictures/` in git

Committed, with `Brookhill.png` and `Storm Grey.jpg`.

### `out/` → `output/`

`app/api.py`, `.gitignore`, `README.md`, `CLAUDE.md`, and
`tools/regen_check.py`, which now writes `output/wardrobe_oct2025/` instead of
loose files at the root — the same one-folder-per-job rule `/api/export` already
followed. The old `out/` stays in `.gitignore` so a stale folder left on a
machine does not turn up as untracked.

---

## Per-ID result

| ID | What | Result |
|---|---|---|
| B1 | Why STORMGREY did not display | **pass** — no static route existed; cause reported above, confirmed live |
| B2 | Picker / drag-and-drop feasibility | **pass** — native dialog works off-thread; drop gives bytes, not a path |
| B3 | Current output structure | **pass** — `out`, and per-job subfolders already existed; brief corrected |
| C1 | Browse… button + drop zone | **pass** — both exercised in the running app |
| C2 | Copy into `Pictures/`, store relative | **pass** — a file picked from outside the repo lands as `Pictures/<name>` |
| C3 | Sanitize on save | **pass** — quoted absolute path accepted and squared up; missing file and non-image refused with a clear message |
| C4 | Rudolf re-sets STORMGREY through the new UI | **not tested by me** — his to do; the picture now displays from the path already stored |
| D-pics | Commit `Pictures/` | **pass** |
| D1 | Rename to `output/`, update every reference | **pass** |
| D2 | Per-job subfolders | **pass** — already true for `/api/export`; `regen_check` brought in line |
| D3 | External xlsx untouched | **pass** — two levels above the repo, unrelated |

### What was exercised in the running app, not only in Python

- Both board swatches render from `/pictures/...` (`naturalWidth` non-zero —
  they are really decoded images, not placeholders).
- The editor's picture box: preview, Browse…, Clear, the read-only field and the
  note.
- **A real drop** — a `DragEvent` carrying a `File` on the zone: the zone
  highlights on dragover, the file is copied into `Pictures/`, the preview
  updates, the note names the file it was saved as.
- **De-duplication** — dropping `Storm Grey.jpg` when one already existed stored
  `Pictures/Storm Grey-2.jpg`.
- **Clear** empties the field, swaps the preview back to the hatched placeholder
  and says so.
- **Browse… with no window** falls through to the file input rather than doing
  nothing.
- **The native dialog opens from the real app** — window registered, dialog
  titled "Open", blocked 3.2 s, cancel returned `{ok: false, cancelled: true}`.
- **Route safety** — traversal 404, non-image 404, missing 404.
- **Export** — `output/Test/` (11 files) and `output/wardrobe_oct2025/`, two
  jobs, two folders.
- **An old job still resolves** — loading `Test.json`, whose captured copies
  still hold the absolute paths on disk, draws both pictures and brings the
  relative form in through `refresh_from_library`. The file on disk is untouched.
- No console errors at any point.

### Verification

- `regen_check`: 272 MEL / 59 BROOKHILL / 30 BACK, 92 pot holes, 18 / 9 / 6
  boards, **R28,363.50**.
- Every `tools/check_*.py`: 15 of 15 pass, including the new
  `tools/check_pictures.py`.
- `Check It Still Works.bat`: clean (now runs `check_pictures` too).
- `snapshot.py --compare`: **identical**. See the note below about the baseline.

---

## Two things to know

**`baseline.json` was already out of date before this work started.**
`snapshot.py --compare baseline.json` differs on a clean checkout because of
uncommitted edits in `jobs/Test.json` — a new cabinet 9, and drawer faces
192/195 changed to 187/200 fixed. That is Rudolf's work in progress, not a
regression, and it was not touched. A snapshot of the tree as it stood before
any of this work was taken instead, and the comparison against that is
identical, so nothing here moved a panel, an issue, a cost or a drawing.
`baseline.json` was **not** regenerated — that is Rudolf's call once he has
finished with Test.json.

**`jobs/Test.json` was deliberately left uncommitted.** It carries only his
in-progress edits. `boards.json` had to be committed because the picture paths
in it are part of this fix; his colour tweak to BROOKHILL (`#d2b36a` →
`#c6a65d`) came along with it.

---

## Still open, unchanged

- The **plan** drag's `pointerdown` still awaits `/api/drag` before attaching
  its listeners, so a quick drag can let go before anything is listening. The
  elevation drag was fixed on 18 September 2026; the plan's never was.
- **Q1** (line endings and git hygiene) and **Q5** (`WHITE_EDGE`) are still
  unruled.
- **Part F (3D)** is not started.
