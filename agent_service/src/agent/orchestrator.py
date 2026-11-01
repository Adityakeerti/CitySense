"""City Sense main voice agent: guardrails -> planner -> strict delegation -> merged answer.

Pipeline per turn
1. Input guardrail (prompt injection / jailbreak).
2. Scope classification + polite refusals for greetings and clearly off-topic requests.
3. ``VoiceAgentPlanner`` decomposes the utterance into ordered steps (planner lives only here).
4. Steps execute in order:
   - main-agent steps call ONLY cross-cutting tools the main agent owns (location resolution);
   - every domain step is delegated to exactly one specialist, which is the sole caller of its
     domain tools (enforced by ``tool_registry.call_tool``).
5. Specialist results are merged into one citizen-facing answer with the plan and tool trace.

Knowledge-only turns fall through to the retrieval + LLM pipeline in ``service.py``.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from src.agent.guardrails import (
    PoliteRefusalResult,
    QueryScope,
    check_input_safety,
    classify_scope,
    refuse_injection,
    refuse_out_of_scope,
    respond_civic_greeting,
)
from src.agent.planner import ExecutionPlan, PlanStep, planner
from src.agent.schemas import ChatRequest, PendingActionView, PlanStepView, ToolCallView
from src.agent.subagents import (
    CityPulseSpecialist,
    CivicComplaintSpecialist,
    EmergencySpecialist,
    KnowledgeSpecialist,
    SubAgentResult,
)
from src.agent.subagents.complaint_agent import extract_location
from src.agent.tool_registry import COMPLAINT, EMERGENCY, KNOWLEDGE, MAIN, PULSE, ToolTrace, call_tool
from src.auth.schemas import Principal
from src.models import AgentConfig, ChatSession

logger = logging.getLogger("citysense.orchestrator")

COMPLAINT_CONTEXT_WORDS = ("complaint", "ticket", "grievance", "शिकायत")
COMPLAINT_FOLLOWUP_WORDS = (
    "active", "all", "show", "list", "check", "open", "pending", "status", "which are", "सक्रिय", "दिखाओ",
)
STATUS_PRIORITY = ["ACTION_PENDING", "CLARIFICATION_REQUIRED", "HANDOFF_REQUIRED", "ANSWERED", "ABSTAINED", "UNAVAILABLE"]


@dataclass
class TurnOutcome:
    handled: bool
    status: str = ""
    answer: str = ""
    sources: list[Any] = field(default_factory=list)
    cta: str | None = None
    pending_action: PendingActionView | None = None
    plan: list[PlanStepView] | None = None
    tool_calls: list[ToolCallView] | None = None
    action_data: dict[str, Any] | None = None


def _refusal(result: PoliteRefusalResult, default_cta: str) -> TurnOutcome:
    return TurnOutcome(True, "ANSWERED", result.message, [], result.suggested_cta or default_cta)


def _plan_view(plan: ExecutionPlan) -> list[PlanStepView]:
    return [
        PlanStepView(id=s.id, executor=s.executor, action=s.action, tools=s.tools, status=s.status, detail=s.detail)
        for s in plan.steps
    ]


def _trace_view(trace: ToolTrace) -> list[ToolCallView]:
    return [
        ToolCallView(tool=c.tool, caller=c.caller, served=c.served, ok=c.ok, durationMs=c.duration_ms)
        for c in trace.calls
    ]


def _is_complaint_followup(message: str, history: list[dict[str, Any]] | None) -> bool:
    if not history:
        return False
    recent = " ".join(m.get("content", "") for m in history[-2:] if isinstance(m, dict) and m.get("content"))
    recent = recent.lower()
    return any(w in recent for w in COMPLAINT_CONTEXT_WORDS) and any(
        w in message.lower() for w in COMPLAINT_FOLLOWUP_WORDS
    )


def finalize_plan(plan: list[PlanStepView] | None, status: str) -> list[PlanStepView] | None:
    """Close out steps answered downstream (knowledge fall-through) with the turn's real outcome."""
    for step in plan or []:
        if step.status == "planned":
            step.status = "failed" if status == "UNAVAILABLE" else "completed"
            step.detail = f"retrieval pipeline: {status}"
    return plan


