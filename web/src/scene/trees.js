// Trees on the vegetated land-cover classes (ESA WorldCover 2021, data/landcover.png), drawn with ez-tree
// (Daniel Greenheck, MIT, npm @dgreenheck/ez-tree: procedural trees for three.js).
//
// WHERE a plant stands comes from the data: each 8 m cell of a 240 m tile is offered a plant with the
// chance its WorldCover class gives (dense on tree cover, bushes on shrubland and wetland, a few lone
// trees on grassland and cropland, none on built-up land or water). Everything else (which tree, its
// height, its exact spot within the cell, its form) is ILLUSTRATIVE, drawn from a hash of the tile, so
// the same trees come back every time. The Copernicus DEM is a SURFACE model: over forest it already
// follows the canopy, so trees on tree cover are sunk into the drawn surface and only their crowns
// show; lone trees on open land stand on it. No crown reaches over a mapped river (scene/rivermask.js):
// the land cover classes most of the length of these 11-12 m rivers as the tree cover on their banks.
//
// ez-tree is about 4 MB (its bark and leaf textures are inlined), so it is imported only when the layer
// is first switched on. A few species are generated once at three levels of detail and drawn as
// instanced meshes: tiles stream around the camera, are culled against the view on the CPU, and each
// tree takes its level by distance; far trees are thinned and shrink away rather than pop. Heights are
// never exaggerated: with vertical exaggeration the trees ride on the exaggerated ground. DISPLAY ONLY.
import * as THREE from 'three';
import { withAtmosphere } from './atmosphere.js';

export const TILE = 240; // m, tile side in scene coordinates (x east, z south)
export const CELL = 8; // m, candidate spacing within a tile

// ez-tree presets used, the height range each is drawn at (m), leaf and bark colours, and how much
// larger its leaf cards are drawn than the preset's (fuller crowns)
export const KINDS = [
  { key: 'oak', preset: 'Oak Medium', height: [13, 21], leaf: 0x7f9a55, bark: 0x7a7062, fuller: 1.45 },
  { key: 'ash', preset: 'Ash Large', height: [16, 26], leaf: 0x6f8c4c, bark: 0x6f675c, fuller: 1.4 },
  { key: 'aspen', preset: 'Aspen Medium', height: [11, 19], leaf: 0x8aa35c, bark: 0x9a9486, fuller: 1.6 },
  { key: 'bush', preset: 'Bush 1', height: [1.6, 3.4], leaf: 0x86a05a, bark: 0x6e6658, fuller: 1.15 },
  { key: 'bush2', preset: 'Bush 2', height: [1.4, 3.0], leaf: 0x7c9852, bark: 0x6e6658, fuller: 1.15 },
];
const KIND_INDEX = Object.fromEntries(KINDS.map((k, i) => [k.key, i]));

// Per WorldCover class: chance a cell holds a plant, the mix of kinds, and the share of each plant's
// height sunk below the drawn surface (forest only: the DSM there is already at the canopy).
export const PLANTING = {
  10: { p: 0.78, mix: { oak: 0.55, ash: 0.27, aspen: 0.18 }, sink: 0.5 }, // tree cover
  20: { p: 0.45, mix: { bush: 0.5, bush2: 0.4, oak: 0.1 }, sink: 0 }, // shrubland
  30: { p: 0.045, mix: { oak: 0.3, ash: 0.12, bush: 0.33, bush2: 0.25 }, sink: 0 }, // grassland: lone trees and bushes
  40: { p: 0.008, mix: { oak: 0.6, ash: 0.4 }, sink: 0 }, // cropland: field-edge trees
  60: { p: 0.01, mix: { bush: 0.6, bush2: 0.4 }, sink: 0 }, // bare / sparse vegetation
  90: { p: 0.12, mix: { bush: 0.6, bush2: 0.4 }, sink: 0 }, // herbaceous wetland
  95: { p: 0.75, mix: { bush: 0.5, bush2: 0.5 }, sink: 0.3 }, // mangroves (none in this window)
};

