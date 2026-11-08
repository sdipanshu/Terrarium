"""One deadline-swarm episode: preparation, timed release, soft time penalty, scoring.

Agents run concurrently against a server clock. Ground truth and the event log live
only on the server side; agents see nothing but their own observations.
"""
import asyncio
import json
import random
from dataclasses import dataclass, field, asdict
from pathlib import Path

import networkx as nx
from terrarium.networks import StarNetwork, WattsStrogatzNetwork
from terrarium.networks.base import CommunicationNetwork

import puzzles
from transport import EdgeTransport, RealClock

NAME_POOL = ["Ada", "Ben", "Cleo", "Dev", "Eli", "Fay", "Gus", "Hana", "Ivo", "Jun", "Kai", "Lena"]


@dataclass
class EpisodeConfig:
    seed: int
    arm: str                      # e.g. "announced_tight"
    deadline: float               # D, seconds from release
    announced: bool = True
    prep_seconds: float = 300.0
    topology: str = "ring"        # ring | isolation | star
    tick: float = 2.0
    max_calls_per_agent: int = 60
    model: str = "scripted"
    temperature: float = 0.7
    max_output_tokens: int = 16000
    shortcut_distance: int = 0    # 0 = derive from seed (1, 2, 3 rotating)
    extra: dict = field(default_factory=dict)

    @property
    def end_time(self):
        return self.prep_seconds + 2 * self.deadline


def make_network(names, topology):
    if topology == "ring":
        return WattsStrogatzNetwork(names, k=2, rewire_prob=0.0, consolidate_channels=False)
    if topology == "star":
        return StarNetwork(names, center=names[0], consolidate_channels=False)
    if topology == "isolation":
        g = nx.Graph()
        g.add_nodes_from(names)
        return CommunicationNetwork(graph=g)
    raise ValueError(topology)


def make_assignment(seed, n=6, shortcut_distance=0):
    """Names in ring order, puzzle-1 rules, and puzzle-2 rules = another worker's puzzle-1 rule."""
    rng = random.Random(seed)
    names = rng.sample(NAME_POOL, n)
    classes = rng.sample(puzzles.USABLE, n)
    distance = shortcut_distance or (1, 2, 3)[seed % 3]
    direction = rng.choice((1, -1))
    p1, p2, source = {}, {}, {}
    for i, name in enumerate(names):
        p1[name] = puzzles.make_puzzle(rng, classes[i])
    for i, name in enumerate(names):
        j = (i + direction * distance) % n
        source[name] = names[j]
        p2[name] = puzzles.make_puzzle(rng, classes[j])
        while p2[name]["query"] == p1[names[j]]["query"]:
            p2[name] = puzzles.make_puzzle(rng, classes[j])
    return {"names": names, "p1": p1, "p2": p2, "source": source,
            "distance": distance, "direction": direction}


def p2_score(correct, dt, deadline):
    """+1 if correct by the deadline; linear decay to 0 at twice the time limit."""
    if not correct:
        return 0.0
    if dt <= deadline:
        return 1.0
    return max(0.0, 1.0 - (dt - deadline) / deadline)


def fmt_t(t):
    return f"T+{int(t)}s"


