"""Build daily series from the SIBH river, dam and transfer stations, and
compare them with the reservoir records.

Inputs: the hourly means downloaded by fetch_sibh_flow.py (data/raw/sibh/);
ANA's SAR reservoir records (data/processed/sar_*.csv); ANA's daily river
gauges (data/processed/ana_discharge_*.csv); and the catchment rain
(data/processed/forcing_*_dam.csv), used only to pick rainless days. No
model is run and no model output is used.

Rules, fixed here before any daily series was computed:
  1. Variables. `value` is a water level in cm and becomes level_m (value /
     100). `read_value` is discharge in m3/s, computed by SIBH from the level
     with the station's rating curve. This was found by probing (see
     fetch_sibh_flow.py) and is re-checked here, on every hour, in two ways:
     (a) where SIBH publishes a rating curve in force for that hour and
     level, the curve Q = a (h - ho)^n must reproduce read_value to within
     CURVE_TOL (relative) or 0.005 m3/s; (b) a station whose median level is
     above 100 m reads a water-surface elevation, which for stations in a
     reservoir is compared with the level ANA's SAR gives for that day.
     A station whose level is below 100 m reads stage above its gauge zero.
     (Correction after a dry run on the first two gauges, before any
     comparison was used: 3E-122 takes its records from ANA's web service,
     and its discharge follows one fixed stage-discharge relation from 2015
     to 2026 that is not among the curves SIBH publishes for it; check (a)
     matched 111 of 1,434 hours. So read_value is discharge from a rating
     curve, but not always from SIBH's published one. No rule that computes
     a series changed. The report gained a table of the rating in use by
     year, the discharge given at fixed stages, so rating changes show.)
     (Second correction, after the first full run and before its results
     were used: the six Sabesp codes with 8-digit prefixes, listed in
     VALUE_IN_METRES, serve `value` in metres. On every hour they share with
     their twin codes they give the twin's value divided by 100, and the
     same discharge. And the two downstream-channel stations changed datum
     in October-November 2022, from stage above a gauge zero (2.5-3.1 m at
     Cachoeira, 6.3-7.7 m at Atibainha) to elevation (791-792 m and
     758-759 m). The first version took one median for the whole record, so
     rule 2 silently rejected the other datum: 8,952 and 35,418 hours. Rule 2
     now works within each datum, and each day records its datum.)
  2. Each hourly level belongs to a datum: elevation if above
     ELEVATION_ABOVE_M, gauge zero otherwise. An hourly mean is invalid if
     it is missing; a level more than LEVEL_BAND_M from the station's median
     level in the same datum (a gross-error filter only); or a discharge that
     is negative or above MAX_Q_M3S. A day takes the datum of most of its
     valid hours; hours in the other datum are dropped that day. A datum with
     fewer than MIN_DATUM_DAYS kept days at a station, where the other datum
     has more, is dropped entirely (a stray value cannot start a datum of its
     own). No spike or flat-line
     filter is applied. The report counts kept days on which the level or
     discharge did not change at all (a possible stuck sensor).
  3. A day is the local calendar day, 00:00 to 24:00 at UTC-3 (03:00 UTC to
     03:00 UTC; the extra hour of daylight saving time before 2019 is
     ignored). This is the day of ANA's conventional river gauges, read at
     07:00 and 17:00. SAR's day is not documented; comparisons with SAR are
     shown with SAR shifted by one day either way, and the series are not
     shifted.
  4. A day is kept for a variable if at least MIN_HOURS of its 24 hours have
     a valid hourly mean for that variable. The daily value is the mean of
     those hourly means, each hour weighted equally. A missing hour is never
     filled.
  5. Sites recorded under two codes (SAISP and Sabesp, or an old and a new
     Sabesp prefix) are not merged. Each code keeps its own series and the
     report compares them where they overlap.
  6. Rainless days, used only to compare noise in the gauge and in SAR's
     inflow: catchment rain (audited, forcing_*_dam.csv) below RAINLESS_MM
     on the day and on each of the five days before it.

Outputs: data/processed/sibh_flow_<id>.csv (date, level_m, level_datum,
discharge_m3s, level_hours, discharge_hours) for every station with at least
one kept day; level_datum is "gauge" (stage above the gauge zero) or
"elevation" (water-surface elevation);
data/processed/sibh_flow_stations.json updated with what each station holds;
the report docs/sibh_flow_report.md.

Usage: python sibh_flow.py
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

RAW_DIR = os.path.join(c.RAW, "sibh")
STATIONS = os.path.join(c.PROCESSED, "sibh_flow_stations.json")
REPORT = os.path.join(c.ROOT, "docs", "sibh_flow_report.md")
LOCAL_OFFSET_H = 3        # UTC-3
MIN_HOURS = 18
MIN_DATUM_DAYS = 30
LEVEL_BAND_M = 50.0
MAX_Q_M3S = 1000.0
CURVE_TOL = 0.02
ELEVATION_ABOVE_M = 100.0
RAINLESS_MM = 1.0
RAINLESS_DAYS = 6
SHORTFALL_M3S = 0.5       # the threshold process.py uses for gauge-below-release days
HM3_PER_DAY_TO_M3S = 1e6 / 86400.0
LAGS = (-1, 0, 1)
FIELDS = ("level", "discharge")

# Which reservoir each gauge above the reservoirs drains to.
INFLOW_OF = {"1397": "atibainha", "1430": "cachoeira"}
# Which SAR reservoir each in-reservoir station sits in (rule 1b).
RESERVOIR_OF = {"10": "cachoeira", "362": "cachoeira", "14": "atibainha", "360": "atibainha",
                "16": "atibainha", "6": "jaguari_jacarei", "358": "jaguari_jacarei"}
# Sabesp codes that serve `value` in metres (rule 1, second correction).
VALUE_IN_METRES = {"362", "360", "361", "349", "358", "238"}
DUPLICATES = [("10", "362"), ("14", "360"), ("12", "361"), ("18", "349"), ("6", "358"), ("35414", "35609"),
              ("35354", "238")]


# ---------------------------------------------------------------- reading ----
def parse_hour(stamp):
    try:
        return dt.datetime.strptime(str(stamp)[:13], "%Y/%m/%d %H")
    except ValueError:
        return None


def num(v):
    if v is None:
        return None
    try:
        v = float(v)
    except (TypeError, ValueError):
        return None
    return v if math.isfinite(v) else None


def load_hourly(sid):
    """{UTC hour: (level_m or None, discharge or None, readings)} from every raw year file."""
    out = {}
    for path in sorted(glob.glob(os.path.join(RAW_DIR, "flow_%s_[0-9][0-9][0-9][0-9].json.gz" % sid))):
        with gzip.open(path, "rb") as f:
            rows = json.loads(f.read().decode("utf-8")).get("measurements") or []
        for r in rows:
            t = parse_hour(r.get("date"))
            if t is None:
                continue
            v = num(r.get("value"))
            if v is not None:
                v = round(v if sid in VALUE_IN_METRES else v / 100.0, 6)
            out[t] = (v, num(r.get("read_value")), int(num(r.get("qtd")) or 0))
    return out


def load_curves(sid):
    path = os.path.join(RAW_DIR, "flow_curves_%s.json.gz" % sid)
    if not os.path.exists(path):
        return []
    with gzip.open(path, "rb") as f:
        rows = json.loads(f.read().decode("utf-8")) or []
    out = []
    for k in rows:
        try:
            start = dt.datetime.strptime(k["start_date"][:10], "%Y-%m-%d")
            end = dt.datetime.strptime(k["end_date"][:10], "%Y-%m-%d") + dt.timedelta(days=1) if k.get("end_date") else None
            out.append({"start": start, "end": end, "a": float(k["a"]), "n": float(k["n"]), "ho": float(k["ho"]),
                        "hmin": float(k["min_value"]), "hmax": float(k["max_value"]), "id": k.get("id")})
        except (KeyError, TypeError, ValueError):
            continue
    return out


def load_prefix(sid):
    """Data source and creation date from the station-prefix record, if stored."""
    path = os.path.join(RAW_DIR, "flow_prefix_%s.json.gz" % sid)
    if not os.path.exists(path):
        return {}
    with gzip.open(path, "rb") as f:
        p = json.loads(f.read().decode("utf-8")) or {}
    return {"data_source": p.get("data_source") or "", "created_in_sibh": str(p.get("created_at") or "")[:10]}


def rating_by_year(hourly, tol_m=0.01, min_hours=5):
    """The rating in use, without fitting anything: the station's median and
    90th-percentile stage over all hours with both values, and for each year
    the median discharge SIBH gives at hours within tol_m of those stages.
    Returns ((stage50, stage90), {year: (q50 or None, q90 or None)})."""
    pts = [(t.year, h, q) for t, (h, q, _) in hourly.items() if h is not None and q is not None]
    if not pts:
        return None, {}
    hs = sorted(h for _, h, _ in pts)
    stages = (hs[len(hs) // 2], hs[min(len(hs) - 1, int(0.9 * len(hs)))])
    out = {}
    for y in sorted({y for y, _, _ in pts}):
        cells = []
        for s in stages:
            near = [q for yy, h, q in pts if yy == y and abs(h - s) <= tol_m]
            cells.append(median(near) if len(near) >= min_hours else None)
        out[y] = tuple(cells)
    return stages, out


def curve_q(k, h):
    """Discharge from a power-law rating curve, h in m."""
    return k["a"] * max(h - k["ho"], 0.0) ** k["n"]


def curve_check(hourly, curves):
    """Rule 1a. Returns (hours with a published curve in force, hours it reproduces)."""
    checked = matched = 0
    for t, (h, q, _) in hourly.items():
        if h is None or q is None:
            continue
        cands = [k for k in curves if k["start"] <= t and (k["end"] is None or t < k["end"]) and k["hmin"] <= h <= k["hmax"]]
        if not cands:
            continue
        checked += 1
        if any(abs(curve_q(k, h) - q) <= max(CURVE_TOL * q, 0.005) for k in cands):
            matched += 1
    return checked, matched


# ------------------------------------------------------------ daily series ----
def median(v):
    v = sorted(v)
    if not v:
        return None
    return v[len(v) // 2] if len(v) % 2 else (v[len(v) // 2 - 1] + v[len(v) // 2]) / 2.0


def local_day(t):
    return (t - dt.timedelta(hours=LOCAL_OFFSET_H)).date().isoformat()


def datum_of(h):
    return "elevation" if h > ELEVATION_ABOVE_M else "gauge"


def valid(field, x, level_median):
    """Rule 2. level_median: the station's median level in the same datum."""
    if x is None:
        return False
    if field == "level":
        return level_median is not None and abs(x - level_median) <= LEVEL_BAND_M
    return 0.0 <= x <= MAX_Q_M3S


