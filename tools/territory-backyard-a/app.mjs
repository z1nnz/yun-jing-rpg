import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { Yard, CROPS, GROW_SECONDS } from './yard.mjs';
import { SLOT, HOUSE_Z, BACK_Z, HALF_X, GATE, SPAWN, blocked, inGateSwing, nearestTarget } from './layout.mjs';

const $ = id => document.getElementById(id);
const COARSE = matchMedia('(pointer: coarse)').matches;
const yard = new Yard(2);

// ------------------------------------------------------------------ renderer, sky, light (pattern from tools/qingxi-waterhead-a)
const canvas = $('world');
const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, powerPreference: 'high-performance' });
renderer.setPixelRatio(Math.min(devicePixelRatio, COARSE ? 1.5 : 1.75));
renderer.outputColorSpace = THREE.SRGBColorSpace;
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFSoftShadowMap;
const scene = new THREE.Scene();
const DAY = { top: new THREE.Color('#7499ad'), hor: new THREE.Color('#c9d2c4'), hemi: 1.0, sun: 2.8, env: 0.55, exposure: 1.0 };
const DUSK = { top: new THREE.Color('#1f2a3c'), hor: new THREE.Color('#5d5868'), hemi: 0.18, sun: 0.12, env: 0.12, exposure: 1.15 };
const skyU = { sun: { value: new THREE.Vector3(0.5, 0.62, 0.45).normalize() }, top: { value: DAY.top.clone() }, hor: { value: DAY.hor.clone() },
  warm: { value: new THREE.Color('#f3d9a8') } };
const sky = new THREE.Mesh(new THREE.SphereGeometry(300, 32, 16), new THREE.ShaderMaterial({
  side: THREE.BackSide, depthWrite: false, fog: false, uniforms: skyU,
  vertexShader: 'varying vec3 vDir; void main(){ vDir = normalize(position); gl_Position = projectionMatrix * modelViewMatrix * vec4(position,1.0); }',
  fragmentShader: `varying vec3 vDir; uniform vec3 sun, top, hor, warm;
    void main(){ float h = clamp(vDir.y, -0.2, 1.0); vec3 c = mix(hor, top, pow(max(h,0.0), 0.6));
      float s = max(dot(normalize(vDir), sun), 0.0); c += warm * (pow(s, 6.0) * 0.3 + pow(s, 400.0) * 2.0);
      gl_FragColor = vec4(c, 1.0); }`,
}));
scene.add(sky);
const hemi = new THREE.HemisphereLight(0xdde6e8, 0x4d4630, DAY.hemi);
scene.add(hemi);
const sun = new THREE.DirectionalLight(0xffe4bc, DAY.sun);
sun.position.set(8, 12, 4);
sun.target.position.set(0, 0, -7.5);
sun.castShadow = true;
sun.shadow.mapSize.set(COARSE ? 1024 : 2048, COARSE ? 1024 : 2048);
Object.assign(sun.shadow.camera, { left: -10, right: 10, top: 10, bottom: -10, near: 1, far: 40 });
sun.shadow.bias = -0.0004; sun.shadow.normalBias = 0.03;
scene.add(sun, sun.target);
{
  const pm = new THREE.PMREMGenerator(renderer), env = new THREE.Scene();
  env.add(sky.clone());
  scene.environment = pm.fromScene(env, 0.04).texture;
  scene.environmentIntensity = DAY.env;
}
let dusk = false;
function setDusk(on) {
  dusk = on;
  const P = on ? DUSK : DAY;
  skyU.top.value.copy(P.top); skyU.hor.value.copy(P.hor);
  hemi.intensity = P.hemi; sun.intensity = P.sun; scene.environmentIntensity = P.env; renderer.toneMappingExposure = P.exposure;
}

