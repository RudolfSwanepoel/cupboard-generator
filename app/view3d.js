/* The 3D view (Part F, 23 September 2026).

   A DRAWING of the model, and nothing else. The server builds the scene from
   `room.solid_parts` (`/api/scene`) and this module only draws it: it extrudes
   the outlines it is given, rotates a door by the angle it is given, and picks
   the nearest snap from a list it is given. The one thing it works out by
   itself is the camera — orbit, pan, zoom, projection — because that moves the
   viewer and not the model.

   Loaded by index.html the first time the 3D tab is opened, through the small
   interface at the bottom of this file. Vanilla JS, no build step. three.js
   0.186.0 and camera-controls 3.1.2 come off /vendor/, served by the app.

   Z up, millimetres: world axes exactly as room.py defines them — X right, Y
   into the room from wall A, Z up. No axis swap anywhere.                    */

import * as THREE from "three";
import CameraControls from "camera-controls";
import {LineSegments2} from "three/addons/lines/LineSegments2.js";
import {LineSegmentsGeometry} from "three/addons/lines/LineSegmentsGeometry.js";
import {LineMaterial} from "three/addons/lines/LineMaterial.js";
import {GTAOPass} from "three/addons/postprocessing/GTAOPass.js";

CameraControls.install({THREE: THREE});

/* ---------- the view's own colours ------------------------------------------
   PAPER is the ONLY place a colour literal may appear in this file
   (tools/check_colour.py holds it to that). None of these is a board: every
   board is drawn in the look the server sends, off render.board_look.        */
const PAPER = {
  bgTop: 0xf4f5f2,       // the viewport: a very slight top-to-bottom gradient (29 Sept 2026)
  bgBottom: 0xe6e8e3,
  floor: 0xe4e6e0,       // the floor slab, as a drawing (X-ray)
  wall: 0xf4f4f1,        // wall planes, as a drawing (X-ray)
  ceiling: 0xf7f7f4,
  // the room in the Shaded modes (Round 2, 29 September 2026), off the
  // reference kitchen: pale floor tiles, warm plaster walls, an off-white ceiling
  // (a floor faces the key and the ceiling's light squarely and is drawn about
  // 1.4 times its colour: these two are stated darker than they read, which
  // is PAPER.floor lightened — measured #ecece7 on screen)
  floorTile: 0xcdcdc8,
  tileJoint: 0xb0b0aa,   // the faint joint between 600 mm tiles
  plaster: 0xcbc3b6,
  ceilingShaded: 0xf5f4ef,
  gridMinor: 0xd5d9d2,
  gridMajor: 0xb9beb5,
  edgeWall: 0x2a2d2b,    // heaviest
  edgeCarcass: 0x3a3f3c,
  edgeFront: 0x6a706c,   // lightest
  edgeRoom: 0x9aa09b,
  obstruction: 0xd9542b, // a strong warning colour: never lost
  pivot: 0x2f6b4f,
  accent: 0x1f6fd0,      // the selection
  hover: 0x5a8fd6,
  clash: 0xa4303f,
  clear: 0x7a8f86,
  overlap: 0xa4303f,
  crit: 0xa4303f,
  warn: 0x8a6d1f,
  cube: 0xf7f7f4,
  cubeEdge: 0x8a908c,
  cubeText: "#2a2d2b",
  cubeHot: "#dbe7f7",
  ink: "#191c1a",
  muted: "#767e78",
  fallback: "#d9d6cf",  // a look the server did not send (model.NO_COLOUR); never a board
  runner: 0x8d9398,      // a drawer runner's outer channel: hardware, not a board — plain grey
  runnerInner: 0xb4b9bd, // its inner member, a tone lighter so the two read apart
  white: 0xffffff,       // lights
  contact: 0x1c1e1d,     // the contact shadow under a standing cabinet
  cubeGround: 0x999999,
  none: 0x000000,        // emissive off, and a transparent clear
};

/* ---------- the look: light, surface and line figures ---------------------------
   The 3D realism brief, Round 1 (29 September 2026). LOOK is the one place a
   lighting, material or line figure is stated, as PAPER is for colours. A
   board's colour still comes off the server (render.board_look); what is
   here is how it is LIT and what its surface is. The exposure is set so that
   a plain board's face, unselected, in the default view, renders within a few
   units of its swatch hex — checked in ui_check_3d.py --stage look.        */
const LOOK = {
  exposure: 1.0,          // NeutralToneMapping exposure (tuned below, see the Status entry)
  environment: 0.7,       // the environment's intensity: the diffuse floor and the reflections
  sky: {ceiling: 1.2, wall: 1.0, floor: 0.5},   // the neutral room the environment is: radiance per face
  // the one directional light, for form: the IRRADIANCE it puts on a front
  // that faces it squarely along the floor (Round 2). The light's own
  // intensity follows from where it stands (`fitKey`), so a front reads its
  // swatch whether the key is over an L of two runs or one cabinet alone.
  key: 1.4,
  // where the key stands (Round 2): above and a little in front of the fronts,
  // as a ceiling's downlights are — `elevation` degrees up from the floor,
  // and with no room `turn` degrees round from straight in front, so the side
  // the Home view shows takes less of it than the front
  keyFrom: {elevation: 55, turn: 25},
  // the key's shadow: three r186's PCFShadowMap (its PCFSoftShadowMap is gone:
  // "has been removed. Using PCFShadowMap instead"), softened by `radius`
  shadow: {size: 2048, radius: 3, bias: -0.0004, normalBias: 5, strength: 1},
  // the faint contact shadow under a cabinet standing on (or a leg height
  // off) the floor: `margin` mm out from its footprint, fading to nothing
  contact: {opacity: 0.22, margin: 70, reach: 200},
  // ambient occlusion (three's GTAOPass): radius and thickness in mm
  // (the pass's defaults are for a scene in metres); `denoise` is the depth, in
  // mm, within which the denoiser takes a neighbouring pixel as the same surface
  ao: {radius: 140, thickness: 180, scale: 1.3, samples: 16, distanceExponent: 1,
       distanceFallOff: 1, intensity: 1, resolution: 1, denoise: 250, passes: 3},
  board: {roughness: 0.45, metalness: 0, clearcoat: 0.12, clearcoatRoughness: 0.5},   // melamine
  tape: {roughness: 0.45, metalness: 0, clearcoat: 0.12, clearcoatRoughness: 0.5},    // an edging band
  runner: {roughness: 0.45, metalness: 0.3},                                          // hardware: grey
  room: {roughness: 0.9, metalness: 0},                                               // floor, walls, ceiling: matte
  edge: {opacity: 0.55, angle: 20},   // Shaded + edges: only where faces meet at an angle, and quieter
  front: {opacity: 1, angle: 1, width: 1.25},   // a FRONT's perimeter: every edge, full strength, in every display mode (px)
  outline: {selected: 2.0, hover: 1.4},   // the selection is an OUTLINE (px), not a tint
  grid: {minor: 0.22, major: 0.4},
  tile: {size: 600, joint: 4},         // the floor's tiles in the Shaded modes, mm
};

const PIXEL_RATIO_CAP = 2;
const LINES = 1;             // the layer every paper line is on (see `draw`)
const CLICK_PX = 4;          // press and release within this is a click
const GHOST = 0.30;          // the house opacity for "not the focus"
const XRAY = 0.35;
const FLY_MS = 300;

/* ---------- one view, as many times as it is shown ---------------------------
   UI restructure (28 September 2026): the 3D tab draws the room, and the
   Cabinets tab draws the ONE selected cabinet alone with the same engine and
   the same controls. Each is its own instance of everything below — renderer,
   cameras, state — made by `createView`. `opts.single` is the Cabinets tab's:
   no walls, no layers, no item list, and move handles only for an ATTACHED
   panel, which it drags in its cabinet's frame (attached-panels spec B4). */

