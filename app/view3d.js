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

CameraControls.install({THREE: THREE});

/* ---------- the view's own colours ------------------------------------------
   PAPER is the ONLY place a colour literal may appear in this file
   (tools/check_colour.py holds it to that). None of these is a board: every
   board is drawn in the look the server sends, off render.board_look.        */
const PAPER = {
  bg: 0xeef0ec,          // the viewport
  floor: 0xe4e6e0,       // the floor slab
  wall: 0xf4f4f1,        // wall planes
  ceiling: 0xf7f7f4,
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
  white: 0xffffff,       // lights
  ground: 0x8f8f86,      // hemisphere light, from below
  cubeGround: 0x999999,
  none: 0x000000,        // emissive off, and a transparent clear
};

const PIXEL_RATIO_CAP = 2;
const CLICK_PX = 4;          // press and release within this is a click
const GHOST = 0.30;          // the house opacity for "not the focus"
const XRAY = 0.35;
const FLY_MS = 300;

/* ---------- state ------------------------------------------------------------ */

const V = {
  els: {},             // view, bar, list, dock, status, from index.html
  hooks: {},           // what index.html asked to be told about
  renderer: null, scene: null, camera: null, persp: null, ortho: null,
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
  textures: new Map(), // `${board}:${rot}` -> Texture
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

/* ---------- renderer, cameras, controls -------------------------------------- */

function makeRenderer() {
  const r = new THREE.WebGLRenderer({antialias: true, alpha: false,
                                     powerPreference: "high-performance"});
  r.setPixelRatio(Math.min(window.devicePixelRatio || 1, PIXEL_RATIO_CAP));
  r.setClearColor(PAPER.bg, 1);
  r.outputColorSpace = THREE.SRGBColorSpace;
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

function render() {
  if (!V.renderer || !V.visible || V.lost) return;
  V.renderer.render(V.scene, V.camera);
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
  requestRender();
}

/* ---------- lights and grid ------------------------------------------------- */

function makeLights() {
  const g = new THREE.Group();
  const hemi = new THREE.HemisphereLight(PAPER.white, PAPER.ground, 1.15);
  hemi.position.set(0, 0, 1);
  const key = new THREE.DirectionalLight(PAPER.white, 1.0);
  key.position.set(-0.5, -0.8, 1.0);
  g.add(hemi, key);
  return g;
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
    gh.material.opacity = gh === major ? 0.55 : 0.35;
    gh.material.depthWrite = false;
    g.add(gh);
  }
  g.position.z = -1;
  return g;
}

/* ---------- looks: materials and textures ------------------------------------ */

// A texture for one board turned by `rot` radians, made once and shared by
// every part that needs it. The picture is asked for at /pictures/<name>; a
// picture that fails to load leaves the part its colour.
function textureFor(board, rot) {
  const look = V.payload.looks[board];
  if (!look || !look.picture) return null;
  const key = board + ":" + Math.round(rot * 1000);
  if (V.textures.has(key)) return V.textures.get(key);
  const tex = new THREE.TextureLoader().load(look.picture,
    () => requestRender(),
    undefined,
    () => { V.textures.delete(key); });
  tex.wrapS = tex.wrapT = THREE.RepeatWrapping;
  tex.colorSpace = THREE.SRGBColorSpace;
  const tile = look.tile_mm || 160;
  tex.repeat.set(1 / tile, 1 / tile);
  tex.rotation = rot;
  tex.anisotropy = 4;
  V.textures.set(key, tex);
  return tex;
}

// The two materials a part needs: one for its caps (the faces in the plan
// plane), one for its side walls. ExtrudeGeometry lays the caps' UV in world
// XY and the walls' V up the extrusion, so the picture's vertical (its grain)
// is turned onto the part's `grain` vector: 0 or 90 degrees, as the elevation
// does it, never an angle worked out here from a photograph.
function materialsFor(part) {
  const look = V.payload.looks[part.board] || {colour: PAPER.fallback, grain: false, picture: ""};
  const base = {color: hex(look.colour), roughness: 0.82, metalness: 0.0};
  const cap = new THREE.MeshStandardMaterial(base);
  const side = new THREE.MeshStandardMaterial(base);
  if (look.picture && part.grain) {
    const [gx, gy, gz] = part.grain;
    const horizontal = Math.abs(gz) < 0.5 && (gx || gy);
    // caps: lay the picture's V along the plan grain vector
    const capRot = horizontal ? Math.atan2(gy, gx) - Math.PI / 2 : 0;
    const capTex = textureFor(part.board, capRot);
    // walls: V runs up; a horizontal grain turns the tile on its side
    const sideTex = textureFor(part.board, horizontal ? Math.PI / 2 : 0);
    if (capTex) cap.map = capTex;
    if (sideTex) side.map = sideTex;
  }
  // Fronts sit exactly on the carcass front face, and coplanar faces flicker:
  // pull a front towards the camera with a polygon offset, never by moving it.
  if (part.role === "door" || part.role === "drawer" || part.role === "blind" || part.role === "panel") {
    for (const m of [cap, side]) {
      m.polygonOffset = true;
      m.polygonOffsetFactor = -1;
      m.polygonOffsetUnits = -2;
    }
  }
  return [cap, side];
}

function applyDisplay(mesh) {
  const xray = V.display === "xray";
  for (const m of mesh.material) {
    m.transparent = xray || mesh.userData.ghost;
    m.opacity = xray ? XRAY : (mesh.userData.ghost ? GHOST : 1);
    m.depthWrite = !xray;
    m.needsUpdate = true;
  }
  if (mesh.userData.edges) {
    mesh.userData.edges.visible = V.display !== "shaded";
    mesh.userData.edges.material.opacity = mesh.userData.ghost ? GHOST : 1;
    mesh.userData.edges.material.transparent = true;
  }
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

function edgeColourFor(role) {
  if (role === "door" || role === "drawer" || role === "blind" || role === "panel") return PAPER.edgeFront;
  return PAPER.edgeCarcass;
}

function buildPart(part) {
  const geom = extrude(part.outline, part.z0, part.z1);
  const mesh = new THREE.Mesh(geom, materialsFor(part));
  mesh.userData = {part: part, number: part.cab, id: part.id, ghost: false};
  const edges = new THREE.LineSegments(
    new THREE.EdgesGeometry(geom, 20),
    new THREE.LineBasicMaterial({color: edgeColourFor(part.role), transparent: true, opacity: 1}));
  edges.userData.base = edgeColourFor(part.role);
  mesh.add(edges);
  mesh.userData.edges = edges;
  // a door rotates about its hinge, a drawer face slides out: keep the rest
  // position so an animation can come back to it
  mesh.userData.rest = {position: mesh.position.clone(), quaternion: mesh.quaternion.clone()};
  applyDisplay(mesh);
  return mesh;
}

function disposeObject(obj) {
  obj.traverse((o) => {
    if (o.geometry) o.geometry.dispose();
    if (o.material) {
      const mats = Array.isArray(o.material) ? o.material : [o.material];
      // textures are shared and live in the cache; only the materials go
      mats.forEach((m) => m.dispose());
    }
  });
}

function buildItem(item) {
  const grp = new THREE.Group();
  grp.userData = {number: item.number, hash: item.hash, item: item};
  for (const part of item.parts) grp.add(buildPart(part));
  return grp;
}

// Rebuild only the cabinets whose hash changed; dispose what they replace.
function syncItems(payload) {
  const seen = new Set();
  for (const item of payload.items) {
    seen.add(item.number);
    const old = V.groups.get(item.number);
    if (old && old.userData.hash === item.hash) { old.userData.item = item; continue; }
    if (old) { V.scene.remove(old); disposeObject(old); V.groups.delete(item.number); }
    if (!item.parts.length) continue;
    const grp = buildItem(item);
    V.scene.add(grp);
    V.groups.set(item.number, grp);
  }
  for (const [n, grp] of [...V.groups]) {
    if (!seen.has(n)) { V.scene.remove(grp); disposeObject(grp); V.groups.delete(n); }
  }
  // plinths and fillers: few, cheap — rebuilt whenever their list changes
  const key = JSON.stringify(payload.room_parts.map((q) => q.id + q.z1 + q.outline.join(",")));
  if (!V.roomParts || V.roomParts.userData.key !== key) {
    if (V.roomParts) { V.scene.remove(V.roomParts); disposeObject(V.roomParts); }
    V.roomParts = new THREE.Group();
    V.roomParts.userData = {key: key, number: 0};
    for (const q of payload.room_parts) V.roomParts.add(buildPart(q));
    V.scene.add(V.roomParts);
  }
  // drop textures for boards no longer in the job
  for (const [k, tex] of [...V.textures]) {
    if (!payload.looks[k.split(":")[0]]) { tex.dispose(); V.textures.delete(k); }
  }
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
  const mat = new THREE.MeshStandardMaterial({color: PAPER.wall, roughness: 0.95, metalness: 0,
                                              side: THREE.BackSide});
  const mesh = new THREE.Mesh(geom, mat);
  const dir = new THREE.Vector3(w.dir[0], w.dir[1], 0);
  const up = new THREE.Vector3(0, 0, 1);
  const nrm = new THREE.Vector3(-w.normal[0], -w.normal[1], 0);
  const m = new THREE.Matrix4().makeBasis(dir, up, nrm);
  m.setPosition(w.start[0], w.start[1], 0);
  mesh.applyMatrix4(m);
  mesh.userData = {wall: w.id, kind: "wall"};
  const edges = new THREE.LineSegments(new THREE.EdgesGeometry(geom, 1),
    new THREE.LineBasicMaterial({color: PAPER.edgeWall}));
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
  if (V.shell) { V.scene.remove(V.shell); disposeObject(V.shell); V.shell = null; }
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
      new THREE.MeshStandardMaterial({color: PAPER.floor, roughness: 1, metalness: 0}));
    floor.position.z = -0.5;
    floor.userData.kind = "floor";
    shell.add(floor);
    const floorEdge = new THREE.LineSegments(new THREE.EdgesGeometry(floor.geometry, 1),
      new THREE.LineBasicMaterial({color: PAPER.edgeWall}));
    shell.add(floorEdge);
    for (const w of room.walls) {
      const [mesh, edges] = wallMesh(w, room.top, room.closed);
      shell.add(mesh, edges);
      V.wallMeshes.push(mesh);
      for (const ob of obstructionMeshes(w)) { shell.add(ob); V.obstructions.push(ob); }
    }
    const ceil = new THREE.Mesh(new THREE.ShapeGeometry(floorShape),
      new THREE.MeshStandardMaterial({color: PAPER.ceiling, roughness: 1, side: THREE.BackSide}));
    ceil.position.z = room.top;
    ceil.userData.kind = "ceiling";
    ceil.visible = V.ceiling;
    V.ceilMesh = ceil;
    shell.add(ceil);
  } else {
    // no room: a plain floor under the Run
    const b = V.bbox;
    const w = Math.max(b.max.x - b.min.x, 1000) + 1200;
    const d = Math.max(b.max.y - b.min.y, 1000) + 1200;
    const floor = new THREE.Mesh(new THREE.PlaneGeometry(w, d),
      new THREE.MeshStandardMaterial({color: PAPER.floor, roughness: 1}));
    floor.position.set((b.max.x + b.min.x) / 2, (b.max.y + b.min.y) / 2, -0.5);
    floor.userData.kind = "floor";
    shell.add(floor);
  }
  V.scene.add(shell);
  V.shell = shell;
  applyWalls();
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
    for (const [x, y] of V.payload.room.floor) b.expandByPoint(new THREE.Vector3(x, y, 0));
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
  V.scene.add(V.grid);
}