def daily(hourly):
    """Rules 2-4. Returns ({"level"|"discharge": {date: (mean, hours)}, "datum": {date: datum}},
    stats, {datum: median level})."""
    medians = {dat: median([h for h, _, _ in hourly.values() if h is not None and datum_of(h) == dat])
               for dat in ("gauge", "elevation")}
    hours = {f: {} for f in FIELDS}
    stats = {f: {"hours": 0, "invalid_hours": 0, "days_short": 0, "flat_days": 0, "other_datum_hours": 0,
                 "dropped_datum_days": 0} for f in FIELDS}
    for t, (h, q, _) in hourly.items():
        for f, x in (("level", h), ("discharge", q)):
            if x is None:
                continue
            stats[f]["hours"] += 1
            if not valid(f, x, medians[datum_of(x)] if f == "level" else None):
                stats[f]["invalid_hours"] += 1
                continue
            hours[f].setdefault(local_day(t), []).append(x)
    days = {"level": {}, "discharge": {}, "datum": {}}
    for f in FIELDS:
        for d, xs in hours[f].items():
            dat = None
            if f == "level":
                by = {}
                for x in xs:
                    by.setdefault(datum_of(x), []).append(x)
                dat = max(by, key=lambda k: (len(by[k]), k))
                stats[f]["other_datum_hours"] += len(xs) - len(by[dat])
                xs = by[dat]
            if len(xs) < MIN_HOURS:
                stats[f]["days_short"] += 1
                continue
            days[f][d] = (sum(xs) / len(xs), len(xs))
            if dat:
                days["datum"][d] = dat
            if max(xs) == min(xs):
                stats[f]["flat_days"] += 1
    count = {dat: sum(1 for k in days["datum"].values() if k == dat) for dat in ("gauge", "elevation")}
    for dat, other in (("gauge", "elevation"), ("elevation", "gauge")):
        ds = [d for d, k in days["datum"].items() if k == dat]
        if 0 < len(ds) < MIN_DATUM_DAYS and count[other] > len(ds):
            for d in ds:
                del days["level"][d], days["datum"][d]
            stats["level"]["dropped_datum_days"] += len(ds)
    return days, stats, medians


