"""Experiment B: per-worker deadlines in one ring (three tight, three generous).

Subclasses Episode without changing it. Each worker sees and is scored against its
own deadline. A worker stops acting at its own end (release + 2 x its deadline), so a
timed-out worker cannot relay (primary-pilot rule). The episode ends at the latest end.
"""
import asyncio
import dataclasses
import json
from contextlib import contextmanager

from episode import Episode

LAYOUTS = {"alternating": (0, 2, 4), "clustered": (0, 1, 2)}


def tight_positions(layout, seed):
    off = seed % 6
    return sorted((p + off) % 6 for p in LAYOUTS[layout])


class MixedEpisode(Episode):
    def __init__(self, cfg, out_dir, agent_factory, clock=None):
        super().__init__(cfg, out_dir, agent_factory, clock)
        x = cfg.extra
        self.tight = set(tight_positions(x["layout"], cfg.seed))
        self.D = {n: float(x["d_tight"] if i in self.tight else x["d_gen"]) for i, n in enumerate(self.names)}
        self._base = cfg

    @contextmanager
    def _as(self, agent):
        old = self.cfg
        self.cfg = dataclasses.replace(self._base, deadline=self.D[agent])
        try:
            yield
        finally:
            self.cfg = old

    def own_end(self, agent):
        return self._base.prep_seconds + 2 * self.D[agent]

    def first_observation(self, agent):
        with self._as(agent):
            return super().first_observation(agent)

    def observation(self, agent, result, release_shown):
        with self._as(agent):
            return super().observation(agent, result, release_shown)

    def submit(self, agent, pid, answer, t):
        with self._as(agent):
            return super().submit(agent, pid, answer, t)

    async def wait_for(self, agent, seconds, release_shown):
        until = min(self.clock.now() + max(5, min(60, int(seconds))), self.own_end(agent))
        ev = self.transport.arrival[agent]
        if len(self.transport.inbox[agent]) > self.seen[agent]:
            return
        ev.clear()
        waits = [asyncio.ensure_future(self.clock.sleep_until(until)), asyncio.ensure_future(ev.wait())]
        if not release_shown:
            waits.append(asyncio.ensure_future(self.released.wait()))
        _, pending = await asyncio.wait(waits, return_when=asyncio.FIRST_COMPLETED)
        for p in pending:
            p.cancel()

    async def agent_loop(self, agent):
        task = asyncio.ensure_future(super().agent_loop(agent))
        stop = asyncio.ensure_future(self.clock.sleep_until(self.own_end(agent)))
        await asyncio.wait([task, stop], return_when=asyncio.FIRST_COMPLETED)
        if not task.done():
            task.cancel()
            self.log("agent_stopped", actor=agent, reason="own end reached")
        stop.cancel()

    def write_manifest(self):
        super().write_manifest()
        (self.out / "deadlines.json").write_text(json.dumps(
            {"layout": self._base.extra["layout"], "tight_positions": sorted(self.tight), "deadline": self.D},
            indent=1))

    def write_results(self):
        rows = super().write_results()
        for a, row in rows.items():
            p2 = row["p2"]
            row["deadline"] = self.D[a]
            row["tight"] = self.D[a] == self._base.extra["d_tight"]
            row["p2_on_time"] = bool(p2 and p2["correct"] and p2["t"] - self._base.prep_seconds <= self.D[a])
        (self.out / "results.json").write_text(json.dumps(rows, indent=1))
        return rows
