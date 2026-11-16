"""Build daily rain series from the SIBH telemetric gauges, on the same day
convention as ANA's conventional gauges.

Inputs: the hourly sums downloaded by fetch_sibh_rain.py (data/raw/sibh/) and
ANA's daily gauges (data/processed/ana_rain_*.csv). No model output is used.

Rules, fixed here before any daily series was computed:
  1. An hourly sum that is missing a value, negative, or above MAX_HOURLY_MM
     is invalid.
  2. A day is the 24 hours from 07:00 to 07:00 local time (UTC-3; the extra
     hour of daylight saving time before 2019 is ignored), matching the
     morning read of the conventional gauges. A day is kept only if all 24
     hourly sums are present and valid. A missing hour is never taken as zero.
     CEMADEN gauges report only hourly when dry and their transmissions to
     SIBH have gaps, so many of their days fail this rule. That is intended:
     a missing hour cannot be told apart from a dry one.
  3. Which date the 24 hours are labelled with is settled by a data-only
     test. Each SIBH gauge is correlated, day by day, with every ANA gauge
     within PAIR_KM that shares at least MIN_PAIR_DAYS days, under both
     labels: "reading day" (07:00 on D-1 to 07:00 on D is labelled D) and
     "rain day" (07:00 on D to 07:00 on D+1 is labelled D). The label with
     the higher median correlation over all pairs is used for every gauge.
  4. Gauges within COLOCATED_KM of each other (single linkage) count as one
     site, so a site is never weighted twice. The site series is the gauge
     with the most kept days; on days it lacks, the next most complete gauge
     of the site fills in, and so on. Each day records which gauge supplied
     it. Several are the same Sabesp instrument under different codes.
     (The first version of this rule kept only the most complete gauge and
     dropped the others. A dry run on the first five gauges downloaded showed
     that the Sabesp Túnel 6 record moves from code 616 to code 2346798 on
     14 January 2026, so that version discarded all of 2026. The rule was
     changed on that evidence alone, before forcing or any model used it.)

Outputs: data/processed/sibh_rain_<id>.csv (date, rain_mm, readings, gauge)
for every gauge: the site series for the gauge that represents a site, the
gauge's own record otherwise. The station file
data/processed/sibh_rain_stations.json is updated with coverage and the
decisions above, and the report is docs/sibh_rain_report.md.

Usage: python sibh_rain.py
"""
import datetime as dt
import glob
import gzip
import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # isolated mode drops the script folder
import common as c  # noqa: E402
import forcing as fo  # noqa: E402

RAW_DIR = os.path.join(c.RAW, "sibh")
STATIONS = os.path.join(c.PROCESSED, "sibh_rain_stations.json")
REPORT = os.path.join(c.ROOT, "docs", "sibh_rain_report.md")
MAX_HOURLY_MM = 150.0
DAY_START_UTC_H = 10  # 07:00 local (UTC-3)
PAIR_KM = 10.0
MIN_PAIR_DAYS = 180
COLOCATED_KM = 1.0
LABELS = ("reading day", "rain day")


def load_hourly(sid):
    """{datetime (UTC hour): (value or None, readings)} from every raw year file."""
    out = {}
    for path in sorted(glob.glob(os.path.join(RAW_DIR, "rain_%s_*.json.gz" % sid))):
        with gzip.open(path, "rb") as f:
            rows = json.loads(f.read().decode("utf-8")).get("measurements") or []
        for r in rows:
            stamp = str(r.get("date") or "")
            try:
                t = dt.datetime.strptime(stamp[:13], "%Y/%m/%d %H")
            except ValueError:
                continue
            v = r.get("value")
            v = None if v is None else float(v)
            out[t] = (v, int(r.get("qtd") or 0))
    return out


def daily(hourly, label):
    """Kept days {iso date: (rain_mm, readings)} and counts of rejected days."""
    windows = {}
    for t, vq in hourly.items():
        start = (t - dt.timedelta(hours=DAY_START_UTC_H)).date()
        windows.setdefault(start, []).append(vq)
    kept, incomplete, invalid = {}, 0, 0
    for start, hours in windows.items():
        if len(hours) < 24:
            incomplete += 1
            continue
        if any(v is None or v < 0 or v > MAX_HOURLY_MM for v, _ in hours):
            invalid += 1
            continue
        key = start + dt.timedelta(days=1) if label == "reading day" else start
        kept[key.isoformat()] = (round(sum(v for v, _ in hours), 2), sum(q for _, q in hours))
    return kept, incomplete, invalid


def pearson(a, b):
    n = len(a)
    ma, mb = sum(a) / n, sum(b) / n
    sab = sum((x - ma) * (y - mb) for x, y in zip(a, b))
    saa = sum((x - ma) ** 2 for x in a)
    sbb = sum((y - mb) ** 2 for y in b)
    return sab / math.sqrt(saa * sbb) if saa > 0 and sbb > 0 else None


