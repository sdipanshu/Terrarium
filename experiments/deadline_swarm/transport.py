"""Edge-limited message transport on a Terrarium CommunicationNetwork.

A sent message crosses exactly one edge and becomes visible to the recipient at the
next delivery tick. Forwarding further is always the recipient's own action. There is
no global board, roster or bypass: an agent can only address its graph neighbours.
"""
import asyncio
import itertools
import math
import time


class RealClock:
    def __init__(self):
        self.t0 = time.monotonic()

    def now(self):
        return time.monotonic() - self.t0

    async def sleep_until(self, t):
        delay = t - self.now()
        if delay > 0:
            await asyncio.sleep(delay)


class FakeClock:
    """Controllable clock for offline tests: time advances only when told to."""
    def __init__(self):
        self.t = 0.0
        self._waiters = []

    def now(self):
        return self.t

    async def sleep_until(self, t):
        if t <= self.t:
            return
        fut = asyncio.get_running_loop().create_future()
        self._waiters.append((t, fut))
        await fut

    def advance(self, dt):
        self.t += dt
        for item in list(self._waiters):
            if item[0] <= self.t and not item[1].done():
                item[1].set_result(None)
                self._waiters.remove(item)


class EdgeTransport:
    def __init__(self, network, clock, log, tick=2.0):
        self.graph = network.graph
        self.clock = clock
        self.log = log
        self.tick = tick
        self.inbox = {a: [] for a in self.graph.nodes}      # delivered, visible messages
        self.pending = []                                   # (visible_at, message)
        self.ids = itertools.count(1)
        self.arrival = {a: asyncio.Event() for a in self.graph.nodes}

    def neighbours(self, agent):
        return sorted(self.graph.neighbors(agent))

    def send(self, sender, to, text):
        now = self.clock.now()
        if to not in self.neighbours(sender):
            self.log("send_rejected", actor=sender, recipient=to, reason="not a neighbour")
            return None
        visible_at = (math.floor(now / self.tick) + 1) * self.tick
        msg = {"id": next(self.ids), "from": sender, "to": to, "text": text,
               "sent_at": now, "visible_at": visible_at}
        self.pending.append(msg)
        self.log("send", actor=sender, recipient=to, msg_id=msg["id"], text=text, visible_at=visible_at)
        return msg

    def deliver_due(self):
        now = self.clock.now()
        due = [m for m in self.pending if m["visible_at"] <= now + 1e-9]
        for m in due:
            self.pending.remove(m)
            self.inbox[m["to"]].append(m)
            self.arrival[m["to"]].set()
            self.log("deliver", actor=m["to"], sender=m["from"], msg_id=m["id"])

    def read_direct(self, reader, owner):
        """Attempt to read another agent's inbox. Only an agent's own inbox is readable."""
        if reader != owner:
            self.log("read_rejected", actor=reader, target=owner)
            return None
        return list(self.inbox[owner])

    async def run_ticks(self, until):
        t = 0.0
        while t <= until:
            await self.clock.sleep_until(t)
            self.deliver_due()
            t += self.tick
