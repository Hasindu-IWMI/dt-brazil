// Building extrusion for one tile (run in buildings.worker.js; pure, so the tests can call it).
// After the Kelani WebTwin (src/buildings/buildings.worker.ts). Footprints and heights are the data,
// unchanged; everything else here is display:
//   walls     one quad per footprint edge; uv = (distance along the perimeter, height above the base) in
//             metres, so the facade shader lays out storeys, window bays and doors at true scale
//   roofs     LOD0: hipped or gabled roofs on small low-rise footprints close to their minimum bounding
//             rectangle (ceramic tile or fibre-cement), shallow gables on large low sheds (metal or
//             fibre-cement), parapets ("platibanda") round most other low flat roofs. The RIDGE or
//             parapet top is at the data height: a roof never makes a building taller than its source
//             says. LOD1 (distant tiles): flat roofs, no doors, no parapets.
//   shadows   the footprint swept along the sun by its height, and a contact-occlusion halo; the
//             vertex shader (buildingMaterial.js) offsets them by the current sun and drapes them on
//             the terrain, so they follow the hour and date without a rebuild
// Coordinates: tile-local metres, x east and z south (scene axes); y is the scene height.
import { ShapeUtils, Vector2 } from 'three';

// Paint and roof palettes (sRGB 0..255), typical of towns in the interior of São Paulo state - display only
const WALL_PAINT = [
  [242, 240, 234], [236, 230, 216], [240, 228, 192], [242, 222, 158], [228, 196, 136], [236, 192, 160], [214, 150, 110],
  [196, 214, 226], [200, 224, 204], [214, 212, 206], [222, 206, 222], [246, 244, 238], [226, 220, 196], [184, 112, 76],
];
const WALL_BY_CLASS = {
  2: [[238, 236, 230], [226, 220, 208], [212, 212, 210], [232, 214, 186], [196, 150, 120], [200, 204, 206]],
  3: [[236, 234, 228], [224, 224, 220], [242, 226, 170], [210, 214, 218], [226, 196, 170], [248, 246, 242]],
  4: [[206, 208, 206], [226, 226, 222], [178, 186, 192], [214, 206, 190], [236, 236, 232]],
  5: [[246, 244, 238], [242, 236, 214], [236, 226, 196]],
  6: [[240, 232, 200], [236, 234, 226], [234, 214, 160], [220, 226, 220], [244, 240, 226]],
  8: [[226, 228, 230], [204, 208, 210], [236, 236, 236]],
};
const ROOF_TILE = [[176, 92, 58], [160, 82, 54], [184, 106, 70], [146, 76, 52], [168, 98, 72], [190, 116, 80]];
const ROOF_METAL = [[198, 200, 200], [184, 188, 190], [170, 176, 180], [210, 210, 206]];
const ROOF_FIBRE = [[168, 168, 162], [150, 152, 150], [182, 180, 172], [136, 138, 136]];
const ROOF_FLAT = [[176, 172, 164], [158, 156, 150], [192, 188, 178], [168, 160, 150]];
// roof material codes for the shader: 0 concrete slab, 1 ceramic tile, 2 metal sheet, 3 fibre-cement sheet
const BURY = 1.5; // walls run this far below the lowest ground under the footprint

const hash1 = (x) => { let h = Math.imul((x | 0) ^ 0x9e3779b9, 0x85ebca6b); h ^= h >>> 13; h = Math.imul(h, 0xc2b2ae35); h ^= h >>> 16; return (h >>> 0) / 4294967296; };
const pick = (arr, r) => arr[Math.min(arr.length - 1, Math.floor(r * arr.length))];

export function convexHull(pts) {
  const p = pts.slice().sort((a, b) => a[0] - b[0] || a[1] - b[1]);
  if (p.length < 3) return p;
  const cross = (o, a, b) => (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0]);
  const lo = [], hi = [];
  for (const q of p) { while (lo.length >= 2 && cross(lo[lo.length - 2], lo[lo.length - 1], q) <= 0) lo.pop(); lo.push(q); }
  for (let i = p.length - 1; i >= 0; i--) { const q = p[i]; while (hi.length >= 2 && cross(hi[hi.length - 2], hi[hi.length - 1], q) <= 0) hi.pop(); hi.push(q); }
  return lo.slice(0, -1).concat(hi.slice(0, -1));
}

