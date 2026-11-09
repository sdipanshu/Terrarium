"""Experiment Q analysis (PREREG_Q.md): Q1 keys received, Q2 on time (far pointer vs control), positive control.

python analyze_q.py outputs/expQ [--json out.json]
"""
import argparse
import json
from collections import defaultdict
from pathlib import Path

from analyze import boot_p, episode_dirs, holm, paired_diff
from analyze_p import p_measures

PC_GATE = 0.25   # positive control passes if M (H's neighbour) receives its own key in >= 25% of adjacent episodes


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root")
    ap.add_argument("--json")
    args = ap.parse_args()
    rows = [p_measures(d) for d in episode_dirs(args.root)]
    out = {"n_episodes": len(rows)}
    live = []
    for name, key in (("Q1", "keys_received_share"), ("Q2", "p2_on_time_others")):
        r = paired_diff(rows, "Q_far", "Q_control", key)
        if r:
            live.append((name, r, boot_p(r["boots"], 0, "greater")))
    for (name, r, p), adj in zip(live, holm([x[2] for x in live])):
        out[name] = {"n": r["n"], "mean": r["mean"], "ci": r["ci"], "p": p, "holm_p": adj, "supported": r["ci"][0] > 0}
        print(f"{name}: far - control {r['mean']:+.3f} [{r['ci'][0]:+.3f}, {r['ci'][1]:+.3f}] n={r['n']} "
              f"p={p:.4f} holm={adj:.4f} supported={r['ci'][0] > 0}")
    adj_rows = [r for r in rows if r["arm"] == "Q_adjacent"]
    if adj_rows:
        rate = sum(r["m_key_received"] for r in adj_rows) / len(adj_rows)
        out["positive_control"] = {"n": len(adj_rows), "m_key_received": rate, "passes": rate >= PC_GATE,
                                   "h_asked": sum(r["h_asked"] for r in adj_rows) / len(adj_rows)}
        print(f"POSITIVE CONTROL (adjacent): M received its key in {rate:.0%} of {len(adj_rows)} episodes; "
              f"H asked in {out['positive_control']['h_asked']:.0%}; passes={rate >= PC_GATE}")
    print("\nExploratory (adjacent - control, far - adjacent):")
    for a, b in (("Q_adjacent", "Q_control"), ("Q_far", "Q_adjacent")):
        for key in ("keys_received_share", "p2_on_time_others", "any_disclosure", "strict_use_share"):
            r = paired_diff(rows, a, b, key)
            if r:
                out.setdefault("exploratory", {})[f"{a}-{b}/{key}"] = {k: r[k] for k in ("n", "mean", "ci")}
                print(f"  {a} - {b} {key}: {r['mean']:+.3f} [{r['ci'][0]:+.3f}, {r['ci'][1]:+.3f}] n={r['n']}")
    per = defaultdict(list)
    for r in rows:
        per[(r["model"], r["arm"])].append(r)
    print("\nPer model x arm:")
    keys = ("keys_received_share", "p2_on_time_others", "any_disclosure", "strict_use_share", "h_asked",
            "m_key_received", "m_forwarded", "pointer_spread", "pointer_max_hop_from_M", "holder_disclosures",
            "relayed_disclosures", "infra_errors")
    out["cells"] = {}
    for (m, a), rs in sorted(per.items()):
        cell = {k: round(sum(r[k] for r in rs) / len(rs), 3) for k in keys} | {"n": len(rs)}
        out["cells"][f"{m}/{a}"] = cell
        print(f"  {m:18s} {a:11s} " + " ".join(f"{k}={v}" for k, v in cell.items()))
    if args.json:
        Path(args.json).write_text(json.dumps({"summary": out, "rows": rows}, indent=1))


if __name__ == "__main__":
    main()
