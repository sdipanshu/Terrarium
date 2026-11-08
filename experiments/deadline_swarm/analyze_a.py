"""Experiment A (and N1) primary analysis: A1-A3 with Holm, per model, and infrastructure sensitivity checks.

python analyze_a.py outputs/expA [--exclude episodes.json] [--json out.json]
--exclude: JSON list of episode names to drop (e.g. standby-overlapping episodes) for a sensitivity run.
"""
import argparse
import json
from pathlib import Path

from analyze import boot_p, episode_dirs, episode_measures, holm, paired_diff

TESTS = [  # name, arm a, arm b, measure
    ("A1", "announced_tight", "announced_generous", "pre_method_any"),
    ("A2", "announced_tight", "unannounced_tight", "pre_method_any"),
    ("A3", "announced_tight", "unannounced_tight", "p2_on_time"),
]


def run(rows):
    out, ps = {}, []
    for name, a, b, key in TESTS:
        r = paired_diff(rows, a, b, key)
        if r:
            p = boot_p(r["boots"], 0, "greater")
            out[name] = {"n": r["n"], "mean": r["mean"], "ci": r["ci"], "p": p, "supported": r["ci"][0] > 0}
            ps.append((name, p))
    for (name, _), adj in zip(ps, holm([p for _, p in ps])):
        out[name]["holm_p"] = adj
    return out


def arm_means(rows, key):
    arms = sorted({r["arm"] for r in rows})
    return {a: sum(r[key] for r in rows if r["arm"] == a) / max(1, sum(r["arm"] == a for r in rows)) for a in arms}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root")
    ap.add_argument("--exclude")
    ap.add_argument("--json")
    args = ap.parse_args()
    rows = [episode_measures(d) for d in episode_dirs(args.root)]
    if args.exclude:
        drop = set(json.loads(Path(args.exclude).read_text()))
        rows = [r for r in rows if r["episode"] not in drop]
    res = {"n_episodes": len(rows), "pooled": run(rows), "per_model": {},
           "arm_means": {k: arm_means(rows, k) for k in ("pre_method_any", "pre_method_msgs", "p2_on_time",
                                                          "p2_score", "relays", "used", "infra_errors")}}
    for m in sorted({r["model"] for r in rows}):
        sub = [r for r in rows if r["model"] == m]
        res["per_model"][m] = {"tests": run(sub), "arm_means": {k: arm_means(sub, k)
                                                                for k in ("pre_method_any", "p2_on_time")}}
    print(json.dumps(res, indent=1))
    if args.json:
        Path(args.json).write_text(json.dumps({"summary": res, "rows": rows}, indent=1))


if __name__ == "__main__":
    main()
