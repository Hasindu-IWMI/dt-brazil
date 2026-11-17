// Upper Atibaia viewer: replays OBSERVED daily records over a 3D terrain.
// The viewer computes nothing hydrological. Every number on screen is read
// from public/data/timeseries.json, produced by pipeline/process.py.
//
// The scene has two styles. REALISTIC (default) drapes Sentinel-2 dry-season imagery on the
// full-resolution Copernicus DEM, lights it with the computed sun for the replayed date, and adds
// a sky, height haze and reflective lakes. ANALYTICAL is the original look: elevation colours,
// lakes coloured by observed storage, storage columns. Everything that makes the realistic style
// realistic is DISPLAY ONLY; no number on screen depends on it.
import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { CSS2DRenderer, CSS2DObject } from 'three/addons/renderers/CSS2DRenderer.js';
import { Atmosphere } from './scene/atmosphere.js';
import { Terrain, loadDem, LANDCOVER } from './scene/terrain.js';
import { realisticWaterMaterial, analyticalWaterMaterial } from './scene/water.js';
import { RecordLayers } from './scene/layers.js';
import { FloodLayer, LEVELS, RISK_STYLE, statusOf } from './scene/floods.js';
import { BuildingLayer } from './scene/buildings.js';
import { Symbols, SYMBOL_UNIFORMS, pinLabel } from './scene/symbols.js';
import { RiverFlow } from './scene/riverflow.js';
import { FloodWater, SPEED_STOPS } from './scene/floodwater.js';
import { SOURCE_COLOURS } from './scene/buildingMaterial.js';

const RULES_FROM = '2017-06-01';
const COLUMN_M = 4500;  // display height of a full (100 %) storage column, metres
const UTC_OFFSET_H = -3; // local standard time in São Paulo (daylight saving, used until 2019, ignored)

// OSM outline -> reservoir record. Cachoeira is unnamed in OSM and is
// identified by position (outline centred near 23.03 S, 46.29 W, at Piracaia).
const OUTLINES = {
  'relation/2319460': 'atibainha',
  'relation/2906093': 'cachoeira',
  'relation/452185': 'jaguari_jacarei',
  'relation/7004538': 'jaguari_jacarei',
};
const RIVERS = ['Rio Atibaia', 'Rio da Cachoeira', 'Rio Atibainha', 'Rio Jaguari', 'Rio Jacareí'];
const SCENE_GAUGES = ['62670000', '62665000', '62662000'];
const SHORT = { '62670000': 'Atibaia gauge', '62665000': 'Piracaia gauge', '62662000': 'Nazaré Paulista gauge', '62676000': 'Bairro da Ponte (Itatiba)' };

const $ = (id) => document.getElementById(id);
const fmt = (v, d = 1) => (v === null || v === undefined ? null : v.toFixed(d));
const params = new URLSearchParams(location.search);
let style = params.get('style') === 'analytical' ? 'analytical' : 'realistic';
let exag = Number(params.get('relief')) || 1;
let hour = Number(params.get('hour')) || 10;
let haze = params.get('haze') === 'hazy' ? 'hazy' : 'clear';

// Relative to the deployed base, so a static build works under any path.
const DATA = `${import.meta.env.BASE_URL}data/`;
// a missing optional file (the basemap is not in git) gives null; some dev servers answer
// a missing path with index.html, so a body that is not JSON also gives null
const json = (f) => fetch(DATA + f).then((r) => (r.ok ? r.json() : null)).catch(() => null);
const [hiMeta, vectors, ts, catchments, imagery, layerData] = await Promise.all([
  json('terrain_hi.json'), json('vectors.json'), json('timeseries.json'), json('catchments.json'),
  new THREE.TextureLoader().loadAsync(DATA + 'imagery.jpg').catch(() => null),
  json('layers.json'), // rain, river and tunnel records (pipeline/viewer_layers.py); optional
]);
let meta = hiMeta;
let elev;
if (hiMeta) {
  elev = await loadDem(DATA + 'terrain_hi.bin', hiMeta.width, hiMeta.height);
} else { // fall back to the 3 arc-second display window
  meta = await json('terrain.json');
  elev = new Float32Array(await (await fetch(DATA + 'terrain.f32')).arrayBuffer());
}
const { bbox } = meta;

// ---- geographic -> scene (metres, local equirectangular about the window centre; x east, y up, z south)
const lon0 = (bbox.west + bbox.east) / 2;
const lat0 = (bbox.south + bbox.north) / 2;
const KX = 111320 * Math.cos((lat0 * Math.PI) / 180);
const KZ = 110570;
const frame = { KX, KZ, X: (lon) => (lon - lon0) * KX, Z: (lat) => -(lat - lat0) * KZ, lon: (x) => lon0 + x / KX, lat: (z) => lat0 - z / KZ };
const { X, Z } = frame;
const inBox = (lon, lat) => lon >= bbox.west && lon <= bbox.east && lat >= bbox.south && lat <= bbox.north;

// ---- renderer, camera, controls
const host = $('scene');
// stencil: overlapping building shadows darken a pixel only once (buildingMaterial.js)
const renderer = new THREE.WebGLRenderer({ antialias: true, stencil: true });
renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
renderer.toneMapping = THREE.NeutralToneMapping;
SYMBOL_UNIFORMS.uPx.value = renderer.getPixelRatio();
host.appendChild(renderer.domElement);
// Mesh density by GPU class (?quality=high|medium|low overrides): the surface mesh is 3.4 M
// triangles at 60 m spacing, which integrated and mobile GPUs draw slowly. Relief shading uses
// the 30 m normal map at every setting.
const gpu = (() => {
  const gl = renderer.getContext();
  const ext = gl.getExtension('WEBGL_debug_renderer_info');
  return ext ? String(gl.getParameter(ext.UNMASKED_RENDERER_WEBGL)) : '';
})();
const quality = params.get('quality') ?? (/Intel|Mali|Adreno|Apple|PowerVR|SwiftShader|llvmpipe/i.test(gpu) ? 'medium' : 'high');
const stride = { high: 2, medium: 3, low: 4 }[quality] ?? 2;
const labels = new CSS2DRenderer();
labels.domElement.style.cssText = 'position:absolute;inset:0;pointer-events:none';
host.appendChild(labels.domElement);

const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(40, 1, 50, 1.5e6);
const controls = new OrbitControls(camera, renderer.domElement);
controls.maxPolarAngle = Math.PI * 0.49;
controls.minDistance = 120; // close enough for buildings
controls.maxDistance = 320000;
controls.enableDamping = true;
controls.screenSpacePanning = false;

const world = new THREE.Group(); // terrain-attached objects; its y scale is the vertical exaggeration
scene.add(world);
const markers = new THREE.Group(); // pins, columns and labels keep their size at any exaggeration
scene.add(markers);

const terrain = new Terrain({ elev, meta, frame, stride, imagery, anisotropy: renderer.capabilities.getMaxAnisotropy() });
world.add(terrain.group);
const atmosphere = new Atmosphere(scene, renderer, lat0, lon0);
// terrain shadows (hills shading valleys at low sun): one extra depth pass, on by default on 'high'
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFSoftShadowMap;
terrain.mesh.castShadow = true;
terrain.mesh.receiveShadow = true;
let shadows = params.has('shadows') ? params.get('shadows') !== '0' : quality === 'high';
function applyShadows() {
  atmosphere.sun.castShadow = shadows && style === 'realistic';
  renderer.shadowMap.needsUpdate = true;
  $('lyr-shadow').checked = shadows;
}

// Height on the drawn mesh (its own triangles), so lines, pins and buildings sit on the surface you see.
function surfaceAt(lon, lat) {
  return terrain.meshAt(lon, lat) ?? terrain.elevAt(lon, lat) ?? terrain.baseElev;
}

// ---- rivers (mapped lines, on the terrain), with streaks moving downstream (scene/riverflow.js)
const riverFlow = new RiverFlow();
const rivers = new THREE.Group();
for (const r of vectors.rivers) {
  if (!RIVERS.includes(r.name)) continue;
  let pts = [];
  const flush = () => { if (pts.length > 1) rivers.add(riverFlow.line(pts, r.name)); pts = []; };
  for (const [lon, lat] of r.line) {
    if (!inBox(lon, lat)) { flush(); continue; }
    pts.push(new THREE.Vector3(X(lon), surfaceAt(lon, lat) + 12, Z(lat)));
  }
  flush();
}
const riverParticles = riverFlow.buildParticles(); // a layer of its own: the lines are off by default
world.add(rivers, riverParticles);
rivers.visible = false;

