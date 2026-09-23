/* The 3D view (Part F, 23 September 2026).

   A DRAWING of the model, and nothing else. The server builds the scene from
   `room.solid_parts` (`/api/scene`) and this module only draws it: it extrudes
   the outlines it is given, rotates a door by the angle it is given, and picks
   the nearest snap from a list it is given. The one thing it works out by
   itself is the camera — orbit, pan, zoom, projection — because that moves the
   viewer and not the model.

   Loaded by index.html the first time the 3D tab is opened, through the small
   interface at the bottom of this file. Vanilla JS, no build step. three.js
   0.186.0 and camera-controls 3.1.2 come off /vendor/, served by the app.  */

import * as THREE from "three";
import CameraControls from "camera-controls";

CameraControls.install({THREE: THREE});

const MM = 1;                        // one world unit is one millimetre, as room.py has it
const PIXEL_RATIO_CAP = 2;

// Everything the view holds, in one place.
const V = {
  el: null,            // the viewport element
  hooks: {},           // what index.html asked to be told about
  renderer: null,
  scene: null,
  camera: null,        // the live camera: perspective or orthographic
  persp: null,
  ortho: null,
  controls: null,
  clock: null,
  visible: false,      // the tab is showing; nothing renders while it is not
  running: false,      // a requestAnimationFrame loop is going (camera moving)
  lost: false,         // the WebGL context is lost
  observer: null,
  grid: null,
  note: null,          // the one-line notice over the viewport
};

/* ---------- WebGL, and losing it -------------------------------------------- */

function webglAvailable() {
  try {
    const c = document.createElement("canvas");
    return !!(window.WebGLRenderingContext &&
              (c.getContext("webgl2") || c.getContext("webgl")));
  } catch (e) {
    return false;
  }
}

function say(text) {
  if (!V.note) return;
  V.note.textContent = text || "";
  V.note.hidden = !text;
}

function status(text) {
  if (V.hooks.status) V.hooks.status(text || "");
}

/* ---------- renderer, camera, controls -------------------------------------- */

function makeRenderer() {
  const r = new THREE.WebGLRenderer({antialias: true, alpha: false,
                                     powerPreference: "high-performance"});
  r.setPixelRatio(Math.min(window.devicePixelRatio || 1, PIXEL_RATIO_CAP));
  r.setClearColor(0xeef0ec, 1);
  r.outputColorSpace = THREE.SRGBColorSpace;
  const canvas = r.domElement;
  canvas.tabIndex = 0;                                   // shortcuts need focus
  // A lost context is caught, and the view is rebuilt when it is restored,
  // rather than leaving a dead canvas: preventDefault is what asks the browser
  // to try restoring it at all.
  canvas.addEventListener("webglcontextlost", (e) => {
    e.preventDefault();
    V.lost = true;
    stopLoop();
    say("The 3D view lost its graphics context — waiting for it to come back.");
  }, false);
  canvas.addEventListener("webglcontextrestored", () => {
    V.lost = false;
    say("");
    requestRender();
  }, false);
  return r;
}

function makeCameras(aspect) {
  const persp = new THREE.PerspectiveCamera(45, aspect, 10 * MM, 100000 * MM);
  const ortho = new THREE.OrthographicCamera(-2000, 2000, 2000 / aspect, -2000 / aspect,
                                             -100000 * MM, 100000 * MM);
  // Z up, world axes exactly as room.py defines them: X right, Y into the
  // room from wall A, Z up. No axis swap anywhere — which is also what lets
  // world vertices off the server be used as they are.
  persp.up.set(0, 0, 1);
  ortho.up.set(0, 0, 1);
  return {persp, ortho};
}

function makeControls(camera, dom) {
  const c = new CameraControls(camera, dom);
  // The ruled mouse scheme: left-drag orbits, right- or middle-drag pans,
  // the wheel and a pinch zoom towards the cursor, Shift+left-drag pans too.
  c.mouseButtons.left = CameraControls.ACTION.ROTATE;
  c.mouseButtons.middle = CameraControls.ACTION.TRUCK;
  c.mouseButtons.right = CameraControls.ACTION.TRUCK;
  c.mouseButtons.wheel = CameraControls.ACTION.DOLLY;
  c.mouseButtons.shiftLeft = CameraControls.ACTION.TRUCK;
  c.touches.one = CameraControls.ACTION.TOUCH_ROTATE;
  c.touches.two = CameraControls.ACTION.TOUCH_DOLLY_TRUCK;
  c.dollyToCursor = true;
  c.infinityDolly = false;
  c.minDistance = 50 * MM;
  c.maxDistance = 60000 * MM;
  // No roll, and the camera may go a little below the floor (looking up under
  // a wall unit is useful) but never over the pole.
  c.minPolarAngle = 0.02;
  c.maxPolarAngle = Math.PI / 2 + 0.35;
  c.dampingFactor = 0.12;
  c.draggingDampingFactor = 0.25;
  c.smoothTime = 0.18;
  c.draggingSmoothTime = 0.08;
  c.addEventListener("wake", startLoop);
  c.addEventListener("sleep", stopLoop);
  return c;
}

