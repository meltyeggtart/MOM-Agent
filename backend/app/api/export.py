"""Download a MOM as DOCX or PDF, in the languages kept at review."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.api.mom import current_version, load_mom
from app.db.session import get_session
from app.schemas.mom import Audience, MomDocument
from app.services.documents import to_docx, to_pdf

router = APIRouter(prefix="/meetings/{meeting_id}/moms", tags=["export"])

SessionDep = Annotated[Session, Depends(get_session)]

DOCX_TYPE = (
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
)
PDF_TYPE = "application/pdf"


def _document(session: Session, meeting_id: uuid.UUID, audience: Audience) -> MomDocument:
    mom = load_mom(session, meeting_id, audience)
    return MomDocument.model_validate(current_version(mom).content)


def _attachment(content: bytes, media_type: str, filename: str) -> Response:
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/{audience}/export.docx")
def export_docx(
    meeting_id: uuid.UUID, audience: Audience, session: SessionDep
) -> Response:
    document = _document(session, meeting_id, audience)
    return _attachment(
        to_docx(document), DOCX_TYPE, f"mom-{meeting_id}-{audience.value}.docx"
    )


@router.get("/{audience}/export.pdf")
def export_pdf(
    meeting_id: uuid.UUID, audience: Audience, session: SessionDep
) -> Response:
    document = _document(session, meeting_id, audience)
    return _attachment(
        to_pdf(document), PDF_TYPE, f"mom-{meeting_id}-{audience.value}.pdf"
    )
