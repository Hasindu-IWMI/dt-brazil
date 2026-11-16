"""Run the pipeline in order, from downloads to the data the viewer reads.

Usage (from the repository root):
  python -I pipeline/run_all.py             rebuild everything from data on disk
  python -I pipeline/run_all.py --fetch     resumable downloads first, then rebuild
  python -I pipeline/run_all.py --refresh   as --fetch, and re-fetch the most recent records
  add --scene to also re-fetch map outlines from OpenStreetMap (needs Node)

Steps, each in its own process. A failed download is reported and the run
continues with what is on disk; a failed build step stops the run.

  fetch  fetch_sar_cantareira.py 1982 <this year>   reservoirs (resumable)
  fetch  fetch_ana_series.py 3 <river gauges>       daily discharge
  fetch  fetch_ana_series.py 2 <rain gauges>        daily rain, ANA
  fetch  fetch_sibh_rain.py [--refresh]             hourly rain, SIBH telemetric gauges
  build  process.py      reservoir and gauge tables, data quality report, viewer JSON
  build  sibh_rain.py    daily series from the telemetric gauges
  build  rain_alignment.py  day labelling of each ANA rain gauge (report only)
  build  audit_rain.py   neighbour audit of every rain gauge
  build  forcing.py      catchment rain and evapotranspiration

Deliberately NOT run: delineate.py and the terrain tools (one-off; their
inputs are fixed), and the frozen analyses model.py, model_run3.py,
model_run4.py and investigate_runoff.py. Their reports document experiments
already made; re-running them on newer inputs would silently rewrite that
record. A new experiment needs its own design, fixed before it is run.

Each step's output goes to the console and to data/logs/run_all_<step>.log.
"""
import datetime as dt
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)  # isolated mode drops the script folder
import common as c  # noqa: E402
from forcing import RAIN_GAUGES  # noqa: E402

# River gauges fetched for the viewer and the quality report (see README).
DISCHARGE = ["62670000", "62665000", "62662000", "62676000", "62678150",
             "62669900", "62680000", "62690000", "62665100"]


def steps(fetch, refresh, scene):
    py = [sys.executable, "-I"]
    s = []
    if fetch or refresh:
        s += [("fetch", "sar", py + [os.path.join(HERE, "fetch_sar_cantareira.py"), "1982", str(dt.date.today().year)]),
              ("fetch", "ana_discharge", py + [os.path.join(HERE, "fetch_ana_series.py"), "3"] + DISCHARGE),
              ("fetch", "ana_rain", py + [os.path.join(HERE, "fetch_ana_series.py"), "2"] + list(RAIN_GAUGES)),
              ("fetch", "sibh_rain", py + [os.path.join(HERE, "fetch_sibh_rain.py")] + (["--refresh"] if refresh else []))]
    s += [("build", "process", py + [os.path.join(HERE, "process.py")]),
          ("build", "sibh_rain", py + [os.path.join(HERE, "sibh_rain.py")]),
          ("build", "rain_alignment", py + [os.path.join(HERE, "rain_alignment.py")]),
          ("build", "audit_rain", py + [os.path.join(HERE, "audit_rain.py")]),
          ("build", "forcing", py + [os.path.join(HERE, "forcing.py")])]
    if scene:
        npm = shutil.which("npm") or "npm"
        s.append(("build", "scene", [npm, "--prefix", os.path.join(c.ROOT, "web"), "run", "scene"]))
    return s


def main():
    args = set(sys.argv[1:])
    unknown = args - {"--fetch", "--refresh", "--scene"}
    if unknown:
        sys.exit("unknown option(s): %s\n%s" % (" ".join(sorted(unknown)), __doc__))
    logs = c.ensure_dir(os.path.join(c.ROOT, "data", "logs"))
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    summary = []
    for kind, name, cmd in steps("--fetch" in args, "--refresh" in args, "--scene" in args):
        print("\n=== %s: %s" % (kind, name), flush=True)
        log_path = os.path.join(logs, "run_all_%s.log" % name)
        with open(log_path, "w", encoding="utf-8") as log:
            p = subprocess.Popen(cmd, cwd=c.ROOT, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                 text=True, encoding="utf-8", errors="replace")
            for line in p.stdout:
                sys.stdout.write(line)
                log.write(line)
            p.wait()
        failed_lines = 0
        with open(log_path, encoding="utf-8") as log:
            failed_lines = sum(1 for line in log if line.startswith("FAIL"))
        summary.append((kind, name, p.returncode, failed_lines))
        if p.returncode != 0 and kind == "build":
            break
    print("\n=== summary")
    for kind, name, code, failed in summary:
        state = "ok" if code == 0 else "exit %d" % code
        print("%-5s %-14s %s%s" % (kind, name, state, ", %d FAIL lines (re-run to fill)" % failed if failed else ""))
    if any(code != 0 and kind == "build" for kind, _, code, _ in summary):
        sys.exit(1)


if __name__ == "__main__":
    main()
