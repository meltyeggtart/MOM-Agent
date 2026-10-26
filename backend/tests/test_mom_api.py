from collections.abc import Callable, Iterator, Sequence

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.schemas.meeting import Language
from app.schemas.mom import MomDocument
from app.services.consistency import (
    ConsistencyCheckError,
    ConsistencyReport,
    Mismatch,
    get_consistency_checker,
)
from app.services.sensitive import (
    Finding,
    SensitiveCheckError,
    SensitiveReport,
    get_sensitive_checker,
)


def create_meeting(client: TestClient) -> str:
    response = client.post(
        "/meetings",
        json={
            "title": "Q3 kickoff",
            "meeting_at": "2026-10-20T09:00:00Z",
            "languages": ["en"],
        },
    )
    assert response.status_code == 201
    return response.json()["id"]


def payload(audience: str = "internal", visible: list[str] | None = None) -> dict:
    return {
        "source_language": "en",
        "audience": audience,
        "visible_languages": visible or ["en", "zh", "id"],
        "versions": [
            {
                "language": language,
                "content": {
                    "title": f"Kickoff {language}",
                    "overview": "The team agreed to keep the budget.",
                },
            }
            for language in ("en", "zh", "id")
        ],
    }


def store(
    client: TestClient,
    meeting_id: str,
    body: dict | None = None,
    audience: str = "internal",
) -> dict:
    response = client.post(
        f"/meetings/{meeting_id}/moms/{audience}/versions",
        json=body or payload(audience),
    )
    assert response.status_code == 201
    return response.json()


def test_stores_and_reads_a_draft(client: TestClient) -> None:
    meeting_id = create_meeting(client)

    stored = store(client, meeting_id)
    read = client.get(f"/meetings/{meeting_id}/moms/internal")

    assert stored["status"] == "draft"
    assert stored["versions"][0]["version_number"] == 1
    assert stored["versions"][0]["ai_generated"] is True
    assert read.status_code == 200
    assert read.json()["versions"][0]["content"]["versions"][0]["content"]["title"] == (
        "Kickoff en"
    )


def test_storing_twice_conflicts(client: TestClient) -> None:
    meeting_id = create_meeting(client)
    store(client, meeting_id)

    again = client.post(
        f"/meetings/{meeting_id}/moms/internal/versions", json=payload()
    )

    assert again.status_code == 409


def test_edit_updates_the_draft(client: TestClient) -> None:
    meeting_id = create_meeting(client)
    store(client, meeting_id)
    edited = payload()
    edited["versions"][0]["content"]["title"] = "Edited by the reviewer"

    response = client.put(f"/meetings/{meeting_id}/moms/internal/draft", json=edited)
    read = client.get(f"/meetings/{meeting_id}/moms/internal").json()

    assert response.status_code == 200
    assert read["versions"][0]["content"]["versions"][0]["content"]["title"] == (
        "Edited by the reviewer"
    )
    assert read["versions"][0]["ai_generated"] is False


def test_approval_locks_the_draft(client: TestClient) -> None:
    meeting_id = create_meeting(client)
    store(client, meeting_id)
    me = client.get("/auth/me").json()

    # The body names someone else; the server must ignore it and record the session.
    approved = client.post(
        f"/meetings/{meeting_id}/moms/internal/approve",
        json={"approved_by": "Someone Else"},
    )
    blocked = client.put(
        f"/meetings/{meeting_id}/moms/internal/draft", json=payload()
    )

    assert approved.status_code == 200
    assert approved.json()["status"] == "approved"
    assert approved.json()["versions"][0]["approved_by"] == me["email"]
    assert approved.json()["versions"][0]["approved_at"] is not None
    assert blocked.status_code == 409


def test_approving_twice_conflicts(client: TestClient) -> None:
    meeting_id = create_meeting(client)
    store(client, meeting_id)
    client.post(f"/meetings/{meeting_id}/moms/internal/approve")

    again = client.post(f"/meetings/{meeting_id}/moms/internal/approve")

    assert again.status_code == 409