export function createView(OPTS) {
OPTS = OPTS || {};

/* ---------- state ------------------------------------------------------------ */

const V = {
  els: {},             // view, bar, list, dock, status, from index.html
  hooks: {},           // what index.html asked to be told about
  renderer: null, scene: null, root: null, camera: null, persp: null, ortho: null,
  controls: null,      // the LIVE controls (perspective or orthographic)
  cP: null, cO: null,  // one CameraControls per camera; only one is enabled
  clock: null,
  visible: false, running: false, lost: false,
  observer: null, grid: null, note: null,
  ortho_on: false,
  // the scene as last sent, and what was built from it
  payload: null,
  groups: new Map(),   // cabinet number -> THREE.Group, userData.hash
  roomParts: null,     // plinths and fillers
  shell: null,         // floor, walls, ceiling, obstructions
  textures: new Map(), // `${board}:${rot}` -> Texture, a rotated clone of the board's picture
  pictures: new Map(), // board -> {tex, failed}: the picture itself, loaded once
  materials: new Map(),// the shared materials, one per board per variant (see boardMaterial)
  env: null, background: null,
  pickables: [],       // meshes a ray may hit (parts)
  bbox: new THREE.Box3(),
  // view settings — browser state, never written to the job
  display: "edges",    // edges | shaded | xray
  walls: "auto",       // auto | all | none
  ceiling: false,
  labels: true,
  layers: null,        // null = all; else a Set of layer names shown solid
  isolate: null,       // one item number, or null
  hidden: new Set(),   // numbers hidden in 3D (the item list's eye)
  frontsOpen: false,
  runners: true,       // drawer runners drawn (the Runners toggle)
  ao: true,            // ambient occlusion (the AO toggle); never under X-ray
  // the drawing grid, per display mode (the Grid toggle flips the one in
  // force): a drawing's by default, so on with edges and in X-ray, off in Shaded
  gridOn: {edges: true, xray: true, shaded: false},
  clearances: false,
  sel: null,           // selected cabinet number
  hover: null,         // {number, id}
  overlays: null,      // clearance meshes group
  // navigation
  pivotDot: null,
  cube: null,          // the view cube
  labelEls: new Map(),
  press: null,         // where a press started, to tell a click from a drag
  space: false,
  jobKey: null,
  dimLines: null,
  cardEl: null,
  legendEl: null,
  helpEl: null,
  menusEl: null,
  handles: null,       // F6 move handles
};

/* ---------- small helpers ---------------------------------------------------- */

function say(text) {
  if (!V.note) return;
  V.note.textContent = text || "";
  V.note.hidden = !text;
}

function status(text) {
  if (V.els.status) V.els.status.textContent = text || "";
}

function h(tag, attrs, children) {
  const el = document.createElement(tag);
  for (const k in (attrs || {})) {
    if (k === "class") el.className = attrs[k];
    else if (k === "text") el.textContent = attrs[k];
    else if (k === "html") el.innerHTML = attrs[k];
    else if (k.startsWith("on")) el.addEventListener(k.slice(2), attrs[k]);
    else el.setAttribute(k, attrs[k]);
  }
  (children || []).forEach((c) => c && el.appendChild(c));
  return el;
}

function hex(s) {
  // a look's colour is a hex string off the server; three wants a number
  return parseInt(String(s || PAPER.fallback).replace("#", ""), 16);
}

function webglAvailable() {
  try {
    const c = document.createElement("canvas");
    return !!(window.WebGLRenderingContext &&
              (c.getContext("webgl2") || c.getContext("webgl")));
  } catch (e) {
    return false;
  }
}

/* ---------- room frame and render frame -----------------------------------------
   room.py's world is X right, Y INTO the room from wall A, Z up, and its plan
   maps onto SVG with no flip — which, with Z up, is a LEFT-handed frame: facing
   wall A from inside the room, the wall's own x runs to your right on the
   elevation, and that is the real room. Drawn as it stands in a right-handed
   renderer the room would come out as its mirror image, hinge sides included.
   So every solid lives under `V.root`, which negates Y, and this is the ONE
   place the two frames meet: `toRender` / `toRoom` for a point or a vector.
   Geometry is never touched; the server's numbers go in as they are.       */

function toRender(x, y, z) { return new THREE.Vector3(x, -y, z); }
function toRoom(v) { return [v.x, -v.y, v.z]; }

/* ---------- renderer, cameras, controls -------------------------------------- */

function makeRenderer() {
  const r = new THREE.WebGLRenderer({antialias: true, alpha: false,
                                     powerPreference: "high-performance"});
  r.setPixelRatio(Math.min(window.devicePixelRatio || 1, PIXEL_RATIO_CAP));
  r.setClearColor(PAPER.bgBottom, 1);
  r.outputColorSpace = THREE.SRGBColorSpace;
  // Physically based light needs a tone map; Neutral (Khronos PBR Neutral)
  // compresses the top without tinting, so a board's hue is its hue.
  r.toneMapping = THREE.NeutralToneMapping;
  r.toneMappingExposure = LOOK.exposure;
  // shadows off the key light (Round 2). The map is drawn when the scene or
  // the light changes (`shadowsDirty`), never per frame while orbiting.
  r.shadowMap.enabled = true;
  r.shadowMap.type = THREE.PCFShadowMap;
  r.shadowMap.autoUpdate = false;
  r.shadowMap.needsUpdate = true;
  const canvas = r.domElement;
  canvas.tabIndex = 0;                                   // shortcuts need focus
  canvas.addEventListener("webglcontextlost", (e) => {
    e.preventDefault();
    V.lost = true;
    stopLoop();
    say("The 3D view lost its graphics context — waiting for it to come back.");
  }, false);
  canvas.addEventListener("webglcontextrestored", () => {
    V.lost = false;
    say("");
    // three re-uploads what it holds; what it does not, we rebuild
    rebuildAll();
    requestRender();
  }, false);
  return r;
}

function makeCameras(aspect) {
  const persp = new THREE.PerspectiveCamera(45, aspect, 10, 100000);
  const half = 2500;
  const ortho = new THREE.OrthographicCamera(-half, half, half / aspect, -half / aspect,
                                             -100000, 100000);
  persp.up.set(0, 0, 1);
  ortho.up.set(0, 0, 1);
  return {persp, ortho};
}

function makeControls(camera, dom, orthographic) {
  const c = new CameraControls(camera, dom);
  // The ruled mouse scheme: left-drag orbits, right- or middle-drag pans, the
  // wheel and a pinch zoom towards the cursor, Shift+left-drag pans too.
  c.mouseButtons.left = CameraControls.ACTION.ROTATE;
  c.mouseButtons.middle = CameraControls.ACTION.TRUCK;
  c.mouseButtons.right = CameraControls.ACTION.TRUCK;
  // the wheel is handled here, not by camera-controls: see `onWheel`
  c.mouseButtons.wheel = CameraControls.ACTION.NONE;
  c.mouseButtons.shiftLeft = CameraControls.ACTION.TRUCK;
  c.touches.one = CameraControls.ACTION.TOUCH_ROTATE;
  c.touches.two = orthographic ? CameraControls.ACTION.TOUCH_ZOOM_TRUCK
                               : CameraControls.ACTION.TOUCH_DOLLY_TRUCK;
  c.dollyToCursor = true;
  c.infinityDolly = false;
  c.minDistance = 60;
  c.maxDistance = 80000;
  c.minZoom = 0.05;
  c.maxZoom = 40;
  // No roll, and the camera may go a little below the floor (looking up under
  // a wall unit is useful) but never over the pole.
  c.minPolarAngle = 0.02;
  c.maxPolarAngle = Math.PI / 2 + 0.35;
  c.smoothTime = 0.16;
  c.draggingSmoothTime = 0.06;
  c.dollySpeed = 1.0;
  c.truckSpeed = 2.0;
  c.addEventListener("wake", startLoop);
  c.addEventListener("transitionstart", startLoop);
  c.addEventListener("controlstart", () => { startLoop(); showPivot(true); });
  c.addEventListener("controlend", () => { showPivot(false); });
  c.enabled = !orthographic;
  return c;
}

/* ---------- render on demand, never in a loop -------------------------------- */

// One frame, as the viewport shows it: the scene, then the ambient occlusion
// over it. `render`, the snapshot and the pixel read all come through here,
// so a snapshot carries what is on screen.
//
// The occlusion is multiplied over everything on screen, and in a 3 mm gap
// between two fronts it is dark and a pixel wide: a front's line drawn under
// it came out dashed on a dark board. So every paper line is on its own layer
// (`paper`), and with AO on the lines are drawn AFTER the occlusion, against
// the depth the boards left: a line is as written whether AO is on or off.
function draw() {
  const cam = V.camera;
  if (!aoActive()) {
    cam.layers.enableAll();
    V.renderer.render(V.scene, cam);
    return;
  }
  cam.layers.set(0);
  V.renderer.render(V.scene, cam);
  drawAO();
  const background = V.scene.background, clear = V.renderer.autoClear;
  V.scene.background = null;
  V.renderer.autoClear = false;
  cam.layers.set(LINES);
  V.renderer.setRenderTarget(null);
  V.renderer.render(V.scene, cam);
  V.renderer.autoClear = clear;
  V.scene.background = background;
  cam.layers.enableAll();
}

function paper(line) {
  line.layers.set(LINES);
  return line;
}

function render() {
  if (!V.renderer || !V.visible || V.lost) return;
  draw();
  placeLabels();
  if (V.cube) V.cube.render();
}

let renderQueued = false;
function requestRender() {
  if (renderQueued || !V.visible) return;
  renderQueued = true;
  requestAnimationFrame(() => { renderQueued = false; render(); });
}

// A loop runs only while something moves — a gesture, a fly-to, a door
// animation — and stops itself a few frames after the last movement. It is
// started by the INPUT (a press, a wheel, a key, a programmatic view change),
// never by camera-controls' own `wake`: that event is only raised from inside
// `update()`, which is exactly what is not running between gestures.
function tick() {
  if (!V.running) return;
  const dt = V.clock.getDelta();
  const moved = V.controls.update(dt);
  if (moved || V.animating) render();
  if (V.animating) V.animating();       // door/drawer animation step (F5)
  // `controls.active` is deliberately not consulted: at a clamped angle it
  // never rests, and a loop that never stops is the fan running.
  const busy = moved || V.animating || V.pressed;
  V.idleFrames = busy ? 0 : V.idleFrames + 1;
  if (V.idleFrames > 6) { V.running = false; return; }
  requestAnimationFrame(tick);
}

function startLoop() {
  V.idleFrames = 0;
  if (V.running || !V.visible) return;
  V.running = true;
  V.clock.getDelta();
  requestAnimationFrame(tick);
}

function stopLoop() {
  if (V.animating) return;              // an animation keeps the loop alive
  V.running = false;
}

function resize() {
  if (!V.renderer || !V.els.view) return;
  const w = Math.max(V.els.view.clientWidth, 1);
  const hh = Math.max(V.els.view.clientHeight, 1);
  V.renderer.setSize(w, hh, false);
  const aspect = w / hh;
  V.persp.aspect = aspect;
  V.persp.updateProjectionMatrix();
  const half = (V.ortho.right - V.ortho.left) / 2;
  V.ortho.top = half / aspect;
  V.ortho.bottom = -half / aspect;
  V.ortho.updateProjectionMatrix();
  for (const m of V.materials.values()) if (m.userData.outline) m.resolution.set(w, hh);
  sizeAO();
  requestRender();
}

/* ---------- lights and grid ------------------------------------------------- */

// The diffuse light and the reflections come from a neutral image-based
// environment, pre-filtered once through a PMREMGenerator: a plain grey room
// — a box whose ceiling, walls and floor are the radiances in LOOK.sky, the
// four walls alike — so a front reads the same whichever wall it stands on.
// (three's own RoomEnvironment was measured first, on 29 September 2026: a
// studio set with one bright side, 3.9 : 1.0 : 0.9 : 1.3 across the four
// horizontal directions, so a cabinet's colour would have depended on its
// wall; it is not used.) Turned so the box's ceiling is our +Z; one
// directional key light gives the form. No hemisphere light any more.
function makeEnvironment(renderer, scene) {
  const pmrem = new THREE.PMREMGenerator(renderer);
  const room = new THREE.Scene();
  const faces = [LOOK.sky.wall, LOOK.sky.wall, LOOK.sky.ceiling, LOOK.sky.floor,   // +x -x +y -y
                 LOOK.sky.wall, LOOK.sky.wall];                                      // +z -z
  const mats = faces.map((v) => {
    const m = new THREE.MeshBasicMaterial({side: THREE.BackSide});
    m.color.setRGB(v, v, v, THREE.LinearSRGBColorSpace);   // a radiance, not a paper colour
    return m;
  });
  const box = new THREE.Mesh(new THREE.BoxGeometry(10, 10, 10), mats);
  room.add(box);
  const env = pmrem.fromScene(room, 0.1).texture;
  box.geometry.dispose();
  mats.forEach((m) => m.dispose());
  pmrem.dispose();
  scene.environment = env;
  scene.environmentIntensity = LOOK.environment;
  // the box's up is +Y; ours is +Z (measured: this turn puts the ceiling over the tops)
  scene.environmentRotation.set(Math.PI / 2, 0, 0);
  return env;
}

function makeLights() {
  const g = new THREE.Group();
  const key = new THREE.DirectionalLight(PAPER.white, LOOK.key);
  key.position.set(-0.5, -0.8, 1.0);
  key.castShadow = true;
  key.shadow.mapSize.set(LOOK.shadow.size, LOOK.shadow.size);
  key.shadow.radius = LOOK.shadow.radius;
  key.shadow.bias = LOOK.shadow.bias;
  key.shadow.normalBias = LOOK.shadow.normalBias;
  key.shadow.intensity = LOOK.shadow.strength;
  V.key = key;
  g.add(key, key.target);
  return g;
}

// Which way the key comes from, in the room frame on the floor: the side the
// fronts FACE. Every wall carrying something counts once — not by how much
// stands on it, so the fronts of an L's two runs take the same light and read
// the same — and a room with runs all round, or no room (the Run, and the
// Cabinets tab's one cabinet, whose fronts face +y), takes +y turned a little
// to the right.
function keyHeading() {
  const room = V.payload && V.payload.room;
  let x = 0, y = 0;
  if (room) {
    for (const w of room.walls) {
      if (!V.payload.items.some((it) => it.wall === w.id && it.placed)) continue;
      x += w.normal[0];
      y += w.normal[1];
    }
  }
  const len = Math.hypot(x, y);
  if (len > 0.2) {
    // how squarely the best-lit fronts face it: 1 on one wall, 0.707 on an L
    let facing = 0;
    for (const w of room.walls) {
      if (!V.payload.items.some((it) => it.wall === w.id && it.placed)) continue;
      facing = Math.max(facing, (w.normal[0] * x + w.normal[1] * y) / len);
    }
    return [x / len, y / len, Math.max(facing, 0.5)];
  }
  const t = THREE.MathUtils.degToRad(LOOK.keyFrom.turn);
  return [Math.sin(t), Math.cos(t), Math.cos(t)];
}

// Stand the key over the scene and fit its shadow map to the scene's bounds:
// on every rebuild, never while orbiting.
function fitKey() {
  if (!V.key) return;
  const [hx, hy, facing] = keyHeading();
  const e = THREE.MathUtils.degToRad(LOOK.keyFrom.elevation);
  if (V.keyFront === undefined) V.keyFront = LOOK.key;
  V.key.intensity = V.keyFront / (Math.cos(e) * facing);
  const dir = toRender(hx * Math.cos(e), hy * Math.cos(e), Math.sin(e)).normalize();
  const c = V.bbox.getCenter(new THREE.Vector3());
  const r = Math.max(V.bbox.getSize(new THREE.Vector3()).length() / 2, 500);
  V.key.position.copy(c).add(dir.clone().multiplyScalar(r * 2));
  V.key.target.position.copy(c);
  V.key.target.updateMatrixWorld();
  const cam = V.key.shadow.camera;
  cam.left = -r; cam.right = r; cam.top = r; cam.bottom = -r;
  cam.near = r * 0.5;
  cam.far = r * 3.5;
  cam.updateProjectionMatrix();
  V.keyDir = dir;
  shadowsDirty();
}

function shadowsDirty() {
  if (V.renderer) V.renderer.shadowMap.needsUpdate = true;
}

/* ---------- ambient occlusion -------------------------------------------------
   three's GTAOPass (vendored, r186), behind the AO toggle; off under X-ray.
   It is driven directly, not through an EffectComposer: the pass works its
   occlusion out of its own depth-and-normal drawing of the scene, and the
   result is multiplied over the frame already on screen. A composer would draw
   the scene into a target and tone-map the whole image in its output pass —
   every paper line, the background and the grid with it (`toneMapped: false`
   means nothing there), without the canvas's own antialiasing — so the frame
   with AO on would not be the frame with AO off, darker in the corners.    */

function makeAO() {
  const size = V.renderer.getDrawingBufferSize(new THREE.Vector2());
  const pass = new GTAOPass(V.scene, V.camera, Math.max(1, Math.round(size.x * LOOK.ao.resolution)),
                            Math.max(1, Math.round(size.y * LOOK.ao.resolution)), undefined,
    {radius: LOOK.ao.radius, thickness: LOOK.ao.thickness, scale: LOOK.ao.scale, samples: LOOK.ao.samples,
     distanceExponent: LOOK.ao.distanceExponent, distanceFallOff: LOOK.ao.distanceFallOff});
  pass.updatePdMaterial({depthPhi: LOOK.ao.denoise});
  pass.output = GTAOPass.OUTPUT.Off;            // the occlusion only; the blend is ours (`drawAO`)
  // a wall is one-sided, drawn from inside the room: both sides here, and the
  // walls the camera is behind taken out (`hiddenFromAO`)
  pass.normalMaterial.side = THREE.DoubleSide;
  // only what is solid occludes: the pass's own rule hides points and lines,
  // ours also the fat lines, overlays, handles, ghosts and contact shadows
  const cache = [];
  let background = null;
  pass._overrideVisibility = () => {
    V.scene.traverse((o) => { if (o.visible && hiddenFromAO(o)) { o.visible = false; cache.push(o); } });
    background = V.scene.background;
    V.scene.background = null;
  };
  pass._restoreVisibility = () => {
    for (const o of cache) o.visible = true;
    cache.length = 0;
    V.scene.background = background;
  };
  return pass;
}

const _aoUp = new THREE.Vector3(0, 0, -1);
function hiddenFromAO(o) {
  if (o.isLine || o.isPoints || o.isLineSegments2 || o.userData.noAO) return true;
  if (!o.isMesh) return false;
  if (o.userData.ghost || o.userData.overlay) return true;
  const kind = o.userData.kind;
  if ((kind === "wall" && V.walls !== "all") || kind === "ceiling") {
    // drawn only from inside the room: behind it, it is not in the frame
    const n = kind === "wall" ? o.userData.inward : _aoUp;
    if (!n) return false;
    if (V.ortho_on) return V.camera.getWorldDirection(new THREE.Vector3()).dot(n) > 0;
    return V.camera.position.clone().sub(o.userData.at).dot(n) < 0;
  }
  return false;
}

function softwareRendered() {
  try {
    const gl = V.renderer.getContext();
    const ext = gl.getExtension("WEBGL_debug_renderer_info");
    const name = String(ext ? gl.getParameter(ext.UNMASKED_RENDERER_WEBGL) : gl.getParameter(gl.RENDERER));
    return /swiftshader|llvmpipe|software|basic render/i.test(name);
  } catch (err) {
    return false;
  }
}

function aoActive() {
  return !!(V.ao && V.aoPass && V.display !== "xray");
}

function sizeAO() {
  if (!V.aoPass) return;
  const size = V.renderer.getDrawingBufferSize(new THREE.Vector2());
  V.aoPass.setSize(Math.max(1, Math.round(size.x * LOOK.ao.resolution)),
                   Math.max(1, Math.round(size.y * LOOK.ao.resolution)));
}

function drawAO() {
  const p = V.aoPass;
  if (p.camera !== V.camera) {
    p.camera = V.camera;
    p.gtaoMaterial.defines.PERSPECTIVE_CAMERA = V.camera.isPerspectiveCamera ? 1 : 0;
    p.gtaoMaterial.needsUpdate = true;
  }
  p.render(V.renderer, null, null);
  // The pass denoises once, which turns the occlusion's dither into grain; on
  // pale boards that grain shows. So it is denoised again, to and fro between
  // the pass's two targets, each time on another channel of its noise.
  let from = p.pdRenderTarget, to = p.gtaoRenderTarget;
  const pd = p.pdMaterial.uniforms;
  const passes = V.aoPasses !== undefined ? V.aoPasses : LOOK.ao.passes;
  for (let i = 1; i < passes; i++) {
    pd.tDiffuse.value = from.texture;
    pd.index.value = i;
    p._renderPass(V.renderer, p.pdMaterial, to, PAPER.white, 1.0);
    [from, to] = [to, from];
  }
  pd.tDiffuse.value = p.gtaoRenderTarget.texture;
  pd.index.value = 0;
  p.blendMaterial.uniforms.intensity.value = LOOK.ao.intensity;
  p.blendMaterial.uniforms.tDiffuse.value = from.texture;
  p._renderPass(V.renderer, p.blendMaterial, null);      // multiplied over the frame on screen
}

// The background: a slight gradient, PAPER.bgTop over PAPER.bgBottom, as a
// 1 x 64 canvas the renderer draws as a full-screen plane. Tagged sRGB so it
// is neither tone mapped nor converted: the two colours land as they are.
function makeBackground() {
  const c = document.createElement("canvas");
  c.width = 1;
  c.height = 64;
  const g = c.getContext("2d");
  const grad = g.createLinearGradient(0, 0, 0, 64);
  grad.addColorStop(0, "#" + PAPER.bgTop.toString(16).padStart(6, "0"));
  grad.addColorStop(1, "#" + PAPER.bgBottom.toString(16).padStart(6, "0"));
  g.fillStyle = grad;
  g.fillRect(0, 0, 1, 64);
  const tex = new THREE.CanvasTexture(c);
  tex.colorSpace = THREE.SRGBColorSpace;
  tex.minFilter = THREE.LinearFilter;
  tex.magFilter = THREE.LinearFilter;
  tex.generateMipmaps = false;
  return tex;
}

function makeGrid(size) {
  // A subtle floor grid, 100 mm minor and 1000 mm major, on the XY plane
  // (three's GridHelper lies in XZ, so it is turned onto the floor).
  const g = new THREE.Group();
  const s = Math.ceil(size / 1000) * 1000;
  const minor = new THREE.GridHelper(s, s / 100, PAPER.gridMinor, PAPER.gridMinor);
  const major = new THREE.GridHelper(s, s / 1000, PAPER.gridMajor, PAPER.gridMajor);
  for (const gh of [minor, major]) {
    gh.rotation.x = Math.PI / 2;
    gh.material.transparent = true;
    gh.material.opacity = gh === major ? LOOK.grid.major : LOOK.grid.minor;
    gh.material.depthWrite = false;
    gh.material.toneMapped = false;
    g.add(gh);
  }
  g.position.z = -1;
  return g;
}

/* ---------- looks: materials and textures ------------------------------------
   One material per board, shared by every part cut from it (the brief's rule
   2), in three variants — solid, ghost, x-ray — so a part changes its look by
   being handed another shared material, never by having one mutated. A
   board's picture is loaded ONCE per board and turned onto each part's grain
   through a clone that shares the image. Everything lives in V.materials /
   V.pictures / V.textures and is dropped when its board leaves the job.   */

function variantOf(mat, variant) {
  if (variant === "xray") { mat.transparent = true; mat.opacity = XRAY; mat.depthWrite = false; }
  else if (variant === "ghost") { mat.transparent = true; mat.opacity = GHOST; mat.depthWrite = true; }
  else { mat.transparent = false; mat.opacity = 1; mat.depthWrite = true; }
  mat.userData.shared = true;             // never disposed with a mesh
  return mat;
}

function cachedMaterial(key, make) {
  let m = V.materials.get(key);
  if (!m) { m = make(); V.materials.set(key, m); }
  return m;
}

// The picture of a board, fetched once; its rotated variants come off
// `pictureFor`. Until it lands the part keeps its colour, and if it never
// lands (no file, a bad file) the colour is what stays: nothing goes black.
function loadPicture(board) {
  let rec = V.pictures.get(board);
  if (rec) return rec;
  const look = V.payload.looks[board];
  rec = {tex: null, failed: false, picture: look.picture || ""};
  V.pictures.set(board, rec);
  new THREE.TextureLoader().load(look.picture, (loaded) => {
    const tex = squareTile(loaded);
    tex.wrapS = tex.wrapT = THREE.RepeatWrapping;
    tex.colorSpace = THREE.SRGBColorSpace;
    const tile = look.tile_mm || 160;
    tex.repeat.set(1 / tile, 1 / tile);
    tex.anisotropy = V.renderer ? V.renderer.capabilities.getMaxAnisotropy() : 1;
    rec.tex = tex;
    applyPictures(board);
    requestRender();
  }, undefined, () => { rec.failed = true; });
  return rec;
}

// The tile the elevation draws (Round 2, 29 September 2026): its <pattern> is a
// SQUARE holding the picture `xMidYMid slice` — scaled evenly until it covers
// the square, the overhang cropped equally off both sides — and the 3D must
// tile the same thing. Handing three the picture as it is stretched a
// 1135 x 953 picture into the square, 19 % narrower across the grain than
// the elevation draws it. So the middle square is cut out once, here, and
// that is what is tiled at `tile_mm`.
function squareTile(loaded) {
  const img = loaded.image;
  const w = img.naturalWidth || img.width, hh = img.naturalHeight || img.height;
  const side = Math.min(w, hh);
  if (!side || w === hh) return loaded;
  const c = document.createElement("canvas");
  c.width = c.height = side;
  c.getContext("2d").drawImage(img, (w - side) / 2, (hh - side) / 2, side, side, 0, 0, side, side);
  loaded.dispose();
  return new THREE.CanvasTexture(c);
}

// The board's picture turned by `rot` radians, one Texture per (board, rot),
// sharing the loaded image with every other rotation of it.
function pictureFor(board, rot) {
  const rec = V.pictures.get(board);
  if (!rec || !rec.tex) return null;
  const key = board + ":" + Math.round(rot * 1000);
  let tex = V.textures.get(key);
  if (!tex) {
    tex = rec.tex.clone();
    tex.rotation = rot;
    tex.needsUpdate = true;
    V.textures.set(key, tex);
  }
  return tex;
}

// A picture has landed: hand it to every material of that board waiting for it.
function applyPictures(board) {
  for (const m of V.materials.values()) {
    if (m.userData.board !== board || m.userData.rot === undefined || m.map) continue;
    m.map = pictureFor(board, m.userData.rot);
    showPicture(m);
    m.needsUpdate = true;
  }
}

// A material's base colour MULTIPLIES its map, so a board drawn in its picture
// takes white: the picture is then the colour, as it is in the elevation. With
// the board's swatch left in (BROOKHILL's fallback, a tan) the pale oak came
// out orange-brown (Round 2, 29 September 2026). No picture, not landed yet,
// or failed: the swatch, as before.
function showPicture(m) {
  if (m.map) m.color.set(PAPER.white);
  else m.color.set(hex(m.userData.colour));
}

function boardParams(look) {
  return {color: hex(look.colour), roughness: LOOK.board.roughness, metalness: LOOK.board.metalness,
          clearcoat: LOOK.board.clearcoat, clearcoatRoughness: LOOK.board.clearcoatRoughness};
}

// The shared material for one face set of one board: `rot` is the picture's
// turn (undefined = no picture on this board), `front` pulls it towards the
// camera with a polygon offset (fronts sit exactly on the carcass face and
// coplanar faces flicker; never a move).
function boardMaterial(board, rot, front, variant) {
  const key = ["board", board, rot === undefined ? "-" : Math.round(rot * 1000), front ? "f" : "", variant].join("|");
  return cachedMaterial(key, () => {
    const look = V.payload.looks[board] || {colour: PAPER.fallback, grain: false, picture: ""};
    const m = new THREE.MeshPhysicalMaterial(boardParams(look));
    m.userData.board = board;
    m.userData.look = lookKey(look);
    m.userData.colour = look.colour;
    if (rot !== undefined) {
      m.userData.rot = rot;
      m.map = pictureFor(board, rot);       // null until the picture lands; applyPictures fills it
      showPicture(m);
    }
    if (front) { m.polygonOffset = true; m.polygonOffsetFactor = -1; m.polygonOffsetUnits = -2; }
    return variantOf(m, variant);
  });
}

function tapeMaterial(board, variant) {
  return cachedMaterial(["tape", board, variant].join("|"), () => {
    const look = V.payload.looks[board] || {colour: PAPER.fallback};
    const m = new THREE.MeshPhysicalMaterial({color: hex(look.colour), roughness: LOOK.tape.roughness,
      metalness: LOOK.tape.metalness, clearcoat: LOOK.tape.clearcoat,
      clearcoatRoughness: LOOK.tape.clearcoatRoughness,
      polygonOffset: true, polygonOffsetFactor: -2, polygonOffsetUnits: -4});
    m.userData.board = board;
    m.userData.look = lookKey(look);
    return variantOf(m, variant);
  });
}

// hardware: one grey, no board, no picture (Part 6, 28 September 2026); the
// inner member a lighter tone than the outer channel (29 Sept 2026)
function runnerMaterial(role, variant) {
  return cachedMaterial(["runner", role, variant].join("|"), () => {
    const m = new THREE.MeshStandardMaterial({
      color: role === "runner_inner" ? PAPER.runnerInner : PAPER.runner,
      roughness: LOOK.runner.roughness, metalness: LOOK.runner.metalness});
    return variantOf(m, variant);
  });
}

// The two materials a part needs, as a function of the variant: one for its
// caps (the faces in the plan plane), one for its side walls. ExtrudeGeometry
// lays the caps' UV in world XY and the walls' V up the extrusion, so the
// picture's vertical (its grain) is turned onto the part's `grain` vector: 0
// or 90 degrees, as the elevation does it, never an angle worked out here
// from a photograph.
function materialsFor(part) {
  if (isRunner(part)) {
    return (variant) => { const m = runnerMaterial(part.role, variant); return [m, m]; };
  }
  const look = V.payload.looks[part.board] || {colour: PAPER.fallback, grain: false, picture: ""};
  const front = part.role === "door" || part.role === "drawer" || part.role === "blind" || part.role === "panel";
  let capRot, sideRot;
  if (look.picture && part.grain) {
    loadPicture(part.board);
    const [gx, gy, gz] = part.grain;
    const horizontal = Math.abs(gz) < 0.5 && (gx || gy);
    // caps: lay the picture's V along the plan grain vector
    capRot = horizontal ? Math.atan2(gy, gx) - Math.PI / 2 : 0;
    // walls: V runs up; a horizontal grain turns the tile on its side
    sideRot = horizontal ? Math.PI / 2 : 0;
  }
  return (variant) => [boardMaterial(part.board, capRot, front, variant),
                       boardMaterial(part.board, sideRot, front, variant)];
}

// A board's look as the server last sent it: a shared material remembers the
// one it was built from, so a change is seen (`refreshLooks`).
function lookKey(look) {
  return JSON.stringify([look.colour, look.picture || "", look.tile_mm || 160]);
}

function refreshLooks(looks) {
  const stale = new Set();
  for (const m of V.materials.values()) {
    const b = m.userData.board;
    if (b === undefined || !looks[b] || m.userData.look === lookKey(looks[b])) continue;
    stale.add(b);
  }
  for (const b of stale) {
    const look = looks[b];
    const rec = V.pictures.get(b);
    const pictureChanged = !rec || rec.picture !== (look.picture || "");
    if (pictureChanged) {
      for (const [k, tex] of [...V.textures]) if (k.split(":")[0] === b) { tex.dispose(); V.textures.delete(k); }
      if (rec && rec.tex) rec.tex.dispose();
      V.pictures.delete(b);
    }
    for (const m of V.materials.values()) {
      if (m.userData.board !== b) continue;
      m.color.set(hex(look.colour));
      m.userData.look = lookKey(look);
      if (pictureChanged) {
        m.map = null;
        if (m.userData.rot !== undefined && look.picture) { loadPicture(b); m.map = pictureFor(b, m.userData.rot); }
      }
      if (m.userData.colour !== undefined) { m.userData.colour = look.colour; showPicture(m); }
      m.needsUpdate = true;
    }
  }
}

// Drop the shared materials, pictures and textures of boards the job no
// longer carries (and, with `all`, everything).
function dropLooks(keep, all) {
  for (const [k, m] of [...V.materials]) {
    const board = m.userData.board;
    if (all || (board !== undefined && !keep[board])) { m.dispose(); V.materials.delete(k); }
  }
  for (const [k, tex] of [...V.textures]) {
    if (all || !keep[k.split(":")[0]]) { tex.dispose(); V.textures.delete(k); }
  }
  for (const [b, rec] of [...V.pictures]) {
    if (all || !keep[b]) { if (rec.tex) rec.tex.dispose(); V.pictures.delete(b); }
  }
}

// What a mesh is drawn with: the variant of its shared materials, and its
// thin edges shown or not — in Shaded + edges only where faces meet at an
// angle (EdgesGeometry's threshold, LOOK.edge.angle) and quieter
// (LOOK.edge.opacity); X-ray as it always was. A front's perimeter is drawn
// in every mode (`isFront`). The selection outline is
// separate (`outlineMesh`) and is not touched here.
function applyDisplay(mesh) {
  const xray = V.display === "xray";
  const variant = xray ? "xray" : (mesh.userData.ghost ? "ghost" : "solid");
  if (mesh.userData.mats) mesh.material = mesh.userData.mats(variant);
  // every board casts and receives; a ghost and an x-ray casts nothing, and a
  // band (inside its part's size) leaves the casting to its part
  mesh.castShadow = variant === "solid" && !mesh.userData.tape;
  mesh.receiveShadow = !xray;
  const edges = mesh.userData.edges;
  if (edges) {
    if (edges.userData.front) {
      edges.visible = true;
      edges.material = frontLineMaterial(mesh.userData.ghost ? "ghost" : "solid");
    } else {
      edges.visible = V.display !== "shaded";
      edges.material.opacity = (xray ? 1 : LOOK.edge.opacity) * (mesh.userData.ghost ? GHOST : 1);
      edges.material.transparent = true;
    }
  }
  if (mesh.userData.outline) mesh.userData.outline.material = outlineMaterial(mesh.userData.outlineKind, mesh.userData.ghost);
}

/* ---------- building parts ---------------------------------------------------- */

function extrude(outline, z0, z1) {
  const shape = new THREE.Shape(outline.map(([x, y]) => new THREE.Vector2(x, y)));
  const g = new THREE.ExtrudeGeometry(shape, {depth: Math.max(z1 - z0, 0.5), bevelEnabled: false,
                                              curveSegments: 1});
  g.translate(0, 0, z0);
  g.computeBoundingBox();
  return g;
}

// A FRONT — a door leaf, a drawer face, a blind corner's flush panel (Round 2,
// 29 September 2026). Its perimeter is what makes a run read as doors: the
// 3 mm gaps between neighbours are a pixel or less at the Home zoom, so each
// front draws every one of its own edges as a thin line at PAPER.edgeFront,
// at full strength and in Shaded as well as Shaded + edges. Carcass and
// interior parts keep the angle threshold and the quieter line.
//
// Drawn as FAT lines (three's LineSegments2, as the selection outline is), not
// GL lines: a front's material is pulled towards the camera by a polygon
// offset (it sits exactly on the carcass face), and a GL line takes no
// offset, so a thin line on a front's own face lost the depth test to the
// face it outlines and came out broken and faint. A fat line is triangles and
// takes an offset of its own.
function isFront(part) {
  return part.role === "door" || part.role === "drawer" || part.role === "blind";
}

function frontLineMaterial(variant) {
  return cachedMaterial(["frontline", variant].join("|"), () => {
    const m = new LineMaterial({
      color: PAPER.edgeFront, linewidth: LOOK.front.width, transparent: true,
      opacity: variant === "ghost" ? LOOK.front.opacity * GHOST : LOOK.front.opacity,
      toneMapped: false, depthWrite: false, side: THREE.DoubleSide,
      polygonOffset: true, polygonOffsetFactor: -3, polygonOffsetUnits: -8});
    m.userData.shared = true;
    m.userData.outline = true;                 // `resize` keeps its resolution
    if (V.els.view) m.resolution.set(Math.max(V.els.view.clientWidth, 1), Math.max(V.els.view.clientHeight, 1));
    return m;
  });
}

function edgeColourFor(role) {
  if (role === "door" || role === "drawer" || role === "blind" || role === "panel") return PAPER.edgeFront;
  return PAPER.edgeCarcass;
}

function buildPart(part) {
  const geom = extrude(part.outline, part.z0, part.z1);
  const mats = materialsFor(part);
  const mesh = new THREE.Mesh(geom, mats("solid"));
  mesh.userData = {part: part, number: part.cab, id: part.id, ghost: false, mats: mats};
  const front = isFront(part);
  let edges;
  if (front) {
    const eg = new THREE.EdgesGeometry(geom, LOOK.front.angle);
    edges = new LineSegments2(new LineSegmentsGeometry().fromEdgesGeometry(eg), frontLineMaterial("solid"));
    eg.dispose();
    edges.renderOrder = 1;
  } else {
    edges = new THREE.LineSegments(
      new THREE.EdgesGeometry(geom, LOOK.edge.angle),
      new THREE.LineBasicMaterial({color: edgeColourFor(part.role), transparent: true,
                                   opacity: LOOK.edge.opacity, toneMapped: false}));
  }
  edges.userData.base = edgeColourFor(part.role);
  edges.userData.front = front;
  paper(edges);
  mesh.add(edges);
  mesh.userData.edges = edges;
  // a door rotates about its hinge, a drawer face slides out: keep the rest
  // position so an animation can come back to it
  mesh.userData.rest = {position: mesh.position.clone(), quaternion: mesh.quaternion.clone()};
  if (isRunner(part)) mesh.visible = V.runners;
  applyDisplay(mesh);
  return mesh;
}

// A runner part: its outer channel or its inner member (R3, 29 September 2026).
function isRunner(part) {
  return part.role === "runner_outer" || part.role === "runner_inner";
}

// The Runners toggle: both members shown or not, every cabinet at once.
function applyRunners() {
  for (const grp of V.groups.values()) {
    for (const m of grp.children) {
      if (m.userData.part && isRunner(m.userData.part)) m.visible = V.runners;
    }
  }
  shadowsDirty();
  requestRender();
}

function disposeObject(obj) {
  obj.traverse((o) => {
    if (o.geometry) o.geometry.dispose();
    if (o.material) {
      const mats = Array.isArray(o.material) ? o.material : [o.material];
      // a board's materials and textures are shared and live in the cache
      // (dropLooks); only a mesh's own — edges, overlays, the shell — go
      mats.forEach((m) => { if (!m.userData.shared) m.dispose(); });
    }
  });
}

// A banded edge: a thin box INSIDE the part's finished size on that face, in
// the edging board's colour (27 September 2026). The server says where — the
// band is a solid like any other — and this only draws it. It picks and tints
// as its part: its userData.part is the part it belongs to. Coplanar with the
// part's face, so a polygon offset pulls it forward, never a move.
function buildTape(band, part) {
  const geom = extrude(band.outline, band.z0, band.z1);
  // two groups (caps, walls), so two entries — the same material twice; one
  // entry left the walls' group with no material, which three's raycaster
  // reads as `material.side` of undefined when a pick lands on a band
  const mats = (variant) => { const m = tapeMaterial(band.board, variant); return [m, m]; };
  const mesh = new THREE.Mesh(geom, mats("solid"));
  mesh.userData = {part: part, number: part.cab, id: part.id, ghost: false, tape: band, mats: mats};
  mesh.userData.rest = {position: mesh.position.clone(), quaternion: mesh.quaternion.clone()};
  applyDisplay(mesh);
  return mesh;
}

function buildItem(item) {
  const grp = new THREE.Group();
  grp.userData = {number: item.number, hash: item.hash, item: item};
  for (const part of item.parts) {
    grp.add(buildPart(part));
    for (const band of part.tapes || []) grp.add(buildTape(band, part));
  }
  return grp;
}

// Rebuild only the cabinets whose hash changed; dispose what they replace.
function syncItems(payload) {
  const seen = new Set();
  for (const item of payload.items) {
    seen.add(item.number);
    const old = V.groups.get(item.number);
    if (old && old.userData.hash === item.hash) { old.userData.item = item; continue; }
    if (old) { V.root.remove(old); disposeObject(old); V.groups.delete(item.number); }
    if (!item.parts.length) continue;
    const grp = buildItem(item);
    V.root.add(grp);
    V.groups.set(item.number, grp);
  }
  for (const [n, grp] of [...V.groups]) {
    if (!seen.has(n)) { V.root.remove(grp); disposeObject(grp); V.groups.delete(n); }
  }
  // plinths and fillers: few, cheap — rebuilt whenever their list changes
  const key = JSON.stringify(payload.room_parts.map((q) => q.id + q.z1 + q.outline.join(",")));
  if (!V.roomParts || V.roomParts.userData.key !== key) {
    if (V.roomParts) { V.root.remove(V.roomParts); disposeObject(V.roomParts); }
    V.roomParts = new THREE.Group();
    V.roomParts.userData = {key: key, number: 0};
    for (const q of payload.room_parts) V.roomParts.add(buildPart(q));
    V.root.add(V.roomParts);
  }
  // drop the materials, pictures and textures of boards no longer in the job,
  // and bring the shared materials of a board whose look CHANGED up to date
  // in place (a colour or a picture edited on the Boards tab; the parts'
  // hashes do not carry the look, so nothing above rebuilt them)
  dropLooks(payload.looks, false);
  refreshLooks(payload.looks);
  V.pickables = [];
  for (const grp of V.groups.values()) grp.children.forEach((m) => V.pickables.push(m));
  V.roomParts.children.forEach((m) => V.pickables.push(m));
}

/* ---------- the room shell ---------------------------------------------------- */

function wallMesh(w, top, closed) {
  // The wall in its own frame (u along, v up), holes for its openings, then
  // set into the world on the basis (dir, up, -normal): right-handed, so the
  // BACK side is the one facing into the room, and that is the one drawn —
  // a wall between the camera and the room is simply not drawn from outside.
  const shape = new THREE.Shape([new THREE.Vector2(0, 0), new THREE.Vector2(w.length, 0),
                                 new THREE.Vector2(w.length, top), new THREE.Vector2(0, top)]);
  for (const o of w.openings) {
    const u0 = Math.max(o.x, 0), u1 = Math.min(o.x + o.width, w.length);
    const v0 = Math.max(o.sill, 0), v1 = Math.min(o.head, top);
    if (u1 - u0 < 1 || v1 - v0 < 1) continue;
    const hole = new THREE.Path([new THREE.Vector2(u0, v0), new THREE.Vector2(u1, v0),
                                 new THREE.Vector2(u1, v1), new THREE.Vector2(u0, v1)]);
    shape.holes.push(hole);
  }
  const geom = new THREE.ShapeGeometry(shape);
  const mat = new THREE.MeshStandardMaterial({color: PAPER.wall, roughness: LOOK.room.roughness,
                                              metalness: LOOK.room.metalness, side: THREE.BackSide});
  const mesh = new THREE.Mesh(geom, mat);
  const dir = new THREE.Vector3(w.dir[0], w.dir[1], 0);
  const up = new THREE.Vector3(0, 0, 1);
  const nrm = new THREE.Vector3(-w.normal[0], -w.normal[1], 0);
  const m = new THREE.Matrix4().makeBasis(dir, up, nrm);
  m.setPosition(w.start[0], w.start[1], 0);
  mesh.applyMatrix4(m);
  mesh.receiveShadow = true;
  mesh.userData = {wall: w.id, kind: "wall", inward: toRender(w.normal[0], w.normal[1], 0),
                   at: toRender(w.start[0], w.start[1], 0)};
  const edges = paper(new THREE.LineSegments(new THREE.EdgesGeometry(geom, 1),
    new THREE.LineBasicMaterial({color: PAPER.edgeWall, toneMapped: false})));
  edges.applyMatrix4(m);
  mesh.userData.edges = edges;
  return [mesh, edges];
}

function obstructionMeshes(w) {
  const out = [];
  const dir = new THREE.Vector3(w.dir[0], w.dir[1], 0);
  const nrm = new THREE.Vector3(w.normal[0], w.normal[1], 0);
  for (const ob of w.obstructions) {
    const proud = Math.max(ob.proud, 0);
    const box = new THREE.BoxGeometry(ob.width, Math.max(proud, 6), ob.height);
    const mat = new THREE.MeshStandardMaterial({color: PAPER.obstruction, roughness: 0.6,
                                                emissive: PAPER.obstruction, emissiveIntensity: 0.35});
    const mesh = new THREE.Mesh(box, mat);
    // the box's Y is out from the wall: basis (dir, normal, up)
    const m = new THREE.Matrix4().makeBasis(dir, nrm, new THREE.Vector3(0, 0, 1));
    const c = new THREE.Vector3(ob.centre[0], ob.centre[1], ob.z)
      .add(nrm.clone().multiplyScalar(Math.max(proud, 6) / 2));
    m.setPosition(c);
    mesh.applyMatrix4(m);
    mesh.userData = {kind: "obstruction", wall: w.id, ob: ob};
    mesh.renderOrder = 5;
    out.push(mesh);
  }
  return out;
}

function buildShell(payload) {
  if (V.shell) { V.root.remove(V.shell); disposeObject(V.shell); V.shell = null; }
  const shell = new THREE.Group();
  shell.userData.kind = "shell";
  const room = payload.room;
  V.wallMeshes = [];
  V.obstructions = [];
  if (room) {
    // the corner chain; on a closed room its last point repeats the first
    const pts = room.floor.slice();
    const [fx, fy] = pts[0], [lx, ly] = pts[pts.length - 1];
    if (pts.length > 3 && Math.abs(fx - lx) < 1 && Math.abs(fy - ly) < 1) pts.pop();
    const floorShape = new THREE.Shape(pts.map(([x, y]) => new THREE.Vector2(x, y)));
    const floor = new THREE.Mesh(new THREE.ShapeGeometry(floorShape),
      new THREE.MeshStandardMaterial({color: PAPER.floor, roughness: LOOK.room.roughness,
                                      metalness: LOOK.room.metalness}));
    floor.position.z = -0.5;
    floor.userData.kind = "floor";
    floor.receiveShadow = true;
    shell.add(floor);
    const floorEdge = paper(new THREE.LineSegments(new THREE.EdgesGeometry(floor.geometry, 1),
      new THREE.LineBasicMaterial({color: PAPER.edgeWall, toneMapped: false})));
    shell.add(floorEdge);
    for (const w of room.walls) {
      // to ITS height (Wall.height, 2 October 2026): a half wall stops short
      // of the ceiling; the payload carries the ceiling, or the drawing's top,
      // where none is set
      const [mesh, edges] = wallMesh(w, Math.min(w.height || room.top, room.top), room.closed);
      shell.add(mesh, edges);
      V.wallMeshes.push(mesh);
      for (const ob of obstructionMeshes(w)) { shell.add(ob); V.obstructions.push(ob); }
    }
    const ceil = new THREE.Mesh(new THREE.ShapeGeometry(floorShape),
      new THREE.MeshStandardMaterial({color: PAPER.ceiling, roughness: LOOK.room.roughness,
                                      metalness: LOOK.room.metalness, side: THREE.BackSide}));
    ceil.position.z = room.top;
    ceil.userData.kind = "ceiling";
    ceil.userData.at = new THREE.Vector3(0, 0, room.top);
    ceil.visible = V.ceiling;
    V.ceilMesh = ceil;
    shell.add(ceil);
  } else {
    // no room: a plain floor under the Run
    const b = V.bbox;
    const w = Math.max(b.max.x - b.min.x, 1000) + 1200;
    const d = Math.max(b.max.y - b.min.y, 1000) + 1200;
    const floor = new THREE.Mesh(new THREE.PlaneGeometry(w, d),
      new THREE.MeshStandardMaterial({color: PAPER.floor, roughness: LOOK.room.roughness,
                                      metalness: LOOK.room.metalness}));
    floor.position.set((b.max.x + b.min.x) / 2, -(b.max.y + b.min.y) / 2, -0.5);   // room frame, in the root
    floor.userData.kind = "floor";
    floor.receiveShadow = true;
    shell.add(floor);
  }
  V.root.add(shell);
  V.shell = shell;
  buildContacts(payload);
  applyRoomLook();
  applyWalls();
}

// The floor's tiles: one tile and its joint as a picture, repeated every
// LOOK.tile.size mm (a floor's UVs are its plan millimetres).
const TILE_PX = 256;
function tileTexture() {
  if (V.tileTex) return V.tileTex;
  const c = document.createElement("canvas");
  c.width = c.height = TILE_PX;
  const g = c.getContext("2d");
  const css = (n) => "#" + n.toString(16).padStart(6, "0");
  g.fillStyle = css(PAPER.tileJoint);
  g.fillRect(0, 0, TILE_PX, TILE_PX);
  const j = Math.max(1, LOOK.tile.joint / LOOK.tile.size * TILE_PX / 2);
  g.fillStyle = css(PAPER.floorTile);
  g.fillRect(j, j, TILE_PX - 2 * j, TILE_PX - 2 * j);
  const tex = new THREE.CanvasTexture(c);
  tex.colorSpace = THREE.SRGBColorSpace;
  tex.wrapS = tex.wrapT = THREE.RepeatWrapping;
  tex.repeat.set(1 / LOOK.tile.size, 1 / LOOK.tile.size);
  tex.anisotropy = V.renderer.capabilities.getMaxAnisotropy();
  V.tileTex = tex;
  return tex;
}

// The room as a room in the Shaded modes — tiles, plaster, an off-white
// ceiling — and as a drawing in X-ray: the paper floor and walls it had.
function applyRoomLook() {
  if (!V.shell) return;
  const drawn = V.display === "xray";
  for (const m of V.shell.children) {
    const kind = m.userData.kind;
    if (!m.isMesh || !(kind === "floor" || kind === "wall" || kind === "ceiling")) continue;
    if (kind === "floor") {
      m.material.map = drawn ? null : tileTexture();
      m.material.color.set(drawn ? PAPER.floor : PAPER.white);
      // a plane's own UVs run 0..1: a floor with no room is laid in millimetres too
      if (m.geometry.type === "PlaneGeometry" && !m.userData.uvMm) {
        const uv = m.geometry.attributes.uv, p = m.geometry.parameters;
        for (let i = 0; i < uv.count; i++) uv.setXY(i, uv.getX(i) * p.width, uv.getY(i) * p.height);
        uv.needsUpdate = true;
        m.userData.uvMm = true;
      }
    } else if (kind === "wall") m.material.color.set(drawn ? PAPER.wall : PAPER.plaster);
    else m.material.color.set(drawn ? PAPER.ceiling : PAPER.ceilingShaded);
    m.material.needsUpdate = true;
  }
  if (V.grid) V.grid.visible = !!V.gridOn[V.display];
}

// A faint contact shadow under every item standing on the floor, or a leg
// height off it (legs are not drawn, so a base unit hangs 100 mm up and
// without this reads as floating): a soft-edged dark patch on the floor, the
// item's plan extent and LOOK.contact.margin more. Drawing only; the extent is
// read off the outlines the server sent.
const CONTACT_MM = 5;                     // one pixel of a contact shadow's picture, in mm
function contactTexture(w, d, margin) {
  // the footprint, white on nothing, blurred out over the margin around it
  const c = document.createElement("canvas");
  c.width = Math.max(4, Math.round((w + 2 * margin) / CONTACT_MM));
  c.height = Math.max(4, Math.round((d + 2 * margin) / CONTACT_MM));
  const g = c.getContext("2d");
  const m = margin / CONTACT_MM;
  g.filter = `blur(${(m / 2.5).toFixed(1)}px)`;
  g.fillStyle = "#" + PAPER.white.toString(16);
  g.fillRect(m, m, c.width - 2 * m, c.height - 2 * m);
  return new THREE.CanvasTexture(c);
}

function buildContacts(payload) {
  if (V.contacts) {
    V.root.remove(V.contacts);
    V.contacts.children.forEach((m) => { m.geometry.dispose(); m.material.alphaMap.dispose(); m.material.dispose(); });
  }
  const g = new THREE.Group();
  g.userData.noAO = true;
  for (const item of payload.items) {
    if (!item.parts.length) continue;
    // Squared up to the item's own wall (29 September 2026): on a wall at an
    // angle the patch turns with the cabinet instead of spanning its box. On a
    // wall along an axis that is the box, exactly as before.
    const wall = payload.room && item.wall ? payload.room.walls.find((w) => w.id === item.wall) : null;
    const turned = wall && Math.abs(wall.dir[0]) > 1e-6 && Math.abs(wall.dir[1]) > 1e-6;
    const [dx, dy] = turned ? wall.dir : [1, 0];
    let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity, z0 = Infinity;
    for (const p of item.parts) {
      z0 = Math.min(z0, p.z0);
      for (const [px, py] of p.outline) {
        const x = px * dx + py * dy, y = -px * dy + py * dx;    // into the wall's frame
        x0 = Math.min(x0, x); x1 = Math.max(x1, x); y0 = Math.min(y0, y); y1 = Math.max(y1, y);
      }
    }
    if (z0 > LOOK.contact.reach) continue;
    const m = LOOK.contact.margin;
    const mesh = new THREE.Mesh(new THREE.PlaneGeometry(x1 - x0 + 2 * m, y1 - y0 + 2 * m),
      new THREE.MeshBasicMaterial({color: PAPER.contact, alphaMap: contactTexture(x1 - x0, y1 - y0, m), transparent: true,
                                   opacity: LOOK.contact.opacity, depthWrite: false, toneMapped: false,
                                   side: THREE.DoubleSide}));
    const cx = (x0 + x1) / 2, cy = (y0 + y1) / 2;
    mesh.position.set(cx * dx - cy * dy, cx * dy + cy * dx, 0.6);   // room frame, in the root
    if (turned) mesh.rotation.z = Math.atan2(dy, dx);
    mesh.userData = {contact: item.number, noAO: true};
    mesh.renderOrder = 1;
    g.add(mesh);
  }
  V.root.add(g);
  V.contacts = g;
}

function contactOf(number) {
  return V.contacts ? V.contacts.children.find((m) => m.userData.contact === number) : null;
}

function applyWalls() {
  for (const m of (V.wallMeshes || [])) {
    m.visible = V.walls !== "none";
    m.material.side = V.walls === "all" ? THREE.DoubleSide : THREE.BackSide;
    m.material.needsUpdate = true;
    if (m.userData.edges) m.userData.edges.visible = V.walls !== "none";
  }
  if (V.ceilMesh) V.ceilMesh.visible = V.ceiling && V.walls !== "none";
  requestRender();
}

/* ---------- the whole scene from a payload ------------------------------------ */

function computeBBox() {
  const b = new THREE.Box3();
  for (const grp of V.groups.values()) b.expandByObject(grp);
  if (V.roomParts) b.expandByObject(V.roomParts);
  if (V.payload && V.payload.room) {
    for (const [x, y] of V.payload.room.floor) b.expandByPoint(toRender(x, y, 0));
    b.expandByPoint(new THREE.Vector3(b.min.x, b.min.y, V.payload.room.top));
  }
  if (b.isEmpty()) b.set(new THREE.Vector3(-1000, -1000, 0), new THREE.Vector3(1000, 1000, 1000));
  V.bbox = b;
  // near and far follow the scene's size, so depth precision holds on a 6 m
  // room and on a single cabinet
  const size = b.getSize(new THREE.Vector3()).length();
  V.persp.near = Math.max(size / 500, 2);
  V.persp.far = size * 20 + 2000;
  V.persp.updateProjectionMatrix();
  V.ortho.near = -size * 10;
  V.ortho.far = size * 10;
  V.ortho.updateProjectionMatrix();
  if (V.grid) { V.scene.remove(V.grid); disposeObject(V.grid); }
  V.grid = makeGrid(Math.max(size * 1.5, 6000));
  const c = b.getCenter(new THREE.Vector3());
  V.grid.position.set(Math.round(c.x / 1000) * 1000, Math.round(c.y / 1000) * 1000, -1);
  V.grid.visible = !!V.gridOn[V.display];
  V.scene.add(V.grid);
  fitKey();
}

function rebuildAll() {
  if (!V.payload) return;
  for (const [n, grp] of [...V.groups]) { V.root.remove(grp); disposeObject(grp); V.groups.delete(n); }
  if (V.roomParts) { V.root.remove(V.roomParts); disposeObject(V.roomParts); V.roomParts = null; }
  syncItems(V.payload);
  computeBBox();
  buildShell(V.payload);
  applyGhosting();
  buildOverlays();
  updateLegend();
}

/* ---------- ghosting: layers, isolate, hidden --------------------------------- */

function itemShown(item) {
  if (V.isolate !== null) return item.number === V.isolate;
  if (V.layers === null) return true;
  return V.layers.has(item.layer);
}

function applyGhosting() {
  for (const grp of V.groups.values()) {
    const item = grp.userData.item;
    const hiddenHere = V.hidden.has(item.number);
    grp.visible = !hiddenHere;
    const ghost = !itemShown(item);
    const contact = contactOf(item.number);
    if (contact) contact.visible = !hiddenHere && !ghost && V.display !== "xray";
    for (const mesh of grp.children) {
      mesh.userData.ghost = ghost;
      // an isolated view takes pointer events away from everything else,
      // exactly as the plan does; a layer ghosted by the toggle keeps its hover
      mesh.userData.unpickable = ghost && V.isolate !== null;
      applyDisplay(mesh);
    }
  }
  if (V.roomParts) {
    for (const mesh of V.roomParts.children) {
      const ghost = V.isolate !== null || (V.layers !== null && !V.layers.has(mesh.userData.part.layer));
      mesh.userData.ghost = ghost;
      mesh.userData.unpickable = ghost && V.isolate !== null;
      applyDisplay(mesh);
    }
  }
  applySelection();
  updateHandles();
  shadowsDirty();
  requestRender();
}

/* ---------- selection and hover ---------------------------------------------- */

// The selection is an OUTLINE, not a tint (29 September 2026): the additive
// emissive glow that turned a dark board navy is gone. A selected item's
// edges are drawn again as fat lines (three's LineSegments2) in the accent,
// a touch heavier than the thin edges; a hovered item the same in
// PAPER.hover, lighter. The board colour under it does not change. Four
// shared LineMaterials — selected / hover, plain / ghosted — sized in pixels
// off the viewport (`resize` keeps their resolution).
function outlineMaterial(kind, ghost) {
  const key = ["outline", kind, ghost ? "g" : ""].join("|");
  return cachedMaterial(key, () => {
    const m = new LineMaterial({
      color: kind === "sel" ? PAPER.accent : PAPER.hover,
      linewidth: kind === "sel" ? LOOK.outline.selected : LOOK.outline.hover,
      transparent: true, opacity: (kind === "sel" ? 1 : 0.85) * (ghost ? GHOST : 1),
      toneMapped: false, depthWrite: false,
      // the quads are built in clip space by the shader, so their winding is
      // not the mirrored root's: under `V.root` (scale 1, -1, 1) a one-sided
      // fat line is culled entirely — both sides, always
      side: THREE.DoubleSide,
      // a fat line is a screen-space quad straddling the edge, half of it over
      // the face that recedes from it: a polygon offset keeps that half in
      // front of the face (thin GL lines win the tie on their own)
      polygonOffset: true, polygonOffsetFactor: -4, polygonOffsetUnits: -12});
    m.userData.shared = true;
    m.userData.outline = true;
    if (V.els.view) m.resolution.set(Math.max(V.els.view.clientWidth, 1), Math.max(V.els.view.clientHeight, 1));
    return m;
  });
}

function outlineMesh(mesh, kind) {
  if (!mesh.userData.edges) return;               // a tape band: inside its part's outline
  if (!kind) {
    if (mesh.userData.outline) mesh.userData.outline.visible = false;
    mesh.userData.outlineKind = null;
    return;
  }
  let ol = mesh.userData.outline;
  if (!ol) {
    // built the first time the part is selected or hovered, from the same
    // EdgesGeometry its thin edges use, so the two cannot disagree
    // (a front's thin edges are fat lines already: the same segments, copied)
    const src = mesh.userData.edges;
    const g = src.userData.front
      ? new LineSegmentsGeometry().setPositions(src.geometry.attributes.instanceStart.data.array)
      : new LineSegmentsGeometry().fromEdgesGeometry(src.geometry);
    ol = paper(new LineSegments2(g, outlineMaterial(kind, mesh.userData.ghost)));
    ol.computeLineDistances();
    ol.renderOrder = 2;
    mesh.add(ol);
    mesh.userData.outline = ol;
  }
  mesh.userData.outlineKind = kind;
  ol.material = outlineMaterial(kind, mesh.userData.ghost);
  ol.visible = true;
}

// The Cabinets tab's view IS the selection (Round 2, 29 September 2026): an
// outline on the cabinet it shows says nothing and lands on every edge. There
// the cabinet gets none; only the PART picked gets the accent outline
// (`V.picked`, set by a click on a part), and the part under the pointer the
// lighter one. An attached panel selected beside its cabinet is still
// outlined as an item: there the view shows more than the selection, and the
// outline is what says which of the two the arrows move. The 3D tab is as it
// was: the selected item, and the hovered item, whole.
function applySelection() {
  for (const grp of V.groups.values()) {
    const selected = grp.userData.number === V.sel;
    const hovered = V.hover && V.hover.number === grp.userData.number;
    if (OPTS.single) {
      const item = grp.userData.item;
      const beside = selected && item && item.attached !== null && item.attached !== undefined;
      for (const mesh of grp.children) {
        const id = mesh.userData.id;
        outlineMesh(mesh, (beside || (V.picked && V.picked === id)) ? "sel"
                          : (V.hover && V.hover.id === id ? "hover" : null));
      }
      continue;
    }
    for (const mesh of grp.children) outlineMesh(mesh, selected ? "sel" : (hovered ? "hover" : null));
  }
  if (V.roomParts) {
    for (const mesh of V.roomParts.children) {
      const hov = V.hover && V.hover.id === mesh.userData.id;
      outlineMesh(mesh, hov ? "hover" : null);
    }
  }
  updateDimLines();
}

/* ---------- picking ----------------------------------------------------------- */

const raycaster = new THREE.Raycaster();
const pointerNDC = new THREE.Vector2();

function ndcOf(e) {
  const r = V.renderer.domElement.getBoundingClientRect();
  pointerNDC.set(((e.clientX - r.left) / r.width) * 2 - 1,
                 -((e.clientY - r.top) / r.height) * 2 + 1);
  return pointerNDC;
}

function pick(e, includeShell) {
  raycaster.setFromCamera(ndcOf(e), V.camera);
  raycaster.params.Line = {threshold: 0};
  const targets = V.pickables.filter((m) => m.visible && m.parent && m.parent.visible && !m.userData.unpickable);
  if (includeShell && V.shell) {
    V.shell.children.forEach((m) => { if (m.isMesh && m.visible) targets.push(m); });
  }
  const hits = raycaster.intersectObjects(targets, false);
  return hits.length ? hits[0] : null;
}

/* ---------- labels: DOM overlay, decluttered ---------------------------------- */

function labelFor(number) {
  let el = V.labelEls.get(number);
  if (!el) {
    el = h("div", {class: "v3dlabel", text: String(number)});
    el.addEventListener("pointerdown", (e) => { e.stopPropagation(); });
    el.addEventListener("click", (e) => { e.stopPropagation(); doSelect(number, null); });
    V.els.view.appendChild(el);
    V.labelEls.set(number, el);
  }
  return el;
}

const _v = new THREE.Vector3();
function placeLabels() {
  const shown = new Set();
  const rect = V.renderer.domElement.getBoundingClientRect();
  if (V.labels && V.payload) {
    const cands = [];
    for (const grp of V.groups.values()) {
      if (!grp.visible) continue;
      const b = new THREE.Box3().setFromObject(grp);
      const c = b.getCenter(_v.clone());
      c.z = b.max.z;
      const d = c.distanceTo(V.camera.position);
      const p = c.clone().project(V.camera);
      if (p.z > 1 || p.z < -1) continue;
      cands.push({number: grp.userData.number, x: (p.x + 1) / 2 * rect.width,
                  y: (1 - p.y) / 2 * rect.height, d: d, ghost: !itemShown(grp.userData.item)});
    }
    // nearer items win; a label that does not fit is hidden, never stacked
    cands.sort((a, b) => a.d - b.d);
    const placed = [];
    for (const c of cands) {
      const w = 26, hh = 18;
      const box = {x0: c.x - w / 2, x1: c.x + w / 2, y0: c.y - hh - 4, y1: c.y - 4};
      if (box.x0 < 0 || box.y0 < 0 || box.x1 > rect.width || box.y1 > rect.height) continue;
      if (placed.some((q) => !(box.x1 < q.x0 || box.x0 > q.x1 || box.y1 < q.y0 || box.y0 > q.y1))) continue;
      placed.push(box);
      const el = labelFor(c.number);
      el.style.left = box.x0 + "px";
      el.style.top = box.y0 + "px";
      el.style.opacity = c.ghost ? GHOST : 1;
      el.classList.toggle("sel", c.number === V.sel);
      // the selected item's label sits where its move handles start: it must
      // not take the press meant for them (its number is in the dock anyway)
      el.style.pointerEvents = V.handles ? "none" : "";
      el.hidden = false;
      shown.add(c.number);
      // a badge beside the label for a cabinet carrying a critical (red) or a
      // warning (amber); an accepted critical greyed, as in the Validation list
      const iss = V.issueOf && V.issueOf.get(c.number);
      if (iss) {
        const b = badgeFor(c.number);
        b.className = "v3dbadge " + (iss.accepted ? "accepted" : iss.level);
        b.title = iss.message;
        b.style.left = (box.x1 + 2) + "px";
        b.style.top = box.y0 + "px";
        b.style.pointerEvents = V.handles ? "none" : "";
        b.hidden = false;
      }
    }
  }
  for (const [n, el] of V.labelEls) if (!shown.has(n)) el.hidden = true;
  if (V.badgeEls) for (const [n, el] of V.badgeEls) if (!shown.has(n) || !(V.issueOf && V.issueOf.get(n))) el.hidden = true;
  placeDimLabels();
}

/* ---------- selected-cabinet dimension lines ---------------------------------- */

function updateDimLines() {
  if (V.dimLines) { V.scene.remove(V.dimLines); disposeObject(V.dimLines); V.dimLines = null; }
  for (const el of (V.dimEls || [])) el.remove();
  V.dimEls = [];
  const grp = V.sel !== null ? V.groups.get(V.sel) : null;
  if (!grp) { requestRender(); return; }
  const item = grp.userData.item;
  const b = new THREE.Box3().setFromObject(grp);
  const off = 90;
  const g = new THREE.Group();
  const mat = new THREE.LineBasicMaterial({color: PAPER.accent});
  const line = (a, c) => {
    const geo = new THREE.BufferGeometry().setFromPoints([a, c]);
    g.add(paper(new THREE.Line(geo, mat)));
  };
  // three lines along the box's own edges at the near-bottom corner, and the
  // figures — room.geometry's, sent by the server, never declared — beside them
  const p0 = new THREE.Vector3(b.min.x, b.min.y - off, b.min.z);
  line(p0, new THREE.Vector3(b.max.x, b.min.y - off, b.min.z));
  const p1 = new THREE.Vector3(b.max.x + off, b.min.y, b.min.z);
  line(p1, new THREE.Vector3(b.max.x + off, b.max.y, b.min.z));
  const p2 = new THREE.Vector3(b.min.x - off, b.min.y - off, b.min.z);
  line(p2, new THREE.Vector3(b.min.x - off, b.min.y - off, b.max.z));
  V.scene.add(g);
  V.dimLines = g;
  const dims = item.dims;
  const mk = (text, at) => {
    const el = h("div", {class: "v3ddim", text: text});
    el.dataset.x = at.x; el.dataset.y = at.y; el.dataset.z = at.z;
    V.els.view.appendChild(el);
    V.dimEls.push(el);
  };
  mk(`W ${dims.width}`, new THREE.Vector3((b.min.x + b.max.x) / 2, b.min.y - off, b.min.z));
  mk(`D ${dims.depth}`, new THREE.Vector3(b.max.x + off, (b.min.y + b.max.y) / 2, b.min.z));
  mk(`H ${dims.height}`, new THREE.Vector3(b.min.x - off, b.min.y - off, (b.min.z + b.max.z) / 2));
  requestRender();
}

function placeDimLabels() {
  if (!V.dimEls || !V.dimEls.length) return;
  const rect = V.renderer.domElement.getBoundingClientRect();
  for (const el of V.dimEls) {
    const p = new THREE.Vector3(+el.dataset.x, +el.dataset.y, +el.dataset.z).project(V.camera);
    const x = (p.x + 1) / 2 * rect.width, y = (1 - p.y) / 2 * rect.height;
    el.hidden = p.z > 1 || x < 0 || y < 0 || x > rect.width || y > rect.height;
    el.style.left = x + "px";
    el.style.top = y + "px";
  }
}

/* ---------- legend ------------------------------------------------------------ */

function updateLegend() {
  const leg = V.legendEl;
  if (!leg || !V.payload) return;
  const inView = new Set();
  for (const grp of V.groups.values()) grp.children.forEach((m) => inView.add(m.userData.part.board));
  if (V.roomParts) V.roomParts.children.forEach((m) => inView.add(m.userData.part.board));
  inView.delete("");                    // a runner: hardware, no board to key
  const rows = [...inView].sort().map((b) => {
    const look = V.payload.looks[b] || {};
    const sw = look.picture
      ? `<span class="sw" style="background:${look.colour} url('${look.picture.replace(/'/g, "%27")}') center/cover"></span>`
      : `<span class="sw" style="background:${look.colour}"></span>`;
    return `<div class="row">${sw}<span>${b}${look.set === false ? " <i>no colour set</i>" : ""}</span></div>`;
  }).join("");
  leg.querySelector(".rows").innerHTML = rows || `<div class="row"><i>nothing drawn</i></div>`;
  leg.querySelector(".nd").textContent = V.payload.not_drawn || "";
}

/* ---------- the pivot dot ------------------------------------------------------ */

function showPivot(on) {
  if (!V.pivotDot) return;
  if (on) {
    const t = V.controls.getTarget(new THREE.Vector3());
    V.pivotDot.position.copy(t);
    const d = V.ortho_on ? 4000 / V.camera.zoom : V.camera.position.distanceTo(t);
    V.pivotDot.scale.setScalar(Math.max(d / 140, 4));
  }
  V.pivotDot.visible = on;
  requestRender();
}

/* ---------- navigation ---------------------------------------------------------- */

function setOrbitPointFrom(e) {
  const hit = pick(e, true);
  if (!hit) return null;
  // Setting the orbit point keeps the camera where it is: nothing jumps.
  V.controls.setOrbitPoint(hit.point.x, hit.point.y, hit.point.z);
  return hit;
}

// Frame a box from wherever the camera is looking. camera-controls'
// `fitToBox` rounds the rotation to the nearest axis, which is not what Fit
// means here; `fitToSphere` keeps the direction and only moves in or out.
// Zoom towards the point under the cursor — wheel, Ctrl+wheel and a trackpad
// pinch, which arrives as a wheel with ctrlKey set, all come here.
//
// camera-controls' dolly-to-cursor holds the point on the TARGET's depth plane
// still, and reads the target as the screen centre, so a surface nearer than
// the target drifts and an orbit pivot set off-centre throws it. This is exact
// instead: in perspective the camera slides along the ray through the point
// under the cursor and the target with it, a pure scaling about that point, so
// it cannot move on screen — and the slide is clamped so the camera never
// passes through it. In orthographic the zoom changes and the camera shifts in
// its own plane by what keeps the point where it was. Nothing under the cursor
// zooms about the point at the pivot's depth on the cursor's ray.
//
// Zoom speed (29 September 2026): a mouse notch (deltaY 100) scales the view by
// exp(100 x WHEEL_ZOOM) = 1.25, double the old step (0.0011, 1.12). A trackpad
// pinch arrives as many small ctrlKey wheel events in pixels, sized by Chromium
// so the page's own zoom is exp(-deltaY / 100): PINCH_ZOOM 0.01 makes the view
// follow the fingers one for one. A pinch step is a few pixels, a notch 100 or
// 120, and a line-mode wheel is never a pinch.
const WHEEL_ZOOM = 0.0022;
const PINCH_ZOOM = 0.01;

function onWheel(e) {
  e.preventDefault();
  if (!V.payload || !V.controls) return;
  const dy = e.deltaMode === 1 ? e.deltaY * 16 : e.deltaMode === 2 ? e.deltaY * 100 : e.deltaY;
  if (!dy) return;
  // > 1 zooms out. One factor per gesture (29 September 2026): see WHEEL_ZOOM.
  const pinch = e.ctrlKey && e.deltaMode === 0 && Math.abs(e.deltaY) < 50;
  const s = Math.exp(Math.max(-300, Math.min(300, dy)) * (pinch ? PINCH_ZOOM : WHEEL_ZOOM));
  const c = V.controls;
  const C = V.camera.position.clone();
  const v = new THREE.Vector3(0, 0, -1).applyQuaternion(V.camera.quaternion);
  const dist = c.distance;
  const T0 = C.clone().add(v.clone().multiplyScalar(dist));   // the target, put back on the view axis
  c.setFocalOffset(0, 0, 0, false);
  const hit = pick(e, true);
  raycaster.setFromCamera(ndcOf(e), V.camera);
  if (!V.ortho_on) {
    let H;
    if (hit) H = hit.point.clone();
    else {
      const along = raycaster.ray.direction.dot(v) || 1;
      H = raycaster.ray.at(dist / along, new THREE.Vector3());
    }
    const dH = Math.max(C.distanceTo(H), 1);
    let k = s;
    if (dH * k < c.minDistance) k = c.minDistance / dH;
    if (dH * k > c.maxDistance) k = c.maxDistance / dH;
    const C2 = H.clone().add(C.clone().sub(H).multiplyScalar(k));
    const T2 = H.clone().add(T0.clone().sub(H).multiplyScalar(k));
    c.setLookAt(C2.x, C2.y, C2.z, T2.x, T2.y, T2.z, true);
  } else {
    const z = V.camera.zoom;
    const z2 = Math.max(c.minZoom, Math.min(c.maxZoom, z / s));
    const k = z2 / z;
    const W = hit ? hit.point.clone() : raycaster.ray.origin.clone();
    const Wp = W.clone().sub(v.clone().multiplyScalar(W.clone().sub(C).dot(v)));   // on the camera's plane
    const shift = Wp.sub(C).multiplyScalar(1 - 1 / k);
    c.setLookAt(C.x + shift.x, C.y + shift.y, C.z + shift.z,
                T0.x + shift.x, T0.y + shift.y, T0.z + shift.z, true);
    c.zoomTo(z2, true);
  }
  startLoop();
}

// Frame a box from a direction — the one the camera is looking from unless
// `dir` says otherwise. camera-controls' `fitToBox` rounds the rotation to the
// nearest axis and `fitToSphere` over-frames a flat room, so this projects the
// box's corners into the camera's own frame and puts the camera exactly far
// enough back (or, orthographic, at exactly the zoom) to hold them.
function fitTo(box, transition, dir) {
  if (!box || box.isEmpty()) return;
  const c = box.getCenter(new THREE.Vector3());
  const cur = V.controls.getPosition(new THREE.Vector3()).sub(V.controls.getTarget(new THREE.Vector3()));
  const d = (dir ? dir.clone() : cur).normalize();
  if (d.lengthSq() === 0) d.copy(ISO_DIR).normalize();
  const up = new THREE.Vector3(0, 0, 1);
  const right = new THREE.Vector3().crossVectors(up, d).normalize();
  if (right.lengthSq() === 0) right.set(1, 0, 0);
  const camUp = new THREE.Vector3().crossVectors(d, right).normalize();
  let hx = 0, hy = 0, hf = 0;
  for (let i = 0; i < 8; i++) {
    const p = new THREE.Vector3(i & 1 ? box.max.x : box.min.x, i & 2 ? box.max.y : box.min.y,
                                i & 4 ? box.max.z : box.min.z).sub(c);
    hx = Math.max(hx, Math.abs(p.dot(right)));
    hy = Math.max(hy, Math.abs(p.dot(camUp)));
    hf = Math.max(hf, p.dot(d));
  }
  const pad = 1.1;
  if (!V.ortho_on) {
    const t = Math.tan(THREE.MathUtils.degToRad(V.persp.fov / 2));
    const dist = Math.max(hy * pad / t, hx * pad / (t * V.persp.aspect), 300) + hf;
    const pos = c.clone().add(d.multiplyScalar(dist));
    V.controls.setLookAt(pos.x, pos.y, pos.z, c.x, c.y, c.z, transition);
  } else {
    const zoom = Math.min(V.ortho.top / Math.max(hy * pad, 1), V.ortho.right / Math.max(hx * pad, 1));
    const size = box.getSize(new THREE.Vector3()).length();
    const pos = c.clone().add(d.multiplyScalar(size * 2 + 1000));
    V.controls.setLookAt(pos.x, pos.y, pos.z, c.x, c.y, c.z, transition);
    V.controls.zoomTo(Math.max(V.controls.minZoom, Math.min(V.controls.maxZoom, zoom)), transition);
  }
  V.controls.setFocalOffset(0, 0, 0, transition);
  startLoop();
}

function fitAll(transition) { fitTo(V.bbox, transition !== false); }

function fitSelection(transition) {
  const grp = V.sel !== null ? V.groups.get(V.sel) : null;
  if (grp) fitTo(new THREE.Box3().setFromObject(grp), transition !== false);
  else fitAll(transition);
}

// Look from direction `dir` (a unit vector from the pivot towards the camera)
// at the scene, framing `box` — the view cube's faces, the named views and the
// number keys all come through here.
function lookFrom(dir, box, transition, keepDistance) {
  const b = box || V.bbox;
  if (keepDistance) {
    // the view cube: turn about the pivot, keeping the distance to it
    const t = V.controls.getTarget(new THREE.Vector3());
    const d = V.controls.distance;
    const pos = t.clone().add(dir.clone().normalize().multiplyScalar(d));
    V.controls.setLookAt(pos.x, pos.y, pos.z, t.x, t.y, t.z, transition !== false);
    startLoop();
    return;
  }
  fitTo(b, transition !== false, dir);
}

const ISO_DIR = new THREE.Vector3(-0.62, -0.72, 0.55);   // render frame

// Home looks at the room from the side its cabinets FACE: the direction is the
// walls' inward normals, each weighted by what stands on it, so a kitchen on
// walls A and B is seen from the open corner and not through wall A at the
// backs of its units. A room with cabinets all round has no such side and
// takes the plain isometric.
function homeDir() {
  const room = V.payload && V.payload.room;
  const d = new THREE.Vector3();
  if (room) {
    for (const w of room.walls) {
      const n = V.payload.items.filter((it) => it.wall === w.id && it.placed).length;
      d.x += w.normal[0] * (n + 0.25);
      d.y += w.normal[1] * (n + 0.25);
    }
  }
  if (d.length() < 0.2) return ISO_DIR.clone();
  d.normalize();
  // turn a little off the exact diagonal so both runs read, and lift it
  const turned = new THREE.Vector3(d.x * 0.92 - d.y * 0.39, d.x * 0.39 + d.y * 0.92, 0);   // room frame
  return toRender(turned.x, turned.y, 0.7).normalize();
}

function viewHome(transition) { lookFrom(homeDir(), V.bbox, transition); }
function viewTop(transition) { lookFrom(new THREE.Vector3(0, -0.02, 1), V.bbox, transition); }

function viewWall(index, transition) {
  const room = V.payload && V.payload.room;
  if (!room || !room.walls[index]) return;
  const w = room.walls[index];
  // face on: from the room, looking at the wall, orthographic — the 3D twin
  // of the wall elevation
  if (!V.ortho_on) setProjection(true, false);
  const box = wallBox(w);
  lookFrom(toRender(w.normal[0], w.normal[1], 0), box, transition);
}

function wallBox(w) {
  const b = new THREE.Box3();
  const top = V.payload.room.top;
  b.expandByPoint(toRender(w.start[0], w.start[1], 0));
  b.expandByPoint(toRender(w.end[0], w.end[1], top));
  // anything standing on it, out to its depth
  for (const grp of V.groups.values()) {
    if (grp.userData.item.wall === w.id) b.expandByObject(grp);
  }
  return b;
}

// Perspective <-> orthographic, keeping what is in view the same size at the
// pivot: the orthographic half-height is what the perspective frustum spans
// at the target's distance, and back again.
function setProjection(ortho, transition) {
  if (ortho === V.ortho_on) return;
  const from = V.controls, to = ortho ? V.cO : V.cP;
  const pos = from.getPosition(new THREE.Vector3());
  const tgt = from.getTarget(new THREE.Vector3());
  const dist = pos.distanceTo(tgt);
  from.enabled = false;
  to.enabled = true;
  V.controls = to;
  V.camera = ortho ? V.ortho : V.persp;
  V.ortho_on = ortho;
  to.setLookAt(pos.x, pos.y, pos.z, tgt.x, tgt.y, tgt.z, false);
  const halfFov = THREE.MathUtils.degToRad(V.persp.fov / 2);
  if (ortho) {
    const halfH = dist * Math.tan(halfFov);          // world mm the view spans, half
    to.zoomTo(V.ortho.top / halfH, false);
  } else {
    // put the perspective camera where it spans the same half-height
    const halfH = V.ortho.top / V.ortho.zoom;
    const d = halfH / Math.tan(halfFov);
    const dir = pos.clone().sub(tgt).normalize();
    const np = tgt.clone().add(dir.multiplyScalar(d));
    to.setLookAt(np.x, np.y, np.z, tgt.x, tgt.y, tgt.z, false);
  }
  updateBar();
  startLoop();
  requestRender();
}

/* ---------- the view cube ------------------------------------------------------- */

function makeCube() {
  const size = 96;
  const canvas = h("canvas", {class: "v3dcube", width: size * 2, height: size * 2, title: "click a face, edge or corner; drag to orbit"});
  canvas.style.width = canvas.style.height = size + "px";
  V.els.view.appendChild(canvas);
  const renderer = new THREE.WebGLRenderer({canvas: canvas, antialias: true, alpha: true});
  renderer.setPixelRatio(2);
  renderer.setSize(size, size, false);
  renderer.setClearColor(PAPER.none, 0);
  const scene = new THREE.Scene();
  const cam = new THREE.OrthographicCamera(-1.7, 1.7, 1.7, -1.7, 0.1, 10);
  cam.up.set(0, 0, 1);
  scene.add(new THREE.HemisphereLight(PAPER.white, PAPER.cubeGround, 1.6));
  const faces = [];   // +x, -x, +y, -y, +z, -z
  const labels = cubeLabels();
  for (let i = 0; i < 6; i++) {
    faces.push(new THREE.MeshLambertMaterial({map: cubeFaceTexture(labels[i]), transparent: false}));
  }
  const cube = new THREE.Mesh(new THREE.BoxGeometry(1.6, 1.6, 1.6), faces);
  scene.add(cube);
  const edges = new THREE.LineSegments(new THREE.EdgesGeometry(cube.geometry),
    new THREE.LineBasicMaterial({color: PAPER.cubeEdge}));
  cube.add(edges);
  const rc = new THREE.Raycaster();
  let drag = null;
  const press = (e) => {
    drag = {x: e.clientX, y: e.clientY, moved: false};
    canvas.setPointerCapture(e.pointerId);
    e.preventDefault();
  };
  const move = (e) => {
    if (!drag) return;
    const dx = e.clientX - drag.x, dy = e.clientY - drag.y;
    if (Math.abs(dx) + Math.abs(dy) > 2) drag.moved = true;
    if (drag.moved) {
      V.controls.rotate(-dx * 0.012, -dy * 0.012, false);
      startLoop();
    }
    drag.x = e.clientX; drag.y = e.clientY;
  };
  const up = (e) => {
    const was = drag; drag = null;
    if (!was || was.moved) return;
    const r = canvas.getBoundingClientRect();
    const nd = new THREE.Vector2(((e.clientX - r.left) / r.width) * 2 - 1,
                                 -((e.clientY - r.top) / r.height) * 2 + 1);
    rc.setFromCamera(nd, cam);
    const hit = rc.intersectObject(cube, false)[0];
    if (!hit) return;
    const p = hit.point.clone();
    // which axes count: a component near the face's extent is a face, two are
    // an edge, three a corner
    const dir = new THREE.Vector3(
      Math.abs(p.x) > 0.55 ? Math.sign(p.x) : 0,
      Math.abs(p.y) > 0.55 ? Math.sign(p.y) : 0,
      Math.abs(p.z) > 0.55 ? Math.sign(p.z) : 0);
    if (dir.lengthSq() === 0) dir.copy(hit.face.normal);
    if (dir.z === 0 && dir.x === 0 && dir.y === 0) return;
    // straight down or up: keep a hair of tilt so the polar limit does not bite
    if (dir.x === 0 && dir.y === 0) dir.y = -0.02;
    lookFrom(dir, null, true, true);
  };
  canvas.addEventListener("pointerdown", press);
  canvas.addEventListener("pointermove", move);
  canvas.addEventListener("pointerup", up);
  canvas.addEventListener("pointercancel", () => { drag = null; });
  const api = {
    render() {
      // the cube turns with the main camera: same rotation, seen from 4 units off
      const q = V.camera.quaternion;
      const dir = new THREE.Vector3(0, 0, 1).applyQuaternion(q).multiplyScalar(4);
      cam.position.copy(dir);
      cam.quaternion.copy(q);
      renderer.render(scene, cam);
    },
    relabel() {
      const lab = cubeLabels();
      faces.forEach((m, i) => { if (m.map) m.map.dispose(); m.map = cubeFaceTexture(lab[i]); m.needsUpdate = true; });
    },
    dispose() { renderer.dispose(); canvas.remove(); },
  };
  return api;
}

// What each cube face says: TOP and BOTTOM, and the letter of the wall that
// faces that way where there is one (its inward normal within 30 degrees of
// the face's outward normal), so "look at wall B" is one click.
function cubeLabels() {
  const out = ["", "", "", "", "TOP", "BOTTOM"];
  const normals = [[1, 0], [-1, 0], [0, 1], [0, -1]];
  const room = V.payload && V.payload.room;
  if (room) {
    normals.forEach(([fx, fy], i) => {
      let best = null;
      for (const w of room.walls) {
        const dot = w.normal[0] * fx - w.normal[1] * fy;   // render frame
        if (dot > Math.cos(Math.PI / 6) && (!best || dot > best.dot)) best = {dot: dot, id: w.id};
      }
      if (best) out[i] = best.id;
    });
  }
  return out;
}

function cubeFaceTexture(text) {
  const c = document.createElement("canvas");
  c.width = c.height = 128;
  const g = c.getContext("2d");
  g.fillStyle = text && text.length <= 2 ? PAPER.cubeHot : "#" + PAPER.cube.toString(16).padStart(6, "0");
  g.fillRect(0, 0, 128, 128);
  g.strokeStyle = "#" + PAPER.cubeEdge.toString(16).padStart(6, "0");
  g.lineWidth = 3;
  g.strokeRect(1.5, 1.5, 125, 125);
  if (text) {
    g.fillStyle = PAPER.cubeText;
    g.font = (text.length <= 2 ? "bold 56px" : "bold 22px") + " system-ui, sans-serif";
    g.textAlign = "center";
    g.textBaseline = "middle";
    g.fillText(text, 64, 66);
  }
  const tex = new THREE.CanvasTexture(c);
  tex.colorSpace = THREE.SRGBColorSpace;
  return tex;
}

/* ---------- pointer: orbit pivot, click, double-click, hover ------------------- */

function onPointerDown(e) {
  if (V.els.view.contains(document.activeElement) === false) V.renderer.domElement.focus({preventScroll: true});
  V.press = {x: e.clientX, y: e.clientY, t: performance.now(), button: e.button};
  V.pressed = true;
  startLoop();
  if (V.dragging) return;              // F6: the move handle owns this press
  if (e.button === 0 && V.handles) {
    const axis = pickHandle(e);
    if (axis) {
      // a press on a move handle: the camera must not see it
      e.preventDefault();
      e.stopImmediatePropagation();
      V.press = null;
      startMove(e, axis);
      return;
    }
  }
  // Orbit about the point pressed on, pan at its depth; nothing hit keeps the
  // current pivot. Done before camera-controls sees the press.
  setOrbitPointFrom(e);
}

function onPointerUp(e) {
  const p = V.press;
  V.press = null;
  if (!p || V.dragging) return;
  const moved = Math.hypot(e.clientX - p.x, e.clientY - p.y) > CLICK_PX;
  if (moved) return;
  if (p.button === 2) { openContextMenu(e); return; }
  if (p.button !== 0) return;
  closeMenus();
  const hit = pick(e, false);
  if (hit) doSelect(hit.object.userData.number || null, hit.object.userData.part);
  else doSelect(null, null);
}

function onDblClick(e) {
  const hit = pick(e, false);
  if (hit && hit.object.userData.number) {
    doSelect(hit.object.userData.number, hit.object.userData.part);
    flyTo(hit.object.userData.number);
  } else {
    fitAll(true);
  }
}

function onPointerMove(e) {
  if (V.press && Math.hypot(e.clientX - V.press.x, e.clientY - V.press.y) > CLICK_PX) return;
  if (V.dragging) return;
  const hit = pick(e, false);
  const now = hit ? {number: hit.object.userData.number, id: hit.object.userData.id, part: hit.object.userData.part} : null;
  const same = (!now && !V.hover) || (now && V.hover && now.id === V.hover.id);
  if (same) return;
  V.hover = now;
  applySelection();
  V.renderer.domElement.style.cursor = now ? "pointer" : "";
  if (now) status(describe(now.number, now.part));
  else status(V.hint || "");
  requestRender();
}

function describe(number, part) {
  const item = V.payload.items.find((i) => i.number === number);
  const kind = item ? (item.panel ? "Panel" : item.kind[0].toUpperCase() + item.kind.slice(1)) : "";
  const role = part ? roleName(part) : "";
  const who = number ? `${number} · ${kind}` : (part ? roleName(part) : "");
  return [who, role && number ? role : "", part ? part.board : ""].filter(Boolean).join(" · ");
}

function roleName(part) {
  const names = {side: "Side", top: "Top", bottom: "Bottom", door: "Door", drawer: "Drawer face",
                 blind: "Blind panel", panel: "Panel", back: "Backing", carcass: "Carcass (footprint only)",
                 plinth: "Plinth board", filler: "Filler", support: "Support", shelf: "Shelf",
                 drawer_side: "Drawer side", drawer_front: "Drawer front", drawer_back: "Drawer back",
                 drawer_base: "Drawer base", runner_outer: "Runner (outer channel)",
                 runner_inner: "Runner (inner member)"};
  const n = names[part.role] || part.role;
  if (part.role === "drawer" && part.label === "inner") return `Inner drawer face ${part.index + 1}`;
  if (part.role === "door" || part.role === "drawer") return `${n} ${part.index + 1}`;
  if (/^drawer_|^runner_/.test(part.role)) return `${n}, drawer ${part.index + 1}`;
  if (part.role === "support" && part.label) return `${n} — ${part.label}`;
  if (part.role === "shelf") return part.label === "fixed" ? `${n} (fixed)` : n;
  return n;
}

/* ---------- keys ---------------------------------------------------------------- */

function onKey(e) {
  const t = e.target;
  if (t && (t.tagName === "INPUT" || t.tagName === "SELECT" || t.tagName === "TEXTAREA" || t.isContentEditable)) return;
  if (!V.visible) return;
  if (!(V.pointerOver || V.els.view.contains(document.activeElement))) return;
  if (e.type === "keyup") {
    if (e.code === "Space") { V.space = false; V.controls.mouseButtons.left = CameraControls.ACTION.ROTATE; }
    return;
  }
  if (e.ctrlKey || e.metaKey || e.altKey) return;
  const k = e.key.toLowerCase();
  if (e.code === "Space") { V.space = true; V.controls.mouseButtons.left = CameraControls.ACTION.TRUCK; e.preventDefault(); return; }
  if (k === "f") fitSelection(true);
  else if (k === "h") { if (V.ortho_on) setProjection(false, false); viewHome(true); }
  else if (k === "t") viewTop(true);
  else if (k === "i") { if (V.ortho_on) setProjection(false, false); viewHome(true); }
  else if (k === "p") setProjection(!V.ortho_on, true);
  else if (k === "o") toggleFronts();
  else if (k === "c") toggleClearances();
  else if (k === "x") setDisplay(V.display === "xray" ? "edges" : "xray");
  else if (k === "l") { V.labels = !V.labels; updateBar(); requestRender(); }
  else if (k === "escape") {
    if (V.dragging) { cancelDrag(); return; }
    if (V.ctxEl && !V.ctxEl.hidden) { closeMenus(); return; }
    closeMenus();
    doSelect(null, null);
  }
  else if (k === "?" || (k === "/" && e.shiftKey)) toggleHelp();
  else if (/^[1-9]$/.test(k)) viewWall(+k - 1, true);
  else return;
  e.preventDefault();
}

/* ---------- toolbar, menus, help ------------------------------------------------- */

function menu(button, items) {
  // a small dropdown under a toolbar button
  const box = h("div", {class: "v3dmenu"});
  const open = () => {
    closeMenus();
    box.innerHTML = "";
    for (const it of items()) {
      box.appendChild(h("button", {text: it.label, class: it.on ? "on" : "",
                                   onclick: () => { it.run(); closeMenus(); updateBar(); }}));
    }
    const r = button.getBoundingClientRect(), br = V.els.bar.getBoundingClientRect();
    box.style.left = (r.left - br.left) + "px";
    box.hidden = false;
  };
  button.addEventListener("click", (e) => { e.stopPropagation(); box.hidden ? open() : closeMenus(); });
  V.els.bar.appendChild(box);
  return box;
}

function closeMenus() {
  V.els.bar.querySelectorAll(".v3dmenu").forEach((m) => { m.hidden = true; });
  if (V.ctxEl) V.ctxEl.hidden = true;
}

function buildBar() {
  const bar = V.els.bar;
  bar.innerHTML = "";
  const B = {};
  B.views = h("button", {text: "Views ▾", title: "named views"});
  B.proj = h("button", {text: "Persp", title: "P: perspective / orthographic",
                        onclick: () => setProjection(!V.ortho_on, true)});
  B.display = h("button", {text: "Shaded + edges ▾", title: "X: x-ray"});
  const sep = () => h("span", {class: "sep"});
  B.layers = {};
  for (const [k, name] of [["base", "Base"], ["wall", "Wall"], ["tall", "Tall"], ["panels", "Panels"]]) {
    B.layers[k] = h("button", {text: name, title: "show this layer solid; others ghost",
                               onclick: () => { if (V.hooks.toggleLayer) V.hooks.toggleLayer(k); }});
  }
  B.fronts = h("button", {text: "Fronts", title: "O: open / close every door and drawer", onclick: () => toggleFronts()});
  B.runners = h("button", {text: "Runners", title: "show or hide the drawer runners (simple blocks: outer channel and inner member)",
                           onclick: () => { V.runners = !V.runners; applyRunners(); updateBar(); }});
  B.ao = h("button", {text: "AO", title: "ambient occlusion: the soft dark where boards meet (off under X-ray)",
                      onclick: () => { V.ao = !V.ao; updateBar(); requestRender(); }});
  B.grid = h("button", {text: "Grid", title: "the drawing grid: 100 mm and 1 m (on with edges and in X-ray, off in Shaded, until changed)",
                        onclick: () => { V.gridOn[V.display] = !V.gridOn[V.display]; applyRoomLook(); updateBar(); requestRender(); }});
  B.clear = h("button", {text: "Clearances", title: "C: door swings and drawer pull-outs", onclick: () => toggleClearances()});
  B.walls = h("button", {text: "Walls: auto ▾", title: "which walls are drawn"});
  B.ceiling = h("button", {text: "Ceiling", title: "draw the ceiling", onclick: () => { V.ceiling = !V.ceiling; applyWalls(); updateBar(); }});
  B.labels = h("button", {text: "Labels", title: "L: item numbers", onclick: () => { V.labels = !V.labels; updateBar(); requestRender(); }});
  B.isolate = h("button", {text: "Isolate", title: "ghost everything but the selection (the plan's isolate too)",
                           onclick: () => setIsolate(V.isolate === null ? V.sel : null)});
  B.snap = h("button", {text: "Snapshot", title: "save this view as a PNG into output/<job>/snapshots/", onclick: () => snapshot()});
  B.fit = h("button", {text: "Fit", title: "F: fit the selection, or everything", onclick: () => fitSelection(true)});
  B.help = h("button", {text: "?", title: "shortcuts", onclick: () => toggleHelp()});
  if (OPTS.single) {
    // the one cabinet alone: nothing to layer, isolate, wall off or clear
    B.layers = {};
    bar.append(B.views, B.proj, B.display, B.ao, B.grid, B.fit, sep(), B.fronts, B.runners, B.labels, sep(), B.help);
  } else {
    bar.append(B.views, B.proj, B.display, B.ao, B.grid, B.fit, sep(),
               B.layers.base, B.layers.wall, B.layers.tall, B.layers.panels, sep(),
               B.fronts, B.runners, B.clear, B.walls, B.ceiling, B.labels, B.isolate, sep(), B.snap, B.help);
  }
  menu(B.views, () => {
    const out = [
      {label: "Home (isometric)   H", run: () => { if (V.ortho_on) setProjection(false, false); viewHome(true); }},
      {label: "Top (plan)   T", run: () => viewTop(true)},
      {label: "Fit all", run: () => fitAll(true)},
    ];
    const room = V.payload && V.payload.room;
    if (room) room.walls.forEach((w, i) => out.push({label: `Front of wall ${w.id}   ${i + 1}`, run: () => viewWall(i, true)}));
    return out;
  });
  menu(B.display, () => [
    {label: "Shaded with edges", on: V.display === "edges", run: () => setDisplay("edges")},
    {label: "Shaded", on: V.display === "shaded", run: () => setDisplay("shaded")},
    {label: "X-ray   X", on: V.display === "xray", run: () => setDisplay("xray")},
  ]);
  if (!OPTS.single) menu(B.walls, () => [
    {label: "Auto (nearest hides)", on: V.walls === "auto", run: () => { V.walls = "auto"; applyWalls(); }},
    {label: "All", on: V.walls === "all", run: () => { V.walls = "all"; applyWalls(); }},
    {label: "None", on: V.walls === "none", run: () => { V.walls = "none"; applyWalls(); }},
  ]);
  V.bar = B;
  document.addEventListener("click", closeMenus);
  updateBar();
}

function updateBar() {
  const B = V.bar;
  if (!B) return;
  B.proj.textContent = V.ortho_on ? "Ortho" : "Persp";
  B.display.textContent = {edges: "Shaded + edges", shaded: "Shaded", xray: "X-ray"}[V.display] + " ▾";
  B.walls.textContent = "Walls: " + V.walls + " ▾";
  B.ceiling.classList.toggle("on", V.ceiling);
  B.labels.classList.toggle("on", V.labels);
  B.fronts.classList.toggle("on", V.frontsOpen);
  B.runners.classList.toggle("on", V.runners);
  B.ao.classList.toggle("on", V.ao && V.display !== "xray");
  B.ao.disabled = V.display === "xray" || !V.aoPass;
  B.grid.classList.toggle("on", !!V.gridOn[V.display]);
  B.clear.classList.toggle("on", V.clearances);
  B.isolate.classList.toggle("on", V.isolate !== null);
  B.isolate.disabled = V.isolate === null && V.sel === null;
  for (const k in B.layers) B.layers[k].classList.toggle("on", V.layers === null || V.layers.has(k));
}

function setDisplay(mode) {
  V.display = mode;
  for (const grp of V.groups.values()) {
    grp.children.forEach(applyDisplay);
    const contact = contactOf(grp.userData.number);
    if (contact) contact.visible = grp.visible && itemShown(grp.userData.item) && mode !== "xray";
  }
  if (V.roomParts) V.roomParts.children.forEach(applyDisplay);
  applyRoomLook();
  shadowsDirty();
  updateBar();
  requestRender();
}

function toggleHelp() {
  if (!V.helpEl) {
    V.helpEl = h("div", {class: "v3dhelp", html: `
      <b>Mouse</b><br>
      Left-drag orbits about the point you pressed on · right- or middle-drag pans (the grabbed point stays under the cursor) ·
      wheel / Ctrl+wheel / pinch zooms towards the cursor · Shift+left-drag and Space+left-drag pan (trackpads: two-finger click-drag pans, pinch zooms).<br>
      Click selects · double-click a part frames its cabinet · double-click empty space fits all · right-click for the menu.<br>
      <b>Keys</b> (pointer over the view)<br>
      F fit · H home · T top · I isometric · 1-9 face on to wall A, B, C… (orthographic) · P perspective / orthographic ·
      O fronts open · C clearances · X x-ray · L labels · Esc clear · ? this card.<br>
      Nothing is deleted or duplicated from a key.${OPTS.single ? `<br>
      <b>An attached panel</b>: select it and drag its arrows — across, back and up its
      cabinet — to move it; it snaps to the carcass faces and edges and writes the
      offsets Panel design shows.` : ""}`});
    V.els.view.appendChild(V.helpEl);
  } else {
    V.helpEl.hidden = !V.helpEl.hidden;
  }
}

/* ---------- selection ---------------------------------------------------------- */

// A click in the view selects WITHOUT isolating; the item list selects AND
// isolates, as the cabinet table does. index.html holds the one selection and
// the one isolate, and tells this view back through `select` / `isolate`.
function doSelect(number, part, opts) {
  V.sel = number;
  V.picked = part ? part.id : null;          // the part clicked (the Cabinets tab's outline)
  const isolate = !!(opts && opts.isolate);
  if (isolate) V.isolate = number;
  else if (V.isolate !== null && number !== null) V.isolate = number;    // follows the selection
  applyGhosting();
  updateBar();
  updateList();
  if (V.hooks.select) V.hooks.select(number, part, {isolate: isolate});
  showCard(number, part);
}

function showCard(number, part) {
  if (V.hooks.card) V.hooks.card(number, part);
}

function setIsolate(number, silent) {
  V.isolate = number === undefined ? null : number;
  applyGhosting();
  updateBar();
  updateList();
  if (!silent && V.hooks.isolate) V.hooks.isolate(V.isolate);
}

function setHidden(number, hidden) {
  if (hidden) V.hidden.add(number); else V.hidden.delete(number);
  applyGhosting();
  updateList();
}

/* ---------- the item list (left, collapsible) ----------------------------------- */

function buildList() {
  const box = V.els.list;
  if (!box) return;
  if (!box.querySelector(".hd")) {
    box.innerHTML = `<div class="hd"><span>Items</span><button class="tog" title="collapse">–</button></div><div class="rows"></div>`;
    box.querySelector(".tog").addEventListener("click", (e) => {
      box.classList.toggle("closed");
      e.target.textContent = box.classList.contains("closed") ? "+" : "–";
      try { localStorage.setItem("cupboard.3dlist", box.classList.contains("closed") ? "closed" : "open"); } catch (err) { /* fine */ }
      resize();
    });
    try { if (localStorage.getItem("cupboard.3dlist") === "closed") { box.classList.add("closed"); box.querySelector(".tog").textContent = "+"; } } catch (err) { /* fine */ }
    box.addEventListener("click", (e) => {
      const eye = e.target.closest(".eye");
      const row = e.target.closest(".row");
      if (!row) return;
      const n = +row.dataset.n;
      if (eye) { setHidden(n, !V.hidden.has(n)); e.stopPropagation(); return; }
      if (!V.groups.has(n)) { doSelect(n, null, {isolate: true}); return; }
      // from the list: select, isolate, and fly to it — how an item buried
      // behind others is reached
      doSelect(n, null, {isolate: true});
      flyTo(n);
    });
  }
  updateList();
}

function updateList() {
  const box = V.els.list;
  if (!box || !V.payload) return;
  const rows = box.querySelector(".rows");
  if (!rows) return;
  rows.innerHTML = V.payload.items.map((it) => {
    const d = it.dims || {};
    const kind = it.panel ? (it.attached !== null && it.attached !== undefined ? `panel on ${it.attached}` : "panel")
                          : it.kind + (it.corner ? " " + it.corner : "");
    const desc = it.placed ? `${d.width}×${d.height}×${d.depth}` : "not placed";
    const cls = ["row", it.number === V.sel ? "sel" : "", it.placed ? "" : "off",
                 V.hidden.has(it.number) ? "hidden3d" : ""].join(" ");
    return `<div class="${cls}" data-n="${it.number}" title="${kind} ${desc}"><span class="n">${it.number}</span>` +
      `<span class="d">${kind} · ${desc}</span>` +
      (it.placed ? `<button class="eye" title="hide / show in 3D">${V.hidden.has(it.number) ? "○" : "●"}</button>` : "") +
      `</div>`;
  }).join("");
}

/* ---------- the context menu (right-click without a drag) ------------------------ */

function openContextMenu(e) {
  closeMenus();
  const hit = pick(e, false);
  const number = hit && hit.object.userData.number ? hit.object.userData.number : (V.sel);
  const part = hit ? hit.object.userData.part : null;
  if (!V.ctxEl) {
    V.ctxEl = h("div", {class: "v3dctx"});
    V.ctxEl.hidden = true;
    V.els.view.appendChild(V.ctxEl);
    V.ctxEl.addEventListener("click", (ev) => ev.stopPropagation());
  }
  const items = [];
  if (number) {
    items.push({label: `Fit to ${number}`, run: () => { doSelect(number, part); flyTo(number); }});
    items.push({label: V.isolate === number ? "Stop isolating" : `Isolate ${number}`,
                run: () => { doSelect(number, part); setIsolate(V.isolate === number ? null : number); }});
    items.push({label: (V.openFor && V.openFor.has(number)) ? `Close ${number}'s fronts` : `Open ${number}'s fronts`,
                run: () => toggleFrontsFor(number)});
    items.push({label: `Hide ${number} in 3D`, run: () => setHidden(number, true)});
  }
  if (V.hidden.size || V.isolate !== null) items.push({label: "Show all", run: () => { V.hidden.clear(); setIsolate(null); }});
  if (part && part.line) items.push({label: `Select ${part.line} in cut list`,
                                     run: () => { doSelect(number, part); if (V.hooks.showLine) V.hooks.showLine(part.line); }});
  if (!items.length) return;
  V.ctxEl.innerHTML = "";
  for (const it of items) V.ctxEl.appendChild(h("button", {text: it.label, onclick: () => { closeMenus(); it.run(); }}));
  const r = V.els.view.getBoundingClientRect();
  V.ctxEl.style.left = Math.min(e.clientX - r.left, r.width - 190) + "px";
  V.ctxEl.style.top = Math.min(e.clientY - r.top, r.height - 40 * items.length - 10) + "px";
  V.ctxEl.hidden = false;
}

/* ---------- fronts open / closed (F5) --------------------------------------------
   A door turns about the hinge axis the server sent, by the angle it sent —
   its sign is which way the leaf swings (model.hinge_side, the same rule the
   plan's arcs and the elevation's marks read). A drawer face slides out along
   its pull-out direction by the runner's length. Because drawer boxes are not
   drawn, a pulled-out face moves on its own. The toolbar opens everything; the
   context menu flips one cabinet the other way. Animated ~400 ms.             */

const FRONT_MS = 400;

function frontOpen(mesh) {
  const n = mesh.userData.number;
  const flipped = V.openFor && V.openFor.has(n);
  return V.frontsOpen ? !flipped : !!flipped;
}

// Pose one front at fraction t of its travel. The mesh's geometry is in world
// coordinates, so turning it about a world axis through A is a rotation about
// Z plus the translation A - R(theta) A.
function poseFront(m) {
  const part = m.userData.part;
  const t = m.userData.t || 0;
  if (part.hinge) {
    const [ax, ay] = part.hinge.axis[0];
    const th = THREE.MathUtils.degToRad(part.hinge.angle) * t;
    const c = Math.cos(th), s = Math.sin(th);
    m.rotation.set(0, 0, th);
    m.position.set(ax - (c * ax - s * ay), ay - (s * ax + c * ay), 0);
  } else if (part.pull) {
    m.position.set(part.pull.dir[0] * part.pull.distance * t,
                   part.pull.dir[1] * part.pull.distance * t, 0);
  }
  shadowsDirty();                         // a front moved: the scene changed
}

function applyFronts(instant) {
  const moving = [];
  for (const grp of V.groups.values()) {
    for (const m of grp.children) {
      const part = m.userData.part;
      if (!part || !(part.hinge || part.pull)) continue;
      m.userData.tTarget = frontOpen(m) ? 1 : 0;
      if (m.userData.t === undefined) m.userData.t = 0;
      if (instant) { m.userData.t = m.userData.tTarget; poseFront(m); }
      else if (m.userData.t !== m.userData.tTarget) moving.push(m);
    }
  }
  if (!moving.length) { requestRender(); return; }
  const start = performance.now();
  const from = new Map(moving.map((m) => [m, m.userData.t]));
  V.animating = () => {
    const k = Math.min((performance.now() - start) / FRONT_MS, 1);
    const e = k < 0.5 ? 2 * k * k : 1 - Math.pow(-2 * k + 2, 2) / 2;   // ease in and out
    for (const m of moving) {
      m.userData.t = from.get(m) + (m.userData.tTarget - from.get(m)) * e;
      poseFront(m);
    }
    if (k >= 1) V.animating = null;
  };
  startLoop();
}

function toggleFronts() {
  V.frontsOpen = !V.frontsOpen;
  if (V.openFor) V.openFor.clear();          // the toolbar speaks for every cabinet
  applyFronts(false);
  updateBar();
}

function toggleFrontsFor(number) {
  if (!V.openFor) V.openFor = new Set();
  if (V.openFor.has(number)) V.openFor.delete(number); else V.openFor.add(number);
  applyFronts(false);
}

/* ---------- clearances, overlaps, validation badges (F5) -------------------------
   The swing and pull-out envelopes room.py already emits for the plan's hover,
   extruded over their height range, translucent; red where room.clashes says
   so. An overlap (a critical) outlines both cabinets in red whatever the
   toggle says. All of it comes from the server; nothing is computed here.  */

function toggleClearances() { V.clearances = !V.clearances; buildOverlays(); updateBar(); }

function buildOverlays() {
  if (V.overlays) { V.root.remove(V.overlays); disposeObject(V.overlays); V.overlays = null; }
  if (!V.payload) { requestRender(); return; }
  const g = new THREE.Group();
  const ov = V.payload.overlays || {swings: [], overlaps: [], issues: []};
  if (V.clearances) {
    for (const sw of ov.swings) {
      if (!sw.outline || sw.outline.length < 3) continue;
      const geom = extrude(sw.outline, sw.z0, sw.z1);
      const colour = sw.clash ? PAPER.clash : PAPER.clear;
      const mesh = new THREE.Mesh(geom, new THREE.MeshBasicMaterial({
        color: colour, transparent: true, opacity: sw.clash ? 0.32 : 0.16, depthWrite: false,
        toneMapped: false}));
      mesh.renderOrder = 3;
      mesh.userData = {overlay: true, cabinet: sw.cabinet, kind: sw.kind, clash: sw.clash};
      const edges = paper(new THREE.LineSegments(new THREE.EdgesGeometry(geom, 30),
        new THREE.LineBasicMaterial({color: colour, transparent: true, opacity: 0.7, toneMapped: false})));
      g.add(mesh, edges);
    }
  }
  for (const o of ov.overlaps) {
    for (const n of [o.a, o.b]) {
      const grp = V.groups.get(n);
      if (!grp) continue;
      const rb = new THREE.Box3().setFromObject(grp).expandByScalar(6);   // render frame
      const box = new THREE.Box3(new THREE.Vector3(rb.min.x, -rb.max.y, rb.min.z),
                                 new THREE.Vector3(rb.max.x, -rb.min.y, rb.max.z));   // room frame
      const helper = paper(new THREE.Box3Helper(box, PAPER.overlap));
      helper.material.toneMapped = false;
      helper.userData = {overlay: true, overlap: true, cabinet: n};
      g.add(helper);
    }
  }
  V.root.add(g);
  V.overlays = g;
  // the worst issue per cabinet, for the badges over the labels
  V.issueOf = new Map();
  for (const i of ov.issues) {
    const rank = i.level === "critical" ? (i.accepted ? 1 : 3) : 2;
    const cur = V.issueOf.get(i.cabinet);
    if (!cur || rank > cur.rank) V.issueOf.set(i.cabinet, {rank: rank, level: i.level, accepted: i.accepted, message: i.message});
  }
  requestRender();
}

function badgeFor(number) {
  if (!V.badgeEls) V.badgeEls = new Map();
  let el = V.badgeEls.get(number);
  if (!el) {
    el = h("div", {class: "v3dbadge", text: "!"});
    el.addEventListener("pointerdown", (e) => e.stopPropagation());
    el.addEventListener("click", (e) => { e.stopPropagation(); doSelect(number, null); });
    V.els.view.appendChild(el);
    V.badgeEls.set(number, el);
  }
  return el;
}

/* ---------- snapshot (F5): the view as a PNG, saved by the server ---------------- */

function snapshot() {
  if (!V.renderer || !V.hooks.snapshot) return;
  draw();                                         // the buffer is not preserved: draw, then read
  V.hooks.snapshot(V.renderer.domElement.toDataURL("image/png"));
}

/* ---------- moving a cabinet or a panel in 3D (F6) -------------------------------
   A SELECTED, placed item shows a move handle per axis it may move on: an
   arrow along its wall, an arrow up, and for a panel an arrow out from the
   wall. Dragging an arrow moves the item along that axis only; a left-drag
   on the part itself still orbits, so moving is always deliberate.

   On the press, ONE /api/drag call (the same the plan and the elevation
   make) gives the snap targets, leg_lift and the tolerance; the wall's world
   direction and normal are already in the scene. The browser projects the
   pointer onto the chosen axis (the point on the axis nearest the cursor's
   ray), keeps the grab offset by construction, and takes the NEAREST
   candidate within Standard.snap_tolerance, ties broken by the nearest
   neighbour along the wall — the plan's rule. It works out no position of
   its own. The press listens before it awaits, and replays the last move and
   a release once the model lands, so a quick flick never sticks. The drop
   writes Placement.x, .z (and .y for a panel) and nothing else; Esc puts the
   item back. No moving onto another wall, no rotating.                      */

const HANDLE_LEN = 420;

function handleMesh(dir, origin, colour, axis) {
  const g = new THREE.Group();
  const mat = new THREE.MeshBasicMaterial({color: colour, depthTest: false, transparent: true, opacity: 0.9});
  const shaft = new THREE.Mesh(new THREE.CylinderGeometry(14, 14, HANDLE_LEN - 110, 10), mat);
  shaft.position.y = (HANDLE_LEN - 110) / 2;
  const head = new THREE.Mesh(new THREE.ConeGeometry(48, 110, 14), mat);
  head.position.y = HANDLE_LEN - 55;
  // a fat invisible sleeve, so a 28 mm shaft is grabbable at all
  const grab = new THREE.Mesh(new THREE.CylinderGeometry(70, 70, HANDLE_LEN, 8),
                              new THREE.MeshBasicMaterial({visible: false}));
  grab.position.y = HANDLE_LEN / 2;
  g.add(shaft, head, grab);
  g.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), dir.clone().normalize());
  g.position.copy(origin);
  g.renderOrder = 20;
  g.userData = {handle: axis, dir: dir.clone().normalize()};
  [shaft, head, grab].forEach((m) => { m.userData = {handle: axis, group: g, noAO: true}; m.renderOrder = 20; });
  return g;
}

