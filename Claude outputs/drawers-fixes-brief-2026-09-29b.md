# Brief: Drawers section fixes after Rudolf's review (29 September 2026, evening)

Rudolf reviewed the redone Drawers section (brief
`drawers-section-redo-brief-2026-09-29.md`, commits through 4244eb6) in the
app. The look is right; six things to fix, one of them a new rule. Run
**Local**. Benchmark unchanged (272 / 59 / 30, 92 pot holes, 18 / 9 / 6,
R28,363.50). `tools/check_all.py` green. `snapshot.py --compare` against the
tree before: the October job identical; Test.json may gain criticals from
Part 2 and Part 3 (listed in the report), and nothing else moves.

## Part 1: the editor jumps on edit (bug)

Pressing **Equal** (also Graduated, and often a size change on any cabinet)
repaints the editor and the settings column ends up scrolled somewhere else,
with the control that was pressed off screen. The repaint must keep the
dock's scroll position, and the control that was clicked or typed into must
stay where it was on screen. Find why the paint moves it (a slot re-created
above the viewport, the section collapsing and re-expanding, a scroll reset)
and fix it at the cause. Pin in `ui_check_drawers.py` (`--stage scroll`):
scroll the dock so the stack is in view, press Equal, and assert the dock's
scrollTop and the Equal button's screen position are unchanged.

## Part 2: NEW RULE, a box never sits flush in its face (Rudolf, 29 Sept)

`Standard.drawer_box_clear = 2`. A box's top stays at least 2 under its
face's top; its bottom at least 2 above its face's bottom; and at least 2
under a Top Front / Top Rear band. So:

- `drawer_layout`'s `max_box` = face − offset − clear, further limited by the
  support band above (Part 3). The `≤` figure shows this.
- **Auto** cuts at that `max_box`.
- `drawer-box-face` fires when box top > face top − clear, or box bottom <
  face bottom + clear (the message names the 2 mm).
- The bottom drawer's minimum offset stays `drawer_rise` 21
  (`drawer-bottom-offset`); an upper drawer's minimum offset is `clear`.
- Typed boxes now within 2 mm show the red `≤` and the critical, and still
  cut as typed. Test.json cabinet 4 may pick up criticals: list them.
- Worked numbers pinned in `check_runners.py` `drawer_checks()`; Standard
  docstring says the rule and the date.

## Part 3: Equal put the top box into the Top Front (bug in Auto)

Auto asked only "fits in the face". The top face runs to 774 and the Top
Front band starts at 764, so Auto filled to 774 and `support-drawer-foul`
fired on a box the app itself chose. `max_box` must also read
`room.drawer_box_tops` / the support layout: the box top may not pass the
band's underside less `drawer_box_clear`. Auto then never raises
`support-drawer-foul` on its own. Pinned in `check_runners.py`: cabinet 4
after Equal with every box Auto raises no `support-drawer-foul` and no
`drawer-box-face`.

## Part 4: the offset has no floor going down (bug)

With Box height Auto, raising the offset moves the box's bottom up its face
until the ≤ limit — right. Lowering it below 21 carried the box on DOWN
PAST THE FACE with no critical and no red ≤. Reproduce on cabinet 4:

- an upper drawer's offset below `drawer_box_clear` (Part 2), or negative:
  red ≤, `drawer-box-face`;
- the bottom drawer's offset below 21: `drawer-bottom-offset` at once;
- the Offset input refuses a negative number (min 0) and a non-number
  reads as blank (= 21).

**And the Offset input is range-limited (Rudolf, 29 Sept):** the engine hands
each drawer its allowed offset range on `/api/compute` (no browser
arithmetic): min = 21 for the bottom drawer, `drawer_box_clear` for an upper
one; max = the largest offset at which the box still fits under the `≤`
limit (the typed box, or for Auto the smallest box the runner allows, its
`height`). The `<input>` carries that `min` / `max` and its spinner and
typing are clamped to it. A saved job whose offset is already outside the
range loads as it is, shows the value red with the critical, and cuts as
typed; it is clamped only when the operator next changes it.

Find which of the two it was (the check not reading the offset on the way
down, or the field accepting a value the check never saw) and say so in the
report. Pinned in `check_runners.py` and `ui_check_drawers.py --stage offset`.

## Part 5: "Face board" label out of line (cosmetic)

Setup's box / face board row has one combined label over two dropdowns.
Make it two labels, one over each control, exactly as the per-drawer
`differs…` sub-row already does.

## Part 6: report on the Cabinets 3D colours (report only, no change)

The single-cabinet 3D draws cabinet 4's right side in a dark navy and its
front faces near black, while the wall elevation draws the same GREY board
as a mid grey. Report, without changing anything: which colour hex each of
those parts is drawn in and where it comes from (`render.board_look` for
GREY, the selection tint, the material's lighting in `view3d.js`), and why
the same board reads so differently in 3D and in the elevation. This feeds
the 3D realism brief that follows; nothing here is to be "fixed" now.

## Report and commit

Update CLAUDE.md: Status, the drawer entries (the new clearance rule, Auto
reading the support band, the offset floor), Standard's constant in the
Layout / ruled-numbers text. Commit per part; give Rudolf the commit message
to paste.