// ---- catchment boundaries delineated from the terrain (pipeline/delineate.py)
const catchMat = new THREE.LineBasicMaterial({ color: 0xf0efec, transparent: true, opacity: 0.75 });
const catchLines = new THREE.Group();
for (const name of ['cachoeira_dam', 'atibainha_dam', 'atibaia_gauge']) {
  const cat = catchments.catchments[name];
  if (!cat) continue;
  const pts = [];
  for (const [a, b, c2, d] of cat.segments) {
    pts.push(new THREE.Vector3(X(a), surfaceAt(a, b) + 25, Z(b)), new THREE.Vector3(X(c2), surfaceAt(c2, d) + 25, Z(d)));
  }
  catchLines.add(new THREE.LineSegments(new THREE.BufferGeometry().setFromPoints(pts), catchMat));
}
world.add(catchLines);

// ---- reservoirs: fixed mapped outline at the DEM's own lake surface; storage shown by colour/column/label
const seqLo = new THREE.Color(0xcfe2f8); // sequential: one hue, light (empty) to dark (full)
const seqHi = new THREE.Color(0x154a8f);
const noData = new THREE.Color(0x6b6a64);
const waterMat = realisticWaterMaterial();
const reservoirs = {};
for (const w of vectors.waters) {
  const key = OUTLINES[w.id];
  if (!key) continue;
  const r = (reservoirs[key] ??= { meshes: [], sx: 0, sz: 0, n: 0, top: -Infinity, analMat: analyticalWaterMaterial(noData) });
  for (const ring of w.rings) {
    const inside = ring.filter(([lon, lat]) => inBox(lon, lat));
    if (inside.length < 3) continue;
    const surface = terrain.medianInside(inside);
    if (surface === null) continue;
    const geo = new THREE.ShapeGeometry(new THREE.Shape(inside.map(([lon, lat]) => new THREE.Vector2(X(lon), -Z(lat)))));
    geo.rotateX(-Math.PI / 2);
    const mesh = new THREE.Mesh(geo, waterMat);
    mesh.position.y = surface + 1.5;
    world.add(mesh);
    r.meshes.push(mesh);
    for (const [lon, lat] of inside) { r.sx += X(lon); r.sz += Z(lat); r.n++; }
    r.top = Math.max(r.top, surface);
  }
}
for (const [key, r] of Object.entries(reservoirs)) {
  if (!r.n) continue;
  r.x = r.sx / r.n;
  r.z = r.sz / r.n;
  r.frame = new THREE.LineSegments(new THREE.EdgesGeometry(new THREE.BoxGeometry(1500, COLUMN_M, 1500)),
    new THREE.LineBasicMaterial({ color: 0xf0efec, transparent: true, opacity: 0.7 }));
  r.fill = new THREE.Mesh(new THREE.BoxGeometry(1300, 1, 1300), new THREE.MeshLambertMaterial({ color: 0x3987e5 }));
  r.el = document.createElement('div');
  r.el.className = 'label';
  r.el.dataset.prio = '5';
  r.label = new CSS2DObject(r.el);
  markers.add(r.frame, r.fill, r.label);
  r.key = key;
}

// ---- ANA river gauges: a white dot each (grey on a day without a record)
const GAUGE_PX = 11;
const gauges = {};
const gaugeCodes = SCENE_GAUGES.filter((code) => { const g = ts.gauges[code]; return g && g.lat != null && inBox(g.lon, g.lat); });
const gaugeDots = new Symbols(gaugeCodes.length, { order: 9 });
markers.add(gaugeDots.group);
gaugeCodes.forEach((code, k) => {
  const g = ts.gauges[code];
  const el = document.createElement('div');
  el.className = 'label';
  el.dataset.prio = '3';
  const label = new CSS2DObject(el);
  pinLabel(label, GAUGE_PX);
  markers.add(label);
  gauges[code] = { k, code, el, label, x: X(g.lon), z: Z(g.lat), h: surfaceAt(g.lon, g.lat) };
});

// ---- rain, river and tunnel records on the terrain (scene/layers.js)
const records = layerData ? new RecordLayers({ data: layerData, dates: ts.dates, frame, surfaceAt, inBox }) : null;
if (records) {
  markers.add(records.group);
  terrain.setOverlay(records.overlayTexture());
}

// ---- floods in Atibaia town (scene/floods.js): the observed town gauge against its official alarm
// levels, and CPRM's official risk sectors. No modelled water: flood run 1 stopped before its test.
const floodData = layerData?.flood && inBox(layerData.flood.town.lon, layerData.flood.town.lat) ? layerData.flood : null;
const floods = floodData ? new FloodLayer({ data: floodData, dates: ts.dates, frame, surfaceAt }) : null;
const riskTex = floods ? floods.riskTexture(quality === 'high' ? 4096 : 2048) : null;
let riskOutline = null; // the sectors as outlines only, made when modelled water first shows (water is blue too)
if (floods) markers.add(floods.group);
if (riskTex) terrain.setDetailOverlay(riskTex.tex, riskTex.box);

// ---- modelled flood water (scene/floodwater.js): ONLY from a flood run that passed its test (the
// published file says accepted: true). An untested file is loaded only by the development server
// (?floodtest=1, from web/dev-data/, which the build does not copy), under a TEST RENDER banner.
const floodTest = import.meta.env.DEV && params.has('floodtest');
const waterData = floodTest
  ? await fetch(`${import.meta.env.BASE_URL}dev-data/flood_water_test.json`).then((r) => (r.ok ? r.json() : null)).catch(() => null)
  : await json('flood_water.json');
const water = waterData?.grid && (waterData.accepted === true || floodTest) ? new FloodWater({ data: waterData, frame, surfaceAt, test: floodTest }) : null;
if (water) world.add(water.group);
if (floodTest) {
  const b = document.createElement('div');
  b.className = 'test-banner';
  b.innerHTML = water
    ? `<b>TEST RENDER</b> · ${waterData.run}${waterData.frames[0]?.label ? ' (' + waterData.frames[0].label + ')' : ''}: untested, for checking the display only; never published.<br>Velocity ${waterData.velocity.split(':')[0]}.`
    : '<b>TEST RENDER</b> · no test file: run pipeline/flood_water_viewer.py --test first';
  host.appendChild(b);
}

// ---- 3D buildings (scene/buildings.js): streamed around the view target when the camera is close
const buildings = new BuildingLayer({ terrain, frame, base: DATA, quality });
const hasBuildings = await buildings.init();
scene.add(buildings.group, buildings.shadowGroup);
if (!hasBuildings) {
  $('lyr-bld').checked = false;
  $('lyr-bld').disabled = true;
  $('lyr-bld').parentElement.title = 'Buildings not built (npm --prefix web run buildings)';
}
$('bld-legend').innerHTML = '<div class="muted">Building height from</div>'
  + [2, 1, 3, 4, 0].map((k) => `<span><i style="background:${SOURCE_COLOURS[k][0]}"></i>${SOURCE_COLOURS[k][1]}</span>`).join('');
for (const p of buildings.places) $('goto').add(new Option(p.name, `${p.lon},${p.lat}`));
$('goto-row').hidden = !buildings.places.length;

let showColumns = style === 'analytical';
let storageT = {}; // reservoir -> fraction stored (or null) for the current date
function placeMarkers() {
  for (const r of Object.values(reservoirs)) {
    if (!r.fill) continue;
    const base = r.top * exag + 60;
    const t = storageT[r.key];
    const hgt = Math.max(20, (t ?? 0) * COLUMN_M);
    r.frame.position.set(r.x, base + COLUMN_M / 2, r.z);
    r.fill.scale.y = hgt;
    r.fill.position.set(r.x, base + hgt / 2, r.z);
    r.frame.visible = showColumns;
    r.fill.visible = showColumns && t !== null && t !== undefined;
    r.label.position.set(r.x, base + (showColumns ? COLUMN_M + 700 : 900), r.z);
  }
  for (const g of Object.values(gauges)) {
    gaugeDots.setPos(g.k, g.x, g.h * exag + 2, g.z);
    g.label.position.set(g.x, g.h * exag + 2, g.z);
  }
  gaugeDots.commit();
}

