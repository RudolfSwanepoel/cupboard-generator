# Corner units: rulings as they stand (22 Sept 2026)

This consolidates everything Rudolf ruled on 22 Sept 2026, in Cowork and in answer to Claude Code's questions during the corner-units session. **Where it differs from `corner-units-brief-2026-09-22.md`, this file wins.** At its final step, Claude Code folds these rulings into `CLAUDE.md` and into `docs/ROOM-LAYOUT-SPEC.md` as items 19 onward.

---

## 1. Diagnosis of "corner unit does nothing" (read off the code, 22 Sept)

- `engine.py` had no corner branch. Ticking Corner unit only reshaped the plan outline; the cut list stayed a straight W×D box.
- The Style dropdown defaulted to blank, and `corner_on` needs a style, so the tick alone did nothing.
- Cabinet 7 (Oct 2025) only works because its panels are hand-typed bespoke panels (`template="none"`).
- There was no left/right hand. A corner could only sit at a wall's end.

## 2. Editor consistency (the intent behind every UI rule here)

The app must be obvious to a new user. **Each dimension is entered in exactly one place.**

- **Kind = Panel:** every size is in *Panel design*. Size W/H/D are greyed and show the derived values.
- **Corner unit ticked** (any type): every size is in *Corner Unit*. Size W/H/D and Outline are greyed and show the derived values.
- Kind, Number and Note stay live. A corner can be tall, base or top-hung (upper).
- Nothing is thrown away when a tick or the kind is switched back.

## 3. Corner types

There are three types: **Mitre**, **Ell** and **Blind**. Every type takes a **Left/Right hand**, stated in plain words as you stand in the room facing the unit, with a small plan icon. A missing hand means today's behaviour (corner at the wall's end), so old jobs are unchanged.

## 4. Mitre construction (all kinds: tall, base and upper)

| Part | Rule |
|---|---|
| Open-face sides | Melamine, H × face_a and H × face_b |
| Back | **Melamine along both walls**: the two wall panels, (arm − t) and (arm − 2t), one wrapping the other (cabinet 7: 834 / 818). Kept coded as sides (01, suffixed by `born_distinct`). Never renamed |
| Backing | No 3 mm backing board, no grooves, no supports on any mitre |
| Top and bottom | Melamine, square blank (arm − 2t) × (arm − 2t), mitred on site. **A base mitre also gets the top.** This overrides the base no-top rule, for corners only. Straight cabinets are unchanged |
| Bracing and hanging | Fully braced, so no warning. An upper mitre hangs by fixing through its melamine wall panels, so no hanging warning |
| Angle | The mitre angle is an output only (spec item 12). No angle field, nothing compares it with 45° |

**Door**
- **RULED 22 Sept: mitre door width = the inner span between the open-face sides' inner front corners, rounded DOWN to the whole mm, with no gap deducted.** Cabinet 7: 472.3 → **472**, as actually cut (707: 2397 × 472, 2 mm edging all round, 4 pot holes). The door sits within the span rather than overlaying the side edges, because the sides meet the door at an angle. A pair = (inner span − `door_pair_gap`) / 2. This replaces "face length − 3".
- Background: cabinet 7's own CAD plan view (`Wardrobes/Main Bed Cupboard Assembly Planview.pdf`, vector-measured at 818 mm to 92.7 drawing units) shows:
  - the door lying flat on the line through the side panels' INNER front corners, covering exactly that span, 472 mm;
  - the side panels' outer corners standing 11 mm proud of that line.

  A face − 3 = 492 door would foul those corners. The earlier ruling (face length − 3) is suspended until Rudolf rules. The proposal is door = the inner span (the mitre cut edge at zero set-back). A pair = (inner span − `door_pair_gap`) / 2. Height = H − 3.
- Board, edging and hinge side work as on any door. An optional door-width override stays available.
- **A door-swing clash with the cabinets or doors on either wall is CRITICAL and blocks export.** This is a deliberate exception: ordinary doors stay a WARNING. Record it in the `validate._room` docstring and in CLAUDE.md.

**Shelves.** Two types; both can be used in one unit. They replace Shelves / Fixed shelves in the mitre's Corner Unit section.

- **Arm shelf** (cabinet 7's configuration)
  - A rectangle along one arm (A or B, default A). Length = arm − 2t.
  - Maximum depth = the lesser of:
    - the distance to the door's inside face less the door clearance;
    - the distance to the front edge of the open-face side panel less **`Standard.hinge_clearance` = 50 mm** (confirmed).
  - The maximum is **rounded DOWN to the nearest 5 mm** (359 → 355). Cabinet 7's maximum is 434 → 430.
  - The depth field defaults to the rounded maximum. A typed depth is taken as typed. Above the maximum is a CRITICAL.
  - Hinge clearance applies whichever side the door is hinged.
- **Mitred shelf**
  - The square blank (arm − 2t) × (arm − 2t), mitred on site, with its mitre cut set back **`Standard.mitre_shelf_clear` = 3 mm** from the door's inside face. The clearance is measured **after** the mitre edge is banded with carcass edging.
  - The panel note gives the two mitre legs, **measured from the blank's own corner**.
  - Resolved: the mitre cut joins the INNER front corners of the two open-face side panels, so cabinet 7's legs are **334** at zero set-back (cut edge 472.3, which is exactly cabinet 7's door), and **338 × 338** at the 3 mm set-back (cut edge 478). Cowork's earlier 318 wrongly used the outline's outer-corner diagonal.
