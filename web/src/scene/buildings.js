// 3D buildings, after the Kelani WebTwin (src/buildings/BuildingManager.ts).
//
// Streams the 1 km building tiles (web/tools/build_buildings.mjs) around the view target, extrudes them
// in a worker (buildingGeom.js) and draws them with the facade material (buildingMaterial.js). Buildings
// appear only when the camera is close enough for them to be legible. Near tiles get pitched roofs,
// parapets and doors (LOD0); distant tiles are flat-roofed massing (LOD1), with 20 % hysteresis.
// Bases sit on the terrain mesh as drawn (its own triangles), with the vertical exaggeration applied to
// the ground but never to the buildings' heights. Shadows are draped by the shadow material.
import * as THREE from 'three';
import { decodeBuildingTile, gunzipIfNeeded, HEIGHT_SOURCE, FOOTPRINT_SOURCE, CLASS_NAME } from './buildingTile.js';
import { createBuildingMaterial, createShadowMaterial } from './buildingMaterial.js';

const PROFILE = {
  high: { showWithin: 9000, radius: 5000, lod0: 1800, inflight: 4 },
  medium: { showWithin: 7000, radius: 3500, lod0: 1200, inflight: 3 },
  low: { showWithin: 4500, radius: 2200, lod0: 700, inflight: 2 },
};

export class BuildingLayer {
  /**
   * terrain: scene/terrain.js Terrain (meshAt and meshGrid give the drawn mesh's heights);
   * frame: main.js frame; base: data URL prefix; quality: 'high' | 'medium' | 'low'.
   */
  constructor({ terrain, frame, base, quality }) {
    this.terrain = terrain;
    this.frame = frame;
    this.base = base;
    this.profile = PROFILE[quality] ?? PROFILE.medium;
    this.group = new THREE.Group();
    this.group.name = 'buildings';
    this.shadowGroup = new THREE.Group();
    this.shadowGroup.name = 'building-shadows';
    this.tiles = new Map();
    this.index = null;
    this.enabled = true;
    this.style = 'realistic';
    this.exag = 1;
    this.frameNo = 0;
    this.inflight = 0;
    this.pending = new Map();
    this.roofStats = { flat: 0, parapet: 0, hipped: 0, gabled: 0, shed: 0 };
    this.mat = createBuildingMaterial();
    // heights of the drawn terrain mesh, for draping shadows in the vertex shader
    const g = terrain.meshGrid();
    const tex = new THREE.DataTexture(g.heights, g.cols, g.rows, THREE.RedFormat, THREE.FloatType);
    tex.minFilter = tex.magFilter = THREE.NearestFilter;
    tex.needsUpdate = true;
    const { bbox, dLon, dLat } = terrain;
    const s = g.stride;
    const lon0 = frame.lon(0), lat0 = frame.lat(0);
    this.grid = {
      texture: tex,
      uGrid: new THREE.Vector4(1 / (frame.KX * dLon * s), ((lon0 - bbox.west) / dLon - 0.5) / s, 1 / (frame.KZ * dLat * s), ((bbox.north - lat0) / dLat - 0.5) / s),
      uGridN: new THREE.Vector2(g.cols, g.rows),
    };
    this.shadowMat = createShadowMaterial(this.grid, false);
    this.haloMat = createShadowMaterial(this.grid, true);
    this.workers = [0, 1].map(() => {
      const w = new Worker(new URL('./buildings.worker.js', import.meta.url), { type: 'module' });
      w.onmessage = (ev) => {
        const cb = this.pending.get(ev.data.id);
        if (cb) { this.pending.delete(ev.data.id); cb(ev.data); }
      };
      return w;
    });
    this.nextWorker = 0;
  }

  /** Loads the tile index; false when the buildings have not been built (the layer then stays empty). */
  async init() {
    try {
      const r = await fetch(this.base + 'buildings/index.json');
      if (!r.ok) return false;
      const ix = await r.json();
      // the tiles must be in this viewer's local frame
      const f = ix.frame;
      if (Math.abs(f.lon0 - this.frame.lon(0)) > 1e-9 || Math.abs(f.lat0 - this.frame.lat(0)) > 1e-9 || Math.abs(f.KX - this.frame.KX) > 1e-6) {
        console.warn('buildings: tiles were built for another window; rebuild them (npm --prefix web run buildings)');
        return false;
      }
      for (const t of ix.tiles) { t.cx = (t.x + 0.5) * ix.tileSize; t.cy = (t.y + 0.5) * ix.tileSize; }
      this.index = ix;
      return true;
    } catch {
      return false;
    }
  }

