// Schematic lake flow: particles drifting across each reservoir along the flow in lakefield.js, from
// where water enters (mapped river mouths, tunnel and transfer outlets, and evenly over the lake) to
// where it leaves (the dams and tunnel intakes). DISPLAY ONLY: the pattern follows a stated rule, not a
// model or measurement of lake currents, and the drift speed is a display rate, slower than the river
// particles' (real through-flow is millimetres a second; wind moves most lake water). The fields are
// computed in a worker, one per lake, and the particles start when they arrive.
// Particles are spawned evenly over the lake water near the view, at a fixed spacing on screen, and
// live a few seconds; slow water (the arms) draws them slower and fainter, and almost still water
// (arm heads, ponds joined to no outlet) not at all.
import * as THREE from 'three';
import { trailMaterial } from './trails.js';
import { cellAt, flowAt, variantOn } from './lakefield.js';

const MAX = 9000; // particles at most
const GAP_PX = 13; // aimed spacing on screen at the orbit centre (sparser toward the horizon)
const RATE_PX = 8; // drift on screen, px per second, where the flow is at its lake's typical speed (rivers: 30)
const STILL = 0.003; // below this share of the typical speed the water counts as still (arm heads, cut-off ponds)
const FAINT = 0.03; // below this share particles are drawn fainter
const TRAIL = 3;
const TRAIL_SIZE = [2.8, 2.2, 1.6];
const TRAIL_ALPHA = [0.8, 0.42, 0.18];
const TAIL_PX = 2.6; // tail spacing on screen at the typical speed
const BLOCK = 16; // spawn bookkeeping: cells per block side
const TINT = new THREE.Color(0xd9ecfb);

export class LakeFlow {
  /** lakes: [{ key, polys: [[ring [[x, z], ...], ...], ...], heights: [y per polygon] }] in scene metres;
   * rivers: [{ name, pts }] listed downstream; tunnels: [{ name, a, b, since }]. */
  constructor({ lakes, rivers, tunnels }) {
    this.domains = [];
    this.state = 'computing';
    this.date = null;
    const g = new THREE.BufferGeometry();
    const attr = (name, k) => { const a = new THREE.BufferAttribute(new Float32Array(MAX * TRAIL * k), k); a.setUsage(THREE.DynamicDrawUsage); g.setAttribute(name, a); return a; };
    this.pos = attr('position', 3);
    this.alpha = attr('aAlpha', 1);
    const size = attr('aSize', 1);
    const tint = attr('aTint', 3);
    for (let k = 0; k < MAX * TRAIL; k++) { size.setX(k, TRAIL_SIZE[k % TRAIL]); tint.setXYZ(k, TINT.r, TINT.g, TINT.b); }
    g.setDrawRange(0, 0);
    this.points = new THREE.Points(g, trailMaterial());
    this.points.frustumCulled = false;
    this.points.renderOrder = 4;
    this.px = new Float32Array(MAX);
    this.pz = new Float32Array(MAX);
    this.age = new Float32Array(MAX);
    this.life = new Float32Array(MAX);
    this.dom = new Int16Array(MAX).fill(-1); // -1: slot empty
    this.hi = 0; // slots in use are below this
    this.v = [0, 0];
    this.compute(lakes, rivers, tunnels);
  }

  async compute(lakes, rivers, tunnels) {
    const jobs = lakes.map((lake, id) => this.solve({ id, polys: lake.polys, rivers: nearRivers(rivers, lake.polys), tunnels })
      .then((res) => this.addDomain(lake, res))
      .catch((err) => { console.warn(`lake flow (${lake.key}) not computed:`, err); }));
    await Promise.all(jobs);
    this.state = this.domains.length ? 'ready' : 'error';
  }

  /** One lake's fields from a worker (or on this thread where workers are unavailable). */
  solve(job) {
    if (typeof Worker === 'undefined') return import('./lakefield.js').then((m) => ({ id: job.id, ...m.lakeField(job.polys, job.rivers, job.tunnels) }));
    return new Promise((resolve, reject) => {
      const w = new Worker(new URL('./lakefield.worker.js', import.meta.url), { type: 'module' });
      w.onmessage = ({ data }) => { w.terminate(); if (data.error) reject(new Error(data.error)); else resolve(data); };
      w.onerror = (e) => { w.terminate(); reject(e); };
      w.postMessage(job);
    });
  }

