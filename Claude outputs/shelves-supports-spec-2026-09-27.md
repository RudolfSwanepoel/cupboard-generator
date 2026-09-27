# Shelves and supports — agreed spec (27 Sept 2026)

Status: AGREED with Rudolf 27 Sept 2026. BUILT the same day. Attached panels spec
follows separately.

**Ruling, 27 Sept 2026 (later the same day), replacing the single Back edging below:
every Back support carries its OWN edging** — board, kind and per-edge ticks — exactly
like Front and Top Rear. A new Back support defaults to the Cut-from board's own edging
with no edges ticked (unedged); a board with no edging defaults to none. Re-enter on a
legacy cabinet keeps each legacy row's own edging, so the cut list and cost do not
change (Test.json cabinet 6 stays at its total). Sections 1 and 4 and "Existing jobs"
are amended in place below.

Hard rules that bind this work: 1 (geometry from the panel set, never declared sizes),
2 (designations never change), 3 (benchmark 272/59/30, 92 pot holes, 18/9/6, R28,363.50),
5 (finished sizes, no tape deduction), 6 (edging only from the Boards tab).

## Conventions used below
Carcass-local: x across the width, y depth from the front face of the sides (0) to the
back of the sides (D), z up from the underside of the sides. t = 16, Wi = W − 32,
backing front face at y = D − back_cavity − back_t = D − 19. The bottom panel runs full
depth, flush at the back; the backing always sits in its slot.

## 1. Supports

Every support is Wi × 100 × 16, code 04, as now. Three types. **Every support** — the
Front, the Top Rear and each Back — has its own **Cut from** board and its own
**edging** (board + kind from the Boards tab, as today, and which edges).

Edging: **any edge**, chosen edge by edge (both long edges, both ends). The cut list
records the counts (edge_l / edge_w) exactly as now; the model draws each chosen edge.
Tape is drawn as a band INSIDE the finished size — edging never moves a part, in the cut
list or the model (hard rule 5: finished size is the same edged or not).

### Front — base units only (0 or 1)
- Flat. y 0…100, z H−16…H. Top flush with the sides, front flush with the side fronts.
- Default edged edge: the front long edge.

### Top Rear — base units only (0 or 1)
- Flat, z H−16…H, top flush with the sides.
- With backing: y (D−119)…(D−19) — rear edge against the backing's front face.
- **No backing:** y (D−100)…D — flush with the back of the sides, running forward.
- Default edged edge: the front long edge.

### Back — every carcass kind except mitre and ell (0…n)
- Upright, y (D−16)…D — in the 16 mm cavity, flush with the back of the sides (same
  plane with or without backing). Each 100 tall.
- **Back 1** (edge faces DOWN): its top starts under whatever is at the top back —
  - the top panel (tall, wall), z top = H−16;
  - the Top Rear when it sits at the back (base, no backing), z top = H−16;
  - otherwise flush with the top of the sides, z top = H.
- **Back 2** (edge faces UP): mirror of Back 1, standing on the top face of the bottom panel.
- **Back 3…n** (edges face UP, like Back 2): same plane, equally spaced (equal gaps)
  between Back 1 and Back 2.
- With only one Back support, it is Back 1.
- **Each Back support carries its own edging** (ruling above): a row per support, its
  own Cut from, edging board, kind and per-edge ticks. A new one starts in its Cut-from
  board's own edging kind with **no edge ticked** — unedged, no tape ordered — and on
  none where the board has no edging. Back 1, 2, 3… are numbered across the rows in
  order.

### Which cabinets get what
| Cabinet | Front | Top Rear | Back |
|---|---|---|---|
| Base with backing | selectable | selectable, against backing | selectable |
| Base, no backing (incl. drawer units, which have no backing) | selectable | selectable, flush with side backs | selectable, Back 1 under Top Rear |
| Tall / wall (have a top panel) | **not selectable** | **not selectable** | selectable, Back 1 under the top panel |
| Blind corner | by its kind, like any straight carcass | by its kind | by its kind |
| Mitre / ell | none (as now) | none | none |

### Validation
- **Critical:** a drawer box reaching into the 16 mm band (z > H−16) under a Front or Top
  Rear blocks export.
- **Critical:** Front and Top Rear overlapping in depth (with backing needs D ≥ 219; without, D ≥ 200).
- **Critical:** Back supports that do not fit between Back 1 and the bottom panel.

### Existing jobs (benchmark)
- Untyped support rows (old `supports / edged_supports / white_supports` numbers and
  existing `support_rows`) cut EXACTLY as today — same lines, same designations, same cost.
- Back style **"three"** stays readable in old jobs (vanity units 27–29 of the benchmark)
  but is removed as a choice for new cabinets. Rudolf: backing always in the slot,
  bottom always flush at the back; "three" was a mistake.