function updateHandles() {
  if (V.handles) { V.scene.remove(V.handles); disposeObject(V.handles); V.handles = null; }
  if (OPTS.single) { updateAttachHandles(); return; }
  const grp = V.sel !== null ? V.groups.get(V.sel) : null;
  const room = V.payload && V.payload.room;
  if (!grp || !room || !grp.visible) { requestRender(); return; }
  const item = grp.userData.item;
  if (!item.placed || !itemShown(item)) { requestRender(); return; }
  // an attached panel stands where its cabinet puts it: no handles of its own
  if (item.attached !== null && item.attached !== undefined) { requestRender(); return; }
  const wall = room.walls.find((w) => w.id === item.wall);
  if (!wall) { requestRender(); return; }
  const b = new THREE.Box3().setFromObject(grp);
  const c = b.getCenter(new THREE.Vector3());
  const dir = toRender(wall.dir[0], wall.dir[1], 0);
  const nrm = toRender(wall.normal[0], wall.normal[1], 0);
  // from the middle of the item's top face, so they read whichever way it is seen
  const origin = new THREE.Vector3(c.x, c.y, b.max.z + 40);
  const hs = new THREE.Group();
  hs.add(handleMesh(dir, origin, PAPER.accent, "x"));
  hs.add(handleMesh(new THREE.Vector3(0, 0, 1), origin, PAPER.pivot, "z"));
  if (item.panel) hs.add(handleMesh(nrm, origin, PAPER.warn, "y"));
  hs.userData = {number: item.number};
  V.scene.add(hs);
  V.handles = hs;
  requestRender();
}

