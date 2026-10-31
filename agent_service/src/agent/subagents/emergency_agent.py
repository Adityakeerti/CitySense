import re
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from src.agent.subagents.base import BaseSubAgent, SubAgentResult
from src.agent.tools import read_tool
from src.auth.schemas import Principal


CRITICAL_KEYWORDS = {
    "ambulance",
    "fire",
    "fire truck",
    "fire brigade",
    "accident",
    "crash",
    "collision",
    "casualty",
    "emergency",
    "hospital",
    "injured",
    "injury",
    "trapped",
    "road block",
    "blocked road",
    "hazard",
    "collapsed",
    "आग",
    "दुर्घटना",
    "एम्बुलेंस",
    "दमकल",
    "हादसा",
    "गंभीर",
    "घायल",
}

ADVISORY_KEYWORDS = {
    "traffic",
    "jam",
    "congestion",
    "slow",
    "delay",
    "bottleneck",
    "diversion",
    "rush",
    "slow traffic",
    "भीड़",
    "जाम",
    "धीमी",
    "धीमी गति",
}


def parse_origin_destination(text: str) -> tuple[str, str]:
    match = re.search(
        r"(?:from|से)\s+([A-Za-z0-9\s,.-]+?)\s+(?:to|तक|जाना)\s+([A-Za-z0-9\s,.-]+)",
        text,
        re.IGNORECASE,
    )
    if match:
        orig = match.group(1).strip()
        dest = match.group(2).strip()
        if len(orig) >= 3 and len(dest) >= 3:
            return orig, dest
    return "Clock Tower, Dehradun", "Max Super Speciality Hospital, Dehradun"


