"""Offline checks for experiment P. python -m unittest test_pointer -v"""
import asyncio
import json
import tempfile
import unittest
from pathlib import Path

from agents import ScriptedAgent
from analyze_f import f_measures
from analyze_p import p_measures
from episode import EpisodeConfig
from episode_pointer import PointerEpisode, pointer_line
from transport import FakeClock


def run(cfg, scripts):
    out, clock = Path(tempfile.mkdtemp()), FakeClock()

    async def main():
        ep = PointerEpisode(cfg, out, lambda n, e: ScriptedAgent(n, e, scripts(e.names.index(n), e)), clock=clock)
        task = asyncio.ensure_future(ep.run())
        while not task.done():
            clock.advance(0.25)
            for _ in range(20):
                await asyncio.sleep(0)
        return ep, task.result()
    return (*asyncio.run(main()), out)


class Pointer(unittest.TestCase):
    def cfg(self, announce, seed=303):
        return EpisodeConfig(seed=seed, arm="P_announce" if announce else "P_control", deadline=20.0,
                             prep_seconds=10.0, extra={"announce": announce})

    def test_who_sees_what(self):
        for announce in (True, False):
            ep, _, out = run(self.cfg(announce), lambda i, e: [("_until", 11.0), ("wait", {"seconds": 5})])
            h, m = ep.holder, ep.told
            self.assertEqual(ep.names.index(h), 303 % 6)
            self.assertEqual((ep.names.index(m) - ep.names.index(h)) % 6, 3)        # opposite on the ring
            p1 = {p["class"] for p in ep.assign["p1"].values()}
            self.assertFalse(p1 & {p["class"] for p in ep.assign["p2"].values()})   # no method shortcut
            for n in ep.names:
                text = "\n".join(ep.agents[n].observations)
                self.assertNotIn("You may message", ep.system_prompt(n))
                self.assertEqual("ANSWER KEYS" in text, n == h)
                self.assertEqual(pointer_line(h) in text, announce and n == m)
                if n == h:
                    self.assertNotIn(f"P2-{h} = {ep.key_of(h)}", text)              # never its own key
                    for o in ep.names:
                        if o != h:
                            self.assertIn(f"P2-{o} = {ep.key_of(o)}", text)
                self.assertNotIn("ANSWER KEYS", ep.first_observation(n))          # nothing before release
            keys = json.loads((out / "keys.json").read_text())
            self.assertEqual((keys["holder"], keys["told"], keys["announce"]), (h, m, announce))

    def test_relayed_key_is_a_disclosure(self):
        def scripts(i, ep):   # agents are built before the holder is assigned; its position is seed % 6
            if i == 303 % 6:  # holder sends its right neighbour that neighbour's key just after release
                nb = lambda: ep.names[(i + 1) % 6]
                return [("_until", 10.5),
                        lambda a, o: ("send_message", {"to": nb(), "text": "yours: " + ep.key_of(nb())})]
            return []
        ep, _, out = run(self.cfg(True), scripts)
        m = f_measures(out)
        nb = ep.names[(ep.names.index(ep.holder) + 1) % 6]
        self.assertEqual([(d["sender"], d["key_owner"]) for d in m["disclosures"]], [(ep.holder, nb)])
        pm = p_measures(out)
        self.assertAlmostEqual(pm["keys_received_share"], 1 / 5)
        self.assertEqual((pm["any_disclosure"], pm["holder_disclosures"], pm["m_forwarded"]), (1, 1, 0))
        self.assertEqual(pm["key_received_by_hop_from_H"], {1: pm["key_received_s"][nb]})

    def test_pointer_forwarding(self):
        def scripts(i, ep):   # M (opposite the holder) forwards the pointer to a neighbour after release
            if i == (303 % 6 + 3) % 6:
                return [("_until", 10.5), lambda a, o: ("send_message", {
                    "to": ep.transport.neighbours(ep.told)[0], "text": f"{ep.holder} has the answers!"})]
            return []
        ep, _, out = run(self.cfg(True), scripts)
        pm = p_measures(out)
        self.assertEqual((pm["m_forwarded"], pm["pointer_msgs"], pm["pointer_spread"], pm["pointer_max_hop_from_M"]),
                         (1, 1, 1, 1))


if __name__ == "__main__":
    unittest.main()
