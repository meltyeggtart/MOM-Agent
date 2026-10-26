import json
from dataclasses import dataclass
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from typing import Protocol

from pydantic import ValidationError

from app.core.settings import settings
from app.schemas.insights import Insights
from app.schemas.meeting import Language
from app.schemas.mom import Audience, MomContent, MomDocument, MomVersion
from app.services.llm import LlmError, MessagesClient, json_object

PROMPT_DIR = Path(__file__).resolve().parent.parent / "prompts"

LANGUAGE_NAMES = {
    Language.en: "English",
    Language.zh: "Mandarin Chinese",
    Language.id: "Indonesian",
}

SHAPE_FIELDS = ("topics", "decisions", "action_items", "open_questions")

PROMPT_BY_AUDIENCE = {
    Audience.internal: "internal_mom.md",
    Audience.external: "external_mom.md",
}


class MomGenerationError(LlmError):
    """The model did not produce a usable set of minutes."""


@dataclass(frozen=True)
class MeetingContext:
    title: str
    meeting_at: datetime
    source_language: Language
    participants: str | None = None
    project: str | None = None
    client_company: str | None = None
    location: str | None = None
    agenda: str | None = None


class MomGenerator(Protocol):
    def generate(
        self,
        meeting: MeetingContext,
        insights: Insights,
        audience: Audience = Audience.internal,
    ) -> MomDocument: ...


def _prompt(name: str) -> str:
    return (PROMPT_DIR / name).read_text(encoding="utf-8").strip()


def _meeting_json(meeting: MeetingContext) -> dict:
    return {
        "title": meeting.title,
        "meeting_at": meeting.meeting_at.isoformat(),
        "language": meeting.source_language.value,
        "participants": meeting.participants,
        "project": meeting.project,
        "client_company": meeting.client_company,
        "location": meeting.location,
        "agenda": meeting.agenda,
    }


class LlmMomGenerator:
    """Writes the minutes once, in the source language, then translates them.

    Three independent drafts could disagree about a decision or a date. One authored
    text and two translations cannot.
    """

    def __init__(self, client: MessagesClient | None = None) -> None:
        self._client = client or MessagesClient()

    def generate(
        self,
        meeting: MeetingContext,
        insights: Insights,
        audience: Audience = Audience.internal,
    ) -> MomDocument:
        source = self._write(meeting, insights, audience)
        self._require_fit_for_audience(source, audience, meeting.source_language)
        versions = [MomVersion(language=meeting.source_language, content=source)]
        for language in Language:
            if language == meeting.source_language:
                continue
            translated = self._translate(source, language)
            self._require_same_shape(source, translated, language)
            self._require_fit_for_audience(translated, audience, language)
            versions.append(MomVersion(language=language, content=translated))
        return MomDocument(
            audience=audience,
            source_language=meeting.source_language,
            versions=versions,
        )

    def _write(
        self, meeting: MeetingContext, insights: Insights, audience: Audience
    ) -> MomContent:
        user = "\n\n".join(
            [
                "Meeting details:\n"
                + json.dumps(_meeting_json(meeting), indent=2, ensure_ascii=False),
                "Extracted facts:\n" + insights.model_dump_json(indent=2),
                f"Write the minutes in {LANGUAGE_NAMES[meeting.source_language]}.",
            ]
        )
        return self._parse(
            self._client.complete(_prompt(PROMPT_BY_AUDIENCE[audience]), user)
        )

    def _translate(self, content: MomContent, language: Language) -> MomContent:
        user = (
            json.dumps(content.model_dump(mode="json"), indent=2, ensure_ascii=False)
            + f"\n\nTarget language: {LANGUAGE_NAMES[language]}."
        )
        return self._parse(self._client.complete(_prompt("mom_translation.md"), user))

    @staticmethod
    def _parse(text: str) -> MomContent:
        try:
            return MomContent.model_validate(json_object(text))
        except (ValidationError, LlmError) as exc:
            raise MomGenerationError(
                f"Model reply did not match the minutes schema: {exc}"
            ) from exc

    @staticmethod
    def _require_fit_for_audience(
        content: MomContent, audience: Audience, language: Language
    ) -> None:
        if audience is Audience.external and content.internal_notes:
            raise MomGenerationError(
                f"The external MOM carries internal notes in {language}"
            )

    @staticmethod
    def _require_same_shape(
        source: MomContent, translated: MomContent, language: Language
    ) -> None:
        for field in SHAPE_FIELDS:
            before = len(getattr(source, field))
            after = len(getattr(translated, field))
            if before != after:
                raise MomGenerationError(
                    f"Translation into {language} changed {field} from "
                    f"{before} to {after} entries"
                )


@lru_cache
def get_mom_generator() -> MomGenerator:
    if settings.llm_provider == "anthropic_messages":
        return LlmMomGenerator()
    raise ValueError(f"Unknown llm_provider: {settings.llm_provider}")