class EmergencySpecialist(BaseSubAgent):
    name: str = "emergency_traffic"
    description: str = "Specialist for emergency green wave corridor coordination, incident triage, and traffic safety guidance"

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
        lower_msg = message.lower()

        # Step 1: triage_severity
        execution_steps.append("triage_severity")

        is_critical = any(kw in lower_msg for kw in CRITICAL_KEYWORDS)
        severity = "CRITICAL" if is_critical else "ADVISORY"

        if "fire" in lower_msg or "दमकल" in lower_msg:
            vehicle_type = "fire_truck"
        else:
            vehicle_type = "ambulance"

        # Step 2: query_corridor
        execution_steps.append("query_corridor")

        action: dict[str, Any] | None = None
        corridor_data: dict[str, Any] = {}
        traffic_data: dict[str, Any] = {}

        if severity == "CRITICAL":
            origin, dest = parse_origin_destination(message)
            origin = kwargs.get("origin") or origin
            dest = kwargs.get("destination") or dest
            corridor_res = await read_tool(
                "get_emergency_corridor",
                {"origin": origin, "destination": dest, "vehicle_type": vehicle_type},
                user_id=principal.user_id,
            )
            corridor_data = corridor_res.get("data") if corridor_res.get("served") == "live" else corridor_res
        else:
            corridor_id = kwargs.get("corridor_id") or "Rajpur Road Corridor"
            junction_id = kwargs.get("junction_id") or "Clock Tower Chowk"
            traffic_res = await read_tool(
                "get_traffic_density",
                {"corridor_id": corridor_id, "junction_id": junction_id},
                user_id=principal.user_id,
            )
            traffic_data = traffic_res.get("data") if traffic_res.get("served") == "live" else traffic_res

        # Step 3: generate_guidance
        execution_steps.append("generate_guidance")

        if severity == "CRITICAL":
            corridor_id = corridor_data.get("corridor_id", "CORR-EMG-08")
            action = {
                "action_type": "emergency_dispatch",
                "tool": "get_emergency_corridor",
                "severity": "CRITICAL",
                "vehicle_type": vehicle_type,
                "corridor_id": corridor_id,
                "origin": corridor_data.get("origin", "Clock Tower, Dehradun"),
                "destination": corridor_data.get("destination", "Max Super Speciality Hospital, Dehradun"),
                "status": "DISPATCH_FLAGGED",
                "admin_dispatch_required": True,
            }

            eta = corridor_data.get("estimated_travel_time_minutes", 11)
            normal_time = corridor_data.get("normal_travel_time_minutes", 26)
            signals = ", ".join(corridor_data.get("signals_cleared", ["Clock Tower", "Rajpur Road", "Jakhan"]))

            if language == "hi":
                response_text = (
                    "🚨 **आपातकालीन ग्रीन कॉरिडोर सूचना (EMERGENCY DISPATCH)**\n\n"
                    f"• **प्राथमिकता:** अति गंभीर (CRITICAL) - {vehicle_type.upper()}\n"
                    f"• **कॉरिडोर रूट:** {corridor_data.get('origin')} ➔ {corridor_data.get('destination')}\n"
                    f"• **ग्रीन वेव स्थिति:** सक्रिय (अनुमानित यात्रा समय: {eta} मिनट, सामान्य: {normal_time} मिनट)\n"
                    f"• **समन्वित सिग्नल्स:** {signals}\n\n"
                    "⚠️ **नागरिक सुरक्षा निर्देश:**\n"
                    "1. कृपया तत्काल बाईं ओर वाहन रोकें और आपातकालीन वाहन को रास्ता दें।\n"
                    "2. लेन 1 को पूरी तरह खाली रखें।\n"
                    "3. आपातकालीन सहायता हेल्पलाइन: **112** (पुलिस/सार्वभौमिक), **108** (एम्बुलेंस), **101** (अग्निशमन)।\n\n"
                    "*ट्रैफिक पुलिस नियंत्रण कक्ष को तत्काल ग्रीन वेव प्राथमिकता के लिए सूचित कर दिया गया है।*"
                )
            else:
                response_text = (
                    "🚨 **EMERGENCY CORRIDOR ACTIVATION & SAFETY ADVISORY**\n\n"
                    f"• **Priority Level:** CRITICAL - {vehicle_type.upper()}\n"
                    f"• **Corridor Route:** {corridor_data.get('origin')} ➔ {corridor_data.get('destination')}\n"
                    f"• **Green Wave Status:** ACTIVE (ETA: {eta} mins vs {normal_time} mins standard)\n"
                    f"• **Signals Coordinated:** {signals}\n\n"
                    "⚠️ **Immediate Citizen Safety Instructions:**\n"
                    "1. Pull over to the left immediately and yield right of way to approaching emergency vehicles.\n"
                    "2. Keep Lane 1 completely clear along this corridor.\n"
                    "3. Emergency Helplines: Call **112** (Integrated Emergency), **108** (Ambulance), **101** (Fire).\n\n"
                    "*Action flagged for Central Traffic Command admin dispatch and signal coordination.*"
                )

            return SubAgentResult(
                status="ACTION_PENDING",
                response_text=response_text,
                action=action,
                cta="dispatch_emergency",
                execution_steps=execution_steps,
                metadata={
                    "severity": "CRITICAL",
                    "corridor_data": corridor_data,
                    "action": action,
                },
            )

        # Advisory guidance
        density = traffic_data.get("density_level", "MODERATE")
        speed = traffic_data.get("average_speed_kmh", 28.5)
        wait_time = traffic_data.get("wait_time_seconds", 90)
        alternate = traffic_data.get("recommended_alternate", "EC Road or Subhash Road")

        if language == "hi":
            response_text = (
                "🚗 **ट्रैफिक स्थिति एवं नागरिक मार्ग सलाह (TRAFFIC ADVISORY)**\n\n"
                f"• **जंक्शन / कॉरिडोर:** {traffic_data.get('junction_id', 'Clock Tower')} | {traffic_data.get('corridor_id', 'Rajpur Road')}\n"
                f"• **यातायात घनत्व:** {density} (औसत गति: {speed} किमी/घंटा, प्रतीक्षा समय: ~{wait_time} सेकंड)\n"
                f"• **वैकल्पिक सुझाई गई मार्ग:** {alternate}\n\n"
                "🛡️ **सुरक्षा निर्देश:** कृपया सुरक्षित दूरी बनाए रखें और जंक्शन बॉक्स को ब्लॉक न करें। गति सीमा का पालन करें।"
            )
        else:
            response_text = (
                "🚗 **TRAFFIC DENSITY & ROUTE ADVISORY**\n\n"
                f"• **Junction / Corridor:** {traffic_data.get('junction_id', 'Clock Tower')} | {traffic_data.get('corridor_id', 'Rajpur Road')}\n"
                f"• **Traffic Density:** {density} (Avg speed: {speed} km/h, Wait time: ~{wait_time}s)\n"
                f"• **Recommended Alternate Route:** {alternate}\n\n"
                "🛡️ **Safety Guidance:** Maintain safe braking distance, do not block yellow box junctions, and yield to pedestrian crossings."
            )

        return SubAgentResult(
            status="ANSWERED",
            response_text=response_text,
            action=None,
            cta="view_alternate_routes",
            execution_steps=execution_steps,
            metadata={
                "severity": "ADVISORY",
                "traffic_data": traffic_data,
            },
        )
