"""The river gauges above Cachoeira and Atibainha, on their DEM catchments.

The gauges (SIBH 3E-122 and 3E-121, ANA 62664500 and 62654500) measure the river
above each lake, independently of the reservoir water balance from which the
operator computes the daily inflow. No drainage area is published for either, so
pipeline/delineate.py derives them from the DEM. This script checks those areas
and puts the gauges' flow and the operator's inflow on the same footing.

Checks (no published area exists, so the areas are checked three other ways):
  1. Nesting: every cell of a gauge catchment lies inside its dam catchment.
  2. River: the snapped outlet lies on the river the inventory names for the gauge
     (distance to that OpenStreetMap river line).
  3. Plausibility: the runoff depth the area implies, against catchment rain.

Comparison, by calendar year (a year counts only with at least MIN_DAYS days on
which both rain and flow exist; sums over those days):
  - gauge catchment: rain (inverse-distance weighting of the audited gauges to the
    catchment centroid, exactly as forcing.py does for the dam catchments) and
    runoff depth = discharge x 86.4 / area (mm);
  - dam catchment: forcing.py's rain and the operator's daily inflow (SAR) as depth.
The runoff ratio (runoff / rain) of the two should be similar if the gauge's
rating and the operator's inflow agree; they share 75% (Cachoeira) and 41%
(Atibainha) of their area.

Outputs: data/processed/upstream_catchments.json, data/processed/upstream_rain_<name>.csv
and docs/upstream_catchments.md. No model output is used and nothing is fitted.
Usage: python upstream_catchments.py
"""
import datetime as dt
import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # isolated mode drops the script folder
import common as c  # noqa: E402
import forcing as fo  # noqa: E402

MIN_DAYS = 300
# gauge catchment -> (dam catchment, SIBH flow station id, SIBH code, river named in ANA's inventory, SAR key)
GAUGES = {
    "cachoeira_upstream_gauge": ("cachoeira_dam", "1430", "3E-122", "Rio da Cachoeira", "cachoeira"),
    "atibainha_upstream_gauge": ("atibainha_dam", "1397", "3E-121", "Rio Atibainha", "atibainha"),
}


def mask_of(runs):
    return {(r, col) for r, a, b in runs for col in range(a, b + 1)}


def dist_to_line_km(lat, lon, line):
    best = float("inf")
    for (x1, y1), (x2, y2) in zip(line, line[1:]):
        k = 111.320 * math.cos(math.radians(lat))
        ax, ay = (x1 - lon) * k, (y1 - lat) * 110.574
        bx, by = (x2 - lon) * k, (y2 - lat) * 110.574
        dx, dy = bx - ax, by - ay
        t = 0.0 if dx == dy == 0 else max(0.0, min(1.0, -(ax * dx + ay * dy) / (dx * dx + dy * dy)))
        best = min(best, math.hypot(ax + t * dx, ay + t * dy))
    return best


