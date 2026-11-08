"""Minimal client for Adaption's Responses API. Never logs headers or the API key."""
import json
import os
import time
from pathlib import Path

import requests

BASE_URL = "https://api.prod.adaptionlabs.ai/api/v1"
RETRY_STATUS = {429, 500, 502, 503, 504}
RETRY_DELAYS = (3, 10, 30)


def load_key():
    key = os.getenv("ADAPTION_API_KEY", "").strip()
    if not key:
        env = Path(__file__).resolve().parents[2] / ".env"
        for line in env.read_text(encoding="utf-8-sig").splitlines():
            if line.startswith("ADAPTION_API_KEY="):
                key = line.split("=", 1)[1].strip()
    if not key:
        raise RuntimeError("ADAPTION_API_KEY missing; no request sent")
    return key


class AdaptionClient:
    def __init__(self, log_path=None, timeout=180):
        self.session = requests.Session()
        self.session.headers["Authorization"] = "Bearer " + load_key()
        self.log_path = Path(log_path) if log_path else None
        self.timeout = timeout

    def _log(self, record):
        if self.log_path:
            self.log_path.parent.mkdir(parents=True, exist_ok=True)
            with self.log_path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")

    def list_models(self):
        r = self.session.get(BASE_URL + "/models", params={"type": "hosted"}, timeout=60)
        r.raise_for_status()
        return r.json()

    def create(self, payload, actor=None):
        """POST /responses with infrastructure retries. Returns (data, timing)."""
        for attempt in range(len(RETRY_DELAYS) + 1):
            t0 = time.monotonic()
            record = {"actor": actor, "attempt": attempt, "request": payload, "t_start": t0}
            try:
                r = self.session.post(BASE_URL + "/responses", json=payload, timeout=self.timeout)
                status, error = r.status_code, None
            except (requests.Timeout, requests.ConnectionError) as exc:
                r, status, error = None, None, type(exc).__name__
            t1 = time.monotonic()
            record.update(t_end=t1, elapsed=t1 - t0, http_status=status, transport_error=error)
            ok = r is not None and r.ok
            if ok:
                record["response"] = data = r.json()
            elif r is not None:
                record["error_body"] = r.text[:2000]
            retry = (error is not None or status in RETRY_STATUS) and attempt < len(RETRY_DELAYS)
            record["retrying"] = retry
            self._log(record)
            if ok:
                return data, {"t_start": t0, "t_end": t1, "attempts": attempt + 1}
            if not retry:
                raise RuntimeError(f"Adaption request failed: HTTP {status} {error or ''}".strip())
            time.sleep(RETRY_DELAYS[attempt])


def function_calls(data):
    return [o for o in data.get("output", []) if o.get("type") == "function_call"]


def reasoning_text(data):
    parts = []
    for o in data.get("output", []):
        if o.get("type") == "reasoning":
            parts += [s.get("text", "") for s in o.get("summary") or []]
            parts += [c.get("text", "") for c in o.get("content") or [] if isinstance(c, dict)]
    return "\n".join(p for p in parts if p)
