"""Unit tests for the pipeline's parsing and processing rules (standard library).

Run from the repository root:  python -I -m unittest discover -s tests -v
"""
import datetime as dt
import gzip
import json
import math
import os
import shutil
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "pipeline"))

import audit_rain  # noqa: E402
import common as c  # noqa: E402
import fetch_ana_series  # noqa: E402
import fetch_sar_cantareira  # noqa: E402
import fetch_sibh_flow  # noqa: E402
import fetch_sibh_rain  # noqa: E402
import forcing  # noqa: E402
import gr4j  # noqa: E402
import process  # noqa: E402
import sibh_flow  # noqa: E402
import sibh_rain  # noqa: E402


class Common(unittest.TestCase):
    def test_fnum_decimal_comma_and_junk(self):
        self.assertEqual(c.fnum("1.234,5"), 1234.5)
        self.assertEqual(c.fnum("12,3"), 12.3)
        self.assertEqual(c.fnum("3.5"), 3.5)
        self.assertEqual(c.fnum(" 7\xa0"), 7.0)
        for junk in ("", "-", "--", "abc", None):
            self.assertIsNone(c.fnum(junk))


class AnaSeries(unittest.TestCase):
    XML = """<root>
<SerieHistorica diffgr:id="1"><DataHora>2020-02-01 00:00:00</DataHora><NivelConsistencia>1</NivelConsistencia>
<Chuva01>5,0</Chuva01><Chuva02>1.0</Chuva02><Chuva29>2</Chuva29><Chuva30>99</Chuva30></SerieHistorica>
<SerieHistorica diffgr:id="2"><DataHora>2020-02-01 00:00:00</DataHora><NivelConsistencia>2</NivelConsistencia>
<Chuva01>4,5</Chuva01></SerieHistorica>
</root>"""

    def test_consolidated_level_wins_and_month_end_respected(self):
        s = fetch_ana_series.parse(self.XML, "Chuva")
        self.assertEqual(s["2020-02-01"], (4.5, "2"))   # level 2 replaces level 1
        self.assertEqual(s["2020-02-02"], (1.0, "1"))   # only level 1 has this day
        self.assertIn("2020-02-29", s)                   # leap day kept
        self.assertNotIn("2020-02-30", s)                # day 30 of February ignored
        self.assertEqual(len(s), 3)


class SarParse(unittest.TestCase):
    def test_rows_and_missing_table(self):
        page = ("<html><table><tr><th>h</th></tr>"
                "<tr><td>x</td><td>y</td><td>820,5</td><td>100,2</td><td>45,1</td><td>3,2</td><td>1,0</td><td>05/03/2015</td></tr>"
                "<tr><td>short</td></tr></table></html>").encode("utf-8")
        rows = fetch_sar_cantareira.parse_rows(page)
        self.assertEqual(rows, [("2015-03-05", 820.5, 100.2, 45.1, 3.2, 1.0)])
        self.assertIsNone(fetch_sar_cantareira.parse_rows(b"<html>no result</html>"))


class SarRefresh(unittest.TestCase):
    def test_open_window_replaces_stale_copy(self):
        """Re-fetching the current half-year must not leave the earlier partial file behind."""
        today = dt.date.today()
        start = dt.date(today.year, 1 if today.month <= 6 else 7, 1)
        page = ("<table><tr><td>x</td><td>y</td><td>1</td><td>2</td><td>3</td><td>4</td><td>5</td><td>%s</td></tr></table>"
                % start.strftime("%d/%m/%Y")).encode("utf-8")
        tmp = tempfile.mkdtemp(dir=ROOT)  # same drive as the repo: main() logs paths relative to it
        saved = (fetch_sar_cantareira.RAW_DIR, fetch_sar_cantareira.fetch_window, c.append_manifest, sys.argv)
        try:
            fetch_sar_cantareira.RAW_DIR = tmp
            fetch_sar_cantareira.fetch_window = lambda code, a, b: ("url", page)
            c.append_manifest = lambda entry: None
            stale = os.path.join(tmp, "cachoeira_%s_%s.html" % (start.isoformat(), (start + dt.timedelta(days=1)).isoformat()))
            open(stale, "wb").close()
            sys.argv = ["fetch_sar_cantareira.py", str(today.year), str(today.year), "29002"]
            fetch_sar_cantareira.main()
            names = sorted(n for n in os.listdir(tmp) if n.startswith("cachoeira_%s_" % start.isoformat()))
            self.assertEqual(names, ["cachoeira_%s_%s.html" % (start.isoformat(), today.isoformat())])
        finally:
            fetch_sar_cantareira.RAW_DIR, fetch_sar_cantareira.fetch_window, c.append_manifest, sys.argv = saved
            shutil.rmtree(tmp)


