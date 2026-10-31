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


class DensityArgs(ToolArgs):
    junction_id: str | None = Field(default=None, max_length=100)
    corridor_id: str | None = Field(default=None, max_length=100)


class CorridorArgs(ToolArgs):
    origin: str = Field(min_length=2, max_length=200)
    destination: str = Field(min_length=2, max_length=200)
    vehicle_type: str = Field(default="ambulance", min_length=2, max_length=50)


class UserArgs(ToolArgs):
    user_id: str = Field(min_length=1, max_length=100)


TOOL_MODELS = {
    "ask_clarification": ClarificationArgs,
    "create_complaint": ComplaintArgs,
    "get_complaint_status": StatusArgs,
    "handoff": HandoffArgs,
    "get_events": QueryArgs,
    "get_active_alerts": QueryArgs,
    "search_schemes": QueryArgs,
    "get_traffic_density": DensityArgs,
    "get_emergency_corridor": CorridorArgs,
    "list_user_complaints": UserArgs,
}

READ_TOOL_NAMES = {
    "get_events",
    "get_active_alerts",
    "get_complaint_status",
    "get_traffic_density",
    "get_emergency_corridor",
    "list_user_complaints",
}


def tool_schemas(allowed: list[str]) -> list[dict]:
    descriptions = {
        "ask_clarification": "Ask the citizen a targeted clarifying question when required fields are missing.",
        "create_complaint": "Propose a civic complaint for citizen confirmation. Never executed directly without user confirmation.",
        "get_complaint_status": "Get the current tracking status and progress update of a municipal complaint.",
        "handoff": "Handoff the conversation to a specialized agent persona.",
        "get_events": "Query upcoming civic, cultural, or municipal public events.",
        "get_active_alerts": "Retrieve active city emergency alerts, weather advisories, or road works.",
        "search_schemes": "Search municipal citizen schemes and civic policies.",
        "get_traffic_density": "Get real-time traffic density, congestion index, and wait times for a junction or corridor.",
        "get_emergency_corridor": "Activate or query an emergency green wave corridor between origin and destination.",
        "list_user_complaints": "List active and historical municipal complaints filed by a citizen.",
    }
    return [
        {
            "type": "function",
            "function": {
                "name": name,
                "description": descriptions.get(
                    name, f"{name.replace('_', ' ')}. A complaint is only proposed, never executed here."
                ),
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


def _get_mock_data(name: str, args: dict, user_id: str = "") -> dict:
    if name == "get_complaint_status":
        tracking_id = args.get("tracking_id", "")
        sample_statuses = {
            "NND-2026-0841": {
                "status": "IN_PROGRESS",
                "category": "Potholes and Road Damage",
                "location": "Subhash Road near Clock Tower, Dehradun",
                "description": "Deep asphalt crater causing traffic bottleneck and accident risk near Central Bank.",
                "assigned_worker": "Ramesh Negi (NND Rapid Road Unit 2)",
                "created_at": "2026-10-31T08:30:00Z",
                "estimated_resolution": "24 hours",
            },
            "NND-2026-0842": {
                "status": "ASSIGNED",
                "category": "Defective Streetlights",
                "location": "Rajpur Road near Jakhan, Dehradun",
                "description": "5 consecutive streetlight poles are completely dark between Jakhan and IT Park turn.",
                "assigned_worker": "Sunil Rawat (Electrical Maintenance Division)",
                "created_at": "2026-10-31T09:15:00Z",
                "estimated_resolution": "Tonight",
            },
            "NND-2026-0843": {
                "status": "ASSIGNED",
                "category": "Garbage and Sanitation Dumps",
                "location": "Paltan Bazaar North Gate, Dehradun",
                "description": "Commercial waste accumulating on pedestrian sidewalk, emitting foul odor.",
                "assigned_worker": "Vikram Chauhan (Sanitary Inspection Squad 4)",
                "created_at": "2026-10-31T10:00:00Z",
                "estimated_resolution": "2 hours",
            },
        }
        if tracking_id in sample_statuses:
            item = sample_statuses[tracking_id]
            return {
                "served": "fallback",
                "trackingId": tracking_id,
                "status": item["status"],
                "data": item,
                "simulated": True,
            }
        if tracking_id.startswith("MOCK-"):
            return {
                "served": "fallback",
                "trackingId": tracking_id,
                "status": "ACKNOWLEDGED",
                "data": {
                    "tracking_id": tracking_id,
                    "status": "ACKNOWLEDGED",
                    "category": "Civic Grievance",
                    "message": "Complaint acknowledged and queued for field unit assignment.",
                    "estimated_resolution": "48 hours",
                },
                "simulated": True,
            }
        return {
            "served": "fallback",
            "trackingId": tracking_id,
            "status": "not_found",
            "simulated": True,
        }

    if name == "get_events":
        query = (args.get("query") or "").lower()
        all_events = [
            {
                "id": "EVT-2026-01",
                "title": "Dehradun Cleanliness & Recycling Drive",
                "category": "Sanitation",
                "date": "2026-11-02",
                "time": "09:00 AM - 01:00 PM",
                "location": "Gandhi Park, Dehradun",
                "organizer": "Nagar Nigam Dehradun",
                "description": "Citizen volunteer drive for dry waste segregation and plastic-free market zones.",
            },
            {
                "id": "EVT-2026-02",
                "title": "Town Hall on Monsoon Drainage & Infrastructure",
                "category": "Civic Planning",
                "date": "2026-11-05",
                "time": "04:00 PM - 06:00 PM",
                "location": "Town Hall Auditorium, Nagar Nigam Complex",
                "organizer": "Municipal Engineering Wing",
                "description": "Public consultation session on culvert repairs and waterlogging mitigation.",
            },
            {
                "id": "EVT-2026-03",
                "title": "Uttarakhand Heritage Cultural & Craft Mela",
                "category": "Culture",
                "date": "2026-11-08",
                "time": "11:00 AM - 09:00 PM",
                "location": "Parade Ground, Dehradun",
                "organizer": "Department of Tourism & Culture",
                "description": "Exhibition of local Garhwali and Kumaoni handicrafts, organic produce, and folk music.",
            },
        ]
        if query:
            filtered = [
                e for e in all_events
                if query in e["title"].lower() or query in e["description"].lower() or query in e["category"].lower()
            ]
            items = filtered if filtered else all_events
        else:
            items = all_events
        return {"served": "fallback", "items": items, "simulated": True}

    if name == "get_active_alerts":
        all_alerts = [
            {
                "id": "ALT-2026-081",
                "severity": "WARNING",
                "badge": "TRAFFIC DIVERSION",
                "title": "Pipeline Repair & Traffic Diversion on Rajpur Road",
                "location": "Rajpur Road near Jakhan Turn",
                "description": "Drinking water pipeline repair work underway. Single lane operational; light vehicles advised to use Canal Road.",
                "issued_at": "2026-10-31T07:00:00Z",
                "valid_until": "2026-11-01T20:00:00Z",
                "authority": "Uttarakhand Jal Sansthan & Traffic Police",
            },
            {
                "id": "ALT-2026-082",
                "severity": "CRITICAL",
                "badge": "WEATHER ALERT",
                "title": "Heavy Rainfall Warning for Dehradun Foothills",
                "location": "Dehradun District & Surrounding Hills",
                "description": "IMD yellow alert for heavy rain and gusty winds. Avoid unnecessary travel near riverbanks and landslide-prone stretches.",
                "issued_at": "2026-10-31T06:30:00Z",
                "valid_until": "2026-11-01T18:00:00Z",
                "authority": "State Disaster Management Authority (SDMA)",
            },
            {
                "id": "ALT-2026-083",
                "severity": "INFO",
                "badge": "MAINTENANCE",
                "title": "Scheduled Power Feeder Maintenance in Prem Nagar",
                "location": "Prem Nagar Sector 3 & Cantonment Area",
                "description": "UPCL maintenance of 33kV transformer. Power outage scheduled from 10:00 AM to 01:00 PM tomorrow.",
                "issued_at": "2026-10-31T08:00:00Z",
                "valid_until": "2026-11-01T13:00:00Z",
                "authority": "Uttarakhand Power Corporation Limited (UPCL)",
            },
        ]
        return {"served": "fallback", "items": all_alerts, "simulated": True}

    if name == "get_traffic_density":
        junction = args.get("junction_id") or "Clock Tower Chowk"
        corridor = args.get("corridor_id") or "Rajpur Road Corridor"
        return {
            "served": "fallback",
            "simulated": True,
            "junction_id": junction,
            "corridor_id": corridor,
            "density_level": "MODERATE",
            "average_speed_kmh": 28.5,
            "congestion_index": 0.45,
            "wait_time_seconds": 90,
            "incident_flag": False,
            "recommended_alternate": "EC Road or Subhash Road",
            "timestamp": "2026-10-31T10:30:00Z",
        }

    if name == "get_emergency_corridor":
        origin = args.get("origin") or "Clock Tower, Dehradun"
        destination = args.get("destination") or "Max Super Speciality Hospital, Dehradun"
        vehicle_type = args.get("vehicle_type") or "ambulance"
        return {
            "served": "fallback",
            "simulated": True,
            "corridor_id": "CORR-EMG-08",
            "origin": origin,
            "destination": destination,
            "vehicle_type": vehicle_type,
            "status": "ACTIVE_CLEAR",
            "green_wave_active": True,
            "estimated_travel_time_minutes": 11,
            "normal_travel_time_minutes": 26,
            "signals_cleared": [
                "Clock Tower Junction",
                "Ashley Hall Chowk",
                "Rajpur Road - Jakhan Signal",
                "Malsi Crossing",
            ],
            "traffic_police_notified": True,
            "advisory": f"Emergency green wave corridor activated for {vehicle_type}. Traffic signals coordinated along route.",
        }

    if name == "list_user_complaints":
        uid = args.get("user_id") or user_id or "anonymous"
        return {
            "served": "fallback",
            "simulated": True,
            "user_id": uid,
            "complaints": [
                {
                    "tracking_id": "NND-2026-0841",
                    "category": "Potholes and Road Damage",
                    "location": "Subhash Road near Clock Tower, Dehradun",
                    "description": "Deep asphalt crater causing traffic bottleneck and accident risk near Central Bank.",
                    "status": "IN_PROGRESS",
                    "created_at": "2026-10-31T08:30:00Z",
                },
                {
                    "tracking_id": "NND-2026-0792",
                    "category": "Defective Streetlights",
                    "location": "Sahastradhara Road, Lane 4",
                    "description": "Streetlight pole flickering continuously for past 3 nights.",
                    "status": "RESOLVED",
                    "created_at": "2026-10-24T14:15:00Z",
                },
            ],
        }

    return {"served": "fallback", "items": [], "simulated": True}


async def read_tool(name: str, args: dict, user_id: str = "") -> dict:
    if name not in READ_TOOL_NAMES:
        raise ValueError(f"Unknown read tool: {name}")

    if name in TOOL_MODELS:
        validated_args = TOOL_MODELS[name].model_validate(args).model_dump(exclude_none=True)
    else:
        validated_args = args

    endpoint_map = {
        "get_events": settings.events_url,
        "get_active_alerts": settings.alerts_url,
        "get_complaint_status": settings.complaint_status_url,
        "get_traffic_density": settings.traffic_density_url,
        "get_emergency_corridor": settings.emergency_corridor_url,
        "list_user_complaints": settings.user_complaints_url,
    }
    endpoint = endpoint_map.get(name)

    if settings.demo_mode or not endpoint:
        return _get_mock_data(name, validated_args, user_id)

    params = validated_args.copy()
    if name == "get_complaint_status" and "{tracking_id}" in endpoint:
        endpoint = endpoint.replace("{tracking_id}", quote(str(validated_args.get("tracking_id", "")), safe=""))
        params.pop("tracking_id", None)
    elif name == "list_user_complaints" and "{user_id}" in endpoint:
        endpoint = endpoint.replace("{user_id}", quote(str(validated_args.get("user_id", user_id)), safe=""))
        params.pop("user_id", None)

    headers = (
        {"Authorization": f"Bearer {settings.adapter_api_key.get_secret_value()}"}
        if settings.adapter_api_key
        else {}
    )
    headers["X-User-ID"] = user_id or str(validated_args.get("user_id", ""))

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
