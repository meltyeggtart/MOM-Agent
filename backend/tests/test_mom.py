import json
from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from app.schemas.insights import Insights
from app.schemas.meeting import Language
from app.schemas.mom import Audience, MomDocument, MomVersion
from app.services.mom import (
    LlmMomGenerator,
    MeetingContext,
    MomGenerationError,
    get_mom_generator,
)

MEETING = MeetingContext(
    title="Q3 kickoff",
    meeting_at=datetime(2026, 10, 20, 9, 0, tzinfo=UTC),
    source_language=Language.en,
    participants="Ana, Budi",
)

INSIGHTS = Insights.model_validate(
    {
        "topics": [{"title": "Pricing", "summary": "The team agreed to hold prices."}],
        "decisions": [{"decision": "Hold prices until Q1", "rationale": None}],
        "action_items": [
            {"task": "Send the quote", "owner": "Ana", "deadline": "Friday"}
        ],
        "open_questions": [],
    }
)

MOM = {
    "title": "Q3 kickoff minutes",
    "overview": "The team met to settle pricing.",
    "topics": [{"heading": "Pricing", "discussion": "Prices stay flat."}],
    "decisions": ["Hold prices until Q1"],
    "action_items": [
        {"task": "Send the quote", "owner": "Ana", "deadline": "Friday"}
    ],
    "open_questions": [],
    "internal_notes": ["Margin is thinner than last quarter."],
}


class FakeClient:
    def __init__(self, *replies: str) -> None:
        self.replies = list(replies)
        self.calls: list[tuple[str, str]] = []

    def complete(self, system: str, user: str) -> str:
        self.calls.append((system, user))
        return self.replies.pop(0)


def reply(**overrides) -> str:
    document = json.loads(json.dumps(MOM))
    document.update(overrides)
    return json.dumps(document)


def test_carries_one_version_per_language() -> None:
    client = FakeClient(reply(), reply(), reply())

    document = LlmMomGenerator(client).generate(MEETING, INSIGHTS)

    assert document.source_language is Language.en
    assert {version.language for version in document.versions} == set(Language)
    assert len(client.calls) == 3


def test_writes_in_the_source_language() -> None:
    meeting = MeetingContext(
        title="Rapat kuartal",
        meeting_at=datetime(2026, 10, 20, 9, 0, tzinfo=UTC),
        source_language=Language.id,
    )
    client = FakeClient(reply(), reply(), reply())

    LlmMomGenerator(client).generate(meeting, INSIGHTS)

    system, user = client.calls[0]
    assert "internal meeting minutes" in system.lower()
    assert "Write the minutes in Indonesian." in user
    assert "Rapat kuartal" in user


def test_translation_receives_the_authored_text() -> None:
    client = FakeClient(reply(), reply(), reply())

    LlmMomGenerator(client).generate(MEETING, INSIGHTS)

    system, user = client.calls[1]
    assert "translate" in system.lower()
    assert "Q3 kickoff minutes" in user
    assert "Target language:" in user


def test_keeps_internal_notes() -> None:
    client = FakeClient(reply(), reply(), reply())

    document = LlmMomGenerator(client).generate(MEETING, INSIGHTS)

    assert document.versions[0].content.internal_notes == [
        "Margin is thinner than last quarter."
    ]


def test_rejects_a_translation_that_drops_a_decision() -> None:
    client = FakeClient(reply(), reply(decisions=[]), reply())

    with pytest.raises(MomGenerationError):
        LlmMomGenerator(client).generate(MEETING, INSIGHTS)


def test_rejects_broken_json() -> None:
    client = FakeClient("I am afraid I cannot do that.", reply(), reply())

    with pytest.raises(MomGenerationError):
        LlmMomGenerator(client).generate(MEETING, INSIGHTS)


def test_document_rejects_a_missing_language() -> None:
    english = MomVersion(language=Language.en, content=MOM)

    with pytest.raises(ValidationError):
        MomDocument(source_language=Language.en, versions=[english])


def test_document_rejects_a_duplicate_language() -> None:
    english = MomVersion(language=Language.en, content=MOM)
    mandarin = MomVersion(language=Language.zh, content=MOM)
    indonesian = MomVersion(language=Language.id, content=MOM)

    with pytest.raises(ValidationError):
        MomDocument(
            source_language=Language.en,
            versions=[english, mandarin, indonesian, english],
        )


def test_default_generator_uses_the_llm() -> None:
    get_mom_generator.cache_clear()
    try:
        assert isinstance(get_mom_generator(), LlmMomGenerator)
    finally:
        get_mom_generator.cache_clear()


def test_external_uses_the_client_prompt() -> None:
    client = FakeClient(*[reply(internal_notes=[]) for _ in range(3)])

    LlmMomGenerator(client).generate(MEETING, INSIGHTS, Audience.external)

    system, _ = client.calls[0]
    assert "client" in system.lower()
    assert "internal_notes must always be an empty array" in system
    assert '"risks" list' in system


def test_external_carries_three_languages() -> None:
    client = FakeClient(*[reply(internal_notes=[]) for _ in range(3)])

    document = LlmMomGenerator(client).generate(MEETING, INSIGHTS, Audience.external)

    assert document.audience is Audience.external
    assert {version.language for version in document.versions} == set(Language)
    assert len(client.calls) == 3


def test_external_rejects_internal_notes() -> None:
    client = FakeClient(reply())

    with pytest.raises(MomGenerationError, match="internal notes"):
        LlmMomGenerator(client).generate(MEETING, INSIGHTS, Audience.external)


def test_external_rejects_notes_added_by_a_translation() -> None:
    client = FakeClient(
        reply(internal_notes=[]),
        reply(internal_notes=["Margin is thin; do not tell the client."]),
        reply(internal_notes=[]),
    )

    with pytest.raises(MomGenerationError, match="internal notes"):
        LlmMomGenerator(client).generate(MEETING, INSIGHTS, Audience.external)


def test_internal_notes_survive_for_the_internal_audience() -> None:
    client = FakeClient(reply(), reply(), reply())

    document = LlmMomGenerator(client).generate(MEETING, INSIGHTS, Audience.internal)

    assert document.audience is Audience.internal
    assert document.versions[0].content.internal_notes
