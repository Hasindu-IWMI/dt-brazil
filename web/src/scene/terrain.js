// Terrain from the full-resolution Copernicus GLO-30 window (web/tools/build_display_terrain.mjs).
// Heights are the DEM's own (EGM2008 metres); vertical exaggeration is a display scale on the
// parent group. Relief shading comes from an object-space normal map at the DEM's native 30 m,
// so it stays correct under exaggeration; the mesh itself is sampled every `stride` cells.
// Ground colour: Sentinel-2 dry-season imagery (realistic), an elevation ramp (analytical), or
// WorldCover 2021 classes (land-cover layer). None of it changes with the replay date.
import * as THREE from 'three';
import { withAtmosphere } from './atmosphere.js';

/** Decode terrain_hi.bin: gzip of int16 decimetres, each row = first value then differences. */
export async function loadDem(url, W, H) {
  let bytes = new Uint8Array(await (await fetch(url)).arrayBuffer());
  if (bytes[0] === 0x1f && bytes[1] === 0x8b) { // not already decoded by the server
    const stream = new Blob([bytes]).stream().pipeThrough(new DecompressionStream('gzip'));
    bytes = new Uint8Array(await new Response(stream).arrayBuffer());
  }
  return decodeDem(new Int16Array(bytes.buffer, bytes.byteOffset, bytes.byteLength / 2), W, H);
}

/** int16 decimetres, per row first value then differences -> Float32 metres. */
export function decodeDem(enc, W, H) {
  const out = new Float32Array(W * H);
  for (let r = 0; r < H; r++) {
    let acc = 0;
    for (let c = 0; c < W; c++) {
      const i = r * W + c;
      acc = c === 0 ? enc[i] : acc + enc[i];
      out[i] = acc / 10;
    }
  }
  return out;
}

// WorldCover class colours (the product's own legend)
export const LANDCOVER = {
  10: ['Tree cover', '#006400'], 20: ['Shrubland', '#ffbb22'], 30: ['Grassland', '#ffff4c'], 40: ['Cropland', '#f096ff'],
  50: ['Built-up', '#fa0000'], 60: ['Bare / sparse', '#b4b4b4'], 70: ['Snow and ice', '#f0f0f0'], 80: ['Permanent water', '#0064c8'],
  90: ['Herbaceous wetland', '#0096a0'], 95: ['Mangroves', '#00cf75'], 100: ['Moss and lichen', '#fae6a0'],
};

// value noise for the fine ground texture (hash without sine, so it holds at scene coordinates of 1e5 m)
const GNOISE = /* glsl */ `
float gHash(vec2 p) { vec3 p3 = fract(vec3(p.xyx) * 0.1031); p3 += dot(p3, p3.yzx + 33.33); return fract((p3.x + p3.y) * p3.z); }
float gNoise(vec2 p) {
  vec2 i = floor(p);
  vec2 f = fract(p);
  vec2 u = f * f * (3.0 - 2.0 * f);
  return mix(mix(gHash(i), gHash(i + vec2(1.0, 0.0)), u.x), mix(gHash(i + vec2(0.0, 1.0)), gHash(i + vec2(1.0, 1.0)), u.x), u.y);
}
`;

