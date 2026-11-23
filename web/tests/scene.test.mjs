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

test('terrain: classAt reads the nearest land-cover pixel, rows north to south, 0 outside', async () => {
  const { Terrain } = await import('../src/scene/terrain.js');
  const t = Object.create(Terrain.prototype);
  // 4 x 2 pixels over lon 0..4, lat 0..2; the top row (north) is 10 10 30 30, the bottom row 80 80 50 50
  Object.assign(t, { bbox: { west: 0, east: 4, south: 0, north: 2 }, lcClass: { cls: Uint8Array.from([10, 10, 30, 30, 80, 80, 50, 50]), w: 4, h: 2 } });
  assert.equal(t.classAt(0.5, 1.5), 10);
  assert.equal(t.classAt(2.5, 1.5), 30);
  assert.equal(t.classAt(1.5, 0.5), 80);
  assert.equal(t.classAt(3.9, 0.1), 50);
  assert.equal(t.classAt(-0.1, 1), 0);
  assert.equal(t.classAt(1, 2.1), 0);
  assert.equal(Object.assign(Object.create(Terrain.prototype), { bbox: t.bbox }).classAt(1, 1), 0); // not loaded yet
});

test('trees: planting follows the land-cover class, stays in its tile and repeats exactly', async () => {
  const { plantTile, PLANTING, KINDS, TILE, CELL } = await import('../src/scene/trees.js');
  const cells = (TILE / CELL) ** 2;
  const forest = plantTile(3, -2, () => 10);
  const again = plantTile(3, -2, () => 10);
  assert.equal(forest.n, again.n);
  assert.deepEqual(forest.x.slice(0, forest.n), again.x.slice(0, again.n)); // the same trees every time
  assert.notDeepEqual(plantTile(4, -2, () => 10).x.slice(0, 10), forest.x.slice(0, 10));
  assert.ok(Math.abs(forest.n / cells - PLANTING[10].p) < 0.06, `forest share ${forest.n / cells}`);
  const treeKinds = new Set(Object.keys(PLANTING[10].mix));
  for (let k = 0; k < forest.n; k++) {
    assert.ok(forest.x[k] >= 3 * TILE && forest.x[k] < 4 * TILE && forest.z[k] >= -2 * TILE && forest.z[k] < -TILE);
    const kd = KINDS[forest.kind[k]];
    assert.ok(treeKinds.has(kd.key), kd.key);
    assert.ok(forest.h[k] >= kd.height[0] && forest.h[k] <= kd.height[1]);
    assert.equal(forest.sink[k], PLANTING[10].sink); // sunk into the canopy of the surface model
  }
  // no plants on water or built-up land; few and unsunk on grassland
  assert.equal(plantTile(0, 0, () => 80).n, 0);
  assert.equal(plantTile(0, 0, () => 50).n, 0);
  assert.equal(plantTile(0, 0, () => 0).n, 0);
  const grass = plantTile(0, 0, () => 30);
  assert.ok(grass.n > 0 && grass.n < cells * 0.1, `grass ${grass.n}`);
  assert.ok([...grass.sink.slice(0, grass.n)].every((s) => s === 0));
  // density scales the chances
  assert.ok(plantTile(3, -2, () => 10, { density: 0.5 }).n < forest.n * 0.6);
});

