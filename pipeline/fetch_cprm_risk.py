"""Download the Geological Survey of Brazil's 2012 flood and landslide risk sectors for Atibaia.

Source: RIGEO (rigeo.sgb.gov.br), record doc/20208, "Ação emergencial para
delimitação de áreas em alto e muito alto risco a inundações e movimentos de
massa: Atibaia, São Paulo", CPRM, November 2012 (Theodorovicz, A.; Pedrazzi,
A. de C.). Only the GIS file (sig_atibaia_sp_risco.zip, about 50 KB) is
fetched; the 26 MB report with its map plates is not.

Stored exactly as received in data/raw/cprm/ and logged in the manifest.
Then: python cprm_risk.py

Usage: python fetch_cprm_risk.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # isolated mode drops the script folder
import common as c  # noqa: E402

URL = "https://rigeo.sgb.gov.br/server/api/core/bitstreams/5a4cfb24-2307-43a5-a294-033383e40d49/content"
SOURCE = "CPRM / Serviço Geológico do Brasil, RIGEO doc/20208 (Atibaia risk sectors, 2012)"
OUT = os.path.join(c.RAW, "cprm", "sig_atibaia_sp_risco.zip")


def main():
    if os.path.exists(OUT):
        print("already on disk:", os.path.relpath(OUT, c.ROOT))
        return
    data = c.http_get(URL, timeout=120, retries=3, backoff=10)
    if data[:2] != b"PK":
        raise SystemExit("not a ZIP file (%d bytes)" % len(data))
    c.write_bytes(OUT, data)
    c.append_manifest({"source": SOURCE, "url": URL, "file": os.path.relpath(OUT, c.ROOT).replace("\\", "/"),
                       "bytes": len(data), "sha256": c.sha256(data)})
    print("stored", os.path.relpath(OUT, c.ROOT), len(data), "bytes")


if __name__ == "__main__":
    main()
