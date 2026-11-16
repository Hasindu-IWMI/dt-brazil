// Full-resolution terrain for the realistic display: Copernicus DEM GLO-30 at its native
// 1 arc-second (about 30 m) over the same window as the delineation DEM.
//
// It is a SURFACE model (canopy and buildings included, EGM2008 metres) and is used for
// DISPLAY ONLY: catchments are still delineated from data/raw/dem/delineation.* (3 arc-sec).
//
// Encoding (web/public/data/terrain_hi.bin): elevation in decimetres as integers, each row
// stored as its first value followed by differences along the row (int16, little-endian),
// then gzip. Missing cells are stored as 0 dm and listed in the sidecar. The viewer decodes it.
//
// Usage: node tools/build_display_terrain.mjs
import fs from 'node:fs';
import path from 'node:path';
import zlib from 'node:zlib';
import { fileURLToPath } from 'node:url';
import { readCopDem } from './lib/raster.mjs';

const here = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(here, '..', '..');
const outDir = path.resolve(here, '..', 'public', 'data');
const window = JSON.parse(fs.readFileSync(path.join(root, 'data', 'raw', 'dem', 'delineation.json'), 'utf8')).bbox;
const STEP = 1;

const { data, cols, rows, urls } = await readCopDem(window, STEP);
const enc = new Int16Array(cols * rows);
let missing = 0;
let lo = Infinity;
let hi = -Infinity;
for (let r = 0; r < rows; r++) {
  let prev = 0;
  for (let c = 0; c < cols; c++) {
    const v = data[r * cols + c];
    let q = 0;
    if (Number.isFinite(v)) {
      q = Math.round(v * 10);
      lo = Math.min(lo, v);
      hi = Math.max(hi, v);
    } else missing++;
    enc[r * cols + c] = c === 0 ? q : q - prev;
    prev = q;
  }
}
const gz = zlib.gzipSync(Buffer.from(enc.buffer), { level: 9 });
fs.writeFileSync(path.join(outDir, 'terrain_hi.bin'), gz);
fs.writeFileSync(path.join(outDir, 'terrain_hi.json'), JSON.stringify({
  source: 'Copernicus DEM GLO-30 (ESA), public AWS bucket copernicus-dem-30m',
  sourceTiles: urls,
  kind: 'digital SURFACE model (includes canopy and buildings)', crs: 'EPSG:4326', verticalDatum: 'EGM2008', units: 'm',
  bbox: window, width: cols, height: rows, sampleStepArcsec: STEP, rowOrder: 'north to south',
  encoding: 'gzip of int16 little-endian; decimetres; per row: first value, then differences along the row',
  missingCells: missing, minElevation: lo, maxElevation: hi,
  use: 'display only (catchments are delineated from the 3 arc-second window)',
  licence: 'Copernicus DEM: free and open; "produced using Copernicus WorldDEM-30 (c) DLR e.V. 2010-2014 and (c) Airbus Defence and Space GmbH 2014-2018 provided under COPERNICUS by the European Union and ESA; all rights reserved"',
  retrieved: new Date().toISOString(),
}, null, 2));
console.log('terrain_hi', cols, 'x', rows, 'missing', missing, 'bytes', gz.length);