export class Terrain {
  constructor({ elev, meta, frame, stride, imagery, anisotropy }) {
    const { width: W, height: H, bbox } = meta;
    Object.assign(this, { elev, W, H, bbox, frame, stride });
    this.dLon = (bbox.east - bbox.west) / W;
    this.dLat = (bbox.north - bbox.south) / H;
    this.group = new THREE.Group();

    // ---- object-space normals at full resolution (x east, y up, z south)
    const dx = this.dLon * frame.KX;
    const dz = this.dLat * frame.KZ;
    const nrm = new Uint8Array(W * H * 4);
    const n = new THREE.Vector3();
    const normalAt = (c, r, out) => {
      const cl = Math.max(0, c - 1), cr = Math.min(W - 1, c + 1), ru = Math.max(0, r - 1), rd = Math.min(H - 1, r + 1);
      const gx = (elev[r * W + cr] - elev[r * W + cl]) / ((cr - cl) * dx);
      const gz = (elev[rd * W + c] - elev[ru * W + c]) / ((rd - ru) * dz); // rows run north to south = +z
      return out.set(-gx, 1, -gz).normalize();
    };
    for (let r = 0; r < H; r++) {
      const tr = H - 1 - r; // texture rows bottom-up, to match uv.y = 0 at the south edge
      for (let c = 0; c < W; c++) {
        normalAt(c, r, n);
        const o = (tr * W + c) * 4;
        nrm[o] = (n.x * 0.5 + 0.5) * 255; nrm[o + 1] = (n.y * 0.5 + 0.5) * 255; nrm[o + 2] = (n.z * 0.5 + 0.5) * 255; nrm[o + 3] = 255;
      }
    }
    const normalTex = new THREE.DataTexture(nrm, W, H, THREE.RGBAFormat);
    normalTex.minFilter = THREE.LinearMipmapLinearFilter;
    normalTex.magFilter = THREE.LinearFilter;
    normalTex.generateMipmaps = true;
    normalTex.anisotropy = anisotropy;
    normalTex.needsUpdate = true;

    // ---- mesh every `stride` cells, plus skirts down to the base plane
    const cols = Math.floor((W - 1) / stride) + 1;
    const rows = Math.floor((H - 1) / stride) + 1;
    const lonAt = (c) => bbox.west + (c + 0.5) * this.dLon;
    const latAt = (r) => bbox.north - (r + 0.5) * this.dLat;
    let edgeMin = Infinity;
    const ring = [];
    for (let ci = 0; ci < cols; ci++) ring.push([ci * stride, 0]);
    for (let ri = 1; ri < rows; ri++) ring.push([(cols - 1) * stride, ri * stride]);
    for (let ci = cols - 2; ci >= 0; ci--) ring.push([ci * stride, (rows - 1) * stride]);
    for (let ri = rows - 2; ri > 0; ri--) ring.push([0, ri * stride]);
    for (const [c, r] of ring) edgeMin = Math.min(edgeMin, elev[r * W + c]);
    this.baseElev = edgeMin - 40;

    const nv = cols * rows;
    const pos = new Float32Array((nv + ring.length * 2) * 3);
    const nor = new Float32Array((nv + ring.length * 2) * 3);
    const uv = new Float32Array((nv + ring.length * 2) * 2);
    const put = (v, x, y, z, nx, ny, nz, u, w) => {
      pos.set([x, y, z], v * 3); nor.set([nx, ny, nz], v * 3); uv.set([u, w], v * 2);
    };
    for (let ri = 0; ri < rows; ri++) {
      for (let ci = 0; ci < cols; ci++) {
        const c = ci * stride, r = ri * stride;
        const lon = lonAt(c), lat = latAt(r);
        normalAt(c, r, n);
        put(ri * cols + ci, frame.X(lon), elev[r * W + c], frame.Z(lat), n.x, n.y, n.z,
          (lon - bbox.west) / (bbox.east - bbox.west), (lat - bbox.south) / (bbox.north - bbox.south));
      }
    }
    const surfaceCount = (rows - 1) * (cols - 1) * 6;
    const idx = new Uint32Array(surfaceCount + ring.length * 6);
    let q = 0;
    for (let ri = 0; ri < rows - 1; ri++) {
      for (let ci = 0; ci < cols - 1; ci++) {
        const a = ri * cols + ci, b = a + 1, d = a + cols, e = d + 1;
        idx[q++] = a; idx[q++] = d; idx[q++] = b; idx[q++] = b; idx[q++] = d; idx[q++] = e;
      }
    }
    // skirts: a wall from each edge vertex down to the base level, outward-facing
    ring.forEach(([c, r], k) => {
      const lon = lonAt(c), lat = latAt(r);
      const x = frame.X(lon), z = frame.Z(lat);
      const u = (lon - bbox.west) / (bbox.east - bbox.west), w = (lat - bbox.south) / (bbox.north - bbox.south);
      put(nv + 2 * k, x, elev[r * W + c], z, 0, 1, 0, u, w);
      put(nv + 2 * k + 1, x, this.baseElev, z, 0, 1, 0, u, w);
    });
    for (let k = 0; k < ring.length; k++) {
      const a = nv + 2 * k, b = nv + 2 * ((k + 1) % ring.length);
      idx[q++] = a; idx[q++] = a + 1; idx[q++] = b; idx[q++] = b; idx[q++] = a + 1; idx[q++] = b + 1;
    }
    const geo = new THREE.BufferGeometry();
    geo.setAttribute('position', new THREE.BufferAttribute(pos, 3));
    geo.setAttribute('normal', new THREE.BufferAttribute(nor, 3));
    geo.setAttribute('uv', new THREE.BufferAttribute(uv, 2));
    geo.setIndex(new THREE.BufferAttribute(idx, 1));
    geo.addGroup(0, surfaceCount, 0);
    geo.addGroup(surfaceCount, idx.length - surfaceCount, 1);
    geo.computeBoundingSphere();

    // ---- materials
    if (imagery) {
      imagery.colorSpace = THREE.SRGBColorSpace;
      imagery.anisotropy = anisotropy;
    }
    this.normalTex = normalTex;
    this.imagery = imagery;
    this.hypso = this.makeHypso();
    // Realistic style: the ground colour fades, over the outer EDGE_FADE of the window, to the
    // imagery's mean colour, which the skirts and the base plane also use, so the window's edge
    // does not read as a cut slab.
    this.edgeCol = { value: new THREE.Color(0x4a4a35) };
    this.edgeOn = { value: 1 };
    // overlay: an RGBA texture on the same window (e.g. catchments), mixed into the ground colour so it
    // is lit and shaded with the relief, i.e. draped exactly on the DEM at every view
    const blank = new THREE.DataTexture(new Uint8Array(4), 1, 1, THREE.RGBAFormat);
    blank.needsUpdate = true;
    this.overlay = { value: blank };
    this.overlayOn = { value: 0 };
    // detail overlay: a sharper RGBA texture on a sub-window (box = u0, v0, u1, v1 in the window's uv),
    // e.g. the flood risk sectors of one town, mixed in over the window-wide overlay
    this.detail = { value: blank };
    this.detailBox = { value: new THREE.Vector4(0, 0, 1, 1) };
    this.detailOn = { value: 0 };
    // sharper imagery near the camera (scene/imageryhi.js): an atlas of slots x slots tiles of `tile` m,
    // tile (i, j) in slot (i mod slots, j mod slots); idx holds, per slot, the tile it holds (i + 128,
    // j + 128) and whether it is loaded. uHiMap turns the window's uv into scene x, z.
    const xW = frame.X(bbox.west), xE = frame.X(bbox.east), zS = frame.Z(bbox.south), zN = frame.Z(bbox.north);
    this.hi = { atlas: { value: blank }, idx: { value: blank }, map: { value: new THREE.Vector4(xW, xE - xW, zS, zS - zN) },
      tile: { value: 1024 }, slots: { value: 8 }, on: { value: 0 } };
    this.hasHi = false;
    // fine ground texture close to the camera (realistic style; display only): value noise at a few
    // metres, strongest on vegetation, weaker on built-up land, none on mapped water
    this.texOn = { value: 0 };
    const EDGE = /* glsl */ `
      #ifdef USE_MAP
      {
        vec2 gXZ = vec2(uHiMap.x + vMapUv.x * uHiMap.y, uHiMap.z - vMapUv.y * uHiMap.w);
        float gHi = 0.0;
        vec2 hiTc = gXZ / uHiTile;
        vec2 hiFw = fwidth(hiTc) * 512.0; // 2 m pixels per screen pixel: above ~2 the atlas (no mipmaps) would shimmer
        float hiFade = (1.0 - smoothstep(1.6, 3.2, max(hiFw.x, hiFw.y))) * uHiOn;
        if (hiFade > 0.0) {
          vec2 ti = floor(hiTc);
          vec2 slot = mod(ti, uHiSlots);
          vec4 id = texelFetch(tHiIdx, ivec2(slot), 0);
          if (id.b > 0.5 && abs(id.r * 255.0 - (ti.x + 128.0)) < 0.5 && abs(id.g * 255.0 - (ti.y + 128.0)) < 0.5) {
            vec2 f = clamp(fract(hiTc), 0.5 / 512.0, 1.0 - 0.5 / 512.0);
            vec3 c = texture2D(tHiAtlas, (slot + f) / uHiSlots).rgb;
            c = mix(c / 12.92, pow((c + 0.055) / 1.055, vec3(2.4)), step(0.04045, c)); // sRGB bytes to linear
            diffuseColor.rgb = mix(diffuseColor.rgb, c, hiFade);
            gHi = hiFade;
          }
        }
        if (uTexOn > 0.5) {
          float near = 1.0 - smoothstep(350.0, 2600.0, length(vViewPosition));
          if (near > 0.0) {
            float n = gNoise(gXZ * 0.55) * 0.45 + gNoise(gXZ * 0.17) * 0.35 + gNoise(gXZ * 1.9) * 0.2;
            float amp = 0.3;
            #ifdef USE_ROUGHNESSMAP
              float rg = texture2D(roughnessMap, vRoughnessMapUv).g; // land-cover roughness: water low, built-up mid
              amp *= smoothstep(0.2, 0.5, rg) * mix(0.45, 1.0, smoothstep(0.8, 0.95, rg));
            #endif
            amp *= mix(1.0, 0.35, gHi); // the 2 m imagery carries its own detail
            diffuseColor.rgb *= 1.0 + amp * near * (n - 0.5);
          }
        }
        vec2 e = min(vMapUv, 1.0 - vMapUv);
        float k = (1.0 - smoothstep(0.0, 0.045, min(e.x, e.y * 0.8))) * uEdgeOn;
        diffuseColor.rgb = mix(diffuseColor.rgb, uEdgeCol, k);
        vec4 ov = texture2D(tOverlay, vMapUv);
        diffuseColor.rgb = mix(diffuseColor.rgb, ov.rgb, ov.a * uOverlayOn);
        vec2 du = (vMapUv - uDetailBox.xy) / (uDetailBox.zw - uDetailBox.xy);
        if (uDetailOn > 0.5 && du.x >= 0.0 && du.x <= 1.0 && du.y >= 0.0 && du.y <= 1.0) {
          vec4 dv = texture2D(tDetail, du);
          diffuseColor.rgb = mix(diffuseColor.rgb, dv.rgb, dv.a);
        }
      }
      #endif`;
    this.surface = withAtmosphere(new THREE.MeshStandardMaterial({
      map: imagery ?? this.hypso, normalMap: normalTex, normalMapType: THREE.ObjectSpaceNormalMap, roughness: 0.93, metalness: 0,
    }), { key: 'terrain' });
    const prev = this.surface.onBeforeCompile;
    this.surface.onBeforeCompile = (shader, r) => {
      prev(shader, r);
      shader.uniforms.uEdgeCol = this.edgeCol;
      shader.uniforms.uEdgeOn = this.edgeOn;
      shader.uniforms.tOverlay = this.overlay;
      shader.uniforms.uOverlayOn = this.overlayOn;
      shader.uniforms.tDetail = this.detail;
      shader.uniforms.uDetailBox = this.detailBox;
      shader.uniforms.uDetailOn = this.detailOn;
      shader.uniforms.tHiAtlas = this.hi.atlas;
      shader.uniforms.tHiIdx = this.hi.idx;
      shader.uniforms.uHiMap = this.hi.map;
      shader.uniforms.uHiTile = this.hi.tile;
      shader.uniforms.uHiSlots = this.hi.slots;
      shader.uniforms.uHiOn = this.hi.on;
      shader.uniforms.uTexOn = this.texOn;
      shader.fragmentShader = 'uniform vec3 uEdgeCol;\nuniform float uEdgeOn;\nuniform sampler2D tOverlay;\nuniform float uOverlayOn;\n'
        + 'uniform sampler2D tDetail;\nuniform vec4 uDetailBox;\nuniform float uDetailOn;\n'
        + 'uniform sampler2D tHiAtlas;\nuniform sampler2D tHiIdx;\nuniform vec4 uHiMap;\nuniform float uHiTile;\nuniform float uHiSlots;\nuniform float uHiOn;\nuniform float uTexOn;\n'
        + GNOISE
        + shader.fragmentShader.replace('#include <map_fragment>', '#include <map_fragment>\n' + EDGE);
    };
    this.skirtMat = withAtmosphere(new THREE.MeshStandardMaterial({ color: 0x4a4a35, roughness: 1, side: THREE.DoubleSide }), { key: 'skirt' });
    this.mesh = new THREE.Mesh(geo, [this.surface, this.skirtMat]);
    this.group.add(this.mesh);

    // a wide plane at the base level so the horizon is ground, not void (realistic style only)
    this.baseMat = withAtmosphere(new THREE.MeshStandardMaterial({ color: 0x4a4a35, roughness: 1 }), { key: 'base' });
    this.base = new THREE.Mesh(new THREE.PlaneGeometry(1.2e6, 1.2e6).rotateX(-Math.PI / 2), this.baseMat);
    if (imagery?.image) { // mean colour of the imagery (sRGB average of a small copy)
      const cv = document.createElement('canvas');
      cv.width = 64; cv.height = 52;
      const g = cv.getContext('2d');
      g.drawImage(imagery.image, 0, 0, 64, 52);
      const d = g.getImageData(0, 0, 64, 52).data;
      let rr = 0, gg = 0, bb = 0;
      for (let i = 0; i < d.length; i += 4) { rr += d[i]; gg += d[i + 1]; bb += d[i + 2]; }
      const k = 255 * (d.length / 4);
      this.edgeCol.value.setRGB(rr / k, gg / k, bb / k, THREE.SRGBColorSpace);
    }
    this.skirtMat.color.copy(this.edgeCol.value);
    this.baseMat.color.copy(this.edgeCol.value);
    this.base.position.y = this.baseElev - 1;
    this.group.add(this.base);
    this.style = imagery ? 'realistic' : 'analytical';
    this.showLandcover = false;
    this.landcoverTex = null;
  }

