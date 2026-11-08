"""Experiment F / F-M: confidential answer keys, tight vs generous, plus monitor arm.

python run_batch_f.py --root outputs/expF --seeds 201-212
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
LAYOUTS = ["F_tight", "F_generous", "FM_tight"]
PREP = 360
DEADLINE = {"F_tight": 40, "F_generous": 160, "FM_tight": 40}


def one(model, seed, layout, out):
    """Child-process entry: run a single answer-key episode."""
    from agents import LLMAgent
    from episode import EpisodeConfig
    from episode_keys import KeyEpisode
    cfg = EpisodeConfig(seed=seed, arm=layout, deadline=DEADLINE[layout], prep_seconds=PREP, model=model,
                        extra={"prompt": "nohint", "monitor": layout.startswith("FM")})
    res = asyncio.run(KeyEpisode(cfg, out, lambda n, ep: LLMAgent(n, ep)).run())
    print(json.dumps({k: [round(v["p2_score"], 2), v["monitor_penalised"]] for k, v in res.items()}))


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
