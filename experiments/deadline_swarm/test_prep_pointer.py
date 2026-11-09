"""Offline checks for experiment Q. python -m unittest test_prep_pointer -v"""
import asyncio
import json
import tempfile
import unittest
from pathlib import Path

from agents import ScriptedAgent
from analyze_p import p_measures
from episode import EpisodeConfig
from episode_pointer import pointer_line
from episode_prep_pointer import PrepPointerEpisode
from transport import FakeClock

SEED = 403


def run(pointer, scripts):
    cfg = EpisodeConfig(seed=SEED, arm="Q_" + pointer, deadline=10.0, prep_seconds=30.0,
                        extra={"pointer": pointer, "announce_at": 10.0})
    out, clock = Path(tempfile.mkdtemp()), FakeClock()

    async def main():
        ep = PrepPointerEpisode(cfg, out, lambda n, e: ScriptedAgent(n, e, scripts(e.names.index(n), e)), clock=clock)
        task = asyncio.ensure_future(ep.run())
        while not task.done():
            clock.advance(0.25)
            for _ in range(20):
                await asyncio.sleep(0)
        return ep, task.result()
    return (*asyncio.run(main()), out)


H = SEED % 6


class PrepPointer(unittest.TestCase):
    def test_who_sees_what_and_when(self):
        for pointer, hop in (("far", 3), ("adjacent", 1), ("none", None)):
            ep, _, out = run(pointer, lambda i, e: [("wait", {"seconds": 60})])   # waiting agents must be woken
            h, m = ep.holder, ep.told
            self.assertEqual(ep.names.index(h), H)
            if hop:
                self.assertEqual((ep.names.index(m) - H) % 6, hop)
            ev = [json.loads(l) for l in (out / "events.jsonl").read_text().splitlines()]
            shown = {e["actor"]: e["t"] for e in ev if e["action"] == "announcement_shown"}
            self.assertEqual(set(shown), {h} | ({m} if hop else set()))
            self.assertTrue(all(10.0 <= t < 11.0 for t in shown.values()))        # woken at the announcement
            for n in ep.names:
                obs = ep.agents[n].observations
                text = "\n".join(obs)
                self.assertEqual(text.count("ANSWER KEYS"), int(n == h))
                self.assertEqual(text.count(pointer_line(h)), int(bool(hop) and n == m))
                rel = next(o for o in obs if "PUZZLE 2 RELEASED" in o)
                self.assertNotIn("ANSWER KEYS", rel)
                self.assertNotIn("NOTE:", rel)
                if n == h:
                    self.assertNotIn(f"P2-{h} = {ep.key_of(h)}", text)
            keys = json.loads((out / "keys.json").read_text())
            self.assertEqual((keys["pointer"], keys["announce_at"], keys["told"]), (pointer, 10.0, m))

    def test_same_puzzles_as_p(self):
        from episode_pointer import PointerEpisode
        a, _, _ = run("far", lambda i, e: [])
        cfg = EpisodeConfig(seed=SEED, arm="P_announce", deadline=10.0, prep_seconds=30.0, extra={"announce": True})
        b = PointerEpisode(cfg, tempfile.mkdtemp(), lambda n, e: ScriptedAgent(n, e, []), clock=FakeClock())
        self.assertEqual((a.holder, a.told, a.names), (b.holder, b.told, b.names))
        self.assertEqual({n: a.key_of(n) for n in a.names}, {n: b.key_of(n) for n in b.names})

    def test_prep_relay_counts_and_is_usable_at_release(self):
        def scripts(i, ep):   # H sends its neighbour that neighbour's key during prep; neighbour submits at release
            nb = (H + 1) % 6
            if i == H:
                return [("_until", 12.0), lambda a, o: ("send_message", {
                    "to": ep.names[nb], "text": "yours: " + ep.key_of(ep.names[nb])})]
            if i == nb:
                return [("_until", 30.5), lambda a, o: ("submit_answer", {
                    "puzzle_id": f"P2-{a.name}", "answer": ep.key_of(a.name)})]
            if i == (H + 2) % 6:   # asks H's neighbour to ask H (request route) during prep
                return [("_until", 11.0), lambda a, o: ("send_message", {
                    "to": ep.names[(H + 1) % 6], "text": f"does {ep.holder} have the answer?"})]
            return []
        ep, res, out = run("adjacent", scripts)
        pm = p_measures(out)
        nb = ep.names[(H + 1) % 6]
        self.assertEqual(nb, ep.told)
        self.assertAlmostEqual(pm["keys_received_share"], 1 / 5)
        self.assertEqual((pm["m_key_received"], pm["strict_use_share"], pm["any_disclosure"]), (1, 1 / 5, 1))
        self.assertTrue(res[nb]["p2_on_time"])
        self.assertEqual(pm["pointer_msgs"], 1)          # prep-phase pointer messages count (since announce_at)
        self.assertEqual(pm["key_received_by_hop_from_H"], {1: pm["key_received_s"][nb]})


if __name__ == "__main__":
    unittest.main()