  get places() { return this.index?.places ?? []; }

  setEnabled(on) { this.enabled = on; this.applyVisibility(); }

  setStyle(style) {
    this.style = style;
    this.mat.uniforms.uFacade.value = style === 'realistic' ? 1 : 0;
    this.applyVisibility();
  }

  setExaggeration(exag) {
    if (exag === this.exag) return;
    this.exag = exag;
    for (const t of this.tiles.values()) if (t.state === 'ready') this.extrude(t);
  }

  applyVisibility() {
    const on = this.enabled && this.shown;
    this.group.visible = on;
    this.shadowGroup.visible = on && this.style === 'realistic';
  }

  /** per frame: shadow strength follows the sun; every 8th frame: visibility, streaming, LOD */
  update(camera, target, sunElevation) {
    const day = THREE.MathUtils.smoothstep(sunElevation, -1, 12);
    this.shadowMat.uniforms.uStrength.value = 0.36 * day;
    this.haloMat.uniforms.uStrength.value = 0.22;
    if (!this.index || ++this.frameNo % 8) return;
    const p = this.profile;
    const dist = camera.position.distanceTo(target);
    this.shown = dist < p.showWithin;
    this.applyVisibility();
    if (!this.enabled || !this.shown) return;
    const tx = target.x, ty = -target.z; // local metres, y north
    const R = THREE.MathUtils.clamp(dist * 1.4, 1500, p.radius);
    const want = this.index.tiles
      .map((t) => ({ t, d: Math.hypot(t.cx - tx, t.cy - ty) }))
      .filter((o) => o.d < R)
      .sort((a, b) => a.d - b.d);
    for (const { t, d } of want) {
      const key = `${t.x}_${t.y}`;
      const ex = this.tiles.get(key);
      if (ex) {
        ex.lastSeen = this.frameNo;
        if (ex.state === 'ready' && !ex.extruding) {
          const lod = ex.lod === 0 ? (d > p.lod0 * 1.2 ? 1 : 0) : (d < p.lod0 ? 0 : 1);
          if (lod !== ex.lod) { ex.lod = lod; this.extrude(ex); }
        }
        continue;
      }
      if (this.inflight >= p.inflight) break;
      this.load(t, key, d < p.lod0 ? 0 : 1);
    }
    for (const [key, t] of this.tiles) {
      if (t.state === 'loading') continue;
      const d = Math.hypot(t.info.cx - tx, t.info.cy - ty);
      if (d > R * 1.6 && this.frameNo - t.lastSeen > 120) { this.dispose(t); this.tiles.delete(key); }
    }
  }

  async load(info, key, lod) {
    const t = { key, info, state: 'loading', lod, extruding: false, lastSeen: this.frameNo, triangles: 0 };
    this.tiles.set(key, t);
    this.inflight++;
    try {
      const url = this.base + this.index.url.replace('{x}', info.x).replace('{y}', info.y);
      const r = await fetch(url);
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      t.buf = await gunzipIfNeeded(await r.arrayBuffer());
      t.data = decodeBuildingTile(t.buf);
      this.groundOf(t);
      t.state = 'ready';
      await this.extrude(t);
    } catch (e) {
      t.state = 'error';
      console.warn(`buildings: tile ${key}:`, e?.message ?? e);
    } finally {
      this.inflight--;
    }
  }

  /** ground under each building on the drawn terrain mesh (true metres): mean and lowest over its outer ring */
  groundOf(t) {
    const d = t.data;
    t.groundMean = new Float32Array(d.n).fill(NaN);
    t.groundLow = new Float32Array(d.n).fill(Infinity);
    const sum = new Float64Array(d.n), cnt = new Uint32Array(d.n);
    for (let r = 0; r < d.nR; r++) {
      if (d.ringHole[r]) continue;
      const b = d.ringBuilding[r];
      for (let i = d.ringStart[r]; i < d.ringStart[r + 1]; i++) {
        const h = this.terrain.meshAtXZ(d.cx + d.xy[i * 2], -(d.cy + d.xy[i * 2 + 1]));
        sum[b] += h; cnt[b]++;
        if (h < t.groundLow[b]) t.groundLow[b] = h;
      }
    }
    for (let b = 0; b < d.n; b++) t.groundMean[b] = cnt[b] ? sum[b] / cnt[b] : this.terrain.baseElev;
  }

