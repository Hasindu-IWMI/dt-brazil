// CBERS-4A WPM 2 m colour imagery for the realistic display, around the towns and along the mapped rivers.
//
// Source: INPE's STAC collection CB4A-WPM-PCA-FUSED-1 (CBERS-4A WPM: the 8 m multispectral bands fused
// with the 2 m panchromatic band by principal components; Creative Commons Attribution 4.0). Two scenes
// of the 2024 dry season, the season of the Sentinel-2 base (imagery.jpg), both cloud-free on their
// previews: path 203 on 25 July 2024 (the west of the window) and path 202 on 30 August 2024 (the east).
// They are read by HTTP range requests of the cloud-optimised GeoTIFFs: only the internal 512 px tiles
// the output needs, each once.
//
// 1. Tiles: 1024 m squares on the viewer's scene frame (x east, z south, from buildings/index.json),
//    kept where the buildings come to 200 or more per km2 (buildings/index.json counts), or within 250 m of a river the
//    viewer draws (vectors.json).
// 2. Alignment: for each scene, the shift that best matches its luminance, averaged to 10 m, to
//    Sentinel-2's 10 m true-colour image of 3 August 2024 (one of the base's dates), searched in 2 m
//    steps over +-40 m on up to 16 town squares and refined between steps; the median is applied.
// 3. Colour: for each scene and band, histogram matching to the base imagery (already display-
//    stretched) at the same places, read from the scene's 16 m overview over every kept tile.
// 4. Per tile, the scene whose 16 m overview has data everywhere in the tile and correlates best with
//    the base; a pixel without data there comes from the other scene, else from the base. A tile next
//    to an uncovered square fades into the base over 96 m, so the edge of the coverage does not show.
// 5. Output: web/public/data/imagery_hi/<i>_<j>.jpg (512 px, 2 m) and imagery_hi.json (index and
//    provenance, read by the viewer).
//
// DISPLAY ONLY; it does not change with the replay date. Credit: "CBERS-4A WPM imagery: INPE (CC BY 4.0)".
// Usage: node tools/build_imagery_hi.mjs [--max-gb 0.8] [--limit N]   (--limit: first N tiles, for a test)
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import jpeg from 'jpeg-js';
import { retry, utmForward } from './lib/raster.mjs';

// count every byte read over HTTP (geotiff.js uses the global fetch); stop past the approved budget
const arg = (k, d) => { const i = process.argv.indexOf(k); return i > 0 ? process.argv[i + 1] : d; };
const MAX_BYTES = Number(arg('--max-gb', 0.8)) * 1e9;
const LIMIT = Number(arg('--limit', 0)) || Infinity;
let bytesRead = 0;
const realFetch = globalThis.fetch;
globalThis.fetch = async (...a) => {
  if (bytesRead > MAX_BYTES) throw new Error(`stopped: ${(bytesRead / 1e9).toFixed(2)} GB read, over the approved ${MAX_BYTES / 1e9} GB`);
  const r = await realFetch(...a);
  bytesRead += Number(r.headers.get('content-length') ?? 0);
  return r;
};
const { fromUrl } = await import('geotiff');

