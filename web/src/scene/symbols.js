// Flat map symbols drawn at a fixed size on screen, so a marker looks the same at any zoom and never
// towers over a town. Shapes: a dot, a ring and a diamond, each with a light rim and a dark edge so it
// reads on imagery; an optional pulse (an expanding ring) marks a live state. Symbols are drawn whole,
// over the ground (a depth test would cut them on the slope they stand on); a symbol whose ground point
// is hidden behind a hill is switched off by occlude(), which the viewer runs every few frames.
import * as THREE from 'three';

export const SHAPE = { dot: 0, ring: 1, diamond: 2 };
/** Shared by every symbol material: the time (s) and the renderer's pixel ratio; set by the viewer. */
export const SYMBOL_UNIFORMS = { uTime: { value: 0 }, uPx: { value: 1 } };

const VERT = /* glsl */ `
attribute float aSize;
attribute vec3 aTint;
attribute float aAlpha;
attribute float aShape;
attribute float aPulse;
attribute float aPhase;
attribute float aVis;
uniform float uTime;
uniform float uPx;
uniform float uPulse;
varying vec3 vTint;
varying float vAlpha;
varying float vShape;
varying float vSize;
void main() {
  gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
  float s = aSize;
  float a = aAlpha * aVis;
  float shape = aShape;
  if (uPulse > 0.5) {
    float f = fract(uTime * aPulse + aPhase);
    s = aSize * (1.0 + 1.1 * f);
    a = aPulse > 0.0 ? aAlpha * aVis * 0.8 * (1.0 - f) : 0.0;
    shape = 3.0;
  }
  vSize = s;
  gl_PointSize = s * uPx;
  vTint = aTint;
  vAlpha = a;
  vShape = shape;
}`;

const FRAG = /* glsl */ `
varying vec3 vTint;
varying float vAlpha;
varying float vShape;
varying float vSize;
void main() {
  if (vAlpha <= 0.0) discard;
  float R = vSize * 0.5;
  vec2 p = (gl_PointCoord * 2.0 - 1.0) * R; // pixels from the centre
  // distance inside the outline, in pixels
  float inside = vShape > 1.5 && vShape < 2.5 ? (R - abs(p.x) - abs(p.y)) * 0.70711 : R - length(p);
  if (inside < 0.0) discard;
  vec3 dark = vec3(0.012);
  vec3 light = vec3(0.92);
  vec3 col;
  float a;
  if (vShape < 0.5 || (vShape > 1.5 && vShape < 2.5)) { // dot or diamond: tint, light rim, dark edge
    float e = min(1.0, R * 0.22);
    float w = min(1.6, R * 0.3);
    col = mix(dark, light, smoothstep(e - 0.5, e + 0.5, inside));
    float fill = smoothstep(e + w - 0.5, e + w + 0.5, inside);
    col = mix(col, vTint, fill);
    a = smoothstep(0.0, 1.0, inside) * mix(1.0, vAlpha, fill);
  } else if (vShape < 1.5) { // ring: a tinted band with dark edges, faint tint inside
    float T = clamp(R * 0.22, 2.0, 3.5);
    float c0 = 1.0 + T * 0.5;
    float d = abs(inside - c0);
    float band = 1.0 - smoothstep(T * 0.5 - 0.5, T * 0.5 + 0.5, d);
    float edge = 1.0 - smoothstep(T * 0.5 + 0.4, T * 0.5 + 1.4, d);
    float centre = smoothstep(c0, c0 + 1.0, inside);
    col = mix(dark, vTint, band);
    a = max(edge * vAlpha, centre * 0.16 * vAlpha);
    col = mix(col, vTint, centre * (1.0 - edge));
    a *= smoothstep(0.0, 1.0, inside);
  } else { // pulse: a thin ring
    float d = abs(inside - 1.5);
    col = vTint;
    a = (1.0 - smoothstep(0.6, 1.6, d)) * vAlpha;
  }
  gl_FragColor = vec4(col, a);
  #include <colorspace_fragment>
}`;

function material(pulse) {
  return new THREE.ShaderMaterial({
    uniforms: { ...SYMBOL_UNIFORMS, uPulse: { value: pulse ? 1 : 0 } },
    vertexShader: VERT, fragmentShader: FRAG,
    transparent: true, depthWrite: false, depthTest: false,
  });
}

