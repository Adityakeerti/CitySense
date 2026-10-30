package com.citysense.civic;

import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import java.util.List;
import java.util.UUID;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PatchMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;

@RestController
@Tag(name = "Civic", description = "Citizen complaints, municipal grievances, and city events")
public class CivicController {

    private final CivicService civicService;

    public CivicController(CivicService civicService) {
        this.civicService = civicService;
    }

    @PostMapping("/api/complaints")
    @ResponseStatus(HttpStatus.CREATED)
    @Operation(summary = "Submit a citizen grievance with auto-department classification and observation ingestion")
    public CivicDtos.ComplaintResponse fileComplaint(@Valid @RequestBody CivicDtos.ComplaintCreateRequest req) {
        return civicService.fileComplaint(req, null);
    }

    @GetMapping("/api/complaints")
    @Operation(summary = "List all complaints with optional filtering by status or department")
    public List<CivicDtos.ComplaintResponse> listComplaints(
            @RequestParam(required = false) String status,
            @RequestParam(required = false) String department) {
        return civicService.listComplaints(status, department);
    }

    @GetMapping("/api/complaints/{trackingId}")
    @Operation(summary = "Track a complaint by tracking ID (e.g. CS-2026-12345)")
    public CivicDtos.ComplaintResponse getComplaint(@PathVariable String trackingId) {
        return civicService.getComplaint(trackingId);
    }

    @PatchMapping("/api/complaints/{id}/status")
    @Operation(summary = "Worker or admin updates complaint resolution status with notes")
    public CivicDtos.ComplaintResponse updateStatus(
            @PathVariable UUID id,
            @Valid @RequestBody CivicDtos.ComplaintStatusUpdateRequest req) {
        return civicService.updateStatus(id, req);
    }

    @GetMapping("/api/city-events")
    @Operation(summary = "List public city events, alerts, and community notices")
    public List<CivicDtos.CityEventResponse> listCityEvents() {
        return civicService.listCityEvents();
    }

    @PostMapping("/api/city-events")
    @ResponseStatus(HttpStatus.CREATED)
    @Operation(summary = "Create a city event or public bulletin notice")
    public CivicDtos.CityEventResponse createCityEvent(@Valid @RequestBody CivicDtos.CityEventCreateRequest req) {
        return civicService.createCityEvent(req);
    }
}
