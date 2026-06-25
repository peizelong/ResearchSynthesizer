from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class ExtractedClaim:
    claim_type: str  # direction|fact|prediction|causality
    subject: str
    predicate: str
    object_value: str | None = None
    direction_tag: str | None = None
    direction_angle: str | None = None  # policy|industry|company|tech|macro
    evidence_text: str = ""
    confidence: float = 0.5


class ClaimExtractor(ABC):
    model_name: str

    @abstractmethod
    def extract(self, title: str, content: str) -> list[ExtractedClaim]:
        ...
