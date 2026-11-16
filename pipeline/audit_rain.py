"""Audit the rain gauges against each other, year by year and month by month.

No model output is used here: a gauge is judged only against its neighbours.

Checks (thresholds fixed here, before looking at any model result):
  A. Dry-record month: a month with at least 25 days reported whose total is
     under 25 % of the regional median, when that median is 50 mm or more.
     Typical of days that were not read but stored as zero.
  B. Anomalous year: a year with at least 330 days reported whose ratio to the
     regional median of complete years is under 70 % or over 140 % of that
     gauge's OWN long-term median ratio. Comparing each gauge with its own
     typical ratio keeps a site that is genuinely wetter or drier than its
     neighbours (for example a high-altitude gauge) from being rejected.
     (The first version of this rule compared with the regional median
     directly; it wrongly flagged Fazenda Bonfim, a consistently wetter
     mountain site. The rule was changed on that evidence alone, before any
     model was run on the audited rainfall.)
The regional median is taken over all audited gauges with enough days in
that month or year (at least three gauges, otherwise no judgement is made).
The audited gauges are ANA's conventional gauges and, once sibh_rain.py has
built them, the SIBH telemetric gauges (forcing.ALL_GAUGES); the rules are
the same for both.

Outputs: docs/rain_audit.md and data/processed/rain_exclusions.json, the
list of gauge-months and gauge-years that forcing.py leaves out.

Usage: python audit_rain.py
"""
import datetime as dt
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # isolated mode drops the script folder
import common as c  # noqa: E402
from forcing import ALL_GAUGES as RAIN_GAUGES, load_rain  # noqa: E402

FIRST_YEAR = 1984
DRY_RATIO = 0.25
DRY_MIN_REGIONAL_MM = 50.0
YEAR_LOW, YEAR_HIGH = 0.70, 1.40
MIN_GAUGES = 3


