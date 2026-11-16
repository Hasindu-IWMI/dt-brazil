// Building materials, after the Kelani WebTwin (src/buildings/buildingMaterial.ts).
//
// createBuildingMaterial: one MeshStandardMaterial (sun, sky light, IBL reflections in glass, the terrain's
// real-time shadows) with a procedural facade and roof stage. Realistic style (uFacade = 1):
//   walls  storeys and window bays laid out in metres from the facade coordinates written by
//          buildingGeom.js and sized by the OSM building type; glass, sills, window grilles on
//          ground floors of houses, balcony slabs on apartment blocks, roller-door shopfronts on
//          commercial ground floors, a door on the longest wall, a coping band, rain streaks, damp
//          at the base and ground-contact occlusion
//   roofs  ceramic tile (courses and rolls), trapezoidal metal sheet, corrugated fibre-cement, or a
//          stained concrete slab
// Analytical style (uFacade = 0): plain massing coloured by WHERE THE HEIGHT COMES FROM (legend in the
// view card), so the data quality of each building is visible.
// Every pattern is anti-aliased with fwidth and fades to its mean below a few pixels. All of it is
// illustrative: window counts, paint and roof materials are not data.
//
// createShadowMaterial: the baked ground shadows. Vertices carry a cast height; the vertex shader offsets
// them away from the current sun and drapes them on the terrain mesh (heights from a texture of the
// mesh's own vertices), so shadows follow the hour and date with no rebuild. Exact on flat ground,
// approximate on slopes (the sun ray is not intersected with the slope).
import * as THREE from 'three';
import { atmo, ATMO_PARS, withAtmosphere } from './atmosphere.js';

export const SOURCE_COLOURS = { // analytical style: colour = height source (sRGB)
  2: ['#5aa9e6', 'OSM height tag'], 1: ['#7fc8a9', 'OSM storeys × 3 m'], 3: ['#e0b04a', 'Google 2.5D estimate'],
  4: ['#c58fd9', 'Microsoft estimate'], 0: ['#9a988f', 'No height data (4 m placeholder)'],
};
const srcVec = (k) => { const c = new THREE.Color(SOURCE_COLOURS[k][0]); return `vec3(${c.r.toFixed(4)}, ${c.g.toFixed(4)}, ${c.b.toFixed(4)})`; };

export function createBuildingMaterial() {
  const uniforms = { uFacade: { value: 1 } };
  const mat = new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 0.85, metalness: 0 });
  mat.onBeforeCompile = (shader) => {
    Object.assign(shader.uniforms, uniforms);
    shader.vertexShader = shader.vertexShader
      .replace('#include <common>', `#include <common>
attribute vec2 aUvF;
attribute vec4 aBld;
varying vec2 vUvF;
varying vec4 vBld;
varying vec3 vNw;`)
      .replace('#include <begin_vertex>', `#include <begin_vertex>
vUvF = aUvF;
vBld = aBld;
vNw = normal;`);
    shader.fragmentShader = shader.fragmentShader
      .replace('#include <common>', `#include <common>
uniform float uFacade;
varying vec2 vUvF;
varying vec4 vBld;
varying vec3 vNw;
float bHash(vec2 p) { p = fract(p * vec2(123.34, 456.21)); p += dot(p, p + 45.32); return fract(p.x * p.y); }
float bNoise(vec2 x) {
  vec2 i = floor(x), f = fract(x);
  vec2 u = f * f * (3.0 - 2.0 * f);
  return mix(mix(bHash(i), bHash(i + vec2(1.0, 0.0)), u.x), mix(bHash(i + vec2(0.0, 1.0)), bHash(i + vec2(1.0, 1.0)), u.x), u.y);
}`)
      .replace('vec4 diffuseColor = vec4( diffuse, opacity );', FACADE)
      .replace('#include <color_fragment>', '') // the vertex colour (sRGB paint) is already in bAlb
      .replace('#include <roughnessmap_fragment>', '#include <roughnessmap_fragment>\nroughnessFactor = bRough;')
      .replace('#include <metalnessmap_fragment>', '#include <metalnessmap_fragment>\nmetalnessFactor = bMetal;');
  };
  // withAtmosphere runs its replacements first, then calls the one above; the normal hook perturbs
  // roof normals for corrugation and tile rolls
  withAtmosphere(mat, {
    key: 'building-v1',
    normal: `if (abs(bDN.x) > 0.0) {
  vec3 n0 = normalize(vNw);
  vec3 T = n0.y > 0.99 ? vec3(1.0, 0.0, 0.0) : normalize(vec3(-n0.z, 0.0, n0.x));
  normal = normalize((viewMatrix * vec4(normalize(n0 + T * bDN.x), 0.0)).xyz);
}`,
  });
  return { material: mat, uniforms };
}

