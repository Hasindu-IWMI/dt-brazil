// Floods in Atibaia town (data: public/data/layers.json -> flood, built by pipeline/viewer_layers.py).
// Observed and official records only; NO modelled water (flood run 1 stopped before its test).
//   town gauge    SP Aguas' gauge 3E-063, a flat diamond at its site in the colour of the alarm level
//                 reached that day (observed highest hourly level against SP Aguas' official levels),
//                 pulsing from the attention level up. Its label carries a small level bar marked with
//                 the alarm levels. ANA's gauge 62670000 stands 77 m away (a white dot).
//   risk sectors  the Geological Survey of Brazil's 2012 sectors (official mapped areas, not flood
//                 extents), painted on the terrain as a sharp detail overlay; hover tests the ground point.
import * as THREE from 'three';
import { CSS2DObject } from 'three/addons/renderers/CSS2DRenderer.js';
import { valueOn } from './layers.js';
import { Symbols, SHAPE, pinLabel } from './symbols.js';

const BAR_TOP_M = 5; // the label's level bar runs from the gauge zero to 5 m
const GAUGE_PX = 24;
export const LEVELS = [ // SP Aguas' alarm levels, lowest first (keys as in its SIBH station record)
  { key: 'attention', name: 'attention', color: '#f2c94c' },
  { key: 'alert', name: 'alert', color: '#f2994a' },
  { key: 'emergency', name: 'emergency', color: '#eb5757' },
  { key: 'extravasation', name: 'overflow', color: '#c2185b' },
];
const NORMAL = { key: 'normal', name: 'below attention', color: '#6fb2ff' };
export const RISK_STYLE = { // fill RGB, by CPRM type
  'Inundação': { rgb: [64, 128, 255], en: 'river flood' },
  'Enxurrada': { rgb: [32, 196, 180], en: 'flash flood' },
  'Deslizamento': { rgb: [196, 120, 52], en: 'landslide' },
};

/** The alarm level reached by a level in cm (or NORMAL). */
export function statusOf(cm, levels) {
  let s = NORMAL;
  if (cm === null || cm === undefined) return null;
  for (const l of LEVELS) if (levels[l.key] !== undefined && cm >= levels[l.key]) s = l;
  return s;
}

export class FloodLayer {
  constructor({ data, dates, frame, surfaceAt }) {
    Object.assign(this, { data, dates, frame, surfaceAt });
    this.off = new Map();
    this.group = new THREE.Group();
    this.riskOn = true; // the sectors are in the terrain overlay; this only gates the hover
    this.index = 0;
    const town = data.town;
    this.levels = town.levels_cm;

    // ---- town gauge: one diamond, pulsing from the attention level up, and its label
    this.gauge = new Symbols(1, { pulse: true, order: 8 });
    this.group.add(this.gauge.group);
    const el = document.createElement('div');
    el.className = 'label label-flood';
    el.dataset.prio = '5';
    this.el = el;
    this.label = new CSS2DObject(el);
    pinLabel(this.label, GAUGE_PX);
    this.group.add(this.label);

    // ---- risk sectors: painted into the terrain (riskTexture); hovered by a point-in-polygon test
    // on the ground point under the pointer (riskAt), so the test follows the relief exactly
    this.sectors = (data.risk?.sectors ?? []).map((s) => {
      const pts = s.rings.flat();
      return { s, west: Math.min(...pts.map((p) => p[0])), east: Math.max(...pts.map((p) => p[0])),
        south: Math.min(...pts.map((p) => p[1])), north: Math.max(...pts.map((p) => p[1])) };
    });
    this.qSeries = town.q_first ? { first: town.q_first } : null;
    this.place(1);
  }

  /** (Re)build positions for a vertical exaggeration. */
  place(exag) {
    this.exag = exag;
    const { X, Z } = this.frame;
    const t = this.data.town;
    const y = this.surfaceAt(t.lon, t.lat) * exag + 2;
    this.gauge.setPos(0, X(t.lon), y, Z(t.lat));
    this.label.position.set(X(t.lon), y, Z(t.lat));
    this.show(this.index);
  }