function rebuildAll() {
  if (!V.payload) return;
  for (const [n, grp] of [...V.groups]) { V.scene.remove(grp); disposeObject(grp); V.groups.delete(n); }
  if (V.roomParts) { V.scene.remove(V.roomParts); disposeObject(V.roomParts); V.roomParts = null; }
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
  requestRender();
}

/* ---------- selection and hover ---------------------------------------------- */

function tintMesh(mesh, colour, strength) {
  for (const m of mesh.material) {
    m.emissive = new THREE.Color(colour || PAPER.none);
    m.emissiveIntensity = strength || 0;
    m.needsUpdate = true;
  }
  if (mesh.userData.edges) mesh.userData.edges.material.color.set(colour && strength ? colour : mesh.userData.edges.userData.base);
}

function applySelection() {
  for (const grp of V.groups.values()) {
    const selected = grp.userData.number === V.sel;
    for (const mesh of grp.children) {
      const hov = V.hover && V.hover.id === mesh.userData.id;
      if (selected) tintMesh(mesh, PAPER.accent, hov ? 0.22 : 0.14);
      else if (hov || (V.hover && V.hover.number === grp.userData.number)) tintMesh(mesh, PAPER.hover, hov ? 0.16 : 0.06);
      else tintMesh(mesh, null, 0);
    }
  }
  if (V.roomParts) {
    for (const mesh of V.roomParts.children) {
      const hov = V.hover && V.hover.id === mesh.userData.id;
      tintMesh(mesh, hov ? PAPER.hover : null, hov ? 0.16 : 0);
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
      el.hidden = false;
      shown.add(c.number);
    }
  }
  for (const [n, el] of V.labelEls) if (!shown.has(n)) el.hidden = true;
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
    g.add(new THREE.Line(geo, mat));
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
function onWheel(e) {
  e.preventDefault();
  if (!V.payload || !V.controls) return;
  const dy = e.deltaMode === 1 ? e.deltaY * 16 : e.deltaMode === 2 ? e.deltaY * 100 : e.deltaY;
  if (!dy) return;
  const s = Math.exp(Math.max(-300, Math.min(300, dy)) * 0.0011);   // > 1 zooms out
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

const ISO_DIR = new THREE.Vector3(-0.62, 0.72, 0.55);

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
  const turned = new THREE.Vector3(d.x * 0.92 - d.y * 0.39, d.x * 0.39 + d.y * 0.92, 0);
  return turned.setZ(0.7).normalize();
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
  lookFrom(new THREE.Vector3(w.normal[0], w.normal[1], 0), box, transition);
}

function wallBox(w) {
  const b = new THREE.Box3();
  const top = V.payload.room.top;
  b.expandByPoint(new THREE.Vector3(w.start[0], w.start[1], 0));
  b.expandByPoint(new THREE.Vector3(w.end[0], w.end[1], top));
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
        const dot = w.normal[0] * fx + w.normal[1] * fy;
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
  const hit = pick(e, false);
  if (hit) doSelect(hit.object.userData.number, hit.object.userData.part);
  else doSelect(null, null);
}

function onDblClick(e) {
  const hit = pick(e, false);
  if (hit && hit.object.userData.number) {
    doSelect(hit.object.userData.number, hit.object.userData.part);
    fitSelection(true);
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
  const names = {side: "Side", top: "Top", bottom: "Bottom", door: "Door leaf", drawer: "Drawer face",
                 blind: "Blind panel", panel: "Panel", back: "Backing", carcass: "Carcass (footprint only)",
                 plinth: "Plinth board", filler: "Filler"};
  const n = names[part.role] || part.role;
  if (part.role === "door" || part.role === "drawer") return `${n} ${part.index + 1}`;
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
  B.clear = h("button", {text: "Clearances", title: "C: door swings and drawer pull-outs", onclick: () => toggleClearances()});
  B.walls = h("button", {text: "Walls: auto ▾", title: "which walls are drawn"});
  B.ceiling = h("button", {text: "Ceiling", title: "draw the ceiling", onclick: () => { V.ceiling = !V.ceiling; applyWalls(); updateBar(); }});
  B.labels = h("button", {text: "Labels", title: "L: item numbers", onclick: () => { V.labels = !V.labels; updateBar(); requestRender(); }});
  B.isolate = h("button", {text: "Isolate", title: "ghost everything but the selection", onclick: () => setIsolate(V.isolate === null ? V.sel : null)});
  B.snap = h("button", {text: "Snapshot", title: "save this view as a PNG into output/<job>/", onclick: () => snapshot()});
  B.fit = h("button", {text: "Fit", title: "F: fit the selection, or everything", onclick: () => fitSelection(true)});
  B.help = h("button", {text: "?", title: "shortcuts", onclick: () => toggleHelp()});
  bar.append(B.views, B.proj, B.display, B.fit, sep(),
             B.layers.base, B.layers.wall, B.layers.tall, B.layers.panels, sep(),
             B.fronts, B.clear, B.walls, B.ceiling, B.labels, B.isolate, sep(), B.snap, B.help);
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
  menu(B.walls, () => [
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
  B.clear.classList.toggle("on", V.clearances);
  B.isolate.classList.toggle("on", V.isolate !== null);
  B.isolate.disabled = V.isolate === null && V.sel === null;
  for (const k in B.layers) B.layers[k].classList.toggle("on", V.layers === null || V.layers.has(k));
}

function setDisplay(mode) {
  V.display = mode;
  for (const grp of V.groups.values()) grp.children.forEach(applyDisplay);
  if (V.roomParts) V.roomParts.children.forEach(applyDisplay);
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
      Nothing is deleted or duplicated from a key.`});
    V.els.view.appendChild(V.helpEl);
  } else {
    V.helpEl.hidden = !V.helpEl.hidden;
  }
}

/* ---------- selection ---------------------------------------------------------- */

function doSelect(number, part) {
  V.sel = number;
  if (V.isolate !== null && number !== null) V.isolate = number;    // isolate follows the selection
  applyGhosting();
  updateBar();
  if (V.hooks.select) V.hooks.select(number, part);
  showCard(number, part);
}

function showCard(number, part) {
  if (V.hooks.card) V.hooks.card(number, part);
}

function setIsolate(number) {
  V.isolate = number === undefined ? null : number;
  applyGhosting();
  updateBar();
}

/* ---------- stubs filled in by later stages ------------------------------------ */

function toggleFronts() { V.frontsOpen = !V.frontsOpen; if (V.hooks.fronts) V.hooks.fronts(V.frontsOpen); updateBar(); }
function toggleClearances() { V.clearances = !V.clearances; buildOverlays(); updateBar(); }
function buildOverlays() {
  if (V.overlays) { V.scene.remove(V.overlays); disposeObject(V.overlays); V.overlays = null; }
  requestRender();
}
function openContextMenu(e) { if (V.hooks.context) V.hooks.context(e, pick(e, false)); }
function snapshot() { if (V.hooks.snapshot) V.hooks.snapshot(); }
function cancelDrag() {}

/* ---------- the interface index.html uses ---------------------------------------- */

export function mount(els, hooks) {
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
  V.scene.add(makeLights());
  V.grid = makeGrid(6000);
  V.scene.add(V.grid);
  const cams = makeCameras(Math.max(el.clientWidth, 1) / Math.max(el.clientHeight, 1));
  V.persp = cams.persp;
  V.ortho = cams.ortho;
  V.camera = V.persp;
  V.clock = new THREE.Clock();
  V.cP = makeControls(V.persp, V.renderer.domElement, false);
  V.cO = makeControls(V.ortho, V.renderer.domElement, true);
  V.controls = V.cP;
  V.cP.setLookAt(-3000, -4500, 3200, 2000, 1500, 900, false);
  V.pivotDot = new THREE.Mesh(new THREE.SphereGeometry(1, 12, 8),
    new THREE.MeshBasicMaterial({color: PAPER.pivot, depthTest: false, transparent: true, opacity: 0.85}));
  V.pivotDot.renderOrder = 10;
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

export function setVisible(on) {
  V.visible = !!on;
  if (V.visible) { resize(); requestRender(); }
  else stopLoop();
}

// A new scene from the server. Only cabinets whose hash changed are rebuilt,
// and the camera is never moved by an update — only by an explicit Fit, a
// view or a double-click; a NEW job opens at Home.
export function update(payload, opts) {
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
  say(payload.banner || (payload.room && !payload.ceiling_measured
    ? "The ceiling is not measured: the walls stop a drawing margin above the tallest item." : ""));
  if (fresh) { setProjection(false, false); viewHome(false); }
  if (V.hooks.updated) V.hooks.updated(payload);
  requestRender();
}

export function select(number) {
  if (number === V.sel) { applySelection(); requestRender(); return; }
  V.sel = number;
  if (V.isolate !== null && number !== null) V.isolate = number;
  applyGhosting();
  updateBar();
}

export function setLayers(list) {
  V.layers = list === null ? null : new Set(list);
  applyGhosting();
  updateBar();
}

export function isolate(number) { setIsolate(number); }

export function flyTo(number) {
  const grp = V.groups.get(number);
  if (grp) fitTo(new THREE.Box3().setFromObject(grp), true);
}

// For the browser checks: is the camera still, where is an item, and how is a
// part drawn. None of it is read by the view itself.
export function idle() { return !V.running && !V.animating; }

export function bounds(number) {
  const grp = V.groups.get(number);
  if (!grp) return null;
  const b = new THREE.Box3().setFromObject(grp);
  return {min: [b.min.x, b.min.y, b.min.z], max: [b.max.x, b.max.y, b.max.z]};
}

export function partInfo(id) {
  for (const grp of [...V.groups.values(), V.roomParts].filter(Boolean)) {
    for (const m of grp.children) {
      if (m.userData.id !== id) continue;
      const mat = m.material[1];
      return {colour: "#" + mat.color.getHexString(), map: !!mat.map,
              opacity: mat.opacity, ghost: !!m.userData.ghost, visible: m.visible && grp.visible,
              edges: !!(m.userData.edges && m.userData.edges.visible),
              rest: m.userData.rest ? [m.userData.rest.position.toArray(), m.position.toArray()] : null,
              rotation: m.rotation.z};
    }
  }
  return null;
}

export function debugCam() {
  const c = V.controls;
  const fo = c.getFocalOffset(new THREE.Vector3());
  return {target: c.getTarget(new THREE.Vector3()).toArray(), distance: c.distance,
          focal: fo.toArray(), cam: V.camera.position.toArray(), fov: V.persp.fov,
          polar: c.polarAngle, azimuth: c.azimuthAngle, zoom: V.camera.zoom, running: V.running,
          active: c.active};
}

export function debugShell() {
  return (V.wallMeshes || []).map((m) => {
    const b = new THREE.Box3().setFromObject(m);
    return {wall: m.userData.wall, visible: m.visible, side: m.material.side,
            min: b.min.toArray(), max: b.max.toArray(), pos: m.position.toArray(),
            det: m.matrixWorld.determinant(), verts: m.geometry.attributes.position.count};
  });
}

export function memory() {
  const m = V.renderer ? V.renderer.info.memory : {geometries: 0, textures: 0};
  return {geometries: m.geometries, textures: m.textures, groups: V.groups.size, pickables: V.pickables.length};
}

export function state() {
  return {sel: V.sel, isolate: V.isolate, layers: V.layers ? [...V.layers] : null, display: V.display,
          walls: V.walls, labels: V.labels, ortho: V.ortho_on, fronts: V.frontsOpen,
          clearances: V.clearances, hidden: [...V.hidden]};
}

export function camera() {
  const p = V.controls.getPosition(new THREE.Vector3());
  const t = V.controls.getTarget(new THREE.Vector3());
  return {position: [p.x, p.y, p.z], target: [t.x, t.y, t.z], zoom: V.camera.zoom, ortho: V.ortho_on};
}

// Screen position of a world point — for the checks, which want to know that
// a corner stayed under the cursor.
export function project(x, y, z) {
  const r = V.renderer.domElement.getBoundingClientRect();
  const p = new THREE.Vector3(x, y, z).project(V.camera);
  return {x: (p.x + 1) / 2 * r.width, y: (1 - p.y) / 2 * r.height, depth: p.z};
}

export function unproject(clientX, clientY) {
  const hit = pick({clientX, clientY}, true);
  return hit ? [hit.point.x, hit.point.y, hit.point.z] : null;
}

export function dispose() {
  stopLoop();
  if (V.observer) V.observer.disconnect();
  window.removeEventListener("keydown", onKey);
  window.removeEventListener("keyup", onKey);
  for (const [n, grp] of [...V.groups]) { V.scene.remove(grp); disposeObject(grp); V.groups.delete(n); }
  if (V.roomParts) disposeObject(V.roomParts);
  if (V.shell) disposeObject(V.shell);
  for (const t of V.textures.values()) t.dispose();
  V.textures.clear();
  if (V.cube) V.cube.dispose();
  if (V.cP) V.cP.dispose();
  if (V.cO) V.cO.dispose();
  if (V.renderer) V.renderer.dispose();
  if (V.els.view) V.els.view.innerHTML = "";
  V.renderer = V.scene = V.camera = V.controls = null;
}

export { resize, fitAll, viewHome, viewTop, viewWall, setProjection, setDisplay };
