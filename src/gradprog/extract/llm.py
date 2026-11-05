"""The LLM call as an interface, so everything else runs without the API (08 §1)."""

from dataclasses import dataclass, field


class LLMCallFailed(Exception):
    """The API failed after the SDK's own retries (08 §2.1)."""

    def __init__(self, reason, usage=None):
        super().__init__(reason)
        self.reason = reason
        self.usage = usage or {}


@dataclass
class LLMResult:
    text: str
    stop_reason: str
    model: str
    request_id: str = ""
    usage: dict = field(default_factory=dict)


def cost_usd(usage, prices):
    """USD for one call. `usage` holds input, cache_write, cache_read and output token counts."""
    return sum(usage.get(k, 0) * prices[k] for k in ("input", "cache_write", "cache_read", "output")) / 1_000_000