class SupervisorOrchestrator:
    """Main voice agent: owns the planner and the cross-cutting tools; delegates everything else."""

    name = MAIN

    def __init__(self) -> None:
        self.complaint_agent = CivicComplaintSpecialist()
        self.emergency_agent = EmergencySpecialist()
        self.city_pulse_agent = CityPulseSpecialist()
        self.knowledge_agent = KnowledgeSpecialist()
        self.specialists = {
            COMPLAINT: self.complaint_agent,
            EMERGENCY: self.emergency_agent,
            PULSE: self.city_pulse_agent,
            KNOWLEDGE: self.knowledge_agent,
        }

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
        history: list[dict[str, Any]] | None = None,
    ) -> TurnOutcome:
        """Run guardrails, plan, and delegated execution.

        ``handled=False`` means the caller should continue with the retrieval + LLM pipeline;
        ``plan`` is still populated so that response can show it.
        """
        # 1. Input guardrail
        from src.agent.events import turn_meta

        meta = turn_meta.get()
        guard = check_input_safety(request.message)
        if meta is not None:
            meta["guard"] = {"safe": guard.is_safe, "risk": round(guard.risk_score, 2), "reason": guard.reason}
        if not guard.is_safe:
            logger.warning("Unsafe input from %s: reason=%s risk=%.2f", principal.user_id, guard.reason, guard.risk_score)
            return _refusal(refuse_injection(language=language), "explore_schemes")

        # 2. Scope + polite refusals
        scope = classify_scope(request.message, language=language)
        if meta is not None:
            meta["scope"] = scope.scope.value
        if scope.scope == QueryScope.CIVIC_GREETING:
            return _refusal(respond_civic_greeting(language=language), "report_issue")
        if scope.scope == QueryScope.OUT_OF_SCOPE and scope.detected_topic and scope.detected_topic not in (
            "non-civic general inquiry",
            "empty_query",
        ):
            return _refusal(refuse_out_of_scope(topic=scope.detected_topic, language=language), "explore_schemes")

        # 3. Plan
        ctx = request.context
        has_coords = ctx.latitude is not None and ctx.longitude is not None
        location = extract_location(request.message)
        plan = planner.plan(
            request.message,
            scope.scope,
            language,
            complaint_followup=_is_complaint_followup(request.message, history),
            location=location,
            has_coordinates=has_coords,
        )
        if agent.agent_id == "municipal":
            # The municipal persona files complaints through its LLM tool loop in service.py.
            plan.steps = [s for s in plan.steps if s.executor != COMPLAINT]

        domain_steps = [s for s in plan.steps if s.executor not in (MAIN, KNOWLEDGE)]
        if not domain_steps:
            return TurnOutcome(handled=False, plan=_plan_view(plan) if plan.steps else None)

        # 4. Execute
        trace = ToolTrace()
        resolved: dict[str, Any] = {"location": location}
        if has_coords:
            resolved.update(latitude=ctx.latitude, longitude=ctx.longitude)
        results: list[tuple[PlanStep, SubAgentResult]] = []

        for step in plan.steps:
            step.status = "running"
            try:
                if step.executor == MAIN:
                    step.detail = await self._run_main_step(step, request, principal, resolved, trace)
                    step.status = "completed"
                    continue
                if step.executor == KNOWLEDGE:
                    step.status = "skipped"
                    continue
                specialist = self.specialists[step.executor]
                result = await specialist.execute(
                    session=session,
                    principal=principal,
                    message=request.message,
                    context=ctx,
                    language=language,
                    history=history,
                    session_id=getattr(chat_session, "session_id", None),
                    location=resolved.get("location"),
                    latitude=resolved.get("latitude"),
                    longitude=resolved.get("longitude"),
                    trace=trace,
                )
                results.append((step, result))
                step.status = "completed"
                step.detail = result.status
            except Exception:
                logger.exception("Plan step %s (%s) failed", step.id, step.executor)
                step.status = "failed"

        if not results:
            return TurnOutcome(handled=False, plan=_plan_view(plan), tool_calls=_trace_view(trace))
        return self._merge(plan, results, trace, resolved, language)

    async def _run_main_step(
        self, step: PlanStep, request: ChatRequest, principal: Principal, resolved: dict[str, Any], trace: ToolTrace
    ) -> str:
        """Main agent executes only the cross-cutting tools it owns."""
        if "verify_citizen_location" in step.tools and resolved.get("location"):
            res = await call_tool(MAIN, "verify_citizen_location", {"query": resolved["location"]},
                                  principal.user_id, trace)
            data = res.get("data", res)
            if resolved.get("latitude") is None and data.get("lat") is not None:
                resolved.update(latitude=data["lat"], longitude=data["lng"])
            resolved["zone"] = data.get("zone")
            resolved["precision"] = data.get("precision")
            return f"{resolved['location']} → {data.get('lat')}, {data.get('lng')} ({data.get('precision')})"
        if "reverse_geocode_coordinates" in step.tools:
            res = await call_tool(MAIN, "reverse_geocode_coordinates",
                                  {"lat": resolved["latitude"], "lng": resolved["longitude"]}, principal.user_id, trace)
            data = res.get("data", res)
            resolved["location"] = data.get("nearest_landmark") or data.get("display_name")
            resolved["zone"] = data.get("zone")
            return f"GPS → near {resolved['location']}"
        return "nothing to resolve"

    @staticmethod
    def _merge(
        plan: ExecutionPlan,
        results: list[tuple[PlanStep, SubAgentResult]],
        trace: ToolTrace,
        resolved: dict[str, Any],
        language: str,
    ) -> TurnOutcome:
        statuses = [r.status for _, r in results]
        status = min(statuses, key=lambda s: STATUS_PRIORITY.index(s) if s in STATUS_PRIORITY else len(STATUS_PRIORITY))
        answer = "\n\n---\n\n".join(r.response_text for _, r in results if r.response_text)
        # Emergency CTA wins: life safety first.
        cta = next((r.cta for st, r in results if st.executor == EMERGENCY and r.cta), None) or next(
            (r.cta for _, r in results if r.cta), None
        )
        pending = None
        action_data: dict[str, Any] = {}
        sources: list[Any] = []
        for st, r in results:
            sources.extend(r.sources or [])
            if r.action and r.action.get("token") and pending is None:
                pending = PendingActionView(
                    token=r.action["token"],
                    summary=r.action["summary"],
                    expiresAt=r.action["expires_at"],
                    action_type=r.action.get("action_type", "create_complaint"),
                )
            if st.executor == EMERGENCY and r.action:
                action_data["emergency"] = r.action
            if r.metadata.get("card"):
                action_data[st.executor] = r.metadata["card"]
        if resolved.get("location"):
            action_data["location"] = {
                k: resolved.get(k) for k in ("location", "latitude", "longitude", "zone", "precision")
            }
        return TurnOutcome(
            handled=True,
            status=status,
            answer=answer,
            sources=sources,
            cta=cta,
            pending_action=pending,
            plan=_plan_view(plan),
            tool_calls=_trace_view(trace),
            action_data=action_data or None,
        )


# Global supervisor instance
supervisor = SupervisorOrchestrator()
