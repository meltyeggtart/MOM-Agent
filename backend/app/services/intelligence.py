import json
import urllib.error
import urllib.request
from collections.abc import Callable
from functools import lru_cache
from pathlib import Path
from typing import Protocol

from pydantic import ValidationError

from app.core.settings import settings
from app.schemas.insights import Insights

PROMPT_PATH = Path(__file__).resolve().parent.parent / "prompts" / "extraction.md"

Sender = Callable[[dict], dict]


class InsightExtractionError(RuntimeError):
    """The model did not return usable structured insights."""


class InsightExtractor(Protocol):
    def extract(self, transcript: str) -> Insights: ...


def load_prompt() -> str:
    return PROMPT_PATH.read_text(encoding="utf-8").strip()


def _json_object(text: str) -> dict:
    body = text.strip()
    if body.startswith("```"):
        _, _, body = body.partition("\n")
        body = body.rstrip().removesuffix("```")

    try:
        value = json.loads(body)
    except json.JSONDecodeError:
        start, end = body.find("{"), body.rfind("}")
        if start == -1 or end <= start:
            raise InsightExtractionError("Model reply contained no JSON object") from None
        try:
            value = json.loads(body[start : end + 1])
        except json.JSONDecodeError as exc:
            raise InsightExtractionError(f"Model reply was not valid JSON: {exc}") from exc

    if not isinstance(value, dict):
        raise InsightExtractionError("Model reply was JSON but not an object")
    return value


def _post_json(url: str, payload: dict, api_key: str, timeout: float) -> dict:
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
        raise InsightExtractionError(f"LLM returned HTTP {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise InsightExtractionError(f"Could not reach the LLM: {exc.reason}") from exc


class MessagesApiExtractor:
    """Talks the Anthropic Messages shape, which any compatible gateway accepts.

    The sender is injectable so tests never touch the network.
    """

    def __init__(self, sender: Sender | None = None) -> None:
        self._sender = sender or self._send

    def _send(self, payload: dict) -> dict:
        if not settings.anthropic_base_url or not settings.anthropic_api_key:
            raise InsightExtractionError(
                "anthropic_base_url and anthropic_api_key must be set"
            )
        url = settings.anthropic_base_url.rstrip("/") + "/v1/messages"
        return _post_json(
            url, payload, settings.anthropic_api_key, settings.llm_timeout_seconds
        )

    def extract(self, transcript: str) -> Insights:
        payload = {
            "model": settings.llm_model,
            "max_tokens": settings.llm_max_tokens,
            "system": load_prompt(),
            "messages": [{"role": "user", "content": transcript}],
        }
        reply = self._sender(payload)
        text = "".join(
            block.get("text", "")
            for block in reply.get("content", [])
            if block.get("type") == "text"
        )
        if not text.strip():
            raise InsightExtractionError("Model reply contained no text block")

        try:
            return Insights.model_validate(_json_object(text))
        except ValidationError as exc:
            raise InsightExtractionError(
                f"Model reply did not match the schema: {exc}"
            ) from exc


@lru_cache
def get_insight_extractor() -> InsightExtractor:
    if settings.llm_provider == "anthropic_messages":
        return MessagesApiExtractor()
    raise ValueError(f"Unknown llm_provider: {settings.llm_provider}")
