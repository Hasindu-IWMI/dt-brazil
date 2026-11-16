"""Download daily Cantareira reservoir records from ANA's SAR (public, no login).

Source: https://www.ana.gov.br/sar0/MedicaoCantareira
Variables per reservoir and day: level (m), useful volume (hm3, %),
inflow (m3/s) and downstream release (m3/s). ANA notes that the release
EXCLUDES transfers through the tunnels.

The service is slow and times out intermittently, so the fetch is resumable:
each reservoir-year is cached as raw HTML and skipped on the next run.

Usage: python fetch_sar_cantareira.py [first_year] [last_year] [reservoir_code]
"""
import datetime as dt
import html
import os
import re
import sys
import urllib.parse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # isolated mode drops the script folder
import common as c  # noqa: E402

BASE = "https://www.ana.gov.br/sar0/MedicaoCantareira"
RAW_DIR = os.path.join(c.RAW, "sar_cantareira")


def fetch_window(code, start, end):
    q = urllib.parse.urlencode({
        "dropDownListReservatorios": code,
        "dataInicial": start.strftime("%d/%m/%Y"),
        "dataFinal": end.strftime("%d/%m/%Y"),
        "button": "Buscar",
    })
    url = BASE + "?" + q
    data = c.http_get(url, timeout=150, retries=6, backoff=15)
    return url, data


def parse_rows(page_bytes):
    s = page_bytes.decode("utf-8", "replace")
    t = re.search(r"<table.*?</table>", s, flags=re.S)
    if not t:
        return None  # page without a result table
    out = []
    for r in re.findall(r"<tr.*?</tr>", t.group(0), flags=re.S):
        cells = [html.unescape(re.sub(r"<[^>]+>", "", x)).strip()
                 for x in re.findall(r"<td[^>]*>(.*?)</td>", r, flags=re.S)]
        if len(cells) < 8:
            continue
        try:
            d = dt.datetime.strptime(cells[7], "%d/%m/%Y").date()
        except ValueError:
            continue
        out.append((d.isoformat(), c.fnum(cells[2]), c.fnum(cells[3]), c.fnum(cells[4]),
                    c.fnum(cells[5]), c.fnum(cells[6])))
    return out


def main():
    y0 = int(sys.argv[1]) if len(sys.argv) > 1 else 2000
    y1 = int(sys.argv[2]) if len(sys.argv) > 2 else dt.date.today().year
    only = sys.argv[3] if len(sys.argv) > 3 else None  # optional reservoir code
    today = dt.date.today()
    for code, meta in c.RESERVOIRS.items():
        if only and code != only:
            continue
        for year in range(y1, y0 - 1, -1):
            # half-year windows keep each request under the gateway timeout
            for a, b in ((dt.date(year, 1, 1), dt.date(year, 6, 30)),
                         (dt.date(year, 7, 1), dt.date(year, 12, 31))):
                if a > today:
                    continue
                b = min(b, today)
                complete = b < today - dt.timedelta(days=45)
                path = os.path.join(RAW_DIR, "%s_%s_%s.html" % (meta["key"], a.isoformat(), b.isoformat()))
                if os.path.exists(path) and complete:
                    continue
                try:
                    url, data = fetch_window(code, a, b)
                except Exception as e:  # keep going; rerun fills the holes
                    print("FAIL", meta["key"], a, b, e, flush=True)
                    continue
                rows = parse_rows(data)
                if rows is None:
                    print("NO TABLE", meta["key"], a, b, len(data), flush=True)
                    continue
                c.write_bytes(path, data)
                c.append_manifest({"source": "ANA SAR Cantareira", "url": url, "file": os.path.relpath(path, c.ROOT),
                                   "bytes": len(data), "sha256": c.sha256(data), "rows": len(rows)})
                print("ok", meta["key"], a, b, len(rows), "rows", flush=True)


if __name__ == "__main__":
    main()
