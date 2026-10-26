"""Review endpoints for a MOM: store, edit, approve, and reopen as a new version.

Approval locks the current version. Editing an approved MOM is not allowed; the
caller reopens it, which writes a new draft version and leaves the approved one
untouched, so the version trail stays honest.
"""

import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.auth import CurrentUser
from app.api.meetings import load_meeting
from app.db.models import Mom, MomStatus, MomVersion
from app.db.session import get_session
from app.schemas.mom import Audience, MomDocument
from app.services.consistency import (
    ConsistencyChecker,
    ConsistencyCheckError,
    ConsistencyReport,
    get_consistency_checker,
)
from app.services.sensitive import (
    SensitiveChecker,
    SensitiveCheckError,
    SensitiveReport,
    get_sensitive_checker,
)

router = APIRouter(prefix="/meetings/{meeting_id}/moms", tags=["moms"])


class MomVersionRead(BaseModel):
    version_number: int
    content: MomDocument
    ai_generated: bool
    approved_at: datetime | None
    approved_by: str | None
    created_at: datetime

    @classmethod
    def of(cls, version: MomVersion) -> "MomVersionRead":
        return cls(
            version_number=version.version_number,
            content=MomDocument.model_validate(version.content),
            ai_generated=version.ai_generated,
            approved_at=version.approved_at,
            approved_by=version.approved_by,
            created_at=version.created_at,
        )


class MomRead(BaseModel):
    audience: Audience
    status: str
    versions: list[MomVersionRead]

    @classmethod
    def of(cls, mom: Mom) -> "MomRead":
        return cls(
            audience=Audience(mom.audience),
            status=mom.status,
            versions=[
                MomVersionRead.of(version)
                for version in sorted(mom.versions, key=lambda v: v.version_number)
            ],
        )


SessionDep = Annotated[Session, Depends(get_session)]


def load_mom(
    session: Session,
    meeting_id: uuid.UUID,
    audience: Audience,
    owner_id: uuid.UUID,
) -> Mom:
    load_meeting(session, meeting_id, owner_id)
    mom = (
        session.query(Mom)
        .filter(Mom.meeting_id == meeting_id, Mom.audience == audience.value)
        .one_or_none()
    )
    if mom is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="MOM not found")
    return mom


def _check_audience(document: MomDocument, audience: Audience) -> None:
    if document.audience is not audience:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Document audience {document.audience} does not match {audience}",
        )


def current_version(mom: Mom) -> MomVersion:
    return max(mom.versions, key=lambda version: version.version_number)


SensitiveCheckerDep = Annotated[SensitiveChecker, Depends(get_sensitive_checker)]
ConsistencyCheckerDep = Annotated[
    ConsistencyChecker, Depends(get_consistency_checker)
]


class ApprovalRequest(BaseModel):
    """Sent only after a pre-approval check has already raised something."""

    acknowledge_issues: bool = False


def _internal_statements(session: Session, meeting_id: uuid.UUID) -> list[str]:
    """The internal-only statements an external MOM must never reveal.

    The internal MOM's notes are this product's own record of what stayed inside the
    room, so they are what the audit compares the external text against.
    """
    internal = (
        session.query(Mom)
        .filter(Mom.meeting_id == meeting_id, Mom.audience == Audience.internal.value)
        .one_or_none()
    )
    if internal is None:
        return []

    statements: list[str] = []
    document = MomDocument.model_validate(current_version(internal).content)
    for version in document.versions:
        for note in version.content.internal_notes:
            if note not in statements:
                statements.append(note)
    return statements


def _audit_external(
    document: MomDocument, statements: list[str], checker: SensitiveChecker
) -> SensitiveReport:
    try:
        return checker.check(document, statements)
    except SensitiveCheckError as exc:
        # Fail closed. An external MOM nobody could check must not reach a client.
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The external MOM could not be checked for internal content, so it "
            f"was not approved: {exc}",
        ) from exc


def _check_consistency(
    document: MomDocument, checker: ConsistencyChecker
) -> ConsistencyReport:
    try:
        return checker.check(document)
    except ConsistencyCheckError as exc:
        # Same reasoning as the audit: no verdict means no approval.
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The language versions could not be compared, so the MOM was not "
            f"approved: {exc}",
        ) from exc


def _approval_message(
    findings: SensitiveReport | None, mismatches: ConsistencyReport
) -> str:
    lines = ["The MOM was not approved."]
    if findings is not None and not findings.is_clean:
        lines.append("It may reveal internal information:")
        lines.extend(
            f"- [{finding.language}] {finding.excerpt} ({finding.reason})"
            for finding in findings.findings
        )
    if not mismatches.is_consistent:
        lines.append("The language versions disagree:")
        lines.extend(
            f"- {mismatch.field}: {mismatch.detail} "
            f"({', '.join(mismatch.languages)})"
            for mismatch in mismatches.mismatches
        )
    lines.append(
        "Edit the MOM, or approve again with acknowledge_issues if these are acceptable."
    )
    return "\n".join(lines)


