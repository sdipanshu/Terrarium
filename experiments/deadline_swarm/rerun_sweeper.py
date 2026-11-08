"""Single re-run of finished episodes with more than 3 infra_error events, gated on a model health probe.

python rerun_sweeper.py

Every 10 minutes: for each (experiment, model, seed) cell whose arms have all finished, archive the
episodes over the limit that were never archived before (single re-run rule), probe the model
(two consecutive successes), and re-run the cell's missing episodes with the experiment's own batch
script. Cells still running are never touched, so the main queues and the sweeper cannot collide.
Exits once every experiment is complete and nothing is pending.
"""
import shutil
import subprocess
import sys
import time
from pathlib import Path

from adaption_client import AdaptionClient

HERE = Path(__file__).parent
OUT = HERE / "outputs"
MODELS = ["glm-5.2", "deepseek-v4-flash", "qwen3.5-397b"]
EXPS = {  # name: (batch script, seeds, arms per (model, seed))
    "expA": ("run_batch.py", range(1, 25), 3),
    "expN1": ("run_batch_nohint.py", range(1, 25), 2),
    "expB": ("run_batch_b.py", range(101, 125), 2),
    "expF": ("run_batch_f.py", range(201, 225), 3),
}
INFRA_LIMIT = 3


def say(msg):
    print(f"{time.strftime('%H:%M:%S')} {msg}", flush=True)


def infra_count(ep):
    return sum('"infra_error"' in line for line in (ep / "events.jsonl").read_text(encoding="utf-8").splitlines())


def healthy(client, model):
    payload = {"model": model, "input": [{"role": "user", "content": "Reply with the single word: ok"}],
               "max_output_tokens": 200}
    for _ in range(2):
        try:
            client.create(payload, actor="probe")
        except Exception as exc:  # noqa: BLE001 - any failure means not healthy
            say(f"probe {model} failed: {str(exc)[:80]}")
            return False
    return True


def pending(exp, model, seed):
    """Finished-cell episodes over the limit and never archived; None if the cell is not finished."""
    root, arms = OUT / exp, EXPS[exp][2]
    eps = [p for p in root.glob(f"{model}__s{seed}__*") if p.is_dir()]
    if len(eps) < arms or not all((p / "results.json").exists() for p in eps):
        return None
    return [p for p in eps if infra_count(p) > INFRA_LIMIT and not any((root / "failed_infra").glob(p.name + "__*"))]


def complete():
    return all(len(list((OUT / e).glob("*/results.json"))) >= len(s) * a * len(MODELS)
               for e, (_, s, a) in EXPS.items())


def main():
    client = AdaptionClient(OUT / "probe_sweeper.jsonl", timeout=90)
    while True:
        did = False
        for exp, (script, seeds, _) in EXPS.items():
            for model in MODELS:
                for seed in seeds:
                    over = pending(exp, model, seed)
                    if not over:
                        continue
                    if not healthy(client, model):
                        say(f"{model} unhealthy; {exp} s{seed} re-run deferred")
                        break
                    for ep in over:
                        dest = OUT / exp / "failed_infra" / f"{ep.name}__over3_infra"
                        dest.parent.mkdir(exist_ok=True)
                        n = infra_count(ep)
                        shutil.move(str(ep), str(dest))
                        log = OUT / exp / f"{ep.name}.log"
                        if log.exists():
                            shutil.move(str(log), str(dest) + ".log")
                        say(f"archived {exp}/{ep.name} ({n} infra errors); re-running once")
                    with open(OUT / "rerun_sweeper_batch.log", "a") as log:
                        rc = subprocess.call([sys.executable, "-W", "ignore", str(HERE / script), "--root",
                                              str(OUT / exp), "--seeds", str(seed), "--models", model],
                                             cwd=HERE, stdout=log, stderr=subprocess.STDOUT)
                    say(f"re-ran {exp} {model} s{seed} (exit {rc})")
                    did = True
        if not did and complete():
            say("ALL DONE: every experiment complete, no pending re-runs")
            return
        time.sleep(600)


if __name__ == "__main__":
    main()
