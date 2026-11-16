// Building footprints and heights for the 3D viewer, after the Kelani WebTwin
// (pipeline/31_build_buildings.py and 33_fetch_building_heights.py).
//
// Footprints, in order of preference:
//   1. OpenStreetMap building ways and multipolygon relations (Overpass API; ODbL), with their tags.
//   2. Microsoft Global ML Building Footprints (ODbL), only where no OSM building overlaps:
//      a Microsoft footprint is dropped when its centroid lies in an OSM building or an OSM
//      building's centroid lies in it.
// Height per building (`hsrc` in the tiles), in order of preference:
//   2 = OSM `height` tag;  1 = OSM `building:levels` × STOREY_M;
//   3 = Google Open Buildings 2.5D Temporal, 2023 epoch (CC BY 4.0): median `building_height` of the
//       2 m pixels whose centres lie inside the footprint eroded by 1 m (all pixels inside if none).
//       A model estimate; medians below 2 m count as "not detected";
//   4 = the Microsoft footprint's own height estimate, where it has one;
//   0 = no information: PLACEHOLDER_M, a display placeholder, not a measurement.
// Base elevation is NOT stored: the viewer samples the terrain it draws.
//
// Output (generated, not committed; see .gitignore): web/public/data/buildings/{x}_{y}.bin (gzip of
// the UBT1 layout in src/scene/buildingTile.js, one per 1 km square of the viewer's local frame, by
// centroid) and buildings/index.json. The provenance record web/public/data/buildings.json IS committed.
// Downloads are cached in web/.cache/buildings/ (about 300 MB; --refresh fetches again).
//
// Usage: node tools/build_buildings.mjs [--refresh] [--no-osm]
//   --no-osm  skip OpenStreetMap (Microsoft footprints only; for tests, or while Overpass is down)
import fs from 'node:fs';
import path from 'node:path';
import zlib from 'node:zlib';
import readline from 'node:readline';
import { pipeline } from 'node:stream/promises';
import { Readable } from 'node:stream';
import { fileURLToPath } from 'node:url';
import { fromUrl } from 'geotiff';
import { retry, utmForward } from './lib/raster.mjs';
import {
  parseHeight, parseLevels, classOf, roofOf, ringArea, pointInRing, cleanRing, orient, footprintPixel, footprintMedian, encodeBuildingTile,
} from './lib/buildings.mjs';

const STOREY_M = 3.0;
const PLACEHOLDER_M = 4.0;
const GOB_MIN_M = 2.0;
const MIN_AREA_M2 = 4.0;
const TILE_M = 1000;
const QUANTUM_M = 0.05;
const UTM_ZONE = 23; // EPSG:32723, the Google 2.5D grid for this window
// the main instance first and most often; a mirror now and then (they are often down, and a dead one
// costs a long timeout)
const MAIN = 'https://overpass-api.de/api/interpreter';
const OVERPASS = [MAIN, MAIN, MAIN, 'https://overpass.kumi.systems/api/interpreter', MAIN, MAIN, MAIN, 'https://overpass.private.coffee/api/interpreter'];
const MS_LINKS = 'https://minedbuildings.z5.web.core.windows.net/global-buildings/dataset-links.csv';
const GOB = 'https://storage.googleapis.com/open-buildings-temporal-data/v1';
const GOB_MANIFESTS = ['01', '07', '93', '95'].map((s) => `${s}_EPSG_32723_2023_06_30.json`);

const here = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(here, '..', '..');
const dataDir = path.resolve(here, '..', 'public', 'data');
const outDir = path.join(dataDir, 'buildings');
const cache = path.resolve(here, '..', '.cache', 'buildings');
const refresh = process.argv.includes('--refresh');
const noOsm = process.argv.includes('--no-osm');
fs.mkdirSync(cache, { recursive: true });

const bbox = JSON.parse(fs.readFileSync(path.join(root, 'data', 'raw', 'dem', 'delineation.json'), 'utf8')).bbox;
// the viewer's local frame (main.js): equirectangular about the window centre, x east, y north
const lon0 = (bbox.west + bbox.east) / 2;
const lat0 = (bbox.south + bbox.north) / 2;
const KX = 111320 * Math.cos((lat0 * Math.PI) / 180);
const KZ = 110570;
const toLocal = (lon, lat) => [(lon - lon0) * KX, (lat - lat0) * KZ];
const inBox = (lon, lat) => lon >= bbox.west && lon <= bbox.east && lat >= bbox.south && lat <= bbox.north;
const t0 = Date.now();
const log = (...a) => console.log(`[${((Date.now() - t0) / 1000).toFixed(0)}s]`, ...a);