const here = path.dirname(fileURLToPath(import.meta.url));
const dataDir = path.resolve(here, '..', 'public', 'data');
const outDir = path.join(dataDir, 'imagery_hi');
const CACHE = path.resolve(here, '..', '.cache', 'cbers'); // git-ignored, like the buildings tool's downloads
// the buildings index gives the town counts; without it (its build can fail on a busy Overpass) only the
// river bands are kept, on the same frame as main.js builds from the terrain window
const ixPath = path.join(dataDir, 'buildings', 'index.json');
const tw = JSON.parse(fs.readFileSync(path.join(dataDir, fs.existsSync(path.join(dataDir, 'terrain_hi.json')) ? 'terrain_hi.json' : 'terrain.json'), 'utf8')).bbox;
const ix = fs.existsSync(ixPath) ? JSON.parse(fs.readFileSync(ixPath, 'utf8')) : { tiles: [] };
if (!ix.tiles.length) console.log('no buildings index: river bands only');
const lat0w = (tw.south + tw.north) / 2;
const F = ix.frame ?? { lon0: (tw.west + tw.east) / 2, lat0: lat0w, KX: 111320 * Math.cos((lat0w * Math.PI) / 180), KZ: 110570 };
const bbox = tw;
const vectors = JSON.parse(fs.readFileSync(path.join(dataDir, 'vectors.json'), 'utf8'));
const RIVERS = ['Rio Atibaia', 'Rio da Cachoeira', 'Rio Atibainha', 'Rio Jaguari', 'Rio Jacareí']; // as main.js draws
const STAC = 'https://data.inpe.br/bdc/stac/v1';
const SCENES = ['CBERS4A_WPM_PCA_RGB321_20240725_203_142', 'CBERS4A_WPM_PCA_RGB321_20240830_202_142'];
const S2_TCI = 'https://sentinel-cogs.s3.us-west-2.amazonaws.com/sentinel-s2-l2a-cogs/23/K/LQ/2024/8/S2A_23KLQ_20240803_0_L2A/TCI.tif';
const T = 1024; // tile size, m
const PX = 512; // tile size, px (2 m)
const M = T / PX;
const TOWN_N = 200; // buildings in a 1 km tile
const RIVER_BAND = 250; // m: a tile is kept if a river passes within this distance of it
const FEATHER = 96; // m
const ZONE = 23; // both scenes and Sentinel-2 are in UTM 23S (EPSG:32723)

const X = (lon) => (lon - F.lon0) * F.KX;
const Z = (lat) => -(lat - F.lat0) * F.KZ;
const lonOf = (x) => F.lon0 + x / F.KX;
const latOf = (z) => F.lat0 - z / F.KZ;
const lum = (r, g, b) => 0.2126 * r + 0.7152 * g + 0.0722 * b;

// ---- 1. tiles
const iMin = Math.floor(X(bbox.west) / T), iMax = Math.ceil(X(bbox.east) / T) - 1;
const jMin = Math.floor(Z(bbox.north) / T), jMax = Math.ceil(Z(bbox.south) / T) - 1;
const want = new Set();
const mark = (x0, x1, z0, z1) => {
  for (let i = Math.max(iMin, Math.floor(x0 / T)); i <= Math.min(iMax, Math.floor((x1 - 1e-6) / T)); i++) {
    for (let j = Math.max(jMin, Math.floor(z0 / T)); j <= Math.min(jMax, Math.floor((z1 - 1e-6) / T)); j++) want.add(`${i}_${j}`);
  }
};
// towns: each 1 km buildings tile spreads its count over the 1024 m tiles it overlaps, by area; a tile
// is kept at TOWN_N or more buildings per km2
const dens = new Map();
for (const t of ix.tiles) {
  const x0 = t.x * 1000, x1 = x0 + 1000, z0 = -(t.y + 1) * 1000, z1 = z0 + 1000;
  for (let i = Math.floor(x0 / T); i <= Math.floor((x1 - 1e-6) / T); i++) {
    for (let j = Math.floor(z0 / T); j <= Math.floor((z1 - 1e-6) / T); j++) {
      const a = Math.max(0, Math.min(x1, (i + 1) * T) - Math.max(x0, i * T)) * Math.max(0, Math.min(z1, (j + 1) * T) - Math.max(z0, j * T));
      dens.set(`${i}_${j}`, (dens.get(`${i}_${j}`) ?? 0) + (t.n * a) / 1e6);
    }
  }
}
let town = 0;
const townKeys = new Set();
for (const [k, n] of dens) {
  const [i, j] = k.split('_').map(Number);
  if (n / ((T * T) / 1e6) >= TOWN_N && i >= iMin && i <= iMax && j >= jMin && j <= jMax) { want.add(k); townKeys.add(k); town++; }
}
const inBox = (lon, lat) => lon >= bbox.west && lon <= bbox.east && lat >= bbox.south && lat <= bbox.north;
for (const r of vectors.rivers) {
  if (!RIVERS.includes(r.name)) continue;
  for (let k = 1; k < r.line.length; k++) {
    const [a, b] = [r.line[k - 1], r.line[k]];
    const xa = X(a[0]), za = Z(a[1]), xb = X(b[0]), zb = Z(b[1]);
    const n = Math.max(1, Math.ceil(Math.hypot(xb - xa, zb - za) / 100));
    for (let s = 0; s <= n; s++) {
      const x = xa + ((xb - xa) * s) / n, z = za + ((zb - za) * s) / n;
      if (inBox(lonOf(x), latOf(z))) mark(x - RIVER_BAND, x + RIVER_BAND, z - RIVER_BAND, z + RIVER_BAND);
    }
  }
}
const tiles = [...want].map((k) => k.split('_').map(Number)).sort((a, b) => a[1] - b[1] || a[0] - b[0]);
console.log(`tiles: ${tiles.length} (${town} by building density, the rest along the rivers)`);

