import asyncio
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from src.agent.subagents.base import BaseSubAgent, SubAgentResult
from src.agent.tools import read_tool
from src.auth.schemas import Principal


class CityPulseSpecialist(BaseSubAgent):
    name: str = "city_pulse"
    description: str = "Specialist for real-time city alerts, upcoming public events, and citizen pulse briefings"

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

        # Step 1: fetch_city_data in parallel
        execution_steps.append("fetch_city_data")

        query_str = kwargs.get("query") or message
        alerts_task = read_tool("get_active_alerts", {"query": query_str}, user_id=principal.user_id)
        events_task = read_tool("get_events", {"query": query_str}, user_id=principal.user_id)

        alerts_res, events_res = await asyncio.gather(alerts_task, events_task, return_exceptions=True)

        alerts: list[dict[str, Any]] = (
            alerts_res.get("items", []) if isinstance(alerts_res, dict) else []
        )
        events: list[dict[str, Any]] = (
            events_res.get("items", []) if isinstance(events_res, dict) else []
        )

        # Step 2: format_briefing
        execution_steps.append("format_briefing")

        if language == "hi":
            lines = [
                "# 🌆 देहरादून सिटी पल्स: लाइव नागरिक बुलेटिन",
                "",
                "### 🚨 सक्रिय नागरिक चेतावनियाँ एवं अलर्ट (Active Alerts)",
            ]
            if alerts:
                for a in alerts:
                    severity = a.get("severity", "INFO")
                    badge = a.get("badge") or severity
                    title = a.get("title", "सूचना")
                    loc = a.get("location", "देहरादून")
                    desc = a.get("description", "")
                    lines.append(f"- `[{badge}]` **{title}**")
                    lines.append(f"  • *स्थान:* {loc}")
                    if desc:
                        lines.append(f"  • *विवरण:* {desc}")
            else:
                lines.append("- वर्तमान में कोई सक्रिय अलर्ट नहीं है।")

            lines.append("")
            lines.append("### 📅 आगामी सार्वजनिक एवं नागरिक कार्यक्रम (Upcoming Events)")
            if events:
                for e in events:
                    title = e.get("title", "कार्यक्रम")
                    date = e.get("date", "")
                    time_slot = e.get("time", "")
                    loc = e.get("location", "देहरादून")
                    desc = e.get("description", "")
                    lines.append(f"- 🗓️ **{date}** ({time_slot}) — **{title}**")
                    lines.append(f"  • *स्थान:* {loc}")
                    if desc:
                        lines.append(f"  • *विवरण:* {desc}")
            else:
                lines.append("- वर्तमान में कोई आगामी कार्यक्रम सूचीबद्ध नहीं है।")

            lines.append("")
            lines.append(f"📊 **सिटी पल्स स्थिति:** {len(alerts)} सक्रिय अलर्ट | {len(events)} आगामी नागरिक कार्यक्रम")

        else:
            lines = [
                "# 🌆 Dehradun City Pulse: Live Briefing",
                "",
                "### 🚨 Active City Alerts & Advisories",
            ]
            if alerts:
                for a in alerts:
                    severity = a.get("severity", "INFO")
                    badge = a.get("badge") or severity
                    title = a.get("title", "Alert")
                    loc = a.get("location", "Dehradun")
                    desc = a.get("description", "")
                    lines.append(f"- `[{badge}]` **{title}**")
                    lines.append(f"  • *Location:* {loc}")
                    if desc:
                        lines.append(f"  • *Details:* {desc}")
            else:
                lines.append("- No active emergency alerts at this time.")

            lines.append("")
            lines.append("### 📅 Upcoming Civic & Community Events")
            if events:
                for e in events:
                    title = e.get("title", "Event")
                    date = e.get("date", "")
                    time_slot = e.get("time", "")
                    loc = e.get("location", "Dehradun")
                    desc = e.get("description", "")
                    lines.append(f"- 🗓️ **{date}** ({time_slot}) — **{title}**")
                    lines.append(f"  • *Venue:* {loc}")
                    if desc:
                        lines.append(f"  • *Overview:* {desc}")
            else:
                lines.append("- No public events scheduled for this window.")

            lines.append("")
            lines.append(f"📊 **Live Digest Status:** {len(alerts)} active alerts | {len(events)} upcoming civic events")

        response_text = "\n".join(lines)

        return SubAgentResult(
            status="ANSWERED",
            response_text=response_text,
            sources=[],
            cta="view_alerts",
            execution_steps=execution_steps,
            metadata={
                "alerts_count": len(alerts),
                "events_count": len(events),
            },
        )