class OperatingBands(unittest.TestCase):
    def test_thresholds(self):
        self.assertEqual(process.band_for(60.0)["name"], "Normal")
        self.assertEqual(process.band_for(59.99)["name"], "Atenção")
        self.assertEqual(process.band_for(30.0)["name"], "Alerta")
        self.assertEqual(process.band_for(20.0)["name"], "Restrição")
        self.assertEqual(process.band_for(-23.3)["name"], "Especial")


class Forcing(unittest.TestCase):
    def test_oudin_pet(self):
        self.assertEqual(forcing.oudin_pet(-6.0, -23.0, 15), 0.0)
        summer = forcing.oudin_pet(22.0, -23.0, 15)
        winter = forcing.oudin_pet(22.0, -23.0, 196)
        self.assertTrue(3.0 < summer < 7.0, summer)
        self.assertGreater(summer, winter)  # southern hemisphere: January has more radiation

    def test_areal_inverse_distance_squared(self):
        rain = {"a": {"d": 10.0}, "b": {"d": 20.0}, "c": {}}
        v, k = forcing.areal(rain, [(1.0, "a"), (2.0, "b"), (3.0, "c")], "d")
        self.assertEqual(k, 2)
        self.assertAlmostEqual(v, round((10 * 1 + 20 * 0.25) / 1.25, 2))
        self.assertEqual(forcing.areal(rain, [(3.0, "c")], "d"), (None, 0))

    def test_km(self):
        self.assertAlmostEqual(forcing.km(-23, -46, -23, -46), 0.0)
        self.assertAlmostEqual(forcing.km(-23, -46, -24, -46), 110.574, places=2)

    def test_load_rain_exclusions_and_sources(self):
        tmp = tempfile.mkdtemp()
        old = c.PROCESSED
        try:
            c.PROCESSED = tmp
            c.write_csv(os.path.join(tmp, "ana_rain_123.csv"), ["date", "rain_mm", "consistency_level"],
                        [("2020-01-01", 5, 1), ("2020-02-01", 7, 1), ("2021-01-01", 9, 1), ("2021-01-02", 500, 1), ("2021-01-03", -1, 1)])
            c.write_csv(os.path.join(tmp, "sibh_rain_77.csv"), ["date", "rain_mm", "readings"], [("2022-01-01", 3.2, 144)])
            excl = {"months": ["123|2020-02"], "years": ["123|2021"]}
            self.assertEqual(forcing.load_rain("123"), {"2020-01-01": 5.0, "2020-02-01": 7.0, "2021-01-01": 9.0})
            self.assertEqual(forcing.load_rain("123", excl), {"2020-01-01": 5.0})
            self.assertEqual(forcing.load_rain("SIBH-77"), {"2022-01-01": 3.2})
            self.assertEqual(forcing.load_rain("missing"), {})
        finally:
            c.PROCESSED = old
            shutil.rmtree(tmp)


class Audit(unittest.TestCase):
    def test_median(self):
        self.assertEqual(audit_rain.median([3, 1, 2]), 2)
        self.assertEqual(audit_rain.median([4, 1, 3, 2]), 2.5)


