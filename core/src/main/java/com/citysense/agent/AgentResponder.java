package com.citysense.agent;

import java.time.Instant;
import java.util.List;
import java.util.Locale;
import java.util.UUID;
import org.springframework.stereotype.Component;

/**
 * Persona reply engine used by every chat surface in core (agent tab and avatar chat).
 * Currently a keyword responder; the seam where the Python agent_service will be plugged in.
 */
@Component
public class AgentResponder {

    public AgentDtos.ChatResponse respond(AgentDtos.ChatRequest req) {
        String sessId = req.sessionId() != null && !req.sessionId().isBlank() ? req.sessionId() : UUID.randomUUID().toString();
        String persona = req.persona() != null ? req.persona().toUpperCase(Locale.ROOT) : "CIVIC";
        String lang = req.language() != null ? req.language() : "en";
        String msg = req.message().toLowerCase(Locale.ROOT);

        String reply;
        List<String> sources;
        boolean abstained = false;

        if (msg.contains("pothole") || msg.contains("road") || msg.contains("gaddha")) {
            reply = "hi".equalsIgnoreCase(lang)
                    ? "सड़क पर गड्ढे की शिकायत नगर निगम (PWD) को दर्ज की जा सकती है। आप 'Report' टैब से फोटो और जीपीएस लोकेशन भेज सकते हैं। तुरंत कार्रवाई की जाएगी।"
                    : "Potholes and road damages can be reported under the PWD Department via the 'Report' tab with GPS coordinates and a photo.";
            sources = List.of("Uttarakhand PWD Citizen Charter 2026", "Dehradun Municipal Corporation By-laws Sec 14");
        } else if (msg.contains("water") || msg.contains("leak") || msg.contains("paani")) {
            reply = "hi".equalsIgnoreCase(lang)
                    ? "पानी की आपूर्ति या पाइपलाइन लीकेज संबंधी समस्या उत्तराखंड जल संस्थान को भेजी जाती है। ट्रैकिंग आईडी तुरंत जारी होगी।"
                    : "Water supply disruption or pipeline leaks are routed to Uttarakhand Jal Sansthan. You will receive an instant tracking ID upon submission.";
            sources = List.of("Uttarakhand Jal Sansthan Service Directory");
        } else if (msg.contains("rain") || msg.contains("flood") || msg.contains("baarish") || msg.contains("underpass")) {
            reply = "hi".equalsIgnoreCase(lang)
                    ? "मौसम विभाग (Open-Meteo) के अनुसार देहरादून में वर्षा की निगरानी की जा रही है। राजपुर रोड अंडरपास में 25 सेमी से अधिक जलभराव होने पर ईसी रोड बाईपास का उपयोग करें।"
                    : "Live weather monitoring indicates active surveillance for Dehradun underpasses. When water depth exceeds 25cm, emergency traffic is diverted via EC Road Bypass.";
            sources = List.of("Dehradun Smart City Disaster Management SOP", "Open-Meteo Inundation Telemetry");
        } else if (msg.contains("hospital") || msg.contains("ambulance") || msg.contains("aspatal")) {
            reply = "hi".equalsIgnoreCase(lang)
                    ? "आपातकालीन स्थिति में दून अस्पताल (सरकारी) और मैक्स सुपर स्पेशियलिटी अस्पताल 24x7 ट्रॉमा केयर और एम्बुलेंस सहायता प्रदान करते हैं।"
                    : "For medical emergencies, Doon Hospital (Government, Level 1 Trauma) and Max Super Speciality Hospital operate 24x7 emergency response with active corridor preemption.";
            sources = List.of("Dehradun District Emergency Medical Network");
        } else {
            reply = "hi".equalsIgnoreCase(lang)
                    ? "मैं आपकी स्मार्ट सिटी सेवाओं में सहायता कर सकता हूँ। आप शिकायत दर्ज करने, यातायात, मौसम या आपातकालीन सेवाओं के बारे में पूछ सकते हैं।"
                    : "I am your CitySense Assistant. I can help you report civic grievances, check live weather/flood routes, or coordinate emergency services.";
            sources = List.of("CitySense Knowledge Base v2.0");
        }

        return new AgentDtos.ChatResponse(
                sessId,
                reply,
                persona,
                lang,
                sources,
                abstained,
                Instant.now()
        );
    }
}