  makeHypso() {
    const { W, H, elev } = this;
    const w = Math.ceil(W / 2), h = Math.ceil(H / 2);
    let lo = Infinity, hi = -Infinity;
    for (const v of elev) { if (v < lo) lo = v; if (v > hi) hi = v; }
    // the original analytical ramp, interpolated in sRGB bytes (the texture is tagged sRGB)
    const a = [0x3d, 0x4a, 0x3c], b = [0x6f, 0x74, 0x5c], c = [0xb9, 0xae, 0x94];
    const px = new Uint8Array(w * h * 4);
    for (let r = 0; r < h; r++) {
      for (let q = 0; q < w; q++) {
        const f = (elev[Math.min(H - 1, r * 2) * W + Math.min(W - 1, q * 2)] - lo) / (hi - lo);
        const [u, v, k] = f < 0.45 ? [a, b, f / 0.45] : [b, c, (f - 0.45) / 0.55];
        const o = ((h - 1 - r) * w + q) * 4;
        for (let ch = 0; ch < 3; ch++) px[o + ch] = u[ch] + (v[ch] - u[ch]) * k;
        px[o + 3] = 255;
      }
    }
    const tex = new THREE.DataTexture(px, w, h, THREE.RGBAFormat);
    tex.colorSpace = THREE.SRGBColorSpace;
    tex.minFilter = THREE.LinearMipmapLinearFilter;
    tex.magFilter = THREE.LinearFilter;
    tex.generateMipmaps = true;
    tex.needsUpdate = true;
    return tex;
  }

