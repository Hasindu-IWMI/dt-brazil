// Upper Atibaia viewer: replays OBSERVED daily records over a 3D terrain.
// The viewer computes nothing hydrological. Every number on screen is read
// from public/data/timeseries.json, produced by pipeline/process.py.
import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { CSS2DRenderer, CSS2DObject } from 'three/addons/renderers/CSS2DRenderer.js';

const EXAG = 4;          // vertical exaggeration of terrain (display choice)
const BASE_M = 600;      // elevation drawn at y = 0
const RULES_FROM = '2017-06-01';
const COLUMN_KM = 5;     // height of a full (100 %) storage column

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

const [terrainMeta, terrainBuf, vectors, ts, catchments] = await Promise.all([
  fetch('/data/terrain.json').then((r) => r.json()),
  fetch('/data/terrain.f32').then((r) => r.arrayBuffer()),
  fetch('/data/vectors.json').then((r) => r.json()),
  fetch('/data/timeseries.json').then((r) => r.json()),
  fetch('/data/catchments.json').then((r) => r.json()),
]);
const elev = new Float32Array(terrainBuf);
const { bbox, width: W, height: H } = terrainMeta;

// ---- geographic -> scene (km, local equirectangular about the window centre)
const lon0 = (bbox.west + bbox.east) / 2;
const lat0 = (bbox.south + bbox.north) / 2;
const KX = 111.32 * Math.cos((lat0 * Math.PI) / 180);
const KZ = 110.57;
const X = (lon) => (lon - lon0) * KX;
const Z = (lat) => -(lat - lat0) * KZ;
const Y = (m) => ((m - BASE_M) / 1000) * EXAG;
const inBox = (lon, lat) => lon >= bbox.west && lon <= bbox.east && lat >= bbox.south && lat <= bbox.north;

function elevAt(lon, lat) {
  const fx = ((lon - bbox.west) / (bbox.east - bbox.west)) * (W - 1);
  const fy = ((bbox.north - lat) / (bbox.north - bbox.south)) * (H - 1);
  const x0 = Math.max(0, Math.min(W - 2, Math.floor(fx)));
  const y0 = Math.max(0, Math.min(H - 2, Math.floor(fy)));
  const tx = Math.max(0, Math.min(1, fx - x0));
  const ty = Math.max(0, Math.min(1, fy - y0));
  const i = y0 * W + x0;
  return (elev[i] * (1 - tx) + elev[i + 1] * tx) * (1 - ty) + (elev[i + W] * (1 - tx) + elev[i + W + 1] * tx) * ty;
}

// ---- renderer
const host = $('scene');
const renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
host.appendChild(renderer.domElement);
const labels = new CSS2DRenderer();
labels.domElement.style.cssText = 'position:absolute;inset:0;pointer-events:none';
host.appendChild(labels.domElement);

const scene = new THREE.Scene();
scene.background = new THREE.Color(0x111110);
const camera = new THREE.PerspectiveCamera(40, 1, 0.1, 500);
camera.position.set(-6, 74, 88);
const controls = new OrbitControls(camera, renderer.domElement);
controls.target.set(0, 0.5, 6);
controls.maxPolarAngle = Math.PI * 0.48;
controls.minDistance = 8;
controls.maxDistance = 220;
controls.enableDamping = true;

scene.add(new THREE.HemisphereLight(0xffffff, 0x2a2a26, 0.9));
const sun = new THREE.DirectionalLight(0xffffff, 1.6);
sun.position.set(-40, 60, -30);
scene.add(sun);

// ---- terrain
{
  const wKm = (bbox.east - bbox.west) * KX;
  const hKm = (bbox.north - bbox.south) * KZ;
  const geo = new THREE.PlaneGeometry(wKm, hKm, W - 1, H - 1);
  geo.rotateX(-Math.PI / 2);
  const pos = geo.attributes.position;
  const col = new Float32Array(pos.count * 3);
  const lo = new THREE.Color(0x3d4a3c);
  const mid = new THREE.Color(0x6f745c);
  const hi = new THREE.Color(0xb9ae94);
  const c = new THREE.Color();
  const { minElevation: e0, maxElevation: e1 } = terrainMeta;
  for (let i = 0; i < pos.count; i++) {
    const m = elev[i];
    pos.setY(i, Y(m));
    const t = (m - e0) / (e1 - e0);
    if (t < 0.45) c.copy(lo).lerp(mid, t / 0.45); else c.copy(mid).lerp(hi, (t - 0.45) / 0.55);
    col.set([c.r, c.g, c.b], i * 3);
  }
  geo.setAttribute('color', new THREE.BufferAttribute(col, 3));
  geo.computeVertexNormals();
  scene.add(new THREE.Mesh(geo, new THREE.MeshLambertMaterial({ vertexColors: true })));
}

