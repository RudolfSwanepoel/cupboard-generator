# The rule set

Derived from two kitchens (445 panels) and two wardrobe jobs (361 panels in the
October 2025 job alone), and checked against what Plazaboard actually cut and
invoiced on quotation VRG_SOQ497999.

Notation: `W` width, `H` height, `D` depth, `t` = 16 board thickness,
`Wi = W − 32` internal width.

## Settled by decision, September 2026

| Parameter | Value | Note |
|---|---|---|
| Board | 16 mm, sheet 2750 × 1830 | "9×6" on the invoice |
| Backing | 3 mm | imported white decor |
| Groove depth | 8 mm | |
| Groove engagement | 6 mm | 2 mm clearance so the board enters easily |
| Cavity behind the back | 16 mm | room for a rail / stiffener / filler |
| Shelf clearance | 4 mm adjustable, 1 mm fixed | |
| Door height | H − 3 | |
| Door width | W − 3 single, (W − 6)/2 pair | |
| Stacked front gap | 2 mm | |
| Drawer front deduction | Wi − 59 | 25 runner + 2 × 16 sides + 2 clearance |
| Drawer base groove | 16 mm up from the bottom edge | leaves room below |
| Runners | 350 / 450 / 500 | longest leaving 40 mm behind it |
| Exposed end panel | H × (D + 16) | finishes flush with the door face |
| Hinges | 2 up to 1600, 4 above | |

## Derived

| Panel | Formula |
|---|---|
| Side | H × D |
| Top / Bottom | Wi × D (base units carry no top) |
| Support rail | Wi × 100 |
| Shelf, adjustable | Wi × (D − 23) |
| Shelf, fixed | Wi × (D − 20) |
| Back, grooved four edges | (W − 20) × (H − 20) |
| Back, grooved top and sides | (W − 20) × (H − 10) |
| Drawer side | runner × box height |
| Drawer front / back | (Wi − 59) × box height |
| Drawer base, 3 mm grooved | (runner − 20) × (front + 12) |
| Drawer base, 16 mm melamine | (runner − 32) × front |
| Drawer face | face height × (W − 3) |

## The two commercial formulas

Both exact against the real invoice.

```
edging_m = ((edgeL × L + edgeW × W) + 70 × (edgeL + edgeW)) × qty ÷ 1000
potholes = qty × (2 if door length ≤ 1600 else 4)
```

The 70 mm is Plazaboard's trim allowance per banded edge. Verified on all 166
edged rows across the three returned CSVs, zero error. The pot-hole rule gives
92 for the October job, which is exactly what was invoiced.

## Rate card — quotation VRG_SOQ497999, 21 Oct 2025, incl VAT

| Item | Rate |
|---|---|
| Brookhill Fusion board | R999 |
| Super white melamine board | R575 |
| 3 mm white decor board | R310 |
| Beam saw cut | R67 per 16 mm board |
| Masonite cutting | R34 per 3 mm board |
| 2 mm tape | R12/m + R7.50/m to apply |
| 1 mm tape | R8/m + R5/m to apply |
| PVC tape | R2.75/m + R4/m to apply |
| Pot hole | R3 each |

Board and cutting were 82 % of that bill. Nothing is charged per cut, so nesting
yield — not cut count — is the lever. Yields achieved: 89 % melamine, 80 % on
the 3 mm, 78 % on the Brookhill.

## Findings

Errors found in the real jobs. Each is why a validation rule exists.

### Kitchens (D-series, 20 findings — see the published audit)

Headline four: cabinets 45 and 49 shipped with no side panels; drawer banks 32
and 35 contradict the layout drawing; shelves in cabinets 19 and 41 are 16 mm
too deep for their inset backs; doors 3607 and 3707 have no hinge boring.

### Wardrobe, October 2025

| | Finding |
|---|---|
| W1 | Cabinet 14's 397 mm doors specced 4 pot holes; rule gives 2. Sheet said 96, invoice charged 92 |
| W2 | Cabinet 18 ordered a 2882 mm strip off a 2750 mm board. Plazaboard cut it 2730 — 152 mm short — and told nobody |
| W3 | Cabinets 1 and 4 are the same cabinet built three ways: front 610/609, base 622/621, face edging 2 mm/1 mm. The 1 mm line on the invoice (11 m, R143) exists only because of this |
| W4 | Cabinets 8, 9, 10 have a bottom 1 mm deeper than their top |
| W5 | Cabinet 30's four faces of 178 leave 75 mm of open gap in a 787 opening |
| W6 | Cabinet 27's back is 440 wide where the rule gives 480 |
| W7 | PVC WHITE specced on 20 drawer panels; everything was banded in Brookhill |
| W8 | Grain 0 on all 164 rows of the sheet; the Brookhill CSV came back with grain 1 on all 35. The counter caught it, not us |
| W9 | Quantity-zero rows travelled into the order |
| W10 | "2mm WOOD" and "2mm PVC Wood" used for the same tape |
| W11 | All three CSVs name the board SUPWHTTXT, including the Brookhill and the 3 mm |
| W12 | A 2730 × 1300 panel appears in two CSVs but not in the cut list |
| W13 | The corner unit and the overhead have no back; the corner has no rails either |
| W14 | The divider is coded 08 in cabinets 3 and 5, 99 in cabinets 11 and 12 |
| W15 | Cabinet 27's melamine drawer base is 377 × 520, which matches no sensible construction |

## Where the standard changed

Moving to 6 mm engagement resizes every back and every grooved drawer base by
1–2 mm against all previous jobs. The October wardrobe's backs already match the
new rule; the kitchens were cut at 7 mm. Old cut lists are not reusable as-is.
