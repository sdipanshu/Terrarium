"""Offline acceptance checks (no GPU, no API): python -m unittest test_smoke -v"""
import asyncio
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from agents import ScriptedAgent
from episode import Episode, EpisodeConfig, p2_score
from transport import FakeClock


def run_episode(cfg, scripts, clock=None, step=0.25):
    """Run with a FakeClock; scripts maps ring index -> list of steps (or a factory)."""
    out = Path(tempfile.mkdtemp())
    clock = clock or FakeClock()

    def factory(name, ep):
        idx = ep.names.index(name)
        steps = scripts(idx, ep) if callable(scripts) else scripts.get(idx, [])
        return ScriptedAgent(name, ep, steps)

    async def main():
        ep = Episode(cfg, out, factory, clock=clock)
        task = asyncio.ensure_future(ep.run())
        while not task.done():
            clock.advance(step)
            for _ in range(20):
                await asyncio.sleep(0)
        return ep, task.result()

    ep, res = asyncio.run(main())
    events = [json.loads(l) for l in (out / "events.jsonl").read_text(encoding="utf-8").splitlines()]
    return ep, res, events, out


def submit_both(ep, name, p2_at):
    a = ep.assign
    return [("submit_answer", {"puzzle_id": f"P1-{name}", "answer": a["p1"][name]["answer"]}),
            ("_until", p2_at),
            ("submit_answer", {"puzzle_id": f"P2-{name}", "answer": a["p2"][name]["answer"]})]


class Smoke(unittest.TestCase):
    def cfg(self, **kw):
        base = dict(seed=7, arm="test", deadline=20.0, prep_seconds=30.0, tick=2.0)
        base.update(kw)
        return EpisodeConfig(**base)

    def test_all_six_submit_easy_episode(self):
        _, res, _, out = run_episode(self.cfg(), lambda i, ep: submit_both(ep, ep.names[i], 31.0))
        self.assertEqual(len(res), 6)
        for row in res.values():
            self.assertEqual(row["p1"]["score"], 1.0)
            self.assertEqual(row["p2_score"], 1.0)
            self.assertTrue(row["p2_on_time"])
        shutil.rmtree(out)

    def test_relay_reaches_non_neighbour_only_via_hops(self):
        def scripts(i, ep):
            n = ep.names
            if i == 0:  # n0 tries n2 directly (must fail), then sends to n1
                return [("send_message", {"to": n[2], "text": "direct"}),
                        ("send_message", {"to": n[1], "text": "CLUE-42"})]
            if i == 1:  # n1 forwards once it sees the clue
                def fwd(agent, obs):
                    return ("send_message", {"to": n[2], "text": "fwd CLUE-42"}) if "CLUE-42" in obs else ("wait", {"seconds": 5})
                return [("wait", {"seconds": 30})] + [fwd] * 10
            return []
        ep, _, events, out = run_episode(self.cfg(), scripts)
        n = ep.names
        self.assertIn(n[2], [e["recipient"] for e in events if e["action"] == "send_rejected"])
        vis = {(e["actor"], e["msg_id"]): e["t"] for e in events if e["action"] == "deliver"}
        sends = [e for e in events if e["action"] == "send"]
        first = next(s for s in sends if s["text"] == "CLUE-42")
        relay = next(s for s in sends if s["text"] == "fwd CLUE-42")
        self.assertEqual((first["recipient"], relay["actor"], relay["recipient"]), (n[1], n[1], n[2]))
        self.assertGreaterEqual(relay["t"], vis[(n[1], first["msg_id"])])   # forwarded only after it was visible
        self.assertGreaterEqual(vis[(n[2], relay["msg_id"])], vis[(n[1], first["msg_id"])] + 2.0)  # one hop per tick
        self.assertIsNone(ep.transport.read_direct(n[0], n[2]))           # direct read of another inbox fails
        self.assertFalse(any(m["text"].endswith("CLUE-42") for m in ep.transport.inbox[n[3]]))
        shutil.rmtree(out)

    def test_star_leaves_cannot_reach_each_other(self):
        def scripts(i, ep):
            n = ep.names
            return [("send_message", {"to": n[2], "text": "leaf to leaf"})] if i == 1 else []
        ep, _, events, out = run_episode(self.cfg(topology="star"), scripts)
        n = ep.names
        self.assertEqual(ep.transport.neighbours(n[1]), [n[0]])
        self.assertTrue(any(e["action"] == "send_rejected" and e["actor"] == n[1] for e in events))
        self.assertEqual(ep.transport.inbox[n[2]], [])
        shutil.rmtree(out)

    def test_deadline_edges(self):
        cfg = self.cfg()
        rel, D = cfg.prep_seconds, cfg.deadline
        def scripts(i, ep):
            name = ep.names[i]
            when = {0: rel + D - 0.5, 1: rel + D + 1.0, 2: rel + 2 * D + 1.0}.get(i)
            return submit_both(ep, name, when) if when else []
        ep, res, _, out = run_episode(cfg, scripts, step=0.25)
        n = ep.names
        self.assertEqual(res[n[0]]["p2_score"], 1.0)
        self.assertTrue(0.9 < res[n[1]]["p2_score"] < 1.0)
        self.assertFalse(res[n[1]]["p2_on_time"])
        self.assertIsNone(res[n[2]]["p2"])            # episode had ended
        self.assertEqual(p2_score(True, 2 * D, D), 0.0)
        self.assertEqual(p2_score(False, 1.0, D), 0.0)
        shutil.rmtree(out)

    def test_prompts_are_neutral_and_arms_differ_only_in_limit_line(self):
        out = Path(tempfile.mkdtemp())
        mk = lambda **kw: Episode(self.cfg(**kw), out / str(len(kw)) / kw.get("arm", "x"),
                                  lambda n, e: ScriptedAgent(n, e, []), clock=FakeClock())
        async def build():
            return mk(arm="a", announced=True), mk(arm="u", announced=False)
        a, u = asyncio.run(build())
        name = a.names[0]
        self.assertEqual(a.system_prompt(name), u.system_prompt(name))
        fa, fu = a.first_observation(name).splitlines(), u.first_observation(name).splitlines()
        self.assertEqual(fa[:-1], fu[:-1])
        text = (a.system_prompt(name) + a.first_observation(name)).lower()
        for word in ("share", "relay", "forward to", "pass on", "help", "cache", "collu", "same rule",
                     "other workers' puzzle"):
            self.assertNotIn(word, text)
        shutil.rmtree(out, ignore_errors=True)

    def test_puzzle2_rule_comes_from_worker_at_distance(self):
        from episode import make_assignment
        for seed, d in ((3, 1), (4, 2), (5, 3)):
            a = make_assignment(seed)
            self.assertEqual(a["distance"], d)
            n = a["names"]
            for i, name in enumerate(n):
                src = a["source"][name]
                ring = min((n.index(src) - i) % 6, (i - n.index(src)) % 6)
                self.assertEqual(ring, d)
                self.assertEqual(a["p2"][name]["class"], a["p1"][src]["class"])


if __name__ == "__main__":
    unittest.main()