// ---- rivers (mapped lines, draped on the terrain)
{
  const mat = new THREE.LineBasicMaterial({ color: 0x7fb4ee, transparent: true, opacity: 0.85 });
  for (const r of vectors.rivers) {
    if (!RIVERS.includes(r.name)) continue;
    let pts = [];
    const flush = () => { if (pts.length > 1) scene.add(new THREE.Line(new THREE.BufferGeometry().setFromPoints(pts), mat)); pts = []; };
    for (const [lon, lat] of r.line) {
      if (!inBox(lon, lat)) { flush(); continue; }
      pts.push(new THREE.Vector3(X(lon), Y(elevAt(lon, lat)) + 0.06, Z(lat)));
    }
    flush();
  }
}

// ---- catchment boundaries delineated from the terrain (pipeline/delineate.py)
{
  const mat = new THREE.LineBasicMaterial({ color: 0xf0efec, transparent: true, opacity: 0.75 });
  for (const name of ['cachoeira_dam', 'atibainha_dam', 'atibaia_gauge']) {
    const cat = catchments.catchments[name];
    if (!cat) continue;
    const pts = [];
    for (const [a, b, c2, d] of cat.segments) {
      pts.push(new THREE.Vector3(X(a), Y(elevAt(a, b)) + 0.12, Z(b)), new THREE.Vector3(X(c2), Y(elevAt(c2, d)) + 0.12, Z(d)));
    }
    scene.add(new THREE.LineSegments(new THREE.BufferGeometry().setFromPoints(pts), mat));
  }
}

// ---- reservoirs: fixed mapped outline, coloured by observed storage; a column shows % stored
const seqLo = new THREE.Color(0xcfe2f8); // sequential: one hue, light (empty) to dark (full)
const seqHi = new THREE.Color(0x154a8f);
const noData = new THREE.Color(0x6b6a64);
const reservoirs = {};
for (const w of vectors.waters) {
  const key = OUTLINES[w.id];
  if (!key) continue;
  const r = (reservoirs[key] ??= { meshes: [], sx: 0, sz: 0, n: 0, top: -Infinity });
  for (const ring of w.rings) {
    const inside = ring.filter(([lon, lat]) => inBox(lon, lat));
    if (inside.length < 3) continue;
    const hs = inside.map(([lon, lat]) => elevAt(lon, lat)).sort((a, b) => a - b);
    const shoreline = hs[Math.floor(hs.length / 2)];
    const shape = new THREE.Shape(inside.map(([lon, lat]) => new THREE.Vector2(X(lon), -Z(lat))));
    const geo = new THREE.ShapeGeometry(shape);
    geo.rotateX(-Math.PI / 2);
    const mesh = new THREE.Mesh(geo, new THREE.MeshBasicMaterial({ color: noData, transparent: true, opacity: 0.92, depthTest: false }));
    mesh.position.y = Y(shoreline) + 0.05;
    mesh.renderOrder = 2;
    scene.add(mesh);
    r.meshes.push(mesh);
    for (const [lon, lat] of inside) { r.sx += X(lon); r.sz += Z(lat); r.n++; }
    r.top = Math.max(r.top, Y(shoreline));
  }
}
for (const [key, r] of Object.entries(reservoirs)) {
  if (!r.n) continue;
  const x = r.sx / r.n;
  const z = r.sz / r.n;
  const frame = new THREE.LineSegments(
    new THREE.EdgesGeometry(new THREE.BoxGeometry(0.9, COLUMN_KM, 0.9)),
    new THREE.LineBasicMaterial({ color: 0xf0efec, transparent: true, opacity: 0.7 }));
  frame.position.set(x, r.top + COLUMN_KM / 2 + 0.1, z);
  scene.add(frame);
  const fill = new THREE.Mesh(new THREE.BoxGeometry(0.8, 1, 0.8), new THREE.MeshLambertMaterial({ color: 0x3987e5 }));
  fill.position.set(x, r.top + 0.1, z);
  scene.add(fill);
  const el = document.createElement('div');
  el.className = 'label';
  const lab = new CSS2DObject(el);
  lab.position.set(x, r.top + COLUMN_KM + 1.1, z);
  scene.add(lab);
  Object.assign(r, { fill, el, base: r.top + 0.1 });
}

