"""Launch one episode.

python run.py --model glm-5.2 --seed 1 --arm announced_tight --deadline 150 --prep 300 \
              --topology ring --out outputs/<dir>
--model scripted runs the oracle policy (everyone submits correct answers) on the real clock.
"""
import argparse
import asyncio
import json
from pathlib import Path

from agents import LLMAgent, ScriptedAgent
from episode import Episode, EpisodeConfig


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--arm", required=True)
    ap.add_argument("--deadline", type=float, required=True)
    ap.add_argument("--prep", type=float, default=300.0)
    ap.add_argument("--unannounced", action="store_true")
    ap.add_argument("--topology", default="ring", choices=["ring", "isolation", "star"])
    ap.add_argument("--max-calls", type=int, default=60)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    out = Path(args.out)
    if (out / "results.json").exists():
        raise SystemExit(f"{out} already has results; refusing to overwrite")
    cfg = EpisodeConfig(seed=args.seed, arm=args.arm, deadline=args.deadline, announced=not args.unannounced,
                        prep_seconds=args.prep, topology=args.topology, model=args.model,
                        max_calls_per_agent=args.max_calls)

    def factory(name, ep):
        if args.model == "scripted":
            a = ep.assign
            return ScriptedAgent(name, ep, [
                ("submit_answer", {"puzzle_id": f"P1-{name}", "answer": a["p1"][name]["answer"]}),
                ("_until", cfg.prep_seconds + 1),
                ("submit_answer", {"puzzle_id": f"P2-{name}", "answer": a["p2"][name]["answer"]})])
        return LLMAgent(name, ep)

    res = asyncio.run(Episode(cfg, out, factory).run())
    print(json.dumps({k: {"p1": (v["p1"] or {}).get("correct"), "p2_score": round(v["p2_score"], 3),
                          "on_time": v["p2_on_time"]} for k, v in res.items()}))


if __name__ == "__main__":
    main()
