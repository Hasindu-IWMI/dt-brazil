// Sky, sun, ambient light, image-based lighting and height haze for the REALISTIC style.
// Approach after the Kelani WebTwin (src/env/atmosphere.ts, src/core/Environment.ts):
//  - the sun is placed by a solar ephemeris for the scene centre at the display time;
//  - three's Preetham Sky is scaled into the scene's exposure (SKY_SCALE);
//  - the haze takes its colour from a CPU copy of the same sky model at the horizon, so the
//    terrain meets the sky without a seam.
// Everything here is DISPLAY ONLY. Haze presets are looks, not observations.
import * as THREE from 'three';
import { Sky } from 'three/addons/objects/Sky.js';
import { solarPosition, sunVector } from './sun.js';

// Sky.js output scale that puts the sky into the same exposure as the sun- and sky-lit ground.
// three r170's Sky applies a gamma before output (Kelani's r186 value of 0.045 does not carry
// over); 0.24 gives a horizon about 2-3x as bright as sunlit pasture, as in a clear dry-season sky.
export const SKY_SCALE = 0.24;

export const atmo = {
  uSunDir: { value: new THREE.Vector3(0, 1, 0) },
  uFogCol: { value: new THREE.Color(0.7, 0.78, 0.86) },
  uFogSunCol: { value: new THREE.Color(1, 0.9, 0.75) },
  uFogA: { value: 6.5e-5 }, // extinction near sea level (1/m)
  uFogB: { value: 1 / 2500 }, // its exponential falloff with height (1/m)
  uExag: { value: 1 },
  uFogOn: { value: 1 },
  uTime: { value: 0 },
};

export const ATMO_PARS = /* glsl */ `
uniform vec3 uSunDir;
uniform vec3 uFogCol;
uniform vec3 uFogSunCol;
uniform float uFogA;
uniform float uFogB;
uniform float uExag;
uniform float uFogOn;
uniform float uTime;
varying vec3 vAtmoWP;
// exponential height fog with in-scattering towards the sun (analytic integral along the ray);
// heights are taken without the display exaggeration
vec3 atmoFog(vec3 col, vec3 wp) {
  if (uFogOn < 0.5) return col;
  float ex = max(uExag, 1e-3);
  vec3 c = vec3(cameraPosition.x, cameraPosition.y / ex, cameraPosition.z);
  vec3 p = vec3(wp.x, wp.y / ex, wp.z);
  vec3 rd = p - c;
  float dist = length(rd);
  rd /= max(dist, 1e-3);
  float b = uFogB;
  float camH = max(c.y, 0.0);
  float amount = abs(rd.y) > 1e-4
    ? uFogA * (exp(-b * camH) - exp(-b * max(camH + rd.y * dist, 0.0))) / (b * rd.y)
    : uFogA * exp(-b * camH) * dist;
  float f = 1.0 - exp(-max(amount, 0.0));
  float glow = pow(max(dot(rd, uSunDir), 0.0), 6.0);
  return mix(col, mix(uFogCol, uFogSunCol, glow), f);
}
`;

/** Add the height haze to a built-in material, applied in linear light before tone mapping. */
export function withAtmosphere(material, extra = {}) {
  const prev = material.onBeforeCompile;
  material.onBeforeCompile = (shader, renderer) => {
    Object.assign(shader.uniforms, atmo);
    shader.vertexShader = 'varying vec3 vAtmoWP;\n' + shader.vertexShader.replace('#include <project_vertex>',
      '#include <project_vertex>\n  #ifdef USE_INSTANCING\n  vAtmoWP = (modelMatrix * instanceMatrix * vec4(transformed, 1.0)).xyz;\n'
      + '  #else\n  vAtmoWP = (modelMatrix * vec4(transformed, 1.0)).xyz;\n  #endif');
    shader.fragmentShader = ATMO_PARS + (extra.fragmentPars ?? '') + shader.fragmentShader
      .replace('#include <normal_fragment_maps>', '#include <normal_fragment_maps>\n' + (extra.normal ?? ''))
      .replace('#include <tonemapping_fragment>', 'gl_FragColor.rgb = atmoFog(gl_FragColor.rgb, vAtmoWP);\n#include <tonemapping_fragment>');
    prev?.(shader, renderer);
  };
  material.customProgramCacheKey = () => 'atmo' + (extra.key ?? '');
  return material;
}