// ------------------------------------------------------------------ ground and the house's back wall (placeholders: terrain and house are not this kit)
function canvasTex(size, paint, repeat) {
  const c = document.createElement('canvas'); c.width = c.height = size; paint(c.getContext('2d'), size);
  const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; t.wrapS = t.wrapT = THREE.RepeatWrapping; t.repeat.set(repeat, repeat); t.anisotropy = 4;
  return t;
}
function rand(seed) { let s = seed >>> 0; return () => ((s = (1664525 * s + 1013904223) >>> 0) / 2 ** 32); }
const groundTex = canvasTex(256, (g, n) => { const r = rand(3); g.fillStyle = '#5b5a3a'; g.fillRect(0, 0, n, n);
  for (let i = 0; i < 2600; i++) { g.fillStyle = r() < 0.5 ? `rgba(${96 + r() * 36},${84 + r() * 26},${52 + r() * 16},.5)` : `rgba(${60 + r() * 22},${80 + r() * 26},${40 + r() * 12},.45)`;
    g.fillRect(r() * n, r() * n, 1 + r() * 3, 1 + r() * 3); } }, 24);
const ground = new THREE.Mesh(new THREE.PlaneGeometry(60, 60).rotateX(-Math.PI / 2), new THREE.MeshStandardMaterial({ map: groundTex, roughness: 1 }));
ground.position.set(0, -0.005, -8);
ground.receiveShadow = true;
scene.add(ground);
{
  const wallM = new THREE.MeshStandardMaterial({ color: 0x8f877a, roughness: 0.95 });
  for (const [x0, x1] of [[-HALF_X - 0.2, -0.6], [0.6, HALF_X + 0.2]]) {
    const w = new THREE.Mesh(new THREE.BoxGeometry(x1 - x0, 3.2, 0.3), wallM);
    w.position.set((x0 + x1) / 2, 1.6, HOUSE_Z + 0.15); w.castShadow = w.receiveShadow = true; scene.add(w);
  }
  const lintel = new THREE.Mesh(new THREE.BoxGeometry(1.2, 1.0, 0.3), wallM);
  lintel.position.set(0, 2.7, HOUSE_Z + 0.15); scene.add(lintel);
  const door = new THREE.Mesh(new THREE.PlaneGeometry(1.2, 2.2), new THREE.MeshStandardMaterial({ color: 0x2a1d14, roughness: 0.9 }));
  door.position.set(0, 1.1, HOUSE_Z + 0.31); door.rotation.y = Math.PI; scene.add(door);
}

// ------------------------------------------------------------------ load the kit
const loader = new GLTFLoader();
const FILES = ['TY01_SpiritField', 'TY02_QinglingGrass', 'TY03_ClearwaterLotus', 'TY04_Shoudeng', 'TY05_PracticeFloor', 'TY06_TrainingGear',
  'TY07_Fence', 'TY08_HerbRack', 'TY09_YardClutter', 'TY10_GravelPath'];
const nodes = {};      // node name -> Object3D (LOD0 / water only; LOD1 / LOD2 are for the engine's LOD group)
let loaded = 0;
async function loadAll() {
  const all = [...FILES.map(f => `assets/${f}_v001.glb`), 'post/agility-post.glb'];
  const res = await Promise.all(all.map(u => loader.loadAsync(u).then(g => { loaded++; $('load-bar').style.width = `${loaded / all.length * 100}%`; return g; })));
  res.forEach((g, i) => {
    g.scene.traverse(o => {
      if (o.isMesh) { o.castShadow = true; o.receiveShadow = true; }
    });
    for (const o of [...g.scene.children]) {
      if (/_LOD[12]$/.test(o.name) || o.name.startsWith('SOCKET_')) continue;
      nodes[i < FILES.length ? o.name : 'agility-post'] = o;
    }
    if (i === FILES.length) nodes['agility-post'] = g.scene;
  });
}
/** Clone a kit node into a group placed at three (x, z) with yaw (same yaw as the Blender layout). */
function put(name, x, z, yaw = 0, y = 0) {
  const src = nodes[name];
  if (!src) { console.warn('missing node', name); return null; }
  const g = new THREE.Group();
  const c = src.clone(true);
  c.traverse(o => { if (o.isMesh) o.material = o.material.clone(); });
  g.add(c);
  g.position.set(x, y, z); g.rotation.y = yaw;
  scene.add(g);
  return g;
}

