import uuid
from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class Language(StrEnum):
    en = "en"
    zh = "zh"


class MeetingCreate(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    meeting_at: datetime
    languages: list[Language] = Field(min_length=1)
    client_company: str | None = None
    project: str | None = None
    participants: str | None = None
    agenda: str | None = None
    location: str | None = None
    meeting_type: str | None = None
    is_in_person: bool = True


class MeetingRead(MeetingCreate):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    status: str
    created_at: datetime
    updated_at: datetime
