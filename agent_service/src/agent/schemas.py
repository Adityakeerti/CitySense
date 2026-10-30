from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ChatContext(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    cityId: str | None = Field(default=None, min_length=1, max_length=100)


class ChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    sessionId: UUID | None = None
    requestId: UUID
    agentId: str | None = Field(default=None, min_length=1, max_length=100)
    message: str = Field(min_length=1, max_length=4000)
    language: Literal["hi", "en"] | None = None
    context: ChatContext = Field(default_factory=ChatContext)


class AgentInfo(BaseModel):
    id: str
    name: str


class Source(BaseModel):
    docId: str
    title: str
    url: str | None
    excerpt: str
    fetchedAt: datetime
    stale: bool = False


class PendingActionView(BaseModel):
    token: str
    summary: str
    expiresAt: datetime


class AgentResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    sessionId: UUID
    messageId: UUID
    status: Literal[
        "ANSWERED",
        "CLARIFICATION_REQUIRED",
        "ABSTAINED",
        "HANDOFF_REQUIRED",
        "ACTION_PENDING",
        "UNAVAILABLE",
    ]
    answer: str
    agent: AgentInfo
    sources: list[Source] = Field(default_factory=list)
    cta: str | None = None
    handoff: dict[str, str] | None = None
    pendingAction: PendingActionView | None = None
    served: Literal["live", "cache", "fallback"]


class SessionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    agentId: str = Field(default="general", min_length=1, max_length=100)
    language: Literal["hi", "en"] | None = None


class SessionView(BaseModel):
    sessionId: UUID
    agentId: str
    language: str | None


class PersonaView(BaseModel):
    id: str
    name: str
    tier: str


class ConfirmResponse(BaseModel):
    status: Literal["executed", "failed", "rejected", "cancelled"]
    result: dict[str, Any] | None = None
    detail: str | None = None