// ---- view: style, sun, relief, haze, layers
function sunTime(dateIso) {
  const [y, m, d] = dateIso.split('-').map(Number);
  return new Date(Date.UTC(y, m - 1, d) + (hour - UTC_OFFSET_H) * 3600e3);
}
function applyStyle() {
  const real = style === 'realistic';
  scene.background = real ? null : new THREE.Color(0x111110);
  atmosphere.setEnabled(real);
  terrain.setStyle(style);
  riverFlow.setLook(real ? 0x8fc4ec : 0x7fb4ee);
  water?.setStyle(real);
  catchMat.opacity = real ? 0.6 : 0.75;
  for (const r of Object.values(reservoirs)) for (const m of r.meshes) {
    m.material = real ? waterMat : r.analMat;
    m.renderOrder = real ? 0 : 2;
  }
  applyShadows();
  buildings.setStyle(style);
  $('bld-legend').hidden = real || !hasBuildings || !$('lyr-bld').checked;
  document.querySelectorAll('#style button').forEach((b) => b.classList.toggle('on', b.dataset.style === style));
  document.body.classList.toggle('analytical', !real);
  $('lyr-columns').checked = showColumns;
  show(index);
}
let shownExag = exag;
function applyRelief() {
  // keep the view: heights of camera and target scale with the relief
  const k = exag / shownExag;
  controls.target.y *= k;
  camera.position.y *= k;
  shownExag = exag;
  world.scale.y = exag;
  buildings.setExaggeration(exag);
  placeMarkers();
  records?.place(exag);
  floods?.place(exag);
  $('exag').textContent = exag === 1 ? 'true scale (×1)' : `×${exag}`;
}
function sunText() {
  const p = atmosphere.sunPos;
  const hh = String(Math.floor(hour)).padStart(2, '0');
  const mm = String(Math.round((hour % 1) * 60)).padStart(2, '0');
  $('hour-out').textContent = `${hh}:${mm}`;
  $('sun-out').textContent = style !== 'realistic' ? 'Fixed light (analytical style)'
    : p.elevation < 0 ? `Sun below the horizon on ${ts.dates[index]} (lit as twilight)`
      : `Sun on ${ts.dates[index]}: ${p.elevation.toFixed(0)}° up, bearing ${p.azimuth.toFixed(0)}°`;
}

$('style').addEventListener('click', (e) => {
  const s = e.target.dataset?.style;
  if (!s || s === style) return;
  style = s;
  showColumns = style === 'analytical';
  applyStyle();
  placeMarkers();
});
$('hour').value = String(hour);
$('hour').addEventListener('input', () => { hour = Number($('hour').value); lastSunDay = null; show(index); });
$('relief').value = String(exag);
$('relief').addEventListener('change', () => { exag = Number($('relief').value); applyRelief(); });
$('haze').value = haze;
$('haze').addEventListener('change', () => { haze = $('haze').value; atmosphere.set({ haze }); sunText(); });
$('lyr-shadow').addEventListener('change', (e) => { shadows = e.target.checked; applyShadows(); });
$('lyr-catch').addEventListener('change', (e) => { catchLines.visible = e.target.checked; });
$('lyr-rain').addEventListener('change', (e) => { if (records) records.rainGroup.visible = e.target.checked; });
$('lyr-flows').addEventListener('change', (e) => {
  if (records) { records.flowGroup.visible = e.target.checked; records.tunnelGroup.visible = e.target.checked; }
});
$('lyr-upcatch').addEventListener('change', (e) => terrain.setOverlay(e.target.checked && records ? records.overlayTexture() : null));
if (!records) for (const id of ['lyr-rain', 'lyr-flows', 'lyr-upcatch']) { $(id).checked = false; $(id).disabled = true; }
$('lyr-rivers').addEventListener('change', (e) => { rivers.visible = e.target.checked; });
$('lyr-particles').addEventListener('change', (e) => {
  riverParticles.visible = e.target.checked;
  if (water) water.points.visible = e.target.checked;
});
$('lyr-flood').addEventListener('change', (e) => {
  if (!floods) return;
  floods.group.visible = e.target.checked;
  floods.riskOn = e.target.checked;
  riskOverlay();
});
if (!floods) { $('lyr-flood').checked = false; $('lyr-flood').disabled = true; }
$('lyr-water').addEventListener('change', () => show(index));
if (!water) {
  $('lyr-water').checked = false;
  $('lyr-water').disabled = true;
  $('lyr-water').parentElement.title = 'No flood run has passed its test yet, so no modelled water is shown';
}
$('lyr-bld').addEventListener('change', (e) => {
  buildings.setEnabled(e.target.checked);
  $('bld-legend').hidden = style === 'realistic' || !e.target.checked;
});
$('goto').addEventListener('change', (e) => {
  if (!e.target.value) return;
  const [lon, lat] = e.target.value.split(',').map(Number);
  flyTo(lon, lat);
  e.target.value = '';
});
$('lyr-columns').addEventListener('change', (e) => { showColumns = e.target.checked; placeMarkers(); });
$('lyr-lc').addEventListener('change', async (e) => {
  if (e.target.checked && !terrain.landcoverTex) {
    try {
      await terrain.loadLandcover(DATA + 'landcover.png');
    } catch {
      e.target.checked = false; // not built yet: npm --prefix web run basemap
      e.target.disabled = true;
      e.target.parentElement.title = 'Land cover not built (npm --prefix web run basemap)';
      return;
    }
  }
  terrain.setLandcover(e.target.checked);
  $('lc-legend').hidden = !e.target.checked;
});
$('lc-legend').innerHTML = '<div class="muted">ESA WorldCover 2021</div>' + [10, 20, 30, 40, 50, 60, 80, 90]
  .map((k) => `<span><i style="background:${LANDCOVER[k][1]}"></i>${LANDCOVER[k][0]}</span>`).join('');
$('reset').addEventListener('click', () => homeView());
function setCardOpen(open) {
  $('view').classList.toggle('collapsed', !open);
  $('view-toggle').setAttribute('aria-expanded', String(open));
  $('view-toggle').textContent = open ? 'View ▾' : 'View ▸';
}
$('view-toggle').addEventListener('click', () => setCardOpen($('view').classList.contains('collapsed')));
setCardOpen(innerWidth >= 1100);

function homeView() {
  flight = null;
  const ty = surfaceAt(lon0, lat0 - 0.05) * exag;
  // oblique enough that the sky and the haze at the horizon are in view
  controls.target.set(-2000, ty, 2000);
  camera.position.set(-14000, ty + 30000, 68000);
  controls.update();
}

// Fly to a town (the "Go to" menu): keep the compass bearing, look down at about 35 degrees from 1.8 km.
let flight = null;
function flyTo(lon, lat, dist = 1800) {
  const to = new THREE.Vector3(X(lon), surfaceAt(lon, lat) * exag, Z(lat));
  const az = Math.atan2(camera.position.x - controls.target.x, camera.position.z - controls.target.z);
  const up = 0.62;
  const cam = to.clone().add(new THREE.Vector3(Math.sin(az) * Math.cos(up), Math.sin(up), Math.cos(az) * Math.cos(up)).multiplyScalar(dist));
  flight = { t0: performance.now(), dur: 1800, fromT: controls.target.clone(), fromC: camera.position.clone(), toT: to, toC: cam };
}
function flightStep(now) {
  const k = Math.min(1, (now - flight.t0) / flight.dur);
  const e = k < 0.5 ? 4 * k * k * k : 1 - (-2 * k + 2) ** 3 / 2; // ease in-out
  // travel high: the camera rises over the midpoint so the flight does not skim the hills
  const lift = Math.sin(Math.PI * e) * 0.35 * flight.fromC.distanceTo(flight.toC);
  controls.target.lerpVectors(flight.fromT, flight.toT, e);
  camera.position.lerpVectors(flight.fromC, flight.toC, e);
  camera.position.y += lift;
  if (k >= 1) flight = null;
}
controls.addEventListener('start', () => { flight = null; });

