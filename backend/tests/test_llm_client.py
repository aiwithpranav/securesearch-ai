"""Phase 6A: the OpenAI client, tested with a fake network (no key, no internet, no cost)."""
import json

import httpx
import pytest

from app.core.config import settings
from app.llm import LlmError, LlmNotConfigured, get_llm, set_llm
from app.llm.openai_client import OpenAiClient

KEY = "sk-test-not-a-real-key-0123456789"


def client_for(handler, **kw):
    return OpenAiClient(KEY, "gpt-4o-mini", transport=httpx.MockTransport(handler), **kw)


def ok_response(text='{"can_answer": false, "answer": "", "citations": []}'):
    return httpx.Response(200, json={"choices": [{"message": {"content": text}}], "usage": {"prompt_tokens": 120, "completion_tokens": 30}})


def test_the_request_is_safe_and_cheap():
    seen = {}

    def handler(request):
        seen["body"] = json.loads(request.content)
        seen["auth"] = request.headers["authorization"]
        seen["url"] = str(request.url)
        return ok_response()

    result = client_for(handler).complete("SYSTEM", "USER", 321)
    body = seen["body"]
    assert seen["url"] == "https://api.openai.com/v1/chat/completions" and seen["auth"] == f"Bearer {KEY}"
    assert body["model"] == "gpt-4o-mini" and body["temperature"] == 0 and body["max_tokens"] == 321
    assert body["response_format"] == {"type": "json_object"}
    assert [m["role"] for m in body["messages"]] == ["system", "user"]
    assert "tools" not in body and "functions" not in body and "tool_choice" not in body  # the model gets no tools
    assert (result.input_tokens, result.output_tokens) == (120, 30)


def test_the_key_is_never_in_repr_or_in_errors():
    c = client_for(lambda r: httpx.Response(401, text=f"bad key {KEY}"))
    assert KEY not in repr(c)
    with pytest.raises(LlmError) as err:
        c.complete("s", "u", 10)
    assert KEY not in str(err.value) and "bad key" not in str(err.value) and str(err.value) == "auth"


@pytest.mark.parametrize("status, code", [(401, "auth"), (403, "auth"), (400, "unavailable"), (404, "unavailable")])
def test_error_statuses_become_short_code_words(status, code):
    with pytest.raises(LlmError, match=f"^{code}$"):
        client_for(lambda r: httpx.Response(status, text="body that must not be copied")).complete("s", "u", 10)


def test_a_busy_service_is_retried_once_then_succeeds(monkeypatch):
    monkeypatch.setattr("app.llm.openai_client.time.sleep", lambda s: None)
    calls = []

    def handler(request):
        calls.append(1)
        return httpx.Response(429, headers={"retry-after": "0"}) if len(calls) == 1 else ok_response()

    assert client_for(handler).complete("s", "u", 10).text
    assert len(calls) == 2


@pytest.mark.parametrize("status, code", [(429, "rate_limited"), (503, "unavailable")])
def test_a_service_that_stays_busy_fails_after_one_retry(monkeypatch, status, code):
    monkeypatch.setattr("app.llm.openai_client.time.sleep", lambda s: None)
    calls = []

    def handler(request):
        calls.append(1)
        return httpx.Response(status)

    with pytest.raises(LlmError, match=f"^{code}$"):
        client_for(handler).complete("s", "u", 10)
    assert len(calls) == 2  # never a retry storm (cost and rate limits)


def test_timeouts_and_network_errors_are_short_code_words():
    def slow(request):
        raise httpx.ReadTimeout("slow")

    def down(request):
        raise httpx.ConnectError("no route")

    with pytest.raises(LlmError, match="^timeout$"):
        client_for(slow).complete("s", "u", 10)
    with pytest.raises(LlmError, match="^unavailable$"):
        client_for(down).complete("s", "u", 10)


@pytest.mark.parametrize("payload", [{}, {"choices": []}, {"choices": [{"message": {}}]}, {"choices": [{"message": {"content": 5}}]}])
def test_a_reply_in_the_wrong_shape_is_a_clean_error(payload):
    with pytest.raises(LlmError, match="^bad_response$"):
        client_for(lambda r: httpx.Response(200, json=payload)).complete("s", "u", 10)


def test_without_a_key_the_model_is_not_configured(monkeypatch):
    set_llm(None)
    for value in ("", "CHANGE_ME"):
        monkeypatch.setattr(settings, "openai_api_key", value)
        with pytest.raises(LlmNotConfigured):
            get_llm()


def test_with_a_key_the_real_client_is_built_and_can_be_replaced_in_tests(monkeypatch):
    set_llm(None)
    monkeypatch.setattr(settings, "openai_api_key", KEY)
    c = get_llm()
    assert isinstance(c, OpenAiClient) and KEY not in repr(c)
    set_llm(None)