const FACADE = /* glsl */ `
float bCls = floor(mod(vBld.x + 0.01, 16.0));
float bRoofMat = floor(mod(vBld.x / 16.0 + 0.001, 4.0));
float bSrc = floor(vBld.x / 64.0 + 0.001);
float bSeed = vBld.y;
float bTop = vBld.z;
float bDoor = vBld.w;
vec3 bAlb = pow(vColor.rgb, vec3(2.2));   // palette is sRGB
float bRough = 0.88, bMetal = 0.0;
vec2 bDN = vec2(0.0);
bool bWall = vNw.y < 0.35 && vNw.y > -0.5;
bool bSoffit = vNw.y <= -0.5;
if (uFacade < 0.5) {
  // analytical: massing coloured by height source, lighter roofs, darker towards the ground
  vec3 sc = bSrc > 3.5 ? ${srcVec(4)} : bSrc > 2.5 ? ${srcVec(3)} : bSrc > 1.5 ? ${srcVec(2)} : bSrc > 0.5 ? ${srcVec(1)} : ${srcVec(0)};
  bAlb = pow(sc, vec3(2.2)) * (bWall || bSoffit ? 0.78 : 1.0);
  if (bWall) bAlb *= mix(0.55, 1.0, smoothstep(-0.3, 3.0, vUvF.y));
  bRough = 0.9;
} else if (bSoffit) {
  bRough = 0.9;   // eave soffits: plain, already darkened
} else if (bWall) {
  // ------------------------------- walls -------------------------------
  float bPx = max(max(fwidth(vUvF.x), fwidth(vUvF.y)), 1e-4);   // metres per pixel
  float u = vUvF.x, v = vUvF.y;
  float house = (bCls == 0.0 || bCls == 1.0) ? 1.0 : 0.0;
  float storeyH = (bCls == 3.0 || bCls == 6.0) ? 3.6 : bCls == 4.0 ? 5.5 : bCls == 5.0 ? 6.0 : bCls == 2.0 ? 2.9 : 3.0;
  float bayW = bCls == 2.0 ? 3.2 : bCls == 3.0 ? 3.6 : bCls == 4.0 ? 6.0 : bCls == 5.0 ? 4.0 : 3.4;
  float detail = 1.0 - smoothstep(0.08, 0.35, bPx);
  float fy = mod(v, storeyH);
  float storey = floor(v / storeyH);
  float bu = u + bSeed * 13.7;
  float bx = mod(bu, bayW) - bayW * 0.5;
  float bayId = floor(bu / bayW);
  float winHalf = bCls == 3.0 ? bayW * 0.38 : bCls == 4.0 ? bayW * 0.32 : bCls == 2.0 ? bayW * 0.3 : bCls == 5.0 ? 0.55 : 0.62;
  float sill = bCls == 3.0 ? 0.6 : bCls == 4.0 ? storeyH - 1.5 : bCls == 5.0 ? 2.2 : 1.0;
  float head = bCls == 3.0 ? storeyH - 0.55 : bCls == 4.0 ? storeyH - 0.6 : bCls == 5.0 ? 4.6 : 2.2;
  float aa = bPx * 0.75;
  float wx = 1.0 - smoothstep(winHalf - aa, winHalf + aa, abs(bx));
  float wy = smoothstep(sill - aa, sill + aa, fy) * (1.0 - smoothstep(head - aa, head + aa, fy));
  // integer inputs only: the seed is an interpolated varying whose last bits differ between pixels
  float seedI = floor(bSeed * 997.0 + 0.5);
  float rnd = bHash(vec2(mod(bayId, 211.0) * 0.731 + mod(seedI, 89.0) * 0.137, storey * 1.37 + mod(seedI, 97.0) * 0.071));
  // windows only where a whole window fits between the ground and the wall top; some bays are blank
  float sb = storey * storeyH;
  float fits = step(0.3, sb + sill) * step(sb + head + 0.02, bTop - 0.3);
  float open = step(house > 0.5 ? 0.3 : 0.14, rnd);
  float win = wx * wy * fits * open * (bCls == 8.0 || bCls == 7.0 ? 0.0 : 1.0);
  // commercial ground floors: wide openings with roller doors (portas de enrolar), about half of them down
  if (bCls == 3.0 && storey == 0.0) {
    float sw = 1.0 - smoothstep(bayW * 0.45 - aa, bayW * 0.45 + aa, abs(bx));
    float shH = smoothstep(0.0, aa, fy) * (1.0 - smoothstep(2.9 - aa, 2.9 + aa, fy));
    float shutter = step(0.5, rnd);
    float slats = 0.85 + 0.15 * sin(fy * 6.2832 / 0.1);
    bAlb = mix(bAlb, mix(vec3(0.03, 0.035, 0.04), vec3(0.42, 0.43, 0.44) * mix(1.0, slats, detail), shutter), sw * shH * fits);
    win = 0.0;
  }
  win *= detail;
  vec3 glass = vec3(0.018, 0.022, 0.028) + vec3(0.05, 0.045, 0.035) * step(0.85, rnd);   // a few curtained
  // lighter sill band under each window
  float sillB = wx * fits * open * smoothstep(sill - 0.12 - aa, sill - 0.12 + aa, fy) * (1.0 - smoothstep(sill - aa, sill + aa, fy));
  bAlb = mix(bAlb, min(bAlb * 1.12 + 0.04, vec3(1.0)), sillB * detail * (bCls == 4.0 ? 0.0 : 1.0));
  bAlb = mix(bAlb, glass, win);
  bRough = mix(bRough, 0.06, win);
  // grilles (grades) over ground-floor windows of houses
  if (house > 0.5 && storey == 0.0) {
    float bars = 1.0 - smoothstep(0.012, 0.012 + aa, abs(fract((bx + winHalf) / 0.12) - 0.5) * 0.12);
    bAlb = mix(bAlb, vec3(0.05), bars * win * (1.0 - smoothstep(0.02, 0.06, bPx)));
  }
  // balcony slabs on apartment blocks: a light band at each floor and a shaded recess above it
  if (bCls == 2.0 && storey >= 1.0) {
    float slab = (1.0 - smoothstep(0.16 - aa, 0.16 + aa, fy)) * fits;
    float recess = smoothstep(0.16, 0.2, fy) * (1.0 - smoothstep(0.55, 0.9, fy)) * (1.0 - win) * 0.25 * step(0.5, mod(bayId, 2.0));
    bAlb = mix(bAlb, vec3(0.75), slab * detail * 0.7);
    bAlb *= 1.0 - recess * detail;
  }
  // door on the longest wall
  if (bDoor >= 0.0) {
    float door = (1.0 - smoothstep(0.5 - aa, 0.5 + aa, abs(u - bDoor))) * (1.0 - smoothstep(2.1 - aa, 2.1 + aa, v)) * step(0.0, v);
    bAlb = mix(bAlb, vec3(0.07, 0.045, 0.03) + vec3(0.06, 0.05, 0.03) * bSeed, door * detail);
    bRough = mix(bRough, 0.6, door * detail);
  }
  // coping band at the wall top (inner parapet faces, flagged with door = -2, are all coping)
  bAlb *= bDoor < -1.5 ? 0.86 : 1.0 - 0.16 * smoothstep(bTop - 0.3 - aa, bTop - 0.3 + aa, v);
  // weathering: rain streaks below the top, damp at the base, uneven paint
  float n1 = bNoise(vec2(u * 2.1, v * 0.16 + bSeed * 10.0));
  float n2 = bNoise(vec2(u * 0.35, v * 0.35 + bSeed * 5.0));
  float streak = smoothstep(0.55, 0.95, n1) * (0.3 + 0.7 * smoothstep(bTop - 3.5, bTop, v)) * mix(1.0, n2, 0.5);
  float damp = 1.0 - smoothstep(0.0, 0.7 + 0.6 * n2, v);
  float grime = clamp(streak * 0.25 + damp * 0.28, 0.0, 0.5) * (0.5 + 0.8 * bSeed);
  bAlb *= 1.0 - grime * (1.0 - win);
  bAlb = mix(bAlb, bAlb * vec3(0.8, 0.82, 0.74), damp * 0.4);
  bAlb *= 0.93 + 0.14 * n2;
  // ground-contact occlusion
  bAlb *= mix(0.55, 1.0, smoothstep(-0.3, 2.4, v));
} else {
  // ------------------------------- roofs -------------------------------
  float bPx = max(max(fwidth(vUvF.x), fwidth(vUvF.y)), 1e-4);
  vec2 r = vUvF;
  if (bRoofMat == 1.0) {
    // ceramic tiles: courses every 0.36 m up the slope, rolls every 0.21 m
    float k = 1.0 - smoothstep(0.03, 0.12, bPx);
    float roll = sin(r.x * 6.2832 / 0.21);
    float course = smoothstep(0.0, 0.08, fract(r.y / 0.36));
    bAlb *= mix(1.0, (0.8 + 0.2 * (0.5 + 0.5 * roll)) * (0.74 + 0.26 * course), k);
    bDN = vec2(cos(r.x * 6.2832 / 0.21) * 0.35 * k, 0.0);
    bRough = 0.74;
    float age = bNoise(r * 0.45 + bSeed * 20.0);
    bAlb *= 1.0 - 0.32 * smoothstep(0.45, 0.95, age);   // blackening and lichen
    bAlb = mix(bAlb, bAlb * vec3(0.8, 0.86, 0.7), 0.4 * smoothstep(0.7, 0.98, bNoise(r * 0.9 + 7.0)));
  } else if (bRoofMat == 2.0) {
    // trapezoidal metal sheet (galvalume), 0.25 m pitch
    float k = 1.0 - smoothstep(0.02, 0.08, bPx);
    float ph = fract(r.x / 0.25);
    float rib = smoothstep(0.0, 0.08, ph) * (1.0 - smoothstep(0.22, 0.3, ph));
    bDN = vec2((smoothstep(0.0, 0.08, ph) - smoothstep(0.22, 0.3, ph)) * 0.6 * k, 0.0);
    bAlb *= mix(1.0, 0.92 + 0.12 * rib, k);
    bRough = 0.38;
    bMetal = 0.55;
    bAlb = mix(bAlb, bAlb * vec3(0.78, 0.64, 0.5), 0.45 * smoothstep(0.66, 0.97, bNoise(r * 0.3 + bSeed * 30.0)));
  } else if (bRoofMat == 3.0) {
    // corrugated fibre-cement, 177 mm waves; dark streaks of lichen and dirt
    float k = 1.0 - smoothstep(0.015, 0.06, bPx);
    bDN = vec2(cos(r.x * 6.2832 / 0.177) * 0.45 * k, 0.0);
    bAlb *= mix(1.0, 0.9 + 0.1 * sin(r.x * 6.2832 / 0.177), k);
    bRough = 0.86;
    bAlb *= 1.0 - 0.3 * smoothstep(0.5, 0.95, bNoise(vec2(r.x * 0.5, r.y * 0.12) + bSeed * 30.0));
  } else {
    // concrete slab: stains and ponding marks
    float st = bNoise(r * 0.22 + bSeed * 40.0) * 0.6 + bNoise(r * 1.3) * 0.4;
    bAlb *= 0.72 + 0.38 * st;
    bAlb = mix(bAlb, bAlb * 0.55, smoothstep(0.7, 0.95, bNoise(r * 0.12 + 3.0)) * 0.6);
    bRough = 0.9;
  }
}
vec4 diffuseColor = vec4(bAlb, opacity);
`;