// ---- panel: rain, rivers above the lakes, tunnels (observed, except catchment rain, which is derived)
function recordsPanel() {
  const i = index;
  const r = records;
  const mm = (v) => (v === null ? '<span class="nodata">–</span>' : v.toFixed(v < 10 ? 1 : 0));
  const rain = [['cachoeira_dam', 'Cachoeira'], ['atibainha_dam', 'Atibainha']].map(([k, n]) =>
    `<tr><td>${n}</td><td>${mm(r.catchRainOn(k, i))}</td><td>${mm(r.catchRainSum(k, i, 7))}</td><td>${mm(r.catchRainSum(k, i, 30))}</td></tr>`).join('');
  const rivers = ['1430', '1397'].map((id) => {
    const s = r.station(id);
    const q = r.flowOn(s, i);
    return `<tr><td>${s.label.replace(' above the lake', '')}</td><td>${q === null ? '<span class="nodata">no record</span>' : q.toFixed(2)}</td>`
      + `<td>${q === null ? '' : (q * 86.4 / s.area_km2).toFixed(2)}</td></tr>`;
  }).join('');
  const tunnels = layerData.tunnels.map((t) => {
    const q = t.station ? r.flowOn(r.station(t.station), i) : null;
    return `<tr><td>${t.name}<br><span class="muted">${t.from} → ${t.to}</span></td><td>${!t.measured ? '<span class="nodata">not public</span>'
      : q === null ? '<span class="nodata">no record</span>' : q.toFixed(1)}</td></tr>`;
  }).join('');
  $('rec-body').innerHTML = `
    <table><thead><tr><th>Catchment rain, mm <i class="tag">derived</i></th><th>Day</th><th>7 days</th><th>30 days</th></tr></thead><tbody>${rain}</tbody></table>
    <table><thead><tr><th>River above the lake</th><th>m³/s</th><th>mm/day</th></tr></thead><tbody>${rivers}</tbody></table>
    <table><thead><tr><th>Tunnels and transfers</th><th>m³/s</th></tr></thead><tbody>${tunnels}</tbody></table>`;
}

// ---- panel: floods in Atibaia town (observed gauge; floods derived from it; official risk sectors)
const cap = (t) => t[0].toUpperCase() + t.slice(1);
function floodPanel() {
  const i = index;
  const lv = floodData.town.levels_cm;
  const cm = floods.levelOn(i);
  const st = statusOf(cm, lv);
  const q = floods.flowOn(i);
  const dn = floods.downstreamOn(i);
  const m = (v) => (v / 100).toFixed(2);
  const ev = floods.eventOn(i);
  const gap = cm === null ? null : cm - lv.extravasation;
  const status = st === null ? 'No record this day'
    : st.key === 'extravasation' ? `Overflow: ${m(gap)} m over the overflow level`
      : `${cap(st.name)}: ${m(-gap)} m under the overflow level`;
  const levels = LEVELS.filter((l) => lv[l.key] !== undefined).map((l) =>
    `<tr${st?.key === l.key ? ' class="on"' : ''}><td><i class="sw" style="background:${l.color}"></i>${cap(l.name)}</td><td>${m(lv[l.key])}</td></tr>`).join('');
  $('flood-prev').disabled = floods.eventFrom(i, -1) === null;
  $('flood-next').disabled = floods.eventFrom(i, 1) === null;
  $('flood-body').innerHTML = `
    <div class="kv"><span>Town gauge 3E-063, highest level that day</span><b>${cm === null ? 'no record' : m(cm) + ' m'}</b></div>
    <div class="flood-status" style="--c:${st ? st.color : '#77756d'}">${status}</div>
    <div class="kv"><span>Mean flow that day (SP Águas rating)</span><b>${q === null ? '–' : q.toFixed(1) + ' m³/s'}</b></div>
    <div class="kv"><span>4 km downstream (ANA 62671200), highest level</span><b>${dn === null ? 'no record' : m(dn) + ' m'}</b></div>
    <table><thead><tr><th>Official alarm levels at 3E-063 (SP Águas)</th><th>m</th></tr></thead><tbody>${levels}</tbody></table>
    <div class="kv derived"><span>Flood on this day <i>derived</i></span><b>${ev ? `peak ${m(ev.peak_cm)} m` : 'none'}</b></div>`
    + (ev ? `<div class="muted small">${ev.first} to ${ev.last}: ${ev.days_above} day${ev.days_above > 1 ? 's' : ''} at or over the overflow
      level; peak on ${ev.peak_date}</div>` : '');
}

// ---- the risk sectors on the terrain: filled, or outlines only while modelled water is shown
let riskShown = riskTex?.tex;
function riskOverlay() {
  if (!riskTex) return;
  let tex = null;
  if ($('lyr-flood').checked) {
    if (water?.group.visible) tex = (riskOutline ??= floods.riskTexture(quality === 'high' ? 4096 : 2048, false)).tex;
    else tex = riskTex.tex;
  }
  if (tex !== riskShown) { terrain.setDetailOverlay(tex, riskTex.box); riskShown = tex; }
}

// ---- legend of the modelled flood water (depth colours, particle speed colours, the display speed-up)
function waterLegend() {
  const el = $('water-legend');
  const on = water && water.group.visible;
  el.hidden = !on;
  if (!on) return;
  const ramp = (stops) => `linear-gradient(90deg, ${stops.join(', ')})`;
  el.innerHTML = `<div><b>Modelled flood water</b>${water.test ? ' <span class="test-tag">TEST RENDER</span>' : ''}</div>`
    + `<div>Depth</div><div class="ramp" style="background:${ramp(['#6cbbe3', '#0c3c84'])}"></div><div class="ends"><span>0</span><span>3 m and more</span></div>`
    + `<div>Particles: speed of the modelled flow</div><div class="ramp" style="background:${ramp(SPEED_STOPS.map((s) => s[1]))}"></div>`
    + `<div class="ends"><span>0</span><span>0.5</span><span>1.5 m/s</span></div>`
    + `<div class="muted small">Particles move about ${Math.round(water.speedUp ?? 0)} times faster than the water at this zoom. ${waterData.run}; ${waterData.status}.</div>`;
}
if (water) {
  $('water-note').textContent = water.test
    ? 'TEST RENDER of untested model output (development only): it is not a flood and is never published.'
    : `Modelled water: ${waterData.run}, ${waterData.status}. Velocity: ${waterData.velocity}.`;
}

// ---- panel tables
const resBody = document.querySelector('#res-table tbody');
const resRows = {};
for (const [key, r] of Object.entries(ts.reservoirs)) {
  const tr = document.createElement('tr');
  tr.innerHTML = `<td>${r.name}</td><td></td><td></td><td></td><td></td>`;
  resBody.appendChild(tr);
  resRows[key] = tr.children;
}
const gaugeBody = document.querySelector('#gauge-table tbody');
const gaugeRows = {};
for (const [code, g] of Object.entries(ts.gauges)) {
  const tr = document.createElement('tr');
  tr.innerHTML = `<td>${SHORT[code] ?? g.name}</td><td>${g.area_km2 ?? '–'}</td><td></td>`;
  gaugeBody.appendChild(tr);
  gaugeRows[code] = tr.children;
}
const MODEL_RES = { cachoeira_dam: 'cachoeira', atibainha_dam: 'atibainha' };
const modelBody = document.querySelector('#model-table tbody');
const modelRows = {};
const verdicts = [];
for (const [name, m] of Object.entries(ts.model ?? {})) {
  const tr = document.createElement('tr');
  tr.innerHTML = `<td>${m.label}<span class="${m.accepted ? 'badge-ok' : 'badge-no'}">${m.accepted ? 'validated' : 'failed validation'}</span></td><td></td><td></td><td></td>`;
  modelBody.appendChild(tr);
  modelRows[name] = tr.children;
  if (m.summary) { verdicts.push(m.summary); continue; }
  const p = m.periods;
  const fmtP = (k) => (p[k] && p[k].kge !== null ? `${p[k].kge.toFixed(2)} (benchmark ${p[k].benchmark_kge.toFixed(2)})` : 'n/a');
  verdicts.push(`${m.label}: KGE drought 2014–16 ${fmtP('A_drought_2014_2016')}, 2017 on ${fmtP('B_recent_2017_on')}, 1986–2001 ${fmtP('C_early_1986_2001')}.`);
}
$('model-note').textContent = verdicts.length
  ? `Inflow in m³/s. ${verdicts.join(' ')} Acceptance needed low-flow bias within ±50% in both folds. A model that failed validation is not shown.`
  : 'No model results yet.';
