package com.citysense.civic;

import com.citysense.common.error.ApiException;
import com.citysense.platform.observation.ObservationDtos.ObservationRequest;
import com.citysense.platform.observation.ObservationService;
import com.citysense.platform.realtime.CityEventMessage;
import java.time.Instant;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.UUID;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.context.ApplicationEventPublisher;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class CivicService {

    private static final Logger log = LoggerFactory.getLogger(CivicService.class);

    private final ComplaintRepository complaintRepo;
    private final CityEventRepository cityEventRepo;
    private final ObservationService observationService;
    private final ApplicationEventPublisher eventPublisher;

    public CivicService(
            ComplaintRepository complaintRepo,
            CityEventRepository cityEventRepo,
            ObservationService observationService,
            ApplicationEventPublisher eventPublisher) {
        this.complaintRepo = complaintRepo;
        this.cityEventRepo = cityEventRepo;
        this.observationService = observationService;
        this.eventPublisher = eventPublisher;
    }

    @Transactional
    public CivicDtos.ComplaintResponse fileComplaint(CivicDtos.ComplaintCreateRequest req, UUID userId) {
        Complaint complaint = new Complaint();
        String trackingId = "CS-" + (System.currentTimeMillis() % 900000 + 100000);
        complaint.setTrackingId(trackingId);
        complaint.setUserId(userId);
        complaint.setCitizenName(req.citizenName() != null ? req.citizenName() : "Anonymous Citizen");
        complaint.setTitle(req.title());
        complaint.setDescription(req.description());
        complaint.setCategory(req.category() != null ? req.category() : "CIVIC");
        complaint.setPriority(req.priority() != null ? req.priority().toUpperCase(Locale.ROOT) : "MEDIUM");
        complaint.setStatus("FILED");
        complaint.setLatitude(req.latitude());
        complaint.setLongitude(req.longitude());
        complaint.setPhotoUrl(req.photoUrl());
        complaint.setEscalationLevel(0);

        // Auto-classify department if not provided
        String dept = req.department();
        if (dept == null || dept.isBlank() || "AUTO".equalsIgnoreCase(dept)) {
            dept = autoClassifyDepartment(req.title(), req.description());
        }
        complaint.setDepartment(dept);

        Complaint saved = complaintRepo.save(complaint);

        // Ingest into ObservationService so Member A's correlation engine clusters it
        try {
            ObservationRequest obsReq = new ObservationRequest(
                    com.citysense.platform.observation.ObservationType.COMPLAINT,
                    req.latitude(),
                    req.longitude(),
                    Instant.now(),
                    "civic-module",
                    0.95,
                    com.citysense.platform.observation.ObservationStatus.VERIFIED,
                    Map.of(
                            "trackingId", saved.getTrackingId(),
                            "title", saved.getTitle(),
                            "department", saved.getDepartment(),
                            "category", saved.getCategory()
                    )
            );
            observationService.ingest(obsReq, "civic-module");
        } catch (Exception e) {
            log.warn("Could not ingest observation for complaint {}: {}", saved.getTrackingId(), e.getMessage());
        }

        // Broadcast realtime notification
        eventPublisher.publishEvent(CityEventMessage.of("COMPLAINT_FILED", saved.getId(), CivicDtos.ComplaintResponse.from(saved)));

        return CivicDtos.ComplaintResponse.from(saved);
    }

    @Transactional(readOnly = true)
    public CivicDtos.ComplaintResponse getComplaint(String trackingId) {
        Complaint c = complaintRepo.findByTrackingId(trackingId)
                .orElseThrow(() -> new ApiException(HttpStatus.NOT_FOUND, "Complaint not found: " + trackingId));
        return CivicDtos.ComplaintResponse.from(c);
    }

    @Transactional(readOnly = true)
    public List<CivicDtos.ComplaintResponse> listMine(UUID userId) {
        return complaintRepo.findByUserIdOrderByCreatedAtDesc(userId).stream()
                .map(CivicDtos.ComplaintResponse::from).toList();
    }

    @Transactional(readOnly = true)
    public List<CivicDtos.ComplaintResponse> listComplaints(String status, String department) {
        List<Complaint> list;
        if (status != null && !status.isBlank()) {
            list = complaintRepo.findByStatus(status.toUpperCase(Locale.ROOT));
        } else if (department != null && !department.isBlank()) {
            list = complaintRepo.findByDepartment(department.toUpperCase(Locale.ROOT));
        } else {
            list = complaintRepo.findAllByOrderByCreatedAtDesc();
        }
        return list.stream().map(CivicDtos.ComplaintResponse::from).toList();
    }

    @Transactional
    public CivicDtos.ComplaintResponse updateStatus(UUID id, CivicDtos.ComplaintStatusUpdateRequest req) {
        Complaint c = complaintRepo.findById(id)
                .orElseThrow(() -> new ApiException(HttpStatus.NOT_FOUND, "Complaint not found with ID: " + id));

        String newStatus = req.status().toUpperCase(Locale.ROOT);
        c.setStatus(newStatus);
        c.setUpdatedAt(Instant.now());

        if (req.assignedWorker() != null && !req.assignedWorker().isBlank()) {
            c.setAssignedWorker(req.assignedWorker());
        }
        if (req.resolutionNotes() != null && !req.resolutionNotes().isBlank()) {
            c.setResolutionNotes(req.resolutionNotes());
        }
        if ("RESOLVED".equals(newStatus)) {
            c.setResolvedAt(Instant.now());
        }

        Complaint saved = complaintRepo.save(c);

        eventPublisher.publishEvent(CityEventMessage.of(
                "RESOLVED".equals(newStatus) ? "COMPLAINT_RESOLVED" : "COMPLAINT_STATUS_UPDATED",
                saved.getId(),
                CivicDtos.ComplaintResponse.from(saved)
        ));

        return CivicDtos.ComplaintResponse.from(saved);
    }

    @Transactional(readOnly = true)
    public List<CivicDtos.CityEventResponse> listCityEvents() {
        return cityEventRepo.findAllByOrderByStartsAtDesc()
                .stream()
                .map(CivicDtos.CityEventResponse::from)
                .toList();
    }

    @Transactional
    public CivicDtos.CityEventResponse createCityEvent(CivicDtos.CityEventCreateRequest req) {
        CityEvent event = new CityEvent();
        event.setTitle(req.title());
        event.setDescription(req.description());
        event.setCategory(req.category() != null ? req.category() : "COMMUNITY");
        event.setSeverity(req.severity() != null ? req.severity().toUpperCase(Locale.ROOT) : "INFO");
        event.setLatitude(req.latitude());
        event.setLongitude(req.longitude());
        event.setStartsAt(req.startsAt() != null ? req.startsAt() : Instant.now());
        event.setEndsAt(req.endsAt());

        CityEvent saved = cityEventRepo.save(event);

        eventPublisher.publishEvent(CityEventMessage.of("CITY_EVENT_CREATED", saved.getId(), CivicDtos.CityEventResponse.from(saved)));

        return CivicDtos.CityEventResponse.from(saved);
    }

    private String autoClassifyDepartment(String title, String desc) {
        String combined = (title + " " + desc).toLowerCase(Locale.ROOT);
        if (combined.contains("pothole") || combined.contains("road") || combined.contains("tar") || combined.contains("footpath") || combined.contains("divider")) {
            return "PWD_ROADS";
        }
        if (combined.contains("garbage") || combined.contains("trash") || combined.contains("waste") || combined.contains("drain") || combined.contains("clean") || combined.contains("sweep")) {
            return "SANITATION";
        }
        if (combined.contains("water") || combined.contains("pipe") || combined.contains("leak") || combined.contains("supply") || combined.contains("tap") || combined.contains("sewage")) {
            return "JAL_SANSTHAN";
        }
        if (combined.contains("light") || combined.contains("pole") || combined.contains("wire") || combined.contains("power") || combined.contains("meter") || combined.contains("blackout")) {
            return "ELECTRICITY";
        }
        if (combined.contains("traffic") || combined.contains("signal") || combined.contains("jam") || combined.contains("parking") || combined.contains("accident")) {
            return "TRAFFIC_POLICE";
        }
        return "MUNICIPAL";
    }
}