def median(v):
    v = sorted(v)
    return v[len(v) // 2] if len(v) % 2 else (v[len(v) // 2 - 1] + v[len(v) // 2]) / 2.0


def main():
    rain = {code: load_rain(code) for code in RAIN_GAUGES}
    last_year = dt.date.today().year
    month = {}  # (code, 'YYYY-MM') -> [days, total]
    year = {}   # (code, 'YYYY') -> [days, total, wet days]
    for code, series in rain.items():
        for d, v in series.items():
            if int(d[:4]) < FIRST_YEAR:
                continue
            m = month.setdefault((code, d[:7]), [0, 0.0])
            m[0] += 1
            m[1] += v
            y = year.setdefault((code, d[:4]), [0, 0.0, 0])
            y[0] += 1
            y[1] += v
            y[2] += 1 if v > 0.1 else 0

    dry = []      # (code, month, total, regional)
    months = sorted({k[1] for k in month})
    for ym in months:
        vals = {code: month[(code, ym)][1] for code in RAIN_GAUGES if (code, ym) in month and month[(code, ym)][0] >= 25}
        if len(vals) < MIN_GAUGES:
            continue
        ref = median(list(vals.values()))
        if ref < DRY_MIN_REGIONAL_MM:
            continue
        for code, v in vals.items():
            if v < DRY_RATIO * ref:
                dry.append((code, ym, v, ref))

    biased = []   # (code, year, total, regional, ratio)
    ratios = {}
    for y in range(FIRST_YEAR, last_year + 1):
        ys = str(y)
        vals = {code: year[(code, ys)][1] for code in RAIN_GAUGES if (code, ys) in year and year[(code, ys)][0] >= 330}
        if len(vals) < MIN_GAUGES:
            continue
        ref = median(list(vals.values()))
        for code, v in vals.items():
            ratios[(code, ys)] = v / ref
        totals_ref = locals().setdefault("totals_ref", {})
        for code, v in vals.items():
            totals_ref[(code, ys)] = (v, ref)
    own = {}
    for code in RAIN_GAUGES:
        rs = [r for (cd, _), r in ratios.items() if cd == code]
        if rs:
            own[code] = median(rs)
    for (code, ys), r in sorted(ratios.items()):
        rel = r / own[code]
        if rel < YEAR_LOW or rel > YEAR_HIGH:
            v, ref = totals_ref[(code, ys)]
            biased.append((code, ys, v, ref, r))

    excl = {"rule": {"dry_month": "at least 25 days reported, total under %.0f%% of the regional median, median at least %.0f mm" % (DRY_RATIO * 100, DRY_MIN_REGIONAL_MM),
                     "biased_year": "at least 330 days reported, ratio to the regional median under %.0f%% or over %.0f%% of the gauge's own median ratio" % (YEAR_LOW * 100, YEAR_HIGH * 100),
                     "regional_median": "all audited gauges with enough days; at least %d gauges" % MIN_GAUGES},
            "months": sorted({"%s|%s" % (code, ym) for code, ym, _, _ in dry}),
            "years": sorted({"%s|%s" % (code, y) for code, y, _, _, _ in biased})}
    with open(os.path.join(c.PROCESSED, "rain_exclusions.json"), "w", encoding="utf-8") as f:
        json.dump(excl, f, indent=1)

    L = ["# Rain gauge audit", "",
         "Generated %s UTC by `pipeline/audit_rain.py`. Gauges are judged only against each other; no model output is used." %
         dt.datetime.utcnow().strftime("%Y-%m-%d %H:%M"), "",
         "Rules: " + excl["rule"]["dry_month"] + " (dry-record month); " + excl["rule"]["biased_year"] + " (anomalous year).", "",
         "## Summary by gauge, %d to %d" % (FIRST_YEAR, last_year), "",
         "| Code | Name | Years with 330+ days | Median ratio to region | Lowest and highest yearly ratio | Dry-record months | Anomalous years |",
         "| --- | --- | --- | --- | --- | --- | --- |"]
    for code, (name, _, _) in RAIN_GAUGES.items():
        rs = [(r, y) for (cd, y), r in ratios.items() if cd == code]
        nd = sum(1 for d in dry if d[0] == code)
        nb = sorted(b[1] for b in biased if b[0] == code)
        if not rs:
            L.append("| %s | %s | 0 | no complete year | | %d | |" % (code, name, nd))
            continue
        lo, hi = min(rs), max(rs)
        L.append("| %s | %s | %d | %.2f | %.2f (%s) to %.2f (%s) | %d | %s |" % (
            code, name, len(rs), median([r for r, _ in rs]), lo[0], lo[1], hi[0], hi[1], nd, ", ".join(nb) or "none"))

    L += ["", "## Dry-record months by gauge and year", "",
          "Count of flagged months per year (only years with at least one flag are listed).", "",
          "| Code | Name | Flagged months by year |", "| --- | --- | --- |"]
    for code, (name, _, _) in RAIN_GAUGES.items():
        by = {}
        for cd, ym, _, _ in dry:
            if cd == code:
                by[ym[:4]] = by.get(ym[:4], 0) + 1
        if by:
            L.append("| %s | %s | %s |" % (code, name, ", ".join("%s: %d" % kv for kv in sorted(by.items()))))

    L += ["", "## Yearly totals from 2010, mm (blank = fewer than 330 days reported; * = flagged biased year)", ""]
    codes = [cd for cd in RAIN_GAUGES if any((cd, str(y)) in year for y in range(2010, last_year + 1))]
    L.append("| Year | " + " | ".join("%s %s" % (cd, RAIN_GAUGES[cd][0]) for cd in codes) + " | Regional median |")
    L.append("| --- |" + " --- |" * (len(codes) + 1))
    flagged = {(b[0], b[1]) for b in biased}
    for y in range(2010, last_year + 1):
        ys = str(y)
        cells = []
        full = []
        for cd in codes:
            k = (cd, ys)
            if k in year and year[k][0] >= 330:
                cells.append("%.0f%s" % (year[k][1], "*" if k in flagged else ""))
                full.append(year[k][1])
            elif k in year:
                cells.append("(%d days)" % year[k][0])
            else:
                cells.append("")
        L.append("| %s | %s | %s |" % (ys, " | ".join(cells), "%.0f" % median(full) if len(full) >= MIN_GAUGES else "too few gauges"))

    L += ["", "## Coverage: gauges reporting at least 330 days, by year", "",
          "| Year | Gauges |", "| --- | --- |"]
    for y in range(FIRST_YEAR, last_year + 1):
        n = sum(1 for cd in RAIN_GAUGES if (cd, str(y)) in year and year[(cd, str(y))][0] >= 330)
        L.append("| %d | %d |" % (y, n))
    with open(os.path.join(c.ROOT, "docs", "rain_audit.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")
    print("dry-record months:", len(dry), " biased years:", len(biased))
    print("report: docs/rain_audit.md")


if __name__ == "__main__":
    main()
