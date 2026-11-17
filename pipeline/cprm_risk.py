"""The Geological Survey of Brazil's 2012 risk sectors for Atibaia, as a small JSON for the viewer.

Reads data/raw/cprm/sig_atibaia_sp_risco.zip (fetch_cprm_risk.py): the shapefile
Shape/SP_AT_SR_CPRM_atualizado (the updated version of the same 12 sectors;
WGS84 longitude/latitude, PolygonZ) and its attribute table. Copies the
geometry (Z dropped) and the attributes as published; nothing is derived.

Each sector: number, place, type (Inundação = river flood, Enxurrada = flash
flood, Deslizamento = landslide), risk grade (Alto, Muito Alto), homes and
people counted in the sector, survey date, the description and the suggested
interventions, all in Portuguese as published.

Output: data/processed/cprm_risk_atibaia.json

Usage: python cprm_risk.py
"""
import io
import json
import os
import struct
import sys
import zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # isolated mode drops the script folder
import common as c  # noqa: E402

SRC = os.path.join(c.RAW, "cprm", "sig_atibaia_sp_risco.zip")
LAYER = "Shape/SP_AT_SR_CPRM_atualizado"
OUT = os.path.join(c.PROCESSED, "cprm_risk_atibaia.json")


def read_dbf(b):
    nrec, hlen, rlen = struct.unpack("<IHH", b[4:12])
    fields = []
    for k in range(32, hlen - 1, 32):
        name = b[k:k + 11].split(b"\0")[0].decode("latin-1")
        fields.append((name, chr(b[k + 11]), b[k + 16]))
    rows, off = [], hlen
    for _ in range(nrec):
        rec, pos, row = b[off + 1: off + rlen], 0, {}
        off += rlen
        for name, typ, ln in fields:
            raw = rec[pos:pos + ln].decode("latin-1").strip()
            pos += ln
            row[name] = (float(raw) if raw else None) if typ == "N" else raw
        rows.append(row)
    return rows


def read_polygons(b):
    """Rings (lon, lat) of each record of a Polygon / PolygonZ / PolygonM shapefile."""
    out, off = [], 100
    while off < len(b):
        _, clen = struct.unpack(">ii", b[off:off + 8])
        rec = b[off + 8: off + 8 + clen * 2]
        off += 8 + clen * 2
        stype = struct.unpack("<i", rec[:4])[0]
        if stype not in (5, 15, 25):
            out.append([])
            continue
        nparts, npts = struct.unpack("<ii", rec[36:44])
        parts = list(struct.unpack("<%di" % nparts, rec[44:44 + 4 * nparts])) + [npts]
        p0 = 44 + 4 * nparts
        pts = [struct.unpack("<dd", rec[p0 + 16 * k: p0 + 16 * k + 16]) for k in range(npts)]
        out.append([[[round(x, 6), round(y, 6)] for x, y in pts[parts[k]:parts[k + 1]]] for k in range(nparts)])
    return out


def main():
    z = zipfile.ZipFile(SRC)
    rows = read_dbf(z.read(LAYER + ".dbf"))
    geoms = read_polygons(z.read(LAYER + ".shp"))
    prj = z.read(LAYER + ".prj").decode("latin-1")
    if "WGS_1984" not in prj or "GEOGCS" not in prj:
        raise SystemExit("unexpected coordinate system: %s" % prj[:80])
    sectors = []
    for r, g in zip(rows, geoms):
        d = r.get("DATA_SETOR") or ""
        sectors.append({
            "id": r.get("NUM_SETOR"), "place": r.get("LOCAL"), "type": r.get("TIPOLOGIA"), "grade": r.get("GRAU_RISCO"),
            "homes": int(r["NUM_MORAD"]) if r.get("NUM_MORAD") is not None else None,
            "people": int(r["NUM_PESS"]) if r.get("NUM_PESS") is not None else None,
            "surveyed": "%s-%s-%s" % (d[:4], d[4:6], d[6:8]) if len(d) == 8 else d,
            "description": r.get("DESCRICAO"), "interventions": r.get("SUG_INTERV"), "rings": g})
    out = {"source": "Serviço Geológico do Brasil (CPRM), 'Ação emergencial para delimitação de áreas em alto e muito alto "
                     "risco a inundações e movimentos de massa: Atibaia, São Paulo', November 2012 (Theodorovicz, A.; "
                     "Pedrazzi, A. de C.). RIGEO doc/20208, file sig_atibaia_sp_risco.zip, layer SP_AT_SR_CPRM_atualizado.",
           "meaning": "Mapped sectors of high and very high risk, surveyed in November-December 2012. Official mapped "
                      "areas, not flood extents, and not updated since.",
           "crs": "WGS84 longitude/latitude", "sectors": sectors}
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    kinds = {}
    for s in sectors:
        kinds.setdefault(s["type"], []).append(s)
    for k, v in kinds.items():
        print("%-13s %d sectors, %d homes, %d people" % (k, len(v), sum(s["homes"] or 0 for s in v), sum(s["people"] or 0 for s in v)))
    print("written:", os.path.relpath(OUT, c.ROOT))


if __name__ == "__main__":
    main()
