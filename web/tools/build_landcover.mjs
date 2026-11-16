// Land cover for the viewer: ESA WorldCover 10 m 2021 v200 (CC BY 4.0), read from the public COG
// by HTTP range requests and resampled (nearest) onto the same grid as imagery.jpg.
//
// Output web/public/data/landcover.png: 8-bit grayscale, each pixel the WorldCover class code
// (10 tree cover, 20 shrubland, 30 grassland, 40 cropland, 50 built-up, 60 bare/sparse, 70 snow,
// 80 permanent water, 90 herbaceous wetland, 95 mangroves, 100 moss/lichen; 0 = no data).
// The viewer uses it for an analytical land-cover layer and for display material cues (water
// sheen, forest roughness). WorldCover describes 2021; it does not change with the replay date.
//
// Usage: node tools/build_landcover.mjs
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { fromUrl } from 'geotiff';
import { encodePng, retry } from './lib/raster.mjs';

const here = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(here, '..', '..');
const outDir = path.resolve(here, '..', 'public', 'data');
const bbox = JSON.parse(fs.readFileSync(path.join(root, 'data', 'raw', 'dem', 'delineation.json'), 'utf8')).bbox;
const OUT_W = 4096; // same grid as build_imagery.mjs
const OUT_H = Math.round((OUT_W * (bbox.north - bbox.south)) / (bbox.east - bbox.west));
const CLASSES = { 10: 'Tree cover', 20: 'Shrubland', 30: 'Grassland', 40: 'Cropland', 50: 'Built-up', 60: 'Bare / sparse vegetation',
  70: 'Snow and ice', 80: 'Permanent water bodies', 90: 'Herbaceous wetland', 95: 'Mangroves', 100: 'Moss and lichen' };

const latSW = Math.floor(bbox.south / 3) * 3;
const lonSW = Math.floor(bbox.west / 3) * 3;
if (bbox.north > latSW + 3 || bbox.east > lonSW + 3) throw new Error('window spans more than one WorldCover tile; extend this tool');
const tile = `${latSW < 0 ? 'S' : 'N'}${String(Math.abs(latSW)).padStart(2, '0')}${lonSW < 0 ? 'W' : 'E'}${String(Math.abs(lonSW)).padStart(3, '0')}`;
const url = `https://esa-worldcover.s3.eu-central-1.amazonaws.com/v200/2021/map/ESA_WorldCover_10m_2021_v200_${tile}_Map.tif`;

const band = await retry(async () => {
  const img = await (await fromUrl(url)).getImage();
  const [ox, oy] = img.getOrigin();
  const [rx, ry] = img.getResolution();
  const win = [Math.round((bbox.west - ox) / rx), Math.round((bbox.north - oy) / ry), Math.round((bbox.east - ox) / rx), Math.round((bbox.south - oy) / ry)];
  const [b] = await img.readRasters({ window: win, width: OUT_W, height: OUT_H, resampleMethod: 'nearest' });
  return b;
}, url);

const counts = {};
for (const v of band) counts[v] = (counts[v] ?? 0) + 1;
fs.writeFileSync(path.join(outDir, 'landcover.png'), encodePng(Uint8Array.from(band), OUT_W, OUT_H, 1));
fs.writeFileSync(path.join(outDir, 'landcover.json'), JSON.stringify({
  source: 'ESA WorldCover 10 m 2021 v200', url, licence: 'CC BY 4.0',
  attribution: '© ESA WorldCover project 2021 / Contains modified Copernicus Sentinel data (2021) processed by ESA WorldCover consortium',
  meaning: 'Land cover in 2021. It does not change with the replay date.',
  bbox, width: OUT_W, height: OUT_H, resampling: 'nearest', classes: CLASSES,
  shareOfWindowPct: Object.fromEntries(Object.entries(counts).sort((a, b) => b[1] - a[1]).map(([k, n]) => [k, +((100 * n) / band.length).toFixed(2)])),
  built: new Date().toISOString(),
}, null, 2));
console.log('landcover', OUT_W, 'x', OUT_H, Object.entries(counts).map(([k, n]) => `${k}:${((100 * n) / band.length).toFixed(1)}%`).join(' '));