// ------------------------------------------------------------------ assemble the yard (same slots as art/previews/territory-backyard-a/backyard)
const fieldsView = [];
let lanternMats = [], lanternLight, rackHerbs, gateLeaf;
let wetTex = null;
function buildYard() {
  const F = 'SM_TY_SpiritField', G = 'SM_TY_QinglingGrass', L = 'SM_TY_ClearwaterLotus';
  [SLOT.TY_Field_1, SLOT.TY_Field_2].forEach((s, i) => {
    const yaw = i ? Math.PI : 0;
    const bed = put(`${F}_LOD0`, s.x, s.z, yaw);
    const water = put(`${F}_Water`, s.x, s.z, yaw);
    water.visible = false;
    const stages = {
      qingling: [1, 2, 3, 4].map(k => put(`${G}_S${k}_LOD0`, s.x, s.z, yaw)),
      lotus: [1, 2, 3, 4].map(k => put(`${L}_S${k}_LOD0`, s.x, s.z, yaw)),
    };
    for (const list of Object.values(stages)) for (const o of list) o.visible = false;
    const dryMats = [];
    bed.traverse(o => { if (o.isMesh) dryMats.push([o, o.material]); });
    fieldsView.push({ bed, water, stages, dryMats, wet: false });
  });
  put('SM_TY_PracticeFloor_LayoutA_LOD0', SLOT.TY_Practice.x, SLOT.TY_Practice.z);
  const post = nodes['agility-post'].clone(true); post.position.set(SLOT.TY_Practice.x, 0.05, SLOT.TY_Practice.z); scene.add(post);
  const lantern = put('SM_TY_Shoudeng_LOD0', SLOT.TY_Lantern.x, SLOT.TY_Lantern.z);
  lantern.traverse(o => { if (o.isMesh && /Paper/.test(o.material.name)) lanternMats.push(o.material); });
  lanternLight = new THREE.PointLight(0xffc77a, 0, 6, 1.8);
  lanternLight.position.set(SLOT.TY_Lantern.x, 1.27, SLOT.TY_Lantern.z);
  scene.add(lanternLight);
  put('SM_TY_TrainingGear_StoneBarbell_LOD0', -3.1, -12.0, 0.15);
  put('SM_TY_TrainingGear_StoneLock_LOD0', 1.95, -10.1);
  put('SM_TY_TrainingGear_WeaponRack_LOD0', -2.4, -10.4, Math.PI / 2);
  const C = SLOT.TY_Corner_R;
  for (const [nm, dx, dz, r] of [['WaterJar', -0.45, -0.35, 0], ['Basket', 0.15, -0.45, 0], ['Hoe', 0.62, -0.15, Math.PI / 2], ['Bucket', -0.5, 0.35, 0],
    ['Woodpile', 0.15, 0.2, Math.PI / 2], ['Stool', -0.05, 0.6, 0.3]]) put(`SM_TY_YardClutter_${nm}_LOD0`, C.x + dx, C.z + dz, r);
  put('SM_TY_HerbRack_Rack_LOD0', SLOT.TY_Rack.x, SLOT.TY_Rack.z, Math.PI / 2);
  rackHerbs = put('SM_TY_HerbRack_Herbs_LOD0', SLOT.TY_Rack.x, SLOT.TY_Rack.z, Math.PI / 2);
  rackHerbs.visible = false;
  put('SM_TY_GravelPath_End_LOD0', 0, HOUSE_Z - 0.55, Math.PI);
  for (const [nm, z] of [['StraightA', -4.1], ['StraightB', -6.1], ['StraightA', -8.1]]) put(`SM_TY_GravelPath_${nm}_LOD0`, 0, z);
  // fence runs (module centre along the run, posts at each module's -X end), as the Blender layout
  const run = (x0, z0, x1, z1, kinds) => {
    const dx = x1 - x0, dz = z1 - z0, len = Math.hypot(dx, dz), ux = dx / len, uz = dz / len, yaw = Math.atan2(-uz, ux);
    let d = 0;
    for (const k of kinds) {
      const Lm = k === 'StraightA' || k === 'StraightB' ? 2 : 1, cx = x0 + ux * (d + Lm / 2), cz = z0 + uz * (d + Lm / 2);
      if (k === 'Gate') {
        put('SM_TY_Fence_GateFrame_LOD0', cx, cz, yaw);
        const leaf = put('SM_TY_Fence_GateLeaf_LOD0', cx, cz, yaw);
        gateLeaf = leaf.children[0];          // its origin is the hinge (art/exports/.../TY07_Fence_v001_model_info.json)
      } else put(`SM_TY_Fence_${k}_LOD0`, cx, cz, yaw);
      d += Lm;
    }
  };
  run(-HALF_X, BACK_Z, HALF_X, BACK_Z, ['StraightA', 'StraightB', 'StraightA', 'StraightB', 'Straight1m', 'Gate', 'Straight1m', 'Straight1m']);
  run(-HALF_X, HOUSE_Z, -HALF_X, BACK_Z, ['StraightB', 'StraightA', 'StraightB', 'StraightA', 'StraightB']);
  run(HALF_X, BACK_Z, HALF_X, HOUSE_Z, ['StraightA', 'StraightB', 'StraightA', 'StraightB', 'StraightA']);
  for (const x of [-HALF_X, HALF_X]) { put('SM_TY_Fence_Corner_LOD0', x, BACK_Z); put('SM_TY_Fence_End_LOD0', x, HOUSE_Z, Math.PI / 2); }
}
async function loadWet() {
  const tl = new THREE.TextureLoader();
  const [bc, orm] = await Promise.all(['tex/T_TY01_SpiritField_Wet_BaseColor.png', 'tex/T_TY01_SpiritField_Wet_ORM.png'].map(u => tl.loadAsync(u)));
  for (const t of [bc, orm]) t.flipY = false;
  bc.colorSpace = THREE.SRGBColorSpace;
  wetTex = { bc, orm };
}
function setWet(f, wet) {
  if (f.wet === wet || !wetTex) return;
  f.wet = wet;
  for (const [o, dry] of f.dryMats) {
    if (!wet) { o.material = dry; continue; }
    const m = dry.clone(); m.map = wetTex.bc; m.roughnessMap = m.metalnessMap = wetTex.orm; m.needsUpdate = true; o.material = m;
  }
}