$('stamp').textContent = `Records to ${ts.dates.at(-1)}. Data file built ${ts.generated_utc.slice(0, 10)}. Sources: ANA SAR; ANA HidroSerieHistorica; `
  + 'SP Águas SIBH telemetry; Serviço Geológico do Brasil (CPRM) risk sectors, Atibaia, 2012; '
  + 'Copernicus DEM GLO-30; contains modified Copernicus Sentinel data 2024; ESA WorldCover 2021 (CC BY 4.0); © OpenStreetMap contributors; '
  + 'Microsoft Global ML Building Footprints (ODbL); Google Open Buildings 2.5D Temporal (CC BY 4.0).';

const cell = (td, v, d = 1) => {
  const s = fmt(v, d);
  td.textContent = s ?? 'no data';
  td.className = s === null ? 'nodata' : '';
};

// ---- chart: one measure at a time, chosen from the menu (never two y-scales)
const canvas = $('chart');
const ctx = canvas.getContext('2d');
const PAD = { l: 34, r: 36, t: 6, b: 18 };
const N = ts.dates.length;
const OBS = '#3987e5';
const MOD = '#d95926';

function smooth(arr, w) { // centred running mean; a window with any gap stays a gap
  const out = new Array(arr.length).fill(null);
  const h = Math.floor(w / 2);
  let sum = 0;
  let bad = 0;
  for (let i = 0; i < arr.length; i++) {
    const add = arr[i];
    if (add === null) bad++; else sum += add;
    if (i >= w) { const rem = arr[i - w]; if (rem === null) bad--; else sum -= rem; }
    if (i >= w - 1 && bad === 0) out[i - h] = sum / w;
  }
  return out;
}

const charts = {
  storage: {
    title: 'System storage, % of useful volume',
    sub: '· dashed: band thresholds (Normal ≥ 60, Atenção ≥ 40, Alerta ≥ 30, Restrição ≥ 20) · below 0 = dead-volume use',
    unit: '%', series: [{ name: 'Observed', color: OBS, data: ts.system.pct, raw: ts.system.pct }], bands: true,
  },
};
for (const [name, m] of Object.entries(ts.model ?? {})) {
  const obs = ts.reservoirs[MODEL_RES[name]].inflow;
  const series = [{ name: 'Observed', color: OBS, data: smooth(obs, 30), raw: obs }];
  let band = null;
  if (m.accepted) {
    series.push({ name: 'Modelled', color: MOD, data: smooth(m.sim, 30), raw: m.sim });
    band = { low: smooth(m.low, 30), high: smooth(m.high, 30) };
  }
  charts[name] = {
    title: `${m.label} inflow, m³/s`,
    sub: m.accepted ? '· 30-day running mean · shaded: parameter-ensemble range' : '· 30-day running mean · model failed validation, so only the observation is drawn',
    unit: ' m³/s', series, band,
  };
}
// Observed rain, river and tunnel records (layers.json). Orange stays reserved for modelled series.
const TEAL = '#2bb3a3';
const VIOLET = '#b48cff';
function trailingSum(arr, w) { // total of the w days ending on each day; a window with a gap stays a gap
  const out = new Array(arr.length).fill(null);
  let sum = 0;
  let bad = 0;
  for (let i = 0; i < arr.length; i++) {
    if (arr[i] === null) bad++; else sum += arr[i];
    if (i >= w) { if (arr[i - w] === null) bad--; else sum -= arr[i - w]; }
    if (i >= w - 1 && bad === 0) out[i] = sum;
  }
  return out;
}
if (records) {
  const full = (s, vals) => { // a contiguous series -> an array on the viewer's dates
    const a = new Array(N).fill(null);
    const o = ts.dates.indexOf(s.first);
    if (o >= 0) vals.forEach((v, k) => { if (o + k < N) a[o + k] = v; });
    return a;
  };
  const cr = layerData.catchment_rain;
  const st = (id) => layerData.flow_stations.find((s) => s.id === id);
  const flow7 = (id) => smooth(full(st(id), st(id).q), 7);
  const area = (n) => layerData.catchments.masks[n]?.area_km2;
  charts.rain = {
    title: 'Catchment rain, 30-day total, mm (derived)', windowed: true, unit: ' mm',
    sub: '· inverse-distance mean of the audited gauges within 20 km of each catchment centroid · a 30-day window with a missing day stays a gap',
    series: [{ name: 'Cachoeira', color: OBS, data: trailingSum(full(cr.cachoeira_dam, cr.cachoeira_dam.mm), 30) },
      { name: 'Atibainha', color: TEAL, data: trailingSum(full(cr.atibainha_dam, cr.atibainha_dam.mm), 30) }],
  };
  for (const [key, id, res, catchName, dam] of [['upC', '1430', 'cachoeira', 'cachoeira_upstream_gauge', 'cachoeira_dam'],
    ['upA', '1397', 'atibainha', 'atibainha_upstream_gauge', 'atibainha_dam']]) {
    charts[key] = {
      title: `${ts.reservoirs[res].name}: river above the lake (${st(id).code}) and operator inflow, m³/s`, windowed: true, unit: ' m³/s',
      sub: `· 7-day running means · the gauge drains ${area(catchName)} of the ${area(dam)} km² catchment (DEM) · the inflow is the operator's, from the reservoir balance`,
      series: [{ name: `River above the lake (${st(id).code})`, color: TEAL, data: flow7(id), win: true },
        { name: 'Operator inflow (SAR)', color: OBS, data: smooth(ts.reservoirs[res].inflow, 7) }],
    };
  }
  charts.tunnels = {
    title: 'Tunnels 6 and 5: measured outlet flow, m³/s', windowed: true, unit: ' m³/s',
    sub: '· 7-day running means · Tunnel 7 and the Paraíba do Sul transfer have no public flow record',
    series: [{ name: 'Tunnel 6 (Cachoeira → Atibainha)', color: VIOLET, data: flow7('12'), win: true },
      { name: 'Tunnel 5 (Atibainha → Paiva Castro)', color: TEAL, data: flow7('18'), win: true }],
  };
}
if (floods) {
  const onDates = (g) => { // a contiguous gauge series in cm -> metres on the viewer's dates
    const a = new Array(N).fill(null);
    const o = ts.dates.indexOf(g.first);
    if (o >= 0) g.max_cm.forEach((v, k) => { if (o + k < N) a[o + k] = v === null ? null : v / 100; });
    return a;
  };
  const lv = floodData.town.levels_cm;
  const spans = floodData.events.map((e) => [ts.dates.indexOf(e.first), ts.dates.indexOf(e.last)]).filter(([a, b]) => a >= 0 && b >= 0);
  charts.flood = {
    title: 'Atibaia town (3E-063): highest river level each day, m', windowed: true, unit: ' m', digits: 2, step: 1, spans,
    sub: '· SP Águas gauge, own zero · dashed: official alarm levels · shaded: floods (derived)',
    series: [{ name: 'Town gauge 3E-063', color: OBS, data: onDates(floodData.town) }],
    lines: LEVELS.filter((l) => lv[l.key] !== undefined)
      .map((l) => ({ v: lv[l.key] / 100, color: l.color, name: cap(l.name), label: l.key === 'extravasation' })),
  };
  charts.floodDown = {
    title: 'Rio Atibaia 4 km below the town (ANA 62671200): highest level each day, m', windowed: true, unit: ' m', digits: 2, step: 2, spans,
    sub: "· the station's own zero, not the town gauge's · no alarm levels published · readings over 10 m dropped as faults",
    series: [{ name: 'ANA 62671200', color: TEAL, data: onDates(floodData.downstream) }],
  };

  const by = {};
  for (const s of floodData.risk?.sectors ?? []) {
    const b = (by[s.type] ??= { n: 0, homes: 0, people: 0 });
    b.n++; b.homes += s.homes ?? 0; b.people += s.people ?? 0;
  }
  $('risk-body').innerHTML = Object.keys(by).length
    ? '<table><thead><tr><th>Official risk sectors (CPRM, 2012)</th><th>Sectors</th><th>Homes</th><th>People</th></tr></thead><tbody>'
      + Object.entries(by).map(([t, b]) => `<tr><td><i class="sw" style="background:rgb(${RISK_STYLE[t]?.rgb ?? [200, 200, 200]})"></i>`
        + `${cap(RISK_STYLE[t]?.en ?? t)}</td><td>${b.n}</td><td>${b.homes}</td><td>${b.people}</td></tr>`).join('') + '</tbody></table>'
    : '';
  const later = floodData.events.filter((e) => e.peak_date > ts.dates.at(-1));
  $('flood-count').textContent = `${floodData.events.length} floods since ${floodData.town.first.slice(0, 4)}`;
  if (later.length) { // the gauge record runs past the reservoir record that sets the viewer's dates
    $('flood-count').title = `${later.length} of them peaked after ${ts.dates.at(-1)}, the last replayed day: ${later.map((e) => e.peak_date).join(', ')}`;
    $('flood-count').textContent += ` (${later.length} after the last day)`;
  }
  $('flood-prev').addEventListener('click', () => { const k = floods.eventFrom(index, -1); if (k !== null) show(k); });
  $('flood-next').addEventListener('click', () => { const k = floods.eventFrom(index, 1); if (k !== null) show(k); });
  $('flood-goto').addEventListener('click', () => flyTo(floodData.town.lon, floodData.town.lat, 2600));
  // the floods' peak days, marked along the date slider
  $('flood-ticks').innerHTML = floodData.events.map((e) => {
    const k = ts.dates.indexOf(e.peak_date);
    return k < 0 ? '' : `<i style="left:${((100 * k) / (N - 1)).toFixed(3)}%"></i>`;
  }).join('');
}
$('flood-sec').hidden = !floods;
const pick = $('chart-pick');
for (const [k, c] of Object.entries(charts)) pick.add(new Option(c.title, k));
let chart = charts.storage;
let yMin = 0;
let yMax = 100;
let i0 = 0; // the chart's date window: series that start late get the axis they need
let i1 = N - 1;
function useChart(k) {
  chart = charts[k];
  i0 = 0;
  i1 = N - 1;
  if (chart.windowed) {
    // the window starts with the record that defines it (a comparison only means something where both exist)
    const def = chart.series.some((sr) => sr.win) ? chart.series.filter((sr) => sr.win) : chart.series;
    i0 = Math.min(...def.map((sr) => sr.data.findIndex((v) => v !== null)).filter((j) => j >= 0));
    i0 = Math.max(0, ts.dates.indexOf(ts.dates[i0].slice(0, 4) + '-01-01') >= 0 ? ts.dates.indexOf(ts.dates[i0].slice(0, 4) + '-01-01') : i0);
  }
  const all = chart.series.flatMap((sr) => sr.data.slice(i0, i1 + 1)).concat(chart.band ? chart.band.high : []).filter((v) => v !== null);
  if (chart.bands) { yMin = Math.min(0, Math.floor(Math.min(...all) / 10) * 10); yMax = 100; }
  else { yMin = 0; yMax = Math.ceil(Math.max(...all) / 5) * 5; }
  $('chart-sub').textContent = chart.sub;
  $('legend').innerHTML = (chart.series.length > 1
    ? chart.series.map((sr) => `<span><i style="border-color:${sr.color}"></i>${sr.name}</span>`).join('')
      + (chart.band ? `<span><i class="band" style="background:${MOD}"></i>Ensemble range</span>` : '')
    : '') + (chart.lines ?? []).map((l) => `<span><i class="dash" style="border-color:${l.color}"></i>${l.name}</span>`).join('');
}
useChart('storage');
let cw = 0;
let ch = 0;
const px = (i) => PAD.l + ((i - i0) / (i1 - i0)) * (cw - PAD.l - PAD.r);
const py = (v) => PAD.t + (1 - (v - yMin) / (yMax - yMin)) * (ch - PAD.t - PAD.b);

