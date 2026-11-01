"""Typed configuration for the population simulator."""

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator

Intent = Literal["commute", "errand", "leisure", "stay_home"]
Departure = Literal["now", "delay_short", "delay_long"]
Share = Literal["low", "medium", "high"]
INTENTS: tuple[str, ...] = ("commute", "errand", "leisure", "stay_home")
DEPARTURES: tuple[str, ...] = ("now", "delay_short", "delay_long")
SHARES: tuple[str, ...] = ("low", "medium", "high")


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ClusterConfig(Strict):
    id: str
    name: str
    persona: str
    population: int = Field(gt=0)
    source_id: int = Field(ge=0)
    offset_m: tuple[float, float] = (0.0, 0.0)


class RootCauseConfig(Strict):
    base_url: str
    model: str
    fallback_model: str
    reasoning_effort: Literal["low", "medium", "high"] = "medium"
    temperature: float = 0.2
    max_tokens: int = 4096
    timeout_sec: float = 60


class SimConfig(Strict):
    twin_url: str
    llm_base_url: str
    llm_model: str
    llm_timeout_sec: float
    llm_temperature: float
    llm_max_tokens: int
    max_concurrent_llm: int = Field(ge=1)
    poll_interval_sec: float = Field(gt=0)
    planning_interval_sim_sec: float = Field(gt=0)
    clock_start: str
    memory_size: int = Field(ge=0)
    trace_log_size: int = Field(ge=1)
    car_cluster_size: int = Field(ge=1)
    seed: int
    walk_router_url: str = ""
    root_cause: RootCauseConfig | None = None
    walk_cache_path: str = "data/walk_paths.json"
    share_fraction: dict[Share, float]
    car_ratio: dict[Intent, float]
    departure_window_sec: dict[Departure, tuple[float, float]]
    clusters: list[ClusterConfig]

    @model_validator(mode="after")
    def complete_tables(self) -> "SimConfig":
        if set(self.share_fraction) != set(SHARES) or set(self.car_ratio) != set(INTENTS):
            raise ValueError("share_fraction / car_ratio must cover every enum value")
        if set(self.departure_window_sec) != set(DEPARTURES):
            raise ValueError("departure_window_sec must cover every departure option")
        if len({c.id for c in self.clusters}) != len(self.clusters):
            raise ValueError("cluster ids must be unique")
        return self


def load_config(path: str | Path) -> SimConfig:
    with open(path, "r", encoding="utf-8") as f:
        return SimConfig.model_validate(yaml.safe_load(f))
