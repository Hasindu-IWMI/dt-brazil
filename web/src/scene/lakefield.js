// Schematic through-flow inside a lake: water moving from where it enters to where it leaves, with no
// flow through the shore. DISPLAY ONLY: it computes no hydrological number and is not a model of lake
// currents (wind and temperature layering drive most real circulation, and neither is here).
// The rule, on a 30 m grid over the mapped outline (steady potential flow):
//   in    an equal share at each mapped inlet: where a mapped river enters the outline, and each
//         tunnel or transfer outlet; and as much again spread evenly over the lake, for the streams and
//         slopes around it that are not in the map data (so every arm drains, and the flow builds up
//         downstream as in a valley network)
//   out   where a mapped river leaves the outline (the dam) and each tunnel intake, all at one level,
//         so the outlets share the water by how easily it reaches them, not by their recorded flows
// A part of the outline joined to no outlet is still. Pure functions over scene metres (x east,
// z south), so the worker and the tests can use them.

export const CELL_M = 30; // grid cell
export const NEAR_M = 2000; // a tunnel end this close to an outline belongs to that lake
const MERGE_M = 300; // ends of one kind closer than this are one end
const END_CELLS = 1; // an end holds its cell and the wet cells this many cells around it

/** Is (x, z) inside a polygon (a list of rings [[x, z], ...]; even-odd, so inner rings are islands)? */
export function insidePoly(x, z, rings) {
  let c = false;
  for (const ring of rings) {
    for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
      const [x1, z1] = ring[i];
      const [x2, z2] = ring[j];
      if ((z1 > z) !== (z2 > z) && x < ((x2 - x1) * (z - z1)) / (z2 - z1) + x1) c = !c;
    }
  }
  return c;
}

/** The polygons on a grid. polyOf: per cell, the polygon its centre falls in (-1 none); particles live
 * there. wet: those cells plus every cell the outline passes through, so a channel narrower than a
 * cell stays joined; the flow is solved there. */
export function rasterize(polys, cell = CELL_M) {
  let x0 = Infinity; let x1 = -Infinity; let z0 = Infinity; let z1 = -Infinity;
  for (const rings of polys) for (const ring of rings) for (const [x, z] of ring) {
    x0 = Math.min(x0, x); x1 = Math.max(x1, x); z0 = Math.min(z0, z); z1 = Math.max(z1, z);
  }
  x0 -= cell; z0 -= cell;
  const W = Math.ceil((x1 - x0) / cell) + 2;
  const H = Math.ceil((z1 - z0) / cell) + 2;
  const polyOf = new Int16Array(W * H).fill(-1);
  const wet = new Uint8Array(W * H);
  const xs = [];
  polys.forEach((rings, p) => {
    for (let r = 0; r < H; r++) { // scanline: crossings of the row's centre line, filled pairwise
      const zc = z0 + (r + 0.5) * cell;
      xs.length = 0;
      for (const ring of rings) {
        for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
          const [ax, az] = ring[i];
          const [bx, bz] = ring[j];
          if ((az > zc) !== (bz > zc)) xs.push(ax + ((bx - ax) * (zc - az)) / (bz - az));
        }
      }
      xs.sort((a, b) => a - b);
      for (let k = 0; k + 1 < xs.length; k += 2) {
        const c0 = Math.max(0, Math.ceil((xs[k] - x0) / cell - 0.5));
        const c1 = Math.min(W - 1, Math.floor((xs[k + 1] - x0) / cell - 0.5));
        for (let c = c0; c <= c1; c++) { if (polyOf[r * W + c] < 0) polyOf[r * W + c] = p; wet[r * W + c] = 1; }
      }
    }
    for (const ring of rings) { // the cells each edge passes through (a 4-connected chain)
      for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) walk(ring[j], ring[i], x0, z0, cell, W, H, wet);
    }
  });
  return { x0, z0, cell, W, H, polyOf, wet };
}

