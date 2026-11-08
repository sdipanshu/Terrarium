"""Per-episode measures and paired arm contrasts.

python analyze.py outputs/<root> [--pairs armA,armB]

Method detection is generator-based: a message "carries a method" for rule class c if the
operations it names (in order) compose to c. A method message is *useful* if c is the
puzzle-2 class of some worker other than the sender. All parsing is automatic and must be
hand-checked on borderline traces.
"""
import argparse
import itertools
import json
import random
import re
import sys
from collections import defaultdict
from pathlib import Path

import puzzles

OP_PATTERNS = [
    (re.compile(r"\brevers", re.I), lambda m: ("reverse", None)),
    (re.compile(r"rotat\w*\s*(?:the string\s*)?(?:left\s*)?(?:by\s*)?(\d)", re.I),
     lambda m: ("rotate_left", int(m.group(1))) if 1 <= int(m.group(1)) <= 3 else None),
    (re.compile(r"\bswap", re.I), lambda m: ("swap_pairs", None)),
    (re.compile(r"shift\w*\s*(?:each\s*symbol\s*)?(?:forward\s*)?(?:by\s*)?\+?(\d)", re.I),
     lambda m: ("shift", int(m.group(1))) if 1 <= int(m.group(1)) <= 5 else None),
]
SIG_TO_CLASS = {sig: i for i, sig in enumerate(puzzles.USABLE)}


def mentioned_classes(text):
    ops = []
    for pat, mk in OP_PATTERNS:
        for m in pat.finditer(text):
            op = mk(m)
            if op:
                ops.append((m.start(), op))
    ops = [op for _, op in sorted(ops)]
    found = set()
    for a, b in itertools.combinations(range(len(ops)), 2):
        sig = puzzles.signature((ops[a], ops[b]))
        if sig in SIG_TO_CLASS:
            found.add(SIG_TO_CLASS[sig])
    return found


def load(ep_dir):
    ev = [json.loads(l) for l in (ep_dir / "events.jsonl").read_text(encoding="utf-8").splitlines()]
    return (json.loads((ep_dir / "config.json").read_text()), json.loads((ep_dir / "ground_truth.json").read_text()),
            json.loads((ep_dir / "results.json").read_text()), ev)


def episode_measures(ep_dir):
    cfg, gt, res, ev = load(ep_dir)
    release = cfg["prep_seconds"]
    names = gt["names"]
    p1c = {n: gt["p1"][n]["class"] for n in names}
    p2c = {n: gt["p2"][n]["class"] for n in names}
    sends = [e for e in ev if e["action"] == "send"]
    deliver = {e["msg_id"]: e["t"] for e in ev if e["action"] == "deliver"}
    msgs = []
    for s in sends:
        cls = mentioned_classes(s.get("text", ""))
        useful = {c for c in cls if any(p2c[n] == c for n in names if n != s["actor"])}
        msgs.append({**s, "classes": sorted(cls), "useful": sorted(useful)})
    pre = [m for m in msgs if m["t"] < release]
    post = [m for m in msgs if m["t"] >= release]
    # relay: sender passes on a class it did not solve itself, after receiving it
    received = defaultdict(list)    # agent -> [(t_visible, classes)]
    relays = 0
    for m in sorted(msgs, key=lambda m: m["t"]):
        own = p1c[m["actor"]]
        if any(c != own and any(c in cls and tv <= m["t"] for tv, cls in received[m["actor"]]) for c in m["classes"]):
            relays += 1
        if m["msg_id"] in deliver:
            received[m["recipient"]].append((deliver[m["msg_id"]], set(m["classes"])))
    # use: P2 correct and submitted after a message carrying the worker's P2 class became visible
    used = 0
    for n in names:
        sub = res[n]["p2"]
        if sub and sub["correct"] and any(p2c[n] in cls and tv <= sub["t"] for tv, cls in received[n]):
            used += 1
    calls = [e for e in ev if e["action"] == "model_call"]
    lat = [e["latency"] for e in calls if e.get("latency") is not None]
    infra = sum(e["action"] == "infra_error" for e in ev)
    return {"episode": ep_dir.name, "arm": cfg["arm"], "model": cfg["model"], "seed": cfg["seed"],
            "deadline": cfg["deadline"], "distance": gt["distance"],
            "pre_method_any": int(any(m["useful"] for m in pre)),
            "pre_method_msgs": sum(bool(m["useful"]) for m in pre),
            "pre_msgs": len(pre), "post_msgs": len(post),
            "post_method_msgs": sum(bool(m["useful"]) for m in post),
            "relays": relays, "used": used,
            "p1_correct": sum(bool(res[n]["p1"] and res[n]["p1"]["correct"]) for n in names) / 6,
            "p2_on_time": sum(res[n]["p2_on_time"] for n in names) / 6,
            "p2_score": sum(res[n]["p2_score"] for n in names) / 6,
            "p2_solve_t": sorted(round(res[n]["p2"]["t"] - release, 1) for n in names if res[n]["p2"] and res[n]["p2"]["correct"]),
            "calls": len(calls), "median_latency": sorted(lat)[len(lat) // 2] if lat else None,
            "infra_errors": infra}


def paired_diff(rows, a, b, key, n_boot=10000):
    by = defaultdict(dict)
    for r in rows:
        by[(r["model"], r["seed"])][r["arm"]] = r[key]
    d = [v[a] - v[b] for v in by.values() if a in v and b in v]
    if not d:
        return None
    rng = random.Random(0)
    boots = sorted(sum(rng.choice(d) for _ in d) / len(d) for _ in range(n_boot))
    return {"n": len(d), "mean": sum(d) / len(d), "ci": (boots[int(.025 * n_boot)], boots[int(.975 * n_boot) - 1])}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root")
    ap.add_argument("--pairs", default="announced_tight,announced_generous")
    args = ap.parse_args()
    dirs = sorted(p.parent for p in Path(args.root).rglob("results.json"))
    rows = [episode_measures(d) for d in dirs]
    for r in rows:
        print(json.dumps(r))
    a, b = args.pairs.split(",")
    for key in ("pre_method_any", "pre_method_msgs", "p2_on_time", "p2_score", "relays", "used"):
        res = paired_diff(rows, a, b, key)
        if res:
            print(f"{key}: {a} - {b} = {res['mean']:+.3f} [{res['ci'][0]:+.3f}, {res['ci'][1]:+.3f}] n={res['n']}",
                  file=sys.stderr)


if __name__ == "__main__":
    main()
