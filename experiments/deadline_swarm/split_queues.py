"""Run the remaining episodes with DeepSeek split into its own health-gated queue.

python split_queues.py

DeepSeek-v4-flash returned HTTP 504 on most requests from ~20:20 IST, so every DeepSeek episode launched
then exceeded the infra limit. Comparisons are within (model, seed), so DeepSeek cells can run at a
different time from glm/qwen cells of the same seed without breaking pairing. Streams:
  gq1: B 101-124 (glm, qwen)
  gq2: N1 13-24, then F 201-224 (glm, qwen)
  ds:  DeepSeek, up to 2 cells at a time, each only after a passing health probe; missing B and F
       cells first (alternating), then missing N1 cells, then single re-runs of over-limit cells.
glm/qwen over-limit re-runs stay with rerun_sweeper.py --models glm-5.2,qwen3.5-397b.
Waits first until no episode process is alive, so no batch script archives a live directory.
"""
import argparse
import shutil
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from adaption_client import AdaptionClient
from rerun_sweeper import EXPS, INFRA_LIMIT, healthy, infra_count

HERE = Path(__file__).parent
OUT = HERE / "outputs"
GQ = "glm-5.2,qwen3.5-397b"
DS = "deepseek-v4-flash"
_lock = threading.Lock()


def say(msg):
    with _lock, open(OUT / "split_queues.log", "a") as f:
        f.write(f"{time.strftime('%H:%M:%S')} {msg}\n")


def live_episodes():
    ps = ("(Get-CimInstance Win32_Process | Where-Object { $_.Name -match 'python' -and "
          "$_.CommandLine -match '--one|run\\.py ' }).Count")
    out = subprocess.run(["powershell", "-NoProfile", "-Command", ps], capture_output=True, text=True).stdout
    return int(out.strip() or 0)


def batch(exp, seeds, models, log_name):
    script = EXPS[exp][0]
    cmd = [sys.executable, "-W", "ignore", str(HERE / script), "--root", str(OUT / exp), "--seeds", seeds,
           "--models", models]
    with open(OUT / log_name, "a") as log:
        return subprocess.call(cmd, cwd=HERE, stdout=log, stderr=subprocess.STDOUT)


def stream(name, jobs):
    for exp, seeds in jobs:
        say(f"{name}: start {exp} {seeds}")
        rc = batch(exp, seeds, GQ, f"{exp}_gq_batch.log")
        say(f"{name}: {exp} {seeds} exit {rc}")


def ds_cells_done(exp, seed):
    return len([p for p in (OUT / exp).glob(f"{DS}__s{seed}__*") if (p / "results.json").exists()])


def ds_healthy(client):
    """DeepSeek is 'healthy' only if 3 consecutive short requests each finish in under 20 s.
    Healthy hours had a median latency of ~3 s; during the 20:00+ overload successful calls took
    ~44 s and the gateway cut anything past 60 s, while a one-word probe still passed."""
    payload = {"model": DS, "input": [{"role": "user", "content": "What is 17 * 23? Reply with the number only."}],
               "max_output_tokens": 400}
    for _ in range(3):
        t0 = time.monotonic()
        try:
            client.create(payload, actor="probe")
        except Exception as exc:  # noqa: BLE001 - any failure means not healthy
            say(f"ds: probe failed: {str(exc)[:60]}")
            return False
        if time.monotonic() - t0 > 20:
            say(f"ds: probe slow ({time.monotonic() - t0:.0f}s)")
            return False
    return True


def ds_cell(client, exp, seed, rerun):
    while not ds_healthy(client):
        say(f"ds: unhealthy; {exp} s{seed} waits 5 min")
        time.sleep(300)
    if rerun:
        root = OUT / exp
        for ep in sorted(root.glob(f"{DS}__s{seed}__*")):
            if (ep / "results.json").exists() and infra_count(ep) > INFRA_LIMIT \
                    and not any((root / "failed_infra").glob(ep.name + "__*")):
                n = infra_count(ep)
                dest = root / "failed_infra" / f"{ep.name}__over3_infra"
                dest.parent.mkdir(exist_ok=True)
                shutil.move(str(ep), str(dest))
                if (root / f"{ep.name}.log").exists():
                    shutil.move(str(root / f"{ep.name}.log"), str(dest) + ".log")
                say(f"ds: archived {exp}/{ep.name} ({n} infra errors); re-running once")
    rc = batch(exp, str(seed), DS, f"{exp}_ds_batch.log")
    say(f"ds: {exp} s{seed} exit {rc}")


