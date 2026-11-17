// Rain, river and tunnel records drawn on the terrain (data: public/data/layers.json, built by
// pipeline/viewer_layers.py). Encodings, all for the replayed date:
//   rain gauges   a dot per gauge whose AREA on screen is proportional to that day's audited rain
//                 (observed), darker blue for more; small and pale on a dry day, grey with no record
//   flow stations a ring whose AREA on screen is proportional to the day's mean discharge
//                 (observed), with a slow pulse; grey and small when there is no record
//   Rain dots and flow rings are flat symbols of a fixed size on screen (scene/symbols.js).
//   tunnels       an arc between the two ends. Measured tunnels carry particles whose number
//                 and speed follow the measured flow; the others are grey and dashed. Arcs are
//                 deliberately schematic: the underground alignments are not in the data.
//   catchments    the DEM catchments of the gauges above the lakes, draped on the terrain as a
//                 tint (see Terrain.setOverlay)
import * as THREE from 'three';
import { CSS2DObject } from 'three/addons/renderers/CSS2DRenderer.js';
import { Symbols, SHAPE, pinLabel } from './symbols.js';

export const COLORS = {
  rainLo: new THREE.Color(0xbfe1ff), rainHi: new THREE.Color(0x1f5fbf), noRecord: new THREE.Color(0x77756d),
  upstream: new THREE.Color(0x2bb3a3), below_dam: new THREE.Color(0x6fb2ff), tunnel: new THREE.Color(0xb48cff),
  overlay: [43, 179, 163],
};
// symbol diameters in CSS pixels: diameter = k * sqrt(value), so AREA is proportional to the value
// (between a floor, so a small value stays visible, and a cap)
const RAIN_PX_PER_SQRT_MM = 4.5; // 80 mm reaches the 40 px cap
const RING_PX_PER_SQRT_Q = 6.5; // 55 m3/s reaches the 48 px cap
const rainPx = (mm) => Math.min(40, Math.max(7, RAIN_PX_PER_SQRT_MM * Math.sqrt(mm)));
const ringPx = (q) => Math.min(48, Math.max(9, RING_PX_PER_SQRT_Q * Math.sqrt(Math.max(q, 0))));

const dayIndex = (dates, iso) => dates.indexOf(iso);
/** value of a contiguous series {first, values} on dates[i], or null */
export function valueOn(series, values, dates, i, offsetCache) {
  if (!series || !series.first) return null;
  let off = offsetCache.get(series);
  if (off === undefined) { off = dayIndex(dates, series.first); offsetCache.set(series, off); }
  const j = i - off;
  return j < 0 || j >= values.length ? null : values[j];
}

export class RecordLayers {
  constructor({ data, dates, frame, surfaceAt, inBox }) {
    Object.assign(this, { data, dates, frame, surfaceAt, inBox });
    this.off = new Map();
    this.group = new THREE.Group();
    this.rainGroup = new THREE.Group();
    this.flowGroup = new THREE.Group();
    this.tunnelGroup = new THREE.Group();
    this.group.add(this.rainGroup, this.flowGroup, this.tunnelGroup);
    this.exag = 1;
    this.index = 0;
    this.pickables = [];

    // ---- rain gauges: one dot each
    this.sites = data.rain_sites.filter((s) => inBox(s.lon, s.lat));
    this.rain = new Symbols(this.sites.length, { order: 6 });
    this.rainGroup.add(this.rain.group);

    // ---- flow stations: a ring each, pulsing while there is a record (+ a label for river gauges)
    this.stations = data.flow_stations.filter((s) => inBox(s.lon, s.lat)).map((s) => {
      let label = null;
      if (s.role !== 'tunnel') {
        const el = document.createElement('div');
        el.className = 'label label-flow';
        el.dataset.prio = s.role === 'upstream' ? '4' : '1';
        label = new CSS2DObject(el);
        this.flowGroup.add(label);
      }
      return { s, label };
    });
    this.flow = new Symbols(this.stations.length, { pulse: true, order: 7 });
    this.flowGroup.add(this.flow.group);

    // ---- tunnels
    this.tunnels = data.tunnels.map((t) => {
      const obj = { t, group: new THREE.Group() };
      const el = document.createElement('div');
      el.className = 'label label-tunnel' + (t.measured ? '' : ' unmeasured');
      el.dataset.prio = t.measured ? '4' : '2';
      obj.el = el;
      obj.label = new CSS2DObject(el);
      obj.group.add(obj.label);
      this.tunnelGroup.add(obj.group);
      return obj;
    });
    this.place(1);
  }

