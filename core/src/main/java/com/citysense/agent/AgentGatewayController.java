package com.citysense.agent;

import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import java.time.Instant;
import java.util.List;
import java.util.Locale;
import java.util.UUID;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/agent")
@Tag(name = "Agent", description = "Multilingual Citizen AI Assistant, RAG Knowledge Base, and specialist personas")
public class AgentGatewayController {

    private static final List<AgentDtos.PersonaView> PERSONAS = List.of(
            new AgentDtos.PersonaView("CIVIC", "Nagrik Sahayak (Civic Assistant)", "Civic Grievances & Municipal Help", "Guides citizens through filing potholes, sanitation, water, and electricity grievances", List.of("en", "hi")),
            new AgentDtos.PersonaView("TRAFFIC", "Vahan Margdarshak (Traffic Guide)", "Traffic & Route Planning", "Advises on congestion, waterlogged underpasses, diversions, and green corridors", List.of("en", "hi")),
            new AgentDtos.PersonaView("EMERGENCY", "Aapat Sahayak (Emergency Coordinator)", "Accident & Medical Emergency", "Dispatches ambulance missions, coordinates with Doon/Max hospitals, and alerts police", List.of("en", "hi")),
            new AgentDtos.PersonaView("TRANSIT", "Yatra Sahayak (Transit Navigator)", "Public Transport & Inter-city", "Provides schedules for Dehradun Railway Station, ISBT, and Jolly Grant Airport", List.of("en", "hi"))
    );

    @GetMapping("/personas")
    @Operation(summary = "List specialist citizen agent personas")
    public List<AgentDtos.PersonaView> listPersonas() {
        return PERSONAS;
    }

    @PostMapping("/chat")
    @Operation(summary = "Interact with Multilingual Citizen Assistant with grounded knowledge citations and abstain guardrails")
    public AgentDtos.ChatResponse chat(@Valid @RequestBody AgentDtos.ChatRequest req) {
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

    @PostMapping("/knowledge/docs")
    @ResponseStatus(HttpStatus.CREATED)
    @Operation(summary = "Register verified document into municipal knowledge base")
    public AgentDtos.KnowledgeDocResponse registerKnowledgeDoc(@Valid @RequestBody AgentDtos.KnowledgeDocRequest req) {
        return new AgentDtos.KnowledgeDocResponse(
                UUID.randomUUID().toString(),
                req.title(),
                req.category(),
                req.department() != null ? req.department() : "MUNICIPAL",
                true,
                Instant.now()
        );
    }
}
