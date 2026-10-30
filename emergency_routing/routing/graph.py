"""Road Network Graph and Pathfinding Utilities for Emergency Routing."""

from typing import Dict, List, Optional, Tuple
import heapq
import math
from pydantic import BaseModel


class RoadNode(BaseModel):
    id: str
    name: str
    latitude: float
    longitude: float


class ActiveJam(BaseModel):
    segment_id: str
    start_node: str
    end_node: str
    severity: float  # 0.0 (light slowdown) to 1.0 (deadlock)
    delay_minutes: float  # Current observed delay
    started_minutes_ago: float = 0.0


class RoadEdge(BaseModel):
    id: str
    start_node: str
    end_node: str
    distance_km: float
    speed_limit_kmh: float = 60.0
    active_jam: Optional[ActiveJam] = None

    @property
    def nominal_travel_time_minutes(self) -> float:
        return (self.distance_km / self.speed_limit_kmh) * 60.0


class PathResult(BaseModel):
    nodes: List[str]
    edges: List[str]
    total_distance_km: float
    nominal_time_minutes: float
    jams_encountered: List[ActiveJam]


class RoadGraph:
    """Graph representation of the city road network with dynamic traffic conditions."""

    def __init__(self):
        self.nodes: Dict[str, RoadNode] = {}
        self.adjacency: Dict[str, List[RoadEdge]] = {}
        self.edges_by_id: Dict[str, RoadEdge] = {}

    def add_node(self, node_id: str, name: str, latitude: float, longitude: float) -> RoadNode:
        node = RoadNode(id=node_id, name=name, latitude=latitude, longitude=longitude)
        self.nodes[node_id] = node
        if node_id not in self.adjacency:
            self.adjacency[node_id] = []
        return node

    def add_edge(
        self,
        edge_id: str,
        start_node: str,
        end_node: str,
        distance_km: float,
        speed_limit_kmh: float = 60.0,
        bidirectional: bool = True,
    ):
        edge1 = RoadEdge(
            id=edge_id,
            start_node=start_node,
            end_node=end_node,
            distance_km=distance_km,
            speed_limit_kmh=speed_limit_kmh,
        )
        self.adjacency[start_node].append(edge1)
        self.edges_by_id[edge_id] = edge1

        if bidirectional:
            edge_id_rev = f"{edge_id}_rev"
            edge2 = RoadEdge(
                id=edge_id_rev,
                start_node=end_node,
                end_node=start_node,
                distance_km=distance_km,
                speed_limit_kmh=speed_limit_kmh,
            )
            self.adjacency[end_node].append(edge2)
            self.edges_by_id[edge_id_rev] = edge2

    def set_jam(
        self,
        edge_id: str,
        severity: float,
        delay_minutes: float,
        started_minutes_ago: float = 0.0,
    ):
        """Inject or update a real-time traffic jam on a road segment."""
        edge = self.edges_by_id.get(edge_id)
        if edge:
            edge.active_jam = ActiveJam(
                segment_id=edge_id,
                start_node=edge.start_node,
                end_node=edge.end_node,
                severity=severity,
                delay_minutes=delay_minutes,
                started_minutes_ago=started_minutes_ago,
            )

    def clear_jam(self, edge_id: str):
        edge = self.edges_by_id.get(edge_id)
        if edge:
            edge.active_jam = None

    def find_shortest_path(
        self,
        start_node: str,
        target_node: str,
        avoid_edges: Optional[List[str]] = None,
    ) -> Optional[PathResult]:
        """Finds the fastest nominal path using Dijkstra's algorithm."""
        if start_node not in self.nodes or target_node not in self.nodes:
            return None

        avoid = set(avoid_edges or [])
        # Priority queue stores (cumulative_minutes, current_node, path_nodes, path_edges)
        pq: List[Tuple[float, str, List[str], List[str]]] = [(0.0, start_node, [start_node], [])]
        min_time: Dict[str, float] = {start_node: 0.0}

        while pq:
            current_time, u, path_nodes, path_edges = heapq.heappop(pq)

            if u == target_node:
                # Calculate total distance and collect jams
                total_dist = 0.0
                jams: List[ActiveJam] = []
                for e_id in path_edges:
                    edge = self.edges_by_id[e_id]
                    total_dist += edge.distance_km
                    if edge.active_jam:
                        jams.append(edge.active_jam)

                return PathResult(
                    nodes=path_nodes,
                    edges=path_edges,
                    total_distance_km=round(total_dist, 2),
                    nominal_time_minutes=round(current_time, 2),
                    jams_encountered=jams,
                )

            if current_time > min_time.get(u, float("inf")):
                continue

            for edge in self.adjacency.get(u, []):
                if edge.id in avoid:
                    continue

                v = edge.end_node
                tentative_time = current_time + edge.nominal_travel_time_minutes

                if tentative_time < min_time.get(v, float("inf")):
                    min_time[v] = tentative_time
                    heapq.heappush(
                        pq,
                        (tentative_time, v, path_nodes + [v], path_edges + [edge.id]),
                    )

        return None

    def estimate_travel_time_to_segment(
        self, path_result: PathResult, target_segment_id: str
    ) -> float:
        """Computes the travel time (in minutes) from path start until reaching a specific segment."""
        time_elapsed = 0.0
        for edge_id in path_result.edges:
            if edge_id == target_segment_id:
                break
            edge = self.edges_by_id[edge_id]
            time_elapsed += edge.nominal_travel_time_minutes
        return time_elapsed