def median(v):
    v = sorted(v)
    return v[len(v) // 2] if len(v) % 2 else (v[len(v) // 2 - 1] + v[len(v) // 2]) / 2.0


def clusters(items, dist):
    """Single-linkage groups of items closer than dist km."""
    groups = []
    for it in items:
        joined = [g for g in groups if any(fo.km(it["lat"], it["lon"], o["lat"], o["lon"]) < dist for o in g)]
        merged = [it]
        for g in joined:
            merged += g
            groups.remove(g)
        groups.append(merged)
    return groups


def merge_site(members):
    """members: [(gauge id, {date: (rain, readings)})], most complete first.
    Returns {date: (rain, readings, gauge id)}: each day from the first member
    that has it."""
    merged = {}
    for gid, days in members:
        for d, (v, q) in days.items():
            merged.setdefault(d, (v, q, gid))
    return merged


def main():
    if not os.path.exists(STATIONS):
        print("no SIBH station file; run fetch_sibh_rain.py first. Skipped.")
        return
    meta = json.load(open(STATIONS, encoding="utf-8"))
    cands = meta["candidates"]
    kept_st = [s for s in cands if not s["excluded"]]
    hourly = {s["id"]: load_hourly(s["id"]) for s in kept_st}
    series = {lab: {s["id"]: daily(hourly[s["id"]], lab) for s in kept_st} for lab in LABELS}

    # Rule 3: day label, from correlation with ANA gauges nearby.
    ana = {code: fo.load_rain(code) for code in fo.RAIN_GAUGES}
    pairs = []
    for s in kept_st:
        for code, (name, la, lo) in fo.RAIN_GAUGES.items():
            d = fo.km(s["lat"], s["lon"], la, lo)
            if d > PAIR_KM or not ana[code]:
                continue
            rs = {}
            for lab in LABELS:
                days = series[lab][s["id"]][0]
                common = sorted(set(days) & set(ana[code]))
                if len(common) >= MIN_PAIR_DAYS:
                    rs[lab] = (pearson([days[k][0] for k in common], [ana[code][k] for k in common]), len(common))
            if len(rs) == len(LABELS) and all(r[0] is not None for r in rs.values()):
                pairs.append((s, code, name, d, rs))
    if not pairs:
        sys.exit("no SIBH-ANA gauge pairs to settle the day label; nothing written")
    med = {lab: median([p[4][lab][0] for p in pairs]) for lab in LABELS}
    label = max(LABELS, key=lambda lab: med[lab])

    # Rule 4: co-located gauges form one site; the most complete gauge leads, the others fill its gaps.
    for s in kept_st:
        s["days_kept"] = len(series[label][s["id"]][0])
    site_of, colocated = {}, []
    sites = {}  # lead id -> {date: (rain, readings, gauge id)}
    for g in clusters(kept_st, COLOCATED_KM):
        g = sorted(g, key=lambda s: (-s["days_kept"], s["id"]))
        if len(g) > 1:
            colocated.append(g)
        lead = g[0]
        for s in g:
            site_of[s["id"]] = lead["id"]
        if lead["days_kept"] == 0:
            continue
        sites[lead["id"]] = merge_site([(s["id"], series[label][s["id"]][0]) for s in g])

    for s in cands:
        if s["excluded"]:
            s["used"] = False
            continue
        days, incomplete, invalid = series[label][s["id"]]
        ds = sorted(days)
        s.update({"hours": len(hourly[s["id"]]), "days_kept": len(ds), "days_incomplete": incomplete,
                  "days_invalid_hour": invalid, "first_day": ds[0] if ds else None, "last_day": ds[-1] if ds else None,
                  "used": s["id"] in sites})
        if s["used"]:
            site = sites[s["id"]]
            s["site_days"] = len(site)
            s["site_filled_from"] = sorted({g for _, _, g in site.values()} - {s["id"]})
            rows = [(d,) + site[d] for d in sorted(site)]
        else:
            s["not_used"] = ("no complete day" if not ds else
                             "co-located with %s, which leads the site; this gauge fills its gaps" % site_of[s["id"]])
            rows = [(d, days[d][0], days[d][1], s["id"]) for d in ds]
        c.write_csv(os.path.join(c.PROCESSED, "sibh_rain_%s.csv" % s["id"]), ["date", "rain_mm", "readings", "gauge"], rows)
    meta.update({"day_label": label, "day_window": "07:00 to 07:00 local (UTC-3)",
                 "rules": {"max_hourly_mm": MAX_HOURLY_MM, "complete_day": "all 24 hourly sums present and valid",
                           "label_test": "median correlation with ANA gauges within %.0f km, at least %d shared days" % (PAIR_KM, MIN_PAIR_DAYS),
                           "colocated_km": COLOCATED_KM}})
    with open(STATIONS, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=1)

    # Report.
    now = dt.datetime.utcnow().strftime("%Y-%m-%d %H:%M")
    L = ["# Telemetric rain gauges from SIBH", "",
         "Generated %s UTC by `pipeline/sibh_rain.py` from hourly sums downloaded by `pipeline/fetch_sibh_rain.py` "
         "(SP Águas SIBH public API, retrieved %s). No model output is used." % (now, meta["retrieved"]), "",
         "## Selection", "",
         "Rain stations in SIBH within %.0f km of either catchment centroid: %d. Excluded before download: %d "
         "(ANA-owned, radar products, or conventional gauges already taken from ANA). Downloaded: %d. "
         "Sites after the co-location rule (each enters the forcing once): %d." % (
             meta["radius_km"], len(cands), sum(1 for s in cands if s["excluded"]), len(kept_st), len(sites)), "",
         "## Which date a day is labelled with (rule 3)", "",
         "Pairs of SIBH and ANA gauges within %.0f km with at least %d shared complete days: %d. "
         "Median daily correlation: %s. **Label used: %s.**" % (
             PAIR_KM, MIN_PAIR_DAYS, len(pairs), "; ".join("%s %.3f" % (lab, med[lab]) for lab in LABELS), label), "",
         "In words: ANA's daily rain labelled D is %s." % (
             "the 24 hours ending at 07:00 on D, i.e. mostly rain that fell on D-1" if label == "reading day"
             else "the 24 hours starting at 07:00 on D"), "",
         "| SIBH gauge | ANA gauge | Distance (km) | Shared days | r, reading day | r, rain day |",
         "| --- | --- | --- | --- | --- | --- |"]
    for s, code, name, d, rs in sorted(pairs, key=lambda p: (p[0]["id"], p[3])):
        L.append("| %s %s (%s) | %s %s | %.1f | %d | %.3f | %.3f |" % (
            s["id"], s["name"], s["owner"], code, name, d, rs[LABELS[0]][1], rs[LABELS[0]][0], rs[LABELS[1]][0]))
    L += ["", "## Gauges", "",
          "A day is kept only if all 24 hourly sums are present and none is negative or above %.0f mm. "
          "Distances are to the nearer catchment centroid." % MAX_HOURLY_MM, "",
          "| SIBH id | Code | Operator | Name | km | Hours on record | Complete days | Days with missing hours | Days with an invalid hour | First kept day | Last kept day | Used |",
          "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
    for s in kept_st:
        L.append("| %s | %s | %s | %s | %.1f | %d | %d | %d | %d | %s | %s | %s |" % (
            s["id"], s["prefix"], s["owner"], s["name"], min(s["km_to_centroid"].values()), s["hours"], s["days_kept"],
            s["days_incomplete"], s["days_invalid_hour"], s["first_day"] or "", s["last_day"] or "",
            ("yes, leads its site (%d days%s)" % (s["site_days"], ", gaps filled from " + ", ".join(s["site_filled_from"])
                                                  if s["site_filled_from"] else "")) if s["used"] else "no: " + s["not_used"]))
    L += ["", "### Excluded before download", "", "| SIBH id | Code | Operator | Name | Reason |", "| --- | --- | --- | --- | --- |"]
    for s in cands:
        if s["excluded"]:
            L.append("| %s | %s | %s | %s | %s |" % (s["id"], s["prefix"], s["owner"], s["name"], s["excluded"]))
    L += ["", "### Co-located groups (rule 4)", "", "The first gauge listed leads the site; the others fill its missing days, in order.", ""]
    for g in colocated:
        L.append("- " + "; ".join("%s %s (%s, %d days)" % (s["id"], s["name"], s["owner"], s["days_kept"]) for s in g))
    years = range(2010, dt.date.today().year + 1)
    L += ["", "## Complete days per year, by site", "",
          "| Site (lead SIBH id) | Name | " + " | ".join(str(y) for y in years) + " |",
          "| --- | --- |" + " --- |" * len(years)]
    for s in kept_st:
        if not s["used"]:
            continue
        days = sites[s["id"]]
        L.append("| %s | %s | %s |" % (s["id"], s["name"], " | ".join(
            str(sum(1 for d in days if d.startswith(str(y)))) for y in years)))
    with open(REPORT, "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")
    print("day label:", label, med)
    print("sites:", len(sites), "from", len(kept_st), "gauges downloaded")
    print("report:", os.path.relpath(REPORT, c.ROOT) if os.path.splitdrive(REPORT)[0] == os.path.splitdrive(c.ROOT)[0] else REPORT)


if __name__ == "__main__":
    main()