// ------------------------------------------------------------------ the player stand-in and camera
const player = new THREE.Group();
{
  const m = new THREE.MeshStandardMaterial({ color: 0x2f5a4c, roughness: 0.8 });
  const body = new THREE.Mesh(new THREE.CapsuleGeometry(0.24, 0.95, 6, 14), m); body.position.y = 0.72; body.castShadow = true;
  const head = new THREE.Mesh(new THREE.SphereGeometry(0.15, 16, 12), new THREE.MeshStandardMaterial({ color: 0xd9b48f, roughness: 0.7 }));
  head.position.y = 1.58; head.castShadow = true;
  player.add(body, head);
}
scene.add(player);
const P = { x: SPAWN.x, z: SPAWN.z, heading: SPAWN.heading };
const cam = new THREE.PerspectiveCamera(55, innerWidth / innerHeight, 0.05, 400);
const view = { yaw: 0, pitch: 0.38, dist: 4.2, eye: false };     // yaw 0 = looking toward -z, into the yard
const keys = new Set();
addEventListener('keydown', e => {
  keys.add(e.code);
  if (e.repeat) return;
  if (e.code === 'Digit1') act('qingling');
  if (e.code === 'Digit2') act('lotus');
  if (e.code === 'KeyE') act('use');
  if (e.code === 'KeyN') setDusk(!dusk);
});
addEventListener('keyup', e => keys.delete(e.code));
let drag = null;
canvas.addEventListener('pointerdown', e => { if (e.pointerType === 'mouse' || !COARSE) drag = { x: e.clientX, y: e.clientY }; });
addEventListener('pointerup', () => { drag = null; });
addEventListener('pointermove', e => {
  if (!drag) return;
  view.yaw -= (e.clientX - drag.x) * 0.006; view.pitch = Math.min(1.2, Math.max(0.08, view.pitch + (e.clientY - drag.y) * 0.004));
  drag = { x: e.clientX, y: e.clientY };
});
// touch: left stick to move, right side drag to look
const stick = { x: 0, y: 0, id: null };
{
  const el = $('stick'), knob = el.querySelector('i');
  el.addEventListener('pointerdown', e => { stick.id = e.pointerId; el.setPointerCapture(e.pointerId); move(e); });
  const move = e => {
    if (e.pointerId !== stick.id) return;
    const r = el.getBoundingClientRect(), dx = (e.clientX - r.left - r.width / 2) / (r.width / 2), dy = (e.clientY - r.top - r.height / 2) / (r.height / 2);
    const l = Math.min(1, Math.hypot(dx, dy)), a = Math.atan2(dy, dx);
    stick.x = Math.cos(a) * l; stick.y = Math.sin(a) * l;
    knob.style.transform = `translate(${stick.x * 36}px, ${stick.y * 36}px)`;
  };
  el.addEventListener('pointermove', move);
  const end = e => { if (e.pointerId === stick.id) { stick.id = null; stick.x = stick.y = 0; knob.style.transform = ''; } };
  el.addEventListener('pointerup', end); el.addEventListener('pointercancel', end);
  let look = null;
  canvas.addEventListener('pointerdown', e => { if (COARSE && e.clientX > innerWidth * 0.4) look = { id: e.pointerId, x: e.clientX, y: e.clientY }; });
  canvas.addEventListener('pointermove', e => {
    if (!look || e.pointerId !== look.id) return;
    view.yaw -= (e.clientX - look.x) * 0.008; view.pitch = Math.min(1.2, Math.max(0.08, view.pitch + (e.clientY - look.y) * 0.005));
    look.x = e.clientX; look.y = e.clientY;
  });
  canvas.addEventListener('pointerup', () => { look = null; });
  const hold = (id, on, off) => { const b = $(id); b.addEventListener('pointerdown', e => { e.preventDefault(); b.classList.add('down'); on(); });
    for (const ev of ['pointerup', 'pointercancel', 'pointerleave']) b.addEventListener(ev, () => { b.classList.remove('down'); off && off(); }); };
  hold('t-grass', () => act('qingling'));
  hold('t-lotus', () => act('lotus'));
  hold('t-use', () => act('use'));
  hold('t-fast', () => { touchFast = true; }, () => { touchFast = false; });
}
let touchFast = false;

