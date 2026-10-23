from enum import StrEnum

from pydantic import BaseModel, Field, model_validator

from app.schemas.meeting import Language


class Audience(StrEnum):
    internal = "internal"
    external = "external"


class MomTopic(BaseModel):
    heading: str
    discussion: str


class MomAction(BaseModel):
    task: str
    owner: str | None = None
    deadline: str | None = None


class MomContent(BaseModel):
    title: str
    overview: str
    topics: list[MomTopic] = Field(default_factory=list)
    decisions: list[str] = Field(default_factory=list)
    action_items: list[MomAction] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)
    # Internal minutes only. The external generator leaves this empty.
    internal_notes: list[str] = Field(default_factory=list)


class MomVersion(BaseModel):
    language: Language
    content: MomContent


class MomDocument(BaseModel):
    """One document carrying every MOM language.

    Hiding a language at review is a view of this document, not a deletion, so the
    document always holds all three.
    """

    source_language: Language
    audience: Audience = Audience.internal
    # Every language is stored; this is what the reviewer chose to show. Hiding is
    # never deletion, so a hidden language can be brought back without regenerating.
    visible_languages: list[Language] = Field(default_factory=lambda: list(Language))
    versions: list[MomVersion]

    @model_validator(mode="after")
    def _visible_languages_are_stored(self) -> "MomDocument":
        if not self.visible_languages:
            raise ValueError("At least one language must stay visible")
        if len(set(self.visible_languages)) != len(self.visible_languages):
            raise ValueError("A language cannot be listed twice")
        stored = {version.language for version in self.versions}
        if set(self.visible_languages) - stored:
            raise ValueError("A visible language has no version in this document")
        return self

    @model_validator(mode="after")
    def _one_version_per_language(self) -> "MomDocument":
        languages = [version.language for version in self.versions]
        if len(languages) != len(Language) or set(languages) != set(Language):
            raise ValueError("a MOM must carry exactly one version per language")
        return self