  /** (Re)build positions for a vertical exaggeration. */
  place(exag) {
    this.exag = exag;
    const { X, Z } = this.frame;
    this.sites.forEach((s, k) => this.rain.setPos(k, X(s.lon), this.surfaceAt(s.lon, s.lat) * exag + 2, Z(s.lat)));
    this.stations.forEach((st, k) => {
      const y = this.surfaceAt(st.s.lon, st.s.lat) * exag + 2;
      this.flow.setPos(k, X(st.s.lon), y, Z(st.s.lat));
      st.label?.position.set(X(st.s.lon), y, Z(st.s.lat));
    });
    for (const o of this.tunnels) {
      o.group.clear();
      o.group.add(o.label);
      const pa = new THREE.Vector3(X(o.t.a.lon), this.surfaceAt(o.t.a.lon, o.t.a.lat) * exag + 40, Z(o.t.a.lat));
      const pb = new THREE.Vector3(X(o.t.b.lon), this.surfaceAt(o.t.b.lon, o.t.b.lat) * exag + 40, Z(o.t.b.lat));
      const mid = pa.clone().lerp(pb, 0.5);
      mid.y = Math.max(pa.y, pb.y) + Math.max(1400, pa.distanceTo(pb) * 0.22);
      o.curve = new THREE.QuadraticBezierCurve3(pa, mid, pb);
      const pts = o.curve.getPoints(64);
      if (o.t.measured) {
        const tube = new THREE.Mesh(new THREE.TubeGeometry(o.curve, 64, 70, 8, false),
          new THREE.MeshStandardMaterial({ color: COLORS.tunnel, transparent: true, opacity: 0.35, roughness: 0.3 }));
        tube.userData = { kind: 'tunnel', tunnel: o.t };
        this.pickables.push(tube);
        o.group.add(tube);
        o.points = new THREE.Points(new THREE.BufferGeometry().setFromPoints(new Array(48).fill(0).map(() => new THREE.Vector3())),
          new THREE.PointsMaterial({ color: 0xe9ddff, size: 11, sizeAttenuation: false, transparent: true, opacity: 0.95, depthWrite: false }));
        o.points.frustumCulled = false;
        o.group.add(o.points);
      } else {
        const line = new THREE.Line(new THREE.BufferGeometry().setFromPoints(pts),
          new THREE.LineDashedMaterial({ color: 0x9b998f, dashSize: 600, gapSize: 450, transparent: true, opacity: 0.85 }));
        line.computeLineDistances();
        line.userData = { kind: 'tunnel', tunnel: o.t };
        o.group.add(line);
      }
      // a small marker at a schematic end, so the guess is visible as one
      for (const [end, p] of [[o.t.a, pa], [o.t.b, pb]]) {
        if (end.is !== 'schematic') continue;
        const mk = new THREE.Mesh(new THREE.RingGeometry(140, 200, 24).rotateX(-Math.PI / 2),
          new THREE.MeshBasicMaterial({ color: 0xd8d6cc, transparent: true, opacity: 0.8, side: THREE.DoubleSide, depthWrite: false }));
        mk.position.copy(p);
        o.group.add(mk);
      }
      o.label.position.copy(o.curve.getPoint(0.5)).add(new THREE.Vector3(0, 450, 0));
    }
    this.show(this.index);
  }

  rainOn(site, i) { return valueOn(site, site.mm, this.dates, i, this.off); }
  flowOn(st, i) { return valueOn(st, st.q, this.dates, i, this.off); }
  catchRainOn(name, i) { const r = this.data.catchment_rain[name]; return r ? valueOn(r, r.mm, this.dates, i, this.off) : null; }
  catchRainSum(name, i, days) {
    let s = 0;
    for (let k = i - days + 1; k <= i; k++) { const v = this.catchRainOn(name, k); if (v === null) return null; s += v; }
    return s;
  }
  station(id) { return this.data.flow_stations.find((s) => s.id === id); }

  /** Update every encoding to dates[i]. */
  show(i) {
    this.index = i;
    const c = new THREE.Color();
    this.sites.forEach((s, k) => {
      const v = this.rainOn(s, i);
      if (v === null) this.rain.set(k, { size: 7, color: COLORS.noRecord, alpha: 0.9 });
      else if (v <= 0) this.rain.set(k, { size: 7, color: 0xe9f3ff });
      else this.rain.set(k, { size: rainPx(v), color: c.copy(COLORS.rainLo).lerp(COLORS.rainHi, Math.min(1, v / 60)), alpha: 0.85 });
    });
    this.rain.commit();
    this.stations.forEach((st, k) => {
      const q = this.flowOn(st.s, i);
      st.q = q;
      st.px = q === null ? 9 : ringPx(q);
      this.flow.set(k, { size: st.px, color: q === null ? COLORS.noRecord : COLORS[st.s.role], shape: SHAPE.ring, pulse: q === null ? 0 : 0.35 });
      if (st.label) {
        pinLabel(st.label, st.px);
        const depth = q !== null && st.s.area_km2 ? ` · ${(q * 86.4 / st.s.area_km2).toFixed(1)} mm/day` : '';
        const name = st.s.label.replace(/ \(.*\)$/, '');
        st.label.element.innerHTML = `<b>${st.s.code}</b> <span>${name}</span><br><span>${q === null ? 'no record this day' : q.toFixed(2) + ' m³/s' + depth}</span>`;
      }
    });
    this.flow.commit();
    for (const o of this.tunnels) {
      const q = o.t.station ? this.flowOn(this.station(o.t.station), i) : null;
      o.q = q;
      o.el.innerHTML = `<b>${o.t.name}</b> <span>${!o.t.measured ? '· no public flow record' : q === null ? '· no record this day' : q.toFixed(1) + ' m³/s'}</span><br><span>${o.t.from} → ${o.t.to}</span>`;
    }
  }

