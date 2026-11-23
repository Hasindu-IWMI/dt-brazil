// The mapped river channels as a keep-out for display layers (trees): how far a scene point is from the
// nearest mapped river's water edge. The rivers are OpenStreetMap waterway=river centrelines (drawn in
// the direction of flow) with the river's mapped width (the OpenStreetMap width tag where there is one,
// else a nominal width; scene/riverflow.js), and the water edge is the centreline offset by half that
// width. This is the MAPPED channel, not an observed water extent for any date. Pure: no three.js.

const KEY = (i, j) => (i + 32768) * 65536 + (j + 32768);

export class RiverMask {
  /**
   * lines: [{ pts: [[x, z], ...] in scene metres, width: m }]. reach: m, the largest distance from the
   * water edge that is ever asked about (farther than that, edgeDistance gives Infinity). bucket: m,
   * side of the grid cells that index the segments.
   */
  constructor(lines, { reach = 30, bucket = 120 } = {}) {
    const seg = [];
    for (const { pts, width } of lines) for (let k = 1; k < pts.length; k++) seg.push(pts[k - 1][0], pts[k - 1][1], pts[k][0], pts[k][1], width / 2);
    this.seg = Float64Array.from(seg);
    this.count = seg.length / 5;
    this.reach = reach;
    this.bucket = bucket;
    // each segment goes in every grid cell that holds a point within (half width + reach) of it
    const cells = new Map();
    const B = bucket, s = this.seg;
    for (let n = 0; n < this.count; n++) {
      const o = n * 5, pad = s[o + 4] + reach;
      const i0 = Math.floor((Math.min(s[o], s[o + 2]) - pad) / B), i1 = Math.floor((Math.max(s[o], s[o + 2]) + pad) / B);
      const j0 = Math.floor((Math.min(s[o + 1], s[o + 3]) - pad) / B), j1 = Math.floor((Math.max(s[o + 1], s[o + 3]) + pad) / B);
      for (let i = i0; i <= i1; i++) {
        for (let j = j0; j <= j1; j++) {
          // the cell's centre within pad plus its half-diagonal of the segment (long diagonal segments skip most cells of their box)
          if (segDist((i + 0.5) * B, (j + 0.5) * B, s, o) > pad + B * Math.SQRT1_2) continue;
          const key = KEY(i, j);
          const list = cells.get(key);
          if (list) list.push(n); else cells.set(key, [n]);
        }
      }
    }
    this.cells = new Map([...cells].map(([k, v]) => [k, Uint32Array.from(v)]));
  }

  /** Metres from scene point (x, z) to the nearest mapped water edge: negative inside a channel, Infinity beyond reach. */
  edgeDistance(x, z) {
    const list = this.cells.get(KEY(Math.floor(x / this.bucket), Math.floor(z / this.bucket)));
    if (!list) return Infinity;
    const s = this.seg;
    let best = Infinity;
    for (let k = 0; k < list.length; k++) {
      const o = list[k] * 5;
      const d = segDist(x, z, s, o) - s[o + 4];
      if (d < best) best = d;
    }
    return best <= this.reach ? best : Infinity;
  }
}

/** Distance from (x, z) to the segment at s[o..o+3]. */
function segDist(x, z, s, o) {
  const ax = s[o], az = s[o + 1], dx = s[o + 2] - ax, dz = s[o + 3] - az;
  const L2 = dx * dx + dz * dz;
  const t = L2 > 0 ? Math.max(0, Math.min(1, ((x - ax) * dx + (z - az) * dz) / L2)) : 0;
  return Math.hypot(x - ax - t * dx, z - az - t * dz);
}
