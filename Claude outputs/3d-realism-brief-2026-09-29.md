# Brief: the 3D view drawn realistically (29 September 2026)

Agreed with Rudolf in Cowork. The wall elevations read as drawings; the 3D
reads as a cartoon. The report in the Drawers fixes brief (Part 6, and in
CLAUDE.md) measured why: GREY `#504f4e` is handed to the material exactly,
but the lights deliver about 65 % of it on screen, and the selection is an
additive blue glow at 0.14 that turns a dark board navy. This brief is
**`app/view3d.js` and its vendored libraries only**: no file under
`cabinetgen/` changes, `/api/scene` is byte-identical, `check_scene.py`
and `check_colour.py` pass unchanged except where a rule below says a
`PAPER` entry is added. Run **Local** (screenshots are the acceptance).
Benchmark unchanged, `check_all` green, all four Playwright scripts pass
(`ui_check_3d.py` reads `project` / `bounds` / `camera`, which must not
move).

Two rounds. Round 1 is built, screenshotted and committed; Rudolf looks;
Round 2 after his notes. Before-and-after screenshots of the same views
(3D tab Home on Test.json; Cabinets 3D on cabinet 4, fronts closed and
open; a wall face-on view `1`) go into
`Claude outputs/3d-realism-screenshots/`.

## Round 1: colour, light, selection, texture

1. **A board's colour on screen is its colour.** Rule: a plain board's lit,
   face-on surface, unselected, in the default view, renders within a small
   tolerance of its swatch hex (target: within 8 units per channel; report
   the figures for WHITEMEL, GREY and BROOKHILL's fallback colour). Do it
   with physically based lighting, not by brightening the colour: a
   neutral image-based environment for diffuse and reflections
   (`RoomEnvironment` through `PMREMGenerator`, vendored from three's own
   `examples/jsm/environments/` at the same 0.186.0 with its licence), a
   key directional light for form, and tone mapping that does not tint
   (`NeutralToneMapping`, exposure set so the rule above holds).
   `outputColorSpace` stays sRGB; every colour and texture is tagged with
   the right colour space so nothing is double-converted.
2. **Melamine looks like melamine.** `MeshPhysicalMaterial`, roughness
   about 0.45, metalness 0, a light clearcoat for the sheen a melamine face
   has under room light; one material per board, shared. Edging bands keep
   their board colour. The runner blocks stay grey hardware. Report the
   figures chosen and keep them in `PAPER` (or a sibling `LOOK` block that
   `check_colour.py` is taught to allow: no colour literal outside those
   two blocks).
3. **Grained boards draw their picture.** The scene already sends the
   picture URL and each part's `grain` vector for grained boards
   (`render.PICTURE_TILE_MM`). Apply it as a texture: sRGB, repeat-wrapped,
   tiled at `PICTURE_TILE_MM` in world mm, turned so the grain runs along
   the part's grain vector (the elevation's rule: 0 or 90 degrees, never a
   guessed angle), anisotropic filtering at the renderer's maximum, loaded
   once per board and shared. Plain boards stay flat colour (the
   elevation's rule, unchanged). No picture or a failed load: the colour.
4. **Selection is an outline, not a tint.** The additive emissive glow on
   the selected cabinet goes. Selected = its edges drawn in the accent, a
   touch heavier, plus the existing label; hover the same at `PAPER.hover`,
   lighter. The board colour under it does not change. The obstruction's
   warning emissive stays (it is meant to shout). Clash red stays.
5. **Edges quieter.** In Shaded + edges, the edge lines are thinner and
   drawn only where a face meets another at an angle (`EdgesGeometry`
   threshold about 20°), not on every coplanar seam; the three edge weights
   in `PAPER` keep their roles. X-ray and Edges-only modes unchanged.
6. **The room is matte and neutral.** Floor, walls and ceiling non-glossy
   (roughness ~0.9), the grid a little fainter, the background a very
   slight top-to-bottom gradient rather than one flat colour. A gradient is
   two `PAPER` entries.

Pinned: `ui_check_3d.py` gains `--stage look`: read the centre pixel of
cabinet 4's front face in the Cabinets 3D at Home, unselected (select
another cabinet first), and assert it within the tolerance of GREY's hex;
select it and assert the pixel is unchanged (the outline, not the face,
shows selection).

## Round 2 (after Rudolf's notes): depth

7. **Shadows.** The key light casts soft shadows (PCF soft, a shadow map
   sized to the room, its frustum fitted to the scene bounds on each
   rebuild); every board casts and receives; a faint contact shadow under
   standing cabinets so they sit on the floor rather than float. Render on
   demand stays: the shadow map is updated only when the scene or the light
   changes, never per frame while orbiting.
8. **Ambient occlusion.** Try three's `GTAOPass` (vendored from
   `examples/jsm/postprocessing/` with `EffectComposer`, same version,
   licences kept). Keep it if it holds the frame rate on the laptop with
   Test.json's room and adds depth in the corners and drawer boxes; behind
   a toggle in the 3D toolbar (`AO`), default on; off under X-ray. If it
   costs too much, say so with the numbers and leave it off by default.
9. **Snapshot** (`/api/snapshot`) captures the same image the viewport
   shows, shadows and AO included.

## Not in this brief

Legs, handles, hinges and worktops are still not drawn (nothing modelled).
The Cabinets-tab and 3D-tab views share one `createView`, so every change
lands in both; do not fork them. No change to what is selected, how
anything is moved or snapped, the camera maths, or any check id.

## Report and commit

Per round: one commit, the screenshots, the figures asked for in 1 and 2,
and the frame-time numbers for 8. Update CLAUDE.md (Status; **The 3D view**
section: lighting, materials, textures, selection, shadows, AO; the
vendored additions in Layout).