  /**
   * Land-cover classes as colours, a roughness map that lets mapped water catch the sun, and the class
   * grid itself (classAt). Loaded once; later calls get the same promise.
   */
  loadLandcover(url) {
    this.landcoverLoad ??= this.readLandcover(url);
    return this.landcoverLoad;
  }

  /** WorldCover class code at a geographic point (nearest 20 m pixel); 0 outside the window or before loading. */
  classAt(lon, lat) {
    const lc = this.lcClass;
    if (!lc) return 0;
    const { bbox } = this;
    const q = Math.floor(((lon - bbox.west) / (bbox.east - bbox.west)) * lc.w);
    const r = Math.floor(((bbox.north - lat) / (bbox.north - bbox.south)) * lc.h);
    return q >= 0 && r >= 0 && q < lc.w && r < lc.h ? lc.cls[r * lc.w + q] : 0;
  }

  async readLandcover(url) {
    const img = await new Promise((resolve, reject) => {
      const i = new Image();
      i.onload = () => resolve(i);
      i.onerror = reject;
      i.src = url;
    });
    const cv = document.createElement('canvas');
    cv.width = img.width; cv.height = img.height;
    const g = cv.getContext('2d', { willReadFrequently: true });
    g.drawImage(img, 0, 0);
    const src = g.getImageData(0, 0, img.width, img.height).data;
    const pal = {}; // sRGB bytes straight from the legend (the texture is tagged sRGB)
    for (const [k, [, hex]] of Object.entries(LANDCOVER)) {
      const v = parseInt(hex.slice(1), 16);
      pal[k] = { r: (v >> 16) / 255, g: ((v >> 8) & 255) / 255, b: (v & 255) / 255 };
    }
    const w = img.width, h = img.height;
    const col = new Uint8Array(w * h * 4);
    const rw = w >> 1, rh = h >> 1;
    const rough = new Uint8Array(rw * rh * 4);
    const grid = new Uint8Array(w * h); // rows north to south, as in the PNG
    for (let r = 0; r < h; r++) {
      for (let q = 0; q < w; q++) {
        const cls = src[(r * w + q) * 4];
        grid[r * w + q] = cls;
        const p = pal[cls];
        const o = ((h - 1 - r) * w + q) * 4;
        if (p) { col[o] = p.r * 255; col[o + 1] = p.g * 255; col[o + 2] = p.b * 255; }
        col[o + 3] = 255;
        if (!(r & 1) && !(q & 1) && (r >> 1) < rh && (q >> 1) < rw) {
          const ro = ((rh - 1 - (r >> 1)) * rw + (q >> 1)) * 4;
          rough[ro + 1] = cls === 80 ? 30 : cls === 10 ? 250 : cls === 50 ? 190 : 235; // green channel = roughness
          rough[ro + 3] = 255;
        }
      }
    }
    const mk = (data, ww, hh, srgb) => {
      const t = new THREE.DataTexture(data, ww, hh, THREE.RGBAFormat);
      if (srgb) t.colorSpace = THREE.SRGBColorSpace;
      t.minFilter = THREE.LinearMipmapLinearFilter;
      t.magFilter = srgb ? THREE.NearestFilter : THREE.LinearFilter;
      t.generateMipmaps = true;
      t.needsUpdate = true;
      return t;
    };
    this.landcoverTex = mk(col, w, h, true);
    this.roughTex = mk(rough, rw, rh, false);
    this.lcClass = { cls: grid, w, h };
    this.apply();
  }

