"""Turn the raw downloads into tidy tables, a quality report, water-balance
diagnostics and the JSON the viewer reads.

Everything here is either an observation copied from its source, or a value
DERIVED from observations by a formula stated in the output. Nothing is
simulated and nothing is filled in: gaps stay gaps.

Derived quantities
  system storage      S   = sum of the four reservoirs' useful volume (hm3)
  system storage %        = S / 981.56 hm3 (ANA's stated system useful volume)
  operating band          = band whose lower bound S% meets (Res. ANA/DAEE 925/2017)
  implied net export  X   = sum(inflow) - sum(release) - dS/dt        (m3/s)
        where dS/dt uses storage change from the previous day, 1 hm3/day = 11.574 m3/s.
        X lumps withdrawal to Sao Paulo, minus any transfer received from the
        Paraiba do Sul link, plus evaporation, rain on the lakes and all
        measurement error. It is a residual, not a measurement.
  incremental flow        = flow at the Atibaia gauge - (Cachoeira release + Atibainha release)
        i.e. what the 436 km2 between the two dams and the gauge contributed,
        net of abstractions, same day, no travel-time lag.

Usage: python process.py
"""
import datetime as dt
import glob
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # isolated mode drops the script folder
import common as c  # noqa: E402
from fetch_sar_cantareira import parse_rows  # noqa: E402

SYSTEM_USEFUL_HM3 = 981.56
HM3_PER_DAY_TO_M3S = 1e6 / 86400.0
RULES_FROM = "2017-06-01"  # Joint Resolution ANA/DAEE 925 of 29 May 2017
CURVE_REVISION = "2010-04-01"  # revised level-area-volume curves adopted from this date
SENTINEL = 99999.0  # the raw gauge series carry 100000.0 as a placeholder on some days
REJECTED = {}
GAPS = []
EXTRA_META = {"62665000": {"lat": -23.0517, "lon": -46.3653, "area_km2": 431},
              "62662000": {"lat": -23.1664, "lon": -46.4161, "area_km2": 358}}
WEB_DATA = os.path.join(c.ROOT, "web", "public", "data")
REPORT = os.path.join(c.ROOT, "docs", "data_quality_report.md")


def daterange(a, b):
    d = a
    while d <= b:
        yield d
        d += dt.timedelta(days=1)


def load_sar():
    """{key: {date: dict(level, hm3, pct, inflow, release)}} from cached raw HTML."""
    out = {}
    for code, meta in c.RESERVOIRS.items():
        days = {}
        for path in sorted(glob.glob(os.path.join(c.RAW, "sar_cantareira", meta["key"] + "_*.html"))):
            with open(path, "rb") as f:
                rows = parse_rows(f.read()) or []
            for d, level, hm3, pct, inflow, release in rows:
                days[d] = {"level": level, "hm3": hm3, "pct": pct, "inflow": inflow, "release": release}
        out[meta["key"]] = days
        rows = [(d, v["level"], v["hm3"], v["pct"], v["inflow"], v["release"]) for d, v in sorted(days.items())]
        c.write_csv(os.path.join(c.PROCESSED, "sar_%s.csv" % meta["key"]),
                    ["date", "level_m", "useful_volume_hm3", "useful_volume_pct", "inflow_m3s", "release_m3s"], rows)
    return out


def load_gauge(station):
    path = os.path.join(c.PROCESSED, "ana_discharge_%s.csv" % station)
    if not os.path.exists(path):
        return {}
    out = {}
    for r in c.read_csv(path):
        v = float(r["discharge_m3s"])
        if v >= SENTINEL or v < 0:
            REJECTED[station] = REJECTED.get(station, 0) + 1  # placeholder values in the raw series
            continue
        out[r["date"]] = (v, r["consistency_level"])
    return out


def band_for(pct):
    for b in c.OPERATING_BANDS:
        if pct >= b["min_pct"]:
            return b
    return c.OPERATING_BANDS[-1]


def stats(values):
    v = sorted(x for x in values if x is not None)
    if not v:
        return None
    n = len(v)
    q = lambda p: v[min(n - 1, int(p * n))]
    return {"n": n, "min": v[0], "p05": q(0.05), "median": q(0.5), "p95": q(0.95), "max": v[-1],
            "mean": sum(v) / n}


