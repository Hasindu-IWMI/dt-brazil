// Rain, river and tunnel records drawn on the terrain (data: public/data/layers.json, built by
// pipeline/viewer_layers.py). Encodings, all for the replayed date:
//   rain gauges   a column per gauge, height proportional to that day's audited rain (observed);
//                 a grey base where the gauge has no record that day
//   flow stations a ring whose AREA is proportional to the day's mean discharge (observed),
//                 with a slow ripple; grey and small when there is no record
//   tunnels       an arc between the two ends. Measured tunnels carry particles whose number
//                 and speed follow the measured flow; the others are grey and dashed. Arcs are
//                 deliberately schematic: the underground alignments are not in the data.
//   catchments    the DEM catchments of the gauges above the lakes, draped on the terrain as a
//                 tint (see Terrain.setOverlay)
import * as THREE from 'three';
import { CSS2DObject } from 'three/addons/renderers/CSS2DRenderer.js';

export const COLORS = {
  rainLo: new THREE.Color(0xbfe1ff), rainHi: new THREE.Color(0x1f5fbf), noRecord: new THREE.Color(0x77756d),
  upstream: new THREE.Color(0x2bb3a3), below_dam: new THREE.Color(0x6fb2ff), tunnel: new THREE.Color(0xb48cff),
  overlay: [43, 179, 163],
};
const RAIN_M_PER_MM = 25; // column height (display scale)
const RING_M_PER_SQRT_Q = 380; // ring radius = k * sqrt(Q): ring AREA is proportional to discharge

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

    // ---- rain gauges: instanced columns and bases
    this.sites = data.rain_sites.filter((s) => inBox(s.lon, s.lat));
    const col = new THREE.CylinderGeometry(1, 1, 1, 14).translate(0, 0.5, 0);
    this.rainCols = new THREE.InstancedMesh(col, new THREE.MeshStandardMaterial({ roughness: 0.35, metalness: 0, transparent: true, opacity: 0.8, emissive: 0x0b2a55, emissiveIntensity: 0.6 }), this.sites.length);
    this.rainBase = new THREE.InstancedMesh(new THREE.CylinderGeometry(1, 1, 1, 18).translate(0, 0.5, 0),
      new THREE.MeshStandardMaterial({ roughness: 0.6 }), this.sites.length);
    for (const m of [this.rainCols, this.rainBase]) {
      m.instanceMatrix.setUsage(THREE.DynamicDrawUsage);
      m.frustumCulled = false;
      m.userData.kind = 'rain';
      this.rainGroup.add(m);
      this.pickables.push(m);
    }

    // ---- flow stations: ring + ripple + pole (+ label for river gauges)
    this.stations = data.flow_stations.filter((s) => inBox(s.lon, s.lat)).map((s) => {
      const color = COLORS[s.role];
      const ring = new THREE.Mesh(new THREE.RingGeometry(0.72, 1, 48).rotateX(-Math.PI / 2),
        new THREE.MeshBasicMaterial({ color, transparent: true, opacity: 0.75, side: THREE.DoubleSide, depthWrite: false }));
      const ripple = new THREE.Mesh(new THREE.RingGeometry(0.94, 1, 48).rotateX(-Math.PI / 2),
        new THREE.MeshBasicMaterial({ color, transparent: true, opacity: 0.5, side: THREE.DoubleSide, depthWrite: false }));
      const pole = new THREE.Mesh(new THREE.CylinderGeometry(55, 55, 700, 10).translate(0, 350, 0), new THREE.MeshStandardMaterial({ color }));
      ring.renderOrder = ripple.renderOrder = 3;
      pole.userData = { kind: 'flow', station: s };
      this.pickables.push(pole);
      this.flowGroup.add(ring, ripple, pole);
      let label = null;
      if (s.role !== 'tunnel') {
        const el = document.createElement('div');
        el.className = 'label label-flow';
        el.dataset.prio = s.role === 'upstream' ? '4' : '1';
        label = new CSS2DObject(el);
        this.flowGroup.add(label);
      }
      return { s, ring, ripple, pole, label, phase: Math.random() };
    });

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
    const m = new THREE.Matrix4();
    this.sites.forEach((s, k) => {
      s._p = new THREE.Vector3(X(s.lon), this.surfaceAt(s.lon, s.lat) * exag, Z(s.lat));
      m.compose(s._p, new THREE.Quaternion(), new THREE.Vector3(190, 30, 190));
      this.rainBase.setMatrixAt(k, m);
    });
    this.rainBase.instanceMatrix.needsUpdate = true;
    for (const st of this.stations) {
      const y = this.surfaceAt(st.s.lon, st.s.lat) * exag + 25;
      for (const o of [st.ring, st.ripple, st.pole]) o.position.set(X(st.s.lon), y, Z(st.s.lat));
      st.label?.position.set(X(st.s.lon), y + 1250, Z(st.s.lat));
    }
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
    const m = new THREE.Matrix4();
    const c = new THREE.Color();
    this.sites.forEach((s, k) => {
      const v = this.rainOn(s, i);
      const h = v ? Math.max(1, v * RAIN_M_PER_MM) : 0.001;
      m.compose(s._p.clone().setY(s._p.y + 30), new THREE.Quaternion(), new THREE.Vector3(v ? 115 : 0.001, h, v ? 115 : 0.001));
      this.rainCols.setMatrixAt(k, m);
      this.rainCols.setColorAt(k, c.copy(COLORS.rainLo).lerp(COLORS.rainHi, Math.min(1, (v ?? 0) / 60)));
      this.rainBase.setColorAt(k, v === null ? COLORS.noRecord : c.set(0xe9f3ff));
    });
    this.rainCols.instanceMatrix.needsUpdate = true;
    this.rainCols.instanceColor.needsUpdate = true;
    this.rainBase.instanceColor.needsUpdate = true;
    this.rainCols.computeBoundingSphere(); // for picking: heights change every day
    this.rainBase.computeBoundingSphere();
    for (const st of this.stations) {
      const q = this.flowOn(st.s, i);
      const r = q === null ? 160 : Math.max(120, RING_M_PER_SQRT_Q * Math.sqrt(Math.max(q, 0)));
      st.radius = r;
      st.q = q;
      st.ring.scale.setScalar(r);
      st.ring.material.color.copy(q === null ? COLORS.noRecord : COLORS[st.s.role]);
      st.ripple.visible = q !== null;
      if (st.label) {
        const depth = q !== null && st.s.area_km2 ? ` · ${(q * 86.4 / st.s.area_km2).toFixed(1)} mm/day` : '';
        const name = st.s.label.replace(/ \(.*\)$/, '');
        st.label.element.innerHTML = `<b>${st.s.code}</b> <span>${name}</span><br><span>${q === null ? 'no record this day' : q.toFixed(2) + ' m³/s' + depth}</span>`;
      }
    }
    for (const o of this.tunnels) {
      const q = o.t.station ? this.flowOn(this.station(o.t.station), i) : null;
      o.q = q;
      o.el.innerHTML = `<b>${o.t.name}</b> <span>${!o.t.measured ? '· no public flow record' : q === null ? '· no record this day' : q.toFixed(1) + ' m³/s'}</span><br><span>${o.t.from} → ${o.t.to}</span>`;
    }
  }

  /** Per-frame animation: ripples and tunnel particles. */
  tick(t) {
    for (const st of this.stations) {
      if (!st.ripple.visible) continue;
      const f = (t * 0.35 + st.phase) % 1;
      st.ripple.scale.setScalar(st.radius * (1 + 0.6 * f));
      st.ripple.material.opacity = 0.55 * (1 - f);
    }
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

  /** Text for the hover tip, or null. */
  describe(hit) {
    const i = this.index;
    const date = this.dates[i];
    const o = hit.object;
    if (o === this.rainCols || o === this.rainBase) {
      const s = this.sites[hit.instanceId];
      const v = this.rainOn(s, i);
      return `<b>${s.name}</b><br>${s.operator} · ${s.kind} gauge<br>${date}: ${v === null ? 'no record (or excluded by the audit)' : v.toFixed(1) + ' mm'}<br><i>observed, audited · day = 24 h to 07:00</i>`;
    }
    if (o.userData.kind === 'flow') {
      const s = o.userData.station;
      const q = this.flowOn(s, i);
      return `<b>${s.label}</b><br>SIBH ${s.code} · ${s.role.replace('_', ' ')}<br>${date}: ${q === null ? 'no record' : q.toFixed(2) + ' m³/s, daily mean'}`
        + (s.area_km2 ? `<br>catchment ${s.area_km2} km² from the DEM (other snap rule ${s.max_rule_area_km2} km²)` : '')
        + '<br><i>observed; discharge from a rating curve</i>';
    }
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