async function cached(name, fetcher) {
  const f = path.join(cache, name);
  if (!refresh && fs.existsSync(f) && fs.statSync(f).size > 0) return f;
  await fetcher(f + '.part');
  fs.renameSync(f + '.part', f);
  return f;
}

// ---------------------------------------------------------------- OpenStreetMap

async function overpass(query, label) {
  let k = 0;
  return retry(async () => {
    const url = OVERPASS[k++ % OVERPASS.length];
    const res = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded', 'User-Agent': 'upper-atibaia-pipeline/0.1' },
      body: 'data=' + encodeURIComponent(query),
      signal: AbortSignal.timeout(url === MAIN ? 150000 : 60000),
    });
    const text = await res.text();
    if (!res.ok || !text.startsWith('{')) throw new Error(`${new URL(url).host} ${res.status}`);
    const j = JSON.parse(text);
    if (j.remark && /runtime error|timed out/i.test(j.remark)) throw new Error(`${new URL(url).host}: ${j.remark}`);
    return text;
  }, label, 16);
}

/** stitch member ways (arrays of [lon, lat]) into closed rings */
function stitch(segs) {
  segs = segs.filter((s) => s.length >= 2);
  const rings = [];
  const same = (a, b) => a[0] === b[0] && a[1] === b[1];
  while (segs.length) {
    let cur = segs.shift();
    for (let grew = true; grew && !same(cur[0], cur.at(-1));) {
      grew = false;
      for (let i = 0; i < segs.length; i++) {
        const s = segs[i];
        if (same(s[0], cur.at(-1))) { cur = cur.concat(s.slice(1)); segs.splice(i, 1); grew = true; break; }
        if (same(s.at(-1), cur.at(-1))) { cur = cur.concat(s.slice().reverse().slice(1)); segs.splice(i, 1); grew = true; break; }
      }
    }
    if (same(cur[0], cur.at(-1)) && cur.length >= 4) rings.push(cur);
  }
  return rings;
}

async function osmBuildings() {
  // A busy Overpass server refuses queries that declare a long timeout, and refuses most queries of any
  // size while it is at capacity: so a short declared timeout, and blocks of 2 x 2 chunks of an 8 x 8 grid
  // (each about 20 x 16 km) to keep the number of requests down. Chunk files from earlier runs are reused.
  const NX = 8, NY = 8, G = 2;
  const dx = (bbox.east - bbox.west) / NX, dy = (bbox.north - bbox.south) / NY;
  const seen = new Set();
  const out = [];
  const skipped = { geometry: 0, outside: 0 };
  for (let j = 0; j < NY; j += G) {
    for (let i = 0; i < NX; i += G) {
      const parts = [];
      for (let dj = 0; dj < G; dj++) for (let di = 0; di < G; di++) parts.push(path.join(cache, `osm_buildings_${i + di}_${j + dj}.json`));
      let files = parts;
      if (refresh || !parts.every((p) => fs.existsSync(p))) {
        const s = bbox.south + j * dy, w = bbox.west + i * dx;
        const b = `${s.toFixed(5)},${w.toFixed(5)},${(s + G * dy).toFixed(5)},${(w + G * dx).toFixed(5)}`;
        files = [await cached(`osm_buildings_block_${i}_${j}.json`, async (dest) => {
          const q = `[out:json][timeout:90];(way["building"](${b});relation["building"]["type"="multipolygon"](${b}););out body geom qt;`;
          fs.writeFileSync(dest, await overpass(q, `osm block ${i},${j}`));
        })];
      }
      const els = files.flatMap((f) => JSON.parse(fs.readFileSync(f, 'utf8')).elements ?? []);
      let n = 0;
      for (const e of els) {
        const key = `${e.type}/${e.id}`;
        if (seen.has(key)) continue;
        seen.add(key);
        const tags = e.tags ?? {};
        if (tags.building === 'no' || !tags.building) continue;
        let polys = []; // [{outer, holes}] in lon/lat
        if (e.type === 'way') {
          const g = (e.geometry ?? []).filter(Boolean).map((p) => [p.lon, p.lat]);
          if (g.length >= 4 && g[0][0] === g.at(-1)[0] && g[0][1] === g.at(-1)[1]) polys = [{ outer: g, holes: [] }];
        } else {
          const mem = (role) => stitch((e.members ?? []).filter((m) => m.type === 'way' && (m.role || 'outer') === role && m.geometry)
            .map((m) => m.geometry.filter(Boolean).map((p) => [p.lon, p.lat])));
          const inners = mem('inner');
          polys = mem('outer').map((o) => ({ outer: o, holes: inners.filter((h) => pointInRing(h[0][0], h[0][1], o)) }));
        }
        if (!polys.length) { skipped.geometry++; continue; }
        out.push({ src: e.type === 'way' ? 1 : 2, id: e.id, tags, polys });
        n++;
      }
      log(`osm block ${i},${j}: ${n} buildings`);
    }
  }
  return { list: out, skipped };
}

