// Small raster helpers for the scene-data tools (no native dependencies).
import zlib from 'node:zlib';
import { fromUrl } from 'geotiff';

// ---- WGS84 -> UTM (Snyder 1987, eq. 8-9 to 8-13); accurate to well under 1 m inside a zone.
const A = 6378137;
const F = 1 / 298.257223563;
const E2 = F * (2 - F);
const EP2 = E2 / (1 - E2);
const K0 = 0.9996;

/** [easting, northing] in metres for a UTM zone; south=true adds the 10 000 km false northing. */
export function utmForward(lon, lat, zone, south) {
  const phi = (lat * Math.PI) / 180;
  const lam0 = (((zone - 1) * 6 - 180 + 3) * Math.PI) / 180;
  const s = Math.sin(phi);
  const c = Math.cos(phi);
  const t = Math.tan(phi);
  const N = A / Math.sqrt(1 - E2 * s * s);
  const T = t * t;
  const C = EP2 * c * c;
  const Aa = c * ((lon * Math.PI) / 180 - lam0);
  const e4 = E2 * E2;
  const e6 = e4 * E2;
  const M = A * ((1 - E2 / 4 - (3 * e4) / 64 - (5 * e6) / 256) * phi
    - ((3 * E2) / 8 + (3 * e4) / 32 + (45 * e6) / 1024) * Math.sin(2 * phi)
    + ((15 * e4) / 256 + (45 * e6) / 1024) * Math.sin(4 * phi)
    - ((35 * e6) / 3072) * Math.sin(6 * phi));
  const x = K0 * N * (Aa + ((1 - T + C) * Aa ** 3) / 6 + ((5 - 18 * T + T * T + 72 * C - 58 * EP2) * Aa ** 5) / 120) + 500000;
  let y = K0 * (M + N * t * ((Aa * Aa) / 2 + ((5 - T + 9 * C + 4 * C * C) * Aa ** 4) / 24
    + ((61 - 58 * T + T * T + 600 * C - 330 * EP2) * Aa ** 6) / 720));
  if (south) y += 10000000;
  return [x, y];
}

// ---- minimal PNG writer (8-bit grayscale or RGB, filter 0), enough for class maps and normals.
const CRC = new Int32Array(256).map((_, n) => {
  let c = n;
  for (let k = 0; k < 8; k++) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1;
  return c;
});
function crc32(buf) {
  let c = -1;
  for (let i = 0; i < buf.length; i++) c = CRC[(c ^ buf[i]) & 0xff] ^ (c >>> 8);
  return (c ^ -1) >>> 0;
}
function chunk(type, data) {
  const out = Buffer.alloc(12 + data.length);
  out.writeUInt32BE(data.length, 0);
  out.write(type, 4, 'ascii');
  data.copy(out, 8);
  out.writeUInt32BE(crc32(out.subarray(4, 8 + data.length)), 8 + data.length);
  return out;
}
export function encodePng(pixels, width, height, channels) {
  const stride = width * channels;
  const raw = Buffer.alloc((stride + 1) * height);
  for (let y = 0; y < height; y++) {
    raw[y * (stride + 1)] = 0;
    Buffer.from(pixels.buffer, pixels.byteOffset + y * stride, stride).copy(raw, y * (stride + 1) + 1);
  }
  const ihdr = Buffer.alloc(13);
  ihdr.writeUInt32BE(width, 0);
  ihdr.writeUInt32BE(height, 4);
  ihdr[8] = 8;
  ihdr[9] = channels === 1 ? 0 : 2;
  return Buffer.concat([Buffer.from([137, 80, 78, 71, 13, 10, 26, 10]), chunk('IHDR', ihdr),
    chunk('IDAT', zlib.deflateSync(raw, { level: 9 })), chunk('IEND', Buffer.alloc(0))]);
}

/** Retry an async read: public buckets and STAC services drop connections now and then. */
export async function retry(fn, label, tries = 4) {
  for (let k = 1; ; k++) {
    try {
      return await fn();
    } catch (e) {
      if (k >= tries) throw e;
      console.log('retry', k, label, e?.message ?? e);
      await new Promise((r) => setTimeout(r, Math.min(5000 * k, 30000)));
    }
  }
}

// ---- Copernicus DEM GLO-30 window (public AWS bucket, HTTP range reads).
const copTile = (latSW, lonSW) => {
  const ns = latSW < 0 ? 'S' : 'N';
  const ew = lonSW < 0 ? 'W' : 'E';
  const name = `Copernicus_DSM_COG_10_${ns}${String(Math.abs(latSW)).padStart(2, '0')}_00_${ew}${String(Math.abs(lonSW)).padStart(3, '0')}_00_DEM`;
  return `https://copernicus-dem-30m.s3.amazonaws.com/${name}/${name}.tif`;
};

/** Float32 elevations (m, EGM2008), north-to-south rows, sampled every `step` arc-seconds. */
export async function readCopDem({ west, south, east, north }, step, log = console.log) {
  const cols = Math.round(((east - west) * 3600) / step);
  const rows = Math.round(((north - south) * 3600) / step);
  const data = new Float32Array(cols * rows).fill(NaN);
  const urls = [];
  for (let lat = Math.floor(south); lat < north; lat++) {
    for (let lon = Math.floor(west); lon < east; lon++) {
      const w = Math.max(west, lon);
      const e = Math.min(east, lon + 1);
      const s = Math.max(south, lat);
      const n = Math.min(north, lat + 1);
      const url = copTile(lat, lon);
      urls.push(url);
      const pw = Math.round(((e - w) * 3600) / step);
      const ph = Math.round(((n - s) * 3600) / step);
      const band = await retry(async () => {
        const img = await (await fromUrl(url)).getImage();
        const [ox, oy] = img.getOrigin();
        const [rx, ry] = img.getResolution();
        const [b] = await img.readRasters({
          window: [Math.round((w - ox) / rx), Math.round((n - oy) / ry), Math.round((e - ox) / rx), Math.round((s - oy) / ry)],
          width: pw, height: ph, resampleMethod: 'bilinear',
        });
        return b;
      }, url);
      const c0 = Math.round(((w - west) * 3600) / step);
      const r0 = Math.round(((north - n) * 3600) / step);
      for (let r = 0; r < ph; r++) data.set(band.subarray(r * pw, (r + 1) * pw), (r0 + r) * cols + c0);
      log('dem tile', lat, lon, pw, 'x', ph);
    }
  }
  return { data, cols, rows, urls };
}
