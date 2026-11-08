"""Agent policies. act(observation, tools) -> (tool_name | None, args, meta)."""
import asyncio
import json

from adaption_client import AdaptionClient, function_calls, reasoning_text


class LLMAgent:
    """Adaption Responses API agent. Context persists for the whole episode.

    Only the first function call of a reply is executed; extras get a rejection output.
    Reasoning items are not replayed (they are logged in the request log).
    """
    def __init__(self, name, episode, client=None):
        self.name = name
        self.ep = episode
        self.client = client or AdaptionClient(log_path=episode.out / "requests.jsonl")
        self.history = []
        self.pending_call_id = None

    def _append_observation(self, obs):
        if self.pending_call_id:
            self.history.append({"type": "function_call_output", "call_id": self.pending_call_id, "output": obs})
            self.pending_call_id = None
        else:
            self.history.append({"role": "user", "content": obs})

    async def act(self, obs, tools):
        self._append_observation(obs)
        cfg = self.ep.cfg
        payload = {"model": cfg.model, "instructions": self.ep.system_prompt(self.name), "input": self.history,
                   "tools": tools, "temperature": cfg.temperature, "max_output_tokens": cfg.max_output_tokens}
        t_req = self.ep.clock.now()
        data, _ = await asyncio.to_thread(self.client.create, payload, self.name)
        t_resp = self.ep.clock.now()
        usage = data.get("usage") or {}
        meta = {"t_request": round(t_req, 3), "t_response": round(t_resp, 3),
                "latency": round(t_resp - t_req, 3), "status": data.get("status"),
                "out_tokens": usage.get("output_tokens"),
                "reasoning_tokens": (usage.get("output_tokens_details") or {}).get("reasoning_tokens"),
                "reasoning": reasoning_text(data)[:6000]}
        text = "".join(c.get("text", "") for o in data.get("output", []) if o.get("type") == "message"
                       for c in o.get("content") or [] if isinstance(c, dict))
        if text:
            self.history.append({"role": "assistant", "content": text})
            meta["text"] = text[:2000]
        calls = function_calls(data)
        if not calls:
            return None, {}, meta
        for i, c in enumerate(calls):
            self.history.append({"type": "function_call", "call_id": c["call_id"], "name": c["name"],
                                 "arguments": c.get("arguments") or "{}"})
            if i > 0:
                self.history.append({"type": "function_call_output", "call_id": c["call_id"],
                                     "output": "rejected: only one tool call per turn is executed."})
        first = calls[0]
        self.pending_call_id = first["call_id"]
        meta["n_calls"] = len(calls)
        try:
            args = json.loads(first.get("arguments") or "{}")
        except json.JSONDecodeError:
            args, meta["bad_json"] = {}, True
        return first["name"], args, meta


class ScriptedAgent:
    """Deterministic policy for offline tests: a list of (tool, args) steps, then wait."""
    def __init__(self, name, episode, steps):
        self.name = name
        self.ep = episode
        self.steps = list(steps)
        self.observations = []

    async def act(self, obs, tools):
        self.observations.append(obs)
        await asyncio.sleep(0)
        while self.steps and isinstance(self.steps[0], tuple) and self.steps[0][0] == "_until":  # scripted pause until an episode time
            await self.ep.clock.sleep_until(self.steps.pop(0)[1])
        if self.steps:
            step = self.steps.pop(0)
            if callable(step):
                step = step(self, obs)
            if step is not None:
                return step[0], step[1], {"scripted": True}
        return "wait", {"seconds": 60}, {"scripted": True}