@router.post(
    "/{audience}/versions",
    response_model=MomRead,
    status_code=status.HTTP_201_CREATED,
)
def store_version(
    meeting_id: uuid.UUID,
    audience: Audience,
    document: MomDocument,
    session: SessionDep,
    user: CurrentUser,
) -> MomRead:
    """Store a freshly generated MOM as the first draft."""
    load_meeting(session, meeting_id, user.id)
    _check_audience(document, audience)

    existing = (
        session.query(Mom)
        .filter(Mom.meeting_id == meeting_id, Mom.audience == audience.value)
        .one_or_none()
    )
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This meeting already has a MOM for that audience",
        )

    mom = Mom(meeting_id=meeting_id, audience=audience.value, status=MomStatus.draft)
    mom.versions.append(
        MomVersion(
            version_number=1,
            content=document.model_dump(mode="json"),
            ai_generated=True,
        )
    )
    session.add(mom)
    session.commit()
    session.refresh(mom)
    return MomRead.of(mom)


@router.get("/{audience}", response_model=MomRead)
def read_mom(
    meeting_id: uuid.UUID, audience: Audience, session: SessionDep, user: CurrentUser
) -> MomRead:
    return MomRead.of(load_mom(session, meeting_id, audience, user.id))


@router.get("/{audience}/consistency", response_model=ConsistencyReport)
def check_consistency(
    meeting_id: uuid.UUID,
    audience: Audience,
    session: SessionDep,
    user: CurrentUser,
    consistency: ConsistencyCheckerDep,
) -> ConsistencyReport:
    """Compare the versions on demand, without changing the MOM's state."""
    mom = load_mom(session, meeting_id, audience, user.id)
    document = MomDocument.model_validate(current_version(mom).content)
    return _check_consistency(document, consistency)


@router.put("/{audience}/draft", response_model=MomRead)
def update_draft(
    meeting_id: uuid.UUID,
    audience: Audience,
    document: MomDocument,
    session: SessionDep,
    user: CurrentUser,
) -> MomRead:
    _check_audience(document, audience)
    mom = load_mom(session, meeting_id, audience, user.id)
    if mom.status != MomStatus.draft:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The MOM is approved and locked; reopen it to edit",
        )

    current = current_version(mom)
    current.content = document.model_dump(mode="json")
    # An edited draft is no longer exactly what the model wrote.
    current.ai_generated = False
    session.commit()
    session.refresh(mom)
    return MomRead.of(mom)


@router.post("/{audience}/approve", response_model=MomRead)
def approve(
    meeting_id: uuid.UUID,
    audience: Audience,
    session: SessionDep,
    user: CurrentUser,
    checker: SensitiveCheckerDep,
    consistency: ConsistencyCheckerDep,
    request: ApprovalRequest | None = None,
) -> MomRead:
    mom = load_mom(session, meeting_id, audience, user.id)
    if mom.status != MomStatus.draft:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="The MOM is already approved"
        )

    current = current_version(mom)
    document = MomDocument.model_validate(current.content)

    findings: SensitiveReport | None = None
    if audience is Audience.external:
        findings = _audit_external(
            document, _internal_statements(session, meeting_id), checker
        )
    mismatches = _check_consistency(document, consistency)

    blocked = (findings is not None and not findings.is_clean) or (
        not mismatches.is_consistent
    )
    acknowledged = request is not None and request.acknowledge_issues
    if blocked and not acknowledged:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=_approval_message(findings, mismatches),
        )

    current.approved_at = datetime.now(UTC)
    # Taken from the session, not the request, so the trail cannot name someone else.
    current.approved_by = user.email
    mom.status = MomStatus.approved
    session.commit()
    session.refresh(mom)
    return MomRead.of(mom)


@router.post("/{audience}/reopen", response_model=MomRead)
def reopen(
    meeting_id: uuid.UUID, audience: Audience, session: SessionDep, user: CurrentUser
) -> MomRead:
    """Start a new draft from the approved version, leaving that version intact."""
    mom = load_mom(session, meeting_id, audience, user.id)
    if mom.status != MomStatus.approved:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only an approved MOM can be reopened",
        )

    current = current_version(mom)
    mom.versions.append(
        MomVersion(
            version_number=current.version_number + 1,
            content=dict(current.content),
            ai_generated=False,
        )
    )
    mom.status = MomStatus.draft
    session.commit()
    session.refresh(mom)
    return MomRead.of(mom)