  async extrude(t) {
    if (t.extruding) { t.again = true; return; }
    t.extruding = true;
    try {
      do {
        t.again = false;
        const ex = this.exag;
        const bases = t.groundMean.map((v) => v * ex), lows = t.groundLow.map((v) => v * ex);
        const id = `${t.key}#${Math.random().toString(36).slice(2)}`;
        const res = await new Promise((resolve) => {
          this.pending.set(id, resolve);
          const buf = t.buf.slice(0);
          this.workers[this.nextWorker++ % this.workers.length].postMessage({ id, buf, bases, lows, lod: t.lod }, [buf, bases.buffer, lows.buffer]);
        });
        if (res.error) throw new Error(res.error);
        if (this.tiles.get(t.key) !== t) return; // unloaded meanwhile
        this.dispose(t);
        const g = new THREE.BufferGeometry();
        g.setAttribute('position', new THREE.BufferAttribute(res.position, 3));
        g.setAttribute('normal', new THREE.BufferAttribute(res.normal, 3, true));
        g.setAttribute('color', new THREE.BufferAttribute(res.color, 3, true));
        g.setAttribute('aUvF', new THREE.BufferAttribute(res.uv, 2));
        g.setAttribute('aBld', new THREE.BufferAttribute(res.bld, 4));
        g.setIndex(new THREE.BufferAttribute(res.index, 1));
        g.computeBoundingSphere();
        const m = new THREE.Mesh(g, this.mat.material);
        m.position.set(t.info.cx, 0, -t.info.cy);
        m.receiveShadow = true;
        m.matrixAutoUpdate = false;
        m.updateMatrix();
        t.mesh = m;
        t.triangles = res.index.length / 3;
        this.group.add(m);
        for (const k of Object.keys(this.roofStats)) this.roofStats[k] += res.roofs[k];
        const drape = (arr, h, mat) => {
          if (!arr.length) return null;
          const sg = new THREE.BufferGeometry();
          sg.setAttribute('position', new THREE.BufferAttribute(arr, 3));
          sg.setAttribute('aH', new THREE.BufferAttribute(h, 1));
          const sm = new THREE.Mesh(sg, mat);
          sm.position.copy(m.position);
          sm.frustumCulled = false; // the shader moves the vertices
          sm.matrixAutoUpdate = false;
          sm.updateMatrix();
          this.shadowGroup.add(sm);
          return sm;
        };
        t.halo = drape(res.ao, res.aoV, this.haloMat);
        t.shadow = drape(res.shadow, res.shadowH, this.shadowMat);
        this.boxes(t, ex);
      } while (t.again);
    } catch (e) {
      console.warn(`buildings: extrude ${t.key}:`, e?.message ?? e);
    } finally {
      t.extruding = false;
    }
  }

  /** per-building scene boxes (and one for the tile) for picking */
  boxes(t, ex) {
    const d = t.data;
    const bx = new Float32Array(d.n * 6);
    for (let b = 0; b < d.n; b++) bx.set([Infinity, Infinity, Infinity, -Infinity, -Infinity, -Infinity], b * 6);
    for (let r = 0; r < d.nR; r++) {
      const b = d.ringBuilding[r];
      for (let i = d.ringStart[r]; i < d.ringStart[r + 1]; i++) {
        const x = d.cx + d.xy[i * 2], z = -(d.cy + d.xy[i * 2 + 1]);
        bx[b * 6] = Math.min(bx[b * 6], x); bx[b * 6 + 2] = Math.min(bx[b * 6 + 2], z);
        bx[b * 6 + 3] = Math.max(bx[b * 6 + 3], x); bx[b * 6 + 5] = Math.max(bx[b * 6 + 5], z);
      }
    }
    const tb = new THREE.Box3();
    for (let b = 0; b < d.n; b++) {
      bx[b * 6 + 1] = t.groundLow[b] * ex - 1.5;
      bx[b * 6 + 4] = t.groundMean[b] * ex + d.height[b];
      tb.expandByPoint(new THREE.Vector3(bx[b * 6], bx[b * 6 + 1], bx[b * 6 + 2]));
      tb.expandByPoint(new THREE.Vector3(bx[b * 6 + 3], bx[b * 6 + 4], bx[b * 6 + 5]));
    }
    t.bx = bx;
    t.box = tb;
    t.boxExag = ex;
  }

  dispose(t) {
    for (const k of ['mesh', 'shadow', 'halo']) {
      const m = t[k];
      if (!m) continue;
      m.parent?.remove(m);
      m.geometry.dispose();
      t[k] = null;
    }
  }