class SibhSelection(unittest.TestCase):
    def test_rules(self):
        cen = {"x": (-23.0, -46.0)}
        base = {"station_type_id": "2", "latitude": "-23.01", "longitude": "-46.01"}
        st = [dict(base, id="1", prefix="A1", station_owner="CEMADEN", name="Gauge"),
              dict(base, id="2", prefix="A2", station_owner="ANA", name="Ana gauge"),
              dict(base, id="3", prefix="A3", station_owner="SABESP", name="Precipitação Radar Bacia"),
              dict(base, id="4", prefix="E3-1", station_owner="SP ÁGUAS", name="Old"),
              dict(base, id="5", prefix="A5", station_owner="SABESP", name="Far", latitude="-24.0"),
              dict(base, id="6", prefix="A6", station_owner="SABESP", name="River", station_type_id="1"),
              dict(base, id="7", prefix="A7", station_owner="IAC", name="Bad coords", latitude="")]
        out = {s["id"]: s["excluded"] for s in fetch_sibh_rain.select(st, {"E3-1"}, cen)}
        self.assertEqual(set(out), {"1", "2", "3", "4"})
        self.assertEqual(out["1"], "")
        self.assertIn("ANA", out["2"])
        self.assertIn("radar", out["3"])
        self.assertIn("conventional", out["4"])


class SibhDaily(unittest.TestCase):
    @staticmethod
    def window(start_date, values, qtd=6):
        """24 hourly sums starting 10:00 UTC (07:00 local) on start_date."""
        t0 = dt.datetime.combine(start_date, dt.time(10))
        return {t0 + dt.timedelta(hours=i): (v, qtd) for i, v in enumerate(values)}

    def test_window_label_and_sum(self):
        h = self.window(dt.date(2021, 3, 1), [1.0] * 12 + [0.5] * 12)
        rd, inc, inv = sibh_rain.daily(h, "reading day")
        self.assertEqual(rd, {"2021-03-02": (18.0, 144)})  # read at 07:00 on the 2nd
        self.assertEqual((inc, inv), (0, 0))
        rn, _, _ = sibh_rain.daily(h, "rain day")
        self.assertEqual(list(rn), ["2021-03-01"])

    def test_missing_hour_rejects_day(self):
        h = self.window(dt.date(2021, 3, 1), [0.0] * 24)
        del h[min(h)]
        kept, inc, inv = sibh_rain.daily(h, "rain day")
        self.assertEqual((kept, inc, inv), ({}, 1, 0))

    def test_invalid_hour_rejects_day(self):
        for bad in (None, -0.2, sibh_rain.MAX_HOURLY_MM + 1):
            h = self.window(dt.date(2021, 3, 1), [0.0] * 23 + [bad])
            kept, inc, inv = sibh_rain.daily(h, "rain day")
            self.assertEqual((kept, inc, inv), ({}, 0, 1), bad)

    def test_hours_split_across_utc_midnight(self):
        # 23:00 UTC and 09:00 UTC next day belong to the same local day.
        h = self.window(dt.date(2021, 12, 31), [0.0] * 13 + [2.0] + [0.0] * 9 + [3.0])
        kept, _, _ = sibh_rain.daily(h, "rain day")
        self.assertEqual(kept, {"2021-12-31": (5.0, 144)})

    def test_site_lead_wins_and_others_fill_gaps(self):
        lead = {"2026-01-12": (1.0, 144), "2026-01-13": (2.0, 144)}
        new_code = {"2026-01-13": (9.0, 144), "2026-01-14": (3.0, 144)}
        site = sibh_rain.merge_site([("616", lead), ("2346798", new_code)])
        self.assertEqual(site, {"2026-01-12": (1.0, 144, "616"), "2026-01-13": (2.0, 144, "616"),
                                "2026-01-14": (3.0, 144, "2346798")})

    def test_pearson_and_clusters(self):
        self.assertAlmostEqual(sibh_rain.pearson([1, 2, 3], [2, 4, 6]), 1.0)
        self.assertIsNone(sibh_rain.pearson([1, 1, 1], [1, 2, 3]))
        pts = [{"id": "a", "lat": -23.0, "lon": -46.0}, {"id": "b", "lat": -23.006, "lon": -46.0},
               {"id": "c", "lat": -23.012, "lon": -46.0}, {"id": "d", "lat": -23.5, "lon": -46.0}]
        groups = sorted(sorted(p["id"] for p in g) for g in sibh_rain.clusters(pts, 1.0))
        self.assertEqual(groups, [["a", "b", "c"], ["d"]])  # single linkage chains a-b-c