  /** Per-frame animation: tunnel particles (the symbols pulse on the GPU). */
  tick(t) {
    for (const o of this.tunnels) {
      if (!o.points) continue;
      const q = o.q ?? 0;
      const n = q > 0 ? Math.min(48, Math.max(4, Math.round(q * 1.5))) : 0;
      const pos = o.points.geometry.attributes.position;
      const speed = 0.03 + 0.004 * q; // curve lengths per second
      const p = new THREE.Vector3();
      for (let k = 0; k < 48; k++) {
        if (k < n) o.curve.getPoint(((k / n) + t * speed) % 1, p); else p.set(0, -1e6, 0);
        pos.setXYZ(k, p.x, p.y, p.z);
      }
      pos.needsUpdate = true;
    }
  }

  /** Rain dots and flow rings under a screen point: [{dpx, pos, text}] (see Symbols.hits). */
  symbolHits(ndc, camera, w, h) {
    const out = [];
    if (!this.group.visible) return out;
    for (const hh of this.rain.hits(ndc, camera, w, h)) out.push({ ...hh, text: this.describeRain(this.sites[hh.k]) });
    for (const hh of this.flow.hits(ndc, camera, w, h)) out.push({ ...hh, text: this.describeFlow(this.stations[hh.k].s) });
    return out;
  }
  describeRain(s) {
    const v = this.rainOn(s, this.index);
    return `<b>${s.name}</b><br>${s.operator} · ${s.kind} gauge<br>${this.dates[this.index]}: ${v === null ? 'no record (or excluded by the audit)' : v.toFixed(1) + ' mm'}<br><i>observed, audited · day = 24 h to 07:00</i>`;
  }
  describeFlow(s) {
    const q = this.flowOn(s, this.index);
    return `<b>${s.label}</b><br>SIBH ${s.code} · ${s.role.replace('_', ' ')}<br>${this.dates[this.index]}: ${q === null ? 'no record' : q.toFixed(2) + ' m³/s, daily mean'}`
      + (s.area_km2 ? `<br>catchment ${s.area_km2} km² from the DEM (other snap rule ${s.max_rule_area_km2} km²)` : '')
      + '<br><i>observed; discharge from a rating curve</i>';
  }

  /** Text for the hover tip over a tunnel, or null. */
  describe(hit) {
    const o = hit.object;
    if (o.userData.kind === 'tunnel') {
      const t = o.userData.tunnel;
      return `<b>${t.name}</b>: ${t.from} → ${t.to}<br>${t.note}<br><i>route drawn schematically; the underground alignment is not in the data</i>`;
    }
    return null;
  }

  /** RGBA overlay (delineation grid) tinting the gauge catchments; rows bottom-up for the terrain uv. */
  overlayTexture() {
    const { grid, masks } = this.data.catchments;
    const W = grid.width, H = grid.height;
    const inside = new Uint8Array(W * H);
    for (const mk of Object.values(masks)) {
      if (mk.role !== 'upstream') continue;
      for (const [r, a, b] of mk.runs) for (let q = a; q <= b; q++) inside[r * W + q] = 1;
    }
    const px = new Uint8Array(W * H * 4);
    const [cr, cg, cb] = COLORS.overlay;
    for (let r = 0; r < H; r++) {
      for (let q = 0; q < W; q++) {
        if (!inside[r * W + q]) continue;
        const edge = r === 0 || q === 0 || r === H - 1 || q === W - 1 || !inside[(r - 1) * W + q] || !inside[(r + 1) * W + q] || !inside[r * W + q - 1] || !inside[r * W + q + 1];
        const o = ((H - 1 - r) * W + q) * 4;
        px[o] = cr; px[o + 1] = cg; px[o + 2] = cb; px[o + 3] = edge ? 215 : 46;
      }
    }
    const tex = new THREE.DataTexture(px, W, H, THREE.RGBAFormat);
    tex.colorSpace = THREE.SRGBColorSpace;
    tex.magFilter = THREE.LinearFilter;
    tex.minFilter = THREE.LinearMipmapLinearFilter;
    tex.generateMipmaps = true;
    tex.needsUpdate = true;
    return tex;
  }
}
