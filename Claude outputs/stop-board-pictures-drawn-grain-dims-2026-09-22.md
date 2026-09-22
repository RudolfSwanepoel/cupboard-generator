# Stop: a board's picture is what its parts are drawn in

22 September 2026. Against the brief
`claude_brief-doors-colour-grain-2026-09-22.md`.

## The contradiction, resolved

The brief asked which of two prior readings was right: that doors and drawer
faces "were never built" in the wall elevation, or that they clearly were.

**They were built.** The first reading came from a screenshot of an ISOLATED
cabinet — isolate ghosts everything else at `opacity="0.30"`, which is the
feature working, not a missing one. Nothing was rebuilt on the strength of it.

## G1 — what rendered before this stop

`render._interior` has filled every door leaf, every drawer face and the carcass
body with the real board colour since 20 September, resolved through
`board_look` off the same fields the engine cuts from — `door_board(i)`,
`face_board_of(d)`, `carcass_board`. Edge bands, hinge marks, hinge counts and
drawer-face heights on top. Part C was done.

**The picture was read and never drawn.** `board_look` returned it and said so
in its own docstring: *"`picture` is carried because the record has one. Nothing
draws it yet."* That was the one real gap.

## G2 — the diagonals are the swing, not the grain

`render._hinge_marks`: a dashed polyline from the latch edge at the top, to the
hinge edge at mid-height, back to the latch edge at the bottom — the standard
furniture-elevation opening triangle, point on the hinge side, paired with the
"n hinges" label already underneath it.

Grain **was** drawn, separately: `_grain_lines`, fine vertical hairlines at 22 %
opacity on a board whose record says grain. Subtle enough to be missed next to
the swing triangle, which is how the two got confused.

So this was the larger of the two jobs the brief anticipated: real texture had
never been drawn at all.

## G3 — no picture reached any drawing

No `<pattern>`, no `<image>`, not even a representative colour sampled from one.
The only pattern in `render.py` was `ehatch`, the 45-degree hatch for return
profiles.

## What was built

**`render.Fills`** — one class, one rule, every fill in both elevations and the
legend through it.

* **A picture wins over the colour, on a GRAINED board only.** A plain board
  keeps its colour even when it carries a picture. In the current library that
  is BROOKHILL drawn in its photo, GREY (plain, has a picture) drawn in
  `#504f4e`, CASCADE (grain, no picture) drawn in `#b0b0b0`.
* **Tiled as an SVG `<pattern>`, turned onto the panel's grain direction.**
  0 or 90 degrees, never an arbitrary angle — which is what the vertical-source
  convention buys. One pattern per board per direction.
* **The board's colour sits under the image**, so a picture that will not load
  leaves the part its colour rather than a hole.
* **A picture replaces the grain hairlines.** Fake grain over real grain is
  noise.
* **The legend swatch takes the same fill as the parts.**
* **On screen `/pictures/<name>`; exported, the bare file name with the file
  copied in beside it.** `render.pictures_drawn(job)` says which — the export
  does not answer that itself, or it becomes a second list that disagrees.

**The plan stays on flat colour, deliberately.** A plan is a top view: you are
looking at a board's edge, not its face, and a face texture there would be
saying something untrue.

**Grain-vertical validation on upload.** `pictures.grain_verdict` compares
gradient energy along x against along y — the direction the texture is coherent
in, nothing about wood. It warns and never blocks, and says nothing at all about
a picture with no texture or no decisive direction.

The browser samples and the app judges: decoding a JPEG is the one thing the
browser can do that this app cannot, and taking a third-party dependency for an
advisory would be a large price. A 64-square canvas area-averages the picture and
posts the luminance to `/api/picture-grain`.

**Area averaging is the measurement, not a detail.** Point-sampling the real
1135-wide `Brookhill.png` gives +0.08 — indistinguishable from noise. Area
averaging gives +0.29, and holds from a 32-square grid to a 128-square one.

**The top dimension line breaks at every cupboard.** `wall_chain` was the hung
run's edges alone, so past the last overhead it handed over one figure spanning
everything below it — on `Test.json` wall A, `632 | 300 | 3068`. It is
`chain(hung + floor, wall.length)` now: `600 | 300 | 150 | 400 | 400 | 550 | 350
| 600 | 602`, against the bottom's `600 | 450 | 400 | 400 | 550 | 350 | 600 |
602`. Still closes on the wall. A wall with no overheads still gets no top chain.

## Verification

| | |
|---|---|
| `regen_check` | 272 MEL / 59 BROOKHILL / 30 BACK, 92 pot holes, 18 / 9 / 6 boards, R28,363.50, 22 of 30 clean |
| every `tools/check_*.py` | 16 of 16 green |
| `snapshot --compare baseline.json --allow svg` | see below |
| `Check It Still Works.bat` | no failure in the whole run |

**The snapshot was proved, not assumed.** `baseline.json` is the known-stale one
CLAUDE.md describes, so the compare was run twice: once on this code, once on
`HEAD` in a throwaway git worktree with the same `Test.json` and the same
baseline. The two reports differ by **exactly two lines**, both
`svg changed ... (allowed)`. Every non-SVG difference is byte-identical to what
the unmodified code reports — this stop adds nothing to it.

## Exercised in the running app, not only in Python

* Wall A: BROOKHILL parts tiled in the real photo, grain running vertically;
  GREY flat at its colour; legend swatches matching the parts.
* Top dimension line read out of the live DOM against the bottom one — same
  resolution, plus the overhead's own break.
* A grain-sideways picture dropped on the real drop zone: warned in the toast
  and in the field note, and **still taken in**.
* A grain-vertical picture and a flat-colour picture: silent, as intended.
* Export: `Brookhill.png` copied into `output/Test/`, the SVG asking for it by
  bare name, and the drawing rendering the texture when the folder is served.
  Opened where the picture cannot be reached, it falls back to the board colour
  — which is the `<rect>` under the image doing its job.
* Test pictures deleted from `Pictures/` afterwards; the board edit was
  cancelled, so `boards.json` is untouched.

## Not done, and why

* **The plan view** is on flat colour by the reasoning above, not by omission.
* **`baseline.json` not regenerated** — still stale, still deliberately so, for
  the reason already in CLAUDE.md.
* **Nothing from the board-form-rebuild brief** was touched. The diagnosis did
  not show any of it was needed for doors or colour to work.
