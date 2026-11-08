"""Spend so far from logged token usage, at Adaption's listed prices (credits per 1M tokens).

python cost.py [outputs_dir]
"""
import json
import sys
from collections import defaultdict
from pathlib import Path

PRICES = {  # model: (input, cached input, output)
    "glm-5.2": (1.40, 0.26, 4.40), "qwen3.5-397b": (0.55, 0.225, 3.50),
    "deepseek-v4-flash": (0.04444, 0.001414, 0.13332), "glm-53-flash": (0.15, 0.03, 0.50),
    "gemma-4-26b-a4b-it": (0.0765, 0.0425, 0.255), "gemma-4-31b-it": (0.09, 0.05, 0.34),
    "qwen3.8-27b": (0.039, 0.0039, 1.25),
}


def main():
    root = Path(sys.argv[1] if len(sys.argv) > 1 else Path(__file__).parent / "outputs")
    by = defaultdict(lambda: defaultdict(float))
    for f in root.rglob("requests.jsonl"):
        group = f.relative_to(root).parts[0]
        for line in f.read_text(encoding="utf-8").splitlines():
            r = json.loads(line)
            resp = r.get("response")
            if not resp:
                continue
            u = resp.get("usage") or {}
            model = r["request"]["model"]
            pin, pcache, pout = PRICES.get(model, (0, 0, 0))
            cached = (u.get("input_tokens_details") or {}).get("cached_tokens") or 0
            inp = (u.get("input_tokens") or 0) - cached
            out = u.get("output_tokens") or 0
            c = (inp * pin + cached * pcache + out * pout) / 1e6
            by[group][model] += c
            by[group]["_calls"] += 1
            by["TOTAL"][model] += c
    for group, models in sorted(by.items(), key=lambda kv: kv[0] == "TOTAL"):
        total = sum(v for k, v in models.items() if not k.startswith("_"))
        detail = ", ".join(f"{k} {v:.2f}" for k, v in sorted(models.items()) if not k.startswith("_"))
        print(f"{group:28s} {total:8.2f} credits   ({detail})")


if __name__ == "__main__":
    main()
