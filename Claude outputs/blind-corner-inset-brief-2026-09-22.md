# Claude Code (web) brief: blind corner, inset blind panel (22 Sept 2026)

Repo `RudolfSwanepoel/cupboard-generator`, branch master. Rudolf is away with his laptop off, and nobody else is working on the repo.

When you are done, commit on `master` and push to `origin master`, not a feature branch. On his return, Rudolf runs `Start Session.bat`, which does `git pull` on master, and that has to bring this work down. If a push to master is refused, push a branch, open a PR, and say so plainly in your final message.

Read `CLAUDE.md` first, especially the hard rules and the Status entry dated 22 September 2026 "Corner units made usable". Then read `Claude outputs/corner-units-rulings-2026-09-22.md`, section 5 "Blind corner". This brief replaces section 5 wherever the two differ.

## What Rudolf ruled today (22 Sept, final)

The blind corner is built differently from what is coded now. The cut sizes of the door and the opening do not change; the blind panel's construction does.

1. The blind panel sits INSIDE the carcass at the corner end, between the corner-end side panel and the opening.
   * Its front face is flush with the carcass front edges, like the sides, top and bottom, so the unit reads as one flush front.
   * Width = B, exactly as typed. The opening is still O = W − 2t − B.
2. The door is an ordinary overlay door on the outside, following the same overlap rules as every other door.
   * It overlays the far side panel, and overlays the blind panel's face by the same amount it would overlay a side (t − door_single_gap/2 = 14.5 mm).
   * Door = O + 2t − door_single_gap = W − B − 3, which is unchanged: W 1000 / B 500 gives a 497 door.
3. Blind panel height: between the top and the bottom, so the whole front looks flush.
   * Tall and wall units: H − 2t.
   * Base units (no top): it stands on the bottom and runs up to the underside of the front support. Supports are the same 16 mm board, so that is also H − 2t. Check this against how the engine cuts a base unit's supports. If it isn't H − 2t, stop and say what it is instead; don't guess.
4. Blind panel board: selectable. Add a "Blind panel board" dropdown in the Corner Unit section, listing the project's boards (thick boards only, the same filter the door-leaf dropdown uses).
   * Blank means the exterior board, which is the default. The strip visible between the door and the return run should match the doors.
   * Add the new field to `Cabinet._board_slots`, so swap, un-select, rename and the library scan all see it. `check_single_source.py` fails if you don't.
5. Edging: one long edge only, the vertical edge facing the opening, which is the one seen and rubbed when the door is open.
   * Grain runs vertical (Length = height), as on doors, so it is `edge_l = 1`, `edge_w = 0`.
   * Edging kind: selectable 1 mm or 2 mm, defaulting to whatever kind the cabinet's door edging uses. Rudolf wants a robust edge, because reaching into the cupboard rubs against it.
   * Colour: the blind panel's own board's edging, through the existing `tape_for` chain.
   * A kind the board doesn't offer is the existing EDGING critical. No hardcoded edging (hard rule 6).
6. Still code 08, role "Blind Panel", never drilled: no pot holes, not a filler. Unchanged.

## What to change

* Engine (`engine.py`, the blind branch): the blind panel line becomes (H − 2t) × B, grain vertical, on the chosen board, with `edge_l = 1` in the chosen kind. The door and carcass lines are unchanged.
* Model / store: add `blind_board` (`""` = exterior) and `blind_edge_kind` (None = the door's kind). Write both only when non-default (`store.LATE_CABINET_FIELDS`), so old jobs and `Test_Panels.json` round-trip byte-identical.
* Corner Unit section (`app/index.html`, `renderCorner`, blind branch): add the two new controls under "Blind panel width". Keep the readout line, and add the blind panel's cut size to it, e.g. "blind panel 2368 × 500".
* Plan diagram (`drawDiagram`, blind part): draw the blind panel inside the box at the corner end, with its face on the front line. Draw the door in front of the box, spanning from the far end to 14.5 mm past the opening onto the blind panel.
* Elevation (`render._corner_interior`, blind branch), seen from the front:
   * the corner-end side edge (t wide) at the corner end;
   * next to it, the blind panel face (the part of B the door doesn't cover), filled in the blind panel's board;
   * the door at W − B − 3, starting 1.5 mm in from the far end and overlapping onto the blind panel;
   * labels: "blind B" on the panel, "1 x 497" on the door.
* Validation: the return-run clearance check (`_blind_clearance`) keeps its meaning. Re-read it against the new geometry: the door opening now starts at t + B from the corner end, not at B.

## Checks, and prove each one

* A new blind corner, W 1000, H 2400, D 500, B 500, carcass 16. It must cut:
   * blind panel 2368 × 500, one long edge, code 08;
   * door 2397 × 497;
   * opening 468.
* A base blind, H 790: blind panel 758 × B, if the support rule confirms.
* Board dropdown: blank → exterior board. Choosing another board changes the cut line and the drawing colour. A board swap moves it.
* Edging kind 1 mm vs 2 mm changes the edging name on the cut line only, never a size (hard rule 5).
* Regression benchmark exact: `python tools/regen_check.py` must print 272 MEL / 59 BROOKHILL / 30 BACK panels, pot holes 92, R 28,363.50. The xlsx diff at the end needs Rudolf's Wardrobes folder, which is not in the repo; "skipping the diff" is expected here.
* Every `tools/check_*.py` passes. Add the cases above to `tools/check_drag.py` (or a new check that is also added to `Check It Still Works.bat`).
* Drive the UI headless: Playwright/Chromium is available. Run `python run_app.py --no-window` and screenshot the Corner Unit section, the Wall elevation and the cut list for the blind unit.

## Finish

* Update `CLAUDE.md` Status, add spec item(s) to `docs/ROOM-LAYOUT-SPEC.md`, and update section 5 of the rulings file to match this brief.
* Save this brief in the repo as `Claude outputs/blind-corner-inset-brief-2026-09-22.md`.
* Keep each file's existing line endings. Don't renormalise.
* Commit message: `Blind corner: inset blind panel between top and bottom, selectable board, one robust edge; overlay door unchanged`
* Push to origin master. Say in the final message whether it landed on master.

---

## What was built, and the one place the answer differed

Everything above is built and checked. Two notes on how it landed:

**Point 3 confirmed, not guessed.** A base unit's support is cut from the carcass board at the same 16 mm thickness as a top and lies flat with its face flush with the carcass top edge, so the clear span is H − 2t exactly as a tall unit's is. That is also the figure `engine.generate_cabinet` already takes as a divider's default height (`cab.height - 2 * std.board_t`), so the two agree by construction rather than by coincidence. H 790 → 758, as the brief predicted.

**The clearance check's threshold stays at B, and that is the re-read.** The brief asked for `_blind_clearance` to be re-read against the new geometry, noting the opening now starts at t + B. Read against what actually has to clear, the threshold must not move: the door is what the return run blocks, and the door did not move — its corner-end edge still stands `B + door_single_gap / 2` from the corner, lapping the panel's face. A return run reaching between B and B + t clears the opening and still stops the door opening. Measuring against the opening would therefore be wrong in the unsafe direction, so the check keeps `reach > B`; only its message and its docstring changed, and `check_drag.py` now pins the discriminating case (a return cabinet reaching 508 against a 500 panel).

**One drawing decision.** In the Corner Unit plan diagram both the panel and the door are drawn at a fixed screen depth rather than a true 16 mm, which at plan scale is three pixels and says nothing. Every position ALONG the wall is the engine's, to the millimetre, off `room.blind_spans`; only the depth each part is drawn at is exaggerated, and the front line is what they are read against — the panel behind it, the door in front of it.
