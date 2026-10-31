import json
import logging
import re
import secrets
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from src.agent.schemas import (
    AgentInfo,
    AgentResponse,
    ChatRequest,
    ConfirmResponse,
    PendingActionView,
    Source,
)
from src.auth.schemas import Principal

logger = logging.getLogger("citysense.offline")

# In-memory storage for offline mode
PENDING_ACTIONS: dict[str, dict[str, Any]] = {}
OFFLINE_SESSIONS: dict[UUID, dict[str, Any]] = {}

# Initial seeded Dehradun complaints for the Worker Island
MOCK_COMPLAINTS: list[dict[str, Any]] = [
    {
        "tracking_id": "NND-2026-0841",
        "title": "Severe Pothole on Subhash Road near Clock Tower",
        "description": "Deep asphalt crater causing traffic bottleneck and accident risk near Central Bank.",
        "category": "Potholes and Road Damage",
        "status": "IN_PROGRESS",
        "priority": "HIGH",
        "ward": "Ward 24 - Paltan Bazaar",
        "location": {"lat": 30.3244, "lng": 78.0418, "address": "Subhash Road near Clock Tower, Dehradun"},
        "created_at": "2026-10-31T08:30:00Z",
        "warnings_count": 1,
        "assigned_worker": {"name": "Ramesh Negi", "team": "NND Rapid Road Unit 2"},
        "photo_url": "",
        "citizen": {"name": "Aditya Sharma"},
        "citizen_notification": {
            "message": "Nagar Nigam field crew Ramesh Negi (Unit 2) has been assigned. Work is underway.",
            "channel": "SMS & App"
        }
    },
    {
        "tracking_id": "NND-2026-0842",
        "title": "Non-functional LED Streetlights on Rajpur Road",
        "description": "5 consecutive streetlight poles are completely dark between Jakhan and IT Park turn.",
        "category": "Defective Streetlights",
        "status": "WARNING_1",
        "priority": "MEDIUM",
        "ward": "Ward 12 - Rajpur",
        "location": {"lat": 30.3541, "lng": 78.0700, "address": "Rajpur Road near Jakhan, Dehradun"},
        "created_at": "2026-10-31T09:15:00Z",
        "warnings_count": 2,
        "assigned_worker": {"name": "Sunil Rawat", "team": "Electrical Maintenance Division"},
        "photo_url": "",
        "citizen": {"name": "Pooja Verma"},
        "citizen_notification": {
            "message": "Escalated to JE Electrical: Streetlight repair ticket scheduled for tonight.",
            "channel": "WhatsApp"
        }
    },
    {
        "tracking_id": "NND-2026-0843",
        "title": "Overflowing Public Dustbin at Paltan Bazaar Entrance",
        "description": "Commercial waste accumulating on pedestrian sidewalk, emitting foul odor.",
        "category": "Garbage and Sanitation Dumps",
        "status": "ASSIGNED",
        "priority": "HIGH",
        "ward": "Ward 24 - Paltan Bazaar",
        "location": {"lat": 30.3225, "lng": 78.0392, "address": "Paltan Bazaar North Gate, Dehradun"},
        "created_at": "2026-10-31T10:00:00Z",
        "warnings_count": 0,
        "assigned_worker": {"name": "Vikram Chauhan", "team": "Sanitary Inspection Squad 4"},
        "photo_url": "",
        "citizen": {"name": "Rajesh Gupta"},
        "citizen_notification": {
            "message": "Compactor truck dispatched to Paltan Bazaar entrance. ETA 30 mins.",
            "channel": "SMS"
        }
    }
]


STOPWORDS = {
    "the", "and", "for", "with", "from", "that", "this", "are", "was", "were",
    "will", "can", "could", "would", "should", "you", "your", "tell", "give",
    "what", "when", "where", "which", "who", "whom", "whose", "why", "how",
    "all", "any", "both", "each", "few", "more", "most", "other", "some", "such",
    "than", "too", "very", "about", "above", "after", "again", "against",
    "between", "into", "through", "during", "before", "after", "below", "world",
    "to", "of", "in", "on", "at", "by", "is", "it", "an", "as", "be", "or",
    "है", "हैं", "था", "थी", "थे", "का", "के", "की", "को", "में", "से", "पर",
    "और", "या", "तो", "भी", "नहीं", "क्या", "कहाँ", "कब", "कैसे", "कौन", "किस",
    "बताओ", "दीजिए", "करें", "नियम", "बारे"
}


