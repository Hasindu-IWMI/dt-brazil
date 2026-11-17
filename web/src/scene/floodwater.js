// Modelled flood water: depth and velocity from a flood run (data: flood_water.json, written by
// pipeline/flood_water_viewer.py). The viewer shows a published file only if its run passed its test
// (accepted: true); an untested file is only ever loaded in development (?floodtest=1), under a
// TEST RENDER banner.
//   water surface  the wet cells, draped 1 m over the drawn terrain, coloured by modelled depth
//                  (light shallow, dark deep) with the lakes' ripples and sky reflection; edges fade
//   particles      carried by the modelled velocity field, coloured by speed (white slow, yellow,
//                  orange fast). Sped up to be visible: the speed-up follows the camera distance
import * as THREE from 'three';
import { floodWaterMaterial } from './water.js';
import { trailMaterial } from './trails.js';

const SHALLOW = new THREE.Color(0x6cbbe3);
const DEEP = new THREE.Color(0x0c3c84);
export const SPEED_STOPS = [[0, '#eaf6ff'], [0.5, '#ffe08a'], [1.5, '#ff6b3d']]; // m/s
const N = 2400; // particles
const TRAIL = 6;

function decode(b64, Type) {
  const s = atob(b64);
  const u8 = new Uint8Array(s.length);
  for (let k = 0; k < s.length; k++) u8[k] = s.charCodeAt(k);
  return new Type(u8.buffer);
}
function speedColor(v, out) {
  const s = SPEED_STOPS;
  if (v <= s[0][0]) return out.set(s[0][1]);
  for (let k = 1; k < s.length; k++) {
    if (v <= s[k][0]) return out.set(s[k - 1][1]).lerp(new THREE.Color(s[k][1]), (v - s[k - 1][0]) / (s[k][0] - s[k - 1][0]));
  }
  return out.set(s[s.length - 1][1]);
}

export class FloodWater {
  constructor({ data, frame, surfaceAt, test }) {
    Object.assign(this, { data, frame, test });
    const g = data.grid;
    const W = (this.W = g.width);
    const H = (this.H = g.height);
    this.dmin = data.depth_min_m ?? 0.05;
    this.cellX = ((g.east - g.west) / W) * frame.KX; // metres
    this.cellZ = ((g.north - g.south) / H) * frame.KZ;
    this.lonAt = (c) => g.west + ((c + 0.5) * (g.east - g.west)) / W;
    this.latAt = (r) => g.north - ((r + 0.5) * (g.north - g.south)) / H;
    this.frames = data.frames.map((f) => ({
      date: f.date, label: f.label,
      depth: decode(f.depth_cm, Uint16Array), ve: decode(f.ve_cms, Int16Array), vn: decode(f.vn_cms, Int16Array),
    }));
    // ground under each cell centre, on the drawn terrain (unscaled: the group sits in the world group)
    this.hgt = new Float32Array(W * H);
    const pos = new Float32Array(W * H * 3);
    const nrm = new Float32Array(W * H * 3);
    for (let r = 0; r < H; r++) {
      for (let c = 0; c < W; c++) {
        const k = r * W + c;
        const lon = this.lonAt(c);
        const lat = this.latAt(r);
        this.hgt[k] = surfaceAt(lon, lat);
        pos.set([frame.X(lon), this.hgt[k] + 1, frame.Z(lat)], k * 3);
        nrm[k * 3 + 1] = 1;
      }
    }
    const geo = new THREE.BufferGeometry();
    geo.setAttribute('position', new THREE.BufferAttribute(pos, 3));
    geo.setAttribute('normal', new THREE.BufferAttribute(nrm, 3));
    geo.setAttribute('color', new THREE.BufferAttribute(new Float32Array(W * H * 4), 4));
    this.realMat = floodWaterMaterial();
    this.analMat = new THREE.MeshBasicMaterial({ vertexColors: true, transparent: true, depthWrite: false, side: THREE.DoubleSide,
      polygonOffset: true, polygonOffsetFactor: -4, polygonOffsetUnits: -8 });
    this.mesh = new THREE.Mesh(geo, this.realMat);
    this.mesh.renderOrder = 3;
    this.mesh.frustumCulled = false;

    // particles: TRAIL points each (head first), positions in scene metres
    const pg = new THREE.BufferGeometry();
    const attr = (name, k) => { const a = new THREE.BufferAttribute(new Float32Array(N * TRAIL * k), k); a.setUsage(THREE.DynamicDrawUsage); pg.setAttribute(name, a); return a; };
    this.ppos = attr('position', 3);
    this.palpha = attr('aAlpha', 1);
    this.ptint = attr('aTint', 3);
    const size = attr('aSize', 1);
    for (let k = 0; k < N * TRAIL; k++) size.setX(k, 3.4 - (2.0 * (k % TRAIL)) / TRAIL);
    this.points = new THREE.Points(pg, trailMaterial());
    this.points.frustumCulled = false;
    this.points.renderOrder = 5;
    this.pc = new Float32Array(N); // grid coordinates (cell c spans [c, c+1))
    this.pr = new Float32Array(N);
    this.age = new Float32Array(N);
    this.life = new Float32Array(N);
    this.hist = new Float32Array(N * TRAIL * 3);

    this.group = new THREE.Group();
    this.group.add(this.mesh, this.points);
    this.cur = -1;
    this.setFrame(0);
  }