// ---- base imagery (the colour target and the fill), bilinear in sRGB bytes
const baseMeta = JSON.parse(fs.readFileSync(path.join(dataDir, 'imagery.json'), 'utf8'));
const baseImg = jpeg.decode(fs.readFileSync(path.join(dataDir, 'imagery.jpg')), { maxMemoryUsageInMB: 1024 });
const bW = baseImg.width, bH = baseImg.height, bb = baseMeta.bbox;
function base(lon, lat, out) {
  const fx = Math.min(bW - 1.001, Math.max(0, ((lon - bb.west) / (bb.east - bb.west)) * bW - 0.5));
  const fy = Math.min(bH - 1.001, Math.max(0, ((bb.north - lat) / (bb.north - bb.south)) * bH - 0.5));
  const x = Math.floor(fx), y = Math.floor(fy), ax = fx - x, ay = fy - y;
  const d = baseImg.data, i00 = (y * bW + x) * 4, i10 = i00 + 4, i01 = i00 + bW * 4, i11 = i01 + 4;
  for (let c = 0; c < 3; c++) out[c] = (d[i00 + c] * (1 - ax) + d[i10 + c] * ax) * (1 - ay) + (d[i01 + c] * (1 - ax) + d[i11 + c] * ax) * ay;
  return out;
}