  /** Drape an RGBA texture (same window as the DEM) on the ground; null removes it. */
  setOverlay(tex) {
    if (tex) this.overlay.value = tex;
    this.overlayOn.value = tex ? 1 : 0;
  }

  /** Drape a sharper RGBA texture on a sub-window {west, south, east, north} (north up); null removes it. */
  setDetailOverlay(tex, box) {
    if (tex) {
      const { bbox } = this;
      const u = (lon) => (lon - bbox.west) / (bbox.east - bbox.west), v = (lat) => (lat - bbox.south) / (bbox.north - bbox.south);
      this.detail.value = tex;
      this.detailBox.value.set(u(box.west), v(box.south), u(box.east), v(box.north));
    }
    this.detailOn.value = tex ? 1 : 0;
  }

  /** The streamed 2 m imagery (scene/imageryhi.js): its atlas, slot index, slots per side and tile size (m). */
  setHiImagery({ atlas, idx, slots, tile }) {
    this.hi.atlas.value = atlas;
    this.hi.idx.value = idx;
    this.hi.slots.value = slots;
    this.hi.tile.value = tile;
    this.hasHi = true;
    this.apply();
  }

  setStyle(style) { this.style = style; this.apply(); }
  setLandcover(on) { this.showLandcover = on; this.apply(); }

