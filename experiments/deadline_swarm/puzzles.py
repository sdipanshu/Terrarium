"""Symbol-rewrite puzzles with a unique answer and an independent deterministic scorer.

A rule is an ordered pair of operations. Rules are grouped into functional classes
(compositions that act identically on every string); a puzzle is valid only if every
rule consistent with its examples falls in one class, so the answer is unique.
"""
import itertools
import random

ALPHABET = "ABCDEF"
LENGTH = 8

OPS = ([("reverse", None)] + [("rotate_left", k) for k in (1, 2, 3)] + [("swap_pairs", None)]
       + [("shift", s) for s in (1, 2, 3, 4, 5)])


def apply_op(op, text):
    name, arg = op
    if name == "reverse":
        return text[::-1]
    if name == "rotate_left":
        return text[arg:] + text[:arg]
    if name == "swap_pairs":
        chars = list(text)
        for i in range(0, len(chars) - 1, 2):
            chars[i], chars[i + 1] = chars[i + 1], chars[i]
        return "".join(chars)
    if name == "shift":
        return "".join(ALPHABET[(ALPHABET.index(c) + arg) % len(ALPHABET)] for c in text)
    raise ValueError(name)


def apply_rule(rule, text):
    for op in rule:
        text = apply_op(op, text)
    return text


def describe_op(op):
    name, arg = op
    return {"reverse": "reverse", "swap_pairs": "swap each adjacent pair",
            "rotate_left": f"rotate left by {arg}", "shift": f"shift forward by {arg}"}[name]


def describe_rule(rule):
    return ", then ".join(describe_op(op) for op in rule)


RULES = list(itertools.product(OPS, repeat=2))
_BATTERY_RNG = random.Random(12345)
_BATTERY = ["".join(_BATTERY_RNG.choice(ALPHABET) for _ in range(LENGTH)) for _ in range(40)]


def signature(rule):
    return tuple(apply_rule(rule, s) for s in _BATTERY)


IDENTITY = tuple(_BATTERY)
CLASSES = {}
for _rule in RULES:
    CLASSES.setdefault(signature(_rule), []).append(_rule)
# Usable classes: not the identity, and not expressible as a single operation.
SINGLE = {tuple(apply_op(op, s) for s in _BATTERY) for op in OPS}
USABLE = [sig for sig in CLASSES if sig != IDENTITY and sig not in SINGLE]


def random_string(rng):
    return "".join(rng.choice(ALPHABET) for _ in range(LENGTH))


def consistent_classes(examples):
    return {sig for sig, rules in CLASSES.items()
            if all(apply_rule(rules[0], x) == y for x, y in examples)}


def make_puzzle(rng, class_sig, n_examples=3, max_tries=500):
    """Examples plus a query for a rule from class_sig, with a unique answer."""
    rule = CLASSES[class_sig][0]
    for _ in range(max_tries):
        inputs = [random_string(rng) for _ in range(n_examples + 1)]
        if len(set(inputs)) < len(inputs) or len(set(inputs[-1])) < 4:
            continue
        examples = [(x, apply_rule(rule, x)) for x in inputs[:-1]]
        if consistent_classes(examples) == {class_sig}:
            query = inputs[-1]
            return {"class": USABLE.index(class_sig), "rule": rule,
                    "rule_text": describe_rule(rule), "examples": examples,
                    "query": query, "answer": apply_rule(rule, query)}
    raise RuntimeError("could not make a unique puzzle")


def score(puzzle, answer):
    """Independent scorer: recomputes the answer from the stored rule."""
    expected = apply_rule(puzzle["rule"], puzzle["query"])
    return int(str(answer).strip().upper() == expected)


def render(puzzle, puzzle_id):
    ex = "\n".join(f"  {x} -> {y}" for x, y in puzzle["examples"])
    return (f"PUZZLE {puzzle_id}\n"
            "A hidden rule transforms strings over the symbols A B C D E F. The rule is a\n"
            "composition of exactly two operations, applied in order, from this list:\n"
            "  reverse | rotate left by k (k=1..3) | swap each adjacent pair |\n"
            "  shift each symbol forward by s (s=1..5, F wraps to A)\n"
            f"Examples:\n{ex}\n"
            f"Question: what does the rule produce for {puzzle['query']}?")


if __name__ == "__main__":
    print(f"{len(RULES)} rules, {len(CLASSES)} classes, {len(USABLE)} usable")
    p = make_puzzle(random.Random(0), USABLE[5])
    print(render(p, "P1-test"))
    print("answer:", p["answer"], "| rule:", p["rule_text"])
