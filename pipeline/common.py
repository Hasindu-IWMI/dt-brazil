"""Shared helpers for the Upper Atibaia pipeline. Standard library only."""
import csv
import datetime as dt
import hashlib
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "data", "raw")
PROCESSED = os.path.join(ROOT, "data", "processed")
USER_AGENT = "upper-atibaia-pipeline/0.1 (research; stdlib urllib)"

# Reservoirs of the Cantareira system as coded by ANA's SAR (Cantareira module).
# Useful volumes (hm3) are the operating volumes published in ANA's monthly
# Cantareira bulletin (Nov 2023); they are used only for cross-checks.
RESERVOIRS = {
    "29001": {"key": "jaguari_jacarei", "name": "Jaguari-Jacareí", "useful_hm3": 808.04, "basin": "PCJ (Jaguari)"},
    "29002": {"key": "cachoeira", "name": "Cachoeira", "useful_hm3": 69.65, "basin": "PCJ (Atibaia)"},
    "29003": {"key": "atibainha", "name": "Atibainha", "useful_hm3": 96.25, "basin": "PCJ (Atibaia)"},
    "29004": {"key": "paiva_castro", "name": "Paiva Castro", "useful_hm3": 7.61, "basin": "Alto Tietê (Juqueri)"},
}

RESERVOIRS_BY_KEY = {m["key"]: m for m in RESERVOIRS.values()}

# River gauges on the Atibaia, from ANA's HidroInventario (queried 2026-11-14).
# area_km2, coordinates and record start are the inventory's own values.
GAUGES = {
    "62669900": {"name": "Atibaia (SP Águas, telemetric)", "area_km2": 1143, "lat": -23.1053, "lon": -46.5558, "role": "control point: Rio Atibaia em Atibaia"},
    "62670000": {"name": "Atibaia (ANA / SGB)", "area_km2": 1140, "lat": -23.1056, "lon": -46.5569, "role": "long conventional record at the control point"},
    "62676000": {"name": "Bairro da Ponte", "area_km2": 1930, "lat": -22.9831, "lon": -46.8294, "role": "Itatiba, between control points"},
    "62678150": {"name": "Captação de Valinhos", "area_km2": 2152, "lat": -22.9283, "lon": -46.9392, "role": "control point: Valinhos"},
    "62680000": {"name": "Desembargador Furtado", "area_km2": 2490, "lat": -22.7694, "lon": -46.9894, "role": "downstream check"},
    "62690000": {"name": "Acima de Paulínia", "area_km2": 2730, "lat": -22.7444, "lon": -47.1361, "role": "downstream check"},
}

# Operating bands of the Cantareira system (Joint Resolution ANA/DAEE 925/2017),
# as tabulated in the Comitês PCJ status report 2020. Lower bound of stored
# volume (% of useful volume, whole system) and the withdrawal limit (m3/s).
OPERATING_BANDS = [
    {"band": 1, "name": "Normal", "min_pct": 60.0, "max_withdrawal_m3s": 33.0},
    {"band": 2, "name": "Atenção", "min_pct": 40.0, "max_withdrawal_m3s": 31.0},
    {"band": 3, "name": "Alerta", "min_pct": 30.0, "max_withdrawal_m3s": 27.0},
    {"band": 4, "name": "Restrição", "min_pct": 20.0, "max_withdrawal_m3s": 23.0},
    {"band": 5, "name": "Especial", "min_pct": -1e9, "max_withdrawal_m3s": 15.5},
]


def ensure_dir(path):
    os.makedirs(path, exist_ok=True)
    return path


def http_get(url, timeout=120, retries=5, backoff=20):
    """GET with retries. Returns bytes, or raises the last error."""
    last = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read()
        except (urllib.error.URLError, TimeoutError, ConnectionError, OSError) as e:
            last = e
            time.sleep(backoff * (attempt + 1))
    raise last


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def write_bytes(path, data):
    ensure_dir(os.path.dirname(path))
    with open(path, "wb") as f:
        f.write(data)


def append_manifest(entry):
    """Record every raw download: url, file, bytes, checksum, retrieval time."""
    ensure_dir(RAW)
    entry = dict(entry)
    entry["retrieved_utc"] = dt.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    with open(os.path.join(RAW, "manifest.jsonl"), "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def write_csv(path, header, rows):
    ensure_dir(os.path.dirname(path))
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)


def read_csv(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def fnum(text):
    """Parse a number that may use a decimal comma; '' or junk -> None."""
    if text is None:
        return None
    t = str(text).strip().replace("\xa0", "")
    if not t or t in {"-", "--"}:
        return None
    if "," in t:
        t = t.replace(".", "").replace(",", ".")
    try:
        return float(t)
    except ValueError:
        return None