function walk([ax, az], [bx, bz], x0, z0, cell, W, H, wet) {
  let c = Math.floor((ax - x0) / cell);
  let r = Math.floor((az - z0) / cell);
  const ce = Math.floor((bx - x0) / cell);
  const re = Math.floor((bz - z0) / cell);
  const dx = bx - ax;
  const dz = bz - az;
  const sc = Math.sign(dx);
  const sr = Math.sign(dz);
  const tdx = sc ? cell / Math.abs(dx) : Infinity;
  const tdz = sr ? cell / Math.abs(dz) : Infinity;
  let tx = sc > 0 ? (x0 + (c + 1) * cell - ax) / dx : sc < 0 ? (x0 + c * cell - ax) / dx : Infinity;
  let tz = sr > 0 ? (z0 + (r + 1) * cell - az) / dz : sr < 0 ? (z0 + r * cell - az) / dz : Infinity;
  for (let guard = 0; guard < 1e5; guard++) {
    if (c >= 0 && r >= 0 && c < W && r < H) wet[r * W + c] = 1;
    if (c === ce && r === re) break;
    if (tx < tz) { c += sc; tx += tdx; } else { r += sr; tz += tdz; }
  }
}

/** The grid cell holding (x, z), or -1 outside the grid. */
export function cellAt(g, x, z) {
  const c = Math.floor((x - g.x0) / g.cell);
  const r = Math.floor((z - g.z0) / g.cell);
  return c < 0 || r < 0 || c >= g.W || r >= g.H ? -1 : r * g.W + c;
}

/** The cell (of the outline's centre cells) nearest to (x, z), with its distance (m). */
export function nearestCell(g, x, z) {
  let best = -1;
  let bd = Infinity;
  for (let i = 0; i < g.W * g.H; i++) {
    if (g.polyOf[i] < 0) continue;
    const d = Math.hypot(g.x0 + ((i % g.W) + 0.5) * g.cell - x, g.z0 + (Math.floor(i / g.W) + 0.5) * g.cell - z);
    if (d < bd) { bd = d; best = i; }
  }
  return { cell: best, dist: bd };
}

/** Where water enters ('in') and leaves ('out') the lake, from the map. rivers: [{ name, pts: [[x, z],
 * ...] }] listed downstream (OpenStreetMap draws waterways in the direction of flow); a line's first
 * entry into the outline is an inlet, and its exit an outlet if it does not come back in (crossings
 * in between are meanders along the shore). tunnels: [{ name, a: {x, z} intake, b: {x, z} outlet,
 * since }]; an end within NEAR_M of the outline belongs to the lake, at the outline cell nearest to it.
 * Returns [{ kind, name, x, z, cell, since }]. */
export function findEnds(g, rivers, tunnels = []) {
  const inside = (x, z) => { const k = cellAt(g, x, z); return k >= 0 && g.polyOf[k] >= 0; };
  const ends = [];
  const add = (kind, name, x, z, since = null) => {
    const cell = inside(x, z) ? cellAt(g, x, z) : nearestCell(g, x, z).cell;
    if (cell < 0) return;
    if (!ends.some((e) => e.kind === kind && e.since === since && Math.hypot(e.x - x, e.z - z) < MERGE_M)) ends.push({ kind, name, x, z, cell, since });
  };
  const gx1 = g.x0 + g.W * g.cell;
  const gz1 = g.z0 + g.H * g.cell;
  for (const { pts, name = '' } of rivers) {
    if (!pts.some(([x, z]) => x >= g.x0 && x <= gx1 && z >= g.z0 && z <= gz1)) continue;
    let entry = null;
    let exit = null;
    let was = inside(pts[0][0], pts[0][1]);
    for (let i = 1; i < pts.length; i++) {
      const now = inside(pts[i][0], pts[i][1]);
      if (now && !was) { entry ??= pts[i]; exit = null; } // a line that comes back in did not leave
      if (!now && was) exit = pts[i - 1];
      was = now;
    }
    if (entry) add('in', name, entry[0], entry[1]);
    if (exit) add('out', name, exit[0], exit[1]);
  }
  for (const t of tunnels) {
    for (const [end, kind] of [['a', 'out'], ['b', 'in']]) {
      const p = t[end];
      if (p && (inside(p.x, p.z) || nearestCell(g, p.x, p.z).dist <= NEAR_M)) add(kind, t.name, p.x, p.z, t.since ?? null);
    }
  }
  return ends;
}