  /** The frame to show on a date (a test file's undated frame shows on every date), or -1. */
  frameFor(dateIso) {
    const k = this.frames.findIndex((f) => f.date === dateIso);
    return k >= 0 ? k : this.test ? this.frames.findIndex((f) => !f.date) : -1;
  }

  setFrame(k) {
    this.group.visible = k >= 0;
    if (k < 0 || k === this.cur) return;
    this.cur = k;
    const f = this.frames[k];
    const { W, H } = this;
    const col = this.mesh.geometry.attributes.color;
    const c = new THREE.Color();
    for (let i = 0; i < W * H; i++) {
      const d = f.depth[i] / 100;
      const t = Math.min(1, d / 3);
      c.copy(SHALLOW).lerp(DEEP, Math.sqrt(t));
      const a = d < this.dmin ? 0 : Math.min(1, d / 0.25) * (0.62 + 0.3 * t);
      col.setXYZW(i, c.r, c.g, c.b, a);
    }
    col.needsUpdate = true;
    // triangles over every 2 x 2 block of cell centres with water at any corner (dry corners fade out)
    const idx = [];
    const wet = (r, cc) => f.depth[r * W + cc] >= this.dmin * 100;
    for (let r = 0; r < H - 1; r++) {
      for (let cc = 0; cc < W - 1; cc++) {
        if (!(wet(r, cc) || wet(r + 1, cc) || wet(r, cc + 1) || wet(r + 1, cc + 1))) continue;
        const a = r * W + cc;
        idx.push(a, a + W, a + 1, a + 1, a + W, a + W + 1);
      }
    }
    this.mesh.geometry.setIndex(idx);
    // where particles start: cells with moving water (else any wet cell)
    const moving = [];
    const anyWet = [];
    for (let i = 0; i < W * H; i++) {
      if (f.depth[i] < this.dmin * 100) continue;
      anyWet.push(i);
      if (Math.hypot(f.ve[i], f.vn[i]) >= 5) moving.push(i);
    }
    this.seeds = moving.length ? moving : anyWet;
    for (let k = 0; k < N; k++) this.spawn(k, Math.random());
  }

  setStyle(real) { this.mesh.material = real ? this.realMat : this.analMat; }

  /** Is the scene point (x, z) on a wet cell of the shown frame? */
  wetAtXZ(x, z) {
    if (!this.group.visible || this.cur < 0) return false;
    const g = this.data.grid;
    const c = Math.floor(((this.frame.lon(x) - g.west) / (g.east - g.west)) * this.W);
    const r = Math.floor(((g.north - this.frame.lat(z)) / (g.north - g.south)) * this.H);
    if (c < 0 || r < 0 || c >= this.W || r >= this.H) return false;
    return this.frames[this.cur].depth[r * this.W + c] >= this.dmin * 100;
  }

  /** Bilinear sample of a cell-centred field at grid coordinates (c, r). */
  sample(field, c, r, scale = 1) {
    const { W, H } = this;
    const x = Math.min(W - 1, Math.max(0, c - 0.5));
    const y = Math.min(H - 1, Math.max(0, r - 0.5));
    const c0 = Math.floor(x);
    const r0 = Math.floor(y);
    const c1 = Math.min(W - 1, c0 + 1);
    const r1 = Math.min(H - 1, r0 + 1);
    const fx = x - c0;
    const fy = y - r0;
    const v = (rr, ccc) => field[rr * W + ccc];
    return (((v(r0, c0) * (1 - fx) + v(r0, c1) * fx) * (1 - fy)) + ((v(r1, c0) * (1 - fx) + v(r1, c1) * fx) * fy)) * scale;
  }

  scenePos(c, r, out) {
    const g = this.data.grid;
    const lon = g.west + (c / this.W) * (g.east - g.west);
    const lat = g.north - (r / this.H) * (g.north - g.south);
    return out.set(this.frame.X(lon), this.sample(this.hgt, c, r) + 4, this.frame.Z(lat));
  }