async function osmPlaces() {
  const f = await cached('osm_places.json', async (dest) => {
    const q = `[out:json][timeout:25];node["place"~"^(city|town)$"](${bbox.south},${bbox.west},${bbox.north},${bbox.east});out body;`;
    fs.writeFileSync(dest, await overpass(q, 'osm places'));
  });
  return (JSON.parse(fs.readFileSync(f, 'utf8')).elements ?? [])
    .filter((e) => e.tags?.name && inBox(e.lon, e.lat))
    .map((e) => ({ name: e.tags.name, kind: e.tags.place, lon: +e.lon.toFixed(5), lat: +e.lat.toFixed(5), population: Number(e.tags.population) || null }))
    .sort((a, b) => (b.population ?? 0) - (a.population ?? 0) || a.name.localeCompare(b.name));
}

// ---------------------------------------------------------------- Microsoft footprints

function quadkeys(z) {
  const qk = (lon, lat) => {
    const s = Math.sin((lat * Math.PI) / 180);
    const x = Math.floor(((lon + 180) / 360) * 2 ** z);
    const y = Math.floor((0.5 - Math.log((1 + s) / (1 - s)) / (4 * Math.PI)) * 2 ** z);
    let q = '';
    for (let i = z; i > 0; i--) { const m = 1 << (i - 1); q += ((x & m) ? 1 : 0) + ((y & m) ? 2 : 0); }
    return q;
  };
  const set = new Set();
  for (let lon = bbox.west; lon <= bbox.east + 1e-9; lon += 0.02) for (let lat = bbox.south; lat <= bbox.north + 1e-9; lat += 0.02) set.add(qk(lon, lat));
  for (const [lon, lat] of [[bbox.east, bbox.south], [bbox.east, bbox.north], [bbox.west, bbox.north]]) set.add(qk(lon, lat));
  return set;
}

async function download(url, dest) {
  const res = await fetch(url, { signal: AbortSignal.timeout(1800000) });
  if (!res.ok) throw new Error(`${res.status} ${url}`);
  await pipeline(Readable.fromWeb(res.body), fs.createWriteStream(dest));
}

