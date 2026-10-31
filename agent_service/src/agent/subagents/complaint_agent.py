import re
import secrets
from datetime import timedelta
from typing import Any
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from src.agent.subagents.base import BaseSubAgent, SubAgentResult
from src.agent.tools import args_hash, read_tool
from src.auth.schemas import Principal
from src.config import settings
from src.models import utcnow


KNOWN_LANDMARKS = [
    "clock tower",
    "rajpur road",
    "subhash road",
    "paltan bazaar",
    "jakhan",
    "it park",
    "prem nagar",
    "sahastradhara road",
    "ballupur",
    "gandhi park",
    "parade ground",
    "dharampur",
    "karanpur",
    "ec road",
    "haridwar road",
    "chakrata road",
    "ghanta ghar",
    "घंटाघर",
    "राजपुर रोड",
    "पलटन बाजार",
    "गांधी पार्क",
]


def extract_category(text: str) -> str | None:
    lower = text.lower()
    if any(k in lower for k in ["pothole", "crater", "broken road", "road damage", "asphalt", "गड्ढा", "गड्ढे", "सड़क"]):
        return "Potholes and Road Damage"
    if any(k in lower for k in ["streetlight", "street light", "street lamp", "dark", "light", "स्ट्रीट लाइट", "अंधेरा", "लाइट"]):
        return "Defective Streetlights"
    if any(k in lower for k in ["garbage", "trash", "waste", "dustbin", "dump", "sanitation", "कूड़ा", "कचरा", "सफाई", "डस्टबिन"]):
        return "Garbage and Sanitation Dumps"
    if any(k in lower for k in ["water leak", "pipeline", "drain", "sewage", "manhole", "water supply", "सीवर", "नाली", "पानी", "मैनहोल"]):
        return "Blocked Drains and Water Supply"
    if any(k in lower for k in ["encroachment", "illegal parking", "footpath blocked", "अतिक्रमण"]):
        return "Encroachments and Traffic Obstructions"
    if any(k in lower for k in ["complaint", "grievance", "issue", "damaged", "broken", "overflow", "not working", "fix", "repair", "problem", "शिकायत", "समस्या"]):
        return "Civic Grievance"
    return None


def extract_location(text: str) -> str | None:
    lower = text.lower()
    # Check known landmarks first
    for landmark in KNOWN_LANDMARKS:
        if landmark in lower:
            # Expand context around the landmark
            idx = lower.find(landmark)
            segment = text[max(0, idx - 15):min(len(text), idx + len(landmark) + 20)].strip()
            # Clean segment
            segment = re.sub(r"^(?:at|near|on|in|opposite)\s+", "", segment, flags=re.IGNORECASE)
            return segment.strip(".,;: ")

    # Preposition pattern match (English)
    match = re.search(
        r"(?:at|near|on|in|opposite|around|close to|behind)\s+([A-Za-z0-9\s,.-]{3,60}?)(?:,|\.|$|\s+(?:and|because|causing|which|where|since|due|with))",
        text,
        re.IGNORECASE,
    )
    if match:
        loc = match.group(1).strip()
        if len(loc) >= 3 and loc.lower() not in {"the road", "the street", "my area", "this area"}:
            return loc

    # Hindi preposition pattern match
    hindi_match = re.search(
        r"([A-Za-z0-9\s\u0900-\u097f]{3,60}?)\s*(?:के पास|में|पर|रोड|चौक|मार्ग|बाजार|कॉलोनी|गली)",
        text,
    )
    if hindi_match:
        loc = hindi_match.group(1).strip()
        if len(loc) >= 3:
            return loc

    return None


