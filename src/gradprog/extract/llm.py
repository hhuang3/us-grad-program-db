"""The LLM call as an interface, so everything else runs without the API (08 §1)."""

from dataclasses import dataclass, field

import anthropic


class LLMCallFailed(Exception):
    """The API failed after the retries, or with an error no retry helps (08 §2.1)."""

    def __init__(self, reason, usage=None):
        super().__init__(reason)
        self.reason = reason
        self.usage = usage or {}


class LLMSetupError(ValueError):
    """The request itself is unusable (bad key, no credit, rejected schema): no page is at fault, so the run stops."""


@dataclass
class LLMResult:
    text: str
    stop_reason: str
    model: str
    request_id: str = ""
    usage: dict = field(default_factory=dict)


MAX_RETRIES = 3   # 08 §2.1: the SDK backs off on 408, 409, 429, 5xx and connection errors


def cost_usd(usage, prices):
    """USD for one call. `usage` holds input, cache_write, cache_read and output token counts."""
    return sum(usage.get(k, 0) * prices[k] for k in ("input", "cache_write", "cache_read", "output")) / 1_000_000


def _usage(response):
    u = response.usage
    return {"input": u.input_tokens or 0, "cache_write": u.cache_creation_input_tokens or 0,
            "cache_read": u.cache_read_input_tokens or 0, "output": u.output_tokens or 0}


class AnthropicClient:
    """One Messages call. No sampling parameters: the API rejects them (08 §1)."""

    def __init__(self, api_key, client=None):
        self.client = client or anthropic.Anthropic(api_key=api_key, max_retries=MAX_RETRIES)

    def extract(self, system, user, schema, settings):
        try:
            response = self.client.messages.create(
                model=settings["model"],
                max_tokens=settings["max_tokens"],
                system=[{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
                messages=[{"role": "user", "content": user}],
                output_config={"effort": settings["effort"], "format": {"type": "json_schema", "schema": schema}},
            )
        except (anthropic.BadRequestError, anthropic.AuthenticationError, anthropic.PermissionDeniedError,
                anthropic.NotFoundError) as e:
            raise LLMSetupError(f"API rejected the request: {type(e).__name__} (HTTP {e.status_code})") from None
        except anthropic.APIStatusError as e:
            raise LLMCallFailed(f"{type(e).__name__} (HTTP {e.status_code})") from None
        except anthropic.APIConnectionError as e:
            raise LLMCallFailed(type(e).__name__) from None
        text = next((b.text for b in response.content if b.type == "text"), "")   # thinking blocks may come first
        return LLMResult(text, response.stop_reason, response.model, response._request_id or "", _usage(response))
