// Lake surfaces for the realistic style: a smooth dielectric that reflects the prefiltered sky
// (Fresnel comes from the PBR model), with procedural ripples that fade with distance so the far
// water does not shimmer. DISPLAY ONLY: the outline is the fixed OpenStreetMap outline and the
// height is the DEM's own lake surface, NOT the observed level on the replay date (no bathymetry
// is public, and the level datum is not tied to the DEM's).
import * as THREE from 'three';
import { withAtmosphere } from './atmosphere.js';

const RIPPLE = /* glsl */ `
  {
    // sum of a few travelling waves; gradient in world xz, tilted into view space
    vec2 p = vAtmoWP.xz;
    float t = uTime;
    vec2 g = vec2(0.0);
    vec2 d1 = normalize(vec2(0.8, 0.6)), d2 = normalize(vec2(-0.5, 0.9)), d3 = normalize(vec2(0.95, -0.3)), d4 = normalize(vec2(-0.7, -0.7));
    g += d1 * cos(dot(d1, p) * 0.21 + t * 1.3) * 0.21 * 0.10;
    g += d2 * cos(dot(d2, p) * 0.37 + t * 1.7) * 0.37 * 0.05;
    g += d3 * cos(dot(d3, p) * 0.071 + t * 0.8) * 0.071 * 0.30;
    g += d4 * cos(dot(d4, p) * 0.63 + t * 2.1) * 0.63 * 0.025;
    float dist = length(vAtmoWP - cameraPosition);
    g *= 1.0 / (1.0 + dist / 6000.0);
    vec3 nw = normalize(vec3(-g.x, 1.0, -g.y));
    normal = normalize((viewMatrix * vec4(nw, 0.0)).xyz);
  }
`;

export function realisticWaterMaterial() {
  return withAtmosphere(new THREE.MeshStandardMaterial({
    color: 0x17323a, roughness: 0.07, metalness: 0, envMapIntensity: 1.0,
    polygonOffset: true, polygonOffsetFactor: -2, polygonOffsetUnits: -4,
  }), { normal: RIPPLE, key: 'water' });
}

/** Analytical style: flat fill coloured by observed storage, drawn over the terrain. */
export function analyticalWaterMaterial(color) {
  return new THREE.MeshBasicMaterial({ color, transparent: true, opacity: 0.92, depthTest: false });
}