def tokenize(text: str) -> list[str]:
    raw = [w.strip().lower() for w in re.split(r'[\s\.,?!;:\"\'()\[\]{}।]+', text) if w.strip()]
    return [t for t in raw if len(t) > 2 and t not in STOPWORDS]


class OfflineCorpus:
    def __init__(self, corpus_root: Path):
        self.documents: list[dict[str, Any]] = []
        self._load(corpus_root)

    def _load(self, root: Path):
        if not root.exists():
            return
        for md_path in root.rglob("*.md"):
            if md_path.name == "README.md":
                continue
            meta_path = md_path.with_name(f"{md_path.stem}.meta.json")
            meta = {}
            if meta_path.exists():
                try:
                    meta = json.loads(meta_path.read_text(encoding="utf-8"))
                except Exception:
                    pass
            content = md_path.read_text(encoding="utf-8")
            # Extract title from markdown if not in meta
            title = meta.get("title")
            if not title:
                lines = content.strip().split("\n")
                title = lines[0].lstrip("# ").strip() if lines else md_path.stem
            doc_id = md_path.stem
            is_hindi = "_hi" in doc_id or meta.get("language") == "hi"
            self.documents.append({
                "doc_id": doc_id,
                "title": title,
                "url": meta.get("source_url") or "https://nagarnigamdehradun.com",
                "content": content,
                "language": "hi" if is_hindi else "en",
                "jurisdiction": meta.get("jurisdiction", "dehradun"),
                "publisher": meta.get("publisher", "Government of Uttarakhand")
            })
        logger.info("Loaded %d documents into offline corpus", len(self.documents))

    def search(self, query: str, language: str) -> list[tuple[dict[str, Any], float, str]]:
        """Performs token-based relevance scoring with language affinity."""
        query_tokens = tokenize(query)
        if not query_tokens:
            return []

        scored = []
        for doc in self.documents:
            doc_lang = doc["language"]
            lang_mult = 1.3 if doc_lang == language else 0.7
            doc_text = doc["content"].lower()
            doc_title = doc["title"].lower()

            matched_tokens = 0
            score = 0.0
            for token in query_tokens:
                in_title = token in doc_title
                in_text = token in doc_text
                if in_title:
                    score += 6.0
                    matched_tokens += 1
                elif in_text:
                    score += 1.5
                    matched_tokens += 1

            # Require at least 2 matching tokens or high title overlap if multi-word query
            if len(query_tokens) >= 2 and matched_tokens < 2 and score < 5.0:
                continue

            if score > 0:
                final_score = score * lang_mult
                excerpt = self._extract_excerpt(doc["content"], set(query_tokens))
                scored.append((doc, final_score, excerpt))

        scored.sort(key=lambda x: x[1], reverse=True)
        return scored

    def _extract_excerpt(self, content: str, tokens: set[str], max_len: int = 500) -> str:
        paragraphs = [p.strip() for p in content.split("\n\n") if p.strip() and not p.strip().startswith("#")]
        if not paragraphs:
            return content[:max_len]
        best_p = paragraphs[0]
        max_overlap = -1
        for p in paragraphs:
            p_tokens = set(re.findall(r"\w+", p.lower()))
            overlap = len(tokens.intersection(p_tokens))
            if overlap > max_overlap:
                max_overlap = overlap
                best_p = p
        return best_p[:max_len]


# Initialize corpus
CORPUS_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "corpus"
offline_corpus = OfflineCorpus(CORPUS_PATH)

# Complaint detection keywords
COMPLAINT_PATTERNS = [
    r"pothole", r"potholes", r"road damage", r"broken road",
    r"garbage", r"waste", r"dustbin", r"trash", r"cleaning",
    r"streetlight", r"street light", r"dark", r"power cut", r"wire",
    r"water leak", r"drain", r"sewage", r"manhole", r"encroachment",
    r"complaint", r"shikayat", r"report", r"issue",
    # Hindi patterns
    r"गड्ढा", r"गड्ढे", r"सड़क", r"कचरा", r"कूड़ा", r"सफाई",
    r"लाइट", r"स्ट्रीट लाइट", r"अंधेरा", r"बिजली", r"पानी",
    r"नाली", r"सीवर", r"मैनहोल", r"शिकायत", r"समस्या"
]