async function msBuildings() {
  const linksFile = await cached('ms_dataset_links.csv', (dest) => retry(() => download(MS_LINKS, dest), 'ms links'));
  const want = quadkeys(9);
  const rows = fs.readFileSync(linksFile, 'utf8').split('\n').slice(1).map((l) => l.split(','))
    .filter((r) => r[0] === 'Brazil' && want.has(r[1]));
  const out = [];
  const files = [];
  for (const [, qk, url, size] of rows) {
    const f = await cached(`ms_${qk}.csv.gz`, (dest) => { log(`downloading Microsoft quadkey ${qk} (${size})`); return retry(() => download(url, dest), qk); });
    files.push({ quadkey: qk, url, size });
    let lines = 0, kept = 0;
    const rl = readline.createInterface({ input: fs.createReadStream(f).pipe(zlib.createGunzip()), crlfDelay: Infinity });
    for await (const line of rl) {
      lines++;
      // cheap pre-filter on the first coordinate before parsing the whole line
      const k = line.indexOf('[[[');
      if (k < 0) continue;
      const m = line.slice(k + 3, k + 60).match(/^\s*(-?[0-9.]+),\s*(-?[0-9.]+)/);
      if (!m || +m[1] < bbox.west - 0.01 || +m[1] > bbox.east + 0.01 || +m[2] < bbox.south - 0.01 || +m[2] > bbox.north + 0.01) continue;
      const ft = JSON.parse(line);
      const polys = ft.geometry.type === 'Polygon' ? [ft.geometry.coordinates] : ft.geometry.type === 'MultiPolygon' ? ft.geometry.coordinates : [];
      for (const p of polys) {
        const o = p[0];
        let sx = 0, sy = 0;
        for (const [x, y] of o) { sx += x; sy += y; }
        if (!inBox(sx / o.length, sy / o.length)) continue;
        out.push({ src: 0, id: 0, tags: {}, polys: [{ outer: o, holes: p.slice(1) }], msHeight: ft.properties?.height ?? -1, msConf: ft.properties?.confidence ?? -1 });
        kept++;
      }
    }
    log(`Microsoft quadkey ${qk}: ${kept.toLocaleString()} footprints in the window of ${lines.toLocaleString()}`);
  }
  return { list: out, files };
}

// ---------------------------------------------------------------- Google Open Buildings 2.5D heights

async function gobTiles() {
  const corners = [[bbox.west, bbox.south], [bbox.east, bbox.south], [bbox.west, bbox.north], [bbox.east, bbox.north]].map(([a, b]) => utmForward(a, b, UTM_ZONE, true));
  const E0 = Math.min(...corners.map((c) => c[0])), E1 = Math.max(...corners.map((c) => c[0]));
  const N0 = Math.min(...corners.map((c) => c[1])), N1 = Math.max(...corners.map((c) => c[1]));
  const tiles = [];
  for (const name of GOB_MANIFESTS) {
    const f = await cached(`gob_${name}`, (dest) => retry(() => download(`${GOB}/manifests/${name}`, dest), name));
    const m = JSON.parse(fs.readFileSync(f, 'utf8'));
    const prefix = m.uriPrefix.replace('gs://open-buildings-temporal-data/v1', GOB);
    for (const ts of m.tilesets) {
      for (const s of ts.sources) {
        const a = s.affineTransform, d = s.dimensions;
        const x0 = a.translateX, y1 = a.translateY, x1 = x0 + a.scaleX * d.width, y0 = y1 + a.scaleY * d.height;
        if (x1 > E0 && x0 < E1 && y1 > N0 && y0 < N1) tiles.push({ url: prefix + s.uris[0], x0, y0, x1, y1, manifest: name });
      }
    }
  }
  return tiles;
}

/**
 * Fill b.gob (median height, m) for the buildings that need it. Pixels are read at the 2 m overview, one
 * internal 512-pixel COG tile (1,024 m) at a time, so each compressed block is fetched once. Neighbouring
 * S2 cells overlap, but each file holds data (> 0) only inside its own cell, so no pixel is counted twice.
 */