def station_rows(days):
    dates = sorted(set(days["level"]) | set(days["discharge"]))
    rows = []
    for d in dates:
        lv, qv = days["level"].get(d), days["discharge"].get(d)
        rows.append((d, None if lv is None else round(lv[0], 4), days["datum"].get(d),
                     None if qv is None else round(qv[0], 4),
                     None if lv is None else lv[1], None if qv is None else qv[1]))
    return rows


def datum_spans(datums):
    """[(datum, first day, last day, days)] in date order, one entry per run of the same datum."""
    out = []
    for d in sorted(datums):
        k = datums[d]
        if out and out[-1][0] == k:
            out[-1] = (k, out[-1][1], d, out[-1][3] + 1)
        else:
            out.append((k, d, d, 1))
    return out


def level_kind(datums):
    """'stage', 'elevation', or e.g. 'stage to 2022-10-31, then elevation'. Runs shorter than
    MIN_DATUM_DAYS are ignored."""
    names = {"gauge": "stage", "elevation": "elevation"}
    merged = []
    for k, a, b, n in datum_spans(datums):
        if n < MIN_DATUM_DAYS:
            continue
        if merged and merged[-1][0] == k:
            merged[-1] = (k, merged[-1][1], b)
        else:
            merged.append((k, a, b))
    if not merged:
        return None
    return ", then ".join("%s to %s" % (names[k], b) if i < len(merged) - 1 else names[k]
                          for i, (k, a, b) in enumerate(merged))


def by_datum(level, datums, dat):
    return {d: v for d, v in level.items() if datums.get(d) == dat}


# ------------------------------------------------------------ comparisons ----
def pearson(a, b):
    n = len(a)
    if n < 3:
        return None
    ma, mb = sum(a) / n, sum(b) / n
    sab = sum((x - ma) * (y - mb) for x, y in zip(a, b))
    saa = sum((x - ma) ** 2 for x in a)
    sbb = sum((y - mb) ** 2 for y in b)
    return sab / math.sqrt(saa * sbb) if saa > 0 and sbb > 0 else None


def ranks(v):
    """Average ranks (ties share the mean rank)."""
    order = sorted(range(len(v)), key=lambda i: v[i])
    r = [0.0] * len(v)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and v[order[j + 1]] == v[order[i]]:
            j += 1
        for k in range(i, j + 1):
            r[order[k]] = (i + j) / 2.0 + 1
        i = j + 1
    return r


def spearman(a, b):
    return pearson(ranks(a), ranks(b))


def shift(d, k):
    return (dt.date.fromisoformat(d) + dt.timedelta(days=k)).isoformat()


def paired(a, b, lag=0, year=None):
    """[(a on D, b on D+lag)] for every D where both exist (D in `year` if given). a, b: {date: value}."""
    return [(a[d], b[shift(d, lag)]) for d in sorted(a)
            if shift(d, lag) in b and (year is None or d.startswith(str(year)))]


def best_lag(res):
    return max(LAGS, key=lambda k: res[k].get("r") if res[k].get("r") is not None else -2.0)


def compare(a, b, lag=0):
    p = paired(a, b, lag)
    if not p:
        return {"n": 0}
    xs, ys = [x for x, _ in p], [y for _, y in p]
    return {"n": len(p), "r": pearson(xs, ys), "median_diff": median([x - y for x, y in p]),
            "mean_a": sum(xs) / len(xs), "mean_b": sum(ys) / len(ys)}