class SibhFlowStations(unittest.TestCase):
    def test_describe_keeps_fixed_list_and_flags_missing(self):
        listed = [{"id": "1397", "prefix": "3E-121 ", "alt_prefix": "724", "station_id": "6678", "station_owner": "SP ÁGUAS",
                   "name": "Nazaré Paulista (Atibainha Montante)", "latitude": "-23.0952", "longitude": "-46.2646"},
                  {"id": "999", "prefix": "X", "station_owner": "SABESP", "name": "Not wanted", "latitude": "-23", "longitude": "-46"}]
        out = fetch_sibh_flow.describe(listed)
        self.assertEqual([s["id"] for s in out], list(fetch_sibh_flow.STATIONS))  # fixed list, fixed order
        first = out[0]
        self.assertEqual((first["prefix"], first["group"], first["owner"]), ("3E-121", "upstream", "SP ÁGUAS"))
        self.assertTrue(all(s.get("missing_from_list") for s in out[1:]))

    def test_groups_are_known(self):
        self.assertTrue(set(g for g, _ in fetch_sibh_flow.STATIONS.values()) <= {"upstream", "below_dam", "dam", "transfer"})


class SibhFlowDaily(unittest.TestCase):
    @staticmethod
    def hours(day, levels, discharges=None, start_h=3):
        """Hourly (level_m, discharge, readings) from 03:00 UTC (00:00 local) on `day`."""
        t0 = dt.datetime.combine(day, dt.time(start_h))
        discharges = discharges if discharges is not None else [None] * len(levels)
        return {t0 + dt.timedelta(hours=i): (h, q, 6) for i, (h, q) in enumerate(zip(levels, discharges))}

    def test_local_day_runs_03_to_03_utc(self):
        self.assertEqual(sibh_flow.local_day(dt.datetime(2024, 3, 10, 2)), "2024-03-09")
        self.assertEqual(sibh_flow.local_day(dt.datetime(2024, 3, 10, 3)), "2024-03-10")
        self.assertEqual(sibh_flow.local_day(dt.datetime(2024, 3, 11, 2)), "2024-03-10")

    def test_mean_of_valid_hours_and_min_hours(self):
        h = self.hours(dt.date(2024, 3, 10), [1.0] * 12 + [2.0] * 12, [3.0] * 24)
        days, stats, med = sibh_flow.daily(h)
        self.assertEqual(days["level"], {"2024-03-10": (1.5, 24)})
        self.assertEqual(days["discharge"], {"2024-03-10": (3.0, 24)})
        self.assertEqual(stats["discharge"]["flat_days"], 1)  # unchanged all day: counted, not removed
        short = self.hours(dt.date(2024, 3, 10), [1.0] * (sibh_flow.MIN_HOURS - 1))
        days, stats, _ = sibh_flow.daily(short)
        self.assertEqual((days["level"], stats["level"]["days_short"]), ({}, 1))

    def test_invalid_hours_dropped_not_filled(self):
        q = [2.0] * 22 + [-0.1, sibh_flow.MAX_Q_M3S + 1]
        lv = [816.0] * 22 + [700.0, 0.0]  # 700 m: gross error at a reservoir at 816 m; 0 m: another datum
        days, stats, med = sibh_flow.daily(self.hours(dt.date(2024, 3, 10), lv, q))
        self.assertEqual(days["discharge"]["2024-03-10"], (2.0, 22))
        self.assertEqual(days["level"]["2024-03-10"], (816.0, 22))
        self.assertEqual(days["datum"]["2024-03-10"], "elevation")
        self.assertEqual((stats["discharge"]["invalid_hours"], stats["level"]["invalid_hours"]), (2, 1))
        self.assertEqual(stats["level"]["other_datum_hours"], 1)

    def test_datum_change_keeps_both_and_short_datum_is_dropped(self):
        h = {}
        for i in range(40):  # 40 days of stage (about 2.8 m), then 40 days of elevation (about 791.6 m)
            h.update(self.hours(dt.date(2022, 9, 1) + dt.timedelta(days=i), [2.8] * 24))
            h.update(self.hours(dt.date(2022, 11, 1) + dt.timedelta(days=i), [791.6] * 24))
        for i in range(5):   # five later days in the elevation datum just extend it
            h.update(self.hours(dt.date(2023, 3, 1) + dt.timedelta(days=i), [791.5] * 24))
        days, stats, med = sibh_flow.daily(h)
        self.assertEqual(days["datum"]["2022-09-01"], "gauge")
        self.assertEqual(days["datum"]["2022-11-01"], "elevation")
        self.assertEqual(stats["level"]["invalid_hours"], 0)  # neither datum rejects the other
        self.assertEqual(sibh_flow.level_kind(days["datum"]), "stage to 2022-10-10, then elevation")
        stray = {}
        for i in range(40):
            stray.update(self.hours(dt.date(2024, 1, 1) + dt.timedelta(days=i), [816.0] * 24))
        for i in range(3):
            stray.update(self.hours(dt.date(2024, 3, 1) + dt.timedelta(days=i), [0.0] * 24))
        days, stats, _ = sibh_flow.daily(stray)
        self.assertNotIn("2024-03-01", days["level"])
        self.assertEqual(stats["level"]["dropped_datum_days"], 3)
        self.assertEqual(sibh_flow.level_kind(days["datum"]), "elevation")

    def test_rating_curve_reproduces_sibh_discharge(self):
        # 3E-116 on 10 March 2016: curve Q = 1.0 (h - 1.0)^1.38, value 137.9 cm -> read_value 0.262.
        k = {"start": dt.datetime(2015, 12, 8), "end": dt.datetime(2017, 1, 1), "a": 1.0, "n": 1.38, "ho": 1.0,
             "hmin": 0.0, "hmax": 2.01}
        self.assertAlmostEqual(sibh_flow.curve_q(k, 1.379), 0.262, places=3)
        self.assertEqual(sibh_flow.curve_q(k, 0.9), 0.0)  # below the curve's zero-flow stage
        hourly = {dt.datetime(2016, 3, 10, 23): (1.379, 0.262, 1), dt.datetime(2016, 3, 10, 20): (1.234, 0.5, 1),
                  dt.datetime(2018, 1, 1, 0): (1.3, 0.2, 1)}  # outside the curve's dates: not checkable
        self.assertEqual(sibh_flow.curve_check(hourly, [k]), (2, 1))

    def test_rating_by_year_shows_a_curve_change(self):
        h = {}
        for y, factor in ((2022, 1.0), (2023, 1.25)):
            for i in range(600):  # each stage six times a year
                stage = 0.5 + (i % 100) / 100.0
                h[dt.datetime(y, 1, 1) + dt.timedelta(hours=i)] = (stage, factor * 4.0 * stage ** 2, 6)
        stages, by = sibh_flow.rating_by_year(h)
        self.assertAlmostEqual(stages[0], 1.0, places=6)
        self.assertAlmostEqual(by[2023][0] / by[2022][0], 1.25, places=6)
        self.assertEqual(sibh_flow.rating_by_year({}), (None, {}))

    def test_load_hourly_parses_raw_file(self):
        tmp = tempfile.mkdtemp()
        old = sibh_flow.RAW_DIR
        try:
            sibh_flow.RAW_DIR = tmp
            rows = {"measurements": [{"date": "2019/03/10 23", "value": 105.2, "read_value": 2.19, "qtd": "6"},
                                     {"date": "2019/03/10 22", "value": 81646.3, "read_value": None, "qtd": "6"},
                                     {"date": "bad", "value": 1}]}
            c.write_bytes(os.path.join(tmp, "flow_77_2019.json.gz"), gzip.compress(json.dumps(rows).encode("utf-8")))
            c.write_bytes(os.path.join(tmp, "flow_curves_77.json.gz"), gzip.compress(b"[]"))  # not a year file
            h = sibh_flow.load_hourly("77")
            self.assertEqual(h[dt.datetime(2019, 3, 10, 23)], (1.052, 2.19, 6))
            self.assertEqual(h[dt.datetime(2019, 3, 10, 22)], (816.463, None, 6))
            self.assertEqual(len(h), 2)
            # the Sabesp 8-digit codes serve metres
            metres = {"measurements": [{"date": "2024/05/21 15", "value": 817.43, "read_value": None, "qtd": "6"}]}
            sid = sorted(sibh_flow.VALUE_IN_METRES)[0]
            c.write_bytes(os.path.join(tmp, "flow_%s_2024.json.gz" % sid), gzip.compress(json.dumps(metres).encode("utf-8")))
            self.assertEqual(sibh_flow.load_hourly(sid)[dt.datetime(2024, 5, 21, 15)], (817.43, None, 6))
        finally:
            sibh_flow.RAW_DIR = old
            shutil.rmtree(tmp)


