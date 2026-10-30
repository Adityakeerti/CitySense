"""Predictive Emergency Routing Engine with Historical Jam Clearance Analysis."""

from typing import List, Optional
from pydantic import BaseModel
from routing.graph import RoadGraph, PathResult, ActiveJam
from routing.traffic_history import TrafficHistoryDB


class JamEvaluation(BaseModel):
    segment_id: str
    ambulance_reach_time_minutes: float  # t_reach
    predicted_clearance_time_minutes: float  # t_clear
    will_clear_before_arrival: bool
    residual_delay_minutes: float
    explanation: str


class PredictiveRouteDecision(BaseModel):
    selected_path: PathResult
    rerouted: bool
    nominal_fastest_path: PathResult
    alternative_path: Optional[PathResult] = None
    reason: str
    jam_evaluations: List[JamEvaluation]


class PredictiveRouter:
    """Evaluates routes and determines whether to preserve the fastest path or reroute."""

    def __init__(self, graph: RoadGraph, history_db: Optional[TrafficHistoryDB] = None):
        self.graph = graph
        self.history_db = history_db or TrafficHistoryDB()

    def plan_emergency_route(
        self, origin_node: str, destination_node: str
    ) -> Optional[PredictiveRouteDecision]:
        # 1. Compute fastest nominal path
        primary_path = self.graph.find_shortest_path(origin_node, destination_node)
        if not primary_path:
            return None

        # 2. Check for active jams on primary path
        if not primary_path.jams_encountered:
            return PredictiveRouteDecision(
                selected_path=primary_path,
                rerouted=False,
                nominal_fastest_path=primary_path,
                reason="Primary fastest path is completely clear of traffic jams.",
                jam_evaluations=[],
            )

        jam_evaluations: List[JamEvaluation] = []
        avoid_edges: List[str] = []
        total_unavoidable_delay = 0.0

        for jam in primary_path.jams_encountered:
            # Time for ambulance to reach the jam segment
            t_reach = self.graph.estimate_travel_time_to_segment(primary_path, jam.segment_id)

            # Historical clearance prediction
            t_clear = self.history_db.predict_clearance_time_from_now(
                segment_id=jam.segment_id,
                severity=jam.severity,
                started_minutes_ago=jam.started_minutes_ago,
            )

            # Core Decision Rule:
            # If ambulance arrives after or as jam clears (t_reach >= t_clear), DO NOT REROUTE
            if t_reach >= t_clear:
                will_clear = True
                residual_delay = 0.0
                explanation = (
                    f"Jam on '{jam.segment_id}' will clear in {t_clear:.1f} mins from now. "
                    f"Ambulance will arrive in {t_reach:.1f} mins. "
                    f"Traffic will be cleared by arrival -> PRESERVE PATH."
                )
            else:
                will_clear = False
                # Remaining delay ambulance will suffer
                residual_delay = min(jam.delay_minutes, max(1.0, t_clear - t_reach))
                total_unavoidable_delay += residual_delay
                avoid_edges.append(jam.segment_id)
                explanation = (
                    f"Jam on '{jam.segment_id}' will persist for {t_clear:.1f} mins. "
                    f"Ambulance will arrive in {t_reach:.1f} mins (before clearance). "
                    f"Estimated residual delay: {residual_delay:.1f} mins -> CANDIDATE FOR REROUTE."
                )

            jam_evaluations.append(
                JamEvaluation(
                    segment_id=jam.segment_id,
                    ambulance_reach_time_minutes=round(t_reach, 2),
                    predicted_clearance_time_minutes=round(t_clear, 2),
                    will_clear_before_arrival=will_clear,
                    residual_delay_minutes=round(residual_delay, 2),
                    explanation=explanation,
                )
            )

        # If all jams will clear before arrival, do not reroute
        if not avoid_edges:
            return PredictiveRouteDecision(
                selected_path=primary_path,
                rerouted=False,
                nominal_fastest_path=primary_path,
                reason="All jams on fastest path are predicted to clear before ambulance arrives. No reroute needed.",
                jam_evaluations=jam_evaluations,
            )

        # 3. If there are persistent jams, compute alternative path avoiding them
        alternative_path = self.graph.find_shortest_path(
            origin_node, destination_node, avoid_edges=avoid_edges
        )

        effective_primary_time = primary_path.nominal_time_minutes + total_unavoidable_delay

        if alternative_path and alternative_path.nominal_time_minutes < effective_primary_time:
            reason = (
                f"Rerouting: Alternative path ({alternative_path.nominal_time_minutes:.1f} mins) "
                f"is faster than staying on primary path with persistent jam delay "
                f"({effective_primary_time:.1f} mins)."
            )
            return PredictiveRouteDecision(
                selected_path=alternative_path,
                rerouted=True,
                nominal_fastest_path=primary_path,
                alternative_path=alternative_path,
                reason=reason,
                jam_evaluations=jam_evaluations,
            )
        else:
            reason = (
                f"Staying on primary path: Even with persistent delay ({effective_primary_time:.1f} mins), "
                f"it remains optimal compared to alternatives."
            )
            return PredictiveRouteDecision(
                selected_path=primary_path,
                rerouted=False,
                nominal_fastest_path=primary_path,
                alternative_path=alternative_path,
                reason=reason,
                jam_evaluations=jam_evaluations,
            )