// ---- COG access: internal tiles decoded once each and kept in a small LRU cache
class Cog {
  constructor(img, label, geo = null) { // geo: [ox, oy, res] for an overview, which carries no geotransform
    this.img = img;
    this.label = label;
    [this.ox, this.oy, this.res] = geo ?? [...img.getOrigin().slice(0, 2), img.getResolution()[0]];
    this.W = img.getWidth();
    this.H = img.getHeight();
    this.tw = img.getTileWidth();
    this.th = img.getTileHeight();
    this.bands = img.getSamplesPerPixel();
    this.cache = new Map();
  }
  static async open(href, level, label) {
    const tiff = await retry(() => fromUrl(href), label);
    const base0 = await tiff.getImage(0);
    const img = await tiff.getImage(level);
    const [ox, oy] = base0.getOrigin();
    const c = new Cog(img, label, [ox, oy, base0.getResolution()[0] * (base0.getWidth() / img.getWidth())]);
    c.disk = path.join(CACHE, `${label.split(' ')[0]}_L${level}`);
    return c;
  }
  /** The internal tile's file in the download cache (web/.cache/cbers: a re-run reads nothing twice). */
  cached(tx, ty) { return this.disk ? path.join(this.disk, `${tx}_${ty}.bin`) : null; }
  tile(tx, ty) {
    const key = tx + ',' + ty;
    let p = this.cache.get(key);
    if (p) { this.cache.delete(key); this.cache.set(key, p); return p; }
    const x0 = tx * this.tw, y0 = ty * this.th;
    const w = Math.min(this.tw, this.W - x0), h = Math.min(this.th, this.H - y0);
    const file = this.cached(tx, ty);
    p = (file && fs.existsSync(file) ? Promise.resolve(new Uint8Array(fs.readFileSync(file)))
      : retry(() => this.img.readRasters({ window: [x0, y0, x0 + w, y0 + h], interleave: true }), `${this.label} ${key}`)
        .then((data) => { if (file) { fs.mkdirSync(this.disk, { recursive: true }); fs.writeFileSync(file, data); } return data; }))
      .then((data) => ({ data, w, h, x0, y0 }));
    this.cache.set(key, p);
    if (this.cache.size > 360) this.cache.delete(this.cache.keys().next().value);
    return p;
  }
  /** Load every internal tile under a UTM rectangle; returns a sampler (E, N, out) -> out or null (no data). */
  async sampler(e0, n0, e1, n1) {
    const px0 = Math.floor((e0 - this.ox) / this.res) - 2, px1 = Math.ceil((e1 - this.ox) / this.res) + 2;
    const py0 = Math.floor((this.oy - n1) / this.res) - 2, py1 = Math.ceil((this.oy - n0) / this.res) + 2;
    if (px1 < 0 || py1 < 0 || px0 >= this.W || py0 >= this.H) return null;
    const got = new Map();
    const jobs = [];
    for (let ty = Math.max(0, Math.floor(py0 / this.th)); ty <= Math.min(Math.ceil(this.H / this.th) - 1, Math.floor(py1 / this.th)); ty++) {
      for (let tx = Math.max(0, Math.floor(px0 / this.tw)); tx <= Math.min(Math.ceil(this.W / this.tw) - 1, Math.floor(px1 / this.tw)); tx++) {
        jobs.push(this.tile(tx, ty).then((t) => got.set(tx + ',' + ty, t)));
      }
    }
    await Promise.all(jobs);
    const nb = this.bands;
    const px = (x, y) => { // the pixel's bands, or null outside or no data
      if (x < 0 || y < 0 || x >= this.W || y >= this.H) return null;
      const t = got.get(Math.floor(x / this.tw) + ',' + Math.floor(y / this.th));
      if (!t) return null;
      const o = ((y - t.y0) * t.w + (x - t.x0)) * nb;
      return t.data[o] === 0 && t.data[o + 1] === 0 && t.data[o + 2] === 0 ? null : [t.data, o];
    };
    return (E, N, out) => {
      const fx = (E - this.ox) / this.res - 0.5, fy = (this.oy - N) / this.res - 0.5;
      const x = Math.floor(fx), y = Math.floor(fy), ax = fx - x, ay = fy - y;
      const a = px(x, y), b = px(x + 1, y), c = px(x, y + 1), d = px(x + 1, y + 1);
      if (!a || !b || !c || !d) return null;
      for (let k = 0; k < 3; k++) {
        out[k] = (a[0][a[1] + k] * (1 - ax) + b[0][b[1] + k] * ax) * (1 - ay) + (c[0][c[1] + k] * (1 - ax) + d[0][d[1] + k] * ax) * ay;
      }
      return out;
    };
  }
}

const utm = (x, z) => utmForward(lonOf(x), latOf(z), ZONE, true);
/** The UTM rectangle around a scene-frame rectangle, with a margin (m). */
function utmRect(x0, z0, x1, z1, m = 0) {
  const c = [utm(x0, z0), utm(x1, z0), utm(x0, z1), utm(x1, z1)];
  return [Math.min(...c.map((p) => p[0])) - m, Math.min(...c.map((p) => p[1])) - m, Math.max(...c.map((p) => p[0])) + m, Math.max(...c.map((p) => p[1])) + m];
}

// ---- 2-4 per scene: open, colour statistics and tile scores from the 16 m overview, then alignment
const items = await retry(async () => {
  const r = await fetch(`${STAC}/search`, {
    method: 'POST', headers: { 'Content-Type': 'application/json', 'User-Agent': 'upper-atibaia-pipeline/0.1' },
    body: JSON.stringify({ collections: ['CB4A-WPM-PCA-FUSED-1'], ids: SCENES, limit: 10 }),
  });
  const text = await r.text();
  if (!r.ok || !text.trim().startsWith('{')) throw new Error(`STAC search: HTTP ${r.status}, ${text.slice(0, 80)}`);
  return JSON.parse(text);
}, 'STAC search');
const scenes = [];
for (const id of SCENES) {
  const f = items.features.find((g) => g.id === id);
  if (!f) throw new Error('scene not in the catalogue: ' + id);
  const full = await Cog.open(f.assets.tci.href, 0, id);
  const ov = await Cog.open(f.assets.tci.href, 3, id + ' 16m');
  scenes.push({ id, date: f.properties.datetime.slice(0, 10), href: f.assets.tci.href, full, ov, hist: [0, 1, 2].map(() => new Float64Array(256)), baseHist: [0, 1, 2].map(() => new Float64Array(256)), score: new Map() });
}
console.log('scenes', scenes.map((s) => `${s.id} (${s.date}) ${s.full.W}x${s.full.H} @${s.full.res} m, overview @${s.ov.res} m`).join('; '));

