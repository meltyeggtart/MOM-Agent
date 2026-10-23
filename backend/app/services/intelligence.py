from functools import lru_cache
from pathlib import Path
from typing import Protocol

from pydantic import ValidationError

from app.core.settings import settings
from app.schemas.insights import Insights
from app.services.llm import LlmError, MessagesClient, Sender, json_object

PROMPT_PATH = Path(__file__).resolve().parent.parent / "prompts" / "extraction.md"


class InsightExtractionError(LlmError):
    """The model did not return usable structured insights."""


class InsightExtractor(Protocol):
    def extract(self, transcript: str) -> Insights: ...


def load_prompt() -> str:
    return PROMPT_PATH.read_text(encoding="utf-8").strip()


class MessagesApiExtractor:
    def __init__(self, sender: Sender | None = None) -> None:
        self._client = MessagesClient(sender)

    def extract(self, transcript: str) -> Insights:
        try:
            text = self._client.complete(load_prompt(), transcript)
            return Insights.model_validate(json_object(text))
        except ValidationError as exc:
            raise InsightExtractionError(
                f"Model reply did not match the schema: {exc}"
            ) from exc
        except LlmError as exc:
            raise InsightExtractionError(str(exc)) from exc


@lru_cache
def get_insight_extractor() -> InsightExtractor:
    if settings.llm_provider == "anthropic_messages":
        return MessagesApiExtractor()
    raise ValueError(f"Unknown llm_provider: {settings.llm_provider}")