// ---- CPU port of three r170's Preetham Sky (examples/jsm/objects/Sky.js), for the haze colour.
const TOTAL_RAYLEIGH = [5.804542996261093e-6, 1.3562911419845635e-5, 3.0265902468824876e-5];
const MIE_CONST = [1.8399918514433978e14, 2.7798023919660528e14, 4.0790479543861094e14];
function skyRadiance(dir, sun, p, out) {
  const pi = Math.PI;
  const zc = Math.min(1, Math.max(-1, sun.y));
  const sunE = 1000 * Math.max(0, 1 - Math.exp(-((1.6110731556870734 - Math.acos(zc)) / 1.5)));
  const sunfade = 1 - Math.min(1, Math.max(0, 1 - Math.exp(sun.y / 450000)));
  const rc = p.rayleigh - (1 - sunfade);
  const c = 0.2 * p.turbidity * 10e-18;
  const betaR = TOTAL_RAYLEIGH.map((v) => v * rc);
  const betaM = MIE_CONST.map((v) => 0.434 * c * v * p.mieCoefficient);
  const zen = Math.acos(Math.max(0, dir.y));
  const inv = 1 / (Math.cos(zen) + 0.15 * Math.pow(93.885 - (zen * 180) / pi, -1.253));
  const cosT = dir.dot(sun);
  const rPhase = (3 / (16 * pi)) * (1 + Math.pow(cosT * 0.5 + 0.5, 2));
  const g = p.mieDirectionalG;
  const mPhase = (1 / (4 * pi)) * ((1 - g * g) / Math.pow(1 - 2 * g * cosT + g * g, 1.5));
  const k = Math.min(1, Math.max(0, Math.pow(1 - sun.y, 5)));
  const res = [0, 0, 0];
  for (let i = 0; i < 3; i++) {
    const Fex = Math.exp(-(betaR[i] * 8.4e3 * inv + betaM[i] * 1.25e3 * inv));
    const ratio = (betaR[i] * rPhase + betaM[i] * mPhase) / (betaR[i] + betaM[i]);
    let Lin = Math.pow(sunE * ratio * (1 - Fex), 1.5);
    Lin *= 1 - k + k * Math.pow(sunE * ratio * Fex, 0.5);
    const tex = (Lin + 0.1 * Fex) * 0.04 + [0, 0.0003, 0.00075][i];
    res[i] = Math.pow(tex, 1 / (1.2 + 1.2 * sunfade)) * SKY_SCALE; // r170 applies this gamma, then we scale
  }
  return out.setRGB(res[0], res[1], res[2]);
}
function horizonColours(sun, p) {
  const mean = new THREE.Color(0, 0, 0);
  const tmp = new THREE.Color();
  const d = new THREE.Vector3();
  const el = 0.035;
  for (let i = 0; i < 16; i++) {
    const a = (i / 16) * Math.PI * 2;
    skyRadiance(d.set(Math.cos(a) * Math.cos(el), Math.sin(el), Math.sin(a) * Math.cos(el)), sun, p, tmp);
    mean.r += tmp.r / 16; mean.g += tmp.g / 16; mean.b += tmp.b / 16;
  }
  const hs = new THREE.Vector3(sun.x, 0, sun.z);
  if (hs.lengthSq() < 1e-6) hs.set(1, 0, 0);
  hs.normalize();
  return { mean, sunSide: skyRadiance(d.set(hs.x * Math.cos(el), Math.sin(el), hs.z * Math.cos(el)), sun, p, new THREE.Color()) };
}

export const HAZE = {
  clear: { label: 'Clear', turbidity: 3.2, rayleigh: 1.2, visibilityKm: 70, sun: 3.0, hemi: 0.8 },
  hazy: { label: 'Hazy (dry-season smoke)', turbidity: 9, rayleigh: 2.2, visibilityKm: 22, sun: 2.3, hemi: 1.0 },
};

export class Atmosphere {
  constructor(scene, renderer, latDeg, lonDeg) {
    this.scene = scene;
    this.lat = latDeg;
    this.lon = lonDeg;
    this.sun = new THREE.DirectionalLight(0xfff4e5, 3);
    this.hemi = new THREE.HemisphereLight(0xcfe3ff, 0x5b5446, 0.8);
    this.sunDir = new THREE.Vector3(0, 1, 0);
    this.sunPos = { azimuth: 0, elevation: 90 };
    this.haze = 'clear';
    this.time = new Date();
    this.enabled = true;
    this.sky = new Sky();
    this.sky.scale.setScalar(900000);
    this.sky.frustumCulled = false;
    this.skyScene = new THREE.Scene();
    this.skyClone = new Sky();
    this.skyClone.scale.setScalar(1000);
    this.skyScene.add(this.skyClone);
    for (const s of [this.sky, this.skyClone]) {
      s.material.uniforms.skyScale = { value: SKY_SCALE };
      s.material.uniforms.mieCoefficient.value = 0.004;
      s.material.uniforms.mieDirectionalG.value = 0.82;
      s.material.fragmentShader = 'uniform float skyScale;\n' + s.material.fragmentShader
        .replace('gl_FragColor = vec4( retColor, 1.0 );', 'gl_FragColor = vec4( retColor * skyScale, 1.0 );');
      s.material.needsUpdate = true;
    }
    // terrain shadows: one orthographic shadow map over the whole window (about 27 m texels)
    this.sun.shadow.mapSize.set(4096, 4096);
    const sc = this.sun.shadow.camera;
    sc.left = -58000; sc.right = 58000; sc.top = 58000; sc.bottom = -58000;
    sc.near = 1000; sc.far = 260000;
    sc.updateProjectionMatrix();
    this.sun.shadow.bias = -0.0004;
    this.sun.shadow.normalBias = 40;
    this.pmrem = new THREE.PMREMGenerator(renderer);
    this.envRT = null;
    this.envTimer = null;
    this.lastEnvDir = new THREE.Vector3();
    scene.add(this.sky, this.sun, this.sun.target, this.hemi);
  }