class SibhFlowComparisons(unittest.TestCase):
    def test_lag_pairs_second_series_on_later_day(self):
        a = {"2024-01-01": 1.0, "2024-01-02": 2.0}
        b = {"2024-01-02": 10.0, "2024-01-03": 20.0}
        self.assertEqual(sibh_flow.paired(a, b, 1), [(1.0, 10.0), (2.0, 20.0)])
        self.assertEqual(sibh_flow.paired(a, b, 0), [(2.0, 10.0)])
        self.assertEqual(sibh_flow.paired(a, b, 1, 2023), [])

    def test_spearman_with_ties(self):
        self.assertEqual(sibh_flow.ranks([10, 20, 20, 30]), [1.0, 2.5, 2.5, 4.0])
        self.assertAlmostEqual(sibh_flow.spearman([1, 2, 3, 4], [1, 4, 9, 16]), 1.0)
        self.assertAlmostEqual(sibh_flow.spearman([1, 2, 3, 4], [4, 3, 2, 1]), -1.0)

    def test_rainless_days_need_six_dry_days(self):
        rain = {"2024-01-%02d" % d: 0.0 for d in range(1, 11)}
        rain["2024-01-04"] = 5.0
        self.assertEqual(sorted(sibh_flow.rainless_days(rain)), ["2024-01-10"])

    def test_noise_stats_smooth_recession_vs_noisy(self):
        days = ["2024-01-%02d" % d for d in range(1, 31)]
        smooth = {d: 10.0 * 0.95 ** i for i, d in enumerate(days)}
        s = sibh_flow.noise_stats(smooth, set(days[1:]))
        self.assertEqual(s["rises"], 0.0)
        noisy = {d: 5.0 + (0.5 if i % 2 else -0.5) for i, d in enumerate(days)}
        n = sibh_flow.noise_stats(noisy, set(days[1:]))
        self.assertAlmostEqual(n["rises"], 0.5, delta=0.05)
        self.assertLess(n["r1"], -0.9)
        self.assertAlmostEqual(n["noise"], 1.0, places=6)  # alternating +-1 changes: covariance -1

    def test_shortfall_level_test_groups_by_year_and_release(self):
        level, release, gauge = {}, {}, {}
        for i in range(20):
            d = (dt.date(2022, 1, 1) + dt.timedelta(days=i)).isoformat()
            release[d] = 2.0
            short = i % 2 == 0
            gauge[d] = 1.0 if short else 2.2       # 1.0 is more than 0.5 below the release
            level[d] = 0.90 if short else 1.00     # river 10 cm lower on short days
        for i in range(10):                         # another release value, for the scale
            d = (dt.date(2022, 3, 1) + dt.timedelta(days=i)).isoformat()
            release[d], gauge[d], level[d] = 2.5, 2.7, 1.04
        t = sibh_flow.shortfall_level_test(level, release, gauge)
        self.assertEqual((t["n"], t["groups"], t["short_days"], t["groups_lower"]), (30, 1, 10, 1))
        self.assertAlmostEqual(t["diff_m"], -0.10)
        self.assertAlmostEqual(t["step_m"], 1.04 - 0.95)  # median level at 2.0 (0.95) to 2.5 (1.04)
        # short days in one year are never set against other days of another year
        level, release, gauge = {}, {}, {}
        for year, short in ((2022, False), (2023, True)):
            for i in range(10):
                d = dt.date(year, 1, 1 + i).isoformat()
                release[d], gauge[d], level[d] = 2.0, (1.0 if short else 2.2), (0.9 if short else 1.0)
        self.assertEqual(sibh_flow.shortfall_level_test(level, release, gauge)["groups"], 0)

    def test_storage_change_from_previous_day(self):
        sar = {"2024-01-01": {"hm3": 10.0}, "2024-01-02": {"hm3": 10.864}, "2024-01-04": {"hm3": 11.0}}
        ds = sibh_flow.storage_change(sar)
        self.assertEqual(list(ds), ["2024-01-02"])  # no previous day for the others
        self.assertAlmostEqual(ds["2024-01-02"], 10.0, places=2)  # 0.864 hm3/day = 10 m3/s


