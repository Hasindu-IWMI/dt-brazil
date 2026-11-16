// Viewer unit tests (Node's built-in runner, no dependencies): npm --prefix web run test:web
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { solarPosition, sunVector } from '../src/scene/sun.js';
import { utmForward } from '../tools/lib/raster.mjs';

// terrain.js imports three; the decoder is pure, so load it through a tiny shim-free import
const { decodeDem } = await import('../src/scene/terrain.js');

test('sun: São Paulo, December solstice, local noon is almost overhead', () => {
  // 2025-12-21 15:00 UTC = 12:00 UTC-3; the window centre is at 23.075 S, 46.3 W (tropic at 23.44 S)
  const p = solarPosition(new Date(Date.UTC(2025, 11, 21, 15, 0)), -23.075, -46.3);
  assert.ok(p.elevation > 85 && p.elevation < 90, `elevation ${p.elevation}`);
  const winter = solarPosition(new Date(Date.UTC(2025, 5, 21, 15, 0)), -23.075, -46.3);
  assert.ok(Math.abs(winter.elevation - (90 - 23.075 - 23.44)) < 1.5, `June noon elevation ${winter.elevation}`);
  assert.ok(Math.abs(winter.azimuth - 0) < 10 || Math.abs(winter.azimuth - 360) < 10, `June noon sun is to the north: ${winter.azimuth}`);
});

test('sun: morning sun is in the east, evening sun in the west, night below the horizon', () => {
  const am = solarPosition(new Date(Date.UTC(2024, 7, 10, 10, 0)), -23.075, -46.3); // 07:00 local
  const pm = solarPosition(new Date(Date.UTC(2024, 7, 10, 20, 0)), -23.075, -46.3); // 17:00 local
  const night = solarPosition(new Date(Date.UTC(2024, 7, 11, 3, 0)), -23.075, -46.3); // 00:00 local
  assert.ok(am.azimuth > 45 && am.azimuth < 135 && am.elevation > 0);
  assert.ok(pm.azimuth > 225 && pm.azimuth < 315 && pm.elevation > 0);
  assert.ok(night.elevation < -30);
  const v = { set(x, y, z) { Object.assign(this, { x, y, z }); return this; } };
  sunVector({ azimuth: 90, elevation: 0 }, v); // due east on the horizon -> +x
  assert.ok(Math.abs(v.x - 1) < 1e-9 && Math.abs(v.y) < 1e-9 && Math.abs(v.z) < 1e-9);
});

test('terrain encoding round-trips (build_display_terrain.mjs -> decodeDem)', () => {
  const W = 5, H = 3;
  const metres = [532.5, 533.1, 540, 512.3, 2035, 800, 801.2, 799.9, 799.9, 0, 1000.04, 999.96, 1000, 1000, 1000];
  const enc = new Int16Array(W * H); // same algorithm as the build tool
  for (let r = 0; r < H; r++) {
    let prev = 0;
    for (let c = 0; c < W; c++) {
      const q = Math.round(metres[r * W + c] * 10);
      enc[r * W + c] = c === 0 ? q : q - prev;
      prev = q;
    }
  }
  const out = decodeDem(enc, W, H);
  metres.forEach((m, i) => assert.ok(Math.abs(out[i] - m) <= 0.05 + 1e-9, `${i}: ${out[i]} vs ${m}`));
});

