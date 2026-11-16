// Helpers for tools/build_buildings.mjs (pure; covered by tests/scene.test.mjs).
import { MAGIC } from '../../src/scene/buildingTile.js';

const FT = 0.3048;

/** OSM `height` -> metres (explicit feet converted), or null when missing, unparseable or implausible. */
export function parseHeight(v) {
  if (!v) return null;
  const s = String(v).trim().toLowerCase().replace(',', '.');
  const m = s.match(/^([0-9]*\.?[0-9]+)\s*(m|meters|metres|metros|ft|feet|')?$/);
  if (!m) return null;
  let x = Number(m[1]);
  if (m[2] === 'ft' || m[2] === 'feet' || m[2] === "'") x *= FT;
  return x >= 0.5 && x <= 400 ? x : null;
}

/** OSM `building:levels` -> number of storeys above ground, or null. */
export function parseLevels(v) {
  if (!v) return null;
  const m = String(v).trim().replace(',', '.').match(/^([0-9]+(\.[0-9]+)?)$/);
  if (!m) return null;
  const x = Number(m[1]);
  return x > 0 && x <= 120 ? x : null;
}

// OSM building=* grouped for the facade and roof generator (display only); after the Kelani WebTwin
// (pipeline/31_build_buildings.py), with the values common in São Paulo state added.
const BUILDING_CLASS = {
  1: ['house', 'detached', 'semidetached_house', 'residential', 'terrace', 'bungalow', 'hut', 'cabin', 'farm', 'static_caravan', 'villa'],
  2: ['apartments', 'dormitory', 'hotel', 'condominium'],
  3: ['commercial', 'retail', 'office', 'supermarket', 'kiosk', 'bank', 'mall', 'shop', 'restaurant'],
  4: ['industrial', 'warehouse', 'factory', 'manufacture', 'service', 'garage', 'garages', 'shed', 'hangar', 'barn', 'greenhouse',
    'farm_auxiliary', 'cowshed', 'stable', 'sty', 'agricultural', 'storage', 'transformer_tower', 'slurry_tank'],
  5: ['church', 'chapel', 'cathedral', 'temple', 'mosque', 'shrine', 'monastery', 'religious', 'synagogue', 'convent'],
  6: ['school', 'hospital', 'university', 'government', 'public', 'college', 'train_station', 'civic', 'stadium', 'sports_centre',
    'sports_hall', 'grandstand', 'kindergarten', 'fire_station', 'transportation', 'police', 'library', 'townhall', 'clinic', 'museum'],
  7: ['roof', 'carport', 'shelter', 'canopy'],
  8: ['storage_tank', 'silo', 'tank', 'water_tower', 'reservoir_covered'],
  9: ['construction'],
};
const CLASS_OF = Object.fromEntries(Object.entries(BUILDING_CLASS).flatMap(([k, vs]) => vs.map((v) => [v, Number(k)])));
const AMENITY_CLASS = { place_of_worship: 5, school: 6, hospital: 6, university: 6, college: 6, townhall: 6, police: 6,
  fire_station: 6, library: 6, kindergarten: 6, clinic: 6, bank: 3, marketplace: 3, fuel: 3, restaurant: 3 };
export const ROOF_SHAPE = { flat: 1, gabled: 2, hipped: 3, 'half-hipped': 3, pyramidal: 4, skillion: 5, lean_to: 5,
  dome: 6, round: 6, onion: 6, cone: 4 };

/** Display class of an OSM building from its tags (0 = untyped, as `building=yes`). */
export function classOf(tags = {}) {
  const b = String(tags.building ?? 'yes').toLowerCase();
  if (CLASS_OF[b] !== undefined) return CLASS_OF[b];
  if (AMENITY_CLASS[tags.amenity] !== undefined) return AMENITY_CLASS[tags.amenity];
  if (tags.shop || tags.office) return 3;
  if (tags.tourism === 'hotel') return 2;
  if (tags.man_made === 'storage_tank' || tags.man_made === 'silo' || tags.man_made === 'water_tower') return 8;
  return 0;
}

/** roof:shape -> code (0 untagged, 7 tagged but other) */
export function roofOf(tags = {}) {
  const r = tags['roof:shape'];
  if (!r) return 0;
  return ROOF_SHAPE[String(r).toLowerCase()] ?? 7;
}

// ---- polygons (rings are arrays of [x, y] without the closing vertex)

export function ringArea(r) {
  let s = 0;
  for (let i = 0; i < r.length; i++) {
    const [x0, y0] = r[i], [x1, y1] = r[(i + 1) % r.length];
    s += x0 * y1 - x1 * y0;
  }
  return s / 2;
}

export function pointInRing(x, y, r) {
  let inside = false;
  for (let i = 0, j = r.length - 1; i < r.length; j = i++) {
    const [xi, yi] = r[i], [xj, yj] = r[j];
    if ((yi > y) !== (yj > y) && x < ((xj - xi) * (y - yi)) / (yj - yi) + xi) inside = !inside;
  }
  return inside;
}

/** distance from a point to the ring's boundary */
export function distToRing(x, y, r) {
  let d = Infinity;
  for (let i = 0; i < r.length; i++) {
    const [x0, y0] = r[i], [x1, y1] = r[(i + 1) % r.length];
    const dx = x1 - x0, dy = y1 - y0;
    const l2 = dx * dx + dy * dy;
    const t = l2 > 0 ? Math.max(0, Math.min(1, ((x - x0) * dx + (y - y0) * dy) / l2)) : 0;
    d = Math.min(d, Math.hypot(x - x0 - t * dx, y - y0 - t * dy));
  }
  return d;
}

/** Drop the closing vertex, repeated vertices (< 2 cm apart) and near-collinear vertices (< 2 cm off the line). */
export function cleanRing(r) {
  const d = (a, b) => Math.hypot(a[0] - b[0], a[1] - b[1]);
  const out = [];
  for (const p of r) if (!out.length || d(p, out.at(-1)) >= 0.02) out.push(p);
  while (out.length > 1 && d(out[0], out.at(-1)) < 0.02) out.pop(); // closing vertex
  for (let changed = true; changed && out.length > 3;) {
    changed = false;
    for (let i = 0; i < out.length && out.length > 3; i++) {
      const prev = out[(i - 1 + out.length) % out.length], p = out[i], next = out[(i + 1) % out.length];
      const l = d(prev, next);
      const off = l > 0 ? Math.abs((next[0] - prev[0]) * (p[1] - prev[1]) - (next[1] - prev[1]) * (p[0] - prev[0])) / l : 0;
      if (off < 0.02) { out.splice(i, 1); i--; changed = true; } // collinear, or a spike back along the same line
    }
  }
  return out.length >= 3 && Math.abs(ringArea(out)) > 1e-6 ? out : null;
}

/** Outer rings counter-clockwise, holes clockwise (as the viewer's worker expects). */
export function orient(ring, hole) {
  const ccw = ringArea(ring) > 0;
  return ccw === !hole ? ring : ring.slice().reverse();
}

export function median(v) {
  if (!v.length) return null;
  const s = Float64Array.from(v).sort();
  const m = s.length >> 1;
  return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2;
}

/**
 * Median raster value inside a footprint, as the Kelani WebTwin does it: the pixels whose centre lies inside
 * the footprint eroded by `erode` metres, or all pixels inside if there are none. Feed every pixel (centre
 * px, py and value v; v <= 0 or null is "no building") to footprintPixel, then take footprintMedian.
 */
export function footprintPixel(acc, ring, px, py, v, erode = 1) {
  if (!(v > 0) || !pointInRing(px, py, ring)) return;
  acc.all.push(v);
  if (distToRing(px, py, ring) >= erode) acc.inner.push(v);
}
export const footprintMedian = (acc) => median(acc.inner) ?? median(acc.all);

// ---- tile encoding (decoder: src/scene/buildingTile.js)

const pad4 = (parts) => { const len = parts.reduce((s, b) => s + b.length, 0); if (len % 4) parts.push(Buffer.alloc(4 - (len % 4))); };

/**
 * buildings: [{ height, hsrc, cls, levels, roof, src, id, name, rings: [{ pts: [[x, y], ...] (local metres), hole }] }]
 * Returns an uncompressed UBT1 tile.
 */
export function encodeBuildingTile(buildings, cx, cy, quantum = 0.05) {
  const n = buildings.length;
  const rings = [];
  buildings.forEach((b, i) => { for (const r of b.rings) rings.push({ ...r, b: i }); });
  const nR = rings.length;
  const nV = rings.reduce((s, r) => s + r.pts.length, 0);
  const parts = [];
  const head = Buffer.alloc(32);
  head.write(MAGIC, 0, 'ascii');
  head.writeUInt32LE(n, 4); head.writeUInt32LE(nR, 8); head.writeUInt32LE(nV, 12);
  head.writeFloatLE(cx, 16); head.writeFloatLE(cy, 20); head.writeFloatLE(quantum, 24);
  parts.push(head);
  parts.push(Buffer.from(Uint16Array.from(buildings, (b) => Math.min(65535, Math.round(b.height * 100))).buffer)); pad4(parts);
  for (const k of ['hsrc', 'cls', 'levels', 'roof', 'src']) parts.push(Buffer.from(Uint8Array.from(buildings, (b) => Math.min(255, Math.round(b[k] ?? 0)))));
  pad4(parts);
  parts.push(Buffer.from(Uint32Array.from(buildings, (b) => b.id ?? 0).buffer));
  const start = new Uint32Array(nR + 1);
  rings.forEach((r, k) => { start[k + 1] = start[k] + r.pts.length; });
  parts.push(Buffer.from(start.buffer), Buffer.from(Uint32Array.from(rings, (r) => r.b).buffer), Buffer.from(Uint8Array.from(rings, (r) => (r.hole ? 1 : 0))));
  pad4(parts);
  const xy = new Int16Array(nV * 2);
  let v = 0;
  for (const r of rings) {
    for (const [x, y] of r.pts) {
      const qx = Math.round((x - cx) / quantum), qy = Math.round((y - cy) / quantum);
      if (Math.abs(qx) > 32767 || Math.abs(qy) > 32767) throw new Error(`vertex ${x},${y} out of the tile's range`);
      xy[v++] = qx; xy[v++] = qy;
    }
  }
  parts.push(Buffer.from(xy.buffer));
  const names = {};
  buildings.forEach((b, i) => { if (b.name) names[i] = b.name; });
  const nb = Buffer.from(Object.keys(names).length ? JSON.stringify(names) : '', 'utf8');
  const len = Buffer.alloc(4);
  len.writeUInt32LE(nb.length, 0);
  parts.push(len, nb);
  return Buffer.concat(parts);
}
