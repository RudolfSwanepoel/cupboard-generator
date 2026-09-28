# Brief — Plazaboard CSV: right columns, right numbers, right edging names (28 September 2026)

Agreed with Rudolf in Cowork, point by point. Run AFTER the output-folders brief
is merged (never two sessions on the repo at once).

## Reference

`Sample Plaza cutlist and quote/` in the repo root: Plazaboard's own files for
the October job (`RUDOLPH MEL/BRK/MAS 211025.csv`) and quotation
VRG_SOQ497999. Checked:

- The header is byte-identical to `export_plaza.HEADER`.
- **Component** = their line (item) number, 1…n, per file.
- **Material** = `SUPWHTTXT` on every line of all three files (a template
  default; it does not name the board).
- No customer designation anywhere.
- **Identical lines are NOT merged.** One line per line sent, repeats kept
  (MEL lines 1, 10, 15, 22 are the same 2400×500 side from four cabinets).
  Line counts match ours: 112/35/19 vs 111/35/19.
- Edging is keyed as BROOKHILL (`PVC BROOKHILL`, `2MM BROOKHILL`; quote:
  `EDGING-IMP BROOKHILL`), never WOOD.
- Padded to 236 rows with empty template lines. Do not copy that.
- A zero edging total is written `0`. Ours writes `0.0`.

## Part 1 — columns

**The fault.** `export_plaza.rows_for` writes `[i, p.label, length, ...]` under
`Component, Material, Length, ...`. Component gets a line number, Material gets
the panel designation, and the board is never written. (CLAUDE.md says three
times that Component is written from `Panel.label`; the code does not. Correct
CLAUDE.md.)

**Ruled.** One column added in FRONT; everything after it is Plazaboard's
template exactly.

| # | Heading | Content |
|---|---------|---------|
| 1 | `Customer Number` | the panel designation, `Panel.label`, Rudolf's convention |
| 2 | `Component` | Plazaboard's item number, 1…n, restarting in each file |
| 3 | `Material` | the board **id** (WHITEMEL, BROOKHILL, BACK…) |
| 4… | `Length` … `total edging`, `total edging` | unchanged, same order and meaning |

Keep columns 2–19's header text byte-identical to Plazaboard's (`JOB NO `
with its trailing space, the four blank headings, both `total edging`).
`holes` stays the line total; the edging-metres formula is untouched. Zero
edging total written `0`; non-zero unchanged. No padding rows.

## Part 2 — one number per panel, no merging

**Ruled:**

1. **No merging.** Every line stays a line, as Plazaboard keeps them.
2. **Identical panels share a number**, one line each: `1517, 1517, 1517`
   with items 1, 2, 3. Lines that differ ONLY in qty are the same panel.
3. **Different panels under one code get their own letter**, and identical
   ones share it. Test.json 404 (1× PVC Grey; 3× identical PVC WHITE, one long
   edge; 1× PVC WHITE, two long edges) reads `404a, 404b, 404b, 404b, 404c`,
   items still 1–5.
4. "Different" = any difference except qty: size, board, grain, edge counts,
   holes, edging name.
5. Letters are given **when the panel is born**, through `engine.born_distinct`
   (edging name and banded-edge counts join the signature it reads). Nothing is
   renamed afterwards (hard rule 2). The Cut list tab, validation and the CSV
   show the same numbers.
6. Found today with the same number on different panels:
   - Test.json WHITEMEL: 204, 304, 404, 604, 704, 1504. BACK: 1517 is qty-only,
     so it keeps its number.
   - **October benchmark: 104, 404, 2704, 2804, 2904, 3004** (supports that
     differ only in edging). They get letters. Panel counts, pot holes, boards
     and cost do not move. Rudolf agreed.
7. The D13 warning (a designation on two different panels) must then never
   fire on a generated job. Pin it.

## Part 3 — edging names: the Boards tab, and nothing else

**Ruled:** the **Edging Name** on the board's Boards-tab record is the name
used, on the order AND on screen. They can never differ. Today they do, for
two reasons. Fix both:

1. **The Edging Colour dropdowns show the board id** (WHITEMEL, GREY), not the
   Edging Name (WHITE, Grey). Every edging-colour dropdown — supports, doors,
   drawers, blind panel, Panel design — shows the board's Edging Name. Where
   two boards in the project share one (WHITEMEL and BACK are both WHITE),
   add the id in brackets, `WHITE (WHITEMEL)`, so they can be told apart. The
   stored value is still the board id; only the label changes. The resolved
   name beside each control ("Ordered as…") is the same text the CSV writes.
2. **Old typed edging names are retired everywhere**, the October job
   included (Rudolf ruled). `carcass_edge`, `door_edge`, `drawer_box_edge` and
   any other flat edging string on a cabinet are no longer read; the edging
   follows the board picked, through `tape_for`. Test.json cabinets carry
   `"carcass_edge": "PVC WOOD"` / `"door_edge": "2mm WOOD"` on five cabinets.
   These now resolve through their exterior board (BROOKHILL) to `PVC
   BROOKHILL` / `2mm BROOKHILL`. Leave the keys in the files (store round
   trip); just stop reading them. Remove the editor's "override — clear it"
   offer.
3. **Bespoke and loose panels** (October fixture) store `edge_material` as a
   typed literal such as `2mm WOOD`. Resolve it the same way: a literal whose
   name matches no project board's Edging Name is read as the same kind in
   the board it was cut beside. On the October job WOOD is the exterior board,
   BROOKHILL. Say in the report exactly which panels this touched.
4. The output: edge mat = kind (`PVC` / `1mm` / `2mm`) + the board's Edging
   Name, exactly as typed on the Boards tab (case included: GREY's is `Grey`,
   so `PVC Grey`). No hardcoded edging anywhere (hard rule 6).
5. `model.WHITE_EDGE` and any other stored edging token: read the Boards
   record instead, or say why one must stay.
6. Update CLAUDE.md where it says the October order "was edged with" PVC WOOD
   / 2mm WOOD. That is what the sheet sent said; Plazaboard keyed it as
   Brookhill, and the job now reads BROOKHILL.

## Checks

- Benchmark: 272 / 59 / 30 panels, 92 pot holes, 18 / 9 / 6 boards,
  R28,363.50. Edging cost is by kind, so it must not move. If it does, stop
  and report.
- Every `check_*.py` green. Checks that pinned WOOD names or override
  behaviour are updated to the new rule, each named in the report.
- New `tools/check_export.py`:
  - header = `Customer Number` + Plazaboard's header byte for byte, read from
    the sample CSV itself;
  - column 1 = designation, column 2 = 1…n per file, column 3 = the file's
    board id;
  - no number sits on two DIFFERENT panels (qty aside) in any file, for the
    benchmark, Test.json and every fixture;
  - Test.json: 404 → 404a, 404b ×3, 404c; 1517 ×3 unchanged; no WOOD anywhere;
  - every edge mat in every export is kind + an Edging Name that exists on
    the Boards record for that project;
  - **October vs Plazaboard's files**: as a multiset per board, Length / Width
    / qty / Grain / edge l / edge w / holes / edge flags / edging metres /
    edge mat (case-insensitive) match, apart from the eight cabinets in
    `regen_check.KNOWN`. List every other difference; don't hide any.
- `snapshot.py --compare`: only labels, edging names and CSV content move.
  Say which.
