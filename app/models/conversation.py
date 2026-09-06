from dataclasses import asdict, dataclass, field
from enum import StrEnum
from typing import Any


class Intent(StrEnum):
    CHAT = "CHAT"
    MENTIONED_MOVIE = "MENTIONED_MOVIE"
    CONFIRMING_MOVIE = "CONFIRMING_MOVIE"
    COLLECTING_LOG_DETAILS = "COLLECTING_LOG_DETAILS"
    READY_TO_LOG = "READY_TO_LOG"
    LOGGED = "LOGGED"
    MEMORY_RECALL = "MEMORY_RECALL"
    RECOMMENDING = "RECOMMENDING"


@dataclass
class ConversationState:
    intent: str = Intent.CHAT
    current_movie: dict[str, Any] | None = None
    watched: bool = False
    rating: float | None = None
    rewatch: bool = False
    watched_date: str | None = None
    review: str = ""
    missing_fields: list[str] = field(default_factory=list)
    candidates: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None):
        if not data:
            return cls()
        return cls(**{key: data[key] for key in cls.__dataclass_fields__ if key in data})


@dataclass
class AgentDecision:
    intent: str
    details: dict[str, Any] = field(default_factory=dict)
    speech: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
