# Brief — Room tab touch-ups after Phase 2

3 October 2026. From Cowork, ruled by Rudolf after testing Phase 2. Layout
and the plan's labels only: nothing in `cabinetgen/` that cuts, nests or
costs changes, `/api/compute` unchanged, benchmark must not move. Small —
one commit per item.

## Rulings — Phase 2's two open decisions

- `Standard.loop_miss_max` 1000: **accepted**.
- A corner unit keeps its x when walls are dragged, and Validation's
  out-of-corner warning flags it: **accepted**.
Record both in `docs/ROOM-LAYOUT-SPEC.md` under Ruled — 3 Oct 2026.

## 1. The tool buttons go into the strip above the plan

Select · Draw walls · Wall nook leave the left column and sit in the strip at
the top of the Room tab, on the same line as the Plan | Elevation sub-tabs,
to their right, as a segmented control in the same style. They show on
Plan only (hidden on Elevation). Esc still returns to Select.

## 2. Placements goes into the left column

The left column the buttons leave becomes the home of the **Placements**
card: full height of the plan beside it, its table narrowed to fit (Item ·
Wall · X · Z · Y · Layer, inputs sized to five digits, the "?" help as now),
scrolling within itself if the job has more items than fit. It stays a
Plan-only card. Under the plan: **Gaps** full width, **Plinth** under it
(it no longer shares a row). Nothing removed (hard rule 9): add the moves
to CLAUDE.md's where-it-lives-now table.

## 3. The plan's length labels are cut off and overlap — fix

Seen on Rudolf's laptop at 93 % (screenshot in the chat of 3 Oct): the
editable length labels clip their own digits ("B · 330( mm", "D · 1840 mm"
with the 0 cut, "A · 155" with its first digit hidden), and two labels on
short neighbouring walls print over each other ("F · 355 mm" over
"H · 560 mm").
- A label's text box is sized to its content (width from the text, not a
  fixed box), at every zoom.
- Length labels go through the same `_place_labels` collision step as the
  cabinet numbers and gap widths (Drawings → "Plan labels never sit on each
  other"): a label that would overlap another moves out along its wall's
  normal on a short leader; it is never dropped (a wall's length is not
  optional on a plan).
- `ui_check_walls.py --stage labels`: on a room with a nook (short walls
  side by side), every length label's bounding box holds its full text and
  no two overlap, at 50 %, 93 % and 150 %.

## Checks

`check_all` green; benchmark 272 / 59 / 30, 92 pot holes, 18 / 9 / 6,
R28,363.50 — quote it; `snapshot.py --compare`: panels, issues, totals
identical. All five Playwright scripts re-run (the selectors for the tool
buttons and Placements move). Screenshots at 1360 × 900 and 1920 × 1080 into
`output/_checks/ui_check_walls/` (`touchup_*`).

## Report back

The benchmark line and the screenshots' names.
