// Computes one lake's schematic flow (lakefield.js) off the main thread: about a second per large lake.
import { lakeField } from './lakefield.js';

self.onmessage = ({ data: { id, polys, rivers, tunnels } }) => {
  try {
    const { grid, ends, variants } = lakeField(polys, rivers, tunnels);
    const out = {
      id,
      grid: { x0: grid.x0, z0: grid.z0, cell: grid.cell, W: grid.W, H: grid.H, polyOf: grid.polyOf },
      ends,
      variants: variants.map(({ since, ends: used, field }) => ({ since, ends: used, field })),
    };
    const buffers = [grid.polyOf.buffer, ...variants.flatMap((v) => [v.field.vx.buffer, v.field.vz.buffer])];
    self.postMessage(out, buffers);
  } catch (err) {
    self.postMessage({ id, error: String(err?.stack ?? err) });
  }
};