// The single view (UI restructure, 28 September 2026 — attached-panels spec
// B4): a selected ATTACHED panel gets three arrows in its cabinet's frame —
// across (at_x), back (at_y, from the front face of the sides towards the
// back) and up (at_z). The view stands the cabinet with its back on y 0 and
// its front towards +y, so "back" is -y in the room frame.
function updateAttachHandles() {
  const grp = V.sel !== null ? V.groups.get(V.sel) : null;
  if (!grp || !grp.visible) { requestRender(); return; }
  const item = grp.userData.item;
  if (item.attached === null || item.attached === undefined || !item.at) { requestRender(); return; }
  const b = new THREE.Box3().setFromObject(grp);
  const c = b.getCenter(new THREE.Vector3());
  const origin = new THREE.Vector3(c.x, c.y, b.max.z + 40);
  const hs = new THREE.Group();
  hs.add(handleMesh(toRender(1, 0, 0), origin, PAPER.accent, "x"));
  hs.add(handleMesh(toRender(0, -1, 0), origin, PAPER.warn, "y"));
  hs.add(handleMesh(new THREE.Vector3(0, 0, 1), origin, PAPER.pivot, "z"));
  hs.userData = {number: item.number};
  V.scene.add(hs);
  V.handles = hs;
  requestRender();
}

