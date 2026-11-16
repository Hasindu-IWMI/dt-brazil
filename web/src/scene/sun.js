// Solar position (NOAA Global Monitoring Division algorithm, after Meeus 1998), ported from the
// Kelani WebTwin (src/env/sun.ts). About 0.01 degree in elevation for 1950-2050: ample for lighting.
// Refraction near the horizon uses the Saemundsson approximation.
const rad = Math.PI / 180;

/** { azimuth: degrees clockwise from true north, elevation: degrees above the horizon } */
export function solarPosition(date, latDeg, lonDeg) {
  const jd = date.getTime() / 86400000 + 2440587.5;
  const T = (jd - 2451545.0) / 36525;
  const L0 = (280.46646 + T * (36000.76983 + T * 0.0003032)) % 360;
  const M = 357.52911 + T * (35999.05029 - 0.0001537 * T);
  const e = 0.016708634 - T * (0.000042037 + 0.0000001267 * T);
  const C = Math.sin(M * rad) * (1.914602 - T * (0.004817 + 0.000014 * T)) + Math.sin(2 * M * rad) * (0.019993 - 0.000101 * T) + Math.sin(3 * M * rad) * 0.000289;
  const omega = 125.04 - 1934.136 * T;
  const lambda = L0 + C - 0.00569 - 0.00478 * Math.sin(omega * rad);
  const eps0 = 23 + (26 + (21.448 - T * (46.815 + T * (0.00059 - T * 0.001813))) / 60) / 60;
  const eps = eps0 + 0.00256 * Math.cos(omega * rad);
  const decl = Math.asin(Math.sin(eps * rad) * Math.sin(lambda * rad));
  const y = Math.tan((eps / 2) * rad) ** 2;
  const eqTime = (4 / rad) * (y * Math.sin(2 * L0 * rad) - 2 * e * Math.sin(M * rad) + 4 * e * y * Math.sin(M * rad) * Math.cos(2 * L0 * rad)
    - 0.5 * y * y * Math.sin(4 * L0 * rad) - 1.25 * e * e * Math.sin(2 * M * rad));
  const utcMin = date.getUTCHours() * 60 + date.getUTCMinutes() + date.getUTCSeconds() / 60;
  const trueSolarTime = (((utcMin + eqTime + 4 * lonDeg) % 1440) + 1440) % 1440;
  let hourAngle = trueSolarTime / 4 - 180;
  if (hourAngle < -180) hourAngle += 360;
  const lat = latDeg * rad;
  const cosZen = Math.sin(lat) * Math.sin(decl) + Math.cos(lat) * Math.cos(decl) * Math.cos(hourAngle * rad);
  let elevation = 90 - Math.acos(Math.min(1, Math.max(-1, cosZen))) / rad;
  if (elevation > -1) elevation += 1.02 / Math.tan((elevation + 10.3 / (elevation + 5.11)) * rad) / 60;
  const az = Math.atan2(Math.sin(hourAngle * rad), Math.cos(hourAngle * rad) * Math.sin(lat) - Math.tan(decl) * Math.cos(lat));
  return { azimuth: (((az / rad + 180) % 360) + 360) % 360, elevation };
}

/** Unit vector towards the sun in scene axes (x east, y up, z south). */
export function sunVector(p, out) {
  const el = p.elevation * rad;
  const az = p.azimuth * rad;
  return out.set(Math.sin(az) * Math.cos(el), Math.sin(el), -Math.cos(az) * Math.cos(el));
}