async function googleHeights(need, tiles) {
  const RES = 2;
  const tiffs = new Map();
  const open = (url) => {
    if (!tiffs.has(url)) {
      tiffs.set(url, (async () => {
        const tif = await fromUrl(url, { allowFullFile: false });
        const n = await tif.getImageCount();
        const full = await tif.getImage(0);
        const want = Math.round((full.getWidth() * full.getResolution()[0]) / RES);
        for (let i = 0; i < n; i++) {
          const im = await tif.getImage(i);
          if (im.getWidth() === want) return im;
        }
        throw new Error(`no ${RES} m overview in ${url}`);
      })());
    }
    return tiffs.get(url);
  };
  const BLK = 512;
  const B = BLK * RES;
  const jobs = new Map();
  for (const b of need) {
    const u = b.utm;
    b.acc = { inner: [], all: [] };
    for (const t of tiles) {
      if (u.xb <= t.x0 || u.xa >= t.x1 || u.yb <= t.y0 || u.ya >= t.y1) continue;
      const i0 = Math.floor((Math.max(u.xa, t.x0) - t.x0) / B), i1 = Math.floor((Math.min(u.xb, t.x1 - 1e-6) - t.x0) / B);
      const j0 = Math.floor((t.y1 - Math.min(u.yb, t.y1)) / B), j1 = Math.floor((t.y1 - Math.max(u.ya, t.y0 + 1e-6)) / B);
      for (let i = i0; i <= i1; i++) for (let j = j0; j <= j1; j++) {
        const k = `${t.url}|${i}|${j}`;
        (jobs.get(k) ?? jobs.set(k, { t, i, j, list: [] }).get(k)).list.push(b);
      }
    }
  }
  const list = [...jobs.values()];
  let done = 0, pixels = 0;
  const work = async ({ t, i, j, list: bs }) => {
    const im = await open(t.url);
    const c0 = i * BLK, r0 = j * BLK, c1 = Math.min(c0 + BLK, im.getWidth()), r1 = Math.min(r0 + BLK, im.getHeight());
    const [h] = await retry(() => im.readRasters({ window: [c0, r0, c1, r1], samples: [1] }), `${t.url} ${i},${j}`);
    const w = c1 - c0;
    for (const b of bs) {
      const u = b.utm;
      const ca = Math.max(c0, Math.floor((u.xa - t.x0) / RES)), cb = Math.min(c1 - 1, Math.floor((u.xb - t.x0) / RES));
      const ra = Math.max(r0, Math.floor((t.y1 - u.yb) / RES)), rb = Math.min(r1 - 1, Math.floor((t.y1 - u.ya) / RES));
      for (let r = ra; r <= rb; r++) {
        for (let c = ca; c <= cb; c++) {
          const v = h[(r - r0) * w + (c - c0)];
          if (!(v > 0)) continue;
          footprintPixel(b.acc, u.ring, t.x0 + (c + 0.5) * RES, t.y1 - (r + 0.5) * RES, v, 1);
          pixels++;
        }
      }
    }
    if (++done % 250 === 0 || done === list.length) log(`Google 2.5D: ${done} of ${list.length} COG blocks read`);
  };
  const queue = list.slice();
  await Promise.all(Array.from({ length: 8 }, async () => { while (queue.length) await work(queue.shift()); }));
  for (const b of need) {
    const m = footprintMedian(b.acc);
    if (m !== null && m >= GOB_MIN_M) b.gob = Math.min(m, 100);
    delete b.acc;
  }
  return { blocks: list.length, pixels };
}

/** Google 2.5D against OSM heights (tag) and storeys × STOREY_M: the estimate minus the OSM value */
function googleCheck(list) {
  const stats = (pairs) => {
    if (!pairs.length) return null;
    const n = pairs.length;
    const d = pairs.map(([g, o]) => g - o);
    const mean = (a) => a.reduce((x, y) => x + y, 0) / a.length;
    const mg = mean(pairs.map((p) => p[0])), mo = mean(pairs.map((p) => p[1]));
    let sgo = 0, sgg = 0, soo = 0;
    for (const [g, o] of pairs) { sgo += (g - mg) * (o - mo); sgg += (g - mg) ** 2; soo += (o - mo) ** 2; }
    const r2 = (x) => Math.round(x * 100) / 100;
    return { n, biasM: r2(mean(d)), maeM: r2(mean(d.map(Math.abs))), rmseM: r2(Math.sqrt(mean(d.map((x) => x * x)))),
      r: sgg && soo ? r2(sgo / Math.sqrt(sgg * soo)) : null, medianOsmM: r2([...pairs.map((p) => p[1])].sort((a, b) => a - b)[n >> 1]) };
  };
  return {
    against_height_tag: stats(list.filter((b) => b.hsrc === 2 && b.gob !== undefined).map((b) => [b.gob, b.height])),
    against_storeys_x_3m: stats(list.filter((b) => b.hsrc === 1 && b.gob !== undefined).map((b) => [b.gob, b.height])),
    osmWithoutGoogle: list.filter((b) => b.gob === undefined).length,
  };
}

// ---------------------------------------------------------------- assemble

const osm = noOsm ? { list: [], skipped: {} } : await osmBuildings();
log(`OSM: ${osm.list.length.toLocaleString()} buildings`);
const places = noOsm ? [] : await osmPlaces();
log(`places: ${places.map((p) => p.name).join(', ')}`);
const ms = await msBuildings();
log(`Microsoft: ${ms.list.length.toLocaleString()} footprints in the window`);

