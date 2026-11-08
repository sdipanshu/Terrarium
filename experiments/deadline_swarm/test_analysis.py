"""Offline checks for the analysis scripts, on scripted episodes. python -m unittest test_analysis -v"""
import asyncio
import json
import shutil
import tempfile
import unittest
from pathlib import Path

import puzzles
from agents import ScriptedAgent
from analyze import episode_dirs, holm
from analyze_b import b_measures
from analyze_f import STRICT_WINDOW, f_measures
from episode import EpisodeConfig
from episode_keys import KeyEpisode
from episode_mixed import MixedEpisode
from transport import FakeClock


def run(cls, cfg, scripts, out):
    clock = FakeClock()

    async def main():
        ep = cls(cfg, out, lambda n, e: ScriptedAgent(n, e, scripts(e.names.index(n), e)), clock=clock)
        task = asyncio.ensure_future(ep.run())
        while not task.done():
            clock.advance(0.25)
            for _ in range(20):
                await asyncio.sleep(0)
        return ep
    return asyncio.run(main())


class B(unittest.TestCase):
    def test_first_exchange_and_on_time(self):
        root = Path(tempfile.mkdtemp())
        for layout in ("alternating", "clustered"):
            cfg = EpisodeConfig(seed=7, arm=layout, deadline=40.0, prep_seconds=30.0,
                                extra={"layout": layout, "d_tight": 10.0, "d_gen": 40.0})

            def scripts(i, ep):
                n, nb = ep.names, ep.transport.neighbours
                if i == 0:   # 0 asks 1 first; 1 then answers with its own P1 rule (a useful method)
                    return [("send_message", {"to": n[1], "text": "hi, anything useful for P2?"}),
                            ("_until", 31.0),
                            lambda a, o: ("submit_answer", {"puzzle_id": f"P2-{n[0]}", "answer": ep.assign["p2"][n[0]]["answer"]})]
                if i == 1:
                    return [("_until", 5.0),
                            lambda a, o: ("send_message", {"to": n[0], "text": "mine: " + ep.assign["p1"][n[1]]["rule_text"]})]
                return []   # nobody else submits
            ep = run(MixedEpisode, cfg, scripts, root / f"m__s7__{layout}")
            m = b_measures(root / f"m__s7__{layout}")
            self.assertEqual(m["first"]["sender"], ep.names[1])
            self.assertEqual(m["first"]["initiator"], ep.names[0])
            self.assertEqual(m["first"]["kind"], "request")
            self.assertEqual(m["first"]["initiator_tight"], 0 in ep.tight)
            self.assertAlmostEqual(m["tight_on_time"], (1 if 0 in ep.tight else 0) / 3)
            self.assertAlmostEqual(m["generous_on_time"], (0 if 0 in ep.tight else 1) / 3)
        # archived originals are never analysed
        shutil.copytree(root / "m__s7__clustered", root / "failed_infra" / "m__s7__clustered__old")
        self.assertEqual([d.name for d in episode_dirs(root)], ["m__s7__alternating", "m__s7__clustered"])

    def test_holm(self):
        self.assertEqual(holm([0.01, 0.04, 0.03]), [0.03, 0.06, 0.06])


class F(unittest.TestCase):
    def episode(self, submit_at, out):
        cfg = EpisodeConfig(seed=205, arm="F_tight", deadline=40.0, prep_seconds=20.0, extra={"monitor": False})

        def scripts(i, ep):
            n = ep.names
            if i == 0:   # holder of n[1]'s key leaks it to n[1]
                return [lambda a, o: ("send_message", {"to": ep.holds[n[0]], "text": "use " + ep.key_of(ep.holds[n[0]])})]
            if i == 1:   # owner submits the key; also sends its own answer back (not a disclosure)
                return [("_until", submit_at),
                        lambda a, o: ("submit_answer", {"puzzle_id": f"P2-{n[1]}", "answer": ep.key_of(n[1])}),
                        lambda a, o: ("send_message", {"to": ep.holder_of[n[1]], "text": "got " + ep.key_of(n[1])})]
            return []
        return run(KeyEpisode, cfg, scripts, out)

    def test_strict_and_late_use(self):
        root = Path(tempfile.mkdtemp())
        ep = self.episode(21.0, root / "fast")
        m = f_measures(root / "fast")
        self.assertEqual([(d["sender"], d["key_owner"]) for d in m["disclosures"]], [(ep.names[0], ep.names[1])])
        self.assertEqual((m["breach_strict"], m["breach_lenient"], m["disclosures_before_owner_submit"]), (1, 1, 1))
        self.episode(20.0 + STRICT_WINDOW + 5, root / "slow")
        m = f_measures(root / "slow")
        self.assertEqual((m["any_disclosure"], m["breach_strict"]), (1, 0))
        # a hand-coded paraphrase becomes an undetected (escaped) disclosure
        codes = {str(ev["msg_id"]): {"disclosure": True, "subtype": "paraphrase"}
                 for ev in map(json.loads, (root / "slow" / "events.jsonl").read_text().splitlines())
                 if ev["action"] == "send" and ev["actor"] == ep.names[1]}
        m = f_measures(root / "slow", codes)
        self.assertEqual(m["escaped_disclosure"], 1)


if __name__ == "__main__":
    unittest.main()