// --estimate: the internal tiles the render would read (geometry only, no image data), and how many
// are already in the download cache; west of 46.55 W the path 203 scene, else path 202
if (process.argv.includes('--estimate')) {
  const MB = 0.71; // measured: one 512 px internal tile of these files, read by range
  for (const [label, filter] of [['all kept tiles', () => true], ['town tiles only', (k) => townKeys.has(k)]]) {
    const need = new Set();
    let cached = 0;
    for (const [i, j] of tiles) {
      if (!filter(`${i}_${j}`)) continue;
      const s = lonOf((i + 0.5) * T) < -46.55 ? scenes[0] : scenes[1];
      const c = s.full;
      const [e0, n0, e1, n1] = utmRect(i * T, j * T, i * T + T, j * T + T, 8);
      for (let ty = Math.floor(((c.oy - n1) / c.res - 2) / c.th); ty <= Math.floor(((c.oy - n0) / c.res + 2) / c.th); ty++) {
        for (let tx = Math.floor(((e0 - c.ox) / c.res - 2) / c.tw); tx <= Math.floor(((e1 - c.ox) / c.res + 2) / c.tw); tx++) {
          const k = `${s.id} ${tx},${ty}`;
          if (need.has(k)) continue;
          need.add(k);
          if (fs.existsSync(c.cached(tx, ty))) cached++;
        }
      }
    }
    console.log(`${label}: ${need.size} internal tiles, ${cached} cached; about ${((need.size - cached) * MB / 1000).toFixed(2)} GB still to read at 2 m`);
  }
  process.exit(0);
}

// overview pass: per tile and scene, data cover and correlation with the base on a 64 m lattice; colour histograms
const tmp = [0, 0, 0], tb = [0, 0, 0];
for (const [i, j] of tiles) {
  const x0 = i * T, z0 = j * T;
  for (const s of scenes) {
    const smp = await s.ov.sampler(...utmRect(x0, z0, x0 + T, z0 + T, 64));
    let n = 0, valid = 0, sa = 0, sb = 0, saa = 0, sbb = 0, sab = 0;
    for (let r = 0; r < 16; r++) {
      for (let c = 0; c < 16; c++) {
        const x = x0 + (c + 0.5) * 64, z = z0 + (r + 0.5) * 64;
        n++;
        const [E, N] = utm(x, z);
        if (!smp || !smp(E, N, tmp)) continue;
        valid++;
        base(lonOf(x), latOf(z), tb);
        for (let k = 0; k < 3; k++) { s.hist[k][Math.max(0, Math.min(255, Math.round(tmp[k])))]++; s.baseHist[k][Math.round(tb[k])]++; }
        const a = lum(...tmp), b = lum(...tb);
        sa += a; sb += b; saa += a * a; sbb += b * b; sab += a * b;
      }
    }
    const cov = (sab - (sa * sb) / valid) / Math.sqrt(Math.max(1e-9, (saa - (sa * sa) / valid) * (sbb - (sb * sb) / valid)));
    s.score.set(`${i}_${j}`, { cover: valid / n, corr: valid > 20 ? cov : -1 });
  }
}
// colour: per band, the base value at the scene value's quantile (histogram matching)
for (const s of scenes) {
  s.lut = [0, 1, 2].map((k) => {
    const cdf = (h) => { const t = h.reduce((a, b) => a + b, 0) || 1; let acc = 0; return Array.from(h, (v) => (acc += v) / t); };
    const cs = cdf(s.hist[k]), cb = cdf(s.baseHist[k]);
    const lut = new Float32Array(256);
    let q = 0;
    for (let v = 0; v < 256; v++) { while (q < 255 && cb[q] < cs[v]) q++; lut[v] = q; }
    return lut;
  });
}
console.log('overview pass done; read so far', (bytesRead / 1e6).toFixed(0), 'MB');

