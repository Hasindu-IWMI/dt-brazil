"""Download daily conventional series from ANA's public web service (no login).

Source: http://telemetriaws1.ana.gov.br/ServiceANA.asmx  (HidroSerieHistorica)
tipoDados: 1 = stage (cm), 2 = rain (mm), 3 = discharge (m3/s).
Each XML row is one month with daily fields 01..31 and a consistency level
(NivelConsistencia: 1 = raw "bruto", 2 = consolidated "consistido").

Raw XML is cached per station and type; a tidy CSV with one row per day is
written to data/processed. Where a month exists at both levels, the
consolidated one is kept and the level is recorded on every row.

Usage: python fetch_ana_series.py <tipo: 1|2|3> <station> [<station> ...]
"""
import datetime as dt
import os
import re
import sys
import urllib.parse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # isolated mode drops the script folder
import common as c  # noqa: E402

BASE = "http://telemetriaws1.ana.gov.br/ServiceANA.asmx/HidroSerieHistorica"
KIND = {"1": ("stage", "Cota", "cm"), "2": ("rain", "Chuva", "mm"), "3": ("discharge", "Vazao", "m3/s")}


def tag(block, name):
    m = re.search(r"<%s>(.*?)</%s>" % (name, name), block, flags=re.S)
    return m.group(1).strip() if m else ""


def parse(xml_text, prefix):
    """Return {date_iso: (value, level)} keeping the highest consistency level."""
    best = {}
    for block in re.findall(r"<SerieHistorica .*?</SerieHistorica>", xml_text, flags=re.S):
        level = tag(block, "NivelConsistencia")
        stamp = tag(block, "DataHora")[:10]
        try:
            first = dt.datetime.strptime(stamp, "%Y-%m-%d").date()
        except ValueError:
            continue
        for day in range(1, 32):
            try:
                d = dt.date(first.year, first.month, day)
            except ValueError:
                break
            v = c.fnum(tag(block, "%s%02d" % (prefix, day)))
            if v is None:
                continue
            key = d.isoformat()
            if key not in best or level > best[key][1]:
                best[key] = (v, level)
    return best


def main():
    tipo = sys.argv[1]
    kind, prefix, unit = KIND[tipo]
    for station in sys.argv[2:]:
        q = urllib.parse.urlencode({"codEstacao": station, "dataInicio": "01/01/1900",
                                    "dataFim": dt.date.today().strftime("%d/%m/%Y"),
                                    "tipoDados": tipo, "nivelConsistencia": ""})
        url = BASE + "?" + q
        raw_path = os.path.join(c.RAW, "ana_series", "%s_%s.xml" % (station, kind))
        try:
            data = c.http_get(url, timeout=300, retries=4, backoff=20)
        except Exception as e:
            print("FAIL", station, kind, e, flush=True)
            continue
        c.write_bytes(raw_path, data)
        series = parse(data.decode("utf-8", "replace"), prefix)
        c.append_manifest({"source": "ANA HidroSerieHistorica", "url": url, "file": os.path.relpath(raw_path, c.ROOT),
                           "bytes": len(data), "sha256": c.sha256(data), "days": len(series)})
        rows = [(d, series[d][0], series[d][1]) for d in sorted(series)]
        out = os.path.join(c.PROCESSED, "ana_%s_%s.csv" % (kind, station))
        c.write_csv(out, ["date", "%s_%s" % (kind, unit.replace("/", "")), "consistency_level"], rows)
        span = (rows[0][0], rows[-1][0]) if rows else ("-", "-")
        print("ok", station, kind, len(rows), "days", span[0], span[1], flush=True)


if __name__ == "__main__":
    main()