/* ---------- render on demand, never in a loop ------------------------------- */

function render() {
  if (!V.renderer || !V.visible || V.lost) return;
  V.renderer.render(V.scene, V.camera);
}

// One frame, drawn when the scene or the size changed and the camera is still.
let renderQueued = false;
function requestRender() {
  if (renderQueued || !V.visible) return;
  renderQueued = true;
  requestAnimationFrame(() => { renderQueued = false; render(); });
}

// A loop runs only while the camera is moving — from the first movement of a
// gesture or a fly-to until the damping has settled — and stops itself.
function tick() {
  if (!V.running) return;
  const dt = V.clock.getDelta();
  const moved = V.controls.update(dt);
  if (moved) render();
  requestAnimationFrame(tick);
}

function startLoop() {
  if (V.running || !V.visible) return;
  V.running = true;
  V.clock.getDelta();
  requestAnimationFrame(tick);
}

function stopLoop() {
  V.running = false;
}

/* ---------- size ------------------------------------------------------------ */

function resize() {
  if (!V.renderer || !V.el) return;
  const w = Math.max(V.el.clientWidth, 1);
  const h = Math.max(V.el.clientHeight, 1);
  V.renderer.setSize(w, h, false);
  const aspect = w / h;
  V.persp.aspect = aspect;
  V.persp.updateProjectionMatrix();
  const half = (V.ortho.right - V.ortho.left) / 2;
  V.ortho.top = half / aspect;
  V.ortho.bottom = -half / aspect;
  V.ortho.updateProjectionMatrix();
  requestRender();
}

/* ---------- the empty room: floor grid and lights --------------------------- */

function makeGrid() {
  // A subtle floor grid, 100 mm minor and 1000 mm major, in the XY plane
  // (three's GridHelper lies in XZ, so it is turned onto the floor).
  const g = new THREE.Group();
  const minor = new THREE.GridHelper(20000, 200, 0xc9cdc5, 0xdfe2dc);
  const major = new THREE.GridHelper(20000, 20, 0xb4b9b0, 0xb4b9b0);
  for (const gh of [minor, major]) {
    gh.rotation.x = Math.PI / 2;
    gh.material.transparent = true;
    gh.material.opacity = 0.6;
    gh.material.depthWrite = false;
    g.add(gh);
  }
  g.position.z = -0.5;
  return g;
}

function makeLights() {
  const g = new THREE.Group();
  const hemi = new THREE.HemisphereLight(0xffffff, 0x9a9a90, 1.1);
  hemi.position.set(0, 0, 1);
  const key = new THREE.DirectionalLight(0xffffff, 1.2);
  key.position.set(-3000, -4000, 6000);
  g.add(hemi, key);
  return g;
}

/* ---------- the interface index.html uses ----------------------------------- */

export function mount(el, hooks) {
  V.el = el;
  V.hooks = hooks || {};
  el.innerHTML = "";
  V.note = document.createElement("div");
  V.note.className = "v3dnote";
  V.note.hidden = true;
  if (!webglAvailable()) {
    // One line, and the rest of the app untouched.
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
  V.grid = makeGrid();
  V.scene.add(V.grid);
  const cams = makeCameras(Math.max(el.clientWidth, 1) / Math.max(el.clientHeight, 1));
  V.persp = cams.persp;
  V.ortho = cams.ortho;
  V.camera = V.persp;
  V.clock = new THREE.Clock();
  V.controls = makeControls(V.camera, V.renderer.domElement);
  V.controls.setLookAt(-3000, -4500, 3200, 2000, 1500, 900, false);
  V.observer = new ResizeObserver(() => resize());
  V.observer.observe(el);
  resize();
  status("Left-drag orbits · right-drag pans · wheel zooms to the cursor");
  return true;
}

export function setVisible(on) {
  V.visible = !!on;
  if (V.visible) { resize(); requestRender(); }
  else stopLoop();
}

export function update(scene) {          // F2/F3: the scene payload
  requestRender();
}

export function select(number) {         // F4
}

export function setLayers(list) {        // F5
}

export function dispose() {
  stopLoop();
  if (V.observer) V.observer.disconnect();
  if (V.controls) V.controls.dispose();
  if (V.renderer) V.renderer.dispose();
  if (V.el) V.el.innerHTML = "";
  V.renderer = V.scene = V.camera = V.controls = null;
}

export { resize };
