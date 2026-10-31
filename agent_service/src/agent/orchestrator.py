"""City Sense Supervisor Orchestrator.

Hierarchical Multi-Agent Architecture:
1. Input Guardrail: Prompt injection and jailbreak detection.
2. Scope Classification: Distinguish Injections, Out-of-Scope queries, Civic Greetings,
   Complaints, Emergencies, Live Data, and Knowledge inquiries.
3. Polite Refusal Engine: Empathetic, dignified boundaries with civic action chips.
4. Domain Specialists (Deterministic SOP Sub-Agents):
   - CivicComplaintSpecialist: Collect -> Deduplicate -> Propose -> Confirm SOP
   - EmergencySpecialist: Triage -> Corridor -> Guidance & Dispatch SOP
   - CityPulseSpecialist: Real-time alerts, events, traffic feeds SOP
   - KnowledgeSpecialist: Hybrid search, evidence verification, grounded citations SOP
"""

from __future__ import annotations

import logging
import time
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.agent.guardrails import (
    ActionChip,
    PoliteRefusalResult,
    QueryScope,
    build_polite_refusal,
    check_input_safety,
    classify_scope,
    refuse_injection,
    refuse_out_of_scope,
    respond_civic_greeting,
)
from src.agent.schemas import (
    AgentInfo,
    AgentResponse,
    ChatRequest,
    PendingActionView,
    Source,
)
from src.agent.subagents import (
    BaseSubAgent,
    CityPulseSpecialist,
    CivicComplaintSpecialist,
    EmergencySpecialist,
    KnowledgeSpecialist,
    SubAgentResult,
)
from src.auth.schemas import Principal
from src.config import settings
from src.models import AgentConfig, ChatSession

logger = logging.getLogger("citysense.orchestrator")


class SupervisorOrchestrator:
    """Top-level supervisor managing guardrails, subagents, and app data tools."""

    def __init__(self) -> None:
        self.complaint_agent = CivicComplaintSpecialist()
        self.emergency_agent = EmergencySpecialist()
        self.city_pulse_agent = CityPulseSpecialist()
        self.knowledge_agent = KnowledgeSpecialist()

    async def evaluate_turn(
        self,
        session: AsyncSession | None,
        principal: Principal,
        request: ChatRequest,
        chat_session: ChatSession,
        agent: AgentConfig,
        language: str,
        city: str,
        started: float,
    ) -> tuple[bool, str, str, list[Any], str | None, PendingActionView | None]:
        """Runs Guardrails and Sub-Agents.

        Returns:
            (handled, status, answer, sources, cta, pending_action)
            If handled is True, the response should be persisted and returned directly.
            If handled is False, execution falls through to the standard RAG / LLM path.
        """
        # Step 1: Input Guardrail Safety Inspection
        guard_res = check_input_safety(request.message)
        if not guard_res.is_safe:
            logger.warning(
                "Prompt injection / unsafe input detected for user %s: reason=%s risk=%.2f",
                principal.user_id,
                guard_res.reason,
                guard_res.risk_score,
            )
            refusal: PoliteRefusalResult = refuse_injection(language=language)
            return (
                True,
                "ANSWERED",
                refusal.message,
                [],
                refusal.suggested_cta or "explore_schemes",
                None,
            )

        # Step 2: Scope Classification & Polite Refusal Check
        scope_res = classify_scope(request.message, language=language)

        if scope_res.scope == QueryScope.CIVIC_GREETING:
            greeting: PoliteRefusalResult = respond_civic_greeting(language=language)
            return (
                True,
                "ANSWERED",
                greeting.message,
                [],
                greeting.suggested_cta or "report_issue",
                None,
            )

        if scope_res.scope == QueryScope.OUT_OF_SCOPE:
            # If it's an explicit detected off-topic domain (coding, math, cooking, trivia)
            if scope_res.detected_topic and scope_res.detected_topic not in (
                "non-civic general inquiry",
                "empty_query",
            ):
                refusal = refuse_out_of_scope(
                    topic=scope_res.detected_topic, language=language
                )
                return (
                    True,
                    "ANSWERED",
                    refusal.message,
                    [],
                    refusal.suggested_cta or "explore_schemes",
                    None,
                )
            # Otherwise, allow arbitrary inquiries to fall through to RAG to check verified civic evidence

        # Step 3: Domain Specialist Sub-Agent Routing
        # If the persona is explicitly set to a specialist or query is complaint/emergency/live
        if scope_res.scope == QueryScope.CIVIC_COMPLAINT and agent.agent_id != "municipal":
            # Civic Complaint Specialist SOP:
            # 1. Parse & validate fields
            # 2. Clarify if missing
            # 3. Deduplication check
            # 4. Propose pending action (agent proposes, user disposes)
            sub_res: SubAgentResult = await self.complaint_agent.execute(
                session=session,
                principal=principal,
                message=request.message,
                context=request.context,
                language=language,
            )
            pending_view = None
            if sub_res.action and sub_res.action.get("token"):
                pending_view = PendingActionView(
                    token=sub_res.action["token"],
                    summary=sub_res.action["summary"],
                    expiresAt=sub_res.action["expires_at"],
                    action_type=sub_res.action.get("action_type", "create_complaint"),
                )
            return (
                True,
                sub_res.status,
                sub_res.response_text,
                sub_res.sources,
                sub_res.cta,
                pending_view,
            )

        if scope_res.scope == QueryScope.CIVIC_EMERGENCY:
            # Emergency Specialist SOP:
            # 1. Triage severity
            # 2. Query corridor / density
            # 3. Deliver citizen safety guidance
            sub_res = await self.emergency_agent.execute(
                session=session,
                principal=principal,
                message=request.message,
                context=request.context,
                language=language,
            )
            return (
                True,
                sub_res.status,
                sub_res.response_text,
                sub_res.sources,
                sub_res.cta,
                None,
            )

        if scope_res.scope == QueryScope.CIVIC_LIVE_DATA:
            # City Pulse Specialist SOP:
            # 1. Fetch live alerts & events
            # 2. Format live briefing
            sub_res = await self.city_pulse_agent.execute(
                session=session,
                principal=principal,
                message=request.message,
                context=request.context,
                language=language,
            )
            return (
                True,
                sub_res.status,
                sub_res.response_text,
                sub_res.sources,
                sub_res.cta,
                None,
            )

        # Step 4: Falls through to RAG Knowledge Retrieval & Evidence Verification
        return (False, "", "", [], None, None)


# Global supervisor instance
supervisor = SupervisorOrchestrator()