def detect_complaint_intent(text: str) -> bool:
    lower = text.lower()
    return any(re.search(pat, lower, re.IGNORECASE) for pat in COMPLAINT_PATTERNS)


async def offline_chat(
    principal: Principal,
    request: ChatRequest,
    started: float
) -> AgentResponse:
    session_id = request.sessionId or uuid4()
    message_id = uuid4()
    agent_id = request.agentId or "general"
    agent_name = "Municipal Grievance Officer" if agent_id == "municipal" else "City Sense"

    # Detect language
    is_hindi = (
        request.language == "hi"
        or any("\u0900" <= c <= "\u097f" for c in request.message)
    )
    lang = "hi" if is_hindi else "en"

    # 1. Action Check: Is this a complaint or service request to lodge?
    is_complaint = detect_complaint_intent(request.message)
    is_reporting = any(w in request.message.lower() for w in [
        "there is", "broken", "overflow", "not working", "fix", "please", "huge",
        "near", "at", "road", "खराब", "है", "टूटी", "गंदा", "कचरा", "भर गया", "करो"
    ])

    if is_complaint and (is_reporting or agent_id == "municipal"):
        token = secrets.token_hex(16)
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=15)

        category = "Civic Grievance"
        msg_l = request.message.lower()
        if "pothole" in msg_l or "road" in msg_l or "गड्ढा" in msg_l or "सड़क" in msg_l:
            category = "Potholes and Road Damage"
        elif "light" in msg_l or "streetlight" in msg_l or "लाइट" in msg_l:
            category = "Defective Streetlights"
        elif "garbage" in msg_l or "waste" in msg_l or "कूड़ा" in msg_l or "कचरा" in msg_l:
            category = "Garbage and Sanitation Dumps"
        elif "water" in msg_l or "drain" in msg_l or "नाली" in msg_l or "पानी" in msg_l:
            category = "Blocked Drains and Water Supply"

        summary = (
            f"Lodge {category} complaint with Nagar Nigam Dehradun"
            if lang == "en"
            else f"देहरादून नगर निगम में {category} संबंधी नागरिक शिकायत दर्ज करें"
        )

        PENDING_ACTIONS[token] = {
            "token": token,
            "user_id": principal.user_id,
            "agent_id": agent_id,
            "category": category,
            "summary": summary,
            "message": request.message,
            "expires_at": expires_at,
            "status": "pending",
            "city_id": request.context.cityId or "dehradun"
        }

        answer = (
            f"I have prepared a civic grievance draft under '{category}' for Nagar Nigam Dehradun based on your report. "
            "Please review the action card below and click 'Confirm' to dispatch the municipal inspection unit."
            if lang == "en"
            else
            f"मैंने आपकी रिपोर्ट के आधार पर देहरादून नगर निगम के लिए '{category}' श्रेणी में शिकायत का मसौदा तैयार किया है। "
            "कृपया नीचे दिए गए कार्ड की समीक्षा करें और संबंधित वार्ड निरीक्षण दल को भेजने के लिए 'Confirm' पर क्लिक करें।"
        )

        pending_view = PendingActionView(
            token=token,
            summary=summary,
            expiresAt=expires_at,
            action_type="create_complaint"
        )

        return AgentResponse(
            sessionId=session_id,
            messageId=message_id,
            status="ACTION_PENDING",
            answer=answer,
            agent=AgentInfo(id=agent_id, name=agent_name),
            sources=[],
            cta="confirm_complaint",
            pendingAction=pending_view,
            served="fallback"
        )

    # 2. Knowledge Retrieval from Verified Corpus
    hits = offline_corpus.search(request.message, lang)

    if not hits or hits[0][1] < 2.0:
        # Strict Abstain Rule
        abstain_msg = (
            "इस प्रश्न के लिए मेरे पास देहरादून नागरिक रिकॉर्ड में सत्यापित जानकारी नहीं है।"
            if lang == "hi"
            else
            "I do not have verified municipal information for that question in Dehradun civic records."
        )
        return AgentResponse(
            sessionId=session_id,
            messageId=message_id,
            status="ABSTAINED",
            answer=abstain_msg,
            agent=AgentInfo(id=agent_id, name=agent_name),
            sources=[],
            cta="file_complaint",
            served="fallback"
        )

    best_doc, score, excerpt = hits[0]
    sources = [
        Source(
            docId=best_doc["doc_id"],
            title=best_doc["title"],
            url=best_doc["url"],
            excerpt=excerpt,
            fetchedAt=datetime.now(timezone.utc),
            stale=False
        )
    ]

    # Format grounded response from excerpt
    if lang == "hi":
        answer = f"सत्यापित स्रोत ({best_doc['title']}) के अनुसार:\n\n{excerpt}"
    else:
        answer = f"Based on verified municipal records ({best_doc['title']}):\n\n{excerpt}"

    return AgentResponse(
        sessionId=session_id,
        messageId=message_id,
        status="ANSWERED",
        answer=answer,
        agent=AgentInfo(id=agent_id, name=agent_name),
        sources=sources,
        cta=None,
        served="fallback"
    )


