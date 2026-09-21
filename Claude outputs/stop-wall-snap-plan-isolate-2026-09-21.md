# Stop: wall-view vertical snap, plan-view isolate — 21 September 2026

Against the brief *Wall-view vertical snap, Plan-view isolate* (21 Sept 2026).
Standalone interaction fix, not a lettered Part. Branch `master`, repo
`C:\Dev\CupboardApp`.

---

## Per ID

| ID | Result | |
|---|---|---|
| W1 | **pass** | diagnosed and reported before any fix |
| W2 | **pass** | exercised in the running app |
| W3 | **pass** | engine and app |
| P1 | **pass** | diagnosed and reported |
| P2 | **pass** | exercised in the running app |
| P3 | **pass** | exercised in the running app |
| P4 | **pass** | exercised in the running app |

Nothing **failed**. Nothing is **not tested**.

---

## W1 — what the two snap generators actually offered

`room.snap_points` (sideways) and `room.z_snap_points` (vertical) come off one
`/api/drag` reply and one browser handler, on the same 20 mm
`Standard.snap_tolerance`. The mechanism was sound — vertical snapping did fire.
The target **sets** diverged three ways.

| Sideways | Vertical |
|---|---|
| wall start / wall end | floor / ceiling |
| `right of N` | `on top of N` |
| `left of N` | `under N` |
| — | `tops level with N`, `bottoms level with N` |
| `clear of the <kind>` ×2, both jambs | **nothing at all — no sill, no head** |

1. **Openings contributed nothing vertically.** `wall_elevation_svg` has drawn
   every opening's sill and head since it was built, and neither was a target.
2. **`bottoms level with N` was a leg height out** for a floor-standing
   neighbour: it read `oz if op.z > 0 else 0`, where a standing carcass's
   underside is `carcass_z` = `leg_height` = 100.
3. **The plinth top was unreachable, and the fixture proved it.** `Test.json`
   cabinet 8 — the placed end panel — sits at z=100, level with the plinth line.
   Dragging it offered nothing there and nothing brought it back:

   ```
    0 => 100 mm up           (where it already is — unsnapped)
   -2 => 110 mm up    2 => 90 mm up
   -6 => 129 mm up    6 => 71 mm up
                     20 => on the floor
   ```

   The guard that caused it (`z > std.leg_height` on both level lines) is right
   only for an item that stands on legs. A panel and a hung unit do not.

Nothing bigger than the brief expected: more targets and one corrected figure,
no new data model, no browser arithmetic.

## P1 — was E8 done for cabinets, or only panels?

**For cabinets too.** `free_x` hangs off the Placements table's wall dropdown,
which is shared by every item, and `room.free_x` branches on `cab.is_panel`
itself. Auto-isolate is not filling that gap.

Two narrower gaps it *does* fill:

- **`Add cabinet` creates no placement at all**, so the occlusion happens when a
  wall is picked — where `free_x` already runs.
- **`free_x` only avoids items in the same run.** A new *wall* unit ignores
  every base and tall unit, so on `Test.json` wall A it lands at x=0, over the
  tall unit, occluded. And when nothing fits it deliberately returns an
  overlapping position.

---

## W2 — what was built

`cabinetgen/room.py`:

- **`_hangs_clear(z, cab, std)`** — the one rule about the strip between the
  floor and the plinth top, asked by `under N` and both level lines. A carcass
  that stands on the floor is offered nothing there (it stands on its legs, and
  any z above 0 reads as hung via `layer_of`, so it would change drawing layer
  standing where it already stood). A panel stands on nothing and an upper is
  hung by definition, so for those any height clear of the floor is real. The
  floor is offered unconditionally, so the rule only ever rules out that strip.
- **A standing neighbour's underside is `carcass_z`**, never 0 — the plinth top.
- **Four opening datums**, each carrying no stretch because a datum runs the
  whole wall: `above the <kind>` (head), `below the <kind>` (sill − height),
  `tops level with the <kind> head`, `bottoms level with the <kind> sill`.

Every figure comes off `room.geometry` and the placements. No declared height
feeds any of it. Tolerance unchanged at 20 mm, as the brief asked.

`app/index.html` — **one change beyond the literal ask, flagged here.** Both
loops took the **first** candidate within tolerance; the docstrings said
"nearest". With an opening's datums now landing among the neighbours', first-wins
would have started picking a farther target over a nearer one — a defect the new
targets would have introduced. Both axes now pick the nearest, identical shape,
so they cannot drift.

**Verified in the app** (`Test.json` and a probe job with a 1200 window, sill
900 / head 2100):

- panel 8 now snaps to 100 mm — the position it could not be dragged back to
  (it read `bottoms level with 1` at this point; the sort-key fix below makes it
  name cabinet 7, the one touching it);