// ------------------------------------------------------------------ interaction (texts say only what is seen; the lantern is never explained)
// Player-visible text is hardcoded here for the local demo, each line kept within 16 characters (standards section 3.1).
// Section 3.5 wants it in packages/content/*.json, which is outside this kit's folder: TODO for the core team, listed in README.
function toast(text) { const t = $('toast'); t.textContent = text; t.classList.remove('show'); void t.offsetWidth; t.classList.add('show'); }
const SIDE = ['左田', '右田'];
function act(kind) {
  const tgt = nearestTarget(P.x, P.z);
  if (!tgt) return;
  if (tgt.kind === 'gate') {
    if (kind !== 'use') return;
    const before = yard.gateOpen, now = yard.toggleGate(inGateSwing(P.x, P.z));
    if (before && now) toast('先讓開門口');
    return;
  }
  const i = tgt.i, f = yard.fields[i];
  if ((kind === 'qingling' || kind === 'lotus') && !f.crop) {
    yard.plant(i, kind);
    toast(`種下${CROPS[kind].name}`);
  } else if (kind === 'use' && yard.canHarvest(i)) {
    const crop = f.crop;
    if (yard.harvest(i)) toast(`收成了${CROPS[crop].name}`);
  }
}
function refreshFields() {
  yard.fields.forEach((f, i) => {
    const v = fieldsView[i], st = yard.stage(i);
    for (const [crop, list] of Object.entries(v.stages)) list.forEach((o, k) => { o.visible = f.crop === crop && st === k; });
    v.water.visible = f.crop === 'lotus';
    setWet(v, !!f.crop);
    const el = $(`f${i}`);
    el.querySelector('span').textContent = f.crop ? `${CROPS[f.crop].name}・${CROPS[f.crop].stages[st]}` : '空著';
    el.querySelector('i').style.width = `${f.crop ? f.t * 100 : 0}%`;
    el.classList.toggle('ripe', st === 3);
  });
  const lv = [0, 0.2, 0.5, 0.9, 1.5][yard.level];
  for (const m of lanternMats) m.emissiveIntensity = lv;
  lanternLight.intensity = [0, 0.3, 0.8, 1.6, 3.0][yard.level];
  rackHerbs.visible = yard.rackFull;
}
function promptText() {
  const tgt = nearestTarget(P.x, P.z);
  if (!tgt) return yard.speed > 1 ? '時間快轉中' : '';
  if (tgt.kind === 'gate') return yard.gateOpen ? 'E 關上柴門' : 'E 打開柴門';
  const f = yard.fields[tgt.i], st = yard.stage(tgt.i);
  if (!f.crop) return `${SIDE[tgt.i]}：1 青靈草・2 淨水蓮`;
  if (st === 3) return `${SIDE[tgt.i]}：E 收成${CROPS[f.crop].name}`;
  return `${SIDE[tgt.i]}：${CROPS[f.crop].name}・${CROPS[f.crop].stages[st]}`;
}