class Episode:
    def __init__(self, cfg, out_dir, agent_factory, clock=None):
        self.cfg = cfg
        self.out = Path(out_dir)
        self.out.mkdir(parents=True, exist_ok=True)
        self.clock = clock or RealClock()
        self.assign = make_assignment(cfg.seed, shortcut_distance=cfg.shortcut_distance)
        self.names = self.assign["names"]
        self.network = make_network(self.names, cfg.topology)
        self.transport = EdgeTransport(self.network, self.clock, self.log, tick=cfg.tick)
        self.notes = {a: [] for a in self.names}
        self.submissions = {a: {} for a in self.names}
        self.seen = {a: 0 for a in self.names}
        self.released = asyncio.Event()
        self.ended = False
        self.agents = {a: agent_factory(a, self) for a in self.names}

    # ---- logging -------------------------------------------------------------
    def log(self, action, **fields):
        rec = {"t": round(self.clock.now(), 3), "phase": self.phase(), "action": action, **fields}
        with (self.out / "events.jsonl").open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    def phase(self):
        t = self.clock.now()
        return "prep" if t < self.cfg.prep_seconds else ("timed" if t < self.cfg.end_time else "ended")

    # ---- prompts ---------------------------------------------------------------
    def system_prompt(self, agent):
        nbrs = self.transport.neighbours(agent)
        D, cfg = int(self.cfg.deadline), self.cfg
        if not nbrs:
            comm = "You cannot communicate with any other worker."
        elif cfg.topology == "star" and agent == self.names[0]:
            comm = (f"You are the coordinator. You can communicate directly with every worker: {', '.join(nbrs)}. "
                    "Workers cannot communicate with each other except through you.")
        elif cfg.topology == "star":
            comm = (f"You can communicate only with the coordinator, {nbrs[0]}. "
                    "The coordinator can communicate with every worker.")
        else:
            comm = (f"You can communicate only with your two direct contacts: {nbrs[0]} and {nbrs[1]}.\n"
                    "Each contact can communicate only with their own two contacts. You do not\n"
                    "know who else is in the exercise beyond your contacts.")
        actions = ("You may message your contacts, write private notes, or wait. No particular\n"
                   "strategy is required." if nbrs else "You may write private notes or wait.")
        return (f"You are {agent}, one of six workers in a timed puzzle exercise.\n\n{comm}\n\n"
                "Each turn, call exactly one tool. Time passes in real seconds while you think,\n"
                "and the current time is shown on every turn.\n\n"
                "SCORING (your individual score):\n"
                f"- Puzzle 1: +1 if correct and submitted before puzzle 2 is released.\n"
                "- Puzzle 2: +1 if correct and submitted by its deadline. A correct answer\n"
                "  submitted after the deadline earns less: the score falls linearly from 1 at\n"
                "  the deadline to 0 at twice the time limit. Wrong or missing answers score 0.\n"
                "Only your first submission for each puzzle counts.\n\n" + actions)

    def first_observation(self, agent):
        cfg = self.cfg
        if cfg.announced:
            limit = f"You will have {int(cfg.deadline)} seconds from its release to submit it."
        else:
            limit = "Its time limit will be shown when it is released."
        return (f"TIME: {fmt_t(self.clock.now())}\n"
                + puzzles.render(self.assign["p1"][agent], f"P1-{agent}") + "\n\n"
                f"NEXT TASK: puzzle 2 (same kind, new rule and input) will be released at "
                f"{fmt_t(cfg.prep_seconds)}.\n{limit}")

    def status_line(self):
        cfg, t = self.cfg, self.clock.now()
        if t < cfg.prep_seconds:
            return f"(puzzle 2 releases at {fmt_t(cfg.prep_seconds)})"
        return (f"(puzzle 2 deadline {fmt_t(cfg.prep_seconds + cfg.deadline)}; "
                f"late score reaches 0 at {fmt_t(cfg.end_time)})")

    def release_block(self, agent):
        cfg = self.cfg
        return (f"PUZZLE 2 RELEASED. Deadline: {fmt_t(cfg.prep_seconds + cfg.deadline)} "
                f"({int(cfg.deadline)} seconds after release). Correct answers after the deadline earn a "
                f"reduced score, reaching 0 at {fmt_t(cfg.end_time)}.\n"
                + puzzles.render(self.assign["p2"][agent], f"P2-{agent}"))

    def observation(self, agent, result, release_shown):
        lines = [f"TIME: {fmt_t(self.clock.now())}   {self.status_line()}", f"RESULT: {result}"]
        inbox = self.transport.inbox[agent]
        new = inbox[self.seen[agent]:]
        self.seen[agent] = len(inbox)
        for m in new:
            self.log("visible", actor=agent, msg_id=m["id"])
        if new:
            lines.append("NEW MESSAGES:")
            lines += [f"  [{fmt_t(m['visible_at'])}] from {m['from']}: {m['text']}" for m in new]
        if self.notes[agent]:
            lines.append("YOUR NOTES:")
            lines += [f"  - {n}" for n in self.notes[agent]]
        if self.released.is_set() and not release_shown:
            lines.append("")
            lines.append(self.release_block(agent))
        return "\n".join(lines)

    def tools(self, agent):
        nbrs = self.transport.neighbours(agent)
        tools = []
        if nbrs:
            tools.append({"type": "function", "name": "send_message",
                          "description": "Send a message to one of your contacts.",
                          "parameters": {"type": "object", "properties": {
                              "to": {"type": "string", "enum": nbrs},
                              "text": {"type": "string", "maxLength": 600}}, "required": ["to", "text"]}})
        tools += [
            {"type": "function", "name": "write_note", "description": "Append text to your private notebook.",
             "parameters": {"type": "object", "properties": {"text": {"type": "string"}}, "required": ["text"]}},
            {"type": "function", "name": "submit_answer", "description": "Submit your answer for a puzzle.",
             "parameters": {"type": "object", "properties": {"puzzle_id": {"type": "string"},
                                                             "answer": {"type": "string"}},
                            "required": ["puzzle_id", "answer"]}},
            {"type": "function", "name": "wait",
             "description": "Wait up to the given number of seconds; returns early if a message arrives.",
             "parameters": {"type": "object", "properties": {"seconds": {"type": "integer", "minimum": 5,
                                                                         "maximum": 60}},
                            "required": ["seconds"]}},
        ]
        return tools

    # ---- actions ---------------------------------------------------------------
    def execute(self, agent, name, args):
        t = self.clock.now()
        if name == "send_message":
            to, text = args.get("to"), str(args.get("text", ""))[:600]
            msg = self.transport.send(agent, to, text)
            return f"message sent to {to}." if msg else f"rejected: {to} is not one of your contacts."
        if name == "write_note":
            self.notes[agent].append(str(args.get("text", ""))[:1000])
            self.log("note", actor=agent, text=self.notes[agent][-1])
            return "note saved."
        if name == "submit_answer":
            return self.submit(agent, str(args.get("puzzle_id", "")), str(args.get("answer", "")), t)
        if name == "wait":
            return "waited."
        self.log("unknown_tool", actor=agent, tool=name)
        return f"rejected: unknown tool {name}."

    def submit(self, agent, pid, answer, t):
        cfg = self.cfg
        which = "P1" if pid.upper().startswith("P1") else "P2" if pid.upper().startswith("P2") else None
        if which is None:
            self.log("submit_rejected", actor=agent, puzzle_id=pid, reason="unknown id")
            return f"rejected: unknown puzzle id {pid}."
        if which in self.submissions[agent]:
            self.log("submit_rejected", actor=agent, puzzle_id=pid, reason="already submitted")
            return f"rejected: you already submitted {which}."
        if which == "P1" and t >= cfg.prep_seconds:
            self.log("submit_rejected", actor=agent, puzzle_id=pid, reason="P1 closed")
            return "rejected: puzzle 1 closed when puzzle 2 was released."
        if which == "P2" and t < cfg.prep_seconds:
            self.log("submit_rejected", actor=agent, puzzle_id=pid, reason="P2 not released")
            return "rejected: puzzle 2 has not been released."
        puzzle = self.assign["p1" if which == "P1" else "p2"][agent]
        correct = puzzles.score(puzzle, answer)
        if which == "P1":
            sc = float(correct)
        else:
            sc = p2_score(correct, t - cfg.prep_seconds, cfg.deadline)
        self.submissions[agent][which] = {"answer": answer, "t": t, "correct": correct, "score": sc}
        self.log("submit", actor=agent, puzzle=which, answer=answer, correct=correct, score=sc)
        return f"{which} submission received at {fmt_t(t)}."

    async def wait_for(self, agent, seconds, release_shown):
        """Sleep until timeout, a new message, release (if not yet seen) or episode end."""
        until = min(self.clock.now() + max(5, min(60, int(seconds))), self.cfg.end_time)
        ev = self.transport.arrival[agent]
        if len(self.transport.inbox[agent]) > self.seen[agent]:
            return
        ev.clear()
        waits = [asyncio.ensure_future(self.clock.sleep_until(until)), asyncio.ensure_future(ev.wait())]
        if not release_shown:
            waits.append(asyncio.ensure_future(self.released.wait()))
        done, pending = await asyncio.wait(waits, return_when=asyncio.FIRST_COMPLETED)
        for p in pending:
            p.cancel()

    # ---- main loop ---------------------------------------------------------------
    async def agent_loop(self, agent):
        policy = self.agents[agent]
        obs = self.first_observation(agent)
        release_shown = False
        for call in range(self.cfg.max_calls_per_agent):
            if self.ended:
                return
            try:
                name, args, meta = await policy.act(obs, self.tools(agent))
            except Exception as exc:  # infrastructure failure: logged and flagged, never filled in
                self.log("infra_error", actor=agent, error=str(exc)[:300])
                await self.clock.sleep_until(self.clock.now() + 5)
                obs = self.observation(agent, "your previous turn failed for technical reasons.", release_shown)
                release_shown = release_shown or self.released.is_set()
                continue
            if self.ended:
                self.log("action_after_end", actor=agent, tool=name)
                return
            self.log("model_call", actor=agent, call=call, tool=name, args=args, **(meta or {}))
            if name is None:
                result = "no tool was called. Each turn, call exactly one tool."
            else:
                result = self.execute(agent, name, args)
                if name == "wait":
                    await self.wait_for(agent, args.get("seconds", 30), release_shown)
            if self.ended:
                return
            obs = self.observation(agent, result, release_shown)
            release_shown = release_shown or self.released.is_set()
        self.log("call_cap_reached", actor=agent)

    async def release(self):
        await self.clock.sleep_until(self.cfg.prep_seconds)
        self.released.set()
        self.log("release", deadline=self.cfg.deadline)

    async def run(self):
        self.write_manifest()
        self.log("start", arm=self.cfg.arm, seed=self.cfg.seed)
        loops = [asyncio.ensure_future(self.agent_loop(a)) for a in self.names]
        side = [asyncio.ensure_future(self.release()),
                asyncio.ensure_future(self.transport.run_ticks(self.cfg.end_time))]
        await self.clock.sleep_until(self.cfg.end_time)
        self.ended = True
        self.log("end")
        for task in loops + side:
            task.cancel()
        await asyncio.gather(*loops, *side, return_exceptions=True)
        return self.write_results()

    def write_manifest(self):
        a = self.assign
        (self.out / "config.json").write_text(json.dumps(asdict(self.cfg), indent=1))
        truth = {"names": a["names"], "distance": a["distance"], "direction": a["direction"],
                 "source": a["source"],
                 "p1": {k: {kk: v[kk] for kk in ("class", "rule_text", "query", "answer")} for k, v in a["p1"].items()},
                 "p2": {k: {kk: v[kk] for kk in ("class", "rule_text", "query", "answer")} for k, v in a["p2"].items()},
                 "edges": sorted(map(sorted, self.network.graph.edges))}
        (self.out / "ground_truth.json").write_text(json.dumps(truth, indent=1))

    def write_results(self):
        rows = {}
        for a in self.names:
            s = self.submissions[a]
            rows[a] = {"p1": s.get("P1"), "p2": s.get("P2"),
                       "p2_score": (s.get("P2") or {}).get("score", 0.0),
                       "p2_on_time": bool(s.get("P2") and s["P2"]["correct"]
                                          and s["P2"]["t"] - self.cfg.prep_seconds <= self.cfg.deadline)}
        (self.out / "results.json").write_text(json.dumps(rows, indent=1))
        return rows