test('UTM forward matches known points (zone 23 S)', () => {
  // central meridian of zone 23 (45 W) on the equator -> E 500 000, N 10 000 000 (south hemisphere false northing)
  const [e0, n0] = utmForward(-45, 0, 23, true);
  assert.ok(Math.abs(e0 - 500000) < 0.01 && Math.abs(n0 - 10000000) < 0.01);
  // on the central meridian, northing = 10 000 km - k0 * meridian arc; check the series against a
  // numerical integral of the WGS84 meridian arc
  const a = 6378137, f = 1 / 298.257223563, e2 = f * (2 - f);
  const lat = 23.075 * Math.PI / 180;
  let arc = 0;
  const n = 2000;
  for (let i = 0; i < n; i++) { // midpoint rule
    const p = ((i + 0.5) / n) * lat;
    arc += (a * (1 - e2)) / Math.pow(1 - e2 * Math.sin(p) ** 2, 1.5) * (lat / n);
  }
  const [eCm, nCm] = utmForward(-45, -23.075, 23, true);
  assert.ok(Math.abs(eCm - 500000) < 0.01);
  assert.ok(Math.abs(nCm - (10000000 - 0.9996 * arc)) < 0.05, `${nCm} vs ${10000000 - 0.9996 * arc}`);
  // east-west symmetry about the central meridian
  const [eW, nW] = utmForward(-46.3, -23.075, 23, true);
  const [eE, nE] = utmForward(-43.7, -23.075, 23, true);
  assert.ok(Math.abs((eW - 500000) + (eE - 500000)) < 0.01 && Math.abs(nW - nE) < 0.01);
});

test('record layers: a contiguous series maps onto the viewer dates, null outside it', async () => {
  const { valueOn } = await import('../src/scene/layers.js');
  const dates = ['2020-01-01', '2020-01-02', '2020-01-03', '2020-01-04', '2020-01-05'];
  const s = { first: '2020-01-02', q: [1.5, null, 3] };
  const cache = new Map();
  assert.equal(valueOn(s, s.q, dates, 0, cache), null); // before the record
  assert.equal(valueOn(s, s.q, dates, 1, cache), 1.5);
  assert.equal(valueOn(s, s.q, dates, 2, cache), null); // a gap stays a gap
  assert.equal(valueOn(s, s.q, dates, 3, cache), 3);
  assert.equal(valueOn(s, s.q, dates, 4, cache), null); // after the record
  assert.equal(valueOn({ first: null }, [], dates, 2, cache), null);
});

// ---- buildings (tools/build_buildings.mjs -> src/scene/buildingTile.js -> src/scene/buildingGeom.js)
test('building tags: heights, storeys and display classes', async () => {
  const { parseHeight, parseLevels, classOf, roofOf } = await import('../tools/lib/buildings.mjs');
  assert.equal(parseHeight('12'), 12);
  assert.equal(parseHeight('7,5 m'), 7.5);
  assert.ok(Math.abs(parseHeight('30 ft') - 9.144) < 1e-9);
  assert.equal(parseHeight('tall'), null);
  assert.equal(parseHeight('0.2'), null); // implausible
  assert.equal(parseLevels('3'), 3);
  assert.equal(parseLevels('2;3'), null);
  assert.equal(classOf({ building: 'house' }), 1);
  assert.equal(classOf({ building: 'yes', amenity: 'place_of_worship' }), 5);
  assert.equal(classOf({ building: 'yes', shop: 'bakery' }), 3);
  assert.equal(classOf({ building: 'yes' }), 0);
  assert.equal(roofOf({ 'roof:shape': 'hipped' }), 3);
  assert.equal(roofOf({}), 0);
});

const asArrayBuffer = (b) => b.buffer.slice(b.byteOffset, b.byteOffset + b.byteLength);