/** lon/lat polygons -> local metres, cleaned and oriented; area and centroid */
function prepare(b) {
  const polys = [];
  let area = 0, sx = 0, sy = 0;
  for (const p of b.polys) {
    const outer = cleanRing(p.outer.map(([lon, lat]) => toLocal(lon, lat)));
    if (!outer) continue;
    const a = Math.abs(ringArea(outer));
    const holes = p.holes.map((h) => cleanRing(h.map(([lon, lat]) => toLocal(lon, lat)))).filter(Boolean);
    const net = a - holes.reduce((s, h) => s + Math.abs(ringArea(h)), 0);
    if (net < MIN_AREA_M2) continue;
    polys.push({ outer: orient(outer, false), holes: holes.map((h) => orient(h, true)) });
    let cx = 0, cy = 0;
    for (const [x, y] of outer) { cx += x; cy += y; }
    sx += (cx / outer.length) * net; sy += (cy / outer.length) * net; area += net;
  }
  if (!polys.length) return null;
  return { ...b, poly: polys, area, cx: sx / area, cy: sy / area };
}

const osmList = osm.list.map(prepare).filter(Boolean).filter((b) => inBox(lon0 + b.cx / KX, lat0 + b.cy / KZ));
// spatial index of OSM footprints (100 m cells)
const CELL = 100;
const grid = new Map();
for (const b of osmList) {
  let xa = Infinity, xb = -Infinity, ya = Infinity, yb = -Infinity;
  for (const p of b.poly) for (const [x, y] of p.outer) { xa = Math.min(xa, x); xb = Math.max(xb, x); ya = Math.min(ya, y); yb = Math.max(yb, y); }
  for (let i = Math.floor(xa / CELL); i <= Math.floor(xb / CELL); i++) for (let j = Math.floor(ya / CELL); j <= Math.floor(yb / CELL); j++) {
    const k = `${i},${j}`;
    (grid.get(k) ?? grid.set(k, []).get(k)).push(b);
  }
}
let dropped = 0;
const msList = [];
for (const raw of ms.list) {
  const b = prepare(raw);
  if (!b) continue;
  const outer = b.poly[0].outer;
  let xa = Infinity, xb = -Infinity, ya = Infinity, yb = -Infinity;
  for (const [x, y] of outer) { xa = Math.min(xa, x); xb = Math.max(xb, x); ya = Math.min(ya, y); yb = Math.max(yb, y); }
  let clash = false;
  for (let i = Math.floor(xa / CELL); i <= Math.floor(xb / CELL) && !clash; i++) for (let j = Math.floor(ya / CELL); j <= Math.floor(yb / CELL) && !clash; j++) {
    for (const o of grid.get(`${i},${j}`) ?? []) {
      if (o.poly.some((p) => pointInRing(b.cx, b.cy, p.outer)) || pointInRing(o.cx, o.cy, outer)) { clash = true; break; }
    }
  }
  if (clash) { dropped++; continue; }
  msList.push(b);
}
log(`Microsoft footprints overlapping OSM buildings dropped: ${dropped.toLocaleString()}; kept ${msList.length.toLocaleString()}`);