  /**
   * The building under a ray: the nearest footprint prism (walls from the ground to the data height, a
   * flat top) that the ray enters. Pitched roofs are tested as their prism.
   */
  pick(ray) {
    if (!this.group.visible) return null;
    let best = null;
    const box = new THREE.Box3(), hit = new THREE.Vector3();
    const o = ray.origin, dir = ray.direction;
    for (const t of this.tiles.values()) {
      if (!t.mesh || !t.bx || !ray.intersectBox(t.box, hit)) continue;
      const d = t.data, bx = t.bx;
      for (let b = 0; b < d.n; b++) {
        box.min.set(bx[b * 6], bx[b * 6 + 1], bx[b * 6 + 2]);
        box.max.set(bx[b * 6 + 3], bx[b * 6 + 4], bx[b * 6 + 5]);
        if (!ray.intersectBox(box, hit)) continue;
        const enter = hit.distanceTo(o);
        if (best && enter > best.distance) continue;
        const dist = this.prismHit(t, b, o, dir);
        if (dist !== null && (!best || dist < best.distance)) best = { distance: dist, tile: t, b };
      }
    }
    if (!best) return null;
    const { tile: t, b } = best;
    const d = t.data;
    return {
      distance: best.distance,
      info: {
        height: d.height[b], hsrc: d.hsrc[b], src: d.src[b], id: d.id[b], cls: d.cls[b], levels: d.levels[b],
        name: d.names[b] ?? null, ground: t.groundMean[b],
      },
    };
  }

  prismHit(t, b, o, dir) {
    const d = t.data, top = t.bx[b * 6 + 4], bottom = t.bx[b * 6 + 1];
    let best = null;
    for (let r = 0; r < d.nR; r++) {
      if (d.ringBuilding[r] !== b) continue;
      const s = d.ringStart[r], n = d.ringStart[r + 1] - s;
      const X = (i) => d.cx + d.xy[(s + i) * 2], Z = (i) => -(d.cy + d.xy[(s + i) * 2 + 1]);
      if (!d.ringHole[r] && Math.abs(dir.y) > 1e-9) { // flat top at the data height
        const k = (top - o.y) / dir.y;
        if (k > 0) {
          const px = o.x + dir.x * k, pz = o.z + dir.z * k;
          let inside = false;
          for (let i = 0, j = n - 1; i < n; j = i++) {
            if ((Z(i) > pz) !== (Z(j) > pz) && px < ((X(j) - X(i)) * (pz - Z(i))) / (Z(j) - Z(i)) + X(i)) inside = !inside;
          }
          if (inside && (best === null || k < best)) best = k;
        }
      }
      for (let i = 0; i < n; i++) { // walls
        const x0 = X(i), z0 = Z(i), x1 = X((i + 1) % n), z1 = Z((i + 1) % n);
        const ex = x1 - x0, ez = z1 - z0;
        const den = dir.x * ez - dir.z * ex;
        if (Math.abs(den) < 1e-12) continue;
        const k = ((x0 - o.x) * ez - (z0 - o.z) * ex) / den;
        const u = ((x0 - o.x) * dir.z - (z0 - o.z) * dir.x) / den;
        if (k <= 0 || u < 0 || u > 1) continue;
        const y = o.y + dir.y * k;
        if (y >= bottom && y <= top && (best === null || k < best)) best = k;
      }
    }
    return best;
  }

  /** hover text for a pick() result */
  static describe(info) {
    const what = info.name ? `<b>${escapeHtml(info.name)}</b>` : `<b>Building</b>${info.cls ? ` · ${CLASS_NAME[info.cls]}` : ''}`;
    const fp = info.src ? `${FOOTPRINT_SOURCE[info.src]} ${info.id}` : FOOTPRINT_SOURCE[0];
    const h = info.hsrc === 1 ? `${info.height.toFixed(1)} m: ${info.levels} storeys × 3 m (OSM)` : info.hsrc === 0
      ? `unknown; drawn ${info.height.toFixed(0)} m tall (placeholder)` : `${info.height.toFixed(1)} m: ${HEIGHT_SOURCE[info.hsrc]}`;
    return `${what}<br><span>Footprint: ${fp}</span><br><span>Height ${h}</span>`
      + '<br><span class="muted">Roof form, facade and colours are illustrative, not data</span>';
  }

  stats() {
    let tris = 0, ready = 0, lod0 = 0, buildings = 0;
    for (const t of this.tiles.values()) {
      if (t.state !== 'ready' || !t.mesh) continue;
      tris += t.triangles; ready++; buildings += t.data.n;
      if (t.lod === 0) lod0++;
    }
    return { tiles: ready, lod0, buildings, triangles: tris, shown: this.group.visible, roofs: { ...this.roofStats } };
  }
}

function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]);
}
