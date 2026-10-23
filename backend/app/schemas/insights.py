from pydantic import BaseModel, Field


class Topic(BaseModel):
    title: str
    summary: str


class Decision(BaseModel):
    decision: str
    rationale: str | None = None


class ActionItem(BaseModel):
    task: str
    # Null when the transcript never names an owner or a deadline. The prompt forbids
    # guessing, so these stay empty instead of being invented.
    owner: str | None = None
    deadline: str | None = None


class OpenQuestion(BaseModel):
    question: str
    owner: str | None = None


class Insights(BaseModel):
    topics: list[Topic] = Field(default_factory=list)
    decisions: list[Decision] = Field(default_factory=list)
    action_items: list[ActionItem] = Field(default_factory=list)
    open_questions: list[OpenQuestion] = Field(default_factory=list)
    # Worries and concerns, including ones said off the record. They feed the internal
    # minutes only, and the external generator must never use them.
    risks: list[str] = Field(default_factory=list)
