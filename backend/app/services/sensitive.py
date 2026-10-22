import json
from collections.abc import Sequence
from enum import StrEnum
from functools import lru_cache
from pathlib import Path
from typing import Protocol

from pydantic import BaseModel, Field, ValidationError

from app.core.settings import settings
from app.schemas.meeting import Language
from app.schemas.mom import Audience, MomDocument
from app.services.llm import LlmError, MessagesClient, json_object

PROMPT_PATH = Path(__file__).resolve().parent.parent / "prompts" / "sensitive_check.md"


class Severity(StrEnum):
    high = "high"
    medium = "medium"


class Finding(BaseModel):
    language: Language
    excerpt: str
    reason: str
    severity: Severity = Severity.high


class SensitiveReport(BaseModel):
    findings: list[Finding] = Field(default_factory=list)

    @property
    def is_clean(self) -> bool:
        return not self.findings


class SensitiveCheckError(LlmError):
    """The check could not produce a usable verdict."""


class SensitiveChecker(Protocol):
    def check(
        self, external: MomDocument, secrets: Sequence[str]
    ) -> SensitiveReport: ...


def load_prompt() -> str:
    return PROMPT_PATH.read_text(encoding="utf-8").strip()


class LlmSensitiveChecker:
    """Asks a model to audit the finished external minutes against the internal facts.

    This runs after the external MOM is written, on purpose. The writer's prompt is a
    request; this is a second reader that can disagree with it.
    """

    def __init__(self, client: MessagesClient | None = None) -> None:
        self._client = client or MessagesClient()

    def check(self, external: MomDocument, secrets: Sequence[str]) -> SensitiveReport:
        if external.audience is not Audience.external:
            raise ValueError("The sensitive-content check only applies to an external MOM")

        user = "\n\n".join(
            [
                "Secrets (internal only):\n"
                + json.dumps(list(secrets), indent=2, ensure_ascii=False),
                "Minutes:\n" + external.model_dump_json(indent=2),
            ]
        )
        try:
            text = self._client.complete(load_prompt(), user)
            return SensitiveReport.model_validate(json_object(text))
        except ValidationError as exc:
            raise SensitiveCheckError(f"Check reply did not match the schema: {exc}") from exc
        except LlmError as exc:
            raise SensitiveCheckError(str(exc)) from exc


@lru_cache
def get_sensitive_checker() -> SensitiveChecker:
    if settings.llm_provider == "anthropic_messages":
        return LlmSensitiveChecker()
    raise ValueError(f"Unknown llm_provider: {settings.llm_provider}")
