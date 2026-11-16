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
