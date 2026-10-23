import json

import pytest

from app.schemas.meeting import Language
from app.schemas.mom import MomContent, MomDocument, MomVersion
from app.services.consistency import (
    ConsistencyCheckError,
    LlmConsistencyChecker,
    get_consistency_checker,
    load_prompt,
)


def document(deadline_id: str = "15 November 2026") -> MomDocument:
    action = {"task": "Send the media plan", "owner": "Ana", "deadline": "15 November 2026"}
    action_id = {**action, "deadline": deadline_id}
    contents = {
        Language.en: MomContent(
            title="Q3 kickoff",
            overview="The team met and kept the budget.",
            action_items=[action],
            decisions=["Keep the budget"],
        ),
        Language.zh: MomContent(
            title="Q3 启动会",
            overview="团队开会并维持预算。",
            action_items=[action],
            decisions=["维持预算"],
        ),
        Language.id: MomContent(
            title="Kickoff Q3",
            overview="Tim bertemu dan mempertahankan anggaran.",
            action_items=[action_id],
            decisions=["Pertahankan anggaran"],
        ),
    }
    return MomDocument(
        source_language=Language.en,
        versions=[
            MomVersion(language=language, content=content)
            for language, content in contents.items()
        ],
    )


class FakeClient:
    def __init__(self, *replies: str) -> None:
        self.replies = list(replies)
        self.calls: list[tuple[str, str]] = []

    def complete(self, system: str, user: str) -> str:
        self.calls.append((system, user))
        return self.replies.pop(0)


def reply(mismatches: list[dict] | None = None) -> str:
    return json.dumps({"mismatches": mismatches or []})


def test_flags_a_changed_deadline() -> None:
    found = {
        "field": "action_items[0].deadline",
        "detail": "English and Chinese say 15 November 2026; Indonesian says 15 September 2026.",
        "languages": ["en", "id"],
    }
    checker = LlmConsistencyChecker(FakeClient(reply([found])))

    report = checker.check(document("15 September 2026"))

    assert report.is_consistent is False
    assert report.mismatches[0].field == "action_items[0].deadline"
    assert set(report.mismatches[0].languages) == {Language.en, Language.id}


def test_consistent_document_passes() -> None:
    checker = LlmConsistencyChecker(FakeClient(reply()))

    report = checker.check(document())

    assert report.is_consistent is True
    assert report.mismatches == []


def test_sends_all_three_languages() -> None:
    client = FakeClient(reply())
    checker = LlmConsistencyChecker(client)

    checker.check(document())

    _, user = client.calls[0]
    assert '"en"' in user and '"zh"' in user and '"id"' in user
    assert "15 November 2026" in user


def test_a_single_language_cannot_be_a_mismatch() -> None:
    found = {"field": "overview", "detail": "odd", "languages": ["en"]}
    checker = LlmConsistencyChecker(FakeClient(reply([found])))

    with pytest.raises(ConsistencyCheckError):
        checker.check(document())


def test_rejects_broken_json() -> None:
    checker = LlmConsistencyChecker(FakeClient("Everything matches."))

    with pytest.raises(ConsistencyCheckError):
        checker.check(document())


def test_prompt_is_present() -> None:
    prompt = load_prompt()

    assert "mismatches" in prompt
    assert "at least two" in prompt


def test_default_checker_uses_the_llm() -> None:
    get_consistency_checker.cache_clear()
    try:
        assert isinstance(get_consistency_checker(), LlmConsistencyChecker)
    finally:
        get_consistency_checker.cache_clear()
