// Sentinel-2 L2A true-colour ground imagery for the realistic display.
//
// 1. STAC search (Element 84 Earth Search, no login) for L2A scenes over the scene window in the
//    dry season (SEASON). Keep dates on which EVERY Sentinel-2 tile covering the window is almost
//    cloud-free (MAX_TILE_CLOUD %), up to MAX_DATES of them.
// 2. Window reads, over HTTP range requests, of the 20 m overview of the TCI ('visual') COG and of
//    the 20 m scene classification (SCL), in UTM.
// 3. Each output pixel (geographic grid on the DEM window) samples every date (bilinear for colour,
//    nearest for SCL). Pixels flagged no-data, saturated, cloud shadow, cloud or cirrus (SCL 0, 1,
//    3, 8, 9, 10) are dropped. Of the remaining observations the one with the median luminance is
//    kept (lower median for an even count), so colours are never mixed between dates.
// 4. One linear display stretch (luminance percentiles) for the whole image, then JPEG.
//
// The result is a DISPLAY BASEMAP for one dry season. It does not change with the replay date.
// Licence: Copernicus Sentinel data, free and open. "Contains modified Copernicus Sentinel data 2024".
//
// Usage: node tools/build_imagery.mjs
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { fromUrl } from 'geotiff';
import jpeg from 'jpeg-js';
import { retry, utmForward } from './lib/raster.mjs';

const here = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(here, '..', '..');
const outDir = path.resolve(here, '..', 'public', 'data');
const bbox = JSON.parse(fs.readFileSync(path.join(root, 'data', 'raw', 'dem', 'delineation.json'), 'utf8')).bbox;

const STAC = 'https://earth-search.aws.element84.com/v1/search';
const SEASON = ['2024-07-15T00:00:00Z', '2024-09-01T00:00:00Z'];
const MAX_TILE_CLOUD = 0.05; // % of the tile
const MAX_DATES = 4;
const BAD_SCL = new Set([0, 1, 3, 8, 9, 10]);
const OUT_W = 4096;
const OUT_H = Math.round((OUT_W * (bbox.north - bbox.south)) / (bbox.east - bbox.west));
const STRETCH = [0.2, 99.7]; // luminance percentiles mapped to 0 and 255

// ---- 1. scenes
const body = { collections: ['sentinel-2-l2a'], bbox: [bbox.west, bbox.south, bbox.east, bbox.north],
  datetime: SEASON.join('/'), query: { 'eo:cloud_cover': { lt: 1 } }, limit: 200 };