class CivicComplaintSpecialist(BaseSubAgent):
    name: str = "civic_complaint"
    description: str = "Specialist for civic grievances, complaint intake, deduplication, and verification"

    async def execute(
        self,
        session: AsyncSession | None,
        principal: Principal,
        message: str,
        context: Any = None,
        language: str = "en",
        **kwargs: Any,
    ) -> SubAgentResult:
        execution_steps: list[str] = []

        # Step 1: Parse & validate required parameters (category, location, description)
        execution_steps.append("parse_and_validate")

        provided_args = kwargs.get("args") or {}
        category = (
            kwargs.get("category")
            or provided_args.get("category")
            or extract_category(message)
        )
        location = (
            kwargs.get("location")
            or provided_args.get("location")
            or extract_location(message)
        )
        description = (
            kwargs.get("description")
            or provided_args.get("description")
            or (message.strip() if len(message.strip()) >= 10 else None)
        )

        missing_fields: list[str] = []
        if not category:
            missing_fields.append("category")
        if not location:
            missing_fields.append("location")
        if not description:
            missing_fields.append("description")

        # Step 2: If required parameters missing, clarify missing fields
        if missing_fields:
            execution_steps.append("clarify_missing_fields")

            if language == "hi":
                if "location" in missing_fields and "category" not in missing_fields:
                    clarification = (
                        f"मैंने आपकी {category} संबंधी शिकायत दर्ज करने के लिए विवरण तैयार करना शुरू कर दिया है। "
                        "कृपया वह सटीक स्थान या लैंडमार्क (जैसे: सड़क, चौक, कॉलोनी) बताएं जहाँ यह समस्या है।"
                    )
                elif "category" in missing_fields and "location" not in missing_fields:
                    clarification = (
                        f"कृपया {location} पर आ रही विशिष्ट नागरिक समस्या (जैसे: गड्ढा, स्ट्रीट लाइट, कचरा, नाली) का विवरण दें।"
                    )
                else:
                    clarification = (
                        "नागरिक शिकायत दर्ज करने के लिए कृपया समस्या का प्रकार और सटीक स्थान (जैसे: 'राजपुर रोड पर गड्ढा') बताएं।"
                    )
            else:
                if "location" in missing_fields and "category" not in missing_fields:
                    clarification = (
                        f"I have identified this as a **{category}** issue. "
                        "Could you please specify the exact location or landmark (e.g., street name, chowk) where the issue is present?"
                    )
                elif "category" in missing_fields and "location" not in missing_fields:
                    clarification = (
                        f"Could you please describe the specific problem you are reporting at **{location}** (e.g., pothole, streetlight, garbage, drainage)?"
                    )
                else:
                    clarification = (
                        "To lodge your civic complaint, please provide both the issue description and its exact location (e.g., 'Broken streetlight near Jakhan, Rajpur Road')."
                    )

            return SubAgentResult(
                status="CLARIFICATION_REQUIRED",
                response_text=clarification,
                cta="provide_details",
                execution_steps=execution_steps,
                metadata={
                    "missing_fields": missing_fields,
                    "parsed": {
                        "category": category,
                        "location": location,
                        "description": description,
                    },
                },
            )

        # Step 3: Deduplication check
        execution_steps.append("deduplication_check")
        duplicate_match = None
        try:
            complaint_list_res = await read_tool("list_user_complaints", {"user_id": principal.user_id}, user_id=principal.user_id)
            existing_complaints = complaint_list_res.get("complaints", [])
            for c in existing_complaints:
                same_cat = c.get("category", "").lower() == category.lower()
                c_loc = c.get("location", "").lower()
                overlap = any(word in c_loc for word in location.lower().split() if len(word) > 3)
                if same_cat and overlap:
                    duplicate_match = c
                    break
        except Exception:
            pass

        # Step 4: Propose action
        execution_steps.append("propose_action")
        token = secrets.token_urlsafe(32)
        expires_at = utcnow() + timedelta(seconds=settings.action_ttl_seconds)
        summary = f"Complaint ({category}) at {location}: {description[:150]}"
        action_args = {
            "category": category,
            "location": location,
            "description": description,
        }

        action_dict = {
            "token": token,
            "action_type": "create_complaint",
            "tool": "create_complaint",
            "summary": summary,
            "args": action_args,
            "expires_at": expires_at.isoformat(),
        }

        # Persist pending action to DB or memory
        if session:
            try:
                from src.models import PendingAction
                session_id = kwargs.get("session_id") or uuid4()
                pending = PendingAction(
                    token=token,
                    session_id=session_id,
                    user_id=principal.user_id,
                    agent_id="municipal",
                    tool="create_complaint",
                    args=action_args,
                    args_hash=args_hash(action_args),
                    summary=summary,
                    expires_at=expires_at,
                )
                session.add(pending)
                await session.flush()
            except Exception:
                from src.agent.offline import PENDING_ACTIONS
                PENDING_ACTIONS[token] = {
                    "token": token,
                    "user_id": principal.user_id,
                    "agent_id": "municipal",
                    "category": category,
                    "summary": summary,
                    "args": action_args,
                    "expires_at": expires_at,
                    "status": "pending",
                }
        else:
            from src.agent.offline import PENDING_ACTIONS
            PENDING_ACTIONS[token] = {
                "token": token,
                "user_id": principal.user_id,
                "agent_id": "municipal",
                "category": category,
                "summary": summary,
                "args": action_args,
                "expires_at": expires_at,
                "status": "pending",
            }

        duplicate_note = ""
        if duplicate_match:
            duplicate_note = (
                f"\n\n*Notice: An active complaint (#{duplicate_match.get('tracking_id')}) with status '{duplicate_match.get('status')}' "
                f"was recently filed for this area.*"
                if language != "hi"
                else
                f"\n\n*सूचना: इस क्षेत्र में हाल ही में स्थिति '{duplicate_match.get('status')}' के साथ शिकायत (#{duplicate_match.get('tracking_id')}) पहले से दर्ज है।*"
            )

        if language == "hi":
            response_text = (
                f"मैंने देहरादून नगर निगम के लिए **{category}** श्रेणी में शिकायत का मसौदा तैयार किया है:\n\n"
                f"• **स्थान:** {location}\n"
                f"• **विवरण:** {description}\n\n"
                "कृपया नीचे दिए गए विवरण की समीक्षा करें और संबंधित वार्ड निरीक्षण दल को भेजने के लिए 'Confirm' पर क्लिक करें।"
                f"{duplicate_note}"
            )
        else:
            response_text = (
                f"I have prepared a civic grievance draft for **{category}**:\n\n"
                f"• **Location:** {location}\n"
                f"• **Description:** {description}\n\n"
                "Please review the action card below and confirm to dispatch the Nagar Nigam Dehradun field unit."
                f"{duplicate_note}"
            )

        return SubAgentResult(
            status="ACTION_PENDING",
            response_text=response_text,
            action=action_dict,
            cta="confirm_complaint",
            execution_steps=execution_steps,
            metadata={
                "token": token,
                "category": category,
                "location": location,
                "duplicate_found": duplicate_match is not None,
                "duplicate_tracking_id": duplicate_match.get("tracking_id") if duplicate_match else None,
            },
        )
