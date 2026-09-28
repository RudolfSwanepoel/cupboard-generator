# Brief — Plazaboard CSV: columns under the right headings (28 September 2026)

Agreed with Rudolf in Cowork. Run AFTER the output-folders brief is merged
(never two sessions on the repo at once).

## The fault

`export_plaza.rows_for` writes `[i, p.label, length, ...]` under the header
`Component, Material, Length, ...`. So Component holds a line number, Material
holds the panel designation (101, 107…), and the board is never written.
CLAUDE.md says three times that "Plazaboard's CSV writes the Component column
from `Panel.label`"; the code does not. Correct CLAUDE.md with the fix.

## The reference

`Sample Plaza cutlist and quote/` (in the repo root): Plazaboard's own files for
the October job (`RUDOLPH MEL/BRK/MAS 211025.csv`) and quotation VRG_SOQ497999.
What they show, checked:

- Header is byte-identical to `export_plaza.HEADER`.
- **Component** = their line number, 1…n, per file.
- **Material** = `SUPWHTTXT` on every line of all three files (their template
  default; it does not name the board).
- They carry no customer designation at all.
- They do **not** merge identical lines: one line per line sent, repeats kept
  (MEL lines 1, 10, 15, 22 are the same 2400×500 side from four cabinets).
- Their files are padded with empty template rows to 236 lines. Do not copy that.
- A zero edging total is written `0`. Ours writes `0.0`.

## Ruled by Rudolf

New column layout: one column added in FRONT, everything else exactly
Plazaboard's template.

| # | Heading | Content |
|---|---------|---------|
| 1 | `Customer Number` | the panel designation — `Panel.label`, Rudolf's convention (cabinet + 2-digit code, a/b/c when one code covers different panels) |
| 2 | `Component` | line number, 1…n, restarting in each file (Plazaboard's logic) |
| 3 | `Material` | the **board id** (WHITEMEL, BROOKHILL, BACK…), the file's board |
| 4… | `Length` … `total edging`, `total edging` | unchanged, same order, same meaning |

Worked example (Test.json, WHITEMEL file):

```
Customer Number,Component,Material,Length,Width,qty,Invoice Number,JOB NO ,Grain,edge l,edge w,holes,edge mat,,,,,total edging,total edging
101,1,WHITEMEL,2400,600,2,,,0,1,,,PVC WOOD,1,,,,4.94,5
204a,8,WHITEMEL,418,100,1,,,0,1,,,PVC BROOKHILL,1,,,,0.488,12
204b,9,WHITEMEL,418,100,1,,,0,1,,,PVC WHITE,1,,,,0.488,13
204c,10,WHITEMEL,418,100,3,,,0,,,,,,,,,0,13
```

(Line numbers and running totals illustrative. They follow from the rows as generated.)

### One designation, one panel

1. **Same designation, identical in every field** → one line, qty summed.
   Test.json: `417` ×4 in BACK becomes one line, qty 4.
2. **Same designation, different panels** (different edging, edge counts,
   size…) → each gets its own suffix **when the panel is born**, through
   `engine.born_distinct` (edging and banded-edge counts become part of the
   signature it reads). Never renamed afterwards (hard rule 2). Found today:
   - Test.json: 204, 304, 404, 604, 704, 1504 (supports, WHITEMEL), 1517 (BACK).
   - **October benchmark: 104, 404, 2704, 2804, 2904, 3004** (supports that
     differ only in edging). They will read 104a/104b etc. Panel counts, pot
     holes, boards and cost do not move. Rudolf has been told.
3. Do both where the cut list is made, so the Cut list tab, validation and the
   CSV all show the same lines. Do not do it in the export alone.
4. The D13 warning ("a designation on two different panels") should then
   never fire on a generated job. Pin that.

### Keep

- Header text for columns 2–19 byte-identical to Plazaboard's (including
  `JOB NO ` with its trailing space, the four blank headings, the two
  `total edging`).
- `holes` stays the line total; edging keeps the 70 mm trim formula.
- Edging names exactly as the Boards tab generates them (hard rule 6). Their
  file shows `2MM BROOKHILL` uppercase, but that is their re-keying. Do not
  change case.
- Zero edging total written `0`, not `0.0` (matches their file). Non-zero
  unchanged (`4.94`, `10.55`, `7.136`).
- No padding rows.

## Checks

- Benchmark unchanged: 272 / 59 / 30 panels (qty sums), 92 pot holes,
  18 / 9 / 6 boards, R28,363.50. Every `check_*.py` green.
- New `tools/check_export.py`:
  - the header is `Customer Number` + Plazaboard's header byte for byte (read
    from the sample CSV itself);
  - column 1 is every line's designation, column 2 is 1…n, column 3 is the
    file's board id;
  - no designation appears on two lines in any file, for the benchmark,
    Test.json and every fixture;
  - Test.json's 417 is one line of qty 4, and 204 is 204a/b/c;
  - the October export matches Plazaboard's files line for line on
    Length/Width/qty/Grain/edge l/edge w/holes/edge flags/edging metres,
    **as a multiset**, apart from the edging names (WOOD vs BROOKHILL) and
    the eight cabinets listed in `regen_check.KNOWN`. List any other
    difference; don't hide it.
- `snapshot.py --compare`: only labels and CSV content move. Say which.

## Side note for CLAUDE.md, not a change

Plazaboard's October files are edged **BROOKHILL** (`PVC BROOKHILL`,
`2MM BROOKHILL`; quote: `EDGING-IMP BROOKHILL`), not WOOD. CLAUDE.md says the
order "was edged with" PVC WOOD / 2mm WOOD. That is what the sheet sent to
them said; Plazaboard keyed it as their Brookhill edging. Correct the wording.
Leave the frozen job's tokens alone.
