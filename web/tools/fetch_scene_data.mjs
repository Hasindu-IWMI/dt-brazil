// Fetch display data for the 3D scene: a terrain window and mapped water outlines.
//
// Terrain: Copernicus DEM GLO-30 (ESA). It is a SURFACE model (includes canopy
// and buildings), heights in metres above EGM2008. It is used for display and
// for catchment delineation, not for any hydraulic calculation.
//
// Water outlines and rivers: OpenStreetMap via the Overpass API (ODbL).
// These are mapped outlines, not observed water extents for any date.
//
// Usage: node tools/fetch_scene_data.mjs
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const outDir = path.resolve(here, '..', 'public', 'data');
fs.mkdirSync(outDir, { recursive: true });

// The scene uses the same DEM window as the catchment delineation
// (data/raw/dem/delineation.*, fetched by tools/fetch_dem_window.mjs).
const demBase = path.resolve(here, '..', '..', 'data', 'raw', 'dem', 'delineation');
const demMeta = JSON.parse(fs.readFileSync(demBase + '.json', 'utf8'));
const BBOX = demMeta.bbox;

async function terrain() {
  const buf = fs.readFileSync(demBase + '.f32');
  const data = new Float32Array(buf.buffer, buf.byteOffset, buf.byteLength / 4);
  let min = Infinity;
  let max = -Infinity;
  for (const v of data) { if (v < min) min = v; if (v > max) max = v; }
  fs.writeFileSync(path.join(outDir, 'terrain.f32'), buf);
  const meta = { ...demMeta, minElevation: min, maxElevation: max, use: 'display and catchment delineation' };
  fs.writeFileSync(path.join(outDir, 'terrain.json'), JSON.stringify(meta, null, 2));
  console.log('terrain', meta.width, 'x', meta.height, 'min', min.toFixed(1), 'max', max.toFixed(1));
}

async function overpass(query) {
  const res = await fetch('https://overpass-api.de/api/interpreter', {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded', 'User-Agent': 'upper-atibaia-pipeline/0.1' },
    body: 'data=' + encodeURIComponent(query),
  });
  if (!res.ok) throw new Error('Overpass ' + res.status);
  return res.json();
}

async function vectors() {
  const b = `${BBOX.south},${BBOX.west},${BBOX.north},${BBOX.east}`;
  const q = `[out:json][timeout:120];
(
  way["natural"="water"]["water"="reservoir"](${b});
  relation["natural"="water"]["water"="reservoir"](${b});
  way["waterway"="river"](${b});
);
out geom;`;
  const j = await overpass(q);
  const rivers = [];
  const waters = [];
  const ring = (g) => g.map((p) => [p.lon, p.lat]);
  for (const e of j.elements) {
    const name = e.tags?.name ?? '';
    if (e.type === 'way' && e.tags?.waterway === 'river') {
      rivers.push({ name, line: ring(e.geometry) });
    } else if (e.type === 'way' && e.geometry) {
      waters.push({ name, id: 'way/' + e.id, rings: [ring(e.geometry)] });
    } else if (e.type === 'relation') {
      // stitch outer member ways into rings
      const segs = e.members.filter((m) => m.role === 'outer' && m.geometry).map((m) => ring(m.geometry));
      const rings = [];
      while (segs.length) {
        let cur = segs.shift();
        let grew = true;
        while (grew && (cur[0][0] !== cur.at(-1)[0] || cur[0][1] !== cur.at(-1)[1])) {
          grew = false;
          for (let i = 0; i < segs.length; i++) {
            const s = segs[i];
            const end = cur.at(-1);
            if (s[0][0] === end[0] && s[0][1] === end[1]) { cur = cur.concat(s.slice(1)); segs.splice(i, 1); grew = true; break; }
            if (s.at(-1)[0] === end[0] && s.at(-1)[1] === end[1]) { cur = cur.concat(s.slice().reverse().slice(1)); segs.splice(i, 1); grew = true; break; }
          }
        }
        rings.push(cur);
      }
      waters.push({ name, id: 'relation/' + e.id, rings });
    }
  }
  const out = {
    source: 'OpenStreetMap contributors via Overpass API', licence: 'ODbL 1.0',
    note: 'Mapped outlines; not observed water extent for any date.',
    retrieved: new Date().toISOString(), bbox: BBOX, rivers, waters,
  };
  fs.writeFileSync(path.join(outDir, 'vectors.json'), JSON.stringify(out));
  console.log('rivers', rivers.length, 'water bodies', waters.length);
  for (const w of waters) console.log('  ', w.id, w.name || '(unnamed)', w.rings.map((r) => r.length).join('+'));
}

await terrain();
await vectors();