def offline_confirm_action(principal: Principal, token: str) -> ConfirmResponse:
    action = PENDING_ACTIONS.get(token)
    if not action:
        return ConfirmResponse(status="rejected", detail="Action is invalid, expired, or already used")
    if action["status"] != "pending":
        return ConfirmResponse(status="rejected", detail=f"Action is already {action['status']}")
    if action["expires_at"] <= datetime.now(timezone.utc):
        action["status"] = "expired"
        return ConfirmResponse(status="rejected", detail="Action has expired")

    # Generate realistic tracking ID
    tracking_id = f"NND-2026-{secrets.randbelow(9000) + 1000}"
    action["status"] = "executed"
    action["result_ref"] = tracking_id

    # Add to complaints for Worker Island
    category = action.get("category", "Potholes and Road Damage")
    worker = "Ramesh Negi (Unit 2)" if "Road" in category else "Sunil Rawat (Electrical)"
    new_ticket = {
        "tracking_id": tracking_id,
        "title": action.get("summary", "Citizen Reported Civic Issue"),
        "description": action.get("message", "Citizen report lodged via City Sense Assistant."),
        "category": category,
        "status": "IN_PROGRESS",
        "priority": "HIGH",
        "ward": "Ward 14 - Rajpur Road",
        "location": {"lat": 30.3244, "lng": 78.0418, "address": "Rajpur Road, Dehradun"},
        "created_at": datetime.now(timezone.utc).isoformat(),
        "warnings_count": 0,
        "assigned_worker": {"name": worker, "team": "NND Field Unit"},
        "photo_url": "",
        "citizen": {"name": "Citizen (Mobile App)"},
        "citizen_notification": {
            "message": f"Your complaint {tracking_id} has been registered. Field crew dispatched.",
            "channel": "SMS & Push"
        }
    }
    MOCK_COMPLAINTS.insert(0, new_ticket)

    return ConfirmResponse(
        status="executed",
        result={
            "trackingId": tracking_id,
            "category": category,
            "status": "ASSIGNED",
            "message": f"Grievance {tracking_id} successfully registered with Nagar Nigam Dehradun."
        }
    )


def offline_cancel_action(principal: Principal, token: str) -> ConfirmResponse:
    action = PENDING_ACTIONS.get(token)
    if not action or action["status"] != "pending":
        return ConfirmResponse(status="rejected", detail="Action is invalid or already completed")
    action["status"] = "cancelled"
    return ConfirmResponse(status="cancelled", detail="Action cancelled successfully")


def offline_action_status(principal: Principal, token: str) -> dict[str, Any] | None:
    action = PENDING_ACTIONS.get(token)
    if not action:
        return None
    state = "expired" if action["status"] == "pending" and action["expires_at"] <= datetime.now(timezone.utc) else action["status"]
    return {
        "status": state,
        "summary": action["summary"],
        "expiresAt": action["expires_at"],
        "resultRef": action.get("result_ref")
    }


def get_all_complaints() -> list[dict[str, Any]]:
    return MOCK_COMPLAINTS


def resolve_complaint_by_id(tracking_id: str, resolution_note: str) -> dict[str, Any] | None:
    for c in MOCK_COMPLAINTS:
        if c["tracking_id"] == tracking_id:
            c["status"] = "RESOLVED"
            c["resolution_note"] = resolution_note
            c["resolved_at"] = datetime.now(timezone.utc).isoformat()
            c["citizen_notification"] = {
                "message": f"Resolved: {resolution_note}",
                "channel": "SMS & App"
            }
            return c
    return None
