"""Build daily forcing (rain, potential evapotranspiration) for each catchment.

Rain: ANA daily rain gauges (observed). Catchment rain is the inverse-distance-
squared weighted mean, to the catchment centroid, of the gauges within
RADIUS_KM that report on that day. The number of gauges used is stored for
every day, and days with no gauge are left empty.

Potential evapotranspiration: Oudin et al. (2005) formula from daily mean air
temperature and latitude. Temperature is NASA POWER T2M (MERRA-2 reanalysis,
about 0.5 degree), fetched at the catchment centroid. This is a REANALYSIS
input, not an observation, and is the weakest forcing here.

Usage: python forcing.py
"""
import datetime as dt
import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # isolated mode drops the script folder
import common as c  # noqa: E402

RADIUS_KM = 20.0
# Rain gauges from ANA's HidroInventario (queried 2026-11-14): code -> (name, lat, lon)
RAIN_GAUGES = {
    "2346004": ("Piracaia (SP Águas)", -23.05, -46.35),
    "2346005": ("Batatuba", -23.0833, -46.40),
    "2346094": ("Piracaia (ANA)", -23.0522, -46.3653),
    "2346334": ("Crioulos", -23.0667, -46.30),
    "2246090": ("Joanópolis", -22.9333, -46.2667),
    "2246099": ("Fazenda Bonfim", -22.9667, -46.10),
    "2246134": ("Mato Mole", -22.9833, -46.2333),
    "2246046": ("Fazenda Retiro", -22.9333, -46.1167),
    "2346403": ("Água do Poço", -23.0167, -46.1667),
    "2346010": ("Nazaré Paulista (SP Águas)", -23.1833, -46.40),
    "2346017": ("Morro Grande", -23.2667, -46.4167),
    "2346352": ("Ribeirão Acima", -23.1833, -46.3333),
    "2346402": ("Bairro Cuiabá", -23.25, -46.3833),
    "2346007": ("Atibaia (SP Águas)", -23.15, -46.55),
    "2346095": ("Atibaia (ANA)", -23.1033, -46.5581),
    "2346019": ("Santa Isabel", -23.3333, -46.2333),
    "2246174": ("Joanópolis (ANA)", -22.9347, -46.2117),
    "2346446": ("Nazaré Paulista (ANA)", -23.2103, -46.3553),
}
CATCHMENTS = ["cachoeira_dam", "atibainha_dam"]
MAX_DAILY_RAIN_MM = 400.0  # values above this are treated as placeholders


def km(lat1, lon1, lat2, lon2):
    x = (lon2 - lon1) * 111.32 * math.cos(math.radians((lat1 + lat2) / 2))
    y = (lat2 - lat1) * 110.574
    return math.hypot(x, y)


def load_rain(code, exclusions=None):
    """Daily rain for one gauge. With exclusions (from audit_rain.py), the
    flagged gauge-months and gauge-years are dropped, i.e. treated as missing."""
    path = os.path.join(c.PROCESSED, "ana_rain_%s.csv" % code)
    if not os.path.exists(path):
        return {}
    months = years = ()
    if exclusions:
        months = {k.split("|")[1] for k in exclusions["months"] if k.startswith(code + "|")}
        years = {k.split("|")[1] for k in exclusions["years"] if k.startswith(code + "|")}
    out = {}
    for r in c.read_csv(path):
        v = float(r["rain_mm"])
        d = r["date"]
        if 0 <= v <= MAX_DAILY_RAIN_MM and d[:7] not in months and d[:4] not in years:
            out[d] = v
    return out


def areal(rain, used, key):
    num = den = 0.0
    k = 0
    for dist, code in used:
        v = rain[code].get(key)
        if v is None:
            continue
        w = 1.0 / max(dist, 1.0) ** 2
        num += w * v
        den += w
        k += 1
    return (None if k == 0 else round(num / den, 2)), k


def power_temperature(name, lat, lon):
    """Daily mean 2 m temperature from NASA POWER, cached as raw JSON."""
    path = os.path.join(c.RAW, "nasa_power", "t2m_%s.json" % name)
    if not os.path.exists(path):
        end = (dt.date.today() - dt.timedelta(days=7)).strftime("%Y%m%d")
        url = ("https://power.larc.nasa.gov/api/temporal/daily/point?parameters=T2M&community=AG"
               "&longitude=%.4f&latitude=%.4f&start=19810101&end=%s&format=JSON" % (lon, lat, end))
        data = c.http_get(url, timeout=300, retries=4, backoff=20)
        c.write_bytes(path, data)
        c.append_manifest({"source": "NASA POWER daily T2M (MERRA-2)", "url": url,
                           "file": os.path.relpath(path, c.ROOT), "bytes": len(data), "sha256": c.sha256(data)})
    with open(path, encoding="utf-8") as f:
        j = json.load(f)
    fill = j["header"].get("fill_value", -999.0)
    out = {}
    for k, v in j["properties"]["parameter"]["T2M"].items():
        if v != fill:
            out["%s-%s-%s" % (k[:4], k[4:6], k[6:8])] = v
    return out


