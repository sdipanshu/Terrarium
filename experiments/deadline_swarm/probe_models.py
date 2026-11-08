"""One-off probe: which hosted models make valid function calls, how accurate and how fast.

Usage: python probe_models.py [--concurrent MODEL] [--models a,b,...]
No behavioural outcome is looked at; this only checks the interface and latency.
"""
import argparse
import json
import random
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from adaption_client import AdaptionClient, function_calls
import puzzles

OUT = Path(__file__).parent / "outputs" / "probe"
TOOLS = [
    {"type": "function", "name": "submit_answer", "description": "Submit your final answer for a puzzle.",
     "parameters": {"type": "object", "properties": {"puzzle_id": {"type": "string"},
                                                     "answer": {"type": "string"}},
                    "required": ["puzzle_id", "answer"]}},
    {"type": "function", "name": "write_note", "description": "Append text to your private notebook.",
     "parameters": {"type": "object", "properties": {"text": {"type": "string"}}, "required": ["text"]}},
]


EFFORT = None


def one_call(client, model, seed):
    rng = random.Random(seed)
    p = puzzles.make_puzzle(rng, rng.choice(puzzles.USABLE))
    payload = {"model": model, "temperature": 0.7, "max_output_tokens": 16000, "tools": TOOLS,
               "instructions": "You are a worker in a puzzle exercise. Each turn, call exactly one tool.",
               "input": puzzles.render(p, "P1-probe")}
    if EFFORT:
        payload["reasoning"] = {"effort": EFFORT}
    t0 = time.monotonic()
    try:
        data, _ = client.create(payload, actor=f"{model}#{seed}")
    except RuntimeError as exc:
        return {"model": model, "seed": seed, "error": str(exc), "elapsed": time.monotonic() - t0}
    calls = function_calls(data)
    answer = None
    if calls and calls[0].get("name") == "submit_answer":
        try:
            answer = json.loads(calls[0].get("arguments") or "{}").get("answer")
        except json.JSONDecodeError:
            answer = "<bad json>"
    usage = data.get("usage") or {}
    return {"model": model, "seed": seed, "elapsed": round(time.monotonic() - t0, 1),
            "status": data.get("status"), "n_calls": len(calls),
            "tool": calls[0].get("name") if calls else None,
            "correct": puzzles.score(p, answer) if answer is not None else None,
            "out_tokens": usage.get("output_tokens"),
            "reasoning_tokens": (usage.get("output_tokens_details") or {}).get("reasoning_tokens"),
            "types": [o.get("type") for o in data.get("output", [])]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", default="")
    ap.add_argument("--concurrent", default="")
    ap.add_argument("--n", type=int, default=6)
    ap.add_argument("--effort", default="")
    args = ap.parse_args()
    global EFFORT
    EFFORT = args.effort or None
    OUT.mkdir(parents=True, exist_ok=True)
    client = AdaptionClient(log_path=OUT / "requests.jsonl")
    if args.concurrent:
        start = time.monotonic()
        with ThreadPoolExecutor(args.n) as pool:
            rows = list(pool.map(lambda s: one_call(client, args.concurrent, s), range(100, 100 + args.n)))
        for r in rows:
            print(json.dumps(r))
        print(f"wall {time.monotonic() - start:.1f}s for {args.n} concurrent calls")
        return
    models = args.models.split(",") if args.models else None
    if not models:
        listing = client.list_models()
        (OUT / "models.json").write_text(json.dumps(listing, indent=1))
        items = listing.get("data", listing) if isinstance(listing, dict) else listing
        models = [m.get("id") or m.get("name") for m in items]
        print("models:", models)
    for model in models:
        for seed in (1, 2):
            print(json.dumps(one_call(client, model, seed)), flush=True)


if __name__ == "__main__":
    main()