// alignment against Sentinel-2 10 m on town squares wholly covered by the scene, spread out
const s2tiff = await retry(() => fromUrl(S2_TCI), 'S2 TCI');
const s2img = await s2tiff.getImage(0);
const s2 = new Cog(s2img, 'S2 TCI');
s2.disk = path.join(CACHE, 'S2A_23KLQ_20240803_L0');
const townSet = new Set();
for (const t of ix.tiles) if (t.n >= 500) for (const [i, j] of tiles) if (Math.abs(i * T + T / 2 - (t.x + 0.5) * 1000) < 600 && Math.abs(j * T + T / 2 + (t.y + 0.5) * 1000) < 600) townSet.add(`${i}_${j}`);
for (const s of scenes) {
  const cands = tiles.filter(([i, j]) => townSet.has(`${i}_${j}`) && s.score.get(`${i}_${j}`).cover === 1);
  const picks = [];
  for (const t of cands) if (picks.every((p) => Math.hypot(p[0] - t[0], p[1] - t[1]) >= 5) && picks.length < 16) picks.push(t);
  const found = [];
  for (const [i, j] of picks) {
    const [e0, n0, e1, n1] = utmRect(i * T, j * T, i * T + T, j * T + T);
    const s2s = await s2.sampler(e0, n0, e1, n1);
    const cbs = await s.full.sampler(e0 - 60, n0 - 60, e1 + 60, n1 + 60);
    if (!s2s || !cbs) continue;
    // Sentinel-2 pixel centres inside the square, and the scene's 2 m luminance around them
    const ref = [], at = [];
    for (let E = Math.ceil((e0 - s2.ox) / 10) * 10 + s2.ox + 5; E < e1; E += 10) {
      for (let N = s2.oy - Math.ceil((s2.oy - n1) / 10) * 10 - 5; N > n0; N -= 10) {
        if (s2s(E, N, tmp)) { ref.push(lum(...tmp)); at.push([E, N]); }
      }
    }
    const L = (E, N) => (cbs(E, N, tb) ? lum(...tb) : NaN);
    const block = (E, N) => { // mean of the 5 x 5 scene pixels (10 m) centred on (E, N)
      let sum = 0;
      for (let a = -2; a <= 2; a++) for (let b = -2; b <= 2; b++) { const v = L(E + a * 2, N + b * 2); if (Number.isNaN(v)) return NaN; sum += v; }
      return sum / 25;
    };
    const corrAt = (dE, dN) => {
      let n = 0, sa = 0, sb = 0, saa = 0, sbb = 0, sab = 0;
      for (let k = 0; k < at.length; k += 3) { // every third pixel: plenty, and three times as fast
        const b = block(at[k][0] + dE, at[k][1] + dN);
        if (Number.isNaN(b)) continue;
        const a = ref[k];
        n++; sa += a; sb += b; saa += a * a; sbb += b * b; sab += a * b;
      }
      return n < 500 ? -1 : (sab - (sa * sb) / n) / Math.sqrt(Math.max(1e-9, (saa - (sa * sa) / n) * (sbb - (sb * sb) / n)));
    };
    let best = { c: -2, dE: 0, dN: 0 };
    const grid = new Map();
    for (let dE = -40; dE <= 40; dE += 4) for (let dN = -40; dN <= 40; dN += 4) { const c = corrAt(dE, dN); grid.set(dE + ',' + dN, c); if (c > best.c) best = { c, dE, dN }; }
    for (let dE = best.dE - 4; dE <= best.dE + 4; dE += 2) for (let dN = best.dN - 4; dN <= best.dN + 4; dN += 2) {
      const c = grid.get(dE + ',' + dN) ?? corrAt(dE, dN); grid.set(dE + ',' + dN, c); if (c > best.c) best = { c, dE, dN };
    }
    const g = (dE, dN) => grid.get(dE + ',' + dN) ?? corrAt(dE, dN);
    const para = (m, c0, p) => { const d = m - 2 * c0 + p; return d < 0 ? (0.5 * (m - p)) / d * 2 : 0; }; // offset in m (step 2 m)
    const fE = best.dE + para(g(best.dE - 2, best.dN), best.c, g(best.dE + 2, best.dN));
    const fN = best.dN + para(g(best.dE, best.dN - 2), best.c, g(best.dE, best.dN + 2));
    found.push({ tile: `${i}_${j}`, corr: +best.c.toFixed(3), east: +fE.toFixed(1), north: +fN.toFixed(1) });
  }
  const good = found.filter((f) => f.corr >= 0.5);
  const med = (a) => { const b = [...a].sort((x, y) => x - y); return b.length ? (b[(b.length - 1) >> 1] + b[b.length >> 1]) / 2 : 0; };
  s.shift = { east: +med(good.map((f) => f.east)).toFixed(1), north: +med(good.map((f) => f.north)).toFixed(1), squares: found, used: good.length };
  s.shift.spreadM = +med(good.map((f) => Math.hypot(f.east - s.shift.east, f.north - s.shift.north))).toFixed(1);
  console.log(`${s.id}: shift east ${s.shift.east} m, north ${s.shift.north} m (median of ${good.length} squares, spread ${s.shift.spreadM} m)`);
}
console.log('alignment done; read so far', (bytesRead / 1e6).toFixed(0), 'MB');