function drawChart(cur, hover) {
  const dpr = Math.min(devicePixelRatio, 2);
  cw = canvas.clientWidth;
  ch = canvas.clientHeight;
  if (canvas.width !== Math.round(cw * dpr) || canvas.height !== Math.round(ch * dpr)) {
    canvas.width = Math.round(cw * dpr);
    canvas.height = Math.round(ch * dpr);
  }
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.clearRect(0, 0, cw, ch);
  ctx.font = '11px system-ui, sans-serif';
  ctx.textBaseline = 'middle';
  const stepY = chart.step ?? (chart.bands ? 20 : Math.max(5, Math.ceil(yMax / 5 / 5) * 5));
  for (let v = Math.ceil(yMin / stepY) * stepY; v <= yMax; v += stepY) {
    ctx.strokeStyle = v === 0 ? '#5a5a55' : '#2c2c2a';
    ctx.lineWidth = 1;
    ctx.beginPath(); ctx.moveTo(PAD.l, py(v)); ctx.lineTo(cw - PAD.r, py(v)); ctx.stroke();
    ctx.fillStyle = '#8f8e85';
    ctx.textAlign = 'right';
    ctx.fillText(String(v), PAD.l - 6, py(v));
  }
  if (chart.bands) {
    ctx.setLineDash([4, 4]);
    for (const b of ts.bands) {
      if (b.min_pct < 0) continue;
      ctx.strokeStyle = '#8f8e85';
      ctx.beginPath(); ctx.moveTo(PAD.l, py(b.min_pct)); ctx.lineTo(cw - PAD.r, py(b.min_pct)); ctx.stroke();
      ctx.fillStyle = '#c3c2b7';
      ctx.textAlign = 'left';
      ctx.fillText(`${b.min_pct}%`, cw - PAD.r + 5, py(b.min_pct));
    }
    ctx.setLineDash([]);
  }
  if (chart.lines) { // official levels: dashed, in their colours; only the top one labelled (they are 0.2 m apart)
    ctx.setLineDash([4, 4]);
    ctx.lineWidth = 1;
    for (const l of chart.lines) {
      ctx.strokeStyle = l.color;
      ctx.beginPath(); ctx.moveTo(PAD.l, py(l.v)); ctx.lineTo(cw - PAD.r, py(l.v)); ctx.stroke();
      if (!l.label) continue;
      ctx.fillStyle = l.color;
      ctx.textAlign = 'left';
      ctx.fillText(l.v.toFixed(2), cw - PAD.r + 4, py(l.v));
    }
    ctx.setLineDash([]);
  }
  if (chart.spans) { // derived flood periods
    ctx.fillStyle = '#c2185b40';
    for (const [a, b] of chart.spans) {
      if (b < i0) continue;
      const xa = px(Math.max(a, i0)) - 1;
      ctx.fillRect(xa, PAD.t, Math.max(2, px(b) + 1 - xa), ch - PAD.t - PAD.b);
    }
  }
  ctx.textAlign = 'center';
  ctx.fillStyle = '#8f8e85';
  let lastX = -99;
  for (let i = i0; i <= i1; i++) {
    if (ts.dates[i].endsWith('-01-01') && px(i) - lastX > 44) {
      ctx.fillText(ts.dates[i].slice(0, 4), px(i), ch - 7);
      ctx.strokeStyle = '#2c2c2a';
      ctx.beginPath(); ctx.moveTo(px(i), PAD.t); ctx.lineTo(px(i), ch - PAD.b); ctx.stroke();
      lastX = px(i);
    }
  }
  if (chart.band) { // ensemble range, drawn as thin vertical spans so gaps stay gaps
    ctx.strokeStyle = MOD;
    ctx.globalAlpha = 0.28;
    ctx.lineWidth = 1;
    ctx.beginPath();
    const stride2 = Math.max(1, Math.floor(N / (cw * 2)));
    for (let i = i0; i <= i1; i += stride2) {
      const l = chart.band.low[i];
      const h = chart.band.high[i];
      if (l === null || h === null) continue;
      ctx.moveTo(px(i), py(Math.min(h, yMax))); ctx.lineTo(px(i), py(l));
    }
    ctx.stroke();
    ctx.globalAlpha = 1;
  }
  for (const sr of chart.series) {
    ctx.strokeStyle = sr.color;
    ctx.lineWidth = 2;
    ctx.lineJoin = 'round';
    ctx.beginPath();
    let pen = false;
    for (let i = i0; i <= i1; i++) {
      const v = sr.data[i];
      if (v === null) { pen = false; continue; }
      if (pen) ctx.lineTo(px(i), py(v)); else ctx.moveTo(px(i), py(v));
      pen = true;
    }
    ctx.stroke();
  }
  const mark = (i, color, w) => {
    ctx.strokeStyle = color; ctx.lineWidth = w;
    ctx.beginPath(); ctx.moveTo(px(i), PAD.t); ctx.lineTo(px(i), ch - PAD.b); ctx.stroke();
    for (const sr of chart.series) {
      if (sr.data[i] === null) continue;
      ctx.fillStyle = '#1a1a19'; ctx.beginPath(); ctx.arc(px(i), py(sr.data[i]), 5, 0, 7); ctx.fill();
      ctx.fillStyle = sr.color; ctx.beginPath(); ctx.arc(px(i), py(sr.data[i]), 3.5, 0, 7); ctx.fill();
    }
  };
  if (hover !== null && hover !== cur && hover >= i0) mark(hover, '#8f8e85', 1);
  if (cur >= i0) mark(cur, '#f0efec', 1.5); // a date before the window is not marked
}