  levelOn(i) { return valueOn(this.data.town, this.data.town.max_cm, this.dates, i, this.off); }
  flowOn(i) { return this.qSeries ? valueOn(this.qSeries, this.data.town.q, this.dates, i, this.off) : null; }

  /** The risk sector containing a geographic point (even-odd rule over its rings), or null. */
  riskAt(lon, lat) {
    if (!this.riskOn) return null;
    for (const o of this.sectors) {
      if (lon < o.west || lon > o.east || lat < o.south || lat > o.north) continue;
      let inside = false;
      for (const ring of o.s.rings) {
        for (let a = 0, b = ring.length - 1; a < ring.length; b = a++) {
          const [xa, ya] = ring[a], [xb, yb] = ring[b];
          if ((ya > lat) !== (yb > lat) && lon < ((xb - xa) * (lat - ya)) / (yb - ya) + xa) inside = !inside;
        }
      }
      if (inside) return o.s;
    }
    return null;
  }
  downstreamOn(i) { const d = this.data.downstream; return d ? valueOn(d, d.max_cm, this.dates, i, this.off) : null; }
  /** The flood (derived) whose days include dates[i], or null. */
  eventOn(i) {
    const d = this.dates[i];
    return this.data.events.find((e) => d >= e.first && d <= e.last) ?? null;
  }
  /** Index of the next (dir 1) or previous (dir -1) flood peak from i, or null. */
  eventFrom(i, dir) {
    const d = this.dates[i];
    const peaks = this.data.events.map((e) => e.peak_date).filter((p) => (dir > 0 ? p > d : p < d));
    if (!peaks.length) return null;
    const p = dir > 0 ? peaks[0] : peaks[peaks.length - 1];
    const k = this.dates.indexOf(p);
    return k >= 0 ? k : null;
  }

  /** Update the gauge to dates[i]. */
  show(i) {
    this.index = i;
    const cm = this.levelOn(i);
    const st = statusOf(cm, this.levels);
    this.status = st;
    const pulse = !st || st.key === 'normal' ? 0 : st.key === 'extravasation' ? 0.6 : 0.35;
    this.gauge.set(0, { size: GAUGE_PX, color: st ? st.color : '#77756d', shape: SHAPE.diamond, pulse });
    this.gauge.commit();
    const over = cm !== null && this.levels.extravasation !== undefined ? (cm - this.levels.extravasation) / 100 : null;
    const pct = (v) => `${Math.max(0, Math.min(100, (100 * v) / (BAR_TOP_M * 100))).toFixed(1)}%`;
    const ticks = LEVELS.filter((l) => this.levels[l.key] !== undefined)
      .map((l) => `<i class="tick" style="left:${pct(this.levels[l.key])};background:${l.color}"></i>`).join('');
    const bar = cm === null ? '' : `<div class="lvl"><i class="fill" style="width:${pct(cm)};background:${st.color}"></i>${ticks}</div>`;
    this.el.style.borderColor = st ? st.color : '';
    this.el.innerHTML = `<b>3E-063</b> <span>Atibaia town</span>${bar}`
      + (cm === null ? '<span>no record this day</span>'
        : `<span>${(cm / 100).toFixed(2)} m · <b style="color:${st.color}">${st.name}</b>`
          + (over !== null && over >= 0 ? ` +${over.toFixed(2)} m` : '') + '</span>');
  }

  /** The gauge under a screen point: [{dpx, pos, text}] (see Symbols.hits). */
  symbolHits(ndc, camera, w, h) {
    if (!this.group.visible) return [];
    return this.gauge.hits(ndc, camera, w, h).map((hh) => ({ ...hh, text: this.describeGauge() }));
  }

