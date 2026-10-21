import json
import urllib.error
import urllib.request
from collections.abc import Callable

from app.core.settings import settings

Sender = Callable[[dict], dict]


class LlmError(RuntimeError):
    """The language model could not produce a usable answer."""


def json_object(text: str) -> dict:
    body = text.strip()
    if body.startswith("```"):
        _, _, body = body.partition("\n")
        body = body.rstrip().removesuffix("```")

    try:
        value = json.loads(body)
    except json.JSONDecodeError:
        start, end = body.find("{"), body.rfind("}")
        if start == -1 or end <= start:
            raise LlmError("Model reply contained no JSON object") from None
        try:
            value = json.loads(body[start : end + 1])
        except json.JSONDecodeError as exc:
            raise LlmError(f"Model reply was not valid JSON: {exc}") from exc

    if not isinstance(value, dict):
        raise LlmError("Model reply was JSON but not an object")
    return value


def post_messages(url: str, payload: dict, api_key: str, timeout: float) -> dict:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode(),
        headers={
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")[:500]
        raise LlmError(f"LLM returned HTTP {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise LlmError(f"Could not reach the LLM: {exc.reason}") from exc


class MessagesClient:
    """Calls a Messages-compatible endpoint and returns the text blocks joined.

    The sender is injectable so tests never touch the network.
    """

    def __init__(self, sender: Sender | None = None) -> None:
        self._sender = sender or self._send

    def _send(self, payload: dict) -> dict:
        if not settings.anthropic_base_url or not settings.anthropic_api_key:
            raise LlmError("anthropic_base_url and anthropic_api_key must be set")
        url = settings.anthropic_base_url.rstrip("/") + "/v1/messages"
        return post_messages(
            url, payload, settings.anthropic_api_key, settings.llm_timeout_seconds
        )

    def complete(self, system: str, user: str) -> str:
        reply = self._sender(
            {
                "model": settings.llm_model,
                "max_tokens": settings.llm_max_tokens,
                "system": system,
                "messages": [{"role": "user", "content": user}],
            }
        )
        text = "".join(
            block.get("text", "")
            for block in reply.get("content", [])
            if block.get("type") == "text"
        )
        if not text.strip():
            raise LlmError("Model reply contained no text block")
        return text
