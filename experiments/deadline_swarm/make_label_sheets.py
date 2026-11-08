"""Draw the blind label-validation samples (PREREG deviations A3 / N3 / B2 / F2). Run once, after all runs finish.

python make_label_sheets.py --out outputs/labels [--allow-incomplete]

Writes, per sheet, items.json (blind: no arm, model, episode or detector label; shuffled, seed 0) and
key.json (item id -> episode, msg_id, arm, model, detector label) for un-blinding after coding.
  method sheet: 40 detector positives + 20 negatives from A, N1 and B, stratified by experiment x model.
  keys sheet:   every F candidate (detect_key hit, owners' own answers excluded, or keyword match).
"""
import argparse
import json
import random
import re
from collections import defaultdict
from pathlib import Path

from analyze import episode_dirs, load, mentioned_classes
from episode_keys import detect_key

HERE = Path(__file__).parent
METHOD_EXPS = {"expA": 216, "expN1": 144, "expB": 144}
F_EXP = ("expF", 216)
KEYWORDS = re.compile(r"key|keys|confirm|match|verif|correct\?|right\?|can't share|cannot share|not allowed"
                      r"|confidential", re.I)
N_POS, N_NEG = 40, 20


def allocate(strata, total, rng):
    """Spread `total` draws over strata as evenly as their sizes allow; returns the drawn items."""
    pools = {k: rng.sample(v, len(v)) for k, v in strata.items()}
    picked, order = [], sorted(pools)
    while len(picked) < total and any(pools.values()):
        for k in order:
            if pools[k] and len(picked) < total:
                picked.append(pools[k].pop())
    return picked


def method_messages(root):
    out = []
    for ep in episode_dirs(root):
        cfg, gt, _, ev = load(ep)
        names = gt["names"]
        p2 = {n: gt["p2"][n] for n in names}
        for s in (e for e in ev if e["action"] == "send"):
            useful = any(p2[n]["class"] == c for c in mentioned_classes(s.get("text", "")) for n in names
                         if n != s["actor"])
            others = sorted({p2[n]["rule_text"] for n in names if n != s["actor"]})
            out.append({"episode": ep.name, "msg_id": s["msg_id"], "arm": cfg["arm"], "model": cfg["model"],
                        "detector": int(useful), "text": s.get("text", ""), "other_p2_rules": others})
    return out


def key_candidates(root):
    out = []
    for ep in episode_dirs(root):
        cfg, gt, res, ev = load(ep)
        keys = json.loads((ep / "keys.json").read_text())
        holds = keys["holds"]
        sends = [e for e in ev if e["action"] == "send"]
        p2_t = {e["actor"]: e["t"] for e in ev if e["action"] == "submit" and e["puzzle"] == "P2"}
        for s in sends:
            text = s.get("text", "")
            hits = [o for o in gt["names"] if o != s["actor"] and detect_key(text, keys["keys"][o])]
            if not hits and not KEYWORDS.search(text):
                continue
            edge = {s["actor"], s["recipient"]}
            thread = [{"from": e["actor"], "to": e["recipient"], "text": e.get("text", ""), "t": round(e["t"])}
                      for e in sends if {e["actor"], e["recipient"]} == edge and e["t"] < s["t"]][-3:]
            out.append({"episode": ep.name, "msg_id": s["msg_id"], "arm": cfg["arm"], "model": cfg["model"],
                        "detector_owners": hits, "sender": s["actor"], "recipient": s["recipient"],
                        "t": round(s["t"]), "release": cfg["prep_seconds"], "text": text, "thread": thread,
                        "key_table": [{"owner": o, "key": keys["keys"][o], "held_by": h}
                                      for h, o in holds.items()],
                        "owner_p2_submitted_at": {o: round(t) for o, t in p2_t.items()}})
    return out


BLIND_DROP = {"episode", "msg_id", "arm", "model", "detector", "detector_owners"}


def write_sheet(out, name, items, rng):
    rng.shuffle(items)
    blind, key = [], {}
    for i, it in enumerate(items):
        iid = f"{name[0]}{i + 1:03d}"
        blind.append({"id": iid} | {k: v for k, v in it.items() if k not in BLIND_DROP})
        key[iid] = {k: it[k] for k in BLIND_DROP if k in it}
    d = out / name
    d.mkdir(parents=True, exist_ok=False)
    (d / "items.json").write_text(json.dumps(blind, indent=1))
    (d / "key.json").write_text(json.dumps(key, indent=1))
    return len(blind)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(HERE / "outputs" / "labels"))
    ap.add_argument("--outputs", default=str(HERE / "outputs"))
    ap.add_argument("--allow-incomplete", action="store_true", help="testing only")
    args = ap.parse_args()
    base, out = Path(args.outputs), Path(args.out)
    counts = {e: len(episode_dirs(base / e)) for e in list(METHOD_EXPS) + [F_EXP[0]]}
    targets = METHOD_EXPS | {F_EXP[0]: F_EXP[1]}
    if not args.allow_incomplete and any(counts[e] < targets[e] for e in targets):
        raise SystemExit(f"runs incomplete: {counts}; samples are drawn once, after all runs")
    rng = random.Random(0)

    pos, neg = defaultdict(list), defaultdict(list)
    for exp in METHOD_EXPS:
        for m in method_messages(base / exp):
            (pos if m["detector"] else neg)[(exp, m["model"])].append(m | {"arm": f"{exp}/{m['arm']}"})
    method = allocate(pos, N_POS, rng) + allocate(neg, N_NEG, rng)
    n_method = write_sheet(out, "method", method, rng)

    cands = key_candidates(base / F_EXP[0])
    n_keys = write_sheet(out, "keys", cands, rng)
    plan = ("user codes all" if n_keys <= 80 else
            "analyst codes all; user codes a stratified sample of 80 (seed 0) for kappa")
    if n_keys > 80:
        strata = defaultdict(list)
        for iid, k in json.loads((out / "keys" / "key.json").read_text()).items():
            strata[(k["arm"], k["model"])].append(iid)
        (out / "keys" / "user_sample.json").write_text(json.dumps(sorted(allocate(strata, 80, rng))))
    summary = {"episodes": counts, "method_items": n_method, "key_candidates": n_keys, "key_plan": plan}
    (out / "summary.json").write_text(json.dumps(summary, indent=1))
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
