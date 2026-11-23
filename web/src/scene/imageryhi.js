// Sharper ground imagery near the camera: CBERS-4A WPM 2 m tiles (web/tools/build_imagery_hi.mjs, data
// imagery_hi.json and imagery_hi/<i>_<j>.jpg), around the towns and along the mapped rivers. The tiles
// around the orbit centre are streamed into an atlas of SLOTS x SLOTS tiles (tile (i, j) goes to slot
// (i mod SLOTS, j mod SLOTS)), and the terrain shader draws a slot where it holds the tile wanted there
// (Terrain.setHiImagery). Elsewhere, and far away, the Sentinel-2 base shows. DISPLAY ONLY.
import * as THREE from 'three';

const mod = (a, n) => ((a % n) + n) % n;

export class ImageryHi {
  constructor({ renderer, terrain, index, base, slots = 8 }) {
    Object.assign(this, { renderer, terrain, slots });
    this.T = index.tileM;
    this.P = index.tilePx;
    this.url = (i, j) => `${base}${index.dir}/${i}_${j}.jpg`;
    this.tiles = new Set(index.tiles.map(([i, j]) => `${i}_${j}`));
    const S = slots * this.P;
    this.atlas = new THREE.DataTexture(null, S, S, THREE.RGBAFormat); // allocated on the GPU, filled by tile
    this.atlas.minFilter = THREE.LinearFilter;
    this.atlas.magFilter = THREE.LinearFilter;
    this.atlas.generateMipmaps = false;
    this.idxData = new Uint8Array(slots * slots * 4); // per slot: tile i + 128, j + 128, loaded (255)
    this.idx = new THREE.DataTexture(this.idxData, slots, slots, THREE.RGBAFormat);
    this.idx.minFilter = THREE.NearestFilter;
    this.idx.magFilter = THREE.NearestFilter;
    this.idx.needsUpdate = true;
    this.slot = new Array(slots * slots).fill(null); // the tile key a slot holds or is loading
    this.inflight = 0;
    this.enabled = true;
    // allocate the atlas on the GPU now (no data to upload: dataReady false), so tiles can be copied in
    this.atlas.source.dataReady = false;
    this.atlas.needsUpdate = true;
    renderer.initTexture(this.atlas);
    terrain.setHiImagery({ atlas: this.atlas, idx: this.idx, slots, tile: this.T });
  }

  /** Per frame (cheap): load the wanted tiles around the orbit centre that are not in their slots. */
  update(target, dist) {
    if (!this.enabled || dist > 12000) return;
    const ci = Math.floor(target.x / this.T);
    const cj = Math.floor(target.z / this.T);
    const lo = -(this.slots / 2) + 1;
    const want = [];
    for (let di = lo; di < lo + this.slots; di++) {
      for (let dj = lo; dj < lo + this.slots; dj++) {
        const i = ci + di, j = cj + dj;
        if (this.tiles.has(`${i}_${j}`)) want.push([i, j, Math.hypot((i + 0.5) * this.T - target.x, (j + 0.5) * this.T - target.z)]);
      }
    }
    want.sort((a, b) => a[2] - b[2]);
    for (const [i, j] of want) {
      if (this.inflight >= 4) break;
      const s = mod(i, this.slots) + mod(j, this.slots) * this.slots;
      const key = `${i}_${j}`;
      if (this.slot[s] !== key) this.load(i, j, s, key);
    }
  }

  async load(i, j, s, key) {
    this.inflight++;
    this.slot[s] = key;
    this.idxData[s * 4 + 2] = 0; // the slot is stale until the tile is in
    this.idx.needsUpdate = true;
    try {
      const res = await fetch(this.url(i, j));
      if (!res.ok) throw new Error(res.status);
      const bmp = await createImageBitmap(await res.blob());
      if (this.slot[s] !== key) { bmp.close(); return; } // the slot was given to another tile meanwhile
      const tex = new THREE.Texture(bmp);
      this.renderer.copyTextureToTexture(tex, this.atlas, null, new THREE.Vector2((s % this.slots) * this.P, Math.floor(s / this.slots) * this.P));
      tex.dispose();
      bmp.close();
      this.idxData.set([i + 128, j + 128, 255, 255], s * 4);
      this.idx.needsUpdate = true;
    } catch {
      if (this.slot[s] === key) this.slot[s] = null;
    } finally {
      this.inflight--;
    }
  }

  /** Tiles drawn now (for the view note). */
  get loaded() { let n = 0; for (let s = 0; s < this.slot.length; s++) if (this.idxData[s * 4 + 2]) n++; return n; }
}