- cabinet 5 reaches all four kinds: ceiling 1500, `tops level with 1` 1400,
  `on top of 2` 880, plinth top 100;
- cabinet 4 reaches all four window datums: 120 `below the window`, 900
  `bottoms level with the window sill`, 1320 `tops level with the window head`,
  2100 `above the window`;
- a 2400-high unit is offered none of them — the ceiling still caps the list;
- at the rest position the floor (0 mm off) wins over the sill-derived 120
  (20 mm off), which is the nearest-pick change working.

## W3 — overlaps on a vertical move

`room.overlaps` reads `_z_span`, which reads `carcass_z`, so it was already
height-aware. Confirmed both ways. In the engine, dropping cabinet 5 with x
unchanged: clear at z 1400 and at the snap target 880 (touching is clear),
`(2, 5, 300 mm)` at 700 and below. In the app, a purely vertical drag from 1400
to 400 gives `CRITICAL — cabinets 2 and 5 overlap by 300 mm on wall A`, export
blocked.

## P2, P3, P4 — isolate

`plan_svg(..., isolate=N)`: that item is the only thing drawn solid, drawn
whatever its layer is doing; everything else is **ghosted, not hidden**, at the
same `opacity="0.30"` the layer toggle uses. One convention for "not the focus".

**Ghosting alone was not enough.** The item that is hidden is hidden UNDER
something, and that something still swallowed the click — confirmed with
`elementsFromPoint`. So a ghosted cabinet takes no pointer events **while
isolating only**; a layer ghosted by the toggle keeps its events, which is what
reveals its door swing on hover.

`S.isolate` lives in the browser, one number or null, sent to `/api/plan` and
decided nowhere else. `selectCabinet(i)` is the single place it moves, and every
selection goes through it: the cabinet table, Duplicate, Add cabinet, and a press
in the wall elevation. Never a click in the plan. An `isolating N ×` pill sits
beside the layer toggles, because unexplained ghosting looks like a fault.

Verified in the app, on `Test.json`:

- cabinet 5 moved to x=1950 is buried under cabinet 6 — `elementsFromPoint`
  returns cabinet 6, so it cannot be clicked. Selected from the list it becomes
  the top hit and drags;
- cabinet 1 buried completely under a new cabinet 9 at x=0: same, and it drags
  (`wall A · 0 mm · left of 2`);
- **P4**: Wall layer toggled off, cabinet 5 isolated — still solid, still
  interactive, every other toggle untouched;
- **P3**: Add cabinet gives `isolating 9 ×` immediately. With no wall yet the
  plan draws normally rather than greying out — `plan_svg` falls back when the
  number names nothing it draws. Given wall A it lands at `free_x` 2816 as the
  one solid item;
- **exits**: a real mouse click on empty plan canvas clears it; selecting
  cabinet 3 from the list re-isolates on 3; the pill's × clears it.

A panel isolates exactly as a cabinet does — it is occluded the same way. It is
still not draggable in the plan, isolated or not; that existing ruling is
unchanged.

---

## Checks

All fifteen `tools/check_*.py` green. `Check It Still Works.bat` green (real
Python 3.12.10, openpyxl 3.1.5).

Benchmark unmoved: **272 MEL / 59 BROOKHILL / 30 BACK, 92 pot holes, 18 / 9 / 6
boards, R 28,363.50.**

**`snapshot.py --compare baseline.json` is not identical, and was not identical
before this work either.** Verified by stashing every change and re-running on
`cf3fe75` unchanged:

```
Test.panels: changed 1
    507/Door#1: {'grain': (0, 1), 'material': ('GREY', 'BROOKHILL')}
Test.summary changed
Test.svg changed: elev, wallA
```

`baseline.json` is stale against `Test.json` cabinet 5's door board. This work
added nothing to that diff — `plan_svg` is hashed in the snapshot and is byte
identical, pinned in `check_room.py`.

Two checks were changed because the behaviour they pinned was changed
deliberately, and both now pin the corrected rule:

- `check_drag.py` — "a standing neighbour's underside is the floor" was wrong;
  it is the plinth top. The "no level line under the leg height" rule is kept,
  scoped to a carcass that stands on legs. Plus a new block for the opening
  datums, both axes side by side.