- For drawing only, legacy untyped rows are placed as: base unit — one front-edged row → Front,
  the rest → Back; tall/wall — all Back. No legacy row is converted or renamed in the
  job file unless Rudolf re-enters it in the new form.
- **Re-enter keeps each legacy row's own edging** (ruling above): every legacy row becomes
  a typed row of its own — the first front-edged rail on a base unit the Front, everything
  else a Back — with its qty and exactly what it was cut from and edged in, so the cut
  list and the cost do not change. Test.json cabinet 6 (4 unedged, 1 PVC WHITE,
  1 1mm WHITE) re-enters as three Back rows and stays at its total. No Top Rear is guessed.

## 2. Shelves
- Counts as now (adjustable / fixed); sizes, depth rule and cut list unchanged.
- **Drawn**, display only: spaced evenly from the top face of the bottom panel to the
  top of the sides. Real heights are set bespoke at fitment — nothing validates them.
- Drawn in the carcass board (picture/colour per the render priority), front edge band
  in the carcass edge (exterior colour) — all from the Boards tab, never hardcoded.

## 3. Where they show
- 3D (the 3D tab and the new single-cabinet 3D on the Cabinets tab): shelves and supports
  drawn. `scene.NOT_DRAWN` drops "shelves, supports".
- Plan and wall elevations: unchanged.

## 4. Editor
- Supports section: a Front block (tick), a Top Rear block (tick), and **one block per
  Back support** with "+ Back support" and a remove button (ruling above — not one Back
  block with a quantity). Each block has Cut from, edging board + kind, and per-edge
  edging ticks.
- Front and Top Rear greyed (not selectable) on any carcass with a top panel.

## 5. Save button (cabinet configuration window)
- Refresh only (does not write the job file — the top-bar Save still does that).
- Live updating stays as now. Save forces a complete, comprehensive refresh of EVERY place
  the cabinet appears: single-cabinet 3D, Plan, Elevation, 3D tab, cut list, nesting,
  validation, summary strip.

---

## BUILD BRIEF for Claude Code (cloud session, 27 Sept 2026)

Scope: THIS spec only (sections 1–5 above). Do NOT start the UI restructure
(`ui-restructure-spec-2026-09-27.md` in the claude.ai project) or attached panels.
The single-cabinet 3D view does not exist yet — shelves and supports show in the
existing 3D tab for now, and must work unchanged when that view is built.

Read `CLAUDE.md` first (hard rules, Supports section, "A support row: cut from, and
edged in"). Work on `master`; push when verified.

### Worked numbers — assert these exactly in a new `tools/check_supports.py`
Base, W600 H720 D560, back "four" (Wi 568; backing front face y 541):
- Front: y 0–100, z 704–720, flat.
- Top Rear: y 441–541, z 704–720, flat.
- Back 1: y 544–560, z 620–720, upright, edge down.
- Back 2: y 544–560, z 16–116, edge up.
- With 3 Backs: the middle one z 318–418 (equal 202 gaps).
Same base, back "none":
- Top Rear: y 460–560, z 704–720. Back 1: z 604–704.
Tall, H2400 (top panel z 2384–2400): Back 1 z 2284–2384; Front and Top Rear not offered.
Mitre / ell: no supports. Blind corner: by its kind.
z is carcass-local (underside of the sides = 0); the scene adds the leg height as it
already does for every other part.

### Must hold
- Benchmark exact: 272 MEL / 59 DECOR(BROOKHILL) / 30 BACK, 92 pot holes, 18/9/6 boards,
  R28,363.50. Every existing job's cut list byte-identical (tools/snapshot.py on all jobs).
- Every existing tools/check_*.py passes. Legacy rows load, save and cut unchanged.
- Old jobs with back "three" load and cut unchanged; "three" is not offered for new cabinets.
- Tape drawn inside the finished size; no position ever depends on whether an edge is taped.
- No hardcoded edging or colour: boards, tapes and colours only through the existing resolvers.

### Verify headless (Playwright/Chromium: `python run_app.py --no-window`)
Screenshot the 3D tab for: base with backing (Front + Top Rear + 3 Backs), base with no
backing, a drawer base unit, a tall unit with 4 Backs, and a benchmark tall unit. Screenshot
the new Supports editor section on a base and a tall unit (Front/Top Rear greyed). Check the
drawer-fouling critical fires and blocks export.

### Finish
Update CLAUDE.md's Status and Supports sections. Push to master. Report the benchmark
figures and list anything you could not verify (the cloud machine has no Wardrobes xlsx,
so the cut-list diff in Check It Still Works.bat is for Rudolf to run locally).