  addDomain(lake, { grid, ends, variants }) {
    const nb = { c: Math.ceil(grid.W / BLOCK), r: Math.ceil(grid.H / BLOCK) };
    // per variant: the moving-water cells (where particles are spawned), listed by block
    const blockOf = (i) => Math.floor(Math.floor(i / grid.W) / BLOCK) * nb.c + Math.floor((i % grid.W) / BLOCK);
    for (const v of variants) {
      const f = v.field;
      const moving = (i) => grid.polyOf[i] >= 0 && Math.hypot(f.vx[i], f.vz[i]) >= STILL * f.vref;
      v.blocks = new Int32Array(nb.c * nb.r);
      for (let i = 0; i < grid.W * grid.H; i++) if (moving(i)) v.blocks[blockOf(i)]++;
      v.start = new Int32Array(nb.c * nb.r + 1);
      for (let b = 0; b < nb.c * nb.r; b++) v.start[b + 1] = v.start[b] + v.blocks[b];
      v.cells = new Int32Array(v.start.at(-1));
      const fill = v.start.slice(0, -1);
      for (let i = 0; i < grid.W * grid.H; i++) if (moving(i)) v.cells[fill[blockOf(i)]++] = i;
    }
    const d = { key: lake.key, grid, ends, variants, nb, heights: lake.heights };
    d.cur = this.date ? variantOn(variants, this.date) : variants.at(-1);
    this.domains.push(d);
  }

  /** The replayed date: an end with a start date (the Paraíba do Sul transfer) is used from then on. */
  setDate(dateIso) {
    this.date = dateIso;
    for (const d of this.domains) d.cur = variantOn(d.variants, dateIso);
  }

  /** Is (x, z) on a lake's water (its outline, on the 30 m grid)? The river particles stop there. */
  covers(x, z) {
    for (const d of this.domains) {
      const k = cellAt(d.grid, x, z);
      if (k >= 0 && d.grid.polyOf[k] >= 0) return true;
    }
    return false;
  }

  stats() {
    return { state: this.state, drawn: this.count ?? 0, ends: this.domains.map((d) => ({ key: d.key, ends: d.cur.ends.map((e) => `${e.kind} ${e.name || 'river'}`) })) };
  }

