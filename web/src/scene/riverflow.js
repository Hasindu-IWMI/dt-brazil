// Mapped rivers: optional lines of a fixed width on screen, and particles that drift downstream
// across the whole width of each river, faster mid-channel than at the banks.
// OpenStreetMap draws every waterway in the direction of flow, so the order of a line's points gives
// the direction; nothing is modelled. The particles' speed is a display rate, NOT a measured or
// modelled velocity, and the faster middle is drawn, not measured. The band they fill is the river's
// mapped width (the OpenStreetMap width tag where there is one, else a nominal width), never narrower
// than a few pixels on screen. The particles are placed afresh every frame from a hash of their slot
// along the river, so their density on screen is the same at any zoom and only the rivers near the
// view are computed.
import * as THREE from 'three';
import { Line2 } from 'three/addons/lines/Line2.js';
import { LineGeometry } from 'three/addons/lines/LineGeometry.js';
import { LineMaterial } from 'three/addons/lines/LineMaterial.js';
import { trailMaterial } from './trails.js';

export const RIVER_WIDTH_M = { 'Rio Atibaia': 11 }; // OpenStreetMap width tag (as used by flood run 1)
export const NOMINAL_WIDTH_M = 12; // rivers with no mapped width
const MIN_BAND_PX = 7; // the band is never narrower than this on screen
const SLOT_M = 2; // the finest spacing of particle slots along a river
const SCREEN_GAP_PX = 4; // aimed spacing on screen: slots are thinned in steps of two as you zoom out
const MAX = 16000; // particles drawn at most
const TRAIL = 3; // points per particle: the head and a fading tail
const TRAIL_SIZE = [3.2, 2.5, 1.8];
const TRAIL_ALPHA = [0.92, 0.5, 0.22];
const hash = (x) => { const s = Math.sin(x * 12.9898 + 78.233) * 43758.5453; return s - Math.floor(s); };

export class RiverFlow {
  constructor() {
    this.material = new LineMaterial({ color: 0x7fb4ee, linewidth: 2.2 });
    this.paths = [];
    this.travel = 0;
    this.t = 0;
    this.points = null;
  }

  /** A line along points listed downstream (scene metres), on the river called name. */
  line(points, name) {
    const g = new LineGeometry();
    g.setPositions(points.flatMap((p) => [p.x, p.y, p.z]));
    const cum = new Float32Array(points.length);
    for (let k = 1; k < points.length; k++) cum[k] = cum[k - 1] + points[k].distanceTo(points[k - 1]);
    const xs = points.map((p) => p.x);
    const zs = points.map((p) => p.z);
    this.paths.push({ pts: points, cum, len: cum[points.length - 1], width: RIVER_WIDTH_M[name] ?? NOMINAL_WIDTH_M,
      box: [Math.min(...xs), Math.max(...xs), Math.min(...zs), Math.max(...zs)], seed: this.paths.length * 7919.13 });
    return new Line2(g, this.material);
  }

  /** The particle layer: a THREE.Points to add to the scene. */
  buildParticles() {
    const g = new THREE.BufferGeometry();
    const attr = (name, k) => { const a = new THREE.BufferAttribute(new Float32Array(MAX * TRAIL * k), k); a.setUsage(THREE.DynamicDrawUsage); g.setAttribute(name, a); return a; };
    this.pos = attr('position', 3);
    this.alpha = attr('aAlpha', 1);
    const size = attr('aSize', 1);
    const tint = attr('aTint', 3);
    const c = new THREE.Color(0xeaf7ff);
    for (let k = 0; k < MAX * TRAIL; k++) { size.setX(k, TRAIL_SIZE[k % TRAIL]); tint.setXYZ(k, c.r, c.g, c.b); }
    g.setDrawRange(0, 0);
    this.points = new THREE.Points(g, trailMaterial());
    this.points.frustumCulled = false;
    this.points.renderOrder = 4;
    return this.points;
  }

  setLook(color) { this.material.color.set(color); }
  setResolution(w, h) { this.material.resolution.set(w, h); }

  /** Per frame: dt in seconds; target = the orbit centre (scene); dist = camera distance to it (m);
   * mPerPx = metres per screen pixel there; skip(x, z) true leaves a particle out (where modelled
   * flood water draws its own particles). */
  tick(dt, target, dist, mPerPx, skip = null) {
    if (!this.points || !this.points.visible) return;
    this.t += dt;
    const stride = 2 ** Math.max(0, Math.round(Math.log2((SCREEN_GAP_PX * mPerPx) / SLOT_M)));
    this.travel += 30 * mPerPx * dt; // display rate: about 30 px a second mid-channel
    const step = 3.2 * mPerPx; // tail spacing: about 3 px
    const reach = dist * 3; // rivers farther than this from the orbit centre are left out
    const pos = this.pos.array;
    const a = this.alpha.array;
    const p = new THREE.Vector3();
    const tan = new THREE.Vector3();
    let n = 0;
    for (const path of this.paths) {
      const [x0, x1, z0, z1] = path.box;
      if (Math.hypot(Math.max(x0 - target.x, 0, target.x - x1), Math.max(z0 - target.z, 0, target.z - z1)) > reach) continue;
      const half = Math.max(path.width / 2, (MIN_BAND_PX / 2) * mPerPx);
      const slots = Math.floor(path.len / SLOT_M);
      for (let i = 0; i < slots && n < MAX; i += stride) {
        const u = hash(path.seed + i) - 0.5; // across the river: -0.5 one bank, 0.5 the other
        const f = 1 - 0.6 * (2 * u) ** 2; // faster mid-channel (drawn, not measured)
        const lateral = (u + 0.06 * Math.sin(this.t * 0.8 + 6.28 * hash(path.seed - i))) * 2 * half;
        const d = ((i + hash(path.seed + i + 0.37) * stride) * SLOT_M + this.travel * f) % path.len;
        const base = n * TRAIL;
        let kept = true;
        for (let j = 0; j < TRAIL; j++) {
          const dj = d - j * step;
          if (dj < 0) { a[base + j] = 0; continue; }
          at(path, dj, p, tan);
          p.x += -tan.z * lateral; // across the river, in the ground plane
          p.z += tan.x * lateral;
          if (j === 0 && skip && skip(p.x, p.z)) { kept = false; break; }
          pos[(base + j) * 3] = p.x;
          pos[(base + j) * 3 + 1] = p.y + 3;
          pos[(base + j) * 3 + 2] = p.z;
          a[base + j] = TRAIL_ALPHA[j];
        }
        if (kept) n++;
      }
    }
    this.count = n;
    this.points.geometry.setDrawRange(0, n * TRAIL);
    for (const at2 of [this.pos, this.alpha]) {
      at2.clearUpdateRanges();
      at2.addUpdateRange(0, n * TRAIL * at2.itemSize);
      at2.needsUpdate = true;
    }
  }
}

/** The point at distance d along a path, and the unit tangent there (binary search on lengths). */
function at(path, d, out, tan) {
  const { cum, pts } = path;
  let lo = 0;
  let hi = cum.length - 1;
  while (hi - lo > 1) { const m = (lo + hi) >> 1; if (cum[m] <= d) lo = m; else hi = m; }
  const f = cum[hi] > cum[lo] ? (d - cum[lo]) / (cum[hi] - cum[lo]) : 0;
  tan.set(pts[hi].x - pts[lo].x, 0, pts[hi].z - pts[lo].z).normalize();
  return out.lerpVectors(pts[lo], pts[hi], f);
}