/** n symbols in one draw call (two with pulses). Set each with set(), then commit(). */
export class Symbols {
  constructor(n, { pulse = false, order = 6 } = {}) {
    this.n = n;
    const g = new THREE.BufferGeometry();
    const attr = (name, k) => {
      const a = new THREE.BufferAttribute(new Float32Array(Math.max(1, n) * k), k);
      a.setUsage(THREE.DynamicDrawUsage);
      g.setAttribute(name, a);
      return a;
    };
    this.pos = attr('position', 3);
    this.size = attr('aSize', 1);
    this.tint = attr('aTint', 3);
    this.alpha = attr('aAlpha', 1);
    this.shape = attr('aShape', 1);
    this.pulse = attr('aPulse', 1);
    const phase = attr('aPhase', 1);
    for (let k = 0; k < n; k++) phase.setX(k, Math.random());
    this.vis = attr('aVis', 1);
    this.vis.array.fill(1);
    g.setDrawRange(0, n);
    this.group = new THREE.Group();
    this.points = new THREE.Points(g, material(false));
    this.points.frustumCulled = false;
    this.points.renderOrder = order;
    this.group.add(this.points);
    if (pulse) {
      this.pulsePoints = new THREE.Points(g, material(true));
      this.pulsePoints.frustumCulled = false;
      this.pulsePoints.renderOrder = order - 1;
      this.group.add(this.pulsePoints);
    }
    this._c = new THREE.Color();
  }

  setPos(k, x, y, z) { this.pos.setXYZ(k, x, y, z); }
  /** size in CSS pixels; color anything THREE.Color takes; alpha scales the fill; pulse in cycles per second (0: none) */
  set(k, { size, color, alpha = 1, shape = SHAPE.dot, pulse = 0 }) {
    this.size.setX(k, size);
    this._c.set(color);
    this.tint.setXYZ(k, this._c.r, this._c.g, this._c.b);
    this.alpha.setX(k, alpha);
    this.shape.setX(k, shape);
    this.pulse.setX(k, pulse);
  }
  hide(k) { this.alpha.setX(k, 0); this.pulse.setX(k, 0); }
  /** Switch off the symbols whose ground point hidden(pos) says the terrain hides. */
  occlude(hidden) {
    if (!this.group.visible || this.group.parent?.visible === false) return;
    const v = new THREE.Vector3();
    let changed = false;
    for (let k = 0; k < this.n; k++) {
      const on = hidden(v.fromBufferAttribute(this.pos, k)) ? 0 : 1;
      if (this.vis.getX(k) !== on) { this.vis.setX(k, on); changed = true; }
    }
    if (changed) this.vis.needsUpdate = true;
  }
  commit() {
    for (const a of [this.pos, this.size, this.tint, this.alpha, this.shape, this.pulse]) a.needsUpdate = true;
  }

  /** Symbols under a screen point: [{k, dpx, pos}], nearest first. ndc: the pointer in normalised
   * device coordinates; w, h: the canvas size in CSS pixels. Hiding by terrain is the caller's test. */
  hits(ndc, camera, w, h, slack = 3) {
    const out = [];
    if (!this.group.visible || this.group.parent?.visible === false) return out;
    const v = new THREE.Vector3();
    for (let k = 0; k < this.n; k++) {
      if (this.alpha.getX(k) <= 0 || this.size.getX(k) <= 0 || this.vis.getX(k) <= 0) continue;
      v.fromBufferAttribute(this.pos, k).project(camera);
      if (v.z > 1 || v.z < -1) continue;
      const dpx = Math.hypot(((v.x - ndc.x) * w) / 2, ((v.y - ndc.y) * h) / 2);
      if (dpx <= this.size.getX(k) / 2 + slack) out.push({ k, dpx, pos: new THREE.Vector3().fromBufferAttribute(this.pos, k) });
    }
    return out.sort((a, b) => a.dpx - b.dpx);
  }
}

/** Anchor a CSS2D label just above a symbol of the given size (pixels). */
export function pinLabel(label, size) {
  label.center.set(0.5, 1);
  label.element.style.marginTop = `${-Math.round(size / 2 + 4)}px`;
}