def oudin_pet(temp_c, lat_deg, day_of_year):
    """Oudin et al. 2005: PE = Re / (lambda rho) * (T + 5) / 100 when T + 5 > 0 (mm/day)."""
    phi = math.radians(lat_deg)
    dr = 1 + 0.033 * math.cos(2 * math.pi * day_of_year / 365.0)
    delta = 0.409 * math.sin(2 * math.pi * day_of_year / 365.0 - 1.39)
    ws = math.acos(max(-1.0, min(1.0, -math.tan(phi) * math.tan(delta))))
    re = 24 * 60 / math.pi * 0.0820 * dr * (ws * math.sin(phi) * math.sin(delta) + math.cos(phi) * math.cos(delta) * math.sin(ws))
    return max(0.0, re / 2.45 * (temp_c + 5.0) / 100.0)


def main():
    cats = json.load(open(os.path.join(c.PROCESSED, "catchments.json"), encoding="utf-8"))["catchments"]
    raw = {code: load_rain(code) for code in RAIN_GAUGES}
    excl_path = os.path.join(c.PROCESSED, "rain_exclusions.json")
    exclusions = json.load(open(excl_path, encoding="utf-8")) if os.path.exists(excl_path) else None
    rain = {code: load_rain(code, exclusions) for code in RAIN_GAUGES}
    lines = ["# Forcing report", "",
             "Generated %s UTC by `pipeline/forcing.py`." % dt.datetime.utcnow().strftime("%Y-%m-%d %H:%M"), "",
             "Catchment rain uses the audited gauge records: %s. The unaudited value is kept beside it." %
             ("%d gauge-months and %d gauge-years excluded by `audit_rain.py`" % (len(exclusions["months"]), len(exclusions["years"]))
              if exclusions else "no audit file found, so nothing is excluded"), "",
             "## Rain gauges", "",
             "| Code | Name | First day | Last day | Days present | Mean annual rain, complete years (mm) |",
             "| --- | --- | --- | --- | --- | --- |"]
    for code, (name, _, _) in RAIN_GAUGES.items():
        r = rain[code]
        if not r:
            lines.append("| %s | %s | no data | | | |" % (code, name))
            continue
        ds = sorted(r)
        years = {}
        for d, v in r.items():
            y = years.setdefault(d[:4], [0, 0.0])
            y[0] += 1
            y[1] += v
        full = [t for n, t in years.values() if n >= 360]
        lines.append("| %s | %s | %s | %s | %d | %s |" % (code, name, ds[0], ds[-1], len(ds),
                                                      "%.0f (%d years)" % (sum(full) / len(full), len(full)) if full else "no complete year"))
    for cat in CATCHMENTS:
        cen = cats[cat]["centroid"]
        near = sorted((km(cen["lat"], cen["lon"], la, lo), code) for code, (_, la, lo) in RAIN_GAUGES.items())
        used = [(d, code) for d, code in near if d <= RADIUS_KM and rain[code]]
        temp = power_temperature(cat, cen["lat"], cen["lon"])
        start = dt.date(1981, 1, 1)
        end = dt.date.today()
        rows = []
        counts = {}
        d = start
        while d <= end:
            key = d.isoformat()
            value, k = areal(rain, used, key)
            value_raw, _ = areal(raw, used, key)
            t = temp.get(key)
            pet = None if t is None else round(oudin_pet(t, cen["lat"], d.timetuple().tm_yday), 3)
            rows.append((key, value, k, pet, t, value_raw))
            counts[key[:4]] = counts.get(key[:4], []) + [k]
            d += dt.timedelta(days=1)
        c.write_csv(os.path.join(c.PROCESSED, "forcing_%s.csv" % cat),
                    ["date", "rain_mm", "gauges_used", "pet_mm", "temperature_c", "rain_unaudited_mm"], rows)
        lines += ["", "## Catchment: %s" % cat, "",
                  "- Centroid %.4f, %.4f; delineated area %.1f km2 (published %.1f)." %
                  (cen["lat"], cen["lon"], cats[cat]["area_km2"], cats[cat]["published_km2"]),
                  "- Gauges within %.0f km of the centroid: %s." %
                  (RADIUS_KM, ", ".join("%s %s (%.1f km)" % (code, RAIN_GAUGES[code][0], dist) for dist, code in used)),
                  "- Days with no gauge reporting: %d of %d." % (sum(1 for r in rows if r[1] is None), len(rows)),
                  "- Days with no temperature: %d." % sum(1 for r in rows if r[3] is None), "",
                  "| Period | Median gauges per day | Days with one gauge or none | Mean annual rain, audited (mm) | Before the audit (mm) | Mean annual PET (mm) |",
                  "| --- | --- | --- | --- | --- | --- |"]
        for a, b in [(1984, 1993), (1994, 2003), (2004, 2013), (2014, 2016), (2017, 2017), (2018, 2021), (2022, 2025)]:
            sel = [r for r in rows if a <= int(r[0][:4]) <= b and r[1] is not None]
            ks = sorted(r[2] for r in sel)
            yrs = len(sel) / 365.25
            lines.append("| %d–%d | %d | %d | %.0f | %.0f | %.0f |" % (
                a, b, ks[len(ks) // 2], sum(1 for k in ks if k <= 1),
                sum(r[1] for r in sel) / yrs, sum(r[5] or 0 for r in sel) / yrs, sum(r[3] or 0 for r in sel) / yrs))
        print(cat, "gauges:", [code for _, code in used], flush=True)
    out = os.path.join(c.ROOT, "docs", "forcing_report.md")
    with open(out, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print("report:", out)


if __name__ == "__main__":
    main()