// heights from OSM tags
const all = osmList.concat(msList);
for (const b of all) {
  b.cls = classOf(b.tags);
  b.roof = roofOf(b.tags);
  const lv = parseLevels(b.tags['building:levels']);
  b.levels = lv ? Math.min(255, Math.round(lv)) : 0;
  const h = parseHeight(b.tags.height);
  if (h !== null) { b.height = h; b.hsrc = 2; } else if (lv !== null) { b.height = lv * STOREY_M; b.hsrc = 1; }
}
// Google 2.5D for the rest; also read for the OSM buildings that have a height or storey count, to check
// the estimate against them (their own heights are kept)
const need = all.filter((b) => b.hsrc === undefined);
const tagged = all.filter((b) => b.hsrc === 1 || b.hsrc === 2);
for (const b of need.concat(tagged)) {
  const ring = b.poly[0].outer.map(([x, y]) => utmForward(lon0 + x / KX, lat0 + y / KZ, UTM_ZONE, true));
  let xa = Infinity, xb = -Infinity, ya = Infinity, yb = -Infinity, sx = 0, sy = 0;
  for (const [x, y] of ring) { xa = Math.min(xa, x); xb = Math.max(xb, x); ya = Math.min(ya, y); yb = Math.max(yb, y); sx += x; sy += y; }
  b.utm = { ring, xa, xb, ya, yb, cx: sx / ring.length, cy: sy / ring.length };
}
const gTiles = await gobTiles();
log(`Google 2.5D: ${gTiles.length} tiles cover the window; heights wanted for ${need.length.toLocaleString()} buildings`);
const gStats = await googleHeights(need.concat(tagged), gTiles);
const check = googleCheck(tagged);
for (const b of tagged) { delete b.utm; delete b.gob; }
for (const b of need) {
  if (b.gob !== undefined) { b.height = b.gob; b.hsrc = 3; } else if (b.msHeight > 0) { b.height = b.msHeight; b.hsrc = 4; } else { b.height = PLACEHOLDER_M; b.hsrc = 0; }
  delete b.utm;
}

// ---------------------------------------------------------------- tiles
fs.rmSync(outDir, { recursive: true, force: true });
fs.mkdirSync(outDir, { recursive: true });
const tiles = new Map();
for (const b of all) {
  const k = `${Math.floor(b.cx / TILE_M)}_${Math.floor(b.cy / TILE_M)}`;
  (tiles.get(k) ?? tiles.set(k, []).get(k)).push(b);
}
const index = [];
let bytes = 0, rawBytes = 0, outOfRange = 0;
const counts = { footprint: { osm: 0, microsoft: 0 }, height: { 0: 0, 1: 0, 2: 0, 3: 0, 4: 0 }, cls: {} };
const hist = [0, 0, 0, 0, 0, 0]; // < 4, 4-8, 8-15, 15-30, 30-60, >= 60 m
for (const [k, list] of [...tiles].sort()) {
  const [tx, ty] = k.split('_').map(Number);
  const cx = (tx + 0.5) * TILE_M, cy = (ty + 0.5) * TILE_M;
  const lim = 32767 * QUANTUM_M;
  const ok = list.filter((b) => b.poly.every((p) => p.outer.every(([x, y]) => Math.abs(x - cx) < lim && Math.abs(y - cy) < lim)));
  outOfRange += list.length - ok.length;
  const recs = ok.map((b) => ({
    height: b.height, hsrc: b.hsrc, cls: b.cls, levels: b.levels, roof: b.roof, src: b.src, id: b.id,
    name: b.tags.name, rings: b.poly.flatMap((p) => [{ pts: p.outer, hole: false }, ...p.holes.map((h) => ({ pts: h, hole: true }))]),
  }));
  for (const b of ok) {
    counts.footprint[b.src ? 'osm' : 'microsoft']++;
    counts.height[b.hsrc]++;
    counts.cls[b.cls] = (counts.cls[b.cls] ?? 0) + 1;
    hist[b.height < 4 ? 0 : b.height < 8 ? 1 : b.height < 15 ? 2 : b.height < 30 ? 3 : b.height < 60 ? 4 : 5]++;
  }
  const raw = encodeBuildingTile(recs, cx, cy, QUANTUM_M);
  const gz = zlib.gzipSync(raw, { level: 9 });
  fs.writeFileSync(path.join(outDir, `${tx}_${ty}.bin`), gz);
  rawBytes += raw.length;
  bytes += gz.length;
  index.push({ x: tx, y: ty, n: recs.length, bytes: gz.length });
}
const total = counts.footprint.osm + counts.footprint.microsoft;
fs.writeFileSync(path.join(outDir, 'index.json'), JSON.stringify({
  format: 'UBT1', tileSize: TILE_M, url: 'buildings/{x}_{y}.bin', frame: { lon0, lat0, KX, KZ }, bbox, count: total,
  storeyM: STOREY_M, placeholderM: PLACEHOLDER_M, places, tiles: index,
}));
const checkText = (c) => [['height tags', c.against_height_tag], [`storeys × ${STOREY_M} m`, c.against_storeys_x_3m]]
  .filter(([, v]) => v).map(([k, v]) => `${k} (n ${v.n}): bias ${v.biasM >= 0 ? '+' : ''}${v.biasM} m, MAE ${v.maeM} m, RMSE ${v.rmseM} m, r ${v.r}`).join('; ') || 'no OSM heights to compare';
