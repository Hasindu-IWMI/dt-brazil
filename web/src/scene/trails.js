// Material for flow particles (rivers, modelled flood water): round soft dots of a fixed size on
// screen, with per-point colour and alpha so a particle can draw a fading tail. Depth-tested, so the
// hills hide them; each point is pulled 0.5% of its distance toward the camera, which keeps the
// ground or water it rides on from cutting it.
import * as THREE from 'three';
import { SYMBOL_UNIFORMS } from './symbols.js';

const VERT = /* glsl */ `
attribute float aSize;
attribute float aAlpha;
attribute vec3 aTint;
uniform float uPx;
varying float vAlpha;
varying vec3 vTint;
void main() {
  vec4 mv = modelViewMatrix * vec4(position, 1.0);
  mv.xyz *= 0.995;
  gl_Position = projectionMatrix * mv;
  gl_PointSize = aSize * uPx;
  vAlpha = aAlpha;
  vTint = aTint;
}`;

const FRAG = /* glsl */ `
varying float vAlpha;
varying vec3 vTint;
void main() {
  if (vAlpha <= 0.0) discard;
  float r = length(gl_PointCoord * 2.0 - 1.0);
  float a = (1.0 - smoothstep(0.55, 1.0, r)) * vAlpha;
  if (a <= 0.0) discard;
  gl_FragColor = vec4(vTint, a);
  #include <colorspace_fragment>
}`;

export function trailMaterial() {
  return new THREE.ShaderMaterial({
    uniforms: { uPx: SYMBOL_UNIFORMS.uPx },
    vertexShader: VERT, fragmentShader: FRAG,
    transparent: true, depthWrite: false, depthTest: true,
  });
}
