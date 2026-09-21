# Session summary — 21 September 2026

Part E: placing panels. Plus the three things that were not in the brief — a
multi-select layer toggle, a sensible default position for a new placement, and
scroll-wheel zoom.

One commit on `master`:

| | |
|---|---|
| *(this session)* | Part E: placing panels |

**The benchmark held throughout and is what says so:** 272 MEL / 59 BROOKHILL /
30 BACK panels, 92 pot holes, 18 / 9 / 6 boards, R28,363.50, `snapshot.py
--compare` identical on all three fixed jobs, and every `tools/check_*.py` green
at the end.

---

## 1. What Part E actually is

One field, one list, one warning, and a lot of machinery being told that a panel
exists.

**`Placement.y`** — out from the wall face to the panel's back. 0 is flush. It
is the field a bulkhead needs and a cabinet does not: a carcass sits against the
wall it is placed on. **Written to the job file only when it is non-zero**, so
every placement written before panels could be placed round-trips byte for byte
— pinned both ways in `check_panels.py`.

**`room.placed_panels(job)`** — the panel-only twin of `placed()`, which stays
cabinet-only. Two lists rather than one, deliberately: `placed()` is what gaps,
runs, plinth, tip-up and door swing come through, and a panel takes part in none
of them. `room._on_wall` is the **one** place the two are read together, because
what something comes to rest against does not care what kind of thing it is.

**`room.panel_clashes`** — a WARNING, never a critical. Two carcasses sharing a
stretch of wall is a critical because the cut list built on it is wrong; a panel
is cut and costed wherever it is and its position moves no figure on the order.
Touching is clear, as everywhere else, so a bulkhead sitting flush on the run
raises nothing. Proved in the running app: driving the front panel down into the
units gave five warnings and `blocking: false`.

Everything else was existing machinery:

- **The drag is the same pipeline**, not a second one. A placed panel gets the
  same `g.ecabg` with the same `data-cab`, so one press handler, one
  `/api/drag`, one set of rules.
- **`snap_points` / `z_snap_points` read both lists**, which is where cabinet
  tops come from — the thing a bulkhead front actually lands on.

## 2. Four things that would have been wrong, and were caught

**The browser would have stood every panel 100 mm off the floor.** `carcassZ` in
the browser derived the lift from `model.layer`, and a panel at z 0 reads as
layer `base`. `/api/drag` now returns **`leg_lift`** — `room.carcass_z` asked at
z 0, which is the leg height for a standing carcass and 0 for a hung unit and
for a panel — and the browser reads it rather than deriving it. One less
dimension in the browser than before.

**A panel's third extent is its board's thickness**, so `room.geometry` needs
the job's materials to answer for one. `snap_points`, `z_snap_points`,
`api.drag`, `cabinet_footprint` and `overlaps` all called it without them and
would have silently measured every panel at the house 16 mm. They thread
`job.materials` now. Nothing a cabinet answers changes — the engine reads the
boards for tapes and grain and never for a size.

**A bulkhead underside made every cabinet it caps undraggable in the plan.**
Found in the running app, not in Python. The underside is 570 deep on plan and
is drawn over the run; the plan drag looks for `.cab` under the pointer and
found the panel polygon instead. Panel footprints take `pointer-events="none"`
now — they are not draggable in the plan anyway, because the plan drag knows
nothing about `y`.

**A 16 mm panel is about three pixels of target.** Every one carries an
invisible rectangle at least `render.PANEL_GRAB` (16) px across with
`pointer-events` on. It works: the first end cap I moved in the running app was
moved by accident, with a press aimed at something else.

## 3. The three things beyond the brief

**E3b — the layer toggle is multi-select.** Base, Wall, Tall and Panels each on
and off on their own; it used to be one radio, so picking a layer meant giving
up every other one. All four on by default, which draws exactly what the old
"All" drew.

**One call made here and worth Rudolf's eye:** everything not shown is
**ghosted, not hidden**. That is the existing house rule — *"the plan view
ghosts unselected layers rather than hiding them"*, because an overhead means
nothing without the base run underneath it — and applying it to Panels as well
keeps one behaviour rather than one toggle that acts differently from the other
three. It is one line to change if he wants Panels-off to mean gone.

