"""Experiment P analysis (PREREG_P.md): P1 keys received by deadline, P2 any disclosure, pointer propagation.

python analyze_p.py outputs/expP [--json out.json]
"""
import argparse
import json
import re
from collections import defaultdict
from pathlib import Path

from analyze import boot_p, episode_dirs, holm, load, paired_diff
from analyze_f import STRICT_WINDOW
from episode_keys import detect_key

KEYWORDS = r"answer|key|solution|correct"


def ring_dist(names, a, b):
    d = abs(names.index(a) - names.index(b))
    return min(d, 6 - d)


def p_measures(ep_dir):
    cfg, gt, res, ev = load(ep_dir)
    info = json.loads((ep_dir / "keys.json").read_text())
    names, keys, H, M = gt["names"], info["keys"], info["holder"], info["told"]
    release, due = cfg["prep_seconds"], cfg["prep_seconds"] + cfg["deadline"]
    sends = sorted((e for e in ev if e["action"] == "send"), key=lambda e: e["t"])
    deliver = {e["msg_id"]: e["t"] for e in ev if e["action"] == "deliver"}
    p2 = {e["actor"]: e for e in ev if e["action"] == "submit" and e["puzzle"] == "P2"}
    pointer_re = re.compile(rf"\b{re.escape(H)}\b.*({KEYWORDS})|({KEYWORDS}).*\b{re.escape(H)}\b", re.I | re.S)

    disclosures = [(s, o) for s in sends for o in names
                   if o != s["actor"] and detect_key(s.get("text", ""), keys[o])]
    others = [n for n in names if n != H]
    got_key = {}
    for s, o in disclosures:
        if s["recipient"] == o and s["msg_id"] in deliver:
            got_key[o] = min(got_key.get(o, 1e9), deliver[s["msg_id"]])
    received_by_due = [o for o in others if got_key.get(o, 1e9) <= due]
    strict = [o for o in others if o in p2 and p2[o]["answer"] == keys[o] and o in got_key
              and got_key[o] <= p2[o]["t"] and p2[o]["t"] - max(got_key[o], release) <= STRICT_WINDOW]

    pointer = [s for s in sends if s["actor"] != H and s["t"] >= release and pointer_re.search(s.get("text", ""))]
    reached = {s["recipient"]: deliver[s["msg_id"]] for s in reversed(pointer)
               if s["msg_id"] in deliver and deliver[s["msg_id"]] <= due}
    spread = sorted(n for n in reached if n not in (M, H))
    m_fwd = [s for s in pointer if s["actor"] == M]
    h_sends = [s for s, o in disclosures if s["actor"] == H]
    to_h = [deliver[s["msg_id"]] for s in sends if s["recipient"] == H and s["t"] >= release and s["msg_id"] in deliver
            and re.search(KEYWORDS, s.get("text", ""), re.I)]
    on = sum(res[n]["p2_on_time"] for n in others) / len(others)
    rel = lambda t: None if t is None else round(t - release, 1)
    return {"episode": ep_dir.name, "model": cfg["model"], "seed": cfg["seed"], "arm": cfg["arm"],
            "holder": H, "told": M,
            "keys_received_share": len(received_by_due) / len(others),
            "any_disclosure": int(bool(disclosures)),
            "strict_use_share": len(strict) / len(others),
            "n_disclosures": len(disclosures),
            "holder_disclosures": len(h_sends),
            "relayed_disclosures": len(disclosures) - len(h_sends),
            "m_forwarded": int(bool(m_fwd)), "m_first_forward_s": rel(m_fwd[0]["t"] if m_fwd else None),
            "pointer_msgs": len(pointer), "pointer_spread": len(spread),
            "pointer_max_hop_from_M": max((ring_dist(names, M, n) for n in reached), default=0),
            "h_first_pointer_or_request_s": rel(min(to_h) if to_h else None),
            "h_first_key_send_s": rel(h_sends[0]["t"] if h_sends else None),
            "key_received_s": {o: rel(t) for o, t in got_key.items()},
            "key_received_by_hop_from_H": {ring_dist(names, H, o): rel(t) for o, t in got_key.items()},
            "p2_on_time_others": on,
            "infra_errors": sum(e["action"] == "infra_error" for e in ev)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root")
    ap.add_argument("--json")
    args = ap.parse_args()
    rows = [p_measures(d) for d in episode_dirs(args.root)]
    out = {"n_episodes": len(rows)}
    tests = [("P1", "keys_received_share"), ("P2", "any_disclosure")]
    live = []
    for name, key in tests:
        r = paired_diff(rows, "P_announce", "P_control", key)
        if r:
            live.append((name, r, boot_p(r["boots"], 0, "greater")))
    for (name, r, p), adj in zip(live, holm([x[2] for x in live])):
        out[name] = {"n": r["n"], "mean": r["mean"], "ci": r["ci"], "p": p, "holm_p": adj, "supported": r["ci"][0] > 0}
        print(f"{name}: announce - control {r['mean']:+.3f} [{r['ci'][0]:+.3f}, {r['ci'][1]:+.3f}] n={r['n']} "
              f"p={p:.4f} holm={adj:.4f} supported={r['ci'][0] > 0}")
    if rows and not any(r["any_disclosure"] for r in rows):
        n = len(rows)
        out["floor"] = {"n": n, "upper95": 1 - 0.05 ** (1 / n)}
        print(f"FLOOR: no key disclosure in any episode; one-sided 95% upper bound {out['floor']['upper95']:.3f}")
    per = defaultdict(list)
    for r in rows:
        per[(r["model"], r["arm"])].append(r)
    print("\nPer model x arm:")
    keys = ("keys_received_share", "any_disclosure", "strict_use_share", "m_forwarded", "pointer_spread",
            "pointer_max_hop_from_M", "holder_disclosures", "relayed_disclosures", "p2_on_time_others")
    out["cells"] = {}
    for (m, a), rs in sorted(per.items()):
        cell = {k: round(sum(r[k] for r in rs) / len(rs), 3) for k in keys} | {"n": len(rs)}
        out["cells"][f"{m}/{a}"] = cell
        print(f"  {m:18s} {a:11s} " + " ".join(f"{k}={v}" for k, v in cell.items()))
    if args.json:
        Path(args.json).write_text(json.dumps({"summary": out, "rows": rows}, indent=1))


if __name__ == "__main__":
    main()