test('river mask: distance to the mapped water edge matches brute force, negative inside, Infinity beyond reach', async () => {
  const { RiverMask } = await import('../src/scene/rivermask.js');
  // a meandering river 11 m wide and a straight one 30 m wide, long segments crossing many grid cells
  const meander = Array.from({ length: 40 }, (_, k) => [k * 37 - 400, Math.sin(k * 0.7) * 90 + 50]);
  const lines = [{ pts: meander, width: 11 }, { pts: [[-500, -700], [900, 400]], width: 30 }];
  const reach = 30;
  const mask = new RiverMask(lines, { reach, bucket: 120 });
  const brute = (x, z) => {
    let best = Infinity;
    for (const { pts, width } of lines) {
      for (let k = 1; k < pts.length; k++) {
        const [ax, az] = pts[k - 1], [bx, bz] = pts[k], dx = bx - ax, dz = bz - az;
        const t = Math.max(0, Math.min(1, ((x - ax) * dx + (z - az) * dz) / (dx * dx + dz * dz)));
        best = Math.min(best, Math.hypot(x - ax - t * dx, z - az - t * dz) - width / 2);
      }
    }
    return best;
  };
  let near = 0, inside = 0;
  for (let k = 0; k < 20000; k++) {
    const x = ((k * 7919) % 1600) - 600 + (k % 13) * 0.37, z = ((k * 104729) % 1400) - 800 + (k % 7) * 0.53;
    const want = brute(x, z), got = mask.edgeDistance(x, z);
    if (want <= reach) { near++; assert.ok(Math.abs(got - want) < 1e-9, `${x},${z}: ${got} vs ${want}`); } else assert.equal(got, Infinity);
    if (want < 0) { inside++; assert.ok(got < 0); }
  }
  assert.ok(near > 500 && inside > 100, `${near} near, ${inside} inside`);
  assert.ok(Math.abs(mask.edgeDistance(-400, 50) + 5.5) < 1e-9); // on the centreline: half the width inside
  assert.equal(new RiverMask([]).edgeDistance(0, 0), Infinity);
});

test('trees: no crown reaches over a mapped river, and the other plants stay as they were', async () => {
  const { plantTile, KINDS, TILE } = await import('../src/scene/trees.js');
  const { RiverMask } = await import('../src/scene/rivermask.js');
  // a 12 m river across tile (3, -2), corner to corner
  const mask = new RiverMask([{ pts: [[3 * TILE, -2 * TILE], [4 * TILE, -TILE]], width: 12 }]);
  const keepOut = (x, z) => mask.edgeDistance(x, z);
  const crown = KINDS.map((_, k) => 0.3 + k * 0.05);
  const all = plantTile(3, -2, () => 10);
  const kept = plantTile(3, -2, () => 10, { keepOut, crown });
  const clear = [];
  for (let k = 0; k < all.n; k++) if (!(keepOut(all.x[k], all.z[k]) < crown[all.kind[k]] * all.h[k])) clear.push(k);
  assert.ok(kept.n < all.n && kept.n === clear.length, `${kept.n} kept of ${all.n}, ${clear.length} clear`);
  clear.forEach((k, m) => {
    for (const f of ['x', 'z', 'h', 'rot', 'tone', 'kind']) assert.equal(kept[f][m], all[f][k], f);
    assert.ok(keepOut(kept.x[m], kept.z[m]) >= crown[kept.kind[m]] * kept.h[m]);
  });
});

test('lake flow: inlets and outlets from the mapped rivers and tunnel ends; meanders and far tunnels ignored', async () => {
  const { rasterize, findEnds } = await import('../src/scene/lakefield.js');
  const lake = [[[0, 0], [3000, 0], [3000, 600], [0, 600]]]; // 3 km by 600 m, x east, z south
  const g = rasterize([lake]);
  const river = { name: 'R', pts: [[-500, 300], [100, 300], [1500, 300], [2900, 300], [3500, 300]] }; // through, downstream to the east
  const meander = { name: 'M', pts: [[1000, -300], [1000, 50], [1000, -20], [1000, 100], [1000, 300]] }; // enters, leaves, comes back and ends inside
  const tunnels = [
    { name: 'T near', a: { x: 1500, z: 1400 }, b: { x: -9000, z: 0 } }, // intake 800 m south of the shore; outlet far away
    { name: 'T far', a: { x: 1500, z: 3200 }, b: null }, // 2.6 km off: not this lake's
  ];
  const ends = findEnds(g, [river, meander], tunnels);
  const got = ends.map((e) => `${e.kind} ${e.name}`).sort();
  assert.deepEqual(got, ['in M', 'in R', 'out R', 'out T near']);
  const outR = ends.find((e) => e.kind === 'out' && e.name === 'R');
  assert.ok(outR.x > 2800, `the river's outlet is at the east shore: ${outR.x}`);
  const t = ends.find((e) => e.name === 'T near');
  const tz = g.z0 + (Math.floor(t.cell / g.W) + 0.5) * g.cell;
  assert.ok(tz > 500 && tz < 600, `the intake is snapped to the nearest shore cell: z ${tz}`);
});

