# Brief — Line / Finish redone, faces in the plan, line weights (23 Sept 2026)

Supersedes item 4 of the 22 Sept brief (Line / Finish). Items 1–3 of that brief
stand; the panel drag is signed off ("perfect").

Hard rules apply as always: drawings are read-only views, every shape comes off
`room.geometry(cab)` / the actual panel set (hard rule 1), and the benchmark
must hold (272 / 59 / 30, 92, 18 / 9 / 6, R28,363.50) — none of this should move
it.

---

## 1. Line / Finish — what they actually mean

The 22 Sept wording was misread. Line was built as a white/grey "line drawing"
of the whole elevation. That mode is of no use and is **removed**.

Both views draw **this wall's own cabinets exactly as today's Finish does** —
full colour, board pictures, doors, drawers, hinges, dimensions. They differ
**only in how the return runs on the neighbouring walls are drawn**, i.e. the
cabinets seen end-on at each end of the wall (on Test.json, Wall A: the region
labelled "B: 8, 11, 12, 13").

**LINE** = today's Finish drawing, unchanged. Return runs are the grey end-on
outlines they are now.

**FINISH** = the same drawing, but the return runs are drawn as **what you
would actually see standing in front of this wall**: every board surface of
those cabinets that faces the viewer, projected straight onto this wall's
plane, in the colour/picture of the board it is cut from (`render.board_look`).
No unfolding, no rotating — it is a true orthographic view from this wall.

What that means on Test.json, Wall A:

- Mitre 13's angled door shows at its **projected** width, in its door board.
- Panel 12 (end panel on 11) shows in its board's colour.
- If panel 12 were not there, the exposed **end side of cabinet 11** would
  show instead, in its carcass board (white melamine here).
- Panel 8 and any other panel seen edge-on shows as its thickness strip, in its
  board, the way panels 9 and 10 already draw on this wall.
- The purpose: Rudolf checks the whole corner and that every exposed side /
  end panel is the right colour. So the rule is simply "draw what is visible,
  in the board it is cut from" — do not special-case panels vs carcass sides.

How to build it (guidance, not a prescription):

- Take each return-run cabinet's and placed panel's actual parts, keep the
  faces whose outward normal has a component toward the viewer of this wall,
  project them onto the wall plane, and paint far-to-near (nearest the viewer
  last), so a nearer end panel covers the carcass side behind it.
- Where a return-run surface stands in front of this wall's own cabinets, it
  draws over them — the same precedence today's outlines already follow.
- On those return-run faces: no hinge dots, no swing diamonds, no drawer sizes
  (they would be foreshortened and misleading). Keep the cabinet number, and
  on a mitre door keep its real-width label as `_corner_interior` does.
- Keep the wall label ("B: 8, 11, 12, 13") and the note under the drawing;
  reword the note per view (Line: "shaded outlines…"; Finish: "cabinets on
  the walls either side, as seen from this wall").
- Run view: Line and Finish are identical there (it has no neighbouring walls);
  either keep the toggle harmlessly or grey it out — your call, say which.
- Still a view setting only (`S.elevMode`), not saved in the job. Finish stays
  the default.

Checks: update `check_elevation.py` — Line with no room still equals
`elevation_svg` byte for byte; add a Finish case on Test.json that finds panel
12's board colour and 13's door board colour in Wall A's drawing, and one with
panel 12 removed that finds cabinet 11's carcass colour instead.

## 2. Door and drawer faces in the plan (top view)

Draw every door and drawer face in the plan: a thin strip in front of its
carcass at the face's real thickness, in its own board's colour (per-leaf and
per-drawer boards as the cut list has them). On a mitre, along the angled face;
on a blind corner, the door and blind panel where they really are.

- Faces only. **The hover swing animation stays exactly as it is** — Rudolf
  says it is perfect.
- Faces must not take the pointer from the cabinet (same treatment as plan
  labels, `pointer-events:none`), so drag and select are unchanged.
- Wall units above keep their dashed/ghosted treatment; their faces follow the
  same layer rules.

## 3. Line weights and legibility (plan and elevation)

Zoomed in on the plan (cabinets 1, 2, panels 9/10, wall unit 5) the strokes are
heavy and uniform: the 16 mm panel between 1 and 2 is swamped by two thick
outlines, shared edges between neighbouring cabinets are stroked twice, the
dashed wall-unit outline is as heavy as a carcass, and the labels "16", "10",
"2" collide.

Proposal — Rudolf to confirm or adjust before build:

| Element | Weight (screen px) | Style |
|---|---|---|
| Walls | 2.0 | solid, darkest ink |
| Carcass outline | 1.0 | solid |
| Panels (edge-on / placed) | 0.75 outline + board fill | solid |
| Door / drawer faces | 0.75 | solid |
| Internal lines (shelves, divisions, grain) | 0.5 | solid / as now |
| Wall units above, hidden items | 0.75 | dashed 4–3 |
| Dimension and reference lines | 0.5 | as now, red stays red |

- Use `vector-effect: non-scaling-stroke` so zooming in makes the geometry
  bigger, not the lines fatter — that alone makes a 16 mm panel readable.
- Draw a shared edge once (or draw neighbours with a butt join so two strokes
  don't stack).
- Labels must not overlap: when a cabinet or panel is too small for its label,
  offset it with a short leader, or drop the size text and keep the number.
- One set of weights for plan and elevation, defined in one place.

## Report back

Commit message to paste, benchmark confirmation, and screenshots of Wall A in
Line and Finish, the plan with faces, and the same zoomed plan area as
Rudolf's example.
