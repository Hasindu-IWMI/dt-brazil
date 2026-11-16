"""Why does the share of rain that becomes inflow change between decades?

Three areas are compared by water year (October to September):
  cachoeira   inflow to Cachoeira reservoir, operator-computed (ANA SAR), 392 km2
  atibainha   inflow to Atibainha reservoir, operator-computed (ANA SAR), 312 km2
  middle      the unregulated area between the two dams and the Atibaia gauge,
              measured ONLY by river gauges, independent of the operator:
              Atibaia gauge 62670000 (1140 km2) minus Piracaia gauge 62665000
              (431 km2) minus Nazare Paulista gauge 62662000 (358 km2) = 351 km2

Tests
  T1  Does the independent middle area show the same change as the two
      operator-computed inflows? If yes, the change is in the catchments, not
      in the operator's accounting.
  T2  How much of the change does climate explain? Fu's form of the Budyko
      curve, with its one parameter fitted on 2004-2013 water years, predicts
      the runoff share from rain and evaporation demand alone.
  T3  Is the runoff share lower after dry years (catchment memory)? Correlation
      of the yearly share with that year's rain and with the previous two years.
  T4  Did Atibainha gain inflow relative to Cachoeira when the Paraiba do Sul
      link started (2018)? Ratio of the two inflows by period.

No model calibration is involved. Rain is the audited catchment rain.

Usage: python investigate_runoff.py
"""
import datetime as dt
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # isolated mode drops the script folder
import common as c  # noqa: E402
import forcing as fo  # noqa: E402
import json  # noqa: E402

PERIODS = [("1986–2001", 1986, 2001), ("2004–2013", 2004, 2013), ("2014–2016", 2014, 2016),
           ("2017–2021", 2017, 2021), ("2022–2025", 2022, 2025)]
MIDDLE_CENTROID = (-23.11, -46.46)  # between the dams and the Atibaia gauge
MIN_DAYS = 350


def wy(date):
    """Water year label: October 1985 to September 1986 is water year 1986."""
    y, m = int(date[:4]), int(date[5:7])
    return y + 1 if m >= 10 else y


def corr(xs, ys):
    n = len(xs)
    if n < 5:
        return None
    mx, my = sum(xs) / n, sum(ys) / n
    vx = sum((a - mx) ** 2 for a in xs)
    vy = sum((b - my) ** 2 for b in ys)
    if vx <= 0 or vy <= 0:
        return None
    return sum((a - mx) * (b - my) for a, b in zip(xs, ys)) / math.sqrt(vx * vy)


def fu_runoff_share(p, pet, w):
    phi = pet / p
    return 1.0 - (1.0 + phi - (1.0 + phi ** w) ** (1.0 / w))