/** minimum-area bounding rectangle (rotating edges of the hull): centre, long axis (ux, uy), half extents a >= b */
export function minRect(hull) {
  let best = { area: Infinity, cx: 0, cy: 0, ux: 1, uy: 0, a: 0, b: 0 };
  for (let i = 0; i < hull.length; i++) {
    const [x0, y0] = hull[i], [x1, y1] = hull[(i + 1) % hull.length];
    const l = Math.hypot(x1 - x0, y1 - y0);
    if (l < 1e-6) continue;
    const ux = (x1 - x0) / l, uy = (y1 - y0) / l;
    let u0 = Infinity, u1 = -Infinity, v0 = Infinity, v1 = -Infinity;
    for (const [x, y] of hull) {
      const u = x * ux + y * uy, v = -x * uy + y * ux;
      u0 = Math.min(u0, u); u1 = Math.max(u1, u); v0 = Math.min(v0, v); v1 = Math.max(v1, v);
    }
    const area = (u1 - u0) * (v1 - v0);
    if (area < best.area) {
      const uc = (u0 + u1) / 2, vc = (v0 + v1) / 2;
      best = { area, cx: uc * ux - vc * uy, cy: uc * uy + vc * ux, ux, uy, a: (u1 - u0) / 2, b: (v1 - v0) / 2 };
    }
  }
  if (best.b > best.a) best = { ...best, ux: -best.uy, uy: best.ux, a: best.b, b: best.a };
  return best;
}

export function polyArea(r) { let s = 0; for (let i = 0; i < r.length; i++) { const [x0, y0] = r[i], [x1, y1] = r[(i + 1) % r.length]; s += x0 * y1 - x1 * y0; } return s / 2; }

/** ring offset into the solid (left of the direction of travel) by t metres, mitred (miter limited to 3 t) */
function insetRing(pts, t) {
  const n = pts.length;
  const out = [];
  for (let i = 0; i < n; i++) {
    const p = pts[(i - 1 + n) % n], c = pts[i], q = pts[(i + 1) % n];
    let ax = c[0] - p[0], ay = c[1] - p[1], bx = q[0] - c[0], by = q[1] - c[1];
    const la = Math.hypot(ax, ay) || 1, lb = Math.hypot(bx, by) || 1;
    const n1x = -ay / la, n1y = ax / la, n2x = -by / lb, n2y = bx / lb;
    let mx = n1x + n2x, my = n1y + n2y;
    const ml = Math.hypot(mx, my);
    if (ml < 1e-6) { mx = n1x; my = n1y; } else { mx /= ml; my /= ml; }
    const k = Math.min(3 * t, t / Math.max(mx * n1x + my * n1y, 0.2));
    out.push([c[0] + mx * k, c[1] + my * k]);
  }
  return out;
}