test('building tiles round-trip (encodeBuildingTile -> decodeBuildingTile)', async () => {
  const { encodeBuildingTile } = await import('../tools/lib/buildings.mjs');
  const { decodeBuildingTile } = await import('../src/scene/buildingTile.js');
  const cx = 1500, cy = -500;
  const sq = (x, y, s) => [[x, y], [x + s, y], [x + s, y + s], [x, y + s]];
  const recs = [
    { height: 6.25, hsrc: 1, cls: 1, levels: 2, roof: 3, src: 1, id: 123456789, name: 'Igreja Matriz', rings: [{ pts: sq(1490, -510, 10), hole: false }] },
    { height: 4, hsrc: 0, cls: 0, levels: 0, roof: 0, src: 0, id: 0, rings: [{ pts: sq(1100, -900, 30), hole: false }, { pts: sq(1110, -890, 5).reverse(), hole: true }] },
  ];
  const t = decodeBuildingTile(asArrayBuffer(encodeBuildingTile(recs, cx, cy, 0.05)));
  assert.equal(t.n, 2); assert.equal(t.nR, 3); assert.equal(t.nV, 12);
  assert.equal(t.cx, cx); assert.equal(t.cy, cy);
  assert.deepEqual([...t.height], [6.25, 4]);
  assert.deepEqual([...t.hsrc], [1, 0]); assert.deepEqual([...t.cls], [1, 0]); assert.deepEqual([...t.roof], [3, 0]);
  assert.deepEqual([...t.id], [123456789, 0]);
  assert.deepEqual([...t.ringBuilding], [0, 1, 1]); assert.deepEqual([...t.ringHole], [0, 0, 1]);
  assert.deepEqual(t.names, { 0: 'Igreja Matriz' });
  // vertices are stored relative to the tile centre, to 5 cm
  assert.ok(Math.abs(t.xy[0] - (1490 - cx)) < 0.026 && Math.abs(t.xy[1] - (-510 - cy)) < 0.026);
});

test('building height: median inside the footprint eroded by 1 m', async () => {
  const { footprintPixel, footprintMedian, cleanRing, orient, ringArea } = await import('../tools/lib/buildings.mjs');
  // 10 x 10 m footprint on 2 m pixels: edge pixels 3 m, the inner 3 x 3 pixels 9 m, one more pixel outside
  const ring = [[0, 0], [10, 0], [10, 10], [0, 10]];
  const run = (erode) => {
    const acc = { inner: [], all: [] };
    for (let r = 0; r < 6; r++) for (let c = 0; c < 6; c++) {
      footprintPixel(acc, ring, (c + 0.5) * 2, 10 - (r + 0.5) * 2, c >= 1 && c <= 3 && r >= 1 && r <= 3 ? 9 : 3, erode);
    }
    return footprintMedian(acc);
  };
  assert.equal(run(2), 9); // only the inner 3 x 3 survive a 2 m erosion
  assert.equal(run(1), 3); // pixel centres 1 m from the edge are still inside a 1 m erosion
  const acc = { inner: [], all: [] };
  footprintPixel(acc, ring, 9.5, 5, 7, 1); // too close to the edge for the eroded set, kept in "all"
  footprintPixel(acc, ring, 5, 5, -99, 1); // nodata
  assert.equal(footprintMedian(acc), 7);
  assert.equal(footprintMedian({ inner: [], all: [] }), null);
  // clean: closing vertex, a repeated vertex and a collinear vertex go; orientation as requested
  const c = cleanRing([[0, 0], [5, 0], [10, 0], [10, 0], [10, 10], [0, 10], [0, 0]]);
  assert.equal(c.length, 4);
  assert.ok(ringArea(orient(c, false)) > 0 && ringArea(orient(c, true)) < 0);
});

