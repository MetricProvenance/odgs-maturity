"""
Charter data models.

Defines the structures for improvement charters generated
from maturity assessment results. Three charter types map
directly to the ISO/IEC 38505-1 & ISO/IEC 25012 framework:

  1. LifecyclePainPoint — Process-stage improvement charter
  2. KPIImprovement — KPI reliability charter
  3. StrategicOrAIInitiative — Strategic/AI readiness charter
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
from typing import Any


class CharterType(Enum):
    """The three charter types from the Clavis framework."""
    LIFECYCLE_PAIN_POINT = "LifecyclePainPoint"
    KPI_IMPROVEMENT = "KPIImprovement"
    STRATEGIC_OR_AI = "StrategicOrAIInitiative"

    @property
    def display_name(self) -> str:
        names = {
            "LifecyclePainPoint": "Lifecycle Pain Point Charter",
            "KPIImprovement": "KPI Improvement Charter",
            "StrategicOrAIInitiative": "Strategic / AI Initiative Charter",
        }
        return names[self.value]

    @property
    def description(self) -> str:
        descs = {
            "LifecyclePainPoint": (
                "Addresses pain points within a specific business process "
                "stage. Most comprehensive — 8 sections covering business "
                "case through next steps."
            ),
            "KPIImprovement": (
                "Focuses on improving the reliability and trustworthiness "
                "of a specific KPI. 3 focused sections."
            ),
            "StrategicOrAIInitiative": (
                "Prepares data readiness for a strategic or AI programme. "
                "2 executive-level sections."
            ),
        }
        return descs[self.value]


class SPOTCategory(Enum):
    """SPOT root-cause classification."""
    STANDARD = "Standard"
    PROCESS = "Process"
    ORGANIZATION = "Organization"
    TECHNOLOGY = "Technology"


@dataclass
class CharterSection:
    """A single section within a generated charter."""
    heading: str
    section_id: str
    content: list[str] = field(default_factory=list)
    guidance: str = ""


@dataclass
class CharterContext:
    """
    User-provided context that drives charter template population.

    This is the input to the charter generator — it combines
    maturity assessment results with user selections.
    """
    # Common fields
    charter_type: CharterType = CharterType.LIFECYCLE_PAIN_POINT
    org_name: str = ""
    maturity_score: float = 0.0
    maturity_level: str = ""

    # Lifecycle Pain Point fields
    lifecycle_id: str = ""
    lifecycle_name: str = ""
    stage_id: str = ""
    stage_name: str = ""
    pain_points: list[str] = field(default_factory=list)

    # KPI Improvement fields
    kpi_name: str = ""
    kpi_objective: str = ""
    data_sources: list[str] = field(default_factory=list)

    # Strategic/AI Initiative fields
    initiative_name: str = ""
    ai_use_case: str = ""

    # Auto-populated from maturity gaps
    affected_dimension_ids: list[int] = field(default_factory=list)
    dimension_names: list[str] = field(default_factory=list)
    strategic_objective_id: str = ""
    strategic_objective_name: str = ""
    spot_classifications: dict[str, list[str]] = field(default_factory=dict)
    cost_flags: list[str] = field(default_factory=list)
    red_flag_rules: list[str] = field(default_factory=list)
    regulatory_alignment: list[str] = field(default_factory=list)

    # Metadata
    generated_at: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class Charter:
    """
    Complete generated charter document.

    This is the output of the charter generator — ready for
    export to Markdown, JSON, or PDF.
    """
    charter_type: CharterType
    title: str
    sections: list[CharterSection] = field(default_factory=list)
    context: CharterContext = field(default_factory=CharterContext)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialise charter for JSON export."""
        return {
            "charter_type": self.charter_type.value,
            "title": self.title,
            "generated_at": self.context.generated_at,
            "maturity_score": self.context.maturity_score,
            "maturity_level": self.context.maturity_level,
            "org_name": self.context.org_name,
            "sections": [
                {
                    "heading": s.heading,
                    "id": s.section_id,
                    "content": s.content,
                    "guidance": s.guidance,
                }
                for s in self.sections
            ],
            "metadata": self.metadata,
        }