/** Height of the drawn terrain mesh at a scene point (x, z): the same triangles as terrain.js. */
const MESH_HEIGHT = /* glsl */ `
uniform sampler2D tHgt;
uniform vec4 uGrid;   // fx = x * uGrid.x + uGrid.y, fy = z * uGrid.z + uGrid.w (mesh vertex units)
uniform vec2 uGridN;  // mesh vertices across, down
float meshH(vec2 xz) {
  vec2 g = clamp(vec2(xz.x * uGrid.x + uGrid.y, xz.y * uGrid.z + uGrid.w), vec2(0.0), uGridN - 1.001);
  ivec2 i0 = ivec2(floor(g));
  vec2 f = g - vec2(i0);
  float a = texelFetch(tHgt, i0, 0).r;
  float b = texelFetch(tHgt, i0 + ivec2(1, 0), 0).r;
  float d = texelFetch(tHgt, i0 + ivec2(0, 1), 0).r;
  float e = texelFetch(tHgt, i0 + ivec2(1, 1), 0).r;
  // each mesh cell is split along b-d into the triangles (a, d, b) and (b, d, e)
  return f.x + f.y <= 1.0 ? a + (b - a) * f.x + (d - a) * f.y : e + (d - e) * (1.0 - f.x) + (b - e) * (1.0 - f.y);
}`;

