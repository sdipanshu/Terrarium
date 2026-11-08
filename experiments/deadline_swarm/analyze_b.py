"""Experiment B analysis (PREREG_B.md): B1 tight on-time by layout, B2 initiator of the first useful exchange.

python analyze_b.py outputs/expB [--json out.json]
"""
import argparse
import json
import random
from collections import defaultdict
from pathlib import Path

from analyze import boot_p, episode_dirs, holm, load, mentioned_classes, paired_diff

N_BOOT = 10000


def b_measures(ep_dir):
    cfg, gt, res, ev = load(ep_dir)
    dl = json.loads((ep_dir / "deadlines.json").read_text())
    release = cfg["prep_seconds"]
    names = gt["names"]
    tight = {n for n in names if res[n]["tight"]}
    p2c = {n: gt["p2"][n]["class"] for n in names}
    sends = sorted((e for e in ev if e["action"] == "send"), key=lambda e: (e["t"], e["msg_id"]))
    deliver = {e["msg_id"]: e["t"] for e in ev if e["action"] == "deliver"}
    useful = [s for s in sends
              if any(p2c[n] == c for c in mentioned_classes(s.get("text", "")) for n in names if n != s["actor"])]
    first = None
    if useful:
        m = useful[0]
        edge = {m["actor"], m["recipient"]}
        opener = next(s for s in sends if {s["actor"], s["recipient"]} == edge and
                      (s["t"], s["msg_id"]) <= (m["t"], m["msg_id"]))
        first = {"msg_id": m["msg_id"], "t": m["t"], "sender": m["actor"], "recipient": m["recipient"],
                 "initiator": opener["actor"], "initiator_tight": opener["actor"] in tight,
                 "kind": "volunteer" if opener["actor"] == m["actor"] else "request"}
    # exploratory: a message carrying the tight worker's own P2 class became visible before its deadline
    helped = 0
    for n in tight:
        due = release + res[n]["deadline"]
        if any(s["recipient"] == n and s["msg_id"] in deliver and deliver[s["msg_id"]] <= due and
               p2c[n] in mentioned_classes(s.get("text", "")) for s in sends):
            helped += 1
    on = lambda group: sum(res[n]["p2_on_time"] for n in group) / len(group)
    score = lambda group: sum(res[n]["p2_score"] for n in group) / len(group)
    return {"episode": ep_dir.name, "model": cfg["model"], "seed": cfg["seed"], "arm": dl["layout"],
            "tight_on_time": on(tight), "generous_on_time": on(set(names) - tight),
            "tight_p2_score": score(tight), "generous_p2_score": score(set(names) - tight),
            "tight_helped_in_time": helped / len(tight), "useful_msgs": len(useful), "first": first,
            "infra_errors": sum(e["action"] == "infra_error" for e in ev)}


def share_test(rows):
    """Share of first useful exchanges initiated by a tight worker; bootstrap over (model, seed) units, vs 0.5."""
    units = defaultdict(list)
    for r in rows:
        if r["first"]:
            units[(r["model"], r["seed"])].append(int(r["first"]["initiator_tight"]))
    if not units:
        return None
    keys = list(units)
    flat = [v for k in keys for v in units[k]]
    rng = random.Random(0)
    boots = []
    for _ in range(N_BOOT):
        s = [v for k in (rng.choice(keys) for _ in keys) for v in units[k]]
        boots.append(sum(s) / len(s))
    boots.sort()
    return {"n": len(flat), "share": sum(flat) / len(flat),
            "ci": (boots[int(.025 * N_BOOT)], boots[int(.975 * N_BOOT) - 1]), "p": boot_p(boots, 0.5, "two")}


def fmt(r):
    return f"{r['mean']:+.3f} [{r['ci'][0]:+.3f}, {r['ci'][1]:+.3f}] n={r['n']}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root")
    ap.add_argument("--json")
    args = ap.parse_args()
    rows = [b_measures(d) for d in episode_dirs(args.root)]
    models = sorted({r["model"] for r in rows})
    out = {"n_episodes": len(rows), "per_model": {}}

    b1 = paired_diff(rows, "alternating", "clustered", "tight_on_time")
    b2 = share_test(rows)
    tests = [("B1", b1, boot_p(b1["boots"], 0, "greater") if b1 else None), ("B2", b2, b2["p"] if b2 else None)]
    live = [t for t in tests if t[2] is not None]
    for (name, _, _), adj in zip(live, holm([t[2] for t in live])):
        out[name + "_holm_p"] = adj
    if b1:
        out["B1"] = {k: v for k, v in b1.items() if k != "boots"} | {"p": tests[0][2],
                                                                     "supported": b1["ci"][0] > 0}
        print(f"B1 tight on-time, alternating - clustered: {fmt(b1)}  p={tests[0][2]:.4f} holm={out['B1_holm_p']:.4f}")
    if b2:
        out["B2"] = b2
        print(f"B2 share initiated by tight: {b2['share']:.3f} [{b2['ci'][0]:.3f}, {b2['ci'][1]:.3f}] "
              f"n={b2['n']} p={b2['p']:.4f} holm={out['B2_holm_p']:.4f}")
        for lay in ("alternating", "clustered"):
            s = share_test([r for r in rows if r["arm"] == lay])
            out["B2_" + lay] = s
            if s:
                print(f"   {lay}: {s['share']:.3f} [{s['ci'][0]:.3f}, {s['ci'][1]:.3f}] n={s['n']}")
    else:
        print("B2: not estimable (no useful exchange in any episode)")

    print("\nExploratory (paired alternating - clustered):")
    for key in ("generous_on_time", "tight_p2_score", "generous_p2_score", "tight_helped_in_time", "useful_msgs"):
        r = paired_diff(rows, "alternating", "clustered", key)
        if r:
            out["explore_" + key] = {k: v for k, v in r.items() if k != "boots"}
            print(f"  {key}: {fmt(r)}")
    kinds = defaultdict(int)
    for r in rows:
        if r["first"]:
            kinds[(r["arm"], r["first"]["kind"])] += 1
    out["first_exchange_kinds"] = {f"{a}/{k}": n for (a, k), n in sorted(kinds.items())}
    print("  first exchange kinds:", out["first_exchange_kinds"])

    print("\nPer model:")
    for m in models:
        sub = [r for r in rows if r["model"] == m]
        r1, r2 = paired_diff(sub, "alternating", "clustered", "tight_on_time"), share_test(sub)
        out["per_model"][m] = {"B1": {k: v for k, v in r1.items() if k != "boots"} if r1 else None, "B2": r2}
        print(f"  {m}: B1 {fmt(r1) if r1 else 'n/a'};  B2 "
              + (f"{r2['share']:.3f} n={r2['n']}" if r2 else "n/a"))
    if args.json:
        Path(args.json).write_text(json.dumps({"summary": out, "rows": rows}, indent=1))


if __name__ == "__main__":
    main()