- `check_panels.py` — "the bulkhead is something for a cabinet to come up under"
  used a 780-high unit whose only way under the bulkhead is standing on the
  floor (top at 880, exactly the bulkhead's underside). The old target at z=100
  was a duplicate of the floor that would have reclassified it as a wall unit.
  Now a 600-high unit is offered `under 3` at 280, and the 780 one is not.

New coverage: `check_drag.py` (opening datums, plinth top, the legged-carcass
rule), `check_room.py` (isolate: ghosted not hidden, P4's layer override, the
pointer-events rule, the fall-back), `check_panels.py` (isolating a panel).

Line endings untouched throughout — every file edited was CRLF and stayed CRLF
(Q1 still unruled).

---

## Not built, on purpose

- **Freestanding / island cabinets** — deferred, per the ruling.
- **Anything 3D** — Phase 6, untouched.
- **Drag a new cabinet from the list onto the plan.** Awaiting Rudolf's ruling.
  It came up in the same conversation as the deferred island work and was never
  separately confirmed once islands were dropped. Isolate covers the case it was
  meant to solve — getting at something out of reach — without a second way to
  place things. Noted in `CLAUDE.md`'s open items.

## Ruled and built the same day: the reason names the nearest neighbour

Raised as a follow-up above and ruled straight away. Several cabinets on the
floor put their undersides on one line, so a whole row of candidates share a
height and differ only in which one they name. Sorted on the reason alone that
was answered alphabetically — panel 8 read `bottoms level with 1` with cabinet 7
the one touching it — and without `spans` it also decided which single reason
survived the de-duplication.

It is stated in the two places that need it, as one rule:

- **`room._gap_along(mine, span)`** — how far apart two stretches of one wall
  are, 0 where they touch or overlap, and 0 for a wall-wide datum (the floor,
  the ceiling, an opening's sill or head), which is never far from anything.
  `z_snap_points` sorts on `(z, that gap, the reason)`, so the nearest is first
  among equals and is the one the de-duplication keeps.
- **The browser tie-breaks the same way at the LIVE position.** The engine can
  only sort for where the drag started, and a drag crosses the wall. Among
  candidates at the same distance in z, the one whose stretch is nearest to
  where the item is now wins. It chooses between candidates the engine named and
  works out no height of its own — the same bargain the rest of the drag makes.

Verified in the app. Panel 8 now reads `bottoms level with 7`, and dragged along
wall A the reason follows it:

```
2800 (right of 7)  bottoms level with 7
2450 (right of 6)  bottoms level with 6
1884 (left of 6)   bottoms level with 6
1452               bottoms level with 4
 970               bottoms level with 3
 600 (right of 1)  bottoms level with 1
 296               bottoms level with 2
   0 (wall start)  bottoms level with 2
```

The last two are the two rules working together: standing over cabinet 1, a
level line does not apply at all — level bottoms would put one inside the other
— so the nearest it can line up with is 2.

## The baseline was never stale; `Test.json` was

Recorded here because the stop above got it the wrong way round. `baseline.json`
already held cabinet 5's door as GREY; `jobs/Test.json` had drifted to
BROOKHILL. Rudolf settled the cabinet as grey throughout and saved, which put
the file back to what the baseline recorded — at that point `--compare` was
clean with no `--allow` flags and a regenerated baseline was byte for byte the
same file (md5 `52e53c19d893f3163df5bff08e0acc35`).

Then the **GREY board was renamed Grey → STORMGREY** in the Boards tab and
`Test.json` was saved again, which carries the new name into the job's captured
copy. That is `api.LIVE_FIELDS` working as designed: a board's description is
edited in the library and the project on screen uses it. The legend prints that
name, so three of Test's four drawings re-hashed — `elev`, `plan` and `wallA`.
Nothing else moved: no panel, no issue, no summary, no total. Proved by putting
only the display name back in a scratch copy, at which point all four hashes
match the old baseline exactly; the picture path plays no part.

Ruled by Rudolf: regenerate over it. The baseline is now md5
`a3c7179aa6c68ed123eb2d9c14ff9f2d` and `--compare` is clean again with no
`--allow` flags. **`baseline.json` is not in this commit and never is** —
`.gitignore` line 15 keeps it per-machine, generated off a known-good tree and
never shared. `jobs/Test.json` and `boards.json` are the files that moved, and
they go together: the job's copy says STORMGREY, and `refresh_from_library`
would pull `Grey` back over it on the next open if the library were left behind.

**One thing to look at, not touched:** that board's picture is stored as
`"\"C:\Dev\CupboardApp\Pictures\Storm Grey.jpg\""` — an absolute path
with literal quote characters inside the string, which looks like a
"Copy as path" paste. It is machine-specific and the quotes are part of the
value, and `Pictures/` is untracked, so the other machine will not resolve it.
A colour changes no cut, so nothing warns about it.

## Environment note

`regen_check.py` cannot run its spreadsheet diff on this machine: the real cut
list is expected at `..\..\Wardrobes\R Swanepoel Cutlist.xlsx`, outside the
repo, and it is not there. Pre-existing and unrelated — every other figure in
`regen_check` is printed and correct.
