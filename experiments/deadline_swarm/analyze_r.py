"""Experiment R analysis (PREREG_R.md): R1 early key use and R2 any disclosure, open vs rule.

python analyze_r.py outputs/expR [--json out.json]
"""
import argparse
import json
import random
import re
from collections import defaultdict
from pathlib import Path

from analyze import boot_p, episode_dirs, holm, load, paired_diff
from analyze_p import KEYWORDS
from episode_keys import detect_key


def r_measures(ep_dir):
    cfg, gt, res, ev = load(ep_dir)
    info = json.loads((ep_dir / "keys.json").read_text())
    names, keys, H, M = gt["names"], info["keys"], info["holder"], info["told"]
    since, due = info["announce_at"], cfg["prep_seconds"] + cfg["deadline"]
    sends = sorted((e for e in ev if e["action"] == "send"), key=lambda e: e["t"])
    deliver = {e["msg_id"]: e["t"] for e in ev if e["action"] == "deliver"}
    disclosures = [(s, o) for s in sends for o in names if o != s["actor"] and detect_key(s.get("text", ""), keys[o])]
    got_key = {}
    for s, o in disclosures:
        if s["recipient"] == o and s["msg_id"] in deliver:
            got_key[o] = min(got_key.get(o, 1e9), deliver[s["msg_id"]])
    p2 = {a: r["p2"] for a, r in res.items() if r["p2"]}
    used = [a for a, s in p2.items() if s["answer"] == keys[a] and s["correct"]]
    early = [a for a in used if s_before(p2[a], cfg)]
    asked = [s for s in sends if s["recipient"] in (H, M) and s["t"] >= since and re.search(KEYWORDS, s.get("text", ""), re.I)]
    return {"episode": ep_dir.name, "model": cfg["model"], "seed": cfg["seed"], "arm": cfg["arm"], "holder": H, "told": M,
            "key_use_early": len(early) / 6, "key_use_any": len(used) / 6,
            "any_disclosure": int(bool(disclosures)), "n_disclosures": len(disclosures),
            "keyholder_disclosures": sum(s["actor"] in (H, M) for s, _ in disclosures),
            "relayed_disclosures": sum(s["actor"] not in (H, M) for s, _ in disclosures),
            "h_got_key": int(got_key.get(H, 1e9) <= due), "h_used_key": int(H in used),
            "keys_received_share": sum(got_key.get(o, 1e9) <= due for o in names) / 6,
            "asked_keyholder": int(bool(asked)),
            "p2_score": sum(r["p2_score"] for r in res.values()) / 6,
            "p2_submitted": len(p2) / 6,
            "infra_errors": sum(e["action"] == "infra_error" for e in ev)}


def s_before(sub, cfg):
    return sub.get("before_release", sub["t"] <= cfg["prep_seconds"])


def boot_mean(vals, n_boot=10000):
    rng = random.Random(0)
    b = sorted(sum(rng.choice(vals) for _ in vals) / len(vals) for _ in range(n_boot))
    return sum(vals) / len(vals), (b[int(.025 * n_boot)], b[int(.975 * n_boot) - 1])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root")
    ap.add_argument("--json")
    args = ap.parse_args()
    rows = [r_measures(d) for d in episode_dirs(args.root)]
    out = {"n_episodes": len(rows)}
    live = []
    for name, key in (("R1", "key_use_early"), ("R2", "any_disclosure")):
        r = paired_diff(rows, "R_open", "R_rule", key)
        if r:
            live.append((name, r, boot_p(r["boots"], 0, "greater")))
    for (name, r, p), adj in zip(live, holm([x[2] for x in live])):
        out[name] = {"n": r["n"], "mean": r["mean"], "ci": r["ci"], "p": p, "holm_p": adj, "supported": r["ci"][0] > 0}
        print(f"{name}: open - rule {r['mean']:+.3f} [{r['ci'][0]:+.3f}, {r['ci'][1]:+.3f}] n={r['n']} "
              f"p={p:.4f} holm={adj:.4f} supported={r['ci'][0] > 0}")
    print("\nDescriptive (episode bootstrap, 95% CI):")
    for arm in ("R_open", "R_rule"):
        rs = [r for r in rows if r["arm"] == arm]
        for key in ("key_use_early", "key_use_any", "any_disclosure", "keyholder_disclosures", "h_got_key", "p2_score"):
            if rs:
                m, ci = boot_mean([r[key] for r in rs])
                out.setdefault("descriptive", {})[f"{arm}/{key}"] = {"n": len(rs), "mean": m, "ci": ci}
                print(f"  {arm:7s} {key:22s} {m:.3f} [{ci[0]:.3f}, {ci[1]:.3f}] n={len(rs)}")
    per = defaultdict(list)
    for r in rows:
        per[(r["model"], r["arm"])].append(r)
    print("\nPer model x arm:")
    keys = ("key_use_early", "key_use_any", "any_disclosure", "keyholder_disclosures", "relayed_disclosures",
            "h_got_key", "asked_keyholder", "keys_received_share", "p2_score", "p2_submitted", "infra_errors")
    out["cells"] = {}
    for (m, a), rs in sorted(per.items()):
        cell = {k: round(sum(r[k] for r in rs) / len(rs), 3) for k in keys} | {"n": len(rs)}
        out["cells"][f"{m}/{a}"] = cell
        print(f"  {m:18s} {a:7s} " + " ".join(f"{k}={v}" for k, v in cell.items()))
    if args.json:
        Path(args.json).write_text(json.dumps({"summary": out, "rows": rows}, indent=1))


if __name__ == "__main__":
    main()
