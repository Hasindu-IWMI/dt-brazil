// Extrudes one building tile off the main thread (buildingGeom.js does the work).
import { decodeBuildingTile } from './buildingTile.js';
import { extrudeTile } from './buildingGeom.js';

self.onmessage = (ev) => {
  const { id, buf, bases, lows, lod } = ev.data;
  try {
    const r = extrudeTile(decodeBuildingTile(buf), bases, lows, lod);
    const transfer = ['position', 'normal', 'color', 'uv', 'bld', 'index', 'triBuilding', 'shadow', 'shadowH', 'ao', 'aoV'].map((k) => r[k].buffer);
    self.postMessage({ id, ...r }, transfer);
  } catch (e) {
    self.postMessage({ id, error: e?.message ?? String(e) });
  }
};
