import json

import pytest

from app.core.settings import settings
from app.schemas.insights import Insights
from app.services.intelligence import (
    InsightExtractionError,
    MessagesApiExtractor,
    get_insight_extractor,
    load_prompt,
)

GOOD = {
    "topics": [{"title": "Pricing", "summary": "The team agreed to hold prices."}],
    "decisions": [{"decision": "Hold prices until Q1", "rationale": None}],
    "action_items": [
        {"task": "Send the updated quote", "owner": "Ana", "deadline": "Friday"}
    ],
    "open_questions": [{"question": "Who signs the contract?", "owner": None}],
}


def text_block(text: str) -> dict:
    return {"type": "text", "text": text}


def sender_returning(*blocks: dict, captured: list | None = None):
    def send(payload: dict) -> dict:
        if captured is not None:
            captured.append(payload)
        return {"model": "deepseek-flash", "content": list(blocks)}

    return send


def test_extracts_structured_insights() -> None:
    extractor = MessagesApiExtractor(
        sender=sender_returning(text_block(json.dumps(GOOD)))
    )

    insights = extractor.extract("Ana will send the updated quote by Friday.")

    assert isinstance(insights, Insights)
    assert insights.topics[0].title == "Pricing"
    assert insights.decisions[0].decision == "Hold prices until Q1"
    assert insights.action_items[0].owner == "Ana"
    assert insights.action_items[0].deadline == "Friday"


def test_accepts_fenced_json() -> None:
    fenced = "```json\n" + json.dumps(GOOD) + "\n```"
    extractor = MessagesApiExtractor(sender=sender_returning(text_block(fenced)))

    insights = extractor.extract("transcript")

    assert len(insights.decisions) == 1


def test_ignores_thinking_blocks() -> None:
    blocks = (
        {"type": "thinking", "thinking": "not json at all"},
        text_block(json.dumps(GOOD)),
    )
    extractor = MessagesApiExtractor(sender=sender_returning(*blocks))

    insights = extractor.extract("transcript")

    assert insights.action_items[0].task == "Send the updated quote"


def test_rejects_prose_without_json() -> None:
    extractor = MessagesApiExtractor(
        sender=sender_returning(text_block("I could not find any decisions."))
    )

    with pytest.raises(InsightExtractionError):
        extractor.extract("transcript")


def test_rejects_json_that_breaks_the_schema() -> None:
    payload = json.dumps({"topics": [{"title": "No summary here"}]})
    extractor = MessagesApiExtractor(sender=sender_returning(text_block(payload)))

    with pytest.raises(InsightExtractionError):
        extractor.extract("transcript")


def test_rejects_empty_reply() -> None:
    extractor = MessagesApiExtractor(sender=sender_returning())

    with pytest.raises(InsightExtractionError):
        extractor.extract("transcript")


def test_keeps_missing_owner_and_deadline_as_null() -> None:
    payload = json.dumps(
        {"action_items": [{"task": "Follow up with legal"}]}
    )
    extractor = MessagesApiExtractor(sender=sender_returning(text_block(payload)))

    item = extractor.extract("transcript").action_items[0]

    assert item.owner is None
    assert item.deadline is None


def test_sends_the_prompt_and_the_transcript() -> None:
    captured: list = []
    extractor = MessagesApiExtractor(
        sender=sender_returning(text_block(json.dumps(GOOD)), captured=captured)
    )

    extractor.extract("The whole transcript goes here.")

    payload = captured[0]
    assert payload["messages"] == [
        {"role": "user", "content": "The whole transcript goes here."}
    ]
    assert "JSON" in payload["system"]
    assert payload["max_tokens"] > 0


def test_prompt_file_is_present() -> None:
    prompt = load_prompt()

    assert "JSON" in prompt
    assert "action_items" in prompt


def test_default_provider_is_the_messages_api() -> None:
    get_insight_extractor.cache_clear()
    try:
        assert isinstance(get_insight_extractor(), MessagesApiExtractor)
    finally:
        get_insight_extractor.cache_clear()


def test_unknown_provider_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "llm_provider", "not-a-provider")
    get_insight_extractor.cache_clear()
    try:
        with pytest.raises(ValueError):
            get_insight_extractor()
    finally:
        get_insight_extractor.cache_clear()