test('lake flow: through a channel the water moves to the outlet, builds up downstream, drains the arms, and a cut-off pond is still', async () => {
  const { rasterize, solveField, flowAt, cellAt } = await import('../src/scene/lakefield.js');
  const main = [[[0, 0], [3000, 0], [3000, 300], [0, 300]]]; // channel, west to east
  const arm = [[[1500, 300], [1650, 300], [1650, 1200], [1500, 1200]]]; // arm to the south, touching the channel
  const pond = [[[0, 2000], [600, 2000], [600, 2600], [0, 2600]]]; // joined to nothing
  const g = rasterize([main, arm, pond]);
  const at = (x, z) => ({ kind: '', cell: cellAt(g, x, z), x, z });
  const ends = [{ ...at(60, 150), kind: 'in' }, { ...at(2940, 150), kind: 'out' }];
  const f = solveField(g, ends);
  assert.ok(f.residual < 1e-5, `solver converged: ${f.residual}`);
  const v = [0, 0];
  for (const x of [600, 1200, 2000, 2600]) {
    flowAt(g, f, x, 150, v);
    assert.ok(v[0] > 0 && Math.abs(v[1]) < 0.2 * v[0], `east along the channel at x=${x}: ${v}`);
  }
  const speed = (x) => Math.hypot(...flowAt(g, f, x, 150, [0, 0]));
  assert.ok(speed(2600) > speed(600), 'the flow builds up downstream (the lake adds water as it goes)');
  flowAt(g, f, 1575, 800, v);
  assert.ok(v[1] < 0 && Math.abs(v[0]) < Math.abs(v[1]), `the arm drains north into the channel: ${v}`);
  flowAt(g, f, 1575, 1170, v);
  const tip = Math.hypot(...v);
  flowAt(g, f, 1575, 450, v);
  assert.ok(Math.hypot(...v) > tip * 3, 'the arm is slowest at its head');
  flowAt(g, f, 300, 2300, v);
  assert.deepEqual([...v], [0, 0], 'a pond joined to no outlet is still');
  assert.equal(f.stillParts, 1);
});

test('lake flow: a neck narrower than a cell stays joined; an end with a start date is used from then on', async () => {
  const { rasterize, solveField, lakeField, variantOn, cellAt, flowAt } = await import('../src/scene/lakefield.js');
  // two basins joined by a 10 m wide channel (a third of a cell)
  const lake = [[[0, 0], [600, 0], [600, 290], [1400, 290], [1400, 0], [2000, 0], [2000, 600], [1400, 600], [1400, 300], [600, 300], [600, 600], [0, 600]]];
  const g = rasterize([lake]);
  const ends = [{ kind: 'in', cell: cellAt(g, 100, 300) }, { kind: 'out', cell: cellAt(g, 1900, 300) }];
  const f = solveField(g, ends);
  assert.equal(f.stillParts, 0, 'one connected lake');
  assert.ok(Math.hypot(...flowAt(g, f, 300, 300, [0, 0])) > 0, 'the far basin drains through the neck');
  // a transfer outlet that starts in 2018 makes a second field
  const rivers = [{ name: 'R', pts: [[-300, 150], [300, 150]] }, { name: 'D', pts: [[1700, 150], [2300, 150]] }];
  const tunnels = [{ name: 'Link', a: null, b: { x: 1000, z: 900 }, since: '2018' }];
  const L = lakeField([lake], rivers, tunnels);
  assert.deepEqual(L.variants.map((v) => v.since), [null, '2018']);
  assert.equal(variantOn(L.variants, '2017-12-31').since, null);
  assert.equal(variantOn(L.variants, '2018-03-01').since, '2018');
  assert.deepEqual(L.variants[1].ends.map((e) => e.name).sort(), ['D', 'Link', 'R']);
});