// ---- state
let index = N - 1;
let hoverIndex = null;
let playing = false;
let lastSunDay = null;
const slider = $('slider');
slider.max = String(N - 1);

function show(i) {
  index = Math.max(0, Math.min(N - 1, i));
  slider.value = String(index);
  $('date').textContent = ts.dates[index];
  $('hover-tip').hidden = true; // its values were for the previous date
  if (ts.dates[index] !== lastSunDay) { // the sun follows the replayed date (display only)
    lastSunDay = ts.dates[index];
    atmosphere.set({ time: sunTime(ts.dates[index]), haze });
  }
  sunText();
  const s = ts.system;
  const pct = s.pct[index];
  $('sys-pct').textContent = fmt(pct, 1) ?? 'no data';
  // Volume curves were revised on 1 April 2010; earlier percentages use the older capacity.
  const oldCurves = ts.dates[index] < ts.curve_revision_date;
  const capacity = fmt(s.capacity[index], 2) ?? ts.system_useful_hm3;
  $('sys-hm3').textContent = s.hm3[index] === null ? 'no data' : `${fmt(s.hm3[index], 1)} of ${capacity} hm³${oldCurves ? ' (pre-2010 curves)' : ''}`;
  // The five bands come from Joint Resolution ANA/DAEE 925 of 29 May 2017; they did not exist before.
  const ruled = ts.dates[index] >= RULES_FROM;
  const band = ruled ? ts.bands.find((b) => b.band === s.band[index]) : null;
  $('band').textContent = !ruled ? 'Before the 2017 operating rules' : band ? `Band ${band.band} · ${band.name}` : 'no data';
  $('sys-limit').textContent = !ruled ? 'not applicable' : band ? `${band.max_withdrawal_m3s} m³/s` : 'no data';
  $('sys-export').textContent = s.export30[index] === null ? 'no data' : `${fmt(s.export30[index], 1)} m³/s`;

  for (const [key, r] of Object.entries(ts.reservoirs)) {
    const td = resRows[key];
    cell(td[1], r.level[index], 2);
    cell(td[2], r.pct[index], 1);
    cell(td[3], r.inflow[index], 1);
    cell(td[4], r.release[index], 1);
    const o = reservoirs[key];
    if (!o || !o.fill) continue;
    const p = r.pct[index];
    const t = p === null ? null : Math.max(0, Math.min(1, p / 100));
    storageT[key] = t;
    o.analMat.color.copy(t === null ? noData : seqLo.clone().lerp(seqHi, t));
    const bar = p === null ? '' : `<div class="bar${p < 0 ? ' neg' : ''}"><i style="width:${Math.max(0, Math.min(100, p))}%"></i></div>`;
    o.el.innerHTML = `<b>${r.name}</b>${bar}<span>${p === null ? 'no data' : fmt(p, 1) + '% stored' + (p < 0 ? ' (below minimum operating level)' : '')}${r.level[index] === null ? '' : ' · ' + fmt(r.level[index], 2) + ' m'}</span>`;
  }
  placeMarkers();
  if (records) { records.show(index); recordsPanel(); }
  if (floods) { floods.show(index); floodPanel(); }
  if (water) {
    water.setFrame(water.frameFor(ts.dates[index]));
    if (!$('lyr-water').checked) water.group.visible = false;
  }
  riskOverlay();
  for (const [code, g] of Object.entries(ts.gauges)) {
    cell(gaugeRows[code][2], g.flow[index], 2);
    if (gauges[code]) {
      const f = g.flow[index];
      gauges[code].el.innerHTML = `<b>${SHORT[code]}</b><br><span>${f === null ? 'no data' : fmt(f, 2) + ' m³/s'}</span>`;
      gaugeDots.set(gauges[code].k, { size: GAUGE_PX, color: f === null ? 0x77756d : 0xf0efec });
    }
  }
  gaugeDots.commit();
  for (const [name, m] of Object.entries(ts.model ?? {})) {
    const td = modelRows[name];
    cell(td[1], ts.reservoirs[MODEL_RES[name]].inflow[index], 1);
    if (m.accepted) {
      cell(td[2], m.sim[index], 1);
      const l = m.low[index];
      td[3].textContent = l === null ? 'no data' : `${fmt(l, 1)}–${fmt(m.high[index], 1)}`;
      td[3].className = l === null ? 'nodata' : '';
    } else {
      td[2].textContent = 'not shown'; td[2].className = 'nodata';
      td[3].textContent = '–'; td[3].className = 'nodata';
    }
  }
  const q = ts.gauges['62670000']?.flow[index];
  const rc = ts.reservoirs.cachoeira.release[index];
  const ra = ts.reservoirs.atibainha.release[index];
  // displayed difference of three observed values; same formula as pipeline/process.py
  $('inc').textContent = q == null || rc == null || ra == null ? 'no data' : `${fmt(q - rc - ra, 2)} m³/s`;
  drawChart(index, hoverIndex);
}

slider.addEventListener('input', () => show(Number(slider.value)));
$('play').addEventListener('click', () => {
  playing = !playing;
  if (playing && index >= N - 1) show(0);
  $('play').textContent = playing ? 'Pause' : 'Play';
});
addEventListener('keydown', (e) => {
  if (e.target.tagName === 'SELECT' || e.target.tagName === 'INPUT') return;
  if (e.key === 'ArrowRight') show(index + 1);
  if (e.key === 'ArrowLeft') show(index - 1);
  if (e.key === ' ') { e.preventDefault(); $('play').click(); }
});

const tip = $('tip');
const indexAt = (e) => {
  const r = canvas.getBoundingClientRect();
  return Math.max(i0, Math.min(i1, i0 + Math.round(((e.clientX - r.left - PAD.l) / (cw - PAD.l - PAD.r)) * (i1 - i0))));
};
canvas.addEventListener('pointermove', (e) => {
  hoverIndex = indexAt(e);
  const v = chart.series[0].data[hoverIndex];
  tip.hidden = false;
  tip.textContent = `${ts.dates[hoverIndex]} · ` + chart.series.map((sr) =>
    `${chart.series.length > 1 ? sr.name + ' ' : ''}${sr.data[hoverIndex] === null ? 'no data' : sr.data[hoverIndex].toFixed(chart.digits ?? 1) + chart.unit}`).join(' · ');
  tip.style.left = `${Math.max(110, Math.min(cw - 110, px(hoverIndex)))}px`;
  tip.style.top = `${canvas.offsetTop + (v === null ? PAD.t + 20 : py(Math.min(v, yMax)))}px`;
  drawChart(index, hoverIndex);
});
canvas.addEventListener('pointerleave', () => { hoverIndex = null; tip.hidden = true; drawChart(index, null); });
canvas.addEventListener('click', (e) => show(indexAt(e)));
pick.addEventListener('change', () => { useChart(pick.value); drawChart(index, hoverIndex); });

function resize() {
  const w = host.clientWidth;
  const h = host.clientHeight;
  renderer.setSize(w, h);
  labels.setSize(w, h);
  riverFlow.setResolution(w, h);
  camera.aspect = w / h;
  camera.updateProjectionMatrix();
  drawChart(index, hoverIndex);
}
addEventListener('resize', resize);
resize();
applyRelief();
applyStyle();
homeView();
if (import.meta.env.DEV) window.__viewer = { camera, controls, atmosphere, terrain, scene, renderer, buildings, flyTo, riverFlow, water }; // debugging only
// the land-cover roughness cue (mapped water catches the sun) loads after the first frame
if (imagery) terrain.loadLandcover(DATA + 'landcover.png').catch(() => {});