/**
 * Ground shadow (halo = false) or contact-occlusion halo (halo = true). `grid` = { texture, uGrid, uGridN }
 * from BuildingLayer. Sun shadows write the stencil so overlapping shadows darken a pixel only once.
 */
export function createShadowMaterial(grid, halo) {
  const uniforms = { ...atmo, tHgt: { value: grid.texture }, uGrid: { value: grid.uGrid }, uGridN: { value: grid.uGridN }, uStrength: { value: 0.35 } };
  const m = new THREE.ShaderMaterial({
    uniforms,
    vertexShader: /* glsl */ `
attribute float aH;   // shadows: cast height (0 on the footprint); halos: occlusion weight
uniform vec3 uSunDir;
uniform float uExag;
varying float vA;
varying vec3 vAtmoWP;
${MESH_HEIGHT}
void main() {
  vec4 wp = modelMatrix * vec4(position, 1.0);
  float el = max(uSunDir.y, 0.1045);   // sun elevation clamped to 6 degrees
  ${halo ? '' : 'wp.xz -= uSunDir.xz / el * aH;   // away from the sun by height / tan(elevation)'}
  wp.y = meshH(wp.xz) * uExag + 0.3;
  vA = ${halo ? 'aH' : '1.0'};
  vAtmoWP = wp.xyz;
  gl_Position = projectionMatrix * viewMatrix * wp;
}`,
    fragmentShader: /* glsl */ `
${ATMO_PARS}
uniform float uStrength;
varying float vA;
void main() {
  // shadowed ground = ground x (1 - a); with haze the fog colour stays (blend: src * a + dst * (1 - a))
  gl_FragColor = vec4(atmoFog(vec3(0.0), vAtmoWP), uStrength * vA);
  #include <tonemapping_fragment>
  #include <colorspace_fragment>
}`,
    transparent: true, depthWrite: false, side: THREE.DoubleSide,
    polygonOffset: true, polygonOffsetFactor: -2, polygonOffsetUnits: -4,
  });
  if (!halo) {
    m.stencilWrite = true;
    m.stencilRef = 1;
    m.stencilFunc = THREE.NotEqualStencilFunc;
    m.stencilZPass = THREE.ReplaceStencilOp;
  }
  return m;
}
