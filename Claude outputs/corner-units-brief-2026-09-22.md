# Claude Code brief: corner units (mitre, ell, blind) and greyed-out Size fields

Written 22 Sept 2026 in Cowork. Every ruling here is Rudolf's own, from this session's Q&A. Run this in `C:\Dev\CupboardApp`, one session, and don't run anything else against the repo while it is running.

---

## 0. Before touching anything

1. Run `git pull`, then `git status`. The working tree on swanepoelr-nb showed ~20 files as modified on 22 Sept. A whitespace-blind diff shows no real content in them, so it is probably CRLF churn. Report what you find. **Never run `git checkout`, `git reset`, `git stash` or anything else that discards changes without asking Rudolf first.**
2. Read `CLAUDE.md`, `docs/ROOM-LAYOUT-SPEC.md` items 11–18, and `docs/RULES.md` W13.
3. **Reproduce "corner unit does nothing"** on a fresh cabinet (Add cabinet → tick Corner unit → enter arms/faces) and report the causes before fixing. My reading of the code is below. Confirm or correct each one:
   - `cabinetgen/engine.py` has **no corner branch at all**. A template cabinet with Corner unit ticked still cuts a straight W×D box from the Size fields. The four corner measurements only reshape the plan outline, so nothing on the cut list changes.
   - The Style dropdown defaults to `""`, and `Cabinet.corner_on` needs a style. Ticking the box on its own therefore does nothing, and nothing says why.
   - Cabinet 7 (Oct 2025) only "works" because its panels are hand-typed bespoke panels (`template="none"`).
   - Corner geometry only supports a corner at the wall's **end** (`corner_shadow`: `p.x + arm_a == wall.length`, wall B = next wall). There is no left/right hand.

---

## Part A: Size fields greyed out for panels and corner units (UI consistency)

**Ruling (verbatim intent):** it must be obvious to a new user where a dimension is entered. When Kind = Panel, every dimension lives in *Panel design* and the Size dimensions are greyed. **Exactly the same for corner units:** every dimension lives in the *Corner Unit* section and the Size dimensions are greyed.

A1. In the **Size** section, grey out Width, Height and Depth when the item is a panel (`isPanelCab`) **or** a corner unit is ticked, whatever its type (mitre, ell or blind). Use the existing `unavailableField` pattern, but with its own wording:
   - panel: "Set in Panel design below"
   - corner: "Set in Corner Unit below"

   Each greyed field **shows the engine's derived value** (from `/api/compute` geometry), never a stale declared value. This follows hard rule 1: declared dims are labels only.

A2. Kind, Number and Note stay live. Kind must stay live for corners, because a corner can be **top-hung (upper), base or tall**.

A3. The **Outline** section is also greyed when a corner unit is on ("derived from the corner measurements"). `geometry()` already ignores an entered footprint when the corner resolves, so the field must not look editable.

A4. No data is thrown away. Switching the tick or the kind back restores everything (spec item 16).

**Acceptance:** Panel → only Panel design takes sizes. Corner ticked → only Corner Unit takes sizes. Untick → the Size fields are live again with the values they had before.

---

## Part B: The Corner Unit section is rebuilt around three types

B1. **Type:** Mitre / Ell / Blind. This replaces the style dropdown and its blank option. Ticking *Corner unit* with no type chosen shows one plain line, "Choose a corner type", instead of silently doing nothing. `corner_style` gains `"blind"`.

B2. **Hand:** Left / Right, required for all three types. It says in plain words which end of the unit is in the corner, as you stand in the room facing the unit. Add a small plan icon for each type × hand. New field `corner_hand: "L" | "R"`.
   - A **missing** hand reads as whatever today's geometry does (corner at the wall's end), so old jobs and cabinet 7 are unchanged.
   - Work out and state which wall end "Right" maps to. Don't assume it.
   - The other hand mirrors the outline, the front faces, the hinge logic and `corner_shadow` onto the **previous** wall.