- **Hinges and mitred shelves:** do nothing. No notch, no note, no extra set-back, no check. The assembler places shelves clear of the hinges.
  - `hinge_positions` stays drawing-only.
  - Shelf heights stay unmodelled. Modelling everything (shelf heights, build/exploded view) is a later, separate piece of work; build nothing towards it now.
- **How shelves are fixed** (pegs or fixed) is never noted or generated. That is the assembler's choice.

**Benchmark.** Cabinet 7 in `jobs/wardrobe_oct2025.py` **stays bespoke and untouched**. A *template* copy with cabinet 7's numbers must generate:
- sides 500 ×2, 834 and 818
- top and bottom 818 × 818
- door 2397 × 492
- an arm shelf at 350, accepted

## 5. Blind corner

A straight carcass with a large flush **blind panel** at the corner end and **one door** at the far end. The return run is ordinary cabinets and panels, not part of this unit.

> **Superseded in part.** `blind-corner-inset-brief-2026-09-22.md` (22 Sept 2026, final) is the ruling for the blind panel's construction: it sits INSIDE the carcass between the top and the bottom, it names its own board and its own edging thickness, and it carries one banded edge. The opening and the door below are unchanged.

- **Inputs** (all in the Corner Unit section): carcass width W, height H, depth D, blind panel width B, and the hand.
- **Opening** O = W − 2t − B, where t is the carcass board thickness, never a hardcoded 16.
- **Door:** derived from the opening **exactly like any other door**, with the same adjustments. Door = O + 2t − `door_single_gap` = W − B − 3.
  - Worked example: W 1000, B 500 → opening 468, door 497, blind panel 500.
  - Default hinge at the far (outer) end; changeable.
- **Blind panel:** exactly **B** wide ("the board size is the board size"), and **INSIDE the carcass** — superseded in detail by `blind-corner-inset-brief-2026-09-22.md`, which is the final ruling. In short:
  - It sits between the corner-end side panel and the opening, front face flush with the carcass front edges, and runs between the top and the bottom: **(H − 2t) × B**. A base unit has no top and is the same figure — it runs up to the underside of the front support, which is the same 16 mm board.
  - The door is an ordinary **overlay** door on the outside, unchanged at `W − B − 3`. It overlays the blind panel's face by `t − door_single_gap / 2` = 14.5 mm, the same as it overlays the far side panel.
  - **Board is selectable** (`Cabinet.blind_board`, blank = the exterior board, which is the default because the visible strip sits beside the doors). It is in `Cabinet._board_slots`.
  - **Edging is ONE long edge** — the vertical edge facing the opening, the one rubbed when reaching in. Grain vertical, so `edge_l = 1`, `edge_w = 0`. Thickness is selectable 1 mm / 2 mm (`Cabinet.blind_edge_kind`, None = the doors'); colour is the panel's own board's edging.
  - **Code 08, role "Blind Panel"**, suffixed by `born_distinct` if the cabinet also has an 08.
  - **Never drilled:** no pot holes, no hinges.
  - It is **not a filler** (filler is code 11). Never call it a filler anywhere.
- **Carcass:** back, supports and shelves follow the standard engine path. Drawers are greyed, and Doors is fixed at 1.
- **Plan:** a rectangle W × D. It casts a shadow on the return wall so the return run starts at its depth and Gaps proposes no filler there.
- **Critical if:**
  - the return run's first cabinet, including its door front, reaches past **B** — the threshold stays at B after the inset ruling, because what has to clear is the DOOR, whose corner-end edge still stands `B + door_single_gap / 2` from the corner, not the opening, which now starts at `t + B`;
  - the door is ≤ 0 wide;
  - B ≥ W − 2t;
  - the panel's board does not offer the edging kind asked for (the standard EDGING critical).

## 6. Ell

**Construction is parked by Rudolf.**

- Build the outline, the hand, plan drawing, overlaps, shadow and gaps, and a face-length readout.
- The engine generates **nothing**.
- CRITICAL: "Ell corner: construction not decided yet, so this unit cuts nothing." An ell with bespoke panels in the job file works like cabinet 7.

## 7. New Standard values

| Name | Value | Status |
|---|---|---|
| `hinge_clearance` | 50 mm | confirmed |
| `mitre_shelf_clear` | 3 mm | confirmed |

## 8. Still open (not blocking this build)

- Ell construction.
- Rudolf may later measure his own hinges and adjust `hinge_clearance`.
- Plazaboard sign-off on codes 10/11 (unchanged). The blind panel uses 08, so it needs no sign-off.
