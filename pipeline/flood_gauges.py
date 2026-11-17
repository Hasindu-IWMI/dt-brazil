"""Daily river level at Atibaia town and above the Salto Grande plant, and the floods since 2015.

Reads the hourly SIBH records stored by fetch_flood_stations.py:
  3E-063  SP Águas, Rio Atibaia at Av. São João, Atibaia town (SIBH id 30863)
  62671200  ANA, Rio Atibaia above the Salto Grande plant, 4 km downstream (SIBH id 14585)

Daily values, by the rule sibh_flow.py uses: a local calendar day (UTC-3), kept
if at least 18 hourly means are valid, never filled.
  max_cm   the highest hourly mean level that day (cm, the gauge's own zero):
           the flood signal
  mean_cm  the mean level
  q_m3s    mean discharge, where SIBH gives one (3E-063 only; from SP Águas'
           rating)

Hourly levels above CAP_CM are dropped before the daily rule, as instrument
faults: at 62671200 four days read 45 to 460 m (2024-03-05, 2025-05-18,
2025-07-08, 2025-11-10), at a station whose level otherwise stays below 9 m
(median 2.9 m). Nothing else is removed. December 2015 at 62671200 reads 5 to
9 m while the town gauge stays below 3.2 m; that is unexplained and kept.

SP Águas' alarm levels for 3E-063 (attention, alert, emergency, overflow) are
copied from its station record in SIBH.

Floods (derived, and labelled so): runs of days whose maximum reaches the
overflow level, joined when less than 10 days apart; for each, the first and
last day, the peak day and its maximum level and mean discharge.

Outputs: data/processed/flood_daily_3E-063.csv, flood_daily_62671200.csv,
flood_gauges.json.

Usage: python flood_gauges.py
"""
import datetime as dt
import glob
import gzip
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # isolated mode drops the script folder
import common as c  # noqa: E402

SIBH = os.path.join(c.RAW, "sibh")
STATIONS = {"30863": "3E-063", "14585": "62671200"}
MIN_HOURS, JOIN_DAYS = 18, 10
CAP_CM = 1000  # hourly level above this (10 m) is an instrument fault at either station
LEVELS = ("attention", "alert", "emergency", "extravasation")


def find_keys(obj, keys, out):
    """First non-empty value of each key anywhere in a nested JSON record."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in keys and k not in out and v not in (None, ""):
                out[k] = v
            find_keys(v, keys, out)
    elif isinstance(obj, list):
        for v in obj:
            find_keys(v, keys, out)
    return out


def daily(sid):
    days = {}
    for path in sorted(glob.glob(os.path.join(SIBH, "flood_%s_[0-9][0-9][0-9][0-9].json.gz" % sid))):
        for r in json.load(gzip.open(path, "rt", encoding="utf-8")).get("measurements") or []:
            t = dt.datetime.strptime(str(r["date"])[:13], "%Y/%m/%d %H") - dt.timedelta(hours=3)
            d = days.setdefault(t.date().isoformat(), {"lv": [], "q": []})
            if r.get("value") is not None and float(r["value"]) <= CAP_CM:
                d["lv"].append(float(r["value"]))
            if r.get("read_value") is not None:
                d["q"].append(float(r["read_value"]))
    rows = []
    for day in sorted(days):
        lv, q = days[day]["lv"], days[day]["q"]
        if len(lv) < MIN_HOURS:
            continue
        rows.append([day, round(max(lv), 1), round(sum(lv) / len(lv), 1),
                     round(sum(q) / len(q), 2) if len(q) >= MIN_HOURS else None, len(lv)])
    return rows


def main():
    meta = {}
    for sid, code in STATIONS.items():
        rec = {}
        for f in ("flood_station_%s.json.gz" % sid, "flood_prefix_%s.json.gz" % sid):
            p = os.path.join(SIBH, f)
            if os.path.exists(p):
                find_keys(json.load(gzip.open(p, "rt", encoding="utf-8")), set(LEVELS) | {"latitude", "longitude", "name"}, rec)
        rows = daily(sid)
        c.write_csv(os.path.join(c.PROCESSED, "flood_daily_%s.csv" % code), ["date", "max_cm", "mean_cm", "q_m3s", "hours"], rows)
        meta[code] = {"sibh_id": sid, "name": rec.get("name"), "lat": float(rec["latitude"]), "lon": float(rec["longitude"]),
                      "levels_cm": {k: float(rec[k]) for k in LEVELS if k in rec}, "days": len(rows),
                      "first": rows[0][0] if rows else None, "last": rows[-1][0] if rows else None, "rows": rows}
        print("%-9s %5d days %s to %s; alarm levels %s" % (code, len(rows), meta[code]["first"], meta[code]["last"], meta[code]["levels_cm"] or "none published"))

    town = meta["3E-063"]
    over = town["levels_cm"]["extravasation"]
    above = [r for r in town["rows"] if r[1] >= over]
    events = []
    for r in above:
        d = dt.date.fromisoformat(r[0])
        if events and (d - dt.date.fromisoformat(events[-1]["last"])).days < JOIN_DAYS:
            e = events[-1]
            e["last"] = r[0]
            e["days_above"] += 1
            if r[1] > e["peak_cm"]:
                e.update({"peak_date": r[0], "peak_cm": r[1], "peak_q_m3s": r[3]})
        else:
            events.append({"first": r[0], "last": r[0], "days_above": 1, "peak_date": r[0], "peak_cm": r[1], "peak_q_m3s": r[3]})
    out = {"source": "SP Águas SIBH public API: hourly means of 10-minute readings (pipeline/fetch_flood_stations.py)",
           "day_rule": "local calendar day (UTC-3), kept if at least %d hourly means are valid; never filled" % MIN_HOURS,
           "stations": {k: {kk: vv for kk, vv in v.items() if kk != "rows"} for k, v in meta.items()},
           "events_rule": "DERIVED: days whose highest hourly level at 3E-063 reaches the overflow level (%g cm), joined when "
                          "less than %d days apart" % (over, JOIN_DAYS),
           "events": events}
    with open(os.path.join(c.PROCESSED, "flood_gauges.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    top = sorted(events, key=lambda e: -e["peak_cm"])[:5]
    print("floods (day maximum >= %g cm): %d since %s; highest: %s" % (over, len(events), town["first"],
          ", ".join("%s %.0f cm" % (e["peak_date"], e["peak_cm"]) for e in top)))


if __name__ == "__main__":
    main()
