# UI build brief

Everything the engine needs already exists. This is the front end only.

## Decisions already made — don't reopen them

- **Form/list first, canvas later.** Add a cabinet, set its width, pick options.
  A pan/zoom elevation canvas is a later job.
- **Local desktop, single user.** No accounts, no server, no cloud.
- **Criticals block export, warnings don't.** `validate.blocking()` already
  answers this.
- **Job files are JSON** via `cabinetgen/store.py`. They must stay readable and
  diffable — a job file is a record of what was ordered.

## Shape

Serve it over `http.server` on `127.0.0.1`, and open it with `pywebview` if
that's installed, otherwise the default browser. Two reasons: it runs even
without pywebview, and it can be tested by hitting the endpoints directly.

```
run_app.py        starts the server, opens the window
app/index.html    the whole UI, vanilla JS, no framework
app/api.py        request handlers, thin — they call cabinetgen and return JSON
```

No build step. No npm. The engine has no dependencies and the UI shouldn't add
any; openpyxl is only used by the regression tool.

## Screens

One page, four tabs, with a summary strip always visible across the top:
panels, boards by material, estimated cost, and the critical/warning count.

**Cabinets** — the working screen. A table of cabinets, and above it the
elevation from `render.elevation_svg(job)` so the run can be checked at a
glance. Clicking a row opens an edit panel. Fields, grouped:

*(Superseded 18 September 2026 — the sections as built are in CLAUDE.md, "The
UI". Kept here as the original brief.)*

- *Size* — width, height, depth, kind (tall / upper / base)
- *Structure* — back (four / three / none), supports, edged supports, white
  supports, shelves, fixed shelves, shelf width, dividers, divider height
- *Fronts* — doors, door height, drawers (count, box height, base material,
  and face mode: equal / ratio / exact heights)
- *Finishes* — décor, carcass edge, door edge, drawer box edge, exposed sides

Duplicate-cabinet is worth having early; runs are mostly repeats.

**Cut list** — every generated panel, grouped by cabinet, with validation
messages attached to the rows they belong to.

**Nesting** — board counts and yields per material, and the sheet layouts from
`nest.sheets_svg(sheets, title)` injected straight into the page.

**Validation** — the full issue list, criticals first, each with its finding
reference. This is the screen that has to be convincing; it is the reason the
app exists.

## API surface

The handlers should be thin. Everything below already exists:

```python
from cabinetgen.engine   import generate_job
from cabinetgen.validate import validate, report, blocking
from cabinetgen.nest     import nest_job, sheets_svg, NEST_REJECTS
from cabinetgen.export_plaza import summarise, estimate_cost, write_csvs
from cabinetgen.render   import elevation_svg
from cabinetgen.store    import save, load, job_to_dict, job_from_dict, next_number
from cabinetgen.drawers  import stack, equal_faces, graduated_faces, faces_with_fixed
```

One `POST /api/compute` that returns panels, issues, summary, cost, elevation
SVG and nest SVGs in a single payload is simpler than many small endpoints, and
the whole job computes in well under a second.

Drawer faces come from `drawers.stack(height, spec, boxes, door_height=...)`.
`spec` is an int for equal faces, a list under 50 for ratios, or a list of
actual heights. Exact heights are never silently adjusted — that is deliberate.

## Done looks like

- A new kitchen can be built, validated, nested and exported without touching
  Python.
- `python tools/regen_check.py` still reports 22 clean cabinets, 18/9/6 boards
  and 92 pot holes. The UI must not change any number the engine produces.
- Loading `jobs/wardrobe_oct2025.py`'s job as JSON shows 19 cabinets and the
  elevation looks like the real wardrobe.

## The dock and the 3D tab (23 September 2026)

The cabinet editor is ONE element, `#editor`, docked as a right-hand column on
the Cabinets, Room and 3D tabs and moved between them — never cloned, so
there is nothing to disagree with it. Its dock collapses to a thin strip with
a chevron, resizes by dragging the strip, and remembers both per viewer in
`localStorage` (wrapped, and the app works without it). With nothing selected
it says "Select a cabinet in the drawing or the list". The selected cabinet's
own criticals and warnings sit at its top, one line each, linking to the
Validation tab.

The **3D view** tab: a toolbar (views, Persp/Ortho, display mode, layer
toggles shared with the plan, Fronts, Clearances, Walls, Ceiling, Labels,
Isolate, Snapshot, ?), then a row of the collapsible item list, the viewport
(view cube top right, part card bottom left, legend bottom right) and the
dock, then a status line saying what is under the cursor or how the current
gesture is going. The viewport fills the window below the tab bar and never
makes the page scroll. Everything in it is `app/view3d.js`, loaded the first
time the tab opens.

## Don't

- Don't put dimension logic in the front end. If the UI needs a number the
  engine doesn't expose, add it to the engine.
- Don't let the UI write a cut list that skips validation.
- Don't add a framework or a bundler for a single-user local tool.
