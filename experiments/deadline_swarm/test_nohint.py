"""python -m unittest test_nohint -v"""
import asyncio
import tempfile
import unittest

from agents import ScriptedAgent
from episode import Episode, EpisodeConfig
from episode_nohint import NoHintEpisode
from transport import FakeClock


class NoHint(unittest.TestCase):
    def test_prompt_has_no_coordination_text_but_tool_exists(self):
        async def build():
            mk = lambda cls: cls(EpisodeConfig(seed=1, arm="x", deadline=40, prep_seconds=360), tempfile.mkdtemp(),
                                 lambda n, e: ScriptedAgent(n, e, []), clock=FakeClock())
            return mk(NoHintEpisode), mk(Episode)
        nh, base = asyncio.run(build())
        name = nh.names[0]
        text = (nh.system_prompt(name) + nh.first_observation(name)).lower()
        for word in ("contact", "message", "six", "worker", "strategy", "communicat", "share", "coordinat", "help"):
            self.assertNotIn(word, text)
        tools = {t["name"]: t for t in nh.tools(name)}
        self.assertIn("send_message", tools)
        self.assertEqual(tools["send_message"]["parameters"]["properties"]["to"]["enum"],
                         base.tools(name)[0]["parameters"]["properties"]["to"]["enum"])
        self.assertEqual(nh.first_observation(name), base.first_observation(name))


if __name__ == "__main__":
    unittest.main()
