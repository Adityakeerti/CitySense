import asyncio
import json
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.agent import service
from src.agent.schemas import (
    AgentResponse,
    ChatRequest,
    ConfirmResponse,
    PersonaView,
    SessionCreate,
    SessionView,
)
from src.auth.dependencies import current_principal
from src.auth.schemas import Principal
from src.config import settings
from src.database import get_session
from src.models import AgentConfig, ChatMessage, ChatSession, PendingAction, utcnow
from src.providers.speech import transcribe_with_fallback
from src.rate_limit import check_rate_limit

router = APIRouter(prefix="/api/agent", tags=["agent"])
Session = Annotated[AsyncSession, Depends(get_session)]
User = Annotated[Principal, Depends(current_principal)]


@router.post("/chat", response_model=AgentResponse)
async def chat(payload: ChatRequest, request: Request, session: Session, principal: User):
    if not getattr(request.app.state, "embedder_ready", False):
        raise HTTPException(503, "EMBEDDER_UNAVAILABLE: check /ready")
    check_rate_limit(principal.user_id)
    if len(payload.message) > settings.max_message_length:
        raise HTTPException(422, "Message exceeds configured length limit")
    try:
        async with asyncio.timeout(settings.request_timeout_seconds):
            response = await service.chat(session, principal, payload)
    except TimeoutError as exc:
        await session.rollback()
        raise HTTPException(504, "Chat request timed out; retry with the same requestId") from exc
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if "text/event-stream" in request.headers.get("accept", ""):

        async def frames():
            yield f"data: {json.dumps({'t': 'token', 'v': response.answer}, ensure_ascii=False)}\n\n"
            yield f"data: {json.dumps({'t': 'final', **response.model_dump(mode='json')}, ensure_ascii=False)}\n\n"

        return StreamingResponse(
            frames(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )
    return response


@router.get("/personas", response_model=list[PersonaView])
async def personas(session: Session, principal: User) -> list[PersonaView]:
    agents = (await session.scalars(select(AgentConfig).where(AgentConfig.active.is_(True)))).all()
    return [PersonaView(id=a.agent_id, name=a.display_name, tier=a.tier) for a in agents]


@router.post("/sessions", response_model=SessionView, status_code=201)
async def create_session(payload: SessionCreate, session: Session, principal: User) -> SessionView:
    try:
        return await service.create_session(session, principal, payload.agentId, payload.language)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/sessions", response_model=list[SessionView])
async def sessions(
    session: Session, principal: User, offset: int = 0, limit: int = 50
) -> list[SessionView]:
    records = (
        await session.scalars(
            select(ChatSession)
            .where(ChatSession.user_id == principal.user_id)
            .order_by(ChatSession.updated_at.desc())
            .offset(max(offset, 0))
            .limit(min(max(limit, 1), 100))
        )
    ).all()
    return [
        SessionView(sessionId=s.session_id, agentId=s.agent_id, language=s.language)
        for s in records
    ]


@router.get("/sessions/{session_id}/messages")
async def history(
    session_id: UUID, session: Session, principal: User, offset: int = 0, limit: int = 50
):
    owned = await session.scalar(
        select(ChatSession).where(
            ChatSession.session_id == session_id, ChatSession.user_id == principal.user_id
        )
    )
    if not owned:
        raise HTTPException(404, "Session not found")
    messages = (
        await session.scalars(
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at)
            .offset(max(offset, 0))
            .limit(min(max(limit, 1), 100))
        )
    ).all()
    return [
        {
            "messageId": m.message_id,
            "role": m.role,
            "content": m.content,
            "status": m.status,
            "createdAt": m.created_at,
            "response": m.meta.get("response"),
        }
        for m in messages
    ]


@router.post("/voice")
async def voice(
    principal: User,
    file: Annotated[UploadFile, File()],
    language: Annotated[str | None, Form()] = None,
):
    check_rate_limit(principal.user_id)
    if language not in {None, "en", "hi"}:
        raise HTTPException(422, "Language must be en or hi")
    from pathlib import Path

    if Path(file.filename or "").suffix.lower() not in {
        ".wav",
        ".mp3",
        ".mp4",
        ".m4a",
        ".mpeg",
        ".mpga",
        ".ogg",
        ".webm",
        ".flac",
    }:
        raise HTTPException(415, "Unsupported audio format")
    data = await file.read(settings.max_upload_bytes + 1)
    if not data or len(data) > settings.max_upload_bytes:
        raise HTTPException(
            413, "Audio must be nonempty and no larger than the configured upload limit"
        )
    try:
        text, lang, _provider = await transcribe_with_fallback(
            data, file.filename or "recording.wav", language
        )
    except Exception as exc:
        raise HTTPException(503, "STT_UNAVAILABLE: use keyboard dictation") from exc
    if not text.strip():
        raise HTTPException(503, "STT_UNAVAILABLE: use keyboard dictation")
    return {"text": text, "lang": lang}


@router.post("/actions/{token}/confirm", response_model=ConfirmResponse)
async def confirm(token: str, session: Session, principal: User) -> ConfirmResponse:
    return await service.confirm_action(session, principal, token)


@router.get("/actions/{token}")
async def action_status(token: str, session: Session, principal: User):
    action = await session.scalar(select(PendingAction).where(PendingAction.token == token, PendingAction.user_id == principal.user_id))
    if not action:
        raise HTTPException(404, "Action not found")
    state = "expired" if action.status == "pending" and action.expires_at <= utcnow() else action.status
    return {"status": state, "summary": action.summary, "expiresAt": action.expires_at, "resultRef": action.result_ref}


@router.post("/actions/{token}/cancel", response_model=ConfirmResponse)
async def cancel(token: str, session: Session, principal: User) -> ConfirmResponse:
    return await service.cancel_action(session, principal, token)