// ---- 5. render the tiles
fs.mkdirSync(outDir, { recursive: true });
for (const f of fs.readdirSync(outDir)) if (f.endsWith('.jpg')) fs.unlinkSync(path.join(outDir, f));
const done = [];
const perScene = Object.fromEntries(scenes.map((s) => [s.id, 0]));
let filledFromBase = 0;
const rgb = new Float32Array(PX * PX * 3);
const sharp = Buffer.alloc(PX * PX * 4);
/** A tile's scenes in order of use, and their samplers: the second scene is read only where the first
 * does not cover the whole tile. */
async function prepare([i, j]) {
  const key = `${i}_${j}`;
  // the scene: data everywhere and the best correlation with the base; else the most data
  const order = [...scenes].sort((a, b) => {
    const A = a.score.get(key), B = b.score.get(key);
    return (B.cover === 1) - (A.cover === 1) || (A.cover === 1 ? B.corr - A.corr : B.cover - A.cover);
  });
  if (order[0].score.get(key).cover === 0) return null; // no scene covers it: the base stays
  const [e0, n0, e1, n1] = utmRect(i * T, j * T, i * T + T, j * T + T, 8);
  const smp = [];
  for (const [k, s] of order.entries()) {
    const need = s.score.get(key).cover > 0 && (k === 0 || order[0].score.get(key).cover < 1);
    smp.push(need ? await s.full.sampler(e0 + s.shift.east, n0 + s.shift.north, e1 + s.shift.east, n1 + s.shift.north) : null);
  }
  return { order, smp };
}
const AHEAD = 6; // tiles read ahead while one is rendered
const todo = tiles.slice(0, LIMIT);
const pending = todo.slice(0, AHEAD).map(prepare);
for (let q = 0; q < todo.length; q++) {
  const [i, j] = todo[q];
  const key = `${i}_${j}`;
  const prep = await pending[q];
  pending[q] = null;
  if (q + AHEAD < todo.length) pending[q + AHEAD] = prepare(todo[q + AHEAD]);
  if (!prep) continue;
  const { order, smp } = prep;
  const x0 = i * T, z0 = j * T;
  const has = (di, dj) => want.has(`${i + di}_${j + dj}`);
  const used = new Set();
  for (let r = 0; r < PX; r++) {
    for (let c = 0; c < PX; c++) {
      const x = x0 + (c + 0.5) * M, z = z0 + (r + 0.5) * M;
      const lon = lonOf(x), lat = latOf(z);
      const [E, N] = utmForward(lon, lat, ZONE, true);
      let got = null;
      for (let k = 0; k < order.length && !got; k++) {
        const s = order[k];
        if (smp[k] && smp[k](E + s.shift.east, N + s.shift.north, tmp)) {
          got = s;
          for (let b = 0; b < 3; b++) { const v = Math.min(255, tmp[b]), lo = Math.floor(v), hi = Math.min(255, lo + 1); tmp[b] = s.lut[b][lo] + (s.lut[b][hi] - s.lut[b][lo]) * (v - lo); }
        }
      }
      base(lon, lat, tb);
      // fade into the base toward an edge (or corner) with no tile beyond
      const dl = (c + 0.5) * M, dr = T - dl, dt = (r + 0.5) * M, db = T - dt;
      let d = Infinity;
      if (!has(-1, 0)) d = Math.min(d, dl);
      if (!has(1, 0)) d = Math.min(d, dr);
      if (!has(0, -1)) d = Math.min(d, dt);
      if (!has(0, 1)) d = Math.min(d, db);
      if (!has(-1, -1)) d = Math.min(d, Math.hypot(dl, dt));
      if (!has(1, -1)) d = Math.min(d, Math.hypot(dr, dt));
      if (!has(-1, 1)) d = Math.min(d, Math.hypot(dl, db));
      if (!has(1, 1)) d = Math.min(d, Math.hypot(dr, db));
      const t = Math.min(1, d / FEATHER);
      const w = got ? t * t * (3 - 2 * t) : 0;
      if (got) used.add(got.id); else filledFromBase++;
      for (let b = 0; b < 3; b++) rgb[(r * PX + c) * 3 + b] = tmp[b] * w + tb[b] * (1 - w);
    }
  }
  // a light unsharp mask, to give back what the resampling softened
  for (let r = 0; r < PX; r++) {
    for (let c = 0; c < PX; c++) {
      for (let b = 0; b < 3; b++) {
        const v = (rr, cc) => rgb[(Math.min(PX - 1, Math.max(0, rr)) * PX + Math.min(PX - 1, Math.max(0, cc))) * 3 + b];
        const blur = (v(r - 1, c) + v(r + 1, c) + v(r, c - 1) + v(r, c + 1) + 4 * v(r, c)) / 8;
        sharp[(r * PX + c) * 4 + b] = Math.max(0, Math.min(255, Math.round(v(r, c) + 0.45 * (v(r, c) - blur))));
      }
      sharp[(r * PX + c) * 4 + 3] = 255;
    }
  }
  fs.writeFileSync(path.join(outDir, `${key}.jpg`), jpeg.encode({ data: sharp, width: PX, height: PX }, 84).data);
  for (const id of used) perScene[id]++;
  done.push([i, j]);
  if (done.length % 50 === 0) console.log(`${done.length}/${tiles.length} tiles, read ${(bytesRead / 1e6).toFixed(0)} MB`);
}