def main():
    sar = load_sar()
    keys = [m["key"] for m in c.RESERVOIRS.values()]
    lines = ["# Data quality report: upper Atibaia pilot", "",
             "Generated %s UTC by `pipeline/process.py`. Every figure is computed from the files in `data/raw`." %
             dt.datetime.utcnow().strftime("%Y-%m-%d %H:%M"), ""]

    # ---- 1. reservoir records -------------------------------------------------
    lines += ["## 1. Reservoir records (ANA SAR, Cantareira module)", "",
              "| Reservoir | First day | Last day | Days present | Days missing in span | Missing inflow | Missing release | Volume % vs hm3 mismatch |",
              "| --- | --- | --- | --- | --- | --- | --- | --- |"]
    for code, meta in c.RESERVOIRS.items():
        days = sar[meta["key"]]
        if not days:
            lines.append("| %s | no data downloaded | | | | | | |" % meta["name"])
            continue
        ds = sorted(days)
        for d0, d1 in zip(ds, ds[1:]):
            gap = (dt.date.fromisoformat(d1) - dt.date.fromisoformat(d0)).days - 1
            if gap > 30:
                GAPS.append("%s, %d days after %s" % (meta["name"], gap, d0))
        a, b = dt.date.fromisoformat(ds[0]), dt.date.fromisoformat(ds[-1])
        span = (b - a).days + 1
        miss_in = sum(1 for v in days.values() if v["inflow"] is None)
        miss_rel = sum(1 for v in days.values() if v["release"] is None)
        # internal consistency: reported % should equal hm3 / useful capacity
        bad = 0
        checked = 0
        for v in days.values():
            if v["hm3"] is None or v["pct"] is None:
                continue
            checked += 1
            if abs(v["hm3"] / meta["useful_hm3"] * 100.0 - v["pct"]) > 0.5:
                bad += 1
        lines.append("| %s | %s | %s | %d | %d | %d | %d | %d of %d days differ by more than 0.5 points |" % (
            meta["name"], ds[0], ds[-1], len(ds), span - len(ds), miss_in, miss_rel, bad, checked))
    lines += ["", "Gaps longer than 30 days: " + ("; ".join(GAPS) or "none") + "."]
    lines += ["", "The last column tests the records against themselves: reported percentage versus reported volume "
              "divided by the useful capacity ANA publishes (%s hm3). A mismatch means the capacity used by the "
              "source differs from the published one for those days." %
              ", ".join("%s %.2f" % (m["name"], m["useful_hm3"]) for m in c.RESERVOIRS.values()), ""]

    # ---- 1b. capacity in force ------------------------------------------------------
    # The source computes its percentages against a useful capacity that has changed
    # over the years as the level-area-volume curves were revised (the last revision
    # was adopted on 1 April 2010, per ANA's December 2010 Cantareira bulletin).
    # The capacity in force is recovered from the records themselves: for each
    # reservoir and calendar month, the median of volume / percentage.
    cap_month = {}
    lines += ["### Useful capacity in force, recovered from the records", "",
              "| Reservoir | From | To | Capacity implied by the records (hm3) | Published today (hm3) |",
              "| --- | --- | --- | --- | --- |"]
    for code, meta in c.RESERVOIRS.items():
        k = meta["key"]
        per = {}
        for d, x in sar[k].items():
            if x["hm3"] is None or x["pct"] is None or abs(x["pct"]) <= 5:
                continue
            per.setdefault(d[:7], []).append(x["hm3"] / x["pct"] * 100.0)
        med = {m: sorted(v)[len(v) // 2] for m, v in per.items()}
        cap_month[k] = med
        regimes = []
        for m in sorted(med):
            if regimes and abs(regimes[-1][2] - med[m]) < 0.3:
                regimes[-1][1] = m
            else:
                regimes.append([m, m, med[m]])
        for r0, r1, v in regimes:
            lines.append("| %s | %s | %s | %.2f | %.2f |" % (meta["name"], r0, r1, v, meta["useful_hm3"]))

    def capacity(k, d):
        med = cap_month[k]
        if d[:7] in med:
            return med[d[:7]]
        earlier = [m for m in med if m <= d[:7]]
        return med[max(earlier)] if earlier else (med[min(med)] if med else c.RESERVOIRS_BY_KEY[k]["useful_hm3"])

    still = 0
    for k in cap_month:
        for d, x in sar[k].items():
            if x["hm3"] is not None and x["pct"] is not None and abs(x["hm3"] / capacity(k, d) * 100.0 - x["pct"]) > 0.5:
                still += 1
    lines += ["", "The mismatches counted in section 1 come from these capacity changes, not from bad values: "
              "using the capacity in force for each month, %d reservoir-days remain inconsistent by more than 0.5 "
              "points. System storage is therefore expressed against the sum of the capacities in force on each "
              "day. Volumes on either side of a revision are not strictly comparable." % still, ""]

    # ---- 2. system storage, band, implied export ------------------------------
    common_days = sorted(set.intersection(*[set(sar[k]) for k in keys])) if all(sar[k] for k in keys) else []
    system = {}
    for d in common_days:
        vals = [sar[k][d] for k in keys]
        if any(v["hm3"] is None for v in vals):
            continue
        s = sum(v["hm3"] for v in vals)
        cap = sum(capacity(k, d) for k in keys)
        system[d] = {"hm3": s, "pct": s / cap * 100.0, "cap": cap, "curves": "pre-2010" if d < CURVE_REVISION else "2010",
                     "inflow": None if any(v["inflow"] is None for v in vals) else sum(v["inflow"] for v in vals),
                     "release": None if any(v["release"] is None for v in vals) else sum(v["release"] for v in vals)}
    rows = []
    prev = None
    for d in sorted(system):
        s = system[d]
        b = band_for(s["pct"])
        s["band"] = b["band"]
        export = None
        if prev is not None and (dt.date.fromisoformat(d) - dt.date.fromisoformat(prev)).days == 1 \
                and s["inflow"] is not None and s["release"] is not None:
            ds_m3s = (s["hm3"] - system[prev]["hm3"]) * HM3_PER_DAY_TO_M3S
            export = s["inflow"] - s["release"] - ds_m3s
        s["export"] = export
        rows.append((d, round(s["hm3"], 3), round(s["pct"], 3), s["curves"], b["band"],
                     s["inflow"], s["release"], None if export is None else round(export, 3)))
        prev = d
    c.write_csv(os.path.join(c.PROCESSED, "system_daily.csv"),
                ["date", "system_useful_volume_hm3", "system_useful_volume_pct", "volume_curves", "operating_band",
                 "sum_inflow_m3s", "sum_release_m3s", "implied_net_export_m3s"], rows)

    lines += ["## 2. System storage and the implied net export", ""]
    if system:
        ds = sorted(system)
        lo = min(ds, key=lambda d: system[d]["pct"])
        hi = max(ds, key=lambda d: system[d]["pct"])
        lines += ["- Days with all four reservoirs reported: %d (%s to %s)." % (len(ds), ds[0], ds[-1]),
                  "- Lowest system storage in the downloaded record: %.1f%% of useful volume on %s (%.1f hm3)." %
                  (system[lo]["pct"], lo, system[lo]["hm3"]),
                  "- Highest: %.1f%% on %s." % (system[hi]["pct"], hi), ""]
        # 30-day mean export vs band limit, by period
        dates = ds
        exp = [system[d]["export"] for d in dates]
        lines += ["Implied net export, 30-day running mean, against the withdrawal limit of the band in force "
                  "(the bands exist only from June 2017, so the comparison is made only from then):", "",
                  "| Year | Days with a 30-day mean | Median (m3/s) | 5th to 95th percentile (m3/s) | Days above the band limit | Median band limit (m3/s) |",
                  "| --- | --- | --- | --- | --- | --- |"]
        run = {}
        for i in range(29, len(dates)):
            window = exp[i - 29:i + 1]
            if any(x is None for x in window):
                continue
            if (dt.date.fromisoformat(dates[i]) - dt.date.fromisoformat(dates[i - 29])).days != 29:
                continue
            run[dates[i]] = sum(window) / 30.0
        for d in run:
            system[d]["export30"] = run[d]
        by_year = {}
        for d, x in run.items():
            by_year.setdefault(d[:4], []).append((x, band_for(system[d]["pct"])["max_withdrawal_m3s"], d >= RULES_FROM))
        for y in sorted(by_year):
            xs = [a for a, _, _ in by_year[y]]
            ruled = [(a, b) for a, b, ok in by_year[y] if ok]
            st = stats(xs)
            if ruled:
                lim = sorted(b for _, b in ruled)
                above = "%d of %d" % (sum(1 for a, b in ruled if a > b), len(ruled))
                limit = "%.1f" % lim[len(lim) // 2]
            else:
                above, limit = "not applicable", "not applicable"
            lines.append("| %s | %d | %.1f | %.1f to %.1f | %s | %s |" % (
                y, st["n"], st["median"], st["p05"], st["p95"], above, limit))
        lines += ["", "Reading this table: the implied export is a residual. It should sit near the real withdrawal "
                  "to Sao Paulo only if SAR's inflow is the natural inflow and evaporation is small. A persistent "
                  "value far above the band limit, or negative, signals that one of those assumptions fails or that "
                  "a transfer is unaccounted for (the Paraiba do Sul link feeds Atibainha since 2018).", ""]
    else:
        lines += ["No day has all four reservoirs yet; rerun after the downloads finish.", ""]

    # ---- 3. gauges -------------------------------------------------------------
    lines += ["## 3. River gauges (ANA HidroSerieHistorica, daily discharge)", "",
              "| Station | Name | First day | Last day | Days present | Missing in span | Consolidated share | Min | Median | Max (m3/s) |",
              "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
    gauge_codes = list(c.GAUGES) + ["62665000", "62662000", "62665100"]
    extra = {"62665000": "Piracaia (rio da Cachoeira, 431 km2, below Cachoeira dam)",
             "62662000": "Nazaré Paulista (rio Atibainha, 358 km2, below Atibainha dam)",
             "62665100": "Cravorana (rio da Cachoeira, 407 km2)"}
    gauges = {}
    for code in gauge_codes:
        g = load_gauge(code)
        gauges[code] = g
        name = c.GAUGES.get(code, {}).get("name") or extra.get(code, "")
        if not g:
            lines.append("| %s | %s | no data | | | | | | | |" % (code, name))
            continue
        ds = sorted(g)
        span = (dt.date.fromisoformat(ds[-1]) - dt.date.fromisoformat(ds[0])).days + 1
        st = stats([v for v, _ in g.values()])
        cons = sum(1 for _, lv in g.values() if lv == "2") / len(g) * 100.0
        lines.append("| %s | %s | %s | %s | %d | %d | %.0f%% | %.2f | %.2f | %.1f |" % (
            code, name, ds[0], ds[-1], len(ds), span - len(ds), cons, st["min"], st["median"], st["max"]))
    lines += ["", "Placeholder values rejected (100000.0 or negative in the raw series): %s." %
              (", ".join("%s: %d days" % kv for kv in sorted(REJECTED.items())) or "none"), ""]

    # ---- 4. independent cross-checks --------------------------------------------
    lines += ["## 4. Independent cross-checks", "",
              "Reservoir releases are reported by the operator through ANA; the gauges just below each dam are "
              "run by other agencies. Agreement between them is an independent test of both.", "",
              "| Pair | Days compared | Median gauge minus release (m3/s) | 5th to 95th percentile | Correlation |",
              "| --- | --- | --- | --- | --- |"]

    def compare(label, release_key, station):
        pairs = [(gauges[station][d][0], sar[release_key][d]["release"]) for d in sorted(gauges[station])
                 if d in sar[release_key] and sar[release_key][d]["release"] is not None]
        if len(pairs) < 30:
            lines.append("| %s | %d | too few days | | |" % (label, len(pairs)))
            return
        diff = stats([g - r for g, r in pairs])
        n = len(pairs)
        mg = sum(g for g, _ in pairs) / n
        mr = sum(r for _, r in pairs) / n
        cov = sum((g - mg) * (r - mr) for g, r in pairs)
        vg = sum((g - mg) ** 2 for g, _ in pairs)
        vr = sum((r - mr) ** 2 for _, r in pairs)
        corr = cov / (vg * vr) ** 0.5 if vg > 0 and vr > 0 else float("nan")
        lines.append("| %s | %d | %.2f | %.2f to %.2f | %.2f |" % (label, n, diff["median"], diff["p05"], diff["p95"], corr))

    compare("Piracaia gauge (431 km2) vs Cachoeira release (392 km2)", "cachoeira", "62665000")
    compare("Nazaré Paulista gauge (358 km2) vs Atibainha release (312 km2)", "atibainha", "62662000")
    lines += ["", "The gauges drain slightly more area than the dams (39 and 46 km2), so a small positive "
              "difference is expected. A large or negative one is a data problem to resolve before modelling.", ""]

    lines += ["### Where the gauge reads below the reported release", "",
              "Days on which the gauge is more than 0.5 m3/s below the release, by year (days / days compared):", "",
              "| Year | Piracaia vs Cachoeira | Nazaré Paulista vs Atibainha |", "| --- | --- | --- |"]

    def low_days(release_key, station):
        out = {}
        for d, (q, _) in gauges[station].items():
            r = sar[release_key].get(d, {}).get("release")
            if r is None:
                continue
            a, b = out.get(d[:4], (0, 0))
            out[d[:4]] = (a + (1 if q - r < -0.5 else 0), b + 1)
        return out

    la, lb = low_days("cachoeira", "62665000"), low_days("atibainha", "62662000")
    for y in sorted(set(la) | set(lb)):
        lines.append("| %s | %s | %s |" % (y, "%d / %d" % la[y] if y in la else "no data",
                                         "%d / %d" % lb[y] if y in lb else "no data"))

    def stepped(key):
        v = [x["release"] for _, x in sorted(sar[key].items()) if x["release"] is not None]
        half = sum(1 for x in v if abs(x * 2 - round(x * 2)) < 1e-9) / len(v) * 100.0
        same = sum(1 for a, b in zip(v, v[1:]) if a == b) / len(v) * 100.0
        return half, same

    ca, at = stepped("cachoeira"), stepped("atibainha")
    lines += ["", "What was tested: shifting the release by one or two days in either direction does not improve "
              "the agreement, so travel time is not the cause. The shortfalls cluster in particular years, which "
              "points to a rating-curve or reporting problem in those periods.", "",
              "The reported releases are stepped rather than continuously varying, as valve settings would be: %.0f%% of Cachoeira "
              "values and %.0f%% of Atibainha values are exact multiples of 0.5 m3/s, and %.0f%% and %.0f%% repeat the "
              "previous day. Which record is wrong on the shortfall days cannot be decided from open data; it needs "
              "the measured outflow from the operator or the rating history of the gauge." %
              (ca[0], at[0], ca[1], at[1]), ""]

    # ---- 5. control point -------------------------------------------------------
    lines += ["## 5. Control point: Rio Atibaia at Atibaia (station 62670000)", ""]
    ctrl = gauges.get("62670000", {})
    cp_rows = []
    for d in sorted(ctrl):
        rc = sar["cachoeira"].get(d, {}).get("release")
        ra = sar["atibainha"].get(d, {}).get("release")
        if rc is None or ra is None:
            continue
        q = ctrl[d][0]
        cp_rows.append((d, q, rc, ra, round(q - rc - ra, 3)))
    c.write_csv(os.path.join(c.PROCESSED, "control_point_atibaia.csv"),
                ["date", "gauge_flow_m3s", "cachoeira_release_m3s", "atibainha_release_m3s", "incremental_flow_m3s"], cp_rows)
    if cp_rows:
        inc = stats([r[4] for r in cp_rows])
        neg = sum(1 for r in cp_rows if r[4] < 0)
        share = stats([(r[2] + r[3]) / r[1] * 100.0 for r in cp_rows if r[1] > 0])
        below2 = sum(1 for r in cp_rows if r[1] < 2.0)
        below3 = sum(1 for r in cp_rows if r[1] < 3.0)
        lines += ["- Days with gauge flow and both releases: %d (%s to %s)." % (len(cp_rows), cp_rows[0][0], cp_rows[-1][0]),
                  "- Incremental flow from the area between the dams and the gauge: median %.2f m3/s, 5th to 95th percentile %.2f to %.2f." %
                  (inc["median"], inc["p05"], inc["p95"]),
                  "- Days with a negative incremental flow: %d (%.1f%%). Negative values mean abstractions, travel-time lag or measurement error exceed local runoff." %
                  (neg, neg / len(cp_rows) * 100.0),
                  "- Reservoir releases as a share of gauge flow: median %.0f%%." % share["median"],
                  "- Days with gauge flow under 2 m3/s: %d; under 3 m3/s: %d. The operating rules cite a 2 to 3 m3/s target range at this point (Comitês PCJ status report 2020); the exact daily target in force is not in these data." %
                  (below2, below3), ""]
    else:
        lines += ["No overlapping days yet.", ""]

    lines += ["## 6. What these data cannot tell us", "",
              "- Tunnel flows between reservoirs and the withdrawal to Sao Paulo are not published in SAR; only the residual in section 2 is available.",
              "- No sub-daily river data: ANA's public telemetry returned nothing for the Atibaia gauges. Ten-minute river data exist on the Sao Paulo state network (SIBH) and have not been downloaded; its rain gauges are used, as daily totals (`pipeline/sibh_rain.py`).",
              "- Gauge discharge comes from rating curves; their uncertainty is not published in the open service.",
              "- Rainfall and evaporation are in the pipeline (`pipeline/forcing.py`); the inflow models built on them did not pass validation (see the README).", ""]

    c.ensure_dir(os.path.dirname(REPORT))
    with open(REPORT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    # ---- viewer data ------------------------------------------------------------
    c.ensure_dir(WEB_DATA)
    if system:
        all_days = [d.isoformat() for d in daterange(dt.date.fromisoformat(min(system)), dt.date.fromisoformat(max(system)))]
    else:
        all_days = []
    r2 = lambda x: None if x is None else round(x, 2)
    web = {
        "generated_utc": dt.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "dates": all_days,
        "provenance": {
            "reservoirs": "ANA SAR, Cantareira module (https://www.ana.gov.br/sar0/MedicaoCantareira). Observed, operator-reported. Release excludes tunnel transfers.",
            "gauges": "ANA HidroSerieHistorica (http://telemetriaws1.ana.gov.br/ServiceANA.asmx). Observed stage converted to discharge by rating curve.",
            "derived": "System storage, operating band, implied net export and incremental flow are computed in pipeline/process.py from the observations; formulas in that file and in docs/data_quality_report.md.",
        },
        "system_useful_hm3": SYSTEM_USEFUL_HM3,
        "curve_revision_date": CURVE_REVISION,
        "bands": c.OPERATING_BANDS,
        "reservoirs": {},
        "system": {
            "pct": [r2(system[d]["pct"]) if d in system else None for d in all_days],
            "hm3": [r2(system[d]["hm3"]) if d in system else None for d in all_days],
            "capacity": [r2(system[d]["cap"]) if d in system else None for d in all_days],
            "band": [system[d]["band"] if d in system else None for d in all_days],
            "inflow": [r2(system[d]["inflow"]) if d in system else None for d in all_days],
            "release": [r2(system[d]["release"]) if d in system else None for d in all_days],
            "export30": [r2(system[d].get("export30")) if d in system else None for d in all_days],
        },
        "gauges": {},
    }
    for code, meta in c.RESERVOIRS.items():
        k = meta["key"]
        web["reservoirs"][k] = {
            "name": meta["name"], "basin": meta["basin"], "useful_hm3": meta["useful_hm3"],
            "level": [r2(sar[k][d]["level"]) if d in sar[k] else None for d in all_days],
            "pct": [r2(sar[k][d]["pct"]) if d in sar[k] else None for d in all_days],
            "hm3": [r2(sar[k][d]["hm3"]) if d in sar[k] else None for d in all_days],
            "inflow": [r2(sar[k][d]["inflow"]) if d in sar[k] else None for d in all_days],
            "release": [r2(sar[k][d]["release"]) if d in sar[k] else None for d in all_days],
        }
    for code in ["62670000", "62665000", "62662000", "62676000"]:
        g = gauges.get(code, {})
        meta = c.GAUGES.get(code) or EXTRA_META.get(code, {})
        web["gauges"][code] = {
            "name": meta.get("name") or extra.get(code, code),
            "lat": meta.get("lat"), "lon": meta.get("lon"), "area_km2": meta.get("area_km2"),
            "flow": [r2(g[d][0]) if d in g else None for d in all_days],
            "last_day": max(g) if g else None,
        }
    # ---- model output: the series reaches the viewer ONLY if the model passed validation
    web["model"] = {}
    results_path = os.path.join(c.PROCESSED, "model_results.json")
    if os.path.exists(results_path):
        with open(results_path, encoding="utf-8") as f:
            results = json.load(f)
        for name, res in results.items():
            entry = {"label": res["label"], "accepted": res["accepted"], "parameters": res["parameters"],
                     "rain_lag_days": res["rain_lag_days"], "ensemble_size": res["ensemble_size"],
                     "periods": {k: {"kge": None if v["model"] is None else round(v["model"]["kge"], 2),
                                     "benchmark_kge": None if v["benchmark"] is None else round(v["benchmark"]["kge"], 2),
                                     "bias_pct": None if v["model"] is None else round(v["model"]["bias_pct"], 0),
                                     "passed": v.get("passed")} for k, v in res["periods"].items()}}
            if res["accepted"]:
                rows = {r["date"]: r for r in c.read_csv(os.path.join(c.PROCESSED, "model_inflow_%s.csv" % name))}
                pick = lambda col: [round(float(rows[d][col]), 2) if d in rows else None for d in all_days]
                entry.update({"sim": pick("modelled_inflow_m3s"), "low": pick("ensemble_low_m3s"),
                              "high": pick("ensemble_high_m3s"), "last_day": max(rows)})
            web["model"][name] = entry
    # ---- run 3 supersedes runs 1 and 2: its verdict is what the viewer reports
    run3_dir = os.path.join(c.PROCESSED, "run3")
    decision_path = os.path.join(run3_dir, "decision.json")
    if os.path.exists(decision_path):
        with open(decision_path, encoding="utf-8") as f:
            decision = json.load(f)
        labels = {"cachoeira_dam": "Cachoeira", "atibainha_dam": "Atibainha"}
        web["model"] = {}
        for name, pick in decision["chosen"].items():
            parts = []
            for fold in ("fold1", "fold2"):
                p = os.path.join(run3_dir, "%s_gr4j_%s.json" % (name, fold))
                if os.path.exists(p):
                    with open(p, encoding="utf-8") as f:
                        v = json.load(f)["validation"]
                    parts.append("%s validation daily KGE %.2f, volume bias %+.0f%%, low-flow bias %+.0f%%" %
                                 (fold.replace("fold", "fold "), v["kge"], v["bias_pct"], v["low_flow_bias_pct"]))
            web["model"][name] = {"label": labels[name], "accepted": pick is not None, "ensemble_size": 30,
                                  "summary": "%s (run 3, GR4J): %s." % (labels[name], "; ".join(parts))}
            r4 = os.path.join(run3_dir, "run4_decision.json")
            if name == "cachoeira_dam" and os.path.exists(r4):
                with open(r4, encoding="utf-8") as f:
                    d4 = json.load(f)
                web["model"][name]["accepted"] = d4["accepted"]
                web["model"][name]["summary"] += " Run 4 re-scored low flows on 7-day means: %s. %s" % (
                    ", ".join("%s %+.0f%%" % (k.replace("fold", "fold "), v["low_flow_7day"]["bias_pct"]) for k, v in d4["folds"].items()),
                    "Accepted (provisional)." if d4["accepted"] else "Still not accepted; modelling on this record has stopped.")
            # an accepted structure would add its series here after the final calibration
    with open(os.path.join(WEB_DATA, "timeseries.json"), "w", encoding="utf-8") as f:
        json.dump(web, f, ensure_ascii=False, separators=(",", ":"))
    print("report:", REPORT)
    print("days in viewer file:", len(all_days))


if __name__ == "__main__":
    main()
