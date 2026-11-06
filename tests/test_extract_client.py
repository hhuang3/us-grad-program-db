"""docs/spec/08_extraction.md §1, §2.1: the Anthropic client, against a stand-in for the SDK. No network."""

from types import SimpleNamespace as NS

import anthropic
import httpx2
import pytest

from gradprog.extract.llm import AnthropicClient, LLMCallFailed, LLMSetupError

SETTINGS = {"model": "claude-haiku-5-5", "max_tokens": 16000, "effort": "medium"}
REQUEST = httpx2.Request("POST", "https://example.invalid/v1/messages")


def response(content=None, stop="end_turn"):
    usage = NS(input_tokens=10, cache_creation_input_tokens=20, cache_read_input_tokens=None, output_tokens=5)
    return NS(content=content or [NS(type="text", text="{}")], stop_reason=stop, model="claude-haiku-5-5",
              usage=usage, _request_id="req_1")


class Sdk:
    def __init__(self, result):
        self.result, self.kwargs = result, None
        self.messages = self

    def create(self, **kwargs):
        self.kwargs = kwargs
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


def status_error(cls, code):
    return cls("page text must not leak", response=httpx2.Response(code, request=REQUEST), body=None)


def call(result):
    sdk = Sdk(result)
    return AnthropicClient("key", client=sdk).extract("sys", "user", {"type": "object"}, SETTINGS), sdk


def test_request_shape():
    _, sdk = call(response())
    k = sdk.kwargs
    assert k["model"] == "claude-haiku-5-5" and k["max_tokens"] == 16000
    assert k["output_config"] == {"effort": "medium", "format": {"type": "json_schema", "schema": {"type": "object"}}}
    assert k["system"] == [{"type": "text", "text": "sys", "cache_control": {"type": "ephemeral"}}]
    assert k["messages"] == [{"role": "user", "content": "user"}]


def test_no_sampling_parameters_are_sent():
    _, sdk = call(response())
    assert not {"temperature", "top_p", "top_k", "thinking", "fallbacks"} & set(sdk.kwargs)


def test_result_skips_thinking_blocks_and_maps_usage():
    result, _ = call(response([NS(type="thinking", thinking=""), NS(type="text", text='{"a":1}')]))
    assert result.text == '{"a":1}'
    assert result.usage == {"input": 10, "cache_write": 20, "cache_read": 0, "output": 5}
    assert (result.stop_reason, result.model, result.request_id) == ("end_turn", "claude-haiku-5-5", "req_1")


@pytest.mark.parametrize("stop", ["refusal", "max_tokens"])
def test_stop_reasons_reach_the_pipeline(stop):
    assert call(response(stop=stop))[0].stop_reason == stop


@pytest.mark.parametrize("cls,code", [(anthropic.RateLimitError, 429), (anthropic.InternalServerError, 500)])
def test_retryable_errors_fail_this_call_only(cls, code):
    with pytest.raises(LLMCallFailed) as e:
        call(status_error(cls, code))
    assert str(code) in e.value.reason and "page text" not in e.value.reason


def test_connection_errors_fail_this_call_only():
    with pytest.raises(LLMCallFailed):
        call(anthropic.APIConnectionError(request=REQUEST))


@pytest.mark.parametrize("cls,code", [(anthropic.BadRequestError, 400), (anthropic.AuthenticationError, 401),
                                      (anthropic.PermissionDeniedError, 403), (anthropic.NotFoundError, 404)])
def test_request_problems_stop_the_run(cls, code):
    with pytest.raises(LLMSetupError) as e:
        call(status_error(cls, code))
    assert "page text" not in str(e.value)