const bytesOut = done.reduce((s, [i, j]) => s + fs.statSync(path.join(outDir, `${i}_${j}.jpg`)).size, 0);
fs.writeFileSync(path.join(dataDir, 'imagery_hi.json'), JSON.stringify({
  title: 'CBERS-4A WPM 2 m colour imagery around the towns and along the mapped rivers',
  source: "INPE STAC collection CB4A-WPM-PCA-FUSED-1 (CBERS-4A WPM, multispectral fused with the 2 m panchromatic band), data.inpe.br",
  licence: 'Creative Commons Attribution 4.0 International', attribution: 'CBERS-4A WPM imagery: INPE (CC BY 4.0)',
  meaning: 'Display basemap detail for the 2024 dry season, the season of the Sentinel-2 base. It does NOT change with the replay date.',
  frame: F, tileM: T, tilePx: PX, pixelM: M, dir: 'imagery_hi',
  selection: { townBuildingsPerKm2: TOWN_N, riverBandM: RIVER_BAND, rivers: RIVERS, featherM: FEATHER },
  alignment: { reference: S2_TCI, method: 'shift maximising the correlation of luminance averaged to 10 m with Sentinel-2 10 m, +-40 m in 2 m steps, refined by a parabola; median over town squares' },
  colour: 'per scene and band, histogram matching to the base imagery (imagery.jpg) on a 64 m lattice over every tile, from the 16 m overview',
  scenes: scenes.map((s) => ({ id: s.id, date: s.date, href: s.href, shiftM: s.shift, tiles: perScene[s.id] })),
  tiles: done, pixelsFromBase: filledFromBase, bytesRead, bytesOut, built: new Date().toISOString(),
}));
console.log(`done: ${done.length} tiles, ${(bytesOut / 1e6).toFixed(1)} MB written, ${(bytesRead / 1e6).toFixed(0)} MB read`);