// ---- gauges
const gaugeLabels = {};
for (const code of SCENE_GAUGES) {
  const g = ts.gauges[code];
  if (!g || g.lat == null || !inBox(g.lon, g.lat)) continue;
  const y = Y(elevAt(g.lon, g.lat));
  const pin = new THREE.Mesh(new THREE.ConeGeometry(0.35, 1.2, 12), new THREE.MeshLambertMaterial({ color: 0xf0efec }));
  pin.rotation.x = Math.PI;
  pin.position.set(X(g.lon), y + 0.7, Z(g.lat));
  scene.add(pin);
  const el = document.createElement('div');
  el.className = 'label';
  const lab = new CSS2DObject(el);
  lab.position.set(X(g.lon), y + 2.0, Z(g.lat));
  scene.add(lab);
  gaugeLabels[code] = el;
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
$('exag').textContent = EXAG;
$('stamp').textContent = `Records to ${ts.dates.at(-1)}. Data file built ${ts.generated_utc.slice(0, 10)}. Sources: ANA SAR; ANA HidroSerieHistorica; Copernicus DEM; © OpenStreetMap contributors.`;

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
const pick = $('chart-pick');
for (const [k, c] of Object.entries(charts)) pick.add(new Option(c.title, k));
let chart = charts.storage;
let yMin = 0;
let yMax = 100;
function useChart(k) {
  chart = charts[k];
  const all = chart.series.flatMap((sr) => sr.data).concat(chart.band ? chart.band.high : []).filter((v) => v !== null);
  if (chart.bands) { yMin = Math.min(0, Math.floor(Math.min(...all) / 10) * 10); yMax = 100; }
  else { yMin = 0; yMax = Math.ceil(Math.max(...all) / 5) * 5; }
  $('chart-sub').textContent = chart.sub;
  $('legend').innerHTML = chart.series.length > 1
    ? chart.series.map((sr) => `<span><i style="border-color:${sr.color}"></i>${sr.name}</span>`).join('') + `<span><i class="band" style="background:${MOD}"></i>Ensemble range</span>`
    : '';
}
useChart('storage');
let cw = 0;
let ch = 0;
const px = (i) => PAD.l + (i / (N - 1)) * (cw - PAD.l - PAD.r);
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
  const stepY = chart.bands ? 20 : Math.max(5, Math.ceil(yMax / 5 / 5) * 5);
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
  ctx.textAlign = 'center';
  ctx.fillStyle = '#8f8e85';
  let lastX = -99;
  for (let i = 0; i < N; i++) {
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
    const stride = Math.max(1, Math.floor(N / (cw * 2)));
    for (let i = 0; i < N; i += stride) {
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
    for (let i = 0; i < N; i++) {
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
  if (hover !== null && hover !== cur) mark(hover, '#8f8e85', 1);
  mark(cur, '#f0efec', 1.5);
}

// ---- state
let index = N - 1;
let hoverIndex = null;
let playing = false;
const slider = $('slider');
slider.max = String(N - 1);

function show(i) {
  index = Math.max(0, Math.min(N - 1, i));
  slider.value = String(index);
  $('date').textContent = ts.dates[index];
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
    const colour = t === null ? noData : seqLo.clone().lerp(seqHi, t);
    for (const m of o.meshes) m.material.color.copy(colour);
    const hgt = Math.max(0.02, (t ?? 0) * COLUMN_KM);
    o.fill.scale.y = hgt;
    o.fill.position.y = o.base + hgt / 2;
    o.fill.visible = t !== null;
    o.el.innerHTML = `<b>${r.name}</b><br><span>${p === null ? 'no data' : fmt(p, 1) + '% stored' + (p < 0 ? ' (below minimum operating level)' : '')}${r.level[index] === null ? '' : ' · ' + fmt(r.level[index], 2) + ' m'}</span>`;
  }
  for (const [code, g] of Object.entries(ts.gauges)) {
    cell(gaugeRows[code][2], g.flow[index], 2);
    if (gaugeLabels[code]) {
      const f = g.flow[index];
      gaugeLabels[code].innerHTML = `<b>${SHORT[code]}</b><br><span>${f === null ? 'no data' : fmt(f, 2) + ' m³/s'}</span>`;
    }
  }
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
  if (e.target.tagName === 'SELECT') return;
  if (e.key === 'ArrowRight') show(index + 1);
  if (e.key === 'ArrowLeft') show(index - 1);
  if (e.key === ' ') { e.preventDefault(); $('play').click(); }
});

const tip = $('tip');
const indexAt = (e) => {
  const r = canvas.getBoundingClientRect();
  return Math.max(0, Math.min(N - 1, Math.round(((e.clientX - r.left - PAD.l) / (cw - PAD.l - PAD.r)) * (N - 1))));
};
canvas.addEventListener('pointermove', (e) => {
  hoverIndex = indexAt(e);
  const v = chart.series[0].data[hoverIndex];
  tip.hidden = false;
  tip.textContent = `${ts.dates[hoverIndex]} · ` + chart.series.map((sr) =>
    `${chart.series.length > 1 ? sr.name + ' ' : ''}${sr.data[hoverIndex] === null ? 'no data' : sr.data[hoverIndex].toFixed(1) + chart.unit}`).join(' · ');
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
  camera.aspect = w / h;
  camera.updateProjectionMatrix();
  drawChart(index, hoverIndex);
}
addEventListener('resize', resize);
resize();
show(index);

let last = 0;
renderer.setAnimationLoop((t) => {
  if (playing && t - last > 60) {
    last = t;
    const step = Number($('speed').value);
    if (index >= N - 1) { playing = false; $('play').textContent = 'Play'; } else show(index + step);
  }
  controls.update();
  renderer.render(scene, camera);
  labels.render(scene, camera);
});