function pickHandle(e) {
  if (!V.handles) return null;
  V.handles.updateMatrixWorld(true);        // built since the last frame, maybe
  raycaster.setFromCamera(ndcOf(e), V.camera);
  const hits = raycaster.intersectObjects(V.handles.children, true);
  return hits.length ? hits[0].object.userData.handle : null;
}

// The point on the axis (through P0 along u) nearest the cursor's ray, as a
// distance from P0 along u — pure camera maths, no dimension of the model.
function axisParam(e, P0, u) {
  raycaster.setFromCamera(ndcOf(e), V.camera);
  const o = raycaster.ray.origin, d = raycaster.ray.direction;
  const w0 = P0.clone().sub(o);
  const a = u.dot(u), b = u.dot(d), c = d.dot(d);
  const dd = w0.dot(u), ee = w0.dot(d);
  const den = a * c - b * b;
  if (Math.abs(den) < 1e-9) return null;               // looking straight along the axis
  return (b * ee - c * dd) / den;
}

function startMove(e, axis) {
  if (OPTS.single) { startAttachMove(e, axis); return; }
  const grp = V.groups.get(V.sel);
  const item = grp.userData.item;
  const wall = V.payload.room.walls.find((w) => w.id === item.wall);
  const u = axis === "x" ? toRender(wall.dir[0], wall.dir[1], 0)
          : axis === "y" ? toRender(wall.normal[0], wall.normal[1], 0)
          : new THREE.Vector3(0, 0, 1);   // render frame: the cursor's ray is
  V.handles.updateMatrixWorld(true);
  raycaster.setFromCamera(ndcOf(e), V.camera);
  const hit = raycaster.intersectObjects(V.handles.children, true)[0];
  const P0 = hit ? hit.point.clone() : V.handles.children[0].position.clone();
  const d = {number: item.number, axis: axis, u: u, P0: P0, grp: grp, item: item, wall: wall,
             from: {x: item.x, z: item.z, y: item.y || 0}, at: {x: item.x, z: item.z, y: item.y || 0},
             model: null, last: null, released: false, moved: false, reason: ""};
  V.dragging = d;
  V.controls.enabled = false;                    // the camera stays put while a handle moves
  window.addEventListener("pointermove", onMoveDrag);
  window.addEventListener("pointerup", endMoveDrag);
  window.addEventListener("pointercancel", endMoveDrag);
  status(`moving ${item.number} …`);
  // listen first, THEN ask: the model may land after the pointer has let go
  Promise.resolve(V.hooks.dragModel ? V.hooks.dragModel(item.number) : null).then((model) => {
    if (V.dragging !== d && !d.released) return;          // superseded by a newer press
    if (!model || !model.ok) { d.moved = false; finishMove(d, true); return; }
    d.model = model;
    if (d.last) moveDrag(d, d.last);
    if (d.released) finishMove(d, false);
  });
}