def test_reopen_starts_a_new_version(client: TestClient) -> None:
    meeting_id = create_meeting(client)
    store(client, meeting_id)
    client.post(f"/meetings/{meeting_id}/moms/internal/approve")

    reopened = client.post(f"/meetings/{meeting_id}/moms/internal/reopen").json()

    assert reopened["status"] == "draft"
    assert [v["version_number"] for v in reopened["versions"]] == [1, 2]
    assert reopened["versions"][0]["approved_at"] is not None
    assert reopened["versions"][1]["approved_at"] is None
    assert reopened["versions"][1]["ai_generated"] is False
    assert reopened["versions"][1]["content"] == reopened["versions"][0]["content"]


def test_reopen_before_approval_conflicts(client: TestClient) -> None:
    meeting_id = create_meeting(client)
    store(client, meeting_id)

    response = client.post(f"/meetings/{meeting_id}/moms/internal/reopen")

    assert response.status_code == 409


def test_a_hidden_language_stays_stored(client: TestClient) -> None:
    meeting_id = create_meeting(client)
    store(client, meeting_id, payload(visible=["en", "id"]))

    read = client.get(f"/meetings/{meeting_id}/moms/internal").json()

    assert read["versions"][0]["content"]["visible_languages"] == ["en", "id"]
    assert len(read["versions"][0]["content"]["versions"]) == 3


def test_an_unknown_meeting_is_404(client: TestClient) -> None:
    missing = "00000000-0000-0000-0000-000000000000"

    assert client.get(f"/meetings/{missing}/moms/internal").status_code == 404
    assert (
        client.post(f"/meetings/{missing}/moms/internal/versions", json=payload()).status_code
        == 404
    )


def test_an_audience_mismatch_is_rejected(client: TestClient) -> None:
    meeting_id = create_meeting(client)

    response = client.post(
        f"/meetings/{meeting_id}/moms/internal/versions",
        json=payload(audience="external"),
    )

    assert response.status_code == 400


def test_languages_must_be_a_subset(client: TestClient) -> None:
    meeting_id = create_meeting(client)
    body = payload()
    body["visible_languages"] = ["fr"]

    response = client.post(
        f"/meetings/{meeting_id}/moms/internal/versions", json=body
    )

    assert response.status_code == 422


class FakeSensitive:
    """Stands in for the model so these tests stay offline and deterministic."""

    def __init__(self, outcome: SensitiveReport | Exception) -> None:
        self.outcome = outcome
        self.calls: list[tuple[MomDocument, list[str]]] = []

    def check(self, external: MomDocument, secrets: Sequence[str]) -> SensitiveReport:
        self.calls.append((external, list(secrets)))
        if isinstance(self.outcome, Exception):
            raise self.outcome
        return self.outcome


class FakeConsistency:
    """Stands in for the model so these tests stay offline and deterministic."""

    def __init__(self, outcome: ConsistencyReport | Exception) -> None:
        self.outcome = outcome
        self.calls: list[MomDocument] = []

    def check(self, document: MomDocument) -> ConsistencyReport:
        self.calls.append(document)
        if isinstance(self.outcome, Exception):
            raise self.outcome
        return self.outcome


@pytest.fixture(autouse=True)
def offline_checks(clean_checks: None) -> None:
    """Approval runs both checks. Every test starts with clean verdicts."""


@pytest.fixture
def use_checker() -> Iterator[Callable[[SensitiveReport | Exception], FakeSensitive]]:
    def install(outcome: SensitiveReport | Exception) -> FakeSensitive:
        fake = FakeSensitive(outcome)
        app.dependency_overrides[get_sensitive_checker] = lambda: fake
        return fake

    yield install
    app.dependency_overrides.pop(get_sensitive_checker, None)


@pytest.fixture
def use_consistency() -> Iterator[
    Callable[[ConsistencyReport | Exception], FakeConsistency]
]:
    def install(outcome: ConsistencyReport | Exception) -> FakeConsistency:
        fake = FakeConsistency(outcome)
        app.dependency_overrides[get_consistency_checker] = lambda: fake
        return fake

    yield install
    app.dependency_overrides.pop(get_consistency_checker, None)


def leak(excerpt: str = "Our margin is thinner than last quarter.") -> Finding:
    return Finding(
        language=Language.en,
        excerpt=excerpt,
        reason="This restates an internal figure.",
    )


