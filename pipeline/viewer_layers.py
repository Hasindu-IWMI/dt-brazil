"""Package the rain, river and tunnel records for the 3D viewer (web/public/data/layers.json).

Everything here is copied from the processed records, or derived by a formula stated
in the output; nothing is simulated or filled. Each series is a contiguous daily
array from its first date; null is a day without a record (or one the audit excluded).

  rain_sites      audited daily rain at every gauge forcing.py may use (ANA and SIBH)
  catchment_rain  DERIVED: inverse-distance-weighted catchment rain (forcing.py and
                  upstream_catchments.py), for the dam and upstream-gauge catchments
  flow_stations   observed daily discharge: gauges above and below the dams, tunnel outlets
  tunnels         the transfers between reservoirs. An end is a measuring station where one
                  exists; otherwise the nearest point of the reservoir it connects to, marked
                  "schematic". The underground alignments are not in the data used.
  catchments      cell masks (row runs on the 3 arc-second delineation grid) for draping
                  catchments on the terrain

Usage: python viewer_layers.py
"""
import datetime as dt
import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # isolated mode drops the script folder
import common as c  # noqa: E402
import forcing as fo  # noqa: E402

WEB = os.path.join(c.ROOT, "web", "public", "data")
# flow stations shown, by SIBH id: role, short label. Duplicate Sabesp codes (361, 349) are left out:
# they cover the same sites for 184 days and add nothing to 12 and 18.
FLOW = {
    "1430": ("upstream", "Rio da Cachoeira above the lake (3E-122)"),
    "1397": ("upstream", "Rio Atibainha above the lake (3E-121)"),
    "30862": ("below_dam", "Rio Cachoeira at Piracaia intake (3E-116)"),
    "832": ("below_dam", "Rio Cachoeira at Piracaia centre (3E-145)"),
    "12": ("tunnel", "Tunnel 6 outlet (616)"),
    "18": ("tunnel", "Tunnel 5 outlet (309)"),
}
UPSTREAM = {"1430": "cachoeira_upstream_gauge", "1397": "atibainha_upstream_gauge"}
# reservoir OSM outlines (as in web/src/main.js)
OUTLINES = {"relation/2319460": "atibainha", "relation/2906093": "cachoeira",
            "relation/452185": "jaguari_jacarei", "relation/7004538": "jaguari_jacarei"}
# name, from, to, end A (station id or reservoir), end B, station measuring the flow (or None), what is known
TUNNELS = [
    ("Tunnel 7", "Jaguari-Jacareí", "Cachoeira", ("station", "6"), ("reservoir", "cachoeira"), None,
     "Water level at the intake only; no public flow record."),
    ("Tunnel 6", "Cachoeira", "Atibainha", ("reservoir", "cachoeira"), ("station", "12"), "12",
     "Flow measured at the outlet (SAISP 616)."),
    ("Tunnel 5", "Atibainha", "Paiva Castro", ("station", "16"), ("station", "18"), "18",
     "Flow measured at the outlet (Sabesp 309)."),
    ("Paraíba do Sul transfer", "Jaguari (Paraíba do Sul)", "Atibainha", ("station", "35354"), ("reservoir", "atibainha"), None,
     "Water level at the pumping station only; no public flow record (both transfer codes in SIBH are empty)."),
]


def num(v):
    try:
        return None if v in ("", None) else float(v)
    except ValueError:
        return None


def contiguous(series, dates, digits):
    """{date: value} -> (first date, list aligned to the viewer's dates from that date)."""
    keys = [d for d in dates if series.get(d) is not None]
    if not keys:
        return None, []
    i0 = dates.index(keys[0])
    i1 = dates.index(keys[-1])
    return keys[0], [None if series.get(d) is None else round(series[d], digits) for d in dates[i0:i1 + 1]]


def nearest_shore(lat, lon, rings):
    best = None
    for ring in rings:
        for x, y in ring:
            d = math.hypot((x - lon) * math.cos(math.radians(lat)), y - lat)
            if best is None or d < best[0]:
                best = (d, [round(x, 5), round(y, 5)])
    return best[1]