function onMoveDrag(e) {
  const d = V.dragging;
  if (!d) return;
  if (!d.model) { d.last = {clientX: e.clientX, clientY: e.clientY}; return; }
  if (d.attach) moveAttach(d, e); else moveDrag(d, e);
}

// The attached panel's drag: the same shape as the room's — one request on the
// press (`attachModel`, the server's snap targets off the carcass faces and
// edges), listening before it lands, the nearest candidate within tolerance,
// and the drop handed to index.html (`attachDrop`), which asks the server for
// the offsets to write. Nothing here works out an offset: the pointer is
// projected onto the axis (camera maths) and a candidate the engine named is
// taken, or the pointer's own millimetre when none is near.
function startAttachMove(e, axis) {
  const grp = V.groups.get(V.sel);
  const item = grp.userData.item;
  const u = axis === "x" ? toRender(1, 0, 0) : axis === "y" ? toRender(0, -1, 0)
          : new THREE.Vector3(0, 0, 1);
  V.handles.updateMatrixWorld(true);
  raycaster.setFromCamera(ndcOf(e), V.camera);
  const hit = raycaster.intersectObjects(V.handles.children, true)[0];
  const P0 = hit ? hit.point.clone() : V.handles.children[0].position.clone();
  const d = {attach: true, number: item.number, axis: axis, u: u, P0: P0, grp: grp, item: item,
             from: {...item.at}, at: {...item.at}, model: null, last: null, released: false,
             moved: false, reason: ""};
  V.dragging = d;
  V.controls.enabled = false;
  window.addEventListener("pointermove", onMoveDrag);
  window.addEventListener("pointerup", endMoveDrag);
  window.addEventListener("pointercancel", endMoveDrag);
  status(`moving panel ${item.number} on cabinet ${item.attached} …`);
  Promise.resolve(V.hooks.attachModel ? V.hooks.attachModel(item.number) : null).then((model) => {
    if (V.dragging !== d && !d.released) return;
    if (!model || !model.ok) { d.moved = false; finishMove(d, true); return; }
    d.model = model;
    d.from = {...model.at};
    d.at = {...model.at};
    if (d.last) moveAttach(d, d.last);
    if (d.released) finishMove(d, false);
  });
}