  /** Per frame: dt in seconds; target = orbit centre (scene); dist = camera distance to it; mPerPx =
   * metres per screen pixel there. */
  tick(dt, target, dist, mPerPx) {
    if (!this.points.visible || !this.domains.length) { this.points.geometry.setDrawRange(0, 0); this.count = 0; return; }
    // the blocks near the view, weighted by their moving water, and how many particles they need
    const reach = Math.max(dist * 1.6, 2000);
    const cands = [];
    let cells = 0;
    this.domains.forEach((d, di) => {
      const { grid: g, nb } = d;
      const c0 = Math.max(0, Math.floor((target.x - reach - g.x0) / (g.cell * BLOCK)));
      const c1 = Math.min(nb.c - 1, Math.floor((target.x + reach - g.x0) / (g.cell * BLOCK)));
      const r0 = Math.max(0, Math.floor((target.z - reach - g.z0) / (g.cell * BLOCK)));
      const r1 = Math.min(nb.r - 1, Math.floor((target.z + reach - g.z0) / (g.cell * BLOCK)));
      for (let r = r0; r <= r1; r++) {
        for (let c = c0; c <= c1; c++) {
          const n = d.cur.blocks[r * nb.c + c];
          if (n) { cells += n; cands.push(di, r * nb.c + c, cells); }
        }
      }
    });
    const cellArea = this.domains[0].grid.cell ** 2;
    const want = Math.min(MAX, Math.round((cells * cellArea) / (GAP_PX * mPerPx) ** 2));
    const pos = this.pos.array;
    const a = this.alpha.array;
    const v = this.v;
    let hi = 0;
    let n = 0;
    for (let k = 0; k < Math.max(this.hi, want); k++) {
      let di = this.dom[k];
      if (di >= 0) { // move with the flow
        const d = this.domains[di];
        const f = d.cur.field;
        flowAt(d.grid, f, this.px[k], this.pz[k], v);
        const s = Math.hypot(v[0], v[1]) / f.vref;
        const step = s > 0 ? (RATE_PX * mPerPx * Math.min(2, Math.sqrt(s)) * dt) / (s * f.vref) : 0;
        this.px[k] += v[0] * step;
        this.pz[k] += v[1] * step;
        this.age[k] += dt;
        const cell = cellAt(d.grid, this.px[k], this.pz[k]);
        const gone = cell < 0 || d.grid.polyOf[cell] < 0 || s < STILL || this.age[k] > this.life[k]
          || Math.abs(this.px[k] - target.x) > reach || Math.abs(this.pz[k] - target.z) > reach;
        if (gone) { this.dom[k] = -1; di = -1; }
      }
      if (di < 0 && k < want && cands.length) { di = this.spawn(k, cands, cells); }
      const base = k * TRAIL;
      if (di < 0) { for (let j = 0; j < TRAIL; j++) a[base + j] = 0; continue; }
      // head and a tail traced back along the flow
      const d = this.domains[di];
      const f = d.cur.field;
      const cell = cellAt(d.grid, this.px[k], this.pz[k]);
      const y = d.heights[d.grid.polyOf[cell]] ?? 0;
      const fade = Math.min(1, this.age[k] / 0.6, (this.life[k] - this.age[k]) / 0.6);
      let x = this.px[k];
      let z = this.pz[k];
      let vis = 1;
      for (let j = 0; j < TRAIL; j++) {
        if (j > 0) {
          flowAt(d.grid, f, x, z, v);
          const sp = Math.hypot(v[0], v[1]);
          if (sp === 0) { a[base + j] = 0; continue; }
          const back = TAIL_PX * mPerPx * Math.max(0.45, Math.min(1.4, Math.sqrt(sp / f.vref)));
          x -= (v[0] / sp) * back;
          z -= (v[1] / sp) * back;
        } else {
          flowAt(d.grid, f, x, z, v);
          vis = Math.min(1, Math.hypot(v[0], v[1]) / f.vref / FAINT); // almost still water fades out
        }
        pos[(base + j) * 3] = x;
        pos[(base + j) * 3 + 1] = y + 1;
        pos[(base + j) * 3 + 2] = z;
        a[base + j] = TRAIL_ALPHA[j] * fade * vis;
      }
      hi = k + 1;
      n++;
    }
    this.hi = hi;
    this.count = n;
    this.points.geometry.setDrawRange(0, hi * TRAIL);
    for (const at of [this.pos, this.alpha]) {
      at.clearUpdateRanges();
      at.addUpdateRange(0, hi * TRAIL * at.itemSize);
      at.needsUpdate = true;
    }
  }

  /** Put particle k on a random moving-water cell of a nearby block picked by its share of those cells. */
  spawn(k, cands, total) {
    const pick = Math.random() * total;
    let lo = 0;
    let hiI = cands.length / 3 - 1;
    while (lo < hiI) { const m = (lo + hiI) >> 1; if (cands[m * 3 + 2] <= pick) lo = m + 1; else hiI = m; }
    const di = cands[lo * 3];
    const block = cands[lo * 3 + 1];
    const d = this.domains[di];
    const g = d.grid;
    const v = d.cur;
    const i = v.cells[v.start[block] + Math.floor(Math.random() * v.blocks[block])];
    this.px[k] = g.x0 + ((i % g.W) + Math.random()) * g.cell;
    this.pz[k] = g.z0 + (Math.floor(i / g.W) + Math.random()) * g.cell;
    this.life[k] = 3 + Math.random() * 4;
    this.age[k] = k >= this.hi ? Math.random() * this.life[k] : 0; // a new slot starts part-way through its life
    this.dom[k] = di;
    return di;
  }
}

/** The river lines that come near a lake (its outline's box, widened by 2 km). */
function nearRivers(rivers, polys) {
  let x0 = Infinity; let x1 = -Infinity; let z0 = Infinity; let z1 = -Infinity;
  for (const rings of polys) for (const ring of rings) for (const [x, z] of ring) {
    x0 = Math.min(x0, x); x1 = Math.max(x1, x); z0 = Math.min(z0, z); z1 = Math.max(z1, z);
  }
  const m = 2000;
  return rivers.filter((r) => r.pts.some(([x, z]) => x > x0 - m && x < x1 + m && z > z0 - m && z < z1 + m));
}
