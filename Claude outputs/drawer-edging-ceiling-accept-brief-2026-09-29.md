# Brief — drawer box edging chosen per drawer; above-ceiling acceptable (29 September 2026)

Agreed with Rudolf in Cowork. Two small, separate parts. Run after
`plaza-csv-columns-brief-2026-09-28.md` (f298425) is on master.

## Part 1 — drawer box edging: a choice, per drawer

**Today.** A drawer box's PVC edging (sides 18, fronts 19) is not chosen. It
follows the drawer's BOX board (`Cabinet.drawer_box_tape_of`), so a WHITEMEL
box is always `PVC WHITE`. There is no way to edge it anything else.

**Ruled.**

1. A new per-drawer field, `Drawer.box_edge_board` (a board id, `None` =
   default), with a dropdown in each drawer row: **Box edging**. It lists the
   project's boards that offer PVC, showing their **Edging Name** exactly as
   every other edging-colour dropdown does since f298425 (`Grey`,
   `WHITE (WHITEMEL)` where shared). The kind stays PVC.
2. **Default (nothing chosen): the cabinet's EXTERIOR board**, not the box
   board. This applies to every existing drawer, the October job included
   (Rudolf ruled). October's drawer sides and fronts therefore go from
   `PVC WHITE` to `PVC BROOKHILL`, which is what Plazaboard actually keyed and
   cut. Edging cost is priced by kind, so the benchmark total must not move.
3. The edging name comes off the Boards record through `tape_for`, as
   everywhere. An exterior board with no PVC offered: the ordinary `EDGING`
   critical, naming the drawer and what to tick.
4. Written to the job file only when set (`store` round trip byte for byte for
   every job that never sets it).
5. In `Cabinet._board_slots` (labelled "drawer N box edging board"), so swap,
   un-select, rename and the library scan find it. `check_single_source.py`
   must pass by reflection.
6. The drawer table is already nine columns in a 560-wide column. Fit it
   without losing any existing column (hard rule 9). If it cannot fit, say
   so and propose, don't squeeze.
7. **Supports are NOT touched.** White-edged support rows keep their own
   Edging Colour, as they are. Only drawer box sides (18) and fronts (19)
   read this.
8. Drawer boxes in 3D draw the band in the new edging board's colour.

## Part 2 — above the ceiling becomes acceptable

**Changes the 22 September ruling** ("tip-up is the only acceptable
critical"). Rudolf ruled 29 September:

- `above-ceiling` (a carcass top above the MEASURED ceiling) is acceptable
  with a reason, exactly like `tip-up`: an entry in `validate.ACCEPTABLE`, its
  own fingerprint function over exactly the inputs the check reads (the
  carcass top off `carcass_z` + `geometry` height, and the ceiling), lapsing
  when any of them moves.
- `ceiling-measured` (no ceiling measured) **still blocks**. It is a missing
  site figure.
- Panels longer than the board **still block** (`_panel_fits_board`). A panel
  can never be longer than the board.
- Every other critical still blocks.
- Update CLAUDE.md's **Accepting a critical** section and the 22 Sept
  ruling text to say so.

## Checks

- Benchmark: 272 / 59 / 30 panels, 92 pot holes, 18 / 9 / 6 boards,
  R28,363.50. Only October's drawer-box edging names move (WHITE → BROOKHILL).
  List every line that moved.
- `check_export.py`'s October-vs-Plazaboard comparison should now have FEWER
  differences (the drawer sides). Update its pinned list and say what dropped out.
- New pins in `check_runners.py` or a fitting check: the default is the
  exterior board; a chosen board wins; a board with no PVC is an `EDGING`
  critical; the job-file round trip; the swap moves it.
- `check_accept.py`: `above-ceiling` accepted, exported, and lapses when the
  ceiling or the cabinet height moves; `ceiling-measured` refused by
  `/api/accept`.
- Every `check_*.py` green; `ui_check_drawers.py` extended to set the new
  dropdown in the running app.
