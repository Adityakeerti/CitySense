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

    private final AgentResponder responder;

    public AgentGatewayController(AgentResponder responder) {
        this.responder = responder;
    }

    @GetMapping("/personas")
    @Operation(summary = "List specialist citizen agent personas")
    public List<AgentDtos.PersonaView> listPersonas() {
        return PERSONAS;
    }

    @PostMapping("/chat")
    @Operation(summary = "Interact with Multilingual Citizen Assistant with grounded knowledge citations and abstain guardrails")
    public AgentDtos.ChatResponse chat(@Valid @RequestBody AgentDtos.ChatRequest req) {
        return responder.respond(req);
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
