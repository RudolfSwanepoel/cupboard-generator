# 3D realism, Round 2: Rudolf's notes on Round 1 (29 September 2026)

Round 1 (commit 02b3a7b, merged to master) is better but not there. Read
this with `3d-realism-brief-2026-09-29.md`; it replaces that brief's
Round 2 list. Same rules: `app/view3d.js` and vendored three.js files only;
`/api/scene` byte-identical; benchmark and `check_all` unchanged; the four
Playwright scripts pass; screenshots of the same views before and after
into `Claude outputs/3d-realism-screenshots/`.

**The reference is `Claude outputs/3d-realism-screenshots/reference-kitchen-brookhill-grey.jpg`**:
a kitchen Rudolf built in exactly the boards Test.json uses, BROOKHILL and
GREY, under ordinary downlights. Look at it before touching anything. The
board catalogue picture is the master source for BROOKHILL's look; the
photo is what it looks like fitted. The wall elevation already reads
right; the 3D must reach the same board colours and then add light.

## 1. BROOKHILL is the wrong colour and the wrong scale (first, it is the biggest fault)

In the elevation and the photo it is a pale, grey-toned oak with wide
planks and knots. In the 3D it is saturated orange-brown with fine stripes.

- **Colour.** Tag the picture texture `SRGBColorSpace` (it is almost
  certainly being read as linear and gamma-shifted darker and warmer), and
  check nothing else re-encodes it. Then apply the Round 1 swatch rule to
  textured boards too: the MEAN colour of a lit, face-on BROOKHILL door in
  the default view must be within the tolerance of the mean colour of the
  picture itself. Report both figures.
- **Scale.** Cabinet 10's 600 door shows about three planks in the wall
  elevation and eight or more stripes in 3D. The tile must be
  `render.PICTURE_TILE_MM` in WORLD millimetres, exactly as the elevation
  tiles it (40 px at its scale = 160 mm). Measure plank width on the same
  door in both and make them agree; report the numbers.
- Grain direction stays as built (turned onto the part's grain vector).

## 2. Door and drawer gaps must read

The 3 mm gaps are modelled but draw as nothing, and Round 1's "edges only
at angles" rule dropped the seams between neighbouring doors because they
are coplanar. In the photo the gaps are the dark lines that make a run
read as doors.

- Every FRONT (door leaf, drawer face, blind panel) draws its perimeter as
  a thin line at `PAPER.edgeFront` regardless of coplanarity; the angle
  threshold still applies to carcass and interior parts.
- Round 2's shadows and occlusion (4) then put real dark in the gaps.
  Check on cabinet 4's drawer stack and on the 12 / 13 / 10 tall run that
  each leaf and face is separable at the 3D tab's Home zoom.

## 3. The Cabinets-tab view draws no selection outline

That view IS the selection, so Round 1's accent outline lands on every
edge of the shown cabinet (cabinet 7's screenshot: blue on everything).
There: no cabinet outline at all; only a PICKED part gets the accent
outline, and the hover its lighter one. The 3D tab is unchanged.

## 4. Light and depth (the brief's Round 2, kept)

Everything is lit the same: the white carcass's top, front and side read
as one brightness, so nothing has form. The environment is doing all the
work.

- **Key light** stronger relative to the environment, from above and a
  little in front (the photo's downlights): top faces brightest, fronts
  mid, sides a step darker. Re-check the Round 1 swatch rule on the
  face-on front after re-balancing; it must still hold.
- **Shadows**: the key casts soft shadows (PCF soft, map fitted to the
  scene bounds on each rebuild); every board casts and receives; a faint
  contact shadow under standing cabinets. Shadow map updated only when the
  scene or the light changes, never per frame while orbiting.
- **Ambient occlusion**: three's `GTAOPass` with `EffectComposer` (vendored,
  same version, licences kept) behind an `AO` toggle in the toolbar,
  default on, off under X-ray. Keep it if it holds the frame rate on the
  laptop with Test.json's room; if not, default off and say so with the
  numbers.
- **Snapshot** captures what the viewport shows.

## 5. The room

Grid floor and no wall colour read as a drawing. In Shaded modes: the
floor a plain pale tile colour (`PAPER.floor` lightened; a faint 600 mm
tile grid at most), the walls a warm plaster grey near the photo's, the
ceiling off-white. The drawing grid stays and is the default in Edges and
X-ray; a `Grid` toggle in the toolbar for Shaded. Colours in `PAPER` only.

## 6. Also, small

- `tools/check_launch.py` fails on Linux (Windows-only checks). It must
  print "skipped: Windows only" and exit 0 there, so a cloud run's
  `check_all` can be green.
- `ui_check_3d.py --stage look` extends to BROOKHILL's mean-colour rule.

## Order and report

1 → 2 → 3 → 4 → 5 → 6, one commit each, screenshots after 1, after 3 and
after 5. Push to master (not a branch). Report the colour and plank
figures from 1, the frame-time numbers from 4, and stop for Rudolf.
