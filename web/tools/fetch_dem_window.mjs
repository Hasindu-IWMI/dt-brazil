// Read a window of Copernicus DEM GLO-30 by HTTP range request and save it as
// raw float32 (north-to-south rows) with a JSON sidecar. Used for catchment
// delineation. The DEM is a surface model in EGM2008 metres.
//
// Usage: node tools/fetch_dem_window.mjs <west> <south> <east> <north> <step_arcsec> <out_basename>
import { fromUrl } from 'geotiff';
import fs from 'node:fs';
import path from 'node:path';

const [west, south, east, north, step] = process.argv.slice(2, 7).map(Number);
const out = process.argv[7];
fs.mkdirSync(path.dirname(out), { recursive: true });

const tileUrl = (latSW, lonSW) => {
  const ns = latSW < 0 ? 'S' : 'N';
  const ew = lonSW < 0 ? 'W' : 'E';
  const name = `Copernicus_DSM_COG_10_${ns}${String(Math.abs(latSW)).padStart(2, '0')}_00_${ew}${String(Math.abs(lonSW)).padStart(3, '0')}_00_DEM`;
  return `https://copernicus-dem-30m.s3.amazonaws.com/${name}/${name}.tif`;
};

const cols = Math.round(((east - west) * 3600) / step);
const rows = Math.round(((north - south) * 3600) / step);
const data = new Float32Array(cols * rows).fill(NaN);

for (let lat = Math.floor(south); lat < north; lat++) {
  for (let lon = Math.floor(west); lon < east; lon++) {
    const w = Math.max(west, lon);
    const e = Math.min(east, lon + 1);
    const s = Math.max(south, lat);
    const n = Math.min(north, lat + 1);
    const tiff = await fromUrl(tileUrl(lat, lon));
    const img = await tiff.getImage();
    const [ox, oy] = img.getOrigin();
    const [rx, ry] = img.getResolution();
    const x0 = Math.round((w - ox) / rx);
    const x1 = Math.round((e - ox) / rx);
    const y0 = Math.round((n - oy) / ry);
    const y1 = Math.round((s - oy) / ry);
    const pw = Math.round(((e - w) * 3600) / step);
    const ph = Math.round(((n - s) * 3600) / step);
    const [band] = await img.readRasters({ window: [x0, y0, x1, y1], width: pw, height: ph, resampleMethod: 'bilinear' });
    const c0 = Math.round(((w - west) * 3600) / step);
    const r0 = Math.round(((north - n) * 3600) / step);
    for (let r = 0; r < ph; r++) data.set(band.subarray(r * pw, (r + 1) * pw), (r0 + r) * cols + c0);
    console.log('tile', lat, lon, pw, 'x', ph);
  }
}
fs.writeFileSync(out + '.f32', Buffer.from(data.buffer));
fs.writeFileSync(out + '.json', JSON.stringify({
  source: 'Copernicus DEM GLO-30 (ESA), public AWS bucket copernicus-dem-30m',
  kind: 'digital SURFACE model', crs: 'EPSG:4326', verticalDatum: 'EGM2008', units: 'm',
  bbox: { west, south, east, north }, width: cols, height: rows, sampleStepArcsec: step,
  rowOrder: 'north to south', dtype: 'float32 little-endian', retrieved: new Date().toISOString(),
}, null, 2));
console.log('saved', cols, 'x', rows);