def main():
    dates = json.load(open(os.path.join(WEB, "timeseries.json"), encoding="utf-8"))["dates"]
    excl = json.load(open(os.path.join(c.PROCESSED, "rain_exclusions.json"), encoding="utf-8"))
    cats = json.load(open(os.path.join(c.PROCESSED, "catchments.json"), encoding="utf-8"))
    up = json.load(open(os.path.join(c.PROCESSED, "upstream_catchments.json"), encoding="utf-8"))
    flow_meta = {s["id"]: s for s in json.load(open(os.path.join(c.PROCESSED, "sibh_flow_stations.json"), encoding="utf-8"))["stations"]}
    sibh_meta = {"SIBH-" + s["id"]: s for s in json.load(open(os.path.join(c.PROCESSED, "sibh_rain_stations.json"), encoding="utf-8"))["candidates"]}

    out = {"generated_utc": dt.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
           "provenance": {
               "rain_sites": "Daily rain (mm) at ANA conventional gauges (HidroSerieHistorica) and SIBH telemetric sites, audited by pipeline/audit_rain.py; ANA's day D = 24 h ending 07:00 on D.",
               "catchment_rain": "DERIVED: inverse-distance-squared mean of the audited gauges within 20 km of each catchment centroid (pipeline/forcing.py, pipeline/upstream_catchments.py).",
               "flow_stations": "Observed daily mean discharge (m3/s) from SIBH telemetry (pipeline/sibh_flow.py); rating curves are not checkable from open data.",
               "tunnels": "Routes are schematic: an end is a measuring station where one exists, otherwise the nearest shore of the connected reservoir. Underground alignments are not in the data used.",
               "catchments": "Delineated from Copernicus GLO-30 at 3 arc-seconds (pipeline/delineate.py)."},
           "rain_sites": [], "catchment_rain": {}, "flow_stations": [], "tunnels": [], "catchments": {}}

    for code, (name, lat, lon) in fo.ALL_GAUGES.items():
        first, mm = contiguous(fo.load_rain(code, excl), dates, 1)
        if first is None:
            continue
        s = sibh_meta.get(code)
        out["rain_sites"].append({"code": code, "name": s["name"] if s else name, "operator": s["owner"] if s else "ANA network",
                                  "kind": "telemetric" if s else "conventional", "lat": lat, "lon": lon, "first": first, "mm": mm})

    labels = {"cachoeira_dam": "Cachoeira dam catchment", "atibainha_dam": "Atibainha dam catchment",
              "cachoeira_upstream_gauge": "Rio da Cachoeira above the lake (3E-122)", "atibainha_upstream_gauge": "Rio Atibainha above the lake (3E-121)"}
    for name in ("cachoeira_dam", "atibainha_dam"):
        rows = {r["date"]: num(r["rain_mm"]) for r in c.read_csv(os.path.join(c.PROCESSED, "forcing_%s.csv" % name))}
        first, mm = contiguous(rows, dates, 1)
        out["catchment_rain"][name] = {"label": labels[name], "area_km2": cats["catchments"][name]["area_km2"], "first": first, "mm": mm}
    for name in ("cachoeira_upstream_gauge", "atibainha_upstream_gauge"):
        rows = {r["date"]: num(r["rain_mm"]) for r in c.read_csv(os.path.join(c.PROCESSED, "upstream_rain_%s.csv" % name))}
        first, mm = contiguous(rows, dates, 1)
        out["catchment_rain"][name] = {"label": labels[name], "area_km2": up[name]["area_km2"], "first": first, "mm": mm}

    for sid, (role, label) in FLOW.items():
        rows = {r["date"]: num(r["discharge_m3s"]) for r in c.read_csv(os.path.join(c.PROCESSED, "sibh_flow_%s.csv" % sid))}
        first, q = contiguous(rows, dates, 2)
        m = flow_meta[sid]
        rec = {"id": sid, "code": m["prefix"], "label": label, "role": role, "lat": m["lat"], "lon": m["lon"], "first": first, "q": q}
        if sid in UPSTREAM:  # runoff depth needs the DEM area
            rec.update({"catchment": UPSTREAM[sid], "area_km2": up[UPSTREAM[sid]]["area_km2"],
                        "max_rule_area_km2": up[UPSTREAM[sid]]["max_rule_area_km2"]})
        out["flow_stations"].append(rec)

    vectors = json.load(open(os.path.join(WEB, "vectors.json"), encoding="utf-8"))
    rings = {}
    for w in vectors["waters"]:
        key = OUTLINES.get(w["id"])
        if key:
            rings.setdefault(key, []).extend(w["rings"])
    for name, frm, to, a, b, station, note in TUNNELS:
        ends = []
        for kind, ref in (a, b):
            if kind == "station":
                m = flow_meta[ref]
                ends.append({"lon": m["lon"], "lat": m["lat"], "is": "station", "station": ref, "name": m["name"]})
            else:
                other = b if (kind, ref) == a else a
                om = flow_meta[other[1]]
                lon, lat = nearest_shore(om["lat"], om["lon"], rings[ref])
                ends.append({"lon": lon, "lat": lat, "is": "schematic", "reservoir": ref})
        out["tunnels"].append({"name": name, "from": frm, "to": to, "a": ends[0], "b": ends[1], "station": station,
                               "measured": station is not None, "note": note})

    grid = {k: cats["dem"][k] for k in ("bbox", "width", "height")}
    out["catchments"] = {"grid": grid, "masks": {
        name: {"label": labels.get(name, name.replace("_", " ")), "area_km2": v["area_km2"], "runs": v["runs"],
               "role": "upstream" if name in UPSTREAM.values() else "dam" if name.endswith("_dam") else "gauge"}
        for name, v in cats["catchments"].items() if name in labels}}

    with open(os.path.join(WEB, "layers.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, separators=(",", ":"))
    size = os.path.getsize(os.path.join(WEB, "layers.json"))
    print("layers.json: %d rain sites, %d flow stations, %d tunnels, %d catchments, %.1f MB" % (
        len(out["rain_sites"]), len(out["flow_stations"]), len(out["tunnels"]), len(out["catchments"]["masks"]), size / 1e6))


if __name__ == "__main__":
    main()