/** Roof form and material for one building (LOD0). Exported for the tests. */
export function roofPlan({ pts, holes, H, levels, cls, tag, seed }) {
  const r = (k) => hash1(seed * 1e6 + k);
  if (holes || cls === 7 || cls === 8) return { kind: 'flat', mat: cls === 7 ? 2 : 0, parapet: 0 };
  const area = Math.abs(polyArea(pts));
  const rect = minRect(convexHull(pts));
  const fill = area / Math.max(4 * rect.a * rect.b, 1e-6);
  const storeys = levels || Math.max(1, Math.round(H / 3));
  // without a storey count, up to 11 m still counts as low-rise: the Google 2.5D estimates run high
  // (the Kelani WebTwin measured +2.3 m), so most two-storey houses come out at 8-11 m
  const lowRise = (levels === 0 ? H <= 11 : levels <= 2) && [0, 1, 5, 6].includes(cls);
  const roofTag = tag === 2 || tag === 3 || tag === 4;
  const house = roofTag || (tag === 0 && lowRise && area >= 20 && area <= 800 && fill >= 0.75 && pts.length <= 16 && r(9) < 0.85);
  const shed = !roofTag && tag === 0 && (cls === 4 || cls === 0) && area >= 500 && H <= 14 && fill >= 0.85 && rect.b >= 4;
  if ((house || shed) && rect.b >= 2.2 && tag !== 1) {
    let mat, pitchDeg;
    if (shed) { mat = r(6) < 0.6 ? 2 : 3; pitchDeg = 5 + 4 * r(4); } else {
      // houses in the towns of the region: mostly ceramic tile, some fibre-cement, a few metal
      const rm = r(6);
      mat = rm < 0.8 ? 1 : rm < 0.96 ? 3 : 2;
      pitchDeg = mat === 1 ? 17 + 7 * r(4) : 8 + 4 * r(4);
    }
    const B = rect.b + 0.45;
    let rise = Math.min(B * Math.tan((pitchDeg * Math.PI) / 180), 0.45 * H, shed ? 3.5 : 4.0);
    if (H - rise < 2.4) rise = H - 2.4;
    if (rise >= (shed ? 0.3 : 0.6)) {
      const kind = tag === 2 || cls === 5 || shed ? 'gable' : tag === 3 || tag === 4 || cls === 6 ? 'hip' : r(5) < 0.55 ? 'hip' : 'gable';
      return { kind, mat, rect, rise, overhang: shed ? 0.3 : 0.45 };
    }
  }
  // flat. Large regular low footprints read as sheds and industrial halls: sheet roofs.
  const sheet = cls === 4 || (cls === 0 && area >= 400 && H <= 14 && fill >= 0.85);
  // Untyped low footprints that are irregular or large are mostly rows of houses that the footprint
  // model merged into one: give them the houses' roof mix, drawn flat (no one ridge would fit them)
  if (!sheet && cls === 0 && H <= 11) {
    const rm = r(6);
    const par = area >= 25 && H >= 3.4 && r(10) < 0.25 ? Math.min(0.5 + 0.4 * r(11), H - 2.4) : 0;
    return { kind: 'flat', mat: par ? (r(12) < 0.5 ? 3 : 0) : rm < 0.7 ? 1 : rm < 0.9 ? 3 : 0, parapet: par };
  }
  // a parapet (platibanda) round most other low flat roofs, often hiding a fibre-cement roof
  const parapet = !sheet && storeys <= 4 && area >= 25 && [0, 1, 2, 3, 6].includes(cls) && r(10) < 0.75 ? 0.5 + 0.4 * r(11) : 0;
  let mat = sheet ? (r(6) < 0.6 ? 2 : 3) : 0;
  if (!sheet && parapet && (cls === 0 || cls === 1) && r(12) < 0.5) mat = 3;
  return { kind: 'flat', mat, parapet: Math.min(parapet, H - 2.4 > 0 ? H - 2.4 : 0) };
}

/**
 * t: decoded tile (buildingTile.js). bases[b]: scene height of the building's base (terrain under it,
 * vertical exaggeration applied); lows[b]: lowest terrain under its footprint. lod 0 = full detail.
 */