function moveAttach(d, e) {
  const t = axisParam(e, d.P0, d.u);
  if (t === null) return;
  const m = d.model;
  d.moved = true;
  const v0 = d.from[d.axis] + t;
  const snap = nearestSnap(v0, m[d.axis] || [], (c) => c.v, m.tolerance, null);
  d.at[d.axis] = snap ? snap.value : Math.round(v0);
  d.reason = snap ? snap.why : "";
  // the preview: the panel's group moved by the difference, in the room frame
  const dx = d.at.x - d.from.x, dy = d.at.y - d.from.y, dz = d.at.z - d.from.z;
  d.grp.position.set(dx, -dy, dz);                  // at_y runs back: -y in the room frame
  shadowsDirty();
  if (V.handles) V.handles.position.copy(toRender(dx, -dy, dz));
  status(`panel ${d.item.number}: at_${d.axis} ${d.at[d.axis]} mm${d.reason ? " · " + d.reason : ""}`);
  requestRender();
}

function nearestSnap(value, cands, get, tol, span) {
  let best = null;
  for (const c of cands) {
    const v = get(c);
    if (v === null || v === undefined) continue;
    const dist = Math.abs(v - value);
    if (dist > tol) continue;
    // ties: the candidate whose neighbour is nearest along the wall (0 for a
    // wall-wide datum), the plan's and the elevation's rule
    const gap = (c.x0 !== undefined && c.x0 !== null && span)
      ? Math.max(0, c.x0 - span[1], span[0] - c.x1) : 0;
    if (!best || dist < best.dist - 1e-9 || (Math.abs(dist - best.dist) < 1e-9 && gap < best.gap)) {
      best = {value: v, why: c.why, dist: dist, gap: gap};
    }
  }
  return best;
}

function moveDrag(d, e) {
  const t = axisParam(e, d.P0, d.u);
  if (t === null) return;
  const m = d.model;
  const wallModel = m.walls[d.wall.id];
  const tol = m.tolerance;
  const width = m.width;
  d.moved = true;
  let reason = "";
  if (d.axis === "x") {
    let x = d.from.x + t;
    x = Math.max(0, Math.min(wallModel.max_x, x));
    const snap = nearestSnap(x, wallModel.snaps, (c) => c.x, tol, null);
    if (snap) { x = snap.value; reason = snap.why; }
    d.at.x = Math.round(x);
  } else if (d.axis === "y") {
    let y = Math.max(0, d.from.y + t);
    const span = [d.at.x, d.at.x + width];
    const snap = nearestSnap(y, wallModel.y_snaps || [], (c) => c.y, tol, span);
    if (snap) { y = snap.value; reason = snap.why; }
    d.at.y = Math.round(y);
  } else {
    // the pointer moves the UNDERSIDE; Placement.z is 0 on the floor (the
    // carcass then stands on its legs, leg_lift up) and the underside above it
    const lift = m.leg_lift || 0;
    const under0 = d.from.z > 0 ? d.from.z : lift;
    let under = under0 + t;
    const span = [d.at.x, d.at.x + width];
    const cands = (wallModel.z_snaps || []).filter((c) => {
      if (c.x0 !== undefined && c.x0 !== null && (c.x1 <= span[0] || c.x0 >= span[1])) return false;
      if (c.not_x0 !== undefined && c.not_x0 !== null && !(c.not_x1 <= span[0] || c.not_x0 >= span[1])) return false;
      return true;
    });
    const snap = nearestSnap(under, cands, (c) => (c.z > 0 ? c.z : lift), tol, span);
    let z;
    if (snap) { under = snap.value; z = snap.value <= lift ? 0 : snap.value; reason = snap.why; }
    else z = under <= lift ? 0 : Math.round(under);
    if (m.max_z !== null && m.max_z !== undefined) z = Math.min(z, m.max_z);
    d.at.z = Math.max(0, z);
  }
  d.reason = reason;
  // move the group by the world difference from where it stands
  const dx = d.at.x - d.from.x, dy = d.at.y - d.from.y;
  const lift = m.leg_lift || 0;
  const zNow = d.at.z > 0 ? d.at.z : lift, zWas = d.from.z > 0 ? d.from.z : lift;
  const along = new THREE.Vector3(d.wall.dir[0], d.wall.dir[1], 0).multiplyScalar(dx);
  const out = new THREE.Vector3(d.wall.normal[0], d.wall.normal[1], 0).multiplyScalar(dy);
  d.grp.position.copy(along.add(out).setZ(zNow - zWas));              // room frame, in the root
  attachedGroups(d.number).forEach((g) => g.position.copy(d.grp.position));   // they move with it
  const contact = contactOf(d.number);
  if (contact && !contact.userData.rest) contact.userData.rest = contact.position.clone();
  if (contact) contact.position.copy(contact.userData.rest).add(new THREE.Vector3(d.grp.position.x, d.grp.position.y, 0));
  shadowsDirty();
  if (V.handles) V.handles.position.copy(toRender(d.grp.position.x, d.grp.position.y, d.grp.position.z));
  const fig = d.axis === "x" ? `x ${d.at.x}` : d.axis === "y" ? `y ${d.at.y}` : `z ${d.at.z}`;
  status(`${d.item.number}: ${fig} mm${reason ? " · " + reason : ""}`);
  requestRender();
}

// The groups of the panels attached to a cabinet (28 September 2026): they are
// carried along in the preview of its drag, and the drop's compute places them.
function attachedGroups(number) {
  const out = [];
  if (!V.payload) return out;
  V.payload.items.forEach((it) => {
    if (it.attached === number) {
      const g = V.groups.get(it.number);
      if (g) out.push(g);
    }
  });
  return out;
}

function endMoveDrag() {
  const d = V.dragging;
  if (!d) return;
  d.released = true;
  if (!d.model) return;                          // the model is still on its way: replayed when it lands
  finishMove(d, false);
}

function finishMove(d, cancelled) {
  if (V.dragging === d) V.dragging = null;
  window.removeEventListener("pointermove", onMoveDrag);
  window.removeEventListener("pointerup", endMoveDrag);
  window.removeEventListener("pointercancel", endMoveDrag);
  V.controls.enabled = true;
  d.grp.position.set(0, 0, 0);
  attachedGroups(d.number).forEach((g) => g.position.set(0, 0, 0));
  const contact = contactOf(d.number);
  if (contact && contact.userData.rest) contact.position.copy(contact.userData.rest);
  shadowsDirty();
  if (V.handles) V.handles.position.set(0, 0, 0);
  const changed = d.at.x !== d.from.x || d.at.z !== d.from.z || d.at.y !== d.from.y;
  if (cancelled || !d.moved || !changed) { status(V.hint); requestRender(); return; }
  if (d.attach) {
    status(`panel ${d.item.number}: at_${d.axis} ${d.at[d.axis]} mm${d.reason ? " · " + d.reason : ""}`);
    if (V.hooks.attachDrop) V.hooks.attachDrop(d.item.number, {...d.at});
    requestRender();
    return;
  }
  status(`${d.item.number} moved to ${d.axis} ${d.at[d.axis]} mm${d.reason ? " · " + d.reason : ""}`);
  if (V.hooks.drop) V.hooks.drop(d.item.number, {x: d.at.x, z: d.at.z, y: d.item.panel ? d.at.y : undefined});
  requestRender();
}

function cancelDrag() {
  const d = V.dragging;
  if (!d) return;
  d.at = {...d.from};
  finishMove(d, true);
  status(`${d.item.number}: move cancelled`);
}

/* ---------- the interface index.html uses ---------------------------------------- */