def test_a_flagged_external_mom_is_not_approved(
    client: TestClient, use_checker: Callable[..., FakeSensitive]
) -> None:
    meeting_id = create_meeting(client)
    store(client, meeting_id)
    store(client, meeting_id, audience="external")
    use_checker(SensitiveReport(findings=[leak()]))

    response = client.post(f"/meetings/{meeting_id}/moms/external/approve")

    assert response.status_code == 409
    assert "Our margin is thinner" in response.json()["detail"]
    assert client.get(f"/meetings/{meeting_id}/moms/external").json()["status"] == "draft"


def test_an_acknowledged_finding_still_approves(
    client: TestClient, use_checker: Callable[..., FakeSensitive]
) -> None:
    meeting_id = create_meeting(client)
    store(client, meeting_id)
    store(client, meeting_id, audience="external")
    use_checker(SensitiveReport(findings=[leak()]))

    response = client.post(
        f"/meetings/{meeting_id}/moms/external/approve",
        json={"acknowledge_issues": True},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "approved"


def test_a_clean_external_mom_approves_without_a_word(
    client: TestClient, use_checker: Callable[..., FakeSensitive]
) -> None:
    meeting_id = create_meeting(client)
    store(client, meeting_id, audience="external")
    use_checker(SensitiveReport())

    response = client.post(f"/meetings/{meeting_id}/moms/external/approve")

    assert response.status_code == 200
    assert response.json()["status"] == "approved"


def test_the_audit_reads_the_internal_notes(
    client: TestClient, use_checker: Callable[..., FakeSensitive]
) -> None:
    meeting_id = create_meeting(client)
    internal = payload()
    internal["versions"][0]["content"]["internal_notes"] = ["Our margin is thin."]
    store(client, meeting_id, internal)
    store(client, meeting_id, audience="external")
    checker = use_checker(SensitiveReport())

    client.post(f"/meetings/{meeting_id}/moms/external/approve")

    assert checker.calls[0][1] == ["Our margin is thin."]


def test_the_audit_sees_the_document_it_checks(
    client: TestClient, use_checker: Callable[..., FakeSensitive]
) -> None:
    meeting_id = create_meeting(client)
    external = payload("external")
    external["versions"][0]["content"]["overview"] = "The budget is settled."
    store(client, meeting_id, external, audience="external")
    checker = use_checker(SensitiveReport())

    client.post(f"/meetings/{meeting_id}/moms/external/approve")

    checked = checker.calls[0][0]
    assert checked.audience.value == "external"
    assert checked.versions[0].content.overview == "The budget is settled."


def test_an_internal_mom_is_never_audited(
    client: TestClient, use_checker: Callable[..., FakeSensitive]
) -> None:
    meeting_id = create_meeting(client)
    store(client, meeting_id)
    checker = use_checker(SensitiveReport(findings=[leak()]))

    response = client.post(f"/meetings/{meeting_id}/moms/internal/approve")

    assert response.status_code == 200
    assert checker.calls == []


def test_a_failed_check_blocks_approval(
    client: TestClient, use_checker: Callable[..., FakeSensitive]
) -> None:
    meeting_id = create_meeting(client)
    store(client, meeting_id, audience="external")
    use_checker(SensitiveCheckError("the model timed out"))

    response = client.post(f"/meetings/{meeting_id}/moms/external/approve")

    assert response.status_code == 503
    assert client.get(f"/meetings/{meeting_id}/moms/external").json()["status"] == "draft"



def mismatch(
    field: str = "action_items[1].deadline",
    detail: str = "en says 3 November, id says 10 November",
) -> Mismatch:
    return Mismatch(field=field, detail=detail, languages=[Language.en, Language.id])


def test_versions_that_disagree_block_approval(
    client: TestClient, use_consistency: Callable[..., FakeConsistency]
) -> None:
    meeting_id = create_meeting(client)
    store(client, meeting_id)
    use_consistency(ConsistencyReport(mismatches=[mismatch()]))

    response = client.post(f"/meetings/{meeting_id}/moms/internal/approve")

    assert response.status_code == 409
    assert "action_items[1].deadline" in response.json()["detail"]
    assert "3 November" in response.json()["detail"]
    assert client.get(f"/meetings/{meeting_id}/moms/internal").json()["status"] == "draft"


def test_an_acknowledged_mismatch_still_approves(
    client: TestClient, use_consistency: Callable[..., FakeConsistency]
) -> None:
    meeting_id = create_meeting(client)
    store(client, meeting_id)
    use_consistency(ConsistencyReport(mismatches=[mismatch()]))

    response = client.post(
        f"/meetings/{meeting_id}/moms/internal/approve",
        json={"acknowledge_issues": True},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "approved"


def test_both_checks_block_in_one_answer(
    client: TestClient,
    use_checker: Callable[..., FakeSensitive],
    use_consistency: Callable[..., FakeConsistency],
) -> None:
    meeting_id = create_meeting(client)
    store(client, meeting_id)
    store(client, meeting_id, audience="external")
    use_checker(SensitiveReport(findings=[leak()]))
    use_consistency(ConsistencyReport(mismatches=[mismatch()]))

    response = client.post(f"/meetings/{meeting_id}/moms/external/approve")

    assert response.status_code == 409
    detail = response.json()["detail"]
    assert "may reveal internal information" in detail
    assert "Our margin is thinner" in detail
    assert "The language versions disagree" in detail


def test_a_failed_comparison_blocks_approval(
    client: TestClient, use_consistency: Callable[..., FakeConsistency]
) -> None:
    meeting_id = create_meeting(client)
    store(client, meeting_id)
    use_consistency(ConsistencyCheckError("the model timed out"))

    response = client.post(f"/meetings/{meeting_id}/moms/internal/approve")

    assert response.status_code == 503
    assert client.get(f"/meetings/{meeting_id}/moms/internal").json()["status"] == "draft"


def test_the_comparison_sees_every_version(
    client: TestClient, use_consistency: Callable[..., FakeConsistency]
) -> None:
    meeting_id = create_meeting(client)
    store(client, meeting_id)
    checker = use_consistency(ConsistencyReport())

    response = client.post(f"/meetings/{meeting_id}/moms/internal/approve")

    assert response.status_code == 200
    assert len(checker.calls[0].versions) == 3


def test_the_consistency_endpoint_reports_without_approving(
    client: TestClient, use_consistency: Callable[..., FakeConsistency]
) -> None:
    meeting_id = create_meeting(client)
    store(client, meeting_id)
    use_consistency(ConsistencyReport(mismatches=[mismatch()]))

    response = client.get(f"/meetings/{meeting_id}/moms/internal/consistency")

    assert response.status_code == 200
    assert response.json()["mismatches"][0]["field"] == "action_items[1].deadline"
    assert client.get(f"/meetings/{meeting_id}/moms/internal").json()["status"] == "draft"


def test_the_consistency_endpoint_can_fail(
    client: TestClient, use_consistency: Callable[..., FakeConsistency]
) -> None:
    meeting_id = create_meeting(client)
    store(client, meeting_id)
    use_consistency(ConsistencyCheckError("no answer"))

    response = client.get(f"/meetings/{meeting_id}/moms/internal/consistency")

    assert response.status_code == 503



def test_a_draft_cannot_be_exported(client: TestClient) -> None:
    meeting_id = create_meeting(client)
    store(client, meeting_id)

    pdf = client.get(f"/meetings/{meeting_id}/moms/internal/export.pdf")
    docx = client.get(f"/meetings/{meeting_id}/moms/internal/export.docx")

    assert pdf.status_code == 409
    assert "Approve it before exporting" in pdf.json()["detail"]
    assert docx.status_code == 409


def test_an_approved_mom_exports(client: TestClient) -> None:
    meeting_id = create_meeting(client)
    store(client, meeting_id)
    approved = client.post(f"/meetings/{meeting_id}/moms/internal/approve")
    assert approved.status_code == 200

    pdf = client.get(f"/meetings/{meeting_id}/moms/internal/export.pdf")
    docx = client.get(f"/meetings/{meeting_id}/moms/internal/export.docx")

    assert pdf.status_code == 200
    assert pdf.headers["content-type"] == "application/pdf"
    assert pdf.content.startswith(b"%PDF")
    assert docx.status_code == 200
    assert docx.content.startswith(b"PK")