const neighbours = (i, W, N) => {
  const c = i % W;
  return [i - W, i + W < N ? i + W : -1, c > 0 ? i - 1 : -1, c < W - 1 ? i + 1 : -1];
};

/** The cells an end holds: its own and the wet cells within END_CELLS of it. */
function endCells(g, e) {
  const out = [];
  const c0 = e.cell % g.W;
  const r0 = Math.floor(e.cell / g.W);
  for (let r = r0 - END_CELLS; r <= r0 + END_CELLS; r++) {
    for (let c = c0 - END_CELLS; c <= c0 + END_CELLS; c++) {
      if (r >= 0 && c >= 0 && r < g.H && c < g.W && g.wet[r * g.W + c]) out.push(r * g.W + c);
    }
  }
  return out;
}

/** The steady flow for a set of ends (see the rule at the top): { vx, vz } per cell (relative units;
 * 0 on still water and off the outline), vref (the 70th percentile of the speed on the lake's cells
 * away from the ends), and the solver's iterations and residual. The potential solves Poisson's
 * equation on the wet cells' 4-neighbour graph (sources at the inlets and over the lake, 0 at the
 * outlets, no flow through the shore) by conjugate gradients; the flow runs down its slope. */
export function solveField(g, ends, { tol = 1e-6, maxIter = 8000 } = {}) {
  const { W, H, wet } = g;
  const N = W * H;
  const outlet = new Uint8Array(N);
  for (const e of ends) if (e.kind === 'out') for (const i of endCells(g, e)) outlet[i] = 1;
  // connected parts; only those with an outlet carry flow
  const part = new Int32Array(N).fill(-1);
  const live = [];
  const stack = [];
  for (let s = 0; s < N; s++) {
    if (!wet[s] || part[s] >= 0) continue;
    const id = live.length;
    let hasOut = false;
    part[s] = id;
    stack.push(s);
    while (stack.length) {
      const i = stack.pop();
      if (outlet[i]) hasOut = true;
      for (const j of neighbours(i, W, N)) if (j >= 0 && wet[j] && part[j] < 0) { part[j] = id; stack.push(j); }
    }
    live.push(hasOut);
  }
  const idx = new Int32Array(N).fill(-1);
  const cells = [];
  for (let i = 0; i < N; i++) if (wet[i] && !outlet[i] && live[part[i]]) { idx[i] = cells.length; cells.push(i); }
  const n = cells.length;
  // sources: 1 on every live cell, and at each inlet as much as the whole lake, spread over its cells
  const b = new Float64Array(n).fill(1);
  for (const e of ends) {
    if (e.kind !== 'in') continue;
    const own = endCells(g, e).filter((i) => idx[i] >= 0);
    for (const i of own) b[idx[i]] += n / own.length;
  }
  const nb = new Int32Array(n * 4).fill(-1);
  const diag = new Float64Array(n);
  for (let k = 0; k < n; k++) {
    let m = 0;
    for (const j of neighbours(cells[k], W, N)) {
      if (j < 0 || !wet[j]) continue;
      diag[k]++;
      if (!outlet[j]) nb[k * 4 + m++] = idx[j]; // an outlet neighbour holds 0
    }
  }
  // preconditioned (Jacobi) conjugate gradients from 0
  const x = new Float64Array(n);
  const r = Float64Array.from(b);
  const z = new Float64Array(n);
  const p = new Float64Array(n);
  const q = new Float64Array(n);
  const mul = (v, out) => {
    for (let k = 0; k < n; k++) {
      let s = diag[k] * v[k];
      for (let m = 0; m < 4; m++) { const j = nb[k * 4 + m]; if (j < 0) break; s -= v[j]; }
      out[k] = s;
    }
  };
  let bn = 0;
  let rz = 0;
  for (let k = 0; k < n; k++) { z[k] = r[k] / diag[k]; p[k] = z[k]; bn += b[k] * b[k]; rz += r[k] * z[k]; }
  bn = Math.sqrt(bn) || 1;
  let it = 0;
  let res = n ? 1 : 0;
  for (; it < maxIter && n; it++) {
    mul(p, q);
    let pq = 0;
    for (let k = 0; k < n; k++) pq += p[k] * q[k];
    const a = rz / pq;
    let rr = 0;
    for (let k = 0; k < n; k++) { x[k] += a * p[k]; r[k] -= a * q[k]; rr += r[k] * r[k]; }
    res = Math.sqrt(rr) / bn;
    if (res < tol) break;
    let rz2 = 0;
    for (let k = 0; k < n; k++) { z[k] = r[k] / diag[k]; rz2 += r[k] * z[k]; }
    const beta = rz2 / rz;
    rz = rz2;
    for (let k = 0; k < n; k++) p[k] = z[k] + beta * p[k];
  }
  // the flow down the potential's slope: central differences inside, one-sided at the shore
  const phi = new Float32Array(N).fill(NaN);
  for (let i = 0; i < N; i++) if (wet[i] && live[part[i]]) phi[i] = outlet[i] ? 0 : x[idx[i]];
  const vx = new Float32Array(N);
  const vz = new Float32Array(N);
  const slope = (i, j, k) => {
    const a = j >= 0 && !Number.isNaN(phi[j]) ? phi[j] : null;
    const c = k >= 0 && !Number.isNaN(phi[k]) ? phi[k] : null;
    if (a !== null && c !== null) return (c - a) / (2 * g.cell);
    if (c !== null) return (c - phi[i]) / g.cell;
    if (a !== null) return (phi[i] - a) / g.cell;
    return 0;
  };
  for (let i = 0; i < N; i++) {
    if (Number.isNaN(phi[i])) continue;
    const [up, down, left, right] = neighbours(i, W, N);
    vx[i] = -slope(i, left, right);
    vz[i] = -slope(i, up, down);
  }
  const atEnd = new Uint8Array(N);
  for (const e of ends) for (const i of endCells(g, e)) atEnd[i] = 1;
  const speeds = [];
  for (let i = 0; i < N; i++) if (g.polyOf[i] >= 0 && !atEnd[i] && !Number.isNaN(phi[i])) speeds.push(Math.hypot(vx[i], vz[i]));
  speeds.sort((a, c) => a - c);
  const vref = speeds.length ? speeds[Math.floor(speeds.length * 0.7)] : 0;
  return { vx, vz, vref, iterations: it, residual: res, unknowns: n, stillParts: live.filter((l) => !l).length };
}

