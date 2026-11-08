"""Run remaining episodes under a fixed concurrency budget, seed by seed with all models together.

python slot_queue.py [--budget 9]

Replaces split_queues.py / rerun_sweeper.py after the per-user rate limit (HTTP 429, 60 s window) was
hit at ~13 concurrent episodes. A slot is (experiment, seed, models); its episodes are launched together
by the experiment's own batch script, as in the original design. Slots start while running episodes +
slot size <= budget. Order:
  1. F and B seeds alternating, every model whose cell is incomplete (DeepSeek only if its latency
     probe passes at launch; otherwise it is deferred);
  2. deferred and other incomplete cells (A, N1, B, F);
  3. single re-run of every finished cell with > 3 infra errors that was never archived before.
Incomplete directories left by stopped runs are archived by the batch scripts before their re-run.
"""
import argparse
import json
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path

from adaption_client import AdaptionClient

HERE = Path(__file__).parent
OUT = HERE / "outputs"
MODELS = ["glm-5.2", "deepseek-v4-flash", "qwen3.5-397b"]
DS = "deepseek-v4-flash"
EXPS = {  # name: (batch script, seeds, arms per (model, seed))
    "expA": ("run_batch.py", range(1, 25), 3),
    "expN1": ("run_batch_nohint.py", range(1, 25), 2),
    "expB": ("run_batch_b.py", range(101, 125), 2),
    "expF": ("run_batch_f.py", range(201, 225), 3),
}
INFRA_LIMIT = 3
_lock = threading.Lock()
running = 0


def say(msg):
    with _lock, open(OUT / "slot_queue.log", "a") as f:
        f.write(f"{time.strftime('%H:%M:%S')} {msg}\n")


def infra_count(ep):
    return sum('"infra_error"' in l for l in (ep / "events.jsonl").read_text(encoding="utf-8").splitlines())


def finished(exp, model, seed):
    return [p for p in (OUT / exp).glob(f"{model}__s{seed}__*") if (p / "results.json").exists()]


def incomplete(exp, model, seed):
    return len(finished(exp, model, seed)) < EXPS[exp][2]


def archived_before(exp, ep):
    return any((OUT / exp / "failed_infra").glob(ep.name + "__*"))


def over_limit(exp, model, seed):
    return [p for p in finished(exp, model, seed) if infra_count(p) > INFRA_LIMIT and not archived_before(exp, p)]


def ds_fast(client):
    payload = {"model": DS, "input": [{"role": "user", "content": "What is 17 * 23? Reply with the number only."}],
               "max_output_tokens": 400}
    for _ in range(3):
        t0 = time.monotonic()
        try:
            client.create(payload, actor="probe")
        except Exception:  # noqa: BLE001
            return False
        if time.monotonic() - t0 > 20:
            return False
    return True


def run_slot(exp, seed, models, size, rerun):
    global running
    try:
        if rerun:
            for m in models:
                for ep in over_limit(exp, m, seed):
                    n, dest = infra_count(ep), OUT / exp / "failed_infra" / f"{ep.name}__over3_infra"
                    dest.parent.mkdir(exist_ok=True)
                    shutil.move(str(ep), str(dest))
                    log = OUT / exp / f"{ep.name}.log"
                    if log.exists():
                        shutil.move(str(log), str(dest) + ".log")
                    say(f"archived {exp}/{ep.name} ({n} infra errors); re-running once")
        cmd = [sys.executable, "-W", "ignore", str(HERE / EXPS[exp][0]), "--root", str(OUT / exp),
               "--seeds", str(seed), "--models", ",".join(models)]
        with open(OUT / f"{exp}_slot_batch.log", "a") as log:
            rc = subprocess.call(cmd, cwd=HERE, stdout=log, stderr=subprocess.STDOUT)
        say(f"{exp} s{seed} {','.join(models)} exit {rc}")
    finally:
        with _lock:
            running -= size


