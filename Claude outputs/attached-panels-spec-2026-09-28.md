# Attached panels + support defaults — spec (28 Sept 2026)

Status: AGREED with Rudolf 28 Sept 2026. Not built.
Hard rules 1, 2, 3, 6, 8 apply. Standalone panels stay EXACTLY as now.

## A. Support defaults for a new cabinet (ruled 28 Sept 2026)
Replaces the "four Back rows on every new cabinet" default built on 27 Sept.
| New cabinet | Front | Top Rear | Back |
|---|---|---|---|
| Base | 1 | 1 | 2 |
| Wall | — | — | 3 |
| Tall | — | — | 4 |
| Blind corner | by its kind (above) | | |
| Mitre / ell | none | none | none |
Existing cabinets and legacy rows are untouched.

## B. Attached panels
1. **What it is.** A Panel item (Kind = Panel) that carries a link `attached_to` = a cabinet
   number. Everything else about the panel (board, size, orientation, edging, code 08) is
   exactly as a standalone panel today.
2. **Numbering.** Same series and same arithmetic as every other item; the number is given
   when the panel is made and never changes, attached or not (hard rule 2).
3. **Making one.** From the cabinet's editor: "+ Panel on this cabinet".
   Also: an existing standalone panel can be ATTACHED to a cabinet, and an attached panel
   DETACHED to standalone — both ways, number unchanged. On attach, its local offsets are
   computed from its current world position (it does not jump); on detach it stays where it is.
4. **Position.** Cabinet-local, in the supports-spec frame: x across the width from the
   cabinet's left side, y from the front face of the sides (0) toward the back, z up from the
   underside of the sides; plus the panel's orientation (upright / flat / end).
   - Typed offsets in the Panel design section (one place only, hard rule 8), AND
   - dragged in the single-cabinet 3D with snap to the carcass faces and edges. (That view
     arrives with the UI restructure; the drag is built there, the typed offsets now.)
5. **Travels with the cabinet.** World position = the cabinet's placement applied to the local
   offsets, so it moves, snaps and changes wall with the cabinet in Plan, Elevation and 3D.
6. **Room checks.** It counts in the cabinet's geometry for footprint, overlaps, door swing and
   ceiling clash (hard rule 1, via the panel set). It does NOT count in the tip-up check:
   attached panels are fitted on site, after the carcass is stood up.
   An attached panel that cuts INTO its own cabinet's carcass (overlaps, not merely touching)
   raises a WARNING (does not block export).
7. **Deleting the cabinet.** A popup asks: "Also delete its N attached panels?"
   Yes → deleted. No → they become standalone panels at their current world position,
   numbers unchanged.
8. **Duplicating the cabinet.** Attached panels are copied too, with new numbers in the same
   series and the same local offsets.
9. **Cut list.** Each attached panel is its own line under its own number, as a standalone
   panel is. Benchmark unaffected (it has none).

## C. Build notes for Claude Code
- Do A and B now, EXCEPT the drag-in-single-cabinet-3D (B4), which is built with the UI
  restructure (`ui-restructure-spec-2026-09-27.md`, in the claude.ai project).
- Attached panels must show and move correctly in the existing Plan, wall Elevation and 3D tab.
- New `tools/check_attached.py`: attach/detach round trip keeps numbers and world position;
  moving/rotating the cabinet moves the panel; footprint/overlap/swing/ceiling include it,
  tip-up excludes it; delete-with-yes and delete-with-no; duplicate gives new numbers;
  own-carcass overlap warns; job save/load round-trips `attached_to`.
- Benchmark exact (272/59/30, 92 pot holes, 18/9/6, R28,363.50); every existing job's cut
  list identical (snapshot.py --compare); all check_*.py green. Report the figures.
- Update CLAUDE.md Status and add an Attached panels section.