const res = await fetch(STAC, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
const items = (await res.json()).features;
const tilesAll = new Set(items.map((f) => f.properties['grid:code']));
const byDate = new Map();
for (const f of items) {
  const day = f.properties.datetime.slice(0, 10);
  if (!byDate.has(day)) byDate.set(day, []);
  byDate.get(day).push(f);
}
const dates = [...byDate.entries()]
  .filter(([, fs2]) => new Set(fs2.map((f) => f.properties['grid:code'])).size === tilesAll.size
    && fs2.every((f) => f.properties['eo:cloud_cover'] < MAX_TILE_CLOUD))
  .sort((a, b) => Math.max(...a[1].map((f) => f.properties['eo:cloud_cover'])) - Math.max(...b[1].map((f) => f.properties['eo:cloud_cover'])) || a[0].localeCompare(b[0]))
  .slice(0, MAX_DATES)
  .sort((a, b) => a[0].localeCompare(b[0]));
if (!dates.length) throw new Error('no date with every tile cloud-free; widen SEASON or MAX_TILE_CLOUD');
console.log('tiles', [...tilesAll].join(' '), '| dates', dates.map(([d]) => d).join(' '));

// ---- output grid -> UTM (one zone for the window; stored relative to an origin as float32)
const epsgOf = (f) => Number(String(f.properties['proj:epsg'] ?? f.properties['proj:code'] ?? '').replace('EPSG:', ''));
const epsg = epsgOf(dates[0][1][0]);
const zone = epsg % 100;
const south = Math.floor(epsg / 100) === 327;
const N = OUT_W * OUT_H;
const E0 = 500000;
const N0 = south ? 7400000 : 0;
const east = new Float32Array(N);
const north = new Float32Array(N);
const dLon = (bbox.east - bbox.west) / OUT_W;
const dLat = (bbox.north - bbox.south) / OUT_H;
let eMin = Infinity, eMax = -Infinity, nMin = Infinity, nMax = -Infinity;
for (let j = 0; j < OUT_H; j++) {
  const lat = bbox.north - (j + 0.5) * dLat;
  for (let i = 0; i < OUT_W; i++) {
    const [x, y] = utmForward(bbox.west + (i + 0.5) * dLon, lat, zone, south);
    east[j * OUT_W + i] = x - E0;
    north[j * OUT_W + i] = y - N0;
    eMin = Math.min(eMin, x); eMax = Math.max(eMax, x); nMin = Math.min(nMin, y); nMax = Math.max(nMax, y);
  }
}

// ---- 2-3. read and sample every tile of every date
async function overview20(href) {
  const tiff = await fromUrl(href);
  const base = await tiff.getImage(0);
  const [ox, oy] = base.getOrigin();
  const [rx] = base.getResolution();
  let img = base;
  for (let k = 1, n = await tiff.getImageCount(); k < n; k++) {
    const cand = await tiff.getImage(k);
    if (Math.abs(rx * (base.getWidth() / cand.getWidth()) - 20) < Math.abs(rx * (base.getWidth() / img.getWidth()) - 20)) img = cand;
  }
  const res = rx * (base.getWidth() / img.getWidth());
  return { img, ox, oy, res };
}
function windowFor(o) {
  const m = 2 * o.res;
  const x0 = Math.max(0, Math.floor((eMin - m - o.ox) / o.res));
  const x1 = Math.min(o.img.getWidth(), Math.ceil((eMax + m - o.ox) / o.res));
  const y0 = Math.max(0, Math.floor((o.oy - (nMax + m)) / o.res));
  const y1 = Math.min(o.img.getHeight(), Math.ceil((o.oy - (nMin - m)) / o.res));
  return x1 > x0 && y1 > y0 ? [x0, y0, x1, y1] : null;
}

const obs = [];
const used = [];
for (const [day, feats] of dates) {
  const rgb = new Uint8Array(N * 3);
  const ok = new Uint8Array(N);
  for (const f of feats) {
    const tci = await retry(() => overview20(f.assets.visual.href), f.id);
    const scl = await retry(() => overview20(f.assets.scl.href), f.id);
    const wt = windowFor(tci);
    const ws = windowFor(scl);
    if (!wt || !ws) continue;
    const c = await retry(() => tci.img.readRasters({ window: wt, interleave: true }), f.id + ' TCI');
    const [s] = await retry(() => scl.img.readRasters({ window: ws }), f.id + ' SCL');
    const tw = wt[2] - wt[0], th = wt[3] - wt[1], sw = ws[2] - ws[0], sh = ws[3] - ws[1];
    let n = 0;
    for (let p = 0; p < N; p++) {
      if (ok[p]) continue; // already filled by the other tile of the same overpass
      const E = east[p] + E0, Nn = north[p] + N0;
      const si = Math.floor((E - scl.ox) / scl.res) - ws[0];
      const sj = Math.floor((scl.oy - Nn) / scl.res) - ws[1];
      if (si < 0 || sj < 0 || si >= sw || sj >= sh || BAD_SCL.has(s[sj * sw + si])) continue;
      const fx = (E - tci.ox) / tci.res - 0.5 - wt[0];
      const fy = (tci.oy - Nn) / tci.res - 0.5 - wt[1];
      const x = Math.floor(fx), y = Math.floor(fy);
      if (x < 0 || y < 0 || x + 1 >= tw || y + 1 >= th) continue;
      const ax = fx - x, ay = fy - y;
      const i00 = (y * tw + x) * 3, i10 = i00 + 3, i01 = i00 + tw * 3, i11 = i01 + 3;
      if (!(c[i00] | c[i00 + 1] | c[i00 + 2]) || !(c[i10] | c[i10 + 1] | c[i10 + 2])
        || !(c[i01] | c[i01 + 1] | c[i01 + 2]) || !(c[i11] | c[i11 + 1] | c[i11 + 2])) continue; // edge no-data
      for (let b = 0; b < 3; b++) {
        rgb[p * 3 + b] = Math.round((c[i00 + b] * (1 - ax) + c[i10 + b] * ax) * (1 - ay) + (c[i01 + b] * (1 - ax) + c[i11 + b] * ax) * ay);
      }
      ok[p] = 1;
      n++;
    }
    used.push({ id: f.id, datetime: f.properties.datetime, cloud_cover_pct: f.properties['eo:cloud_cover'], visual: f.assets.visual.href, scl: f.assets.scl.href, pixels: n });
    console.log(day, f.properties['grid:code'], 'clear pixels', n);
  }
  obs.push({ rgb, ok });
}

// ---- composite: per pixel, the observation with the (lower) median luminance
const out = new Uint8Array(N * 3);
let empty = 0;
const lum = (a, i) => 0.2126 * a[i] + 0.7152 * a[i + 1] + 0.0722 * a[i + 2];
const hist = new Float64Array(256);
const cand = [];
for (let p = 0; p < N; p++) {
  cand.length = 0;
  for (const o of obs) if (o.ok[p]) cand.push(o.rgb);
  if (!cand.length) { empty++; continue; }
  cand.sort((a, b) => lum(a, p * 3) - lum(b, p * 3));
  const pick = cand[(cand.length - 1) >> 1];
  out[p * 3] = pick[p * 3]; out[p * 3 + 1] = pick[p * 3 + 1]; out[p * 3 + 2] = pick[p * 3 + 2];
  hist[Math.round(lum(out, p * 3))]++;
}

// ---- 4. display stretch and JPEG
const total = N - empty;
const pct = (q) => { let acc = 0; for (let v = 0; v < 256; v++) { acc += hist[v]; if (acc >= (q / 100) * total) return v; } return 255; };
const lo = pct(STRETCH[0]);
const hi = Math.max(lo + 1, pct(STRETCH[1]));
const rgba = Buffer.alloc(N * 4);
for (let p = 0; p < N; p++) {
  for (let b = 0; b < 3; b++) rgba[p * 4 + b] = Math.max(0, Math.min(255, Math.round(((out[p * 3 + b] - lo) / (hi - lo)) * 255)));
  rgba[p * 4 + 3] = 255;
}
const jpg = jpeg.encode({ data: rgba, width: OUT_W, height: OUT_H }, 88);
fs.writeFileSync(path.join(outDir, 'imagery.jpg'), jpg.data);
fs.writeFileSync(path.join(outDir, 'imagery.json'), JSON.stringify({
  source: 'Sentinel-2 L2A (ESA Copernicus), TCI and SCL COGs via Element 84 Earth Search (AWS sentinel-cogs)',
  attribution: 'Contains modified Copernicus Sentinel data 2024',
  licence: 'Copernicus Sentinel data: free, full and open (Sentinel data legal notice)',
  meaning: 'Dry-season ground imagery for display. It is one season (dates below) and does NOT change with the replay date.',
  bbox, width: OUT_W, height: OUT_H, crs: 'EPSG:4326 grid (pixel centres)', approxPixelM: 20,
  season: SEASON, maxTileCloudPct: MAX_TILE_CLOUD, maskedScl: [...BAD_SCL],
  method: 'per pixel, the cloud-free observation with the median luminance (lower median for even counts)',
  stretch: { luminancePercentiles: STRETCH, lo, hi }, pixelsWithoutClearObservation: empty,
  scenes: used, built: new Date().toISOString(),
}, null, 2));
console.log('imagery', OUT_W, 'x', OUT_H, 'stretch', lo, hi, 'empty', empty, 'jpeg bytes', jpg.data.length);
