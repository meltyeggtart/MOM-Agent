import json

import pytest

from app.schemas.meeting import Language
from app.schemas.mom import Audience, MomContent, MomDocument, MomVersion
from app.services.sensitive import (
    LlmSensitiveChecker,
    SensitiveCheckError,
    Severity,
    get_sensitive_checker,
    load_prompt,
)

SECRETS = ["Our margin on this account is thinner than last quarter."]


def document(overview: str, audience: Audience = Audience.external) -> MomDocument:
    content = MomContent(title="Q3 kickoff", overview=overview)
    return MomDocument(
        audience=audience,
        source_language=Language.en,
        versions=[
            MomVersion(language=language, content=content) for language in Language
        ],
    )


class FakeClient:
    def __init__(self, *replies: str) -> None:
        self.replies = list(replies)
        self.calls: list[tuple[str, str]] = []

    def complete(self, system: str, user: str) -> str:
        self.calls.append((system, user))
        return self.replies.pop(0)


def reply(findings: list[dict] | None = None) -> str:
    return json.dumps({"findings": findings or []})


def test_flags_seeded_internal_text() -> None:
    leaked = {
        "language": "en",
        "excerpt": "Our margin is thinner than last quarter.",
        "reason": "This restates an internal figure the client must not see.",
        "severity": "high",
    }
    checker = LlmSensitiveChecker(FakeClient(reply([leaked])))

    report = checker.check(document("The margin is thinner than last quarter."), SECRETS)

    assert report.is_clean is False
    assert report.findings[0].language is Language.en
    assert report.findings[0].severity is Severity.high


def test_clean_minutes_pass() -> None:
    checker = LlmSensitiveChecker(FakeClient(reply()))

    report = checker.check(document("The team agreed to hold prices."), SECRETS)

    assert report.is_clean is True
    assert report.findings == []


def test_sends_the_secrets_and_the_minutes() -> None:
    client = FakeClient(reply())
    checker = LlmSensitiveChecker(client)

    checker.check(document("The team agreed to hold prices."), SECRETS)

    _, user = client.calls[0]
    assert "thinner than last quarter" in user
    assert "The team agreed to hold prices." in user
    assert '"en"' in user


def test_severity_defaults_to_high() -> None:
    finding = {
        "language": "id",
        "excerpt": "Marjin kami lebih tipis.",
        "reason": "Internal figure restated.",
    }
    checker = LlmSensitiveChecker(FakeClient(reply([finding])))

    report = checker.check(document("ok"), SECRETS)

    assert report.findings[0].severity is Severity.high


def test_rejects_broken_json() -> None:
    checker = LlmSensitiveChecker(FakeClient("Nothing to report, all good."))

    with pytest.raises(SensitiveCheckError):
        checker.check(document("ok"), SECRETS)


def test_rejects_an_unknown_severity() -> None:
    finding = {
        "language": "en",
        "excerpt": "x",
        "reason": "y",
        "severity": "catastrophic",
    }
    checker = LlmSensitiveChecker(FakeClient(reply([finding])))

    with pytest.raises(SensitiveCheckError):
        checker.check(document("ok"), SECRETS)


def test_refuses_to_audit_an_internal_document() -> None:
    checker = LlmSensitiveChecker(FakeClient(reply()))

    with pytest.raises(ValueError):
        checker.check(document("ok", audience=Audience.internal), SECRETS)


def test_prompt_is_present() -> None:
    prompt = load_prompt()

    assert "findings" in prompt
    assert '"secrets"' in prompt.lower() or "secrets" in prompt.lower()


def test_default_checker_uses_the_llm() -> None:
    get_sensitive_checker.cache_clear()
    try:
        assert isinstance(get_sensitive_checker(), LlmSensitiveChecker)
    finally:
        get_sensitive_checker.cache_clear()