B3. **Fields per type.** All sizing lives here, and nothing else in the cabinet editor asks for sizes.

| Type | Fields |
|---|---|
| Mitre / Ell | Height, Arm A, Arm B, Face A, Face B. Relabel in plain words (e.g. "Length along this wall", "Length along the return wall", "Open end on this wall = depth of the run it meets") |
| Blind | Carcass width, Height, Depth, Blind panel width |

   Height, and for blind the width and depth too, are stored in `cab.height` / `cab.width` / `cab.depth`, as now. Only the place they are entered moves.

B4. **Readout line** (extend `refreshGeometryReadout`):
   - Mitre: the derived size, the mitre angle and the face length.
   - Ell: the face lengths.
   - Blind: opening and door width, e.g. "W 1000, blind 500 → opening 468, door 497".

B5. **Other sections for a corner unit:**
   - **Mitre / ell:** back fixing and supports greyed with "no back and no supports on a corner unit, as built (RULES W13)". Drawers greyed.
   - **Blind:** it is a straight box, so Structure (back, supports, shelves) works exactly as for any cabinet. Drawers greyed. Doors are fixed at 1.

---

## Part C: Mitre, generated from the four measurements

The rules are already ruled and live in the spec (items 11–15). The outline is derived, the angle is an output only, there is no angle field, and nothing compares the angle with 45°.

C1. **Engine:** add a corner branch in `generate_cabinet` for `corner_on` and style `mitre` on a template cabinet. The panels below are derived from cabinet 7's real cut list (t = the carcass board's thickness, never a hardcoded 16):

| Part | Size | Notes |
|---|---|---|
| Open-face sides | H × face_a and H × face_b | |
| Wall sides | H × (arm_a − t) and H × (arm_b − 2t) | One wraps the other. The hand decides which is which, and the validator's existing rule in `_outlines` already expects this |
| Top and bottom | (arm_a − 2t) × (arm_b − 2t) | Guillotine blank. The panel note says "mitre on site" and gives the two leg lengths. **Plazaboard cuts guillotine only**, so a mitre is always trimmed on site |
| Top on a base mitre | none | Follows the standing base rule (no top), unless Q2 says otherwise |
| Door | height H − `door_height_gap`; width = face length − `door_single_gap` | **Ruled: the standard gap, not cabinet 7's 23 mm.** A pair (the Doors section allows 1 or 2) = (face − `door_pair_gap`) / 2 |
| Door options | board, edging, hinge side | Exactly as on any door |

   Let `engine.born_distinct` assign the suffixes (01a/01b/01c). Never hand-assign them.

C2. **Door clash blocks export (ruled 22 Sept).** Check the mitre door's swing against the cabinets and doors on **both** walls, in world coordinates, using `swing_envelopes`. A foul is **CRITICAL** for corner units, and the message states the minimum arm (or maximum door) that clears.

   This is a deliberate exception. The house rule in `validate._room` keeps an ordinary door-swing foul as a WARNING, and ordinary doors stay that way. Write the exception into the `_room` docstring and into CLAUDE.md so no later session "fixes" it back.

C3. The designer can still override: keep an optional door-width override on the corner door. It defaults blank, meaning derived.

**Acceptance:** a new *template* cabinet with cabinet 7's numbers (tall, 850/850/500/500, H 2400, no back, no supports, 1 door) must generate:
- sides 500 ×2, 834 and 818
- top and bottom 818 × 818
- door 2397 × 492 (the 492 is deliberate)
- shelves per Q1

Cabinet 7 in `jobs/wardrobe_oct2025.py` **stays bespoke and untouched**, so the benchmark can't move.

---

## Part D: Blind corner, a straight single-door cupboard

**Ruled construction.** A straight carcass, with a large **flush blind panel** at the corner end and **one door** at the far end. The run on the return wall is ordinary cabinets and panels, and it is not part of this unit.

D1. **Inputs:** carcass width W, height H, depth D, blind panel width B, and the hand (which end is blind).

