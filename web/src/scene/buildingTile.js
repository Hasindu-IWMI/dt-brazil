// Building tiles (web/public/data/buildings/{x}_{y}.bin, written by web/tools/build_buildings.mjs).
// Pure functions, shared by the build tool, the viewer, its worker and the tests.
//
// A tile holds the buildings whose centroid falls in one 1 km square of the viewer's local frame
// (x east, y north, metres from the window centre; the same equirectangular frame as main.js).
// The file is gzip of the 'UBT1' layout below (little-endian, every section padded to 4 bytes):
//   header (32 bytes): magic 'UBT1', nB, nR, nV (u32), cx, cy (f32, tile centre), quantum (f32, m), reserved
//   height u16[nB]  centimetres (the display height of the highest point; see hsrc for where it comes from)
//   hsrc u8[nB] | cls u8[nB] | levels u8[nB] | roof u8[nB] | src u8[nB]
//   id u32[nB]      OpenStreetMap way or relation id (0 for Microsoft footprints)
//   ringStart u32[nR+1] | ringBuilding u32[nR] | ringHole u8[nR]
//   xy i16[nV*2]    vertex offsets from the tile centre, in quantum units (outer rings counter-clockwise)
//   names           u32 byte length, then UTF-8 JSON {building index: OSM name}
export const MAGIC = 'UBT1';

/** Height sources, in order of preference (see build_buildings.mjs). */
export const HEIGHT_SOURCE = {
  0: 'no height data: drawn at a placeholder height',
  1: 'OpenStreetMap building:levels × storey height',
  2: 'OpenStreetMap height tag',
  3: 'Google Open Buildings 2.5D 2023 (model estimate, median in the footprint)',
  4: 'Microsoft ML building height (model estimate)',
};
export const FOOTPRINT_SOURCE = { 0: 'Microsoft ML footprint', 1: 'OpenStreetMap way', 2: 'OpenStreetMap relation' };
/** OSM building=* values grouped for the facade and roof generator (display only). */
export const CLASS_NAME = {
  0: 'untyped', 1: 'house', 2: 'apartments / hotel', 3: 'commercial', 4: 'industrial / farm', 5: 'religious',
  6: 'school / hospital / public', 7: 'roof only', 8: 'tank / silo', 9: 'under construction',
};

const pad = (n, a) => n + ((a - (n % a)) % a);

/** Decode a UBT1 tile (an ArrayBuffer that is NOT gzip any more). */
export function decodeBuildingTile(buf) {
  const dv = new DataView(buf);
  const magic = String.fromCharCode(dv.getUint8(0), dv.getUint8(1), dv.getUint8(2), dv.getUint8(3));
  if (magic !== MAGIC) throw new Error(`not a building tile (${magic})`);
  const n = dv.getUint32(4, true), nR = dv.getUint32(8, true), nV = dv.getUint32(12, true);
  const cx = dv.getFloat32(16, true), cy = dv.getFloat32(20, true), q = dv.getFloat32(24, true);
  let o = 32;
  const height = new Float32Array(n);
  const hcm = new Uint16Array(buf, o, n);
  for (let i = 0; i < n; i++) height[i] = hcm[i] / 100;
  o = pad(o + 2 * n, 4);
  const u8 = (k) => new Uint8Array(buf, o + k * n, n);
  const hsrc = u8(0), cls = u8(1), levels = u8(2), roof = u8(3), src = u8(4);
  o = pad(o + 5 * n, 4);
  const id = new Uint32Array(buf, o, n); o += 4 * n;
  const ringStart = new Uint32Array(buf, o, nR + 1); o += 4 * (nR + 1);
  const ringBuilding = new Uint32Array(buf, o, nR); o += 4 * nR;
  const ringHole = new Uint8Array(buf, o, nR); o = pad(o + nR, 4);
  const qi = new Int16Array(buf, o, nV * 2); o += 4 * nV;
  const xy = new Float32Array(nV * 2);
  for (let i = 0; i < qi.length; i++) xy[i] = qi[i] * q;
  let names = {};
  if (o + 4 <= buf.byteLength) {
    const len = dv.getUint32(o, true);
    if (len) names = JSON.parse(new TextDecoder().decode(new Uint8Array(buf, o + 4, len)));
  }
  return { n, nR, nV, cx, cy, height, hsrc, cls, levels, roof, src, id, ringStart, ringBuilding, ringHole, xy, names };
}

/** gzip-aware fetch body -> ArrayBuffer (a dev server may or may not have decoded it already). */
export async function gunzipIfNeeded(buf) {
  const b = new Uint8Array(buf);
  if (b[0] !== 0x1f || b[1] !== 0x8b) return buf;
  const stream = new Blob([b]).stream().pipeThrough(new DecompressionStream('gzip'));
  return new Response(stream).arrayBuffer();
}
