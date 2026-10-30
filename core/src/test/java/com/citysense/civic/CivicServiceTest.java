package com.citysense.civic;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.citysense.platform.observation.ObservationService;
import java.util.Optional;
import java.util.UUID;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.context.ApplicationEventPublisher;

class CivicServiceTest {

    private ComplaintRepository complaintRepo;
    private CityEventRepository cityEventRepo;
    private ObservationService observationService;
    private ApplicationEventPublisher eventPublisher;
    private CivicService service;

    @BeforeEach
    void setUp() {
        complaintRepo = mock(ComplaintRepository.class);
        cityEventRepo = mock(CityEventRepository.class);
        observationService = mock(ObservationService.class);
        eventPublisher = mock(ApplicationEventPublisher.class);
        service = new CivicService(complaintRepo, cityEventRepo, observationService, eventPublisher);
    }

    @Test
    void fileComplaintAutoClassifiesRoadsDepartment() {
        when(complaintRepo.save(any(Complaint.class))).thenAnswer(inv -> {
            Complaint c = inv.getArgument(0);
            c.setId(UUID.randomUUID());
            return c;
        });

        var req = new CivicDtos.ComplaintCreateRequest(
                "Large pothole near Clock Tower",
                "Dangerous deep pothole on main road causing traffic slow down",
                "CIVIC",
                "AUTO",
                "HIGH",
                30.3243,
                78.0418,
                "Aditya",
                null
        );

        var res = service.fileComplaint(req, null);

        assertThat(res.department()).isEqualTo("PWD_ROADS");
        assertThat(res.trackingId()).startsWith("CS-");
        assertThat(res.status()).isEqualTo("FILED");
        verify(observationService).ingest(any(), any());
    }

    @Test
    void fileComplaintAutoClassifiesSanitationDepartment() {
        when(complaintRepo.save(any(Complaint.class))).thenAnswer(inv -> {
            Complaint c = inv.getArgument(0);
            c.setId(UUID.randomUUID());
            return c;
        });

        var req = new CivicDtos.ComplaintCreateRequest(
                "Garbage pile at Paltan Bazaar",
                "Overflowing waste bins and trash not collected for three days",
                "CIVIC",
                null,
                "MEDIUM",
                30.3230,
                78.0400,
                "Shopkeeper",
                null
        );

        var res = service.fileComplaint(req, null);
        assertThat(res.department()).isEqualTo("SANITATION");
    }

    @Test
    void updateStatusToResolvedSetsResolvedAt() {
        UUID id = UUID.randomUUID();
        Complaint existing = new Complaint();
        existing.setId(id);
        existing.setTrackingId("CS-2026-99999");
        existing.setStatus("IN_PROGRESS");
        existing.setTitle("Water leakage");
        existing.setDescription("Pipe burst");
        existing.setCategory("CIVIC");
        existing.setDepartment("JAL_SANSTHAN");
        existing.setPriority("HIGH");

        when(complaintRepo.findById(id)).thenReturn(Optional.of(existing));
        when(complaintRepo.save(any(Complaint.class))).thenAnswer(inv -> inv.getArgument(0));

        var req = new CivicDtos.ComplaintStatusUpdateRequest(
                "RESOLVED",
                "Worker Ram Singh",
                "Main valve replaced and leak sealed successfully."
        );

        var res = service.updateStatus(id, req);
        assertThat(res.status()).isEqualTo("RESOLVED");
        assertThat(res.assignedWorker()).isEqualTo("Worker Ram Singh");
        assertThat(res.resolvedAt()).isNotNull();
    }
}