class Gr4j(unittest.TestCase):
    def test_unit_hydrographs_sum_to_one(self):
        for x4 in (0.6, 1.7, 4.3):
            o1, o2 = gr4j._ordinates(x4)
            self.assertAlmostEqual(sum(o1), 1.0, places=9)
            self.assertAlmostEqual(sum(o2), 1.0, places=9)

    def test_runoff_nonnegative_and_bounded(self):
        rain = [0, 20, 50, 0, 0, 5, 0, 0, 0, 0] * 30
        pet = [3.0] * len(rain)
        q = gr4j.run(rain, pet, 350.0, 0.0, 90.0, 1.7)
        self.assertEqual(len(q), len(rain))
        self.assertTrue(all(v >= 0 for v in q))
        self.assertLess(sum(q), sum(rain))  # no water created with x2 = 0


class DataInvariants(unittest.TestCase):
    """Checks on the committed data, so a refresh cannot break them silently."""

    def test_processed_series_have_unique_sorted_dates(self):
        names = [n for n in os.listdir(c.PROCESSED) if n.endswith(".csv")
                 and n.startswith(("sar_", "ana_", "sibh_rain_", "sibh_flow_", "forcing_"))]
        self.assertTrue(names)
        for n in names:
            dates = [r["date"] for r in c.read_csv(os.path.join(c.PROCESSED, n))]
            self.assertEqual(dates, sorted(set(dates)), n)

    def test_viewer_file_is_consistent_and_shows_nothing_modelled(self):
        path = os.path.join(ROOT, "web", "public", "data", "timeseries.json")
        with open(path, encoding="utf-8") as f:
            ts = json.load(f)
        n = len(ts["dates"])
        self.assertGreater(n, 10000)
        for k, v in ts["system"].items():
            self.assertEqual(len(v), n, "system." + k)
        for name, r in ts["reservoirs"].items():
            for k in ("level", "pct", "hm3", "inflow", "release"):
                self.assertEqual(len(r[k]), n, name + "." + k)
        for code, g in ts["gauges"].items():
            self.assertEqual(len(g["flow"]), n, code)
        # The pilot's central rule: a modelled series reaches the viewer only if accepted.
        for name, m in ts.get("model", {}).items():
            if not m.get("accepted"):
                self.assertNotIn("sim", m, name)

    def test_storage_never_below_documented_minimum(self):
        with open(os.path.join(ROOT, "web", "public", "data", "timeseries.json"), encoding="utf-8") as f:
            pct = [p for p in json.load(f)["system"]["pct"] if p is not None]
        self.assertAlmostEqual(min(pct), -23.3, delta=0.1)  # 2 Feb 2015, the 2014-15 crisis low
        self.assertTrue(all(not math.isnan(p) for p in pct))


if __name__ == "__main__":
    unittest.main()