test('building extrusion: walls to the ground, ridge at the data height, party walls dropped', async () => {
  const { encodeBuildingTile } = await import('../tools/lib/buildings.mjs');
  const { decodeBuildingTile } = await import('../src/scene/buildingTile.js');
  const { extrudeTile, roofPlan } = await import('../src/scene/buildingGeom.js');
  const rect = (x, y, w, h) => [[x, y], [x + w, y], [x + w, y + h], [x, y + h]];
  // two terraced houses sharing the edge x = 10, and a free-standing house with a hipped-roof tag
  const recs = [
    { height: 6, hsrc: 1, cls: 1, levels: 2, roof: 0, src: 1, id: 11, rings: [{ pts: rect(0, 0, 10, 8), hole: false }] },
    { height: 6, hsrc: 1, cls: 1, levels: 2, roof: 0, src: 1, id: 12, rings: [{ pts: rect(10, 0, 10, 8), hole: false }] },
    { height: 7, hsrc: 2, cls: 1, levels: 0, roof: 3, src: 1, id: 13, rings: [{ pts: rect(40, 40, 12, 9), hole: false }] },
  ];
  const t = decodeBuildingTile(asArrayBuffer(encodeBuildingTile(recs, 0, 0)));
  const bases = Float32Array.from([800, 800, 810]), lows = Float32Array.from([799, 799.5, 808]);
  for (const lod of [0, 1]) {
    const g = extrudeTile(t, bases, lows, lod);
    assert.equal(g.index.length % 3, 0);
    assert.equal(g.triBuilding.length, g.index.length / 3);
    assert.equal(g.position.length / 3, g.uv.length / 2);
    assert.equal(g.bld.length / 4, g.position.length / 3);
    let maxA = -Infinity, minA = Infinity, maxC = -Infinity;
    for (let i = 0; i < g.position.length; i += 3) {
      const x = g.position[i], y = g.position[i + 1];
      if (x < 25) { maxA = Math.max(maxA, y); minA = Math.min(minA, y); } else maxC = Math.max(maxC, y);
    }
    assert.ok(maxA <= 806 + 1e-3 && maxA > 805, `terrace top ${maxA}`);
    assert.ok(maxC <= 817 + 1e-3 && maxC > 816, `house top ${maxC}`);
    assert.ok(minA <= 799 - 1.5 + 1e-3, `walls reach below the lowest ground: ${minA}`);
    // no wall quad on the shared edge x = 10 (wall normals there would point along x)
    for (let i = 0; i < g.position.length; i += 3) {
      const nx = g.normal[i] / 127, ny = g.normal[i + 1] / 127;
      if (Math.abs(g.position[i] - 10) < 0.1 && Math.abs(ny) < 0.1 && Math.abs(Math.abs(nx) - 1) < 0.01) assert.fail('party wall built');
    }
    assert.equal(g.shadow.length / 3, g.shadowH.length);
    assert.equal(g.ao.length / 3, g.aoV.length);
    if (lod === 0) assert.ok(g.roofs.hipped >= 1); else assert.equal(g.roofs.hipped + g.roofs.gabled, 0); // LOD1: flat roofs only
  }
  // a roof is never pitched above the data height, and keeps 2.4 m of wall under the eaves
  const plan = roofPlan({ pts: rect(0, 0, 12, 9), holes: false, H: 4, levels: 0, cls: 1, tag: 3, seed: 0.3 });
  assert.equal(plan.kind, 'hip');
  assert.ok(plan.rise > 0 && 4 - plan.rise >= 2.4 - 1e-9);
  assert.equal(roofPlan({ pts: rect(0, 0, 12, 9), holes: false, H: 6, levels: 0, cls: 1, tag: 1, seed: 0.3 }).kind, 'flat');
});

test('terrain: meshAt follows the drawn triangles (vertices exact, linear inside each triangle)', async () => {
  const { Terrain } = await import('../src/scene/terrain.js');
  const W = 5, H = 5, stride = 2;
  const elev = Float32Array.from({ length: W * H }, (_, i) => (i % 7) * 10 + Math.floor(i / W));
  const t = Object.create(Terrain.prototype);
  Object.assign(t, { elev, W, H, bbox: { west: 0, east: 5, south: 0, north: 5 }, stride, dLon: 1, dLat: 1 });
  const at = (c, r) => t.meshAt(c + 0.5, 5 - (r + 0.5)); // centre of DEM column c, row r
  for (const [c, r] of [[0, 0], [2, 0], [2, 2], [4, 4]]) assert.ok(Math.abs(at(c, r) - elev[r * W + c]) < 1e-9);
  // inside the NW triangle (a, d, b) of the first mesh cell, and inside its SE triangle (b, d, e)
  const a = elev[0], b = elev[2], d = elev[2 * W], e = elev[2 * W + 2];
  assert.ok(Math.abs(at(0.5, 0.5) - (a + (b - a) * 0.25 + (d - a) * 0.25)) < 1e-9);
  assert.ok(Math.abs(at(1.5, 1.5) - (e + (d - e) * 0.25 + (b - e) * 0.25)) < 1e-9);
  assert.equal(t.meshAt(-1, 2), null);
});