// ------------------------------------------------------------------ loop
let gateAngle = 0;
const clock = new THREE.Clock();
function frame() {
  const dt = Math.min(0.05, clock.getDelta());
  yard.setSpeed(keys.has('KeyF') || touchFast ? 30 : 1);
  yard.tick(dt);
  // move relative to the camera; slide along whatever blocks
  let mx = (keys.has('KeyD') ? 1 : 0) - (keys.has('KeyA') ? 1 : 0) + stick.x, my = (keys.has('KeyW') ? 1 : 0) - (keys.has('KeyS') ? 1 : 0) - stick.y;
  const ml = Math.hypot(mx, my);
  if (ml > 0.05) {
    mx /= Math.max(1, ml); my /= Math.max(1, ml);
    const fx = -Math.sin(view.yaw), fz = -Math.cos(view.yaw), rx = -fz, rz = fx;
    const vx = (fx * my + rx * mx) * 3.0 * dt, vz = (fz * my + rz * mx) * 3.0 * dt;
    const opt = { gateOpen: yard.gateOpen && Math.abs(gateAngle) > 1.2 };
    if (!blocked(P.x + vx, P.z + vz, opt)) { P.x += vx; P.z += vz; }
    else if (!blocked(P.x + vx, P.z, opt)) P.x += vx;
    else if (!blocked(P.x, P.z + vz, opt)) P.z += vz;
    P.heading = Math.atan2(vx, vz);
  }
  player.position.set(P.x, 0, P.z); player.rotation.y = P.heading;
  const target = yard.gateOpen ? -1.75 : 0;
  gateAngle += (target - gateAngle) * Math.min(1, dt * 5);
  if (gateLeaf) gateLeaf.rotation.y = gateAngle;
  refreshFields();
  const pr = $('prompt'); pr.textContent = promptText(); pr.hidden = !pr.textContent; pr.classList.toggle('fast', yard.speed > 1);
  if (view.eye) {
    cam.position.set(P.x, 1.7, P.z);
    cam.lookAt(P.x - Math.sin(view.yaw) * 4, 1.7 - Math.tan(view.pitch) * 4, P.z - Math.cos(view.yaw) * 4);
    player.visible = false;
  } else {
    player.visible = true;
    let dist = view.dist;                     // keep the camera in front of the house wall
    const back = Math.cos(view.yaw) * Math.cos(view.pitch);
    if (back > 0.05) dist = Math.max(1.2, Math.min(dist, (HOUSE_Z - 0.35 - P.z) / back));
    const cx = P.x + Math.sin(view.yaw) * Math.cos(view.pitch) * dist, cz = P.z + Math.cos(view.yaw) * Math.cos(view.pitch) * dist;
    cam.position.set(cx, 1.2 + Math.sin(view.pitch) * dist, cz);
    cam.lookAt(P.x, 1.0, P.z);
  }
  renderer.render(scene, cam);
  requestAnimationFrame(frame);
}
addEventListener('resize', () => { renderer.setSize(innerWidth, innerHeight, false); cam.aspect = innerWidth / innerHeight; cam.updateProjectionMatrix(); });
renderer.setSize(innerWidth, innerHeight, false);
cam.aspect = innerWidth / innerHeight; cam.updateProjectionMatrix();

// ------------------------------------------------------------------ test hooks for capture.mjs (real key input drives the player; these only read state or aim the camera)
globalThis.__yard = {
  state: () => ({ ...yard.snapshot(), player: { x: P.x, z: P.z }, target: nearestTarget(P.x, P.z), gateAngle, dusk }),
  look: (yawDeg, pitch) => { view.yaw = yawDeg * Math.PI / 180; if (pitch != null) view.pitch = pitch; },
  eye: on => { view.eye = !!on; },
  GROW_SECONDS, GATE,
};

loadAll().then(async () => { await loadWet(); buildYard(); refreshFields(); $('loading').hidden = true; frame(); })
  .catch(e => { $('load-text').textContent = `載入失敗：${e.message}`; console.error(e); });