const pct = (n) => `${((100 * n) / Math.max(total, 1)).toFixed(1)} %`;
fs.writeFileSync(path.join(dataDir, 'buildings.json'), JSON.stringify({
  title: 'Building footprints and heights for 3D display',
  meaning: 'Context for the 3D view only. No number on screen depends on the buildings.',
  footprints: [
    { source: 'OpenStreetMap contributors via the Overpass API', licence: 'ODbL 1.0', attribution: '© OpenStreetMap contributors', count: counts.footprint.osm },
    { source: 'Microsoft Global ML Building Footprints', licence: 'ODbL 1.0', url: MS_LINKS, files: ms.files, count: counts.footprint.microsoft,
      rule: 'kept only where no OSM building overlaps (its centroid in an OSM building, or an OSM building centroid in it)' },
  ],
  heights: {
    order: ['OSM height tag', `OSM building:levels × ${STOREY_M} m`, 'Google Open Buildings 2.5D Temporal 2023: median of the 2 m pixels in the footprint eroded by 1 m',
      'Microsoft footprint height estimate', `placeholder ${PLACEHOLDER_M} m`],
    counts: {
      osm_height_tag: counts.height[2], osm_levels_x_storey: counts.height[1], google_25d_2023: counts.height[3],
      microsoft_estimate: counts.height[4], placeholder: counts.height[0],
    },
    google: { source: 'Google Open Buildings 2.5D Temporal v1, 2023 epoch (imagery centred on 30 Jun 2023)', licence: 'CC BY 4.0',
      attribution: 'Google Open Buildings 2.5D Temporal (CC BY 4.0)', manifests: GOB_MANIFESTS.map((m) => `${GOB}/manifests/${m}`),
      tiles: gTiles.length, cogBlocksRead: gStats.blocks, band: 'building_height (sample 2 of 3)', readAt: '2 m overview of the 0.5 m delivery; effective resolution 4 m' },
    checkAgainstOsm: check,
    histogramM: { '<4': hist[0], '4-8': hist[1], '8-15': hist[2], '15-30': hist[3], '30-60': hist[4], '>=60': hist[5] },
  },
  classCounts: counts.cls,
  reliabilityNotes: [
    `${pct(counts.height[0])} of buildings have no height information; they are drawn ${PLACEHOLDER_M} m tall, a display placeholder.`,
    `${pct(counts.height[3])} use Google 2.5D, a model estimate from Sentinel-2 (provider MAE 1.5 m was reported for North America, Europe and Japan only; in Sri Lanka the Kelani WebTwin found bias +2.3 m, MAE 5.1 m against OSM storeys). Here, against OSM: ${checkText(check)}.`,
    `Storey height ${STOREY_M} m is an assumption.`,
    'Microsoft footprints are machine-detected from imagery of varying date; some are missing, merged or false. OSM completeness varies by town.',
    'Base elevation comes from the terrain the viewer draws (Copernicus GLO-30, a surface model at 30 m), so bases are approximate; walls extend below it.',
    'Roof form, facade, paint and roof material are drawn procedurally and are not data.',
  ],
  osmSkipped: noOsm, tiles: index.length, tileSizeM: TILE_M, bytesGzip: bytes, bytesRaw: rawBytes, droppedOutOfTileRange: outOfRange,
  built: new Date().toISOString(),
}, null, 2));
log(`Google 2.5D against OSM: ${checkText(check)}`);
log(`buildings: ${total.toLocaleString()} in ${index.length} tiles, ${(bytes / 1e6).toFixed(1)} MB gzip (${(rawBytes / 1e6).toFixed(1)} MB raw);`
  + ` footprints OSM ${counts.footprint.osm.toLocaleString()} / Microsoft ${counts.footprint.microsoft.toLocaleString()};`
  + ` heights tag ${counts.height[2]}, levels ${counts.height[1]}, Google ${counts.height[3]}, Microsoft ${counts.height[4]}, placeholder ${counts.height[0]};`
  + ` peak memory ${(process.resourceUsage().maxRSS / 1024 / 1024).toFixed(1)} GB`);
