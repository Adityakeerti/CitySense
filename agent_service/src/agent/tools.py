import hashlib
import json
from urllib.parse import quote

import httpx
from pydantic import BaseModel, ConfigDict, Field

from src.config import settings


class ToolArgs(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class ComplaintArgs(ToolArgs):
    category: str = Field(min_length=2, max_length=100)
    location: str = Field(min_length=3, max_length=500)
    description: str = Field(min_length=10, max_length=4000)


class StatusArgs(ToolArgs):
    tracking_id: str = Field(min_length=3, max_length=100, pattern=r"^[a-zA-Z0-9_-]+$")


class HandoffArgs(ToolArgs):
    agent_id: str = Field(min_length=1, max_length=100)


class QueryArgs(ToolArgs):
    query: str = Field(default="", max_length=500)


class ClarificationArgs(ToolArgs):
    question: str = Field(min_length=3, max_length=1000)


TOOL_MODELS = {
    "ask_clarification": ClarificationArgs,
    "create_complaint": ComplaintArgs,
    "get_complaint_status": StatusArgs,
    "handoff": HandoffArgs,
    "get_events": QueryArgs,
    "get_active_alerts": QueryArgs,
    "search_schemes": QueryArgs,
}


def tool_schemas(allowed: list[str]) -> list[dict]:
    return [
        {
            "type": "function",
            "function": {
                "name": name,
                "description": f"{name.replace('_', ' ')}. A complaint is only proposed, never executed here.",
                "parameters": TOOL_MODELS[name].model_json_schema(),
            },
        }
        for name in allowed
        if name in TOOL_MODELS
    ]


def args_hash(args: dict) -> str:
    return hashlib.sha256(
        json.dumps(args, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    ).hexdigest()


async def read_tool(name: str, args: dict, user_id: str = "") -> dict:
    if name not in {"get_events", "get_active_alerts", "get_complaint_status"}:
        raise ValueError("Unknown read tool")
    endpoint = {
        "get_events": settings.events_url,
        "get_active_alerts": settings.alerts_url,
        "get_complaint_status": settings.complaint_status_url,
    }[name]
    if settings.demo_mode or not endpoint:
        if name == "get_complaint_status":
            return {
                "served": "fallback",
                "trackingId": args["tracking_id"],
                "status": "not_found",
                "simulated": True,
            }
        return {"served": "fallback", "items": [], "simulated": True}
    params = args
    if name == "get_complaint_status" and "{tracking_id}" in endpoint:
        endpoint = endpoint.replace("{tracking_id}", quote(args["tracking_id"], safe=""))
        params = {}
    headers = (
        {"Authorization": f"Bearer {settings.adapter_api_key.get_secret_value()}"}
        if settings.adapter_api_key
        else {}
    )
    headers["X-User-ID"] = user_id
    async with httpx.AsyncClient(timeout=10, follow_redirects=False) as client:
        result = await client.get(endpoint, params=params, headers=headers)
        result.raise_for_status()
        return {"served": "live", "data": result.json()}


async def execute_complaint(args: dict, token: str, user_id: str = "") -> dict:
    ComplaintArgs.model_validate(args)
    if settings.demo_mode or not settings.complaint_adapter_url:
        return {
            "trackingId": f"MOCK-{hashlib.sha256(token.encode()).hexdigest()[:12].upper()}",
            "simulated": True,
        }
    headers = {"Idempotency-Key": token, "X-User-ID": user_id}
    if settings.adapter_api_key:
        headers["Authorization"] = f"Bearer {settings.adapter_api_key.get_secret_value()}"
    async with httpx.AsyncClient(timeout=10, follow_redirects=False) as client:
        response = await client.post(settings.complaint_adapter_url, json=args, headers=headers)
        response.raise_for_status()
        result = response.json()
        if not isinstance(result, dict) or not result.get("trackingId"):
            raise ValueError("Complaint adapter must return trackingId")
        return result
