package com.citysense.civic;

import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;

public interface ComplaintRepository extends JpaRepository<Complaint, UUID> {
    Optional<Complaint> findByTrackingId(String trackingId);
    List<Complaint> findByStatus(String status);
    List<Complaint> findByDepartment(String department);
    List<Complaint> findAllByOrderByCreatedAtDesc();
}