// Distances (m) for a REF_H tall tree; a plant of height h uses them scaled by h / REF_H. lod0, lod1: ends
// of the full and middle levels; past lod1 trees thin as (lod1 / d)^thin, down to minKeep, and shrink away
// over the last 18 % before far. density scales the planting chances; plant: tiles planted per rebuild.
const REF_H = 20;
const MAX_H = Math.max(...KINDS.map((k) => k.height[1]));
const PROFILE = {
  high: { lod0: 120, lod1: 450, far: 2200, thin: 1.3, minKeep: 0.22, density: 1, plant: 24 },
  medium: { lod0: 80, lod1: 300, far: 1500, thin: 1.5, minKeep: 0.18, density: 0.8, plant: 16 },
  low: { lod0: 40, lod1: 180, far: 900, thin: 1.6, minKeep: 0.15, density: 0.6, plant: 10 },
};

/** Deterministic random numbers in [0, 1) for a tile (mulberry32 on a hash of i, j). */
export function tileRandom(i, j, salt = 0) {
  let s = (Math.imul(i | 0, 73856093) ^ Math.imul(j | 0, 19349663) ^ Math.imul(salt | 0, 83492791)) >>> 0;
  return () => {
    s = (s + 0x6d2b79f5) >>> 0;
    let t = s;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

// a crown's radius as a share of the plant's height, until it is measured from the generated trees
export const CROWN_SHARE = 0.4;

/**
 * The plants of tile (i, j). classAt(x, z) gives the WorldCover class at a scene point (0 where there is
 * none). Each cell's point is jittered, and its class is read a few metres off the point, so class edges
 * (20 m pixels) are dithered rather than stepped. keepOut(x, z), if given, is the distance (m) from a
 * point to the nearest mapped water edge: a plant whose crown (radius crown[kind] x height) would reach
 * it is left out. Pure: no three.js, no terrain.
 */
export function plantTile(i, j, classAt, { tile = TILE, cell = CELL, density = 1, keepOut = null, crown = null } = {}) {
  const rnd = tileRandom(i, j);
  const per = Math.floor(tile / cell);
  const cap = per * per;
  const x = new Float32Array(cap), z = new Float32Array(cap), h = new Float32Array(cap), rot = new Float32Array(cap);
  const sink = new Float32Array(cap), rank = new Float32Array(cap), tone = new Float32Array(cap);
  const kind = new Uint8Array(cap), cls = new Uint8Array(cap);
  let n = 0;
  for (let a = 0; a < per; a++) {
    for (let b = 0; b < per; b++) {
      const px = i * tile + (a + rnd()) * cell, pz = j * tile + (b + rnd()) * cell;
      const c = classAt(px + (rnd() - 0.5) * 12, pz + (rnd() - 0.5) * 12);
      const rule = PLANTING[c];
      const u = rnd(), v = rnd(), w = rnd(), q = rnd(), r = rnd();
      if (!rule || u >= rule.p * density) continue;
      let acc = 0, k = null;
      for (const [key, share] of Object.entries(rule.mix)) { acc += share; if (v < acc) { k = key; break; } }
      k ??= Object.keys(rule.mix).at(-1);
      const kd = KINDS[KIND_INDEX[k]];
      x[n] = px; z[n] = pz;
      kind[n] = KIND_INDEX[k];
      cls[n] = c;
      h[n] = kd.height[0] + (kd.height[1] - kd.height[0]) * w * w * (3 - 2 * w); // middling heights most often
      rot[n] = q * Math.PI * 2;
      sink[n] = rule.sink;
      rank[n] = r;
      tone[n] = rnd();
      // tested after every random draw, so leaving a plant out changes none of the others
      if (keepOut && keepOut(px, pz) < (crown?.[kind[n]] ?? CROWN_SHARE) * h[n]) continue;
      n++;
    }
  }
  return { n, x, z, h, rot, sink, rank, tone, kind, cls };
}

// ---- species geometry from ez-tree

// Levels of detail, all cut from the one full tree so the crown keeps its shape from near to far:
// branches down to `levels` below the finest (0 = every twig), and a share of the leaves, each enlarged
// about its base so the crown stays about as full.
const LODS = [
  { drop: 0, keep: 0.5 },
  { drop: 2, keep: 0.12 }, // trunk and main limbs
  { drop: 9, keep: 1 / 40 }, // the trunk only
];

/**
 * The preset made lighter and fuller: fewer rings per branch and fewer sides per ring (about half the
 * bark triangles, same form), and larger leaf cards, since the presets are temperate trees with open
 * crowns and the Atlantic Forest canopy is closed and evergreen.
 */
function lean(o, kd) {
  const b = o.branch;
  for (const k of Object.keys(b.sections)) b.sections[k] = Math.max(k === '0' ? 4 : 2, Math.round(b.sections[k] * 0.7));
  for (const k of Object.keys(b.segments)) b.segments[k] = Math.min(b.segments[k], [6, 5, 4, 3][k] ?? 3);
  o.leaves.size *= kd.fuller ?? 1;
  return o;
}

const yieldFrame = () => new Promise((r) => setTimeout(r, 0));

/**
 * Generates every kind once and cuts its three levels of detail. Geometry is scaled so the tree is 1
 * unit tall with its trunk base at the origin; leaf normals point out of the crown, which lights the
 * foliage as a mass instead of as flat cards.
 */
async function buildSpecies(ez) {
  const out = [];
  for (const kd of KINDS) {
    const tree = new ez.Tree();
    tree.options.copy(lean(structuredClone(ez.TreePreset[kd.preset]), kd)); // with the preset's own seed
    // ez-tree grows branches breadth-first, so each level's triangles follow the level above's
    const levelEnd = [];
    const grow = tree.generateBranch.bind(tree);
    tree.generateBranch = (b) => { grow(b); levelEnd[b.level] = tree.branches.indices.length; };
    tree.generate();
    const bg = tree.branchesMesh.geometry, lg = tree.leavesMesh.geometry;
    bg.computeBoundingBox(); lg.computeBoundingBox();
    const scale = 1 / Math.max(bg.boundingBox.max.y, lg.boundingBox.max.y);
    bg.scale(scale, scale, scale);
    lg.scale(scale, scale, scale);
    const lb = lg.boundingBox;
    const centre = new THREE.Vector3((lb.min.x + lb.max.x) / 2, lb.min.y * 0.35 + lb.max.y * 0.65, (lb.min.z + lb.max.z) / 2).multiplyScalar(scale);
    const levels = tree.options.branch.levels;
    const perLeaf = tree.options.leaves.billboard === 'double' ? 8 : 4;
    const lods = LODS.map(({ drop, keep }) => {
      const b = new THREE.BufferGeometry();
      for (const k of ['position', 'normal', 'uv']) b.setAttribute(k, bg.attributes[k]);
      b.setIndex(bg.index);
      const last = Math.max(0, levels - drop);
      b.setDrawRange(0, drop ? levelEnd[last] ?? bg.index.count : bg.index.count);
      b.boundingSphere = bg.boundingSphere;
      const l = thinLeaves(lg, perLeaf, keep, Math.sqrt(1 / keep) * (keep < 1 ? 0.82 : 1));
      crownNormals(l, centre);
      return { branches: b, leaves: l, triangles: b.drawRange.count / 3 + l.index.count / 3 };
    });
    out.push({ kd, lods, crown: crownShare(lg), maps: { bark: tree.branchesMesh.material.map, barkNormal: tree.branchesMesh.material.normalMap, leaf: tree.leavesMesh.material.map } });
    tree.branchesMesh.material.dispose();
    tree.leavesMesh.material.dispose();
    lg.dispose();
    await yieldFrame();
  }
  return out;
}

/** The crown's radius as a share of height (the tree is 1 tall, trunk at the origin): 95 % of leaf vertices lie within it. */
function crownShare(g) {
  const p = g.attributes.position.array;
  const r = new Float32Array(p.length / 3);
  for (let k = 0; k < r.length; k++) r[k] = Math.hypot(p[k * 3], p[k * 3 + 2]);
  r.sort();
  return r.length ? r[Math.floor((r.length - 1) * 0.95)] : CROWN_SHARE;
}

/** Every leaf (perLeaf vertices: one or two crossed cards) kept at a regular share `keep`, grown about its base. */
function thinLeaves(g, perLeaf, keep, growBy) {
  const p = g.attributes.position.array, uv = g.attributes.uv.array;
  const total = p.length / 3 / perLeaf;
  const kept = [];
  for (let i = 0; i < total; i++) if (Math.floor((i + 1) * keep) > Math.floor(i * keep)) kept.push(i);
  const pos = new Float32Array(kept.length * perLeaf * 3), tex = new Float32Array(kept.length * perLeaf * 2);
  const idx = new Uint32Array(kept.length * (perLeaf / 4) * 6);
  kept.forEach((leaf, n) => {
    const v0 = leaf * perLeaf;
    // the card's base: the middle of its lower edge (vertices 1 and 2 of the first card)
    const bx = (p[(v0 + 1) * 3] + p[(v0 + 2) * 3]) / 2, by = (p[(v0 + 1) * 3 + 1] + p[(v0 + 2) * 3 + 1]) / 2, bz = (p[(v0 + 1) * 3 + 2] + p[(v0 + 2) * 3 + 2]) / 2;
    for (let v = 0; v < perLeaf; v++) {
      const s = (v0 + v) * 3, d = (n * perLeaf + v) * 3;
      pos[d] = bx + (p[s] - bx) * growBy; pos[d + 1] = by + (p[s + 1] - by) * growBy; pos[d + 2] = bz + (p[s + 2] - bz) * growBy;
      tex[(n * perLeaf + v) * 2] = uv[(v0 + v) * 2]; tex[(n * perLeaf + v) * 2 + 1] = uv[(v0 + v) * 2 + 1];
    }
    for (let c = 0; c < perLeaf / 4; c++) {
      const o = n * perLeaf + c * 4, q = (n * (perLeaf / 4) + c) * 6;
      idx.set([o, o + 1, o + 2, o, o + 2, o + 3], q);
    }
  });
  const out = new THREE.BufferGeometry();
  out.setAttribute('position', new THREE.BufferAttribute(pos, 3));
  out.setAttribute('uv', new THREE.BufferAttribute(tex, 2));
  out.setAttribute('normal', new THREE.BufferAttribute(new Float32Array(pos.length), 3));
  out.setIndex(new THREE.BufferAttribute(idx, 1));
  out.computeVertexNormals(); // card normals, blended into the crown normals below
  out.computeBoundingSphere();
  return out;
}

function crownNormals(g, c) {
  const p = g.attributes.position, n = g.attributes.normal;
  const v = new THREE.Vector3(), f = new THREE.Vector3();
  for (let k = 0; k < p.count; k++) {
    v.fromBufferAttribute(p, k).sub(c);
    v.y *= 1.6; // flatter crowns: more of the light from above
    f.fromBufferAttribute(n, k);
    v.normalize().multiplyScalar(0.8).addScaledVector(f, 0.2 * Math.sign(f.dot(v) || 1)).normalize();
    n.setXYZ(k, v.x, v.y, v.z);
  }
  n.needsUpdate = true;
}

// ---- materials: lit like the terrain, hazed like it, swaying a little

const treeUniforms = { uTreeTime: { value: 0 } };

function leafMaterial(map, colour, alphaTest, key) {
  const m = new THREE.MeshStandardMaterial({ map, color: colour, alphaTest, side: THREE.DoubleSide, roughness: 0.85, metalness: 0 });
  m.alphaToCoverage = true; // with MSAA: soft leaf edges, and far foliage keeps its coverage
  m.onBeforeCompile = (shader) => {
    shader.uniforms.uTreeTime = treeUniforms.uTreeTime;
    shader.vertexShader = 'uniform float uTreeTime;\n' + shader.vertexShader.replace('#include <begin_vertex>', /* glsl */ `
      #include <begin_vertex>
      #ifdef USE_INSTANCING
        vec3 tPos = instanceMatrix[3].xyz;
      #else
        vec3 tPos = vec3(0.0);
      #endif
      float tPh = dot(tPos.xz, vec2(0.071, 0.053));
      float tSw = sin(uTreeTime * 1.3 + tPh + position.y * 3.0) * 0.6 + sin(uTreeTime * 2.9 + tPh * 1.7) * 0.4;
      transformed.xz += vec2(1.0, 0.6) * tSw * 0.006 * position.y * (0.5 + uv.y);
      vTreeAo = mix(0.5, 1.0, smoothstep(0.25, 0.95, position.y)); // the lower crown sits in its own shade`);
    shader.vertexShader = 'varying float vTreeAo;\n' + shader.vertexShader;
    // crown normals light both faces of a card alike (no flip for the back face)
    shader.fragmentShader = 'varying float vTreeAo;\n' + shader.fragmentShader
      .replace('#include <normal_fragment_begin>', THREE.ShaderChunk.normal_fragment_begin.replace('normal *= faceDirection;', ''))
      .replace('#include <aomap_fragment>', '#include <aomap_fragment>\n  reflectedLight.indirectDiffuse *= vTreeAo;\n  reflectedLight.directDiffuse *= mix(0.75, 1.0, vTreeAo);');
  };
  return withAtmosphere(m, { key });
}

function barkMaterial(map, normalMap, colour, key) {
  const m = new THREE.MeshStandardMaterial({ map, normalMap, color: colour, roughness: 0.95, metalness: 0 });
  return withAtmosphere(m, { key });
}

// ---- the layer

const LEAF_TONES = [new THREE.Color(0.78, 0.86, 0.72), new THREE.Color(1.0, 1.0, 0.86), new THREE.Color(0.66, 0.78, 0.64)];

export class TreeLayer {
  /**
   * terrain: scene/terrain.js Terrain; landcoverUrl: data/landcover.png; quality: 'high' | 'medium' | 'low';
   * rivers: scene/rivermask.js RiverMask of the mapped rivers, kept clear of crowns (optional).
   */
  constructor({ terrain, quality, landcoverUrl, rivers = null }) {
    this.terrain = terrain;
    this.frame = terrain.frame;
    this.landcoverUrl = landcoverUrl;
    this.keepOut = rivers ? (x, z) => rivers.edgeDistance(x, z) : null;
    this.crown = null; // per kind, measured once the trees are generated
    this.profile = PROFILE[quality] ?? PROFILE.medium;
    this.group = new THREE.Group();
    this.group.name = 'trees';
    this.group.visible = false;
    this.enabled = false;
    this.state = 'off'; // off | loading | ready | error
    this.exag = 1;
    this.tiles = new Map();
    this.frameNo = 0;
    this.lastBuild = -99;
    this.dirty = true;
    this.lastView = new Float64Array(32); // camera matrices last built for (scene coordinates reach 1e5 m)
    this.drawn = 0;
    this.triangles = 0;
    this.inRange = false;
    this.frustum = new THREE.Frustum();
    this.box = new THREE.Box3();
    this.mat4 = new THREE.Matrix4();
  }

  setEnabled(on) {
    this.enabled = on;
    this.group.visible = on && this.state === 'ready';
    if (on && this.state === 'off') this.init();
  }

  setExaggeration(exag) {
    if (exag !== this.exag) { this.exag = exag; this.dirty = true; }
  }

  async init() {
    this.state = 'loading';
    try {
      const [ez] = await Promise.all([import('@dgreenheck/ez-tree'), this.terrain.loadLandcover(this.landcoverUrl)]);
      const species = await buildSpecies(ez);
      this.meshes = species.map((s, ki) => s.lods.map((l, lod) => {
        const leaf = leafMaterial(s.maps.leaf, s.kd.leaf, [0.5, 0.42, 0.3][lod], `tree-leaf-${lod}`);
        const bark = barkMaterial(lod < 2 ? s.maps.bark : null, lod === 0 ? s.maps.barkNormal : null, s.kd.bark, `tree-bark-${lod}`);
        return this.makePair(l, bark, leaf, 1024, `${KINDS[ki].key}-${lod}`);
      }));
      this.species = species;
      this.crown = species.map((s) => s.crown);
      this.state = 'ready';
      this.dirty = true;
      this.group.visible = this.enabled;
    } catch (e) {
      console.warn('trees:', e?.message ?? e);
      this.state = 'error';
    }
  }

  makePair(l, barkMat, leafMat, capacity, name) {
    const branches = new THREE.InstancedMesh(l.branches, barkMat, capacity);
    const leaves = new THREE.InstancedMesh(l.leaves, leafMat, capacity);
    leaves.instanceMatrix = branches.instanceMatrix; // one set of transforms for both
    branches.instanceMatrix.setUsage(THREE.DynamicDrawUsage);
    leaves.instanceColor = new THREE.InstancedBufferAttribute(new Float32Array(capacity * 3), 3);
    leaves.instanceColor.setUsage(THREE.DynamicDrawUsage);
    for (const m of [branches, leaves]) {
      m.count = 0;
      m.frustumCulled = false; // culled per tile on the CPU
      m.receiveShadow = true; // hills shade the trees in their valleys
      m.name = `trees-${name}`;
      this.group.add(m);
    }
    return { branches, leaves, capacity, n: 0, tris: l.triangles };
  }

  grow(pair, need) {
    let cap = pair.capacity;
    while (cap < need) cap *= 2;
    const geo = { branches: pair.branches.geometry, leaves: pair.leaves.geometry };
    const mats = [pair.branches.material, pair.leaves.material];
    const fresh = this.makePair({ ...geo, triangles: pair.tris }, mats[0], mats[1], cap, pair.branches.name.slice(6));
    fresh.branches.instanceMatrix.array.set(pair.branches.instanceMatrix.array); // keep what this rebuild has written
    fresh.leaves.instanceColor.array.set(pair.leaves.instanceColor.array);
    for (const m of [pair.branches, pair.leaves]) { this.group.remove(m); m.dispose(); }
    Object.assign(pair, { branches: fresh.branches, leaves: fresh.leaves, capacity: cap });
  }

  classAtXZ = (x, z) => this.terrain.classAt(this.frame.lon(x), this.frame.lat(z));

  plant(i, j) {
    const t = plantTile(i, j, this.classAtXZ, { density: this.profile.density, keepOut: this.keepOut, crown: this.crown });
    t.g = new Float32Array(t.n);
    t.sinkM = new Float32Array(t.n);
    let gLo = Infinity, gHi = -Infinity, top = 0, deep = 0;
    for (let k = 0; k < t.n; k++) {
      const g = this.terrain.meshAtXZ(t.x[k], t.z[k]);
      t.g[k] = g;
      t.sinkM[k] = t.sink[k] * t.h[k] + 0.3; // a little into the ground, so no base floats on a slope
      gLo = Math.min(gLo, g); gHi = Math.max(gHi, g);
      top = Math.max(top, t.h[k] - t.sinkM[k]); deep = Math.max(deep, t.sinkM[k]);
    }
    Object.assign(t, { i, j, gLo, gHi, top, deep, used: this.frameNo });
    return t;
  }

  /** Per frame: sway; when the view has changed, re-cull and rebuild the instance lists. */
  update(camera, timeSec) {
    treeUniforms.uTreeTime.value = timeSec;
    this.frameNo++;
    if (!this.enabled || this.state !== 'ready') return;
    const e = camera.matrixWorld.elements, pe = camera.projectionMatrix.elements, lv = this.lastView;
    let moved = false;
    for (let k = 0; k < 16; k++) {
      if (Math.abs(e[k] - lv[k]) > 1e-3 || Math.abs(pe[k] - lv[16 + k]) > 1e-6) { moved = true; break; }
    }
    if ((!moved && !this.dirty) || this.frameNo - this.lastBuild < 3) return;
    lv.set(e, 0); lv.set(pe, 16);
    this.lastBuild = this.frameNo;
    this.dirty = false;
    this.rebuild(camera);
  }

  rebuild(camera) {
    const P = this.profile, ex = this.exag, T = TILE;
    const cam = camera.position;
    const groundY = this.terrain.elevAtXZ(cam.x, cam.z) * ex;
    const above = Math.max(0, cam.y - groundY - 30);
    for (const row of this.meshes) for (const pair of row) pair.n = 0;
    const reach = P.far * (MAX_H / REF_H); // the tallest trees are drawn this far
    this.inRange = above < reach;
    let drawn = 0, tris = 0;
    if (this.inRange) {
      this.frustum.setFromProjectionMatrix(this.mat4.multiplyMatrices(camera.projectionMatrix, camera.matrixWorldInverse));
      const rH = Math.sqrt(reach * reach - above * above);
      const i0 = Math.floor((cam.x - rH) / T), i1 = Math.floor((cam.x + rH) / T);
      const j0 = Math.floor((cam.z - rH) / T), j1 = Math.floor((cam.z + rH) / T);
      // tiles to plant, nearest first, a few per rebuild
      const todo = [];
      for (let i = i0; i <= i1; i++) {
        for (let j = j0; j <= j1; j++) {
          const dx = Math.max(i * T - cam.x, 0, cam.x - (i + 1) * T), dz = Math.max(j * T - cam.z, 0, cam.z - (j + 1) * T);
          if (dx * dx + dz * dz > rH * rH) continue;
          const key = `${i},${j}`;
          const t = this.tiles.get(key);
          if (t) { t.used = this.frameNo; this.draw(t, cam); } else todo.push([dx * dx + dz * dz, i, j, key]);
        }
      }
      todo.sort((a, b) => a[0] - b[0]);
      for (const [, i, j, key] of todo.slice(0, P.plant)) {
        const t = this.plant(i, j);
        this.tiles.set(key, t);
        this.draw(t, cam);
      }
      if (todo.length > P.plant) this.dirty = true; // more to plant next time
    }
    for (const row of this.meshes) {
      for (const pair of row) {
        pair.branches.count = pair.leaves.count = pair.n;
        if (pair.n) {
          for (const a of [pair.branches.instanceMatrix, pair.leaves.instanceColor]) {
            a.clearUpdateRanges();
            a.addUpdateRange(0, pair.n * a.itemSize);
            a.needsUpdate = true;
          }
        }
        drawn += pair.n;
        tris += pair.n * pair.tris;
      }
    }
    this.drawn = drawn;
    this.triangles = tris;
    if (this.tiles.size > 2500) this.evict();
  }

  /** Adds tile t's visible trees to the instance lists. */
  draw(t, cam) {
    if (!t.n) return;
    const P = this.profile, ex = this.exag, T = TILE;
    this.box.min.set(t.i * T - 15, t.gLo * ex - t.deep, t.j * T - 15);
    this.box.max.set((t.i + 1) * T + 15, t.gHi * ex + t.top, (t.j + 1) * T + 15);
    if (!this.frustum.intersectsBox(this.box)) return;
    const far2 = P.far * P.far, l0 = P.lod0 * P.lod0, l1 = P.lod1 * P.lod1, fade0 = P.far * 0.82;
    for (let k = 0; k < t.n; k++) {
      const x = t.x[k], z = t.z[k], y = t.g[k] * ex - t.sinkM[k];
      const dx = x - cam.x, dy = y + t.h[k] * 0.5 - cam.y, dz = z - cam.z;
      const r = REF_H / t.h[k]; // distances as for a REF_H tree: what matters is the size on screen
      const d2 = (dx * dx + dy * dy + dz * dz) * r * r;
      if (d2 >= far2) continue;
      let lod = 0, s = t.h[k];
      if (d2 >= l1) {
        const d = Math.sqrt(d2);
        const keep = Math.max(P.minKeep, Math.pow(P.lod1 / d, P.thin));
        if (t.rank[k] >= keep) continue;
        s *= Math.min(1, (keep - t.rank[k]) / 0.06) * (d > fade0 ? 1 - (d - fade0) / (P.far - fade0) : 1);
        lod = 2;
      } else if (d2 >= l0) lod = 1;
      const pair = this.meshes[t.kind[k]][lod];
      if (pair.n >= pair.capacity) this.grow(pair, pair.n + 1);
      const o = pair.n * 16, m = pair.branches.instanceMatrix.array;
      const c = Math.cos(t.rot[k]) * s, sn = Math.sin(t.rot[k]) * s;
      m[o] = c; m[o + 1] = 0; m[o + 2] = -sn; m[o + 3] = 0;
      m[o + 4] = 0; m[o + 5] = s; m[o + 6] = 0; m[o + 7] = 0;
      m[o + 8] = sn; m[o + 9] = 0; m[o + 10] = c; m[o + 11] = 0;
      m[o + 12] = x; m[o + 13] = y; m[o + 14] = z; m[o + 15] = 1;
      const tn = t.tone[k], a = LEAF_TONES[0], b = tn < 0.5 ? LEAF_TONES[1] : LEAF_TONES[2], f = Math.abs(tn - 0.5) * 2;
      const col = pair.leaves.instanceColor.array, oc = pair.n * 3;
      col[oc] = a.r + (b.r - a.r) * f; col[oc + 1] = a.g + (b.g - a.g) * f; col[oc + 2] = a.b + (b.b - a.b) * f;
      pair.n++;
    }
  }

  evict() {
    const old = [...this.tiles.values()].sort((a, b) => a.used - b.used);
    for (const t of old.slice(0, this.tiles.size - 1800)) this.tiles.delete(`${t.i},${t.j}`);
  }

  stats() {
    return { state: this.state, enabled: this.enabled, inRange: this.inRange, drawn: this.drawn, triangles: this.triangles, tiles: this.tiles.size };
  }
}