D2. **Derived sizes** (t = the carcass board's thickness):

| Item | Rule |
|---|---|
| Opening | O = W − 2t − B |
| Door | Derived from the opening **exactly like any other door**, with the same adjustments (board, edging, hinge side, door-height override). An ordinary door is (opening + 2t) − `door_single_gap`, so here door = O + 2t − `door_single_gap` = W − B − `door_single_gap` |
| Blind panel | **Exactly B wide** ("the board size is the board size"), same height as the door, cut from the exterior board, grain as a door (vertical), edged like the door, fixed (no pot holes). Code per Q3 |
| Carcass | Sides, top/bottom, back, supports and shelves: the standard engine path for W × H × D, unchanged |

   Worked example, which must show in the readout and pass as a check: W 1000, B 500, t 16 → opening 468, door 497, blind panel 500.

D3. **Default hinge side:** the far (outer) end, so the door's free edge sits beside the blind panel. The operator can change it, as on any door.

D4. **Plan:** a plain rectangle W × D. Give the blind unit a shadow on the return wall, like `corner_shadow`. The return run starts at the blind unit's depth, so Gaps must not propose a filler for that space.

D5. **Validation (critical, per Q4):**
   - the return run's first cabinet, including its door front, reaches past the blind panel into the door opening;
   - the door is ≤ 0 wide;
   - B ≥ W − 2t.

---

## Part E: Ell, shape only (panels parked by Rudolf)

Rudolf has never built one and has **deferred the construction**. Build what is known:
- the outline (already in `corner_outline`)
- the hand
- plan drawing, overlaps, shadow and gaps
- a face-length readout
- two faces, one door per face, shown as intent only

The engine generates **nothing** for an ell, and don't invent one. Give the ell a CRITICAL: "Ell corner: construction not decided yet, so this unit cuts nothing. Add bespoke panels in the job file or change the type." An ell with `template="none"` bespoke panels works like cabinet 7.

---

## Open items: ask Rudolf in ONE batched round at the start. Each has a default that applies until he answers.

- **Q1 Mitre shelves.** Cabinet 7 cut 6 shelves at 818 × 350 (350 = arm − face), and the rule behind that isn't known. Default: shelves follow the top/bottom square blank, less the shelf clearance at the back, with the note "mitre on site". Show him cabinet 7's figures when asking.
- **Q2 Base mitre bracing.** A base unit has no top, and a corner has no supports (W13), which leaves a base mitre unbraced. Default: no top, no supports, plus a warning asking him to confirm.
- **Q3 Blind panel code.** Default: `08` with role "Blind Panel", suffixed by `born_distinct` if the cabinet also has an 08 exposed side. The code needs Plazaboard sign-off, like 10/11.
- **Q4 Blind clearance.** Rudolf ruled that a mitre door clash blocks export. This brief applies the same to a blind unit whose opening is covered by the return run. Confirm. Also ask whether the check needs a handle clearance on top of the return door's thickness (default: none).

---

## Final step

1. Re-run the regression benchmark: **272 MEL / 59 DECOR / 30 BACK, 92 pot holes, 18/9/6 boards, R28,363.50.** It must be exact.
2. Re-run every `tools/check_*.py`, and extend `check_drag.py` with the Part C and D acceptance cases and the mirrored hand. Remind Rudolf to spot-check with `Check It Still Works.bat`.
3. Drive the real UI through each of these and report pass/fail **per item**, not as a batch:
   - panel greying
   - corner greying
   - the type prompt
   - mitre L and R
   - blind L and R with the 1000/500 example
   - an ell's critical
   - a clashing mitre blocking export
4. Update CLAUDE.md (the Status section, the corner rules and the C2 exception) and add spec items 19+ to `ROOM-LAYOUT-SPEC.md` recording these rulings.
5. Stop at a clean point and give Rudolf the exact commit message to paste, e.g.:
   `Corner units: mitre and blind generated, ell shape-only, hand L/R, Size fields greyed for panels and corners`