  set({ time, haze } = {}) {
    if (time) this.time = time;
    if (haze) this.haze = haze;
    this.apply();
  }

  setEnabled(on) {
    this.enabled = on;
    this.sky.visible = on;
    atmo.uFogOn.value = on ? 1 : 0;
    this.apply();
  }

  apply() {
    const w = HAZE[this.haze];
    this.sunPos = solarPosition(this.time, this.lat, this.lon);
    if (!this.enabled) { // analytical style: a fixed, neutral light from the north-west
      this.sunDir.set(-0.45, 0.75, -0.5).normalize();
      this.sun.color.set(0xffffff); this.sun.intensity = 2.2;
      this.hemi.color.set(0xffffff); this.hemi.groundColor.set(0x2a2a26); this.hemi.intensity = 1.1;
      this.sun.position.copy(this.sunDir).multiplyScalar(1e5);
      this.scene.environment = null;
      return;
    }
    // below the horizon the scene would be black; light it from a low twilight sun (the panel shows the real elevation)
    sunVector({ azimuth: this.sunPos.azimuth, elevation: Math.max(this.sunPos.elevation, 1.5) }, this.sunDir);
    atmo.uSunDir.value.copy(this.sunDir);
    const p = { turbidity: w.turbidity, rayleigh: w.rayleigh, mieCoefficient: 0.004, mieDirectionalG: 0.82 };
    for (const s of [this.sky, this.skyClone]) {
      const u = s.material.uniforms;
      u.turbidity.value = p.turbidity;
      u.rayleigh.value = p.rayleigh;
      u.sunPosition.value.copy(this.sunDir);
    }
    const el = this.sunPos.elevation;
    const warm = THREE.MathUtils.smoothstep(el, 2, 35);
    const day = THREE.MathUtils.smoothstep(el, -2, 8);
    this.sun.color.setRGB(1.0, 0.62 + 0.34 * warm, 0.4 + 0.5 * warm);
    this.sun.intensity = w.sun * (0.2 + 0.8 * day);
    this.hemi.color.setRGB(0.81, 0.89, 1.0);
    this.hemi.groundColor.setRGB(0.36, 0.33, 0.27);
    this.hemi.intensity = w.hemi * (0.35 + 0.65 * day);
    this.sun.position.copy(this.sunDir).multiplyScalar(1.3e5);
    atmo.uFogA.value = 3.912 / (w.visibilityKm * 1000); // Koschmieder
    const { mean, sunSide } = horizonColours(this.sunDir, p);
    atmo.uFogCol.value.copy(mean);
    atmo.uFogSunCol.value.copy(sunSide);
    this.scheduleEnv();
  }

  scheduleEnv() {
    if (this.envRT && this.lastEnvDir.angleTo(this.sunDir) < 0.01 && this.envHaze === this.haze) {
      this.scene.environment = this.envRT.texture;
      return;
    }
    if (this.envTimer !== null) return;
    // debounce: playback and slider drags must not re-filter the environment map every frame
    this.envTimer = setTimeout(() => {
      this.envTimer = null;
      const old = this.envRT;
      this.envRT = this.pmrem.fromScene(this.skyScene, 0, 0.1, 2000);
      this.lastEnvDir.copy(this.sunDir);
      this.envHaze = this.haze;
      if (this.enabled) this.scene.environment = this.envRT.texture;
      old?.dispose();
    }, this.envRT ? 150 : 0);
  }

  /** per frame: haze and exaggeration uniforms, water clock */
  update(exag, dt) {
    atmo.uExag.value = exag;
    atmo.uTime.value += dt;
  }
}