**E8 — a new placement lands clear of what is already on that wall.** It used to
be 0 mm whatever was there, which dropped it on top of the first thing on that
wall and out of sight underneath it. `room.free_x` answers it, off the same
candidates a drag reads, and the browser asks `/api/drag` and uses the figure —
the browser computes no dimension, as ever. An item that fits nowhere comes to
rest against the end of the run, clamped to the wall: an honest overlap the
validator will name beats a position nothing worked out. It applies to cabinets
as much as to panels; it was one handler with a hardcoded `x: 0`.

**E9 — scroll-wheel zoom on the wall elevation and the plan**, with
`−` / `100%` / `+` beside each; the percentage is the way back.

The important decision is **how** it zooms. The drawing is scaled by setting the
**SVG element's CSS size**, and the viewBox is left alone. That way every
conversion from a pointer to millimetres — `elevPoint`, `svgPoint`, the plan's
wall tracks, the elevation's `.etrack` mapping and the new hit areas — goes on
reading `getBoundingClientRect()` against the same viewBox and is exact at any
zoom level, without one line of that arithmetic changing. Scaling the viewBox,
or a CSS transform on a wrapper, would each have needed it changed in five
places.

**Measured in the running app, not assumed:**

| | | |
|---|---|---|
| elevation, panel 8 | 100 % | 33 px drag → 298 mm (expected 298) |
| elevation, panel 8 | 156 % | 35 px drag → 203 mm (expected 200) |
| elevation, cabinet 6 | 156 % | 35 px drag → 200 mm (expected 200) |
| plan, cabinet 7 | 64 / 100 / 156 % | 80 CSS px → 732 / 469 / 300 mm, all exact |

**Worth knowing:** a wheel over a drawing now zooms it instead of scrolling the
page. That is what was asked for, but it is a real change in feel — reaching for
the wheel to scroll past the plan zooms the plan.

## 4. The live walkthrough

On `Test.json` (a room, 7 cabinets on two walls), **never saved** — the disk
file is untouched, which `git diff` confirms.

- Four panels added through the editor: a front (upright, 2200 × 400), an
  underside (flat, 2200 × 570) and two end caps (end, 570 × 400), three of them
  by **Duplicate**.
- Given wall A from the Placements table. They landed at the engine's `free_x`,
  not at 0.
- The front dragged **along** to the wall end (x 1800, "wall end"), back to
  "right of 1" (x 600), and **up and down**, coming to rest on the cabinet tops
  at z 880.
- `y = 16` on the end caps puts them behind the front; `y = 120` on the underside
  makes it project, and the plan shows it projecting.
- A deliberate overlap: five **warnings**, `blocking: false`, the panel drawn red
  and heavy in the elevation.
- Layer toggles: Base + Panels on with Wall + Tall off shows exactly that, and
  Panels toggles independently.
- Console clean throughout.

**One thing the walkthrough found that is NOT Part E's:** the plan's
`pointerdown` handler still **awaits `/api/drag` before it starts listening**, so
a fast drag can let go before anything is listening and the cabinet sticks to the
pointer. That is the same bug that was fixed for the *elevation* drag on 18
September and never for the plan — CLAUDE.md describes the fix as though it
applies to both. It reproduces at 100 % zoom, so it is nothing to do with E9, and
I left it alone rather than fixing it inside a Part E commit. **It is worth its
own small change.**

## 5. Where it stands

**Part E is complete: E1 to E9, pass.** Part F (3D) is not started.

Still not built and not asked for: dragging a panel in the plan (typed entry is
what ships), and `PanelSpec.anchor` — a panel still stays where it is put and
does not follow a cabinet.

**Still open, and Rudolf's to rule:** **Q1** (line endings — the working tree is
CRLF, HEAD is LF; every edit this session kept each file's existing endings, and
`git diff --ignore-space-at-eol` shows only real changes) and **Q5**
(`WHITE_EDGE`). **H5** and **H6** are still not in CLAUDE.md, because they are
his to accept.