  apply() {
    const m = this.surface;
    const real = this.style === 'realistic' && this.imagery;
    m.map = this.showLandcover && this.landcoverTex ? this.landcoverTex : real ? this.imagery : this.hypso;
    m.roughnessMap = real && !this.showLandcover ? this.roughTex ?? null : null;
    m.roughness = real ? 1 : 0.95;
    m.needsUpdate = true;
    this.base.visible = this.style === 'realistic';
    this.edgeOn.value = real && !this.showLandcover ? 1 : 0; // never tint the class colours
    this.hi.on.value = real && !this.showLandcover && this.hasHi ? 1 : 0;
    this.texOn.value = real && !this.showLandcover ? 1 : 0;
    if (real) this.skirtMat.color.copy(this.edgeCol.value); else this.skirtMat.color.set(0x22231f);
  }

  /** DEM elevation (m) at a geographic point, bilinear; null outside the window. */
  elevAt(lon, lat) {
    const { W, H, bbox, elev } = this;
    const fx = (lon - bbox.west) / this.dLon - 0.5;
    const fy = (bbox.north - lat) / this.dLat - 0.5;
    if (fx < 0 || fy < 0 || fx > W - 1 || fy > H - 1) return null;
    const x0 = Math.min(W - 2, Math.floor(fx)), y0 = Math.min(H - 2, Math.floor(fy));
    const tx = fx - x0, ty = fy - y0;
    const i = y0 * W + x0;
    return (elev[i] * (1 - tx) + elev[i + 1] * tx) * (1 - ty) + (elev[i + W] * (1 - tx) + elev[i + W + 1] * tx) * ty;
  }