def num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def main():
    cats = json.load(open(os.path.join(c.PROCESSED, "catchments.json"), encoding="utf-8"))["catchments"]
    vectors = json.load(open(os.path.join(c.ROOT, "web", "public", "data", "vectors.json"), encoding="utf-8"))
    excl = json.load(open(os.path.join(c.PROCESSED, "rain_exclusions.json"), encoding="utf-8"))
    rain = {code: fo.load_rain(code, excl) for code in fo.ALL_GAUGES}
    out = {}
    L = ["# River gauges above the reservoirs, on their DEM catchments", "",
         "Generated %s UTC by `pipeline/upstream_catchments.py`. Observed records only; no model output is used and nothing is fitted." %
         dt.datetime.utcnow().strftime("%Y-%m-%d %H:%M"), "",
         "The two gauges measure the river above each lake, independently of the reservoir balance from which the operator "
         "computes daily inflow. Neither SIBH nor ANA's inventory gives a drainage area, so `pipeline/delineate.py` "
         "derives them from the Copernicus DEM (3 arc-seconds), snapping each gauge to the nearest stream draining at least "
         "20 km2. The other snap rule (largest flow accumulation within 540 m) is shown as the area's sensitivity.", "",
         "## The catchments", "",
         "| Gauge | River (ANA inventory) | DEM area (km2) | Other snap rule (km2) | Snap distance (m) | Share of the dam catchment | Cells outside the dam catchment | Outlet to the OSM river line (m) |",
         "| --- | --- | --- | --- | --- | --- | --- | --- |"]
    for name, (dam, sid, code, river, sar_key) in GAUGES.items():
        g, d = cats[name], cats[dam]
        gm, dm = mask_of(g["runs"]), mask_of(d["runs"])
        outside = len(gm - dm)
        lines = [r["line"] for r in vectors["rivers"] if r.get("name") == river]
        dist = min((dist_to_line_km(g["outlet"]["lat"], g["outlet"]["lon"], ln) for ln in lines), default=None)
        out[name] = {"dam": dam, "sibh_id": sid, "code": code, "river": river, "area_km2": g["area_km2"],
                     "max_rule_area_km2": g.get("max_rule_area_km2"), "snap_m": g.get("snap_m"),
                     "share_of_dam_pct": round(100 * g["area_km2"] / d["area_km2"], 1), "cells_outside_dam": outside,
                     "outlet_to_river_m": None if dist is None else round(dist * 1000), "centroid": g["centroid"]}
        L.append("| %s %s | %s | %.1f | %s | %s | %.0f%% | %d | %s |" % (
            code, sid, river, g["area_km2"], g.get("max_rule_area_km2") or "", g.get("snap_m", ""),
            out[name]["share_of_dam_pct"], outside, "%.0f" % (dist * 1000) if dist is not None else "river not in the map data"))

        # catchment rain for the gauge catchment, as forcing.py does it
        cen = g["centroid"]
        near = sorted((fo.km(cen["lat"], cen["lon"], la, lo), k) for k, (_, la, lo) in fo.ALL_GAUGES.items())
        used = [(dd, k) for dd, k in near if dd <= fo.RADIUS_KM and rain[k]]
        flow = {r["date"]: num(r["discharge_m3s"]) for r in c.read_csv(os.path.join(c.PROCESSED, "sibh_flow_%s.csv" % sid))}
        flow = {k: v for k, v in flow.items() if v is not None}
        first = min(flow)
        rows = []
        d0 = dt.date.fromisoformat(first) - dt.timedelta(days=1)
        day = d0
        while day <= dt.date.today():
            key = day.isoformat()
            v, k = fo.areal(rain, used, key)
            rows.append((key, v, k))
            day += dt.timedelta(days=1)
        c.write_csv(os.path.join(c.PROCESSED, "upstream_rain_%s.csv" % name), ["date", "rain_mm", "gauges_used"], rows)
        g_rain = {k: v for k, v, _ in rows if v is not None}
        out[name]["rain_gauges_used"] = [k for _, k in used]

        dam_f = {r["date"]: num(r["rain_mm"]) for r in c.read_csv(os.path.join(c.PROCESSED, "forcing_%s.csv" % dam))}
        sar = {r["date"]: num(r["inflow_m3s"]) for r in c.read_csv(os.path.join(c.PROCESSED, "sar_%s.csv" % sar_key))}
        years = {}
        for k, q in flow.items():
            y = years.setdefault(k[:4], {"n": 0, "rain": 0.0, "runoff": 0.0, "nd": 0, "drain": 0.0, "drunoff": 0.0})
            if g_rain.get(k) is not None:
                y["n"] += 1
                y["rain"] += g_rain[k]
                y["runoff"] += q * 86.4 / g["area_km2"]
            if dam_f.get(k) is not None and sar.get(k) is not None:
                y["nd"] += 1
                y["drain"] += dam_f[k]
                y["drunoff"] += sar[k] * 86.4 / d["area_km2"]
        out[name]["years"] = {}
        for y, s in sorted(years.items()):
            if s["n"] < MIN_DAYS:
                continue
            rec = {"days": s["n"], "rain_mm": round(s["rain"]), "runoff_mm": round(s["runoff"]),
                   "ratio": round(s["runoff"] / s["rain"], 2) if s["rain"] else None}
            if s["nd"] >= MIN_DAYS:
                rec.update({"dam_days": s["nd"], "dam_rain_mm": round(s["drain"]), "dam_runoff_mm": round(s["drunoff"]),
                            "dam_ratio": round(s["drunoff"] / s["drain"], 2) if s["drain"] else None})
            out[name]["years"][y] = rec

    L += ["", "Nesting holds when no cell lies outside the dam catchment. The outlet distance is from the snapped DEM cell "
          "(90 m) to the mapped river line; under about 100 m means the gauge sits on the river the inventory names.", ""]
    for name, (dam, sid, code, river, _) in GAUGES.items():
        o = out[name]
        L += ["## %s %s above %s: runoff against rain, by year" % (code, river, dam.replace("_dam", "").title()), "",
              "Rain on the gauge catchment from %d gauges within %.0f km of its centroid (audited, inverse-distance weighted). "
              "Runoff depth = discharge x 86.4 / %.1f km2. The dam columns use the operator's daily inflow over the %.1f km2 dam catchment "
              "and forcing.py's rain, on the days both exist. Years with at least %d days." % (
                  len(o["rain_gauges_used"]), fo.RADIUS_KM, o["area_km2"], cats[dam]["area_km2"], MIN_DAYS), "",
              "| Year | Days | Rain (mm) | Gauge runoff (mm) | Gauge runoff ratio | Dam days | Dam rain (mm) | Operator inflow (mm) | Dam runoff ratio |",
              "| --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
        for y, r in o["years"].items():
            L.append("| %s | %d | %d | %d | %.2f | %s | %s | %s | %s |" % (
                y, r["days"], r["rain_mm"], r["runoff_mm"], r["ratio"], r.get("dam_days", ""), r.get("dam_rain_mm", ""),
                r.get("dam_runoff_mm", ""), "%.2f" % r["dam_ratio"] if r.get("dam_ratio") is not None else ""))
        L.append("")
    L += ["## Limits", "",
          "- The areas come from a 90 m surface model (canopy included) and carry the snap uncertainty in the first table; "
          "runoff depth scales inversely with them.",
          "- Gauge discharge is SIBH's unconsolidated telemetric record, from a rating curve the open data do not let us check "
          "(see `sibh_flow_report.md`). 3E-121's rating changed in 2023 and again in 2024: from 2024 the same stage gives "
          "23-41% more discharge, so its 2024 onward runoff is not comparable with earlier years.",
          "- Rain is the same inverse-distance interpolation of point gauges used for the forcing; it is derived, not measured "
          "over the area.",
          "- Calendar years; storage carry-over between years is ignored."]
    with open(os.path.join(c.PROCESSED, "upstream_catchments.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1)
    with open(os.path.join(c.ROOT, "docs", "upstream_catchments.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")
    for name, o in out.items():
        print(name, o["area_km2"], "km2; outside dam:", o["cells_outside_dam"], "; outlet to river:", o["outlet_to_river_m"], "m")
    print("report: docs/upstream_catchments.md")


if __name__ == "__main__":
    main()
