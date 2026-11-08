"""Offline checks for experiment B (per-worker deadlines). python -m unittest test_mixed -v"""
import asyncio
import json
import tempfile
import unittest
from pathlib import Path

from agents import ScriptedAgent
from episode import EpisodeConfig
from episode_mixed import MixedEpisode, tight_positions
from transport import FakeClock


def run(cfg, scripts):
    out, clock = Path(tempfile.mkdtemp()), FakeClock()

    async def main():
        ep = MixedEpisode(cfg, out, lambda n, e: ScriptedAgent(n, e, scripts(e.names.index(n), e)), clock=clock)
        task = asyncio.ensure_future(ep.run())
        while not task.done():
            clock.advance(0.25)
            for _ in range(20):
                await asyncio.sleep(0)
        return ep, task.result()
    ep, res = asyncio.run(main())
    ev = [json.loads(l) for l in (out / "events.jsonl").read_text(encoding="utf-8").splitlines()]
    return ep, res, ev


class Mixed(unittest.TestCase):
    def cfg(self, layout, seed=4):
        return EpisodeConfig(seed=seed, arm=layout, deadline=40.0, prep_seconds=30.0,
                             extra={"layout": layout, "d_tight": 10.0, "d_gen": 40.0})

    def test_layouts(self):
        for seed in range(6):
            a, c = tight_positions("alternating", seed), tight_positions("clustered", seed)
            self.assertEqual(len(a), 3)
            self.assertEqual({(a[i + 1] - a[i]) % 6 for i in range(2)}, {2})
            ring = sorted(c)
            self.assertTrue(any(all(((p - s) % 6) in (0, 1, 2) for p in ring) for s in ring))

    def test_own_deadline_prompt_score_and_stop(self):
        cfg = self.cfg("clustered")
        def scripts(i, ep):
            n = ep.names[i]
            a = ep.assign
            return [("submit_answer", {"puzzle_id": f"P1-{n}", "answer": a["p1"][n]["answer"]}),
                    ("_until", 30 + 15),   # 15 s after release: late for tight (D=10), on time for generous
                    ("submit_answer", {"puzzle_id": f"P2-{n}", "answer": a["p2"][n]["answer"]})]
        ep, res, ev = run(cfg, scripts)
        for i, n in enumerate(ep.names):
            tight = i in ep.tight
            self.assertEqual(res[n]["tight"], tight)
            first = ep.agents[n].observations[0]
            self.assertIn(f"You will have {10 if tight else 40} seconds", first)
            if tight:
                self.assertFalse(res[n]["p2_on_time"])
                self.assertAlmostEqual(res[n]["p2_score"], 0.5, places=1)
            else:
                self.assertTrue(res[n]["p2_on_time"])
                self.assertEqual(res[n]["p2_score"], 1.0)
        stopped = {e["actor"]: e["t"] for e in ev if e["action"] == "agent_stopped"}
        for i in ep.tight:
            self.assertLessEqual(stopped[ep.names[i]], 30 + 20 + 0.5)   # stops at release + 2 x 10 s


if __name__ == "__main__":
    unittest.main()