def main():
    f_c = {r["date"]: r for r in c.read_csv(os.path.join(c.PROCESSED, "forcing_cachoeira_dam.csv"))}
    f_a = {r["date"]: r for r in c.read_csv(os.path.join(c.PROCESSED, "forcing_atibainha_dam.csv"))}
    num = lambda v: None if v in ("", "None") else float(v)
    inflow = {k: {r["date"]: num(r["inflow_m3s"]) for r in c.read_csv(os.path.join(c.PROCESSED, "sar_%s.csv" % k))}
              for k in ("cachoeira", "atibainha")}

    def gauge(code):
        out = {}
        for r in c.read_csv(os.path.join(c.PROCESSED, "ana_discharge_%s.csv" % code)):
            v = float(r["discharge_m3s"])
            if 0 <= v < 99999:
                out[r["date"]] = v
        return out

    q_at, q_pi, q_na = gauge("62670000"), gauge("62665000"), gauge("62662000")

    # audited rain for the middle area
    excl = json.load(open(os.path.join(c.PROCESSED, "rain_exclusions.json"), encoding="utf-8"))
    rain = {code: fo.load_rain(code, excl) for code in fo.RAIN_GAUGES}
    near = sorted((fo.km(MIDDLE_CENTROID[0], MIDDLE_CENTROID[1], la, lo), code) for code, (_, la, lo) in fo.RAIN_GAUGES.items())
    used = [(d, code) for d, code in near if d <= fo.RADIUS_KM and rain[code]]

    areas = {"cachoeira": 392.0, "atibainha": 312.0, "middle": 1140.0 - 431.0 - 358.0}
    yearly = {k: {} for k in areas}  # wy -> dict(days, rain, pet, flow_mm)
    d = dt.date(1984, 10, 1)
    end = dt.date.today()
    while d <= end:
        key = d.isoformat()
        y = wy(key)
        for name, fr in (("cachoeira", f_c), ("atibainha", f_a)):
            r = fr.get(key)
            q = inflow[name].get(key)
            if r and num(r["rain_mm"]) is not None and num(r["pet_mm"]) is not None and q is not None:
                a = yearly[name].setdefault(y, [0, 0.0, 0.0, 0.0])
                a[0] += 1
                a[1] += num(r["rain_mm"])
                a[2] += num(r["pet_mm"])
                a[3] += q * 86.4 / areas[name]
        p, _ = fo.areal(rain, used, key)
        r = f_a.get(key)
        if p is not None and key in q_at and key in q_pi and key in q_na and r and num(r["pet_mm"]) is not None:
            a = yearly["middle"].setdefault(y, [0, 0.0, 0.0, 0.0])
            a[0] += 1
            a[1] += p
            a[2] += num(r["pet_mm"])
            a[3] += (q_at[key] - q_pi[key] - q_na[key]) * 86.4 / areas["middle"]
        d += dt.timedelta(days=1)
    for name in yearly:  # keep near-complete water years, scaled to a full year
        yearly[name] = {y: (v[1] * 365.25 / v[0], v[2] * 365.25 / v[0], v[3] * 365.25 / v[0])
                        for y, v in yearly[name].items() if v[0] >= MIN_DAYS}

    L = ["# Why the runoff share changes: investigation", "",
         "Generated %s UTC by `pipeline/investigate_runoff.py`. Water years run October to September. "
         "Rain is the audited catchment rain; evaporation demand is Oudin PET from reanalysis temperature. "
         "No model calibration is involved." % dt.datetime.utcnow().strftime("%Y-%m-%d %H:%M"), "",
         "Areas: **Cachoeira** and **Atibainha** inflows are computed by the operator from a reservoir balance. "
         "**Middle** is the 351 km2 between the two dams and the Atibaia gauge, measured only by three river gauges "
         "(rain gauges used: %s)." % ", ".join(fo.RAIN_GAUGES[code][0] for _, code in used), "",
         "## T1. Runoff share by period: operator inflows against the independent area", "",
         "| Period | Area | Water years | Rain (mm) | PET (mm) | Runoff (mm) | Runoff share |",
         "| --- | --- | --- | --- | --- | --- | --- |"]
    means = {}
    for label, a, b in PERIODS:
        for name in ("cachoeira", "atibainha", "middle"):
            ys = [v for y, v in yearly[name].items() if a <= y <= b]
            if not ys:
                L.append("| %s | %s | 0 | no data | | | |" % (label, name))
                continue
            p = sum(v[0] for v in ys) / len(ys)
            e = sum(v[1] for v in ys) / len(ys)
            q = sum(v[2] for v in ys) / len(ys)
            means[(label, name)] = (p, e, q, len(ys))
            L.append("| %s | %s | %d | %.0f | %.0f | %.0f | %.2f |" % (label, name, len(ys), p, e, q, q / p))

    L += ["", "## T2. How much does climate alone explain?", "",
          "Fu's Budyko curve, one parameter fitted to each area's 2004–2013 mean, then applied to the other periods' "
          "rain and PET. The last column is observed minus predicted runoff, as a share of observed.", "",
          "| Area | Fitted w | Period | Observed share | Climate-only prediction | Observed runoff (mm) | Predicted (mm) | Unexplained |",
          "| --- | --- | --- | --- | --- | --- | --- | --- |"]
    for name in ("cachoeira", "atibainha", "middle"):
        base = means.get(("2004–2013", name))
        if not base:
            continue
        p0, e0, q0, _ = base
        lo, hi = 1.01, 10.0
        for _ in range(60):  # bisection: runoff share falls as w rises
            mid = (lo + hi) / 2
            if fu_runoff_share(p0, e0, mid) > q0 / p0:
                lo = mid
            else:
                hi = mid
        w = (lo + hi) / 2
        for label, _, _ in PERIODS:
            m = means.get((label, name))
            if not m:
                continue
            p, e, q, _ = m
            pred = fu_runoff_share(p, e, w)
            L.append("| %s | %.2f | %s | %.2f | %.2f | %.0f | %.0f | %+.0f%% |" % (
                name, w, label, q / p, pred, q, pred * p, (q - pred * p) / q * 100.0))

    L += ["", "## T3. Catchment memory: yearly runoff share against rain", "",
          "| Area | Water years | Correlation with same-year rain | With mean rain of the previous two years | With the year (trend) |",
          "| --- | --- | --- | --- | --- |"]
    for name in ("cachoeira", "atibainha", "middle"):
        ys = sorted(yearly[name])
        share = {y: yearly[name][y][2] / yearly[name][y][0] for y in ys}
        same = corr([yearly[name][y][0] for y in ys], [share[y] for y in ys])
        prev = [(0.5 * (yearly[name][y - 1][0] + yearly[name][y - 2][0]), share[y]) for y in ys
                if y - 1 in yearly[name] and y - 2 in yearly[name]]
        pc = corr([a for a, _ in prev], [b for _, b in prev]) if prev else None
        tr = corr([float(y) for y in ys], [share[y] for y in ys])
        f = lambda v: "too few years" if v is None else "%.2f" % v
        L.append("| %s | %d | %s | %s | %s |" % (name, len(ys), f(same), f(pc), f(tr)))

    L += ["", "## T4. Atibainha inflow relative to Cachoeira inflow", "",
          "If water from the Paraíba do Sul link (operating since 2018) were counted as Atibainha inflow, this ratio "
          "would rise from 2018.", "",
          "| Period | Days | Mean Cachoeira inflow (m3/s) | Mean Atibainha inflow (m3/s) | Ratio |", "| --- | --- | --- | --- | --- |"]
    for label, a, b in [("1986–2001", 1986, 2001), ("2004–2013", 2004, 2013), ("2014–2017", 2014, 2017),
                        ("2018–2021", 2018, 2021), ("2022–2026", 2022, 2026)]:
        pairs = [(inflow["cachoeira"][k], inflow["atibainha"][k]) for k in inflow["cachoeira"]
                 if a <= int(k[:4]) <= b and inflow["cachoeira"][k] is not None and inflow["atibainha"].get(k) is not None]
        mc = sum(x for x, _ in pairs) / len(pairs)
        ma = sum(y for _, y in pairs) / len(pairs)
        L.append("| %s | %d | %.2f | %.2f | %.2f |" % (label, len(pairs), mc, ma, ma / mc))

    L += ["", "## Water-year table", "",
          "| Water year | Cachoeira rain | runoff | share | Atibainha rain | runoff | share | Middle rain | runoff | share |",
          "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
    for y in range(1985, end.year + 1):
        cells = []
        for name in ("cachoeira", "atibainha", "middle"):
            v = yearly[name].get(y)
            cells += ["", "", ""] if v is None else ["%.0f" % v[0], "%.0f" % v[2], "%.2f" % (v[2] / v[0])]
        if any(cells):
            L.append("| %d | %s |" % (y, " | ".join(cells)))
    with open(os.path.join(c.ROOT, "docs", "runoff_shift_investigation.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")
    print("\n".join(L[4:]))


if __name__ == "__main__":
    main()
