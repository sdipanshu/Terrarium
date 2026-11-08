"""List episodes whose wall-clock span overlaps a Modern Standby window.

python standby_check.py outputs/standby_windows.txt outputs out.json
standby_windows.txt: lines "ISO-time 506|507" exported from the Windows System log (Kernel-Power)."""
import json, os, sys
from datetime import datetime
from pathlib import Path

lines = [l.split() for l in Path(sys.argv[1]).read_text().split("\n") if l.strip()]
wins, start = [], None
for ts, eid in lines:
    t = datetime.fromisoformat(ts).timestamp()
    if eid == "506":
        start = t
    elif start is not None:
        wins.append((start, t)); start = None
root = Path(sys.argv[2])
rows = []
for ev in sorted(root.glob("*/*/events.jsonl")) + sorted(root.glob("*/failed_infra/*/events.jsonl")):
    ep = ev.parent
    res = ep / "results.json"
    t0 = os.stat(ev).st_ctime
    t1 = os.stat(res).st_mtime if res.exists() else os.stat(ev).st_mtime
    ov = sum(max(0, min(t1, b) - max(t0, a)) for a, b in wins)
    ts = [json.loads(l)["t"] for l in ev.read_text(encoding="utf-8").splitlines() if l.strip()]
    gap = max((b - a for a, b in zip(ts, ts[1:])), default=0)
    rows.append((str(ep.relative_to(root)), datetime.fromtimestamp(t0).strftime("%H:%M"),
                 datetime.fromtimestamp(t1).strftime("%H:%M"), round(ov), round(gap), res.exists()))
json.dump(rows, open(sys.argv[3], "w"), indent=0)
hit = [r for r in rows if r[3] > 0]
print(f"episodes scanned {len(rows)}; overlapping standby {len(hit)}")
by = {}
for r in hit:
    by.setdefault(r[0].split("/")[0].split("\\")[0], []).append(r)
for k, v in sorted(by.items()):
    print(f"== {k}: {len(v)}")
    for r in v:
        print(f"   {r[0]}  {r[1]}-{r[2]}  overlap={r[3]}s maxgap={r[4]}s results={r[5]}")
big = [r for r in rows if r[3] == 0 and r[4] > 200]
print(f"non-overlapping episodes with an internal event gap >200s: {len(big)}")
for r in big:
    print("  ", r)
