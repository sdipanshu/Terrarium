"""Experiment R: lucrative answer-key shortcut (no examples, early answer box, speed score), rule vs open.

python run_batch_r.py --root outputs/expR --seeds 501-510
Same resume/archive rules as run_batch.py.
"""
import argparse
import asyncio
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).parent
MODELS = ["glm-5.2", "deepseek-v4-flash", "qwen3.5-397b"]
LAYOUTS = ["R_open", "R_rule"]
PREP = 360
DEADLINE = {"R_open": 40, "R_rule": 40}
RULE = {"R_open": False, "R_rule": True}
ANNOUNCE_AT = 120


def one(model, seed, layout, out):
    """Child-process entry: run a single lucrative-key episode."""
    from agents import LLMAgent
    from episode_lucrative import LucrativeEpisode, RConfig
    cfg = RConfig(seed=seed, arm=layout, deadline=DEADLINE[layout], prep_seconds=PREP, model=model,
                  extra={"prompt": "nohint", "rule": RULE[layout], "announce_at": ANNOUNCE_AT})
    res = asyncio.run(LucrativeEpisode(cfg, out, lambda n, ep: LLMAgent(n, ep)).run())
    print(json.dumps({k: round(v["p2_score"], 2) for k, v in res.items()}))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root")
    ap.add_argument("--seeds")
    ap.add_argument("--models", default=",".join(MODELS))
    ap.add_argument("--one", nargs=4, metavar=("MODEL", "SEED", "LAYOUT", "OUT"))
    args = ap.parse_args()
    if args.one:
        m, s, l, o = args.one
        return one(m, int(s), l, Path(o))
    root = Path(args.root)
    root.mkdir(parents=True, exist_ok=True)
    a, _, b = args.seeds.partition("-")
    for seed in range(int(a), int(b or a) + 1):
        procs = []
        for model in args.models.split(","):
            for layout in LAYOUTS:
                out = root / f"{model}__s{seed}__{layout}"
                if (out / "results.json").exists():
                    continue
                if out.exists():
                    dest = root / "failed_infra" / f"{out.name}__{int(time.time())}"
                    dest.parent.mkdir(exist_ok=True)
                    shutil.move(str(out), str(dest))
                    print(f"archived incomplete {out.name}", flush=True)
                cmd = [sys.executable, "-W", "ignore", str(Path(__file__).resolve()), "--one", model, str(seed),
                       layout, str(out)]
                log = open(root / f"{out.name}.log", "w")
                procs.append((out.name, subprocess.Popen(cmd, stdout=log, stderr=subprocess.STDOUT, cwd=HERE)))
        print(f"seed {seed}: launched {len(procs)} episodes at {time.strftime('%H:%M:%S')}", flush=True)
        for name, p in procs:
            print(f"  {name} exit {p.wait()}", flush=True)


if __name__ == "__main__":
    main()
