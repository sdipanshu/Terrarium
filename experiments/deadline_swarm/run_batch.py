"""Run experiment A: per seed, launch every (model, arm) episode together, then wait.

python run_batch.py --root outputs/expA --seeds 1-12
Resumable: episodes with results.json are skipped; an episode directory without
results.json (crash) is archived to failed_infra/ before its single re-run.
"""
import argparse
import shutil
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).parent
MODELS = ["glm-5.2", "deepseek-v4-flash", "qwen3.5-397b"]
ARMS = {"announced_tight": (40, False), "announced_generous": (160, False), "unannounced_tight": (40, True)}
PREP = 360


def parse_seeds(text):
    a, _, b = text.partition("-")
    return list(range(int(a), int(b or a) + 1))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True)
    ap.add_argument("--seeds", required=True)
    ap.add_argument("--models", default=",".join(MODELS))
    ap.add_argument("--arms", default=",".join(ARMS))
    args = ap.parse_args()
    root = Path(args.root)
    root.mkdir(parents=True, exist_ok=True)
    for seed in parse_seeds(args.seeds):
        procs = []
        for model in args.models.split(","):
            for arm in args.arms.split(","):
                deadline, unannounced = ARMS[arm]
                out = root / f"{model}__s{seed}__{arm}"
                if (out / "results.json").exists():
                    continue
                if out.exists():
                    dest = root / "failed_infra" / f"{out.name}__{int(time.time())}"
                    dest.parent.mkdir(exist_ok=True)
                    shutil.move(str(out), str(dest))
                    print(f"archived incomplete {out.name}", flush=True)
                cmd = [sys.executable, "-W", "ignore", str(HERE / "run.py"), "--model", model, "--seed", str(seed),
                       "--arm", arm, "--deadline", str(deadline), "--prep", str(PREP), "--out", str(out)]
                if unannounced:
                    cmd.append("--unannounced")
                log = open(root / f"{out.name}.log", "w")
                procs.append((out.name, subprocess.Popen(cmd, stdout=log, stderr=subprocess.STDOUT, cwd=HERE)))
        print(f"seed {seed}: launched {len(procs)} episodes at {time.strftime('%H:%M:%S')}", flush=True)
        for name, p in procs:
            rc = p.wait()
            print(f"  {name} exit {rc}", flush=True)


if __name__ == "__main__":
    main()