def block_means(series, days=7):
    """Means over consecutive 7-day blocks that are complete. {block index: mean}."""
    blocks = {}
    for d, v in series.items():
        blocks.setdefault(dt.date.fromisoformat(d).toordinal() // days, []).append(v)
    return {k: sum(v) / len(v) for k, v in blocks.items() if len(v) == days}


def rainless_days(rain):
    """Rule 6. rain: {date: mm}. Returns the set of rainless dates."""
    out = set()
    for d in rain:
        window = [rain.get(shift(d, -k)) for k in range(RAINLESS_DAYS)]
        if all(x is not None and x < RAINLESS_MM for x in window):
            out.add(d)
    return out


def noise_stats(series, days):
    """On the given days: share of rises, lag-1 autocorrelation of daily changes,
    and implied white noise sqrt(-cov) (m3/s)."""
    ch = {d: series[d] - series[shift(d, -1)] for d in days if d in series and shift(d, -1) in series}
    if len(ch) < 10:
        return None
    rises = sum(1 for v in ch.values() if v > 0) / len(ch)
    pairs = [(ch[d], ch[shift(d, 1)]) for d in ch if shift(d, 1) in ch]
    r1 = pearson([a for a, _ in pairs], [b for _, b in pairs]) if len(pairs) >= 10 else None
    cov = None
    if len(pairs) >= 10:
        ma = sum(a for a, _ in pairs) / len(pairs)
        mb = sum(b for _, b in pairs) / len(pairs)
        cov = sum((a - ma) * (b - mb) for a, b in pairs) / len(pairs)
    sigma = math.sqrt(-cov) if cov is not None and cov < 0 else 0.0 if cov is not None else None
    return {"days": len(ch), "rises": rises, "r1": r1, "noise": sigma, "median": median([series[d] for d in ch])}


def shortfall_level_test(level, release, gauge, min_each=3):
    """Water level on days a river gauge reads more than SHORTFALL_M3S below the
    reported release, against other days of the same year with the same
    reported release. All inputs {date: value}. Nothing is fitted."""
    ds = [d for d in sorted(level) if d in release and d in gauge]
    out = {"n": len(ds), "s_rel": None, "s_gauge": None, "groups": 0, "short_days": 0, "groups_lower": 0,
           "diff_m": None, "step_m": None}
    if len(ds) < 3:
        return out
    out["s_rel"] = spearman([level[d] for d in ds], [release[d] for d in ds])
    out["s_gauge"] = spearman([level[d] for d in ds], [gauge[d] for d in ds])
    groups = {}
    for d in ds:
        short = gauge[d] < release[d] - SHORTFALL_M3S
        groups.setdefault((d[:4], round(release[d], 2)), ([], []))[0 if short else 1].append(level[d])
    diffs, n_short = [], 0
    for sh, ot in groups.values():
        if len(sh) >= min_each and len(ot) >= min_each:
            diffs.append(median(sh) - median(ot))
            n_short += len(sh)
    level_at = {k: median(sh + ot) for k, (sh, ot) in groups.items() if len(sh) + len(ot) >= 5}
    steps = [level_at[(y, round(r + 0.5, 2))] - level_at[(y, r)] for (y, r) in level_at if (y, round(r + 0.5, 2)) in level_at]
    out.update({"groups": len(diffs), "short_days": n_short, "groups_lower": sum(1 for x in diffs if x < 0),
                "diff_m": median(diffs), "step_m": median(steps)})
    return out


def storage_change(sar):
    """{date: dS/dt in m3/s} from the previous day's useful volume, as process.py."""
    out = {}
    for d, r in sar.items():
        p = sar.get(shift(d, -1))
        if p and r["hm3"] is not None and p["hm3"] is not None:
            out[d] = (r["hm3"] - p["hm3"]) * HM3_PER_DAY_TO_M3S
    return out


# ------------------------------------------------------------------ loading ----
def load_sar(key):
    path = os.path.join(c.PROCESSED, "sar_%s.csv" % key)
    out = {}
    if not os.path.exists(path):
        return out
    for r in c.read_csv(path):
        out[r["date"]] = {"level": c.fnum(r["level_m"]), "hm3": c.fnum(r["useful_volume_hm3"]),
                          "inflow": c.fnum(r["inflow_m3s"]), "release": c.fnum(r["release_m3s"])}
    return out


def load_ana(code):
    path = os.path.join(c.PROCESSED, "ana_discharge_%s.csv" % code)
    if not os.path.exists(path):
        return {}
    return {r["date"]: c.fnum(r["discharge_m3s"]) for r in c.read_csv(path) if c.fnum(r["discharge_m3s"]) is not None}


def load_rain(cat):
    path = os.path.join(c.PROCESSED, "forcing_%s.csv" % cat)
    if not os.path.exists(path):
        return {}
    return {r["date"]: c.fnum(r["rain_mm"]) for r in c.read_csv(path) if c.fnum(r["rain_mm"]) is not None}


def col(sar, field):
    return {d: r[field] for d, r in sar.items() if r[field] is not None}


# ------------------------------------------------------------------- report ----
def f2(x, fmt="%.2f"):
    return "" if x is None else fmt % x


def lag_cells(a, b):
    """Correlation at SAR shifted -1, 0, +1 day, and the best lag."""
    res = {k: compare(a, b, k) for k in LAGS}
    return res, [f2(res[k].get("r")) for k in LAGS], best_lag(res)


def main():
    if not os.path.exists(STATIONS):
        print("no SIBH flow station file; run fetch_sibh_flow.py first. Skipped.")
        return
    meta = json.load(open(STATIONS, encoding="utf-8"))
    st = {s["id"]: s for s in meta["stations"]}
    hourly = {sid: load_hourly(sid) for sid in st}
    series, stats = {}, {}
    for sid, s in st.items():
        days, sstats, _ = daily(hourly[sid])
        checked, matched = curve_check(hourly[sid], load_curves(sid))
        series[sid] = {f: {d: v for d, (v, _) in days[f].items()} for f in FIELDS}
        series[sid]["datum"] = days["datum"]
        stats[sid] = sstats
        spans = datum_spans(days["datum"])
        last = by_datum(series[sid]["level"], days["datum"], spans[-1][0]) if spans else {}
        s.update(load_prefix(sid))
        s.update({"hours_on_record": len(hourly[sid]), "level_kind": level_kind(days["datum"]),
                  "level_median_m": round(median(list(last.values())), 3) if last else None,
                  "level_other_datum_hours": sstats["level"]["other_datum_hours"],
                  "level_dropped_datum_days": sstats["level"]["dropped_datum_days"],
                  "value_in_metres": sid in VALUE_IN_METRES,
                  "curve_hours_checked": checked, "curve_hours_matched": matched,
                  "curves_published": len(load_curves(sid))})
        for f in FIELDS:
            ds = sorted(series[sid][f])
            s.update({"%s_days" % f: len(ds), "%s_first_day" % f: ds[0] if ds else None,
                      "%s_last_day" % f: ds[-1] if ds else None, "%s_hours" % f: sstats[f]["hours"],
                      "%s_invalid_hours" % f: sstats[f]["invalid_hours"], "%s_days_short" % f: sstats[f]["days_short"],
                      "%s_flat_days" % f: sstats[f]["flat_days"]})
        rows = station_rows(days)
        path = os.path.join(c.PROCESSED, "sibh_flow_%s.csv" % sid)
        if rows:
            c.write_csv(path, ["date", "level_m", "level_datum", "discharge_m3s", "level_hours", "discharge_hours"], rows)
        elif os.path.exists(path):
            os.remove(path)
        s["csv"] = os.path.basename(path) if rows else None
    meta["rules"] = {"day": "local calendar day, 00:00-24:00 UTC-3", "min_hours": MIN_HOURS,
                     "level_band_m": LEVEL_BAND_M, "elevation_above_m": ELEVATION_ABOVE_M,
                     "min_datum_days": MIN_DATUM_DAYS, "value_in_metres": sorted(VALUE_IN_METRES), "max_q_m3s": MAX_Q_M3S, "curve_tol": CURVE_TOL,
                     "rainless": "catchment rain < %.1f mm on the day and the %d days before" % (RAINLESS_MM, RAINLESS_DAYS - 1)}
    with open(STATIONS, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=1)

    sar = {k: load_sar(k) for k in ("cachoeira", "atibainha", "jaguari_jacarei")}
    L = report(meta, st, hourly, series, sar)
    with open(REPORT, "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")
    for sid, s in st.items():
        print("%-6s %-10s %-9s level days %5d  discharge days %5d  %s" % (
            sid, s.get("prefix", ""), s.get("level_kind") or "-", s["level_days"], s["discharge_days"], s.get("name", "")))
    print("report:", os.path.relpath(REPORT, c.ROOT) if os.path.splitdrive(REPORT)[0] == os.path.splitdrive(c.ROOT)[0] else REPORT)


def label(s):
    return "%s %s (%s)" % (s["id"], s.get("prefix", ""), s.get("name", ""))


def report(meta, st, hourly, series, sar):
    now = dt.datetime.utcnow().strftime("%Y-%m-%d %H:%M")
    q = {sid: series[sid]["discharge"] for sid in st}
    lv = {sid: series[sid]["level"] for sid in st}
    datum = {sid: series[sid]["datum"] for sid in st}
    L = ["# River, dam and transfer stations from SIBH", "",
         "Generated %s UTC by `pipeline/sibh_flow.py` from hourly means downloaded by `pipeline/fetch_sibh_flow.py` "
         "(SP Águas SIBH public API, retrieved %s). Observed records only: no model is run and no model output is used. "
         "SIBH's telemetric records are unconsolidated." % (now, meta["retrieved"]), "",
         "A day is the local calendar day (UTC-3) and is kept for a variable if at least %d of its 24 hourly means are "
         "valid; the daily value is their mean. Levels more than %.0f m from the station's median in the same datum, and "
         "discharges below 0 or above %.0f m3/s, are rejected; nothing else is filtered or filled. Rules: docstring of "
         "`pipeline/sibh_flow.py`."
         % (MIN_HOURS, LEVEL_BAND_M, MAX_Q_M3S), ""]

    # 1. what each station holds
    L += ["## 1. What each station holds", "",
          "`value` is a water level, in cm (in metres at the six Sabesp codes with 8-digit prefixes: %s), shown here in "
          "m. A level above %.0f m is a water-surface elevation; below, it is stage above the gauge zero. `read_value` is "
          "discharge in m3/s, which SIBH gives from the level with a rating curve. Where SIBH publishes a curve in force, "
          "the curve is applied to every hourly level and compared with SIBH's discharge (tolerance %.0f%% or 0.005 m3/s). "
          "Median level is over kept days in the latest datum." % (
              ", ".join(sorted(VALUE_IN_METRES, key=int)), ELEVATION_ABOVE_M, CURVE_TOL * 100), "",
          "| SIBH id | Code | Operator | Name | Group | Feed | Level | Median level (m) | Days with level | Days with discharge "
          "| Rating curves published | Hours the curve reproduces | Flat days (level / discharge) |",
          "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
    for sid, s in st.items():
        var = s.get("level_kind") or "none"
        cur = ("%d of %d" % (s["curve_hours_matched"], s["curve_hours_checked"])) if s["curve_hours_checked"] else "not checkable"
        L.append("| %s | %s | %s | %s | %s | %s | %s | %s | %d | %d | %d | %s | %d / %d |" % (
            sid, s.get("prefix", ""), s.get("owner", ""), s.get("name", ""), s["group"], s.get("data_source") or "",
            var,
            f2(s.get("level_median_m")), s["level_days"], s["discharge_days"], s["curves_published"], cur,
            s["level_flat_days"], s["discharge_flat_days"]))
    L += ["", "Feed is the station record's `data_source` in SIBH (WS-ANA: taken from ANA's web service; blank: not stated)."]
    L += ["", "Hours rejected by the validity rule (level / discharge): " + "; ".join(
        "%s: %d / %d" % (sid, s["level_invalid_hours"], s["discharge_invalid_hours"]) for sid, s in st.items()
        if s["level_invalid_hours"] or s["discharge_invalid_hours"]) + ("." if any(
            s["level_invalid_hours"] or s["discharge_invalid_hours"] for s in st.values()) else "none."), "",
          "Level hours dropped because most of that day was in the other datum: " + ("; ".join(
              "%s: %d" % (sid, s["level_other_datum_hours"]) for sid, s in st.items() if s["level_other_datum_hours"])
              or "none") + ". Days dropped because their datum has fewer than %d days at the station: " % MIN_DATUM_DAYS + (
              "; ".join("%s: %d" % (sid, s["level_dropped_datum_days"]) for sid, s in st.items()
                        if s["level_dropped_datum_days"]) or "none") + ".", ""]

    # 1b. rating in use by year
    rated = {sid: rating_by_year(hourly[sid]) for sid in st if st[sid]["discharge_days"]}
    rated = {sid: r for sid, r in rated.items() if r[0]}
    if rated:
        yrs = sorted({y for _, by in rated.values() for y in by})
        L += ["### Rating in use, by year", "",
              "Discharge SIBH gives at two fixed stages of each station, its median and 90th-percentile stage over the "
              "whole record (median over the hours within 1 cm of that stage; blank if fewer than 5 hours). A change "
              "between years is a change of rating curve, not of flow. Nothing is fitted.", "",
              "| Station | Stage (m) | " + " | ".join(str(y) for y in yrs) + " |", "| --- | --- |" + " --- |" * len(yrs)]
        for sid, (stages, by) in rated.items():
            for i, s in enumerate(stages):
                L.append("| %s | %.2f | %s |" % (label(st[sid]), s, " | ".join(
                    f2(by.get(y, (None, None))[i]) for y in yrs)))
        L.append("")

    # 2. coverage by year
    all_days = [d for sid in st for f in FIELDS for d in series[sid][f]]
    if all_days:
        years = list(range(int(min(all_days)[:4]), int(max(all_days)[:4]) + 1))
        for f, title in (("discharge", "discharge (m3/s)"), ("level", "level")):
            L += ["## 2%s. Days kept per year: %s" % ("a" if f == "discharge" else "b", title), "",
                  "| Station | " + " | ".join(str(y) for y in years) + " |", "| --- |" + " --- |" * len(years)]
            for sid, s in st.items():
                if not series[sid][f]:
                    continue
                L.append("| %s | %s |" % (label(s), " | ".join(
                    str(sum(1 for d in series[sid][f] if d.startswith(str(y)))) for y in years)))
            none = [label(s) for sid, s in st.items() if not series[sid][f]]
            L += ["", "No %s on any kept day: %s." % (f, "; ".join(none) if none else "none"), ""]
    else:
        L += ["## 2. Coverage", "", "No station has a kept day.", ""]

    # 3. upstream gauges vs SAR inflow
    inflow = {k: col(sar[k], "inflow") for k in sar}
    L += ["## 3. Gauges above the reservoirs against SAR inflow", "",
          "SAR's inflow is the operator's figure, computed from the reservoir balance. The gauges measure the river above "
          "the lake and drain only part of each catchment (SIBH gives no drainage area for either), so their "
          "flow should be smaller than the inflow and move with it. Correlation is shown with SAR's day shifted by one "
          "day either way.", "",
          "| Gauge | Reservoir | Days compared | Gauge mean (m3/s) | SAR inflow mean (m3/s) | Ratio | r, SAR day D-1 | "
          "r, same day | r, SAR day D+1 | r, 7-day means |", "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
    up = [(sid, INFLOW_OF[sid]) for sid in st if sid in INFLOW_OF]
    for sid, key in up:
        a, b = q[sid], inflow[key]
        res, cells, _ = lag_cells(a, b)
        r0 = res[0]
        if not r0["n"]:
            L.append("| %s | %s | 0 | | | | | | | |" % (label(st[sid]), key))
            continue
        ba, bb = block_means(a), block_means(b)
        common = sorted(set(ba) & set(bb))
        r7 = pearson([ba[k] for k in common], [bb[k] for k in common])
        L.append("| %s | %s | %d | %.2f | %.2f | %.2f | %s | %s | %s | %s |" % (
            label(st[sid]), key, r0["n"], r0["mean_a"], r0["mean_b"], r0["mean_a"] / r0["mean_b"] if r0["mean_b"] else float("nan"),
            cells[0], cells[1], cells[2], f2(r7)))
    L += ["", "Ratio of gauge to SAR inflow by year (sums over days both have):", "",
          "| Gauge | Reservoir | " + " | ".join("%d" % y for y in range(2015, dt.date.today().year + 1)) + " |",
          "| --- | --- |" + " --- |" * (dt.date.today().year + 1 - 2015)]
    for sid, key in up:
        cells = []
        for y in range(2015, dt.date.today().year + 1):
            p = paired(q[sid], inflow[key], 0, y)
            cells.append("%.2f (%d)" % (sum(x for x, _ in p) / sum(z for _, z in p), len(p)) if len(p) >= 30 and sum(z for _, z in p) > 0 else "")
        L.append("| %s | %s | %s |" % (label(st[sid]), key, " | ".join(cells)))

    L += ["", "### Noise on rainless days", "",
          "On days with less than %.0f mm of catchment rain on the day and the %d days before, flow should only recede. "
          "Rises on such days, and successive daily changes that cancel (negative lag-1 correlation), indicate measurement "
          "noise; the implied noise is the square root of minus the lag-1 covariance of daily changes. Same days for "
          "both records." % (RAINLESS_MM, RAINLESS_DAYS - 1), "",
          "| Record | Rainless days compared | Median flow (m3/s) | Days on which flow rises | Lag-1 correlation of changes | Implied noise (m3/s) |",
          "| --- | --- | --- | --- | --- | --- |"]
    for sid, key in up:
        rl = rainless_days(load_rain("%s_dam" % key))
        both = {d for d in rl if d in q[sid] and shift(d, -1) in q[sid] and d in inflow[key] and shift(d, -1) in inflow[key]}
        for name, ser in ((label(st[sid]), q[sid]), ("SAR inflow, %s (same days)" % key, inflow[key])):
            ns = noise_stats(ser, both)
            if ns is None:
                L.append("| %s | %d | too few | | | |" % (name, len(both)))
                continue
            L.append("| %s | %d | %.2f | %.0f%% | %s | %.2f |" % (name, ns["days"], ns["median"], ns["rises"] * 100,
                                                               f2(ns["r1"]), ns["noise"]))

    # 4. below Cachoeira dam: release, ANA gauge, SIBH gauges
    rel = {k: col(sar[k], "release") for k in sar}
    ana = {code: load_ana(code) for code in ("62665000", "62662000")}
    below = [sid for sid, s in st.items() if s["group"] == "below_dam"]
    short_years = {}
    for d, v in ana["62665000"].items():
        if d in rel["cachoeira"] and v < rel["cachoeira"][d] - SHORTFALL_M3S:
            short_years[d[:4]] = short_years.get(d[:4], 0) + 1
    many = sorted(y for y, n in short_years.items() if n >= 50)
    L += ["", "## 4. Below Cachoeira dam: the reported release against measured river flow", "",
          "ANA gauge 62665000 (Piracaia, 431 km2) reads more than %.1f m3/s below Cachoeira's reported release on 50 "
          "days or more in %s (`docs/data_quality_report.md`). Two SIBH stations on the same river give two more "
          "measurements: 3E-116 about 1 km below the dam, and 3E-145 in Piracaia beside ANA's gauge." % (
              SHORTFALL_M3S, ", ".join(many) if many else "no year"), "",
          "| Pair | Days compared | Mean of first (m3/s) | Mean of second (m3/s) | Median first minus second | r, same day | r, second shifted D+1 |",
          "| --- | --- | --- | --- | --- | --- | --- |"]
    pairs4 = [(label(st[sid]), q[sid], "SAR release, Cachoeira", rel["cachoeira"]) for sid in below]
    pairs4 += [(label(st[sid]), q[sid], "ANA 62665000 Piracaia", ana["62665000"]) for sid in below]
    pairs4 += [("ANA 62665000 Piracaia", ana["62665000"], "SAR release, Cachoeira", rel["cachoeira"])]
    if len(below) == 2:
        pairs4.append((label(st[below[0]]), q[below[0]], label(st[below[1]]), q[below[1]]))
    for na, a, nb, b in pairs4:
        r0, r1 = compare(a, b, 0), compare(a, b, 1)
        if r0["n"] < 30:
            L.append("| %s vs %s | %d | too few days | | | | |" % (na, nb, r0["n"]))
            continue
        L.append("| %s vs %s | %d | %.2f | %.2f | %.2f | %s | %s |" % (
            na, nb, r0["n"], r0["mean_a"], r0["mean_b"], r0["median_diff"], f2(r0["r"]), f2(r1.get("r"))))

    L += ["", "### Days on which a gauge reads more than %.1f m3/s below the release" % SHORTFALL_M3S, "",
          "Same-day comparison. Each cell: shortfall days / days compared.", "",
          "| Year | ANA 62665000 | " + " | ".join(label(st[sid]) for sid in below) + " | ANA and SIBH 3E-145 both short, of days all three exist |",
          "| --- | --- |" + " --- |" * len(below) + " --- |"]
    gauges4 = [("ana", ana["62665000"])] + [(sid, q[sid]) for sid in below]
    yrs = sorted({d[:4] for _, g in gauges4 for d in g if d in rel["cachoeira"] and d >= "2014"})
    sid145 = next((sid for sid in below if st[sid].get("prefix") == "3E-145"), None)
    for y in yrs:
        cells = []
        for _, g in gauges4:
            ds = [d for d in g if d.startswith(y) and d in rel["cachoeira"]]
            short = sum(1 for d in ds if g[d] < rel["cachoeira"][d] - SHORTFALL_M3S)
            cells.append("%d / %d" % (short, len(ds)) if ds else "")
        both = ""
        if sid145:
            ds = [d for d in ana["62665000"] if d.startswith(y) and d in rel["cachoeira"] and d in q[sid145]]
            sa = [d for d in ds if ana["62665000"][d] < rel["cachoeira"][d] - SHORTFALL_M3S]
            sb = [d for d in sa if q[sid145][d] < rel["cachoeira"][d] - SHORTFALL_M3S]
            both = "%d of %d ANA-short days (%d days)" % (len(sb), len(sa), len(ds)) if ds else ""
        L.append("| %s | %s | %s |" % (y, " | ".join(cells), both))

    # water level below the dam on shortfall days
    L += ["", "### Water level below the dam on shortfall days", "",
          "A water level needs no rating curve. Stations 22 and 20 read the channel just below each dam (from 2024); "
          "3E-116 reads the river about 1 km below Cachoeira dam (from 2010); 3E-145 reads it in Piracaia beside ANA's "
          "gauge. Days are grouped by year and by reported release. Within a group, a lower level on the days the river "
          "gauge reads short means less water was in the river than on other days with the same reported release; an "
          "unchanged level means the river gauge alone is low. The scale column gives, for comparison, the median "
          "difference in level between reported releases 0.5 m3/s apart in the same year. No rating is fitted.", "",
          "| Level station | Shortfall judged by | Days with level, release and gauge | Spearman: level vs release | "
          "Spearman: level vs gauge | Groups with at least 3 short and 3 other days | Short days in those groups "
          "| Median level difference, short minus other (cm) | Groups where short days are lower | Scale: level per 0.5 m3/s of release (cm) |",
          "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
    level_tests = [("cachoeira", "22", "62665000"), ("cachoeira", "30862", "62665000"), ("cachoeira", "832", "62665000"),
                   ("atibainha", "20", "62662000")]
    for key, tid, gcode in level_tests:
        if tid not in st or not lv[tid]:
            continue
        gauge_sets = [("ANA %s" % gcode, ana[gcode])]
        if key == "cachoeira" and sid145 and sid145 != tid:
            gauge_sets.append((label(st[sid145]), q[sid145]))
        for dat in ("gauge", "elevation"):
            seg = by_datum(lv[tid], datum[tid], dat)
            if not seg:
                continue
            name = "%s, %s" % (label(st[tid]), "stage" if dat == "gauge" else "elevation")
            for gname, g in gauge_sets:
                t = shortfall_level_test(seg, rel[key], g)
                if t["n"] < 30:
                    L.append("| %s | %s | %d | too few days | | | | | | |" % (name, gname, t["n"]))
                    continue
                L.append("| %s | %s | %d | %s | %s | %d | %d | %s | %d of %d | %s |" % (
                    name, gname, t["n"], f2(t["s_rel"]), f2(t["s_gauge"]), t["groups"], t["short_days"],
                    f2(None if t["diff_m"] is None else t["diff_m"] * 100, "%.1f"), t["groups_lower"], t["groups"],
                    f2(None if t["step_m"] is None else t["step_m"] * 100, "%.1f")))
    # the longest level record, year by year
    if "30862" in st and lv["30862"]:
        L += ["", "By year, for 3E-116 just below the dam (same test; blank where no group has 3 short and 3 other days):", "",
              "| Year | Shortfall judged by | Groups | Short days | Median level difference, short minus other (cm) | Scale (cm per 0.5 m3/s) |",
              "| --- | --- | --- | --- | --- | --- |"]
        judges = [("ANA 62665000", ana["62665000"])] + ([(label(st[sid145]), q[sid145])] if sid145 else [])
        for y in sorted({d[:4] for d in lv["30862"]}):
            for gname, g in judges:
                sub = {d: v for d, v in by_datum(lv["30862"], datum["30862"], "gauge").items() if d.startswith(y)}
                t = shortfall_level_test(sub, rel["cachoeira"], g)
                if t["groups"]:
                    L.append("| %s | %s | %d | %d | %s | %s |" % (
                        y, gname, t["groups"], t["short_days"], f2(t["diff_m"] * 100, "%.1f"),
                        f2(None if t["step_m"] is None else t["step_m"] * 100, "%.1f")))

    # 5. reservoir levels
    L += ["", "## 5. Reservoir levels against SAR", "",
          "SAR gives one level per reservoir per day. Compared here with the station's mean level over the hour from "
          "07:00 to 08:00 local time (10:00 UTC) on the same day, and with its daily mean.", "",
          "| Station | Reservoir | Days compared | Median station minus SAR, 07:00 (m) | Within 5 cm, 07:00 | "
          "Median station minus SAR, daily mean (m) | Within 5 cm, daily mean |", "| --- | --- | --- | --- | --- | --- | --- |"]
    for sid, key in RESERVOIR_OF.items():
        if sid not in st:
            continue
        sl = col(sar[key], "level")
        h7 = {}
        for t, (h, _, _) in hourly[sid].items():
            if t.hour == 10 and h is not None and datum_of(h) == "elevation":
                h7[t.date().isoformat()] = h
        el = by_datum(lv[sid], datum[sid], "elevation")
        a = [h7[d] - sl[d] for d in h7 if d in sl]
        b = [el[d] - sl[d] for d in el if d in sl]
        if not a and not b:
            L.append("| %s | %s | 0 | | | | |" % (label(st[sid]), key))
            continue
        L.append("| %s | %s | %d | %s | %s | %s | %s |" % (
            label(st[sid]), key, max(len(a), len(b)), f2(median(a), "%.3f"),
            "%.0f%%" % (100.0 * sum(1 for x in a if abs(x) <= 0.05) / len(a)) if a else "",
            f2(median(b), "%.3f"), "%.0f%%" % (100.0 * sum(1 for x in b if abs(x) <= 0.05) / len(b)) if b else ""))

    # 6. tunnels against the reservoir balance
    dS = {k: storage_change(sar[k]) for k in sar}
    resid = {}
    for k in ("cachoeira", "atibainha"):
        resid[k] = {d: inflow[k][d] - rel[k][d] - dS[k][d] for d in dS[k] if d in inflow[k] and d in rel[k]}
    t6 = [sid for sid, s in st.items() if s["group"] == "transfer" and "Tunnel 6" in s["site"] and q[sid]]
    t5 = [sid for sid, s in st.items() if s["group"] == "transfer" and "Tunnel 5 outlet" in s["site"] and q[sid]]
    ps = [sid for sid, s in st.items() if s["group"] == "transfer" and "Paraíba" in s["site"] and q[sid]]
    L += ["", "## 6. Tunnel flows against the reservoir balance", "",
          "For each reservoir SAR's records imply a net outflow that is neither the reported release nor storage change: "
          "inflow minus release minus storage change (from the previous day's volume, as in `process.py`). For Cachoeira "
          "that should be Tunnel 6 to Atibainha, less Tunnel 7 water received from Jaguari-Jacareí; for Atibainha, Tunnel 5 "
          "to Paiva Castro less Tunnel 6 received (and any Paraíba do Sul water, if SAR does not count it as inflow). "
          "Evaporation and rain on the lake are ignored. An accounting check, not a model.", "",
          "| Balance residual | Measured | SAR shift used | Days compared | Residual mean (m3/s) | Measured mean (m3/s) "
          "| Median residual minus measured | Days within 1 m3/s | r, SAR day D-1 | r, same day | r, SAR day D+1 |",
          "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
    checks = [("Cachoeira", resid["cachoeira"], label(st[sid]), q[sid]) for sid in t6]
    checks += [("Atibainha", resid["atibainha"], label(st[sid]), q[sid]) for sid in t5]
    for s5 in t5:
        for s6 in t6:
            net = {d: q[s5][d] - q[s6][d] for d in q[s5] if d in q[s6]}
            checks.append(("Atibainha", resid["atibainha"], "%s minus %s" % (st[s5]["prefix"], st[s6]["prefix"]), net))
            for sp in ps:
                net2 = {d: v - q[sp][d] for d, v in net.items() if d in q[sp]}
                checks.append(("Atibainha", resid["atibainha"], "%s minus %s minus %s" % (
                    st[s5]["prefix"], st[s6]["prefix"], st[sp]["prefix"]), net2))
    if not checks:
        L.append("| no tunnel station has discharge | | | | | | | | |")
    for name, rsd, mname, m in checks:
        res = {k: compare(m, rsd, k) for k in LAGS}
        lag = best_lag(res)
        r0 = res[lag]
        if not r0["n"]:
            L.append("| %s | %s | | 0 | | | | | | | |" % (name, mname))
            continue
        within = sum(1 for a, b in paired(m, rsd, lag) if abs(a - b) <= 1.0) / r0["n"]
        L.append("| %s | %s | %+d day | %d | %.2f | %.2f | %.2f | %.0f%% | %s | %s | %s |" % (
            name, mname, lag, r0["n"], r0["mean_b"], r0["mean_a"], -r0["median_diff"], within * 100,
            f2(res[-1].get("r")), f2(res[0].get("r")), f2(res[1].get("r"))))
    L += ["", "Means, the median difference and the share within 1 m3/s are for the SAR shift with the highest "
          "correlation (a shift of -1 pairs the station's day D with SAR's day D-1)."]
    if t5 and t6:
        s5, s6 = t5[0], t6[0]  # the longer records come first in the station list
        net = {d: q[s5][d] - q[s6][d] for d in q[s5] if d in q[s6]}
        lag = best_lag({k: compare(net, resid["atibainha"], k) for k in LAGS})
        L += ["", "### What the measured tunnels add to SAR's balance, by year", "",
              "Atibainha: Tunnel 5 minus Tunnel 6 (%s minus %s), minus SAR's residual. If SAR's inflow is the natural "
              "inflow and nothing else enters, this is zero; a positive value is water entering Atibainha that SAR's "
              "inflow does not count. Cachoeira: Tunnel 6 minus SAR's residual, which is what Tunnel 7 must have "
              "delivered from Jaguari-Jacareí if SAR's inflow is natural (no Tunnel 7 flow is published). SAR shifted %+d "
              "day, the shift with the highest correlation above. Derived, not measured." % (
                  st[s5]["prefix"], st[s6]["prefix"], lag), "",
              "| Year | Atibainha days | Atibainha: median (m3/s) | Atibainha: mean (m3/s) | Cachoeira days | "
              "Cachoeira, implied Tunnel 7: median (m3/s) | Cachoeira, implied Tunnel 7: mean (m3/s) |",
              "| --- | --- | --- | --- | --- | --- | --- |"]
        gap, t7 = {}, {}
        for d, v in net.items():
            if shift(d, lag) in resid["atibainha"]:
                gap.setdefault(d[:4], []).append(v - resid["atibainha"][shift(d, lag)])
        for d, v in q[s6].items():
            if shift(d, lag) in resid["cachoeira"]:
                t7.setdefault(d[:4], []).append(v - resid["cachoeira"][shift(d, lag)])
        for y in sorted(set(gap) | set(t7)):
            a, b = gap.get(y, []), t7.get(y, [])
            L.append("| %s | %d | %s | %s | %d | %s | %s |" % (
                y, len(a), f2(median(a)), f2(sum(a) / len(a) if a else None),
                len(b), f2(median(b)), f2(sum(b) / len(b) if b else None)))

    # 7. duplicate codes
    L += ["", "## 7. Sites recorded under two codes", "",
          "| Site | First code | Second code | Variable | Days both have | Median first minus second | r |",
          "| --- | --- | --- | --- | --- | --- | --- |"]
    for a, b in DUPLICATES:
        if a not in st or b not in st:
            continue
        for f in FIELDS:
            sa, sb = series[a][f], series[b][f]
            if f == "level":
                sa = {d: v for d, v in sa.items() if datum[a].get(d) == datum[b].get(d)}
            res = compare(sa, sb)
            if not res["n"]:
                if series[a][f] or series[b][f]:
                    L.append("| %s | %s | %s | %s | 0 | | |" % (st[a]["site"], st[a]["prefix"], st[b]["prefix"], f))
                continue
            L.append("| %s | %s | %s | %s | %d | %s | %s |" % (st[a]["site"], st[a]["prefix"], st[b]["prefix"], f,
                                                          res["n"], f2(res["median_diff"], "%.3f"), f2(res["r"], "%.3f")))
    return L


if __name__ == "__main__":
    main()