function mount(els, hooks) {
  V.els = els;
  V.hooks = hooks || {};
  const el = els.view;
  el.innerHTML = "";
  V.note = h("div", {class: "v3dnote"});
  V.note.hidden = true;
  if (!webglAvailable()) {
    V.note.textContent = "3D needs WebGL, which this machine's graphics driver does not provide.";
    V.note.hidden = false;
    el.appendChild(V.note);
    return false;
  }
  try {
    V.renderer = makeRenderer();
  } catch (err) {
    V.note.textContent = "3D could not start: " + (err && err.message || err);
    V.note.hidden = false;
    el.appendChild(V.note);
    return false;
  }
  el.appendChild(V.renderer.domElement);
  el.appendChild(V.note);
  V.scene = new THREE.Scene();
  V.root = new THREE.Group();
  V.root.scale.set(1, -1, 1);              // the room frame, drawn true (see toRender)
  V.scene.add(V.root);
  V.env = makeEnvironment(V.renderer, V.scene);
  V.background = makeBackground();
  V.scene.background = V.background;
  V.scene.add(makeLights());
  V.grid = makeGrid(6000);
  V.scene.add(V.grid);
  const cams = makeCameras(Math.max(el.clientWidth, 1) / Math.max(el.clientHeight, 1));
  V.persp = cams.persp;
  V.ortho = cams.ortho;
  V.camera = V.persp;
  try { V.aoPass = makeAO(); } catch (err) { V.aoPass = null; V.ao = false; }
  // on by default where a graphics card draws it; a software renderer (no
  // GPU: SwiftShader, llvmpipe, Windows' basic driver) takes about a second a
  // frame over it, so there it starts off and the toggle turns it on
  if (softwareRendered()) V.ao = false;
  V.clock = new THREE.Clock();
  V.cP = makeControls(V.persp, V.renderer.domElement, false);
  V.cO = makeControls(V.ortho, V.renderer.domElement, true);
  V.controls = V.cP;
  V.cP.setLookAt(-3000, -4500, 3200, 2000, 1500, 900, false);
  V.pivotDot = new THREE.Mesh(new THREE.SphereGeometry(1, 12, 8),
    new THREE.MeshBasicMaterial({color: PAPER.pivot, depthTest: false, transparent: true, opacity: 0.85,
                                 toneMapped: false}));
  V.pivotDot.renderOrder = 10;
  V.pivotDot.userData.noAO = true;
  V.pivotDot.visible = false;
  V.scene.add(V.pivotDot);
  V.observer = new ResizeObserver(() => resize());
  V.observer.observe(el);
  const canvas = V.renderer.domElement;
  canvas.addEventListener("pointerdown", onPointerDown, true);
  canvas.addEventListener("pointerup", onPointerUp);
  window.addEventListener("pointerup", () => { V.pressed = false; });
  window.addEventListener("pointercancel", () => { V.pressed = false; });
  // The canvas owns the wheel: it is a full-height viewport, so there is no
  // page to scroll behind it. Zoom is this module's own (see `onWheel`).
  canvas.addEventListener("wheel", onWheel, {passive: false, capture: true});
  canvas.addEventListener("pointermove", onPointerMove);
  canvas.addEventListener("dblclick", onDblClick);
  canvas.addEventListener("contextmenu", (e) => e.preventDefault());
  canvas.addEventListener("pointerenter", () => { V.pointerOver = true; });
  canvas.addEventListener("pointerleave", () => { V.pointerOver = false; if (V.hover) { V.hover = null; applySelection(); status(V.hint); requestRender(); } });
  window.addEventListener("keydown", onKey);
  window.addEventListener("keyup", onKey);
  V.legendEl = h("div", {class: "v3dlegend", html: `<div class="hd">Boards <button class="tog" title="collapse">–</button></div><div class="rows"></div><div class="nd"></div>`});
  V.legendEl.querySelector(".tog").addEventListener("click", (e) => {
    V.legendEl.classList.toggle("closed");
    e.target.textContent = V.legendEl.classList.contains("closed") ? "+" : "–";
  });
  el.appendChild(V.legendEl);
  V.cube = makeCube();
  buildBar();
  resize();
  V.hint = "Left-drag orbits about the point pressed · right-drag pans · wheel zooms to the cursor · ? for keys";
  status(V.hint);
  return true;
}

function setVisible(on) {
  V.visible = !!on;
  if (V.visible) { resize(); requestRender(); }
  else stopLoop();
}

// A new scene from the server. Only cabinets whose hash changed are rebuilt,
// and the camera is never moved by an update — only by an explicit Fit, a
// view or a double-click; a NEW job opens at Home.
function update(payload, opts) {
  if (!V.renderer) return;
  const fresh = !!(opts && opts.fresh) || !V.payload;
  V.payload = payload;
  syncItems(payload);
  computeBBox();
  buildShell(payload);
  if (V.cube) V.cube.relabel();
  applyGhosting();
  buildOverlays();
  updateLegend();
  // a loop that opened is said in `room.closure`'s own words (ruling 2, 3 October
  // 2026): the same text the Room card and the toast show, decided on the server
  const loop = payload.room && payload.room.closure && payload.room.closure.miss
    ? payload.room.closure.text : "";
  say([payload.banner || (payload.room && !payload.ceiling_measured
    ? "The ceiling is not measured: the walls stop a drawing margin above the tallest item." : ""), loop]
    .filter(Boolean).join(" · "));
  if (fresh) { V.hidden.clear(); if (V.openFor) V.openFor.clear(); setProjection(false, false); viewHome(false); }
  applyFronts(true);                       // rebuilt parts take the open/closed state as it stands
  buildList();
  if (V.hooks.updated) V.hooks.updated(payload);
  shadowsDirty();
  requestRender();
}

// index.html tells the view the one selection; nothing is decided here
function select(number) {
  if (number === V.sel) { applySelection(); updateList(); requestRender(); return; }
  V.sel = number;
  V.picked = null;                           // another item: the picked part was the old one's
  applyGhosting();
  updateBar();
  updateList();
  if (number === null) showCard(null, null);
}

function setLayers(list) {
  V.layers = list === null ? null : new Set(list);
  applyGhosting();
  updateBar();
}

// and the one isolate — mirrored here, never decided here
function isolate(number) {
  if (number === V.isolate) return;
  setIsolate(number, true);
}

function flyTo(number) {
  const grp = V.groups.get(number);
  if (grp) fitTo(new THREE.Box3().setFromObject(grp), true);
}

// For the browser checks: is the camera still, where is an item, and how is a
// part drawn. None of it is read by the view itself.
function idle() { return !V.running && !V.animating; }

function bounds(number) {
  const grp = V.groups.get(number);
  if (!grp) return null;
  const b = new THREE.Box3().setFromObject(grp);                // render frame
  return {min: [b.min.x, -b.max.y, b.min.z], max: [b.max.x, -b.min.y, b.max.z]};   // room frame
}

function partInfo(id) {
  for (const grp of [...V.groups.values(), V.roomParts].filter(Boolean)) {
    for (const m of grp.children) {
      if (m.userData.id !== id) continue;
      const mat = m.material[1];
      const ol = m.userData.outline;
      // `colour` is the board's own (its swatch off the server); a board drawn
      // in its picture multiplies the picture by white, which is `tint`
      return {colour: mat.userData.colour !== undefined ? String(mat.userData.colour).toLowerCase()
                                                        : "#" + mat.color.getHexString(),
              tint: "#" + mat.color.getHexString(), map: !!mat.map,
              opacity: mat.opacity, ghost: !!m.userData.ghost, visible: m.visible && grp.visible,
              edges: !!(m.userData.edges && m.userData.edges.visible),
              outline: ol && ol.visible ? m.userData.outlineKind : null,
              outlineInfo: ol ? {segments: ol.geometry.instanceCount, depthTest: ol.material.depthTest,
                                 width: ol.material.linewidth, res: ol.material.resolution.toArray()} : null,
              rest: m.userData.rest ? [m.userData.rest.position.toArray(), m.position.toArray()] : null,
              rotation: m.rotation.z};
    }
  }
  return null;
}

function debugCam() {
  const c = V.controls;
  const fo = c.getFocalOffset(new THREE.Vector3());
  return {target: c.getTarget(new THREE.Vector3()).toArray(), distance: c.distance,
          focal: fo.toArray(), cam: V.camera.position.toArray(), fov: V.persp.fov,
          polar: c.polarAngle, azimuth: c.azimuthAngle, zoom: V.camera.zoom, running: V.running,
          active: c.active};
}

function pickHandleAt(clientX, clientY) {
  if (!V.handles) return {axis: null, handles: []};
  V.handles.updateMatrixWorld(true);
  const axis = pickHandle({clientX, clientY});
  const boxes = V.handles.children.map((g) => {
    const b = new THREE.Box3().setFromObject(g);
    return {axis: g.userData.handle, min: b.min.toArray(), max: b.max.toArray(),
            meshes: g.children.length, visible: g.visible};
  });
  raycaster.setFromCamera(ndcOf({clientX, clientY}), V.camera);
  const hits = raycaster.intersectObjects(V.handles.children, true).map((hh) => [hh.object.userData.handle, hh.distance]);
  return {axis, handles: boxes, hits, ray: [raycaster.ray.origin.toArray(), raycaster.ray.direction.toArray()]};
}

function dragInfo() {
  const d = V.dragging;
  const hs = V.handles ? V.handles.children.map((g) => ({axis: g.userData.handle, origin: toRoom(g.position),
                                                         dir: toRoom(g.userData.dir)})) : [];
  return {dragging: !!d, axis: d ? d.axis : null, at: d ? d.at : null, reason: d ? d.reason : "",
          hasModel: !!(d && d.model), handles: hs};
}

function overlayInfo() {
  if (!V.overlays) return {swings: 0, clashes: 0, overlaps: 0};
  let swings = 0, clashes = 0, overlaps = 0;
  V.overlays.children.forEach((o) => {
    if (o.userData.overlap) overlaps += 1;
    else if (o.isMesh) { swings += 1; if (o.userData.clash) clashes += 1; }
  });
  return {swings, clashes, overlaps};
}

function groupIds() {
  const out = {};
  for (const [n, grp] of V.groups) out[n] = grp.uuid;
  return out;
}

function debugShell() {
  return (V.wallMeshes || []).map((m) => {
    const b = new THREE.Box3().setFromObject(m);
    return {wall: m.userData.wall, visible: m.visible, side: m.material.side,
            min: b.min.toArray(), max: b.max.toArray(), pos: m.position.toArray(),
            det: m.matrixWorld.determinant(), verts: m.geometry.attributes.position.count};
  });
}

function memory() {
  const m = V.renderer ? V.renderer.info.memory : {geometries: 0, textures: 0};
  // outlines: the selection / hover fat-line geometries in existence, built
  // lazily and kept while their part lives — a transient the checks take out
  let outlines = 0, shown = 0;
  for (const grp of [...V.groups.values(), V.roomParts].filter(Boolean)) {
    for (const mesh of grp.children) if (mesh.userData.outline) { outlines += 1; if (mesh.userData.outline.visible) shown += 1; }
  }
  return {geometries: m.geometries, textures: m.textures, groups: V.groups.size, pickables: V.pickables.length,
          outlines: outlines, outlinesShown: shown, hover: V.hover ? V.hover.number : null, sel: V.sel};
}

function state() {
  return {sel: V.sel, isolate: V.isolate, layers: V.layers ? [...V.layers] : null, display: V.display,
          walls: V.walls, labels: V.labels, ortho: V.ortho_on, fronts: V.frontsOpen, runners: V.runners,
          clearances: V.clearances, hidden: [...V.hidden], picked: V.picked || null,
          ao: aoActive(), grid: !!V.gridOn[V.display]};
}

function camera() {
  const p = V.controls.getPosition(new THREE.Vector3());
  const t = V.controls.getTarget(new THREE.Vector3());
  return {position: toRoom(p), target: toRoom(t), zoom: V.camera.zoom, ortho: V.ortho_on};
}

// Screen position of a world point — for the checks, which want to know that
// a corner stayed under the cursor.
function project(x, y, z) {
  const r = V.renderer.domElement.getBoundingClientRect();
  const p = toRender(x, y, z).project(V.camera);
  return {x: (p.x + 1) / 2 * r.width, y: (1 - p.y) / 2 * r.height, depth: p.z};
}

function unproject(clientX, clientY) {
  const hit = pick({clientX, clientY}, true);
  return hit ? toRoom(hit.point) : null;
}

// Where a point on the canvas falls in the room, for a drop from the unplaced
// list (UI restructure, 28 September 2026): the wall under the cursor, how far
// along it and how high — or, over the floor or nothing, the NEAREST wall to
// the point on the floor, at floor level. Camera maths and a projection onto
// the wall's line, the plan's `project` in 3D; no dimension of the model.
function wallAt(clientX, clientY) {
  const room = V.payload && V.payload.room;
  if (!room || !V.renderer) return null;
  const r = V.renderer.domElement.getBoundingClientRect();
  if (clientX < r.left || clientX > r.right || clientY < r.top || clientY > r.bottom) return null;
  const ev = {clientX, clientY};
  const along = (w, x, y) => (x - w.start[0]) * w.dir[0] + (y - w.start[1]) * w.dir[1];
  const hit = pick(ev, true);
  if (hit && hit.object.userData.kind === "wall") {
    const [x, y, z] = toRoom(hit.point);
    const w = room.walls.find((k) => k.id === hit.object.userData.wall);
    if (w) return {wall: w.id, along: along(w, x, y), up: z, floor: false};
  }
  // otherwise the floor under the cursor: where the ray meets z = 0
  raycaster.setFromCamera(ndcOf(ev), V.camera);
  const ray = raycaster.ray;
  if (Math.abs(ray.direction.z) < 1e-9) return null;
  const k = -ray.origin.z / ray.direction.z;
  if (k < 0) return null;
  const [x, y] = toRoom(ray.at(k, new THREE.Vector3()));
  let best = null;
  for (const w of room.walls) {
    const a = Math.max(0, Math.min(w.length, along(w, x, y)));
    const px = w.start[0] + w.dir[0] * a, py = w.start[1] + w.dir[1] * a;
    const dist = Math.hypot(x - px, y - py);
    if (!best || dist < best.dist) best = {wall: w.id, along: along(w, x, y), up: 0, floor: true, dist: dist};
  }
  return best;
}

// The colour on screen at a canvas point, for the look check: drawn, then read
// straight off the drawing buffer (which is not preserved between frames).
function pixel(clientX, clientY) {
  if (!V.renderer) return null;
  draw();
  const gl = V.renderer.getContext();
  const r = V.renderer.domElement.getBoundingClientRect();
  const pr = V.renderer.getPixelRatio();
  const x = Math.round((clientX - r.left) * pr), y = Math.round((r.bottom - clientY) * pr);
  const buf = new Uint8Array(4);
  gl.readPixels(x, y, 1, 1, gl.RGBA, gl.UNSIGNED_BYTE, buf);
  return [buf[0], buf[1], buf[2]];
}

// The MEAN colour drawn over a rectangle of the canvas, for the look check on
// a board drawn in its picture: one pixel of a picture says nothing.
function meanPixel(x0, y0, x1, y1) {
  if (!V.renderer) return null;
  draw();
  const gl = V.renderer.getContext();
  const r = V.renderer.domElement.getBoundingClientRect();
  const pr = V.renderer.getPixelRatio();
  const ax = Math.round((Math.min(x0, x1) - r.left) * pr), bx = Math.round((Math.max(x0, x1) - r.left) * pr);
  const ay = Math.round((r.bottom - Math.max(y0, y1)) * pr), by = Math.round((r.bottom - Math.min(y0, y1)) * pr);
  const w = Math.max(bx - ax, 1), hh = Math.max(by - ay, 1);
  const buf = new Uint8Array(w * hh * 4);
  gl.readPixels(ax, ay, w, hh, gl.RGBA, gl.UNSIGNED_BYTE, buf);
  const sum = [0, 0, 0];
  for (let i = 0; i < buf.length; i += 4) { sum[0] += buf[i]; sum[1] += buf[i + 1]; sum[2] += buf[i + 2]; }
  return sum.map((v) => Math.round(v / (w * hh) * 10) / 10);
}

// Try a lighting figure in the running view (the tuning harness only: browser
// state, written nowhere): exposure, environment, key, and the environment's
// turn about X in radians.
function tune(o) {
  if (!V.renderer) return null;
  if (o.exposure !== undefined) V.renderer.toneMappingExposure = o.exposure;
  if (o.environment !== undefined) V.scene.environmentIntensity = o.environment;
  if (o.elevation !== undefined) LOOK.keyFrom.elevation = o.elevation;
  if (o.key !== undefined) V.keyFront = o.key;
  if (o.key !== undefined || o.elevation !== undefined) fitKey();
  if (o.ao !== undefined) { V.ao = !!o.ao; updateBar(); }
  if (o.aoParams && V.aoPass) V.aoPass.updateGtaoMaterial(o.aoParams);
  if (o.aoPasses !== undefined) V.aoPasses = o.aoPasses;
  if (o.pdParams && V.aoPass) V.aoPass.updatePdMaterial(o.pdParams);
  if (o.shadows !== undefined && V.key) { V.key.castShadow = !!o.shadows; shadowsDirty(); }
  if (o.envEuler) V.scene.environmentRotation.set(o.envEuler[0], o.envEuler[1], o.envEuler[2]);
  requestRender();
  return look();
}

// The figures the look is built on, for the report and the checks.
function look() {
  return {exposure: V.renderer ? V.renderer.toneMappingExposure : LOOK.exposure,
          environment: V.scene ? V.scene.environmentIntensity : LOOK.environment,
          key: V.keyFront !== undefined ? V.keyFront : LOOK.key, keyIntensity: V.key ? V.key.intensity : null,
          envRot: V.scene ? V.scene.environmentRotation.toArray().slice(0, 3) : null, board: LOOK.board,
          edge: LOOK.edge, outline: LOOK.outline, materials: V.materials.size,
          keyFrom: LOOK.keyFrom, keyDir: V.keyDir ? toRoom(V.keyDir) : null, shadow: LOOK.shadow,
          shadowMap: V.renderer ? {type: V.renderer.shadowMap.type, auto: V.renderer.shadowMap.autoUpdate,
                                   due: V.renderer.shadowMap.needsUpdate} : null,
          ao: LOOK.ao, aoOn: aoActive(), software: softwareRendered(),
          pictures: [...V.pictures].map(([b, r]) => [b, !!r.tex, r.failed]),
          toneMapping: V.renderer ? V.renderer.toneMapping : null};
}

// How long one frame takes, for the report on AO (the checks only): `n`
// frames drawn one after another, each forced through by reading a pixel
// back, in milliseconds a frame.
function frameTime(n) {
  if (!V.renderer) return null;
  const gl = V.renderer.getContext();
  const buf = new Uint8Array(4);
  draw();
  gl.readPixels(0, 0, 1, 1, gl.RGBA, gl.UNSIGNED_BYTE, buf);
  const t0 = performance.now();
  for (let i = 0; i < n; i++) { draw(); gl.readPixels(0, 0, 1, 1, gl.RGBA, gl.UNSIGNED_BYTE, buf); }
  return (performance.now() - t0) / n;
}

function dispose() {
  stopLoop();
  if (V.observer) V.observer.disconnect();
  window.removeEventListener("keydown", onKey);
  window.removeEventListener("keyup", onKey);
  for (const [n, grp] of [...V.groups]) { V.root.remove(grp); disposeObject(grp); V.groups.delete(n); }
  if (V.roomParts) disposeObject(V.roomParts);
  if (V.shell) disposeObject(V.shell);
  dropLooks({}, true);
  if (V.aoPass) V.aoPass.dispose();
  if (V.tileTex) V.tileTex.dispose();
  if (V.contacts) V.contacts.children.forEach((m) => { m.geometry.dispose(); m.material.alphaMap.dispose(); m.material.dispose(); });
  if (V.env) V.env.dispose();
  if (V.background) V.background.dispose();
  if (V.cube) V.cube.dispose();
  if (V.cP) V.cP.dispose();
  if (V.cO) V.cO.dispose();
  if (V.renderer) V.renderer.dispose();
  if (V.els.view) V.els.view.innerHTML = "";
  V.renderer = V.scene = V.camera = V.controls = null;
}

  return {mount, setVisible, update, select, setLayers, isolate, flyTo, idle, bounds, partInfo, debugCam, pickHandleAt, dragInfo, overlayInfo, groupIds, debugShell, memory, state, camera, project, unproject, dispose, resize, fitAll, viewHome, viewTop, viewWall, setProjection, setDisplay, wallAt, pixel, meanPixel, look, tune, frameTime};
}
