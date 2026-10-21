"""OpenAI chat completions over plain HTTPS (GPT-4o mini by default).

Safety rules for this file:
- The key is used only in the Authorization header. It is never logged, never put in an error message and never
  appears in repr() of this object.
- Errors are short code words (timeout, rate_limited, unavailable, auth, bad_response). Response bodies are not
  copied anywhere, because they could echo prompt text.
- The model gets no tools and no functions. Temperature 0, JSON output, a hard output token cap."""
import time

import httpx

from app.llm.base import LlmError, LlmResult

_RETRY_STATUS = {429, 500, 502, 503, 504}


class OpenAiClient:
    def __init__(
        self, api_key: str, model: str, base_url: str = "https://api.openai.com/v1", timeout_seconds: int = 30,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._api_key = api_key
        self.model = model
        self._url = base_url.rstrip("/") + "/chat/completions"
        self._http = httpx.Client(timeout=timeout_seconds, transport=transport)

    def __repr__(self) -> str:  # never show the key
        return f"OpenAiClient(model={self.model!r})"

    def complete(self, system: str, user: str, max_output_tokens: int) -> LlmResult:
        payload = {
            "model": self.model,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            "temperature": 0,
            "max_tokens": max_output_tokens,
            "response_format": {"type": "json_object"},
        }
        headers = {"Authorization": f"Bearer {self._api_key}", "Content-Type": "application/json"}
        response: httpx.Response | None = None
        for attempt in range(2):  # one retry for a busy or briefly failing service
            try:
                response = self._http.post(self._url, json=payload, headers=headers)
            except httpx.TimeoutException:
                raise LlmError("timeout") from None
            except httpx.HTTPError:
                raise LlmError("unavailable") from None
            if response.status_code in _RETRY_STATUS and attempt == 0:
                wait = response.headers.get("retry-after", "1")
                time.sleep(min(float(wait) if wait.replace(".", "", 1).isdigit() else 1.0, 2.0))
                continue
            break
        assert response is not None
        if response.status_code in (401, 403):
            raise LlmError("auth")
        if response.status_code == 429:
            raise LlmError("rate_limited")
        if response.status_code >= 400:
            raise LlmError("unavailable")
        try:
            data = response.json()
            text = data["choices"][0]["message"]["content"]
            usage = data.get("usage") or {}
            if not isinstance(text, str):
                raise TypeError
            return LlmResult(text, int(usage.get("prompt_tokens", 0)), int(usage.get("completion_tokens", 0)))
        except (ValueError, KeyError, IndexError, TypeError):
            raise LlmError("bad_response") from None
