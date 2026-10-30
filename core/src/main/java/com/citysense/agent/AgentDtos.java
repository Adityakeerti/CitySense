package com.citysense.agent;

import jakarta.validation.constraints.NotBlank;
import java.time.Instant;
import java.util.List;
import java.util.Map;

public class AgentDtos {

    public record ChatRequest(
            @NotBlank String message,
            String persona,
            String language,
            String sessionId
    ) {}

    public record ChatResponse(
            String sessionId,
            String reply,
            String persona,
            String language,
            List<String> sources,
            boolean abstained,
            Instant timestamp
    ) {}

    public record PersonaView(
            String id,
            String name,
            String role,
            String description,
            List<String> supportedLanguages
    ) {}

    public record KnowledgeDocRequest(
            @NotBlank String title,
            @NotBlank String category,
            String department,
            String content,
            String sourceUrl
    ) {}

    public record KnowledgeDocResponse(
            String id,
            String title,
            String category,
            String department,
            boolean isVerified,
            Instant createdAt
    ) {}
}