def ds_live():
    ps = ("(Get-CimInstance Win32_Process | Where-Object { $_.Name -match 'python' -and "
          "$_.CommandLine -match 'deepseek' -and $_.CommandLine -match '--one|run\\.py ' }).Count")
    out = subprocess.run(["powershell", "-NoProfile", "-Command", ps], capture_output=True, text=True).stdout
    return int(out.strip() or 0)


DS_WORKERS = 2


def ds_stream():
    while ds_live():   # a restarted DeepSeek stream must not archive cells a previous one is still running
        say("ds: waiting for live DeepSeek episodes from a previous stream")
        time.sleep(60)
    client = AdaptionClient(OUT / "probe_ds_queue.jsonl", timeout=90)
    b, f = EXPS["expB"][1], EXPS["expF"][1]
    missing = [x for pair in zip(b, f) for x in (("expB", pair[0]), ("expF", pair[1]))]
    missing += [("expN1", s) for s in EXPS["expN1"][1]] + [("expA", s) for s in EXPS["expA"][1]]
    missing = [(e, s) for e, s in missing if ds_cells_done(e, s) < EXPS[e][2]]
    with ThreadPoolExecutor(max_workers=DS_WORKERS) as pool:
        list(pool.map(lambda c: ds_cell(client, c[0], c[1], False), missing))
    over = []
    for exp, (_, seeds, _) in EXPS.items():
        root = OUT / exp
        for s in seeds:
            if any(infra_count(p) > INFRA_LIMIT and not any((root / "failed_infra").glob(p.name + "__*"))
                   for p in root.glob(f"{DS}__s{s}__*") if (p / "results.json").exists()):
                over.append((exp, s))
    say(f"ds: missing cells done; {len(over)} over-limit cells to re-run once")
    with ThreadPoolExecutor(max_workers=DS_WORKERS) as pool:
        list(pool.map(lambda c: ds_cell(client, c[0], c[1], True), over))
    say("ds: ALL DONE")


def batch_running(script):
    ps = (f"(Get-CimInstance Win32_Process | Where-Object {{ $_.Name -match 'python' -and "
          f"$_.CommandLine -match '{script}' -and $_.CommandLine -notmatch '--one' }}).Count")
    out = subprocess.run(["powershell", "-NoProfile", "-Command", ps], capture_output=True, text=True).stdout
    return int(out.strip() or 0) > 0


def f_after_n1():
    while batch_running("run_batch_nohint"):
        time.sleep(60)
    stream("gq2F", [("expF", "201-224")])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--streams", default="gq1,gq2,ds", help="gq1, gq2, gq2F (F once N1 batch exits), ds")
    ap.add_argument("--no-wait", action="store_true", help="skip waiting for live episodes")
    ap.add_argument("--ds-workers", type=int, default=2, help="DeepSeek cells run at once")
    args = ap.parse_args()
    global DS_WORKERS
    DS_WORKERS = args.ds_workers
    while not args.no_wait and (n := live_episodes()) > 0:
        say(f"waiting for {n} live episode processes to finish")
        time.sleep(60)
    say(f"starting streams {args.streams}")
    make = {"gq1": lambda: threading.Thread(target=stream, args=("gq1", [("expB", "101-124")])),
            "gq2": lambda: threading.Thread(target=stream, args=("gq2", [("expN1", "13-24"), ("expF", "201-224")])),
            "gq2F": lambda: threading.Thread(target=f_after_n1),
            "ds": lambda: threading.Thread(target=ds_stream)}
    threads = [make[s]() for s in args.streams.split(",")]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    say("ALL STREAMS DONE")


if __name__ == "__main__":
    main()
