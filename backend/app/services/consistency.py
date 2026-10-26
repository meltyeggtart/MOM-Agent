from functools import lru_cache
from pathlib import Path
from typing import Protocol

from pydantic import BaseModel, Field, ValidationError

from app.core.settings import settings
from app.schemas.meeting import Language
from app.schemas.mom import MomDocument
from app.services.llm import LlmError, MessagesClient, json_object

PROMPT_PATH = Path(__file__).resolve().parent.parent / "prompts" / "consistency_check.md"


class Mismatch(BaseModel):
    field: str
    detail: str
    # One version cannot disagree with itself.
    languages: list[Language] = Field(min_length=2)


class ConsistencyReport(BaseModel):
    mismatches: list[Mismatch] = Field(default_factory=list)

    @property
    def is_consistent(self) -> bool:
        return not self.mismatches


class ConsistencyCheckError(LlmError):
    """The check could not produce a usable verdict."""


class ConsistencyChecker(Protocol):
    def check(self, document: MomDocument) -> ConsistencyReport: ...


def load_prompt() -> str:
    return PROMPT_PATH.read_text(encoding="utf-8").strip()


class LlmConsistencyChecker:
    """Compares the three versions of one document for meaning, not wording.

    `LlmMomGenerator` already refuses a translation whose entry counts differ. That
    catches a dropped decision, not a decision whose date changed.
    """

    def __init__(self, client: MessagesClient | None = None) -> None:
        self._client = client or MessagesClient()

    def check(self, document: MomDocument) -> ConsistencyReport:
        user = "Minutes:\n" + document.model_dump_json(indent=2)
        try:
            text = self._client.complete(load_prompt(), user)
            return ConsistencyReport.model_validate(json_object(text))
        except ValidationError as exc:
            raise ConsistencyCheckError(
                f"Check reply did not match the schema: {exc}"
            ) from exc
        except LlmError as exc:
            raise ConsistencyCheckError(str(exc)) from exc


@lru_cache
def get_consistency_checker() -> ConsistencyChecker:
    if settings.llm_provider == "anthropic_messages":
        return LlmConsistencyChecker()
    raise ValueError(f"Unknown llm_provider: {settings.llm_provider}")