/** Everything for one lake: the grid, the ends from the map, and one field per set of ends in use
 * (an end with a `since` date joins from that date on). Returns { grid, ends, variants: [{ since,
 * ends, field }] }, variants in date order; the first has since null. */
export function lakeField(polys, rivers, tunnels, { cell = CELL_M } = {}) {
  const grid = rasterize(polys, cell);
  const ends = findEnds(grid, rivers, tunnels);
  const dates = [...new Set(ends.map((e) => e.since).filter(Boolean))].sort();
  const variants = [null, ...dates].map((since) => {
    const used = ends.filter((e) => e.since === null || (since !== null && e.since <= since));
    return { since, ends: used, field: solveField(grid, used) };
  });
  return { grid, ends, variants };
}

/** The variant in use on a date (ISO 'YYYY-MM-DD'): the last whose since is on or before it. */
export function variantOn(variants, dateIso) {
  let v = variants[0];
  for (const w of variants) if (w.since !== null && w.since <= dateIso) v = w;
  return v;
}

/** Bilinear flow at (x, z) from the cell-centred field, into out = [vx, vz]. */
export function flowAt(g, f, x, z, out) {
  const fx = (x - g.x0) / g.cell - 0.5;
  const fz = (z - g.z0) / g.cell - 0.5;
  const c0 = Math.floor(fx);
  const r0 = Math.floor(fz);
  const tx = fx - c0;
  const tz = fz - r0;
  let sx = 0; let sz = 0;
  for (let dr = 0; dr < 2; dr++) {
    for (let dc = 0; dc < 2; dc++) {
      const c = c0 + dc;
      const r = r0 + dr;
      if (c < 0 || r < 0 || c >= g.W || r >= g.H) continue;
      const w = (dc ? tx : 1 - tx) * (dr ? tz : 1 - tz);
      sx += w * f.vx[r * g.W + c];
      sz += w * f.vz[r * g.W + c];
    }
  }
  out[0] = sx;
  out[1] = sz;
  return out;
}
