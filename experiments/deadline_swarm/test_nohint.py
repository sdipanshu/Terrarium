"""python -m unittest test_nohint -v"""
import asyncio
import tempfile
import unittest

from agents import ScriptedAgent
from episode import Episode, EpisodeConfig
from episode_nohint import NoHintEpisode, CLOSING
from transport import FakeClock


class NoHint(unittest.TestCase):
    def test_only_the_closing_line_differs(self):
        async def build():
            mk = lambda cls: cls(EpisodeConfig(seed=1, arm="x", deadline=40, prep_seconds=360), tempfile.mkdtemp(),
                                 lambda n, e: ScriptedAgent(n, e, []), clock=FakeClock())
            return mk(NoHintEpisode), mk(Episode)
        nh, base = asyncio.run(build())
        for name in nh.names:
            self.assertEqual(nh.system_prompt(name) + CLOSING, base.system_prompt(name))
            self.assertNotIn("You may message", nh.system_prompt(name))
            self.assertIn("direct contacts", nh.system_prompt(name))
            self.assertEqual(nh.tools(name), base.tools(name))
            self.assertEqual(nh.first_observation(name), base.first_observation(name))


if __name__ == "__main__":
    unittest.main()
