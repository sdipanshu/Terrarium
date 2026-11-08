"""Readable per-agent transcript of one episode: system prompt, then each turn's
observation, reasoning and action. python transcript.py <episode_dir> [--agent NAME] [--max-reasoning N]
Writes <episode_dir>/TRANSCRIPT.md.
"""
import argparse
import json
from pathlib import Path


def obs_text(item):
    return item.get("content") if "content" in item else item.get("output", "")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("episode")
    ap.add_argument("--agent", default="")
    ap.add_argument("--max-reasoning", type=int, default=2500)
    args = ap.parse_args()
    ep = Path(args.episode)
    cfg = json.loads((ep / "config.json").read_text())
    gt = json.loads((ep / "ground_truth.json").read_text())
    res = json.loads((ep / "results.json").read_text()) if (ep / "results.json").exists() else {}
    events = [json.loads(l) for l in (ep / "events.jsonl").read_text(encoding="utf-8").splitlines()]
    reqs = [json.loads(l) for l in (ep / "requests.jsonl").read_text(encoding="utf-8").splitlines()]
    ok = {}
    for r in reqs:
        if r.get("response") is not None:
            ok.setdefault(r["actor"], []).append(r)
    calls = {}
    for e in events:
        if e["action"] == "model_call":
            calls.setdefault(e["actor"], []).append(e)

    names = [args.agent] if args.agent else gt["names"]
    out = [f"# Transcript: {ep.name}",
           f"model `{cfg['model']}` · arm `{cfg['arm']}` · seed {cfg['seed']} · D = {cfg['deadline']} s · "
           f"release at T+{int(cfg['prep_seconds'])}s · shortcut distance {gt['distance']}", "",
           "Ring order: " + " – ".join(gt["names"]) + " – (back to start)", ""]
    for n in names:
        p2 = gt["p2"][n]
        r = res.get(n, {})
        out += [f"## {n}", f"- puzzle 1 rule: {gt['p1'][n]['rule_text']}",
                f"- puzzle 2 rule: {p2['rule_text']} (same as **{gt['source'][n]}**'s puzzle 1)",
                f"- result: P1 {'✔' if (r.get('p1') or {}).get('correct') else '✘'}, "
                f"P2 score {r.get('p2_score', 0):.2f}, on time {r.get('p2_on_time')}", ""]
        rq = ok.get(n, [])
        if rq:
            out += ["<details><summary>System prompt</summary>", "", "```", rq[0]["request"]["instructions"], "```",
                    "</details>", ""]
        for i, c in enumerate(calls.get(n, [])):
            obs = obs_text(rq[i]["request"]["input"][-1]) if i < len(rq) else "(not found)"
            reasoning = (c.get("reasoning") or "").strip()
            if len(reasoning) > args.max_reasoning:
                reasoning = reasoning[:args.max_reasoning] + " […]"
            out += [f"### Turn {i + 1} · request T+{c.get('t_request', 0):.0f}s → reply T+{c['t']:.0f}s "
                    f"({c.get('latency', 0):.0f} s)",
                    "**Observation**", "```", obs, "```"]
            if reasoning:
                out += ["**Reasoning**", "", "> " + reasoning.replace("\n", "\n> "), ""]
            if c.get("text"):
                out += ["**Visible text**", "", c["text"], ""]
            out += [f"**Action:** `{c['tool']}` {json.dumps(c.get('args'), ensure_ascii=False)}", ""]
    path = ep / "TRANSCRIPT.md"
    path.write_text("\n".join(out), encoding="utf-8")
    print(path)


if __name__ == "__main__":
    main()