let last = 0;
let prevT = performance.now();
renderer.setAnimationLoop((t) => {
  if (playing && t - last > 60) {
    last = t;
    const step = Number($('speed').value);
    if (index >= N - 1) { playing = false; $('play').textContent = 'Play'; } else show(index + step);
  }
  const dt = Math.min(0.1, (t - prevT) / 1000);
  prevT = t;
  if (flight) flightStep(t);
  controls.update();
  // keep the orbit centre on the ground (moving the camera with it), so zooming in to a town on a hill
  // or in a valley ends at the town, not above or under it
  if (!flight) {
    const dy = (terrain.meshAtXZ(controls.target.x, controls.target.z) * exag - controls.target.y) * 0.15;
    if (Math.abs(dy) > 0.01) { controls.target.y += dy; camera.position.y += dy; }
  }
  // keep the camera above the ground, and the near plane as far out as the view allows
  const ground = terrain.elevAtXZ(camera.position.x, camera.position.z) * exag;
  if (camera.position.y < ground + 25) camera.position.y = ground + 25;
  const near = THREE.MathUtils.clamp((camera.position.y - ground) * 0.25, 5, 3000);
  if (Math.abs(near - camera.near) > camera.near * 0.2) { camera.near = near; camera.updateProjectionMatrix(); }
  atmosphere.update(exag, dt);
  SYMBOL_UNIFORMS.uTime.value = t / 1000;
  const camDist = camera.position.distanceTo(controls.target);
  const mPerPx = (camDist * 2 * Math.tan(THREE.MathUtils.degToRad(camera.fov / 2))) / Math.max(1, host.clientHeight);
  riverFlow.tick(dt, controls.target, camDist, mPerPx, water?.group.visible ? (x, z) => water.wetAtXZ(x, z) : null);
  water?.tick(dt, camDist);
  if (water && frameNo % 30 === 0) waterLegend();
  records?.tick(t / 1000);
  if (frameNo % 6 === 0) for (const sy of symbolSets) sy.occlude(hiddenByTerrain);
  buildings.update(camera, controls.target, atmosphere.sunPos.elevation);
  renderer.render(scene, camera);
  if (++bldFrame % 30 === 0) buildingNote();
  labels.render(scene, camera);
  if (++frameNo % 3 === 0) declutter();
});

let bldFrame = 0;
function buildingNote() {
  if (!hasBuildings) return;
  const s = buildings.stats();
  $('bld-note').textContent = !$('lyr-bld').checked ? '' : s.shown ? (s.buildings ? `${s.buildings.toLocaleString()} drawn` : 'loading…') : 'zoom in to a town';
}

// Labels: where two overlap on screen, the lower-priority one is hidden (hover still describes it).
// Priority: reservoirs 5, measured tunnels and gauges above the lakes 4, ANA gauges 3, unmeasured tunnels 2, others 1.
let frameNo = 0;
function declutter() {
  const els = [...labels.domElement.querySelectorAll('.label')].filter((el) => el.style.display !== 'none');
  els.sort((a, b) => (Number(b.dataset.prio) || 0) - (Number(a.dataset.prio) || 0));
  const kept = [];
  for (const el of els) {
    const r = el.getBoundingClientRect();
    const clash = kept.some((k) => r.left < k.right + 4 && r.right > k.left - 4 && r.top < k.bottom + 2 && r.bottom > k.top - 2);
    el.style.visibility = clash ? 'hidden' : '';
    if (!clash) kept.push(r);
  }
}

// ---- hover: what a marker is, where it comes from, its value on the replayed date; else the building
// Ground point under a ray: march to the drawn surface (heights from the mesh, times the relief), then bisect.
function groundHit(r) {
  const p = r.origin.clone();
  let t = 0;
  let step = 0;
  for (let k = 0; k < 400 && t < 4e5; k++) {
    const h = p.y - terrain.meshAtXZ(p.x, p.z) * exag;
    if (h <= 0) {
      let lo = t - step;
      let hi = t;
      for (let b = 0; b < 12; b++) {
        const mid = (lo + hi) / 2;
        r.at(mid, p);
        if (p.y - terrain.meshAtXZ(p.x, p.z) * exag > 0) lo = mid; else hi = mid;
      }
      return r.at(hi, p);
    }
    step = Math.max(3, h * 0.5);
    t += step;
    r.at(t, p);
  }
  return null;
}

// Is a symbol on the ground at p hidden from the camera by the terrain? (march the sight line)
const symbolSets = [gaugeDots, records?.rain, records?.flow, floods?.gauge].filter(Boolean);
function hiddenByTerrain(p) {
  const c = camera.position;
  const q = new THREE.Vector3();
  for (let k = 1; k < 64; k++) {
    const f = k / 64;
    if (f > 0.97) break; // the last stretch is the slope the symbol stands on
    q.lerpVectors(c, p, f);
    if (q.y < terrain.meshAtXZ(q.x, q.z) * exag - 2) return true;
  }
  return false;
}
function gaugeHits(ndc, w, h) {
  return gaugeDots.hits(ndc, camera, w, h).map((hh) => {
    const code = gaugeCodes[hh.k];
    const f = ts.gauges[code].flow[index];
    return { ...hh, text: `<b>${ts.gauges[code].name}</b><br>ANA river gauge ${code}<br>${ts.dates[index]}: `
      + `${f === null ? 'no record' : fmt(f, 2) + ' m³/s, daily mean'}<br><i>observed; discharge from ANA's rating curve</i>` };
  });
}

{
  const ray = new THREE.Raycaster();
  const ndc = new THREE.Vector2();
  const hoverTip = $('hover-tip');
  let pending = null;
  renderer.domElement.addEventListener('pointermove', (e) => {
    pending = e;
    requestAnimationFrame(() => {
      if (!pending) return;
      const ev = pending;
      pending = null;
      const r = renderer.domElement.getBoundingClientRect();
      ndc.set(((ev.clientX - r.left) / r.width) * 2 - 1, -((ev.clientY - r.top) / r.height) * 2 + 1);
      ray.setFromCamera(ndc, camera);
      // flat symbols, tested on screen: several sites have a rain gauge and a river gauge side by side,
      // so up to two are described, nearest first
      const syms = [...(records ? records.symbolHits(ndc, camera, r.width, r.height) : []),
        ...(floods ? floods.symbolHits(ndc, camera, r.width, r.height) : []), ...gaugeHits(ndc, r.width, r.height)]
        .sort((a, b) => a.dpx - b.dpx); // symbols hidden by a hill are already off (occlude)
      const parts = syms.slice(0, 2).map((hh) => hh.text);
      if (!parts.length && records && records.tunnelGroup.visible && records.group.visible) { // tunnels: meshes
        const hit = ray.intersectObjects(records.pickables.filter((o) => o.visible), false)[0];
        const d = hit ? records.describe(hit) : null;
        if (d) parts.push(d);
      }
      let text = parts.length ? parts.join('<hr>') : null;
      if (!text) { // a building and/or the official risk sector it stands in
        const more = [];
        const b = hasBuildings ? buildings.pick(ray.ray) : null;
        if (b) more.push(BuildingLayer.describe(b.info));
        const g = floods?.riskOn || water?.group.visible ? groundHit(ray.ray) : null;
        const wet = g && water ? water.describeAt(frame.lon(g.x), frame.lat(g.z)) : null;
        if (wet) more.push(wet);
        const sec = g && floods ? floods.riskAt(frame.lon(g.x), frame.lat(g.z)) : null;
        if (sec) more.push(floods.describeRisk(sec));
        text = more.length ? more.join('<hr>') : null;
      }
      hoverTip.hidden = !text;
      if (text) {
        hoverTip.innerHTML = text;
        hoverTip.style.left = `${ev.clientX - r.left + 14}px`;
        hoverTip.style.top = `${ev.clientY - r.top + 14}px`;
      }
      renderer.domElement.style.cursor = text ? 'help' : '';
    });
  });
  renderer.domElement.addEventListener('pointerleave', () => { hoverTip.hidden = true; });
}
