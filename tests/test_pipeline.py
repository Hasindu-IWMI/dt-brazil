"""Unit tests for the pipeline's parsing and processing rules (standard library).

Run from the repository root:  python -I -m unittest discover -s tests -v
"""
import datetime as dt
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
import fetch_sibh_rain  # noqa: E402
import forcing  # noqa: E402
import gr4j  # noqa: E402
import process  # noqa: E402
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
        names = [n for n in os.listdir(c.PROCESSED) if n.endswith(".csv") and n.startswith(("sar_", "ana_", "sibh_rain_", "forcing_"))]
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