  spawn(k, ageFrac = 0) {
    const i = this.seeds[Math.floor(Math.random() * this.seeds.length)];
    if (i === undefined) { this.life[k] = 0; return; }
    this.pc[k] = (i % this.W) + Math.random();
    this.pr[k] = Math.floor(i / this.W) + Math.random();
    this.life[k] = 2 + Math.random() * 3;
    this.age[k] = ageFrac * this.life[k];
    const p = this.scenePos(this.pc[k], this.pr[k], new THREE.Vector3());
    for (let j = 0; j < TRAIL; j++) this.hist.set([p.x, p.y, p.z], (k * TRAIL + j) * 3);
  }

  /** Per frame: move the particles with the modelled velocity, sped up for display. */
  tick(dt, dist) {
    if (!this.group.visible || !this.points.visible || this.cur < 0) return;
    const f = this.frames[this.cur];
    const speedUp = Math.min(4000, Math.max(10, dist * 0.05));
    this.speedUp = speedUp;
    const p = new THREE.Vector3();
    const c = new THREE.Color();
    for (let k = 0; k < N; k++) {
      if (this.life[k] <= 0) { for (let j = 0; j < TRAIL; j++) this.palpha.setX(k * TRAIL + j, 0); continue; }
      const ve = this.sample(f.ve, this.pc[k], this.pr[k], 0.01);
      const vn = this.sample(f.vn, this.pc[k], this.pr[k], 0.01);
      const v = Math.hypot(ve, vn);
      this.pc[k] += (ve / this.cellX) * dt * speedUp;
      this.pr[k] -= (vn / this.cellZ) * dt * speedUp;
      this.age[k] += dt;
      const ci = Math.floor(this.pc[k]);
      const ri = Math.floor(this.pr[k]);
      const out = ci < 0 || ri < 0 || ci >= this.W || ri >= this.H || f.depth[ri * this.W + ci] < this.dmin * 100;
      if (out || this.age[k] > this.life[k] || v < 0.02) { this.spawn(k); continue; }
      const h = k * TRAIL * 3;
      this.hist.copyWithin(h + 3, h, h + (TRAIL - 1) * 3);
      this.scenePos(this.pc[k], this.pr[k], p);
      this.hist.set([p.x, p.y, p.z], h);
      speedColor(v, c);
      const fade = Math.min(1, this.age[k] / 0.4, (this.life[k] - this.age[k]) / 0.4);
      for (let j = 0; j < TRAIL; j++) {
        const o = k * TRAIL + j;
        this.ppos.setXYZ(o, this.hist[(o * 3)], this.hist[o * 3 + 1], this.hist[o * 3 + 2]);
        this.ptint.setXYZ(o, c.r, c.g, c.b);
        this.palpha.setX(o, fade * (0.95 - (0.85 * j) / TRAIL));
      }
    }
    this.ppos.needsUpdate = true;
    this.palpha.needsUpdate = true;
    this.ptint.needsUpdate = true;
  }

  /** Modelled depth and velocity at a geographic point, as hover text, or null when dry or outside. */
  describeAt(lon, lat) {
    if (!this.group.visible || this.cur < 0) return null;
    const g = this.data.grid;
    const c = Math.floor(((lon - g.west) / (g.east - g.west)) * this.W);
    const r = Math.floor(((g.north - lat) / (g.north - g.south)) * this.H);
    if (c < 0 || r < 0 || c >= this.W || r >= this.H) return null;
    const f = this.frames[this.cur];
    const i = r * this.W + c;
    const d = f.depth[i] / 100;
    if (d < this.dmin) return null;
    const ve = f.ve[i] / 100;
    const vn = f.vn[i] / 100;
    const v = Math.hypot(ve, vn);
    const dirs = ['north', 'north-east', 'east', 'south-east', 'south', 'south-west', 'west', 'north-west'];
    const toward = v >= 0.02 ? ` toward the ${dirs[Math.round(((Math.atan2(ve, vn) * 180) / Math.PI + 360) % 360 / 45) % 8]}` : '';
    return `<b>Modelled flood water</b>${this.test ? ' <span class="test-tag">TEST RENDER</span>' : ''}<br>`
      + `depth ${d.toFixed(2)} m · speed ${v.toFixed(2)} m/s${toward}<br>`
      + `<i>${this.data.run}${f.label ? ' · ' + f.label : ''}; ${this.data.status}. Velocity: ${this.data.velocity}.</i>`;
  }
}