export function extrudeTile(t, bases, lows, lod) {
  const pos = [], nor = [], col = [], uvs = [], bld = [], idx = [], triB = [];
  const sh = [], shH = [], ao = [], aoV = [];
  const roofs = { flat: 0, parapet: 0, hipped: 0, gabled: 0, shed: 0 };
  const rings = Array.from({ length: t.n }, () => []);
  for (let r = 0; r < t.ringBuilding.length; r++) rings[t.ringBuilding[r]].push({ start: t.ringStart[r], end: t.ringStart[r + 1], hole: t.ringHole[r] === 1 });
  const ringPts = (rg) => { const a = []; for (let i = rg.start; i < rg.end; i++) a.push([t.xy[i * 2], t.xy[i * 2 + 1]]); return a; };
  // party walls: an edge shared by two footprints (terraces share OSM nodes) is interior and not built
  const vk = (i) => `${Math.round(t.xy[i * 2] * 20)},${Math.round(t.xy[i * 2 + 1] * 20)}`;
  const edgeKey = (i, j) => { const a = vk(i), b = vk(j); return a < b ? `${a}|${b}` : `${b}|${a}`; };
  const edgeCount = new Map();
  for (let r = 0; r < t.ringBuilding.length; r++) {
    const s0 = t.ringStart[r], n = t.ringStart[r + 1] - s0;
    for (let i = 0; i < n; i++) { const k = edgeKey(s0 + i, s0 + ((i + 1) % n)); edgeCount.set(k, (edgeCount.get(k) ?? 0) + 1); }
  }

  let bCur = 0, colCur = null, blCur = null;
  /** convex polygon (3 or 4 points, scene coords) with one normal; flips the winding to face along n */
  const poly = (P, n, uv, c = colCur, bl = blCur) => {
    const v0 = pos.length / 3;
    const e1 = [P[1][0] - P[0][0], P[1][1] - P[0][1], P[1][2] - P[0][2]], e2 = [P[2][0] - P[0][0], P[2][1] - P[0][1], P[2][2] - P[0][2]];
    const cr = [e1[1] * e2[2] - e1[2] * e2[1], e1[2] * e2[0] - e1[0] * e2[2], e1[0] * e2[1] - e1[1] * e2[0]];
    const flip = cr[0] * n[0] + cr[1] * n[1] + cr[2] * n[2] < 0;
    for (let k = 0; k < P.length; k++) {
      pos.push(P[k][0], P[k][1], P[k][2]);
      nor.push(Math.round(n[0] * 127), Math.round(n[1] * 127), Math.round(n[2] * 127));
      col.push(c[0], c[1], c[2]);
      uvs.push(uv[k][0], uv[k][1]);
      bld.push(bl[0], bl[1], bl[2], bl[3]);
    }
    for (let k = 1; k + 1 < P.length; k++) {
      if (flip) idx.push(v0, v0 + k + 1, v0 + k); else idx.push(v0, v0 + k, v0 + k + 1);
      triB.push(bCur);
    }
  };

  for (let b = 0; b < t.n; b++) {
    bCur = b;
    const base = bases[b];
    const H = t.height[b];
    const top = base + H;
    const bottom = Math.min(lows[b], base) - BURY;
    // per-building seed for paint, roof and window choices: the OSM id, or the first vertex's absolute position
    const v0 = rings[b][0]?.start ?? 0;
    const seed = hash1(t.id[b] ? t.id[b] % 2147483647 : Math.round((t.xy[v0 * 2] + t.cx) * 10) * 7919 + Math.round((t.xy[v0 * 2 + 1] + t.cy) * 10));
    const r = (k) => hash1(seed * 1e6 + k);
    const cls = t.cls[b];
    const outer = rings[b].filter((rg) => !rg.hole);
    const holes = rings[b].filter((rg) => rg.hole);
    if (!outer.length) continue;
    const pts0 = ringPts(outer[0]);

    let wallC = pick(WALL_BY_CLASS[cls] ?? WALL_PAINT, r(1));
    const dim = 0.86 + 0.14 * r(2);
    wallC = wallC.map((v) => v * dim);

    const plan = lod === 0
      ? roofPlan({ pts: pts0, holes: outer.length > 1 || holes.length > 0, H, levels: t.levels[b], cls, tag: t.roof[b], seed })
      : { kind: 'flat', mat: cls === 4 || cls === 7 ? 2 : 0, parapet: 0 };
    const roofC = pick(plan.mat === 1 ? ROOF_TILE : plan.mat === 2 ? ROOF_METAL : plan.mat === 3 ? ROOF_FIBRE : ROOF_FLAT, r(7));
    const pitched = plan.kind !== 'flat';
    const eave = pitched ? top - plan.rise : top;
    const roofY = plan.kind === 'flat' ? top - (plan.parapet || 0) : eave;
    const wallTop = pitched ? eave : top;

    // door: on the longest outer edge (houses, apartments, shops, untyped)
    let doorU = -1;
    if (lod === 0 && [0, 1, 2, 3].includes(cls)) {
      let acc = 0, best = 0;
      for (let i = 0; i < pts0.length; i++) {
        const [x0, y0] = pts0[i], [x1, y1] = pts0[(i + 1) % pts0.length];
        const l = Math.hypot(x1 - x0, y1 - y0);
        if (l > best && l >= 3) { best = l; doorU = acc + l * (0.3 + 0.4 * r(8)); }
        acc += l;
      }
    }
    const packed = cls + 16 * plan.mat + 64 * t.hsrc[b];
    const bl = [packed, seed, wallTop - base, doorU];
    blCur = bl;
    colCur = wallC;

    // ---- walls: inset 2-5 cm per building, so near-coincident walls of neighbours do not z-fight
    const inset = 0.02 + 0.03 * seed;
    const wallBottom = cls === 7 ? top - 0.45 : bottom; // roof-only structures: a fascia, not walls
    for (const rg of rings[b]) {
      const n = rg.end - rg.start;
      let u = 0;
      for (let i = 0; i < n; i++) {
        const a = rg.start + i, c = rg.start + ((i + 1) % n);
        let x0 = t.xy[a * 2], y0 = t.xy[a * 2 + 1], x1 = t.xy[c * 2], y1 = t.xy[c * 2 + 1];
        const len = Math.hypot(x1 - x0, y1 - y0) || 1;
        const nx = (y1 - y0) / len, ny = -(x1 - x0) / len; // outward (right of travel), local x/y
        if ((edgeCount.get(edgeKey(a, c)) ?? 0) > 1) { u += len; continue; }
        x0 -= nx * inset; x1 -= nx * inset; y0 -= ny * inset; y1 -= ny * inset;
        const vb = wallBottom - base, vt = wallTop - base;
        poly([[x0, wallBottom, -y0], [x1, wallBottom, -y1], [x1, wallTop, -y1], [x0, wallTop, -y0]], [nx, 0, -ny],
          [[u, vb], [u + len, vb], [u + len, vt], [u, vt]]);
        u += len;
      }
    }
    if (cls === 7) { // underside of a canopy / carport roof
      for (const o of outer) {
        const P = ringPts(o);
        for (const f of ShapeUtils.triangulateShape(P.map(([x, y]) => new Vector2(x, y)), [])) {
          poly(f.map((i) => [P[i][0], top - 0.45, -P[i][1]]), [0, -1, 0], f.map((i) => [P[i][0], P[i][1]]), wallC.map((v) => v * 0.7));
        }
      }
    }

    // ---- roof
    colCur = roofC;
    if (pitched) {
      const { rect: rc, overhang: o } = plan;
      const A = rc.a + o, B = rc.b + o;
      const ux = rc.ux, uy = rc.uy, vx = -rc.uy, vy = rc.ux;
      const P = (su, sv, h) => [rc.cx + ux * su + vx * sv, h, -(rc.cy + uy * su + vy * sv)];
      const rl = plan.kind === 'hip' ? Math.max(A - B, 0) : A;
      const soffit = wallC.map((v) => v * 0.62);
      const face = (pts) => {
        const e1 = [pts[1][0] - pts[0][0], pts[1][1] - pts[0][1], pts[1][2] - pts[0][2]], e2 = [pts[2][0] - pts[0][0], pts[2][1] - pts[0][1], pts[2][2] - pts[0][2]];
        let n = [e1[1] * e2[2] - e1[2] * e2[1], e1[2] * e2[0] - e1[0] * e2[2], e1[0] * e2[1] - e1[1] * e2[0]];
        const nl = Math.hypot(n[0], n[1], n[2]) || 1;
        n = n.map((v) => v / nl);
        if (n[1] < 0) n = n.map((v) => -v);
        const hl = Math.hypot(n[0], n[2]) || 1;
        const ex = -n[2] / hl, ez = n[0] / hl; // along the eave
        const uvOf = (p) => [p[0] * ex + p[2] * ez, (p[1] - eave) / Math.max(hl, 0.08)];
        const uv = pts.map(uvOf);
        poly(pts, n, uv);
        poly(pts, n.map((v) => -v), uv, soffit); // underside: soffits under the eaves
      };
      face([P(-A, B, eave), P(A, B, eave), P(rl, 0, top), P(-rl, 0, top)]);
      face([P(A, -B, eave), P(-A, -B, eave), P(-rl, 0, top), P(rl, 0, top)]);
      if (plan.kind === 'hip') {
        face([P(A, B, eave), P(A, -B, eave), P(rl, 0, top)]);
        face([P(-A, -B, eave), P(-A, B, eave), P(-rl, 0, top)]);
        roofs.hipped++;
      } else {
        // gable end walls in the rectangle's end planes: plain painted triangles (wall top = eave, no windows)
        colCur = wallC;
        blCur = [bl[0], bl[1], eave - base, -1];
        for (const s of [1, -1]) {
          poly([P(s * rc.a, rc.b, eave), P(s * rc.a, -rc.b, eave), P(s * rc.a, 0, top)], [ux * s, 0, -uy * s],
            [[0, eave - base], [2 * rc.b, eave - base], [rc.b, top - base]]);
        }
        blCur = bl;
        if (cls === 4 || (cls === 0 && Math.abs(polyArea(pts0)) >= 400)) roofs.shed++; else roofs.gabled++;
      }
    } else {
      for (const o of outer) {
        const P = ringPts(o);
        const hs = holes.map((hr) => ringPts(hr));
        const all = P.concat(...hs);
        for (const f of ShapeUtils.triangulateShape(P.map(([x, y]) => new Vector2(x, y)), hs.map((h) => h.map(([x, y]) => new Vector2(x, y))))) {
          poly(f.map((i) => [all[i][0], roofY, -all[i][1]]), [0, 1, 0], f.map((i) => [all[i][0] + t.cx, all[i][1] + t.cy]));
        }
      }
      if (plan.parapet > 0) {
        // inner faces and cap of the parapet (the outer walls already reach the data height)
        colCur = wallC;
        const th = 0.15;
        for (const rg of rings[b]) {
          const P = ringPts(rg);
          const I = insetRing(P, th + inset);
          let u = 0;
          for (let i = 0; i < P.length; i++) {
            const j = (i + 1) % P.length;
            const len = Math.hypot(P[j][0] - P[i][0], P[j][1] - P[i][1]) || 1;
            const nx = (P[j][1] - P[i][1]) / len, ny = -(P[j][0] - P[i][0]) / len;
            const vb = roofY - base, vt = top - base;
            // inner face looks into the roof (opposite to the wall's outward normal); flagged as a coping band (door -2)
            blCur = [bl[0], bl[1], -1, -2];
            poly([[I[i][0], roofY, -I[i][1]], [I[j][0], roofY, -I[j][1]], [I[j][0], top, -I[j][1]], [I[i][0], top, -I[i][1]]], [-nx, 0, ny],
              [[u, vb], [u + len, vb], [u + len, vt], [u, vt]]);
            poly([[P[i][0] - nx * inset, top, -(P[i][1] - ny * inset)], [P[j][0] - nx * inset, top, -(P[j][1] - ny * inset)], [I[j][0], top, -I[j][1]], [I[i][0], top, -I[i][1]]],
              [0, 1, 0], [[u, vt], [u + len, vt], [u + len, vt], [u, vt]]);
            u += len;
          }
        }
        blCur = bl;
        roofs.parapet++;
      } else roofs.flat++;
    }

    // ---- shadow and contact-occlusion geometry (offset and draped in the vertex shader)
    if (cls === 8 && H < 2) continue;
    for (const o of outer) {
      const P = ringPts(o);
      const n = P.length;
      for (let i = 0; i < n; i++) {
        const [x0, y0] = P[i], [x1, y1] = P[(i + 1) % n];
        // swept edge: two vertices on the ground, two at the building's height
        sh.push(x0, base, -y0, x1, base, -y1, x1, base, -y1, x0, base, -y0, x1, base, -y1, x0, base, -y0);
        shH.push(0, 0, H, 0, H, H);
        // halo 2 m outwards (outer rings are counter-clockwise: outward = right of travel)
        const l = Math.hypot(x1 - x0, y1 - y0) || 1;
        const ox = ((y1 - y0) / l) * 2, oy = (-(x1 - x0) / l) * 2;
        ao.push(x0, base, -y0, x1, base, -y1, x1 + ox, base, -(y1 + oy), x0, base, -y0, x1 + ox, base, -(y1 + oy), x0 + ox, base, -(y0 + oy));
        aoV.push(1, 1, 0, 1, 0, 0);
      }
      // the footprint displaced along the sun (the roof's shadow)
      for (const f of ShapeUtils.triangulateShape(P.map(([x, y]) => new Vector2(x, y)), [])) {
        for (const i of f) { sh.push(P[i][0], base, -P[i][1]); shH.push(H); }
      }
    }
  }
  return {
    position: new Float32Array(pos), normal: Int8Array.from(nor), color: Uint8Array.from(col, (v) => Math.max(0, Math.min(255, Math.round(v)))),
    uv: new Float32Array(uvs), bld: new Float32Array(bld), index: new Uint32Array(idx), triBuilding: new Uint32Array(triB),
    shadow: new Float32Array(sh), shadowH: new Float32Array(shH), ao: new Float32Array(ao), aoV: new Float32Array(aoV), roofs,
  };
}
