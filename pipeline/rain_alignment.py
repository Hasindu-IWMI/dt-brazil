"""Check the day labelling of each ANA rain gauge against the telemetric SIBH sites.

sibh_rain.py found that most ANA gauges label day D with the 24 hours ending at 07:00 on D,
but some pairs agreed better one day apart. This script asks, gauge by gauge and year by year:
does the ANA gauge agree best with nearby telemetric sites at a shift of -1, 0 or +1 day?

Method (fixed here before running): ANA gauge day D is compared with the SIBH site series
(already on ANA's convention) at day D + s, s in {-1, 0, +1}. For each ANA gauge and calendar
year, the correlation is computed against every SIBH site within PAIR_KM sharing at least
MIN_DAYS complete days that year, and the median over sites is taken. A gauge-year is reported
as SHIFTED when the best shift is not 0 and its median correlation exceeds the shift-0 value by
at least MARGIN. Unaudited ANA records are used (the audit removes only gross under-recording).

No model output is used. Nothing here changes forcing.py: the result is reported only.

Output: docs/rain_alignment.md and data/processed/rain_alignment.json.
Usage: python rain_alignment.py
"""
import datetime as dt
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # isolated mode drops the script folder
import common as c  # noqa: E402
import forcing as fo  # noqa: E402
from sibh_rain import median, pearson  # noqa: E402

PAIR_KM = 15.0
MIN_DAYS = 200
MARGIN = 0.15
SHIFTS = (-1, 0, 1)


def shifted(day, s):
    return (dt.date.fromisoformat(day) + dt.timedelta(days=s)).isoformat()


def main():
    sibh = fo.sibh_gauges()
    if not sibh:
        sys.exit("no SIBH sites; run sibh_rain.py first")
    sites = {code: fo.load_rain(code) for code in sibh}
    rows, out = [], {}
    for code, (name, la, lo) in fo.RAIN_GAUGES.items():
        ana = {d: v for d, v in fo.load_rain(code).items() if d >= "2010-01-01"}
        if not ana:
            continue
        near = [(fo.km(la, lo, sibh[s][1], sibh[s][2]), s) for s in sites]
        near = [s for d, s in sorted(near) if d <= PAIR_KM]
        years = sorted({d[:4] for d in ana})
        for y in years:
            per_shift = {}
            n_sites = 0
            for s in SHIFTS:
                rs = []
                for site in near:
                    days = [d for d in ana if d[:4] == y and shifted(d, s) in sites[site]]
                    if len(days) < MIN_DAYS:
                        continue
                    r = pearson([ana[d] for d in days], [sites[site][shifted(d, s)] for d in days])
                    if r is not None:
                        rs.append(r)
                if rs:
                    per_shift[s] = median(rs)
                    n_sites = max(n_sites, len(rs))
            if len(per_shift) < len(SHIFTS):
                continue
            best = max(SHIFTS, key=lambda s: per_shift[s])
            flag = best != 0 and per_shift[best] - per_shift[0] >= MARGIN
            out.setdefault(code, {})[y] = {"r": {str(s): round(per_shift[s], 3) for s in SHIFTS}, "best": best, "shifted": flag, "sites": n_sites}
            rows.append((code, name, y, per_shift, best, flag, n_sites))
    with open(os.path.join(c.PROCESSED, "rain_alignment.json"), "w", encoding="utf-8") as f:
        json.dump({"rule": "best shift != 0 and median r exceeds shift 0 by >= %.2f; sites within %.0f km, >= %d shared days" % (MARGIN, PAIR_KM, MIN_DAYS),
                   "shift_meaning": "ANA day D compared with SIBH day D + shift", "gauges": out}, f, indent=1)

    L = ["# Day alignment of the ANA rain gauges", "",
         "Generated %s UTC by `pipeline/rain_alignment.py`. No model output is used; nothing here changes the forcing." %
         dt.datetime.utcnow().strftime("%Y-%m-%d %H:%M"), "",
         "Each ANA gauge, from 2010, is compared year by year with the telemetric SIBH sites within %.0f km "
         "(on ANA's own day convention, see `sibh_rain_report.md`). r(s) is the median, over sites with at least %d "
         "shared days that year, of the daily correlation between ANA day D and the site's day D + s. "
         "A year is marked **shifted** when the best s is not 0 and beats s = 0 by at least %.2f." % (PAIR_KM, MIN_DAYS, MARGIN), "",
         "## Summary by gauge", "", "| Code | Name | Years compared | Years shifted | Shifted years | Median r(0) | Median r at best shift |", "| --- | --- | --- | --- | --- | --- | --- |"]
    by = {}
    for code, name, y, ps, best, flag, n in rows:
        by.setdefault((code, name), []).append((y, ps, best, flag))
    for (code, name), ys in by.items():
        sh = [y for y, _, _, f in ys if f]
        L.append("| %s | %s | %d | %d | %s | %.2f | %.2f |" % (code, name, len(ys), len(sh), ", ".join(sh) or "none",
                                                           median([ps[0] for _, ps, _, _ in ys]), median([ps[b] for _, ps, b, _ in ys])))
    L += ["", "## By year", "", "| Code | Name | Year | Sites | r(-1) | r(0) | r(+1) | Best | Shifted |", "| --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
    for code, name, y, ps, best, flag, n in rows:
        L.append("| %s | %s | %s | %d | %.2f | %.2f | %.2f | %+d | %s |" % (code, name, y, n, ps[-1], ps[0], ps[1], best, "**yes**" if flag else ""))
    with open(os.path.join(c.ROOT, "docs", "rain_alignment.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")
    print("gauge-years compared:", len(rows), " shifted:", sum(1 for r in rows if r[5]))
    print("report: docs/rain_alignment.md")


if __name__ == "__main__":
    main()