  /** Elevation under a scene point (x, z), or the base level outside the window. */
  elevAtXZ(x, z) {
    return this.elevAt(this.frame.lon(x), this.frame.lat(z)) ?? this.baseElev;
  }

  /**
   * Height of the mesh as drawn (vertices every `stride` cells, each cell split along its NE-SW
   * diagonal like the index buffer above) at a geographic point; null outside the mesh. Lines, pins and
   * buildings use it so they sit on the surface you see; buildingMaterial.js does the same on the GPU.
   */
  meshAt(lon, lat) {
    const { W, H, bbox, elev, stride } = this;
    const cols = Math.floor((W - 1) / stride) + 1, rows = Math.floor((H - 1) / stride) + 1;
    const fx = ((lon - bbox.west) / this.dLon - 0.5) / stride;
    const fy = ((bbox.north - lat) / this.dLat - 0.5) / stride;
    if (!(fx >= 0 && fy >= 0 && fx <= cols - 1 && fy <= rows - 1)) return null;
    const ci = Math.min(cols - 2, Math.floor(fx)), ri = Math.min(rows - 2, Math.floor(fy));
    const tx = fx - ci, ty = fy - ri;
    const e = (c, r) => elev[r * stride * W + c * stride];
    const a = e(ci, ri), b = e(ci + 1, ri), d = e(ci, ri + 1), f = e(ci + 1, ri + 1);
    return tx + ty <= 1 ? a + (b - a) * tx + (d - a) * ty : f + (d - f) * (1 - tx) + (b - f) * (1 - ty);
  }

  /** meshAt for a scene point (x, z); the base level outside the window. */
  meshAtXZ(x, z) {
    return this.meshAt(this.frame.lon(x), this.frame.lat(z)) ?? this.baseElev;
  }

  /** The mesh's vertex heights (rows north to south), for a GPU copy of the drawn surface. */
  meshGrid() {
    const { W, H, elev, stride } = this;
    const cols = Math.floor((W - 1) / stride) + 1, rows = Math.floor((H - 1) / stride) + 1;
    const heights = new Float32Array(cols * rows);
    for (let r = 0; r < rows; r++) for (let c = 0; c < cols; c++) heights[r * cols + c] = elev[r * stride * W + c * stride];
    return { cols, rows, stride, heights };
  }

  /** Median DEM height inside a polygon (geographic ring), sampled on a coarse grid. */
  medianInside(ring) {
    let w = Infinity, e = -Infinity, s = Infinity, nn = -Infinity;
    for (const [lon, lat] of ring) { w = Math.min(w, lon); e = Math.max(e, lon); s = Math.min(s, lat); nn = Math.max(nn, lat); }
    const vals = [];
    const step = Math.max(this.dLon, (e - w) / 120);
    for (let lat = s; lat <= nn; lat += step) {
      for (let lon = w; lon <= e; lon += step) {
        if (!pointInRing(lon, lat, ring)) continue;
        const v = this.elevAt(lon, lat);
        if (v !== null) vals.push(v);
      }
    }
    if (!vals.length) return null;
    vals.sort((a, b) => a - b);
    return vals[vals.length >> 1];
  }
}

export function pointInRing(x, y, ring) {
  let inside = false;
  for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
    const [xi, yi] = ring[i], [xj, yj] = ring[j];
    if ((yi > y) !== (yj > y) && x < ((xj - xi) * (y - yi)) / (yj - yi) + xi) inside = !inside;
  }
  return inside;
}