  /** Text for the hover tip over the gauge. */
  describeGauge() {
    const i = this.index;
    const date = this.dates[i];
    const cm = this.levelOn(i);
    const q = this.flowOn(i);
    const st = statusOf(cm, this.levels);
    const lv = LEVELS.filter((l) => this.levels[l.key] !== undefined)
      .map((l) => `<span style="color:${l.color}">${l.name} ${(this.levels[l.key] / 100).toFixed(2)} m</span>`).join(' · ');
    const ev = this.eventOn(i);
    return `<b>${this.data.town.label}</b><br>SP Águas telemetric gauge, SIBH ${this.data.town.code}<br>`
      + `${date}: ${cm === null ? 'no record' : `highest hourly level ${(cm / 100).toFixed(2)} m (${st.name})`}`
      + `${q === null ? '' : `, mean flow ${q.toFixed(1)} m³/s`}<br>Official alarm levels: ${lv}`
      + (ev ? `<br>Flood of ${ev.peak_date}: peak ${(ev.peak_cm / 100).toFixed(2)} m, ${ev.days_above} day(s) at or over the overflow level` : '')
      + '<br><i>observed; level on the gauge\'s own zero. The diamond marks the gauge, not the flooded area. ANA\'s gauge'
      + ' 62670000 stands 77 m away; its daily flow comes from ANA\'s own rating and can differ</i>';
  }

  /** Text for the hover tip over a risk sector. */
  describeRisk(s) {
    const ty = RISK_STYLE[s.type]?.en ?? s.type;
    const grade = s.grade === 'Muito Alto' ? 'very high' : s.grade === 'Alto' ? 'high' : s.grade;
    const text = s.description.length > 260 ? s.description.slice(0, 257).replace(/\s+\S*$/, '') + '…' : s.description;
    return `<b>${s.place}</b><br>Risk sector ${s.id.replace(/_CPRM$/, '')}: ${ty}, risk ${grade} (${s.type}, ${s.grade})<br>`
      + `${s.homes ?? '?'} homes, ${s.people ?? '?'} people at risk when surveyed (${s.surveyed})<br><span class="tip-pt">${text}</span>`
      + '<br><i>Geological Survey of Brazil (CPRM), 2012: an official mapped area, not a flood extent and not a model; not updated since</i>';
  }

  /** The risk sectors painted on a canvas texture over their own extent (padded), for
   * terrain.setDetailOverlay: { tex, box: {west, south, east, north} }, or null without sectors. */
  riskTexture(width = 2048, fill = true) {
    if (!this.sectors.length) return null;
    const pts = this.sectors.flatMap((o) => o.s.rings.flat());
    const pad = 0.004; // about 400 m
    const bbox = { west: Math.min(...pts.map((p) => p[0])) - pad, east: Math.max(...pts.map((p) => p[0])) + pad,
      south: Math.min(...pts.map((p) => p[1])) - pad, north: Math.max(...pts.map((p) => p[1])) + pad };
    const W = width;
    const H = Math.round(W * ((bbox.north - bbox.south) * this.frame.KZ) / ((bbox.east - bbox.west) * this.frame.KX));
    const cv = document.createElement('canvas');
    cv.width = W; cv.height = H;
    this.paintRisk(cv.getContext('2d'), W, H, bbox, fill);
    const tex = new THREE.CanvasTexture(cv); // flipY: canvas top row = north = top of the terrain uv
    tex.colorSpace = THREE.SRGBColorSpace;
    tex.anisotropy = 8;
    return { tex, box: bbox };
  }

  /** Paint the risk sectors into a 2D canvas covering bbox (north up). */
  paintRisk(g, W, H, bbox, fill = true) { // fill false: outlines only (under modelled water)
    const x = (lon) => ((lon - bbox.west) / (bbox.east - bbox.west)) * W;
    const y = (lat) => ((bbox.north - lat) / (bbox.north - bbox.south)) * H;
    for (const { s } of this.sectors) {
      const st = RISK_STYLE[s.type] ?? { rgb: [200, 200, 200] };
      const [r, gg, b] = st.rgb;
      const strong = s.grade === 'Muito Alto';
      g.beginPath();
      for (const ring of s.rings) {
        ring.forEach(([lon, lat], k) => (k ? g.lineTo(x(lon), y(lat)) : g.moveTo(x(lon), y(lat))));
        g.closePath();
      }
      g.fillStyle = `rgba(${r},${gg},${b},${strong ? 0.5 : 0.34})`;
      if (fill) g.fill('evenodd');
      g.lineWidth = fill ? Math.max(2, W / 700) : Math.max(1.5, W / 1600);
      g.setLineDash(fill ? [] : [W / 260, W / 420]); // outlines only: thin and dashed, unlike a river
      g.strokeStyle = `rgba(${r},${gg},${b},0.95)`;
      g.stroke();
    }
  }
}
