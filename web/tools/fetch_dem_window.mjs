// Read a window of Copernicus DEM GLO-30 by HTTP range request and save it as
// raw float32 (north-to-south rows) with a JSON sidecar. Used for catchment
// delineation. The DEM is a surface model in EGM2008 metres.
//
// Usage: node tools/fetch_dem_window.mjs <west> <south> <east> <north> <step_arcsec> <out_basename>
import fs from 'node:fs';
import path from 'node:path';
import { readCopDem } from './lib/raster.mjs';

const [west, south, east, north, step] = process.argv.slice(2, 7).map(Number);
const out = process.argv[7];
fs.mkdirSync(path.dirname(out), { recursive: true });

const { data, cols, rows } = await readCopDem({ west, south, east, north }, step);
fs.writeFileSync(out + '.f32', Buffer.from(data.buffer));
fs.writeFileSync(out + '.json', JSON.stringify({
  source: 'Copernicus DEM GLO-30 (ESA), public AWS bucket copernicus-dem-30m',
  kind: 'digital SURFACE model', crs: 'EPSG:4326', verticalDatum: 'EGM2008', units: 'm',
  bbox: { west, south, east, north }, width: cols, height: rows, sampleStepArcsec: step,
  rowOrder: 'north to south', dtype: 'float32 little-endian', retrieved: new Date().toISOString(),
}, null, 2));
console.log('saved', cols, 'x', rows);