def launch(exp, seed, models, rerun, budget):
    global running
    if rerun:
        size = sum(len(over_limit(exp, m, seed)) for m in models)
    else:
        size = sum(EXPS[exp][2] - len(finished(exp, m, seed)) for m in models)
    if size == 0:
        return
    while True:
        budget = current_budget(budget)
        share = recent_429_share()
        if share > 0.10:
            say(f"rate limit: {share:.0%} of recent requests are HTTP 429; holding launches")
            time.sleep(60)
            continue
        with _lock:
            if running + size <= budget or running == 0:
                running += size
                break
        time.sleep(10)
    say(f"start {exp} s{seed} {','.join(models)} ({size} episodes{', re-run' if rerun else ''}); running {running}")
    threading.Thread(target=run_slot, args=(exp, seed, models, size, rerun)).start()


def recent_429_share(window=120):
    """Share of requests ending in the last `window` s that got HTTP 429 (monotonic clock is machine-wide)."""
    now, n, bad = time.monotonic(), 0, 0
    for f in OUT.glob("exp*/*__*/requests.jsonl"):
        if time.time() - f.stat().st_mtime > window:
            continue
        for line in f.read_text(encoding="utf-8").splitlines()[-40:]:
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            if now - r.get("t_end", 0) <= window:
                n += 1
                bad += r.get("http_status") == 429
    return bad / n if n >= 10 else 0.0


BUDGET_FILE = OUT / "slot_budget.txt"


def current_budget(default):
    """Budget can be changed while running by writing a number to outputs/slot_budget.txt."""
    try:
        return int(BUDGET_FILE.read_text().strip())
    except (OSError, ValueError):
        return default


def live_episodes():
    ps = ("(Get-CimInstance Win32_Process | Where-Object { $_.Name -match 'python' -and "
          "$_.CommandLine -match '--one|run\\.py ' }).Count")
    out = subprocess.run(["powershell", "-NoProfile", "-Command", ps], capture_output=True, text=True).stdout
    return int(out.strip() or 0)


def wait_all():
    while True:
        with _lock:
            if running == 0:
                return
        time.sleep(10)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--budget", type=int, default=4, help="max concurrent episodes")
    ap.add_argument("--stop-at", default="08:00", help="local HH:MM after which no new slot is launched")
    args = ap.parse_args()
    while live_episodes():   # never archive a directory an earlier queue is still running
        say("waiting for live episodes from an earlier queue")
        time.sleep(60)
    BUDGET_FILE.write_text(str(args.budget))
    client = AdaptionClient(OUT / "probe_slot_queue.jsonl", timeout=90)
    say(f"start, budget {args.budget}")
    stop_at = time.mktime(time.strptime(time.strftime("%Y-%m-%d ") + args.stop_at, "%Y-%m-%d %H:%M"))
    if stop_at < time.time():
        stop_at += 86400
    # F and B seeds alternating, low seeds first, so whatever finishes by the cutoff is balanced across
    # models; each (model, seed) cell is its own slot, re-run right after its seed. A/N1 leftovers last
    # (N1 has all 24 seeds; its remaining work is DeepSeek re-runs and DeepSeek s24).
    order = [x for pair in zip(EXPS["expF"][1], EXPS["expB"][1]) for x in (("expF", pair[0]), ("expB", pair[1]))]
    order += [(e, s) for e in ("expA", "expN1") for s in EXPS[e][1]]
    deferred = []

    def do(exp, seed, model, wait_ds):
        if time.time() > stop_at:
            return False
        if model == DS and (incomplete(exp, model, seed) or over_limit(exp, model, seed)):
            while not ds_fast(client):
                if not wait_ds:
                    deferred.append((exp, seed))
                    say(f"DeepSeek slow/unhealthy: {exp} s{seed} deferred")
                    return True
                say(f"DeepSeek slow/unhealthy; {exp} s{seed} waits 5 min")
                time.sleep(300)
        if incomplete(exp, model, seed):
            launch(exp, seed, [model], False, args.budget)
        elif over_limit(exp, model, seed):
            launch(exp, seed, [model], True, args.budget)
        return True

    for exp, seed in order:
        for model in MODELS:
            if not do(exp, seed, model, wait_ds=False):
                say(f"stop time {args.stop_at} reached; no new launches")
                wait_all()
                say("ALL DONE (time cutoff)")
                return
    wait_all()
    for exp, seed in deferred + order:                         # deferred DeepSeek cells, then any re-run still due
        for model in MODELS:
            if not do(exp, seed, model, wait_ds=True):
                break
    wait_all()
    say("ALL DONE")


if __name__ == "__main__":
    main()
